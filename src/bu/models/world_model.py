"""The world model (Schedule W3 Mon).

Predicts the next state from the current state and an action. This is the object
of diagnosis: everything in the thesis is downstream of *this* model failing, so
what it predicts and what its error means are design decisions rather than
implementation details.

What it predicts, and why not everything (D-032)
------------------------------------------------
The model outputs only the **dynamic** components of the next observation:

* the agent's next position -- two continuous dimensions, grid-normalised;
* each object's next activation bit -- Bernoulli, one per object.

Static object attributes -- position, shape, colour -- are **deterministic
passthrough**. They are copied from the current observation when a full next
state is reconstructed (:meth:`WorldModel.predict_next_obs`), and they never
enter the loss or the error score.

That is not a simplification, it is a correction of one. Measured on collected
data: 26 of 30 output dimensions never change within an episode, an identity
predictor -- output equals input -- scores MSE 0.0047, and 92.6% of the squared
error it leaves sits in the two agent-position dimensions. A full-state averaged
MSE therefore hides the passability rule behind dimensions any model copies
immediately, diluting the manipulated mechanism roughly fifteen-fold.

Worse, the dilution is not constant across conditions. The observation is 30
dimensions with every feature visible and 22 with shape withheld, so a
full-state mean would put the estimation and missing-feature families on
different error scales for reasons that are an artefact of the encoding rather
than of the manipulation -- and Plan §10.1's failure threshold, a fixed
percentile frozen permanently in Week 4, would inherit that.

A full *delta* target was also rejected: static deltas are zeros and reproduce
the same dilution in another form, and for agent position next-state and delta
prediction carry equivalent residual information.

The primary error (DEV-007)
---------------------------
:func:`primary_error` is the thesis's headline model-quality number: error on the
next agent position, over **movement-action transitions only**, grid-normalised.
The manipulated mechanism is passability, and its observable consequence is
whether the agent moved -- an ``interact`` step cannot be blocked, so it carries
no evidence about the rule. Activation error is a secondary metric and is
reported beside it, never averaged into it.

Randomness
----------
Weights initialise from the named ``init`` stream (D-030), drawn through the
supplied generator rather than torch's global RNG. Two reasons: ensemble members
must differ from one another in a way that is reproducible from the config
alone, and nothing about a model's initialisation may depend on the order in
which models happened to be constructed in a process.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn

from ..config import UnitSpec
from ..env.encoder import ObservationEncoder
from ..env.gridworld import INTERACT, N_ACTIONS

#: Actions that can be refused by the passability rule. ``interact`` cannot, so
#: it carries no evidence about the mechanism under study (DEV-007).
MOVEMENT_ACTIONS: tuple[int, ...] = (0, 1, 2, 3)

#: Hidden layers in the trunk. **Frozen, not a caller argument** (D-047). The
#: schedule fixes hidden *size* as Experiment 2B's swept axis; depth is held
#: constant so that experiment varies one thing. It was briefly a public
#: constructor parameter, which made a result-affecting quantity selectable at a
#: call site and absent from every run record -- the class of defect D-017 and
#: D-006 exist to prevent.
N_HIDDEN_LAYERS = 2

#: Architecture facts a run record should carry, so the model that trained is
#: recoverable from the record rather than from whichever code is checked out.
ARCHITECTURE: dict[str, object] = {
    "n_hidden_layers": N_HIDDEN_LAYERS,
    "activation": "relu",
    "action_encoding": "one_hot",
    "auxiliary_head": "detached",
}


@dataclass(frozen=True)
class DynamicLayout:
    """Which observation dimensions the model predicts, and which it copies.

    Derived from the encoder rather than hardcoded, because the observation
    width depends on what the condition withholds -- 30 dimensions with every
    feature visible, 22 with shape withheld. A model that assumed a width would
    be silently wrong for exactly the Experiment 2A conditions the thesis is
    about.
    """

    obs_dim: int
    position: tuple[int, ...]
    activation: tuple[int, ...]

    @property
    def dynamic(self) -> tuple[int, ...]:
        return self.position + self.activation

    @property
    def static(self) -> tuple[int, ...]:
        dynamic = set(self.dynamic)
        return tuple(i for i in range(self.obs_dim) if i not in dynamic)

    @property
    def n_outputs(self) -> int:
        return len(self.dynamic)


def dynamic_layout(encoder: ObservationEncoder) -> DynamicLayout:
    """Split an encoder's blocks into what changes and what cannot."""
    position: list[int] = []
    activation: list[int] = []
    for block in encoder.blocks:
        if block.name == "agent_position":
            position.extend(range(block.start, block.stop))
        elif block.name.endswith("_activated"):
            activation.extend(range(block.start, block.stop))
    if not position:
        raise ValueError("no agent_position block; the agent is never withholdable")
    return DynamicLayout(
        obs_dim=encoder.size,
        position=tuple(position),
        activation=tuple(activation),
    )


class WorldModel(nn.Module):
    """An MLP over (observation, one-hot action) with two heads.

    Built from a :class:`UnitSpec` for the same reason the environment is
    (D-017): ``hidden_size`` is a registered identity field swept by Experiment
    2B, so it must come from the statistical unit rather than from a call site,
    or a run record could state one capacity while another was trained.
    """

    def __init__(self, unit: UnitSpec, rng: np.random.Generator) -> None:
        """
        Args:
            unit: the configuration-condition. Supplies ``hidden_size``.
            rng: **required** -- a generator from the named ``init`` stream
                (D-030). Not optional, because an optional generator is one a
                caller forgets, and the fallback would be torch's global RNG:
                weights would then depend on process history rather than on
                ``(unit_id, seed, member)``, and ensemble members could
                silently coincide (D-047).
        """
        super().__init__()
        if rng is None:
            raise TypeError(
                "WorldModel requires a generator from the init stream; pass "
                "streams.stream(unit, stage, 'init', seed, member=k)"
            )
        self.unit = unit
        self.encoder = ObservationEncoder(
            n_objects=unit.n_objects,
            grid_size=unit.grid_size,
            withheld=unit.withheld_features,
        )
        self.layout = dynamic_layout(self.encoder)

        self.in_dim = self.encoder.size + N_ACTIONS
        hidden = unit.hidden_size

        trunk: list[nn.Module] = []
        width = self.in_dim
        for _ in range(N_HIDDEN_LAYERS):
            trunk += [nn.Linear(width, hidden), nn.ReLU()]
            width = hidden
        self.trunk = nn.Sequential(*trunk)

        #: Continuous, grid-normalised. MSE. Owns the trunk.
        self.position_head = nn.Linear(hidden, len(self.layout.position))
        #: Bernoulli logits, one per object. Binary cross-entropy, and it reads
        #: a **detached** trunk representation -- see :meth:`forward`.
        self.activation_head = nn.Linear(hidden, len(self.layout.activation))

        self.reset_parameters(rng)

    # --- initialisation ---------------------------------------------------

    def reset_parameters(self, rng: np.random.Generator) -> None:
        """Initialise every weight from ``rng`` (the ``init`` stream, D-030).

        Reproduces torch's default ``Linear`` bound, ``1/sqrt(fan_in)``, but
        draws through the supplied generator so initialisation is a function of
        ``(unit_id, seed, member)`` and of nothing else -- not of torch's global
        state, and not of construction order within a process.
        """
        for module in self.modules():
            if not isinstance(module, nn.Linear):
                continue
            fan_in = module.weight.shape[1]
            bound = 1.0 / math.sqrt(fan_in)
            with torch.no_grad():
                module.weight.copy_(
                    torch.as_tensor(
                        rng.uniform(-bound, bound, size=tuple(module.weight.shape)),
                        dtype=torch.float32,
                    )
                )
                module.bias.copy_(
                    torch.as_tensor(
                        rng.uniform(-bound, bound, size=tuple(module.bias.shape)),
                        dtype=torch.float32,
                    )
                )

    # --- forward ----------------------------------------------------------

    def forward(
        self, obs: torch.Tensor, action: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return ``(position, activation_logits)``.

        Logits rather than probabilities: the loss uses
        ``binary_cross_entropy_with_logits``, which is numerically stable in a
        way that sigmoid-then-BCE is not.
        """
        if obs.ndim != 2 or obs.shape[1] != self.encoder.size:
            raise ValueError(
                f"expected obs of shape (batch, {self.encoder.size}), got "
                f"{tuple(obs.shape)}. Observation width depends on what the "
                "condition withholds -- check the unit, not the caller."
            )
        h = self.trunk(torch.cat([obs, _one_hot(action, obs)], dim=1))
        # The position task owns the trunk (D-047). Detaching here lets the
        # auxiliary head learn while preventing activation loss from moving the
        # representation the position head reads. Measured before the change:
        # the two trunk gradients had cosine similarity around -0.1, so the
        # interference was mild but real, and removing it costs nothing.
        return self.position_head(h), self.activation_head(h.detach())

    def predict_next_obs(self, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        """A complete next observation, with **action-conditional** passthrough.

        Three copies rather than one (D-047), all outside the loss:

        * static object attributes -- they cannot change under any action;
        * the agent's position on an ``interact`` step -- ``interact`` never
          moves the agent;
        * every activation bit on a movement step -- a move never toggles one.

        The action-conditional copies are the same argument as the static one,
        applied to no-ops the *action* makes known rather than ones the
        encoding does. A head is used only where its component can actually
        change, so the model is never rewarded for reproducing a no-op it could
        have looked up.
        """
        position, logits = self(obs, action)
        out = obs.clone()

        move = _movement_mask(action)
        pos_idx = torch.as_tensor(self.layout.position, device=obs.device)
        act_idx = torch.as_tensor(self.layout.activation, device=obs.device)

        rows = torch.nonzero(move).reshape(-1)
        if rows.numel():
            out[rows[:, None], pos_idx[None, :]] = position[rows]
        rows = torch.nonzero(~move).reshape(-1)
        if rows.numel():
            out[rows[:, None], act_idx[None, :]] = torch.sigmoid(logits[rows])
        return out

    # --- targets ----------------------------------------------------------

    def targets(self, next_obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Extract the two supervised targets from an observed next state."""
        return (
            next_obs[:, list(self.layout.position)],
            next_obs[:, list(self.layout.activation)],
        )


@dataclass(frozen=True)
class Losses:
    """The two loss terms, kept apart because D-032 reports them apart.

    Both are unweighted and trained on disjoint transition sets, so neither can
    be traded off against the other by a constant nobody recorded.
    """

    position: torch.Tensor
    activation: torch.Tensor
    n_movement: int = 0
    n_interact: int = 0

    @property
    def total(self) -> torch.Tensor:
        """What the optimiser minimises.

        A plain sum. The gradients do not mix: the position term reaches the
        trunk, the activation term stops at its own head.
        """
        return self.position + self.activation


def losses(
    model: WorldModel,
    obs: torch.Tensor,
    action: torch.Tensor,
    next_obs: torch.Tensor,
) -> Losses:
    """Position MSE on movement steps; activation BCE on ``interact`` steps.

    **Action-conditional** (D-047). A movement action never toggles an
    activation bit and an ``interact`` never moves the agent, so training either
    head on the other's transitions teaches it to reproduce a known no-op --
    the same objection as full-state MSE, applied per action rather than per
    dimension.

    There is deliberately **no weighting argument**. Once the auxiliary head
    reads a detached representation and the two losses train on disjoint
    transitions, a cross-task weight has no methodological work left to do, and
    leaving one would be an unrecorded result-affecting knob.

    Raises when the batch has no movement transitions: the primary task would
    then train on nothing, and a training loop must fail loudly rather than
    quietly optimise the auxiliary task alone. An absence of ``interact``
    transitions is reported through ``Losses.n_interact`` rather than raised,
    so the caller can assert on its own batching.
    """
    move = _movement_mask(action)
    n_movement = int(move.sum())
    if n_movement == 0:
        raise ValueError(
            "no movement transitions in this batch; the primary position loss "
            "would train on nothing. Build batches that contain movement steps."
        )

    position, logits = model(obs, action)
    target_position, target_activation = model.targets(next_obs)

    position_loss = nn.functional.mse_loss(
        position[move], target_position[move]
    )

    n_interact = int((~move).sum())
    if n_interact:
        activation_loss = nn.functional.binary_cross_entropy_with_logits(
            logits[~move], target_activation[~move]
        )
    else:
        activation_loss = torch.zeros((), dtype=position_loss.dtype)

    return Losses(
        position=position_loss,
        activation=activation_loss,
        n_movement=n_movement,
        n_interact=n_interact,
    )


# --- the primary error score (DEV-007) ------------------------------------


def primary_error(
    model: WorldModel,
    obs: torch.Tensor,
    action: torch.Tensor,
    next_obs: torch.Tensor,
) -> torch.Tensor:
    """Per-transition error on the next agent position, movement actions only.

    The thesis's headline model-quality number. Returns one value per *movement*
    transition, so callers can take means, percentiles or mixed-effects models
    over the transitions themselves -- Plan §7.3's acceptance test needs the
    per-transition values, not a summary.

    Grid-normalised because the encoder already normalises positions into
    [0, 1], so the scale is fixed across grid sizes and conditions.

    Returns an empty tensor when the batch contains no movement transitions.
    That is a real case for a tiny evaluation batch, and returning ``nan`` from
    a mean over nothing is how a silently empty failure set gets averaged into
    a result.
    """
    mask = _movement_mask(action)
    if not bool(mask.any()):
        return torch.empty(0, dtype=torch.float32, device=obs.device)

    predicted, _ = model(obs[mask], action[mask])
    target, _ = model.targets(next_obs[mask])
    return torch.linalg.vector_norm(predicted - target, dim=1)


def activation_error(
    model: WorldModel,
    obs: torch.Tensor,
    action: torch.Tensor,
    next_obs: torch.Tensor,
) -> torch.Tensor:
    """Per-transition activation error on ``interact`` steps only.

    Secondary metric, reported beside the primary error and never inside it
    (D-032). Restricted to ``interact`` because a movement step cannot change
    an activation bit, so including those measures a copy (D-047).
    """
    interact = ~_movement_mask(action)
    if not bool(interact.any()):
        return torch.empty(0, dtype=torch.float32, device=obs.device)
    _, logits = model(obs[interact], action[interact])
    _, target = model.targets(next_obs[interact])
    return (torch.sigmoid(logits) - target).abs().mean(dim=1)


@dataclass(frozen=True)
class ActivationReport:
    """The auxiliary task, sliced so its number means something (D-047).

    All-action activation error is dominated by transitions where nothing can
    change, so it flatters any model that has learned to copy. These slices
    separate the copy from the prediction.

    ``copy_baseline`` is the score of emitting the *current* bit unchanged --
    the floor any useful auxiliary model must beat. Note that the remaining
    error must **not** be called irreducible without the INTERACT aliasing
    check: where object positions are visible the interact rule is
    deterministic, so which bit flips may well be predictable.
    """

    n_interact: int
    n_changed: int
    error_interact: float
    error_changed: float
    error_interact_unchanged: float
    copy_baseline_interact: float

    def summary(self) -> str:
        return (
            f"interact {self.n_interact} (changed {self.n_changed})  "
            f"err {self.error_interact:.4f}  on-change {self.error_changed:.4f}  "
            f"no-change {self.error_interact_unchanged:.4f}  "
            f"copy baseline {self.copy_baseline_interact:.4f}"
        )


def activation_report(
    model: WorldModel,
    obs: torch.Tensor,
    action: torch.Tensor,
    next_obs: torch.Tensor,
) -> ActivationReport:
    """Slice the auxiliary task the way Sol's ruling requires (D-047)."""
    interact = ~_movement_mask(action)
    idx = list(model.layout.activation)
    current = obs[interact][:, idx]
    target = next_obs[interact][:, idx]
    changed = (current != target).any(dim=1)

    if int(interact.sum()) == 0:
        return ActivationReport(0, 0, float("nan"), float("nan"), float("nan"), float("nan"))

    with torch.no_grad():
        _, logits = model(obs[interact], action[interact])
        error = (torch.sigmoid(logits) - target).abs().mean(dim=1)
    copy = (current - target).abs().mean(dim=1)

    def _mean(x: torch.Tensor) -> float:
        return float(x.mean()) if x.numel() else float("nan")

    return ActivationReport(
        n_interact=int(interact.sum()),
        n_changed=int(changed.sum()),
        error_interact=_mean(error),
        error_changed=_mean(error[changed]),
        error_interact_unchanged=_mean(error[~changed]),
        copy_baseline_interact=_mean(copy),
    )


# --- helpers --------------------------------------------------------------


def _movement_mask(action: torch.Tensor) -> torch.Tensor:
    moves = torch.as_tensor(MOVEMENT_ACTIONS, device=action.device)
    return torch.isin(action.reshape(-1), moves)


def _one_hot(action: torch.Tensor, like: torch.Tensor) -> torch.Tensor:
    action = action.reshape(-1)
    if action.shape[0] != like.shape[0]:
        raise ValueError(
            f"got {action.shape[0]} actions for {like.shape[0]} observations"
        )
    if bool(((action < 0) | (action >= N_ACTIONS)).any()):
        raise ValueError(f"action out of range [0, {N_ACTIONS})")
    return nn.functional.one_hot(action.long(), N_ACTIONS).to(like.dtype)
