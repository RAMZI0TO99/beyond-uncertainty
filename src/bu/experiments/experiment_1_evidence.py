"""Read-only, source-bound inputs for Experiment 1 (Week 7).

This boundary reopens exactly the 150 physical fits in ``experiment_1_jobs``.
The existing fit reader verifies the bytes and registered execution procedure;
this consumer additionally checks the exact Experiment-1 inventory and paired
evaluation pools across the six sizes within each configuration and seed.
The 30 multi-role fits remain one row each (D-033). Configuration identity is
``comparison_group_id(unit, "exp1")`` (D-039), NOT a pooled configuration.

Rows contain float64 means of the verified, already-normalised, whole-movement
error/disagreement arrays. No mask, new normalisation, across-configuration
aggregation, trend, verdict, repair label, or scientific execution is performed.
Returned tuples/scalars are immutable snapshots, not reusable evidence tokens:
the public loader accepts only explicit source paths and always reopens them.
There is no directory discovery, implicit commit, CLI, or write operation.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .. import constants as K
from ..config import UnitSpec
from ..models.uncertainty import NormalisationScale
from ..streams import comparison_group_id, confirmatory_seeds
from .batch import BatchJob, experiment_1_jobs
from .fit_evidence import VerifiedFitEvidence, load_fit_evidence


@dataclass(frozen=True)
class Experiment1Scale:
    """Immutable copy of a verified full-movement-pool normalisation identity."""

    vector: tuple[float, ...]
    n_reference: int
    domain: str
    source: str


@dataclass(frozen=True)
class Experiment1Row:
    """One configuration/seed/size cell; means weight movement rows equally."""

    causal_attribute: str
    layout: str
    comparison_group_id: str
    seed: int
    n_transitions: int
    unit: UnitSpec
    unit_id: str
    config_id: str
    fit_id: str
    arm: str
    roles: tuple[str, ...]
    execution_stage: str
    execution_run_id: str
    source_path: Path
    execution_digest: str
    evaluation_pool_digest: str
    scale: Experiment1Scale
    episode: tuple[int, ...]
    step: tuple[int, ...]
    evaluation_action: tuple[int, ...]
    n_movement: int
    mean_error: float
    mean_disagreement: float


@dataclass(frozen=True)
class Experiment1Evidence:
    """Complete grid ordered by (comparison_group_id, seed, n_transitions).

    No curve is pooled across configurations, and matching seed numbers in
    different configurations do not assert paired pools. ``expected_git_commit``
    binds every source to the caller's one explicit, validated execution commit.
    """

    expected_git_commit: str
    comparison_group_ids: tuple[str, ...]
    seeds: tuple[int, ...]
    data_sizes: tuple[int, ...]
    rows: tuple[Experiment1Row, ...]


def _registered_grid() -> tuple[dict[str, BatchJob], tuple[str, ...], tuple[int, ...]]:
    jobs = experiment_1_jobs()
    by_fit = {job.job_id: job for job in jobs}
    seeds = tuple(confirmatory_seeds(K.SEEDS_HYPOTHESIS))
    groups = tuple(sorted({comparison_group_id(job.unit, "exp1") for job in jobs}))
    cells = {
        (comparison_group_id(job.unit, "exp1"), job.seed, job.unit.n_transitions)
        for job in jobs
    }
    expected_cells = {
        (group, seed, size) for group in groups for seed in seeds for size in K.DATA_SIZES
    }
    if (
        len(jobs) != 150
        or len(by_fit) != 150
        or len(groups) != 5
        or len(seeds) != 5
        or len(K.DATA_SIZES) != 6
        or cells != expected_cells
        or any(job.arm != "baseline" or job.stage != "exp1" for job in jobs)
    ):
        raise ValueError("Experiment-1 registry is not the exact 5 x 5 x 6 baseline grid")
    return by_fit, groups, seeds


def _digest(value: object, *, field: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{field} must be an exact lowercase 64-hex digest")
    return value


def _integer_vector(value: object, *, field: str) -> tuple[int, ...]:
    if (
        type(value) is not np.ndarray
        or value.ndim != 1
        or value.size == 0
        or value.dtype.kind not in "iu"
    ):
        raise ValueError(f"{field} must be a nonempty one-dimensional integer array")
    return tuple(int(item) for item in value)


def _mean(value: object, *, field: str, n_movement: int) -> float:
    if (
        type(value) is not np.ndarray
        or value.shape != (n_movement,)
        or value.dtype.kind not in "fiu"
        or not np.all(np.isfinite(value))
        or np.any(value < 0)
    ):
        raise ValueError(f"{field} must have one finite nonnegative value per movement row")
    mean = float(np.mean(value, dtype=np.float64))
    if not np.isfinite(mean):
        raise ValueError(f"{field} mean is not finite")
    return mean


def _row(verified: VerifiedFitEvidence, job: BatchJob, path: Path) -> Experiment1Row:
    cfg = job.config
    expected = {
        "unit": job.unit,
        "unit_id": cfg.unit_id,
        "config_id": cfg.config_id,
        "fit_id": job.job_id,
        "arm": job.arm,
        "seed": job.seed,
        "roles": job.roles,
        "execution_stage": job.stage,
        "execution_run_id": cfg.run_id,
        "n_train": job.unit.n_transitions,
        "ensemble_size": cfg.train.ensemble_size,
    }
    for field, value in expected.items():
        actual = getattr(verified, field)
        if type(actual) is not type(value) or actual != value:
            raise ValueError(
                f"fit {job.job_id} {field} does not equal the exact registered "
                f"Experiment-1 value {value!r}"
            )
    if not isinstance(verified.fit_dir, Path) or verified.fit_dir.resolve() != path:
        raise ValueError(f"fit reader returned a different source path for {job.job_id}")

    episode = _integer_vector(verified.episode, field="episode")
    step = _integer_vector(verified.step, field="step")
    action = _integer_vector(
        verified.diagnostics.get("evaluation_action"), field="evaluation_action"
    )
    if len(episode) != len(step):
        raise ValueError("episode and step inventories must be one-to-one")
    if len(action) != K.EVALUATION_EPISODES * K.EPISODE_LENGTH:
        raise ValueError("evaluation_action must contain the complete registered pool")

    if type(verified.scale) is not NormalisationScale:
        raise ValueError("fit lacks an exact verified NormalisationScale")
    # The persisted scale diagnostic is float64. The existing reader's torch
    # convenience object is float32; comparing only that object could hide a
    # source-scale difference below float32 resolution across paired sizes.
    scale_vector = verified.diagnostics.get("scale")
    if (
        type(scale_vector) is not np.ndarray
        or scale_vector.shape != (2,)
        or scale_vector.dtype.kind != "f"
    ):
        raise ValueError("fit lacks the exact two-dimensional persisted scale vector")
    scale = Experiment1Scale(
        vector=tuple(float(v) for v in scale_vector),
        n_reference=verified.scale.n_reference,
        domain=verified.scale.domain,
        source=verified.scale.source,
    )
    if (
        len(scale.vector) != 2
        or not all(np.isfinite(v) and v > 0 for v in scale.vector)
        or type(scale.n_reference) is not int
        or scale.n_reference != len(episode)
        or scale.domain != K.NORMALISATION_SCALE_DOMAIN
        or scale.source != K.NORMALISATION_SCALE_SOURCE
    ):
        raise ValueError("normalisation must identify the full registered movement pool")

    return Experiment1Row(
        causal_attribute=job.unit.causal_attribute,
        layout=job.unit.layout,
        comparison_group_id=comparison_group_id(job.unit, "exp1"),
        seed=job.seed,
        n_transitions=job.unit.n_transitions,
        unit=job.unit,
        unit_id=cfg.unit_id,
        config_id=cfg.config_id,
        fit_id=job.job_id,
        arm=job.arm,
        roles=job.roles,
        execution_stage=job.stage,
        execution_run_id=cfg.run_id,
        source_path=path,
        execution_digest=_digest(verified.execution_digest, field="execution_digest"),
        evaluation_pool_digest=_digest(
            verified.evaluation_pool_digest, field="evaluation_pool_digest"
        ),
        scale=scale,
        episode=episode,
        step=step,
        evaluation_action=action,
        n_movement=len(episode),
        mean_error=_mean(verified.error, field="error", n_movement=len(episode)),
        mean_disagreement=_mean(
            verified.diagnostics.get("disagreement"),
            field="disagreement",
            n_movement=len(episode),
        ),
    )


def load_experiment_1_evidence(
    fit_directories: Sequence[Path], *, expected_git_commit: str
) -> Experiment1Evidence:
    """Reopen all 150 registered fits and return an immutable, unpooled grid.

    Each arbitrary-named directory is identified by verified source bytes, not
    its basename. The underlying reader accepts a commit constraint, not unit /
    arm / seed / role constraints; those are checked here against the exact
    jobs after reopening. A same-length substitution cannot complete the grid.
    Invalid or missing commits fail at THIS boundary even if the inner reader
    is replaced in a synthetic test. No handcrafted ``VerifiedFitEvidence`` or
    previously returned grid can substitute for reopening the source paths.
    """
    if (
        type(expected_git_commit) is not str
        or re.fullmatch(r"[0-9a-f]{40}", expected_git_commit) is None
    ):
        raise ValueError("expected_git_commit must be an exact lowercase 40-hex commit")
    if not isinstance(fit_directories, Sequence) or isinstance(
        fit_directories, (str, bytes)
    ):
        raise ValueError("fit_directories must be an explicit sequence of Path objects")
    sources = tuple(fit_directories)
    if any(not isinstance(source, Path) for source in sources):
        raise ValueError("fit_directories accepts Path objects only, never evidence objects")
    by_fit, groups, seeds = _registered_grid()
    if len(sources) != len(by_fit):
        raise ValueError(f"expected exactly 150 fit directories, got {len(sources)}")
    paths = tuple(source.resolve() for source in sources)
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate fit directory (including resolved path aliases)")

    rows: dict[str, Experiment1Row] = {}
    references: dict[tuple[str, int], Experiment1Row] = {}
    for path in paths:
        try:
            verified = load_fit_evidence(path, expected_git_commit=expected_git_commit)
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot verify Experiment-1 source {path}: {exc}") from exc
        if type(verified) is not VerifiedFitEvidence:
            raise ValueError("fit reader must return an exact VerifiedFitEvidence")
        if type(verified.fit_id) is not str or verified.fit_id not in by_fit:
            raise ValueError(f"unregistered Experiment-1 fit {verified.fit_id!r} at {path}")
        if verified.fit_id in rows:
            raise ValueError(f"duplicate Experiment-1 physical fit {verified.fit_id}")
        row = _row(verified, by_fit[verified.fit_id], path)
        key = (row.comparison_group_id, row.seed)
        reference = references.setdefault(key, row)
        for field in (
            "evaluation_pool_digest", "scale", "episode", "step", "evaluation_action"
        ):
            if getattr(row, field) != getattr(reference, field):
                raise ValueError(
                    f"paired Experiment-1 {field} differs across sizes within "
                    f"configuration {key[0]}, seed {key[1]}"
                )
        rows[verified.fit_id] = row
    if set(rows) != set(by_fit):
        raise ValueError("missing registered Experiment-1 fits after source verification")

    ordered = tuple(sorted(
        rows.values(), key=lambda r: (r.comparison_group_id, r.seed, r.n_transitions)
    ))
    return Experiment1Evidence(
        expected_git_commit=expected_git_commit,
        comparison_group_ids=groups,
        seeds=seeds,
        data_sizes=tuple(K.DATA_SIZES),
        rows=ordered,
    )
