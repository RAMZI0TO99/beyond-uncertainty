"""Versioned physical execution of baseline-anchored sweep repairs.

This is NOT a relaxation of the legacy confirmatory runner or fit reader.
Obligations retain Config identities; actual executions use the contract's
qualified identities and ``paired_run.json`` / ``paired_fit_evidence.json``.
No legacy ``run.json`` is emitted. All inputs are saved and checked before
training, and their hashes are bound by the first fsynced metric.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import torch

from .. import constants as K
from ..config import Arm, Config, UnitSpec
from ..durable import atomic_write_bytes, atomic_write_json, read_json, sha256_file
from ..env.collect import CapturedPools, Pools, SymbolicTransition, TransitionDataset, expected_size
from ..env.gridworld import N_ACTIONS
from ..metrics import RunLogger
from ..models.ensemble import assert_pools_match, train_ensemble
from ..models.uncertainty import NormalisationScale, normalised_error
from ..models.world_model import MOVEMENT_ACTIONS
from ..runrecord import PROJECT_ROOT
from ..streams import POOL_PURPOSES, STREAM_VERSION
from . import confirmatory as C
from . import fit_evidence as F
from . import launch as L
from . import pool_anchors as A
from . import repair_pairing as RP


PAIRED_FIT_SCHEMA_VERSION = 1
PAIRED_FIT_FILE = "paired_fit_evidence.json"
PAIRED_RUN_FILE = "paired_run.json"
CONTRACT_FILE = "pairing_contract.json"
COMPATIBILITY_FILE = "pool_compatibility.json"
INPUT_DIRECTORY = "paired_inputs"
EVALUATION_DIRECTORY = "paired_evaluation"


@dataclass(frozen=True)
class VerifiedPairedRepair:
    fit_dir: Path
    unit: UnitSpec
    arm: str
    seed: int
    physical_fit_id: str
    physical_run_id: str
    obligation_fit_id: str
    obligation_run_id: str
    config_id: str
    execution_digest: str
    contract: RP.SweepRepairContract
    diagnostics: Mapping[str, np.ndarray]
    scale: NormalisationScale
    n_train: int

    @property
    def error(self):
        return self.diagnostics["error"]

    @property
    def episode(self):
        return self.diagnostics["episode"]

    @property
    def step(self):
        return self.diagnostics["step"]


def _json(value: Any) -> bytes:
    return L._pretty_json_bytes(value)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def _equal(actual: Any, expected: Any, *, what: str) -> None:
    if _json(actual) != _json(expected):
        raise ValueError(f"paired repair {what} differs from registered evidence")


def _config(contract: RP.SweepRepairContract) -> Config:
    return Config(unit=contract.unit, arm=Arm(contract.arm), seed=contract.seed,
                  stage="exp3_repairs", train=C.REPAIRED_TRAIN)


def _procedure(contract: RP.SweepRepairContract) -> dict:
    return {
        "paired_fit_schema_version": PAIRED_FIT_SCHEMA_VERSION,
        "pairing_procedure": RP.PAIRING_PROCEDURE,
        "contract_sha256": contract.contract_sha256,
        "physical_fit_id": contract.physical_fit_id,
        "physical_run_id": contract.physical_run_id,
        "obligation_config": _config(contract).to_dict(),
        "obligation_fit_id": contract.obligation_fit_id,
        "obligation_run_id": contract.obligation_run_id,
        "generation_stage": "config_sweep", "obligation_stage": "exp3_repairs",
        "train": dataclasses.asdict(C.REPAIRED_TRAIN),
        "threading": {"num_threads": C.CONFIRMATORY_THREADS,
                      "num_interop_threads": C.CONFIRMATORY_INTEROP_THREADS},
        "device": C.CONFIRMATORY_DEVICE, "granularity": C.CONFIRMATORY_GRANULARITY,
        "normalisation": contract.as_dict()["normalisation"],
    }


def _input_paths() -> dict[str, str]:
    return {f"{pool}.{field}": f"{INPUT_DIRECTORY}/{pool}.{field}.npy"
            for pool in POOL_PURPOSES for field in A._FIELDS}


def _paths(contract: RP.SweepRepairContract) -> dict[str, str]:
    return {
        "contract": CONTRACT_FILE, "compatibility": COMPATIBILITY_FILE,
        "run": f"{contract.physical_run_id}/{PAIRED_RUN_FILE}",
        "metrics": f"{contract.physical_run_id}/metrics.jsonl",
        **_input_paths(),
        **{f"diagnostic.{name}": f"{EVALUATION_DIRECTORY}/{name}.npy"
           for name in F._REPAIR_DIAGNOSTICS},
        "predictions": f"{EVALUATION_DIRECTORY}/predictions.npy",
    }


def _artifact(root: Path, path: str) -> Path:
    candidate = root / path
    A._regular(candidate)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError("paired artifact escapes its physical fit directory")
    if candidate.stat().st_nlink != 1:
        raise ValueError("paired artifact must not be a hard-linked alias")
    return candidate


def _project_root(path: str | Path, *, existing: bool) -> Path:
    candidate = Path(path).absolute()
    for part in (candidate, *candidate.parents):
        if part.exists() or part.is_symlink():
            A._regular(part, directory=True)
    root = candidate.resolve(strict=existing)
    workspace = PROJECT_ROOT.parent.resolve(strict=True)
    if root == workspace or not root.is_relative_to(workspace):
        raise ValueError("paired execution and sources must stay inside the project workspace")
    return root


def _write_inputs(root: Path, collected: RP.AnchoredRepairPools, expected: dict) -> dict:
    RP.validate_anchored_repair_pools(collected, **expected)
    receipt = RP.validate_pool_compatibility(collected.contract, collected.captured, **expected)
    _equal(receipt, json.loads(collected.compatibility_json), what="collected compatibility")
    arrays = RP._repair_arrays(collected.captured, collected.contract.unit,
                               collected.contract.arm, collected.contract.seed)
    for pool, fields in arrays.items():
        for field, array in fields.items():
            atomic_write_bytes(root / _input_paths()[f"{pool}.{field}"], A._array_bytes(array))
    atomic_write_bytes(root / CONTRACT_FILE, collected.contract.canonical_json)
    atomic_write_json(root / COMPATIBILITY_FILE, receipt)
    reread = _read_inputs(root, collected.contract)
    A.assert_pools_equal(collected.pools, reread.pools)
    _equal(RP.validate_pool_compatibility(collected.contract, reread, **expected),
           receipt, what="before-training input readback")
    return receipt


def _read_array(path: Path, *, shape: tuple[int, ...], dtype: np.dtype) -> np.ndarray:
    A._regular(path)
    if path.stat().st_size > int(np.prod(shape)) * dtype.itemsize + 1024:
        raise ValueError("paired input exceeds its registered byte bound")
    raw = path.read_bytes()
    try:
        array = np.load(io.BytesIO(raw), allow_pickle=False)
    except (OSError, ValueError, TypeError, EOFError) as exc:
        raise ValueError("paired input is not a non-pickle NPY array") from exc
    if (type(array) is not np.ndarray or array.dtype != dtype or array.shape != shape
            or not np.isfinite(array).all() or A._array_bytes(array) != raw):
        raise ValueError("paired input has noncanonical dtype/shape/content/encoding")
    return array


def _read_inputs(root: Path, contract: RP.SweepRepairContract) -> CapturedPools:
    unit, arm, seed = contract.unit, contract.arm, contract.seed
    effective = Arm(arm).resolve(unit)
    width = A._encoding(effective)["obs_dim"]
    pools, symbolic = {}, {}
    paths = _input_paths()
    for pool in POOL_PURPOSES:
        n = expected_size(effective, pool, K.EPISODE_LENGTH)
        arrays = {}
        for field in A._FIELDS:
            floating = field in ("obs", "next_obs")
            shape = ((n, width) if floating else (n, 2 + 5 * unit.n_objects)
                     if field in ("state", "next_state") else (n,))
            arrays[field] = _read_array(
                _artifact(root, paths[f"{pool}.{field}"]), shape=shape,
                dtype=np.dtype("float32" if floating else "int64"),
            )
        if np.any((arrays["action"] < 0) | (arrays["action"] >= N_ACTIONS)):
            raise ValueError("paired input action is outside the environment inventory")
        transitions = tuple(SymbolicTransition(
            A._from_row(arrays["state"][i], effective), int(arrays["action"][i]),
            A._from_row(arrays["next_state"][i], effective),
            int(arrays["episode"][i]), int(arrays["step"][i]),
        ) for i in range(n))
        pools[pool] = TransitionDataset(
            **{field: arrays[field] for field in A._ARRAY_FIELDS}, unit=effective,
            coverage=A._coverage(transitions, effective), seed=seed,
            pool=pool, source_unit=unit, arm=arm, stage="config_sweep",
            episode_length=K.EPISODE_LENGTH, stream_version=STREAM_VERSION,
        )
        symbolic[pool] = transitions
    captured = CapturedPools(Pools(**pools), **symbolic)
    RP._repair_arrays(captured, unit, arm, seed)
    return captured


def _validate_environment(environment: object, expected_commit: str) -> None:
    env = L._strict_keys(environment, {"git", "python", "platform", "packages", "exact_pins"},
                         what="paired run environment")
    git = L._strict_keys(env["git"], {"commit", "branch", "dirty", "trustworthy"},
                         what="paired run Git provenance")
    if (git["commit"] != F._validate_expected_git_commit(expected_commit)
            or git["dirty"] is not False or git["trustworthy"] is not True
            or type(git["branch"]) is not str or not git["branch"]):
        raise ValueError("paired run does not attest the independently expected clean commit")
    _equal(env["packages"], F._FROZEN_PACKAGE_VERSIONS, what="package inventory")
    _equal(env["exact_pins"], F._FROZEN_PACKAGE_VERSIONS, what="package pins")
    for field in ("python", "platform"):
        if type(env[field]) is not str or not env[field].strip():
            raise ValueError(f"paired run lacks {field} provenance")


def _assert_separate_source(root: Path, baseline_source: Path) -> None:
    """Writer and recovery must agree on immutable-source separation."""
    if root == baseline_source or root in baseline_source.parents or baseline_source in root.parents:
        raise ValueError("paired output must not overlap its immutable baseline source")


def _check_separate_schema(root: Path) -> dict[str, list[str]]:
    """Inventory execution markers recursively, without hiding aliases/errors.

    Checking only the sidecar's declared paths misses a second execution whose
    files were never included in that sidecar. Supervisor receipts and ordinary
    auxiliary files are allowed; extra run/fit records and metrics are not.
    Manual traversal avoids rglob's suppressed scan errors and refuses links
    before descending, including a linked directory hiding another execution.
    """
    A._regular(root, directory=True)
    legacy = {F.FIT_EVIDENCE_FILE, "run.json", "confirmatory.json"}
    inventory = {name: [] for name in (*legacy, PAIRED_FIT_FILE, PAIRED_RUN_FILE, "metrics.jsonl")}
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            children = list(directory.iterdir())
        except OSError as exc:
            raise ValueError(f"cannot inspect paired execution directory: {directory}") from exc
        for child in children:
            is_directory = child.is_dir()
            A._regular(child, directory=is_directory)
            # Recognize reserved names even on case-sensitive hosts; a changed
            # spelling must not become a way to hide a second execution.
            name = child.name.casefold()
            if name in inventory:
                if is_directory:
                    raise ValueError("paired execution marker must be a regular file")
                inventory[name].append(child.relative_to(root).as_posix())
            if is_directory:
                pending.append(child)
    if any(inventory[name] for name in legacy):
        raise ValueError("legacy fit/run evidence cannot masquerade as a paired execution")
    return inventory


def _assert_one_physical_execution(root: Path, contract: RP.SweepRepairContract) -> None:
    inventory = _check_separate_schema(root)
    expected = {
        PAIRED_FIT_FILE: [PAIRED_FIT_FILE],
        PAIRED_RUN_FILE: [f"{contract.physical_run_id}/{PAIRED_RUN_FILE}"],
        "metrics.jsonl": [f"{contract.physical_run_id}/metrics.jsonl"],
    }
    for name, paths in expected.items():
        if sorted(inventory[name]) != paths:
            raise ValueError(
                "paired directory must contain exactly one physical paired run, "
                "metrics stream and fit sidecar under their deterministic paths; "
                f"{name}: found={sorted(inventory[name])}, expected={paths}"
            )


def run_paired_repair(
    unit: UnitSpec, *, arm: str, seed: int, baseline_source: str | Path,
    expected_baseline_commit: str, expected_baseline_execution_digest: str,
    expected_git_commit: str, out_dir: str | Path,
) -> VerifiedPairedRepair:
    """One fixed single-model repair, distinct from all legacy executions."""
    root = _project_root(out_dir, existing=False)
    baseline_source = _project_root(baseline_source, existing=True)
    _assert_separate_source(root, baseline_source)
    expected = dict(baseline_source=baseline_source,
                    expected_baseline_commit=expected_baseline_commit,
                    expected_baseline_execution_digest=expected_baseline_execution_digest)
    F._require_current_git_commit(expected_git_commit)
    contract = RP.registered_sweep_pairing(unit, arm=arm, seed=seed, **expected)
    for part in (root, *root.parents):
        if part.exists():
            A._regular(part, directory=True)
    # Supervisor envelope may already exist, but no scientific execution may.
    if root.exists() and any(p.name != "attempt.json" for p in root.iterdir()):
        raise ValueError("paired output contains prior evidence; refuse overwrite/retraining")
    C._pin_threading(C.CONFIRMATORY_THREADS, C.CONFIRMATORY_INTEROP_THREADS)
    _equal(C.torch_threading(), _procedure(contract)["threading"], what="actual CPU threading")
    environment = L._current_environment()
    _validate_environment(environment, expected_git_commit)
    collected = RP.collect_anchored_repair_pools(contract, **expected)
    root.mkdir(parents=True, exist_ok=True)
    receipt = _write_inputs(root, collected, expected)
    procedure = _procedure(contract)
    run_record = {"procedure": procedure, "environment": environment,
                  "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "compatibility_sha256": _digest(receipt)}
    run_dir = root / contract.physical_run_id
    atomic_write_json(run_dir / PAIRED_RUN_FILE, run_record)
    # No RunLogger.start(Config): that would falsely stamp an old physical ID.
    with RunLogger(run_dir, contract.physical_run_id) as logger:
        logger.log(event="paired_inputs", contract_sha256=contract.contract_sha256,
                   compatibility_sha256=_digest(receipt), paired_fit_schema_version=1)
        assert_pools_match(collected.pools, unit=unit, arm=arm, stage="config_sweep", seed=seed)
        RP.validate_anchored_repair_pools(collected, **expected)
        F._require_current_git_commit(expected_git_commit)
        ensemble = train_ensemble(
            unit, collected.pools, C.REPAIRED_TRAIN, stage="config_sweep", seed=seed,
            arm=arm, granularity=C.CONFIRMATORY_GRANULARITY, logger=logger,
            epoch_logger=lambda member: C._EpochLogger(logger, member), device=C.CONFIRMATORY_DEVICE,
        )
    if len(ensemble.members) != 1 or {p.device.type for m in ensemble.members for p in m.parameters()} != {"cpu"}:
        raise ValueError("paired repair did not use the fixed single CPU model")
    pools = collected.pools
    move = np.isin(pools.evaluation.action, MOVEMENT_ACTIONS)
    obs = torch.as_tensor(np.array(pools.evaluation.obs[move], copy=True))
    action = torch.as_tensor(np.array(pools.evaluation.action[move], copy=True))
    nxt = torch.as_tensor(np.array(pools.evaluation.next_obs[move], copy=True))
    predictions = ensemble.member_predictions(obs, action).mean(dim=0)
    targets = ensemble.members[0].targets(nxt)[0]
    error = normalised_error(predictions, targets, collected.scale).detach().numpy()
    values = {
        "error": error, "episode": pools.evaluation.episode[move],
        "step": pools.evaluation.step[move], "evaluation_action": pools.evaluation.action,
        "scale": np.asarray(collected.scale.vector, dtype=np.float64),
        "scale_n_reference": np.asarray(collected.scale.n_reference),
        "scale_source": np.asarray(collected.scale.source),
        "scale_domain": np.asarray(collected.scale.domain),
    }
    paths = _paths(contract)
    for name, value in values.items():
        atomic_write_bytes(root / paths[f"diagnostic.{name}"], F._npy_bytes(F._canonical_array(name, value)))
    atomic_write_bytes(root / paths["predictions"], A._array_bytes(predictions.detach().numpy()))
    # Re-open exact consumed inputs and baseline after computation, before seal.
    after = _read_inputs(root, contract)
    A.assert_pools_equal(pools, after.pools)
    _equal(RP.validate_pool_compatibility(contract, after, **expected), receipt,
           what="after-training compatibility")
    F._require_current_git_commit(expected_git_commit)
    payload = {"paired_fit_schema_version": PAIRED_FIT_SCHEMA_VERSION,
               "procedure": procedure,
               "artifacts": {name: {"path": path, "sha256": sha256_file(_artifact(root, path))}
                             for name, path in paths.items()}}
    atomic_write_json(root / PAIRED_FIT_FILE, {**payload, "execution_digest": _digest(payload)})
    return load_paired_repair_evidence(root, unit=unit, arm=arm, seed=seed,
                                      expected_git_commit=expected_git_commit, **expected)


def load_paired_repair_evidence(
    root: str | Path, *, unit: UnitSpec, arm: str, seed: int,
    baseline_source: str | Path, expected_baseline_commit: str,
    expected_baseline_execution_digest: str, expected_git_commit: str,
) -> VerifiedPairedRepair:
    """Strict new-schema reader; reconstruct compatibility without regenerating data."""
    directory = _project_root(root, existing=True)
    baseline_source = _project_root(baseline_source, existing=True)
    _assert_separate_source(directory, baseline_source)
    F._validate_expected_git_commit(expected_git_commit)
    expected = dict(baseline_source=baseline_source,
                    expected_baseline_commit=expected_baseline_commit,
                    expected_baseline_execution_digest=expected_baseline_execution_digest)
    contract = RP.registered_sweep_pairing(unit, arm=arm, seed=seed, **expected)
    _assert_one_physical_execution(directory, contract)
    sidecar = _artifact(directory, PAIRED_FIT_FILE)
    document = L._strict_keys(read_json(sidecar), {"paired_fit_schema_version", "procedure",
                                                 "artifacts", "execution_digest"}, what="paired fit")
    if sidecar.read_bytes() != _json(document):
        raise ValueError("paired fit sidecar is not canonical JSON")
    if type(document["paired_fit_schema_version"]) is not int or document["paired_fit_schema_version"] != 1:
        raise ValueError("wrong paired fit schema")
    procedure = _procedure(contract)
    _equal(document["procedure"], procedure, what="procedure")
    paths = _paths(contract)
    artifacts = L._strict_keys(document["artifacts"], set(paths), what="paired artifact inventory")
    payload = {k: document[k] for k in ("paired_fit_schema_version", "procedure", "artifacts")}
    if document["execution_digest"] != _digest(payload):
        raise ValueError("paired execution digest differs")
    for name, path in paths.items():
        row = L._strict_keys(artifacts[name], {"path", "sha256"}, what=f"paired artifact {name}")
        if row["path"] != path or sha256_file(_artifact(directory, path)) != row["sha256"]:
            raise ValueError(f"paired artifact {name} changed or has a substituted path")
    if (directory / CONTRACT_FILE).read_bytes() != contract.canonical_json:
        raise ValueError("paired contract differs from independently rederived baseline anchor")
    captured = _read_inputs(directory, contract)
    receipt = RP.validate_pool_compatibility(contract, captured, **expected)
    _equal(read_json(directory / COMPATIBILITY_FILE), receipt, what="persisted compatibility")
    run_record = L._strict_keys(read_json(directory / paths["run"]),
                                {"procedure", "environment", "started_utc", "compatibility_sha256"},
                                what="paired physical run")
    _equal(run_record["procedure"], procedure, what="physical run procedure")
    _validate_environment(run_record["environment"], expected_git_commit)
    F._validate_started_utc(run_record["started_utc"])
    if run_record["compatibility_sha256"] != _digest(receipt):
        raise ValueError("paired run does not bind before-training input compatibility")
    raw_metrics = (directory / paths["metrics"]).read_bytes()
    F._validate_metrics(raw_metrics)
    metrics = [F._load_json_text(line, what="paired metrics") for line in raw_metrics.decode().splitlines()]
    first = {"i": 0, "event": "paired_inputs", "contract_sha256": contract.contract_sha256,
             "compatibility_sha256": _digest(receipt), "paired_fit_schema_version": 1}
    _equal(metrics[0], first, what="before-training first metric")
    if sum(row.get("event") == "paired_inputs" for row in metrics) != 1:
        raise ValueError("paired metrics contain duplicate input bindings")
    arrays = {name: F._load_canonical_npy((directory / paths[f"diagnostic.{name}"]).read_bytes(), name=name)
              for name in F._REPAIR_DIAGNOSTICS}
    F._validate_diagnostic_relationships(arrays, {"normalisation": procedure["normalisation"]}, arm=arm)
    evaluation = captured.pools.evaluation
    move = np.isin(evaluation.action, MOVEMENT_ACTIONS)
    for field, value in (("evaluation_action", evaluation.action),
                         ("episode", evaluation.episode[move]), ("step", evaluation.step[move])):
        if not np.array_equal(arrays[field], value):
            raise ValueError("paired scored transitions differ from exact anchored evaluation")
    predictions = _read_array(directory / paths["predictions"],
                              shape=(int(move.sum()), 2), dtype=np.dtype("float32"))
    scale = F._scale_from_row(procedure["normalisation"])
    expected_error = normalised_error(torch.as_tensor(predictions),
                                      torch.as_tensor(evaluation.next_obs[move][:, [0, 1]]), scale).numpy()
    if not np.array_equal(arrays["error"], F._canonical_array("error", expected_error)):
        raise ValueError("paired error differs from saved predictions, full-pool scale and actual targets")
    # Detect concurrent mutations after the expensive compatibility verification.
    for name, path in paths.items():
        if sha256_file(_artifact(directory, path)) != artifacts[name]["sha256"]:
            raise ValueError("paired source changed during verification")
    if sidecar.read_bytes() != _json(document):
        raise ValueError("paired sidecar changed during verification")
    # An extra execution need not modify any declared artifact. Re-inventory
    # after the expensive readback as well as checking the declared hashes.
    _assert_one_physical_execution(directory, contract)
    for array in arrays.values():
        array.flags.writeable = False
    return VerifiedPairedRepair(
        directory.resolve(), unit, arm, seed, contract.physical_fit_id,
        contract.physical_run_id, contract.obligation_fit_id, contract.obligation_run_id,
        _config(contract).config_id, document["execution_digest"], contract,
        MappingProxyType(arrays), scale, len(captured.pools.train),
    )
