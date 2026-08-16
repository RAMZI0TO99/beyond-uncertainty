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
from bu.env.collect import collect_pools
from bu.models.ensemble import Ensemble, bootstrap_episodes, train_ensemble
from bu.models.train import episode_indices
from bu.streams import stream

torch.set_num_threads(2)

CONFIG = TrainConfig(max_epochs=25, patience=6)


def _unit(n: int = 2000, hidden: int = 32) -> UnitSpec:
    return UnitSpec(hidden_size=hidden, n_transitions=n)


def _pools(unit):
    return collect_pools(unit, stage="exp1", seed=1000)


def _boot(unit, pools, member=0, **kw):
    return bootstrap_episodes(
        pools.train, stream(unit, "exp1", "bootstrap", 1000, member=member), **kw
    )


# --- the acceptance criterion ---------------------------------------------


def test_five_members_train_with_per_member_validation_error(tmp_path):
    from bu.config import Config
    from bu.metrics import RunLogger, load_runs

    unit = _unit()
    pools = _pools(unit)

    cfg = Config(unit=unit, seed=1000, stage="exp1")
    with RunLogger.start(cfg, root=tmp_path) as logger:
        ensemble = train_ensemble(unit, pools, CONFIG, stage="exp1", seed=1000, logger=logger)

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
    ensemble = train_ensemble(unit, _pools(unit), CONFIG, stage="exp1", seed=1000)
    errors = np.array(ensemble.val_position_errors)
    assert len(set(errors.tolist())) == len(errors), "members produced identical errors"
    assert errors.std(ddof=1) > 0


# --- what is shared, and what is not (D-052) ------------------------------


def test_only_the_training_pool_is_resampled():
    """Validation and evaluation are fixed, so per-member errors are comparable
    and the evaluation set is identical across members and dataset sizes."""
    unit = _unit()
    pools = _pools(unit)
    for k in range(5):
        index = _boot(unit, pools, member=k)
        assert index.max() < len(pools.train)
    # The pools themselves never move.
    again = _pools(unit)
    assert np.array_equal(pools.validation.obs, again.validation.obs)
    assert np.array_equal(pools.evaluation.obs, again.evaluation.obs)


def test_members_draw_roughly_the_classic_bootstrap_share_of_episodes():
    """~63% unique under sampling with replacement -- the property that makes
    this a bootstrap rather than a shuffle."""
    unit = _unit(5000)
    pools = _pools(unit)
    total = len(episode_indices(pools.train))
    shares = [
        len(np.unique(pools.train.episode[_boot(unit, pools, member=k)])) / total
        for k in range(5)
    ]
    assert 0.5 < float(np.mean(shares)) < 0.75


def test_the_smallest_condition_has_real_resampling_diversity():
    """At the old episode length N=100 had one training episode, so an episode
    bootstrap over it had exactly one possible sample (D-052)."""
    unit = _unit(100)
    pools = _pools(unit)
    uniques = {
        len(np.unique(pools.train.episode[_boot(unit, pools, member=k)]))
        for k in range(5)
    }
    assert len(uniques) > 1, "every member drew the same number of episodes"
    assert max(uniques) >= 4


# --- members differ, and for the recorded reasons -------------------------


def test_members_hold_different_weights_and_make_different_predictions():
    unit = _unit()
    pools = _pools(unit)
    ensemble = train_ensemble(unit, pools, CONFIG, stage="exp1", seed=1000)

    a, b = ensemble.members[0], ensemble.members[1]
    assert any(not torch.equal(pa, pb) for pa, pb in zip(a.parameters(), b.parameters()))

    obs = torch.tensor(pools.evaluation.obs[:128])
    action = torch.tensor(pools.evaluation.action[:128])
    predictions = ensemble.member_predictions(obs, action)
    assert predictions.shape == (5, 128, 2)
    assert not torch.equal(predictions[0], predictions[1])


def test_each_source_of_diversity_is_its_own_stream():
    """Bootstrap, init and batch are separate, so diversity can be attributed
    and changing one cannot silently shift another."""
    unit = _unit()
    pools = _pools(unit)
    assert not np.array_equal(_boot(unit, pools, 0), _boot(unit, pools, 1))

    init_a = stream(unit, "exp1", "init", 1000, member=0).random(4)
    init_b = stream(unit, "exp1", "init", 1000, member=1).random(4)
    assert not np.array_equal(init_a, init_b)
    assert not np.array_equal(
        stream(unit, "exp1", "bootstrap", 1000, member=0).random(4), init_a
    )


def test_an_ensemble_is_reproducible_from_its_streams():
    unit = _unit()
    pools = _pools(unit)
    a = train_ensemble(unit, pools, CONFIG, stage="exp1", seed=1000)
    b = train_ensemble(unit, pools, CONFIG, stage="exp1", seed=1000)
    assert a.val_position_errors == b.val_position_errors


def test_a_member_does_not_depend_on_the_order_members_were_trained_in():
    """A member must be refittable alone and reproduce exactly."""
    unit = _unit()
    pools = _pools(unit)
    full = train_ensemble(unit, pools, CONFIG, stage="exp1", seed=1000)
    solo = train_ensemble(
        unit, pools,
        TrainConfig(max_epochs=CONFIG.max_epochs, patience=CONFIG.patience, ensemble_size=1),
        stage="exp1", seed=1000,
    )
    assert solo.val_position_errors[0] == pytest.approx(full.val_position_errors[0])


# --- resampling granularity: episode is primary (Q-011 -> D-053) ----------


def test_episode_bootstrap_is_the_primary_method():
    unit = _unit()
    ensemble = train_ensemble(unit, _pools(unit), CONFIG, stage="exp1", seed=1000)
    assert ensemble.granularity == "episode"


def test_transition_bootstrap_retains_nearly_every_episode():
    """Why it is a secondary sensitivity and never a verdict: it treats
    correlated transitions as exchangeable, so it suppresses the data-resampling
    component of disagreement (D-053)."""
    unit = _unit()
    pools = _pools(unit)
    total = len(episode_indices(pools.train))

    by_transition = _boot(unit, pools, granularity="transition")
    by_episode = _boot(unit, pools, granularity="episode")
    assert len(np.unique(pools.train.episode[by_transition])) > 0.9 * total
    assert len(np.unique(pools.train.episode[by_episode])) < 0.8 * total


def test_an_initialisation_only_ensemble_uses_the_whole_pool():
    """The cleaner sensitivity: it isolates weight-init diversity from data
    resampling rather than blurring the two."""
    unit = _unit()
    pools = _pools(unit)
    index = _boot(unit, pools, granularity="none")
    assert np.array_equal(index, np.arange(len(pools.train)))


def test_an_unknown_granularity_is_rejected():
    unit = _unit()
    pools = _pools(unit)
    with pytest.raises(ValueError, match="unknown bootstrap granularity"):
        _boot(unit, pools, granularity="weekly")


def test_the_bootstrap_ratio_is_respected():
    unit = _unit(5000)
    pools = _pools(unit)
    total = len(episode_indices(pools.train))
    half = _boot(unit, pools, ratio=0.5)
    assert len(np.unique(pools.train.episode[half])) < total
    with pytest.raises(ValueError, match="ratio must be positive"):
        _boot(unit, pools, ratio=0.0)
