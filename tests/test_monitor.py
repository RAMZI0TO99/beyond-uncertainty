"""Synthetic refusal tests for the read-only Experiment-1 monitor.

No test in this module trains a model, loads real confirmatory data, computes a
scientific statistic, or creates a label.  Completed job trees use a planted
fit-evidence loader so these tests exercise only monitor orchestration; the
real loader's byte-level scientific-evidence contract is tested separately in
``test_fit_evidence.py``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import (
    DivergentTargetError,
    append_jsonl,
    atomic_write_bytes,
    atomic_write_json,
    sha256_file,
)
from bu.experiments import batch as B
from bu.experiments import monitor as M
from bu.experiments.fit_evidence import (
    FIT_EVIDENCE_FILE,
    FIT_EVIDENCE_SCHEMA_VERSION,
)
from bu.experiments.supervisor import acquire_batch_lease


COMMIT = "b" * 40
STARTED_AT = "2026-08-30T12:00:00Z"
SNAPSHOT_AT = "2026-08-30T12:01:00Z"


@pytest.fixture
def launch(tmp_path):
    roots = {
        name: tmp_path / name
        for name in ("preflight", "output", "staging", "sync", "snapshots")
    }
    for root in roots.values():
        root.mkdir()
    preflight = roots["preflight"] / "preflight_report.json"
    atomic_write_json(preflight, {"synthetic": True, "launch_performed": False})
    lease = acquire_batch_lease(
        roots["output"], lease_name="experiment-1"
    )
    jobs = B.experiment_1_jobs()
    batch_id = B._manifest(jobs)["batch_id"]
    evidence = M.write_launch_start_evidence(
        preflight_path=preflight,
        preflight_sha256=sha256_file(preflight),
        git_commit=COMMIT,
        batch_id=batch_id,
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        attempt_timeout_seconds=3600,
        lease_path=lease.path,
        lease_name=lease.name,
        lease_token=lease.token,
        started_at=STARTED_AT,
    )
    yield SimpleNamespace(
        roots=roots,
        preflight=preflight,
        lease=lease,
        jobs=jobs,
        batch_id=batch_id,
        evidence=evidence,
        local_batch=roots["output"] / batch_id,
        remote_batch=roots["sync"] / batch_id,
    )
    if not lease._released:
        lease.release()


def _execution_digest(job: B.BatchJob) -> str:
    return hashlib.sha256(f"synthetic:{job.job_id}".encode()).hexdigest()


def _result(job: B.BatchJob) -> dict:
    return {
        "run_id": job.config.run_id,
        "config_id": job.config.config_id,
        "unit_id": job.config.unit_id,
        "fit_id": job.config.fit_id,
        "stage": job.stage,
        "seed": job.seed,
        "arm": job.arm,
        "fit_roles": list(job.roles),
        "role_run_ids": {
            role: job.config.__class__(
                unit=job.unit,
                arm=job.config.arm,
                seed=job.seed,
                stage=role,
            ).run_id
            for role in job.roles
        },
        "fit_evidence_schema_version": FIT_EVIDENCE_SCHEMA_VERSION,
        "fit_evidence_file": FIT_EVIDENCE_FILE,
        "fit_evidence_digest": _execution_digest(job),
        "synthetic_monitor_fixture": True,
    }


def _events(launch) -> Path:
    return launch.local_batch / B.EVENTS_FILE


def _append(launch, event: dict) -> None:
    append_jsonl(_events(launch), event)


def _publish_completed(
    launch,
    job: B.BatchJob,
    *,
    resumed: bool = False,
) -> dict:
    result = _result(job)
    job_dir = launch.local_batch / "jobs" / job.job_id
    job_dir.mkdir(parents=True)
    atomic_write_bytes(job_dir / FIT_EVIDENCE_FILE, b"synthetic monitor sidecar\n")
    atomic_write_json(job_dir / B.RESULT_FILE, result)
    if resumed:
        _append(launch, B._event(job, "started"))
        _append(
            launch,
            B._event(
                job,
                "failed",
                error_type="SyntheticInterruption",
                error="planted first-attempt interruption",
            ),
        )
        _append(launch, B._event(job, "started", recovery=True))
        _append(
            launch,
            B._event(
                job,
                "completed",
                result=result,
                result_digest=B._result_digest(result),
                recovered_after_failure=True,
            ),
        )
    else:
        _append(launch, B._event(job, "started"))
        _append(
            launch,
            B._event(
                job,
                "completed",
                result=result,
                result_digest=B._result_digest(result),
            ),
        )
    return result


def _install_fake_loader(
    monkeypatch,
    launch,
    *,
    observed_commit: str = COMMIT,
    calls: list | None = None,
) -> None:
    by_id = {job.job_id: job for job in launch.jobs}

    def fake_loader(path, *, expected_git_commit=None):
        job_dir = Path(path).resolve()
        job = by_id[job_dir.name]
        if calls is not None:
            calls.append((job.job_id, expected_git_commit))
        if expected_git_commit != observed_commit:
            raise ValueError(
                "fit evidence Git commit does not equal the launch-bound commit"
            )
        return SimpleNamespace(
            fit_dir=job_dir,
            fit_id=job.config.fit_id,
            unit_id=job.config.unit_id,
            config_id=job.config.config_id,
            arm=job.arm,
            seed=job.seed,
            roles=job.roles,
            execution_digest=_execution_digest(job),
        )

    monkeypatch.setattr(M, "load_fit_evidence", fake_loader)


def _sync_completed(launch, job: B.BatchJob, result: dict) -> B.SyncReceipt:
    source = launch.local_batch / "jobs" / job.job_id
    destination = launch.remote_batch / "jobs" / job.job_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    receipt = B.SyncReceipt(
        destination=str(destination.resolve()),
        job_id=job.job_id,
        result_digest=B._result_digest(result),
        job_tree_digest=B._job_tree_digest(source),
        copy_evidence_digest=B._copy_evidence_digest(source, destination),
    )
    _append(
        launch,
        B._event(
            job,
            "synced",
            result_digest=B._result_digest(result),
            sync_receipt=receipt.as_record(),
        ),
    )
    atomic_write_bytes(
        launch.remote_batch / B.EVENTS_FILE,
        _events(launch).read_bytes(),
    )
    return receipt


def _snapshot(launch, *, path: Path | None = None) -> dict:
    return M.snapshot_experiment_1(
        launch_start_receipt=launch.evidence.local_path,
        snapshot_path=(
            launch.roots["snapshots"] / "snapshot.json" if path is None else path
        ),
        snapshot_at=SNAPSHOT_AT,
    )


def test_launch_start_evidence_binds_exact_manifest_roots_timeout_and_lease(launch):
    record = launch.evidence.record
    manifest = B._manifest(launch.jobs)
    assert record["batch"]["batch_id"] == manifest["batch_id"]
    assert record["batch"]["job_count"] == 150
    assert record["preflight"]["git_commit"] == COMMIT
    assert record["execution"] == {
        "attempt_timeout_seconds": 3600.0,
        "fresh_process_per_attempt": True,
        "registered_executor_only": True,
    }
    assert record["lease"]["token"] == launch.lease.token
    assert launch.evidence.local_path.read_bytes() == (
        launch.evidence.durable_path.read_bytes()
    )
    assert not os.path.samefile(
        launch.evidence.local_path, launch.evidence.durable_path
    )
    expected_manifest = M._pretty_json_bytes(manifest)
    assert (launch.local_batch / B.MANIFEST_FILE).read_bytes() == expected_manifest
    assert (launch.remote_batch / B.MANIFEST_FILE).read_bytes() == expected_manifest


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("batch", "not exact Experiment-1 batch"),
        ("preflight", "do not match preflight_sha256"),
        ("lease", "different name or token"),
    ],
)
def test_start_evidence_refuses_forged_bindings(tmp_path, change, message):
    roots = {name: tmp_path / name for name in ("preflight", "output", "staging", "sync")}
    for root in roots.values():
        root.mkdir()
    preflight = roots["preflight"] / "preflight_report.json"
    atomic_write_json(preflight, {"synthetic": True})
    lease = acquire_batch_lease(roots["output"], lease_name="experiment-1")
    jobs = B.experiment_1_jobs()
    kwargs = {
        "preflight_path": preflight,
        "preflight_sha256": sha256_file(preflight),
        "git_commit": COMMIT,
        "batch_id": B._manifest(jobs)["batch_id"],
        "output_root": roots["output"],
        "staging_root": roots["staging"],
        "sync_root": roots["sync"],
        "attempt_timeout_seconds": 3600,
        "lease_path": lease.path,
        "lease_name": lease.name,
        "lease_token": lease.token,
        "started_at": STARTED_AT,
    }
    if change == "batch":
        kwargs["batch_id"] = "forged-batch"
    elif change == "preflight":
        kwargs["preflight_sha256"] = "0" * 64
    else:
        kwargs["lease_token"] = "different-token"
    with pytest.raises(ValueError, match=message):
        M.write_launch_start_evidence(**kwargs)
    lease.release()


def test_start_evidence_refuses_overlapping_roots_before_publication(tmp_path):
    root = tmp_path / "root"
    preflight_root = tmp_path / "preflight"
    sync = tmp_path / "sync"
    for path in (root, preflight_root, sync):
        path.mkdir()
    preflight = preflight_root / "preflight_report.json"
    atomic_write_json(preflight, {})
    lease = acquire_batch_lease(root, lease_name="experiment-1")
    with pytest.raises(ValueError, match="alias or overlap"):
        M.write_launch_start_evidence(
            preflight_path=preflight,
            preflight_sha256=sha256_file(preflight),
            git_commit=COMMIT,
            batch_id=B._manifest(B.experiment_1_jobs())["batch_id"],
            output_root=root,
            staging_root=root,
            sync_root=sync,
            attempt_timeout_seconds=3600,
            lease_path=lease.path,
            lease_name=lease.name,
            lease_token=lease.token,
            started_at=STARTED_AT,
        )
    lease.release()


def test_empty_started_batch_is_a_valid_partial_inventory(launch):
    document = _snapshot(launch)
    assert document["status"] == "in_progress"
    assert document["counts"] == {
        "started": 0,
        "completed": 0,
        "resumed": 0,
        "failed": 0,
        "sync_failed": 0,
        "synced": 0,
        "outstanding": 150,
    }
    assert document["latest_state_counts"]["not_started"] == 150
    assert document["scientific_analysis"] == {
        "performed": False,
        "h1_verdict": None,
        "outcome_statistics": None,
    }


def test_partial_batch_reports_exact_started_and_failure_inventory(launch):
    first, second = launch.jobs[:2]
    _append(launch, B._event(first, "started"))
    _append(
        launch,
        B._event(
            first,
            "failed",
            error_type="SyntheticFailure",
            error="planted failure",
        ),
    )
    _append(launch, B._event(second, "started"))
    document = _snapshot(launch)
    assert document["counts"] == {
        "started": 2,
        "completed": 0,
        "resumed": 0,
        "failed": 1,
        "sync_failed": 0,
        "synced": 0,
        "outstanding": 150,
    }
    assert document["latest_state_counts"]["started"] == 1
    assert document["latest_state_counts"]["failed"] == 1
    assert document["latest_state_counts"]["not_started"] == 148


def test_completed_and_resumed_jobs_are_both_fit_verified(monkeypatch, launch):
    first, second = launch.jobs[:2]
    _publish_completed(launch, first)
    _publish_completed(launch, second, resumed=True)
    calls = []
    _install_fake_loader(monkeypatch, launch, calls=calls)
    document = _snapshot(launch)
    assert document["counts"]["completed"] == 2
    assert document["counts"]["resumed"] == 1
    assert document["counts"]["failed"] == 1
    assert calls == [(first.job_id, COMMIT), (second.job_id, COMMIT)]
    assert len(document["verified_completed"]) == 2


def test_wrong_fit_commit_is_refused(monkeypatch, launch):
    _publish_completed(launch, launch.jobs[0])
    _install_fake_loader(monkeypatch, launch, observed_commit="c" * 40)
    with pytest.raises(ValueError, match="Git commit"):
        _snapshot(launch)


def test_unsynced_completed_job_is_reported_not_inflated(monkeypatch, launch):
    job = launch.jobs[0]
    _publish_completed(launch, job)
    _install_fake_loader(monkeypatch, launch)
    document = _snapshot(launch)
    assert document["counts"]["completed"] == 1
    assert document["counts"]["synced"] == 0
    assert document["counts"]["outstanding"] == 150
    assert document["inventories"]["unsynced_completed_job_ids"] == [job.job_id]


def test_sync_failed_is_counted_without_claiming_durable_sync(monkeypatch, launch):
    job = launch.jobs[0]
    result = _publish_completed(launch, job)
    _append(
        launch,
        B._event(
            job,
            "sync_failed",
            error_type="OSError",
            error="planted durable-store outage",
            result_digest=B._result_digest(result),
        ),
    )
    _install_fake_loader(monkeypatch, launch)
    document = _snapshot(launch)
    assert document["counts"]["sync_failed"] == 1
    assert document["counts"]["synced"] == 0
    assert document["latest_state_counts"]["sync_failed"] == 1


def test_valid_sync_requires_tree_receipt_and_remote_terminal_event(monkeypatch, launch):
    job = launch.jobs[0]
    result = _publish_completed(launch, job)
    _sync_completed(launch, job, result)
    _install_fake_loader(monkeypatch, launch)
    document = _snapshot(launch)
    assert document["counts"]["completed"] == 1
    assert document["counts"]["synced"] == 1
    assert document["counts"]["outstanding"] == 149
    assert document["inventories"]["durably_synced_job_ids"] == [job.job_id]
    assert len(document["validated_sync_receipts"]) == 1


def test_local_synced_ack_without_remote_journal_row_stays_outstanding(
    monkeypatch, launch
):
    job = launch.jobs[0]
    result = _publish_completed(launch, job)
    source = launch.local_batch / "jobs" / job.job_id
    destination = launch.remote_batch / "jobs" / job.job_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    receipt = B.SyncReceipt(
        destination=str(destination.resolve()),
        job_id=job.job_id,
        result_digest=B._result_digest(result),
        job_tree_digest=B._job_tree_digest(source),
        copy_evidence_digest=B._copy_evidence_digest(source, destination),
    )
    _append(
        launch,
        B._event(
            job,
            "synced",
            result_digest=B._result_digest(result),
            sync_receipt=receipt.as_record(),
        ),
    )
    # This is the crash window between local acknowledgement and the final
    # journal transport. The receipt/tree are real, but progress is not durable.
    atomic_write_bytes(
        launch.remote_batch / B.EVENTS_FILE,
        b"".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for row in [
                B._event(job, "started"),
                B._event(
                    job,
                    "completed",
                    result=result,
                    result_digest=B._result_digest(result),
                ),
            ]
        ),
    )
    _install_fake_loader(monkeypatch, launch)
    document = _snapshot(launch)
    assert document["latest_state_counts"]["synced"] == 1
    assert document["counts"]["synced"] == 0
    assert document["counts"]["outstanding"] == 150


@pytest.mark.parametrize(
    "event",
    [
        {
            "schema_version": B.BATCH_SCHEMA_VERSION,
            "job_id": "unknown-job",
            "status": "started",
        },
        {
            "schema_version": B.BATCH_SCHEMA_VERSION,
            "job_id": None,
            "status": "started",
        },
    ],
)
def test_unknown_jobs_are_refused(launch, event):
    _append(launch, event)
    with pytest.raises(ValueError, match="unknown job"):
        _snapshot(launch)


def test_forged_event_fields_are_refused(launch):
    event = B._event(launch.jobs[0], "started")
    event["forged_progress"] = 150
    _append(launch, event)
    with pytest.raises(ValueError, match="forged or missing fields"):
        _snapshot(launch)


@pytest.mark.parametrize("statuses", [("started", "started"), ("completed",)])
def test_duplicate_or_illegal_transitions_are_refused(launch, statuses):
    job = launch.jobs[0]
    if statuses == ("completed",):
        result = _result(job)
        _append(
            launch,
            B._event(
                job,
                "completed",
                result=result,
                result_digest=B._result_digest(result),
            ),
        )
    else:
        for status in statuses:
            _append(launch, B._event(job, status))
    with pytest.raises(ValueError, match="illegal transition"):
        _snapshot(launch)


def test_completed_event_with_forged_result_digest_is_refused(launch):
    job = launch.jobs[0]
    result = _result(job)
    _append(launch, B._event(job, "started"))
    _append(
        launch,
        B._event(
            job,
            "completed",
            result=result,
            result_digest="f" * 64,
        ),
    )
    with pytest.raises(ValueError, match="does not match result_digest"):
        _snapshot(launch)


def test_duplicate_synced_receipt_without_re_attestation_is_refused(
    monkeypatch, launch
):
    job = launch.jobs[0]
    result = _publish_completed(launch, job)
    receipt = _sync_completed(launch, job, result)
    _append(
        launch,
        B._event(
            job,
            "synced",
            result_digest=B._result_digest(result),
            sync_receipt=receipt.as_record(),
        ),
    )
    _install_fake_loader(monkeypatch, launch)
    with pytest.raises(ValueError, match="re-attestation"):
        _snapshot(launch)


def test_forged_sync_receipt_is_refused(monkeypatch, launch):
    job = launch.jobs[0]
    result = _publish_completed(launch, job)
    source = launch.local_batch / "jobs" / job.job_id
    destination = launch.remote_batch / "jobs" / job.job_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    receipt = B.SyncReceipt(
        destination=str(destination.resolve()),
        job_id=job.job_id,
        result_digest=B._result_digest(result),
        job_tree_digest=B._job_tree_digest(source),
        copy_evidence_digest="0" * 64,
    )
    _append(
        launch,
        B._event(
            job,
            "synced",
            result_digest=B._result_digest(result),
            sync_receipt=receipt.as_record(),
        ),
    )
    _install_fake_loader(monkeypatch, launch)
    with pytest.raises(ValueError, match="independently materialised"):
        _snapshot(launch)


def test_hard_link_alias_in_job_tree_is_refused(monkeypatch, launch):
    job = launch.jobs[0]
    result = _publish_completed(launch, job)
    source = launch.local_batch / "jobs" / job.job_id
    destination = launch.remote_batch / "jobs" / job.job_id
    destination.mkdir(parents=True)
    for local_file in source.iterdir():
        os.link(local_file, destination / local_file.name)
    receipt = B.SyncReceipt(
        destination=str(destination.resolve()),
        job_id=job.job_id,
        result_digest=B._result_digest(result),
        job_tree_digest="0" * 64,
        copy_evidence_digest="1" * 64,
    )
    _append(
        launch,
        B._event(
            job,
            "synced",
            result_digest=B._result_digest(result),
            sync_receipt=receipt.as_record(),
        ),
    )
    _install_fake_loader(monkeypatch, launch)
    with pytest.raises(ValueError, match="hard-linked"):
        _snapshot(launch)


def test_published_unknown_or_uncheckpointed_job_is_refused(launch):
    planted = launch.local_batch / "jobs" / "unknown-job"
    planted.mkdir(parents=True)
    atomic_write_bytes(planted / "evidence.bin", b"forged\n")
    with pytest.raises(ValueError, match="unknown job"):
        _snapshot(launch)


def test_completed_checkpoint_without_job_tree_is_refused(launch):
    job = launch.jobs[0]
    result = _result(job)
    _append(launch, B._event(job, "started"))
    _append(
        launch,
        B._event(
            job,
            "completed",
            result=result,
            result_digest=B._result_digest(result),
        ),
    )
    with pytest.raises(ValueError, match="no published evidence tree"):
        _snapshot(launch)


def test_torn_final_event_is_ignored_and_digest_reported(launch):
    job = launch.jobs[0]
    _append(launch, B._event(job, "started"))
    fragment = b'{"schema_version":2,"status":"completed"'
    with _events(launch).open("ab") as handle:
        handle.write(fragment)
    document = _snapshot(launch)
    source = document["source_digests"]["events_local"]
    assert document["counts"]["started"] == 1
    assert document["counts"]["completed"] == 0
    assert source["torn_tail_size_bytes"] == len(fragment)
    assert source["torn_tail_sha256"] == hashlib.sha256(fragment).hexdigest()
    assert _events(launch).read_bytes().endswith(fragment)


def test_durable_event_history_must_be_an_exact_local_prefix(launch):
    first, second = launch.jobs[:2]
    _append(launch, B._event(first, "started"))
    atomic_write_bytes(
        launch.remote_batch / B.EVENTS_FILE,
        (
            json.dumps(
                B._event(second, "started"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode(),
    )
    with pytest.raises(ValueError, match="not an exact local prefix"):
        _snapshot(launch)


def test_snapshot_source_digests_and_snapshot_id_are_revalidated(launch):
    path = launch.roots["snapshots"] / "snapshot.json"
    document = _snapshot(launch, path=path)
    assert M.validate_monitor_snapshot(path) == document
    assert document["source_digests"]["manifest_local"]["sha256"] == (
        document["source_digests"]["manifest_durable"]["sha256"]
    )


def test_stale_snapshot_is_refused_after_event_journal_advances(launch):
    path = launch.roots["snapshots"] / "snapshot.json"
    _snapshot(launch, path=path)
    _append(launch, B._event(launch.jobs[0], "started"))
    with pytest.raises(ValueError, match="stale"):
        M.validate_monitor_snapshot(path)


def test_snapshot_is_immutable(launch):
    path = launch.roots["snapshots"] / "snapshot.json"
    _snapshot(launch, path=path)
    with pytest.raises(DivergentTargetError, match="different content"):
        M.snapshot_experiment_1(
            launch_start_receipt=launch.evidence.local_path,
            snapshot_path=path,
            snapshot_at="2026-08-30T12:02:00Z",
        )


def test_cli_writes_snapshot_and_prints_same_document(launch, capsys):
    path = launch.roots["snapshots"] / "cli.json"
    result = M.main(
        [
            "--launch-start-receipt",
            str(launch.evidence.local_path),
            "--snapshot-path",
            str(path),
        ]
    )
    assert result == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == json.loads(path.read_text(encoding="utf-8"))
    assert printed["scientific_analysis"]["performed"] is False


def test_module_exposes_no_executor_or_scientific_verdict_surface():
    assert not hasattr(M, "executor")
    assert not hasattr(M, "run_batch")
    assert not hasattr(M, "run_confirmatory_fit")
    source = Path(M.__file__).read_text(encoding="utf-8")
    assert "def h1" not in source.casefold()
