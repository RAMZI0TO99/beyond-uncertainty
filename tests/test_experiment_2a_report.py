"""Fabricated-only tests for the source-bound Experiment-2A report.

No production evidence is opened and no confirmatory pool is generated.  The
already-certified fit/label byte readers are replaced by deterministic exact
objects; this suite instead proves that the report invokes both original/copy
roads with independent pins and enforces inventory, joins, replay, paths and
immutability.  Lower-layer sidecar parsing remains covered by its own suites.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import stat
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu import constants as K
from bu.config import Config
from bu.durable import DivergentTargetError, sha256_file
from bu.experiments import experiment_2a_report as R
from bu.experiments import fit_evidence as F
from bu.experiments import h2_diagnostics as H
from bu.experiments.enumerate_units import experiment_2a_units
from bu.experiments.labels import observed_label
from bu.streams import group_of


COMMIT = "a" * 40


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ordered_units():
    return R._registered_units()


def _acceptance(passed: bool, n_seeds: int) -> dict:
    effect = -0.4 if passed else -0.1
    return {
        "effect": effect,
        "ci_low": -0.5 if passed else -0.2,
        "ci_high": -0.3 if passed else 0.1,
        "relative_reduction": -effect,
        "passed": passed,
        "reason": "fabricated accepted" if passed else "fabricated interval crosses zero",
        "method": "paired_seed_cluster",
        "converged": True,
        "n_transitions": n_seeds * 100,
        "n_seeds": n_seeds,
        "n_episodes": n_seeds * 10,
        "unrepaired_mean": 1.0,
        "min_practical_effect": float(K.MIN_PRACTICAL_EFFECT),
        "confidence": float(K.CONFIDENCE_LEVEL),
    }


def _fit_id(unit_id: str, role: str, seed: int) -> str:
    return f"{unit_id}-{role}-s{seed}"


def _fit_digest(unit_id: str, role: str, seed: int) -> str:
    return _digest(_fit_id(unit_id, role, seed))


def _label_record(unit, *, path: Path, validation: bool, index: int) -> dict:
    unit_id = Config(unit=unit).unit_id
    seeds = list(range(1000, 1020)) if validation else list(range(1000, 1003))
    data_passed = index % 4 in (0, 2)
    feature_passed = index % 4 in (1, 2)
    runs = []
    for seed in seeds:
        items = {}
        for record_key, role in (
            ("baseline", "baseline"),
            ("data_repair", "data_repair"),
            ("model_repair", "feature_repair"),
        ):
            item = {
                "fit_id": _fit_id(unit_id, role, seed),
                "fit_evidence_digest": _fit_digest(unit_id, role, seed),
                "fit_evidence_path": f"fits/{role}-s{seed}",
            }
            if not validation:
                item["expected_git_commit"] = COMMIT
            items[record_key] = item
        runs.append({"seed": seed, **items})
    label = {
        "unit_id": unit_id,
        "comparison_group_id": group_of(unit, "exp2a"),
        "intended_class": "hypothesis_class",
        "data_repair_works": data_passed,
        "model_repair_works": feature_passed,
        "observed_label": observed_label(data_passed, feature_passed),
    }
    return {
        "unit_id": unit_id,
        "unit": Config(unit=unit).to_dict()["unit"],
        "family": "missing_feature",
        "comparison_group_id": group_of(unit, "exp2a"),
        "intended_class": "hypothesis_class",
        "stage": "repair_validation" if validation else "exp3_repairs",
        "seeds": seeds,
        "model_repair_arm": "feature_repair",
        "runs": runs,
        "acceptance": {
            "data_repair": _acceptance(data_passed, len(seeds)),
            "model_repair": _acceptance(feature_passed, len(seeds)),
        },
        "label": label,
        "record_digest": _digest(f"label:{unit_id}:{'v' if validation else 'o'}"),
    }


def _diagnostic(unit, sources) -> dict:
    unit_id = Config(unit=unit).unit_id
    index = next(i for i, item in enumerate(_ordered_units()) if item == unit)
    per_seed = []
    ratios = []
    for seed_index, (seed, source) in enumerate(zip(range(1000, 1005), sources, strict=True)):
        ratio = float(0.08 + index * 0.003 + seed_index * 0.002)
        ratios.append(ratio)
        pearson = None if (index + seed_index) % 7 == 0 else float(-0.5 + seed_index * 0.2)
        per_seed.append(
            {
                "h2_diagnostic_schema_version": H.H2_DIAGNOSTIC_SCHEMA_VERSION,
                "purpose": "per_seed_metrics_not_h2_adjudication",
                "unit_id": unit_id,
                "comparison_group_id": group_of(unit, "exp2a"),
                "stage": "exp2a",
                "seed": seed,
                "fit_id": _fit_id(unit_id, "baseline", seed),
                "execution_digest": source.expected_execution_digest,
                "expected_git_commit": source.expected_git_commit,
                "normalisation": {
                    "scale": [1.0, 2.0],
                    "scale_n_reference": 400,
                    "scale_domain": K.NORMALISATION_SCALE_DOMAIN,
                    "scale_source": K.NORMALISATION_SCALE_SOURCE,
                },
                "failure_definition": {
                    "operator": ">",
                    "threshold": K.FAILURE_THRESHOLD,
                },
                "ratio_floor": 1e-6,
                "correlation_method": "pearson",
                "correlation_domain": "baseline_failure_set",
                "n_movement": 400,
                "n_failure": 80 + seed_index,
                "failure_mask_sha256": _digest(f"mask:{unit_id}:{seed}"),
                "mean_error": 1.0,
                "mean_disagreement": ratio,
                "ratio_of_means": ratio,
                "pearson_r": pearson,
                "correlation_undefined_reason": (
                    "constant_error_or_disagreement" if pearson is None else None
                ),
                "observed_repair_label": None,
                "h2_verdict": None,
            }
        )
    mean, sd = R._mean_sd(ratios)
    return {
        "h2_diagnostic_schema_version": H.H2_DIAGNOSTIC_SCHEMA_VERSION,
        "purpose": "condition_metrics_not_h2_adjudication",
        "unit_id": unit_id,
        "seeds": list(range(1000, 1005)),
        "per_seed": per_seed,
        "ratio_mean_across_seeds": mean,
        "ratio_sample_sd_across_seeds": sd,
        "ratio_sd_ddof": 1,
        "transitions_pooled_across_seeds": False,
        "correlations_aggregated": False,
        "h2_verdict": None,
    }


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "_PROJECT_ROOT", tmp_path.resolve())
    validation_ids = R._validation_unit_ids()
    records = {}
    baselines = []
    validation_sources = []
    ordinary_sources = []
    fit_metadata = {}

    def pair(unit, role, seed):
        unit_id = Config(unit=unit).unit_id
        source_path = tmp_path / "exports-original" / unit_id / "fits" / f"{role}-s{seed}"
        copy_path = tmp_path / "exports-copy" / unit_id / "fits" / f"{role}-s{seed}"
        source_path.mkdir(parents=True, exist_ok=True)
        copy_path.mkdir(parents=True, exist_ok=True)
        result = R.Experiment2AFitSourcePair(
            source_path=source_path,
            copy_path=copy_path,
            expected_git_commit=COMMIT,
            expected_execution_digest=_fit_digest(unit_id, role, seed),
        )
        arm = role
        fit_metadata[source_path.resolve()] = (unit, arm, seed, result)
        fit_metadata[copy_path.resolve()] = (unit, arm, seed, result)
        return result

    for index, unit in enumerate(_ordered_units()):
        unit_id = Config(unit=unit).unit_id
        fit_pairs = {
            ("baseline", seed): pair(unit, "baseline", seed)
            for seed in range(1000, 1005)
        }
        baseline_sources = tuple(fit_pairs[("baseline", seed)] for seed in range(1000, 1005))
        baselines.append(R.Experiment2ABaselineSources(unit, baseline_sources))
        validation = unit_id in validation_ids
        source_label = tmp_path / "exports-original" / unit_id / "label.json"
        copy_label = tmp_path / "exports-copy" / unit_id / "label.json"
        label_bytes = (json.dumps({"fixture": unit_id}) + "\n").encode("utf-8")
        source_label.write_bytes(label_bytes)
        copy_label.write_bytes(label_bytes)
        record = _label_record(unit, path=source_label, validation=validation, index=index)
        records[source_label.resolve()] = record
        records[copy_label.resolve()] = deepcopy(record)
        seeds = range(1000, 1020) if validation else range(1000, 1003)
        conditions = []
        for seed in seeds:
            for role in ("baseline", "data_repair", "feature_repair"):
                if (role, seed) not in fit_pairs:
                    fit_pairs[(role, seed)] = pair(unit, role, seed)
            conditions.append(
                R.Experiment2ARepairConditionSources(
                    seed=seed,
                    baseline=fit_pairs[("baseline", seed)],
                    data_repair=fit_pairs[("data_repair", seed)],
                    feature_repair=fit_pairs[("feature_repair", seed)],
                )
            )
        label_args = (
            unit,
            source_label,
            copy_label,
            sha256_file(source_label),
            sha256_file(copy_label),
            tuple(conditions),
        )
        if validation:
            validation_sources.append(R.RepairValidationLabelSource(*label_args))
        else:
            ordinary_sources.append(R.OrdinaryLabelSource(*label_args))

    state = SimpleNamespace(
        baselines=tuple(baselines),
        validation=tuple(validation_sources),
        ordinary=tuple(ordinary_sources),
        records=records,
        report_path=tmp_path / "report" / "experiment_2a_report.json",
        project_root=tmp_path.resolve(),
        fit_metadata=fit_metadata,
        fit_load_calls=[],
        diagnostic_calls=[],
        validation_derive_calls=[],
        validation_load_calls=[],
        ordinary_load_calls=[],
    )

    def diagnostics(sources, *, unit):
        state.diagnostic_calls.append((unit, tuple(sources)))
        return _diagnostic(unit, sources)

    def fit_loader(path, *, expected_git_commit=None):
        resolved = Path(path).resolve()
        state.fit_load_calls.append((resolved, expected_git_commit))
        unit, arm, seed, pins = state.fit_metadata[resolved]
        if expected_git_commit != pins.expected_git_commit:
            raise ValueError("fabricated independent commit pin mismatch")
        unit_id = Config(unit=unit).unit_id
        return F.VerifiedFitEvidence(
            fit_dir=resolved,
            unit=unit,
            arm=arm,
            seed=seed,
            roles=("exp2a", "repair_validation", "exp3_repairs"),
            execution_stage="exp2a",
            unit_id=unit_id,
            config_id=f"{unit_id}-{arm}",
            fit_id=_fit_id(unit_id, arm, seed),
            execution_run_id=f"{unit_id}-{arm}-run-s{seed}",
            execution_digest=pins.expected_execution_digest,
            evaluation_pool_digest=_digest(f"pool:{unit_id}:{seed}"),
            diagnostics={},
            error=(),
            episode=(),
            step=(),
            scale=object(),
            n_train=1,
            ensemble_size=5 if arm == "baseline" else 1,
        )

    def derive(conditions, *, label_path):
        state.validation_derive_calls.append((tuple(conditions), Path(label_path).resolve()))
        return json.loads(json.dumps(state.records[Path(label_path).resolve()]))

    def validation_loader(path):
        state.validation_load_calls.append(Path(path).resolve())
        return json.loads(json.dumps(state.records[Path(path).resolve()]))

    def ordinary_loader(path, *, unit, conditions):
        state.ordinary_load_calls.append((Path(path).resolve(), unit, tuple(conditions)))
        return json.loads(json.dumps(state.records[Path(path).resolve()]))

    monkeypatch.setattr(R.H, "condition_failure_diagnostics", diagnostics)
    monkeypatch.setattr(R.F, "load_fit_evidence", fit_loader)
    monkeypatch.setattr(R.L, "_derive_label_evidence", derive)
    monkeypatch.setattr(R.L, "load_label_evidence", validation_loader)
    monkeypatch.setattr(R.O, "load_ordinary_label_evidence", ordinary_loader)
    return state


def _write(state):
    return R.write_experiment_2a_report(
        state.baselines,
        state.validation,
        state.ordinary,
        report_path=state.report_path,
    )


def _rehash_report(document):
    source_payload = {
        key: document["source_manifests"][key]
        for key in ("baseline_diagnostics", "repair_validation_labels", "ordinary_labels")
    }
    document["source_manifests"]["source_inventory_sha256"] = R._hash(source_payload)
    document["sign_consistency_evidence_gate"] = R._sign_consistency_evidence_gate(
        document["units"], document["source_manifests"]
    )
    document["payload_sha256"] = R._hash(
        {key: value for key, value in document.items() if key != "payload_sha256"}
    )
    return document


def _tampered_path(state, document, name):
    path = state.project_root / "tampered" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_writer_reopens_exact_inventory_and_emits_complete_family_report(synthetic):
    path = _write(synthetic)
    digest = sha256_file(path)
    report = R.load_experiment_2a_report(path, expected_sha256=digest)
    assert len(synthetic.diagnostic_calls) == 40
    assert len(synthetic.fit_load_calls) == 2 * 384
    assert {commit for _, commit in synthetic.fit_load_calls} == {COMMIT}
    assert len(synthetic.validation_derive_calls) == 8
    assert len(synthetic.validation_load_calls) == 8
    assert len(synthetic.ordinary_load_calls) == 32
    assert report["registered_inventory"] == {
        "unit_count": 20,
        "configuration_count": 5,
        "confound_levels": list(K.CONFOUND_LEVELS_2A),
        "baseline_seed_count_per_unit": 5,
        "baseline_source_count": 100,
        "repair_validation_label_count": 4,
        "ordinary_label_count": 16,
        "label_fit_reference_count": 384,
        "seeds": list(range(1000, 1005)),
    }
    assert len(report["units"]) == 20
    assert len(report["source_manifests"]["baseline_diagnostics"]) == 100
    assert all(
        row["source_path"] != row["copy_path"]
        and row["source_verified_execution_digest"]
        == row["copy_verified_execution_digest"]
        == row["expected_execution_digest"]
        for row in report["source_manifests"]["baseline_diagnostics"]
    )
    assert sum(
        len(row["fit_sources"])
        for key in ("repair_validation_labels", "ordinary_labels")
        for row in report["source_manifests"][key]
    ) == 384
    assert all(
        ref["source_path"] != ref["copy_path"]
        and ref["source_verified_execution_digest"]
        == ref["copy_verified_execution_digest"]
        == ref["expected_execution_digest"]
        and ref["expected_git_commit"] == COMMIT
        for key in ("repair_validation_labels", "ordinary_labels")
        for label in report["source_manifests"][key]
        for ref in label["fit_sources"]
    )
    assert report["h2_verdict"] is None and report["sign_consistency"] is None
    assert report["exposure_disclosure"] == {
        "reporting_spec_status": (
            "disclosed_post_outcome_post_collection_reporting_spec"
        ),
        "smoke_experiment_2a_label_known_before_specification": True,
        "pristine_preregistration_claimed": False,
    }


def test_report_keeps_seed_ratios_sample_sd_correlations_and_joined_labels(synthetic):
    report = R.replay_experiment_2a_report(
        _write(synthetic), expected_sha256=sha256_file(synthetic.report_path)
    )
    for row in report["units"]:
        seed_rows = row["h2_diagnostics"]["per_seed"]
        assert [item["seed"] for item in seed_rows] == list(range(1000, 1005))
        mean, sd = R._mean_sd([item["ratio_of_means"] for item in seed_rows])
        assert row["h2_diagnostics"]["ratio_mean_across_seeds"] == mean
        assert row["h2_diagnostics"]["ratio_sample_sd_across_seeds"] == sd
        assert all(
            item["observed_repair_label"]
            == row["repair_evidence"]["observed_label"]
            for item in seed_rows
        )
        assert any(
            item["pearson_r"] is None for item in seed_rows
        ) or all(item["pearson_r"] is not None for item in seed_rows)
        assert row["h2_verdict"] is None


def test_counts_preserve_all_four_outcomes_and_intended_class_is_separate(synthetic):
    report = R.load_experiment_2a_report(
        _write(synthetic), expected_sha256=sha256_file(synthetic.report_path)
    )
    assert report["counts"]["pooled"] == {
        "attempted": 20,
        "observed_0": 5,
        "observed_1": 5,
        "ambiguous": 5,
        "undiagnosed": 5,
        "decidable": 10,
        "excluded": 10,
        "exclusion_rate": 0.5,
    }
    assert report["counts"]["by_intended_class"]["estimation"]["attempted"] == 0
    assert report["counts"]["by_intended_class"]["estimation"]["exclusion_rate"] is None
    assert report["counts"]["by_intended_class"]["hypothesis_class"] == report["counts"]["pooled"]
    assert report["sign_consistency_status"] == "not_applied_in_experiment_2a_family_report"


def test_p1_sign_gate_binds_complete_labels_diagnostics_ratios_and_masks(synthetic):
    report = R.load_experiment_2a_report(
        _write(synthetic), expected_sha256=sha256_file(synthetic.report_path)
    )
    gate = report["sign_consistency_evidence_gate"]
    assert gate == R._sign_consistency_evidence_gate(
        report["units"], report["source_manifests"]
    )
    assert gate["registered_unit_count"] == 20
    assert gate["label_record_count"] == 20
    assert gate["diagnostic_row_count"] == 100
    assert gate["ambiguous_and_undiagnosed_retained"] is True
    assert gate["label_record_digests_bound"] is True
    assert gate["source_pins_bound"] is True
    assert gate["ratio_and_failure_mask_digests_bound"] is True
    assert gate["caller_constructed_eligible_rows_accepted"] is False
    assert gate["eligible_row_adapter_invoked"] is False
    assert gate["sign_consistency_invoked"] is False
    assert len(gate["complete_inventory_sha256"]) == 64
    assert report["sign_consistency"] is None


def test_real_evidence_road_has_no_caller_constructed_eligible_rows(synthetic):
    signature = inspect.signature(R.write_experiment_2a_report)
    assert set(signature.parameters) == {
        "baseline_sources", "repair_validation_labels", "ordinary_labels", "report_path"
    }
    source = inspect.getsource(R)
    assert "from .h2_sign_consistency" not in source
    assert "compute_h2_sign_consistency(" not in source
    with pytest.raises(ValueError):
        R.write_experiment_2a_report(
            synthetic.baselines,
            synthetic.validation,
            synthetic.ordinary[:-1],
            report_path=synthetic.report_path,
        )
    assert not synthetic.report_path.exists()


def test_scheduled_checks_are_descriptive_and_make_no_data_sweep_claim(synthetic):
    report = R.load_experiment_2a_report(
        _write(synthetic), expected_sha256=sha256_file(synthetic.report_path)
    )
    checks = report["scheduled_checks"]
    assert checks["strict_failure_set"]["total_unit_seed_rows"] == 100
    assert checks["strict_failure_set"]["all_unit_seed_rows_have_failures"] is True
    assert checks["ten_times_data_repair"]["assumed_outcome"] is False
    assert checks["feature_restoration"]["assumed_outcome"] is False
    assert checks["low_ratio"]["absolute_cutoff"] is None
    assert checks["low_ratio"]["adjudicated"] is False
    assert checks["data_size_sweep_claim_made"] is False


@pytest.mark.parametrize("kind", ["baseline-short", "baseline-duplicate", "validation-short", "ordinary-short", "raw"])
def test_public_writer_refuses_incomplete_duplicate_or_raw_inventories(synthetic, kind):
    baselines, validation, ordinary = synthetic.baselines, synthetic.validation, synthetic.ordinary
    if kind == "baseline-short":
        baselines = baselines[:-1]
    elif kind == "baseline-duplicate":
        baselines = (baselines[1],) + baselines[1:]
    elif kind == "validation-short":
        validation = validation[:-1]
    elif kind == "ordinary-short":
        ordinary = ordinary[:-1]
    else:
        baselines = ({"unit": baselines[0].unit, "sources": baselines[0].sources},) + baselines[1:]
    with pytest.raises(ValueError):
        R.write_experiment_2a_report(
            baselines, validation, ordinary, report_path=synthetic.report_path
        )
    assert not synthetic.report_path.exists()


def test_wrong_label_policy_is_refused_before_publication(synthetic):
    source = synthetic.ordinary[0]
    forged = R.RepairValidationLabelSource(
        source.unit,
        source.source_path,
        source.copy_path,
        source.expected_source_sha256,
        source.expected_copy_sha256,
        tuple(),
    )
    with pytest.raises(ValueError, match="wrong-policy|twenty-seed"):
        R.write_experiment_2a_report(
            synthetic.baselines,
            (forged,) + synthetic.validation[1:],
            synthetic.ordinary,
            report_path=synthetic.report_path,
        )
    assert not synthetic.report_path.exists()


def test_changed_label_file_is_refused_before_any_report(synthetic):
    source = synthetic.ordinary[0]
    source.source_path.write_bytes(b"changed fixture bytes\n")
    with pytest.raises(ValueError, match="SHA-256"):
        _write(synthetic)
    assert not synthetic.report_path.exists()


def test_label_record_must_bind_same_explicit_baseline_fit_pair(synthetic):
    source = synthetic.ordinary[0]
    for path in (source.source_path, source.copy_path):
        synthetic.records[path.resolve()]["runs"][0]["baseline"]["fit_id"] = "different-fit"
    with pytest.raises(ValueError, match="explicit original/copy fit source"):
        _write(synthetic)
    assert not synthetic.report_path.exists()


def test_existing_report_never_bypasses_source_reverification(synthetic, monkeypatch):
    path = _write(synthetic)
    before = path.read_bytes()
    monkeypatch.setattr(
        R.H,
        "condition_failure_diagnostics",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("changed fit source")),
    )
    with pytest.raises(ValueError, match="changed fit source"):
        _write(synthetic)
    assert path.read_bytes() == before


def test_load_and_replay_are_strictly_offline(synthetic, monkeypatch):
    path = _write(synthetic)
    digest = sha256_file(path)
    monkeypatch.setattr(R.H, "condition_failure_diagnostics", lambda *a, **k: pytest.fail("fit opened"))
    monkeypatch.setattr(R.L, "load_label_evidence", lambda *a, **k: pytest.fail("label opened"))
    monkeypatch.setattr(R.O, "load_ordinary_label_evidence", lambda *a, **k: pytest.fail("label opened"))
    loaded = R.load_experiment_2a_report(path, expected_sha256=digest)
    replayed = R.replay_experiment_2a_report(path, expected_sha256=digest)
    assert loaded == replayed


def test_report_digest_and_payload_validation_refuse_tampering(synthetic, tmp_path):
    path = _write(synthetic)
    with pytest.raises(ValueError, match="externally supplied"):
        R.load_experiment_2a_report(path, expected_sha256="f" * 64)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["h2_verdict"] = True
    document["payload_sha256"] = R._hash(
        {key: value for key, value in document.items() if key != "payload_sha256"}
    )
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="H2 verdict"):
        R.load_experiment_2a_report(tampered, expected_sha256=sha256_file(tampered))


def test_replay_recomputes_exact_ratio_of_means(synthetic):
    document = json.loads(_write(synthetic).read_text(encoding="utf-8"))
    diagnostic = document["units"][0]["h2_diagnostics"]
    diagnostic["per_seed"][0]["ratio_of_means"] += 0.125
    ratios = [row["ratio_of_means"] for row in diagnostic["per_seed"]]
    diagnostic["ratio_mean_across_seeds"], diagnostic["ratio_sample_sd_across_seeds"] = (
        R._mean_sd(ratios)
    )
    path = _tampered_path(synthetic, _rehash_report(document), "wrong-ratio.json")
    with pytest.raises(ValueError, match="exact per-seed ratio of means"):
        R.load_experiment_2a_report(path, expected_sha256=sha256_file(path))


def test_replay_refuses_unregistered_pearson_undefined_reason(synthetic):
    document = json.loads(_write(synthetic).read_text(encoding="utf-8"))
    row = document["units"][0]["h2_diagnostics"]["per_seed"][0]
    row["pearson_r"] = None
    row["correlation_undefined_reason"] = "invented_after_results"
    path = _tampered_path(synthetic, _rehash_report(document), "wrong-pearson-reason.json")
    with pytest.raises(ValueError, match="exact registered reason"):
        R.load_experiment_2a_report(path, expected_sha256=sha256_file(path))


def test_replay_cross_binds_unit_label_digest_to_source_manifest(synthetic):
    document = json.loads(_write(synthetic).read_text(encoding="utf-8"))
    document["source_manifests"]["repair_validation_labels"][0]["record_digest"] = "e" * 64
    path = _tampered_path(synthetic, _rehash_report(document), "wrong-label-join.json")
    with pytest.raises(ValueError, match="unit label record/source-manifest"):
        R.load_experiment_2a_report(path, expected_sha256=sha256_file(path))


def test_writer_refuses_same_object_as_original_and_copy(synthetic):
    first = synthetic.baselines[0]
    pair = first.sources[0]
    forged_pair = replace(pair, copy_path=pair.source_path)
    forged = replace(first, sources=(forged_pair,) + first.sources[1:])
    with pytest.raises(ValueError, match="original and independent copy"):
        R.write_experiment_2a_report(
            (forged,) + synthetic.baselines[1:],
            synthetic.validation,
            synthetic.ordinary,
            report_path=synthetic.report_path,
        )
    assert not synthetic.report_path.exists()


def test_writer_refuses_changed_independent_label_copy(synthetic):
    source = synthetic.ordinary[0]
    source.copy_path.write_bytes(b"divergent independent label copy\n")
    with pytest.raises(ValueError, match="SHA-256|copy bytes differ"):
        _write(synthetic)
    assert not synthetic.report_path.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [("expected_execution_digest", "f" * 64), ("expected_git_commit", "b" * 40)],
)
def test_writer_refuses_changed_independent_fit_pin(synthetic, field, value):
    label = synthetic.ordinary[0]
    condition = label.conditions[0]
    changed = replace(condition.data_repair, **{field: value})
    forged_condition = replace(condition, data_repair=changed)
    forged_label = replace(label, conditions=(forged_condition,) + label.conditions[1:])
    with pytest.raises(ValueError, match="independent pins|commit pin mismatch"):
        R.write_experiment_2a_report(
            synthetic.baselines,
            synthetic.validation,
            (forged_label,) + synthetic.ordinary[1:],
            report_path=synthetic.report_path,
        )
    assert not synthetic.report_path.exists()


@pytest.mark.parametrize(
    ("mode", "attributes"),
    [
        (stat.S_IFLNK, 0),
        (stat.S_IFREG, getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)),
    ],
)
def test_lexical_source_guard_refuses_symlink_and_reparse_before_resolution(
    synthetic, monkeypatch, mode, attributes
):
    blocked = synthetic.ordinary[0].source_path
    original_lstat = Path.lstat

    def fake_lstat(self):
        if Path(self) == blocked:
            return SimpleNamespace(st_mode=mode, st_file_attributes=attributes, st_nlink=1)
        return original_lstat(self)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ValueError, match="symlink or reparse"):
        _write(synthetic)
    assert not synthetic.report_path.exists()


def test_writer_refuses_outside_project_output_before_publication(synthetic):
    outside = synthetic.project_root.parent / f"{synthetic.project_root.name}-outside.json"
    with pytest.raises(ValueError, match="inside project root"):
        R.write_experiment_2a_report(
            synthetic.baselines,
            synthetic.validation,
            synthetic.ordinary,
            report_path=outside,
        )
    assert not outside.exists()


def test_writer_refuses_outside_project_scientific_source(synthetic):
    first = synthetic.baselines[0]
    outside = synthetic.project_root.parent / f"{synthetic.project_root.name}-outside-fit"
    forged_pair = replace(first.sources[0], source_path=outside)
    forged = replace(first, sources=(forged_pair,) + first.sources[1:])
    with pytest.raises(ValueError, match="inside project root"):
        R.write_experiment_2a_report(
            (forged,) + synthetic.baselines[1:],
            synthetic.validation,
            synthetic.ordinary,
            report_path=synthetic.report_path,
        )
    assert not synthetic.report_path.exists()


def test_writer_output_must_be_disjoint_from_every_source_and_copy(synthetic):
    output = synthetic.baselines[0].sources[0].copy_path / "report.json"
    with pytest.raises(ValueError, match="disjoint from every evidence source"):
        R.write_experiment_2a_report(
            synthetic.baselines,
            synthetic.validation,
            synthetic.ordinary,
            report_path=output,
        )
    assert not output.exists()


def test_immutable_writer_is_idempotent_and_refuses_divergence(synthetic):
    path = _write(synthetic)
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    again = _write(synthetic)
    assert again == path
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    path.write_bytes(b"preserve divergent report\n")
    with pytest.raises(DivergentTargetError, match="different content"):
        _write(synthetic)
    assert path.read_bytes() == b"preserve divergent report\n"


def test_registered_input_is_exact_twenty_unit_grid():
    assert set(_ordered_units()) == set(experiment_2a_units())
    assert len(_ordered_units()) == 20
    validation_ids = R._validation_unit_ids()
    validation = {
        (unit.causal_attribute, unit.layout, float(unit.confound_rate))
        for unit in _ordered_units()
        if Config(unit=unit).unit_id in validation_ids
    }
    assert validation == {
        ("shape", "uniform", 0.25),
        ("shape", "uniform", 0.50),
        ("shape", "uniform", 0.75),
        ("shape", "uniform", 0.90),
    }
