"""Three-seed sweep labels from legacy baselines and NEW paired repair evidence.

Only the 225 registered sweep-only ordinary conditions enter this schema.
Canonical ordinary and twenty-seed label APIs are intentionally unchanged.
Every creation/reload requires an external unit and nine independently pinned
sources. The label never selects its own evidence, baseline, commits or digests.

Each paired reader receives the very same condition baseline and its independent
commit/execution digest. The paired reader verifies the complete anchor, actual
input compatibility, predictions and qualified physical execution. This
consumer additionally pins its returned execution digest, contract identities,
full movement inventories and ACTUAL diagnostic scale values. No scale is
rounded, recomputed on a failure subset or substituted with a new tensor.

Missing work is pending, not an observed label. Invalid evidence or an empty
strict baseline failure set blocks label creation. The unchanged acceptance
test and Table-2 mapping operate on verified paired transitions at three seeds.
This evidence boundary is not the final label-to-critic bridge (C-007).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from os import PathLike
from pathlib import Path
from typing import Any

import numpy as np

from .. import constants as K
from ..config import Arm, Config, UnitSpec, seeds_for
from ..durable import DurabilityError, read_json
from ..env.gridworld import N_ACTIONS
from ..models.uncertainty import NormalisationScale
from ..models.world_model import MOVEMENT_ACTIONS
from ..stats.acceptance import acceptance_test
from ..streams import confirmatory_seeds, group_of
from . import fit_evidence as F
from . import label_evidence as L
from . import paired_repair_evidence as E
from . import repair_pairing as RP
from .enumerate_units import design_units, repair_obligations, stage_of
from .labels import LabelAssignment


ORDINARY_SWEEP_LABEL_EVIDENCE_SCHEMA_VERSION = 1
ORDINARY_SWEEP_LABEL_EVIDENCE_FILE = "ordinary_sweep_label_evidence.json"
_BASELINE_STAGE = "config_sweep"
_REPAIR_STAGE = "exp3_repairs"


class SweepLabelPending(ValueError):
    """A required source is absent; no observed label or exclusion exists."""


@dataclass(frozen=True)
class SweepBaselineSource:
    """Original legacy baseline with independently retained execution pins."""

    path: str | PathLike[str]
    expected_git_commit: str
    expected_execution_digest: str


@dataclass(frozen=True)
class PairedRepairSource:
    """Qualified paired execution, never interchangeable with a legacy source."""

    path: str | PathLike[str]
    expected_git_commit: str
    expected_execution_digest: str


@dataclass(frozen=True)
class SweepRepairCondition:
    """One baseline and its two paired repairs; seed/arms are source-derived."""

    baseline: SweepBaselineSource
    data_repair: PairedRepairSource
    model_repair: PairedRepairSource


@dataclass(frozen=True)
class _Arrays:
    error: np.ndarray
    action: np.ndarray
    episode: np.ndarray
    step: np.ndarray
    normalisation: dict[str, Any]


@dataclass(frozen=True)
class _Baseline:
    source: SweepBaselineSource
    verified: F.VerifiedFitEvidence
    arrays: _Arrays


@dataclass(frozen=True)
class _Paired:
    source: PairedRepairSource
    verified: E.VerifiedPairedRepair
    arrays: _Arrays


@dataclass(frozen=True)
class _Condition:
    seed: int
    baseline: _Baseline
    data_repair: _Paired
    model_repair: _Paired


@lru_cache(maxsize=1)
def sweep_ordinary_units() -> tuple[UnitSpec, ...]:
    """Exactly the 225 sweep ordinary units from the design, not its larger pool."""

    # Immutable registry metadata only; never cache evidence or caller pins.
    units: dict[str, UnitSpec] = {}
    for obligation in repair_obligations(design_units()):
        if obligation.stage == _REPAIR_STAGE and stage_of(obligation.unit) == _BASELINE_STAGE:
            units.setdefault(Config(unit=obligation.unit).unit_id, obligation.unit)
    return tuple(units.values())


def _registered_unit(unit: object) -> str:
    if type(unit) is not UnitSpec or unit not in sweep_ordinary_units():
        raise ValueError("unit must be an exact registered sweep-only ordinary unit; canonical/validation units are refused")
    arms = {
        row.arm for row in repair_obligations(design_units())
        if row.unit == unit and row.stage == _REPAIR_STAGE and row.arm != "data_repair"
    }
    if len(arms) != 1:
        raise ValueError("sweep condition must register exactly one assigned model repair")
    return next(iter(arms))


def _seeds() -> tuple[int, ...]:
    seeds = tuple(confirmatory_seeds(seeds_for(_REPAIR_STAGE)))
    if seeds != (1000, 1001, 1002):
        raise ValueError("sweep label schema v1 requires exactly registered seeds 1000..1002")
    return seeds


@lru_cache(maxsize=None)
def _baseline_spec(unit: UnitSpec, seed: int):
    return F.registered_fit_spec(unit, arm="baseline", seed=seed)


def _source_path(source: object, expected_type: type) -> Path:
    if type(source) is not expected_type:
        raise ValueError(f"source must be exact {expected_type.__name__}; legacy and paired source kinds cannot be exchanged")
    F._validate_expected_git_commit(source.expected_git_commit)
    L._require_digest(source.expected_execution_digest, field="expected_execution_digest")
    if not isinstance(source.path, (str, PathLike)) or not str(source.path).strip():
        raise ValueError("source path must be a nonblank filesystem path, not in-memory evidence")
    try:
        return Path(source.path).resolve()
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("invalid source filesystem path") from exc


def _same(observed: object, expected: object, *, what: str) -> None:
    if L._canonical_json(observed) != L._canonical_json(expected):
        raise ValueError(f"{what} differs from independently derived sweep evidence")


def _arrays(verified: F.VerifiedFitEvidence | E.VerifiedPairedRepair) -> _Arrays:
    diagnostics = verified.diagnostics
    if not isinstance(diagnostics, Mapping):
        raise ValueError("source must expose verified diagnostic arrays")
    required = ("error", "evaluation_action", "episode", "step", "scale",
                "scale_n_reference", "scale_domain", "scale_source")
    if any(type(diagnostics.get(name)) is not np.ndarray for name in required):
        raise ValueError("source lacks exact required diagnostic arrays")
    copies = {name: np.array(diagnostics[name], copy=True) for name in required}
    error, action, episode, step = (copies[name] for name in required[:4])
    if (error.ndim != 1 or not len(error) or error.dtype.kind not in "fiu"
            or not np.isfinite(error).all() or np.any(error < 0)):
        raise ValueError("source error must be a finite nonnegative nonempty numeric vector")
    n = K.EVALUATION_EPISODES * K.EPISODE_LENGTH
    if (action.shape != (n,) or action.dtype.kind not in "iu"
            or np.any((action < 0) | (action >= N_ACTIONS))):
        raise ValueError("source must contain the exact valid full evaluation action inventory")
    movement = np.isin(action, MOVEMENT_ACTIONS)
    expected_episode = np.repeat(np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH)[movement]
    expected_step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)[movement]
    if len(error) != int(movement.sum()):
        raise ValueError("source errors do not cover its exact full movement inventory")
    for name, value, expected in (("episode", episode, expected_episode), ("step", step, expected_step)):
        if value.dtype.kind not in "iu" or not np.array_equal(value, expected):
            raise ValueError(f"source {name} is not the ordered full movement inventory")
    for name, value in (("error", error), ("episode", episode), ("step", step)):
        if not np.array_equal(value, getattr(verified, name)):
            raise ValueError(f"source exposed {name} disagrees with its diagnostic bytes")
    vector = copies["scale"]
    if (vector.dtype != np.dtype("float64") or vector.shape != (2,)
            or not np.isfinite(vector).all() or np.any(vector <= 0)):
        raise ValueError("source actual scale array must be a finite positive float64 two-vector")
    reference = copies["scale_n_reference"]
    if reference.shape != () or reference.dtype.kind not in "iu" or reference.item() != len(error):
        raise ValueError("source scale must attest the entire movement pool before failure masking")
    for name in ("scale_domain", "scale_source"):
        if copies[name].shape != () or copies[name].dtype.kind != "U":
            raise ValueError("source scale provenance must be scalar string arrays")
    normalisation = {
        "scale": vector.tolist(), "scale_n_reference": int(reference.item()),
        "scale_domain": copies["scale_domain"].item(), "scale_source": copies["scale_source"].item(),
    }
    if (normalisation["scale_domain"] != K.NORMALISATION_SCALE_DOMAIN
            or normalisation["scale_source"] != K.NORMALISATION_SCALE_SOURCE):
        raise ValueError("source scale provenance is not the registered full-pool movement scale")
    if type(verified.scale) is not NormalisationScale:
        raise ValueError("source lacks exact NormalisationScale")
    # Compare before constructing/rounding any tensor: even a change smaller
    # than float32 precision in persisted float64 scale bytes must fail closed.
    _same(verified.scale.as_row(), normalisation, what="actual diagnostic scale and exposed scale")
    for value in (error, action, episode, step):
        value.flags.writeable = False
    return _Arrays(error, action, episode, step, normalisation)


def _load_baseline(source: SweepBaselineSource, *, unit: UnitSpec) -> _Baseline:
    path = _source_path(source, SweepBaselineSource)
    if not path.exists():
        raise SweepLabelPending(f"baseline {path} is absent; label remains pending, not observed")
    if (path / E.PAIRED_FIT_FILE).exists():
        raise ValueError("paired evidence cannot supply a legacy sweep baseline")
    try:
        verified = F.load_fit_evidence(path, expected_git_commit=source.expected_git_commit)
    except (OSError, ValueError) as exc:
        raise ValueError(f"blocked sweep label: invalid baseline at {path}: {exc}") from exc
    if type(verified) is not F.VerifiedFitEvidence or Path(verified.fit_dir).resolve() != path:
        raise ValueError("baseline loader returned wrong type or substituted source directory")
    if verified.unit != unit or verified.arm != "baseline":
        raise ValueError("baseline unit/arm differs from requested sweep condition")
    if type(verified.seed) is not int or verified.seed not in _seeds():
        raise ValueError("baseline must carry an exact seed from 1000..1002")
    spec = _baseline_spec(unit, verified.seed)
    for field in ("unit_id", "config_id", "fit_id", "execution_run_id", "execution_stage", "roles"):
        observed, expected = getattr(verified, field), getattr(spec, field)
        if type(observed) is not type(expected) or observed != expected:
            raise ValueError(f"baseline {field} differs from registered config_sweep execution")
    if verified.roles != (_BASELINE_STAGE,) or verified.execution_stage != _BASELINE_STAGE:
        raise ValueError("only the original config_sweep baseline role is allowed")
    if verified.execution_digest != source.expected_execution_digest:
        raise ValueError("baseline execution digest differs from independently expected digest")
    for field, expected in (("n_train", unit.n_transitions), ("ensemble_size", K.DEFAULT_ENSEMBLE_SIZE)):
        if type(getattr(verified, field)) is not int or getattr(verified, field) != expected:
            raise ValueError(f"baseline {field} differs from registered procedure")
    return _Baseline(source, verified, _arrays(verified))


def _load_paired(source: PairedRepairSource, *, unit: UnitSpec, arm: str, baseline: _Baseline) -> _Paired:
    path = _source_path(source, PairedRepairSource)
    if not path.exists():
        raise SweepLabelPending(f"paired repair {path} is absent; label remains pending, not observed")
    if (path / F.FIT_EVIDENCE_FILE).exists():
        raise ValueError("legacy repairs cannot supply qualified paired evidence")
    seed = baseline.verified.seed
    try:
        verified = E.load_paired_repair_evidence(
            path, unit=unit, arm=arm, seed=seed,
            baseline_source=Path(baseline.source.path).resolve(),
            expected_baseline_commit=baseline.source.expected_git_commit,
            expected_baseline_execution_digest=baseline.source.expected_execution_digest,
            expected_git_commit=source.expected_git_commit,
        )
    except (OSError, ValueError) as exc:
        raise ValueError(f"blocked sweep label: invalid paired repair at {path}: {exc}") from exc
    if type(verified) is not E.VerifiedPairedRepair or Path(verified.fit_dir).resolve() != path:
        raise ValueError("paired loader returned wrong type or substituted source directory")
    if verified.execution_digest != source.expected_execution_digest:
        raise ValueError("paired execution digest differs from independently expected digest")
    spec = RP.registered_sweep_repair_spec(unit, arm=arm, seed=seed)
    physical_fit, physical_run = RP._physical_ids(spec, baseline.source.expected_execution_digest)
    expected = {
        "unit": unit, "arm": arm, "seed": seed, "config_id": spec.config_id,
        "obligation_fit_id": spec.fit_id, "obligation_run_id": spec.execution_run_id,
        "physical_fit_id": physical_fit, "physical_run_id": physical_run,
        "n_train": Arm(arm).resolve(unit).n_transitions,
    }
    for field, value in expected.items():
        observed = getattr(verified, field)
        if type(observed) is not type(value) or observed != value:
            raise ValueError(f"paired {field} differs from registered qualified execution")
    if type(verified.contract) is not RP.SweepRepairContract:
        raise ValueError("paired source lacks exact SweepRepairContract")
    contract = verified.contract.as_dict()
    contract_expected = {
        "pairing_schema_version": RP.PAIRING_SCHEMA_VERSION, "procedure": RP.PAIRING_PROCEDURE,
        "unit": L._unit_row(unit), "unit_id": Config(unit=unit).unit_id,
        "arm": arm, "seed": seed, "config_id": spec.config_id,
        "generation_stage": _BASELINE_STAGE, "obligation_stage": _REPAIR_STAGE,
        "physical_fit_id": physical_fit, "physical_run_id": physical_run,
        "obligation_fit_id": spec.fit_id, "obligation_run_id": spec.execution_run_id,
        "physical_identity_sha256": RP._physical_digest(spec, baseline.source.expected_execution_digest),
        "baseline_fit_id": baseline.verified.fit_id, "baseline_run_id": baseline.verified.execution_run_id,
        "baseline_commit": baseline.source.expected_git_commit,
        "baseline_execution_digest": baseline.source.expected_execution_digest,
        "normalisation": baseline.arrays.normalisation,
    }
    for field, value in contract_expected.items():
        _same(contract.get(field), value, what=f"paired contract {field}")
    # The strict paired reader already rederives the complete contract, sealed
    # anchor and actual arrays. These cross-source checks prevent accepting a
    # correct paired execution whose baseline is not this label's baseline.
    arrays = _arrays(verified)
    _same(arrays.normalisation, baseline.arrays.normalisation, what="cross-arm actual full-pool scale")
    for field in ("action", "episode", "step"):
        if not np.array_equal(getattr(arrays, field), getattr(baseline.arrays, field)):
            raise ValueError(f"paired {field} inventory differs from this baseline")
    return _Paired(source, verified, arrays)


def _identity(source: _Baseline | _Paired, *, label_path: Path) -> dict[str, Any]:
    fit = source.verified
    common = {
        "arm": fit.arm, "config_id": fit.config_id,
        "execution_digest": fit.execution_digest, "expected_git_commit": source.source.expected_git_commit,
        "fit_evidence_path": L._portable_fit_path(Path(fit.fit_dir), label_path=label_path),
    }
    if type(source) is _Baseline:
        return {
            **common, "source_kind": "legacy_sweep_baseline",
            "physical_fit_id": fit.fit_id, "physical_run_id": fit.execution_run_id,
            "obligation_fit_id": fit.fit_id, "obligation_run_id": fit.execution_run_id,
            "obligation_stage": _BASELINE_STAGE, "execution_stage": _BASELINE_STAGE,
            "fit_roles": list(fit.roles),
        }
    return {
        **common, "source_kind": "baseline_anchored_paired_repair",
        "physical_fit_id": fit.physical_fit_id, "physical_run_id": fit.physical_run_id,
        "obligation_fit_id": fit.obligation_fit_id, "obligation_run_id": fit.obligation_run_id,
        "generation_stage": _BASELINE_STAGE, "obligation_stage": _REPAIR_STAGE,
        "pairing_procedure": RP.PAIRING_PROCEDURE, "pairing_contract_sha256": fit.contract.contract_sha256,
        "baseline_execution_digest": fit.contract.as_dict()["baseline_execution_digest"],
    }


def _acceptance_arrays(conditions: Sequence[_Condition], masks: dict[int, np.ndarray], arm: str) -> dict[str, np.ndarray]:
    """Private assembly of already verified pairs; no legacy stage projection."""
    columns = {name: [] for name in ("errors", "repair", "seed", "episode", "transition")}
    for item in conditions:
        mask = masks[item.seed]
        for source, flag in ((item.baseline, 0), (getattr(item, arm), 1)):
            arrays = source.arrays
            columns["errors"].append(arrays.error[mask])
            columns["repair"].append(np.full(int(mask.sum()), flag))
            columns["seed"].append(np.full(int(mask.sum()), item.seed))
            columns["episode"].append(arrays.episode[mask])
            columns["transition"].append(arrays.step[mask])
    return {name: np.concatenate(values) for name, values in columns.items()}


def _derive(conditions: Sequence[SweepRepairCondition], *, unit: UnitSpec, label_path: Path) -> dict[str, Any]:
    model_arm, required = _registered_unit(unit), _seeds()
    if isinstance(conditions, (str, bytes)) or not isinstance(conditions, Sequence):
        raise ValueError("conditions must be a sequence of exact SweepRepairCondition objects")
    if len(conditions) < len(required):
        raise SweepLabelPending("three complete conditions are required; missing work is pending, not observed")
    if len(conditions) != len(required):
        raise ValueError("exactly three sweep conditions required; extra conditions refused")
    paths: set[Path] = set()
    for item in conditions:
        if type(item) is not SweepRepairCondition:
            raise ValueError("every condition must be exact SweepRepairCondition")
        for source, kind in ((item.baseline, SweepBaselineSource), (item.data_repair, PairedRepairSource), (item.model_repair, PairedRepairSource)):
            path = _source_path(source, kind)
            L._portable_fit_path(path, label_path=label_path)
            if path in paths:
                raise ValueError("duplicate physical source directory in sweep label inputs")
            paths.add(path)
    validated = []
    for item in conditions:
        base = _load_baseline(item.baseline, unit=unit)
        data = _load_paired(item.data_repair, unit=unit, arm="data_repair", baseline=base)
        model = _load_paired(item.model_repair, unit=unit, arm=model_arm, baseline=base)
        validated.append(_Condition(base.verified.seed, base, data, model))
    validated.sort(key=lambda item: item.seed)
    if tuple(item.seed for item in validated) != required:
        raise ValueError("sweep conditions must contain exact seeds 1000..1002; duplicates/missing refused")
    physical_ids = [
        identity for item in validated for identity in (
            item.baseline.verified.fit_id, item.data_repair.verified.physical_fit_id,
            item.model_repair.verified.physical_fit_id,
        )
    ]
    if len(set(physical_ids)) != 9:
        raise ValueError("duplicate physical execution identity in sweep label inputs")
    masks = {item.seed: item.baseline.arrays.error > K.FAILURE_THRESHOLD for item in validated}
    if any(not mask.any() for mask in masks.values()):
        raise ValueError("blocked sweep label: empty strict baseline failure set; no observed label")
    results = {arm: acceptance_test(**_acceptance_arrays(validated, masks, arm)) for arm in ("data_repair", "model_repair")}
    assignment = LabelAssignment(
        unit_id=Config(unit=unit).unit_id, comparison_group_id=group_of(unit, _BASELINE_STAGE),
        intended_class="estimation" if unit.family == "estimation" else "hypothesis_class",
        data_repair_works=results["data_repair"].passed, model_repair_works=results["model_repair"].passed,
    )
    payload = {
        "ordinary_sweep_label_evidence_schema_version": ORDINARY_SWEEP_LABEL_EVIDENCE_SCHEMA_VERSION,
        "procedure": "ordinary_sweep_three_seed_v1", "paired_procedure": RP.PAIRING_PROCEDURE,
        "unit_id": assignment.unit_id, "unit": L._unit_row(unit), "family": unit.family,
        "comparison_group_id": assignment.comparison_group_id, "intended_class": assignment.intended_class,
        "stage": _REPAIR_STAGE, "baseline_stage": _BASELINE_STAGE, "seeds": list(required), "model_repair_arm": model_arm,
        "failure_definition": {"metric": "baseline.normalised_movement_error", "operator": ">", "threshold": K.FAILURE_THRESHOLD},
        "failure_masks": [L._mask_row(item.seed, item.baseline.arrays, masks[item.seed]) for item in validated],
        "runs": [{
            "seed": item.seed, "normalisation": item.baseline.arrays.normalisation,
            **{arm: _identity(getattr(item, arm), label_path=label_path) for arm in ("baseline", "data_repair", "model_repair")},
        } for item in validated],
        "acceptance": {arm: L._acceptance_row(result) for arm, result in results.items()},
        "label": {
            "unit_id": assignment.unit_id, "comparison_group_id": assignment.comparison_group_id,
            "intended_class": assignment.intended_class, "data_repair_works": assignment.data_repair_works,
            "model_repair_works": assignment.model_repair_works, "observed_label": assignment.observed_label,
        },
    }
    return {**payload, "record_digest": L._digest(payload)}


def build_ordinary_sweep_label_evidence(conditions: Sequence[SweepRepairCondition], *, unit: UnitSpec, path: str | Path) -> dict[str, Any]:
    """Reopen nine pinned sources and immutably publish a complete sweep label."""
    label_path = Path(path).resolve()
    record = _derive(conditions, unit=unit, label_path=label_path)
    L._write_json_exclusive(label_path, record)
    return record


def load_ordinary_sweep_label_evidence(path: str | Path, *, unit: UnitSpec, conditions: Sequence[SweepRepairCondition]) -> dict[str, Any]:
    """Rederive from external conditions, never artifact-selected evidence/pins."""
    _registered_unit(unit)
    label_path = Path(path).resolve()
    try:
        record = read_json(label_path)
    except DurabilityError as exc:
        raise ValueError(f"cannot load complete sweep label evidence: {exc}") from exc
    derived = _derive(conditions, unit=unit, label_path=label_path)
    _same(record, derived, what="sweep label metadata, masks, sources and statistics")
    return derived
