"""Durable batch orchestration for unattended confirmatory runs (S§W6 Fri).

The scientific runner in :mod:`bu.experiments.confirmatory` deliberately owns
the rules for *one* fit.  This module owns the operational rules around many
fits: an immutable plan, append-only checkpoints, one directory per job,
failure isolation, resume, incremental result writes, and a mandatory sync
callback after every locally completed result.

There is no Kaggle API or shell command here.  Authentication and transport are
deployment concerns; accepting an arbitrary command would turn a scientific
runner into a command-execution surface.  ``run_batch`` instead requires a
callable sync boundary.  ``sync_to_directory`` is the concrete adapter for a
mounted Kaggle output/dataset directory and is exercised without a network.

Nothing in this module launches work at import time.  In particular, defining
the registered Experiment-1 plan is not evidence that Experiment 1 ran.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import constants as K
from ..config import Arm, Config, UnitSpec
from .confirmatory import run_confirmatory
from .enumerate_units import design_units, execution_plan


BATCH_SCHEMA_VERSION = 1
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


SyncCallback = Callable[[Path, BatchJob, Mapping[str, Any]], None]
Executor = Callable[[BatchJob, Path], Mapping[str, Any]]


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
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != dict(value):
            raise ValueError(
                f"{path} already exists with different content; refusing to "
                "overwrite evidence from another job or plan"
            )


_ALLOWED_TRANSITIONS = {
    None: {"started"},
    "started": {"completed", "failed"},
    "completed": {"synced", "sync_failed"},
    "failed": {"started", "failed"},
    "sync_failed": {"synced", "sync_failed"},
    "synced": set(),
}


def _append_event(path: Path, event: Mapping[str, Any]) -> None:
    line = _canonical_json(event) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


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
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed batch event at line {line_no}: {exc}") from exc
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


def _default_executor(job: BatchJob, job_dir: Path) -> Mapping[str, Any]:
    if len(job.roles) != 1:
        raise ValueError(
            f"fit {job.job_id} discharges roles {job.roles}, but the current "
            "confirmatory runner writes one obligation record at a time. "
            "Refusing to train it under one stage and duplicate the same fit "
            "later under another (D-033); a multi-role recorder requires Sol's "
            "ruling before launch"
        )
    result = run_confirmatory(
        job.unit,
        stage=job.stage,
        seed=job.seed,
        arm=job.arm,
        out_dir=job_dir,
    )
    row = result.as_row()
    row["fit_roles"] = list(job.roles)
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
    ):
        if out.get(name) != expected:
            raise ValueError(
                f"executor result for {job.job_id} has {name}={out.get(name)!r}; "
                f"expected {expected!r}"
            )
    # Prove serialisability before an event claims completion.
    _canonical_json(out)
    return out


def _recover_result(job: BatchJob, job_dir: Path) -> dict[str, Any] | None:
    result_path = job_dir / RESULT_FILE
    if result_path.exists():
        return _validate_result(job, json.loads(result_path.read_text(encoding="utf-8")))
    confirmatory = job_dir / job.config.run_id / "confirmatory.json"
    if confirmatory.exists():
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


def run_batch(
    jobs: Sequence[BatchJob],
    *,
    root: str | Path,
    sync: SyncCallback,
    executor: Executor = _default_executor,
) -> BatchReport:
    """Run or resume a batch, checkpointing and syncing each isolated job.

    ``sync`` is mandatory.  A caller cannot accidentally start an unattended
    batch whose only copy lives on an ephemeral worker.  Exceptions from one
    executor or sync call are recorded and the next job still runs.
    """

    if not callable(sync):
        raise ValueError("sync must be a callable; unattended runs require sync-off")
    if not callable(executor):
        raise ValueError("executor must be callable")
    try:
        job_tuple = tuple(jobs)
    except TypeError as exc:
        raise ValueError("jobs must be an iterable of exact BatchJob records") from exc
    # Validate the public boundary before reading attributes below.
    manifest = _manifest(job_tuple)
    shared = [job for job in job_tuple if len(job.roles) > 1]
    if executor is _default_executor and shared:
        raise ValueError(
            f"batch contains {len(shared)} multi-role fit(s), for example "
            f"{shared[0].job_id} with roles {shared[0].roles}. The default "
            "runner cannot yet write several obligation records from one fit; "
            "the whole launch is refused before any compute starts (D-033)"
        )
    batch_dir = Path(root) / manifest["batch_id"]
    batch_dir.mkdir(parents=True, exist_ok=True)
    _write_json_exclusive(batch_dir / MANIFEST_FILE, manifest)
    events_path = batch_dir / EVENTS_FILE
    events_path.touch(exist_ok=True)
    by_id = {job.job_id: job for job in job_tuple}
    latest = _events(events_path, set(by_id))

    executed = resumed = synced = failed = sync_failed = 0
    for job in job_tuple:
        job_dir = batch_dir / "jobs" / job.job_id
        state = latest.get(job.job_id)
        if state and state["status"] == "synced":
            resumed += 1
            synced += 1
            continue

        try:
            result = _recover_result(job, job_dir)
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
            job_dir.mkdir(parents=True, exist_ok=True)
            _append_transition(events_path, latest, _event(job, "started"))
            try:
                result = _validate_result(job, executor(job, job_dir))
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
            sync(batch_dir, job, result)
            _append_transition(
                events_path, latest, _event(job, "synced", result_digest=digest)
            )
            synced += 1
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

    return BatchReport(
        batch_id=manifest["batch_id"],
        total=len(job_tuple),
        executed=executed,
        resumed=resumed,
        synced=synced,
        failed=failed,
        sync_failed=sync_failed,
    )


def sync_to_directory(destination: str | Path) -> SyncCallback:
    """Return a sync adapter for a durable mounted output directory."""

    target_root = Path(destination)

    def copy_static(source: Path, target: Path) -> None:
        """Create an immutable remote file or prove the existing bytes agree."""
        if target.exists():
            if source.read_bytes() != target.read_bytes():
                raise ValueError(
                    f"durable sync target {target} already exists with different "
                    "bytes; refusing to overwrite batch identity evidence"
                )
            return
        shutil.copy2(source, target)

    def extend_events(source: Path, target: Path) -> None:
        """Extend only an exact prefix of the append-only event stream."""
        source_bytes = source.read_bytes()
        if target.exists():
            target_bytes = target.read_bytes()
            if not source_bytes.startswith(target_bytes):
                raise ValueError(
                    f"durable event log {target} is not an exact prefix of the "
                    "local append-only stream; refusing to overwrite either history"
                )
            if source_bytes == target_bytes:
                return
        shutil.copy2(source, target)

    def sync(batch_dir: Path, job: BatchJob, result: Mapping[str, Any]) -> None:
        del result  # the validated result already lives inside the job directory
        target = target_root / batch_dir.name
        target.mkdir(parents=True, exist_ok=True)
        source_job = batch_dir / "jobs" / job.job_id
        target_job = target / "jobs" / job.job_id
        if target_job.exists():
            source_files = {
                path.relative_to(source_job): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in source_job.rglob("*") if path.is_file()
            }
            target_files = {
                path.relative_to(target_job): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in target_job.rglob("*") if path.is_file()
            }
            if source_files != target_files:
                raise ValueError(
                    f"durable sync target {target_job} already exists with "
                    "different bytes; refusing to delete or overwrite evidence"
                )
        else:
            target_job.parent.mkdir(parents=True, exist_ok=True)
            temporary = target_job.with_name(f".{target_job.name}.partial")
            if temporary.exists():
                raise ValueError(
                    f"durable sync temporary {temporary} already exists; inspect "
                    "and quarantine it before retrying"
                )
            shutil.copytree(source_job, temporary)
            os.replace(temporary, target_job)
        copy_static(batch_dir / MANIFEST_FILE, target / MANIFEST_FILE)
        extend_events(batch_dir / EVENTS_FILE, target / EVENTS_FILE)

    return sync
