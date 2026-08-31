"""Synthetic data only: contemporaneous capture/persistence, no model training.

The late-link integration test fabricates a registered sidecar, using the
existing fit-evidence fixture and real writer/reader. No scientific result is
inspected, created or assigned a label by these tests.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

from bu.config import Arm, Config, UnitSpec
from bu.durable import DivergentTargetError, sha256_file
from bu.env import collect as C
from bu.env.encoder import ObservationEncoder
from bu.env.gridworld import GridObject, GridState, GridWorld
from bu.env.policy import ExploratoryPolicy
from bu.experiments import pool_anchors as A
from bu.models.uncertainty import NormalisationScale
from bu.models.world_model import MOVEMENT_ACTIONS
from bu.streams import DATA_PURPOSES, stream_key


COMMIT = "b" * 40


def _expected(anchor, *, unit=None, seed=None, stage=None):
    data = anchor.pools.train
    return dict(expected_unit=unit or data.unit,
                expected_seed=data.seed if seed is None else seed,
                expected_stage=stage or data.stage,
                expected_source_commit=COMMIT,
                expected_anchor_sha256=anchor.anchor_sha256)


@pytest.fixture(scope="module")
def capture():
    return C.collect_pools_with_anchors(
        UnitSpec(n_transitions=20, n_objects=2), stage="config_sweep", seed=7,
    )


@pytest.fixture
def anchor(tmp_path, capture):
    data = capture.pools.train
    return A.write_pool_anchors(tmp_path / "anchors", capture, unit=data.unit,
                               seed=data.seed, stage=data.stage, source_commit=COMMIT)


@pytest.mark.parametrize("stage,arm,withheld", [
    ("exp1", "baseline", ()), ("config_sweep", "baseline", ()),
    ("exp2a", "baseline", ("shape",)), ("exp2a", "feature_repair", ("shape",)),
    ("exp1", "data_repair", ()), ("exp2b", "capacity_repair", ()),
])
def test_capture_shares_exact_old_arrays_and_provenance(stage, arm, withheld):
    unit = UnitSpec(n_transitions=20, hidden_size=16, withheld_features=withheld)
    old = C.collect_pools(unit, stage=stage, seed=8, arm=arm)
    captured = C.collect_pools_with_anchors(unit, stage=stage, seed=8, arm=arm)
    A.assert_pools_equal(old, captured.pools)
    for pool in ("train", "validation", "evaluation"):
        assert len(getattr(captured, pool)) == len(getattr(old, pool))


def test_capture_does_not_add_transitions_policy_calls_or_global_rng_draws(monkeypatch):
    calls = {"transition": 0, "act": 0, "reset": 0}
    for owner, name in ((GridWorld, "transition"), (ExploratoryPolicy, "act"),
                        (ExploratoryPolicy, "reset")):
        original = getattr(owner, name)
        def counted(self, *args, _method=original, _name=name, **kwargs):
            calls[_name] += 1
            return _method(self, *args, **kwargs)
        monkeypatch.setattr(owner, name, counted)
    before = np.random.get_state()
    torch_before = torch.random.get_rng_state().clone()
    result = C.collect_with_anchors(UnitSpec(n_transitions=21), seed=7)
    assert calls == {"transition": 21, "act": 21, "reset": 3}
    after = np.random.get_state()
    assert before[0] == after[0] and np.array_equal(before[1], after[1])
    assert before[2:] == after[2:]
    assert torch.equal(torch_before, torch.random.get_rng_state())
    for i, t in enumerate(result.transitions):
        assert t.action == result.dataset.action[i]
        assert (t.episode, t.step) == (i // 10, i % 10)
        if t.step:
            assert t.state is result.transitions[i - 1].next_state


@pytest.mark.parametrize("kwargs", [
    {"n_transitions": 99}, {"episode_length": 11}, {"policy": object()},
])
def test_capture_preserves_confirmatory_refusals(kwargs):
    with pytest.raises(ValueError):
        C.collect_with_anchors(UnitSpec(n_transitions=100), seed=1000, **kwargs)


def test_capture_preserves_exact_training_prefix():
    unit = UnitSpec(n_transitions=20)
    baseline = C.collect_with_anchors(unit, stage="config_sweep", seed=8)
    extended = C.collect_with_anchors(unit, stage="config_sweep", seed=8, arm="data_repair")
    assert extended.transitions[:20] == baseline.transitions
    np.testing.assert_array_equal(extended.dataset.obs[:20], baseline.dataset.obs)


def test_round_trip_full_metadata_arrays_and_scale(anchor, capture):
    back = A.load_pool_anchors(anchor.path, **_expected(anchor), expected_pools=capture.pools)
    assert back.captured.train == capture.train
    assert back.captured.validation == capture.validation
    assert back.captured.evaluation == capture.evaluation
    A.assert_pools_equal(back.pools, capture.pools)
    document = json.loads((anchor.path / A.POOL_ANCHOR_FILE).read_text())
    identity = document["identity"]
    unit = capture.pools.train.unit
    config = Config(unit=unit, seed=7, stage="config_sweep")
    assert (identity["fit_id"], identity["execution_run_id"], identity["unit_id"]) == (
        config.fit_id, config.run_id, config.unit_id)
    assert identity["source_commit"] == COMMIT
    assert identity["data_keys"] == {
        purpose: dict(stream_key(unit, "config_sweep", purpose), seed=7)
        for purpose in DATA_PURPOSES
    }
    assert document["capture_kind"] == "contemporaneous"
    assert document["experimenter_only"] is True
    move = np.isin(capture.pools.evaluation.action, MOVEMENT_ACTIONS)
    want = NormalisationScale.from_evaluation_pool(
        torch.as_tensor(capture.pools.evaluation.next_obs)[move][:, [0, 1]])
    assert back.scale.as_row() == want.as_row()
    assert len(list(anchor.path.iterdir())) == 22
    assert not (anchor.path / A.POOL_ANCHOR_LINK_FILE).exists()


def test_anchor_is_copy_stable_and_identical_write_is_idempotent(anchor, capture, tmp_path):
    snapshot = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in anchor.path.iterdir()}
    repeated = A.write_pool_anchors(anchor.path, capture, unit=capture.pools.train.unit,
                                   seed=7, stage="config_sweep", source_commit=COMMIT)
    assert repeated.anchor_sha256 == anchor.anchor_sha256
    assert snapshot == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in anchor.path.iterdir()}
    target = tmp_path / "independent-copy"
    shutil.copytree(anchor.path, target)
    copied = A.load_pool_anchors(target, **_expected(anchor))
    assert copied.anchor_sha256 == anchor.anchor_sha256
    assert copied.path != anchor.path


def test_existing_divergent_bytes_never_overwritten(anchor, capture):
    target = anchor.path / "train.obs.npy"
    target.write_bytes(b"preserved divergent partial")
    with pytest.raises(DivergentTargetError):
        A.write_pool_anchors(anchor.path, capture, unit=capture.pools.train.unit,
                            seed=7, stage="config_sweep", source_commit=COMMIT)
    assert target.read_bytes() == b"preserved divergent partial"


@pytest.mark.parametrize("field,value", [
    ("expected_source_commit", "c" * 40), ("expected_seed", 8),
    ("expected_stage", "exp3_repairs"), ("expected_stage", "exp1"),
    ("expected_anchor_sha256", "0" * 64), ("expected_seed", True),
    ("expected_source_commit", "HEAD"),
])
def test_independent_expectations_are_mandatory(anchor, field, value):
    expected = _expected(anchor)
    expected[field] = value
    with pytest.raises(ValueError):
        A.load_pool_anchors(anchor.path, **expected)


@pytest.mark.parametrize("field", ["obs", "next_obs", "action", "episode", "step", "state", "next_state"])
def test_every_array_digest_is_checked(anchor, field):
    path = anchor.path / f"train.{field}.npy"
    path.write_bytes(path.read_bytes()[:-1] + b"!")
    with pytest.raises(ValueError, match="digest"):
        A.load_pool_anchors(anchor.path, **_expected(anchor))


def _resign_manifest(anchor, mutate):
    path = anchor.path / A.POOL_ANCHOR_FILE
    document = json.loads(path.read_text())
    mutate(document)
    path.write_bytes(A._json(document))
    expected = _expected(anchor)
    expected["expected_anchor_sha256"] = sha256_file(path)
    return expected


@pytest.mark.parametrize("mutation", [
    lambda d: d["identity"]["data_keys"]["env"].update(group="0" * 12),
    lambda d: d["identity"].update(source_commit="c" * 40),
    lambda d: d.update(pool_anchor_schema_version=True),
    lambda d: d.update(capture_kind="reconstructed"),
    lambda d: d.update(experimenter_only=False),
    lambda d: d["encoding"].update(observation_slot_order="raster"),
    lambda d: d["normalisation"].update(scale=[1.0, 1.0]),
    lambda d: d["normalisation"].update(scale_n_reference=1),
    lambda d: d["coverage"]["train"].update(n_transitions=1),
    lambda d: d["arrays"]["train"]["obs"].update(path="../train.obs.npy"),
    lambda d: d["arrays"]["train"]["obs"].update(dtype="<f8"),
    lambda d: d["arrays"]["train"].pop("state"),
    lambda d: d.update(extra="unregistered"),
])
def test_resigned_metadata_cannot_override_derived_contract(anchor, mutation):
    expected = _resign_manifest(anchor, mutation)
    with pytest.raises(ValueError):
        A.load_pool_anchors(anchor.path, **expected)


@pytest.mark.parametrize("field,mutate", [
    ("obs", lambda a: a.__setitem__((0, 0), 0.0)),
    ("state", lambda a: a.__setitem__((0, 4), 2)),
    ("action", lambda a: a.__setitem__(0, 9)),
    ("episode", lambda a: a.__setitem__(0, 1)),
    ("step", lambda a: a.__setitem__(0, 1)),
])
def test_resigned_arrays_still_need_valid_symbolic_content(anchor, field, mutate):
    path = anchor.path / f"train.{field}.npy"
    array = np.load(path, allow_pickle=False)
    mutate(array)
    path.write_bytes(A._array_bytes(array))
    expected = _resign_manifest(anchor, lambda d: d["arrays"]["train"][field].update(sha256=sha256_file(path)))
    with pytest.raises(ValueError):
        A.load_pool_anchors(anchor.path, **expected)


def test_noncanonical_trailing_npy_data_refused_even_if_resigned(anchor):
    path = anchor.path / "train.action.npy"
    path.write_bytes(path.read_bytes() + b"hidden trailing payload")
    expected = _resign_manifest(anchor, lambda d: d["arrays"]["train"]["action"].update(sha256=sha256_file(path)))
    with pytest.raises(ValueError, match="noncanonical"):
        A.load_pool_anchors(anchor.path, **expected)


def test_missing_and_unregistered_artifacts_are_refused(anchor):
    extra = anchor.path / "unregistered.npy"
    extra.write_bytes(b"extra")
    with pytest.raises(ValueError, match="unregistered artifact"):
        A.load_pool_anchors(anchor.path, **_expected(anchor))
    extra.unlink()
    (anchor.path / "train.state.npy").unlink()
    with pytest.raises(ValueError, match="missing anchor"):
        A.load_pool_anchors(anchor.path, **_expected(anchor))


def test_writer_refuses_wrong_or_modified_exact_pools_before_output(capture, tmp_path):
    wrong = copy.deepcopy(capture)
    wrong.pools.train.obs[0, 0] = 0.0
    with pytest.raises(ValueError, match="re-encoding"):
        A.write_pool_anchors(tmp_path / "must-not-exist", wrong, unit=capture.pools.train.unit,
                            seed=7, stage="config_sweep", source_commit=COMMIT)
    assert not (tmp_path / "must-not-exist").exists()


def test_readback_compares_exact_objects_consumed_by_training(anchor, capture):
    other = copy.deepcopy(capture.pools)
    other.validation.action[0] = (other.validation.action[0] + 1) % 5
    with pytest.raises(ValueError, match="exact consumed pool"):
        A.load_pool_anchors(anchor.path, **_expected(anchor), expected_pools=other)


def test_feature_restoration_requires_reencoding_not_column_deletion():
    hidden = UnitSpec(n_objects=2, withheld_features=("position",))
    full = Arm("feature_repair").resolve(hidden)
    state = GridState((3, 3), (
        GridObject(1, 1, "triangle", "red", True),
        GridObject(2, 1, "square", "blue", False),
    ))
    transition = C.SymbolicTransition(state, 0, replace(state, agent=(3, 2)), 0, 0)
    latent = (transition,)
    restored = A.reencode_anchors(latent, full)
    masked = A.reencode_anchors(latent, hidden)
    encoder = ObservationEncoder(full.n_objects, full.grid_size)
    columns = [i for b in encoder.blocks if not b.name.endswith("_position") or b.name == "agent_position"
               for i in range(b.start, b.stop)]
    assert not np.array_equal(restored[:, columns], masked)
    np.testing.assert_array_equal(masked[0], ObservationEncoder(2, 8, ("position",)).encode(state))
    np.testing.assert_array_equal(restored[:, :2], masked[:, :2])
    np.testing.assert_array_equal(A.reencode_anchors(latent, full, next_state=True)[:, :2],
                                  A.reencode_anchors(latent, hidden, next_state=True)[:, :2])


def _synthetic_linked_fit(tmp_path, *, mutate_metrics=None):
    """Registered bytes through the real fit reader, no trained model."""
    from test_fit_evidence import _completed_run, _rewrite_unsealed_sources
    from bu.experiments import fit_evidence as F
    from bu.experiments.confirmatory import _digest_pool

    fit_dir = tmp_path / "fit"
    completed, spec = _completed_run(fit_dir)
    captured = C.collect_pools_with_anchors(spec.unit, seed=spec.seed, stage=spec.execution_stage)
    anchor = A.write_pool_anchors(fit_dir / A.POOL_ANCHORS_DIRECTORY, captured,
                                 unit=spec.unit, seed=spec.seed, stage=spec.execution_stage,
                                 source_commit=COMMIT)
    evaluation = captured.pools.evaluation
    keep = np.isin(evaluation.action, MOVEMENT_ACTIONS)
    n = int(keep.sum())
    diagnostics = dict(completed.diagnostics)
    for key, lo, hi in (("error", 1., 2.), ("disagreement", .2, .8), ("predictive_variance", .1, .4)):
        diagnostics[key] = np.linspace(lo, hi, n, dtype=np.float32)
    diagnostics.update(episode=evaluation.episode[keep], step=evaluation.step[keep],
                       evaluation_action=evaluation.action,
                       scale=np.asarray(anchor.scale.vector, dtype=np.float64),
                       scale_n_reference=np.asarray(n))
    error, disagreement, variance = (diagnostics[x] for x in ("error", "disagreement", "predictive_variance"))
    def update(run, summary):
        digest = _digest_pool(captured.pools)
        run["extra"]["evaluation_pool_digest"] = digest
        summary.update(evaluation_pool_digest=digest, normalisation=anchor.scale.as_row(),
                       mean_error=float(error.mean()), mean_disagreement=float(disagreement.mean()),
                       mean_predictive_variance=float(variance.mean()),
                       ratio=float(disagreement.mean()) / float(error.mean()))
        metrics = Path(completed.record_dir) / "metrics.jsonl"
        rows = [json.loads(line) for line in metrics.read_text().splitlines()]
        for row in rows:
            row["i"] += 1
        rows.insert(0, dict(i=0, event="pool_anchors", pool_anchor_schema_version=1,
                            pool_anchor_sha256=anchor.sha))
        if mutate_metrics is not None:
            mutate_metrics(rows)
        raw = b"".join((json.dumps(row) + "\n").encode() for row in rows)
        metrics.write_bytes(raw)
        summary["member_record_digest"] = hashlib.sha256(raw).hexdigest()
    completed = _rewrite_unsealed_sources(completed, update)
    completed = replace(completed, diagnostics=diagnostics,
                        mean_disagreement=float(disagreement.mean()),
                        evaluation=replace(completed.evaluation, error=error,
                                           episode=diagnostics["episode"], step=diagnostics["step"],
                                           scale=anchor.scale))
    F.write_fit_evidence(completed, fit_dir=fit_dir)
    return anchor, fit_dir


def test_afterfit_link_reopens_real_strict_sidecar_and_does_not_mutate_sources(tmp_path):
    anchor, fit_dir = _synthetic_linked_fit(tmp_path)
    expected = _expected(anchor)
    before = {p.relative_to(fit_dir): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in fit_dir.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="missing anchor"):
        A.load_pool_anchor_link(anchor.path, fit_dir, **expected)
    link = A.link_pool_anchors(anchor.path, fit_dir, **expected)
    assert link.name == A.POOL_ANCHOR_LINK_FILE
    assert A.load_pool_anchor_link(anchor.path, fit_dir, **expected).anchor_sha256 == anchor.anchor_sha256
    A.link_pool_anchors(anchor.path, fit_dir, **expected)
    assert before == {p: ((fit_dir / p).read_bytes(), (fit_dir / p).stat().st_mtime_ns) for p in before}
    document = json.loads(link.read_text())
    assert document["fit_evidence_sha256"] == sha256_file(fit_dir / "fit_evidence.json")
    document["fit_execution_digest"] = "0" * 64
    link.write_bytes(A._json(document))
    with pytest.raises(ValueError, match="linkage differs"):
        A.load_pool_anchor_link(anchor.path, fit_dir, **expected)


def test_afterfit_link_refuses_changed_source_bytes(tmp_path):
    anchor, fit_dir = _synthetic_linked_fit(tmp_path)
    expected = _expected(anchor)
    A.link_pool_anchors(anchor.path, fit_dir, **expected)
    sidecar = fit_dir / "fit_evidence.json"
    sidecar.write_bytes(sidecar.read_bytes() + b" ")
    with pytest.raises(ValueError):
        A.load_pool_anchor_link(anchor.path, fit_dir, **expected)


@pytest.mark.parametrize("mutate", [
    lambda rows: rows[0].update(pool_anchor_sha256="0" * 64),
    lambda rows: rows[0].update(pool_anchor_schema_version=True),
    lambda rows: rows[0].update(i=False),
    lambda rows: rows[0].update(extra="unregistered"),
    lambda rows: (rows.reverse(), [row.update(i=i) for i, row in enumerate(rows)]),
    lambda rows: (rows.pop(0), rows[0].update(i=0)),
    lambda rows: rows.append(dict(rows[0], i=2)),
])
def test_fully_sealed_wrong_missing_late_or_duplicate_anchor_event_refused(tmp_path, mutate):
    anchor, fit_dir = _synthetic_linked_fit(tmp_path, mutate_metrics=mutate)
    with pytest.raises(ValueError, match="first sealed metrics event"):
        A.link_pool_anchors(anchor.path, fit_dir, **_expected(anchor))
    assert not (anchor.path / A.POOL_ANCHOR_LINK_FILE).exists()


def test_reencoded_feature_capture_retains_identical_latent_trajectories():
    unit = UnitSpec(n_transitions=20, n_objects=2, withheld_features=("position",))
    baseline = C.collect_with_anchors(unit, stage="config_sweep", seed=7)
    restored = C.collect_with_anchors(unit, stage="config_sweep", seed=7, arm="feature_repair")
    assert restored.transitions == baseline.transitions
    np.testing.assert_array_equal(
        A.reencode_anchors(restored.transitions, unit), baseline.dataset.obs)
    np.testing.assert_array_equal(
        A.reencode_anchors(baseline.transitions, Arm("feature_repair").resolve(unit)), restored.dataset.obs)


@pytest.mark.parametrize("mutation", [
    lambda c: setattr(c.pools.train, "episode_length", 10.0),
    lambda c: setattr(c.pools.train, "stream_version", 3.0),
    lambda c: setattr(c.pools.train, "source_unit", None),
    lambda c: setattr(c.pools.train, "arm", "data_repair"),
])
def test_writer_rejects_bad_pool_provenance_before_any_output(capture, tmp_path, mutation):
    changed = copy.deepcopy(capture)
    mutation(changed)
    path = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="provenance"):
        A.write_pool_anchors(path, changed, unit=capture.pools.train.unit,
                            seed=7, stage="config_sweep", source_commit=COMMIT)
    assert not path.exists()


def test_symlinked_anchor_file_refused(anchor, tmp_path):
    file = anchor.path / "train.obs.npy"
    real = tmp_path / "outside.npy"
    shutil.copyfile(file, real)
    file.unlink()
    try:
        file.symlink_to(real)
    except OSError:
        pytest.skip("host has no symlink permission")
    with pytest.raises(ValueError, match="link/reparse"):
        A.load_pool_anchors(anchor.path, **_expected(anchor))
