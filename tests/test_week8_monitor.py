"""Synthetic operational-only tests for the Week-8 monitor."""

from __future__ import annotations

import json
import stat
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import DivergentTargetError, append_jsonl, atomic_write_json, read_json
from bu.experiments import batch as B
from bu.experiments import preflight as P
from bu.experiments import week7_plan as W7P
from bu.experiments import week8_launch as L
from bu.experiments import week8_monitor as M
from bu.experiments import week8_preflight as PF
from bu.runrecord import GitState


SNAPSHOT_AT = "2026-09-01T12:00:00Z"


@pytest.fixture(scope="module")
def jobs():
    inventory = W7P.configuration_sweep_baseline_jobs()
    unit = inventory[3].unit
    selected = tuple(job for job in inventory if job.unit == unit)
    assert len(selected) == 3
    return selected


@pytest.fixture
def launch(tmp_path, monkeypatch, jobs):
    roots = {
        name: tmp_path / name for name in ("preflight", "output", "staging", "sync")
    }
    roots["monitor"] = tmp_path / "week8-monitor-sweep-002-test"
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

    monkeypatch.setattr(PF, "_input_file", input_file)
    monkeypatch.setattr(
        PF,
        "_batch_jobs",
        lambda document, key: jobs
        if document == {"synthetic": 8} and key == "sweep-002"
        else (_ for _ in ()).throw(ValueError("wrong synthetic batch")),
    )
    PF.run_week8_preflight(
        plan_path=plan,
        batch_key="sweep-002",
        preflight_dir=roots["preflight"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        sync_destination_identity="synthetic-week8-monitor-copy",
    )
    monkeypatch.setattr(
        B,
        "_run_batch",
        lambda selected, **kwargs: B.BatchReport(
            B._manifest(selected)["batch_id"],
            len(selected),
            len(selected),
            0,
            0,
            0,
            0,
        ),
    )
    report = L.launch_week8(
        preflight_report=roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE,
        output_root=roots["output"],
        sync_root=roots["sync"],
    )
    start = Path(report["start"]["local_path"])
    batch_id = report["start"]["record"]["batch"]["batch_id"]
    monkeypatch.setattr(M.M, "_utc_now", lambda: SNAPSHOT_AT)
    return roots, start, jobs, batch_id


def _event(job, status, **extra):
    return {"schema_version": B.BATCH_SCHEMA_VERSION, "job_id": job.job_id,
            "status": status, **extra}


def _journals(launch):
    roots, _, _, batch_id = launch
    return (
        roots["output"] / batch_id / B.EVENTS_FILE,
        roots["sync"] / batch_id / B.EVENTS_FILE,
    )


def _snapshot(launch, name="snapshot.json"):
    roots, start, _, _ = launch
    return M.snapshot_week8_batch(
        launch_start_receipt=start,
        snapshot_path=roots["monitor"] / name,
    )


def test_empty_snapshot_has_only_operational_inventory(launch):
    document = _snapshot(launch)
    assert document["status"] == "in_progress"
    assert document["counts"] == {
        "started": 0,
        "completed": 0,
        "resumed": 0,
        "failed_events": 0,
        "sync_failed_events": 0,
        "synced": 0,
        "outstanding": 3,
    }
    assert document["batch"]["git_commit"] == "b" * 40
    assert document["snapshot_at"] == SNAPSHOT_AT
    assert document["monitor_scope"]["level"] == "batch"
    assert document["monitor_scope"]["launch_attempt_count"] == 1
    assert document["monitor_scope"]["launch_attempts"][0]["lease_evidence"][
        "state"
    ] == "released"
    assert document["plan_inventory_only"]["train_batch_sizes"] == [128]
    assert launch[0]["monitor"].resolve() in PF._immutable_source_roots()
    assert document["scientific_analysis"] == {
        "performed": False, "outcomes": None, "labels": None, "h2_verdict": None,
    }
    encoded = json.dumps(document, sort_keys=True)
    for forbidden in ("movement_error", "disagreement_ratio", "observed_label"):
        assert forbidden not in encoded


def test_partial_local_event_prefix_counts_started_without_claiming_completion(launch):
    local, _ = _journals(launch)
    append_jsonl(local, _event(launch[2][0], "started"))
    document = _snapshot(launch)
    assert document["counts"]["started"] == 1
    assert document["counts"]["completed"] == 0
    assert document["counts"]["synced"] == 0
    assert document["latest_state_counts"]["started"] == 1
    assert document["latest_state_counts"]["not_started"] == 2


def test_durable_journal_must_be_exact_row_and_byte_prefix(launch):
    local, durable = _journals(launch)
    first, second = launch[2][:2]
    append_jsonl(local, _event(first, "started"))
    append_jsonl(local, _event(second, "started"))
    append_jsonl(durable, _event(second, "started"))
    with pytest.raises(ValueError, match="exact local prefix"):
        _snapshot(launch)


def test_unknown_job_or_forged_event_fields_refuse(launch):
    local, _ = _journals(launch)
    append_jsonl(local, {
        "schema_version": B.BATCH_SCHEMA_VERSION,
        "job_id": "unknown-s1000",
        "status": "started",
    })
    with pytest.raises(ValueError, match="unknown job"):
        _snapshot(launch)


def test_completed_validation_receives_exact_commit_and_sweep_anchor(launch, monkeypatch):
    local, durable = _journals(launch)
    job = launch[2][0]
    result = {
        "run_id": job.config.run_id,
        "config_id": job.config.config_id,
        "unit_id": job.config.unit_id,
        "fit_id": job.config.fit_id,
        "stage": job.stage,
        "seed": job.seed,
        "arm": job.arm,
        "fit_roles": list(job.roles),
        "role_run_ids": {role: job.config.run_id for role in job.roles},
    }
    digest = B._result_digest(result)
    rows = [
        _event(job, "started"),
        _event(job, "completed", result=result, result_digest=digest),
        _event(job, "synced", result_digest=digest, sync_receipt={
            "schema_version": B.SYNC_RECEIPT_SCHEMA_VERSION,
            "destination": str(launch[0]["sync"] / launch[3] / "jobs" / job.job_id),
            "job_id": job.job_id,
            "result_digest": digest,
            "job_tree_digest": "1" * 64,
            "copy_evidence_digest": "2" * 64,
        }),
    ]
    for row in rows:
        append_jsonl(local, row)
        append_jsonl(durable, row)
    calls = []

    def completed(**kwargs):
        calls.append(("completed", kwargs["expected_commit"]))
        return ({job.job_id: {
            "job_id": job.job_id,
            "result_digest": digest,
            "fit_evidence_digest": "3" * 64,
            "job_tree_digest": "1" * 64,
            "local_path": str(launch[0]["output"] / launch[3] / "jobs" / job.job_id),
        }}, [job.job_id])

    monkeypatch.setattr(M.M, "_load_completed_jobs", completed)
    monkeypatch.setattr(
        M.M, "_validate_sync_events",
        lambda **kwargs: ([], {job.job_id}),
    )
    monkeypatch.setattr(M.M, "_re_attest_snapshot_sources", lambda **kwargs: None)
    monkeypatch.setattr(
        M, "validate_sweep_pool_anchors",
        lambda path, *, expected_git_commit: calls.append(
            ("anchors", expected_git_commit)
        ),
    )
    document = _snapshot(launch)
    assert calls == [("completed", "b" * 40), ("anchors", "b" * 40)]
    assert document["counts"]["completed"] == 1
    assert document["counts"]["synced"] == 1
    assert document["status"] == "in_progress"


def test_start_execution_boundary_and_manifest_tampering_refuse(launch):
    roots, start, _, batch_id = launch
    durable = Path(read_json(start)["copies"]["durable_path"])
    document = read_json(start)
    document["execution"]["cpu_only"] = False
    raw = M.L._pretty_json_bytes(document)
    start.write_bytes(raw)
    durable.write_bytes(raw)
    with pytest.raises(ValueError, match="weakened"):
        _snapshot(launch)


@pytest.mark.parametrize("timeout", [30.0, 3600])
def test_monitor_refuses_nonfrozen_launch_timeout(launch, timeout):
    _, start, _, _ = launch
    durable = Path(read_json(start)["copies"]["durable_path"])
    document = read_json(start)
    document["execution"]["attempt_timeout_seconds"] = timeout
    raw = M.L._pretty_json_bytes(document)
    start.write_bytes(raw)
    durable.write_bytes(raw)
    with pytest.raises(ValueError, match="weakened"):
        _snapshot(launch, "wrong-timeout.json")


def test_monitor_independently_requires_exact_storage_floor(launch, monkeypatch):
    original = PF.validate_week8_preflight

    def lowered(*args, **kwargs):
        validated = original(*args, **kwargs)
        report = dict(validated.report)
        storage = dict(report["storage"])
        storage["minimum_free_bytes"] = PF.WEEK8_MINIMUM_FREE_BYTES - 1
        report["storage"] = storage
        return replace(validated, report=report)

    monkeypatch.setattr(PF, "validate_week8_preflight", lowered)
    with pytest.raises(ValueError, match="exact 8-GiB"):
        _snapshot(launch, "wrong-floor.json")


def test_snapshot_revalidation_detects_later_event_and_immutable_destination(launch):
    roots, _, jobs, _ = launch
    path = roots["monitor"] / "stable.json"
    document = M.snapshot_week8_batch(
        launch_start_receipt=launch[1], snapshot_path=path
    )
    assert M.validate_week8_monitor_snapshot(path) == document
    local, _ = _journals(launch)
    append_jsonl(local, _event(jobs[0], "started"))
    with pytest.raises(ValueError, match="stale|changed"):
        M.validate_week8_monitor_snapshot(path)
    with pytest.raises(DivergentTargetError):
        M.snapshot_week8_batch(
            launch_start_receipt=launch[1],
            snapshot_path=path,
        )


def test_public_snapshot_timestamp_is_not_caller_controlled(launch):
    with pytest.raises(TypeError, match="snapshot_at"):
        M.snapshot_week8_batch(
            launch_start_receipt=launch[1],
            snapshot_path=launch[0]["monitor"] / "caller-time.json",
            snapshot_at="2000-01-01T00:00:00Z",
        )


@pytest.mark.parametrize("root_name", ["preflight", "output", "staging", "sync"])
def test_monitor_refuses_execution_roots_before_write(launch, root_name):
    target = launch[0][root_name] / "monitor.json"
    with pytest.raises(ValueError, match="dedicated direct project root"):
        M.snapshot_week8_batch(
            launch_start_receipt=launch[1], snapshot_path=target
        )
    assert not target.exists()


def test_monitor_refuses_non_dedicated_or_reparse_root_before_write(
    launch, monkeypatch
):
    roots = launch[0]
    unrelated = roots["preflight"].parent / "ordinary-directory"
    unrelated.mkdir()
    with pytest.raises(ValueError, match="dedicated direct project root"):
        M.snapshot_week8_batch(
            launch_start_receipt=launch[1],
            snapshot_path=unrelated / "snapshot.json",
        )

    target = roots["monitor"].absolute()
    original = Path.lstat

    def marked(path: Path):
        info = original(path)
        if path.absolute() == target:
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
        M.snapshot_week8_batch(
            launch_start_receipt=launch[1],
            snapshot_path=roots["monitor"] / "reparse.json",
        )
    assert not (roots["monitor"] / "reparse.json").exists()


def test_monitor_inventories_every_restart_and_archived_lease(launch):
    roots, first_start, _, _ = launch
    second = L.launch_week8(
        preflight_report=roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE,
        output_root=roots["output"],
        sync_root=roots["sync"],
    )
    second_token = second["start"]["record"]["lease"]["token"]
    document = M.snapshot_week8_batch(
        launch_start_receipt=first_start,
        snapshot_path=roots["monitor"] / "restart-chain.json",
    )
    scope = document["monitor_scope"]
    assert scope["level"] == "batch"
    assert scope["launch_attempt_count"] == 2
    assert scope["selected_anchor_lease_token"] == read_json(first_start)["lease"][
        "token"
    ]
    assert {row["lease_token"] for row in scope["launch_attempts"]} == {
        read_json(first_start)["lease"]["token"],
        second_token,
    }
    assert {row["lease_evidence"]["state"] for row in scope["launch_attempts"]} == {
        "released"
    }


def test_monitor_refuses_start_without_active_or_archived_lease(launch):
    start = read_json(launch[1])
    token = start["lease"]["token"]
    history = (
        launch[0]["preflight"].parent
        / PF.COMMON_CONTROL_DIRECTORY
        / "leases"
        / "history"
        / f"{L.WEEK8_LEASE_NAME}.{token}.released.json"
    )
    history.unlink()
    with pytest.raises(ValueError, match="exactly one active or archived lease"):
        _snapshot(launch, "missing-lease.json")
