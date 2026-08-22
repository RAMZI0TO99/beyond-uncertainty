"""The W4 Friday timing harness (D-113/D-114).

The harness itself measures wall time, which no test can usefully assert on.
What IS testable is the part that was wrong first: the fit accounting the
extrapolation multiplies. The first version summed obligations directly and
produced 6,750 baseline fits against the design's 6,375 — **the exact 375
phantom fits of D-033** — while simultaneously undercounting the repair side by
charging one fit per obligation instead of per seed. Two errors in opposite
directions, in a function whose only job is counting.
"""

from __future__ import annotations

import pytest

from bu.experiments.enumerate_units import design_units, total_model_fits
from bu.experiments.w4_timing import TIMING_STAGE, design_fits_by_size, extrapolate


def test_the_accounting_matches_the_design_exactly():
    """The regression for D-033. Off-by-375 must fail here, loudly."""
    fits = design_fits_by_size()
    reference = total_model_fits(design_units())
    expected = reference["total"] - reference["ablations"]
    assert sum(fits.values()) == expected, (
        f"harness counts {sum(fits.values())} fits against the design's "
        f"{expected}. If this is off by 375, the accounting has re-acquired "
        "D-033's phantom fits by summing obligations instead of execution_plan"
    )


def test_data_repair_is_counted_at_its_ten_times_budget():
    """A repair arm that trains on 10x data must not be costed at the base size.

    This is what makes the extrapolation more than a single scaled rate: the
    largest registered size is 5,000, but data repair on it trains at 50,000,
    and 50,000 is over 12x more expensive per fit than 5,000.
    """
    fits = design_fits_by_size()
    assert max(fits) == 50_000, "no fits are counted above the largest base size"
    assert fits[50_000] > 0


def test_the_harness_never_runs_at_a_registered_stage():
    """A timing run must not be able to enter a claim."""
    assert TIMING_STAGE == "pilot"


def test_extrapolation_charges_unmeasured_sizes_conservatively():
    """A size with no measured rate is charged at the nearest size AT OR ABOVE it.

    Charging it at a smaller size would understate the total, and this harness
    exists because a compute condition was already signed off on an optimistic
    proxy.
    """
    rates = {100: 1.0, 5000: 10.0}
    seconds = extrapolate(rates, {2500: 3})
    assert seconds[2500] == pytest.approx(30.0), "2,500 must be charged at 5,000's rate"


def test_extrapolation_is_linear_in_the_fit_count():
    rates = {5000: 2.0}
    assert extrapolate(rates, {5000: 10})[5000] == pytest.approx(20.0)
