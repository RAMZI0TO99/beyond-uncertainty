"""Exact additive Week-8 baseline inventory; never an execution permission.

This boundary opens only the 125 registered Experiment-2B baselines and the
second already ordered whole configuration-sweep group.  It rederives both
sets from the certified registries and binds the frozen Week-7 preparation and
launch-plan bytes.  It never edits or broadens the Week-7 plan.
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
from ..durable import atomic_write_json, read_json, sha256_file
from ..streams import group_of
from . import week7_launch_plan as W7L
from . import week7_plan as W7P
from .batch import BatchJob
from .enumerate_units import design_units, execution_plan, experiment_2b_units, stage_of


WEEK8_PLAN_SCHEMA_VERSION = 1
WEEK8_PLAN_FILE = "week8_baseline_launch_plan.json"
WEEK7_PREPARATION_PATH = W7L.PREPARATION_PATH
WEEK7_PREPARATION_SHA256 = W7L.PREPARATION_SHA256
WEEK7_LAUNCH_PLAN_PATH = Path(
    "D:/Aenv/pro2/week7-execution-preparation-2026-08-31-attempt-001/"
    "week7_baseline_launch_plan.json"
)
WEEK7_LAUNCH_PLAN_SHA256 = (
    "a6d229a7119a5c892df0c5e74785d8ea92bbe5dbc0d4e40c0d270851811d3d86"
)
AUTHORIZED_BATCH_KEYS = ("exp2b", "sweep-002")
EXP2B_ALLOWED_ROLE_TUPLES = (
    ("exp2b",),
    ("exp2b", "repair_validation"),
)
SWEEP_002_GROUP_ID = "029dd4484382"
SWEEP_002_UNIT_ID = "029dd4484382"
SWEEP_002_CONFIG_ID = "eab7f1b3a520"


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
        raise ValueError("Week-8 plan must be strict JSON") from exc


def _pretty(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            allow_nan=False,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _assert_frozen_upstream_registries() -> tuple[str, str]:
    """Prove current code still serializes to both frozen Week-7 byte pins."""
    preparation = W7P.build_week7_plan()
    if hashlib.sha256(_pretty(preparation)).hexdigest() != WEEK7_PREPARATION_SHA256:
        raise ValueError("registered Week-7 preparation differs from its frozen SHA-256")
    launch = W7L.build_week7_launch_plan()
    if hashlib.sha256(_pretty(launch)).hexdigest() != WEEK7_LAUNCH_PLAN_SHA256:
        raise ValueError("registered Week-7 launch plan differs from its frozen SHA-256")
    return preparation["plan_digest"], launch["plan_digest"]


def _verify_upstream_files(
    preparation_path: str | Path | None,
    week7_launch_plan_path: str | Path | None,
) -> tuple[Path, Path]:
    preparation = (
        WEEK7_PREPARATION_PATH if preparation_path is None else Path(preparation_path)
    )
    launch = (
        WEEK7_LAUNCH_PLAN_PATH
        if week7_launch_plan_path is None
        else Path(week7_launch_plan_path)
    )
    W7P.load_week7_plan(preparation)
    if sha256_file(preparation) != WEEK7_PREPARATION_SHA256:
        raise ValueError("Week-7 preparation bytes differ from the frozen SHA-256")
    W7L.load_week7_launch_plan(launch, preparation_path=preparation)
    if sha256_file(launch) != WEEK7_LAUNCH_PLAN_SHA256:
        raise ValueError("Week-7 launch-plan bytes differ from the frozen SHA-256")
    return preparation.resolve(strict=True), launch.resolve(strict=True)


def experiment_2b_baseline_jobs() -> tuple[BatchJob, ...]:
    """The exact 25-condition x five-seed Experiment-2B baseline grid."""
    jobs = tuple(
        sorted(
            (
                BatchJob(
                    unit=fit.unit,
                    arm="baseline",
                    stage="exp2b",
                    seed=K.CONFIRMATORY_SEED_BASE + fit.seed,
                    roles=fit.roles,
                )
                for fit in execution_plan(design_units())
                if fit.arm == "baseline" and "exp2b" in fit.roles
            ),
            key=lambda job: job.job_id,
        )
    )
    expected_units = {Config(unit=unit).unit_id for unit in experiment_2b_units()}
    observed = Counter((job.config.unit_id, job.seed) for job in jobs)
    expected = Counter(
        (unit_id, seed)
        for unit_id in expected_units
        for seed in range(K.CONFIRMATORY_SEED_BASE, K.CONFIRMATORY_SEED_BASE + 5)
    )
    reference_jobs = tuple(
        job for job in jobs if job.roles == ("exp2b", "repair_validation")
    )
    if (
        K.CONFIRMATORY_SEED_BASE != 1000
        or K.DEFAULT_ENSEMBLE_SIZE != 5
        or len(expected_units) != 25
        or len(jobs) != 125
        or len({job.job_id for job in jobs}) != 125
        or observed != expected
        or sum(job.config.train.ensemble_size for job in jobs) != 625
        or len(reference_jobs) != 25
        or any(
            job.roles != ("exp2b", "repair_validation")
            or job.unit.causal_attribute != "shape"
            or job.unit.layout != "uniform"
            for job in reference_jobs
        )
        or any(
            job.roles not in EXP2B_ALLOWED_ROLE_TUPLES
            for job in jobs
        )
        or any(
            job.stage != "exp2b"
            or job.arm != "baseline"
            or job.config.train.batch_size != 128
            or job.config.train.ensemble_size != K.DEFAULT_ENSEMBLE_SIZE
            for job in jobs
        )
    ):
        raise ValueError("Week-8 Experiment-2B inventory drifted from 25 x five seeds")
    return jobs


def sweep_002_baseline_jobs() -> tuple[BatchJob, ...]:
    """Rederive only Week-7's already ordered second whole sweep group."""
    jobs = W7L.sweep_baseline_batches()[1]
    group_id = group_of(jobs[0].unit, stage_of(jobs[0].unit))
    if (
        group_id != SWEEP_002_GROUP_ID
        or len(jobs) != 3
        or tuple(job.config.unit_id for job in jobs) != (SWEEP_002_UNIT_ID,) * 3
        or tuple(job.config.config_id for job in jobs) != (SWEEP_002_CONFIG_ID,) * 3
        or tuple(job.job_id for job in jobs)
        != tuple(f"{SWEEP_002_CONFIG_ID}-s{seed}" for seed in range(1000, 1003))
        or any(
            job.stage != "config_sweep"
            or job.arm != "baseline"
            or job.roles != ("config_sweep",)
            or job.config.train.batch_size != 128
            for job in jobs
        )
        or sum(job.config.train.ensemble_size for job in jobs) != 15
    ):
        raise ValueError("Week-8 sweep-002 anchor or whole-group inventory drifted")
    return jobs


def build_week8_launch_plan() -> dict[str, Any]:
    """Rederive the complete bounded plan without reading outcomes or launching."""
    preparation_digest, week7_launch_digest = _assert_frozen_upstream_registries()
    exp2b = experiment_2b_baseline_jobs()
    sweep = sweep_002_baseline_jobs()
    all_jobs = exp2b + sweep
    if len({job.job_id for job in all_jobs}) != 128:
        raise ValueError("Week-8 batches overlap or do not contain exactly 128 fits")
    payload: dict[str, Any] = {
        "week8_plan_schema_version": WEEK8_PLAN_SCHEMA_VERSION,
        "purpose": "exact_additive_week8_exp2b_and_sweep_002_baselines",
        "upstream": {
            "week7_preparation": {
                "file_sha256": WEEK7_PREPARATION_SHA256,
                "plan_digest": preparation_digest,
            },
            "week7_launch_plan": {
                "file_sha256": WEEK7_LAUNCH_PLAN_SHA256,
                "plan_digest": week7_launch_digest,
            },
        },
        "week7_plan_modified": False,
        "authorized_batch_keys": list(AUTHORIZED_BATCH_KEYS),
        "fit_count": 128,
        "member_model_count": 640,
        "confirmatory_train_batch_size": 128,
        "batches": {
            "exp2b": {
                "comparison_group_id": None,
                "fit_count": 125,
                "member_model_count": 625,
                "sweep_anchors_required": False,
                "jobs": [job.as_record() for job in exp2b],
            },
            "sweep-002": {
                "comparison_group_id": SWEEP_002_GROUP_ID,
                "fit_count": 3,
                "member_model_count": 15,
                "sweep_anchors_required": True,
                "jobs": [job.as_record() for job in sweep],
            },
        },
        "scientific_analysis_performed": False,
    }
    return {**payload, "plan_digest": hashlib.sha256(_canonical(payload)).hexdigest()}


def validate_week8_launch_plan(document: object) -> None:
    if type(document) is not dict or _canonical(document) != _canonical(
        build_week8_launch_plan()
    ):
        raise ValueError("Week-8 plan differs from the exact registered inventory")


def load_week8_launch_plan(
    path: str | Path,
    *,
    preparation_path: str | Path | None = None,
    week7_launch_plan_path: str | Path | None = None,
) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("Week-8 plan must be a regular non-symlink file")
    _verify_upstream_files(preparation_path, week7_launch_plan_path)
    document = read_json(target)
    validate_week8_launch_plan(document)
    return document


def write_week8_launch_plan(
    directory: str | Path,
    *,
    preparation_path: str | Path | None = None,
    week7_launch_plan_path: str | Path | None = None,
) -> Path:
    _verify_upstream_files(preparation_path, week7_launch_plan_path)
    path = atomic_write_json(Path(directory) / WEEK8_PLAN_FILE, build_week8_launch_plan())
    load_week8_launch_plan(
        path,
        preparation_path=preparation_path,
        week7_launch_plan_path=week7_launch_plan_path,
    )
    return path


def jobs_for_batch(plan: object, batch_key: str) -> tuple[BatchJob, ...]:
    if type(batch_key) is not str or batch_key not in AUTHORIZED_BATCH_KEYS:
        raise ValueError("Week-8 authorizes only exp2b and sweep-002")
    validate_week8_launch_plan(plan)
    return (
        experiment_2b_baseline_jobs()
        if batch_key == "exp2b"
        else sweep_002_baseline_jobs()
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Publish the exact plan through a fixed no-compute command-line boundary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--preparation-path", type=Path)
    parser.add_argument("--week7-launch-plan-path", type=Path)
    arguments = parser.parse_args(argv)
    path = write_week8_launch_plan(
        arguments.directory,
        preparation_path=arguments.preparation_path,
        week7_launch_plan_path=arguments.week7_launch_plan_path,
    )
    print(f"Exact Week-8 baseline plan published: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
