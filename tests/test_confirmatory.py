"""C-008's runner: the rules it owns, and one real fit that proves it records.

Sol raised this at the certification of 2875e60 and it has blocked confirmatory
execution and repair validation since. Every test here asks the question the
project keeps learning to ask: could this fail?
"""

from __future__ import annotations

import inspect
import json

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Config, TrainConfig, UnitSpec
from bu.experiments import confirmatory as C

CONF = K.CONFIRMATORY_SEED_BASE


def small(**kw):
    """A cheap unit for the refusal tests, which never fit anything."""
    kw.setdefault("n_transitions", 100)
    kw.setdefault("hidden_size", 16)
    return UnitSpec(**kw)


def registered_unit():
    """A unit the design ACTUALLY registers, and the cheapest one available.

    The refusal tests can use any spec because they never reach a fit, but a real
    run has to discharge a real obligation now -- `assert_registered_obligation`
    refuses anything the design's execution plan does not contain. Derived from
    `execution_plan(design_units())`, the same artefact the guard reads (D-133):
    the no-arg plan is the POOL, and this helper previously found the right unit
    only because `full_matrix()` happens to enumerate the reference
    configuration first -- a property standing on an accident (D-055). This is
    the n=100 estimation/uniform/shape condition, which carries both `exp1` and
    `repair_validation` roles at seed index 0.
    """
    from bu.experiments.enumerate_units import design_units, execution_plan

    for fit in execution_plan(design_units()):
        if fit.arm == "baseline" and fit.seed == 0 and fit.unit.n_transitions == 100:
            return fit.unit
    raise AssertionError("no cheap registered baseline obligation found")


# --- the seed policy (D-034) ------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 4, K.CONFIRMATORY_SEED_BASE - 1])
def test_development_seeds_are_refused(seed):
    with pytest.raises(ValueError, match="development data"):
        C.check_confirmatory(stage="exp1", seed=seed, arm="baseline", unit=small())


def test_the_confirmatory_boundary_is_inclusive_at_the_base():
    C.check_confirmatory(stage="exp1", seed=CONF, arm="baseline", unit=small())


def test_the_refusal_happens_before_any_fit(tmp_path):
    """A development fit that reaches an analysis has already spent its compute."""
    with pytest.raises(ValueError, match="development data"):
        C.run_confirmatory(small(), stage="exp1", seed=0, out_dir=tmp_path)
    assert not list(tmp_path.iterdir()), "a refused run still wrote to disk"


# --- registered stage and arm ------------------------------------------------


def test_the_pilot_stage_cannot_carry_a_confirmatory_obligation():
    with pytest.raises(ValueError, match="no registered seed policy"):
        C.check_confirmatory(stage="pilot", seed=CONF, arm="baseline", unit=small())


def test_an_unknown_stage_is_refused():
    with pytest.raises(ValueError, match="unknown stage"):
        C.check_confirmatory(stage="exp9", seed=CONF, arm="baseline", unit=small())


def test_an_arm_that_cannot_apply_to_this_unit_is_refused():
    """Feature repair on a unit with nothing withheld has nothing to restore."""
    with pytest.raises(ValueError):
        C.check_confirmatory(stage="exp1", seed=CONF, arm="feature_repair",
                             unit=small(withheld_features=()))


# --- episode bootstrap only, structurally ------------------------------------


def test_the_runner_has_no_granularity_parameter():
    """A parameter accepting one value is weaker than no parameter.

    It invites a caller to pass something else and reads as a knob. This asserts
    the absence, which is the actual design claim (D-053).
    """
    params = inspect.signature(C.run_confirmatory).parameters
    assert "granularity" not in params
    assert C.CONFIRMATORY_GRANULARITY == "episode"


def test_the_bypass_train_ensemble_used_to_confess_is_closed():
    """`bootstrap_episodes` + `train(train_index=...)` no longer walks around it.

    Asserted on the low-level resampling function, because that is where the
    hole was. Going through `train_ensemble` would only re-test the outer guard.
    """
    from bu.models.ensemble import bootstrap_episodes
    from bu.env.collect import collect_pools
    from bu.streams import stream

    unit = registered_unit()
    pools = collect_pools(unit, stage="exp1", seed=CONF)
    rng = stream(unit, "exp1", "bootstrap", CONF, member=0)
    for bad in ("transition", "none"):
        with pytest.raises(ValueError, match="on confirmatory seed"):
            bootstrap_episodes(pools.train, rng, seed=CONF, granularity=bad)


# --- one real fit, and what it must record -----------------------------------


@pytest.fixture(scope="module")
def clean_tree():
    """Force a clean git state for the module's real runs.

    `run_confirmatory` refuses a dirty tree with no override (Sol, delta 45), so
    a test that fits anything has to say what code state it is pretending to be.
    Monkeypatching that is honest; an `allow_dirty` flag in the runner would not
    have been.
    """
    import bu.runrecord as RR
    from bu.runrecord import GitState

    fake = lambda *_args, **_kwargs: GitState(
        commit="d" * 40, dirty=False, branch="main"
    )
    real_confirmatory = C.git_state
    real_runrecord = RR.git_state
    C.git_state = fake
    RR.git_state = fake
    try:
        yield
    finally:
        C.git_state = real_confirmatory
        RR.git_state = real_runrecord


@pytest.fixture(scope="module")
def real_run(tmp_path_factory, clean_tree):
    """One genuine confirmatory fit at a tiny shape. Two members, ~seconds."""
    out = tmp_path_factory.mktemp("confirmatory")
    return C.run_confirmatory(registered_unit(), stage="exp1", seed=CONF, out_dir=out)


def test_a_real_run_records_the_granularity_it_actually_used(real_run):
    assert real_run.run["granularity"] == "episode"
    record = json.loads((real_run.record_dir / "run.json").read_text())
    assert record["extra"]["granularity"] == "episode"


def test_a_real_run_is_marked_confirmatory_in_the_record(real_run):
    assert real_run.run["seed_partition"] == "confirmatory"
    record = json.loads((real_run.record_dir / "run.json").read_text())
    assert record["extra"]["seed_partition"] == "confirmatory"


def test_the_record_carries_every_field_the_evidence_contract_requires(real_run):
    """Complete records was one of Sol's five, and this is what makes it checkable."""
    from bu.stats.gate import REQUIRED_RUN_FIELDS

    missing = [f for f in REQUIRED_RUN_FIELDS
               if f not in real_run.run and f not in ("row_index", "row_digest")]
    assert not missing, f"the run record could not be verified: missing {missing}"


def test_the_digests_are_of_the_files_actually_written(real_run):
    """A digest that matches nothing on disk verifies nothing."""
    import hashlib

    for field, name in (("run_record_digest", "run.json"),
                        ("member_record_digest", "metrics.jsonl")):
        actual = hashlib.sha256((real_run.record_dir / name).read_bytes()).hexdigest()
        assert real_run.run[field] == actual


def test_confirmatory_metrics_persist_member_bound_epoch_curves(real_run):
    """A completed batch must retain the loss curves needed for diagnosis."""
    rows = [
        json.loads(line)
        for line in (real_run.record_dir / "metrics.jsonl").read_text().splitlines()
        if line.strip()
    ]
    epochs = [row for row in rows if row.get("record_type") == "epoch"]
    summaries = [
        row for row in rows if row.get("record_type") == "member_summary"
    ]
    assert epochs
    assert {row["member"] for row in epochs} == set(range(real_run.member_count))
    assert len(summaries) == real_run.member_count


def test_threading_is_recorded_for_contract_v2(real_run):
    """v2 requires it on the record written at training time (D-088)."""
    record = json.loads((real_run.record_dir / "run.json").read_text())
    for field in ("num_threads", "num_interop_threads"):
        assert record["extra"]["threading"][field] is not None
        assert real_run.run["threading"][field] == record["extra"]["threading"][field]


def test_the_execution_device_is_frozen_and_recorded(real_run):
    record = json.loads((real_run.record_dir / "run.json").read_text())
    assert C.CONFIRMATORY_DEVICE == "cpu"
    assert record["extra"]["device"] == C.CONFIRMATORY_DEVICE
    assert real_run.run["device"] == C.CONFIRMATORY_DEVICE


def test_the_identities_are_distinct_roles_not_duplicates(real_run):
    """fit_id has no stage; run_id does. Conflating them cost 375 phantom fits."""
    assert real_run.fit_id != real_run.run_id
    assert real_run.stage in real_run.run_id
    assert real_run.stage not in real_run.fit_id


def test_the_evaluation_pool_digest_is_of_contents_not_of_a_label(real_run):
    """A label can be reused across different pools; contents cannot."""
    from bu.env.collect import collect_pools

    pools = collect_pools(registered_unit(), stage="exp1", seed=CONF)
    assert real_run.run["evaluation_pool_digest"] == C._digest_pool(pools)
    other = collect_pools(registered_unit(), stage="exp1", seed=CONF + 1)
    assert C._digest_pool(other) != real_run.run["evaluation_pool_digest"]


def test_evaluation_pool_digest_frames_names_shapes_and_dtypes():
    from types import SimpleNamespace

    def pools(obs, action):
        evaluation = SimpleNamespace(
            obs=np.asarray(obs, dtype=np.int64),
            action=np.asarray(action, dtype=np.int64),
            next_obs=np.asarray([3], dtype=np.int64),
            episode=np.asarray([4], dtype=np.int64),
        )
        return SimpleNamespace(evaluation=evaluation)

    # These first two raw arrays concatenate to the same bytes.  Their framed
    # semantic inventories are still different and must hash differently.
    assert C._digest_pool(pools([1], [2])) != C._digest_pool(pools([1, 2], []))


def test_the_scale_comes_from_the_full_pool_with_no_mask_available(real_run):
    """D-061/C-010: the scale precedes any mask structurally, not by ordering."""
    from bu.models.uncertainty import ScaledEvaluation

    assert "mask" not in inspect.signature(ScaledEvaluation.from_pool).parameters
    assert real_run.run["normalisation"]["scale_source"] == "evaluation_pool"


def test_primary_outputs_survive_beyond_the_training_process(real_run):
    """Week 7 must not need to rerun a Week 6 model to recover its inputs."""
    assert np.isfinite(real_run.run["mean_error"])
    assert np.isfinite(real_run.run["mean_disagreement"])
    assert np.isfinite(real_run.run["mean_predictive_variance"])
    assert np.isfinite(real_run.run["ratio"])
    assert real_run.diagnostics is not None
    required = {
        "episode", "step", "error", "disagreement", "predictive_variance",
        "scale", "scale_n_reference", "scale_domain", "scale_source",
        "evaluation_action",
    }
    assert required == set(real_run.diagnostics)
    n = len(real_run.evaluation)
    for field in ("episode", "step", "error", "disagreement", "predictive_variance"):
        assert real_run.diagnostics[field].shape == (n,)


@pytest.fixture(scope="module")
def real_persisted_fit(tmp_path_factory, clean_tree):
    """One genuine producer -> immutable sidecar -> verified loader round trip."""
    from bu.experiments.fit_evidence import run_confirmatory_fit

    out = tmp_path_factory.mktemp("persisted-confirmatory-fit")
    return run_confirmatory_fit(
        registered_unit(), arm="baseline", seed=CONF, out_dir=out
    )


def test_real_producer_sidecar_preserves_the_complete_action_inventory(
    real_persisted_fit,
):
    """The full-action mask contract is exercised on a real fit, not only stubs."""
    from bu.models.world_model import MOVEMENT_ACTIONS

    physical = real_persisted_fit.physical
    verified = real_persisted_fit.verified
    source_actions = np.asarray(physical.diagnostics["evaluation_action"])
    stored_actions = verified.diagnostics["evaluation_action"]
    movement = np.isin(stored_actions, np.asarray(MOVEMENT_ACTIONS))
    full_episode = np.repeat(
        np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH
    )
    full_step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)

    assert len(stored_actions) == K.EVALUATION_EPISODES * K.EPISODE_LENGTH
    assert np.array_equal(stored_actions, source_actions)
    assert np.array_equal(verified.episode, full_episode[movement])
    assert np.array_equal(verified.step, full_step[movement])
    assert np.array_equal(verified.error, physical.evaluation.error)


# --- C-008 integration (Sol's ruling on delta 44) ---------------------------


def test_an_unregistered_obligation_is_refused():
    """Sol: the runner accepted arbitrary unit/stage combinations.

    A fit that discharges no registered obligation is compute spent outside the
    design while writing a record indistinguishable from one inside it.
    """
    with pytest.raises(ValueError, match="not a registered obligation"):
        C.assert_registered_obligation(
            small(hidden_size=16), arm="baseline", stage="exp1", seed=CONF
        )


def test_a_registered_obligation_is_accepted():
    """The guard must not refuse the thing it exists to protect."""
    C.assert_registered_obligation(
        registered_unit(), arm="baseline", stage="exp1", seed=CONF
    )


def test_a_seed_beyond_the_registered_count_is_refused():
    """exp1 owes five seeds; the sixth discharges nothing."""
    from bu.config import seeds_for

    n = seeds_for("exp1")
    with pytest.raises(ValueError, match="not a registered obligation"):
        C.assert_registered_obligation(
            registered_unit(), arm="baseline", stage="exp1", seed=CONF + n
        )


def test_every_pool_only_obligation_key_is_refused():
    """The registry must be built from the design, not from the pool.

    `full_matrix()` is the ~531-unit pool the design draws on; `design_units()`
    is the registered 300 ("this matrix is the pool, not the plan"). A
    confirmatory fit on a pool-only unit discharges no registered obligation,
    The original regression covered only baseline/config_sweep/seed-index-0,
    231 of 1,653 removed obligation keys.  Quantifying the COMPLETE key
    difference covers repaired arms, every role, and every seed index too; a
    partial fix that filters only the old test shape must fail (D-055, D-133).

    Stated over EVERY pool-only unit rather than one example: which units the
    round-robin sweep leaves out is an accident of the draw, and a single named
    unit's pool-only-ness would stand on that accident (D-055). Pure set
    membership -- nothing here trains, collects, or fits.
    """
    from bu.config import Config
    from bu.experiments.enumerate_units import (
        design_units,
        execution_plan,
        full_matrix,
    )

    def keys(units):
        out = {}
        for fit in execution_plan(units):
            unit_id = Config(unit=fit.unit).unit_id
            for role in fit.roles:
                out[(unit_id, fit.arm, role, fit.seed)] = fit.unit
        return out

    design = keys(design_units())
    pool = keys(full_matrix())
    removed = {key: unit for key, unit in pool.items() if key not in design}
    assert removed, "the pool plan no longer exceeds the design; test is vacuous"
    assert {key[1] for key in removed} > {"baseline"}, (
        "fixture lost repaired-arm coverage"
    )
    assert max(key[3] for key in removed) > 0, "fixture lost later seed indices"
    for (_, arm, stage, seed_index), unit in removed.items():
        with pytest.raises(ValueError, match="not a registered obligation"):
            C.assert_registered_obligation(
                unit, arm=arm, stage=stage, seed=CONF + seed_index
            )


def test_every_design_obligation_key_remains_registered():
    """The complement: narrowing pool -> design must preserve every exact key.

    Covers all arms, roles, and seed indices in the 300-unit plan. A registry
    narrowed to canonical units, baseline only, or seed index zero would pass
    the negative test but fail here.
    """
    from bu.experiments.enumerate_units import design_units, execution_plan

    plan = execution_plan(design_units())
    assert plan, "registered execution plan is empty"
    seen_arms = set()
    seen_seed_indices = set()
    for fit in plan:
        seen_arms.add(fit.arm)
        seen_seed_indices.add(fit.seed)
        for role in fit.roles:
            C.assert_registered_obligation(
                fit.unit,
                arm=fit.arm,
                stage=role,
                seed=CONF + fit.seed,
            )
    assert seen_arms == {"baseline", "data_repair", "feature_repair",
                         "capacity_repair"}
    assert max(seen_seed_indices) > 0


def test_the_training_configuration_is_frozen_not_accepted():
    """TrainConfig is not part of run_id, so two configurations would share one identity."""
    params = inspect.signature(C.run_confirmatory).parameters
    assert "train" not in params
    assert C.CONFIRMATORY_TRAIN == TrainConfig()
    assert C.REPAIRED_TRAIN.ensemble_size == 1


def test_a_dirty_tree_is_refused_before_fitting(monkeypatch, tmp_path):
    from bu.runrecord import GitState

    monkeypatch.setattr(C, "git_state",
                        lambda: GitState(commit="c" * 40, dirty=True, branch="main"))
    with pytest.raises(ValueError, match="dirty"):
        C.run_confirmatory(registered_unit(), stage="exp1", seed=CONF, out_dir=tmp_path)
    assert not list(tmp_path.iterdir()), "a refused run still wrote to disk"


def test_a_gitless_tree_is_refused_before_fitting(monkeypatch, tmp_path):
    """An empty git stderr is not evidence of a clean, reproducible tree."""
    from bu.runrecord import GitState

    monkeypatch.setattr(
        C,
        "git_state",
        lambda: GitState(commit="UNCOMMITTED", dirty=False, branch="unknown"),
    )
    with pytest.raises(ValueError, match="UNCOMMITTED"):
        C.run_confirmatory(
            registered_unit(), stage="exp1", seed=CONF, out_dir=tmp_path
        )
    assert not list(tmp_path.iterdir()), "a refused run still wrote to disk"


def test_a_repaired_arm_without_a_scale_is_refused(tmp_path):
    """D-061: the repaired arm reuses the baseline's scale, never its own."""
    with pytest.raises(ValueError, match="was given no scale"):
        C.run_confirmatory(registered_unit(), stage="repair_validation", seed=CONF,
                           arm="data_repair", out_dir=tmp_path)


def test_a_baseline_refuses_a_caller_supplied_scale_before_writing(tmp_path):
    from bu.models.uncertainty import NormalisationScale

    injected = NormalisationScale(torch.ones(2), n_reference=2)
    with pytest.raises(ValueError, match="baseline cannot accept"):
        C.run_confirmatory(
            registered_unit(),
            stage="exp1",
            seed=CONF,
            arm="baseline",
            out_dir=tmp_path,
            scale=injected,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("arm", ["baseline", "data_repair", "feature_repair"])
def test_legacy_pair_by_pair_repair_validation_is_disabled(
    arm, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        C,
        "run_confirmatory",
        lambda *args, **kwargs: pytest.fail("refusal must happen before a fit"),
    )
    with pytest.raises(ValueError, match="duplicate a baseline fit"):
        C.run_repair_validation(
            registered_unit(), seed=CONF, arm=arm, out_dir=tmp_path
        )
    assert not list(tmp_path.iterdir())


def test_the_runner_exposes_no_dirty_override_or_thread_choice():
    """Sol, delta 45: both produce registered evidence under a configuration
    that is not represented in run identity."""
    params = set(inspect.signature(C.run_confirmatory).parameters)
    for forbidden in ("allow_dirty", "threads", "interop_threads"):
        assert forbidden not in params
    assert C.CONFIRMATORY_THREADS == 4 and C.CONFIRMATORY_INTEROP_THREADS == 4


def test_a_dirty_tree_cannot_be_overridden(tmp_path):
    from bu.runrecord import GitState

    real = C.git_state
    C.git_state = lambda: GitState(commit="e" * 40, dirty=True, branch="main")
    try:
        with pytest.raises(ValueError, match="no override"):
            C.run_confirmatory(registered_unit(), stage="exp1", seed=CONF,
                               out_dir=tmp_path)
    finally:
        C.git_state = real
    assert not list(tmp_path.iterdir())


# --- Legacy Week 6 one-seed repair harness ---------------------------------


@pytest.mark.parametrize(
    "unit",
    [
        UnitSpec(
            family="missing_feature",
            withheld_features=("shape",),
            confound_rate=0.25,
        ),
        UnitSpec(family="capacity", hidden_size=16),
        UnitSpec(family="estimation", n_transitions=100),
        UnitSpec(
            family="missing_feature",
            withheld_features=("shape",),
            hidden_size=16,
            confound_rate=0.25,
        ),
    ],
)
def test_legacy_one_seed_repair_condition_path_is_disabled(
    unit, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        C,
        "run_confirmatory",
        lambda *args, **kwargs: pytest.fail("refusal must happen before a fit"),
    )
    with pytest.raises(ValueError, match="one-seed in-memory result"):
        C.run_repair_condition(unit, seed=CONF, out_dir=tmp_path)
