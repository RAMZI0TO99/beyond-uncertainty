"""The bootstrap ensemble (Schedule W3 Wed).

The ensemble is not a modelling convenience here -- it *is* the measurement
instrument. H1 and H2 are both claims about **mean pairwise disagreement**
between members, so anything that changes how members differ changes the
dependent variable directly. Every choice below is therefore a methodological
one wearing implementation clothes.

Two sources of member diversity, both from named streams
--------------------------------------------------------
* **Bootstrap resampling** of the training data (`bootstrap` stream);
* **independent initialisation** (`init` stream), plus independent minibatch
  order (`batch` stream).

Keeping them in separate streams matters: it means the ensemble's diversity can
later be attributed, and that changing the resampling scheme cannot silently
shift the weights members start from.

The validation set is shared and never resampled
------------------------------------------------
Bootstrapping touches the **training** split only. Every member is scored on the
same held-out episodes, because per-member validation errors that were computed
on different data would not be comparable to one another -- and Week 3 Friday
compares them.

Resampling granularity is a live question (Q-011)
-------------------------------------------------
Default is **episode-level** (a block bootstrap), for the same reason the split
is episode-level: transitions inside an episode are near-duplicates, so
resampling them individually produces members whose datasets differ far less
than their nominal sample counts suggest. But the choice is not free of
consequence for H1, and it is flagged rather than settled -- see Q-011 and the
measurement in the delta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import torch

from .. import constants as K
from ..config import Arm, TrainConfig, UnitSpec
from ..env.collect import Pools, TransitionDataset
from ..streams import is_confirmatory, stream
from .train import TrainResult, episode_indices, train
from .world_model import WorldModel

Granularity = Literal["episode", "transition", "none"]


def bootstrap_episodes(
    dataset: TransitionDataset,
    rng: np.random.Generator,
    *,
    granularity: Granularity = "episode",
    ratio: float = 1.0,
) -> np.ndarray:
    """Transition indices for one member's resample of the **training** pool.

    Args:
        granularity: ``"episode"`` draws whole episodes with replacement -- a
            block bootstrap, and the **primary method** for H1 and H2 (D-053).
            ``"transition"`` draws rows, which treats correlated transitions as
            exchangeable and retains nearly every episode, suppressing the
            data-resampling component of disagreement. It is a labelled
            secondary sensitivity only and never determines a verdict.
        ratio: resample size as a fraction of the training pool.
    """
    if ratio <= 0:
        raise ValueError(f"bootstrap ratio must be positive, got {ratio}")

    if granularity == "transition":
        n = max(1, int(round(len(dataset) * ratio)))
        return np.sort(rng.choice(len(dataset), size=n, replace=True))

    if granularity == "none":
        # Initialisation-only ensemble: every member sees the whole pool, so
        # all disagreement comes from weights. A cleaner sensitivity than a
        # transition bootstrap, because it isolates the source rather than
        # blurring it (Sol, Q-011).
        return np.arange(len(dataset))

    if granularity != "episode":
        raise ValueError(f"unknown bootstrap granularity {granularity!r}")

    by_episode = episode_indices(dataset)
    episodes = np.array(sorted(by_episode))
    n = max(1, int(round(len(episodes) * ratio)))
    drawn = rng.choice(episodes, size=n, replace=True)
    return np.concatenate([by_episode[int(e)] for e in drawn])


@dataclass
class Ensemble:
    """K models fitted to the same condition, differing only by their streams."""

    #: The unresolved unit -- what keyed the streams.
    unit: UnitSpec
    #: What was actually built and trained.
    effective_unit: UnitSpec
    arm: str
    members: tuple[WorldModel, ...]
    results: tuple[TrainResult, ...]
    granularity: Granularity

    def __len__(self) -> int:
        return len(self.members)

    @property
    def val_position_errors(self) -> tuple[float, ...]:
        """Per-member held-out position loss, on the shared validation set."""
        return tuple(r.best_val_position for r in self.results)

    def member_predictions(
        self, obs: torch.Tensor, action: torch.Tensor
    ) -> torch.Tensor:
        """``(n_members, batch, position_dims)`` predicted next agent positions.

        Only the position head: H1 and H2 are claims about disagreement on the
        quantity the manipulated mechanism moves (D-032, DEV-007). Disagreement
        metrics themselves are Week 3 Friday; this is the tensor they read.
        """
        outputs = []
        for model in self.members:
            model.eval()
            with torch.no_grad():
                position, _ = model(obs, action)
            outputs.append(position)
        return torch.stack(outputs)


def train_ensemble(
    unit: UnitSpec,
    pools: Pools,
    config: TrainConfig | None = None,
    *,
    stage: str,
    seed: int,
    arm: str = "baseline",
    granularity: Granularity = "episode",
    logger: Any | None = None,
) -> Ensemble:
    """Fit ``config.ensemble_size`` members and log each one's validation error.

    ``unit`` is the **unresolved** unit and ``arm`` the repair applied to it —
    the same split the pools use, and for the same reason (D-056):

    * the **effective** unit builds the model, so a capacity repair actually
      gets the larger network and a feature repair gets the wider input;
    * the **unresolved** unit keys every named stream, so a repair's members
      initialise, resample and batch exactly as its baseline's did.

    Passing one unit for both was silently wrong in opposite directions. With
    the unresolved unit a capacity repair trained the *original small model* —
    the repair was never applied, no error was raised, and every capacity
    condition would have been labelled "repair failed". With the effective unit
    the model was right but the streams moved.

    Only the **training** pool is resampled. Validation and evaluation are fixed
    and shared, so per-member errors are comparable and the evaluation set is
    identical across members, dataset sizes and conditions (D-052).
    """
    config = config or TrainConfig()
    effective = Arm(arm).resolve(unit)
    if granularity != "episode" and is_confirmatory(seed):
        raise ValueError(
            f"granularity={granularity!r} on confirmatory seed {seed}. Episode "
            "block bootstrap is the fixed primary method (D-053); the other "
            "schemes are development diagnostics for the Week 3 Friday pilot "
            "and are not in the 8,197-fit plan (D-054). They are also not part "
            "of Config or run identity, so a non-primary confirmatory fit would "
            "occupy the same recorded identity as the primary one.\n\n"
            "Note this is a guard on THIS entry point, not proof that every "
            "confirmatory path is closed: bootstrap_episodes() plus "
            "train(train_index=...) still bypasses it. The confirmatory runner "
            "must own the rule when it exists (D-056)."
        )

    members: list[WorldModel] = []
    results: list[TrainResult] = []

    for k in range(config.ensemble_size):
        index = bootstrap_episodes(
            pools.train,
            stream(unit, stage, "bootstrap", seed, member=k),
            granularity=granularity,
            ratio=config.bootstrap_ratio,
        )
        model = WorldModel(effective, stream(unit, stage, "init", seed, member=k))
        result = train(
            model,
            pools.train,
            pools.validation,
            config,
            rng=stream(unit, stage, "batch", seed, member=k),
            train_index=index,
        )
        members.append(model)
        results.append(result)

        if logger is not None:
            # Per-member validation error is the schedule's acceptance
            # criterion, and it is logged per member rather than aggregated:
            # the spread across members is the quantity H1 and H2 are about,
            # and a mean would discard exactly it.
            n_unique = len(np.unique(pools.train.episode[index]))
            logger.log(
                member=k,
                val_position=result.best_val_position,
                best_epoch=result.best_epoch,
                epochs_run=result.epochs_run,
                stopped_early=result.stopped_early,
                n_train=len(index),
                n_unique_train_episodes=n_unique,
                granularity=granularity,
                arm=arm,
            )

    return Ensemble(
        unit=unit,
        effective_unit=effective,
        arm=arm,
        members=tuple(members),
        results=tuple(results),
        granularity=granularity,
    )


def default_ensemble_size() -> int:
    """Plan §14.2's default, swept at 3/5/10 in the Week 14 ablation."""
    return K.DEFAULT_ENSEMBLE_SIZE
