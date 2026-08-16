"""The training loop (Schedule W3 Tue).

Its stated purpose is narrow and worth restating, because every choice below
follows from it: *"early stopping on a held-out split, so 'insufficient data' is
never confounded with 'insufficient training'."* Experiment 1 induces estimation
failure by shrinking the dataset. If a small-data condition also happened to be
under-trained, the sweep would measure optimisation effort rather than sample
size, and H1 would be testing the wrong proposition.

A separate validation pool, not a slice of training (D-052)
-----------------------------------------------------------
Validation comes from its own generating stream, never from carving up the
training set. Two reasons, both found the hard way.

**A slice makes the held-out set a function of dataset size.** Holding out every
k-th episode of a nested prefix gave the N=250 condition one validation episode
and the N=5000 condition twenty. Dataset size then changed the training data,
the validation composition, the validation sample size, the early-stopping noise
and the chance of selecting a lucky checkpoint -- all at once, and worst at
small N, which is where Experiment 1's conclusion is decided.

**A slice also spends the registered N on validation.** A "100-transition"
condition trained on 50. The registered N is training transitions; validation
and evaluation are separate pools and do not count against it.

Transitions inside one episode remain temporally correlated -- the fact that
makes Plan §7.3 require random intercepts for episode within seed -- so the
pools are whole episodes and the bootstrap resamples whole episodes.

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


def episode_indices(dataset: TransitionDataset) -> dict[int, np.ndarray]:
    """Transition indices grouped by episode -- the unit the bootstrap resamples."""
    return {
        int(e): np.flatnonzero(dataset.episode == e)
        for e in np.unique(dataset.episode)
    }


@dataclass
class TrainResult:
    """What a fit produced, and enough of how it got there to audit it."""

    best_epoch: int
    best_val_position: float
    epochs_run: int
    stopped_early: bool
    history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    n_train: int = 0
    n_validation: int = 0

    def curve(self, key: str) -> tuple[float, ...]:
        return tuple(row[key] for row in self.history)


def train(
    model: WorldModel,
    train_data: TransitionDataset,
    validation: TransitionDataset,
    config: TrainConfig | None = None,
    *,
    rng: np.random.Generator,
    train_index: np.ndarray | None = None,
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

        train_index: optional transition indices into ``train_data``, for the
            ensemble's per-member bootstrap resample. The validation pool is
            never resampled, so per-member errors stay comparable.

    Restores the best checkpoint before returning, so the model a caller holds
    afterwards is the one the validation loss selected, not the last one trained.
    """
    config = config or TrainConfig()

    # The evaluation pool must never reach checkpoint selection, and "train()
    # has no parameter called evaluation" was not that guarantee -- the pools
    # share a type, so `train(model, pools.train, pools.evaluation, ...)`
    # simply worked, and every reported number would have been selected on
    # (D-055). Provenance is checked instead of the signature.
    if train_data.pool != "train":
        raise ValueError(
            f"training data came from the {train_data.pool!r} pool; only the "
            "training pool may be trained on"
        )
    if validation.pool != "validation":
        raise ValueError(
            f"validation data came from the {validation.pool!r} pool. Early "
            "stopping and checkpoint selection may only read the validation "
            "pool -- the evaluation pool exists so reported error, disagreement "
            "and failure sets are never selected on."
        )

    obs = torch.as_tensor(train_data.obs)
    action = torch.as_tensor(train_data.action)
    next_obs = torch.as_tensor(train_data.next_obs)

    v_obs = torch.as_tensor(validation.obs)
    v_action = torch.as_tensor(validation.action)
    v_next = torch.as_tensor(validation.next_obs)

    train_idx = torch.as_tensor(
        np.arange(len(train_data)) if train_index is None else train_index,
        dtype=torch.long,
    )
    val_idx = torch.arange(len(validation), dtype=torch.long)

    _assert_trainable(model, obs, action, next_obs, train_idx, "training")
    _assert_trainable(model, v_obs, v_action, v_next, val_idx, "validation")

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

        val = _evaluate(model, v_obs, v_action, v_next, val_idx)
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
        n_train=len(train_idx),
        n_validation=len(validation),
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
