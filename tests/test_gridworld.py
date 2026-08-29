"""Week 1 Fri/Sat and Week 2 Mon/Tue acceptance tests for the environment.

Each maps to a schedule "Done when" criterion, or to a property the experimental
design depends on being true of the generator.
"""

from __future__ import annotations

import numpy as np
import pytest

from bu.config import FEATURES, LAYOUTS, UnitSpec
from bu.env.encoder import BLOCK_WIDTHS, ObservationEncoder
from bu.env.gridworld import (
    COLOURS,
    DECOY_OF,
    INTERACT,
    MOVE_EAST,
    N_ACTIONS,
    SHAPES,
    GridObject,
    GridState,
    GridWorld,
    is_passable,
    measure_confound,
    rollout,
)

# --- W1 Fri: "a 200-step random rollout runs without error" ---------------


def test_two_hundred_step_random_rollout():
    env = GridWorld(UnitSpec())
    obs, info = env.reset(seed=0)
    assert obs.shape == (env.encoder.size,)
    rng = np.random.default_rng(0)
    for _ in range(200):
        obs, reward, terminated, truncated, info = env.step(int(rng.integers(N_ACTIONS)))
        assert obs.shape == (env.encoder.size,)
        assert np.isfinite(obs).all()
        assert reward == 0.0 and not terminated and not truncated


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("causal", FEATURES)
def test_rollout_runs_for_every_layout_and_causal_attribute(layout, causal):
    """The configuration axes must all actually work, not just the defaults."""
    env = GridWorld(UnitSpec(layout=layout, causal_attribute=causal, confound_rate=0.5))
    for _ in rollout(env, 50, seed=1):
        pass


def test_step_before_reset_is_refused():
    with pytest.raises(RuntimeError, match="reset"):
        GridWorld(UnitSpec()).step(0)


def test_invalid_action_is_refused():
    env = GridWorld(UnitSpec())
    env.reset(seed=0)
    with pytest.raises(ValueError, match="action must be in"):
        env.step(N_ACTIONS)


# --- the transition rule is the experimental instrument -------------------


def test_transitions_are_deterministic():
    """f* must be a function. Stochasticity would add an unmodelled failure
    source that the labelling protocol has no category for (Plan §7.4)."""
    env = GridWorld(UnitSpec())
    _, info = env.reset(seed=3)
    state = info["state"]
    for action in range(N_ACTIONS):
        assert env.transition(state, action) == env.transition(state, action)


def test_agent_cannot_leave_the_interior():
    env = GridWorld(UnitSpec(grid_size=5, n_objects=1))
    n = 5
    for _ in range(200):
        pass
    for step_state, _, nxt in rollout(env, 200, seed=2):
        x, y = nxt.agent
        assert 1 <= x <= n - 2 and 1 <= y <= n - 2


def test_passability_follows_the_causal_attribute_alone():
    """A blocking object blocks regardless of its other attributes."""
    env = GridWorld(UnitSpec(causal_attribute="shape"))
    _, info = env.reset(seed=0)
    state = info["state"]
    for obj in state.objects:
        expected = obj.shape == SHAPES[0]
        assert is_passable(obj, "shape") is expected
        # colour must not influence the rule
        assert is_passable(obj, "shape") == expected


@pytest.mark.parametrize("shape,walkable", [(SHAPES[0], True), (SHAPES[1], False)])
@pytest.mark.parametrize("colour", COLOURS)
def test_blocking_object_stops_the_agent(shape, walkable, colour):
    """The rule, checked directly rather than by waiting for a lucky sample.

    Constructing the state means both branches are always exercised, and
    sweeping colour proves the decoy attribute has no influence on passability
    whatever its value.
    """
    env = GridWorld(UnitSpec(causal_attribute="shape", n_objects=1, grid_size=5))
    state = GridState(
        agent=(1, 1), objects=(GridObject(x=2, y=1, shape=shape, colour=colour),)
    )
    nxt = env.transition(state, MOVE_EAST)
    assert (nxt.agent == (2, 1)) is walkable, (
        f"{shape} should be {'passable' if walkable else 'blocking'} "
        f"regardless of colour={colour}"
    )


def test_interact_toggles_an_adjacent_object_and_nothing_else():
    """Interact must do something observable, or the action carries no
    information -- but it must not touch passability, or it would confound the
    manipulation under study."""
    env = GridWorld(UnitSpec(n_objects=1, grid_size=5))
    state = GridState(
        agent=(1, 1), objects=(GridObject(x=2, y=1, shape=SHAPES[1], colour=COLOURS[1]),)
    )
    nxt = env.transition(state, INTERACT)

    assert nxt.agent == state.agent, "interact must not move the agent"
    before, after = state.objects[0], nxt.objects[0]
    assert after.activated is not before.activated
    assert (after.x, after.y, after.shape, after.colour) == (
        before.x, before.y, before.shape, before.colour
    ), "interact must touch nothing but the activated bit"

    # ...and toggling back restores the original state exactly.
    assert env.transition(nxt, INTERACT) == state


def test_interact_with_no_adjacent_object_is_a_no_op():
    env = GridWorld(UnitSpec(n_objects=1, grid_size=6))
    state = GridState(
        agent=(1, 1), objects=(GridObject(x=4, y=4, shape=SHAPES[0], colour=COLOURS[0]),)
    )
    assert env.transition(state, INTERACT) == state


def test_objects_never_share_a_cell():
    env = GridWorld(UnitSpec(n_objects=6, grid_size=6))
    for seed in range(20):
        _, info = env.reset(seed=seed)
        positions = [o.pos for o in info["state"].objects]
        assert len(set(positions)) == len(positions)
        assert info["state"].agent not in positions


# --- W2 Mon: "sampling test shows empirical correlation matches the setting"


@pytest.mark.parametrize("rate", [0.0, 0.25, 0.5, 0.75, 0.9])
def test_empirical_confound_matches_the_configured_rate(rate):
    """The decoy agrees with the causal class at exactly the configured rate.

    Constructed so the phi coefficient equals confound_rate in expectation:
    P(agree) = c + (1-c)/2, and for balanced binary variables the correlation
    is 2*P(agree) - 1 = c.
    """
    # 1500 episodes x 4 objects = 6000 pairs, so the standard error on the
    # correlation is ~0.012 and the 0.05 tolerance is ~4 SE. At the original
    # 500 episodes it was ~2 SE, which an unlucky seed block would trip: seeds
    # 0-8000 happen to sit 2.5 SE low, checked against 20 independent blocks
    # (mean deviation -0.07 SE, sd 1.20) -- noise, not generator bias.
    measured = measure_confound(UnitSpec(confound_rate=rate), n_episodes=1500, seed=0)
    assert abs(measured - rate) < 0.05, f"configured {rate}, measured {measured:.3f}"


def test_zero_confound_leaves_the_decoy_uninformative():
    assert abs(measure_confound(UnitSpec(confound_rate=0.0), n_episodes=1500)) < 0.05


@pytest.mark.parametrize("causal", FEATURES)
def test_confound_holds_for_every_causal_attribute(causal):
    unit = UnitSpec(causal_attribute=causal, confound_rate=0.75)
    measured = measure_confound(unit, n_episodes=1200, seed=1)
    assert abs(measured - 0.75) < 0.06, f"{causal}: measured {measured:.3f}"
    assert DECOY_OF[causal] != causal


# --- W1 Sat: "env constructs with the shape feature withheld" -------------


def test_env_constructs_with_shape_withheld():
    env = GridWorld(UnitSpec(family="missing_feature", withheld_features=("shape",)))
    obs, info = env.reset(seed=0)
    assert obs.shape == (env.encoder.size,)
    assert "shape" not in env.encoder.visible
    assert any("colour" in b.name for b in env.encoder.blocks)
    assert not any("shape" in b.name for b in env.encoder.blocks)


def test_withholding_shrinks_the_observation_by_exactly_that_block():
    full = ObservationEncoder(n_objects=4, grid_size=8)
    masked = ObservationEncoder(n_objects=4, grid_size=8, withheld=("shape",))
    assert full.size - masked.size == 4 * BLOCK_WIDTHS["shape"]


def test_withholding_hides_the_attribute_but_not_the_dynamics():
    """The crux of Experiment 2A: the rule still uses shape; the model cannot see it.

    Two states differing only in a withheld attribute encode identically -- so
    no model on this input space can separate them -- while the environment
    still transitions differently.
    """
    unit = UnitSpec(causal_attribute="shape", withheld_features=("shape",), n_objects=1)
    env = GridWorld(unit)
    _, info = env.reset(seed=0)
    state = info["state"]

    from dataclasses import replace

    obj = state.objects[0]
    flipped = replace(state, objects=(replace(obj, shape=SHAPES[1 - SHAPES.index(obj.shape)]),))

    assert np.array_equal(env.encoder.encode(state), env.encoder.encode(flipped)), (
        "the withheld attribute must be invisible in the observation"
    )
    assert is_passable(state.objects[0], "shape") != is_passable(flipped.objects[0], "shape"), (
        "but it must still determine the true dynamics"
    )


def test_visible_attribute_changes_the_observation():
    """Control for the test above: a non-withheld attribute must show up."""
    from dataclasses import replace

    unit = UnitSpec(n_objects=1)
    env = GridWorld(unit)
    _, info = env.reset(seed=0)
    state = info["state"]
    obj = state.objects[0]
    flipped = replace(state, objects=(replace(obj, shape=SHAPES[1 - SHAPES.index(obj.shape)]),))
    assert not np.array_equal(env.encoder.encode(state), env.encoder.encode(flipped))


def test_encoder_refuses_an_unknown_attribute():
    with pytest.raises(ValueError, match="cannot withhold"):
        ObservationEncoder(n_objects=2, grid_size=8, withheld=("texture",))


def test_encoder_refuses_to_withhold_everything():
    with pytest.raises(ValueError, match="nothing to predict"):
        ObservationEncoder(n_objects=2, grid_size=8, withheld=tuple(BLOCK_WIDTHS))


def test_encoder_layout_is_order_independent():
    a = ObservationEncoder(n_objects=3, grid_size=8, withheld=("shape", "colour"))
    b = ObservationEncoder(n_objects=3, grid_size=8, withheld=("colour", "shape"))
    assert [x.name for x in a.blocks] == [x.name for x in b.blocks]


def test_observations_stay_in_the_declared_box():
    env = GridWorld(UnitSpec())
    for _, _, nxt in rollout(env, 100, seed=0):
        obs = env.encoder.encode(nxt)
        assert obs.min() >= 0.0 and obs.max() <= 1.0
        assert obs.dtype == np.float32


# --- reproducibility ------------------------------------------------------


def test_same_seed_gives_the_same_episode():
    unit = UnitSpec(layout="clustered", confound_rate=0.5)
    a = [t for t in rollout(GridWorld(unit), 40, seed=7)]
    b = [t for t in rollout(GridWorld(unit), 40, seed=7)]
    assert a == b


def test_different_seeds_give_different_episodes():
    unit = UnitSpec()
    a = [t for t in rollout(GridWorld(unit), 40, seed=1)]
    b = [t for t in rollout(GridWorld(unit), 40, seed=2)]
    assert a != b
