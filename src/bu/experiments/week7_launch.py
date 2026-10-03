"""Project-local, resumable launch for the exact initial Week-7 baseline batches.

Historical launchers stay unchanged. No caller executor, job subset, stage,
thread count, evidence bypass or age-only lease recovery is exposed here.
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
from . import week7_preflight as PF
from .supervisor import acquire_batch_lease
from .prefit_storage import PreflightStorageGuard


WEEK7_LAUNCH_SCHEMA_VERSION = 1
WEEK7_LEASE_NAME = "week7-production"
WEEK7_START_DIRECTORY = "week7_launch_starts"
WEEK7_REPORT_DIRECTORY = "week7_launch_reports"


def _batch_directories(validated: PF.ValidatedWeek7Preflight) -> tuple[Path, Path]:
    batch_id = validated.report["batch"]["batch_id"]
    return tuple(
        RF.ensure_regular_child_directory(validated.roots[name], batch_id)
        for name in ("output", "sync")
    )


def _write_start(validated, lease, *, timeout: float) -> dict[str, Any]:
    manifest = B._manifest(validated.jobs)
    if manifest != validated.report["batch"]:
        raise ValueError("Week-7 manifest changed before launch start")
    lease_path, lease_sha = M._load_active_lease(
        lease.path, output_root=PF._control_root(),
        lease_name=WEEK7_LEASE_NAME, lease_token=lease.token,
    )
    local, durable = _batch_directories(validated)
    # Publish the same bytes the common batch engine will later re-open.
    for directory in (durable, local):
        B._write_json_exclusive(directory / B.MANIFEST_FILE, manifest)
    PF._same_document(local / B.MANIFEST_FILE, durable / B.MANIFEST_FILE)
    local_dir = RF.ensure_regular_child_directory(local, WEEK7_START_DIRECTORY)
    durable_dir = RF.ensure_regular_child_directory(durable, WEEK7_START_DIRECTORY)
    local_path = local_dir / f"{lease.token}.json"
    durable_path = durable_dir / local_path.name
    record = {
        "week7_launch_start_schema_version": WEEK7_LAUNCH_SCHEMA_VERSION,
        "status": "launch_started", "started_at": L._utc_now(),
        "preflight": {"path": str(validated.report_path),
                      "sha256": validated.report_sha256,
                      "git_commit": validated.git_commit},
        "binding_sha256": validated.report["binding_sha256"],
        "batch_key": validated.report["batch_key"],
        "batch": {"batch_id": manifest["batch_id"], "job_count": len(validated.jobs),
                  "manifest_sha256": sha256_file(local / B.MANIFEST_FILE)},
        "storage": {name: str(root) for name, root in validated.roots.items()},
        "execution": {"attempt_timeout_seconds": timeout,
                      "fresh_process_per_attempt": True,
                      "registered_executor_only": True,
                      "sweep_anchors_required": any(j.stage == "config_sweep"
                                                    for j in validated.jobs)},
        "lease": {"name": WEEK7_LEASE_NAME, "token": lease.token,
                  "path": str(lease_path), "sha256": lease_sha,
                  "common_control_root": str(PF._control_root())},
        "copies": {"local_path": str(local_path), "durable_path": str(durable_path)},
        "scientific_analysis_performed": False,
    }
    # Durable first. A local start receipt cannot exist before readback of its
    # independent copy; no training happens if publication is interrupted.
    atomic_write_json(durable_path, record)
    atomic_write_json(local_path, record)
    PF._same_document(local_path, durable_path)
    return {"local_path": str(local_path), "durable_path": str(durable_path),
            "sha256": sha256_file(local_path), "record": record}


def _run_initial_batch(validated: PF.ValidatedWeek7Preflight, timeout: float):
    """Only exact enabled jobs may reach the fixed, process-isolated executor."""
    refreshed = PF.validate_week7_preflight(
        validated.report_path, output_root=validated.roots["output"],
        sync_root=validated.roots["sync"],
    )
    if refreshed.report_sha256 != validated.report_sha256:
        raise ValueError("Week-7 readiness changed after launch start")
    jobs = PF._batch_jobs(
        PF._input_files(validated.report["inputs"]["plan"]["path"],
                        validated.report["inputs"]["reuse_ledger"]["path"])[1],
        validated.report["batch_key"],
    )
    if tuple(j.as_record() for j in jobs) != tuple(j.as_record() for j in validated.jobs):
        raise ValueError("Week-7 job inventory changed at the execution boundary")
    return B._run_batch(
        jobs, root=validated.roots["output"],
        sync=B.sync_to_directory(validated.roots["sync"]),
        executor=B._default_executor, require_fit_evidence=True,
        expected_git_commit=validated.git_commit,
        attempt_timeout_seconds=timeout,
        attempt_staging_root=validated.roots["staging"],
        preflight_storage_guard=PreflightStorageGuard(
            validated.report_path, validated.report_sha256,
            tuple(sorted(validated.roots.items())),
        ),
    )


def _write_report(validated, token: str, report: dict[str, Any]) -> dict[str, Any]:
    paths = []
    for name in ("sync", "output"):
        directory = RF.ensure_regular_child_directory(
            validated.roots[name], WEEK7_REPORT_DIRECTORY
        )
        paths.append(atomic_write_json(directory / f"{token}.json", report))
    PF._same_document(paths[1], paths[0])
    if read_json(paths[1]) != report:
        raise ValueError("Week-7 launch report readback differs")
    return {**report, "report_path": str(paths[1])}


def launch_week7(
    *, preflight_report: str | Path, output_root: str | Path,
    sync_root: str | Path, attempt_timeout_seconds: float,
) -> dict[str, Any]:
    """Launch or resume one activated batch; never execute historical reuse."""
    timeout = L._positive_number(attempt_timeout_seconds, what="attempt_timeout_seconds")
    validated = PF.validate_week7_preflight(
        preflight_report, output_root=output_root, sync_root=sync_root
    )
    L._validate_environment(validated.report["environment"])
    if sha256_file(validated.report_path) != validated.report_sha256:
        raise ValueError("Week-7 preflight changed at lease acquisition")
    lease = acquire_batch_lease(PF._control_root(), lease_name=WEEK7_LEASE_NAME)
    start = None
    checked = None
    failure = None
    try:
        start = _write_start(validated, lease, timeout=timeout)
        batch = _run_initial_batch(validated, timeout)
        checked = L._validate_batch_report(batch, jobs=validated.jobs)
        # Reopen original reuse and exact independent copies at completion too.
        completion_preflight = PF.validate_week7_preflight(
            preflight_report, output_root=output_root, sync_root=sync_root
        )
        if completion_preflight.report_sha256 != validated.report_sha256:
            raise ValueError("Week-7 preflight changed during execution")
    except BaseException as exc:
        # Cancellation must remain a failure even after every fit completed.
        # Re-raise it unchanged; child stop/join is the supervisor's boundary.
        failure = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        released = lease.release()
        report = {
            "week7_launch_schema_version": WEEK7_LAUNCH_SCHEMA_VERSION,
            "status": ("failed" if failure is not None else
                       "complete" if checked is not None and checked.complete else "incomplete"),
            "finished_at": L._utc_now(), "launch_performed": start is not None,
            "batch_key": validated.report["batch_key"],
            "preflight": {"path": str(validated.report_path),
                          "sha256": validated.report_sha256,
                          "git_commit": validated.git_commit},
            "start": start, "failure": failure,
            "batch": (None if checked is None else {**asdict(checked), "complete": checked.complete}),
            "historical_reuse_retrained": False,
            "released_lease": {"token": lease.token, "path": str(released)},
        }
        result = _write_report(validated, lease.token, report)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preflight-report", "output-root", "sync-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--attempt-timeout-seconds", type=float, required=True)
    report = launch_week7(**vars(parser.parse_args(argv)))
    print(f"Week-7 batch status: {report['status']}; evidence: {report['report_path']}")
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
