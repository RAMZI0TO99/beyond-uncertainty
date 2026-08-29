"""Week 2 Friday: scripted policy, dataset collector, coverage metric.

"Done when: 5,000-transition dataset saved with a coverage report."
"""

from __future__ import annotations

import numpy as np
import pytest

from bu import constants as K
from bu.config import UnitSpec
from bu.env.collect import DEFAULT_EPISODE_LENGTH, TransitionDataset, collect
from bu.env.gridworld import N_ACTIONS, SHAPES
from bu.env.policy import ExploratoryPolicy, random_policy

# --- the acceptance criterion ---------------------------------------------


def test_five_thousand_transition_dataset_with_a_coverage_report(tmp_path):
    unit = UnitSpec(n_transitions=5000)
    data = collect(unit, seed=0)

    assert len(data) == 5000
    assert data.obs.shape == (5000, data.obs_dim)
    assert data.next_obs.shape == data.obs.shape
    assert data.coverage.n_transitions == 5000
    assert data.coverage.is_adequate()

    path = data.save(tmp_path / "d.npz")
    assert path.exists()
    back = TransitionDataset.load(path)
    assert len(back) == 5000
    assert back.unit == unit
    assert back.coverage.bumps == data.coverage.bumps
    assert np.array_equal(back.obs, data.obs)


def test_dataset_size_defaults_to_the_units_own_size():
    """A condition's dataset size comes from the statistical unit (D-017)."""
    assert len(collect(UnitSpec(n_transitions=250), seed=0)) == 250


@pytest.mark.parametrize("n", [1, 7, 100, 313])
def test_collection_returns_exactly_the_requested_count(n):
    """Including counts that do not divide the episode length."""
    assert len(collect(UnitSpec(), n_transitions=n, seed=0)) == n


def test_zero_transitions_is_refused():
    with pytest.raises(ValueError, match="must be positive"):
        collect(UnitSpec(), n_transitions=0)


# --- episode structure, which the acceptance test depends on --------------


def test_episode_and_step_indices_are_recorded():
    """Plan §7.3's mixed model needs random intercepts for episode within seed.

    That test creates the ground-truth label for H3, so the episode index is an
    input to the label -- and it cannot be reconstructed after collection.
    """
    data = collect(UnitSpec(), n_transitions=200, seed=0, episode_length=50)
    assert data.episode.min() == 0
    assert data.episode.max() == 3
    assert data.coverage.n_episodes == 4
    for ep in np.unique(data.episode):
        steps = data.step[data.episode == ep]
        assert steps.tolist() == sorted(steps.tolist())
        assert steps[0] == 0


def test_each_episode_gets_a_fresh_layout():
    """Otherwise the dataset spans one object arrangement, not many."""
    data = collect(UnitSpec(), n_transitions=300, seed=0, episode_length=50)
    firsts = {int(data.episode[i]): tuple(data.obs[i]) for i in range(len(data))[::-1]}
    assert len({v for v in firsts.values()}) > 1


def test_episodes_are_capped_at_the_episode_length():
    data = collect(UnitSpec(), n_transitions=120, seed=0, episode_length=25)
    counts = np.bincount(data.episode)
    assert counts.max() <= 25


# --- coverage: the evidence that makes DEV-001 defensible -----------------


def test_scripted_policy_beats_random_on_informative_transitions():
    """Plan §13.2 requires the substitution recorded with evidence, not asserted.

    The rule concerns passability, so only attempted moves into objects can
    teach it. A uniform random walk in an 8x8 grid barely produces them.
    """
    unit = UnitSpec(n_transitions=2000)
    scripted = collect(unit, seed=0)
    random_ = collect(unit, seed=0, policy=random_policy(unit, 0))

    s = sum(scripted.coverage.bumps.values())
    r = sum(random_.coverage.bumps.values())
    assert s > 3 * r, f"scripted {s} vs random {r}"


def test_both_causal_classes_are_bumped():
    """A dataset that only ever walked through passable objects shows half the
    rule, and a model trained on it fails for a reason unrelated to the design."""
    cov = collect(UnitSpec(n_transitions=2000), seed=0).coverage
    assert cov.bumps["pass"] >= 50
    assert cov.bumps["block"] >= 50


def test_coverage_grows_with_dataset_size():
    """Required by Plan §3.2.1: thin coverage must be repairable by more data
    from the same generating process, or it is not estimation failure."""
    counts = [
        sum(collect(UnitSpec(n_transitions=n), seed=0).coverage.bumps.values())
        for n in K.DATA_SIZES
    ]
    assert counts == sorted(counts), counts
    assert counts[-1] > 10 * counts[0]


def test_shape_action_coverage_is_complete_at_full_size():
    cov = collect(UnitSpec(n_transitions=5000), seed=0).coverage
    assert cov.shape_action_coverage(min_count=10) == 1.0
    for shape in SHAPES:
        for action in range(N_ACTIONS):
            assert cov.shape_action.get(f"{shape}|{action}", 0) > 0


@pytest.mark.parametrize("causal", ["shape", "colour", "position"])
def test_coverage_tracks_the_causal_attribute_not_just_shape(causal):
    """When the configuration rotates the causal attribute, the class that
    matters rotates with it."""
    cov = collect(
        UnitSpec(causal_attribute=causal, n_transitions=2000), seed=0
    ).coverage
    assert cov.bumps.get("pass", 0) >= 30
    assert cov.bumps.get("block", 0) >= 30


def test_a_thin_dataset_reports_itself_as_thin():
    """n=100 is Experiment 1's smallest condition and should not look adequate.

    Plan §3.2.1 counts "does not cover the relevant region" as estimation
    failure, so this is the manipulation working, not a defect.
    """
    assert not collect(UnitSpec(n_transitions=100), seed=0).coverage.is_adequate()


def test_summary_mentions_what_a_reader_needs():
    text = collect(UnitSpec(n_transitions=500), seed=0).coverage.summary()
    for token in ("transitions", "bumps", "adequate"):
        assert token in text


# --- the policy itself ----------------------------------------------------


def test_policy_is_deterministic_given_a_seed():
    unit = UnitSpec(n_transitions=300)
    a = collect(unit, seed=1)
    b = collect(unit, seed=1)
    assert np.array_equal(a.action, b.action)
    assert np.array_equal(a.obs, b.obs)


def test_different_seeds_give_different_data():
    unit = UnitSpec(n_transitions=300)
    assert not np.array_equal(collect(unit, seed=1).action, collect(unit, seed=2).action)


def test_policy_emits_every_action():
    data = collect(UnitSpec(n_transitions=2000), seed=0)
    assert set(np.unique(data.action)) == set(range(N_ACTIONS))


def test_policy_uses_interact_enough_to_be_learnable():
    """Interact has a visible effect; if the policy never takes it, the model
    cannot learn what it does and the action is dead weight in the input."""
    data = collect(UnitSpec(n_transitions=2000), seed=0)
    assert (data.action == 4).mean() > 0.05


def test_policy_holds_no_learned_state_across_units():
    """It is a fixed procedure, not something fitted per condition (Plan §13.2)."""
    p = ExploratoryPolicy(UnitSpec(), seed=0)
    assert not p.visits
