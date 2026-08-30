"""Week 6 unattended-batch acceptance tests (synthetic executors only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bu import constants as K
from bu.config import Config, UnitSpec
from bu.experiments.batch import (
    EVENTS_FILE,
    MANIFEST_FILE,
    RESULT_FILE,
    BatchJob,
    experiment_1_jobs,
    run_batch,
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
    }


def event_rows(root: Path) -> list[dict]:
    path = next(root.glob(f"*/{EVENTS_FILE}"))
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


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

    report = run_batch([job(0), job(1)], root=tmp_path, executor=executor, sync=sync)
    assert report.executed == report.synced == 2
    assert seen == [
        ("execute", job(0).job_id), ("sync", job(0).config.run_id),
        ("execute", job(1).job_id), ("sync", job(1).config.run_id),
    ]
    assert (next(tmp_path.iterdir()) / MANIFEST_FILE).exists()


def test_one_condition_failure_does_not_stop_the_next(tmp_path):
    def executor(item, out):
        if item.seed == 1000:
            raise RuntimeError("planted condition failure")
        return result_for(item)

    report = run_batch(
        [job(0), job(1)], root=tmp_path, executor=executor, sync=lambda *args: None
    )
    assert report.failed == 1
    assert report.executed == report.synced == 1
    rows = event_rows(tmp_path)
    assert [r["status"] for r in rows] == ["started", "failed", "started", "completed", "synced"]
    assert "planted condition failure" in rows[1]["error"]


def test_resume_skips_synced_jobs_without_reexecution(tmp_path):
    calls = []

    def executor(item, out):
        calls.append(item.job_id)
        return result_for(item)

    jobs = [job(0), job(1)]
    first = run_batch(jobs, root=tmp_path, executor=executor, sync=lambda *args: None)
    second = run_batch(jobs, root=tmp_path, executor=executor, sync=lambda *args: None)
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
            sync=lambda *args: None,
        )

    report = run_batch(
        [item], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=lambda *args: None,
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
            sync=lambda *args: None,
        )

    report = run_batch(
        [item], root=tmp_path,
        executor=lambda *args: pytest.fail("durable result must not refit"),
        sync=lambda *args: None,
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
        [job(0)], root=tmp_path, executor=executor, sync=lambda *args: None
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

    # A fresh worker can use the synced tree as its checkpoint. The remote
    # event stream intentionally ends at "completed" (the first sync occurs
    # before the local "synced" acknowledgement), which causes one harmless
    # sync retry and never a second fit.
    resumed = run_batch(
        [job(0)],
        root=remote,
        executor=lambda *args: pytest.fail("synced result must not rerun"),
        sync=lambda *args: None,
    )
    assert resumed.executed == 0
    assert resumed.resumed == resumed.synced == 1


def test_manifest_is_immutable_and_plan_changes_get_a_new_batch(tmp_path):
    first = run_batch(
        [job(0)], root=tmp_path, executor=lambda item, out: result_for(item),
        sync=lambda *args: None,
    )
    second = run_batch(
        [job(0), job(1)], root=tmp_path,
        executor=lambda item, out: result_for(item), sync=lambda *args: None,
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
        sync=lambda *args: None,
    )
    batch = tmp_path / manifest_report.batch_id
    # Make a different batch root with an intentionally partial run using a
    # second job, then prove resume will not call its executor over that state.
    other = job(1)
    called = []
    first = run_batch(
        [other], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=lambda *args: None,
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
            sync=lambda *args: None,
        )
    assert called == []


def test_checkpoint_refuses_an_illegal_event_transition(tmp_path):
    item = job(0)
    report = run_batch(
        [item], root=tmp_path, executor=lambda i, out: result_for(i),
        sync=lambda *args: None,
    )
    path = tmp_path / report.batch_id / EVENTS_FILE
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "schema_version": 1,
            "job_id": item.job_id,
            "status": "started",
        }) + "\n")
    with pytest.raises(ValueError, match="illegal transition"):
        run_batch(
            [item], root=tmp_path, executor=lambda i, out: result_for(i),
            sync=lambda *args: None,
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


def test_registered_exp1_launch_refuses_multi_role_fits_before_compute(tmp_path):
    with pytest.raises(ValueError, match="multi-role fit"):
        run_batch(
            experiment_1_jobs(),
            root=tmp_path,
            sync=lambda *args: None,
        )
    assert not tmp_path.exists() or not list(tmp_path.iterdir())
