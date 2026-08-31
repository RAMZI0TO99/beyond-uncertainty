"""Exact Week-7 baseline readiness, with project-local independent evidence.

This adapter does not relax either historical public preflight. It binds the
entire Week-7 plan, all five historical reuse sources and one initially enabled
batch. A ready report is not permission to substitute jobs or retrain reuse.
"""

from __future__ import annotations

import argparse
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..durable import atomic_write_json, read_json, sha256_file
from ..runrecord import PROJECT_ROOT
from . import batch as B
from . import launch as L
from . import preflight as P
from . import repair_label_preflight as RF


WEEK7_PREFLIGHT_SCHEMA_VERSION = 1
WEEK7_PREFLIGHT_FILE = "week7_preflight_report.json"
WORKSPACE_ROOT = PROJECT_ROOT.parent


@dataclass(frozen=True)
class ValidatedWeek7Preflight:
    report_path: Path
    report_sha256: str
    git_commit: str
    roots: Mapping[str, Path]
    jobs: tuple[B.BatchJob, ...]
    report: Mapping[str, Any]


def _project_path(path: str | Path, *, what: str, directory: bool) -> Path:
    """Refuse lexical links before resolution and enforce the owner's boundary."""
    candidate = Path(path).absolute()
    # Junctions may have directory mode without S_ISLNK on Windows. Inspect
    # every lexical component, including the leaf, before resolve can erase
    # that redirection. The historical shared path helper remains unchanged.
    for component in (*reversed(candidate.parents), candidate):
        try:
            info = component.lstat()
        except OSError as exc:
            raise ValueError(f"{what} is unavailable: {exc}") from exc
        reparse = getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        )
        if stat.S_ISLNK(info.st_mode) or reparse:
            raise ValueError(f"{what} contains a link/reparse-point component: {component}")
        if component != candidate and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"{what} has a non-directory ancestor: {component}")
    if not directory:
        RF._regular_file(candidate, what=what)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"{what} is unavailable: {exc}") from exc
    workspace = WORKSPACE_ROOT.resolve(strict=True)
    if not resolved.is_relative_to(workspace) or resolved == workspace:
        raise ValueError(f"{what} must be inside the project workspace: {resolved}")
    if directory and not resolved.is_dir():
        raise ValueError(f"{what} must be a directory")
    return resolved


def _same_document(source: Path, destination: Path) -> None:
    RF._regular_file(source, what="local readiness evidence")
    RF._regular_file(destination, what="independent readiness evidence")
    if RF._same_file_identity(source, destination):
        raise ValueError("readiness copy aliases its local source")
    if source.read_bytes() != destination.read_bytes():
        raise ValueError("readiness source and independent copy differ")


def _input_files(plan_path: str | Path, reuse_ledger_path: str | Path):
    # Deferred imports avoid a shared registry/import cycle. The narrow loaders
    # rederive semantic inventories; a self-consistent hash is not sufficient.
    from . import week7_launch_plan as LP
    from . import week7_sources as WS

    plan_file = _project_path(plan_path, what="Week-7 launch plan", directory=False)
    ledger_file = _project_path(
        reuse_ledger_path, what="Week-7 reuse ledger", directory=False
    )
    plan = LP.load_week7_launch_plan(plan_file)
    ledger = WS.load_week7_source_ledger(ledger_file)
    return plan_file, plan, ledger_file, ledger


def _batch_jobs(plan: Mapping[str, Any], batch_key: str) -> tuple[B.BatchJob, ...]:
    from . import week7_launch_plan as LP

    return LP.jobs_for_batch(plan, batch_key)


def _bound_inputs(plan_file: Path, ledger_file: Path) -> dict[str, Any]:
    return {
        "plan": {"path": str(plan_file), "sha256": sha256_file(plan_file)},
        "reuse_ledger": {"path": str(ledger_file), "sha256": sha256_file(ledger_file)},
    }


def _protect_roots(roots: Mapping[str, Path], inputs: Mapping[str, Any]) -> None:
    from . import week7_sources as WS

    for name, root in roots.items():
        _project_path(root, what=f"{name} root", directory=True)
        if P._overlap(root, _control_root()):
            raise ValueError("execution roots overlap the common Week-7 lease root")
        for historical in (WS.HISTORICAL_OUTPUT_ROOT, WS.HISTORICAL_COPY_ROOT,
                           WS.HISTORICAL_PREFLIGHT_ROOT):
            if P._overlap(root, historical.resolve(strict=False)):
                raise ValueError("Week-7 execution roots overlap immutable historical reuse")
    L._validate_same_volume_staging(roots["output"], roots["staging"])
    for evidence in inputs.values():
        path = Path(evidence["path"])
        if any(path.is_relative_to(root) for root in roots.values()):
            raise ValueError("original plan/reuse ledger must be outside execution roots")


def _control_root() -> Path:
    """One workspace-wide lease prevents concurrent Week-7 production owners."""
    root = _project_path(WORKSPACE_ROOT / "week7-production-control",
                         what="common Week-7 control root", directory=True)
    # Acquisition can create the namespace, but must not write through an
    # existing redirected leases/history directory or transition-lock file.
    lease_directory = root / "leases"
    try:
        lease_directory.lstat()
    except FileNotFoundError:
        return root
    except OSError as exc:
        raise ValueError(f"common Week-7 lease directory is unavailable: {exc}") from exc
    _project_path(lease_directory, what="common Week-7 lease directory", directory=True)
    for child in lease_directory.iterdir():
        try:
            info = child.lstat()
        except OSError as exc:
            raise ValueError(f"common Week-7 lease entry is unavailable: {exc}") from exc
        _project_path(child, what="common Week-7 lease entry",
                      directory=stat.S_ISDIR(info.st_mode))
    return root


def run_week7_preflight(
    *, plan_path: str | Path, reuse_ledger_path: str | Path, batch_key: str,
    preflight_dir: str | Path, output_root: str | Path, staging_root: str | Path,
    sync_root: str | Path, sync_destination_identity: str,
    minimum_free_bytes: int,
) -> dict[str, Any]:
    """Persist exact readiness and independent readback copies; execute nothing."""
    plan_file, plan, ledger_file, _ = _input_files(plan_path, reuse_ledger_path)
    jobs = _batch_jobs(plan, batch_key)
    environment = L._current_environment()
    device = P._verify_device("cpu")
    destination = P._validate_destination_identity(sync_destination_identity)
    # Validate raw paths before the generic storage helper resolves aliases.
    for name, path in (("preflight", preflight_dir), ("output", output_root),
                       ("staging", staging_root), ("sync", sync_root)):
        _project_path(path, what=name, directory=True)
    roots, storage = P._verify_storage(
        preflight_dir=preflight_dir, output_root=output_root,
        staging_root=staging_root, sync_root=sync_root,
        minimum_free_bytes=minimum_free_bytes,
    )
    inputs = _bound_inputs(plan_file, ledger_file)
    _protect_roots(roots, inputs)
    manifest = B._manifest(jobs)
    binding = P.sha256_bytes(P._canonical_json_bytes({
        "inputs": inputs, "batch_key": batch_key, "manifest": manifest,
    }))
    canary, receipt = P._run_sync_canary(
        roots=roots, plan_digest=binding, destination_identity=destination,
        adapter=P.sync_canary_to_mounted_directory,
    )
    _same_document(Path(canary["source_path"]), Path(canary["destination_path"]))
    for name, source in (("week7_launch_plan.json", plan_file),
                         ("week7_reuse_ledger.json", ledger_file)):
        RF.sync_immutable_file(source, roots["preflight"] / name)
        RF.sync_immutable_file(source, roots["sync"] / name)
    report = {
        "week7_preflight_schema_version": WEEK7_PREFLIGHT_SCHEMA_VERSION,
        "status": "ready", "launch_performed": False,
        "inputs": inputs, "batch_key": batch_key,
        "batch": manifest, "binding_sha256": binding,
        "control_root": str(_control_root()),
        "environment": environment, "device": device, "storage": storage,
        "sync_canary": canary, "sync_receipt": receipt,
    }
    path = atomic_write_json(roots["preflight"] / WEEK7_PREFLIGHT_FILE, report)
    RF.sync_immutable_file(path, roots["sync"] / WEEK7_PREFLIGHT_FILE)
    validate_week7_preflight(path, output_root=output_root, sync_root=sync_root)
    return report


def validate_week7_preflight(
    path: str | Path, *, output_root: str | Path, sync_root: str | Path,
) -> ValidatedWeek7Preflight:
    """Reopen all reuse evidence and rederive every claim before any launch."""
    report_path = _project_path(path, what="Week-7 preflight", directory=False)
    if report_path.name != WEEK7_PREFLIGHT_FILE:
        raise ValueError("not the canonical Week-7 preflight filename")
    raw = report_path.read_bytes()
    report = L._strict_keys(read_json(report_path), {
        "week7_preflight_schema_version", "status", "launch_performed", "inputs",
        "batch_key", "batch", "binding_sha256", "environment", "device",
        "storage", "sync_canary", "sync_receipt", "control_root",
    }, what="Week-7 preflight")
    if raw != L._pretty_json_bytes(report):
        raise ValueError("Week-7 preflight is not canonical immutable JSON")
    if (type(report["week7_preflight_schema_version"]) is not int
            or report["week7_preflight_schema_version"] != WEEK7_PREFLIGHT_SCHEMA_VERSION
            or report["status"] != "ready" or report["launch_performed"] is not False):
        raise ValueError("Week-7 preflight is not a ready schema-1 report")
    if report["control_root"] != str(_control_root()):
        raise ValueError("Week-7 preflight names a different common lease root")
    inputs = L._strict_keys(report["inputs"], {"plan", "reuse_ledger"}, what="inputs")
    for name, value in inputs.items():
        row = L._strict_keys(value, {"path", "sha256"}, what=name)
        _project_path(row["path"], what=name, directory=False)
        L._lower_sha256(row["sha256"], what=name)
    plan_file, plan, ledger_file, _ = _input_files(
        inputs["plan"]["path"], inputs["reuse_ledger"]["path"]
    )
    if inputs != _bound_inputs(plan_file, ledger_file):
        raise ValueError("Week-7 plan/reuse ledger changed since preflight")
    jobs = _batch_jobs(plan, report["batch_key"])
    manifest = B._manifest(jobs)
    if P._canonical_json_bytes(report["batch"]) != P._canonical_json_bytes(manifest):
        raise ValueError("Week-7 batch differs from exact activated jobs")
    binding = P.sha256_bytes(P._canonical_json_bytes({
        "inputs": inputs, "batch_key": report["batch_key"], "manifest": manifest,
    }))
    if report["binding_sha256"] != binding:
        raise ValueError("Week-7 preflight input/batch binding differs")
    environment = L._validate_environment(report["environment"])
    L._validate_device(report["device"])
    roots = L._validate_storage(
        report["storage"], report_parent=report_path.parent,
        requested_output=_project_path(output_root, what="output", directory=True),
        requested_sync=_project_path(sync_root, what="sync", directory=True),
    )
    _protect_roots(roots, inputs)
    L._validate_sync_evidence(report, roots=roots, plan_sha256=binding)
    _same_document(Path(report["sync_canary"]["source_path"]),
                   Path(report["sync_canary"]["destination_path"]))
    for name, source in (("week7_launch_plan.json", plan_file),
                         ("week7_reuse_ledger.json", ledger_file)):
        _same_document(source, roots["preflight"] / name)
        _same_document(source, roots["sync"] / name)
    _same_document(report_path, roots["sync"] / WEEK7_PREFLIGHT_FILE)
    if report_path.read_bytes() != raw:
        raise ValueError("Week-7 preflight changed during verification")
    return ValidatedWeek7Preflight(
        report_path, P.sha256_bytes(raw), environment["git"]["commit"], roots,
        jobs, report,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan-path", "reuse-ledger-path", "preflight-dir", "output-root",
                 "staging-root", "sync-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--batch-key", required=True)
    parser.add_argument("--sync-destination-identity", required=True)
    parser.add_argument("--minimum-free-bytes", type=int, required=True)
    run_week7_preflight(**vars(parser.parse_args(argv)))
    print("Week-7 readiness verified and copied; no fit launched.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
