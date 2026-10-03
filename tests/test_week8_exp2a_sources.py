"""Synthetic source-ledger tests; no model is trained and no real result is read."""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import fit_evidence as F
from bu.experiments import week8_exp2a_repairs as W
from bu.experiments import week8_exp2a_sources as S
from bu.models.uncertainty import NormalisationScale


class SyntheticFits:
    def __init__(self):
        self.entries = {}
        self.loads = []

    def persist(self, root, job, commit, digest):
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(root / F.FIT_EVIDENCE_FILE, {
            "job": job.as_record(), "commit": commit, "execution_digest": digest,
        })
        action = np.tile(np.arange(5, dtype=np.int64), 200)
        movement = action != 4
        episode = np.repeat(np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH)[movement]
        step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)[movement]
        seed_offset = job.seed - 1000
        error = np.full(
            int(movement.sum()), 0.80 + 0.002 * seed_offset, dtype=np.float64
        )
        if job.arm == "data_repair":
            error[:] = 0.30 + 0.0005 * seed_offset
        elif job.arm == "feature_repair":
            error[:] = 0.45 + 0.001 * seed_offset
        pool_kind = "feature" if job.arm == "feature_repair" else "baseline"
        verified = F.VerifiedFitEvidence(
            fit_dir=root.resolve(), unit=job.unit, arm=job.arm, seed=job.seed,
            roles=job.roles, execution_stage=job.stage,
            unit_id=job.config.unit_id, config_id=job.config.config_id,
            fit_id=job.job_id, execution_run_id=job.config.run_id,
            execution_digest=digest,
            evaluation_pool_digest=hashlib.sha256(
                f"pool:{job.config.unit_id}:{job.seed}:{pool_kind}".encode()
            ).hexdigest(),
            diagnostics=MappingProxyType({"evaluation_action": action}), error=error,
            episode=episode, step=step,
            scale=NormalisationScale(torch.tensor([1.0, 2.0]), 10),
            n_train=job.config.effective_unit.n_transitions,
            ensemble_size=job.config.train.ensemble_size,
        )
        self.entries[root.resolve()] = (commit, verified)
        return verified

    def load(self, path, *, expected_git_commit=None):
        root = Path(path).resolve()
        self.loads.append((root, expected_git_commit))
        if root not in self.entries:
            raise ValueError("synthetic source is missing; replacement is forbidden")
        commit, verified = self.entries[root]
        if expected_git_commit is not None and expected_git_commit != commit:
            raise ValueError("synthetic source commit differs")
        return verified


def _independent_copy(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    assert not os.path.samefile(source, destination)


@pytest.fixture
def authority(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(W, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(
        W, "COMMON_LEASE_ROOT", root / "week7-production-control"
    )
    (root / "week7-production-control").mkdir()

    smoke = root / "smoke"
    smoke_copy = root / "smoke-copy"
    week7 = root / "week7"
    week7_copy = root / "week7-copy"
    receipts = root / "receipts"
    for path in (smoke, smoke_copy, week7, week7_copy, receipts):
        path.mkdir()
    monkeypatch.setattr(S, "SMOKE_OUTPUT_ROOT", smoke)
    monkeypatch.setattr(S, "SMOKE_COPY_ROOT", smoke_copy)
    monkeypatch.setattr(S, "SMOKE_FINALIZATION_FILE", "finalization.json")
    monkeypatch.setattr(S, "WEEK7_OUTPUT_ROOT", week7)
    monkeypatch.setattr(S, "WEEK7_COPY_ROOT", week7_copy)
    monkeypatch.setattr(S, "WEEK7_REPORT_FILE", "report.json")
    monkeypatch.setattr(S, "WEEK7_RECEIPT_ROOT", receipts)
    monkeypatch.setattr(S, "WEEK7_RECEIPT_ORIGINAL", receipts / "original.json")
    monkeypatch.setattr(S, "WEEK7_RECEIPT_COPY", receipts / "copy.json")

    smoke_jobs = {
        job.job_id: job for job in W.existing_exp2a_jobs()
        if W.source_kind(job) == "week6_smoke"
    }
    runs = []
    smoke_digests = {}
    for seed in range(1000, 1020):
        row = {"seed": seed}
        for arm, key in (("baseline", "baseline"), ("data_repair", "data_repair"),
                         ("feature_repair", "model_repair")):
            job = next(j for j in smoke_jobs.values() if j.seed == seed and j.arm == arm)
            digest = hashlib.sha256(f"smoke:{job.job_id}".encode()).hexdigest()
            smoke_digests[job.job_id] = digest
            row[key] = {
                "arm": arm, "config_id": job.config.config_id,
                "execution_run_id": job.config.run_id,
                "execution_stage": job.stage, "fit_id": job.job_id,
                "fit_roles": list(job.roles), "fit_evidence_digest": digest,
            }
        runs.append(row)
    label = {
        "label_evidence_schema_version": 3, "unit_id": W.SMOKE_UNIT_ID,
        "stage": "repair_validation", "model_repair_arm": "feature_repair",
        "seeds": list(range(1000, 1020)), "runs": runs,
        "label": {"observed_label": "must_not_be_inspected"},
    }
    label_path = atomic_write_json(smoke / S.SMOKE_LABEL_FILE, label)
    _independent_copy(label_path, smoke_copy / S.SMOKE_LABEL_FILE)
    monkeypatch.setattr(S, "SMOKE_LABEL_SHA256", sha256_file(label_path))
    finalization = {
        "repair_label_finalization_schema_version": 2,
        "status": "complete_after_fail_closed_correction", "unit_id": W.SMOKE_UNIT_ID,
        "fit_count": 60, "verified_existing_fits": 60, "project_copied_fits": 60,
        "executed_fits": 0, "retrained_fits": 0,
        "preflight": {"fit_commit": W.SMOKE_EXECUTION_COMMIT},
        "label": {"sha256": S.SMOKE_LABEL_SHA256},
    }
    final_path = atomic_write_json(smoke / S.SMOKE_FINALIZATION_FILE, finalization)
    _independent_copy(final_path, smoke_copy / S.SMOKE_FINALIZATION_FILE)
    monkeypatch.setattr(S, "SMOKE_FINALIZATION_SHA256", sha256_file(final_path))

    batch = {"batch_id": S.WEEK7_BATCH_ID, "complete": True, "executed": 95,
             "failed": 0, "resumed": 0, "sync_failed": 0, "synced": 95, "total": 95}
    report = {"status": "complete", "historical_reuse_retrained": False,
              "batch_key": "exp2a", "batch": batch,
              "preflight": {"git_commit": W.WEEK7_EXECUTION_COMMIT}}
    report_path = atomic_write_json(week7 / S.WEEK7_REPORT_FILE, report)
    _independent_copy(report_path, week7_copy / S.WEEK7_REPORT_FILE)
    monkeypatch.setattr(S, "WEEK7_REPORT_SHA256", sha256_file(report_path))
    week7_jobs = [job for job in W.existing_exp2a_jobs()
                  if W.source_kind(job) == "week7_exp2a"]
    week7_digests = {
        job.job_id: hashlib.sha256(f"week7:{job.job_id}".encode()).hexdigest()
        for job in week7_jobs
    }
    receipt = {
        "e2a95_verification_schema_version": 1,
        "status": "source_readback_verified",
        "expected_execution_commit": W.WEEK7_EXECUTION_COMMIT,
        "historical_reuses_reverified": 5,
        "scientific_analysis_performed": False,
        "actual_report": {"sha256": S.WEEK7_REPORT_SHA256},
        "batch": batch,
        "verified_jobs": [
            {"job_id": job.job_id, "execution_digest": week7_digests[job.job_id]}
            for job in week7_jobs
        ],
    }
    receipt_path = atomic_write_json(S.WEEK7_RECEIPT_ORIGINAL, receipt)
    _independent_copy(receipt_path, S.WEEK7_RECEIPT_COPY)
    monkeypatch.setattr(S, "WEEK7_RECEIPT_SHA256", sha256_file(receipt_path))
    return root, smoke_digests, week7_digests


@pytest.fixture
def source_trees(authority, monkeypatch):
    _, smoke_digests, week7_digests = authority
    store = SyntheticFits()
    for job in W.existing_exp2a_jobs():
        source, copy_path = S._source_paths(job)
        commit = W.SMOKE_EXECUTION_COMMIT if W.source_kind(job) == "week6_smoke" else W.WEEK7_EXECUTION_COMMIT
        digest = smoke_digests.get(job.job_id, week7_digests.get(job.job_id))
        store.persist(source, job, commit, digest)
        store.persist(copy_path, job, commit, digest)
    monkeypatch.setattr(S.F, "load_fit_evidence", store.load)
    return authority[0], store


def test_independent_authorities_cover_exact_source_partition(authority):
    record, pins = S.source_authority()
    assert set(record) == {"week6_smoke", "week7_exp2a"}
    assert len(pins) == 155
    assert sum(commit == W.SMOKE_EXECUTION_COMMIT for commit, _ in pins.values()) == 60
    assert sum(commit == W.WEEK7_EXECUTION_COMMIT for commit, _ in pins.values()) == 95
    assert record["week6_smoke"]["outcome_fields_read"] is False


def test_build_reopens_original_and_copy_of_all_155(source_trees):
    _, store = source_trees
    ledger = S.build_exp2a_source_ledger()
    assert ledger["reused_fit_count"] == 155
    assert ledger["week6_smoke_fit_count"] == 60
    assert ledger["week7_baseline_fit_count"] == 95
    assert ledger["newly_executed_fit_count"] == 0
    assert ledger["replacement_training_allowed"] is False
    assert len(ledger["sources"]) == 155
    assert len(store.loads) == 310
    assert all(row["independent_files"] is True for row in ledger["sources"])
    assert all(not os.path.samefile(row["source_path"], row["copy_path"])
               for row in ledger["sources"])


def test_missing_historical_fit_stops_without_training(source_trees, monkeypatch):
    root, _ = source_trees
    job = W.existing_exp2a_jobs()[0]
    path, _ = S._source_paths(job)
    (path / F.FIT_EVIDENCE_FILE).unlink()
    trained = []
    monkeypatch.setattr(F, "run_confirmatory_fit", lambda *a, **k: trained.append(True))
    with pytest.raises(ValueError):
        S.build_exp2a_source_ledger()
    assert trained == []
    assert root.exists()


def test_source_mutation_or_wrong_execution_digest_is_refused(source_trees):
    _, store = source_trees
    job = W.existing_exp2a_jobs()[0]
    _, copy_path = S._source_paths(job)
    (copy_path / F.FIT_EVIDENCE_FILE).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        S.build_exp2a_source_ledger()
    assert store.loads == []  # tree/copy check fails before scientific loading


def test_hard_linked_copy_is_refused(source_trees):
    job = W.existing_exp2a_jobs()[0]
    source, copy_path = S._source_paths(job)
    original = source / F.FIT_EVIDENCE_FILE
    target = copy_path / F.FIT_EVIDENCE_FILE
    target.unlink()
    try:
        os.link(original, target)
    except OSError:
        pytest.skip("hard links unavailable on this test filesystem")
    with pytest.raises(ValueError, match="hard-linked|aliases"):
        S.build_exp2a_source_ledger()


def test_resigned_metadata_cannot_change_a_source_commit_or_path(source_trees, monkeypatch):
    root, _ = source_trees
    ledger = S.build_exp2a_source_ledger()
    path = atomic_write_json(root / "ledger.json", ledger)
    changed = copy.deepcopy(ledger)
    changed["sources"][0]["expected_git_commit"] = "f" * 40
    changed["ledger_digest"] = W._seal(
        {key: value for key, value in changed.items() if key != "ledger_digest"},
        "ledger_digest",
    )["ledger_digest"]
    path.write_text(__import__("json").dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError):
        S._metadata_source_ledger(path, sha256_file(path))


def test_write_is_immutable_and_public_load_reopens_sources(source_trees):
    root, store = source_trees
    output = root / "ledger-output"
    output.mkdir()
    path = S.write_exp2a_source_ledger(output)
    build_loads = len(store.loads)
    loaded = S.load_exp2a_source_ledger(path)
    assert loaded["reused_fit_count"] == 155
    assert len(store.loads) == build_loads + 310
    # Durable publication permits an exact idempotent retry, but never a
    # divergent overwrite.  Rebuilding must therefore return the same bytes.
    before = sha256_file(path)
    assert S.write_exp2a_source_ledger(output) == path
    assert sha256_file(path) == before


def test_authority_tamper_is_detected_before_source_loading(source_trees):
    _, store = source_trees
    S.WEEK7_RECEIPT_COPY.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="pinned|bytes differ"):
        S.build_exp2a_source_ledger()
    assert store.loads == []
