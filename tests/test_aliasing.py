"""Observational aliasing: does withholding an attribute actually make the
dynamics unrepresentable? (Sol review, 2026-08-16 · D-026)

Experiment 2A rests on a single claim: with the causal attribute withheld, no
model on the observation space can express the true transition rule, because the
observation space itself cannot separate two states the rule treats differently.
Everything downstream -- the H2 signature, every hypothesis-class label, the
critic's entire positive class -- is downstream of that claim being true.

The test that existed before this file asserted something weaker and narrower.
It checked one attribute (shape), on one state, and compared ``is_passable`` --
the rule as a Python function -- rather than running the two states through
``transition()`` and comparing successors. So it verified that the rule reads
the attribute, not that the *environment* is aliased under the model's input
space. Those come apart the moment anything else in the encoding correlates with
the withheld attribute, which is exactly what slot ordering did.

What is proved here instead, per attribute:

    there exist s1, s2 and an action a with
        encode(s1) == encode(s2)   and   encode(f*(s1, a)) != encode(f*(s2, a))

and, as the control that gives it meaning, that **no** such pair exists when
nothing is withheld. Without the control the property is unfalsifiable: an
encoder that collapsed every state would satisfy it trivially.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from bu.config import UnitSpec
from bu.env.encoder import ObservationEncoder
from bu.env.gridworld import GridObject, GridState, GridWorld
from bu.experiments.enumerate_units import CANONICAL_PAIRS

GRID = 5
N_OBJECTS = 2
SHAPES_ = ("triangle", "square")
COLOURS_ = ("red", "blue")


def _states(grid: int = GRID, n_objects: int = N_OBJECTS):
    """Every state of a small world: positions, attributes, agent placement."""
    cells = [(x, y) for x in range(1, grid - 1) for y in range(1, grid - 1)]
    attrs = list(itertools.product(SHAPES_, COLOURS_))
    for positions in itertools.combinations(cells, n_objects):
        for combo in itertools.product(attrs, repeat=n_objects):
            objects = tuple(
                GridObject(x=p[0], y=p[1], shape=a[0], colour=a[1])
                for p, a in zip(positions, combo)
            )
            for agent in cells:
                if agent in positions:
                    continue
                yield GridState(agent=agent, objects=objects)


def _aliased_pair(unit: UnitSpec):
    """Find (obs, action) reached by two states with different successors."""
    env = GridWorld(unit)
    enc = env.encoder
    seen: dict[tuple[bytes, int], bytes] = {}
    for state in _states():
        obs = enc.encode(state).tobytes()
        for action in range(4):  # moves only: interact cannot be blocked
            key = (obs, action)
            successor = enc.encode(env.transition(state, action)).tobytes()
            if key in seen and seen[key] != successor:
                return state, action
            seen.setdefault(key, successor)
    return None


@pytest.mark.parametrize("attribute", ["shape", "colour"])
def test_withholding_the_causal_attribute_aliases_the_dynamics(attribute: str):
    """f* ∉ H by construction, proved through transition() rather than the rule.

    This is the property Experiment 2A claims, stated over the environment the
    model actually sees.
    """
    unit = UnitSpec(
        causal_attribute=attribute,
        withheld_features=(attribute,),
        n_objects=N_OBJECTS,
        grid_size=GRID,
        family="missing_feature",
    )
    assert _aliased_pair(unit) is not None, (
        f"withholding {attribute!r} left the dynamics fully determined by the "
        "observation: the condition is not a hypothesis-class failure at all"
    )


def test_no_aliasing_when_nothing_is_withheld():
    """The control, without which the test above is unfalsifiable.

    A fully-observed configuration must be Markov in the observation. If it is
    not, the aliasing above is a defect in the encoder rather than the
    manipulation, and every 2A label would be measuring the wrong thing.
    """
    unit = UnitSpec(causal_attribute="shape", n_objects=N_OBJECTS, grid_size=GRID)
    assert _aliased_pair(unit) is None, (
        "states are aliased with every attribute visible -- the encoding is "
        "lossy independently of the Experiment 2A manipulation"
    )


@pytest.mark.parametrize("attribute", ["shape", "colour"])
def test_the_withheld_attribute_is_invisible_but_still_drives_the_rule(attribute: str):
    """Same physical arrangement, one flipped attribute: identical observation."""
    other = {"shape": SHAPES_, "colour": COLOURS_}[attribute]
    unit = UnitSpec(
        causal_attribute=attribute,
        withheld_features=(attribute,),
        n_objects=1,
        grid_size=GRID,
        family="missing_feature",
    )
    env = GridWorld(unit)

    fields = {"shape": SHAPES_[0], "colour": COLOURS_[0]}
    a = GridState(agent=(1, 2), objects=(GridObject(x=2, y=2, **fields),))
    b = GridState(
        agent=(1, 2),
        objects=(GridObject(x=2, y=2, **{**fields, attribute: other[1]}),),
    )

    assert np.array_equal(env.encoder.encode(a), env.encoder.encode(b))
    # ... and the environment still tells them apart, through transition().
    assert env.transition(a, 1).agent != env.transition(b, 1).agent, (
        "the withheld attribute no longer changes the successor state; the "
        "manipulation has stopped manipulating anything"
    )


# --- the slot-order leak (D-027) ------------------------------------------


def test_slot_order_cannot_leak_a_withheld_position():
    """Withholding position must hide position, including through slot order.

    ``GridState`` orders objects in raster order by position, so slot assignment
    was a function of position. With position withheld the observation therefore
    still carried positional information -- through *which slot* an object's
    visible attributes landed in -- while claiming to carry none.
    """
    enc = ObservationEncoder(n_objects=2, grid_size=6, withheld=("position",))

    # Same two visible descriptors, opposite spatial arrangement. Under raster
    # ordering these swapped slots and encoded differently.
    a = GridState(
        agent=(2, 2),
        objects=(
            GridObject(x=1, y=1, shape="triangle", colour="red"),
            GridObject(x=3, y=3, shape="square", colour="blue"),
        ),
    )
    b = GridState(
        agent=(2, 2),
        objects=(
            GridObject(x=1, y=1, shape="square", colour="blue"),
            GridObject(x=3, y=3, shape="triangle", colour="red"),
        ),
    )
    assert np.array_equal(enc.encode(a), enc.encode(b)), (
        "object positions changed a position-masked observation through slot "
        "order; the attribute is not withheld, only partly hidden"
    )


def test_visible_position_still_reaches_the_observation():
    """Control: the fix must not hide position when it is *not* withheld."""
    enc = ObservationEncoder(n_objects=2, grid_size=6)
    a = GridState(
        agent=(2, 2),
        objects=(
            GridObject(x=1, y=1, shape="triangle", colour="red"),
            GridObject(x=3, y=3, shape="square", colour="blue"),
        ),
    )
    b = GridState(
        agent=(2, 2),
        objects=(
            GridObject(x=1, y=1, shape="square", colour="blue"),
            GridObject(x=3, y=3, shape="triangle", colour="red"),
        ),
    )
    assert not np.array_equal(enc.encode(a), enc.encode(b))


def test_encoding_is_invariant_to_the_order_objects_are_listed_in():
    """B1's property, restated at the encoder rather than at GridState.

    The encoder now assigns slots by the descriptor it writes, so this holds
    whatever order the caller supplies -- and, unlike raster ordering, it holds
    for every withholding configuration too.
    """
    objects = (
        GridObject(x=1, y=3, shape="triangle", colour="red"),
        GridObject(x=3, y=1, shape="square", colour="blue"),
    )
    for withheld in [(), ("shape",), ("colour",), ("position",)]:
        enc = ObservationEncoder(n_objects=2, grid_size=6, withheld=withheld)
        forward = enc.encode(GridState(agent=(2, 2), objects=objects))
        backward = enc.encode(GridState(agent=(2, 2), objects=objects[::-1]))
        assert np.array_equal(forward, backward), f"order leaked with {withheld=}"


# --- why position left the canonical set (D-026) ---------------------------


def test_position_masking_hides_occupancy_not_just_the_rule():
    """The measurement behind D-026, pinned so the reasoning stays checkable.

    Withholding shape or colour removes an attribute of an object the model can
    still see. Withholding position removes the object-position block outright,
    so the model cannot locate objects at all and cannot represent *that a move
    was into an object* -- a different structural failure from an
    unrepresentable rule, which is why it is not a canonical 2A condition.
    """
    masked = ObservationEncoder(n_objects=2, grid_size=6, withheld=("position",))
    assert not any("position" in b.name for b in masked.blocks if b.name != "agent_position")

    shape_masked = ObservationEncoder(n_objects=2, grid_size=6, withheld=("shape",))
    assert any(b.name.endswith("_position") and b.name != "agent_position"
               for b in shape_masked.blocks), (
        "shape masking must leave object positions visible -- that is what "
        "makes it a rule failure rather than an observability failure"
    )


def test_no_canonical_configuration_is_position_causal():
    """D-026: position-causal conditions run in the sweep, never as canonical 2A."""
    assert all(causal != "position" for causal, _ in CANONICAL_PAIRS)
    assert len(CANONICAL_PAIRS) == 5, "Plan §14.2 budgets five canonical configurations"
