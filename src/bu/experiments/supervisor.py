"""Process isolation and attempt staging for unattended batch work.

This module is deliberately generic.  It does not know about scientific
``Config`` or ``BatchJob`` records; callers provide a safe job identifier, a
picklable top-level callback, and a picklable payload.  Every callback runs in
a fresh ``spawn`` process so a failed condition cannot poison the supervisor's
Python or accelerator state.

The parent process is the only writer of ``job_result.json`` and
``attempt_receipt.json``.  Failed attempts are atomically moved from
``staging`` to ``quarantine``.  Successful attempts are atomically published
under ``jobs`` only after a complete JSON result exists.  Existing divergent
evidence is never overwritten.

Batch leases are immutable ownership records created with exclusive file
creation. A stable OS-level transition lock closes ownership races. Normal
release preserves the old lease under an exclusive hard-link name in
``leases/history`` before removing the active name. Time-only stale recovery
is deliberately disabled: acquisition age cannot prove that an owner died.
"""

from __future__ import annotations

import errno
import hashlib
import json
import math
import multiprocessing
import os
import pickle
import re
import time
import traceback
import uuid
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


SUPERVISOR_SCHEMA_VERSION = 2
ATTEMPT_FILE = "attempt.json"
RESULT_FILE = "job_result.json"
RECEIPT_FILE = "attempt_receipt.json"

AttemptStatus = Literal[
    "success",
    "python_exception",
    "process_exit",
    "timeout",
]

JobCallback = Callable[[Path, Any], Mapping[str, Any]]

_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")


class DivergentEvidenceError(ValueError):
    """Raised when a completed attempt conflicts with published evidence."""

    def __init__(self, message: str, *, quarantine_dir: Path) -> None:
        super().__init__(message)
        self.quarantine_dir = quarantine_dir


class LeaseConflictError(ValueError):
    """Raised when another owner holds a live or non-recoverable lease."""


@dataclass(frozen=True)
class AttemptOutcome:
    """Parent-authored outcome of one isolated process attempt."""

    job_id: str
    attempt_token: str
    status: AttemptStatus
    attempt_dir: Path
    canonical_dir: Path | None
    exit_code: int | None
    error_type: str | None = None
    error: str | None = None
    published: bool = False

    @property
    def succeeded(self) -> bool:
        return self.status == "success"


@dataclass
class BatchLease:
    """One active batch lease.

    ``release`` is token-checked and preserves the lease record in history.
    The method is idempotent only for this object; a different owner can never
    release a lease merely by naming its path.
    """

    path: Path
    history_dir: Path
    name: str
    token: str
    _released: bool = False

    def release(self) -> Path:
        if self._released:
            return self.history_dir / f"{self.name}.{self.token}.released.json"
        destination = self.history_dir / (
            f"{self.name}.{self.token}.released.json"
        )
        guard = _lease_guard_path(self.path, self.name)
        with _lease_transition_lock(guard):
            try:
                record = _read_json_object(self.path)
            except FileNotFoundError as exc:
                raise LeaseConflictError(
                    f"active lease {self.path} disappeared before release"
                ) from exc
            if record.get("token") != self.token:
                raise LeaseConflictError(
                    f"active lease {self.path} belongs to another owner; "
                    "refusing to release it"
                )
            _archive_file_exclusive(self.path, destination)
        self._released = True
        return destination

    def __enter__(self) -> BatchLease:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.release()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_component(value: object, *, what: str) -> str:
    if type(value) is not str or not _SAFE_COMPONENT.fullmatch(value):
        raise ValueError(
            f"{what} must be a safe nonempty path component of at most 200 "
            f"characters, got {value!r}"
        )
    if value in {".", ".."}:
        raise ValueError(f"{what} cannot be {value!r}")
    return value


def _validate_positive_finite(value: object, *, what: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{what} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{what} must be a finite positive number")
    return number


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _filesystem_identity(path: Path) -> tuple[int, str]:
    """Return the local volume identity used to gate atomic publication."""
    resolved = path.resolve()
    drive = os.path.splitdrive(str(resolved))[0].casefold()
    return int(resolved.stat().st_dev), drive


def _attempt_roots(
    output_root: Path, staging_root: str | Path | None
) -> tuple[Path, Path]:
    """Resolve staging/quarantine roots and prove atomic publication is safe."""
    if staging_root is None:
        return output_root / "staging", output_root / "quarantine"

    output_root.mkdir(parents=True, exist_ok=True)
    staging_base = Path(staging_root)
    staging_base.mkdir(parents=True, exist_ok=True)
    resolved_output = output_root.resolve()
    resolved_staging = staging_base.resolve()
    if _paths_overlap(resolved_output, resolved_staging):
        raise ValueError(
            "output root and separate staging root must be distinct, "
            "non-overlapping directories"
        )
    if _filesystem_identity(resolved_output) != _filesystem_identity(
        resolved_staging
    ):
        raise ValueError(
            "output root and separate staging root must be on the same "
            "filesystem volume for atomic directory publication"
        )
    return resolved_staging / "staging", resolved_staging / "quarantine"


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    """Write one complete JSON object without exposing a partial final file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_bytes(value)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    """Create one JSON object and refuse any existing path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_bytes(value)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _job_tree_inventory(root: Path) -> tuple[dict[str, Any], ...]:
    """Return a canonical inventory of one job's immutable payload tree.

    ``attempt.json`` and ``attempt_receipt.json`` are supervisor control
    records whose timestamps, PIDs, and attempt tokens necessarily differ
    between equivalent attempts. Every other directory and regular file,
    including ``job_result.json`` and worker-authored side artifacts, is part
    of the payload identity. Links and special files are refused because
    their targets or contents can change after publication.
    """
    if not root.is_dir():
        raise ValueError(f"job tree {root} must be a directory")
    inventory: list[dict[str, Any]] = []
    paths = sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if relative in {ATTEMPT_FILE, RECEIPT_FILE}:
            continue
        if path.is_symlink():
            raise ValueError(
                f"job tree {root} contains unsupported link {relative!r}"
            )
        if path.is_dir():
            inventory.append({"kind": "directory", "path": relative})
            continue
        if not path.is_file():
            raise ValueError(
                f"job tree {root} contains unsupported entry {relative!r}"
            )
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        inventory.append(
            {
                "kind": "file",
                "path": relative,
                "size": size,
                "sha256": digest.hexdigest(),
            }
        )
    if not any(
        entry["kind"] == "file" and entry["path"] == RESULT_FILE
        for entry in inventory
    ):
        raise ValueError(f"job tree {root} has no {RESULT_FILE}")
    return tuple(inventory)


def _job_tree_digest(root: Path) -> str:
    inventory = {"entries": _job_tree_inventory(root)}
    return hashlib.sha256(_canonical_json_bytes(inventory)).hexdigest()


def _lease_guard_path(active: Path, lease_name: str) -> Path:
    return active.with_name(f".{lease_name}.lease-transition.lock")


@contextmanager
def _lease_transition_lock(path: Path):
    """Serialize lease read/archive/create transitions across processes.

    The lock lives at a stable path that is never renamed with the active
    lease. Windows uses a one-byte ``msvcrt`` range lock; POSIX uses
    ``flock``. Both are released by the OS if the holder process exits.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:  # pragma: no cover - exercised on non-Windows CI
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _archive_file_exclusive(source: Path, destination: Path) -> None:
    """Archive ``source`` without any overwrite window.

    A hard link gives exclusive destination creation on Windows and POSIX.
    Only after the immutable history name exists is the active name removed.
    A crash between those operations leaves duplicate names for the same
    bytes and therefore fails closed on the next transition.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except FileExistsError as exc:
        raise LeaseConflictError(
            f"lease history {destination} already exists; refusing to "
            "overwrite ownership evidence"
        ) from exc
    try:
        source.unlink()
    except OSError as exc:
        raise LeaseConflictError(
            f"lease history {destination} was preserved but active lease "
            f"{source} could not be removed"
        ) from exc


def _spawn_worker(
    callback: JobCallback,
    attempt_dir: str,
    payload: Any,
    connection: Any,
) -> None:
    """Top-level spawn target; never replace with a closure or lambda."""
    try:
        result = callback(Path(attempt_dir), payload)
        if not isinstance(result, Mapping):
            raise TypeError(
                "isolated job callback must return a mapping for job_result.json"
            )
        result_object = dict(result)
        # Serialize in the child to turn malformed/non-JSON callback output
        # into a classified Python exception.  The parent still owns the file.
        result_json = json.dumps(
            result_object,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        connection.send({"kind": "success", "result_json": result_json})
    except Exception as exc:
        try:
            connection.send(
                {
                    "kind": "python_exception",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        except Exception:
            # If IPC itself is broken, the parent will classify the missing
            # protocol message from the process exit.
            pass
    finally:
        connection.close()


def _wait_for_worker(
    process: multiprocessing.Process,
    connection: Any,
    timeout_seconds: float,
) -> tuple[dict[str, Any] | None, bool]:
    """Drain the pipe while waiting so large JSON results cannot deadlock."""
    deadline = time.monotonic() + timeout_seconds
    message: dict[str, Any] | None = None
    timed_out = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            if process.is_alive():
                timed_out = True
            break
        if connection.poll(min(0.05, remaining)):
            try:
                received = connection.recv()
            except EOFError:
                received = None
            if isinstance(received, dict):
                message = received
            break
        if not process.is_alive():
            break

    if timed_out:
        process.terminate()
        process.join(2.0)
        if process.is_alive():
            process.kill()
            process.join(2.0)
    else:
        remaining = max(0.0, deadline - time.monotonic())
        process.join(remaining)
        if process.is_alive():
            timed_out = True
            process.terminate()
            process.join(2.0)
            if process.is_alive():
                process.kill()
                process.join(2.0)
    return message, timed_out


def _quarantine(staging: Path, quarantine_root: Path) -> Path:
    quarantine_root.mkdir(parents=True, exist_ok=True)
    destination = quarantine_root / staging.name
    if destination.exists():
        raise ValueError(
            f"quarantine destination {destination} already exists; refusing to "
            "overwrite attempt evidence"
        )
    os.replace(staging, destination)
    return destination


def _same_published_tree(staging: Path, canonical: Path) -> bool:
    """Compare every immutable payload entry, not only the summary JSON."""
    try:
        return _job_tree_inventory(staging) == _job_tree_inventory(canonical)
    except (OSError, ValueError):
        return False


def run_isolated_attempt(
    callback: JobCallback,
    *,
    root: str | Path,
    staging_root: str | Path | None = None,
    job_id: str,
    payload: Any = None,
    timeout_seconds: float,
) -> AttemptOutcome:
    """Run one job in a fresh spawned process and preserve its evidence.

    Worker failures are returned as classified :class:`AttemptOutcome`
    records. Publication conflicts are parent-side integrity failures and
    raise :class:`DivergentEvidenceError` after quarantining the new attempt.

    ``staging_root`` may place staging and quarantine outside ``root`` while
    canonical jobs remain under ``root/jobs``. A separate root must neither
    overlap ``root`` nor cross a filesystem-volume boundary: publication is a
    single atomic directory rename, never a copy-and-delete fallback.
    """
    safe_job_id = _validate_component(job_id, what="job_id")
    timeout = _validate_positive_finite(
        timeout_seconds, what="timeout_seconds"
    )
    if not callable(callback):
        raise ValueError("callback must be callable")
    try:
        pickle.dumps((callback, payload))
    except Exception as exc:
        raise ValueError(
            "callback and payload must be picklable for a fresh spawned process"
        ) from exc

    root_path = Path(root)
    attempt_staging_root, quarantine_root = _attempt_roots(
        root_path, staging_root
    )
    canonical = root_path / "jobs" / safe_job_id
    attempt_staging_root.mkdir(parents=True, exist_ok=True)
    attempt_token = uuid.uuid4().hex
    staging = attempt_staging_root / f"{safe_job_id}.{attempt_token}"
    staging.mkdir()

    started_at = _utc_now()
    started_monotonic = time.monotonic()
    _write_json_exclusive(
        staging / ATTEMPT_FILE,
        {
            "schema_version": SUPERVISOR_SCHEMA_VERSION,
            "job_id": safe_job_id,
            "attempt_token": attempt_token,
            "parent_pid": os.getpid(),
            "started_at": started_at,
            "timeout_seconds": timeout,
        },
    )

    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_spawn_worker,
        args=(callback, str(staging), payload, send_connection),
        name=f"bu-job-{safe_job_id[:40]}",
    )
    process.start()
    child_pid = process.pid
    send_connection.close()
    try:
        message, timed_out = _wait_for_worker(
            process, receive_connection, timeout
        )
    finally:
        receive_connection.close()

    elapsed = time.monotonic() - started_monotonic
    exit_code = process.exitcode
    status: AttemptStatus
    error_type: str | None = None
    error: str | None = None
    worker_traceback: str | None = None
    result: dict[str, Any] | None = None

    if timed_out:
        status = "timeout"
        error_type = "TimeoutError"
        error = f"isolated job exceeded {timeout} seconds"
    elif exit_code != 0:
        status = "process_exit"
        error_type = "ProcessExitError"
        error = (
            "isolated job exited without a successful worker protocol "
            f"message (exit code {exit_code})"
        )
    elif message is None:
        status = "process_exit"
        error_type = "WorkerProtocolError"
        error = "isolated job exited without a worker protocol message"
    elif message.get("kind") == "python_exception":
        status = "python_exception"
        error_type = str(message.get("error_type", "Exception"))
        error = str(message.get("error", ""))
        worker_traceback = str(message.get("traceback", ""))
    elif message.get("kind") == "success":
        try:
            decoded = json.loads(message["result_json"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            status = "process_exit"
            error_type = "WorkerProtocolError"
            error = f"worker returned a malformed success message: {exc}"
        else:
            if not isinstance(decoded, dict):
                status = "process_exit"
                error_type = "WorkerProtocolError"
                error = "worker success result was not a JSON object"
            else:
                status = "success"
                result = decoded
    else:
        status = "process_exit"
        error_type = "WorkerProtocolError"
        error = "worker returned an unknown protocol message"

    receipt: dict[str, Any] = {
        "schema_version": SUPERVISOR_SCHEMA_VERSION,
        "job_id": safe_job_id,
        "attempt_token": attempt_token,
        "status": status,
        "parent_pid": os.getpid(),
        "child_pid": child_pid,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "elapsed_seconds": elapsed,
        "timeout_seconds": timeout,
        "exit_code": exit_code,
        "error_type": error_type,
        "error": error,
    }
    if worker_traceback is not None:
        receipt["traceback"] = worker_traceback

    if status != "success":
        _write_json_exclusive(staging / RECEIPT_FILE, receipt)
        quarantined = _quarantine(staging, quarantine_root)
        return AttemptOutcome(
            job_id=safe_job_id,
            attempt_token=attempt_token,
            status=status,
            attempt_dir=quarantined,
            canonical_dir=None,
            exit_code=exit_code,
            error_type=error_type,
            error=error,
        )

    if result is None:  # pragma: no cover - narrowed by the status branch
        raise RuntimeError("internal supervisor result-state mismatch")
    _write_json_exclusive(staging / RESULT_FILE, result)
    result_digest = hashlib.sha256(_canonical_json_bytes(result)).hexdigest()
    receipt["result_digest"] = result_digest
    receipt["job_tree_digest"] = _job_tree_digest(staging)

    if canonical.exists():
        if _same_published_tree(staging, canonical):
            receipt["published"] = False
            receipt["already_published"] = True
            _write_json_exclusive(staging / RECEIPT_FILE, receipt)
            duplicate = _quarantine(staging, quarantine_root)
            return AttemptOutcome(
                job_id=safe_job_id,
                attempt_token=attempt_token,
                status="success",
                attempt_dir=duplicate,
                canonical_dir=canonical,
                exit_code=exit_code,
                published=False,
            )
        receipt["status"] = "publish_refused"
        receipt["error_type"] = "DivergentEvidenceError"
        receipt["error"] = (
            f"canonical job directory {canonical} already contains divergent "
            "evidence"
        )
        _write_json_exclusive(staging / RECEIPT_FILE, receipt)
        quarantined = _quarantine(staging, quarantine_root)
        raise DivergentEvidenceError(
            str(receipt["error"]), quarantine_dir=quarantined
        )

    receipt["published"] = True
    _write_json_exclusive(staging / RECEIPT_FILE, receipt)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(staging, canonical)
    except OSError as exc:
        # A concurrent publisher may have won after the existence check.  An
        # identical result is safe and retained as a quarantined duplicate;
        # divergent bytes remain a hard refusal.
        if canonical.exists() and _same_published_tree(staging, canonical):
            duplicate = _quarantine(staging, quarantine_root)
            return AttemptOutcome(
                job_id=safe_job_id,
                attempt_token=attempt_token,
                status="success",
                attempt_dir=duplicate,
                canonical_dir=canonical,
                exit_code=exit_code,
                published=False,
            )
        if staging.exists():
            quarantined = _quarantine(staging, quarantine_root)
        else:
            quarantined = quarantine_root / staging.name
        if exc.errno == errno.EXDEV or getattr(exc, "winerror", None) == 17:
            detail = (
                "atomic directory publication crossed a filesystem-volume "
                "boundary; output and staging roots must share one volume"
            )
        else:
            detail = str(exc)
        raise DivergentEvidenceError(
            f"could not publish {staging} to {canonical} without overwriting "
            f"evidence: {detail}",
            quarantine_dir=quarantined,
        ) from exc

    return AttemptOutcome(
        job_id=safe_job_id,
        attempt_token=attempt_token,
        status="success",
        attempt_dir=canonical,
        canonical_dir=canonical,
        exit_code=exit_code,
        published=True,
    )


def acquire_batch_lease(
    root: str | Path,
    *,
    lease_name: str = "batch",
    stale_after_seconds: float | None = None,
) -> BatchLease:
    """Acquire an exclusive batch lease.

    Existing ownership always conflicts. ``stale_after_seconds`` is retained
    only as a fail-closed compatibility parameter and every non-``None`` value
    is rejected before filesystem access. Elapsed age alone cannot distinguish
    a dead owner from a valid long-running batch; recovery requires a future
    heartbeat and process-liveness protocol. Every read/archive/create
    transition is protected by one stable OS-level lock.
    """
    safe_name = _validate_component(lease_name, what="lease_name")
    if stale_after_seconds is not None:
        raise ValueError(
            "time-only stale lease recovery is disabled: acquisition age "
            "cannot prove owner death; release the lease with its owner token "
            "or use a future heartbeat and process-liveness protocol"
        )
    lease_root = Path(root) / "leases"
    history_dir = lease_root / "history"
    lease_root.mkdir(parents=True, exist_ok=True)
    active = lease_root / f"{safe_name}.lease.json"
    guard = _lease_guard_path(active, safe_name)
    token = uuid.uuid4().hex

    def new_record() -> dict[str, Any]:
        return {
            "schema_version": SUPERVISOR_SCHEMA_VERSION,
            "lease_name": safe_name,
            "pid": os.getpid(),
            "token": token,
            "timestamp": time.time(),
            "timestamp_utc": _utc_now(),
        }

    with _lease_transition_lock(guard):
        try:
            _write_json_exclusive(active, new_record())
        except FileExistsError:
            try:
                existing = _read_json_object(active)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise LeaseConflictError(
                    f"active lease {active} is unreadable; refusing recovery"
                ) from exc
            owner = existing.get("token")
            pid = existing.get("pid")
            raise LeaseConflictError(
                f"batch lease {safe_name!r} is held by pid {pid!r}, token "
                f"{owner!r}"
            )

    return BatchLease(
        path=active,
        history_dir=history_dir,
        name=safe_name,
        token=token,
    )
