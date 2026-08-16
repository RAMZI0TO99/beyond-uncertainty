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
from ..env.gridworld import N_ACTIONS

#: Actions that can be refused by the passability rule. ``interact`` cannot, so
#: it carries no evidence about the mechanism under study (DEV-007).
MOVEMENT_ACTIONS: tuple[int, ...] = (0, 1, 2, 3)


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

    def __init__(
        self,
        unit: UnitSpec,
        *,
        rng: np.random.Generator | None = None,
        n_layers: int = 2,
    ) -> None:
        super().__init__()
        if n_layers < 1:
            raise ValueError(f"n_layers must be >= 1, got {n_layers}")

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
        for _ in range(n_layers):
            trunk += [nn.Linear(width, hidden), nn.ReLU()]
            width = hidden
        self.trunk = nn.Sequential(*trunk)

        #: Continuous, grid-normalised. MSE.
        self.position_head = nn.Linear(hidden, len(self.layout.position))
        #: Bernoulli logits, one per object. Cross-entropy (binary).
        self.activation_head = nn.Linear(hidden, len(self.layout.activation))

        if rng is not None:
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
        return self.position_head(h), self.activation_head(h)

    def predict_next_obs(self, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        """A complete next observation: predicted dynamics, copied statics.

        The model predicts the next *state* in the sense Plan §10.2 asks for,
        without ever being rewarded for reproducing dimensions that cannot
        change. The copy happens here and only here, outside the loss.
        """
        position, logits = self(obs, action)
        out = obs.clone()
        out[:, list(self.layout.position)] = position
        out[:, list(self.layout.activation)] = torch.sigmoid(logits)
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

    ``position`` and ``activation`` are always the **unweighted** values, so
    what is reported cannot be changed by how the optimiser was told to trade
    them off. Only :attr:`total` applies the weight.
    """

    position: torch.Tensor
    activation: torch.Tensor
    activation_weight: float = 1.0

    @property
    def total(self) -> torch.Tensor:
        """What the optimiser minimises."""
        return self.position + self.activation_weight * self.activation

    @property
    def activation_share(self) -> float:
        """Fraction of the optimised total coming from the auxiliary task.

        Q-010 exists because this is 97.7% at weight 1.0.
        """
        with torch.no_grad():
            return float(self.activation_weight * self.activation / self.total)


#: Weight on the activation term in the optimised total. **Provisional at 1.0,
#: and the subject of Q-010** -- measured after 400 epochs at hidden=64,
#: n=2000, the activation term is **97.7%** of the total loss (BCE 0.0936
#: against position MSE 0.0022), so the optimiser spends almost all of its
#: gradient on the auxiliary task while the passability rule -- the entire
#: scientific claim -- gets 2.3%.
#:
#: Left at 1.0 deliberately rather than tuned to a number of my choosing: no
#: model has trained for a result, so nothing is lost by waiting, and picking a
#: weight is a methodological decision about what the world model is optimised
#: for. See Q-010.
DEFAULT_ACTIVATION_WEIGHT = 1.0


def losses(
    model: WorldModel,
    obs: torch.Tensor,
    action: torch.Tensor,
    next_obs: torch.Tensor,
    *,
    activation_weight: float = DEFAULT_ACTIVATION_WEIGHT,
) -> Losses:
    """MSE on position, binary cross-entropy on activation.

    Summed for optimisation, returned separately for reporting. They are never
    averaged into one number in a result: the activation bit is orthogonal to
    passability by construction (D-017), so folding it into the headline error
    would put a quantity the thesis makes no claim about inside the quantity it
    does.

    ``activation_weight`` scales the auxiliary term in the **optimised** total
    only; the reported components are always unweighted, so a weight can never
    flatter a reported number. See :data:`DEFAULT_ACTIVATION_WEIGHT` and Q-010
    for why it is not yet set to anything else.
    """
    position, logits = model(obs, action)
    target_position, target_activation = model.targets(next_obs)
    return Losses(
        position=nn.functional.mse_loss(position, target_position),
        activation=nn.functional.binary_cross_entropy_with_logits(
            logits, target_activation
        ),
        activation_weight=float(activation_weight),
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
    """Secondary metric: per-transition activation error, over all actions.

    Reported beside the primary error, never inside it (D-032).
    """
    _, logits = model(obs, action)
    _, target = model.targets(next_obs)
    return (torch.sigmoid(logits) - target).abs().mean(dim=1)


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
