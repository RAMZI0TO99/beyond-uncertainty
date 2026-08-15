"""Transition dataset collection and the coverage report (Schedule W2 Fri).

The dataset is what every world model in this thesis trains on. Two properties
matter beyond simply having enough rows.

**Episode structure must be recorded.** The repair-acceptance test is a mixed
model with random intercepts for seed and for *episode within seed* (Plan §7.3),
because transitions from one episode are temporally correlated and treating them
as independent produces intervals that are too narrow. That test creates the
ground-truth label for H3, so the episode index is not bookkeeping -- it is an
input to the label. It has to be captured here, at collection, because it cannot
be reconstructed later.

**Coverage must be measured, not assumed.** The transition rule concerns
passability, so a dataset without attempted moves into objects cannot teach it,
however many rows it has. A policy that starved those transitions would make
Experiment 1's "estimation failure" family measure coverage rather than sample
size. The report below is the evidence that it did not, and Plan §13.2 requires
that evidence to accompany the PPO substitution rather than be taken on trust.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ..config import UnitSpec
from .gridworld import N_ACTIONS, SHAPES, GridState, GridWorld, is_passable
from .policy import ExploratoryPolicy

#: Steps per episode before the environment is reset with a fresh layout.
DEFAULT_EPISODE_LENGTH = 50


class Policy(Protocol):
    def act(self, state: GridState) -> int: ...


@dataclass(frozen=True)
class CoverageReport:
    """What the collected data actually contains, by the axes that matter."""

    n_transitions: int
    n_episodes: int
    #: Literal Schedule W2 Fri requirement: (shape, action) pairs.
    shape_action: dict[str, int]
    #: The general version: (causal class, action). For the default
    #: configuration the causal attribute *is* shape and the two agree, but
    #: when the configuration rotates the causal attribute to colour or
    #: position, this is the axis the dynamics actually turn on.
    causal_action: dict[str, int]
    #: Attempted moves into an occupied cell, by causal class. These are the
    #: transitions that carry the rule.
    bumps: dict[str, int]
    #: Fraction of transitions in which the agent's move was blocked.
    blocked_fraction: float
    #: Fraction of transitions that changed the agent's position.
    moved_fraction: float

    def shape_action_coverage(self, min_count: int = 10) -> float:
        cells = len(SHAPES) * N_ACTIONS
        return sum(1 for v in self.shape_action.values() if v >= min_count) / cells

    def is_adequate(self, min_bumps: int = 30, min_coverage: float = 0.9) -> bool:
        """Whether the data can support learning the rule at all.

        Both classes must have been bumped enough times: a dataset that only
        ever walked through passable objects shows one half of the rule.

        A *small* dataset reporting False is not a policy failure and must not
        be read as one. Plan §3.2.1 defines estimation failure to include data
        that "does not cover the relevant region of the state-action space",
        provided more data from the same generating process fixes it -- which
        the bump counts do, rising monotonically with dataset size. So thin
        coverage at n=100 is the Experiment 1 manipulation working, on the
        plan's own definition, rather than a confound in it.

        What this flag is for is the opposite case: a *large* dataset that still
        lacks the informative transitions. That would mean the policy, not the
        sample size, is the binding constraint, and every "estimation failure"
        label downstream would be measuring the wrong thing.
        """
        return (
            min(self.bumps.get("pass", 0), self.bumps.get("block", 0)) >= min_bumps
            and self.shape_action_coverage() >= min_coverage
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_transitions": self.n_transitions,
            "n_episodes": self.n_episodes,
            "shape_action": self.shape_action,
            "causal_action": self.causal_action,
            "bumps": self.bumps,
            "blocked_fraction": self.blocked_fraction,
            "moved_fraction": self.moved_fraction,
            "shape_action_coverage": self.shape_action_coverage(),
            "adequate": self.is_adequate(),
        }

    def summary(self) -> str:
        lines = [
            f"transitions {self.n_transitions}  episodes {self.n_episodes}",
            f"moved {self.moved_fraction:.1%}   blocked {self.blocked_fraction:.1%}",
            f"bumps by causal class: pass={self.bumps.get('pass', 0)} "
            f"block={self.bumps.get('block', 0)}",
            f"(shape, action) cells with >=10 observations: "
            f"{self.shape_action_coverage():.0%}",
            f"adequate for learning the rule: {self.is_adequate()}",
        ]
        return "\n".join(lines)


@dataclass
class TransitionDataset:
    """(s, a, s') transitions with the episode structure Plan §7.3 needs."""

    obs: np.ndarray
    action: np.ndarray
    next_obs: np.ndarray
    episode: np.ndarray
    step: np.ndarray
    unit: UnitSpec
    coverage: CoverageReport
    seed: int

    def __len__(self) -> int:
        return len(self.action)

    @property
    def obs_dim(self) -> int:
        return self.obs.shape[1]

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            obs=self.obs,
            action=self.action,
            next_obs=self.next_obs,
            episode=self.episode,
            step=self.step,
            meta=json.dumps(
                {
                    "unit": {
                        k: list(v) if isinstance(v, tuple) else v
                        for k, v in self.unit.__dict__.items()
                    },
                    "seed": self.seed,
                    "coverage": self.coverage.to_dict(),
                }
            ),
        )
        return path

    @classmethod
    def load(cls, path: str | Path) -> TransitionDataset:
        z = np.load(Path(path), allow_pickle=False)
        meta = json.loads(str(z["meta"]))
        unit_fields = dict(meta["unit"])
        unit_fields["withheld_features"] = tuple(unit_fields["withheld_features"])
        cov = dict(meta["coverage"])
        return cls(
            obs=z["obs"],
            action=z["action"],
            next_obs=z["next_obs"],
            episode=z["episode"],
            step=z["step"],
            unit=UnitSpec(**unit_fields),
            seed=int(meta["seed"]),
            coverage=CoverageReport(
                n_transitions=cov["n_transitions"],
                n_episodes=cov["n_episodes"],
                shape_action=cov["shape_action"],
                causal_action=cov["causal_action"],
                bumps=cov["bumps"],
                blocked_fraction=cov["blocked_fraction"],
                moved_fraction=cov["moved_fraction"],
            ),
        )


def collect(
    unit: UnitSpec,
    n_transitions: int | None = None,
    *,
    seed: int = 0,
    episode_length: int = DEFAULT_EPISODE_LENGTH,
    policy: Policy | None = None,
) -> TransitionDataset:
    """Collect exactly ``n_transitions`` transitions under ``policy``.

    Defaults to the unit's own ``n_transitions``, so a condition's dataset size
    comes from the statistical unit rather than from a call site -- the same
    reason the environment takes a UnitSpec (D-017).

    Episodes are fixed-length and each begins with a fresh environment layout,
    so the dataset spans many object arrangements rather than one.
    """
    n = unit.n_transitions if n_transitions is None else n_transitions
    if n <= 0:
        raise ValueError(f"n_transitions must be positive, got {n}")

    env = GridWorld(unit)
    pol = ExploratoryPolicy(unit, seed=seed) if policy is None else policy

    obs_list: list[np.ndarray] = []
    next_list: list[np.ndarray] = []
    actions: list[int] = []
    episodes: list[int] = []
    steps: list[int] = []

    shape_action: Counter[str] = Counter()
    causal_action: Counter[str] = Counter()
    bumps: Counter[str] = Counter()
    blocked = moved = 0

    episode = 0
    while len(actions) < n:
        _, info = env.reset(seed=seed * 100_000 + episode)
        state: GridState = info["state"]

        for step in range(episode_length):
            if len(actions) >= n:
                break
            action = pol.act(state)
            nxt = env.transition(state, action)

            obs_list.append(env.encoder.encode(state))
            next_list.append(env.encoder.encode(nxt))
            actions.append(action)
            episodes.append(episode)
            steps.append(step)

            _tally(
                unit, state, action, nxt,
                shape_action, causal_action, bumps,
            )
            if nxt.agent != state.agent:
                moved += 1
            elif action != 4:  # a move that did not move: blocked
                blocked += 1

            state = nxt
        episode += 1

    total = len(actions)
    coverage = CoverageReport(
        n_transitions=total,
        n_episodes=episode,
        shape_action=dict(shape_action),
        causal_action=dict(causal_action),
        bumps=dict(bumps),
        blocked_fraction=blocked / total,
        moved_fraction=moved / total,
    )
    return TransitionDataset(
        obs=np.asarray(obs_list, dtype=np.float32),
        action=np.asarray(actions, dtype=np.int64),
        next_obs=np.asarray(next_list, dtype=np.float32),
        episode=np.asarray(episodes, dtype=np.int64),
        step=np.asarray(steps, dtype=np.int64),
        unit=unit,
        coverage=coverage,
        seed=seed,
    )


_DELTAS = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}


def _tally(
    unit: UnitSpec,
    state: GridState,
    action: int,
    nxt: GridState,
    shape_action: Counter,
    causal_action: Counter,
    bumps: Counter,
) -> None:
    """Record what this transition contributes to coverage."""
    ax, ay = state.agent

    # (shape, action) over adjacent objects -- the literal W2 Fri requirement.
    for dx, dy in _DELTAS.values():
        obj = state.object_at((ax + dx, ay + dy))
        if obj is not None:
            shape_action[f"{obj.shape}|{action}"] += 1
            cls = "pass" if is_passable(obj, unit.causal_attribute) else "block"
            causal_action[f"{cls}|{action}"] += 1

    # A bump is an attempted move into an occupied cell: the transition that
    # actually carries the passability rule.
    if action in _DELTAS:
        dx, dy = _DELTAS[action]
        target = state.object_at((ax + dx, ay + dy))
        if target is not None:
            cls = "pass" if is_passable(target, unit.causal_attribute) else "block"
            bumps[cls] += 1
