"""The three-pool invariants, and what may never touch what (D-052, D-054).

Sol's point that these needed asserting directly: distinct stream names make
overlap *unlikely*, but the scientific property is non-overlap, and a test
should assert the property rather than the mechanism that currently delivers it.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Arm, TrainConfig, UnitSpec
from bu.env.collect import collect, collect_pools
from bu.env.policy import ExploratoryPolicy
from bu.models.train import episode_indices, train
from bu.models.world_model import WorldModel
from bu.streams import stream

torch.set_num_threads(2)
SEED = K.CONFIRMATORY_SEED_BASE


def _pools(n: int, seed: int = SEED):
    return collect_pools(UnitSpec(n_transitions=n), stage="exp1", seed=seed)


def _rows(dataset) -> set[bytes]:
    """A transition's full identity, not just its observation."""
    return {
        (o.tobytes(), int(a), no.tobytes())
        for o, a, no in zip(dataset.obs, dataset.action, dataset.next_obs)
    }


# --- non-overlap, asserted as the property ---------------------------------


def test_the_pools_are_independently_generated_and_state_their_provenance():
    """The invariant, stated as what it actually is (D-055).

    An earlier version of this test allowed 35% overlap among distinct
    ``(obs, action, next_obs)`` values and claimed in its comment to compare
    episodes. It did neither. In a discrete world identical transition *values*
    recur legitimately across independent draws, so value overlap is not the
    property. The property is that the pools are independently generated --
    different stream keys -- and that each dataset records which pool it came
    from, so provenance can be checked rather than inferred.
    """
    from bu.streams import POOL_PURPOSES, stream_key

    pools = _pools(1000)
    assert (pools.train.pool, pools.validation.pool, pools.evaluation.pool) == (
        "train", "validation", "evaluation",
    )

    unit = UnitSpec(n_transitions=1000)
    keys = {
        str(stream_key(unit, "exp1", purpose))
        for pair in POOL_PURPOSES.values()
        for purpose in pair
    }
    assert len(keys) == 6, "two pools share a stream key"


def test_the_pools_come_from_genuinely_different_draws():
    pools = _pools(1000)
    assert not np.array_equal(
        pools.validation.obs[:400], pools.evaluation.obs[:400]
    )
    assert not np.array_equal(pools.train.obs[:400], pools.validation.obs[:400])


def test_the_three_pools_use_three_distinct_stream_pairs():
    from bu.streams import POOL_PURPOSES

    purposes = [p for pair in POOL_PURPOSES.values() for p in pair]
    assert len(set(purposes)) == len(purposes) == 6


# --- fixed across everything that must not move it -------------------------


def test_validation_and_evaluation_are_identical_across_dataset_sizes():
    """Every array, not only ``obs`` -- a byte-identity claim should be checked
    over everything that varies (D-055)."""
    reference = _pools(100)
    for n in (250, 500, 1000, 2500, 5000):
        pools = _pools(n)
        for name in ("obs", "action", "next_obs", "episode", "step"):
            for which in ("validation", "evaluation"):
                assert np.array_equal(
                    getattr(getattr(pools, which), name),
                    getattr(getattr(reference, which), name),
                ), f"{which}.{name} moved at N={n}"


@pytest.mark.parametrize(
    "arm, unit, stage",
    [
        ("data_repair", UnitSpec(family="estimation", n_transitions=250), "exp1"),
        ("capacity_repair",
         UnitSpec(family="capacity", hidden_size=16, n_transitions=5000), "exp2b"),
        ("feature_repair",
         UnitSpec(family="missing_feature", withheld_features=("shape",),
                  confound_rate=0.5, n_transitions=5000), "exp2a"),
    ],
)
def test_every_repair_arm_keeps_its_baselines_failure_set(arm, unit, stage):
    """P§7.2 evaluates a repair on the *same recorded failure set* as its baseline.

    This previously held for data and capacity repair by accident -- Experiment
    1 excludes ``n_transitions`` from its comparison group and 2B excludes
    ``hidden_size``, so resolving those arms left the stream key untouched.
    Feature repair changes ``withheld_features``, which 2A does *not* exclude,
    so it drew a different environment, validation and evaluation pool from its
    own baseline. Two arms passing was not evidence about the third (D-055).

    Compared on the **latent** trajectory, because restoring a feature changes
    the observation width and byte equality of encoded observations is
    therefore the wrong test.
    """
    base = collect_pools(unit, stage=stage, seed=SEED)
    repaired = collect_pools(unit, stage=stage, seed=SEED, arm=arm)

    for which in ("validation", "evaluation"):
        b, r = getattr(base, which), getattr(repaired, which)
        assert np.array_equal(b.action, r.action), f"{which} actions diverged"
        assert np.array_equal(b.episode, r.episode)
        assert np.array_equal(b.obs[:, :2], r.obs[:, :2]), (
            f"{which} agent trajectory diverged"
        )

    expected = K.DATA_REPAIR_MULTIPLIER if arm == "data_repair" else 1
    assert len(repaired.train) == len(base.train) * expected


def test_the_registered_n_counts_training_transitions_only():
    for n in (100, 250, 1000, 5000):
        assert len(_pools(n).train) == n


# --- evaluation stays outside model selection ------------------------------


def test_the_evaluation_pool_cannot_be_used_for_model_selection():
    """The previous version of this test was false (D-055).

    It asserted that ``train`` has no parameter *named* evaluation -- but the
    pools share a type, so ``train(model, pools.train, pools.evaluation, ...)``
    simply worked, and every reported number would have been selected on.
    Provenance is checked now, so the call raises.
    """
    unit = UnitSpec(hidden_size=32, n_transitions=500)
    pools = _pools(500)
    model = WorldModel(unit, stream(unit, "exp1", "init", SEED))
    cfg = TrainConfig(max_epochs=1)

    with pytest.raises(ValueError, match="evaluation"):
        train(model, pools.train, pools.evaluation, cfg,
              rng=stream(unit, "exp1", "batch", SEED))

    with pytest.raises(ValueError, match="only the training pool"):
        train(model, pools.validation, pools.validation, cfg,
              rng=stream(unit, "exp1", "batch", SEED))


def test_the_loss_curve_is_computed_on_validation_not_evaluation():
    unit = UnitSpec(hidden_size=32, n_transitions=1000)
    pools = _pools(1000)
    result = train(
        WorldModel(unit, stream(unit, "exp1", "init", SEED)),
        pools.train, pools.validation, TrainConfig(max_epochs=4),
        rng=stream(unit, "exp1", "batch", SEED),
    )
    assert result.n_validation == len(pools.validation)
    assert result.n_validation != len(pools.evaluation)


# --- frozen experimental procedure (D-054) ---------------------------------


def test_episode_length_is_frozen_for_confirmatory_seeds():
    with pytest.raises(ValueError, match="frozen value"):
        collect(UnitSpec(n_transitions=100), stage="exp1", seed=SEED, episode_length=5)


@pytest.mark.parametrize("call", ["n_transitions", "policy", "granularity"])
def test_confirmatory_runs_cannot_deviate_from_the_frozen_procedure(call):
    """Development overrides may exist; a confirmatory run may not use them.

    ``granularity`` matters most: it is not part of Config, so a non-primary
    confirmatory fit would occupy the *same recorded identity* as the primary
    one (D-055).
    """
    unit = UnitSpec(hidden_size=32, n_transitions=500)
    if call == "n_transitions":
        with pytest.raises(ValueError, match="registers"):
            collect_pools(unit, stage="exp1", seed=SEED, n_transitions=99)
    elif call == "policy":
        with pytest.raises(ValueError, match="custom policy"):
            collect(unit, stage="exp1", seed=SEED, policy=object())
    else:
        from bu.models.ensemble import train_ensemble

        with pytest.raises(ValueError, match="fixed primary method"):
            train_ensemble(
                unit, _pools(500), TrainConfig(max_epochs=1, ensemble_size=1),
                stage="exp1", seed=SEED, granularity="transition",
            )


def test_a_legacy_dataset_is_not_stamped_with_todays_constants(tmp_path):
    """Loading an older record used to assign the *current* EPISODE_LENGTH, so a
    dataset generated at 50 would be silently relabelled 10 -- the opposite of
    a provenance guarantee (D-055)."""
    import json

    from bu.env.collect import TransitionDataset

    path = _pools(250).evaluation.save(tmp_path / "legacy.npz")
    data = dict(np.load(path, allow_pickle=False))
    meta = json.loads(str(data["meta"]))
    del meta["episode_length"]
    data["meta"] = np.array(json.dumps(meta))
    np.savez_compressed(path, **data)

    with pytest.raises(ValueError, match="generator is unknown"):
        TransitionDataset.load(path)


def test_a_development_override_is_permitted_and_recorded():
    dataset = collect(UnitSpec(n_transitions=100), stage="exp1", seed=0, episode_length=5)
    assert dataset.episode_length == 5, "an override must be recorded on the dataset"


def test_the_pool_and_episode_length_survive_a_round_trip(tmp_path):
    from bu.env.collect import TransitionDataset

    pools = _pools(250)
    path = pools.evaluation.save(tmp_path / "eval.npz")
    reloaded = TransitionDataset.load(path)
    assert reloaded.pool == "evaluation"
    assert reloaded.episode_length == K.EPISODE_LENGTH


def test_the_frozen_pool_sizes_are_what_the_constants_say():
    pools = _pools(1000)
    assert len(pools.validation) == K.VALIDATION_EPISODES * K.EPISODE_LENGTH
    assert len(pools.evaluation) == K.EVALUATION_EPISODES * K.EPISODE_LENGTH
    assert len(episode_indices(pools.validation)) == K.VALIDATION_EPISODES


# --- the policy carries no state across episodes (D-051, D-054) ------------


#: Everything a policy is *allowed* to carry across an episode boundary.
#: Enumerated rather than inferred from type, because the previous version of
#: this test only noticed non-empty dicts, lists and sets -- a scalar counter or
#: an array would have sailed through (D-055).
PERSISTENT_POLICY_FIELDS = {
    "unit", "rng", "p_bump", "p_interact", "p_approach", "epsilon",
}


def test_only_the_declared_fields_survive_a_reset():
    """Structural, because stationarity is a design property and a null
    diagnostic cannot prove it (D-054)."""
    unit = UnitSpec(n_transitions=200)
    policy = ExploratoryPolicy(unit, rng=stream(unit, "exp1", "policy", SEED))
    for i in range(20):
        policy.visits[("none", i % 5)] += 1
    policy.bump_visits["pass"] += 3
    assert policy.visits and policy.bump_visits

    policy.reset()
    assert not policy.visits and not policy.bump_visits

    stateful = {
        name for name, value in vars(policy).items()
        if name not in PERSISTENT_POLICY_FIELDS and value not in (None, 0, (), [], {})
    }
    assert not stateful, (
        f"undeclared state survived reset(): {sorted(stateful)}. Either clear it "
        "in reset() or add it to PERSISTENT_POLICY_FIELDS with a reason."
    )


def test_collect_resets_the_policy_once_per_episode():
    """The reset must actually be *called*, not merely available."""
    unit = UnitSpec(n_transitions=200)

    class _Spy(ExploratoryPolicy):
        resets = 0

        def reset(self) -> None:
            type(self).resets += 1
            super().reset()

    spy = _Spy(unit, rng=stream(unit, "exp1", "policy", 0))
    dataset = collect(unit, stage="exp1", seed=0, policy=spy)
    assert _Spy.resets == len(np.unique(dataset.episode))


def test_an_episode_does_not_depend_on_how_many_preceded_it():
    """The property the reset exists to give: identical state and identical RNG
    state produce identical behaviour, whatever came before."""
    unit = UnitSpec(n_transitions=200)
    _, info = __import__("bu.env.gridworld", fromlist=["GridWorld"]).GridWorld(unit).reset(seed=3)
    state = info["state"]

    fresh = ExploratoryPolicy(unit, rng=np.random.default_rng(11))
    worn = ExploratoryPolicy(unit, rng=np.random.default_rng(11))
    for _ in range(500):  # wear it in, then reset as collect() does
        worn.act(state)
    worn.reset()
    worn.rng = np.random.default_rng(11)

    assert [fresh.act(state) for _ in range(30)] == [worn.act(state) for _ in range(30)]
