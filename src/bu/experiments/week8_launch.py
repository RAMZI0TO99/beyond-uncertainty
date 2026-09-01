"""Resumable CPU launch for one exact Week-8 baseline batch.

The public boundary accepts no executor, job subset, device, seed, stage,
storage-floor override, or age-based lease recovery.  Every new attempt uses
the fixed registered executor in a fresh spawned process.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_file
from . import batch as B
from . import launch as L
from . import monitor as M
from . import repair_label_preflight as RF
from . import week8_preflight as PF
from .prefit_storage import PreflightStorageGuard
from .supervisor import acquire_batch_lease


WEEK8_LAUNCH_SCHEMA_VERSION = 1
WEEK8_ATTEMPT_TIMEOUT_SECONDS = 3600.0
# Deliberately identical to Week 7: both weeks compete for one production owner.
WEEK8_LEASE_NAME = "week7-production"
WEEK8_START_DIRECTORY = "week8_launch_starts"
WEEK8_REPORT_DIRECTORY = "week8_launch_reports"


def _batch_directories(validated: PF.ValidatedWeek8Preflight) -> tuple[Path, Path]:
    batch_id = validated.report["batch"]["batch_id"]
    return tuple(
        RF.ensure_regular_child_directory(validated.roots[name], batch_id)
        for name in ("output", "sync")
    )


def _assert_no_preserved_failed_attempts(
    validated: PF.ValidatedWeek8Preflight,
) -> None:
    """Refuse replacement training after any committed failed fit attempt."""
    manifest = B._manifest(validated.jobs)
    events_path = (
        validated.roots["output"] / manifest["batch_id"] / B.EVENTS_FILE
    )
    rows, evidence, _ = M._event_source(
        events_path, known={job.job_id for job in validated.jobs}
    )
    if evidence["torn_tail_size_bytes"] != 0:
        raise ValueError(
            "Week-8 event history has an unterminated tail; refusing before "
            "the no-retry execution boundary"
        )
    failed = sorted(
        {row["job_id"] for row in rows if row["status"] == "failed"}
    )
    if failed:
        raise ValueError(
            "Week-8 no-retry boundary found preserved failed attempts for "
            f"{failed}; replacement training is not authorized"
        )


def _write_start(validated, lease) -> dict[str, Any]:
    manifest = B._manifest(validated.jobs)
    if manifest != validated.report["batch"]:
        raise ValueError("Week-8 manifest changed before launch start")
    lease_path, lease_sha = M._load_active_lease(
        lease.path,
        output_root=PF._control_root(),
        lease_name=WEEK8_LEASE_NAME,
        lease_token=lease.token,
    )
    local, durable = _batch_directories(validated)
    for directory in (durable, local):
        B._write_json_exclusive(directory / B.MANIFEST_FILE, manifest)
    PF._same_document(local / B.MANIFEST_FILE, durable / B.MANIFEST_FILE)
    local_dir = RF.ensure_regular_child_directory(local, WEEK8_START_DIRECTORY)
    durable_dir = RF.ensure_regular_child_directory(durable, WEEK8_START_DIRECTORY)
    local_path = local_dir / f"{lease.token}.json"
    durable_path = durable_dir / local_path.name
    sweep = any(job.stage == "config_sweep" for job in validated.jobs)
    record = {
        "week8_launch_start_schema_version": WEEK8_LAUNCH_SCHEMA_VERSION,
        "status": "launch_started",
        "started_at": L._utc_now(),
        "preflight": {
            "path": str(validated.report_path),
            "sha256": validated.report_sha256,
            "git_commit": validated.git_commit,
        },
        "binding_sha256": validated.report["binding_sha256"],
        "batch_key": validated.report["batch_key"],
        "batch": {
            "batch_id": manifest["batch_id"],
            "job_count": len(validated.jobs),
            "manifest_sha256": sha256_file(local / B.MANIFEST_FILE),
        },
        "storage": {name: str(root) for name, root in validated.roots.items()},
        "execution": {
            "attempt_timeout_seconds": WEEK8_ATTEMPT_TIMEOUT_SECONDS,
            "fresh_process_per_attempt": True,
            "registered_executor_only": True,
            "cpu_only": True,
            "prefit_storage_check_before_each_new_child": True,
            "sweep_anchors_required": sweep,
        },
        "lease": {
            "name": WEEK8_LEASE_NAME,
            "token": lease.token,
            "path": str(lease_path),
            "sha256": lease_sha,
            "common_control_root": str(PF._control_root()),
            "age_recovery_allowed": False,
        },
        "copies": {
            "local_path": str(local_path),
            "durable_path": str(durable_path),
        },
        "scientific_analysis_performed": False,
    }
    # Durable first: no local launch receipt and no training until readback is possible.
    atomic_write_json(durable_path, record)
    atomic_write_json(local_path, record)
    PF._same_document(local_path, durable_path)
    return {
        "local_path": str(local_path),
        "durable_path": str(durable_path),
        "sha256": sha256_file(local_path),
        "record": record,
    }


def _run_week8_batch(validated: PF.ValidatedWeek8Preflight):
    refreshed = PF.validate_week8_preflight(
        validated.report_path,
        output_root=validated.roots["output"],
        sync_root=validated.roots["sync"],
    )
    if refreshed.report_sha256 != validated.report_sha256:
        raise ValueError("Week-8 readiness changed after launch start")
    plan = PF._input_file(validated.report["plan"]["path"])[1]
    jobs = PF._batch_jobs(plan, validated.report["batch_key"])
    if tuple(job.as_record() for job in jobs) != tuple(
        job.as_record() for job in validated.jobs
    ):
        raise ValueError("Week-8 job inventory changed at the execution boundary")
    return B._run_batch(
        jobs,
        root=validated.roots["output"],
        sync=B.sync_to_directory(validated.roots["sync"]),
        executor=B._default_executor,
        require_fit_evidence=True,
        expected_git_commit=validated.git_commit,
        attempt_timeout_seconds=WEEK8_ATTEMPT_TIMEOUT_SECONDS,
        attempt_staging_root=validated.roots["staging"],
        preflight_storage_guard=PreflightStorageGuard(
            validated.report_path,
            validated.report_sha256,
            tuple(sorted(validated.roots.items())),
        ),
    )


def _write_report(validated, token: str, report: dict[str, Any]) -> dict[str, Any]:
    paths = []
    for name in ("sync", "output"):
        directory = RF.ensure_regular_child_directory(
            validated.roots[name], WEEK8_REPORT_DIRECTORY
        )
        paths.append(atomic_write_json(directory / f"{token}.json", report))
    PF._same_document(paths[1], paths[0])
    if read_json(paths[1]) != report:
        raise ValueError("Week-8 launch report readback differs")
    return {**report, "report_path": str(paths[1])}


def launch_week8(
    *,
    preflight_report: str | Path,
    output_root: str | Path,
    sync_root: str | Path,
    attempt_timeout_seconds: float = WEEK8_ATTEMPT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Launch or resume exactly one preflight-bound Week-8 batch."""
    if (
        type(attempt_timeout_seconds) is not float
        or attempt_timeout_seconds != WEEK8_ATTEMPT_TIMEOUT_SECONDS
    ):
        raise ValueError(
            "Week-8 attempt_timeout_seconds is frozen at exactly 3600.0"
        )
    validated = PF.validate_week8_preflight(
        preflight_report, output_root=output_root, sync_root=sync_root
    )
    L._validate_environment(validated.report["environment"])
    if sha256_file(validated.report_path) != validated.report_sha256:
        raise ValueError("Week-8 preflight changed at lease acquisition")
    _assert_no_preserved_failed_attempts(validated)
    lease = acquire_batch_lease(PF._control_root(), lease_name=WEEK8_LEASE_NAME)
    start = None
    checked = None
    failure = None
    try:
        # Recheck while holding the one shared production lease. A prior owner
        # could have finished and released between the pre-lease check and our
        # acquisition; its failed history must never be retrained.
        _assert_no_preserved_failed_attempts(validated)
        start = _write_start(validated, lease)
        batch = _run_week8_batch(validated)
        checked = L._validate_batch_report(batch, jobs=validated.jobs)
        completion = PF.validate_week8_preflight(
            preflight_report, output_root=output_root, sync_root=sync_root
        )
        if completion.report_sha256 != validated.report_sha256:
            raise ValueError("Week-8 preflight changed during execution")
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        released = lease.release()
        report = {
            "week8_launch_schema_version": WEEK8_LAUNCH_SCHEMA_VERSION,
            "status": (
                "failed"
                if failure is not None
                else "complete"
                if checked is not None and checked.complete
                else "incomplete"
            ),
            "finished_at": L._utc_now(),
            "launch_performed": start is not None,
            "batch_key": validated.report["batch_key"],
            "preflight": {
                "path": str(validated.report_path),
                "sha256": validated.report_sha256,
                "git_commit": validated.git_commit,
            },
            "start": start,
            "failure": failure,
            "batch": (
                None
                if checked is None
                else {**asdict(checked), "complete": checked.complete}
            ),
            "scientific_analysis_performed": False,
            "released_lease": {"token": lease.token, "path": str(released)},
        }
        result = _write_report(validated, lease.token, report)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preflight-report", "output-root", "sync-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    report = launch_week8(**vars(parser.parse_args(argv)))
    print(f"Week-8 batch status: {report['status']}; evidence: {report['report_path']}")
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
