"""The repair acceptance test and its permutation null (P§7.3, S§W5 Tue–Wed).

The acceptance rule is three conditions, not one: a negative fixed effect, a 95%
interval excluding zero, **and** a reduction clearing the 20% minimum practical
effect. Plan v1.0's "two across-seed standard deviations over five seeds" was
withdrawn because at n = 5 the sample SD moves with the noise it is meant to
control, so the tests here check each condition can independently refuse.

Everything runs on **synthetic data with a known truth**, which is what S§W5
Tue's "done when" asks for — no run records, no compute.
"""

from __future__ import annotations

import numpy as np
import pytest

from bu import constants as K
from bu.stats.acceptance import (
    CONFIDENCE, acceptance_test, permutation_null,
)

BASE = 0.10


def synthetic(reduction=0.0, *, n_seeds=20, n_episodes=8, n_transitions=10,
              seed_sd=0.02, episode_sd=0.01, noise=0.01, rng=None):
    """Paired data: the same failure set evaluated under both arms (P§7.2 step 4)."""
    rng = rng or np.random.default_rng(0)
    errors, repair, seeds, episodes, transitions = [], [], [], [], []
    for s in range(n_seeds):
        s_effect = rng.normal(0, seed_sd)
        for ep in range(n_episodes):
            e_effect = rng.normal(0, episode_sd)
            for step in range(n_transitions):
                base = BASE + s_effect + e_effect + rng.normal(0, noise)
                for arm in (0, 1):
                    value = base * (1 - reduction) if arm else base
                    errors.append(value + (rng.normal(0, noise) if arm else 0.0))
                    repair.append(arm)
                    seeds.append(s)
                    episodes.append(ep)
                    transitions.append(step)
    return (np.array(errors), np.array(repair), np.array(seeds),
            np.array(episodes), np.array(transitions))


def synthetic_paired(pair_strength=1.0, *, n_seeds=20, n_episodes=8, n_transitions=10,
                     noise=0.01, rng=None):
    """Like `synthetic`, but with the arms' shared transition difficulty tunable.

    `pair_strength=1.0` is the original generator: the arms share the transition
    draw exactly. `0.0` gives them independent draws. Sol's point is that the
    near-perfect case is a valid stress test but NOT an estimate of real-data
    pairing, so calibration has to hold across the range.
    """
    rng = rng or np.random.default_rng(0)
    E, R, S, P, T = [], [], [], [], []
    for s in range(n_seeds):
        se = rng.normal(0, 0.02)
        for ep in range(n_episodes):
            ee = rng.normal(0, 0.01)
            for st in range(n_transitions):
                shared = rng.normal(0, noise)
                for arm in (0, 1):
                    own = rng.normal(0, noise)
                    tn = pair_strength * shared + np.sqrt(max(0.0, 1 - pair_strength**2)) * own
                    E.append(BASE + se + ee + tn + (rng.normal(0, noise) if arm else 0.0))
                    R.append(arm); S.append(s); P.append(ep); T.append(st)
    return (np.array(E), np.array(R), np.array(S), np.array(P), np.array(T))


# --- the three conditions, each able to refuse on its own -------------------


def test_a_real_repair_is_accepted_and_its_size_recovered():
    result = acceptance_test(*synthetic(reduction=0.35, rng=np.random.default_rng(0)))
    assert result.passed
    assert result.method == "paired_seed_cluster"
    assert result.effect < 0
    assert result.ci_high < 0
    assert result.relative_reduction == pytest.approx(0.35, abs=0.05), (
        "the estimated reduction does not recover the simulated one; the model is "
        "not measuring the quantity the acceptance rule is written about"
    )


def test_no_effect_is_rejected():
    result = acceptance_test(*synthetic(reduction=0.0, rng=np.random.default_rng(1)))
    assert not result.passed
    assert "interval includes zero" in result.reason or "not negative" in result.reason


def test_a_real_but_negligible_effect_is_rejected_by_the_practical_floor():
    """Condition three exists so a large sample cannot manufacture a success.

    A 5% reduction over 3,200 transitions is statistically unmissable — the
    interval excludes zero comfortably — and it is still refused, because P§7.3
    fixes the minimum practical effect at 20% *before* data collection.
    """
    result = acceptance_test(*synthetic(reduction=0.05, rng=np.random.default_rng(2)))
    assert result.effect < 0 and result.ci_high < 0, "should be statistically clear"
    assert not result.passed
    assert "minimum practical effect" in result.reason
    assert result.relative_reduction < K.MIN_PRACTICAL_EFFECT


def test_an_effect_in_the_wrong_direction_is_rejected():
    """A repair that makes things worse must not pass on interval width alone."""
    result = acceptance_test(*synthetic(reduction=-0.35, rng=np.random.default_rng(3)))
    assert not result.passed
    assert "not negative" in result.reason


def test_the_three_conditions_are_all_required():
    """No two of them suffice — each test above pins one, this pins the rule."""
    accepted = acceptance_test(*synthetic(reduction=0.35, rng=np.random.default_rng(0)))
    assert accepted.passed
    row = accepted.as_row()
    assert row["min_practical_effect"] == K.MIN_PRACTICAL_EFFECT
    assert row["confidence"] == CONFIDENCE == 0.95


# --- the fallback is a different claim, and says so -------------------------


def _constant_difference_data(n_seeds=6, n_ep=3, n_tr=4):
    """Every pair identical, so the across-seed spread is EXACTLY zero.

    Built from two literal values so the differences are bitwise identical and
    the standard deviation is truly 0 rather than merely tiny -- an approximately
    zero spread would take the ordinary path and this would test nothing.
    """
    e, r, s, ep, tr = [], [], [], [], []
    for seed in range(n_seeds):
        for episode in range(n_ep):
            for step in range(n_tr):
                for arm, value in ((0, 1.0), (1, 0.99)):
                    e.append(value); r.append(arm)
                    s.append(seed); ep.append(episode); tr.append(step)
    return (np.array(e), np.array(r), np.array(s), np.array(ep), np.array(tr))


def test_there_is_no_fallback_to_fall_back_to():
    """Sol, delta 45: remove the episode-level fallback from registered acceptance.

    The old fallback existed because an optimiser could fail. This analysis has
    none, and switching the replication unit from seeds to episodes because of
    the observed data would be choosing the inference after seeing it.
    """
    from bu.stats import acceptance as A

    assert not hasattr(A, "_paired_difference_fallback")
    assert not hasattr(A, "_episode_mean_fallback")


def test_a_zero_seed_spread_FAILS_CLOSED_rather_than_switching_analysis():
    """The condition that used to trigger the fallback now refuses outright."""
    result = acceptance_test(*_constant_difference_data())
    assert result.method == "paired_seed_cluster"
    assert not result.passed
    assert not result.converged
    assert np.isnan(result.effect)
    assert "across-seed spread" in result.reason
    assert "seeing it" in result.reason


def test_a_single_seed_fails_closed():
    e, r, s, ep, tr = _constant_difference_data(n_seeds=1)
    result = acceptance_test(e, r, s, ep, tr)
    assert not result.passed and np.isnan(result.effect)
    assert "no replication" in result.reason

def test_mismatched_lengths_are_refused():
    errors, repair, seeds, episodes, steps = synthetic(rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match="same length"):
        acceptance_test(errors[:-1], repair, seeds, episodes, steps)


def test_a_single_arm_is_refused():
    """A one-armed test would report the intercept as an effect."""
    errors, repair, seeds, episodes, steps = synthetic(rng=np.random.default_rng(0))
    keep = repair == 0
    with pytest.raises(ValueError, match="only one value"):
        acceptance_test(errors[keep], repair[keep], seeds[keep], episodes[keep], steps[keep])


def test_a_non_binary_repair_indicator_is_refused():
    errors, repair, seeds, episodes, steps = synthetic(rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match="0/1 indicator"):
        acceptance_test(errors, repair * 2, seeds, episodes, steps)


def test_empty_input_is_refused():
    with pytest.raises(ValueError, match="no transitions"):
        acceptance_test([], [], [], [], [])


def test_episode_identity_is_scoped_to_its_seed():
    """Two seeds both have an episode 0, and they are different episodes (D-052)."""
    from bu.stats import acceptance as A

    frame = A._frame([1.0, 2.0, 3.0, 4.0], [0, 1, 0, 1], [0, 0, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0])
    assert frame["episode"].nunique() == 2, (
        "episode 0 of seed 0 and episode 0 of seed 1 collapsed into one group; the "
        "random intercept would pool transitions from different seeds"
    )


# --- the permutation null (S§W5 Wed) ---------------------------------------


def _permuted_labels(data, *, n, rng_seed=0):
    """Capture the label vectors `permutation_null` ACTUALLY passes downstream.

    The previous version of this test reimplemented the permutation inline and
    asserted on its own copy, so it could not fail on the real function -- and
    duly did not, while `permutation_null` was breaking the matched design in
    every single draw. It enshrined the defective mechanism as the tested
    behaviour. Monkeypatching the consumer records the real path instead
    (D-055, D-057; Sol's ruling on delta 42).
    """
    from bu.stats import acceptance as A

    seen = []
    real = A.acceptance_test

    def spy(errors, repair, seed, episode, transition, **kw):
        seen.append(np.asarray(repair).copy())
        return real(errors, repair, seed, episode, transition, **kw)

    A.acceptance_test = spy
    try:
        A.permutation_null(*data, n_permutations=n, rng=np.random.default_rng(rng_seed))
    finally:
        A.acceptance_test = real
    assert len(seen) == n
    return seen


def test_the_permutation_moves_whole_runs_never_transitions():
    """P§7.3: never permute across episodes or transitions.

    A transition-level shuffle would break the within-episode and within-seed
    correlation the model exists to account for, and the resulting null would be
    far too narrow -- the test would look better calibrated than it is.
    """
    from bu.stats import acceptance as A

    data = synthetic(rng=np.random.default_rng(0))
    frame = A._frame(*data)
    run_key = np.array([f"{s}|{r}" for s, r in zip(frame["seed"], frame["repair"])])

    for permuted in _permuted_labels(data, n=20):
        for run in np.unique(run_key):
            block = run_key == run
            assert len(np.unique(permuted[block])) == 1, (
                f"run {run} was split by the permutation: transitions of one "
                "(seed, arm) block received different labels"
            )


def test_every_permuted_seed_keeps_one_baseline_and_one_repaired():
    """Sol's required regression (delta 42). The null must preserve the design.

    Keeping runs intact is necessary but NOT sufficient. The withdrawn
    implementation permuted labels globally, preserving only the total number of
    repaired runs; measured on the registered 20-seed shape, 48.4% of seeds came
    out with two baseline or two repaired labels (48.72% analytic) and EVERY
    permutation corrupted at least one seed. A null drawn from a design the
    study never ran cannot calibrate the test that ran.
    """
    from bu.stats import acceptance as A

    data = synthetic(rng=np.random.default_rng(0))
    frame = A._frame(*data)
    seeds = frame["seed"].to_numpy()

    for permuted in _permuted_labels(data, n=50):
        for s in np.unique(seeds):
            rows = seeds == s
            arms = {
                lbl: len(np.unique(frame["episode"].to_numpy()[rows & (permuted == lbl)]))
                for lbl in (0, 1)
            }
            present = np.unique(permuted[rows])
            assert np.array_equal(present, np.array([0, 1])), (
                f"seed {s} came out with labels {present.tolist()} -- it must "
                "retain exactly one baseline run and one repaired run"
            )
            assert arms[0] and arms[1], f"seed {s} lost an arm's episodes"


def test_the_global_permutation_would_fail_this_regression():
    """Could the regression above actually fail? Yes -- on the withdrawn method.

    Asserting a property without showing it is refutable is how three earlier
    tests in this project passed while asserting nothing (D-055, D-057). This
    reproduces the withdrawn global permutation and shows it breaks the very
    invariant the corrected null must hold, so the regression is load-bearing
    rather than decorative.
    """
    from bu.stats import acceptance as A

    data = synthetic(rng=np.random.default_rng(0))
    frame = A._frame(*data)
    seeds = frame["seed"].to_numpy()
    labels = frame["repair"].to_numpy()

    run_key = [f"{s}|{r}" for s, r in zip(seeds, labels)]
    runs = sorted(set(run_key))
    run_labels = np.array([int(float(r.split("|")[1])) for r in runs])
    position = {run: i for i, run in enumerate(runs)}
    rows = np.array([position[k] for k in run_key])

    rng = np.random.default_rng(0)
    broken = 0
    for _ in range(50):
        permuted = rng.permutation(run_labels)[rows]
        if any(
            not np.array_equal(np.unique(permuted[seeds == s]), np.array([0, 1]))
            for s in np.unique(seeds)
        ):
            broken += 1
    assert broken == 50, (
        f"the withdrawn global permutation corrupted only {broken}/50 draws; it "
        "corrupted every one when measured, so this reproduction is wrong"
    )


def test_the_permutation_null_refuses_a_seed_missing_an_arm():
    """A seed with one arm has nothing to swap, so it is refused, not carried."""
    errors, repair, seeds, episodes, steps = synthetic(rng=np.random.default_rng(0))
    # Strip the repaired arm from one seed.
    keep = ~((np.asarray(seeds) == np.unique(seeds)[0]) & (np.asarray(repair) == 1))
    # The pairing validator fires first and is the more specific refusal:
    # stripping an arm from a seed also destroys that seed's pairs.
    with pytest.raises(ValueError, match="exactly one baseline and one repaired"):
        permutation_null(
            np.asarray(errors)[keep], np.asarray(repair)[keep],
            np.asarray(seeds)[keep], np.asarray(episodes)[keep],
            np.asarray(steps)[keep], n_permutations=5,
        )


def test_the_permutation_null_refuses_more_than_two_arms():
    """Different repair types are permuted separately against baseline."""
    errors, repair, seeds, episodes, steps = synthetic(rng=np.random.default_rng(0))
    repair = np.asarray(repair).copy()
    repair[:10] = 2
    # `_frame` refuses a non-0/1 indicator before the matched-design check
    # is reached; both guards exist, and this pins the one that fires.
    with pytest.raises(ValueError, match="0/1 indicator"):
        permutation_null(errors, repair, seeds, episodes, steps, n_permutations=5)


def test_the_permutation_null_meets_the_frozen_criterion():
    """D-085's criterion, at the 200 permutations it is frozen at.

    The count is not incidental. The withdrawn test asserted calibration at 60
    permutations, where an exact interval CANNOT support the claim: with zero
    acceptances the Clopper-Pearson upper bound is 5.96%, so the full rule's
    "upper bound within 5%" is unreachable at n=60 even for a perfectly sized
    test. Reporting a point estimate hid that; the interval exposes it. This is
    Sol's Monte-Carlo-uncertainty ruling made mechanical.
    """
    data = synthetic(reduction=0.0, rng=np.random.default_rng(1))
    result = permutation_null(*data, n_permutations=200, rng=np.random.default_rng(3))

    assert result.statistical_contains_nominal, (
        f"statistical-only CI {result.statistical_ci} must contain 0.05: "
        f"{result.reason}"
    )
    assert result.full_upper_within_nominal, (
        f"full-rule CI upper {result.full_ci[1]:.4f} must not exceed 0.05: "
        f"{result.reason}"
    )
    assert result.calibrated
    # D-085's admissible counts at the CORRECTED 2.5% directional nominal,
    # computed in advance from the exact binomial. The old [4, 16] / [0, 3]
    # belonged to a 5% target that the one-directional acceptance rule never had.
    assert 1 <= result.n_accepted_statistical <= 10
    assert result.n_accepted_full == 0
    assert np.std(result.effects) > 0, (
        "the permuted effects are identical, so the permutation is not permuting "
        "anything and the calibration check is vacuous"
    )


def test_the_nominal_rate_is_directional_and_half_the_two_sided_level():
    """Sol's correction to its own D-085 rule, pinned.

    Acceptance needs a negative effect AND a two-sided 95% interval below zero.
    Under the null that fires 2.5% of the time, not 5% -- the two-sided level is
    split between directions and only one of them accepts. Calibrating against
    5% demands the test reject twice as often as its own rule permits.
    """
    from bu.stats.acceptance import CONFIDENCE, DIRECTIONAL_NOMINAL

    assert DIRECTIONAL_NOMINAL == pytest.approx((1 - CONFIDENCE) / 2) == 0.025


def test_the_frozen_admissible_counts_follow_from_the_exact_binomial():
    """D-085's integers are recomputed here rather than trusted as written."""
    from bu.stats.acceptance import DIRECTIONAL_NOMINAL as NOM, clopper_pearson

    contains = [k for k in range(201)
                if clopper_pearson(k, 200)[0] <= NOM <= clopper_pearson(k, 200)[1]]
    within = [k for k in range(201) if clopper_pearson(k, 200)[1] <= NOM]
    assert (min(contains), max(contains)) == (1, 10)
    assert within == [0]


def test_sixty_permutations_cannot_satisfy_the_full_rule_at_any_count():
    """Why D-085 freezes n=200: the old n=60 test was unsatisfiable, not lucky."""
    from bu.stats.acceptance import DIRECTIONAL_NOMINAL as NOM, clopper_pearson

    assert clopper_pearson(0, 60)[1] > NOM
    assert clopper_pearson(0, 200)[1] <= NOM


def test_the_models_interval_matches_the_permutation_spread():
    """A 0% headline FPR could hide a badly sized interval. It does not here.

    Estimating the two-condition rate would need many hundreds of permutations
    to tell 5% from 0% — an earlier version of this test asserted it at 60 and
    was flaky for exactly that reason. The underlying property is cheaper and
    more direct: the mixed model's standard error should match the spread of the
    permutation null. If the model's interval were too narrow the test would be
    anti-conservative; too wide and the calibration check is vacuous.
    """
    data = synthetic(reduction=0.0, rng=np.random.default_rng(1))
    observed = acceptance_test(*data)
    model_se = (observed.ci_high - observed.ci_low) / (2 * 1.959963985)

    null = permutation_null(*data, n_permutations=60, rng=np.random.default_rng(3))
    permutation_sd = float(np.std(null.effects, ddof=1))

    ratio = model_se / permutation_sd
    assert 0.5 < ratio < 2.0, (
        f"the model's SE ({model_se:.6f}) and the permutation spread "
        f"({permutation_sd:.6f}) disagree by {ratio:.2f}x. The interval the "
        "acceptance rule depends on is not the width the data's own dependence "
        "structure implies"
    )


def test_an_uncalibrated_null_is_reported_as_such():
    """The result must be able to say the test failed calibration."""
    data = synthetic(reduction=0.0, rng=np.random.default_rng(1))
    result = permutation_null(
        *data, n_permutations=20, nominal=-1.0, rng=np.random.default_rng(3)
    )
    assert not result.calibrated
    # Assert the PROPERTY that failed, not the wording that reports it. An
    # earlier test here matched a message string, which survives any change to
    # the mechanism and fails on any change to the prose -- exactly backwards.
    assert not result.full_upper_within_nominal
    assert result.full_ci[1] > result.nominal


def test_seed_remains_the_replication_level_after_the_pairing_correction():
    """What D-082's seed-intercept regression was really protecting (D-094).

    That test asserted a `mixedlm` structure the primary no longer uses, so
    asserting it now would pin a mechanism instead of a property. The property
    is that **seed is a modelled level**: the interval is taken across seeds, so
    seed-level variation in the repair effect must widen it.

    This is the exact failure mode of the literal Change-Record specification.
    Reduced to what is estimable, that model treats pairs as iid and is blind to
    seed-level effect variation -- measured, its SE runs up to 8.7x too small,
    which would make the test anti-conservative and manufacture repairs out of
    seed noise. If anyone reverts to it, this test fails.
    """
    def with_seed_spread(sd, rng):
        e, r, s, ep, tr = synthetic(reduction=0.0, rng=rng)
        shift = {seed: rng.normal(0, sd) for seed in np.unique(s)}
        e = e + np.array([shift[a] * b for a, b in zip(s, r)])
        return e, r, s, ep, tr

    flat = acceptance_test(*with_seed_spread(0.0, np.random.default_rng(1)))
    varied = acceptance_test(*with_seed_spread(0.01, np.random.default_rng(1)))

    flat_w = flat.ci_high - flat.ci_low
    varied_w = varied.ci_high - varied.ci_low
    assert varied_w > 3 * flat_w, (
        f"interval width {varied_w:.8f} with seed-varying effects vs "
        f"{flat_w:.8f} without. Seed is not acting as the replication level, so "
        "the test cannot see effects that differ across training runs -- which is "
        "what P§7.3's twenty seeds exist to measure"
    )


def test_the_degrees_of_freedom_come_from_seeds_not_transitions():
    """20 seeds means t(19), not a normal on 3,200 rows."""
    from scipy import stats

    data = synthetic(reduction=0.35, rng=np.random.default_rng(0))
    result = acceptance_test(*data)
    half = (result.ci_high - result.ci_low) / 2
    se = half / stats.t.ppf(0.975, result.n_seeds - 1)
    # Reconstructing with a normal quantile would give a visibly different width.
    assert abs(half / (1.959964 * se) - 1) > 0.05

def test_the_paired_model_matches_the_paired_null_spread():
    """The Change Record's whole purpose, asserted on the number.

    Before D-094 the model's SE was 1.51x the true paired null spread, because
    P§7.3 had no transition-level term while the comparison is paired per
    transition. The withdrawn global permutation had HIDDEN that by inflating
    the null's spread 1.46x, cancelling to a reassuring 1.03. This asserts the
    two now agree, and fails if either the pairing is dropped from the model or
    the null stops preserving the matched design.
    """
    data = synthetic(reduction=0.0, rng=np.random.default_rng(1))
    observed = acceptance_test(*data)
    model_se = (observed.ci_high - observed.ci_low) / 2 / 2.093024  # t(19), 95%

    null = permutation_null(*data, n_permutations=200, rng=np.random.default_rng(3))
    paired_sd = float(np.std(null.effects, ddof=1))

    ratio = model_se / paired_sd
    assert 0.7 < ratio < 1.4, (
        f"model SE {model_se:.8f} vs paired null spread {paired_sd:.8f} = "
        f"{ratio:.2f}x. The D-094 pairing correction is not holding"
    )


def test_the_pairing_is_required_not_optional():
    """An absent pairing key would silently restore the over-wide interval."""
    import inspect

    params = inspect.signature(acceptance_test).parameters
    assert params["transition"].default is inspect.Parameter.empty


def test_an_unmatched_pair_is_refused():
    """A pair with two rows of one arm is not a pair (D-094)."""
    e, r, s, ep, tr = synthetic(reduction=0.0, rng=np.random.default_rng(1))
    r = r.copy()
    r[1] = 0  # that pair now has two baseline rows and no repaired row
    with pytest.raises(ValueError, match="exactly one baseline and one repaired"):
        acceptance_test(e, r, s, ep, tr)


@pytest.mark.parametrize("pair_strength", [1.0, 0.9, 0.5, 0.0])
def test_calibration_holds_across_preregistered_pairing_strengths(pair_strength):
    """Sol's requirement: the near-perfect generator is a stress case, not an estimate.

    The old model failed hardest exactly where pairing was strongest (0/200 at
    1.0, drifting to 8/200 at 0.0). The corrected one must be calibrated at all
    of them, or it has merely moved the miscalibration somewhere else.
    """
    data = synthetic_paired(pair_strength=pair_strength, rng=np.random.default_rng(1))
    result = permutation_null(*data, n_permutations=200, rng=np.random.default_rng(3))
    assert result.calibrated, result.reason
    assert 1 <= result.n_accepted_statistical <= 10
    assert result.n_accepted_full == 0


def test_the_effect_and_its_denominator_are_weighted_THE_SAME_WAY():
    """Sol, delta 45: both sides of the ratio must use equal-seed weighting.

    The effect equally weights seed means. A denominator weighting raw
    transitions would make the reported relative reduction a ratio of two
    differently-weighted quantities -- the D-042/D-044 shape, where correct
    arithmetic on mismatched estimands produces a wrong number.

    Made refutable by giving the seeds UNEQUAL transition counts, so the two
    weightings genuinely differ.
    """
    from bu.stats import acceptance as A

    e, r, s, ep, tr = [], [], [], [], []
    for seed, n_ep in enumerate((2, 8, 8, 8)):          # seed 0 is much smaller
        for episode in range(n_ep):
            for step in range(10):
                base = 1.0 if seed == 0 else 0.1        # ...and much worse
                for arm, val in ((0, base), (1, base * 0.5)):
                    e.append(val); r.append(arm)
                    s.append(seed); ep.append(episode); tr.append(step)
    data = A._frame(np.array(e), np.array(r), np.array(s), np.array(ep), np.array(tr))

    equal_seed = A.equal_seed_baseline_mean(data)
    by_transition = float(data.loc[data.repair == 0, "error"].mean())
    assert equal_seed != pytest.approx(by_transition), (
        "the fixture does not distinguish the two weightings, so this test "
        "could not fail"
    )

    result = acceptance_test(np.array(e), np.array(r), np.array(s),
                             np.array(ep), np.array(tr))
    assert result.unrepaired_mean == pytest.approx(equal_seed)
    # Every arm is halved, so the equal-seed relative reduction is exactly 50%.
    assert result.relative_reduction == pytest.approx(0.5, abs=1e-9)


def test_the_result_language_is_not_a_mixed_model_claim():
    """Sol: this is no longer 'a fixed effect from a mixed model'."""
    result = acceptance_test(*synthetic(reduction=0.35, rng=np.random.default_rng(0)))
    text = result.summary()
    assert "equal-seed mean paired difference" in text
    assert "fixed effect" not in text
    assert "mixedlm" not in text and result.method == "paired_seed_cluster"
