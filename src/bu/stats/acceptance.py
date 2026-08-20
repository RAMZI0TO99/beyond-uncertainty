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

**Why a mixed model rather than a t-test on five numbers.** Step 4 of the
protocol evaluates every repair on the *same recorded failure set* as the
unrepaired condition, so the comparison is paired per transition within seed.
Collapsing to per-seed means throws that structure away. The model is therefore
per-transition error with a fixed effect for repair and **random intercepts for
seed and for episode within seed** — transitions inside an episode are not
independent, and neither are episodes inside a seed.

**The fallback is part of the specification, not a rescue.** Mixed models on
thousands of correlated rows do not always converge, and a test that silently
reports whatever the optimiser last held would be worse than one that says so.
When the full model fails, the data are collapsed to **episode means** and the
same three conditions are applied to a seed-random-intercept model on those. The
result records which path ran, because "passed under the fallback" and "passed
under the registered model" are different claims.
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


@dataclass(frozen=True)
class AcceptanceResult:
    """A repair's verdict, with everything needed to report it honestly."""

    effect: float
    ci_low: float
    ci_high: float
    #: Reduction relative to the unrepaired mean. Positive means error fell.
    relative_reduction: float
    passed: bool
    reason: str
    #: ``"mixedlm"`` or ``"episode_mean_fallback"`` — different claims.
    method: str
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
            f"{'' if self.converged else ', DID NOT CONVERGE'})\n"
            f"  fixed effect {self.effect:+.6f}  95% CI "
            f"[{self.ci_low:+.6f}, {self.ci_high:+.6f}]\n"
            f"  relative reduction {self.relative_reduction:+.1%} against a "
            f"{K.MIN_PRACTICAL_EFFECT:.0%} minimum\n"
            f"  {self.reason}\n"
            f"  {self.n_transitions} transitions, {self.n_episodes} episodes, "
            f"{self.n_seeds} seeds"
        )


def _frame(errors, repair, seed, episode) -> pd.DataFrame:
    errors = np.asarray(errors, dtype=float)
    repair = np.asarray(repair)
    seed = np.asarray(seed)
    episode = np.asarray(episode)
    lengths = {len(errors), len(repair), len(seed), len(episode)}
    if len(lengths) != 1:
        raise ValueError(
            f"errors, repair, seed and episode must be the same length; got "
            f"{[len(errors), len(repair), len(seed), len(episode)]}"
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
    return pd.DataFrame(
        {
            "error": errors,
            "repair": repair.astype(float),
            "seed": seed,
            # Episode identity is only meaningful *within* a seed (D-052): two
            # seeds both have an episode 0, and they are different episodes.
            "episode": [f"{s}::{e}" for s, e in zip(seed, episode)],
        }
    )


def _verdict(effect, ci_low, ci_high, unrepaired_mean) -> tuple[bool, float, str]:
    relative = -effect / unrepaired_mean if unrepaired_mean > 0 else float("nan")
    negative = effect < 0
    excludes_zero = ci_high < 0
    practical = relative >= K.MIN_PRACTICAL_EFFECT
    if negative and excludes_zero and practical:
        return True, relative, (
            "all three conditions met: negative fixed effect, 95% interval "
            f"excluding zero, and a {relative:.1%} reduction clearing the "
            f"{K.MIN_PRACTICAL_EFFECT:.0%} minimum practical effect"
        )
    failures = []
    if not negative:
        failures.append("the fixed effect is not negative (error did not fall)")
    if not excludes_zero:
        failures.append("the 95% interval includes zero")
    if not practical:
        failures.append(
            f"the {relative:.1%} reduction does not clear the "
            f"{K.MIN_PRACTICAL_EFFECT:.0%} minimum practical effect"
        )
    return False, relative, "; ".join(failures)


def acceptance_test(
    errors, repair, seed, episode, *, allow_fallback: bool = True
) -> AcceptanceResult:
    """Run the registered acceptance test on per-transition error (P§7.3).

    Args:
        errors: per-transition error, unrepaired and repaired rows together.
        repair: 0/1 per transition — 1 for the repaired arm.
        seed: seed id per transition.
        episode: episode id per transition, interpreted **within** its seed.
        allow_fallback: if the mixed model does not converge, collapse to
            episode means and apply the same three conditions there. Recorded on
            the result either way; set ``False`` to make non-convergence an error
            rather than a different test.
    """
    import statsmodels.formula.api as smf

    data = _frame(errors, repair, seed, episode)
    unrepaired_mean = float(data.loc[data.repair == 0, "error"].mean())
    counts = dict(
        n_transitions=len(data),
        n_seeds=int(data.seed.nunique()),
        n_episodes=int(data.episode.nunique()),
        unrepaired_mean=unrepaired_mean,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = smf.mixedlm(
                "error ~ repair",
                data=data,
                groups=data["seed"],
                # The seed random intercept must be REQUESTED explicitly. Found
                # by audit (D-082): passing vc_formula without re_formula makes
                # statsmodels drop its default group intercept, so the model had
                # only the episode component and no seed intercept -- contrary to
                # P§7.3 and to this function's own docstring. CI-neutral for the
                # paired repair contrast (the seed effect cancels within episode,
                # verified identical), but the model must still be the registered
                # one, not one that happens to give the same number.
                re_formula="1",
                # Episode within seed, as a variance component nested in `groups`.
                vc_formula={"episode": "0 + C(episode)"},
            )
            fit = model.fit(reml=True, method="lbfgs")
            converged = bool(getattr(fit, "converged", True))
        except Exception:  # noqa: BLE001 -- reported as non-convergence, never swallowed
            fit, converged = None, False

    if fit is not None and converged:
        effect = float(fit.fe_params["repair"])
        low, high = fit.conf_int(alpha=1 - CONFIDENCE).loc["repair"]
        passed, relative, reason = _verdict(effect, float(low), float(high), unrepaired_mean)
        return AcceptanceResult(
            effect=effect, ci_low=float(low), ci_high=float(high),
            relative_reduction=relative, passed=passed, reason=reason,
            method="mixedlm", converged=True, **counts,
        )

    if not allow_fallback:
        raise RuntimeError(
            "the mixed model did not converge and allow_fallback is False. The "
            "episode-mean fallback is part of P§7.3's specification, but it is a "
            "different test and the caller has asked not to substitute it silently"
        )
    return _episode_mean_fallback(data, counts, unrepaired_mean)


def _episode_mean_fallback(data, counts, unrepaired_mean) -> AcceptanceResult:
    """P§7.3's fallback: collapse to episode means, keep the seed random intercept."""
    import statsmodels.formula.api as smf

    means = (
        data.groupby(["seed", "episode", "repair"], as_index=False)["error"].mean()
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            fit = smf.mixedlm("error ~ repair", data=means, groups=means["seed"]).fit(
                reml=True, method="lbfgs"
            )
            converged = bool(getattr(fit, "converged", True))
            effect = float(fit.fe_params["repair"])
            low, high = fit.conf_int(alpha=1 - CONFIDENCE).loc["repair"]
        except Exception:  # noqa: BLE001
            converged, effect, low, high = False, float("nan"), float("nan"), float("nan")

    if not converged or not np.isfinite(effect):
        return AcceptanceResult(
            effect=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
            relative_reduction=float("nan"), passed=False,
            reason=(
                "neither the registered mixed model nor the episode-mean fallback "
                "converged, so there is no effect to accept. Failing closed: an "
                "unestimated effect is not a null one"
            ),
            method="episode_mean_fallback", converged=False, **counts,
        )
    passed, relative, reason = _verdict(effect, float(low), float(high), unrepaired_mean)
    return AcceptanceResult(
        effect=effect, ci_low=float(low), ci_high=float(high),
        relative_reduction=relative, passed=passed,
        reason=f"{reason} (episode-mean fallback: the registered model did not converge)",
        method="episode_mean_fallback", converged=True, **counts,
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
    *,
    n_permutations: int = 200,
    nominal: float = 1 - CONFIDENCE,
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
            ``1 - CONFIDENCE`` = 0.05.
    """
    rng = rng or np.random.default_rng(0)
    data = _frame(errors, repair, seed, episode)
    seeds = data["seed"].to_numpy()
    labels = data["repair"].to_numpy()
    unique_seeds = _validate_matched_design(seeds, labels)

    # Row -> index of its seed, so a per-seed decision applies to every
    # transition of both that seed's runs at once.
    seed_position = {s: i for i, s in enumerate(unique_seeds)}
    row_seed = np.array([seed_position[s] for s in seeds])
    scoped_episode = [e.split("::", 1)[1] for e in data["episode"]]
    error_values = data["error"].to_numpy()

    stat_accepted, full_accepted, effects = 0, 0, []
    for _ in range(n_permutations):
        swap = rng.random(len(unique_seeds)) < 0.5
        permuted = np.where(swap[row_seed], 1 - labels, labels)
        result = acceptance_test(error_values, permuted, seeds, scoped_episode)
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
