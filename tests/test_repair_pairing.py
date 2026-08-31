"""Synthetic anchors/untrained model fixtures only; no real outcomes or labels.

All 225 units x two assigned arms x three seeds receive metadata coverage.
Actual-content checks use three registered representatives (including a
position-withheld feature repair whose object slots genuinely reorder). The
training boundary is replaced explicitly; no optimizer/production fit runs.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Arm, Config, UnitSpec
from bu.env.collect import collect_pools_with_anchors, collect_with_anchors
from bu.env.encoder import ObservationEncoder
from bu.experiments import confirmatory as C
from bu.experiments import fit_evidence as F
from bu.experiments import pool_anchors as A
from bu.experiments import repair_pairing as P
from bu.experiments.enumerate_units import (
    arms_for, canonical_units, design_units, execution_plan, full_matrix, stage_of,
)
from bu.models.ensemble import Ensemble
from bu.models.world_model import WorldModel
from bu.runrecord import GitState
from bu.streams import DATA_PURPOSES, PURPOSES, STREAM_VERSION, stream_key
import bu.runrecord as RR
from fixture_randomness import use_development_input_streams

COMMIT = "b" * 40
SEED = K.CONFIRMATORY_SEED_BASE
DESIGN = design_units()
SWEEP = tuple(u for u in DESIGN if stage_of(u) == "config_sweep")
PLAN = execution_plan(DESIGN)


def _expected(source):
    return dict(baseline_source=source["path"], expected_baseline_commit=COMMIT,
                expected_baseline_execution_digest=source["digest"])


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic-pairing")
    patches = pytest.MonkeyPatch()
    use_development_input_streams(patches)
    state = lambda *a, **kw: GitState(COMMIT, False, "synthetic-test")
    for module in (C, F, RR):
        patches.setattr(module, "git_state", state)
    calls = []

    def untrained(unit, pools, config, *, stage, seed, arm, granularity,
                  logger, epoch_logger, device):
        first = json.loads((Path(logger.run_dir) / "metrics.jsonl").read_text().splitlines()[0])
        assert first["event"] == "pool_anchors" and first["i"] == 0
        calls.append(unit)
        models = tuple(WorldModel(Arm(arm).resolve(unit), np.random.default_rng(i))
                       for i in range(config.ensemble_size))
        for i in range(config.ensemble_size):
            logger.log(record_type="member_summary", member=i, synthetic_untrained=True)
        return Ensemble(unit, Arm(arm).resolve(unit), arm, models, (), granularity)

    patches.setattr(C, "train_ensemble", untrained)
    result = {}
    try:
        for arm in ("capacity_extension_repair", "capacity_repair", "feature_repair"):
            units = [u for u in SWEEP if arm in arms_for(u)]
            if arm == "feature_repair":
                units = [u for u in units if u.withheld_features == ("position",)]
            unit = min(units, key=lambda u: (u.n_transitions, u.hidden_size, Config(unit=u).unit_id))
            path = root / arm
            done = F.run_confirmatory_fit(unit, arm="baseline", seed=SEED,
                                          out_dir=path, expected_git_commit=COMMIT)
            result[arm] = dict(unit=unit, path=path, digest=done.verified.execution_digest)
        result["data_repair"] = result["capacity_extension_repair"]
        assert len(calls) == 3
        yield result
    finally:
        patches.undo()


@pytest.fixture(scope="module")
def examples(sources):
    result = {}
    for arm, source in sources.items():
        contract = P.registered_sweep_pairing(source["unit"], arm=arm, seed=SEED, **_expected(source))
        pools = P.collect_anchored_repair_pools(contract, **_expected(source))
        anchor = F.validate_sweep_pool_anchors(source["path"], expected_git_commit=COMMIT)
        result[arm] = (source, contract, pools, anchor)
    return result


@pytest.mark.parametrize("unit", SWEEP, ids=lambda u: Config(unit=u).unit_id)
def test_metadata_all_225_units_two_arms_three_seeds(unit):
    expected = [f for f in PLAN if f.unit == unit and f.arm != "baseline"]
    assert len(expected) == 6
    for fit in expected:
        seed = SEED + fit.seed
        spec = P.registered_sweep_repair_spec(unit, arm=fit.arm, seed=seed)
        config = Config(unit=unit, arm=Arm(fit.arm), stage="exp3_repairs", seed=seed)
        assert spec.roles == ("exp3_repairs",)
        assert (spec.fit_id, spec.execution_run_id) == (config.fit_id, config.run_id)
        data, model = P._keys(unit, seed)
        assert set(data) == DATA_PURPOSES
        assert set(model) == {"init", "bootstrap", "batch"}
        for purpose, key in data.items():
            assert key == dict(stream_key(unit, "config_sweep", purpose), seed=seed)
            assert key != dict(stream_key(unit, "exp3_repairs", purpose), seed=seed)
        for purpose, key in model.items():
            assert key == dict(stream_key(unit, "exp3_repairs", purpose, member=0), seed=seed)
            assert key == dict(stream_key(unit, "config_sweep", purpose, member=0), seed=seed)
            assert key["unit"] == config.unit_id
        physical = P._physical_ids(spec, "a" * 64)
        assert physical != (config.fit_id, config.run_id)
        assert physical == P._physical_ids(spec, "a" * 64)
        assert physical != P._physical_ids(spec, "c" * 64)


def test_all_8100_legacy_keys_remain_unchanged():
    rows = [[Config(unit=u).unit_id, stage, purpose, stream_key(u, stage, purpose)]
            for u in sorted(DESIGN, key=lambda u: Config(unit=u).unit_id)
            for stage in (stage_of(u), "repair_validation", "exp3_repairs") for purpose in PURPOSES]
    assert STREAM_VERSION == 3 and len(rows) == 8100
    assert hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == (
        "fd97e6c4ca59db074c34f823dc90fd857a5122a97533e7b9a23dcd25878d6d9f")


def test_compact_ids_preserve_typical_deep_windows_path_budget():
    from pathlib import PureWindowsPath
    spec = P.registered_sweep_repair_spec(SWEEP[0], arm="data_repair", seed=SEED)
    fit_id, run_id = P._physical_ids(spec, "a" * 64)
    digest = P._physical_digest(spec, "a" * 64)
    assert fit_id == "ps1-" + digest[:32] and run_id == fit_id + "-r"
    path = (PureWindowsPath("D:/Aenv/pro/pro/week7-confirmatory-2026-08-31-attempt-001-staging")
            / "0123456789abcdef" / "jobs" / fit_id / "attempt-001" / run_id
            / "diagnostics" / "normalised_movement_error.npy")
    assert len(str(path)) < 240  # Leave twenty characters below legacy MAX_PATH.
    assert len(digest) == 64


def test_all_1350_qualified_physical_ids_are_distinct_and_path_independent():
    ids = set()
    for fit in PLAN:
        if fit.unit not in SWEEP or fit.arm == "baseline":
            continue
        spec = P.registered_sweep_repair_spec(fit.unit, arm=fit.arm, seed=SEED + fit.seed)
        physical = P._physical_ids(spec, "a" * 64)
        assert physical not in ids
        ids.add(physical)
    assert len(ids) == 1350


@pytest.mark.parametrize("seed", [True, False, 0, 999, 1003, 1019, 1000.0, "1000", None])
def test_invalid_or_unregistered_seeds_fail_before_source_io(seed, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("source opened before registration"))
    monkeypatch.setattr(F, "validate_sweep_pool_anchors", forbidden)
    with pytest.raises(ValueError):
        P.registered_sweep_pairing(SWEEP[0], arm="data_repair", seed=seed,
                                  baseline_source="absent", expected_baseline_commit=COMMIT,
                                  expected_baseline_execution_digest="a" * 64)
    forbidden.assert_not_called()


def test_canonical_unselected_and_wrong_arm_refused():
    unknown = next(u for u in full_matrix() if u not in DESIGN)
    for unit in (*canonical_units(), unknown):
        with pytest.raises(ValueError):
            P.registered_sweep_repair_spec(unit, arm="data_repair", seed=SEED)
    for arm in ("baseline", "not_an_arm", True, None):
        with pytest.raises(ValueError):
            P.registered_sweep_repair_spec(SWEEP[0], arm=arm, seed=SEED)
    full = next(u for u in SWEEP if not u.withheld_features)
    with pytest.raises(ValueError):
        P.registered_sweep_repair_spec(full, arm="feature_repair", seed=SEED)
    with pytest.raises(ValueError):
        P.registered_sweep_repair_spec(None, arm="data_repair", seed=SEED)


@pytest.mark.parametrize("override", ["stage", "generation_stage", "policy", "n_transitions", "scale", "skip_pairing"])
def test_no_free_override_in_contract_or_collection(override):
    with pytest.raises(TypeError):
        P.registered_sweep_pairing(SWEEP[0], arm="data_repair", seed=SEED, baseline_source="absent",
                                  expected_baseline_commit=COMMIT,
                                  expected_baseline_execution_digest="a" * 64, **{override: None})
    with pytest.raises(TypeError):
        P.collect_anchored_repair_pools(None, baseline_source="absent", expected_baseline_commit=COMMIT,
                                       expected_baseline_execution_digest="a" * 64, **{override: None})


@pytest.mark.parametrize("arm", ["data_repair", "capacity_repair", "capacity_extension_repair", "feature_repair"])
def test_actual_content_contract_and_receipt(examples, arm):
    source, contract, result, anchor = examples[arm]
    doc = contract.as_dict()
    assert doc["generation_stage"] == "config_sweep" and doc["obligation_stage"] == "exp3_repairs"
    assert doc["procedure"] == "baseline_anchored_sweep_v1"
    assert doc["baseline_execution_digest"] == source["digest"]
    assert doc["pool_anchor_sha256"] == anchor.anchor_sha256
    assert doc["physical_identity_sha256"][:32] == contract.physical_fit_id.removeprefix("ps1-")
    assert doc["normalisation"] == anchor.scale.as_row() == result.scale.as_row()
    assert str(source["path"]) not in contract.canonical_json.decode()
    receipt = json.loads(result.compatibility_json)
    assert receipt["contract_sha256"] == contract.contract_sha256
    for pool, inventory in receipt["pools"].items():
        base, repaired = getattr(anchor.pools, pool), getattr(result.pools, pool)
        n = len(base)
        assert len(repaired) == n * (10 if arm == "data_repair" and pool == "train" else 1)
        assert getattr(result.captured, pool)[:n] == getattr(anchor.captured, pool)
        assert repaired.stage == "config_sweep" and repaired.source_unit == source["unit"]
        assert repaired.unit == Arm(arm).resolve(source["unit"])
        assert set(inventory["repair_arrays"]) == {"obs", "next_obs", "action", "episode", "step", "state", "next_state"}
        if arm in ("capacity_repair", "capacity_extension_repair") or (arm == "data_repair" and pool != "train"):
            assert inventory["baseline_arrays"] == inventory["repair_arrays"]
        for name in P._ARRAY_FIELDS:
            # The existing torch converter wraps ordinary writable buffers;
            # safety comes from revalidation, not advisory numpy flags.
            assert getattr(repaired, name).flags.writeable
    # Returned dictionaries are copies, not a mutable hole in the frozen contract.
    doc["model_keys"]["init"]["unit"] = "forged"
    assert contract.as_dict()["model_keys"]["init"]["unit"] != "forged"


def test_feature_slots_really_reorder_not_column_projection(examples):
    source, contract, result, anchor = examples["feature_repair"]
    encoder = ObservationEncoder(source["unit"].n_objects, source["unit"].grid_size)
    columns = [i for b in encoder.blocks if not b.name.endswith("_position") or b.name == "agent_position"
               for i in range(b.start, b.stop)]
    assert not np.array_equal(result.pools.train.obs[:, columns], anchor.pools.train.obs)
    for future, field in ((False, "obs"), (True, "next_obs")):
        np.testing.assert_array_equal(A.reencode_anchors(result.captured.train, source["unit"], next_state=future),
                                      getattr(anchor.pools.train, field))


@pytest.mark.parametrize("field,value", [
    ("procedure", "legacy"), ("pairing_schema_version", True), ("seed", True),
    ("generation_stage", "exp3_repairs"), ("obligation_stage", "config_sweep"),
    ("baseline_commit", "c" * 40), ("baseline_execution_digest", "c" * 64),
    ("pool_anchor_sha256", "c" * 64), ("physical_fit_id", "legacy-fit"),
    ("physical_identity_sha256", "c" * 64),
    ("physical_run_id", "legacy-run"), ("obligation_fit_id", "invented"),
    ("stream_version", 4), ("pool_anchor_schema_version", 2),
])
def test_resigned_contract_forgeries_refused(sources, field, value):
    source = sources["data_repair"]
    contract = P.registered_sweep_pairing(source["unit"], arm="data_repair", seed=SEED, **_expected(source))
    doc = contract.as_dict()
    doc[field] = value
    forged = P.SweepRepairContract(P._json(doc))
    with pytest.raises(ValueError):
        P.validate_pairing_contract(forged, **_expected(source))


@pytest.mark.parametrize("mutation", [
    lambda d: d["data_keys"]["env"].update(group="arbitrary"),
    lambda d: d["model_keys"]["init"].update(member=1),
    lambda d: d["normalisation"].update(scale=[1.0, 1.0]),
    lambda d: d["compatibility_requirement"]["repair_sizes"].update(train=99),
    lambda d: d.update(extra="not registered"),
    lambda d: d.pop("symbolic_capture_version"),
])
def test_nested_resigned_forgery_fails_before_collection(examples, mutation, monkeypatch):
    source, contract, _, _ = examples["data_repair"]
    doc = contract.as_dict()
    mutation(doc)
    forbidden = Mock(side_effect=AssertionError("collection ran on forged contract"))
    monkeypatch.setattr(P, "collect_with_anchors", forbidden)
    with pytest.raises(ValueError):
        P.collect_anchored_repair_pools(P.SweepRepairContract(P._json(doc)), **_expected(source))
    forbidden.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("expected_baseline_commit", "c" * 40), ("expected_baseline_commit", "HEAD"),
    ("expected_baseline_execution_digest", "c" * 64), ("expected_baseline_execution_digest", ""),
])
def test_wrong_independent_expectations_refused(sources, field, value):
    source = sources["data_repair"]
    expected = dict(_expected(source), **{field: value})
    with pytest.raises(ValueError):
        P.registered_sweep_pairing(source["unit"], arm="data_repair", seed=SEED, **expected)


def test_same_commit_wrong_baseline_not_accepted(sources):
    source = sources["data_repair"]
    wrong = sources["feature_repair"]
    with pytest.raises(ValueError, match="baseline identity"):
        P.registered_sweep_pairing(source["unit"], arm="data_repair", seed=SEED, **_expected(wrong))


def test_independent_copy_load_and_exclusive_write_keep_identity(examples, tmp_path):
    source, contract, _, _ = examples["data_repair"]
    copy_path = tmp_path / "independent-copy"
    shutil.copytree(source["path"], copy_path)
    copied = dict(_expected(source), baseline_source=copy_path)
    repeated = P.registered_sweep_pairing(source["unit"], arm="data_repair", seed=SEED, **copied)
    assert repeated == contract
    target = tmp_path / "contract.json"
    assert P.write_pairing_contract(target, contract, **copied) == target
    before = target.stat().st_mtime_ns
    P.write_pairing_contract(target, contract, **copied)
    assert target.stat().st_mtime_ns == before
    loaded = P.load_pairing_contract(target, unit=source["unit"], arm="data_repair", seed=SEED,
                                     expected_contract_sha256=contract.contract_sha256, **copied)
    assert loaded == contract
    with pytest.raises(ValueError):
        P.load_pairing_contract(target, unit=source["unit"], arm="capacity_extension_repair", seed=SEED,
                                expected_contract_sha256=contract.contract_sha256, **copied)
    target.write_bytes(b"preserve divergent partial")
    with pytest.raises(ValueError):
        P.write_pairing_contract(target, contract, **copied)
    assert target.read_bytes() == b"preserve divergent partial"


@pytest.mark.parametrize("artifact", ["pool_anchors.json", "fit_link.json", "train.state.npy"])
def test_source_reopened_and_missing_anchor_never_reconstructed(examples, tmp_path, artifact, monkeypatch):
    source, contract, _, _ = examples["data_repair"]
    path = tmp_path / "source"
    shutil.copytree(source["path"], path)
    (path / A.POOL_ANCHORS_DIRECTORY / artifact).unlink()
    forbidden = Mock(side_effect=AssertionError("collected after source loss"))
    monkeypatch.setattr(P, "collect_with_anchors", forbidden)
    with pytest.raises(ValueError):
        P.collect_anchored_repair_pools(contract, **dict(_expected(source), baseline_source=path))
    forbidden.assert_not_called()


def test_resigned_anchor_substitution_cannot_replace_first_sealed_event(examples, tmp_path):
    source, contract, _, _ = examples["data_repair"]
    path = tmp_path / "source"
    shutil.copytree(source["path"], path)
    manifest = path / A.POOL_ANCHORS_DIRECTORY / A.POOL_ANCHOR_FILE
    document = json.loads(manifest.read_bytes())
    document["identity"]["source_commit"] = "c" * 40
    manifest.write_bytes(A._json(document))
    # Even if the contract and late link both repeat the substitute's checksum,
    # the baseline execution digest independently seals its first metrics event.
    doc = contract.as_dict()
    doc["pool_anchor_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    link = path / A.POOL_ANCHORS_DIRECTORY / A.POOL_ANCHOR_LINK_FILE
    linked = json.loads(link.read_bytes())
    linked["anchor_sha256"] = doc["pool_anchor_sha256"]
    link.write_bytes(A._json(linked))
    with pytest.raises(ValueError):
        P.validate_pairing_contract(P.SweepRepairContract(P._json(doc)),
                                    **dict(_expected(source), baseline_source=path))


@pytest.mark.parametrize("pool,field", [
    (pool, field) for pool in ("train", "validation", "evaluation")
    for field in ("obs", "next_obs", "action", "episode", "step")
])
def test_each_repair_array_checked_exactly(examples, pool, field):
    _, contract, result, anchor = examples["data_repair"]
    captured = copy.deepcopy(result.captured)
    value = getattr(getattr(captured.pools, pool), field)
    value.flags.writeable = True
    value.flat[-1] += 1
    with pytest.raises(ValueError):
        P._compatibility(contract, captured, anchor)


@pytest.mark.parametrize("field,value", [
    ("stage", "exp3_repairs"), ("seed", True), ("arm", "baseline"),
    ("episode_length", 20), ("stream_version", 4), ("pool", "evaluation"),
])
def test_repair_provenance_not_restamped_as_legacy(examples, field, value):
    _, contract, result, anchor = examples["data_repair"]
    train = replace(result.pools.train, **{field: value})
    captured = replace(result.captured, pools=replace(result.pools, train=train))
    with pytest.raises(ValueError):
        P._compatibility(contract, captured, anchor)


def test_latent_full_state_and_prefix_not_only_transition_ids(examples):
    source, contract, result, anchor = examples["data_repair"]
    # A valid internally self-consistent collection on the WRONG legacy streams
    # can be dishonestly restamped. IDs/action counts and even the arm are not
    # sufficient: complete baseline/prefix content must match.
    wrong = collect_pools_with_anchors(source["unit"], stage="exp3_repairs", seed=SEED, arm="data_repair")
    pools = replace(wrong.pools, **{pool: replace(getattr(wrong.pools, pool), stage="config_sweep")
                                  for pool in ("train", "validation", "evaluation")})
    with pytest.raises(ValueError, match="exact baseline trajectory/prefix"):
        P._compatibility(contract, replace(wrong, pools=pools), anchor)
    # Changing only latent object identity also cannot hide behind equal arrays.
    transitions = list(result.captured.train)
    t = transitions[0]
    obj = t.state.objects[0]
    changed = replace(obj, activated=not obj.activated)
    state = replace(t.state, objects=(changed, *t.state.objects[1:]))
    transitions[0] = replace(t, state=state)
    with pytest.raises(ValueError):
        P._compatibility(contract, replace(result.captured, train=tuple(transitions)), anchor)


def test_short_data_repair_or_changed_validation_size_refused(examples):
    _, contract, result, anchor = examples["data_repair"]
    for pool in ("train", "validation", "evaluation"):
        data = getattr(result.pools, pool)
        shortened = replace(data, **{field: getattr(data, field)[:-1] for field in P._ARRAY_FIELDS})
        captured = replace(result.captured, pools=replace(result.pools, **{pool: shortened}),
                           **{pool: getattr(result.captured, pool)[:-1]})
        with pytest.raises(ValueError):
            P._compatibility(contract, captured, anchor)


def test_final_consumer_rechecks_scale_receipt_and_arrays(examples):
    source, _, result, _ = examples["data_repair"]
    assert P.validate_anchored_repair_pools(result, **_expected(source)) is result
    wrong_scale = replace(result.scale, vector=torch.tensor([1.0, 1.0]))
    for altered in (replace(result, scale=wrong_scale), replace(result, compatibility_json=b"{}"), None):
        with pytest.raises(ValueError):
            P.validate_anchored_repair_pools(altered, **_expected(source))


def test_source_reopened_after_collection_and_no_partial_result(examples, tmp_path, monkeypatch):
    source, contract, _, _ = examples["data_repair"]
    path = tmp_path / "copy"
    shutil.copytree(source["path"], path)
    count = []
    def interrupted(*args, **kwargs):
        captured = collect_with_anchors(*args, **kwargs)
        count.append(kwargs["pool"])
        if kwargs["pool"] == "evaluation":
            (path / A.POOL_ANCHORS_DIRECTORY / A.POOL_ANCHOR_LINK_FILE).unlink()
        return captured
    monkeypatch.setattr(P, "collect_with_anchors", interrupted)
    with pytest.raises(ValueError):
        P.collect_anchored_repair_pools(contract, **dict(_expected(source), baseline_source=path))
    assert count == ["train", "validation", "evaluation"]


def test_loader_rejects_resigned_payload_wrong_digest_and_oversize(examples, tmp_path):
    source, contract, _, _ = examples["data_repair"]
    path = tmp_path / "contract.json"
    kwargs = dict(unit=source["unit"], arm="data_repair", seed=SEED, **_expected(source))
    path.write_bytes(contract.canonical_json)
    with pytest.raises(ValueError, match="expected digest"):
        P.load_pairing_contract(path, expected_contract_sha256="0" * 64, **kwargs)
    doc = contract.as_dict()
    doc["data_keys"]["env"]["group"] = "forged"
    raw = P._json(doc)
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="rederived"):
        P.load_pairing_contract(path, expected_contract_sha256=hashlib.sha256(raw).hexdigest(), **kwargs)
    raw = b" " * 32769
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="schema size"):
        P.load_pairing_contract(path, expected_contract_sha256=hashlib.sha256(raw).hexdigest(), **kwargs)


def test_contract_and_qualified_id_never_weaken_legacy_boundaries(examples, tmp_path):
    source, contract, _, _ = examples["data_repair"]
    with pytest.raises(ValueError, match="Wrong pairing"):
        C.run_confirmatory(source["unit"], arm="data_repair", stage="exp3_repairs", seed=SEED,
                           out_dir=tmp_path / "legacy")
    assert not (tmp_path / "legacy").exists()
    with pytest.raises(ValueError):
        C.assert_registered_obligation(source["unit"], arm="data_repair", stage="config_sweep", seed=SEED)
    path = tmp_path / "not-fit-evidence"
    path.mkdir()
    (path / F.FIT_EVIDENCE_FILE).write_bytes(contract.canonical_json)
    with pytest.raises(ValueError):
        F.load_fit_evidence(path, expected_git_commit=COMMIT)
    with pytest.raises(ValueError):
        P.validate_pairing_contract(F.load_fit_evidence(source["path"], expected_git_commit=COMMIT), **_expected(source))


@pytest.mark.parametrize("raw", [b"[]\n", b'{"seed":1000,"seed":1000}\n', b'{"seed":NaN}\n', b"{}", "{}", b"invalid"])
def test_contract_malformed_json_refused(raw):
    with pytest.raises(ValueError):
        P.SweepRepairContract(raw).as_dict()
