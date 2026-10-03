"""Source-bound Week-8 exclusion report for the exact first sweep batch.

This module has one deliberately narrow job: reopen the already-produced
ordinary-sweep label for batch ``sweep-001`` through its certified source
boundary and report the registered pre-reserve exclusion arithmetic.  It does
not discover labels, accept in-memory label rows, select reserve units, import
the reserve module, or run any experiment.

The caller must retain three independent things: the label path, the exact
registered :class:`~bu.config.UnitSpec`, and the three exact
:class:`~bu.experiments.ordinary_sweep_label_evidence.SweepRepairCondition`
objects containing all nine source pins.  Every summary and every load passes
those objects back to ``load_ordinary_sweep_label_evidence``.  The report is
therefore a view over reverified evidence rather than a second authority for
the observed label.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any

from ..config import Config, UnitSpec
from ..critic.split import INTENDED_CLASSES
from ..durable import (
    DivergentTargetError,
    DurabilityError,
    atomic_write_json,
    read_json,
    sha256_file,
)
from ..runrecord import PROJECT_ROOT
from ..streams import group_of
from . import label_evidence as L
from .labels import observed_label
from .ordinary_sweep_label_evidence import (
    ORDINARY_SWEEP_LABEL_EVIDENCE_SCHEMA_VERSION,
    PairedRepairSource,
    SweepBaselineSource,
    SweepRepairCondition,
    load_ordinary_sweep_label_evidence,
)


WEEK8_SWEEP_EXCLUSION_SCHEMA_VERSION = 1
WEEK8_SWEEP_EXCLUSION_FILE = "week8_first_sweep_exclusion.json"
FIRST_SWEEP_BATCH_KEY = "sweep-001"
FIRST_SWEEP_BATCH_1_UNIT_ID = "0184fbfcd8b9"
FIRST_SWEEP_BATCH_1_UNIT_IDS = (FIRST_SWEEP_BATCH_1_UNIT_ID,)
REGISTERED_PLANNING_EXCLUSION_RATE = 0.00
RESERVE_STATUS = "not_authorized_not_drawn"
WORKSPACE_ROOT = PROJECT_ROOT.parent

_STAGE = "exp3_repairs"
_BASELINE_STAGE = "config_sweep"
_SEEDS = (1000, 1001, 1002)
_INTENDED_CLASSES = ("estimation", "hypothesis_class")
_OBSERVED_LABELS = (0, 1, "ambiguous", "undiagnosed")
_ARMS = ("baseline", "data_repair", "model_repair")
_HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class SourceBoundSweepLabel:
    """One persisted label plus its independently retained source contract."""

    path: str | PathLike[str]
    unit: UnitSpec
    conditions: tuple[SweepRepairCondition, ...]


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not strict JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _copy(value: Any) -> Any:
    """Return a detached strict-JSON copy of a report."""

    return json.loads(_canonical(value))


def _same(actual: Any, expected: Any, *, what: str) -> None:
    # Canonical JSON equality distinguishes booleans from integer labels.
    if _canonical(actual) != _canonical(expected):
        raise ValueError(f"{what} differs from independently verified evidence")


def _hex(value: object, *, length: int, field: str) -> str:
    pattern = _HEX_40 if length == 40 else _HEX_64
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError(f"{field} must be exact lowercase {length}-hex")
    return value


def _is_reparse(info: os.stat_result) -> bool:
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(marker and getattr(info, "st_file_attributes", 0) & marker)


def _unresolved_path(value: object, *, field: str) -> Path:
    if isinstance(value, bytes) or not isinstance(value, (str, PathLike)):
        raise ValueError(f"{field} must be a filesystem path")
    if not str(value).strip():
        raise ValueError(f"{field} must be a nonblank filesystem path")
    try:
        candidate = Path(value).absolute()
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc
    try:
        for part in reversed((candidate, *candidate.parents)):
            if not os.path.lexists(part):
                continue
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
                raise ValueError(f"{field} contains a link/reparse point: {part}")
            if part != candidate and not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"{field} has a non-directory parent: {part}")
    except OSError as exc:
        raise ValueError(f"cannot inspect {field}: {exc}") from exc
    return candidate


def _path(value: object, *, field: str) -> Path:
    candidate = _unresolved_path(value, field=field)
    try:
        return candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"invalid {field}") from exc


def _project_report_path(value: object) -> Path:
    target = _path(value, field="report path")
    workspace = _path(WORKSPACE_ROOT, field="workspace root")
    if target == workspace or not target.is_relative_to(workspace):
        raise ValueError("report path must be inside the project workspace")
    return target


def _regular_file(path: Path, *, field: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {field} {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{field} must be an independent regular file, not a link")


def _expected_ids(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or value != FIRST_SWEEP_BATCH_1_UNIT_IDS:
        raise ValueError(
            "expected_unit_ids must be the exact frozen first-batch tuple "
            f"{FIRST_SWEEP_BATCH_1_UNIT_IDS!r}"
        )
    return value


def _source_pin(source: object, expected_type: type, *, field: str) -> tuple[str, str]:
    if type(source) is not expected_type:
        raise ValueError(f"{field} must be exact {expected_type.__name__}")
    _path(source.path, field=f"{field}.path")
    commit = _hex(source.expected_git_commit, length=40, field=f"{field}.expected_git_commit")
    execution = _hex(
        source.expected_execution_digest,
        length=64,
        field=f"{field}.expected_execution_digest",
    )
    return commit, execution


def _condition_pins(conditions: object) -> list[tuple[tuple[str, str], ...]]:
    if type(conditions) is not tuple or len(conditions) != 3:
        raise ValueError("conditions must be an exact three-item tuple")
    pins: list[tuple[tuple[str, str], ...]] = []
    for position, condition in enumerate(conditions):
        if type(condition) is not SweepRepairCondition:
            raise ValueError(
                f"condition {position} must be exact SweepRepairCondition"
            )
        pins.append(
            (
                _source_pin(
                    condition.baseline,
                    SweepBaselineSource,
                    field=f"conditions[{position}].baseline",
                ),
                _source_pin(
                    condition.data_repair,
                    PairedRepairSource,
                    field=f"conditions[{position}].data_repair",
                ),
                _source_pin(
                    condition.model_repair,
                    PairedRepairSource,
                    field=f"conditions[{position}].model_repair",
                ),
            )
        )
    if len({_canonical(pin) for pin in pins}) != 3:
        raise ValueError("duplicate independently supplied sweep source condition")
    return pins


def _source_contract(source: object) -> tuple[SourceBoundSweepLabel, Path, list]:
    if type(source) is not SourceBoundSweepLabel:
        raise ValueError(
            "every label must be exact SourceBoundSweepLabel; raw label dictionaries "
            "and bare paths are refused"
        )
    if type(source.unit) is not UnitSpec:
        raise ValueError("source unit must be exact UnitSpec")
    unit_id = Config(unit=source.unit).unit_id
    if unit_id != FIRST_SWEEP_BATCH_1_UNIT_ID:
        raise ValueError(
            "source unit is not exact first-sweep batch-1 unit "
            f"{FIRST_SWEEP_BATCH_1_UNIT_ID}"
        )
    path = _path(source.path, field="label path")
    _regular_file(path, field="label path")
    return source, path, _condition_pins(source.conditions)


def _record_source_row(
    source: SourceBoundSweepLabel,
    *,
    path: Path,
    independent_pins: list[tuple[tuple[str, str], ...]],
) -> tuple[dict[str, Any], object]:
    before = sha256_file(path)
    try:
        record = load_ordinary_sweep_label_evidence(
            path,
            unit=source.unit,
            conditions=source.conditions,
        )
    except (OSError, ValueError) as exc:
        raise ValueError(f"invalid first-sweep label source {path}: {exc}") from exc
    after = sha256_file(path)
    if before != after:
        raise ValueError("first-sweep label file changed while it was being verified")
    if type(record) is not dict:
        raise ValueError("ordinary-sweep loader must return an exact dictionary")

    unit_id = Config(unit=source.unit).unit_id
    _same(
        record.get("ordinary_sweep_label_evidence_schema_version"),
        ORDINARY_SWEEP_LABEL_EVIDENCE_SCHEMA_VERSION,
        what="ordinary-sweep label schema",
    )
    _same(record.get("unit_id"), unit_id, what="label unit_id")
    _same(record.get("unit"), L._unit_row(source.unit), what="label unit provenance")
    _same(record.get("family"), source.unit.family, what="label family")
    group_id = group_of(source.unit, _BASELINE_STAGE)
    _same(record.get("comparison_group_id"), group_id, what="label comparison group")
    intended = "estimation" if source.unit.family == "estimation" else "hypothesis_class"
    if intended not in INTENDED_CLASSES or tuple(INTENDED_CLASSES) != _INTENDED_CLASSES:
        raise ValueError("intended-class registry differs from Week-8 report schema v1")
    _same(record.get("intended_class"), intended, what="label intended class")
    _same(record.get("stage"), _STAGE, what="label stage")
    _same(record.get("baseline_stage"), _BASELINE_STAGE, what="label baseline stage")
    _same(record.get("seeds"), list(_SEEDS), what="label seeds")

    label = record.get("label")
    expected_label_keys = {
        "unit_id",
        "comparison_group_id",
        "intended_class",
        "data_repair_works",
        "model_repair_works",
        "observed_label",
    }
    if type(label) is not dict or set(label) != expected_label_keys:
        raise ValueError("ordinary-sweep label has invalid exact label schema")
    _same(label["unit_id"], unit_id, what="nested label unit_id")
    _same(label["comparison_group_id"], group_id, what="nested label comparison group")
    _same(label["intended_class"], intended, what="nested label intended class")
    for field in ("data_repair_works", "model_repair_works"):
        if type(label[field]) is not bool:
            raise ValueError(f"nested label {field} must be exact bool")
    observed = label["observed_label"]
    if type(observed) is bool or observed not in _OBSERVED_LABELS:
        raise ValueError("nested observed_label is not an exact registered label")
    _same(
        observed,
        observed_label(label["data_repair_works"], label["model_repair_works"]),
        what="observed label versus repair verdicts",
    )

    record_digest = _hex(record.get("record_digest"), length=64, field="record_digest")
    payload = {key: value for key, value in record.items() if key != "record_digest"}
    if L._digest(payload) != record_digest:
        raise ValueError("ordinary-sweep record_digest does not match verified content")

    runs = record.get("runs")
    if type(runs) is not list or len(runs) != 3:
        raise ValueError("ordinary-sweep label must contain exactly three run rows")
    observed_pins: list[tuple[tuple[str, str], ...]] = []
    source_runs: list[dict[str, Any]] = []
    for row in runs:
        if type(row) is not dict or set(_ARMS + ("seed",)) - set(row):
            raise ValueError("ordinary-sweep run row lacks exact source identities")
        seed = row["seed"]
        if type(seed) is not int or seed not in _SEEDS:
            raise ValueError("ordinary-sweep run row carries wrong seed")
        run_pins: list[tuple[str, str]] = []
        report_arms: dict[str, Any] = {}
        for arm in _ARMS:
            identity = row[arm]
            if type(identity) is not dict:
                raise ValueError(f"ordinary-sweep {arm} identity must be an object")
            commit = _hex(
                identity.get("expected_git_commit"),
                length=40,
                field=f"runs[{seed}].{arm}.expected_git_commit",
            )
            execution = _hex(
                identity.get("execution_digest"),
                length=64,
                field=f"runs[{seed}].{arm}.execution_digest",
            )
            run_pins.append((commit, execution))
            report_arms[arm] = {
                "expected_git_commit": commit,
                "execution_sha256": execution,
            }
        observed_pins.append(tuple(run_pins))
        source_runs.append({"seed": seed, **report_arms})
    if sorted(row["seed"] for row in source_runs) != list(_SEEDS):
        raise ValueError("ordinary-sweep label has duplicate or missing source seed")
    if sorted(_canonical(value) for value in observed_pins) != sorted(
        _canonical(value) for value in independent_pins
    ):
        raise ValueError(
            "ordinary-sweep source hashes differ from independently supplied conditions"
        )
    source_runs.sort(key=lambda row: row["seed"])

    source_row = {
        "unit_id": unit_id,
        "label_path": str(path),
        "label_file_sha256": before,
        "label_record_sha256": record_digest,
        "intended_class": intended,
        "observed_label": observed,
        "runs": source_runs,
        # The complete portable run/source identities remain embedded so the
        # report and retained label bundle form an explicit delivery contract;
        # reduced commit/digest rows above are not the only provenance copy.
        "verified_label_runs": _copy(runs),
    }
    return source_row, observed


def _empty_counts() -> dict[str, int]:
    return {"observed_0": 0, "observed_1": 0, "ambiguous": 0, "undiagnosed": 0}


def _add_label(counts: dict[str, int], value: object) -> None:
    if type(value) is bool:
        raise ValueError("boolean observed label is invalid")
    key = {
        0: "observed_0",
        1: "observed_1",
        "ambiguous": "ambiguous",
        "undiagnosed": "undiagnosed",
    }.get(value)
    if key is None:
        raise ValueError(f"unknown observed label {value!r}")
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
        "exclusion_rate": excluded / attempted if attempted else None,
    }


def _labels(value: object) -> tuple[SourceBoundSweepLabel, ...]:
    if isinstance(value, (str, bytes, PathLike, Mapping)) or not isinstance(
        value, Sequence
    ):
        raise ValueError(
            "labels must be a sequence of exact SourceBoundSweepLabel objects; "
            "raw label dictionaries and bare paths are refused"
        )
    labels = tuple(value)
    if len(labels) != 1:
        raise ValueError("the Week-8 first-sweep report requires exactly one batch-1 label")
    return labels


def _build_report(
    labels: object,
    *,
    expected_unit_ids: object,
) -> dict[str, Any]:
    expected = _expected_ids(expected_unit_ids)
    supplied = _labels(labels)
    contracts = [_source_contract(source) for source in supplied]
    unit_ids = tuple(Config(unit=item[0].unit).unit_id for item in contracts)
    if unit_ids != expected:
        raise ValueError("supplied labels do not exactly cover the frozen first-sweep batch")

    pooled = _empty_counts()
    per_class = {name: _empty_counts() for name in _INTENDED_CLASSES}
    source_rows: list[dict[str, Any]] = []
    for source, path, pins in contracts:
        row, label = _record_source_row(
            source,
            path=path,
            independent_pins=pins,
        )
        source_rows.append(row)
        _add_label(pooled, label)
        _add_label(per_class[row["intended_class"]], label)

    pooled_report = _count_report(pooled)
    class_reports = {
        name: _count_report(per_class[name]) for name in _INTENDED_CLASSES
    }
    excluded = pooled_report["excluded"]
    payload: dict[str, Any] = {
        "week8_sweep_exclusion_schema_version": WEEK8_SWEEP_EXCLUSION_SCHEMA_VERSION,
        "kind": "week8_first_sweep_exclusion_report",
        "batch": {
            "batch_key": FIRST_SWEEP_BATCH_KEY,
            "expected_unit_ids": list(expected),
            "attempted_unit_ids": [row["unit_id"] for row in source_rows],
        },
        "sources": source_rows,
        "source_inventory_sha256": _digest(source_rows),
        "counts": {
            "pooled": pooled_report,
            "per_intended_class": class_reports,
        },
        "surviving_min_n0_n1": min(
            pooled_report["observed_0"], pooled_report["observed_1"]
        ),
        "registered_planning_exclusion_rate": REGISTERED_PLANNING_EXCLUSION_RATE,
        "planning_assumption_missed": excluded > 0,
        "shortfall_before_reserve_count": excluded,
        "shortfall_before_reserve_by_intended_class": {
            name: class_reports[name]["excluded"] for name in _INTENDED_CLASSES
        },
        "reserve_status": RESERVE_STATUS,
        "interpretation": (
            "Exact one-unit batch result; it is not a population exclusion-rate estimate. "
            "No reserve unit was selected, drawn, or run."
        ),
    }
    return {**payload, "report_digest": _digest(payload)}


def summarize_sweep_exclusion(
    labels: Sequence[SourceBoundSweepLabel],
    *,
    expected_unit_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Reopen the exact batch-1 label and return its pre-reserve report."""

    return _copy(_build_report(labels, expected_unit_ids=expected_unit_ids))


def write_sweep_exclusion_report(
    labels: Sequence[SourceBoundSweepLabel],
    *,
    expected_unit_ids: tuple[str, ...],
    path: str | PathLike[str],
) -> dict[str, Any]:
    """Source-reverify and immutably publish the exact Week-8 report."""

    report = _build_report(labels, expected_unit_ids=expected_unit_ids)
    supplied = _labels(labels)
    target = _project_report_path(path)
    source_paths = {_path(source.path, field="label path") for source in supplied}
    if target in source_paths:
        raise ValueError("report path must not replace a source label")
    protected_roots = {source.parent for source in source_paths}
    for source in supplied:
        for condition in source.conditions:
            protected_roots.update(
                _path(item.path, field="fit source path")
                for item in (
                    condition.baseline,
                    condition.data_repair,
                    condition.model_repair,
                )
            )
    output_root = target.parent
    if any(
        output_root == protected
        or output_root.is_relative_to(protected)
        or protected.is_relative_to(output_root)
        for protected in protected_roots
    ):
        raise ValueError("report output root must be disjoint from label/source roots")
    if target.exists() or target.is_symlink():
        _regular_file(target, field="existing report")
    try:
        atomic_write_json(target, report)
    except DivergentTargetError as exc:
        raise ValueError(
            f"{target} already exists with different content; refusing to overwrite "
            "immutable Week-8 exclusion report"
        ) from exc
    return _copy(report)


def load_sweep_exclusion_report(
    path: str | PathLike[str],
    *,
    labels: Sequence[SourceBoundSweepLabel],
    expected_unit_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Reload sources and require the persisted report to equal their result."""

    target = _project_report_path(path)
    _regular_file(target, field="report")
    try:
        stored = read_json(target)
    except DurabilityError as exc:
        raise ValueError(f"cannot load Week-8 exclusion report: {exc}") from exc
    if type(stored) is not dict:
        raise ValueError("Week-8 exclusion report must be an exact JSON object")
    expected = _build_report(labels, expected_unit_ids=expected_unit_ids)
    _same(stored, expected, what="stored Week-8 exclusion report")
    return _copy(expected)
