"""The repair acceptance test (P§7.3, S§W5 Tue), and its permutation null (S§W5 Wed).

**What it decides.** Whether a repair actually worked. Plan v1.0 used "two
across-seed standard deviations over five seeds"; v1.2 withdrew that, because at
n = 5 the sample standard deviation is itself so noisy that the criterion moves
with the noise it is meant to control.

**Three conditions, all required** (P§7.3, and frozen in §2 of PROJECT_STATE):

1. the fixed effect for repair condition is **negative** — error reduced;
2. its **95% confidence interval excludes zero**;
3. the estimated reduction exceeds the **minimum practical effect**, fixed
   before data collection at **20% relative** (`K.MIN_PRACTICAL_EFFECT`).

A repair that clears (1) and (2) but not (3) is a real but negligible effect,
and the third condition exists so that a large enough sample cannot manufacture
a "successful" repair out of one.

**The registered analysis, in one sentence** (P§7.3 as amended by D-094 and
D-100). For each matched transition, the repaired minus baseline error; those
differences averaged within each seed; the **twenty seeds as replication
units**; a t interval on nineteen degrees of freedom; and a relative reduction
taken against the **equal-seed** baseline mean, so both sides of the ratio are
weighted the same way.

**Why the pairing is taken first.** Step 4 of the protocol evaluates every
repair on the *same recorded failure set* as the unrepaired condition, so
everything the two arms share on a transition — the seed effect, the episode
effect, that transition's own difficulty — is common to both rows and cancels in
the difference. Charging it to residual variance instead made the interval 1.51x
the true paired spread (D-086).

**Why seeds remain the replication level.** Repair effects vary across training
runs, which is exactly what P§7.3's twenty seeds exist to measure. An analysis
that treated pairs as exchangeable would understate the standard error by up to
8.7x (D-094).

**There is no fallback** (D-100). The old episode-mean fallback existed because
an optimiser could fail; this analysis has none. If the across-seed interval
cannot be formed, the result fails closed rather than switching the replication
unit from seeds to episodes on the strength of the observed data.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import beta

from .. import constants as K

#: The registered interval. 95%, matching P§7.3's "ninety-five percent
#: confidence interval excluding zero".
CONFIDENCE = 0.95

#: The size the acceptance rule actually has under the null -- **half** the
#: two-sided level, not all of it.
#:
#: Sol corrected its own D-085 target here, and the correction is directional.
#: Acceptance requires a **negative** effect *and* a two-sided 95% interval
#: entirely below zero. Under the null a two-sided interval excludes zero 5% of
#: the time, split evenly between the two directions, so rejection in the one
#: beneficial direction has nominal probability **2.5%**. Calibrating against
#: 5% would have demanded the test reject twice as often as the rule permits,
#: and would have condemned a correctly sized procedure as conservative.
DIRECTIONAL_NOMINAL = (1 - CONFIDENCE) / 2


@dataclass(frozen=True)
class AcceptanceResult:
    """A repair's verdict, with everything needed to report it honestly."""

    #: The **equal-seed mean paired difference**, repaired minus baseline. Not a
    #: fixed effect from a mixed model (D-100) -- there is no model being fitted.
    effect: float
    ci_low: float
    ci_high: float
    #: Reduction relative to the unrepaired mean. Positive means error fell.
    relative_reduction: float
    passed: bool
    reason: str
    #: Always ``"paired_seed_cluster"``. Kept as a field because a recorded
    #: result must say which analysis produced it, and the registered analysis
    #: has changed once already (D-094, D-100).
    method: str
    #: Whether the across-seed interval could be formed at all. There is no
    #: optimiser here, so this is not convergence in the fitting sense.
    converged: bool
    n_transitions: int
    n_seeds: int
    n_episodes: int
    unrepaired_mean: float

    def as_row(self) -> dict:
        return {
            "effect": self.effect,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "relative_reduction": self.relative_reduction,
            "passed": self.passed,
            "reason": self.reason,
            "method": self.method,
            "converged": self.converged,
            "n_transitions": self.n_transitions,
            "n_seeds": self.n_seeds,
            "n_episodes": self.n_episodes,
            "unrepaired_mean": self.unrepaired_mean,
            "min_practical_effect": K.MIN_PRACTICAL_EFFECT,
            "confidence": CONFIDENCE,
        }

    def summary(self) -> str:
        verdict = "ACCEPTED" if self.passed else "REJECTED"
        return (
            f"REPAIR {verdict} ({self.method}"
            f"{'' if self.converged else ', INTERVAL NOT FORMED'})\n"
            f"  equal-seed mean paired difference {self.effect:+.6f}  95% t CI "
            f"[{self.ci_low:+.6f}, {self.ci_high:+.6f}]\n"
            f"  relative reduction {self.relative_reduction:+.1%} against a "
            f"{K.MIN_PRACTICAL_EFFECT:.0%} minimum\n"
            f"  {self.reason}\n"
            f"  {self.n_transitions} transitions, {self.n_episodes} episodes, "
            f"{self.n_seeds} seeds"
        )


def _frame(errors, repair, seed, episode, transition) -> pd.DataFrame:
    errors = np.asarray(errors, dtype=float)
    repair = np.asarray(repair)
    seed = np.asarray(seed)
    episode = np.asarray(episode)
    transition = np.asarray(transition)
    lengths = {len(errors), len(repair), len(seed), len(episode), len(transition)}
    if len(lengths) != 1:
        raise ValueError(
            f"errors, repair, seed, episode and transition must be the same "
            f"length; got {[len(errors), len(repair), len(seed), len(episode), len(transition)]}"
        )
    if not len(errors):
        raise ValueError("no transitions; a mean over nothing is nan")
    if set(np.unique(repair)) - {0, 1, True, False}:
        raise ValueError(
            f"repair must be a 0/1 indicator, got values {np.unique(repair)}"
        )
    if len(np.unique(repair)) != 2:
        raise ValueError(
            "repair takes only one value, so there is no comparison to make. A "
            "one-armed acceptance test would report the intercept as an effect"
        )
    frame = pd.DataFrame(
        {
            "error": errors,
            "repair": repair.astype(float),
            "seed": seed,
            # Episode identity is only meaningful *within* a seed (D-052): two
            # seeds both have an episode 0, and they are different episodes.
            "episode": [f"{s}::{e}" for s, e in zip(seed, episode)],
            # The PAIR: one evaluation transition, scored under both arms. Scoped
            # by seed and episode because a step index repeats across both.
            "pair": [f"{s}::{e}::{x}" for s, e, x in zip(seed, episode, transition)],
        }
    )
    _validate_pairing(frame)
    return frame


def _validate_pairing(frame: pd.DataFrame) -> None:
    """Every pair must carry exactly one baseline and one repaired observation.

    The whole point of the transition-within-episode term is that the SAME
    evaluation transition is scored under both arms (P§7.2 step 4). A pair with
    two rows of one arm, or one row of one arm, is not a pair -- and a model
    told to treat it as one would attribute the arm difference to whatever the
    unmatched rows happened to contain. Checked rather than assumed, because a
    mask or a pool mismatch upstream produces exactly that shape silently.
    """
    counts = frame.groupby("pair")["repair"].agg(["size", "sum"])
    bad = counts[(counts["size"] != 2) | (counts["sum"] != 1.0)]
    if len(bad):
        example = bad.index[0]
        raise ValueError(
            f"{len(bad)} transition pair(s) do not carry exactly one baseline and "
            f"one repaired observation -- for example {example!r}, with "
            f"{int(bad.iloc[0]['size'])} row(s) of which {int(bad.iloc[0]['sum'])} "
            "repaired. The acceptance test is paired per transition within seed "
            "(P§7.2 step 4); an unmatched pair is not a pair, and modelling it as "
            "one attributes the arm difference to whatever the odd rows contain"
        )


def _verdict(effect, ci_low, ci_high, unrepaired_mean) -> tuple[bool, float, str]:
    relative = -effect / unrepaired_mean if unrepaired_mean > 0 else float("nan")
    negative = effect < 0
    excludes_zero = ci_high < 0
    practical = relative >= K.MIN_PRACTICAL_EFFECT
    if negative and excludes_zero and practical:
        return True, relative, (
            "all three conditions met: negative equal-seed mean paired "
            "difference, 95% t interval "
            f"excluding zero, and a {relative:.1%} reduction clearing the "
            f"{K.MIN_PRACTICAL_EFFECT:.0%} minimum practical effect"
        )
    failures = []
    if not negative:
        failures.append(
            "the equal-seed mean paired difference is not negative (error did not fall)"
        )
    if not excludes_zero:
        failures.append("the 95% t interval includes zero")
    if not practical:
        failures.append(
            f"the {relative:.1%} reduction does not clear the "
            f"{K.MIN_PRACTICAL_EFFECT:.0%} minimum practical effect"
        )
    return False, relative, "; ".join(failures)


def acceptance_test(
    errors, repair, seed, episode, transition, *, allow_fallback: bool = True
) -> AcceptanceResult:
    """Run the registered acceptance test on per-transition error (P§7.3).

    **Change Record, 2026-08-20 (D-094), authorised by Sol.** The model now
    carries a **transition-within-episode** variance component. The registered
    v1.2 model had random intercepts for seed and episode-within-seed only,
    while the comparison is paired transition-by-transition on the same failure
    set — so the difficulty shared between the two arms on one transition
    cancels in the contrast but was still being counted as residual variance.
    Measured: the interval came out **1.51×** the true paired null spread, and
    the test was conservative. Sol authorised the change rather than accepting it
    as a power limitation, on the grounds that repair acceptance **creates the
    thesis labels**: an over-wide interval converts genuine repairs into
    ambiguous or undiagnosed units and so alters H2's and H3's population.

    Args:
        errors: per-transition error, unrepaired and repaired rows together.
        repair: 0/1 per transition — 1 for the repaired arm.
        seed: seed id per transition.
        episode: episode id per transition, interpreted **within** its seed.
        transition: the transition identifier (``ArmEvaluation.step``). Required,
            not optional: it is what identifies the two arms' rows as the *same*
            transition, and an absent pairing key would silently restore the
            over-wide interval this Change Record exists to remove.
        allow_fallback: **retained only to refuse it.** There is no fallback in
            registered acceptance any more (D-100): the analysis has no optimiser
            that can fail, and switching the replication unit to episodes because
            of the observed data would be choosing the inference after seeing it.
            Passing ``False`` is accepted and means what it says; passing ``True``
            is accepted and changes nothing.
    """
    data = _frame(errors, repair, seed, episode, transition)
    unrepaired_mean = equal_seed_baseline_mean(data)
    counts = dict(
        n_transitions=len(data),
        n_seeds=int(data.seed.nunique()),
        n_episodes=int(data.episode.nunique()),
        unrepaired_mean=unrepaired_mean,
    )

    return _paired_seed_cluster(data, counts, unrepaired_mean, allow_fallback)


def equal_seed_baseline_mean(data: pd.DataFrame) -> float:
    """The denominator, weighted the same way the effect is (Sol, delta 45).

    ``mean_s(mean_i baseline_error[s, i])``. The effect equally weights seed
    means, so a denominator that weighted raw transitions would make the
    reported relative reduction a ratio of two differently-weighted quantities —
    the D-042/D-044 shape, where a number is correct arithmetic on mismatched
    estimands. Seeds contribute equally to both.
    """
    baseline = data.loc[data.repair == 0]
    return float(baseline.groupby("seed")["error"].mean().mean())


def paired_differences(data: pd.DataFrame) -> pd.DataFrame:
    """One row per transition pair: the repaired-minus-baseline error.

    Everything the two arms share on a transition -- the seed effect, the episode
    effect and the transition's own difficulty -- is common to both rows and
    cancels here, before any averaging. That cancellation IS the Change Record
    (D-094); the old model charged the shared difficulty to residual variance.
    """
    wide = data.pivot_table(
        index=["seed", "episode", "pair"], columns="repair", values="error"
    )
    out = (wide[1.0] - wide[0.0]).rename("difference").reset_index()
    return out


def _paired_seed_cluster(data, counts, unrepaired_mean, allow_fallback) -> AcceptanceResult:
    """The registered acceptance analysis (P§7.3 as amended by D-094, D-100).

    **The estimand, stated.** For each matched transition, the repaired minus
    baseline error. Those differences are averaged within each seed; the twenty
    seed means are the replication units; the interval is a t interval on
    nineteen degrees of freedom. The relative reduction is that equal-seed mean
    difference over the equal-seed baseline mean — both sides weighted the same
    way. This is **not** a fixed effect from a mixed model and is not described
    as one.

    **Why this rather than the long-form variance-component model.** Shared
    intercepts cancel from the paired treatment contrast, so that specification
    was singular in practice (`LinAlgError` at 250 and 1,000 pairs),
    computationally unacceptable where it did fit (231 s, which makes a
    200-permutation null a ~13-hour run), and — reduced to what it could
    actually estimate — did not represent **repair-effect heterogeneity across
    seeds**, understating the standard error by up to 8.7×. Those three facts
    justify this analysis. They are not a proof that every variance component is
    mathematically unidentifiable in long-form data, and the claim is not made.

    **There is no fallback.** The previous episode-mean fallback existed because
    an optimiser could fail; this analysis has no optimiser. If the across-seed
    interval cannot be formed, the result **fails closed** rather than switching
    the inferential replication unit from seeds to episodes on the strength of
    the observed data (Sol, delta 45).
    """
    from scipy import stats

    paired = paired_differences(data)
    per_seed = paired.groupby("seed")["difference"].mean()
    n = int(per_seed.size)

    def refuse(reason: str) -> AcceptanceResult:
        return AcceptanceResult(
            effect=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
            relative_reduction=float("nan"), passed=False, reason=reason,
            method="paired_seed_cluster", converged=False, **counts,
        )

    if n < 2:
        return refuse(
            f"only {n} seed(s): the interval is taken across seeds, so there is no "
            "replication to estimate it from. Failing closed -- an unestimated "
            "effect is not a null one"
        )

    effect = float(per_seed.mean())
    spread = float(per_seed.std(ddof=1))
    if not np.isfinite(spread) or spread == 0.0:
        return refuse(
            f"the across-seed spread is {spread!r}, so the seed-level interval "
            "cannot be formed. Failing closed: switching the replication unit from "
            "seeds to episodes because of the observed data would choose the "
            "inference after seeing it (Sol, delta 45)"
        )

    se = spread / np.sqrt(n)
    half = float(stats.t.ppf(1 - (1 - CONFIDENCE) / 2, n - 1)) * se
    low, high = effect - half, effect + half
    passed, relative, reason = _verdict(effect, low, high, unrepaired_mean)
    return AcceptanceResult(
        effect=effect, ci_low=low, ci_high=high,
        relative_reduction=relative, passed=passed, reason=reason,
        method="paired_seed_cluster", converged=True, **counts,
    )


def clopper_pearson(k: int, n: int, confidence: float = CONFIDENCE) -> tuple[float, float]:
    """Exact binomial interval for ``k`` acceptances in ``n`` permutations.

    Sol's ruling on delta 42: calibration must **not** be defined as the raw
    point estimate landing under nominal. At 200 permutations a point estimate
    carries roughly ±3 points of Monte-Carlo noise, so "0% observed" and "5.5%
    observed" are both consistent with a correctly sized test — and reading
    either as a measurement is the D-042 shape, a bound reported as a number.
    """
    alpha = 1 - confidence
    low = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    high = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return low, high


@dataclass(frozen=True)
class PermutationNull:
    """How often the acceptance test accepts when the labels carry no information.

    **Two rates, because they answer different questions** (Sol, delta 42). The
    *statistical-only* rate uses conditions 1–2 and is the one that establishes
    the mixed model's interval is correctly sized under the real dependence
    structure. The *full* rate adds the 20% practical floor, which supplies
    conservatism on top. Reporting the full rate alone credits the model with a
    calibration the floor was providing.
    """

    n_permutations: int
    #: Conditions 1-2 only: negative effect with a 95% interval excluding zero.
    n_accepted_statistical: int
    statistical_rate: float
    statistical_ci: tuple[float, float]
    #: All three registered conditions, the floor included.
    n_accepted_full: int
    full_rate: float
    full_ci: tuple[float, float]
    nominal: float
    #: D-085's frozen criterion, both parts.
    statistical_contains_nominal: bool
    full_upper_within_nominal: bool
    calibrated: bool
    reason: str
    effects: tuple[float, ...] = ()

    def as_row(self) -> dict:
        return {
            "n_permutations": self.n_permutations,
            "n_accepted_statistical": self.n_accepted_statistical,
            "statistical_rate": self.statistical_rate,
            "statistical_ci_low": self.statistical_ci[0],
            "statistical_ci_high": self.statistical_ci[1],
            "n_accepted_full": self.n_accepted_full,
            "full_rate": self.full_rate,
            "full_ci_low": self.full_ci[0],
            "full_ci_high": self.full_ci[1],
            "nominal": self.nominal,
            "statistical_contains_nominal": self.statistical_contains_nominal,
            "full_upper_within_nominal": self.full_upper_within_nominal,
            "calibrated": self.calibrated,
            "reason": self.reason,
        }

    def summary(self) -> str:
        return (
            f"PERMUTATION NULL over {self.n_permutations} paired relabellings "
            f"({'CALIBRATED' if self.calibrated else 'NOT CALIBRATED'})\n"
            f"  statistical only (conditions 1-2): "
            f"{self.n_accepted_statistical}/{self.n_permutations} = "
            f"{self.statistical_rate:.3%}, exact 95% CI "
            f"[{self.statistical_ci[0]:.3%}, {self.statistical_ci[1]:.3%}] "
            f"-- must CONTAIN {self.nominal:.0%}: "
            f"{'yes' if self.statistical_contains_nominal else 'NO'}\n"
            f"  full three conditions:             "
            f"{self.n_accepted_full}/{self.n_permutations} = {self.full_rate:.3%}, "
            f"exact 95% CI [{self.full_ci[0]:.3%}, {self.full_ci[1]:.3%}] "
            f"-- upper must NOT EXCEED {self.nominal:.0%}: "
            f"{'yes' if self.full_upper_within_nominal else 'NO'}\n"
            f"  {self.reason}"
        )


def _validate_matched_design(seeds: np.ndarray, repair: np.ndarray) -> np.ndarray:
    """Every seed must carry exactly one baseline run and one repaired run.

    The permutation is only a null for the design that was actually run. A seed
    missing an arm cannot be relabelled without inventing or destroying a run,
    so it is refused rather than silently carried.
    """
    labels = np.unique(repair)
    if not np.array_equal(labels, np.array([0, 1])):
        raise ValueError(
            f"repair must carry exactly the two labels 0 and 1, got {labels.tolist()}. "
            "Comparisons involving different repair types are permuted separately "
            "against baseline, one call each (Sol, delta 42)"
        )
    unique_seeds = np.unique(seeds)
    for s in unique_seeds:
        present = np.unique(repair[seeds == s])
        if not np.array_equal(present, np.array([0, 1])):
            raise ValueError(
                f"seed {s} carries repair labels {present.tolist()}, not both arms. "
                "The acceptance test is paired within seed, so the null must permute "
                "within seed, and a seed with one arm has nothing to swap"
            )
    return unique_seeds


def permutation_null(
    errors,
    repair,
    seed,
    episode,
    transition,
    *,
    n_permutations: int = 200,
    nominal: float = DIRECTIONAL_NOMINAL,
    rng: np.random.Generator | None = None,
) -> PermutationNull:
    """Run the acceptance test on paired within-seed relabellings (S§W5 Wed).

    **The null must preserve the matched design, not merely the run boundaries.**
    The first implementation permuted labels globally across all (seed, arm)
    runs, preserving only the total number of repaired runs. That keeps every
    run intact -- necessary, and what P§7.3 says about never permuting across
    episodes or transitions -- but it is not sufficient: measured on the
    registered 20-seed shape, **48.4%** of seeds came out with two baseline or
    two repaired labels, against 48.72% analytic, and **every** permutation
    corrupted at least one seed. A null drawn from a design the study never ran
    cannot calibrate the test that ran (Sol's ruling on delta 42; D-085).

    So the operation is: independently for each seed, **retain or swap** that
    seed's two labels. Every transition in a run moves together, and every seed
    keeps exactly one baseline and one repaired run.

    Args:
        n_permutations: how many relabellings to draw. The frozen criterion in
            D-085 is stated at 200.
        nominal: the size the test is meant to have. Defaults to
            ``DIRECTIONAL_NOMINAL`` = 0.025 -- half the two-sided level, because
            the acceptance rule only fires in one direction (Sol's correction to
            D-085).
    """
    rng = rng or np.random.default_rng(0)
    data = _frame(errors, repair, seed, episode, transition)
    seeds = data["seed"].to_numpy()
    labels = data["repair"].to_numpy()
    unique_seeds = _validate_matched_design(seeds, labels)

    # Row -> index of its seed, so a per-seed decision applies to every
    # transition of both that seed's runs at once.
    seed_position = {s: i for i, s in enumerate(unique_seeds)}
    row_seed = np.array([seed_position[s] for s in seeds])
    scoped_episode = [e.split("::", 1)[1] for e in data["episode"]]
    scoped_pair = [p.rsplit("::", 1)[1] for p in data["pair"]]
    error_values = data["error"].to_numpy()

    stat_accepted, full_accepted, effects = 0, 0, []
    for _ in range(n_permutations):
        swap = rng.random(len(unique_seeds)) < 0.5
        permuted = np.where(swap[row_seed], 1 - labels, labels)
        result = acceptance_test(
            error_values, permuted, seeds, scoped_episode, scoped_pair
        )
        effects.append(result.effect)
        # Conditions 1-2 alone, read off the same fitted interval the full rule
        # uses -- not a second fit, so the two rates cannot disagree by method.
        if result.effect < 0 and result.ci_high < 0:
            stat_accepted += 1
        full_accepted += bool(result.passed)

    stat_rate = stat_accepted / n_permutations
    full_rate = full_accepted / n_permutations
    stat_ci = clopper_pearson(stat_accepted, n_permutations)
    full_ci = clopper_pearson(full_accepted, n_permutations)

    contains = stat_ci[0] <= nominal <= stat_ci[1]
    within = full_ci[1] <= nominal
    calibrated = contains and within
    return PermutationNull(
        n_permutations=n_permutations,
        n_accepted_statistical=stat_accepted,
        statistical_rate=stat_rate,
        statistical_ci=stat_ci,
        n_accepted_full=full_accepted,
        full_rate=full_rate,
        full_ci=full_ci,
        nominal=nominal,
        statistical_contains_nominal=contains,
        full_upper_within_nominal=within,
        calibrated=calibrated,
        reason=(
            "Calibrated: the statistical-only interval covers nominal and the "
            "full rule's upper bound stays within it (D-085)."
            if calibrated
            else "NOT CALIBRATED against D-085: "
            + "; ".join(
                filter(None, [
                    None if contains else
                    f"the statistical-only interval "
                    f"[{stat_ci[0]:.3%}, {stat_ci[1]:.3%}] does not contain "
                    f"{nominal:.0%}, so the mixed model's interval is the wrong size",
                    None if within else
                    f"the full rule's upper bound {full_ci[1]:.3%} exceeds "
                    f"{nominal:.0%}",
                ])
            )
        ),
        effects=tuple(float(e) for e in effects),
    )
