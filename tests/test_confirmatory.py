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

from bu import constants as K
from bu.config import TrainConfig, UnitSpec
from bu.experiments import confirmatory as C

CONF = K.CONFIRMATORY_SEED_BASE


def small(**kw):
    kw.setdefault("n_transitions", 100)
    kw.setdefault("hidden_size", 16)
    return UnitSpec(**kw)


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

    unit = small()
    pools = collect_pools(unit, stage="exp1", seed=CONF)
    rng = stream(unit, "exp1", "bootstrap", CONF, member=0)
    for bad in ("transition", "none"):
        with pytest.raises(ValueError, match="on confirmatory seed"):
            bootstrap_episodes(pools.train, rng, seed=CONF, granularity=bad)


# --- one real fit, and what it must record -----------------------------------


@pytest.fixture(scope="module")
def real_run(tmp_path_factory):
    """One genuine confirmatory fit at a tiny shape. Two members, ~seconds."""
    out = tmp_path_factory.mktemp("confirmatory")
    return C.run_confirmatory(
        small(), stage="exp1", seed=CONF, out_dir=out,
        train=TrainConfig(ensemble_size=2, max_epochs=3, patience=2),
    )


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


def test_threading_is_recorded_for_contract_v2(real_run):
    """v2 requires it on the record written at training time (D-088)."""
    record = json.loads((real_run.record_dir / "run.json").read_text())
    for field in ("num_threads", "num_interop_threads"):
        assert record["extra"]["threading"][field] is not None
        assert real_run.run["threading"][field] == record["extra"]["threading"][field]


def test_the_identities_are_distinct_roles_not_duplicates(real_run):
    """fit_id has no stage; run_id does. Conflating them cost 375 phantom fits."""
    assert real_run.fit_id != real_run.run_id
    assert real_run.stage in real_run.run_id
    assert real_run.stage not in real_run.fit_id


def test_the_evaluation_pool_digest_is_of_contents_not_of_a_label(real_run):
    """A label can be reused across different pools; contents cannot."""
    from bu.env.collect import collect_pools

    pools = collect_pools(small(), stage="exp1", seed=CONF)
    assert real_run.run["evaluation_pool_digest"] == C._digest_pool(pools)
    other = collect_pools(small(), stage="exp1", seed=CONF + 1)
    assert C._digest_pool(other) != real_run.run["evaluation_pool_digest"]


def test_the_scale_comes_from_the_full_pool_with_no_mask_available(real_run):
    """D-061/C-010: the scale precedes any mask structurally, not by ordering."""
    from bu.models.uncertainty import ScaledEvaluation

    assert "mask" not in inspect.signature(ScaledEvaluation.from_pool).parameters
    assert real_run.run["normalisation"]["scale_source"] == "evaluation_pool"
