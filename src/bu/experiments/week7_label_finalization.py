"""Exact E1 evidence export and label finalization; no fitting capability.

The independently pinned Week-7 repair plan defines all thirty labels: six
twenty-seed validation conditions and twenty-four ordinary three-seed ones.
All 150 old fits remain untouched; only the 102 needed by these labels are
read. New-job authority comes from week7_exp1_repairs, not invented results.

Each label gets descendant source trees in a NEW export root and a separate
NEW durable-copy root. Source originals, existing independent copies and both
exports are reverified before/after use. Existing paths, links, reparse points,
hard links, divergent copies and source substitution fail closed. Partial
exports from a failed attempt remain evidence, never overwritten on a retry.

Missing jobs are pending. An empty required baseline failure set is explicitly
blocked, not an ambiguous/undiagnosed observation. Neither state creates a
label. The manifest reports observed counts separately and never estimates a
Week-8 exclusion rate. Existing label APIs, role identities and science remain
unchanged; independent commit/digest pins wrap the legacy twenty-seed reader.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .. import constants as K
from ..durable import atomic_write_bytes, atomic_write_json, read_json, sha256_file
from . import batch as B
from . import fit_evidence as F
from . import label_evidence as L
from . import ordinary_label_evidence as O
from . import repair_label_preflight as RF
from . import week7_exp1_repairs as W


FINALIZATION_SCHEMA_VERSION = 1
MANIFEST_FILE = "week7_exp1_label_finalization.json"
UNIT_STATUS_FILE = "label_status.json"
LABEL_FILE = "label_evidence.json"
SOURCE_DIRECTORY = "sources"


@dataclass(frozen=True)
class Exp1FinalizationInputs:
    """Independent inputs retained outside the finalization artifact itself."""

    plan_path: str | Path
    plan_sha256: str
    reuse_ledger_path: str | Path
    reuse_ledger_sha256: str
    checkpoint_path: str | Path
    checkpoint_sha256: str
    expected_execution_commit: str
    expected_finalizer_commit: str


def _same(actual: object, expected: object, what: str) -> None:
    W._equal(actual, expected, what=what)


def _pin_file(path: str | Path, digest: str) -> Path:
    target = W._project_path(path, directory=False)
    if sha256_file(target) != W.L._lower_sha256(digest, what="independent input SHA256"):
        raise ValueError("finalization input differs from its independent SHA256")
    return target


def _finalizer_environment(commit: str) -> dict[str, Any]:
    expected = F._validate_expected_git_commit(commit)
    state, versions, pins = W.P._verify_environment()
    if state.commit != expected or state.dirty or not state.trustworthy:
        raise ValueError("finalization requires the independently expected clean trustworthy code commit")
    return {"git_commit": expected, "branch": state.branch, "packages": versions, "exact_pins": pins}


def _collect_sources(inputs: Exp1FinalizationInputs) -> dict[str, Any]:
    """Delegate released execution/result authority to W; never synthesize it."""
    if type(inputs) is not Exp1FinalizationInputs:
        raise ValueError("inputs must be exact Exp1FinalizationInputs with independent pins")
    F._validate_expected_git_commit(inputs.expected_execution_commit)
    plan_path = _pin_file(inputs.plan_path, inputs.plan_sha256)
    ledger_path = _pin_file(inputs.reuse_ledger_path, inputs.reuse_ledger_sha256)
    checkpoint = _pin_file(inputs.checkpoint_path, inputs.checkpoint_sha256)
    plan = W.load_exp1_repair_plan(plan_path)
    ledger = W.load_exp1_reuse_ledger(ledger_path)
    verified = W.load_released_exp1_source_inventory(
        checkpoint_path=checkpoint, checkpoint_sha256=inputs.checkpoint_sha256,
        expected_execution_commit=inputs.expected_execution_commit,
    )
    start, bound_ledger, roots = verified["start"], verified["ledger"], verified["roots"]
    _same(bound_ledger, ledger, "checkpoint-bound historical reuse inventory")
    if (Path(start["reuse_ledger"]["path"]).resolve() != ledger_path
            or start["reuse_ledger"]["sha256"] != inputs.reuse_ledger_sha256):
        raise ValueError("checkpoint does not bind the independently supplied reuse ledger")
    _same(plan["plan_digest"], start["plan_digest"], "checkpoint-bound exact E1 plan")
    sources = verified["sources"]
    pending = verified["pending_new_fit_ids"]
    if type(sources) is not list or type(pending) is not list or any(type(key) is not str for key in pending):
        raise ValueError("released source verifier must return explicit source/pending lists")
    expected_jobs = {job.job_id: job for job in W.historical_exp1_jobs(label_required_only=True) + W.new_exp1_repair_jobs()}
    by_id = {}
    old_ids = {job.job_id for job in W.historical_exp1_jobs(label_required_only=True)}
    for row in sources:
        if not isinstance(row, Mapping) or not isinstance(row.get("job"), Mapping):
            raise ValueError("source verifier returned malformed source metadata")
        W.L._strict_keys(row, {"job", "source_path", "copy_path", "expected_git_commit",
                               "execution_digest", "source_tree_digest", "copy_evidence_digest"},
                         what="released finalization source row")
        job_id = row["job"].get("job_id")
        if job_id not in expected_jobs or job_id in by_id:
            raise ValueError("source verifier returned extra or duplicate physical jobs")
        _same(row["job"], expected_jobs[job_id].as_record(), "verified source exact job")
        commit = W.HISTORICAL_COMMIT if job_id in old_ids else inputs.expected_execution_commit
        if row.get("expected_git_commit") != commit:
            raise ValueError("source verifier changed a historical or new execution commit")
        if job_id in old_ids:
            _same(row, next(old for old in ledger["sources"] if old["job"]["job_id"] == job_id),
                  "independently pinned historical source ledger row")
        _verify_pair(expected_jobs[job_id], row)
        by_id[job_id] = dict(row)
    if old_ids - set(by_id) or set(by_id) | set(pending) != set(expected_jobs):
        raise ValueError("verified sources/pending jobs do not partition the exact 576 label-required fits")
    if len(pending) != len(set(pending)) or set(by_id) & set(pending):
        raise ValueError("source verifier duplicated pending or completed job identities")
    for path, digest in ((plan_path, inputs.plan_sha256), (ledger_path, inputs.reuse_ledger_sha256), (checkpoint, inputs.checkpoint_sha256)):
        _pin_file(path, digest)
    return {
        "plan": plan, "reuse_digest": ledger["reuse_digest"],
        "execution_context_digest": start["execution_context_digest"],
        "execution_roots": {name: str(path) for name, path in roots.items()},
        "sources": [by_id[key] for key in sorted(by_id)], "pending_new_fit_ids": sorted(pending),
    }


def _plain_tree(root: Path) -> dict[str, Any]:
    root = W._project_path(root, directory=True)
    W._plain_tree(root)
    directories = []
    for current, names, files in os.walk(root, followlinks=False):
        for name in names:
            directories.append((Path(current) / name).relative_to(root).as_posix())
        for name in files:
            RF._regular_file(Path(current) / name, what="finalization source/export")
    inventory = B._regular_tree_inventory(root)
    return {"directories": sorted(directories), "files": inventory,
            "content_digest": B._job_tree_digest(root)}


def _verify_pair(job: W.Exp1RepairJob, row: Mapping[str, Any]) -> F.VerifiedFitEvidence:
    for name in ("source_path", "copy_path"):
        _plain_tree(Path(row[name]))
    verified, actual = W._source_pair(job, Path(row["source_path"]), Path(row["copy_path"]), commit=row["expected_git_commit"])
    _same(actual, row, "independently pinned original/durable source pair")
    return verified


def _roots(export_root, durable_copy_root, inputs, inventory, *, creating):
    roots = tuple(W._project_path(path, directory=True, existing=not creating) for path in (export_root, durable_copy_root))
    if W.P._overlap(*roots):
        raise ValueError("export and durable-copy roots must be separate and nonoverlapping")
    protected = [W.HISTORICAL_JOBS_ROOT, W.HISTORICAL_COPY_ROOT, W.COMMON_LEASE_ROOT]
    protected += [Path(path) for path in inventory["execution_roots"].values()]
    protected += [Path(inputs.plan_path), Path(inputs.reuse_ledger_path), Path(inputs.checkpoint_path)]
    for root in roots:
        if creating and os.path.lexists(root):
            raise ValueError("finalization roots must be new; existing or partial evidence is never overwritten")
        if any(W.P._overlap(root, path.resolve()) for path in protected):
            raise ValueError("finalization root overlaps immutable source, input, execution or control evidence")
        # _project_path has already checked every ancestor for links/reparse
        # points. The workspace itself may be a parent, never an export target.
        if not root.parent.is_dir():
            raise ValueError("finalization root parent must already exist")
    return roots


def _copy_tree(source: Path, destination: Path) -> None:
    before = _plain_tree(source)
    W._project_path(destination, directory=True, existing=False)
    if os.path.lexists(destination):
        raise ValueError("source export already exists; no overwrite or in-place completion")
    destination.mkdir()
    for relative in before["directories"]:
        target = destination / relative
        target.mkdir()
        W._project_path(target, directory=True)
    for row in before["files"]:
        original, target = source / row["path"], destination / row["path"]
        RF._regular_file(original, what="export source")
        if os.path.lexists(target):
            raise ValueError("export file unexpectedly exists")
        data = original.read_bytes()
        atomic_write_bytes(target, data)
        RF._regular_file(target, what="exported source")
    after = _plain_tree(source)
    _same(after, before, "source tree before/after independent export")
    exported = _plain_tree(destination)
    _same(exported["directories"], before["directories"], "export directory inventory")
    _same(exported["content_digest"], before["content_digest"], "exported source content")
    B._copy_evidence_digest(source, destination)


def _verify_export(job, row, destination):
    _plain_tree(destination)
    verified = F.load_fit_evidence(destination, expected_git_commit=row["expected_git_commit"])
    W._match_fit(verified, job)
    _same(verified.execution_digest, row["execution_digest"], "export independently pinned fit digest")
    _same(B._job_tree_digest(destination), row["source_tree_digest"], "full exported source tree")
    B._copy_evidence_digest(Path(row["source_path"]), destination)
    B._copy_evidence_digest(Path(row["copy_path"]), destination)
    return verified


def _conditions(jobs, rows_by_id, unit_root, *, ordinary):
    result = []
    for seed in sorted({job.seed for job in jobs}):
        sources = []
        for arm in ("baseline", "data_repair", "capacity_extension_repair"):
            job = next(job for job in jobs if job.seed == seed and job.arm == arm)
            source = rows_by_id[job.job_id]
            path = unit_root / SOURCE_DIRECTORY / job.job_id
            sources.append(O.OrdinaryFitSource(path, source["expected_git_commit"], source["execution_digest"]) if ordinary else path)
        result.append(O.OrdinaryRepairCondition(*sources) if ordinary else L.PersistedRepairCondition(*sources))
    return tuple(result)


def _label(unit, jobs, rows_by_id, local, durable, *, creating):
    ordinary = len({job.seed for job in jobs}) == 3
    local_conditions = _conditions(jobs, rows_by_id, local, ordinary=ordinary)
    copy_conditions = _conditions(jobs, rows_by_id, durable, ordinary=ordinary)
    local_path, copy_path = local / LABEL_FILE, durable / LABEL_FILE
    if creating:
        if os.path.lexists(local_path) or os.path.lexists(copy_path):
            raise ValueError("label output already exists")
        record = (O.build_ordinary_label_evidence(local_conditions, unit=unit, path=local_path)
                  if ordinary else L.build_label_evidence(local_conditions, path=local_path))
        RF.sync_immutable_file(local_path, copy_path)
    else:
        record = read_json(W._project_path(local_path, directory=False))
    left = (O.load_ordinary_label_evidence(local_path, unit=unit, conditions=local_conditions)
            if ordinary else L.load_label_evidence(local_path))
    right = (O.load_ordinary_label_evidence(copy_path, unit=unit, conditions=copy_conditions)
             if ordinary else L.load_label_evidence(copy_path))
    _same(left, record, "source-reverified local label")
    _same(right, record, "source-reverified independent label copy")
    W._same_file_copy(local_path, copy_path)
    return record


def _unit_record(label_plan, job_map, rows_by_id, roots, *, creating):
    uid = label_plan["unit_id"]
    jobs = [job_map[fit_id] for fit_id in label_plan["required_fit_ids"]]
    unit = jobs[0].unit
    local, durable = (root / uid for root in roots)
    if creating:
        for root in (local, durable):
            root.mkdir()
            (root / SOURCE_DIRECTORY).mkdir()
    missing = [job.job_id for job in jobs if job.job_id not in rows_by_id]
    exported = []
    baseline_fits = {}
    for job in jobs:
        if job.job_id not in rows_by_id:
            continue
        row = rows_by_id[job.job_id]
        _verify_pair(job, row)
        destinations = tuple(root / SOURCE_DIRECTORY / job.job_id for root in (local, durable))
        if creating:
            for destination in destinations:
                _copy_tree(Path(row["source_path"]), destination)
        fits = [_verify_export(job, row, destination) for destination in destinations]
        if job.arm == "baseline":
            baseline_fits[job.seed] = fits[0]
        exported.append({
            "fit_id": job.job_id, "expected_git_commit": row["expected_git_commit"],
            "execution_digest": row["execution_digest"], "source_tree_digest": row["source_tree_digest"],
            "source_path": row["source_path"], "copy_path": row["copy_path"],
            "original_copy_evidence_digest": row["copy_evidence_digest"],
            "job": row["job"],
            "relative_path": f"{SOURCE_DIRECTORY}/{job.job_id}",
            "independent_export_copy_digest": B._copy_evidence_digest(*destinations),
        })
    empty = ([] if missing else sorted(seed for seed, fit in baseline_fits.items()
                                      if not (np.asarray(fit.error) > K.FAILURE_THRESHOLD).any()))
    label = None
    if not missing and not empty:
        label = _label(unit, jobs, rows_by_id, local, durable, creating=creating)
        for field in ("unit_id", "comparison_group_id", "seeds"):
            _same(label[field], label_plan[field], f"label registered {field}")
        _same(label["stage"], label_plan["label_stage"], "label registered stage")
    else:
        for root in (local, durable):
            if os.path.lexists(root / LABEL_FILE):
                raise ValueError("pending/blocked condition must not contain an observed label artifact")
    # Reopen every original/copy and every export after label creation/reload.
    for job in jobs:
        if job.job_id in rows_by_id:
            row = rows_by_id[job.job_id]
            _verify_pair(job, row)
            for root in (local, durable):
                _verify_export(job, row, root / SOURCE_DIRECTORY / job.job_id)
    record = {
        "unit_id": uid, "comparison_group_id": label_plan["comparison_group_id"],
        "label_stage": label_plan["label_stage"], "label_api": label_plan["label_api"],
        "seeds": label_plan["seeds"], "required_fit_ids": label_plan["required_fit_ids"],
        "status": "pending" if missing else "blocked" if empty else "labelled",
        "reason": "missing_registered_fits" if missing else "empty_strict_baseline_failure_set" if empty else None,
        "missing_fit_ids": missing, "empty_failure_seeds": empty, "exported_sources": exported,
        "observed_label": None if label is None else label["label"]["observed_label"],
        "label_record_digest": None if label is None else label["record_digest"],
        "label_file_sha256": None if label is None else sha256_file(local / LABEL_FILE),
    }
    for root in (local, durable):
        path = root / UNIT_STATUS_FILE
        if creating:
            atomic_write_json(path, record)
        _same(read_json(W._project_path(path, directory=False)), record, "unit finalization status")
        expected = {SOURCE_DIRECTORY, UNIT_STATUS_FILE} | ({LABEL_FILE} if label is not None else set())
        if {p.name for p in root.iterdir()} != expected:
            raise ValueError("unit finalization tree contains extra or missing artifacts")
        if {p.name for p in (root / SOURCE_DIRECTORY).iterdir()} != {r["fit_id"] for r in exported}:
            raise ValueError("unit source export inventory is not exact")
    W._same_file_copy(local / UNIT_STATUS_FILE, durable / UNIT_STATUS_FILE)
    return record


def _record(inputs, inventory, roots, environment, *, creating):
    plan = inventory["plan"]
    job_map = {job.job_id: job for job in W.registered_exp1_jobs()}
    rows_by_id = {row["job"]["job_id"]: row for row in inventory["sources"]}
    units = [_unit_record(row, job_map, rows_by_id, roots, creating=creating) for row in plan["labels"]]
    observed = {"observed_0": 0, "observed_1": 0, "ambiguous": 0, "undiagnosed": 0}
    for row in units:
        if row["status"] == "labelled":
            label = row["observed_label"]
            if type(label) is int and label in (0, 1):
                observed[f"observed_{label}"] += 1
            elif type(label) is str and label in ("ambiguous", "undiagnosed"):
                observed[label] += 1
            else:
                raise ValueError("label API returned an invalid observed label")
    counts = {
        "registered_units": 30, "labelled_units": sum(observed.values()),
        "pending_units": sum(row["status"] == "pending" for row in units),
        "blocked_units": sum(row["status"] == "blocked" for row in units),
        "observed": observed, "historical_fits_preserved": 150,
        "historical_fits_required": 102, "new_fit_obligations": 474,
        "verified_source_pairs": len(rows_by_id), "pending_new_fits": len(inventory["pending_new_fit_ids"]),
        "exported_fit_trees_per_root": sum(len(row["exported_sources"]) for row in units),
        "executed_fits": 0, "retrained_fits": 0,
    }
    if counts["labelled_units"] + counts["pending_units"] + counts["blocked_units"] != 30:
        raise ValueError("finalization statuses do not partition all thirty E1 units")
    payload = {
        "week7_label_finalization_schema_version": FINALIZATION_SCHEMA_VERSION,
        "purpose": "exact_week7_experiment1_label_finalization",
        "status": "complete" if counts["labelled_units"] == 30 else "incomplete",
        "inputs": {
            "plan": {"path": str(Path(inputs.plan_path).resolve()), "sha256": inputs.plan_sha256},
            "reuse_ledger": {"path": str(Path(inputs.reuse_ledger_path).resolve()), "sha256": inputs.reuse_ledger_sha256},
            "checkpoint": {"path": str(Path(inputs.checkpoint_path).resolve()), "sha256": inputs.checkpoint_sha256},
            "expected_execution_commit": inputs.expected_execution_commit,
        },
        "finalizer": environment, "plan_digest": plan["plan_digest"],
        "reuse_digest": inventory["reuse_digest"], "execution_context_digest": inventory["execution_context_digest"],
        "source_inventory_digest": L._digest(inventory["sources"]),
        "roots": {"export": str(roots[0]), "durable_copy": str(roots[1])},
        "counts": counts, "pending_new_fit_ids": inventory["pending_new_fit_ids"], "units": units,
    }
    return W._seal(payload, "manifest_digest")


def finalize_exp1_labels(inputs: Exp1FinalizationInputs, *, export_root: str | Path, durable_copy_root: str | Path) -> dict[str, Any]:
    """Export/reverify exact registered sources and publish two identical manifests.

    Requires a genuinely released launch checkpoint, not an active worker lease.
    No source subset, executor, seed override, repair choice or label is accepted.
    A failed attempt is retained and must use new roots on its next attempt.
    """
    inventory = _collect_sources(inputs)
    environment = _finalizer_environment(inputs.expected_finalizer_commit)
    roots = _roots(export_root, durable_copy_root, inputs, inventory, creating=True)
    for root in roots:
        root.mkdir()
    record = _record(inputs, inventory, roots, environment, creating=True)
    _same(_collect_sources(inputs), inventory, "original sources/checkpoint before and after finalization")
    _same(_finalizer_environment(inputs.expected_finalizer_commit), environment, "finalizer environment before/after")
    expected_units = {row["unit_id"] for row in inventory["plan"]["labels"]}
    for root in roots:
        if {path.name for path in root.iterdir()} != expected_units:
            raise ValueError("finalization root contains extra or missing artifacts before publication")
    for root in reversed(roots):
        atomic_write_json(root / MANIFEST_FILE, record)
        _same(read_json(root / MANIFEST_FILE), record, "persisted finalization manifest")
    W._same_file_copy(roots[0] / MANIFEST_FILE, roots[1] / MANIFEST_FILE)
    return record


def load_exp1_label_finalization(inputs: Exp1FinalizationInputs, *, export_root: str | Path,
                                 durable_copy_root: str | Path, expected_manifest_sha256: str) -> dict[str, Any]:
    """Read-only reload against independent inputs; the manifest is not authority."""
    inventory = _collect_sources(inputs)
    environment = _finalizer_environment(inputs.expected_finalizer_commit)
    roots = _roots(export_root, durable_copy_root, inputs, inventory, creating=False)
    for root in roots:
        _pin_file(root / MANIFEST_FILE, expected_manifest_sha256)
        expected = {row["unit_id"] for row in inventory["plan"]["labels"]} | {MANIFEST_FILE}
        if {p.name for p in root.iterdir()} != expected:
            raise ValueError("finalization root contains extra or missing artifacts")
    record = read_json(roots[0] / MANIFEST_FILE)
    derived = _record(inputs, inventory, roots, environment, creating=False)
    _same(record, derived, "source-rederived complete finalization manifest")
    _same(_collect_sources(inputs), inventory, "sources before/after finalization reload")
    _same(_finalizer_environment(inputs.expected_finalizer_commit), environment, "finalizer environment before/after reload")
    W._same_file_copy(roots[0] / MANIFEST_FILE, roots[1] / MANIFEST_FILE)
    return derived
