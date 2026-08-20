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
    errors, repair, seeds, episodes = [], [], [], []
    for s in range(n_seeds):
        s_effect = rng.normal(0, seed_sd)
        for ep in range(n_episodes):
            e_effect = rng.normal(0, episode_sd)
            for _ in range(n_transitions):
                base = BASE + s_effect + e_effect + rng.normal(0, noise)
                for arm in (0, 1):
                    value = base * (1 - reduction) if arm else base
                    errors.append(value + (rng.normal(0, noise) if arm else 0.0))
                    repair.append(arm)
                    seeds.append(s)
                    episodes.append(ep)
    return np.array(errors), np.array(repair), np.array(seeds), np.array(episodes)


# --- the three conditions, each able to refuse on its own -------------------


def test_a_real_repair_is_accepted_and_its_size_recovered():
    result = acceptance_test(*synthetic(reduction=0.35, rng=np.random.default_rng(0)))
    assert result.passed
    assert result.method == "mixedlm"
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


def test_the_fallback_is_recorded_as_a_different_method():
    """"Passed under the fallback" and "passed under the registered model" differ."""
    from bu.stats import acceptance as A

    data = synthetic(reduction=0.35, rng=np.random.default_rng(0))
    frame = A._frame(*data)
    result = A._episode_mean_fallback(
        frame, dict(n_transitions=len(frame), n_seeds=20, n_episodes=160,
                    unrepaired_mean=float(frame.loc[frame.repair == 0, "error"].mean())),
        float(frame.loc[frame.repair == 0, "error"].mean()),
    )
    assert result.method == "episode_mean_fallback"
    assert result.passed
    assert "fallback" in result.reason


def test_refusing_the_fallback_is_possible():
    """A caller may insist on the registered model rather than a substitute."""
    import bu.stats.acceptance as A

    original = A.acceptance_test
    data = synthetic(reduction=0.35, rng=np.random.default_rng(0))
    # Force non-convergence by handing the model a single episode per seed with
    # no within-seed variation to estimate.
    errors, repair, seeds, episodes = data
    with pytest.raises(RuntimeError, match="allow_fallback is False"):
        import statsmodels.formula.api as smf
        real = smf.mixedlm
        smf.mixedlm = lambda *a, **k: (_ for _ in ()).throw(ValueError("forced"))
        try:
            A.acceptance_test(errors, repair, seeds, episodes, allow_fallback=False)
        finally:
            smf.mixedlm = real
    assert A.acceptance_test is original


# --- input validation -------------------------------------------------------


def test_mismatched_lengths_are_refused():
    errors, repair, seeds, episodes = synthetic(rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match="same length"):
        acceptance_test(errors[:-1], repair, seeds, episodes)


def test_a_single_arm_is_refused():
    """A one-armed test would report the intercept as an effect."""
    errors, repair, seeds, episodes = synthetic(rng=np.random.default_rng(0))
    keep = repair == 0
    with pytest.raises(ValueError, match="only one value"):
        acceptance_test(errors[keep], repair[keep], seeds[keep], episodes[keep])


def test_a_non_binary_repair_indicator_is_refused():
    errors, repair, seeds, episodes = synthetic(rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match="0/1 indicator"):
        acceptance_test(errors, repair * 2, seeds, episodes)


def test_empty_input_is_refused():
    with pytest.raises(ValueError, match="no transitions"):
        acceptance_test([], [], [], [])


def test_episode_identity_is_scoped_to_its_seed():
    """Two seeds both have an episode 0, and they are different episodes (D-052)."""
    from bu.stats import acceptance as A

    frame = A._frame([1.0, 2.0], [0, 1], [0, 1], [0, 0])
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

    def spy(errors, repair, seed, episode, **kw):
        seen.append(np.asarray(repair).copy())
        return real(errors, repair, seed, episode, **kw)

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
    errors, repair, seeds, episodes = synthetic(rng=np.random.default_rng(0))
    # Strip the repaired arm from one seed.
    keep = ~((np.asarray(seeds) == np.unique(seeds)[0]) & (np.asarray(repair) == 1))
    with pytest.raises(ValueError, match="not both arms"):
        permutation_null(
            np.asarray(errors)[keep], np.asarray(repair)[keep],
            np.asarray(seeds)[keep], np.asarray(episodes)[keep],
            n_permutations=5,
        )


def test_the_permutation_null_refuses_more_than_two_arms():
    """Different repair types are permuted separately against baseline."""
    errors, repair, seeds, episodes = synthetic(rng=np.random.default_rng(0))
    repair = np.asarray(repair).copy()
    repair[:10] = 2
    # `_frame` refuses a non-0/1 indicator before the matched-design check
    # is reached; both guards exist, and this pins the one that fires.
    with pytest.raises(ValueError, match="0/1 indicator"):
        permutation_null(errors, repair, seeds, episodes, n_permutations=5)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "D-085's statistical-only rule is NOT met on the registered generator: "
        "0/200, exact CI [0.000%, 1.828%], which does not contain 5%. The "
        "registered P7.3 model has random intercepts for seed and "
        "episode-within-seed but NO transition-level pairing term, while the "
        "acceptance comparison is paired transition-by-transition on the same "
        "failure set -- so its SE is 1.51x the paired null's true spread and the "
        "test is CONSERVATIVE. The model is a Section-2 frozen constant, so "
        "changing it is a Change Record and Sol's ruling, not a fix made here. "
        "strict=True so that if this ever passes, the suite says so."
    ),
)
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
    # D-085's admissible counts, computed in advance from the exact binomial.
    assert 4 <= result.n_accepted_statistical <= 16
    assert 0 <= result.n_accepted_full <= 3
    assert np.std(result.effects) > 0, (
        "the permuted effects are identical, so the permutation is not permuting "
        "anything and the calibration check is vacuous"
    )


def test_sixty_permutations_cannot_satisfy_the_full_rule_at_any_count():
    """Why D-085 freezes n=200: the old n=60 test was unsatisfiable, not lucky."""
    from bu.stats.acceptance import clopper_pearson

    assert clopper_pearson(0, 60)[1] > 0.05
    assert clopper_pearson(0, 200)[1] <= 0.05


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


def test_the_model_has_a_seed_random_intercept_not_only_episode(monkeypatch):
    """P§7.3 wants random intercepts for seed AND episode-within-seed (D-082).

    Passing vc_formula without re_formula makes statsmodels silently drop the
    default group intercept, leaving only the episode component. The CI is
    unchanged for the paired repair contrast, so no verdict test would catch the
    omission -- this asserts the model *structure* directly. It captures the
    fitted MixedLMResults and checks its seed random-effect covariance is
    populated.
    """
    import statsmodels.formula.api as smf
    from bu.stats import acceptance as A

    captured = {}
    real_fit = smf.mixedlm

    def spy(*args, **kwargs):
        model = real_fit(*args, **kwargs)
        real_model_fit = model.fit

        def fit(*a, **k):
            res = real_model_fit(*a, **k)
            captured["cov_re_size"] = res.cov_re.size
            return res

        model.fit = fit
        return model

    monkeypatch.setattr(smf, "mixedlm", spy)
    acceptance_test(*synthetic(reduction=0.35, rng=np.random.default_rng(0)))

    assert captured.get("cov_re_size", 0) > 0, (
        "the fitted model has no seed random intercept; vc_formula without "
        "re_formula dropped it, and the model is not the one P§7.3 registers"
    )


def test_the_registered_model_is_conservative_under_transition_pairing():
    """The finding the corrected null exposed, pinned so it cannot drift silently.

    The withdrawn global permutation HID this. Breaking the within-seed pairing
    inflated the null's spread by 1.46x, which almost exactly cancelled the
    model's 1.51x over-wide SE and produced a reassuring ratio of 1.03 -- so the
    old check reported "the model's SE matches the permutation spread" and
    passed comfortably. Two independent errors cancelling into a number that
    looked like evidence.

    This asserts the real relationship. It fails if the model gains a pairing
    term (which would be a Section-2 Change Record) or if the null regresses to
    an unpaired shuffle.
    """
    data = synthetic(reduction=0.0, rng=np.random.default_rng(1))
    observed = acceptance_test(*data)
    model_se = (observed.ci_high - observed.ci_low) / (2 * 1.959963985)

    null = permutation_null(*data, n_permutations=200, rng=np.random.default_rng(3))
    paired_sd = float(np.std(null.effects, ddof=1))

    ratio = model_se / paired_sd
    assert ratio > 1.3, (
        f"model SE {model_se:.6f} vs paired null spread {paired_sd:.6f} = "
        f"{ratio:.2f}x. The conservatism D-085 recorded is gone -- either the "
        "acceptance model changed (Section 2 Change Record required) or the "
        "permutation stopped preserving the matched design"
    )
