"""Ensemble uncertainty metrics (Plan §10.3, Schedule W3 Fri).

These are H1's and H2's dependent variables, so the definitions are
preregistered rather than conventional. The tests below are mostly about the
choices Plan §10.3 fixes explicitly — because each one is a statistic that
differs from its neighbour, and a number computed the other way is not
comparable to anything the plan describes.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bu.models.uncertainty import (
    RATIO_FLOOR,
    UncertaintySummary,
    across_seeds,
    normalised_error,
    pairwise_disagreement,
    per_dimension_scale,
    predictive_variance,
    summarise,
)


def _members(k: int = 5, n: int = 64, d: int = 2, spread: float = 1.0) -> torch.Tensor:
    g = torch.Generator().manual_seed(0)
    base = torch.randn(n, d, generator=g)
    return base.unsqueeze(0) + spread * torch.randn(k, n, d, generator=g)


# --- disagreement ----------------------------------------------------------


def test_identical_members_disagree_by_exactly_zero():
    one = torch.randn(16, 2)
    members = one.unsqueeze(0).repeat(4, 1, 1)
    assert torch.allclose(pairwise_disagreement(members), torch.zeros(16), atol=1e-6)


def test_disagreement_grows_with_member_spread():
    tight = pairwise_disagreement(_members(spread=0.1)).mean()
    loose = pairwise_disagreement(_members(spread=2.0)).mean()
    assert loose > tight


def test_disagreement_is_one_number_per_transition():
    assert pairwise_disagreement(_members(n=37)).shape == (37,)


def test_disagreement_uses_the_ordered_pair_convention():
    """Two members, distance d: the mean over ordered pairs is d, not d/2.

    Stated because the two conventions differ by a factor of two, and a
    disagreement number without its convention is not comparable to anything.
    """
    a = torch.zeros(1, 1, 3)
    b = torch.full((1, 1, 3), 1.0)
    members = torch.cat([a, b])
    expected = float(torch.linalg.vector_norm(b - a))
    assert float(pairwise_disagreement(members)[0]) == pytest.approx(expected)


def test_a_single_member_cannot_disagree():
    with pytest.raises(ValueError, match="at least two members"):
        pairwise_disagreement(torch.randn(1, 8, 2))


# --- normalisation ---------------------------------------------------------


def test_per_dimension_normalisation_stops_one_dimension_dominating():
    """Plan §10.3's reason for normalising, stated as the property."""
    targets = torch.stack([torch.randn(256), 100 * torch.randn(256)], dim=1)
    predictions = targets + torch.stack([torch.ones(256), torch.ones(256)], dim=1)

    scale = per_dimension_scale(targets)
    assert scale[1] > 10 * scale[0]
    # After normalisation the same absolute error in the wide dimension counts
    # for far less, which is the entire point.
    raw = (predictions - targets).abs().mean(dim=0)
    normalised = ((predictions - targets) / scale).abs().mean(dim=0)
    assert raw[0] == pytest.approx(float(raw[1]), rel=1e-3)
    assert normalised[0] > 10 * normalised[1]


def test_a_constant_dimension_does_not_divide_by_zero():
    targets = torch.stack([torch.randn(64), torch.ones(64)], dim=1)
    # float32 stores the floor a hair below its decimal value; the property
    # is that it is floored at all, not that it round-trips exactly.
    assert float(per_dimension_scale(targets)[1]) == pytest.approx(RATIO_FLOOR)


def test_a_perfect_prediction_has_zero_error():
    targets = torch.randn(32, 2)
    assert torch.allclose(normalised_error(targets, targets), torch.zeros(32), atol=1e-6)


# --- the H2 ratio ----------------------------------------------------------


def test_the_ratio_is_of_means_not_a_mean_of_ratios():
    """Plan §10.3 names one of these, and on this data they differ.

    Near-zero denominators make per-transition ratios arbitrarily large, so a
    mean of them is dominated by the smallest errors rather than describing the
    condition.
    """
    members = _members(spread=0.5)
    targets = members.mean(dim=0) + 1e-4 * torch.randn(members.shape[1], 2)

    summary = summarise(members, targets, n_transitions=100, seed=0)
    scale = per_dimension_scale(targets)
    per_transition = (
        pairwise_disagreement(members, scale)
        / torch.clamp(normalised_error(members.mean(dim=0), targets, scale), min=RATIO_FLOOR)
    )
    assert summary.ratio != pytest.approx(float(per_transition.mean()), rel=0.05)


def test_the_denominator_floor_prevents_an_exploding_ratio():
    members = _members(spread=0.0)          # no disagreement
    targets = members[0].clone()            # and no error either
    summary = summarise(members, targets, n_transitions=10, seed=0)
    assert np.isfinite(summary.ratio)


# --- aggregation across seeds ----------------------------------------------


def test_seeds_are_aggregated_after_dividing_never_before():
    """Plan §10.3: computed per seed, reported as a mean across seeds."""
    summaries = [
        UncertaintySummary(100, s, 50, mean_error=e, mean_disagreement=d,
                           mean_predictive_variance=0.1, ratio=d / e)
        for s, (e, d) in enumerate([(1.0, 0.5), (2.0, 0.5), (4.0, 0.5)])
    ]
    aggregated = across_seeds(summaries)
    expected = float(np.mean([0.5 / 1.0, 0.5 / 2.0, 0.5 / 4.0]))
    assert aggregated["ratio_mean"] == pytest.approx(expected)
    # Pooling first would give 0.5 / mean(1, 2, 4) = 0.214, a different number.
    assert aggregated["ratio_mean"] != pytest.approx(0.5 / np.mean([1.0, 2.0, 4.0]))


def test_aggregation_reports_a_standard_deviation():
    summaries = [
        UncertaintySummary(100, s, 50, 1.0 + s, 0.5, 0.1, 0.5) for s in range(3)
    ]
    aggregated = across_seeds(summaries)
    assert aggregated["n_seeds"] == 3
    assert aggregated["mean_error_sd"] > 0


def test_one_seed_reports_zero_spread_rather_than_nan():
    aggregated = across_seeds([UncertaintySummary(100, 0, 50, 1.0, 0.5, 0.1, 0.5)])
    assert aggregated["mean_error_sd"] == 0.0


def test_empty_aggregation_is_an_error_not_a_nan():
    with pytest.raises(ValueError, match="no summaries"):
        across_seeds([])


# --- predictive variance ---------------------------------------------------


def test_predictive_variance_is_zero_for_identical_members():
    one = torch.randn(16, 2)
    members = one.unsqueeze(0).repeat(4, 1, 1)
    assert torch.allclose(predictive_variance(members), torch.zeros(16), atol=1e-6)


def test_predictive_variance_tracks_spread():
    assert (
        predictive_variance(_members(spread=2.0)).mean()
        > predictive_variance(_members(spread=0.2)).mean()
    )
