"""The three-pool invariants, and what may never touch what (D-052, D-054).

Sol's point that these needed asserting directly: distinct stream names make
overlap *unlikely*, but the scientific property is non-overlap, and a test
should assert the property rather than the mechanism that currently delivers it.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Arm, TrainConfig, UnitSpec
from bu.env.collect import collect, collect_pools
from bu.env.policy import ExploratoryPolicy
from bu.models.train import episode_indices, train
from bu.models.world_model import WorldModel
from bu.streams import stream

torch.set_num_threads(2)
SEED = K.CONFIRMATORY_SEED_BASE


def _pools(n: int, seed: int = SEED):
    return collect_pools(UnitSpec(n_transitions=n), stage="exp1", seed=seed)


def _rows(dataset) -> set[bytes]:
    """A transition's full identity, not just its observation."""
    return {
        (o.tobytes(), int(a), no.tobytes())
        for o, a, no in zip(dataset.obs, dataset.action, dataset.next_obs)
    }


# --- non-overlap, asserted as the property ---------------------------------


def test_the_pools_are_independently_generated_and_state_their_provenance():
    """The invariant, stated as what it actually is (D-055).

    An earlier version of this test allowed 35% overlap among distinct
    ``(obs, action, next_obs)`` values and claimed in its comment to compare
    episodes. It did neither. In a discrete world identical transition *values*
    recur legitimately across independent draws, so value overlap is not the
    property. The property is that the pools are independently generated --
    different stream keys -- and that each dataset records which pool it came
    from, so provenance can be checked rather than inferred.
    """
    from bu.streams import POOL_PURPOSES, stream_key

    pools = _pools(1000)
    assert (pools.train.pool, pools.validation.pool, pools.evaluation.pool) == (
        "train", "validation", "evaluation",
    )

    unit = UnitSpec(n_transitions=1000)
    keys = {
        str(stream_key(unit, "exp1", purpose))
        for pair in POOL_PURPOSES.values()
        for purpose in pair
    }
    assert len(keys) == 6, "two pools share a stream key"


def test_the_pools_come_from_genuinely_different_draws():
    pools = _pools(1000)
    assert not np.array_equal(
        pools.validation.obs[:400], pools.evaluation.obs[:400]
    )
    assert not np.array_equal(pools.train.obs[:400], pools.validation.obs[:400])


def test_the_three_pools_use_three_distinct_stream_pairs():
    from bu.streams import POOL_PURPOSES

    purposes = [p for pair in POOL_PURPOSES.values() for p in pair]
    assert len(set(purposes)) == len(purposes) == 6


# --- fixed across everything that must not move it -------------------------


def test_validation_and_evaluation_are_identical_across_dataset_sizes():
    """Every array, not only ``obs`` -- a byte-identity claim should be checked
    over everything that varies (D-055)."""
    reference = _pools(100)
    for n in (250, 500, 1000, 2500, 5000):
        pools = _pools(n)
        for name in ("obs", "action", "next_obs", "episode", "step"):
            for which in ("validation", "evaluation"):
                assert np.array_equal(
                    getattr(getattr(pools, which), name),
                    getattr(getattr(reference, which), name),
                ), f"{which}.{name} moved at N={n}"


@pytest.mark.parametrize(
    "arm, unit, stage",
    [
        ("data_repair", UnitSpec(family="estimation", n_transitions=250), "exp1"),
        ("capacity_repair",
         UnitSpec(family="capacity", hidden_size=16, n_transitions=5000), "exp2b"),
        ("feature_repair",
         UnitSpec(family="missing_feature", withheld_features=("shape",),
                  confound_rate=0.5, n_transitions=5000), "exp2a"),
    ],
)
def test_every_repair_arm_keeps_its_baselines_failure_set(arm, unit, stage):
    """P§7.2 evaluates a repair on the *same recorded failure set* as its baseline.

    This previously held for data and capacity repair by accident -- Experiment
    1 excludes ``n_transitions`` from its comparison group and 2B excludes
    ``hidden_size``, so resolving those arms left the stream key untouched.
    Feature repair changes ``withheld_features``, which 2A does *not* exclude,
    so it drew a different environment, validation and evaluation pool from its
    own baseline. Two arms passing was not evidence about the third (D-055).

    Compared on the **latent** trajectory, because restoring a feature changes
    the observation width and byte equality of encoded observations is
    therefore the wrong test.
    """
    base = collect_pools(unit, stage=stage, seed=SEED)
    repaired = collect_pools(unit, stage=stage, seed=SEED, arm=arm)

    for which in ("validation", "evaluation"):
        b, r = getattr(base, which), getattr(repaired, which)
        assert np.array_equal(b.action, r.action), f"{which} actions diverged"
        assert np.array_equal(b.episode, r.episode)
        assert np.array_equal(b.obs[:, :2], r.obs[:, :2]), (
            f"{which} agent trajectory diverged"
        )

    expected = K.DATA_REPAIR_MULTIPLIER if arm == "data_repair" else 1
    assert len(repaired.train) == len(base.train) * expected


def test_the_registered_n_counts_training_transitions_only():
    for n in (100, 250, 1000, 5000):
        assert len(_pools(n).train) == n


# --- evaluation stays outside model selection ------------------------------


def test_the_evaluation_pool_cannot_be_used_for_model_selection():
    """The previous version of this test was false (D-055).

    It asserted that ``train`` has no parameter *named* evaluation -- but the
    pools share a type, so ``train(model, pools.train, pools.evaluation, ...)``
    simply worked, and every reported number would have been selected on.
    Provenance is checked now, so the call raises.
    """
    unit = UnitSpec(hidden_size=32, n_transitions=500)
    pools = _pools(500)
    model = WorldModel(unit, stream(unit, "exp1", "init", SEED))
    cfg = TrainConfig(max_epochs=1)

    with pytest.raises(ValueError, match="evaluation"):
        train(model, pools.train, pools.evaluation, cfg,
              rng=stream(unit, "exp1", "batch", SEED))

    with pytest.raises(ValueError, match="only the training pool"):
        train(model, pools.validation, pools.validation, cfg,
              rng=stream(unit, "exp1", "batch", SEED))


def test_the_loss_curve_is_computed_on_validation_not_evaluation():
    unit = UnitSpec(hidden_size=32, n_transitions=1000)
    pools = _pools(1000)
    result = train(
        WorldModel(unit, stream(unit, "exp1", "init", SEED)),
        pools.train, pools.validation, TrainConfig(max_epochs=4),
        rng=stream(unit, "exp1", "batch", SEED),
    )
    assert result.n_validation == len(pools.validation)
    assert result.n_validation != len(pools.evaluation)


# --- frozen experimental procedure (D-054) ---------------------------------


def test_episode_length_is_frozen_for_confirmatory_seeds():
    with pytest.raises(ValueError, match="frozen value"):
        collect(UnitSpec(n_transitions=100), stage="exp1", seed=SEED, episode_length=5)


@pytest.mark.parametrize("call", ["n_transitions", "policy", "granularity"])
def test_confirmatory_runs_cannot_deviate_from_the_frozen_procedure(call):
    """Development overrides may exist; a confirmatory run may not use them.

    ``granularity`` matters most: it is not part of Config, so a non-primary
    confirmatory fit would occupy the *same recorded identity* as the primary
    one (D-055).
    """
    unit = UnitSpec(hidden_size=32, n_transitions=500)
    if call == "n_transitions":
        with pytest.raises(ValueError, match="frozen size"):
            collect_pools(unit, stage="exp1", seed=SEED, n_transitions=99)
    elif call == "policy":
        with pytest.raises(ValueError, match="custom policy"):
            collect(unit, stage="exp1", seed=SEED, policy=object())
    else:
        from bu.models.ensemble import train_ensemble

        pools = collect_pools(unit, stage="exp1", seed=SEED)  # matching, so the
        # D-057 guard passes and the granularity guard is what fires
        with pytest.raises(ValueError, match="fixed primary method"):
            train_ensemble(
                unit, pools, TrainConfig(max_epochs=1, ensemble_size=1),
                stage="exp1", seed=SEED, granularity="transition",
            )


def test_a_legacy_dataset_is_not_stamped_with_todays_constants(tmp_path):
    """Loading an older record used to assign the *current* EPISODE_LENGTH, so a
    dataset generated at 50 would be silently relabelled 10 -- the opposite of
    a provenance guarantee (D-055)."""
    import json

    from bu.env.collect import TransitionDataset

    path = _pools(250).evaluation.save(tmp_path / "legacy.npz")
    data = dict(np.load(path, allow_pickle=False))
    meta = json.loads(str(data["meta"]))
    del meta["episode_length"]
    data["meta"] = np.array(json.dumps(meta))
    np.savez_compressed(path, **data)

    with pytest.raises(ValueError, match="generator is unknown"):
        TransitionDataset.load(path)


def test_a_development_override_is_permitted_and_recorded():
    dataset = collect(UnitSpec(n_transitions=100), stage="exp1", seed=0, episode_length=5)
    assert dataset.episode_length == 5, "an override must be recorded on the dataset"


def test_the_pool_and_episode_length_survive_a_round_trip(tmp_path):
    from bu.env.collect import TransitionDataset

    pools = _pools(250)
    path = pools.evaluation.save(tmp_path / "eval.npz")
    reloaded = TransitionDataset.load(path)
    assert reloaded.pool == "evaluation"
    assert reloaded.episode_length == K.EPISODE_LENGTH


def test_the_frozen_pool_sizes_are_what_the_constants_say():
    pools = _pools(1000)
    assert len(pools.validation) == K.VALIDATION_EPISODES * K.EPISODE_LENGTH
    assert len(pools.evaluation) == K.EVALUATION_EPISODES * K.EPISODE_LENGTH
    assert len(episode_indices(pools.validation)) == K.VALIDATION_EPISODES


# --- the policy carries no state across episodes (D-051, D-054) ------------


#: Everything a policy is *allowed* to carry across an episode boundary.
#: Enumerated rather than inferred from type, because the previous version of
#: this test only noticed non-empty dicts, lists and sets -- a scalar counter or
#: an array would have sailed through (D-055).
PERSISTENT_POLICY_FIELDS = {
    "unit", "rng", "p_bump", "p_interact", "p_approach", "epsilon",
}


def test_only_the_declared_fields_survive_a_reset():
    """Structural, because stationarity is a design property and a null
    diagnostic cannot prove it (D-054)."""
    unit = UnitSpec(n_transitions=200)
    policy = ExploratoryPolicy(unit, rng=stream(unit, "exp1", "policy", SEED))
    for i in range(20):
        policy.visits[("none", i % 5)] += 1
    policy.bump_visits["pass"] += 3
    assert policy.visits and policy.bump_visits

    policy.reset()
    assert not policy.visits and not policy.bump_visits

    stateful = {
        name for name, value in vars(policy).items()
        if name not in PERSISTENT_POLICY_FIELDS and value not in (None, 0, (), [], {})
    }
    assert not stateful, (
        f"undeclared state survived reset(): {sorted(stateful)}. Either clear it "
        "in reset() or add it to PERSISTENT_POLICY_FIELDS with a reason."
    )


def test_collect_resets_the_policy_once_per_episode():
    """The reset must actually be *called*, not merely available."""
    unit = UnitSpec(n_transitions=200)

    class _Spy(ExploratoryPolicy):
        resets = 0

        def reset(self) -> None:
            type(self).resets += 1
            super().reset()

    spy = _Spy(unit, rng=stream(unit, "exp1", "policy", 0))
    dataset = collect(unit, stage="exp1", seed=0, policy=spy)
    assert _Spy.resets == len(np.unique(dataset.episode))


def test_an_episode_does_not_depend_on_how_many_preceded_it():
    """The property the reset exists to give: identical state and identical RNG
    state produce identical behaviour, whatever came before."""
    unit = UnitSpec(n_transitions=200)
    _, info = __import__("bu.env.gridworld", fromlist=["GridWorld"]).GridWorld(unit).reset(seed=3)
    state = info["state"]

    fresh = ExploratoryPolicy(unit, rng=np.random.default_rng(11))
    worn = ExploratoryPolicy(unit, rng=np.random.default_rng(11))
    for _ in range(500):  # wear it in, then reset as collect() does
        worn.act(state)
    worn.reset()
    worn.rng = np.random.default_rng(11)

    assert [fresh.act(state) for _ in range(30)] == [worn.act(state) for _ in range(30)]


# --- repaired ensembles train the right model (D-056) ---------------------


REPAIR_CASES = [
    ("baseline", UnitSpec(family="capacity", hidden_size=16, n_transitions=500), "exp2b"),
    ("capacity_repair",
     UnitSpec(family="capacity", hidden_size=16, n_transitions=500), "exp2b"),
    ("feature_repair",
     UnitSpec(family="missing_feature", withheld_features=("shape",),
              confound_rate=0.5, n_transitions=500, hidden_size=32), "exp2a"),
    ("data_repair",
     UnitSpec(family="estimation", n_transitions=250, hidden_size=32), "exp1"),
]


@pytest.mark.parametrize("arm, unit, stage", REPAIR_CASES)
def test_every_repair_arm_trains_the_effective_model(arm, unit, stage):
    """Pool-collection tests were not enough (D-056).

    Passing one unit for both the model and the streams was silently wrong in
    opposite directions. With the unresolved unit a **capacity repair built the
    original small network** — the repair was never applied, nothing raised, and
    every capacity condition would have been labelled "repair failed". With the
    effective unit the model was right but the streams moved off the baseline's.
    """
    from bu.models.ensemble import train_ensemble

    pools = collect_pools(unit, stage=stage, seed=SEED, arm=arm)
    ensemble = train_ensemble(
        unit, pools, TrainConfig(max_epochs=2, ensemble_size=2),
        stage=stage, seed=SEED, arm=arm,
    )
    effective = Arm(arm).resolve(unit)

    assert ensemble.members[0].position_head.in_features == effective.hidden_size
    assert ensemble.members[0].encoder.size == pools.train.obs.shape[1]
    assert len(pools.train) == effective.n_transitions
    assert ensemble.effective_unit == effective
    assert ensemble.unit == unit, "the unresolved unit must survive on the ensemble"


def test_a_capacity_repair_is_actually_larger_than_its_baseline():
    """The specific silent failure, pinned."""
    from bu.models.ensemble import train_ensemble

    unit = UnitSpec(family="capacity", hidden_size=16, n_transitions=500)
    cfg = TrainConfig(max_epochs=1, ensemble_size=1)
    base = train_ensemble(unit, collect_pools(unit, stage="exp2b", seed=SEED),
                          cfg, stage="exp2b", seed=SEED)
    repaired = train_ensemble(
        unit, collect_pools(unit, stage="exp2b", seed=SEED, arm="capacity_repair"),
        cfg, stage="exp2b", seed=SEED, arm="capacity_repair",
    )
    assert base.members[0].position_head.in_features == 16
    assert repaired.members[0].position_head.in_features == max(K.HIDDEN_SIZES)


def test_a_feature_repair_widens_the_input():
    unit = UnitSpec(family="missing_feature", withheld_features=("shape",),
                    confound_rate=0.5, n_transitions=500)
    narrow = collect_pools(unit, stage="exp2a", seed=SEED).train.obs.shape[1]
    wide = collect_pools(unit, stage="exp2a", seed=SEED,
                         arm="feature_repair").train.obs.shape[1]
    assert wide > narrow


@pytest.mark.parametrize("arm, unit, stage", REPAIR_CASES)
def test_repair_streams_are_keyed_on_the_unresolved_unit(arm, unit, stage, monkeypatch):
    """Rewritten: the previous version was tautological (D-057).

    It asserted ``stream_key(unit, ...) == stream_key(Arm("baseline").resolve(unit), ...)``
    — but resolving the *baseline* arm returns the unit unchanged, so it
    compared a value with itself and passed for every arm without testing
    anything. That is the third instance of the property-versus-mechanism
    pattern already in CLAUDE.md's traps.

    This captures the units ``train_ensemble`` actually passes to ``stream()``,
    and asserts non-vacuity: for a repair that changes an identity field, the
    effective-unit key genuinely differs, so the test could fail.
    """
    import bu.models.ensemble as ensemble_module
    from bu.models.ensemble import train_ensemble
    from bu.streams import stream, stream_key

    seen: list[tuple] = []

    def _spy(unit_arg, stage_arg, purpose, seed_arg, *, member=None):
        seen.append((unit_arg, purpose))
        return stream(unit_arg, stage_arg, purpose, seed_arg, member=member)

    monkeypatch.setattr(ensemble_module, "stream", _spy)

    pools = collect_pools(unit, stage=stage, seed=SEED, arm=arm)
    train_ensemble(
        unit, pools, TrainConfig(max_epochs=1, ensemble_size=2),
        stage=stage, seed=SEED, arm=arm,
    )

    model_side = {"bootstrap", "init", "batch"}
    used = {purpose: {u for u, p in seen if p == purpose} for purpose in model_side}
    assert set(used) == model_side, f"a model-side stream was never drawn: {used}"
    for purpose, units in used.items():
        assert units == {unit}, (
            f"{purpose} was keyed on {units} rather than the unresolved unit"
        )

    # Non-vacuity: for an arm that moves an identity field, keying on the
    # effective unit would have produced a different stream.
    effective = Arm(arm).resolve(unit)
    if effective != unit:
        assert stream_key(unit, stage, "init") != stream_key(effective, stage, "init")


# --- pools and the run must describe the same thing (D-057) ---------------


MISMATCHES = [
    ("baseline pools with a repair arm", dict(arm="data_repair"), dict()),
    ("repair pools with baseline", dict(arm="baseline"), dict(arm="data_repair")),
    ("a different seed", dict(), dict(seed=SEED + 1)),
    ("a different stage", dict(), dict(stage="config_sweep")),
]


@pytest.mark.parametrize("label, run_kw, pool_kw", MISMATCHES)
def test_mismatched_pools_fail_before_any_model_is_built(label, run_kw, pool_kw):
    """Measured before this guard: baseline pools plus ``arm="data_repair"``
    trained on 250 transitions while the ensemble reported the data-repair
    identity with its effective 2,500 — a false repair label one layer above
    the one D-056 removed (D-057)."""
    from bu.models.ensemble import train_ensemble

    unit = UnitSpec(family="estimation", n_transitions=250, hidden_size=32)
    pools = collect_pools(
        unit, stage=pool_kw.get("stage", "exp1"), seed=pool_kw.get("seed", SEED),
        arm=pool_kw.get("arm", "baseline"),
    )
    with pytest.raises(ValueError, match="not generated for this run"):
        train_ensemble(
            unit, pools, TrainConfig(max_epochs=1, ensemble_size=1),
            stage=run_kw.get("stage", "exp1"), seed=run_kw.get("seed", SEED),
            arm=run_kw.get("arm", "baseline"),
        )


def test_pools_from_a_different_unit_are_rejected():
    from bu.models.ensemble import train_ensemble

    unit = UnitSpec(family="estimation", n_transitions=250, hidden_size=32)
    other = UnitSpec(family="estimation", n_transitions=500, hidden_size=32)
    with pytest.raises(ValueError, match="source_unit differs"):
        train_ensemble(
            unit, collect_pools(other, stage="exp1", seed=SEED),
            TrainConfig(max_epochs=1, ensemble_size=1), stage="exp1", seed=SEED,
        )


@pytest.mark.parametrize("arm, unit, stage", REPAIR_CASES)
def test_matched_pools_are_accepted_for_every_arm(arm, unit, stage):
    """The guard must not be so strict that the legitimate path stops working."""
    from bu.models.ensemble import train_ensemble

    pools = collect_pools(unit, stage=stage, seed=SEED, arm=arm)
    ensemble = train_ensemble(
        unit, pools, TrainConfig(max_epochs=1, ensemble_size=1),
        stage=stage, seed=SEED, arm=arm,
    )
    assert ensemble.arm == arm


# --- direct collect() is guarded too (D-056) ------------------------------


@pytest.mark.parametrize("pool", ["train", "validation", "evaluation"])
def test_direct_collect_enforces_the_frozen_size_on_confirmatory_seeds(pool):
    """The guard lived only in collect_pools, so a confirmatory caller could
    reach collect() directly and mint a pool of any size (D-056)."""
    unit = UnitSpec(family="estimation", n_transitions=5000)
    with pytest.raises(ValueError, match="frozen size"):
        collect(unit, 99, stage="exp1", seed=SEED, pool=pool)


def test_development_seeds_may_still_choose_any_size():
    unit = UnitSpec(family="estimation", n_transitions=5000)
    assert len(collect(unit, 99, stage="exp1", seed=0)) == 99


# --- repaired datasets can reconstruct their own stream (D-056) -----------


@pytest.mark.parametrize("arm, unit, stage", REPAIR_CASES)
def test_a_repaired_dataset_records_what_generated_it(arm, unit, stage, tmp_path):
    """Without the unresolved unit, arm and stage, a repaired dataset cannot
    reconstruct its stream — and a feature-repair dataset is indistinguishable
    from a baseline whose unit already had the restored features."""
    from bu.env.collect import TransitionDataset
    from bu.streams import STREAM_VERSION

    dataset = collect_pools(unit, stage=stage, seed=SEED, arm=arm).evaluation
    reloaded = TransitionDataset.load(dataset.save(tmp_path / f"{arm}.npz"))

    assert reloaded.source_unit == unit
    assert reloaded.unit == Arm(arm).resolve(unit)
    assert (reloaded.arm, reloaded.stage, reloaded.pool) == (arm, stage, "evaluation")
    assert reloaded.stream_version == STREAM_VERSION
    assert reloaded.episode_length == K.EPISODE_LENGTH


# --- W3 audit regressions (D-060) -----------------------------------------


def test_member_predictions_restores_training_mode():
    """W3-4. Inert for this MLP, live for P§9.3's MC-dropout fallback.

    A member silently left in eval mode returns deterministic predictions under
    test-time dropout, so disagreement would be exactly zero and the fallback
    estimator would look like it had failed H1 at the very gate it exists for.
    """
    from bu.models.ensemble import train_ensemble

    unit = UnitSpec(hidden_size=32, n_transitions=500)
    pools = collect_pools(unit, stage="exp1", seed=SEED)
    ensemble = train_ensemble(
        unit, pools, TrainConfig(max_epochs=1, ensemble_size=2), stage="exp1", seed=SEED
    )
    for model in ensemble.members:
        model.train()

    ensemble.member_predictions(
        torch.as_tensor(pools.evaluation.obs[:8]),
        torch.as_tensor(pools.evaluation.action[:8]),
    )
    assert all(m.training for m in ensemble.members), "members left in eval mode"

    for model in ensemble.members:
        model.eval()
    ensemble.member_predictions(
        torch.as_tensor(pools.evaluation.obs[:8]),
        torch.as_tensor(pools.evaluation.action[:8]),
    )
    assert not any(m.training for m in ensemble.members), "eval mode not preserved either"


@pytest.mark.parametrize("bad", ["negative", "too_large"])
def test_an_out_of_range_train_index_is_rejected(bad):
    """W3-6. Torch wraps negative indices silently, so a resample producing one
    would train on the wrong rows and fail later for an unrelated reason."""
    unit = UnitSpec(hidden_size=32, n_transitions=500)
    pools = collect_pools(unit, stage="exp1", seed=SEED)
    index = np.array([-1]) if bad == "negative" else np.array([len(pools.train) + 1])

    with pytest.raises(ValueError, match="train_index runs"):
        train(
            WorldModel(unit, stream(unit, "exp1", "init", SEED)),
            pools.train, pools.validation, TrainConfig(max_epochs=1),
            rng=stream(unit, "exp1", "batch", SEED), train_index=index,
        )


def test_the_normalising_scale_is_fixed_to_the_pool():
    """W3-1, ruled on by D-061. The scale belongs to the pool, not to a subset.

    Recomputing it from a subset makes the *units* move with the subset:
    measured, [0.229, 0.224] over the full pool against [0.294, 0.348] over its
    worst 5%. **Both** the primary error and the registered H2 ratio move with
    it — a scalar scale would cancel between numerator and denominator, but a
    per-dimension one divides each dimension differently, so the two norms have
    no common factor. Measured on pilot data the endpoint shifts by up to 4.6%.

    The docstring this replaces asserted the ratio was invariant. It was not.
    """
    from bu.models.uncertainty import NormalisationScale, summarise

    g = torch.Generator().manual_seed(0)
    targets = torch.randn(500, 2, generator=g)
    members = targets.unsqueeze(0) + 0.3 * torch.randn(5, 500, 2, generator=g)

    pool_scale = NormalisationScale.from_evaluation_pool(targets)
    subset = slice(0, 20)
    subset_scale = NormalisationScale.from_evaluation_pool(targets[subset])

    free = summarise(
        members[:, subset], targets[subset], n_transitions=1, seed=0, scale=subset_scale
    )
    fixed = summarise(
        members[:, subset], targets[subset], n_transitions=1, seed=0, scale=pool_scale
    )
    assert free.mean_error != pytest.approx(fixed.mean_error, rel=1e-3), (
        "the subset happened to have the pool's scale; pick a different subset"
    )
    assert free.ratio != pytest.approx(fixed.ratio, rel=1e-6)
    # The scale that produced the number is carried in the number's own record,
    # and it names how many transitions it was measured over -- 500, not 20.
    assert fixed.scale_n_reference == 500
    assert fixed.scale == pytest.approx(tuple(float(v) for v in pool_scale.vector))


def test_the_dead_validation_fraction_knob_is_gone():
    """W3-5. A knob that does nothing still tells a reader a split happens."""
    assert not hasattr(TrainConfig(), "val_fraction")
