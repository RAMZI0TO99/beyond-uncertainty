"""Read-only operational monitor for one exact Week-8 baseline batch.

Snapshots validate the launch, immutable manifest, append-only local/durable
event prefix, completed fit provenance, sync receipts, and execution commit.
They contain operational counts and evidence digests only: no outcome scalar,
repair label, scientific comparison, or H2 verdict is computed or copied.
"""

from __future__ import annotations

import argparse
import os
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_file
from . import batch as B
from . import launch as L
from . import monitor as M
from . import week8_launch as W8L
from . import week8_preflight as PF
from .fit_evidence import validate_sweep_pool_anchors


WEEK8_MONITOR_SCHEMA_VERSION = 2
MONITOR_ROOT_PREFIXES = {
    "exp2b": "week8-monitor-exp2b-",
    "sweep-002": "week8-monitor-sweep-002-",
}


def _load_launch_start(
    path: str | Path,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    requested = M._plain_file(path, what="Week-8 launch-start receipt")
    raw = requested.read_bytes()
    record = M._strict_keys(
        read_json(requested),
        {
            "week8_launch_start_schema_version",
            "status",
            "started_at",
            "preflight",
            "binding_sha256",
            "batch_key",
            "batch",
            "storage",
            "execution",
            "lease",
            "copies",
            "scientific_analysis_performed",
        },
        what="Week-8 launch-start receipt",
    )
    if raw != L._pretty_json_bytes(record):
        raise ValueError("Week-8 launch-start receipt is not canonical immutable JSON")
    if (
        type(record["week8_launch_start_schema_version"]) is not int
        or record["week8_launch_start_schema_version"] != W8L.WEEK8_LAUNCH_SCHEMA_VERSION
        or record["status"] != "launch_started"
        or record["scientific_analysis_performed"] is not False
    ):
        raise ValueError("Week-8 launch-start receipt has the wrong ready schema")
    M._require_timestamp(record["started_at"], what="started_at")
    M._require_sha256(record["binding_sha256"], what="binding_sha256")

    storage = M._strict_keys(
        record["storage"],
        {"preflight", "output", "staging", "sync"},
        what="storage roots",
    )
    roots = {
        name: PF._project_path(value, what=f"{name} root", directory=True)
        for name, value in storage.items()
    }
    if storage != {name: str(root) for name, root in roots.items()}:
        raise ValueError("Week-8 launch-start storage paths are not canonical")
    preflight = M._strict_keys(
        record["preflight"], {"path", "sha256", "git_commit"}, what="preflight"
    )
    M._require_sha256(preflight["sha256"], what="preflight sha256")
    commit = M._require_commit(preflight["git_commit"], what="preflight commit")
    validated = PF.validate_week8_preflight(
        preflight["path"], output_root=roots["output"], sync_root=roots["sync"]
    )
    if (
        validated.report_sha256 != preflight["sha256"]
        or sha256_file(validated.report_path) != preflight["sha256"]
        or validated.git_commit != commit
        or validated.report["binding_sha256"] != record["binding_sha256"]
        or validated.report["batch_key"] != record["batch_key"]
        or dict(validated.roots) != roots
    ):
        raise ValueError("Week-8 launch start disagrees with its bound preflight")
    floor = validated.report["storage"].get("minimum_free_bytes")
    if type(floor) is not int or floor != PF.WEEK8_MINIMUM_FREE_BYTES:
        raise ValueError("Week-8 monitor requires the exact 8-GiB storage floor")

    jobs = validated.jobs
    manifest = B._manifest(jobs)
    manifest_bytes = L._pretty_json_bytes(manifest)
    batch = M._strict_keys(
        record["batch"],
        {"batch_id", "job_count", "manifest_sha256"},
        what="batch",
    )
    if (
        batch["batch_id"] != manifest["batch_id"]
        or type(batch["job_count"]) is not int
        or batch["job_count"] != len(jobs)
        or batch["manifest_sha256"]
        != M.sha256_bytes(manifest_bytes)
    ):
        raise ValueError("Week-8 launch-start batch differs from the exact manifest")

    execution = M._strict_keys(
        record["execution"],
        {
            "attempt_timeout_seconds",
            "fresh_process_per_attempt",
            "registered_executor_only",
            "cpu_only",
            "prefit_storage_check_before_each_new_child",
            "sweep_anchors_required",
        },
        what="execution boundary",
    )
    timeout = M._positive_number(
        execution["attempt_timeout_seconds"], what="attempt_timeout_seconds"
    )
    expected_sweep = any(job.stage == "config_sweep" for job in jobs)
    if (
        type(execution["attempt_timeout_seconds"]) is not float
        or timeout != W8L.WEEK8_ATTEMPT_TIMEOUT_SECONDS
        or execution["fresh_process_per_attempt"] is not True
        or execution["registered_executor_only"] is not True
        or execution["cpu_only"] is not True
        or execution["prefit_storage_check_before_each_new_child"] is not True
        or execution["sweep_anchors_required"] is not expected_sweep
    ):
        raise ValueError("Week-8 launch-start execution boundary was weakened")

    lease = M._strict_keys(
        record["lease"],
        {
            "name",
            "token",
            "path",
            "sha256",
            "common_control_root",
            "age_recovery_allowed",
        },
        what="lease",
    )
    if (
        lease["name"] != W8L.WEEK8_LEASE_NAME
        or lease["common_control_root"] != str(PF._control_root())
        or lease["path"]
        != str(
            PF._control_root()
            / "leases"
            / f"{W8L.WEEK8_LEASE_NAME}.lease.json"
        )
        or lease["age_recovery_allowed"] is not False
    ):
        raise ValueError("Week-8 launch did not use the common no-age-recovery lease")
    M._require_component(lease["token"], what="lease token")
    M._require_sha256(lease["sha256"], what="lease sha256")

    local_batch = roots["output"] / manifest["batch_id"]
    durable_batch = roots["sync"] / manifest["batch_id"]
    copies = M._strict_keys(
        record["copies"], {"local_path", "durable_path"}, what="start copies"
    )
    local = M._plain_file(copies["local_path"], what="local Week-8 start receipt")
    durable = M._plain_file(
        copies["durable_path"], what="durable Week-8 start receipt"
    )
    expected_local = (
        local_batch / W8L.WEEK8_START_DIRECTORY / f"{lease['token']}.json"
    )
    expected_durable = (
        durable_batch / W8L.WEEK8_START_DIRECTORY / f"{lease['token']}.json"
    )
    if local != expected_local or durable != expected_durable:
        raise ValueError("Week-8 launch-start copies are outside their bound roots")
    if requested not in {local, durable}:
        raise ValueError("requested Week-8 start receipt is not a bound copy")
    if os.path.samefile(local, durable) or local.read_bytes() != raw or durable.read_bytes() != raw:
        raise ValueError("Week-8 launch-start copies alias or diverge")

    local_manifest = M._plain_file(
        local_batch / B.MANIFEST_FILE, what="local Week-8 manifest"
    )
    durable_manifest = M._plain_file(
        durable_batch / B.MANIFEST_FILE, what="durable Week-8 manifest"
    )
    if (
        local_manifest.read_bytes() != manifest_bytes
        or durable_manifest.read_bytes() != manifest_bytes
        or os.path.samefile(local_manifest, durable_manifest)
    ):
        raise ValueError("Week-8 manifest copies differ, alias, or are not exact")

    return requested, record, {
        "validated": validated,
        "jobs": jobs,
        "manifest": manifest,
        "commit": commit,
        "roots": roots,
        "local_receipt": local,
        "durable_receipt": durable,
        "local_manifest": local_manifest,
        "durable_manifest": durable_manifest,
    }


def _validated_lease_record(
    path: Path, *, expected_token: str | None
) -> tuple[dict[str, Any], str]:
    evidence = PF._project_path(path, what="Week-8 lease evidence", directory=False)
    raw = evidence.read_bytes()
    record = M._strict_keys(
        read_json(evidence),
        {"schema_version", "lease_name", "pid", "token", "timestamp", "timestamp_utc"},
        what="Week-8 lease evidence",
    )
    if raw != L._pretty_json_bytes(record):
        raise ValueError("Week-8 lease evidence is not canonical immutable JSON")
    if (
        record["schema_version"] != M.SUPERVISOR_SCHEMA_VERSION
        or record["lease_name"] != W8L.WEEK8_LEASE_NAME
        or type(record["pid"]) is not int
        or record["pid"] <= 0
    ):
        raise ValueError("Week-8 lease evidence has the wrong owner schema")
    token = M._require_component(record["token"], what="lease evidence token")
    if expected_token is not None and token != expected_token:
        raise ValueError("Week-8 lease evidence belongs to a different token")
    M._positive_number(record["timestamp"], what="lease acquisition timestamp")
    M._require_timestamp(record["timestamp_utc"], what="lease timestamp_utc")
    return record, sha256_file(evidence)


def _lease_evidence_for_start(start: Mapping[str, Any]) -> dict[str, Any]:
    token = start["lease"]["token"]
    expected_sha = start["lease"]["sha256"]
    lease_root = PF._control_root() / "leases"
    active = lease_root / f"{W8L.WEEK8_LEASE_NAME}.lease.json"
    released = (
        lease_root
        / "history"
        / f"{W8L.WEEK8_LEASE_NAME}.{token}.released.json"
    )
    matches: list[tuple[str, Path, str]] = []
    if os.path.lexists(active):
        active_record, active_sha = _validated_lease_record(
            active, expected_token=None
        )
        if active_record["token"] == token:
            if active_sha != expected_sha:
                raise ValueError("active Week-8 lease digest differs from launch start")
            matches.append(("active", active, active_sha))
    if os.path.lexists(released):
        _, released_sha = _validated_lease_record(
            released, expected_token=token
        )
        if released_sha != expected_sha:
            raise ValueError("archived Week-8 lease digest differs from launch start")
        matches.append(("released", released, released_sha))
    if len(matches) != 1:
        raise ValueError(
            "Week-8 launch start must bind exactly one active or archived lease"
        )
    state, path, digest = matches[0]
    return {"state": state, "path": str(path), "sha256": digest}


def _start_inventory(directory: Path, *, what: str) -> dict[str, Path]:
    root = M._plain_directory(directory, what=what)
    inventory: dict[str, Path] = {}
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if child.suffix != ".json":
            raise ValueError(f"{what} contains a non-receipt entry: {child}")
        token = M._require_component(child.stem, what=f"{what} token")
        if token in inventory:
            raise ValueError(f"{what} contains a duplicate launch token")
        inventory[token] = M._plain_file(child, what=f"{what} receipt")
    if not inventory:
        raise ValueError(f"{what} contains no launch-start receipts")
    return inventory


def _discover_launch_attempts(
    selected_start: Mapping[str, Any], selected_context: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Validate every locally and durably discoverable start for this batch."""
    batch_id = selected_context["manifest"]["batch_id"]
    local_dir = (
        selected_context["roots"]["output"]
        / batch_id
        / W8L.WEEK8_START_DIRECTORY
    )
    durable_dir = (
        selected_context["roots"]["sync"]
        / batch_id
        / W8L.WEEK8_START_DIRECTORY
    )
    local = _start_inventory(local_dir, what="local Week-8 start inventory")
    durable = _start_inventory(durable_dir, what="durable Week-8 start inventory")
    if set(local) != set(durable):
        raise ValueError("local and durable Week-8 launch-attempt inventories differ")
    selected_token = selected_start["lease"]["token"]
    if selected_token not in local:
        raise ValueError("selected Week-8 launch start is absent from batch inventory")

    attempts: list[dict[str, Any]] = []
    active_count = 0
    for token in sorted(local):
        _, record, context = _load_launch_start(local[token])
        if (
            record["lease"]["token"] != token
            or context["durable_receipt"] != durable[token]
            or record["batch_key"] != selected_start["batch_key"]
            or record["binding_sha256"] != selected_start["binding_sha256"]
            or record["preflight"] != selected_start["preflight"]
            or record["storage"] != selected_start["storage"]
            or record["batch"] != selected_start["batch"]
            or context["manifest"] != selected_context["manifest"]
        ):
            raise ValueError("Week-8 launch attempts do not bind one exact batch")
        lease_evidence = _lease_evidence_for_start(record)
        active_count += lease_evidence["state"] == "active"
        attempts.append(
            {
                "lease_token": token,
                "started_at": record["started_at"],
                "local_path": str(local[token]),
                "durable_path": str(durable[token]),
                "sha256": sha256_file(local[token]),
                "lease_evidence": lease_evidence,
            }
        )
    if active_count > 1:
        raise ValueError("more than one discoverable Week-8 attempt claims an active lease")
    return sorted(attempts, key=lambda row: (row["started_at"], row["lease_token"]))


def _monitor_destination(
    snapshot_path: str | Path,
    *,
    start: Mapping[str, Any],
    context: Mapping[str, Any],
) -> Path:
    """Require one dedicated project-local, link-free monitor root."""
    candidate = Path(snapshot_path).absolute()
    if candidate.suffix != ".json":
        raise ValueError("Week-8 monitor snapshot must use a .json filename")
    M._require_component(candidate.name, what="Week-8 monitor snapshot filename")
    root = PF._project_path(
        candidate.parent, what="dedicated Week-8 monitor root", directory=True
    )
    workspace = PF.WORKSPACE_ROOT.resolve(strict=True)
    prefix = MONITOR_ROOT_PREFIXES.get(start["batch_key"])
    if (
        root.parent != workspace
        or prefix is None
        or not root.name.startswith(prefix)
        or root.name == prefix
    ):
        raise ValueError(
            "Week-8 monitor destination must be a dedicated direct project root "
            "for the exact batch"
        )
    if candidate.parent != root:
        raise ValueError("Week-8 monitor snapshot path is not canonical")
    if os.path.lexists(candidate):
        checked = PF._project_path(
            candidate, what="existing Week-8 monitor snapshot", directory=False
        )
        if checked != candidate:
            raise ValueError("Week-8 monitor snapshot path is not canonical")

    plan_file = PF._project_path(
        context["validated"].report["plan"]["path"],
        what="bound Week-8 plan",
        directory=False,
    )
    immutable_sources = tuple(
        path for path in PF._immutable_source_roots() if path != root
    )
    protected = [
        plan_file,
        context["validated"].report_path,
        PF._control_root(),
        *context["roots"].values(),
        *immutable_sources,
    ]
    for claim in PF._read_root_claims().values():
        protected.extend(claim.values())
    if any(M._paths_overlap(root, path) for path in protected):
        raise ValueError(
            "dedicated Week-8 monitor root overlaps plan, execution, control, "
            "or historical evidence"
        )
    for child in root.iterdir():
        if child.suffix != ".json":
            raise ValueError("dedicated Week-8 monitor root contains non-monitor data")
        M._require_component(child.name, what="monitor-root entry")
        entry = PF._project_path(child, what="monitor-root entry", directory=False)
        entry_document = read_json(entry)
        if (
            entry.read_bytes() != L._pretty_json_bytes(entry_document)
            or type(entry_document) is not dict
            or entry_document.get("week8_monitor_schema_version")
            != WEEK8_MONITOR_SCHEMA_VERSION
            or type(entry_document.get("batch")) is not dict
            or entry_document["batch"].get("batch_key") != start["batch_key"]
        ):
            raise ValueError(
                "dedicated Week-8 monitor root contains non-monitor evidence"
            )
    return candidate


def _snapshot_material(
    launch_start_receipt: str | Path,
    *,
    snapshot_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _, start, context = _load_launch_start(launch_start_receipt)
    attempts = _discover_launch_attempts(start, context)
    timestamp = M._require_timestamp(
        M._utc_now() if snapshot_at is None else snapshot_at, what="snapshot_at"
    )
    jobs: tuple[B.BatchJob, ...] = context["jobs"]
    known = {job.job_id for job in jobs}
    batch_id = context["manifest"]["batch_id"]
    local_batch = context["roots"]["output"] / batch_id
    durable_batch = context["roots"]["sync"] / batch_id
    rows, local_events, local_committed = M._event_source(
        local_batch / B.EVENTS_FILE, known=known
    )
    remote_rows, durable_events, durable_committed = M._event_source(
        durable_batch / B.EVENTS_FILE, known=known
    )
    if durable_events["torn_tail_size_bytes"] != 0:
        raise ValueError("durable Week-8 event journal has an unterminated tail")
    if not local_committed.startswith(durable_committed):
        raise ValueError("durable Week-8 event bytes are not an exact local prefix")
    if list(rows[: len(remote_rows)]) != list(remote_rows):
        raise ValueError("durable Week-8 event rows are not an exact local prefix")

    verified, published = M._load_completed_jobs(
        batch_dir=local_batch,
        jobs=jobs,
        rows=rows,
        expected_commit=context["commit"],
    )
    for job in jobs:
        if job.job_id in verified and job.stage == "config_sweep":
            validate_sweep_pool_anchors(
                local_batch / "jobs" / job.job_id,
                expected_git_commit=context["commit"],
            )
    receipts, durably_synced = M._validate_sync_events(
        batch_dir=local_batch,
        sync_batch_dir=durable_batch,
        jobs=jobs,
        rows=rows,
        remote_rows=remote_rows,
        verified=verified,
    )

    latest: dict[str, str] = {}
    started: set[str] = set()
    completed: set[str] = set()
    for event in rows:
        latest[event["job_id"]] = event["status"]
        if event["status"] == "started":
            started.add(event["job_id"])
        elif event["status"] == "completed":
            completed.add(event["job_id"])
    resumed = M._explicit_resumed_jobs(rows)
    counts = {
        "started": len(started),
        "completed": len(completed),
        "resumed": len(resumed),
        "failed_events": sum(event["status"] == "failed" for event in rows),
        "sync_failed_events": sum(
            event["status"] == "sync_failed" for event in rows
        ),
        "synced": len(durably_synced),
        "outstanding": len(jobs) - len(durably_synced),
    }
    latest_counts = Counter(latest.values())
    current = {
        name: int(latest_counts.get(name, 0))
        for name in ("started", "completed", "failed", "sync_failed", "synced")
    }
    current["not_started"] = len(jobs) - len(latest)

    sources = {
        "preflight": {
            "path": str(context["validated"].report_path),
            "sha256": context["validated"].report_sha256,
        },
        "launch_start_local": {
            "path": str(context["local_receipt"]),
            "sha256": sha256_file(context["local_receipt"]),
        },
        "launch_start_durable": {
            "path": str(context["durable_receipt"]),
            "sha256": sha256_file(context["durable_receipt"]),
        },
        "manifest_local": {
            "path": str(context["local_manifest"]),
            "sha256": sha256_file(context["local_manifest"]),
        },
        "manifest_durable": {
            "path": str(context["durable_manifest"]),
            "sha256": sha256_file(context["durable_manifest"]),
        },
        "events_local": local_events,
        "events_durable": durable_events,
    }
    M._re_attest_snapshot_sources(
        source_digests=sources, verified=verified, receipts=receipts
    )
    seeds = sorted({job.seed for job in jobs})
    payload: dict[str, Any] = {
        "week8_monitor_schema_version": WEEK8_MONITOR_SCHEMA_VERSION,
        "kind": "week8_validated_operational_inventory",
        "snapshot_at": timestamp,
        "status": "complete" if len(durably_synced) == len(jobs) else "in_progress",
        "batch": {
            "batch_key": start["batch_key"],
            "batch_id": batch_id,
            "job_count": len(jobs),
            "manifest_sha256": start["batch"]["manifest_sha256"],
            "git_commit": context["commit"],
        },
        "launch_start": {
            "local_path": str(context["local_receipt"]),
            "durable_path": str(context["durable_receipt"]),
            "sha256": sha256_file(context["local_receipt"]),
            "lease_token": start["lease"]["token"],
        },
        "monitor_scope": {
            "level": "batch",
            "status_applies_to": "all_discoverable_launch_attempts_for_exact_batch",
            "selected_anchor_lease_token": start["lease"]["token"],
            "launch_attempt_count": len(attempts),
            "launch_attempts": attempts,
        },
        "counts": counts,
        "latest_state_counts": current,
        "inventories": {
            "started_job_ids": sorted(started),
            "completed_job_ids": sorted(completed),
            "resumed_job_ids": sorted(resumed),
            "published_job_ids": published,
            "durably_synced_job_ids": sorted(durably_synced),
            "unsynced_completed_job_ids": sorted(completed - durably_synced),
            "active_started_job_ids": sorted(
                job_id for job_id, state in latest.items() if state == "started"
            ),
        },
        "verified_completed": [verified[key] for key in sorted(verified)],
        "validated_sync_receipts": receipts,
        "plan_inventory_only": {
            "unit_count": len({job.config.unit_id for job in jobs}),
            "seed_range": [min(seeds), max(seeds)],
            "arms": sorted({job.arm for job in jobs}),
            "stages": sorted({job.stage for job in jobs}),
            "roles": sorted({role for job in jobs for role in job.roles}),
            "train_batch_sizes": sorted({job.config.train.batch_size for job in jobs}),
        },
        "source_digests": sources,
        "scientific_analysis": {
            "performed": False,
            "outcomes": None,
            "labels": None,
            "h2_verdict": None,
        },
    }
    payload["snapshot_id"] = M._canonical_digest(payload)
    return payload, start, context


def _snapshot_document(
    launch_start_receipt: str | Path,
    *,
    snapshot_at: str | None = None,
) -> dict[str, Any]:
    """Private replay hook; public snapshot timestamps are never caller-set."""
    return _snapshot_material(
        launch_start_receipt, snapshot_at=snapshot_at
    )[0]


def snapshot_week8_batch(
    *,
    launch_start_receipt: str | Path,
    snapshot_path: str | Path,
) -> dict[str, Any]:
    document, start, context = _snapshot_material(launch_start_receipt)
    destination = _monitor_destination(
        snapshot_path, start=start, context=context
    )
    path = atomic_write_json(destination, document)
    _monitor_destination(path, start=start, context=context)
    if read_json(path) != document:
        raise ValueError("persisted Week-8 monitor snapshot differs from validated evidence")
    return document


def validate_week8_monitor_snapshot(path: str | Path) -> dict[str, Any]:
    target = M._plain_file(path, what="Week-8 monitor snapshot")
    raw = target.read_bytes()
    document = read_json(target)
    if raw != L._pretty_json_bytes(document):
        raise ValueError("Week-8 monitor snapshot is not canonical immutable JSON")
    if (
        type(document) is not dict
        or document.get("week8_monitor_schema_version")
        != WEEK8_MONITOR_SCHEMA_VERSION
    ):
        raise ValueError("Week-8 monitor snapshot has the wrong schema")
    supplied = M._require_sha256(document.get("snapshot_id"), what="snapshot_id")
    payload = {key: value for key, value in document.items() if key != "snapshot_id"}
    if M._canonical_digest(payload) != supplied:
        raise ValueError("Week-8 snapshot_id does not bind its document")
    launch = document.get("launch_start")
    if type(launch) is not dict or type(launch.get("local_path")) is not str:
        raise ValueError("Week-8 monitor snapshot has no launch-start source")
    fresh, start, context = _snapshot_material(
        launch["local_path"], snapshot_at=document.get("snapshot_at")
    )
    _monitor_destination(target, start=start, context=context)
    if M._pretty_json_bytes(fresh) != M._pretty_json_bytes(document):
        raise ValueError("Week-8 monitor snapshot is stale or source-bound fields changed")
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch-start-receipt", type=Path, required=True)
    parser.add_argument("--snapshot-path", type=Path, required=True)
    document = snapshot_week8_batch(**vars(parser.parse_args(argv)))
    print(
        f"Week-8 {document['batch']['batch_key']} monitor: "
        f"{document['counts']['synced']}/{document['batch']['job_count']} synced"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
