"""The Week 4 reliability gate's eligibility and aggregation rules (D-070).

The gate is where an *authorised verdict* is distinguished from a computed
number. Every test here asserts a refusal or an aggregation rule, because the
statistic itself is already tested in `test_trend.py` and is deliberately not
reimplemented here.
"""

from __future__ import annotations

import pytest

from bu import constants as K
from bu.stats.gate import (
    GATE_CONFIG_IDS, GATE_LAYOUTS, GATE_SEEDS, RUNGS, gate_config_ids,
    gate_units, reliability_gate,
)

SIZES = K.DATA_SIZES
FALLING = [0.9, 0.7, 0.5, 0.4, 0.3, 0.2]
RISING = [0.2, 0.3, 0.4, 0.5, 0.7, 0.9]


def curves(values, seeds=GATE_SEEDS, jitter=0.01):
    return {
        seed: {n: v + jitter * i for n, v in zip(SIZES, values)}
        for i, seed in enumerate(seeds)
    }


def all_configurations(values=FALLING, **overrides):
    out = {name: curves(values) for name in GATE_LAYOUTS}
    out.update({name: curves(v) for name, v in overrides.items()})
    return out


# --- the predeclared configurations, frozen before Tuesday ----------------


def test_the_frozen_config_ids_still_describe_the_intended_units():
    """Golden values. If identity canonicalisation moves, this fails loudly.

    The gate's record names exact `config_id`s. Were they regenerated at run
    time, a change to identity fields would silently redirect the gate at
    different units while the record kept claiming the old ones (D-016).
    """
    for layout in GATE_LAYOUTS:
        assert gate_config_ids(layout) == GATE_CONFIG_IDS[layout], (
            f"{layout}: derived config ids no longer match the frozen set. If "
            "this is an intended identity change, it needs a Change Record and "
            "an IDENTITY_VERSION bump, not a test update."
        )


def test_a_configuration_spans_the_six_registered_sizes():
    """A configuration is six units, not one — the curve runs *across* them."""
    for layout in GATE_LAYOUTS:
        units = gate_units(layout)
        assert tuple(u.n_transitions for u in units) == tuple(SIZES)
        assert {u.layout for u in units} == {layout}
        assert {u.causal_attribute for u in units} == {"shape"}
        assert {u.confound_rate for u in units} == {0.0}
        assert len(set(GATE_CONFIG_IDS[layout])) == 6, "config ids must be distinct"


def test_the_three_configurations_vary_only_the_layout():
    """Causal rule and confounding held fixed, so the gate tests the estimator."""
    ids = {layout: set(GATE_CONFIG_IDS[layout]) for layout in GATE_LAYOUTS}
    assert len(set.union(*ids.values())) == 18, "configurations share a unit"
    assert set(GATE_LAYOUTS) == {"uniform", "clustered", "sparse"}


# --- eligibility ----------------------------------------------------------


def test_exactly_three_predeclared_configurations():
    with pytest.raises(ValueError, match="exactly the three predeclared"):
        reliability_gate({"uniform": curves(FALLING)}, rung=0)

    extra = all_configurations()
    extra["dense"] = curves(FALLING)
    with pytest.raises(ValueError, match="exactly the three predeclared"):
        reliability_gate(extra, rung=0)

    substituted = all_configurations()
    substituted["elsewhere"] = substituted.pop("sparse")
    with pytest.raises(ValueError, match="exactly the three predeclared"):
        reliability_gate(substituted, rung=0)


@pytest.mark.parametrize(
    "seeds, why",
    [
        ((0, 1, 2), "the three-seed pilot is not a gate result"),
        ((0, 1, 2, 3), "four seeds is not five"),
        ((0, 1, 2, 3, 4, 5), "six seeds is not five"),
        ((0, 1, 2, 3, 7), "a substituted seed is not the registered set"),
    ],
)
def test_exactly_five_development_seeds(seeds, why):
    """The pilot's three seeds cannot become a gate verdict by being rerun."""
    bad = all_configurations()
    bad["clustered"] = curves(FALLING, seeds=seeds)
    with pytest.raises(ValueError, match="the gate requires"):
        reliability_gate(bad, rung=0)


def test_the_gate_refuses_confirmatory_seeds():
    """Estimator selection must not consume the verdict's evidence."""
    conf = tuple(K.CONFIRMATORY_SEED_BASE + i for i in range(5))
    bad = all_configurations()
    bad["uniform"] = curves(FALLING, seeds=conf)
    with pytest.raises(ValueError, match="the gate requires|development-only"):
        reliability_gate(bad, rung=0)


def test_an_unknown_rung_is_refused():
    with pytest.raises(ValueError, match="rung must be one of"):
        reliability_gate(all_configurations(), rung=5)


def test_an_incomplete_curve_is_still_refused_downstream():
    """The wrapper does not weaken any of `trend_test`'s refusals."""
    bad = all_configurations()
    del bad["sparse"][GATE_SEEDS[0]][SIZES[2]]
    with pytest.raises(ValueError, match="missing dataset sizes"):
        reliability_gate(bad, rung=0)


# --- aggregation ----------------------------------------------------------


def test_rung_zero_passes_only_when_all_three_pass():
    result = reliability_gate(all_configurations(FALLING), rung=0)
    assert result.passed
    assert len(result.per_configuration) == 3
    assert all(r.passed for r in result.per_configuration.values())
    assert result.estimator == "ensemble"


def test_one_failing_configuration_fails_the_rung():
    """No majority vote. Configuration sensitivity IS a reliability failure."""
    mixed = all_configurations(FALLING, sparse=RISING)
    result = reliability_gate(mixed, rung=0)

    assert not result.passed
    assert result.per_configuration["uniform"].passed
    assert result.per_configuration["clustered"].passed
    assert not result.per_configuration["sparse"].passed
    assert "1 of 3 configurations failed (sparse)" in result.reason
    assert "no majority vote" in result.reason


def test_every_configuration_result_is_preserved():
    """All three coefficients and intervals are reported, never reduced."""
    mixed = all_configurations(FALLING, sparse=RISING)
    row = reliability_gate(mixed, rung=0).as_row()

    assert set(row["configurations"]) == set(GATE_LAYOUTS)
    for name in GATE_LAYOUTS:
        entry = row["configurations"][name]
        assert "rho" in entry and "ci_low" in entry and "ci_high" in entry
        assert entry["partition"] == "development"
        assert entry["n_resamples"] == 5 ** 5
    assert row["aggregation"] == "all_configurations_must_pass"


def test_curves_are_never_pooled_across_configurations():
    """Pooling would let a strong layout carry a weak one.

    Constructed so the *pooled* curve would pass while one configuration on its
    own does not — the gate must report the failure, not the average.
    """
    mixed = all_configurations(
        [0.90, 0.70, 0.50, 0.40, 0.30, 0.20], sparse=[0.20, 0.30, 0.40, 0.50, 0.55, 0.60]
    )
    result = reliability_gate(mixed, rung=0)
    assert not result.passed
    assert not result.per_configuration["sparse"].passed
    # Each configuration's own seeds only: five blocks, not fifteen.
    for r in result.per_configuration.values():
        assert r.seeds == GATE_SEEDS
        assert r.n_resamples == 5 ** 5


# --- the rung on the record ------------------------------------------------


def test_the_rung_and_estimator_travel_with_the_verdict():
    """"Passed at rung 0" and "passed at rung 3" are different claims."""
    for rung, name in RUNGS.items():
        result = reliability_gate(all_configurations(FALLING), rung=rung)
        assert result.rung == rung
        assert result.estimator == name
        assert result.as_row()["rung"] == rung
        assert result.as_row()["estimator"] == name


def test_reaching_rung_three_reports_h1_falsified_for_ensembles():
    """P§11.3: a pass at rung 3 or 4 is a secondary path, not a clean pass."""
    high = reliability_gate(all_configurations(FALLING), rung=3)
    assert high.passed
    assert "FALSIFIED FOR" in high.summary()
    assert "secondary" in high.summary()

    low = reliability_gate(all_configurations(FALLING), rung=0)
    assert "FALSIFIED FOR" not in low.summary()


def test_the_record_states_the_partition_and_the_aggregation_rule():
    row = reliability_gate(all_configurations(FALLING), rung=0).as_row()
    assert row["partition"] == "development"
    assert row["seeds"] == list(GATE_SEEDS)
    assert row["config_ids"]["uniform"] == list(GATE_CONFIG_IDS["uniform"])
