"""The H1 trend test, against the reading rule frozen before it saw data (D-068).

Every test here states a clause of the registered rule. The rule was fixed by
Sol *in advance* precisely because the pilot's curve is non-monotone at the
small end, and the temptation at that point is to adjust the instrument. So the
tests assert the rule as written, including the cases where it refuses a result
that a friendlier reading would have passed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bu import constants as K
from bu.stats.trend import (
    PARTITIONS, curves_from_rows, spearman, trend_test,
)

SIZES = K.DATA_SIZES
DEV = (0, 1, 2)
CONF = tuple(K.CONFIRMATORY_SEED_BASE + i for i in range(5))
ROOT = Path(__file__).resolve().parents[1]


def curve(values, seeds=DEV, jitter=0.0):
    """One curve per seed; ``jitter`` separates seeds without changing shape."""
    return {
        seed: {n: v + jitter * i for n, v in zip(SIZES, values)}
        for i, seed in enumerate(seeds)
    }


# --- the statistic itself --------------------------------------------------


def test_spearman_matches_an_independent_implementation():
    """Checked against scipy rather than against my own arithmetic.

    A rank correlation is easy to write and easy to write subtly wrong -- tie
    handling especially -- and the coefficient is a registered endpoint.
    """
    scipy_stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(0)
    for _ in range(25):
        x = rng.normal(size=6)
        y = rng.normal(size=6)
        assert spearman(x, y) == pytest.approx(scipy_stats.spearmanr(x, y).statistic)

    # And with ties, which is where a naive rank assignment diverges.
    x = np.array([1.0, 2.0, 2.0, 3.0, 3.0, 3.0])
    y = np.array([5.0, 4.0, 4.0, 1.0, 2.0, 2.0])
    assert spearman(x, y) == pytest.approx(scipy_stats.spearmanr(x, y).statistic)


def test_a_constant_series_has_no_coefficient():
    assert np.isnan(spearman(np.arange(6.0), np.ones(6)))


# --- the nine clauses of the registered rule -------------------------------


def test_a_perfect_expected_trend_passes():
    """Disagreement falling monotonically with data: H1's prediction."""
    result = trend_test(curve([0.9, 0.7, 0.5, 0.4, 0.3, 0.2]), partition="development")
    assert result.rho == pytest.approx(-1.0)
    assert result.ci_high < 0
    assert result.passed
    assert "below zero" in result.reason


def test_a_reversed_trend_fails():
    """An interval entirely above zero is a reversal, not a weaker success."""
    result = trend_test(curve([0.2, 0.3, 0.4, 0.5, 0.7, 0.9]), partition="development")
    assert result.rho == pytest.approx(1.0)
    assert result.ci_low > 0
    assert not result.passed
    assert "REVERSED" in result.reason


def test_an_interval_touching_zero_fails():
    """Constructed so the upper bound is exactly 0.0 -- the boundary case.

    One seed falls perfectly, one rises perfectly, one is flat-with-a-kink, so
    resamples span the whole range and the 97.5th percentile sits at zero.
    """
    curves = {
        0: dict(zip(SIZES, [0.9, 0.7, 0.5, 0.4, 0.3, 0.2])),
        1: dict(zip(SIZES, [0.2, 0.3, 0.4, 0.5, 0.7, 0.9])),
        2: dict(zip(SIZES, [0.5, 0.5, 0.5, 0.5, 0.5, 0.6])),
    }
    result = trend_test(curves, partition="development")
    assert result.ci_high >= 0
    assert not result.passed
    assert "contains or touches zero" in result.reason


def test_a_mildly_non_monotone_curve_can_still_pass():
    """THE case this rule exists for, and the pilot's actual shape.

    Disagreement peaks at N=250 and falls thereafter. No point is removed, no
    curve is smoothed: the peak weakens rho, and if the interval stays wholly
    negative the test passes on the registered statistic alone. An out-of-order
    point has no separate veto (D-068).
    """
    values = [0.60, 0.82, 0.55, 0.42, 0.27, 0.21]  # the N=250 peak
    result = trend_test(curve(values, jitter=0.01), partition="development")
    assert result.mean_curve[1] > result.mean_curve[0], "the peak was flattened"
    assert -1.0 < result.rho < 0.0, "a non-monotone curve should weaken rho"
    assert result.passed
    assert result.ci_high < 0


def test_constant_disagreement_fails():
    """No direction at all. The strongest evidence against a trend must not
    produce an interval by imputation."""
    result = trend_test(curve([0.5] * 6), partition="development")
    assert np.isnan(result.rho)
    assert not result.passed
    assert "undefined coefficient" in result.reason


@pytest.mark.parametrize(
    "sizes, match",
    [
        ((100, 250, 500, 1000, 2500), "registered grid"),
        ((100, 250, 250, 500, 1000, 2500), "duplicate dataset sizes"),
        ((5000, 2500, 1000, 500, 250, 100), "ascending"),
        ((100, 250, 500, 1000, 2500, 7500), "registered grid"),
    ],
)
def test_a_malformed_size_grid_fails(sizes, match):
    """Missing, duplicated, unordered or non-registered grids are refused.

    The trimmed grid is the one that matters. Computing the statistic over five
    sizes yields a number indistinguishable from the registered one in every
    artefact that carries it — which is exactly the "drop the awkward small
    end" move the frozen rule forbids.
    """
    curves = curve([0.9, 0.7, 0.5, 0.4, 0.3, 0.2])
    with pytest.raises(ValueError, match=match):
        trend_test(curves, partition="development", sizes=sizes)


def test_a_trimmed_grid_is_refused_even_when_the_curves_match_it():
    """The loophole a passing test would have hidden.

    Refusing a five-size grid because the *curves* have six sizes is not the
    property; the property is that the grid itself is preregistered. Trim both
    consistently and it must still fail.
    """
    trimmed = SIZES[:-1]
    curves = {
        seed: {n: v for n, v in zip(trimmed, [0.9, 0.7, 0.5, 0.4, 0.3])}
        for seed in DEV
    }
    with pytest.raises(ValueError, match="registered grid"):
        trend_test(curves, partition="development", sizes=trimmed)


def test_an_incomplete_seed_curve_fails():
    curves = curve([0.9, 0.7, 0.5, 0.4, 0.3, 0.2])
    del curves[1][SIZES[3]]
    with pytest.raises(ValueError, match="missing dataset sizes"):
        trend_test(curves, partition="development")


def test_a_seed_carrying_an_unregistered_size_fails():
    curves = curve([0.9, 0.7, 0.5, 0.4, 0.3, 0.2])
    curves[2][7500] = 0.1
    with pytest.raises(ValueError, match="outside the registered grid"):
        trend_test(curves, partition="development")


def test_seed_ordering_does_not_change_the_result():
    """The blocks are exchangeable; a dict's insertion order is not evidence."""
    values = [0.60, 0.82, 0.55, 0.42, 0.27, 0.21]
    forward = curve(values, jitter=0.02)
    reversed_order = {seed: forward[seed] for seed in reversed(list(forward))}

    a = trend_test(forward, partition="development")
    b = trend_test(reversed_order, partition="development")
    assert (a.rho, a.ci_low, a.ci_high, a.passed) == (b.rho, b.ci_low, b.ci_high, b.passed)
    assert a.seeds == b.seeds


def test_the_exact_bootstrap_is_deterministic_and_complete():
    """No RNG exists, so two runs cannot differ and no seed can be forgotten."""
    values = [0.60, 0.82, 0.55, 0.42, 0.27, 0.21]
    a = trend_test(curve(values, jitter=0.02), partition="development")
    b = trend_test(curve(values, jitter=0.02), partition="development")
    assert a == b
    assert a.n_resamples == 3 ** 3 == 27

    five = trend_test(curve(values, seeds=CONF, jitter=0.02), partition="confirmatory")
    assert five.n_resamples == 5 ** 5 == 3125


# --- the partition boundary (D-034, D-040, D-068) --------------------------


def test_the_partition_is_validated_and_never_pooled():
    """The gate is development-only, the verdict confirmatory-only.

    Spending confirmatory seeds to choose an estimator would consume the
    evidence the verdict needs, during method selection.
    """
    values = [0.9, 0.7, 0.5, 0.4, 0.3, 0.2]
    with pytest.raises(ValueError, match="is 'development' but this call declares"):
        trend_test(curve(values), partition="confirmatory")
    with pytest.raises(ValueError, match="is 'confirmatory' but this call declares"):
        trend_test(curve(values, seeds=CONF), partition="development")

    pooled = {**curve(values), **curve(values, seeds=CONF)}
    with pytest.raises(ValueError, match="this call declares"):
        trend_test(pooled, partition="development")

    with pytest.raises(ValueError, match="partition must be one of"):
        trend_test(curve(values), partition="pilot")


def test_the_partition_label_does_not_change_the_mathematics():
    """Same numbers, same verdict, whichever stage is reading them (D-068).

    The argument validates and labels. If it could change the statistic, the
    gate and the verdict would be two tests wearing one name.
    """
    values = [0.60, 0.82, 0.55, 0.42, 0.27, 0.21]
    dev = trend_test(curve(values, seeds=DEV, jitter=0.02), partition="development")
    conf_seeds = tuple(K.CONFIRMATORY_SEED_BASE + i for i in range(3))
    conf = trend_test(curve(values, seeds=conf_seeds, jitter=0.02), partition="confirmatory")

    assert dev.rho == conf.rho
    assert (dev.ci_low, dev.ci_high, dev.passed) == (conf.ci_low, conf.ci_high, conf.passed)
    assert dev.partition == "development" and conf.partition == "confirmatory"


def test_diagnostics_do_not_enter_the_pass_rule():
    """Per-seed rho is reported and is not a vote (D-068).

    Two of three seeds falling perfectly while the third reverses is exactly the
    "3 out of 5" reading Gate 2 refuses to treat as a positive.
    """
    curves = {
        0: dict(zip(SIZES, [0.9, 0.7, 0.5, 0.4, 0.3, 0.2])),
        1: dict(zip(SIZES, [0.9, 0.7, 0.5, 0.4, 0.3, 0.2])),
        2: dict(zip(SIZES, [0.1, 0.3, 0.6, 0.9, 1.4, 2.0])),
    }
    result = trend_test(curves, partition="development")
    assert result.per_seed_rho[0] == pytest.approx(-1.0)
    assert result.per_seed_rho[2] == pytest.approx(1.0)
    # The verdict comes from the mean curve and its interval, not from 2 of 3.
    assert result.passed is (result.ci_high < 0)


def test_the_result_records_the_rule_it_was_read_under():
    result = trend_test(curve([0.9, 0.7, 0.5, 0.4, 0.3, 0.2]), partition="development")
    row = result.as_row()
    assert row["direction"] == "negative"
    assert row["bootstrap"] == "exact_paired_seed_block"
    assert row["quantile_method"] == "linear"
    assert row["confidence_level"] == 0.95
    assert row["n_resamples"] == 27
    assert "PASS" in result.summary()


# --- reading the delivered attempt ----------------------------------------


def test_curves_are_built_from_one_immutable_attempt():
    rows = [
        {"seed": 0, "n_transitions": 100, "uncertainty": {"mean_disagreement": 0.5}},
        {"seed": 0, "n_transitions": 250, "uncertainty": {"mean_disagreement": 0.4}},
        {"seed": 1, "n_transitions": 100, "uncertainty": {"mean_disagreement": 0.6}},
    ]
    curves = curves_from_rows(rows)
    assert curves == {0: {100: 0.5, 250: 0.4}, 1: {100: 0.6}}

    with pytest.raises(ValueError, match="two rows for dataset size"):
        curves_from_rows(rows + [rows[0]])


@pytest.mark.skipif(
    not (ROOT / "runs" / "w3_pilot" / "attempt-001" / "rows.json").exists(),
    reason="no delivered pilot attempt",
)
def test_the_delivered_pilot_curves_are_complete():
    """The function runs against Week 3's outputs, which is W4 Mon's criterion.

    Asserts the shape of the input only. What the *verdict* is belongs in the
    session log and the delta, not in an assertion that would have to be edited
    if the pilot were ever regenerated.
    """
    rows = json.loads(
        (ROOT / "runs" / "w3_pilot" / "attempt-001" / "rows.json").read_text()
    )
    curves = curves_from_rows(rows)
    assert set(curves) == {0, 1, 2}
    for seed, c in curves.items():
        assert set(c) == set(SIZES), f"seed {seed} has an incomplete curve"

    result = trend_test(curves, partition="development")
    assert result.n_resamples == 27
    assert result.partition == "development"
    assert -1.0 <= result.rho <= 1.0
