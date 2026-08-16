"""Week 3 Wednesday: the bootstrap ensemble.

Acceptance criterion: *"five members train, per-member validation error
logged"*.

The ensemble is the measurement instrument rather than a modelling convenience:
H1 and H2 are both claims about **mean pairwise disagreement between members**,
so anything that changes how members differ changes the dependent variable. The
tests below are mostly about that -- that members really do differ, that they
differ for the recorded reasons, and that what they are *scored* on is identical
across members so their errors can be compared at all.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bu.config import TrainConfig, UnitSpec
from bu.env.collect import collect
from bu.models.ensemble import Ensemble, bootstrap_split, train_ensemble
from bu.models.train import split_by_episode
from bu.streams import stream

torch.set_num_threads(2)

CONFIG = TrainConfig(max_epochs=25, patience=6)


def _unit(n: int = 2000, hidden: int = 32) -> UnitSpec:
    return UnitSpec(hidden_size=hidden, n_transitions=n)


# --- the acceptance criterion ---------------------------------------------


def test_five_members_train_with_per_member_validation_error(tmp_path):
    from bu.config import Config
    from bu.metrics import RunLogger, load_runs

    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)

    cfg = Config(unit=unit, seed=0, stage="exp1")
    with RunLogger.start(cfg, root=tmp_path) as logger:
        ensemble = train_ensemble(unit, dataset, CONFIG, stage="exp1", seed=0, logger=logger)

    assert len(ensemble) == CONFIG.ensemble_size == 5
    assert len(ensemble.val_position_errors) == 5
    assert all(np.isfinite(e) for e in ensemble.val_position_errors)

    frame = load_runs(tmp_path)
    assert len(frame) == 5, "one record per member, not one aggregate"
    assert sorted(frame["member"]) == [0, 1, 2, 3, 4]
    assert "val_position" in frame.columns


def test_per_member_errors_are_logged_rather_than_averaged():
    """The spread across members is the quantity H1 and H2 are about.

    A mean would discard exactly the thing being measured.
    """
    unit = _unit()
    ensemble = train_ensemble(unit, collect(unit, stage="exp1", seed=0), CONFIG,
                              stage="exp1", seed=0)
    errors = np.array(ensemble.val_position_errors)
    assert len(set(errors.tolist())) == len(errors), "members produced identical errors"
    assert errors.std(ddof=1) > 0


# --- what is shared, and what is not --------------------------------------


def test_every_member_is_scored_on_the_same_held_out_episodes():
    """Per-member errors that were computed on different data would not be
    comparable -- and Friday compares them."""
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    base = split_by_episode(dataset, CONFIG.val_fraction)

    for k in range(5):
        member = bootstrap_split(
            dataset, base, stream(unit, "exp1", "bootstrap", 0, member=k)
        )
        assert np.array_equal(member.val, base.val)
        assert member.val_episodes == base.val_episodes


def test_the_bootstrap_never_leaks_a_validation_episode_into_training():
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    base = split_by_episode(dataset, CONFIG.val_fraction)

    for k in range(5):
        member = bootstrap_split(
            dataset, base, stream(unit, "exp1", "bootstrap", 0, member=k)
        )
        drawn = set(dataset.episode[member.train].tolist())
        assert drawn.isdisjoint(base.val_episodes)


def test_members_draw_roughly_the_classic_bootstrap_share_of_episodes():
    """~63% unique under sampling with replacement -- the property that makes
    this a bootstrap rather than a shuffle."""
    unit = _unit(5000)
    dataset = collect(unit, stage="exp1", seed=0)
    base = split_by_episode(dataset, CONFIG.val_fraction)

    shares = []
    for k in range(5):
        member = bootstrap_split(
            dataset, base, stream(unit, "exp1", "bootstrap", 0, member=k)
        )
        shares.append(len(set(member.train_episodes)) / len(base.train_episodes))
    assert 0.5 < float(np.mean(shares)) < 0.75


# --- members differ, and for the recorded reasons -------------------------


def test_members_hold_different_weights_and_make_different_predictions():
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    ensemble = train_ensemble(unit, dataset, CONFIG, stage="exp1", seed=0)

    a, b = ensemble.members[0], ensemble.members[1]
    assert any(not torch.equal(pa, pb) for pa, pb in zip(a.parameters(), b.parameters()))

    obs = torch.tensor(dataset.obs[:128])
    action = torch.tensor(dataset.action[:128])
    predictions = ensemble.member_predictions(obs, action)
    assert predictions.shape == (5, 128, 2)
    assert not torch.equal(predictions[0], predictions[1])


def test_each_source_of_diversity_is_its_own_stream():
    """Bootstrap, init and batch are separate, so diversity can be attributed
    and changing one cannot silently shift another."""
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    base = split_by_episode(dataset, CONFIG.val_fraction)

    first = bootstrap_split(dataset, base, stream(unit, "exp1", "bootstrap", 0, member=0))
    second = bootstrap_split(dataset, base, stream(unit, "exp1", "bootstrap", 0, member=1))
    assert first.train_episodes != second.train_episodes

    init_a = stream(unit, "exp1", "init", 0, member=0).random(4)
    init_b = stream(unit, "exp1", "init", 0, member=1).random(4)
    assert not np.array_equal(init_a, init_b)
    # ... and the bootstrap stream is not the init stream wearing a hat.
    assert not np.array_equal(
        stream(unit, "exp1", "bootstrap", 0, member=0).random(4), init_a
    )


def test_an_ensemble_is_reproducible_from_its_streams():
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    a = train_ensemble(unit, dataset, CONFIG, stage="exp1", seed=0)
    b = train_ensemble(unit, dataset, CONFIG, stage="exp1", seed=0)
    assert a.val_position_errors == b.val_position_errors


def test_a_member_does_not_depend_on_the_order_members_were_trained_in():
    """A member must be refittable alone and reproduce exactly.

    Without this, re-running one failed member of a batch would silently
    produce a different model from the one the run record describes.
    """
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    full = train_ensemble(unit, dataset, CONFIG, stage="exp1", seed=0)

    solo = train_ensemble(
        unit, dataset,
        TrainConfig(max_epochs=CONFIG.max_epochs, patience=CONFIG.patience, ensemble_size=1),
        stage="exp1", seed=0,
    )
    assert solo.val_position_errors[0] == pytest.approx(full.val_position_errors[0])


# --- resampling granularity (Q-011) ---------------------------------------


def test_the_two_granularities_produce_different_training_sets():
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    base = split_by_episode(dataset, CONFIG.val_fraction)
    rng = stream(unit, "exp1", "bootstrap", 0, member=0)

    by_episode = bootstrap_split(dataset, base, rng, granularity="episode")
    by_transition = bootstrap_split(
        dataset, base, stream(unit, "exp1", "bootstrap", 0, member=0),
        granularity="transition",
    )
    assert not np.array_equal(by_episode.train, by_transition.train)

    # A transition bootstrap keeps essentially every episode represented, which
    # is the whole reason it produces less member diversity on correlated data.
    episodes_seen = set(dataset.episode[by_transition.train].tolist())
    assert len(episodes_seen) > 0.9 * len(base.train_episodes)
    assert len(set(by_episode.train_episodes)) < 0.8 * len(base.train_episodes)


def test_the_default_granularity_is_the_block_bootstrap():
    unit = _unit()
    ensemble = train_ensemble(unit, collect(unit, stage="exp1", seed=0), CONFIG,
                              stage="exp1", seed=0)
    assert ensemble.granularity == "episode"


def test_an_unknown_granularity_is_rejected():
    unit = _unit()
    dataset = collect(unit, stage="exp1", seed=0)
    base = split_by_episode(dataset, CONFIG.val_fraction)
    with pytest.raises(ValueError, match="unknown bootstrap granularity"):
        bootstrap_split(dataset, base, np.random.default_rng(0), granularity="weekly")  # type: ignore[arg-type]


def test_the_bootstrap_ratio_is_respected():
    unit = _unit(5000)
    dataset = collect(unit, stage="exp1", seed=0)
    base = split_by_episode(dataset, CONFIG.val_fraction)
    rng = stream(unit, "exp1", "bootstrap", 0, member=0)

    half = bootstrap_split(dataset, base, rng, granularity="episode", ratio=0.5)
    assert len(half.train_episodes) == pytest.approx(len(base.train_episodes) / 2, abs=1)

    with pytest.raises(ValueError, match="ratio must be positive"):
        bootstrap_split(dataset, base, rng, ratio=0.0)
