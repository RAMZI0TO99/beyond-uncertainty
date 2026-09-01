"""Synthetic production-boundary tests for Week-8 E2A repairs."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import week8_exp2a_repair_launch as X
from bu.experiments import week8_exp2a_repairs as W
from bu.experiments import week8_exp2a_sources as S
from bu.experiments.supervisor import AttemptOutcome, LeaseConflictError, acquire_batch_lease
from bu.runrecord import GitState, TRACKED_PACKAGES

from test_week8_exp2a_sources import authority, source_trees


COMMIT = "b" * 40


@pytest.fixture
def environment(monkeypatch):
    pins = {name: f"synthetic-{index}" for index, name in enumerate(TRACKED_PACKAGES)}
    monkeypatch.setattr(
        X.P,
        "_verify_environment",
        lambda: (GitState(COMMIT, False, "synthetic"), dict(pins), dict(pins)),
    )
    monkeypatch.setattr(
        X.P,
        "_verify_device",
        lambda route: {
            "frozen_route": "cpu",
            "requested_route": route,
            "available": route == "cpu",
        },
    )


@pytest.fixture
def preflight(source_trees, environment, monkeypatch):
    root, store = source_trees
    for name in ("inputs", "preflight", "output", "staging", "sync"):
        (root / name).mkdir()
    plan = W.write_exp2a_repair_plan(root / "inputs")
    ledger = S.write_exp2a_source_ledger(root / "inputs")
    X.run_exp2a_repair_preflight(
        plan_path=plan,
        source_ledger_path=ledger,
        expected_git_commit=COMMIT,
        preflight_dir=root / "preflight",
        output_root=root / "output",
        staging_root=root / "staging",
        sync_root=root / "sync",
        attempt_timeout_seconds=17,
        minimum_free_bytes=0,
        sync_destination_identity="synthetic-independent-project-copy",
    )
    report_path = root / "preflight" / X.PREFLIGHT_FILE
    validated = X.validate_exp2a_repair_preflight(
        report_path,
        output_root=root / "output",
        sync_root=root / "sync",
        expected_git_commit=COMMIT,
    )
    # Consumer tests retain the exact already-validated immutable snapshot.
    monkeypatch.setattr(X, "validate_exp2a_repair_preflight", lambda *a, **k: validated)
    return {
        "root": root,
        "store": store,
        "plan": plan,
        "ledger": ledger,
        "report": report_path,
        "validated": validated,
    }


@pytest.fixture
def checkpoint(preflight):
    with acquire_batch_lease(W.COMMON_LEASE_ROOT, lease_name=W.COMMON_LEASE_NAME) as lease:
        path = X.write_exp2a_repair_start_checkpoint(
            source_ledger_path=preflight["ledger"],
            expected_git_commit=COMMIT,
            output_root=preflight["root"] / "output",
            staging_root=preflight["root"] / "staging",
            sync_root=preflight["root"] / "sync",
            attempt_timeout_seconds=17,
            lease=lease,
            preflight_report=preflight["report"],
        )
        yield {
            **preflight,
            "path": path,
            "sha": sha256_file(path),
            "doc": read_json(path),
            "lease": lease,
        }


@pytest.fixture
def publication(monkeypatch):
    calls = []

    def install(cp, *, mode="success"):
        original_publish = X.B._publish_job_tree

        def publish(source, destination):
            original_publish(source, destination)
            commit, verified = cp["store"].entries[Path(source).resolve()]
            cp["store"].entries[Path(destination).resolve()] = (
                commit,
                __import__("dataclasses").replace(
                    verified, fit_dir=Path(destination).resolve()
                ),
            )

        monkeypatch.setattr(X.B, "_publish_job_tree", publish)

        def isolated(callback, *, root, staging_root, job_id, payload, timeout_seconds):
            assert callback is X._fit_worker
            assert timeout_seconds == 17
            job = X._new_job(job_id)
            assert payload["job"] == job.as_record()
            calls.append(job_id)
            token = hashlib.sha256(job_id.encode()).hexdigest()[:32]
            if mode == "timeout":
                quarantine = Path(staging_root) / "quarantine" / f"{job_id}.{token}"
                quarantine.mkdir(parents=True)
                atomic_write_json(quarantine / "attempt_receipt.json", {"status": "timeout"})
                return AttemptOutcome(job_id, token, "timeout", quarantine, None, -1)
            start, ledger, roots = X._load_start(
                payload["checkpoint_path"],
                expected_sha256=payload["checkpoint_sha256"],
                expected_git_commit=COMMIT,
            )
            binding = None
            if job.arm != "baseline":
                # Match the private worker: prove and load the exact seed
                # baseline before any fit output can be created.
                _, binding = X._baseline(job, ledger, roots, COMMIT, start)
            path = Path(root) / "jobs" / job_id
            digest = hashlib.sha256(f"new:{job_id}".encode()).hexdigest()
            verified = cp["store"].persist(path, job, COMMIT, digest)
            atomic_write_json(
                path / "job_result.json",
                X._result_record(
                    job,
                    verified,
                    commit=COMMIT,
                    checkpoint_digest=start["checkpoint_digest"],
                    binding=binding,
                    execution_context_digest=start["execution_context_digest"],
                ),
            )
            return AttemptOutcome(job_id, token, "success", path, path, 0, published=True)

        monkeypatch.setattr(X, "run_isolated_attempt", isolated)
        return calls

    return install


def _events(cp):
    return X._load_events(cp["validated"].roots, cp["doc"])


def _run(cp, job, events):
    return X._run_one_job(
        job,
        validated=cp["validated"],
        checkpoint_path=cp["path"],
        start=cp["doc"],
        events=events,
    )


def test_preflight_is_cpu_only_immutable_and_binds_exact_counts(preflight):
    report = read_json(preflight["report"])
    assert report["status"] == "ready"
    assert report["launch_performed"] is False
    assert report["environment"]["device"]["requested_route"] == "cpu"
    assert report["budget"] == {
        "new_physical_fits": 261,
        "new_member_models": 441,
        "new_baseline_fits": 45,
        "new_repair_fits": 216,
        "historical_sources_reopened": 155,
        "interpretation": "exact inventory counts; not a runtime or GPU-hour estimate",
    }
    assert report["common_control_root"] == str(W.COMMON_LEASE_ROOT.resolve())
    assert not os.path.samefile(
        preflight["report"], preflight["root"] / "sync" / X.PREFLIGHT_FILE
    )


def test_fixed_fresh_supervisor_syncs_once_and_resume_never_retrains(
    checkpoint, publication
):
    calls = publication(checkpoint)
    job = next(job for job in W.new_exp2a_jobs() if job.arm == "baseline")
    events = _events(checkpoint)
    assert _run(checkpoint, job, events) == "executed"
    assert calls == [job.job_id]
    assert [event["kind"] for event in events] == ["attempt_started", "job_synced"]
    source = checkpoint["root"] / "output" / "jobs" / job.job_id
    copy_path = checkpoint["root"] / "sync" / "jobs" / job.job_id
    assert X.B._copy_evidence_digest(source, copy_path) == events[-1]["data"]["copy_evidence_digest"]
    assert _run(checkpoint, job, events) == "resumed"
    assert calls == [job.job_id]


def test_existing_seed_repair_uses_week7_baseline_without_retraining_it(
    checkpoint, publication
):
    calls = publication(checkpoint)
    job = next(
        job for job in W.new_exp2a_jobs()
        if job.arm == "data_repair" and job.stage == "exp3_repairs"
    )
    events = _events(checkpoint)
    assert _run(checkpoint, job, events) == "executed"
    result = read_json(
        checkpoint["root"] / "output" / "jobs" / job.job_id / "job_result.json"
    )
    assert result["baseline_source"]["expected_git_commit"] == W.WEEK7_EXECUTION_COMMIT
    assert calls == [job.job_id]


def test_new_validation_repair_cannot_run_before_its_new_seed_baseline(
    checkpoint, publication
):
    calls = publication(checkpoint)
    job = next(
        job for job in W.new_exp2a_jobs()
        if job.arm == "feature_repair" and job.seed == 1005
    )
    events = _events(checkpoint)
    with pytest.raises(ValueError, match="missing|unavailable|source"):
        _run(checkpoint, job, events)
    assert calls == [job.job_id]
    assert [event["kind"] for event in events] == ["attempt_started", "attempt_failed"]
    assert not (checkpoint["root"] / "output" / "jobs" / job.job_id).exists()


def test_new_baseline_then_repair_share_exact_scale_and_pool(checkpoint, publication):
    calls = publication(checkpoint)
    repair = next(
        job for job in W.new_exp2a_jobs()
        if job.arm == "data_repair" and job.seed == 1005
    )
    baseline = next(
        job for job in W.new_exp2a_jobs()
        if job.unit == repair.unit and job.seed == repair.seed and job.arm == "baseline"
    )
    events = _events(checkpoint)
    assert _run(checkpoint, baseline, events) == "executed"
    assert _run(checkpoint, repair, events) == "executed"
    local_baseline = checkpoint["store"].load(
        checkpoint["root"] / "output" / "jobs" / baseline.job_id,
        expected_git_commit=COMMIT,
    )
    local_repair = checkpoint["store"].load(
        checkpoint["root"] / "output" / "jobs" / repair.job_id,
        expected_git_commit=COMMIT,
    )
    assert local_repair.scale.as_row() == local_baseline.scale.as_row()
    assert local_repair.evaluation_pool_digest == local_baseline.evaluation_pool_digest
    assert calls == [baseline.job_id, repair.job_id]


def test_private_worker_passes_exact_baseline_scale_and_rechecks_pool(
    checkpoint, monkeypatch
):
    job = next(
        job for job in W.new_exp2a_jobs()
        if job.arm == "data_repair" and job.stage == "exp3_repairs"
    )
    token = "a" * 32
    attempt = checkpoint["root"] / "staging" / "staging" / f"{job.job_id}.{token}"
    attempt.mkdir(parents=True)
    parent_pid = read_json(Path(checkpoint["doc"]["lease"]["path"]))["pid"]
    atomic_write_json(
        attempt / "attempt.json",
        {
            "schema_version": X.SUPERVISOR_SCHEMA_VERSION,
            "job_id": job.job_id,
            "attempt_token": token,
            "parent_pid": parent_pid,
            "started_at": checkpoint["doc"]["lease"]["started_at"],
            "timeout_seconds": 17,
        },
    )
    captured = {}

    def run(unit, *, arm, seed, out_dir, scale, expected_git_commit):
        captured.update(unit=unit, arm=arm, seed=seed, scale=scale, commit=expected_git_commit)
        digest = hashlib.sha256(f"worker:{job.job_id}".encode()).hexdigest()
        checkpoint["store"].persist(out_dir, job, COMMIT, digest)

    monkeypatch.setattr(X.F, "run_confirmatory_fit", run)
    real_pid = os.getpid()
    monkeypatch.setattr(X.os, "getpid", lambda: real_pid + 1)
    result = X._fit_worker(
        attempt,
        {
            "checkpoint_path": str(checkpoint["path"]),
            "checkpoint_sha256": checkpoint["sha"],
            "expected_git_commit": COMMIT,
            "job": job.as_record(),
        },
    )
    baseline = next(
        old for old in W.existing_exp2a_jobs()
        if old.unit == job.unit and old.seed == job.seed and old.arm == "baseline"
    )
    baseline_fit = checkpoint["store"].load(
        S._source_paths(baseline)[0], expected_git_commit=W.WEEK7_EXECUTION_COMMIT
    )
    assert captured["scale"].as_row() == baseline_fit.scale.as_row()
    assert result["baseline_source"]["job"]["job_id"] == baseline.job_id


def test_failed_attempt_is_preserved_and_never_automatically_retried(
    checkpoint, publication
):
    calls = publication(checkpoint, mode="timeout")
    job = next(job for job in W.new_exp2a_jobs() if job.arm == "baseline")
    events = _events(checkpoint)
    with pytest.raises(ValueError, match="exact successful"):
        _run(checkpoint, job, events)
    assert [event["kind"] for event in events] == ["attempt_started", "attempt_failed"]
    with pytest.raises(ValueError, match="prior failed attempt"):
        _run(checkpoint, job, events)
    assert calls == [job.job_id]


@pytest.mark.parametrize("prior", ["event", "staging", "quarantine", "durable"])
def test_partial_or_unknown_history_never_starts_another_fit(
    checkpoint, publication, prior
):
    calls = publication(checkpoint)
    job = next(job for job in W.new_exp2a_jobs() if job.arm == "baseline")
    events = _events(checkpoint)
    roots = checkpoint["validated"].roots
    if prior == "event":
        X._append_event(
            roots,
            checkpoint["doc"],
            events,
            kind="attempt_started",
            job_id=job.job_id,
            data={"checkpoint_digest": checkpoint["doc"]["checkpoint_digest"]},
        )
    elif prior == "durable":
        (roots["sync"] / "jobs" / job.job_id).mkdir(parents=True)
    else:
        (roots["staging"] / prior / f"{job.job_id}.{'c' * 32}").mkdir(parents=True)
    with pytest.raises(ValueError, match="prior|retraining|inspection"):
        _run(checkpoint, job, events)
    assert calls == []


def test_public_launch_contends_on_the_shared_production_lease(checkpoint):
    with pytest.raises(LeaseConflictError):
        X.launch_exp2a_repairs(
            preflight_report=checkpoint["report"],
            output_root=checkpoint["root"] / "output",
            sync_root=checkpoint["root"] / "sync",
            expected_git_commit=COMMIT,
        )
