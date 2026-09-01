"""Synthetic zero-compute tests for the mixed-policy E2A finalizer."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from bu import constants as K
from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import fit_evidence as F
from bu.experiments import label_evidence as L
from bu.experiments import ordinary_label_evidence as O
from bu.experiments import week8_exp2a_label_finalization as Z
from bu.experiments import week8_exp2a_repair_launch as X
from bu.experiments import week8_exp2a_repairs as W
from bu.experiments import week8_exp2a_sources as S
from bu.runrecord import GitState

from test_week8_exp2a_sources import authority, source_trees


EXECUTION_COMMIT = "b" * 40
FINALIZER_COMMIT = "c" * 40


@pytest.fixture
def evidence(source_trees, monkeypatch):
    root, store = source_trees
    for name in ("inputs", "output", "sync", "staging"):
        (root / name).mkdir()
    plan = W.write_exp2a_repair_plan(root / "inputs")
    ledger = S.write_exp2a_source_ledger(root / "inputs")
    start = {
        "source_ledger": {"path": str(ledger), "sha256": sha256_file(ledger)},
        "plan_digest": W.build_exp2a_repair_plan()["plan_digest"],
        "execution_context_digest": "e" * 64,
    }
    checkpoint = atomic_write_json(root / "inputs" / "checkpoint.json", start)
    roots = {name: root / name for name in ("output", "sync", "staging")}
    calls = []

    def released(*, checkpoint_path, checkpoint_sha256, expected_execution_commit):
        assert Path(checkpoint_path) == checkpoint
        assert checkpoint_sha256 == sha256_file(checkpoint)
        assert expected_execution_commit == EXECUTION_COMMIT
        calls.append("released")
        bound = S.load_exp2a_source_ledger(ledger)
        sources = list(bound["sources"])
        pending = []
        for job in W.new_exp2a_jobs():
            local = roots["output"] / "jobs" / job.job_id
            durable = roots["sync"] / "jobs" / job.job_id
            if not local.exists() and not durable.exists():
                pending.append(job.job_id)
            elif local.exists() != durable.exists():
                raise ValueError("synthetic partial source must remain incomplete")
            else:
                sources.append(
                    S._source_pair(
                        job, local, durable, commit=EXECUTION_COMMIT
                    )[1]
                )
        return {
            "start": read_json(checkpoint),
            "ledger": bound,
            "roots": roots,
            "sources": sources,
            "pending_new_fit_ids": pending,
        }

    monkeypatch.setattr(X, "load_released_exp2a_source_inventory", released)
    monkeypatch.setattr(
        X.P,
        "_verify_environment",
        lambda: (
            GitState(FINALIZER_COMMIT, False, "synthetic"),
            {"synthetic": "1"},
            {"synthetic": "1"},
        ),
    )
    monkeypatch.setattr(L, "load_fit_evidence", store.load)
    monkeypatch.setattr(O, "load_fit_evidence", store.load)
    monkeypatch.setattr(Z.F, "load_fit_evidence", store.load)

    original_copy = Z._copy_tree

    def copy_and_register(source, destination):
        original_copy(source, destination)
        commit, verified = store.entries[Path(source).resolve()]
        store.entries[Path(destination).resolve()] = (
            commit, replace(verified, fit_dir=Path(destination).resolve())
        )

    monkeypatch.setattr(Z, "_copy_tree", copy_and_register)
    inputs = Z.Exp2AFinalizationInputs(
        plan,
        sha256_file(plan),
        ledger,
        sha256_file(ledger),
        checkpoint,
        sha256_file(checkpoint),
        EXECUTION_COMMIT,
        FINALIZER_COMMIT,
    )
    return {"root": root, "store": store, "inputs": inputs, "calls": calls}


def _complete(evidence, *, unit_ids=None):
    selected = None if unit_ids is None else set(unit_ids)
    for job in W.new_exp2a_jobs():
        if selected is not None and job.config.unit_id not in selected:
            continue
        digest = hashlib.sha256(f"new:{job.job_id}".encode()).hexdigest()
        for name in ("output", "sync"):
            evidence["store"].persist(
                evidence["root"] / name / "jobs" / job.job_id,
                job,
                EXECUTION_COMMIT,
                digest,
            )


def _final_roots(evidence, suffix=""):
    return {
        "export_root": evidence["root"] / f"labels{suffix}",
        "durable_copy_root": evidence["root"] / f"label-copy{suffix}",
    }


def test_registered_finalization_inventory_is_four_plus_sixteen_and_384_sources():
    plan = W.build_exp2a_repair_plan()
    assert len(plan["labels"]) == 20
    assert sum(len(row["seeds"]) == 20 for row in plan["labels"]) == 4
    assert sum(len(row["seeds"]) == 3 for row in plan["labels"]) == 16
    required = [fit_id for row in plan["labels"] for fit_id in row["required_fit_ids"]]
    assert len(required) == len(set(required)) == 384
    assert len({job.job_id for job in W.existing_exp2a_jobs()} - set(required)) == 32


def test_collect_sources_uses_released_boundary_and_reports_pending_explicitly(evidence):
    inventory = Z._collect_sources(evidence["inputs"])
    assert len(inventory["sources"]) == 123
    assert len(inventory["pending_new_fit_ids"]) == 261
    assert len(inventory["non_label_existing_fit_ids"]) == 32
    assert evidence["calls"] == ["released"]


def test_conditions_use_certified_twenty_and_three_seed_types(evidence):
    rows = {
        row["job"]["job_id"]: row
        for row in S.load_exp2a_source_ledger(evidence["inputs"].source_ledger_path)["sources"]
    }
    validation_unit = next(
        job.unit for job in W.existing_exp2a_jobs()
        if job.config.unit_id == W.SMOKE_UNIT_ID
    )
    validation_jobs = [
        job for job in W.label_required_exp2a_jobs() if job.unit == validation_unit
    ]
    validation = Z._conditions(
        validation_jobs, rows, evidence["root"], ordinary=False
    )
    assert len(validation) == 20
    assert all(type(item) is L.PersistedRepairCondition for item in validation)

    ordinary_unit = next(
        job.unit for job in W.existing_exp2a_jobs()
        if job.stage == "exp2a" and job.config.unit_id != W.SMOKE_UNIT_ID
        and any(candidate.stage == "exp3_repairs" and candidate.unit == job.unit
                for candidate in W.new_exp2a_jobs())
    )
    ordinary_jobs = [
        job for job in W.label_required_exp2a_jobs() if job.unit == ordinary_unit
    ]
    # Ordinary rows need six new repairs, so fabricate only metadata here.
    for job in ordinary_jobs:
        if job.job_id not in rows:
            rows[job.job_id] = {
                "expected_git_commit": EXECUTION_COMMIT,
                "execution_digest": "a" * 64,
            }
    ordinary = Z._conditions(ordinary_jobs, rows, evidence["root"], ordinary=True)
    assert len(ordinary) == 3
    assert all(type(item) is O.OrdinaryRepairCondition for item in ordinary)


def test_pending_finalization_labels_only_complete_evidence_and_executes_no_fit(
    evidence, monkeypatch
):
    def forbidden(*args, **kwargs):
        pytest.fail("zero-compute finalizer reached a fitting function")

    monkeypatch.setattr(F, "run_confirmatory_fit", forbidden)
    monkeypatch.setattr(X, "_fit_worker", forbidden)
    record = Z.finalize_exp2a_labels(
        evidence["inputs"], **_final_roots(evidence)
    )
    assert record["status"] == "incomplete"
    assert record["counts"]["labelled_units"] == 1
    assert record["counts"]["pending_units"] == 19
    assert record["counts"]["executed_fits"] == 0
    assert record["counts"]["retrained_fits"] == 0
    assert record["counts"]["exported_fit_trees_per_root"] == 123
    labels = list((evidence["root"] / "labels").rglob(Z.LABEL_FILE))
    assert labels == [evidence["root"] / "labels" / W.SMOKE_UNIT_ID / Z.LABEL_FILE]


def test_complete_finalization_calls_both_real_label_apis_and_exports_384(
    evidence, monkeypatch
):
    _complete(evidence)
    calls = {"twenty": 0, "ordinary": 0}
    real_twenty = L.build_label_evidence
    real_ordinary = O.build_ordinary_label_evidence

    def twenty(*args, **kwargs):
        calls["twenty"] += 1
        return real_twenty(*args, **kwargs)

    def ordinary(*args, **kwargs):
        calls["ordinary"] += 1
        return real_ordinary(*args, **kwargs)

    monkeypatch.setattr(L, "build_label_evidence", twenty)
    monkeypatch.setattr(O, "build_ordinary_label_evidence", ordinary)
    record = Z.finalize_exp2a_labels(
        evidence["inputs"], **_final_roots(evidence)
    )
    assert record["status"] == "complete"
    assert record["counts"]["labelled_units"] == 20
    assert record["counts"]["pending_units"] == 0
    assert record["counts"]["blocked_units"] == 0
    assert record["counts"]["verified_source_pairs"] == 384
    assert record["counts"]["exported_fit_trees_per_root"] == 384
    assert record["counts"]["executed_fits"] == record["counts"]["retrained_fits"] == 0
    assert calls == {"twenty": 4, "ordinary": 16}
    assert all(row["observed_label"] in (0, 1, "ambiguous", "undiagnosed")
               for row in record["units"])
    assert not Path(evidence["inputs"].plan_path).is_relative_to(
        evidence["root"] / "labels"
    )


def test_empty_strict_baseline_failure_set_is_blocked_not_labelled(evidence):
    ordinary_unit = next(
        job.unit for job in W.new_exp2a_jobs() if job.stage == "exp3_repairs"
    )
    unit_id = next(job.config.unit_id for job in W.new_exp2a_jobs() if job.unit == ordinary_unit)
    _complete(evidence, unit_ids={unit_id})
    for job in W.label_required_exp2a_jobs():
        if job.unit != ordinary_unit or job.arm != "baseline":
            continue
        source, copy_path = S._source_paths(job)
        for path in (source, copy_path):
            commit, verified = evidence["store"].entries[path.resolve()]
            error = np.full_like(verified.error, K.FAILURE_THRESHOLD)
            evidence["store"].entries[path.resolve()] = (
                commit, replace(verified, error=error)
            )
    record = Z.finalize_exp2a_labels(
        evidence["inputs"], **_final_roots(evidence, "-blocked")
    )
    row = next(item for item in record["units"] if item["unit_id"] == unit_id)
    assert row["status"] == "blocked"
    assert row["reason"] == "empty_strict_baseline_failure_set"
    assert row["observed_label"] is None
    assert not (evidence["root"] / "labels-blocked" / unit_id / Z.LABEL_FILE).exists()


def test_partial_new_source_is_refused_not_healed_or_retrained(evidence):
    job = W.new_exp2a_jobs()[0]
    digest = hashlib.sha256(job.job_id.encode()).hexdigest()
    evidence["store"].persist(
        evidence["root"] / "output" / "jobs" / job.job_id,
        job,
        EXECUTION_COMMIT,
        digest,
    )
    with pytest.raises(ValueError, match="partial"):
        Z._collect_sources(evidence["inputs"])
    assert not (evidence["root"] / "sync" / "jobs" / job.job_id).exists()


def test_existing_or_overlapping_finalization_roots_fail_before_publication(evidence):
    existing = evidence["root"] / "already"
    existing.mkdir()
    with pytest.raises(ValueError, match="new"):
        Z.finalize_exp2a_labels(
            evidence["inputs"], export_root=existing,
            durable_copy_root=evidence["root"] / "other",
        )
    with pytest.raises(ValueError, match="overlap"):
        Z.finalize_exp2a_labels(
            evidence["inputs"],
            export_root=evidence["root"] / "nested",
            durable_copy_root=evidence["root"] / "nested" / "copy",
        )
