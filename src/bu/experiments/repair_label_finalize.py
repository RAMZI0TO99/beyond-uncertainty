"""Project-local correction finalizer for immutable Week-6 smoke sidecars.

The first production finalization failed closed after all sixty fits because the
old consumer required a feature repair's encoded observation-pool digest to equal
the baseline digest. Restoring a withheld feature necessarily changes encoded
``obs``/``next_obs``; D-147 corrects that invariant without retraining a fit.

After the owner required all further writes to stay inside the project workspace
(D-148), this boundary treats the original C-volume copy as read-only historical
evidence. It verifies that copy without touching it, reloads every sidecar against
the original fit commit, and writes all new independent copies, label, four counts,
and correction report to a fixed project-local evidence root. It has no fitting,
process-spawn, timeout, executor, or recovery capability.
"""

from __future__ import annotations

import argparse
import json
import platform
import stat
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_file
from ..runrecord import git_state
from . import preflight as P
from . import repair_label_launch as L
from . import repair_label_preflight as PF
from . import repair_label_run as R
from .supervisor import acquire_batch_lease


REPAIR_LABEL_FINALIZATION_SCHEMA_VERSION = 2
REPAIR_LABEL_FINALIZATION_DIRECTORY = "repair_label_finalization_reports"
REPAIR_LABEL_FINALIZATION_LEASE = "week6-repair-label-finalization"
PROJECT_EVIDENCE_SUFFIX = "-project-evidence"
CORRECTION_RECORDS = ("D-147", "D-148")


def _regular_directory(path: Path, *, what: str) -> Path:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {what} {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or PF._is_reparse(info) or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{what} must be a regular non-link directory: {path}")
    return path.resolve(strict=True)


def _verify_receipt_file(
    path: Path, *, sha256: object, size_bytes: object, what: str
) -> None:
    PF._regular_file(path, what=what)
    if type(sha256) is not str or len(sha256) != 64:
        raise ValueError(f"{what} receipt has an invalid sha256")
    if type(size_bytes) is not int or size_bytes < 0:
        raise ValueError(f"{what} receipt has an invalid size_bytes")
    if path.stat().st_size != size_bytes or sha256_file(path) != sha256:
        raise ValueError(f"{what} bytes do not match the immutable receipt")


def _verify_independent_receipt(
    value: object, *, source: Path, what: str
) -> Path:
    row = L._strict_keys(
        value,
        {
            "source_path",
            "destination_path",
            "sha256",
            "size_bytes",
            "independent_file",
        },
        what=what,
    )
    source = source.resolve(strict=True)
    if Path(row["source_path"]).resolve(strict=True) != source:
        raise ValueError(f"{what} names the wrong source path")
    destination = Path(row["destination_path"]).resolve(strict=True)
    _verify_receipt_file(
        source,
        sha256=row["sha256"],
        size_bytes=row["size_bytes"],
        what=f"{what} source",
    )
    _verify_receipt_file(
        destination,
        sha256=row["sha256"],
        size_bytes=row["size_bytes"],
        what=f"{what} destination",
    )
    if row["independent_file"] is not True or PF._same_file_identity(source, destination):
        raise ValueError(f"{what} destination is not an independent file")
    if source.read_bytes() != destination.read_bytes():
        raise ValueError(f"{what} destination differs from source")
    return destination


def _validate_original_preflight_read_only(
    preflight_report: str | Path, *, output_root: str | Path
) -> L.ValidatedRepairLabelPreflight:
    """Validate the old preflight and C copy without writing outside the project."""

    requested = Path(preflight_report)
    PF._regular_file(requested, what="smoke preflight report")
    path = requested.resolve(strict=True)
    if path.name != PF.REPAIR_LABEL_PREFLIGHT_FILE:
        raise ValueError(
            f"smoke preflight report must be named {PF.REPAIR_LABEL_PREFLIGHT_FILE!r}"
        )
    raw = path.read_bytes()
    report = L._strict_keys(
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

    storage = L._strict_keys(
        report["storage"], {"minimum_free_bytes", "roots"}, what="smoke storage"
    )
    roots_row = L._strict_keys(
        storage["roots"], {"preflight", "output", "staging", "sync"}, what="smoke roots"
    )
    roots: dict[str, Path] = {}
    for name in ("preflight", "output", "staging", "sync"):
        snapshot = L._strict_keys(
            roots_row[name],
            {"path", "writable", "free_bytes"},
            what=f"smoke {name} root",
        )
        roots[name] = _regular_directory(Path(snapshot["path"]), what=f"smoke {name} root")
        if snapshot["path"] != str(roots[name]) or snapshot["writable"] is not True:
            raise ValueError(f"smoke preflight {name} root no longer matches")
    if roots["preflight"] != path.parent:
        raise ValueError("smoke preflight report is outside its recorded root")
    if roots["output"] != Path(output_root).resolve(strict=True):
        raise ValueError("requested output root differs from smoke preflight")

    state, versions, pins = P._verify_environment()
    if state.dirty or not state.trustworthy:
        raise ValueError("correction finalization requires a clean trustworthy tree")
    recorded_environment = L._strict_keys(
        report["environment"],
        {"git", "python", "platform", "packages", "exact_pins"},
        what="smoke preflight environment",
    )
    recorded_git = L._strict_keys(
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
        raise ValueError("smoke preflight does not name one clean trustworthy fit commit")
    current_non_git = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": versions,
        "exact_pins": pins,
    }
    for key, value in current_non_git.items():
        if recorded_environment[key] != value:
            raise ValueError(
                f"correction environment differs from fit preflight at {key!r}"
            )
    if report["device"] != P._verify_device("cpu"):
        raise ValueError("smoke preflight is not the frozen CPU route")

    plan, plan_path = PF._plan_snapshot(roots["output"])
    observed_plan = L._strict_keys(
        report["plan"], set(plan) | {"sync"}, what="smoke preflight plan"
    )
    if {key: observed_plan[key] for key in plan} != plan:
        raise ValueError("smoke preflight plan differs from the exact current plan")
    plan_destination = _verify_independent_receipt(
        observed_plan["sync"], source=plan_path, what="historical plan sync"
    )

    sync_directory = _regular_directory(
        Path(report["sync_directory"]), what="historical smoke sync directory"
    )
    if sync_directory != roots["sync"] / PF.REPAIR_LABEL_SYNC_DIRECTORY:
        raise ValueError("smoke preflight names the wrong historical sync directory")
    if plan_destination.parent != sync_directory:
        raise ValueError("historical plan copy is outside the recorded sync directory")
    L._validate_preflight_copy(path, sync_directory)

    canary = L._strict_keys(
        report["sync_canary"],
        {"source_path", "destination_path", "sha256", "size_bytes"},
        what="historical sync canary",
    )
    canary_source = Path(canary["source_path"]).resolve(strict=True)
    canary_destination = Path(canary["destination_path"]).resolve(strict=True)
    _verify_receipt_file(
        canary_source,
        sha256=canary["sha256"],
        size_bytes=canary["size_bytes"],
        what="historical canary source",
    )
    _verify_receipt_file(
        canary_destination,
        sha256=canary["sha256"],
        size_bytes=canary["size_bytes"],
        what="historical canary destination",
    )
    if PF._same_file_identity(canary_source, canary_destination):
        raise ValueError("historical canary destination aliases its source")
    canary_receipt = L._strict_keys(
        report["sync_receipt"],
        {
            "schema_version",
            "destination_identity",
            "destination_path",
            "sha256",
            "size_bytes",
        },
        what="historical canary receipt",
    )
    if (
        canary_receipt["schema_version"] != P.SYNC_RECEIPT_SCHEMA_VERSION
        or canary_receipt["destination_identity"] != report["sync_destination_identity"]
        or Path(canary_receipt["destination_path"]).resolve(strict=True) != canary_destination
        or canary_receipt["sha256"] != canary["sha256"]
        or canary_receipt["size_bytes"] != canary["size_bytes"]
    ):
        raise ValueError("historical canary receipt no longer matches")
    if path.read_bytes() != raw:
        raise ValueError("smoke preflight report changed during read-only validation")
    return L.ValidatedRepairLabelPreflight(
        report_path=path,
        report_sha256=sha256_file(path),
        git_commit=recorded_git["commit"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        sync_directory=sync_directory,
        report=report,
    )


def _project_evidence_root(output_root: Path) -> Path:
    name = output_root.name
    if not name.endswith("-output"):
        raise ValueError("smoke output root name must end with '-output'")
    candidate = output_root.parent / f"{name[:-len('-output')]}{PROJECT_EVIDENCE_SUFFIX}"
    root = _regular_directory(candidate, what="project evidence root")
    if any(root.iterdir()):
        raise ValueError(f"project evidence root must be empty before finalization: {root}")
    return root


def finalize_existing_repair_label_smoke(
    *, preflight_report: str | Path, output_root: str | Path
) -> dict[str, Any]:
    """Finalize sixty existing fits and write only inside the project workspace."""

    validated = _validate_original_preflight_read_only(
        preflight_report, output_root=output_root
    )
    finalizer = git_state()
    if finalizer.dirty or not finalizer.trustworthy:
        raise ValueError("repair-label correction finalizer requires a clean tree")
    if finalizer.commit == validated.git_commit:
        raise ValueError(
            "the correction-only finalizer requires a commit after the failed "
            "preflight commit; use the ordinary launcher when source is unchanged"
        )
    evidence_root = _project_evidence_root(validated.output_root)

    unit = R.registered_week6_smoke_unit()
    model_arm, seeds, planned = R._registered_plan(unit, validated.output_root)
    expected_order = tuple(
        (seed, arm)
        for seed in range(1000, 1020)
        for arm in ("baseline", "data_repair", "feature_repair")
    )
    if model_arm != "feature_repair" or tuple(
        (item.seed, item.arm) for item in planned
    ) != expected_order:
        raise ValueError("correction finalizer is not the exact registered smoke plan")

    lease = acquire_batch_lease(
        validated.output_root, lease_name=REPAIR_LABEL_FINALIZATION_LEASE
    )
    released_path: Path | None = None
    verified_fits = 0
    project_copied_fits = 0
    baseline_scale = None
    project_fit_directory = PF.ensure_regular_child_directory(evidence_root, R.FIT_DIRECTORY)
    preflight_copy = PF.sync_immutable_file(
        validated.report_path, evidence_root / validated.report_path.name
    )
    plan_path = validated.output_root / R.REPAIR_LABEL_PLAN_FILE
    plan_copy = PF.sync_immutable_file(plan_path, evidence_root / plan_path.name)
    canary_source = Path(validated.report["sync_canary"]["source_path"])
    canary_copy = PF.sync_immutable_file(canary_source, evidence_root / canary_source.name)
    try:
        for item in planned:
            verified = L._load_bound_fit(item, expected_commit=validated.git_commit)
            if item.arm == "baseline":
                baseline_scale = verified.scale
            elif (
                baseline_scale is None
                or R._scale_fingerprint(verified.scale)
                != R._scale_fingerprint(baseline_scale)
            ):
                raise ValueError(
                    f"repair fit {item.spec.fit_id} does not reuse its seed's "
                    "exact baseline scale"
                )
            L._sync_tree(item.path, project_fit_directory / item.spec.fit_id)
            verified_fits += 1
            project_copied_fits += 1
        if verified_fits != 60 or project_copied_fits != 60:
            raise ValueError(
                "correction finalizer requires 60/60 verified and project-copied "
                f"fits, got {verified_fits}/{project_copied_fits}"
            )
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
            raise ValueError("Week-6 correction crossed into Week-8 analysis")
        label_copy = PF.sync_immutable_file(
            result.label_path, evidence_root / result.label_path.name
        )
        count_copy = PF.sync_immutable_file(
            result.count_path, evidence_root / result.count_path.name
        )
    finally:
        released_path = lease.release()

    report: dict[str, Any] = {
        "repair_label_finalization_schema_version": REPAIR_LABEL_FINALIZATION_SCHEMA_VERSION,
        "status": "complete_after_fail_closed_correction",
        "correction_records": list(CORRECTION_RECORDS),
        "corrected_invariant": (
            "feature repair preserves action/episode/step latent-trajectory "
            "inventories while its encoded obs/next_obs pool digest must differ"
        ),
        "unit_id": R.WEEK6_SMOKE_UNIT_ID,
        "seeds": list(seeds),
        "arms": ["baseline", "data_repair", model_arm],
        "fit_count": len(planned),
        "executed_fits": 0,
        "retrained_fits": 0,
        "verified_existing_fits": verified_fits,
        "project_copied_fits": project_copied_fits,
        "preflight": {
            "path": str(validated.report_path),
            "sha256": validated.report_sha256,
            "fit_commit": validated.git_commit,
        },
        "historical_sync": {
            "mode": "read_only",
            "root": str(validated.sync_root),
            "directory": str(validated.sync_directory),
        },
        "project_evidence": {
            "root": str(evidence_root),
            "preflight": preflight_copy,
            "plan": plan_copy,
            "canary": canary_copy,
        },
        "finalizer": {
            "commit": finalizer.commit,
            "branch": finalizer.branch,
            "dirty": finalizer.dirty,
            "trustworthy": finalizer.trustworthy,
        },
        "label": label_copy,
        "counts": {"values": result.counts, "copy": count_copy},
        "lease": {
            "name": REPAIR_LABEL_FINALIZATION_LEASE,
            "released_history_path": str(released_path.resolve(strict=True)),
        },
    }
    report_id = uuid.uuid4().hex
    report["finalization_id"] = report_id
    report_path = (
        validated.output_root
        / REPAIR_LABEL_FINALIZATION_DIRECTORY
        / f"{report_id}.json"
    )
    atomic_write_json(report_path, report)
    if read_json(report_path) != report:
        raise ValueError("persisted correction finalization report differs from memory")
    project_report_directory = PF.ensure_regular_child_directory(
        evidence_root, REPAIR_LABEL_FINALIZATION_DIRECTORY
    )
    report_copy = PF.sync_immutable_file(
        report_path, project_report_directory / report_path.name
    )
    return {
        **report,
        "report": {
            "path": str(report_path.resolve(strict=True)),
            "sha256": sha256_file(report_path),
            "copy": report_copy,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize immutable Week-6 smoke fits after D-147 and write new "
            "evidence only inside the project workspace; no fitting capability."
        )
    )
    parser.add_argument("--preflight-report", required=True)
    parser.add_argument("--output-root", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> dict[str, Any]:
    args = _parser().parse_args(argv)
    report = finalize_existing_repair_label_smoke(
        preflight_report=args.preflight_report,
        output_root=args.output_root,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":  # pragma: no cover
    main()
