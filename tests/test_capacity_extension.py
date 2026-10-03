"""D-154's additive capacity arm: source invariants and synthetic evidence.

No experimental payload is opened or confirmatory model trained. The model
construction test calls the real ensemble builder but replaces optimization;
persisted fits below are fabricated by the existing evidence-test helpers.
Sweep pairing and historical production launchers are deliberately not changed.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Arm, Config, UnitSpec
from bu.env.collect import collect_pools
from bu.experiments import fit_evidence as F, label_evidence as L
from bu.experiments.enumerate_units import (
    arms_for, comparison_groups, design_units, execution_plan,
    repair_obligations, repair_validation_units, total_model_fits,
)
from bu.experiments.repair import REPAIR_STAGE, applicable_arms
from bu.models import ensemble as E
from bu.models.train import TrainResult
from bu.models.world_model import N_HIDDEN_LAYERS, WorldModel
from bu.streams import confirmatory_seeds, stream, stream_key

from test_fit_evidence import (
    _completed_run, _resign_physical_sources, _rewrite_unsealed_sources,
)
from test_label_evidence import _SyntheticFitStore, _conditions


EXTENSION = "capacity_extension_repair"
MODEL_ARMS = {"feature_repair", "capacity_repair", EXTENSION}
OLD_PLAN_SHA256 = "dd05d299a8f159ceaf749dc89ae5480b2c9777695dfdae8bf3a90aa47d5f3642"


def _extension_unit():
    return next(
        unit for unit in repair_validation_units()
        if unit.family == "estimation" and unit.n_transitions == 100
    )


def test_d154_completes_exactly_the_missing_assignments_without_new_units():
    units = design_units()
    assert len(units) == 300
    assert len(comparison_groups(units)) == 240
    for unit in units:
        registered = set(arms_for(unit)) & MODEL_ARMS
        assert len(registered) == 1, unit
        assert set(applicable_arms(unit)) == set(arms_for(unit)) - {"baseline"}
    added = [unit for unit in units if EXTENSION in arms_for(unit)]
    assert len(added) == 173
    assert Counter(unit.family for unit in added) == {
        "estimation": 150, "capacity": 23,
    }
    assert all(not unit.withheld_features and unit.hidden_size == 256 for unit in added)
    ladder = repair_validation_units()
    assert sum(unit in ladder for unit in added) == 7
    assert sum(unit not in ladder for unit in added) == 166
    assert all(len(set(arms_for(unit)) & MODEL_ARMS) == 1 for unit in ladder)


def test_d154_adds_638_single_models_with_exact_registered_seed_obligations():
    units = design_units()
    obligations = [ob for ob in repair_obligations(units) if ob.arm == EXTENSION]
    assert Counter((ob.stage, ob.seeds) for ob in obligations) == {
        ("repair_validation", 20): 7, ("exp3_repairs", 3): 166,
    }
    assert sum(ob.seeds for ob in obligations) == 638
    assert len(repair_obligations(units)) == 600
    plan = execution_plan(units)
    added = [fit for fit in plan if fit.arm == EXTENSION]
    assert len(added) == 638
    assert Counter(fit.roles for fit in added) == {
        ("repair_validation",): 140, ("exp3_repairs",): 498,
    }
    assert all(fit.members == 1 for fit in added)
    assert len(plan) == 3585
    assert len({fit.fit_id for fit in plan}) == len(plan)
    assert total_model_fits(units) == {
        "baseline_ensembles": 6375, "repairs": 2310,
        "ablations": 150, "total": 8835,
    }


def test_every_old_execution_row_retains_its_golden_identity_roles_and_config():
    old = [fit for fit in execution_plan(design_units()) if fit.arm != EXTENSION]
    assert len(old) == 2947
    rows = [
        {
            "fit_id": fit.fit_id,
            "roles": fit.roles,
            "members": fit.members,
            "config": Config(
                unit=fit.unit, arm=Arm(fit.arm), seed=fit.seed,
            ).to_dict(),
        }
        for fit in old
    ]
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == OLD_PLAN_SHA256


@pytest.mark.parametrize("hidden_size", [16, 64, 128, 255, 256, 257, 512, 1024])
@pytest.mark.parametrize("withheld", [(), ("shape",), ("colour",), ("position",)])
def test_extension_applicability_is_exact_not_a_general_larger_model_ladder(
    hidden_size, withheld,
):
    unit = UnitSpec(hidden_size=hidden_size, withheld_features=withheld)
    permitted = hidden_size == 256 and not withheld
    assert (EXTENSION in arms_for(unit)) == permitted
    assert (EXTENSION in applicable_arms(unit)) == permitted
    if permitted:
        effective = Arm(EXTENSION).resolve(unit)
        assert effective == replace(unit, hidden_size=512)
    else:
        with pytest.raises(ValueError, match="full observation.*hidden_size=256"):
            Arm(EXTENSION).resolve(unit)
        with pytest.raises(ValueError, match="full observation.*hidden_size=256"):
            Config(unit=unit, arm=Arm(EXTENSION))


def test_existing_capacity_repair_and_other_interventions_are_not_redefined():
    assert K.HIDDEN_SIZES == (16, 32, 64, 128, 256)
    assert K.CAPACITY_EXTENSION_HIDDEN_SIZE == 512
    assert N_HIDDEN_LAYERS == 2
    for width in K.HIDDEN_SIZES[:-1]:
        unit = UnitSpec(hidden_size=width)
        assert Arm("capacity_repair").resolve(unit) == replace(unit, hidden_size=256)
    for width in (256, 512):
        with pytest.raises(ValueError, match="there is no capacity to add"):
            Arm("capacity_repair").resolve(UnitSpec(hidden_size=width))
    unit = _extension_unit()
    assert Arm("baseline").resolve(unit) is unit
    assert Arm("data_repair").resolve(unit) == replace(unit, n_transitions=1000)
    missing = replace(unit, withheld_features=("shape",))
    assert Arm("feature_repair").resolve(missing) == unit
    # A non-design unit with two OLD model repairs remains ambiguous by
    # construction; extension registration must not select one by priority.
    multiple = replace(missing, hidden_size=64)
    assert set(applicable_arms(multiple)) & MODEL_ARMS == {
        "feature_repair", "capacity_repair",
    }


def test_extension_config_keeps_source_identity_and_changes_only_effective_width():
    source = _extension_unit()
    config = Config(unit=source, arm=Arm(EXTENSION), seed=1000, stage=REPAIR_STAGE)
    baseline = replace(config, arm=Arm("baseline"))
    assert config.unit is source
    assert config.unit_id == baseline.unit_id
    assert config.config_id != baseline.config_id
    assert config.fit_id != baseline.fit_id
    assert config.run_id != baseline.run_id
    assert config.to_dict()["unit"]["hidden_size"] == 256
    assert Config.from_dict(config.to_dict()) == config
    changed = {
        key: value for key, value in asdict(config.effective_unit).items()
        if value != asdict(source)[key]
    }
    assert changed == {"hidden_size": 512}


def test_real_ensemble_constructs_width512_using_only_source_unit_rng(monkeypatch):
    source = _extension_unit()
    stage, seed = "pilot", 17
    baseline = collect_pools(source, stage=stage, seed=seed)
    pools = collect_pools(source, stage=stage, seed=seed, arm=EXTENSION)
    for name in ("train", "validation", "evaluation"):
        base_pool, repaired_pool = getattr(baseline, name), getattr(pools, name)
        assert repaired_pool.source_unit == source
        assert repaired_pool.unit == replace(source, hidden_size=512)
        for field in ("obs", "next_obs", "action", "episode", "step"):
            np.testing.assert_array_equal(getattr(base_pool, field), getattr(repaired_pool, field))

    stream_calls = []

    def checked_stream(unit, requested_stage, purpose, requested_seed, *, member=None):
        assert unit is source, "effective width must not enter stream identity"
        stream_calls.append((purpose, member))
        return stream(unit, requested_stage, purpose, requested_seed, member=member)

    trained = []

    def construction_only(model, train_data, validation, config, *, rng, train_index, logger):
        # Exercise real initialization and ensemble wiring, never optimization.
        reference = WorldModel(
            replace(source, hidden_size=512), stream(source, stage, "init", seed, member=0),
        )
        assert model.trunk[0].in_features == 35
        assert model.trunk[0].out_features == model.trunk[2].out_features == 512
        assert model.position_head.out_features == 2
        assert model.activation_head.out_features == 4
        assert config == F.REPAIRED_TRAIN
        for key, value in reference.state_dict().items():
            assert torch.equal(model.state_dict()[key], value)
        expected_batch = stream(source, stage, "batch", seed, member=0)
        np.testing.assert_array_equal(rng.integers(2**31, size=8), expected_batch.integers(2**31, size=8))
        trained.append(model)
        return TrainResult(0, 0.0, 0, False, n_train=len(train_index), n_validation=len(validation))

    monkeypatch.setattr(E, "stream", checked_stream)
    monkeypatch.setattr(E, "train", construction_only)
    ensemble = E.train_ensemble(
        source, pools, F.REPAIRED_TRAIN, stage=stage, seed=seed, arm=EXTENSION,
    )
    assert stream_calls == [("bootstrap", 0), ("init", 0), ("batch", 0)]
    assert ensemble.unit is source
    assert ensemble.effective_unit == replace(source, hidden_size=512)
    assert ensemble.members == tuple(trained)
    assert len(ensemble.members) == 1
    assert stream_key(source, stage, "init", member=0) != stream_key(
        ensemble.effective_unit, stage, "init", member=0,
    ), "source/effective RNG comparison must be non-vacuous"


@pytest.fixture
def extension_store(tmp_path, monkeypatch):
    store = _SyntheticFitStore(tmp_path / "synthetic-extension-fits")
    monkeypatch.setattr(L, "load_fit_evidence", store.load)
    return store


@pytest.mark.parametrize("data_works, model_works, expected", [
    (True, False, 0), (False, True, 1),
    (True, True, "ambiguous"), (False, False, "undiagnosed"),
])
def test_canonical_twenty_seed_extension_label_round_trip(
    tmp_path, extension_store, data_works, model_works, expected,
):
    conditions = _conditions(
        extension_store, _extension_unit(), data_works=data_works, model_works=model_works,
    )
    path = tmp_path / "synthetic-label.json"
    record = L.build_label_evidence(conditions, path=path)
    assert len(extension_store.calls) == 60
    assert record["model_repair_arm"] == EXTENSION
    assert record["label"]["observed_label"] == expected
    assert record["seeds"] == list(confirmatory_seeds(20))
    assert [row["failure_count"] for row in record["failure_masks"]] == [3] * 20
    first_base = extension_store.entries[Path(conditions[0].baseline)]
    assert first_base.roles == ("exp1", REPAIR_STAGE)
    assert first_base.execution_stage == "exp1"
    assert L.load_label_evidence(path) == record
    assert len(extension_store.calls) == 120


@pytest.mark.parametrize("on_reload", [False, True])
def test_extension_requires_equal_encoded_pool_digest_at_creation_and_reload(
    tmp_path, extension_store, on_reload,
):
    conditions = _conditions(
        extension_store, _extension_unit(), data_works=False, model_works=True,
    )
    path = tmp_path / "synthetic-label.json"
    if on_reload:
        L.build_label_evidence(conditions, path=path)
    model_path = Path(conditions[0].model_repair)
    extension_store.entries[model_path] = replace(
        extension_store.entries[model_path], evaluation_pool_digest="f" * 64,
    )
    with pytest.raises(ValueError, match="capacity_extension_repair evaluation_pool_digest"):
        if on_reload:
            L.load_label_evidence(path)
        else:
            L.build_label_evidence(conditions, path=path)


def test_extension_fit_writer_reader_validates_real_persisted_synthetic_sources(tmp_path):
    completed, spec = _completed_run(tmp_path, arm=EXTENSION)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    verified = F.load_fit_evidence(tmp_path, expected_git_commit="b" * 40)
    assert verified.arm == EXTENSION
    assert verified.unit.hidden_size == 256
    assert verified.fit_id == spec.fit_id
    assert verified.roles == (REPAIR_STAGE,)
    assert verified.ensemble_size == 1
    assert tuple(verified.diagnostics) == F._REPAIR_DIAGNOSTICS
    assert "disagreement" not in verified.diagnostics
    assert "predictive_variance" not in verified.diagnostics
    run_record = json.loads((Path(completed.record_dir) / "run.json").read_text())
    assert run_record["effective_unit"]["hidden_size"] == 512
    assert run_record["arm_changed"] == {"hidden_size": 512}
    projected = verified.for_role(REPAIR_STAGE)
    assert projected.config_id == spec.config_id
    assert projected.scale is verified.scale


@pytest.mark.parametrize("boundary", ["writer", "reader"])
@pytest.mark.parametrize("incorrect_width", [256, 1024])
def test_extension_evidence_refuses_a_resigned_wrong_effective_width(
    tmp_path, boundary, incorrect_width,
):
    completed, _ = _completed_run(tmp_path, arm=EXTENSION)

    def mutate(run_record, confirmation):
        run_record["effective_unit"]["hidden_size"] = incorrect_width
        run_record["arm_changed"] = {"hidden_size": incorrect_width}

    if boundary == "reader":
        F.write_fit_evidence(completed, fit_dir=tmp_path)
        _resign_physical_sources(tmp_path, mutate)
        with pytest.raises(ValueError, match="effective_unit|arm_changed"):
            F.load_fit_evidence(tmp_path)
    else:
        completed = _rewrite_unsealed_sources(completed, mutate)
        with pytest.raises(ValueError, match="effective_unit|arm_changed"):
            F.write_fit_evidence(completed, fit_dir=tmp_path)
