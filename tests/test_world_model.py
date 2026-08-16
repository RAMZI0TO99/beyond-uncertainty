"""Week 3 Monday: the world model.

Acceptance criterion, from the schedule: *"forward-pass shape tests pass"*.
Those are here, and they are the least interesting tests in the file.

The ones that matter check the design decisions the shapes cannot: that the
model predicts only what can change (D-032), that static dimensions are copied
rather than learned, that the observation width follows the *condition* rather
than a constant -- which is what makes Experiment 2A's masked conditions work at
all -- and that initialisation comes from the named stream rather than torch's
global RNG (D-030).
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import UnitSpec
from bu.env.collect import collect
from bu.env.gridworld import N_ACTIONS
from bu.models.world_model import (
    MOVEMENT_ACTIONS,
    WorldModel,
    activation_error,
    dynamic_layout,
    losses,
    primary_error,
)
from bu.streams import stream

torch.manual_seed(0)  # only so an unseeded construction is deterministic here


def _model(unit: UnitSpec, member: int = 0) -> WorldModel:
    return WorldModel(unit, rng=stream(unit, "exp1", "init", 0, member=member))


def _batch(unit: UnitSpec, n: int = 64):
    ds = collect(unit, n_transitions=n, stage="pilot", seed=0)
    return (
        torch.tensor(ds.obs),
        torch.tensor(ds.action),
        torch.tensor(ds.next_obs),
    )


# --- the acceptance criterion ---------------------------------------------


@pytest.mark.parametrize("hidden", K.HIDDEN_SIZES)
def test_forward_pass_shapes(hidden: int):
    """Every capacity level Experiment 2B sweeps."""
    unit = UnitSpec(hidden_size=hidden, n_transitions=64)
    model = _model(unit)
    obs, action, _ = _batch(unit)

    position, logits = model(obs, action)
    assert position.shape == (len(action), 2)
    assert logits.shape == (len(action), unit.n_objects)


@pytest.mark.parametrize("withheld", [(), ("shape",), ("colour",), ("position",)])
def test_forward_pass_shapes_under_every_withholding(withheld):
    """Observation width follows the condition, not a constant.

    30 dimensions with everything visible, 22 with shape withheld. A model that
    assumed a width would be silently wrong for exactly the conditions
    Experiment 2A is about.
    """
    unit = UnitSpec(
        family="missing_feature" if withheld else "estimation",
        withheld_features=withheld,
        confound_rate=0.5 if withheld else 0.0,
        n_transitions=64,
    )
    model = _model(unit)
    obs, action, _ = _batch(unit)

    assert obs.shape[1] == model.encoder.size
    assert model.in_dim == model.encoder.size + N_ACTIONS
    position, logits = model(obs, action)
    assert position.shape == (len(action), 2)
    assert logits.shape == (len(action), unit.n_objects)


def test_a_wrong_width_observation_is_rejected_loudly():
    model = _model(UnitSpec(n_transitions=64))
    with pytest.raises(ValueError, match="expected obs of shape"):
        model(torch.zeros(4, model.encoder.size + 1), torch.zeros(4, dtype=torch.long))


def test_an_out_of_range_action_is_rejected():
    unit = UnitSpec(n_transitions=64)
    model = _model(unit)
    obs, _, _ = _batch(unit)
    with pytest.raises(ValueError, match="action out of range"):
        model(obs, torch.full((len(obs),), N_ACTIONS, dtype=torch.long))


# --- what the model predicts, and what it must not (D-032) ----------------


@pytest.mark.parametrize("withheld", [(), ("shape",), ("position",)])
def test_the_dynamic_layout_is_exactly_agent_position_and_activation(withheld):
    unit = UnitSpec(
        family="missing_feature" if withheld else "estimation",
        withheld_features=withheld,
        confound_rate=0.5 if withheld else 0.0,
    )
    model = _model(unit)
    layout = model.layout

    assert len(layout.position) == 2
    assert len(layout.activation) == unit.n_objects
    assert layout.n_outputs == 2 + unit.n_objects
    # ... and every other dimension is static, whatever the width happens to be.
    assert len(layout.static) == model.encoder.size - layout.n_outputs
    assert set(layout.dynamic).isdisjoint(layout.static)


def test_static_dimensions_are_copied_not_predicted():
    """The claim that makes "it predicts the next state" honest.

    An untrained model reproduces every static dimension exactly, because those
    dimensions are copied outside the loss rather than learned inside it.
    """
    unit = UnitSpec(n_transitions=128)
    model = _model(unit)
    obs, action, _ = _batch(unit, 128)

    predicted = model.predict_next_obs(obs, action)
    static = list(model.layout.static)
    assert torch.equal(predicted[:, static], obs[:, static])


def test_the_static_dimensions_really_are_static_in_the_data():
    """The measurement D-032 rests on, checked against collected data.

    If a "static" dimension ever changed within an episode, copying it would be
    a modelling error rather than a passthrough -- and the loss would be blind
    to it.
    """
    unit = UnitSpec(n_transitions=1000)
    model = _model(unit)
    obs, _, next_obs = _batch(unit, 1000)

    static = list(model.layout.static)
    assert torch.equal(obs[:, static], next_obs[:, static]), (
        "a dimension classified as static changed within a transition"
    )
    # Control: the dynamic ones do change, or the split is vacuous.
    dynamic = list(model.layout.dynamic)
    assert not torch.equal(obs[:, dynamic], next_obs[:, dynamic])


def test_the_loss_never_sees_a_static_dimension():
    """Stated over gradients, which is where it actually matters.

    Perturbing a static input dimension may change the prediction -- statics are
    legitimate *inputs*. What must not happen is a static dimension appearing as
    a *target*: the loss is computed only on the two heads, so no gradient can
    reward copying.
    """
    unit = UnitSpec(n_transitions=128)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 128)

    out = losses(model, obs, action, next_obs)
    n_targets = out.position.numel() + out.activation.numel()
    assert n_targets == 2  # two scalar terms, from two heads, and nothing else
    assert model.position_head.out_features + model.activation_head.out_features == (
        model.layout.n_outputs
    )


def test_the_two_loss_terms_stay_separate():
    unit = UnitSpec(n_transitions=128)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 128)

    out = losses(model, obs, action, next_obs)
    assert out.position.ndim == 0 and out.activation.ndim == 0
    assert torch.isclose(out.total, out.position + out.activation)
    # Reported apart, per D-032: the activation bit is orthogonal to
    # passability by construction, so it must not enter the headline number.
    assert not torch.isclose(out.position, out.activation)


def test_the_model_can_actually_learn(tmp_path):
    """A sanity floor, not a result: loss must fall on a tiny fit.

    Cheap deliberately -- this is Week 3 Monday, and no compute budget is
    spent here. It exists so a model that cannot train at all fails today
    rather than on Friday's sweep.
    """
    unit = UnitSpec(hidden_size=32, n_transitions=256)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 256)

    opt = torch.optim.Adam(model.parameters(), lr=1e-2)
    first = losses(model, obs, action, next_obs).total.item()
    for _ in range(100):
        opt.zero_grad()
        losses(model, obs, action, next_obs).total.backward()
        opt.step()
    assert losses(model, obs, action, next_obs).total.item() < first


# --- the primary error (DEV-007) ------------------------------------------


def test_the_primary_error_is_per_transition_and_movement_only():
    unit = UnitSpec(n_transitions=256)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 256)

    error = primary_error(model, obs, action, next_obs)
    n_moves = int(sum(int(a) in MOVEMENT_ACTIONS for a in action))
    assert error.shape == (n_moves,)
    assert n_moves < len(action), "the batch should contain some interact steps"


def test_interact_transitions_are_excluded_from_the_primary_error():
    """An interact step cannot be refused, so it carries no evidence about the
    passability rule the thesis manipulates."""
    unit = UnitSpec(n_transitions=64)
    model = _model(unit)
    obs, _, next_obs = _batch(unit, 64)
    interact = torch.full((len(obs),), 4, dtype=torch.long)

    assert primary_error(model, obs, interact, next_obs).numel() == 0


def test_an_empty_movement_batch_returns_empty_not_nan():
    """A mean over nothing is how a silently empty failure set enters a result."""
    unit = UnitSpec(n_transitions=64)
    model = _model(unit)
    obs, _, next_obs = _batch(unit, 64)
    error = primary_error(model, obs, torch.full((len(obs),), 4, dtype=torch.long), next_obs)
    assert error.numel() == 0
    assert not torch.isnan(error).any()


def test_a_perfect_position_prediction_scores_zero():
    unit = UnitSpec(n_transitions=64)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 64)

    target_position, _ = model.targets(next_obs)
    with torch.no_grad():  # force the head to emit the truth
        model.position_head.weight.zero_()
        model.position_head.bias.zero_()
    error = primary_error(model, obs, action, next_obs)
    # Not zero in general -- but zero exactly where the truth is the zero vector.
    mask = torch.linalg.vector_norm(target_position, dim=1) == 0
    moves = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
    assert torch.allclose(error[mask[moves]], torch.zeros(int(mask[moves].sum())))


def test_activation_error_is_secondary_and_separate():
    unit = UnitSpec(n_transitions=128)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 128)

    secondary = activation_error(model, obs, action, next_obs)
    assert secondary.shape == (len(action),)  # all actions, unlike the primary
    assert secondary.shape != primary_error(model, obs, action, next_obs).shape


# --- initialisation comes from the named stream (D-030) -------------------


def test_initialisation_is_reproducible_from_the_stream():
    unit = UnitSpec(n_transitions=64)
    a = WorldModel(unit, rng=stream(unit, "exp1", "init", 0, member=0))
    b = WorldModel(unit, rng=stream(unit, "exp1", "init", 0, member=0))
    for pa, pb in zip(a.parameters(), b.parameters()):
        assert torch.equal(pa, pb)


def test_ensemble_members_initialise_differently():
    """H1 and H2 are claims about disagreement, so members must differ."""
    unit = UnitSpec(n_transitions=64)
    a = WorldModel(unit, rng=stream(unit, "exp1", "init", 0, member=0))
    b = WorldModel(unit, rng=stream(unit, "exp1", "init", 0, member=1))
    assert any(not torch.equal(pa, pb) for pa, pb in zip(a.parameters(), b.parameters()))


def test_initialisation_does_not_depend_on_torch_global_state():
    """Construction order within a process must not reach the weights."""
    unit = UnitSpec(n_transitions=64)
    torch.manual_seed(1234)
    a = WorldModel(unit, rng=stream(unit, "exp1", "init", 0, member=0))
    torch.manual_seed(9999)
    WorldModel(unit, rng=np.random.default_rng(7))  # perturb any shared state
    b = WorldModel(unit, rng=stream(unit, "exp1", "init", 0, member=0))
    for pa, pb in zip(a.parameters(), b.parameters()):
        assert torch.equal(pa, pb)


def test_capacity_comes_from_the_unit_not_the_call_site():
    """hidden_size is a registered identity field swept by Experiment 2B.

    A run record stating one capacity while another trained is the class of
    defect D-017 exists to prevent.
    """
    for hidden in K.HIDDEN_SIZES:
        model = _model(UnitSpec(hidden_size=hidden))
        assert model.position_head.in_features == hidden


def test_the_layout_rejects_an_encoder_without_an_agent():
    class _Fake:
        size = 4
        blocks = ()

    with pytest.raises(ValueError, match="no agent_position block"):
        dynamic_layout(_Fake())  # type: ignore[arg-type]


# --- Q-010: the auxiliary task dominates the optimised loss ---------------


def test_the_activation_term_dominates_the_total_at_weight_one():
    """Pins the measurement behind Q-010 so it cannot be forgotten.

    D-032 fixed the dilution problem in the *metric*: full-state MSE hid the
    passability rule behind 28 copyable dimensions. This is the same problem
    reappearing in the *loss*. Binary cross-entropy on activation and mean
    squared error on grid-normalised positions have different natural scales,
    and the activation task is ~97% solvable by copying the current bit, so its
    irreducible floor is large while the position term is small.

    The consequence is not cosmetic: under Experiment 1's small-data conditions
    the optimiser would be spending its gradient budget on a quantity the
    thesis makes no claim about, which shifts where estimation failure appears
    -- the same class of confound as the object-order leak (B1).

    This test asserts the imbalance *exists*, not that it is acceptable. It
    should be revisited when Q-010 is answered.
    """
    unit = UnitSpec(hidden_size=64, n_transitions=512)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 512)

    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for _ in range(200):
        opt.zero_grad()
        losses(model, obs, action, next_obs).total.backward()
        opt.step()

    out = losses(model, obs, action, next_obs)
    assert out.activation_share > 0.8, (
        f"activation share is {out.activation_share:.1%}; if this has fallen, "
        "Q-010's premise has changed and the question needs re-examining"
    )


def test_the_weight_changes_the_optimised_total_but_not_the_reported_parts():
    """A weight must never be able to flatter a reported number."""
    unit = UnitSpec(hidden_size=32, n_transitions=128)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 128)

    a = losses(model, obs, action, next_obs, activation_weight=1.0)
    b = losses(model, obs, action, next_obs, activation_weight=0.01)

    assert torch.equal(a.position, b.position)
    assert torch.equal(a.activation, b.activation)   # reported values identical
    assert not torch.isclose(a.total, b.total)       # optimised totals differ
    assert b.activation_share < a.activation_share
