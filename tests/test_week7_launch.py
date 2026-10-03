"""Fabricated Week-7 readiness/launch evidence; never execute a real fit."""

import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_json, read_json
from bu.experiments import batch as B
from bu.experiments import preflight as P
from bu.experiments import week7_launch as L
from bu.experiments import week7_plan as W
from bu.experiments import week7_preflight as PF
from bu.experiments.supervisor import LeaseConflictError, acquire_batch_lease
from bu.runrecord import GitState


@pytest.fixture(scope="module")
def jobs():
    inventory = W.configuration_sweep_baseline_jobs()
    unit = inventory[0].unit
    return tuple(j for j in inventory if j.unit == unit)


@pytest.fixture
def case(tmp_path, monkeypatch, jobs):
    roots = {n: tmp_path / n for n in ("preflight", "output", "staging", "sync")}
    for root in roots.values():
        root.mkdir()
    (tmp_path / "week7-production-control").mkdir()
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    plan = atomic_write_json(inputs / "plan.json", {"synthetic_plan": 1})
    ledger = atomic_write_json(inputs / "ledger.json", {"synthetic_reuse": 5})
    pins = P._pinned_package_versions()
    monkeypatch.setattr(PF, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(P, "git_state", lambda: GitState("b" * 40, False, "main"))
    monkeypatch.setattr(P, "package_versions", lambda: dict(pins))
    monkeypatch.setattr(P, "_device_available", lambda device: device == "cpu")

    def load_inputs(plan_path, reuse_path):
        # Only this fixture substitutes scientific/source loaders. Production
        # loaders receive real independent expected commits and reopen sources.
        p = PF._project_path(plan_path, what="plan", directory=False)
        r = PF._project_path(reuse_path, what="reuse", directory=False)
        return p, read_json(p), r, read_json(r)

    def fixed_jobs(plan_doc, key):
        if plan_doc != {"synthetic_plan": 1} or key != "first-sweep":
            raise ValueError("not exact enabled synthetic batch")
        return jobs

    monkeypatch.setattr(PF, "_input_files", load_inputs)
    monkeypatch.setattr(PF, "_batch_jobs", fixed_jobs)
    calls = []

    def fake_batch(selected, **kwargs):
        calls.append((selected, kwargs))
        return B.BatchReport(B._manifest(selected)["batch_id"], len(selected),
                             len(selected), 0, len(selected), 0, 0)

    monkeypatch.setattr(B, "_run_batch", fake_batch)
    args = dict(plan_path=plan, reuse_ledger_path=ledger, batch_key="first-sweep",
                preflight_dir=roots["preflight"], output_root=roots["output"],
                staging_root=roots["staging"], sync_root=roots["sync"],
                sync_destination_identity="synthetic-independent-project-copy",
                minimum_free_bytes=0)
    return roots, args, calls


def ready(case):
    roots, args, calls = case
    PF.run_week7_preflight(**args)
    return roots["preflight"] / PF.WEEK7_PREFLIGHT_FILE


def launch(case, **extras):
    roots, _, _ = case
    return L.launch_week7(
        preflight_report=roots["preflight"] / PF.WEEK7_PREFLIGHT_FILE,
        output_root=roots["output"], sync_root=roots["sync"],
        attempt_timeout_seconds=3600, **extras,
    )


def rewrite_both(case, change):
    roots, _, _ = case
    path = roots["preflight"] / PF.WEEK7_PREFLIGHT_FILE
    doc = read_json(path)
    change(doc)
    raw = PF.L._pretty_json_bytes(doc)
    path.write_bytes(raw)
    (roots["sync"] / path.name).write_bytes(raw)


def test_preflight_publishes_independent_inputs_report_and_canary(case):
    path = ready(case)
    roots, args, calls = case
    assert calls == []
    assert tuple(roots["output"].iterdir()) == ()
    assert tuple(roots["staging"].iterdir()) == ()
    for name in (PF.WEEK7_PREFLIGHT_FILE, "week7_launch_plan.json",
                 "week7_reuse_ledger.json", P.SYNC_CANARY_FILE):
        source, copy = roots["preflight"] / name, roots["sync"] / name
        assert source.read_bytes() == copy.read_bytes()
        assert not os.path.samefile(source, copy)
    validated = PF.validate_week7_preflight(
        path, output_root=roots["output"], sync_root=roots["sync"])
    assert validated.git_commit == "b" * 40
    assert validated.report["launch_performed"] is False


def test_launch_only_fixed_executor_timeout_sync_and_matching_receipts(case, jobs):
    ready(case)
    result = launch(case)
    roots, _, calls = case
    assert len(calls) == 1
    selected, kwargs = calls[0]
    assert selected == jobs
    assert kwargs["executor"] is B._default_executor
    assert kwargs["require_fit_evidence"] is True
    assert kwargs["expected_git_commit"] == "b" * 40
    assert kwargs["attempt_timeout_seconds"] == 3600
    assert kwargs["attempt_staging_root"] == roots["staging"]
    assert callable(kwargs["sync"])
    assert result["status"] == "complete"
    assert result["historical_reuse_retrained"] is False
    start = result["start"]
    assert Path(start["local_path"]).read_bytes() == Path(start["durable_path"]).read_bytes()
    assert start["record"]["execution"]["sweep_anchors_required"] is True
    assert start["record"]["batch"]["job_count"] == 3
    assert Path(result["released_lease"]["path"]).is_file()
    report = Path(result["report_path"])
    assert report.read_bytes() == (roots["sync"] / L.WEEK7_REPORT_DIRECTORY / report.name).read_bytes()


@pytest.mark.parametrize("change", [
    lambda d: d.update(week7_preflight_schema_version=True),
    lambda d: d.update(status="complete"),
    lambda d: d.update(launch_performed=True),
    lambda d: d.update(extra=True),
    lambda d: d.update(batch_key="second-sweep"),
    lambda d: d.update(binding_sha256="0" * 64),
    lambda d: d["batch"]["jobs"].pop(),
    lambda d: d["inputs"]["plan"].update(sha256="0" * 64),
    lambda d: d["environment"]["git"].update(commit="c" * 40),
    lambda d: d["device"].update(requested_route="cuda"),
    lambda d: d["storage"].update(minimum_free_bytes=True),
    lambda d: d["sync_receipt"].update(destination_identity="wrong"),
])
def test_resigned_bad_reports_refuse_before_any_launch(case, change):
    ready(case)
    rewrite_both(case, change)
    with pytest.raises(ValueError):
        launch(case)
    roots, _, calls = case
    assert calls == []
    assert not (roots["output"] / "leases").exists()


@pytest.mark.parametrize("which", ["plan_path", "reuse_ledger_path"])
def test_changed_original_input_refuses(case, which):
    ready(case)
    _, args, calls = case
    args[which].write_text('{"changed": true}\n')
    with pytest.raises(ValueError):
        launch(case)
    assert calls == []


@pytest.mark.parametrize("name", [PF.WEEK7_PREFLIGHT_FILE, "week7_launch_plan.json",
                                 "week7_reuse_ledger.json", P.SYNC_CANARY_FILE])
def test_missing_independent_readiness_evidence_refuses(case, name):
    ready(case)
    roots, _, calls = case
    (roots["sync"] / name).unlink()
    with pytest.raises(ValueError):
        launch(case)
    assert calls == []


def test_hardlinked_canary_refuses(case):
    ready(case)
    roots, _, calls = case
    copy = roots["sync"] / P.SYNC_CANARY_FILE
    copy.unlink()
    os.link(roots["preflight"] / P.SYNC_CANARY_FILE, copy)
    with pytest.raises(ValueError, match="hard-linked|aliases"):
        launch(case)
    assert calls == []


def test_changed_git_and_package_environment_refuses(case, monkeypatch):
    ready(case)
    monkeypatch.setattr(P, "git_state", lambda: GitState("b" * 40, True, "main"))
    with pytest.raises(ValueError, match="trustworthy"):
        launch(case)
    assert case[2] == []


def test_overlapping_roots_and_outside_workspace_refuse(case, monkeypatch):
    roots, args, calls = case
    with pytest.raises(ValueError, match="non-overlapping"):
        PF.run_week7_preflight(**{**args, "sync_root": roots["output"]})
    monkeypatch.setattr(PF, "WORKSPACE_ROOT", roots["output"])
    with pytest.raises(ValueError, match="inside the project"):
        PF.run_week7_preflight(**args)
    assert calls == []


def test_live_lease_conflict_never_launches(case):
    ready(case)
    roots, _, calls = case
    owner = acquire_batch_lease(PF._control_root(), lease_name=L.WEEK7_LEASE_NAME)
    try:
        with pytest.raises(LeaseConflictError):
            launch(case)
        assert calls == []
    finally:
        owner.release()


def test_executor_and_age_override_not_public(case):
    ready(case)
    for extra in ({"executor": object()}, {"stale_lease_after_seconds": 1}):
        with pytest.raises(TypeError):
            launch(case, **extra)
    assert case[2] == []


def test_batch_failure_preserves_receipts_and_releases_owned_lease(case, monkeypatch):
    ready(case)
    roots, _, calls = case
    def broken(*args, **kwargs):
        raise RuntimeError("synthetic interruption")
    monkeypatch.setattr(B, "_run_batch", broken)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        launch(case)
    assert not (PF._control_root() / "leases" / f"{L.WEEK7_LEASE_NAME}.lease.json").exists()
    reports = list((roots["output"] / L.WEEK7_REPORT_DIRECTORY).glob("*.json"))
    assert len(reports) == 1
    report = read_json(reports[0])
    assert report["status"] == "failed"
    assert report["failure"]["type"] == "RuntimeError"
    assert Path(report["start"]["durable_path"]).is_file()


def test_sources_reopened_at_preflight_launch_and_completion(case, monkeypatch):
    original = PF._input_files
    reopens = []
    def observed(*args):
        reopens.append(args)
        return original(*args)
    monkeypatch.setattr(PF, "_input_files", observed)
    ready(case)
    before = len(reopens)
    launch(case)
    assert len(reopens) >= before + 3


def test_wrong_batch_accounting_refuses_and_records_failure(case, monkeypatch):
    ready(case)
    def wrong(jobs, **kwargs):
        return B.BatchReport("wrong", len(jobs), len(jobs), 0, len(jobs), 0, 0)
    monkeypatch.setattr(B, "_run_batch", wrong)
    with pytest.raises(ValueError, match="batch"):
        launch(case)


def test_completion_rejects_another_valid_preflight_digest(case, monkeypatch):
    path = ready(case)
    roots, _, calls = case
    original_digest = L.sha256_file(path)
    original_batch = B._run_batch

    def changed_during_batch(selected, **kwargs):
        result = original_batch(selected, **kwargs)
        # This measured snapshot is not part of the configuration binding.
        # Both copies remain canonical and independently pass preflight, but
        # they are NOT the immutable document that authorized this launch.
        def change(document):
            document["storage"]["roots"]["output"]["free_bytes"] -= 1
        rewrite_both(case, change)
        refreshed = PF.validate_week7_preflight(
            path, output_root=roots["output"], sync_root=roots["sync"])
        assert refreshed.report_sha256 != original_digest
        return result

    monkeypatch.setattr(B, "_run_batch", changed_during_batch)
    with pytest.raises(ValueError, match="preflight changed during execution"):
        launch(case)
    assert len(calls) == 1
    reports = list((roots["output"] / L.WEEK7_REPORT_DIRECTORY).glob("*.json"))
    assert len(reports) == 1
    report = read_json(reports[0])
    assert report["status"] == "failed"
    assert report["failure"]["type"] == "ValueError"
    assert report["batch"]["complete"] is True
    assert report["preflight"]["sha256"] == original_digest
    assert report["preflight"]["sha256"] != L.sha256_file(path)
    assert reports[0].read_bytes() == (
        roots["sync"] / L.WEEK7_REPORT_DIRECTORY / reports[0].name
    ).read_bytes()


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("phase", ["batch", "completion"])
def test_interruption_is_reported_failed_and_reraised(case, monkeypatch, exception_type, phase):
    ready(case)
    roots, _, _ = case
    original_batch = B._run_batch
    original_validate = PF.validate_week7_preflight
    batch_finished = False
    interruption = exception_type("synthetic cancellation")

    def interrupted_batch(selected, **kwargs):
        nonlocal batch_finished
        if phase == "batch":
            raise interruption
        result = original_batch(selected, **kwargs)
        batch_finished = True
        return result

    def interrupted_completion(*args, **kwargs):
        if batch_finished:
            raise interruption
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(B, "_run_batch", interrupted_batch)
    monkeypatch.setattr(PF, "validate_week7_preflight", interrupted_completion)
    with pytest.raises(exception_type) as caught:
        launch(case)
    assert caught.value is interruption
    reports = list((roots["output"] / L.WEEK7_REPORT_DIRECTORY).glob("*.json"))
    assert len(reports) == 1
    report = read_json(reports[0])
    assert report["week7_launch_schema_version"] == L.WEEK7_LAUNCH_SCHEMA_VERSION == 1
    assert report["status"] == "failed"
    assert report["failure"] == {
        "type": exception_type.__name__, "message": "synthetic cancellation",
    }
    assert (report["batch"] is not None) == (phase == "completion")
    assert Path(report["start"]["durable_path"]).is_file()
    assert Path(report["released_lease"]["path"]).is_file()
    assert not (PF._control_root() / "leases" / f"{L.WEEK7_LEASE_NAME}.lease.json").exists()
    assert reports[0].read_bytes() == (
        roots["sync"] / L.WEEK7_REPORT_DIRECTORY / reports[0].name
    ).read_bytes()


def _mark_reparse(monkeypatch, target):
    """Exercise the Windows attribute without requiring symlink privileges."""
    original = Path.lstat
    def marked(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == target:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path, "lstat", marked)


@pytest.mark.parametrize("directory", [False, True])
@pytest.mark.parametrize("component", ["leaf", "parent", "workspace", "anchor"])
def test_every_project_path_component_refuses_reparse_before_resolution(
    tmp_path, monkeypatch, directory, component,
):
    candidate = tmp_path / "outer" / "leaf"
    candidate.parent.mkdir()
    if directory:
        candidate.mkdir()
    else:
        candidate.write_text("synthetic input")
    target = {
        "leaf": candidate, "parent": candidate.parent,
        "workspace": tmp_path, "anchor": Path(candidate.anchor),
    }[component]
    # Keep the low-level attribute simulation out of pytest teardown.
    with monkeypatch.context() as marker:
        marker.setattr(PF, "WORKSPACE_ROOT", tmp_path)
        _mark_reparse(marker, target)
        marker.setattr(Path, "resolve", lambda *a, **k: pytest.fail("resolved a reparse path"))
        with pytest.raises(ValueError, match="link/reparse-point component"):
            PF._project_path(candidate, what="synthetic path", directory=directory)


@pytest.mark.parametrize("phase", ["preflight", "launch"])
@pytest.mark.parametrize("component", [
    "control", "leases", "history", "active", "transition_guard",
])
def test_common_lease_namespace_refuses_reparse_before_acquisition(
    case, monkeypatch, phase, component,
):
    roots, args, calls = case
    if phase == "launch":
        ready(case)
    control = PF._control_root()
    leases = control / "leases"
    leases.mkdir()
    history = leases / "history"
    history.mkdir()
    active = leases / f"{L.WEEK7_LEASE_NAME}.lease.json"
    guard = leases / f".{L.WEEK7_LEASE_NAME}.lease-transition.lock"
    active.write_text("synthetic unconsumed active path")
    guard.write_bytes(b"0")
    target = {
        "control": control, "leases": leases, "history": history,
        "active": active, "transition_guard": guard,
    }[component]
    with monkeypatch.context() as marker:
        _mark_reparse(marker, target)
        marker.setattr(L, "acquire_batch_lease", lambda *a, **k: pytest.fail("acquired redirected lease"))
        with pytest.raises(ValueError, match="link/reparse-point component"):
            if phase == "preflight":
                PF.run_week7_preflight(**args)
            else:
                launch(case)
    assert calls == []
