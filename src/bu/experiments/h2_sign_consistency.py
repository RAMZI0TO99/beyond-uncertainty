"""Pure, fail-closed H2 sign-consistency calculation.

This module consumes already-prepared, strict-failure-set ratio rows.  It does
not read files, discover evidence, threshold error, infer repair labels, pair
comparison groups, or adjudicate H2.  Those boundaries are deliberate: strict
failure-set membership supplies the registered meaning of "high error", while
``ratio_of_means`` supplies the relative disagreement quantity.

Only exact observed repair labels 0 and 1 are eligible.  Construction classes,
ambiguous labels, and undiagnosed labels are not alternate spellings and are
refused.  Every accepted unit must have exactly one row for each of seeds
1000--1004 and immutable label/group provenance across those rows.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass


H2_SIGN_CONSISTENCY_SCHEMA_VERSION = 1
H2_SIGN_SEEDS: tuple[int, ...] = (1000, 1001, 1002, 1003, 1004)

_IDENTITY = re.compile(r"[0-9a-f]{12}")


@dataclass(frozen=True)
class H2SeedUnitRatio:
    """One eligible unit's registered ratio for one confirmatory seed.

    ``comparison_group_id`` is retained as provenance only.  The calculation
    gives every unit one vote and neither pairs nor clusters by this field.
    Validation occurs in :func:`compute_h2_sign_consistency`, so malformed
    synthetic rows can exercise the public fail-closed boundary.
    """

    unit_id: str
    comparison_group_id: str
    seed: int
    observed_label: int
    ratio_of_means: float


@dataclass(frozen=True)
class H2EligibleUnit:
    """Validated unit-level provenance retained in the result."""

    unit_id: str
    comparison_group_id: str
    observed_label: int


@dataclass(frozen=True)
class H2SeedContrast:
    """Equal-unit class contrast for one seed."""

    seed: int
    n_observed_0: int
    n_observed_1: int
    mean_ratio_observed_0: float
    mean_ratio_observed_1: float
    delta_observed_1_minus_0: float
    reproduced: bool


@dataclass(frozen=True)
class H2SignConsistency:
    """Five-seed reliability component; explicitly not an H2 verdict."""

    schema_version: int
    seeds: tuple[int, ...]
    eligible_units: tuple[H2EligibleUnit, ...]
    per_seed: tuple[H2SeedContrast, ...]
    reproduced_seeds: tuple[int, ...]
    n_reproduced: int
    denominator: int
    sign_consistency: float
    reliability_met: bool
    unit_weighting: str
    comparison_groups_retained: bool
    comparison_groups_used_for_pairing: bool
    inference_performed: bool
    h2_verdict: None


def _validated_identity(value: object, *, field: str) -> str:
    if type(value) is not str or _IDENTITY.fullmatch(value) is None:
        raise ValueError(f"{field} must be an exact lowercase 12-hex identity")
    return value


def _validated_label(value: object) -> int:
    if type(value) is not int or value not in (0, 1):
        raise ValueError(
            "observed_label must be exact integer 0 or 1; booleans, "
            "ambiguous/undiagnosed outcomes, and intended/construction "
            "classes are forbidden"
        )
    return value


def _validated_seed(value: object) -> int:
    if type(value) is not int or value not in H2_SIGN_SEEDS:
        raise ValueError(
            f"seed must be an exact registered H2 sign seed in {H2_SIGN_SEEDS}"
        )
    return value


def _validated_ratio(value: object) -> float:
    if type(value) is not float or not math.isfinite(value) or value < 0:
        raise ValueError(
            "ratio_of_means must be an exact finite nonnegative float"
        )
    return value


def _scaled_mean(values: Sequence[float]) -> float:
    """Return an arithmetic mean without overflowing a finite input sum."""
    if not values:
        raise ValueError("each seed must contain both observed repair classes")
    scale = max(values)
    if scale == 0:
        return 0.0
    mean = scale * (math.fsum(value / scale for value in values) / len(values))
    if not math.isfinite(mean):
        raise ValueError("class mean ratio is not finite")
    return mean


def compute_h2_sign_consistency(
    rows: Sequence[H2SeedUnitRatio],
) -> H2SignConsistency:
    """Compute the fixed five-seed H2 sign-consistency reliability metric.

    For each seed, the arithmetic mean ratio among observed-label-1 units is
    subtracted from neither quantity: the registered contrast is exactly
    ``mean(class 1) - mean(class 0)``.  A seed reproduces the signature only
    when that delta is strictly negative.  Equality therefore does not count.

    The input must be a complete rectangular unit-by-seed inventory.  A
    missing row, duplicate unit/seed, changing label or group, absent class, or
    malformed scalar blocks the entire calculation rather than changing the
    denominator.
    """
    if type(rows) not in (tuple, list) or not rows:
        raise ValueError("rows must be a nonempty exact list or tuple")

    by_cell: dict[tuple[str, int], float] = {}
    unit_metadata: dict[str, tuple[str, int]] = {}
    unit_seeds: dict[str, set[int]] = {}

    for position, row in enumerate(rows):
        if type(row) is not H2SeedUnitRatio:
            raise ValueError(
                f"row at position {position} must be an exact H2SeedUnitRatio; "
                "raw dictionaries and alternate provenance records are forbidden"
            )
        unit_id = _validated_identity(row.unit_id, field="unit_id")
        group_id = _validated_identity(
            row.comparison_group_id, field="comparison_group_id"
        )
        seed = _validated_seed(row.seed)
        label = _validated_label(row.observed_label)
        ratio = _validated_ratio(row.ratio_of_means)

        cell = (unit_id, seed)
        if cell in by_cell:
            raise ValueError(f"duplicate unit-seed row {cell!r}")
        by_cell[cell] = ratio

        metadata = (group_id, label)
        previous = unit_metadata.setdefault(unit_id, metadata)
        if previous != metadata:
            raise ValueError(
                f"unit {unit_id!r} changes comparison group or observed label "
                "across seeds"
            )
        unit_seeds.setdefault(unit_id, set()).add(seed)

    required_seeds = set(H2_SIGN_SEEDS)
    for unit_id, seeds in unit_seeds.items():
        if seeds != required_seeds:
            missing = sorted(required_seeds - seeds)
            extra = sorted(seeds - required_seeds)
            raise ValueError(
                f"unit {unit_id!r} lacks the exact five-seed inventory; "
                f"missing={missing}, extra={extra}"
            )

    units = tuple(
        H2EligibleUnit(
            unit_id=unit_id,
            comparison_group_id=unit_metadata[unit_id][0],
            observed_label=unit_metadata[unit_id][1],
        )
        for unit_id in sorted(unit_metadata)
    )
    class_units = {
        label: tuple(unit.unit_id for unit in units if unit.observed_label == label)
        for label in (0, 1)
    }
    if not class_units[0] or not class_units[1]:
        raise ValueError("each seed must contain both observed repair classes")

    contrasts: list[H2SeedContrast] = []
    for seed in H2_SIGN_SEEDS:
        ratios_0 = [by_cell[(unit_id, seed)] for unit_id in class_units[0]]
        ratios_1 = [by_cell[(unit_id, seed)] for unit_id in class_units[1]]
        mean_0 = _scaled_mean(ratios_0)
        mean_1 = _scaled_mean(ratios_1)
        delta = mean_1 - mean_0
        if not math.isfinite(delta):
            raise ValueError("class mean contrast is not finite")
        contrasts.append(
            H2SeedContrast(
                seed=seed,
                n_observed_0=len(ratios_0),
                n_observed_1=len(ratios_1),
                mean_ratio_observed_0=mean_0,
                mean_ratio_observed_1=mean_1,
                delta_observed_1_minus_0=delta,
                reproduced=delta < 0,
            )
        )

    per_seed = tuple(contrasts)
    reproduced = tuple(row.seed for row in per_seed if row.reproduced)
    n_reproduced = len(reproduced)
    denominator = len(H2_SIGN_SEEDS)
    return H2SignConsistency(
        schema_version=H2_SIGN_CONSISTENCY_SCHEMA_VERSION,
        seeds=H2_SIGN_SEEDS,
        eligible_units=units,
        per_seed=per_seed,
        reproduced_seeds=reproduced,
        n_reproduced=n_reproduced,
        denominator=denominator,
        sign_consistency=n_reproduced / denominator,
        reliability_met=n_reproduced == denominator,
        unit_weighting="equal_unit",
        comparison_groups_retained=True,
        comparison_groups_used_for_pairing=False,
        inference_performed=False,
        h2_verdict=None,
    )
