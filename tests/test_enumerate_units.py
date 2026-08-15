"""Week 2 Tuesday: the configuration-condition enumerator.

"Done when: enumerator returns >=300 configuration-conditions and prints the
count by axis." Plus the arithmetic that must agree with Plan §14.2, and the
deduplication rule Sol's Q-003 ruling imposed.
"""

from __future__ import annotations

from collections import Counter

import pytest

from bu import constants as K
from bu.config import Config, UnitSpec
from bu.experiments.enumerate_units import (
    CANONICAL_PAIRS,
    _intended_class,
    arms_for,
    canonical_units,
    count_by_axis,
    deduplicate,
    design_units,
    experiment_1_units,
    experiment_2a_units,
    experiment_2b_units,
    full_matrix,
    obligations,
    repair_validation_units,
    select_sweep,
    summarise,
    total_model_fits,
)


def ids(units) -> set[str]:
    return {Config(unit=u).unit_id for u in units}


# --- the acceptance criterion ---------------------------------------------


def test_enumerator_returns_at_least_three_hundred_units():
    assert len(full_matrix()) >= K.MIN_LABELLED_UNITS


def test_summary_prints_the_count_by_axis():
    text = summarise(design_units())
    for axis in ("causal_attribute", "layout", "confound_rate", "family"):
        assert axis in text
    assert "distinct statistical units" in text


# --- counts must agree with Plan §14.2 ------------------------------------


def test_canonical_counts_match_the_plan():
    """Plan §14.2: 6x5=30, 4x5=20, 5x5=25."""
    assert len(experiment_1_units()) == 30
    assert len(experiment_2a_units()) == 20
    assert len(experiment_2b_units()) == 25
    assert len(canonical_units()) == 75
    assert len(CANONICAL_PAIRS) == 5


def test_repair_validation_is_fifteen_conditions():
    """Plan §14.2: "15 canonical conditions at full seed count"."""
    assert len(repair_validation_units()) == 15
    assert len(ids(repair_validation_units())) == 15


def test_design_hits_three_hundred_units():
    assert len(design_units()) == 300


def test_compute_stays_within_the_planned_budget():
    """A design that does not fit the compute budget is not the planned design.

    Repairs cost one model fit, not an ensemble: the Plan §7.3 acceptance test
    compares per-transition error and needs no member spread. Costing them as
    ensembles inflates the estimate five-fold.
    """
    fits = total_model_fits(design_units())
    assert fits["total"] <= 8700, fits
    assert fits["baseline_ensembles"] == 6750


# --- Sol's Q-003 ruling, enforced (D-007) ---------------------------------


def test_units_are_deduplicated_by_unit_id():
    units = full_matrix()
    assert len(ids(units)) == len(units)


def test_experiment_2a_units_are_inside_the_matrix_not_additional():
    """The four 2A confound levels identify units the sweep also contains.

    Counting them twice would inflate the effective sample size and invalidate
    the power calculation -- Sol's Q-003 answer, recorded as D-007.
    """
    assert ids(experiment_2a_units()) <= ids(full_matrix())
    combined = deduplicate(list(full_matrix()) + list(experiment_2a_units()))
    assert len(combined) == len(full_matrix()), "re-adding 2A must not grow the matrix"


def test_deduplicate_collapses_a_repeated_unit():
    u = UnitSpec()
    assert len(deduplicate([u, UnitSpec(), u])) == 1


# --- stage obligations: dedupe units, never dedupe obligations (D-012) ----


def test_a_unit_can_hold_two_obligations():
    obs = obligations(design_units())
    by_unit: Counter[str] = Counter(o.unit_id for o in obs)
    doubled = [uid for uid, n in by_unit.items() if n > 1]
    assert doubled, "repair-validation units must also hold a canonical stage"
    for uid in doubled:
        stages = {o.stage for o in obs if o.unit_id == uid}
        assert "repair_validation" in stages
        assert len(stages) == 2


def test_obligation_seed_counts_follow_the_stage():
    for ob in obligations(design_units()):
        assert ob.seeds == {
            "exp1": 5, "exp2a": 5, "exp2b": 5,
            "config_sweep": 3, "repair_validation": 20,
        }[ob.stage]


def test_every_unit_has_at_least_one_obligation():
    units = design_units()
    assert {o.unit_id for o in obligations(units)} == ids(units)


def test_obligation_counts_match_the_plan():
    counts = Counter(o.stage for o in obligations(design_units()))
    assert counts["exp1"] == 30
    assert counts["exp2a"] == 20
    assert counts["exp2b"] == 25
    assert counts["repair_validation"] == 15
    assert counts["config_sweep"] == 225


# --- the design is balanced where power depends on it ---------------------


def test_intended_classes_are_balanced():
    """Power depends on min(N0, N1), not the total (Plan §10.7).

    Balanced on *intended* class only. Real labels come from the repair test,
    and the ambiguous and undiagnosed cells will shrink both counts.
    """
    counts = Counter(_intended_class(u) for u in design_units())
    assert min(counts.values()) >= 140
    assert abs(counts[0] - counts[1]) <= 10


@pytest.mark.parametrize("axis", ["causal_attribute", "layout", "confound_rate"])
def test_no_axis_level_is_starved_by_truncation(axis):
    """A truncated sweep must not collapse an axis.

    Stratifying without confound gave 99 units at 0.0 and 9 at 0.9 -- the
    strongest shortcut condition nearly absent from the sweep.
    """
    counts = count_by_axis(design_units())[axis]
    assert min(counts.values()) >= 0.4 * max(counts.values()), counts


def test_selection_is_deterministic():
    assert ids(design_units()) == ids(design_units())
    assert [u for u in select_sweep(50)] == [u for u in select_sweep(50)]


def test_selection_respects_the_requested_size():
    for n in (10, 100, 225):
        assert len(select_sweep(n)) == n


# --- the units mean what they say -----------------------------------------


def test_2a_units_withhold_their_own_causal_attribute():
    for u in experiment_2a_units():
        assert u.withheld_features == (u.causal_attribute,)
        assert u.confound_rate in K.CONFOUND_LEVELS_2A
        assert u.n_transitions == max(K.DATA_SIZES), "data insufficiency ruled out"


def test_2b_units_supply_complete_features():
    for u in experiment_2b_units():
        assert u.withheld_features == ()
        assert u.hidden_size in K.HIDDEN_SIZES
        assert u.n_transitions == max(K.DATA_SIZES)


def test_experiment_1_sweeps_exactly_the_planned_data_sizes():
    assert {u.n_transitions for u in experiment_1_units()} == set(K.DATA_SIZES)
    for u in experiment_1_units():
        assert u.withheld_features == () and u.hidden_size == max(K.HIDDEN_SIZES)


def test_missing_feature_units_never_use_zero_confound():
    """At zero confound there is no decoy to substitute for the withheld cause,
    so the condition is not the shortcut construction Plan §8.2.1 describes."""
    for u in full_matrix():
        if u.family == "missing_feature":
            assert u.confound_rate in K.CONFOUND_LEVELS_2A


def test_arms_are_the_meaningful_ones_only():
    """Each repair targets one mechanism, and only where there is one to fix."""
    est = UnitSpec(family="estimation", hidden_size=256)
    assert arms_for(est) == ("baseline", "data_repair")

    miss = UnitSpec(family="missing_feature", withheld_features=("shape",))
    assert set(arms_for(miss)) == {"baseline", "data_repair", "feature_repair"}

    cap = UnitSpec(family="capacity", hidden_size=16)
    assert set(arms_for(cap)) == {"baseline", "data_repair", "capacity_repair"}


def test_every_enumerated_unit_builds_a_valid_config():
    """Every unit must survive Config construction, including its arms.

    Config validates arms at build time (the audit's fail-fast change), so this
    catches an enumerated unit whose repair is impossible before a batch runner
    meets it on Kaggle.
    """
    from bu.config import Arm

    for u in design_units():
        for arm in arms_for(u):
            Config(unit=u, arm=Arm(arm), stage="config_sweep")
