"""Named random streams: the Q-008 ruling, as properties (D-030).

Sol's answer to Q-008 is not one rule but a tension between two, and a test file
that checked only independence would pass while destroying the design. Both
directions are asserted here:

* **independent across units** -- confidence intervals are taken over
  configuration-conditions, so correlated environments would understate
  between-unit variance;
* **paired within a comparison** -- a data-size sweep must vary the amount of
  data and nothing else, a capacity sweep must train on the same datasets, and a
  repair must be evaluated against the same recorded failure set as its baseline.

The failure mode a single seed produced -- ``GridWorld.reset(seed=s)`` deriving
everything from ``s`` -- satisfied the second and violated the first.
"""

from __future__ import annotations

import numpy as np
import pytest

from bu import constants as K
from bu.config import ARMS, Arm, Config, UnitSpec
from bu.env.collect import collect
from bu.streams import (
    DATA_PURPOSES,
    MANIPULATED_AXIS,
    PURPOSES,
    comparison_group_id,
    confirmatory_seeds,
    is_confirmatory,
    stream,
    stream_key,
)

SEED = K.CONFIRMATORY_SEED_BASE
ESTIMATION = dict(
    causal_attribute="shape", layout="uniform", confound_rate=0.0, family="estimation"
)


# --- independence across units --------------------------------------------


def test_units_in_different_groups_draw_independent_environments():
    """Q-008 as raised: seed 0 in two different units gave correlated layouts.

    Stated over units in *different* comparison groups, which is the only form
    of the claim that is true. Units inside one group are intentionally
    dependent -- see the grouped-dependence tests below and D-039.
    """
    a = UnitSpec(**ESTIMATION, n_transitions=500)
    b = UnitSpec(
        causal_attribute="colour", layout="sparse", confound_rate=0.5,
        family="estimation", n_transitions=500,
    )
    da = collect(a, stage="config_sweep", seed=SEED)
    db = collect(b, stage="config_sweep", seed=SEED)
    assert not np.array_equal(da.obs, db.obs)
    assert comparison_group_id(a, "config_sweep") != comparison_group_id(b, "config_sweep")


def test_sweep_only_units_have_no_comparison_group():
    """No manipulated axis means no group: the independence case."""
    unit = UnitSpec(**ESTIMATION, n_transitions=500)
    assert comparison_group_id(unit, "config_sweep") == Config(unit=unit).unit_id
    assert "config_sweep" not in MANIPULATED_AXIS


# --- pairing within a comparison ------------------------------------------


def test_experiment_1_datasets_are_nested_prefixes():
    """The property that makes the data-size sweep vary only the data size.

    Collecting 250 transitions must reproduce the first 100 exactly. It holds
    because the generator *flows* across episodes rather than being reseeded per
    episode, and because ``n_transitions`` is the axis excluded from the group.
    """
    small = collect(UnitSpec(**ESTIMATION, n_transitions=100), stage="exp1", seed=SEED)
    large = collect(UnitSpec(**ESTIMATION, n_transitions=250), stage="exp1", seed=SEED)
    assert np.array_equal(small.obs, large.obs[: len(small)])
    assert np.array_equal(small.action, large.action[: len(small)])
    assert np.array_equal(small.next_obs, large.next_obs[: len(small)])


def test_capacity_levels_train_on_the_same_data():
    """Experiment 2B varies capacity; the dataset must not move underneath it."""
    cap = dict(
        causal_attribute="shape", layout="uniform", confound_rate=0.0,
        family="capacity", n_transitions=5000,
    )
    keys = {
        comparison_group_id(UnitSpec(**cap, hidden_size=h), "exp2b")
        for h in K.HIDDEN_SIZES
    }
    assert len(keys) == 1


def test_confound_levels_share_their_underlying_draws():
    """Experiment 2A must change the confound mechanism and nothing else."""
    mf = dict(
        causal_attribute="shape", layout="uniform", family="missing_feature",
        withheld_features=("shape",), n_transitions=5000,
    )
    keys = {
        comparison_group_id(UnitSpec(**mf, confound_rate=c), "exp2a")
        for c in K.CONFOUND_LEVELS_2A
    }
    assert len(keys) == 1


@pytest.mark.parametrize("purpose", sorted(PURPOSES))
def test_the_arm_never_enters_a_stream_key(purpose: str):
    """Baseline and repairs must share the recorded failure set (P§7.2 step 4).

    Stated over the key rather than over one arm, so a future arm cannot slip
    in. Note the key is built from the *unresolved* unit — passing
    ``effective_unit`` would put the repair's enlarged dataset into the key and
    silently unpair the acceptance test.
    """
    # A unit every arm is meaningful on: something withheld to restore, and
    # capacity below the maximum to add to.
    unit = UnitSpec(
        causal_attribute="shape", layout="uniform", confound_rate=0.5,
        family="missing_feature", withheld_features=("shape",),
        n_transitions=500, hidden_size=16,
    )
    keys = {str(stream_key(Config(unit=unit, arm=Arm(a)).unit, "exp2a", purpose)) for a in ARMS}
    assert len(keys) == 1, "the arm reached the stream key"

    # And the control that shows why the *unresolved* unit is the right input:
    # keying on the repaired unit would give each arm its own stream.
    resolved = {str(stream_key(Arm(a).resolve(unit), "exp2a", purpose)) for a in ARMS}
    assert len(resolved) > 1, (
        "resolving the arm no longer changes the unit, so this test would pass "
        "even if the key were built from effective_unit"
    )


def test_a_data_repair_extends_the_baseline_rather_than_redrawing():
    """The 10x dataset must begin with the baseline's own transitions."""
    unit = UnitSpec(**ESTIMATION, n_transitions=100)
    repaired = Arm("data_repair").resolve(unit)
    assert repaired.n_transitions == unit.n_transitions * K.DATA_REPAIR_MULTIPLIER
    base = collect(unit, stage="exp1", seed=SEED)
    more = collect(repaired, stage="exp1", seed=SEED)
    assert np.array_equal(base.obs, more.obs[: len(base)])


# --- what must NOT be in a key --------------------------------------------


def test_stage_never_enters_a_stream_key():
    """D-033 rests on this: one fit, several roles.

    If stage reached the computation, a unit's five canonical seeds and the
    first five of its twenty validation seeds would be different models, and
    deduplicating them would be wrong rather than merely economical.
    """
    unit = UnitSpec(**ESTIMATION, n_transitions=100)
    for purpose in PURPOSES:
        a = stream_key(unit, "exp1", purpose)
        b = stream_key(unit, "repair_validation", purpose)
        assert a == b, purpose


def test_the_named_streams_are_independent_of_one_another():
    """A change to how one stream is consumed must not shift another."""
    unit = UnitSpec(**ESTIMATION, n_transitions=100)
    draws = {p: stream(unit, "exp1", p, SEED).random(8).tobytes() for p in PURPOSES}
    assert len(set(draws.values())) == len(PURPOSES)


def test_ensemble_members_draw_differently():
    unit = UnitSpec(**ESTIMATION, n_transitions=100)
    a = stream(unit, "exp1", "init", SEED, member=0).random(8)
    b = stream(unit, "exp1", "init", SEED, member=1).random(8)
    assert not np.array_equal(a, b)


def test_model_side_streams_do_not_key_on_the_comparison_group():
    """Bootstrap and init are per-unit: sharing *data* is the point, not weights."""
    for purpose in PURPOSES:
        key = stream_key(UnitSpec(**ESTIMATION, n_transitions=100), "exp1", purpose)
        assert ("group" in key) == (purpose in DATA_PURPOSES)


def test_an_unknown_purpose_is_rejected():
    with pytest.raises(ValueError, match="unknown stream purpose"):
        stream_key(UnitSpec(), "exp1", "vibes")


def test_streams_are_reproducible_across_processes():
    """Hash-derived, so no process-local state can reach the numbers."""
    import subprocess
    import sys

    code = (
        "from bu.config import UnitSpec; from bu.streams import stream; "
        "print(stream(UnitSpec(n_transitions=100), 'exp1', 'env', 1000).random())"
    )
    got = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    here = stream(UnitSpec(n_transitions=100), "exp1", "env", 1000).random()
    assert float(got) == here


# --- the pilot boundary (D-034) -------------------------------------------


def test_development_seeds_are_not_confirmatory():
    assert not is_confirmatory(0)
    assert not is_confirmatory(K.CONFIRMATORY_SEED_BASE - 1)
    assert is_confirmatory(K.CONFIRMATORY_SEED_BASE)


def test_confirmatory_seeds_start_above_everything_ever_inspected():
    """Every dataset looked at during development lies below the line.

    The Week 2 coverage evidence and the identity-predictor probe both shaped
    design decisions, and data that shaped a choice cannot also test it.
    """
    seeds = confirmatory_seeds(K.SEEDS_REPAIR_VALIDATION)
    assert len(seeds) == K.SEEDS_REPAIR_VALIDATION
    assert all(is_confirmatory(s) for s in seeds)
    assert min(seeds) == K.CONFIRMATORY_SEED_BASE


def test_the_hypothesis_seed_block_is_a_prefix_of_the_validation_block():
    """D-033's overlap, at the level of actual seed values."""
    assert (
        confirmatory_seeds(K.SEEDS_HYPOTHESIS)
        == confirmatory_seeds(K.SEEDS_REPAIR_VALIDATION)[: K.SEEDS_HYPOTHESIS]
    )


# --- grouped dependence (Sol review of delta 12 · D-039) ------------------
#
# The cost of common random numbers: units sharing a group are DEPENDENT by
# design. Every split and every interval has to respect that, or H3 is
# evaluated on near-identical trajectories sitting on both sides of a split.


def test_the_canonical_design_collapses_into_fifteen_groups():
    from bu.experiments.enumerate_units import canonical_units, comparison_groups

    groups = comparison_groups(canonical_units())
    assert len(canonical_units()) == 75
    assert len(groups) == 15, "5 configs x 3 canonical experiments"


def test_sweep_units_are_singleton_groups():
    """Independence genuinely holds there, so the rule must not over-cluster."""
    from bu.experiments.enumerate_units import (
        canonical_units, comparison_groups, design_units)

    canon = {Config(unit=u).unit_id for u in canonical_units()}
    sweep = tuple(u for u in design_units() if Config(unit=u).unit_id not in canon)
    groups = comparison_groups(sweep)
    assert len(groups) == len(sweep) == 225
    assert all(len(v) == 1 for v in groups.values())


def test_a_group_never_spans_both_intended_classes():
    """A group is atomic for splitting, so a mixed group could not be assigned."""
    from bu.experiments.enumerate_units import comparison_groups, design_units

    for members in comparison_groups(design_units()).values():
        classes = {0 if u.family == "estimation" else 1 for u in members}
        assert len(classes) == 1


def test_group_level_balance_is_reported_and_is_not_the_unit_level_balance():
    """The number that matters for power is not the one the design advertises.

    Plan §10.7 makes power depend on min(N0, N1). At unit level the design is
    150/150; at the level that is actually independent it is 125/115. Pinned so
    the Week 5 MDE simulation cannot quietly resolve over 300 unit ids.
    """
    from collections import Counter

    from bu.experiments.enumerate_units import comparison_groups, design_units

    groups = comparison_groups(design_units())
    assert len(groups) == 240
    counts = Counter(
        0 if members[0].family == "estimation" else 1 for members in groups.values()
    )
    assert (counts[0], counts[1]) == (125, 115)
    assert min(counts.values()) < 150


# --- the multi-role stream invariant (D-038) ------------------------------


def test_every_multi_role_fit_resolves_to_one_set_of_streams():
    """Exhaustive over the plan, not over an example.

    fit_id deduplicates on (unit, arm, seed). If two roles on one fit needed
    different data, that deduplication would be wrong rather than economical.
    """
    from bu.experiments.enumerate_units import design_units, execution_plan
    from bu.streams import stream_key

    checked = 0
    for fit in execution_plan(design_units()):
        if len(fit.roles) < 2:
            continue
        checked += 1
        for purpose in PURPOSES:
            keys = {str(stream_key(fit.unit, role, purpose)) for role in fit.roles}
            assert len(keys) == 1, (fit.fit_id, fit.roles, purpose)
    assert checked == 75, "expected the 15 ladder units x 5 shared seeds"


def test_incompatible_roles_are_rejected_rather_than_merged():
    """The invariant must bite, not merely hold by luck today.

    It currently holds because no canonical unit also carries a config_sweep
    obligation. That is a property of this enumeration, not of the design, so
    it is asserted against a constructed violation.
    """
    from bu.streams import assert_roles_share_one_stream

    unit = UnitSpec(**ESTIMATION, n_transitions=100)
    assert_roles_share_one_stream(unit, ("exp1", "repair_validation"))  # compatible
    with pytest.raises(ValueError, match="different 'env' streams"):
        assert_roles_share_one_stream(unit, ("exp1", "config_sweep"))


# --- the pilot boundary is enforced, not merely checkable (D-040) ---------


def test_development_seeds_are_rejected_by_confirmatory_analyses():
    from bu.streams import assert_confirmatory

    assert_confirmatory(confirmatory_seeds(5), what="test")
    with pytest.raises(ValueError, match="development seeds"):
        assert_confirmatory([0, 1, 2], what="threshold calibration")


def test_a_mixed_batch_fails_closed():
    """Silently dropping development rows would leave an analysis computed on
    fewer units than it reports."""
    from bu.streams import assert_confirmatory

    with pytest.raises(ValueError, match="mixed with confirmatory"):
        assert_confirmatory([0, K.CONFIRMATORY_SEED_BASE], what="repair acceptance")


def test_an_empty_batch_is_not_an_error():
    from bu.streams import assert_confirmatory

    assert_confirmatory([], what="test")


def test_seed_partition_names_both_sides():
    from bu.streams import seed_partition

    assert seed_partition(0) == "development"
    assert seed_partition(K.CONFIRMATORY_SEED_BASE) == "confirmatory"
