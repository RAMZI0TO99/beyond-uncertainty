"""Evidence-bound construction of registered repair labels.

The pure mapping in :mod:`bu.experiments.labels` intentionally knows nothing
about where its two booleans came from.  This module is the confirmatory
boundary around that mapping: it accepts exactly the twenty registered sets of
persisted fit evidence, reloads and verifies every sidecar, projects the
pre-registered ``repair_validation`` role, derives
the baseline failure sets with the frozen strict threshold, runs the registered
acceptance analysis separately for the two repairs, and writes one immutable
label-evidence record.

No in-memory ``ConfirmatoryRun`` is a production input.  In particular, the
baseline fit may have physically executed for Experiment 1 while also carrying
the registered repair-validation role: its role projection is consumed here
without copying artifacts or training a second fit.  No masks, verdicts,
labels, seeds, stages, model-repair choices, or intended classes are caller
arguments.  Each is derived from verified bytes or from a frozen registry.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields, replace
from functools import lru_cache
from os import PathLike
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from .. import constants as K
from ..config import Arm, Config, UnitSpec, seeds_for
from ..critic.split import INTENDED_CLASSES
from ..durable import (
    DivergentTargetError,
    DurabilityError,
    atomic_write_json,
    read_json,
)
from ..stats.acceptance import CONFIDENCE, AcceptanceResult, acceptance_test
from ..streams import confirmatory_seeds, group_of
from ..models.uncertainty import NormalisationScale
from .fit_evidence import (
    VerifiedFitEvidence,
    load_fit_evidence,
    registered_fit_spec,
)
from .labels import LabelAssignment, observed_label
from .repair import ArmEvaluation, REPAIR_STAGE, acceptance_inputs


LABEL_EVIDENCE_SCHEMA_VERSION = 3
LABEL_SUMMARY_SCHEMA_VERSION = 1
LABEL_COUNT_SCHEMA_VERSION = 1
LABEL_EVIDENCE_FILE = "label_evidence.json"
LABEL_SUMMARY_FILE = "label_evidence_summary.json"
LABEL_COUNT_FILE = "label_counts.json"

# Registered before real labels existed (DEV-012).  This is a planning
# convention, never an empirical estimate.
REGISTERED_PLANNING_EXCLUSION_RATE = 0.00

_MODEL_REPAIR_ARMS = (
    "feature_repair", "capacity_repair", "capacity_extension_repair",
)
_LABEL_VALUES = (0, 1, "ambiguous", "undiagnosed")
_HEX_DIGEST_LENGTH = 64

_TOP_LEVEL_KEYS = frozenset({
    "label_evidence_schema_version", "unit_id", "unit", "family",
    "comparison_group_id", "intended_class", "stage", "seeds",
    "model_repair_arm", "failure_definition", "failure_masks", "runs",
    "acceptance", "label", "record_digest",
})
_FAILURE_DEFINITION_KEYS = frozenset({"metric", "operator", "threshold"})
_MASK_KEYS = frozenset({
    "seed", "n_transitions", "failure_count", "mask_digest",
    "baseline_error_digest",
})
_RUN_ROW_KEYS = frozenset({"seed", "baseline", "data_repair", "model_repair"})
_RUN_IDENTITY_KEYS = frozenset({
    "arm", "run_id", "config_id", "fit_id", "execution_stage",
    "execution_run_id", "fit_roles", "fit_evidence_digest",
    "fit_evidence_path",
})
_ACCEPTANCE_KEYS = frozenset({
    "effect", "ci_low", "ci_high", "relative_reduction", "passed",
    "reason", "method", "converged", "n_transitions", "n_seeds",
    "n_episodes", "unrepaired_mean", "min_practical_effect", "confidence",
})
_LABEL_KEYS = frozenset({
    "unit_id", "comparison_group_id", "intended_class",
    "data_repair_works", "model_repair_works", "observed_label",
})


FitEvidenceSource = str | PathLike[str] | VerifiedFitEvidence


@dataclass(frozen=True)
class PersistedRepairCondition:
    """Paths to the three physical fits for one registered seed.

    A :class:`VerifiedFitEvidence` may be supplied for convenience, but only
    its ``fit_dir`` is used.  The sidecar is always loaded again at this
    consumer boundary; caller-owned arrays and identity fields are never
    trusted.
    """

    baseline: FitEvidenceSource
    data_repair: FitEvidenceSource
    model_repair: FitEvidenceSource


@dataclass(frozen=True)
class _ProjectedFit:
    verified: VerifiedFitEvidence
    evaluation: ArmEvaluation
    evaluation_action: np.ndarray
    evaluation_pool_digest: str


@dataclass(frozen=True)
class _ValidatedCondition:
    seed: int
    unit: UnitSpec
    baseline: _ProjectedFit
    data_repair: _ProjectedFit
    model_repair: _ProjectedFit
    model_repair_arm: str


@lru_cache(maxsize=None)
def _registered_spec(unit: UnitSpec, arm: str, seed: int):
    """Cache only the immutable execution-plan lookup, never evidence bytes."""
    return registered_fit_spec(unit, arm=arm, seed=seed)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    """Publish strict JSON through the shared crash-safe evidence boundary."""
    try:
        atomic_write_json(Path(path), dict(value))
    except DivergentTargetError as exc:
        raise ValueError(
            f"{path} already exists with different content; refusing to "
            "overwrite immutable label evidence"
        ) from exc


def _exact_int(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise ValueError(
            f"{field} must be an exact integer, got {value!r} "
            f"({type(value).__name__})"
        )
    return value


def _nonblank(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string, got {value!r}")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], *, field: str
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise ValueError(
            f"{field} keys are not the exact schema; "
            f"missing={sorted(set(expected) - actual)}, "
            f"extra={sorted(actual - set(expected))}"
        )


def _unit_row(unit: UnitSpec) -> dict[str, Any]:
    return dict(Config(unit=unit).to_dict()["unit"])


def _unit_from_row(row: object) -> UnitSpec:
    if not isinstance(row, Mapping):
        raise ValueError("unit provenance must be a JSON object")
    plain = dict(row)
    expected = {field.name for field in fields(UnitSpec)}
    if set(plain) != expected:
        raise ValueError(
            "unit provenance keys are not the exact schema; "
            f"missing={sorted(expected - set(plain))}, "
            f"extra={sorted(set(plain) - expected)}"
        )
    if "withheld_features" in plain:
        withheld = plain["withheld_features"]
        if not isinstance(withheld, list):
            raise ValueError("unit.withheld_features must be a JSON list")
        plain["withheld_features"] = tuple(withheld)
    try:
        return UnitSpec(**plain)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid unit provenance: {exc}") from exc


def _intended_class(unit: UnitSpec) -> str:
    return "estimation" if unit.family == "estimation" else "hypothesis_class"


def _source_path(source: object) -> Path:
    if type(source) is VerifiedFitEvidence:
        return Path(source.fit_dir).resolve()
    if isinstance(source, (str, PathLike)):
        return Path(source).resolve()
    raise ValueError(
        "fit source must be a path or an exact VerifiedFitEvidence; got "
        f"{type(source).__name__}. In-memory ConfirmatoryRun objects are not a "
        "production label boundary"
    )


def _load_projected_fit(source: object) -> _ProjectedFit:
    path = _source_path(source)
    try:
        verified = load_fit_evidence(path)
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot verify persisted fit evidence at {path}: {exc}") from exc
    if type(verified) is not VerifiedFitEvidence:
        raise ValueError(
            f"fit loader returned {type(verified).__name__}, not an exact "
            "VerifiedFitEvidence"
        )
    if Path(verified.fit_dir).resolve() != path:
        raise ValueError(
            f"fit loader returned evidence for {verified.fit_dir}, not requested "
            f"directory {path}"
        )
    spec = _registered_spec(verified.unit, verified.arm, verified.seed)
    expected_verified = {
        "roles": spec.roles,
        "execution_stage": spec.execution_stage,
        "unit_id": spec.unit_id,
        "config_id": spec.config_id,
        "fit_id": spec.fit_id,
        "execution_run_id": spec.execution_run_id,
    }
    for field, value in expected_verified.items():
        if getattr(verified, field) != value:
            raise ValueError(
                f"reloaded fit evidence has {field}={getattr(verified, field)!r}, "
                f"but the current registry derives {value!r}"
            )
    _require_digest(verified.execution_digest, field="fit evidence execution_digest")
    if REPAIR_STAGE not in verified.roles:
        raise ValueError(
            f"physical fit {verified.fit_id} carries roles {verified.roles}; it "
            f"cannot be promoted to unregistered role {REPAIR_STAGE!r}"
        )
    # Reconstructs the role run_id from the verified registry.  This is how one
    # Experiment-1 baseline fit discharges repair_validation without retraining.
    evaluation = verified.for_role(REPAIR_STAGE)
    if type(evaluation) is not ArmEvaluation:
        raise ValueError("fit role projection did not return an exact ArmEvaluation")
    expected = {
        "arm": verified.arm,
        "seed": verified.seed,
        "config_id": verified.config_id,
        "run_id": spec.run_id_for(REPAIR_STAGE),
        "stage": REPAIR_STAGE,
        "n_train": verified.n_train,
        "ensemble_size": verified.ensemble_size,
    }
    for field, value in expected.items():
        if getattr(evaluation, field) != value:
            raise ValueError(
                f"projected evaluation for fit {verified.fit_id} has {field}="
                f"{getattr(evaluation, field)!r}; expected {value!r}"
            )
    error = np.asarray(evaluation.error)
    if error.ndim != 1 or not len(error):
        raise ValueError(
            f"evaluation for fit {verified.fit_id!r} must contain a non-empty 1-D error "
            f"array, got shape {error.shape}"
        )
    if not np.all(np.isfinite(error)):
        raise ValueError(f"evaluation for fit {verified.fit_id!r} contains non-finite errors")
    if np.any(error < 0):
        raise ValueError(f"evaluation for fit {verified.fit_id!r} contains negative errors")
    episode = np.asarray(evaluation.episode)
    step = np.asarray(evaluation.step)
    if episode.ndim != 1 or step.ndim != 1 or not (
        len(error) == len(episode) == len(step)
    ):
        raise ValueError(
            f"evaluation for fit {verified.fit_id!r} has error/episode/step shapes "
            f"{error.shape}/{episode.shape}/{step.shape}; transition evidence "
            "must be one-to-one"
        )
    if type(evaluation.scale) is not NormalisationScale:
        raise ValueError(
            f"evaluation for fit {verified.fit_id!r} lacks an exact NormalisationScale; "
            "a repair label must retain its registered units"
        )
    evaluation_action, evaluation_pool_digest = _verified_pool_binding(verified)
    return _ProjectedFit(
        verified=verified,
        evaluation=evaluation,
        evaluation_action=evaluation_action,
        evaluation_pool_digest=evaluation_pool_digest,
    )


def _verified_pool_binding(verified: VerifiedFitEvidence) -> tuple[np.ndarray, str]:
    """Bind the verified action inventory to its arm-specific encoded-pool digest.

    Both values are exposed only after :func:`load_fit_evidence` has independently
    revalidated the sidecar, source documents, and diagnostic artifacts.  This
    consumer still canonicalises a private action copy and validates the digest
    shape before comparing arms.  The digest includes encoded ``obs`` and
    ``next_obs``.  It is therefore equal for data/capacity repairs but must differ
    for a feature repair that restores a withheld input; trajectory pairing is
    checked separately on action, episode, and step inventories.
    """

    action = verified.diagnostics.get("evaluation_action")
    expected_size = K.EVALUATION_EPISODES * K.EPISODE_LENGTH
    if type(action) is not np.ndarray:
        raise ValueError(
            f"fit {verified.fit_id!r} lacks the verified full evaluation_action "
            "artifact"
        )
    if action.ndim != 1 or action.size != expected_size or action.dtype.kind not in "iu":
        raise ValueError(
            f"fit {verified.fit_id!r} evaluation_action must be one integer "
            f"full-grid inventory of exactly {expected_size} actions"
        )
    # Copy the loader-owned immutable bytes into this consumer's canonical form
    # so a synthetic or future loader cannot mutate an inventory after the
    # cross-arm comparison but before acceptance inputs are derived.
    canonical_action = np.array(action, dtype=np.dtype("<i8"), order="C", copy=True)
    canonical_action.flags.writeable = False

    pool_digest = _require_digest(
        verified.evaluation_pool_digest,
        field=f"fit {verified.fit_id!r} evaluation_pool_digest",
    )
    return canonical_action, pool_digest


def load_repair_validation_projection(source: FitEvidenceSource) -> ArmEvaluation:
    """Reload one physical fit and return its registered repair-role projection.

    This narrow boundary is useful when the physical execution stage is another
    obligation (notably Experiment 1).  It performs no fit and writes nothing;
    absence of the registered role fails closed.
    """

    return _load_projected_fit(source).evaluation


def _validate_condition(
    condition: object,
) -> _ValidatedCondition:
    if type(condition) is not PersistedRepairCondition:
        raise ValueError(
            "every item must be an exact PersistedRepairCondition, got "
            f"{type(condition).__name__}"
        )
    base = _load_projected_fit(condition.baseline)
    data = _load_projected_fit(condition.data_repair)
    model = _load_projected_fit(condition.model_repair)
    if base.verified.arm != "baseline":
        raise ValueError(f"baseline source carries arm {base.verified.arm!r}")
    if data.verified.arm != "data_repair":
        raise ValueError(f"data-repair source carries arm {data.verified.arm!r}")
    model_arm = model.verified.arm
    if model_arm not in _MODEL_REPAIR_ARMS:
        raise ValueError(
            f"model-repair source carries arm {model_arm!r}, expected one of "
            f"{_MODEL_REPAIR_ARMS}"
        )
    seed = _exact_int(base.verified.seed, field="condition seed")
    if data.verified.seed != seed or model.verified.seed != seed:
        raise ValueError(
            f"one condition must contain one seed; got baseline={seed}, "
            f"data={data.verified.seed}, model={model.verified.seed}"
        )
    units = (base.verified.unit, data.verified.unit, model.verified.unit)
    if any(unit != units[0] for unit in units[1:]):
        raise ValueError(
            f"seed {seed} arms do not share one configuration provenance"
        )
    if len({base.verified.unit_id, data.verified.unit_id, model.verified.unit_id}) != 1:
        raise ValueError(f"seed {seed} arms do not share one unit_id")
    applicable: list[str] = []
    for arm in _MODEL_REPAIR_ARMS:
        try:
            Arm(arm).resolve(units[0])
        except ValueError:
            continue
        applicable.append(arm)
    if applicable != [model_arm]:
        raise ValueError(
            f"unit exposes model-repair arms {tuple(applicable)}, while persisted "
            f"evidence carries {model_arm!r}; exactly one intervention must be "
            "fixed by construction"
        )

    baseline_scale = base.evaluation.scale
    for name, projected in (("data_repair", data), ("model_repair", model)):
        inventories = (
            (
                "evaluation_action",
                projected.evaluation_action,
                base.evaluation_action,
            ),
            ("episode", projected.evaluation.episode, base.evaluation.episode),
            ("step", projected.evaluation.step, base.evaluation.step),
        )
        for inventory_name, observed, expected in inventories:
            if not np.array_equal(observed, expected):
                raise ValueError(
                    f"seed {seed} {name} evidence does not use the baseline's "
                    f"exact full {inventory_name} inventory; cross-arm label "
                    "comparisons require one shared latent trajectory pool"
                )
        if projected.evaluation.scale.as_row() != baseline_scale.as_row():
            raise ValueError(
                f"seed {seed} {name} evidence does not attest the baseline's exact "
                "full-pool normalisation scale"
            )
    if data.evaluation_pool_digest != base.evaluation_pool_digest:
        raise ValueError(
            f"seed {seed} data_repair evaluation_pool_digest does not equal the "
            "baseline's independently verified encoded-pool digest"
        )
    if model_arm in ("capacity_repair", "capacity_extension_repair"):
        if model.evaluation_pool_digest != base.evaluation_pool_digest:
            raise ValueError(
                f"seed {seed} {model_arm} evaluation_pool_digest does not "
                "equal the baseline's independently verified encoded-pool digest"
            )
    elif model.evaluation_pool_digest == base.evaluation_pool_digest:
        raise ValueError(
            f"seed {seed} feature_repair evaluation_pool_digest unexpectedly "
            "equals the baseline's encoded-pool digest; restoring a withheld "
            "feature must change encoded obs/next_obs while preserving the exact "
            "latent trajectory inventory"
        )
    # The persisted values have been compared. Reuse one object so the existing
    # acceptance boundary can also enforce its object-identity invariant.
    data = replace(data, evaluation=replace(data.evaluation, scale=baseline_scale))
    model = replace(model, evaluation=replace(model.evaluation, scale=baseline_scale))
    return _ValidatedCondition(
        seed=seed,
        unit=units[0],
        baseline=base,
        data_repair=data,
        model_repair=model,
        model_repair_arm=model_arm,
    )


def _mask_row(seed: int, evaluation: ArmEvaluation, mask: np.ndarray) -> dict[str, Any]:
    error = np.asarray(evaluation.error, dtype="<f8")
    episode = np.asarray(evaluation.episode)
    step = np.asarray(evaluation.step)
    evidence = {
        "seed": seed,
        "n_transitions": int(mask.size),
        "selected_indices": np.flatnonzero(mask).astype(int).tolist(),
        "episode": episode.tolist(),
        "step": step.tolist(),
    }
    return {
        "seed": seed,
        "n_transitions": int(mask.size),
        "failure_count": int(mask.sum()),
        "mask_digest": _digest(evidence),
        "baseline_error_digest": hashlib.sha256(error.tobytes()).hexdigest(),
    }


def _acceptance_row(result: AcceptanceResult) -> dict[str, Any]:
    row = result.as_row()
    # A failed-closed interval uses NaN internally. JSON has no portable NaN;
    # null records the absence without converting it to a numerical result.
    return {
        key: (None if isinstance(value, float) and not math.isfinite(value) else value)
        for key, value in row.items()
    }


def _portable_fit_path(fit_dir: Path, *, label_path: Path) -> str:
    """Return one relocatable descendant path from a label to a fit directory."""

    root = label_path.resolve().parent
    source = fit_dir.resolve()
    try:
        relative = source.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"fit evidence {source} is outside label evidence tree {root}; "
            "portable label records may name only descendant fit directories"
        ) from exc
    if not relative.parts:
        raise ValueError("fit evidence directory cannot be the label directory itself")
    return PurePosixPath(*relative.parts).as_posix()


def _resolve_portable_fit_path(value: object, *, label_path: Path) -> Path:
    """Resolve a canonical relative path without permitting traversal."""

    value = _nonblank(value, field="fit_evidence_path")
    if "\\" in value:
        raise ValueError("fit_evidence_path must use portable '/' separators")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in ("", ".", "..") for part in relative.parts)
        or ":" in relative.parts[0]
        or relative.as_posix() != value
    ):
        raise ValueError(
            f"fit_evidence_path {value!r} is not a canonical relative descendant; "
            "absolute paths and traversal are refused"
        )
    root = label_path.resolve().parent
    candidate = root.joinpath(*relative.parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"fit_evidence_path {value!r} escapes the label evidence tree"
        ) from exc
    return candidate


def _run_identity(
    projected: _ProjectedFit, *, label_path: Path
) -> dict[str, Any]:
    verified = projected.verified
    evaluation = projected.evaluation
    return {
        "arm": verified.arm,
        "run_id": evaluation.run_id,
        "config_id": verified.config_id,
        "fit_id": verified.fit_id,
        "execution_stage": verified.execution_stage,
        "execution_run_id": verified.execution_run_id,
        "fit_roles": list(verified.roles),
        "fit_evidence_digest": verified.execution_digest,
        "fit_evidence_path": _portable_fit_path(
            Path(verified.fit_dir), label_path=label_path
        ),
    }


def _derive_label_evidence(
    conditions: Sequence[PersistedRepairCondition],
    *,
    label_path: Path,
) -> dict[str, Any]:
    """Rederive one complete label record in memory from persisted fits.

    Every path is independently passed through :func:`load_fit_evidence`, even
    when the caller supplies a previously verified object.  Role projections,
    masks and both acceptance verdicts are then recomputed.  There is no
    production overload accepting ``ConfirmatoryRun`` or raw arrays.
    """

    label_path = label_path.resolve()

    if isinstance(conditions, (str, bytes)) or not isinstance(conditions, Sequence):
        raise ValueError(
            "conditions must be a complete sequence of PersistedRepairCondition "
            "objects"
        )
    required = confirmatory_seeds(seeds_for(REPAIR_STAGE))
    if len(conditions) != len(required):
        raise ValueError(
            f"{REPAIR_STAGE!r} requires exactly {len(required)} persisted "
            f"conditions, got {len(conditions)}"
        )

    validated: list[_ValidatedCondition] = []
    seen_seeds: set[int] = set()
    physical_fit_dirs: dict[str, Path] = {}
    for condition in conditions:
        item = _validate_condition(condition)
        for projected in (item.baseline, item.data_repair, item.model_repair):
            fit_id = projected.verified.fit_id
            fit_dir = Path(projected.verified.fit_dir).resolve()
            if fit_id in physical_fit_dirs:
                raise ValueError(
                    f"duplicate physical fit_id {fit_id!r}: supplied from both "
                    f"{physical_fit_dirs[fit_id]} and {fit_dir}. One fit may carry "
                    "several registered roles, but it may appear as only one "
                    "physical execution"
                )
            physical_fit_dirs[fit_id] = fit_dir
        seed = item.seed
        if seed in seen_seeds:
            raise ValueError(f"duplicate repair-validation seed {seed}")
        seen_seeds.add(seed)
        validated.append(item)
    if seen_seeds != set(required):
        missing = sorted(set(required) - seen_seeds)
        extra = sorted(seen_seeds - set(required))
        raise ValueError(
            f"{REPAIR_STAGE!r} requires exact seeds {required}; "
            f"missing={missing}, unregistered={extra}"
        )
    validated.sort(key=lambda item: item.seed)

    units = [item.unit for item in validated]
    unit_ids = {item.baseline.verified.unit_id for item in validated}
    if len(unit_ids) != 1 or any(unit != units[0] for unit in units[1:]):
        raise ValueError(
            "the twenty condition runs do not share one unit_id and one exact "
            "configuration provenance"
        )
    model_arms = {item.model_repair_arm for item in validated}
    if len(model_arms) != 1:
        raise ValueError(
            f"model repair changes across seeds: {sorted(model_arms)}; the "
            "intervention must be fixed before outcomes are seen"
        )
    unit = units[0]
    model_arm = model_arms.pop()

    baseline = [item.baseline.evaluation for item in validated]
    data = [item.data_repair.evaluation for item in validated]
    model = [item.model_repair.evaluation for item in validated]
    masks: dict[int, np.ndarray] = {}
    mask_rows: list[dict[str, Any]] = []
    for evaluation in baseline:
        # Strictly greater is frozen. Equality is deliberately not a failure.
        mask = np.asarray(evaluation.error) > K.FAILURE_THRESHOLD
        if not mask.any():
            raise ValueError(
                f"the failure set is empty at seed {evaluation.seed} after strict "
                f"baseline.error > FAILURE_THRESHOLD ({K.FAILURE_THRESHOLD!r})"
            )
        masks[evaluation.seed] = mask
        mask_rows.append(_mask_row(evaluation.seed, evaluation, mask))

    data_result = acceptance_test(**acceptance_inputs(
        baseline, data, failure_masks=masks
    ))
    model_result = acceptance_test(**acceptance_inputs(
        baseline, model, failure_masks=masks
    ))
    assignment = LabelAssignment(
        unit_id=next(iter(unit_ids)),
        comparison_group_id=group_of(unit, REPAIR_STAGE),
        intended_class=_intended_class(unit),
        data_repair_works=data_result.passed,
        model_repair_works=model_result.passed,
    )

    payload: dict[str, Any] = {
        "label_evidence_schema_version": LABEL_EVIDENCE_SCHEMA_VERSION,
        "unit_id": assignment.unit_id,
        "unit": _unit_row(unit),
        "family": unit.family,
        "comparison_group_id": assignment.comparison_group_id,
        "intended_class": assignment.intended_class,
        "stage": REPAIR_STAGE,
        "seeds": list(required),
        "model_repair_arm": model_arm,
        "failure_definition": {
            "metric": "baseline.normalised_movement_error",
            "operator": ">",
            "threshold": K.FAILURE_THRESHOLD,
        },
        "failure_masks": mask_rows,
        "runs": [
            {
                "seed": condition.seed,
                "baseline": _run_identity(
                    condition.baseline, label_path=label_path
                ),
                "data_repair": _run_identity(
                    condition.data_repair, label_path=label_path
                ),
                "model_repair": _run_identity(
                    condition.model_repair, label_path=label_path
                ),
            }
            for condition in validated
        ],
        "acceptance": {
            "data_repair": _acceptance_row(data_result),
            "model_repair": _acceptance_row(model_result),
        },
        "label": {
            "unit_id": assignment.unit_id,
            "comparison_group_id": assignment.comparison_group_id,
            "intended_class": assignment.intended_class,
            "data_repair_works": assignment.data_repair_works,
            "model_repair_works": assignment.model_repair_works,
            "observed_label": assignment.observed_label,
        },
    }
    record = {**payload, "record_digest": _digest(payload)}
    _validate_record_metadata_unsafe(record, label_path=label_path)
    return json.loads(json.dumps(record))


def build_label_evidence(
    conditions: Sequence[PersistedRepairCondition],
    *,
    path: str | Path,
) -> dict[str, Any]:
    """Rederive and exclusively persist one source-addressable label record."""

    label_path = Path(path).resolve()
    record = _derive_label_evidence(conditions, label_path=label_path)
    _write_json_exclusive(label_path, record)
    return record


def _require_digest(value: object, *, field: str) -> str:
    value = _nonblank(value, field=field)
    if len(value) != _HEX_DIGEST_LENGTH or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _validate_acceptance_row(row: object, *, name: str, n_seeds: int) -> bool:
    if not isinstance(row, Mapping):
        raise ValueError(f"acceptance.{name} must be a JSON object")
    row = dict(row)
    _require_exact_keys(row, _ACCEPTANCE_KEYS, field=f"acceptance.{name}")
    if type(row.get("passed")) is not bool:
        raise ValueError(f"acceptance.{name}.passed must be an exact boolean")
    if _exact_int(row.get("n_seeds"), field=f"acceptance.{name}.n_seeds") != n_seeds:
        raise ValueError(f"acceptance.{name} does not attest all {n_seeds} seeds")
    if row.get("method") != "paired_seed_cluster":
        raise ValueError(f"acceptance.{name} carries an unregistered method")
    if type(row.get("converged")) is not bool:
        raise ValueError(f"acceptance.{name}.converged must be an exact boolean")
    if row.get("min_practical_effect") != K.MIN_PRACTICAL_EFFECT or isinstance(
        row.get("min_practical_effect"), bool
    ):
        raise ValueError(
            f"acceptance.{name}.min_practical_effect is not the frozen "
            f"{K.MIN_PRACTICAL_EFFECT!r}"
        )
    if row.get("confidence") != CONFIDENCE or isinstance(row.get("confidence"), bool):
        raise ValueError(
            f"acceptance.{name}.confidence is not the frozen {CONFIDENCE!r}"
        )
    _nonblank(row.get("reason"), field=f"acceptance.{name}.reason")
    n_transitions = _exact_int(
        row.get("n_transitions"), field=f"acceptance.{name}.n_transitions"
    )
    n_episodes = _exact_int(
        row.get("n_episodes"), field=f"acceptance.{name}.n_episodes"
    )
    if n_transitions <= 0 or n_episodes <= 0:
        raise ValueError(
            f"acceptance.{name} transition and episode counts must be positive"
        )
    interval_numeric = ("effect", "ci_low", "ci_high", "relative_reduction")
    for field in interval_numeric:
        value = row.get(field)
        if row["converged"]:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"acceptance.{name}.{field} must be finite")
        elif value is not None:
            raise ValueError(
                f"acceptance.{name}.{field} must be null when the interval did not form"
            )
    unrepaired = row.get("unrepaired_mean")
    if isinstance(unrepaired, bool) or not isinstance(unrepaired, (int, float)) or not math.isfinite(unrepaired):
        raise ValueError(f"acceptance.{name}.unrepaired_mean must be finite")
    if unrepaired <= 0:
        raise ValueError(f"acceptance.{name}.unrepaired_mean must be positive")
    if row["converged"]:
        effect = float(row["effect"])
        ci_low = float(row["ci_low"])
        ci_high = float(row["ci_high"])
        relative = float(row["relative_reduction"])
        if not ci_low <= effect <= ci_high or not ci_low < ci_high:
            raise ValueError(
                f"acceptance.{name} interval does not contain its effect"
            )
        expected_relative = -effect / float(unrepaired)
        if not math.isclose(
            relative, expected_relative, rel_tol=1e-12, abs_tol=1e-15
        ):
            raise ValueError(
                f"acceptance.{name}.relative_reduction is not -effect / "
                "unrepaired_mean"
            )
        expected_passed = (
            effect < 0
            and ci_high < 0
            and relative > K.MIN_PRACTICAL_EFFECT
        )
    else:
        expected_passed = False
    if row["passed"] is not expected_passed:
        raise ValueError(
            f"acceptance.{name}.passed={row['passed']!r} disagrees with the "
            "frozen negative-effect, confidence-interval, and practical-effect "
            f"rules; recomputed passed={expected_passed!r}"
        )
    return row["passed"]


def _validate_record_metadata_unsafe(
    record: object, *, label_path: Path
) -> dict[str, Any]:
    """Validate record structure only; this is never sufficient evidence.

    The name is intentionally explicit.  This helper does not open source fit
    directories and must not be used by summaries or claim-producing callers.
    Full verification is :func:`load_label_evidence`.
    """

    label_path = label_path.resolve()
    if not isinstance(record, Mapping):
        raise ValueError("label evidence must be a JSON object")
    record = dict(record)
    _require_exact_keys(record, _TOP_LEVEL_KEYS, field="label evidence")
    digest = _require_digest(record.get("record_digest"), field="record_digest")
    payload = {key: value for key, value in record.items() if key != "record_digest"}
    if _digest(payload) != digest:
        raise ValueError("label evidence record_digest does not match its content")
    if (
        type(record.get("label_evidence_schema_version")) is not int
        or record.get("label_evidence_schema_version") != LABEL_EVIDENCE_SCHEMA_VERSION
    ):
        raise ValueError(
            "unsupported label_evidence_schema_version "
            f"{record.get('label_evidence_schema_version')!r}"
        )
    unit = _unit_from_row(record.get("unit"))
    unit_id = Config(unit=unit).unit_id
    if record.get("unit_id") != unit_id:
        raise ValueError("unit_id does not match the recorded unit provenance")
    if record.get("family") != unit.family:
        raise ValueError("family does not match the recorded unit provenance")
    intended = _intended_class(unit)
    if record.get("intended_class") != intended:
        raise ValueError("intended_class does not match the recorded family")
    if record.get("stage") != REPAIR_STAGE:
        raise ValueError(f"label evidence stage must be {REPAIR_STAGE!r}")
    group = group_of(unit, REPAIR_STAGE)
    if record.get("comparison_group_id") != group:
        raise ValueError("comparison_group_id does not match the unit and stage")
    required = confirmatory_seeds(seeds_for(REPAIR_STAGE))
    if record.get("seeds") != list(required):
        raise ValueError("label evidence does not carry the exact registered seed list")
    model_arm = record.get("model_repair_arm")
    if model_arm not in _MODEL_REPAIR_ARMS:
        raise ValueError("label evidence carries an invalid model_repair_arm")
    Arm(model_arm).resolve(unit)
    failure_definition = record.get("failure_definition")
    if not isinstance(failure_definition, Mapping):
        raise ValueError("failure_definition must be a JSON object")
    _require_exact_keys(
        failure_definition, _FAILURE_DEFINITION_KEYS, field="failure_definition"
    )
    if dict(failure_definition) != {
        "metric": "baseline.normalised_movement_error",
        "operator": ">",
        "threshold": K.FAILURE_THRESHOLD,
    }:
        raise ValueError("failure definition is not the frozen strict threshold rule")

    masks = record.get("failure_masks")
    if not isinstance(masks, list) or len(masks) != len(required):
        raise ValueError("failure_masks must contain one row per registered seed")
    if [row.get("seed") for row in masks if isinstance(row, Mapping)] != list(required):
        raise ValueError("failure mask rows are not in the exact registered seed order")
    for row in masks:
        if not isinstance(row, Mapping):
            raise ValueError("every failure mask row must be a JSON object")
        _require_exact_keys(row, _MASK_KEYS, field="failure mask row")
        _exact_int(row.get("seed"), field="mask.seed")
        n = _exact_int(row.get("n_transitions"), field="mask.n_transitions")
        count = _exact_int(row.get("failure_count"), field="mask.failure_count")
        if n <= 0 or count <= 0 or count > n:
            raise ValueError("failure mask counts must satisfy 0 < failures <= transitions")
        _require_digest(row.get("mask_digest"), field="mask.mask_digest")
        _require_digest(
            row.get("baseline_error_digest"), field="mask.baseline_error_digest"
        )

    runs = record.get("runs")
    if not isinstance(runs, list) or len(runs) != len(required):
        raise ValueError("runs must contain one identity row per registered seed")
    if [row.get("seed") for row in runs if isinstance(row, Mapping)] != list(required):
        raise ValueError("run identity rows are not in the exact registered seed order")
    seen_fit_ids: set[str] = set()
    for row in runs:
        if not isinstance(row, Mapping):
            raise ValueError("every run identity row must be a JSON object")
        _require_exact_keys(row, _RUN_ROW_KEYS, field="run identity row")
        seed = _exact_int(row.get("seed"), field="run.seed")
        for key, arm in (
            ("baseline", "baseline"),
            ("data_repair", "data_repair"),
            ("model_repair", model_arm),
        ):
            identity = row.get(key)
            if not isinstance(identity, Mapping):
                raise ValueError(f"run row {seed} has invalid {key} identity")
            _require_exact_keys(
                identity, _RUN_IDENTITY_KEYS, field=f"run row {seed} {key}"
            )
            if identity.get("arm") != arm:
                raise ValueError(f"run row {seed} has invalid {key} identity")
            spec = _registered_spec(unit, arm, seed)
            expected = {
                "run_id": spec.run_id_for(REPAIR_STAGE),
                "config_id": spec.config_id,
                "fit_id": spec.fit_id,
                "execution_stage": spec.execution_stage,
                "execution_run_id": spec.execution_run_id,
                "fit_roles": list(spec.roles),
            }
            for field, value in expected.items():
                if identity.get(field) != value:
                    raise ValueError(
                        f"run row {seed} {key}.{field} is inconsistent with provenance"
                    )
            _require_digest(
                identity.get("fit_evidence_digest"),
                field=f"run row {seed} {key}.fit_evidence_digest",
            )
            _resolve_portable_fit_path(
                identity.get("fit_evidence_path"), label_path=label_path
            )
            if identity["fit_id"] in seen_fit_ids:
                raise ValueError(
                    f"run row {seed} repeats physical fit_id {identity['fit_id']!r}"
                )
            seen_fit_ids.add(identity["fit_id"])

    acceptance = record.get("acceptance")
    if not isinstance(acceptance, Mapping):
        raise ValueError("acceptance must be a JSON object")
    _require_exact_keys(
        acceptance, frozenset({"data_repair", "model_repair"}), field="acceptance"
    )
    data_passed = _validate_acceptance_row(
        acceptance.get("data_repair"), name="data_repair", n_seeds=len(required)
    )
    model_passed = _validate_acceptance_row(
        acceptance.get("model_repair"), name="model_repair", n_seeds=len(required)
    )
    label = record.get("label")
    if not isinstance(label, Mapping):
        raise ValueError("label must be a JSON object")
    _require_exact_keys(label, _LABEL_KEYS, field="label")
    if type(label.get("data_repair_works")) is not bool:
        raise ValueError("label.data_repair_works must be an exact boolean")
    if type(label.get("model_repair_works")) is not bool:
        raise ValueError("label.model_repair_works must be an exact boolean")
    observed = label.get("observed_label")
    if not (
        (type(observed) is int and observed in (0, 1))
        or (type(observed) is str and observed in ("ambiguous", "undiagnosed"))
    ):
        raise ValueError(
            "label.observed_label must be exact integer 0/1 or the registered "
            "string; booleans are not integer labels"
        )
    expected_label = {
        "unit_id": unit_id,
        "comparison_group_id": group,
        "intended_class": intended,
        "data_repair_works": data_passed,
        "model_repair_works": model_passed,
        "observed_label": observed_label(data_passed, model_passed),
    }
    if dict(label) != expected_label:
        raise ValueError("label does not match provenance and acceptance verdicts")
    return record


def _conditions_from_record(
    record: Mapping[str, Any], *, label_path: Path
) -> tuple[PersistedRepairCondition, ...]:
    conditions: list[PersistedRepairCondition] = []
    for row in record["runs"]:
        conditions.append(
            PersistedRepairCondition(
                baseline=_resolve_portable_fit_path(
                    row["baseline"]["fit_evidence_path"], label_path=label_path
                ),
                data_repair=_resolve_portable_fit_path(
                    row["data_repair"]["fit_evidence_path"], label_path=label_path
                ),
                model_repair=_resolve_portable_fit_path(
                    row["model_repair"]["fit_evidence_path"], label_path=label_path
                ),
            )
        )
    return tuple(conditions)


def load_label_evidence(path: str | Path) -> dict[str, Any]:
    """Reload all source fits and exactly rederive one immutable label record."""

    path = Path(path).resolve()
    try:
        record = read_json(path)
    except DurabilityError as exc:
        raise ValueError(f"cannot load complete label evidence from {path}: {exc}") from exc
    metadata = _validate_record_metadata_unsafe(record, label_path=path)
    conditions = _conditions_from_record(metadata, label_path=path)
    rederived = _derive_label_evidence(conditions, label_path=path)
    if metadata != rederived:
        raise ValueError(
            "label evidence does not exactly equal the record rederived from all "
            "60 persisted fit sidecars; source digests, failure masks, acceptance "
            "statistics and the observed label are evidence-derived"
        )
    return rederived


def _empty_counts() -> dict[str, int]:
    return {"observed_0": 0, "observed_1": 0, "ambiguous": 0, "undiagnosed": 0}


def _add_label(counts: dict[str, int], label: object) -> None:
    if type(label) is bool:
        raise ValueError("boolean observed labels are invalid; False is not label 0")
    key = {
        0: "observed_0",
        1: "observed_1",
        "ambiguous": "ambiguous",
        "undiagnosed": "undiagnosed",
    }.get(label)
    if key is None:
        raise ValueError(f"unknown observed label {label!r}")
    counts[key] += 1


def _count_report(counts: Mapping[str, int]) -> dict[str, Any]:
    attempted = sum(counts.values())
    excluded = counts["ambiguous"] + counts["undiagnosed"]
    return {
        "attempted": attempted,
        "observed_0": counts["observed_0"],
        "observed_1": counts["observed_1"],
        "ambiguous": counts["ambiguous"],
        "undiagnosed": counts["undiagnosed"],
        "excluded": excluded,
        "exclusion_rate": (excluded / attempted if attempted else None),
    }


def count_label_evidence(
    evidence_paths: Iterable[str | PathLike[str]],
) -> dict[str, Any]:
    """Return the Week-6 count-only report over source-reverified labels.

    This boundary deliberately stops before the exclusion-rate estimand.  The
    first comparison with the registered 0.00 planning convention is a Week-8
    obligation (D-144), so neither the rate, an ``excluded`` convenience
    total, the convention, nor a pass/fail comparison appears in this schema.
    Every input is reopened through :func:`load_label_evidence`; callers cannot
    substitute an in-memory label or metadata row for the persisted sources.
    """

    if isinstance(evidence_paths, (str, bytes, PathLike, Mapping)):
        raise ValueError(
            "evidence_paths must be an iterable of label-evidence paths; raw "
            "metadata records are refused because counts must reload sources"
        )
    counts = _empty_counts()
    seen: set[str] = set()
    for position, source in enumerate(evidence_paths):
        if not isinstance(source, (str, PathLike)):
            raise ValueError(
                f"label evidence at position {position} must be a filesystem "
                f"path, got {type(source).__name__}"
            )
        try:
            record = load_label_evidence(source)
        except ValueError as exc:
            raise ValueError(
                f"invalid evidence record at position {position}: {exc}"
            ) from exc
        unit_id = record["unit_id"]
        if unit_id in seen:
            raise ValueError(f"duplicate unit_id {unit_id!r} in evidence counts")
        seen.add(unit_id)
        _add_label(counts, record["label"]["observed_label"])

    if not seen:
        raise ValueError("cannot count zero label-evidence records")
    payload: dict[str, Any] = {
        "label_count_schema_version": LABEL_COUNT_SCHEMA_VERSION,
        "attempted": sum(counts.values()),
        "observed_0": counts["observed_0"],
        "observed_1": counts["observed_1"],
        "ambiguous": counts["ambiguous"],
        "undiagnosed": counts["undiagnosed"],
    }
    return {**payload, "count_digest": _digest(payload)}


def write_label_evidence_counts(
    evidence_paths: Iterable[str | PathLike[str]],
    *,
    path: str | Path,
) -> dict[str, Any]:
    """Persist the exact Week-6 count-only report immutably."""

    counts = count_label_evidence(evidence_paths)
    _write_json_exclusive(Path(path), counts)
    return json.loads(json.dumps(counts))


def summarize_label_evidence(
    evidence_paths: Iterable[str | PathLike[str]],
) -> dict[str, Any]:
    """Return the pre-reserve report over fully source-verified label files."""

    if isinstance(evidence_paths, (str, bytes, PathLike, Mapping)):
        raise ValueError(
            "evidence_paths must be an iterable of label-evidence paths; raw "
            "metadata records are refused because summaries must reload sources"
        )
    pooled = _empty_counts()
    per_class = {name: _empty_counts() for name in INTENDED_CLASSES}
    seen: set[str] = set()
    for position, source in enumerate(evidence_paths):
        if not isinstance(source, (str, PathLike)):
            raise ValueError(
                f"label evidence at position {position} must be a filesystem path, "
                f"got {type(source).__name__}"
            )
        try:
            record = load_label_evidence(source)
        except ValueError as exc:
            raise ValueError(f"invalid evidence record at position {position}: {exc}") from exc
        unit_id = record["unit_id"]
        if unit_id in seen:
            raise ValueError(f"duplicate unit_id {unit_id!r} in evidence summary")
        seen.add(unit_id)
        label = record["label"]["observed_label"]
        _add_label(pooled, label)
        _add_label(per_class[record["intended_class"]], label)

    if not seen:
        raise ValueError(
            "cannot report an exclusion rate from zero evidence records; the "
            "registered 0.00 value is a planning assumption, not an observation"
        )

    pooled_report = _count_report(pooled)
    class_reports = {
        name: _count_report(per_class[name]) for name in INTENDED_CLASSES
    }
    excluded = pooled_report["excluded"]
    attempted = pooled_report["attempted"]
    missed = excluded > 0
    if missed:
        language = (
            f"The registered planning exclusion-rate assumption 0.00 was missed: "
            f"{excluded} of {attempted} attempted unit(s) were excluded. This "
            "shortfall is recorded before any reserve unit is drawn or run."
        )
    else:
        language = (
            "The registered planning exclusion-rate assumption 0.00 was met: "
            "no attempted units were excluded. The zero shortfall is recorded "
            "before any reserve action."
        )
    payload: dict[str, Any] = {
        "label_summary_schema_version": LABEL_SUMMARY_SCHEMA_VERSION,
        **pooled_report,
        "per_intended_class": class_reports,
        "surviving_min_n0_n1": min(
            pooled_report["observed_0"], pooled_report["observed_1"]
        ),
        "registered_planning_exclusion_rate": REGISTERED_PLANNING_EXCLUSION_RATE,
        "planning_assumption_missed": missed,
        "shortfall_before_reserve_count": excluded,
        "shortfall_before_reserve": language,
    }
    return {**payload, "summary_digest": _digest(payload)}


def write_label_evidence_summary(
    evidence_paths: Iterable[str | PathLike[str]],
    *,
    path: str | Path,
) -> dict[str, Any]:
    """Build and exclusively persist the exact pre-reserve summary report."""

    summary = summarize_label_evidence(evidence_paths)
    _write_json_exclusive(Path(path), summary)
    return json.loads(json.dumps(summary))
