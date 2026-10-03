"""Synthetic/pure tests for the additive Week-8 Experiment-2A inventory."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bu.config import Config
from bu.durable import read_json
from bu.experiments import week8_exp2a_repairs as W
from bu.experiments.enumerate_units import execution_plan, experiment_2a_units


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "inputs").mkdir()
    (root / "week7-production-control").mkdir()
    monkeypatch.setattr(W, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(
        W, "COMMON_LEASE_ROOT", root / "week7-production-control"
    )
    return root


def _resign(document):
    payload = {key: value for key, value in document.items() if key != "plan_digest"}
    document["plan_digest"] = W._seal(payload, "plan_digest")["plan_digest"]
    return document


def test_d160_uses_the_one_established_production_lease_namespace():
    assert W.COMMON_LEASE_ROOT == W.WORKSPACE_ROOT / "week7-production-control"
    assert W.COMMON_LEASE_NAME == "week7-production"


def test_exact_inventory_counts_and_models():
    plan = W.build_exp2a_repair_plan()
    assert plan["exp2a_repairs_schema_version"] == 2
    assert plan["counts"] == {
        "units": 20,
        "twenty_seed_units": 4,
        "three_seed_units": 16,
        "registered_physical_fits": 416,
        "total_model_trainings": 1056,
        "existing_fits_preserved": 155,
        "historical_model_trainings": 615,
        "week6_smoke_fits_preserved": 60,
        "week7_baseline_fits_preserved": 95,
        "existing_fits_required_by_labels": 123,
        "label_required_fits": 384,
        "new_baseline_fits": 45,
        "new_repair_fits": 216,
        "new_physical_fits": 261,
        "new_member_model_trainings": 441,
    }
    assert len(W.registered_exp2a_jobs()) == 416
    assert len(W.existing_exp2a_jobs()) == 155
    assert len(W.new_exp2a_jobs()) == 261
    assert len(W.label_required_exp2a_jobs()) == 384


def test_model_training_totals_are_rederived_from_exact_job_configs():
    plan = W.build_exp2a_repair_plan()
    registered = W.registered_exp2a_jobs()
    historical = W.existing_exp2a_jobs()
    new = W.new_exp2a_jobs()
    rederived = {
        "total_model_trainings": sum(
            job.config.train.ensemble_size for job in registered
        ),
        "historical_model_trainings": sum(
            job.config.train.ensemble_size for job in historical
        ),
        "new_member_model_trainings": sum(
            job.config.train.ensemble_size for job in new
        ),
    }
    assert rederived == {
        "total_model_trainings": 1056,
        "historical_model_trainings": 615,
        "new_member_model_trainings": 441,
    }
    assert {
        key: plan["counts"][key] for key in rederived
    } == rederived
    assert (
        rederived["historical_model_trainings"]
        + rederived["new_member_model_trainings"]
        == rederived["total_model_trainings"]
    )


def test_registered_jobs_are_exact_execution_plan_projection():
    original = {
        (Config(unit=fit.unit).unit_id, fit.arm, fit.seed + 1000): fit
        for fit in execution_plan(experiment_2a_units())
    }
    actual = {
        (job.config.unit_id, job.arm, job.seed): job
        for job in W.registered_exp2a_jobs()
    }
    assert set(actual) == set(original)
    assert all(actual[key].roles == original[key].roles for key in original)


def test_four_validation_and_sixteen_ordinary_label_policies_are_disjoint():
    plan = W.build_exp2a_repair_plan()
    validation = [row for row in plan["labels"] if row["label_stage"] == "repair_validation"]
    ordinary = [row for row in plan["labels"] if row["label_stage"] == "exp3_repairs"]
    assert len(validation) == 4
    assert len(ordinary) == 16
    assert {row["unit_id"] for row in validation} == {
        "d5baeb907ac3",
        "399e994df8b7",
        "8640549e3e88",
        "620b0668b967",
    }
    for row in validation:
        assert row["seeds"] == list(range(1000, 1020))
        assert len(row["required_fit_ids"]) == 60
        assert row["label_api"].endswith("label_evidence.build_label_evidence")
    for row in ordinary:
        assert row["seeds"] == [1000, 1001, 1002]
        assert len(row["required_fit_ids"]) == 9
        assert row["label_api"].endswith(
            "ordinary_label_evidence.build_ordinary_label_evidence"
        )


def test_only_baseline_data_and_feature_arms_are_present():
    jobs = W.registered_exp2a_jobs()
    assert {job.arm for job in jobs} == {
        "baseline",
        "data_repair",
        "feature_repair",
    }
    by_unit = {}
    for job in jobs:
        by_unit.setdefault(job.config.unit_id, set()).add(job.arm)
    assert all(arms == {"baseline", "data_repair", "feature_repair"} for arms in by_unit.values())


def test_full_configs_record_five_member_baselines_and_one_member_repairs():
    for job in W.registered_exp2a_jobs():
        record = job.as_record()
        assert Config.from_dict(record["config"]).to_dict() == record["config"]
        assert job.config.train.ensemble_size == (5 if job.arm == "baseline" else 1)
        assert record["fit_id"] == record["job_id"]
        assert record["run_id"] == job.config.run_id


def test_smoke_all_sixty_and_week7_only_ninety_five_are_existing():
    existing = W.existing_exp2a_jobs()
    smoke = [job for job in existing if W.source_kind(job) == "week6_smoke"]
    week7 = [job for job in existing if W.source_kind(job) == "week7_exp2a"]
    assert len(smoke) == 60
    assert {job.arm for job in smoke} == {"baseline", "data_repair", "feature_repair"}
    assert {job.seed for job in smoke} == set(range(1000, 1020))
    assert {job.config.unit_id for job in smoke} == {W.SMOKE_UNIT_ID}
    assert len(week7) == 95
    assert all(job.arm == "baseline" and 1000 <= job.seed <= 1004 for job in week7)
    assert W.SMOKE_UNIT_ID not in {job.config.unit_id for job in week7}


def test_new_inventory_is_fixed_and_baseline_precedes_repairs_per_seed():
    jobs = W.new_exp2a_jobs()
    assert not {job.job_id for job in jobs} & {
        job.job_id for job in W.existing_exp2a_jobs()
    }
    order = {"baseline": 0, "data_repair": 1, "feature_repair": 2}
    assert list(jobs) == sorted(
        jobs, key=lambda job: (job.config.unit_id, job.seed, order[job.arm])
    )
    by_unit_seed = {}
    for job in jobs:
        by_unit_seed.setdefault((job.config.unit_id, job.seed), []).append(job.arm)
    assert all(arms in (["baseline", "data_repair", "feature_repair"],
                        ["data_repair", "feature_repair"])
               for arms in by_unit_seed.values())


def test_label_required_set_is_exact_and_excludes_32_nonlabel_week7_baselines():
    required = {job.job_id for job in W.label_required_exp2a_jobs()}
    existing = {job.job_id for job in W.existing_exp2a_jobs()}
    new = {job.job_id for job in W.new_exp2a_jobs()}
    assert len(required & existing) == 123
    assert len(existing - required) == 32
    assert new <= required
    assert len(required) == 384


def test_plan_is_outcome_free_and_cannot_authorize_execution():
    plan = W.build_exp2a_repair_plan()
    assert plan["execution_authorized_by_this_file"] is False
    assert plan["replacement_training_allowed"] is False
    assert all(row["observed_label"] is None for row in plan["labels"])
    assert "run_confirmatory_fit" not in vars(W)


def test_plan_validation_rederives_semantics_even_after_resigning():
    plan = copy.deepcopy(W.build_exp2a_repair_plan())
    plan["counts"]["new_physical_fits"] = 262
    _resign(plan)
    with pytest.raises(ValueError, match="exact registered evidence"):
        W.validate_exp2a_repair_plan(plan)


def test_plan_write_is_immutable_and_load_rederives(workspace):
    path = W.write_exp2a_repair_plan(workspace / "inputs")
    assert W.load_exp2a_repair_plan(path) == W.build_exp2a_repair_plan()
    assert W.write_exp2a_repair_plan(workspace / "inputs") == path
    changed = read_json(path)
    changed["replacement_training_allowed"] = True
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError):
        W.load_exp2a_repair_plan(path)
    with pytest.raises(Exception):
        W.write_exp2a_repair_plan(workspace / "inputs")


def test_public_path_boundary_refuses_workspace_root_and_outside(workspace, tmp_path):
    with pytest.raises(ValueError, match="child"):
        W._project_path(workspace, directory=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="project-local"):
        W._project_path(outside, directory=True)
