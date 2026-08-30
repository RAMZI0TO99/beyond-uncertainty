"""No-compute preflight for the exact Week-6 repair-label smoke.

The boundary has no unit, seed, arm, executor, or device degree of freedom.
It attests the one predeclared 60-fit plan, a clean trustworthy commit, exact
package pins, the frozen CPU route, four distinct roots, same-volume output and
staging, free space, and an independently read-back mounted sync destination.
The immutable plan and preflight report are published before any fit process
can be started by :mod:`bu.experiments.repair_label_launch`.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..durable import (
    atomic_write_json,
    fsync_directory,
    read_json,
    sha256_bytes,
    sha256_file,
)
from . import preflight as P
from . import repair_label_run as R
from .confirmatory import CONFIRMATORY_DEVICE


REPAIR_LABEL_PREFLIGHT_SCHEMA_VERSION = 1
REPAIR_LABEL_PREFLIGHT_FILE = "repair_label_preflight_report.json"
REPAIR_LABEL_SYNC_DIRECTORY = "week6_repair_label_smoke"


def _canonical_json_bytes(value: object) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"smoke preflight value is not strict JSON: {exc}") from exc
    return (encoded + "\n").encode("utf-8")


def _is_reparse(info: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(info, "st_file_attributes", 0) & attribute)


def _regular_file(path: Path, *, what: str, reject_hardlinks: bool = True) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {what} {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{what} must be a regular non-link file: {path}")
    if reject_hardlinks and getattr(info, "st_nlink", 1) != 1:
        raise ValueError(f"{what} must not be a hard-linked alias: {path}")
    return info


def ensure_regular_child_directory(parent: Path, name: str) -> Path:
    """Create/verify one direct child directory without following a link."""

    resolved_parent = Path(parent).resolve(strict=True)
    candidate = resolved_parent / name
    if not candidate.exists() and not candidate.is_symlink():
        candidate.mkdir()
        fsync_directory(resolved_parent)
    try:
        info = candidate.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect evidence directory {candidate}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
        raise ValueError(
            f"evidence directory must be a regular non-link child: {candidate}"
        )
    resolved = candidate.resolve(strict=True)
    if resolved.parent != resolved_parent:
        raise ValueError(f"evidence directory escapes its prescribed parent: {candidate}")
    return resolved


def _same_file_identity(left: Path, right: Path) -> bool:
    try:
        return os.path.samestat(left.stat(), right.stat())
    except (AttributeError, OSError):
        left_stat = left.stat()
        right_stat = right.stat()
        return (
            left_stat.st_dev == right_stat.st_dev
            and left_stat.st_ino != 0
            and left_stat.st_ino == right_stat.st_ino
        )


def sync_immutable_file(source: Path, destination: Path) -> dict[str, Any]:
    """Copy one immutable file durably and prove independent read-back bytes."""

    source = Path(source)
    destination = Path(destination)
    _regular_file(source, what="sync source")
    source_resolved = source.resolve(strict=True)
    destination_parent = destination.parent.resolve(strict=True)
    destination = destination_parent / destination.name
    if destination.exists() or destination.is_symlink():
        _regular_file(destination, what="existing sync destination")
        if _same_file_identity(source_resolved, destination):
            raise ValueError("sync destination aliases the source file")
    data = source_resolved.read_bytes()
    digest = sha256_bytes(data)
    from ..durable import atomic_write_bytes

    atomic_write_bytes(destination, data)
    _regular_file(destination, what="synced file")
    if _same_file_identity(source_resolved, destination):
        raise ValueError("synced file is not an independent physical file")
    if destination.stat().st_size != len(data) or sha256_file(destination) != digest:
        raise ValueError("synced file failed size/SHA256 read-back")
    if destination.read_bytes() != data or source_resolved.read_bytes() != data:
        raise ValueError("source or destination changed during sync read-back")
    fsync_directory(destination.parent)
    return {
        "source_path": str(source_resolved),
        "destination_path": str(destination.resolve(strict=True)),
        "sha256": digest,
        "size_bytes": len(data),
        "independent_file": True,
    }


def _filesystem_identity(path: Path) -> tuple[int, str]:
    resolved = path.resolve(strict=True)
    return int(resolved.stat().st_dev), os.path.splitdrive(str(resolved))[0].casefold()


def _plan_snapshot(output_root: Path) -> tuple[dict[str, Any], Path]:
    unit = R._require_registered_smoke_unit(R.registered_week6_smoke_unit())
    model_arm, seeds, planned = R._registered_plan(unit, output_root)
    document = R._plan_document(
        unit, model_arm=model_arm, seeds=seeds, planned=planned
    )
    expected_order = [
        (seed, arm)
        for seed in range(1000, 1020)
        for arm in ("baseline", "data_repair", "feature_repair")
    ]
    observed_order = [(row["seed"], row["arm"]) for row in document["fit_order"]]
    if observed_order != expected_order or len(planned) != 60:
        raise ValueError("smoke plan is not exact 20 x baseline/data/feature order")
    path = output_root / R.REPAIR_LABEL_PLAN_FILE
    R._publish_plan(path, document)
    return (
        {
            "unit_id": R.WEEK6_SMOKE_UNIT_ID,
            "stage": "repair_validation",
            "seeds": list(seeds),
            "arms": ["baseline", "data_repair", "feature_repair"],
            "fit_count": len(planned),
            "plan_digest": document["plan_digest"],
            "plan_file_sha256": sha256_file(path),
            "path": str(path.resolve(strict=True)),
        },
        path,
    )


def run_repair_label_preflight(
    *,
    preflight_dir: str | Path,
    output_root: str | Path,
    staging_root: str | Path,
    sync_root: str | Path,
    sync_destination_identity: str,
    execution_route: str,
    minimum_free_bytes: int,
) -> dict[str, Any]:
    """Attest and persist exact smoke readiness without launching a fit."""

    destination_identity = P._validate_destination_identity(
        sync_destination_identity
    )
    state, versions, pins = P._verify_environment()
    device = P._verify_device(execution_route)
    roots, storage = P._verify_storage(
        preflight_dir=preflight_dir,
        output_root=output_root,
        staging_root=staging_root,
        sync_root=sync_root,
        minimum_free_bytes=minimum_free_bytes,
    )
    if _filesystem_identity(roots["output"]) != _filesystem_identity(roots["staging"]):
        raise ValueError(
            "smoke output and staging roots must share one filesystem volume "
            "for atomic attempt publication"
        )
    plan, plan_path = _plan_snapshot(roots["output"])
    sync_directory = ensure_regular_child_directory(
        roots["sync"], REPAIR_LABEL_SYNC_DIRECTORY
    )
    plan_sync = sync_immutable_file(
        plan_path, sync_directory / R.REPAIR_LABEL_PLAN_FILE
    )
    canary, canary_receipt = P._run_sync_canary(
        roots={**roots, "sync": sync_directory},
        plan_digest=plan["plan_digest"],
        destination_identity=destination_identity,
        adapter=P.sync_canary_to_mounted_directory,
    )

    report: dict[str, Any] = {
        "repair_label_preflight_schema_version": REPAIR_LABEL_PREFLIGHT_SCHEMA_VERSION,
        "status": "ready",
        "launch_performed": False,
        "plan": {**plan, "sync": plan_sync},
        "environment": {
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
        },
        "device": device,
        "storage": storage,
        "sync_destination_identity": destination_identity,
        "sync_directory": str(sync_directory),
        "sync_canary": canary,
        "sync_receipt": canary_receipt,
    }
    report_path = roots["preflight"] / REPAIR_LABEL_PREFLIGHT_FILE
    if report_path.exists() or report_path.is_symlink():
        _regular_file(report_path, what="existing smoke preflight report")
        previous = read_json(report_path)
        try:
            previous_storage = previous["storage"]
            previous_roots = previous_storage["roots"]
            if previous_storage["minimum_free_bytes"] != minimum_free_bytes:
                raise ValueError("minimum-free-space registration changed")
            for name, root in roots.items():
                snapshot = previous_roots[name]
                if (
                    snapshot["path"] != str(root)
                    or snapshot["writable"] is not True
                    or type(snapshot["free_bytes"]) is not int
                    or snapshot["free_bytes"] < minimum_free_bytes
                ):
                    raise ValueError(f"prior {name} storage attestation is invalid")
                # Free space naturally changes when the first preflight writes
                # its own evidence. Preserve the immutable first attestation
                # after rechecking the current floor above; every other report
                # field must still reproduce byte-for-byte.
                report["storage"]["roots"][name]["free_bytes"] = snapshot[
                    "free_bytes"
                ]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"existing smoke preflight storage evidence is invalid: {exc}"
            ) from exc
    atomic_write_json(report_path, report)
    persisted = read_json(report_path)
    if persisted != report:
        raise ValueError("persisted smoke preflight report differs from memory")
    sync_immutable_file(report_path, sync_directory / REPAIR_LABEL_PREFLIGHT_FILE)
    return json.loads(json.dumps(report))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bu.experiments.repair_label_preflight",
        description=(
            "Verify and persist the exact Week-6 20-seed repair-label smoke "
            "plan without launching a fit."
        ),
    )
    parser.add_argument("--preflight-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--staging-root", required=True, type=Path)
    parser.add_argument("--sync-root", required=True, type=Path)
    parser.add_argument("--sync-destination-identity", required=True)
    parser.add_argument("--execution-route", default=CONFIRMATORY_DEVICE)
    parser.add_argument("--minimum-free-bytes", required=True, type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        report = run_repair_label_preflight(
            preflight_dir=arguments.preflight_dir,
            output_root=arguments.output_root,
            staging_root=arguments.staging_root,
            sync_root=arguments.sync_root,
            sync_destination_identity=arguments.sync_destination_identity,
            execution_route=arguments.execution_route,
            minimum_free_bytes=arguments.minimum_free_bytes,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
