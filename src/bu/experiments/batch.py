"""Durable batch orchestration for unattended confirmatory runs (S§W6 Fri).

The scientific runner in :mod:`bu.experiments.confirmatory` deliberately owns
the rules for *one* fit.  This module owns the operational rules around many
fits: an immutable plan, append-only checkpoints, one directory per job,
failure isolation, resume, incremental result writes, and a mandatory sync
callback after every locally completed result.

There is no Kaggle API or shell command here.  Authentication and transport are
deployment concerns; accepting an arbitrary command would turn a scientific
runner into a command-execution surface.  The public ``run_synthetic_batch``
test harness requires a callable sync boundary, while the production launcher
uses the private fixed-executor hand-off only after its own validation and
lease.  ``sync_to_directory`` is the concrete mounted-directory adapter.

Nothing in this module launches work at import time.  In particular, defining
the registered Experiment-1 plan is not evidence that Experiment 1 ran.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import constants as K
from ..config import Arm, Config, UnitSpec
from ..durable import (
    DivergentTargetError,
    DurabilityError,
    append_jsonl,
    atomic_write_json,
    read_jsonl,
    recover_unterminated_jsonl,
)
from .fit_evidence import (
    FIT_EVIDENCE_FILE,
    FIT_EVIDENCE_SCHEMA_VERSION,
    load_fit_evidence,
    run_confirmatory_fit,
)
from .supervisor import run_isolated_attempt
from .enumerate_units import design_units, execution_plan


BATCH_SCHEMA_VERSION = 2
SYNC_RECEIPT_SCHEMA_VERSION = 2
MANIFEST_FILE = "batch_manifest.json"
EVENTS_FILE = "batch_events.jsonl"
RESULT_FILE = "job_result.json"


@dataclass(frozen=True)
class BatchJob:
    """One isolated registered run in a batch."""

    unit: UnitSpec
    stage: str
    seed: int
    arm: str = "baseline"
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Only the exact default empty tuple means "this stage only".  Falsy
        # substitutes such as [] must not slip past the public type boundary.
        roles = (self.stage,) if self.roles == () else self.roles
        if (
            not isinstance(roles, tuple)
            or not roles
            or any(type(role) is not str for role in roles)
            or len(set(roles)) != len(roles)
            or tuple(sorted(roles)) != roles
            or self.stage not in roles
        ):
            raise ValueError(
                f"roles must be a sorted unique nonempty tuple containing the "
                f"execution stage {self.stage!r}, got {roles!r}"
            )
        object.__setattr__(self, "roles", roles)
        # Config performs the authoritative stage/arm/applicability checks for
        # every obligation this one computation discharges.
        for role in roles:
            Config(unit=self.unit, arm=Arm(self.arm), stage=role, seed=self.seed)

    @property
    def config(self) -> Config:
        return Config(
            unit=self.unit, arm=Arm(self.arm), stage=self.stage, seed=self.seed
        )

    @property
    def job_id(self) -> str:
        # A batch schedules computations. Several run/role identities can be
        # discharged by one fit (D-033), so using run_id here would double-run
        # shared exp1/repair_validation fits.
        return self.config.fit_id

    def as_record(self) -> dict[str, Any]:
        cfg = self.config
        return {
            "job_id": self.job_id,
            "run_id": cfg.run_id,
            "config_id": cfg.config_id,
            "unit_id": cfg.unit_id,
            "fit_id": cfg.fit_id,
            "stage": self.stage,
            "seed": self.seed,
            "arm": self.arm,
            "roles": list(self.roles),
            "config": cfg.to_dict(),
        }


@dataclass(frozen=True)
class BatchReport:
    batch_id: str
    total: int
    executed: int
    resumed: int
    synced: int
    failed: int
    sync_failed: int

    @property
    def complete(self) -> bool:
        """True only when every registered job has a durable sync receipt."""
        return self.synced == self.total and self.failed == self.sync_failed == 0


@dataclass(frozen=True)
class SyncReceipt:
    """A transport attestation bound to the exact local job evidence."""

    destination: str
    job_id: str
    result_digest: str
    job_tree_digest: str
    copy_evidence_digest: str
    schema_version: int = SYNC_RECEIPT_SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "destination": self.destination,
            "job_id": self.job_id,
            "result_digest": self.result_digest,
            "job_tree_digest": self.job_tree_digest,
            "copy_evidence_digest": self.copy_evidence_digest,
        }


SyncCallback = Callable[[Path, BatchJob, Mapping[str, Any]], SyncReceipt]
Executor = Callable[[BatchJob, Path], Mapping[str, Any]]


def _execute_in_spawned_child(
    attempt_dir: Path,
    payload: tuple[Executor, BatchJob],
) -> Mapping[str, Any]:
    """Picklable bridge from the generic supervisor to a batch executor."""
    executor, job = payload
    return executor(job, attempt_dir)


def experiment_1_jobs() -> tuple[BatchJob, ...]:
    """The registered 6×5×5 plan, deduplicated at the computation identity.

    Thirty jobs also discharge ``repair_validation``. They remain one job with
    two roles; the default executor refuses the launch until it can write both
    obligation records from that one fit.
    """

    jobs = tuple(
        BatchJob(
            unit=fit.unit,
            stage="exp1",
            seed=K.CONFIRMATORY_SEED_BASE + fit.seed,
            arm=fit.arm,
            roles=fit.roles,
        )
        for fit in execution_plan(design_units())
        if "exp1" in fit.roles
    )
    if len(jobs) != 6 * 5 * 5 or len({job.job_id for job in jobs}) != len(jobs):
        raise RuntimeError(
            "Experiment-1 batch is not the registered 6×5×5 unique-run plan"
        )
    return jobs


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _manifest(jobs: Sequence[BatchJob]) -> dict[str, Any]:
    if not jobs:
        raise ValueError("a batch must contain at least one job")
    if any(type(job) is not BatchJob for job in jobs):
        raise ValueError("every batch entry must be an exact BatchJob")
    records = [job.as_record() for job in jobs]
    ids = [record["job_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("batch contains duplicate job identities")
    payload = {"schema_version": BATCH_SCHEMA_VERSION, "jobs": records}
    batch_id = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return {"batch_id": batch_id, **payload}


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    try:
        atomic_write_json(path, dict(value))
    except DivergentTargetError as exc:
        raise ValueError(
            f"{path} already exists with different content; refusing to "
            "overwrite evidence from another job or plan"
        ) from exc


_ALLOWED_TRANSITIONS = {
    None: {"started"},
    "started": {"completed", "failed"},
    "completed": {"synced", "sync_failed"},
    "failed": {"started", "failed"},
    "sync_failed": {"synced", "sync_failed"},
    # A resume may name a newly approved durable destination.  Its receipt is
    # another append-only attestation, not a mutation of the first one.
    "synced": {"synced"},
}


def _append_event(path: Path, event: Mapping[str, Any]) -> None:
    append_jsonl(path, event)


def _append_transition(
    path: Path,
    latest: dict[str, dict[str, Any]],
    event: dict[str, Any],
) -> None:
    """Validate, append, and expose one state transition atomically to this run."""
    job_id = event["job_id"]
    prior = latest.get(job_id)
    prior_status = None if prior is None else prior["status"]
    if event["status"] not in _ALLOWED_TRANSITIONS[prior_status]:
        raise ValueError(
            f"refusing illegal live transition {prior_status!r} -> "
            f"{event['status']!r} for {job_id}"
        )
    _append_event(path, event)
    latest[job_id] = event


def _events(path: Path, known: set[str]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    result_digests: dict[str, str] = {}
    if not path.exists():
        return latest
    try:
        rows = read_jsonl(path)
    except DurabilityError as exc:
        raise ValueError(f"malformed batch event journal: {exc}") from exc
    for line_no, event in enumerate(rows, 1):
        if event.get("schema_version") != BATCH_SCHEMA_VERSION:
            raise ValueError(f"batch event line {line_no} has the wrong schema")
        job_id = event.get("job_id")
        if job_id not in known:
            raise ValueError(
                f"batch event line {line_no} names unknown job {job_id!r}"
            )
        if event.get("status") not in {
            "started", "completed", "failed", "synced", "sync_failed"
        }:
            raise ValueError(f"batch event line {line_no} has unknown status")
        prior = latest.get(job_id)
        prior_status = None if prior is None else prior["status"]
        if event["status"] not in _ALLOWED_TRANSITIONS[prior_status]:
            raise ValueError(
                f"batch event line {line_no} makes illegal transition "
                f"{None if prior is None else prior['status']!r} -> "
                f"{event['status']!r} for {job_id}"
            )
        digest = event.get("result_digest")
        if event["status"] in {"completed", "synced", "sync_failed"}:
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)
            ):
                raise ValueError(
                    f"batch event line {line_no} has no exact result digest"
                )
            if job_id in result_digests and result_digests[job_id] != digest:
                raise ValueError(
                    f"batch events disagree on the completed result for {job_id}"
                )
            result_digests[job_id] = digest
        if event["status"] == "synced":
            receipt = event.get("sync_receipt")
            if not isinstance(receipt, dict):
                raise ValueError(
                    f"batch event line {line_no} has no sync receipt"
                )
            if (
                receipt.get("schema_version") != SYNC_RECEIPT_SCHEMA_VERSION
                or receipt.get("job_id") != job_id
                or receipt.get("result_digest") != digest
                or not _is_sha256(receipt.get("job_tree_digest"))
                or not _is_sha256(receipt.get("copy_evidence_digest"))
            ):
                raise ValueError(
                    f"batch event line {line_no} has an inconsistent sync receipt"
                )
        latest[job_id] = event
    return latest


def _event(job: BatchJob, status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "job_id": job.job_id,
        "status": status,
        **extra,
    }


def _result_digest(result: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(result).encode("utf-8")).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _lstat_regular_file(path: Path) -> os.stat_result:
    """Return immutable-file metadata without following mutable links."""
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect durable evidence file {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"durable evidence path is a symbolic link: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"durable evidence path is not a regular file: {path}")
    if metadata.st_nlink != 1:
        raise ValueError(f"durable evidence path is hard-linked: {path}")
    return metadata


def _require_plain_directory_components(path: Path) -> None:
    """Reject an existing path reached through any symbolic-link component."""
    absolute = Path(os.path.abspath(path))
    components = (absolute, *absolute.parents)
    for component in reversed(components):
        if not os.path.lexists(component):
            continue
        metadata = component.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(
                f"durable sync destination contains a symbolic-link component: "
                f"{component}"
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(
                f"durable sync destination component is not a directory: "
                f"{component}"
            )


def _regular_tree_inventory(root: Path) -> list[dict[str, Any]]:
    """Inventory a plain directory tree, rejecting links and special files."""
    try:
        root_metadata = root.lstat()
    except OSError as exc:
        raise ValueError(f"job evidence directory cannot be inspected: {root}: {exc}") from exc
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError(f"job evidence root is not a plain directory: {root}")

    inventory: list[dict[str, Any]] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in directory_names:
            child = current_path / name
            metadata = child.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(
                    f"job evidence contains a linked or special directory: {child}"
                )
        for name in file_names:
            child = current_path / name
            metadata = _lstat_regular_file(child)
            inventory.append(
                {
                    "path": child.relative_to(root).as_posix(),
                    "size": metadata.st_size,
                    "sha256": hashlib.sha256(child.read_bytes()).hexdigest(),
                    "device": metadata.st_dev,
                    "inode": metadata.st_ino,
                }
            )
    if not inventory:
        raise ValueError(f"job evidence directory is empty: {root}")
    return sorted(inventory, key=lambda row: row["path"])


def _content_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {name: row[name] for name in ("path", "size", "sha256")}
        for row in _regular_tree_inventory(root)
    ]


def _job_tree_digest(job_dir: Path) -> str:
    """Hash every regular file in one link-free published job tree."""
    return hashlib.sha256(
        _canonical_json(_content_inventory(job_dir)).encode("utf-8")
    ).hexdigest()


def _copy_evidence_digest(source: Path, destination: Path) -> str:
    """Prove equal bytes were materialised as independent filesystem objects."""
    source_rows = _regular_tree_inventory(source)
    destination_rows = _regular_tree_inventory(destination)
    source_content = [
        {name: row[name] for name in ("path", "size", "sha256")}
        for row in source_rows
    ]
    destination_content = [
        {name: row[name] for name in ("path", "size", "sha256")}
        for row in destination_rows
    ]
    if source_content != destination_content:
        raise ValueError(
            "durable sync destination does not contain the complete local job tree"
        )
    evidence: list[dict[str, Any]] = []
    for source_row, destination_row in zip(source_rows, destination_rows, strict=True):
        source_file = source / source_row["path"]
        destination_file = destination / destination_row["path"]
        try:
            same_object = os.path.samefile(source_file, destination_file)
        except OSError as exc:
            raise ValueError(
                f"cannot compare source and destination evidence objects: {exc}"
            ) from exc
        if same_object:
            raise ValueError(
                f"durable sync destination aliases the local evidence file: "
                f"{destination_file}"
            )
        evidence.append(
            {
                "path": source_row["path"],
                "source_device": source_row["device"],
                "source_inode": source_row["inode"],
                "destination_device": destination_row["device"],
                "destination_inode": destination_row["inode"],
                "sha256": source_row["sha256"],
            }
        )
    return hashlib.sha256(_canonical_json(evidence).encode("utf-8")).hexdigest()


def _validate_sync_receipt(
    receipt: object,
    *,
    batch_dir: Path,
    job: BatchJob,
    result: Mapping[str, Any],
) -> SyncReceipt:
    if type(receipt) is not SyncReceipt:
        raise ValueError(
            "sync callback must return an exact SyncReceipt; returning None or "
            "merely not raising does not prove evidence was copied off-worker"
        )
    expected_result = _result_digest(result)
    source_job = batch_dir / "jobs" / job.job_id
    expected_tree = _job_tree_digest(source_job)
    if receipt.schema_version != SYNC_RECEIPT_SCHEMA_VERSION:
        raise ValueError("sync receipt has the wrong schema version")
    if type(receipt.destination) is not str or not receipt.destination.strip():
        raise ValueError("sync receipt has no durable destination identity")
    if receipt.job_id != job.job_id:
        raise ValueError("sync receipt names a different job identity")
    if receipt.result_digest != expected_result:
        raise ValueError("sync receipt is not bound to the completed result digest")
    if receipt.job_tree_digest != expected_tree:
        raise ValueError("sync receipt is not bound to the complete job tree digest")
    if not _is_sha256(receipt.copy_evidence_digest):
        raise ValueError("sync receipt has no independent-copy evidence digest")
    raw_destination = Path(receipt.destination)
    try:
        _require_plain_directory_components(raw_destination)
        destination = Path(os.path.abspath(raw_destination))
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            f"sync receipt destination cannot be read back: {exc}"
        ) from exc
    local_batch = batch_dir.resolve()
    if destination == local_batch or local_batch in destination.parents:
        raise ValueError(
            "sync receipt points inside the local batch tree; sync-off requires "
            "an independently mounted destination"
        )
    if _job_tree_digest(destination) != expected_tree:
        raise ValueError("sync receipt destination does not contain the complete local job tree")
    expected_copy_evidence = _copy_evidence_digest(source_job, destination)
    if receipt.copy_evidence_digest != expected_copy_evidence:
        raise ValueError(
            "sync receipt is not bound to independently materialised destination files"
        )
    return receipt


def _default_executor(job: BatchJob, job_dir: Path) -> Mapping[str, Any]:
    result = run_confirmatory_fit(
        job.unit,
        seed=job.seed,
        arm=job.arm,
        out_dir=job_dir,
    )
    row = result.as_row()
    return row


def _validate_result(job: BatchJob, result: object) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise ValueError(
            f"executor for {job.job_id} returned {type(result).__name__}, not a mapping"
        )
    out = dict(result)
    for name, expected in (
        ("run_id", job.config.run_id),
        ("config_id", job.config.config_id),
        ("unit_id", job.config.unit_id),
        ("fit_id", job.config.fit_id),
        ("stage", job.stage),
        ("seed", job.seed),
        ("arm", job.arm),
        ("fit_roles", list(job.roles)),
        ("role_run_ids", {
            role: Config(
                unit=job.unit, arm=Arm(job.arm), stage=role, seed=job.seed
            ).run_id
            for role in job.roles
        }),
    ):
        if out.get(name) != expected:
            raise ValueError(
                f"executor result for {job.job_id} has {name}={out.get(name)!r}; "
                f"expected {expected!r}"
            )
    # Prove serialisability before an event claims completion.
    _canonical_json(out)
    return out


def _validate_fit_evidence(job: BatchJob, job_dir: Path, result: Mapping[str, Any]) -> None:
    if result.get("fit_evidence_schema_version") != FIT_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("default executor result has no fit-evidence schema")
    if result.get("fit_evidence_file") != FIT_EVIDENCE_FILE:
        raise ValueError("default executor result names a noncanonical fit-evidence file")
    verified = load_fit_evidence(job_dir)
    if verified.fit_id != job.job_id or verified.roles != job.roles:
        raise ValueError("fit evidence disagrees with the batch job identity or roles")
    if result.get("fit_evidence_digest") != verified.execution_digest:
        raise ValueError("job result is not bound to its fit-evidence execution digest")


def _recover_result(
    job: BatchJob,
    job_dir: Path,
    *,
    require_fit_evidence: bool = False,
) -> dict[str, Any] | None:
    result_path = job_dir / RESULT_FILE
    if result_path.exists():
        result = _validate_result(
            job, json.loads(result_path.read_text(encoding="utf-8"))
        )
        if require_fit_evidence:
            _validate_fit_evidence(job, job_dir, result)
        return result
    if require_fit_evidence and (job_dir / FIT_EVIDENCE_FILE).exists():
        verified = load_fit_evidence(job_dir)
        confirmatory_path = (
            job_dir / verified.execution_run_id / "confirmatory.json"
        )
        if not confirmatory_path.is_file():
            raise ValueError(
                f"fit evidence for {job.job_id} has no physical confirmatory record"
            )
        result = json.loads(confirmatory_path.read_text(encoding="utf-8"))
        result.update(
            {
                "fit_evidence_schema_version": FIT_EVIDENCE_SCHEMA_VERSION,
                "fit_evidence_file": FIT_EVIDENCE_FILE,
                "fit_evidence_digest": verified.execution_digest,
            }
        )
        result = _validate_result(job, result)
        _validate_fit_evidence(job, job_dir, result)
        _write_json_exclusive(result_path, result)
        return result
    confirmatory = job_dir / job.config.run_id / "confirmatory.json"
    if confirmatory.exists():
        if require_fit_evidence:
            raise ValueError(
                f"job {job.job_id} reached confirmatory.json but has no verified "
                f"{FIT_EVIDENCE_FILE}; this is partial evidence and may not be "
                "recovered or synced as a completed fit"
            )
        result = _validate_result(
            job, json.loads(confirmatory.read_text(encoding="utf-8"))
        )
        _write_json_exclusive(result_path, result)
        return result
    partial = job_dir / job.config.run_id
    if partial.exists():
        raise ValueError(
            f"job {job.job_id} has a partial immutable run directory but no "
            "recoverable confirmatory.json. Refusing to overwrite or pretend the "
            "fit completed; inspect and quarantine that directory before resuming"
        )
    return None


def _run_batch(
    jobs: Sequence[BatchJob],
    *,
    root: str | Path,
    sync: SyncCallback,
    executor: Executor,
    require_fit_evidence: bool,
    attempt_timeout_seconds: float | None = None,
    attempt_staging_root: str | Path | None = None,
) -> BatchReport:
    """Internal common engine for registered and explicitly synthetic batches.

    ``sync`` is mandatory.  A caller cannot accidentally start an unattended
    batch whose only copy lives on an ephemeral worker.  When
    ``attempt_timeout_seconds`` is supplied, each executor call runs in a fresh
    spawned process and is published from staging only after success.
    Exceptions from one executor or sync call are recorded and the next job
    still runs.
    """

    if not callable(sync):
        raise ValueError("sync must be a callable; unattended runs require sync-off")
    if not callable(executor):
        raise ValueError("executor must be callable")
    if attempt_staging_root is not None and attempt_timeout_seconds is None:
        raise ValueError(
            "attempt_staging_root requires process isolation with a positive "
            "attempt_timeout_seconds"
        )
    try:
        job_tuple = tuple(jobs)
    except TypeError as exc:
        raise ValueError("jobs must be an iterable of exact BatchJob records") from exc
    # Validate the public boundary before reading attributes below.
    manifest = _manifest(job_tuple)
    batch_dir = Path(root) / manifest["batch_id"]
    batch_dir.mkdir(parents=True, exist_ok=True)
    _write_json_exclusive(batch_dir / MANIFEST_FILE, manifest)
    events_path = batch_dir / EVENTS_FILE
    events_path.touch(exist_ok=True)
    recover_unterminated_jsonl(
        events_path,
        evidence_dir=batch_dir / "journal_recovery",
    )
    by_id = {job.job_id: job for job in job_tuple}
    latest = _events(events_path, set(by_id))

    executed = resumed = synced = failed = sync_failed = 0
    for job in job_tuple:
        job_dir = batch_dir / "jobs" / job.job_id
        state = latest.get(job.job_id)
        if state and state["status"] == "synced":
            result = _recover_result(
                job,
                job_dir,
                require_fit_evidence=require_fit_evidence,
            )
            if result is None:
                raise ValueError(
                    f"synced job {job.job_id} has no recoverable local result"
                )
            digest = _result_digest(result)
            if state.get("result_digest") != digest:
                raise ValueError(
                    f"synced job {job.job_id} no longer matches its result digest"
                )
            # Always re-attest against the destination supplied by this call.
            # A prior receipt may name a different mounted store; treating that
            # as sufficient would let a resume report complete while the
            # currently approved destination contains nothing.
            receipt = _validate_sync_receipt(
                sync(batch_dir, job, result),
                batch_dir=batch_dir,
                job=job,
                result=result,
            )
            prior_receipt = state.get("sync_receipt")
            if prior_receipt != receipt.as_record():
                _append_transition(
                    events_path,
                    latest,
                    _event(
                        job,
                        "synced",
                        result_digest=digest,
                        sync_receipt=receipt.as_record(),
                        re_attestation=True,
                    ),
                )
                final_receipt = _validate_sync_receipt(
                    sync(batch_dir, job, result),
                    batch_dir=batch_dir,
                    job=job,
                    result=result,
                )
                if final_receipt != receipt:
                    raise ValueError(
                        f"sync receipt for {job.job_id} changed while persisting "
                        "the destination re-attestation"
                    )
            resumed += 1
            synced += 1
            continue

        try:
            result = _recover_result(
                job,
                job_dir,
                require_fit_evidence=require_fit_evidence,
            )
        except Exception as exc:
            # A completed/sync-failed checkpoint must never be downgraded to a
            # generic fit failure.  Its result is evidence and corruption is a
            # batch-level refusal, not a retryable condition.
            if state and state["status"] in {"completed", "sync_failed"}:
                raise ValueError(
                    f"checkpointed result for {job.job_id} cannot be recovered: {exc}"
                ) from exc
            _append_transition(
                events_path, latest,
                _event(job, "failed", error_type=type(exc).__name__, error=str(exc)),
            )
            failed += 1
            continue

        if result is not None:
            digest = _result_digest(result)
            if state is None:
                raise ValueError(
                    f"job {job.job_id} has a result but no append-only start "
                    "checkpoint; refusing unbound evidence"
                )
            if state["status"] in {"completed", "sync_failed"}:
                if state.get("result_digest") != digest:
                    raise ValueError(
                        f"recovered job_result.json for {job.job_id} disagrees "
                        "with the append-only checkpoint digest"
                    )
            elif state["status"] == "started":
                # Crash window: the immutable result reached disk before the
                # completed event.  Bind that exact result now; never refit it.
                _append_transition(
                    events_path, latest,
                    _event(
                        job, "completed", result=result,
                        result_digest=digest, recovered_after_interruption=True,
                    ),
                )
            elif state["status"] == "failed":
                # A valid result may have become durable just before an error was
                # recorded.  Open a fresh recovery attempt, then bind the bytes.
                _append_transition(
                    events_path, latest,
                    _event(job, "started", recovery=True),
                )
                _append_transition(
                    events_path, latest,
                    _event(
                        job, "completed", result=result,
                        result_digest=digest, recovered_after_failure=True,
                    ),
                )

        if result is None:
            if state and state["status"] == "started":
                # The prior process stopped before a result or immutable run
                # directory existed.  Close that incomplete attempt before a
                # new one starts so the event sequence remains auditable.
                _append_transition(
                    events_path, latest,
                    _event(
                        job, "failed", error_type="InterruptedRun",
                        error="prior started checkpoint had no recoverable result",
                    ),
                )
            _append_transition(events_path, latest, _event(job, "started"))
            try:
                if attempt_timeout_seconds is None:
                    job_dir.mkdir(parents=True, exist_ok=True)
                    raw_result = executor(job, job_dir)
                else:
                    outcome = run_isolated_attempt(
                        _execute_in_spawned_child,
                        root=batch_dir,
                        staging_root=(
                            None
                            if attempt_staging_root is None
                            else Path(attempt_staging_root) / manifest["batch_id"]
                        ),
                        job_id=job.job_id,
                        payload=(executor, job),
                        timeout_seconds=attempt_timeout_seconds,
                    )
                    if not outcome.succeeded:
                        raise RuntimeError(
                            f"isolated attempt {outcome.attempt_token} ended as "
                            f"{outcome.status}: {outcome.error_type}: "
                            f"{outcome.error}"
                        )
                    raw_result = json.loads(
                        (job_dir / RESULT_FILE).read_text(encoding="utf-8")
                    )
                result = _validate_result(job, raw_result)
                if require_fit_evidence:
                    _validate_fit_evidence(job, job_dir, result)
                _write_json_exclusive(job_dir / RESULT_FILE, result)
                digest = _result_digest(result)
                _append_transition(
                    events_path, latest,
                    _event(job, "completed", result=result, result_digest=digest),
                )
                executed += 1
            except Exception as exc:
                _append_transition(
                    events_path, latest,
                    _event(
                        job, "failed", error_type=type(exc).__name__, error=str(exc)
                    ),
                )
                failed += 1
                continue
        else:
            resumed += 1

        digest = _result_digest(result)

        try:
            receipt = _validate_sync_receipt(
                sync(batch_dir, job, result),
                batch_dir=batch_dir,
                job=job,
                result=result,
            )
        except Exception as exc:
            _append_transition(
                events_path, latest,
                _event(
                    job,
                    "sync_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                    result_digest=digest,
                ),
            )
            sync_failed += 1
            continue

        _append_transition(
            events_path,
            latest,
            _event(
                job,
                "synced",
                result_digest=digest,
                sync_receipt=receipt.as_record(),
            ),
        )
        # The first transport necessarily precedes the local acknowledgement.
        # Repeat it after the append so a mounted durable destination receives
        # the terminal journal row as well as the evidence tree.  Failure here
        # is a batch-level interruption: the synced state will force this exact
        # read-back operation again on resume before completion is reported.
        final_receipt = _validate_sync_receipt(
            sync(batch_dir, job, result),
            batch_dir=batch_dir,
            job=job,
            result=result,
        )
        if final_receipt != receipt:
            raise ValueError(
                f"sync receipt for {job.job_id} changed while finalising the "
                "remote event journal"
            )
        synced += 1

    return BatchReport(
        batch_id=manifest["batch_id"],
        total=len(job_tuple),
        executed=executed,
        resumed=resumed,
        synced=synced,
        failed=failed,
        sync_failed=sync_failed,
    )


def _run_registered_batch(
    jobs: Sequence[BatchJob],
    *,
    root: str | Path,
    sync: SyncCallback,
    attempt_timeout_seconds: float | None = None,
    attempt_staging_root: str | Path | None = None,
) -> BatchReport:
    """Private launch hand-off for the exact registered production batch.

    The public batch surface intentionally has no production launcher or
    importable authorization token.  ``bu.experiments.launch`` calls this only
    after it has revalidated preflight state and acquired the batch lease.
    Executor injection is absent by construction.
    """

    if (
        attempt_timeout_seconds is None
        or attempt_staging_root is None
    ):
        raise ValueError(
            "the private registered batch hand-off requires mandatory "
            "fresh-process timeout and separate staging"
        )
    job_tuple = tuple(jobs)
    if job_tuple != experiment_1_jobs():
        raise ValueError(
            "the private registered batch hand-off requires the exact "
            "Experiment-1 plan"
        )
    return _run_batch(
        job_tuple,
        root=root,
        sync=sync,
        executor=_default_executor,
        require_fit_evidence=True,
        attempt_timeout_seconds=attempt_timeout_seconds,
        attempt_staging_root=attempt_staging_root,
    )


def run_synthetic_batch(
    jobs: Sequence[BatchJob],
    *,
    root: str | Path,
    sync: SyncCallback,
    executor: Executor,
    attempt_timeout_seconds: float | None = None,
    attempt_staging_root: str | Path | None = None,
) -> BatchReport:
    """Run synthetic test jobs without access to the production executor path."""

    if not callable(executor):
        raise ValueError("executor must be callable")
    if executor is _default_executor:
        raise ValueError(
            "the registered executor cannot be selected through the synthetic API"
        )
    return _run_batch(
        jobs,
        root=root,
        sync=sync,
        executor=executor,
        require_fit_evidence=False,
        attempt_timeout_seconds=attempt_timeout_seconds,
        attempt_staging_root=attempt_staging_root,
    )


def sync_to_directory(destination: str | Path) -> SyncCallback:
    """Return a sync adapter for a durable mounted output directory."""

    target_root = Path(destination)

    def copy_static(source: Path, target: Path) -> None:
        """Create an immutable remote file or prove the existing bytes agree."""
        _lstat_regular_file(source)
        _require_plain_directory_components(target.parent)
        if os.path.lexists(target):
            _lstat_regular_file(target)
            if os.path.samefile(source, target):
                raise ValueError(
                    f"durable sync target aliases its local source: {target}"
                )
            if source.read_bytes() != target.read_bytes():
                raise ValueError(
                    f"durable sync target {target} already exists with different "
                    "bytes; refusing to overwrite batch identity evidence"
                )
            return
        shutil.copy2(source, target)
        _lstat_regular_file(target)
        if os.path.samefile(source, target):
            raise ValueError(f"durable sync target aliases its local source: {target}")

    def extend_events(source: Path, target: Path) -> None:
        """Extend only an exact prefix of the append-only event stream."""
        _lstat_regular_file(source)
        _require_plain_directory_components(target.parent)
        source_bytes = source.read_bytes()
        if os.path.lexists(target):
            _lstat_regular_file(target)
            if os.path.samefile(source, target):
                raise ValueError(
                    f"durable event log aliases its local source: {target}"
                )
            target_bytes = target.read_bytes()
            if not source_bytes.startswith(target_bytes):
                raise ValueError(
                    f"durable event log {target} is not an exact prefix of the "
                    "local append-only stream; refusing to overwrite either history"
                )
            if source_bytes == target_bytes:
                return
        shutil.copy2(source, target)
        _lstat_regular_file(target)
        if os.path.samefile(source, target):
            raise ValueError(f"durable event log aliases its local source: {target}")

    def sync(
        batch_dir: Path, job: BatchJob, result: Mapping[str, Any]
    ) -> SyncReceipt:
        _require_plain_directory_components(target_root)
        target = target_root / batch_dir.name
        target.mkdir(parents=True, exist_ok=True)
        _require_plain_directory_components(target)
        source_job = batch_dir / "jobs" / job.job_id
        _regular_tree_inventory(source_job)
        target_job = target / "jobs" / job.job_id
        if os.path.lexists(target_job):
            _copy_evidence_digest(source_job, target_job)
        else:
            target_job.parent.mkdir(parents=True, exist_ok=True)
            _require_plain_directory_components(target_job.parent)
            temporary = target_job.with_name(f".{target_job.name}.partial")
            if os.path.lexists(temporary):
                raise ValueError(
                    f"durable sync temporary {temporary} already exists; inspect "
                    "and quarantine it before retrying"
                )
            shutil.copytree(source_job, temporary)
            _copy_evidence_digest(source_job, temporary)
            os.replace(temporary, target_job)
        copy_evidence = _copy_evidence_digest(source_job, target_job)
        copy_static(batch_dir / MANIFEST_FILE, target / MANIFEST_FILE)
        extend_events(batch_dir / EVENTS_FILE, target / EVENTS_FILE)
        return SyncReceipt(
            destination=str(target_job.resolve()),
            job_id=job.job_id,
            result_digest=_result_digest(result),
            job_tree_digest=_job_tree_digest(source_job),
            copy_evidence_digest=copy_evidence,
        )

    return sync
