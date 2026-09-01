"""Fabricated Week-8 launch evidence; no real fit is executed."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import append_jsonl, atomic_write_json, read_json
from bu.experiments import batch as B
from bu.experiments import preflight as P
from bu.experiments import week7_launch as W7L
from bu.experiments import week7_plan as W7P
from bu.experiments import week8_launch as L
from bu.experiments import week8_preflight as PF
from bu.experiments.prefit_storage import PreflightStorageGuard
from bu.experiments.supervisor import LeaseConflictError, acquire_batch_lease
from bu.runrecord import GitState


@pytest.fixture(scope="module")
def jobs():
    inventory = W7P.configuration_sweep_baseline_jobs()
    unit = inventory[3].unit
    selected = tuple(job for job in inventory if job.unit == unit)
    assert len(selected) == 3
    return selected


@pytest.fixture
def case(tmp_path, monkeypatch, jobs):
    roots = {
        name: tmp_path / name for name in ("preflight", "output", "staging", "sync")
    }
    for root in roots.values():
        root.mkdir()
    (tmp_path / PF.COMMON_CONTROL_DIRECTORY).mkdir()
    plan = atomic_write_json(tmp_path / "inputs" / "plan.json", {"synthetic": 8})
    pins = P._pinned_package_versions()
    monkeypatch.setattr(PF, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(P, "git_state", lambda: GitState("b" * 40, False, "main"))
    monkeypatch.setattr(P, "package_versions", lambda: dict(pins))
    monkeypatch.setattr(P, "_device_available", lambda device: device == "cpu")
    monkeypatch.setattr(
        P.shutil,
        "disk_usage",
        lambda root: SimpleNamespace(free=PF.WEEK8_MINIMUM_FREE_BYTES + 1_000_000),
    )

    def input_file(path):
        checked = PF._project_path(path, what="plan", directory=False)
        return checked, read_json(checked)

    def fixed_jobs(document, key):
        if document != {"synthetic": 8} or key != "sweep-002":
            raise ValueError("not the exact synthetic Week-8 batch")
        return jobs

    monkeypatch.setattr(PF, "_input_file", input_file)
    monkeypatch.setattr(PF, "_batch_jobs", fixed_jobs)
    calls = []

    def fake_batch(selected, **kwargs):
        calls.append((selected, kwargs))
        return B.BatchReport(
            B._manifest(selected)["batch_id"],
            len(selected),
            len(selected),
            0,
            len(selected),
            0,
            0,
        )

    monkeypatch.setattr(B, "_run_batch", fake_batch)
    arguments = {
        "plan_path": plan,
        "batch_key": "sweep-002",
        "preflight_dir": roots["preflight"],
        "output_root": roots["output"],
        "staging_root": roots["staging"],
        "sync_root": roots["sync"],
        "sync_destination_identity": "synthetic-independent-week8-copy",
    }
    return roots, arguments, calls


def _ready(case):
    roots, arguments, _ = case
    PF.run_week8_preflight(**arguments)
    return roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE


def _launch(case, **extra):
    roots, _, _ = case
    return L.launch_week8(
        preflight_report=roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE,
        output_root=roots["output"],
        sync_root=roots["sync"],
        **extra,
    )


def _rewrite_both(case, change):
    roots, _, _ = case
    path = roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE
    document = read_json(path)
    change(document)
    raw = PF.L._pretty_json_bytes(document)
    path.write_bytes(raw)
    (roots["sync"] / path.name).write_bytes(raw)


def test_fixed_executor_spawn_timeout_storage_guard_and_sweep_anchor(case, jobs):
    _ready(case)
    result = _launch(case)
    roots, _, calls = case
    assert len(calls) == 1
    selected, kwargs = calls[0]
    assert selected == jobs
    assert kwargs["executor"] is B._default_executor
    assert kwargs["require_fit_evidence"] is True
    assert kwargs["expected_git_commit"] == "b" * 40
    assert kwargs["attempt_timeout_seconds"] == L.WEEK8_ATTEMPT_TIMEOUT_SECONDS
    assert kwargs["attempt_staging_root"] == roots["staging"]
    assert callable(kwargs["sync"])
    guard = kwargs["preflight_storage_guard"]
    assert type(guard) is PreflightStorageGuard
    assert guard.source_path == roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE
    assert dict(guard.roots) == roots
    guard.check(output_root=roots["output"], staging_root=roots["staging"])
    execution = result["start"]["record"]["execution"]
    assert type(execution["attempt_timeout_seconds"]) is float
    assert execution == {
        "attempt_timeout_seconds": L.WEEK8_ATTEMPT_TIMEOUT_SECONDS,
        "fresh_process_per_attempt": True,
        "registered_executor_only": True,
        "cpu_only": True,
        "prefit_storage_check_before_each_new_child": True,
        "sweep_anchors_required": True,
    }
    assert result["status"] == "complete"
    assert result["scientific_analysis_performed"] is False


def test_start_is_published_durable_first_and_copies_are_independent(case, monkeypatch):
    _ready(case)
    roots, _, _ = case
    original = L.atomic_write_json
    order = []

    def observed(path, document):
        if L.WEEK8_START_DIRECTORY in Path(path).parts:
            order.append(Path(path))
        return original(path, document)

    monkeypatch.setattr(L, "atomic_write_json", observed)
    result = _launch(case)
    assert order[0].is_relative_to(roots["sync"])
    assert order[1].is_relative_to(roots["output"])
    local = Path(result["start"]["local_path"])
    durable = Path(result["start"]["durable_path"])
    assert local.read_bytes() == durable.read_bytes()
    assert not os.path.samefile(local, durable)


def test_week7_and_week8_share_one_live_lease_namespace(case):
    _ready(case)
    assert L.WEEK8_LEASE_NAME == W7L.WEEK7_LEASE_NAME == "week7-production"
    owner = acquire_batch_lease(PF._control_root(), lease_name=W7L.WEEK7_LEASE_NAME)
    try:
        with pytest.raises(LeaseConflictError):
            _launch(case)
        assert case[2] == []
    finally:
        owner.release()


def test_executor_subset_device_floor_and_age_recovery_are_not_public(case):
    _ready(case)
    for extra in (
        {"executor": object()},
        {"jobs": ()},
        {"device": "cuda"},
        {"minimum_free_bytes": 0},
        {"stale_lease_after_seconds": 1},
    ):
        with pytest.raises(TypeError):
            _launch(case, **extra)
    for timeout in (30.0, 3600):
        with pytest.raises(ValueError, match="frozen at exactly"):
            _launch(case, attempt_timeout_seconds=timeout)
    assert case[2] == []


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(status="complete"),
        lambda d: d.update(batch_key="sweep-003"),
        lambda d: d.update(binding_sha256="0" * 64),
        lambda d: d["batch"]["jobs"].pop(),
        lambda d: d["environment"]["git"].update(commit="c" * 40),
        lambda d: d["device"].update(requested_route="cuda"),
    ],
)
def test_changed_preflight_refuses_before_lease_or_batch(case, change):
    _ready(case)
    _rewrite_both(case, change)
    with pytest.raises(ValueError):
        _launch(case)
    roots, _, calls = case
    assert calls == []
    assert not (PF._control_root() / "leases").exists()
    assert not (roots["output"] / L.WEEK8_REPORT_DIRECTORY).exists()


def test_failure_preserves_start_reports_failure_and_releases_owned_lease(case, monkeypatch):
    _ready(case)
    roots, _, _ = case
    monkeypatch.setattr(B, "_run_batch", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("synthetic interruption")
    ))
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        _launch(case)
    active = PF._control_root() / "leases" / f"{L.WEEK8_LEASE_NAME}.lease.json"
    assert not active.exists()
    reports = list((roots["output"] / L.WEEK8_REPORT_DIRECTORY).glob("*.json"))
    assert len(reports) == 1
    report = read_json(reports[0])
    assert report["status"] == "failed"
    assert report["failure"]["type"] == "RuntimeError"
    assert Path(report["start"]["durable_path"]).is_file()
    assert reports[0].read_bytes() == (
        roots["sync"] / L.WEEK8_REPORT_DIRECTORY / reports[0].name
    ).read_bytes()


def _preserve_failed_attempt(case, jobs):
    roots, _, _ = case
    path = roots["output"] / B._manifest(jobs)["batch_id"] / B.EVENTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    job = jobs[0]
    append_jsonl(path, {
        "schema_version": B.BATCH_SCHEMA_VERSION,
        "job_id": job.job_id,
        "status": "started",
    })
    append_jsonl(path, {
        "schema_version": B.BATCH_SCHEMA_VERSION,
        "job_id": job.job_id,
        "status": "failed",
        "error_type": "RuntimeError",
        "error": "preserved synthetic failure",
    })
    return path


def test_preserved_failed_attempt_refuses_before_lease_or_lower_execution(case, jobs):
    _ready(case)
    _preserve_failed_attempt(case, jobs)
    with pytest.raises(ValueError, match="no-retry.*preserved failed"):
        _launch(case)
    roots, _, calls = case
    assert calls == []
    assert not (PF._control_root() / "leases").exists()
    assert not (roots["output"] / L.WEEK8_REPORT_DIRECTORY).exists()


def test_failed_attempt_is_rechecked_after_shared_lease_acquisition(
    case, jobs, monkeypatch
):
    _ready(case)
    original = L.acquire_batch_lease

    def acquire_then_fail(*args, **kwargs):
        lease = original(*args, **kwargs)
        _preserve_failed_attempt(case, jobs)
        return lease

    monkeypatch.setattr(L, "acquire_batch_lease", acquire_then_fail)
    with pytest.raises(ValueError, match="no-retry.*preserved failed"):
        _launch(case)
    roots, _, calls = case
    assert calls == []
    active = PF._control_root() / "leases" / f"{L.WEEK8_LEASE_NAME}.lease.json"
    assert not active.exists()
    reports = list((roots["output"] / L.WEEK8_REPORT_DIRECTORY).glob("*.json"))
    assert len(reports) == 1
    report = read_json(reports[0])
    assert report["status"] == "failed"
    assert report["launch_performed"] is False


def test_resume_is_delegated_to_same_exact_batch_without_refit_override(
    case, jobs, monkeypatch
):
    _ready(case)
    seen = []

    def resumed(selected, **kwargs):
        seen.append(tuple(job.job_id for job in selected))
        return B.BatchReport(
            B._manifest(selected)["batch_id"], len(selected), 0, len(selected),
            len(selected), 0, 0,
        )

    monkeypatch.setattr(B, "_run_batch", resumed)
    result = _launch(case)
    assert result["batch"]["executed"] == 0
    assert result["batch"]["resumed"] == 3
    assert seen == [tuple(job.job_id for job in jobs)]
