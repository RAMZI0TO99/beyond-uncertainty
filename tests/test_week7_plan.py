"""Preparation-only Week-7 checks: no fitting or real evidence access."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from bu.config import Config
from bu.durable import DivergentTargetError, DurabilityError
from bu.experiments import week7_plan as W
from bu.experiments.batch import experiment_1_jobs
from bu.experiments.repair_label_run import registered_week6_smoke_unit


def test_exp2a_is_exact_grid_and_preserves_all_roles():
    jobs = W.experiment_2a_jobs()
    assert len(jobs) == 100
    assert len({j.config.unit_id for j in jobs}) == 20
    assert {j.seed for j in jobs} == set(range(1000, 1005))
    assert {j.unit.confound_rate for j in jobs} == {0.25, 0.5, 0.75, 0.9}
    assert {j.unit.n_transitions for j in jobs} == {5000}
    assert {j.arm for j in jobs} == {"baseline"}
    assert sum(len(j.roles) == 2 for j in jobs) == 20
    assert {j.roles for j in jobs} == {("exp2a",), ("exp2a", "repair_validation")}
    assert all(j.unit.withheld_features == (j.unit.causal_attribute,) for j in jobs)


def test_sweep_preserves_registered225_not_full_pool_or_reserve():
    jobs = W.configuration_sweep_baseline_jobs()
    assert len(jobs) == 675
    assert len({j.config.unit_id for j in jobs}) == 225
    assert {j.seed for j in jobs} == {1000, 1001, 1002}
    assert {j.roles for j in jobs} == {("config_sweep",)}
    assert {j.arm for j in jobs} == {"baseline"}
    canonical = {j.job_id for j in W.experiment_2a_jobs() + experiment_1_jobs()}
    assert not canonical.intersection(j.job_id for j in jobs)


def test_existing_smoke_overlap_is_required_not_silently_relaunched_or_removed():
    unit = registered_week6_smoke_unit()
    shared = [j for j in W.experiment_2a_jobs() if j.unit == unit]
    assert len(shared) == 5
    assert {j.seed for j in shared} == set(range(1000, 1005))
    assert {j.roles for j in shared} == {("exp2a", "repair_validation")}
    plan = W.build_week7_plan()
    assert plan["execution_authorized"] is False
    assert plan["prior_completion_checked"] is False
    assert plan["sweep_batch_partition"] is None
    assert plan["repair_assignments_added"] is False
    assert "batch_id" not in plan


def test_manifest_every_config_roundtrips_and_digest_binds_all_fields():
    plan = W.build_week7_plan()
    assert W.build_week7_plan() == plan
    payload = {k: v for k, v in plan.items() if k != "plan_digest"}
    assert hashlib.sha256(W._canonical(payload)).hexdigest() == plan["plan_digest"]
    assert set(plan["stages"]) == {"exp2a", "config_sweep"}
    for stage in plan["stages"].values():
        for row in stage["jobs"]:
            cfg = Config.from_dict(row["config"])
            assert cfg.to_dict() == row["config"]
            assert cfg.fit_id == row["fit_id"] == row["job_id"]
            assert cfg.unit_id == row["unit_id"]


@pytest.mark.parametrize("field,value", [
    ("execution_authorized", True),
    ("execution_authorized", 0),
    ("week7_plan_schema_version", True),
    ("week7_plan_schema_version", 1.0),
    ("sweep_batch_partition", [10, 215]),
    ("prior_completion_checked", True),
    ("new_field", "no"),
])
def test_resigned_metadata_drift_is_rejected(field, value):
    plan = W.build_week7_plan()
    plan[field] = value
    payload = {k: v for k, v in plan.items() if k != "plan_digest"}
    plan["plan_digest"] = hashlib.sha256(W._canonical(payload)).hexdigest()
    with pytest.raises(ValueError, match="exact registered plan"):
        W.validate_week7_plan(plan)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "seed", "role", "train"])
def test_resigned_config_inventory_drift_is_rejected(mutation):
    plan = W.build_week7_plan()
    rows = plan["stages"]["exp2a"]["jobs"]
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows[-1] = rows[0]
    elif mutation == "seed":
        rows[0]["seed"] = 1005
    elif mutation == "role":
        rows[0]["roles"] = ["exp2a", "config_sweep"]
    else:
        rows[0]["config"]["train"]["lr"] *= 2
    payload = {k: v for k, v in plan.items() if k != "plan_digest"}
    plan["plan_digest"] = hashlib.sha256(W._canonical(payload)).hexdigest()
    with pytest.raises(ValueError, match="exact registered plan"):
        W.validate_week7_plan(plan)


@pytest.mark.parametrize("value", [None, [], "plan", {"bad": float("nan")}])
def test_malformed_document_fails_closed(value):
    with pytest.raises(ValueError):
        W.validate_week7_plan(value)


def test_registry_drift_stops_before_output(monkeypatch, tmp_path):
    original = W.execution_plan
    def broken(units):
        fits = list(original(units))
        i = next(i for i, f in enumerate(fits) if "exp2a" in f.roles)
        fits[i] = replace(fits[i], seed=6)
        return tuple(fits)
    monkeypatch.setattr(W, "execution_plan", broken)
    with pytest.raises(ValueError, match="drifted|inventory"):
        W.write_week7_plan(tmp_path / "not_created")
    assert not (tmp_path / "not_created").exists()


def test_publish_roundtrip_equal_retry_and_divergent_refusal(tmp_path):
    path = W.write_week7_plan(tmp_path)
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    assert W.load_week7_plan(path) == W.build_week7_plan()
    assert W.write_week7_plan(tmp_path) == path
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    # Synthetic corrupted target must survive the refused write unchanged.
    path.write_text('{}\n', encoding="utf-8")
    with pytest.raises(DivergentTargetError):
        W.write_week7_plan(tmp_path)
    assert path.read_text(encoding="utf-8") == '{}\n'


def test_missing_and_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / W.WEEK7_PLAN_FILE
    with pytest.raises(ValueError, match="regular"):
        W.load_week7_plan(path)
    path.write_text('{"x":1,"x":2}', encoding="utf-8")
    with pytest.raises(DurabilityError, match="duplicate"):
        W.load_week7_plan(path)


def test_cli_prepares_only(tmp_path, capsys):
    assert W.main(["--output-directory", str(tmp_path)]) == 0
    assert {p.name for p in tmp_path.iterdir()} == {W.WEEK7_PLAN_FILE}
    out = capsys.readouterr().out
    assert "No experiment launched" in out
    assert "100 Experiment-2A and 675" in out
