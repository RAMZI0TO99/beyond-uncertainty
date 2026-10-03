"""Synthetic-only tests for the source-bound Week-8 E2A report adapter.

No production fit, label, diagnostic, or outcome is opened here.  The fixtures
exercise the exact registered 416-job topology with fabricated paths/digests.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest

from bu.config import Config
from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import experiment_2a_report as R
from bu.experiments import label_evidence as L
from bu.experiments import ordinary_label_evidence as O
from bu.experiments import week8_exp2a_label_finalization as Z
from bu.experiments import week8_exp2a_reporting as P
from bu.experiments import week8_exp2a_repair_launch as X
from bu.experiments import week8_exp2a_repairs as W
from bu.experiments import week8_exp2a_sources as S

from test_week8_exp2a_repair_launch import (
    COMMIT as EXECUTION_COMMIT,
    checkpoint,
    environment,
    preflight,
    publication,
)
from test_week8_exp2a_sources import authority, source_trees


COMMIT = "a" * 40


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _synthetic_documents(root: Path):
    export = root / "finalized-export"
    durable = root / "finalized-copy"
    export.mkdir(parents=True)
    durable.mkdir(parents=True)
    execution_roots = {
        name: root / f"execution-{name}" for name in ("output", "staging", "sync")
    }
    for value in execution_roots.values():
        value.mkdir()
    preflight_root = root / "execution-preflight"
    preflight_root.mkdir()
    jobs = W.registered_exp2a_jobs()
    released_rows = []
    for job in jobs:
        execution = _digest(f"execution:{job.job_id}")
        tree = _digest(f"tree:{job.job_id}")
        copy_evidence = _digest(f"copy-evidence:{job.job_id}")
        released_rows.append(
            {
                "job": job.as_record(),
                "source_kind": W.source_kind(job),
                "source_path": str(root / "released-source" / job.job_id),
                "copy_path": str(root / "released-copy" / job.job_id),
                "expected_git_commit": COMMIT,
                "execution_digest": execution,
                "sidecar_sha256": _digest(f"sidecar:{job.job_id}"),
                "source_tree_digest": tree,
                "copy_tree_digest": tree,
                "copy_evidence_digest": copy_evidence,
                "independent_files": True,
            }
        )
    released = {
        "start": {"preflight": {"path": str(preflight_root / "preflight.json")}},
        "roots": execution_roots,
        "sources": released_rows,
        "pending_new_fit_ids": [],
    }
    released_by_id = {row["job"]["job_id"]: row for row in released_rows}
    plan = W.build_exp2a_repair_plan()
    job_by_id = {job.job_id: job for job in jobs}
    units = []
    for label in plan["labels"]:
        exported = []
        for job_id in label["required_fit_ids"]:
            job = job_by_id[job_id]
            released_row = released_by_id[job_id]
            exported.append(
                {
                    "fit_id": job_id,
                    "job": job.as_record(),
                    "relative_path": f"{Z.SOURCE_DIRECTORY}/{job_id}",
                    "expected_git_commit": COMMIT,
                    "execution_digest": released_row["execution_digest"],
                    "source_tree_digest": released_row["source_tree_digest"],
                    "source_path": released_row["source_path"],
                    "copy_path": released_row["copy_path"],
                    "original_copy_evidence_digest": released_row[
                        "copy_evidence_digest"
                    ],
                    "independent_export_copy_digest": _digest(
                        f"export-copy:{job_id}"
                    ),
                }
            )
        units.append(
            {
                "unit_id": label["unit_id"],
                "label_stage": label["label_stage"],
                "seeds": label["seeds"],
                "required_fit_ids": label["required_fit_ids"],
                "status": "labelled",
                "reason": None,
                "missing_fit_ids": [],
                "empty_failure_seeds": [],
                "label_file_sha256": _digest(f"label-file:{label['unit_id']}"),
                "label_record_digest": _digest(f"label-record:{label['unit_id']}"),
                "exported_sources": exported,
            }
        )
    manifest = {
        "status": "complete",
        "manifest_digest": _digest("manifest"),
        "roots": {"export": str(export.resolve()), "durable_copy": str(durable.resolve())},
        "counts": {
            "registered_units": 20,
            "labelled_units": 20,
            "pending_units": 0,
            "blocked_units": 0,
            "label_required_fits": 384,
            "exported_fit_trees_per_root": 384,
            "pending_new_fits": 0,
            "historical_fits_required": 123,
            "non_label_historical_fits": 32,
            "verified_source_pairs": 384,
            "executed_fits": 0,
            "retrained_fits": 0,
        },
        "pending_new_fit_ids": [],
        "units": units,
    }
    return export.resolve(), durable.resolve(), manifest, released


def _typed(root: Path):
    export, durable, manifest, released = _synthetic_documents(root)
    typed = P._typed_sources(manifest, released, export=export, durable=durable)
    return export, durable, manifest, released, typed


def _patch_fixed_authorities(monkeypatch, root: Path) -> tuple[Path, ...]:
    values = tuple(root / f"fixed-authority-{index}" for index in range(7))
    for value in values:
        value.mkdir()
    monkeypatch.setattr(P, "_FIXED_AUTHORITY_ROOTS", values)
    return values


def test_typed_adapter_encodes_exact_68_export_32_history_baseline_split(tmp_path):
    export, durable, _, released, (baselines, validation, ordinary) = _typed(tmp_path)
    assert (len(baselines), len(validation), len(ordinary)) == (20, 4, 16)
    pairs = [pair for item in baselines for pair in item.sources]
    exported = [pair for pair in pairs if export in pair.source_path.parents]
    historical = [pair for pair in pairs if export not in pair.source_path.parents]
    assert (len(exported), len(historical)) == (68, 32)
    assert all(durable in pair.copy_path.parents for pair in exported)
    assert all("released-source" in pair.source_path.parts for pair in historical)
    assert all("released-copy" in pair.copy_path.parts for pair in historical)
    assert len(released["sources"]) == 416


def test_typed_adapter_cross_binds_all_overlapping_label_baselines(tmp_path):
    _, _, _, _, (baselines, validation, ordinary) = _typed(tmp_path)
    diagnostic = {
        (Config(unit=item.unit).unit_id, seed): pair
        for item in baselines
        for seed, pair in zip(R._SEEDS, item.sources, strict=True)
    }
    overlap = 0
    label_references = 0
    for label in validation + ordinary:
        unit_id = Config(unit=label.unit).unit_id
        for condition in label.conditions:
            label_references += 3
            if condition.seed in R._SEEDS:
                overlap += 1
                pair = diagnostic[(unit_id, condition.seed)]
                assert pair.source_path == condition.baseline.source_path
                assert pair.copy_path == condition.baseline.copy_path
                assert pair.expected_git_commit == condition.baseline.expected_git_commit
                assert (
                    pair.expected_execution_digest
                    == condition.baseline.expected_execution_digest
                )
    assert overlap == 68
    assert label_references == 384


def test_typed_adapter_pins_exact_four_shape_uniform_twenty_seed_units(tmp_path):
    _, _, _, _, (_, validation, ordinary) = _typed(tmp_path)
    assert {
        (item.unit.causal_attribute, item.unit.layout, float(item.unit.confound_rate))
        for item in validation
    } == {
        ("shape", "uniform", 0.25),
        ("shape", "uniform", 0.5),
        ("shape", "uniform", 0.75),
        ("shape", "uniform", 0.9),
    }
    assert all(len(item.conditions) == 20 for item in validation)
    assert all(len(item.conditions) == 3 for item in ordinary)


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda m, r: r["pending_new_fit_ids"].append("x"), "all 261 new fits"),
        (lambda m, r: m.update(status="incomplete"), "must be complete"),
        (lambda m, r: m["counts"].update(labelled_units=19), "counts"),
        (lambda m, r: m["units"][0].update(status="blocked"), "completed nonempty"),
        (
            lambda m, r: m["units"][0]["exported_sources"][0].update(
                relative_path="../escape"
            ),
            "noncanonical relative path",
        ),
    ],
)
def test_typed_adapter_fails_closed_on_incomplete_or_changed_inventory(
    tmp_path, mutate, match
):
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    mutate(manifest, released)
    with pytest.raises(ValueError, match=match):
        P._typed_sources(manifest, released, export=export, durable=durable)


def test_typed_adapter_refuses_wrong_finalization_root(tmp_path):
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    manifest["roots"]["export"] = str(tmp_path / "other")
    with pytest.raises(ValueError, match="finalization roots"):
        P._typed_sources(manifest, released, export=export, durable=durable)


def test_typed_adapter_refuses_duplicate_exported_fit(tmp_path):
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    first = manifest["units"][0]["exported_sources"][0]
    second = manifest["units"][0]["exported_sources"][1]
    second.update(deepcopy(first))
    with pytest.raises(ValueError, match="exported order|duplicate"):
        P._typed_sources(manifest, released, export=export, durable=durable)


def test_typed_adapter_refuses_reduced_released_row_schema(tmp_path):
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    released["sources"][0].pop("sidecar_sha256")
    with pytest.raises(ValueError, match="source row is malformed"):
        P._typed_sources(manifest, released, export=export, durable=durable)


def test_typed_adapter_cross_checks_finalized_and_released_execution_pins(tmp_path):
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    manifest["units"][0]["exported_sources"][0]["execution_digest"] = "f" * 64
    with pytest.raises(ValueError, match="finalized/released"):
        P._typed_sources(manifest, released, export=export, durable=durable)


def test_publication_binds_all_upstream_pins_and_independent_report_copy(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(R, "_PROJECT_ROOT", tmp_path.resolve())
    _patch_fixed_authorities(monkeypatch, tmp_path)
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    pins_root = tmp_path / "pins"
    pins_root.mkdir()
    plan = atomic_write_json(pins_root / "plan.json", {"kind": "plan"})
    ledger = atomic_write_json(pins_root / "ledger.json", {"kind": "ledger"})
    checkpoint = atomic_write_json(pins_root / "checkpoint.json", {"kind": "checkpoint"})
    finalization_inputs = Z.Exp2AFinalizationInputs(
        plan_path=plan,
        plan_sha256=sha256_file(plan),
        source_ledger_path=ledger,
        source_ledger_sha256=sha256_file(ledger),
        checkpoint_path=checkpoint,
        checkpoint_sha256=sha256_file(checkpoint),
        expected_execution_commit=COMMIT,
        expected_finalizer_commit=COMMIT,
    )
    inputs = P.Exp2AReportPublicationInputs(
        finalization_inputs=finalization_inputs,
        export_root=export,
        durable_copy_root=durable,
        expected_finalization_manifest_sha256=_digest("finalization-bytes"),
        expected_reporting_commit=COMMIT,
    )
    calls = {"finalization": 0, "released": 0, "writer": 0, "loader": 0}

    def load_finalization(*args, **kwargs):
        calls["finalization"] += 1
        return deepcopy(manifest)

    def load_released(**kwargs):
        calls["released"] += 1
        return deepcopy(released)

    report_document = {
        "payload_sha256": _digest("report-payload"),
        "source_manifests": {"source_inventory_sha256": _digest("sources")},
    }

    def writer(baselines, validation, ordinary, *, report_path):
        calls["writer"] += 1
        assert (len(baselines), len(validation), len(ordinary)) == (20, 4, 16)
        return atomic_write_json(report_path, report_document)

    def loader(path, *, expected_sha256):
        calls["loader"] += 1
        assert sha256_file(path) == expected_sha256
        return deepcopy(report_document)

    environment = {
        "git_commit": COMMIT,
        "branch": "synthetic",
        "packages": {},
        "exact_pins": {},
        "fits_executed": 0,
    }
    monkeypatch.setattr(Z, "load_exp2a_label_finalization", load_finalization)
    monkeypatch.setattr(X, "load_released_exp2a_source_inventory", load_released)
    monkeypatch.setattr(Z, "_finalizer_environment", lambda commit: deepcopy(environment))
    monkeypatch.setattr(R, "write_experiment_2a_report", writer)
    monkeypatch.setattr(R, "load_experiment_2a_report", loader)

    report = tmp_path / "report" / "experiment_2a_report.json"
    report_copy = tmp_path / "report-copy" / "experiment_2a_report.json"
    receipt = tmp_path / "receipt" / "week8_exp2a_report_binding.json"
    result = P.write_source_bound_exp2a_report(
        inputs,
        report_path=report,
        report_copy_path=report_copy,
        binding_receipt_path=receipt,
    )
    assert calls == {"finalization": 2, "released": 2, "writer": 1, "loader": 2}
    assert report.read_bytes() == report_copy.read_bytes()
    assert result == read_json(receipt)
    assert result["report"]["sha256"] == sha256_file(report)
    assert result["upstream"]["plan"]["sha256"] == sha256_file(plan)
    assert result["upstream"]["source_ledger"]["sha256"] == sha256_file(ledger)
    assert result["upstream"]["checkpoint"]["sha256"] == sha256_file(checkpoint)
    assert result["counts"]["exported_label_baselines"] == 68
    assert result["counts"]["historical_baseline_only_fits"] == 32
    assert result["sign_consistency_applied"] is False
    assert result["h2_verdict"] is None


def test_publication_refuses_output_inside_finalized_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "_PROJECT_ROOT", tmp_path.resolve())
    _patch_fixed_authorities(monkeypatch, tmp_path)
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    pins_root = tmp_path / "pins"
    pins_root.mkdir()
    pins = Z.Exp2AFinalizationInputs(
        plan_path=pins_root / "plan.json",
        plan_sha256="1" * 64,
        source_ledger_path=pins_root / "ledger.json",
        source_ledger_sha256="2" * 64,
        checkpoint_path=pins_root / "checkpoint.json",
        checkpoint_sha256="3" * 64,
        expected_execution_commit=COMMIT,
        expected_finalizer_commit=COMMIT,
    )
    inputs = P.Exp2AReportPublicationInputs(
        pins, export, durable, _digest("finalization"), COMMIT
    )
    monkeypatch.setattr(Z, "load_exp2a_label_finalization", lambda *a, **k: manifest)
    monkeypatch.setattr(X, "load_released_exp2a_source_inventory", lambda **k: released)
    monkeypatch.setattr(Z, "_finalizer_environment", lambda commit: {"fits_executed": 0})
    with pytest.raises(ValueError, match="disjoint from every authority"):
        P.write_source_bound_exp2a_report(
            inputs,
            report_path=export / "report.json",
            report_copy_path=tmp_path / "copy" / "report.json",
            binding_receipt_path=tmp_path / "receipt.json",
        )


def test_publication_refuses_output_beside_jobs_inside_released_execution_root(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(R, "_PROJECT_ROOT", tmp_path.resolve())
    _patch_fixed_authorities(monkeypatch, tmp_path)
    export, durable, manifest, released = _synthetic_documents(tmp_path)
    pins_root = tmp_path / "pins"
    pins_root.mkdir()
    pins = Z.Exp2AFinalizationInputs(
        plan_path=pins_root / "plan.json",
        plan_sha256="1" * 64,
        source_ledger_path=pins_root / "ledger.json",
        source_ledger_sha256="2" * 64,
        checkpoint_path=pins_root / "checkpoint.json",
        checkpoint_sha256="3" * 64,
        expected_execution_commit=COMMIT,
        expected_finalizer_commit=COMMIT,
    )
    inputs = P.Exp2AReportPublicationInputs(
        pins, export, durable, _digest("finalization"), COMMIT
    )
    monkeypatch.setattr(Z, "load_exp2a_label_finalization", lambda *a, **k: manifest)
    monkeypatch.setattr(X, "load_released_exp2a_source_inventory", lambda **k: released)
    monkeypatch.setattr(Z, "_finalizer_environment", lambda commit: {"fits_executed": 0})
    with pytest.raises(ValueError, match="disjoint from every authority"):
        P.write_source_bound_exp2a_report(
            inputs,
            report_path=released["roots"]["output"] / "report.json",
            report_copy_path=tmp_path / "copy" / "report.json",
            binding_receipt_path=tmp_path / "receipt.json",
        )


def test_publication_refuses_a_different_reporting_commit(tmp_path):
    export, durable, _, _ = _synthetic_documents(tmp_path)
    pins = Z.Exp2AFinalizationInputs(
        plan_path=tmp_path / "plan.json",
        plan_sha256="1" * 64,
        source_ledger_path=tmp_path / "ledger.json",
        source_ledger_sha256="2" * 64,
        checkpoint_path=tmp_path / "checkpoint.json",
        checkpoint_sha256="3" * 64,
        expected_execution_commit=COMMIT,
        expected_finalizer_commit=COMMIT,
    )
    inputs = P.Exp2AReportPublicationInputs(
        pins, export, durable, _digest("finalization"), "b" * 40
    )
    with pytest.raises(ValueError, match="same clean revision"):
        P._roots(inputs)


def test_real_released_finalization_and_report_boundaries_join_end_to_end(
    checkpoint, publication, monkeypatch
):
    """Exercise every real evidence/report loader with only fitting stubbed."""

    publication(checkpoint)
    events = X._load_events(checkpoint["validated"].roots, checkpoint["doc"])
    for job in W.new_exp2a_jobs():
        assert (
            X._run_one_job(
                job,
                validated=checkpoint["validated"],
                checkpoint_path=checkpoint["path"],
                start=checkpoint["doc"],
                events=events,
            )
            == "executed"
        )
    checkpoint["lease"].release()

    # The synthetic fit store already stands in for trained sidecar loading.
    # Add the registered H2 diagnostic array before any finalized export is
    # copied, then use real finalization/report readers thereafter.
    for path, (commit, fit) in list(checkpoint["store"].entries.items()):
        disagreement = np.linspace(0.01, 0.02, len(fit.error), dtype=np.float64)
        diagnostics = MappingProxyType(
            {**dict(fit.diagnostics), "disagreement": disagreement}
        )
        checkpoint["store"].entries[path] = (
            commit,
            replace(fit, diagnostics=diagnostics),
        )

    original_copy = Z._copy_tree

    def copy_and_register(source, destination):
        original_copy(source, destination)
        commit, fit = checkpoint["store"].entries[Path(source).resolve()]
        checkpoint["store"].entries[Path(destination).resolve()] = (
            commit,
            replace(fit, fit_dir=Path(destination).resolve()),
        )

    monkeypatch.setattr(Z, "_copy_tree", copy_and_register)
    # These label modules import the fit loader directly, so patch their local
    # aliases as well as the shared fit_evidence module patched by source_trees.
    monkeypatch.setattr(L, "load_fit_evidence", checkpoint["store"].load)
    monkeypatch.setattr(O, "load_fit_evidence", checkpoint["store"].load)
    finalization_inputs = Z.Exp2AFinalizationInputs(
        plan_path=checkpoint["plan"],
        plan_sha256=sha256_file(checkpoint["plan"]),
        source_ledger_path=checkpoint["ledger"],
        source_ledger_sha256=sha256_file(checkpoint["ledger"]),
        checkpoint_path=checkpoint["path"],
        checkpoint_sha256=checkpoint["sha"],
        expected_execution_commit=EXECUTION_COMMIT,
        expected_finalizer_commit=EXECUTION_COMMIT,
    )
    export = checkpoint["root"] / "labels"
    durable = checkpoint["root"] / "label-copy"
    finalized = Z.finalize_exp2a_labels(
        finalization_inputs,
        export_root=export,
        durable_copy_root=durable,
    )
    assert finalized["status"] == "complete"
    manifest_path = export / Z.MANIFEST_FILE
    manifest_sha = sha256_file(manifest_path)
    assert Z.load_exp2a_label_finalization(
        finalization_inputs,
        export_root=export,
        durable_copy_root=durable,
        expected_manifest_sha256=manifest_sha,
    ) == finalized

    workspace = checkpoint["root"]
    monkeypatch.setattr(R, "_PROJECT_ROOT", workspace.resolve())
    fake_project = workspace / "synthetic-repository"
    fake_project.mkdir()
    monkeypatch.setattr(
        P,
        "_FIXED_AUTHORITY_ROOTS",
        (
            fake_project,
            W.COMMON_LEASE_ROOT,
            S.SMOKE_OUTPUT_ROOT,
            S.SMOKE_COPY_ROOT,
            S.WEEK7_OUTPUT_ROOT,
            S.WEEK7_COPY_ROOT,
            S.WEEK7_RECEIPT_ROOT,
        ),
    )
    inputs = P.Exp2AReportPublicationInputs(
        finalization_inputs=finalization_inputs,
        export_root=export,
        durable_copy_root=durable,
        expected_finalization_manifest_sha256=manifest_sha,
        expected_reporting_commit=EXECUTION_COMMIT,
    )
    result = P.write_source_bound_exp2a_report(
        inputs,
        report_path=workspace / "analysis" / "experiment_2a_report.json",
        report_copy_path=workspace / "analysis-copy" / "experiment_2a_report.json",
        binding_receipt_path=workspace / "analysis-receipt" / "binding.json",
    )
    assert result["status"] == "complete"
    assert result["counts"]["union_fits"] == 416
    assert result["counts"]["exported_label_baselines"] == 68
    assert result["counts"]["historical_baseline_only_fits"] == 32
    assert result["sign_consistency_applied"] is False
    assert result["h2_verdict"] is None
