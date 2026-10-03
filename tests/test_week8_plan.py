"""Configuration-only Week-8 plan tests; no fit or outcome is opened."""

from __future__ import annotations

import copy
import hashlib

import pytest

from bu.durable import DivergentTargetError
from bu.experiments import batch as B
from bu.experiments import week7_launch_plan as W7L
from bu.experiments import week7_plan as W7P
from bu.experiments import week8_plan as P


@pytest.fixture(scope="module")
def plan():
    return P.build_week8_launch_plan()


@pytest.fixture
def upstream(tmp_path):
    preparation = W7P.write_week7_plan(tmp_path / "preparation")
    launch = W7L.write_week7_launch_plan(
        tmp_path / "week7-launch", preparation_path=preparation
    )
    assert P.sha256_file(preparation) == P.WEEK7_PREPARATION_SHA256
    assert P.sha256_file(launch) == P.WEEK7_LAUNCH_PLAN_SHA256
    return preparation, launch


def _resign(document):
    payload = {key: value for key, value in document.items() if key != "plan_digest"}
    document["plan_digest"] = hashlib.sha256(P._canonical(payload)).hexdigest()


def test_exact_exp2b_grid_roles_models_and_train_spec(plan):
    jobs = P.experiment_2b_baseline_jobs()
    assert len(jobs) == len({job.job_id for job in jobs}) == 125
    assert len({job.config.unit_id for job in jobs}) == 25
    assert {job.seed for job in jobs} == set(range(1000, 1005))
    assert sum(job.config.train.ensemble_size for job in jobs) == 625
    assert {job.config.train.batch_size for job in jobs} == {128}
    assert {job.roles for job in jobs} == set(P.EXP2B_ALLOWED_ROLE_TUPLES)
    assert sum(job.roles == ("exp2b", "repair_validation") for job in jobs) == 25
    assert sum(job.roles == ("exp2b",) for job in jobs) == 100
    assert all(
        job.unit.causal_attribute == "shape" and job.unit.layout == "uniform"
        for job in jobs
        if job.roles == ("exp2b", "repair_validation")
    )
    expected_configs = {
        "4446e283c4a5", "b1715a244748", "e1faeca85156", "f73d6162bc18", "0953d94ae32c",
        "b798cf8250ec", "7cf3d4fe7858", "1fd93ed4088f", "f221f217d975", "7962a80bc490",
        "e083075ea28c", "449eb29b248c", "9bb534e5d15a", "5fe8c2c76e9b", "7d33f2cc7ca0",
        "ed991bfc9876", "db49a0bad715", "25f5fcb1b845", "2031b484ae85", "06b72301e432",
        "6e95ba0d6da7", "b9c8685eb187", "542ad2448932", "fd9cd40f4b87", "9aabbff1d3be",
    }
    assert {job.config.config_id for job in jobs} == expected_configs
    assert plan["batches"]["exp2b"]["jobs"] == [job.as_record() for job in jobs]


def test_three_role_registry_drift_is_refused(monkeypatch):
    original = P.execution_plan

    def drifted(units):
        fits = list(original(units))
        index = next(
            index
            for index, fit in enumerate(fits)
            if fit.arm == "baseline" and fit.roles == ("exp2b",)
        )
        fit = fits[index]
        fits[index] = type(fit)(
            unit=fit.unit,
            arm=fit.arm,
            seed=fit.seed,
            roles=("exp2a", "exp2b", "repair_validation"),
        )
        return tuple(fits)

    monkeypatch.setattr(P, "execution_plan", drifted)
    with pytest.raises(ValueError, match="inventory drifted"):
        P.experiment_2b_baseline_jobs()


def test_sweep_002_is_exact_second_whole_group_and_nothing_else(plan):
    jobs = P.sweep_002_baseline_jobs()
    assert tuple(job.job_id for job in jobs) == tuple(
        f"eab7f1b3a520-s{seed}" for seed in range(1000, 1003)
    )
    assert {job.config.unit_id for job in jobs} == {"029dd4484382"}
    assert {job.roles for job in jobs} == {("config_sweep",)}
    assert sum(job.config.train.ensemble_size for job in jobs) == 15
    assert plan["batches"]["sweep-002"]["comparison_group_id"] == "029dd4484382"
    assert plan["batches"]["sweep-002"]["jobs"] == [job.as_record() for job in jobs]


def test_plan_totals_upstream_pins_and_bounded_keys(plan):
    assert plan["authorized_batch_keys"] == ["exp2b", "sweep-002"]
    assert set(plan["batches"]) == {"exp2b", "sweep-002"}
    assert (plan["fit_count"], plan["member_model_count"]) == (128, 640)
    assert plan["confirmatory_train_batch_size"] == 128
    assert plan["week7_plan_modified"] is False
    assert plan["upstream"]["week7_preparation"]["file_sha256"] == P.WEEK7_PREPARATION_SHA256
    assert plan["upstream"]["week7_launch_plan"]["file_sha256"] == P.WEEK7_LAUNCH_PLAN_SHA256
    assert plan["scientific_analysis_performed"] is False


@pytest.mark.parametrize(
    "key", ["exp2a", "sweep-001", "sweep-003", "exp2b ", "", None, True, 2]
)
def test_batch_scope_cannot_expand(plan, key):
    with pytest.raises(ValueError, match="only exp2b and sweep-002"):
        P.jobs_for_batch(plan, key)


@pytest.mark.parametrize(
    "mutation",
    ["job", "role", "seed", "batch", "count", "upstream", "train", "extra", "schema"],
)
def test_even_resigned_plan_forgery_refuses(plan, mutation):
    forged = copy.deepcopy(plan)
    if mutation == "job":
        forged["batches"]["exp2b"]["jobs"].pop()
    elif mutation == "role":
        row = forged["batches"]["exp2b"]["jobs"][0]
        row["roles"] = (
            ["exp2b", "repair_validation"]
            if row["roles"] == ["exp2b"]
            else ["exp2b"]
        )
    elif mutation == "seed":
        forged["batches"]["sweep-002"]["jobs"][0]["seed"] = 1003
    elif mutation == "batch":
        forged["authorized_batch_keys"].append("sweep-003")
    elif mutation == "count":
        forged["fit_count"] = 129
    elif mutation == "upstream":
        forged["upstream"]["week7_launch_plan"]["file_sha256"] = "0" * 64
    elif mutation == "train":
        forged["batches"]["exp2b"]["jobs"][0]["config"]["train"]["batch_size"] = 256
    elif mutation == "extra":
        forged["outcome"] = "never allowed"
    else:
        forged["week8_plan_schema_version"] = True
    _resign(forged)
    with pytest.raises(ValueError, match="exact registered inventory"):
        P.validate_week8_launch_plan(forged)


def test_immutable_publish_reopens_both_frozen_upstreams(tmp_path, upstream, plan):
    preparation, launch = upstream
    directory = tmp_path / "week8"
    path = P.write_week8_launch_plan(
        directory,
        preparation_path=preparation,
        week7_launch_plan_path=launch,
    )
    assert P.load_week8_launch_plan(
        path,
        preparation_path=preparation,
        week7_launch_plan_path=launch,
    ) == plan
    before = path.read_bytes(), path.stat().st_mtime_ns
    assert P.write_week8_launch_plan(
        directory,
        preparation_path=preparation,
        week7_launch_plan_path=launch,
    ) == path
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(DivergentTargetError):
        P.write_week8_launch_plan(
            directory,
            preparation_path=preparation,
            week7_launch_plan_path=launch,
        )


def test_plan_cli_publishes_the_exact_no_compute_document(tmp_path, upstream, plan):
    preparation, launch = upstream
    directory = tmp_path / "cli-plan"
    assert P.main([
        "--directory", str(directory),
        "--preparation-path", str(preparation),
        "--week7-launch-plan-path", str(launch),
    ]) == 0
    path = directory / P.WEEK8_PLAN_FILE
    assert P.load_week8_launch_plan(
        path,
        preparation_path=preparation,
        week7_launch_plan_path=launch,
    ) == plan


@pytest.mark.parametrize("which", ["preparation", "launch"])
def test_missing_or_changed_upstream_refuses_before_publication(tmp_path, upstream, which):
    preparation, launch = upstream
    target = preparation if which == "preparation" else launch
    target.write_bytes(target.read_bytes() + b"\n")
    output = tmp_path / "not-created"
    with pytest.raises(ValueError, match="frozen SHA-256"):
        P.write_week8_launch_plan(
            output,
            preparation_path=preparation,
            week7_launch_plan_path=launch,
        )
    assert not output.exists()


def test_plan_derivation_never_invokes_executor(monkeypatch, plan):
    monkeypatch.setattr(
        B, "_default_executor", lambda *a, **k: pytest.fail("plan launched a fit")
    )
    assert len(P.jobs_for_batch(plan, "exp2b")) == 125
    assert len(P.jobs_for_batch(plan, "sweep-002")) == 3
