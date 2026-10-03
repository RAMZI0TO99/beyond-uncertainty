"""Week-7 baseline configuration preparation, never a launch (S W7 Wed).

The existing execution plan is authoritative. This file serializes its exact
Experiment-2A and sweep baseline requirements without selecting repairs,
reserves, a sweep batch size, or a new seed policy. A requirement is NOT an
outstanding job: the Week-6 smoke already produced five Experiment-2A baselines.
Any future launcher must reconcile existing source-verified fits before work.

This preparation manifest has a different schema/file from a batch manifest.
No launcher consumes it. It contains no result, label, completion attestation,
or authorization to execute. All configuration fields round-trip through
Config, and loading rederives the entire document from the registered design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .. import constants as K
from ..config import Config
from ..durable import atomic_write_json, read_json
from ..streams import confirmatory_seeds
from .batch import BatchJob
from .enumerate_units import (
    CANONICAL_PAIRS,
    canonical_units,
    design_units,
    execution_plan,
    experiment_2a_units,
)


WEEK7_PLAN_SCHEMA_VERSION = 1
WEEK7_PLAN_FILE = "week7_baseline_preparation.json"


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Week-7 preparation must be strict JSON") from exc


def _stage_jobs(stage: str) -> tuple[BatchJob, ...]:
    """Internal fixed selection; no caller-selected pool, count or role set."""
    jobs = tuple(sorted(
        (
            BatchJob(
                unit=fit.unit, arm=fit.arm, stage=stage,
                seed=K.CONFIRMATORY_SEED_BASE + fit.seed, roles=fit.roles,
            )
            for fit in execution_plan(design_units())
            if fit.arm == "baseline" and stage in fit.roles
        ),
        key=lambda job: job.job_id,
    ))
    canonical_ids = {Config(unit=u).unit_id for u in canonical_units()}
    if stage == "exp2a":
        units = experiment_2a_units()
        expected_count = 100
        seeds = confirmatory_seeds(K.SEEDS_HYPOTHESIS)
        if len(units) != 20 or len(CANONICAL_PAIRS) != 5:
            raise ValueError("Experiment-2A registered 4 x 5 design drifted")
        expected_cells = Counter(
            (causal, layout, confound, seed)
            for causal, layout in CANONICAL_PAIRS
            for confound in K.CONFOUND_LEVELS_2A
            for seed in seeds
        )
        observed_cells = Counter(
            (j.unit.causal_attribute, j.unit.layout, j.unit.confound_rate, j.seed)
            for j in jobs
        )
        if observed_cells != expected_cells or any(
            j.unit.withheld_features != (j.unit.causal_attribute,)
            or j.unit.n_transitions != max(K.DATA_SIZES)
            for j in jobs
        ):
            raise ValueError("Experiment-2A cells/withholding/data size drifted")
    else:
        units = tuple(
            u for u in design_units() if Config(unit=u).unit_id not in canonical_ids
        )
        expected_count = 675
        seeds = confirmatory_seeds(K.SEEDS_SWEEP)
        if len(units) != 225:
            raise ValueError("Registered sweep must contain 225 non-canonical units")
    expected = {
        (Config(unit=unit).unit_id, seed) for unit in units for seed in seeds
    }
    if (
        len(jobs) != expected_count
        or len({job.job_id for job in jobs}) != expected_count
        or {(job.config.unit_id, job.seed) for job in jobs} != expected
    ):
        raise ValueError(f"{stage} is not its exact registered baseline inventory")
    for job in jobs:
        if job.stage != job.roles[0]:
            raise ValueError("Preparation stage is not deterministic execution stage")
        # Pin canonical serialization as well as the identities. A train-field
        # drift can leave fit_id unchanged, so checking only ids is insufficient.
        record = job.config.to_dict()
        if _canonical(Config.from_dict(record).to_dict()) != _canonical(record):
            raise ValueError("Prepared Config does not round-trip exactly")
    return jobs


def experiment_2a_jobs() -> tuple[BatchJob, ...]:
    """All 100 required baselines, including already-computed smoke overlap."""
    return _stage_jobs("exp2a")


def configuration_sweep_baseline_jobs() -> tuple[BatchJob, ...]:
    """All 675 sweep baselines; no arbitrary first-batch selection or repairs."""
    return _stage_jobs("config_sweep")


def build_week7_plan() -> dict[str, Any]:
    """Return a fresh, deterministic preparation record with an exact digest."""
    groups = {
        "exp2a": experiment_2a_jobs(),
        "config_sweep": configuration_sweep_baseline_jobs(),
    }
    identifiers = [job.job_id for jobs in groups.values() for job in jobs]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Week-7 stages duplicate a physical fit")
    payload = {
        "week7_plan_schema_version": WEEK7_PLAN_SCHEMA_VERSION,
        "purpose": "registered_baseline_configuration_preparation_only",
        "execution_authorized": False,
        "prior_completion_checked": False,
        "sweep_batch_partition": None,
        "repair_assignments_added": False,
        "stages": {
            stage: {
                "required_fit_count": len(jobs),
                "unit_count": len({job.config.unit_id for job in jobs}),
                "multi_role_fit_count": sum(len(job.roles) > 1 for job in jobs),
                "seeds": sorted({job.seed for job in jobs}),
                "jobs": [job.as_record() for job in jobs],
            }
            for stage, jobs in groups.items()
        },
    }
    return {**payload, "plan_digest": hashlib.sha256(_canonical(payload)).hexdigest()}


def validate_week7_plan(document: object) -> None:
    """Refuse any drift, including self-consistently resigned forged plans.

    Strict JSON comparison distinguishes booleans, integers and floats. No
    caller count, seed subset, alternate constant or additional field is used
    to define the expected plan.
    """
    if type(document) is not dict:
        raise ValueError("Week-7 preparation must be an exact dict")
    if _canonical(document) != _canonical(build_week7_plan()):
        raise ValueError("Week-7 preparation differs from the exact registered plan")


def load_week7_plan(path: str | Path) -> dict[str, Any]:
    """Read and rederive a preparation file; never read experimental results."""
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("Week-7 preparation must be a regular, non-symlink file")
    document = read_json(target)
    validate_week7_plan(document)
    return document


def write_week7_plan(directory: str | Path) -> Path:
    """Publish one immutable file. Equal retries are safe; differences refuse."""
    document = build_week7_plan()
    path = atomic_write_json(Path(directory) / WEEK7_PLAN_FILE, document)
    load_week7_plan(path)
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    path = write_week7_plan(args.output_directory)
    print(f"Prepared 100 Experiment-2A and 675 sweep baseline configurations: {path}")
    print("No experiment launched; existing-fit reconciliation and sweep batching remain.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
