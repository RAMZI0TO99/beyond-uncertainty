"""Reconcile all 155 immutable Experiment-2A source fits.

Two independent, byte-pinned authorities are used.  The finalized Week-6
label binds all sixty smoke fit identities and execution digests; the matching
Week-7 readback receipts bind the ninety-five later baseline identities and
digests.  The label's scientific outcome is never consulted here.  Every build
or public load reopens both the original and independent copy of every fit with
the scientific fit reader and verifies full-tree equality and non-aliasing.

There is no source discovery, caller-selected commit, replacement-training
fallback or cached verified-input token.  Missing or changed history stops.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_file
from . import batch as B
from . import fit_evidence as F
from . import launch as L
from . import repair_label_preflight as RF
from . import week8_exp2a_repairs as W


SOURCE_LEDGER_SCHEMA_VERSION = 1
SOURCE_LEDGER_FILE = "week8_exp2a_source_ledger.json"

SMOKE_OUTPUT_ROOT = W.WORKSPACE_ROOT / "week6-smoke-2026-08-30-attempt-001-output"
SMOKE_COPY_ROOT = W.WORKSPACE_ROOT / "week6-smoke-2026-08-30-attempt-001-project-evidence"
SMOKE_LABEL_FILE = "label_evidence.json"
SMOKE_LABEL_SHA256 = "7e56f9a331a4e10a74b80568c86f527b1ae11ed483d76d45cd195fc945fee614"
SMOKE_FINALIZATION_FILE = (
    "repair_label_finalization_reports/efdbd2081ab349fd835998ce5ee4e5eb.json"
)
SMOKE_FINALIZATION_SHA256 = (
    "979df8c86c00c4feb390477912d8ea3adb4a46a5f19a6c424056a10549a485dd"
)

WEEK7_BATCH_ID = "03972c022a397aa8"
WEEK7_OUTPUT_ROOT = W.WORKSPACE_ROOT / "week7-exp2a-2026-08-31-attempt-002-output"
WEEK7_COPY_ROOT = (
    W.WORKSPACE_ROOT / "week7-exp2a-2026-08-31-attempt-002-project-evidence"
)
WEEK7_REPORT_FILE = "week7_launch_reports/1c61c75244284cdc9560803931d11ab9.json"
WEEK7_REPORT_SHA256 = "a4e61a274c07d3653cbd05073669cc0b94bea57169237def5de397422cfa9f34"
WEEK7_RECEIPT_ROOT = (
    W.WORKSPACE_ROOT / "week7-execution-preparation-2026-08-31-attempt-001"
)
WEEK7_RECEIPT_ORIGINAL = WEEK7_RECEIPT_ROOT / "e2a95-verification-original-001/receipt.json"
WEEK7_RECEIPT_COPY = (
    WEEK7_RECEIPT_ROOT / "e2a95-verification-project-copy-001/receipt.json"
)
WEEK7_RECEIPT_SHA256 = "4c4ae415b806140c437d79c0a90768206abc81058a93c04842675cf439551192"


def _plain_file(path: Path) -> Path:
    return W._project_path(path, directory=False)


def _plain_tree(root: Path) -> None:
    root = W._project_path(root, directory=True)
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(current) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or RF._is_reparse(info):
                raise ValueError("source tree contains a linked/reparse descendant")
    B._regular_tree_inventory(root)


def _pinned_file_pair(source: Path, copy: Path, digest: str, *, what: str) -> dict[str, Any]:
    expected = L._lower_sha256(digest, what=f"{what} SHA256")
    source = _plain_file(source)
    copy = _plain_file(copy)
    if RF._same_file_identity(source, copy) or os.path.samefile(source, copy):
        raise ValueError(f"{what} source and copy must be independent files")
    if sha256_file(source) != expected or sha256_file(copy) != expected:
        raise ValueError(f"{what} differs from its independently pinned SHA256")
    if source.read_bytes() != copy.read_bytes():
        raise ValueError(f"{what} source/copy bytes differ")
    return {
        "source_path": str(source),
        "copy_path": str(copy),
        "sha256": expected,
        "independent_files": True,
    }


def _job_map(kind: str) -> dict[str, W.Exp2ARepairJob]:
    result = {
        job.job_id: job
        for job in W.existing_exp2a_jobs()
        if W.source_kind(job) == kind
    }
    expected = 60 if kind == "week6_smoke" else 95 if kind == "week7_exp2a" else None
    if expected is None or len(result) != expected:
        raise ValueError("unknown or drifted Experiment-2A source family")
    return result


def _smoke_authority() -> tuple[dict[str, Any], dict[str, str]]:
    label_pin = _pinned_file_pair(
        SMOKE_OUTPUT_ROOT / SMOKE_LABEL_FILE,
        SMOKE_COPY_ROOT / SMOKE_LABEL_FILE,
        SMOKE_LABEL_SHA256,
        what="Week-6 smoke label authority",
    )
    finalization_pin = _pinned_file_pair(
        SMOKE_OUTPUT_ROOT / SMOKE_FINALIZATION_FILE,
        SMOKE_COPY_ROOT / SMOKE_FINALIZATION_FILE,
        SMOKE_FINALIZATION_SHA256,
        what="Week-6 smoke finalization authority",
    )
    finalization = read_json(label_path := Path(finalization_pin["source_path"]))
    try:
        valid_finalization = (
            type(finalization) is dict
            and finalization["repair_label_finalization_schema_version"] == 2
            and finalization["status"] == "complete_after_fail_closed_correction"
            and finalization["unit_id"] == W.SMOKE_UNIT_ID
            and finalization["fit_count"] == 60
            and finalization["verified_existing_fits"] == 60
            and finalization["project_copied_fits"] == 60
            and finalization["executed_fits"] == 0
            and finalization["retrained_fits"] == 0
            and finalization["preflight"]["fit_commit"] == W.SMOKE_EXECUTION_COMMIT
            and finalization["label"]["sha256"] == SMOKE_LABEL_SHA256
        )
    except (KeyError, TypeError):
        valid_finalization = False
    if not valid_finalization:
        raise ValueError("Week-6 finalization does not bind the exact sixty preserved fits")

    label = read_json(Path(label_pin["source_path"]))
    jobs = _job_map("week6_smoke")
    try:
        runs = label["runs"]
        if (
            type(label) is not dict
            or label["label_evidence_schema_version"] != 3
            or label["unit_id"] != W.SMOKE_UNIT_ID
            or label["stage"] != "repair_validation"
            or label["model_repair_arm"] != "feature_repair"
            or label["seeds"] != list(range(1000, 1020))
            or type(runs) is not list
            or len(runs) != 20
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Week-6 label authority has the wrong provenance schema") from exc

    digests: dict[str, str] = {}
    arm_keys = {
        "baseline": "baseline",
        "data_repair": "data_repair",
        "feature_repair": "model_repair",
    }
    for seed_index, run in enumerate(runs):
        seed = 1000 + seed_index
        if type(run) is not dict or run.get("seed") != seed:
            raise ValueError("Week-6 label authority seed ordering drifted")
        for arm, key in arm_keys.items():
            row = run.get(key)
            if type(row) is not dict or type(row.get("fit_id")) is not str:
                raise ValueError("Week-6 label authority lacks a physical fit reference")
            job = jobs.get(row["fit_id"])
            if job is None or job.seed != seed or job.arm != arm or job.job_id in digests:
                raise ValueError("Week-6 label authority names an unknown or duplicate fit")
            expected = {
                "arm": job.arm,
                "config_id": job.config.config_id,
                "execution_run_id": job.config.run_id,
                "execution_stage": job.stage,
                "fit_id": job.job_id,
                "fit_roles": list(job.roles),
            }
            W._equal(
                {name: row.get(name) for name in expected},
                expected,
                what="Week-6 label source identity/roles",
            )
            digests[job.job_id] = L._lower_sha256(
                row.get("fit_evidence_digest"), what="Week-6 source execution digest"
            )
    if set(digests) != set(jobs):
        raise ValueError("Week-6 label authority does not cover all sixty fits")
    # Recheck both fixed inputs after parsing provenance.
    _pinned_file_pair(
        Path(label_pin["source_path"]),
        Path(label_pin["copy_path"]),
        SMOKE_LABEL_SHA256,
        what="Week-6 smoke label authority",
    )
    _pinned_file_pair(
        label_path,
        Path(finalization_pin["copy_path"]),
        SMOKE_FINALIZATION_SHA256,
        what="Week-6 smoke finalization authority",
    )
    return {
        "records": ["D-147", "D-149"],
        "execution_commit": W.SMOKE_EXECUTION_COMMIT,
        "label": label_pin,
        "finalization": finalization_pin,
        "outcome_fields_read": False,
    }, digests


def _week7_authority() -> tuple[dict[str, Any], dict[str, str]]:
    receipt_pin = _pinned_file_pair(
        WEEK7_RECEIPT_ORIGINAL,
        WEEK7_RECEIPT_COPY,
        WEEK7_RECEIPT_SHA256,
        what="Week-7 95-fit verification receipt",
    )
    report_pin = _pinned_file_pair(
        WEEK7_OUTPUT_ROOT / WEEK7_REPORT_FILE,
        WEEK7_COPY_ROOT / WEEK7_REPORT_FILE,
        WEEK7_REPORT_SHA256,
        what="Week-7 E2A launch report",
    )
    receipt = read_json(Path(receipt_pin["source_path"]))
    jobs = _job_map("week7_exp2a")
    try:
        batch = receipt["batch"]
        rows = receipt["verified_jobs"]
        valid = (
            type(receipt) is dict
            and receipt["e2a95_verification_schema_version"] == 1
            and receipt["status"] == "source_readback_verified"
            and receipt["expected_execution_commit"] == W.WEEK7_EXECUTION_COMMIT
            and receipt["historical_reuses_reverified"] == 5
            and receipt["scientific_analysis_performed"] is False
            and receipt["actual_report"]["sha256"] == WEEK7_REPORT_SHA256
            and type(rows) is list
            and len(rows) == 95
            and all(batch[name] == value for name, value in {
                "total": 95,
                "executed": 95,
                "synced": 95,
                "failed": 0,
                "sync_failed": 0,
                "complete": True,
            }.items())
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise ValueError("Week-7 receipt does not prove the exact 95-fit release")
    digests: dict[str, str] = {}
    for row in rows:
        if type(row) is not dict or type(row.get("job_id")) is not str:
            raise ValueError("Week-7 receipt has a malformed fit row")
        job_id = row["job_id"]
        if job_id not in jobs or job_id in digests:
            raise ValueError("Week-7 receipt names an unknown or duplicate fit")
        digests[job_id] = L._lower_sha256(
            row.get("execution_digest"), what="Week-7 source execution digest"
        )
    if set(digests) != set(jobs):
        raise ValueError("Week-7 receipt does not cover the exact ninety-five fits")
    report = read_json(Path(report_pin["source_path"]))
    if (
        type(report) is not dict
        or report.get("status") != "complete"
        or report.get("historical_reuse_retrained") is not False
        or report.get("batch_key") != "exp2a"
        or report.get("batch") != batch
        or report.get("preflight", {}).get("git_commit") != W.WEEK7_EXECUTION_COMMIT
    ):
        raise ValueError("Week-7 launch report disagrees with its verification receipt")
    _pinned_file_pair(
        Path(receipt_pin["source_path"]),
        Path(receipt_pin["copy_path"]),
        WEEK7_RECEIPT_SHA256,
        what="Week-7 95-fit verification receipt",
    )
    _pinned_file_pair(
        Path(report_pin["source_path"]),
        Path(report_pin["copy_path"]),
        WEEK7_REPORT_SHA256,
        what="Week-7 E2A launch report",
    )
    return {
        "records": ["D-159"],
        "execution_commit": W.WEEK7_EXECUTION_COMMIT,
        "launch_report": report_pin,
        "verification_receipt": receipt_pin,
        "outcome_fields_read": False,
    }, digests


def source_authority() -> tuple[dict[str, Any], dict[str, tuple[str, str]]]:
    """Return pinned provenance and job -> (commit, execution digest)."""

    smoke, smoke_digests = _smoke_authority()
    week7, week7_digests = _week7_authority()
    pins = {
        job_id: (W.SMOKE_EXECUTION_COMMIT, digest)
        for job_id, digest in smoke_digests.items()
    }
    pins.update(
        {
            job_id: (W.WEEK7_EXECUTION_COMMIT, digest)
            for job_id, digest in week7_digests.items()
        }
    )
    if len(pins) != 155 or set(pins) != {job.job_id for job in W.existing_exp2a_jobs()}:
        raise ValueError("independent authorities do not cover exactly 155 existing fits")
    return {"week6_smoke": smoke, "week7_exp2a": week7}, pins


def _source_paths(job: W.Exp2ARepairJob) -> tuple[Path, Path]:
    kind = W.source_kind(job)
    if kind == "week6_smoke":
        return SMOKE_OUTPUT_ROOT / "jobs" / job.job_id, SMOKE_COPY_ROOT / "jobs" / job.job_id
    if kind == "week7_exp2a":
        return (
            WEEK7_OUTPUT_ROOT / WEEK7_BATCH_ID / "jobs" / job.job_id,
            WEEK7_COPY_ROOT / WEEK7_BATCH_ID / "jobs" / job.job_id,
        )
    raise ValueError("only immutable existing Experiment-2A jobs have source paths")


def _match_fit(verified: F.VerifiedFitEvidence, job: W.Exp2ARepairJob) -> None:
    if type(verified) is not F.VerifiedFitEvidence:
        raise ValueError("fit loader must return exact VerifiedFitEvidence")
    expected = {
        "unit_id": job.config.unit_id,
        "config_id": job.config.config_id,
        "fit_id": job.job_id,
        "execution_run_id": job.config.run_id,
        "execution_stage": job.stage,
        "arm": job.arm,
        "seed": job.seed,
        "roles": list(job.roles),
        "unit": job.config.to_dict()["unit"],
        "n_train": job.config.effective_unit.n_transitions,
        "ensemble_size": job.config.train.ensemble_size,
    }
    observed = {
        name: getattr(verified, name)
        for name in expected
        if name not in {"roles", "unit"}
    }
    observed.update(
        roles=list(verified.roles),
        unit=W.Config(unit=verified.unit).to_dict()["unit"],
    )
    W._equal(observed, expected, what="source fit identity/roles/frozen training")


def _source_pair(
    job: W.Exp2ARepairJob,
    source: Path,
    copy: Path,
    *,
    commit: str,
    expected_execution_digest: str | None = None,
) -> tuple[F.VerifiedFitEvidence, dict[str, Any]]:
    source = W._project_path(source, directory=True)
    copy = W._project_path(copy, directory=True)
    if source == copy or source in copy.parents or copy in source.parents or os.path.samefile(source, copy):
        raise ValueError("source and independent copy alias or overlap")
    _plain_tree(source)
    _plain_tree(copy)
    before = B._copy_evidence_digest(source, copy)
    left = F.load_fit_evidence(source, expected_git_commit=commit)
    right = F.load_fit_evidence(copy, expected_git_commit=commit)
    _match_fit(left, job)
    _match_fit(right, job)
    W._equal(left.execution_digest, right.execution_digest, what="source/copy execution digest")
    if expected_execution_digest is not None:
        W._equal(
            left.execution_digest,
            L._lower_sha256(expected_execution_digest, what="independent execution digest"),
            what="independently pinned execution digest",
        )
    source_tree = B._job_tree_digest(source)
    copy_tree = B._job_tree_digest(copy)
    sidecar = sha256_file(_plain_file(source / F.FIT_EVIDENCE_FILE))
    if sidecar != sha256_file(_plain_file(copy / F.FIT_EVIDENCE_FILE)):
        raise ValueError("source/copy fit sidecars differ")
    after = B._copy_evidence_digest(source, copy)
    if before != after or source_tree != copy_tree:
        raise ValueError("source or independent copy changed during verification")
    return left, {
        "job": job.as_record(),
        "source_kind": W.source_kind(job),
        "source_path": str(source),
        "copy_path": str(copy),
        "expected_git_commit": commit,
        "execution_digest": left.execution_digest,
        "sidecar_sha256": sidecar,
        "source_tree_digest": source_tree,
        "copy_tree_digest": copy_tree,
        "copy_evidence_digest": after,
        "independent_files": True,
    }


def build_exp2a_source_ledger() -> dict[str, Any]:
    """Reopen all 310 fit trees and return the exact 155-source ledger."""

    authority, pins = source_authority()
    rows: list[dict[str, Any]] = []
    for job in W.existing_exp2a_jobs():
        source, copy = _source_paths(job)
        commit, execution_digest = pins[job.job_id]
        _, row = _source_pair(
            job,
            source,
            copy,
            commit=commit,
            expected_execution_digest=execution_digest,
        )
        rows.append(row)
    current_authority, current_pins = source_authority()
    W._equal(current_authority, authority, what="source authority before/after reconciliation")
    W._equal(current_pins, pins, what="source digest registry before/after reconciliation")
    return W._seal(
        {
            "exp2a_source_ledger_schema_version": SOURCE_LEDGER_SCHEMA_VERSION,
            "purpose": "all_155_existing_exp2a_fits_reverified_not_reexecuted",
            "plan_digest": W.build_exp2a_repair_plan()["plan_digest"],
            "authority": authority,
            "replacement_training_allowed": False,
            "reused_fit_count": 155,
            "week6_smoke_fit_count": 60,
            "week7_baseline_fit_count": 95,
            "newly_executed_fit_count": 0,
            "sources": rows,
        },
        "ledger_digest",
    )


def _metadata_source_ledger(path: str | Path, expected_sha256: str) -> dict[str, Any]:
    """Validate metadata and independent authorities without reopening 310 trees.

    Fresh workers use this narrow helper, then reopen their own exact baseline
    source/copy pair.  Public loading always performs the full reconciliation.
    """

    target = _plain_file(Path(path))
    expected_sha = L._lower_sha256(expected_sha256, what="source ledger SHA256")
    if sha256_file(target) != expected_sha:
        raise ValueError("source ledger changed after the immutable preflight")
    document = read_json(target)
    authority, pins = source_authority()
    if type(document) is not dict or type(document.get("sources")) is not list:
        raise ValueError("source ledger must be an exact JSON object with source rows")
    rows = document["sources"]
    jobs = W.existing_exp2a_jobs()
    if len(rows) != len(jobs):
        raise ValueError("source ledger must name exactly 155 existing fits")
    expected_rows: list[dict[str, Any]] = []
    fields = {
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
    for row, job in zip(rows, jobs, strict=True):
        if type(row) is not dict or set(row) != fields:
            raise ValueError("source ledger row has missing or extra fields")
        source, copy = _source_paths(job)
        commit, execution_digest = pins[job.job_id]
        digests = {
            name: L._lower_sha256(row.get(name), what=name)
            for name in (
                "execution_digest",
                "sidecar_sha256",
                "source_tree_digest",
                "copy_tree_digest",
                "copy_evidence_digest",
            )
        }
        if digests["execution_digest"] != execution_digest:
            raise ValueError("source ledger changed an independently pinned execution digest")
        expected_rows.append(
            {
                "job": job.as_record(),
                "source_kind": W.source_kind(job),
                "source_path": str(source.resolve()),
                "copy_path": str(copy.resolve()),
                "expected_git_commit": commit,
                **digests,
                "independent_files": True,
            }
        )
    expected = W._seal(
        {
            "exp2a_source_ledger_schema_version": SOURCE_LEDGER_SCHEMA_VERSION,
            "purpose": "all_155_existing_exp2a_fits_reverified_not_reexecuted",
            "plan_digest": W.build_exp2a_repair_plan()["plan_digest"],
            "authority": authority,
            "replacement_training_allowed": False,
            "reused_fit_count": 155,
            "week6_smoke_fit_count": 60,
            "week7_baseline_fit_count": 95,
            "newly_executed_fit_count": 0,
            "sources": expected_rows,
        },
        "ledger_digest",
    )
    W._equal(document, expected, what="source ledger metadata")
    return document


def reverify_exp2a_source_ledger(document: object) -> dict[str, Any]:
    if type(document) is not dict:
        raise ValueError("Experiment-2A source ledger must be an exact JSON object")
    current = build_exp2a_source_ledger()
    W._equal(document, current, what="Experiment-2A source ledger")
    return current


def load_exp2a_source_ledger(path: str | Path) -> dict[str, Any]:
    target = _plain_file(Path(path))
    return reverify_exp2a_source_ledger(read_json(target))


def write_exp2a_source_ledger(directory: str | Path) -> Path:
    root = W._project_path(directory, directory=True)
    document = build_exp2a_source_ledger()
    path = atomic_write_json(root / SOURCE_LEDGER_FILE, document)
    W._equal(read_json(path), document, what="published Experiment-2A source ledger")
    return path
