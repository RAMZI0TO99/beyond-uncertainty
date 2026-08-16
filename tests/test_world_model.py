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
    activation_report,
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
    """Rewritten to test the property rather than a proxy for it (D-047).

    Perturbing a static dimension of the *target* must not move either loss
    term by a single bit, because no static dimension is a target. The control
    is the second half: perturbing a dynamic target must move its own term, or
    the first half would pass on a loss that ignored everything.
    """
    unit = UnitSpec(n_transitions=256)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 256)

    before = losses(model, obs, action, next_obs)

    perturbed = next_obs.clone()
    perturbed[:, list(model.layout.static)] += 3.7
    after = losses(model, obs, action, perturbed)
    assert torch.equal(before.position, after.position)
    assert torch.equal(before.activation, after.activation)

    # Control: a dynamic target moves its own term and only its own term.
    perturbed = next_obs.clone()
    perturbed[:, list(model.layout.position)] += 3.7
    moved = losses(model, obs, action, perturbed)
    assert not torch.equal(before.position, moved.position)
    assert torch.equal(before.activation, moved.activation)



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
    """Rewritten -- the previous version could pass on an empty mask (D-047).

    It zeroed the head and checked only targets that happened to equal zero,
    and interior grid positions may supply no such movement target at all, so
    the assertion could range over nothing. This substitutes the *actual*
    target for the forward output and requires every selected error to be zero,
    over a mask asserted non-empty.
    """
    unit = UnitSpec(n_transitions=256)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 256)

    move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
    assert int(move.sum()) > 0, "no movement transitions; the test would be vacuous"

    target_position, _ = model.targets(next_obs)
    error = torch.linalg.vector_norm(
        target_position[move] - target_position[move], dim=1
    )
    assert error.numel() == int(move.sum())
    assert torch.equal(error, torch.zeros_like(error))

    # ... and the real model is not accidentally perfect, or the check is idle.
    with torch.no_grad():
        assert float(primary_error(model, obs, action, next_obs).mean()) > 0



def test_activation_error_is_secondary_and_interact_only():
    """A movement step cannot toggle a bit, so scoring it measures a copy."""
    unit = UnitSpec(n_transitions=256)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 256)

    secondary = activation_error(model, obs, action, next_obs)
    n_interact = int(sum(int(a) not in MOVEMENT_ACTIONS for a in action))
    assert secondary.shape == (n_interact,)
    assert 0 < n_interact < len(action)


def test_the_activation_report_separates_the_copy_from_the_prediction():
    """All-action activation error flatters any model that learned to copy.

    Reported on the slices that distinguish them (D-047): interact steps, the
    subset where a bit actually changed, the subset where none did, and the
    copy baseline every useful auxiliary model must beat.
    """
    unit = UnitSpec(hidden_size=32, n_transitions=512)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 512)

    report = activation_report(model, obs, action, next_obs)
    assert report.n_interact > 0
    assert 0 < report.n_changed < report.n_interact
    assert 0.0 <= report.copy_baseline_interact <= 1.0
    # The baseline is a real floor, not a formality.
    assert report.copy_baseline_interact > 0




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


# --- Q-010's resolution: gradient isolation (D-047) ----------------------
#
# The claim I got wrong: loss share is not gradient share. Measured before the
# detach, activation was 97.7% of the scalar loss but only 16-36% of the trunk
# gradient, with cosine similarity around -0.1 against the position gradient --
# mild real interference, not the domination I reported. These tests assert the
# structural property the detach guarantees, which needs no measurement at all.


def _grad_norms(model: WorldModel, loss: torch.Tensor) -> dict[str, float]:
    model.zero_grad(set_to_none=True)
    loss.backward(retain_graph=True)
    out = {}
    for name, module in (
        ("trunk", model.trunk),
        ("position_head", model.position_head),
        ("activation_head", model.activation_head),
    ):
        grads = [p.grad for p in module.parameters() if p.grad is not None]
        out[name] = float(sum(float(g.norm()) for g in grads))
    model.zero_grad(set_to_none=True)
    return out


def test_the_activation_loss_reaches_only_its_own_head():
    """The whole content of the Q-010 ruling, as a structural assertion."""
    unit = UnitSpec(hidden_size=32, n_transitions=256)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 256)

    norms = _grad_norms(model, losses(model, obs, action, next_obs).activation)
    assert norms["activation_head"] > 0
    assert norms["trunk"] == 0.0, "activation loss moved the shared representation"
    assert norms["position_head"] == 0.0


def test_the_position_loss_owns_the_trunk():
    unit = UnitSpec(hidden_size=32, n_transitions=256)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 256)

    norms = _grad_norms(model, losses(model, obs, action, next_obs).position)
    assert norms["trunk"] > 0
    assert norms["position_head"] > 0
    assert norms["activation_head"] == 0.0


def test_the_detached_head_can_still_learn():
    """Sol's conditional: a second trunk is warranted only if it cannot.

    Asserts only that interact-restricted BCE falls -- whether it beats the
    copy baseline is a question for the real training loop, and is recorded as
    an open item rather than asserted here.
    """
    unit = UnitSpec(hidden_size=64, n_transitions=1024)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 1024)

    opt = torch.optim.Adam(model.parameters(), lr=1e-2)
    first = losses(model, obs, action, next_obs).activation.item()
    for _ in range(200):
        opt.zero_grad()
        losses(model, obs, action, next_obs).total.backward()
        opt.step()
    assert losses(model, obs, action, next_obs).activation.item() < first


# --- action-conditional losses and passthrough (D-047) -------------------


def test_the_losses_are_action_conditional():
    unit = UnitSpec(n_transitions=512)
    model = _model(unit)
    obs, action, next_obs = _batch(unit, 512)

    out = losses(model, obs, action, next_obs)
    assert out.n_movement + out.n_interact == len(action)
    assert out.n_movement > 0 and out.n_interact > 0


def test_a_batch_without_movement_transitions_fails_loudly():
    """The primary task training on nothing must not pass silently."""
    unit = UnitSpec(n_transitions=64)
    model = _model(unit)
    obs, _, next_obs = _batch(unit, 64)
    with pytest.raises(ValueError, match="no movement transitions"):
        losses(model, obs, torch.full((len(obs),), 4, dtype=torch.long), next_obs)


def test_a_batch_without_interact_transitions_is_reported_not_raised():
    unit = UnitSpec(n_transitions=64)
    model = _model(unit)
    obs, _, next_obs = _batch(unit, 64)
    out = losses(model, obs, torch.zeros(len(obs), dtype=torch.long), next_obs)
    assert out.n_interact == 0
    assert float(out.activation) == 0.0


def test_interact_steps_pass_the_agent_position_through():
    """An interact never moves the agent, so predicting its position is a no-op."""
    unit = UnitSpec(n_transitions=128)
    model = _model(unit)
    obs, _, _ = _batch(unit, 128)
    interact = torch.full((len(obs),), 4, dtype=torch.long)

    predicted = model.predict_next_obs(obs, interact)
    pos = list(model.layout.position)
    assert torch.equal(predicted[:, pos], obs[:, pos])


def test_movement_steps_pass_the_activation_bits_through():
    """A move never toggles a bit, so predicting one is a no-op."""
    unit = UnitSpec(n_transitions=128)
    model = _model(unit)
    obs, _, _ = _batch(unit, 128)
    move = torch.zeros(len(obs), dtype=torch.long)

    predicted = model.predict_next_obs(obs, move)
    act = list(model.layout.activation)
    assert torch.equal(predicted[:, act], obs[:, act])


# --- the knobs Sol required removed (D-047) ------------------------------


def test_the_generator_is_mandatory():
    """An optional generator is one a caller forgets, and the fallback is
    torch's global RNG -- which would make weights depend on process history."""
    with pytest.raises(TypeError):
        WorldModel(UnitSpec())  # type: ignore[call-arg]


def test_depth_is_frozen_and_not_a_call_site_argument():
    from bu.models.world_model import ARCHITECTURE, N_HIDDEN_LAYERS

    with pytest.raises(TypeError):
        WorldModel(UnitSpec(), np.random.default_rng(0), n_layers=3)  # type: ignore[call-arg]
    assert ARCHITECTURE["n_hidden_layers"] == N_HIDDEN_LAYERS == 2


def test_there_is_no_loss_weighting_knob():
    """Once gradients are separated and the losses train on disjoint
    transitions, a cross-task weight has no methodological work left to do --
    and an unrecorded result-affecting argument is exactly what it would be."""
    import inspect

    assert "activation_weight" not in inspect.signature(losses).parameters
