"""Production launch boundary for the exact Week-6 repair-label smoke.

Every one of the 60 registered fits runs in a fresh spawned process under a
mandatory timeout.  The child is bound to the clean preflight commit before
pool generation, writes only inside same-volume attempt staging, and is
atomically published by the generic supervisor.  The parent independently
reloads the sidecar and incrementally publishes a byte-identical, independent,
read-back-verified tree to the mounted sync root before advancing.

There is no executor injection and no scientific command-line degree of
freedom.  Importing this module never launches work.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import stat
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from ..durable import atomic_write_json, fsync_directory, read_json, sha256_file
from ..models.uncertainty import NormalisationScale
from . import preflight as P
from . import repair_label_preflight as PF
from . import repair_label_run as R
from .fit_evidence import VerifiedFitEvidence, load_fit_evidence, run_confirmatory_fit
from .supervisor import AttemptOutcome, acquire_batch_lease, run_isolated_attempt


REPAIR_LABEL_LAUNCH_SCHEMA_VERSION = 1
REPAIR_LABEL_LAUNCH_FILE = "repair_label_launch_report.json"
REPAIR_LABEL_LAUNCH_DIRECTORY = "repair_label_launch_reports"
REPAIR_LABEL_LEASE_NAME = "week6-repair-label-smoke"
_WORKER_SCHEMA_VERSION = 1
_WORKER_KEYS = frozenset(
    {
        "worker_schema_version",
        "unit_id",
        "seed",
        "arm",
        "fit_id",
        "expected_git_commit",
        "normalisation",
    }
)


@dataclass(frozen=True)
class ValidatedRepairLabelPreflight:
    report_path: Path
    report_sha256: str
    git_commit: str
    output_root: Path
    staging_root: Path
    sync_root: Path
    sync_directory: Path
    report: Mapping[str, Any]


def _strict_keys(value: object, expected: set[str] | frozenset[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{what} must be an exact JSON object")
    if set(value) != set(expected):
        raise ValueError(
            f"{what} fields differ (missing={sorted(set(expected) - set(value))}, "
            f"extra={sorted(set(value) - set(expected))})"
        )
    return value


def _positive_number(value: object, *, what: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{what} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{what} must be a finite positive number")
    return result


def _is_reparse(info: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(info, "st_file_attributes", 0) & attribute)


def _tree_inventory(root: Path) -> tuple[dict[str, Any], ...]:
    try:
        root_info = root.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect evidence tree {root}: {exc}") from exc
    if stat.S_ISLNK(root_info.st_mode) or _is_reparse(root_info) or not stat.S_ISDIR(root_info.st_mode):
        raise ValueError(f"evidence tree must be a regular non-link directory: {root}")
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise ValueError(f"evidence tree contains link/alias {relative!r}")
        if stat.S_ISDIR(info.st_mode):
            rows.append({"path": relative, "kind": "directory"})
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"evidence tree contains special entry {relative!r}")
        if getattr(info, "st_nlink", 1) != 1:
            raise ValueError(f"evidence tree contains hard-linked alias {relative!r}")
        rows.append(
            {
                "path": relative,
                "kind": "file",
                "size_bytes": info.st_size,
                "sha256": sha256_file(path),
            }
        )
    if not rows:
        raise ValueError(f"evidence tree {root} is empty")
    return tuple(rows)


def _same_file_identity(left: Path, right: Path) -> bool:
    try:
        return os.path.samestat(left.stat(), right.stat())
    except (AttributeError, OSError):
        a, b = left.stat(), right.stat()
        return a.st_dev == b.st_dev and a.st_ino != 0 and a.st_ino == b.st_ino


def _verify_independent_trees(source: Path, destination: Path) -> tuple[dict[str, Any], ...]:
    source_inventory = _tree_inventory(source)
    destination_inventory = _tree_inventory(destination)
    if destination_inventory != source_inventory:
        raise ValueError("synced evidence tree differs from the complete source tree")
    for row in source_inventory:
        if row["kind"] != "file":
            continue
        relative = Path(row["path"])
        if _same_file_identity(source / relative, destination / relative):
            raise ValueError(
                f"synced evidence file {row['path']!r} aliases its source"
            )
        if (destination / relative).read_bytes() != (source / relative).read_bytes():
            raise ValueError(f"synced evidence file {row['path']!r} failed read-back")
    return source_inventory


def _sync_tree(source: Path, destination: Path) -> dict[str, Any]:
    """Durably publish a complete immutable tree inside the sync filesystem."""

    source = source.resolve(strict=True)
    destination_parent = destination.parent.resolve(strict=True)
    destination = destination_parent / destination.name
    inventory = _tree_inventory(source)
    if destination.exists() or destination.is_symlink():
        checked = _verify_independent_trees(source, destination)
        return {
            "destination_path": str(destination.resolve(strict=True)),
            "entry_count": len(checked),
            "already_present": True,
        }

    temporary = destination_parent / f".{destination.name}.sync-{uuid.uuid4().hex}"
    if temporary.exists():
        raise ValueError(f"unexpected sync staging collision at {temporary}")
    temporary.mkdir()
    try:
        for row in inventory:
            target = temporary / Path(row["path"])
            if row["kind"] == "directory":
                target.mkdir(parents=True, exist_ok=False)
                fsync_directory(target.parent)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            from ..durable import atomic_write_bytes

            atomic_write_bytes(target, (source / Path(row["path"])).read_bytes())
        _verify_independent_trees(source, temporary)
        fsync_directory(temporary)
        try:
            os.replace(temporary, destination)
        except OSError as exc:
            if destination.exists():
                checked = _verify_independent_trees(source, destination)
                shutil.rmtree(temporary)
                return {
                    "destination_path": str(destination.resolve(strict=True)),
                    "entry_count": len(checked),
                    "already_present": True,
                }
            raise ValueError(
                f"cannot atomically publish synced tree {destination}: {exc}"
            ) from exc
        fsync_directory(destination_parent)
        checked = _verify_independent_trees(source, destination)
        return {
            "destination_path": str(destination.resolve(strict=True)),
            "entry_count": len(checked),
            "already_present": False,
        }
    except Exception:
        # A failed unpublished copy has no evidentiary value.  Preserve a
        # published destination, but remove only this unique private staging
        # directory so a later resume cannot mistake it for durable evidence.
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def _scale_from_row(value: object) -> NormalisationScale | None:
    if value is None:
        return None
    row = _strict_keys(
        value,
        {"scale", "scale_n_reference", "scale_domain", "scale_source"},
        what="worker normalisation",
    )
    vector = row["scale"]
    if type(vector) is not list or not vector or any(type(v) not in {int, float} for v in vector):
        raise ValueError("worker normalisation.scale must be a nonempty numeric list")
    if any(not math.isfinite(float(v)) or float(v) <= 0.0 for v in vector):
        raise ValueError("worker normalisation.scale values must be finite and positive")
    n_reference = row["scale_n_reference"]
    if type(n_reference) is not int or n_reference <= 0:
        raise ValueError("worker scale_n_reference must be a positive exact integer")
    if type(row["scale_domain"]) is not str or type(row["scale_source"]) is not str:
        raise ValueError("worker scale provenance must be exact strings")
    return NormalisationScale(
        torch.tensor(vector, dtype=torch.float32),
        n_reference=n_reference,
        domain=row["scale_domain"],
        source=row["scale_source"],
    )


def _fit_worker(attempt_dir: Path, payload: Any) -> Mapping[str, Any]:
    """Spawn target: validate the exact obligation, then execute one fit."""

    row = _strict_keys(payload, _WORKER_KEYS, what="repair-label worker payload")
    if row["worker_schema_version"] != _WORKER_SCHEMA_VERSION:
        raise ValueError("repair-label worker payload has the wrong schema")
    if row["unit_id"] != R.WEEK6_SMOKE_UNIT_ID:
        raise ValueError("repair-label worker payload names the wrong smoke unit")
    if type(row["seed"]) is not int or row["seed"] not in range(1000, 1020):
        raise ValueError("repair-label worker payload names an unregistered seed")
    if row["arm"] not in {"baseline", "data_repair", "feature_repair"}:
        raise ValueError("repair-label worker payload names an unregistered arm")
    if type(row["expected_git_commit"]) is not str:
        raise ValueError("worker expected Git commit must be a string")
    unit = R.registered_week6_smoke_unit()
    _, _, planned = R._registered_plan(unit, Path(attempt_dir).parent)
    matches = [
        item
        for item in planned
        if item.seed == row["seed"] and item.arm == row["arm"]
    ]
    if len(matches) != 1 or matches[0].spec.fit_id != row["fit_id"]:
        raise ValueError("repair-label worker payload diverges from the exact plan")
    scale = _scale_from_row(row["normalisation"])
    if row["arm"] == "baseline" and scale is not None:
        raise ValueError("baseline worker must derive its own pool scale")
    if row["arm"] != "baseline" and scale is None:
        raise ValueError("repair worker must reuse its baseline scale")

    # ``expected_git_commit`` is checked by run_confirmatory_fit before it
    # generates a pool or trains, then checked again while reopening evidence.
    run_confirmatory_fit(
        unit,
        arm=row["arm"],
        seed=row["seed"],
        out_dir=attempt_dir,
        scale=scale,
        expected_git_commit=row["expected_git_commit"],
    )
    verified = load_fit_evidence(
        attempt_dir, expected_git_commit=row["expected_git_commit"]
    )
    return {
        "unit_id": verified.unit_id,
        "seed": verified.seed,
        "arm": verified.arm,
        "fit_id": verified.fit_id,
        "git_commit": row["expected_git_commit"],
        "fit_evidence_digest": verified.execution_digest,
    }


def _validate_preflight_copy(report_path: Path, sync_directory: Path) -> None:
    destination = sync_directory / PF.REPAIR_LABEL_PREFLIGHT_FILE
    PF._regular_file(report_path, what="local smoke preflight report")
    PF._regular_file(destination, what="synced smoke preflight report")
    if _same_file_identity(report_path, destination):
        raise ValueError("synced smoke preflight report aliases the source")
    if report_path.read_bytes() != destination.read_bytes():
        raise ValueError("synced smoke preflight report differs from the source")


def _validate_repair_label_preflight(
    preflight_report: str | Path,
    *,
    output_root: str | Path,
    sync_root: str | Path,
    require_current_commit: bool,
) -> ValidatedRepairLabelPreflight:
    """Re-attest the immutable report, environment, roots, plan, and sync.

    The private ``require_current_commit=False`` road exists only for the
    correction-only finalizer: it keeps the original preflight commit as the
    required commit of every immutable fit, while requiring the current
    finalizer tree to be clean, trustworthy, and otherwise environment-identical.
    The public launcher has no such option and always requires exact equality.
    """

    if type(require_current_commit) is not bool:
        raise ValueError("require_current_commit must be an exact bool")

    requested = Path(preflight_report)
    PF._regular_file(requested, what="smoke preflight report")
    path = requested.resolve(strict=True)
    if path.name != PF.REPAIR_LABEL_PREFLIGHT_FILE:
        raise ValueError(
            f"smoke preflight report must be named {PF.REPAIR_LABEL_PREFLIGHT_FILE!r}"
        )
    raw = path.read_bytes()
    report = _strict_keys(
        read_json(path),
        {
            "repair_label_preflight_schema_version",
            "status",
            "launch_performed",
            "plan",
            "environment",
            "device",
            "storage",
            "sync_destination_identity",
            "sync_directory",
            "sync_canary",
            "sync_receipt",
        },
        what="smoke preflight report",
    )
    if report["repair_label_preflight_schema_version"] != PF.REPAIR_LABEL_PREFLIGHT_SCHEMA_VERSION:
        raise ValueError("smoke preflight report has the wrong schema version")
    if report["status"] != "ready" or report["launch_performed"] is not False:
        raise ValueError("smoke preflight report is not an unconsumed ready report")

    storage = _strict_keys(
        report["storage"], {"minimum_free_bytes", "roots"}, what="smoke storage"
    )
    roots_row = _strict_keys(
        storage["roots"], {"preflight", "output", "staging", "sync"}, what="smoke roots"
    )
    minimum = storage["minimum_free_bytes"]
    if type(minimum) is not int or minimum < 0:
        raise ValueError("smoke preflight minimum free bytes is invalid")
    roots, _ = P._verify_storage(
        preflight_dir=roots_row["preflight"]["path"],
        output_root=roots_row["output"]["path"],
        staging_root=roots_row["staging"]["path"],
        sync_root=roots_row["sync"]["path"],
        minimum_free_bytes=minimum,
    )
    for name, root in roots.items():
        snapshot = _strict_keys(
            roots_row[name], {"path", "writable", "free_bytes"}, what=f"smoke {name} root"
        )
        if snapshot["path"] != str(root) or snapshot["writable"] is not True:
            raise ValueError(f"smoke preflight {name} root no longer matches")
    if roots["preflight"] != path.parent:
        raise ValueError("smoke preflight report is outside its recorded root")
    if roots["output"] != Path(output_root).resolve(strict=True):
        raise ValueError("requested output root differs from smoke preflight")
    if roots["sync"] != Path(sync_root).resolve(strict=True):
        raise ValueError("requested sync root differs from smoke preflight")
    if PF._filesystem_identity(roots["output"]) != PF._filesystem_identity(roots["staging"]):
        raise ValueError("smoke output/staging roots no longer share a volume")

    state, versions, pins = P._verify_environment()
    current_environment = {
        "git": {
            "commit": state.commit,
            "branch": state.branch,
            "dirty": state.dirty,
            "trustworthy": state.trustworthy,
        },
        "python": sys.version.split()[0],
        "platform": __import__("platform").platform(),
        "packages": versions,
        "exact_pins": pins,
    }
    recorded_environment = _strict_keys(
        report["environment"],
        {"git", "python", "platform", "packages", "exact_pins"},
        what="smoke preflight environment",
    )
    recorded_git = _strict_keys(
        recorded_environment["git"],
        {"commit", "branch", "dirty", "trustworthy"},
        what="smoke preflight git state",
    )
    if (
        type(recorded_git["commit"]) is not str
        or not recorded_git["commit"]
        or recorded_git["dirty"] is not False
        or recorded_git["trustworthy"] is not True
    ):
        raise ValueError("smoke preflight does not name one clean trustworthy commit")
    if require_current_commit:
        if recorded_environment != current_environment:
            raise ValueError("smoke preflight is not the current clean pinned environment")
    else:
        if state.dirty or not state.trustworthy:
            raise ValueError("correction finalization requires a clean trustworthy tree")
        for key in ("python", "platform", "packages", "exact_pins"):
            if recorded_environment[key] != current_environment[key]:
                raise ValueError(
                    "correction finalizer environment differs from the fit preflight "
                    f"at {key!r}"
                )
    if report["device"] != P._verify_device("cpu"):
        raise ValueError("smoke preflight is not the current frozen CPU route")

    plan, plan_path = PF._plan_snapshot(roots["output"])
    observed_plan = _strict_keys(
        report["plan"], set(plan) | {"sync"}, what="smoke preflight plan"
    )
    if {key: observed_plan[key] for key in plan} != plan:
        raise ValueError("smoke preflight plan differs from the exact current plan")
    sync_directory = PF.ensure_regular_child_directory(
        roots["sync"], PF.REPAIR_LABEL_SYNC_DIRECTORY
    )
    if report["sync_directory"] != str(sync_directory):
        raise ValueError("smoke preflight names the wrong sync directory")
    plan_sync = PF.sync_immutable_file(
        plan_path, sync_directory / R.REPAIR_LABEL_PLAN_FILE
    )
    if observed_plan["sync"] != plan_sync:
        raise ValueError("smoke preflight plan sync receipt no longer matches")
    if report["sync_destination_identity"] != P._validate_destination_identity(
        report["sync_destination_identity"]
    ):
        raise ValueError("smoke sync destination identity is invalid")
    canary, canary_receipt = P._run_sync_canary(
        roots={**roots, "sync": sync_directory},
        plan_digest=plan["plan_digest"],
        destination_identity=report["sync_destination_identity"],
        adapter=P.sync_canary_to_mounted_directory,
    )
    if report["sync_canary"] != canary or report["sync_receipt"] != canary_receipt:
        raise ValueError("smoke preflight sync canary no longer revalidates exactly")
    _validate_preflight_copy(path, sync_directory)
    if path.read_bytes() != raw:
        raise ValueError("smoke preflight report changed during validation")
    return ValidatedRepairLabelPreflight(
        report_path=path,
        report_sha256=sha256_file(path),
        git_commit=recorded_git["commit"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        sync_directory=sync_directory,
        report=report,
    )


def validate_repair_label_preflight(
    preflight_report: str | Path,
    *,
    output_root: str | Path,
    sync_root: str | Path,
) -> ValidatedRepairLabelPreflight:
    """Re-attest a launch preflight against the exact current commit."""

    return _validate_repair_label_preflight(
        preflight_report,
        output_root=output_root,
        sync_root=sync_root,
        require_current_commit=True,
    )


def _load_bound_fit(planned: R._PlannedFit, *, expected_commit: str) -> VerifiedFitEvidence:
    if planned.path.is_symlink() or not planned.path.is_dir():
        if planned.path.exists() or planned.path.is_symlink():
            raise ValueError(f"planned fit path is partial or a link: {planned.path}")
        raise FileNotFoundError(planned.path)
    try:
        loaded = load_fit_evidence(
            planned.path, expected_git_commit=expected_commit
        )
    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise ValueError(
            f"existing fit {planned.path} is partial, divergent, or bound to "
            "the wrong preflight commit"
        ) from exc
    return R._validate_loaded(loaded, planned=planned)


def _payload(planned: R._PlannedFit, *, commit: str, scale: NormalisationScale | None) -> dict[str, Any]:
    return {
        "worker_schema_version": _WORKER_SCHEMA_VERSION,
        "unit_id": R.WEEK6_SMOKE_UNIT_ID,
        "seed": planned.seed,
        "arm": planned.arm,
        "fit_id": planned.spec.fit_id,
        "expected_git_commit": commit,
        "normalisation": None if scale is None else scale.as_row(),
    }


def _require_success(outcome: object, *, planned: R._PlannedFit) -> Path:
    if type(outcome) is not AttemptOutcome:
        raise ValueError("isolated smoke attempt returned a non-exact AttemptOutcome")
    if not outcome.succeeded or outcome.canonical_dir is None:
        raise ValueError(
            f"isolated smoke fit {planned.spec.fit_id} failed with "
            f"status={outcome.status!r}, error={outcome.error!r}; attempt evidence "
            f"is preserved at {outcome.attempt_dir}"
        )
    canonical = outcome.canonical_dir.resolve(strict=True)
    if canonical != planned.path.resolve(strict=True):
        raise ValueError("isolated smoke attempt published to the wrong fit path")
    return canonical


def launch_repair_label_smoke(
    *,
    preflight_report: str | Path,
    output_root: str | Path,
    sync_root: str | Path,
    attempt_timeout_seconds: float,
) -> dict[str, Any]:
    """Launch/resume only the exact registered smoke through fixed boundaries."""

    timeout = _positive_number(
        attempt_timeout_seconds, what="attempt_timeout_seconds"
    )
    validated = validate_repair_label_preflight(
        preflight_report, output_root=output_root, sync_root=sync_root
    )
    unit = R.registered_week6_smoke_unit()
    model_arm, seeds, planned = R._registered_plan(unit, validated.output_root)
    if tuple((item.seed, item.arm) for item in planned) != tuple(
        (seed, arm)
        for seed in range(1000, 1020)
        for arm in ("baseline", "data_repair", "feature_repair")
    ):
        raise ValueError("launch plan changed after preflight validation")

    lease = acquire_batch_lease(
        validated.output_root, lease_name=REPAIR_LABEL_LEASE_NAME
    )
    sync_fit_directory = PF.ensure_regular_child_directory(
        validated.sync_directory, R.FIT_DIRECTORY
    )
    executed = 0
    resumed = 0
    synced = 0
    released_path: Path | None = None
    baseline_scale: NormalisationScale | None = None
    try:
        for planned_fit in planned:
            if planned_fit.arm == "baseline":
                baseline_scale = None
            try:
                verified = _load_bound_fit(
                    planned_fit, expected_commit=validated.git_commit
                )
                resumed += 1
            except FileNotFoundError:
                outcome = run_isolated_attempt(
                    _fit_worker,
                    root=validated.output_root,
                    staging_root=validated.staging_root,
                    job_id=planned_fit.spec.fit_id,
                    payload=_payload(
                        planned_fit,
                        commit=validated.git_commit,
                        scale=baseline_scale,
                    ),
                    timeout_seconds=timeout,
                )
                _require_success(outcome, planned=planned_fit)
                verified = _load_bound_fit(
                    planned_fit, expected_commit=validated.git_commit
                )
                executed += 1

            if planned_fit.arm == "baseline":
                baseline_scale = verified.scale
            elif baseline_scale is None or R._scale_fingerprint(verified.scale) != R._scale_fingerprint(baseline_scale):
                raise ValueError(
                    f"repair fit {planned_fit.spec.fit_id} does not reuse its "
                    "seed's exact baseline scale"
                )
            destination = sync_fit_directory / planned_fit.spec.fit_id
            _sync_tree(planned_fit.path, destination)
            synced += 1

        result = R._finalize_registered_label(
            validated.output_root, expected_git_commit=validated.git_commit
        )
        forbidden = {
            "excluded",
            "exclusion_rate",
            "registered_planning_exclusion_rate",
            "planning_assumption_missed",
            "shortfall_before_reserve",
        }
        if forbidden & set(result.counts):
            raise ValueError("Week-6 count artifact crossed into Week-8 analysis")
        label_sync = PF.sync_immutable_file(
            result.label_path, validated.sync_directory / result.label_path.name
        )
        count_sync = PF.sync_immutable_file(
            result.count_path, validated.sync_directory / result.count_path.name
        )
    finally:
        released_path = lease.release()

    report = {
        "repair_label_launch_schema_version": REPAIR_LABEL_LAUNCH_SCHEMA_VERSION,
        "status": "complete",
        "unit_id": R.WEEK6_SMOKE_UNIT_ID,
        "seeds": list(seeds),
        "arms": ["baseline", "data_repair", model_arm],
        "fit_count": len(planned),
        "executed_fits": executed,
        "resumed_fits": resumed,
        "synced_fits": synced,
        "preflight": {
            "path": str(validated.report_path),
            "sha256": validated.report_sha256,
            "git_commit": validated.git_commit,
        },
        "execution": {
            "device": "cpu",
            "fresh_spawn_per_fit": True,
            "attempt_timeout_seconds": timeout,
            "separate_same_volume_staging": True,
            "stale_lease_recovery": False,
            "executor_injection": False,
        },
        "label": label_sync,
        "counts": {"values": result.counts, "sync": count_sync},
        "lease": {
            "name": REPAIR_LABEL_LEASE_NAME,
            "released_history_path": str(released_path.resolve(strict=True)),
        },
    }
    launch_id = uuid.uuid4().hex
    report["launch_id"] = launch_id
    report_path = (
        validated.output_root
        / REPAIR_LABEL_LAUNCH_DIRECTORY
        / f"{launch_id}.json"
    )
    atomic_write_json(report_path, report)
    persisted = read_json(report_path)
    if persisted != report:
        raise ValueError("persisted smoke launch report differs from memory")
    sync_report_directory = PF.ensure_regular_child_directory(
        validated.sync_directory, REPAIR_LABEL_LAUNCH_DIRECTORY
    )
    PF.sync_immutable_file(
        report_path,
        sync_report_directory / report_path.name,
    )
    return json.loads(json.dumps(report))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bu.experiments.repair_label_launch",
        description=(
            "Launch/resume the exact Week-6 repair-label smoke after an "
            "immutable ready preflight."
        ),
    )
    parser.add_argument("--preflight-report", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--sync-root", required=True, type=Path)
    parser.add_argument("--attempt-timeout-seconds", required=True, type=float)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        report = launch_repair_label_smoke(
            preflight_report=arguments.preflight_report,
            output_root=arguments.output_root,
            sync_root=arguments.sync_root,
            attempt_timeout_seconds=arguments.attempt_timeout_seconds,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
