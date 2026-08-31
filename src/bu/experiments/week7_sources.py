"""Reopen the five historical smoke baselines owed by Experiment 2A.

The authority is NOT a fit's own Git claim: D-147/D-149 independently pin
the original clean execution commit and the later label's five source digests.
The historical preflight, correction report and label are byte-pinned below;
only provenance metadata is parsed, never a label verdict or outcome statistic.
The complete fit reader still internally verifies experimental payloads on
every reconciliation, for both the original and independent project copy.

There is no discovery, replacement-training fallback, mutable source selection,
caller-provided commit/digest, cached verified-input token or executor. Missing
or corrupt history stops. Build/load/reverify return a JSON snapshot; launch,
resume and completion must reopen it rather than treating it as authority.
Copy-attestation digests (file identities plus hashes) are deliberately named
separately from content-only tree digests; they are different estimands.
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
from . import week7_launch_plan as P


WEEK7_SOURCE_LEDGER_SCHEMA_VERSION = 1
WEEK7_SOURCE_LEDGER_FILE = "week7_source_reuse_ledger.json"
PROJECT_ROOT = Path("D:/Aenv/pro/pro")
HISTORICAL_OUTPUT_ROOT = PROJECT_ROOT / "week6-smoke-2026-08-30-attempt-001-output"
HISTORICAL_COPY_ROOT = PROJECT_ROOT / "week6-smoke-2026-08-30-attempt-001-project-evidence"
HISTORICAL_PREFLIGHT_ROOT = PROJECT_ROOT / "week6-smoke-2026-08-30-attempt-001-preflight"
HISTORICAL_EXECUTION_COMMIT = "750266c7b8c4eb955b03f6081a861aed1051907b"
HISTORICAL_FINALIZER_COMMIT = "f6833f2eb0d0dc5652effdf4e1fc066722761d09"
HISTORICAL_PREFLIGHT_SHA256 = "216d1206c1145e98291ca1de028fff20519b35055ba54eeac5111ee54b33091e"
HISTORICAL_LABEL_SHA256 = "7e56f9a331a4e10a74b80568c86f527b1ae11ed483d76d45cd195fc945fee614"
HISTORICAL_FINALIZATION_FILE = "repair_label_finalization_reports/efdbd2081ab349fd835998ce5ee4e5eb.json"
HISTORICAL_FINALIZATION_SHA256 = "979df8c86c00c4feb390477912d8ea3adb4a46a5f19a6c424056a10549a485dd"

# Extracted from the independently finalized D-149 label's source-reference
# metadata, not from the sidecars being accepted and not from their outcomes.
# These are physical execution digests, not file SHA256s or copy attestations.
HISTORICAL_EXECUTION_DIGESTS = (
    "c5daacdf3e4305ca29d7806b86e7b5a2d580264cfbe79f615362b9130a2a21ac",
    "897c28c8a9c199a00d0572f5518a486022d3beedca4a86b65cd2cb8fb718959d",
    "075ad9be6dff1b014ca5381cd9506f4913940a64ac514b76a4ce38450ca8a525",
    "92be45b05bfc60aa3da1963e8f14bca61aeac681b48358b75f4fc6798a7409eb",
    "7f676a26483c64d3c015859cfbcff602e18ee933276530badbb44b43356a3496",
)


def _plain_path(path: Path, *, directory: bool) -> Path:
    """Refuse links/junctions through every ancestor before resolving identity."""
    if not path.is_absolute():
        raise ValueError("Week-7 source paths must be absolute and project-local")
    try:
        for component in (*reversed(path.parents), path):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            ):
                raise ValueError(f"Week-7 source path contains a link/junction: {component}")
        resolved = path.resolve(strict=True)
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
        mode = path.lstat().st_mode
        if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
            raise ValueError(f"Week-7 source path has the wrong file type: {path}")
    except (OSError, ValueError) as exc:
        raise ValueError(f"Week-7 source must be a plain project-local path: {path}: {exc}") from exc
    return resolved


def _pinned_pair(source: Path, copy: Path, expected_sha256: str) -> dict[str, Any]:
    source = _plain_path(source, directory=False)
    copy = _plain_path(copy, directory=False)
    if os.path.samefile(source, copy):
        raise ValueError("Historical source and project copy must be independent files")
    if sha256_file(source) != expected_sha256 or sha256_file(copy) != expected_sha256:
        raise ValueError("Historical authority bytes differ from the independently pinned digest")
    return {
        "source_path": str(source), "copy_path": str(copy),
        "sha256": expected_sha256, "independent_files": True,
    }


def _plain_tree(root: Path) -> None:
    # Windows junctions need not report S_ISLNK. Check their reparse attribute
    # before the shared tree hasher can traverse/read a redirected subtree.
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            _plain_path(Path(current) / name, directory=True)
        for name in files:
            _plain_path(Path(current) / name, directory=False)


def _authority() -> dict[str, Any]:
    preflight = _pinned_pair(
        HISTORICAL_PREFLIGHT_ROOT / "repair_label_preflight_report.json",
        HISTORICAL_COPY_ROOT / "repair_label_preflight_report.json",
        HISTORICAL_PREFLIGHT_SHA256,
    )
    label = _pinned_pair(
        HISTORICAL_OUTPUT_ROOT / "label_evidence.json",
        HISTORICAL_COPY_ROOT / "label_evidence.json", HISTORICAL_LABEL_SHA256,
    )
    finalization = _pinned_pair(
        HISTORICAL_OUTPUT_ROOT / HISTORICAL_FINALIZATION_FILE,
        HISTORICAL_COPY_ROOT / HISTORICAL_FINALIZATION_FILE,
        HISTORICAL_FINALIZATION_SHA256,
    )
    # Never take expected_git_commit from either this document or a fit. The
    # independently pinned literal remains the argument to both fit readers.
    historical = read_json(preflight["source_path"])
    try:
        git = historical["environment"]["git"]
        if (
            git["commit"] != HISTORICAL_EXECUTION_COMMIT
            or git["dirty"] is not False or git["trustworthy"] is not True
        ):
            raise ValueError("Historical preflight does not match the pinned clean execution")
    except (KeyError, TypeError) as exc:
        raise ValueError("Historical preflight lacks execution provenance") from exc
    return {
        "records": ["D-147", "D-149"],
        "execution_commit": HISTORICAL_EXECUTION_COMMIT,
        "finalizer_commit": HISTORICAL_FINALIZER_COMMIT,
        "preflight": preflight, "label_source_digest_authority": label,
        "finalization": finalization,
    }


def _verify_fit(path: Path, job: B.BatchJob, execution_digest: str) -> str:
    verified = F.load_fit_evidence(path, expected_git_commit=HISTORICAL_EXECUTION_COMMIT)
    if type(verified) is not F.VerifiedFitEvidence:
        raise ValueError("Week-7 reuse requires exact verified fit evidence")
    expected = {
        "unit": job.unit, "unit_id": job.config.unit_id,
        "config_id": job.config.config_id, "fit_id": job.job_id,
        "arm": job.arm, "seed": job.seed, "roles": job.roles,
        "execution_stage": job.stage, "execution_run_id": job.config.run_id,
        "execution_digest": execution_digest, "n_train": job.unit.n_transitions,
        "ensemble_size": job.config.train.ensemble_size,
    }
    for field, value in expected.items():
        actual = getattr(verified, field)
        if type(actual) is not type(value) or actual != value:
            raise ValueError(f"Historical reuse {job.job_id} differs at pinned {field}")
    if verified.fit_dir != path:
        raise ValueError("Historical fit reader returned a different source path")
    run_path = path / job.config.run_id / "run.json"
    run = read_json(_plain_path(run_path, directory=False))
    if type(run) is not dict or P._canonical(run.get("config")) != P._canonical(job.config.to_dict()):
        raise ValueError("Historical fit Config differs from full registered configuration")
    return sha256_file(_plain_path(path / F.FIT_EVIDENCE_FILE, directory=False))


def build_week7_source_ledger() -> dict[str, Any]:
    """Reopen all ten trees; no source/path/commit override and no fit execution."""
    jobs = P.reused_experiment_2a_jobs()
    if len(HISTORICAL_EXECUTION_DIGESTS) != len(jobs):
        raise ValueError("Historical execution-digest registry must cover exactly five fits")
    authority = _authority()
    original_root = _plain_path(HISTORICAL_OUTPUT_ROOT, directory=True)
    copy_root = _plain_path(HISTORICAL_COPY_ROOT, directory=True)
    if original_root == copy_root or original_root in copy_root.parents or copy_root in original_root.parents:
        raise ValueError("Historical original and copy roots must be non-overlapping")
    rows = []
    for job, digest in zip(jobs, HISTORICAL_EXECUTION_DIGESTS, strict=True):
        source = _plain_path(original_root / "jobs" / job.job_id, directory=True)
        copy = _plain_path(copy_root / "jobs" / job.job_id, directory=True)
        _plain_tree(source)
        _plain_tree(copy)
        before = B._copy_evidence_digest(source, copy)
        source_tree = B._job_tree_digest(source)
        copy_tree = B._job_tree_digest(copy)
        source_sidecar = _verify_fit(source, job, digest)
        copy_sidecar = _verify_fit(copy, job, digest)
        after = B._copy_evidence_digest(source, copy)
        if (
            before != after or source_tree != copy_tree or source_sidecar != copy_sidecar
            or B._job_tree_digest(source) != source_tree
            or B._job_tree_digest(copy) != copy_tree
        ):
            raise ValueError("Historical reuse changed while being reconciled")
        rows.append({
            "job": job.as_record(), "source_path": str(source), "copy_path": str(copy),
            "execution_commit": HISTORICAL_EXECUTION_COMMIT,
            "execution_digest": digest, "sidecar_sha256": source_sidecar,
            "source_tree_digest": source_tree, "copy_tree_digest": copy_tree,
            "copy_evidence_digest": after, "independent_files": True,
        })
    if P._canonical(_authority()) != P._canonical(authority):
        raise ValueError("Historical authority changed during source reconciliation")
    payload = {
        "week7_source_ledger_schema_version": WEEK7_SOURCE_LEDGER_SCHEMA_VERSION,
        "purpose": "five_existing_exp2a_baselines_reverified_not_reexecuted",
        "historical_execution_commit": HISTORICAL_EXECUTION_COMMIT,
        "authority": authority,
        "reused_fit_count": 5, "newly_executed_fit_count": 0,
        "replacement_training_allowed": False,
        "reuse_inside_new_batch_directories_allowed": False,
        "sources": rows,
    }
    return {**payload, "ledger_digest": hashlib.sha256(P._canonical(payload)).hexdigest()}


def reverify_week7_source_ledger(document: object) -> dict[str, Any]:
    """Reopen history and require exact equality; never trust a cached snapshot."""
    if type(document) is not dict:
        raise ValueError("Week-7 source reuse ledger must be an exact JSON object")
    # Validate JSON before accessing experimental payloads.
    encoded = P._canonical(document)
    current = build_week7_source_ledger()
    if encoded != P._canonical(current):
        raise ValueError("Week-7 source reuse ledger differs from pinned/reopened history")
    return current


def load_week7_source_ledger(path: str | Path) -> dict[str, Any]:
    """Reload a regular project-local ledger AND both copies of all five fits."""
    target = _plain_path(Path(path), directory=False)
    return reverify_week7_source_ledger(read_json(target))


def write_week7_source_ledger(directory: str | Path) -> Path:
    """Publish one immutable ledger; refuse divergence, preserve historical files."""
    root = _plain_path(Path(directory), directory=True)
    document = build_week7_source_ledger()
    path = atomic_write_json(root / WEEK7_SOURCE_LEDGER_FILE, document)
    if P._canonical(read_json(path)) != P._canonical(document):
        raise ValueError("Published Week-7 source ledger differs from verified memory")
    return path
