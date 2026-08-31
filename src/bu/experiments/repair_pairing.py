"""Baseline-anchored sweep repair contracts and exact pool compatibility.

D-155 follow-up; see docs/sweep_pairing_and_ordinary_labels_design.md. This
module does NOT execute a fit, assign a label, change a legacy RNG key, or
bypass the legacy confirmatory runner's wrong-pairing refusal. ``config_sweep``
here means data generation, not a newly invented legacy repair obligation.

Every public evidence boundary reopens the baseline and its contemporaneous
anchor. The caller supplies the independently expected baseline commit AND
execution digest. The anchor digest comes from the first sealed metrics event,
through fit_evidence.validate_sweep_pool_anchors, never from caller metadata.
Contracts contain no source paths. Physical IDs are procedure-qualified and
cannot masquerade as Config-derived obligation IDs. A future versioned runner
must persist those IDs truthfully and revalidate the returned pools before use.

Private pool_anchors helpers are reused for symbolic validation/encoding and
coverage (one definition of these invariants), not for manufacturing a baseline
record for repaired data. Full symbolic states remain experimenter-only.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .. import constants as K
from ..config import Arm, Config, IDENTITY_VERSION, SCHEMA_VERSION, UnitSpec
from ..durable import _decode_json, atomic_write_bytes
from ..env.collect import (
    CapturedPools, CoverageReport, Pools, SymbolicTransition, TransitionDataset,
    collect_with_anchors, expected_size,
)
from ..env.gridworld import GridWorld, N_ACTIONS
from ..models.uncertainty import NormalisationScale
from ..streams import DATA_PURPOSES, POOL_PURPOSES, PURPOSES, STREAM_VERSION, stream_key
from . import fit_evidence as F
from . import pool_anchors as A
from .confirmatory import assert_registered_obligation
from .enumerate_units import stage_of

PAIRING_SCHEMA_VERSION = 1
PAIRING_PROCEDURE = "baseline_anchored_sweep_v1"
COMPATIBILITY_SCHEMA_VERSION = 1
_GENERATION_STAGE = "config_sweep"
_OBLIGATION_STAGE = "exp3_repairs"
_ARRAY_FIELDS = ("obs", "action", "next_obs", "episode", "step")


def _json(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("pairing evidence must be finite JSON data") from exc


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hex(value: Any, size: int, name: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{%d}" % size, value) is None:
        raise ValueError(f"{name} must be an exact lowercase {size}-hex digest")
    return value


@dataclass(frozen=True)
class SweepRepairContract:
    """Immutable canonical document, not a reusable trust token.

    ``as_dict`` returns a fresh copy; nested mutation cannot change this object.
    Hand construction is deliberately not evidence verification. Every consumer
    calls validate_pairing_contract against independent expectations and disk.
    """

    canonical_json: bytes

    def as_dict(self) -> dict:
        if type(self.canonical_json) is not bytes:
            raise ValueError("contract canonical_json must be exact bytes")
        value = _decode_json(self.canonical_json, source="sweep repair contract")
        if type(value) is not dict or _json(value) != self.canonical_json:
            raise ValueError("contract must be a canonical JSON object")
        return value

    @property
    def contract_sha256(self) -> str:
        self.as_dict()
        return _digest(self.canonical_json)

    @property
    def unit(self) -> UnitSpec:
        row = self.as_dict()["unit"]
        return UnitSpec(**dict(row, withheld_features=tuple(row["withheld_features"])))

    @property
    def arm(self) -> str:
        return self.as_dict()["arm"]

    @property
    def seed(self) -> int:
        return self.as_dict()["seed"]

    @property
    def physical_fit_id(self) -> str:
        return self.as_dict()["physical_fit_id"]

    @property
    def physical_run_id(self) -> str:
        return self.as_dict()["physical_run_id"]

    @property
    def obligation_fit_id(self) -> str:
        return self.as_dict()["obligation_fit_id"]

    @property
    def obligation_run_id(self) -> str:
        return self.as_dict()["obligation_run_id"]


@dataclass(frozen=True)
class AnchoredRepairPools:
    """Collected inputs plus a compatibility receipt, NOT completed fit evidence."""

    contract: SweepRepairContract
    captured: CapturedPools
    scale: NormalisationScale
    compatibility_json: bytes

    @property
    def pools(self) -> Pools:
        return self.captured.pools

    @property
    def compatibility_sha256(self) -> str:
        return _digest(self.compatibility_json)


def registered_sweep_repair_spec(unit: UnitSpec, *, arm: str, seed: int) -> F.RegisteredFitSpec:
    """Metadata-only plan boundary, useful before any baseline is executed.

    Exactly the assigned two repair arms and three absolute seeds of each of the
    registered 225 sweep units are admitted. No arbitrary stage/seed override.
    It does not claim that a baseline, compatible dataset or repair exists.
    """
    if type(unit) is not UnitSpec or type(arm) is not str or type(seed) is not int:
        raise ValueError("sweep repair requires an exact UnitSpec, string arm and integer seed")
    if arm == "baseline" or stage_of(unit) != _GENERATION_STAGE:
        raise ValueError("baseline-anchored procedure is for sweep-only repair obligations")
    assert_registered_obligation(unit, arm=arm, stage=_OBLIGATION_STAGE, seed=seed)
    assert_registered_obligation(unit, arm="baseline", stage=_GENERATION_STAGE, seed=seed)
    Arm(arm).resolve(unit)
    config = Config(unit=unit, arm=Arm(arm), stage=_OBLIGATION_STAGE, seed=seed)
    return F.RegisteredFitSpec(unit, arm, seed, (_OBLIGATION_STAGE,), _OBLIGATION_STAGE,
                               config.unit_id, config.config_id, config.fit_id, config.run_id)


def _keys(unit: UnitSpec, seed: int) -> tuple[dict, dict]:
    data = {p: dict(stream_key(unit, _GENERATION_STAGE, p), seed=seed)
            for p in sorted(DATA_PURPOSES)}
    # Repairs are single models. Member zero is explicit, exactly as in the
    # existing bootstrap/initialization/batch calls; effective unit NEVER keys RNG.
    model = {p: dict(stream_key(unit, _OBLIGATION_STAGE, p, member=0), seed=seed)
             for p in PURPOSES if p not in DATA_PURPOSES}
    return data, model


def _physical_digest(spec: F.RegisteredFitSpec, baseline_digest: str) -> str:
    return _digest(_json({
        "pairing_schema_version": PAIRING_SCHEMA_VERSION, "procedure": PAIRING_PROCEDURE,
        "obligation_fit_id": spec.fit_id, "baseline_execution_digest": baseline_digest,
    }))


def _physical_ids(spec: F.RegisteredFitSpec, baseline_digest: str) -> tuple[str, str]:
    # New schema, no physical evidence yet: compact IDs avoid consuming the
    # Windows path budget twice in jobs/<fit>/<run>/diagnostics. The complete
    # 256-bit hash and original obligation IDs remain mandatory in the contract;
    # immutable writers/strict reload reject different content on an ID collision.
    stem = f"ps1-{_physical_digest(spec, baseline_digest)[:32]}"
    return stem, f"{stem}-r"


def _read_source(spec: F.RegisteredFitSpec, source: str | Path, commit: str, digest: str):
    _hex(commit, 40, "expected_baseline_commit")
    _hex(digest, 64, "expected_baseline_execution_digest")
    root = Path(source).absolute()
    A._regular(root, directory=True)
    # Checks the first sealed metrics event and the after-fit linkage, including
    # evaluation content and full movement scale; no caller-selected anchor hash.
    anchor = F.validate_sweep_pool_anchors(root, expected_git_commit=commit)
    fit = F.load_fit_evidence(root, expected_git_commit=commit)
    baseline = Config(unit=spec.unit, arm=Arm("baseline"), stage=_GENERATION_STAGE, seed=spec.seed)
    if (fit.unit != spec.unit or fit.arm != "baseline" or fit.seed != spec.seed
            or fit.roles != (_GENERATION_STAGE,) or fit.execution_stage != _GENERATION_STAGE
            or fit.fit_id != baseline.fit_id or fit.execution_run_id != baseline.run_id
            or fit.execution_digest != digest):
        raise ValueError("baseline identity or execution digest differs from independent expectations")
    if (anchor.source_commit != commit or anchor.pools.train.unit != spec.unit
            or anchor.pools.train.seed != spec.seed
            or _json(anchor.scale.as_row()) != _json(fit.scale.as_row())):
        raise ValueError("baseline anchor identity or full movement normalisation differs")
    return fit, anchor


def _array_digest(array: np.ndarray) -> str:
    # Length-framed type/shape and exact bytes, not approximate values or paths.
    header = _json({"dtype": array.dtype.str, "shape": list(array.shape)})
    return _digest(len(header).to_bytes(8, "big") + header + array.tobytes())


def _rule(arm: str) -> str:
    if arm == "data_repair":
        return "exact_training_prefix_10x_and_unchanged_validation_evaluation"
    if arm == "feature_repair":
        return "identical_latent_trajectories_reencoded_through_baseline_encoder"
    return "unchanged_raw_pools"


def _contract(spec: F.RegisteredFitSpec, fit: F.VerifiedFitEvidence,
              anchor: A.VerifiedPoolAnchors, commit: str) -> SweepRepairContract:
    data, model = _keys(spec.unit, spec.seed)
    physical_fit, physical_run = _physical_ids(spec, fit.execution_digest)
    document = {
        "pairing_schema_version": PAIRING_SCHEMA_VERSION, "procedure": PAIRING_PROCEDURE,
        "schema_version": SCHEMA_VERSION, "identity_version": IDENTITY_VERSION,
        "unit": dataclasses.asdict(spec.unit), "unit_id": spec.unit_id,
        "arm": spec.arm, "seed": spec.seed, "config_id": spec.config_id,
        "obligation_stage": _OBLIGATION_STAGE, "generation_stage": _GENERATION_STAGE,
        "obligation_fit_id": spec.fit_id, "obligation_run_id": spec.execution_run_id,
        "physical_fit_id": physical_fit, "physical_run_id": physical_run,
        "physical_identity_sha256": _physical_digest(spec, fit.execution_digest),
        "baseline_fit_id": fit.fit_id, "baseline_run_id": fit.execution_run_id,
        "baseline_commit": commit, "baseline_execution_digest": fit.execution_digest,
        "pool_anchor_sha256": anchor.anchor_sha256,
        "pool_anchor_schema_version": A.POOL_ANCHOR_SCHEMA_VERSION,
        "symbolic_capture_version": A.SYMBOLIC_CAPTURE_VERSION,
        "stream_version": STREAM_VERSION, "data_keys": data, "model_keys": model,
        "normalisation": anchor.scale.as_row(),
        # These are requirements bound before collection, not a false assertion
        # that a repair has already passed compatibility or completed training.
        "compatibility_requirement": {
            "schema_version": COMPATIBILITY_SCHEMA_VERSION, "rule": _rule(spec.arm),
            "episode_length": K.EPISODE_LENGTH,
            "baseline_sizes": {p: len(getattr(anchor.pools, p)) for p in POOL_PURPOSES},
            "repair_sizes": {p: expected_size(Arm(spec.arm).resolve(spec.unit), p, K.EPISODE_LENGTH)
                             for p in POOL_PURPOSES},
        },
    }
    return SweepRepairContract(_json(document))


def registered_sweep_pairing(
    unit: UnitSpec, *, arm: str, seed: int, baseline_source: str | Path,
    expected_baseline_commit: str, expected_baseline_execution_digest: str,
) -> SweepRepairContract:
    """Derive a contract from registered metadata and independently bound evidence."""
    spec = registered_sweep_repair_spec(unit, arm=arm, seed=seed)
    fit, anchor = _read_source(spec, baseline_source, expected_baseline_commit,
                               expected_baseline_execution_digest)
    return _contract(spec, fit, anchor, expected_baseline_commit)


def _validate(contract: SweepRepairContract, *, baseline_source: str | Path,
              expected_baseline_commit: str, expected_baseline_execution_digest: str):
    if type(contract) is not SweepRepairContract:
        raise ValueError("an exact SweepRepairContract is required, not a legacy fit or duck type")
    try:
        document = contract.as_dict()
        fields = document["unit"]
        if type(fields) is not dict or type(fields.get("withheld_features")) is not list:
            raise ValueError("contract unit must have canonical fields")
        unit = UnitSpec(**dict(fields, withheld_features=tuple(fields["withheld_features"])))
        spec = registered_sweep_repair_spec(unit, arm=document["arm"], seed=document["seed"])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("contract has malformed unit, arm or seed metadata") from exc
    fit, anchor = _read_source(spec, baseline_source, expected_baseline_commit,
                               expected_baseline_execution_digest)
    expected = _contract(spec, fit, anchor, expected_baseline_commit)
    if contract.canonical_json != expected.canonical_json:
        raise ValueError("contract differs from rederived registered baseline-anchored procedure")
    return anchor


def validate_pairing_contract(
    contract: SweepRepairContract, *, baseline_source: str | Path,
    expected_baseline_commit: str, expected_baseline_execution_digest: str,
) -> SweepRepairContract:
    """Reject even re-signed forgeries; reopen the baseline and sealed anchor."""
    _validate(contract, baseline_source=baseline_source,
              expected_baseline_commit=expected_baseline_commit,
              expected_baseline_execution_digest=expected_baseline_execution_digest)
    return contract


def write_pairing_contract(path: str | Path, contract: SweepRepairContract, **expected) -> Path:
    """Exclusive/idempotent write only after full evidence revalidation."""
    validate_pairing_contract(contract, **expected)
    target = Path(path).absolute()
    for part in (target.parent, *target.parent.parents):
        if part.exists() or part.is_symlink():
            A._regular(part, directory=True)
    return atomic_write_bytes(target, contract.canonical_json)


def load_pairing_contract(
    path: str | Path, *, unit: UnitSpec, arm: str, seed: int,
    expected_contract_sha256: str, baseline_source: str | Path,
    expected_baseline_commit: str, expected_baseline_execution_digest: str,
) -> SweepRepairContract:
    """Strict reload against independent unit/arm/seed, source and contract hash."""
    _hex(expected_contract_sha256, 64, "expected_contract_sha256")
    path = Path(path).absolute()
    A._regular(path)
    if path.stat().st_size > 32768:
        raise ValueError("pairing contract exceeds schema size")
    raw = path.read_bytes()
    # Hash the same byte snapshot we decode, not a separate first file read.
    if len(raw) > 32768 or _digest(raw) != expected_contract_sha256:
        raise ValueError("pairing contract differs from expected digest or exceeds schema size")
    observed = SweepRepairContract(raw)
    observed.as_dict()
    expected = registered_sweep_pairing(
        unit, arm=arm, seed=seed, baseline_source=baseline_source,
        expected_baseline_commit=expected_baseline_commit,
        expected_baseline_execution_digest=expected_baseline_execution_digest,
    )
    if observed.canonical_json != expected.canonical_json:
        raise ValueError("loaded contract differs from rederived registered procedure")
    return expected


def _repair_arrays(captured: CapturedPools, unit: UnitSpec, arm: str, seed: int) -> dict:
    if type(captured) is not CapturedPools or type(captured.pools) is not Pools:
        raise ValueError("repair compatibility requires exact CapturedPools and Pools")
    effective = Arm(arm).resolve(unit)
    env = GridWorld(effective)
    result = {}
    for pool in POOL_PURPOSES:
        data, transitions = getattr(captured.pools, pool), getattr(captured, pool)
        n = expected_size(effective, pool, K.EPISODE_LENGTH)
        if type(data) is not TransitionDataset:
            raise ValueError(f"{pool} is not an exact TransitionDataset")
        provenance = (data.unit, data.source_unit, data.arm, data.stage, data.seed,
                      data.pool, data.episode_length, data.stream_version)
        expected = (effective, unit, arm, _GENERATION_STAGE, seed, pool, K.EPISODE_LENGTH, STREAM_VERSION)
        if (provenance != expected or any(type(v) is not int for v in
                                        (data.seed, data.episode_length, data.stream_version))
                or any(type(v) is not str for v in (data.arm, data.stage, data.pool))):
            raise ValueError(f"{pool} repaired pool provenance differs from registered generation")
        if type(transitions) is not tuple or len(transitions) != n:
            raise ValueError(f"{pool} repaired symbolic count differs from registered size")
        arrays = {field: getattr(data, field) for field in _ARRAY_FIELDS}
        for field, array in arrays.items():
            floating = field in ("obs", "next_obs")
            shape = (n, env.encoder.size) if floating else (n,)
            if (type(array) is not np.ndarray or array.dtype != np.dtype("float32" if floating else "int64")
                    or array.shape != shape or not np.isfinite(array).all()):
                raise ValueError(f"{pool}.{field} repaired dtype, shape or finite content is invalid")
        states, successors = [], []
        for i, t in enumerate(transitions):
            if (type(t) is not SymbolicTransition or type(t.action) is not int
                    or not 0 <= t.action < N_ACTIONS or type(t.episode) is not int or type(t.step) is not int
                    or t.episode != i // K.EPISODE_LENGTH or t.step != i % K.EPISODE_LENGTH):
                raise ValueError(f"{pool} repaired symbolic transition identifiers are invalid")
            states.append(A._state_row(t.state, effective))
            successors.append(A._state_row(t.next_state, effective))
            if (t.action != data.action[i] or t.episode != data.episode[i] or t.step != data.step[i]
                    or t.next_state != env.transition(t.state, t.action)
                    or (t.step and t.state != transitions[i - 1].next_state)):
                raise ValueError(f"{pool} repaired trajectory or transition identifiers disagree")
        arrays.update(state=np.asarray(states, dtype=np.int64), next_state=np.asarray(successors, dtype=np.int64))
        for field, future in (("obs", False), ("next_obs", True)):
            encoded = A.reencode_anchors(transitions, effective, next_state=future)
            if arrays[field].tobytes() != encoded.tobytes():
                raise ValueError(f"{pool}.{field} repaired array contradicts symbolic encoding")
        if (type(data.coverage) is not CoverageReport
                or _json(data.coverage.to_dict()) != _json(A._coverage(transitions, effective).to_dict())):
            raise ValueError(f"{pool} repaired coverage contradicts latent trajectories")
        result[pool] = arrays
    return result


def _compatibility(contract: SweepRepairContract, captured: CapturedPools,
                   anchor: A.VerifiedPoolAnchors) -> dict:
    unit, arm, seed = contract.unit, contract.arm, contract.seed
    repair = _repair_arrays(captured, unit, arm, seed)
    baseline = A._validated_arrays(anchor.captured, unit=unit, seed=seed, stage=_GENERATION_STAGE)
    inventory = {}
    for pool in POOL_PURPOSES:
        a, b = repair[pool], baseline[pool]
        n = len(b["action"])
        for field in ("state", "next_state", "action", "episode", "step"):
            if a[field][:n].tobytes() != b[field].tobytes():
                raise ValueError(f"{pool}.{field} differs from the exact baseline trajectory/prefix")
        for field, future in (("obs", False), ("next_obs", True)):
            # Feature restoration may reorder slots. Compare full latent state
            # and then re-encode through the original baseline encoder instead
            # of projecting restored arrays by dropping feature columns.
            value = (A.reencode_anchors(getattr(captured, pool)[:n], unit, next_state=future)
                     if arm == "feature_repair" else a[field][:n])
            if value.dtype != b[field].dtype or value.shape != b[field].shape or value.tobytes() != b[field].tobytes():
                raise ValueError(f"{pool}.{field} differs from exact baseline encoding/prefix")
        inventory[pool] = {
            "baseline_count": n, "repair_count": len(a["action"]),
            "baseline_arrays": {field: _array_digest(value) for field, value in b.items()},
            "repair_arrays": {field: _array_digest(value) for field, value in a.items()},
        }
    if _json(A._scale(captured.pools).as_row()) != _json(anchor.scale.as_row()):
        raise ValueError("repair full movement normalisation differs from baseline anchor")
    return {
        "compatibility_schema_version": COMPATIBILITY_SCHEMA_VERSION,
        "procedure": PAIRING_PROCEDURE, "contract_sha256": contract.contract_sha256,
        "pool_anchor_sha256": anchor.anchor_sha256, "rule": _rule(arm),
        "normalisation": anchor.scale.as_row(), "pools": inventory,
    }


def validate_pool_compatibility(
    contract: SweepRepairContract, captured: CapturedPools, *, baseline_source: str | Path,
    expected_baseline_commit: str, expected_baseline_execution_digest: str,
) -> dict:
    """Reopen source evidence and recompute every exact comparison before use."""
    anchor = _validate(contract, baseline_source=baseline_source,
                       expected_baseline_commit=expected_baseline_commit,
                       expected_baseline_execution_digest=expected_baseline_execution_digest)
    return _compatibility(contract, captured, anchor)


def validate_anchored_repair_pools(
    result: AnchoredRepairPools, *, baseline_source: str | Path,
    expected_baseline_commit: str, expected_baseline_execution_digest: str,
) -> AnchoredRepairPools:
    """Consumer boundary also rejects a mutated scale or compatibility receipt."""
    if type(result) is not AnchoredRepairPools or type(result.scale) is not NormalisationScale:
        raise ValueError("an exact AnchoredRepairPools with NormalisationScale is required")
    receipt = validate_pool_compatibility(
        result.contract, result.captured, baseline_source=baseline_source,
        expected_baseline_commit=expected_baseline_commit,
        expected_baseline_execution_digest=expected_baseline_execution_digest,
    )
    if (type(result.compatibility_json) is not bytes or result.compatibility_json != _json(receipt)
            or _json(result.scale.as_row()) != _json(receipt["normalisation"])):
        raise ValueError("repair compatibility receipt or normalisation differs from revalidated pools")
    return result


def collect_anchored_repair_pools(
    contract: SweepRepairContract, *, baseline_source: str | Path,
    expected_baseline_commit: str, expected_baseline_execution_digest: str,
) -> AnchoredRepairPools:
    """Collect exactly the registered repaired pools; never train or mint a run.

    No policy, stage, size, normalization, generation version or RNG override is
    accepted. A future physical runner must retain the separate obligation and
    generation stages and perform a final validation of these objects.
    """
    expected = dict(baseline_source=baseline_source, expected_baseline_commit=expected_baseline_commit,
                    expected_baseline_execution_digest=expected_baseline_execution_digest)
    _validate(contract, **expected)  # Before any data generation.
    collected = {pool: collect_with_anchors(
        contract.unit, stage=_GENERATION_STAGE, seed=contract.seed, arm=contract.arm, pool=pool,
    ) for pool in POOL_PURPOSES}
    captured = CapturedPools(
        Pools(**{pool: value.dataset for pool, value in collected.items()}),
        **{pool: value.transitions for pool, value in collected.items()},
    )
    anchor = _validate(contract, **expected)  # Reopen again after collection.
    receipt = _compatibility(contract, captured, anchor)
    # Ordinary collector arrays stay writable for the existing torch conversion
    # path (torch cannot safely wrap a read-only numpy buffer). Consumers MUST
    # revalidate exact objects and the scale/receipt just before training: neither
    # a frozen dataclass nor an ndarray flag is an evidence trust boundary.
    return AnchoredRepairPools(contract, captured, anchor.scale, _json(receipt))
