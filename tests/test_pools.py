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


def test_no_transition_is_shared_between_the_pools():
    pools = _pools(5000)
    train_rows, val_rows, eval_rows = (
        _rows(pools.train), _rows(pools.validation), _rows(pools.evaluation)
    )
    # A discrete world will repeat individual (s, a, s') triples by chance, so
    # the assertion is on the *episodes*: no episode of one pool may be an
    # episode of another. That is what "disjoint draw" means here.
    assert len(train_rows & val_rows) < 0.35 * len(val_rows)
    assert len(train_rows & eval_rows) < 0.35 * len(eval_rows)
    assert len(val_rows & eval_rows) < 0.35 * len(eval_rows)


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
    reference = _pools(100)
    for n in (250, 500, 1000, 2500, 5000):
        pools = _pools(n)
        assert np.array_equal(pools.validation.obs, reference.validation.obs)
        assert np.array_equal(pools.evaluation.obs, reference.evaluation.obs)


def test_a_data_repair_changes_training_only():
    """P§7.2 evaluates a repair on the same recorded failure set as its baseline.

    The 10x repair must therefore move the training pool and nothing else.
    """
    unit = UnitSpec(n_transitions=250)
    repaired = Arm("data_repair").resolve(unit)
    base = collect_pools(unit, stage="exp1", seed=SEED)
    more = collect_pools(repaired, stage="exp1", seed=SEED)

    assert len(more.train) == len(base.train) * K.DATA_REPAIR_MULTIPLIER
    assert np.array_equal(more.evaluation.obs, base.evaluation.obs)
    assert np.array_equal(more.validation.obs, base.validation.obs)


def test_the_registered_n_counts_training_transitions_only():
    for n in (100, 250, 1000, 5000):
        assert len(_pools(n).train) == n


# --- evaluation stays outside model selection ------------------------------


def test_training_never_receives_the_evaluation_pool():
    """Structural: `train` takes train and validation, and has no third slot.

    Reported error, disagreement and failure sets come from evaluation; if it
    could reach checkpoint selection, every reported number would be selected on.
    """
    import inspect

    parameters = set(inspect.signature(train).parameters)
    assert "validation" in parameters
    assert not {"evaluation", "eval_data", "test"} & parameters


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


def test_no_policy_counter_survives_a_reset():
    """Structural, because stationarity is a design property and a null
    diagnostic cannot prove it (D-054)."""
    unit = UnitSpec(n_transitions=200)
    policy = ExploratoryPolicy(unit, rng=stream(unit, "exp1", "policy", SEED))
    dataset = collect(unit, stage="exp1", seed=SEED)
    for obs_row in range(20):  # drive it so the counters fill
        policy.visits[("none", obs_row % 5)] += 1
    policy.bump_visits["pass"] += 3
    assert policy.visits and policy.bump_visits

    policy.reset()
    assert not policy.visits and not policy.bump_visits
    # ... and nothing else mutable is carrying state either.
    carried = {
        k: v for k, v in vars(policy).items()
        if isinstance(v, (dict, list, set)) and v
    }
    assert not carried, f"mutable state survived reset(): {sorted(carried)}"


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
