"""Exact Experiment-1 repair inventory and a narrow execution foundation.

The owner's ``docs/week7_execution_log.md`` brings the already-registered six
twenty-seed validation ladders forward from Week 9. It does not change seeds,
the remaining 24 units' three-seed label policy, or any scientific procedure.
All 150 old Experiment-1 fits remain immutable; only the 102 needed by these
labels are opened by reuse reconciliation. A missing old fit is an integrity
failure, never an invitation to retrain it.

This is a separate sidecar, NOT a generic batch manifest or production launch
adapter. The pure plan, independently pinned reuse ledger, lease-bound durable
start checkpoint, fixed private spawned worker and completed-job reconciliation
are implemented here. The separate ``week7_exp1_repair_launch`` adapter owns
storage-capacity/timing preflight, fixed supervisor handoff, failure journaling
and durable completion/recovery. It must
use the SAME ``COMMON_LEASE_ROOT`` and lease name across Week-7 launchers.
No caller executor, scale, source commit, seed subset or stage override reaches
the worker. Historical sources stay outside the new job directories. Neither
this module nor its checkpoint creates labels; the exact twenty-seed and
ordinary three-seed public label APIs remain distinct.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import constants as K
from ..config import Arm, Config, UnitSpec, seeds_for
from ..durable import _decode_json, atomic_write_json, read_json, sha256_file
from ..runrecord import PROJECT_ROOT
from ..streams import confirmatory_seeds, group_of
from . import batch as B
from . import confirmatory as C
from . import fit_evidence as F
from . import launch as L
from . import monitor as M
from . import preflight as P
from . import repair_label_preflight as RF
from .enumerate_units import (
    arms_for, execution_plan, experiment_1_units, repair_stage_of,
    repair_validation_units,
)
from .supervisor import BatchLease, SUPERVISOR_SCHEMA_VERSION


EXP1_REPAIRS_SCHEMA_VERSION = 1
PLAN_FILE = "week7_exp1_repair_plan.json"
REUSE_FILE = "week7_exp1_repair_reuse.json"
START_DIRECTORY = "week7_exp1_repair_starts"
CONTEXT_FILE = "week7_exp1_execution_context.json"
WORKSPACE_ROOT = PROJECT_ROOT.parent
COMMON_LEASE_ROOT = WORKSPACE_ROOT / "week7-production-control"
COMMON_LEASE_NAME = "week7-production"
HISTORICAL_COMMIT = "f036fe02c4c9fe2fb756d65480186c8e10f7d48e"
HISTORICAL_JOBS_ROOT = WORKSPACE_ROOT / (
    "week6-confirmatory-2026-08-30-attempt-001-output/ac3fa165d5da4536/jobs"
)
HISTORICAL_COPY_ROOT = WORKSPACE_ROOT / (
    "week6-confirmatory-2026-08-30-attempt-001-project-evidence/ac3fa165d5da4536/jobs"
)
# Independent authority pinned in the existing D-156 project record, NOT
# learned from the two current fit trees or a new reuse ledger. Read provenance
# columns only: do not replay the analysis or inspect/derive any outcome.
HISTORICAL_REPORT_PATH = WORKSPACE_ROOT / (
    "week7-analysis-2026-08-31-attempt-001/experiment_1_report.json"
)
HISTORICAL_REPORT_SHA256 = "82b0277af9be843e46ff7d5b53020e23f5eab4e7c68101bffe457b8a2e37f44b"


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False, ensure_ascii=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise ValueError("Experiment-1 repair evidence must be strict JSON") from exc


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    return {**payload, field: hashlib.sha256(_canonical(payload)).hexdigest()}


def _equal(observed: object, expected: object, *, what: str) -> None:
    if _canonical(observed) != _canonical(expected):
        raise ValueError(f"{what} differs from the exact registered evidence")


@dataclass(frozen=True)
class Exp1RepairJob:
    """Physical job with the ACTUAL arm-specific frozen training Config.

    Generic BatchJob.config defaults to an ensemble even for repairs. Keeping
    this sidecar's job type distinct prevents a full-Config manifest from
    recording five members while its repair worker actually trains one.
    """

    unit: UnitSpec
    arm: str
    seed: int
    roles: tuple[str, ...]

    @property
    def stage(self) -> str:
        return self.roles[0]

    @property
    def config(self) -> Config:
        return Config(unit=self.unit, arm=Arm(self.arm), seed=self.seed,
                      stage=self.stage, train=(C.CONFIRMATORY_TRAIN
                      if self.arm == "baseline" else C.REPAIRED_TRAIN))

    @property
    def job_id(self) -> str:
        return self.config.fit_id

    def as_record(self) -> dict[str, Any]:
        cfg = self.config
        return {
            "job_id": self.job_id, "fit_id": cfg.fit_id,
            "run_id": cfg.run_id, "config_id": cfg.config_id,
            "unit_id": cfg.unit_id, "stage": self.stage,
            "seed": self.seed, "arm": self.arm, "roles": list(self.roles),
            "config": cfg.to_dict(),
        }


def registered_exp1_jobs() -> tuple[Exp1RepairJob, ...]:
    """Rederive all 624 physical obligations, including 150 existing fits."""
    if (seeds_for("repair_validation"), seeds_for("exp3_repairs"),
            K.SEEDS_HYPOTHESIS, K.CONFIRMATORY_SEED_BASE) != (20, 3, 5, 1000):
        raise ValueError("Experiment-1 repair execution must retain exact 20/3/5 seeds at base 1000")
    units = experiment_1_units()
    validation = {Config(unit=u).unit_id for u in repair_validation_units()}
    if len(units) != 30 or len({Config(unit=u).unit_id for u in units}) != 30:
        raise ValueError("Experiment-1 must contain its exact 30 unique units")
    if sum(Config(unit=u).unit_id in validation for u in units) != 6:
        raise ValueError("Experiment-1 must contain six canonical validation units")
    jobs = tuple(Exp1RepairJob(f.unit, f.arm, K.CONFIRMATORY_SEED_BASE + f.seed,
                              f.roles) for f in execution_plan(units))
    actual: dict[tuple[str, str, int], Exp1RepairJob] = {}
    for job in jobs:
        key = (job.config.unit_id, job.arm, job.seed)
        if key in actual:
            raise ValueError("Experiment-1 physical obligations are duplicated")
        actual[key] = job
    expected = {}
    for unit in units:
        uid = Config(unit=unit).unit_id
        repair_stage = repair_stage_of(unit)
        if repair_stage != ("repair_validation" if uid in validation else "exp3_repairs"):
            raise ValueError("Experiment-1 repair-label policy drifted")
        if arms_for(unit) != ("baseline", "data_repair", "capacity_extension_repair"):
            raise ValueError("Experiment-1 fixed D-154 repair assignment drifted")
        label_seeds = confirmatory_seeds(seeds_for(repair_stage))
        baseline_seeds = sorted(set(label_seeds) | set(confirmatory_seeds(K.SEEDS_HYPOTHESIS)))
        for seed in baseline_seeds:
            roles = tuple(sorted(
                (["exp1"] if seed in confirmatory_seeds(K.SEEDS_HYPOTHESIS) else [])
                + (["repair_validation"] if uid in validation else [])
            ))
            expected[(uid, "baseline", seed)] = Exp1RepairJob(unit, "baseline", seed, roles)
        for arm in ("data_repair", "capacity_extension_repair"):
            for seed in label_seeds:
                expected[(uid, arm, seed)] = Exp1RepairJob(unit, arm, seed, (repair_stage,))
    _equal({str(k): v.as_record() for k, v in actual.items()},
           {str(k): v.as_record() for k, v in expected.items()}, what="E1 inventory")
    # Per-unit/seed, baseline before data repair before model repair. This is
    # outcome-independent and supplies each newly owed baseline before its arms.
    order = {"baseline": 0, "data_repair": 1, "capacity_extension_repair": 2}
    return tuple(sorted(jobs, key=lambda j: (j.config.unit_id, j.seed, order[j.arm])))


def historical_exp1_jobs(*, label_required_only: bool = False) -> tuple[Exp1RepairJob, ...]:
    """All 150 old baselines, or the exact 102 required for repair labels."""
    if type(label_required_only) is not bool:
        raise ValueError("label_required_only must be an exact boolean")
    jobs = tuple(j for j in registered_exp1_jobs() if j.arm == "baseline"
                 and "exp1" in j.roles)
    if label_required_only:
        jobs = tuple(j for j in jobs if j.seed in confirmatory_seeds(
            seeds_for(repair_stage_of(j.unit))))
    return jobs


def new_exp1_repair_jobs() -> tuple[Exp1RepairJob, ...]:
    """Exactly 474 jobs; source absence cannot enlarge this inventory."""
    return tuple(j for j in registered_exp1_jobs()
                 if not (j.arm == "baseline" and "exp1" in j.roles))


def build_exp1_repair_plan() -> dict[str, Any]:
    """Pure configuration preparation; never open sources or infer a label."""
    jobs = registered_exp1_jobs()
    old = tuple(j for j in jobs if j.arm == "baseline" and "exp1" in j.roles)
    new = tuple(j for j in jobs if j not in old)
    old_required = {j.job_id for j in historical_exp1_jobs(label_required_only=True)}
    labels = []
    for unit in sorted(experiment_1_units(), key=lambda u: Config(unit=u).unit_id):
        stage = repair_stage_of(unit)
        seeds = confirmatory_seeds(seeds_for(stage))
        relevant = tuple(j for j in jobs if j.unit == unit and j.seed in seeds)
        labels.append({
            "unit_id": Config(unit=unit).unit_id,
            "comparison_group_id": group_of(unit, "exp1"),
            "label_stage": stage, "seeds": list(seeds),
            "label_api": ("bu.experiments.label_evidence.build_label_evidence"
                          if stage == "repair_validation" else
                          "bu.experiments.ordinary_label_evidence.build_ordinary_label_evidence"),
            "required_fit_ids": [j.job_id for j in relevant],
            "observed_label": None,
        })
    return _seal({
        "exp1_repairs_schema_version": EXP1_REPAIRS_SCHEMA_VERSION,
        "purpose": "exact_week7_experiment1_repair_inventory",
        "execution_authorized_by_this_file": False,
        "production_launch_adapter": "bu.experiments.week7_exp1_repair_launch",
        "replacement_training_allowed": False,
        "historical_expected_git_commit": HISTORICAL_COMMIT,
        "historical_jobs_root": str(HISTORICAL_JOBS_ROOT),
        "historical_copy_root": str(HISTORICAL_COPY_ROOT),
        "ordering": "unit_id_then_seed_then_baseline_data_model",
        "labels": labels,
        "historical_jobs": [{**j.as_record(), "required_for_label": j.job_id in old_required}
                            for j in old],
        "new_jobs": [j.as_record() for j in new],
        "counts": {
            "units": len(labels),
            "twenty_seed_units": sum(r["label_stage"] == "repair_validation" for r in labels),
            "three_seed_units": sum(r["label_stage"] == "exp3_repairs" for r in labels),
            "registered_physical_fits": len(jobs),
            "historical_fits_preserved": len(old),
            "historical_fits_required_by_labels": len(old_required),
            "new_baseline_fits": sum(j.arm == "baseline" for j in new),
            "new_repair_fits": sum(j.arm != "baseline" for j in new),
            "new_physical_fits": len(new),
            "new_member_model_trainings": sum(j.config.train.ensemble_size for j in new),
        },
    }, "plan_digest")


def validate_exp1_repair_plan(document: object) -> None:
    _equal(document, build_exp1_repair_plan(), what="Experiment-1 repair plan")


def _project_path(path: str | Path, *, directory: bool, existing: bool = True) -> Path:
    """Reject links/junctions before resolving and enforce the owner's boundary."""
    candidate = Path(path).absolute()
    for part in reversed((candidate, *candidate.parents)):
        if not os.path.lexists(part):
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or RF._is_reparse(info):
            raise ValueError(f"project evidence path contains a link/reparse point: {part}")
        if part != candidate and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"project path component is not a directory: {part}")
    workspace = WORKSPACE_ROOT.resolve(strict=True)
    try:
        resolved = candidate.resolve(strict=existing)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"project evidence path is unavailable: {candidate}") from exc
    if resolved == workspace or not resolved.is_relative_to(workspace):
        raise ValueError("all new evidence and source reads must stay inside the project workspace")
    if existing:
        if directory and not resolved.is_dir():
            raise ValueError("expected an existing project evidence directory")
        if not directory:
            RF._regular_file(resolved, what="project evidence")
    return resolved


def write_exp1_repair_plan(directory: str | Path) -> Path:
    document = build_exp1_repair_plan()
    root = _project_path(directory, directory=True)
    return atomic_write_json(root / PLAN_FILE, document)


def load_exp1_repair_plan(path: str | Path) -> dict[str, Any]:
    document = read_json(_project_path(path, directory=False))
    validate_exp1_repair_plan(document)
    return document


def _match_fit(verified: F.VerifiedFitEvidence, job: Exp1RepairJob) -> None:
    if type(verified) is not F.VerifiedFitEvidence:
        raise ValueError("fit loader must return exact VerifiedFitEvidence")
    expected = {
        "unit_id": job.config.unit_id, "config_id": job.config.config_id,
        "fit_id": job.job_id, "execution_run_id": job.config.run_id,
        "execution_stage": job.stage, "arm": job.arm, "seed": job.seed,
        "roles": list(job.roles), "unit": job.config.to_dict()["unit"],
        "n_train": job.config.effective_unit.n_transitions,
        "ensemble_size": job.config.train.ensemble_size,
    }
    observed = {name: getattr(verified, name) for name in expected if name not in {"roles", "unit"}}
    observed.update(roles=list(verified.roles), unit=Config(unit=verified.unit).to_dict()["unit"])
    _equal(observed, expected, what="source fit identity/roles/frozen training")


def _historical_execution_digests() -> dict[str, str]:
    """Extract source pins from the independently SHA-bound D-156 report.

    This is an artifact-only provenance read, not a scientific replay. Full
    Config/roles and the exact 150 old identities are checked without touching
    any source directory or any outcome field. The 102-source ledger format
    stays unchanged; its existing execution_digest field gains this external
    acceptance check, including when an already-prepared ledger is reopened.
    """
    path = _project_path(HISTORICAL_REPORT_PATH, directory=False)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HISTORICAL_REPORT_SHA256:
        raise ValueError("D-156 historical report differs from its independently fixed SHA256")
    doc = _decode_json(raw, source=str(path))
    if (type(doc) is not dict or type(doc.get("schema_version")) is not int
            or doc["schema_version"] != 1 or doc.get("kind") != "experiment_1_coefficient_report"
            or type(doc.get("provenance")) is not dict
            or doc["provenance"].get("expected_fit_commit") != HISTORICAL_COMMIT):
        raise ValueError("D-156 historical report has incorrect schema or independent source commit")
    jobs = {j.job_id: j for j in historical_exp1_jobs()}
    rows = doc.get("rows")
    if type(rows) is not list or len(rows) != len(jobs):
        raise ValueError("D-156 provenance requires exactly the original 150 source identities")
    pins = {}
    for row in rows:
        if type(row) is not dict or type(row.get("fit_id")) is not str:
            raise ValueError("D-156 source row must carry a physical fit identity")
        job = jobs.get(row["fit_id"])
        if job is None or job.job_id in pins:
            raise ValueError("D-156 source identity is unknown or duplicated")
        expected = {"fit_id": job.job_id, "unit_id": job.config.unit_id,
                    "config_id": job.config.config_id, "seed": job.seed,
                    "execution_stage": job.stage, "execution_run_id": job.config.run_id,
                    "roles": list(job.roles), "config": job.config.to_dict()}
        _equal({k: row.get(k) for k in expected}, expected, what="D-156 source Config/identity/roles")
        if (type(row.get("source_path")) is not str
                or Path(row["source_path"]) != HISTORICAL_JOBS_ROOT / job.job_id):
            raise ValueError("D-156 source path is not the fixed original historical job path")
        pins[job.job_id] = L._lower_sha256(row.get("execution_digest"), what="D-156 execution digest")
    return pins


def _source_pair(job: Exp1RepairJob, source: Path, copy: Path, *, commit: str,
                 expected_execution_digest: str | None = None):
    source = _project_path(source, directory=True)
    copy = _project_path(copy, directory=True)
    if P._overlap(source, copy) or os.path.samefile(source, copy):
        raise ValueError("source and independent copy alias or overlap")
    for root in (source, copy):
        _plain_tree(root)
    # Both scientific loader and full-tree verification apply, with different
    # roles: execution_digest binds the fit, copy digest proves independent IO.
    before = B._copy_evidence_digest(source, copy)
    left = F.load_fit_evidence(source, expected_git_commit=commit)
    right = F.load_fit_evidence(copy, expected_git_commit=commit)
    for fit in (left, right):
        _match_fit(fit, job)
    _equal(left.execution_digest, right.execution_digest, what="source/copy execution digest")
    if expected_execution_digest is not None:
        _equal(left.execution_digest, L._lower_sha256(expected_execution_digest,
               what="independent historical execution digest"), what="D-156 original execution digest")
    after = B._copy_evidence_digest(source, copy)
    if before != after:
        raise ValueError("source or independent copy changed during verification")
    return left, {
        "job": job.as_record(), "source_path": str(source), "copy_path": str(copy),
        "expected_git_commit": commit, "execution_digest": left.execution_digest,
        "source_tree_digest": B._job_tree_digest(source),
        "copy_evidence_digest": after,
    }


def _plain_tree(root):
    # The older batch walker does not catch every Windows reparse form. Reject
    # them before either hashing OR transporting any descendant payload bytes.
    _project_path(root, directory=True)
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            candidate = Path(current) / name
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode) or RF._is_reparse(info):
                raise ValueError("source tree contains a linked/reparse descendant")
    B._regular_tree_inventory(root)


def build_exp1_reuse_ledger() -> dict[str, Any]:
    """Open ONLY the 102 required historical source/copy pairs; never train."""
    historical_pins = _historical_execution_digests()
    rows = []
    for job in historical_exp1_jobs(label_required_only=True):
        _, row = _source_pair(job, HISTORICAL_JOBS_ROOT / job.job_id,
                              HISTORICAL_COPY_ROOT / job.job_id, commit=HISTORICAL_COMMIT,
                              expected_execution_digest=historical_pins[job.job_id])
        rows.append(row)
    return _seal({
        "exp1_reuse_schema_version": EXP1_REPAIRS_SCHEMA_VERSION,
        "plan_digest": build_exp1_repair_plan()["plan_digest"],
        "replacement_training_allowed": False, "sources": rows,
    }, "reuse_digest")


def write_exp1_reuse_ledger(directory: str | Path) -> Path:
    root = _project_path(directory, directory=True)
    document = build_exp1_reuse_ledger()  # Entire verification before any write.
    return atomic_write_json(root / REUSE_FILE, document)


def load_exp1_reuse_ledger(path: str | Path) -> dict[str, Any]:
    document = read_json(_project_path(path, directory=False))
    _equal(document, build_exp1_reuse_ledger(), what="historical reuse ledger")
    return document


def _metadata_ledger(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Private child lookup: all rows were reconciled at checkpoint creation.

    The child still reopens its OWN actual seed baseline and its copy below.
    It does not reopen all 102 unrelated fits on each of 474 child launches.
    """
    path = _project_path(path, directory=False)
    if sha256_file(path) != expected_sha256:
        raise ValueError("reuse ledger changed after the durable start checkpoint")
    doc = read_json(path)
    rows = doc.get("sources") if type(doc) is dict else None
    jobs = historical_exp1_jobs(label_required_only=True)
    if type(rows) is not list or len(rows) != len(jobs):
        raise ValueError("reuse ledger must name exactly 102 required old baselines")
    historical_pins = _historical_execution_digests()
    expected_rows = []
    for row, job in zip(rows, jobs, strict=True):
        L._strict_keys(row, {"job", "source_path", "copy_path", "expected_git_commit",
                            "execution_digest", "source_tree_digest", "copy_evidence_digest"},
                       what="historical source reference")
        digests = {k: L._lower_sha256(row[k], what=k) for k in
                   ("execution_digest", "source_tree_digest", "copy_evidence_digest")}
        _equal(digests["execution_digest"], historical_pins[job.job_id],
               what="reuse ledger D-156 original execution digest")
        expected_rows.append({
            "job": job.as_record(),
            "source_path": str((HISTORICAL_JOBS_ROOT / job.job_id).resolve()),
            "copy_path": str((HISTORICAL_COPY_ROOT / job.job_id).resolve()),
            "expected_git_commit": HISTORICAL_COMMIT, **digests,
        })
    _equal(doc, _seal({
        "exp1_reuse_schema_version": EXP1_REPAIRS_SCHEMA_VERSION,
        "plan_digest": build_exp1_repair_plan()["plan_digest"],
        "replacement_training_allowed": False, "sources": expected_rows,
    }, "reuse_digest"), what="reuse ledger metadata")
    return doc


def _roots(output_root, staging_root, sync_root, ledger_path) -> dict[str, Path]:
    roots = {name: _project_path(path, directory=True) for name, path in
             (("output", output_root), ("staging", staging_root), ("sync", sync_root))}
    protected = [HISTORICAL_JOBS_ROOT.resolve(), HISTORICAL_COPY_ROOT.resolve(),
                 HISTORICAL_REPORT_PATH.parent.resolve(), COMMON_LEASE_ROOT.resolve()]
    for index, left in enumerate(roots.values()):
        for right in tuple(roots.values())[index + 1:] + tuple(protected):
            if P._overlap(left, right):
                raise ValueError("execution roots overlap each other or protected historical/lease roots")
        if Path(ledger_path).resolve().is_relative_to(left):
            raise ValueError("reuse ledger must be outside execution roots")
    L._validate_same_volume_staging(roots["output"], roots["staging"])
    return roots


def _environment(expected_git_commit: str) -> dict[str, Any]:
    commit = F._validate_expected_git_commit(expected_git_commit)
    state, versions, pins = P._verify_environment()
    if state.commit != commit:
        raise ValueError("current clean Git commit differs from independently expected launch commit")
    if (C.CONFIRMATORY_DEVICE, C.CONFIRMATORY_THREADS, C.CONFIRMATORY_INTEROP_THREADS) != ("cpu", 4, 4):
        raise ValueError("Experiment-1 repair foundation requires the frozen CPU 4/4 route")
    device = P._verify_device("cpu")
    return {"git_commit": commit, "versions": versions, "pins": pins,
            "device": device, "num_threads": 4, "num_interop_threads": 4}


def _lease_record(token: str) -> dict[str, Any]:
    if type(token) is not str or re.fullmatch(r"[0-9a-f]{32}", token) is None:
        raise ValueError("common Week-7 lease token must be exact 32-hex")
    root = _project_path(COMMON_LEASE_ROOT, directory=True)
    path, digest = M._load_active_lease(
        root / "leases" / f"{COMMON_LEASE_NAME}.lease.json", output_root=root,
        lease_name=COMMON_LEASE_NAME, lease_token=token,
    )
    return {"path": str(path), "sha256": digest, "name": COMMON_LEASE_NAME,
            "token": token, "started_at": read_json(path)["timestamp_utc"]}


def _historical_lease_record(token: str) -> dict[str, Any]:
    """Reconstruct an actual old lease, never infer release from elapsed age."""
    if type(token) is not str or re.fullmatch(r"[0-9a-f]{32}", token) is None:
        raise ValueError("prior lease token must be exact 32-hex")
    root = _project_path(COMMON_LEASE_ROOT, directory=True)
    active = root / "leases" / f"{COMMON_LEASE_NAME}.lease.json"
    history = root / "leases" / "history" / f"{COMMON_LEASE_NAME}.{token}.released.json"
    if active.exists() and read_json(_project_path(active, directory=False)).get("token") == token:
        return _lease_record(token)
    path = _project_path(history, directory=False)
    record = L._strict_keys(read_json(path), {"schema_version", "lease_name", "pid", "token",
                                            "timestamp", "timestamp_utc"}, what="prior released lease")
    if (type(record["schema_version"]) is not int or record["schema_version"] != SUPERVISOR_SCHEMA_VERSION
            or record["lease_name"] != COMMON_LEASE_NAME or record["token"] != token
            or type(record["pid"]) is not int or record["pid"] <= 0):
        raise ValueError("prior lease history does not prove the exact recorded owner")
    L._positive_number(record["timestamp"], what="prior lease timestamp")
    M._require_timestamp(record["timestamp_utc"], what="prior lease UTC timestamp")
    return {"path": str(active), "sha256": sha256_file(path), "name": COMMON_LEASE_NAME,
            "token": token, "started_at": record["timestamp_utc"]}


def _execution_context(start: dict[str, Any]) -> dict[str, Any]:
    """Stable across leases; exact plan, source pins, commit, roots and timeout."""
    payload = {key: value for key, value in start.items()
               if key not in {"lease", "checkpoint_digest", "execution_context_digest"}}
    return _seal(payload, "execution_context_digest")


def write_exp1_repair_start_checkpoint(
    *, reuse_ledger_path: str | Path, expected_git_commit: str,
    output_root: str | Path, staging_root: str | Path, sync_root: str | Path,
    attempt_timeout_seconds: float, lease: BatchLease, preflight_report: str | Path,
) -> Path:
    """Persist an independent, lease-bound start prerequisite; launch nothing.

    Caller already holds the fixed common lease and remains responsible for
    token-only release in finally. The separate launch adapter's full readiness
    validation is mandatory here; writing a checkpoint alone launches nothing.
    """
    timeout = L._positive_number(attempt_timeout_seconds, what="attempt_timeout_seconds")
    if type(lease) is not BatchLease or lease._released:
        raise ValueError("start checkpoint requires an exact active common BatchLease")
    _project_path(lease.path, directory=False)
    history = _project_path(lease.history_dir, directory=True, existing=False)
    if (lease.name != COMMON_LEASE_NAME
            or history != (COMMON_LEASE_ROOT / "leases" / "history").resolve()):
        raise ValueError("start lease name/history must be the fixed common workspace control paths")
    if lease.path.resolve() != (COMMON_LEASE_ROOT / "leases" / f"{COMMON_LEASE_NAME}.lease.json").resolve():
        raise ValueError("start checkpoint must use the shared workspace Week-7 lease")
    ledger_path = _project_path(reuse_ledger_path, directory=False)
    roots = _roots(output_root, staging_root, sync_root, ledger_path)
    environment = _environment(expected_git_commit)
    # Lazy import avoids an import cycle. This required preflight is not an
    # optional flag: the fixed worker cannot be enabled by writing only the
    # lower-level foundation documents, omitting the timing/storage gate.
    from . import week7_exp1_repair_launch as RL
    ready = RL.validate_exp1_repair_preflight(preflight_report, output_root=output_root,
        sync_root=sync_root, expected_git_commit=expected_git_commit)
    if (ready.report["attempt_timeout_seconds"] != timeout
            or Path(ready.report["inputs"]["reuse_ledger"]["path"]).resolve() != ledger_path
            or ready.roots["staging"] != roots["staging"]):
        raise ValueError("start timeout/reuse/staging differ from the validated preflight")
    preflight = {"path": str(ready.report_path), "sha256": ready.report_sha256,
                 "binding_sha256": ready.report["binding_sha256"]}
    ledger_sha = sha256_file(ledger_path)
    ledger = load_exp1_reuse_ledger(ledger_path)
    if sha256_file(ledger_path) != ledger_sha:
        raise ValueError("reuse ledger changed during start verification")
    lease_row = _lease_record(lease.token)
    if read_json(Path(lease_row["path"]))["pid"] != os.getpid():
        raise ValueError("start checkpoint lease must belong to this launcher process")
    payload = {
        "exp1_repair_start_schema_version": EXP1_REPAIRS_SCHEMA_VERSION,
        "purpose": "source_verified_exp1_repair_start",
        "plan_digest": build_exp1_repair_plan()["plan_digest"],
        "preflight": preflight,
        "reuse_ledger": {"path": str(ledger_path), "sha256": ledger_sha,
                         "reuse_digest": ledger["reuse_digest"]},
        "environment": environment, "roots": {k: str(v) for k, v in roots.items()},
        "attempt_timeout_seconds": timeout, "lease": lease_row,
        "fixed_worker": "bu.experiments.week7_exp1_repairs._fit_worker",
        "supervisor_required": "bu.experiments.supervisor.run_isolated_attempt",
        "automatic_retry_allowed": False,
    }
    context = _execution_context(payload)
    document = _seal({**payload, "execution_context_digest": context["execution_context_digest"]},
                     "checkpoint_digest")
    for name in ("sync", "output"):
        atomic_write_json(roots[name] / CONTEXT_FILE, context)
    _same_file_copy(roots["output"] / CONTEXT_FILE, roots["sync"] / CONTEXT_FILE)
    paths = []
    for name in ("sync", "output"):
        directory = RF.ensure_regular_child_directory(roots[name], START_DIRECTORY)
        paths.append(atomic_write_json(directory / f"{lease.token}.json", document))
    _same_file_copy(paths[1], paths[0])
    return paths[1]


def _same_file_copy(source: Path, copy: Path) -> None:
    for path in (source, copy):
        _project_path(path, directory=False)
    if RF._same_file_identity(source, copy) or source.read_bytes() != copy.read_bytes():
        raise ValueError("start prerequisite must have an independent byte-identical durable copy")


def _load_start(path: str | Path, *, expected_sha256: str, expected_git_commit: str):
    """Execution-only boundary: current clean execution commit and LIVE lease."""
    return _read_start(path, expected_sha256=expected_sha256,
                       expected_git_commit=expected_git_commit, released=False)


def _no_active_week7_lease() -> None:
    root = _project_path(COMMON_LEASE_ROOT, directory=True)
    if os.path.lexists(root / "leases" / f"{COMMON_LEASE_NAME}.lease.json"):
        raise ValueError("released-source reading requires no active common Week-7 lease")


def _released_environment(expected_git_commit: str) -> dict[str, Any]:
    """Validate old execution settings without impersonating the old commit.

    The reader must use a clean pinned environment, but may have a different
    Git commit (which the finalizer separately pins). Original provenance is
    bound to the independent checkpoint SHA and expected execution commit.
    """
    commit = F._validate_expected_git_commit(expected_git_commit)
    _, versions, pins = P._verify_environment()
    if (C.CONFIRMATORY_DEVICE, C.CONFIRMATORY_THREADS, C.CONFIRMATORY_INTEROP_THREADS) != ("cpu", 4, 4):
        raise ValueError("released execution evidence requires the frozen CPU 4/4 route")
    return {"git_commit": commit, "versions": versions, "pins": pins,
            "device": P._verify_device("cpu"), "num_threads": 4, "num_interop_threads": 4}


def _read_start(path, *, expected_sha256, expected_git_commit, released):
    if released:
        _no_active_week7_lease()
    path = _project_path(path, directory=False)
    if sha256_file(path) != L._lower_sha256(expected_sha256, what="checkpoint SHA256"):
        raise ValueError("start checkpoint changed after fixed worker dispatch")
    doc = L._strict_keys(read_json(path), {
        "exp1_repair_start_schema_version", "purpose", "plan_digest", "reuse_ledger",
        "environment", "roots", "attempt_timeout_seconds", "lease", "fixed_worker",
        "supervisor_required", "automatic_retry_allowed", "checkpoint_digest", "execution_context_digest",
        "preflight",
    }, what="Experiment-1 repair start checkpoint")
    rr = L._strict_keys(doc["roots"], {"output", "staging", "sync"}, what="checkpoint roots")
    lr = L._strict_keys(doc["reuse_ledger"], {"path", "sha256", "reuse_digest"}, what="checkpoint ledger")
    roots = _roots(rr["output"], rr["staging"], rr["sync"], lr["path"])
    ledger = _metadata_ledger(Path(lr["path"]), lr["sha256"])
    preflight = L._strict_keys(doc["preflight"], {"path", "sha256", "binding_sha256"},
                              what="required production preflight binding")
    preflight_path = _project_path(preflight["path"], directory=False)
    if sha256_file(preflight_path) != L._lower_sha256(preflight["sha256"], what="preflight SHA256"):
        raise ValueError("production preflight changed after the durable start checkpoint")
    preflight_document = read_json(preflight_path)
    if type(preflight_document) is not dict or preflight_document.get("binding_sha256") != L._lower_sha256(
        preflight["binding_sha256"], what="preflight source/timing binding"
    ):
        raise ValueError("production preflight source/timing binding changed")
    lease = L._strict_keys(doc["lease"], {"path", "sha256", "name", "token", "started_at"},
                           what="checkpoint lease")
    current_lease = (_historical_lease_record(lease["token"]) if released
                     else _lease_record(lease["token"]))
    expected = _seal({
        "exp1_repair_start_schema_version": EXP1_REPAIRS_SCHEMA_VERSION,
        "purpose": "source_verified_exp1_repair_start",
        "plan_digest": build_exp1_repair_plan()["plan_digest"],
        "preflight": {**preflight, "path": str(preflight_path)},
        "reuse_ledger": {"path": str(Path(lr["path"]).resolve()), "sha256": lr["sha256"],
                         "reuse_digest": ledger["reuse_digest"]},
        "environment": (_released_environment(expected_git_commit) if released
                        else _environment(expected_git_commit)),
        "roots": {k: str(v) for k, v in roots.items()},
        "attempt_timeout_seconds": L._positive_number(doc["attempt_timeout_seconds"], what="timeout"),
        "lease": current_lease,
        "fixed_worker": "bu.experiments.week7_exp1_repairs._fit_worker",
        "supervisor_required": "bu.experiments.supervisor.run_isolated_attempt",
        "automatic_retry_allowed": False,
    }, "checkpoint_digest")
    context = _execution_context(expected)
    expected = _seal({**{k: v for k, v in expected.items() if k != "checkpoint_digest"},
                      "execution_context_digest": context["execution_context_digest"]}, "checkpoint_digest")
    _equal(doc, expected, what="lease-bound start checkpoint")
    local = roots["output"] / START_DIRECTORY / f"{current_lease['token']}.json"
    durable = roots["sync"] / START_DIRECTORY / local.name
    if path != local:
        raise ValueError("worker must use the prescribed local start checkpoint")
    _same_file_copy(local, durable)
    _same_file_copy(roots["output"] / CONTEXT_FILE, roots["sync"] / CONTEXT_FILE)
    _equal(read_json(roots["output"] / CONTEXT_FILE), context, what="stable execution context")
    return doc, ledger, roots


def _new_job(job_id: str) -> Exp1RepairJob:
    jobs = [j for j in new_exp1_repair_jobs() if j.job_id == job_id]
    if type(job_id) is not str or len(jobs) != 1:
        raise ValueError("worker job is not one of the exact 474 NEW Experiment-1 fits")
    return jobs[0]


def _result_record(job, verified, *, commit, checkpoint_digest, binding, execution_context_digest):
    return {"exp1_repair_result_schema_version": EXP1_REPAIRS_SCHEMA_VERSION,
            "job": job.as_record(), "expected_git_commit": commit,
            "checkpoint_digest": checkpoint_digest,
            "execution_context_digest": execution_context_digest,
            "fit_evidence_digest": verified.execution_digest, "baseline_source": binding}


def _verify_prior_start(checkpoint_digest, current, roots):
    """Require exactly one genuine independently copied start and lease record."""
    L._lower_sha256(checkpoint_digest, what="prior launch checkpoint digest")
    matches = []
    for path in (roots["output"] / START_DIRECTORY).glob("*.json"):
        doc = read_json(_project_path(path, directory=False))
        if type(doc) is not dict or doc.get("checkpoint_digest") != checkpoint_digest:
            continue
        if not re.fullmatch(r"[0-9a-f]{32}\.json", path.name):
            raise ValueError("prior start has a noncanonical lease-token filename")
        lease = _historical_lease_record(path.stem)
        payload = {k: v for k, v in current.items() if k not in {"lease", "checkpoint_digest"}}
        expected = _seal({**payload, "lease": lease}, "checkpoint_digest")
        _equal(doc, expected, what="prior start same stable context and actual archived lease")
        _same_file_copy(path, roots["sync"] / START_DIRECTORY / path.name)
        matches.append(path)
    if len(matches) != 1:
        raise ValueError("completed fit must bind exactly one actual independently copied prior start")


def _baseline(job: Exp1RepairJob, ledger, roots, commit, current):
    baseline = next(j for j in registered_exp1_jobs()
                    if j.unit == job.unit and j.seed == job.seed and j.arm == "baseline")
    if "exp1" in baseline.roles:
        row = next(r for r in ledger["sources"] if r["job"]["job_id"] == baseline.job_id)
        verified, actual = _source_pair(baseline, Path(row["source_path"]), Path(row["copy_path"]),
                                        commit=HISTORICAL_COMMIT,
                                        expected_execution_digest=row["execution_digest"])
        _equal(actual, row, what="independently pinned historical seed baseline")
    else:
        verified, actual = _source_pair(baseline, roots["output"] / "jobs" / baseline.job_id,
                                        roots["sync"] / "jobs" / baseline.job_id, commit=commit)
        result = read_json(_project_path(Path(actual["source_path"]) / "job_result.json", directory=False))
        _verify_prior_start(result.get("checkpoint_digest"), current, roots)
        _equal(result, _result_record(baseline, verified, commit=commit,
                                      checkpoint_digest=result["checkpoint_digest"], binding=None,
                                      execution_context_digest=current["execution_context_digest"]),
               what="new seed baseline completed under this stable execution context")
    return verified, actual


def _fit_worker(attempt_dir: Path, payload: Any) -> dict[str, Any]:
    """Fixed, private fresh-process callback; no arbitrary source or scale."""
    row = L._strict_keys(payload, {"checkpoint_path", "checkpoint_sha256", "expected_git_commit", "job"},
                         what="Experiment-1 repair worker payload")
    job_record = row["job"]
    if type(job_record) is not dict:
        raise ValueError("worker job must be an exact registered record")
    job = _new_job(job_record.get("job_id"))
    _equal(job_record, job.as_record(), what="worker full Config and roles")
    doc, ledger, roots = _load_start(row["checkpoint_path"], expected_sha256=row["checkpoint_sha256"],
                                     expected_git_commit=row["expected_git_commit"])
    attempt = _project_path(attempt_dir, directory=True)
    if attempt.parent != roots["staging"] / "staging" or not re.fullmatch(
        re.escape(job.job_id) + r"\.[0-9a-f]{32}", attempt.name
    ):
        raise ValueError("worker attempt must be the supervisor's prescribed isolated staging child")
    attempt_record = L._strict_keys(read_json(_project_path(attempt / "attempt.json", directory=False)),
                                   {"schema_version", "job_id", "attempt_token", "parent_pid",
                                    "started_at", "timeout_seconds"}, what="supervisor attempt")
    if (type(attempt_record["schema_version"]) is not int
            or attempt_record["schema_version"] != SUPERVISOR_SCHEMA_VERSION
            or attempt_record.get("job_id") != job.job_id
            or attempt_record.get("attempt_token") != attempt.name.rsplit(".", 1)[1]
            or type(attempt_record.get("parent_pid")) is not int
            or attempt_record["parent_pid"] == os.getpid()
            or attempt_record["parent_pid"] != read_json(Path(doc["lease"]["path"]))["pid"]
            or type(attempt_record.get("timeout_seconds")) not in {int, float}
            or attempt_record["timeout_seconds"] != doc["attempt_timeout_seconds"]):
        raise ValueError("worker attempt lacks the exact timeout/fresh-process/lease-owner binding")
    M._require_timestamp(attempt_record["started_at"], what="supervisor attempt start")
    for directory in (roots["staging"] / "staging", roots["staging"] / "quarantine"):
        if directory.exists():
            _project_path(directory, directory=True)
            if any(path != attempt for path in directory.glob(f"{job.job_id}.*")):
                raise ValueError("prior attempt evidence exists; automatic retry is prohibited")
    for root in (roots["output"], roots["sync"]):
        if os.path.lexists(root / "jobs" / job.job_id):
            raise ValueError("existing or partial job must be reconciled, never retrained")
    scale, binding = None, None
    if job.arm != "baseline":
        baseline, binding = _baseline(job, ledger, roots, row["expected_git_commit"], doc)
        scale = baseline.scale
    F.run_confirmatory_fit(job.unit, arm=job.arm, seed=job.seed, out_dir=attempt,
                           scale=scale, expected_git_commit=row["expected_git_commit"])
    verified = F.load_fit_evidence(attempt, expected_git_commit=row["expected_git_commit"])
    _match_fit(verified, job)
    if binding is not None:
        baseline_after, after = _baseline(job, ledger, roots, row["expected_git_commit"], doc)
        _equal(after, binding, what="baseline source after repair execution")
        _equal(verified.scale.as_row(), baseline_after.scale.as_row(), what="repair baseline scale")
        _equal(verified.evaluation_pool_digest, baseline_after.evaluation_pool_digest,
               what="Experiment-1 repair evaluation pool")
    return _result_record(job, verified, commit=row["expected_git_commit"],
                          checkpoint_digest=doc["checkpoint_digest"], binding=binding,
                          execution_context_digest=doc["execution_context_digest"])


def reconcile_completed_exp1_job(
    job_id: str, *, checkpoint_path: str | Path, checkpoint_sha256: str,
    expected_git_commit: str,
) -> dict[str, Any] | None:
    """Read-only recovery foundation: missing both is pending, partial refuses.

    No retry or copying is performed here. A local-only complete job needs a
    durable-sync recovery step in the parent, not a fresh training attempt.
    Old results retain their original lease-bound checkpoint, whose complete
    start and actual active/released lease history must verify. The stable
    execution context must be identical to this launch, so a new lease does
    not rewrite an old fit or silently adopt a different procedure.
    """
    job = _new_job(job_id)
    doc, ledger, roots = _load_start(checkpoint_path, expected_sha256=checkpoint_sha256,
                                   expected_git_commit=expected_git_commit)
    return _completed_source_pair(job, doc, ledger, roots, expected_git_commit)


def _completed_source_pair(job, doc, ledger, roots, expected_git_commit):
    local = roots["output"] / "jobs" / job.job_id
    durable = roots["sync"] / "jobs" / job.job_id
    exists = [os.path.lexists(path) for path in (local, durable)]
    if not any(exists):
        return None
    if not all(exists):
        raise ValueError("partial local/durable job requires sync recovery; retraining is prohibited")
    _, source = _source_pair(job, local, durable, commit=expected_git_commit)
    _local_completed(job, doc, ledger, roots, expected_git_commit)
    return source


def _local_completed(job, doc, ledger, roots, expected_git_commit):
    local = _project_path(roots["output"] / "jobs" / job.job_id, directory=True)
    # Inventory first: a complete fit sidecar is not permission to transport
    # an extra linked or special file hidden elsewhere in the job directory.
    _plain_tree(local)
    verified = F.load_fit_evidence(local, expected_git_commit=expected_git_commit)
    _match_fit(verified, job)
    result = L._strict_keys(read_json(_project_path(local / "job_result.json", directory=False)), {
        "exp1_repair_result_schema_version", "job", "expected_git_commit", "checkpoint_digest",
        "fit_evidence_digest", "baseline_source", "execution_context_digest",
    }, what="completed Experiment-1 repair result")
    binding = None
    if job.arm != "baseline":
        baseline, binding = _baseline(job, ledger, roots, expected_git_commit, doc)
        _equal(verified.scale.as_row(), baseline.scale.as_row(), what="recovered repair scale")
        _equal(verified.evaluation_pool_digest, baseline.evaluation_pool_digest, what="recovered repair pool")
    _verify_prior_start(result["checkpoint_digest"], doc, roots)
    _equal(result, _result_record(job, verified, commit=expected_git_commit,
                                  checkpoint_digest=result["checkpoint_digest"], binding=binding,
                                  execution_context_digest=doc["execution_context_digest"]),
           what="completed job result bound to the stable context and actual prior start")
    return {"result": result, "source_tree_digest": B._job_tree_digest(local),
            "execution_digest": verified.execution_digest}


def validate_local_completed_exp1_job(
    job_id: str, *, checkpoint_path: str | Path, checkpoint_sha256: str,
    expected_git_commit: str,
) -> dict[str, Any]:
    """Verify a complete local result before sync-only recovery; never train."""
    job = _new_job(job_id)
    doc, ledger, roots = _load_start(checkpoint_path, expected_sha256=checkpoint_sha256,
                                   expected_git_commit=expected_git_commit)
    return _local_completed(job, doc, ledger, roots, expected_git_commit)


def load_released_exp1_source_inventory(
    *, checkpoint_path: str | Path, checkpoint_sha256: str,
    expected_execution_commit: str,
) -> dict[str, Any]:
    """Read-only source inventory for finalization AFTER the production lease.

    No active common lease is permitted. The supplied checkpoint SHA, original
    execution commit, actual released lease history, independent start/context
    copies and original per-fit starts/results remain mandatory. This returns
    exact historical102 plus completed new sources; jobs missing on both sides
    are explicitly pending, never evidence that the whole launch is complete.
    A partial source/copy refuses: this API does not create directories, heal
    copies, rewrite old results, replay outcomes, acquire a lease or train.

    A different current clean pinned finalizer commit is allowed. This API is
    deliberately separate from _load_start: private workers still REQUIRE the
    active lease and the current independently expected execution commit.
    """
    doc, ledger, roots = _read_start(checkpoint_path, expected_sha256=checkpoint_sha256,
        expected_git_commit=expected_execution_commit, released=True)
    _equal(load_exp1_reuse_ledger(doc["reuse_ledger"]["path"]), ledger,
           what="released checkpoint full historical source inventory")
    sources, pending = list(ledger["sources"]), []
    for job in new_exp1_repair_jobs():
        source = _completed_source_pair(job, doc, ledger, roots, expected_execution_commit)
        if source is None:
            pending.append(job.job_id)
        else:
            sources.append(source)
    # The finalizer performs its own independent before/after inventory check;
    # this boundary also guards historical source drift and a resumed producer.
    _equal(load_exp1_reuse_ledger(doc["reuse_ledger"]["path"]), ledger,
           what="historical sources after released inventory verification")
    after, _, _ = _read_start(checkpoint_path, expected_sha256=checkpoint_sha256,
        expected_git_commit=expected_execution_commit, released=True)
    _equal(after, doc, what="released checkpoint after source inventory verification")
    return {"start": doc, "ledger": ledger, "roots": roots,
            "sources": sorted(sources, key=lambda row: row["job"]["job_id"]),
            "pending_new_fit_ids": sorted(pending)}
