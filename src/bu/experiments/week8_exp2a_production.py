"""Fixed, receipt-driven Week-8 Experiment-2A production orchestration.

This module removes path, hash and phase-handoff discretion from the Week-8
Experiment-2A operating sequence.  It delegates all scientific work to the
existing certified layers and adds only immutable preparation/control receipts,
fixed attempt-001 paths and an outcome-blind operational monitor.

The monitor is intentionally independent of
``week8_exp2a_repair_launch._load_events``.  It never heals evidence and never
opens fit, label, scientific-report or figure files.  It reads only the
independently copied control receipt, start checkpoint, event stream and
terminal operational launch report, then publishes an independently copied
snapshot containing operational counts.  Failure text is represented only by
a SHA-256 digest.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..durable import (
    atomic_write_bytes,
    atomic_write_json,
    read_json,
    sha256_bytes,
    sha256_file,
)
from . import experiment_2a_figures as Figures
from . import fit_evidence as Fit
from . import week8_exp2a_label_finalization as Finalize
from . import week8_exp2a_repair_launch as Launch
from . import week8_exp2a_repairs as Plan
from . import week8_exp2a_reporting as Reporting
from . import week8_exp2a_sources as Sources


PRODUCTION_SCHEMA_VERSION = 2
MONITOR_SCHEMA_VERSION = 2
ATTEMPT_TIMEOUT_SECONDS = 3600.0
MINIMUM_FREE_BYTES = 8_589_934_592
SYNC_DESTINATION_IDENTITY = "week8-exp2a-2026-09-01-attempt-001-project-evidence"

_REGISTERED_WORKSPACE_ROOT = Path("D:/Aenv/pro/pro")
WORKSPACE_ROOT = Plan.WORKSPACE_ROOT
PREPARATION_ROOT = (
    WORKSPACE_ROOT / "week8-execution-preparation-2026-09-01-attempt-001"
)
PREPARATION_ORIGINAL_ROOT = PREPARATION_ROOT / "exp2a-original"
PREPARATION_COPY_ROOT = PREPARATION_ROOT / "exp2a-project-evidence"
PREFLIGHT_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-preflight"
OUTPUT_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-output"
STAGING_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-staging"
SYNC_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-project-evidence"
)
LABEL_EXPORT_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-labels-2026-09-01-attempt-001"
)
LABEL_COPY_ROOT = (
    WORKSPACE_ROOT
    / "week8-exp2a-labels-2026-09-01-attempt-001-project-evidence"
)
REPORT_ROOT = WORKSPACE_ROOT / "week8-exp2a-report-2026-09-01-attempt-001"
REPORT_COPY_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-report-2026-09-01-attempt-001-project-evidence"
)
FIGURE_ROOT = WORKSPACE_ROOT / "week8-exp2a-figures-2026-09-01-attempt-001"
FIGURE_CACHE_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-figures-2026-09-01-attempt-001-mpl-cache"
)
MONITOR_ROOT = WORKSPACE_ROOT / "week8-exp2a-monitor-2026-09-01-attempt-001"
MONITOR_COPY_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-monitor-2026-09-01-attempt-001-project-evidence"
)

REPORT_FILE = "experiment_2a_report.json"
REPORT_BINDING_FILE = "experiment_2a_reporting_binding.json"
_PHASES = {
    "prepare",
    "preflight",
    "launch-control",
    "launch",
    "finalize",
    "report",
    "figures",
}
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN_FILE = re.compile(r"([0-9a-f]{32})\.json\Z")
_EVENT_FILE = re.compile(r"[0-9]{6}\.json\Z")


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
        raise ValueError("Week-8 E2A production evidence must be strict JSON") from exc


def _expect_keys(value: object, keys: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(f"{what} has missing or extra fields")
    return value


def _sha(value: object, *, what: str) -> str:
    if type(value) is not str or not _HEX64.fullmatch(value):
        raise ValueError(f"{what} must be canonical lowercase SHA256")
    return value


def _commit(value: object) -> str:
    if type(value) is not str or not _HEX40.fullmatch(value):
        raise ValueError("expected Git commit must be canonical lowercase 40-hex")
    return Fit._validate_expected_git_commit(value)


def _fixed_roots() -> dict[str, Path]:
    """Return the live constants so tests can relocate the whole fixed layout."""

    return {
        "preparation": PREPARATION_ROOT,
        "preparation_original": PREPARATION_ORIGINAL_ROOT,
        "preparation_copy": PREPARATION_COPY_ROOT,
        "preflight": PREFLIGHT_ROOT,
        "output": OUTPUT_ROOT,
        "staging": STAGING_ROOT,
        "sync": SYNC_ROOT,
        "label_export": LABEL_EXPORT_ROOT,
        "label_copy": LABEL_COPY_ROOT,
        "report": REPORT_ROOT,
        "report_copy": REPORT_COPY_ROOT,
        "figures": FIGURE_ROOT,
        "figure_cache": FIGURE_CACHE_ROOT,
        "monitor": MONITOR_ROOT,
        "monitor_copy": MONITOR_COPY_ROOT,
    }


def _overlap(left: Path, right: Path) -> bool:
    left = Path(os.path.abspath(left))
    right = Path(os.path.abspath(right))
    return left == right or left in right.parents or right in left.parents


def _validate_fixed_layout() -> None:
    workspace = Path(os.path.abspath(WORKSPACE_ROOT))
    roots = _fixed_roots()
    absolute_roots = {
        name: Path(os.path.abspath(path)) for name, path in roots.items()
    }
    values = tuple(absolute_roots.values())
    if any(path == workspace or not path.is_relative_to(workspace) for path in values):
        raise ValueError("every Week-8 E2A production root must be a workspace child")
    allowed_nested = {
        frozenset((Path(os.path.abspath(PREPARATION_ROOT)), Path(os.path.abspath(PREPARATION_ORIGINAL_ROOT)))),
        frozenset((Path(os.path.abspath(PREPARATION_ROOT)), Path(os.path.abspath(PREPARATION_COPY_ROOT)))),
    }
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            if _overlap(left, right) and frozenset((left, right)) not in allowed_nested:
                raise ValueError("fixed Week-8 E2A roots unexpectedly overlap")
    # Keep the production-name guard anchored to the literal registered
    # workspace.  Tests relocate Plan.WORKSPACE_ROOT because the lower path
    # validators share it; consulting that mutable test seam here would make a
    # relocated fixture indistinguishable from the real attempt-001 layout.
    registered_workspace = Path(os.path.abspath(_REGISTERED_WORKSPACE_ROOT))
    if workspace == registered_workspace:
        expected = {
            "preparation": workspace / "week8-execution-preparation-2026-09-01-attempt-001",
            "preparation_original": workspace / "week8-execution-preparation-2026-09-01-attempt-001" / "exp2a-original",
            "preparation_copy": workspace / "week8-execution-preparation-2026-09-01-attempt-001" / "exp2a-project-evidence",
            "preflight": workspace / "week8-exp2a-2026-09-01-attempt-001-preflight",
            "output": workspace / "week8-exp2a-2026-09-01-attempt-001-output",
            "staging": workspace / "week8-exp2a-2026-09-01-attempt-001-staging",
            "sync": workspace / "week8-exp2a-2026-09-01-attempt-001-project-evidence",
            "label_export": workspace / "week8-exp2a-labels-2026-09-01-attempt-001",
            "label_copy": workspace / "week8-exp2a-labels-2026-09-01-attempt-001-project-evidence",
            "report": workspace / "week8-exp2a-report-2026-09-01-attempt-001",
            "report_copy": workspace / "week8-exp2a-report-2026-09-01-attempt-001-project-evidence",
            "figures": workspace / "week8-exp2a-figures-2026-09-01-attempt-001",
            "figure_cache": workspace / "week8-exp2a-figures-2026-09-01-attempt-001-mpl-cache",
            "monitor": workspace / "week8-exp2a-monitor-2026-09-01-attempt-001",
            "monitor_copy": workspace / "week8-exp2a-monitor-2026-09-01-attempt-001-project-evidence",
        }
        if absolute_roots != expected:
            raise ValueError("fixed Week-8 E2A attempt-001 root names drifted")
    if (
        ATTEMPT_TIMEOUT_SECONDS != 3600.0
        or type(MINIMUM_FREE_BYTES) is not int
        or MINIMUM_FREE_BYTES != 8_589_934_592
        or Plan.COMMON_LEASE_NAME != "week7-production"
        or Plan.COMMON_LEASE_ROOT
        != WORKSPACE_ROOT / "week7-production-control"
    ):
        raise ValueError("Week-8 E2A fixed resource or shared-lease policy drifted")


def _ensure_directory(path: Path) -> Path:
    """Create one fixed project-local directory, then recheck links/reparse."""

    candidate = Plan._project_path(path, directory=True, existing=False)
    candidate.mkdir(parents=True, exist_ok=True)
    return Plan._project_path(candidate, directory=True)


def _plain_file(path: Path, *, what: str) -> Path:
    target = Plan._project_path(path, directory=False)
    try:
        info = target.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {what}: {target}") from exc
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    attributes = int(getattr(info, "st_file_attributes", 0))
    if (
        stat.S_ISLNK(info.st_mode)
        or attributes & reparse
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
    ):
        raise ValueError(f"{what} must be an independent regular non-link file")
    return target


def _independent_equal(left: Path, right: Path, *, what: str) -> str:
    left = _plain_file(left, what=f"{what} original")
    right = _plain_file(right, what=f"{what} copy")
    if left == right or _overlap(left, right):
        raise ValueError(f"{what} files must be in non-overlapping paths")
    try:
        aliases = os.path.samefile(left, right)
    except OSError as exc:
        raise ValueError(f"cannot compare {what} file identities") from exc
    if aliases:
        raise ValueError(f"{what} files alias the same filesystem object")
    left_bytes = left.read_bytes()
    right_bytes = right.read_bytes()
    if left_bytes != right_bytes:
        raise ValueError(f"{what} independent bytes differ")
    digest = sha256_bytes(left_bytes)
    if sha256_file(left) != digest or sha256_file(right) != digest:
        raise ValueError(f"{what} changed during read-back")
    return digest


def _copy_file(source: Path, destination: Path, *, what: str) -> str:
    source = _plain_file(source, what=f"{what} source")
    destination = atomic_write_bytes(destination, source.read_bytes())
    return _independent_equal(source, destination, what=what)


def _receipt_paths(phase: str) -> tuple[Path, Path]:
    if phase not in _PHASES:
        raise ValueError(f"unknown Week-8 E2A production phase: {phase!r}")
    return (
        PREPARATION_ORIGINAL_ROOT / "receipts" / f"{phase}.json",
        PREPARATION_COPY_ROOT / "receipts" / f"{phase}.json",
    )


def _publish_receipt(
    phase: str,
    *,
    status: str,
    purpose: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    original, copy = _receipt_paths(phase)
    _ensure_directory(original.parent)
    _ensure_directory(copy.parent)
    document = Plan._seal(
        {
            "week8_exp2a_production_schema_version": PRODUCTION_SCHEMA_VERSION,
            "phase": phase,
            "purpose": purpose,
            "status": status,
            "receipt_paths": {
                "original": str(original.resolve()),
                "copy": str(copy.resolve()),
            },
            "payload": dict(payload),
        },
        "receipt_digest",
    )
    atomic_write_json(original, document)
    atomic_write_json(copy, document)
    digest = _independent_equal(original, copy, what=f"{phase} receipt")
    if read_json(original) != document or read_json(copy) != document:
        raise ValueError(f"persisted {phase} receipt differs from its document")
    document["_file_sha256"] = digest
    return document


def _load_receipt(phase: str) -> dict[str, Any]:
    original, copy = _receipt_paths(phase)
    digest = _independent_equal(original, copy, what=f"{phase} receipt")
    document = _expect_keys(
        read_json(original),
        {
            "week8_exp2a_production_schema_version",
            "phase",
            "purpose",
            "status",
            "receipt_paths",
            "payload",
            "receipt_digest",
        },
        what=f"{phase} receipt",
    )
    if (
        document["week8_exp2a_production_schema_version"]
        != PRODUCTION_SCHEMA_VERSION
        or document["phase"] != phase
        or type(document["purpose"]) is not str
        or type(document["status"]) is not str
        or type(document["payload"]) is not dict
        or document["receipt_paths"]
        != {"original": str(original.resolve()), "copy": str(copy.resolve())}
    ):
        raise ValueError(f"{phase} receipt identity/schema drifted")
    _sha(document["receipt_digest"], what=f"{phase} receipt digest")
    expected = Plan._seal(
        {key: value for key, value in document.items() if key != "receipt_digest"},
        "receipt_digest",
    )
    if document != expected or read_json(copy) != document:
        raise ValueError(f"{phase} receipt digest or independent copy differs")
    return {**document, "_file_sha256": digest}


def _pin_row(path: Path, copy: Path, *, what: str) -> dict[str, Any]:
    digest = _independent_equal(path, copy, what=what)
    return {
        "path": str(path.resolve()),
        "copy_path": str(copy.resolve()),
        "sha256": digest,
        "independent_copy": True,
    }


def _validate_pin(row: object, path: Path, copy: Path, *, what: str) -> str:
    row = _expect_keys(
        row,
        {"path", "copy_path", "sha256", "independent_copy"},
        what=f"{what} pin",
    )
    expected = {
        "path": str(path.resolve()),
        "copy_path": str(copy.resolve()),
        "sha256": _independent_equal(path, copy, what=what),
        "independent_copy": True,
    }
    if row != expected:
        raise ValueError(f"{what} pin differs from fixed independent evidence")
    return _sha(row["sha256"], what=f"{what} SHA256")


def _nonnegative_int(value: object, *, what: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{what} must be an exact nonnegative integer")
    return value


def _receipt_present(phase: str) -> bool:
    """Return true only for a complete receipt pair; never heal one missing twin."""

    original, copy = _receipt_paths(phase)
    present = tuple(os.path.lexists(path) for path in (original, copy))
    if any(present) and not all(present):
        raise ValueError(f"{phase} receipt has only one preserved twin")
    return all(present)


def _route_payload(environment: Mapping[str, Any]) -> dict[str, Any]:
    device = environment.get("device")
    if (
        type(device) is not dict
        or device.get("frozen_route") != "cpu"
        or device.get("requested_route") != "cpu"
        or device.get("available") is not True
        or environment.get("num_threads") != 4
        or environment.get("num_interop_threads") != 4
    ):
        raise ValueError("Week-8 E2A production requires the frozen CPU 4/4 route")
    return {
        "device": "cpu",
        "num_threads": 4,
        "num_interop_threads": 4,
        "gpu_used": False,
    }


def _load_prepare(expected_commit: str | None = None) -> dict[str, Any]:
    receipt = _load_receipt("prepare")
    payload = _expect_keys(
        receipt["payload"],
        {
            "expected_git_commit",
            "route",
            "plan",
            "source_ledger",
            "plan_digest",
            "fixed_paths",
            "execution_authorized",
        },
        what="prepare payload",
    )
    commit = _commit(payload["expected_git_commit"])
    if expected_commit is not None and commit != _commit(expected_commit):
        raise ValueError("requested commit differs from immutable preparation")
    if payload["route"] != {
        "device": "cpu",
        "num_threads": 4,
        "num_interop_threads": 4,
        "gpu_used": False,
    } or payload["execution_authorized"] is not False:
        raise ValueError("prepare receipt changed the fixed route or authorization")
    plan_path = PREPARATION_ORIGINAL_ROOT / Plan.PLAN_FILE
    plan_copy = PREPARATION_COPY_ROOT / Plan.PLAN_FILE
    ledger_path = PREPARATION_ORIGINAL_ROOT / Sources.SOURCE_LEDGER_FILE
    ledger_copy = PREPARATION_COPY_ROOT / Sources.SOURCE_LEDGER_FILE
    _validate_pin(payload["plan"], plan_path, plan_copy, what="E2A plan")
    _validate_pin(
        payload["source_ledger"], ledger_path, ledger_copy, what="E2A source ledger"
    )
    if payload["fixed_paths"] != {
        name: str(path.resolve()) for name, path in _fixed_roots().items()
    }:
        raise ValueError("prepare receipt does not bind the exact attempt-001 layout")
    if type(payload["plan_digest"]) is not str:
        raise ValueError("prepare receipt lacks the registered plan digest")
    return receipt


def prepare(*, expected_git_commit: str) -> dict[str, Any]:
    """Build/copy the plan and 155-source ledger, then bind them immutably."""

    _validate_fixed_layout()
    commit = _commit(expected_git_commit)
    environment = Launch._environment(commit)
    route = _route_payload(environment)
    original = _ensure_directory(PREPARATION_ORIGINAL_ROOT)
    copy = _ensure_directory(PREPARATION_COPY_ROOT)
    plan_path = Plan.write_exp2a_repair_plan(original)
    ledger_path = Sources.write_exp2a_source_ledger(original)
    plan_copy = copy / Plan.PLAN_FILE
    ledger_copy = copy / Sources.SOURCE_LEDGER_FILE
    _copy_file(plan_path, plan_copy, what="E2A plan")
    _copy_file(ledger_path, ledger_copy, what="E2A source ledger")
    plan_document = Plan.load_exp2a_repair_plan(plan_path)
    receipt = _publish_receipt(
        "prepare",
        status="complete",
        purpose="bind_exact_plan_and_155_reverified_historical_sources",
        payload={
            "expected_git_commit": commit,
            "route": route,
            "plan": _pin_row(plan_path, plan_copy, what="E2A plan"),
            "source_ledger": _pin_row(
                ledger_path, ledger_copy, what="E2A source ledger"
            ),
            "plan_digest": plan_document["plan_digest"],
            "fixed_paths": {
                name: str(path.resolve()) for name, path in _fixed_roots().items()
            },
            "execution_authorized": False,
        },
    )
    return _operational("prepare", receipt, status="complete")


def _load_preflight(expected_commit: str | None = None) -> dict[str, Any]:
    prepare_receipt = _load_prepare(expected_commit)
    receipt = _load_receipt("preflight")
    payload = _expect_keys(
        receipt["payload"],
        {
            "expected_git_commit",
            "prepare_receipt_sha256",
            "preflight",
            "roots",
            "attempt_timeout_seconds",
            "minimum_free_bytes",
            "sync_destination_identity",
            "shared_lease",
        },
        what="preflight handoff payload",
    )
    commit = _commit(payload["expected_git_commit"])
    if expected_commit is not None and commit != _commit(expected_commit):
        raise ValueError("preflight commit differs from the requested commit")
    if payload["prepare_receipt_sha256"] != prepare_receipt["_file_sha256"]:
        raise ValueError("preflight handoff does not bind the preparation receipt")
    local = PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE
    durable = SYNC_ROOT / Launch.PREFLIGHT_FILE
    _validate_pin(payload["preflight"], local, durable, what="E2A preflight")
    expected_roots = {
        "preflight": str(PREFLIGHT_ROOT.resolve()),
        "output": str(OUTPUT_ROOT.resolve()),
        "staging": str(STAGING_ROOT.resolve()),
        "sync": str(SYNC_ROOT.resolve()),
    }
    if (
        payload["roots"] != expected_roots
        or payload["attempt_timeout_seconds"] != ATTEMPT_TIMEOUT_SECONDS
        or payload["minimum_free_bytes"] != MINIMUM_FREE_BYTES
        or payload["sync_destination_identity"] != SYNC_DESTINATION_IDENTITY
        or payload["shared_lease"]
        != {
            "root": str(Plan.COMMON_LEASE_ROOT.resolve()),
            "name": Plan.COMMON_LEASE_NAME,
        }
    ):
        raise ValueError("preflight handoff changed the fixed attempt policy")
    Launch.validate_exp2a_repair_preflight(
        local,
        output_root=OUTPUT_ROOT,
        sync_root=SYNC_ROOT,
        expected_git_commit=commit,
    )
    return receipt


def preflight(*, expected_git_commit: str) -> dict[str, Any]:
    """Run the exact fixed-path 261-fit preflight and publish its handoff."""

    _validate_fixed_layout()
    prepared = _load_prepare(expected_git_commit)
    commit = _commit(expected_git_commit)
    for root in (PREFLIGHT_ROOT, OUTPUT_ROOT, STAGING_ROOT, SYNC_ROOT):
        _ensure_directory(root)
    plan_path = PREPARATION_ORIGINAL_ROOT / Plan.PLAN_FILE
    ledger_path = PREPARATION_ORIGINAL_ROOT / Sources.SOURCE_LEDGER_FILE
    Launch.run_exp2a_repair_preflight(
        plan_path=plan_path,
        source_ledger_path=ledger_path,
        expected_git_commit=commit,
        preflight_dir=PREFLIGHT_ROOT,
        output_root=OUTPUT_ROOT,
        staging_root=STAGING_ROOT,
        sync_root=SYNC_ROOT,
        attempt_timeout_seconds=ATTEMPT_TIMEOUT_SECONDS,
        minimum_free_bytes=MINIMUM_FREE_BYTES,
        sync_destination_identity=SYNC_DESTINATION_IDENTITY,
    )
    local = PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE
    durable = SYNC_ROOT / Launch.PREFLIGHT_FILE
    Launch.validate_exp2a_repair_preflight(
        local,
        output_root=OUTPUT_ROOT,
        sync_root=SYNC_ROOT,
        expected_git_commit=commit,
    )
    receipt = _publish_receipt(
        "preflight",
        status="ready",
        purpose="bind_fixed_cpu_preflight_before_any_e2a_repair_fit",
        payload={
            "expected_git_commit": commit,
            "prepare_receipt_sha256": prepared["_file_sha256"],
            "preflight": _pin_row(local, durable, what="E2A preflight"),
            "roots": {
                "preflight": str(PREFLIGHT_ROOT.resolve()),
                "output": str(OUTPUT_ROOT.resolve()),
                "staging": str(STAGING_ROOT.resolve()),
                "sync": str(SYNC_ROOT.resolve()),
            },
            "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
            "minimum_free_bytes": MINIMUM_FREE_BYTES,
            "sync_destination_identity": SYNC_DESTINATION_IDENTITY,
            "shared_lease": {
                "root": str(Plan.COMMON_LEASE_ROOT.resolve()),
                "name": Plan.COMMON_LEASE_NAME,
            },
        },
    )
    return _operational("preflight", receipt, status="ready")


def _control_payload(commit: str, preflight_receipt: Mapping[str, Any]) -> dict[str, Any]:
    local_preflight = PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE
    durable_preflight = SYNC_ROOT / Launch.PREFLIGHT_FILE
    prepared = _load_prepare(commit)
    return {
        "expected_git_commit": commit,
        "preflight_receipt_sha256": preflight_receipt["_file_sha256"],
        "preflight": _pin_row(
            local_preflight, durable_preflight, what="E2A preflight"
        ),
        "plan_digest": prepared["payload"]["plan_digest"],
        "source_ledger": prepared["payload"]["source_ledger"],
        "shared_lease": {
            "root": str(Plan.COMMON_LEASE_ROOT.resolve()),
            "name": Plan.COMMON_LEASE_NAME,
        },
        "checkpoint_identity": {
            "local_directory": str(
                (OUTPUT_ROOT / Plan.START_DIRECTORY).resolve()
            ),
            "copy_directory": str((SYNC_ROOT / Plan.START_DIRECTORY).resolve()),
            "filename_rule": "single_32hex_lease_token_json",
        },
        "event_identity": {
            "local_directory": str((OUTPUT_ROOT / Launch.EVENT_DIRECTORY).resolve()),
            "copy_directory": str((SYNC_ROOT / Launch.EVENT_DIRECTORY).resolve()),
            "filename_rule": "contiguous_six_digit_json",
        },
        "launch_report_identity": {
            "local_directory": str((OUTPUT_ROOT / Launch.REPORT_DIRECTORY).resolve()),
            "copy_directory": str((SYNC_ROOT / Launch.REPORT_DIRECTORY).resolve()),
            "filename_rule": "matching_lease_token_json",
        },
        "roots": {
            "output": str(OUTPUT_ROOT.resolve()),
            "staging": str(STAGING_ROOT.resolve()),
            "sync": str(SYNC_ROOT.resolve()),
        },
        "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
        "expected_physical_fits": 261,
        "expected_member_models": 441,
        "automatic_retry_allowed": False,
        "scientific_files_permitted_for_monitor": False,
    }


def _load_control(
    expected_commit: str | None = None, *, monitor_only: bool = False
) -> dict[str, Any]:
    receipt = _load_receipt("launch-control")
    if receipt["status"] != "armed_before_blocking_launch":
        raise ValueError("launch control was not published in the armed state")
    payload = receipt["payload"]
    commit = _commit(payload.get("expected_git_commit"))
    if expected_commit is not None and commit != _commit(expected_commit):
        raise ValueError("launch control commit differs from the requested commit")
    if monitor_only:
        payload = _expect_keys(
            payload,
            {
                "expected_git_commit",
                "preflight_receipt_sha256",
                "preflight",
                "plan_digest",
                "source_ledger",
                "shared_lease",
                "checkpoint_identity",
                "event_identity",
                "launch_report_identity",
                "roots",
                "attempt_timeout_seconds",
                "expected_physical_fits",
                "expected_member_models",
                "automatic_retry_allowed",
                "scientific_files_permitted_for_monitor",
            },
            what="outcome-blind launch control payload",
        )
        preflight_pin = _expect_keys(
            payload["preflight"],
            {"path", "copy_path", "sha256", "independent_copy"},
            what="outcome-blind preflight pin",
        )
        source_pin = _expect_keys(
            payload["source_ledger"],
            {"path", "copy_path", "sha256", "independent_copy"},
            what="outcome-blind source-ledger pin",
        )
        _sha(payload["preflight_receipt_sha256"], what="preflight receipt SHA256")
        _sha(preflight_pin["sha256"], what="preflight SHA256")
        _sha(source_pin["sha256"], what="source-ledger SHA256")
        expected_scalars = {
            "shared_lease": {
                "root": str(Plan.COMMON_LEASE_ROOT.resolve()),
                "name": Plan.COMMON_LEASE_NAME,
            },
            "checkpoint_identity": {
                "local_directory": str((OUTPUT_ROOT / Plan.START_DIRECTORY).resolve()),
                "copy_directory": str((SYNC_ROOT / Plan.START_DIRECTORY).resolve()),
                "filename_rule": "single_32hex_lease_token_json",
            },
            "event_identity": {
                "local_directory": str((OUTPUT_ROOT / Launch.EVENT_DIRECTORY).resolve()),
                "copy_directory": str((SYNC_ROOT / Launch.EVENT_DIRECTORY).resolve()),
                "filename_rule": "contiguous_six_digit_json",
            },
            "launch_report_identity": {
                "local_directory": str((OUTPUT_ROOT / Launch.REPORT_DIRECTORY).resolve()),
                "copy_directory": str((SYNC_ROOT / Launch.REPORT_DIRECTORY).resolve()),
                "filename_rule": "matching_lease_token_json",
            },
            "roots": {
                "output": str(OUTPUT_ROOT.resolve()),
                "staging": str(STAGING_ROOT.resolve()),
                "sync": str(SYNC_ROOT.resolve()),
            },
        }
        if any(payload[name] != value for name, value in expected_scalars.items()):
            raise ValueError("launch control changed a fixed monitor identity")
        if (
            preflight_pin
            != {
                "path": str((PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE).resolve()),
                "copy_path": str((SYNC_ROOT / Launch.PREFLIGHT_FILE).resolve()),
                "sha256": preflight_pin["sha256"],
                "independent_copy": True,
            }
            or source_pin["path"]
            != str((PREPARATION_ORIGINAL_ROOT / Sources.SOURCE_LEDGER_FILE).resolve())
            or source_pin["copy_path"]
            != str((PREPARATION_COPY_ROOT / Sources.SOURCE_LEDGER_FILE).resolve())
            or source_pin["independent_copy"] is not True
            or type(payload["plan_digest"]) is not str
            or payload["attempt_timeout_seconds"] != ATTEMPT_TIMEOUT_SECONDS
            or payload["expected_physical_fits"] != 261
            or payload["expected_member_models"] != 441
            or payload["automatic_retry_allowed"] is not False
            or payload["scientific_files_permitted_for_monitor"] is not False
        ):
            raise ValueError("launch control changed the outcome-blind monitor policy")
    else:
        preflight_receipt = _load_preflight(commit)
        expected = _control_payload(commit, preflight_receipt)
        if payload != expected:
            raise ValueError("launch control differs from the deterministic attempt identity")
    return receipt


def _validated_lower_counts(value: object) -> dict[str, int]:
    counts = _expect_keys(
        value,
        {"executed", "resumed", "synced", "total"},
        what="lower E2A launch counts",
    )
    result = {
        name: _nonnegative_int(counts[name], what=f"lower E2A {name} count")
        for name in ("executed", "resumed", "synced", "total")
    }
    if (
        result["total"] != 261
        or result["synced"] > result["total"]
        or result["executed"] + result["resumed"] != result["synced"]
    ):
        raise ValueError("lower E2A launch counts do not exactly reconcile to 261")
    return result


def _failure_digest(value: object, *, what: str) -> str | None:
    if value is None:
        return None
    row = _expect_keys(value, {"type", "message"}, what=what)
    if any(type(row[name]) is not str for name in ("type", "message")):
        raise ValueError(f"{what} fields must be exact strings")
    return sha256_bytes(_canonical(row))


def _lower_launch_report_material(
    control: Mapping[str, Any], *, require_complete: bool = False
) -> dict[str, Any] | None:
    """Validate at most one exact independently copied terminal lower report."""

    local_dir = OUTPUT_ROOT / Launch.REPORT_DIRECTORY
    copy_dir = SYNC_ROOT / Launch.REPORT_DIRECTORY
    local = _directory_json_inventory(local_dir, _TOKEN_FILE)
    copied = _directory_json_inventory(copy_dir, _TOKEN_FILE)
    if set(local) != set(copied):
        raise ValueError("lower launch-report original/copy inventories differ")
    if len(local) > 1:
        raise ValueError("fixed attempt-001 has multiple lower launch reports")
    if not local:
        return None
    name = next(iter(local))
    token_match = _TOKEN_FILE.fullmatch(name)
    if token_match is None:  # guarded by the inventory helper; defense in depth
        raise ValueError("lower launch report has a noncanonical token filename")
    token = token_match.group(1)
    file_sha = _independent_equal(
        local[name], copied[name], what="lower E2A terminal launch report"
    )
    document = _expect_keys(
        read_json(local[name]),
        {
            "exp2a_repair_launch_schema_version",
            "status",
            "counts",
            "failure",
            "historical_retrained",
            "preflight",
            "checkpoint",
            "released_lease",
            "lease_release_failure",
        },
        what="lower E2A terminal launch report",
    )
    if read_json(copied[name]) != document:
        raise ValueError("lower launch-report copy differs after read-back")
    status = document["status"]
    if (
        type(document["exp2a_repair_launch_schema_version"]) is not int
        or document["exp2a_repair_launch_schema_version"] != 1
        or status not in {"complete", "incomplete", "interrupted"}
        or document["historical_retrained"] is not False
    ):
        raise ValueError("lower E2A terminal report schema/status drifted")
    counts = _validated_lower_counts(document["counts"])
    preflight = _expect_keys(
        document["preflight"], {"path", "sha256"}, what="lower report preflight pin"
    )
    control_preflight = control["payload"]["preflight"]
    if preflight != {
        "path": control_preflight["path"],
        "sha256": control_preflight["sha256"],
    }:
        raise ValueError("lower launch report does not bind the armed preflight")

    checkpoint, checkpoint_sha = _checkpoint_material(control)
    checkpoint_row = document["checkpoint"]
    if checkpoint_row is None:
        if checkpoint is not None:
            raise ValueError("lower launch report omits its preserved checkpoint")
    else:
        checkpoint_row = _expect_keys(
            checkpoint_row, {"path", "sha256"}, what="lower report checkpoint pin"
        )
        expected_path = OUTPUT_ROOT / Plan.START_DIRECTORY / f"{token}.json"
        if (
            checkpoint is None
            or Path(checkpoint_row["path"]).resolve() != expected_path.resolve()
            or checkpoint_row["sha256"] != checkpoint_sha
            or checkpoint["lease"]["token"] != token
        ):
            raise ValueError("lower launch report/checkpoint/token binding differs")
        _sha(checkpoint_row["sha256"], what="lower report checkpoint SHA256")

    failure_sha = _failure_digest(document["failure"], what="lower launch failure")
    release_failure = document["lease_release_failure"]
    release_failure_sha: str | None = None
    if release_failure is not None:
        release_failure = _expect_keys(
            release_failure,
            {
                "type",
                "message",
                "token",
                "active_path",
                "automatic_recovery_allowed",
            },
            what="lower launch lease-release failure",
        )
        if (
            type(release_failure["type"]) is not str
            or type(release_failure["message"]) is not str
            or release_failure["token"] != token
            or Path(release_failure["active_path"]).resolve()
            != (
                Plan.COMMON_LEASE_ROOT
                / "leases"
                / f"{Plan.COMMON_LEASE_NAME}.lease.json"
            ).resolve()
            or release_failure["automatic_recovery_allowed"] is not False
        ):
            raise ValueError("lower launch lease-release failure is not exact")
        release_failure_sha = sha256_bytes(_canonical(release_failure))

    released = document["released_lease"]
    if released is not None:
        released = _expect_keys(
            released, {"token", "history_path"}, what="lower released lease"
        )
        expected_history = (
            Plan.COMMON_LEASE_ROOT
            / "leases"
            / "history"
            / f"{Plan.COMMON_LEASE_NAME}.{token}.released.json"
        )
        if (
            released["token"] != token
            or Path(released["history_path"]).resolve() != expected_history.resolve()
        ):
            raise ValueError("lower launch report names a different released lease")
        _plain_file(expected_history, what="released shared-production lease history")
        historical = Launch._historical_lease_record(token)
        if historical["token"] != token or historical["name"] != Plan.COMMON_LEASE_NAME:
            raise ValueError("released lease history does not validate the lower report")

    if (released is None) == (release_failure is None):
        raise ValueError("lower launch report must prove exactly one lease-release outcome")
    if status == "complete":
        if (
            checkpoint is None
            or counts
            != {"executed": 261, "resumed": 0, "synced": 261, "total": 261}
            or failure_sha is not None
            or released is None
            or release_failure is not None
        ):
            raise ValueError("complete lower launch report is not exact 261-fit released evidence")
    elif failure_sha is None and release_failure_sha is None:
        raise ValueError("stopped lower launch report lacks preserved failure evidence")
    if require_complete and status != "complete":
        raise ValueError("preserved lower launch is not complete; fitting will not be rerun")
    diagnostics_sha = (
        None
        if failure_sha is None and release_failure_sha is None
        else sha256_bytes(
            _canonical(
                {
                    "failure_sha256": failure_sha,
                    "lease_release_failure_sha256": release_failure_sha,
                }
            )
        )
    )
    return {
        "token": token,
        "document": document,
        "local_path": local[name],
        "copy_path": copied[name],
        "file_sha256": file_sha,
        "counts": counts,
        "status": status,
        "failure_sha256": diagnostics_sha,
    }


def _publish_launch_receipt(
    *, commit: str, control: Mapping[str, Any], material: Mapping[str, Any]
) -> dict[str, Any]:
    token = material["token"]
    counts = material["counts"]
    checkpoint_path = OUTPUT_ROOT / Plan.START_DIRECTORY / f"{token}.json"
    checkpoint_copy = SYNC_ROOT / Plan.START_DIRECTORY / f"{token}.json"
    report_path = OUTPUT_ROOT / Launch.REPORT_DIRECTORY / f"{token}.json"
    report_copy = SYNC_ROOT / Launch.REPORT_DIRECTORY / f"{token}.json"
    member_models = sum(
        job.config.train.ensemble_size for job in Plan.new_exp2a_jobs()
    )
    if member_models != 441:
        raise ValueError("registered E2A new-job model accounting drifted from 441")
    return _publish_receipt(
        "launch",
        status="complete",
        purpose="bind_released_261_fit_e2a_repair_launch",
        payload={
            "expected_git_commit": commit,
            "control_receipt_sha256": control["_file_sha256"],
            "lease_token": token,
            "checkpoint": _pin_row(
                checkpoint_path, checkpoint_copy, what="E2A start checkpoint"
            ),
            "launch_report": _pin_row(
                report_path, report_copy, what="E2A launch report"
            ),
            "status": "complete",
            "lower_counts": dict(counts),
            "released_lease": dict(material["document"]["released_lease"]),
            "counts": {
                "physical_fits": counts["total"],
                "member_models": member_models,
                "historical_retrained": 0,
            },
        },
    )


def launch(*, expected_git_commit: str) -> dict[str, Any]:
    """Recover one completion or enter the lower launch exactly once."""

    _validate_fixed_layout()
    if _receipt_present("launch"):
        existing = _load_launch(expected_git_commit)
        return _operational("launch", existing, status="complete")
    preflight_receipt = _load_preflight(expected_git_commit)
    commit = _commit(expected_git_commit)
    control = _publish_receipt(
        "launch-control",
        status="armed_before_blocking_launch",
        purpose="outcome_blind_control_identity_published_before_blocking_launch",
        payload=_control_payload(commit, preflight_receipt),
    )
    terminal = _lower_launch_report_material(control)
    if terminal is not None:
        if terminal["status"] != "complete":
            raise ValueError(
                "preserved lower launch is incomplete/interrupted; fitting will not be rerun"
            )
        receipt = _publish_launch_receipt(
            commit=commit, control=control, material=terminal
        )
        return _operational("launch", receipt, status="complete")
    checkpoint, _ = _checkpoint_material(control)
    if checkpoint is not None:
        raise ValueError(
            "a preserved checkpoint exists without one complete lower report; "
            "fitting will not be rerun"
        )
    # The immutable control pair exists before this call.  Tests pin this
    # ordering; the lower layer retains sole ownership of the lease and fits.
    result = Launch.launch_exp2a_repairs(
        preflight_report=PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE,
        output_root=OUTPUT_ROOT,
        sync_root=SYNC_ROOT,
        expected_git_commit=commit,
    )
    terminal = _lower_launch_report_material(control, require_complete=True)
    if terminal is None:
        raise ValueError("lower E2A launch returned without terminal report evidence")
    expected_result = {
        **terminal["document"],
        "report_path": str(terminal["local_path"]),
    }
    if type(result) is not dict or result != expected_result:
        raise ValueError("lower E2A return value differs from its immutable report")
    receipt = _publish_launch_receipt(
        commit=commit, control=control, material=terminal
    )
    return _operational("launch", receipt, status="complete")


def _load_launch(expected_commit: str | None = None) -> dict[str, Any]:
    receipt = _load_receipt("launch")
    payload = _expect_keys(
        receipt["payload"],
        {
            "expected_git_commit",
            "control_receipt_sha256",
            "lease_token",
            "checkpoint",
            "launch_report",
            "status",
            "lower_counts",
            "released_lease",
            "counts",
        },
        what="launch handoff payload",
    )
    commit = _commit(payload["expected_git_commit"])
    if expected_commit is not None and commit != _commit(expected_commit):
        raise ValueError("launch handoff commit differs from requested commit")
    control = _load_control(commit)
    if payload["control_receipt_sha256"] != control["_file_sha256"]:
        raise ValueError("launch handoff does not bind its pre-launch control")
    terminal = _lower_launch_report_material(control, require_complete=True)
    if terminal is None:
        raise ValueError("launch handoff lacks its lower terminal report")
    token = payload["lease_token"]
    if (
        type(token) is not str
        or not re.fullmatch(r"[0-9a-f]{32}", token)
        or token != terminal["token"]
    ):
        raise ValueError("launch handoff lease token is not canonical")
    checkpoint = OUTPUT_ROOT / Plan.START_DIRECTORY / f"{token}.json"
    checkpoint_copy = SYNC_ROOT / Plan.START_DIRECTORY / f"{token}.json"
    _validate_pin(payload["checkpoint"], checkpoint, checkpoint_copy, what="checkpoint")
    report = OUTPUT_ROOT / Launch.REPORT_DIRECTORY / f"{token}.json"
    report_copy = SYNC_ROOT / Launch.REPORT_DIRECTORY / f"{token}.json"
    _validate_pin(payload["launch_report"], report, report_copy, what="launch report")
    if (
        payload["status"] != "complete"
        or payload["lower_counts"] != terminal["counts"]
        or payload["released_lease"] != terminal["document"]["released_lease"]
        or payload["counts"]
        != {
            "physical_fits": terminal["counts"]["total"],
            "member_models": 441,
            "historical_retrained": 0,
        }
    ):
        raise ValueError("launch handoff is not the exact complete 261/441 batch")
    return receipt


def _directory_json_inventory(path: Path, pattern: re.Pattern[str]) -> dict[str, Path]:
    """Read-only inventory; unlike the launch loader, never creates or repairs."""

    if not os.path.lexists(path):
        return {}
    directory = Plan._project_path(path, directory=True)
    result: dict[str, Path] = {}
    for child in directory.iterdir():
        if child.name.startswith(".") and child.name.endswith(".tmp"):
            continue
        if pattern.fullmatch(child.name) is None:
            raise ValueError(f"unknown file in outcome-blind monitor source: {child.name}")
        result[child.name] = _plain_file(child, what="monitor source evidence")
    return result


def _checkpoint_material(control: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    identity = control["payload"]["checkpoint_identity"]
    local_dir = Path(identity["local_directory"])
    copy_dir = Path(identity["copy_directory"])
    local = _directory_json_inventory(local_dir, _TOKEN_FILE)
    copied = _directory_json_inventory(copy_dir, _TOKEN_FILE)
    if set(local) != set(copied):
        raise ValueError("checkpoint original/copy inventories differ")
    if len(local) > 1:
        raise ValueError("automatic retry is prohibited; multiple checkpoints found")
    if not local:
        return None, None
    name = next(iter(local))
    digest = _independent_equal(local[name], copied[name], what="monitor checkpoint")
    document = _expect_keys(
        read_json(local[name]),
        {
            "exp2a_repair_start_schema_version",
            "purpose",
            "plan_digest",
            "preflight",
            "source_ledger",
            "environment",
            "roots",
            "attempt_timeout_seconds",
            "lease",
            "fixed_worker",
            "supervisor_required",
            "automatic_retry_allowed",
            "execution_context_digest",
            "checkpoint_digest",
        },
        what="outcome-blind checkpoint",
    )
    token = _TOKEN_FILE.fullmatch(name).group(1)  # type: ignore[union-attr]
    payload = control["payload"]
    _expect_keys(
        document["preflight"],
        {"path", "sha256", "binding_sha256"},
        what="outcome-blind checkpoint preflight pin",
    )
    source_ledger = _expect_keys(
        document["source_ledger"],
        {"path", "sha256", "ledger_digest"},
        what="outcome-blind checkpoint source-ledger pin",
    )
    roots = _expect_keys(
        document["roots"],
        {"output", "staging", "sync"},
        what="outcome-blind checkpoint roots",
    )
    lease = _expect_keys(
        document["lease"],
        {"path", "sha256", "name", "token", "started_at"},
        what="outcome-blind checkpoint lease",
    )
    if type(document["environment"]) is not dict:
        raise ValueError("outcome-blind checkpoint environment must be an exact object")
    environment = document["environment"]
    if (
        document["exp2a_repair_start_schema_version"] != Launch.START_SCHEMA_VERSION
        or document["purpose"] != "source_verified_week8_exp2a_repair_start"
        or roots != payload["roots"]
        or document["attempt_timeout_seconds"] != ATTEMPT_TIMEOUT_SECONDS
        or document["automatic_retry_allowed"] is not False
        or lease.get("token") != token
        or lease.get("name") != Plan.COMMON_LEASE_NAME
        or environment.get("git_commit") != payload["expected_git_commit"]
        or _route_payload(environment)
        != {"device": "cpu", "num_threads": 4, "num_interop_threads": 4, "gpu_used": False}
    ):
        raise ValueError("checkpoint differs from the fixed control identity")
    if (
        document["plan_digest"] != payload["plan_digest"]
        or source_ledger["path"] != payload["source_ledger"]["path"]
        or source_ledger["sha256"]
        != payload["source_ledger"]["sha256"]
    ):
        raise ValueError("checkpoint does not bind the immutable preparation")
    expected = Plan._seal(
        {key: value for key, value in document.items() if key != "checkpoint_digest"},
        "checkpoint_digest",
    )
    if document != expected:
        raise ValueError("checkpoint content digest is invalid")
    if document["execution_context_digest"] != Launch._execution_context(document)[
        "execution_context_digest"
    ]:
        raise ValueError("checkpoint execution-context digest is invalid")
    if digest != sha256_file(local[name]) or read_json(copied[name]) != document:
        raise ValueError("checkpoint changed during outcome-blind read-back")
    return document, digest


def _events_material(
    control: Mapping[str, Any], checkpoint: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    identity = control["payload"]["event_identity"]
    local_dir = Path(identity["local_directory"])
    copy_dir = Path(identity["copy_directory"])
    local = _directory_json_inventory(local_dir, _EVENT_FILE)
    copied = _directory_json_inventory(copy_dir, _EVENT_FILE)
    if set(local) != set(copied):
        raise ValueError("event original/copy inventories differ")
    names = sorted(local)
    if names != [f"{index:06d}.json" for index in range(len(names))]:
        raise ValueError("outcome-blind event stream contains a gap")
    if checkpoint is None and names:
        raise ValueError("events cannot precede their start checkpoint")
    events: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    previous: str | None = None
    started: set[str] = set()
    synced: set[str] = set()
    terminal = False
    all_jobs = {job.job_id for job in Plan.new_exp2a_jobs()}
    for index, name in enumerate(names):
        if terminal:
            raise ValueError("events exist after a terminal failure/completion")
        _independent_equal(local[name], copied[name], what=f"monitor event {name}")
        row = read_json(local[name])
        Launch._validate_event(
            row,
            index=index,
            previous=previous,
            context_digest=checkpoint["execution_context_digest"],  # type: ignore[index]
        )
        if read_json(copied[name]) != row:
            raise ValueError("event copy differs after validation")
        kind = row["kind"]
        job_id = row["job_id"]
        if kind == "attempt_started":
            if job_id in started or job_id not in all_jobs:
                raise ValueError("event stream duplicates or invents a launch job")
            if row["data"]["checkpoint_digest"] != checkpoint["checkpoint_digest"]:  # type: ignore[index]
                raise ValueError("attempt event binds a different checkpoint")
            started.add(job_id)
        elif kind == "job_synced":
            if job_id not in started or job_id in synced:
                raise ValueError("synced event lacks one unique attempt start")
            synced.add(job_id)
        elif kind in {"attempt_failed", "sync_pending"}:
            if job_id not in started or job_id in synced:
                raise ValueError("failure event lacks one unresolved attempt")
            failures.append(
                {
                    "sequence": index,
                    "kind": kind,
                    "job_id": job_id,
                    "failure_sha256": sha256_bytes(_canonical(row["data"])),
                }
            )
            terminal = True
        else:
            if synced != all_jobs or len(synced) != 261:
                raise ValueError("completion event lacks all exact synced jobs")
            terminal = True
        events.append(row)
        previous = row["event_digest"]
    return events, failures


def _monitor_material() -> dict[str, Any]:
    """Recompute one operational view without opening any scientific file."""

    _validate_fixed_layout()
    control = _load_control(monitor_only=True)
    terminal = _lower_launch_report_material(control)
    checkpoint, checkpoint_sha = _checkpoint_material(control)
    events, failures = _events_material(control, checkpoint)
    counts = {
        "expected": 261,
        "started": sum(row["kind"] == "attempt_started" for row in events),
        "synced": sum(row["kind"] == "job_synced" for row in events),
        "failed": sum(row["kind"] == "attempt_failed" for row in events),
        "sync_pending": sum(row["kind"] == "sync_pending" for row in events),
    }
    counts["remaining"] = counts["expected"] - counts["synced"]
    complete = bool(events and events[-1]["kind"] == "complete")
    terminal_summary = None
    if terminal is not None:
        terminal_summary = {
            "token": terminal["token"],
            "status": terminal["status"],
            "sha256": terminal["file_sha256"],
            "counts": terminal["counts"],
            "failure_sha256": terminal["failure_sha256"],
            "released_lease": terminal["document"]["released_lease"] is not None,
        }
        if terminal["status"] == "complete":
            if not complete or counts["synced"] != 261:
                raise ValueError(
                    "complete lower report lacks the exact complete event stream"
                )
            status = "complete"
        else:
            if terminal["failure_sha256"] is None:
                raise ValueError("stopped lower report lacks hashed failure evidence")
            failures.append(
                {
                    "sequence": len(events),
                    "kind": f"lower_launch_{terminal['status']}",
                    "job_id": None,
                    "failure_sha256": terminal["failure_sha256"],
                }
            )
            status = "stopped_with_preserved_failure"
    else:
        status = (
            "awaiting_checkpoint"
            if checkpoint is None
            else "complete"
            if complete
            else "stopped_with_preserved_failure"
            if failures
            else "running"
        )
    payload = {
        "week8_exp2a_monitor_schema_version": MONITOR_SCHEMA_VERSION,
        "purpose": "outcome_blind_read_only_exp2a_operational_snapshot",
        "status": status,
        "control": {
            "original_path": control["receipt_paths"]["original"],
            "copy_path": control["receipt_paths"]["copy"],
            "sha256": control["_file_sha256"],
            "receipt_digest": control["receipt_digest"],
        },
        "checkpoint": (
            None
            if checkpoint is None
            else {
                "token": checkpoint["lease"]["token"],
                "sha256": checkpoint_sha,
                "checkpoint_digest": checkpoint["checkpoint_digest"],
            }
        ),
        "event_stream": {
            "event_count": len(events),
            "last_event_digest": None if not events else events[-1]["event_digest"],
            "stream_sha256": sha256_bytes(
                _canonical([row["event_digest"] for row in events])
            ),
        },
        "terminal_report": terminal_summary,
        "counts": counts,
        "preserved_failures": failures,
        "failure_text_included": False,
        "scientific_files_opened": False,
        "automatic_repair_performed": False,
    }
    return Plan._seal(payload, "snapshot_digest")


def _monitor_paths(snapshot_digest: str) -> tuple[Path, Path]:
    digest = _sha(snapshot_digest, what="monitor snapshot digest")
    name = f"snapshot-{digest}.json"
    return MONITOR_ROOT / name, MONITOR_COPY_ROOT / name


def monitor() -> dict[str, Any]:
    """Publish a read-only, independently copied operational snapshot."""

    document = _monitor_material()
    local_root = _ensure_directory(MONITOR_ROOT)
    copy_root = _ensure_directory(MONITOR_COPY_ROOT)
    local, copied = _monitor_paths(document["snapshot_digest"])
    if local.parent != local_root or copied.parent != copy_root:
        raise ValueError("monitor snapshot escaped its dedicated fixed roots")
    atomic_write_json(local, document)
    atomic_write_json(copied, document)
    digest = _independent_equal(local, copied, what="E2A monitor snapshot")
    fresh = validate_monitor_snapshot(local)
    if fresh != document:
        raise ValueError("persisted monitor snapshot differs from fresh evidence")
    return {
        "command": "monitor",
        "status": document["status"],
        "snapshot_path": str(local),
        "snapshot_copy_path": str(copied),
        "snapshot_file_sha256": digest,
        "counts": document["counts"],
    }


def validate_monitor_snapshot(path: str | Path) -> dict[str, Any]:
    """Revalidate a snapshot against current control/checkpoint/event twins."""

    target = _plain_file(Path(path), what="E2A monitor snapshot")
    document = _expect_keys(
        read_json(target),
        {
            "week8_exp2a_monitor_schema_version",
            "purpose",
            "status",
            "control",
            "checkpoint",
            "event_stream",
            "terminal_report",
            "counts",
            "preserved_failures",
            "failure_text_included",
            "scientific_files_opened",
            "automatic_repair_performed",
            "snapshot_digest",
        },
        what="E2A monitor snapshot",
    )
    _sha(document["snapshot_digest"], what="monitor snapshot digest")
    expected_path, copy_path = _monitor_paths(document["snapshot_digest"])
    if target.resolve() not in {expected_path.resolve(), copy_path.resolve()}:
        raise ValueError("monitor snapshot is outside its dedicated fixed roots")
    expected = Plan._seal(
        {key: value for key, value in document.items() if key != "snapshot_digest"},
        "snapshot_digest",
    )
    if document != expected:
        raise ValueError("monitor snapshot digest is invalid")
    counterpart = copy_path if target.resolve() == expected_path.resolve() else expected_path
    _independent_equal(expected_path, copy_path, what="E2A monitor snapshot")
    if read_json(counterpart) != document:
        raise ValueError("monitor snapshot copy differs")
    fresh = _monitor_material()
    if fresh != document:
        raise ValueError("monitor snapshot is stale or its source evidence changed")
    return document


def _finalization_inputs(launch_receipt: Mapping[str, Any], commit: str):
    prepared = _load_prepare(launch_receipt["payload"]["expected_git_commit"])
    plan_row = prepared["payload"]["plan"]
    ledger_row = prepared["payload"]["source_ledger"]
    checkpoint = launch_receipt["payload"]["checkpoint"]
    return Finalize.Exp2AFinalizationInputs(
        plan_path=plan_row["path"],
        plan_sha256=plan_row["sha256"],
        source_ledger_path=ledger_row["path"],
        source_ledger_sha256=ledger_row["sha256"],
        checkpoint_path=checkpoint["path"],
        checkpoint_sha256=checkpoint["sha256"],
        expected_execution_commit=launch_receipt["payload"]["expected_git_commit"],
        expected_finalizer_commit=commit,
    )


def _validated_finalization_accounting(value: object) -> dict[str, int]:
    document = _expect_keys(
        value,
        {
            "week8_exp2a_label_finalization_schema_version",
            "purpose",
            "status",
            "inputs",
            "finalizer",
            "plan_digest",
            "ledger_digest",
            "execution_context_digest",
            "source_inventory_digest",
            "roots",
            "counts",
            "pending_new_fit_ids",
            "non_label_existing_fit_ids",
            "units",
            "manifest_digest",
        },
        what="E2A finalization document",
    )
    counts = _expect_keys(
        document["counts"],
        {
            "registered_units",
            "twenty_seed_units",
            "three_seed_units",
            "labelled_units",
            "pending_units",
            "blocked_units",
            "observed",
            "historical_fits_preserved",
            "historical_fits_required",
            "non_label_historical_fits",
            "new_fit_obligations",
            "label_required_fits",
            "verified_source_pairs",
            "pending_new_fits",
            "exported_fit_trees_per_root",
            "executed_fits",
            "retrained_fits",
        },
        what="E2A finalization counts",
    )
    observed = _expect_keys(
        counts["observed"],
        {"observed_0", "observed_1", "ambiguous", "undiagnosed"},
        what="E2A observed-label counts",
    )
    for name, number in observed.items():
        _nonnegative_int(number, what=f"E2A {name} count")
    fixed = {
        "registered_units": 20,
        "twenty_seed_units": 4,
        "three_seed_units": 16,
        "labelled_units": 20,
        "pending_units": 0,
        "blocked_units": 0,
        "historical_fits_preserved": 155,
        "historical_fits_required": 123,
        "non_label_historical_fits": 32,
        "new_fit_obligations": 261,
        "label_required_fits": 384,
        "verified_source_pairs": 384,
        "pending_new_fits": 0,
        "exported_fit_trees_per_root": 384,
        "executed_fits": 0,
        "retrained_fits": 0,
    }
    for name, expected in fixed.items():
        if _nonnegative_int(counts[name], what=f"E2A {name}") != expected:
            raise ValueError(f"E2A finalization {name} differs from {expected}")
    if (
        sum(observed.values()) != 20
        or type(document["week8_exp2a_label_finalization_schema_version"]) is not int
        or document["week8_exp2a_label_finalization_schema_version"]
        != Finalize.FINALIZATION_SCHEMA_VERSION
        or document["status"] != "complete"
        or document["purpose"] != "exact_week8_experiment2a_label_finalization"
        or document["pending_new_fit_ids"] != []
        or type(document["non_label_existing_fit_ids"]) is not list
        or len(document["non_label_existing_fit_ids"]) != 32
        or any(
            type(item) is not str for item in document["non_label_existing_fit_ids"]
        )
        or len(set(document["non_label_existing_fit_ids"])) != 32
        or type(document["units"]) is not list
        or len(document["units"]) != 20
    ):
        raise ValueError("E2A finalization does not prove exact complete 20/416/384 accounting")
    _sha(document["manifest_digest"], what="E2A finalization manifest digest")
    expected_document = Plan._seal(
        {key: item for key, item in document.items() if key != "manifest_digest"},
        "manifest_digest",
    )
    if document != expected_document:
        raise ValueError("E2A finalization manifest digest is invalid")
    return {
        "registered_units": 20,
        "registered_physical_fits": 416,
        "historical_fits": 155,
        "new_fits": 261,
        "label_required_fits": 384,
        "exported_fit_trees_per_root": 384,
        "fits_executed_during_finalization": 0,
    }


_REPORTING_COUNTS = {
    "released_fits": 416,
    "historical_fits": 155,
    "new_fits": 261,
    "label_required_fits": 384,
    "historical_label_fits": 123,
    "new_label_fits": 261,
    "baseline_diagnostic_fits": 100,
    "exported_label_baselines": 68,
    "historical_baseline_only_fits": 32,
    "union_fits": 416,
    "labelled_units": 20,
    "twenty_seed_labels": 4,
    "three_seed_labels": 16,
}


def _validated_reporting_binding(
    value: object,
    *,
    expected_commit: str,
    expected_execution_commit: str,
    expected_manifest_sha256: str,
    report_path: Path,
    report_copy_path: Path,
    binding_path: Path,
) -> dict[str, int]:
    document = _expect_keys(
        value,
        {
            "week8_exp2a_reporting_adapter_schema_version",
            "purpose",
            "status",
            "binding_receipt_path",
            "fits_executed",
            "labels_created",
            "sign_consistency_applied",
            "h2_verdict",
            "reporting_environment",
            "upstream",
            "report",
            "counts",
            "receipt_digest",
        },
        what="E2A reporting binding",
    )
    counts = _expect_keys(
        document["counts"], set(_REPORTING_COUNTS), what="E2A reporting counts"
    )
    for name, expected in _REPORTING_COUNTS.items():
        if _nonnegative_int(counts[name], what=f"E2A reporting {name}") != expected:
            raise ValueError(
                "E2A reporting binding does not prove exact 416/384 accounting"
            )
    environment = document["reporting_environment"]
    if type(environment) is not dict or environment.get("git_commit") != expected_commit:
        raise ValueError("E2A reporting binding uses a different clean commit")
    upstream = _expect_keys(
        document["upstream"],
        {
            "plan",
            "source_ledger",
            "checkpoint",
            "expected_execution_commit",
            "expected_finalizer_commit",
            "expected_reporting_commit",
            "finalization",
        },
        what="E2A reporting upstream",
    )
    finalization = _expect_keys(
        upstream["finalization"],
        {
            "export_manifest_path",
            "durable_manifest_path",
            "sha256",
            "manifest_digest",
        },
        what="E2A reporting finalization pin",
    )
    report = _expect_keys(
        document["report"],
        {
            "path",
            "copy_path",
            "sha256",
            "payload_sha256",
            "source_inventory_sha256",
            "independent_copy",
        },
        what="E2A reporting report pin",
    )
    for name in ("plan", "source_ledger", "checkpoint"):
        pin = _expect_keys(
            upstream[name], {"path", "sha256"}, what=f"E2A reporting {name} pin"
        )
        if type(pin["path"]) is not str:
            raise ValueError(f"E2A reporting {name} path must be an exact string")
        _sha(pin["sha256"], what=f"E2A reporting {name} SHA256")
    if (
        type(document["week8_exp2a_reporting_adapter_schema_version"]) is not int
        or document["week8_exp2a_reporting_adapter_schema_version"]
        != Reporting.REPORTING_ADAPTER_SCHEMA_VERSION
        or document["purpose"]
        != "bind_rederived_week8_exp2a_sources_to_descriptive_report"
        or document["status"] != "complete"
        or document["binding_receipt_path"] != str(binding_path.resolve())
        or _nonnegative_int(document["fits_executed"], what="reporting fits executed") != 0
        or _nonnegative_int(document["labels_created"], what="reporting labels created") != 0
        or document["sign_consistency_applied"] is not False
        or document["h2_verdict"] is not None
        or upstream["expected_execution_commit"] != expected_execution_commit
        or upstream["expected_finalizer_commit"] != expected_commit
        or upstream["expected_reporting_commit"] != expected_commit
        or finalization["sha256"] != expected_manifest_sha256
        or report["path"] != str(report_path.resolve())
        or report["copy_path"] != str(report_copy_path.resolve())
        or report["independent_copy"] is not True
    ):
        raise ValueError("E2A reporting binding changed its fixed source/report contract")
    for name in ("sha256", "payload_sha256", "source_inventory_sha256"):
        _sha(report[name], what=f"E2A report {name}")
    _sha(finalization["manifest_digest"], what="E2A finalization manifest digest")
    _sha(document["receipt_digest"], what="E2A reporting receipt digest")
    expected_document = Plan._seal(
        {key: item for key, item in document.items() if key != "receipt_digest"},
        "receipt_digest",
    )
    if document != expected_document:
        raise ValueError("E2A reporting binding receipt digest is invalid")
    return {name: counts[name] for name in _REPORTING_COUNTS}


def finalize(*, expected_git_commit: str) -> dict[str, Any]:
    """Finalize labels with automatic checkpoint pins; print no label outcome."""

    _validate_fixed_layout()
    commit = _commit(expected_git_commit)
    launched = _load_launch(commit)
    inputs = _finalization_inputs(launched, commit)
    record = Finalize.finalize_exp2a_labels(
        inputs,
        export_root=LABEL_EXPORT_ROOT,
        durable_copy_root=LABEL_COPY_ROOT,
    )
    accounting = _validated_finalization_accounting(record)
    local = LABEL_EXPORT_ROOT / Finalize.MANIFEST_FILE
    copied = LABEL_COPY_ROOT / Finalize.MANIFEST_FILE
    manifest_pin = _pin_row(local, copied, what="E2A finalization manifest")
    reloaded = Finalize.load_exp2a_label_finalization(
        inputs,
        export_root=LABEL_EXPORT_ROOT,
        durable_copy_root=LABEL_COPY_ROOT,
        expected_manifest_sha256=manifest_pin["sha256"],
    )
    if reloaded != record or _validated_finalization_accounting(reloaded) != accounting:
        raise ValueError("E2A finalization return differs from its source-reloaded manifest")
    receipt = _publish_receipt(
        "finalize",
        status="complete",
        purpose="bind_complete_zero_compute_twenty_unit_label_finalization",
        payload={
            "expected_execution_commit": inputs.expected_execution_commit,
            "expected_finalizer_commit": commit,
            "launch_receipt_sha256": launched["_file_sha256"],
            "manifest": manifest_pin,
            "roots": {
                "export": str(LABEL_EXPORT_ROOT.resolve()),
                "durable_copy": str(LABEL_COPY_ROOT.resolve()),
            },
            "status": "complete",
            "counts": accounting,
            "fits_executed": 0,
        },
    )
    return _operational("finalize", receipt, status="complete")


def _load_finalize(expected_commit: str | None = None) -> dict[str, Any]:
    receipt = _load_receipt("finalize")
    payload = _expect_keys(
        receipt["payload"],
        {
            "expected_execution_commit",
            "expected_finalizer_commit",
            "launch_receipt_sha256",
            "manifest",
            "roots",
            "status",
            "counts",
            "fits_executed",
        },
        what="finalization handoff payload",
    )
    commit = _commit(payload["expected_finalizer_commit"])
    if expected_commit is not None and commit != _commit(expected_commit):
        raise ValueError("finalization commit differs from requested reporting commit")
    launched = _load_launch(payload["expected_execution_commit"])
    if payload["launch_receipt_sha256"] != launched["_file_sha256"]:
        raise ValueError("finalization handoff does not bind the released launch")
    local = LABEL_EXPORT_ROOT / Finalize.MANIFEST_FILE
    copied = LABEL_COPY_ROOT / Finalize.MANIFEST_FILE
    _validate_pin(payload["manifest"], local, copied, what="finalization manifest")
    if (
        payload["roots"]
        != {
            "export": str(LABEL_EXPORT_ROOT.resolve()),
            "durable_copy": str(LABEL_COPY_ROOT.resolve()),
        }
        or payload["status"] != "complete"
        or payload["fits_executed"] != 0
    ):
        raise ValueError("finalization handoff is not the fixed complete zero-compute phase")
    inputs = _finalization_inputs(launched, commit)
    record = Finalize.load_exp2a_label_finalization(
        inputs,
        export_root=LABEL_EXPORT_ROOT,
        durable_copy_root=LABEL_COPY_ROOT,
        expected_manifest_sha256=payload["manifest"]["sha256"],
    )
    accounting = _validated_finalization_accounting(record)
    if payload["counts"] != accounting:
        raise ValueError("finalization handoff accounting differs from its manifest")
    return receipt


def report(*, expected_git_commit: str) -> dict[str, Any]:
    """Publish the source-bound report using only automatic upstream pins."""

    _validate_fixed_layout()
    commit = _commit(expected_git_commit)
    finalized = _load_finalize(commit)
    launched = _load_launch(finalized["payload"]["expected_execution_commit"])
    inputs = _finalization_inputs(launched, commit)
    publication = Reporting.Exp2AReportPublicationInputs(
        finalization_inputs=inputs,
        export_root=LABEL_EXPORT_ROOT,
        durable_copy_root=LABEL_COPY_ROOT,
        expected_finalization_manifest_sha256=finalized["payload"]["manifest"][
            "sha256"
        ],
        expected_reporting_commit=commit,
    )
    _ensure_directory(REPORT_ROOT)
    _ensure_directory(REPORT_COPY_ROOT)
    report_path = REPORT_ROOT / REPORT_FILE
    report_copy = REPORT_COPY_ROOT / REPORT_FILE
    binding = REPORT_ROOT / REPORT_BINDING_FILE
    binding_copy = REPORT_COPY_ROOT / REPORT_BINDING_FILE
    binding_document = Reporting.write_source_bound_exp2a_report(
        publication,
        report_path=report_path,
        report_copy_path=report_copy,
        binding_receipt_path=binding,
    )
    accounting = _validated_reporting_binding(
        binding_document,
        expected_commit=commit,
        expected_execution_commit=finalized["payload"]["expected_execution_commit"],
        expected_manifest_sha256=finalized["payload"]["manifest"]["sha256"],
        report_path=report_path,
        report_copy_path=report_copy,
        binding_path=binding,
    )
    if read_json(binding) != binding_document:
        raise ValueError("reporting writer return differs from its immutable binding")
    _copy_file(binding, binding_copy, what="E2A report binding receipt")
    report_pin = _pin_row(report_path, report_copy, what="E2A report")
    binding_pin = _pin_row(
        binding, binding_copy, what="E2A report binding receipt"
    )
    if binding_document["report"]["sha256"] != report_pin["sha256"]:
        raise ValueError("reporting binding SHA differs from the published report")
    receipt = _publish_receipt(
        "report",
        status="complete",
        purpose="carry_finalization_pins_into_source_bound_descriptive_report",
        payload={
            "expected_reporting_commit": commit,
            "finalize_receipt_sha256": finalized["_file_sha256"],
            "report": report_pin,
            "report_binding": binding_pin,
            "counts": accounting,
            "sign_consistency_applied": False,
            "h2_verdict": None,
        },
    )
    return _operational("report", receipt, status="complete")


def _load_report(expected_commit: str | None = None) -> dict[str, Any]:
    receipt = _load_receipt("report")
    payload = _expect_keys(
        receipt["payload"],
        {
            "expected_reporting_commit",
            "finalize_receipt_sha256",
            "report",
            "report_binding",
            "counts",
            "sign_consistency_applied",
            "h2_verdict",
        },
        what="report handoff payload",
    )
    commit = _commit(payload["expected_reporting_commit"])
    if expected_commit is not None and commit != _commit(expected_commit):
        raise ValueError("report handoff commit differs from requested commit")
    finalized = _load_finalize(commit)
    if payload["finalize_receipt_sha256"] != finalized["_file_sha256"]:
        raise ValueError("report handoff does not bind finalization")
    report_sha = _validate_pin(
        payload["report"],
        REPORT_ROOT / REPORT_FILE,
        REPORT_COPY_ROOT / REPORT_FILE,
        what="E2A report",
    )
    _validate_pin(
        payload["report_binding"],
        REPORT_ROOT / REPORT_BINDING_FILE,
        REPORT_COPY_ROOT / REPORT_BINDING_FILE,
        what="E2A report binding",
    )
    binding_path = REPORT_ROOT / REPORT_BINDING_FILE
    binding_document = read_json(binding_path)
    accounting = _validated_reporting_binding(
        binding_document,
        expected_commit=commit,
        expected_execution_commit=finalized["payload"]["expected_execution_commit"],
        expected_manifest_sha256=finalized["payload"]["manifest"]["sha256"],
        report_path=REPORT_ROOT / REPORT_FILE,
        report_copy_path=REPORT_COPY_ROOT / REPORT_FILE,
        binding_path=binding_path,
    )
    if (
        payload["counts"] != accounting
        or binding_document["report"]["sha256"] != report_sha
    ):
        raise ValueError("report handoff accounting/digest differs from its binding")
    Figures.R.load_experiment_2a_report(
        REPORT_ROOT / REPORT_FILE, expected_sha256=report_sha
    )
    if payload["sign_consistency_applied"] is not False or payload["h2_verdict"] is not None:
        raise ValueError("Week-8 report handoff must leave H2 unapplied")
    return receipt


def _validated_figure_manifest(
    value: object, *, expected_report_sha256: str
) -> dict[str, int]:
    document = _expect_keys(
        value,
        {
            "experiment_2a_figure_schema_version",
            "kind",
            "interpretation",
            "source_report_sha256",
            "source_report_payload_sha256",
            "plot_data_sha256",
            "unit_count",
            "seed_count",
            "figure_count",
            "figures",
            "sign_consistency",
            "h2_verdict",
            "payload_sha256",
        },
        what="E2A figure manifest",
    )
    rows = document["figures"]
    if type(rows) is not list or len(rows) != 3:
        raise ValueError("E2A figure manifest must contain exactly three figures")
    expected_names = {
        Figures.FOREST_FILE,
        Figures.RATIO_FILE,
        Figures.PEARSON_FILE,
    }
    observed_names: set[str] = set()
    for row in rows:
        row = _expect_keys(row, {"filename", "kind", "sha256"}, what="figure row")
        if type(row["filename"]) is not str or type(row["kind"]) is not str:
            raise ValueError("figure manifest names/kinds must be exact strings")
        if row["filename"] not in expected_names or row["filename"] in observed_names:
            raise ValueError("figure manifest contains an unknown or duplicate filename")
        observed_names.add(row["filename"])
        _sha(row["sha256"], what="figure PNG SHA256")
        path = FIGURE_ROOT / row["filename"]
        if sha256_file(_plain_file(path, what="E2A figure PNG")) != row["sha256"]:
            raise ValueError("figure PNG differs from its manifest digest")
    if (
        observed_names != expected_names
        or type(document["experiment_2a_figure_schema_version"]) is not int
        or document["experiment_2a_figure_schema_version"] != Figures.FIGURE_SCHEMA_VERSION
        or document["kind"] != "offline_experiment_2a_figures"
        or document["source_report_sha256"] != expected_report_sha256
        or _nonnegative_int(document["unit_count"], what="figure unit count") != 20
        or _nonnegative_int(document["seed_count"], what="figure seed count") != 5
        or _nonnegative_int(document["figure_count"], what="figure count") != 3
        or document["sign_consistency"] is not None
        or document["h2_verdict"] is not None
    ):
        raise ValueError("E2A figure manifest changed its fixed 20/5/3/H2-null contract")
    for name in ("source_report_payload_sha256", "plot_data_sha256", "payload_sha256"):
        _sha(document[name], what=f"figure manifest {name}")
    expected = Plan._seal(
        {key: item for key, item in document.items() if key != "payload_sha256"},
        "payload_sha256",
    )
    if document != expected:
        raise ValueError("E2A figure manifest payload digest is invalid")
    return {"units": 20, "seeds": 5, "figures": 3}


def figures(*, expected_git_commit: str) -> dict[str, Any]:
    """Render offline figures using the report SHA from its immutable handoff."""

    _validate_fixed_layout()
    commit = _commit(expected_git_commit)
    before_environment = Launch._environment(commit)
    reported = _load_report(commit)
    report_row = reported["payload"]["report"]
    _ensure_directory(FIGURE_ROOT)
    _ensure_directory(FIGURE_CACHE_ROOT)
    configured = os.environ.get("MPLCONFIGDIR")
    if configured is not None and Path(configured).resolve() != FIGURE_CACHE_ROOT.resolve():
        raise ValueError("MPLCONFIGDIR differs from the fixed Week-8 E2A cache")
    os.environ["MPLCONFIGDIR"] = str(FIGURE_CACHE_ROOT.resolve())
    written = Figures.prepare_experiment_2a_figures(
        Path(report_row["path"]),
        expected_report_sha256=report_row["sha256"],
        figures_dir=FIGURE_ROOT,
    )
    after_environment = Launch._environment(commit)
    if after_environment != before_environment:
        raise ValueError("clean renderer environment changed during figure generation")
    manifest = FIGURE_ROOT / Figures.MANIFEST_FILE
    if manifest not in [Path(path) for path in written]:
        raise ValueError("figure renderer did not publish its canonical manifest last")
    manifest_sha = sha256_file(_plain_file(manifest, what="figure manifest"))
    accounting = _validated_figure_manifest(
        read_json(manifest), expected_report_sha256=report_row["sha256"]
    )
    receipt = _publish_receipt(
        "figures",
        status="complete",
        purpose="bind_three_offline_figures_to_the_immutable_report_sha",
        payload={
            "renderer_commit": commit,
            "renderer_environment": before_environment,
            "report_receipt_sha256": reported["_file_sha256"],
            "source_report": {
                "path": report_row["path"],
                "sha256": report_row["sha256"],
            },
            "figure_root": str(FIGURE_ROOT.resolve()),
            "matplotlib_cache": str(FIGURE_CACHE_ROOT.resolve()),
            "manifest": {"path": str(manifest.resolve()), "sha256": manifest_sha},
            "counts": accounting,
            "figure_count": accounting["figures"],
            "h2_verdict": None,
        },
    )
    return _operational("figures", receipt, status="complete")


def _operational(command: str, receipt: Mapping[str, Any], *, status: str) -> dict[str, Any]:
    """Return only operational fields safe for CLI display."""

    return {
        "command": command,
        "status": status,
        "receipt_path": receipt["receipt_paths"]["original"],
        "receipt_copy_path": receipt["receipt_paths"]["copy"],
        "receipt_sha256": receipt["_file_sha256"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "preflight", "launch", "finalize", "report", "figures"):
        child = subparsers.add_parser(name)
        child.add_argument("--expected-git-commit", required=True)
    subparsers.add_parser("monitor")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = vars(_parser().parse_args(argv))
    command = arguments.pop("command")
    handlers = {
        "prepare": prepare,
        "preflight": preflight,
        "launch": launch,
        "monitor": monitor,
        "finalize": finalize,
        "report": report,
        "figures": figures,
    }
    try:
        result = handlers[command](**arguments)
    except Exception as exc:
        # The terminal lower evidence retains the original diagnostics.  The
        # operator-facing CLI emits only a type and content digest: no traceback,
        # raw message, label, metric, ratio or scientific source path.
        failure = {
            "type": type(exc).__name__,
            "sha256": sha256_bytes(
                _canonical({"type": type(exc).__name__, "message": str(exc)})
            ),
        }
        print(
            json.dumps(
                {
                    "command": command,
                    "status": "stopped_with_preserved_failure",
                    "error": failure,
                },
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 1
    # The returned objects are deliberately operational-only.  Never print a
    # finalization manifest, report, label, metric, ratio or failure message.
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
