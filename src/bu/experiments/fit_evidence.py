"""Immutable evidence for one physical fit carrying one or more obligations.

``run_id`` identifies an obligation, while ``fit_id`` identifies the computation
(D-033).  The execution plan can therefore assign several registered stages to
one fit.  This module records that fact without copying metrics, inventing an
alias run directory, or training again: one completed :class:`ConfirmatoryRun`
is wrapped by one versioned sidecar whose role projections all cite the same
bytes and execution digest.

The registry remains authoritative.  Roles are always re-derived from
``execution_plan(design_units())`` using the absolute confirmatory seed; neither
the writer nor the loader accepts a caller-provided role list.  The sidecar is
written last, so its presence means every named artifact was already fsynced and
published exclusively.  A directory without the sidecar is legacy or partial
evidence and cannot be projected into another role.
"""

from __future__ import annotations

import dataclasses
import errno
import hashlib
import io
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import torch

from .. import constants as K
from ..config import (
    IDENTITY_VERSION,
    SCHEMA_VERSION,
    UNIT_IDENTITY_FIELDS,
    Arm,
    Config,
    UnitSpec,
)
from ..env.gridworld import N_ACTIONS
from ..metrics import METRICS_FILE
from ..models.uncertainty import RATIO_FLOOR, NormalisationScale
from ..models.world_model import MOVEMENT_ACTIONS
from ..runrecord import TRACKED_PACKAGES, GitState, git_state
from ..stats.gate import METRIC_SCHEMA_VERSION
from ..streams import (
    PURPOSES,
    STREAM_VERSION,
    assert_roles_share_one_stream,
    is_confirmatory,
    stream_key,
)
from .confirmatory import (
    CONFIRMATORY_DEVICE,
    CONFIRMATORY_GRANULARITY,
    CONFIRMATORY_INTEROP_THREADS,
    CONFIRMATORY_THREADS,
    CONFIRMATORY_TRAIN,
    REPAIRED_TRAIN,
    ConfirmatoryRun,
    assert_registered_obligation,
    run_confirmatory,
)
from .enumerate_units import design_units, execution_plan
from .repair import ArmEvaluation


#: v2 is the first procedure-authoritative fit-evidence contract.  Version 1
#: cross-checked documents only against one another, so a consistently resigned
#: bundle could attest an unregistered optimiser, thread count, device, metric
#: schema, or incomplete/untrustworthy run provenance.  No v1 sidecar is
#: grandfathered into this new scientific boundary.
FIT_EVIDENCE_SCHEMA_VERSION = 2
FIT_EVIDENCE_FILE = "fit_evidence.json"
EVALUATION_DIRECTORY = "evaluation"

# Exact runtime pins are part of the v2 procedure contract.  Keep this registry
# in the evidence reader rather than trusting a run record to attest its own
# environment.  Changing a pin requires a fit-evidence schema change.
_FROZEN_PACKAGE_VERSIONS = {
    "torch": "2.13.0",
    "gymnasium": "1.3.0",
    "numpy": "2.4.1",
    "scipy": "1.17.0",
    "statsmodels": "0.14.6",
    "pandas": "2.3.3",
    "matplotlib": "3.11.1",
    "PyYAML": "6.0.1",
}
if tuple(_FROZEN_PACKAGE_VERSIONS) != TRACKED_PACKAGES:
    raise RuntimeError(
        "fit-evidence package pins do not exactly follow runrecord.TRACKED_PACKAGES"
    )

_RUN_RECORD_KEYS = {
    "run_id", "config_id", "unit_id", "fit_id", "seed", "stage",
    "seed_partition", "confirmatory", "schema_version", "identity_version",
    "unit_identity_fields", "started_utc", "config", "effective_unit",
    "arm_changed", "git", "env", "extra",
}
_RUN_EXTRA_KEYS = {
    "granularity", "seed_partition", "evaluation_pool_digest", "threading",
    "device", "fit_roles", "role_run_ids",
}
_GIT_KEYS = {"commit", "branch", "dirty", "trustworthy"}
_ENV_KEYS = {"python", "platform", "packages"}

_CORE_DIAGNOSTICS = ("episode", "step", "error")
_TRANSITION_DIAGNOSTICS = frozenset(
    {"episode", "step", "error", "disagreement", "predictive_variance"}
)
_FULL_EVALUATION_DIAGNOSTICS = frozenset({"evaluation_action"})
_SCALE_DIAGNOSTICS = frozenset(
    {"scale", "scale_n_reference", "scale_domain", "scale_source"}
)
_KNOWN_DIAGNOSTICS = (
    _TRANSITION_DIAGNOSTICS
    | _FULL_EVALUATION_DIAGNOSTICS
    | _SCALE_DIAGNOSTICS
)
_BASELINE_DIAGNOSTICS = tuple(sorted(_KNOWN_DIAGNOSTICS))
_REPAIR_DIAGNOSTICS = tuple(
    sorted(
        set(_CORE_DIAGNOSTICS)
        | _FULL_EVALUATION_DIAGNOSTICS
        | _SCALE_DIAGNOSTICS
    )
)
_FULL_EVALUATION_TRANSITIONS = K.EVALUATION_EPISODES * K.EPISODE_LENGTH
_SUMMARY_NAMES = (
    "mean_error",
    "mean_disagreement",
    "mean_predictive_variance",
    "ratio",
)
_SOURCE_NAMES = {
    "run_record": "run.json",
    "metrics": METRICS_FILE,
    "confirmatory": "confirmatory.json",
}
_TOP_LEVEL_KEYS = {
    "fit_evidence_schema_version",
    "identities",
    "obligations",
    "artifacts",
    "procedure",
    "execution_digest",
}
_IDENTITY_KEYS = {
    "fit_id",
    "unit_id",
    "config_id",
    "seed",
    "arm",
    "execution_stage",
    "execution_run_id",
}
_PROCEDURE_KEYS = {
    "granularity",
    "seed_partition",
    "stream_version",
    "role_stream_fingerprints",
    "train",
    "threading",
    "device",
    "evaluation_pool_digest",
    "normalisation",
    "n_train",
    "member_count",
    "metric_schema_version",
    "diagnostic_names",
    "summaries",
}


@dataclass(frozen=True)
class RegisteredFitSpec:
    """The exact registered interpretation of one absolute-seed computation."""

    unit: UnitSpec
    arm: str
    seed: int
    roles: tuple[str, ...]
    execution_stage: str
    unit_id: str
    config_id: str
    fit_id: str
    execution_run_id: str

    def run_id_for(self, stage: str) -> str:
        if stage not in self.roles:
            raise ValueError(
                f"stage {stage!r} is not a registered role of fit {self.fit_id}; "
                f"expected one of {self.roles}"
            )
        return Config(
            unit=self.unit,
            arm=Arm(self.arm),
            seed=self.seed,
            stage=stage,
        ).run_id


@dataclass(frozen=True)
class VerifiedFitEvidence:
    """A fully revalidated sidecar and its read-only evaluation arrays."""

    fit_dir: Path
    unit: UnitSpec
    arm: str
    seed: int
    roles: tuple[str, ...]
    execution_stage: str
    unit_id: str
    config_id: str
    fit_id: str
    execution_run_id: str
    execution_digest: str
    evaluation_pool_digest: str
    diagnostics: Mapping[str, np.ndarray]
    error: np.ndarray
    episode: np.ndarray
    step: np.ndarray
    scale: NormalisationScale
    n_train: int
    ensemble_size: int

    def for_role(self, stage: str) -> ArmEvaluation:
        """Project the verified bytes into one pre-registered obligation.

        No free-form ``run_id`` is accepted.  It is reconstructed from the
        verified unit, arm, absolute seed and requested registered stage.
        """
        if type(stage) is not str or stage not in self.roles:
            raise ValueError(
                f"stage {stage!r} is not a verified role of fit {self.fit_id}; "
                f"expected one of {self.roles}. Legacy and invented roles cannot "
                "be projected"
            )
        run_id = Config(
            unit=self.unit,
            arm=Arm(self.arm),
            seed=self.seed,
            stage=stage,
        ).run_id
        assert_registered_obligation(
            self.unit, arm=self.arm, stage=stage, seed=self.seed
        )
        return ArmEvaluation(
            arm=self.arm,
            seed=self.seed,
            error=self.error,
            episode=self.episode,
            step=self.step,
            scale=self.scale,
            config_id=self.config_id,
            run_id=run_id,
            n_train=self.n_train,
            stage=stage,
            ensemble_size=self.ensemble_size,
        )


@dataclass(frozen=True)
class CompletedFitEvidence:
    """One physical confirmatory run and its verified role-aware sidecar."""

    physical: ConfirmatoryRun
    verified: VerifiedFitEvidence
    evidence_path: Path

    def as_row(self) -> dict[str, Any]:
        row = self.physical.as_row()
        row["fit_roles"] = list(self.verified.roles)
        row["role_run_ids"] = {
            role: Config(
                unit=self.verified.unit,
                arm=Arm(self.verified.arm),
                seed=self.verified.seed,
                stage=role,
            ).run_id
            for role in self.verified.roles
        }
        row["fit_evidence_schema_version"] = FIT_EVIDENCE_SCHEMA_VERSION
        row["fit_evidence_digest"] = self.verified.execution_digest
        row["fit_evidence_file"] = FIT_EVIDENCE_FILE
        return row


def registered_fit_spec(
    unit: UnitSpec, *, arm: str, seed: int
) -> RegisteredFitSpec:
    """Derive the exact role inventory for an absolute confirmatory seed."""
    if type(unit) is not UnitSpec:
        raise ValueError(f"unit must be an exact UnitSpec, got {type(unit).__name__}")
    if type(seed) is not int or seed < 0:
        raise ValueError(f"seed must be an exact non-negative integer, got {seed!r}")
    if not is_confirmatory(seed):
        raise ValueError(
            f"seed {seed} is development data; fit evidence may wrap only an "
            "absolute confirmatory seed"
        )
    arm_obj = Arm(arm)
    arm_obj.resolve(unit)
    unit_id = Config(unit=unit).unit_id
    seed_index = seed - K.CONFIRMATORY_SEED_BASE
    matches = [
        fit
        for fit in execution_plan(design_units())
        if Config(unit=fit.unit).unit_id == unit_id
        and fit.arm == arm
        and fit.seed == seed_index
    ]
    if len(matches) != 1:
        raise ValueError(
            f"fit ({unit_id}, arm={arm!r}, seed={seed}) has {len(matches)} "
            "registered execution-plan entries; expected exactly one"
        )
    fit = matches[0]
    roles = tuple(sorted(fit.roles))
    if not roles or roles != fit.roles or len(roles) != len(set(roles)):
        raise ValueError(
            f"registered fit roles are not a unique sorted non-empty inventory: "
            f"{fit.roles!r}"
        )
    assert_roles_share_one_stream(unit, roles)
    for role in roles:
        assert_registered_obligation(unit, arm=arm, stage=role, seed=seed)
    execution_stage = roles[0]
    config = Config(unit=unit, arm=arm_obj, seed=seed, stage=execution_stage)
    return RegisteredFitSpec(
        unit=unit,
        arm=arm,
        seed=seed,
        roles=roles,
        execution_stage=execution_stage,
        unit_id=config.unit_id,
        config_id=config.config_id,
        fit_id=config.fit_id,
        execution_run_id=config.run_id,
    )


def _validate_expected_git_commit(value: object) -> str:
    """Return one exact launch-bound Git commit or fail closed."""

    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError(
            "expected_git_commit must be an exact lowercase 40-hex commit, "
            f"got {value!r}"
        )
    return value


def _require_current_git_commit(expected_git_commit: object) -> str:
    """Bind a fit to the preflight commit before any scientific work starts."""

    expected = _validate_expected_git_commit(expected_git_commit)
    state = git_state()
    if type(state) is not GitState:
        raise ValueError(
            f"git_state returned {type(state).__name__}, not an exact GitState"
        )
    if not state.trustworthy or state.commit != expected:
        raise ValueError(
            "current clean trustworthy Git commit does not equal the "
            f"launch-bound preflight commit: current={state.commit!r}, "
            f"dirty={state.dirty!r}, expected={expected!r}"
        )
    return expected


def run_confirmatory_fit(
    unit: UnitSpec,
    *,
    arm: str,
    seed: int,
    out_dir: str | Path,
    scale: NormalisationScale | None = None,
    expected_git_commit: str | None = None,
) -> CompletedFitEvidence:
    """Execute one registered fit once and seal every obligation it carries.

    The role inventory and execution stage are derived, never caller supplied.
    They are written into ``run.json`` before training and rederived by the
    sidecar loader after every artifact has landed.
    """
    if expected_git_commit is not None:
        _require_current_git_commit(expected_git_commit)
    spec = registered_fit_spec(unit, arm=arm, seed=seed)
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    completed = run_confirmatory(
        unit,
        stage=spec.execution_stage,
        seed=seed,
        arm=arm,
        out_dir=root,
        scale=scale,
        _fit_roles=spec.roles,
    )
    evidence_path = write_fit_evidence(completed, fit_dir=root)
    verified = load_fit_evidence(
        root, expected_git_commit=expected_git_commit
    )
    return CompletedFitEvidence(
        physical=completed,
        verified=verified,
        evidence_path=evidence_path,
    )


def write_fit_evidence(
    completed: ConfirmatoryRun, *, fit_dir: str | Path | None = None
) -> Path:
    """Persist one immutable sidecar around an already-completed physical run.

    The completed run must already use the deterministic execution stage.  This
    function never creates a role-specific run directory or another metrics
    stream; role-specific ``run_id`` values exist only as projections in the
    sidecar.
    """
    if type(completed) is not ConfirmatoryRun:
        raise ValueError(
            f"completed must be an exact ConfirmatoryRun, got "
            f"{type(completed).__name__}"
        )
    root = Path(fit_dir) if fit_dir is not None else Path(completed.record_dir).parent
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"fit directory does not exist or is not a directory: {root}")

    bundle = _validate_completed_run(completed, root)
    spec = bundle["spec"]
    arrays = _validated_diagnostics(completed)
    paths = _canonical_artifact_paths(spec.execution_run_id, tuple(arrays))
    _assert_one_physical_run(root, paths)

    final_paths = {
        name: _safe_artifact_path(root, rel, expected=rel, must_exist=False)
        for name, rel in _diagnostic_paths(tuple(arrays)).items()
    }
    sidecar_path = root / FIT_EVIDENCE_FILE
    if sidecar_path.exists() or any(path.exists() for path in final_paths.values()):
        raise FileExistsError(
            f"fit evidence already or partially exists under {root}; immutable "
            "evidence is never overwritten or completed in place"
        )
    array_bytes = {name: _npy_bytes(array) for name, array in arrays.items()}
    artifact_bytes = {
        **bundle["artifact_bytes"],
        **array_bytes,
    }
    artifacts = {
        name: {"path": paths[name], "sha256": _sha256(data)}
        for name, data in artifact_bytes.items()
    }
    procedure = _procedure_from_documents(
        bundle["config"],
        bundle["run_record"],
        bundle["confirmatory"],
        spec,
        tuple(arrays),
    )
    payload = {
        "fit_evidence_schema_version": FIT_EVIDENCE_SCHEMA_VERSION,
        "identities": _identities(spec),
        "obligations": _obligations(spec),
        "artifacts": artifacts,
        "procedure": procedure,
    }
    document = {**payload, "execution_digest": _execution_digest(payload)}

    # No final evidence path is created until every identity, relationship,
    # summary and byte digest has been validated and the complete sidecar exists
    # in memory.  The sidecar itself is still published last.
    evaluation_dir = root / EVALUATION_DIRECTORY
    try:
        evaluation_dir.mkdir()
    except FileExistsError as exc:
        raise FileExistsError(
            f"{evaluation_dir} already exists; refusing to merge with partial or "
            "legacy evidence"
        ) from exc
    _fsync_directory(root)
    for name in arrays:
        _write_bytes_exclusive_atomic(final_paths[name], array_bytes[name])
    _write_bytes_exclusive_atomic(sidecar_path, _canonical_json_bytes(document))
    return sidecar_path


def load_fit_evidence(
    fit_dir: str | Path,
    *,
    expected_git_commit: str | None = None,
) -> VerifiedFitEvidence:
    """Load and independently verify a fit-evidence sidecar.

    A completed legacy run without ``fit_evidence.json`` remains valid only for
    its physical stage; it cannot be promoted through this role-aware loader.
    """
    if expected_git_commit is not None:
        _validate_expected_git_commit(expected_git_commit)
    root = Path(fit_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"fit directory does not exist or is not a directory: {root}")
    sidecar_path = root / FIT_EVIDENCE_FILE
    if not sidecar_path.is_file():
        raise ValueError(
            f"{root} has no {FIT_EVIDENCE_FILE}; legacy or partial evidence cannot "
            "be projected into another experimental role"
        )
    if sidecar_path.is_symlink():
        raise ValueError(f"{sidecar_path} is a symlink; evidence must be a regular file")
    raw_sidecar = sidecar_path.read_bytes()
    document = _load_json_bytes(raw_sidecar, what=FIT_EVIDENCE_FILE)
    _require_exact_keys(document, _TOP_LEVEL_KEYS, what=FIT_EVIDENCE_FILE)
    if document["fit_evidence_schema_version"] != FIT_EVIDENCE_SCHEMA_VERSION:
        raise ValueError(
            f"fit-evidence schema {document['fit_evidence_schema_version']!r} != "
            f"{FIT_EVIDENCE_SCHEMA_VERSION}"
        )
    if raw_sidecar != _canonical_json_bytes(document):
        raise ValueError(f"{FIT_EVIDENCE_FILE} is not canonical JSON bytes")
    payload = {key: value for key, value in document.items() if key != "execution_digest"}
    expected_execution_digest = _execution_digest(payload)
    _require_digest(document["execution_digest"], what="execution_digest")
    if document["execution_digest"] != expected_execution_digest:
        raise ValueError("fit-evidence execution digest does not match its payload")

    identities = _require_mapping(document["identities"], what="identities")
    _require_exact_keys(identities, _IDENTITY_KEYS, what="identities")
    execution_run_id = _require_text(
        identities["execution_run_id"], what="identities.execution_run_id"
    )
    artifacts_doc = _require_mapping(document["artifacts"], what="artifacts")
    diagnostic_names = _diagnostic_inventory_from_artifacts(artifacts_doc)
    paths = _canonical_artifact_paths(execution_run_id, diagnostic_names)
    if set(artifacts_doc) != set(paths):
        raise ValueError(
            f"artifact inventory is {sorted(artifacts_doc)}, expected {sorted(paths)}"
        )

    artifact_bytes: dict[str, bytes] = {}
    for name, expected_path in paths.items():
        entry = _require_mapping(artifacts_doc[name], what=f"artifacts.{name}")
        _require_exact_keys(entry, {"path", "sha256"}, what=f"artifacts.{name}")
        path = _safe_artifact_path(
            root, entry["path"], expected=expected_path, must_exist=True
        )
        expected_digest = _require_digest(
            entry["sha256"], what=f"artifacts.{name}.sha256"
        )
        data = path.read_bytes()
        if _sha256(data) != expected_digest:
            raise ValueError(f"artifact {name!r} bytes do not match the recorded digest")
        artifact_bytes[name] = data

    run_record = _load_json_bytes(artifact_bytes["run_record"], what="run.json")
    confirmatory = _load_json_bytes(
        artifact_bytes["confirmatory"], what="confirmatory.json"
    )
    _validate_metrics(artifact_bytes["metrics"])
    config = _config_from_run_record(run_record)
    spec = registered_fit_spec(
        config.unit, arm=config.arm.kind, seed=config.seed
    )
    if _identities(spec) != dict(identities):
        raise ValueError("sidecar identities do not equal the re-derived registered fit")
    obligations = document["obligations"]
    if obligations != _obligations(spec):
        raise ValueError(
            "sidecar obligations do not exactly equal the registered sorted role "
            "inventory; missing, extra, duplicated and invented roles are refused"
        )
    if config.stage != spec.execution_stage:
        raise ValueError(
            f"physical run stage {config.stage!r} is not deterministic execution "
            f"stage {spec.execution_stage!r}"
        )
    _validate_documents(
        config,
        run_record,
        confirmatory,
        spec,
        artifact_bytes["run_record"],
        artifact_bytes["metrics"],
    )
    if (
        expected_git_commit is not None
        and run_record["git"]["commit"] != expected_git_commit
    ):
        raise ValueError(
            "fit evidence Git commit does not equal the launch-bound "
            f"preflight commit: recorded={run_record['git']['commit']!r}, "
            f"expected={expected_git_commit!r}"
        )
    procedure = _require_mapping(document["procedure"], what="procedure")
    expected_procedure = _procedure_from_documents(
        config, run_record, confirmatory, spec, diagnostic_names
    )
    if dict(procedure) != expected_procedure:
        raise ValueError(
            "sidecar procedure does not match the physical run and registered streams"
        )

    arrays = {
        name: _load_canonical_npy(artifact_bytes[name], name=name)
        for name in diagnostic_names
    }
    _validate_diagnostic_relationships(
        arrays, expected_procedure, arm=spec.arm
    )
    for array in arrays.values():
        array.flags.writeable = False
    _assert_one_physical_run(root, paths)
    scale = _scale_from_row(expected_procedure["normalisation"])
    return VerifiedFitEvidence(
        fit_dir=root,
        unit=config.unit,
        arm=spec.arm,
        seed=spec.seed,
        roles=spec.roles,
        execution_stage=spec.execution_stage,
        unit_id=spec.unit_id,
        config_id=spec.config_id,
        fit_id=spec.fit_id,
        execution_run_id=spec.execution_run_id,
        execution_digest=document["execution_digest"],
        evaluation_pool_digest=expected_procedure["evaluation_pool_digest"],
        diagnostics=MappingProxyType(dict(arrays)),
        error=arrays["error"],
        episode=arrays["episode"],
        step=arrays["step"],
        scale=scale,
        n_train=expected_procedure["n_train"],
        ensemble_size=expected_procedure["member_count"],
    )


def _validate_completed_run(completed: ConfirmatoryRun, root: Path) -> dict[str, Any]:
    if completed.evaluation is None:
        raise ValueError("completed ConfirmatoryRun has no per-transition evaluation")
    record_dir = Path(completed.record_dir).resolve()
    if record_dir.parent != root:
        raise ValueError(
            f"physical run directory {record_dir} is not a direct child of fit "
            f"directory {root}"
        )
    run_path = record_dir / "run.json"
    metrics_path = record_dir / METRICS_FILE
    confirmatory_path = record_dir / "confirmatory.json"
    for path in (run_path, metrics_path, confirmatory_path):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"completed physical artifact is absent or not regular: {path}")
    artifact_bytes = {
        "run_record": run_path.read_bytes(),
        "metrics": metrics_path.read_bytes(),
        "confirmatory": confirmatory_path.read_bytes(),
    }
    run_record = _load_json_bytes(artifact_bytes["run_record"], what="run.json")
    confirmatory = _load_json_bytes(
        artifact_bytes["confirmatory"], what="confirmatory.json"
    )
    _validate_metrics(artifact_bytes["metrics"])
    config = _config_from_run_record(run_record)
    spec = registered_fit_spec(config.unit, arm=config.arm.kind, seed=config.seed)
    if config.stage != spec.execution_stage:
        raise ValueError(
            f"already-completed run used stage {config.stage!r}; the registered "
            f"execution stage is deterministically {spec.execution_stage!r}"
        )
    if record_dir.name != spec.execution_run_id:
        raise ValueError(
            f"physical run directory {record_dir.name!r} != canonical execution "
            f"run_id {spec.execution_run_id!r}"
        )
    expected_completed = {
        "run_id": spec.execution_run_id,
        "config_id": spec.config_id,
        "unit_id": spec.unit_id,
        "fit_id": spec.fit_id,
        "stage": spec.execution_stage,
        "arm": spec.arm,
        "seed": spec.seed,
    }
    for field, expected in expected_completed.items():
        if getattr(completed, field) != expected:
            raise ValueError(
                f"ConfirmatoryRun.{field}={getattr(completed, field)!r} != {expected!r}"
            )
    if completed.run != confirmatory:
        raise ValueError(
            "ConfirmatoryRun.run does not equal the persisted confirmatory.json"
        )
    _validate_documents(
        config,
        run_record,
        confirmatory,
        spec,
        artifact_bytes["run_record"],
        artifact_bytes["metrics"],
    )
    evaluation = completed.evaluation
    for field, expected in (
        ("arm", spec.arm),
        ("seed", spec.seed),
        ("config_id", spec.config_id),
        ("run_id", spec.execution_run_id),
        ("stage", spec.execution_stage),
        ("n_train", completed.n_train),
        ("ensemble_size", completed.member_count),
    ):
        if getattr(evaluation, field) != expected:
            raise ValueError(
                f"completed evaluation {field}={getattr(evaluation, field)!r} "
                f"!= {expected!r}"
            )
    if completed.n_train != confirmatory.get("n_train"):
        raise ValueError("ConfirmatoryRun.n_train disagrees with confirmatory.json")
    if completed.member_count != confirmatory.get("member_count"):
        raise ValueError("ConfirmatoryRun.member_count disagrees with confirmatory.json")
    if evaluation.scale.as_row() != confirmatory.get("normalisation"):
        raise ValueError("evaluation scale disagrees with confirmatory.json")
    return {
        "spec": spec,
        "config": config,
        "run_record": run_record,
        "confirmatory": confirmatory,
        "artifact_bytes": artifact_bytes,
    }


def _validate_documents(
    config: Config,
    run_record: Mapping[str, Any],
    confirmatory: Mapping[str, Any],
    spec: RegisteredFitSpec,
    run_bytes: bytes,
    metrics_bytes: bytes,
) -> None:
    expected = {
        "run_id": spec.execution_run_id,
        "config_id": spec.config_id,
        "unit_id": spec.unit_id,
        "fit_id": spec.fit_id,
        "seed": spec.seed,
        "stage": spec.execution_stage,
    }
    for field, value in expected.items():
        if not _same_json_value(run_record.get(field), value):
            raise ValueError(f"run.json {field} does not match registered fit")
        if not _same_json_value(confirmatory.get(field), value):
            raise ValueError(f"confirmatory.json {field} does not match registered fit")
    if confirmatory.get("arm") != spec.arm:
        raise ValueError("confirmatory.json arm does not match registered fit")
    confirm_config = confirmatory.get("config")
    canonical_config = config.to_dict()
    if not _same_json_value(run_record.get("config"), canonical_config):
        raise ValueError("run.json config is not the exact canonical configuration")
    if not _same_json_value(confirm_config, canonical_config):
        raise ValueError("confirmatory.json config does not equal run.json config")
    _validate_registered_procedure(config, run_record, confirmatory, spec)
    _validate_run_record_provenance(config, run_record)
    if run_record.get("seed_partition") != "confirmatory":
        raise ValueError("run.json is not marked as confirmatory evidence")
    if run_record.get("confirmatory") is not True:
        raise ValueError("run.json confirmatory flag is not exactly true")
    if confirmatory.get("seed_partition") != "confirmatory":
        raise ValueError("confirmatory.json is not marked as confirmatory evidence")
    if confirmatory.get("granularity") != CONFIRMATORY_GRANULARITY:
        raise ValueError("confirmatory.json does not attest episode granularity")
    extra = _require_mapping(run_record.get("extra"), what="run.json.extra")
    for field in (
        "granularity", "seed_partition", "evaluation_pool_digest",
        "threading", "device", "fit_roles", "role_run_ids",
    ):
        if extra.get(field) != confirmatory.get(field):
            raise ValueError(f"run.json.extra.{field} disagrees with confirmatory.json")
    expected_roles = list(spec.roles)
    expected_role_ids = {
        role: spec.run_id_for(role) for role in spec.roles
    }
    if extra.get("fit_roles") != expected_roles:
        raise ValueError("pre-fit run record does not carry the exact registered roles")
    if extra.get("role_run_ids") != expected_role_ids:
        raise ValueError("pre-fit run record has inconsistent role run identities")
    if confirmatory.get("run_record_digest") != _sha256(run_bytes):
        raise ValueError("confirmatory.json run_record_digest does not match run.json")
    if confirmatory.get("member_record_digest") != _sha256(metrics_bytes):
        raise ValueError("confirmatory.json member_record_digest does not match metrics")
    _require_digest(
        confirmatory.get("evaluation_pool_digest"),
        what="confirmatory.json evaluation_pool_digest",
    )
    _normalisation_row(confirmatory.get("normalisation"))
    _require_nonnegative_int(confirmatory.get("n_train"), what="n_train", positive=True)
    member_count = _require_nonnegative_int(
        confirmatory.get("member_count"), what="member_count", positive=True
    )
    indices = confirmatory.get("member_indices")
    if indices != list(range(member_count)):
        raise ValueError("confirmatory.json member_indices are not complete and canonical")


def _validate_registered_procedure(
    config: Config,
    run_record: Mapping[str, Any],
    confirmatory: Mapping[str, Any],
    spec: RegisteredFitSpec,
) -> None:
    """Require the physical artifacts to name the frozen procedure exactly."""

    expected_train = CONFIRMATORY_TRAIN if spec.arm == "baseline" else REPAIRED_TRAIN
    expected_train_row = dataclasses.asdict(expected_train)
    observed_train = config.to_dict()["train"]
    if not _same_json_value(observed_train, expected_train_row):
        raise ValueError(
            f"{spec.arm} fit uses training {observed_train!r}, not the frozen "
            f"{expected_train_row!r}"
        )

    expected_threading = {
        "num_threads": CONFIRMATORY_THREADS,
        "num_interop_threads": CONFIRMATORY_INTEROP_THREADS,
    }
    extra = _require_mapping(run_record.get("extra"), what="run.json.extra")
    for location, observed in (
        ("run.json.extra.threading", extra.get("threading")),
        ("confirmatory.json threading", confirmatory.get("threading")),
    ):
        if not _same_json_value(observed, expected_threading):
            raise ValueError(
                f"{location} is {observed!r}, not frozen threading "
                f"{expected_threading!r}"
            )
    for location, observed in (
        ("run.json.extra.device", extra.get("device")),
        ("confirmatory.json device", confirmatory.get("device")),
    ):
        if type(observed) is not str or observed != CONFIRMATORY_DEVICE:
            raise ValueError(
                f"{location} is {observed!r}, not frozen device "
                f"{CONFIRMATORY_DEVICE!r}"
            )
    metric_schema = confirmatory.get("metric_schema_version")
    if type(metric_schema) is not int or metric_schema != METRIC_SCHEMA_VERSION:
        raise ValueError(
            f"confirmatory.json metric_schema_version is {metric_schema!r}, not "
            f"the frozen schema {METRIC_SCHEMA_VERSION}"
        )

    n_train = confirmatory.get("n_train")
    if type(n_train) is not int or n_train != config.effective_unit.n_transitions:
        raise ValueError(
            f"confirmatory.json n_train is {n_train!r}, not the effective frozen "
            f"training-pool size {config.effective_unit.n_transitions}"
        )
    member_count = confirmatory.get("member_count")
    if type(member_count) is not int or member_count != expected_train.ensemble_size:
        raise ValueError(
            f"confirmatory.json member_count is {member_count!r}, not the frozen "
            f"arm-specific count {expected_train.ensemble_size}"
        )


def _validate_run_record_provenance(
    config: Config, run_record: Mapping[str, Any]
) -> None:
    """Validate complete v2 run provenance against independent registries."""

    _require_exact_keys(run_record, _RUN_RECORD_KEYS, what="run.json")
    if type(run_record.get("schema_version")) is not int or (
        run_record["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError(
            f"run.json schema_version is {run_record.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION}"
        )
    if type(run_record.get("identity_version")) is not int or (
        run_record["identity_version"] != IDENTITY_VERSION
    ):
        raise ValueError(
            f"run.json identity_version is {run_record.get('identity_version')!r}, "
            f"expected {IDENTITY_VERSION}"
        )
    expected_identity_fields = list(UNIT_IDENTITY_FIELDS)
    if not _same_json_value(
        run_record.get("unit_identity_fields"), expected_identity_fields
    ):
        raise ValueError(
            "run.json unit_identity_fields do not equal the registered ordered fields"
        )
    _validate_started_utc(run_record.get("started_utc"))

    expected_effective = Config(unit=config.effective_unit).to_dict()["unit"]
    if not _same_json_value(run_record.get("effective_unit"), expected_effective):
        raise ValueError("run.json effective_unit does not equal the resolved arm")
    base_unit = config.to_dict()["unit"]
    expected_changed = {
        name: value
        for name, value in expected_effective.items()
        if not _same_json_value(base_unit[name], value)
    }
    if not _same_json_value(run_record.get("arm_changed"), expected_changed):
        raise ValueError("run.json arm_changed does not equal the resolved arm diff")

    git = _require_mapping(run_record.get("git"), what="run.json.git")
    _require_exact_keys(git, _GIT_KEYS, what="run.json.git")
    commit = git.get("commit")
    if (
        type(commit) is not str
        or re.fullmatch(r"[0-9a-f]{40}", commit) is None
    ):
        raise ValueError("run.json git.commit is not a lowercase 40-hex commit")
    branch = git.get("branch")
    if type(branch) is not str or not branch.strip() or branch == "unknown":
        raise ValueError("run.json git.branch is absent or unknown")
    if git.get("dirty") is not False or git.get("trustworthy") is not True:
        raise ValueError(
            "run.json Git provenance is not exactly clean and trustworthy"
        )

    env = _require_mapping(run_record.get("env"), what="run.json.env")
    _require_exact_keys(env, _ENV_KEYS, what="run.json.env")
    python_version = env.get("python")
    if (
        type(python_version) is not str
        or re.fullmatch(r"\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)?", python_version) is None
    ):
        raise ValueError("run.json env.python is not a complete Python version")
    major, minor = (int(part) for part in python_version.split(".", 2)[:2])
    if (major, minor) < (3, 11):
        raise ValueError("run.json env.python does not satisfy Python >= 3.11")
    if type(env.get("platform")) is not str or not env["platform"].strip():
        raise ValueError("run.json env.platform must be a non-empty exact string")
    packages = _require_mapping(env.get("packages"), what="run.json.env.packages")
    _require_exact_keys(
        packages, set(TRACKED_PACKAGES), what="run.json.env.packages"
    )
    if not _same_json_value(packages, _FROZEN_PACKAGE_VERSIONS):
        raise ValueError(
            "run.json package versions do not equal the frozen runtime pins"
        )

    extra = _require_mapping(run_record.get("extra"), what="run.json.extra")
    _require_exact_keys(extra, _RUN_EXTRA_KEYS, what="run.json.extra")


def _validate_started_utc(value: Any) -> None:
    if type(value) is not str:
        raise ValueError("run.json started_utc must be an exact timestamp string")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", value) is None:
        raise ValueError(
            "run.json started_utc must use second-resolution ISO-8601 UTC syntax"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("run.json started_utc is not a valid timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("run.json started_utc is not UTC")


def _same_json_value(observed: Any, expected: Any) -> bool:
    """JSON equality that never treats booleans as integers."""

    if type(observed) is not type(expected):
        return False
    if type(expected) is dict:
        return set(observed) == set(expected) and all(
            _same_json_value(observed[key], expected[key]) for key in expected
        )
    if type(expected) is list:
        return len(observed) == len(expected) and all(
            _same_json_value(left, right)
            for left, right in zip(observed, expected, strict=True)
        )
    return observed == expected


def _procedure_from_documents(
    config: Config,
    run_record: Mapping[str, Any],
    confirmatory: Mapping[str, Any],
    spec: RegisteredFitSpec,
    diagnostic_names: tuple[str, ...],
) -> dict[str, Any]:
    extra = _require_mapping(run_record.get("extra"), what="run.json.extra")
    summaries = {
        name: confirmatory[name]
        for name in _SUMMARY_NAMES
        if name in confirmatory
    }
    for name, value in summaries.items():
        if value is not None and (
            type(value) not in (int, float)
            or isinstance(value, bool)
            or not np.isfinite(float(value))
        ):
            raise ValueError(f"confirmatory.json {name} must be finite or null")
    _validate_diagnostic_names(diagnostic_names, arm=spec.arm)
    procedure = {
        "granularity": confirmatory.get("granularity"),
        "seed_partition": confirmatory.get("seed_partition"),
        "stream_version": STREAM_VERSION,
        "role_stream_fingerprints": {
            role: _role_stream_fingerprint(spec.unit, role, spec.seed)
            for role in spec.roles
        },
        "train": config.to_dict()["train"],
        "threading": confirmatory.get("threading"),
        "device": confirmatory.get("device"),
        "evaluation_pool_digest": confirmatory.get("evaluation_pool_digest"),
        "normalisation": confirmatory.get("normalisation"),
        "n_train": confirmatory.get("n_train"),
        "member_count": confirmatory.get("member_count"),
        "metric_schema_version": confirmatory.get("metric_schema_version"),
        "diagnostic_names": list(diagnostic_names),
        "summaries": summaries,
    }
    _require_exact_keys(procedure, _PROCEDURE_KEYS, what="procedure")
    if procedure["granularity"] != CONFIRMATORY_GRANULARITY:
        raise ValueError("procedure granularity is not episode")
    if procedure["seed_partition"] != "confirmatory":
        raise ValueError("procedure seed partition is not confirmatory")
    if procedure["threading"] != extra.get("threading"):
        raise ValueError("procedure threading disagrees with the pre-fit run record")
    if procedure["device"] != extra.get("device"):
        raise ValueError("procedure device disagrees with the pre-fit run record")
    _require_text(procedure["device"], what="device")
    _require_digest(procedure["evaluation_pool_digest"], what="evaluation_pool_digest")
    _normalisation_row(procedure["normalisation"])
    _require_nonnegative_int(procedure["n_train"], what="n_train", positive=True)
    _require_nonnegative_int(procedure["member_count"], what="member_count", positive=True)
    _require_nonnegative_int(
        procedure["metric_schema_version"], what="metric_schema_version", positive=True
    )
    fingerprints = set(procedure["role_stream_fingerprints"].values())
    if len(fingerprints) != 1:
        raise ValueError("registered roles do not share one computation stream")
    return procedure


def _validated_diagnostics(completed: ConfirmatoryRun) -> dict[str, np.ndarray]:
    """Canonicalise the complete arm-specific transition-evidence inventory.

    Fit evidence has no legacy/core-only route.  A sidecar sealed during Week 6
    must already contain everything Week 7 can consume; reconstructing missing
    diagnostics by rerunning the fit would violate the one-fit/many-role
    contract this module exists to enforce.
    """
    evaluation = completed.evaluation
    if evaluation is None:
        raise ValueError("completed run has no per-transition evaluation")
    supplied = completed.diagnostics
    if supplied is None:
        raise ValueError(
            "ConfirmatoryRun.diagnostics is absent; fit evidence requires the "
            "complete canonical diagnostic inventory and never reconstructs a "
            "core-only fallback"
        )
    if type(supplied) is not dict:
        raise ValueError("ConfirmatoryRun.diagnostics must be an exact dict")
    names = tuple(sorted(supplied))
    _validate_diagnostic_names(names, arm=completed.arm)
    arrays = {name: _canonical_array(name, supplied[name]) for name in names}
    _validate_diagnostic_relationships(
        arrays,
        {
            "normalisation": evaluation.scale.as_row(),
            "summaries": {
                name: completed.run[name]
                for name in _SUMMARY_NAMES
                if name in completed.run
            },
        },
        arm=completed.arm,
    )
    for name in _CORE_DIAGNOSTICS:
        expected = _canonical_array(name, getattr(evaluation, name))
        if not np.array_equal(arrays[name], expected):
            raise ValueError(
                f"diagnostics[{name!r}] disagrees with ConfirmatoryRun.evaluation"
            )
    normalisation = evaluation.scale.as_row()
    for name, expected in (
        ("scale", np.asarray(normalisation["scale"], dtype=np.float64)),
        ("scale_n_reference", np.asarray(normalisation["scale_n_reference"])),
        ("scale_domain", np.asarray(normalisation["scale_domain"])),
        ("scale_source", np.asarray(normalisation["scale_source"])),
    ):
        if name in arrays and not np.array_equal(
            arrays[name], _canonical_array(name, expected)
        ):
            raise ValueError(f"diagnostics[{name!r}] disagrees with evaluation scale")
    return arrays


def _canonical_array(name: str, value: Any) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise ValueError(f"{name} must be an exact numpy.ndarray")
    if name == "evaluation_action":
        if value.ndim != 1 or value.size != _FULL_EVALUATION_TRANSITIONS:
            raise ValueError(
                "evaluation_action must be one full one-dimensional evaluation "
                f"inventory of exactly {_FULL_EVALUATION_TRANSITIONS} actions"
            )
        if value.dtype.kind not in "iu":
            raise ValueError(
                "evaluation_action must contain integers, never booleans or floats"
            )
        if (
            value.dtype.kind == "u"
            and value.size
            and int(value.max()) > np.iinfo(np.int64).max
        ):
            raise ValueError("evaluation_action contains a value outside signed int64")
        canonical = np.ascontiguousarray(value, dtype=np.dtype("<i8"))
        if np.any(canonical < 0) or np.any(canonical >= N_ACTIONS):
            raise ValueError(
                "evaluation_action contains an action outside the registered "
                f"range [0, {N_ACTIONS})"
            )
        return canonical
    if name in _TRANSITION_DIAGNOSTICS and (value.ndim != 1 or value.size == 0):
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if name in {"error", "disagreement", "predictive_variance"}:
        if value.dtype.kind != "f" or not np.isfinite(value).all():
            raise ValueError(f"{name} must contain only finite floating-point values")
        return np.ascontiguousarray(value, dtype=np.dtype("<f8"))
    if name in {"episode", "step"}:
        if value.dtype.kind not in "iu":
            raise ValueError(f"{name} must contain integers, never booleans or floats")
        if value.dtype.kind == "u" and value.size and int(value.max()) > np.iinfo(np.int64).max:
            raise ValueError(f"{name} contains a value outside signed int64")
        return np.ascontiguousarray(value, dtype=np.dtype("<i8"))
    if name == "scale":
        if (
            value.ndim != 1
            or value.size == 0
            or value.dtype.kind != "f"
            or not np.isfinite(value).all()
            or np.any(value <= 0)
        ):
            raise ValueError("scale must be a non-empty positive finite float array")
        return np.ascontiguousarray(value, dtype=np.dtype("<f8"))
    if name == "scale_n_reference":
        if value.ndim != 0 or value.dtype.kind not in "iu" or int(value) <= 0:
            raise ValueError("scale_n_reference must be one positive integer scalar")
        return np.asarray(int(value), dtype=np.dtype("<i8"))
    if name in {"scale_domain", "scale_source"}:
        if value.ndim != 0 or value.dtype.kind not in "US" or not str(value.item()):
            raise ValueError(f"{name} must be one non-empty string scalar")
        text = str(value.item())
        return np.asarray(text, dtype=np.dtype(f"<U{len(text)}"))
    raise ValueError(f"unknown diagnostic array {name!r}")


def _expected_diagnostic_names(arm: str) -> tuple[str, ...]:
    if arm == "baseline":
        return _BASELINE_DIAGNOSTICS
    if arm in {"data_repair", "feature_repair", "capacity_repair"}:
        # A repair is deliberately one model, so member disagreement and
        # predictive variance are undefined rather than fabricated as zero.
        return _REPAIR_DIAGNOSTICS
    raise ValueError(f"unknown fit-evidence arm {arm!r}")


def _validate_diagnostic_names(
    names: tuple[str, ...], *, arm: str | None = None
) -> None:
    if names != tuple(sorted(set(names))):
        raise ValueError("diagnostic names must be unique and sorted")
    missing = set(_CORE_DIAGNOSTICS) - set(names)
    unknown = set(names) - _KNOWN_DIAGNOSTICS
    if arm is not None:
        expected = _expected_diagnostic_names(arm)
        if names != expected:
            missing_expected = set(expected) - set(names)
            extra = set(names) - set(expected)
            raise ValueError(
                f"{arm} diagnostic inventory is {list(names)}, expected exactly "
                f"{list(expected)}; missing={sorted(missing_expected)} "
                f"extra={sorted(extra)} unknown={sorted(unknown)}. Incomplete "
                "evidence cannot be repaired by rerunning a later experimental "
                "role"
            )
    elif missing or unknown:
        raise ValueError(
            f"diagnostic inventory missing={sorted(missing)} unknown={sorted(unknown)}"
        )


def _validate_diagnostic_relationships(
    arrays: Mapping[str, np.ndarray],
    procedure: Mapping[str, Any],
    *,
    arm: str,
) -> None:
    _validate_diagnostic_names(tuple(sorted(arrays)), arm=arm)
    for name, array in arrays.items():
        canonical = _canonical_array(name, array)
        if (
            array.dtype != canonical.dtype
            or array.shape != canonical.shape
            or not array.flags.c_contiguous
        ):
            raise ValueError(
                f"diagnostic {name!r} does not have its canonical dtype, shape, "
                "and C-contiguous layout"
            )
    lengths = {
        name: int(array.shape[0])
        for name, array in arrays.items()
        if name in _TRANSITION_DIAGNOSTICS
    }
    if len(set(lengths.values())) != 1:
        raise ValueError(f"evaluation arrays have different lengths: {lengths}")

    full_episode = np.repeat(
        np.arange(K.EVALUATION_EPISODES, dtype=np.dtype("<i8")),
        K.EPISODE_LENGTH,
    )
    full_step = np.tile(
        np.arange(K.EPISODE_LENGTH, dtype=np.dtype("<i8")),
        K.EVALUATION_EPISODES,
    )
    movement_mask = np.isin(
        arrays["evaluation_action"],
        np.asarray(MOVEMENT_ACTIONS, dtype=np.dtype("<i8")),
    )
    expected_episode = full_episode[movement_mask]
    expected_step = full_step[movement_mask]
    expected_rows = int(movement_mask.sum())
    if expected_rows == 0:
        raise ValueError(
            "evaluation_action identifies no movement transitions; scored "
            "movement evidence cannot be empty"
        )
    if set(lengths.values()) != {expected_rows}:
        raise ValueError(
            f"movement-transition arrays have lengths {lengths}, but the "
            f"canonical mask derived from evaluation_action selects exactly "
            f"{expected_rows} rows"
        )
    if not np.array_equal(arrays["episode"], expected_episode) or not np.array_equal(
        arrays["step"], expected_step
    ):
        raise ValueError(
            "persisted movement episode/step rows do not equal exactly the "
            "canonical full-grid identities selected by evaluation_action; "
            "dropped, extra, duplicated, or reordered rows are refused"
        )

    if np.any(arrays["error"] < 0):
        raise ValueError("error must contain only finite non-negative values")
    if arm == "baseline":
        for name in ("disagreement", "predictive_variance"):
            if np.any(arrays[name] < 0):
                raise ValueError(
                    f"baseline {name} must contain only finite non-negative values"
                )
    normalisation = _normalisation_row(procedure["normalisation"])
    scale_expectations = {
        "scale": _canonical_array(
            "scale", np.asarray(normalisation["scale"], dtype=np.float64)
        ),
        "scale_n_reference": _canonical_array(
            "scale_n_reference", np.asarray(normalisation["scale_n_reference"])
        ),
        "scale_domain": _canonical_array(
            "scale_domain", np.asarray(normalisation["scale_domain"])
        ),
        "scale_source": _canonical_array(
            "scale_source", np.asarray(normalisation["scale_source"])
        ),
    }
    for name, expected in scale_expectations.items():
        if name in arrays and not np.array_equal(arrays[name], expected):
            raise ValueError(f"diagnostic {name!r} disagrees with normalisation")
    summaries = _require_mapping(procedure.get("summaries", {}), what="summaries")
    summary_arrays = {
        "mean_error": "error",
        "mean_disagreement": "disagreement",
        "mean_predictive_variance": "predictive_variance",
    }
    for summary_name, array_name in summary_arrays.items():
        value = summaries.get(summary_name)
        if value is not None and array_name in arrays:
            observed = float(np.mean(arrays[array_name], dtype=np.float64))
            if not np.isclose(float(value), observed, rtol=1e-6, atol=1e-9):
                raise ValueError(
                    f"summary {summary_name}={value!r} disagrees with persisted "
                    f"{array_name} mean {observed!r}"
                )
    ratio = summaries.get("ratio")
    if ratio is not None and {"error", "disagreement"} <= set(arrays):
        mean_error = float(np.mean(arrays["error"], dtype=np.float64))
        mean_disagreement = float(
            np.mean(arrays["disagreement"], dtype=np.float64)
        )
        observed_ratio = mean_disagreement / max(mean_error, RATIO_FLOOR)
        if not np.isclose(float(ratio), observed_ratio, rtol=1e-6, atol=1e-9):
            raise ValueError(
                f"summary ratio={ratio!r} disagrees with persisted diagnostic "
                f"ratio {observed_ratio!r}"
            )


def _npy_bytes(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    return buffer.getvalue()


def _load_canonical_npy(data: bytes, *, name: str) -> np.ndarray:
    buffer = io.BytesIO(data)
    try:
        array = np.load(buffer, allow_pickle=False)
    except Exception as exc:
        raise ValueError(f"{name}.npy is not a valid non-pickle NPY file") from exc
    if buffer.tell() != len(data):
        raise ValueError(f"{name}.npy has trailing bytes")
    canonical = _canonical_array(name, array)
    if _npy_bytes(canonical) != data:
        raise ValueError(
            f"{name}.npy is valid but not in the canonical dtype/layout/NPY encoding"
        )
    return canonical


def _diagnostic_paths(names: tuple[str, ...]) -> dict[str, str]:
    _validate_diagnostic_names(names)
    return {name: f"{EVALUATION_DIRECTORY}/{name}.npy" for name in names}


def _diagnostic_inventory_from_artifacts(
    artifacts: Mapping[str, Any]
) -> tuple[str, ...]:
    source_names = set(_SOURCE_NAMES)
    if not source_names <= set(artifacts):
        raise ValueError(
            f"artifact inventory is missing physical sources "
            f"{sorted(source_names - set(artifacts))}"
        )
    names = tuple(sorted(set(artifacts) - source_names))
    _validate_diagnostic_names(names)
    return names


def _canonical_artifact_paths(
    execution_run_id: str, diagnostic_names: tuple[str, ...]
) -> dict[str, str]:
    if type(execution_run_id) is not str or not execution_run_id:
        raise ValueError("execution_run_id must be a non-empty string")
    return {
        **{
            name: f"{execution_run_id}/{filename}"
            for name, filename in _SOURCE_NAMES.items()
        },
        **_diagnostic_paths(diagnostic_names),
    }


def _safe_artifact_path(
    root: Path, raw: Any, *, expected: str, must_exist: bool
) -> Path:
    if type(raw) is not str or not raw:
        raise ValueError(f"artifact path must be a non-empty relative string, got {raw!r}")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise ValueError(f"artifact path {raw!r} is absolute or traverses its fit directory")
    if "\\" in raw or ":" in raw or pure.as_posix() != raw:
        raise ValueError(f"artifact path {raw!r} is not canonical POSIX-relative syntax")
    if raw != expected:
        raise ValueError(f"artifact path {raw!r} != canonical path {expected!r}")
    path = root.joinpath(*pure.parts)
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"artifact path {raw!r} escapes the fit directory") from exc
    if must_exist:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"artifact {raw!r} is absent, a symlink, or not a file")
        if resolved != path:
            raise ValueError(f"artifact {raw!r} does not resolve to its canonical path")
    return path


def _assert_one_physical_run(root: Path, paths: Mapping[str, str]) -> None:
    expected_run = root / paths["run_record"]
    expected_metrics = root / paths["metrics"]
    run_records = sorted(path.resolve() for path in root.rglob("run.json") if path.is_file())
    metrics = sorted(path.resolve() for path in root.rglob(METRICS_FILE) if path.is_file())
    if run_records != [expected_run.resolve()] or metrics != [expected_metrics.resolve()]:
        raise ValueError(
            "fit directory must contain exactly one physical run.json and one "
            "metrics stream, both under the deterministic execution run_id"
        )


def _config_from_run_record(run_record: Mapping[str, Any]) -> Config:
    config_doc = run_record.get("config")
    if not isinstance(config_doc, dict):
        raise ValueError("run.json has no configuration object")
    try:
        return Config.from_dict(config_doc)
    except Exception as exc:
        raise ValueError("run.json configuration is invalid") from exc


def _identities(spec: RegisteredFitSpec) -> dict[str, Any]:
    return {
        "fit_id": spec.fit_id,
        "unit_id": spec.unit_id,
        "config_id": spec.config_id,
        "seed": spec.seed,
        "arm": spec.arm,
        "execution_stage": spec.execution_stage,
        "execution_run_id": spec.execution_run_id,
    }


def _obligations(spec: RegisteredFitSpec) -> list[dict[str, str]]:
    return [
        {"stage": role, "run_id": spec.run_id_for(role)}
        for role in spec.roles
    ]


def _role_stream_fingerprint(unit: UnitSpec, role: str, seed: int) -> str:
    payload = {
        "seed": seed,
        "streams": {purpose: stream_key(unit, role, purpose) for purpose in PURPOSES},
    }
    return _sha256(_canonical_json_bytes(payload))


def _normalisation_row(value: Any) -> dict[str, Any]:
    row = _require_mapping(value, what="normalisation")
    expected = {"scale", "scale_n_reference", "scale_domain", "scale_source"}
    _require_exact_keys(row, expected, what="normalisation")
    scale = row["scale"]
    if (
        type(scale) is not list
        or not scale
        or any(type(item) not in (int, float) or isinstance(item, bool) for item in scale)
        or not np.isfinite(np.asarray(scale, dtype=np.float64)).all()
        or any(float(item) <= 0 for item in scale)
    ):
        raise ValueError("normalisation.scale must be a non-empty positive finite list")
    _require_nonnegative_int(
        row["scale_n_reference"], what="normalisation.scale_n_reference", positive=True
    )
    _require_text(row["scale_domain"], what="normalisation.scale_domain")
    _require_text(row["scale_source"], what="normalisation.scale_source")
    return dict(row)


def _scale_from_row(value: Any) -> NormalisationScale:
    row = _normalisation_row(value)
    return NormalisationScale(
        vector=torch.tensor(row["scale"], dtype=torch.float32),
        n_reference=row["scale_n_reference"],
        domain=row["scale_domain"],
        source=row["scale_source"],
    )


def _validate_metrics(data: bytes) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("metrics.jsonl is not UTF-8") from exc
    lines = text.splitlines()
    if not lines:
        raise ValueError("metrics.jsonl is empty")
    for index, line in enumerate(lines):
        if not line.strip():
            raise ValueError("metrics.jsonl contains a blank record")
        record = _load_json_text(line, what=f"metrics.jsonl line {index + 1}")
        if record.get("i") != index:
            raise ValueError(
                f"metrics.jsonl line {index + 1} has i={record.get('i')!r}; "
                f"expected {index}"
            )


def _load_json_bytes(data: bytes, *, what: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{what} is not UTF-8") from exc
    return _load_json_text(text, what=what)


def _load_json_text(text: str, *, what: str) -> dict[str, Any]:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"{what} contains duplicate JSON key {key!r}")
            out[key] = value
        return out

    try:
        value = json.loads(
            text,
            object_pairs_hook=no_duplicates,
            parse_constant=lambda token: (_raise_json_constant(what, token)),
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"{what} is not valid strict JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{what} must contain one JSON object")
    return value


def _raise_json_constant(what: str, token: str) -> None:
    raise ValueError(f"{what} contains non-finite JSON constant {token}")


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _execution_digest(payload: Mapping[str, Any]) -> str:
    return _sha256(_canonical_json_bytes(payload))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_digest(value: Any, *, what: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{what} is not an exact lowercase SHA256 digest")
    return value


def _require_mapping(value: Any, *, what: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{what} must be an exact JSON object")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, what: str) -> None:
    if set(value) != expected:
        raise ValueError(
            f"{what} keys are {sorted(value)}, expected exactly {sorted(expected)}"
        )


def _require_text(value: Any, *, what: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{what} must be a non-empty string")
    return value


def _require_nonnegative_int(value: Any, *, what: str, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{what} must be an exact {qualifier} integer")
    return value


def _write_bytes_exclusive_atomic(path: Path, data: bytes) -> None:
    """Publish fsynced bytes atomically while refusing an existing final name."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"{path} already exists; evidence is immutable")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.tmp-", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise FileExistsError(
                f"{path} appeared while evidence was being published; refusing "
                "to overwrite it"
            ) from exc
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _fsync_directory(path: Path) -> None:
    """Sync a directory where the host supports directory handles.

    Windows rejects opening directories through ``os.open``.  Artifact file
    contents are still fsynced before publication there; on POSIX the directory
    entry itself is fsynced as well.
    """
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if os.name == "nt" and exc.errno in {
            errno.EACCES,
            errno.EINVAL,
            errno.EPERM,
        }:
            return
        raise
    try:
        os.fsync(descriptor)
    except OSError as exc:
        if not (os.name == "nt" and exc.errno in {errno.EINVAL, errno.EBADF}):
            raise
    finally:
        os.close(descriptor)
