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

from bu import constants as K
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
        evaluate_arm(UNIT, arm=arm, seed=K.CONFIRMATORY_SEED_BASE)


# --- assembling the paired arrays ------------------------------------------


def fake(arm, seed, *, n=40, scale=object(), episode=None, step=None, stage=None,
         ensemble_size=1):
    """A synthetic evaluation.

    `stage` defaults to the exploratory one because these ARE fakes, not
    registered evidence -- and since C-007 the repair path refuses development
    seeds on a registered stage. Labelling the fixture honestly keeps these
    mechanics tests about masks and pairing, and leaves the seed policy to the
    tests written for it below.
    """
    from bu.experiments.repair import ArmEvaluation, EXPLORATORY_STAGE

    episode = np.arange(n) // 10 if episode is None else episode
    step = np.arange(n) % 10 if step is None else step
    return ArmEvaluation(
        arm=arm, seed=seed, error=np.linspace(1.0, 2.0, n), episode=episode,
        step=step, scale=scale, config_id="c", run_id="r", n_train=100,
        stage=stage or EXPLORATORY_STAGE, ensemble_size=ensemble_size,
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
                            [fake("data_repair", 0, scale=scale)],
                            failure_masks={0: mask})
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
                          [fake("data_repair", 0, scale=scale)],
                          failure_masks={0: mask})


def test_no_mask_is_the_whole_pool_and_is_not_the_registered_comparison():
    """Scoring the whole pool is a diagnostic; the registered test is masked."""
    scale = object()
    out = acceptance_inputs([fake("baseline", 0, scale=scale)],
                            [fake("data_repair", 0, scale=scale)])
    assert len(out["errors"]) == 80


# --- seed-specific failure masks (Sol's ruling on the recovered repair path) --


def test_each_seed_gets_its_own_failure_mask():
    """Different seeds may fail on different transitions, and must be able to."""
    scale = object()
    m0 = np.zeros(40, dtype=bool); m0[:12] = True
    m1 = np.zeros(40, dtype=bool); m1[20:26] = True
    out = acceptance_inputs(
        [fake("baseline", 0, scale=scale), fake("baseline", 1, scale=scale)],
        [fake("data_repair", 0, scale=scale), fake("data_repair", 1, scale=scale)],
        failure_masks={0: m0, 1: m1},
    )
    # 12 failing transitions at seed 0 and 6 at seed 1, each scored on both arms.
    assert len(out["errors"]) == (12 + 6) * 2
    assert (out["seed"] == 0).sum() == 24
    assert (out["seed"] == 1).sum() == 12


def test_a_missing_seed_mask_is_refused():
    scale = object()
    mask = np.ones(40, dtype=bool)
    with pytest.raises(ValueError, match=r"no failure mask for seed\(s\) \[1\]"):
        acceptance_inputs(
            [fake("baseline", 0, scale=scale), fake("baseline", 1, scale=scale)],
            [fake("data_repair", 0, scale=scale), fake("data_repair", 1, scale=scale)],
            failure_masks={0: mask},
        )


def test_an_extra_seed_mask_is_refused():
    """Not harmless slack: the masks were built against a different seed set."""
    scale = object()
    mask = np.ones(40, dtype=bool)
    with pytest.raises(ValueError, match=r"seed\(s\) \[7\], which are not being scored"):
        acceptance_inputs(
            [fake("baseline", 0, scale=scale)],
            [fake("data_repair", 0, scale=scale)],
            failure_masks={0: mask, 7: mask},
        )


def test_a_bare_array_is_refused_rather_than_broadcast():
    """The withdrawn API took one array and applied it to every seed.

    It passed every length check while selecting a different transition set in
    each seed, because pools are the same LENGTH across seeds but not the same
    transitions. Refusing the type is what makes that unrepeatable.
    """
    scale = object()
    with pytest.raises(TypeError, match="seed -> mask mapping"):
        acceptance_inputs(
            [fake("baseline", 0, scale=scale)],
            [fake("data_repair", 0, scale=scale)],
            failure_masks=np.ones(40, dtype=bool),
        )


# --- one model per repaired arm (P§14.2) ------------------------------------


def test_a_repaired_arm_refuses_an_ensemble():
    """P§14.2 budgets ONE model per repaired arm; running K is a different study."""
    from bu.config import TrainConfig
    from bu.experiments.repair import evaluate_arm
    from bu.experiments.enumerate_units import canonical_units

    unit = canonical_units()[0]
    with pytest.raises(ValueError, match="budgets 1 model per repaired arm"):
        evaluate_arm(unit, arm="data_repair", seed=K.CONFIRMATORY_SEED_BASE,
                     train=TrainConfig(ensemble_size=5), scale=object())


def test_the_repaired_default_is_one_model_and_the_baseline_default_is_not():
    """The default differs by arm on purpose, and the difference is the budget."""
    from bu.config import TrainConfig
    from bu.experiments.repair import REPAIR_ENSEMBLE_SIZE
    from bu import constants as K

    assert REPAIR_ENSEMBLE_SIZE == 1
    assert TrainConfig().ensemble_size == K.DEFAULT_ENSEMBLE_SIZE != REPAIR_ENSEMBLE_SIZE


def test_the_budget_is_taken_at_one_model_per_repair():
    """The enumerator and the repair path must agree, or the estimate is fiction."""
    from bu.experiments.enumerate_units import execution_plan
    from bu.experiments.repair import REPAIR_ENSEMBLE_SIZE

    plan = execution_plan()
    repaired = [f for f in plan if f.arm != "baseline"]
    assert repaired, "no repaired arms in the plan; this test would be vacuous"
    assert all(f.members == REPAIR_ENSEMBLE_SIZE for f in repaired)


# --- C-007: the confirmatory guard at the repair-acceptance call site --------


def test_a_registered_repair_run_refuses_a_development_seed():
    """D-034 excludes development seeds from repair acceptance permanently.

    Refused before the fit: a development repair fit that reaches a label has
    already spent its compute and already carries the identity.
    """
    from bu.experiments.repair import evaluate_arm
    from bu.experiments.enumerate_units import canonical_units

    with pytest.raises(ValueError, match="development data but stage is"):
        evaluate_arm(canonical_units()[0], arm="baseline", seed=0)


def test_a_probe_must_call_itself_a_pilot_rather_than_flip_a_flag():
    """The policy is tied to the STAGE, not to a boolean a caller can pass.

    D-077 had to close two opt-outs that existed because a caller could say
    "not this time". A stage already declares which obligation a run discharges,
    so an exploratory run is labelled rather than exempted -- and it is then
    visibly not registered evidence.
    """
    import inspect
    from bu.experiments.repair import evaluate_arm

    params = inspect.signature(evaluate_arm).parameters
    assert "require_confirmatory" not in params
    assert "allow_development" not in params


def test_the_label_is_refused_where_it_would_be_BUILT_not_only_where_it_was_run():
    """Two layers, because evaluations can be constructed without evaluate_arm.

    `acceptance_inputs` is where a repair label actually comes into existence,
    so the guard is there as well as at the fit. A check only at the producer
    would be one the consumer could be handed around.
    """
    from bu.experiments.repair import REPAIR_STAGE

    scale = object()
    seeds = (0,) + REGISTERED_SEEDS[1:]      # one development seed among them
    base, rep, masks = registered_set(scale, seeds=seeds)
    with pytest.raises(ValueError, match="development data on a registered stage"):
        acceptance_inputs(base, rep, failure_masks=masks)


def test_confirmatory_seeds_on_a_registered_stage_are_accepted():
    """The guard must not refuse the thing it exists to protect."""
    from bu.experiments.repair import REPAIR_STAGE

    scale = object()
    base, rep, masks = registered_set(scale)
    out = acceptance_inputs(base, rep, failure_masks=masks)
    assert len(out["errors"]) == 2 * 40 * len(REGISTERED_SEEDS)


REGISTERED_SEEDS = tuple(K.CONFIRMATORY_SEED_BASE + i
                         for i in range(K.SEEDS_REPAIR_VALIDATION))


def registered_set(scale, *, arm="data_repair", seeds=REGISTERED_SEEDS, **kw):
    """A full registered comparison: the frozen 20-seed set on both arms."""
    base = [fake("baseline", s, scale=scale, stage=REPAIR_STAGE) for s in seeds]
    rep = [fake(arm, s, scale=scale, stage=REPAIR_STAGE, **kw) for s in seeds]
    masks = {s: np.ones(40, dtype=bool) for s in seeds}
    return base, rep, masks


# --- consumer-side refusals (Sol's ruling on delta 44) ----------------------


def test_whole_pool_scoring_is_refused_on_a_registered_stage():
    """Sol found this hole in one of MY OWN tests.

    `failure_masks=None` scores the whole evaluation pool, which is a diagnostic.
    P§7.2 step 4 evaluates every repair on the RECORDED FAILURE SET, so on a
    registered stage the mapping is mandatory. `None` survives only for pilot.
    """
    scale = object()
    base, rep, _ = registered_set(scale)
    with pytest.raises(ValueError, match="registered but no failure_masks"):
        acceptance_inputs(base, rep)


def test_whole_pool_scoring_is_still_available_for_a_probe():
    """The diagnostic must remain usable where it is honestly labelled."""
    scale = object()
    out = acceptance_inputs([fake("baseline", 0, scale=scale)],
                            [fake("data_repair", 0, scale=scale)])
    assert len(out["errors"]) == 80


def test_a_repaired_evaluation_attesting_an_ensemble_is_refused():
    """The producer enforces K=1; an ArmEvaluation can be built without it."""
    scale = object()
    base, rep, masks = registered_set(scale, ensemble_size=5)
    with pytest.raises(ValueError, match="attest an ensemble size other than 1"):
        acceptance_inputs(base, rep, failure_masks=masks)


def test_mixed_stages_are_refused():
    """One acceptance test is one obligation; a probe may not supply half a label."""
    scale = object()
    base, rep, masks = registered_set(scale)
    rep[0] = fake("data_repair", REGISTERED_SEEDS[0], scale=scale)   # pilot stage
    with pytest.raises(ValueError, match="mixed stages"):
        acceptance_inputs(base, rep, failure_masks=masks)


def test_two_repair_types_in_one_call_are_refused():
    """Different repairs are different interventions; pooling reports a treatment
    nobody applied."""
    scale = object()
    base, rep, masks = registered_set(scale)
    rep[1] = fake("feature_repair", REGISTERED_SEEDS[1], scale=scale, stage=REPAIR_STAGE)
    with pytest.raises(ValueError, match="Exactly one repair type per"):
        acceptance_inputs(base, rep, failure_masks=masks)


# --- the exact registered seed set (Sol, delta 45) --------------------------


@pytest.mark.parametrize("drop", [1, 5])
def test_a_short_seed_set_is_refused_at_label_creation(drop):
    """Nineteen seeds is a different, unregistered experiment."""
    scale = object()
    base, rep, masks = registered_set(scale, seeds=REGISTERED_SEEDS[:-drop])
    with pytest.raises(ValueError, match="registers exactly 20 seeds"):
        acceptance_inputs(base, rep, failure_masks=masks)


def test_arbitrary_confirmatory_seeds_are_refused():
    """Confirmatory is necessary but not sufficient: it must be THE frozen set."""
    scale = object()
    odd = tuple(K.CONFIRMATORY_SEED_BASE + 100 + i for i in range(20))
    base, rep, masks = registered_set(scale, seeds=odd)
    with pytest.raises(ValueError, match="unregistered"):
        acceptance_inputs(base, rep, failure_masks=masks)


def test_the_exact_frozen_set_is_accepted():
    scale = object()
    base, rep, masks = registered_set(scale)
    out = acceptance_inputs(base, rep, failure_masks=masks)
    assert sorted(set(out["seed"])) == list(REGISTERED_SEEDS)


# --- confirmatory evidence is not automatically repair evidence (delta 46) ---


@pytest.mark.parametrize("stage, n_seeds", [
    ("exp1", 5),
    ("threshold_calibration", 5),
    ("exp2a", 5),
    ("config_sweep", 3),
])
def test_another_registered_stage_cannot_create_a_repair_label(stage, n_seeds):
    """Sol, delta 46: an otherwise-valid registered input must be refused BY NAME.

    Measured before the fix: a five-seed `exp1` set and a five-seed
    `threshold_calibration` set each produced 400 rows of repair-label input.
    They carry a registered stage and the right confirmatory seeds for that
    stage, so every other clause was satisfied -- while the repair protocol had
    never been run at all.
    """
    scale = object()
    seeds = [K.CONFIRMATORY_SEED_BASE + i for i in range(n_seeds)]
    base = [fake("baseline", s, scale=scale, stage=stage) for s in seeds]
    rep = [fake("data_repair", s, scale=scale, stage=stage) for s in seeds]
    masks = {s: np.ones(40, dtype=bool) for s in seeds}
    with pytest.raises(ValueError, match="cannot create a repair label"):
        acceptance_inputs(base, rep, failure_masks=masks)


def test_only_the_repair_stage_and_the_pilot_stage_are_reachable():
    """pilot stays available for diagnostics that create no registered label."""
    from bu.config import STAGES
    from bu.experiments.repair import EXPLORATORY_STAGE, REPAIR_STAGE

    scale = object()
    out = acceptance_inputs([fake("baseline", 0, scale=scale)],
                            [fake("data_repair", 0, scale=scale)])
    assert len(out["errors"]) == 80          # pilot: diagnostic, no label
    assert {REPAIR_STAGE, EXPLORATORY_STAGE} < set(STAGES)


def test_acceptance_test_has_no_fallback_parameter():
    """Sol, delta 46: a dead result-changing-looking option is worse than none."""
    import inspect
    from bu.stats.acceptance import acceptance_test

    assert "allow_fallback" not in inspect.signature(acceptance_test).parameters
