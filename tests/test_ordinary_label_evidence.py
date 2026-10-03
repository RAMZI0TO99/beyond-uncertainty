"""Synthetic ordinary-label contract tests; no production payloads or training.

The loader doubles test consumer refusals. The persisted integration fixture
writes full synthetic legacy sidecars and exercises the real strict loader.
Everything is scoped to pytest's project-local temporary directory.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch
from scipy.stats import t

from bu import constants as K
from bu.config import Arm, Config, UnitSpec
from bu.experiments import fit_evidence as F
from bu.experiments import label_evidence as L
from bu.experiments import ordinary_label_evidence as O
from bu.experiments.confirmatory import ConfirmatoryRun
from bu.experiments.enumerate_units import (
    design_units, full_matrix, repair_validation_units, stage_of,
)
from bu.experiments.repair import ArmEvaluation, acceptance_inputs
from bu.models.uncertainty import NormalisationScale
from bu.streams import DATA_PURPOSES, confirmatory_seeds, group_of, stream_key


SEEDS = confirmatory_seeds(K.SEEDS_SWEEP)
CANONICAL = O.canonical_ordinary_units()


def _unit(family="estimation", *, extension=False):
    return next(
        unit for unit in CANONICAL if unit.family == family
        and (family != "capacity" or (unit.hidden_size == 256) == extension)
    )


def _arrays():
    action = np.tile(np.arange(5, dtype=np.int64), 200)
    movement = action != 4
    episode = np.repeat(np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH)[movement]
    step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)[movement]
    error = np.linspace(1.0, 1.2, len(episode), dtype=np.float64)
    error[0] = K.FAILURE_THRESHOLD  # equality is never part of the failure set
    return action, episode, step, error


class _Store:
    def __init__(self, root):
        self.root = root
        self.entries = {}
        self.calls = []
        self.counter = 0

    def add(self, unit, arm, seed, delta=0.0):
        spec = O._spec(unit, arm, seed)
        self.counter += 1
        path = (self.root / f"source-{self.counter:04d}-{spec.fit_id}").resolve()
        path.mkdir(parents=True)
        action, episode, step, error = _arrays()
        error = error + delta
        digest = hashlib.sha256(spec.fit_id.encode() + error.tobytes()).hexdigest()
        pool_kind = "restored" if arm == "feature_repair" else "original"
        pool_digest = hashlib.sha256(f"{spec.unit_id}:{seed}:{pool_kind}".encode()).hexdigest()
        verified = F.VerifiedFitEvidence(
            fit_dir=path, unit=unit, arm=arm, seed=seed, roles=spec.roles,
            execution_stage=spec.execution_stage, unit_id=spec.unit_id,
            config_id=spec.config_id, fit_id=spec.fit_id,
            execution_run_id=spec.execution_run_id, execution_digest=digest,
            evaluation_pool_digest=pool_digest,
            diagnostics={"evaluation_action": action}, error=error, episode=episode, step=step,
            scale=NormalisationScale(torch.ones(2), n_reference=len(error)),
            n_train=Arm(arm).resolve(unit).n_transitions,
            ensemble_size=K.DEFAULT_ENSEMBLE_SIZE if arm == "baseline" else 1,
        )
        commit = ("a" if arm == "baseline" else "b" if arm == "data_repair" else "c") * 40
        self.entries[path] = (verified, commit)
        return O.OrdinaryFitSource(path, commit, digest)

    def load(self, path, *, expected_git_commit):
        path = Path(path).resolve()
        self.calls.append((path, expected_git_commit))
        if path not in self.entries:
            raise ValueError("synthetic partial sidecar")
        verified, commit = self.entries[path]
        if expected_git_commit != commit:
            raise ValueError("recorded execution commit differs from independently expected commit")
        return verified

    def change(self, source, **changes):
        old, commit = self.entries[Path(source.path)]
        self.entries[Path(source.path)] = (replace(old, **changes), commit)


@pytest.fixture
def store(tmp_path, monkeypatch):
    value = _Store(tmp_path / "fits")
    monkeypatch.setattr(O, "load_fit_evidence", value.load)
    return value


def _conditions(store, unit=None, *, data=True, model=False):
    unit = _unit() if unit is None else unit
    _, model_arm = O._registered_unit(unit)
    rows = []
    for i, seed in enumerate(SEEDS):
        variation = (i - 1) * .002
        rows.append(O.OrdinaryRepairCondition(
            store.add(unit, "baseline", seed),
            store.add(unit, "data_repair", seed, (-.35 if data else .02) + variation),
            store.add(unit, model_arm, seed, (-.35 if model else .02) - variation),
        ))
    return tuple(rows)


def _build(store, tmp_path, **kwargs):
    unit = kwargs.pop("unit", _unit())
    conditions = _conditions(store, unit, **kwargs)
    path = tmp_path / O.ORDINARY_LABEL_EVIDENCE_FILE
    record = O.build_ordinary_label_evidence(conditions, unit=unit, path=path)
    return unit, conditions, path, record


def _rewrite(path, record):
    payload = {key: value for key, value in record.items() if key != "record_digest"}
    record["record_digest"] = L._digest(payload)
    path.write_text(json.dumps(record), encoding="utf-8")


def test_eligibility_is_exact_registered_285_not_only_sweep_or_entire_pool():
    eligible = O.ordinary_units()
    assert len(eligible) == 285
    assert len(set(eligible)) == 285
    assert len(CANONICAL) == 60
    assert {u for u in eligible if stage_of(u) == "config_sweep"} == set(design_units()) - set(CANONICAL) - set(repair_validation_units())
    assert not set(eligible) & set(repair_validation_units())
    assert len(full_matrix()) > len(eligible)


@pytest.mark.parametrize("unit", CANONICAL, ids=lambda u: Config(unit=u).unit_id)
def test_every_supported_unit_derives_canonical_role_and_matching_data_keys(unit):
    baseline_stage, model_arm = O._registered_unit(unit)
    assert baseline_stage == stage_of(unit)
    assert baseline_stage in ("exp1", "exp2a", "exp2b")
    assert model_arm in ("feature_repair", "capacity_repair", "capacity_extension_repair")
    for purpose in DATA_PURPOSES:
        assert stream_key(unit, baseline_stage, purpose) == stream_key(unit, O.ORDINARY_STAGE, purpose)


@pytest.mark.parametrize("unit", [u for u in O.ordinary_units() if stage_of(u) == "config_sweep"], ids=lambda u: Config(unit=u).unit_id)
def test_every_sweep_unit_positively_refuses_before_io(unit, tmp_path):
    path = tmp_path / "absent" / "label.json"
    with pytest.raises(ValueError, match="separately verified.*paired"):
        O.build_ordinary_label_evidence((), unit=unit, path=path)
    with pytest.raises(ValueError, match="separately verified.*paired"):
        O.load_ordinary_label_evidence(path, unit=unit, conditions=())
    assert not path.parent.exists()


@pytest.mark.parametrize("unit", repair_validation_units())
def test_twenty_seed_units_can_never_be_downgraded_to_ordinary(unit, tmp_path):
    with pytest.raises(ValueError, match="twenty-seed validation"):
        O.build_ordinary_label_evidence((), unit=unit, path=tmp_path / "label.json")


@pytest.mark.parametrize("unit", [None, {}, UnitSpec(causal_attribute="position", n_transitions=100)])
def test_unknown_unit_refuses(unit, tmp_path):
    if unit in O.ordinary_units():
        unit = next(u for u in full_matrix() if u not in design_units())
    with pytest.raises(ValueError, match="registered ordinary"):
        O.build_ordinary_label_evidence((), unit=unit, path=tmp_path / "label.json")


@pytest.mark.parametrize("data,model,label", [(True, False, 0), (False, True, 1), (True, True, "ambiguous"), (False, False, "undiagnosed")])
def test_all_four_labels_and_nine_reopens_on_creation_and_reload(store, tmp_path, data, model, label):
    unit, rows, path, record = _build(store, tmp_path, data=data, model=model)
    assert record["label"]["observed_label"] == label
    assert len(store.calls) == 9
    assert len(set(store.calls)) == 9
    assert {commit for _, commit in store.calls} == {"a" * 40, "b" * 40, "c" * 40}
    assert O.load_ordinary_label_evidence(path, unit=unit, conditions=rows) == record
    assert store.calls[:9] == store.calls[9:]
    assert record["comparison_group_id"] == group_of(unit, stage_of(unit))
    assert record["seeds"] == list(SEEDS)
    assert all(mask["failure_count"] == 799 for mask in record["failure_masks"])


@pytest.mark.parametrize("unit", [_unit(), _unit("missing_feature"), _unit("capacity"), _unit("capacity", extension=True)])
def test_original_baseline_roles_and_all_three_model_repairs_preserved(store, tmp_path, unit):
    _, rows, path, record = _build(store, tmp_path, unit=unit)
    for row in record["runs"]:
        base = row["baseline"]
        assert base["role"] == stage_of(unit)
        assert base["fit_roles"] == [stage_of(unit)]
        assert base["run_id"] == Config(unit=unit, seed=row["seed"], stage=stage_of(unit)).run_id
        for key in ("data_repair", "model_repair"):
            assert row[key]["fit_roles"] == ["exp3_repairs"]
            assert row[key]["role"] == "exp3_repairs"
        assert "repair_validation" not in str(row)
    assert O.load_ordinary_label_evidence(path, unit=unit, conditions=rows) == record


def test_three_seed_t_interval_and_equal_seed_weighting_match_exact_math(store, tmp_path):
    rows = _conditions(store)
    means, baselines = [], []
    for i, row in enumerate(rows):
        base = store.entries[Path(row.baseline.path)][0]
        error = base.error.copy()
        error[1:1 + 100 * i] = K.FAILURE_THRESHOLD  # different failure counts
        store.change(row.baseline, error=error)
        repaired = store.entries[Path(row.data_repair.path)][0]
        store.change(row.data_repair, error=error + (-.35 + (i - 1) * .002))
        mask = error > K.FAILURE_THRESHOLD
        means.append(float(np.mean(store.entries[Path(row.data_repair.path)][0].error[mask] - error[mask])))
        baselines.append(float(error[mask].mean()))
    record = O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    acceptance = record["acceptance"]["data_repair"]
    effect = np.mean(means)
    half = t.ppf(.975, 2) * np.std(means, ddof=1) / np.sqrt(3)
    assert acceptance["n_seeds"] == 3
    assert acceptance["effect"] == pytest.approx(effect)
    assert acceptance["ci_low"] == pytest.approx(effect - half)
    assert acceptance["ci_high"] == pytest.approx(effect + half)
    assert acceptance["unrepaired_mean"] == pytest.approx(np.mean(baselines))
    assert acceptance["relative_reduction"] == pytest.approx(-effect / np.mean(baselines))


def test_zero_seed_spread_uses_existing_fail_closed_result_without_fallback(store, tmp_path):
    rows = _conditions(store)
    for row in rows:
        base = store.entries[Path(row.baseline.path)][0]
        for source in (row.data_repair, row.model_repair):
            store.change(source, error=base.error.copy())
    record = O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    for result in record["acceptance"].values():
        assert result["passed"] is False
        assert result["converged"] is False
        assert result["effect"] is None
    assert record["label"]["observed_label"] == "undiagnosed"


@pytest.mark.parametrize("count", [0, 1, 2, 4])
def test_missing_and_extra_conditions_never_create_a_label(store, tmp_path, count):
    rows = _conditions(store)
    rows = rows[:count] if count < 3 else rows + rows[:1]
    path = tmp_path / "label.json"
    error = O.OrdinaryLabelPending if count < 3 else ValueError
    with pytest.raises(error, match="conditions"):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=path)
    assert not path.exists()
    assert store.calls == []


def test_missing_source_is_pending_but_partial_source_is_blocked(store, tmp_path):
    rows = _conditions(store)
    source = rows[1].model_repair
    Path(source.path).rmdir()  # empty synthetic fixture directory only
    path = tmp_path / "label.json"
    with pytest.raises(O.OrdinaryLabelPending, match="pending, not observed"):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=path)
    Path(source.path).mkdir()
    del store.entries[Path(source.path)]
    with pytest.raises(ValueError, match="blocked ordinary label") as error:
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=path)
    assert type(error.value) is ValueError
    assert not path.exists()


@pytest.mark.parametrize("field,bad", [("expected_git_commit", None), ("expected_git_commit", "abc"), ("expected_git_commit", "A" * 40), ("expected_execution_digest", "a" * 63), ("expected_execution_digest", False), ("path", None), ("path", " ")])
def test_pin_and_path_validation_is_strict_before_source_io(store, tmp_path, field, bad):
    rows = list(_conditions(store))
    rows[0] = replace(rows[0], baseline=replace(rows[0].baseline, **{field: bad}))
    with pytest.raises(ValueError):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    assert store.calls == []


@pytest.mark.parametrize("field,value", [("expected_git_commit", "d" * 40), ("expected_execution_digest", "d" * 64)])
def test_each_independent_source_pin_is_used(store, tmp_path, field, value):
    rows = list(_conditions(store))
    rows[1] = replace(rows[1], model_repair=replace(rows[1].model_repair, **{field: value}))
    with pytest.raises(ValueError, match="expected"):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("field,value", [("seed", 999), ("seed", 1003), ("seed", 1000.0), ("seed", True), ("roles", ("pilot",)), ("roles", ("exp1", "exp3_repairs")), ("execution_stage", "exp3_repairs"), ("unit_id", "0" * 12), ("fit_id", "substituted"), ("config_id", "0" * 12), ("execution_run_id", "substituted"), ("ensemble_size", 1), ("n_train", 42), ("arm", "data_repair")])
def test_reloaded_metadata_cannot_substitute_seed_roles_identity_or_procedure(store, tmp_path, field, value):
    rows = _conditions(store)
    store.change(rows[0].baseline, **{field: value})
    with pytest.raises(ValueError):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("slot", ["data_repair", "model_repair"])
def test_repaired_ensembles_are_single_model_and_mixed_seeds_refused(store, tmp_path, slot):
    rows = list(_conditions(store))
    store.change(getattr(rows[0], slot), ensemble_size=5)
    with pytest.raises(ValueError, match="ensemble_size"):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    store.change(getattr(rows[0], slot), ensemble_size=1)
    first, second = getattr(rows[0], slot), getattr(rows[1], slot)
    rows[0] = replace(rows[0], **{slot: second})
    rows[1] = replace(rows[1], **{slot: first})
    with pytest.raises(ValueError, match="same seed"):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


def test_duplicate_sources_and_duplicate_seeds_even_under_distinct_copy_paths_refuse(store, tmp_path):
    rows = _conditions(store)
    with pytest.raises(ValueError, match="duplicate physical source"):
        O.build_ordinary_label_evidence((rows[0], rows[0], rows[2]), unit=_unit(), path=tmp_path / "label.json")
    duplicate = _conditions(store)[0]  # distinct paths, same physical fit IDs
    with pytest.raises(ValueError, match="duplicates/missing"):
        O.build_ordinary_label_evidence((rows[0], duplicate, rows[2]), unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("mutation", ["scale", "pool", "action", "episode", "step", "empty", "nan", "negative", "shape"])
def test_pool_scale_inventory_and_failure_set_refusals(store, tmp_path, mutation):
    rows = _conditions(store)
    source = rows[0].data_repair
    fit = store.entries[Path(source.path)][0]
    if mutation == "scale":
        store.change(source, scale=NormalisationScale(torch.ones(2) * 2, n_reference=len(fit.error)))
    elif mutation == "pool":
        store.change(source, evaluation_pool_digest="f" * 64)
    elif mutation == "action":
        action = fit.diagnostics["evaluation_action"].copy()
        action[0] = 1  # changes action without changing movement mask
        store.change(source, diagnostics={"evaluation_action": action})
    elif mutation in ("episode", "step"):
        array = getattr(fit, mutation).copy()
        array[0] += 1
        store.change(source, **{mutation: array})
    else:
        source = rows[0].baseline
        base = store.entries[Path(source.path)][0]
        error = base.error.copy()
        if mutation == "empty":
            error[:] = K.FAILURE_THRESHOLD
        elif mutation == "nan":
            error[0] = np.nan
        elif mutation == "negative":
            error[0] = -1
        else:
            error = error[:, None]
        store.change(source, error=error)
    with pytest.raises(ValueError):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    assert not (tmp_path / "label.json").exists()


def test_feature_repair_cannot_claim_unchanged_encoded_pool(store, tmp_path):
    unit = _unit("missing_feature")
    rows = _conditions(store, unit)
    base = store.entries[Path(rows[0].baseline.path)][0]
    store.change(rows[0].model_repair, evaluation_pool_digest=base.evaluation_pool_digest)
    with pytest.raises(ValueError, match="feature repair must change"):
        O.build_ordinary_label_evidence(rows, unit=unit, path=tmp_path / "label.json")


@pytest.mark.parametrize("mutation", ["extra", "missing", "schema", "stage", "baseline_role", "seeds", "mask", "acceptance", "boolean_label", "float_seed", "float_count", "path", "digest", "commit", "label"])
def test_resigned_label_metadata_forgery_cannot_supply_its_own_sources(store, tmp_path, mutation):
    unit, rows, path, record = _build(store, tmp_path)
    if mutation == "extra":
        record["extra"] = True
    elif mutation == "missing":
        del record["procedure"]
    elif mutation == "schema":
        record["ordinary_label_evidence_schema_version"] = 2
    elif mutation == "stage":
        record["stage"] = "repair_validation"
    elif mutation == "baseline_role":
        record["runs"][0]["baseline"]["role"] = "exp3_repairs"
    elif mutation == "seeds":
        record["seeds"] = [1000, 1001, 1003]
    elif mutation == "mask":
        record["failure_masks"][0]["failure_count"] += 1
    elif mutation == "acceptance":
        record["acceptance"]["data_repair"]["effect"] += .01
    elif mutation == "boolean_label":
        record["label"]["observed_label"] = False
    elif mutation == "float_seed":
        record["runs"][0]["seed"] = 1000.0
    elif mutation == "float_count":
        record["acceptance"]["data_repair"]["n_seeds"] = 3.0
    elif mutation == "path":
        record["runs"][0]["baseline"]["fit_evidence_path"] = "../outside"
    elif mutation == "digest":
        record["runs"][0]["baseline"]["fit_evidence_digest"] = "d" * 64
    elif mutation == "commit":
        record["runs"][0]["baseline"]["expected_git_commit"] = "d" * 40
    else:
        record["label"]["observed_label"] = 1
    _rewrite(path, record)
    with pytest.raises(ValueError, match="does not exactly match"):
        O.load_ordinary_label_evidence(path, unit=unit, conditions=rows)
    assert len(store.calls) == 18  # reopens trusted pins, not the forged path


def test_source_changes_and_missing_sources_are_rechecked_on_reload(store, tmp_path):
    unit, rows, path, _ = _build(store, tmp_path)
    source = rows[-1].model_repair
    store.change(source, execution_digest="d" * 64)
    with pytest.raises(ValueError, match="execution digest"):
        O.load_ordinary_label_evidence(path, unit=unit, conditions=rows)
    Path(source.path).rmdir()
    with pytest.raises(O.OrdinaryLabelPending):
        O.load_ordinary_label_evidence(path, unit=unit, conditions=rows)


def test_returned_record_is_not_trusted_and_conflicting_write_is_immutable(store, tmp_path):
    unit, rows, path, record = _build(store, tmp_path)
    before = path.read_bytes()
    record["label"]["observed_label"] = 1
    assert O.load_ordinary_label_evidence(path, unit=unit, conditions=rows)["label"]["observed_label"] == 0
    other = _conditions(store, unit, data=False, model=True)
    with pytest.raises(ValueError, match="overwrite immutable"):
        O.build_ordinary_label_evidence(other, unit=unit, path=path)
    assert path.read_bytes() == before


def test_creation_order_is_irrelevant_and_evidence_tree_is_portable(store, tmp_path):
    unit, rows, path, record = _build(store, tmp_path)
    assert O.build_ordinary_label_evidence(tuple(reversed(rows)), unit=unit, path=path) == record
    relocated = tmp_path / "relocated"
    relocated.mkdir()
    shutil.copy2(path, relocated / path.name)
    new_rows = []
    for row in rows:
        changes = {}
        for slot in ("baseline", "data_repair", "model_repair"):
            source = getattr(row, slot)
            new_path = relocated / Path(source.path).relative_to(tmp_path)
            new_path.mkdir(parents=True)
            verified, commit = store.entries[Path(source.path)]
            store.entries[new_path] = (replace(verified, fit_dir=new_path), commit)
            changes[slot] = replace(source, path=new_path)
        new_rows.append(O.OrdinaryRepairCondition(**changes))
    assert O.load_ordinary_label_evidence(relocated / path.name, unit=unit, conditions=new_rows) == record


def test_outside_tree_and_in_memory_source_refusals(store, tmp_path):
    rows = _conditions(store)
    with pytest.raises(ValueError, match="outside label evidence tree"):
        O.build_ordinary_label_evidence(rows, unit=_unit(), path=tmp_path / "nested" / "label.json")
    verified = store.entries[Path(rows[0].baseline.path)][0]
    malformed = (replace(rows[0], baseline=verified),) + rows[1:]
    with pytest.raises(ValueError, match="exact OrdinaryFitSource"):
        O.build_ordinary_label_evidence(malformed, unit=_unit(), path=tmp_path / "label.json")


def test_existing_twenty_seed_api_and_public_stage_guard_are_unchanged(store, tmp_path):
    unit, rows, path, record = _build(store, tmp_path)
    old_conditions = tuple(L.PersistedRepairCondition(row.baseline.path, row.data_repair.path, row.model_repair.path) for row in rows)
    with pytest.raises(ValueError, match="exactly 20"):
        L.build_label_evidence(old_conditions, path=tmp_path / "old-label.json")
    with pytest.raises(ValueError, match="exact schema"):
        L.load_label_evidence(path)
    base = [store.entries[Path(row.baseline.path)][0].for_role(stage_of(unit)) for row in rows]
    data = [store.entries[Path(row.data_repair.path)][0].for_role(O.ORDINARY_STAGE) for row in rows]
    with pytest.raises(ValueError, match="mixed stages"):
        acceptance_inputs(base, data, failure_masks={seed: np.ones(800, dtype=bool) for seed in SEEDS})
    assert record["ordinary_label_evidence_schema_version"] == 1
    with pytest.raises(TypeError):
        O.load_ordinary_label_evidence(path)  # independent unit/source inventory required


def _persist_synthetic_fit(root, unit, arm, seed, delta):
    """Seal a full fabricated physical fit with the real evidence writer."""
    spec = O._spec(unit, arm, seed)
    config = Config(
        unit=unit, arm=Arm(arm), seed=seed, stage=spec.execution_stage,
        train=F.CONFIRMATORY_TRAIN if arm == "baseline" else F.REPAIRED_TRAIN,
    )
    record_dir = root / config.run_id
    record_dir.mkdir(parents=True)
    threading = {"num_threads": F.CONFIRMATORY_THREADS, "num_interop_threads": F.CONFIRMATORY_INTEROP_THREADS}
    commit = ("a" if arm == "baseline" else "b" if arm == "data_repair" else "c") * 40
    pool = hashlib.sha256(f"{spec.unit_id}:{seed}:{arm == 'feature_repair'}".encode()).hexdigest()
    role_ids = {role: spec.run_id_for(role) for role in spec.roles}
    effective = Config(unit=config.effective_unit).to_dict()["unit"]
    original = config.to_dict()["unit"]
    record = {
        "run_id": config.run_id, "config_id": config.config_id, "unit_id": config.unit_id,
        "fit_id": config.fit_id, "seed": seed, "stage": config.stage,
        "seed_partition": "confirmatory", "confirmatory": True,
        "schema_version": F.SCHEMA_VERSION, "identity_version": F.IDENTITY_VERSION,
        "unit_identity_fields": list(F.UNIT_IDENTITY_FIELDS),
        "started_utc": "2026-08-31T00:00:00+00:00", "config": config.to_dict(),
        "effective_unit": effective,
        "arm_changed": {key: value for key, value in effective.items() if original[key] != value},
        "git": {"commit": commit, "branch": "synthetic", "dirty": False, "trustworthy": True},
        "env": {"python": "3.13.5", "platform": "synthetic-test-platform", "packages": dict(F._FROZEN_PACKAGE_VERSIONS)},
        "extra": {
            "granularity": "episode", "seed_partition": "confirmatory",
            "evaluation_pool_digest": pool, "threading": threading,
            "device": F.CONFIRMATORY_DEVICE, "fit_roles": list(spec.roles), "role_run_ids": role_ids,
        },
    }
    run_bytes = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()
    metrics_bytes = b'{"i":0,"record_type":"member","member":0}\n'
    (record_dir / "run.json").write_bytes(run_bytes)
    (record_dir / "metrics.jsonl").write_bytes(metrics_bytes)
    action, episode, step, error = _arrays()
    error = error + delta
    scale = NormalisationScale(torch.ones(2), n_reference=len(error))
    diagnostics = {
        "evaluation_action": action, "episode": episode, "step": step, "error": error,
        "scale": np.ones(2, dtype=np.float64), "scale_n_reference": np.asarray(len(error)),
        "scale_domain": np.asarray(scale.domain), "scale_source": np.asarray(scale.source),
    }
    mean_disagreement = None
    mean_variance = None
    if arm == "baseline":
        diagnostics["disagreement"] = np.linspace(.2, .8, len(error))
        diagnostics["predictive_variance"] = np.linspace(.1, .4, len(error))
        mean_disagreement = float(diagnostics["disagreement"].mean())
        mean_variance = float(diagnostics["predictive_variance"].mean())
    confirmation = {
        "config": config.to_dict(), "run_id": config.run_id, "config_id": config.config_id,
        "unit_id": config.unit_id, "fit_id": config.fit_id, "seed": seed, "arm": arm,
        "stage": config.stage, "seed_partition": "confirmatory", "granularity": "episode",
        "member_count": config.train.ensemble_size,
        "member_indices": list(range(config.train.ensemble_size)),
        "member_record_digest": hashlib.sha256(metrics_bytes).hexdigest(),
        "run_record_digest": hashlib.sha256(run_bytes).hexdigest(),
        "evaluation_pool_digest": pool, "normalisation": scale.as_row(),
        "metric_schema_version": F.METRIC_SCHEMA_VERSION, "threading": threading,
        "device": F.CONFIRMATORY_DEVICE, "fit_roles": list(spec.roles), "role_run_ids": role_ids,
        "n_train": config.effective_unit.n_transitions, "mean_error": float(error.mean()),
        "mean_disagreement": mean_disagreement, "mean_predictive_variance": mean_variance,
        "ratio": mean_disagreement / float(error.mean()) if mean_disagreement is not None else None,
    }
    (record_dir / "confirmatory.json").write_text(json.dumps(confirmation, sort_keys=True), encoding="utf-8")
    evaluation = ArmEvaluation(
        arm=arm, seed=seed, error=error, episode=episode, step=step, scale=scale,
        config_id=config.config_id, run_id=config.run_id, n_train=config.effective_unit.n_transitions,
        stage=config.stage, ensemble_size=config.train.ensemble_size,
    )
    completed = ConfirmatoryRun(
        run_id=config.run_id, config_id=config.config_id, unit_id=config.unit_id,
        fit_id=config.fit_id, stage=config.stage, arm=arm, seed=seed,
        n_train=config.effective_unit.n_transitions, member_count=config.train.ensemble_size,
        mean_disagreement=mean_disagreement if mean_disagreement is not None else float("nan"),
        record_dir=record_dir, run=confirmation, evaluation=evaluation, diagnostics=diagnostics,
    )
    sidecar = F.write_fit_evidence(completed, fit_dir=root)
    digest = json.loads(sidecar.read_text())["execution_digest"]
    return O.OrdinaryFitSource(root, commit, digest)


@pytest.mark.parametrize("unit", [_unit(), _unit("missing_feature"), _unit("capacity")])
def test_real_sidecars_reload_all_nine_with_distinct_execution_commits(tmp_path, monkeypatch, unit):
    """No mocked writer/verifier: every artifact inventory is actually checked."""
    _, model_arm = O._registered_unit(unit)
    rows = []
    for i, seed in enumerate(SEEDS):
        sources = []
        for arm, delta in (("baseline", 0), ("data_repair", -.35 + (i - 1) * .002), (model_arm, .02 - (i - 1) * .002)):
            sources.append(_persist_synthetic_fit(tmp_path / f"{arm}-{seed}", unit, arm, seed, delta))
        rows.append(O.OrdinaryRepairCondition(*sources))
    calls = []

    def spy(path, *, expected_git_commit):
        calls.append((path, expected_git_commit))
        return F.load_fit_evidence(path, expected_git_commit=expected_git_commit)

    monkeypatch.setattr(O, "load_fit_evidence", spy)
    path = tmp_path / "label.json"
    record = O.build_ordinary_label_evidence(rows, unit=unit, path=path)
    assert record["label"]["observed_label"] == 0
    assert len(calls) == 9
    assert O.load_ordinary_label_evidence(path, unit=unit, conditions=rows) == record
    assert len(calls) == 18
    wrong = list(rows)
    wrong[1] = replace(wrong[1], model_repair=replace(wrong[1].model_repair, expected_git_commit="b" * 40))
    with pytest.raises(ValueError, match="Git commit"):
        O.load_ordinary_label_evidence(path, unit=unit, conditions=wrong)
    assert json.loads(path.read_text()) == record
    # Tamper the final source's immutable diagnostic without resigning it.
    diagnostic = Path(rows[-1].model_repair.path) / "evaluation" / "error.npy"
    assert diagnostic.is_file()
    diagnostic.write_bytes(diagnostic.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="bytes do not match"):
        O.load_ordinary_label_evidence(path, unit=unit, conditions=rows)
