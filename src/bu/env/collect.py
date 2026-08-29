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

import dataclasses
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from .. import constants as K
from ..config import Arm, UnitSpec
from ..streams import POOL_PURPOSES, STREAM_VERSION, is_confirmatory, stream
from .gridworld import INTERACT, N_ACTIONS, SHAPES, GridState, GridWorld, is_passable
from .policy import ExploratoryPolicy

#: Steps per episode before the environment is reset with a fresh layout.
#: Preregistered in constants.py (D-052); re-exported here for callers.
DEFAULT_EPISODE_LENGTH = K.EPISODE_LENGTH


def expected_size(effective: UnitSpec, pool: str, episode_length: int) -> int:
    """The one legal size for a pool: registered N, or a frozen episode count."""
    if pool == "train":
        return effective.n_transitions
    if pool == "validation":
        return K.VALIDATION_EPISODES * episode_length
    if pool == "evaluation":
        return K.EVALUATION_EPISODES * episode_length
    raise ValueError(f"unknown pool {pool!r}")


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
    #: Fraction of transitions in which a move was refused by an object --
    #: the passability rule firing. Kept apart from wall blocks: they are
    #: different mechanisms, and only this one carries the rule under study.
    blocked_by_object_fraction: float
    #: Fraction refused by a boundary wall. Learnable, but not the manipulation.
    blocked_by_wall_fraction: float
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
            "blocked_by_object_fraction": self.blocked_by_object_fraction,
            "blocked_by_wall_fraction": self.blocked_by_wall_fraction,
            "moved_fraction": self.moved_fraction,
            "shape_action_coverage": self.shape_action_coverage(),
            "adequate": self.is_adequate(),
        }

    def summary(self) -> str:
        lines = [
            f"transitions {self.n_transitions}  episodes {self.n_episodes}",
            f"moved {self.moved_fraction:.1%}   "
            f"blocked by object {self.blocked_by_object_fraction:.1%}   "
            f"by wall {self.blocked_by_wall_fraction:.1%}",
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
    #: The **effective** unit -- what was actually generated.
    unit: UnitSpec
    coverage: CoverageReport
    seed: int
    #: Frozen experimental procedure, recorded so a dataset states the
    #: generator that produced it rather than relying on whichever constant is
    #: checked out (D-054).
    episode_length: int = K.EPISODE_LENGTH
    pool: str = "train"
    #: The **unresolved** unit, the arm and the stage: together with `pool` and
    #: `stream_version` these are exactly what the generating stream was keyed
    #: on (D-056). Without them a repaired dataset cannot reconstruct its own
    #: stream, and a feature-repair dataset is indistinguishable from a baseline
    #: whose unit already had the restored features.
    source_unit: UnitSpec | None = None
    arm: str = "baseline"
    stage: str = "pilot"
    stream_version: int = STREAM_VERSION

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
                    # dataclasses.asdict rather than __dict__: the latter
                    # happens to work today but breaks the moment UnitSpec gains
                    # __slots__ or a non-field attribute.
                    "unit": {
                        k: list(v) if isinstance(v, tuple) else v
                        for k, v in dataclasses.asdict(self.unit).items()
                    },
                    "source_unit": {
                        k: list(v) if isinstance(v, tuple) else v
                        for k, v in dataclasses.asdict(
                            self.source_unit or self.unit
                        ).items()
                    },
                    "arm": self.arm,
                    "stage": self.stage,
                    "stream_version": self.stream_version,
                    "seed": self.seed,
                    "episode_length": self.episode_length,
                    "pool": self.pool,
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
            # Never stamp a historical dataset with the currently checked-out
            # constant -- that is the opposite of a provenance guarantee
            # (D-055). A record that does not state its generator is rejected.
            episode_length=_require_provenance(meta, "episode_length"),
            pool=_require_provenance(meta, "pool"),
            source_unit=UnitSpec(**{
                **_require_provenance(meta, "source_unit"),
                "withheld_features": tuple(meta["source_unit"]["withheld_features"]),
            }),
            arm=_require_provenance(meta, "arm"),
            stage=_require_provenance(meta, "stage"),
            stream_version=_require_provenance(meta, "stream_version"),
            coverage=CoverageReport(
                n_transitions=cov["n_transitions"],
                n_episodes=cov["n_episodes"],
                shape_action=cov["shape_action"],
                causal_action=cov["causal_action"],
                bumps=cov["bumps"],
                blocked_by_object_fraction=cov["blocked_by_object_fraction"],
                blocked_by_wall_fraction=cov["blocked_by_wall_fraction"],
                moved_fraction=cov["moved_fraction"],
            ),
        )


def collect(
    unit: UnitSpec,
    n_transitions: int | None = None,
    *,
    seed: int = 0,
    stage: str = "pilot",
    arm: str = "baseline",
    pool: str = "train",
    episode_length: int = DEFAULT_EPISODE_LENGTH,
    policy: Policy | None = None,
) -> TransitionDataset:
    """Collect exactly ``n_transitions`` transitions under ``policy``.

    Defaults to the unit's own ``n_transitions``, so a condition's dataset size
    comes from the statistical unit rather than from a call site -- the same
    reason the environment takes a UnitSpec (D-017).

    Episodes are fixed-length and each begins with a fresh environment layout,
    so the dataset spans many object arrangements rather than one.

    Randomness comes from the named ``env`` and ``policy`` streams (D-030), keyed
    on ``stage``'s comparison group. Two consequences worth stating, because
    both are design requirements rather than side effects:

    * within Experiment 1, the six dataset sizes are **nested prefixes** -- the
      generator flows across episodes instead of being reseeded per episode, so
      collecting 250 transitions reproduces the first 100 exactly;
    * across the configuration sweep, two different units at the same seed draw
      **independent** layouts, because the key includes the unit rather than the
      seed alone. That coupling is what Q-008 was raised about, and confidence
      intervals taken over units depend on its absence.

    ``pool`` selects which of three **physically separate** draws this is
    (D-052). Validation and evaluation come from their own streams rather than
    from a slice of training, so no transition can appear in two pools and a
    condition's held-out data does not depend on how much training data it
    happened to have. **The registered N is training transitions only.**
    """
    if pool not in POOL_PURPOSES:
        raise ValueError(f"unknown pool {pool!r}; expected {sorted(POOL_PURPOSES)}")
    # Episode length is frozen experimental procedure (D-052, D-054): it sets
    # how many independent clusters a condition contains and therefore what a
    # block bootstrap can resample. A development override is allowed and is
    # recorded on the dataset; a confirmatory seed may not use one.
    if policy is not None and is_confirmatory(seed):
        raise ValueError(
            f"a custom policy was injected on confirmatory seed {seed}. The "
            "behaviour policy is frozen experimental procedure (D-051, D-054) "
            "and is not a call-site argument for a run that reaches a result."
        )
    if episode_length != K.EPISODE_LENGTH and is_confirmatory(seed):
        raise ValueError(
            f"episode_length={episode_length} on confirmatory seed {seed}; the "
            f"frozen value is {K.EPISODE_LENGTH} (D-052). Development overrides "
            "are permitted below CONFIRMATORY_SEED_BASE and are recorded on the "
            "dataset, but a confirmatory run may not change the procedure."
        )

    env_purpose, policy_purpose = POOL_PURPOSES[pool]
    # Stream identity comes from the UNRESOLVED unit; the environment and
    # encoder come from the EFFECTIVE one (D-055). Without the split, resolving
    # a feature repair changed `withheld_features`, which Experiment 2A's
    # comparison group does not exclude, so the repair drew a different
    # environment, validation and evaluation pool from its own baseline -- and
    # Plan §7.2 requires a repair to be scored on the same recorded failure set.
    effective = Arm(arm).resolve(unit)
    n = expected_size(effective, pool, episode_length) if n_transitions is None else n_transitions
    if n <= 0:
        raise ValueError(f"n_transitions must be positive, got {n}")
    # The guard belongs *here*, not only in collect_pools: a confirmatory caller
    # could otherwise reach this function directly and mint an evaluation pool
    # of any size (D-056). Every pool has one legal size on a confirmatory seed.
    if is_confirmatory(seed):
        want = expected_size(effective, pool, episode_length)
        if n != want:
            raise ValueError(
                f"n_transitions={n} for the {pool!r} pool on confirmatory seed "
                f"{seed}, but the frozen size is {want}. Dataset size is "
                "Experiment 1's manipulation and the pool sizes are frozen "
                "procedure (D-052); a confirmatory run may not choose either."
            )
    env = GridWorld(effective)
    env_rng = stream(unit, stage, env_purpose, seed)
    pol = (
        ExploratoryPolicy(effective, rng=stream(unit, stage, policy_purpose, seed))
        if policy is None
        else policy
    )

    obs_list: list[np.ndarray] = []
    next_list: list[np.ndarray] = []
    actions: list[int] = []
    episodes: list[int] = []
    steps: list[int] = []

    shape_action: Counter[str] = Counter()
    causal_action: Counter[str] = Counter()
    bumps: Counter[str] = Counter()
    blocked_object = blocked_wall = moved = 0

    episode = 0
    while len(actions) < n:
        # Stationarity: every episode starts from the same behaviour
        # distribution, so episodes are independent draws and a nested prefix
        # is a smaller sample of the *same* process rather than an earlier,
        # different one (D-051).
        if hasattr(pol, "reset"):
            pol.reset()
        _, info = env.reset(rng=env_rng)
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
                effective, state, action, nxt,
                shape_action, causal_action, bumps,
            )
            if nxt.agent != state.agent:
                moved += 1
            elif action != INTERACT:
                # A move that did not move. Which mechanism refused it matters:
                # only an object block is the passability rule firing.
                dx, dy = _DELTAS[action]
                target = (state.agent[0] + dx, state.agent[1] + dy)
                if state.object_at(target) is not None:
                    blocked_object += 1
                else:
                    blocked_wall += 1

            state = nxt
        episode += 1

    total = len(actions)
    coverage = CoverageReport(
        n_transitions=total,
        n_episodes=episode,
        shape_action=dict(shape_action),
        causal_action=dict(causal_action),
        bumps=dict(bumps),
        blocked_by_object_fraction=blocked_object / total,
        blocked_by_wall_fraction=blocked_wall / total,
        moved_fraction=moved / total,
    )
    return TransitionDataset(
        obs=np.asarray(obs_list, dtype=np.float32),
        action=np.asarray(actions, dtype=np.int64),
        next_obs=np.asarray(next_list, dtype=np.float32),
        episode=np.asarray(episodes, dtype=np.int64),
        step=np.asarray(steps, dtype=np.int64),
        unit=effective,
        coverage=coverage,
        seed=seed,
        episode_length=episode_length,
        pool=pool,
        source_unit=unit,
        arm=arm,
        stage=stage,
        stream_version=STREAM_VERSION,
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


@dataclass(frozen=True)
class Pools:
    """The three disjoint datasets a fit needs (D-052).

    ``train`` holds **exactly** the registered N transitions -- validation no
    longer eats into it, so a "100-transition condition" trains on 100. The
    other two are fixed-size and identical for every dataset size in a
    comparison group and for every ensemble member, so a data-size sweep varies
    training data and nothing else.
    """

    train: TransitionDataset
    validation: TransitionDataset
    evaluation: TransitionDataset


def collect_pools(
    unit: UnitSpec,
    *,
    stage: str,
    seed: int,
    arm: str = "baseline",
    n_transitions: int | None = None,
    episode_length: int = DEFAULT_EPISODE_LENGTH,
) -> Pools:
    """Training, validation and evaluation pools from three separate streams.

    ``unit`` is the **unresolved** unit and ``arm`` the repair applied to it.
    Keeping them apart is what makes the acceptance test paired: a baseline and
    all of its repairs draw the same environment, validation and evaluation
    streams, while the repair still changes what it is supposed to change
    (D-055).
    """
    common = dict(stage=stage, seed=seed, arm=arm, episode_length=episode_length)
    return Pools(
        train=collect(unit, n_transitions, pool="train", **common),
        validation=collect(unit, None, pool="validation", **common),
        evaluation=collect(unit, None, pool="evaluation", **common),
    )


def _require_provenance(meta: dict[str, Any], field: str) -> Any:
    if field not in meta:
        raise ValueError(
            f"dataset record has no {field!r}; it predates the provenance fields "
            "(D-055) and its generator is unknown. Regenerate it rather than "
            "assuming today's constants describe it."
        )
    return meta[field]
