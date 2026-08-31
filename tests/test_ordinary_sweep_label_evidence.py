"""Synthetic sweep-label boundaries; no real outcomes or model optimisation.

Fast tests use strict typed reader doubles. The integration test uses real
anchored collectors/sidecars with explicitly untrained synthetic models.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
import torch
from scipy.stats import t

from bu import constants as K
from bu.config import Arm, Config
from bu.experiments import fit_evidence as F
from bu.experiments import label_evidence as L
from bu.experiments import ordinary_label_evidence as O
from bu.experiments import ordinary_sweep_label_evidence as S
from bu.experiments import paired_repair_evidence as E
from bu.experiments import repair_pairing as RP
from bu.experiments.enumerate_units import canonical_units, design_units, full_matrix
from bu.models.uncertainty import NormalisationScale
from bu.streams import group_of


SEEDS = (1000, 1001, 1002)
SWEEP = S.sweep_ordinary_units()


@lru_cache(maxsize=None)
def _unit(arm="capacity_repair"):
    return next(unit for unit in SWEEP if S._registered_unit(unit) == arm)


def _diagnostics(delta=0):
    action = np.tile(np.arange(5, dtype=np.int64), 200)
    move = action != 4
    episode = np.repeat(np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH)[move]
    step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)[move]
    error = np.linspace(1, 1.2, len(episode))
    error[0] = K.FAILURE_THRESHOLD
    vector = np.asarray([np.float32(.12345679), np.float32(.31415927)], dtype=np.float64)
    scale = NormalisationScale(torch.from_numpy(vector.copy()), len(error))
    return {
        "error": error + delta, "evaluation_action": action, "episode": episode, "step": step,
        "scale": vector, "scale_n_reference": np.asarray(len(error), dtype=np.int64),
        "scale_domain": np.asarray(scale.domain), "scale_source": np.asarray(scale.source),
    }, scale


class _Store:
    def __init__(self, root):
        self.root = root
        self.entries = {}
        self.calls = []
        self.counter = 0

    def add_baseline(self, unit, seed):
        spec = S._baseline_spec(unit, seed)
        self.counter += 1
        path = (self.root / f"base-{self.counter}-{seed}").resolve()
        path.mkdir(parents=True)
        diagnostics, scale = _diagnostics()
        digest = hashlib.sha256(f"baseline:{spec.fit_id}".encode()).hexdigest()
        verified = F.VerifiedFitEvidence(
            path, unit, "baseline", seed, spec.roles, spec.execution_stage, spec.unit_id,
            spec.config_id, spec.fit_id, spec.execution_run_id, digest, "a" * 64,
            diagnostics, diagnostics["error"], diagnostics["episode"], diagnostics["step"],
            scale, unit.n_transitions, K.DEFAULT_ENSEMBLE_SIZE,
        )
        self.entries[path] = (verified, "a" * 40)
        return S.SweepBaselineSource(path, "a" * 40, digest)

    def add_paired(self, unit, arm, seed, baseline, delta):
        spec = RP.registered_sweep_repair_spec(unit, arm=arm, seed=seed)
        self.counter += 1
        path = (self.root / f"paired-{self.counter}-{seed}").resolve()
        path.mkdir(parents=True)
        base = self.entries[Path(baseline.path)][0]
        physical_fit, physical_run = RP._physical_ids(spec, baseline.expected_execution_digest)
        diagnostics, scale = _diagnostics(delta)
        doc = {
            "pairing_schema_version": RP.PAIRING_SCHEMA_VERSION, "procedure": RP.PAIRING_PROCEDURE,
            "unit": L._unit_row(unit), "unit_id": Config(unit=unit).unit_id,
            "arm": arm, "seed": seed, "config_id": spec.config_id,
            "generation_stage": "config_sweep", "obligation_stage": "exp3_repairs",
            "physical_fit_id": physical_fit, "physical_run_id": physical_run,
            "obligation_fit_id": spec.fit_id, "obligation_run_id": spec.execution_run_id,
            "physical_identity_sha256": RP._physical_digest(spec, baseline.expected_execution_digest),
            "baseline_fit_id": base.fit_id, "baseline_run_id": base.execution_run_id,
            "baseline_commit": baseline.expected_git_commit,
            "baseline_execution_digest": baseline.expected_execution_digest,
            "normalisation": scale.as_row(),
        }
        digest = hashlib.sha256(physical_fit.encode() + diagnostics["error"].tobytes()).hexdigest()
        verified = E.VerifiedPairedRepair(
            path, unit, arm, seed, physical_fit, physical_run, spec.fit_id, spec.execution_run_id,
            spec.config_id, digest, RP.SweepRepairContract(RP._json(doc)), diagnostics, scale,
            Arm(arm).resolve(unit).n_transitions,
        )
        commit = ("b" if arm == "data_repair" else "c") * 40
        self.entries[path] = (verified, commit)
        return S.PairedRepairSource(path, commit, digest)

    def load_baseline(self, path, *, expected_git_commit):
        path = Path(path).resolve()
        self.calls.append(("baseline", path, {"expected_git_commit": expected_git_commit}))
        if path not in self.entries:
            raise ValueError("synthetic partial baseline")
        verified, commit = self.entries[path]
        if commit != expected_git_commit:
            raise ValueError("wrong independently expected baseline commit")
        return verified

    def load_paired(self, path, **kwargs):
        path = Path(path).resolve()
        self.calls.append(("paired", path, kwargs))
        if path not in self.entries:
            raise ValueError("synthetic partial paired source")
        verified, commit = self.entries[path]
        if commit != kwargs["expected_git_commit"]:
            raise ValueError("wrong independently expected repair commit")
        if type(verified) is E.VerifiedPairedRepair:
            doc = verified.contract.as_dict()
            baseline = self.entries[Path(kwargs["baseline_source"])][0]
            if (baseline.execution_digest != kwargs["expected_baseline_execution_digest"]
                    or doc["baseline_execution_digest"] != kwargs["expected_baseline_execution_digest"]
                    or doc["baseline_commit"] != kwargs["expected_baseline_commit"]):
                raise ValueError("paired evidence is bound to a different baseline")
        return verified

    def change(self, source, **changes):
        verified, commit = self.entries[Path(source.path)]
        self.entries[Path(source.path)] = (replace(verified, **changes), commit)


@pytest.fixture
def store(tmp_path, monkeypatch):
    value = _Store(tmp_path / "sources")
    monkeypatch.setattr(F, "load_fit_evidence", value.load_baseline)
    monkeypatch.setattr(E, "load_paired_repair_evidence", value.load_paired)
    return value


def _conditions(store, unit=None, data=True, model=False):
    unit = _unit() if unit is None else unit
    model_arm = S._registered_unit(unit)
    rows = []
    for i, seed in enumerate(SEEDS):
        base = store.add_baseline(unit, seed)
        rows.append(S.SweepRepairCondition(
            base,
            store.add_paired(unit, "data_repair", seed, base, (-.35 if data else .02) + (i - 1) * .002),
            store.add_paired(unit, model_arm, seed, base, (-.35 if model else .02) - (i - 1) * .002),
        ))
    return tuple(rows)


def _build(store, tmp_path, *, unit=None, **kwargs):
    unit = _unit() if unit is None else unit
    rows = _conditions(store, unit, **kwargs)
    path = tmp_path / S.ORDINARY_SWEEP_LABEL_EVIDENCE_FILE
    record = S.build_ordinary_sweep_label_evidence(rows, unit=unit, path=path)
    return unit, rows, path, record


def _rewrite(path, record):
    record["record_digest"] = L._digest({key: value for key, value in record.items() if key != "record_digest"})
    path.write_text(json.dumps(record), encoding="utf-8")


def test_exact_225_registry_and_no_canonical_or_unselected_pool_units():
    assert len(SWEEP) == 225
    assert len(set(SWEEP)) == 225
    assert set(SWEEP) == set(design_units()) - set(canonical_units())
    assert not set(SWEEP) & set(O.canonical_ordinary_units())


@pytest.mark.parametrize("unit", SWEEP, ids=lambda u: Config(unit=u).unit_id)
def test_all_225_have_exact_assigned_repair_and_three_registered_seeds(unit):
    model_arm = S._registered_unit(unit)
    assert model_arm in ("feature_repair", "capacity_repair", "capacity_extension_repair")
    for seed in S._seeds():
        for arm in ("data_repair", model_arm):
            spec = RP.registered_sweep_repair_spec(unit, arm=arm, seed=seed)
            assert spec.roles == ("exp3_repairs",)


@pytest.mark.parametrize("unit", [None, *canonical_units(), next(u for u in full_matrix() if u not in design_units())])
def test_all_canonical_validation_and_non_design_units_refuse_before_io(unit, tmp_path):
    with pytest.raises(ValueError, match="registered sweep-only"):
        S.build_ordinary_sweep_label_evidence((), unit=unit, path=tmp_path / "label.json")
    with pytest.raises(ValueError, match="registered sweep-only"):
        S.load_ordinary_sweep_label_evidence(tmp_path / "label.json", unit=unit, conditions=())


@pytest.mark.parametrize("data,model,label", [(True, False, 0), (False, True, 1), (True, True, "ambiguous"), (False, False, "undiagnosed")])
def test_four_labels_reopen_nine_and_pin_same_condition_baseline(store, tmp_path, data, model, label):
    unit, rows, path, record = _build(store, tmp_path, data=data, model=model)
    assert record["label"]["observed_label"] == label
    assert record["comparison_group_id"] == group_of(unit, "config_sweep")
    assert len(store.calls) == 9
    for i, row in enumerate(rows):
        for call in store.calls[i * 3 + 1:i * 3 + 3]:
            kwargs = call[2]
            assert kwargs["baseline_source"] == Path(row.baseline.path)
            assert kwargs["expected_baseline_commit"] == row.baseline.expected_git_commit
            assert kwargs["expected_baseline_execution_digest"] == row.baseline.expected_execution_digest
            assert kwargs["seed"] == SEEDS[i]
    assert S.load_ordinary_sweep_label_evidence(path, unit=unit, conditions=rows) == record
    assert store.calls[:9] == store.calls[9:]
    assert all(row["failure_count"] == 799 for row in record["failure_masks"])


@pytest.mark.parametrize("arm", ["capacity_repair", "capacity_extension_repair", "feature_repair"])
def test_identity_kinds_are_explicit_and_no_legacy_role_is_fabricated(store, tmp_path, arm):
    unit, rows, path, record = _build(store, tmp_path, unit=_unit(arm))
    assert record["model_repair_arm"] == arm
    for row in record["runs"]:
        base = row["baseline"]
        assert base["source_kind"] == "legacy_sweep_baseline"
        assert base["fit_roles"] == ["config_sweep"]
        assert base["physical_fit_id"] == base["obligation_fit_id"]
        for slot in ("data_repair", "model_repair"):
            repair = row[slot]
            assert repair["source_kind"] == "baseline_anchored_paired_repair"
            assert repair["physical_fit_id"] != repair["obligation_fit_id"]
            assert repair["physical_run_id"] != repair["obligation_run_id"]
            assert repair["generation_stage"] == "config_sweep"
            assert repair["obligation_stage"] == "exp3_repairs"
            assert "run_id" not in repair and "fit_roles" not in repair and "execution_stage" not in repair
    assert S.load_ordinary_sweep_label_evidence(path, unit=unit, conditions=rows) == record


def test_actual_full_pool_scale_values_are_preserved_not_rounded_or_subset_derived(store, tmp_path):
    _, _, _, record = _build(store, tmp_path)
    raw, _ = _diagnostics()
    for row in record["runs"]:
        assert row["normalisation"]["scale"] == raw["scale"].tolist()
        assert row["normalisation"]["scale_n_reference"] == 800
    assert record["failure_masks"][0]["failure_count"] == 799


def test_sub_float32_actual_scale_drift_cannot_hide_behind_equal_scale_objects(store, tmp_path):
    rows = _conditions(store)
    source = rows[0].model_repair
    fit = store.entries[Path(source.path)][0]
    diagnostics = dict(fit.diagnostics)
    diagnostics["scale"] = fit.diagnostics["scale"].copy()
    diagnostics["scale"][0] += 1e-12
    assert np.array_equal(diagnostics["scale"].astype("float32"), fit.diagnostics["scale"].astype("float32"))
    store.change(source, diagnostics=diagnostics)
    with pytest.raises(ValueError, match="actual diagnostic scale"):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


def test_equal_seed_t_interval_uses_exact_existing_math(store, tmp_path):
    rows = _conditions(store)
    differences, means = [], []
    for i, row in enumerate(rows):
        base = store.entries[Path(row.baseline.path)][0]
        error = base.error.copy()
        error[1:1 + 100 * i] = K.FAILURE_THRESHOLD
        diagnostic = dict(base.diagnostics, error=error)
        store.change(row.baseline, error=error, diagnostics=diagnostic)
        rep = store.entries[Path(row.data_repair.path)][0]
        delta = -.35 + (i - 1) * .002
        store.change(row.data_repair, diagnostics=dict(rep.diagnostics, error=error + delta))
        mask = error > K.FAILURE_THRESHOLD
        differences.append(float(np.mean((error + delta)[mask] - error[mask])))
        means.append(float(error[mask].mean()))
    record = S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    result = record["acceptance"]["data_repair"]
    effect = np.mean(differences)
    half = t.ppf(.975, 2) * np.std(differences, ddof=1) / np.sqrt(3)
    assert result["n_seeds"] == 3
    assert result["effect"] == pytest.approx(effect)
    assert result["ci_low"] == pytest.approx(effect - half)
    assert result["ci_high"] == pytest.approx(effect + half)
    assert result["unrepaired_mean"] == pytest.approx(np.mean(means))
    assert result["relative_reduction"] == pytest.approx(-effect / np.mean(means))


@pytest.mark.parametrize("count", [0, 1, 2, 4])
def test_missing_or_extra_conditions_never_create_labels(store, tmp_path, count):
    rows = _conditions(store)
    rows = rows[:count] if count < 3 else rows + rows[:1]
    expected = S.SweepLabelPending if count < 3 else ValueError
    with pytest.raises(expected):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    assert store.calls == []
    assert not (tmp_path / "label.json").exists()


@pytest.mark.parametrize("slot", ["baseline", "data_repair", "model_repair"])
def test_absent_is_pending_partial_is_blocked_and_reload_rechecks(store, tmp_path, slot):
    unit, rows, path, record = _build(store, tmp_path)
    source = getattr(rows[-1], slot)
    Path(source.path).rmdir()
    with pytest.raises(S.SweepLabelPending):
        S.load_ordinary_sweep_label_evidence(path, unit=unit, conditions=rows)
    Path(source.path).mkdir()
    del store.entries[Path(source.path)]
    with pytest.raises(ValueError, match="blocked sweep label") as error:
        S.load_ordinary_sweep_label_evidence(path, unit=unit, conditions=rows)
    assert type(error.value) is ValueError
    assert json.loads(path.read_text()) == record


@pytest.mark.parametrize("slot", ["baseline", "data_repair", "model_repair"])
@pytest.mark.parametrize("field,value", [("expected_git_commit", "d" * 40), ("expected_execution_digest", "d" * 64)])
def test_independent_commits_and_execution_digests_are_pinned_for_every_source_kind(store, tmp_path, slot, field, value):
    rows = list(_conditions(store))
    rows[1] = replace(rows[1], **{slot: replace(getattr(rows[1], slot), **{field: value})})
    with pytest.raises(ValueError):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("slot", ["baseline", "data_repair", "model_repair"])
def test_baseline_and_paired_pin_types_cannot_be_swapped(store, tmp_path, slot):
    rows = list(_conditions(store))
    source = getattr(rows[0], slot)
    kind = S.PairedRepairSource if slot == "baseline" else S.SweepBaselineSource
    rows[0] = replace(rows[0], **{slot: kind(source.path, source.expected_git_commit, source.expected_execution_digest)})
    with pytest.raises(ValueError, match="source kinds cannot be exchanged"):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    assert store.calls == []


@pytest.mark.parametrize("slot,file", [("baseline", E.PAIRED_FIT_FILE), ("data_repair", F.FIT_EVIDENCE_FILE)])
def test_opposite_schema_on_disk_is_refused(store, tmp_path, slot, file):
    rows = _conditions(store)
    (Path(getattr(rows[0], slot).path) / file).write_text("{}")
    with pytest.raises(ValueError, match="cannot supply"):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("field,value", [("seed", 999), ("seed", 1003), ("seed", 1000.0), ("seed", True), ("roles", ("exp3_repairs",)), ("execution_stage", "exp3_repairs"), ("unit_id", "x"), ("ensemble_size", 1), ("n_train", 42)])
def test_wrong_baseline_metadata_refuses(store, tmp_path, field, value):
    rows = _conditions(store)
    store.change(rows[0].baseline, **{field: value})
    with pytest.raises(ValueError):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("field,value", [("seed", 999), ("seed", 1003), ("seed", 1000.0), ("seed", True), ("arm", "baseline"), ("config_id", "x"), ("obligation_fit_id", "x"), ("obligation_run_id", "x"), ("physical_fit_id", "x"), ("physical_run_id", "x"), ("n_train", 42)])
def test_wrong_paired_metadata_refuses(store, tmp_path, field, value):
    rows = _conditions(store)
    store.change(rows[0].data_repair, **{field: value})
    with pytest.raises(ValueError, match="paired .* differs"):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("field,value", [("baseline_commit", "d" * 40), ("baseline_execution_digest", "d" * 64), ("baseline_fit_id", "x"), ("physical_fit_id", "x"), ("obligation_fit_id", "x"), ("generation_stage", "exp3_repairs"), ("obligation_stage", "config_sweep"), ("seed", 1001), ("arm", "capacity_repair"), ("procedure", "legacy")])
def test_resigned_contract_cannot_substitute_baseline_or_stage_meaning(store, tmp_path, field, value):
    rows = _conditions(store)
    source = rows[0].data_repair
    fit = store.entries[Path(source.path)][0]
    doc = fit.contract.as_dict()
    doc[field] = value
    store.change(source, contract=RP.SweepRepairContract(RP._json(doc)))
    with pytest.raises(ValueError):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


def test_duplicate_paths_and_duplicate_seeds_even_with_independent_copies_refuse(store, tmp_path):
    rows = _conditions(store)
    with pytest.raises(ValueError, match="duplicate physical source"):
        S.build_ordinary_sweep_label_evidence((rows[0], rows[0], rows[2]), unit=_unit(), path=tmp_path / "label.json")
    duplicate = _conditions(store)[0]
    with pytest.raises(ValueError, match="duplicates/missing"):
        S.build_ordinary_sweep_label_evidence((rows[0], duplicate, rows[2]), unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("mutation", ["action", "episode", "step", "empty", "nan", "negative", "subset_scale"])
def test_cross_arm_inventory_and_invalid_failure_sets_never_become_observed(store, tmp_path, mutation):
    rows = _conditions(store)
    if mutation in ("empty", "nan", "negative"):
        source = rows[0].baseline
        fit = store.entries[Path(source.path)][0]
        error = fit.error.copy()
        error[:] = K.FAILURE_THRESHOLD if mutation == "empty" else np.nan if mutation == "nan" else -1
        store.change(source, error=error, diagnostics=dict(fit.diagnostics, error=error))
    else:
        source = rows[0].data_repair
        fit = store.entries[Path(source.path)][0]
        diagnostics = dict(fit.diagnostics)
        field = "evaluation_action" if mutation == "action" else "scale_n_reference" if mutation == "subset_scale" else mutation
        diagnostics[field] = fit.diagnostics[field].copy()
        if mutation == "subset_scale":
            diagnostics[field] = np.asarray(799)
        else:
            diagnostics[field][0] += 1
        store.change(source, diagnostics=diagnostics)
    with pytest.raises(ValueError):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    assert not (tmp_path / "label.json").exists()


@pytest.mark.parametrize("mutation", ["schema", "extra", "source_kind", "path", "baseline_digest", "commit", "physical_id", "mask", "scale", "acceptance", "boolean_label", "float_seed"])
def test_label_forgery_is_rederived_from_external_sources_not_artifact_fields(store, tmp_path, mutation):
    unit, rows, path, record = _build(store, tmp_path)
    rep = record["runs"][0]["data_repair"]
    if mutation == "schema":
        record["ordinary_sweep_label_evidence_schema_version"] = 2
    elif mutation == "extra":
        record["extra"] = 1
    elif mutation == "source_kind":
        rep["source_kind"] = "legacy_sweep_baseline"
    elif mutation == "path":
        rep["fit_evidence_path"] = "../outside"
    elif mutation == "baseline_digest":
        rep["baseline_execution_digest"] = "d" * 64
    elif mutation == "commit":
        rep["expected_git_commit"] = "d" * 40
    elif mutation == "physical_id":
        rep["physical_fit_id"] = rep["obligation_fit_id"]
    elif mutation == "mask":
        record["failure_masks"][0]["failure_count"] += 1
    elif mutation == "scale":
        record["runs"][0]["normalisation"]["scale"][0] += 1e-12
    elif mutation == "acceptance":
        record["acceptance"]["data_repair"]["effect"] += .01
    elif mutation == "boolean_label":
        record["label"]["observed_label"] = False
    else:
        record["runs"][0]["seed"] = 1000.0
    _rewrite(path, record)
    with pytest.raises(ValueError, match="sweep label metadata"):
        S.load_ordinary_sweep_label_evidence(path, unit=unit, conditions=rows)
    assert len(store.calls) == 18


def test_portability_requires_descendants_and_immutable_writes(store, tmp_path):
    unit, rows, path, record = _build(store, tmp_path)
    with pytest.raises(ValueError, match="outside label evidence tree"):
        S.build_ordinary_sweep_label_evidence(rows, unit=unit, path=tmp_path / "nested" / "label.json")
    assert S.build_ordinary_sweep_label_evidence(tuple(reversed(rows)), unit=unit, path=path) == record
    before = path.read_bytes()
    other = _conditions(store, data=False, model=True)
    with pytest.raises(ValueError, match="overwrite immutable"):
        S.build_ordinary_sweep_label_evidence(other, unit=unit, path=path)
    assert path.read_bytes() == before
    copied = tmp_path / "copy"
    copied.mkdir()
    shutil.copy2(path, copied / path.name)
    copied_rows = []
    for row in rows:
        sources = []
        for source in (row.baseline, row.data_repair, row.model_repair):
            new_path = copied / Path(source.path).relative_to(tmp_path)
            new_path.mkdir(parents=True)
            fit, commit = store.entries[Path(source.path)]
            store.entries[new_path] = (replace(fit, fit_dir=new_path), commit)
            sources.append(replace(source, path=new_path))
        copied_rows.append(S.SweepRepairCondition(*sources))
    assert S.load_ordinary_sweep_label_evidence(copied / path.name, unit=unit, conditions=copied_rows) == record


def test_old_label_boundaries_stay_separate_and_external_conditions_are_required(store, tmp_path):
    unit, rows, path, record = _build(store, tmp_path)
    with pytest.raises(ValueError):
        L.load_label_evidence(path)
    with pytest.raises(ValueError, match="sweep labels are blocked"):
        O.load_ordinary_label_evidence(path, unit=unit, conditions=())
    with pytest.raises(TypeError):
        S.load_ordinary_sweep_label_evidence(path)
    assert "ordinary_label_evidence_schema_version" not in record
    assert "label_evidence_schema_version" not in record


def test_replacing_baseline_with_another_pinned_execution_cannot_reuse_old_repairs(store, tmp_path):
    rows = list(_conditions(store))
    baseline = rows[0].baseline
    store.change(baseline, execution_digest="f" * 64)
    rows[0] = replace(rows[0], baseline=replace(baseline, expected_execution_digest="f" * 64))
    with pytest.raises(ValueError, match="different baseline"):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    assert not (tmp_path / "label.json").exists()


def test_reader_cannot_return_legacy_repair_or_substituted_source_path(store, tmp_path):
    rows = _conditions(store)
    source = rows[0].data_repair
    paired, commit = store.entries[Path(source.path)]
    legacy = store.entries[Path(rows[0].baseline.path)][0]
    store.entries[Path(source.path)] = (replace(legacy, fit_dir=Path(source.path)), commit)
    with pytest.raises(ValueError, match="wrong type"):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    store.entries[Path(source.path)] = (replace(paired, fit_dir=tmp_path / "substitution"), commit)
    with pytest.raises(ValueError, match="substituted source directory"):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")


@pytest.mark.parametrize("field,bad", [("expected_git_commit", "B" * 40), ("expected_execution_digest", "a" * 63), ("path", None)])
def test_malformed_external_pins_fail_before_any_reader(store, tmp_path, field, bad):
    rows = list(_conditions(store))
    rows[0] = replace(rows[0], model_repair=replace(rows[0].model_repair, **{field: bad}))
    with pytest.raises(ValueError):
        S.build_ordinary_sweep_label_evidence(rows, unit=_unit(), path=tmp_path / "label.json")
    assert store.calls == []


def test_real_anchored_readers_with_untrained_synthetic_models(tmp_path, monkeypatch):
    """Real nine-source round trip, including contracts, arrays and corruption.

    Local fixture duplicates the small fake-training boundary rather than
    changing shared tests or touching any production artifacts.
    """
    from bu.experiments import confirmatory as C
    from bu.experiments import preflight as P
    from bu.models.ensemble import Ensemble
    from bu.models.world_model import WorldModel
    from bu.runrecord import GitState
    import bu.runrecord as RR
    from fixture_randomness import use_development_input_streams

    use_development_input_streams(monkeypatch)

    state = lambda *args, **kwargs: GitState("b" * 40, False, "synthetic")
    for module in (C, F, P, RR):
        monkeypatch.setattr(module, "git_state", state)
    calls = []

    def untrained(unit, pools, config, *, stage, seed, arm, granularity, logger, epoch_logger, device):
        assert device == "cpu"
        first = json.loads((logger.run_dir / "metrics.jsonl").read_text().splitlines()[0])
        assert first["event"] == ("pool_anchors" if arm == "baseline" else "paired_inputs")
        models = tuple(WorldModel(Arm(arm).resolve(unit), np.random.default_rng(i)) for i in range(config.ensemble_size))
        for i in range(config.ensemble_size):
            logger.log(record_type="member_summary", member=i, synthetic_untrained=True)
        calls.append((arm, seed))
        return Ensemble(unit, Arm(arm).resolve(unit), arm, models, (), granularity)

    monkeypatch.setattr(C, "train_ensemble", untrained)
    monkeypatch.setattr(E, "train_ensemble", untrained)
    unit = min(SWEEP, key=lambda u: (u.n_transitions, u.hidden_size, Config(unit=u).unit_id))
    model_arm = S._registered_unit(unit)
    rows = []
    for seed in SEEDS:
        base_path = tmp_path / f"baseline-{seed}"
        base = F.run_confirmatory_fit(unit, arm="baseline", seed=seed, out_dir=base_path, expected_git_commit="b" * 40)
        base_source = S.SweepBaselineSource(base_path, "b" * 40, base.verified.execution_digest)
        repairs = []
        for arm in ("data_repair", model_arm):
            repair_path = tmp_path / f"{arm}-{seed}"
            result = E.run_paired_repair(
                unit, arm=arm, seed=seed, baseline_source=base_path,
                expected_baseline_commit="b" * 40,
                expected_baseline_execution_digest=base.verified.execution_digest,
                expected_git_commit="b" * 40, out_dir=repair_path,
            )
            repairs.append(S.PairedRepairSource(repair_path, "b" * 40, result.execution_digest))
        rows.append(S.SweepRepairCondition(base_source, *repairs))
    assert len(calls) == 9  # untrained models only; all optimisation replaced
    path = tmp_path / "label.json"
    record = S.build_ordinary_sweep_label_evidence(rows, unit=unit, path=path)
    assert record["seeds"] == list(SEEDS)
    assert record["label"]["observed_label"] in (0, 1, "ambiguous", "undiagnosed")
    assert S.load_ordinary_sweep_label_evidence(path, unit=unit, conditions=rows) == record
    assert len(calls) == 9  # both label boundaries are reader-only
    final = Path(rows[-1].model_repair.path) / E.EVALUATION_DIRECTORY / "error.npy"
    final.write_bytes(final.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="paired artifact.*changed"):
        S.load_ordinary_sweep_label_evidence(path, unit=unit, conditions=rows)
    assert len(calls) == 9
