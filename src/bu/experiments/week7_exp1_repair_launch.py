"""Exact, project-local Experiment-1 repair launch and evidence-only recovery.

Only the 474 new physical jobs derived by week7_exp1_repairs are executable.
The 102 required historical baselines are reverified at preflight and final
completion, never copied into new job identities or retrained. Every attempt
uses the fixed private worker in a fresh process, a mandatory timeout and the
workspace-wide Week-7 lease. Failed/unknown attempts halt; there is no automatic
retry. Complete local jobs can be copied on resume without executing a model.

Events are numbered immutable JSON files with a hash chain, independently
published to the durable directory first. A crash between the two publications
is recovered by copying the one verified event, not by editing a journal tail.
Model result bytes retain the actual original launch start across new leases.

Readiness requires the two separate local timing schemas: all twelve exact
repair architecture/size cases and all six five-model baseline ensemble cases.
Historical W4 rates are not substituted. No benchmark or production fit is
launched merely by defining these adapters or loading their configuration.
"""

from __future__ import annotations

import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..durable import atomic_write_bytes, atomic_write_json, read_json, sha256_file
from . import batch as B
from . import launch as L
from . import preflight as P
from . import repair_label_preflight as RF
from . import repair_timing as RT
from . import week7_exp1_repairs as W
from .prefit_storage import check_preflight_storage
from .supervisor import AttemptOutcome, acquire_batch_lease, run_isolated_attempt


PREFLIGHT_SCHEMA_VERSION = 1
PREFLIGHT_FILE = "week7_exp1_repair_preflight.json"
EVENT_DIRECTORY = "week7_exp1_repair_events"
REPORT_DIRECTORY = "week7_exp1_repair_reports"
_EVENT_KINDS = {"attempt_started", "attempt_failed", "sync_pending", "job_synced", "complete"}


@dataclass(frozen=True)
class ValidatedExp1Preflight:
    report_path: Path
    report_sha256: str
    report: dict[str, Any]
    roots: dict[str, Path]
    git_commit: str


def _pinned_file(path, sha, commit):
    target = W._project_path(path, directory=False)
    expected_sha = L._lower_sha256(sha, what="independent timing SHA256")
    expected_commit = W.F._validate_expected_git_commit(commit)
    if sha256_file(target) != expected_sha:
        raise ValueError("timing file differs from its independently supplied SHA256")
    return target, {"path": str(target), "sha256": expected_sha,
                    "expected_git_commit": expected_commit}


def _repair_timing(path, sha, commit):
    target, pin = _pinned_file(path, sha, commit)
    try:
        record = RT.load_timing_record(target)
    except OSError as exc:
        raise ValueError(f"repair timing evidence is unavailable: {exc}") from exc
    inventory = RT.repair_inventory("e1_repairs")
    if len(inventory["groups"]) != 12 or inventory["model_fits"] != 384:
        raise ValueError("Experiment-1 repair timing must cover exactly 12 architecture/size groups and 384 models")
    projection = RT.project_repairs(inventory, record["benchmarks"], how="max")
    _timing_host_commit(record["benchmarks"], pin)
    return pin, projection


def _timing_host_commit(benchmarks, pin):
    for benchmark in benchmarks:
        before, after = benchmark["environment_before"], benchmark["environment_after"]
        if before["source_commit"] != pin["expected_git_commit"] or after != before:
            raise ValueError("timing differs from the independent timing execution commit")
        expected_host = {"platform": platform.platform(), "processor": platform.processor() or platform.machine(),
                         "python": platform.python_version(), "machine": platform.machine(),
                         "hostname": platform.node(), "logical_cpu_count": os.cpu_count()}
        W._equal({k: before[k] for k in expected_host}, expected_host, what="local timing host")


def _baseline_timing(path, sha, commit):
    """Use only the agreed six-case local, full-five-model baseline schema."""
    target, pin = _pinned_file(path, sha, commit)
    try:
        record = RT.load_baseline_timing_record(target)
    except OSError as exc:
        raise ValueError(f"baseline timing evidence is unavailable: {exc}") from exc
    inventory = RT.baseline_inventory()
    if (len(inventory["groups"]) != 6 or inventory["ensemble_jobs"] != 90
            or inventory["model_fits"] != 450 or inventory["collection_events"] != 90):
        raise ValueError("baseline timing must cover six groups, 90 ensembles, 450 models and 90 collections")
    projection = RT.project_baselines(inventory, record["benchmarks"], how="max")
    _timing_host_commit(record["benchmarks"], pin)
    return pin, projection


def _inputs(plan_path, ledger_path, repair_pin, baseline_pin):
    plan_file = W._project_path(plan_path, directory=False)
    ledger_file = W._project_path(ledger_path, directory=False)
    plan = W.load_exp1_repair_plan(plan_file)
    ledger = W.load_exp1_reuse_ledger(ledger_file)
    repair, projection = _repair_timing(repair_pin["path"], repair_pin["sha256"], repair_pin["expected_git_commit"])
    baseline, baseline_projection = _baseline_timing(
        baseline_pin["path"], baseline_pin["sha256"], baseline_pin["expected_git_commit"])
    inputs = {"plan": {"path": str(plan_file), "sha256": sha256_file(plan_file)},
              "reuse_ledger": {"path": str(ledger_file), "sha256": sha256_file(ledger_file)},
              "repair_timing": repair, "baseline_timing": baseline}
    budget = {"new_physical_fits": plan["counts"]["new_physical_fits"],
              "new_member_models": plan["counts"]["new_member_model_trainings"],
              "repairs": projection, "baselines": baseline_projection,
              "interpretation": "local measured estimates, not a runtime bound or GPU-hour gate"}
    return inputs, budget, plan, ledger


def _protect(roots, inputs):
    _check_lease_namespace()
    W._roots(roots["output"], roots["staging"], roots["sync"], inputs["reuse_ledger"]["path"])
    for root in roots.values():
        W._project_path(root, directory=True)
        for protected in (W.HISTORICAL_JOBS_ROOT, W.HISTORICAL_COPY_ROOT,
                          W.HISTORICAL_REPORT_PATH.parent, W.COMMON_LEASE_ROOT):
            if P._overlap(root, protected.resolve()):
                raise ValueError("preflight/execution root overlaps protected historical or common-lease evidence")
        for value in inputs.values():
            if Path(value["path"]).is_relative_to(root):
                raise ValueError("original plan, reuse and timing inputs must stay outside execution roots")


def _input_copies(roots, inputs, *, write):
    for key, source in inputs.items():
        path = Path(source["path"])
        for root in (roots["preflight"], roots["sync"]):
            destination = root / f"exp1_input_{key}.json"
            if write:
                RF.sync_immutable_file(path, destination)
            W._same_file_copy(path, destination)


def run_exp1_repair_preflight(
    *, plan_path, reuse_ledger_path, repair_timing_path, repair_timing_sha256,
    repair_timing_expected_git_commit, baseline_timing_path, baseline_timing_sha256,
    baseline_timing_expected_git_commit, expected_git_commit, preflight_dir,
    output_root, staging_root, sync_root, attempt_timeout_seconds,
    minimum_free_bytes, sync_destination_identity,
) -> dict[str, Any]:
    """Require exact sources, compatible measured timing, storage and real copy IO."""
    timeout = L._positive_number(attempt_timeout_seconds, what="attempt_timeout_seconds")
    environment = W._environment(expected_git_commit)
    inputs, budget, plan, _ = _inputs(plan_path, reuse_ledger_path,
        {"path": repair_timing_path, "sha256": repair_timing_sha256,
         "expected_git_commit": repair_timing_expected_git_commit},
        {"path": baseline_timing_path, "sha256": baseline_timing_sha256,
         "expected_git_commit": baseline_timing_expected_git_commit})
    for path in (preflight_dir, output_root, staging_root, sync_root):
        W._project_path(path, directory=True)
    roots, storage = P._verify_storage(preflight_dir=preflight_dir, output_root=output_root,
        staging_root=staging_root, sync_root=sync_root, minimum_free_bytes=minimum_free_bytes)
    _protect(roots, inputs)
    binding = W._seal({"inputs": inputs, "plan_digest": plan["plan_digest"],
                       "attempt_timeout_seconds": timeout}, "binding_sha256")["binding_sha256"]
    destination = P._validate_destination_identity(sync_destination_identity)
    canary, receipt = P._run_sync_canary(roots=roots, plan_digest=binding,
        destination_identity=destination, adapter=P.sync_canary_to_mounted_directory)
    W._same_file_copy(Path(canary["source_path"]), Path(canary["destination_path"]))
    _input_copies(roots, inputs, write=True)
    report = {"exp1_repair_preflight_schema_version": PREFLIGHT_SCHEMA_VERSION,
              "status": "ready", "launch_performed": False,
              "inputs": inputs, "budget": budget, "plan_digest": plan["plan_digest"],
              "binding_sha256": binding, "environment": environment, "storage": storage,
              "attempt_timeout_seconds": timeout, "common_control_root": str(W.COMMON_LEASE_ROOT.resolve()),
              "sync_canary": canary, "sync_receipt": receipt}
    path = atomic_write_json(roots["preflight"] / PREFLIGHT_FILE, report)
    RF.sync_immutable_file(path, roots["sync"] / PREFLIGHT_FILE)
    validate_exp1_repair_preflight(path, output_root=output_root, sync_root=sync_root,
                                   expected_git_commit=expected_git_commit)
    return report


def validate_exp1_repair_preflight(path, *, output_root, sync_root, expected_git_commit) -> ValidatedExp1Preflight:
    report_path = W._project_path(path, directory=False)
    if report_path.name != PREFLIGHT_FILE:
        raise ValueError("Experiment-1 repairs require their own canonical preflight file")
    raw = report_path.read_bytes()
    report = L._strict_keys(read_json(report_path), {
        "exp1_repair_preflight_schema_version", "status", "launch_performed", "inputs", "budget",
        "plan_digest", "binding_sha256", "environment", "storage", "attempt_timeout_seconds",
        "common_control_root", "sync_canary", "sync_receipt"}, what="Experiment-1 repair preflight")
    if raw != L._pretty_json_bytes(report):
        raise ValueError("preflight report is not canonical immutable JSON")
    if (type(report["exp1_repair_preflight_schema_version"]) is not int
            or report["exp1_repair_preflight_schema_version"] != PREFLIGHT_SCHEMA_VERSION
            or report["status"] != "ready" or report["launch_performed"] is not False):
        raise ValueError("Experiment-1 repair preflight is not ready")
    inputs = L._strict_keys(report["inputs"], {"plan", "reuse_ledger", "repair_timing", "baseline_timing"}, what="inputs")
    for name, row in inputs.items():
        L._strict_keys(row, {"path", "sha256"} | ({"expected_git_commit"} if "timing" in name else set()), what=name)
    current, budget, plan, _ = _inputs(inputs["plan"]["path"], inputs["reuse_ledger"]["path"],
                                     inputs["repair_timing"], inputs["baseline_timing"])
    timeout = L._positive_number(report["attempt_timeout_seconds"], what="attempt timeout")
    binding = W._seal({"inputs": current, "plan_digest": plan["plan_digest"],
                       "attempt_timeout_seconds": timeout}, "binding_sha256")["binding_sha256"]
    W._equal(inputs, current, what="all source/timing input pins")
    W._equal(report["budget"], budget, what="rederived timing budget")
    W._equal(report["environment"], W._environment(expected_git_commit), what="independent execution environment")
    if report["plan_digest"] != plan["plan_digest"] or report["binding_sha256"] != binding:
        raise ValueError("preflight plan/timing/source binding changed")
    if report["common_control_root"] != str(W.COMMON_LEASE_ROOT.resolve()):
        raise ValueError("preflight uses a different common Week-7 lease")
    roots = L._validate_storage(report["storage"], report_parent=report_path.parent,
        requested_output=W._project_path(output_root, directory=True),
        requested_sync=W._project_path(sync_root, directory=True))
    _protect(roots, inputs)
    L._validate_sync_evidence(report, roots=roots, plan_sha256=binding)
    W._same_file_copy(Path(report["sync_canary"]["source_path"]), Path(report["sync_canary"]["destination_path"]))
    _input_copies(roots, inputs, write=False)
    W._same_file_copy(report_path, roots["sync"] / PREFLIGHT_FILE)
    if report_path.read_bytes() != raw:
        raise ValueError("preflight changed during validation")
    return ValidatedExp1Preflight(report_path, sha256_file(report_path), report, roots, expected_git_commit)


def _event_directories(roots):
    return tuple(RF.ensure_regular_child_directory(roots[name], EVENT_DIRECTORY) for name in ("output", "sync"))


def _validate_event(row, *, index, previous, context_digest):
    fields = {"event_schema_version", "sequence", "previous_digest", "execution_context_digest",
              "kind", "job_id", "data", "event_digest"}
    L._strict_keys(row, fields, what="immutable repair event")
    if (type(row["event_schema_version"]) is not int or row["event_schema_version"] != 1
            or type(row["sequence"]) is not int or row["sequence"] != index
            or row["previous_digest"] != previous or row["execution_context_digest"] != context_digest
            or type(row["kind"]) is not str or row["kind"] not in _EVENT_KINDS
            or type(row["data"]) is not dict):
        raise ValueError("repair event sequence/context/schema is not exact")
    if row["kind"] == "complete":
        if row["job_id"] is not None:
            raise ValueError("completion event cannot name one job")
        W._equal(row["data"], {"synced_physical_fits": len(W.new_exp1_repair_jobs()),
                               "historical_sources_reverified": 102}, what="completion counts")
    else:
        W._new_job(row["job_id"])
        if row["kind"] == "attempt_started":
            L._strict_keys(row["data"], {"checkpoint_digest"}, what="attempt start")
            L._lower_sha256(row["data"]["checkpoint_digest"], what="attempt start checkpoint")
        elif row["kind"] == "job_synced":
            L._strict_keys(row["data"], {"execution_digest", "source_tree_digest", "copy_evidence_digest"}, what="sync result")
            for key, value in row["data"].items():
                L._lower_sha256(value, what=key)
        else:
            L._strict_keys(row["data"], {"type", "message"}, what="preserved failure")
            if any(type(value) is not str for value in row["data"].values()):
                raise ValueError("failure event must carry exact string diagnostics")
    W._equal(row, W._seal({k: v for k, v in row.items() if k != "event_digest"}, "event_digest"),
             what="repair event content digest")


def _load_events(roots, start):
    local, durable = _event_directories(roots)
    names = set()
    for directory in (local, durable):
        for path in directory.iterdir():
            if re.fullmatch(r"[0-9]{6}\.json", path.name):
                W._project_path(path, directory=False)
                names.add(path.name)
            elif not (path.name.startswith(".") and path.name.endswith(".tmp")):
                raise ValueError("unknown file in immutable repair event directory")
    if sorted(names) != [f"{i:06d}.json" for i in range(len(names))]:
        raise ValueError("immutable repair event sequence has a gap")
    events, previous = [], None
    for index, name in enumerate(sorted(names)):
        paths = local / name, durable / name
        existing = [p for p in paths if p.exists()]
        row = read_json(existing[0])
        _validate_event(row, index=index, previous=previous, context_digest=start["execution_context_digest"])
        if row["kind"] == "attempt_started":
            W._verify_prior_start(row["data"]["checkpoint_digest"], start, roots)
        # Repair only a missing twin, never rewrite a present divergent event.
        for path in paths:
            if not path.exists():
                atomic_write_bytes(path, existing[0].read_bytes())
        W._same_file_copy(*paths)
        events.append(row)
        previous = row["event_digest"]
    starts, synced, completed = set(), set(), False
    for event in events:
        if completed:
            raise ValueError("repair events exist after whole-plan completion")
        if event["kind"] == "complete":
            if synced != {j.job_id for j in W.new_exp1_repair_jobs()}:
                raise ValueError("completion event is missing exact synced jobs")
            completed = True
        elif event["kind"] != "attempt_started" and event["job_id"] not in starts:
            raise ValueError("repair event has no preceding durable attempt-start record")
        target = starts if event["kind"] == "attempt_started" else synced if event["kind"] == "job_synced" else None
        if target is not None:
            if event["job_id"] in target:
                raise ValueError("duplicate attempt or sync event; automatic retry is prohibited")
            target.add(event["job_id"])
    return events


def _append_event(roots, start, events, *, kind, job_id, data):
    row = W._seal({"event_schema_version": 1, "sequence": len(events),
        "previous_digest": events[-1]["event_digest"] if events else None,
        "execution_context_digest": start["execution_context_digest"],
        "kind": kind, "job_id": job_id, "data": data}, "event_digest")
    _validate_event(row, index=len(events), previous=row["previous_digest"],
                    context_digest=start["execution_context_digest"])
    local, durable = _event_directories(roots)
    name = f"{len(events):06d}.json"
    atomic_write_json(durable / name, row)
    atomic_write_json(local / name, row)
    W._same_file_copy(local / name, durable / name)
    events.append(row)


def _request(checkpoint_path, start, commit, job):
    return {"checkpoint_path": str(checkpoint_path), "checkpoint_sha256": sha256_file(checkpoint_path),
            "expected_git_commit": commit, "job": job.as_record()}


def _kwargs(request):
    return {k: request[k] for k in ("checkpoint_path", "checkpoint_sha256", "expected_git_commit")}


def _sync_complete(job, request, roots):
    before = W.validate_local_completed_exp1_job(job.job_id, **_kwargs(request))
    source, destination = (roots[name] / "jobs" / job.job_id for name in ("output", "sync"))
    W._project_path(source, directory=True)
    W._project_path(destination, directory=True, existing=False)
    # Fixed transport only; no caller-supplied sync function or external path.
    B._publish_job_tree(source, destination)
    verified = W.reconcile_completed_exp1_job(job.job_id, **_kwargs(request))
    if verified is None or verified["source_tree_digest"] != before["source_tree_digest"]:
        raise ValueError("completed source changed during durable synchronization")
    return {key: verified[key] for key in ("execution_digest", "source_tree_digest", "copy_evidence_digest")}


def _run_one_job(job, *, validated, checkpoint_path, start, events):
    roots = validated.roots
    request = _request(checkpoint_path, start, validated.git_commit, job)
    local, durable = (roots[name] / "jobs" / job.job_id for name in ("output", "sync"))
    history = [row for row in events if row["job_id"] == job.job_id]
    synced = [row for row in history if row["kind"] == "job_synced"]
    if any(row["kind"] == "attempt_failed" for row in history):
        raise ValueError("prior failed attempt is preserved; no automatic retry or silent adoption")
    if os.path.lexists(local):
        if not any(row["kind"] == "attempt_started" for row in history):
            raise ValueError("complete local fit has no durable launch-attempt history")
        result = _sync_complete(job, request, roots)
        if synced:
            W._equal(synced[0]["data"], result, what="resumed prior sync attestation")
        else:
            _append_event(roots, start, events, kind="job_synced", job_id=job.job_id, data=result)
        return "resumed"
    if os.path.lexists(durable) or history:
        raise ValueError("job has prior execution evidence but no complete local fit; retraining is prohibited")
    for directory in (roots["staging"] / "staging", roots["staging"] / "quarantine"):
        if directory.exists():
            W._project_path(directory, directory=True)
            if any(directory.glob(f"{job.job_id}.*")):
                raise ValueError("preserved prior attempt requires inspection; automatic retry is prohibited")
    W._environment(validated.git_commit)
    # New-child-only: refusal must not create attempt history or block the
    # complete-fit sync branch above. Reopen the original launch-pinned floor.
    check_preflight_storage(validated.report_path, validated.report_sha256, roots=roots)
    _append_event(roots, start, events, kind="attempt_started", job_id=job.job_id,
                  data={"checkpoint_digest": start["checkpoint_digest"]})
    try:
        outcome = run_isolated_attempt(W._fit_worker, root=roots["output"], staging_root=roots["staging"],
            job_id=job.job_id, payload=request, timeout_seconds=validated.report["attempt_timeout_seconds"])
        if (type(outcome) is not AttemptOutcome or outcome.job_id != job.job_id
                or not outcome.succeeded or outcome.canonical_dir != local):
            raise ValueError(f"isolated attempt did not publish its exact successful job: {outcome!r}")
    except BaseException as exc:
        _append_event(roots, start, events, kind="attempt_failed", job_id=job.job_id,
                      data={"type": type(exc).__name__, "message": str(exc)})
        raise
    try:
        result = _sync_complete(job, request, roots)
    except BaseException as exc:
        _append_event(roots, start, events, kind="sync_pending", job_id=job.job_id,
                      data={"type": type(exc).__name__, "message": str(exc)})
        raise
    _append_event(roots, start, events, kind="job_synced", job_id=job.job_id, data=result)
    return "executed"


def _check_lease_namespace() -> Path:
    """Check raw control descendants BEFORE any supervisor lock/lease writes."""
    root = W._project_path(W.COMMON_LEASE_ROOT, directory=True)
    for path in (root / "leases", root / "leases" / "history"):
        W._project_path(path, directory=True, existing=os.path.lexists(path))
    for name in (f"{W.COMMON_LEASE_NAME}.lease.json",
                 f".{W.COMMON_LEASE_NAME}.lease-transition.lock"):
        path = root / "leases" / name
        W._project_path(path, directory=False, existing=os.path.lexists(path))
    return root


def launch_exp1_repairs(*, preflight_report, output_root, sync_root, expected_git_commit) -> dict[str, Any]:
    """Execute/resume only the exact new E1 jobs; stop on any failed attempt."""
    validated = validate_exp1_repair_preflight(preflight_report, output_root=output_root,
        sync_root=sync_root, expected_git_commit=expected_git_commit)
    original_report_sha256 = validated.report_sha256
    jobs = W.new_exp1_repair_jobs()
    W._equal([j.as_record() for j in jobs], W.build_exp1_repair_plan()["new_jobs"], what="exact new launch jobs")
    lease = acquire_batch_lease(_check_lease_namespace(), lease_name=W.COMMON_LEASE_NAME)
    checkpoint_path, failure, complete = None, None, False
    counts = {"executed": 0, "resumed": 0, "synced": 0, "total": len(jobs)}
    try:
        # Revalidate all 102 references under the common lease before start.
        revalidated = validate_exp1_repair_preflight(preflight_report, output_root=output_root,
            sync_root=sync_root, expected_git_commit=expected_git_commit)
        if revalidated.report_sha256 != original_report_sha256:
            raise ValueError("preflight report changed from the original launch SHA256 under the lease")
        checkpoint_path = W.write_exp1_repair_start_checkpoint(
            reuse_ledger_path=validated.report["inputs"]["reuse_ledger"]["path"],
            expected_git_commit=validated.git_commit, output_root=validated.roots["output"],
            staging_root=validated.roots["staging"], sync_root=validated.roots["sync"],
            attempt_timeout_seconds=validated.report["attempt_timeout_seconds"], lease=lease,
            preflight_report=validated.report_path)
        start = read_json(checkpoint_path)
        if start["preflight"]["sha256"] != original_report_sha256:
            raise ValueError("start preflight changed from the original launch SHA256")
        events = _load_events(validated.roots, start)
        for job in jobs:
            status = _run_one_job(job, validated=validated, checkpoint_path=checkpoint_path,
                                  start=start, events=events)
            counts[status] += 1
            counts["synced"] += 1
        # Reopen every historical source and every new completed copy before
        # the one event that may claim the exact whole plan is complete.
        revalidated = validate_exp1_repair_preflight(preflight_report, output_root=output_root,
            sync_root=sync_root, expected_git_commit=expected_git_commit)
        if revalidated.report_sha256 != original_report_sha256:
            raise ValueError("preflight report changed from the original launch SHA256 before completion")
        for job in jobs:
            if W.reconcile_completed_exp1_job(job.job_id, **_kwargs(_request(checkpoint_path, start, validated.git_commit, job))) is None:
                raise ValueError("a new fit disappeared before complete-plan finalization")
        if not any(e["kind"] == "complete" for e in events):
            _append_event(validated.roots, start, events, kind="complete", job_id=None,
                          data={"synced_physical_fits": len(jobs), "historical_sources_reverified": 102})
        complete = True
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        released, release_error = None, None
        try:
            _check_lease_namespace()
            # A supervisor cleanup refusal must retain ownership. Never turn
            # that refusal into an undocumented exit or an automatic unlock.
            released = lease.release()
        except BaseException as exc:
            release_error = exc
        interrupted = failure is not None and failure["type"] in {"KeyboardInterrupt", "SystemExit"}
        report = {"exp1_repair_launch_schema_version": 1,
                  "status": "complete" if complete and released is not None else "interrupted" if interrupted else "incomplete",
                  "counts": counts, "failure": failure, "historical_retrained": False,
                  "preflight": {"path": str(validated.report_path), "sha256": validated.report_sha256},
                  "checkpoint": None if checkpoint_path is None else {"path": str(checkpoint_path),
                                "sha256": sha256_file(checkpoint_path)},
                  "released_lease": None if released is None else {"token": lease.token, "history_path": str(released)},
                  "lease_release_failure": None if release_error is None else {
                      "type": type(release_error).__name__, "message": str(release_error),
                      "token": lease.token, "active_path": str(lease.path),
                      "automatic_recovery_allowed": False}}
        paths = []
        for name in ("sync", "output"):
            directory = RF.ensure_regular_child_directory(validated.roots[name], REPORT_DIRECTORY)
            paths.append(atomic_write_json(directory / f"{lease.token}.json", report))
        W._same_file_copy(paths[1], paths[0])
        if release_error is not None:
            raise release_error
    return {**report, "report_path": str(paths[1])}
