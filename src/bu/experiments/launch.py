"""Production launch boundary for the registered Experiment-1 batch.

The preflight and batch runners intentionally remain separate.  A preflight
report is immutable readiness evidence, while a launch is the state-changing
act that acquires ownership and starts (or resumes) fits.  This module joins
those boundaries without weakening either one:

* the exact, canonically encoded ``preflight_report.json`` is revalidated
  against the current registered plan, Git commit, package environment,
  device, storage roots, and read-back sync canary;
* no lease, output directory, or batch callback is touched before validation;
* one explicit Experiment-1 lease protects the output root; acquisition age
  alone can never authorize stale recovery; and
* the batch always uses its production default executor, a fresh-process
  timeout, and the mounted-directory sync adapter.

Importing this module never performs preflight or launches work.  The command
line interface is an explicit operator boundary and prints the persisted launch
report only after :func:`launch_experiment_1` returns.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import stat
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_bytes, sha256_file
from . import batch as B
from . import preflight as P
from .confirmatory import CONFIRMATORY_DEVICE
from .monitor import write_launch_start_evidence
from .supervisor import acquire_batch_lease


LAUNCH_SCHEMA_VERSION = 2
LAUNCH_REPORT_DIRECTORY = "launch_reports"
EXPERIMENT_1_LEASE_NAME = "experiment-1"


@dataclass(frozen=True)
class ValidatedPreflight:
    """A fully revalidated ready report and its launch-bound filesystem roots.

    Instances are created only by :func:`validate_ready_preflight`; callers
    should not treat hand-constructed instances as readiness evidence.
    """

    report_path: Path
    report_sha256: str
    plan_sha256: str
    git_commit: str
    output_root: Path
    staging_root: Path
    sync_root: Path
    destination_identity: str
    report: Mapping[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _strict_keys(value: object, expected: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{what} must be an exact JSON object")
    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise ValueError(
            f"{what} fields differ from the registered schema "
            f"(missing={missing}, extra={extra})"
        )
    return value


def _pretty_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"preflight report is not strict JSON: {exc}") from exc
    return (text + "\n").encode("utf-8")


def _regular_file(path: Path, *, what: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {what} {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{what} must be a regular non-symlink file: {path}")


def _resolve_directory(path: str | Path, *, what: str) -> Path:
    try:
        resolved = Path(path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"{what} must be an existing directory: {path!r}: {exc}") from exc
    if not resolved.is_dir():
        raise ValueError(f"{what} must be an existing directory: {resolved}")
    return resolved


def _positive_number(value: object, *, what: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{what} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{what} must be a finite positive number")
    return number


def _filesystem_identity(path: Path) -> tuple[int, str]:
    """Return the volume identity required for atomic attempt publication."""

    resolved = path.resolve(strict=True)
    return int(resolved.stat().st_dev), os.path.splitdrive(str(resolved))[0].casefold()


def _validate_same_volume_staging(output_root: Path, staging_root: Path) -> None:
    """Refuse a preflight staging root that cannot publish atomically."""

    if _filesystem_identity(output_root) != _filesystem_identity(staging_root):
        raise ValueError(
            "preflight output and staging roots must share one filesystem "
            "volume for atomic attempt publication"
        )


def _validate_plan(
    report_plan: object,
    *,
    jobs: Sequence[B.BatchJob] | None = None,
) -> tuple[tuple[B.BatchJob, ...], dict[str, Any]]:
    job_tuple = B.experiment_1_jobs() if jobs is None else tuple(jobs)
    expected = P._verify_plan(job_tuple)
    observed = _strict_keys(
        report_plan,
        {
            "fit_count",
            "unique_fit_count",
            "multi_role_fit_count",
            "seeds",
            "sizes",
            "configurations_per_size_seed",
            "sha256",
        },
        what="preflight plan",
    )
    if observed != expected:
        raise ValueError(
            "preflight plan is not the current exact registered Experiment-1 plan"
        )
    return job_tuple, expected


def _current_environment() -> dict[str, Any]:
    state, versions, pins = P._verify_environment()
    return {
        "git": {
            "commit": state.commit,
            "branch": state.branch,
            "dirty": state.dirty,
            "trustworthy": state.trustworthy,
        },
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": versions,
        "exact_pins": pins,
    }


def _validate_environment(report_environment: object) -> dict[str, Any]:
    observed = _strict_keys(
        report_environment,
        {"git", "python", "platform", "packages", "exact_pins"},
        what="preflight environment",
    )
    _strict_keys(
        observed["git"],
        {"commit", "branch", "dirty", "trustworthy"},
        what="preflight Git environment",
    )
    _strict_keys(
        observed["packages"], set(P.TRACKED_PACKAGES),
        what="preflight package inventory",
    )
    _strict_keys(
        observed["exact_pins"], set(P.TRACKED_PACKAGES),
        what="preflight exact-pin inventory",
    )
    current = _current_environment()
    if observed != current:
        raise ValueError(
            "preflight environment is not the current clean Git/package environment"
        )
    return current


def _validate_device(report_device: object) -> None:
    observed = _strict_keys(
        report_device,
        {"frozen_route", "requested_route", "available"},
        what="preflight device",
    )
    current = P._verify_device(CONFIRMATORY_DEVICE)
    if observed != current:
        raise ValueError("preflight device is not the current frozen execution route")


def _validate_storage(
    report_storage: object,
    *,
    report_parent: Path,
    requested_output: Path,
    requested_sync: Path,
) -> dict[str, Path]:
    storage = _strict_keys(
        report_storage,
        {"minimum_free_bytes", "roots"},
        what="preflight storage",
    )
    minimum = storage["minimum_free_bytes"]
    if type(minimum) is not int or minimum < 0:
        raise ValueError(
            "preflight minimum_free_bytes must be an exact nonnegative integer"
        )
    roots = _strict_keys(
        storage["roots"],
        {"preflight", "output", "staging", "sync"},
        what="preflight storage roots",
    )
    for name, snapshot in roots.items():
        record = _strict_keys(
            snapshot,
            {"path", "writable", "free_bytes"},
            what=f"preflight {name} storage snapshot",
        )
        if type(record["path"]) is not str or not record["path"]:
            raise ValueError(f"preflight {name} storage path must be a string")
        if record["writable"] is not True:
            raise ValueError(f"preflight {name} storage was not writable")
        if type(record["free_bytes"]) is not int or record["free_bytes"] < minimum:
            raise ValueError(
                f"preflight {name} free-byte evidence is below its registered minimum"
            )

    current_roots, _ = P._verify_storage(
        preflight_dir=roots["preflight"]["path"],
        output_root=roots["output"]["path"],
        staging_root=roots["staging"]["path"],
        sync_root=roots["sync"]["path"],
        minimum_free_bytes=minimum,
    )
    for name, resolved in current_roots.items():
        if roots[name]["path"] != str(resolved):
            raise ValueError(
                f"preflight {name} path is not its current exact resolved path"
            )
    if current_roots["preflight"] != report_parent:
        raise ValueError(
            "preflight report is not inside its recorded preflight directory"
        )
    if current_roots["output"] != requested_output:
        raise ValueError("requested output_root differs from the ready preflight")
    if current_roots["sync"] != requested_sync:
        raise ValueError("requested sync_root differs from the ready preflight")
    return current_roots


def _lower_sha256(value: object, *, what: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{what} must be a lowercase SHA256 digest")
    return value


def _validate_sync_evidence(
    report: Mapping[str, Any],
    *,
    roots: Mapping[str, Path],
    plan_sha256: str,
) -> str:
    canary = _strict_keys(
        report["sync_canary"],
        {"source_path", "destination_path", "sha256", "size_bytes"},
        what="preflight sync canary",
    )
    receipt = _strict_keys(
        report["sync_receipt"],
        {
            "schema_version",
            "destination_identity",
            "destination_path",
            "sha256",
            "size_bytes",
        },
        what="preflight sync receipt",
    )
    if (
        type(receipt["schema_version"]) is not int
        or receipt["schema_version"] != P.SYNC_RECEIPT_SCHEMA_VERSION
    ):
        raise ValueError("preflight sync receipt has the wrong schema version")
    destination_identity = P._validate_destination_identity(
        receipt["destination_identity"]
    )

    expected_source = roots["preflight"] / P.SYNC_CANARY_FILE
    expected_destination = roots["sync"] / P.SYNC_CANARY_FILE
    for field, expected in (
        ("source_path", expected_source),
        ("destination_path", expected_destination),
    ):
        if type(canary[field]) is not str:
            raise ValueError(f"preflight canary {field} must be a string")
        try:
            resolved = Path(canary[field]).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"preflight canary {field} is unavailable: {exc}") from exc
        if resolved != expected:
            raise ValueError(f"preflight canary {field} names the wrong file")
        if canary[field] != str(expected):
            raise ValueError(f"preflight canary {field} is not an exact resolved path")

    _regular_file(expected_source, what="local preflight sync canary")
    _regular_file(expected_destination, what="mounted preflight sync canary")
    digest = _lower_sha256(canary["sha256"], what="preflight canary sha256")
    size = canary["size_bytes"]
    if type(size) is not int or size < 0:
        raise ValueError("preflight canary size_bytes must be a nonnegative integer")
    if sha256_file(expected_source) != digest or expected_source.stat().st_size != size:
        raise ValueError("local preflight sync canary no longer matches its evidence")
    if (
        sha256_file(expected_destination) != digest
        or expected_destination.stat().st_size != size
        or expected_destination.read_bytes() != expected_source.read_bytes()
    ):
        raise ValueError("mounted preflight sync canary no longer matches local bytes")

    if receipt["destination_path"] != str(expected_destination):
        raise ValueError("preflight sync receipt names the wrong mounted canary")
    if receipt["sha256"] != digest or receipt["size_bytes"] != size:
        raise ValueError("preflight sync receipt does not bind the current canary")

    canary_document = _strict_keys(
        read_json(expected_source),
        {"canary_schema_version", "destination_identity", "plan_sha256"},
        what="preflight sync canary document",
    )
    if canary_document != {
        "canary_schema_version": 1,
        "destination_identity": destination_identity,
        "plan_sha256": plan_sha256,
    }:
        raise ValueError("preflight sync canary is not bound to this plan/destination")
    return destination_identity


def validate_ready_preflight(
    preflight_report: str | Path,
    *,
    output_root: str | Path,
    sync_root: str | Path,
) -> ValidatedPreflight:
    """Revalidate one immutable ready preflight without launching or writing.

    The report must be the canonical artifact produced by
    :func:`bu.experiments.preflight.run_experiment_1_preflight`.  Every
    readiness claim is checked again against the current process and mounted
    filesystem.  Any mismatch raises :class:`ValueError` before a lease or
    batch runner can be reached.
    """

    requested_report = Path(preflight_report)
    _regular_file(requested_report, what="preflight report")
    try:
        path = requested_report.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"preflight report does not exist: {preflight_report!r}: {exc}") from exc
    if path.name != P.PREFLIGHT_REPORT_FILE:
        raise ValueError(
            f"preflight report must be named {P.PREFLIGHT_REPORT_FILE!r}"
        )
    raw = path.read_bytes()
    report = _strict_keys(
        read_json(path),
        {
            "preflight_schema_version",
            "status",
            "launch_performed",
            "plan",
            "environment",
            "device",
            "storage",
            "sync_canary",
            "sync_receipt",
        },
        what="preflight report",
    )
    if raw != _pretty_json_bytes(report):
        raise ValueError(
            "preflight report is not the canonical immutable encoding produced by preflight"
        )
    if (
        type(report["preflight_schema_version"]) is not int
        or report["preflight_schema_version"] != P.PREFLIGHT_SCHEMA_VERSION
    ):
        raise ValueError("preflight report has the wrong schema version")
    if report["status"] != "ready" or report["launch_performed"] is not False:
        raise ValueError("preflight report is not an unconsumed ready report")

    requested_output = _resolve_directory(output_root, what="output_root")
    requested_sync = _resolve_directory(sync_root, what="sync_root")
    _, plan = _validate_plan(report["plan"])
    current_environment = _validate_environment(report["environment"])
    _validate_device(report["device"])
    roots = _validate_storage(
        report["storage"],
        report_parent=path.parent,
        requested_output=requested_output,
        requested_sync=requested_sync,
    )
    destination_identity = _validate_sync_evidence(
        report, roots=roots, plan_sha256=plan["sha256"]
    )
    if path.read_bytes() != raw:
        raise ValueError("preflight report changed while it was being validated")

    return ValidatedPreflight(
        report_path=path,
        report_sha256=sha256_bytes(raw),
        plan_sha256=plan["sha256"],
        git_commit=current_environment["git"]["commit"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        destination_identity=destination_identity,
        report=report,
    )


def _validate_batch_report(
    report: object,
    *,
    jobs: Sequence[B.BatchJob],
) -> B.BatchReport:
    if type(report) is not B.BatchReport:
        raise ValueError(
            f"run_batch returned {type(report).__name__}, not an exact BatchReport"
        )
    expected_id = B._manifest(tuple(jobs))["batch_id"]
    if report.batch_id != expected_id:
        raise ValueError("run_batch returned a report for the wrong exact plan")
    for field in ("total", "executed", "resumed", "synced", "failed", "sync_failed"):
        value = getattr(report, field)
        if type(value) is not int or value < 0:
            raise ValueError(f"BatchReport.{field} must be a nonnegative integer")
    if report.total != len(jobs):
        raise ValueError("run_batch returned the wrong total job count")
    if report.executed + report.resumed + report.failed != report.total:
        raise ValueError("run_batch report does not account for every Experiment-1 job")
    if report.synced + report.sync_failed > report.executed + report.resumed:
        raise ValueError("run_batch report sync counts exceed completed/recovered jobs")
    return report


def launch_experiment_1(
    *,
    preflight_report: str | Path,
    output_root: str | Path,
    sync_root: str | Path,
    attempt_timeout_seconds: float,
    stale_lease_after_seconds: float | None = None,
) -> dict[str, Any]:
    """Validate, exclusively launch/resume, sync, and report Experiment 1.

    This is the only production launch path in this module.  It always obtains
    the exact plan from :func:`bu.experiments.batch.experiment_1_jobs`, omits an
    executor override so the private registered batch hand-off uses its fixed
    production executor, supplies a mandatory fresh-process timeout, and builds
    sync solely with :func:`bu.experiments.batch.sync_to_directory`.

    ``stale_lease_after_seconds`` is a fail-closed compatibility parameter.
    Every non-``None`` value is refused because acquisition age cannot prove
    that a long-running owner died (D-146).
    """

    timeout = _positive_number(
        attempt_timeout_seconds, what="attempt_timeout_seconds"
    )
    if stale_lease_after_seconds is not None:
        raise ValueError(
            "time-only stale lease recovery is disabled: acquisition age "
            "cannot prove owner death"
        )
    stale_bound = None
    validated = validate_ready_preflight(
        preflight_report,
        output_root=output_root,
        sync_root=sync_root,
    )
    _validate_same_volume_staging(
        validated.output_root, validated.staging_root
    )
    jobs = B.experiment_1_jobs()
    # Recheck immediately before the state-changing boundary.  This is cheap,
    # and it prevents an in-process registry mutation after preflight validation
    # from silently changing the launched plan.
    _, current_plan = _validate_plan(validated.report["plan"], jobs=jobs)
    if current_plan["sha256"] != validated.plan_sha256:
        raise ValueError("Experiment-1 plan changed after preflight validation")
    if sha256_file(validated.report_path) != validated.report_sha256:
        raise ValueError("preflight report changed after validation")
    _validate_environment(validated.report["environment"])

    started_at = _utc_now()
    lease = acquire_batch_lease(
        validated.output_root,
        lease_name=EXPERIMENT_1_LEASE_NAME,
        stale_after_seconds=stale_bound,
    )
    released_path: Path | None = None
    try:
        start_evidence = write_launch_start_evidence(
            preflight_path=validated.report_path,
            preflight_sha256=validated.report_sha256,
            git_commit=validated.git_commit,
            batch_id=B._manifest(jobs)["batch_id"],
            output_root=validated.output_root,
            staging_root=validated.staging_root,
            sync_root=validated.sync_root,
            attempt_timeout_seconds=timeout,
            lease_path=lease.path,
            lease_name=EXPERIMENT_1_LEASE_NAME,
            lease_token=lease.token,
            started_at=started_at,
        )
        batch_report = B._run_registered_batch(
            jobs,
            root=validated.output_root,
            sync=B.sync_to_directory(validated.sync_root),
            expected_git_commit=validated.git_commit,
            attempt_timeout_seconds=timeout,
            attempt_staging_root=validated.staging_root,
        )
        checked_batch = _validate_batch_report(batch_report, jobs=jobs)
    finally:
        released_path = lease.release()

    launch_id = uuid.uuid4().hex
    report_path = (
        validated.output_root
        / LAUNCH_REPORT_DIRECTORY
        / f"{launch_id}.json"
    )
    report: dict[str, Any] = {
        "launch_schema_version": LAUNCH_SCHEMA_VERSION,
        "launch_id": launch_id,
        "status": "complete" if checked_batch.complete else "incomplete",
        "launch_performed": True,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "preflight": {
            "path": str(validated.report_path),
            "sha256": validated.report_sha256,
            "plan_sha256": validated.plan_sha256,
            "git_commit": validated.git_commit,
            "destination_identity": validated.destination_identity,
        },
        "storage": {
            "output_root": str(validated.output_root),
            "staging_root": str(validated.staging_root),
            "sync_root": str(validated.sync_root),
        },
        "execution": {
            "attempt_timeout_seconds": timeout,
            "stale_lease_after_seconds": stale_bound,
            "fresh_process_per_attempt": True,
            "separate_same_volume_staging": True,
            "default_executor": True,
            "mounted_directory_sync": True,
        },
        "lease": {
            "name": EXPERIMENT_1_LEASE_NAME,
            "token": lease.token,
            "released_history_path": str(released_path.resolve(strict=True)),
        },
        "launch_start": {
            "local_path": str(start_evidence.local_path),
            "durable_path": str(start_evidence.durable_path),
            "sha256": start_evidence.sha256,
        },
        "batch": {
            **asdict(checked_batch),
            "complete": checked_batch.complete,
        },
        "report_path": str(report_path.resolve(strict=False)),
    }
    atomic_write_json(report_path, report)
    persisted = read_json(report_path)
    if persisted != report:
        raise ValueError("persisted launch report does not match the returned report")
    return report


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit command-line contract for one Experiment-1 launch."""

    parser = argparse.ArgumentParser(
        prog="python -m bu.experiments.launch",
        description=(
            "Launch/resume the exact registered Experiment-1 plan only after "
            "revalidating an immutable ready preflight report."
        ),
    )
    parser.add_argument("--preflight-report", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--sync-root", required=True, type=Path)
    parser.add_argument("--attempt-timeout-seconds", required=True, type=float)
    parser.add_argument(
        "--stale-lease-after-seconds",
        type=float,
        default=None,
        help=(
            "Compatibility-only option: every supplied value is refused; "
            "time-only stale recovery is disabled."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments, launch once, print its report, and return status."""

    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        report = launch_experiment_1(
            preflight_report=arguments.preflight_report,
            output_root=arguments.output_root,
            sync_root=arguments.sync_root,
            attempt_timeout_seconds=arguments.attempt_timeout_seconds,
            stale_lease_after_seconds=arguments.stale_lease_after_seconds,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":  # pragma: no cover - exercised through main(argv)
    raise SystemExit(main())
