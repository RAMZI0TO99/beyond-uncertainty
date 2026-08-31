"""Synthetic-only checks: never open historical payloads or train a model.

Scientific fit loading is a typed in-memory double; real independent tiny
filesystem trees exercise path, digest, mutation and durable-copy boundaries.
The worker is tested by direct invocation with a fabricated supervisor record,
not by claiming these doubles are real confirmatory evidence.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest
import torch

from bu.config import Config
from bu.durable import DivergentTargetError, atomic_write_json, read_json, sha256_file
from bu.experiments import week7_exp1_repairs as W
from bu.experiments import batch as B
from bu.experiments import fit_evidence as F
from bu.experiments.enumerate_units import execution_plan, experiment_1_units
from bu.experiments.supervisor import acquire_batch_lease
from bu.models.uncertainty import NormalisationScale
from bu.runrecord import GitState, TRACKED_PACKAGES


COMMIT = "b" * 40


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(W, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(W, "COMMON_LEASE_ROOT", root / "control")
    monkeypatch.setattr(W, "HISTORICAL_JOBS_ROOT", root / "old" / "jobs")
    monkeypatch.setattr(W, "HISTORICAL_COPY_ROOT", root / "old-copy" / "jobs")
    monkeypatch.setattr(W, "HISTORICAL_REPORT_PATH", root / "old-analysis" / "report.json")
    for name in ("input", "output", "sync", "staging", "control"):
        (root / name).mkdir()
    return root


@pytest.fixture
def environment(monkeypatch):
    pins = {name: f"synthetic-{i}" for i, name in enumerate(TRACKED_PACKAGES)}
    monkeypatch.setattr(W.P, "_verify_environment",
                        lambda: (GitState(COMMIT, False, "test"), dict(pins), dict(pins)))
    monkeypatch.setattr(W.P, "_verify_device", lambda route: {
        "frozen_route": "cpu", "requested_route": route, "available": route == "cpu",
    })


class SyntheticFits:
    def __init__(self):
        self.entries = {}
        self.loads = []
        self.executions = []

    def persist(self, root, job, commit):
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        # Digest is synthetic provenance, not a claimed scientific sidecar.
        document = {"job": job.as_record(), "commit": commit}
        atomic_write_json(root / "fit_evidence.json", document)
        scale = NormalisationScale(torch.tensor([1.0 + job.seed / 10000, 2.0]), n_reference=10)
        digest = hashlib.sha256(W._canonical(document)).hexdigest()
        empty = np.asarray([1.0], dtype=np.float64)
        verified = F.VerifiedFitEvidence(
            fit_dir=root, unit=job.unit, arm=job.arm, seed=job.seed,
            roles=job.roles, execution_stage=job.stage, unit_id=job.config.unit_id,
            config_id=job.config.config_id, fit_id=job.job_id, execution_run_id=job.config.run_id,
            execution_digest=digest,
            evaluation_pool_digest=hashlib.sha256(f"pool:{job.config.unit_id}:{job.seed}".encode()).hexdigest(),
            diagnostics=MappingProxyType({}), error=empty, episode=np.asarray([0]), step=np.asarray([0]),
            scale=scale, n_train=job.config.effective_unit.n_transitions,
            ensemble_size=job.config.train.ensemble_size,
        )
        self.entries[root] = (commit, verified)
        return verified

    def load(self, path, *, expected_git_commit=None):
        root = Path(path).resolve()
        self.loads.append((root, expected_git_commit))
        if not (root / "fit_evidence.json").is_file() or root not in self.entries:
            raise ValueError("synthetic required baseline is missing; never retrain")
        commit, verified = self.entries[root]
        if expected_git_commit != commit:
            raise ValueError("synthetic loader refused wrong independently expected commit")
        return verified


@pytest.fixture
def old_sources(workspace, monkeypatch):
    store = SyntheticFits()
    rows = []
    for job in W.historical_exp1_jobs():
        rows.append({"fit_id": job.job_id, "unit_id": job.config.unit_id,
                     "config_id": job.config.config_id, "seed": job.seed,
                     "execution_stage": job.stage, "execution_run_id": job.config.run_id,
                     "roles": list(job.roles), "config": job.config.to_dict(),
                     "source_path": str(W.HISTORICAL_JOBS_ROOT / job.job_id),
                     "execution_digest": hashlib.sha256(W._canonical(
                         {"job": job.as_record(), "commit": W.HISTORICAL_COMMIT})).hexdigest(),
                     "mean_error": "must not be inspected; this is a provenance-only fixture"})
    W.HISTORICAL_REPORT_PATH.parent.mkdir()
    atomic_write_json(W.HISTORICAL_REPORT_PATH, {"schema_version": 1,
        "kind": "experiment_1_coefficient_report",
        "provenance": {"expected_fit_commit": W.HISTORICAL_COMMIT}, "rows": rows})
    monkeypatch.setattr(W, "HISTORICAL_REPORT_SHA256", sha256_file(W.HISTORICAL_REPORT_PATH))
    for job in W.historical_exp1_jobs(label_required_only=True):
        for root in (W.HISTORICAL_JOBS_ROOT, W.HISTORICAL_COPY_ROOT):
            store.persist(root / job.job_id, job, W.HISTORICAL_COMMIT)
    monkeypatch.setattr(W.F, "load_fit_evidence", store.load)
    return store


@pytest.fixture
def checkpoint(workspace, old_sources, environment, monkeypatch):
    ledger = W.write_exp1_reuse_ledger(workspace / "input")
    from bu.experiments import week7_exp1_repair_launch as RL
    preflight = atomic_write_json(workspace / "input" / "synthetic-preflight.json", {
        "binding_sha256": "e" * 64, "attempt_timeout_seconds": 17.0,
        "inputs": {"reuse_ledger": {"path": str(ledger)}}})
    monkeypatch.setattr(RL, "validate_exp1_repair_preflight", lambda *a, **k:
        RL.ValidatedExp1Preflight(preflight, sha256_file(preflight), read_json(preflight),
            {name: workspace / name for name in ("output", "staging", "sync")}, COMMIT))
    with acquire_batch_lease(W.COMMON_LEASE_ROOT, lease_name=W.COMMON_LEASE_NAME) as lease:
        path = W.write_exp1_repair_start_checkpoint(
            reuse_ledger_path=ledger, expected_git_commit=COMMIT,
            output_root=workspace / "output", staging_root=workspace / "staging",
            sync_root=workspace / "sync", attempt_timeout_seconds=17,
            lease=lease, preflight_report=preflight,
        )
        yield {"path": path, "sha": sha256_file(path), "ledger": ledger,
               "lease": lease, "doc": read_json(path), "store": old_sources,
               "workspace": workspace, "preflight": preflight}


def _resign(plan):
    plan["plan_digest"] = hashlib.sha256(W._canonical({k: v for k, v in plan.items()
                                                     if k != "plan_digest"})).hexdigest()
    return plan


def test_exact_counts_derive_from_whole_registered_inventory():
    plan = W.build_exp1_repair_plan()
    assert plan["counts"] == {
        "units": 30, "twenty_seed_units": 6, "three_seed_units": 24,
        "registered_physical_fits": 624, "historical_fits_preserved": 150,
        "historical_fits_required_by_labels": 102, "new_baseline_fits": 90,
        "new_repair_fits": 384, "new_physical_fits": 474,
        "new_member_model_trainings": 834,
    }
    original = {(Config(unit=f.unit).unit_id, f.arm, f.seed + 1000): f
                for f in execution_plan(experiment_1_units())}
    actual = {(j.config.unit_id, j.arm, j.seed): j for j in W.registered_exp1_jobs()}
    assert set(actual) == set(original)
    assert all(actual[key].roles == original[key].roles for key in original)


def test_history_exactly_preserved_but_only_label_required_subset_loaded():
    old = W.historical_exp1_jobs()
    assert {j.job_id for j in old} == {j.job_id for j in B.experiment_1_jobs()}
    assert len(old) == 150
    assert len(W.historical_exp1_jobs(label_required_only=True)) == 102
    assert sum(len(j.roles) == 2 for j in old) == 30
    assert not {j.job_id for j in old} & {j.job_id for j in W.new_exp1_repair_jobs()}


def test_label_policies_are_separate_and_baseline_roles_never_invented():
    plan = W.build_exp1_repair_plan()
    inventory = {r["job_id"]: r for r in plan["historical_jobs"] + plan["new_jobs"]}
    for row in plan["labels"]:
        validation = row["label_stage"] == "repair_validation"
        assert row["seeds"] == list(range(1000, 1020 if validation else 1003))
        assert row["label_api"] == (
            "bu.experiments.label_evidence.build_label_evidence" if validation else
            "bu.experiments.ordinary_label_evidence.build_ordinary_label_evidence")
        fits = [inventory[key] for key in row["required_fit_ids"]]
        assert len(fits) == (60 if validation else 9)
        assert row["observed_label"] is None
        for job in fits:
            if job["arm"] == "baseline":
                assert "exp3_repairs" not in job["roles"]
                assert job["stage"] == ("exp1" if job["seed"] < 1005 else "repair_validation")


def test_full_configs_have_actual_repair_member_count_and_fixed512():
    for job in W.registered_exp1_jobs():
        record = job.as_record()
        cfg = Config.from_dict(record["config"])
        assert cfg.to_dict() == record["config"]
        assert cfg.train.ensemble_size == (5 if job.arm == "baseline" else 1)
        assert cfg.fit_id == record["job_id"]
        assert cfg.effective_unit.hidden_size == (512 if job.arm == "capacity_extension_repair" else 256)
        assert cfg.effective_unit.n_transitions == job.unit.n_transitions * (10 if job.arm == "data_repair" else 1)


def test_execution_order_supplies_every_new_seed_baseline_before_its_repairs():
    seen = {j.job_id for j in W.historical_exp1_jobs()}
    jobs = W.new_exp1_repair_jobs()
    for job in jobs:
        if job.arm != "baseline":
            baseline = Config(unit=job.unit, seed=job.seed).fit_id
            assert baseline in seen
        seen.add(job.job_id)
    assert jobs == W.new_exp1_repair_jobs()


@pytest.mark.parametrize("mutation", ["delete", "duplicate", "seed", "stage", "roles", "train", "arm",
                                      "history_commit", "historical_required", "label_policy", "counts",
                                      "authorize", "schema_bool", "extra"])
def test_resigned_plan_forgery_is_not_its_own_authority(mutation):
    plan = W.build_exp1_repair_plan()
    row = plan["new_jobs"][0]
    if mutation == "delete":
        plan["new_jobs"].pop()
    elif mutation == "duplicate":
        plan["new_jobs"][-1] = copy.deepcopy(row)
    elif mutation == "seed":
        row["seed"] = 999
    elif mutation == "stage":
        row["stage"] = "pilot"
    elif mutation == "roles":
        row["roles"] = ["exp1", "exp3_repairs"]
    elif mutation == "train":
        row["config"]["train"]["ensemble_size"] = 5
    elif mutation == "arm":
        row["arm"] = "capacity_repair"
    elif mutation == "history_commit":
        plan["historical_expected_git_commit"] = COMMIT
    elif mutation == "historical_required":
        plan["historical_jobs"][0]["required_for_label"] = False
    elif mutation == "label_policy":
        plan["labels"][0]["seeds"] = list(range(1000, 1020))
    elif mutation == "counts":
        plan["counts"]["new_physical_fits"] = 475
    elif mutation == "authorize":
        plan["execution_authorized_by_this_file"] = True
    elif mutation == "schema_bool":
        plan["exp1_repairs_schema_version"] = True
    else:
        plan["extra"] = None
    with pytest.raises(ValueError, match="exact registered"):
        W.validate_exp1_repair_plan(_resign(plan))


@pytest.mark.parametrize("value", [None, [], {"bad": float("nan")}, {"bad": object()}])
def test_bad_plan_types_refuse(value):
    with pytest.raises(ValueError):
        W.validate_exp1_repair_plan(value)


def test_pure_plan_never_opens_payloads_or_trains(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pure preparation reached IO or scientific execution")
    monkeypatch.setattr(W.F, "load_fit_evidence", forbidden)
    monkeypatch.setattr(W.F, "run_confirmatory_fit", forbidden)
    plan = W.build_exp1_repair_plan()
    W.validate_exp1_repair_plan(plan)
    assert plan["production_launch_adapter"] == "bu.experiments.week7_exp1_repair_launch"
    assert not hasattr(W, "launch_exp1_repairs")


def test_plan_immutable_roundtrip_and_divergent_refusal(workspace):
    path = W.write_exp1_repair_plan(workspace / "input")
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    assert W.load_exp1_repair_plan(path) == W.build_exp1_repair_plan()
    assert W.write_exp1_repair_plan(workspace / "input") == path
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(DivergentTargetError):
        W.write_exp1_repair_plan(workspace / "input")
    assert path.read_text(encoding="utf-8") == "{}\n"


def test_registry_seed_drift_refuses_before_plan_write(workspace, monkeypatch):
    original = W.seeds_for
    monkeypatch.setattr(W, "seeds_for", lambda stage: 5 if stage == "exp3_repairs" else original(stage))
    with pytest.raises(ValueError, match="exact 20/3/5"):
        W.write_exp1_repair_plan(workspace / "input")
    assert not list((workspace / "input").iterdir())


def test_raw_windows_reparse_ancestor_is_refused_before_resolution(workspace, monkeypatch):
    """Portable metadata simulation; no privileged Windows junction is made."""
    ancestor = workspace / "synthetic-junction"
    child = ancestor / "child"
    child.mkdir(parents=True)
    marker = ancestor.lstat().st_ino
    original = W.RF._is_reparse
    monkeypatch.setattr(W.RF, "_is_reparse", lambda info: info.st_ino == marker or original(info))
    with pytest.raises(ValueError, match="link/reparse"):
        W._project_path(child, directory=True)


def test_reuse_reopens_exact102_both_copies_under_independent_old_commit(workspace, old_sources):
    path = W.write_exp1_reuse_ledger(workspace / "input")
    document = W.load_exp1_reuse_ledger(path)
    assert len(document["sources"]) == 102
    assert len(old_sources.loads) == 102 * 2 * 2
    assert {commit for _, commit in old_sources.loads} == {W.HISTORICAL_COMMIT}
    assert {path.parent for path, _ in old_sources.loads} == {W.HISTORICAL_JOBS_ROOT, W.HISTORICAL_COPY_ROOT}
    assert {row["job"]["job_id"] for row in document["sources"]} == {
        j.job_id for j in W.historical_exp1_jobs(label_required_only=True)}
    assert all(row["source_tree_digest"] != row["copy_evidence_digest"] for row in document["sources"])


def test_historical_pin_extraction_reads_metadata_not_source_payloads_or_outcomes(old_sources):
    assert len(W._historical_execution_digests()) == 150
    assert old_sources.loads == []
    assert not old_sources.executions


@pytest.mark.parametrize("failure", ["hash", "missing_row", "duplicate", "identity", "roles", "path", "commit"])
def test_independent_d156_inventory_refuses_before_any_source_read(workspace, old_sources, monkeypatch, failure):
    document = read_json(W.HISTORICAL_REPORT_PATH)
    if failure == "missing_row":
        document["rows"].pop()
    elif failure == "duplicate":
        document["rows"][-1] = document["rows"][0]
    elif failure == "identity":
        document["rows"][0]["config"]["train"]["ensemble_size"] = 1
    elif failure == "roles":
        document["rows"][0]["roles"] = ["exp3_repairs"]
    elif failure == "path":
        document["rows"][0]["source_path"] = str(W.HISTORICAL_COPY_ROOT / document["rows"][0]["fit_id"])
    else:
        document["provenance"]["expected_fit_commit"] = COMMIT
    W.HISTORICAL_REPORT_PATH.write_text(json.dumps(document), encoding="utf-8")
    if failure != "hash":
        monkeypatch.setattr(W, "HISTORICAL_REPORT_SHA256", sha256_file(W.HISTORICAL_REPORT_PATH))
    with pytest.raises(ValueError, match="D-156"):
        W.write_exp1_reuse_ledger(workspace / "input")
    assert old_sources.loads == []
    assert not (workspace / "input" / W.REUSE_FILE).exists()


def test_both_current_source_trees_cannot_replace_the_original_execution_digest(workspace, old_sources):
    job = W.historical_exp1_jobs(label_required_only=True)[0]
    for root in (W.HISTORICAL_JOBS_ROOT, W.HISTORICAL_COPY_ROOT):
        path = root / job.job_id
        commit, fit = old_sources.entries[path]
        old_sources.entries[path] = commit, replace(fit, execution_digest="f" * 64)
        (path / "fit_evidence.json").write_text('{"both_current_trees":"changed"}', encoding="utf-8")
    with pytest.raises(ValueError, match="D-156 original execution digest"):
        W.write_exp1_reuse_ledger(workspace / "input")
    assert not (workspace / "input" / W.REUSE_FILE).exists()


def test_resigned_ledger_cannot_replace_d156_execution_pin_at_worker_boundary(workspace, old_sources):
    path = W.write_exp1_reuse_ledger(workspace / "input")
    document = read_json(path)
    document["sources"][0]["execution_digest"] = "f" * 64
    document = W._seal({k: v for k, v in document.items() if k != "reuse_digest"}, "reuse_digest")
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="D-156 original execution digest"):
        W._metadata_ledger(path, sha256_file(path))


@pytest.mark.parametrize("failure", ["missing", "different_copy", "wrong_commit", "identity", "hardlink"])
def test_bad_historical_source_halts_before_ledger_write(workspace, old_sources, failure):
    job = W.historical_exp1_jobs(label_required_only=True)[0]
    source = W.HISTORICAL_JOBS_ROOT / job.job_id
    target = W.HISTORICAL_COPY_ROOT / job.job_id / "fit_evidence.json"
    if failure == "missing":
        target.unlink()
    elif failure == "different_copy":
        target.write_text("corrupted synthetic copy", encoding="utf-8")
    elif failure == "wrong_commit":
        _, v = old_sources.entries[source]
        old_sources.entries[source] = (COMMIT, v)
    elif failure == "identity":
        commit, v = old_sources.entries[source]
        old_sources.entries[source] = (commit, replace(v, roles=("exp3_repairs",)))
    else:
        target.unlink()
        os.link(source / "fit_evidence.json", target)
    with pytest.raises(ValueError):
        W.write_exp1_reuse_ledger(workspace / "input")
    assert not (workspace / "input" / W.REUSE_FILE).exists()
    assert not old_sources.executions


def test_reuse_digest_forgery_cannot_replace_independent_old_source_commit(workspace, old_sources):
    path = W.write_exp1_reuse_ledger(workspace / "input")
    doc = read_json(path)
    doc["sources"][0]["expected_git_commit"] = COMMIT
    doc = W._seal({k: v for k, v in doc.items() if k != "reuse_digest"}, "reuse_digest")
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="historical reuse ledger"):
        W.load_exp1_reuse_ledger(path)


def test_checkpoint_requires_exact_shared_lease_and_independent_readback(checkpoint):
    cp = checkpoint
    doc = cp["doc"]
    durable = cp["workspace"] / "sync" / W.START_DIRECTORY / cp["path"].name
    assert cp["path"].read_bytes() == durable.read_bytes()
    assert not os.path.samefile(cp["path"], durable)
    assert doc["lease"]["path"] == str(cp["lease"].path)
    assert doc["environment"]["num_threads"] == doc["environment"]["num_interop_threads"] == 4
    assert doc["environment"]["git_commit"] == COMMIT
    assert doc["automatic_retry_allowed"] is False
    assert doc["purpose"] == "source_verified_exp1_repair_start"
    assert W._load_start(cp["path"], expected_sha256=cp["sha"], expected_git_commit=COMMIT)[0] == doc


@pytest.mark.parametrize("failure", ["overlap", "historical_overlap", "outside", "bad_timeout", "wrong_commit", "wrong_lease"])
def test_checkpoint_refusal_before_any_start_artifact(workspace, old_sources, environment, failure):
    ledger = W.write_exp1_reuse_ledger(workspace / "input")
    lease_root = workspace / "output" if failure == "wrong_lease" else W.COMMON_LEASE_ROOT
    with acquire_batch_lease(lease_root, lease_name=W.COMMON_LEASE_NAME) as lease:
        kwargs = dict(reuse_ledger_path=ledger, expected_git_commit=COMMIT,
                      output_root=workspace / "output", staging_root=workspace / "staging",
                      sync_root=workspace / "sync", attempt_timeout_seconds=17, lease=lease,
                      preflight_report=workspace / "input" / "unused-preflight.json")
        if failure == "overlap":
            kwargs["sync_root"] = kwargs["output_root"]
        elif failure == "historical_overlap":
            kwargs["output_root"] = W.HISTORICAL_JOBS_ROOT
        elif failure == "outside":
            kwargs["output_root"] = workspace.parent
        elif failure == "bad_timeout":
            kwargs["attempt_timeout_seconds"] = True
        elif failure == "wrong_commit":
            kwargs["expected_git_commit"] = "c" * 40
        with pytest.raises(ValueError):
            W.write_exp1_repair_start_checkpoint(**kwargs)
    assert not list(workspace.rglob(W.START_DIRECTORY))


@pytest.mark.parametrize("mutation", ["hash", "durable", "source_ledger", "lease", "threads", "preflight"])
def test_checkpoint_revalidation_detects_drift(checkpoint, monkeypatch, mutation):
    cp = checkpoint
    if mutation == "hash":
        cp["path"].write_text("{}", encoding="utf-8")
    elif mutation == "durable":
        (cp["workspace"] / "sync" / W.START_DIRECTORY / cp["path"].name).write_text("{}", encoding="utf-8")
    elif mutation == "source_ledger":
        cp["ledger"].write_text("{}", encoding="utf-8")
    elif mutation == "lease":
        cp["lease"].release()
    elif mutation == "preflight":
        cp["preflight"].write_text("{}", encoding="utf-8")
    else:
        monkeypatch.setattr(W.C, "CONFIRMATORY_THREADS", 8)
    with pytest.raises(ValueError):
        W._load_start(cp["path"], expected_sha256=cp["sha"], expected_git_commit=COMMIT)


@pytest.mark.parametrize("mutation", ["plan", "worker", "retry", "schema", "commit", "lease_root"])
def test_resigned_and_independently_copied_checkpoint_cannot_change_semantics(checkpoint, mutation):
    cp = checkpoint
    document = copy.deepcopy(cp["doc"])
    if mutation == "plan":
        document["plan_digest"] = "a" * 64
    elif mutation == "worker":
        document["fixed_worker"] = "untrusted.executor"
    elif mutation == "retry":
        document["automatic_retry_allowed"] = True
    elif mutation == "schema":
        document["exp1_repair_start_schema_version"] = True
    elif mutation == "commit":
        document["environment"]["git_commit"] = W.HISTORICAL_COMMIT
    else:
        document["lease"]["path"] = str(cp["workspace"] / "output" / "leases" / "week7-production.lease.json")
    document = W._seal({k: v for k, v in document.items() if k != "checkpoint_digest"}, "checkpoint_digest")
    for path in (cp["path"], cp["workspace"] / "sync" / W.START_DIRECTORY / cp["path"].name):
        path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="exact registered"):
        W._load_start(cp["path"], expected_sha256=sha256_file(cp["path"]), expected_git_commit=COMMIT)


def _payload(cp, job):
    return {"checkpoint_path": str(cp["path"]), "checkpoint_sha256": cp["sha"],
            "expected_git_commit": COMMIT, "job": job.as_record()}


def _attempt(cp, job):
    path = cp["workspace"] / "staging" / "staging" / f"{job.job_id}.{'a' * 32}"
    path.mkdir(parents=True)
    atomic_write_json(path / "attempt.json", {
        "schema_version": W.SUPERVISOR_SCHEMA_VERSION, "job_id": job.job_id,
        "attempt_token": "a" * 32, "parent_pid": os.getpid(),
        "started_at": "2026-08-31T00:00:00Z", "timeout_seconds": 17.0,
    })
    return path


def _fake_child(monkeypatch, store):
    parent = os.getpid()
    monkeypatch.setattr(W.os, "getpid", lambda: parent + 100000)
    def execute(unit, *, arm, seed, out_dir, scale, expected_git_commit):
        job = next(j for j in W.new_exp1_repair_jobs() if j.unit == unit and j.arm == arm and j.seed == seed)
        store.executions.append({"job": job, "scale": scale, "commit": expected_git_commit})
        store.persist(out_dir, job, expected_git_commit)
    monkeypatch.setattr(W.F, "run_confirmatory_fit", execute)


@pytest.mark.parametrize("arm,stage,seed", [
    ("baseline", "repair_validation", 1005),
    ("data_repair", "exp3_repairs", 1000),
    ("capacity_extension_repair", "exp3_repairs", 1002),
    ("capacity_extension_repair", "repair_validation", 1004),
])
def test_worker_fixed_config_and_historical_scale(checkpoint, monkeypatch, arm, stage, seed):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if (j.arm, j.stage, j.seed) == (arm, stage, seed))
    attempt = _attempt(cp, job)
    _fake_child(monkeypatch, cp["store"])
    result = W._fit_worker(attempt, _payload(cp, job))
    execution = cp["store"].executions[-1]
    assert execution["job"] == job
    assert execution["commit"] == COMMIT
    assert result["checkpoint_digest"] == cp["doc"]["checkpoint_digest"]
    if arm == "baseline":
        assert execution["scale"] is None and result["baseline_source"] is None
    else:
        baseline_id = Config(unit=job.unit, seed=seed).fit_id
        baseline = cp["store"].entries[W.HISTORICAL_JOBS_ROOT / baseline_id][1]
        assert execution["scale"] is baseline.scale
        assert result["baseline_source"]["expected_git_commit"] == W.HISTORICAL_COMMIT


@pytest.mark.parametrize("failure", ["history_job", "config", "scale_injection", "executor_injection",
                                    "timeout", "parent_pid", "partial", "prior_attempt", "source_change"])
def test_worker_refuses_before_training(checkpoint, monkeypatch, failure):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "data_repair" and j.stage == "exp3_repairs")
    attempt = _attempt(cp, job)
    payload = _payload(cp, job)
    if failure == "history_job":
        payload["job"] = W.historical_exp1_jobs()[0].as_record()
    elif failure == "config":
        payload["job"]["config"]["train"]["lr"] *= 2
    elif failure in {"scale_injection", "executor_injection"}:
        payload[failure] = "untrusted"
    elif failure in {"timeout", "parent_pid"}:
        record = read_json(attempt / "attempt.json")
        record["timeout_seconds" if failure == "timeout" else "parent_pid"] = True
        (attempt / "attempt.json").write_text(json.dumps(record), encoding="utf-8")
    elif failure == "partial":
        (cp["workspace"] / "output" / "jobs" / job.job_id).mkdir(parents=True)
    elif failure == "prior_attempt":
        (cp["workspace"] / "staging" / "quarantine" / f"{job.job_id}.{'b' * 32}").mkdir(parents=True)
    else:
        baseline_id = Config(unit=job.unit, seed=job.seed).fit_id
        (W.HISTORICAL_COPY_ROOT / baseline_id / "fit_evidence.json").write_text("changed", encoding="utf-8")
    _fake_child(monkeypatch, cp["store"])
    with pytest.raises(ValueError):
        W._fit_worker(attempt, payload)
    assert cp["store"].executions == []


def _persist_completed(cp, job, *, binding=None, wrong_checkpoint=False):
    for name in ("output", "sync"):
        path = cp["workspace"] / name / "jobs" / job.job_id
        verified = cp["store"].persist(path, job, COMMIT)
        atomic_write_json(path / "job_result.json", W._result_record(
            job, verified, commit=COMMIT,
            checkpoint_digest="f" * 64 if wrong_checkpoint else cp["doc"]["checkpoint_digest"], binding=binding,
            execution_context_digest=cp["doc"]["execution_context_digest"]))


def test_worker_requires_new20seed_baseline_completed_and_copied_first(checkpoint, monkeypatch):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "data_repair" and j.seed == 1019)
    baseline = next(j for j in W.new_exp1_repair_jobs() if j.unit == job.unit and j.seed == job.seed and j.arm == "baseline")
    _persist_completed(cp, baseline)
    attempt = _attempt(cp, job)
    _fake_child(monkeypatch, cp["store"])
    result = W._fit_worker(attempt, _payload(cp, job))
    assert result["baseline_source"]["expected_git_commit"] == COMMIT
    assert result["baseline_source"]["job"]["job_id"] == baseline.job_id
    assert cp["store"].executions[0]["scale"] is cp["store"].entries[cp["workspace"] / "output" / "jobs" / baseline.job_id][1].scale


@pytest.mark.parametrize("failure", ["absent", "no_copy", "wrong_checkpoint"])
def test_new_baseline_absence_or_wrong_start_never_falls_back_to_retraining(checkpoint, monkeypatch, failure):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "data_repair" and j.seed == 1019)
    baseline = next(j for j in W.new_exp1_repair_jobs() if j.unit == job.unit and j.seed == job.seed and j.arm == "baseline")
    if failure == "no_copy":
        cp["store"].persist(cp["workspace"] / "output" / "jobs" / baseline.job_id, baseline, COMMIT)
    elif failure == "wrong_checkpoint":
        _persist_completed(cp, baseline, wrong_checkpoint=True)
    attempt = _attempt(cp, job)
    _fake_child(monkeypatch, cp["store"])
    with pytest.raises(ValueError):
        W._fit_worker(attempt, _payload(cp, job))
    assert not cp["store"].executions


@pytest.mark.parametrize("state", ["pending", "complete", "local_only", "wrong_checkpoint", "corrupt_copy"])
def test_recovery_foundation_never_reexecutes_and_does_not_claim_cross_lease_resume(checkpoint, state):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    kwargs = dict(checkpoint_path=cp["path"], checkpoint_sha256=cp["sha"], expected_git_commit=COMMIT)
    if state in {"complete", "wrong_checkpoint", "corrupt_copy"}:
        _persist_completed(cp, job, wrong_checkpoint=state == "wrong_checkpoint")
    elif state == "local_only":
        cp["store"].persist(cp["workspace"] / "output" / "jobs" / job.job_id, job, COMMIT)
    if state == "corrupt_copy":
        (cp["workspace"] / "sync" / "jobs" / job.job_id / "job_result.json").write_text("{}", encoding="utf-8")
    if state == "pending":
        assert W.reconcile_completed_exp1_job(job.job_id, **kwargs) is None
    elif state == "complete":
        result = W.reconcile_completed_exp1_job(job.job_id, **kwargs)
        assert result["job"] == job.as_record()
        assert result["expected_git_commit"] == COMMIT
    else:
        with pytest.raises(ValueError):
            W.reconcile_completed_exp1_job(job.job_id, **kwargs)
    assert not cp["store"].executions


def test_no_launch_or_caller_executor_surface():
    names = set(inspect.signature(W.write_exp1_repair_start_checkpoint).parameters)
    assert not {"executor", "jobs", "scale", "seed", "stage", "threads", "skip_pairing"} & names
    assert "run_isolated_attempt" not in W.__dict__
    assert W.COMMON_LEASE_NAME == "week7-production"


def _next_checkpoint(cp):
    cp["lease"].release()
    lease = acquire_batch_lease(W.COMMON_LEASE_ROOT, lease_name=W.COMMON_LEASE_NAME)
    path = W.write_exp1_repair_start_checkpoint(
        reuse_ledger_path=cp["ledger"], expected_git_commit=COMMIT,
        output_root=cp["workspace"] / "output", staging_root=cp["workspace"] / "staging",
        sync_root=cp["workspace"] / "sync", attempt_timeout_seconds=17, lease=lease,
        preflight_report=cp["preflight"])
    return {**cp, "lease": lease, "path": path, "sha": sha256_file(path), "doc": read_json(path)}


def test_new_lease_reuses_completed_fit_with_unchanged_context_and_result(checkpoint):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    _persist_completed(cp, job)
    result_path = cp["workspace"] / "output" / "jobs" / job.job_id / "job_result.json"
    before = (result_path.read_bytes(), result_path.stat().st_mtime_ns)
    newer = _next_checkpoint(cp)
    try:
        assert newer["doc"]["checkpoint_digest"] != cp["doc"]["checkpoint_digest"]
        assert newer["doc"]["execution_context_digest"] == cp["doc"]["execution_context_digest"]
        assert W.reconcile_completed_exp1_job(job.job_id, checkpoint_path=newer["path"],
                                              checkpoint_sha256=newer["sha"], expected_git_commit=COMMIT)
        assert (result_path.read_bytes(), result_path.stat().st_mtime_ns) == before
    finally:
        newer["lease"].release()


@pytest.mark.parametrize("failure", ["history", "prior_copy", "context"])
def test_cross_lease_resume_refuses_unproved_history_copy_or_changed_context(checkpoint, failure):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    _persist_completed(cp, job)
    newer = _next_checkpoint(cp)
    try:
        if failure == "history":
            history = cp["lease"].history_dir / f"{W.COMMON_LEASE_NAME}.{cp['lease'].token}.released.json"
            history.write_text("{}", encoding="utf-8")
        elif failure == "prior_copy":
            (cp["workspace"] / "sync" / W.START_DIRECTORY / cp["path"].name).write_text("{}", encoding="utf-8")
        else:
            (cp["workspace"] / "output" / W.CONTEXT_FILE).write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError):
            W.reconcile_completed_exp1_job(job.job_id, checkpoint_path=newer["path"],
                                           checkpoint_sha256=newer["sha"], expected_git_commit=COMMIT)
    finally:
        newer["lease"].release()


def _released_inventory(cp, **overrides):
    return W.load_released_exp1_source_inventory(**{
        "checkpoint_path": cp["path"], "checkpoint_sha256": cp["sha"],
        "expected_execution_commit": COMMIT, **overrides})


def _snapshot_files(root):
    return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file()}


def test_released_inventory_keeps_exact_missing_jobs_pending_and_does_not_write(checkpoint):
    cp = checkpoint
    cp["lease"].release()
    before = _snapshot_files(cp["workspace"])
    inventory = _released_inventory(cp)
    assert inventory["start"] == cp["doc"]
    assert inventory["ledger"] == read_json(cp["ledger"])
    assert len(inventory["sources"]) == 102
    assert inventory["pending_new_fit_ids"] == sorted(j.job_id for j in W.new_exp1_repair_jobs())
    assert _snapshot_files(cp["workspace"]) == before
    assert cp["store"].executions == []


def test_released_inventory_different_finalizer_commit_preserves_original_sources_and_starts(checkpoint, monkeypatch):
    cp = checkpoint
    jobs = W.new_exp1_repair_jobs()
    baseline = next(j for j in jobs if j.arm == "baseline")
    _persist_completed(cp, baseline)
    repairs = [next(j for j in jobs if j.arm == "data_repair" and j.unit == baseline.unit and j.seed == baseline.seed),
               next(j for j in jobs if j.arm == "data_repair" and j.stage == "exp3_repairs")]
    for job in repairs:
        _, binding = W._baseline(job, read_json(cp["ledger"]),
            {name: cp["workspace"] / name for name in ("output", "staging", "sync")}, COMMIT, cp["doc"])
        _persist_completed(cp, job, binding=binding)
    newer = _next_checkpoint(cp)
    newer["lease"].release()
    _, versions, pins = W.P._verify_environment()
    monkeypatch.setattr(W.P, "_verify_environment", lambda: (GitState("c" * 40, False, "finalizer"), versions, pins))
    before = _snapshot_files(cp["workspace"])
    inventory = _released_inventory(newer)
    assert len(inventory["sources"]) == 105
    assert len(inventory["pending_new_fit_ids"]) == 471
    old_ids = {j.job_id for j in W.historical_exp1_jobs(label_required_only=True)}
    for source in inventory["sources"]:
        assert source["expected_git_commit"] == (W.HISTORICAL_COMMIT if source["job"]["job_id"] in old_ids else COMMIT)
    assert inventory["start"]["environment"]["git_commit"] == COMMIT
    assert _snapshot_files(cp["workspace"]) == before
    with pytest.raises(ValueError):
        W._load_start(newer["path"], expected_sha256=newer["sha"], expected_git_commit=COMMIT)
    assert cp["store"].executions == []


@pytest.mark.parametrize("failure", ["active", "other_active", "history", "checkpoint_sha", "context",
                                    "preflight", "partial", "wrong_prior_start", "wrong_execution_commit", "pins"])
def test_released_reader_refuses_without_healing_or_authorizing_workers(checkpoint, monkeypatch, failure):
    cp = checkpoint
    job = next(j for j in W.new_exp1_repair_jobs() if j.arm == "baseline")
    if failure in {"partial", "wrong_prior_start"}:
        _persist_completed(cp, job, wrong_checkpoint=failure == "wrong_prior_start")
    history = cp["lease"].path
    if failure != "active":
        history = cp["lease"].release()
    other = None
    overrides = {}
    if failure == "other_active":
        other = acquire_batch_lease(W.COMMON_LEASE_ROOT, lease_name=W.COMMON_LEASE_NAME)
    elif failure == "history":
        history.write_text("{}", encoding="utf-8")
    elif failure == "checkpoint_sha":
        overrides["checkpoint_sha256"] = "f" * 64
    elif failure == "context":
        (cp["workspace"] / "sync" / W.CONTEXT_FILE).write_text("{}", encoding="utf-8")
    elif failure == "preflight":
        cp["preflight"].write_text("{}", encoding="utf-8")
    elif failure == "partial":
        (cp["workspace"] / "sync" / "jobs" / job.job_id / "job_result.json").unlink()
    elif failure == "wrong_execution_commit":
        overrides["expected_execution_commit"] = "c" * 40
    elif failure == "pins":
        state, versions, pins = W.P._verify_environment()
        pins = {**pins, "torch": "changed"}
        monkeypatch.setattr(W.P, "_verify_environment", lambda: (state, versions, pins))
    before = _snapshot_files(cp["workspace"])
    try:
        with pytest.raises(ValueError):
            _released_inventory(cp, **overrides)
        assert _snapshot_files(cp["workspace"]) == before
        assert cp["store"].executions == []
    finally:
        if other is not None:
            other.release()


def test_released_inventory_api_has_no_worker_bypass_or_caller_subset():
    assert set(inspect.signature(W.load_released_exp1_source_inventory).parameters) == {
        "checkpoint_path", "checkpoint_sha256", "expected_execution_commit"}
    assert set(inspect.signature(W._load_start).parameters) == {
        "path", "expected_sha256", "expected_git_commit"}
