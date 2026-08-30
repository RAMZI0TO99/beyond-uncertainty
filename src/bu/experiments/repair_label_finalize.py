"""Correction-only finalizer for the immutable Week-6 smoke sidecars.

This module exists because the first production finalization failed closed after
all sixty fits: the old consumer required a feature repair's encoded observation
pool digest to equal the baseline digest even though restoring a withheld feature
necessarily changes encoded ``obs``/``next_obs``.  D-147 corrects that consumer
invariant without retraining or mutating a fit.

The boundary below has no fitting, process-spawn, timeout, executor, or recovery
capability.  It revalidates the original immutable preflight, permits only a clean
environment-identical correction commit, reloads every sidecar against the
original fit commit, rechecks exact plan/order/scale and durable copies, derives
the label, and records both commits in a correction report.
"""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_file
from ..runrecord import git_state
from . import repair_label_launch as L
from . import repair_label_preflight as PF
from . import repair_label_run as R
from .supervisor import acquire_batch_lease


REPAIR_LABEL_FINALIZATION_SCHEMA_VERSION = 1
REPAIR_LABEL_FINALIZATION_DIRECTORY = "repair_label_finalization_reports"
REPAIR_LABEL_FINALIZATION_LEASE = "week6-repair-label-finalization"
CORRECTION_RECORD = "D-147"


def finalize_existing_repair_label_smoke(
    *,
    preflight_report: str | Path,
    output_root: str | Path,
    sync_root: str | Path,
) -> dict[str, Any]:
    """Finalize exactly sixty existing fits; this function cannot train one."""

    validated = L._validate_repair_label_preflight(
        preflight_report,
        output_root=output_root,
        sync_root=sync_root,
        require_current_commit=False,
    )
    finalizer = git_state()
    if finalizer.dirty or not finalizer.trustworthy:
        raise ValueError("repair-label correction finalizer requires a clean tree")
    if finalizer.commit == validated.git_commit:
        raise ValueError(
            "the correction-only finalizer requires a commit after the failed "
            "preflight commit; use the ordinary launcher when source is unchanged"
        )

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
    synced_fits = 0
    baseline_scale = None
    sync_fit_directory = PF.ensure_regular_child_directory(
        validated.sync_directory, R.FIT_DIRECTORY
    )
    try:
        for item in planned:
            verified = L._load_bound_fit(
                item, expected_commit=validated.git_commit
            )
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
            L._sync_tree(
                item.path, sync_fit_directory / item.spec.fit_id
            )
            verified_fits += 1
            synced_fits += 1

        if verified_fits != 60 or synced_fits != 60:
            raise ValueError(
                f"correction finalizer requires 60/60 verified and synced fits, "
                f"got {verified_fits}/{synced_fits}"
            )
        result = R._finalize_registered_label(
            validated.output_root,
            expected_git_commit=validated.git_commit,
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
        label_sync = PF.sync_immutable_file(
            result.label_path, validated.sync_directory / result.label_path.name
        )
        count_sync = PF.sync_immutable_file(
            result.count_path, validated.sync_directory / result.count_path.name
        )
    finally:
        released_path = lease.release()

    report: dict[str, Any] = {
        "repair_label_finalization_schema_version": (
            REPAIR_LABEL_FINALIZATION_SCHEMA_VERSION
        ),
        "status": "complete_after_fail_closed_correction",
        "correction_record": CORRECTION_RECORD,
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
        "synced_fits": synced_fits,
        "preflight": {
            "path": str(validated.report_path),
            "sha256": validated.report_sha256,
            "fit_commit": validated.git_commit,
        },
        "finalizer": {
            "commit": finalizer.commit,
            "branch": finalizer.branch,
            "dirty": finalizer.dirty,
            "trustworthy": finalizer.trustworthy,
        },
        "label": label_sync,
        "counts": {"values": result.counts, "sync": count_sync},
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
    sync_report_directory = PF.ensure_regular_child_directory(
        validated.sync_directory, REPAIR_LABEL_FINALIZATION_DIRECTORY
    )
    report_sync = PF.sync_immutable_file(
        report_path, sync_report_directory / report_path.name
    )
    return {
        **report,
        "report": {
            "path": str(report_path.resolve(strict=True)),
            "sha256": sha256_file(report_path),
            "sync": report_sync,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize the existing immutable Week-6 smoke fits after D-147; "
            "this command has no fitting capability."
        )
    )
    parser.add_argument("--preflight-report", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--sync-root", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> dict[str, Any]:
    args = _parser().parse_args(argv)
    report = finalize_existing_repair_label_smoke(
        preflight_report=args.preflight_report,
        output_root=args.output_root,
        sync_root=args.sync_root,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":  # pragma: no cover
    main()
