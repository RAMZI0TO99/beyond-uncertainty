"""The repair path (P§7.2, S§W5 Mon).

D-055's lesson governs this file: **one arm passing is not evidence about
another.** Repair pairing held for data and capacity repair because their
experiments exclude the field those repairs change; feature repair changes a
field Experiment 2A does not exclude, and broke. Every pairing property here is
therefore parametrised over every applicable arm.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bu.config import Arm, UnitSpec
from bu.env.collect import collect_pools
from bu.experiments.repair import (
    REPAIR_STAGE, acceptance_inputs, applicable_arms, evaluate_arm,
)
from bu.models.world_model import WorldModel

# Withheld feature and headroom, so all three repairs apply.
UNIT = UnitSpec(n_transitions=250, withheld_features=("shape",), hidden_size=64)
REPAIRS = ("data_repair", "feature_repair", "capacity_repair")


# --- which repairs apply --------------------------------------------------


def test_applicable_arms_reports_rather_than_raises():
    assert applicable_arms(UNIT) == REPAIRS
    assert "feature_repair" not in applicable_arms(UnitSpec(hidden_size=64))
    assert applicable_arms(UnitSpec(hidden_size=max((16, 32, 64, 128, 256)))) == ("data_repair",)


# --- what makes the comparison paired, for EVERY arm ----------------------


@pytest.mark.parametrize("arm", REPAIRS)
def test_every_arm_draws_the_same_evaluation_transitions(arm):
    """The pool is keyed on the UNRESOLVED unit, so all arms share it (D-055)."""
    base = collect_pools(UNIT, stage=REPAIR_STAGE, seed=0, arm="baseline").evaluation
    rep = collect_pools(UNIT, stage=REPAIR_STAGE, seed=0, arm=arm).evaluation

    assert len(base) == len(rep)
    assert np.array_equal(base.episode, rep.episode)
    assert np.array_equal(base.step, rep.step)
    assert np.array_equal(base.action, rep.action)


@pytest.mark.parametrize("arm", REPAIRS)
def test_every_arm_predicts_the_same_targets(arm):
    """Feature repair widens the observation encoding. The targets must not move.

    This is the property the acceptance test actually depends on: errors from
    two arms are only comparable if they are errors against the same targets.
    Feature repair takes the encoding from 22 columns to 30, so the fact that
    the *targets* coincide is a real claim about the dynamic/static split
    (D-032), not a restatement of the pooling.
    """
    base_pools = collect_pools(UNIT, stage=REPAIR_STAGE, seed=0, arm="baseline")
    rep_pools = collect_pools(UNIT, stage=REPAIR_STAGE, seed=0, arm=arm)

    base_model = WorldModel(UNIT, np.random.default_rng(0))
    rep_model = WorldModel(Arm(arm).resolve(UNIT), np.random.default_rng(0))

    base_targets = base_model.targets(torch.as_tensor(base_pools.evaluation.next_obs))[0]
    rep_targets = rep_model.targets(torch.as_tensor(rep_pools.evaluation.next_obs))[0]

    assert torch.equal(base_targets, rep_targets), (
        f"{arm} changes the prediction targets, so its per-transition errors are "
        "not comparable with the baseline's and the acceptance test is invalid"
    )


def test_feature_repair_really_does_widen_the_encoding():
    """Guards the test above from becoming vacuous.

    If feature repair ever stopped changing the observation width, the target
    test would still pass while no longer demonstrating anything.
    """
    base = collect_pools(UNIT, stage=REPAIR_STAGE, seed=0, arm="baseline").evaluation
    rep = collect_pools(UNIT, stage=REPAIR_STAGE, seed=0, arm="feature_repair").evaluation
    assert rep.obs.shape[1] > base.obs.shape[1]


# --- the scale is not the repaired arm's own ------------------------------


@pytest.mark.parametrize("arm", REPAIRS)
def test_a_repaired_arm_without_a_scale_is_refused(arm):
    """D-061: a repaired arm scored in its own units is the defect that ruling closed."""
    with pytest.raises(ValueError, match="was given no scale"):
        evaluate_arm(UNIT, arm=arm, seed=0)


# --- assembling the paired arrays ------------------------------------------


def fake(arm, seed, *, n=40, scale=object(), episode=None, step=None):
    from bu.experiments.repair import ArmEvaluation

    episode = np.arange(n) // 10 if episode is None else episode
    step = np.arange(n) % 10 if step is None else step
    return ArmEvaluation(
        arm=arm, seed=seed, error=np.linspace(1.0, 2.0, n), episode=episode,
        step=step, scale=scale, config_id="c", run_id="r", n_train=100,
    )


def test_the_arrays_are_paired_per_seed():
    scale = object()
    base = [fake("baseline", s, scale=scale) for s in (0, 1)]
    rep = [fake("data_repair", s, scale=scale) for s in (0, 1)]
    out = acceptance_inputs(base, rep)

    assert len(out["errors"]) == 160
    assert set(np.unique(out["repair"])) == {0, 1}
    assert set(np.unique(out["seed"])) == {0, 1}
    for seed in (0, 1):
        rows = out["seed"] == seed
        assert (out["repair"][rows] == 0).sum() == (out["repair"][rows] == 1).sum()


def test_mismatched_seeds_are_refused():
    scale = object()
    with pytest.raises(ValueError, match="is paired with"):
        acceptance_inputs([fake("baseline", 0, scale=scale)],
                          [fake("data_repair", 7, scale=scale)])


def test_a_different_number_of_seeds_is_refused():
    scale = object()
    with pytest.raises(ValueError, match="the same seeds on both arms"):
        acceptance_inputs([fake("baseline", 0, scale=scale)],
                          [fake("data_repair", 0, scale=scale),
                           fake("data_repair", 1, scale=scale)])


def test_arms_scored_on_different_transitions_are_refused():
    scale = object()
    base = [fake("baseline", 0, scale=scale)]
    rep = [fake("data_repair", 0, scale=scale, episode=np.arange(40) // 5)]
    with pytest.raises(ValueError, match="not the same transitions"):
        acceptance_inputs(base, rep)


def test_arms_carrying_different_scale_objects_are_refused():
    """Identity, not equality: two equal scales can still be two measurements."""
    with pytest.raises(ValueError, match="different scale objects"):
        acceptance_inputs([fake("baseline", 0, scale=object())],
                          [fake("data_repair", 0, scale=object())])


def test_a_non_baseline_first_list_is_refused():
    scale = object()
    with pytest.raises(ValueError, match="baseline list carries arm"):
        acceptance_inputs([fake("data_repair", 0, scale=scale)],
                          [fake("data_repair", 0, scale=scale)])


# --- the failure mask -------------------------------------------------------


def test_the_failure_mask_selects_the_same_set_on_both_arms():
    scale = object()
    mask = np.zeros(40, dtype=bool)
    mask[:12] = True
    out = acceptance_inputs([fake("baseline", 0, scale=scale)],
                            [fake("data_repair", 0, scale=scale)], failure_mask=mask)
    assert len(out["errors"]) == 24
    assert (out["repair"] == 0).sum() == (out["repair"] == 1).sum() == 12


@pytest.mark.parametrize(
    "mask, match",
    [
        (np.zeros(40, dtype=bool), "failure set is empty"),
        (np.ones(39, dtype=bool), "movement transitions"),
        (np.arange(40), "must be boolean"),
    ],
)
def test_a_bad_failure_mask_is_refused(mask, match):
    scale = object()
    with pytest.raises(ValueError, match=match):
        acceptance_inputs([fake("baseline", 0, scale=scale)],
                          [fake("data_repair", 0, scale=scale)], failure_mask=mask)


def test_no_mask_is_the_whole_pool_and_is_not_the_registered_comparison():
    """Scoring the whole pool is a diagnostic; the registered test is masked."""
    scale = object()
    out = acceptance_inputs([fake("baseline", 0, scale=scale)],
                            [fake("data_repair", 0, scale=scale)])
    assert len(out["errors"]) == 80
