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
from ..config import TrainConfig, UnitSpec
from ..env.collect import TransitionDataset
from ..streams import stream
from .train import EpisodeSplit, TrainResult, split_by_episode, train
from .world_model import WorldModel

Granularity = Literal["episode", "transition"]


def bootstrap_split(
    dataset: TransitionDataset,
    base: EpisodeSplit,
    rng: np.random.Generator,
    *,
    granularity: Granularity = "episode",
    ratio: float = 1.0,
) -> EpisodeSplit:
    """Resample the training side of ``base``; leave validation untouched.

    Args:
        granularity: ``"episode"`` draws whole episodes with replacement -- a
            block bootstrap, which respects the temporal correlation that makes
            an episode the unit of near-duplication. ``"transition"`` draws rows
            with replacement, which is the classical bootstrap and treats
            correlated rows as exchangeable.
        ratio: resample size as a fraction of the training set.
    """
    if ratio <= 0:
        raise ValueError(f"bootstrap ratio must be positive, got {ratio}")

    if granularity == "transition":
        n = max(1, int(round(len(base.train) * ratio)))
        drawn = rng.choice(base.train, size=n, replace=True)
        return EpisodeSplit(
            train=np.sort(drawn),
            val=base.val,
            train_episodes=base.train_episodes,
            val_episodes=base.val_episodes,
        )

    if granularity != "episode":
        raise ValueError(f"unknown bootstrap granularity {granularity!r}")

    episodes = np.array(base.train_episodes)
    n = max(1, int(round(len(episodes) * ratio)))
    drawn = rng.choice(episodes, size=n, replace=True)

    # Concatenate the transitions of every drawn episode, with multiplicity: an
    # episode drawn twice contributes its rows twice, which is what gives the
    # bootstrap its weight distribution.
    by_episode = {int(e): np.flatnonzero(dataset.episode == e) for e in np.unique(episodes)}
    train = np.concatenate([by_episode[int(e)] for e in drawn]) if len(drawn) else np.array([], int)

    return EpisodeSplit(
        train=train,
        val=base.val,
        train_episodes=tuple(int(e) for e in drawn),
        val_episodes=base.val_episodes,
    )


@dataclass
class Ensemble:
    """K models fitted to the same condition, differing only by their streams."""

    unit: UnitSpec
    members: tuple[WorldModel, ...]
    results: tuple[TrainResult, ...]
    split: EpisodeSplit
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
    dataset: TransitionDataset,
    config: TrainConfig | None = None,
    *,
    stage: str,
    seed: int,
    granularity: Granularity = "episode",
    logger: Any | None = None,
) -> Ensemble:
    """Fit ``config.ensemble_size`` members and log each one's validation error.

    Member ``k`` draws from ``(unit, stage, purpose, seed, member=k)`` for each
    of ``bootstrap``, ``init`` and ``batch``. Nothing about a member depends on
    the order members happen to be trained in, so a member can be refitted alone
    and reproduce exactly.
    """
    config = config or TrainConfig()
    base = split_by_episode(dataset, config.val_fraction)

    members: list[WorldModel] = []
    results: list[TrainResult] = []

    for k in range(config.ensemble_size):
        member_split = bootstrap_split(
            dataset,
            base,
            stream(unit, stage, "bootstrap", seed, member=k),
            granularity=granularity,
            ratio=config.bootstrap_ratio,
        )
        model = WorldModel(unit, stream(unit, stage, "init", seed, member=k))
        result = train(
            model,
            dataset,
            config,
            rng=stream(unit, stage, "batch", seed, member=k),
            split=member_split,
        )
        members.append(model)
        results.append(result)

        if logger is not None:
            # Per-member validation error is the schedule's acceptance
            # criterion, and it is logged per member rather than aggregated:
            # the spread across members is the quantity H1 and H2 are about,
            # and a mean would discard exactly it.
            logger.log(
                member=k,
                val_position=result.best_val_position,
                best_epoch=result.best_epoch,
                epochs_run=result.epochs_run,
                stopped_early=result.stopped_early,
                n_train=len(member_split.train),
                n_unique_train_episodes=len(set(member_split.train_episodes)),
                granularity=granularity,
            )

    return Ensemble(
        unit=unit,
        members=tuple(members),
        results=tuple(results),
        split=base,
        granularity=granularity,
    )


def default_ensemble_size() -> int:
    """Plan §14.2's default, swept at 3/5/10 in the Week 14 ablation."""
    return K.DEFAULT_ENSEMBLE_SIZE
