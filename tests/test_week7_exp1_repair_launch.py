"""Synthetic production-boundary tests; no real payloads or model training."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import platform
import stat
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import week7_exp1_repair_launch as L
from bu.experiments import week7_exp1_repairs as W
from bu.experiments.supervisor import AttemptOutcome, LeaseConflictError

from test_week7_exp1_repairs import (
    COMMIT, checkpoint, environment, old_sources, workspace, _next_checkpoint,
)
from test_repair_timing import fake_benchmark


@pytest.fixture
def cache_source_enumeration(monkeypatch):
    """Consumer tests cache only immutable source-derived snapshots, not outputs."""
    jobs, plan = W.registered_exp1_jobs(), W.build_exp1_repair_plan()
    monkeypatch.setattr(W, "registered_exp1_jobs", lambda: jobs)
    monkeypatch.setattr(W, "build_exp1_repair_plan", lambda: copy.deepcopy(plan))


def _validated(cp):
    return L.ValidatedExp1Preflight(cp["preflight"], sha256_file(cp["preflight"]), {
        "binding_sha256": "e" * 64,
        "attempt_timeout_seconds": 17.0,
        "inputs": {"reuse_ledger": {"path": str(cp["ledger"])}}},
        {name: cp["workspace"] / name for name in ("output", "staging", "sync")}, COMMIT)


@pytest.fixture
def publication_double(monkeypatch):
    """Supervisor/fit loader are doubles; copy implementation and receipts are real."""
    calls = []
    def install(cp, *, mode="success"):
        original_publish = L.B._publish_job_tree
        def publish(source, destination):
            original_publish(source, destination)
            commit, verified = cp["store"].entries[Path(source)]
            cp["store"].entries[Path(destination)] = (commit, replace(verified, fit_dir=Path(destination)))
        monkeypatch.setattr(L.B, "_publish_job_tree", publish)
        def isolated(callback, *, root, staging_root, job_id, payload, timeout_seconds):
            assert callback is W._fit_worker
            assert Path(staging_root) == cp["workspace"] / "staging"
            assert timeout_seconds == 17.0
            assert payload["expected_git_commit"] == COMMIT
            job = W._new_job(job_id)
            assert payload["job"] == job.as_record()
            calls.append(job_id)
            token = hashlib.sha256(job_id.encode()).hexdigest()[:32]
            if mode == "timeout":
                quarantine = Path(staging_root) / "quarantine" / f"{job_id}.{token}"
                quarantine.mkdir(parents=True)
                atomic_write_json(quarantine / "attempt_receipt.json", {"status": "timeout"})
                return AttemptOutcome(job_id, token, "timeout", quarantine, None, -1)
            path = Path(root) / "jobs" / job_id
            verified = cp["store"].persist(path, job, COMMIT)
            start, ledger, roots = W._load_start(payload["checkpoint_path"],
                expected_sha256=payload["checkpoint_sha256"], expected_git_commit=COMMIT)
            binding = None
            if job.arm != "baseline":
                _, binding = W._baseline(job, ledger, roots, COMMIT, start)
            atomic_write_json(path / "job_result.json", W._result_record(job, verified,
                commit=COMMIT, checkpoint_digest=start["checkpoint_digest"],
                execution_context_digest=start["execution_context_digest"], binding=binding))
            return AttemptOutcome(job_id, token, "success", path, path, 0, published=True)
        monkeypatch.setattr(L, "run_isolated_attempt", isolated)
        return calls
    return install


def _run(cp, job, events):
    return L._run_one_job(job, validated=_validated(cp), checkpoint_path=cp["path"],
                          start=cp["doc"], events=events)


def test_fixed_supervisor_and_real_independent_sync_then_no_second_execution(
        checkpoint, publication_double, cache_source_enumeration):
    cp = checkpoint
    calls = publication_double(cp)
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    events = L._load_events(_validated(cp).roots, cp["doc"])
    assert _run(cp, job, events) == "executed"
    assert calls == [job.job_id]
    assert [e["kind"] for e in events] == ["attempt_started", "job_synced"]
    source = cp["workspace"] / "output" / "jobs" / job.job_id
    durable = cp["workspace"] / "sync" / "jobs" / job.job_id
    assert W.B._copy_evidence_digest(source, durable) == events[-1]["data"]["copy_evidence_digest"]
    assert _run(cp, job, events) == "resumed"
    assert calls == [job.job_id]
    assert len(events) == 2


def test_old_seed_repair_runs_with_historical_binding_not_retrained_baseline(
        checkpoint, publication_double, cache_source_enumeration):
    cp = checkpoint
    calls = publication_double(cp)
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "data_repair" and j.stage == "exp3_repairs")
    events = L._load_events(_validated(cp).roots, cp["doc"])
    assert _run(cp, job, events) == "executed"
    assert calls == [job.job_id]
    result = read_json(cp["workspace"] / "output" / "jobs" / job.job_id / "job_result.json")
    assert result["baseline_source"]["expected_git_commit"] == W.HISTORICAL_COMMIT
    assert not any(j.arm == "baseline" and j.job_id in calls for j in W.historical_exp1_jobs())


def test_sync_failure_then_new_lease_recovers_only_copy_without_rewriting_fit(
        checkpoint, publication_double, cache_source_enumeration, monkeypatch):
    cp = checkpoint
    calls = publication_double(cp)
    normal = L.B._publish_job_tree
    def fail_copy(source, destination):
        raise ValueError("synthetic transport interruption")
    monkeypatch.setattr(L.B, "_publish_job_tree", fail_copy)
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    events = L._load_events(_validated(cp).roots, cp["doc"])
    with pytest.raises(ValueError, match="transport interruption"):
        _run(cp, job, events)
    result_path = cp["workspace"] / "output" / "jobs" / job.job_id / "job_result.json"
    before = result_path.read_bytes(), result_path.stat().st_mtime_ns
    assert [e["kind"] for e in events] == ["attempt_started", "sync_pending"]
    newer = _next_checkpoint(cp)
    monkeypatch.setattr(L.B, "_publish_job_tree", normal)
    try:
        recovered = L._load_events(_validated(newer).roots, newer["doc"])
        assert _run(newer, job, recovered) == "resumed"
        assert calls == [job.job_id]
        assert (result_path.read_bytes(), result_path.stat().st_mtime_ns) == before
        assert [e["kind"] for e in recovered] == ["attempt_started", "sync_pending", "job_synced"]
    finally:
        newer["lease"].release()


def test_failed_attempt_is_preserved_and_never_automatically_retried(
        checkpoint, publication_double, cache_source_enumeration):
    cp = checkpoint
    calls = publication_double(cp, mode="timeout")
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    events = L._load_events(_validated(cp).roots, cp["doc"])
    with pytest.raises(ValueError, match="exact successful"):
        _run(cp, job, events)
    assert list((cp["workspace"] / "staging" / "quarantine").rglob("attempt_receipt.json"))
    newer = _next_checkpoint(cp)
    try:
        recovered = L._load_events(_validated(newer).roots, newer["doc"])
        with pytest.raises(ValueError, match="prior failed attempt"):
            _run(newer, job, recovered)
        assert calls == [job.job_id]
    finally:
        newer["lease"].release()


@pytest.mark.parametrize("prior", ["started", "staging", "quarantine", "durable_only"])
def test_unknown_or_partial_prior_work_never_creates_another_attempt(
        checkpoint, publication_double, cache_source_enumeration, prior):
    cp = checkpoint
    calls = publication_double(cp)
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    roots = _validated(cp).roots
    events = L._load_events(roots, cp["doc"])
    if prior == "started":
        L._append_event(roots, cp["doc"], events, kind="attempt_started", job_id=job.job_id,
                        data={"checkpoint_digest": cp["doc"]["checkpoint_digest"]})
    elif prior == "durable_only":
        (roots["sync"] / "jobs" / job.job_id).mkdir(parents=True)
    else:
        (roots["staging"] / prior / f"{job.job_id}.{'a' * 32}").mkdir(parents=True)
    with pytest.raises(ValueError, match="prior|retraining"):
        _run(cp, job, events)
    assert calls == []


def test_durable_only_event_tail_is_restored_but_existing_different_bytes_refuse(
        checkpoint, cache_source_enumeration):
    cp = checkpoint
    roots = _validated(cp).roots
    events = L._load_events(roots, cp["doc"])
    job = W.new_exp1_repair_jobs()[0]
    L._append_event(roots, cp["doc"], events, kind="attempt_started", job_id=job.job_id,
                    data={"checkpoint_digest": cp["doc"]["checkpoint_digest"]})
    local, durable = L._event_directories(roots)
    (local / "000000.json").unlink()
    assert L._load_events(roots, cp["doc"]) == events
    assert not os.path.samefile(local / "000000.json", durable / "000000.json")
    (local / "000000.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        L._load_events(roots, cp["doc"])


@pytest.mark.parametrize("mutation", ["gap", "context", "duplicate_start", "false_complete", "synced_without_start"])
def test_event_forgery_cannot_change_inventory_or_retry_policy(checkpoint, cache_source_enumeration, mutation):
    cp = checkpoint
    roots = _validated(cp).roots
    events = L._load_events(roots, cp["doc"])
    job = W.new_exp1_repair_jobs()[0]
    kind, data = "attempt_started", {"checkpoint_digest": cp["doc"]["checkpoint_digest"]}
    if mutation == "false_complete":
        kind, data = "complete", {"synced_physical_fits": 474, "historical_sources_reverified": 102}
    elif mutation == "synced_without_start":
        kind, data = "job_synced", {key: "a" * 64 for key in ("execution_digest", "source_tree_digest", "copy_evidence_digest")}
    L._append_event(roots, cp["doc"], events, kind=kind, job_id=None if kind == "complete" else job.job_id, data=data)
    if mutation == "duplicate_start":
        L._append_event(roots, cp["doc"], events, kind=kind, job_id=job.job_id, data=data)
    elif mutation == "gap":
        for directory in L._event_directories(roots):
            (directory / "000000.json").rename(directory / "000001.json")
    elif mutation == "context":
        row = {**events[0], "execution_context_digest": "d" * 64}
        row = W._seal({k: v for k, v in row.items() if k != "event_digest"}, "event_digest")
        for directory in L._event_directories(roots):
            (directory / "000000.json").write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError):
        L._load_events(roots, cp["doc"])


def test_public_launch_contends_on_shared_week7_lease(checkpoint, monkeypatch):
    cp = checkpoint
    monkeypatch.setattr(L, "validate_exp1_repair_preflight", lambda *a, **k: _validated(cp))
    with pytest.raises(LeaseConflictError):
        L.launch_exp1_repairs(preflight_report=cp["path"], output_root=cp["workspace"] / "output",
                              sync_root=cp["workspace"] / "sync", expected_git_commit=COMMIT)


@pytest.mark.parametrize("target", ["leases", "history", "active", "transition"])
def test_reparse_lease_namespace_is_refused_before_acquire(checkpoint, monkeypatch, target):
    """Simulate Windows reparse metadata; never create an actual junction."""
    cp = checkpoint
    lease_dir = W.COMMON_LEASE_ROOT / "leases"
    paths = {"leases": lease_dir, "history": lease_dir / "history",
             "active": cp["lease"].path,
             "transition": lease_dir / f".{W.COMMON_LEASE_NAME}.lease-transition.lock"}
    paths["history"].mkdir(exist_ok=True)
    original = Path.lstat
    def marked_attributes(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == paths[target]:
            return SimpleNamespace(st_mode=info.st_mode,
                st_file_attributes=getattr(info, "st_file_attributes", 0) | stat.FILE_ATTRIBUTE_REPARSE_POINT)
        return info
    monkeypatch.setattr(Path, "lstat", marked_attributes)
    monkeypatch.setattr(L, "validate_exp1_repair_preflight", lambda *a, **k: _validated(cp))
    acquired = []
    def forbidden(*args, **kwargs):
        acquired.append(True)
        pytest.fail("supervisor reached a linked lease namespace before raw-path validation")
    monkeypatch.setattr(L, "acquire_batch_lease", forbidden)
    with pytest.raises(ValueError, match="link/reparse"):
        L.launch_exp1_repairs(preflight_report=cp["preflight"], output_root=cp["workspace"] / "output",
                              sync_root=cp["workspace"] / "sync", expected_git_commit=COMMIT)
    assert acquired == []


def test_lease_namespace_check_permits_missing_children_without_creating_them(workspace):
    root = W.COMMON_LEASE_ROOT
    assert L._check_lease_namespace() == root
    assert list(root.iterdir()) == []


def test_public_loop_visits_exact474_and_rechecks_sources_before_completion(
        checkpoint, cache_source_enumeration, monkeypatch):
    """Orchestration-only doubles; per-job physical/copy checks tested above."""
    cp = checkpoint
    cp["lease"].release()
    checks, visited = [], []
    def validate(*args, **kwargs):
        checks.append(kwargs)
        return _validated(cp)
    monkeypatch.setattr(L, "validate_exp1_repair_preflight", validate)
    monkeypatch.setattr(W, "reconcile_completed_exp1_job", lambda *a, **k: {"synthetic": True})
    monkeypatch.setattr(L, "_run_one_job", lambda job, **kwargs: visited.append(job.job_id) or "resumed")
    result = L.launch_exp1_repairs(preflight_report=cp["path"], output_root=cp["workspace"] / "output",
                                   sync_root=cp["workspace"] / "sync", expected_git_commit=COMMIT)
    assert visited == [j.job_id for j in W.new_exp1_repair_jobs()]
    assert len(visited) == 474 and len(set(visited)) == 474
    assert len(checks) == 4
    assert result["counts"] == {"executed": 0, "resumed": 474, "synced": 474, "total": 474}
    assert result["status"] == "complete"
    assert Path(result["released_lease"]["history_path"]).is_file()


@pytest.mark.parametrize("drift_call", [2, 4])
def test_public_launch_retains_original_preflight_pin_under_lease_and_at_completion(
        checkpoint, cache_source_enumeration, monkeypatch, drift_call):
    cp = checkpoint
    cp["lease"].release()
    original = _validated(cp)
    calls, visited = [], []
    def validate(*args, **kwargs):
        calls.append(None)
        return replace(original, report_sha256="d" * 64) if len(calls) == drift_call else original
    monkeypatch.setattr(L, "validate_exp1_repair_preflight", validate)
    monkeypatch.setattr(L, "_run_one_job", lambda job, **kwargs: visited.append(job.job_id) or "resumed")
    monkeypatch.setattr(W, "reconcile_completed_exp1_job", lambda *a, **k: {"synthetic": True})
    with pytest.raises(ValueError, match="original launch SHA256"):
        L.launch_exp1_repairs(preflight_report=cp["preflight"], output_root=cp["workspace"] / "output",
                              sync_root=cp["workspace"] / "sync", expected_git_commit=COMMIT)
    assert len(visited) == (0 if drift_call == 2 else 474)
    path = next((cp["workspace"] / "output" / L.REPORT_DIRECTORY).glob("*.json"))
    report = read_json(path)
    assert report["status"] == "incomplete"
    assert report["preflight"]["sha256"] == original.report_sha256
    for event in (cp["workspace"] / "output" / L.EVENT_DIRECTORY).glob("*.json"):
        assert read_json(event)["kind"] != "complete"


def test_public_failure_releases_only_own_lease_and_preserves_durable_report(
        checkpoint, cache_source_enumeration, monkeypatch):
    cp = checkpoint
    cp["lease"].release()
    monkeypatch.setattr(L, "validate_exp1_repair_preflight", lambda *a, **k: _validated(cp))
    def broken(*args, **kwargs):
        raise ValueError("synthetic failed first attempt")
    monkeypatch.setattr(L, "_run_one_job", broken)
    with pytest.raises(ValueError, match="synthetic failed"):
        L.launch_exp1_repairs(preflight_report=cp["path"], output_root=cp["workspace"] / "output",
                              sync_root=cp["workspace"] / "sync", expected_git_commit=COMMIT)
    reports = list((cp["workspace"] / "output" / L.REPORT_DIRECTORY).glob("*.json"))
    assert len(reports) == 1
    report = read_json(reports[0])
    assert report["status"] == "incomplete"
    assert report["counts"]["synced"] == 0
    assert Path(report["released_lease"]["history_path"]).is_file()
    W._same_file_copy(reports[0], cp["workspace"] / "sync" / L.REPORT_DIRECTORY / reports[0].name)


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, SystemExit])
def test_public_interrupt_is_recorded_truthfully_before_returning_control(
        checkpoint, cache_source_enumeration, monkeypatch, interrupt):
    cp = checkpoint
    cp["lease"].release()
    monkeypatch.setattr(L, "validate_exp1_repair_preflight", lambda *a, **k: _validated(cp))
    def interrupted(*args, **kwargs):
        raise interrupt("synthetic controlled interruption")
    monkeypatch.setattr(L, "_run_one_job", interrupted)
    with pytest.raises(interrupt):
        L.launch_exp1_repairs(preflight_report=cp["path"], output_root=cp["workspace"] / "output",
                              sync_root=cp["workspace"] / "sync", expected_git_commit=COMMIT)
    path = next((cp["workspace"] / "output" / L.REPORT_DIRECTORY).glob("*.json"))
    report = read_json(path)
    assert report["status"] == "interrupted"
    assert report["failure"]["type"] == interrupt.__name__
    assert report["counts"]["synced"] == 0
    assert Path(report["released_lease"]["history_path"]).is_file()
    W._same_file_copy(path, cp["workspace"] / "sync" / L.REPORT_DIRECTORY / path.name)


@pytest.mark.parametrize("interrupted", [False, True])
def test_unconfirmed_release_retains_lease_and_records_incomplete_or_interrupted_report(
        checkpoint, cache_source_enumeration, monkeypatch, interrupted):
    cp = checkpoint
    cp["lease"].release()
    monkeypatch.setattr(L, "validate_exp1_repair_preflight", lambda *a, **k: _validated(cp))
    actual_acquire, actual_release = L.acquire_batch_lease, W.BatchLease.release
    held = []
    def acquire(*args, **kwargs):
        lease = actual_acquire(*args, **kwargs)
        held.append(lease)
        return lease
    def cannot_release(lease):
        if lease in held:
            raise RuntimeError("synthetic child cleanup was not confirmed")
        return actual_release(lease)
    def run(*args, **kwargs):
        if interrupted:
            raise KeyboardInterrupt("synthetic interrupted child")
        return "resumed"
    monkeypatch.setattr(L, "acquire_batch_lease", acquire)
    monkeypatch.setattr(W.BatchLease, "release", cannot_release)
    monkeypatch.setattr(L, "_run_one_job", run)
    monkeypatch.setattr(W, "reconcile_completed_exp1_job", lambda *a, **k: {"synthetic": True})
    try:
        with pytest.raises(RuntimeError, match="cleanup was not confirmed"):
            L.launch_exp1_repairs(preflight_report=cp["preflight"], output_root=cp["workspace"] / "output",
                                  sync_root=cp["workspace"] / "sync", expected_git_commit=COMMIT)
        assert len(held) == 1 and held[0].path.is_file() and not held[0]._released
        path = next((cp["workspace"] / "output" / L.REPORT_DIRECTORY).glob("*.json"))
        report = read_json(path)
        assert report["status"] == ("interrupted" if interrupted else "incomplete")
        assert report["released_lease"] is None
        assert report["lease_release_failure"]["automatic_recovery_allowed"] is False
        assert report["lease_release_failure"]["token"] == held[0].token
        assert report["failure"] == ({"type": "KeyboardInterrupt", "message": "synthetic interrupted child"} if interrupted else None)
        W._same_file_copy(path, cp["workspace"] / "sync" / L.REPORT_DIRECTORY / path.name)
    finally:
        for lease in held:
            actual_release(lease)  # Only test teardown, never production recovery.


def test_validly_stored_repair_timing_cannot_stand_in_for_baseline_timing(workspace, monkeypatch):
    monkeypatch.setattr(L.RT, "PROJECT_ROOT", workspace)
    inventory = L.RT.repair_inventory("e1_repairs")
    benchmark = fake_benchmark(inventory["groups"][0], inventory)
    record = L.RT.build_timing_record([benchmark], "e1_repairs")
    path = L.RT.write_timing_record(workspace / "input" / "wrong-schema-timing.json", record)
    with pytest.raises(ValueError, match="baseline benchmark|repair records"):
        L._baseline_timing(path, sha256_file(path), "a" * 40)


@pytest.fixture
def timing_inputs(workspace, monkeypatch):
    """Preflight lifecycle uses explicit timing-loader doubles, not claimed timings."""
    paths = {name: atomic_write_json(workspace / "input" / f"{name}.json", {"synthetic": name})
             for name in ("repair_timing", "baseline_timing")}
    def repair(path, sha, commit):
        _, pin = L._pinned_file(path, sha, commit)
        return pin, {"model_fits": 384, "total_s": 1234.0, "scope": "e1_repairs"}
    def baseline(path, sha, commit):
        _, pin = L._pinned_file(path, sha, commit)
        return pin, {"physical_fits": 90, "total_s": 2345.0, "synthetic": True}
    monkeypatch.setattr(L, "_repair_timing", repair)
    monkeypatch.setattr(L, "_baseline_timing", baseline)
    return paths


@pytest.fixture
def ready(workspace, old_sources, environment, timing_inputs, cache_source_enumeration):
    preflight = workspace / "preflight"
    preflight.mkdir()
    plan = W.write_exp1_repair_plan(workspace / "input")
    ledger = W.write_exp1_reuse_ledger(workspace / "input")
    kwargs = dict(plan_path=plan, reuse_ledger_path=ledger,
        repair_timing_path=timing_inputs["repair_timing"], repair_timing_sha256=sha256_file(timing_inputs["repair_timing"]),
        repair_timing_expected_git_commit="a" * 40,
        baseline_timing_path=timing_inputs["baseline_timing"], baseline_timing_sha256=sha256_file(timing_inputs["baseline_timing"]),
        baseline_timing_expected_git_commit="a" * 40,
        expected_git_commit=COMMIT, preflight_dir=preflight, output_root=workspace / "output",
        staging_root=workspace / "staging", sync_root=workspace / "sync", attempt_timeout_seconds=17,
        minimum_free_bytes=0, sync_destination_identity="synthetic-independent-mounted-copy")
    report = L.run_exp1_repair_preflight(**kwargs)
    return {"kwargs": kwargs, "report": report, "path": preflight / L.PREFLIGHT_FILE}


def test_preflight_rederives_plan_sources_timing_roots_and_independent_copy(ready, workspace):
    validated = L.validate_exp1_repair_preflight(ready["path"], output_root=workspace / "output",
                                               sync_root=workspace / "sync", expected_git_commit=COMMIT)
    assert validated.report == ready["report"]
    assert validated.report["status"] == "ready"
    assert validated.report["launch_performed"] is False
    assert validated.report["budget"]["new_physical_fits"] == 474
    assert validated.report["common_control_root"] == str(W.COMMON_LEASE_ROOT)
    assert not (workspace / "output" / "jobs").exists()


@pytest.mark.parametrize("mutation", ["schema", "timeout", "budget", "plan", "control", "commit"])
def test_resigned_preflight_semantic_changes_refuse(ready, workspace, mutation):
    report = copy.deepcopy(ready["report"])
    if mutation == "schema":
        report["exp1_repair_preflight_schema_version"] = True
    elif mutation == "timeout":
        report["attempt_timeout_seconds"] = 25.0
    elif mutation == "budget":
        report["budget"]["new_physical_fits"] = 475
    elif mutation == "plan":
        report["plan_digest"] = "a" * 64
    elif mutation == "control":
        report["common_control_root"] = str(workspace / "output")
    else:
        report["environment"]["git_commit"] = W.HISTORICAL_COMMIT
    for path in (ready["path"], workspace / "sync" / L.PREFLIGHT_FILE):
        path.write_bytes(L.L._pretty_json_bytes(report))
    with pytest.raises(ValueError):
        L.validate_exp1_repair_preflight(ready["path"], output_root=workspace / "output",
                                         sync_root=workspace / "sync", expected_git_commit=COMMIT)


def test_current_environment_rechecked_before_supervisor_dispatch(
        checkpoint, publication_double, cache_source_enumeration, monkeypatch):
    cp = checkpoint
    calls = publication_double(cp)
    job = W.new_exp1_repair_jobs()[0]
    events = L._load_events(_validated(cp).roots, cp["doc"])
    def dirty(commit):
        raise ValueError("synthetic dirty Git")
    monkeypatch.setattr(W, "_environment", dirty)
    with pytest.raises(ValueError, match="dirty Git"):
        _run(cp, job, events)
    assert calls == [] and events == []


def test_no_caller_jobs_executor_retry_or_timing_bypass():
    params = set(inspect.signature(L.launch_exp1_repairs).parameters)
    assert params == {"preflight_report", "output_root", "sync_root", "expected_git_commit"}
    assert not {"executor", "sync", "jobs", "retry", "skip_timing", "scale", "stage"} & params


@pytest.mark.parametrize("failure", [None, "missing_group", "wrong_commit", "wrong_host", "wrong_sha"])
@pytest.mark.parametrize("kind", ["repair", "baseline"])
def test_real_timing_readers_require_all_exact_local_cases(workspace, monkeypatch, failure, kind):
    monkeypatch.setattr(L.RT, "PROJECT_ROOT", workspace)
    inventory = L.RT.repair_inventory("e1_repairs") if kind == "repair" else L.RT.baseline_inventory()
    records = [fake_benchmark(g, inventory) for g in inventory["groups"]]
    if kind == "baseline":
        for record in records:
            record["artifact_type"] = "development_e1_baseline_case"
            for trial in (record["warmup"], *record["repetitions"]):
                trial["epochs_run"] = [23, 24, 25, 26, 27]
    current_host = {"platform": platform.platform(), "processor": platform.processor() or platform.machine(),
                    "python": platform.python_version(), "machine": platform.machine(),
                    "hostname": platform.node(), "logical_cpu_count": os.cpu_count()}
    for record in records:
        for env in (record["environment_before"], record["environment_after"]):
            env.update(current_host)
            if failure == "wrong_host":
                env["hostname"] = "different-synthetic-machine"
    if failure == "missing_group":
        records.pop()
    if kind == "repair":
        record = L.RT.build_timing_record(records, "e1_repairs")
        path = L.RT.write_timing_record(workspace / "input" / "timing.json", record)
        loader = L._repair_timing
    else:
        record = L.RT.build_baseline_timing_record(records)
        path = L.RT.write_baseline_timing_record(workspace / "input" / "timing.json", record)
        loader = L._baseline_timing
    sha = "f" * 64 if failure == "wrong_sha" else sha256_file(path)
    commit = "b" * 40 if failure == "wrong_commit" else "a" * 40
    if failure is not None:
        with pytest.raises(ValueError):
            loader(path, sha, commit)
    else:
        pin, projection = loader(path, sha, commit)
        assert pin["expected_git_commit"] == "a" * 40
        assert projection["model_fits"] == (384 if kind == "repair" else 450)
        assert len(projection["contributions"]) == (12 if kind == "repair" else 6)
        if kind == "baseline":
            assert projection["ensemble_jobs"] == 90
