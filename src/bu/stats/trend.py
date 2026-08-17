"""The H1 trend test (Plan §4.2, Schedule W4 Mon). **One function, two stages.**

The Week 4 reliability gate and the Week 10 H1 verdict use *this* function, with
the same statistic, the same interval construction, the same direction and the
same pass rule. Only the seed partition differs — development for the gate,
confirmatory for the verdict — and the partition argument **validates and labels
the input without touching the mathematics** (D-068). Two implementations, or
one implementation with a stage-dependent branch, is how a gate and a verdict
come to disagree for reasons nobody recorded.

The reading rule, frozen before this ran on anything
----------------------------------------------------
Sol fixed every clause below *before* the function was applied to the pilot,
which is the point of it. The pilot's disagreement curve is **non-monotone at
the small end** — it peaks at N=250 in all three seeds — and a rank correlation
over six sizes is precisely the instrument that bends on that. Removing N=100 or
N=250, smoothing the curve, switching to Kendall, or bolting on a separate
monotonic-order rule would each convert an inconvenient result into a passing
one. P§4.2 says ordinary non-monotonicity in six observed means is *not itself*
the criterion; the criterion is the directional rank correlation with an
interval over seeds. The peak should weaken the statistic naturally. **That is
evidence, not an exception to repair.**

* Spearman's rho between ascending dataset size and mean pairwise disagreement,
  over **all six** preregistered sizes;
* expected direction **negative** — disagreement falls as data grows;
* **pass only when the entire 95% interval lies below zero**. An interval
  containing or touching zero fails. An interval entirely above zero is a
  reversed trend and fails. A constant curve or an undefined coefficient fails;
* individual out-of-order points have **no separate veto** beyond their effect
  on rho and its interval.

The interval, and why it is enumerated rather than sampled
-----------------------------------------------------------
A **paired seed-block bootstrap**: one seed's complete six-size curve is one
block, because the six sizes within a seed are not independent — Experiment 1's
datasets are nested prefixes of one another (D-030). Resample seeds with
replacement, average across the selected seeds at every size, recompute rho on
the six resulting means.

With 3 development seeds and 5 confirmatory ones the resample space is 3³ = 27
and 5⁵ = 3,125, so it is **enumerated exactly**. Every ordered tuple is one
resample, which reproduces the ordinary bootstrap's multinomial multiplicities
by construction. No bootstrap RNG exists — so there is no seed to record, drift
or forget, and two runs of a registered endpoint cannot differ.

The point estimate is rho on the **across-seed mean curve**. Per-seed curves and
per-seed rho values are reported as diagnostics and do **not** enter the pass
rule; a "3 of 5 seeds show it" reading is exactly the unreliable-positive that
Gate 2 exists to refuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping

import numpy as np

from .. import constants as K
from ..streams import is_confirmatory, seed_partition

#: Which seeds each stage may use, frozen by D-068. The Week 4 gate is estimator
#: selection: spending confirmatory evidence to choose an estimator would use it
#: up during method selection, which is what D-034's partition exists to stop.
PARTITIONS = frozenset({"development", "confirmatory"})


def _ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks, so tied values cannot be ordered by array position."""
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1, dtype=float)
    # Average within tie groups.
    unique, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    for i, count in enumerate(counts):
        if count > 1:
            ranks[inverse == i] = ranks[inverse == i].mean()
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman's rho: Pearson correlation of the average ranks.

    Returns ``nan`` when either side has no rank variation — a constant
    disagreement curve has no direction, and D-068 makes an undefined
    coefficient a **failure** rather than something to impute.
    """
    rx, ry = _ranks(np.asarray(x, dtype=float)), _ranks(np.asarray(y, dtype=float))
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return float("nan")
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


@dataclass(frozen=True)
class TrendResult:
    """The registered H1 statistic, its interval, and the verdict."""

    #: rho on the across-seed mean curve. The point estimate.
    rho: float
    ci_low: float
    ci_high: float
    #: The registered rule: the **whole** interval below zero.
    passed: bool
    #: Why, in words, so a run log says what happened rather than just False.
    reason: str
    partition: str
    seeds: tuple[int, ...]
    sizes: tuple[int, ...]
    #: Exactly ``n_seeds ** n_seeds``; enumerated, never sampled.
    n_resamples: int
    #: Diagnostics. They do **not** enter the pass rule (D-068).
    per_seed_rho: tuple[float, ...]
    mean_curve: tuple[float, ...]

    def as_row(self) -> dict:
        return {
            "rho": self.rho,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "passed": self.passed,
            "reason": self.reason,
            "partition": self.partition,
            "seeds": list(self.seeds),
            "sizes": list(self.sizes),
            "n_resamples": self.n_resamples,
            "per_seed_rho": list(self.per_seed_rho),
            "mean_curve": list(self.mean_curve),
            "direction": K.TREND_EXPECTED_DIRECTION,
            "bootstrap": K.TREND_BOOTSTRAP,
            "quantile_method": K.TREND_QUANTILE_METHOD,
            "confidence_level": K.CONFIDENCE_LEVEL,
        }

    def summary(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"H1 trend test [{self.partition}] {verdict}: rho = {self.rho:+.4f}, "
            f"95% CI [{self.ci_low:+.4f}, {self.ci_high:+.4f}] over "
            f"{len(self.seeds)} seeds ({self.n_resamples} exact resamples). "
            f"{self.reason}"
        )


def _validate(
    curves: Mapping[int, Mapping[int, float]],
    sizes: tuple[int, ...],
    partition: str,
) -> tuple[tuple[int, ...], np.ndarray]:
    """Reject anything the pass rule could not be read over.

    Every check here is a *refusal*, not a repair. A missing size, a duplicated
    one or an incomplete seed curve makes the six-point rank correlation
    something other than the registered statistic, and silently computing it
    over five points would produce a number that looks exactly like the real
    one.
    """
    if partition not in PARTITIONS:
        raise ValueError(
            f"partition must be one of {sorted(PARTITIONS)}, got {partition!r}"
        )
    if len(set(sizes)) != len(sizes):
        raise ValueError(f"duplicate dataset sizes: {sizes}")
    if list(sizes) != sorted(sizes):
        raise ValueError(f"sizes must be ascending, got {sizes}")
    if tuple(sizes) != tuple(K.DATA_SIZES):
        # D-068 says "use all six preregistered dataset sizes". Without this the
        # grid is an argument, and a five-point statistic computed over a
        # trimmed grid is indistinguishable from the registered one in every
        # artefact that carries it -- which is precisely the "drop the awkward
        # small end" move the frozen rule exists to forbid.
        raise ValueError(
            f"the registered grid is {tuple(K.DATA_SIZES)}, got {tuple(sizes)}. "
            "Dataset sizes are preregistered; the trend test is not defined over "
            "a subset of them (D-068)."
        )
    if not curves:
        raise ValueError("no seed curves supplied")

    seeds = tuple(sorted(curves))
    if len(seeds) < 2:
        raise ValueError(
            f"the seed-block bootstrap needs at least two seeds, got {len(seeds)}"
        )

    for seed in seeds:
        # The partition is validated, never inferred and never mixed. Pooling
        # development and confirmatory seeds is forbidden outright (D-034,
        # D-068): the gate would then consume the evidence the verdict needs.
        if seed_partition(seed) != partition:
            raise ValueError(
                f"seed {seed} is {seed_partition(seed)!r} but this call declares "
                f"{partition!r}. The W4 gate is development-only and the W10 "
                "verdict confirmatory-only; the two are never pooled (D-068)."
            )
        curve = curves[seed]
        missing = [n for n in sizes if n not in curve]
        if missing:
            raise ValueError(
                f"seed {seed} is missing dataset sizes {missing}. An incomplete "
                "curve cannot enter a paired seed block."
            )
        extra = [n for n in curve if n not in sizes]
        if extra:
            raise ValueError(
                f"seed {seed} carries dataset sizes {extra} outside the "
                f"registered grid {sizes}"
            )

    matrix = np.array(
        [[float(curves[seed][n]) for n in sizes] for seed in seeds], dtype=float
    )
    if not np.isfinite(matrix).all():
        raise ValueError("seed curves contain NaN or inf")
    return seeds, matrix


def trend_test(
    curves: Mapping[int, Mapping[int, float]],
    *,
    partition: str,
    sizes: tuple[int, ...] = K.DATA_SIZES,
) -> TrendResult:
    """The registered H1 statistic. Same function at the W4 gate and W10 verdict.

    Args:
        curves: ``{seed: {dataset_size: mean_pairwise_disagreement}}``. Every
            seed must carry every registered size; incomplete curves are
            refused rather than dropped.
        partition: ``"development"`` (W4 gate) or ``"confirmatory"`` (W10
            verdict). **Validates and labels only** — the mathematics below does
            not read it.
        sizes: the registered grid, ascending.

    Returns:
        The coefficient, the interval, and pass/fail under D-068's rule.
    """
    seeds, matrix = _validate(curves, sizes, partition)
    x = np.asarray(sizes, dtype=float)

    mean_curve = matrix.mean(axis=0)
    rho = spearman(x, mean_curve)
    per_seed_rho = tuple(spearman(x, row) for row in matrix)

    # Exact enumeration of every ordered resample of the seed blocks. Ordered
    # tuples give each multiset its multinomial weight, so this *is* the
    # ordinary bootstrap distribution, computed rather than approximated.
    n = len(seeds)
    resampled = np.array(
        [spearman(x, matrix[list(pick)].mean(axis=0)) for pick in product(range(n), repeat=n)]
    )

    if np.isnan(resampled).any() or np.isnan(rho):
        # An undefined coefficient anywhere in the distribution fails (D-068).
        # Imputing or dropping it would let a constant curve — the strongest
        # possible evidence *against* a trend — quietly produce an interval.
        ci_low = ci_high = float("nan")
        passed = False
        reason = (
            "undefined coefficient: at least one resampled curve has no rank "
            "variation, which is a constant disagreement curve"
        )
    else:
        lo, hi = 100 * (1 - K.CONFIDENCE_LEVEL) / 2, 100 * (1 + K.CONFIDENCE_LEVEL) / 2
        ci_low, ci_high = (
            float(v)
            for v in np.percentile(
                resampled, [lo, hi], method=K.TREND_QUANTILE_METHOD
            )
        )
        passed = ci_high < K.TREND_PASS_REQUIRES_UPPER_BOUND_BELOW
        if passed:
            reason = "the whole interval lies below zero"
        elif ci_low > 0:
            reason = (
                "REVERSED: the whole interval lies above zero — disagreement "
                "rises with data, the opposite of H1's prediction"
            )
        else:
            reason = "the interval contains or touches zero"

    return TrendResult(
        rho=rho,
        ci_low=ci_low,
        ci_high=ci_high,
        passed=passed,
        reason=reason,
        partition=partition,
        seeds=seeds,
        sizes=tuple(sizes),
        n_resamples=len(resampled),
        per_seed_rho=per_seed_rho,
        mean_curve=tuple(float(v) for v in mean_curve),
    )


def curves_from_rows(rows: list[dict]) -> dict[int, dict[int, float]]:
    """Build the input from one attempt's ``rows.json`` (C-010's spirit).

    Takes the rows of a **single immutable attempt** — never a directory tree —
    so the curve a verdict reads is traceable to one execution with one manifest
    and one set of run records.
    """
    curves: dict[int, dict[int, float]] = {}
    for row in rows:
        seed, n = int(row["seed"]), int(row["n_transitions"])
        disagreement = float(row["uncertainty"]["mean_disagreement"])
        if n in curves.setdefault(seed, {}):
            raise ValueError(
                f"seed {seed} has two rows for dataset size {n}; an attempt "
                "directory should hold exactly one run per (size, seed)"
            )
        curves[seed][n] = disagreement
    return curves
