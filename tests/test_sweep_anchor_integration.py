"""Collectors/readers with development-only inputs and fabricated CPU models.

No production fit or outcome is consumed. Fake clean provenance is explicit;
the training boundary is replaced so this tests ordering, linkage and recovery.
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from bu.config import Arm
from bu.experiments import batch as B
from bu.experiments import confirmatory as C
from bu.experiments import fit_evidence as F
from bu.experiments import pool_anchors as A
from bu.experiments import week7_plan as W
from bu.models.ensemble import Ensemble
from bu.models.world_model import WorldModel
from bu.runrecord import GitState
import bu.runrecord as RR
from fixture_randomness import use_development_input_streams


@pytest.fixture(scope="module")
def sweep_job():
    return min(W.configuration_sweep_baseline_jobs(),
               key=lambda j: (j.unit.n_transitions, j.unit.hidden_size, j.job_id))


@pytest.fixture
def fake_training(monkeypatch):
    use_development_input_streams(monkeypatch)
    state = lambda *a, **k: GitState("b" * 40, False, "main")
    for module in (C, F, RR):
        monkeypatch.setattr(module, "git_state", state)
    calls = []
    def untrained(unit, pools, config, *, stage, seed, arm, granularity,
                  logger, epoch_logger, device):
        # Before any model is constructed, the exact consumed arrays must have
        # durable readback plus a first fsynced metric bound into fit evidence.
        run_dir = Path(logger.run_dir)
        first = json.loads((run_dir / "metrics.jsonl").read_text().splitlines()[0])
        assert first["event"] == "pool_anchors"
        assert first["i"] == 0
        anchor = A.load_pool_anchors(
            run_dir.parent / A.POOL_ANCHORS_DIRECTORY,
            expected_unit=unit, expected_seed=seed, expected_stage=stage,
            expected_source_commit="b" * 40,
            expected_anchor_sha256=first["pool_anchor_sha256"], expected_pools=pools,
        )
        assert not (anchor.path / A.POOL_ANCHOR_LINK_FILE).exists()
        calls.append(anchor.anchor_sha256)
        models = tuple(WorldModel(Arm(arm).resolve(unit), np.random.default_rng(i))
                       for i in range(config.ensemble_size))
        for i in range(config.ensemble_size):
            logger.log(record_type="member_summary", member=i, synthetic_untrained=True)
        return Ensemble(unit, Arm(arm).resolve(unit), arm, models, (), granularity)
    monkeypatch.setattr(C, "train_ensemble", untrained)
    return calls


def make_fit(tmp_path, sweep_job):
    return F.run_confirmatory_fit(
        sweep_job.unit, arm="baseline", seed=sweep_job.seed,
        out_dir=tmp_path / "fit", expected_git_commit="b" * 40,
    )


def test_capture_before_training_links_after_fit_and_keeps_schema(
    tmp_path, sweep_job, fake_training,
):
    result = make_fit(tmp_path, sweep_job)
    assert len(fake_training) == 1
    assert result.verified.fit_id == sweep_job.job_id
    assert result.verified.execution_run_id == sweep_job.config.run_id
    assert result.as_row()["fit_evidence_schema_version"] == 2
    anchor = F.validate_sweep_pool_anchors(tmp_path / "fit", expected_git_commit="b" * 40)
    assert anchor.anchor_sha256 == fake_training[0]
    assert anchor.scale.as_row() == result.verified.scale.as_row()
    extra = json.loads((result.physical.record_dir / "run.json").read_text())["extra"]
    assert set(extra) == F._RUN_EXTRA_KEYS
    B._validate_fit_evidence(sweep_job, tmp_path / "fit", result.as_row(),
                             expected_git_commit="b" * 40)


def test_independent_copy_keeps_same_anchor_and_execution_identity(
    tmp_path, sweep_job, fake_training,
):
    result = make_fit(tmp_path, sweep_job)
    shutil.copytree(tmp_path / "fit", tmp_path / "copy")
    copied = F.validate_sweep_pool_anchors(tmp_path / "copy", expected_git_commit="b" * 40)
    assert copied.anchor_sha256 == fake_training[0]
    assert F.load_fit_evidence(tmp_path / "copy", expected_git_commit="b" * 40).execution_digest == result.verified.execution_digest


@pytest.mark.parametrize("missing", [A.POOL_ANCHOR_LINK_FILE, A.POOL_ANCHOR_FILE])
def test_anchor_missing_on_recovery_never_becomes_completed_fit(
    tmp_path, sweep_job, fake_training, missing,
):
    result = make_fit(tmp_path, sweep_job)
    (tmp_path / "fit" / A.POOL_ANCHORS_DIRECTORY / missing).unlink()
    # Legacy reader retains its meaning; additional sweep boundary fails closed.
    F.load_fit_evidence(tmp_path / "fit", expected_git_commit="b" * 40)
    with pytest.raises(ValueError):
        B._validate_fit_evidence(sweep_job, tmp_path / "fit", result.as_row(),
                                 expected_git_commit="b" * 40)
    with pytest.raises(ValueError):
        B._recover_result(sweep_job, tmp_path / "fit", require_fit_evidence=True,
                          expected_git_commit="b" * 40)
    assert not (tmp_path / "fit" / B.RESULT_FILE).exists()
    assert len(fake_training) == 1


def test_recovered_result_does_not_fit_again(tmp_path, sweep_job, fake_training):
    result = make_fit(tmp_path, sweep_job)
    recovered = B._recover_result(sweep_job, tmp_path / "fit", require_fit_evidence=True,
                                  expected_git_commit="b" * 40)
    assert recovered == result.as_row()
    again = B._recover_result(sweep_job, tmp_path / "fit", require_fit_evidence=True,
                              expected_git_commit="b" * 40)
    assert again == recovered
    assert len(fake_training) == 1


def test_wrong_expected_commit_refused_before_capture(tmp_path, sweep_job, fake_training):
    with pytest.raises(ValueError, match="launch-bound"):
        F.run_confirmatory_fit(sweep_job.unit, arm="baseline", seed=sweep_job.seed,
                              out_dir=tmp_path / "fit", expected_git_commit="c" * 40)
    assert not (tmp_path / "fit").exists()
    assert fake_training == []


def test_missing_expected_commit_refused_before_capture(tmp_path, sweep_job, fake_training):
    with pytest.raises(ValueError, match="expected_git_commit"):
        F.run_confirmatory_fit(sweep_job.unit, arm="baseline", seed=sweep_job.seed,
                              out_dir=tmp_path / "fit")
    assert not (tmp_path / "fit").exists()
    assert fake_training == []


def test_anchor_readback_failure_precedes_any_training(
    tmp_path, sweep_job, fake_training, monkeypatch,
):
    def fail(*args, **kwargs):
        raise ValueError("synthetic anchor readback failed")
    monkeypatch.setattr(A, "write_pool_anchors", fail)
    with pytest.raises(ValueError, match="anchor readback"):
        make_fit(tmp_path, sweep_job)
    assert fake_training == []
    assert not (tmp_path / "fit" / sweep_job.config.run_id).exists()
