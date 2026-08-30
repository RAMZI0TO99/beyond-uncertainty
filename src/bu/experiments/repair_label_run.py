"""Persisted end-to-end orchestration for one Week 6 repair label.

This module supplies the narrow operational bridge between the role-aware fit
evidence boundary and the repair-label boundary.  It accepts one exact
registered :class:`~bu.config.UnitSpec`, derives the complete twenty-seed
``repair_validation`` ladder, and executes exactly three arms per seed in the
registered order: baseline, data repair, then the unit's sole model-class
repair.  No seed subset, stage, arm choice, or training parameter is exposed.

The immutable plan is published before the first fit.  Resume is deliberately
strict: an expected fit directory is reused only after
``load_fit_evidence`` independently verifies it and this module matches every
identity to the precomputed plan.  An existing partial or divergent directory
is never completed in place and never retrained over.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..config import Config, UnitSpec, seeds_for
from ..durable import (
    DivergentTargetError,
    DurabilityError,
    atomic_write_json,
    read_json,
)
from ..models.uncertainty import NormalisationScale
from ..streams import confirmatory_seeds
from .fit_evidence import (
    RegisteredFitSpec,
    VerifiedFitEvidence,
    load_fit_evidence,
    registered_fit_spec,
    run_confirmatory_fit,
)
from .label_evidence import (
    LABEL_COUNT_FILE,
    LABEL_EVIDENCE_FILE,
    PersistedRepairCondition,
    build_label_evidence,
    write_label_evidence_counts,
)
from .repair import REPAIR_STAGE, applicable_arms


REPAIR_LABEL_PLAN_SCHEMA_VERSION = 2
REPAIR_LABEL_PLAN_FILE = "repair_label_plan.json"
FIT_DIRECTORY = "jobs"
WEEK6_SMOKE_UNIT_ID = "d5baeb907ac3"

_MODEL_REPAIR_ARMS = ("feature_repair", "capacity_repair")
_ARMS_BEFORE_MODEL = ("baseline", "data_repair")
_PLAN_KEYS = frozenset(
    {
        "repair_label_plan_schema_version",
        "unit_id",
        "unit",
        "stage",
        "seeds",
        "model_repair_arm",
        "fit_order",
        "outputs",
        "plan_digest",
    }
)


@dataclass(frozen=True)
class RepairLabelRunResult:
    """Paths and records produced by one complete orchestration."""

    plan_path: Path
    label_path: Path
    count_path: Path
    label: dict[str, Any]
    counts: dict[str, Any]
    executed_fits: int
    resumed_fits: int


@dataclass(frozen=True)
class _PlannedFit:
    ordinal: int
    seed: int
    arm: str
    spec: RegisteredFitSpec
    path: Path
    relative_path: str


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _unit_row(unit: UnitSpec) -> dict[str, Any]:
    return dict(Config(unit=unit).to_dict()["unit"])


def registered_week6_smoke_unit() -> UnitSpec:
    """Return the one predeclared Week-6 repair-label smoke condition."""

    unit = UnitSpec(
        causal_attribute="shape",
        confound_rate=0.25,
        layout="uniform",
        family="missing_feature",
        n_transitions=5000,
        withheld_features=("shape",),
        hidden_size=256,
    )
    observed = Config(unit=unit).unit_id
    if observed != WEEK6_SMOKE_UNIT_ID:
        raise RuntimeError(
            "the predeclared Week-6 smoke unit identity drifted: "
            f"observed {observed!r}, expected {WEEK6_SMOKE_UNIT_ID!r}"
        )
    return unit


def _require_registered_smoke_unit(unit: object) -> UnitSpec:
    if type(unit) is not UnitSpec:
        raise ValueError(
            f"unit must be an exact UnitSpec, got {type(unit).__name__}"
        )
    expected = registered_week6_smoke_unit()
    observed_id = Config(unit=unit).unit_id
    if unit != expected or observed_id != WEEK6_SMOKE_UNIT_ID:
        raise ValueError(
            "the production Week-6 smoke boundary accepts only predeclared "
            f"unit {WEEK6_SMOKE_UNIT_ID}; got {observed_id}"
        )
    return unit


def _model_repair_arm(unit: UnitSpec) -> str:
    repairs = applicable_arms(unit)
    if "data_repair" not in repairs:
        raise ValueError("the registered repair protocol has no data-repair arm")
    model_arms = tuple(arm for arm in repairs if arm in _MODEL_REPAIR_ARMS)
    if len(model_arms) != 1:
        raise ValueError(
            f"unit exposes model-repair arms {model_arms}; the Week 6 2x2 "
            "protocol requires exactly one registered model-class repair"
        )
    return model_arms[0]


def _registered_plan(
    unit: UnitSpec, root: Path
) -> tuple[str, tuple[int, ...], tuple[_PlannedFit, ...]]:
    if type(unit) is not UnitSpec:
        raise ValueError(
            f"unit must be an exact UnitSpec, got {type(unit).__name__}"
        )
    model_arm = _model_repair_arm(unit)
    n_seeds = seeds_for(REPAIR_STAGE)
    if type(n_seeds) is not int or n_seeds <= 0:
        raise RuntimeError(
            f"{REPAIR_STAGE!r} has no positive registered seed inventory"
        )
    seeds = confirmatory_seeds(n_seeds)
    arms = (*_ARMS_BEFORE_MODEL, model_arm)
    planned: list[_PlannedFit] = []
    for seed in seeds:
        for arm in arms:
            # This lookup proves that the exact unit/arm/seed is an obligation
            # in the registered design before a plan file or fit is created.
            spec = registered_fit_spec(unit, arm=arm, seed=seed)
            if REPAIR_STAGE not in spec.roles:
                raise ValueError(
                    f"fit {spec.fit_id!r} does not carry the registered "
                    f"{REPAIR_STAGE!r} role"
                )
            relative = (Path(FIT_DIRECTORY) / spec.fit_id).as_posix()
            planned.append(
                _PlannedFit(
                    ordinal=len(planned),
                    seed=seed,
                    arm=arm,
                    spec=spec,
                    path=root / Path(relative),
                    relative_path=relative,
                )
            )
    if len(planned) != n_seeds * 3:
        raise RuntimeError(
            f"repair-label plan contains {len(planned)} fits, expected "
            f"{n_seeds} seeds x 3 arms"
        )
    return model_arm, seeds, tuple(planned)


def _plan_document(
    unit: UnitSpec,
    *,
    model_arm: str,
    seeds: tuple[int, ...],
    planned: tuple[_PlannedFit, ...],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "repair_label_plan_schema_version": REPAIR_LABEL_PLAN_SCHEMA_VERSION,
        "unit_id": Config(unit=unit).unit_id,
        "unit": _unit_row(unit),
        "stage": REPAIR_STAGE,
        "seeds": list(seeds),
        "model_repair_arm": model_arm,
        "fit_order": [
            {
                "ordinal": item.ordinal,
                "seed": item.seed,
                "arm": item.arm,
                "unit_id": item.spec.unit_id,
                "config_id": item.spec.config_id,
                "fit_id": item.spec.fit_id,
                "execution_stage": item.spec.execution_stage,
                "execution_run_id": item.spec.execution_run_id,
                "roles": list(item.spec.roles),
                "path": item.relative_path,
            }
            for item in planned
        ],
        "outputs": {
            "label": LABEL_EVIDENCE_FILE,
            "counts": LABEL_COUNT_FILE,
        },
    }
    return {**payload, "plan_digest": _digest(payload)}


def _publish_plan(path: Path, document: Mapping[str, Any]) -> None:
    try:
        atomic_write_json(path, dict(document))
        loaded = read_json(path)
    except DivergentTargetError as exc:
        raise ValueError(
            f"immutable repair-label plan at {path} differs from the exact "
            "registered plan; refusing resume"
        ) from exc
    except DurabilityError as exc:
        raise ValueError(f"cannot persist and verify repair-label plan at {path}: {exc}") from exc
    if not isinstance(loaded, Mapping) or set(loaded) != set(_PLAN_KEYS):
        raise ValueError(f"repair-label plan at {path} does not have the exact schema")
    payload = {key: loaded[key] for key in loaded if key != "plan_digest"}
    if loaded.get("plan_digest") != _digest(payload):
        raise ValueError(f"repair-label plan at {path} has an invalid digest")
    if dict(loaded) != dict(document):
        raise ValueError(
            f"repair-label plan at {path} does not equal the re-derived plan"
        )


def _scale_fingerprint(scale: NormalisationScale) -> tuple[Any, ...]:
    if type(scale) is not NormalisationScale:
        raise ValueError(
            f"fit evidence scale must be an exact NormalisationScale, got "
            f"{type(scale).__name__}"
        )
    vector = scale.vector.detach().cpu().contiguous().numpy()
    return (
        vector.dtype.str,
        tuple(vector.shape),
        vector.tobytes(),
        scale.n_reference,
        scale.domain,
        scale.source,
    )


def _validate_loaded(
    verified: object, *, planned: _PlannedFit
) -> VerifiedFitEvidence:
    if type(verified) is not VerifiedFitEvidence:
        raise ValueError(
            f"fit loader returned {type(verified).__name__} for {planned.path}; "
            "expected exact VerifiedFitEvidence"
        )
    expected = planned.spec
    actual_path = Path(verified.fit_dir).resolve()
    expected_path = planned.path.resolve()
    mismatches: list[str] = []
    for name, actual, wanted in (
        ("fit_dir", actual_path, expected_path),
        ("unit", verified.unit, expected.unit),
        ("arm", verified.arm, expected.arm),
        ("seed", verified.seed, expected.seed),
        ("roles", verified.roles, expected.roles),
        ("execution_stage", verified.execution_stage, expected.execution_stage),
        ("unit_id", verified.unit_id, expected.unit_id),
        ("config_id", verified.config_id, expected.config_id),
        ("fit_id", verified.fit_id, expected.fit_id),
        ("execution_run_id", verified.execution_run_id, expected.execution_run_id),
    ):
        if actual != wanted:
            mismatches.append(f"{name}={actual!r}, expected {wanted!r}")
    if mismatches:
        raise ValueError(
            f"persisted fit at {planned.path} diverges from its immutable plan: "
            + "; ".join(mismatches)
        )
    _scale_fingerprint(verified.scale)
    return verified


def _load_existing(
    planned: _PlannedFit, *, expected_git_commit: str | None = None
) -> VerifiedFitEvidence:
    if planned.path.is_symlink():
        raise ValueError(
            f"expected fit directory {planned.path} is a symlink; refusing resume"
        )
    if not planned.path.is_dir():
        raise ValueError(
            f"expected fit path {planned.path} exists but is not a directory"
        )
    try:
        if expected_git_commit is None:
            loaded = load_fit_evidence(planned.path)
        else:
            loaded = load_fit_evidence(
                planned.path, expected_git_commit=expected_git_commit
            )
    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise ValueError(
            f"existing fit directory {planned.path} is partial or invalid; "
            "refusing to retrain or complete it in place"
        ) from exc
    return _validate_loaded(loaded, planned=planned)


def _obtain_fit(
    planned: _PlannedFit,
    *,
    scale: NormalisationScale | None,
) -> tuple[VerifiedFitEvidence, bool]:
    if planned.path.exists() or planned.path.is_symlink():
        return _load_existing(planned), False
    try:
        run_confirmatory_fit(
            planned.spec.unit,
            arm=planned.arm,
            seed=planned.seed,
            out_dir=planned.path,
            scale=scale,
        )
    except Exception:
        # Any artifacts left by an interrupted execution are intentionally left
        # visible.  The next invocation will classify the directory as partial
        # and refuse rather than obscuring or training over it.
        raise
    if not planned.path.is_dir():
        raise ValueError(
            f"fit execution returned without publishing its directory: {planned.path}"
        )
    try:
        loaded = load_fit_evidence(planned.path)
    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise ValueError(
            f"new fit at {planned.path} did not publish complete verifiable "
            "fit evidence"
        ) from exc
    return _validate_loaded(loaded, planned=planned), True


def _run_synthetic_repair_label(
    unit: UnitSpec,
    *,
    out_dir: str | Path,
) -> RepairLabelRunResult:
    """Synthetic-only in-process exercise of the persisted label boundary.

    Production code must use :mod:`bu.experiments.repair_label_launch`, which
    supplies a lease, a mandatory timeout, fresh-process isolation, staging,
    atomic publication, commit binding, and incremental independent sync.
    This private function remains only for deterministic tests with fabricated
    fit writers; calling it is never a valid way to produce scientific data.
    """

    root = Path(out_dir).resolve()
    model_arm, seeds, planned = _registered_plan(unit, root)
    plan_path = root / REPAIR_LABEL_PLAN_FILE
    plan = _plan_document(
        unit, model_arm=model_arm, seeds=seeds, planned=planned
    )
    # This is intentionally the first filesystem write in this function.
    _publish_plan(plan_path, plan)

    by_seed: dict[int, dict[str, Path]] = {}
    executed = 0
    resumed = 0
    for position in range(0, len(planned), 3):
        seed_items = planned[position : position + 3]
        if tuple(item.arm for item in seed_items) != (
            "baseline",
            "data_repair",
            model_arm,
        ):
            raise RuntimeError("internal repair-label fit order is not canonical")
        baseline, did_execute = _obtain_fit(seed_items[0], scale=None)
        executed += int(did_execute)
        resumed += int(not did_execute)
        baseline_scale = baseline.scale

        paths = {"baseline": seed_items[0].path}
        for item in seed_items[1:]:
            repaired, did_execute = _obtain_fit(item, scale=baseline_scale)
            executed += int(did_execute)
            resumed += int(not did_execute)
            if _scale_fingerprint(repaired.scale) != _scale_fingerprint(baseline_scale):
                raise ValueError(
                    f"seed {item.seed} arm {item.arm!r} does not persist the "
                    "baseline's exact normalisation scale"
                )
            paths[item.arm] = item.path
        by_seed[seed_items[0].seed] = paths

    conditions = tuple(
        PersistedRepairCondition(
            baseline=by_seed[seed]["baseline"],
            data_repair=by_seed[seed]["data_repair"],
            model_repair=by_seed[seed][model_arm],
        )
        for seed in seeds
    )
    label_path = root / LABEL_EVIDENCE_FILE
    count_path = root / LABEL_COUNT_FILE
    label = build_label_evidence(conditions, path=label_path)
    # The count boundary deliberately reloads the immutable label from its
    # path rather than trusting the in-memory mapping returned by the writer.
    counts = write_label_evidence_counts((label_path,), path=count_path)
    return RepairLabelRunResult(
        plan_path=plan_path,
        label_path=label_path,
        count_path=count_path,
        label=label,
        counts=counts,
        executed_fits=executed,
        resumed_fits=resumed,
    )


def _finalize_registered_label(
    root: str | Path, *, expected_git_commit: str | None = None
) -> RepairLabelRunResult:
    """Reopen all 60 planned sidecars, then publish label and Week-6 counts."""

    root_path = Path(root).resolve()
    unit = registered_week6_smoke_unit()
    model_arm, seeds, planned = _registered_plan(unit, root_path)
    plan = _plan_document(
        unit, model_arm=model_arm, seeds=seeds, planned=planned
    )
    _publish_plan(root_path / REPAIR_LABEL_PLAN_FILE, plan)

    by_seed: dict[int, dict[str, Path]] = {}
    for item in planned:
        verified = _load_existing(
            item, expected_git_commit=expected_git_commit
        )
        by_seed.setdefault(item.seed, {})[item.arm] = verified.fit_dir
    conditions = tuple(
        PersistedRepairCondition(
            baseline=by_seed[seed]["baseline"],
            data_repair=by_seed[seed]["data_repair"],
            model_repair=by_seed[seed][model_arm],
        )
        for seed in seeds
    )
    label_path = root_path / LABEL_EVIDENCE_FILE
    count_path = root_path / LABEL_COUNT_FILE
    label = build_label_evidence(conditions, path=label_path)
    counts = write_label_evidence_counts((label_path,), path=count_path)
    return RepairLabelRunResult(
        plan_path=root_path / REPAIR_LABEL_PLAN_FILE,
        label_path=label_path,
        count_path=count_path,
        label=label,
        counts=counts,
        executed_fits=0,
        resumed_fits=len(planned),
    )


def run_repair_label(unit: UnitSpec, *, out_dir: str | Path) -> RepairLabelRunResult:
    """Refuse the retired in-process production path before filesystem access."""

    del unit, out_dir
    raise RuntimeError(
        "direct repair-label execution is disabled; run the immutable "
        "repair_label_preflight CLI followed by repair_label_launch so every "
        "fit is commit-bound, isolated, timed, staged, leased, and synced"
    )
