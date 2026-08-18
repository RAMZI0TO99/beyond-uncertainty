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


def test_the_permutation_moves_whole_runs_never_transitions():
    """P§7.3: never permute across episodes or transitions.

    A transition-level shuffle would break the within-episode and within-seed
    correlation the model exists to account for, and the resulting null would be
    far too narrow — the test would look better calibrated than it is.
    """
    from bu.stats import acceptance as A

    errors, repair, seeds, episodes = synthetic(rng=np.random.default_rng(0))
    frame = A._frame(errors, repair, seeds, episodes)
    run_key = list(zip(frame["seed"], frame["repair"]))
    runs = sorted(set(run_key), key=repr)
    labels = np.array([r[1] for r in runs])

    # The permuted label vector must be constant within every run block.
    index = {run: i for i, run in enumerate(runs)}
    positions = np.array([index[k] for k in run_key])
    permuted = np.random.default_rng(0).permutation(labels)[positions]
    for run in runs:
        block = np.array([k == run for k in run_key])
        assert len(np.unique(permuted[block])) == 1, "a run was split by the permutation"
    assert permuted.sum() == labels.sum() * len(frame) / len(runs), (
        "the number of repaired transitions changed"
    )


def test_the_permutation_null_is_calibrated_on_null_data():
    """S§W5 Wed's deliverable: an FPR number, and it must not exceed nominal."""
    data = synthetic(reduction=0.0, rng=np.random.default_rng(1))
    result = permutation_null(*data, n_permutations=60, rng=np.random.default_rng(3))
    assert result.calibrated, result.reason
    assert result.false_positive_rate <= result.nominal
    assert np.std(result.effects) > 0, (
        "the permuted effects are identical, so the permutation is not permuting "
        "anything and the calibration check is vacuous"
    )


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
    assert "ABOVE NOMINAL" in result.reason


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
