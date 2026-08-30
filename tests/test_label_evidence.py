"""Synthetic tests for the persisted Week 6 label-evidence boundary.

Every fit in this file is a fabricated ``VerifiedFitEvidence`` returned by a
test loader. No model is trained, no real sidecar is read and no confirmatory
data are inspected. The real sidecar loader has its own tests; these tests pin
the label consumer's independent reload, role projection and fail-closed schema.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Arm
from bu.experiments import label_evidence as L
from bu.experiments.enumerate_units import repair_validation_units
from bu.experiments.fit_evidence import VerifiedFitEvidence, registered_fit_spec
from bu.experiments.label_evidence import (
    PersistedRepairCondition,
    build_label_evidence,
    count_label_evidence,
    load_label_evidence,
    summarize_label_evidence,
    write_label_evidence_counts,
    write_label_evidence_summary,
)
from bu.experiments.repair import REPAIR_STAGE
from bu.models.uncertainty import NormalisationScale
from bu.streams import confirmatory_seeds


SEEDS = confirmatory_seeds(K.SEEDS_REPAIR_VALIDATION)


@lru_cache(maxsize=None)
def _spec(unit, arm: str, seed: int):
    return registered_fit_spec(unit, arm=arm, seed=seed)


def _units_with_one_model_repair():
    return tuple(
        unit for unit in repair_validation_units() if unit.family == "missing_feature"
    )


def _model_repair_arm(unit) -> str:
    applicable = []
    for arm in ("feature_repair", "capacity_repair"):
        try:
            Arm(arm).resolve(unit)
        except ValueError:
            continue
        applicable.append(arm)
    assert len(applicable) == 1
    return applicable[0]


def _experiment1_repair_unit():
    for unit in repair_validation_units():
        if "exp1" in _spec(unit, "baseline", SEEDS[0]).roles:
            return unit
    raise AssertionError("no repair-validation unit carries an Experiment-1 role")


class _SyntheticFitStore:
    """Test-only loader inventory; it never writes a fit or sidecar."""

    def __init__(self, root: Path):
        self.root = root
        self.entries: dict[Path, VerifiedFitEvidence] = {}
        self.calls: list[Path] = []
        self._counter = 0

    def add(
        self,
        unit,
        *,
        seed: int,
        arm: str,
        error: np.ndarray,
        scale: NormalisationScale,
        evaluation_action: np.ndarray | None = None,
        evaluation_pool_digest: str | None = None,
    ) -> Path:
        spec = _spec(unit, arm, seed)
        self._counter += 1
        path = (self.root / f"fit-{self._counter:04d}-{spec.fit_id}").resolve()
        episode = np.array([0, 0, 1, 1], dtype=np.int64)
        step = np.array([0, 1, 0, 1], dtype=np.int64)
        errors = np.asarray(error, dtype=np.float64)
        digest = hashlib.sha256(
            f"{spec.fit_id}:{self._counter}".encode("ascii")
        ).hexdigest()
        if evaluation_action is None:
            base_actions = np.tile(np.arange(5, dtype=np.int64), 200)
            evaluation_action = np.roll(base_actions, seed % 5)
        else:
            evaluation_action = np.asarray(evaluation_action)
        if evaluation_pool_digest is None:
            pool_kind = "feature-restored" if arm == "feature_repair" else "baseline"
            evaluation_pool_digest = hashlib.sha256(
                f"pool:{spec.unit_id}:{seed}:{pool_kind}".encode("ascii")
            ).hexdigest()
        verified = VerifiedFitEvidence(
            fit_dir=path,
            unit=unit,
            arm=arm,
            seed=seed,
            roles=spec.roles,
            execution_stage=spec.execution_stage,
            unit_id=spec.unit_id,
            config_id=spec.config_id,
            fit_id=spec.fit_id,
            execution_run_id=spec.execution_run_id,
            execution_digest=digest,
            evaluation_pool_digest=evaluation_pool_digest,
            diagnostics=MappingProxyType(
                {
                    "episode": episode,
                    "step": step,
                    "error": errors,
                    "evaluation_action": evaluation_action,
                }
            ),
            error=errors,
            episode=episode,
            step=step,
            scale=scale,
            n_train=Arm(arm).resolve(unit).n_transitions,
            ensemble_size=K.DEFAULT_ENSEMBLE_SIZE if arm == "baseline" else 1,
        )
        self.entries[path] = verified
        return path

    def load(self, path) -> VerifiedFitEvidence:
        resolved = Path(path).resolve()
        self.calls.append(resolved)
        try:
            return self.entries[resolved]
        except KeyError as exc:
            raise ValueError(f"synthetic sidecar absent at {resolved}") from exc


@pytest.fixture
def fit_store(tmp_path, monkeypatch):
    store = _SyntheticFitStore(tmp_path / "persisted-fits")
    monkeypatch.setattr(L, "load_fit_evidence", store.load)
    return store


def _conditions(
    store: _SyntheticFitStore,
    unit,
    *,
    data_works: bool,
    model_works: bool,
    baseline_error: np.ndarray | None = None,
) -> tuple[PersistedRepairCondition, ...]:
    baseline_error = (
        np.array([K.FAILURE_THRESHOLD, 1.0, 1.1, 1.2])
        if baseline_error is None
        else np.asarray(baseline_error, dtype=float)
    )
    rows = []
    model_arm = _model_repair_arm(unit)
    for position, seed in enumerate(SEEDS):
        variation = (position - (len(SEEDS) - 1) / 2) * 0.002
        data_delta = (-0.35 if data_works else 0.02) + variation
        model_delta = (-0.35 if model_works else 0.02) - variation
        scale = NormalisationScale(torch.ones(2), n_reference=len(baseline_error))
        baseline = store.add(
            unit, seed=seed, arm="baseline", error=baseline_error, scale=scale
        )
        data = store.add(
            unit,
            seed=seed,
            arm="data_repair",
            error=baseline_error + data_delta,
            scale=scale,
        )
        model = store.add(
            unit,
            seed=seed,
            arm=model_arm,
            error=baseline_error + model_delta,
            scale=scale,
        )
        rows.append(PersistedRepairCondition(baseline, data, model))
    return tuple(rows)


def _redigest(record: dict) -> None:
    payload = {key: value for key, value in record.items() if key != "record_digest"}
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    record["record_digest"] = hashlib.sha256(encoded).hexdigest()


@pytest.mark.parametrize(
    ("data_works", "model_works", "expected"),
    [
        (True, False, 0),
        (False, True, 1),
        (True, True, "ambiguous"),
        (False, False, "undiagnosed"),
    ],
)
def test_persisted_evidence_emits_each_registered_label(
    tmp_path, fit_store, data_works, model_works, expected
):
    unit = _units_with_one_model_repair()[0]
    conditions = _conditions(
        fit_store, unit, data_works=data_works, model_works=model_works
    )
    path = tmp_path / f"label-{expected}.json"
    record = build_label_evidence(conditions, path=path)

    assert len(fit_store.calls) == 60
    assert record["label"]["observed_label"] == expected
    assert record["label"]["data_repair_works"] is data_works
    assert record["label"]["model_repair_works"] is model_works
    assert record["acceptance"]["data_repair"]["passed"] is data_works
    assert record["acceptance"]["model_repair"]["passed"] is model_works
    assert record["seeds"] == list(SEEDS)
    assert [row["failure_count"] for row in record["failure_masks"]] == [3] * 20
    assert load_label_evidence(path) == record


def test_experiment1_baseline_is_projected_without_duplicate_fit(fit_store, tmp_path):
    unit = _experiment1_repair_unit()
    source = fit_store.add(
        unit,
        seed=SEEDS[0],
        arm="baseline",
        error=np.array([K.FAILURE_THRESHOLD, 1.0, 1.1, 1.2]),
        scale=NormalisationScale(torch.ones(2), n_reference=4),
    )
    physical = fit_store.entries[source]
    projected = L.load_repair_validation_projection(source)

    assert physical.execution_stage == "exp1"
    assert physical.roles == ("exp1", REPAIR_STAGE)
    assert physical.execution_run_id.endswith("-exp1-s1000")
    assert projected.run_id.endswith(f"-{REPAIR_STAGE}-s1000")
    assert physical.execution_run_id != projected.run_id
    assert projected.config_id == physical.config_id
    assert fit_store.calls == [source]


def test_verified_object_is_only_a_path_and_is_reloaded(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    path = Path(conditions[0].baseline)
    genuine = fit_store.entries[path.resolve()]
    stale = replace(genuine, execution_digest="0" * 64, error=np.array([999.0]))
    conditions[0] = replace(conditions[0], baseline=stale)

    record = build_label_evidence(conditions, path=tmp_path / "label.json")
    assert record["runs"][0]["baseline"]["fit_evidence_digest"] == genuine.execution_digest
    assert path.resolve() in fit_store.calls


def test_in_memory_confirmatory_objects_have_no_production_overload(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    conditions[0] = replace(conditions[0], baseline=object())
    with pytest.raises(ValueError, match="In-memory ConfirmatoryRun"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_incomplete_registered_seed_set_is_refused_before_loading(fit_store, tmp_path):
    conditions = _conditions(
        fit_store,
        _units_with_one_model_repair()[0],
        data_works=True,
        model_works=False,
    )
    with pytest.raises(ValueError, match="exactly 20"):
        build_label_evidence(conditions[:-1], path=tmp_path / "label.json")
    assert fit_store.calls == []


def test_cross_seed_unit_identity_change_is_refused(fit_store, tmp_path):
    units = _units_with_one_model_repair()
    conditions = list(
        _conditions(fit_store, units[0], data_works=True, model_works=False)
    )
    other = _conditions(fit_store, units[1], data_works=True, model_works=False)[-1]
    conditions[-1] = other
    with pytest.raises(ValueError, match="one unit_id"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_wrong_arm_is_refused_from_reloaded_evidence(fit_store, tmp_path):
    units = _units_with_one_model_repair()
    conditions = list(
        _conditions(fit_store, units[0], data_works=True, model_works=False)
    )
    alien = fit_store.add(
        units[1],
        seed=SEEDS[0],
        arm="baseline",
        error=np.ones(4),
        scale=NormalisationScale(torch.ones(2), n_reference=4),
    )
    conditions[0] = replace(conditions[0], data_repair=alien)
    with pytest.raises(ValueError, match="data-repair source carries arm"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_unregistered_role_projection_is_refused(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    source = Path(conditions[0].baseline).resolve()
    fit_store.entries[source] = replace(fit_store.entries[source], roles=("exp1",))
    with pytest.raises(ValueError, match="current registry derives"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_missing_or_partial_fit_sidecar_is_refused(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    missing = Path(conditions[0].data_repair).resolve()
    del fit_store.entries[missing]
    with pytest.raises(ValueError, match="cannot verify persisted fit evidence"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_duplicate_physical_fit_id_is_refused(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    conditions[-1] = conditions[0]
    with pytest.raises(ValueError, match="duplicate physical fit_id"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_repaired_scale_must_equal_persisted_baseline_scale(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    source = Path(conditions[0].data_repair).resolve()
    fit_store.entries[source] = replace(
        fit_store.entries[source],
        scale=NormalisationScale(torch.tensor([1.0, 2.0]), n_reference=4),
    )
    with pytest.raises(ValueError, match="baseline's exact"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_cross_arm_full_evaluation_action_inventory_must_match(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    source = Path(conditions[0].data_repair).resolve()
    verified = fit_store.entries[source]
    changed = np.array(verified.diagnostics["evaluation_action"], copy=True)
    changed[0] = (int(changed[0]) + 1) % 5
    fit_store.entries[source] = replace(
        verified,
        diagnostics=MappingProxyType(
            {**dict(verified.diagnostics), "evaluation_action": changed}
        ),
    )

    with pytest.raises(ValueError, match="exact full evaluation_action inventory"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_cross_arm_independently_verified_pool_digest_must_match(
    fit_store, tmp_path
):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    source = Path(conditions[0].data_repair).resolve()
    verified = fit_store.entries[source]
    fit_store.entries[source] = replace(
        verified, evaluation_pool_digest="f" * 64
    )

    with pytest.raises(ValueError, match="independently verified encoded-pool digest"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_feature_repair_encoded_pool_digest_must_change(fit_store, tmp_path):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    baseline = fit_store.entries[Path(conditions[0].baseline).resolve()]
    source = Path(conditions[0].model_repair).resolve()
    feature = fit_store.entries[source]
    assert feature.arm == "feature_repair"
    fit_store.entries[source] = replace(
        feature, evaluation_pool_digest=baseline.evaluation_pool_digest
    )

    with pytest.raises(ValueError, match="restoring a withheld feature"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


@pytest.mark.parametrize("inventory", ["episode", "step"])
def test_cross_arm_latent_trajectory_inventory_must_match(
    fit_store, tmp_path, inventory
):
    conditions = list(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[0],
            data_works=True,
            model_works=False,
        )
    )
    source = Path(conditions[0].model_repair).resolve()
    verified = fit_store.entries[source]
    changed = np.array(verified.diagnostics[inventory], copy=True)
    changed[-1] += 1
    fit_store.entries[source] = replace(
        verified,
        diagnostics=MappingProxyType(
            {**dict(verified.diagnostics), inventory: changed}
        ),
        **{inventory: changed},
    )

    with pytest.raises(ValueError, match=f"exact full {inventory} inventory"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


@pytest.mark.parametrize("binding", ["evaluation_action", "evaluation_pool_digest"])
def test_loader_rechecks_cross_arm_pool_binding(fit_store, tmp_path, binding):
    record = _record(fit_store, tmp_path)
    path = _record_path(tmp_path)
    source = (
        path.parent / record["runs"][0]["data_repair"]["fit_evidence_path"]
    ).resolve()
    verified = fit_store.entries[source]
    if binding == "evaluation_action":
        changed = np.array(verified.diagnostics["evaluation_action"], copy=True)
        changed[-1] = (int(changed[-1]) + 1) % 5
        fit_store.entries[source] = replace(
            verified,
            diagnostics=MappingProxyType(
                {**dict(verified.diagnostics), "evaluation_action": changed}
            ),
        )
        message = "exact full evaluation_action inventory"
    else:
        fit_store.entries[source] = replace(
            verified, evaluation_pool_digest="e" * 64
        )
        message = "independently verified encoded-pool digest"

    with pytest.raises(ValueError, match=message):
        load_label_evidence(path)


def test_empty_strict_failure_mask_is_refused(fit_store, tmp_path):
    errors = np.full(4, K.FAILURE_THRESHOLD)
    conditions = _conditions(
        fit_store,
        _units_with_one_model_repair()[0],
        data_works=True,
        model_works=False,
        baseline_error=errors,
    )
    with pytest.raises(ValueError, match="failure set is empty"):
        build_label_evidence(conditions, path=tmp_path / "label.json")


def test_mask_digest_is_deterministic_and_binds_baseline_errors(fit_store, tmp_path):
    conditions = _conditions(
        fit_store,
        _units_with_one_model_repair()[0],
        data_works=True,
        model_works=False,
    )
    first = build_label_evidence(conditions, path=tmp_path / "first.json")
    second = build_label_evidence(conditions, path=tmp_path / "second.json")
    assert first["failure_masks"] == second["failure_masks"]
    assert len(first["failure_masks"][0]["mask_digest"]) == 64


def test_existing_different_record_is_never_overwritten(fit_store, tmp_path):
    units = _units_with_one_model_repair()
    path = tmp_path / "label.json"
    first_conditions = _conditions(
        fit_store, units[0], data_works=True, model_works=False
    )
    first = build_label_evidence(first_conditions, path=path)
    assert build_label_evidence(first_conditions, path=path) == first
    before = path.read_bytes()
    with pytest.raises(ValueError, match="different content"):
        build_label_evidence(
            _conditions(fit_store, units[1], data_works=False, model_works=True),
            path=path,
        )
    assert path.read_bytes() == before


def _record(fit_store, tmp_path, *, data=True, model=False, unit_index=0):
    path = _record_path(
        tmp_path, data=data, model=model, unit_index=unit_index
    )
    return build_label_evidence(
        _conditions(
            fit_store,
            _units_with_one_model_repair()[unit_index],
            data_works=data,
            model_works=model,
        ),
        path=path,
    )


def _record_path(tmp_path, *, data=True, model=False, unit_index=0):
    return tmp_path / f"label-{unit_index}-{data}-{model}.json"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda r: r.update({"extra": 1}), "exact schema"),
        (lambda r: r.pop("family"), "exact schema"),
        (lambda r: r["label"].update({"extra": 1}), "label keys"),
        (lambda r: r["label"].pop("unit_id"), "label keys"),
        (
            lambda r: r["acceptance"]["data_repair"].update({"extra": 1}),
            "acceptance.data_repair keys",
        ),
        (
            lambda r: r["failure_masks"][0].update({"extra": 1}),
            "failure mask row keys",
        ),
        (
            lambda r: r["runs"][0]["baseline"].update({"extra": 1}),
            "run row 1000 baseline keys",
        ),
    ],
)
def test_loader_refuses_extra_schema_fields(fit_store, tmp_path, mutation, message):
    record = _record(fit_store, tmp_path)
    mutation(record)
    _redigest(record)
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_label_evidence(path)


@pytest.mark.parametrize("field", ["data_repair_works", "model_repair_works"])
def test_loader_refuses_integer_substitute_for_boolean(fit_store, tmp_path, field):
    record = _record(fit_store, tmp_path)
    record["label"][field] = int(record["label"][field])
    _redigest(record)
    path = tmp_path / f"bad-{field}.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="exact boolean"):
        load_label_evidence(path)


def test_false_never_satisfies_observed_integer_zero(fit_store, tmp_path):
    record = _record(fit_store, tmp_path, data=True, model=False)
    assert record["label"]["observed_label"] == 0
    record["label"]["observed_label"] = False
    _redigest(record)
    path = tmp_path / "false-is-not-zero.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="booleans are not integer labels"):
        load_label_evidence(path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: row.update({"passed": not row["passed"]}),
        lambda row: row.update({"ci_high": 0.01}),
        lambda row: row.update(
            {"relative_reduction": K.MIN_PRACTICAL_EFFECT - 0.01}
        ),
        lambda row: row.update({"min_practical_effect": 0.0}),
        lambda row: row.update({"confidence": 0.90}),
    ],
)
def test_loader_recomputes_acceptance_verdict(fit_store, tmp_path, mutate):
    record = _record(fit_store, tmp_path, data=True, model=False)
    mutate(record["acceptance"]["data_repair"])
    _redigest(record)
    path = tmp_path / "forged-verdict.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen|relative_reduction|passed"):
        load_label_evidence(path)


def test_persisted_acceptance_uses_the_strict_twenty_percent_boundary():
    """The evidence loader must enforce the same strict P§7.3 rule as creation."""
    row = {
        "effect": -K.MIN_PRACTICAL_EFFECT,
        "ci_low": -0.25,
        "ci_high": -0.15,
        "relative_reduction": K.MIN_PRACTICAL_EFFECT,
        "passed": True,
        "reason": "synthetic exact-boundary row",
        "method": "paired_seed_cluster",
        "converged": True,
        "n_transitions": 40,
        "n_seeds": 20,
        "n_episodes": 20,
        "unrepaired_mean": 1.0,
        "min_practical_effect": K.MIN_PRACTICAL_EFFECT,
        "confidence": 0.95,
    }
    with pytest.raises(ValueError, match="passed=True.*recomputed passed=False"):
        L._validate_acceptance_row(row, name="data_repair", n_seeds=20)

    row["passed"] = False
    assert not L._validate_acceptance_row(row, name="data_repair", n_seeds=20)


def test_loader_refuses_duplicate_physical_fit_id_in_record(fit_store, tmp_path):
    record = _record(fit_store, tmp_path)
    record["runs"][1]["baseline"] = dict(record["runs"][0]["baseline"])
    _redigest(record)
    path = tmp_path / "duplicate-fit.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="inconsistent with provenance|repeats physical"):
        load_label_evidence(path)


def test_record_persists_only_portable_descendant_source_paths(fit_store, tmp_path):
    record = _record(fit_store, tmp_path)
    for row in record["runs"]:
        for key in ("baseline", "data_repair", "model_repair"):
            source = row[key]["fit_evidence_path"]
            assert source.startswith("persisted-fits/")
            assert "\\" not in source
            assert ".." not in Path(source).parts
            assert not Path(source).is_absolute()


def test_builder_refuses_fit_sources_outside_the_label_evidence_tree(
    fit_store, tmp_path
):
    conditions = _conditions(
        fit_store,
        _units_with_one_model_repair()[0],
        data_works=True,
        model_works=False,
    )
    nested_label = tmp_path / "separate-label-tree" / "label.json"

    with pytest.raises(ValueError, match="outside label evidence tree"):
        build_label_evidence(conditions, path=nested_label)
    assert not nested_label.exists()


@pytest.mark.parametrize(
    "forged_path",
    ["../outside-fit", "/absolute/fit", "C:/absolute/fit", "a/../fit", "a\\fit"],
)
def test_loader_refuses_source_path_traversal(
    fit_store, tmp_path, forged_path
):
    record = _record(fit_store, tmp_path)
    record["runs"][0]["baseline"]["fit_evidence_path"] = forged_path
    _redigest(record)
    path = tmp_path / "traversal.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="canonical relative|portable"):
        load_label_evidence(path)


def test_consistently_redigested_acceptance_forgery_is_refused_against_sources(
    fit_store, tmp_path
):
    record = _record(fit_store, tmp_path, data=True, model=False)
    row = record["acceptance"]["data_repair"]
    row.update(
        {
            "effect": -0.4,
            "ci_low": -0.5,
            "ci_high": -0.3,
            "relative_reduction": 0.4,
            "unrepaired_mean": 1.0,
            "passed": True,
            "reason": "forged but internally consistent acceptance row",
        }
    )
    _redigest(record)
    path = tmp_path / "consistently-redigested-forgery.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="does not exactly equal.*rederived"):
        load_label_evidence(path)


def test_loader_refuses_changed_source_fit_even_with_valid_record_digest(
    fit_store, tmp_path
):
    record = _record(fit_store, tmp_path)
    path = _record_path(tmp_path)
    source = (
        path.parent / record["runs"][0]["baseline"]["fit_evidence_path"]
    ).resolve()
    original = fit_store.entries[source]
    fit_store.entries[source] = replace(
        original,
        error=np.array([K.FAILURE_THRESHOLD, 0.8, 0.9, 1.0]),
        execution_digest="a" * 64,
    )

    with pytest.raises(ValueError, match="does not exactly equal.*rederived"):
        load_label_evidence(path)


def test_loader_refuses_missing_source_fit(fit_store, tmp_path):
    record = _record(fit_store, tmp_path)
    path = _record_path(tmp_path)
    source = (
        path.parent / record["runs"][0]["data_repair"]["fit_evidence_path"]
    ).resolve()
    del fit_store.entries[source]

    with pytest.raises(ValueError, match="cannot verify persisted fit evidence"):
        load_label_evidence(path)


def test_whole_evidence_tree_can_be_relocated(fit_store, tmp_path):
    record = _record(fit_store, tmp_path)
    original_path = _record_path(tmp_path)
    relocated_root = (tmp_path / "relocated-tree").resolve()
    relocated_root.mkdir()
    relocated_path = relocated_root / original_path.name
    relocated_path.write_bytes(original_path.read_bytes())

    original_root = tmp_path.resolve()
    for old_path, verified in list(fit_store.entries.items()):
        relative = old_path.relative_to(original_root)
        new_path = (relocated_root / relative).resolve()
        fit_store.entries[new_path] = replace(verified, fit_dir=new_path)

    assert load_label_evidence(relocated_path) == record


def test_exact_summary_reports_all_counts_and_pre_reserve_shortfall(
    fit_store, tmp_path
):
    outcomes = ((True, False), (False, True), (True, True), (False, False))
    records = [
        _record(
            fit_store,
            tmp_path,
            data=data,
            model=model,
            unit_index=index,
        )
        for index, (data, model) in enumerate(outcomes)
    ]
    paths = [
        _record_path(
            tmp_path,
            data=data,
            model=model,
            unit_index=index,
        )
        for index, (data, model) in enumerate(outcomes)
    ]
    summary = summarize_label_evidence(paths)
    assert summary["attempted"] == 4
    assert summary["observed_0"] == 1
    assert summary["observed_1"] == 1
    assert summary["ambiguous"] == 1
    assert summary["undiagnosed"] == 1
    assert summary["excluded"] == 2
    assert summary["exclusion_rate"] == 0.5
    assert summary["surviving_min_n0_n1"] == 1
    assert summary["registered_planning_exclusion_rate"] == 0.00
    assert summary["planning_assumption_missed"] is True
    assert summary["shortfall_before_reserve_count"] == 2
    assert "before any reserve" in summary["shortfall_before_reserve"]

    path = tmp_path / "summary.json"
    assert write_label_evidence_summary(paths, path=path) == summary


def test_summary_refuses_duplicate_statistical_units(fit_store, tmp_path):
    _record(fit_store, tmp_path)
    path = _record_path(tmp_path)
    with pytest.raises(ValueError, match="duplicate unit_id"):
        summarize_label_evidence([path, path])


def test_summary_refuses_raw_metadata_even_if_metadata_is_valid(fit_store, tmp_path):
    record = _record(fit_store, tmp_path)
    with pytest.raises(ValueError, match="filesystem path"):
        summarize_label_evidence([record])


def test_summary_refuses_to_call_planning_assumption_observed_without_data():
    with pytest.raises(ValueError, match="planning assumption"):
        summarize_label_evidence([])


def test_week6_count_report_reopens_sources_and_omits_week8_estimand(
    fit_store, tmp_path
):
    outcomes = ((True, False), (False, True), (True, True), (False, False))
    paths = []
    for index, (data, model) in enumerate(outcomes):
        _record(
            fit_store,
            tmp_path,
            data=data,
            model=model,
            unit_index=index,
        )
        paths.append(
            _record_path(
                tmp_path,
                data=data,
                model=model,
                unit_index=index,
            )
        )

    counts = count_label_evidence(paths)

    assert counts["label_count_schema_version"] == 1
    assert counts["attempted"] == 4
    assert counts["observed_0"] == 1
    assert counts["observed_1"] == 1
    assert counts["ambiguous"] == 1
    assert counts["undiagnosed"] == 1
    forbidden = {
        "excluded",
        "exclusion_rate",
        "registered_planning_exclusion_rate",
        "planning_assumption_missed",
        "shortfall_before_reserve_count",
        "shortfall_before_reserve",
    }
    assert forbidden.isdisjoint(counts)

    destination = tmp_path / "counts.json"
    assert write_label_evidence_counts(paths, path=destination) == counts
    assert json.loads(destination.read_text(encoding="utf-8")) == counts


def test_week6_counts_refuse_raw_duplicate_and_empty_inputs(fit_store, tmp_path):
    record = _record(fit_store, tmp_path)
    path = _record_path(tmp_path)
    with pytest.raises(ValueError, match="filesystem path"):
        count_label_evidence([record])
    with pytest.raises(ValueError, match="duplicate unit_id"):
        count_label_evidence([path, path])
    with pytest.raises(ValueError, match="zero label-evidence"):
        count_label_evidence([])
