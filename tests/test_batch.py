"""Week 6 unattended-batch acceptance tests (synthetic executors only)."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu import constants as K
from bu.config import Arm, Config, UnitSpec
from bu.experiments import batch as B
from bu.experiments.batch import (
    BATCH_SCHEMA_VERSION,
    EVENTS_FILE,
    MANIFEST_FILE,
    RESULT_FILE,
    BatchJob,
    experiment_1_jobs,
    run_synthetic_batch as run_batch,
    sync_to_directory,
)


def job(seed: int) -> BatchJob:
    return BatchJob(
        unit=UnitSpec(n_transitions=100),
        stage="exp1",
        seed=K.CONFIRMATORY_SEED_BASE + seed,
    )


def result_for(item: BatchJob) -> dict:
    cfg = item.config
    return {
        "run_id": cfg.run_id,
        "config_id": cfg.config_id,
        "unit_id": cfg.unit_id,
        "fit_id": cfg.fit_id,
        "stage": item.stage,
        "seed": item.seed,
        "arm": item.arm,
        "fit_roles": list(item.roles),
        "role_run_ids": {
            role: Config(
                unit=item.unit,
                arm=Arm(item.arm),
                stage=role,
                seed=item.seed,
            ).run_id
            for role in item.roles
        },
    }


def event_rows(root: Path) -> list[dict]:
    path = next(root.glob(f"*/{EVENTS_FILE}"))
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def receipt_sync(batch_dir, item, result):
    """Test-only mounted-directory transport with parent-side read-back."""
    adapter = sync_to_directory(batch_dir.parent / "_test_remote")
    return adapter(batch_dir, item, result)


def isolated_result_executor(item, out):
    """Module-level callback so Windows spawn can import and pickle it."""
    (out / "worker_pid.txt").write_text(str(os.getpid()), encoding="utf-8")
    return {**result_for(item), "worker_pid": os.getpid()}


def isolated_exit_then_success_executor(item, out):
    if item.seed == K.CONFIRMATORY_SEED_BASE:
        os._exit(23)
    return isolated_result_executor(item, out)


def test_experiment_1_plan_is_exactly_six_by_five_by_five():
    jobs = experiment_1_jobs()
    assert len(jobs) == 150
    assert len({item.job_id for item in jobs}) == 150
    assert {item.seed for item in jobs} == set(range(1000, 1005))
    assert {item.stage for item in jobs} == {"exp1"}
    assert {item.arm for item in jobs} == {"baseline"}
    shared = [item for item in jobs if len(item.roles) > 1]
    assert len(shared) == 30
    assert {item.roles for item in shared} == {("exp1", "repair_validation")}


def test_incremental_results_and_sync_are_mandatory(tmp_path):
    seen = []

    def executor(item, out):
        assert out.name == item.job_id
        seen.append(("execute", item.job_id))
        return result_for(item)

    def sync(batch_dir, item, result):
        assert (batch_dir / "jobs" / item.job_id / RESULT_FILE).exists()
        seen.append(("sync", result["run_id"]))
        return receipt_sync(batch_dir, item, result)

    report = run_batch([job(0), job(1)], root=tmp_path, executor=executor, sync=sync)
    assert report.executed == report.synced == 2
    assert seen == [
        ("execute", job(0).job_id),
        ("sync", job(0).config.run_id),
        ("sync", job(0).config.run_id),
        ("execute", job(1).job_id),
        ("sync", job(1).config.run_id),
        ("sync", job(1).config.run_id),
    ]
    assert (next(tmp_path.iterdir()) / MANIFEST_FILE).exists()


def test_one_condition_failure_does_not_stop_the_next(tmp_path):
    def executor(item, out):
        if item.seed == 1000:
            raise RuntimeError("planted condition failure")
        return result_for(item)

    report = run_batch(
        [job(0), job(1)], root=tmp_path, executor=executor, sync=receipt_sync
    )
    assert report.failed == 1
    assert report.executed == report.synced == 1
    rows = event_rows(tmp_path)
    assert [r["status"] for r in rows] == ["started", "failed", "started", "completed", "synced"]
    assert "planted condition failure" in rows[1]["error"]


def test_isolated_batch_publishes_child_evidence_and_result(tmp_path):
    report = run_batch(
        [job(0)],
        root=tmp_path,
        executor=isolated_result_executor,
        sync=receipt_sync,
        attempt_timeout_seconds=10,
    )
    assert report.complete is True
    batch_dir = tmp_path / report.batch_id
    job_dir = batch_dir / "jobs" / job(0).job_id
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["worker_pid"] != os.getpid()
    assert (job_dir / "attempt.json").exists()
    assert (job_dir / "attempt_receipt.json").exists()


def test_isolated_batch_uses_separate_validated_staging_root(tmp_path):
    output = tmp_path / "output"
    staging = tmp_path / "staging"
    report = run_batch(
        [job(0)],
        root=output,
        executor=isolated_result_executor,
        sync=receipt_sync,
        attempt_timeout_seconds=10,
        attempt_staging_root=staging,
    )
    assert report.complete is True
    assert (output / report.batch_id / "jobs" / job(0).job_id).exists()
    assert not list((staging / report.batch_id / "staging").iterdir())


def test_staging_root_without_isolation_is_refused_before_manifest(tmp_path):
    with pytest.raises(ValueError, match="requires process isolation"):
        run_batch(
            [job(0)],
            root=tmp_path / "output",
            executor=lambda item, out: result_for(item),
            sync=receipt_sync,
            attempt_staging_root=tmp_path / "staging",
        )
    assert not (tmp_path / "output").exists()


def test_isolated_process_exit_is_quarantined_and_next_condition_runs(tmp_path):
    report = run_batch(
        [job(0), job(1)],
        root=tmp_path,
        executor=isolated_exit_then_success_executor,
        sync=receipt_sync,
        attempt_timeout_seconds=10,
    )
    assert report.failed == 1
    assert report.executed == report.synced == 1
    batch_dir = tmp_path / report.batch_id
    receipts = list((batch_dir / "quarantine").rglob("attempt_receipt.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["status"] == "process_exit"
    assert receipt["exit_code"] == 23
    assert (batch_dir / "jobs" / job(1).job_id / RESULT_FILE).exists()


def test_resume_skips_synced_jobs_without_reexecution(tmp_path):
    calls = []

    def executor(item, out):
        calls.append(item.job_id)
        return result_for(item)

    jobs = [job(0), job(1)]
    first = run_batch(jobs, root=tmp_path, executor=executor, sync=receipt_sync)
    second = run_batch(jobs, root=tmp_path, executor=executor, sync=receipt_sync)
    assert first.executed == 2
    assert second.executed == 0
    assert second.resumed == second.synced == 2
    assert calls == [item.job_id for item in jobs]


def test_interrupted_started_job_is_closed_then_restarted(tmp_path):
    item = job(0)

    with pytest.raises(KeyboardInterrupt):
        run_batch(
            [item], root=tmp_path,
            executor=lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()),
            sync=receipt_sync,
        )

    report = run_batch(
        [item], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=receipt_sync,
    )
    assert report.executed == report.synced == 1
    rows = event_rows(tmp_path)
    assert [row["status"] for row in rows] == [
        "started", "failed", "started", "completed", "synced"
    ]
    assert rows[1]["error_type"] == "InterruptedRun"


def test_result_written_before_interruption_is_recovered_without_refit(tmp_path):
    item = job(0)

    def interrupted_after_result(_item, out):
        (out / RESULT_FILE).write_text(
            json.dumps(result_for(item)), encoding="utf-8"
        )
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        run_batch(
            [item], root=tmp_path, executor=interrupted_after_result,
            sync=receipt_sync,
        )

    report = run_batch(
        [item], root=tmp_path,
        executor=lambda *args: pytest.fail("durable result must not refit"),
        sync=receipt_sync,
    )
    assert report.executed == 0
    assert report.resumed == report.synced == 1
    rows = event_rows(tmp_path)
    assert [row["status"] for row in rows] == ["started", "completed", "synced"]
    assert rows[1]["recovered_after_interruption"] is True


def test_sync_failure_retries_sync_without_rerunning_fit(tmp_path):
    executions = []

    def executor(item, out):
        executions.append(item.job_id)
        return result_for(item)

    def broken(*args):
        raise OSError("planted sync outage")

    first = run_batch([job(0)], root=tmp_path, executor=executor, sync=broken)
    second = run_batch(
        [job(0)], root=tmp_path, executor=executor, sync=receipt_sync
    )
    assert first.sync_failed == 1
    assert second.resumed == second.synced == 1
    assert executions == [job(0).job_id]


def test_directory_sync_copies_each_incremental_job(tmp_path):
    local, remote = tmp_path / "local", tmp_path / "remote"
    report = run_batch(
        [job(0)],
        root=local,
        executor=lambda item, out: result_for(item),
        sync=sync_to_directory(remote),
    )
    copied = remote / report.batch_id
    assert (copied / MANIFEST_FILE).exists()
    assert (copied / "jobs" / job(0).job_id / RESULT_FILE).exists()
    assert (copied / EVENTS_FILE).read_bytes() == (
        local / report.batch_id / EVENTS_FILE
    ).read_bytes()

    # A fresh worker can use the synced tree as its checkpoint. The remote
    # event stream intentionally ends at "completed" (the first sync occurs
    # before the local "synced" acknowledgement), which causes one harmless
    # sync retry and never a second fit.
    resumed = run_batch(
        [job(0)],
        root=remote,
        executor=lambda *args: pytest.fail("synced result must not rerun"),
        sync=receipt_sync,
    )
    assert resumed.executed == 0
    assert resumed.resumed == resumed.synced == 1


def test_resume_revalidates_the_current_sync_destination(tmp_path):
    local = tmp_path / "local"
    first_store = tmp_path / "store-a"
    second_store = tmp_path / "store-b"
    first = run_batch(
        [job(0)],
        root=local,
        executor=lambda item, out: result_for(item),
        sync=sync_to_directory(first_store),
    )
    assert (first_store / first.batch_id / "jobs" / job(0).job_id).exists()
    assert not second_store.exists()

    resumed = run_batch(
        [job(0)],
        root=local,
        executor=lambda *args: pytest.fail("synced fit must not rerun"),
        sync=sync_to_directory(second_store),
    )
    assert resumed.complete is True
    assert (second_store / first.batch_id / "jobs" / job(0).job_id).exists()
    rows = event_rows(local)
    assert rows[-1]["status"] == "synced"
    assert rows[-1]["re_attestation"] is True
    assert Path(rows[-1]["sync_receipt"]["destination"]).is_relative_to(
        second_store.resolve()
    )
    assert (second_store / first.batch_id / EVENTS_FILE).read_bytes() == (
        local / first.batch_id / EVENTS_FILE
    ).read_bytes()


def test_interrupted_post_ack_sync_is_retried_without_refit(tmp_path):
    calls = []

    def executor(item, out):
        calls.append(item.job_id)
        return result_for(item)

    transports = 0

    def interrupted_finalization(batch_dir, item, result):
        nonlocal transports
        transports += 1
        if transports == 2:
            raise OSError("planted post-ack transport interruption")
        return receipt_sync(batch_dir, item, result)

    with pytest.raises(OSError, match="post-ack transport"):
        run_batch(
            [job(0)],
            root=tmp_path,
            executor=executor,
            sync=interrupted_finalization,
        )

    resumed = run_batch(
        [job(0)], root=tmp_path, executor=executor, sync=receipt_sync
    )
    assert resumed.executed == 0
    assert resumed.resumed == resumed.synced == 1
    assert calls == [job(0).job_id]


def test_manifest_is_immutable_and_plan_changes_get_a_new_batch(tmp_path):
    first = run_batch(
        [job(0)], root=tmp_path, executor=lambda item, out: result_for(item),
        sync=receipt_sync,
    )
    second = run_batch(
        [job(0), job(1)], root=tmp_path,
        executor=lambda item, out: result_for(item), sync=receipt_sync,
    )
    assert first.batch_id != second.batch_id


def test_result_identity_is_cross_checked_before_completion(tmp_path):
    bad = result_for(job(0))
    bad["seed"] = 999
    report = run_batch(
        [job(0)], root=tmp_path, executor=lambda item, out: bad,
        sync=lambda *args: pytest.fail("bad result must not sync"),
    )
    assert report.failed == 1
    assert not any(r["status"] == "completed" for r in event_rows(tmp_path))


def test_partial_immutable_run_is_refused_not_overwritten(tmp_path):
    item = job(0)
    manifest_report = run_batch(
        [item], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=receipt_sync,
    )
    batch = tmp_path / manifest_report.batch_id
    # Make a different batch root with an intentionally partial run using a
    # second job, then prove resume will not call its executor over that state.
    other = job(1)
    called = []
    first = run_batch(
        [other], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=receipt_sync,
    )
    other_batch = tmp_path / first.batch_id
    result_path = other_batch / "jobs" / other.job_id / RESULT_FILE
    result_path.unlink()
    (other_batch / "jobs" / other.job_id / other.config.run_id).mkdir()
    # Remove the terminal sync event so recovery is attempted.
    events = other_batch / EVENTS_FILE
    rows = events.read_text(encoding="utf-8").splitlines()[:-1]
    events.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checkpointed result.*cannot be recovered"):
        run_batch(
            [other], root=tmp_path,
            executor=lambda i, out: called.append(i.job_id) or result_for(i),
            sync=receipt_sync,
        )
    assert called == []


def test_checkpoint_refuses_an_illegal_event_transition(tmp_path):
    item = job(0)
    report = run_batch(
        [item], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=receipt_sync,
    )
    path = tmp_path / report.batch_id / EVENTS_FILE
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "schema_version": BATCH_SCHEMA_VERSION,
            "job_id": item.job_id,
            "status": "started",
        }) + "\n")
    with pytest.raises(ValueError, match="illegal transition"):
        run_batch(
            [item], root=tmp_path, executor=lambda i, out: result_for(i),
            sync=receipt_sync,
        )


def test_checkpoint_digest_binds_recovered_result(tmp_path):
    item = job(0)
    report = run_batch(
        [item], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    result_path = tmp_path / report.batch_id / "jobs" / item.job_id / RESULT_FILE
    changed = json.loads(result_path.read_text(encoding="utf-8"))
    changed["extra"] = "mutated after checkpoint"
    result_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint digest"):
        run_batch(
            [item], root=tmp_path,
            executor=lambda *args: pytest.fail("must not rerun"),
            sync=lambda *args: pytest.fail("mutated result must not sync"),
        )


def test_torn_final_event_is_preserved_then_resume_continues(tmp_path):
    item = job(0)
    executions = []

    def executor(current, out):
        executions.append(current.job_id)
        return result_for(current)

    first = run_batch(
        [item],
        root=tmp_path,
        executor=executor,
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    events = tmp_path / first.batch_id / EVENTS_FILE
    fragment = b'{"status":"torn"'
    with events.open("ab") as handle:
        handle.write(fragment)

    resumed = run_batch(
        [item], root=tmp_path, executor=executor, sync=receipt_sync
    )

    assert resumed.executed == 0
    assert resumed.resumed == resumed.synced == 1
    assert executions == [item.job_id]
    preserved = list(
        (tmp_path / first.batch_id / "journal_recovery").glob("*.torn")
    )
    assert len(preserved) == 1
    assert preserved[0].read_bytes() == fragment


def test_directory_sync_never_overwrites_different_remote_evidence(tmp_path):
    local, remote = tmp_path / "local", tmp_path / "remote"
    adapter = sync_to_directory(remote)
    report = run_batch(
        [job(0)], root=local, executor=lambda item, out: result_for(item),
        sync=adapter,
    )
    remote_result = remote / report.batch_id / "jobs" / job(0).job_id / RESULT_FILE
    remote_result.write_text("different bytes\n", encoding="utf-8")
    # Force a sync retry while preserving the completed-result digest.
    events = local / report.batch_id / EVENTS_FILE
    rows = events.read_text(encoding="utf-8").splitlines()
    synced = json.loads(rows[-1])
    synced["status"] = "sync_failed"
    rows[-1] = json.dumps(synced)
    events.write_text("\n".join(rows) + "\n", encoding="utf-8")
    retried = run_batch(
        [job(0)], root=local, executor=lambda *args: pytest.fail("must not rerun"),
        sync=adapter,
    )
    assert retried.sync_failed == 1
    assert remote_result.read_text(encoding="utf-8") == "different bytes\n"


def test_directory_sync_fsyncs_then_atomically_replaces_every_new_final(
    monkeypatch, tmp_path
):
    local, remote = tmp_path / "local", tmp_path / "remote"
    item = job(0)
    report = run_batch(
        [item],
        root=local,
        executor=lambda current, out: result_for(current),
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    batch_dir = local / report.batch_id
    real_replace = B.os.replace
    real_fsync = B.os.fsync
    replacements = []
    fsynced_descriptors = []

    def recording_replace(source, target):
        replacements.append((Path(source), Path(target)))
        return real_replace(source, target)

    def recording_fsync(descriptor):
        fsynced_descriptors.append(descriptor)
        return real_fsync(descriptor)

    monkeypatch.setattr(B.os, "replace", recording_replace)
    monkeypatch.setattr(B.os, "fsync", recording_fsync)
    receipt = sync_to_directory(remote)(batch_dir, item, result_for(item))

    target_batch = remote / report.batch_id
    final_targets = {target for _, target in replacements}
    assert target_batch / "jobs" / item.job_id in final_targets
    assert target_batch / MANIFEST_FILE in final_targets
    assert target_batch / EVENTS_FILE in final_targets
    assert all(source.parent == target.parent for source, target in replacements)
    assert all(source.name.startswith(".") for source, _ in replacements)
    assert len(fsynced_descriptors) >= 3
    assert (target_batch / MANIFEST_FILE).read_bytes() == (
        batch_dir / MANIFEST_FILE
    ).read_bytes()
    assert (target_batch / EVENTS_FILE).read_bytes() == (
        batch_dir / EVENTS_FILE
    ).read_bytes()
    assert receipt.destination == str(
        (target_batch / "jobs" / item.job_id).resolve()
    )


def test_directory_sync_never_acknowledges_a_tree_that_failed_fsync(
    monkeypatch, tmp_path
):
    local, remote = tmp_path / "local", tmp_path / "remote"
    item = job(0)
    report = run_batch(
        [item],
        root=local,
        executor=lambda current, out: result_for(current),
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    batch_dir = local / report.batch_id
    target_job = remote / report.batch_id / "jobs" / item.job_id
    real_fsync_file = B._fsync_regular_file

    def tear_before_publication(path):
        if ".partial" in str(path):
            raise ValueError("synthetic torn durable write")
        return real_fsync_file(path)

    monkeypatch.setattr(B, "_fsync_regular_file", tear_before_publication)
    with pytest.raises(ValueError, match="synthetic torn durable write"):
        sync_to_directory(remote)(batch_dir, item, result_for(item))

    assert not os.path.lexists(target_job)
    assert not list(target_job.parent.glob(f".{item.job_id}.*.partial"))
    assert not (remote / report.batch_id / MANIFEST_FILE).exists()
    assert not (remote / report.batch_id / EVENTS_FILE).exists()


def test_directory_sync_rejects_a_hard_linked_destination_tree(tmp_path):
    local, remote = tmp_path / "local", tmp_path / "remote"
    item = job(0)
    report = run_batch(
        [item],
        root=local,
        executor=lambda current, out: result_for(current),
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    batch_dir = local / report.batch_id
    source_job = batch_dir / "jobs" / item.job_id
    target_job = remote / report.batch_id / "jobs" / item.job_id
    for source in source_job.rglob("*"):
        relative = source.relative_to(source_job)
        target = target_job / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(source, target)

    with pytest.raises(ValueError, match="hard-linked"):
        sync_to_directory(remote)(batch_dir, item, result_for(item))


def test_directory_sync_rejects_a_symlinked_destination_tree(tmp_path):
    local, remote = tmp_path / "local", tmp_path / "remote"
    item = job(0)
    report = run_batch(
        [item],
        root=local,
        executor=lambda current, out: result_for(current),
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    batch_dir = local / report.batch_id
    source_job = batch_dir / "jobs" / item.job_id
    target_job = remote / report.batch_id / "jobs" / item.job_id
    target_job.parent.mkdir(parents=True)
    try:
        target_job.symlink_to(source_job, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"this Windows account cannot create symlinks: {exc}")

    with pytest.raises(ValueError, match="plain directory|symbolic-link"):
        sync_to_directory(remote)(batch_dir, item, result_for(item))


def test_directory_sync_rejects_non_regular_source_artifacts(monkeypatch, tmp_path):
    local, remote = tmp_path / "local", tmp_path / "remote"
    item = job(0)
    report = run_batch(
        [item],
        root=local,
        executor=lambda current, out: result_for(current),
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    batch_dir = local / report.batch_id
    planted = batch_dir / "jobs" / item.job_id / RESULT_FILE
    original_lstat = Path.lstat

    def planted_special_file(path, *args, **kwargs):
        metadata = original_lstat(path, *args, **kwargs)
        if path == planted:
            return SimpleNamespace(
                st_mode=stat.S_IFIFO,
                st_nlink=1,
                st_size=metadata.st_size,
                st_dev=metadata.st_dev,
                st_ino=metadata.st_ino,
            )
        return metadata

    monkeypatch.setattr(Path, "lstat", planted_special_file)
    with pytest.raises(ValueError, match="not a regular file"):
        sync_to_directory(remote)(batch_dir, item, result_for(item))


def test_receipt_validation_requires_current_independent_copy_evidence(tmp_path):
    local, remote = tmp_path / "local", tmp_path / "remote"
    item = job(0)
    report = run_batch(
        [item],
        root=local,
        executor=lambda current, out: result_for(current),
        sync=lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    batch_dir = local / report.batch_id
    receipt = sync_to_directory(remote)(batch_dir, item, result_for(item))
    forged = replace(receipt, copy_evidence_digest="0" * 64)

    with pytest.raises(ValueError, match="independently materialised"):
        B._validate_sync_receipt(
            forged,
            batch_dir=batch_dir,
            job=item,
            result=result_for(item),
        )


@pytest.mark.parametrize("artifact", [MANIFEST_FILE, EVENTS_FILE])
def test_directory_sync_never_overwrites_divergent_batch_history(
    tmp_path, artifact
):
    local, remote = tmp_path / "local", tmp_path / "remote"
    adapter = sync_to_directory(remote)
    report = run_batch(
        [job(0)], root=local, executor=lambda item, out: result_for(item),
        sync=adapter,
    )
    remote_artifact = remote / report.batch_id / artifact
    planted = b"divergent remote evidence\n"
    remote_artifact.write_bytes(planted)

    # Retry the sync while preserving the completed-result checkpoint.
    events = local / report.batch_id / EVENTS_FILE
    rows = events.read_text(encoding="utf-8").splitlines()
    synced = json.loads(rows[-1])
    synced["status"] = "sync_failed"
    rows[-1] = json.dumps(synced)
    events.write_text("\n".join(rows) + "\n", encoding="utf-8")

    retried = run_batch(
        [job(0)], root=local, executor=lambda *args: pytest.fail("must not rerun"),
        sync=adapter,
    )
    assert retried.sync_failed == 1
    assert remote_artifact.read_bytes() == planted


def test_batch_refuses_missing_sync_and_duplicate_jobs(tmp_path):
    with pytest.raises(ValueError, match="sync must be a callable"):
        run_batch([job(0)], root=tmp_path, executor=lambda i, out: result_for(i), sync=None)
    with pytest.raises(ValueError, match="duplicate job identities"):
        run_batch([job(0), job(0)], root=tmp_path, executor=lambda i, out: result_for(i), sync=lambda *args: None)
    with pytest.raises(ValueError, match="exact BatchJob"):
        run_batch([{"job": "not typed"}], root=tmp_path, executor=lambda *args: {}, sync=lambda *args: None)
    with pytest.raises(ValueError, match="roles must be"):
        BatchJob(unit=UnitSpec(n_transitions=100), stage="exp1", seed=1000, roles=[])


def test_no_op_sync_callback_cannot_claim_durable_completion(tmp_path):
    report = run_batch(
        [job(0)],
        root=tmp_path,
        executor=lambda item, out: result_for(item),
        sync=lambda *args: None,
    )
    assert report.executed == 1
    assert report.synced == 0
    assert report.sync_failed == 1
    assert report.complete is False
    assert event_rows(tmp_path)[-1]["status"] == "sync_failed"
    assert "exact SyncReceipt" in event_rows(tmp_path)[-1]["error"]


def test_self_attested_local_tree_cannot_claim_sync_off(tmp_path):
    def self_attest(batch_dir, item, result):
        source = batch_dir / "jobs" / item.job_id
        return B.SyncReceipt(
            destination=str(source),
            job_id=item.job_id,
            result_digest=B._result_digest(result),
            job_tree_digest=B._job_tree_digest(source),
            copy_evidence_digest="a" * 64,
        )

    report = run_batch(
        [job(0)],
        root=tmp_path,
        executor=lambda item, out: result_for(item),
        sync=self_attest,
    )
    assert report.synced == 0
    assert report.sync_failed == 1
    assert "inside the local batch tree" in event_rows(tmp_path)[-1]["error"]


def test_default_recovery_refuses_confirmatory_without_fit_sidecar(tmp_path):
    item = next(item for item in experiment_1_jobs() if len(item.roles) > 1)
    job_dir = tmp_path / "job"
    physical = job_dir / item.config.run_id
    physical.mkdir(parents=True)
    (physical / "confirmatory.json").write_text(
        json.dumps(result_for(item)), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="partial evidence"):
        B._recover_result(
            item,
            job_dir,
            require_fit_evidence=True,
            expected_git_commit="b" * 40,
        )
    assert not (job_dir / RESULT_FILE).exists()


def test_default_executor_accepts_one_registered_multi_role_fit(monkeypatch, tmp_path):
    import bu.experiments.batch as B

    item = next(job for job in experiment_1_jobs() if len(job.roles) > 1)
    calls = []

    class Completed:
        def as_row(self):
            return {
                **result_for(item),
                "fit_evidence_schema_version": 1,
                "fit_evidence_file": "fit_evidence.json",
                "fit_evidence_digest": "a" * 64,
            }

    def fake_run(unit, *, seed, arm, out_dir, expected_git_commit):
        calls.append((unit, seed, arm, out_dir, expected_git_commit))
        return Completed()

    monkeypatch.setattr(B, "run_confirmatory_fit", fake_run)
    assert B._default_executor(
        item, tmp_path, expected_git_commit="a" * 40
    ).get("fit_roles") == list(item.roles)
    assert len(calls) == 1
    assert calls[0][-1] == "a" * 40


def test_registered_spawn_payload_preserves_the_exact_preflight_commit(
    monkeypatch, tmp_path
):
    item = experiment_1_jobs()[0]
    calls = []

    def fake_default(job, out, *, expected_git_commit):
        calls.append((job, out, expected_git_commit))
        return result_for(job)

    monkeypatch.setattr(B, "_default_executor", fake_default)
    request = B._RegisteredFitRequest(
        job=item, expected_git_commit="a" * 40
    )
    result = B._execute_registered_in_spawned_child(tmp_path, request)

    assert result == result_for(item)
    assert calls == [(item, tmp_path, "a" * 40)]


@pytest.mark.parametrize("bad", [None, "A" * 40, "a" * 39, True])
def test_registered_batch_refuses_an_invalid_preflight_commit_before_writing(
    tmp_path, bad
):
    with pytest.raises(ValueError, match="expected_git_commit"):
        B._run_registered_batch(
            experiment_1_jobs(),
            root=tmp_path / "output",
            sync=receipt_sync,
            expected_git_commit=bad,
            attempt_timeout_seconds=10,
            attempt_staging_root=tmp_path / "staging",
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("timeout", "staging"),
    [
        pytest.param(None, "staging", id="missing-timeout"),
        pytest.param(10, None, id="missing-staging"),
    ],
)
def test_registered_default_batch_requires_every_production_launch_guard(
    tmp_path, timeout, staging
):
    staging_root = None if staging is None else tmp_path / staging
    with pytest.raises(ValueError, match="private registered batch hand-off"):
        B._run_registered_batch(
            experiment_1_jobs(),
            root=tmp_path,
            sync=receipt_sync,
            expected_git_commit="a" * 40,
            attempt_timeout_seconds=timeout,
            attempt_staging_root=staging_root,
        )
    assert not list(tmp_path.iterdir())


def test_batch_exposes_no_public_production_launcher_or_capability(tmp_path):
    assert not hasattr(B, "run_batch")
    assert not hasattr(B, "_REGISTERED_LAUNCH_CAPABILITY")
    wrapped = lambda item, out: B._default_executor(
        item, out, expected_git_commit="a" * 40
    )
    with pytest.raises(TypeError, match="executor"):
        B._run_registered_batch(
            experiment_1_jobs(),
            root=tmp_path / "output",
            sync=receipt_sync,
            expected_git_commit="a" * 40,
            executor=wrapped,
            attempt_timeout_seconds=10,
            attempt_staging_root=tmp_path / "staging",
        )
    assert not list(tmp_path.iterdir())
