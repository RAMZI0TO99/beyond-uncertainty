"""Week 6 process-isolation and attempt-staging tests."""

from __future__ import annotations

import errno
import json
import os
import stat
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import bu.experiments.supervisor as supervisor
from bu.experiments.supervisor import (
    RECEIPT_FILE,
    RESULT_FILE,
    DivergentEvidenceError,
    LeaseConflictError,
    acquire_batch_lease,
    run_isolated_attempt,
)


# These callbacks must remain at module scope: Windows ``spawn`` imports this
# module in the child and cannot pickle local functions or lambdas.
def successful_job(attempt_dir: Path, payload: object) -> dict:
    (attempt_dir / "worker_artifact.txt").write_text(
        "created by worker\n", encoding="utf-8"
    )
    return {"payload": payload, "worker_pid": os.getpid()}


def fixed_result_job(attempt_dir: Path, payload: object) -> dict:
    del attempt_dir
    return {"value": payload}


def fixed_result_with_artifact(attempt_dir: Path, payload: object) -> dict:
    artifact_dir = attempt_dir / "evidence"
    artifact_dir.mkdir()
    (artifact_dir / "trace.bin").write_bytes(str(payload).encode("utf-8"))
    return {"value": "same-result"}


def failing_job(attempt_dir: Path, payload: object) -> dict:
    del attempt_dir, payload
    raise RuntimeError("planted Python failure")


def native_exit_job(attempt_dir: Path, payload: object) -> dict:
    del attempt_dir, payload
    os._exit(23)


def slow_job(attempt_dir: Path, payload: object) -> dict:
    del attempt_dir
    time.sleep(float(payload))
    return {"finished": True}


def symlink_job(attempt_dir: Path, payload: object) -> dict:
    """Plant a worker-authored mutable link for the parent to refuse."""

    del payload
    target = attempt_dir / "worker-target.txt"
    target.write_text("mutable target\n", encoding="utf-8")
    os.symlink(target.name, attempt_dir / "worker-link.txt")
    return {"created_link": True}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "component",
    ["", ".", "..", "../escape", "nested/name", r"nested\name", "C:escape"],
)
def test_malicious_job_id_components_are_refused_before_filesystem_writes(
    tmp_path, component
):
    with pytest.raises(ValueError, match="safe nonempty path component|cannot be"):
        run_isolated_attempt(
            fixed_result_job,
            root=tmp_path,
            job_id=component,
            payload="unused",
            timeout_seconds=10,
        )

    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "component",
    ["", ".", "..", "../escape", "nested/name", r"nested\name", "C:escape"],
)
def test_malicious_lease_name_components_are_refused_before_filesystem_writes(
    tmp_path, component
):
    with pytest.raises(ValueError, match="safe nonempty path component|cannot be"):
        acquire_batch_lease(tmp_path, lease_name=component)

    assert not list(tmp_path.iterdir())


def test_worker_authored_symlink_is_refused_before_publication(tmp_path):
    probe_target = tmp_path / "symlink-probe-target"
    probe_link = tmp_path / "symlink-probe-link"
    probe_target.write_text("probe\n", encoding="utf-8")
    try:
        os.symlink(probe_target.name, probe_link)
    except OSError as exc:
        pytest.skip(f"OS does not permit unprivileged symlink creation: {exc}")
    else:
        probe_link.unlink()
        probe_target.unlink()

    with pytest.raises(ValueError, match="contains unsupported link"):
        run_isolated_attempt(
            symlink_job,
            root=tmp_path,
            job_id="worker-link-refused",
            timeout_seconds=10,
        )

    assert not (tmp_path / "jobs" / "worker-link-refused").exists()
    attempts = list((tmp_path / "staging").glob("worker-link-refused.*"))
    assert len(attempts) == 1
    assert (attempts[0] / "worker-link.txt").is_symlink()


def test_windows_reparse_jobs_component_is_refused_before_staging_or_spawn(
    tmp_path, monkeypatch
):
    jobs_root = tmp_path / "jobs"
    jobs_root.mkdir()
    original = Path.lstat

    def marked(path: Path):
        info = original(path)
        if path.absolute() == jobs_root.absolute():
            return SimpleNamespace(
                st_mode=info.st_mode,
                st_file_attributes=getattr(
                    stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
                ),
                st_nlink=info.st_nlink,
            )
        return info

    monkeypatch.setattr(Path, "lstat", marked)
    with pytest.raises(ValueError, match="link/reparse"):
        run_isolated_attempt(
            successful_job,
            root=tmp_path,
            job_id="reparse-refused",
            payload={"seed": 1000},
            timeout_seconds=10,
        )
    assert not (tmp_path / "staging").exists()


def test_success_runs_in_spawned_child_and_parent_publishes_json(tmp_path):
    outcome = run_isolated_attempt(
        successful_job,
        root=tmp_path,
        job_id="condition-001",
        payload={"seed": 1000},
        timeout_seconds=10,
    )

    assert outcome.status == "success"
    assert outcome.succeeded is True
    assert outcome.published is True
    assert outcome.attempt_dir == tmp_path / "jobs" / "condition-001"
    result = read_json(outcome.attempt_dir / RESULT_FILE)
    receipt = read_json(outcome.attempt_dir / RECEIPT_FILE)
    assert result["payload"] == {"seed": 1000}
    assert result["worker_pid"] != os.getpid()
    assert receipt["parent_pid"] == os.getpid()
    assert receipt["child_pid"] == result["worker_pid"]
    assert receipt["status"] == "success"
    assert len(receipt["job_tree_digest"]) == 64
    assert not list((tmp_path / "staging").iterdir())


@pytest.mark.parametrize('exception', [KeyboardInterrupt, SystemExit, RuntimeError])
def test_parent_interruption_stops_and_joins_child_before_lease_release(tmp_path, monkeypatch, exception):
    lease = acquire_batch_lease(tmp_path, lease_name='interruption-test')
    observed = []
    original_stop = supervisor._stop_and_join_worker
    def stop(process):
        assert lease.path.exists()
        original_stop(process)
        observed.append(process)
        assert not process.is_alive() and process.exitcode is not None
    def interrupt(*args):
        raise exception('planted parent interruption')
    monkeypatch.setattr(supervisor, '_stop_and_join_worker', stop)
    monkeypatch.setattr(supervisor, '_wait_for_worker', interrupt)
    with pytest.raises(exception, match='planted parent interruption'):
        try:
            run_isolated_attempt(slow_job, root=tmp_path, job_id='interrupt',
                                 payload=30, timeout_seconds=60)
        finally:
            lease.release()
    assert len(observed) == 1
    assert not lease.path.exists()
    assert not (tmp_path / 'jobs' / 'interrupt').exists()
    receipt = next((tmp_path / 'staging').glob('*/parent_interruption.json'))
    record = read_json(receipt)
    assert record['worker_stopped_and_joined'] is True
    assert record['error_type'] == exception.__name__
    assert not supervisor._WORKERS_REQUIRING_REAP


def test_unconfirmed_worker_cleanup_cannot_release_lease(tmp_path, monkeypatch):
    lease = acquire_batch_lease(tmp_path, lease_name='unconfirmed-worker')
    # A fabricated handle avoids deliberately leaking a real process in a test.
    monkeypatch.setattr(supervisor, '_WORKERS_REQUIRING_REAP', {object()})
    with pytest.raises(LeaseConflictError, match='cleanup is incomplete'):
        lease.release()
    assert lease.path.exists()
    assert not list(lease.history_dir.glob('*.released.json'))
    supervisor._WORKERS_REQUIRING_REAP.clear()
    lease.release()


def test_cleanup_escalates_to_kill_and_still_checks_actual_death():
    class Worker:
        pid = 123456
        exitcode = None
        alive = True
        stopped = False
        def is_alive(self):
            return self.alive
        def terminate(self):
            self.stopped = True
        def join(self, timeout):
            assert timeout <= 2
        def kill(self):
            assert self.stopped
            self.alive, self.exitcode = False, -9
    worker = Worker()
    supervisor._stop_and_join_worker(worker)
    assert not worker.is_alive() and worker.exitcode == -9
    worker = Worker()
    worker.kill = lambda: None
    with pytest.raises(RuntimeError, match='did not stop'):
        supervisor._stop_and_join_worker(worker)


def test_separate_staging_root_publishes_only_to_output_root(tmp_path):
    output_root = tmp_path / "output"
    staging_root = tmp_path / "external-staging"

    outcome = run_isolated_attempt(
        successful_job,
        root=output_root,
        staging_root=staging_root,
        job_id="separate-storage",
        payload={"seed": 1000},
        timeout_seconds=10,
    )

    canonical = output_root / "jobs" / "separate-storage"
    assert outcome.canonical_dir == canonical.resolve()
    assert outcome.attempt_dir == canonical.resolve()
    assert (canonical / "worker_artifact.txt").is_file()
    assert not (output_root / "staging").exists()
    assert not list((staging_root / "staging").iterdir())
    assert not (staging_root / "quarantine").exists()


@pytest.mark.parametrize("layout", ["same", "staging-child", "output-child"])
def test_separate_staging_root_must_not_overlap_output(tmp_path, layout):
    if layout == "same":
        output_root = tmp_path / "shared"
        staging_root = output_root
    elif layout == "staging-child":
        output_root = tmp_path / "output"
        staging_root = output_root / "scratch"
    else:
        staging_root = tmp_path / "scratch"
        output_root = staging_root / "output"

    with pytest.raises(ValueError, match="distinct, non-overlapping"):
        run_isolated_attempt(
            fixed_result_job,
            root=output_root,
            staging_root=staging_root,
            job_id="overlap-refused",
            payload="unused",
            timeout_seconds=10,
        )

    assert not list(tmp_path.rglob("attempt.json"))


def test_separate_staging_root_must_share_output_filesystem_volume(
    tmp_path, monkeypatch
):
    output_root = tmp_path / "output"
    staging_root = tmp_path / "external-staging"

    def planted_volume_identity(path: Path) -> tuple[int, str]:
        if path.resolve() == output_root.resolve():
            return 101, "volume-output"
        return 202, "volume-staging"

    monkeypatch.setattr(
        supervisor, "_filesystem_identity", planted_volume_identity
    )
    with pytest.raises(ValueError, match="same filesystem volume"):
        run_isolated_attempt(
            fixed_result_job,
            root=output_root,
            staging_root=staging_root,
            job_id="cross-volume-refused",
            payload="unused",
            timeout_seconds=10,
        )

    assert not list(tmp_path.rglob("attempt.json"))
    assert not (output_root / "jobs").exists()


def test_runtime_cross_volume_publish_error_is_quarantined_and_explicit(
    tmp_path, monkeypatch
):
    output_root = tmp_path / "output"
    staging_root = tmp_path / "external-staging"
    real_replace = os.replace

    def planted_cross_volume_replace(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        if (
            source_path.parent == (staging_root / "staging").resolve()
            and destination_path.parent == output_root / "jobs"
        ):
            raise OSError(errno.EXDEV, "planted cross-volume move")
        return real_replace(source, destination)

    monkeypatch.setattr(supervisor.os, "replace", planted_cross_volume_replace)
    with pytest.raises(
        DivergentEvidenceError, match="must share one volume"
    ) as caught:
        run_isolated_attempt(
            fixed_result_job,
            root=output_root,
            staging_root=staging_root,
            job_id="runtime-cross-volume",
            payload="preserved",
            timeout_seconds=10,
        )

    assert caught.value.quarantine_dir.parent == staging_root / "quarantine"
    assert read_json(caught.value.quarantine_dir / RESULT_FILE) == {
        "value": "preserved"
    }
    assert not (output_root / "jobs" / "runtime-cross-volume").exists()


def test_python_exception_has_distinct_receipt_and_is_quarantined(tmp_path):
    outcome = run_isolated_attempt(
        failing_job,
        root=tmp_path,
        job_id="python-error",
        timeout_seconds=10,
    )

    assert outcome.status == "python_exception"
    assert outcome.error_type == "RuntimeError"
    assert "planted Python failure" in outcome.error
    assert outcome.attempt_dir.parent == tmp_path / "quarantine"
    assert not (tmp_path / "jobs" / "python-error").exists()
    receipt = read_json(outcome.attempt_dir / RECEIPT_FILE)
    assert receipt["status"] == "python_exception"
    assert receipt["error_type"] == "RuntimeError"
    assert "failing_job" in receipt["traceback"]


def test_os_exit_is_classified_as_process_exit_and_quarantined(tmp_path):
    outcome = run_isolated_attempt(
        native_exit_job,
        root=tmp_path,
        job_id="native-exit",
        timeout_seconds=10,
    )

    assert outcome.status == "process_exit"
    assert outcome.exit_code == 23
    assert outcome.error_type == "ProcessExitError"
    assert outcome.attempt_dir.parent == tmp_path / "quarantine"
    receipt = read_json(outcome.attempt_dir / RECEIPT_FILE)
    assert receipt["exit_code"] == 23


def test_timeout_terminates_child_and_has_distinct_receipt(tmp_path):
    started = time.monotonic()
    outcome = run_isolated_attempt(
        slow_job,
        root=tmp_path,
        job_id="timeout",
        payload=5,
        timeout_seconds=0.5,
    )

    assert time.monotonic() - started < 4
    assert outcome.status == "timeout"
    assert outcome.error_type == "TimeoutError"
    assert outcome.attempt_dir.parent == tmp_path / "quarantine"
    assert read_json(outcome.attempt_dir / RECEIPT_FILE)["status"] == "timeout"


def test_failed_attempt_is_quarantined_and_fresh_retry_can_publish(tmp_path):
    failed = run_isolated_attempt(
        failing_job,
        root=tmp_path,
        job_id="retryable",
        timeout_seconds=10,
    )
    succeeded = run_isolated_attempt(
        fixed_result_job,
        root=tmp_path,
        job_id="retryable",
        payload="second-attempt",
        timeout_seconds=10,
    )

    assert failed.status == "python_exception"
    assert succeeded.status == "success"
    assert failed.attempt_token != succeeded.attempt_token
    assert failed.attempt_dir.exists()
    assert succeeded.canonical_dir == tmp_path / "jobs" / "retryable"
    assert read_json(succeeded.canonical_dir / RESULT_FILE) == {
        "value": "second-attempt"
    }


def test_divergent_publish_is_refused_without_overwriting_evidence(tmp_path):
    canonical = tmp_path / "jobs" / "same-job"
    canonical.mkdir(parents=True)
    planted = b'{"value": "existing"}\n'
    (canonical / RESULT_FILE).write_bytes(planted)

    with pytest.raises(DivergentEvidenceError) as caught:
        run_isolated_attempt(
            fixed_result_job,
            root=tmp_path,
            job_id="same-job",
            payload="new",
            timeout_seconds=10,
        )

    assert (canonical / RESULT_FILE).read_bytes() == planted
    quarantine = caught.value.quarantine_dir
    assert quarantine.parent == tmp_path / "quarantine"
    assert read_json(quarantine / RESULT_FILE) == {"value": "new"}
    receipt = read_json(quarantine / RECEIPT_FILE)
    assert receipt["status"] == "publish_refused"
    assert receipt["error_type"] == "DivergentEvidenceError"


def test_duplicate_publication_requires_complete_tree_identity(tmp_path):
    first = run_isolated_attempt(
        fixed_result_with_artifact,
        root=tmp_path,
        job_id="tree-identity",
        payload="original-side-evidence",
        timeout_seconds=10,
    )
    canonical_artifact = first.attempt_dir / "evidence" / "trace.bin"
    planted = canonical_artifact.read_bytes()

    with pytest.raises(DivergentEvidenceError) as caught:
        run_isolated_attempt(
            fixed_result_with_artifact,
            root=tmp_path,
            job_id="tree-identity",
            payload="altered-side-evidence",
            timeout_seconds=10,
        )

    assert canonical_artifact.read_bytes() == planted
    assert read_json(first.attempt_dir / RESULT_FILE) == {
        "value": "same-result"
    }
    refused = caught.value.quarantine_dir
    assert read_json(refused / RESULT_FILE) == {"value": "same-result"}
    assert (refused / "evidence" / "trace.bin").read_bytes() == (
        b"altered-side-evidence"
    )


def test_identical_complete_tree_is_retained_as_safe_duplicate(tmp_path):
    first = run_isolated_attempt(
        fixed_result_with_artifact,
        root=tmp_path,
        job_id="identical-tree",
        payload="same-side-evidence",
        timeout_seconds=10,
    )
    duplicate = run_isolated_attempt(
        fixed_result_with_artifact,
        root=tmp_path,
        job_id="identical-tree",
        payload="same-side-evidence",
        timeout_seconds=10,
    )

    assert first.published is True
    assert duplicate.published is False
    assert duplicate.canonical_dir == first.canonical_dir
    assert duplicate.attempt_dir.parent == tmp_path / "quarantine"
    receipt = read_json(duplicate.attempt_dir / RECEIPT_FILE)
    assert receipt["already_published"] is True
    assert receipt["job_tree_digest"] == read_json(
        first.canonical_dir / RECEIPT_FILE
    )["job_tree_digest"]


def test_concurrent_batch_lease_is_refused_and_release_is_preserved(tmp_path):
    first = acquire_batch_lease(tmp_path, lease_name="experiment-1")
    active = read_json(first.path)
    assert active["pid"] == os.getpid()
    assert active["token"] == first.token
    assert isinstance(active["timestamp"], float)

    with pytest.raises(LeaseConflictError, match="held by pid"):
        acquire_batch_lease(tmp_path, lease_name="experiment-1")

    history = first.release()
    assert history.exists()
    assert read_json(history) == active
    with acquire_batch_lease(tmp_path, lease_name="experiment-1") as second:
        assert second.token != first.token


def test_release_never_overwrites_existing_history(tmp_path):
    lease = acquire_batch_lease(tmp_path, lease_name="protected-history")
    active = lease.path.read_bytes()
    destination = (
        lease.history_dir
        / f"protected-history.{lease.token}.released.json"
    )
    destination.parent.mkdir(parents=True)
    planted = b'{"protected": true}\n'
    destination.write_bytes(planted)

    with pytest.raises(LeaseConflictError, match="refusing to overwrite"):
        lease.release()

    assert destination.read_bytes() == planted
    assert lease.path.read_bytes() == active


def test_old_owner_cannot_release_replacement_owner_lease(tmp_path):
    old = acquire_batch_lease(tmp_path, lease_name="replacement")
    old_record = read_json(old.path)
    old.path.unlink()
    replacement_record = {
        **old_record,
        "pid": 123456,
        "token": "replacement-owner-token",
        "timestamp": time.time(),
    }
    old.path.write_text(json.dumps(replacement_record), encoding="utf-8")

    with pytest.raises(LeaseConflictError, match="another owner"):
        old.release()

    assert read_json(old.path) == replacement_record
    assert not (
        old.history_dir / f"replacement.{old.token}.released.json"
    ).exists()


def test_time_only_stale_recovery_is_disabled_before_filesystem_access(tmp_path):
    root = tmp_path / "does-not-exist"

    with pytest.raises(ValueError, match="time-only stale lease recovery"):
        acquire_batch_lease(root, lease_name="batch", stale_after_seconds=60)

    assert not root.exists()


def test_live_aged_lease_is_never_archived_or_replaced_by_age(tmp_path):
    live = acquire_batch_lease(tmp_path, lease_name="long-running")
    live_record = read_json(live.path)
    live_record["timestamp"] = time.time() - 24 * 60 * 60
    live_record["timestamp_utc"] = "2000-01-01T00:00:00Z"
    live.path.write_text(json.dumps(live_record), encoding="utf-8")
    planted = live.path.read_bytes()

    with pytest.raises(ValueError, match="cannot prove owner death"):
        acquire_batch_lease(
            tmp_path,
            lease_name="long-running",
            stale_after_seconds=1,
        )

    assert live.path.read_bytes() == planted
    assert not live.history_dir.exists()
    assert list((tmp_path / "leases").glob("*.stale.json")) == []

    released = live.release()
    assert read_json(released) == live_record
    with acquire_batch_lease(tmp_path, lease_name="long-running") as next_owner:
        assert next_owner.token != live.token


@pytest.mark.parametrize(
    "timeout", [True, 0, -1, float("inf"), float("nan")]
)
def test_timeout_must_be_finite_and_positive(tmp_path, timeout):
    with pytest.raises(ValueError, match="finite positive"):
        run_isolated_attempt(
            fixed_result_job,
            root=tmp_path,
            job_id="bad-timeout",
            timeout_seconds=timeout,
        )
