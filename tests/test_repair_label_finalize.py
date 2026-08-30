"""Correction-only Week-6 smoke finalization never trains or mutates a fit."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from bu.models.uncertainty import NormalisationScale
from bu.runrecord import GitState
from bu.experiments import repair_label_finalize as F
from bu.experiments import repair_label_launch as L
from bu.experiments import repair_label_preflight as PF
from bu.experiments import repair_label_run as R


FIT_COMMIT = "a" * 40
FINALIZER_COMMIT = "b" * 40


@pytest.fixture
def correction_boundary(tmp_path, monkeypatch):
    output = tmp_path / "attempt-output"
    sync = tmp_path / "historical-sync"
    staging = tmp_path / "staging"
    preflight_root = tmp_path / "preflight"
    project_evidence = tmp_path / "attempt-project-evidence"
    for path in (output, sync, staging, preflight_root, project_evidence):
        path.mkdir()
    sync_directory = sync / PF.REPAIR_LABEL_SYNC_DIRECTORY
    sync_directory.mkdir()
    preflight = preflight_root / PF.REPAIR_LABEL_PREFLIGHT_FILE
    preflight.write_text("{}\n", encoding="utf-8")
    plan = output / R.REPAIR_LABEL_PLAN_FILE
    plan.write_text("{}\n", encoding="utf-8")
    canary = preflight_root / "preflight_sync_canary.json"
    canary.write_text("{}\n", encoding="utf-8")
    validated = L.ValidatedRepairLabelPreflight(
        report_path=preflight,
        report_sha256="c" * 64,
        git_commit=FIT_COMMIT,
        output_root=output.resolve(),
        staging_root=staging.resolve(),
        sync_root=sync.resolve(),
        sync_directory=sync_directory.resolve(),
        report={"sync_canary": {"source_path": str(canary)}},
    )

    monkeypatch.setattr(
        F,
        "_validate_original_preflight_read_only",
        lambda *args, **kwargs: validated,
    )
    monkeypatch.setattr(
        F,
        "git_state",
        lambda: GitState(FINALIZER_COMMIT, False, "main"),
    )

    unit = R.registered_week6_smoke_unit()
    _model_arm, _seeds, planned = R._registered_plan(unit, output)
    scales = {
        seed: NormalisationScale(
            torch.tensor([1.0 + seed / 10000, 2.0]), n_reference=1000
        )
        for seed in range(1000, 1020)
    }
    loads = []

    def load(item, *, expected_commit):
        loads.append((item.spec.fit_id, expected_commit))
        return SimpleNamespace(scale=scales[item.seed])

    syncs = []

    def sync_tree(source, destination):
        syncs.append((Path(source), Path(destination)))

    monkeypatch.setattr(L, "_load_bound_fit", load)
    monkeypatch.setattr(L, "_sync_tree", sync_tree)

    def finalize(root, *, expected_git_commit):
        assert Path(root).resolve() == output.resolve()
        assert expected_git_commit == FIT_COMMIT
        label = output / "label_evidence.json"
        counts = output / "label_counts.json"
        label.write_text('{"label":"synthetic"}\n', encoding="utf-8")
        values = {
            "label_count_schema_version": 1,
            "attempted": 1,
            "observed_0": 1,
            "observed_1": 0,
            "ambiguous": 0,
            "undiagnosed": 0,
            "count_digest": "d" * 64,
        }
        counts.write_text(json.dumps(values) + "\n", encoding="utf-8")
        return SimpleNamespace(label_path=label, count_path=counts, counts=values)

    monkeypatch.setattr(R, "_finalize_registered_label", finalize)
    return SimpleNamespace(
        output=output,
        sync=sync,
        project_evidence=project_evidence,
        preflight=preflight,
        planned=planned,
        loads=loads,
        syncs=syncs,
    )


def _finalize(boundary):
    return F.finalize_existing_repair_label_smoke(
        preflight_report=boundary.preflight,
        output_root=boundary.output,
    )


def test_correction_finalizer_reuses_exactly_sixty_original_commit_fits(
    correction_boundary,
):
    report = _finalize(correction_boundary)

    assert len(correction_boundary.loads) == 60
    assert {commit for _fit, commit in correction_boundary.loads} == {FIT_COMMIT}
    assert len(correction_boundary.syncs) == 60
    assert report["executed_fits"] == 0
    assert report["retrained_fits"] == 0
    assert report["verified_existing_fits"] == 60
    assert report["project_copied_fits"] == 60
    assert report["preflight"]["fit_commit"] == FIT_COMMIT
    assert report["finalizer"]["commit"] == FINALIZER_COMMIT
    assert report["correction_records"] == ["D-147", "D-148"]
    assert report["historical_sync"]["mode"] == "read_only"
    assert Path(report["project_evidence"]["root"]) == correction_boundary.project_evidence
    assert report["counts"]["values"]["attempted"] == 1
    assert Path(report["report"]["path"]).is_file()
    assert Path(report["report"]["copy"]["destination_path"]).is_file()


def test_correction_finalizer_has_no_fit_or_process_boundary():
    source = inspect.getsource(F)
    for forbidden in (
        "run_confirmatory_fit",
        "run_isolated_attempt",
        "_fit_worker",
        "attempt_timeout_seconds",
    ):
        assert forbidden not in source


def test_same_commit_is_refused_before_plan_or_label(correction_boundary, monkeypatch):
    monkeypatch.setattr(F, "git_state", lambda: GitState(FIT_COMMIT, False, "main"))
    with pytest.raises(ValueError, match="commit after the failed preflight commit"):
        _finalize(correction_boundary)
    assert not (correction_boundary.output / "label_evidence.json").exists()


def test_missing_existing_fit_fails_and_releases_lease(correction_boundary, monkeypatch):
    def missing(_item, *, expected_commit):
        assert expected_commit == FIT_COMMIT
        raise FileNotFoundError("synthetic missing fit")

    monkeypatch.setattr(L, "_load_bound_fit", missing)
    with pytest.raises(FileNotFoundError, match="synthetic missing fit"):
        _finalize(correction_boundary)
    assert not (correction_boundary.output / "label_evidence.json").exists()
    history = correction_boundary.output / "leases" / "history"
    assert len(list(history.glob("*.released.json"))) == 1


def test_week8_count_fields_remain_refused(correction_boundary, monkeypatch):
    def forbidden_counts(root, *, expected_git_commit):
        label = Path(root) / "label_evidence.json"
        counts = Path(root) / "label_counts.json"
        label.write_text("{}\n", encoding="utf-8")
        counts.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            label_path=label,
            count_path=counts,
            counts={"attempted": 1, "exclusion_rate": 0.0},
        )

    monkeypatch.setattr(R, "_finalize_registered_label", forbidden_counts)
    with pytest.raises(ValueError, match="crossed into Week-8"):
        _finalize(correction_boundary)
