"""One physical fit, many honest obligation projections.

All evidence here is synthetic.  The tests exercise persistence and refusal
boundaries only; they do not train, inspect real confirmatory results, or create
scientific labels.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Arm, Config
from bu.env.gridworld import INTERACT, N_ACTIONS
from bu.experiments import fit_evidence as F
from bu.experiments.confirmatory import ConfirmatoryRun
from bu.experiments.enumerate_units import design_units, execution_plan
from bu.experiments.repair import ArmEvaluation
from bu.models.uncertainty import NormalisationScale
from bu.models.world_model import MOVEMENT_ACTIONS
from bu.runrecord import GitState


def _registered_shared_fit():
    return next(
        fit
        for fit in execution_plan(design_units())
        if fit.arm == "baseline" and fit.seed == 0 and len(fit.roles) > 1
    )


def _json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _completed_run(
    root: Path,
    *,
    diagnostics: bool = True,
    stage: str | None = None,
    arm: str = "baseline",
) -> tuple[ConfirmatoryRun, F.RegisteredFitSpec]:
    planned = (
        _registered_shared_fit()
        if arm == "baseline"
        else next(
            fit
            for fit in execution_plan(design_units())
            if fit.arm == arm and fit.seed == 0
        )
    )
    seed = K.CONFIRMATORY_SEED_BASE + planned.seed
    spec = F.registered_fit_spec(planned.unit, arm=planned.arm, seed=seed)
    execution_stage = spec.execution_stage if stage is None else stage
    config = Config(
        unit=planned.unit,
        arm=Arm(planned.arm),
        train=(F.CONFIRMATORY_TRAIN if arm == "baseline" else F.REPAIRED_TRAIN),
        seed=seed,
        stage=execution_stage,
    )
    record_dir = root / config.run_id
    record_dir.mkdir(parents=True)
    threading = {
        "num_threads": F.CONFIRMATORY_THREADS,
        "num_interop_threads": F.CONFIRMATORY_INTEROP_THREADS,
    }
    pool_digest = "a" * 64
    role_run_ids = {role: spec.run_id_for(role) for role in spec.roles}
    effective_unit = Config(unit=config.effective_unit).to_dict()["unit"]
    base_unit = config.to_dict()["unit"]
    run_record = {
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        "fit_id": config.fit_id,
        "seed": seed,
        "stage": execution_stage,
        "seed_partition": "confirmatory",
        "confirmatory": True,
        "schema_version": F.SCHEMA_VERSION,
        "identity_version": F.IDENTITY_VERSION,
        "unit_identity_fields": list(F.UNIT_IDENTITY_FIELDS),
        "started_utc": "2026-08-30T00:00:00+00:00",
        "config": config.to_dict(),
        "effective_unit": effective_unit,
        "arm_changed": {
            name: value
            for name, value in effective_unit.items()
            if base_unit[name] != value
        },
        "git": {
            "commit": "b" * 40,
            "branch": "main",
            "dirty": False,
            "trustworthy": True,
        },
        "env": {
            "python": "3.11.9",
            "platform": "synthetic-test-platform",
            "packages": dict(F._FROZEN_PACKAGE_VERSIONS),
        },
        "extra": {
            "granularity": "episode",
            "seed_partition": "confirmatory",
            "evaluation_pool_digest": pool_digest,
            "threading": threading,
            "device": F.CONFIRMATORY_DEVICE,
            "fit_roles": list(spec.roles),
            "role_run_ids": role_run_ids,
        },
    }
    run_bytes = _json_bytes(run_record)
    (record_dir / "run.json").write_bytes(run_bytes)
    metrics_bytes = b'{"i":0,"record_type":"member","member":0}\n'
    (record_dir / "metrics.jsonl").write_bytes(metrics_bytes)

    n_evaluation = K.EVALUATION_EPISODES * K.EPISODE_LENGTH
    full_episode = np.repeat(
        np.arange(K.EVALUATION_EPISODES, dtype=np.int32), K.EPISODE_LENGTH
    )
    full_step = np.tile(
        np.arange(K.EPISODE_LENGTH, dtype=np.int32), K.EVALUATION_EPISODES
    )
    # Three noncontiguous INTERACT positions per episode make this an
    # adversarially useful movement subset rather than a convenient prefix.
    action_pattern = np.asarray(
        [0, INTERACT, 1, 2, INTERACT, 3, 0, INTERACT, 2, 3], dtype=np.int32
    )
    evaluation_action = np.tile(action_pattern, K.EVALUATION_EPISODES)
    movement = np.isin(evaluation_action, np.asarray(MOVEMENT_ACTIONS))
    episode = full_episode[movement]
    step = full_step[movement]
    n_movement = int(movement.sum())
    error = np.linspace(1.0, 2.0, n_movement, dtype=np.float32)
    disagreement = np.linspace(0.2, 0.8, n_movement, dtype=np.float32)
    variance = np.linspace(0.1, 0.4, n_movement, dtype=np.float32)
    scale = NormalisationScale(
        torch.tensor([1.0, 2.0]), n_reference=n_movement
    )
    diagnostic_arrays = {
        "evaluation_action": evaluation_action,
        "episode": episode,
        "step": step,
        "error": error,
        "disagreement": disagreement,
        "predictive_variance": variance,
        "scale": np.asarray([1.0, 2.0], dtype=np.float64),
        "scale_n_reference": np.asarray(n_movement),
        "scale_domain": np.asarray(scale.domain),
        "scale_source": np.asarray(scale.source),
    }
    summaries = {
        "mean_error": float(error.mean()),
        "mean_disagreement": (
            float(disagreement.mean()) if arm == "baseline" else None
        ),
        "mean_predictive_variance": (
            float(variance.mean()) if arm == "baseline" else None
        ),
        "ratio": (
            float(disagreement.mean()) / float(error.mean())
            if arm == "baseline"
            else None
        ),
    }
    if arm != "baseline":
        diagnostic_arrays.pop("disagreement")
        diagnostic_arrays.pop("predictive_variance")
    confirmation = {
        "config": config.to_dict(),
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        "fit_id": config.fit_id,
        "seed": seed,
        "arm": planned.arm,
        "stage": execution_stage,
        "seed_partition": "confirmatory",
        "granularity": "episode",
        "member_count": config.train.ensemble_size,
        "member_indices": list(range(config.train.ensemble_size)),
        "member_record_digest": _digest(metrics_bytes),
        "run_record_digest": _digest(run_bytes),
        "evaluation_pool_digest": pool_digest,
        "normalisation": scale.as_row(),
        "metric_schema_version": F.METRIC_SCHEMA_VERSION,
        "threading": threading,
        "device": F.CONFIRMATORY_DEVICE,
        "fit_roles": list(spec.roles),
        "role_run_ids": role_run_ids,
        "n_train": config.effective_unit.n_transitions,
        **summaries,
    }
    (record_dir / "confirmatory.json").write_bytes(_json_bytes(confirmation))
    evaluation = ArmEvaluation(
        arm=planned.arm,
        seed=seed,
        error=error,
        episode=episode,
        step=step,
        scale=scale,
        config_id=config.config_id,
        run_id=config.run_id,
        n_train=config.effective_unit.n_transitions,
        stage=execution_stage,
        ensemble_size=config.train.ensemble_size,
    )
    completed = ConfirmatoryRun(
        run_id=config.run_id,
        config_id=config.config_id,
        unit_id=config.unit_id,
        fit_id=config.fit_id,
        stage=execution_stage,
        arm=planned.arm,
        seed=seed,
        n_train=config.effective_unit.n_transitions,
        member_count=config.train.ensemble_size,
        mean_disagreement=(
            summaries["mean_disagreement"]
            if summaries["mean_disagreement"] is not None
            else float("nan")
        ),
        record_dir=record_dir,
        run=confirmation,
        evaluation=evaluation,
        diagnostics=diagnostic_arrays if diagnostics else None,
    )
    return completed, spec


def _sidecar(root: Path) -> dict:
    return json.loads((root / F.FIT_EVIDENCE_FILE).read_text())


def _resign(root: Path, mutate) -> None:
    document = _sidecar(root)
    mutate(document)
    payload = {
        key: value for key, value in document.items() if key != "execution_digest"
    }
    document["execution_digest"] = F._execution_digest(payload)
    (root / F.FIT_EVIDENCE_FILE).write_bytes(F._canonical_json_bytes(document))


def _rewrite_unsealed_sources(completed: ConfirmatoryRun, mutate) -> ConfirmatoryRun:
    """Make two physical documents agree before the writer sees them."""

    record_dir = Path(completed.record_dir)
    run_path = record_dir / "run.json"
    confirmatory_path = record_dir / "confirmatory.json"
    run_record = json.loads(run_path.read_text())
    confirmation = json.loads(confirmatory_path.read_text())
    mutate(run_record, confirmation)
    run_bytes = _json_bytes(run_record)
    run_path.write_bytes(run_bytes)
    confirmation["run_record_digest"] = _digest(run_bytes)
    confirmatory_path.write_bytes(_json_bytes(confirmation))
    return replace(completed, run=confirmation)


def _resign_physical_sources(root: Path, mutate, *, mutate_procedure=None) -> None:
    """Resign the complete source/sidecar chain after an adversarial mutation."""

    document = _sidecar(root)
    run_path = root / Path(document["artifacts"]["run_record"]["path"])
    confirmation_path = root / Path(document["artifacts"]["confirmatory"]["path"])
    run_record = json.loads(run_path.read_text())
    confirmation = json.loads(confirmation_path.read_text())
    mutate(run_record, confirmation)
    run_bytes = _json_bytes(run_record)
    run_path.write_bytes(run_bytes)
    confirmation["run_record_digest"] = _digest(run_bytes)
    confirmation_bytes = _json_bytes(confirmation)
    confirmation_path.write_bytes(confirmation_bytes)
    document["artifacts"]["run_record"]["sha256"] = _digest(run_bytes)
    document["artifacts"]["confirmatory"]["sha256"] = _digest(
        confirmation_bytes
    )
    if mutate_procedure is not None:
        mutate_procedure(document["procedure"])
    payload = {
        key: value for key, value in document.items() if key != "execution_digest"
    }
    document["execution_digest"] = F._execution_digest(payload)
    (root / F.FIT_EVIDENCE_FILE).write_bytes(F._canonical_json_bytes(document))


def _set_nested(document: dict, path: tuple[str, ...], value) -> None:
    target = document
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value


_PROVENANCE_MUTATIONS = [
    ("schema-version", ("schema_version",), 1, "schema_version"),
    ("identity-version", ("identity_version",), 1, "identity_version"),
    (
        "identity-fields",
        ("unit_identity_fields",),
        list(reversed(F.UNIT_IDENTITY_FIELDS)),
        "unit_identity_fields",
    ),
    (
        "started-utc",
        ("started_utc",),
        "2026-08-30T00:00:00",
        "started_utc",
    ),
    (
        "effective-unit",
        ("effective_unit", "n_transitions"),
        1,
        "effective_unit",
    ),
    (
        "arm-changed",
        ("arm_changed", "n_transitions"),
        1,
        "arm_changed",
    ),
    ("git-commit", ("git", "commit"), "UNCOMMITTED", "git.commit"),
    ("git-branch", ("git", "branch"), "unknown", "git.branch"),
    ("git-dirty", ("git", "dirty"), True, "clean and trustworthy"),
    ("git-trustworthy", ("git", "trustworthy"), False, "clean and trustworthy"),
    ("python", ("env", "python"), "3.10.9", "Python >= 3.11"),
    ("platform", ("env", "platform"), "", "env.platform"),
] + [
    (
        f"package-{package}",
        ("env", "packages", package),
        "0.0.invalid",
        "frozen runtime pins",
    )
    for package in F.TRACKED_PACKAGES
]


def _mutate_frozen_procedure(
    run_record: dict, confirmation: dict, field: str, value
) -> None:
    if field.startswith("train."):
        name = field.removeprefix("train.")
        run_record["config"]["train"][name] = value
        confirmation["config"]["train"][name] = value
        return
    if field.startswith("threading."):
        name = field.removeprefix("threading.")
        run_record["extra"]["threading"][name] = value
        confirmation["threading"][name] = value
        return
    if field == "device":
        run_record["extra"]["device"] = value
        confirmation["device"] = value
        return
    if field == "metric_schema_version":
        confirmation["metric_schema_version"] = value
        return
    raise AssertionError(f"unknown synthetic procedure mutation {field!r}")


def _mutate_sidecar_procedure(procedure: dict, field: str, value) -> None:
    if field.startswith("train."):
        procedure["train"][field.removeprefix("train.")] = value
    elif field.startswith("threading."):
        procedure["threading"][field.removeprefix("threading.")] = value
    else:
        procedure[field] = value


def _replace_diagnostic(root: Path, name: str, array: np.ndarray) -> None:
    document = _sidecar(root)
    path = root / Path(document["artifacts"][name]["path"])
    path.write_bytes(F._npy_bytes(array))

    def update(doc):
        doc["artifacts"][name]["sha256"] = _digest(path.read_bytes())

    _resign(root, update)


def _drop_diagnostics(root: Path, names: set[str]) -> None:
    document = _sidecar(root)
    for name in names:
        (root / Path(document["artifacts"][name]["path"])).unlink()

    def update(doc):
        for name in names:
            doc["artifacts"].pop(name)
        doc["procedure"]["diagnostic_names"] = [
            name
            for name in doc["procedure"]["diagnostic_names"]
            if name not in names
        ]

    _resign(root, update)


def test_registry_derives_roles_and_deterministic_execution_stage():
    planned = _registered_shared_fit()
    spec = F.registered_fit_spec(
        planned.unit,
        arm=planned.arm,
        seed=K.CONFIRMATORY_SEED_BASE + planned.seed,
    )
    assert spec.roles == tuple(sorted(planned.roles))
    assert spec.execution_stage == spec.roles[0]
    assert len(spec.roles) > 1
    assert len({spec.run_id_for(role) for role in spec.roles}) == len(spec.roles)


def test_fit_evidence_v2_is_the_first_procedure_authoritative_schema():
    assert F.FIT_EVIDENCE_SCHEMA_VERSION == 2


def test_launch_bound_fit_refuses_a_clean_new_commit_before_runner_or_output(
    monkeypatch, tmp_path
):
    planned = _registered_shared_fit()
    calls = []
    monkeypatch.setattr(
        F,
        "git_state",
        lambda: GitState(commit="c" * 40, dirty=False, branch="main"),
    )
    monkeypatch.setattr(
        F,
        "run_confirmatory",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    with pytest.raises(ValueError, match="launch-bound preflight commit"):
        F.run_confirmatory_fit(
            planned.unit,
            arm=planned.arm,
            seed=K.CONFIRMATORY_SEED_BASE + planned.seed,
            out_dir=tmp_path / "must-not-exist",
            expected_git_commit="b" * 40,
        )

    assert calls == []
    assert not (tmp_path / "must-not-exist").exists()


def test_loader_refuses_valid_fit_evidence_from_a_different_clean_commit(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)

    with pytest.raises(ValueError, match="does not equal.*preflight commit"):
        F.load_fit_evidence(tmp_path, expected_git_commit="c" * 40)


@pytest.mark.parametrize("arm", ["baseline", "data_repair"])
@pytest.mark.parametrize(
    ("train_field", "bad"),
    [
        ("lr", 0.002),
        ("batch_size", 64),
        ("max_epochs", 1),
        ("patience", 10),
        ("ensemble_size", None),
        ("bootstrap_ratio", 0.5),
    ],
)
def test_writer_refuses_each_unregistered_arm_specific_training_field(
    tmp_path, arm, train_field, bad
):
    completed, _ = _completed_run(tmp_path, arm=arm)
    if train_field == "ensemble_size":
        bad = 1 if arm == "baseline" else K.DEFAULT_ENSEMBLE_SIZE
    completed = _rewrite_unsealed_sources(
        completed,
        lambda run, confirmation: _mutate_frozen_procedure(
            run, confirmation, f"train.{train_field}", bad
        ),
    )
    with pytest.raises(ValueError, match="not the frozen"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert not (tmp_path / F.FIT_EVIDENCE_FILE).exists()


@pytest.mark.parametrize("arm", ["baseline", "data_repair"])
@pytest.mark.parametrize(
    ("train_field", "bad"),
    [
        ("lr", 0.002),
        ("batch_size", 64),
        ("max_epochs", 1),
        ("patience", 10),
        ("ensemble_size", None),
        ("bootstrap_ratio", 0.5),
    ],
)
def test_loader_refuses_resigned_unregistered_arm_specific_training(
    tmp_path, arm, train_field, bad
):
    completed, _ = _completed_run(tmp_path, arm=arm)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    if train_field == "ensemble_size":
        bad = 1 if arm == "baseline" else K.DEFAULT_ENSEMBLE_SIZE
    field = f"train.{train_field}"
    _resign_physical_sources(
        tmp_path,
        lambda run, confirmation: _mutate_frozen_procedure(
            run, confirmation, field, bad
        ),
        mutate_procedure=lambda procedure: _mutate_sidecar_procedure(
            procedure, field, bad
        ),
    )
    with pytest.raises(ValueError, match="not the frozen"):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize(
    ("field", "bad", "message"),
    [
        ("threading.num_threads", 3, "frozen threading"),
        ("threading.num_interop_threads", 3, "frozen threading"),
        ("device", "cuda", "frozen device"),
        ("metric_schema_version", 999, "frozen schema"),
    ],
)
def test_writer_refuses_each_other_unregistered_procedure_field(
    tmp_path, field, bad, message
):
    completed, _ = _completed_run(tmp_path)
    completed = _rewrite_unsealed_sources(
        completed,
        lambda run, confirmation: _mutate_frozen_procedure(
            run, confirmation, field, bad
        ),
    )
    with pytest.raises(ValueError, match=message):
        F.write_fit_evidence(completed, fit_dir=tmp_path)


@pytest.mark.parametrize(
    ("field", "bad", "message"),
    [
        ("threading.num_threads", 3, "frozen threading"),
        ("threading.num_interop_threads", 3, "frozen threading"),
        ("device", "cuda", "frozen device"),
        ("metric_schema_version", 999, "frozen schema"),
    ],
)
def test_loader_refuses_each_resigned_unregistered_procedure_field(
    tmp_path, field, bad, message
):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    _resign_physical_sources(
        tmp_path,
        lambda run, confirmation: _mutate_frozen_procedure(
            run, confirmation, field, bad
        ),
        mutate_procedure=lambda procedure: _mutate_sidecar_procedure(
            procedure, field, bad
        ),
    )
    with pytest.raises(ValueError, match=message):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize(
    ("case", "path", "bad", "message"), _PROVENANCE_MUTATIONS
)
def test_writer_refuses_each_untrustworthy_or_incomplete_provenance_field(
    tmp_path, case, path, bad, message
):
    completed, _ = _completed_run(tmp_path)
    completed = _rewrite_unsealed_sources(
        completed,
        lambda run, confirmation: _set_nested(run, path, bad),
    )
    with pytest.raises(ValueError, match=message):
        F.write_fit_evidence(completed, fit_dir=tmp_path)


@pytest.mark.parametrize(
    ("case", "path", "bad", "message"), _PROVENANCE_MUTATIONS
)
def test_loader_refuses_each_resigned_untrustworthy_provenance_field(
    tmp_path, case, path, bad, message
):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    _resign_physical_sources(
        tmp_path,
        lambda run, confirmation: _set_nested(run, path, bad),
    )
    with pytest.raises(ValueError, match=message):
        F.load_fit_evidence(tmp_path)


def test_writer_and_loader_require_the_complete_run_record_inventory(tmp_path):
    completed, _ = _completed_run(tmp_path)
    completed = _rewrite_unsealed_sources(
        completed,
        lambda run, confirmation: run.pop("env"),
    )
    with pytest.raises(ValueError, match="run.json keys"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)

    second = tmp_path / "loader"
    completed, _ = _completed_run(second)
    F.write_fit_evidence(completed, fit_dir=second)
    _resign_physical_sources(
        second,
        lambda run, confirmation: run.pop("env"),
    )
    with pytest.raises(ValueError, match="run.json keys"):
        F.load_fit_evidence(second)


def test_round_trip_persists_every_diagnostic_and_projects_both_roles(tmp_path):
    completed, spec = _completed_run(tmp_path)
    sidecar = F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert sidecar == tmp_path / F.FIT_EVIDENCE_FILE
    document = _sidecar(tmp_path)
    expected_diagnostics = tuple(sorted(completed.diagnostics))
    assert tuple(document["procedure"]["diagnostic_names"]) == expected_diagnostics
    for name in expected_diagnostics:
        assert document["artifacts"][name]["path"] == f"evaluation/{name}.npy"
        assert (tmp_path / "evaluation" / f"{name}.npy").is_file()
    assert document["procedure"]["summaries"] == {
        name: completed.run[name]
        for name in F._SUMMARY_NAMES
    }

    verified = F.load_fit_evidence(tmp_path)
    assert verified.evaluation_pool_digest == "a" * 64
    assert tuple(verified.diagnostics) == expected_diagnostics
    assert verified.roles == spec.roles
    projections = [verified.for_role(role) for role in spec.roles]
    assert {item.stage for item in projections} == set(spec.roles)
    assert {item.run_id for item in projections} == {
        spec.run_id_for(role) for role in spec.roles
    }
    assert {item.config_id for item in projections} == {spec.config_id}
    assert all(item.scale is verified.scale for item in projections)
    assert all(item.error is verified.error for item in projections)
    assert not verified.error.flags.writeable


def test_repair_round_trip_requires_complete_error_identity_and_scale_evidence(
    tmp_path,
):
    completed, spec = _completed_run(tmp_path, arm="data_repair")
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    verified = F.load_fit_evidence(tmp_path)
    assert verified.arm == "data_repair"
    assert verified.roles == spec.roles
    assert tuple(verified.diagnostics) == F._REPAIR_DIAGNOSTICS
    assert "disagreement" not in verified.diagnostics
    assert "predictive_variance" not in verified.diagnostics


def test_sidecar_keeps_one_physical_run_and_one_metrics_stream(tmp_path):
    completed, spec = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert [path.parent.name for path in tmp_path.rglob("run.json")] == [
        spec.execution_run_id
    ]
    assert [path.parent.name for path in tmp_path.rglob("metrics.jsonl")] == [
        spec.execution_run_id
    ]
    for role in spec.roles:
        if role != spec.execution_stage:
            assert not (tmp_path / spec.run_id_for(role)).exists()


def test_absent_diagnostics_are_refused_without_a_core_only_fallback(tmp_path):
    completed, _ = _completed_run(tmp_path, diagnostics=False)
    with pytest.raises(ValueError, match="complete canonical.*never reconstructs"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert not (tmp_path / F.FIT_EVIDENCE_FILE).exists()
    assert not (tmp_path / "evaluation").exists()


@pytest.mark.parametrize("missing", F._BASELINE_DIAGNOSTICS)
def test_writer_refuses_each_missing_baseline_diagnostic(tmp_path, missing):
    completed, _ = _completed_run(tmp_path)
    supplied = dict(completed.diagnostics)
    supplied.pop(missing)
    completed = replace(completed, diagnostics=supplied)
    with pytest.raises(ValueError, match="baseline diagnostic inventory"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert not (tmp_path / "evaluation").exists()


@pytest.mark.parametrize("missing", F._REPAIR_DIAGNOSTICS)
def test_writer_refuses_each_missing_repair_diagnostic(tmp_path, missing):
    completed, _ = _completed_run(tmp_path, arm="data_repair")
    supplied = dict(completed.diagnostics)
    supplied.pop(missing)
    completed = replace(completed, diagnostics=supplied)
    with pytest.raises(ValueError, match="data_repair diagnostic inventory"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert not (tmp_path / "evaluation").exists()


def test_loader_refuses_a_resigned_core_only_baseline_sidecar(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    _drop_diagnostics(
        tmp_path,
        set(F._BASELINE_DIAGNOSTICS) - set(F._CORE_DIAGNOSTICS),
    )
    with pytest.raises(ValueError, match="baseline diagnostic inventory"):
        F.load_fit_evidence(tmp_path)


def test_repair_inventory_refuses_fabricated_spread_diagnostics(tmp_path):
    completed, _ = _completed_run(tmp_path, arm="data_repair")
    n_movement = len(completed.evaluation.error)
    supplied = {
        **completed.diagnostics,
        "disagreement": np.zeros(n_movement, dtype=np.float64),
        "predictive_variance": np.zeros(n_movement, dtype=np.float64),
    }
    completed = replace(completed, diagnostics=supplied)
    with pytest.raises(ValueError, match="data_repair diagnostic inventory"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)


def test_noncontiguous_movement_subset_is_exactly_derived_from_full_actions(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    verified = F.load_fit_evidence(tmp_path)
    actions = verified.diagnostics["evaluation_action"]
    movement = np.isin(actions, np.asarray(MOVEMENT_ACTIONS))
    full_episode = np.repeat(
        np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH
    )
    full_step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)
    movement_indices = np.flatnonzero(movement)
    assert len(actions) == K.EVALUATION_EPISODES * K.EPISODE_LENGTH
    assert len(verified.error) == int(movement.sum()) == 700
    assert np.any(np.diff(movement_indices) > 1)
    assert np.array_equal(verified.episode, full_episode[movement])
    assert np.array_equal(verified.step, full_step[movement])


def test_loader_refuses_dropped_movement_row_from_every_scored_array(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    for name in F._TRANSITION_DIAGNOSTICS:
        array = F._canonical_array(name, completed.diagnostics[name])
        _replace_diagnostic(tmp_path, name, np.delete(array, 17))
    with pytest.raises(ValueError, match="mask.*selects exactly 700 rows"):
        F.load_fit_evidence(tmp_path)


def test_loader_refuses_resigned_incomplete_repair_inventory(tmp_path):
    completed, _ = _completed_run(tmp_path, arm="data_repair")
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    _drop_diagnostics(tmp_path, {"scale_source"})
    with pytest.raises(ValueError, match="data_repair diagnostic inventory"):
        F.load_fit_evidence(tmp_path)


def test_loader_refuses_extra_movement_row_in_every_scored_array(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    for name in F._TRANSITION_DIAGNOSTICS:
        array = F._canonical_array(name, completed.diagnostics[name])
        _replace_diagnostic(tmp_path, name, np.append(array, array[-1]))
    with pytest.raises(ValueError, match="mask.*selects exactly 700 rows"):
        F.load_fit_evidence(tmp_path)


def test_loader_refuses_reordered_movement_rows_even_when_all_arrays_agree(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    for name in F._TRANSITION_DIAGNOSTICS:
        array = F._canonical_array(name, completed.diagnostics[name])
        array[[0, 1]] = array[[1, 0]]
        _replace_diagnostic(tmp_path, name, array)
    with pytest.raises(ValueError, match="do not equal exactly.*selected"):
        F.load_fit_evidence(tmp_path)


def test_loader_refuses_resigned_action_outside_registered_range(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    action = F._canonical_array(
        "evaluation_action", completed.diagnostics["evaluation_action"]
    )
    action[0] = N_ACTIONS
    _replace_diagnostic(tmp_path, "evaluation_action", action)
    with pytest.raises(ValueError, match=r"registered range \[0, 5\)"):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize(
    ("index", "replacement", "expected"),
    [(0, INTERACT, 699), (1, 0, 701)],
)
def test_loader_refuses_valid_range_action_tamper_that_changes_mask(
    tmp_path, index, replacement, expected
):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    action = F._canonical_array(
        "evaluation_action", completed.diagnostics["evaluation_action"]
    )
    action[index] = replacement
    _replace_diagnostic(tmp_path, "evaluation_action", action)
    with pytest.raises(ValueError, match=rf"mask.*selects exactly {expected} rows"):
        F.load_fit_evidence(tmp_path)


def test_loader_refuses_same_size_mismatched_action_mask(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    action = F._canonical_array(
        "evaluation_action", completed.diagnostics["evaluation_action"]
    )
    action[[0, 1]] = action[[1, 0]]
    _replace_diagnostic(tmp_path, "evaluation_action", action)
    with pytest.raises(ValueError, match="do not equal exactly.*selected"):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda action: action[:-1], "exactly 1000 actions"),
        (lambda action: action.reshape(100, 10), "one-dimensional"),
        (lambda action: action.astype(np.float64), "integers"),
    ],
)
def test_writer_refuses_noncanonical_full_action_inventory(
    tmp_path, mutate, message
):
    completed, _ = _completed_run(tmp_path)
    supplied = dict(completed.diagnostics)
    supplied["evaluation_action"] = mutate(supplied["evaluation_action"])
    completed = replace(completed, diagnostics=supplied)
    with pytest.raises(ValueError, match=message):
        F.write_fit_evidence(completed, fit_dir=tmp_path)


def test_loader_refuses_resigned_short_full_action_inventory(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    action = F._canonical_array(
        "evaluation_action", completed.diagnostics["evaluation_action"]
    )[:-1]
    _replace_diagnostic(tmp_path, "evaluation_action", action)
    with pytest.raises(ValueError, match="exactly 1000 actions"):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize("name", ["error", "disagreement", "predictive_variance"])
def test_loader_refuses_resigned_negative_baseline_diagnostic(tmp_path, name):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    array = np.asarray(completed.diagnostics[name], dtype=np.dtype("<f8"))
    array[17] = -0.001
    _replace_diagnostic(tmp_path, name, array)
    with pytest.raises(ValueError, match=f"{name}.*non-negative"):
        F.load_fit_evidence(tmp_path)


def test_loader_refuses_resigned_negative_repair_error(tmp_path):
    completed, _ = _completed_run(tmp_path, arm="data_repair")
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    error = np.asarray(completed.diagnostics["error"], dtype=np.dtype("<f8"))
    error[17] = -0.001
    _replace_diagnostic(tmp_path, "error", error)
    with pytest.raises(ValueError, match="error.*non-negative"):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize(
    ("name", "bad"),
    [
        ("error", np.nan),
        ("error", np.inf),
        ("disagreement", np.nan),
        ("predictive_variance", np.inf),
    ],
)
def test_writer_refuses_nonfinite_transition_diagnostics(tmp_path, name, bad):
    completed, _ = _completed_run(tmp_path)
    supplied = dict(completed.diagnostics)
    array = supplied[name].copy()
    array[0] = bad
    supplied[name] = array
    completed = replace(completed, diagnostics=supplied)
    with pytest.raises(ValueError, match=f"{name}.*finite"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)


@pytest.mark.parametrize(
    ("name", "bad"),
    [("error", np.nan), ("disagreement", np.inf)],
)
def test_loader_refuses_resigned_nonfinite_transition_diagnostic(
    tmp_path, name, bad
):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    array = F._canonical_array(name, completed.diagnostics[name])
    array[0] = bad
    _replace_diagnostic(tmp_path, name, array)
    with pytest.raises(ValueError, match=f"{name}.*finite"):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize("name", sorted(F._TRANSITION_DIAGNOSTICS))
def test_writer_refuses_non_vector_transition_shape(tmp_path, name):
    completed, _ = _completed_run(tmp_path)
    supplied = dict(completed.diagnostics)
    supplied[name] = supplied[name].reshape(K.EVALUATION_EPISODES, -1)
    completed = replace(completed, diagnostics=supplied)
    with pytest.raises(ValueError, match="one-dimensional"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)


def test_loader_refuses_resigned_non_vector_transition_shape(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    error = F._canonical_array("error", completed.diagnostics["error"]).reshape(
        K.EVALUATION_EPISODES, -1
    )
    _replace_diagnostic(tmp_path, "error", error)
    with pytest.raises(ValueError, match="one-dimensional"):
        F.load_fit_evidence(tmp_path)


def test_a_second_write_never_changes_existing_evidence(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    with pytest.raises(FileExistsError, match="immutable"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before


@pytest.mark.parametrize(
    "artifact",
    [
        "run_record",
        "metrics",
        "confirmatory",
        "evaluation_action",
        "error",
        "disagreement",
        "scale",
    ],
)
def test_any_persisted_artifact_tamper_is_refused(tmp_path, artifact):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    document = _sidecar(tmp_path)
    path = tmp_path / Path(document["artifacts"][artifact]["path"])
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="digest"):
        F.load_fit_evidence(tmp_path)


@pytest.mark.parametrize("bad_path", ["../error.npy", "/tmp/error.npy", "C:/error.npy"])
def test_traversal_and_absolute_artifact_paths_are_refused_even_if_resigned(
    tmp_path, bad_path
):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    _resign(
        tmp_path,
        lambda document: document["artifacts"]["error"].__setitem__(
            "path", bad_path
        ),
    )
    with pytest.raises(ValueError, match="absolute|travers|canonical"):
        F.load_fit_evidence(tmp_path)


def test_missing_extra_and_invented_role_inventories_are_refused(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    _resign(
        tmp_path,
        lambda document: document["obligations"].append(
            {"stage": "config_sweep", "run_id": "invented"}
        ),
    )
    with pytest.raises(ValueError, match="obligations"):
        F.load_fit_evidence(tmp_path)


def test_verified_projection_refuses_an_invented_role(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    verified = F.load_fit_evidence(tmp_path)
    with pytest.raises(ValueError, match="invented roles"):
        verified.for_role("config_sweep")


def test_legacy_run_without_sidecar_cannot_gain_a_role(tmp_path):
    _completed_run(tmp_path)
    with pytest.raises(ValueError, match="legacy or partial"):
        F.load_fit_evidence(tmp_path)


def test_non_deterministic_physical_stage_is_refused_before_sidecar_write(tmp_path):
    completed, spec = _completed_run(tmp_path, stage="repair_validation")
    assert completed.stage in spec.roles and completed.stage != spec.execution_stage
    with pytest.raises(ValueError, match="deterministically"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert not (tmp_path / F.FIT_EVIDENCE_FILE).exists()
    assert not (tmp_path / "evaluation").exists()


def test_unknown_diagnostic_is_not_silently_dropped(tmp_path):
    completed, _ = _completed_run(tmp_path)
    diagnostics = {**completed.diagnostics, "posthoc_score": np.ones(4)}
    completed = replace(completed, diagnostics=diagnostics)
    with pytest.raises(ValueError, match="unknown=.*posthoc_score"):
        F.write_fit_evidence(completed, fit_dir=tmp_path)
    assert not (tmp_path / "evaluation").exists()


def test_resigned_noncanonical_npy_is_still_refused(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    document = _sidecar(tmp_path)
    path = tmp_path / Path(document["artifacts"]["error"]["path"])
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(completed.evaluation.error, dtype=np.float32))
    path.write_bytes(buffer.getvalue())

    def update(doc):
        doc["artifacts"]["error"]["sha256"] = _digest(path.read_bytes())

    _resign(tmp_path, update)
    with pytest.raises(ValueError, match="not in the canonical"):
        F.load_fit_evidence(tmp_path)


def test_resigned_summary_disagreement_with_arrays_is_refused(tmp_path):
    completed, _ = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    document = _sidecar(tmp_path)
    confirmation_path = tmp_path / Path(
        document["artifacts"]["confirmatory"]["path"]
    )
    confirmation = json.loads(confirmation_path.read_text())
    confirmation["mean_error"] = 999.0
    confirmation_path.write_bytes(_json_bytes(confirmation))

    def update(doc):
        doc["artifacts"]["confirmatory"]["sha256"] = _digest(
            confirmation_path.read_bytes()
        )
        doc["procedure"]["summaries"]["mean_error"] = 999.0

    _resign(tmp_path, update)
    with pytest.raises(ValueError, match="mean_error.*disagrees"):
        F.load_fit_evidence(tmp_path)
