"""Configuration-only Week-7 launch tests; never open scientific outcomes."""

from __future__ import annotations

import copy
import hashlib

import pytest

from bu.durable import DivergentTargetError, atomic_write_json
from bu.experiments import week7_launch_plan as P
from bu.experiments import week7_plan as W
from bu.streams import group_of
from bu.experiments.enumerate_units import stage_of


@pytest.fixture(scope="module")
def plan():
    return P.build_week7_launch_plan()


@pytest.fixture
def preparation(tmp_path):
    return W.write_week7_plan(tmp_path / "preparation")


def _resign(document):
    payload = {k: v for k, v in document.items() if k != "plan_digest"}
    document["plan_digest"] = hashlib.sha256(P._canonical(payload)).hexdigest()


def test_all100_requirements_partition_into_fixed5_reused_and95_new(plan):
    reused = P.reused_experiment_2a_jobs()
    new = P.new_experiment_2a_jobs()
    assert len(reused) == 5 and len(new) == 95
    assert tuple(j.job_id for j in reused) == P.REUSED_FIT_IDS
    assert {j.roles for j in reused} == {("exp2a", "repair_validation")}
    assert not set(j.job_id for j in reused).intersection(j.job_id for j in new)
    assert sorted(j.job_id for j in reused + new) == plan["exp2a_required_fit_ids"]
    assert {j.seed for j in reused} == set(range(1000, 1005))
    assert plan["replacement_training_allowed"] is False
    assert plan["source_reconciliation_required"] is True
    assert plan["reused_fits_belong_in_new_batch_directories"] is False


def test_all675_sweep_jobs_have_unique_total_group_preserving_order(plan):
    batches = P.sweep_baseline_batches()
    assert len(batches) == 225
    flattened = tuple(j for batch in batches for j in batch)
    assert len(flattened) == len({j.job_id for j in flattened}) == 675
    assert {j.job_id for j in flattened} == {j.job_id for j in W.configuration_sweep_baseline_jobs()}
    keys = [group_of(batch[0].unit, stage_of(batch[0].unit)) for batch in batches]
    assert keys == sorted(keys)
    assert len(set(keys)) == 225
    for number, batch in enumerate(batches, 1):
        assert tuple(j.seed for j in batch) == (1000, 1001, 1002)
        assert len({j.config.unit_id for j in batch}) == 1
        assert plan["batches"][f"sweep-{number:03d}"]["jobs"] == [j.as_record() for j in batch]
        assert plan["batches"][f"sweep-{number:03d}"]["contemporaneous_anchors_required"] is True


def test_first_group_is_fixed_without_outcomes_and_later672_remain_owed(plan):
    first = P.jobs_for_batch(plan, "sweep-001")
    assert tuple(j.job_id for j in first) == tuple(f"cc428cf4ab47-s{s}" for s in range(1000, 1003))
    assert first[0].config.unit_id == "0184fbfcd8b9"
    assert first[0].unit.causal_attribute == "position"
    assert first[0].unit.hidden_size == 64
    assert first[0].unit.confound_rate == 0.9
    assert len(P.jobs_for_batch(plan, "exp2a")) == 95
    assert plan["authorized_batch_keys"] == ["exp2a", "sweep-001"]
    assert plan["initial_new_fit_count"] == 98
    assert plan["remaining_sweep_fit_count_after_initial_batch"] == 672
    assert len(plan["batches"]) == 226


@pytest.mark.parametrize("batch", ["sweep-002", "sweep-225", "sweep-000", "sweep-1", "exp1", "exp2a ", None, True, 1])
def test_batch_scope_is_not_caller_expandable(plan, batch):
    with pytest.raises(ValueError, match="only exp2a and sweep-001"):
        P.jobs_for_batch(plan, batch)


@pytest.mark.parametrize("mutation", [
    "train", "role", "reuse", "replace_reuse", "missing_job", "duplicate_job",
    "seed", "reorder_group", "split_group", "last_group", "enable_later",
    "extra_field", "bool_schema", "float_count", "preparation_digest",
])
def test_resigned_full_document_forgery_refused(plan, mutation):
    forged = copy.deepcopy(plan)
    new = forged["batches"]["exp2a"]["jobs"]
    if mutation == "train":
        new[0]["config"]["train"]["lr"] *= 2
    elif mutation == "role":
        new[0]["roles"] = ["exp2a", "repair_validation"]
    elif mutation == "reuse":
        forged["reused_exp2a_jobs"].pop()
    elif mutation == "replace_reuse":
        new.append(forged["reused_exp2a_jobs"].pop())
    elif mutation == "missing_job":
        new.pop()
    elif mutation == "duplicate_job":
        new[-1] = new[0]
    elif mutation == "seed":
        new[0]["config"]["seed"] = 1005
    elif mutation == "reorder_group":
        a, b = forged["batches"]["sweep-001"], forged["batches"]["sweep-002"]
        a["jobs"], b["jobs"] = b["jobs"], a["jobs"]
    elif mutation == "split_group":
        a, b = forged["batches"]["sweep-001"]["jobs"], forged["batches"]["sweep-002"]["jobs"]
        a[0], b[0] = b[0], a[0]
    elif mutation == "last_group":
        forged["batches"]["sweep-225"]["jobs"][0]["config"]["train"]["lr"] *= 2
    elif mutation == "enable_later":
        forged["authorized_batch_keys"].append("sweep-002")
        forged["batches"]["sweep-002"]["in_current_scope"] = True
    elif mutation == "extra_field":
        forged["replacement_reason"] = "missing_history"
    elif mutation == "bool_schema":
        forged["week7_launch_plan_schema_version"] = True
    elif mutation == "float_count":
        forged["initial_new_fit_count"] = 98.0
    else:
        forged["preparation"]["file_sha256"] = "a" * 64
    _resign(forged)
    with pytest.raises(ValueError, match="exact registered inventory"):
        P.validate_week7_launch_plan(forged)


@pytest.mark.parametrize("value", [None, [], True, "plan", {"bad": float("nan")}])
def test_malformed_plan_refused(value):
    with pytest.raises(ValueError):
        P.validate_week7_launch_plan(value)


def test_immutable_publish_roundtrip_and_equal_retry(tmp_path, preparation, plan):
    directory = tmp_path / "output"
    path = P.write_week7_launch_plan(directory, preparation_path=preparation)
    assert P.load_week7_launch_plan(path, preparation_path=preparation) == plan
    before = path.read_bytes(), path.stat().st_mtime_ns
    assert P.write_week7_launch_plan(directory, preparation_path=preparation) == path
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    path.write_text('{}\n', encoding="utf-8")
    with pytest.raises(DivergentTargetError):
        P.write_week7_launch_plan(directory, preparation_path=preparation)
    assert path.read_text() == '{}\n'


def test_missing_or_reformatted_frozen_preparation_cannot_create_plan(tmp_path, preparation):
    output = tmp_path / "not-created"
    with pytest.raises(ValueError):
        P.write_week7_launch_plan(output, preparation_path=tmp_path / "absent")
    assert not output.exists()
    preparation.write_bytes(preparation.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="frozen SHA-256"):
        P.write_week7_launch_plan(output, preparation_path=preparation)
    assert not output.exists()


def test_load_uses_fixed_preparation_default(monkeypatch, preparation, tmp_path, plan):
    monkeypatch.setattr(P, "PREPARATION_PATH", preparation)
    path = atomic_write_json(tmp_path / P.WEEK7_LAUNCH_PLAN_FILE, plan)
    assert P.load_week7_launch_plan(path) == plan


def test_registry_train_field_drift_is_caught_without_files(monkeypatch):
    original = W.build_week7_plan
    def drifted():
        document = original()
        document["stages"]["exp2a"]["jobs"][0]["config"]["train"]["lr"] *= 2
        return document
    monkeypatch.setattr(W, "build_week7_plan", drifted)
    with pytest.raises(ValueError, match="frozen SHA-256"):
        P.build_week7_launch_plan()


def test_plan_selection_never_invokes_executor(monkeypatch, plan):
    from bu.experiments import batch as B
    def forbidden(*args, **kwargs):
        pytest.fail("configuration selection invoked training")
    monkeypatch.setattr(B, "_default_executor", forbidden)
    all_new = P.jobs_for_batch(plan, "exp2a") + P.jobs_for_batch(plan, "sweep-001")
    assert len(all_new) == 98
    assert not set(P.REUSED_FIT_IDS).intersection(j.job_id for j in all_new)
