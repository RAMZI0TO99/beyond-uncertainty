"""Synthetic-only E1 finalization/export tests; no training or real outcomes.

Execution authority is explicitly mocked at the existing W boundary. Tiny
independent on-disk trees exercise copying, source pinning, alias refusal and
mutation checks. The label APIs themselves remain real in integration cases.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Config
from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import fit_evidence as F
from bu.experiments import label_evidence as L
from bu.experiments import ordinary_label_evidence as O
from bu.experiments import week7_exp1_repairs as W
from bu.experiments import week7_label_finalization as Z
from bu.models.uncertainty import NormalisationScale
from bu.runrecord import GitState


EXECUTION_COMMIT = "b" * 40
FINALIZER_COMMIT = "c" * 40
RELEASED_READER = W.load_released_exp1_source_inventory


@lru_cache(maxsize=1)
def _jobs():
    return W.registered_exp1_jobs()


@lru_cache(maxsize=1)
def _job_map():
    return {job.job_id: job for job in _jobs()}


class _Fits:
    def __init__(self):
        self.loads = []

    def persist(self, path, job, commit, *, empty=False):
        path.mkdir(parents=True)
        atomic_write_json(path / "synthetic_fit.json", {"job": job.as_record(), "commit": commit, "empty": empty})

    def load(self, root, *, expected_git_commit=None):
        root = Path(root).resolve()
        self.loads.append((root, expected_git_commit))
        path = root / "synthetic_fit.json"
        row = read_json(path)
        job = _job_map()[row["job"]["job_id"]]
        W._equal(row["job"], job.as_record(), what="synthetic job")
        if expected_git_commit is not None and row["commit"] != expected_git_commit:
            raise ValueError("synthetic fit has wrong independently expected execution commit")
        action = np.tile(np.arange(5, dtype=np.int64), 200)
        movement = action != 4
        episode = np.repeat(np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH)[movement]
        step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)[movement]
        error = np.linspace(1, 1.2, len(episode))
        error[0] = K.FAILURE_THRESHOLD
        if row["empty"]:
            error[:] = K.FAILURE_THRESHOLD
        if job.arm != "baseline":
            variation = (job.seed - 1000) * .001
            error = error + (-.35 + variation if job.arm == "data_repair" else .02 + variation)
        scale = NormalisationScale(torch.tensor([1.0, 2.0]), len(error))
        return F.VerifiedFitEvidence(
            root, job.unit, job.arm, job.seed, job.roles, job.stage,
            job.config.unit_id, job.config.config_id, job.job_id, job.config.run_id,
            hashlib.sha256(path.read_bytes()).hexdigest(),
            hashlib.sha256(f"pool:{job.config.unit_id}:{job.seed}".encode()).hexdigest(),
            {"evaluation_action": action, "error": error, "episode": episode, "step": step},
            error, episode, step, scale, job.config.effective_unit.n_transitions,
            job.config.train.ensemble_size,
        )


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    for name in ("input", "old", "old-copy", "output", "sync", "staging", "control"):
        (root / name).mkdir()
    monkeypatch.setattr(W, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(W, "HISTORICAL_JOBS_ROOT", root / "old")
    monkeypatch.setattr(W, "HISTORICAL_COPY_ROOT", root / "old-copy")
    monkeypatch.setattr(W, "HISTORICAL_REPORT_PATH", root / "input" / "synthetic-history.json")
    monkeypatch.setattr(W, "COMMON_LEASE_ROOT", root / "control")
    # Cache only the real immutable job enumeration, never source verification.
    planned = _jobs()
    monkeypatch.setattr(W, "registered_exp1_jobs", lambda: planned)
    monkeypatch.setattr(W.P, "_verify_environment", lambda: (GitState(FINALIZER_COMMIT, False, "synthetic"), {"synthetic": "1"}, {"synthetic": "1"}))
    return root


def _pin_history(monkeypatch):
    """Fabricate all 150 metadata pins, without creating the unused 48 fits."""
    rows = []
    for job in W.historical_exp1_jobs():
        source = W.HISTORICAL_JOBS_ROOT / job.job_id
        path = source / "synthetic_fit.json"
        rows.append({
            "fit_id": job.job_id, "unit_id": job.config.unit_id,
            "config_id": job.config.config_id, "seed": job.seed,
            "execution_stage": job.stage, "execution_run_id": job.config.run_id,
            "roles": list(job.roles), "config": job.config.to_dict(),
            "source_path": str(source),
            "execution_digest": sha256_file(path) if path.exists() else hashlib.sha256(job.job_id.encode()).hexdigest(),
            "mean_error": "not an outcome; must not be inspected",
        })
    W.HISTORICAL_REPORT_PATH.write_text(json.dumps({"schema_version": 1,
        "kind": "experiment_1_coefficient_report",
        "provenance": {"expected_fit_commit": W.HISTORICAL_COMMIT}, "rows": rows}), encoding="utf-8")
    monkeypatch.setattr(W, "HISTORICAL_REPORT_SHA256", sha256_file(W.HISTORICAL_REPORT_PATH))


@pytest.fixture
def evidence(workspace, monkeypatch):
    store = _Fits()
    for module in (F, L, O):
        monkeypatch.setattr(module, "load_fit_evidence", store.load)
    for job in W.historical_exp1_jobs(label_required_only=True):
        for root in (W.HISTORICAL_JOBS_ROOT, W.HISTORICAL_COPY_ROOT):
            store.persist(root / job.job_id, job, W.HISTORICAL_COMMIT)
    _pin_history(monkeypatch)
    plan = W.write_exp1_repair_plan(workspace / "input")
    ledger = W.write_exp1_reuse_ledger(workspace / "input")
    start = {
        "reuse_ledger": {"path": str(ledger), "sha256": sha256_file(ledger)},
        "plan_digest": W.build_exp1_repair_plan()["plan_digest"],
        "execution_context_digest": "e" * 64,
    }
    checkpoint = atomic_write_json(workspace / "input" / "synthetic_checkpoint.json", start)
    roots = {name: workspace / name for name in ("output", "sync", "staging")}
    authority_calls = []

    def released_inventory(*, checkpoint_path, checkpoint_sha256, expected_execution_commit):
        assert Path(checkpoint_path) == checkpoint
        assert checkpoint_sha256 == sha256_file(checkpoint)
        assert expected_execution_commit == EXECUTION_COMMIT
        authority_calls.append((checkpoint_path, checkpoint_sha256, expected_execution_commit))
        bound_ledger = W.load_exp1_reuse_ledger(ledger)
        sources = list(bound_ledger["sources"])
        pending = []
        for job in W.new_exp1_repair_jobs():
            local, durable = roots["output"] / "jobs" / job.job_id, roots["sync"] / "jobs" / job.job_id
            if not local.exists() and not durable.exists():
                pending.append(job.job_id)
            else:
                sources.append(W._source_pair(job, local, durable, commit=EXECUTION_COMMIT)[1])
        return {"start": read_json(checkpoint), "ledger": bound_ledger, "roots": roots,
                "sources": sources, "pending_new_fit_ids": pending}

    monkeypatch.setattr(W, "load_released_exp1_source_inventory", released_inventory)
    def active_forbidden(*args, **kwargs):
        pytest.fail("finalization must not use an active-worker verification boundary")
    monkeypatch.setattr(W, "_load_start", active_forbidden)
    monkeypatch.setattr(W, "reconcile_completed_exp1_job", active_forbidden)
    inputs = Z.Exp1FinalizationInputs(plan, sha256_file(plan), ledger, sha256_file(ledger), checkpoint,
                                    sha256_file(checkpoint), EXECUTION_COMMIT, FINALIZER_COMMIT)
    return workspace, store, inputs, authority_calls


def _complete(evidence, *, ordinary, empty=False, all_units=False, monkeypatch=None):
    root, store, _, _ = evidence
    chosen = next(job.unit for job in _jobs() if (len({j.seed for j in _jobs() if j.unit == job.unit and j.arm == "data_repair"}) == 3) == ordinary)
    for job in W.new_exp1_repair_jobs():
        if all_units or job.unit == chosen:
            for directory in (root / "output" / "jobs", root / "sync" / "jobs"):
                store.persist(directory / job.job_id, job, EXECUTION_COMMIT, empty=empty and job.arm == "baseline")
    if empty:
        for job in W.historical_exp1_jobs(label_required_only=True):
            if job.unit == chosen:
                for directory in (W.HISTORICAL_JOBS_ROOT, W.HISTORICAL_COPY_ROOT):
                    path = directory / job.job_id / "synthetic_fit.json"
                    row = read_json(path)
                    row["empty"] = True
                    path.write_text(json.dumps(row), encoding="utf-8")
        # These are synthetic fixtures created before the new independent pin.
        _pin_history(monkeypatch)
        ledger_path = Path(evidence[2].reuse_ledger_path)
        ledger_path.write_text(json.dumps(W.build_exp1_reuse_ledger()), encoding="utf-8")
        start_path = Path(evidence[2].checkpoint_path)
        start = read_json(start_path)
        start["reuse_ledger"]["sha256"] = sha256_file(ledger_path)
        start_path.write_text(json.dumps(start), encoding="utf-8")
        inputs = replace(evidence[2], reuse_ledger_sha256=sha256_file(ledger_path), checkpoint_sha256=sha256_file(start_path))
        evidence = (root, store, inputs, evidence[3])
    return chosen, evidence


def _roots(root):
    return {"export_root": root / "labels", "durable_copy_root": root / "label-copy"}


def test_registered_plan_is_exact_thirty_labels_and_576_required_physical_sources():
    plan = W.build_exp1_repair_plan()
    assert len(plan["labels"]) == 30
    assert sum(len(row["seeds"]) == 20 for row in plan["labels"]) == 6
    assert sum(len(row["seeds"]) == 3 for row in plan["labels"]) == 24
    required = [fit for row in plan["labels"] for fit in row["required_fit_ids"]]
    assert len(required) == len(set(required)) == 576
    assert len(W.historical_exp1_jobs()) == 150
    assert len(W.historical_exp1_jobs(label_required_only=True)) == 102
    assert len(W.new_exp1_repair_jobs()) == 474


def test_source_authority_is_existing_W_not_invented_job_results(evidence):
    _, store, inputs, calls = evidence
    inventory = Z._collect_sources(inputs)
    assert calls == [(inputs.checkpoint_path, inputs.checkpoint_sha256, EXECUTION_COMMIT)]
    assert len(inventory["sources"]) == 102
    assert len(inventory["pending_new_fit_ids"]) == 474
    allowed_old = {job.job_id for job in W.historical_exp1_jobs(label_required_only=True)}
    assert {path.name for path, _ in store.loads} == allowed_old
    assert {commit for _, commit in store.loads} == {W.HISTORICAL_COMMIT}


@pytest.mark.parametrize("mutation", ["duplicate", "extra", "omitted_old", "omitted_pending",
                                      "pending_overlap", "commit", "digest", "roles"])
def test_released_inventory_cannot_change_exact_job_partition_or_source_pins(evidence, monkeypatch, mutation):
    root, _, inputs, _ = evidence
    original = W.load_released_exp1_source_inventory

    def corrupt(**kwargs):
        result = original(**kwargs)
        if mutation == "duplicate":
            result["sources"].append(result["sources"][0])
        elif mutation == "extra":
            result["sources"][0]["job"]["job_id"] = "unregistered-fit"
        elif mutation == "omitted_old":
            result["sources"].pop()
        elif mutation == "omitted_pending":
            result["pending_new_fit_ids"].pop()
        elif mutation == "pending_overlap":
            result["pending_new_fit_ids"].append(result["sources"][0]["job"]["job_id"])
        elif mutation == "commit":
            result["sources"][0]["expected_git_commit"] = FINALIZER_COMMIT
        elif mutation == "digest":
            result["sources"][0]["execution_digest"] = "f" * 64
        else:
            result["sources"][0]["job"]["roles"] = ["exp3_repairs"]
        return result

    monkeypatch.setattr(W, "load_released_exp1_source_inventory", corrupt)
    with pytest.raises(ValueError):
        Z.finalize_exp1_labels(inputs, **_roots(root))
    assert not (root / "labels").exists()


@pytest.mark.parametrize("ordinary", [True, False])
def test_real_label_api_export_and_reload_for_each_registered_seed_policy(evidence, ordinary):
    unit, evidence = _complete(evidence, ordinary=ordinary)
    root, store, inputs, _ = evidence
    result = Z.finalize_exp1_labels(inputs, **_roots(root))
    uid = Config(unit=unit).unit_id
    row = next(row for row in result["units"] if row["unit_id"] == uid)
    assert row["status"] == "labelled"
    assert row["observed_label"] == 0
    assert len(row["seeds"]) == (3 if ordinary else 20)
    assert len(row["exported_sources"]) == (9 if ordinary else 60)
    assert result["counts"]["labelled_units"] == 1
    assert result["counts"]["pending_units"] == 29
    assert result["counts"]["observed"] == {"observed_0": 1, "observed_1": 0, "ambiguous": 0, "undiagnosed": 0}
    assert result["counts"]["executed_fits"] == result["counts"]["retrained_fits"] == 0
    assert result["status"] == "incomplete"
    local, durable = root / "labels", root / "label-copy"
    assert (local / Z.MANIFEST_FILE).read_bytes() == (durable / Z.MANIFEST_FILE).read_bytes()
    again = Z.load_exp1_label_finalization(inputs, **_roots(root), expected_manifest_sha256=sha256_file(local / Z.MANIFEST_FILE))
    assert again == result
    for source in row["exported_sources"]:
        job = _job_map()[source["fit_id"]]
        expected = W.HISTORICAL_COMMIT if job.arm == "baseline" and "exp1" in job.roles else EXECUTION_COMMIT
        assert source["expected_git_commit"] == expected
        exported = local / uid / source["relative_path"]
        copied = durable / uid / source["relative_path"]
        assert not os.path.samefile(exported / "synthetic_fit.json", copied / "synthetic_fit.json")
    assert {"excluded", "exclusion_rate", "planning_assumption_missed"}.isdisjoint(result["counts"])


def test_empty_failure_is_explicit_blocker_not_observed_or_successful_label(evidence, monkeypatch):
    unit, evidence = _complete(evidence, ordinary=True, empty=True, monkeypatch=monkeypatch)
    root, _, inputs, _ = evidence
    result = Z.finalize_exp1_labels(inputs, **_roots(root))
    row = next(row for row in result["units"] if row["unit_id"] == Config(unit=unit).unit_id)
    assert row["status"] == "blocked"
    assert row["reason"] == "empty_strict_baseline_failure_set"
    assert row["empty_failure_seeds"] == [1000, 1001, 1002]
    assert row["observed_label"] is None
    assert row["label_record_digest"] is None
    assert result["counts"]["labelled_units"] == 0
    assert result["counts"]["blocked_units"] == 1
    assert not (root / "labels" / row["unit_id"] / Z.LABEL_FILE).exists()
    assert result["counts"]["observed"] == {"observed_0": 0, "observed_1": 0, "ambiguous": 0, "undiagnosed": 0}


def test_all_missing_new_work_is_pending_and_old_48_unneeded_fits_are_never_loaded(evidence):
    root, store, inputs, _ = evidence
    result = Z.finalize_exp1_labels(inputs, **_roots(root))
    assert result["counts"]["pending_units"] == 30
    assert result["counts"]["pending_new_fits"] == 474
    assert result["counts"]["verified_source_pairs"] == 102
    assert result["counts"]["exported_fit_trees_per_root"] == 102
    forbidden = {job.job_id for job in W.historical_exp1_jobs()} - {job.job_id for job in W.historical_exp1_jobs(label_required_only=True)}
    assert not {path.name for path, _ in store.loads} & forbidden
    assert all(row["observed_label"] is None for row in result["units"])


@pytest.mark.parametrize("field", ["plan_sha256", "reuse_ledger_sha256", "checkpoint_sha256"])
def test_independent_input_file_pins_are_required_before_export(evidence, field):
    root, _, inputs, _ = evidence
    with pytest.raises(ValueError, match="independent SHA256"):
        Z.finalize_exp1_labels(replace(inputs, **{field: "f" * 64}), **_roots(root))
    assert not (root / "labels").exists()


def test_finalizer_commit_does_not_replace_historical_or_new_fit_commit(evidence):
    root, _, inputs, _ = evidence
    with pytest.raises(ValueError, match="finalization requires"):
        Z.finalize_exp1_labels(replace(inputs, expected_finalizer_commit=EXECUTION_COMMIT), **_roots(root))
    assert not (root / "labels").exists()


@pytest.mark.parametrize("kind", ["same", "nested", "existing", "source", "outside"])
def test_output_roots_refuse_alias_overlap_existing_or_outside_workspace(evidence, tmp_path, kind):
    root, _, inputs, _ = evidence
    paths = _roots(root)
    if kind == "same":
        paths["durable_copy_root"] = paths["export_root"]
    elif kind == "nested":
        paths["durable_copy_root"] = paths["export_root"] / "copy"
    elif kind == "existing":
        paths["export_root"].mkdir()
    elif kind == "source":
        paths["export_root"] = root / "output" / "labels"
    else:
        paths["export_root"] = tmp_path / "outside"
    with pytest.raises(ValueError):
        Z.finalize_exp1_labels(inputs, **paths)


def test_source_hardlink_is_refused_before_transport(evidence):
    root, _, inputs, _ = evidence
    source = next((root / "old").glob("*/synthetic_fit.json"))
    os.link(source, root / "hardlink-alias.json")
    with pytest.raises(ValueError, match="hard-linked"):
        Z.finalize_exp1_labels(inputs, **_roots(root))
    assert not (root / "labels").exists()


def test_plain_tree_export_preserves_empty_directories_and_never_overwrites(workspace):
    source, destination = workspace / "source", workspace / "destination"
    source.mkdir()
    (source / "empty").mkdir()
    (source / "nested").mkdir()
    (source / "nested" / "file.bin").write_bytes(b"synthetic source")
    Z._copy_tree(source, destination)
    assert (destination / "empty").is_dir()
    assert (destination / "nested" / "file.bin").read_bytes() == b"synthetic source"
    with pytest.raises(ValueError, match="already exists"):
        Z._copy_tree(source, destination)


def test_copy_detects_source_mutation_and_preserves_partial_attempt(workspace, monkeypatch):
    source, destination = workspace / "source", workspace / "destination"
    source.mkdir()
    (source / "file.bin").write_bytes(b"before")
    original = Z.atomic_write_bytes

    def mutate(path, data):
        result = original(path, data)
        (source / "file.bin").write_bytes(b"after")
        return result

    monkeypatch.setattr(Z, "atomic_write_bytes", mutate)
    with pytest.raises(ValueError, match="before/after"):
        Z._copy_tree(source, destination)
    assert destination.exists()  # failure evidence is never silently deleted


def test_forged_manifest_cannot_become_its_own_authority(evidence):
    root, _, inputs, _ = evidence
    result = Z.finalize_exp1_labels(inputs, **_roots(root))
    result["counts"]["labelled_units"] = 30
    result["status"] = "complete"
    result = W._seal({k: v for k, v in result.items() if k != "manifest_digest"}, "manifest_digest")
    for directory in (root / "labels", root / "label-copy"):
        (directory / Z.MANIFEST_FILE).write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="source-rederived"):
        Z.load_exp1_label_finalization(inputs, **_roots(root), expected_manifest_sha256=sha256_file(root / "labels" / Z.MANIFEST_FILE))


def test_exact_full_plan_has_30_labels_and_separate_observed_counts(evidence, monkeypatch):
    _, evidence = _complete(evidence, ordinary=True, all_units=True)
    root, _, inputs, _ = evidence
    label_plans = W.build_exp1_repair_plan()["labels"]
    unit_order = {row["unit_id"]: i for i, row in enumerate(label_plans)}
    seen_policies = []

    def synthetic_label(unit, jobs, sources, local, durable, *, creating):
        uid = Config(unit=unit).unit_id
        seeds = sorted({job.seed for job in jobs})
        seen_policies.append(len(seeds))
        assert len(jobs) == 3 * len(seeds)
        assert seeds == list(range(1000, 1000 + len(seeds)))
        observed = (0, 1, "ambiguous", "undiagnosed")[unit_order[uid] % 4]
        plan = label_plans[unit_order[uid]]
        record = {"unit_id": uid, "comparison_group_id": plan["comparison_group_id"],
                  "stage": plan["label_stage"], "seeds": seeds,
                  "label": {"observed_label": observed}, "record_digest": hashlib.sha256(uid.encode()).hexdigest()}
        if creating:
            for directory in (local, durable):
                atomic_write_json(directory / Z.LABEL_FILE, record)
        return record

    monkeypatch.setattr(Z, "_label", synthetic_label)
    result = Z.finalize_exp1_labels(inputs, **_roots(root))
    assert result["status"] == "complete"
    assert result["counts"]["labelled_units"] == 30
    assert result["counts"]["pending_units"] == result["counts"]["blocked_units"] == 0
    assert result["counts"]["observed"] == {"observed_0": 8, "observed_1": 8, "ambiguous": 7, "undiagnosed": 7}
    assert result["counts"]["verified_source_pairs"] == 576
    assert result["counts"]["exported_fit_trees_per_root"] == 576
    assert seen_policies.count(20) == 6
    assert seen_policies.count(3) == 24


def test_changed_export_and_extra_artifacts_are_refused_on_reload(evidence):
    root, _, inputs, _ = evidence
    Z.finalize_exp1_labels(inputs, **_roots(root))
    digest = sha256_file(root / "labels" / Z.MANIFEST_FILE)
    path = next((root / "label-copy").glob("*/sources/*/synthetic_fit.json"))
    before = path.read_bytes()
    row = read_json(path)
    row["empty"] = True
    path.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="export independently pinned"):
        Z.load_exp1_label_finalization(inputs, **_roots(root), expected_manifest_sha256=digest)
    path.write_bytes(before)
    (root / "labels" / "extra.json").write_text("{}")
    with pytest.raises(ValueError, match="extra or missing"):
        Z.load_exp1_label_finalization(inputs, **_roots(root), expected_manifest_sha256=digest)


def test_actual_released_source_reader_handoff_is_read_only_and_keeps_old_commit(evidence, monkeypatch):
    """Real start/context/lease/source verification; only fits/preflight are synthetic."""
    from bu.experiments import week7_exp1_repair_launch as RL
    from bu.experiments.supervisor import acquire_batch_lease

    root, store, inputs, _ = evidence
    monkeypatch.setattr(W, "load_released_exp1_source_inventory", RELEASED_READER)
    versions, pins = {"synthetic": "1"}, {"synthetic": "1"}
    monkeypatch.setattr(W.P, "_verify_environment", lambda: (GitState(EXECUTION_COMMIT, False, "synthetic"), versions, pins))
    monkeypatch.setattr(W.P, "_verify_device", lambda route: {"frozen_route": "cpu", "requested_route": route, "available": route == "cpu"})
    preflight = atomic_write_json(root / "input" / "synthetic_preflight.json", {
        "binding_sha256": "f" * 64, "attempt_timeout_seconds": 17.0,
        "inputs": {"reuse_ledger": {"path": str(inputs.reuse_ledger_path)}}})
    roots = {name: root / name for name in ("output", "sync", "staging")}
    monkeypatch.setattr(RL, "validate_exp1_repair_preflight", lambda *a, **k:
        RL.ValidatedExp1Preflight(preflight, sha256_file(preflight), read_json(preflight), roots, EXECUTION_COMMIT))
    with acquire_batch_lease(W.COMMON_LEASE_ROOT, lease_name=W.COMMON_LEASE_NAME) as lease:
        checkpoint = W.write_exp1_repair_start_checkpoint(
            reuse_ledger_path=inputs.reuse_ledger_path, expected_git_commit=EXECUTION_COMMIT,
            output_root=roots["output"], sync_root=roots["sync"], staging_root=roots["staging"],
            attempt_timeout_seconds=17, lease=lease, preflight_report=preflight)
        start = read_json(checkpoint)
        job = next(job for job in W.new_exp1_repair_jobs() if job.arm == "baseline")
        for name in ("output", "sync"):
            directory = roots[name] / "jobs" / job.job_id
            store.persist(directory, job, EXECUTION_COMMIT)
            fit = store.load(directory, expected_git_commit=EXECUTION_COMMIT)
            atomic_write_json(directory / "job_result.json", W._result_record(
                job, fit, commit=EXECUTION_COMMIT, checkpoint_digest=start["checkpoint_digest"],
                execution_context_digest=start["execution_context_digest"], binding=None))
    monkeypatch.setattr(W.P, "_verify_environment", lambda: (GitState(FINALIZER_COMMIT, False, "finalizer"), versions, pins))
    inputs = replace(inputs, checkpoint_path=checkpoint, checkpoint_sha256=sha256_file(checkpoint))
    def snapshot():
        return {path.relative_to(root).as_posix(): (sha256_file(path), path.stat().st_mtime_ns)
                for path in root.rglob("*") if path.is_file() and not path.is_relative_to(root / "labels")
                and not path.is_relative_to(root / "label-copy")}
    before = snapshot()
    result = Z.finalize_exp1_labels(inputs, **_roots(root))
    assert result["counts"]["verified_source_pairs"] == 103
    assert result["counts"]["pending_new_fits"] == 473
    assert result["counts"]["pending_units"] == 30
    assert result["counts"]["labelled_units"] == 0
    assert result["finalizer"]["git_commit"] == FINALIZER_COMMIT
    assert result["inputs"]["expected_execution_commit"] == EXECUTION_COMMIT
    assert snapshot() == before
    assert Z.load_exp1_label_finalization(inputs, **_roots(root),
        expected_manifest_sha256=sha256_file(root / "labels" / Z.MANIFEST_FILE)) == result
    assert snapshot() == before
