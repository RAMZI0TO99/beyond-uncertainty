"""The Week 5 minimum-detectable-effect simulation (C-006, P§10.7, S§W5 Thu).

**What this is for.** Gate 1 asks whether the design can resolve a five-point
balanced-accuracy difference at eighty percent power (P§4.2, P§10.7). If it
cannot, the fix is *configuration count* — never seeds, which Plan v1.2
withdrew as a lever, and never the reliability protocol.

**Why it is a simulation and not a formula** (D-044). The estimand is a
**unit-weighted** balanced accuracy over configuration-conditions that are
**correlated within comparison groups**, compared **paired** against a fitted
baseline on the same held-out units. Sol's ruling was that the simulation must
reproduce *that* estimator rather than a scalar proxy: actual group sizes,
actual class membership, group-preserving partitions, unit weights, paired
predictions, within-group correlation, and the balanced-accuracy difference with
its interval.

**There is deliberately no ``n_eff()`` here.** D-044: "A function returning an
effective sample size is how the first wrong number escaped, and naming it would
invite the same misuse." The analytic effective sample sizes exist only inside
`tests/test_mde.py`, as the two agreements that validate this module — at
ICC = 0 against the independent-units result, and at ICC = 1 against the
unit-weighted boundary of 75.00 and 72.58. They are a *check on the simulation*,
not an output of it.

**The design this samples from is the real one.** 300 units in 240 comparison
groups, class-pure: class 0 is 150 units in 125 groups (120 singletons and five
of size six), class 1 is 150 units in 115 groups (105 singletons, five of size
four and five of size five). Because no group spans both classes, a
group-preserving partition is automatically class-preserving.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass

import numpy as np
from scipy import stats

from .. import constants as K
from ..config import Config
from ..experiments.enumerate_units import (
    _intended_class, design_units, obligations,
)
from ..streams import comparison_group_id

#: P§10.7, verbatim: "the smallest balanced-accuracy difference the design can
#: resolve at eighty percent power".
TARGET_POWER = 0.80

#: Not stated in the plan. Two-sided 0.05, consistent with the 95% intervals
#: used for repair acceptance (P§7.3) and the trend test (D-068). Recorded as a
#: stated assumption rather than chosen silently (DEV-008).
ALPHA = 0.05

#: S§W5 Thu: "Minimum-detectable-effect simulation at N = 20 / 40 / 60 / 80
#: held-out units." Read as the **total** held out, with unit-level class
#: balance, so ``min(N0, N1)`` is half of it — reported alongside, because
#: power depends on the smaller class and a number without its estimand is not
#: a number (D-042, D-044).
HELDOUT_GRID: tuple[int, ...] = (20, 40, 60, 80)


def design_group_sizes() -> dict[int, tuple[int, ...]]:
    """Comparison-group sizes per class, from the real 300-unit design matrix."""
    units = design_units()
    stage = {o.unit_id: o.stage for o in obligations(units)}
    groups: dict[str, list] = collections.defaultdict(list)
    for unit in units:
        key = comparison_group_id(unit, stage[Config(unit=unit).unit_id])
        groups[key].append(unit)

    by_class: dict[int, list[int]] = collections.defaultdict(list)
    for members in groups.values():
        classes = {_intended_class(m) for m in members}
        if len(classes) != 1:
            raise RuntimeError(
                f"comparison group spans classes {classes}; a group-preserving "
                "partition would no longer be class-preserving, and the balanced "
                "accuracy's two halves would not be independent of the split (D-039)"
            )
        by_class[classes.pop()].append(len(members))
    return {c: tuple(sorted(sizes)) for c, sizes in sorted(by_class.items())}


@dataclass(frozen=True)
class HeldOutDesign:
    """The held-out units, as whole comparison groups, per class.

    ``sizes[c]`` are the group sizes drawn for class ``c``. Units are never
    split across a partition boundary: a comparison group was *given* related
    data by design, so a group spanning a split leaks between train and held-out
    (D-039).
    """

    sizes: dict[int, tuple[int, ...]]

    @property
    def n_units(self) -> dict[int, int]:
        return {c: int(sum(s)) for c, s in self.sizes.items()}

    @property
    def n_total(self) -> int:
        return sum(self.n_units.values())

    @property
    def min_class(self) -> int:
        """``min(N0, N1)`` — what power actually depends on (S§W5, D-042)."""
        return min(self.n_units.values())

    @property
    def n_groups(self) -> dict[int, int]:
        return {c: len(s) for c, s in self.sizes.items()}


def projected_pool(
    n_units_per_class: int, *, pool: dict[int, tuple[int, ...]] | None = None
) -> dict[int, tuple[int, ...]]:
    """The design's group-size *distribution*, scaled to a larger unit count.

    P§10.7 computes the MDE "over the projected number of held-out units", and
    P§14.3's escalation raises **configuration count** when it does not clear
    the margin. Projecting means keeping the shape of the design — the mix of
    singleton sweep units and multi-unit canonical comparison groups — and
    repeating it, because that mix is what determines how much the correlation
    costs. Scaling by inflating existing groups instead would change the design
    effect and flatter the answer.
    """
    pool = pool or design_group_sizes()
    out: dict[int, tuple[int, ...]] = {}
    for cls, sizes in pool.items():
        reps = int(np.ceil(n_units_per_class / sum(sizes)))
        scaled: list[int] = []
        total = 0
        for _ in range(reps):
            for m in sizes:
                if total >= n_units_per_class:
                    break
                scaled.append(int(m))
                total += m
        out[cls] = tuple(sorted(scaled))
    return out


def draw_heldout(
    n_heldout: int,
    rng: np.random.Generator,
    *,
    pool: dict[int, tuple[int, ...]] | None = None,
) -> HeldOutDesign:
    """Draw whole comparison groups until each class reaches ``n_heldout // 2``.

    Class balance is at the **unit** level (P§10.4), so each class is filled to
    the same unit count. Because groups are indivisible, the last group drawn
    may overshoot; it is taken whole and the overshoot is reported rather than
    trimmed — trimming would split a group, which is the one thing the
    partition may not do.
    """
    if n_heldout % 2:
        raise ValueError(
            f"n_heldout={n_heldout} is odd; unit-level class balance needs an even "
            "split between the two classes (P§10.4)"
        )
    pool = pool or design_group_sizes()
    target = n_heldout // 2
    sizes: dict[int, tuple[int, ...]] = {}
    for cls, available in pool.items():
        order = rng.permutation(len(available))
        drawn, total = [], 0
        for index in order:
            if total >= target:
                break
            drawn.append(int(available[index]))
            total += drawn[-1]
        if total < target:
            raise ValueError(
                f"class {cls} has only {sum(available)} units in the design; cannot "
                f"hold out {target}"
            )
        sizes[cls] = tuple(sorted(drawn))
    return HeldOutDesign(sizes=sizes)


def _correlated_latents(
    group_sizes: tuple[int, ...],
    *,
    icc: float,
    system_corr: float,
    n_sim: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Two ``(n_sim, n_units)`` standard-normal latents.

    Within a comparison group, units correlate at ``icc``; between the two
    systems, a unit's latents correlate at ``system_corr``. Both marginals are
    standard normal, so a threshold at ``Phi^-1(p)`` gives exactly accuracy
    ``p`` — which is what makes the simulated accuracies the ones asked for
    rather than approximately them.
    """
    n_units = int(sum(group_sizes))
    index = np.repeat(np.arange(len(group_sizes)), group_sizes)

    def pair(shape):
        a = rng.standard_normal(shape)
        b = system_corr * a + np.sqrt(max(0.0, 1.0 - system_corr**2)) * rng.standard_normal(shape)
        return a, b

    shared_a, shared_b = pair((n_sim, len(group_sizes)))
    own_a, own_b = pair((n_sim, n_units))
    w_group, w_unit = np.sqrt(icc), np.sqrt(1.0 - icc)
    za = w_group * shared_a[:, index] + w_unit * own_a
    zb = w_group * shared_b[:, index] + w_unit * own_b
    return za, zb


def _balanced_accuracy(correct: dict[int, np.ndarray]) -> np.ndarray:
    """Unit-weighted balanced accuracy: equal weight per unit inside a class,
    then the unweighted mean of the two class accuracies (D-044)."""
    return np.mean([c.mean(axis=1) for c in correct.values()], axis=0)


def _bootstrap_se(
    correct_a: dict[int, np.ndarray],
    correct_b: dict[int, np.ndarray],
    group_sizes: dict[int, tuple[int, ...]],
    *,
    n_boot: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Group-bootstrap standard error of the paired difference, per simulation.

    Whole comparison groups are resampled with replacement, **stratified by
    class** so both halves of the balanced accuracy stay populated. Resampling
    units would treat correlated units as exchangeable and understate the
    interval — which is the entire reason the interval is a group bootstrap
    (D-039, D-044).
    """
    if n_boot < 2:
        raise ValueError(
            f"n_boot={n_boot}: a standard error needs at least two resamples. One "
            "gives a zero-degrees-of-freedom variance, i.e. nan, and nan compared "
            "against a critical value is silently False -- a test that never rejects"
        )
    n_sim = next(iter(correct_a.values())).shape[0]
    diffs = np.empty((n_boot, n_sim))
    starts = {
        c: np.concatenate([[0], np.cumsum(s)]) for c, s in group_sizes.items()
    }
    for b in range(n_boot):
        per_class_a, per_class_b = {}, {}
        for cls, sizes in group_sizes.items():
            picks = rng.integers(0, len(sizes), size=len(sizes))
            cols = np.concatenate(
                [np.arange(starts[cls][p], starts[cls][p + 1]) for p in picks]
            )
            per_class_a[cls] = correct_a[cls][:, cols]
            per_class_b[cls] = correct_b[cls][:, cols]
        diffs[b] = _balanced_accuracy(per_class_a) - _balanced_accuracy(per_class_b)
    return diffs.std(axis=0, ddof=1)


def simulate(
    design: HeldOutDesign,
    *,
    baseline_accuracy: float,
    delta: float,
    icc: float,
    system_corr: float = 0.0,
    n_sim: int = 2000,
    n_boot: int = 400,
    rng: np.random.Generator | None = None,
) -> dict:
    """Simulate the paired balanced-accuracy comparison and return its power.

    Args:
        delta: the **true** balanced-accuracy advantage of the critic, in
            proportion units (0.05 is the five-point margin).
        icc: within-comparison-group correlation of unit-level correctness.
        system_corr: correlation between the critic's and the baseline's
            difficulty on the same unit. **0.0 is the conservative default** —
            independent systems make the difference's variance largest and the
            MDE widest. Real pairing can only help, so an MDE computed here does
            not depend on assuming it.
    """
    if not 0.0 <= icc <= 1.0:
        raise ValueError(f"icc must be in [0, 1], got {icc}")
    if not 0.0 <= system_corr <= 1.0:
        raise ValueError(f"system_corr must be in [0, 1], got {system_corr}")
    if not 0.0 < baseline_accuracy < 1.0:
        raise ValueError(f"baseline_accuracy must be in (0, 1), got {baseline_accuracy}")
    if not 0.0 <= baseline_accuracy + delta < 1.0:
        # Clipping instead would silently saturate: every unit correct, the
        # difference pinned, and a power curve that flattens for a reason the
        # reader cannot see.
        raise ValueError(
            f"baseline_accuracy + delta = {baseline_accuracy + delta:.3f} is not a "
            "probability; the critic cannot be more than perfectly accurate. Bound "
            "the delta grid to 1 - baseline_accuracy"
        )
    rng = rng or np.random.default_rng(0)

    correct_a, correct_b = {}, {}
    for cls, sizes in design.sizes.items():
        za, zb = _correlated_latents(
            sizes, icc=icc, system_corr=system_corr, n_sim=n_sim, rng=rng
        )
        correct_a[cls] = za < stats.norm.ppf(min(1 - 1e-12, baseline_accuracy + delta))
        correct_b[cls] = zb < stats.norm.ppf(baseline_accuracy)

    observed = _balanced_accuracy(correct_a) - _balanced_accuracy(correct_b)
    se = _bootstrap_se(correct_a, correct_b, design.sizes, n_boot=n_boot, rng=rng)
    critical = stats.norm.ppf(1 - ALPHA / 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        reject = np.abs(observed) > critical * se
    return {
        "power": float(np.mean(reject)),
        "mean_difference": float(np.mean(observed)),
        "mean_se": float(np.mean(se)),
        "delta": delta,
        "icc": icc,
        "system_corr": system_corr,
        "n_heldout": design.n_total,
        "min_class": design.min_class,
        "n_groups": design.n_groups,
        "n_sim": n_sim,
        "n_boot": n_boot,
    }


def minimum_detectable_effect(
    design: HeldOutDesign,
    *,
    baseline_accuracy: float = 0.70,
    icc: float,
    system_corr: float = 0.0,
    target_power: float = TARGET_POWER,
    grid: np.ndarray | None = None,
    n_sim: int = 2000,
    n_boot: int = 400,
    rng: np.random.Generator | None = None,
) -> dict:
    """The smallest simulated ``delta`` reaching ``target_power``.

    Returned as a grid search rather than a root-find: the power curve is
    estimated with Monte-Carlo noise, so a bisection would chase that noise and
    report a precision the simulation does not have. The curve travels with the
    answer so a reader can see how flat it is near the threshold.
    """
    rng = rng or np.random.default_rng(0)
    grid = np.arange(0.01, 0.31, 0.01) if grid is None else np.asarray(grid)
    grid = grid[grid + baseline_accuracy < 1.0]
    if not len(grid):
        raise ValueError(
            f"no delta on the grid leaves baseline_accuracy={baseline_accuracy} a "
            "probability"
        )
    curve = [
        simulate(
            design, baseline_accuracy=baseline_accuracy, delta=float(d), icc=icc,
            system_corr=system_corr, n_sim=n_sim, n_boot=n_boot, rng=rng,
        )
        for d in grid
    ]
    reached = [row for row in curve if row["power"] >= target_power]
    return {
        "mde": float(reached[0]["delta"]) if reached else float("nan"),
        "reached_target": bool(reached),
        "target_power": target_power,
        "baseline_accuracy": baseline_accuracy,
        "icc": icc,
        "system_corr": system_corr,
        "n_heldout": design.n_total,
        "min_class": design.min_class,
        "curve": curve,
    }


def report(
    *,
    heldout: tuple[int, ...] = HELDOUT_GRID,
    iccs: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
    baseline_accuracy: float = 0.70,
    system_corr: float = 0.0,
    n_sim: int = 3000,
    n_boot: int = 400,
    seed: int = 7,
) -> str:
    """The W5 MDE table, regenerable from one command (S§W5 Thu).

    Defaults are the **conservative** ones: independent systems, so the table
    does not depend on assuming the critic and the baseline find the same units
    hard. Real pairing can only shrink these numbers, and the sensitivity to it
    is large enough that it must be reported alongside rather than folded in.
    """
    lines = [
        f"W5 MINIMUM DETECTABLE EFFECT -- balanced-accuracy difference, "
        f"{int(TARGET_POWER * 100)}% power, alpha {ALPHA} two-sided",
        f"  estimand: unit-weighted balanced accuracy over configuration-conditions",
        f"  baseline accuracy {baseline_accuracy}, system pairing {system_corr}, "
        f"latent within-group ICC as column",
        f"  group-preserving held-out draws; group-bootstrap interval "
        f"({n_sim} simulations x {n_boot} resamples)",
        "",
        f"  {'held out':>9} {'min(N0,N1)':>11}" + "".join(f"{f'ICC {i}':>10}" for i in iccs),
    ]
    for n in heldout:
        design = draw_heldout(n, np.random.default_rng(100 + n))
        cells = []
        for icc in iccs:
            result = minimum_detectable_effect(
                design, baseline_accuracy=baseline_accuracy, icc=icc,
                system_corr=system_corr, n_sim=n_sim, n_boot=n_boot,
                rng=np.random.default_rng(seed),
            )
            cells.append(
                f"{result['mde'] * 100:>8.1f}pp" if result["reached_target"] else "     >30"
            )
        lines.append(
            f"  {design.n_total:>9} {design.min_class:>11}" + "".join(f"{c:>10}" for c in cells)
        )
    lines += [
        "",
        f"  Gate 1 asks whether this clears {int(K.EQUIVALENCE_MARGIN_PP)} points "
        "(P§4.2, P§10.7). Where it does not,",
        "  P§14.3's remedy is to raise CONFIGURATION COUNT -- never seeds, which",
        "  Plan v1.2 withdrew as a lever, and never the reliability protocol.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    print(report())
