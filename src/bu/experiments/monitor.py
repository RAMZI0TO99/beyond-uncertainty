"""Read-only, evidence-validating monitoring for registered Experiment 1.

This module has two deliberately narrow responsibilities:

* :func:`write_launch_start_evidence` is the small integration hook a launcher
  calls after acquiring its lease and immediately before entering the blocking
  batch runner.  It publishes the exact registered manifest and one immutable
  start receipt to both the local output root and the independently mounted
  durable root.  The durable copy is published first, so the local receipt is
  never evidence for a start whose off-worker copy was not observed.
* :func:`snapshot_experiment_1` reads those receipts and the batch evidence. It
  validates the complete append-only transition history, every locally
  completed fit through ``load_fit_evidence``, and every recorded sync receipt
  against its current destination tree.  It never executes a fit and never
  computes an H1 verdict or any outcome statistic.

The monitor imports the batch module's private validators intentionally.  The
manifest hash, transition machine, result identity, tree digest, and sync
receipt must have one implementation shared by writer and reader; duplicating
those rules here would make a second, potentially weaker evidence language.

An unterminated final JSONL fragment is treated exactly as the durability
layer treats it: the newline is the commit marker, so the fragment is excluded
from progress and its exact size and SHA256 are reported.  Monitoring is
read-only and therefore does not truncate or preserve the fragment elsewhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..durable import (
    DurabilityError,
    atomic_write_bytes,
    atomic_write_json,
    read_json,
    read_jsonl,
    sha256_bytes,
    sha256_file,
)
from . import batch as B
from .fit_evidence import (
    FIT_EVIDENCE_FILE,
    FIT_EVIDENCE_SCHEMA_VERSION,
    load_fit_evidence,
)
from .supervisor import SUPERVISOR_SCHEMA_VERSION


LAUNCH_START_SCHEMA_VERSION = 1
MONITOR_SNAPSHOT_SCHEMA_VERSION = 1
LAUNCH_START_DIRECTORY = "launch_starts"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")


@dataclass(frozen=True)
class LaunchStartEvidence:
    """The two independently materialised copies of one start receipt."""

    local_path: Path
    durable_path: Path
    sha256: str
    record: Mapping[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _pretty_json_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"monitor evidence is not strict JSON: {exc}") from exc
    return (rendered + "\n").encode("utf-8")


def _canonical_digest(value: object) -> str:
    try:
        encoded = B._canonical_json(value).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"monitor evidence is not strict JSON: {exc}") from exc
    return sha256_bytes(encoded)


def _strict_keys(value: object, expected: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{what} must be an exact JSON object")
    observed = set(value)
    if observed != expected:
        raise ValueError(
            f"{what} fields differ from the registered schema "
            f"(missing={sorted(expected - observed)}, "
            f"extra={sorted(observed - expected)})"
        )
    return value


def _require_sha256(value: object, *, what: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{what} must be an exact lowercase SHA256")
    return value


def _require_commit(value: object, *, what: str) -> str:
    if type(value) is not str or _COMMIT.fullmatch(value) is None:
        raise ValueError(f"{what} must be an exact lowercase 40-hex Git commit")
    return value


def _require_component(value: object, *, what: str) -> str:
    if (
        type(value) is not str
        or _SAFE_COMPONENT.fullmatch(value) is None
        or value in {".", ".."}
    ):
        raise ValueError(f"{what} must be one safe nonempty path component")
    return value


def _require_timestamp(value: object, *, what: str) -> str:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError(f"{what} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{what} is not a valid ISO-8601 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{what} is not UTC")
    return value


def _positive_number(value: object, *, what: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{what} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{what} must be a finite positive number")
    return number


def _plain_directory(path: str | Path, *, what: str) -> Path:
    requested = Path(path)
    try:
        B._require_plain_directory_components(requested)
        resolved = requested.resolve(strict=True)
        metadata = resolved.lstat()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"{what} is not an existing plain directory: {exc}") from exc
    if not resolved.is_dir() or resolved.is_symlink():
        raise ValueError(f"{what} is not an existing plain directory: {resolved}")
    if not os.path.samefile(requested, resolved):
        raise ValueError(f"{what} does not resolve canonically: {requested}")
    if not metadata.st_mode:
        raise ValueError(f"{what} has unusable filesystem metadata")
    return resolved


def _plain_file(path: str | Path, *, what: str) -> Path:
    requested = Path(path)
    try:
        B._require_plain_directory_components(requested.parent)
        B._lstat_regular_file(requested)
        resolved = requested.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"{what} is not a plain independent file: {exc}") from exc
    if resolved != requested.absolute():
        raise ValueError(f"{what} does not use its canonical absolute path: {requested}")
    return resolved


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _validate_roots(
    *, output_root: str | Path, staging_root: str | Path, sync_root: str | Path
) -> tuple[Path, Path, Path]:
    output = _plain_directory(output_root, what="output_root")
    staging = _plain_directory(staging_root, what="staging_root")
    sync = _plain_directory(sync_root, what="sync_root")
    values = (("output", output), ("staging", staging), ("sync", sync))
    for index, (left_name, left) in enumerate(values):
        for right_name, right in values[index + 1 :]:
            if _paths_overlap(left, right):
                raise ValueError(
                    f"launch roots alias or overlap: {left_name}={left}, "
                    f"{right_name}={right}"
                )
    return output, staging, sync


def _exact_registered_plan() -> tuple[tuple[B.BatchJob, ...], dict[str, Any], bytes]:
    jobs = B.experiment_1_jobs()
    if type(jobs) is not tuple or len(jobs) != 150:
        raise ValueError("experiment_1_jobs is not the exact 150-job tuple")
    manifest = B._manifest(jobs)
    if manifest.get("batch_id") != B._manifest(B.experiment_1_jobs()).get("batch_id"):
        raise ValueError("Experiment-1 registry changed while deriving its manifest")
    return jobs, manifest, _pretty_json_bytes(manifest)


def _load_active_lease(
    lease_path: str | Path,
    *,
    output_root: Path,
    lease_name: str,
    lease_token: str,
) -> tuple[Path, str]:
    path = _plain_file(lease_path, what="active batch lease")
    expected_path = output_root / "leases" / f"{lease_name}.lease.json"
    if path != expected_path:
        raise ValueError(
            f"active lease path {path} is not the prescribed {expected_path}"
        )
    record = _strict_keys(
        read_json(path),
        {"schema_version", "lease_name", "pid", "token", "timestamp", "timestamp_utc"},
        what="active batch lease",
    )
    if record["schema_version"] != SUPERVISOR_SCHEMA_VERSION:
        raise ValueError("active batch lease has the wrong schema version")
    if record["lease_name"] != lease_name or record["token"] != lease_token:
        raise ValueError("active batch lease is owned by a different name or token")
    if type(record["pid"]) is not int or record["pid"] <= 0:
        raise ValueError("active batch lease has no exact positive PID")
    if type(record["timestamp"]) not in {int, float} or isinstance(
        record["timestamp"], bool
    ) or not math.isfinite(float(record["timestamp"])):
        raise ValueError("active batch lease has no finite acquisition timestamp")
    _require_timestamp(record["timestamp_utc"], what="active lease timestamp_utc")
    return path, sha256_file(path)


def write_launch_start_evidence(
    *,
    preflight_path: str | Path,
    preflight_sha256: str,
    git_commit: str,
    batch_id: str,
    output_root: str | Path,
    staging_root: str | Path,
    sync_root: str | Path,
    attempt_timeout_seconds: float,
    lease_path: str | Path,
    lease_name: str,
    lease_token: str,
    started_at: str | None = None,
) -> LaunchStartEvidence:
    """Publish immediate local and durable evidence for one launch attempt.

    The launcher must call this after acquiring the named lease and before the
    blocking registered batch call.  No executor is accepted and no scientific
    code is invoked.  The exact canonical manifest is published first so a
    start receipt can never bind a missing or caller-supplied plan.
    """

    expected_preflight = _require_sha256(
        preflight_sha256, what="preflight_sha256"
    )
    commit = _require_commit(git_commit, what="git_commit")
    timeout = _positive_number(
        attempt_timeout_seconds, what="attempt_timeout_seconds"
    )
    name = _require_component(lease_name, what="lease_name")
    token = _require_component(lease_token, what="lease_token")
    timestamp = _require_timestamp(
        _utc_now() if started_at is None else started_at,
        what="started_at",
    )
    output, staging, sync = _validate_roots(
        output_root=output_root, staging_root=staging_root, sync_root=sync_root
    )
    preflight = _plain_file(preflight_path, what="preflight report")
    if sha256_file(preflight) != expected_preflight:
        raise ValueError("preflight report bytes do not match preflight_sha256")
    lease, lease_digest = _load_active_lease(
        lease_path,
        output_root=output,
        lease_name=name,
        lease_token=token,
    )

    _, manifest, manifest_bytes = _exact_registered_plan()
    expected_batch_id = manifest["batch_id"]
    if batch_id != expected_batch_id:
        raise ValueError(
            f"batch_id {batch_id!r} is not exact Experiment-1 batch "
            f"{expected_batch_id!r}"
        )
    manifest_digest = sha256_bytes(manifest_bytes)
    local_batch = output / expected_batch_id
    durable_batch = sync / expected_batch_id
    local_manifest = local_batch / B.MANIFEST_FILE
    durable_manifest = durable_batch / B.MANIFEST_FILE
    local_receipt = local_batch / LAUNCH_START_DIRECTORY / f"{token}.json"
    durable_receipt = durable_batch / LAUNCH_START_DIRECTORY / f"{token}.json"

    record: dict[str, Any] = {
        "launch_start_schema_version": LAUNCH_START_SCHEMA_VERSION,
        "status": "launch_started",
        "started_at": timestamp,
        "preflight": {
            "path": str(preflight),
            "sha256": expected_preflight,
            "git_commit": commit,
        },
        "batch": {
            "batch_id": expected_batch_id,
            "manifest_sha256": manifest_digest,
            "job_count": 150,
        },
        "storage": {
            "output_root": str(output),
            "staging_root": str(staging),
            "sync_root": str(sync),
        },
        "execution": {
            "attempt_timeout_seconds": timeout,
            "fresh_process_per_attempt": True,
            "registered_executor_only": True,
        },
        "lease": {
            "name": name,
            "token": token,
            "active_path": str(lease),
            "record_sha256": lease_digest,
        },
        "evidence_copies": {
            "local_path": str(local_receipt),
            "durable_path": str(durable_receipt),
        },
        "scientific_analysis_performed": False,
    }
    receipt_bytes = _pretty_json_bytes(record)

    # Durable-first publication makes the local start receipt a strong marker:
    # whenever it exists, the exact manifest and receipt were already observed
    # under the independent sync root.
    atomic_write_bytes(durable_manifest, manifest_bytes)
    atomic_write_bytes(local_manifest, manifest_bytes)
    atomic_write_bytes(durable_receipt, receipt_bytes)
    atomic_write_bytes(local_receipt, receipt_bytes)

    for path, what in (
        (local_manifest, "local manifest"),
        (durable_manifest, "durable manifest"),
        (local_receipt, "local launch-start receipt"),
        (durable_receipt, "durable launch-start receipt"),
    ):
        _plain_file(path, what=what)
    if os.path.samefile(local_manifest, durable_manifest) or os.path.samefile(
        local_receipt, durable_receipt
    ):
        raise ValueError("durable launch-start evidence aliases its local source")
    if local_manifest.read_bytes() != durable_manifest.read_bytes():
        raise ValueError("local and durable manifests differ after publication")
    if local_receipt.read_bytes() != durable_receipt.read_bytes():
        raise ValueError("local and durable launch-start receipts differ")

    return LaunchStartEvidence(
        local_path=local_receipt,
        durable_path=durable_receipt,
        sha256=sha256_bytes(receipt_bytes),
        record=record,
    )


def _load_launch_start(path: str | Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    requested = _plain_file(path, what="launch-start receipt")
    raw = requested.read_bytes()
    record = _strict_keys(
        read_json(requested),
        {
            "launch_start_schema_version",
            "status",
            "started_at",
            "preflight",
            "batch",
            "storage",
            "execution",
            "lease",
            "evidence_copies",
            "scientific_analysis_performed",
        },
        what="launch-start receipt",
    )
    if raw != _pretty_json_bytes(record):
        raise ValueError("launch-start receipt is not canonical immutable JSON")
    if record["launch_start_schema_version"] != LAUNCH_START_SCHEMA_VERSION:
        raise ValueError("launch-start receipt has the wrong schema version")
    if record["status"] != "launch_started":
        raise ValueError("launch-start receipt does not attest launch_started")
    _require_timestamp(record["started_at"], what="launch-start started_at")
    if record["scientific_analysis_performed"] is not False:
        raise ValueError("launch-start receipt makes a scientific-analysis claim")

    preflight = _strict_keys(
        record["preflight"], {"path", "sha256", "git_commit"}, what="preflight binding"
    )
    preflight_path = _plain_file(preflight["path"], what="bound preflight report")
    preflight_digest = _require_sha256(
        preflight["sha256"], what="preflight binding sha256"
    )
    if sha256_file(preflight_path) != preflight_digest:
        raise ValueError("bound preflight report changed after launch start")
    commit = _require_commit(preflight["git_commit"], what="preflight Git commit")

    batch = _strict_keys(
        record["batch"],
        {"batch_id", "manifest_sha256", "job_count"},
        what="batch binding",
    )
    jobs, manifest, manifest_bytes = _exact_registered_plan()
    if (
        batch["batch_id"] != manifest["batch_id"]
        or batch["job_count"] != len(jobs)
        or batch["manifest_sha256"] != sha256_bytes(manifest_bytes)
    ):
        raise ValueError("launch-start receipt is not bound to exact Experiment 1")

    storage = _strict_keys(
        record["storage"],
        {"output_root", "staging_root", "sync_root"},
        what="storage binding",
    )
    output, staging, sync = _validate_roots(
        output_root=storage["output_root"],
        staging_root=storage["staging_root"],
        sync_root=storage["sync_root"],
    )
    execution = _strict_keys(
        record["execution"],
        {
            "attempt_timeout_seconds",
            "fresh_process_per_attempt",
            "registered_executor_only",
        },
        what="execution binding",
    )
    _positive_number(
        execution["attempt_timeout_seconds"], what="attempt_timeout_seconds"
    )
    if (
        execution["fresh_process_per_attempt"] is not True
        or execution["registered_executor_only"] is not True
    ):
        raise ValueError("launch-start receipt does not bind the production execution path")
    lease = _strict_keys(
        record["lease"],
        {"name", "token", "active_path", "record_sha256"},
        what="lease binding",
    )
    _require_component(lease["name"], what="lease name")
    _require_component(lease["token"], what="lease token")
    _require_sha256(lease["record_sha256"], what="lease record sha256")

    copies = _strict_keys(
        record["evidence_copies"],
        {"local_path", "durable_path"},
        what="launch-start evidence copies",
    )
    local = _plain_file(copies["local_path"], what="local launch-start receipt")
    durable = _plain_file(copies["durable_path"], what="durable launch-start receipt")
    expected_local = output / batch["batch_id"] / LAUNCH_START_DIRECTORY / (
        f"{lease['token']}.json"
    )
    expected_durable = sync / batch["batch_id"] / LAUNCH_START_DIRECTORY / (
        f"{lease['token']}.json"
    )
    if local != expected_local or durable != expected_durable:
        raise ValueError("launch-start receipt copies are outside their bound roots")
    if requested not in {local, durable}:
        raise ValueError("requested launch-start receipt is not one of its bound copies")
    if os.path.samefile(local, durable):
        raise ValueError("durable launch-start receipt aliases the local receipt")
    if local.read_bytes() != raw or durable.read_bytes() != raw:
        raise ValueError("launch-start receipt copies are divergent")

    local_manifest = output / batch["batch_id"] / B.MANIFEST_FILE
    durable_manifest = sync / batch["batch_id"] / B.MANIFEST_FILE
    for manifest_path, what in (
        (local_manifest, "local batch manifest"),
        (durable_manifest, "durable batch manifest"),
    ):
        checked = _plain_file(manifest_path, what=what)
        if checked.read_bytes() != manifest_bytes:
            raise ValueError(f"{what} is not the exact registered manifest")
    if os.path.samefile(local_manifest, durable_manifest):
        raise ValueError("durable batch manifest aliases its local source")

    context = {
        "jobs": jobs,
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "commit": commit,
        "preflight_path": preflight_path,
        "output_root": output,
        "staging_root": staging,
        "sync_root": sync,
        "local_receipt": local,
        "durable_receipt": durable,
        "local_manifest": local_manifest,
        "durable_manifest": durable_manifest,
    }
    return requested, record, context


def _event_source(path: Path, *, known: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any], bytes]:
    if not os.path.lexists(path):
        empty_digest = sha256_bytes(b"")
        return [], {
            "path": str(path),
            "exists": False,
            "size_bytes": 0,
            "sha256": None,
            "committed_size_bytes": 0,
            "committed_sha256": empty_digest,
            "torn_tail_size_bytes": 0,
            "torn_tail_sha256": None,
        }, b""

    checked = _plain_file(path, what="batch event journal")
    before = checked.read_bytes()
    boundary = len(before) if not before or before.endswith(b"\n") else before.rfind(b"\n") + 1
    committed = before[:boundary]
    tail = before[boundary:]
    try:
        rows = read_jsonl(checked)
        B._events(checked, known)
    except (DurabilityError, ValueError) as exc:
        raise ValueError(f"invalid batch event journal {checked}: {exc}") from exc
    if checked.read_bytes() != before:
        raise ValueError("batch event journal changed while it was monitored")
    _validate_event_rows(rows, known=known)
    return rows, {
        "path": str(checked),
        "exists": True,
        "size_bytes": len(before),
        "sha256": sha256_bytes(before),
        "committed_size_bytes": len(committed),
        "committed_sha256": sha256_bytes(committed),
        "torn_tail_size_bytes": len(tail),
        "torn_tail_sha256": None if not tail else sha256_bytes(tail),
    }, committed


def _validate_event_rows(rows: Sequence[dict[str, Any]], *, known: set[str]) -> None:
    latest: dict[str, dict[str, Any]] = {}
    for line_number, event in enumerate(rows, 1):
        status = event.get("status")
        common = {"schema_version", "job_id", "status"}
        allowed: set[str]
        required: set[str]
        if status == "started":
            allowed = common | {"recovery"}
            required = common
        elif status == "completed":
            allowed = common | {
                "result",
                "result_digest",
                "recovered_after_interruption",
                "recovered_after_failure",
            }
            required = common | {"result", "result_digest"}
        elif status == "failed":
            allowed = required = common | {"error_type", "error"}
        elif status == "sync_failed":
            allowed = required = common | {
                "error_type",
                "error",
                "result_digest",
            }
        elif status == "synced":
            allowed = common | {"result_digest", "sync_receipt", "re_attestation"}
            required = common | {"result_digest", "sync_receipt"}
        else:
            raise ValueError(f"batch event line {line_number} has unknown status")
        fields = set(event)
        if not required <= fields or not fields <= allowed:
            raise ValueError(
                f"batch event line {line_number} has forged or missing fields "
                f"(required={sorted(required)}, observed={sorted(fields)})"
            )
        if event.get("schema_version") != B.BATCH_SCHEMA_VERSION:
            raise ValueError(f"batch event line {line_number} has wrong schema")
        job_id = event.get("job_id")
        if job_id not in known:
            raise ValueError(
                f"batch event line {line_number} names unknown job {job_id!r}"
            )
        prior = latest.get(job_id)
        prior_status = None if prior is None else prior["status"]
        if status not in B._ALLOWED_TRANSITIONS[prior_status]:
            raise ValueError(
                f"batch event line {line_number} makes illegal transition "
                f"{prior_status!r} -> {status!r} for {job_id}"
            )
        if status == "started" and "recovery" in event and event["recovery"] is not True:
            raise ValueError("started recovery marker must be exactly true")
        if status == "completed":
            flags = [
                name
                for name in ("recovered_after_interruption", "recovered_after_failure")
                if name in event
            ]
            if len(flags) > 1 or any(event[name] is not True for name in flags):
                raise ValueError("completed recovery marker is forged or ambiguous")
            if not isinstance(event["result"], Mapping):
                raise ValueError("completed event result must be an exact mapping")
            if B._result_digest(event["result"]) != event["result_digest"]:
                raise ValueError("completed event result does not match result_digest")
        if status in {"failed", "sync_failed"}:
            if any(
                type(event[name]) is not str or not event[name]
                for name in ("error_type", "error")
            ):
                raise ValueError(f"{status} event has no exact error evidence")
        if status in {"completed", "sync_failed", "synced"}:
            _require_sha256(event.get("result_digest"), what="event result_digest")
        if status == "synced":
            receipt = _strict_keys(
                event["sync_receipt"],
                {
                    "schema_version",
                    "destination",
                    "job_id",
                    "result_digest",
                    "job_tree_digest",
                    "copy_evidence_digest",
                },
                what="sync receipt",
            )
            if prior_status == "synced":
                if event.get("re_attestation") is not True:
                    raise ValueError("duplicate synced event lacks a re-attestation marker")
                if prior.get("sync_receipt") == receipt:
                    raise ValueError("duplicate synced event repeats the same receipt")
            elif "re_attestation" in event:
                raise ValueError("first synced event cannot claim re-attestation")
        latest[job_id] = event


def _load_completed_jobs(
    *,
    batch_dir: Path,
    jobs: Sequence[B.BatchJob],
    rows: Sequence[dict[str, Any]],
    expected_commit: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    by_id = {job.job_id: job for job in jobs}
    completed_events: dict[str, dict[str, Any]] = {}
    for event in rows:
        if event["status"] == "completed":
            completed_events[event["job_id"]] = event

    jobs_root = batch_dir / "jobs"
    published: set[str] = set()
    if os.path.lexists(jobs_root):
        plain_jobs = _plain_directory(jobs_root, what="published jobs root")
        for child in plain_jobs.iterdir():
            if child.name not in by_id:
                raise ValueError(f"published jobs tree names unknown job {child.name!r}")
            if child.is_symlink() or not child.is_dir():
                raise ValueError(f"published job path is not a plain directory: {child}")
            published.add(child.name)
    unbound = sorted(published - set(completed_events))
    if unbound:
        raise ValueError(
            f"published job evidence has no completed checkpoint: {unbound}"
        )

    verified: dict[str, dict[str, Any]] = {}
    for job_id in sorted(completed_events):
        job = by_id[job_id]
        event = completed_events[job_id]
        job_dir = jobs_root / job_id
        if job_id not in published:
            raise ValueError(f"completed job {job_id} has no published evidence tree")
        result_path = _plain_file(job_dir / B.RESULT_FILE, what="job result")
        raw_result = result_path.read_bytes()
        result = read_json(result_path)
        if raw_result != _pretty_json_bytes(result):
            raise ValueError(f"job result for {job_id} is not canonical immutable JSON")
        validated_result = B._validate_result(job, result)
        digest = B._result_digest(validated_result)
        if digest != event["result_digest"] or validated_result != event["result"]:
            raise ValueError(
                f"completed checkpoint for {job_id} disagrees with job_result.json"
            )
        if validated_result.get("fit_evidence_schema_version") != FIT_EVIDENCE_SCHEMA_VERSION:
            raise ValueError(f"completed job {job_id} has no current fit-evidence schema")
        if validated_result.get("fit_evidence_file") != FIT_EVIDENCE_FILE:
            raise ValueError(f"completed job {job_id} names noncanonical fit evidence")
        evidence = load_fit_evidence(
            job_dir,
            expected_git_commit=expected_commit,
        )
        expected_fields = {
            "fit_dir": job_dir.resolve(),
            "fit_id": job.config.fit_id,
            "unit_id": job.config.unit_id,
            "config_id": job.config.config_id,
            "arm": job.arm,
            "seed": job.seed,
            "roles": job.roles,
        }
        for name, expected in expected_fields.items():
            if getattr(evidence, name, None) != expected:
                raise ValueError(
                    f"verified fit evidence for {job_id} has {name}="
                    f"{getattr(evidence, name, None)!r}, expected {expected!r}"
                )
        if validated_result.get("fit_evidence_digest") != getattr(
            evidence, "execution_digest", None
        ):
            raise ValueError(
                f"job result for {job_id} does not bind the verified fit sidecar"
            )
        tree_digest = B._job_tree_digest(job_dir)
        verified[job_id] = {
            "job_id": job_id,
            "result_digest": digest,
            "fit_evidence_digest": evidence.execution_digest,
            "job_tree_digest": tree_digest,
            "local_path": str(job_dir.resolve()),
        }
    return verified, sorted(published)


def _validate_sync_events(
    *,
    batch_dir: Path,
    sync_batch_dir: Path,
    jobs: Sequence[B.BatchJob],
    rows: Sequence[dict[str, Any]],
    remote_rows: Sequence[dict[str, Any]],
    verified: Mapping[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    by_id = {job.job_id: job for job in jobs}
    latest: dict[str, tuple[int, dict[str, Any]]] = {}
    receipts: list[dict[str, Any]] = []
    for index, event in enumerate(rows):
        latest[event["job_id"]] = (index, event)
        if event["status"] != "synced":
            continue
        job_id = event["job_id"]
        if job_id not in verified:
            raise ValueError(f"synced job {job_id} has no verified completed evidence")
        receipt_row = event["sync_receipt"]
        try:
            receipt = B.SyncReceipt(**receipt_row)
        except TypeError as exc:
            raise ValueError(f"sync receipt for {job_id} is not typed exactly") from exc
        result = B._validate_result(by_id[job_id], next(
            row["result"]
            for row in rows
            if row["job_id"] == job_id and row["status"] == "completed"
        ))
        B._validate_sync_receipt(
            receipt,
            batch_dir=batch_dir,
            job=by_id[job_id],
            result=result,
        )
        receipts.append(
            {
                "event_index": index,
                "job_id": job_id,
                "destination": receipt.destination,
                "result_digest": receipt.result_digest,
                "job_tree_digest": receipt.job_tree_digest,
                "copy_evidence_digest": receipt.copy_evidence_digest,
                "receipt_digest": _canonical_digest(receipt_row),
            }
        )

    durably_synced: set[str] = set()
    for job_id, (index, event) in latest.items():
        if event["status"] != "synced":
            continue
        expected_destination = (
            sync_batch_dir / "jobs" / job_id
        ).resolve(strict=False)
        receipt_destination = Path(event["sync_receipt"]["destination"]).resolve(
            strict=True
        )
        mirrored = index < len(remote_rows) and remote_rows[index] == event
        if receipt_destination == expected_destination and mirrored:
            durably_synced.add(job_id)
    return receipts, durably_synced


def _explicit_resumed_jobs(rows: Sequence[dict[str, Any]]) -> set[str]:
    starts: Counter[str] = Counter()
    resumed: set[str] = set()
    for event in rows:
        job_id = event["job_id"]
        if event["status"] == "started":
            starts[job_id] += 1
            if starts[job_id] > 1 or event.get("recovery") is True:
                resumed.add(job_id)
        if event.get("recovered_after_interruption") is True or event.get(
            "recovered_after_failure"
        ) is True or event.get("re_attestation") is True:
            resumed.add(job_id)
    return resumed


def _re_attest_snapshot_sources(
    *,
    source_digests: Mapping[str, dict[str, Any]],
    verified: Mapping[str, dict[str, Any]],
    receipts: Sequence[dict[str, Any]],
) -> None:
    """Refuse a source that changes between validation and snapshot assembly."""

    for name in (
        "preflight",
        "launch_start_local",
        "launch_start_durable",
        "manifest_local",
        "manifest_durable",
    ):
        source = source_digests[name]
        path = _plain_file(source["path"], what=f"snapshot source {name}")
        if sha256_file(path) != source["sha256"]:
            raise ValueError(f"snapshot source {name} changed while monitoring")
    for name in ("events_local", "events_durable"):
        source = source_digests[name]
        path = Path(source["path"])
        if source["exists"] is False:
            if os.path.lexists(path):
                raise ValueError(f"snapshot source {name} appeared while monitoring")
            continue
        checked = _plain_file(path, what=f"snapshot source {name}")
        raw = checked.read_bytes()
        if len(raw) != source["size_bytes"] or sha256_bytes(raw) != source["sha256"]:
            raise ValueError(f"snapshot source {name} changed while monitoring")
    for job_id, evidence in verified.items():
        path = Path(evidence["local_path"])
        if B._job_tree_digest(path) != evidence["job_tree_digest"]:
            raise ValueError(
                f"completed job evidence for {job_id} changed while monitoring"
            )
    for receipt in receipts:
        destination = Path(receipt["destination"])
        if B._job_tree_digest(destination) != receipt["job_tree_digest"]:
            raise ValueError(
                f"sync destination for {receipt['job_id']} changed while monitoring"
            )


def _snapshot_document(
    launch_start_receipt: str | Path,
    *,
    snapshot_at: str | None = None,
) -> dict[str, Any]:
    _, start, context = _load_launch_start(launch_start_receipt)
    timestamp = _require_timestamp(
        _utc_now() if snapshot_at is None else snapshot_at,
        what="snapshot_at",
    )
    jobs: tuple[B.BatchJob, ...] = context["jobs"]
    known = {job.job_id for job in jobs}
    batch_id = context["manifest"]["batch_id"]
    local_batch = context["output_root"] / batch_id
    remote_batch = context["sync_root"] / batch_id
    local_events = local_batch / B.EVENTS_FILE
    remote_events = remote_batch / B.EVENTS_FILE
    rows, local_event_source, local_committed = _event_source(
        local_events, known=known
    )
    remote_rows, remote_event_source, remote_committed = _event_source(
        remote_events, known=known
    )
    if remote_event_source["torn_tail_size_bytes"] != 0:
        raise ValueError("durable event journal has an unterminated tail")
    if not local_committed.startswith(remote_committed):
        raise ValueError("durable event journal is not an exact local prefix")
    if list(rows[: len(remote_rows)]) != list(remote_rows):
        raise ValueError("durable event rows are not an exact local prefix")

    verified, published = _load_completed_jobs(
        batch_dir=local_batch,
        jobs=jobs,
        rows=rows,
        expected_commit=context["commit"],
    )
    receipts, durably_synced = _validate_sync_events(
        batch_dir=local_batch,
        sync_batch_dir=remote_batch,
        jobs=jobs,
        rows=rows,
        remote_rows=remote_rows,
        verified=verified,
    )

    latest: dict[str, str] = {}
    started_jobs: set[str] = set()
    completed_jobs: set[str] = set()
    for event in rows:
        latest[event["job_id"]] = event["status"]
        if event["status"] == "started":
            started_jobs.add(event["job_id"])
        if event["status"] == "completed":
            completed_jobs.add(event["job_id"])
    resumed_jobs = _explicit_resumed_jobs(rows)
    counts = {
        "started": len(started_jobs),
        "completed": len(completed_jobs),
        "resumed": len(resumed_jobs),
        "failed": sum(event["status"] == "failed" for event in rows),
        "sync_failed": sum(event["status"] == "sync_failed" for event in rows),
        "synced": len(durably_synced),
        "outstanding": len(jobs) - len(durably_synced),
    }
    latest_counts = Counter(latest.values())
    current_states = {
        name: int(latest_counts.get(name, 0))
        for name in ("started", "completed", "failed", "sync_failed", "synced")
    }
    current_states["not_started"] = len(jobs) - len(latest)

    source_digests = {
        "preflight": {
            "path": str(context["preflight_path"]),
            "sha256": sha256_file(context["preflight_path"]),
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
        "events_local": local_event_source,
        "events_durable": remote_event_source,
    }
    _re_attest_snapshot_sources(
        source_digests=source_digests,
        verified=verified,
        receipts=receipts,
    )
    sizes = sorted({job.unit.n_transitions for job in jobs})
    seeds = sorted({job.seed for job in jobs})
    payload: dict[str, Any] = {
        "monitor_snapshot_schema_version": MONITOR_SNAPSHOT_SCHEMA_VERSION,
        "kind": "experiment_1_validated_inventory",
        "snapshot_at": timestamp,
        "status": "complete" if counts["synced"] == len(jobs) else "in_progress",
        "batch": {
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
        "counts": counts,
        "count_definitions": {
            "started": "distinct jobs with at least one committed started event",
            "completed": "distinct jobs with a committed completed event and verified local fit evidence",
            "resumed": "distinct jobs with an explicit recovery/re-attestation marker or more than one start",
            "failed": "committed failed event rows, including failures later resumed",
            "sync_failed": "committed sync_failed event rows, including failures later retried",
            "synced": "latest state is synced to the bound durable root, its receipt/tree validate, and that exact event is durably journal-mirrored",
            "outstanding": "registered jobs not satisfying the synced definition",
        },
        "latest_state_counts": current_states,
        "inventories": {
            "started_job_ids": sorted(started_jobs),
            "completed_job_ids": sorted(completed_jobs),
            "resumed_job_ids": sorted(resumed_jobs),
            "published_job_ids": published,
            "durably_synced_job_ids": sorted(durably_synced),
            "unsynced_completed_job_ids": sorted(completed_jobs - durably_synced),
            "active_started_job_ids": sorted(
                job_id for job_id, state in latest.items() if state == "started"
            ),
        },
        "verified_completed": [verified[key] for key in sorted(verified)],
        "validated_sync_receipts": receipts,
        "plan_inventory_only": {
            "n_transition_range": [min(sizes), max(sizes)],
            "seed_range": [min(seeds), max(seeds)],
            "arms": sorted({job.arm for job in jobs}),
            "stages": sorted({job.stage for job in jobs}),
        },
        "source_digests": source_digests,
        "scientific_analysis": {
            "performed": False,
            "h1_verdict": None,
            "outcome_statistics": None,
        },
    }
    payload["snapshot_id"] = _canonical_digest(payload)
    return payload


def snapshot_experiment_1(
    *,
    launch_start_receipt: str | Path,
    snapshot_path: str | Path,
    snapshot_at: str | None = None,
) -> dict[str, Any]:
    """Validate current inventory and publish one immutable monitor snapshot."""

    document = _snapshot_document(
        launch_start_receipt,
        snapshot_at=snapshot_at,
    )
    destination = Path(snapshot_path)
    atomic_write_json(destination, document)
    persisted = read_json(destination)
    if persisted != document:
        raise ValueError("persisted monitor snapshot differs from validated evidence")
    return document


def validate_monitor_snapshot(snapshot_path: str | Path) -> dict[str, Any]:
    """Revalidate an immutable snapshot and refuse stale source bindings."""

    path = _plain_file(snapshot_path, what="monitor snapshot")
    raw = path.read_bytes()
    document = read_json(path)
    if type(document) is not dict or raw != _pretty_json_bytes(document):
        raise ValueError("monitor snapshot is not canonical immutable JSON")
    if document.get("monitor_snapshot_schema_version") != MONITOR_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("monitor snapshot has the wrong schema version")
    supplied_id = _require_sha256(document.get("snapshot_id"), what="snapshot_id")
    payload = {key: value for key, value in document.items() if key != "snapshot_id"}
    if supplied_id != _canonical_digest(payload):
        raise ValueError("monitor snapshot_id does not bind its document")
    launch_start = document.get("launch_start")
    if type(launch_start) is not dict or type(launch_start.get("local_path")) is not str:
        raise ValueError("monitor snapshot has no launch-start source path")
    fresh = _snapshot_document(
        launch_start["local_path"],
        snapshot_at=document.get("snapshot_at"),
    )
    if fresh != document:
        raise ValueError("monitor snapshot is stale: one or more source digests changed")
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bu.experiments.monitor",
        description=(
            "Write a read-only, evidence-validating Experiment-1 inventory "
            "snapshot. No fit or scientific verdict is computed."
        ),
    )
    parser.add_argument("--launch-start-receipt", required=True, type=Path)
    parser.add_argument("--snapshot-path", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        document = snapshot_experiment_1(
            launch_start_receipt=arguments.launch_start_receipt,
            snapshot_path=arguments.snapshot_path,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(document, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via main(argv)
    raise SystemExit(main())
