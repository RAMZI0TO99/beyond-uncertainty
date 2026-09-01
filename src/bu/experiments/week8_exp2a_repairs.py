"""Exact additive Experiment-2A repair inventory for Week 8.

The full registered design contains 416 physical fits and 1,056 member-model
trainings.  Week 6 already completed all sixty baseline/data/feature fits for
one twenty-seed validation unit, and Week 7 completed the other ninety-five
five-seed baselines.  Those 155 fits and 615 member-model trainings are
immutable sources: their absence is an integrity failure, never permission to
train replacements.  Only the remaining 261 fits / 441 member-model trainings
are executable.

This module is deliberately configuration-only.  Source reconciliation lives
in :mod:`week8_exp2a_sources`; preflight, the fixed fresh-process worker and
recovery live in :mod:`week8_exp2a_repair_launch`; label construction lives in
:mod:`week8_exp2a_label_finalization`.  No function here reads outcomes or
executes a model.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import constants as K
from ..config import Arm, Config, UnitSpec, seeds_for
from ..durable import atomic_write_json, read_json
from ..runrecord import PROJECT_ROOT
from ..streams import confirmatory_seeds, group_of
from . import confirmatory as C
from . import repair_label_preflight as RF
from .enumerate_units import (
    arms_for,
    execution_plan,
    experiment_2a_units,
    repair_stage_of,
    repair_validation_units,
)


EXP2A_REPAIRS_SCHEMA_VERSION = 2
PLAN_FILE = "week8_exp2a_repair_plan.json"
START_DIRECTORY = "week8_exp2a_repair_starts"
CONTEXT_FILE = "week8_exp2a_execution_context.json"
WORKSPACE_ROOT = PROJECT_ROOT.parent
# D-160: Week 7, Week 8 baseline work and Experiment 2A repairs share this
# single namespace.  It must never be replaced by a Week-8-specific lease.
COMMON_LEASE_ROOT = WORKSPACE_ROOT / "week7-production-control"
COMMON_LEASE_NAME = "week7-production"

SMOKE_UNIT_ID = "d5baeb907ac3"
SMOKE_EXECUTION_COMMIT = "750266c7b8c4eb955b03f6081a861aed1051907b"
WEEK7_EXECUTION_COMMIT = "4782c90ce0e66fb46768f08d5080a27590a51a48"


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Experiment-2A repair evidence must be strict JSON") from exc


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    return {**payload, field: hashlib.sha256(_canonical(payload)).hexdigest()}


def _equal(observed: object, expected: object, *, what: str) -> None:
    if _canonical(observed) != _canonical(expected):
        raise ValueError(f"{what} differs from the exact registered evidence")


@dataclass(frozen=True)
class Exp2ARepairJob:
    """One physical fit with its actual arm-specific training configuration."""

    unit: UnitSpec
    arm: str
    seed: int
    roles: tuple[str, ...]

    @property
    def stage(self) -> str:
        if not self.roles:
            raise ValueError("an Experiment-2A job must carry at least one role")
        return self.roles[0]

    @property
    def config(self) -> Config:
        train = C.CONFIRMATORY_TRAIN if self.arm == "baseline" else C.REPAIRED_TRAIN
        return Config(
            unit=self.unit,
            arm=Arm(self.arm),
            seed=self.seed,
            stage=self.stage,
            train=train,
        )

    @property
    def job_id(self) -> str:
        return self.config.fit_id

    def as_record(self) -> dict[str, Any]:
        config = self.config
        return {
            "job_id": self.job_id,
            "fit_id": config.fit_id,
            "run_id": config.run_id,
            "config_id": config.config_id,
            "unit_id": config.unit_id,
            "stage": self.stage,
            "seed": self.seed,
            "arm": self.arm,
            "roles": list(self.roles),
            "config": config.to_dict(),
        }


def _validation_ids() -> frozenset[str]:
    e2a = {Config(unit=unit).unit_id for unit in experiment_2a_units()}
    result = frozenset(
        Config(unit=unit).unit_id
        for unit in repair_validation_units()
        if Config(unit=unit).unit_id in e2a
    )
    if result != frozenset(
        {SMOKE_UNIT_ID, "399e994df8b7", "8640549e3e88", "620b0668b967"}
    ):
        raise ValueError("Experiment-2A twenty-seed validation units drifted")
    return result


def registered_exp2a_jobs() -> tuple[Exp2ARepairJob, ...]:
    """Rederive all 416 registered physical obligations."""

    if (
        seeds_for("repair_validation"),
        seeds_for("exp3_repairs"),
        K.SEEDS_HYPOTHESIS,
        K.CONFIRMATORY_SEED_BASE,
    ) != (20, 3, 5, 1000):
        raise ValueError("Experiment-2A must retain the exact 20/3/5 seed policy")
    units = experiment_2a_units()
    if len(units) != 20 or len({Config(unit=unit).unit_id for unit in units}) != 20:
        raise ValueError("Experiment-2A must contain exactly twenty unique units")
    validation_ids = _validation_ids()
    jobs = tuple(
        Exp2ARepairJob(
            fit.unit,
            fit.arm,
            K.CONFIRMATORY_SEED_BASE + fit.seed,
            fit.roles,
        )
        for fit in execution_plan(units)
    )

    actual: dict[tuple[str, str, int], Exp2ARepairJob] = {}
    for job in jobs:
        key = (job.config.unit_id, job.arm, job.seed)
        if key in actual:
            raise ValueError("Experiment-2A physical obligations are duplicated")
        actual[key] = job

    expected: dict[tuple[str, str, int], Exp2ARepairJob] = {}
    for unit in units:
        unit_id = Config(unit=unit).unit_id
        stage = repair_stage_of(unit)
        expected_stage = "repair_validation" if unit_id in validation_ids else "exp3_repairs"
        if stage != expected_stage:
            raise ValueError("Experiment-2A repair-label seed policy drifted")
        if arms_for(unit) != ("baseline", "data_repair", "feature_repair"):
            raise ValueError("Experiment-2A repair arms drifted")
        label_seeds = confirmatory_seeds(seeds_for(stage))
        baseline_seeds = sorted(
            set(label_seeds) | set(confirmatory_seeds(K.SEEDS_HYPOTHESIS))
        )
        for seed in baseline_seeds:
            roles = tuple(
                sorted(
                    (["exp2a"] if seed in confirmatory_seeds(K.SEEDS_HYPOTHESIS) else [])
                    + (["repair_validation"] if unit_id in validation_ids else [])
                )
            )
            expected[(unit_id, "baseline", seed)] = Exp2ARepairJob(
                unit, "baseline", seed, roles
            )
        for arm in ("data_repair", "feature_repair"):
            for seed in label_seeds:
                expected[(unit_id, arm, seed)] = Exp2ARepairJob(
                    unit, arm, seed, (stage,)
                )
    _equal(
        {str(key): value.as_record() for key, value in actual.items()},
        {str(key): value.as_record() for key, value in expected.items()},
        what="Experiment-2A full inventory",
    )
    order = {"baseline": 0, "data_repair": 1, "feature_repair": 2}
    ordered = tuple(
        sorted(jobs, key=lambda job: (job.config.unit_id, job.seed, order[job.arm]))
    )
    if (
        len(ordered) != 416
        or sum(job.arm == "baseline" for job in ordered) != 160
        or sum(job.arm != "baseline" for job in ordered) != 256
        or sum(job.config.train.ensemble_size for job in ordered) != 1056
    ):
        raise ValueError("Experiment-2A exact 416-fit/1056-model inventory drifted")
    return ordered


def source_kind(job: Exp2ARepairJob) -> str | None:
    """Return the immutable historical source family, or ``None`` if new."""

    if type(job) is not Exp2ARepairJob:
        raise ValueError("source classification requires an exact Exp2ARepairJob")
    if job.config.unit_id == SMOKE_UNIT_ID:
        return "week6_smoke"
    if job.arm == "baseline" and job.seed in confirmatory_seeds(K.SEEDS_HYPOTHESIS):
        return "week7_exp2a"
    return None


def existing_exp2a_jobs() -> tuple[Exp2ARepairJob, ...]:
    """The exact 155 immutable historical fits; missing history never enlarges work."""

    jobs = tuple(job for job in registered_exp2a_jobs() if source_kind(job) is not None)
    kinds = [source_kind(job) for job in jobs]
    if (
        len(jobs) != 155
        or kinds.count("week6_smoke") != 60
        or kinds.count("week7_exp2a") != 95
        or sum(job.config.train.ensemble_size for job in jobs) != 615
    ):
        raise ValueError("Experiment-2A historical 155-fit/615-model partition drifted")
    return jobs


def new_exp2a_jobs() -> tuple[Exp2ARepairJob, ...]:
    """The exact 261 executable fits; source absence cannot expand this set."""

    jobs = tuple(job for job in registered_exp2a_jobs() if source_kind(job) is None)
    if (
        len(jobs) != 261
        or sum(job.arm == "baseline" for job in jobs) != 45
        or sum(job.arm != "baseline" for job in jobs) != 216
        or sum(job.config.train.ensemble_size for job in jobs) != 441
    ):
        raise ValueError("Experiment-2A new 261-fit/441-model inventory drifted")
    return jobs


def label_required_exp2a_jobs() -> tuple[Exp2ARepairJob, ...]:
    """The exact 384 source fits consumed by the twenty label procedures."""

    required: list[Exp2ARepairJob] = []
    for job in registered_exp2a_jobs():
        seeds = confirmatory_seeds(seeds_for(repair_stage_of(job.unit)))
        if job.seed in seeds:
            required.append(job)
    result = tuple(required)
    if len(result) != 384 or len({job.job_id for job in result}) != 384:
        raise ValueError("Experiment-2A label source inventory must contain 384 fits")
    return result


def build_exp2a_repair_plan() -> dict[str, Any]:
    """Build a pure, outcome-free plan; this document cannot launch work."""

    jobs = registered_exp2a_jobs()
    existing = existing_exp2a_jobs()
    new = new_exp2a_jobs()
    total_model_trainings = sum(
        job.config.train.ensemble_size for job in jobs
    )
    historical_model_trainings = sum(
        job.config.train.ensemble_size for job in existing
    )
    new_model_trainings = sum(
        job.config.train.ensemble_size for job in new
    )
    if (
        (total_model_trainings, historical_model_trainings, new_model_trainings)
        != (1056, 615, 441)
        or historical_model_trainings + new_model_trainings
        != total_model_trainings
    ):
        raise ValueError(
            "Experiment-2A model-training accounting must be exact 1056/615/441"
        )
    required = {job.job_id for job in label_required_exp2a_jobs()}
    labels: list[dict[str, Any]] = []
    for unit in sorted(experiment_2a_units(), key=lambda value: Config(unit=value).unit_id):
        stage = repair_stage_of(unit)
        seeds = confirmatory_seeds(seeds_for(stage))
        relevant = tuple(job for job in jobs if job.unit == unit and job.seed in seeds)
        labels.append(
            {
                "unit_id": Config(unit=unit).unit_id,
                "comparison_group_id": group_of(unit, "exp2a"),
                "label_stage": stage,
                "seeds": list(seeds),
                "label_api": (
                    "bu.experiments.label_evidence.build_label_evidence"
                    if stage == "repair_validation"
                    else "bu.experiments.ordinary_label_evidence.build_ordinary_label_evidence"
                ),
                "required_fit_ids": [job.job_id for job in relevant],
                "observed_label": None,
            }
        )
    return _seal(
        {
            "exp2a_repairs_schema_version": EXP2A_REPAIRS_SCHEMA_VERSION,
            "purpose": "exact_week8_experiment2a_repair_inventory",
            "execution_authorized_by_this_file": False,
            "production_launch_adapter": (
                "bu.experiments.week8_exp2a_repair_launch.launch_exp2a_repairs"
            ),
            "replacement_training_allowed": False,
            "ordering": "unit_id_then_seed_then_baseline_data_feature",
            "labels": labels,
            "existing_jobs": [
                {
                    **job.as_record(),
                    "source_kind": source_kind(job),
                    "required_for_label": job.job_id in required,
                }
                for job in existing
            ],
            "new_jobs": [job.as_record() for job in new],
            "counts": {
                "units": 20,
                "twenty_seed_units": 4,
                "three_seed_units": 16,
                "registered_physical_fits": len(jobs),
                "total_model_trainings": total_model_trainings,
                "existing_fits_preserved": len(existing),
                "historical_model_trainings": historical_model_trainings,
                "week6_smoke_fits_preserved": 60,
                "week7_baseline_fits_preserved": 95,
                "existing_fits_required_by_labels": sum(
                    job.job_id in required for job in existing
                ),
                "label_required_fits": len(required),
                "new_baseline_fits": sum(job.arm == "baseline" for job in new),
                "new_repair_fits": sum(job.arm != "baseline" for job in new),
                "new_physical_fits": len(new),
                "new_member_model_trainings": new_model_trainings,
            },
        },
        "plan_digest",
    )


def validate_exp2a_repair_plan(document: object) -> None:
    _equal(document, build_exp2a_repair_plan(), what="Experiment-2A repair plan")


def _project_path(
    path: str | Path, *, directory: bool, existing: bool = True
) -> Path:
    """Reject links/junctions and keep all mutable evidence in the workspace."""

    candidate = Path(path).absolute()
    for part in reversed((candidate, *candidate.parents)):
        if not os.path.lexists(part):
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or RF._is_reparse(info):
            raise ValueError(f"project evidence path contains a link/reparse point: {part}")
        if part != candidate and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"project path component is not a directory: {part}")
    workspace = WORKSPACE_ROOT.resolve(strict=True)
    try:
        resolved = candidate.resolve(strict=existing)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"project evidence path is unavailable: {candidate}") from exc
    if resolved == workspace or not resolved.is_relative_to(workspace):
        raise ValueError("Week-8 evidence must stay in a project-local child directory")
    if existing:
        if directory and not resolved.is_dir():
            raise ValueError("expected an existing project evidence directory")
        if not directory:
            RF._regular_file(resolved, what="project evidence")
    return resolved


def write_exp2a_repair_plan(directory: str | Path) -> Path:
    root = _project_path(directory, directory=True)
    return atomic_write_json(root / PLAN_FILE, build_exp2a_repair_plan())


def load_exp2a_repair_plan(path: str | Path) -> dict[str, Any]:
    document = read_json(_project_path(path, directory=False))
    validate_exp2a_repair_plan(document)
    return document
