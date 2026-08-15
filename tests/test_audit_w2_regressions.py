"""Regressions from the Week 2 audit (2026-08-15).

One test per defect. As with the Week 1 set, each names the failure it prevents
so the test is not deleted the first time it is inconvenient.
"""

from __future__ import annotations

import numpy as np
import pytest

from bu.config import LAYOUTS, UnitSpec
from bu.env.collect import collect
from bu.env.encoder import ObservationEncoder
from bu.env.gridworld import GridObject, GridState, GridWorld, is_passable
from bu.env.policy import ExploratoryPolicy

# --- B1. object order leaked into the observation -------------------------


def test_encoding_does_not_depend_on_object_order():
    """The same physical arrangement must encode identically.

    The encoder writes one fixed-width block per object slot. Without a
    canonical order, the generator's placement order decided which object
    landed in which slot, so a model had to learn the passability rule
    separately per slot *and* learn permutation invariance on top -- both
    costing data for reasons unrelated to the manipulation. Experiment 1 varies
    dataset size to induce estimation failure, so anything that inflates the
    data requirement moves where that failure appears.
    """
    enc = ObservationEncoder(n_objects=3, grid_size=8)
    objs = (
        GridObject(2, 2, "triangle", "red"),
        GridObject(5, 1, "square", "blue"),
        GridObject(3, 6, "triangle", "blue"),
    )
    reference = enc.encode(GridState(agent=(1, 1), objects=objs))
    for perm in [(1, 0, 2), (2, 1, 0), (0, 2, 1), (2, 0, 1)]:
        shuffled = tuple(objs[i] for i in perm)
        assert np.array_equal(
            enc.encode(GridState(agent=(1, 1), objects=shuffled)), reference
        )


def test_state_stores_objects_in_canonical_order():
    a = GridObject(5, 1, "square", "blue")
    b = GridObject(2, 2, "triangle", "red")
    assert GridState(agent=(1, 1), objects=(a, b)).objects == (a, b)  # y then x
    assert GridState(agent=(1, 1), objects=(b, a)).objects == (a, b)


def test_canonical_order_survives_a_transition():
    """Interact rebuilds the object tuple; it must not disturb the ordering."""
    env = GridWorld(UnitSpec(n_objects=3, grid_size=6))
    for seed in range(10):
        _, info = env.reset(seed=seed)
        state = info["state"]
        for action in range(5):
            nxt = env.transition(state, action)
            keys = [(o.y, o.x) for o in nxt.objects]
            assert keys == sorted(keys)


# --- B2. the bump balancer read counters nobody wrote ---------------------


def test_bump_balancer_uses_a_counter_that_is_actually_updated():
    """`visits` is keyed by the *aggregate* context, which is "both" when two
    adjacent objects disagree. Reading per-class keys out of it left mixed
    adjacency uncounted -- so the balancer was blind exactly where the choice
    between a passable and a blocking object mattered."""
    pol = ExploratoryPolicy(UnitSpec(), seed=0)
    env = GridWorld(UnitSpec())
    _, info = env.reset(seed=0)
    state = info["state"]
    for _ in range(400):
        state = env.transition(state, pol.act(state))

    assert pol.bump_visits, "bump counter must be populated"
    assert set(pol.bump_visits) <= {"pass", "block"}


def test_both_rule_classes_are_bumped_at_a_usable_ratio():
    """The blocking class is half the rule; a dataset thin in it teaches half."""
    cov = collect(UnitSpec(n_transitions=5000), seed=0).coverage
    p, b = cov.bumps["pass"], cov.bumps["block"]
    assert min(p, b) / max(p, b) > 0.6, f"pass={p} block={b}"


# --- B3. two blocking mechanisms were reported as one ---------------------


def test_object_blocks_and_wall_blocks_are_counted_separately():
    """Only an object block is the passability rule firing. Reporting them
    together made the rule's prevalence unreadable from the coverage report."""
    cov = collect(UnitSpec(n_transitions=2000), seed=0).coverage
    assert cov.blocked_by_object_fraction > 0
    assert cov.blocked_by_wall_fraction > 0
    assert cov.blocked_by_object_fraction > cov.blocked_by_wall_fraction


def test_the_transition_fractions_account_for_everything():
    """moved + object-blocked + wall-blocked + interact == 1."""
    data = collect(UnitSpec(n_transitions=2000), seed=0)
    cov = data.coverage
    interact = float((data.action == 4).mean())
    total = (
        cov.moved_fraction
        + cov.blocked_by_object_fraction
        + cov.blocked_by_wall_fraction
        + interact
    )
    assert abs(total - 1.0) < 1e-9, total


def test_interact_is_never_counted_as_a_blocked_move():
    """It does not move the agent, but nothing refused it."""
    unit = UnitSpec(n_objects=1, grid_size=6)
    from bu.env.collect import collect as _collect

    class AlwaysInteract:
        def act(self, state):
            return 4

    cov = _collect(unit, n_transitions=100, seed=0, policy=AlwaysInteract()).coverage
    assert cov.blocked_by_object_fraction == 0.0
    assert cov.blocked_by_wall_fraction == 0.0


# --- B4/B5. silent losses -------------------------------------------------


def test_design_refuses_to_drop_a_repair_validation_obligation():
    """A missing repair-validation unit would quietly drop a 20-seed
    obligation, and every label resting on it would fall back to three."""
    import bu.experiments.enumerate_units as E

    original = E.repair_validation_units
    try:
        E.repair_validation_units = lambda: original() + (
            UnitSpec(grid_size=99, n_objects=2),
        )
        with pytest.raises(RuntimeError, match="repair-validation"):
            E.design_units()
    finally:
        E.repair_validation_units = original
    E.design_units()  # restored


def test_dataset_round_trip_preserves_the_unit_exactly(tmp_path):
    """Serialisation used __dict__, which works today and breaks the moment
    UnitSpec gains __slots__ or a non-field attribute."""
    unit = UnitSpec(
        family="missing_feature",
        withheld_features=("shape",),
        confound_rate=0.75,
        layout="sparse",
        n_transitions=200,
    )
    data = collect(unit, seed=2)
    back = type(data).load(data.save(tmp_path / "d.npz"))
    assert back.unit == unit
    assert back.seed == 2
    assert back.coverage.bumps == data.coverage.bumps
    assert np.array_equal(back.episode, data.episode)


# --- properties the audit checked and wants held --------------------------


@pytest.mark.parametrize("layout", LAYOUTS)
def test_the_three_layouts_are_three_distributions(layout):
    """"Three procedural layout distributions" must be three distributions,
    not three names for the same one (Schedule W2 Tue)."""
    env = GridWorld(UnitSpec(layout=layout, n_objects=4))
    spreads = []
    for seed in range(120):
        _, info = env.reset(seed=seed)
        pos = [o.pos for o in info["state"].objects]
        spreads.append(
            np.mean([abs(a[0] - b[0]) + abs(a[1] - b[1])
                     for i, a in enumerate(pos) for b in pos[i + 1:]])
        )
    mean = float(np.mean(spreads))
    expected = {"clustered": (1.5, 3.2), "uniform": (3.3, 4.8), "sparse": (5.0, 7.5)}
    lo, hi = expected[layout]
    assert lo < mean < hi, f"{layout} mean pairwise distance {mean:.2f}"


def test_a_grid_too_small_for_the_parity_constraint_raises_clearly():
    """Position-as-causal constrains placement to matching parity cells."""
    with pytest.raises(ValueError, match="grid too small"):
        GridWorld(
            UnitSpec(grid_size=4, n_objects=4, causal_attribute="position")
        ).reset(seed=0)
