"""Synthetic untrained models, real paired inputs/readers; no thesis outcome."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from bu.config import Arm
from bu.durable import read_json
from bu.experiments import fit_evidence as F
from bu.experiments import paired_repair_evidence as E
from bu.experiments import preflight as P
from bu.models.ensemble import Ensemble
from bu.models.world_model import WorldModel
from bu.runrecord import GitState
from test_sweep_anchor_integration import fake_training, sweep_job


@pytest.fixture
def setup(tmp_path, monkeypatch, sweep_job, fake_training):
    baseline = F.run_confirmatory_fit(
        sweep_job.unit, arm="baseline", seed=sweep_job.seed,
        out_dir=tmp_path / "baseline", expected_git_commit="b" * 40,
    )
    monkeypatch.setattr(P, "git_state", lambda: GitState("b" * 40, False, "main"))
    calls = []
    def untrained(unit, pools, config, *, stage, seed, arm, granularity,
                  logger, epoch_logger, device):
        first = json.loads((logger.run_dir / "metrics.jsonl").read_text().splitlines()[0])
        assert first["event"] == "paired_inputs"
        root = logger.run_dir.parent
        assert (root / E.CONTRACT_FILE).is_file()
        assert (root / E.COMPATIBILITY_FILE).is_file()
        assert len(list((root / E.INPUT_DIRECTORY).glob("*.npy"))) == 21
        assert not (root / E.PAIRED_FIT_FILE).exists()
        assert not (logger.run_dir / "run.json").exists()
        calls.append((unit, arm, seed))
        logger.log(record_type="member_summary", member=0, synthetic_untrained=True)
        return Ensemble(unit, Arm(arm).resolve(unit), arm,
                        (WorldModel(Arm(arm).resolve(unit), np.random.default_rng(0)),), (), granularity)
    monkeypatch.setattr(E, "train_ensemble", untrained)
    args = dict(unit=sweep_job.unit, arm="data_repair", seed=sweep_job.seed,
                baseline_source=tmp_path / "baseline", expected_baseline_commit="b" * 40,
                expected_baseline_execution_digest=baseline.verified.execution_digest,
                expected_git_commit="b" * 40)
    return tmp_path, args, calls


def fit(setup):
    root, args, _ = setup
    return E.run_paired_repair(**args, out_dir=root / "repair")


def reload(setup, root=None):
    base, args, _ = setup
    return E.load_paired_repair_evidence(base / "repair" if root is None else root, **args)


def resign_artifact(root, name):
    path = root / E.PAIRED_FIT_FILE
    doc = read_json(path)
    row = doc["artifacts"][name]
    row["sha256"] = E.sha256_file(root / row["path"])
    doc["execution_digest"] = E._digest({k: doc[k] for k in
                                         ("paired_fit_schema_version", "procedure", "artifacts")})
    path.write_bytes(E._json(doc))


def test_new_physical_ids_truthful_records_beforetrain_binding_and_reload(setup):
    result = fit(setup)
    root, args, calls = setup
    assert len(calls) == 1
    assert result.physical_fit_id != result.obligation_fit_id
    assert result.physical_run_id != result.obligation_run_id
    assert result.n_train == args["unit"].n_transitions * 10
    assert result.contract.as_dict()["generation_stage"] == "config_sweep"
    assert result.contract.as_dict()["obligation_stage"] == "exp3_repairs"
    assert not (root / "repair" / F.FIT_EVIDENCE_FILE).exists()
    assert not list((root / "repair").glob("*/run.json"))
    copied = root / "copy"
    shutil.copytree(root / "repair", copied)
    again = reload(setup, copied)
    assert again.execution_digest == result.execution_digest
    assert again.physical_fit_id == result.physical_fit_id
    assert np.array_equal(again.error, result.error)
    assert not again.error.flags.writeable
    assert len(calls) == 1


def test_legacy_reader_and_paired_reader_refuse_cross_schema(setup):
    fit(setup)
    root, args, _ = setup
    with pytest.raises((ValueError, FileNotFoundError)):
        F.load_fit_evidence(root / "repair", expected_git_commit="b" * 40)
    # Keep the schema refusal distinct from the earlier source-overlap refusal.
    independent = root / "independent-baseline"
    shutil.copytree(args["baseline_source"], independent)
    with pytest.raises(ValueError, match="legacy"):
        E.load_paired_repair_evidence(root / "baseline", **{**args, "baseline_source": independent})


@pytest.mark.parametrize("key,value", [("expected_git_commit", "c" * 40),
                                      ("expected_baseline_commit", "c" * 40),
                                      ("expected_baseline_execution_digest", "c" * 64)])
def test_wrong_independent_expectations_refuse_before_training(setup, key, value):
    root, args, calls = setup
    with pytest.raises(ValueError):
        E.run_paired_repair(**{**args, key: value}, out_dir=root / "repair")
    assert calls == []
    assert not (root / "repair").exists()


def test_no_overwrite_or_retraining_completed_evidence(setup):
    result = fit(setup)
    root, args, calls = setup
    with pytest.raises(ValueError, match="prior evidence"):
        E.run_paired_repair(**args, out_dir=root / "repair")
    assert reload(setup).execution_digest == result.execution_digest
    assert len(calls) == 1


def test_resigned_input_corruption_still_refuses(setup):
    fit(setup)
    root = setup[0] / "repair"
    path = root / E.INPUT_DIRECTORY / "train.obs.npy"
    array = np.load(path, allow_pickle=False)
    array[0, 0] += np.float32(0.1)
    path.write_bytes(E.A._array_bytes(array))
    resign_artifact(root, "train.obs")
    with pytest.raises(ValueError, match="encoding|compatibility"):
        reload(setup)


def test_resigned_prediction_change_without_actual_error_refuses(setup):
    fit(setup)
    root = setup[0] / "repair"
    path = root / E.EVALUATION_DIRECTORY / "predictions.npy"
    array = np.load(path, allow_pickle=False)
    array[0] += np.float32(2)
    path.write_bytes(E.A._array_bytes(array))
    resign_artifact(root, "predictions")
    with pytest.raises(ValueError, match="error differs"):
        reload(setup)


def test_resigned_procedure_override_refuses(setup):
    fit(setup)
    root = setup[0] / "repair"
    path = root / E.PAIRED_FIT_FILE
    doc = read_json(path)
    doc["procedure"]["threading"]["num_threads"] = 8
    doc["execution_digest"] = E._digest({k: doc[k] for k in
                                         ("paired_fit_schema_version", "procedure", "artifacts")})
    path.write_bytes(E._json(doc))
    with pytest.raises(ValueError, match="procedure"):
        reload(setup)


def test_missing_input_or_link_is_not_recoverable_completion(setup):
    fit(setup)
    root = setup[0]
    (root / "baseline" / E.A.POOL_ANCHORS_DIRECTORY / E.A.POOL_ANCHOR_LINK_FILE).unlink()
    with pytest.raises(ValueError):
        reload(setup)
    assert len(setup[2]) == 1


@pytest.fixture
def marker_tree(tmp_path):
    """Fabricated filesystem markers only; never accepted as full fit evidence."""
    root = tmp_path / "marker-tree"
    contract = SimpleNamespace(physical_run_id="ps1-" + "a" * 32 + "-r")
    for relative in (E.PAIRED_FIT_FILE, f"{contract.physical_run_id}/{E.PAIRED_RUN_FILE}",
                     f"{contract.physical_run_id}/metrics.jsonl"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"{}\n")
    return root, contract


@pytest.mark.parametrize("relative", [
    "extra/paired_run.json", "extra/metrics.jsonl", "metrics.jsonl",
    "nested/deep/paired_run.json", "nested/deep/metrics.jsonl",
    "extra/paired_fit_evidence.json", "nested/deep/paired_fit_evidence.json",
    "extra/PAIRED_RUN.JSON", "extra/METRICS.JSONL",
])
def test_execution_inventory_refuses_extra_markers_at_every_depth(marker_tree, relative):
    root, contract = marker_tree
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="exactly one physical"):
        E._assert_one_physical_execution(root, contract)


@pytest.mark.parametrize("relative", [
    "run.json", "deep/nested/run.json", "deep/nested/fit_evidence.json",
    "deep/nested/confirmatory.json", "deep/nested/RUN.JSON",
])
def test_execution_inventory_refuses_nested_legacy_records(marker_tree, relative):
    root, contract = marker_tree
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="legacy"):
        E._assert_one_physical_execution(root, contract)


@pytest.mark.parametrize("marker", ["run", "metrics", "fit"])
def test_execution_inventory_refuses_missing_or_misplaced_single_marker(marker_tree, marker):
    root, contract = marker_tree
    relative = {"run": f"{contract.physical_run_id}/{E.PAIRED_RUN_FILE}",
                "metrics": f"{contract.physical_run_id}/metrics.jsonl", "fit": E.PAIRED_FIT_FILE}[marker]
    (root / relative).unlink()
    with pytest.raises(ValueError, match="exactly one physical"):
        E._assert_one_physical_execution(root, contract)
    moved = root / "wrong-location" / Path(relative).name
    moved.parent.mkdir()
    moved.write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="exactly one physical"):
        E._assert_one_physical_execution(root, contract)


def test_execution_inventory_allows_nonexecution_supervisor_receipts(marker_tree):
    root, contract = marker_tree
    for name in ("attempt.json", "result.json", "stdout.log", "stderr.log"):
        (root / name).write_bytes(b"{}\n")
    E._assert_one_physical_execution(root, contract)


def test_execution_marker_directory_is_not_ignored(marker_tree):
    root, contract = marker_tree
    (root / "extra" / "metrics.jsonl").mkdir(parents=True)
    with pytest.raises(ValueError, match="regular file"):
        E._assert_one_physical_execution(root, contract)


def test_execution_inventory_does_not_suppress_directory_read_errors(marker_tree, monkeypatch):
    root, contract = marker_tree
    blocked = root / "unreadable"
    blocked.mkdir()
    original = Path.iterdir
    def guarded(path):
        if path == blocked:
            raise PermissionError("synthetic directory scan failure")
        return original(path)
    monkeypatch.setattr(Path, "iterdir", guarded)
    with pytest.raises(ValueError, match="cannot inspect paired execution"):
        E._assert_one_physical_execution(root, contract)


@pytest.mark.parametrize("entrypoint", ["run", "load"])
@pytest.mark.parametrize("relation", ["equal", "output_contains_source", "source_contains_output"])
def test_both_entrypoints_refuse_source_overlap_before_evidence_io(
    tmp_path, monkeypatch, entrypoint, relation,
):
    source = tmp_path / "source"
    output = {"equal": source, "output_contains_source": tmp_path,
              "source_contains_output": source / "child-repair"}[relation]
    source.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    forbidden = Mock(side_effect=AssertionError("evidence opened or training reached after overlap"))
    monkeypatch.setattr(E.RP, "registered_sweep_pairing", forbidden)
    monkeypatch.setattr(E, "train_ensemble", forbidden)
    monkeypatch.setattr(F, "_require_current_git_commit", forbidden)
    kwargs = dict(unit=None, arm="data_repair", seed=1000, baseline_source=source,
                  expected_baseline_commit="b" * 40,
                  expected_baseline_execution_digest="a" * 64, expected_git_commit="b" * 40)
    with pytest.raises(ValueError, match="must not overlap"):
        if entrypoint == "run":
            E.run_paired_repair(out_dir=output, **kwargs)
        else:
            E.load_paired_repair_evidence(output, **kwargs)
    forbidden.assert_not_called()


def test_loader_refuses_extra_executions_without_resigning_declared_artifacts(setup):
    result = fit(setup)
    root = setup[0] / "repair"
    sealed = (root / E.PAIRED_FIT_FILE).read_bytes()
    for relative in ("extra/paired_run.json", "extra/metrics.jsonl",
                     "deep/nested/run.json", "extra/paired_fit_evidence.json"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"{}\n")
        with pytest.raises(ValueError, match="exactly one physical|legacy"):
            reload(setup)
        assert (root / E.PAIRED_FIT_FILE).read_bytes() == sealed
        target.unlink()
    assert reload(setup).execution_digest == result.execution_digest
    assert len(setup[2]) == 1


def test_loader_rejects_valid_baseline_copy_nested_inside_paired_output(setup):
    fit(setup)
    root, args, calls = setup
    nested = root / "repair" / "nested-baseline"
    shutil.copytree(args["baseline_source"], nested)
    with pytest.raises(ValueError, match="must not overlap"):
        E.load_paired_repair_evidence(root / "repair", **{**args, "baseline_source": nested})
    assert len(calls) == 1


def test_loader_reinventories_executions_after_expensive_verification(setup, monkeypatch):
    fit(setup)
    root = setup[0] / "repair"
    original = E.RP.validate_pool_compatibility
    inserted = []
    def changed_during_read(*args, **kwargs):
        receipt = original(*args, **kwargs)
        target = root / "late-execution" / "metrics.jsonl"
        target.parent.mkdir()
        target.write_bytes(b"{}\n")
        inserted.append(target)
        return receipt
    monkeypatch.setattr(E.RP, "validate_pool_compatibility", changed_during_read)
    with pytest.raises(ValueError, match="exactly one physical"):
        reload(setup)
    assert len(inserted) == 1 and len(setup[2]) == 1
