"""Exactly six first-sweep repairs, with qualified identities and no retry.

Only unit 0184fbfcd8b9, seeds 1000--1002, data/capacity repairs are executable.
Three caller-pinned baseline/copy pairs and an independently pinned all_repairs
timing record are mandatory. No caller executor, arbitrary contract, stage,
scale, seed subset or legacy-runner bypass is accepted.

One stable execution context binds sources, contracts, timing, commit, roots
and timeout; each lease has its own durable start. Results retain their actual
start across later leases. Immutable hash-chained events precede each attempt.
Failed/unknown attempts stop; a valid complete local job may only be synced.
This adapter never labels units or changes the old confirmatory repair guard.
"""

from __future__ import annotations

import dataclasses
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import Arm, Config
from ..durable import atomic_write_bytes, atomic_write_json, read_json, sha256_file
from ..streams import group_of
from . import batch as B
from . import fit_evidence as F
from . import launch as L
from . import paired_repair_evidence as E
from . import preflight as P
from . import repair_label_preflight as RF
from . import repair_pairing as RP
from . import repair_timing as RT
from . import week7_exp1_repairs as W
from .prefit_storage import check_sweep_context_storage
from .enumerate_units import arms_for
from .supervisor import (
    ATTEMPT_FILE, RECEIPT_FILE, RESULT_FILE, SUPERVISOR_SCHEMA_VERSION,
    AttemptOutcome, BatchLease, acquire_batch_lease, run_isolated_attempt,
    _job_tree_digest as _supervisor_tree_digest,
)
from .week7_plan import configuration_sweep_baseline_jobs


LAUNCH_SCHEMA_VERSION = 1
FIRST_UNIT_ID = "0184fbfcd8b9"
SEEDS = (1000, 1001, 1002)
ARMS = ("data_repair", "capacity_repair")
CONTEXT_FILE = "week7_sweep_repair_context.json"
START_DIRECTORY = "week7_sweep_repair_starts"
EVENT_DIRECTORY = "week7_sweep_repair_events"
REPORT_DIRECTORY = "week7_sweep_repair_reports"
_WORKER = "bu.experiments.week7_sweep_repair_launch._fit_worker"
_EVENTS = {"attempt_started", "attempt_failed", "sync_pending", "job_synced", "complete"}


@dataclass(frozen=True)
class BaselineSource:
    seed: int
    source_path: str | Path
    copy_path: str | Path
    expected_git_commit: str
    expected_execution_digest: str
    expected_anchor_sha256: str


@dataclass(frozen=True)
class TimingPin:
    path: str | Path
    sha256: str
    expected_git_commit: str


@dataclass(frozen=True)
class SweepRepairJob:
    contract: RP.SweepRepairContract

    @property
    def job_id(self) -> str:
        return self.contract.physical_fit_id

    @property
    def seed(self) -> int:
        return self.contract.seed

    @property
    def arm(self) -> str:
        return self.contract.arm

    def as_record(self) -> dict:
        cfg = Config(unit=self.contract.unit, arm=Arm(self.arm), seed=self.seed,
                     stage="exp3_repairs", train=E.C.REPAIRED_TRAIN)
        return {"physical_fit_id": self.job_id,
                "physical_run_id": self.contract.physical_run_id,
                "obligation_fit_id": cfg.fit_id, "obligation_run_id": cfg.run_id,
                "config": cfg.to_dict(), "contract_sha256": self.contract.contract_sha256,
                "contract": self.contract.as_dict()}


def _first_baselines():
    jobs = tuple(sorted(configuration_sweep_baseline_jobs(), key=lambda j:
                        (group_of(j.unit, j.stage), j.config.unit_id, j.seed))[:3])
    if (len(jobs) != 3 or tuple(j.seed for j in jobs) != SEEDS
            or any(j.config.unit_id != FIRST_UNIT_ID or j.stage != "config_sweep"
                   or j.arm != "baseline" or j.roles != ("config_sweep",) for j in jobs)
            or tuple(j.job_id for j in jobs) != tuple(f"cc428cf4ab47-s{s}" for s in SEEDS)
            or arms_for(jobs[0].unit) != ("baseline", *ARMS)):
        raise ValueError("first registered sweep inventory changed; exact unit/arms/seeds are required")
    return jobs


def _descriptors(baselines) -> tuple[BaselineSource, ...]:
    if type(baselines) is not tuple or len(baselines) != 3:
        raise ValueError("exactly three BaselineSource descriptors in a tuple are required")
    if any(type(s) is not BaselineSource or type(s.seed) is not int for s in baselines):
        raise ValueError("baseline descriptors and seeds must have exact types")
    if tuple(s.seed for s in baselines) != SEEDS:
        raise ValueError("baseline descriptors must name seeds 1000,1001,1002 in that order")
    canonical, paths = [], []
    for s in baselines:
        source = W._project_path(s.source_path, directory=True)
        copy = W._project_path(s.copy_path, directory=True)
        canonical.append(BaselineSource(s.seed, source, copy,
            F._validate_expected_git_commit(s.expected_git_commit),
            L._lower_sha256(s.expected_execution_digest, what="independent baseline execution digest"),
            L._lower_sha256(s.expected_anchor_sha256, what="independent baseline anchor digest")))
        paths.extend((source, copy))
    for i, left in enumerate(paths):
        if any(P._overlap(left, right) or os.path.samefile(left, right) for right in paths[i + 1:]):
            raise ValueError("baseline originals/copies must be mutually separate plain trees")
    return tuple(canonical)


def _source_record(source: BaselineSource) -> dict:
    return {**dataclasses.asdict(source), "source_path": str(source.source_path),
            "copy_path": str(source.copy_path)}


def _source_pair(source: BaselineSource, baseline_job) -> dict:
    left, right = Path(source.source_path), Path(source.copy_path)
    for path in (left, right):
        W._plain_tree(path)
    before = B._copy_evidence_digest(left, right)
    for path in (left, right):
        fit = F.load_fit_evidence(path, expected_git_commit=source.expected_git_commit)
        if (type(fit) is not F.VerifiedFitEvidence or fit.unit != baseline_job.unit
                or fit.seed != source.seed or fit.arm != "baseline"
                or fit.execution_stage != "config_sweep" or fit.roles != ("config_sweep",)
                or fit.fit_id != baseline_job.job_id
                or fit.execution_run_id != baseline_job.config.run_id
                or fit.execution_digest != source.expected_execution_digest):
            raise ValueError("baseline identity/execution differs from the independently pinned first sweep fit")
        anchor = F.validate_sweep_pool_anchors(path, expected_git_commit=source.expected_git_commit)
        if anchor.anchor_sha256 != source.expected_anchor_sha256:
            raise ValueError("baseline anchor differs from the independent digest")
    after = B._copy_evidence_digest(left, right)
    if after != before:
        raise ValueError("baseline source/copy changed during verification")
    return {**_source_record(source), "source_tree_digest": B._job_tree_digest(left),
            "copy_evidence_digest": after}


def _sources_and_jobs(baselines):
    descriptors = _descriptors(baselines)
    rows, jobs = [], []
    for source, baseline in zip(descriptors, _first_baselines(), strict=True):
        before = _source_pair(source, baseline)
        for arm in ARMS:
            expected = dict(expected_baseline_commit=source.expected_git_commit,
                            expected_baseline_execution_digest=source.expected_execution_digest)
            contract = RP.registered_sweep_pairing(baseline.unit, arm=arm, seed=source.seed,
                                                  baseline_source=source.source_path, **expected)
            copied = RP.registered_sweep_pairing(baseline.unit, arm=arm, seed=source.seed,
                                                baseline_source=source.copy_path, **expected)
            if contract.canonical_json != copied.canonical_json:
                raise ValueError("source/copy pairing contract differs")
            if contract.physical_fit_id == contract.obligation_fit_id:
                raise ValueError("paired execution must have a qualified physical identity")
            jobs.append(SweepRepairJob(contract))
        W._equal(_source_pair(source, baseline), before, what="baseline after contract derivation")
        rows.append(before)
    if len(jobs) != 6 or len({j.job_id for j in jobs}) != 6:
        raise ValueError("exactly six distinct qualified physical repairs are required")
    return rows, tuple(jobs)


def _timing(pin: TimingPin, jobs) -> tuple[dict, dict]:
    if type(pin) is not TimingPin:
        raise ValueError("timing must be an exact TimingPin")
    path = W._project_path(pin.path, directory=False)
    W._project_path(path.with_name(path.name + ".sha256"), directory=False)
    sha = L._lower_sha256(pin.sha256, what="independent timing file SHA256")
    commit = F._validate_expected_git_commit(pin.expected_git_commit)
    if sha256_file(path) != sha:
        raise ValueError("timing bytes differ from their independent pin")
    record = RT.load_timing_record(path)
    inventory = RT.repair_inventory("all_repairs")
    W._equal(record["inventory"], inventory, what="all_repairs timing inventory")
    measured = RT._validate_benchmarks(record["benchmarks"], inventory)
    host = {"platform": platform.platform(), "processor": platform.processor() or platform.machine(),
            "python": platform.python_version(), "machine": platform.machine(),
            "hostname": platform.node(), "logical_cpu_count": os.cpu_count()}
    for row in measured.values():
        if row["environment_before"]["source_commit"] != commit:
            raise ValueError("timing source commit differs from its independent pin")
        W._equal({k: row["environment_before"][k] for k in host}, host, what="timing host")
    groups = {g["group_id"]: g for g in inventory["groups"]}
    counts = {}
    for job in jobs:
        effective = Arm(job.arm).resolve(job.contract.unit)
        key = {"architecture": RT._architecture(effective), "n_transitions": effective.n_transitions}
        gid = RT._digest(key)
        if gid not in groups or gid not in measured:
            raise ValueError("missing exact first-sweep architecture/size timing; no zero or scaled defaults")
        counts[gid] = counts.get(gid, 0) + 1
    contributions = []
    for gid, n in sorted(counts.items()):
        reps = measured[gid]["repetitions"]
        contributions.append({"group_id": gid, "model_fits": n, "collection_events": n,
            "training_s": n * max(r["training_s"] for r in reps),
            "collection_s": n * max(r["collection_s"] for r in reps)})
    total = sum(r["training_s"] + r["collection_s"] for r in contributions)
    L._positive_number(total, what="measured first-sweep repair estimate")
    if sha256_file(path) != sha:
        raise ValueError("timing changed during verification")
    return {"path": str(path), "sha256": sha, "expected_git_commit": commit}, {
        "model_fits": 6, "summary": "sum_of_per_group_empirical_maxima",
        "contributions": contributions, "total_s": total, "local_wall_hours": total / 3600,
        "limitations": list(RT.LIMITATIONS),
        "interpretation": "exact-group local estimate; NOT timeout, upper bound or GPU-hour gate",
    }


def _roots(output_root, staging_root, sync_root, *, sources, timing_path, minimum_free_bytes):
    if type(minimum_free_bytes) is not int or minimum_free_bytes <= 0:
        raise ValueError("minimum_free_bytes must be an explicit positive exact integer")
    roots = {name: W._project_path(path, directory=True) for name, path in
             (("output", output_root), ("staging", staging_root), ("sync", sync_root))}
    protected = [W._project_path(W.COMMON_LEASE_ROOT, directory=True), Path(timing_path)]
    protected += [Path(row[k]) for row in sources for k in ("source_path", "copy_path")]
    for i, (name, root) in enumerate(roots.items()):
        for other in tuple(roots.values())[i + 1:] + tuple(protected):
            if P._overlap(root, other):
                raise ValueError("execution roots overlap each other or protected baseline/timing/lease sources")
        P._resolved_root(root, name=name, minimum_free_bytes=minimum_free_bytes)
    L._validate_same_volume_staging(roots["output"], roots["staging"])
    return roots


def _environment(expected_commit):
    commit = F._validate_expected_git_commit(expected_commit)
    if (E.C.CONFIRMATORY_DEVICE, E.C.CONFIRMATORY_THREADS, E.C.CONFIRMATORY_INTEROP_THREADS) != ("cpu", 4, 4):
        raise ValueError("first-sweep repairs require the exact frozen CPU 4/4 route")
    environment = RT._environment(pin=True)
    if environment["source_commit"] != commit:
        raise ValueError("current clean Git commit differs from independently expected repair commit")
    return {"git_commit": commit, **environment}


def prepare_first_sweep_repairs(
    *, baselines: tuple[BaselineSource, ...], timing: TimingPin, expected_git_commit: str,
    output_root: str | Path, staging_root: str | Path, sync_root: str | Path,
    attempt_timeout_seconds: float, minimum_free_bytes: int, sync_destination_identity: str,
) -> dict:
    """Read-only preparation: exact six jobs, original/copy pins and measured budget."""
    timeout = L._positive_number(attempt_timeout_seconds, what="mandatory attempt timeout")
    environment = _environment(expected_git_commit)
    sources, jobs = _sources_and_jobs(baselines)
    timing_row, budget = _timing(timing, jobs)
    roots = _roots(output_root, staging_root, sync_root, sources=sources,
                   timing_path=timing_row["path"], minimum_free_bytes=minimum_free_bytes)
    return W._seal({"sweep_repair_launch_schema_version": LAUNCH_SCHEMA_VERSION,
        "purpose": "exact_first_sweep_six_paired_repairs", "unit_id": FIRST_UNIT_ID,
        "sources": sources, "jobs": [job.as_record() for job in jobs],
        "timing": timing_row, "budget": budget, "environment": environment,
        "roots": {name: str(path) for name, path in roots.items()},
        "attempt_timeout_seconds": timeout, "minimum_free_bytes": minimum_free_bytes,
        "sync_destination_identity": P._validate_destination_identity(sync_destination_identity),
        "common_lease_root": str(W.COMMON_LEASE_ROOT.resolve()),
        "common_lease_name": W.COMMON_LEASE_NAME, "fixed_worker": _WORKER,
        "automatic_retry_allowed": False, "baseline_retraining_allowed": False,
    }, "execution_context_digest")


def _revalidate_context(context: dict, commit: str) -> dict:
    if type(context) is not dict:
        raise ValueError("execution context must be an exact record")
    try:
        baseline_fields = {field.name for field in dataclasses.fields(BaselineSource)}
        baselines = tuple(BaselineSource(**{k: row[k] for k in baseline_fields})
                          for row in context["sources"])
        roots = context["roots"]
        rebuilt = prepare_first_sweep_repairs(
            baselines=baselines, timing=TimingPin(**context["timing"]), expected_git_commit=commit,
            output_root=roots["output"], staging_root=roots["staging"], sync_root=roots["sync"],
            attempt_timeout_seconds=context["attempt_timeout_seconds"],
            minimum_free_bytes=context["minimum_free_bytes"],
            sync_destination_identity=context["sync_destination_identity"])
    except (KeyError, TypeError) as exc:
        raise ValueError("malformed first-sweep execution context") from exc
    W._equal(context, rebuilt, what="rederived first-sweep execution context")
    return rebuilt


def _job(context, job_id):
    rows = [row for row in context["jobs"] if row["physical_fit_id"] == job_id]
    if type(job_id) is not str or len(rows) != 1:
        raise ValueError("job must be one of the exact six qualified first-sweep repairs")
    contract = RP.SweepRepairContract(RP._json(rows[0]["contract"]))
    job = SweepRepairJob(contract)
    W._equal(rows[0], job.as_record(), what="complete qualified job record")
    return job


def _paths(context):
    return {k: Path(v) for k, v in context["roots"].items()}


def _twins(roots, relative, document=None):
    local, durable = (roots[k] / relative for k in ("output", "sync"))
    # The durable writer resolves parents. Check BOTH raw destinations first,
    # including absent leaves beneath existing Windows reparse ancestors.
    for path in (local, durable):
        W._project_path(path, directory=False, existing=False)
    if document is not None:
        atomic_write_json(durable, document)
        atomic_write_json(local, document)
    W._same_file_copy(local, durable)
    return local


def _start(context, lease: BatchLease):
    if type(lease) is not BatchLease or lease._released:
        raise ValueError("launch needs its exact active common lease")
    lease_row = W._lease_record(lease.token)
    if (lease.path.resolve() != Path(lease_row["path"]).resolve()
            or read_json(lease.path)["pid"] != os.getpid()):
        raise ValueError("common lease belongs to a different launch process")
    roots = _paths(context)
    _twins(roots, CONTEXT_FILE, context)
    for name in ("output", "sync"):
        W._project_path(roots[name] / P.SYNC_CANARY_FILE, directory=False, existing=False)
    canary, receipt = P._run_sync_canary(
        roots={"preflight": roots["output"], "sync": roots["sync"]},
        plan_digest=context["execution_context_digest"],
        destination_identity=context["sync_destination_identity"],
        adapter=P.sync_canary_to_mounted_directory)
    W._same_file_copy(Path(canary["source_path"]), Path(canary["destination_path"]))
    document = W._seal({"sweep_repair_start_schema_version": 1,
        "execution_context_digest": context["execution_context_digest"],
        "lease": lease_row, "sync_canary": canary, "sync_receipt": receipt}, "start_digest")
    path = _twins(roots, Path(START_DIRECTORY) / f"{lease.token}.json", document)
    return path, document


def _verify_start(context, digest, *, active=False):
    L._lower_sha256(digest, what="independently bound start digest")
    roots, matches = _paths(context), []
    directory = W._project_path(roots["output"] / START_DIRECTORY, directory=True)
    for path in directory.iterdir():
        if not re.fullmatch(r"[0-9a-f]{32}\.json", path.name):
            raise ValueError("unknown artifact in sweep repair start directory")
        W._project_path(path, directory=False)
        document = read_json(path)
        if type(document) is not dict or document.get("start_digest") != digest:
            continue
        token = path.stem
        lease = W._lease_record(token) if active else W._historical_lease_record(token)
        expected = W._seal({"sweep_repair_start_schema_version": 1,
            "execution_context_digest": context["execution_context_digest"], "lease": lease,
            "sync_canary": document.get("sync_canary"), "sync_receipt": document.get("sync_receipt")}, "start_digest")
        W._equal(document, expected, what="actual lease-bound start")
        if path.read_bytes() != L._pretty_json_bytes(expected):
            raise ValueError("start checkpoint is not canonical JSON")
        _twins(roots, path.relative_to(roots["output"]))
        # Read-only validation of the same fixed mounted-directory canary.
        L._validate_sync_evidence(document,
            roots={"preflight": roots["output"], "sync": roots["sync"]},
            plan_sha256=context["execution_context_digest"])
        W._same_file_copy(Path(document["sync_canary"]["source_path"]),
                          Path(document["sync_canary"]["destination_path"]))
        matches.append(document)
    if len(matches) != 1:
        raise ValueError("job must bind exactly one genuine independently copied launch start")
    _twins(roots, CONTEXT_FILE)
    W._equal(read_json(roots["output"] / CONTEXT_FILE), context, what="stable context bytes")
    return matches[0]


def _load_start(path, sha, expected_commit, *, active=True):
    path = W._project_path(path, directory=False)
    if sha256_file(path) != L._lower_sha256(sha, what="start checkpoint file SHA256"):
        raise ValueError("worker checkpoint differs from its independent file pin")
    if path.parent.name != START_DIRECTORY:
        raise ValueError("worker must use the prescribed start directory")
    context = read_json(W._project_path(path.parent.parent / CONTEXT_FILE, directory=False))
    _revalidate_context(context, expected_commit)
    start = _verify_start(context, read_json(path).get("start_digest"), active=active)
    if path != _paths(context)["output"] / START_DIRECTORY / f"{start['lease']['token']}.json":
        raise ValueError("worker checkpoint is not the prescribed local start")
    return context, start


def _validate_events(events, context):
    previous, states, complete = None, {}, False
    for i, row in enumerate(events):
        L._strict_keys(row, {"schema_version", "sequence", "previous_digest", "execution_context_digest",
                            "kind", "job_id", "data", "event_digest"}, what="sweep repair event")
        if (type(row["schema_version"]) is not int or row["schema_version"] != 1
                or type(row["sequence"]) is not int or row["sequence"] != i
                or row["previous_digest"] != previous
                or row["execution_context_digest"] != context["execution_context_digest"]
                or type(row["kind"]) is not str or row["kind"] not in _EVENTS or complete):
            raise ValueError("event sequence, context or terminal state is invalid")
        W._equal(row, W._seal({k: v for k, v in row.items() if k != "event_digest"}, "event_digest"),
                 what="event digest")
        kind, jid, data = row["kind"], row["job_id"], row["data"]
        if kind == "complete":
            if jid is not None or set(states) != {j["physical_fit_id"] for j in context["jobs"]} or any(v != "job_synced" for v in states.values()):
                raise ValueError("completion requires all six exact synced jobs")
            W._equal(data, {"synced_repairs": 6, "baseline_retrained": 0}, what="completion counts")
            complete = True
        else:
            _job(context, jid)
            if kind == "attempt_started":
                if jid in states:
                    raise ValueError("duplicate/prior attempt: automatic retry is prohibited")
                L._strict_keys(data, {"start_digest"}, what="job start")
                _verify_start(context, data["start_digest"])
            else:
                if jid not in states or states[jid] in {"attempt_failed", "job_synced"}:
                    raise ValueError("event lacks a live prior start or follows a terminal job")
                if kind == "job_synced":
                    L._strict_keys(data, {"execution_digest", "source_tree_digest", "copy_evidence_digest"}, what="job sync")
                    for key, value in data.items():
                        L._lower_sha256(value, what=key)
                else:
                    L._strict_keys(data, {"type", "message"}, what="job failure")
                    if any(type(v) is not str for v in data.values()):
                        raise ValueError("failure details must be exact strings")
            states[jid] = kind
        previous = row["event_digest"]


def _load_events(context, *, repair_missing=True):
    roots = _paths(context)
    for name in ("output", "sync"):
        W._project_path(roots[name] / EVENT_DIRECTORY, directory=True, existing=False)
    dirs = [RF.ensure_regular_child_directory(roots[k], EVENT_DIRECTORY) for k in ("output", "sync")]
    names = set()
    for directory in dirs:
        for path in directory.iterdir():
            W._project_path(path, directory=False)
            if not re.fullmatch(r"[0-9]{6}\.json", path.name):
                raise ValueError("unknown sweep repair event artifact")
            names.add(path.name)
    if sorted(names) != [f"{i:06d}.json" for i in range(len(names))]:
        raise ValueError("event sequence has a gap")
    events = []
    for name in sorted(names):
        pair = [d / name for d in dirs]
        existing = [p for p in pair if p.exists()]
        row = read_json(existing[0])
        if existing[0].read_bytes() != L._pretty_json_bytes(row):
            raise ValueError("event is not canonical JSON")
        _validate_events([*events, row], context)
        for path in pair:
            if not path.exists():
                if not repair_missing:
                    raise ValueError("worker requires both durable event copies")
                W._project_path(path, directory=False, existing=False)
                atomic_write_bytes(path, existing[0].read_bytes())
        W._same_file_copy(*pair)
        events.append(row)
    return events


def _append(context, events, kind, job_id, data):
    row = W._seal({"schema_version": 1, "sequence": len(events),
        "previous_digest": events[-1]["event_digest"] if events else None,
        "execution_context_digest": context["execution_context_digest"],
        "kind": kind, "job_id": job_id, "data": data}, "event_digest")
    _validate_events([*events, row], context)
    _twins(_paths(context), Path(EVENT_DIRECTORY) / f"{len(events):06d}.json", row)
    events.append(row)


def _source_for(context, job):
    return next(row for row in context["sources"] if row["seed"] == job.seed)


def _reader_args(context, job, *, copy=False):
    source = _source_for(context, job)
    return dict(unit=job.contract.unit, arm=job.arm, seed=job.seed,
        baseline_source=source["copy_path" if copy else "source_path"],
        expected_baseline_commit=source["expected_git_commit"],
        expected_baseline_execution_digest=source["expected_execution_digest"],
        expected_git_commit=context["environment"]["git_commit"])


def _result(context, job, verified, start_digest):
    if (type(verified) is not E.VerifiedPairedRepair or verified.physical_fit_id != job.job_id
            or verified.contract.canonical_json != job.contract.canonical_json):
        raise ValueError("completed repair does not match the exact qualified job")
    return {"sweep_repair_result_schema_version": 1, "job": job.as_record(),
            "execution_context_digest": context["execution_context_digest"],
            "start_digest": start_digest, "repair_commit": context["environment"]["git_commit"],
            "paired_execution_digest": verified.execution_digest,
            "baseline_source": _source_for(context, job)}


def _prior_attempts(context, job, *, current=None):
    roots = _paths(context)
    for name in ("staging", "quarantine"):
        directory = roots["staging"] / name
        if os.path.lexists(directory):
            W._project_path(directory, directory=True)
            for path in directory.iterdir():
                if path.name.startswith(job.job_id + ".") and path != current:
                    raise ValueError("preserved prior/unknown attempt; automatic retry is prohibited")


def _fit_worker(attempt_dir: Path, payload: Any) -> dict:
    row = L._strict_keys(payload, {"checkpoint_path", "checkpoint_sha256", "expected_git_commit", "job_id"}, what="sweep worker")
    context, start = _load_start(row["checkpoint_path"], row["checkpoint_sha256"], row["expected_git_commit"])
    job, roots = _job(context, row["job_id"]), _paths(context)
    attempt = W._project_path(attempt_dir, directory=True)
    if (attempt.parent != roots["staging"] / "staging"
            or not re.fullmatch(re.escape(job.job_id) + r"\.[0-9a-f]{32}", attempt.name)):
        raise ValueError("worker attempt is not the prescribed supervisor staging child")
    envelope = L._strict_keys(read_json(W._project_path(attempt / ATTEMPT_FILE, directory=False)),
        {"schema_version", "job_id", "attempt_token", "parent_pid", "started_at", "timeout_seconds"}, what="attempt envelope")
    owner = read_json(Path(start["lease"]["path"]))["pid"]
    if (type(envelope["schema_version"]) is not int or envelope["schema_version"] != SUPERVISOR_SCHEMA_VERSION
            or envelope["job_id"] != job.job_id or envelope["attempt_token"] != attempt.name.rsplit(".", 1)[1]
            or type(envelope["parent_pid"]) is not int or envelope["parent_pid"] != owner
            or envelope["parent_pid"] == os.getpid()
            or L._positive_number(envelope["timeout_seconds"], what="supervisor timeout") != context["attempt_timeout_seconds"]):
        raise ValueError("worker requires fixed timeout, fresh process and actual lease owner")
    W.M._require_timestamp(envelope["started_at"], what="attempt start")
    history = [e for e in _load_events(context, repair_missing=False) if e["job_id"] == job.job_id]
    if len(history) != 1 or history[0]["kind"] != "attempt_started" or history[0]["data"] != {"start_digest": start["start_digest"]}:
        raise ValueError("worker requires its unique durable before-training job checkpoint")
    _prior_attempts(context, job, current=attempt)
    if any(os.path.lexists(roots[k] / "jobs" / job.job_id) for k in ("output", "sync")):
        raise ValueError("existing job evidence must be reconciled, never retrained")
    E.run_paired_repair(out_dir=attempt, **_reader_args(context, job))
    _revalidate_context(context, row["expected_git_commit"])
    verified = E.load_paired_repair_evidence(attempt, **_reader_args(context, job))
    W._lease_record(start["lease"]["token"])
    return _result(context, job, verified, start["start_digest"])


def _completed(context, job, *, start_digest, copy=False):
    roots = _paths(context)
    path = W._project_path(roots["sync" if copy else "output"] / "jobs" / job.job_id, directory=True)
    W._plain_tree(path)
    verified = E.load_paired_repair_evidence(path, **_reader_args(context, job, copy=copy))
    result = L._strict_keys(read_json(W._project_path(path / RESULT_FILE, directory=False)),
        {"sweep_repair_result_schema_version", "job", "execution_context_digest", "start_digest",
         "repair_commit", "paired_execution_digest", "baseline_source"}, what="completed job result")
    # The expected start comes from the durable before-training event, NOT from
    # the job's own result or a newly acquired lease during evidence-only sync.
    start = _verify_start(context, start_digest)
    W._equal(result, _result(context, job, verified, start["start_digest"]), what="complete job bound to actual prior start")
    attempt_fields = {"schema_version", "job_id", "attempt_token", "parent_pid", "started_at", "timeout_seconds"}
    attempt = L._strict_keys(read_json(W._project_path(path / ATTEMPT_FILE, directory=False)),
                             attempt_fields, what="completed attempt envelope")
    receipt = L._strict_keys(read_json(W._project_path(path / RECEIPT_FILE, directory=False)),
        attempt_fields | {"status", "child_pid", "finished_at", "elapsed_seconds", "exit_code",
                          "error_type", "error", "result_digest", "job_tree_digest", "published"},
        what="completed attempt receipt")
    lease_file = W.COMMON_LEASE_ROOT / "leases" / "history" / f"{W.COMMON_LEASE_NAME}.{start['lease']['token']}.released.json"
    if not lease_file.exists():
        lease_file = Path(start["lease"]["path"])
    lease_record = read_json(W._project_path(lease_file, directory=False))
    if sha256_file(lease_file) != start["lease"]["sha256"]:
        raise ValueError("actual original lease bytes changed")
    if (type(attempt.get("schema_version")) is not int or attempt["schema_version"] != SUPERVISOR_SCHEMA_VERSION
            or type(receipt.get("schema_version")) is not int or receipt["schema_version"] != SUPERVISOR_SCHEMA_VERSION
            or attempt.get("job_id") != job.job_id or receipt.get("job_id") != job.job_id
            or type(attempt.get("attempt_token")) is not str
            or re.fullmatch(r"[0-9a-f]{32}", attempt["attempt_token"]) is None
            or receipt.get("attempt_token") != attempt["attempt_token"]
            or receipt.get("status") != "success" or receipt.get("published") is not True
            or type(receipt.get("exit_code")) is not int or receipt["exit_code"] != 0
            or type(attempt.get("parent_pid")) is not int or attempt["parent_pid"] != lease_record["pid"]
            or type(receipt.get("parent_pid")) is not int or receipt["parent_pid"] != attempt["parent_pid"]
            or type(receipt.get("child_pid")) is not int or receipt["child_pid"] <= 0
            or receipt["child_pid"] == attempt.get("parent_pid")
            or receipt.get("started_at") != attempt.get("started_at")
            or receipt.get("error_type") is not None or receipt.get("error") is not None
            or L._positive_number(attempt["timeout_seconds"], what="completed attempt timeout") != context["attempt_timeout_seconds"]
            or L._positive_number(receipt["timeout_seconds"], what="completed receipt timeout") != context["attempt_timeout_seconds"]
            or receipt.get("result_digest") != B._result_digest(result)
            or receipt.get("job_tree_digest") != _supervisor_tree_digest(path)):
        raise ValueError("completed repair lacks its successful isolated attempt receipt")
    W.M._require_timestamp(attempt.get("started_at"), what="original attempt start")
    W.M._require_timestamp(receipt.get("finished_at"), what="original attempt finish")
    L._positive_number(receipt.get("elapsed_seconds"), what="isolated elapsed seconds")
    return {"execution_digest": verified.execution_digest,
            "source_tree_digest": B._job_tree_digest(path)}


def _sync(context, job, *, start_digest):
    roots = _paths(context)
    before = _completed(context, job, start_digest=start_digest)
    source, destination = (roots[k] / "jobs" / job.job_id for k in ("output", "sync"))
    W._project_path(destination, directory=True, existing=False)
    B._publish_job_tree(source, destination)
    W._equal(_completed(context, job, start_digest=start_digest, copy=True), before, what="copied completed repair")
    digest = B._copy_evidence_digest(source, destination)
    W._equal(_completed(context, job, start_digest=start_digest), before, what="source after sync")
    return {**before, "copy_evidence_digest": digest}


def _run_one(context, job, start_path, start, events):
    roots = _paths(context)
    _revalidate_context(context, context["environment"]["git_commit"])
    W._lease_record(start["lease"]["token"])
    history = [e for e in events if e["job_id"] == job.job_id]
    if any(e["kind"] == "attempt_failed" for e in history):
        raise ValueError("prior failed attempt is preserved; no automatic retry")
    _prior_attempts(context, job)
    local, durable = (roots[k] / "jobs" / job.job_id for k in ("output", "sync"))
    if os.path.lexists(local):
        if not history or history[0]["kind"] != "attempt_started":
            raise ValueError("local completion has no durable before-training attempt history")
        receipt = _sync(context, job, start_digest=history[0]["data"]["start_digest"])
        synced = [e for e in history if e["kind"] == "job_synced"]
        if synced:
            W._equal(receipt, synced[0]["data"], what="prior durable sync receipt")
        else:
            _append(context, events, "job_synced", job.job_id, receipt)
        _revalidate_context(context, context["environment"]["git_commit"])
        return "resumed"
    if history or os.path.lexists(durable):
        raise ValueError("unknown/partial prior evidence without complete local job; no retraining")
    # The earlier full revalidation remains; refresh capacity again after
    # source/history work, against the ORIGINAL start-bound context digest.
    check_sweep_context_storage(
        roots["output"] / CONTEXT_FILE, start["execution_context_digest"], roots=roots,
    )
    _append(context, events, "attempt_started", job.job_id, {"start_digest": start["start_digest"]})
    try:
        outcome = run_isolated_attempt(_fit_worker, root=roots["output"], staging_root=roots["staging"],
            job_id=job.job_id, timeout_seconds=context["attempt_timeout_seconds"],
            payload={"checkpoint_path": str(start_path), "checkpoint_sha256": sha256_file(start_path),
                     "expected_git_commit": context["environment"]["git_commit"], "job_id": job.job_id})
        if (type(outcome) is not AttemptOutcome or not outcome.succeeded or outcome.job_id != job.job_id
                or outcome.canonical_dir != local or not outcome.published):
            raise ValueError(f"isolated repair failed or did not publish its unique job: {outcome!r}")
        _revalidate_context(context, context["environment"]["git_commit"])
    except BaseException as exc:
        _append(context, events, "attempt_failed", job.job_id, {"type": type(exc).__name__, "message": str(exc)})
        raise
    try:
        receipt = _sync(context, job, start_digest=start["start_digest"])
    except BaseException as exc:
        _append(context, events, "sync_pending", job.job_id, {"type": type(exc).__name__, "message": str(exc)})
        raise
    _append(context, events, "job_synced", job.job_id, receipt)
    return "executed"


def _known_jobs(context):
    roots = _paths(context)
    ids = {row["physical_fit_id"] for row in context["jobs"]}
    for name in ("output", "sync"):
        directory = roots[name] / "jobs"
        if os.path.lexists(directory):
            W._project_path(directory, directory=True)
            for path in directory.iterdir():
                W._project_path(path, directory=True)
                if path.name not in ids:
                    raise ValueError("unknown job evidence exists in first-sweep execution roots")
    for name in ("staging", "quarantine"):
        directory = roots["staging"] / name
        if os.path.lexists(directory):
            W._project_path(directory, directory=True)
            for path in directory.iterdir():
                W._project_path(path, directory=True)
                if path.name.rsplit(".", 1)[0] not in ids:
                    raise ValueError("unknown isolated-attempt evidence exists")
                raise ValueError("preserved prior/unknown isolated attempt; automatic retry is prohibited")


def _lease_paths():
    """Validate raw shared-control paths before the supervisor writes them."""
    root = W._project_path(W.COMMON_LEASE_ROOT, directory=True)
    for path in (root / "leases", root / "leases" / "history"):
        W._project_path(path, directory=True, existing=False)
    for name in (f"{W.COMMON_LEASE_NAME}.lease.json", f".{W.COMMON_LEASE_NAME}.lease-transition.lock"):
        W._project_path(root / "leases" / name, directory=False, existing=False)
    return root


def launch_first_sweep_repairs(
    *, baselines: tuple[BaselineSource, ...], timing: TimingPin, expected_git_commit: str,
    output_root: str | Path, staging_root: str | Path, sync_root: str | Path,
    attempt_timeout_seconds: float, minimum_free_bytes: int, sync_destination_identity: str,
) -> dict:
    """Launch/resume exactly six repairs under the shared token-owned Week-7 lease."""
    context = prepare_first_sweep_repairs(
        baselines=baselines, timing=timing, expected_git_commit=expected_git_commit,
        output_root=output_root, staging_root=staging_root, sync_root=sync_root,
        attempt_timeout_seconds=attempt_timeout_seconds, minimum_free_bytes=minimum_free_bytes,
        sync_destination_identity=sync_destination_identity)
    roots = _paths(context)
    _known_jobs(context)
    lease = acquire_batch_lease(_lease_paths(), lease_name=W.COMMON_LEASE_NAME)
    start_path, complete, failure = None, False, None
    counts = {"executed": 0, "resumed": 0, "synced": 0, "total": 6}
    try:
        _revalidate_context(context, expected_git_commit)
        start_path, start = _start(context, lease)
        events = _load_events(context)
        for row in context["jobs"]:
            job = _job(context, row["physical_fit_id"])
            counts[_run_one(context, job, start_path, start, events)] += 1
            counts["synced"] += 1
        _revalidate_context(context, expected_git_commit)
        for row in context["jobs"]:
            job = _job(context, row["physical_fit_id"])
            synced = next(e for e in events if e["job_id"] == job.job_id and e["kind"] == "job_synced")
            started = next(e for e in events if e["job_id"] == job.job_id and e["kind"] == "attempt_started")
            W._equal(_sync(context, job, start_digest=started["data"]["start_digest"]),
                     synced["data"], what="final source/copy re-attestation")
        if not any(e["kind"] == "complete" for e in events):
            _append(context, events, "complete", None, {"synced_repairs": 6, "baseline_retrained": 0})
        complete = True
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        released, release_error = None, None
        try:
            _lease_paths()
            # The central supervisor stops/joins on BaseException. Its release
            # guard retains the lease if cleanup is interrupted or unconfirmed.
            released = lease.release()
        except BaseException as exc:
            release_error = exc
        report = {"sweep_repair_launch_schema_version": 1,
            "status": "complete" if complete and released is not None else "incomplete",
            "execution_context_digest": context["execution_context_digest"], "counts": counts,
            "failure": failure, "baseline_retrained": False, "scientific_labels_created": False,
            "start": None if start_path is None else {"path": str(start_path), "sha256": sha256_file(start_path)},
            "released_lease": None if released is None else {"token": lease.token, "history_path": str(released)},
            "lease_release_failure": None if release_error is None else {
                "type": type(release_error).__name__, "message": str(release_error),
                "token": lease.token, "active_path": str(lease.path),
                "automatic_recovery_allowed": False}}
        report_path = _twins(roots, Path(REPORT_DIRECTORY) / f"{lease.token}.json", report)
        if release_error is not None:
            raise release_error
    return {**report, "report_path": str(report_path)}
