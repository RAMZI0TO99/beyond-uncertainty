"""Synthetic-only tests for the fixed Week-8 baseline production wrapper.

No fit, model, metric, label, effect, or hypothesis result is produced here.
Every mutable test path is relocated below pytest's configured project-local
base temporary directory, and all low-level training calls are replaced.
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import batch as B
from bu.experiments import week8_baseline_production as P


COMMIT = "c" * 40


def _layout(root: Path, key: str, fits: int, models: int) -> P.BatchLayout:
    stem = "week8-exp2b" if key == "exp2b" else "week8-sweep-002"
    monitor = "week8-monitor-exp2b" if key == "exp2b" else "week8-monitor-sweep-002"
    return P.BatchLayout(
        key=key,
        fit_count=fits,
        model_count=models,
        preflight_root=root / f"{stem}-{P.ATTEMPT}-preflight",
        output_root=root / f"{stem}-{P.ATTEMPT}-output",
        staging_root=root / f"{stem}-{P.ATTEMPT}-staging",
        sync_root=root / f"{stem}-{P.ATTEMPT}-project-evidence",
        monitor_root=root / f"{monitor}-{P.ATTEMPT}",
        monitor_copy_root=root / f"{monitor}-{P.ATTEMPT}-project-evidence",
    )


@pytest.fixture
def fixed_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / P.Preflight.COMMON_CONTROL_DIRECTORY).mkdir()
    preparation = root / f"week8-baseline-preparation-{P.ATTEMPT}"
    exp2b = _layout(root, "exp2b", 125, 625)
    sweep = _layout(root, "sweep-002", 3, 15)
    monkeypatch.setattr(P, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(P.Preflight, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(P, "PREPARATION_ROOT", preparation)
    monkeypatch.setattr(P, "PREPARATION_ORIGINAL_ROOT", preparation / "original")
    monkeypatch.setattr(
        P, "PREPARATION_COPY_ROOT", preparation / "project-evidence"
    )
    monkeypatch.setattr(P, "EXP2B", exp2b)
    monkeypatch.setattr(P, "SWEEP_002", sweep)
    monkeypatch.setattr(P, "BATCHES", {"exp2b": exp2b, "sweep-002": sweep})
    monkeypatch.setattr(
        P.Preflight.L,
        "_current_environment",
        lambda: {
            "git": {
                "commit": COMMIT,
                "branch": "synthetic",
                "dirty": False,
                "trustworthy": True,
            },
            "python": "synthetic",
            "platform": "synthetic",
            "packages": {},
            "exact_pins": {},
        },
    )
    monkeypatch.setattr(
        P.Preflight.P,
        "_verify_device",
        lambda route: {
            "frozen_route": route,
            "requested_route": route,
            "available": True,
        },
    )

    def write_plan(directory: Path) -> Path:
        return atomic_write_json(
            Path(directory) / P.Plan.WEEK8_PLAN_FILE,
            {
                "plan_digest": "a" * 64,
                "authorized_batch_keys": ["exp2b", "sweep-002"],
                "fit_count": 128,
                "member_model_count": 640,
            },
        )

    def load_plan(path: Path, **_kwargs):
        document = read_json(path)
        if document.get("plan_digest") != "a" * 64:
            raise ValueError("synthetic plan changed")
        return document

    monkeypatch.setattr(P.Plan, "write_week8_launch_plan", write_plan)
    monkeypatch.setattr(P.Plan, "load_week8_launch_plan", load_plan)
    return root, exp2b, sweep


@pytest.fixture
def prepared(fixed_workspace, monkeypatch):
    P.prepare(expected_git_commit=COMMIT)
    return fixed_workspace


@pytest.fixture
def preflight_boundary(prepared, monkeypatch):
    root, exp2b, sweep = prepared
    calls: list[dict[str, object]] = []

    def layout_for_output(path: Path) -> P.BatchLayout:
        target = Path(path)
        for layout in (exp2b, sweep):
            if target == layout.output_root:
                return layout
        raise ValueError("unknown synthetic output root")

    def run(**kwargs):
        calls.append(dict(kwargs))
        layout = layout_for_output(kwargs["output_root"])
        document = {
            "synthetic": True,
            "batch_key": layout.key,
            "git_commit": COMMIT,
        }
        atomic_write_json(
            layout.preflight_root / P.Preflight.WEEK8_PREFLIGHT_FILE, document
        )
        atomic_write_json(
            layout.sync_root / P.Preflight.WEEK8_PREFLIGHT_FILE, document
        )
        return document

    def validate(path: Path, *, output_root: Path, sync_root: Path):
        layout = layout_for_output(output_root)
        if Path(path) != layout.preflight_root / P.Preflight.WEEK8_PREFLIGHT_FILE:
            raise ValueError("wrong synthetic preflight path")
        if Path(sync_root) != layout.sync_root:
            raise ValueError("wrong synthetic durable root")
        jobs = P._expected_jobs(layout)
        return SimpleNamespace(
            report_path=Path(path).resolve(),
            report_sha256=sha256_file(path),
            git_commit=COMMIT,
            jobs=jobs,
            roots=P._batch_roots(layout),
            report={
                "batch_key": layout.key,
                "batch": B._manifest(jobs),
                "binding_sha256": "b" * 64,
            },
        )

    monkeypatch.setattr(P.Preflight, "run_week8_preflight", run)
    monkeypatch.setattr(P.Preflight, "validate_week8_preflight", validate)
    return root, exp2b, sweep, calls


def _ready_exp2b(preflight_boundary):
    result = P.preflight_exp2b()
    assert result["status"] == "ready"
    return preflight_boundary


def _fake_launch_history(monkeypatch: pytest.MonkeyPatch):
    launched: dict[str, bool] = {}
    calls: list[dict[str, object]] = []

    def history(layout: P.BatchLayout, validated):
        present = launched.get(layout.key, False)
        token = "1" * 32
        marker = {token: object()} if present else {}
        return {
            "manifest": B._manifest(validated.jobs),
            "starts": marker,
            "reports": marker,
        }

    def complete(layout: P.BatchLayout, _validated, _history):
        if not launched.get(layout.key, False):
            raise ValueError("synthetic launch is incomplete")
        token = "1" * 32
        return {
            "token": token,
            "start_path": layout.output_root / "synthetic-start.json",
            "start_copy_path": layout.sync_root / "synthetic-start.json",
            "start_sha256": "d" * 64,
            "report_path": layout.output_root / "synthetic-report.json",
            "report_copy_path": layout.sync_root / "synthetic-report.json",
            "report_sha256": "e" * 64,
            "executed": layout.fit_count,
            "resumed": 0,
            "synced": layout.fit_count,
        }

    def launch(**kwargs):
        layout = next(
            item
            for item in (P.EXP2B, P.SWEEP_002)
            if item.output_root == kwargs["output_root"]
        )
        # This assertion is the central control-before-blocking invariant.
        control = P._load_receipt(P._control_name(layout))
        assert control["status"] == "armed_before_blocking_launch"
        assert kwargs["attempt_timeout_seconds"] == 3600.0
        calls.append(dict(kwargs))
        launched[layout.key] = True
        return {"status": "complete"}

    monkeypatch.setattr(P, "_history", history)
    monkeypatch.setattr(P, "_validated_complete_report", complete)
    monkeypatch.setattr(P.Launch, "launch_week8", launch)
    return launched, calls


def test_production_names_order_counts_route_and_shared_lease_are_fixed():
    assert P.PREPARATION_ROOT.name == f"week8-baseline-preparation-{P.ATTEMPT}"
    assert tuple(P.BATCHES) == ("exp2b", "sweep-002")
    assert (P.EXP2B.fit_count, P.EXP2B.model_count) == (125, 625)
    assert (P.SWEEP_002.fit_count, P.SWEEP_002.model_count) == (3, 15)
    assert P.ATTEMPT_TIMEOUT_SECONDS == 3600.0
    assert P.MINIMUM_FREE_BYTES == 8_589_934_592
    assert (
        P.COMMON_CONTROL_DIRECTORY
        == P.Preflight.COMMON_CONTROL_DIRECTORY
        == "week7-production-control"
    )
    assert P.COMMON_LEASE_NAME == P.Launch.WEEK8_LEASE_NAME == "week7-production"
    assert (P.C.CONFIRMATORY_DEVICE, P.C.CONFIRMATORY_THREADS) == ("cpu", 4)
    assert P.C.CONFIRMATORY_INTEROP_THREADS == 4
    assert P.EXP2B.monitor_root.name.startswith("week8-monitor-exp2b-")
    assert P.SWEEP_002.monitor_root.name.startswith("week8-monitor-sweep-002-")


def test_prepare_publishes_independent_plan_and_receipt(prepared):
    plan, copied = P._plan_paths()
    assert plan.read_bytes() == copied.read_bytes()
    assert not os.path.samefile(plan, copied)
    receipt = P._load_prepare()
    assert receipt["payload"]["plan"]["sha256"] == sha256_file(plan)
    assert receipt["payload"]["counts"]["total"] == {"fits": 128, "models": 640}
    assert receipt["payload"]["route"]["gpu_used"] is False
    original, peer = P._receipt_paths("prepare")
    assert original.read_bytes() == peer.read_bytes()
    assert not os.path.samefile(original, peer)


def test_prepare_refuses_wrong_commit_and_partial_existing_root(
    fixed_workspace, monkeypatch
):
    with pytest.raises(ValueError, match="differs"):
        P.prepare(expected_git_commit="d" * 40)
    P.PREPARATION_ROOT.mkdir()
    with pytest.raises(ValueError, match="preexisting"):
        P.prepare(expected_git_commit=COMMIT)


def test_prepare_copy_divergence_is_detected(prepared):
    _plan, copied = P._plan_paths()
    copied.write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="diverge|differ"):
        P._load_prepare()


def test_exp2b_preflight_uses_only_fixed_resources(preflight_boundary):
    _root, layout, _sweep, calls = _ready_exp2b(preflight_boundary)
    assert len(calls) == 1
    assert calls[0] == {
        "plan_path": P._plan_paths()[0],
        "batch_key": "exp2b",
        "preflight_dir": layout.preflight_root,
        "output_root": layout.output_root,
        "staging_root": layout.staging_root,
        "sync_root": layout.sync_root,
        "sync_destination_identity": layout.sync_root.name,
        "minimum_free_bytes": 8_589_934_592,
    }
    receipt, validated = P._load_preflight(layout)
    assert receipt["payload"]["fit_count"] == len(validated.jobs) == 125
    assert receipt["payload"]["model_count"] == 625
    assert receipt["payload"]["attempt_timeout_seconds"] == 3600.0


def test_partial_batch_layout_refuses_before_low_level_call(
    prepared, monkeypatch
):
    _root, layout, _sweep = prepared
    layout.preflight_root.mkdir()
    called = False

    def run(**_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(P.Preflight, "run_week8_preflight", run)
    with pytest.raises(ValueError, match="preexisting or partial"):
        P.preflight_exp2b()
    assert called is False


@pytest.mark.parametrize(
    "partial_state",
    ["empty_batch", "manifest_only", "event_only", "empty_report_history"],
)
def test_post_preflight_partial_state_before_launch_start_never_reaches_launcher(
    preflight_boundary, monkeypatch, partial_state
):
    _root, layout, _sweep, _calls = _ready_exp2b(preflight_boundary)
    _receipt, validated = P._load_preflight(layout)
    manifest = B._manifest(validated.jobs)
    if partial_state == "empty_report_history":
        (layout.output_root / P.Launch.WEEK8_REPORT_DIRECTORY).mkdir()
        (layout.sync_root / P.Launch.WEEK8_REPORT_DIRECTORY).mkdir()
    else:
        local = layout.output_root / manifest["batch_id"]
        copied = layout.sync_root / manifest["batch_id"]
        local.mkdir()
        copied.mkdir()
        if partial_state == "manifest_only":
            atomic_write_json(local / B.MANIFEST_FILE, manifest)
            atomic_write_json(copied / B.MANIFEST_FILE, manifest)
        elif partial_state == "event_only":
            (local / B.EVENTS_FILE).write_bytes(b"")
            (copied / B.EVENTS_FILE).write_bytes(b"")

    called = False

    def forbidden(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("lower launch must not see preserved partial state")

    monkeypatch.setattr(P.Launch, "launch_week8", forbidden)
    with pytest.raises(ValueError, match="preserved partial state before any launch-start"):
        P.launch_exp2b()
    assert called is False
    assert not any(os.path.lexists(path) for path in P._receipt_paths(P._control_name(layout)))


def test_sweep_preflight_is_closed_until_complete_exp2b_report(
    preflight_boundary, monkeypatch
):
    _root, _exp2b, sweep, calls = preflight_boundary
    with pytest.raises(ValueError):
        P.preflight_sweep_002()
    assert not any(os.path.lexists(path) for path in P._batch_roots(sweep).values())
    assert calls == []
    monkeypatch.setattr(P, "_require_complete", lambda layout: {"status": "complete"})
    result = P.preflight_sweep_002()
    assert result["status"] == "ready"
    assert calls[0]["batch_key"] == "sweep-002"


def test_launch_control_predates_blocking_call_and_completion_is_sha_bound(
    preflight_boundary, monkeypatch
):
    _root, layout, _sweep, _calls = _ready_exp2b(preflight_boundary)
    _launched, calls = _fake_launch_history(monkeypatch)
    result = P.launch_exp2b()
    assert result == {
        "command": "launch-exp2b",
        "status": "complete",
        "report_sha256": "e" * 64,
        "start_sha256": "d" * 64,
        "fit_count": 125,
        "model_count": 625,
        "gpu_used": False,
        "automatic_retry_performed": False,
    }
    assert len(calls) == 1
    assert calls[0] == {
        "preflight_report": layout.preflight_root / P.Preflight.WEEK8_PREFLIGHT_FILE,
        "output_root": layout.output_root,
        "sync_root": layout.sync_root,
        "attempt_timeout_seconds": 3600.0,
    }
    completion = P._require_complete(layout)
    assert completion["payload"]["accounting"] == {
        "fits": 125,
        "models": 625,
        "executed": 125,
        "resumed": 0,
        "synced": 125,
        "failed": 0,
        "sync_failed": 0,
    }


def test_second_launch_call_never_retries_a_complete_history(
    preflight_boundary, monkeypatch
):
    _ready_exp2b(preflight_boundary)
    _launched, calls = _fake_launch_history(monkeypatch)
    P.launch_exp2b()
    P.launch_exp2b()
    assert len(calls) == 1


def test_started_history_without_complete_report_never_relaunches(
    preflight_boundary, monkeypatch
):
    _ready_exp2b(preflight_boundary)
    _arm_with_empty_history(monkeypatch)
    token = "3" * 32
    monkeypatch.setattr(
        P,
        "_history",
        lambda layout, validated: {
            "manifest": B._manifest(validated.jobs),
            "starts": {token: object()},
            "reports": {},
        },
    )
    called = False

    def forbidden(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("started history may only recover a complete report")

    monkeypatch.setattr(P.Launch, "launch_week8", forbidden)
    with pytest.raises(ValueError, match="single complete launch/report history"):
        P.launch_exp2b()
    assert called is False


def test_launch_refuses_partial_control_copies(preflight_boundary):
    _ready_exp2b(preflight_boundary)
    original, copied = P._receipt_paths(P._control_name(P.EXP2B))
    original.parent.mkdir(exist_ok=True)
    atomic_write_json(original, {"partial": True})
    assert not copied.exists()
    with pytest.raises(ValueError, match="partial"):
        P.launch_exp2b()


@pytest.mark.parametrize(
    ("executed", "resumed", "match"),
    [
        (-1, 126, "negative"),
        (124, 1, "partial, failed, or divergent"),
    ],
)
def test_complete_report_requires_exact_nonnegative_attempt_001_accounting(
    preflight_boundary, monkeypatch, executed, resumed, match
):
    _root, layout, _sweep, _calls = _ready_exp2b(preflight_boundary)
    _receipt, validated = P._load_preflight(layout)
    token = "4" * 32
    start_path = layout.output_root / "accounting-start.json"
    start_copy = layout.sync_root / "accounting-start.json"
    start = {"lease": {"token": token}}
    atomic_write_json(start_path, start)
    atomic_write_json(start_copy, start)
    start_sha = sha256_file(start_path)
    released_path = str(layout.output_root / "released-lease.json")
    report = {
        "week8_launch_schema_version": P.Launch.WEEK8_LAUNCH_SCHEMA_VERSION,
        "status": "complete",
        "finished_at": P.Monitor.M._utc_now(),
        "launch_performed": True,
        "batch_key": layout.key,
        "preflight": {
            "path": str(validated.report_path),
            "sha256": validated.report_sha256,
            "git_commit": validated.git_commit,
        },
        "start": {
            "local_path": str(start_path),
            "durable_path": str(start_copy),
            "sha256": start_sha,
            "record": start,
        },
        "failure": None,
        "batch": {
            "batch_id": B._manifest(validated.jobs)["batch_id"],
            "total": layout.fit_count,
            "executed": executed,
            "resumed": resumed,
            "synced": layout.fit_count,
            "failed": 0,
            "sync_failed": 0,
            "complete": True,
        },
        "scientific_analysis_performed": False,
        "released_lease": {"token": token, "path": released_path},
    }
    report_path = layout.output_root / "accounting-report.json"
    report_copy = layout.sync_root / "accounting-report.json"
    atomic_write_json(report_path, report)
    atomic_write_json(report_copy, report)
    monkeypatch.setattr(
        P.Monitor,
        "_load_launch_start",
        lambda _path: (start_path, start, {}),
    )
    monkeypatch.setattr(
        P.Monitor,
        "_lease_evidence_for_start",
        lambda _start: {"path": released_path, "state": "released"},
    )
    history = {
        "manifest": B._manifest(validated.jobs),
        "starts": {token: (start_path, start_copy, start_sha)},
        "reports": {
            token: (
                report_path,
                report_copy,
                sha256_file(report_path),
            )
        },
    }
    with pytest.raises(ValueError, match=match):
        P._validated_complete_report(layout, validated, history)


def _arm_with_empty_history(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        P,
        "_history",
        lambda layout, validated: {
            "manifest": B._manifest(validated.jobs),
            "starts": {},
            "reports": {},
        },
    )
    return P._arm(P.EXP2B)


def test_monitor_is_safe_during_launch_and_copies_only_operational_inventory(
    preflight_boundary, monkeypatch
):
    _root, layout, _sweep, _calls = _ready_exp2b(preflight_boundary)
    _arm_with_empty_history(monkeypatch)
    start = layout.output_root / "synthetic-start.json"
    atomic_write_json(start, {"operational": "start"})
    token = "2" * 32
    monkeypatch.setattr(
        P,
        "_history",
        lambda _layout, validated: {
            "manifest": B._manifest(validated.jobs),
            "starts": {token: (start, start, "f" * 64)},
            "reports": {},
        },
    )
    calls = []

    def snapshot(*, launch_start_receipt: Path, snapshot_path: Path):
        calls.append((launch_start_receipt, snapshot_path))
        document = {
            "week8_monitor_schema_version": P.Monitor.WEEK8_MONITOR_SCHEMA_VERSION,
            "batch": {"batch_key": "exp2b", "job_count": 125},
            "status": "in_progress",
            "counts": {
                "started": 17,
                "completed": 17,
                "resumed": 0,
                "synced": 17,
                "outstanding": 108,
                "failed_events": 0,
                "sync_failed_events": 0,
            },
            "scientific_analysis": {
                "performed": False,
                "outcomes": None,
                "labels": None,
                "h2_verdict": None,
            },
        }
        document["snapshot_id"] = P.Monitor.M._canonical_digest(document)
        atomic_write_json(snapshot_path, document)
        return document

    monkeypatch.setattr(P.Monitor, "snapshot_week8_batch", snapshot)
    monkeypatch.setattr(P.Monitor, "validate_week8_monitor_snapshot", read_json)
    result = P.monitor_exp2b()
    assert result["status"] == "in_progress"
    assert (result["synced"], result["remaining"]) == (17, 108)
    assert set(result) == {
        "command",
        "status",
        "snapshot_sha256",
        "fit_count",
        "synced",
        "remaining",
        "gpu_used",
    }
    first = layout.monitor_root / "snapshot-000001.json"
    copied = layout.monitor_copy_root / first.name
    assert calls == [(start, first)]
    assert first.read_bytes() == copied.read_bytes()
    assert not os.path.samefile(first, copied)
    P.monitor_exp2b()
    assert (layout.monitor_root / "snapshot-000002.json").is_file()


def test_monitor_before_start_is_outcome_blind_and_writes_nothing(
    preflight_boundary, monkeypatch
):
    _root, layout, _sweep, _calls = _ready_exp2b(preflight_boundary)
    _arm_with_empty_history(monkeypatch)
    result = P.monitor_exp2b()
    assert result == {
        "command": "monitor-exp2b",
        "status": "awaiting_start",
        "fit_count": 125,
        "synced": 0,
        "remaining": 125,
        "gpu_used": False,
    }
    assert not layout.monitor_root.exists()


def test_monitor_root_and_copy_history_must_be_complete_and_contiguous(
    preflight_boundary, monkeypatch
):
    _root, layout, _sweep, _calls = _ready_exp2b(preflight_boundary)
    _arm_with_empty_history(monkeypatch)
    layout.monitor_root.mkdir()
    with pytest.raises(ValueError, match="partial"):
        P._ensure_monitor_roots(layout)
    layout.monitor_copy_root.mkdir()
    atomic_write_json(layout.monitor_root / "snapshot-000002.json", {})
    atomic_write_json(layout.monitor_copy_root / "snapshot-000002.json", {})
    with pytest.raises(ValueError, match="snapshot|schema|contiguous"):
        P._monitor_inventory(layout)


def test_paired_history_refuses_missing_copy_unknown_name_and_divergent_bytes(
    tmp_path: Path,
):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    with pytest.raises(ValueError, match="diverged"):
        P._paired_json_inventory(left, right, what="synthetic", required=False)
    right.mkdir()
    atomic_write_json(left / "not-a-token.json", {})
    atomic_write_json(right / "not-a-token.json", {})
    with pytest.raises(ValueError, match="noncanonical"):
        P._paired_json_inventory(left, right, what="synthetic", required=False)


def test_public_functions_and_cli_expose_no_result_changing_overrides():
    assert set(inspect.signature(P.prepare).parameters) == {"expected_git_commit"}
    for function in (
        P.preflight_exp2b,
        P.launch_exp2b,
        P.monitor_exp2b,
        P.preflight_sweep_002,
        P.launch_sweep_002,
        P.monitor_sweep_002,
    ):
        assert inspect.signature(function).parameters == {}
    forbidden = (
        "--path",
        "--device",
        "--jobs",
        "--seed",
        "--attempt-timeout-seconds",
        "--minimum-free-bytes",
    )
    for option in forbidden:
        with pytest.raises(SystemExit):
            P._parser().parse_args(["launch-exp2b", option, "x"])


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="host has no symlink API")
def test_reparse_or_symlink_fixed_root_is_never_accepted(
    prepared, monkeypatch, tmp_path
):
    _root, layout, _sweep = prepared
    target = tmp_path / "target"
    target.mkdir()
    try:
        os.symlink(target, layout.preflight_root, target_is_directory=True)
    except OSError:
        pytest.skip("host policy does not permit test symlinks")
    with pytest.raises(ValueError, match="preexisting or partial"):
        P._create_batch_roots(layout)


def test_main_prints_only_the_sanitized_operational_result(monkeypatch, capsys):
    monkeypatch.setattr(
        P,
        "monitor_exp2b",
        lambda: {
            "command": "monitor-exp2b",
            "status": "in_progress",
            "synced": 1,
            "remaining": 124,
            "gpu_used": False,
        },
    )
    assert P.main(["monitor-exp2b"]) == 0
    output = capsys.readouterr().out
    assert "outcome" not in output.lower()
    assert "label" not in output.lower()
    assert "effect" not in output.lower()
    assert '"gpu_used": false' in output


def test_main_hashes_exception_text_and_emits_no_traceback(monkeypatch, capsys):
    secret = "SECRET_OBSERVED_LABEL_AND_RAW_WORKER_MESSAGE"

    def fail():
        raise ValueError(secret)

    monkeypatch.setattr(P, "monitor_exp2b", fail)
    assert P.main(["monitor-exp2b"]) == 1
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document == P._operational_failure("monitor-exp2b", ValueError(secret))
    assert set(document) == {
        "command",
        "status",
        "failure_type",
        "failure_sha256",
    }
    combined = captured.out + captured.err
    assert secret not in combined
    assert "traceback" not in combined.lower()


@pytest.mark.parametrize("exception", [KeyboardInterrupt("stop"), SystemExit(9)])
def test_main_does_not_catch_process_control_exceptions(
    monkeypatch, capsys, exception
):
    def stop():
        raise exception

    monkeypatch.setattr(P, "monitor_exp2b", stop)
    with pytest.raises(type(exception)):
        P.main(["monitor-exp2b"])
    captured = capsys.readouterr()
    assert captured.out == ""
