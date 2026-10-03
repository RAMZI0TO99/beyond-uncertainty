"""Evidence-bound, three-seed labels for ordinary canonical conditions.

The design in ``docs/sweep_pairing_and_ordinary_labels_design.md`` separates
285 ordinary exp3 obligations from the fifteen exact twenty-seed validation
conditions. This first version implements ONLY the 60 ordinary canonical
conditions. All 225 sweep conditions fail positively: legacy sweep repairs
cannot supply the separately verified, baseline-anchored paired schema.

Source paths, expected execution commits and execution digests are independent
inputs on BOTH creation and reload. Never manufacture those pins by reading the
label being verified. All nine sidecars are reopened, including when reloading
a label. Metadata alone, caller-owned arrays and pending work create no label.

The twenty-seed public API and its stage guard are not called or modified.
Private assembly here follows the same paired-transition/equal-seed analysis,
after independently verifying the actual canonical baseline role and each
exp3 repair role. No role is relabelled as repair_validation or pilot. Pure
serialization helpers from label_evidence are reused, not its policy boundary.
This is not the final label-to-critic bridge (C-007).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from os import PathLike
from pathlib import Path
from typing import Any

import numpy as np

from .. import constants as K
from ..config import Arm, Config, UnitSpec, seeds_for
from ..durable import DurabilityError, read_json
from ..models.uncertainty import NormalisationScale
from ..models.world_model import MOVEMENT_ACTIONS
from ..stats.acceptance import acceptance_test
from ..streams import DATA_PURPOSES, confirmatory_seeds, group_of, stream_key
from . import label_evidence as L
from .enumerate_units import design_units, repair_obligations, stage_of
from .fit_evidence import (
    VerifiedFitEvidence,
    _validate_expected_git_commit,
    load_fit_evidence,
    registered_fit_spec,
)
from .labels import LabelAssignment
from .repair import ArmEvaluation


# Separate schema/file: this must never be accepted by the twenty-seed reader.
ORDINARY_LABEL_EVIDENCE_SCHEMA_VERSION = 1
ORDINARY_LABEL_EVIDENCE_FILE = "ordinary_label_evidence.json"
ORDINARY_STAGE = "exp3_repairs"
_CANONICAL_STAGES = ("exp1", "exp2a", "exp2b")


class OrdinaryLabelPending(ValueError):
    """Required work is absent; no observed label or exclusion is available."""


@dataclass(frozen=True)
class OrdinaryFitSource:
    """One path with independently expected launch commit and execution digest.

    Pins must originate from the verified execution/reuse inventory, not from
    untrusted label metadata. Per-source pins allow old baselines and new
    repairs to truthfully retain their different execution commits.
    """

    path: str | PathLike[str]
    expected_git_commit: str
    expected_execution_digest: str


@dataclass(frozen=True)
class OrdinaryRepairCondition:
    """Three pinned sources for one seed; seed/arms are derived, not supplied."""

    baseline: OrdinaryFitSource
    data_repair: OrdinaryFitSource
    model_repair: OrdinaryFitSource


@dataclass(frozen=True)
class _Projected:
    source: OrdinaryFitSource
    verified: VerifiedFitEvidence
    evaluation: ArmEvaluation
    action: np.ndarray
    pool_digest: str


@dataclass(frozen=True)
class _Condition:
    seed: int
    baseline: _Projected
    data_repair: _Projected
    model_repair: _Projected


def ordinary_units() -> tuple[UnitSpec, ...]:
    """Derive all 285 ordinary units from the registered design, not its pool.

    Eligibility is not execution support: sweep units are listed here but are
    refused by both label entry points until the paired schema is verified.
    """

    units: dict[str, UnitSpec] = {}
    for obligation in repair_obligations(design_units()):
        if obligation.stage == ORDINARY_STAGE:
            units.setdefault(Config(unit=obligation.unit).unit_id, obligation.unit)
    return tuple(units.values())


def canonical_ordinary_units() -> tuple[UnitSpec, ...]:
    """The supported 60, without silently downgrading twenty-seed units."""

    return tuple(unit for unit in ordinary_units() if stage_of(unit) in _CANONICAL_STAGES)


def _registered_unit(unit: object) -> tuple[str, str]:
    if type(unit) is not UnitSpec or unit not in ordinary_units():
        raise ValueError(
            "unit must be an exact registered ordinary exp3_repairs UnitSpec; "
            "twenty-seed validation units and units outside the design are refused"
        )
    baseline_stage = stage_of(unit)
    if baseline_stage not in _CANONICAL_STAGES:
        raise ValueError(
            "ordinary sweep labels are blocked until a separately verified "
            "baseline-anchored paired repair evidence schema exists; legacy "
            "exp3_repairs evidence cannot satisfy this boundary (D-155)"
        )
    model_arms = {
        obligation.arm for obligation in repair_obligations(design_units())
        if obligation.unit == unit and obligation.stage == ORDINARY_STAGE
        and obligation.arm != "data_repair"
    }
    if len(model_arms) != 1:
        raise ValueError("ordinary unit does not register exactly one model repair")
    # An actual stream comparison, never a stage override or pairing bypass.
    if any(
        stream_key(unit, baseline_stage, purpose) != stream_key(unit, ORDINARY_STAGE, purpose)
        for purpose in DATA_PURPOSES
    ):
        raise ValueError("canonical baseline and ordinary repairs have mismatched data streams")
    return baseline_stage, next(iter(model_arms))


@lru_cache(maxsize=None)
def _spec(unit: UnitSpec, arm: str, seed: int):
    # Registry only: source bytes and verified source objects are never cached.
    return registered_fit_spec(unit, arm=arm, seed=seed)


def _source_path(source: object) -> Path:
    if type(source) is not OrdinaryFitSource:
        raise ValueError("every source must be an exact OrdinaryFitSource with independent pins")
    if not isinstance(source.path, (str, PathLike)) or not str(source.path).strip():
        raise ValueError("source path must be a nonblank filesystem path, never in-memory evidence")
    _validate_expected_git_commit(source.expected_git_commit)
    L._require_digest(source.expected_execution_digest, field="expected_execution_digest")
    return Path(source.path).resolve()


def _load_projected(
    source: OrdinaryFitSource, *, unit: UnitSpec, arm: str, role: str,
) -> _Projected:
    path = _source_path(source)
    if not path.exists():
        raise OrdinaryLabelPending(f"required source {path} is absent; label is pending, not observed")
    try:
        verified = load_fit_evidence(path, expected_git_commit=source.expected_git_commit)
    except (OSError, ValueError) as exc:
        raise ValueError(f"blocked ordinary label: invalid persisted source at {path}: {exc}") from exc
    if type(verified) is not VerifiedFitEvidence:
        raise ValueError("source loader must return exact VerifiedFitEvidence")
    if Path(verified.fit_dir).resolve() != path:
        raise ValueError("source loader returned a substituted fit directory")
    if verified.execution_digest != source.expected_execution_digest:
        raise ValueError("source execution digest differs from independently expected execution digest")
    if verified.unit != unit or verified.arm != arm:
        raise ValueError("source unit/arm does not match the independently requested ordinary condition")
    required = confirmatory_seeds(seeds_for(ORDINARY_STAGE))
    if type(verified.seed) is not int or verified.seed not in required:
        raise ValueError(f"source seed must be one of exact ordinary seeds {required}, not {verified.seed!r}")
    spec = _spec(unit, arm, verified.seed)
    for field in ("roles", "execution_stage", "unit_id", "config_id", "fit_id", "execution_run_id"):
        if getattr(verified, field) != getattr(spec, field):
            raise ValueError(f"source {field} does not match the registered physical fit")
    if role not in verified.roles:
        raise ValueError(f"source has no registered {role!r} role; no fabricated projections")
    evaluation = verified.for_role(role)
    if type(evaluation) is not ArmEvaluation:
        raise ValueError("source role projection must return exact ArmEvaluation")
    expected = {
        "arm": arm, "seed": verified.seed, "stage": role,
        "config_id": spec.config_id, "run_id": spec.run_id_for(role),
        "n_train": Arm(arm).resolve(unit).n_transitions,
        "ensemble_size": K.DEFAULT_ENSEMBLE_SIZE if arm == "baseline" else 1,
    }
    for field, value in expected.items():
        observed = getattr(evaluation, field)
        if type(observed) is not type(value) or observed != value:
            raise ValueError(f"projected source {field} does not match its registered role/procedure")
    error = np.asarray(evaluation.error)
    if error.ndim != 1 or not len(error) or error.dtype.kind not in "fiu":
        raise ValueError("source error must be a nonempty numeric vector")
    if not np.all(np.isfinite(error)) or np.any(error < 0):
        raise ValueError("source errors must be finite and nonnegative")
    if type(evaluation.scale) is not NormalisationScale:
        raise ValueError("source must carry exact NormalisationScale")
    action, pool_digest = L._verified_pool_binding(verified)
    movement = np.isin(action, np.asarray(MOVEMENT_ACTIONS))
    expected_episode = np.repeat(np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH)[movement]
    expected_step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)[movement]
    if len(error) != int(movement.sum()):
        raise ValueError("source error rows do not cover its exact full movement inventory")
    for field, inventory in (("episode", expected_episode), ("step", expected_step)):
        array = np.asarray(getattr(evaluation, field))
        if array.dtype.kind not in "iu" or not np.array_equal(array, inventory):
            raise ValueError(f"source {field} inventory does not equal its ordered movement inventory")
    return _Projected(source, verified, evaluation, action, pool_digest)


def _validate_condition(
    condition: OrdinaryRepairCondition, *, unit: UnitSpec, baseline_stage: str, model_arm: str,
) -> _Condition:
    base = _load_projected(condition.baseline, unit=unit, arm="baseline", role=baseline_stage)
    data = _load_projected(condition.data_repair, unit=unit, arm="data_repair", role=ORDINARY_STAGE)
    model = _load_projected(condition.model_repair, unit=unit, arm=model_arm, role=ORDINARY_STAGE)
    seed = base.verified.seed
    if data.verified.seed != seed or model.verified.seed != seed:
        raise ValueError("each ordinary condition must contain the same seed on all three arms")
    for projected in (data, model):
        for name, observed, expected in (
            ("action", projected.action, base.action),
            ("episode", projected.evaluation.episode, base.evaluation.episode),
            ("step", projected.evaluation.step, base.evaluation.step),
        ):
            if not np.array_equal(observed, expected):
                raise ValueError(f"cross-arm {name} inventories do not match the exact baseline pool")
        if L._canonical_json(projected.evaluation.scale.as_row()) != L._canonical_json(base.evaluation.scale.as_row()):
            raise ValueError("repair does not attest the baseline's full-pool normalisation scale")
    if data.pool_digest != base.pool_digest:
        raise ValueError("data repair evaluation pool digest does not match baseline")
    if model_arm == "feature_repair":
        if model.pool_digest == base.pool_digest:
            raise ValueError("feature repair must change the encoded evaluation pool digest")
    elif model.pool_digest != base.pool_digest:
        raise ValueError("capacity repair evaluation pool digest does not match baseline")
    return _Condition(seed, base, data, model)


def _acceptance_arrays(
    conditions: Sequence[_Condition], masks: dict[int, np.ndarray], *, arm: str,
) -> dict[str, np.ndarray]:
    """Private assembly AFTER source/role/pairing checks, never a public bypass.

    The old repair.acceptance_inputs correctly rejects these real, mixed
    canonical/exp3 stages. Do not forge a common stage or borrow its twenty-seed
    role to get past that guard. Pass the verified paired rows directly to the
    unchanged acceptance_test, which equally weights the three seed means and
    uses two degrees of freedom. No free masks are exposed to callers.
    """

    columns: dict[str, list[np.ndarray]] = {
        name: [] for name in ("errors", "repair", "seed", "episode", "transition")
    }
    for item in conditions:
        mask = masks[item.seed]
        for projected, flag in ((item.baseline, 0), (getattr(item, arm), 1)):
            evaluation = projected.evaluation
            columns["errors"].append(evaluation.error[mask])
            columns["repair"].append(np.full(int(mask.sum()), flag))
            columns["seed"].append(np.full(int(mask.sum()), item.seed))
            columns["episode"].append(evaluation.episode[mask])
            columns["transition"].append(evaluation.step[mask])
    return {name: np.concatenate(arrays) for name, arrays in columns.items()}


def _identity(projected: _Projected, *, label_path: Path) -> dict[str, Any]:
    fit, evaluation = projected.verified, projected.evaluation
    return {
        "arm": fit.arm, "role": evaluation.stage, "run_id": evaluation.run_id,
        "config_id": fit.config_id, "fit_id": fit.fit_id,
        "execution_stage": fit.execution_stage, "execution_run_id": fit.execution_run_id,
        "fit_roles": list(fit.roles), "fit_evidence_digest": fit.execution_digest,
        "expected_git_commit": projected.source.expected_git_commit,
        "fit_evidence_path": L._portable_fit_path(Path(fit.fit_dir), label_path=label_path),
    }


def _derive(
    conditions: Sequence[OrdinaryRepairCondition], *, unit: UnitSpec, label_path: Path,
) -> dict[str, Any]:
    baseline_stage, model_arm = _registered_unit(unit)
    required = confirmatory_seeds(seeds_for(ORDINARY_STAGE))
    if isinstance(conditions, (str, bytes)) or not isinstance(conditions, Sequence):
        raise ValueError("conditions must be a complete sequence of OrdinaryRepairCondition")
    if len(conditions) < len(required):
        raise OrdinaryLabelPending(f"exactly {len(required)} conditions are required; missing work is pending")
    if len(conditions) != len(required):
        raise ValueError(f"exactly {len(required)} conditions required; extra conditions are refused")
    paths: set[Path] = set()
    for condition in conditions:
        if type(condition) is not OrdinaryRepairCondition:
            raise ValueError("every condition must be exact OrdinaryRepairCondition")
        for source in (condition.baseline, condition.data_repair, condition.model_repair):
            path = _source_path(source)
            L._portable_fit_path(path, label_path=label_path)
            if path in paths:
                raise ValueError("duplicate physical source path in ordinary label inputs")
            paths.add(path)
    validated = [
        _validate_condition(item, unit=unit, baseline_stage=baseline_stage, model_arm=model_arm)
        for item in conditions
    ]
    validated.sort(key=lambda item: item.seed)
    if tuple(item.seed for item in validated) != tuple(required):
        raise ValueError(f"ordinary conditions must contain exact seeds {required}; duplicates/missing refused")
    fit_ids = [
        fit.verified.fit_id for item in validated
        for fit in (item.baseline, item.data_repair, item.model_repair)
    ]
    if len(set(fit_ids)) != 3 * len(required):
        raise ValueError("duplicate physical fit_id in ordinary label inputs")
    masks: dict[int, np.ndarray] = {}
    for item in validated:
        mask = np.asarray(item.baseline.evaluation.error) > K.FAILURE_THRESHOLD
        if not mask.any():
            raise ValueError(f"blocked ordinary label: empty strict failure set at seed {item.seed}")
        masks[item.seed] = mask
    results = {
        arm: acceptance_test(**_acceptance_arrays(validated, masks, arm=arm))
        for arm in ("data_repair", "model_repair")
    }
    assignment = LabelAssignment(
        unit_id=Config(unit=unit).unit_id,
        comparison_group_id=group_of(unit, baseline_stage),
        intended_class="estimation" if unit.family == "estimation" else "hypothesis_class",
        data_repair_works=results["data_repair"].passed,
        model_repair_works=results["model_repair"].passed,
    )
    payload = {
        "ordinary_label_evidence_schema_version": ORDINARY_LABEL_EVIDENCE_SCHEMA_VERSION,
        "procedure": "ordinary_canonical_three_seed_v1",
        "unit_id": assignment.unit_id, "unit": L._unit_row(unit), "family": unit.family,
        "comparison_group_id": assignment.comparison_group_id,
        "intended_class": assignment.intended_class, "stage": ORDINARY_STAGE,
        "baseline_stage": baseline_stage, "seeds": list(required), "model_repair_arm": model_arm,
        "failure_definition": {
            "metric": "baseline.normalised_movement_error", "operator": ">",
            "threshold": K.FAILURE_THRESHOLD,
        },
        "failure_masks": [
            L._mask_row(item.seed, item.baseline.evaluation, masks[item.seed]) for item in validated
        ],
        "runs": [
            {"seed": item.seed, **{
                arm: _identity(getattr(item, arm), label_path=label_path)
                for arm in ("baseline", "data_repair", "model_repair")
            }} for item in validated
        ],
        "acceptance": {arm: L._acceptance_row(result) for arm, result in results.items()},
        "label": {
            "unit_id": assignment.unit_id, "comparison_group_id": assignment.comparison_group_id,
            "intended_class": assignment.intended_class,
            "data_repair_works": assignment.data_repair_works,
            "model_repair_works": assignment.model_repair_works,
            "observed_label": assignment.observed_label,
        },
    }
    return {**payload, "record_digest": L._digest(payload)}


def build_ordinary_label_evidence(
    conditions: Sequence[OrdinaryRepairCondition], *, unit: UnitSpec, path: str | Path,
) -> dict[str, Any]:
    """Verify all nine pinned sources and immutably publish one complete label.

    Absent work raises OrdinaryLabelPending; invalid/partial evidence and empty
    failure sets raise ValueError. Neither writes a placeholder/observed label.
    All source paths must be descendants of the label directory for portability.
    """

    label_path = Path(path).resolve()
    record = _derive(conditions, unit=unit, label_path=label_path)
    L._write_json_exclusive(label_path, record)
    return record


def load_ordinary_label_evidence(
    path: str | Path, *, unit: UnitSpec, conditions: Sequence[OrdinaryRepairCondition],
) -> dict[str, Any]:
    """Reopen all nine independently pinned sources and exactly rederive.

    A record cannot choose its own source paths, expected commits or digests.
    Pass the independently retained execution/reuse inventory, not fields read
    from the label. Canonical JSON comparison also distinguishes bool/int/float
    substitutions which ordinary Python dictionary equality would conflate.
    """

    _registered_unit(unit)  # Sweep/validation refusal even before label IO.
    label_path = Path(path).resolve()
    try:
        record = read_json(label_path)
    except DurabilityError as exc:
        raise ValueError(f"cannot load complete ordinary label evidence: {exc}") from exc
    rederived = _derive(conditions, unit=unit, label_path=label_path)
    if L._canonical_json(record) != L._canonical_json(rederived):
        raise ValueError(
            "ordinary label metadata does not exactly match all nine independently "
            "pinned, reverified sources and the rederived masks/statistics/label"
        )
    return rederived
