"""The training loop (Schedule W3 Tue).

Its stated purpose is narrow and worth restating, because every choice below
follows from it: *"early stopping on a held-out split, so 'insufficient data' is
never confounded with 'insufficient training'."* Experiment 1 induces estimation
failure by shrinking the dataset. If a small-data condition also happened to be
under-trained, the sweep would measure optimisation effort rather than sample
size, and H1 would be testing the wrong proposition.

Split by episode, never by transition
-------------------------------------
Transitions inside one episode are temporally correlated -- the same fact that
makes Plan §7.3 require random intercepts for episode within seed. A
transition-level split therefore puts near-duplicates of training rows into
validation, early stopping fires late, and the held-out loss is optimistic in
proportion to how correlated the data is. That is worst in exactly the
small-data conditions Experiment 1 depends on.

**Strided rather than contiguous.** The held-out episodes are every k-th, not
the last k-th. The scripted policy carries its coverage counters *across*
episodes (`ExploratoryPolicy.visits`), so its action distribution drifts as a
collection proceeds -- measured over 100 episodes, the fraction of transitions
that moved the agent falls from 0.543 in the first fifth to 0.476 in the last,
and the action distribution shifts with it. A contiguous tail split would hold
out a distribution the model was never trained on and call the gap
generalisation. Striding also keeps the validation episodes *identical across
dataset sizes*, because Experiment 1's datasets are nested prefixes (D-030) --
so the six conditions in a data-size sweep differ in training data alone.

What early stopping is allowed to watch (D-047)
-----------------------------------------------
The **movement-position validation loss, and nothing else**. The activation term
is auxiliary: it trains a detached head on `interact` transitions and is logged
separately, but it may not influence when training stops or which checkpoint is
kept. Nor is there a global gradient-norm clip -- one clip spanning both
parameter groups would let a large activation-head gradient rescale the trunk
gradient indirectly, reintroducing through the optimiser exactly the coupling
the detach removes.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch

from ..config import TrainConfig
from ..env.collect import TransitionDataset
from .world_model import Losses, WorldModel, losses


@dataclass(frozen=True)
class EpisodeSplit:
    """A held-out split taken at the episode level, never the transition level."""

    train: np.ndarray
    val: np.ndarray
    train_episodes: tuple[int, ...]
    val_episodes: tuple[int, ...]

    def __post_init__(self) -> None:
        overlap = set(self.train_episodes) & set(self.val_episodes)
        if overlap:
            raise ValueError(f"episodes {sorted(overlap)} are in both splits")


def split_by_episode(
    dataset: TransitionDataset, val_fraction: float
) -> EpisodeSplit:
    """Hold out every k-th episode, with k derived from ``val_fraction``.

    Deterministic and RNG-free: the split is a function of the dataset's episode
    structure, so it is reproducible from the config alone and identical across
    the nested-prefix datasets of a data-size sweep.
    """
    if not 0.0 < val_fraction < 1.0:
        raise ValueError(f"val_fraction must lie in (0, 1), got {val_fraction}")

    episodes = np.unique(dataset.episode)
    if len(episodes) < 2:
        raise ValueError(
            f"{len(episodes)} episode(s) in this dataset; an episode-level split "
            "needs at least two. Collect more transitions or shorten episodes -- "
            "do not fall back to a transition-level split, which leaks."
        )

    stride = max(2, int(round(1.0 / val_fraction)))
    val_episodes = tuple(int(e) for e in episodes[::stride])
    train_episodes = tuple(int(e) for e in episodes if int(e) not in set(val_episodes))
    if not train_episodes:
        raise ValueError("the split left no training episodes")

    val_mask = np.isin(dataset.episode, val_episodes)
    return EpisodeSplit(
        train=np.flatnonzero(~val_mask),
        val=np.flatnonzero(val_mask),
        train_episodes=train_episodes,
        val_episodes=val_episodes,
    )


@dataclass
class TrainResult:
    """What a fit produced, and enough of how it got there to audit it."""

    best_epoch: int
    best_val_position: float
    epochs_run: int
    stopped_early: bool
    history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    split: EpisodeSplit | None = None

    def curve(self, key: str) -> tuple[float, ...]:
        return tuple(row[key] for row in self.history)


def train(
    model: WorldModel,
    dataset: TransitionDataset,
    config: TrainConfig | None = None,
    *,
    rng: np.random.Generator,
    split: EpisodeSplit | None = None,
    logger: Any | None = None,
) -> TrainResult:
    """Fit ``model`` with early stopping on the movement-position validation loss.

    Args:
        rng: generator for minibatch order. Required for the same reason weight
            initialisation requires one (D-047): batch order affects the fitted
            model, and torch's global RNG would make it a function of process
            history rather than of ``(unit_id, seed, member)``.
        logger: optional :class:`~bu.metrics.RunLogger`. One record per epoch,
            carrying both loss terms separately -- the schedule's "loss curve
            logged", and the only form in which a figure can be regenerated
            without rerunning the fit.

        split: an explicit split, for callers that must control it. The
            ensemble trainer supplies one per member: a **bootstrap-resampled
            training set against the shared, unresampled validation set**, so
            per-member validation errors are comparable to each other.

    Restores the best checkpoint before returning, so the model a caller holds
    afterwards is the one the validation loss selected, not the last one trained.
    """
    config = config or TrainConfig()
    split = split if split is not None else split_by_episode(dataset, config.val_fraction)

    obs = torch.as_tensor(dataset.obs)
    action = torch.as_tensor(dataset.action)
    next_obs = torch.as_tensor(dataset.next_obs)

    train_idx = torch.as_tensor(split.train, dtype=torch.long)
    val_idx = torch.as_tensor(split.val, dtype=torch.long)

    _assert_trainable(model, obs, action, next_obs, train_idx, "training")
    _assert_trainable(model, obs, action, next_obs, val_idx, "validation")

    optimiser = torch.optim.Adam(model.parameters(), lr=config.lr)
    # No global gradient-norm clip. One clip spanning both parameter groups
    # would rescale the trunk gradient whenever the activation head's gradient
    # was large, reintroducing through the optimiser the coupling the detached
    # head removes (D-047). Per-group clipping is the alternative if a fit ever
    # proves unstable; nothing here has, so nothing is clipped.

    best_val = float("inf")
    best_epoch = -1
    best_state: dict[str, torch.Tensor] | None = None
    history: list[dict[str, Any]] = []
    stopped_early = False
    epoch = 0

    for epoch in range(config.max_epochs):
        model.train()
        order = torch.as_tensor(rng.permutation(len(train_idx)), dtype=torch.long)
        epoch_position = epoch_activation = 0.0
        n_batches = 0

        for start in range(0, len(order), config.batch_size):
            batch = train_idx[order[start : start + config.batch_size]]
            out = losses(model, obs[batch], action[batch], next_obs[batch])
            optimiser.zero_grad(set_to_none=True)
            out.total.backward()
            optimiser.step()
            epoch_position += float(out.position.detach())
            epoch_activation += float(out.activation.detach())
            n_batches += 1

        val = _evaluate(model, obs, action, next_obs, val_idx)
        row = {
            "epoch": epoch,
            "train_position": epoch_position / n_batches,
            "train_activation": epoch_activation / n_batches,
            # The only quantity early stopping is permitted to read (D-047).
            "val_position": float(val.position),
            # Logged, never watched.
            "val_activation": float(val.activation),
            "n_movement_val": val.n_movement,
            "n_interact_val": val.n_interact,
        }
        history.append(row)
        if logger is not None:
            logger.log(**row)

        if row["val_position"] < best_val:
            best_val = row["val_position"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        elif epoch - best_epoch >= config.patience:
            stopped_early = True
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    return TrainResult(
        best_epoch=best_epoch,
        best_val_position=best_val,
        epochs_run=epoch + 1,
        stopped_early=stopped_early,
        history=tuple(history),
        split=split,
    )


# --- helpers --------------------------------------------------------------


def _evaluate(
    model: WorldModel,
    obs: torch.Tensor,
    action: torch.Tensor,
    next_obs: torch.Tensor,
    idx: torch.Tensor,
) -> Losses:
    model.eval()
    with torch.no_grad():
        return losses(model, obs[idx], action[idx], next_obs[idx])


def _assert_trainable(
    model: WorldModel,
    obs: torch.Tensor,
    action: torch.Tensor,
    next_obs: torch.Tensor,
    idx: torch.Tensor,
    what: str,
) -> None:
    """Fail loudly rather than optimise or select on nothing (D-047).

    A split with no movement transitions would leave the primary task with no
    signal while the run still produced a loss curve and a "trained" model --
    the failure that looks most like success.
    """
    if len(idx) == 0:
        raise ValueError(f"the {what} split is empty")
    try:
        out = losses(model, obs[idx], action[idx], next_obs[idx])
    except ValueError as exc:  # losses() raises on an empty movement set
        raise ValueError(
            f"the {what} split contains no movement transitions, so the "
            "primary position task has no signal there. A run would still "
            "produce a loss curve and a 'trained' model, which is the failure "
            "that looks most like success."
        ) from exc
    if out.n_interact == 0:
        raise ValueError(
            f"no interact transitions in the {what} split; the auxiliary head "
            "would train or be scored on nothing"
        )
