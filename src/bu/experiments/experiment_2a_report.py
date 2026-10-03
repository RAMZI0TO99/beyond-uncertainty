"""Source-bound Experiment-2A family report and offline replay boundary.

The public writer accepts only exact typed inventories.  It independently
reopens the original and finalized-copy road for all one hundred baseline fits,
all four twenty-seed labels, all sixteen three-seed labels and all 384 label-fit
references.  Every fit road carries caller-fixed commit and execution-digest
pins.  Twenty-seed labels are additionally rederived from both explicit
sixty-fit inventories before either persisted label is accepted. Caller-owned
result dictionaries and directory discovery are never evidence inputs.

The resulting JSON is descriptive.  It retains every seed-level H2 diagnostic,
the two repair analyses, all four observed-label outcomes, and exact source
manifests, but it deliberately leaves both sign consistency and ``h2_verdict``
null.  :func:`load_experiment_2a_report` and
:func:`replay_experiment_2a_report` validate only the immutable report bytes;
they never reopen a fit or label.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .. import constants as K
from ..config import Config, UnitSpec
from ..durable import atomic_write_json, sha256_bytes, sha256_file
from ..models.uncertainty import RATIO_FLOOR
from ..streams import confirmatory_seeds, group_of
from . import h2_diagnostics as H
from . import fit_evidence as F
from . import label_evidence as L
from . import ordinary_label_evidence as O
from .enumerate_units import (
    CANONICAL_PAIRS,
    experiment_2a_units,
    repair_validation_units,
)
from .labels import observed_label


# Bump whenever fields or their scientific meaning change.
EXPERIMENT_2A_REPORT_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = EXPERIMENT_2A_REPORT_SCHEMA_VERSION
REPORT_KIND = "source_bound_experiment_2a_family_report"

_SEEDS = tuple(confirmatory_seeds(K.SEEDS_HYPOTHESIS))
_CONFOUND_LEVELS = tuple(float(value) for value in K.CONFOUND_LEVELS_2A)
_LABEL_VALUES = (0, 1, "ambiguous", "undiagnosed")
_INTENDED_CLASSES = ("estimation", "hypothesis_class")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX12 = re.compile(r"[0-9a-f]{12}")
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PEARSON_UNDEFINED_REASONS = frozenset(
    {
        "fewer_than_two_failure_transitions",
        "constant_error_or_disagreement",
        "numerically_degenerate_centered_vector",
    }
)
if type(RATIO_FLOOR) is not float or RATIO_FLOOR != 1e-6:
    raise RuntimeError("Experiment-2A report requires the registered ratio floor 1e-6")


@dataclass(frozen=True)
class Experiment2AFitSourcePair:
    """One fit reopened from an original and an independent finalized export.

    The commit and execution digest are independent inputs.  Neither copy is
    permitted to attest its own expected values.
    """

    source_path: Path
    copy_path: Path
    expected_git_commit: str
    expected_execution_digest: str


@dataclass(frozen=True)
class Experiment2ARepairConditionSources:
    """The three explicit source pairs for one registered repair-label seed."""

    seed: int
    baseline: Experiment2AFitSourcePair
    data_repair: Experiment2AFitSourcePair
    feature_repair: Experiment2AFitSourcePair


@dataclass(frozen=True)
class Experiment2ABaselineSources:
    """One registered E2A unit and its ordered five baseline source pairs."""

    unit: UnitSpec
    sources: tuple[Experiment2AFitSourcePair, ...]


@dataclass(frozen=True)
class RepairValidationLabelSource:
    """One exact twenty-seed label and copy with explicit paired fit sources."""

    unit: UnitSpec
    source_path: Path
    copy_path: Path
    expected_source_sha256: str
    expected_copy_sha256: str
    conditions: tuple[Experiment2ARepairConditionSources, ...]


@dataclass(frozen=True)
class OrdinaryLabelSource:
    """One exact three-seed label and copy with explicit paired fit sources."""

    unit: UnitSpec
    source_path: Path
    copy_path: Path
    expected_source_sha256: str
    expected_copy_sha256: str
    conditions: tuple[Experiment2ARepairConditionSources, ...]


# Descriptive aliases make the two policies hard to confuse at call sites.
Experiment2ARepairValidationLabelSource = RepairValidationLabelSource
Experiment2AOrdinaryLabelSource = OrdinaryLabelSource


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not strict canonical JSON: {exc}") from exc


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _same(actual: Any, expected: Any, what: str) -> None:
    if _canonical(actual) != _canonical(expected):
        raise ValueError(f"{what} disagrees with the fixed Experiment-2A report")


def _exact_keys(value: Any, expected: set[str], what: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{what} must be an exact JSON object")
    if set(value) != expected:
        raise ValueError(
            f"{what} keys are not exact; missing={sorted(expected - set(value))}, "
            f"extra={sorted(set(value) - expected)}"
        )
    return value


def _digest(value: Any, *, length: int, what: str) -> str:
    pattern = _HEX64 if length == 64 else _HEX40 if length == 40 else _HEX12
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError(f"{what} must be exact lowercase {length}-hex")
    return value


def _finite(value: Any, what: str, *, nonnegative: bool = False) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(f"{what} must be an exact finite float")
    if nonnegative and value < 0:
        raise ValueError(f"{what} must be nonnegative")
    return value


def _exact_int(value: Any, what: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise ValueError(f"{what} must be an exact integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{what} must be at least {minimum}")
    return value


def _is_link_or_reparse(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse)


def _lexical_absolute(path: Path, *, what: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(f"{what} must be an explicit absolute Path")
    if any(part in (".", "..") for part in path.parts[1:]):
        raise ValueError(f"{what} must not contain lexical traversal components")
    return Path(os.path.abspath(path))


def _under_project(path: Path, *, what: str) -> None:
    root = Path(os.path.abspath(_PROJECT_ROOT))
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{what} must stay inside project root {root}") from exc


def _reject_lexical_links(path: Path, *, what: str) -> None:
    """Reject symlink/reparse components before any call to ``resolve``."""

    root = Path(os.path.abspath(_PROJECT_ROOT))
    _under_project(path, what=what)
    current = root
    components = ((),) + tuple((part,) for part in path.relative_to(root).parts)
    for component in components:
        if component:
            current = current / component[0]
        try:
            info = current.lstat()
        except FileNotFoundError:
            # Descendants cannot exist once their first absent ancestor is met.
            break
        except OSError as exc:
            raise ValueError(f"cannot inspect {what} component {current}: {exc}") from exc
        if _is_link_or_reparse(info):
            raise ValueError(f"{what} contains a symlink or reparse point: {current}")


def _project_path(
    path: Path,
    *,
    what: str,
    kind: str | None = None,
    must_exist: bool = False,
) -> Path:
    lexical = _lexical_absolute(path, what=what)
    _under_project(lexical, what=what)
    _reject_lexical_links(lexical, what=what)
    try:
        resolved = lexical.resolve(strict=must_exist)
    except OSError as exc:
        raise ValueError(f"cannot resolve {what} {lexical}: {exc}") from exc
    _under_project(resolved, what=what)
    # Repeat after resolution to narrow the check/use window and catch a changed
    # existing component before the caller opens it.
    _reject_lexical_links(lexical, what=what)
    if kind is not None and resolved.exists():
        if kind == "file":
            try:
                info = lexical.lstat()
            except OSError as exc:
                raise ValueError(f"cannot inspect {what} {lexical}: {exc}") from exc
            if _is_link_or_reparse(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError(f"{what} must be an independent regular file")
        elif kind == "directory" and not resolved.is_dir():
            raise ValueError(f"{what} must be a directory")
        elif kind not in ("file", "directory"):
            raise ValueError(f"unknown path kind {kind!r}")
    elif must_exist:
        raise ValueError(f"{what} does not exist")
    return resolved


def _manifest_project_path(value: Any, *, what: str) -> Path:
    """Validate a recorded path lexically without reopening scientific sources."""

    if type(value) is not str or not value:
        raise ValueError(f"{what} must be a nonblank absolute project-local path")
    path = _lexical_absolute(Path(value), what=what)
    _under_project(path, what=what)
    return path


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _independent_pair(
    left: Path, right: Path, *, what: str, inspect_filesystem: bool = True
) -> None:
    if _overlap(left, right):
        raise ValueError(f"{what} original and independent copy must be disjoint")
    if inspect_filesystem and left.exists() and right.exists():
        try:
            if os.path.samefile(left, right):
                raise ValueError(f"{what} original and copy resolve to the same object")
        except OSError as exc:
            raise ValueError(f"cannot compare {what} original/copy: {exc}") from exc


def _unit_id(unit: UnitSpec) -> str:
    return Config(unit=unit).unit_id


def _registered_units() -> tuple[UnitSpec, ...]:
    pair_index = {pair: index for index, pair in enumerate(CANONICAL_PAIRS)}
    units = tuple(experiment_2a_units())
    if len(units) != 20 or len({_unit_id(unit) for unit in units}) != 20:
        raise ValueError("registered Experiment-2A twenty-unit inventory drifted")
    return tuple(
        sorted(
            units,
            key=lambda unit: (
                pair_index[(unit.causal_attribute, unit.layout)],
                float(unit.confound_rate),
            ),
        )
    )


def _validation_unit_ids() -> set[str]:
    registered = _registered_units()
    exp2a = {_unit_id(unit) for unit in registered}
    exact_shape_uniform = {
        _unit_id(unit)
        for unit in registered
        if unit.causal_attribute == "shape" and unit.layout == "uniform"
    }
    result = {
        _unit_id(unit)
        for unit in repair_validation_units()
        if _unit_id(unit) in exp2a
    }
    if len(result) != 4 or result != exact_shape_uniform:
        raise ValueError("registered Experiment-2A twenty-seed label inventory drifted")
    return result


def _unit_row(unit: UnitSpec) -> dict[str, Any]:
    return dict(Config(unit=unit).to_dict()["unit"])


def _fit_pair_paths(
    pair: Experiment2AFitSourcePair, *, what: str
) -> tuple[Path, Path, str, str]:
    if type(pair) is not Experiment2AFitSourcePair:
        raise ValueError(f"{what} must be an exact Experiment2AFitSourcePair")
    commit = _digest(pair.expected_git_commit, length=40, what=f"{what} expected commit")
    execution = _digest(
        pair.expected_execution_digest,
        length=64,
        what=f"{what} expected execution digest",
    )
    source = _project_path(
        pair.source_path,
        what=f"{what} original source",
        kind="directory",
        must_exist=True,
    )
    copy = _project_path(
        pair.copy_path,
        what=f"{what} independent copy",
        kind="directory",
        must_exist=True,
    )
    _independent_pair(source, copy, what=what)
    return source, copy, commit, execution


def _verify_label_fit_pair(
    pair: Experiment2AFitSourcePair,
    *,
    unit: UnitSpec,
    arm: str,
    seed: int,
    role: str,
) -> tuple[dict[str, Any], F.VerifiedFitEvidence, F.VerifiedFitEvidence]:
    what = f"label seed {seed} {role} fit"
    source_path, copy_path, commit, execution = _fit_pair_paths(pair, what=what)
    verified: list[F.VerifiedFitEvidence] = []
    for name, path in (("original", source_path), ("independent copy", copy_path)):
        try:
            fit = F.load_fit_evidence(path, expected_git_commit=commit)
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot verify {what} {name} at {path}: {exc}") from exc
        if type(fit) is not F.VerifiedFitEvidence:
            raise ValueError(f"{what} loader returned a non-exact VerifiedFitEvidence")
        if (
            Path(fit.fit_dir).resolve() != path
            or fit.unit != unit
            or fit.arm != arm
            or fit.seed != seed
            or fit.execution_digest != execution
        ):
            raise ValueError(f"{what} {name} disagrees with its independent pins")
        verified.append(fit)
    left, right = verified
    for field in (
        "unit", "arm", "seed", "roles", "execution_stage", "unit_id",
        "config_id", "fit_id", "execution_run_id", "execution_digest",
        "evaluation_pool_digest", "n_train", "ensemble_size",
    ):
        if getattr(left, field) != getattr(right, field):
            raise ValueError(f"{what} original/copy disagree on {field}")
    return (
        {
            "seed": seed,
            "role": role,
            "fit_id": left.fit_id,
            "source_path": str(source_path),
            "copy_path": str(copy_path),
            "expected_git_commit": commit,
            "expected_execution_digest": execution,
            "source_verified_execution_digest": left.execution_digest,
            "copy_verified_execution_digest": right.execution_digest,
        },
        left,
        right,
    )


def _label_file_pair(
    source_path: object,
    copy_path: object,
    expected_source_sha256: object,
    expected_copy_sha256: object,
    *,
    what: str,
) -> tuple[Path, Path, str, str]:
    if not isinstance(source_path, Path) or not isinstance(copy_path, Path):
        raise ValueError(f"{what} paths must be explicit absolute Paths")
    source_sha = _digest(
        expected_source_sha256, length=64, what=f"{what} original expected SHA-256"
    )
    copy_sha = _digest(
        expected_copy_sha256, length=64, what=f"{what} copy expected SHA-256"
    )
    source = _project_path(
        source_path, what=f"{what} original", kind="file", must_exist=True
    )
    copy = _project_path(
        copy_path, what=f"{what} independent copy", kind="file", must_exist=True
    )
    _independent_pair(source, copy, what=what)
    if source_sha != copy_sha:
        raise ValueError(f"{what} original/copy independently supplied SHA-256 values differ")
    if sha256_file(source) != source_sha or sha256_file(copy) != copy_sha:
        raise ValueError(f"{what} bytes do not match their independently supplied SHA-256 values")
    if source.read_bytes() != copy.read_bytes():
        raise ValueError(f"{what} original and independent copy bytes differ")
    return source, copy, source_sha, copy_sha


def _label_condition_inventory(
    conditions: Sequence[Experiment2ARepairConditionSources],
    *,
    unit: UnitSpec,
    seeds: tuple[int, ...],
    ordinary: bool,
) -> tuple[tuple[Any, ...], tuple[Any, ...], list[dict[str, Any]]]:
    if type(conditions) is not tuple or len(conditions) != len(seeds):
        raise ValueError(f"label requires an ordered tuple of exactly {len(seeds)} source-pair conditions")
    originals: list[Any] = []
    copies: list[Any] = []
    manifest: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for seed, condition in zip(seeds, conditions, strict=True):
        if type(condition) is not Experiment2ARepairConditionSources or condition.seed != seed:
            raise ValueError("label condition inventory must be exact and ordered by registered seed")
        original_by_arm: dict[str, Any] = {}
        copy_by_arm: dict[str, Any] = {}
        for field, arm, role in (
            ("baseline", "baseline", "baseline"),
            ("data_repair", "data_repair", "data_repair"),
            ("feature_repair", "feature_repair", "feature_repair"),
        ):
            pair = getattr(condition, field)
            row, original_fit, copy_fit = _verify_label_fit_pair(
                pair, unit=unit, arm=arm, seed=seed, role=role
            )
            paths = (Path(row["source_path"]), Path(row["copy_path"]))
            if any(path in seen_paths for path in paths):
                raise ValueError("duplicate physical path in label fit source-pair inventory")
            seen_paths.update(paths)
            manifest.append(row)
            if ordinary:
                original_by_arm[field] = O.OrdinaryFitSource(
                    paths[0], row["expected_git_commit"], row["expected_execution_digest"]
                )
                copy_by_arm[field] = O.OrdinaryFitSource(
                    paths[1], row["expected_git_commit"], row["expected_execution_digest"]
                )
            else:
                # Passing the already verified object is only a convenience;
                # label_evidence deliberately reloads its fit_dir at consumption.
                original_by_arm[field] = original_fit
                copy_by_arm[field] = copy_fit
        originals.append(
            O.OrdinaryRepairCondition(
                original_by_arm["baseline"],
                original_by_arm["data_repair"],
                original_by_arm["feature_repair"],
            )
            if ordinary
            else L.PersistedRepairCondition(
                original_by_arm["baseline"],
                original_by_arm["data_repair"],
                original_by_arm["feature_repair"],
            )
        )
        copies.append(
            O.OrdinaryRepairCondition(
                copy_by_arm["baseline"],
                copy_by_arm["data_repair"],
                copy_by_arm["feature_repair"],
            )
            if ordinary
            else L.PersistedRepairCondition(
                copy_by_arm["baseline"],
                copy_by_arm["data_repair"],
                copy_by_arm["feature_repair"],
            )
        )
    return tuple(originals), tuple(copies), manifest


def _mean_sd(values: Sequence[float]) -> tuple[float, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (5,) or not np.isfinite(array).all() or np.any(array < 0):
        raise ValueError("a unit ratio summary requires five finite nonnegative values")
    scale = float(array.max())
    scaled = array / scale if scale else array
    mean = float(scale * scaled.mean())
    sd = float(scale * scaled.std(ddof=1))
    if not math.isfinite(mean) or not math.isfinite(sd):
        raise ValueError("unit ratio mean/sample SD is not finite")
    return mean, sd


def _baseline_inventory(
    entries: Sequence[Experiment2ABaselineSources],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if type(entries) not in (tuple, list) or len(entries) != 20:
        raise ValueError("supply exactly twenty typed Experiment-2A baseline groups")
    expected = {_unit_id(unit): unit for unit in _registered_units()}
    seen: set[str] = set()
    paths: set[Path] = set()
    diagnostics: dict[str, dict[str, Any]] = {}
    manifest: list[dict[str, Any]] = []
    for entry in entries:
        if type(entry) is not Experiment2ABaselineSources:
            raise ValueError("baseline inventory items must be exact Experiment2ABaselineSources")
        if type(entry.unit) is not UnitSpec:
            raise ValueError("baseline inventory unit must be an exact UnitSpec")
        unit_id = _unit_id(entry.unit)
        if unit_id not in expected or entry.unit != expected[unit_id] or unit_id in seen:
            raise ValueError("baseline inventory has an unknown, changed, or duplicate E2A unit")
        seen.add(unit_id)
        if type(entry.sources) is not tuple or len(entry.sources) != 5:
            raise ValueError("each E2A unit requires an ordered tuple of five baseline source pairs")
        originals: list[H.BaselineDiagnosticSource] = []
        copies: list[H.BaselineDiagnosticSource] = []
        source_rows: list[tuple[Path, Path, str, str]] = []
        for pair in entry.sources:
            source_path, copy_path, commit, execution = _fit_pair_paths(
                pair, what="baseline diagnostic fit"
            )
            if source_path in paths or copy_path in paths:
                raise ValueError("duplicate path in baseline source-pair inventory")
            paths.update((source_path, copy_path))
            originals.append(H.BaselineDiagnosticSource(source_path, commit, execution))
            copies.append(H.BaselineDiagnosticSource(copy_path, commit, execution))
            source_rows.append((source_path, copy_path, commit, execution))
        result = H.condition_failure_diagnostics(tuple(originals), unit=entry.unit)
        copied = H.condition_failure_diagnostics(tuple(copies), unit=entry.unit)
        if type(result) is not dict or type(copied) is not dict:
            raise ValueError("H2 diagnostic loader must return exact result objects")
        if _canonical(result) != _canonical(copied):
            raise ValueError("baseline original/copy diagnostics are not byte-equivalent records")
        diagnostics[unit_id] = result
        per_seed = result.get("per_seed")
        copied_per_seed = copied.get("per_seed")
        if type(per_seed) is not list or len(per_seed) != 5:
            raise ValueError("H2 diagnostic result lacks the complete five-seed rows")
        if type(copied_per_seed) is not list or len(copied_per_seed) != 5:
            raise ValueError("copied H2 diagnostic result lacks the complete five-seed rows")
        for seed, pins, row, copied_row in zip(
            _SEEDS, source_rows, per_seed, copied_per_seed, strict=True
        ):
            if type(row) is not dict or type(copied_row) is not dict:
                raise ValueError("H2 per-seed diagnostics must be exact objects")
            source_path, copy_path, commit, source_digest = pins
            if (
                row.get("unit_id") != unit_id
                or row.get("seed") != seed
                or row.get("expected_git_commit") != commit
                or row.get("execution_digest") != source_digest
                or _canonical(row) != _canonical(copied_row)
            ):
                raise ValueError("diagnostic output is not bound to both explicit source copies")
            manifest.append(
                {
                    "unit_id": unit_id,
                    "seed": seed,
                    "source_path": str(source_path),
                    "copy_path": str(copy_path),
                    "expected_git_commit": commit,
                    "expected_execution_digest": source_digest,
                    "fit_id": row.get("fit_id"),
                    "source_verified_execution_digest": row.get("execution_digest"),
                    "copy_verified_execution_digest": copied_row.get("execution_digest"),
                }
            )
    if seen != set(expected) or len(manifest) != 100:
        raise ValueError("baseline inventory is not the exact registered twenty-by-five grid")
    manifest.sort(key=lambda row: (row["unit_id"], row["seed"]))
    return diagnostics, manifest


def _record_fit_rows(record: Mapping[str, Any], *, label_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in record["runs"]:
        seed = run["seed"]
        for record_key, role in (
            ("baseline", "baseline"),
            ("data_repair", "data_repair"),
            ("model_repair", "feature_repair"),
        ):
            item = run[record_key]
            path = L._resolve_portable_fit_path(
                item["fit_evidence_path"], label_path=label_path
            )
            rows.append(
                {
                    "seed": seed,
                    "role": role,
                    "fit_id": item["fit_id"],
                    "path": str(path),
                    "execution_digest": item["fit_evidence_digest"],
                    "expected_git_commit": item.get("expected_git_commit"),
                }
            )
    return rows


def _bind_record_fit_rows(
    record: Mapping[str, Any],
    *,
    label_path: Path,
    fit_rows: Sequence[dict[str, Any]],
    use_copy: bool,
    ordinary: bool,
) -> None:
    recorded = _record_fit_rows(record, label_path=label_path)
    recorded_by_key = {(row["seed"], row["role"]): row for row in recorded}
    if len(recorded_by_key) != len(recorded) or len(recorded) != len(fit_rows):
        raise ValueError("label record fit inventory is duplicate or incomplete")
    for expected in fit_rows:
        key = (expected["seed"], expected["role"])
        actual = recorded_by_key.get(key)
        if actual is None:
            raise ValueError("label record omits an independently supplied fit source")
        expected_path = expected["copy_path" if use_copy else "source_path"]
        if (
            actual["fit_id"] != expected["fit_id"]
            or actual["path"] != expected_path
            or actual["execution_digest"] != expected["expected_execution_digest"]
        ):
            raise ValueError("label record is not bound to its explicit original/copy fit source")
        if ordinary:
            if actual["expected_git_commit"] != expected["expected_git_commit"]:
                raise ValueError("ordinary label record is not bound to the independent commit pin")
        elif actual["expected_git_commit"] is not None:
            raise ValueError("twenty-seed label schema unexpectedly self-attests a commit")


def _load_validation_label(source: RepairValidationLabelSource) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(source.unit) is not UnitSpec or type(source.conditions) is not tuple:
        raise ValueError("twenty-seed label source requires an exact unit and condition tuple")
    source_path, copy_path, source_sha, copy_sha = _label_file_pair(
        source.source_path,
        source.copy_path,
        source.expected_source_sha256,
        source.expected_copy_sha256,
        what="twenty-seed label",
    )
    originals, copies, fit_rows = _label_condition_inventory(
        source.conditions,
        unit=source.unit,
        seeds=tuple(range(1000, 1020)),
        ordinary=False,
    )
    explicit_source = L._derive_label_evidence(originals, label_path=source_path)
    explicit_copy = L._derive_label_evidence(copies, label_path=copy_path)
    loaded_source = L.load_label_evidence(source_path)
    loaded_copy = L.load_label_evidence(copy_path)
    canonical = L._canonical_json(explicit_source)
    if any(
        L._canonical_json(value) != canonical
        for value in (explicit_copy, loaded_source, loaded_copy)
    ):
        raise ValueError("twenty-seed label/copy do not match both explicit fit inventories")
    _bind_record_fit_rows(
        loaded_source,
        label_path=source_path,
        fit_rows=fit_rows,
        use_copy=False,
        ordinary=False,
    )
    _bind_record_fit_rows(
        loaded_copy,
        label_path=copy_path,
        fit_rows=fit_rows,
        use_copy=True,
        ordinary=False,
    )
    if sha256_file(source_path) != source_sha or sha256_file(copy_path) != copy_sha:
        raise ValueError("twenty-seed label or copy changed during verification")
    return loaded_source, {
        "unit_id": _unit_id(source.unit),
        "procedure": "repair_validation_20_seed",
        "source_path": str(source_path),
        "copy_path": str(copy_path),
        "source_sha256": source_sha,
        "copy_sha256": copy_sha,
        "record_digest": loaded_source["record_digest"],
        "seeds": list(loaded_source["seeds"]),
        "fit_sources": fit_rows,
    }


def _load_ordinary_label(source: OrdinaryLabelSource) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(source.unit) is not UnitSpec or type(source.conditions) is not tuple:
        raise ValueError("ordinary label source requires an exact unit and condition tuple")
    source_path, copy_path, source_sha, copy_sha = _label_file_pair(
        source.source_path,
        source.copy_path,
        source.expected_source_sha256,
        source.expected_copy_sha256,
        what="ordinary label",
    )
    originals, copies, fit_rows = _label_condition_inventory(
        source.conditions,
        unit=source.unit,
        seeds=tuple(range(1000, 1003)),
        ordinary=True,
    )
    loaded_source = O.load_ordinary_label_evidence(
        source_path, unit=source.unit, conditions=originals
    )
    loaded_copy = O.load_ordinary_label_evidence(
        copy_path, unit=source.unit, conditions=copies
    )
    if L._canonical_json(loaded_source) != L._canonical_json(loaded_copy):
        raise ValueError("ordinary label original/copy records disagree")
    _bind_record_fit_rows(
        loaded_source,
        label_path=source_path,
        fit_rows=fit_rows,
        use_copy=False,
        ordinary=True,
    )
    _bind_record_fit_rows(
        loaded_copy,
        label_path=copy_path,
        fit_rows=fit_rows,
        use_copy=True,
        ordinary=True,
    )
    if sha256_file(source_path) != source_sha or sha256_file(copy_path) != copy_sha:
        raise ValueError("ordinary label or copy changed during verification")
    return loaded_source, {
        "unit_id": _unit_id(source.unit),
        "procedure": "ordinary_canonical_three_seed_v1",
        "source_path": str(source_path),
        "copy_path": str(copy_path),
        "source_sha256": source_sha,
        "copy_sha256": copy_sha,
        "record_digest": loaded_source["record_digest"],
        "seeds": list(loaded_source["seeds"]),
        "fit_sources": fit_rows,
    }


def _label_inventory(
    validation: Sequence[RepairValidationLabelSource],
    ordinary: Sequence[OrdinaryLabelSource],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if type(validation) not in (tuple, list) or len(validation) != 4:
        raise ValueError("supply exactly four typed twenty-seed Experiment-2A labels")
    if type(ordinary) not in (tuple, list) or len(ordinary) != 16:
        raise ValueError("supply exactly sixteen typed ordinary Experiment-2A labels")
    expected = {_unit_id(unit): unit for unit in _registered_units()}
    validation_ids = _validation_unit_ids()
    records: dict[str, dict[str, Any]] = {}
    validation_manifest: list[dict[str, Any]] = []
    ordinary_manifest: list[dict[str, Any]] = []
    label_paths: set[Path] = set()

    for source in validation:
        if type(source) is not RepairValidationLabelSource:
            raise ValueError("twenty-seed labels must use RepairValidationLabelSource")
        unit_id = _unit_id(source.unit) if type(source.unit) is UnitSpec else ""
        if unit_id not in validation_ids or source.unit != expected.get(unit_id) or unit_id in records:
            raise ValueError("unknown, changed, duplicate, or wrong-policy twenty-seed E2A unit")
        supplied_paths = (
            source.source_path if isinstance(source.source_path, Path) else None,
            source.copy_path if isinstance(source.copy_path, Path) else None,
        )
        if any(path is not None and path in label_paths for path in supplied_paths):
            raise ValueError("duplicate label original/copy path")
        record, manifest = _load_validation_label(source)
        for key in ("source_path", "copy_path"):
            path = Path(manifest[key])
            if path in label_paths:
                raise ValueError("duplicate resolved label original/copy path")
            label_paths.add(path)
        records[unit_id] = record
        validation_manifest.append(manifest)

    for source in ordinary:
        if type(source) is not OrdinaryLabelSource:
            raise ValueError("ordinary labels must use OrdinaryLabelSource")
        unit_id = _unit_id(source.unit) if type(source.unit) is UnitSpec else ""
        if (
            unit_id not in expected
            or unit_id in validation_ids
            or source.unit != expected.get(unit_id)
            or unit_id in records
        ):
            raise ValueError("unknown, changed, duplicate, or wrong-policy ordinary E2A unit")
        supplied_paths = (
            source.source_path if isinstance(source.source_path, Path) else None,
            source.copy_path if isinstance(source.copy_path, Path) else None,
        )
        if any(path is not None and path in label_paths for path in supplied_paths):
            raise ValueError("duplicate label original/copy path")
        record, manifest = _load_ordinary_label(source)
        for key in ("source_path", "copy_path"):
            path = Path(manifest[key])
            if path in label_paths:
                raise ValueError("duplicate resolved label original/copy path")
            label_paths.add(path)
        records[unit_id] = record
        ordinary_manifest.append(manifest)

    if set(records) != set(expected):
        raise ValueError("label inventory does not cover exactly all twenty E2A units")
    validation_manifest.sort(key=lambda row: row["unit_id"])
    ordinary_manifest.sort(key=lambda row: row["unit_id"])
    if sum(len(row["fit_sources"]) for row in validation_manifest + ordinary_manifest) != 384:
        raise ValueError("twenty E2A labels must bind exactly 384 fit references")
    return records, validation_manifest, ordinary_manifest


def _repair_row(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("verified repair acceptance must be an object")
    fields = (
        "effect", "ci_low", "ci_high", "relative_reduction", "passed",
        "reason", "method", "converged", "n_transitions", "n_seeds",
        "n_episodes", "unrepaired_mean", "min_practical_effect", "confidence",
    )
    if set(value) != set(fields):
        raise ValueError("verified repair acceptance fields are not the exact schema")
    result = {name: value[name] for name in fields}
    for name in (
        "effect", "ci_low", "ci_high", "relative_reduction", "unrepaired_mean",
        "min_practical_effect", "confidence",
    ):
        if result[name] is not None:
            result[name] = float(result[name])
    return result


def _label_row(record: Mapping[str, Any], *, unit: UnitSpec, procedure: str) -> dict[str, Any]:
    unit_id = _unit_id(unit)
    expected_intended = "estimation" if unit.family == "estimation" else "hypothesis_class"
    label = record.get("label")
    if not isinstance(label, Mapping):
        raise ValueError("verified label lacks its exact assignment")
    if (
        record.get("unit_id") != unit_id
        or record.get("unit") != _unit_row(unit)
        or record.get("family") != "missing_feature"
        or record.get("comparison_group_id") != group_of(unit, "exp2a")
        or record.get("intended_class") != expected_intended
        or record.get("model_repair_arm") != "feature_repair"
        or label.get("unit_id") != unit_id
        or label.get("comparison_group_id") != group_of(unit, "exp2a")
        or label.get("intended_class") != expected_intended
    ):
        raise ValueError("verified label is not bound to the registered E2A unit")
    data = _repair_row(record["acceptance"]["data_repair"])
    feature = _repair_row(record["acceptance"]["model_repair"])
    observed = label.get("observed_label")
    if type(observed) is bool or observed not in _LABEL_VALUES:
        raise ValueError("verified label has an invalid observed-label value")
    if (
        type(label.get("data_repair_works")) is not bool
        or type(label.get("model_repair_works")) is not bool
        or label["data_repair_works"] is not data["passed"]
        or label["model_repair_works"] is not feature["passed"]
        or observed != observed_label(data["passed"], feature["passed"])
    ):
        raise ValueError("repair effects, pass states, and observed label disagree")
    return {
        "procedure": procedure,
        "label_stage": record["stage"],
        "label_seed_count": len(record["seeds"]),
        "label_record_digest": record["record_digest"],
        "comparison_group_id": record["comparison_group_id"],
        "intended_class": record["intended_class"],
        "observed_label": observed,
        "data_repair_works": label["data_repair_works"],
        "feature_repair_works": label["model_repair_works"],
        "data_repair": data,
        "feature_repair": feature,
    }


def _counts(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    def one(selected: Sequence[dict[str, Any]]) -> dict[str, Any]:
        counts = {
            "observed_0": sum(row["repair_evidence"]["observed_label"] == 0 for row in selected),
            "observed_1": sum(row["repair_evidence"]["observed_label"] == 1 for row in selected),
            "ambiguous": sum(row["repair_evidence"]["observed_label"] == "ambiguous" for row in selected),
            "undiagnosed": sum(row["repair_evidence"]["observed_label"] == "undiagnosed" for row in selected),
        }
        attempted = len(selected)
        excluded = counts["ambiguous"] + counts["undiagnosed"]
        return {
            "attempted": attempted,
            **counts,
            "decidable": counts["observed_0"] + counts["observed_1"],
            "excluded": excluded,
            "exclusion_rate": (excluded / attempted) if attempted else None,
        }

    return {
        "pooled": one(rows),
        "by_intended_class": {
            intended: one([
                row for row in rows
                if row["repair_evidence"]["intended_class"] == intended
            ])
            for intended in _INTENDED_CLASSES
        },
    }


def _scheduled_checks(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    data_passed = sum(row["repair_evidence"]["data_repair_works"] for row in rows)
    feature_passed = sum(row["repair_evidence"]["feature_repair_works"] for row in rows)
    failure_rows = sum(
        seed["n_failure"] > 0
        for row in rows for seed in row["h2_diagnostics"]["per_seed"]
    )
    return {
        "largest_data_size": max(K.DATA_SIZES),
        "strict_failure_set": {
            "unit_seed_rows_with_failures": failure_rows,
            "total_unit_seed_rows": 100,
            "all_unit_seed_rows_have_failures": failure_rows == 100,
            "interpretation": (
                "descriptive strict-failure prevalence only; failure-set mean error "
                "is not used as circular evidence that error is high"
            ),
        },
        "ten_times_data_repair": {
            "passed_units": data_passed,
            "failed_units": 20 - data_passed,
            "assumed_outcome": False,
        },
        "feature_restoration": {
            "passed_units": feature_passed,
            "failed_units": 20 - feature_passed,
            "assumed_outcome": False,
        },
        "low_ratio": {
            "absolute_cutoff": None,
            "adjudicated": False,
            "reason": "no registered absolute low-ratio threshold",
        },
        "data_size_sweep_claim_made": False,
    }


def _sign_consistency_evidence_gate(
    rows: Sequence[dict[str, Any]], source_manifests: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind the complete family inventory before any future eligible-row adapter.

    This is deliberately not an adapter to ``H2SeedUnitRatio``.  It proves that
    ambiguous and undiagnosed units were present at the evidence boundary, so a
    later observed-class filter cannot make an omitted unit look like complete
    provenance.
    """

    labels = [
        {
            "unit_id": row["unit_id"],
            "label_record_digest": row["repair_evidence"]["label_record_digest"],
            "observed_label": row["repair_evidence"]["observed_label"],
        }
        for row in rows
    ]
    diagnostics = [
        {
            "unit_id": row["unit_id"],
            "seed": seed["seed"],
            "fit_id": seed["fit_id"],
            "execution_digest": seed["execution_digest"],
            "ratio_of_means": seed["ratio_of_means"],
            "failure_mask_sha256": seed["failure_mask_sha256"],
        }
        for row in rows
        for seed in row["h2_diagnostics"]["per_seed"]
    ]
    payload = {
        "registered_unit_ids": [row["unit_id"] for row in rows],
        "labels": labels,
        "diagnostics": diagnostics,
        "source_inventory_sha256": source_manifests["source_inventory_sha256"],
    }
    return {
        "registered_unit_count": len(rows),
        "label_record_count": len(labels),
        "diagnostic_row_count": len(diagnostics),
        "ambiguous_and_undiagnosed_retained": True,
        "label_record_digests_bound": True,
        "source_pins_bound": True,
        "ratio_and_failure_mask_digests_bound": True,
        "caller_constructed_eligible_rows_accepted": False,
        "eligible_row_adapter_invoked": False,
        "sign_consistency_invoked": False,
        "complete_inventory_sha256": _hash(payload),
    }


def _build(
    baselines: Sequence[Experiment2ABaselineSources],
    validation_labels: Sequence[RepairValidationLabelSource],
    ordinary_labels: Sequence[OrdinaryLabelSource],
) -> dict[str, Any]:
    diagnostics, baseline_manifest = _baseline_inventory(baselines)
    labels, validation_manifest, ordinary_manifest = _label_inventory(
        validation_labels, ordinary_labels
    )
    baseline_by_cell = {
        (row["unit_id"], row["seed"]): row for row in baseline_manifest
    }
    label_manifest_by_unit = {
        row["unit_id"]: row for row in validation_manifest + ordinary_manifest
    }

    units: list[dict[str, Any]] = []
    for index, unit in enumerate(_registered_units()):
        unit_id = _unit_id(unit)
        procedure = label_manifest_by_unit[unit_id]["procedure"]
        repair = _label_row(labels[unit_id], unit=unit, procedure=procedure)
        diagnostic = json.loads(json.dumps(diagnostics[unit_id]))
        for seed_row in diagnostic["per_seed"]:
            seed_row["observed_repair_label"] = repair["observed_label"]
            source = baseline_by_cell[(unit_id, seed_row["seed"])]
            matching = [
                row for row in label_manifest_by_unit[unit_id]["fit_sources"]
                if row["role"] == "baseline" and row["seed"] == seed_row["seed"]
            ]
            if matching and (
                len(matching) != 1
                or matching[0]["fit_id"] != source["fit_id"]
                or matching[0]["expected_execution_digest"]
                != source["source_verified_execution_digest"]
                or matching[0]["expected_git_commit"] != source["expected_git_commit"]
                or matching[0]["source_path"] != source["source_path"]
                or matching[0]["copy_path"] != source["copy_path"]
            ):
                raise ValueError("diagnostic and repair label do not bind the same baseline fit")
        diagnostic["h2_verdict"] = None
        units.append(
            {
                "unit_index": index,
                "unit_id": unit_id,
                "comparison_group_id": group_of(unit, "exp2a"),
                "unit": _unit_row(unit),
                "configuration": {
                    "causal_attribute": unit.causal_attribute,
                    "layout": unit.layout,
                },
                "confound_rate": float(unit.confound_rate),
                "repair_evidence": repair,
                "h2_diagnostics": diagnostic,
                "h2_verdict": None,
            }
        )

    counts = _counts(units)
    both_observed = (
        counts["pooled"]["observed_0"] > 0
        and counts["pooled"]["observed_1"] > 0
    )
    source_payload = {
        "baseline_diagnostics": baseline_manifest,
        "repair_validation_labels": validation_manifest,
        "ordinary_labels": ordinary_manifest,
    }
    source_manifests = {
        **source_payload,
        "source_inventory_sha256": _hash(source_payload),
    }
    document: dict[str, Any] = {
        "experiment_2a_report_schema_version": EXPERIMENT_2A_REPORT_SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "purpose": "descriptive_experiment_2a_family_report_not_h2_adjudication",
        "exposure_disclosure": {
            "reporting_spec_status": (
                "disclosed_post_outcome_post_collection_reporting_spec"
            ),
            "smoke_experiment_2a_label_known_before_specification": True,
            "pristine_preregistration_claimed": False,
        },
        "registered_inventory": {
            "unit_count": 20,
            "configuration_count": 5,
            "confound_levels": list(_CONFOUND_LEVELS),
            "baseline_seed_count_per_unit": 5,
            "baseline_source_count": 100,
            "repair_validation_label_count": 4,
            "ordinary_label_count": 16,
            "label_fit_reference_count": 384,
            "seeds": list(_SEEDS),
        },
        "rules": {
            "failure_definition": {
                "metric": "baseline.normalised_movement_error",
                "operator": ">",
                "threshold": K.FAILURE_THRESHOLD,
            },
            "ratio": {
                "numerator": "failure_set_mean_pairwise_disagreement",
                "denominator": "max(failure_set_mean_normalised_movement_error, 1e-6)",
                "floor": RATIO_FLOOR,
                "per_seed_ratio_of_means": True,
                "transitions_pooled_across_seeds": False,
            },
            "unit_summary": {
                "mean": "arithmetic_across_five_seed_ratios",
                "sample_sd_ddof": 1,
            },
            "correlation": {
                "method": "pearson",
                "domain": "strict_baseline_failure_set",
                "secondary_non_decisional": True,
                "aggregated_across_seeds": False,
            },
            "observed_labels_only_for_h2_classes": True,
        },
        "source_manifests": source_manifests,
        "units": units,
        "counts": counts,
        "scheduled_checks": _scheduled_checks(units),
        "sign_consistency_evidence_gate": _sign_consistency_evidence_gate(
            units, source_manifests
        ),
        "sign_consistency": None,
        "sign_consistency_status": (
            "not_applied_in_experiment_2a_family_report"
            if both_observed
            else "not_computable_missing_observed_class"
        ),
        "h2_verdict": None,
    }
    document["payload_sha256"] = _hash(document)
    return _validate_document(document)


def _validate_repair(value: Any, *, n_seeds: int, what: str) -> None:
    row = _exact_keys(
        value,
        {
            "effect", "ci_low", "ci_high", "relative_reduction", "passed",
            "reason", "method", "converged", "n_transitions", "n_seeds",
            "n_episodes", "unrepaired_mean", "min_practical_effect", "confidence",
        },
        what,
    )
    if type(row["passed"]) is not bool or type(row["converged"]) is not bool:
        raise ValueError(f"{what} pass/convergence states must be exact booleans")
    if type(row["reason"]) is not str or not row["reason"].strip():
        raise ValueError(f"{what} reason must be nonblank")
    _same(row["method"], "paired_seed_cluster", f"{what} method")
    _same(row["n_seeds"], n_seeds, f"{what} seed count")
    _exact_int(row["n_transitions"], f"{what} transition count", minimum=1)
    _exact_int(row["n_episodes"], f"{what} episode count", minimum=1)
    unrepaired = _finite(row["unrepaired_mean"], f"{what} unrepaired mean")
    if unrepaired <= 0:
        raise ValueError(f"{what} unrepaired mean must be positive")
    _same(row["min_practical_effect"], float(K.MIN_PRACTICAL_EFFECT), f"{what} practical effect")
    _same(row["confidence"], float(K.CONFIDENCE_LEVEL), f"{what} confidence")
    if row["converged"]:
        effect = _finite(row["effect"], f"{what} effect")
        low = _finite(row["ci_low"], f"{what} CI low")
        high = _finite(row["ci_high"], f"{what} CI high")
        relative = _finite(row["relative_reduction"], f"{what} relative reduction")
        if not low <= effect <= high or not low < high:
            raise ValueError(f"{what} interval does not contain its effect")
        if not math.isclose(relative, -effect / unrepaired, rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError(f"{what} relative reduction does not equal -effect/unrepaired")
        passed = effect < 0 and high < 0 and relative > K.MIN_PRACTICAL_EFFECT
    else:
        if any(row[name] is not None for name in ("effect", "ci_low", "ci_high", "relative_reduction")):
            raise ValueError(f"{what} unconverged statistics must be null")
        passed = False
    _same(row["passed"], passed, f"{what} pass rule")


def _validate_diagnostics(value: Any, *, unit: UnitSpec, observed: Any) -> None:
    unit_id = _unit_id(unit)
    record = _exact_keys(
        value,
        {
            "h2_diagnostic_schema_version", "purpose", "unit_id", "seeds",
            "per_seed", "ratio_mean_across_seeds", "ratio_sample_sd_across_seeds",
            "ratio_sd_ddof", "transitions_pooled_across_seeds",
            "correlations_aggregated", "h2_verdict",
        },
        "unit H2 diagnostics",
    )
    _same(record["h2_diagnostic_schema_version"], H.H2_DIAGNOSTIC_SCHEMA_VERSION, "H2 schema")
    _same(record["purpose"], "condition_metrics_not_h2_adjudication", "H2 purpose")
    _same(record["unit_id"], unit_id, "H2 unit")
    _same(record["seeds"], list(_SEEDS), "H2 seeds")
    _same(record["ratio_sd_ddof"], 1, "ratio SD ddof")
    _same(record["transitions_pooled_across_seeds"], False, "transition pooling")
    _same(record["correlations_aggregated"], False, "correlation aggregation")
    _same(record["h2_verdict"], None, "unit H2 verdict")
    rows = record["per_seed"]
    if type(rows) is not list or len(rows) != 5:
        raise ValueError("unit H2 diagnostics require exactly five seed rows")
    ratios: list[float] = []
    for seed, row in zip(_SEEDS, rows, strict=True):
        row = _exact_keys(
            row,
            {
                "h2_diagnostic_schema_version", "purpose", "unit_id",
                "comparison_group_id", "stage", "seed", "fit_id",
                "execution_digest", "expected_git_commit", "normalisation",
                "failure_definition", "ratio_floor", "correlation_method",
                "correlation_domain", "n_movement", "n_failure",
                "failure_mask_sha256", "mean_error", "mean_disagreement",
                "ratio_of_means", "pearson_r", "correlation_undefined_reason",
                "observed_repair_label", "h2_verdict",
            },
            "per-seed H2 diagnostic",
        )
        _same(row["h2_diagnostic_schema_version"], H.H2_DIAGNOSTIC_SCHEMA_VERSION, "seed H2 schema")
        _same(row["purpose"], "per_seed_metrics_not_h2_adjudication", "seed H2 purpose")
        _same(row["unit_id"], unit_id, "seed H2 unit")
        _same(row["comparison_group_id"], group_of(unit, "exp2a"), "seed comparison group")
        _same(row["stage"], "exp2a", "seed stage")
        _same(row["seed"], seed, "seed identity")
        _digest(row["unit_id"], length=12, what="unit identity")
        if type(row["fit_id"]) is not str or not row["fit_id"]:
            raise ValueError("fit_id must be nonblank")
        _digest(row["execution_digest"], length=64, what="execution digest")
        _digest(row["expected_git_commit"], length=40, what="expected commit")
        _same(
            row["failure_definition"],
            {"operator": ">", "threshold": K.FAILURE_THRESHOLD},
            "seed failure definition",
        )
        _same(row["ratio_floor"], RATIO_FLOOR, "ratio floor")
        _same(row["correlation_method"], "pearson", "correlation method")
        _same(row["correlation_domain"], "baseline_failure_set", "correlation domain")
        normalisation = _exact_keys(
            row["normalisation"],
            {"scale", "scale_n_reference", "scale_domain", "scale_source"},
            "normalisation",
        )
        if type(normalisation["scale"]) is not list or not normalisation["scale"]:
            raise ValueError("normalisation scale must be a nonempty list")
        for scalar in normalisation["scale"]:
            if (
                isinstance(scalar, bool)
                or not isinstance(scalar, (int, float))
                or not math.isfinite(scalar)
                or scalar <= 0
            ):
                raise ValueError("normalisation scale values must be finite positive numbers")
        _exact_int(normalisation["scale_n_reference"], "scale reference count", minimum=1)
        _same(normalisation["scale_domain"], K.NORMALISATION_SCALE_DOMAIN, "scale domain")
        _same(normalisation["scale_source"], K.NORMALISATION_SCALE_SOURCE, "scale source")
        n_movement = _exact_int(row["n_movement"], "movement count", minimum=1)
        n_failure = _exact_int(row["n_failure"], "failure count", minimum=1)
        if n_failure > n_movement:
            raise ValueError("failure count exceeds movement count")
        _digest(row["failure_mask_sha256"], length=64, what="failure mask digest")
        mean_error = _finite(row["mean_error"], "failure-set mean error", nonnegative=True)
        mean_disagreement = _finite(
            row["mean_disagreement"], "failure-set mean disagreement", nonnegative=True
        )
        ratio = _finite(row["ratio_of_means"], "ratio of means", nonnegative=True)
        _same(
            ratio,
            mean_disagreement / max(mean_error, RATIO_FLOOR),
            "exact per-seed ratio of means",
        )
        ratios.append(ratio)
        pearson = row["pearson_r"]
        reason = row["correlation_undefined_reason"]
        if pearson is None:
            if type(reason) is not str or reason not in _PEARSON_UNDEFINED_REASONS:
                raise ValueError("undefined Pearson coefficient requires an exact registered reason")
        else:
            value_r = _finite(pearson, "Pearson coefficient")
            if not -1.000000000000001 <= value_r <= 1.000000000000001 or reason is not None:
                raise ValueError("Pearson coefficient/reason fields disagree")
        _same(row["observed_repair_label"], observed, "joined observed label")
        _same(row["h2_verdict"], None, "seed H2 verdict")
    mean, sd = _mean_sd(ratios)
    _same(record["ratio_mean_across_seeds"], mean, "unit ratio mean")
    _same(record["ratio_sample_sd_across_seeds"], sd, "unit ratio sample SD")


def _validate_manifest(value: Any, units: Sequence[dict[str, Any]]) -> None:
    manifest = _exact_keys(
        value,
        {
            "baseline_diagnostics", "repair_validation_labels", "ordinary_labels",
            "source_inventory_sha256",
        },
        "source manifests",
    )
    baseline = manifest["baseline_diagnostics"]
    validation = manifest["repair_validation_labels"]
    ordinary = manifest["ordinary_labels"]
    if type(baseline) is not list or len(baseline) != 100:
        raise ValueError("source manifest requires exactly one hundred baselines")
    if type(validation) is not list or len(validation) != 4:
        raise ValueError("source manifest requires exactly four twenty-seed labels")
    if type(ordinary) is not list or len(ordinary) != 16:
        raise ValueError("source manifest requires exactly sixteen ordinary labels")
    unit_by_id = {row["unit_id"]: row for row in units}
    diagnostic_by_cell = {
        (row["unit_id"], seed["seed"]): seed
        for row in units
        for seed in row["h2_diagnostics"]["per_seed"]
    }
    cells: set[tuple[str, int]] = set()
    paths: set[Path] = set()
    fit_ids: set[str] = set()
    baseline_by_cell: dict[tuple[str, int], dict[str, Any]] = {}
    for row in baseline:
        row = _exact_keys(
            row,
            {
                "unit_id", "seed", "source_path", "copy_path",
                "expected_git_commit", "expected_execution_digest", "fit_id",
                "source_verified_execution_digest",
                "copy_verified_execution_digest",
            },
            "baseline source row",
        )
        if row["unit_id"] not in unit_by_id or row["seed"] not in _SEEDS:
            raise ValueError("baseline source names an unregistered unit or seed")
        cell = (row["unit_id"], row["seed"])
        source_path = _manifest_project_path(
            row["source_path"], what="baseline original manifest path"
        )
        copy_path = _manifest_project_path(
            row["copy_path"], what="baseline copy manifest path"
        )
        _independent_pair(
            source_path, copy_path, what="baseline manifest fit", inspect_filesystem=False
        )
        if cell in cells or source_path in paths or copy_path in paths:
            raise ValueError("duplicate/malformed baseline source-pair binding")
        cells.add(cell)
        paths.update((source_path, copy_path))
        _digest(row["expected_git_commit"], length=40, what="source expected commit")
        expected_digest = _digest(row["expected_execution_digest"], length=64, what="source expected digest")
        _same(row["source_verified_execution_digest"], expected_digest, "verified original digest")
        _same(row["copy_verified_execution_digest"], expected_digest, "verified copy digest")
        if type(row["fit_id"]) is not str or not row["fit_id"] or row["fit_id"] in fit_ids:
            raise ValueError("baseline fit_id must be nonblank")
        fit_ids.add(row["fit_id"])
        diagnostic = diagnostic_by_cell[cell]
        if (
            row["fit_id"] != diagnostic["fit_id"]
            or row["source_verified_execution_digest"] != diagnostic["execution_digest"]
            or row["copy_verified_execution_digest"] != diagnostic["execution_digest"]
            or row["expected_git_commit"] != diagnostic["expected_git_commit"]
        ):
            raise ValueError("baseline source manifest is not bound to its diagnostic row")
        baseline_by_cell[cell] = row
    expected_cells = {(unit_id, seed) for unit_id in unit_by_id for seed in _SEEDS}
    if cells != expected_cells:
        raise ValueError("baseline source manifest is not the complete twenty-by-five grid")

    label_units: set[str] = set()
    label_paths: set[Path] = set()
    label_fit_ids: set[str] = set()
    label_fit_paths: set[Path] = set()
    fit_count = 0
    validation_ids = _validation_unit_ids()
    for collection, procedure, count, seeds in (
        (validation, "repair_validation_20_seed", 60, list(range(1000, 1020))),
        (ordinary, "ordinary_canonical_three_seed_v1", 9, list(range(1000, 1003))),
    ):
        for row in collection:
            row = _exact_keys(
                row,
                {
                    "unit_id", "procedure", "source_path", "copy_path",
                    "source_sha256", "copy_sha256", "record_digest", "seeds",
                    "fit_sources",
                },
                "label source row",
            )
            unit_id = row["unit_id"]
            if unit_id not in unit_by_id or unit_id in label_units:
                raise ValueError("label source names an unknown or duplicate unit")
            if (procedure == "repair_validation_20_seed") != (unit_id in validation_ids):
                raise ValueError("label source uses the wrong registered seed policy")
            label_units.add(unit_id)
            _same(row["procedure"], procedure, "label procedure")
            _same(row["seeds"], seeds, "label seeds")
            source_path = _manifest_project_path(
                row["source_path"], what="label original manifest path"
            )
            copy_path = _manifest_project_path(
                row["copy_path"], what="label copy manifest path"
            )
            _independent_pair(
                source_path, copy_path, what="label manifest file", inspect_filesystem=False
            )
            if source_path in label_paths or copy_path in label_paths:
                raise ValueError("duplicate label original/copy manifest path")
            label_paths.update((source_path, copy_path))
            source_sha = _digest(row["source_sha256"], length=64, what="label original digest")
            copy_sha = _digest(row["copy_sha256"], length=64, what="label copy digest")
            _same(copy_sha, source_sha, "label original/copy digest")
            record_digest = _digest(row["record_digest"], length=64, what="label record digest")
            _same(
                unit_by_id[unit_id]["repair_evidence"]["label_record_digest"],
                record_digest,
                "unit label record/source-manifest record digest",
            )
            refs = row["fit_sources"]
            if type(refs) is not list or len(refs) != count:
                raise ValueError("label source has the wrong number of fit references")
            seen_refs: set[tuple[int, str]] = set()
            for ref in refs:
                ref = _exact_keys(
                    ref,
                    {
                        "seed", "role", "fit_id", "source_path", "copy_path",
                        "expected_git_commit", "expected_execution_digest",
                        "source_verified_execution_digest",
                        "copy_verified_execution_digest",
                    },
                    "label fit source",
                )
                if ref["seed"] not in seeds or ref["role"] not in ("baseline", "data_repair", "feature_repair"):
                    raise ValueError("label fit source has an unknown seed or role")
                key = (ref["seed"], ref["role"])
                if key in seen_refs:
                    raise ValueError("duplicate label seed/role fit source")
                seen_refs.add(key)
                source_fit_path = _manifest_project_path(
                    ref["source_path"], what="label fit original manifest path"
                )
                copy_fit_path = _manifest_project_path(
                    ref["copy_path"], what="label fit copy manifest path"
                )
                _independent_pair(
                    source_fit_path,
                    copy_fit_path,
                    what="label manifest fit",
                    inspect_filesystem=False,
                )
                if type(ref["fit_id"]) is not str or not ref["fit_id"]:
                    raise ValueError("label fit source identity must be nonblank")
                if ref["fit_id"] in label_fit_ids:
                    raise ValueError("duplicate physical fit_id across label source manifests")
                if source_fit_path in label_fit_paths or copy_fit_path in label_fit_paths:
                    raise ValueError("duplicate physical path across label source manifests")
                label_fit_ids.add(ref["fit_id"])
                label_fit_paths.update((source_fit_path, copy_fit_path))
                _digest(ref["expected_git_commit"], length=40, what="label fit expected commit")
                execution = _digest(
                    ref["expected_execution_digest"],
                    length=64,
                    what="label fit expected execution digest",
                )
                _same(
                    ref["source_verified_execution_digest"], execution,
                    "label fit verified original digest",
                )
                _same(
                    ref["copy_verified_execution_digest"], execution,
                    "label fit verified copy digest",
                )
            expected_refs = {(seed, role) for seed in seeds for role in ("baseline", "data_repair", "feature_repair")}
            if seen_refs != expected_refs:
                raise ValueError("label fit source inventory is incomplete")
            for seed in _SEEDS:
                matching = [ref for ref in refs if ref["seed"] == seed and ref["role"] == "baseline"]
                if matching:
                    base = baseline_by_cell[(unit_id, seed)]
                    if (
                        len(matching) != 1
                        or matching[0]["fit_id"] != base["fit_id"]
                        or matching[0]["expected_execution_digest"]
                        != base["source_verified_execution_digest"]
                        or matching[0]["expected_git_commit"] != base["expected_git_commit"]
                        or matching[0]["source_path"] != base["source_path"]
                        or matching[0]["copy_path"] != base["copy_path"]
                    ):
                        raise ValueError("label and diagnostic manifests bind different baseline fits")
            fit_count += len(refs)
    if label_units != set(unit_by_id) or fit_count != 384:
        raise ValueError("label source manifest is not the exact 20-label/384-fit inventory")
    source_payload = {
        "baseline_diagnostics": baseline,
        "repair_validation_labels": validation,
        "ordinary_labels": ordinary,
    }
    _same(manifest["source_inventory_sha256"], _hash(source_payload), "source inventory digest")


def _validate_document(value: Any) -> dict[str, Any]:
    document = _exact_keys(
        value,
        {
            "experiment_2a_report_schema_version", "kind", "purpose",
            "exposure_disclosure",
            "registered_inventory", "rules", "source_manifests", "units",
            "counts", "scheduled_checks", "sign_consistency_evidence_gate",
            "sign_consistency",
            "sign_consistency_status", "h2_verdict", "payload_sha256",
        },
        "Experiment-2A report",
    )
    _same(document["experiment_2a_report_schema_version"], EXPERIMENT_2A_REPORT_SCHEMA_VERSION, "report schema")
    _same(document["kind"], REPORT_KIND, "report kind")
    _same(document["purpose"], "descriptive_experiment_2a_family_report_not_h2_adjudication", "report purpose")
    _same(
        document["exposure_disclosure"],
        {
            "reporting_spec_status": (
                "disclosed_post_outcome_post_collection_reporting_spec"
            ),
            "smoke_experiment_2a_label_known_before_specification": True,
            "pristine_preregistration_claimed": False,
        },
        "exposure disclosure",
    )
    _digest(document["payload_sha256"], length=64, what="report payload digest")
    _same(
        document["payload_sha256"],
        _hash({key: item for key, item in document.items() if key != "payload_sha256"}),
        "report payload digest",
    )
    _same(
        document["registered_inventory"],
        {
            "unit_count": 20,
            "configuration_count": 5,
            "confound_levels": list(_CONFOUND_LEVELS),
            "baseline_seed_count_per_unit": 5,
            "baseline_source_count": 100,
            "repair_validation_label_count": 4,
            "ordinary_label_count": 16,
            "label_fit_reference_count": 384,
            "seeds": list(_SEEDS),
        },
        "registered inventory",
    )
    expected_rules = {
        "failure_definition": {
            "metric": "baseline.normalised_movement_error",
            "operator": ">",
            "threshold": K.FAILURE_THRESHOLD,
        },
        "ratio": {
            "numerator": "failure_set_mean_pairwise_disagreement",
            "denominator": "max(failure_set_mean_normalised_movement_error, 1e-6)",
            "floor": RATIO_FLOOR,
            "per_seed_ratio_of_means": True,
            "transitions_pooled_across_seeds": False,
        },
        "unit_summary": {
            "mean": "arithmetic_across_five_seed_ratios",
            "sample_sd_ddof": 1,
        },
        "correlation": {
            "method": "pearson",
            "domain": "strict_baseline_failure_set",
            "secondary_non_decisional": True,
            "aggregated_across_seeds": False,
        },
        "observed_labels_only_for_h2_classes": True,
    }
    _same(document["rules"], expected_rules, "report rules")
    units = document["units"]
    expected_units = _registered_units()
    if type(units) is not list or len(units) != 20:
        raise ValueError("report requires exactly twenty unit rows")
    for index, (row, unit) in enumerate(zip(units, expected_units, strict=True)):
        row = _exact_keys(
            row,
            {
                "unit_index", "unit_id", "comparison_group_id", "unit",
                "configuration", "confound_rate", "repair_evidence",
                "h2_diagnostics", "h2_verdict",
            },
            "Experiment-2A unit row",
        )
        _same(row["unit_index"], index, "unit index")
        _same(row["unit_id"], _unit_id(unit), "unit identity")
        _same(row["comparison_group_id"], group_of(unit, "exp2a"), "comparison group")
        _same(row["unit"], _unit_row(unit), "unit provenance")
        _same(
            row["configuration"],
            {"causal_attribute": unit.causal_attribute, "layout": unit.layout},
            "configuration metadata",
        )
        _same(row["confound_rate"], float(unit.confound_rate), "confound rate")
        repair = _exact_keys(
            row["repair_evidence"],
            {
                "procedure", "label_stage", "label_seed_count",
                "label_record_digest", "comparison_group_id", "intended_class",
                "observed_label", "data_repair_works", "feature_repair_works",
                "data_repair", "feature_repair",
            },
            "repair evidence",
        )
        is_validation = _unit_id(unit) in _validation_unit_ids()
        _same(
            repair["procedure"],
            "repair_validation_20_seed" if is_validation else "ordinary_canonical_three_seed_v1",
            "repair procedure",
        )
        _same(repair["label_stage"], "repair_validation" if is_validation else "exp3_repairs", "label stage")
        n_label_seeds = 20 if is_validation else 3
        _same(repair["label_seed_count"], n_label_seeds, "label seed count")
        _digest(repair["label_record_digest"], length=64, what="label record digest")
        _same(repair["comparison_group_id"], group_of(unit, "exp2a"), "label comparison group")
        _same(repair["intended_class"], "hypothesis_class", "label intended class")
        if type(repair["observed_label"]) is bool or repair["observed_label"] not in _LABEL_VALUES:
            raise ValueError("invalid observed repair label")
        if type(repair["data_repair_works"]) is not bool or type(repair["feature_repair_works"]) is not bool:
            raise ValueError("repair work states must be exact booleans")
        _validate_repair(repair["data_repair"], n_seeds=n_label_seeds, what="data repair")
        _validate_repair(repair["feature_repair"], n_seeds=n_label_seeds, what="feature repair")
        _same(repair["data_repair_works"], repair["data_repair"]["passed"], "data repair work state")
        _same(repair["feature_repair_works"], repair["feature_repair"]["passed"], "feature repair work state")
        _same(
            repair["observed_label"],
            observed_label(repair["data_repair_works"], repair["feature_repair_works"]),
            "observed label mapping",
        )
        _validate_diagnostics(row["h2_diagnostics"], unit=unit, observed=repair["observed_label"])
        _same(row["h2_verdict"], None, "unit H2 verdict")

    expected_counts = _counts(units)
    _same(document["counts"], expected_counts, "label counts")
    _same(document["scheduled_checks"], _scheduled_checks(units), "scheduled descriptive checks")
    _same(
        document["sign_consistency_evidence_gate"],
        _sign_consistency_evidence_gate(units, document["source_manifests"]),
        "sign-consistency complete-inventory evidence gate",
    )
    both = expected_counts["pooled"]["observed_0"] > 0 and expected_counts["pooled"]["observed_1"] > 0
    _same(document["sign_consistency"], None, "sign consistency")
    _same(
        document["sign_consistency_status"],
        "not_applied_in_experiment_2a_family_report" if both else "not_computable_missing_observed_class",
        "sign consistency status",
    )
    _same(document["h2_verdict"], None, "H2 verdict")
    _validate_manifest(document["source_manifests"], units)
    return document


def write_experiment_2a_report(
    baseline_sources: Sequence[Experiment2ABaselineSources],
    repair_validation_labels: Sequence[RepairValidationLabelSource],
    ordinary_labels: Sequence[OrdinaryLabelSource],
    *,
    report_path: Path,
) -> Path:
    """Reverify the exact 20-unit evidence inventory and publish one report."""

    output = _project_path(
        report_path, what="Experiment-2A report output", kind="file", must_exist=False
    )
    document = _build(baseline_sources, repair_validation_labels, ordinary_labels)
    label_paths = {
        Path(row[field])
        for key in ("repair_validation_labels", "ordinary_labels")
        for row in document["source_manifests"][key]
        for field in ("source_path", "copy_path")
    }
    fit_paths = {
        Path(row[field])
        for row in document["source_manifests"]["baseline_diagnostics"]
        for field in ("source_path", "copy_path")
    }
    fit_paths.update(
        Path(ref[field])
        for key in ("repair_validation_labels", "ordinary_labels")
        for row in document["source_manifests"][key]
        for ref in row["fit_sources"]
        for field in ("source_path", "copy_path")
    )
    if any(_overlap(output, path) for path in label_paths | fit_paths):
        raise ValueError("report output must be disjoint from every evidence source and copy")
    return atomic_write_json(output, document)


def load_experiment_2a_report(report_path: Path, *, expected_sha256: str) -> dict[str, Any]:
    """Load and validate exact report bytes without reopening scientific sources."""

    _digest(expected_sha256, length=64, what="expected report SHA-256")
    path = _project_path(
        report_path, what="Experiment-2A report", kind="file", must_exist=True
    )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read Experiment-2A report: {exc}") from exc
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError("report bytes do not match the externally supplied SHA-256")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Experiment-2A report is not strict JSON: {exc}") from exc
    return _validate_document(value)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> Any:
    raise ValueError(f"non-finite JSON value {value!r}")


def replay_experiment_2a_report(report_path: Path, *, expected_sha256: str) -> dict[str, Any]:
    """Offline deterministic replay of all report invariants from report bytes."""

    return load_experiment_2a_report(report_path, expected_sha256=expected_sha256)
