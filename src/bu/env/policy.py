"""Scripted exploratory policy, replacing PPO (DEV-001, Plan §13.2).

Plan §13.2 permits substituting a scripted behaviour policy and requires the
substitution to be **recorded rather than hidden**. The policy is explicitly not
an object of study: nothing in the thesis is a claim about it. Its only job is
to produce a transition dataset from which a world model can learn the true
dynamics -- and to do so well enough that "the model failed" never means "the
data never showed it the thing it needed to learn".

That last point is the whole design constraint, and it is sharper than it looks.
The transition rule is about **passability**: triangles can be walked through,
squares cannot. A model can only learn that from transitions in which the agent
*tried to walk into an object*. In an 8x8 grid with four objects, a uniform
random walk almost never produces one -- most steps are moves through empty
space, which teach nothing about the rule under study.

A policy that failed here would be indistinguishable, from the outside, from
insufficient data. Experiment 1 varies dataset size to induce estimation
failure; if small datasets also happened to lack object interactions, the
"estimation failure" family would be measuring coverage rather than sample size,
and H1 would be testing the wrong thing. So the policy deliberately seeks out
the informative transitions, and the coverage report in ``collect.py`` is the
evidence that it did.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from ..config import UnitSpec
from .gridworld import (
    INTERACT,
    MOVE_EAST,
    MOVE_NORTH,
    MOVE_SOUTH,
    MOVE_WEST,
    N_ACTIONS,
    GridObject,
    GridState,
    GridWorld,
    is_passable,
)

_MOVES = (MOVE_NORTH, MOVE_EAST, MOVE_SOUTH, MOVE_WEST)
_DELTA_TO_MOVE = {(0, -1): MOVE_NORTH, (1, 0): MOVE_EAST, (0, 1): MOVE_SOUTH, (-1, 0): MOVE_WEST}


class ExploratoryPolicy:
    """Coverage-biased random walk with forced object interactions.

    Behaviour, in priority order, when an object is adjacent:

    1. **Bump** -- move into it. This is the transition that carries the rule,
       and it is the one a random walk starves. Taken most often.
    2. **Interact** -- toggle its activated bit, so the interact action appears
       in the data with a visible effect rather than only as a no-op.
    3. Otherwise fall through to the coverage-biased choice below.

    With no object adjacent, the policy either approaches the nearest one --
    manufacturing future bump opportunities -- or picks the action least seen so
    far in the current context, where context is the causal class of the
    adjacent object (or "none"). Biasing on the *causal* class rather than on
    shape specifically means coverage is balanced over the attribute that
    actually decides the dynamics, whichever attribute the configuration made
    causal.

    The policy is not tuned per condition and holds no learned parameters. It is
    seeded, deterministic, and reported alongside the data it produced.
    """

    def __init__(
        self,
        unit: UnitSpec,
        seed: int = 0,
        *,
        p_bump: float = 0.55,
        p_interact: float = 0.15,
        p_approach: float = 0.6,
        epsilon: float = 0.1,
    ) -> None:
        self.unit = unit
        self.rng = np.random.default_rng(seed)
        self.p_bump = p_bump
        self.p_interact = p_interact
        self.p_approach = p_approach
        self.epsilon = epsilon
        #: (context, action) -> count, where context is the adjacent object's
        #: causal class. Drives the coverage bias over actions.
        self.visits: Counter[tuple[str, int]] = Counter()
        #: causal class -> count of bumps taken into it. Kept separately from
        #: `visits` because the two are keyed differently: `visits` records the
        #: *aggregate* context, which is "both" when adjacent objects disagree,
        #: while the bump balancer needs per-class counts. Reading per-class
        #: keys out of `visits` left mixed-adjacency bumps uncounted, so the
        #: balancer was partly blind exactly where the choice mattered most.
        self.bump_visits: Counter[str] = Counter()

    # --- action selection -------------------------------------------------

    def act(self, state: GridState) -> int:
        adjacent = self._adjacent(state)
        context = self._context(adjacent)
        action = self._choose(state, adjacent, context)
        self.visits[(context, action)] += 1
        return action

    def _choose(
        self, state: GridState, adjacent: list[tuple[GridObject, int]], context: str
    ) -> int:
        if adjacent:
            r = self.rng.random()
            if r < self.p_bump:
                return self._least_covered_bump(adjacent, context)
            if r < self.p_bump + self.p_interact:
                return INTERACT
            return self._coverage_biased(context)

        if self.rng.random() < self.p_approach:
            approach = self._towards_nearest(state)
            if approach is not None:
                return approach
        return self._coverage_biased(context)

    def _least_covered_bump(
        self, adjacent: list[tuple[GridObject, int]], context: str
    ) -> int:
        """Prefer bumping the object class we have seen bumped least.

        Without this the policy would happily bump the same passable object
        repeatedly and leave the blocking class thin -- and the blocking class
        is half the rule.
        """
        best = min(
            adjacent,
            key=lambda pair: (self.bump_visits[self._class_of(pair[0])], pair[1]),
        )
        self.bump_visits[self._class_of(best[0])] += 1
        return best[1]

    def _coverage_biased(self, context: str) -> int:
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(N_ACTIONS))
        counts = [self.visits[(context, a)] for a in range(N_ACTIONS)]
        fewest = min(counts)
        tied = [a for a, c in enumerate(counts) if c == fewest]
        return int(tied[self.rng.integers(len(tied))])

    # --- geometry ---------------------------------------------------------

    def _adjacent(self, state: GridState) -> list[tuple[GridObject, int]]:
        ax, ay = state.agent
        out: list[tuple[GridObject, int]] = []
        for (dx, dy), move in _DELTA_TO_MOVE.items():
            obj = state.object_at((ax + dx, ay + dy))
            if obj is not None:
                out.append((obj, move))
        return out

    def _towards_nearest(self, state: GridState) -> int | None:
        ax, ay = state.agent
        if not state.objects:
            return None
        target = min(
            state.objects, key=lambda o: (abs(o.x - ax) + abs(o.y - ay), o.pos)
        )
        dx, dy = target.x - ax, target.y - ay
        options = []
        if dx:
            options.append(MOVE_EAST if dx > 0 else MOVE_WEST)
        if dy:
            options.append(MOVE_SOUTH if dy > 0 else MOVE_NORTH)
        if not options:
            return None
        return int(options[self.rng.integers(len(options))])

    def _class_of(self, obj: GridObject) -> str:
        return "pass" if is_passable(obj, self.unit.causal_attribute) else "block"

    def _context(self, adjacent: list[tuple[GridObject, int]]) -> str:
        if not adjacent:
            return "none"
        classes = {self._class_of(o) for o, _ in adjacent}
        return "both" if len(classes) > 1 else classes.pop()


def random_policy(unit: UnitSpec, seed: int = 0):
    """Uniform random baseline, for the coverage comparison in W2 Sat.

    Exists so the substitution record can show what the scripted policy buys
    rather than assert it (Plan §13.2).
    """
    rng = np.random.default_rng(seed)

    class _Random:
        unit_ = unit

        def act(self, state: GridState) -> int:
            return int(rng.integers(N_ACTIONS))

    return _Random()
