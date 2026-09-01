"""Zero-compute export and label finalization for Experiment 2A.

Four units use the certified twenty-seed :mod:`label_evidence` procedure and
sixteen use the certified three-seed :mod:`ordinary_label_evidence` procedure.
All source authority comes from the released Week-8 checkpoint and the pinned
155-source ledger.  This module has no fitting path: it only reopens, exports,
and labels already completed evidence.

Each unit receives source trees in a new export root and a separate new durable
copy.  Originals, their existing independent copies and both exports are
verified before and after label creation.  Missing fits remain ``pending``; an
empty strict baseline failure set is ``blocked``.  Neither state creates a
label, and partial roots are preserved rather than overwritten.
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
from . import week8_exp2a_repair_launch as X
from . import week8_exp2a_repairs as W
from . import week8_exp2a_sources as S


FINALIZATION_SCHEMA_VERSION = 1
MANIFEST_FILE = "week8_exp2a_label_finalization.json"
UNIT_STATUS_FILE = "label_status.json"
LABEL_FILE = "label_evidence.json"
SOURCE_DIRECTORY = "sources"


@dataclass(frozen=True)
class Exp2AFinalizationInputs:
    """Independent pins retained outside the artifact being validated."""

    plan_path: str | Path
    plan_sha256: str
    source_ledger_path: str | Path
    source_ledger_sha256: str
    checkpoint_path: str | Path
    checkpoint_sha256: str
    expected_execution_commit: str
    expected_finalizer_commit: str


def _same(actual: object, expected: object, what: str) -> None:
    W._equal(actual, expected, what=what)


def _pin_file(path: str | Path, digest: str) -> Path:
    target = W._project_path(path, directory=False)
    expected = X.L._lower_sha256(digest, what="independent input SHA256")
    if sha256_file(target) != expected:
        raise ValueError("finalization input differs from its independent SHA256")
    return target


def _finalizer_environment(commit: str) -> dict[str, Any]:
    expected = F._validate_expected_git_commit(commit)
    state, versions, pins = X.P._verify_environment()
    if state.commit != expected or state.dirty or not state.trustworthy:
        raise ValueError("finalization requires the expected clean trustworthy commit")
    return {
        "git_commit": expected,
        "branch": state.branch,
        "packages": versions,
        "exact_pins": pins,
        "fits_executed": 0,
    }


def _verify_pair(
    job: W.Exp2ARepairJob, row: Mapping[str, Any]
) -> F.VerifiedFitEvidence:
    for name in ("source_path", "copy_path"):
        _plain_tree(Path(row[name]))
    verified, actual = S._source_pair(
        job,
        Path(row["source_path"]),
        Path(row["copy_path"]),
        commit=row["expected_git_commit"],
        expected_execution_digest=row["execution_digest"],
    )
    _same(actual, row, "independently pinned original/durable source pair")
    return verified


def _collect_sources(inputs: Exp2AFinalizationInputs) -> dict[str, Any]:
    """Reopen checkpoint authority and return only the 384 label sources."""

    if type(inputs) is not Exp2AFinalizationInputs:
        raise ValueError("inputs must be exact Exp2AFinalizationInputs")
    F._validate_expected_git_commit(inputs.expected_execution_commit)
    plan_path = _pin_file(inputs.plan_path, inputs.plan_sha256)
    ledger_path = _pin_file(inputs.source_ledger_path, inputs.source_ledger_sha256)
    checkpoint_path = _pin_file(inputs.checkpoint_path, inputs.checkpoint_sha256)
    plan = W.load_exp2a_repair_plan(plan_path)
    ledger = S.load_exp2a_source_ledger(ledger_path)
    verified = X.load_released_exp2a_source_inventory(
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=inputs.checkpoint_sha256,
        expected_execution_commit=inputs.expected_execution_commit,
    )
    start = verified["start"]
    bound_ledger = verified["ledger"]
    roots = verified["roots"]
    _same(bound_ledger, ledger, "checkpoint-bound 155-source ledger")
    if (
        Path(start["source_ledger"]["path"]).resolve() != ledger_path
        or start["source_ledger"]["sha256"] != inputs.source_ledger_sha256
    ):
        raise ValueError("checkpoint does not bind the independently supplied source ledger")
    _same(plan["plan_digest"], start["plan_digest"], "checkpoint-bound E2A plan")
    sources = verified["sources"]
    pending = verified["pending_new_fit_ids"]
    if (
        type(sources) is not list
        or type(pending) is not list
        or any(type(job_id) is not str for job_id in pending)
    ):
        raise ValueError("released verifier must return explicit source and pending lists")

    all_jobs = {job.job_id: job for job in W.registered_exp2a_jobs()}
    existing_ids = {job.job_id for job in W.existing_exp2a_jobs()}
    new_ids = {job.job_id for job in W.new_exp2a_jobs()}
    label_ids = {job.job_id for job in W.label_required_exp2a_jobs()}
    ledger_rows = {row["job"]["job_id"]: row for row in ledger["sources"]}
    by_id: dict[str, dict[str, Any]] = {}
    expected_fields = {
        "job",
        "source_kind",
        "source_path",
        "copy_path",
        "expected_git_commit",
        "execution_digest",
        "sidecar_sha256",
        "source_tree_digest",
        "copy_tree_digest",
        "copy_evidence_digest",
        "independent_files",
    }
    for row in sources:
        if not isinstance(row, Mapping) or not isinstance(row.get("job"), Mapping):
            raise ValueError("released source metadata is malformed")
        if set(row) != expected_fields:
            raise ValueError("released source row has missing or extra fields")
        job_id = row["job"].get("job_id")
        if job_id not in all_jobs or job_id in by_id:
            raise ValueError("released verifier returned an extra or duplicate fit")
        job = all_jobs[job_id]
        _same(row["job"], job.as_record(), "released source exact job")
        expected_commit = (
            ledger_rows[job_id]["expected_git_commit"]
            if job_id in existing_ids
            else inputs.expected_execution_commit
        )
        if row["expected_git_commit"] != expected_commit:
            raise ValueError("released source changed its historical/new execution commit")
        if job_id in existing_ids:
            _same(row, ledger_rows[job_id], "pinned historical ledger source")
        _verify_pair(job, row)
        by_id[job_id] = dict(row)
    if (
        set(by_id) | set(pending) != set(all_jobs)
        or set(by_id) & set(pending)
        or len(pending) != len(set(pending))
        or not set(pending).issubset(new_ids)
        or existing_ids - set(by_id)
    ):
        raise ValueError("completed/pending sources do not partition all 416 obligations")

    label_sources = [by_id[job_id] for job_id in sorted(label_ids & set(by_id))]
    pending_labels = sorted(label_ids & set(pending))
    if len(label_sources) + len(pending_labels) != 384:
        raise ValueError("label source/pending partition must cover exactly 384 fits")
    for path, digest in (
        (plan_path, inputs.plan_sha256),
        (ledger_path, inputs.source_ledger_sha256),
        (checkpoint_path, inputs.checkpoint_sha256),
    ):
        _pin_file(path, digest)
    return {
        "plan": plan,
        "ledger_digest": ledger["ledger_digest"],
        "execution_context_digest": start["execution_context_digest"],
        "execution_roots": {name: str(path) for name, path in roots.items()},
        "sources": label_sources,
        "pending_new_fit_ids": pending_labels,
        "non_label_existing_fit_ids": sorted(existing_ids - label_ids),
    }


def _plain_tree(root: Path) -> dict[str, Any]:
    root = W._project_path(root, directory=True)
    S._plain_tree(root)
    directories: list[str] = []
    for current, names, files in os.walk(root, followlinks=False):
        for name in names:
            directories.append((Path(current) / name).relative_to(root).as_posix())
        for name in files:
            RF._regular_file(Path(current) / name, what="E2A finalization source/export")
    inventory = B._regular_tree_inventory(root)
    return {
        "directories": sorted(directories),
        "files": inventory,
        "content_digest": B._job_tree_digest(root),
    }


def _roots(
    export_root: str | Path,
    durable_copy_root: str | Path,
    inputs: Exp2AFinalizationInputs,
    inventory: dict[str, Any],
    *,
    creating: bool,
) -> tuple[Path, Path]:
    roots = tuple(
        W._project_path(path, directory=True, existing=not creating)
        for path in (export_root, durable_copy_root)
    )
    if X.P._overlap(*roots):
        raise ValueError("finalization roots must be separate and non-overlapping")
    protected = list(X._protected_paths())
    protected.extend(Path(path) for path in inventory["execution_roots"].values())
    protected.extend(
        Path(path)
        for path in (
            inputs.plan_path,
            inputs.source_ledger_path,
            inputs.checkpoint_path,
        )
    )
    for root in roots:
        if creating and os.path.lexists(root):
            raise ValueError("finalization roots must be new; partial evidence is preserved")
        if any(X.P._overlap(root, path.resolve()) for path in protected):
            raise ValueError("finalization root overlaps source, execution or control evidence")
        if not root.parent.is_dir():
            raise ValueError("finalization root parent must already exist")
    return roots  # type: ignore[return-value]


def _copy_tree(source: Path, destination: Path) -> None:
    before = _plain_tree(source)
    W._project_path(destination, directory=True, existing=False)
    if os.path.lexists(destination):
        raise ValueError("source export already exists; no overwrite")
    destination.mkdir()
    for relative in before["directories"]:
        target = destination / relative
        target.mkdir()
        W._project_path(target, directory=True)
    for row in before["files"]:
        original = source / row["path"]
        target = destination / row["path"]
        RF._regular_file(original, what="E2A export source")
        if os.path.lexists(target):
            raise ValueError("export file unexpectedly exists")
        atomic_write_bytes(target, original.read_bytes())
        RF._regular_file(target, what="E2A exported source")
    after = _plain_tree(source)
    _same(after, before, "source before/after independent export")
    exported = _plain_tree(destination)
    _same(exported["directories"], before["directories"], "export directory inventory")
    _same(exported["content_digest"], before["content_digest"], "exported source content")
    B._copy_evidence_digest(source, destination)


def _verify_export(
    job: W.Exp2ARepairJob, row: Mapping[str, Any], destination: Path
) -> F.VerifiedFitEvidence:
    _plain_tree(destination)
    verified = F.load_fit_evidence(
        destination, expected_git_commit=row["expected_git_commit"]
    )
    S._match_fit(verified, job)
    _same(verified.execution_digest, row["execution_digest"], "exported fit digest")
    _same(B._job_tree_digest(destination), row["source_tree_digest"], "exported tree")
    B._copy_evidence_digest(Path(row["source_path"]), destination)
    B._copy_evidence_digest(Path(row["copy_path"]), destination)
    return verified


def _conditions(
    jobs: list[W.Exp2ARepairJob],
    rows_by_id: dict[str, dict[str, Any]],
    unit_root: Path,
    *,
    ordinary: bool,
):
    result = []
    for seed in sorted({job.seed for job in jobs}):
        sources = []
        for arm in ("baseline", "data_repair", "feature_repair"):
            job = next(
                candidate
                for candidate in jobs
                if candidate.seed == seed and candidate.arm == arm
            )
            row = rows_by_id[job.job_id]
            path = unit_root / SOURCE_DIRECTORY / job.job_id
            sources.append(
                O.OrdinaryFitSource(
                    path, row["expected_git_commit"], row["execution_digest"]
                )
                if ordinary
                else path
            )
        result.append(
            O.OrdinaryRepairCondition(*sources)
            if ordinary
            else L.PersistedRepairCondition(*sources)
        )
    return tuple(result)


def _label(
    unit,
    jobs: list[W.Exp2ARepairJob],
    rows_by_id: dict[str, dict[str, Any]],
    local: Path,
    durable: Path,
    *,
    creating: bool,
) -> dict[str, Any]:
    ordinary = len({job.seed for job in jobs}) == 3
    local_conditions = _conditions(jobs, rows_by_id, local, ordinary=ordinary)
    durable_conditions = _conditions(jobs, rows_by_id, durable, ordinary=ordinary)
    local_path = local / LABEL_FILE
    durable_path = durable / LABEL_FILE
    if creating:
        if os.path.lexists(local_path) or os.path.lexists(durable_path):
            raise ValueError("label output already exists")
        record = (
            O.build_ordinary_label_evidence(
                local_conditions, unit=unit, path=local_path
            )
            if ordinary
            else L.build_label_evidence(local_conditions, path=local_path)
        )
        RF.sync_immutable_file(local_path, durable_path)
    else:
        record = read_json(W._project_path(local_path, directory=False))
    left = (
        O.load_ordinary_label_evidence(
            local_path, unit=unit, conditions=local_conditions
        )
        if ordinary
        else L.load_label_evidence(local_path)
    )
    right = (
        O.load_ordinary_label_evidence(
            durable_path, unit=unit, conditions=durable_conditions
        )
        if ordinary
        else L.load_label_evidence(durable_path)
    )
    _same(left, record, "source-reverified local label")
    _same(right, record, "source-reverified independent label copy")
    X._same_file_copy(local_path, durable_path)
    return record


def _unit_record(
    label_plan: dict[str, Any],
    job_map: dict[str, W.Exp2ARepairJob],
    rows_by_id: dict[str, dict[str, Any]],
    roots: tuple[Path, Path],
    *,
    creating: bool,
) -> dict[str, Any]:
    unit_id = label_plan["unit_id"]
    jobs = [job_map[fit_id] for fit_id in label_plan["required_fit_ids"]]
    unit = jobs[0].unit
    local, durable = (root / unit_id for root in roots)
    if creating:
        for root in (local, durable):
            root.mkdir()
            (root / SOURCE_DIRECTORY).mkdir()
    missing = [job.job_id for job in jobs if job.job_id not in rows_by_id]
    exported: list[dict[str, Any]] = []
    baseline_fits: dict[int, F.VerifiedFitEvidence] = {}
    for job in jobs:
        if job.job_id not in rows_by_id:
            continue
        row = rows_by_id[job.job_id]
        _verify_pair(job, row)
        destinations = tuple(
            root / SOURCE_DIRECTORY / job.job_id for root in (local, durable)
        )
        if creating:
            for destination in destinations:
                _copy_tree(Path(row["source_path"]), destination)
        fits = [_verify_export(job, row, destination) for destination in destinations]
        if job.arm == "baseline":
            baseline_fits[job.seed] = fits[0]
        exported.append(
            {
                "fit_id": job.job_id,
                "expected_git_commit": row["expected_git_commit"],
                "execution_digest": row["execution_digest"],
                "source_tree_digest": row["source_tree_digest"],
                "source_path": row["source_path"],
                "copy_path": row["copy_path"],
                "original_copy_evidence_digest": row["copy_evidence_digest"],
                "job": row["job"],
                "relative_path": f"{SOURCE_DIRECTORY}/{job.job_id}",
                "independent_export_copy_digest": B._copy_evidence_digest(*destinations),
            }
        )
    empty = (
        []
        if missing
        else sorted(
            seed
            for seed, fit in baseline_fits.items()
            if not (np.asarray(fit.error) > K.FAILURE_THRESHOLD).any()
        )
    )
    label = None
    if not missing and not empty:
        label = _label(
            unit, jobs, rows_by_id, local, durable, creating=creating
        )
        for field in ("unit_id", "comparison_group_id", "seeds"):
            _same(label[field], label_plan[field], f"label registered {field}")
        _same(label["stage"], label_plan["label_stage"], "label registered stage")
    else:
        for root in (local, durable):
            if os.path.lexists(root / LABEL_FILE):
                raise ValueError("pending/blocked unit must not contain a label")
    for job in jobs:
        if job.job_id in rows_by_id:
            row = rows_by_id[job.job_id]
            _verify_pair(job, row)
            for root in (local, durable):
                _verify_export(job, row, root / SOURCE_DIRECTORY / job.job_id)
    record = {
        "unit_id": unit_id,
        "comparison_group_id": label_plan["comparison_group_id"],
        "label_stage": label_plan["label_stage"],
        "label_api": label_plan["label_api"],
        "seeds": label_plan["seeds"],
        "required_fit_ids": label_plan["required_fit_ids"],
        "status": "pending" if missing else "blocked" if empty else "labelled",
        "reason": (
            "missing_registered_fits"
            if missing
            else "empty_strict_baseline_failure_set"
            if empty
            else None
        ),
        "missing_fit_ids": missing,
        "empty_failure_seeds": empty,
        "exported_sources": exported,
        "observed_label": None if label is None else label["label"]["observed_label"],
        "label_record_digest": None if label is None else label["record_digest"],
        "label_file_sha256": None if label is None else sha256_file(local / LABEL_FILE),
    }
    for root in (local, durable):
        status_path = root / UNIT_STATUS_FILE
        if creating:
            atomic_write_json(status_path, record)
        _same(
            read_json(W._project_path(status_path, directory=False)),
            record,
            "unit finalization status",
        )
        expected = {SOURCE_DIRECTORY, UNIT_STATUS_FILE} | (
            {LABEL_FILE} if label is not None else set()
        )
        if {path.name for path in root.iterdir()} != expected:
            raise ValueError("unit finalization tree has extra or missing artifacts")
        if {path.name for path in (root / SOURCE_DIRECTORY).iterdir()} != {
            row["fit_id"] for row in exported
        }:
            raise ValueError("unit source export inventory is not exact")
    X._same_file_copy(local / UNIT_STATUS_FILE, durable / UNIT_STATUS_FILE)
    return record


def _record(
    inputs: Exp2AFinalizationInputs,
    inventory: dict[str, Any],
    roots: tuple[Path, Path],
    environment: dict[str, Any],
    *,
    creating: bool,
) -> dict[str, Any]:
    plan = inventory["plan"]
    job_map = {job.job_id: job for job in W.registered_exp2a_jobs()}
    rows_by_id = {row["job"]["job_id"]: row for row in inventory["sources"]}
    units = [
        _unit_record(row, job_map, rows_by_id, roots, creating=creating)
        for row in plan["labels"]
    ]
    observed = {
        "observed_0": 0,
        "observed_1": 0,
        "ambiguous": 0,
        "undiagnosed": 0,
    }
    for row in units:
        if row["status"] != "labelled":
            continue
        label = row["observed_label"]
        if type(label) is int and label in (0, 1):
            observed[f"observed_{label}"] += 1
        elif type(label) is str and label in ("ambiguous", "undiagnosed"):
            observed[label] += 1
        else:
            raise ValueError("label API returned an invalid observed label")
    counts = {
        "registered_units": 20,
        "twenty_seed_units": 4,
        "three_seed_units": 16,
        "labelled_units": sum(observed.values()),
        "pending_units": sum(row["status"] == "pending" for row in units),
        "blocked_units": sum(row["status"] == "blocked" for row in units),
        "observed": observed,
        "historical_fits_preserved": 155,
        "historical_fits_required": 123,
        "non_label_historical_fits": len(inventory["non_label_existing_fit_ids"]),
        "new_fit_obligations": 261,
        "label_required_fits": 384,
        "verified_source_pairs": len(rows_by_id),
        "pending_new_fits": len(inventory["pending_new_fit_ids"]),
        "exported_fit_trees_per_root": sum(
            len(row["exported_sources"]) for row in units
        ),
        "executed_fits": 0,
        "retrained_fits": 0,
    }
    if counts["labelled_units"] + counts["pending_units"] + counts["blocked_units"] != 20:
        raise ValueError("finalization statuses do not partition all twenty E2A units")
    if not inventory["pending_new_fit_ids"] and counts["exported_fit_trees_per_root"] != 384:
        raise ValueError("complete finalization must export exactly 384 source trees per root")
    payload = {
        "week8_exp2a_label_finalization_schema_version": FINALIZATION_SCHEMA_VERSION,
        "purpose": "exact_week8_experiment2a_label_finalization",
        "status": "complete" if counts["labelled_units"] == 20 else "incomplete",
        "inputs": {
            "plan": {
                "path": str(Path(inputs.plan_path).resolve()),
                "sha256": inputs.plan_sha256,
            },
            "source_ledger": {
                "path": str(Path(inputs.source_ledger_path).resolve()),
                "sha256": inputs.source_ledger_sha256,
            },
            "checkpoint": {
                "path": str(Path(inputs.checkpoint_path).resolve()),
                "sha256": inputs.checkpoint_sha256,
            },
            "expected_execution_commit": inputs.expected_execution_commit,
        },
        "finalizer": environment,
        "plan_digest": plan["plan_digest"],
        "ledger_digest": inventory["ledger_digest"],
        "execution_context_digest": inventory["execution_context_digest"],
        "source_inventory_digest": L._digest(inventory["sources"]),
        "roots": {"export": str(roots[0]), "durable_copy": str(roots[1])},
        "counts": counts,
        "pending_new_fit_ids": inventory["pending_new_fit_ids"],
        "non_label_existing_fit_ids": inventory["non_label_existing_fit_ids"],
        "units": units,
    }
    return W._seal(payload, "manifest_digest")


def finalize_exp2a_labels(
    inputs: Exp2AFinalizationInputs,
    *,
    export_root: str | Path,
    durable_copy_root: str | Path,
) -> dict[str, Any]:
    """Export/reverify exact sources and publish manifests last; train nothing."""

    inventory = _collect_sources(inputs)
    environment = _finalizer_environment(inputs.expected_finalizer_commit)
    roots = _roots(
        export_root, durable_copy_root, inputs, inventory, creating=True
    )
    for root in roots:
        root.mkdir()
    record = _record(inputs, inventory, roots, environment, creating=True)
    _same(_collect_sources(inputs), inventory, "sources before/after finalization")
    _same(
        _finalizer_environment(inputs.expected_finalizer_commit),
        environment,
        "finalizer environment before/after",
    )
    expected_units = {row["unit_id"] for row in inventory["plan"]["labels"]}
    for root in roots:
        if {path.name for path in root.iterdir()} != expected_units:
            raise ValueError("finalization root has extra or missing unit artifacts")
    for root in reversed(roots):
        atomic_write_json(root / MANIFEST_FILE, record)
        _same(read_json(root / MANIFEST_FILE), record, "persisted finalization manifest")
    X._same_file_copy(roots[0] / MANIFEST_FILE, roots[1] / MANIFEST_FILE)
    return record


def load_exp2a_label_finalization(
    inputs: Exp2AFinalizationInputs,
    *,
    export_root: str | Path,
    durable_copy_root: str | Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Rebuild the manifest from independently pinned sources; never trust it."""

    inventory = _collect_sources(inputs)
    environment = _finalizer_environment(inputs.expected_finalizer_commit)
    roots = _roots(
        export_root, durable_copy_root, inputs, inventory, creating=False
    )
    for root in roots:
        _pin_file(root / MANIFEST_FILE, expected_manifest_sha256)
        expected = {row["unit_id"] for row in inventory["plan"]["labels"]} | {
            MANIFEST_FILE
        }
        if {path.name for path in root.iterdir()} != expected:
            raise ValueError("finalization root has extra or missing artifacts")
    record = read_json(roots[0] / MANIFEST_FILE)
    derived = _record(inputs, inventory, roots, environment, creating=False)
    _same(record, derived, "source-rederived E2A finalization manifest")
    _same(_collect_sources(inputs), inventory, "sources before/after reload")
    _same(
        _finalizer_environment(inputs.expected_finalizer_commit),
        environment,
        "finalizer environment before/after reload",
    )
    X._same_file_copy(roots[0] / MANIFEST_FILE, roots[1] / MANIFEST_FILE)
    return derived
