"""Synthetic tests for the persisted Week 6 smoke/label orchestrator.

No environment is sampled and no model is fitted. Most tests use lightweight
boundary doubles; one high-value integration test writes genuine schema-v3 fit
sidecars around fabricated arrays and exercises the production fit loader,
label builder, label loader, and source-reloading Week-6 counts end to end.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.config import Arm, Config, UnitSpec
from bu.env.gridworld import INTERACT
from bu.experiments import repair_label_run as R
from bu.experiments import fit_evidence as F
from bu.experiments.confirmatory import ConfirmatoryRun
from bu.experiments.enumerate_units import repair_validation_units
from bu.experiments.fit_evidence import (
    VerifiedFitEvidence,
    load_fit_evidence,
    registered_fit_spec,
    write_fit_evidence,
)
from bu.experiments.label_evidence import (
    PersistedRepairCondition,
    load_label_evidence,
)
from bu.experiments.repair import ArmEvaluation
from bu.models.uncertainty import NormalisationScale
from bu.models.world_model import MOVEMENT_ACTIONS
from bu.streams import confirmatory_seeds


SEEDS = confirmatory_seeds(K.SEEDS_REPAIR_VALIDATION)


def _model_arms(unit: UnitSpec) -> tuple[str, ...]:
    out = []
    for arm in ("feature_repair", "capacity_repair"):
        try:
            Arm(arm).resolve(unit)
        except ValueError:
            continue
        out.append(arm)
    return tuple(out)


def _eligible_unit() -> UnitSpec:
    unit = R.registered_week6_smoke_unit()
    assert unit in repair_validation_units()
    return unit


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_synthetic_schema_v3_fit(
    unit: UnitSpec,
    *,
    arm: str,
    seed: int,
    out_dir: str | Path,
    scale: NormalisationScale | None = None,
) -> None:
    """Write a real fit sidecar around fabricated, deterministic evidence."""

    root = Path(out_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    spec = registered_fit_spec(unit, arm=arm, seed=seed)
    train = F.CONFIRMATORY_TRAIN if arm == "baseline" else F.REPAIRED_TRAIN
    member_count = train.ensemble_size
    config = Config(
        unit=unit,
        arm=Arm(arm),
        train=train,
        seed=seed,
        stage=spec.execution_stage,
    )
    record_dir = root / spec.execution_run_id
    record_dir.mkdir()
    threading = {"num_threads": 4, "num_interop_threads": 4}
    pool_name = (
        b"synthetic-feature-restored-evaluation-pool"
        if arm == "feature_repair"
        else b"synthetic-fixed-evaluation-pool"
    )
    pool_digest = hashlib.sha256(pool_name).hexdigest()
    role_run_ids = {role: spec.run_id_for(role) for role in spec.roles}
    effective_unit = Config(unit=config.effective_unit).to_dict()["unit"]
    base_unit = config.to_dict()["unit"]
    run_record = {
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        "fit_id": config.fit_id,
        "seed": seed,
        "stage": spec.execution_stage,
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
            "device": "cpu",
            "fit_roles": list(spec.roles),
            "role_run_ids": role_run_ids,
        },
    }
    run_bytes = _json_bytes(run_record)
    metrics_bytes = b'{"i":0,"record_type":"member","member":0}\n'
    (record_dir / "run.json").write_bytes(run_bytes)
    (record_dir / "metrics.jsonl").write_bytes(metrics_bytes)

    full_episode = np.repeat(
        np.arange(K.EVALUATION_EPISODES, dtype=np.int32), K.EPISODE_LENGTH
    )
    full_step = np.tile(
        np.arange(K.EPISODE_LENGTH, dtype=np.int32), K.EVALUATION_EPISODES
    )
    action_pattern = np.asarray(
        [0, INTERACT, 1, 2, INTERACT, 3, 0, INTERACT, 2, 3],
        dtype=np.int32,
    )
    evaluation_action = np.tile(action_pattern, K.EVALUATION_EPISODES)
    movement = np.isin(evaluation_action, np.asarray(MOVEMENT_ACTIONS))
    episode = full_episode[movement]
    step = full_step[movement]
    seed_offset = (seed - SEEDS[0]) * 0.001
    baseline_error = np.full(episode.shape, 1.1, dtype=np.float32)
    if arm == "baseline":
        error = baseline_error
    elif arm == "data_repair":
        error = baseline_error - (0.34 + seed_offset)
    else:
        error = baseline_error + (0.01 + seed_offset)
    disagreement = np.linspace(0.2, 0.8, len(error), dtype=np.float32)
    variance = np.linspace(0.1, 0.4, len(error), dtype=np.float32)
    if scale is None:
        scale = NormalisationScale(
            torch.tensor([1.0, 2.0]), n_reference=len(error)
        )
    diagnostics = {
        "evaluation_action": evaluation_action,
        "episode": episode,
        "step": step,
        "error": error,
        "scale": np.asarray(scale.as_row()["scale"], dtype=np.float64),
        "scale_n_reference": np.asarray(scale.n_reference),
        "scale_domain": np.asarray(scale.domain),
        "scale_source": np.asarray(scale.source),
    }
    if arm == "baseline":
        diagnostics["disagreement"] = disagreement
        diagnostics["predictive_variance"] = variance

    mean_error = float(error.mean())
    mean_disagreement = float(disagreement.mean()) if arm == "baseline" else None
    mean_variance = float(variance.mean()) if arm == "baseline" else None
    confirmation = {
        "config": config.to_dict(),
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        "fit_id": config.fit_id,
        "seed": seed,
        "arm": arm,
        "stage": spec.execution_stage,
        "seed_partition": "confirmatory",
        "granularity": "episode",
        "member_count": member_count,
        "member_indices": list(range(member_count)),
        "member_record_digest": _sha256(metrics_bytes),
        "run_record_digest": _sha256(run_bytes),
        "evaluation_pool_digest": pool_digest,
        "normalisation": scale.as_row(),
        "metric_schema_version": F.METRIC_SCHEMA_VERSION,
        "threading": threading,
        "device": "cpu",
        "fit_roles": list(spec.roles),
        "role_run_ids": role_run_ids,
        "n_train": config.effective_unit.n_transitions,
        "mean_error": mean_error,
        "mean_disagreement": mean_disagreement,
        "mean_predictive_variance": mean_variance,
        "ratio": (
            mean_disagreement / mean_error
            if mean_disagreement is not None
            else None
        ),
    }
    (record_dir / "confirmatory.json").write_bytes(_json_bytes(confirmation))
    evaluation = ArmEvaluation(
        arm=arm,
        seed=seed,
        error=error,
        episode=episode,
        step=step,
        scale=scale,
        config_id=config.config_id,
        run_id=config.run_id,
        n_train=config.effective_unit.n_transitions,
        stage=spec.execution_stage,
        ensemble_size=member_count,
    )
    completed = ConfirmatoryRun(
        run_id=config.run_id,
        config_id=config.config_id,
        unit_id=config.unit_id,
        fit_id=config.fit_id,
        stage=spec.execution_stage,
        arm=arm,
        seed=seed,
        n_train=config.effective_unit.n_transitions,
        member_count=member_count,
        mean_disagreement=(
            mean_disagreement if mean_disagreement is not None else float("nan")
        ),
        record_dir=record_dir,
        run=confirmation,
        evaluation=evaluation,
        diagnostics=diagnostics,
    )
    write_fit_evidence(completed, fit_dir=root)
    load_fit_evidence(root)


class _SyntheticPersistedFits:
    """A test-only persisted-evidence store; it never trains a model."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.entries: dict[Path, VerifiedFitEvidence] = {}
        self.execute_calls: list[tuple[int, str, Path, NormalisationScale | None]] = []
        self.load_calls: list[Path] = []
        self.plan_seen_before_compute: list[bool] = []

    def persist(
        self,
        unit: UnitSpec,
        *,
        arm: str,
        seed: int,
        path: Path,
        scale: NormalisationScale | None = None,
    ) -> VerifiedFitEvidence:
        spec = registered_fit_spec(unit, arm=arm, seed=seed)
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        (path / "fit_evidence.json").write_text("synthetic\n", encoding="utf-8")
        if scale is None:
            scale = NormalisationScale(
                torch.tensor([1.0 + seed / 10000, 2.0], dtype=torch.float32),
                n_reference=K.EVALUATION_EPISODES * K.EPISODE_LENGTH,
            )
        episode = np.repeat(
            np.arange(K.EVALUATION_EPISODES, dtype=np.int64), K.EPISODE_LENGTH
        )
        step = np.tile(
            np.arange(K.EPISODE_LENGTH, dtype=np.int64), K.EVALUATION_EPISODES
        )
        error = np.full(episode.shape, K.FAILURE_THRESHOLD + 0.1, dtype=np.float64)
        evaluation_action = np.tile(
            np.arange(4, dtype=np.int64),
            (K.EVALUATION_EPISODES * K.EPISODE_LENGTH) // 4,
        )
        pool_kind = "feature-restored" if arm == "feature_repair" else "baseline"
        pool_digest = hashlib.sha256(
            f"synthetic-evaluation-pool:{seed}:{pool_kind}".encode("ascii")
        ).hexdigest()
        verified = VerifiedFitEvidence(
            fit_dir=path,
            unit=unit,
            arm=arm,
            seed=seed,
            roles=spec.roles,
            execution_stage=spec.execution_stage,
            unit_id=spec.unit_id,
            config_id=spec.config_id,
            fit_id=spec.fit_id,
            execution_run_id=spec.execution_run_id,
            execution_digest=(f"{seed:04d}{arm}".encode().hex() + "0" * 64)[:64],
            evaluation_pool_digest=pool_digest,
            diagnostics=MappingProxyType(
                {
                    "evaluation_action": evaluation_action,
                    "episode": episode,
                    "step": step,
                    "error": error,
                }
            ),
            error=error,
            episode=episode,
            step=step,
            scale=scale,
            n_train=Arm(arm).resolve(unit).n_transitions,
            ensemble_size=K.DEFAULT_ENSEMBLE_SIZE if arm == "baseline" else 1,
        )
        self.entries[path] = verified
        return verified

    def execute(
        self,
        unit: UnitSpec,
        *,
        arm: str,
        seed: int,
        out_dir: str | Path,
        scale: NormalisationScale | None = None,
    ) -> None:
        path = Path(out_dir).resolve()
        self.plan_seen_before_compute.append(
            (self.root / R.REPAIR_LABEL_PLAN_FILE).is_file()
        )
        self.execute_calls.append((seed, arm, path, scale))
        self.persist(unit, arm=arm, seed=seed, path=path, scale=scale)

    def load(self, path: str | Path) -> VerifiedFitEvidence:
        resolved = Path(path).resolve()
        self.load_calls.append(resolved)
        if not (resolved / "fit_evidence.json").is_file():
            raise ValueError("synthetic fit evidence sidecar is absent")
        try:
            return self.entries[resolved]
        except KeyError as exc:
            raise ValueError("synthetic persisted fit is unverified") from exc


@pytest.fixture
def synthetic_boundaries(tmp_path, monkeypatch):
    root = tmp_path / "week6-smoke"
    store = _SyntheticPersistedFits(root)
    labels: list[tuple[tuple[PersistedRepairCondition, ...], Path]] = []
    counts: list[tuple[tuple[Path, ...], Path]] = []

    def build(conditions, *, path):
        rows = tuple(conditions)
        destination = Path(path)
        destination.write_text('{"synthetic":"exact-label"}\n', encoding="utf-8")
        labels.append((rows, destination))
        return {"synthetic": "exact-label", "condition_count": len(rows)}

    def count(records, *, path):
        rows = tuple(Path(row) for row in records)
        assert all(row.is_file() for row in rows)
        destination = Path(path)
        destination.write_text('{"synthetic":"counts"}\n', encoding="utf-8")
        counts.append((rows, destination))
        return {"synthetic": "counts", "record_count": len(rows)}

    monkeypatch.setattr(R, "run_confirmatory_fit", store.execute)
    monkeypatch.setattr(R, "load_fit_evidence", store.load)
    monkeypatch.setattr(R, "build_label_evidence", build)
    monkeypatch.setattr(R, "write_label_evidence_counts", count)
    return root, store, labels, counts


def test_runs_exact_twenty_by_three_inventory_in_registered_order_and_reuses_scale(
    synthetic_boundaries,
):
    root, store, labels, counts = synthetic_boundaries
    unit = _eligible_unit()
    model_arm = _model_arms(unit)[0]

    result = R._run_synthetic_repair_label(unit, out_dir=root)

    expected_order = [
        (seed, arm)
        for seed in SEEDS
        for arm in ("baseline", "data_repair", model_arm)
    ]
    assert [(seed, arm) for seed, arm, _, _ in store.execute_calls] == expected_order
    assert len(store.execute_calls) == 20 * 3
    assert all(store.plan_seen_before_compute)
    for offset in range(0, len(store.execute_calls), 3):
        baseline, data, model = store.execute_calls[offset : offset + 3]
        assert baseline[3] is None
        persisted_baseline = store.entries[baseline[2]]
        assert data[3] is persisted_baseline.scale
        assert model[3] is persisted_baseline.scale

    plan = json.loads(result.plan_path.read_text(encoding="utf-8"))
    assert plan["repair_label_plan_schema_version"] == 2
    assert plan["unit_id"] == Config(unit=unit).unit_id
    assert plan["stage"] == "repair_validation"
    assert plan["seeds"] == list(SEEDS)
    assert plan["model_repair_arm"] == model_arm
    assert [(row["seed"], row["arm"]) for row in plan["fit_order"]] == expected_order
    assert [row["ordinal"] for row in plan["fit_order"]] == list(range(60))
    assert result.executed_fits == 60
    assert result.resumed_fits == 0

    assert len(labels) == 1
    conditions, label_path = labels[0]
    assert len(conditions) == 20
    assert all(type(row) is PersistedRepairCondition for row in conditions)
    assert label_path == root / "label_evidence.json"
    assert counts == [
        ((root / "label_evidence.json",), root / "label_counts.json")
    ]


def test_schema_v3_orchestrator_reloads_real_synthetic_sidecars_end_to_end(
    tmp_path, monkeypatch
):
    root = tmp_path / "schema-v3-integration"
    monkeypatch.setattr(R, "run_confirmatory_fit", _write_synthetic_schema_v3_fit)

    result = R._run_synthetic_repair_label(_eligible_unit(), out_dir=root)

    assert result.executed_fits == 60
    assert result.resumed_fits == 0
    assert len(list((root / R.FIT_DIRECTORY).glob("*/fit_evidence.json"))) == 60
    loaded = load_label_evidence(result.label_path)
    assert loaded == result.label
    assert loaded["label_evidence_schema_version"] == 3
    assert loaded["label"]["observed_label"] == 0
    source_paths = {
        row[arm]["fit_evidence_path"]
        for row in loaded["runs"]
        for arm in ("baseline", "data_repair", "model_repair")
    }
    assert len(source_paths) == 60
    assert all(not Path(path).is_absolute() and ".." not in Path(path).parts for path in source_paths)
    persisted_counts = json.loads(result.count_path.read_text(encoding="utf-8"))
    assert persisted_counts == result.counts
    assert result.counts["attempted"] == 1
    assert result.counts["observed_0"] == 1
    assert "excluded" not in result.counts
    assert "exclusion_rate" not in result.counts


def test_second_invocation_resumes_only_independently_verified_complete_fits(
    synthetic_boundaries,
):
    root, store, _, _ = synthetic_boundaries
    unit = _eligible_unit()
    first = R._run_synthetic_repair_label(unit, out_dir=root)
    assert first.executed_fits == 60
    store.execute_calls.clear()
    store.load_calls.clear()

    second = R._run_synthetic_repair_label(unit, out_dir=root)

    assert store.execute_calls == []
    assert len(store.load_calls) == 60
    assert second.executed_fits == 0
    assert second.resumed_fits == 60
    assert second.plan_path.read_bytes() == first.plan_path.read_bytes()


def test_existing_partial_fit_directory_is_refused_before_any_fit(
    synthetic_boundaries,
):
    root, store, labels, _ = synthetic_boundaries
    unit = _eligible_unit()
    spec = registered_fit_spec(unit, arm="baseline", seed=SEEDS[0])
    partial = root / R.FIT_DIRECTORY / spec.fit_id
    partial.mkdir(parents=True)
    (partial / "run.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="partial or invalid"):
        R._run_synthetic_repair_label(unit, out_dir=root)

    assert (root / R.REPAIR_LABEL_PLAN_FILE).is_file()
    assert store.execute_calls == []
    assert labels == []


def test_existing_divergent_verified_fit_is_refused_without_retraining(
    synthetic_boundaries,
):
    root, store, labels, _ = synthetic_boundaries
    unit = _eligible_unit()
    spec = registered_fit_spec(unit, arm="baseline", seed=SEEDS[0])
    path = root / R.FIT_DIRECTORY / spec.fit_id
    verified = store.persist(unit, arm="baseline", seed=SEEDS[0], path=path)
    store.entries[path.resolve()] = VerifiedFitEvidence(
        **{**verified.__dict__, "seed": SEEDS[1]}
    )

    with pytest.raises(ValueError, match="diverges from its immutable plan"):
        R._run_synthetic_repair_label(unit, out_dir=root)

    assert store.execute_calls == []
    assert labels == []


def test_divergent_immutable_plan_is_refused_before_resume_or_retraining(
    synthetic_boundaries,
):
    root, store, labels, _ = synthetic_boundaries
    unit = _eligible_unit()
    first = R._run_synthetic_repair_label(unit, out_dir=root)
    document = json.loads(first.plan_path.read_text(encoding="utf-8"))
    document["stage"] = "exp1"
    first.plan_path.write_text(json.dumps(document), encoding="utf-8")
    store.execute_calls.clear()
    store.load_calls.clear()
    labels.clear()

    with pytest.raises(ValueError, match="differs from the exact registered plan"):
        R._run_synthetic_repair_label(unit, out_dir=root)

    assert store.execute_calls == []
    assert store.load_calls == []
    assert labels == []


def test_existing_fit_path_that_is_not_a_directory_is_refused(
    synthetic_boundaries,
):
    root, store, labels, _ = synthetic_boundaries
    unit = _eligible_unit()
    spec = registered_fit_spec(unit, arm="baseline", seed=SEEDS[0])
    destination = root / R.FIT_DIRECTORY / spec.fit_id
    destination.parent.mkdir(parents=True)
    destination.write_text("not a fit directory\n", encoding="utf-8")

    with pytest.raises(ValueError, match="exists but is not a directory"):
        R._run_synthetic_repair_label(unit, out_dir=root)

    assert store.execute_calls == []
    assert labels == []


def test_existing_fit_symlink_is_refused_where_supported(
    synthetic_boundaries,
):
    root, store, labels, _ = synthetic_boundaries
    unit = _eligible_unit()
    spec = registered_fit_spec(unit, arm="baseline", seed=SEEDS[0])
    destination = root / R.FIT_DIRECTORY / spec.fit_id
    destination.parent.mkdir(parents=True)
    target = root / "symlink-target"
    target.mkdir()
    try:
        destination.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"OS does not permit unprivileged symlink creation: {exc}")

    with pytest.raises(ValueError, match="is a symlink; refusing resume"):
        R._run_synthetic_repair_label(unit, out_dir=root)

    assert destination.is_symlink()
    assert store.execute_calls == []
    assert labels == []


def test_new_fit_without_verifiable_sidecar_is_refused(
    synthetic_boundaries, monkeypatch
):
    root, store, labels, _ = synthetic_boundaries

    def incomplete_fit(unit, *, arm, seed, out_dir, scale=None):
        del unit, arm, seed, scale
        path = Path(out_dir)
        path.mkdir(parents=True)
        (path / "worker-stopped.txt").write_text("partial\n", encoding="utf-8")

    monkeypatch.setattr(R, "run_confirmatory_fit", incomplete_fit)
    with pytest.raises(ValueError, match="did not publish complete verifiable"):
        R._run_synthetic_repair_label(_eligible_unit(), out_dir=root)

    assert store.load_calls
    assert store.execute_calls == []
    assert labels == []


def test_repaired_fit_with_wrong_baseline_scale_is_refused(
    synthetic_boundaries, monkeypatch
):
    root, store, labels, _ = synthetic_boundaries

    def wrong_scale_fit(unit, *, arm, seed, out_dir, scale=None):
        if arm != "baseline":
            assert scale is not None
            scale = NormalisationScale(
                scale.vector * 2,
                n_reference=scale.n_reference,
                domain=scale.domain,
                source=scale.source,
            )
        store.execute(
            unit,
            arm=arm,
            seed=seed,
            out_dir=out_dir,
            scale=scale,
        )

    monkeypatch.setattr(R, "run_confirmatory_fit", wrong_scale_fit)
    with pytest.raises(ValueError, match="exact normalisation scale"):
        R._run_synthetic_repair_label(_eligible_unit(), out_dir=root)

    assert [arm for _, arm, _, _ in store.execute_calls] == [
        "baseline",
        "data_repair",
    ]
    assert labels == []


@pytest.mark.parametrize(
    "unit",
    [
        UnitSpec(family="estimation", n_transitions=max(K.DATA_SIZES)),
        UnitSpec(
            family="missing_feature",
            withheld_features=("shape",),
            hidden_size=min(K.HIDDEN_SIZES),
            n_transitions=max(K.DATA_SIZES),
            confound_rate=K.CONFOUND_LEVELS_2A[0],
        ),
    ],
    ids=["no-model-repair", "two-model-repairs"],
)
def test_refuses_units_without_exactly_one_model_repair_before_manifest_or_fit(
    synthetic_boundaries, unit
):
    root, store, labels, _ = synthetic_boundaries

    with pytest.raises(ValueError, match="exactly one registered model-class repair"):
        R._run_synthetic_repair_label(unit, out_dir=root)

    assert not (root / R.REPAIR_LABEL_PLAN_FILE).exists()
    assert store.execute_calls == []
    assert labels == []
