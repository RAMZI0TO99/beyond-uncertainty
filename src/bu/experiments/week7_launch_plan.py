"""Exact Week-7 baseline launch inventory, not permission to execute a fit.

The immutable D-153 preparation supplies all 100 Experiment-2A requirements
and all 675 sweep baselines. Five historical smoke baselines MUST be reused;
their absence is never grounds for replacement training. The complete sweep
partition is outcome-independent: group id, then unit id and seed. Only the
95 outstanding Experiment-2A fits and the first complete sweep group are in
the current operational scope. Later groups remain explicit outstanding work.

No source outcomes, directory discovery, caller-selected jobs or executor are
accepted here. Loading rederives full Configs, including non-identity training
fields, so a resigned document is not its own authority. Source reconciliation
and contemporaneous sweep anchors are mandatory at the separate launch gate.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_file
from ..streams import group_of
from . import week7_plan as W
from .batch import BatchJob
from .enumerate_units import stage_of


WEEK7_LAUNCH_PLAN_SCHEMA_VERSION = 1
WEEK7_LAUNCH_PLAN_FILE = "week7_baseline_launch_plan.json"
PREPARATION_PATH = Path(
    "D:/Aenv/pro/pro/week7-preparation-2026-08-31/week7_baseline_preparation.json"
)
PREPARATION_SHA256 = "9b380e4bbefa4d3c1c5a52e6ab89f8b63cac42dbfaf90cf5b19419fcc9152044"
REUSED_FIT_IDS = tuple(f"f011e07e0a65-s{seed}" for seed in range(1000, 1005))
AUTHORIZED_BATCH_KEYS = ("exp2a", "sweep-001")


def _canonical(value: object) -> bytes:
    return W._canonical(value)


def reused_experiment_2a_jobs() -> tuple[BatchJob, ...]:
    """Exactly five requirements, irrespective of whether their files exist."""
    jobs = tuple(j for j in W.experiment_2a_jobs() if j.job_id in REUSED_FIT_IDS)
    if tuple(j.job_id for j in jobs) != REUSED_FIT_IDS or any(
        j.config.unit_id != "d5baeb907ac3"
        or j.stage != "exp2a"
        or j.roles != ("exp2a", "repair_validation")
        for j in jobs
    ):
        raise ValueError("Week-7 historical smoke overlap is not exactly five fits")
    return jobs


def new_experiment_2a_jobs() -> tuple[BatchJob, ...]:
    """95 new jobs; unavailable historical evidence cannot expand this set."""
    reused_experiment_2a_jobs()
    jobs = tuple(j for j in W.experiment_2a_jobs() if j.job_id not in REUSED_FIT_IDS)
    if len(jobs) != 95:
        raise ValueError("Week-7 must schedule exactly 95 new Experiment-2A fits")
    return jobs


def sweep_baseline_batches() -> tuple[tuple[BatchJob, ...], ...]:
    """All 225 complete comparison groups, each with its three registered seeds."""
    groups: dict[str, list[BatchJob]] = defaultdict(list)
    for job in W.configuration_sweep_baseline_jobs():
        groups[group_of(job.unit, stage_of(job.unit))].append(job)
    batches = tuple(
        tuple(sorted(groups[key], key=lambda j: (j.config.unit_id, j.seed)))
        for key in sorted(groups)
    )
    if len(batches) != 225 or any(
        len(batch) != 3
        or len({j.config.unit_id for j in batch}) != 1
        or tuple(j.seed for j in batch) != (1000, 1001, 1002)
        or any(j.stage != "config_sweep" or j.roles != ("config_sweep",) for j in batch)
        for batch in batches
    ):
        raise ValueError("Week-7 sweep must partition all 675 fits into 225 whole groups")
    if tuple(j.job_id for j in batches[0]) != tuple(
        f"cc428cf4ab47-s{seed}" for seed in range(1000, 1003)
    ) or batches[0][0].config.unit_id != "0184fbfcd8b9":
        raise ValueError("Week-7 outcome-independent first sweep group drifted")
    return batches


def _preparation_digest() -> str:
    # Reproduce durable.atomic_write_json's exact frozen preparation bytes.
    raw = (json.dumps(
        W.build_week7_plan(), sort_keys=True, indent=2, allow_nan=False,
        ensure_ascii=False,
    ) + "\n").encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != PREPARATION_SHA256:
        raise ValueError("Registered Week-7 preparation differs from frozen SHA-256")
    return W.build_week7_plan()["plan_digest"]


def build_week7_launch_plan() -> dict[str, Any]:
    """Pure configuration derivation; neither read outcomes nor launch work."""
    preparation_digest = _preparation_digest()
    reused = reused_experiment_2a_jobs()
    new = new_experiment_2a_jobs()
    sweep = sweep_baseline_batches()
    batches: dict[str, Any] = {
        "exp2a": {
            "comparison_group_id": None,
            "in_current_scope": True,
            "contemporaneous_anchors_required": False,
            "fit_count": len(new),
            "jobs": [j.as_record() for j in new],
        }
    }
    for number, jobs in enumerate(sweep, 1):
        key = f"sweep-{number:03d}"
        batches[key] = {
            "comparison_group_id": group_of(jobs[0].unit, stage_of(jobs[0].unit)),
            "in_current_scope": key in AUTHORIZED_BATCH_KEYS,
            "contemporaneous_anchors_required": True,
            "fit_count": len(jobs),
            "jobs": [j.as_record() for j in jobs],
        }
    payload = {
        "week7_launch_plan_schema_version": WEEK7_LAUNCH_PLAN_SCHEMA_VERSION,
        "purpose": "exact_week7_baseline_launch_inventory",
        "preparation": {
            "file_sha256": PREPARATION_SHA256, "plan_digest": preparation_digest,
        },
        "source_reconciliation_required": True,
        "replacement_training_allowed": False,
        "reused_fits_belong_in_new_batch_directories": False,
        "exp2a_required_fit_ids": [j.job_id for j in W.experiment_2a_jobs()],
        "reused_exp2a_jobs": [j.as_record() for j in reused],
        "sweep_partition_order": "comparison_group_id_then_unit_id_then_seed",
        "sweep_group_count": 225,
        "sweep_required_fit_count": 675,
        "initial_new_fit_count": 98,
        "remaining_sweep_fit_count_after_initial_batch": 672,
        "authorized_batch_keys": list(AUTHORIZED_BATCH_KEYS),
        "batches": batches,
    }
    return {**payload, "plan_digest": hashlib.sha256(_canonical(payload)).hexdigest()}


def validate_week7_launch_plan(document: object) -> None:
    """Full semantic rederivation, not just a digest or identity comparison."""
    if type(document) is not dict or _canonical(document) != _canonical(build_week7_launch_plan()):
        raise ValueError("Week-7 launch plan differs from the exact registered inventory")


def _verify_preparation(path: str | Path | None) -> None:
    target = PREPARATION_PATH if path is None else Path(path)
    W.load_week7_plan(target)
    if sha256_file(target) != PREPARATION_SHA256:
        raise ValueError("Week-7 preparation bytes differ from the frozen SHA-256")


def load_week7_launch_plan(
    path: str | Path, *, preparation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Reopen the frozen preparation and rederive every launch-plan field."""
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("Week-7 launch plan must be a regular non-symlink file")
    _verify_preparation(preparation_path)
    document = read_json(target)
    validate_week7_launch_plan(document)
    return document


def write_week7_launch_plan(
    directory: str | Path, *, preparation_path: str | Path | None = None,
) -> Path:
    """Exclusively publish a complete plan; refuse missing/changed preparation."""
    _verify_preparation(preparation_path)
    document = build_week7_launch_plan()
    path = atomic_write_json(Path(directory) / WEEK7_LAUNCH_PLAN_FILE, document)
    load_week7_launch_plan(path, preparation_path=preparation_path)
    return path


def jobs_for_batch(plan: object, batch_key: str) -> tuple[BatchJob, ...]:
    """Only current-scope jobs; later sweep groups need a separately reviewed gate.

    No source reconciliation result can add the five reused jobs to this set.
    The preflight/launcher must separately reverify all five source references
    before BOTH batches, and must never move them into a new batch directory.
    """
    if type(batch_key) is not str or batch_key not in AUTHORIZED_BATCH_KEYS:
        raise ValueError("Week-7 current scope authorizes only exp2a and sweep-001")
    validate_week7_launch_plan(plan)
    return new_experiment_2a_jobs() if batch_key == "exp2a" else sweep_baseline_batches()[0]
