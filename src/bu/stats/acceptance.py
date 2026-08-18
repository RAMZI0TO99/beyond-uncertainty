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
                # Episode within seed, as a variance component. The seed enters
                # through `groups`; this nests episodes inside it.
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


@dataclass(frozen=True)
class PermutationNull:
    """How often the acceptance test accepts when the labels carry no information."""

    false_positive_rate: float
    n_permutations: int
    n_accepted: int
    nominal: float
    calibrated: bool
    reason: str
    #: The permuted effects, so the null's shape is inspectable rather than
    #: summarised into a single rate.
    effects: tuple[float, ...]

    def as_row(self) -> dict:
        return {
            "false_positive_rate": self.false_positive_rate,
            "n_permutations": self.n_permutations,
            "n_accepted": self.n_accepted,
            "nominal": self.nominal,
            "calibrated": self.calibrated,
            "reason": self.reason,
        }

    def summary(self) -> str:
        return (
            f"PERMUTATION NULL: {self.false_positive_rate:.3%} acceptance over "
            f"{self.n_permutations} permutations "
            f"({'CALIBRATED' if self.calibrated else 'ABOVE NOMINAL'})\n  {self.reason}"
        )


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
    """Run the acceptance test on permuted repair labels (P§7.3, S§W5 Wed).

    **Where the permutation happens is the whole point.** P§7.3: labels are
    permuted "at the level of the repair assignment within condition, never
    across episodes or transitions, which would destroy the dependence
    structure". A transition-level shuffle would break the within-episode and
    within-seed correlation the model exists to account for, and the resulting
    null would be far too narrow — the test would look better calibrated than it
    is, which is the opposite of what a calibration check is for.

    So the unit of permutation is the **run**: every transition belonging to one
    (seed, arm) block moves together, and the number of repaired runs is
    preserved. That leaves the seed and episode structure exactly as observed
    and destroys only the association between the label and the outcome.

    Args:
        n_permutations: how many relabellings to draw.
        nominal: the rate the test is allowed to accept at. Defaults to
            ``1 - CONFIDENCE`` = 0.05. Note the acceptance rule is *three*
            conditions, not one, so a well-behaved test should land **below**
            this rather than at it.
    """
    rng = rng or np.random.default_rng(0)
    data = _frame(errors, repair, seed, episode)
    # A run is one (seed, arm) block. Transitions never move between runs.
    run_key = list(zip(data["seed"], data["repair"]))
    runs = sorted(set(run_key), key=repr)
    labels = np.array([r[1] for r in runs])
    index = {run: i for i, run in enumerate(runs)}
    positions = np.array([index[k] for k in run_key])

    accepted, effects = 0, []
    for _ in range(n_permutations):
        permuted_runs = rng.permutation(labels)
        result = acceptance_test(
            data["error"].to_numpy(),
            permuted_runs[positions],
            data["seed"].to_numpy(),
            [e.split("::", 1)[1] for e in data["episode"]],
        )
        effects.append(result.effect)
        accepted += bool(result.passed)

    rate = accepted / n_permutations
    calibrated = rate <= nominal
    return PermutationNull(
        false_positive_rate=rate,
        n_permutations=n_permutations,
        n_accepted=accepted,
        nominal=nominal,
        calibrated=calibrated,
        reason=(
            f"{accepted} of {n_permutations} permuted relabellings were accepted, "
            f"a rate of {rate:.3%} against a nominal {nominal:.1%}. "
            + (
                "The test is calibrated on this data."
                if calibrated
                else "ABOVE NOMINAL: the acceptance test is anti-conservative here "
                "and must be revised before it decides a repair (S§W5 Wed)."
            )
        ),
        effects=tuple(float(e) for e in effects),
    )
