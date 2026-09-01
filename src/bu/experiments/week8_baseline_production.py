"""Fixed attempt-001 operator boundary for the Week-8 baseline batches.

The scientific and execution semantics remain in :mod:`week8_plan`,
:mod:`week8_preflight`, :mod:`week8_launch`, and :mod:`week8_monitor`.  This
module removes the remaining operator discretion: all roots, batch order,
resource limits, and command handoffs are fixed.  Every handoff is retained in
two independent project-local files and SHA-256 bound before the next phase.

Only operational inventory is returned or printed.  Fit outputs, metrics,
labels, ratios, effects, and hypothesis conclusions are never opened here.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_bytes, sha256_file
from . import batch as B
from . import confirmatory as C
from . import repair_label_preflight as RF
from . import week8_launch as Launch
from . import week8_monitor as Monitor
from . import week8_plan as Plan
from . import week8_preflight as Preflight


PRODUCTION_SCHEMA_VERSION = 1
ATTEMPT = "2026-09-01-attempt-001"
ATTEMPT_TIMEOUT_SECONDS = 3600.0
MINIMUM_FREE_BYTES = 8_589_934_592
COMMON_CONTROL_DIRECTORY = "week7-production-control"
COMMON_LEASE_NAME = "week7-production"

WORKSPACE_ROOT = Preflight.WORKSPACE_ROOT
PREPARATION_ROOT = WORKSPACE_ROOT / f"week8-baseline-preparation-{ATTEMPT}"
PREPARATION_ORIGINAL_ROOT = PREPARATION_ROOT / "original"
PREPARATION_COPY_ROOT = PREPARATION_ROOT / "project-evidence"


@dataclass(frozen=True)
class BatchLayout:
    """One fixed batch identity and all of its disjoint attempt-001 roots."""

    key: str
    fit_count: int
    model_count: int
    preflight_root: Path
    output_root: Path
    staging_root: Path
    sync_root: Path
    monitor_root: Path
    monitor_copy_root: Path


EXP2B = BatchLayout(
    key="exp2b",
    fit_count=125,
    model_count=625,
    preflight_root=WORKSPACE_ROOT / f"week8-exp2b-{ATTEMPT}-preflight",
    output_root=WORKSPACE_ROOT / f"week8-exp2b-{ATTEMPT}-output",
    staging_root=WORKSPACE_ROOT / f"week8-exp2b-{ATTEMPT}-staging",
    sync_root=WORKSPACE_ROOT / f"week8-exp2b-{ATTEMPT}-project-evidence",
    monitor_root=WORKSPACE_ROOT / f"week8-monitor-exp2b-{ATTEMPT}",
    monitor_copy_root=(
        WORKSPACE_ROOT / f"week8-monitor-exp2b-{ATTEMPT}-project-evidence"
    ),
)
SWEEP_002 = BatchLayout(
    key="sweep-002",
    fit_count=3,
    model_count=15,
    preflight_root=WORKSPACE_ROOT / f"week8-sweep-002-{ATTEMPT}-preflight",
    output_root=WORKSPACE_ROOT / f"week8-sweep-002-{ATTEMPT}-output",
    staging_root=WORKSPACE_ROOT / f"week8-sweep-002-{ATTEMPT}-staging",
    sync_root=(
        WORKSPACE_ROOT / f"week8-sweep-002-{ATTEMPT}-project-evidence"
    ),
    monitor_root=WORKSPACE_ROOT / f"week8-monitor-sweep-002-{ATTEMPT}",
    monitor_copy_root=(
        WORKSPACE_ROOT
        / f"week8-monitor-sweep-002-{ATTEMPT}-project-evidence"
    ),
)
BATCHES: Mapping[str, BatchLayout] = {
    EXP2B.key: EXP2B,
    SWEEP_002.key: SWEEP_002,
}

_RECEIPT_NAMES = {
    "prepare",
    "exp2b-preflight",
    "exp2b-launch-control",
    "exp2b-launch-complete",
    "sweep-002-preflight",
    "sweep-002-launch-control",
    "sweep-002-launch-complete",
}
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN = re.compile(r"[0-9a-f]{32}\Z")
_SNAPSHOT = re.compile(r"snapshot-([0-9]{6})\.json\Z")


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Week-8 baseline production evidence must be strict JSON") from exc


def _strict(value: object, keys: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(f"{what} has missing or extra fields")
    return value


def _sha(value: object, *, what: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise ValueError(f"{what} must be a canonical lowercase SHA-256")
    return value


def _commit(value: object) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None:
        raise ValueError("expected Git commit must be canonical lowercase 40-hex")
    return value


def _seal(payload: Mapping[str, Any]) -> dict[str, Any]:
    document = dict(payload)
    document["receipt_digest"] = sha256_bytes(_canonical(document))
    return document


def _overlap(left: Path, right: Path) -> bool:
    first = Path(os.path.abspath(left))
    second = Path(os.path.abspath(right))
    return first == second or first in second.parents or second in first.parents


def _batch_roots(layout: BatchLayout) -> dict[str, Path]:
    return {
        "preflight": layout.preflight_root,
        "output": layout.output_root,
        "staging": layout.staging_root,
        "sync": layout.sync_root,
    }


def _all_fixed_roots() -> dict[str, Path]:
    roots = {
        "preparation": PREPARATION_ROOT,
        "preparation_original": PREPARATION_ORIGINAL_ROOT,
        "preparation_copy": PREPARATION_COPY_ROOT,
    }
    for layout in BATCHES.values():
        roots.update(
            {
                f"{layout.key}_preflight": layout.preflight_root,
                f"{layout.key}_output": layout.output_root,
                f"{layout.key}_staging": layout.staging_root,
                f"{layout.key}_sync": layout.sync_root,
                f"{layout.key}_monitor": layout.monitor_root,
                f"{layout.key}_monitor_copy": layout.monitor_copy_root,
            }
        )
    return roots


def _validate_fixed_layout() -> None:
    """Fail before writes if any fixed name, route, or root relation drifted."""

    workspace = Path(os.path.abspath(WORKSPACE_ROOT))
    roots = {
        name: Path(os.path.abspath(path)) for name, path in _all_fixed_roots().items()
    }
    if any(path == workspace or not path.is_relative_to(workspace) for path in roots.values()):
        raise ValueError("every Week-8 baseline production root must be project-local")
    allowed_nested = {
        frozenset((roots["preparation"], roots["preparation_original"])),
        frozenset((roots["preparation"], roots["preparation_copy"])),
    }
    values = tuple(roots.values())
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            if _overlap(left, right) and frozenset((left, right)) not in allowed_nested:
                raise ValueError("fixed Week-8 baseline production roots overlap")

    expected_names = {
        "preparation": f"week8-baseline-preparation-{ATTEMPT}",
        "preparation_original": "original",
        "preparation_copy": "project-evidence",
        "exp2b_preflight": f"week8-exp2b-{ATTEMPT}-preflight",
        "exp2b_output": f"week8-exp2b-{ATTEMPT}-output",
        "exp2b_staging": f"week8-exp2b-{ATTEMPT}-staging",
        "exp2b_sync": f"week8-exp2b-{ATTEMPT}-project-evidence",
        "exp2b_monitor": f"week8-monitor-exp2b-{ATTEMPT}",
        "exp2b_monitor_copy": (
            f"week8-monitor-exp2b-{ATTEMPT}-project-evidence"
        ),
        "sweep-002_preflight": f"week8-sweep-002-{ATTEMPT}-preflight",
        "sweep-002_output": f"week8-sweep-002-{ATTEMPT}-output",
        "sweep-002_staging": f"week8-sweep-002-{ATTEMPT}-staging",
        "sweep-002_sync": f"week8-sweep-002-{ATTEMPT}-project-evidence",
        "sweep-002_monitor": f"week8-monitor-sweep-002-{ATTEMPT}",
        "sweep-002_monitor_copy": (
            f"week8-monitor-sweep-002-{ATTEMPT}-project-evidence"
        ),
    }
    if any(roots[key].name != name for key, name in expected_names.items()):
        raise ValueError("fixed Week-8 baseline attempt-001 root names drifted")
    for layout in BATCHES.values():
        prefix = Monitor.MONITOR_ROOT_PREFIXES.get(layout.key)
        if (
            prefix is None
            or not layout.monitor_root.name.startswith(prefix)
            or not layout.monitor_copy_root.name.startswith(prefix)
            or layout.monitor_root.name == prefix
            or layout.monitor_copy_root.name == prefix
        ):
            raise ValueError("fixed monitor roots violate the certified prefix policy")
    if (
        ATTEMPT != "2026-09-01-attempt-001"
        or ATTEMPT_TIMEOUT_SECONDS != 3600.0
        or type(MINIMUM_FREE_BYTES) is not int
        or MINIMUM_FREE_BYTES != 8_589_934_592
        or tuple(BATCHES) != Plan.AUTHORIZED_BATCH_KEYS
        or (EXP2B.fit_count, EXP2B.model_count) != (125, 625)
        or (SWEEP_002.fit_count, SWEEP_002.model_count) != (3, 15)
        or COMMON_CONTROL_DIRECTORY != "week7-production-control"
        or Preflight.COMMON_CONTROL_DIRECTORY != COMMON_CONTROL_DIRECTORY
        or Path(os.path.abspath(Preflight._control_root()))
        != workspace / COMMON_CONTROL_DIRECTORY
        or COMMON_LEASE_NAME != "week7-production"
        or Launch.WEEK8_LEASE_NAME != COMMON_LEASE_NAME
        or C.CONFIRMATORY_DEVICE != "cpu"
        or C.CONFIRMATORY_THREADS != 4
        or C.CONFIRMATORY_INTEROP_THREADS != 4
    ):
        raise ValueError("fixed Week-8 baseline resource or ordering policy drifted")


def _workspace() -> Path:
    candidate = Path(WORKSPACE_ROOT).absolute()
    for component in (*reversed(candidate.parents), candidate):
        try:
            info = component.lstat()
        except OSError as exc:
            raise ValueError(f"Week-8 production workspace is unavailable: {exc}") from exc
        reparse = int(getattr(info, "st_file_attributes", 0)) & int(
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        if stat.S_ISLNK(info.st_mode) or reparse:
            raise ValueError(
                f"Week-8 production workspace contains a link/reparse point: {component}"
            )
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(
                f"Week-8 production workspace has a non-directory component: {component}"
            )
    resolved = candidate.resolve(strict=True)
    if resolved != Preflight.WORKSPACE_ROOT.resolve(strict=True):
        raise ValueError("wrapper and certified preflight workspace roots differ")
    return resolved


def _plain_directory(path: Path, *, what: str) -> Path:
    return Preflight._project_path(path, what=what, directory=True)


def _plain_file(path: Path, *, what: str) -> Path:
    target = Preflight._project_path(path, what=what, directory=False)
    RF._regular_file(target, what=what)
    return target


def _create_direct_root(path: Path, *, what: str) -> Path:
    workspace = _workspace()
    candidate = Path(os.path.abspath(path))
    if candidate.parent != workspace:
        raise ValueError(f"{what} must be a direct workspace child")
    if os.path.lexists(candidate):
        raise ValueError(f"{what} is preexisting")
    try:
        candidate.mkdir()
    except OSError as exc:
        raise ValueError(f"cannot create {what}: {exc}") from exc
    return _plain_directory(candidate, what=what)


def _create_preparation() -> tuple[Path, Path]:
    root = _create_direct_root(PREPARATION_ROOT, what="preparation root")
    original = RF.ensure_regular_child_directory(root, PREPARATION_ORIGINAL_ROOT.name)
    copied = RF.ensure_regular_child_directory(root, PREPARATION_COPY_ROOT.name)
    return original, copied


def _ensure_receipt_directories() -> tuple[Path, Path]:
    original = _plain_directory(
        PREPARATION_ORIGINAL_ROOT, what="preparation original root"
    )
    copied = _plain_directory(PREPARATION_COPY_ROOT, what="preparation copy root")
    return (
        RF.ensure_regular_child_directory(original, "receipts"),
        RF.ensure_regular_child_directory(copied, "receipts"),
    )


def _independent_equal(left: Path, right: Path, *, what: str) -> str:
    first = _plain_file(left, what=f"{what} original")
    second = _plain_file(right, what=f"{what} independent copy")
    if _overlap(first, second):
        raise ValueError(f"{what} paths overlap")
    try:
        aliases = os.path.samefile(first, second)
    except OSError as exc:
        raise ValueError(f"cannot establish {what} file independence") from exc
    if aliases:
        raise ValueError(f"{what} files alias one filesystem object")
    raw = first.read_bytes()
    if second.read_bytes() != raw:
        raise ValueError(f"{what} independent bytes diverge")
    digest = sha256_bytes(raw)
    if sha256_file(first) != digest or sha256_file(second) != digest:
        raise ValueError(f"{what} changed during digest read-back")
    return digest


def _copy_independent(source: Path, destination: Path, *, what: str) -> str:
    RF.sync_immutable_file(source, destination)
    return _independent_equal(source, destination, what=what)


def _receipt_paths(name: str) -> tuple[Path, Path]:
    if name not in _RECEIPT_NAMES:
        raise ValueError(f"unknown Week-8 baseline receipt name: {name!r}")
    return (
        PREPARATION_ORIGINAL_ROOT / "receipts" / f"{name}.json",
        PREPARATION_COPY_ROOT / "receipts" / f"{name}.json",
    )


def _publish_receipt(
    name: str, *, status: str, purpose: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    directories = _ensure_receipt_directories()
    paths = _receipt_paths(name)
    if tuple(path.parent for path in paths) != directories:
        raise ValueError("receipt paths escaped their fixed independent roots")
    document = _seal(
        {
            "week8_baseline_production_schema_version": PRODUCTION_SCHEMA_VERSION,
            "name": name,
            "status": status,
            "purpose": purpose,
            "paths": {
                "original": str(paths[0].resolve()),
                "independent_copy": str(paths[1].resolve()),
            },
            "payload": dict(payload),
        }
    )
    atomic_write_json(paths[0], document)
    atomic_write_json(paths[1], document)
    digest = _independent_equal(paths[0], paths[1], what=f"{name} receipt")
    if read_json(paths[0]) != document or read_json(paths[1]) != document:
        raise ValueError(f"persisted {name} receipt differs from its sealed document")
    return {**document, "_file_sha256": digest}


def _load_receipt(name: str) -> dict[str, Any]:
    paths = _receipt_paths(name)
    digest = _independent_equal(paths[0], paths[1], what=f"{name} receipt")
    document = _strict(
        read_json(paths[0]),
        {
            "week8_baseline_production_schema_version",
            "name",
            "status",
            "purpose",
            "paths",
            "payload",
            "receipt_digest",
        },
        what=f"{name} receipt",
    )
    if (
        document["week8_baseline_production_schema_version"]
        != PRODUCTION_SCHEMA_VERSION
        or document["name"] != name
        or type(document["status"]) is not str
        or type(document["purpose"]) is not str
        or type(document["payload"]) is not dict
        or document["paths"]
        != {
            "original": str(paths[0].resolve()),
            "independent_copy": str(paths[1].resolve()),
        }
        or document != _seal(
            {key: value for key, value in document.items() if key != "receipt_digest"}
        )
        or read_json(paths[1]) != document
    ):
        raise ValueError(f"{name} receipt identity, digest, or copy diverged")
    _sha(document["receipt_digest"], what=f"{name} receipt digest")
    return {**document, "_file_sha256": digest}


def _pin(left: Path, right: Path, *, what: str) -> dict[str, Any]:
    return {
        "path": str(left.resolve()),
        "copy_path": str(right.resolve()),
        "sha256": _independent_equal(left, right, what=what),
        "independent_copy": True,
    }


def _validate_pin(row: object, left: Path, right: Path, *, what: str) -> str:
    observed = _strict(
        row,
        {"path", "copy_path", "sha256", "independent_copy"},
        what=f"{what} pin",
    )
    expected = _pin(left, right, what=what)
    if observed != expected:
        raise ValueError(f"{what} pin differs from fixed independent evidence")
    return _sha(observed["sha256"], what=f"{what} SHA-256")


def _expected_jobs(layout: BatchLayout) -> tuple[B.BatchJob, ...]:
    jobs = (
        Plan.experiment_2b_baseline_jobs()
        if layout.key == "exp2b"
        else Plan.sweep_002_baseline_jobs()
    )
    if (
        len(jobs) != layout.fit_count
        or sum(job.config.train.ensemble_size for job in jobs) != layout.model_count
        or any(job.config.train.batch_size != 128 for job in jobs)
    ):
        raise ValueError(f"{layout.key} exact fit/model inventory drifted")
    return jobs


def _plan_paths() -> tuple[Path, Path]:
    return (
        PREPARATION_ORIGINAL_ROOT / Plan.WEEK8_PLAN_FILE,
        PREPARATION_COPY_ROOT / Plan.WEEK8_PLAN_FILE,
    )


def prepare(*, expected_git_commit: str) -> dict[str, Any]:
    """Create and independently retain the exact 128-fit baseline plan."""

    _validate_fixed_layout()
    commit = _commit(expected_git_commit)
    environment = Preflight.L._current_environment()
    device = Preflight.P._verify_device("cpu")
    if environment["git"]["commit"] != commit:
        raise ValueError("requested commit differs from the clean current commit")
    original, copied = _create_preparation()
    plan_path = Plan.write_week8_launch_plan(original)
    plan_copy = copied / Plan.WEEK8_PLAN_FILE
    _copy_independent(plan_path, plan_copy, what="Week-8 baseline plan")
    document = Plan.load_week8_launch_plan(plan_path)
    Plan.load_week8_launch_plan(plan_copy)
    for layout in BATCHES.values():
        _expected_jobs(layout)
    receipt = _publish_receipt(
        "prepare",
        status="complete",
        purpose="bind_exact_serial_exp2b_then_sweep_002_plan",
        payload={
            "attempt": ATTEMPT,
            "expected_git_commit": commit,
            "environment": environment,
            "route": {
                "device": device,
                "num_threads": C.CONFIRMATORY_THREADS,
                "num_interop_threads": C.CONFIRMATORY_INTEROP_THREADS,
                "gpu_used": False,
            },
            "plan": _pin(plan_path, plan_copy, what="Week-8 baseline plan"),
            "plan_digest": document["plan_digest"],
            "order": list(Plan.AUTHORIZED_BATCH_KEYS),
            "counts": {
                "exp2b": {"fits": 125, "models": 625},
                "sweep-002": {"fits": 3, "models": 15},
                "total": {"fits": 128, "models": 640},
            },
            "fixed_roots": {
                name: str(path.resolve()) for name, path in _all_fixed_roots().items()
            },
            "execution_authorized": False,
        },
    )
    return {
        "command": "prepare",
        "status": "complete",
        "plan_sha256": receipt["payload"]["plan"]["sha256"],
        "fit_count": 128,
        "model_count": 640,
        "gpu_used": False,
    }


def _load_prepare() -> dict[str, Any]:
    _validate_fixed_layout()
    receipt = _load_receipt("prepare")
    payload = _strict(
        receipt["payload"],
        {
            "attempt",
            "expected_git_commit",
            "environment",
            "route",
            "plan",
            "plan_digest",
            "order",
            "counts",
            "fixed_roots",
            "execution_authorized",
        },
        what="prepare payload",
    )
    plan_path, plan_copy = _plan_paths()
    _validate_pin(payload["plan"], plan_path, plan_copy, what="Week-8 baseline plan")
    original = Plan.load_week8_launch_plan(plan_path)
    copied = Plan.load_week8_launch_plan(plan_copy)
    if original != copied or payload["plan_digest"] != original["plan_digest"]:
        raise ValueError("prepared plan copies or registered digest diverged")
    expected_roots = {
        name: str(path.resolve()) for name, path in _all_fixed_roots().items()
    }
    environment = payload["environment"]
    if type(environment) is not dict or type(environment.get("git")) is not dict:
        raise ValueError("prepare receipt has invalid environment evidence")
    if (
        receipt["status"] != "complete"
        or payload["attempt"] != ATTEMPT
        or _commit(payload["expected_git_commit"])
        != environment["git"].get("commit")
        or payload["route"]
        != {
            "device": {
                "frozen_route": "cpu",
                "requested_route": "cpu",
                "available": True,
            },
            "num_threads": 4,
            "num_interop_threads": 4,
            "gpu_used": False,
        }
        or payload["order"] != ["exp2b", "sweep-002"]
        or payload["counts"]
        != {
            "exp2b": {"fits": 125, "models": 625},
            "sweep-002": {"fits": 3, "models": 15},
            "total": {"fits": 128, "models": 640},
        }
        or payload["fixed_roots"] != expected_roots
        or payload["execution_authorized"] is not False
    ):
        raise ValueError("prepare receipt differs from the fixed Week-8 policy")
    return receipt


def _create_batch_roots(layout: BatchLayout) -> dict[str, Path]:
    roots = _batch_roots(layout)
    if any(os.path.lexists(path) for path in roots.values()):
        raise ValueError(f"{layout.key} has a preexisting or partial execution layout")
    return {
        name: _create_direct_root(path, what=f"{layout.key} {name} root")
        for name, path in roots.items()
    }


def _preflight_receipt_name(layout: BatchLayout) -> str:
    return f"{layout.key}-preflight"


def _preflight_path(layout: BatchLayout) -> Path:
    return layout.preflight_root / Preflight.WEEK8_PREFLIGHT_FILE


def _preflight_copy_path(layout: BatchLayout) -> Path:
    return layout.sync_root / Preflight.WEEK8_PREFLIGHT_FILE


def _load_preflight(layout: BatchLayout) -> tuple[dict[str, Any], Any]:
    prepared = _load_prepare()
    receipt = _load_receipt(_preflight_receipt_name(layout))
    payload = _strict(
        receipt["payload"],
        {
            "batch_key",
            "prepare_receipt_sha256",
            "expected_git_commit",
            "plan_sha256",
            "preflight",
            "roots",
            "fit_count",
            "model_count",
            "attempt_timeout_seconds",
            "minimum_free_bytes",
            "sync_destination_identity",
            "shared_lease",
        },
        what=f"{layout.key} preflight payload",
    )
    _validate_pin(
        payload["preflight"],
        _preflight_path(layout),
        _preflight_copy_path(layout),
        what=f"{layout.key} preflight",
    )
    validated = Preflight.validate_week8_preflight(
        _preflight_path(layout),
        output_root=layout.output_root,
        sync_root=layout.sync_root,
    )
    jobs = _expected_jobs(layout)
    expected_roots = {
        name: str(path.resolve()) for name, path in _batch_roots(layout).items()
    }
    if (
        receipt["status"] != "ready"
        or payload["batch_key"] != layout.key
        or payload["prepare_receipt_sha256"] != prepared["_file_sha256"]
        or payload["expected_git_commit"]
        != prepared["payload"]["expected_git_commit"]
        or payload["plan_sha256"] != prepared["payload"]["plan"]["sha256"]
        or payload["roots"] != expected_roots
        or (payload["fit_count"], payload["model_count"])
        != (layout.fit_count, layout.model_count)
        or payload["attempt_timeout_seconds"] != ATTEMPT_TIMEOUT_SECONDS
        or payload["minimum_free_bytes"] != MINIMUM_FREE_BYTES
        or payload["sync_destination_identity"] != layout.sync_root.name
        or payload["shared_lease"]
        != {
            "root": str(Preflight._control_root()),
            "name": COMMON_LEASE_NAME,
        }
        or validated.git_commit != payload["expected_git_commit"]
        or tuple(job.as_record() for job in validated.jobs)
        != tuple(job.as_record() for job in jobs)
    ):
        raise ValueError(f"{layout.key} preflight handoff diverged")
    return receipt, validated


def _run_preflight(layout: BatchLayout) -> dict[str, Any]:
    prepared = _load_prepare()
    if layout.key == "sweep-002":
        _require_complete(EXP2B)
    roots = _create_batch_roots(layout)
    plan_path, _ = _plan_paths()
    Preflight.run_week8_preflight(
        plan_path=plan_path,
        batch_key=layout.key,
        preflight_dir=roots["preflight"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        sync_destination_identity=layout.sync_root.name,
        minimum_free_bytes=MINIMUM_FREE_BYTES,
    )
    validated = Preflight.validate_week8_preflight(
        _preflight_path(layout),
        output_root=layout.output_root,
        sync_root=layout.sync_root,
    )
    if (
        validated.git_commit != prepared["payload"]["expected_git_commit"]
        or len(validated.jobs) != layout.fit_count
        or sum(job.config.train.ensemble_size for job in validated.jobs)
        != layout.model_count
    ):
        raise ValueError(f"{layout.key} preflight returned a different exact batch")
    receipt = _publish_receipt(
        _preflight_receipt_name(layout),
        status="ready",
        purpose=f"bind_fixed_{layout.key}_readiness_before_any_fit",
        payload={
            "batch_key": layout.key,
            "prepare_receipt_sha256": prepared["_file_sha256"],
            "expected_git_commit": validated.git_commit,
            "plan_sha256": prepared["payload"]["plan"]["sha256"],
            "preflight": _pin(
                _preflight_path(layout),
                _preflight_copy_path(layout),
                what=f"{layout.key} preflight",
            ),
            "roots": {
                name: str(path.resolve()) for name, path in roots.items()
            },
            "fit_count": layout.fit_count,
            "model_count": layout.model_count,
            "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
            "minimum_free_bytes": MINIMUM_FREE_BYTES,
            "sync_destination_identity": layout.sync_root.name,
            "shared_lease": {
                "root": str(Preflight._control_root()),
                "name": COMMON_LEASE_NAME,
            },
        },
    )
    _load_preflight(layout)
    return {
        "command": f"preflight-{layout.key}",
        "status": "ready",
        "preflight_sha256": receipt["payload"]["preflight"]["sha256"],
        "fit_count": layout.fit_count,
        "model_count": layout.model_count,
        "gpu_used": False,
    }


def preflight_exp2b() -> dict[str, Any]:
    return _run_preflight(EXP2B)


def preflight_sweep_002() -> dict[str, Any]:
    return _run_preflight(SWEEP_002)


def _paired_json_inventory(
    left: Path, right: Path, *, what: str, required: bool
) -> dict[str, tuple[Path, Path, str]]:
    left_exists = os.path.lexists(left)
    right_exists = os.path.lexists(right)
    if left_exists != right_exists:
        raise ValueError(f"{what} original/copy directory history diverged")
    if not left_exists:
        if required:
            raise ValueError(f"{what} history is missing")
        return {}
    first = _plain_directory(left, what=f"{what} original directory")
    second = _plain_directory(right, what=f"{what} copy directory")
    first_children = {child.name: child for child in first.iterdir()}
    second_children = {child.name: child for child in second.iterdir()}
    if set(first_children) != set(second_children):
        raise ValueError(f"{what} original/copy inventory diverged")
    result: dict[str, tuple[Path, Path, str]] = {}
    for name in sorted(first_children):
        if not name.endswith(".json"):
            raise ValueError(f"{what} contains a non-JSON history entry")
        token = name[:-5]
        if _TOKEN.fullmatch(token) is None or token in result:
            raise ValueError(f"{what} contains a noncanonical or duplicate token")
        left_file = _plain_file(first_children[name], what=f"{what} original entry")
        right_file = _plain_file(second_children[name], what=f"{what} copy entry")
        result[token] = (
            left_file,
            right_file,
            _independent_equal(left_file, right_file, what=f"{what} {token}"),
        )
    return result


def _history(layout: BatchLayout, validated: Any) -> dict[str, Any]:
    manifest = B._manifest(validated.jobs)
    local_batch = layout.output_root / manifest["batch_id"]
    copy_batch = layout.sync_root / manifest["batch_id"]
    local_exists = os.path.lexists(local_batch)
    copy_exists = os.path.lexists(copy_batch)
    if local_exists != copy_exists:
        raise ValueError(f"{layout.key} local/durable batch history diverged")
    if local_exists:
        _plain_directory(local_batch, what=f"{layout.key} local batch directory")
        _plain_directory(copy_batch, what=f"{layout.key} durable batch directory")
    starts = _paired_json_inventory(
        local_batch / Launch.WEEK8_START_DIRECTORY,
        copy_batch / Launch.WEEK8_START_DIRECTORY,
        what=f"{layout.key} launch-start",
        required=False,
    ) if local_exists else {}
    local_report_history = layout.output_root / Launch.WEEK8_REPORT_DIRECTORY
    copy_report_history = layout.sync_root / Launch.WEEK8_REPORT_DIRECTORY
    report_history_present = os.path.lexists(local_report_history) or os.path.lexists(
        copy_report_history
    )
    reports = _paired_json_inventory(
        local_report_history,
        copy_report_history,
        what=f"{layout.key} launch-report",
        required=False,
    )
    if not starts and (local_exists or report_history_present):
        raise ValueError(
            f"{layout.key} has preserved partial state before any launch-start; "
            "completed-report recovery is the only post-start path"
        )
    if len(starts) > 1 or len(reports) > 1 or not set(reports).issubset(starts):
        raise ValueError(f"{layout.key} attempt-001 history overlaps or diverges")
    for token, (path, _copy, _digest) in starts.items():
        _, start, context = Monitor._load_launch_start(path)
        if (
            start["batch_key"] != layout.key
            or start["lease"]["token"] != token
            or context["manifest"] != manifest
        ):
            raise ValueError(f"{layout.key} launch-start history changed identity")
    for token, (path, _copy, _digest) in reports.items():
        document = read_json(path)
        if path.read_bytes() != Preflight.L._pretty_json_bytes(document):
            raise ValueError(f"{layout.key} launch report is not canonical JSON")
        if type(document) is not dict or document.get("batch_key") != layout.key:
            raise ValueError(f"{layout.key} launch report changed batch identity")
        released = document.get("released_lease")
        start = document.get("start")
        start_record = start.get("record") if type(start) is dict else None
        start_lease = (
            start_record.get("lease") if type(start_record) is dict else None
        )
        if (
            type(released) is not dict
            or released.get("token") != token
            or type(start) is not dict
            or type(start_record) is not dict
            or type(start_lease) is not dict
            or start_lease.get("token") != token
        ):
            raise ValueError(f"{layout.key} launch report token history diverged")
    return {"manifest": manifest, "starts": starts, "reports": reports}


def _control_name(layout: BatchLayout) -> str:
    return f"{layout.key}-launch-control"


def _completion_name(layout: BatchLayout) -> str:
    return f"{layout.key}-launch-complete"


def _control_payload(
    layout: BatchLayout, preflight_receipt: Mapping[str, Any], validated: Any
) -> dict[str, Any]:
    prepared = _load_prepare()
    return {
        "batch_key": layout.key,
        "prepare_receipt_sha256": prepared["_file_sha256"],
        "preflight_receipt_sha256": preflight_receipt["_file_sha256"],
        "plan_sha256": prepared["payload"]["plan"]["sha256"],
        "preflight_sha256": validated.report_sha256,
        "preflight_path": str(validated.report_path),
        "expected_git_commit": validated.git_commit,
        "roots": {
            name: str(path.resolve()) for name, path in _batch_roots(layout).items()
        },
        "fit_count": layout.fit_count,
        "model_count": layout.model_count,
        "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
        "shared_lease": {
            "root": str(Preflight._control_root()),
            "name": COMMON_LEASE_NAME,
        },
        "automatic_retry_allowed": False,
        "scientific_analysis_performed": False,
    }


def _load_control(layout: BatchLayout) -> tuple[dict[str, Any], Any]:
    preflight_receipt, validated = _load_preflight(layout)
    receipt = _load_receipt(_control_name(layout))
    if (
        receipt["status"] != "armed_before_blocking_launch"
        or receipt["payload"]
        != _control_payload(layout, preflight_receipt, validated)
    ):
        raise ValueError(f"{layout.key} launch control diverged")
    return receipt, validated


def _arm(layout: BatchLayout) -> tuple[dict[str, Any], Any]:
    if layout is SWEEP_002:
        _require_complete(EXP2B)
    preflight_receipt, validated = _load_preflight(layout)
    history = _history(layout, validated)
    if history["starts"] or history["reports"]:
        raise ValueError(f"{layout.key} already has launch history")
    receipt = _publish_receipt(
        _control_name(layout),
        status="armed_before_blocking_launch",
        purpose=f"publish_stable_{layout.key}_control_before_blocking_launch",
        payload=_control_payload(layout, preflight_receipt, validated),
    )
    return receipt, validated


def _validated_complete_report(
    layout: BatchLayout, validated: Any, history: Mapping[str, Any]
) -> dict[str, Any]:
    starts = history["starts"]
    reports = history["reports"]
    if len(starts) != 1 or set(starts) != set(reports):
        raise ValueError(f"{layout.key} has no single complete launch/report history")
    token = next(iter(starts))
    start_path, start_copy, start_sha = starts[token]
    report_path, report_copy, report_sha = reports[token]
    _, start, _context = Monitor._load_launch_start(start_path)
    lease_evidence = Monitor._lease_evidence_for_start(start)
    report = _strict(
        read_json(report_path),
        {
            "week8_launch_schema_version",
            "status",
            "finished_at",
            "launch_performed",
            "batch_key",
            "preflight",
            "start",
            "failure",
            "batch",
            "scientific_analysis_performed",
            "released_lease",
        },
        what=f"{layout.key} complete launch report",
    )
    start_pin = _strict(
        report["start"],
        {"local_path", "durable_path", "sha256", "record"},
        what=f"{layout.key} launch-start report pin",
    )
    released = _strict(
        report["released_lease"],
        {"token", "path"},
        what=f"{layout.key} released-lease report pin",
    )
    counts = _strict(
        report["batch"],
        {
            "batch_id",
            "total",
            "executed",
            "resumed",
            "synced",
            "failed",
            "sync_failed",
            "complete",
        },
        what=f"{layout.key} batch accounting",
    )
    Monitor.M._require_timestamp(report["finished_at"], what="finished_at")
    integer_counts = ("total", "executed", "resumed", "synced", "failed", "sync_failed")
    if any(
        type(counts[name]) is not int or counts[name] < 0
        for name in integer_counts
    ):
        raise ValueError(
            f"{layout.key} launch accounting has non-integer or negative counts"
        )
    if (
        report["week8_launch_schema_version"] != Launch.WEEK8_LAUNCH_SCHEMA_VERSION
        or report["status"] != "complete"
        or report["launch_performed"] is not True
        or report["batch_key"] != layout.key
        or report["failure"] is not None
        or report["scientific_analysis_performed"] is not False
        or report["preflight"]
        != {
            "path": str(validated.report_path),
            "sha256": validated.report_sha256,
            "git_commit": validated.git_commit,
        }
        or start_pin["sha256"] != start_sha
        or start_pin["local_path"] != str(start_path)
        or start_pin["durable_path"] != str(start_copy)
        or start_pin["record"] != start
        or released["token"] != token
        or released["path"] != lease_evidence["path"]
        or lease_evidence["state"] != "released"
        or counts["batch_id"] != history["manifest"]["batch_id"]
        or counts["total"] != layout.fit_count
        or counts["executed"] != layout.fit_count
        or counts["resumed"] != 0
        or counts["synced"] != layout.fit_count
        or counts["failed"] != 0
        or counts["sync_failed"] != 0
        or counts["complete"] is not True
    ):
        raise ValueError(f"{layout.key} launch report is partial, failed, or divergent")
    return {
        "token": token,
        "start_path": start_path,
        "start_copy_path": start_copy,
        "start_sha256": start_sha,
        "report_path": report_path,
        "report_copy_path": report_copy,
        "report_sha256": report_sha,
        "executed": counts["executed"],
        "resumed": counts["resumed"],
        "synced": counts["synced"],
    }


def _completion_payload(
    layout: BatchLayout,
    control: Mapping[str, Any],
    complete: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "batch_key": layout.key,
        "launch_control_receipt_sha256": control["_file_sha256"],
        "expected_git_commit": control["payload"]["expected_git_commit"],
        "start": {
            "path": str(complete["start_path"]),
            "copy_path": str(complete["start_copy_path"]),
            "sha256": complete["start_sha256"],
        },
        "report": {
            "path": str(complete["report_path"]),
            "copy_path": str(complete["report_copy_path"]),
            "sha256": complete["report_sha256"],
        },
        "accounting": {
            "fits": layout.fit_count,
            "models": layout.model_count,
            "executed": complete["executed"],
            "resumed": complete["resumed"],
            "synced": complete["synced"],
            "failed": 0,
            "sync_failed": 0,
        },
        "shared_lease_released": True,
        "automatic_retry_performed": False,
        "scientific_analysis_performed": False,
    }


def _publish_completion(
    layout: BatchLayout, control: Mapping[str, Any], validated: Any
) -> dict[str, Any]:
    history = _history(layout, validated)
    complete = _validated_complete_report(layout, validated, history)
    receipt = _publish_receipt(
        _completion_name(layout),
        status="complete",
        purpose=f"bind_complete_durable_{layout.key}_batch",
        payload=_completion_payload(layout, control, complete),
    )
    return {**complete, "completion_receipt": receipt}


def _require_complete(layout: BatchLayout) -> dict[str, Any]:
    control, validated = _load_control(layout)
    complete = _validated_complete_report(layout, validated, _history(layout, validated))
    receipt = _load_receipt(_completion_name(layout))
    if (
        receipt["status"] != "complete"
        or receipt["payload"] != _completion_payload(layout, control, complete)
    ):
        raise ValueError(f"{layout.key} completion receipt diverged")
    return receipt


def _launch(layout: BatchLayout) -> dict[str, Any]:
    if layout.key == "sweep-002":
        _require_complete(EXP2B)
    control_paths = _receipt_paths(_control_name(layout))
    control_exists = tuple(os.path.lexists(path) for path in control_paths)
    if control_exists == (True, True):
        control, validated = _load_control(layout)
    elif control_exists == (False, False):
        # Arming is deterministic and happens before the blocking low-level call.
        control, validated = _arm(layout)
    else:
        raise ValueError(f"{layout.key} launch-control copies are partial")
    history = _history(layout, validated)
    if history["starts"] or history["reports"]:
        # A crash after a complete low-level report is recoverable without a fit.
        complete = _publish_completion(layout, control, validated)
    else:
        result = Launch.launch_week8(
            preflight_report=validated.report_path,
            output_root=layout.output_root,
            sync_root=layout.sync_root,
            attempt_timeout_seconds=ATTEMPT_TIMEOUT_SECONDS,
        )
        if type(result) is not dict or result.get("status") != "complete":
            raise ValueError(f"{layout.key} low-level launch did not complete")
        complete = _publish_completion(layout, control, validated)
    return {
        "command": f"launch-{layout.key}",
        "status": "complete",
        "report_sha256": complete["report_sha256"],
        "start_sha256": complete["start_sha256"],
        "fit_count": layout.fit_count,
        "model_count": layout.model_count,
        "gpu_used": False,
        "automatic_retry_performed": False,
    }


def launch_exp2b() -> dict[str, Any]:
    return _launch(EXP2B)


def launch_sweep_002() -> dict[str, Any]:
    return _launch(SWEEP_002)


def _ensure_monitor_roots(layout: BatchLayout) -> tuple[Path, Path]:
    first_exists = os.path.lexists(layout.monitor_root)
    second_exists = os.path.lexists(layout.monitor_copy_root)
    if first_exists != second_exists:
        raise ValueError(f"{layout.key} monitor roots are partial")
    if not first_exists:
        return (
            _create_direct_root(layout.monitor_root, what=f"{layout.key} monitor root"),
            _create_direct_root(
                layout.monitor_copy_root,
                what=f"{layout.key} independent monitor root",
            ),
        )
    return (
        _plain_directory(layout.monitor_root, what=f"{layout.key} monitor root"),
        _plain_directory(
            layout.monitor_copy_root, what=f"{layout.key} independent monitor root"
        ),
    )


def _monitor_inventory(layout: BatchLayout) -> tuple[Path, Path, int]:
    first, second = _ensure_monitor_roots(layout)
    first_rows = {child.name: child for child in first.iterdir()}
    second_rows = {child.name: child for child in second.iterdir()}
    if set(first_rows) != set(second_rows):
        raise ValueError(f"{layout.key} monitor-copy history diverged")
    indices: list[int] = []
    for name in sorted(first_rows):
        match = _SNAPSHOT.fullmatch(name)
        if match is None:
            raise ValueError(f"{layout.key} monitor root contains unknown evidence")
        _independent_equal(
            first_rows[name], second_rows[name], what=f"{layout.key} monitor snapshot"
        )
        document = read_json(first_rows[name])
        if type(document) is not dict:
            raise ValueError(f"{layout.key} monitor history is not a JSON object")
        supplied = Monitor.M._require_sha256(
            document.get("snapshot_id"), what="historical snapshot_id"
        )
        payload = {key: value for key, value in document.items() if key != "snapshot_id"}
        batch = document.get("batch")
        if (
            Monitor.M._canonical_digest(payload) != supplied
            or document.get("week8_monitor_schema_version")
            != Monitor.WEEK8_MONITOR_SCHEMA_VERSION
            or type(batch) is not dict
            or batch.get("batch_key") != layout.key
            or batch.get("job_count") != layout.fit_count
        ):
            raise ValueError(f"{layout.key} monitor history changed schema or identity")
        indices.append(int(match.group(1)))
    if indices != list(range(1, len(indices) + 1)):
        raise ValueError(f"{layout.key} monitor history is not contiguous")
    return first, second, len(indices) + 1


def _monitor(layout: BatchLayout) -> dict[str, Any]:
    _control, validated = _load_control(layout)
    history = _history(layout, validated)
    if not history["starts"]:
        return {
            "command": f"monitor-{layout.key}",
            "status": "awaiting_start",
            "fit_count": layout.fit_count,
            "synced": 0,
            "remaining": layout.fit_count,
            "gpu_used": False,
        }
    if history["reports"]:
        report = read_json(next(iter(history["reports"].values()))[0])
        if report.get("status") != "complete":
            raise ValueError(f"{layout.key} has terminal non-complete launch evidence")
        _validated_complete_report(layout, validated, history)
    token = next(iter(history["starts"]))
    start_path = history["starts"][token][0]
    original_root, copied_root, index = _monitor_inventory(layout)
    name = f"snapshot-{index:06d}.json"
    original_path = original_root / name
    copy_path = copied_root / name
    snapshot = Monitor.snapshot_week8_batch(
        launch_start_receipt=start_path,
        snapshot_path=original_path,
    )
    _copy_independent(original_path, copy_path, what=f"{layout.key} monitor snapshot")
    copied = Monitor.validate_week8_monitor_snapshot(copy_path)
    if snapshot != copied:
        raise ValueError(f"{layout.key} monitor copy failed strict source reload")
    scientific = snapshot.get("scientific_analysis")
    counts = _strict(
        snapshot.get("counts"),
        {
            "started",
            "completed",
            "resumed",
            "failed_events",
            "sync_failed_events",
            "synced",
            "outstanding",
        },
        what=f"{layout.key} monitor counts",
    )
    batch = snapshot.get("batch")
    count_names = tuple(counts)
    if (
        scientific
        != {
            "performed": False,
            "outcomes": None,
            "labels": None,
            "h2_verdict": None,
        }
        or type(batch) is not dict
        or batch.get("batch_key") != layout.key
        or batch.get("job_count") != layout.fit_count
        or snapshot.get("status") not in {"in_progress", "complete"}
        or any(type(counts[key]) is not int or counts[key] < 0 for key in count_names)
        or counts["synced"] + counts["outstanding"] != layout.fit_count
    ):
        raise ValueError(f"{layout.key} monitor crossed the operational-only boundary")
    if counts.get("failed_events", 0) or counts.get("sync_failed_events", 0):
        raise ValueError(f"{layout.key} monitor found operational failure evidence")
    return {
        "command": f"monitor-{layout.key}",
        "status": snapshot["status"],
        "snapshot_sha256": sha256_file(original_path),
        "fit_count": layout.fit_count,
        "synced": counts["synced"],
        "remaining": counts["outstanding"],
        "gpu_used": False,
    }


def monitor_exp2b() -> dict[str, Any]:
    return _monitor(EXP2B)


def monitor_sweep_002() -> dict[str, Any]:
    return _monitor(SWEEP_002)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--expected-git-commit", required=True)
    for name in (
        "preflight-exp2b",
        "launch-exp2b",
        "monitor-exp2b",
        "preflight-sweep-002",
        "launch-sweep-002",
        "monitor-sweep-002",
    ):
        commands.add_parser(name)
    return parser


def _operational_failure(command: str, exc: Exception) -> dict[str, str]:
    """Return a deterministic failure token without exposing exception text."""

    failure_type = type(exc).__name__
    failure_sha256 = sha256_bytes(
        _canonical(
            {
                "failure_type": failure_type,
                "failure_message": str(exc),
            }
        )
    )
    return {
        "command": command,
        "status": "failed",
        "failure_type": failure_type,
        "failure_sha256": failure_sha256,
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = vars(_parser().parse_args(argv))
    command = arguments.pop("command")
    handlers = {
        "prepare": prepare,
        "preflight-exp2b": preflight_exp2b,
        "launch-exp2b": launch_exp2b,
        "monitor-exp2b": monitor_exp2b,
        "preflight-sweep-002": preflight_sweep_002,
        "launch-sweep-002": launch_sweep_002,
        "monitor-sweep-002": monitor_sweep_002,
    }
    try:
        result = handlers[command](**arguments)
    except Exception as exc:
        print(
            json.dumps(
                _operational_failure(command, exc),
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 1
    # Every public result is deliberately operational-only.
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
