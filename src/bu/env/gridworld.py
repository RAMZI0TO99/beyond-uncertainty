"""The gridworld (Schedule W1 Fri, W2 Mon–Tue).

A deterministic symbolic gridworld whose transition rule depends on exactly one
object attribute -- the *causal attribute* -- while a second attribute, the
*decoy*, correlates with it at a controllable rate. That construction is the
whole experimental instrument: it lets a world model learn a shortcut that
works on the training distribution and fails structurally (Plan §2.2, §5.5).

Why custom rather than stock MiniGrid: only a purpose-built generator gives
clean control over *which* attribute is causal, which the Experiment 2A
manipulation requires (Plan §19).

Why symbolic rather than pixels: the realizability manipulation must be well
defined. "The model cannot represent this rule" is a precise statement about a
factored input space and an ill-posed one about pixels (Plan §13.1.3).

The rule
--------
An object is passable or blocking. Which one is determined solely by the causal
attribute:

    shape     triangle passable, square blocking   (the Plan §2.2 example)
    colour    red passable, blue blocking
    position  even (x+y) passable, odd blocking

The decoy attribute agrees with the causal class with probability
``confound_rate``, and is otherwise independent. At 0.0 the decoy is useless; at
0.9 a model that reads only the decoy is right most of the time on the training
distribution and still structurally wrong. Empirical correlation between the two
equals ``confound_rate`` in expectation -- see ``measure_confound``.

Reward is always zero. This environment exists to generate transitions for a
world model, and the behaviour policy is scripted rather than learned (DEV-001).
Nothing here optimises a return.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterator

import numpy as np

try:  # Gymnasium is a hard dependency, but the env must be usable without it
    import gymnasium as gym
    from gymnasium import spaces

    _BASE = gym.Env
except ModuleNotFoundError:  # pragma: no cover
    gym = None
    spaces = None
    _BASE = object

from ..config import FEATURES, LAYOUTS, UnitSpec
from .encoder import ObservationEncoder

SHAPES = ("triangle", "square")
COLOURS = ("red", "blue")

#: Action ids. Four moves plus interact (Plan §13.1.2).
MOVE_NORTH, MOVE_EAST, MOVE_SOUTH, MOVE_WEST, INTERACT = range(5)
N_ACTIONS = 5
_DELTAS = {MOVE_NORTH: (0, -1), MOVE_EAST: (1, 0), MOVE_SOUTH: (0, 1), MOVE_WEST: (-1, 0)}

#: Which attribute plays the decoy for each causal attribute. The decoy is what
#: a shortcut-learning model latches onto when the causal attribute is withheld.
DECOY_OF: dict[str, str] = {"shape": "colour", "colour": "shape", "position": "colour"}


@dataclass(frozen=True)
class GridObject:
    x: int
    y: int
    shape: str
    colour: str
    activated: bool = False

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass(frozen=True)
class GridState:
    """Complete symbolic state. Deterministic successor given an action.

    Objects are held in a canonical order -- raster order by position -- and
    sorted on construction. That is not tidiness; it removes a nuisance factor
    that would otherwise distort the central experiment.

    The observation encoder writes one fixed-width block per object slot, so
    without a canonical order the *same physical arrangement* encodes
    differently depending on the order the generator happened to place objects
    in. A model would then have to learn the passability rule separately per
    slot, and learn permutation invariance on top of it -- both of which cost
    data for reasons that have nothing to do with the manipulation under study.
    Experiment 1 varies dataset size to induce estimation failure, so anything
    that inflates the data requirement shifts where that failure appears and
    makes the sweep measure encoding nuisance rather than sample size.
    """

    agent: tuple[int, int]
    objects: tuple[GridObject, ...]

    def __post_init__(self) -> None:
        canonical = tuple(sorted(self.objects, key=lambda o: (o.y, o.x)))
        if canonical != self.objects:
            object.__setattr__(self, "objects", canonical)

    def object_at(self, pos: tuple[int, int]) -> GridObject | None:
        return next((o for o in self.objects if o.pos == pos), None)


def is_passable(obj: GridObject, causal_attribute: str) -> bool:
    """The true transition rule. One attribute decides; the others are noise."""
    if causal_attribute == "shape":
        return obj.shape == "triangle"
    if causal_attribute == "colour":
        return obj.colour == "red"
    if causal_attribute == "position":
        return (obj.x + obj.y) % 2 == 0
    raise ValueError(f"unknown causal attribute {causal_attribute!r}")


class GridWorld(_BASE):
    """Gymnasium-compatible symbolic gridworld built from a :class:`UnitSpec`.

    Taking the UnitSpec directly is deliberate: the environment's configuration
    axes and the statistical unit's identity are then the same object, so a
    condition cannot be described one way in the config and generated another.
    """

    metadata = {"render_modes": []}

    def __init__(self, unit: UnitSpec | None = None) -> None:
        self.unit = unit if unit is not None else UnitSpec()
        if self.unit.layout not in LAYOUTS:  # defence in depth; UnitSpec checks too
            raise ValueError(f"unknown layout {self.unit.layout!r}")
        if self.unit.grid_size < 3:
            raise ValueError("grid_size must leave at least one interior cell")

        self.encoder = ObservationEncoder(
            n_objects=self.unit.n_objects,
            grid_size=self.unit.grid_size,
            withheld=self.unit.withheld_features,
        )
        self._rng = np.random.default_rng(0)
        self._state: GridState | None = None

        if spaces is not None:
            self.action_space = spaces.Discrete(N_ACTIONS)
            self.observation_space = spaces.Box(
                low=0.0, high=1.0, shape=(self.encoder.size,), dtype=np.float32
            )

    # --- Gymnasium API ----------------------------------------------------

    def reset(
        self,
        *,
        seed: int | None = None,
        rng: np.random.Generator | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Generate a fresh layout.

        ``rng`` **adopts** a generator rather than seeding one, and that is the
        difference that matters (D-030). A generator handed in keeps flowing
        across episodes, so a collection of 250 transitions begins with exactly
        the 100 a collection of 100 would produce -- Experiment 1's datasets are
        nested prefixes rather than independent draws, which is what makes the
        data-size sweep vary the amount of data and nothing else.

        ``seed`` remains for tests and one-off probes. It reseeds, so successive
        resets repeat, and two different units at the same seed get correlated
        layouts -- which is precisely the coupling Q-008 was raised about.
        """
        if rng is not None and seed is not None:
            raise ValueError("pass rng or seed, not both: they specify different streams")
        if rng is not None:
            self._rng = rng
        elif seed is not None:
            self._rng = np.random.default_rng(seed)
        self._state = self._generate()
        return self.encoder.encode(self._state), {"state": self._state}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self._state is None:
            raise RuntimeError("reset() must be called before step()")
        if not 0 <= int(action) < N_ACTIONS:
            raise ValueError(f"action must be in [0, {N_ACTIONS}), got {action!r}")

        self._state = self.transition(self._state, int(action))
        # Reward is unused: the behaviour policy is scripted, not learned.
        return self.encoder.encode(self._state), 0.0, False, False, {"state": self._state}

    # --- dynamics ---------------------------------------------------------

    def transition(self, state: GridState, action: int) -> GridState:
        """The true transition function f*. Deterministic and side-effect free."""
        if action == INTERACT:
            return self._interact(state)

        dx, dy = _DELTAS[action]
        target = (state.agent[0] + dx, state.agent[1] + dy)

        if not self._in_bounds(target):
            return state  # boundary wall
        obj = state.object_at(target)
        if obj is not None and not is_passable(obj, self.unit.causal_attribute):
            return state  # blocked by the causal rule
        return replace(state, agent=target)

    def _interact(self, state: GridState) -> GridState:
        """Toggle the activated bit of an adjacent object.

        Deliberately orthogonal to passability. The interact action needs an
        observable effect -- otherwise a world model learns it is the identity
        and the action carries no information -- but giving it any influence on
        the transition rule would confound the manipulation under study.
        """
        ax, ay = state.agent
        adjacent = [(ax, ay - 1), (ax + 1, ay), (ax, ay + 1), (ax - 1, ay)]
        for pos in adjacent:
            obj = state.object_at(pos)
            if obj is not None:
                toggled = replace(obj, activated=not obj.activated)
                return replace(
                    state,
                    objects=tuple(toggled if o is obj else o for o in state.objects),
                )
        return state

    def _in_bounds(self, pos: tuple[int, int]) -> bool:
        """Interior only: row/column 0 and grid_size-1 are boundary walls."""
        n = self.unit.grid_size
        return 1 <= pos[0] <= n - 2 and 1 <= pos[1] <= n - 2

    # --- generation -------------------------------------------------------

    def _generate(self) -> GridState:
        causal = self.unit.causal_attribute
        decoy = DECOY_OF[causal]
        n = self.unit.n_objects

        # 1. The causal class of each object: True means passable. Balanced, so
        #    the decoy correlation below is not confounded by a skewed marginal.
        causal_class = self._rng.random(n) < 0.5

        # 2. The decoy agrees with probability confound_rate, else is independent.
        #    P(agree) = c + (1-c)/2, so the phi correlation between the two
        #    binary variables is 2*P(agree) - 1 = c exactly, in expectation.
        forced = self._rng.random(n) < self.unit.confound_rate
        decoy_class = np.where(forced, causal_class, self._rng.random(n) < 0.5)

        # 3. Positions, with parity forced where position is the causal attribute.
        parity = causal_class if causal == "position" else None
        positions = self._place(n, parity)

        objects: list[GridObject] = []
        for i, (x, y) in enumerate(positions):
            attrs = {"shape": None, "colour": None}
            if causal in attrs:
                attrs[causal] = self._value(causal, bool(causal_class[i]))
            if decoy in attrs:
                attrs[decoy] = self._value(decoy, bool(decoy_class[i]))
            for name in attrs:
                if attrs[name] is None:  # neither causal nor decoy: pure noise
                    attrs[name] = self._value(name, bool(self._rng.random() < 0.5))
            objects.append(GridObject(x=x, y=y, shape=attrs["shape"], colour=attrs["colour"]))

        return GridState(agent=self._place_agent(positions), objects=tuple(objects))

    @staticmethod
    def _value(attribute: str, positive_class: bool) -> str:
        """Map a boolean class to a concrete attribute value.

        The positive class is the one the rule calls passable, so that "agrees
        with the causal class" means the same thing for every attribute.
        """
        if attribute == "shape":
            return SHAPES[0] if positive_class else SHAPES[1]
        if attribute == "colour":
            return COLOURS[0] if positive_class else COLOURS[1]
        raise ValueError(f"{attribute!r} has no categorical value")

    def _interior(self) -> list[tuple[int, int]]:
        n = self.unit.grid_size
        return [(x, y) for x in range(1, n - 1) for y in range(1, n - 1)]

    def _place(self, n: int, parity: np.ndarray | None) -> list[tuple[int, int]]:
        """Sample object positions under the configured layout distribution."""
        cells = self._interior()
        taken: set[tuple[int, int]] = set()
        out: list[tuple[int, int]] = []

        for i in range(n):
            candidates = [c for c in cells if c not in taken]
            if parity is not None:
                want = 0 if parity[i] else 1
                matching = [c for c in candidates if (c[0] + c[1]) % 2 == want]
                if not matching:
                    raise ValueError(
                        f"grid too small to place {n} objects with the parities "
                        "required when position is the causal attribute"
                    )
                candidates = matching
            if not candidates:
                raise ValueError(f"grid too small to place {n} objects")

            pos = self._pick(candidates, out)
            taken.add(pos)
            out.append(pos)
        return out

    def _pick(
        self, candidates: list[tuple[int, int]], placed: list[tuple[int, int]]
    ) -> tuple[int, int]:
        layout = self.unit.layout
        if layout == "uniform":
            return candidates[int(self._rng.integers(len(candidates)))]

        if layout == "clustered":
            # Weight towards the first object, so objects gather in one region.
            if not placed:
                return candidates[int(self._rng.integers(len(candidates)))]
            cx, cy = placed[0]
            d = np.array([abs(x - cx) + abs(y - cy) for x, y in candidates], float)
            w = np.exp(-d)
            return candidates[int(self._rng.choice(len(candidates), p=w / w.sum()))]

        if layout == "sparse":
            # Greedily take the candidate furthest from everything placed.
            if not placed:
                return candidates[int(self._rng.integers(len(candidates)))]
            d = np.array(
                [min(abs(x - px) + abs(y - py) for px, py in placed) for x, y in candidates],
                float,
            )
            best = np.flatnonzero(d == d.max())
            return candidates[int(best[self._rng.integers(len(best))])]

        raise ValueError(f"unknown layout {layout!r}")

    def _place_agent(self, occupied: list[tuple[int, int]]) -> tuple[int, int]:
        free = [c for c in self._interior() if c not in set(occupied)]
        if not free:
            raise ValueError("no free cell for the agent")
        return free[int(self._rng.integers(len(free)))]


# --- diagnostics -----------------------------------------------------------


def measure_confound(unit: UnitSpec, n_episodes: int = 400, seed: int = 0) -> float:
    """Empirical correlation between the decoy and causal classes.

    Schedule W2 Mon's acceptance criterion: the sampled correlation must match
    the configured ``confound_rate``. Reported as the phi coefficient, which for
    two binary variables is the Pearson correlation.
    """
    env = GridWorld(unit)
    causal_attr = unit.causal_attribute
    decoy_attr = DECOY_OF[causal_attr]

    causal_bits: list[float] = []
    decoy_bits: list[float] = []
    for ep in range(n_episodes):
        _, info = env.reset(seed=seed + ep)
        for obj in info["state"].objects:
            causal_bits.append(float(is_passable(obj, causal_attr)))
            decoy_bits.append(float(_positive_class(obj, decoy_attr)))

    a, b = np.array(causal_bits), np.array(decoy_bits)
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def _positive_class(obj: GridObject, attribute: str) -> bool:
    if attribute == "shape":
        return obj.shape == SHAPES[0]
    if attribute == "colour":
        return obj.colour == COLOURS[0]
    if attribute == "position":
        return (obj.x + obj.y) % 2 == 0
    raise ValueError(f"unknown attribute {attribute!r}")


def rollout(
    env: GridWorld, n_steps: int, seed: int = 0
) -> Iterator[tuple[GridState, int, GridState]]:
    """Yield ``(state, action, next_state)`` transitions under a random policy."""
    rng = np.random.default_rng(seed)
    _, info = env.reset(seed=seed)
    state = info["state"]
    for _ in range(n_steps):
        action = int(rng.integers(N_ACTIONS))
        _, _, _, _, info = env.step(action)
        yield state, action, info["state"]
        state = info["state"]
