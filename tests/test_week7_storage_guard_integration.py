"""Actual-package storage-boundary integration with wholly synthetic evidence.

No AST extraction, module copies or guard replacement here. The real launchers,
batch engine, storage guard, journals, leases and copy verification run. Source
readers, timing, and supervisor/model production are explicit fixture doubles.
Only pure registered inventories are derived; no collected inputs are rebuilt.
Run AFTER applying both proposals, not against an active production checkout.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import batch as B
from bu.experiments import confirmatory as C
from bu.experiments import fit_evidence as F
from bu.experiments import prefit_storage as G
from bu.experiments import preflight as P
from bu.experiments import week7_exp1_repair_launch as E1
from bu.experiments import week7_exp1_repairs as W
from bu.experiments import week7_launch as WL
from bu.experiments import week7_launch_plan as LP
from bu.experiments import week7_preflight as PF
from bu.experiments import week7_sweep_repair_launch as SR
from bu.experiments.supervisor import AttemptOutcome

from test_batch import result_for
from test_week7_exp1_repairs import (
    COMMIT, SyntheticFits, checkpoint, environment, old_sources, workspace,
)
from test_week7_exp1_repair_launch import publication_double, cache_source_enumeration
from test_week7_launch import case as baseline_case, jobs
from test_week7_sweep_repair_launch import setup as sweep_setup


# Capture real functions at collection, BEFORE any fixture replaces B._run_batch.
REAL_BATCH_ENGINE = B._run_batch
REAL_BATCH_JOBS = PF._batch_jobs
REAL_RECOVER_RESULT = B._recover_result
REAL_DIRECTORY_SYNC = B.sync_to_directory


@pytest.fixture(autouse=True)
def no_real_model_or_process(monkeypatch):
    """Fixture doubles must opt in; a missed replacement must fail, not train."""
    def prohibited(*args, **kwargs):
        pytest.fail("storage integration must not collect, train, or spawn a real worker")
    for owner, name in (
        (C, "collect_pools"), (C, "collect_pools_with_anchors"), (C, "train_ensemble"),
        (B, "run_confirmatory_fit"), (F, "run_confirmatory_fit"),
        (SR.E, "train_ensemble"), (SR.RT, "train_ensemble"),
        (SR.RP, "collect_anchored_repair_pools"),
        (B, "run_isolated_attempt"), (E1, "run_isolated_attempt"),
        (SR, "run_isolated_attempt"),
    ):
        monkeypatch.setattr(owner, name, prohibited)


@pytest.fixture(autouse=True)
def storage_space(monkeypatch):
    """Only the OS observation is simulated; every guard function stays real."""
    state = SimpleNamespace(free=1_000_000, observed=[])
    def usage(path):
        state.observed.append(Path(path))
        return SimpleNamespace(free=state.free)
    monkeypatch.setattr(P.shutil, "disk_usage", usage)
    assert G.shutil is P.shutil
    return state


def _files(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()} if root.exists() else {}


def _assert_absent_attempt(roots, job_id, *, batch_id=None):
    for name in ("output", "sync"):
        root = roots[name] / batch_id if batch_id else roots[name]
        assert not (root / "jobs" / job_id).exists()
    # No supervisor attempt envelope or quarantine may exist for an unstarted fit.
    assert not list(roots["staging"].rglob(f"{job_id}.*"))


def _rewrite_preflight_pair(path, sync_root):
    document = read_json(path)
    assert document["storage"]["minimum_free_bytes"] == 80
    document["storage"]["minimum_free_bytes"] = 0
    raw = PF.L._pretty_json_bytes(document)
    path.write_bytes(raw)
    (sync_root / path.name).write_bytes(raw)


@pytest.mark.parametrize("checkpoint", [80], indirect=True)
@pytest.mark.parametrize("completed", [0, 1], ids=["before-first", "between-jobs"])
@pytest.mark.parametrize("mutation", ["low_space", "resigned_preflight"])
def test_e1_storage_guard_original_pin_and_no_unstarted_attempt(
    checkpoint, publication_double, cache_source_enumeration, storage_space,
    completed, mutation,
):
    cp = checkpoint
    validated = cp["validated"]  # Original object, never a hash recomputed after mutation.
    roots = validated.roots
    assert set(roots) == {"preflight", "output", "staging", "sync"}
    assert validated.report_path.name == E1.PREFLIGHT_FILE
    assert validated.report["storage"]["minimum_free_bytes"] == 80
    assert cp["doc"]["preflight"]["sha256"] == validated.report_sha256
    assert cp["preflight"].read_bytes() == (roots["sync"] / E1.PREFLIGHT_FILE).read_bytes()
    calls = publication_double(cp)
    selected = tuple(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")[:2]
    events = E1._load_events(roots, cp["doc"])
    storage_space.free = 80  # Equality must permit the first synthetic child.

    def run(job):
        return E1._run_one_job(job, validated=validated, checkpoint_path=cp["path"],
                               start=cp["doc"], events=events)

    if completed:
        assert run(selected[0]) == "executed"
    target = selected[completed]
    before = list(events)
    before_events = {name: _files(roots[name] / E1.EVENT_DIRECTORY) for name in ("output", "sync")}
    before_fits = {name: _files(roots[name] / "jobs") for name in ("output", "sync")}
    if mutation == "low_space":
        storage_space.free = 79
        expected = "pre-fit storage: .*below required 80"
    else:
        _rewrite_preflight_pair(cp["preflight"], roots["sync"])
        assert sha256_file(cp["preflight"]) != validated.report_sha256
        # A hypothetical revalidator could accept the new lower floor. This
        # child still owes the original independently held launch digest.
        assert validated.report["storage"]["minimum_free_bytes"] == 80
        expected = "pre-fit storage: preflight changed from the original launch pin"
    with pytest.raises(ValueError, match=expected):
        run(target)
    assert events == before
    assert calls == [j.job_id for j in selected[:completed]]
    assert cp["store"].executions == []
    assert before_events == {name: _files(roots[name] / E1.EVENT_DIRECTORY) for name in ("output", "sync")}
    assert before_fits == {name: _files(roots[name] / "jobs") for name in ("output", "sync")}
    _assert_absent_attempt(roots, target.job_id)


@pytest.mark.parametrize("checkpoint", [80], indirect=True)
def test_e1_completed_fit_recovery_does_not_require_new_fit_reserve(
    checkpoint, publication_double, cache_source_enumeration, storage_space,
):
    cp = checkpoint
    calls = publication_double(cp)
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    validated = cp["validated"]
    events = E1._load_events(validated.roots, cp["doc"])
    kwargs = dict(validated=validated, checkpoint_path=cp["path"], start=cp["doc"], events=events)
    assert E1._run_one_job(job, **kwargs) == "executed"
    result = validated.roots["output"] / "jobs" / job.job_id / "job_result.json"
    before = result.read_bytes(), result.stat().st_mtime_ns
    storage_space.free = 0
    storage_space.observed.clear()
    assert E1._run_one_job(job, **kwargs) == "resumed"
    assert calls == [job.job_id]
    assert storage_space.observed == []
    assert (result.read_bytes(), result.stat().st_mtime_ns) == before


@pytest.fixture(params=["exp2a", "sweep-001"])
def baseline_storage_case(baseline_case, request, monkeypatch):
    """Real ready reports + exact inventories + the real registered batch path.

    Reuse authority remains the existing fixture's explicit synthetic loader.
    Fit readers are typed SyntheticFits doubles; journals and sync are real.
    The production executor object and registered payload remain unmodified.
    """
    roots, args, legacy_calls = baseline_case
    plan = LP.build_week7_launch_plan()  # Pure configuration; no preparation file read.
    plan_path = atomic_write_json(args["plan_path"].parent / "storage-launch-plan.json", plan)
    args.update(plan_path=plan_path, batch_key=request.param, minimum_free_bytes=80)
    monkeypatch.setattr(PF, "_batch_jobs", REAL_BATCH_JOBS)
    selected = REAL_BATCH_JOBS(plan, request.param)
    assert len(selected) == (95 if request.param == "exp2a" else 3)
    assert not set(LP.REUSED_FIT_IDS) & {job.job_id for job in selected}
    if request.param == "sweep-001":
        assert [j.job_id for j in selected] == [f"cc428cf4ab47-s{s}" for s in (1000, 1001, 1002)]

    state = SimpleNamespace(roots=roots, args=args, jobs=selected, children=[], anchors=[],
        guard_records=[], child_limit=0, before_new_job=lambda job: None,
        after_first_sync=lambda: None, sync_hook_fired=False)
    store = SyntheticFits()
    monkeypatch.setattr(B, "load_fit_evidence", store.load)

    def anchors(path, *, expected_git_commit):
        verified = store.load(path, expected_git_commit=expected_git_commit)
        row = read_json(Path(path) / "synthetic_anchor.json")
        assert row == {"synthetic_only": True, "fit_id": verified.fit_id,
                       "expected_git_commit": expected_git_commit}
        state.anchors.append(verified.fit_id)
        return SimpleNamespace(anchor_sha256=sha256_file(Path(path) / "synthetic_anchor.json"))
    monkeypatch.setattr(F, "validate_sweep_pool_anchors", anchors)

    def isolated(target, *, root, staging_root, job_id, payload, timeout_seconds):
        # pytest.fail is a BaseException: missing storage guards stop quickly
        # instead of iterating 95 fake successes and disguising the regression.
        if len(state.children) >= state.child_limit:
            pytest.fail("storage guard allowed the unstarted next child")
        assert target is B._execute_registered_in_spawned_child
        assert type(payload) is B._RegisteredFitRequest
        assert payload.expected_git_commit == "b" * 40
        job = payload.job
        assert job.as_record() == next(j.as_record() for j in selected if j.job_id == job_id)
        assert staging_root == roots["staging"] / B._manifest(selected)["batch_id"]
        assert timeout_seconds == 3600.0
        state.children.append(job_id)
        path = Path(root) / "jobs" / job_id
        verified = store.persist(path, job, payload.expected_git_commit)
        if job.stage == "config_sweep":
            atomic_write_json(path / "synthetic_anchor.json", {"synthetic_only": True,
                "fit_id": job_id, "expected_git_commit": payload.expected_git_commit})
        atomic_write_json(path / B.RESULT_FILE, {**result_for(job),
            "fit_evidence_schema_version": B.FIT_EVIDENCE_SCHEMA_VERSION,
            "fit_evidence_file": B.FIT_EVIDENCE_FILE,
            "fit_evidence_digest": verified.execution_digest})
        return AttemptOutcome(job_id, "a" * 32, "success", path, path, 0, published=True)
    monkeypatch.setattr(B, "run_isolated_attempt", isolated)

    def recover(job, job_dir, **kwargs):
        result = REAL_RECOVER_RESULT(job, job_dir, **kwargs)
        if result is None:
            state.before_new_job(job)
        return result
    monkeypatch.setattr(B, "_recover_result", recover)

    def directory_sync(destination):
        adapter = REAL_DIRECTORY_SYNC(destination)
        def sync(batch_dir, job, result):
            receipt = adapter(batch_dir, job, result)
            rows = [json.loads(line) for line in (batch_dir / B.EVENTS_FILE).read_text().splitlines()]
            if (not state.sync_hook_fired and job.job_id == selected[0].job_id and
                    rows and rows[-1]["status"] == "synced"):
                state.sync_hook_fired = True
                state.after_first_sync()
            return receipt
        return sync
    monkeypatch.setattr(B, "sync_to_directory", directory_sync)

    def real_batch(jobs, **kwargs):
        guard = kwargs["preflight_storage_guard"]
        assert type(guard) is G.PreflightStorageGuard
        assert guard.source_path == state.path
        assert guard.source_sha256 == state.pin
        assert dict(guard.roots) == roots
        assert tuple(jobs) == selected
        assert kwargs["executor"] is B._default_executor
        assert kwargs["require_fit_evidence"] is True
        assert kwargs["expected_git_commit"] == "b" * 40
        state.guard_records.append(guard)
        return REAL_BATCH_ENGINE(jobs, **kwargs)
    monkeypatch.setattr(B, "_run_batch", real_batch)

    PF.run_week7_preflight(**args)
    state.path = roots["preflight"] / PF.WEEK7_PREFLIGHT_FILE
    state.pin = sha256_file(state.path)
    state.original_report = read_json(state.path)
    assert state.path.read_bytes() == (roots["sync"] / state.path.name).read_bytes()
    assert legacy_calls == []
    return state


@pytest.mark.parametrize("completed", [0, 1], ids=["before-first", "between-jobs"])
@pytest.mark.parametrize("mutation", ["low_space", "resigned_preflight"])
def test_week7_real_batch_guard_original_pin_and_no_unstarted_attempt(
    baseline_storage_case, storage_space, completed, mutation,
):
    case = baseline_storage_case
    roots = case.roots
    case.child_limit = completed
    injected = []
    storage_space.free = 80

    def mutate():
        assert not injected
        injected.append(True)
        if mutation == "low_space":
            storage_space.free = 79
        else:
            _rewrite_preflight_pair(case.path, roots["sync"])
            assert sha256_file(case.path) != case.pin
    if completed:
        case.after_first_sync = mutate
    else:
        # Let real full preflight checks pass; inject only after the real
        # recovery probe has proved this job still needs a NEW child.
        case.before_new_job = lambda job: mutate()
    expected = ("pre-fit storage: .*below required 80" if mutation == "low_space" else
                "pre-fit storage: preflight changed from the original launch pin")
    with pytest.raises(ValueError, match=expected):
        WL.launch_week7(preflight_report=case.path, output_root=roots["output"],
            sync_root=roots["sync"], attempt_timeout_seconds=3600)
    assert injected == [True]
    assert case.children == [job.job_id for job in case.jobs[:completed]]
    assert len(case.guard_records) == 1
    assert case.guard_records[0].source_sha256 == case.pin
    batch_id = B._manifest(case.jobs)["batch_id"]
    local = roots["output"] / batch_id
    rows = [json.loads(line) for line in (local / B.EVENTS_FILE).read_text().splitlines()]
    assert [row["status"] for row in rows] == (["started", "completed", "synced"] if completed else [])
    assert {row["job_id"] for row in rows} == set(case.children)
    assert read_json(local / B.MANIFEST_FILE) == B._manifest(case.jobs)
    _assert_absent_attempt(roots, case.jobs[completed].job_id, batch_id=batch_id)
    if completed:
        B._copy_evidence_digest(local / "jobs" / case.jobs[0].job_id,
            roots["sync"] / batch_id / "jobs" / case.jobs[0].job_id)
        assert set(case.anchors) == (set() if case.args["batch_key"] == "exp2a" else {case.jobs[0].job_id})
    report_path = next((roots["output"] / WL.WEEK7_REPORT_DIRECTORY).glob("*.json"))
    report = read_json(report_path)
    assert report["status"] == "failed"
    assert report["preflight"]["sha256"] == case.pin
    assert report["historical_reuse_retrained"] is False
    assert report_path.read_bytes() == (roots["sync"] / WL.WEEK7_REPORT_DIRECTORY / report_path.name).read_bytes()


@pytest.mark.parametrize("completed", [0, 1], ids=["before-first", "between-jobs"])
@pytest.mark.parametrize("mutation", ["low_space", "resigned_context"])
def test_sweep_repair_guard_uses_original_start_after_earlier_storage_validation(
    sweep_setup, storage_space, monkeypatch, completed, mutation,
):
    case = sweep_setup
    case.kwargs["minimum_free_bytes"] = 80
    storage_space.free = 80
    actual_prior = SR._prior_attempts
    actual_isolated = case.isolated
    injections = []
    before = {}

    def limited_isolated(*args, **kwargs):
        if len(case.calls["supervisor"]) >= completed:
            pytest.fail("sweep storage guard allowed the unstarted next child")
        return actual_isolated(*args, **kwargs)
    monkeypatch.setattr(SR, "run_isolated_attempt", limited_isolated)

    def prior_then_change(context, job, *, current=None):
        result = actual_prior(context, job, current=current)
        # The worker calls this too: never inject inside an already-started
        # attempt. Parent calls occur AFTER the real full context revalidation.
        if current is None and len(case.calls["supervisor"]) == completed and not injections:
            injections.append(job.job_id)
            before.update({name: _files(case.root / name / "jobs") for name in ("output", "sync")})
            source = case.root / "output" / SR.CONTEXT_FILE
            start_path = next((case.root / "output" / SR.START_DIRECTORY).glob("*.json"))
            start = read_json(start_path)
            assert start["execution_context_digest"] == context["execution_context_digest"]
            if mutation == "low_space":
                storage_space.free = 79
            else:
                changed = read_json(source)
                changed["minimum_free_bytes"] = 1
                changed = SR.W._seal({k: v for k, v in changed.items()
                                      if k != "execution_context_digest"}, "execution_context_digest")
                assert changed["execution_context_digest"] != start["execution_context_digest"]
                for name in ("output", "sync"):
                    (case.root / name / SR.CONTEXT_FILE).write_bytes(SR.L._pretty_json_bytes(changed))
        return result
    monkeypatch.setattr(SR, "_prior_attempts", prior_then_change)
    expected = ("pre-fit storage: .*below required 80" if mutation == "low_space" else
                "pre-fit storage: unsupported or unbound sweep context")
    with pytest.raises(ValueError, match=expected):
        SR.launch_first_sweep_repairs(**case.kwargs)
    assert len(injections) == 1
    assert len(case.calls["supervisor"]) == len(case.calls["fits"]) == completed
    events = [read_json(p) for p in sorted((case.root / "output" / SR.EVENT_DIRECTORY).glob("*.json"))]
    assert [row["kind"] for row in events] == (["attempt_started", "job_synced"] if completed else [])
    assert {row["job_id"] for row in events} == set(case.calls["fits"])
    assert before == {name: _files(case.root / name / "jobs") for name in ("output", "sync")}
    roots = {name: case.root / name for name in ("output", "staging", "sync")}
    _assert_absent_attempt(roots, injections[0])
    report_path = next((case.root / "output" / SR.REPORT_DIRECTORY).glob("*.json"))
    report = read_json(report_path)
    assert report["status"] == "incomplete"
    assert report["counts"]["executed"] == report["counts"]["synced"] == completed
    assert report["baseline_retrained"] is False
    assert report_path.read_bytes() == (case.root / "sync" / SR.REPORT_DIRECTORY / report_path.name).read_bytes()
