"""C-006: does the MDE simulation implement the estimator it claims to?

D-044 specified the validation, and it is the whole point of the module: the
simulation must agree with the **independent-units** analytic result at ICC = 0,
and with the **unit-weighted** analytic boundary at ICC = 1 — 75.00 for class 0
and 72.58 for class 1. Those two agreements are what distinguish a simulation of
the registered estimator from a simulation of something adjacent to it.

The analytic formulas live **here and nowhere else**. D-044: "A function
returning an effective sample size is how the first wrong number escaped, and
naming it would invite the same misuse." They are a check on the simulation, not
an output of it, and `bu.stats.mde` deliberately exports no `n_eff`.
"""

from __future__ import annotations

import numpy as np
import pytest

from bu.stats import mde as M


def analytic_class_variance(sizes, p, icc):
    """Var of a unit-weighted class mean under exchangeable within-group correlation.

    Var(mean) = p(1-p)/n^2 * [n + icc*(sum m^2 - n)]. At icc=0 this is p(1-p)/n
    — independent units. At icc=1 it is p(1-p)*sum(m^2)/n^2, i.e. an effective
    sample size of n^2/sum(m^2), which is where 75.00 and 72.58 come from.
    """
    n = float(sum(sizes))
    s2 = float(sum(m * m for m in sizes))
    return p * (1 - p) / n**2 * (n + icc * (s2 - n))


def analytic_difference_sd(design, p_a, p_b, icc):
    """SD of the paired BA difference with independent systems (system_corr=0)."""
    var = 0.0
    for cls, sizes in design.sizes.items():
        var += analytic_class_variance(sizes, p_a, icc) / 4
        var += analytic_class_variance(sizes, p_b, icc) / 4
    return float(np.sqrt(var))


def full_design():
    return M.HeldOutDesign(sizes=M.design_group_sizes())


# --- the design this samples from is the real one --------------------------


def test_the_group_structure_is_the_real_design_matrix():
    sizes = M.design_group_sizes()
    assert sum(sizes[0]) == sum(sizes[1]) == 150, "unit-level balance is 150/150"
    assert len(sizes[0]) == 125 and len(sizes[1]) == 115
    assert sorted(sizes[0]) == sorted([1] * 120 + [6] * 5)
    assert sorted(sizes[1]) == sorted([1] * 105 + [4] * 5 + [5] * 5)


def test_the_icc_one_boundary_is_the_number_d044_records():
    """75.00 and 72.58 — the unit-weighted boundary, not the cluster counts.

    D-042 first reported the cluster counts 125/115 as *the* effective sample
    size; D-044 corrected it. If this test ever disagrees with 75.00/72.58, the
    design matrix has changed and every power statement derived from it is stale.
    """
    sizes = M.design_group_sizes()
    for cls, expected in ((0, 75.00), (1, 72.58)):
        n = sum(sizes[cls])
        n_eff = n**2 / sum(m * m for m in sizes[cls])
        assert n_eff == pytest.approx(expected, abs=0.01)
    # ...and the cluster counts are a DIFFERENT estimand, not an approximation.
    assert len(sizes[0]) == 125 and len(sizes[1]) == 115


# --- the two agreements D-044 requires --------------------------------------


@pytest.mark.parametrize("icc, tol", [(0.0, 0.06), (1.0, 0.08)])
def test_the_simulation_matches_the_analytic_estimator_at_both_boundaries(icc, tol):
    """ICC=0 against independent units; ICC=1 against the 75.00/72.58 boundary.

    Compared on the **standard deviation of the difference**, which is what the
    power calculation actually consumes — agreeing on a point estimate would say
    nothing about whether the dependence is modelled correctly.
    """
    design, p_b, delta = full_design(), 0.70, 0.0
    rng = np.random.default_rng(20260818)
    result = M.simulate(
        design, baseline_accuracy=p_b, delta=delta, icc=icc,
        system_corr=0.0, n_sim=4000, n_boot=2, rng=rng,
    )
    # Empirical SD of the simulated differences, recomputed directly.
    correct_a, correct_b = {}, {}
    rng = np.random.default_rng(20260818)
    from scipy import stats as st
    for cls, sizes in design.sizes.items():
        za, zb = M._correlated_latents(
            sizes, icc=icc, system_corr=0.0, n_sim=4000, rng=rng
        )
        correct_a[cls] = za < st.norm.ppf(p_b + delta)
        correct_b[cls] = zb < st.norm.ppf(p_b)
    observed = M._balanced_accuracy(correct_a) - M._balanced_accuracy(correct_b)

    expected = analytic_difference_sd(design, p_b + delta, p_b, icc)
    assert observed.std(ddof=1) == pytest.approx(expected, rel=tol), (
        f"at icc={icc} the simulated SD {observed.std(ddof=1):.5f} disagrees with "
        f"the analytic {expected:.5f}; the simulation is not implementing the "
        "unit-weighted, group-correlated estimator it claims to (D-044)"
    )
    assert result["mean_difference"] == pytest.approx(0.0, abs=0.01)


def test_the_group_bootstrap_interval_is_calibrated():
    """The bootstrap SE must match the true sampling SD, or the test is wrong.

    This is what makes the power numbers mean anything: power is counted by
    comparing the observed difference to `1.96 * bootstrap SE`, so a bootstrap
    that understates the spread would report power the design does not have.
    """
    design = M.HeldOutDesign(sizes=M.design_group_sizes())
    rng = np.random.default_rng(7)
    result = M.simulate(
        design, baseline_accuracy=0.70, delta=0.0, icc=0.5,
        system_corr=0.0, n_sim=600, n_boot=300, rng=rng,
    )
    truth = analytic_difference_sd(design, 0.70, 0.70, icc=0.0)
    # The latent ICC is not the binary ICC (see the module note), so the true SD
    # lies between the icc=0 and icc=1 analytic values. The bootstrap must land
    # in that band rather than below it — understating is the failure that matters.
    upper = analytic_difference_sd(design, 0.70, 0.70, icc=1.0)
    assert truth <= result["mean_se"] <= upper * 1.15, (
        f"bootstrap SE {result['mean_se']:.5f} outside [{truth:.5f}, {upper:.5f}]"
    )


def test_a_type_one_error_rate_near_alpha_at_zero_effect():
    """With no true difference, rejection should sit near ALPHA, not above it."""
    design = M.draw_heldout(80, np.random.default_rng(3))
    result = M.simulate(
        design, baseline_accuracy=0.70, delta=0.0, icc=0.3,
        system_corr=0.0, n_sim=1500, n_boot=250, rng=np.random.default_rng(11),
    )
    assert result["power"] < 0.10, (
        f"false-positive rate {result['power']:.3f} at zero effect; the interval "
        "is anti-conservative and every power number above it is inflated"
    )


# --- the partition rules ----------------------------------------------------


def test_no_comparison_group_spans_both_classes():
    """A group-preserving partition must also be class-preserving (D-039)."""
    M.design_group_sizes()  # raises if any group spans classes


def test_held_out_units_are_drawn_as_whole_groups():
    """Units sharing a comparison group were given related data by design."""
    rng = np.random.default_rng(1)
    pool = M.design_group_sizes()
    design = M.draw_heldout(60, rng)
    for cls, sizes in design.sizes.items():
        remaining = list(pool[cls])
        for m in sizes:
            assert m in remaining, "a drawn group size is not one the design has"
            remaining.remove(m)


def test_the_class_split_is_balanced_at_the_unit_level():
    """P§10.4 balances units, not groups — and groups are indivisible."""
    design = M.draw_heldout(60, np.random.default_rng(5))
    n0, n1 = design.n_units[0], design.n_units[1]
    assert min(n0, n1) >= 30
    # Overshoot is taken whole rather than trimmed: trimming would split a group.
    assert abs(n0 - n1) <= 6, f"class sizes {n0}/{n1} diverge more than one group"
    assert design.min_class == min(n0, n1)


def test_an_odd_heldout_count_is_refused():
    with pytest.raises(ValueError, match="unit-level class balance"):
        M.draw_heldout(61, np.random.default_rng(0))


def test_asking_for_more_units_than_the_design_has_is_refused():
    with pytest.raises(ValueError, match="cannot hold out"):
        M.draw_heldout(400, np.random.default_rng(0))


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_an_out_of_range_correlation_is_refused(bad):
    design = M.draw_heldout(20, np.random.default_rng(0))
    with pytest.raises(ValueError):
        M.simulate(design, baseline_accuracy=0.7, delta=0.05, icc=bad)
    with pytest.raises(ValueError):
        M.simulate(design, baseline_accuracy=0.7, delta=0.05, icc=0.0, system_corr=bad)


# --- there is deliberately no scalar helper --------------------------------


def test_the_module_exports_no_effective_sample_size():
    """D-044: naming one would invite the misuse that produced the first wrong number."""
    exported = [n for n in dir(M) if not n.startswith("_")]
    assert not any("n_eff" in n or "effective_sample" in n for n in exported), (
        f"a scalar effective-sample-size helper has reappeared: {exported}"
    )


def test_power_rises_with_effect_and_with_held_out_units():
    """Two monotonicities the simulation must show or it is not measuring power."""
    rng = np.random.default_rng(2)
    small = M.draw_heldout(20, rng)
    large = M.draw_heldout(80, rng)
    kw = dict(baseline_accuracy=0.70, icc=0.2, system_corr=0.0, n_sim=500, n_boot=150)

    weak = M.simulate(large, delta=0.02, rng=np.random.default_rng(4), **kw)["power"]
    strong = M.simulate(large, delta=0.20, rng=np.random.default_rng(4), **kw)["power"]
    assert weak < strong

    few = M.simulate(small, delta=0.10, rng=np.random.default_rng(6), **kw)["power"]
    many = M.simulate(large, delta=0.10, rng=np.random.default_rng(6), **kw)["power"]
    assert few < many
