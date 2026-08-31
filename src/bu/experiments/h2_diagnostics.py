"""Source-bound Week-7 H2 metric preparation, never an H2 hypothesis decision.

See docs/week7_secondary_diagnostic_spec.md: Pearson correlation is secondary,
per seed and restricted to the strict baseline failure set. Existing normalized
arrays are consumed without renormalization. No new result is read on import.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .. import constants as K
from ..config import Config, UnitSpec
from ..models.uncertainty import RATIO_FLOOR
from ..streams import confirmatory_seeds, group_of
from . import fit_evidence as F
from . import launch as L
from .enumerate_units import stage_of


H2_DIAGNOSTIC_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BaselineDiagnosticSource:
    path: Path
    expected_git_commit: str
    expected_execution_digest: str


def _pearson(error: np.ndarray, disagreement: np.ndarray) -> tuple[float | None, str | None]:
    if len(error) < 2:
        return None, "fewer_than_two_failure_transitions"
    if np.all(error == error[0]) or np.all(disagreement == disagreement[0]):
        return None, "constant_error_or_disagreement"
    # Rescaling before centering/norms avoids overflow for finite large inputs;
    # Pearson is scale invariant. No near-constant cutoff is chosen or tuned.
    x = error / np.max(np.abs(error))
    y = disagreement / np.max(np.abs(disagreement))
    x, y = x - x.mean(), y - y.mean()
    nx, ny = np.linalg.norm(x), np.linalg.norm(y)
    if nx == 0 or ny == 0:
        return None, "numerically_degenerate_centered_vector"
    return float(np.clip(np.dot(x / nx, y / ny), -1, 1)), None


def _failure_metrics(error: np.ndarray, disagreement: np.ndarray) -> dict[str, Any]:
    for name, value in (("error", error), ("disagreement", disagreement)):
        if (type(value) is not np.ndarray or value.ndim != 1 or value.dtype.kind != "f"
                or not len(value) or not np.isfinite(value).all() or np.any(value < 0)):
            raise ValueError(f"{name} must be finite nonnegative floating point movement rows")
    if error.shape != disagreement.shape:
        raise ValueError("error and disagreement must refer to identical movement rows")
    mask = error > K.FAILURE_THRESHOLD
    if not np.any(mask):
        raise ValueError("H2 diagnostic blocked: empty strict baseline failure set")
    e = np.asarray(error[mask], dtype=np.float64)
    d = np.asarray(disagreement[mask], dtype=np.float64)
    # Means, not per-transition ratios. Scaling the summation prevents a finite
    # input mean from overflowing just because an unscaled sum would overflow.
    mean_error = float(e.max() * np.mean(e / e.max()))
    mean_disagreement = float(d.max() * np.mean(d / d.max())) if np.any(d) else 0.0
    ratio = mean_disagreement / max(mean_error, RATIO_FLOOR)
    if not np.isfinite(ratio):
        raise ValueError("H2 diagnostic ratio is not finite")
    correlation, reason = _pearson(e, d)
    return {
        "n_movement": len(error), "n_failure": int(mask.sum()),
        "failure_mask_sha256": hashlib.sha256(np.asarray(mask, dtype=np.uint8).tobytes()).hexdigest(),
        "mean_error": mean_error, "mean_disagreement": mean_disagreement,
        "ratio_of_means": ratio, "pearson_r": correlation,
        "correlation_undefined_reason": reason,
    }


def baseline_failure_diagnostic(
    source: BaselineDiagnosticSource, *, unit: UnitSpec, seed: int,
) -> dict[str, Any]:
    """Reopen one independently pinned baseline; never infer a failure class."""
    if type(source) is not BaselineDiagnosticSource or type(unit) is not UnitSpec:
        raise ValueError("diagnostics need an exact source and UnitSpec")
    stage = stage_of(unit)
    required = confirmatory_seeds(K.SEEDS_SWEEP if stage == "config_sweep" else K.SEEDS_HYPOTHESIS)
    if type(seed) is not int or seed not in required:
        raise ValueError("diagnostic seed is not in its exact registered hypothesis/sweep inventory")
    expected_digest = L._lower_sha256(source.expected_execution_digest, what="independent fit digest")
    F._validate_expected_git_commit(source.expected_git_commit)
    fit = F.load_fit_evidence(source.path, expected_git_commit=source.expected_git_commit)
    spec = F.registered_fit_spec(unit, arm="baseline", seed=seed)
    if (type(fit) is not F.VerifiedFitEvidence or fit.unit != unit or fit.arm != "baseline"
            or fit.seed != seed or fit.fit_id != spec.fit_id or fit.roles != spec.roles
            or fit.execution_digest != expected_digest or stage not in fit.roles):
        raise ValueError("diagnostic source does not match the independently expected baseline")
    result = _failure_metrics(fit.error, fit.diagnostics["disagreement"])
    return {
        "h2_diagnostic_schema_version": H2_DIAGNOSTIC_SCHEMA_VERSION,
        "purpose": "per_seed_metrics_not_h2_adjudication",
        "unit_id": Config(unit=unit).unit_id,
        "comparison_group_id": group_of(unit, stage), "stage": stage, "seed": seed,
        "fit_id": fit.fit_id, "execution_digest": fit.execution_digest,
        "expected_git_commit": source.expected_git_commit,
        "normalisation": fit.scale.as_row(),
        "failure_definition": {"operator": ">", "threshold": K.FAILURE_THRESHOLD},
        "ratio_floor": RATIO_FLOOR, "correlation_method": "pearson",
        "correlation_domain": "baseline_failure_set", **result,
        "observed_repair_label": None, "h2_verdict": None,
    }


def condition_failure_diagnostics(
    sources: Sequence[BaselineDiagnosticSource], *, unit: UnitSpec,
) -> dict[str, Any]:
    """Per-condition mean/sample SD of seed ratios; do not average correlations."""
    if type(unit) is not UnitSpec:
        raise ValueError("unit must be an exact UnitSpec")
    stage = stage_of(unit)
    seeds = confirmatory_seeds(K.SEEDS_SWEEP if stage == "config_sweep" else K.SEEDS_HYPOTHESIS)
    if type(sources) not in (tuple, list) or len(sources) != len(seeds):
        raise ValueError("exact complete ordered registered seed sources are required")
    rows = [baseline_failure_diagnostic(source, unit=unit, seed=seed)
            for source, seed in zip(sources, seeds, strict=True)]
    ratios = np.asarray([r["ratio_of_means"] for r in rows], dtype=np.float64)
    scale = float(ratios.max())
    scaled = ratios / scale if scale else ratios
    ratio_mean = float(scale * scaled.mean())
    ratio_sd = float(scale * scaled.std(ddof=1))
    if not np.isfinite([ratio_mean, ratio_sd]).all():
        raise ValueError("condition ratio summary is not finite")
    return {
        "h2_diagnostic_schema_version": H2_DIAGNOSTIC_SCHEMA_VERSION,
        "purpose": "condition_metrics_not_h2_adjudication",
        "unit_id": Config(unit=unit).unit_id, "seeds": list(seeds), "per_seed": rows,
        "ratio_mean_across_seeds": ratio_mean,
        "ratio_sample_sd_across_seeds": ratio_sd,
        "ratio_sd_ddof": 1, "transitions_pooled_across_seeds": False,
        "correlations_aggregated": False, "h2_verdict": None,
    }
