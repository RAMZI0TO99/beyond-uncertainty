"""Production preflight, fixed worker and recovery for Week-8 E2A repairs.

Only the 261 jobs derived by :mod:`week8_exp2a_repairs` are executable.  The
155 historical sources are fully reopened at preflight and completion and each
repair worker reopens its own exact seed baseline.  Every new attempt runs in a
fresh isolated process under the workspace-wide shared Week-7/Week-8 lease.  A
failed, unknown or partial attempt is evidence to preserve, not an automatic
retry opportunity.

The preflight, start checkpoint, immutable hash-chained event stream and final
report are independently copied inside project-local, non-overlapping roots.
No caller executor, job subset, source path, seed, scale or repair arm reaches
the worker.  CPU with the frozen 4/4 thread route is mandatory.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..durable import atomic_write_bytes, atomic_write_json, read_json, sha256_file
from . import batch as B
from . import confirmatory as C
from . import fit_evidence as F
from . import launch as L
from . import monitor as M
from . import preflight as P
from . import repair_label_preflight as RF
from . import week8_exp2a_repairs as W
from . import week8_exp2a_sources as S
from .prefit_storage import check_preflight_storage
from .supervisor import (
    AttemptOutcome,
    BatchLease,
    SUPERVISOR_SCHEMA_VERSION,
    acquire_batch_lease,
    run_isolated_attempt,
)


PREFLIGHT_SCHEMA_VERSION = 1
START_SCHEMA_VERSION = 1
# The certified per-fit storage guard dispatches on this established Week-8
# envelope name/schema.  The additive E2A schema remains present as a second,
# stricter discriminator inside the same immutable report.
PREFLIGHT_FILE = "week8_preflight_report.json"
EVENT_DIRECTORY = "week8_exp2a_repair_events"
REPORT_DIRECTORY = "week8_exp2a_repair_reports"
_EVENT_KINDS = {
    "attempt_started",
    "attempt_failed",
    "sync_pending",
    "job_synced",
    "complete",
}


@dataclass(frozen=True)
class ValidatedExp2APreflight:
    report_path: Path
    report_sha256: str
    report: dict[str, Any]
    roots: dict[str, Path]
    git_commit: str


def _environment(expected_git_commit: str) -> dict[str, Any]:
    commit = F._validate_expected_git_commit(expected_git_commit)
    state, versions, pins = P._verify_environment()
    if state.commit != commit or state.dirty or not state.trustworthy:
        raise ValueError("E2A repair execution requires the expected clean trustworthy commit")
    if (
        C.CONFIRMATORY_DEVICE,
        C.CONFIRMATORY_THREADS,
        C.CONFIRMATORY_INTEROP_THREADS,
    ) != ("cpu", 4, 4):
        raise ValueError("E2A repairs require the frozen CPU 4/4 production route")
    return {
        "git_commit": commit,
        "versions": versions,
        "pins": pins,
        "device": P._verify_device("cpu"),
        "num_threads": 4,
        "num_interop_threads": 4,
    }


def _released_environment(expected_git_commit: str) -> dict[str, Any]:
    commit = F._validate_expected_git_commit(expected_git_commit)
    _, versions, pins = P._verify_environment()
    if (
        C.CONFIRMATORY_DEVICE,
        C.CONFIRMATORY_THREADS,
        C.CONFIRMATORY_INTEROP_THREADS,
    ) != ("cpu", 4, 4):
        raise ValueError("released E2A evidence requires the frozen CPU 4/4 route")
    return {
        "git_commit": commit,
        "versions": versions,
        "pins": pins,
        "device": P._verify_device("cpu"),
        "num_threads": 4,
        "num_interop_threads": 4,
    }


def _inputs(plan_path: str | Path, source_ledger_path: str | Path):
    plan_file = W._project_path(plan_path, directory=False)
    ledger_file = W._project_path(source_ledger_path, directory=False)
    plan = W.load_exp2a_repair_plan(plan_file)
    ledger = S.load_exp2a_source_ledger(ledger_file)
    inputs = {
        "plan": {"path": str(plan_file), "sha256": sha256_file(plan_file)},
        "source_ledger": {"path": str(ledger_file), "sha256": sha256_file(ledger_file)},
    }
    budget = {
        "new_physical_fits": plan["counts"]["new_physical_fits"],
        "new_member_models": plan["counts"]["new_member_model_trainings"],
        "new_baseline_fits": plan["counts"]["new_baseline_fits"],
        "new_repair_fits": plan["counts"]["new_repair_fits"],
        "historical_sources_reopened": ledger["reused_fit_count"],
        "interpretation": "exact inventory counts; not a runtime or GPU-hour estimate",
    }
    return inputs, budget, plan, ledger


def _protected_paths() -> tuple[Path, ...]:
    return (
        S.SMOKE_OUTPUT_ROOT,
        S.SMOKE_COPY_ROOT,
        S.WEEK7_OUTPUT_ROOT,
        S.WEEK7_COPY_ROOT,
        S.WEEK7_RECEIPT_ROOT,
        W.COMMON_LEASE_ROOT,
    )


def _protect(roots: dict[str, Path], inputs: dict[str, Any]) -> None:
    _check_lease_namespace()
    values = tuple(roots.values())
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            if P._overlap(left, right):
                raise ValueError("preflight/execution roots must be pairwise non-overlapping")
        for protected in _protected_paths():
            if P._overlap(left, protected.resolve()):
                raise ValueError("execution root overlaps historical or common-control evidence")
        for row in inputs.values():
            if Path(row["path"]).resolve().is_relative_to(left):
                raise ValueError("plan and source ledger must remain outside execution roots")
    L._validate_same_volume_staging(roots["output"], roots["staging"])


def _same_file_copy(source: Path, copy: Path) -> None:
    for path in (source, copy):
        W._project_path(path, directory=False)
    if RF._same_file_identity(source, copy) or source.read_bytes() != copy.read_bytes():
        raise ValueError("required evidence copy must be independent and byte-identical")


def _input_copies(roots: dict[str, Path], inputs: dict[str, Any], *, write: bool) -> None:
    for key, source in inputs.items():
        path = Path(source["path"])
        for root in (roots["preflight"], roots["sync"]):
            destination = root / f"exp2a_input_{key}.json"
            if write:
                RF.sync_immutable_file(path, destination)
            _same_file_copy(path, destination)


def run_exp2a_repair_preflight(
    *,
    plan_path: str | Path,
    source_ledger_path: str | Path,
    expected_git_commit: str,
    preflight_dir: str | Path,
    output_root: str | Path,
    staging_root: str | Path,
    sync_root: str | Path,
    attempt_timeout_seconds: float,
    minimum_free_bytes: int,
    sync_destination_identity: str,
) -> dict[str, Any]:
    """Reopen all old sources, prove storage/copy IO and publish readiness only."""

    timeout = L._positive_number(
        attempt_timeout_seconds, what="attempt_timeout_seconds"
    )
    environment = _environment(expected_git_commit)
    inputs, budget, plan, _ = _inputs(plan_path, source_ledger_path)
    for path in (preflight_dir, output_root, staging_root, sync_root):
        W._project_path(path, directory=True)
    roots, storage = P._verify_storage(
        preflight_dir=preflight_dir,
        output_root=output_root,
        staging_root=staging_root,
        sync_root=sync_root,
        minimum_free_bytes=minimum_free_bytes,
    )
    _protect(roots, inputs)
    binding = W._seal(
        {
            "inputs": inputs,
            "plan_digest": plan["plan_digest"],
            "attempt_timeout_seconds": timeout,
        },
        "binding_sha256",
    )["binding_sha256"]
    destination = P._validate_destination_identity(sync_destination_identity)
    canary, receipt = P._run_sync_canary(
        roots=roots,
        plan_digest=binding,
        destination_identity=destination,
        adapter=P.sync_canary_to_mounted_directory,
    )
    _same_file_copy(Path(canary["source_path"]), Path(canary["destination_path"]))
    _input_copies(roots, inputs, write=True)
    report = {
        "week8_preflight_schema_version": PREFLIGHT_SCHEMA_VERSION,
        "exp2a_repair_preflight_schema_version": PREFLIGHT_SCHEMA_VERSION,
        "status": "ready",
        "launch_performed": False,
        "inputs": inputs,
        "budget": budget,
        "plan_digest": plan["plan_digest"],
        "binding_sha256": binding,
        "environment": environment,
        "storage": storage,
        "attempt_timeout_seconds": timeout,
        "common_control_root": str(W.COMMON_LEASE_ROOT.resolve()),
        "sync_canary": canary,
        "sync_receipt": receipt,
    }
    path = atomic_write_json(roots["preflight"] / PREFLIGHT_FILE, report)
    RF.sync_immutable_file(path, roots["sync"] / PREFLIGHT_FILE)
    validate_exp2a_repair_preflight(
        path,
        output_root=output_root,
        sync_root=sync_root,
        expected_git_commit=expected_git_commit,
    )
    return report


def validate_exp2a_repair_preflight(
    path: str | Path,
    *,
    output_root: str | Path,
    sync_root: str | Path,
    expected_git_commit: str,
) -> ValidatedExp2APreflight:
    report_path = W._project_path(path, directory=False)
    if report_path.name != PREFLIGHT_FILE:
        raise ValueError("E2A repairs require their own canonical preflight file")
    raw = report_path.read_bytes()
    report = L._strict_keys(
        read_json(report_path),
        {
            "week8_preflight_schema_version",
            "exp2a_repair_preflight_schema_version",
            "status",
            "launch_performed",
            "inputs",
            "budget",
            "plan_digest",
            "binding_sha256",
            "environment",
            "storage",
            "attempt_timeout_seconds",
            "common_control_root",
            "sync_canary",
            "sync_receipt",
        },
        what="Experiment-2A repair preflight",
    )
    if raw != L._pretty_json_bytes(report):
        raise ValueError("E2A preflight is not canonical immutable JSON")
    if (
        type(report["week8_preflight_schema_version"]) is not int
        or report["week8_preflight_schema_version"] != PREFLIGHT_SCHEMA_VERSION
        or type(report["exp2a_repair_preflight_schema_version"]) is not int
        or report["exp2a_repair_preflight_schema_version"] != PREFLIGHT_SCHEMA_VERSION
        or report["status"] != "ready"
        or report["launch_performed"] is not False
    ):
        raise ValueError("E2A repair preflight is not ready")
    inputs = L._strict_keys(
        report["inputs"], {"plan", "source_ledger"}, what="preflight inputs"
    )
    for name, row in inputs.items():
        L._strict_keys(row, {"path", "sha256"}, what=f"preflight {name}")
        L._lower_sha256(row["sha256"], what=f"preflight {name} SHA256")
    current, budget, plan, _ = _inputs(
        inputs["plan"]["path"], inputs["source_ledger"]["path"]
    )
    timeout = L._positive_number(
        report["attempt_timeout_seconds"], what="attempt timeout"
    )
    binding = W._seal(
        {
            "inputs": current,
            "plan_digest": plan["plan_digest"],
            "attempt_timeout_seconds": timeout,
        },
        "binding_sha256",
    )["binding_sha256"]
    W._equal(inputs, current, what="preflight source pins")
    W._equal(report["budget"], budget, what="preflight exact inventory budget")
    W._equal(
        report["environment"],
        _environment(expected_git_commit),
        what="preflight execution environment",
    )
    if report["plan_digest"] != plan["plan_digest"] or report["binding_sha256"] != binding:
        raise ValueError("preflight plan/source binding changed")
    if report["common_control_root"] != str(W.COMMON_LEASE_ROOT.resolve()):
        raise ValueError("preflight uses a different shared production lease root")
    roots = L._validate_storage(
        report["storage"],
        report_parent=report_path.parent,
        requested_output=W._project_path(output_root, directory=True),
        requested_sync=W._project_path(sync_root, directory=True),
    )
    _protect(roots, inputs)
    L._validate_sync_evidence(report, roots=roots, plan_sha256=binding)
    _same_file_copy(
        Path(report["sync_canary"]["source_path"]),
        Path(report["sync_canary"]["destination_path"]),
    )
    _input_copies(roots, inputs, write=False)
    _same_file_copy(report_path, roots["sync"] / PREFLIGHT_FILE)
    if report_path.read_bytes() != raw:
        raise ValueError("preflight changed during validation")
    return ValidatedExp2APreflight(
        report_path, sha256_file(report_path), report, roots, expected_git_commit
    )


def _check_lease_namespace() -> Path:
    root = W._project_path(W.COMMON_LEASE_ROOT, directory=True)
    for path in (root / "leases", root / "leases" / "history"):
        W._project_path(path, directory=True, existing=os.path.lexists(path))
    for name in (
        f"{W.COMMON_LEASE_NAME}.lease.json",
        f".{W.COMMON_LEASE_NAME}.lease-transition.lock",
    ):
        path = root / "leases" / name
        W._project_path(path, directory=False, existing=os.path.lexists(path))
    return root


def _lease_record(token: str) -> dict[str, Any]:
    if type(token) is not str or re.fullmatch(r"[0-9a-f]{32}", token) is None:
        raise ValueError("shared production lease token must be exact 32-hex")
    root = _check_lease_namespace()
    path, digest = M._load_active_lease(
        root / "leases" / f"{W.COMMON_LEASE_NAME}.lease.json",
        output_root=root,
        lease_name=W.COMMON_LEASE_NAME,
        lease_token=token,
    )
    return {
        "path": str(path),
        "sha256": digest,
        "name": W.COMMON_LEASE_NAME,
        "token": token,
        "started_at": read_json(path)["timestamp_utc"],
    }


def _historical_lease_record(token: str) -> dict[str, Any]:
    if type(token) is not str or re.fullmatch(r"[0-9a-f]{32}", token) is None:
        raise ValueError("prior shared production lease token must be exact 32-hex")
    root = _check_lease_namespace()
    active = root / "leases" / f"{W.COMMON_LEASE_NAME}.lease.json"
    history = (
        root
        / "leases"
        / "history"
        / f"{W.COMMON_LEASE_NAME}.{token}.released.json"
    )
    # D-161 preserves the externally orphaned epoch-001 lease under an
    # explicitly different classification.  Reserve its exact token before
    # every ordinary active/released-history branch so neither a stale active
    # owner record nor a forged normal release can bypass the transition and
    # orphan-archive validator.
    from . import week8_exp2a_recovery as Recovery

    if token == Recovery.OLD_LEASE_TOKEN:
        if os.path.lexists(history):
            raise ValueError("D-161 orphan token has forbidden normal release history")
        try:
            return Recovery.historical_orphan_lease_record(token)
        except Recovery.RecoveryRefused as exc:
            raise ValueError("D-161 orphan lease history is invalid") from exc
    if active.exists() and read_json(W._project_path(active, directory=False)).get("token") == token:
        return _lease_record(token)
    path = W._project_path(history, directory=False)
    record = L._strict_keys(
        read_json(path),
        {
            "schema_version",
            "lease_name",
            "pid",
            "token",
            "timestamp",
            "timestamp_utc",
        },
        what="released shared production lease",
    )
    if (
        type(record["schema_version"]) is not int
        or record["schema_version"] != SUPERVISOR_SCHEMA_VERSION
        or record["lease_name"] != W.COMMON_LEASE_NAME
        or record["token"] != token
        or type(record["pid"]) is not int
        or record["pid"] <= 0
    ):
        raise ValueError("released lease history does not prove the recorded owner")
    L._positive_number(record["timestamp"], what="released lease timestamp")
    M._require_timestamp(record["timestamp_utc"], what="released lease UTC timestamp")
    return {
        "path": str(active),
        "sha256": sha256_file(path),
        "name": W.COMMON_LEASE_NAME,
        "token": token,
        "started_at": record["timestamp_utc"],
    }


def _execution_context(start: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in start.items()
        if key not in {"lease", "checkpoint_digest", "execution_context_digest"}
    }
    return W._seal(payload, "execution_context_digest")


def write_exp2a_repair_start_checkpoint(
    *,
    source_ledger_path: str | Path,
    expected_git_commit: str,
    output_root: str | Path,
    staging_root: str | Path,
    sync_root: str | Path,
    attempt_timeout_seconds: float,
    lease: BatchLease,
    preflight_report: str | Path,
) -> Path:
    timeout = L._positive_number(
        attempt_timeout_seconds, what="attempt_timeout_seconds"
    )
    if type(lease) is not BatchLease or lease._released:
        raise ValueError("start checkpoint requires an exact active BatchLease")
    if (
        lease.name != W.COMMON_LEASE_NAME
        or lease.path.resolve()
        != (
            W.COMMON_LEASE_ROOT
            / "leases"
            / f"{W.COMMON_LEASE_NAME}.lease.json"
        ).resolve()
        or lease.history_dir.resolve()
        != (W.COMMON_LEASE_ROOT / "leases" / "history").resolve()
    ):
        raise ValueError("start checkpoint must use the shared Week-7/Week-8 lease")
    ledger_path = W._project_path(source_ledger_path, directory=False)
    ready = validate_exp2a_repair_preflight(
        preflight_report,
        output_root=output_root,
        sync_root=sync_root,
        expected_git_commit=expected_git_commit,
    )
    roots = {
        name: ready.roots[name] for name in ("output", "staging", "sync")
    }
    if (
        roots["staging"] != W._project_path(staging_root, directory=True)
        or ready.report["attempt_timeout_seconds"] != timeout
        or Path(ready.report["inputs"]["source_ledger"]["path"]).resolve()
        != ledger_path
    ):
        raise ValueError("start roots/timeout/source ledger differ from preflight")
    ledger_sha = sha256_file(ledger_path)
    ledger = S._metadata_source_ledger(ledger_path, ledger_sha)
    lease_row = _lease_record(lease.token)
    if read_json(Path(lease_row["path"]))["pid"] != os.getpid():
        raise ValueError("start checkpoint lease must belong to this launcher process")
    preflight = {
        "path": str(ready.report_path),
        "sha256": ready.report_sha256,
        "binding_sha256": ready.report["binding_sha256"],
    }
    payload = {
        "exp2a_repair_start_schema_version": START_SCHEMA_VERSION,
        "purpose": "source_verified_week8_exp2a_repair_start",
        "plan_digest": W.build_exp2a_repair_plan()["plan_digest"],
        "preflight": preflight,
        "source_ledger": {
            "path": str(ledger_path),
            "sha256": ledger_sha,
            "ledger_digest": ledger["ledger_digest"],
        },
        "environment": _environment(expected_git_commit),
        "roots": {name: str(path) for name, path in roots.items()},
        "attempt_timeout_seconds": timeout,
        "lease": lease_row,
        "fixed_worker": "bu.experiments.week8_exp2a_repair_launch._fit_worker",
        "supervisor_required": "bu.experiments.supervisor.run_isolated_attempt",
        "automatic_retry_allowed": False,
    }
    context = _execution_context(payload)
    document = W._seal(
        {**payload, "execution_context_digest": context["execution_context_digest"]},
        "checkpoint_digest",
    )
    for name in ("sync", "output"):
        atomic_write_json(roots[name] / W.CONTEXT_FILE, context)
    _same_file_copy(
        roots["output"] / W.CONTEXT_FILE, roots["sync"] / W.CONTEXT_FILE
    )
    paths: list[Path] = []
    for name in ("sync", "output"):
        directory = RF.ensure_regular_child_directory(roots[name], W.START_DIRECTORY)
        paths.append(atomic_write_json(directory / f"{lease.token}.json", document))
    _same_file_copy(paths[1], paths[0])
    return paths[1]


def _no_active_lease() -> None:
    root = _check_lease_namespace()
    if os.path.lexists(root / "leases" / f"{W.COMMON_LEASE_NAME}.lease.json"):
        raise ValueError("released-source reading requires no active shared lease")


def _read_start(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_git_commit: str,
    released: bool,
):
    if released:
        _no_active_lease()
    path = W._project_path(path, directory=False)
    expected_sha = L._lower_sha256(expected_sha256, what="checkpoint SHA256")
    if sha256_file(path) != expected_sha:
        raise ValueError("start checkpoint changed after worker dispatch")
    document = L._strict_keys(
        read_json(path),
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
        what="E2A repair start checkpoint",
    )
    root_rows = L._strict_keys(
        document["roots"], {"output", "staging", "sync"}, what="checkpoint roots"
    )
    roots = {
        name: W._project_path(value, directory=True)
        for name, value in root_rows.items()
    }
    ledger_row = L._strict_keys(
        document["source_ledger"],
        {"path", "sha256", "ledger_digest"},
        what="checkpoint source ledger",
    )
    preflight = L._strict_keys(
        document["preflight"],
        {"path", "sha256", "binding_sha256"},
        what="checkpoint preflight",
    )
    preflight_path = W._project_path(preflight["path"], directory=False)
    ledger_path = W._project_path(ledger_row["path"], directory=False)
    if sha256_file(preflight_path) != L._lower_sha256(
        preflight["sha256"], what="preflight SHA256"
    ):
        raise ValueError("production preflight changed after start")
    preflight_document = read_json(preflight_path)
    if (
        type(preflight_document) is not dict
        or preflight_document.get("binding_sha256")
        != L._lower_sha256(preflight["binding_sha256"], what="preflight binding")
    ):
        raise ValueError("production preflight source binding changed")
    preflight_inputs = L._strict_keys(
        preflight_document.get("inputs"),
        {"plan", "source_ledger"},
        what="checkpoint-bound preflight inputs",
    )
    _protect({"preflight": preflight_path.parent, **roots}, preflight_inputs)
    ledger = S._metadata_source_ledger(ledger_path, ledger_row["sha256"])
    lease = L._strict_keys(
        document["lease"],
        {"path", "sha256", "name", "token", "started_at"},
        what="checkpoint lease",
    )
    current_lease = (
        _historical_lease_record(lease["token"])
        if released
        else _lease_record(lease["token"])
    )
    expected = W._seal(
        {
            "exp2a_repair_start_schema_version": START_SCHEMA_VERSION,
            "purpose": "source_verified_week8_exp2a_repair_start",
            "plan_digest": W.build_exp2a_repair_plan()["plan_digest"],
            "preflight": {**preflight, "path": str(preflight_path)},
            "source_ledger": {
                "path": str(ledger_path),
                "sha256": ledger_row["sha256"],
                "ledger_digest": ledger["ledger_digest"],
            },
            "environment": (
                _released_environment(expected_git_commit)
                if released
                else _environment(expected_git_commit)
            ),
            "roots": {name: str(value) for name, value in roots.items()},
            "attempt_timeout_seconds": L._positive_number(
                document["attempt_timeout_seconds"], what="attempt timeout"
            ),
            "lease": current_lease,
            "fixed_worker": "bu.experiments.week8_exp2a_repair_launch._fit_worker",
            "supervisor_required": "bu.experiments.supervisor.run_isolated_attempt",
            "automatic_retry_allowed": False,
        },
        "checkpoint_digest",
    )
    context = _execution_context(expected)
    expected = W._seal(
        {
            **{key: value for key, value in expected.items() if key != "checkpoint_digest"},
            "execution_context_digest": context["execution_context_digest"],
        },
        "checkpoint_digest",
    )
    W._equal(document, expected, what="lease-bound E2A start checkpoint")
    local = roots["output"] / W.START_DIRECTORY / f"{current_lease['token']}.json"
    durable = roots["sync"] / W.START_DIRECTORY / local.name
    if path != local:
        raise ValueError("worker must use the prescribed local start checkpoint")
    _same_file_copy(local, durable)
    _same_file_copy(
        roots["output"] / W.CONTEXT_FILE, roots["sync"] / W.CONTEXT_FILE
    )
    W._equal(
        read_json(roots["output"] / W.CONTEXT_FILE),
        context,
        what="stable E2A execution context",
    )
    return document, ledger, roots


def _load_start(path: str | Path, *, expected_sha256: str, expected_git_commit: str):
    return _read_start(
        path,
        expected_sha256=expected_sha256,
        expected_git_commit=expected_git_commit,
        released=False,
    )


def _new_job(job_id: str) -> W.Exp2ARepairJob:
    jobs = [job for job in W.new_exp2a_jobs() if job.job_id == job_id]
    if type(job_id) is not str or len(jobs) != 1:
        raise ValueError("worker job is not one of the exact 261 new E2A fits")
    return jobs[0]


def _result_record(
    job: W.Exp2ARepairJob,
    verified: F.VerifiedFitEvidence,
    *,
    commit: str,
    checkpoint_digest: str,
    binding: dict[str, Any] | None,
    execution_context_digest: str,
) -> dict[str, Any]:
    return {
        "exp2a_repair_result_schema_version": 1,
        "job": job.as_record(),
        "expected_git_commit": commit,
        "checkpoint_digest": checkpoint_digest,
        "execution_context_digest": execution_context_digest,
        "fit_evidence_digest": verified.execution_digest,
        "baseline_source": binding,
    }


def _verify_prior_start(
    checkpoint_digest: str,
    current: dict[str, Any],
    roots: dict[str, Path],
) -> None:
    L._lower_sha256(checkpoint_digest, what="prior launch checkpoint digest")
    matches: list[Path] = []
    for path in (roots["output"] / W.START_DIRECTORY).glob("*.json"):
        document = read_json(W._project_path(path, directory=False))
        if type(document) is not dict or document.get("checkpoint_digest") != checkpoint_digest:
            continue
        if re.fullmatch(r"[0-9a-f]{32}\.json", path.name) is None:
            raise ValueError("prior start has a noncanonical lease-token filename")
        lease = _historical_lease_record(path.stem)
        payload = {
            key: value
            for key, value in current.items()
            if key not in {"lease", "checkpoint_digest"}
        }
        expected = W._seal({**payload, "lease": lease}, "checkpoint_digest")
        W._equal(document, expected, what="prior start and actual released lease")
        _same_file_copy(path, roots["sync"] / W.START_DIRECTORY / path.name)
        matches.append(path)
    if len(matches) != 1:
        raise ValueError("completed fit must bind exactly one genuine prior start")


def _baseline(
    job: W.Exp2ARepairJob,
    ledger: dict[str, Any],
    roots: dict[str, Path],
    commit: str,
    current: dict[str, Any],
) -> tuple[F.VerifiedFitEvidence, dict[str, Any]]:
    baseline = next(
        candidate
        for candidate in W.registered_exp2a_jobs()
        if candidate.unit == job.unit
        and candidate.seed == job.seed
        and candidate.arm == "baseline"
    )
    if W.source_kind(baseline) is not None:
        row = next(
            item for item in ledger["sources"] if item["job"]["job_id"] == baseline.job_id
        )
        verified, actual = S._source_pair(
            baseline,
            Path(row["source_path"]),
            Path(row["copy_path"]),
            commit=row["expected_git_commit"],
            expected_execution_digest=row["execution_digest"],
        )
        W._equal(actual, row, what="exact historical seed baseline")
    else:
        verified, actual = S._source_pair(
            baseline,
            roots["output"] / "jobs" / baseline.job_id,
            roots["sync"] / "jobs" / baseline.job_id,
            commit=commit,
        )
        result = read_json(
            W._project_path(Path(actual["source_path"]) / "job_result.json", directory=False)
        )
        _verify_prior_start(result.get("checkpoint_digest"), current, roots)
        W._equal(
            result,
            _result_record(
                baseline,
                verified,
                commit=commit,
                checkpoint_digest=result["checkpoint_digest"],
                binding=None,
                execution_context_digest=current["execution_context_digest"],
            ),
            what="new baseline completed before its repairs",
        )
    return verified, actual


def _assert_baseline_pair(
    job: W.Exp2ARepairJob,
    repair: F.VerifiedFitEvidence,
    baseline: F.VerifiedFitEvidence,
    *,
    what: str,
) -> None:
    """Require the same latent pool/scale and the arm-correct encoded pool.

    Feature restoration necessarily changes encoded observations, so its
    encoded-pool digest must differ.  The exact latent trajectory is instead
    pinned by action, episode and step inventories.  Data repair retains both
    the latent and encoded evaluation pool.
    """

    W._equal(repair.scale.as_row(), baseline.scale.as_row(), what=f"{what} scale")
    for name, observed, expected in (
        ("evaluation_action", repair.diagnostics.get("evaluation_action"),
         baseline.diagnostics.get("evaluation_action")),
        ("episode", repair.episode, baseline.episode),
        ("step", repair.step, baseline.step),
    ):
        if type(observed) is not np.ndarray or type(expected) is not np.ndarray:
            raise ValueError(f"{what} lacks exact verified {name} inventory")
        if not np.array_equal(observed, expected):
            raise ValueError(f"{what} does not reuse the baseline {name} inventory")
    if job.arm == "data_repair":
        W._equal(
            repair.evaluation_pool_digest,
            baseline.evaluation_pool_digest,
            what=f"{what} encoded evaluation pool",
        )
    elif job.arm == "feature_repair":
        if repair.evaluation_pool_digest == baseline.evaluation_pool_digest:
            raise ValueError(
                f"{what} feature restoration must change the encoded evaluation pool"
            )
    else:
        raise ValueError("E2A repair pairing received an unregistered repair arm")


def _fit_worker(attempt_dir: Path, payload: Any) -> dict[str, Any]:
    """Fixed private child: exact job, exact baseline, no caller scale."""

    row = L._strict_keys(
        payload,
        {"checkpoint_path", "checkpoint_sha256", "expected_git_commit", "job"},
        what="E2A repair worker payload",
    )
    job_record = row["job"]
    if type(job_record) is not dict:
        raise ValueError("worker job must be an exact registered record")
    job = _new_job(job_record.get("job_id"))
    W._equal(job_record, job.as_record(), what="worker full Config and roles")
    start, ledger, roots = _load_start(
        row["checkpoint_path"],
        expected_sha256=row["checkpoint_sha256"],
        expected_git_commit=row["expected_git_commit"],
    )
    attempt = W._project_path(attempt_dir, directory=True)
    if attempt.parent != roots["staging"] / "staging" or re.fullmatch(
        re.escape(job.job_id) + r"\.[0-9a-f]{32}", attempt.name
    ) is None:
        raise ValueError("worker attempt is not the supervisor's isolated staging child")
    attempt_record = L._strict_keys(
        read_json(W._project_path(attempt / "attempt.json", directory=False)),
        {
            "schema_version",
            "job_id",
            "attempt_token",
            "parent_pid",
            "started_at",
            "timeout_seconds",
        },
        what="supervisor attempt",
    )
    if (
        type(attempt_record["schema_version"]) is not int
        or attempt_record["schema_version"] != SUPERVISOR_SCHEMA_VERSION
        or attempt_record["job_id"] != job.job_id
        or attempt_record["attempt_token"] != attempt.name.rsplit(".", 1)[1]
        or type(attempt_record["parent_pid"]) is not int
        or attempt_record["parent_pid"] == os.getpid()
        or attempt_record["parent_pid"] != read_json(Path(start["lease"]["path"]))["pid"]
        or type(attempt_record["timeout_seconds"]) not in {int, float}
        or attempt_record["timeout_seconds"] != start["attempt_timeout_seconds"]
    ):
        raise ValueError("worker lacks exact timeout/fresh-process/lease-owner binding")
    M._require_timestamp(attempt_record["started_at"], what="supervisor attempt start")
    for directory in (
        roots["staging"] / "staging",
        roots["staging"] / "quarantine",
    ):
        if directory.exists() and any(
            path != attempt for path in directory.glob(f"{job.job_id}.*")
        ):
            raise ValueError("prior attempt evidence exists; automatic retry is prohibited")
    for root in (roots["output"], roots["sync"]):
        if os.path.lexists(root / "jobs" / job.job_id):
            raise ValueError("existing or partial job must be reconciled, never retrained")
    scale = None
    binding = None
    if job.arm != "baseline":
        baseline, binding = _baseline(
            job, ledger, roots, row["expected_git_commit"], start
        )
        scale = baseline.scale
    F.run_confirmatory_fit(
        job.unit,
        arm=job.arm,
        seed=job.seed,
        out_dir=attempt,
        scale=scale,
        expected_git_commit=row["expected_git_commit"],
    )
    verified = F.load_fit_evidence(
        attempt, expected_git_commit=row["expected_git_commit"]
    )
    S._match_fit(verified, job)
    if binding is not None:
        baseline_after, after = _baseline(
            job, ledger, roots, row["expected_git_commit"], start
        )
        W._equal(after, binding, what="baseline source before/after repair")
        _assert_baseline_pair(
            job, verified, baseline_after, what="repair exact baseline pairing"
        )
    return _result_record(
        job,
        verified,
        commit=row["expected_git_commit"],
        checkpoint_digest=start["checkpoint_digest"],
        binding=binding,
        execution_context_digest=start["execution_context_digest"],
    )


def _completed_source_pair(
    job: W.Exp2ARepairJob,
    start: dict[str, Any],
    ledger: dict[str, Any],
    roots: dict[str, Path],
    expected_git_commit: str,
) -> dict[str, Any] | None:
    local = roots["output"] / "jobs" / job.job_id
    durable = roots["sync"] / "jobs" / job.job_id
    exists = [os.path.lexists(path) for path in (local, durable)]
    if not any(exists):
        return None
    if not all(exists):
        raise ValueError("partial local/durable job requires sync recovery; no retraining")
    _, source = S._source_pair(
        job, local, durable, commit=expected_git_commit
    )
    _local_completed(job, start, ledger, roots, expected_git_commit)
    return source


def _local_completed(
    job: W.Exp2ARepairJob,
    start: dict[str, Any],
    ledger: dict[str, Any],
    roots: dict[str, Path],
    expected_git_commit: str,
) -> dict[str, Any]:
    local = W._project_path(roots["output"] / "jobs" / job.job_id, directory=True)
    S._plain_tree(local)
    verified = F.load_fit_evidence(local, expected_git_commit=expected_git_commit)
    S._match_fit(verified, job)
    result = L._strict_keys(
        read_json(W._project_path(local / "job_result.json", directory=False)),
        {
            "exp2a_repair_result_schema_version",
            "job",
            "expected_git_commit",
            "checkpoint_digest",
            "execution_context_digest",
            "fit_evidence_digest",
            "baseline_source",
        },
        what="completed E2A repair result",
    )
    binding = None
    if job.arm != "baseline":
        baseline, binding = _baseline(
            job, ledger, roots, expected_git_commit, start
        )
        _assert_baseline_pair(job, verified, baseline, what="recovered repair pairing")
    _verify_prior_start(result["checkpoint_digest"], start, roots)
    W._equal(
        result,
        _result_record(
            job,
            verified,
            commit=expected_git_commit,
            checkpoint_digest=result["checkpoint_digest"],
            binding=binding,
            execution_context_digest=start["execution_context_digest"],
        ),
        what="completed job result and stable context",
    )
    return {
        "result": result,
        "source_tree_digest": B._job_tree_digest(local),
        "execution_digest": verified.execution_digest,
    }


def validate_local_completed_exp2a_job(
    job_id: str,
    *,
    checkpoint_path: str | Path,
    checkpoint_sha256: str,
    expected_git_commit: str,
) -> dict[str, Any]:
    job = _new_job(job_id)
    start, ledger, roots = _load_start(
        checkpoint_path,
        expected_sha256=checkpoint_sha256,
        expected_git_commit=expected_git_commit,
    )
    return _local_completed(job, start, ledger, roots, expected_git_commit)


def reconcile_completed_exp2a_job(
    job_id: str,
    *,
    checkpoint_path: str | Path,
    checkpoint_sha256: str,
    expected_git_commit: str,
) -> dict[str, Any] | None:
    job = _new_job(job_id)
    start, ledger, roots = _load_start(
        checkpoint_path,
        expected_sha256=checkpoint_sha256,
        expected_git_commit=expected_git_commit,
    )
    return _completed_source_pair(job, start, ledger, roots, expected_git_commit)


def _event_directories(roots: dict[str, Path]) -> tuple[Path, Path]:
    return tuple(
        RF.ensure_regular_child_directory(roots[name], EVENT_DIRECTORY)
        for name in ("output", "sync")
    )  # type: ignore[return-value]


def _validate_event(
    row: dict[str, Any],
    *,
    index: int,
    previous: str | None,
    context_digest: str,
) -> None:
    L._strict_keys(
        row,
        {
            "event_schema_version",
            "sequence",
            "previous_digest",
            "execution_context_digest",
            "kind",
            "job_id",
            "data",
            "event_digest",
        },
        what="immutable E2A repair event",
    )
    if (
        type(row["event_schema_version"]) is not int
        or row["event_schema_version"] != 1
        or type(row["sequence"]) is not int
        or row["sequence"] != index
        or row["previous_digest"] != previous
        or row["execution_context_digest"] != context_digest
        or type(row["kind"]) is not str
        or row["kind"] not in _EVENT_KINDS
        or type(row["data"]) is not dict
    ):
        raise ValueError("E2A event sequence/context/schema is not exact")
    if row["kind"] == "complete":
        if row["job_id"] is not None:
            raise ValueError("completion event cannot name one fit")
        W._equal(
            row["data"],
            {"synced_physical_fits": 261, "historical_sources_reverified": 155},
            what="E2A completion counts",
        )
    else:
        _new_job(row["job_id"])
        if row["kind"] == "attempt_started":
            L._strict_keys(row["data"], {"checkpoint_digest"}, what="attempt start")
            L._lower_sha256(row["data"]["checkpoint_digest"], what="checkpoint digest")
        elif row["kind"] == "job_synced":
            L._strict_keys(
                row["data"],
                {"execution_digest", "source_tree_digest", "copy_evidence_digest"},
                what="synced result",
            )
            for name, value in row["data"].items():
                L._lower_sha256(value, what=name)
        else:
            L._strict_keys(row["data"], {"type", "message"}, what="preserved failure")
            if any(type(value) is not str for value in row["data"].values()):
                raise ValueError("failure event diagnostics must be strings")
    W._equal(
        row,
        W._seal(
            {key: value for key, value in row.items() if key != "event_digest"},
            "event_digest",
        ),
        what="E2A event content digest",
    )


def _load_events(
    roots: dict[str, Path], start: dict[str, Any]
) -> list[dict[str, Any]]:
    local, durable = _event_directories(roots)
    names: set[str] = set()
    for directory in (local, durable):
        for path in directory.iterdir():
            if re.fullmatch(r"[0-9]{6}\.json", path.name):
                W._project_path(path, directory=False)
                names.add(path.name)
            elif not (path.name.startswith(".") and path.name.endswith(".tmp")):
                raise ValueError("unknown file in immutable E2A event directory")
    if sorted(names) != [f"{index:06d}.json" for index in range(len(names))]:
        raise ValueError("immutable E2A event sequence has a gap")
    events: list[dict[str, Any]] = []
    previous = None
    for index, name in enumerate(sorted(names)):
        paths = local / name, durable / name
        existing = [path for path in paths if path.exists()]
        row = read_json(existing[0])
        _validate_event(
            row,
            index=index,
            previous=previous,
            context_digest=start["execution_context_digest"],
        )
        if row["kind"] == "attempt_started":
            _verify_prior_start(row["data"]["checkpoint_digest"], start, roots)
        for path in paths:
            if not path.exists():
                atomic_write_bytes(path, existing[0].read_bytes())
        _same_file_copy(*paths)
        events.append(row)
        previous = row["event_digest"]
    started: set[str] = set()
    synced: set[str] = set()
    completed = False
    for event in events:
        if completed:
            raise ValueError("events exist after exact-plan completion")
        if event["kind"] == "complete":
            if synced != {job.job_id for job in W.new_exp2a_jobs()}:
                raise ValueError("completion event is missing exact synced jobs")
            completed = True
        elif event["kind"] != "attempt_started" and event["job_id"] not in started:
            raise ValueError("E2A event has no preceding durable attempt start")
        target = (
            started
            if event["kind"] == "attempt_started"
            else synced
            if event["kind"] == "job_synced"
            else None
        )
        if target is not None:
            if event["job_id"] in target:
                raise ValueError("duplicate attempt/sync event; automatic retry is prohibited")
            target.add(event["job_id"])
    return events


def _append_event(
    roots: dict[str, Path],
    start: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    kind: str,
    job_id: str | None,
    data: dict[str, Any],
) -> None:
    row = W._seal(
        {
            "event_schema_version": 1,
            "sequence": len(events),
            "previous_digest": events[-1]["event_digest"] if events else None,
            "execution_context_digest": start["execution_context_digest"],
            "kind": kind,
            "job_id": job_id,
            "data": data,
        },
        "event_digest",
    )
    _validate_event(
        row,
        index=len(events),
        previous=row["previous_digest"],
        context_digest=start["execution_context_digest"],
    )
    local, durable = _event_directories(roots)
    name = f"{len(events):06d}.json"
    atomic_write_json(durable / name, row)
    atomic_write_json(local / name, row)
    _same_file_copy(local / name, durable / name)
    events.append(row)


def _request(
    checkpoint_path: Path,
    start: dict[str, Any],
    commit: str,
    job: W.Exp2ARepairJob,
) -> dict[str, Any]:
    return {
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "expected_git_commit": commit,
        "job": job.as_record(),
    }


def _request_kwargs(request: dict[str, Any]) -> dict[str, Any]:
    return {
        name: request[name]
        for name in ("checkpoint_path", "checkpoint_sha256", "expected_git_commit")
    }


def _sync_complete(
    job: W.Exp2ARepairJob,
    request: dict[str, Any],
    roots: dict[str, Path],
) -> dict[str, str]:
    before = validate_local_completed_exp2a_job(job.job_id, **_request_kwargs(request))
    source = roots["output"] / "jobs" / job.job_id
    destination = roots["sync"] / "jobs" / job.job_id
    W._project_path(source, directory=True)
    W._project_path(destination, directory=True, existing=False)
    B._publish_job_tree(source, destination)
    verified = reconcile_completed_exp2a_job(job.job_id, **_request_kwargs(request))
    if verified is None or verified["source_tree_digest"] != before["source_tree_digest"]:
        raise ValueError("completed source changed during durable synchronization")
    return {
        name: verified[name]
        for name in ("execution_digest", "source_tree_digest", "copy_evidence_digest")
    }


def _run_one_job(
    job: W.Exp2ARepairJob,
    *,
    validated: ValidatedExp2APreflight,
    checkpoint_path: Path,
    start: dict[str, Any],
    events: list[dict[str, Any]],
) -> str:
    roots = validated.roots
    request = _request(checkpoint_path, start, validated.git_commit, job)
    local = roots["output"] / "jobs" / job.job_id
    durable = roots["sync"] / "jobs" / job.job_id
    history = [event for event in events if event["job_id"] == job.job_id]
    synced = [event for event in history if event["kind"] == "job_synced"]
    if any(event["kind"] == "attempt_failed" for event in history):
        raise ValueError("prior failed attempt is preserved; no automatic retry")
    if os.path.lexists(local):
        if not any(event["kind"] == "attempt_started" for event in history):
            raise ValueError("complete local fit lacks durable launch-attempt history")
        result = _sync_complete(job, request, roots)
        if synced:
            W._equal(synced[0]["data"], result, what="resumed sync attestation")
        else:
            _append_event(
                roots, start, events, kind="job_synced", job_id=job.job_id, data=result
            )
        return "resumed"
    if os.path.lexists(durable) or history:
        raise ValueError("job has prior evidence without a complete local fit; no retraining")
    for directory in (
        roots["staging"] / "staging",
        roots["staging"] / "quarantine",
    ):
        if directory.exists() and any(directory.glob(f"{job.job_id}.*")):
            raise ValueError("preserved prior attempt requires inspection; no retry")
    _environment(validated.git_commit)
    check_preflight_storage(
        validated.report_path, validated.report_sha256, roots=roots
    )
    _append_event(
        roots,
        start,
        events,
        kind="attempt_started",
        job_id=job.job_id,
        data={"checkpoint_digest": start["checkpoint_digest"]},
    )
    try:
        outcome = run_isolated_attempt(
            _fit_worker,
            root=roots["output"],
            staging_root=roots["staging"],
            job_id=job.job_id,
            payload=request,
            timeout_seconds=validated.report["attempt_timeout_seconds"],
        )
        if (
            type(outcome) is not AttemptOutcome
            or outcome.job_id != job.job_id
            or not outcome.succeeded
            or outcome.canonical_dir != local
        ):
            raise ValueError("isolated attempt did not publish the exact successful fit")
    except BaseException as exc:
        _append_event(
            roots,
            start,
            events,
            kind="attempt_failed",
            job_id=job.job_id,
            data={"type": type(exc).__name__, "message": str(exc)},
        )
        raise
    try:
        result = _sync_complete(job, request, roots)
    except BaseException as exc:
        _append_event(
            roots,
            start,
            events,
            kind="sync_pending",
            job_id=job.job_id,
            data={"type": type(exc).__name__, "message": str(exc)},
        )
        raise
    _append_event(
        roots, start, events, kind="job_synced", job_id=job.job_id, data=result
    )
    return "executed"


def launch_exp2a_repairs(
    *,
    preflight_report: str | Path,
    output_root: str | Path,
    sync_root: str | Path,
    expected_git_commit: str,
) -> dict[str, Any]:
    """Execute/resume exactly 261 jobs and stop on the first preserved failure."""

    validated = validate_exp2a_repair_preflight(
        preflight_report,
        output_root=output_root,
        sync_root=sync_root,
        expected_git_commit=expected_git_commit,
    )
    original_preflight_sha = validated.report_sha256
    jobs = W.new_exp2a_jobs()
    W._equal(
        [job.as_record() for job in jobs],
        W.build_exp2a_repair_plan()["new_jobs"],
        what="exact new E2A launch jobs",
    )
    lease = acquire_batch_lease(
        _check_lease_namespace(), lease_name=W.COMMON_LEASE_NAME
    )
    checkpoint_path: Path | None = None
    failure: dict[str, str] | None = None
    complete = False
    counts = {"executed": 0, "resumed": 0, "synced": 0, "total": len(jobs)}
    paths: list[Path] = []
    try:
        revalidated = validate_exp2a_repair_preflight(
            preflight_report,
            output_root=output_root,
            sync_root=sync_root,
            expected_git_commit=expected_git_commit,
        )
        if revalidated.report_sha256 != original_preflight_sha:
            raise ValueError("preflight changed after the production lease was acquired")
        checkpoint_path = write_exp2a_repair_start_checkpoint(
            source_ledger_path=validated.report["inputs"]["source_ledger"]["path"],
            expected_git_commit=validated.git_commit,
            output_root=validated.roots["output"],
            staging_root=validated.roots["staging"],
            sync_root=validated.roots["sync"],
            attempt_timeout_seconds=validated.report["attempt_timeout_seconds"],
            lease=lease,
            preflight_report=validated.report_path,
        )
        start = read_json(checkpoint_path)
        if start["preflight"]["sha256"] != original_preflight_sha:
            raise ValueError("start checkpoint bound a different preflight")
        events = _load_events(validated.roots, start)
        for job in jobs:
            status = _run_one_job(
                job,
                validated=validated,
                checkpoint_path=checkpoint_path,
                start=start,
                events=events,
            )
            counts[status] += 1
            counts["synced"] += 1
        revalidated = validate_exp2a_repair_preflight(
            preflight_report,
            output_root=output_root,
            sync_root=sync_root,
            expected_git_commit=expected_git_commit,
        )
        if revalidated.report_sha256 != original_preflight_sha:
            raise ValueError("preflight changed before exact-plan completion")
        for job in jobs:
            request = _request(checkpoint_path, start, validated.git_commit, job)
            if reconcile_completed_exp2a_job(
                job.job_id, **_request_kwargs(request)
            ) is None:
                raise ValueError("a new fit disappeared before completion")
        if not any(event["kind"] == "complete" for event in events):
            _append_event(
                validated.roots,
                start,
                events,
                kind="complete",
                job_id=None,
                data={
                    "synced_physical_fits": 261,
                    "historical_sources_reverified": 155,
                },
            )
        complete = True
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        released = None
        release_error: BaseException | None = None
        try:
            _check_lease_namespace()
            released = lease.release()
        except BaseException as exc:
            release_error = exc
        interrupted = failure is not None and failure["type"] in {
            "KeyboardInterrupt",
            "SystemExit",
        }
        report = {
            "exp2a_repair_launch_schema_version": 1,
            "status": (
                "complete"
                if complete and released is not None
                else "interrupted"
                if interrupted
                else "incomplete"
            ),
            "counts": counts,
            "failure": failure,
            "historical_retrained": False,
            "preflight": {
                "path": str(validated.report_path),
                "sha256": validated.report_sha256,
            },
            "checkpoint": (
                None
                if checkpoint_path is None
                else {
                    "path": str(checkpoint_path),
                    "sha256": sha256_file(checkpoint_path),
                }
            ),
            "released_lease": (
                None
                if released is None
                else {"token": lease.token, "history_path": str(released)}
            ),
            "lease_release_failure": (
                None
                if release_error is None
                else {
                    "type": type(release_error).__name__,
                    "message": str(release_error),
                    "token": lease.token,
                    "active_path": str(lease.path),
                    "automatic_recovery_allowed": False,
                }
            ),
        }
        for name in ("sync", "output"):
            directory = RF.ensure_regular_child_directory(
                validated.roots[name], REPORT_DIRECTORY
            )
            paths.append(atomic_write_json(directory / f"{lease.token}.json", report))
        _same_file_copy(paths[1], paths[0])
        if release_error is not None:
            raise release_error
    return {**report, "report_path": str(paths[1])}


def load_released_exp2a_source_inventory(
    *,
    checkpoint_path: str | Path,
    checkpoint_sha256: str,
    expected_execution_commit: str,
) -> dict[str, Any]:
    """Read all old/new source pairs after lease release; never train or heal."""

    start, metadata_ledger, roots = _read_start(
        checkpoint_path,
        expected_sha256=checkpoint_sha256,
        expected_git_commit=expected_execution_commit,
        released=True,
    )
    ledger = S.load_exp2a_source_ledger(start["source_ledger"]["path"])
    W._equal(ledger, metadata_ledger, what="released full historical source ledger")
    sources = list(ledger["sources"])
    pending: list[str] = []
    for job in W.new_exp2a_jobs():
        source = _completed_source_pair(
            job, start, ledger, roots, expected_execution_commit
        )
        if source is None:
            pending.append(job.job_id)
        else:
            sources.append(source)
    W._equal(
        S.load_exp2a_source_ledger(start["source_ledger"]["path"]),
        ledger,
        what="historical sources after released inventory verification",
    )
    after, _, _ = _read_start(
        checkpoint_path,
        expected_sha256=checkpoint_sha256,
        expected_git_commit=expected_execution_commit,
        released=True,
    )
    W._equal(after, start, what="released checkpoint after source verification")
    return {
        "start": start,
        "ledger": ledger,
        "roots": roots,
        "sources": sorted(sources, key=lambda row: row["job"]["job_id"]),
        "pending_new_fit_ids": sorted(pending),
    }
