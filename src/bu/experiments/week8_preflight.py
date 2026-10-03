"""Fail-closed readiness gate for one exact Week-8 baseline batch."""

from __future__ import annotations

import argparse
import os
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
from . import supervisor as S
from . import week8_plan as LP


WEEK8_PREFLIGHT_SCHEMA_VERSION = 1
WEEK8_PREFLIGHT_FILE = "week8_preflight_report.json"
WEEK8_MINIMUM_FREE_BYTES = 8_589_934_592
WORKSPACE_ROOT = PROJECT_ROOT.parent
COMMON_CONTROL_DIRECTORY = "week7-production-control"
ROOT_CLAIM_SCHEMA_VERSION = 1
ROOT_CLAIM_DIRECTORY = "week8-baseline-root-claims"
ROOT_CLAIM_LOCK = ".week8-baseline-root-claims.lock"

# These direct workspace children are immutable inputs or historical evidence,
# never destinations for a Week-8 baseline batch.  Week-8 baseline-to-baseline
# separation is additionally enforced by the persistent root claims below.
_IMMUTABLE_SOURCE_PREFIXES = (
    "week6-",
    "week7-",
    "week8-execution-preparation-",
    "week8-exp2a-",
    "week8-exp2a-labels-",
    "week8-exclusion-",
    "week8-analysis-",
    "week8-monitor-",
)


@dataclass(frozen=True)
class ValidatedWeek8Preflight:
    report_path: Path
    report_sha256: str
    git_commit: str
    roots: Mapping[str, Path]
    jobs: tuple[B.BatchJob, ...]
    report: Mapping[str, Any]


def _project_path(path: str | Path, *, what: str, directory: bool) -> Path:
    """Reject lexical redirection before resolution and stay project-local."""
    candidate = Path(path).absolute()
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


def _input_file(plan_path: str | Path) -> tuple[Path, dict[str, Any]]:
    plan_file = _project_path(plan_path, what="Week-8 launch plan", directory=False)
    return plan_file, LP.load_week8_launch_plan(plan_file)


def _batch_jobs(plan: Mapping[str, Any], batch_key: str) -> tuple[B.BatchJob, ...]:
    return LP.jobs_for_batch(plan, batch_key)


def _bound_input(plan_file: Path) -> dict[str, Any]:
    return {"path": str(plan_file), "sha256": sha256_file(plan_file)}


def _control_root() -> Path:
    """Use the same lease namespace as Week 7; never recover by age."""
    root = _project_path(
        WORKSPACE_ROOT / COMMON_CONTROL_DIRECTORY,
        what="common Week-7/8 control root",
        directory=True,
    )
    lease_directory = root / "leases"
    try:
        lease_directory.lstat()
    except FileNotFoundError:
        return root
    except OSError as exc:
        raise ValueError(f"common production lease directory is unavailable: {exc}") from exc
    _project_path(lease_directory, what="common production lease directory", directory=True)
    for child in lease_directory.iterdir():
        try:
            info = child.lstat()
        except OSError as exc:
            raise ValueError(f"common production lease entry is unavailable: {exc}") from exc
        _project_path(
            child,
            what="common production lease entry",
            directory=stat.S_ISDIR(info.st_mode),
        )
    return root


def _immutable_source_roots() -> tuple[Path, ...]:
    """Return every existing direct historical/source root, fail-closed."""
    workspace = WORKSPACE_ROOT.resolve(strict=True)
    protected: list[Path] = [PROJECT_ROOT.resolve(strict=True)]
    for child in workspace.iterdir():
        if child.name == COMMON_CONTROL_DIRECTORY or not child.name.startswith(
            _IMMUTABLE_SOURCE_PREFIXES
        ):
            continue
        try:
            info = child.lstat()
        except OSError as exc:
            raise ValueError(f"historical/source root is unavailable: {child}: {exc}") from exc
        protected.append(
            _project_path(
                child,
                what="immutable historical/source root",
                directory=stat.S_ISDIR(info.st_mode),
            )
        )
    return tuple(sorted(protected, key=str))


def _claim_directory(*, create: bool) -> Path | None:
    candidate = _control_root() / ROOT_CLAIM_DIRECTORY
    if not os.path.lexists(candidate):
        if not create:
            return None
        return RF.ensure_regular_child_directory(_control_root(), ROOT_CLAIM_DIRECTORY)
    return _project_path(candidate, what="Week-8 root-claim directory", directory=True)


def _read_root_claims() -> dict[str, dict[str, Path]]:
    """Read all immutable cross-batch root reservations."""
    directory = _claim_directory(create=False)
    if directory is None:
        return {}
    claims: dict[str, dict[str, Path]] = {}
    for child in sorted(directory.iterdir(), key=lambda item: item.name):
        RF._regular_file(child, what="Week-8 root claim")
        raw = child.read_bytes()
        record = L._strict_keys(
            read_json(child),
            {"week8_root_claim_schema_version", "batch_key", "roots"},
            what="Week-8 root claim",
        )
        batch_key = record["batch_key"]
        if (
            type(record["week8_root_claim_schema_version"]) is not int
            or record["week8_root_claim_schema_version"] != ROOT_CLAIM_SCHEMA_VERSION
            or type(batch_key) is not str
            or batch_key not in LP.AUTHORIZED_BATCH_KEYS
            or child.name != f"{batch_key}.json"
            or raw != L._pretty_json_bytes(record)
            or batch_key in claims
        ):
            raise ValueError("Week-8 root claim is not canonical registered evidence")
        root_values = L._strict_keys(
            record["roots"],
            {"preflight", "output", "staging", "sync"},
            what="claimed Week-8 roots",
        )
        claimed = {
            name: _project_path(value, what=f"claimed {name} root", directory=True)
            for name, value in root_values.items()
        }
        if root_values != {name: str(path) for name, path in claimed.items()}:
            raise ValueError("Week-8 root claim paths are not canonical")
        claims[batch_key] = claimed
    return claims


def _claim_roots(batch_key: str, roots: Mapping[str, Path], plan_file: Path) -> None:
    """Atomically reserve roots before any execution-root write."""
    control = _control_root()
    guard = control / ROOT_CLAIM_LOCK
    if os.path.lexists(guard):
        RF._regular_file(guard, what="Week-8 root-claim transition lock")
    with S._lease_transition_lock(guard):
        RF._regular_file(guard, what="Week-8 root-claim transition lock")
        _protect_roots(
            roots,
            plan_file,
            batch_key=batch_key,
            require_current_claim=False,
        )
        claims = _read_root_claims()
        if batch_key not in claims:
            for name, root in roots.items():
                try:
                    entries = tuple(root.iterdir())
                except OSError as exc:
                    raise ValueError(
                        f"cannot inspect unclaimed Week-8 {name} root: {exc}"
                    ) from exc
                if entries:
                    raise ValueError(
                        f"unclaimed Week-8 {name} root must be empty before its "
                        "immutable reservation"
                    )
        directory = _claim_directory(create=True)
        if directory is None:  # pragma: no cover - narrowed by create=True
            raise RuntimeError("could not create Week-8 root-claim directory")
        record = {
            "week8_root_claim_schema_version": ROOT_CLAIM_SCHEMA_VERSION,
            "batch_key": batch_key,
            "roots": {name: str(roots[name]) for name in sorted(roots)},
        }
        path = atomic_write_json(directory / f"{batch_key}.json", record)
        RF._regular_file(path, what="Week-8 root claim")
        if read_json(path) != record:
            raise ValueError("persisted Week-8 root claim differs from reservation")
        _protect_roots(
            roots,
            plan_file,
            batch_key=batch_key,
            require_current_claim=True,
        )


def _protect_roots(
    roots: Mapping[str, Path],
    plan_file: Path,
    *,
    batch_key: str,
    require_current_claim: bool,
) -> None:
    if type(batch_key) is not str or batch_key not in LP.AUTHORIZED_BATCH_KEYS:
        raise ValueError("Week-8 root protection requires an authorized batch key")
    control = _control_root()
    immutable_sources = _immutable_source_roots()
    for name, root in roots.items():
        _project_path(root, what=f"{name} root", directory=True)
        if P._overlap(root, control):
            raise ValueError("execution roots overlap the common Week-7/8 lease root")
        for protected in immutable_sources:
            if P._overlap(root, protected):
                raise ValueError(
                    f"{name} root overlaps immutable historical/source evidence: "
                    f"{protected}"
                )
    claims = _read_root_claims()
    current = claims.get(batch_key)
    canonical = {name: roots[name] for name in sorted(roots)}
    if current is not None and current != canonical:
        raise ValueError(f"{batch_key} already has a different immutable root claim")
    if require_current_claim and current != canonical:
        raise ValueError(f"{batch_key} has no exact immutable root claim")
    for other_batch, claimed in claims.items():
        if other_batch == batch_key:
            continue
        for name, root in roots.items():
            for claimed_name, claimed_root in claimed.items():
                if P._overlap(root, claimed_root):
                    raise ValueError(
                        f"{name} root overlaps {other_batch} claimed "
                        f"{claimed_name} root"
                    )
    L._validate_same_volume_staging(roots["output"], roots["staging"])
    if any(plan_file.is_relative_to(root) for root in roots.values()):
        raise ValueError("original Week-8 plan must be outside execution roots")


def run_week8_preflight(
    *,
    plan_path: str | Path,
    batch_key: str,
    preflight_dir: str | Path,
    output_root: str | Path,
    staging_root: str | Path,
    sync_root: str | Path,
    sync_destination_identity: str,
    minimum_free_bytes: int = WEEK8_MINIMUM_FREE_BYTES,
) -> dict[str, Any]:
    """Persist readiness and independent copies; perform no fit or analysis."""
    if (
        type(minimum_free_bytes) is not int
        or minimum_free_bytes != WEEK8_MINIMUM_FREE_BYTES
    ):
        raise ValueError(
            "Week-8 minimum_free_bytes is frozen at exactly 8,589,934,592"
        )
    plan_file, plan = _input_file(plan_path)
    jobs = _batch_jobs(plan, batch_key)
    environment = L._current_environment()
    device = P._verify_device("cpu")
    destination = P._validate_destination_identity(sync_destination_identity)
    for name, path in (
        ("preflight", preflight_dir),
        ("output", output_root),
        ("staging", staging_root),
        ("sync", sync_root),
    ):
        _project_path(path, what=name, directory=True)
    roots, storage = P._verify_storage(
        preflight_dir=preflight_dir,
        output_root=output_root,
        staging_root=staging_root,
        sync_root=sync_root,
        minimum_free_bytes=minimum_free_bytes,
    )
    _protect_roots(
        roots,
        plan_file,
        batch_key=batch_key,
        require_current_claim=False,
    )
    _claim_roots(batch_key, roots, plan_file)
    source = _bound_input(plan_file)
    manifest = B._manifest(jobs)
    binding = P.sha256_bytes(
        P._canonical_json_bytes(
            {"plan": source, "batch_key": batch_key, "manifest": manifest}
        )
    )
    canary, receipt = P._run_sync_canary(
        roots=roots,
        plan_digest=binding,
        destination_identity=destination,
        adapter=P.sync_canary_to_mounted_directory,
    )
    _same_document(Path(canary["source_path"]), Path(canary["destination_path"]))
    for root in (roots["preflight"], roots["sync"]):
        RF.sync_immutable_file(plan_file, root / "week8_launch_plan.json")
    report = {
        "week8_preflight_schema_version": WEEK8_PREFLIGHT_SCHEMA_VERSION,
        "status": "ready",
        "launch_performed": False,
        "plan": source,
        "batch_key": batch_key,
        "batch": manifest,
        "binding_sha256": binding,
        "control_root": str(_control_root()),
        "environment": environment,
        "device": device,
        "storage": storage,
        "sync_canary": canary,
        "sync_receipt": receipt,
        "scientific_analysis_performed": False,
    }
    path = atomic_write_json(roots["preflight"] / WEEK8_PREFLIGHT_FILE, report)
    RF.sync_immutable_file(path, roots["sync"] / WEEK8_PREFLIGHT_FILE)
    validate_week8_preflight(path, output_root=output_root, sync_root=sync_root)
    return report


def validate_week8_preflight(
    path: str | Path,
    *,
    output_root: str | Path,
    sync_root: str | Path,
) -> ValidatedWeek8Preflight:
    """Reopen the exact plan and rederive every claim before launch."""
    report_path = _project_path(path, what="Week-8 preflight", directory=False)
    if report_path.name != WEEK8_PREFLIGHT_FILE:
        raise ValueError("not the canonical Week-8 preflight filename")
    raw = report_path.read_bytes()
    report = L._strict_keys(
        read_json(report_path),
        {
            "week8_preflight_schema_version",
            "status",
            "launch_performed",
            "plan",
            "batch_key",
            "batch",
            "binding_sha256",
            "control_root",
            "environment",
            "device",
            "storage",
            "sync_canary",
            "sync_receipt",
            "scientific_analysis_performed",
        },
        what="Week-8 preflight",
    )
    if raw != L._pretty_json_bytes(report):
        raise ValueError("Week-8 preflight is not canonical immutable JSON")
    if (
        type(report["week8_preflight_schema_version"]) is not int
        or report["week8_preflight_schema_version"] != WEEK8_PREFLIGHT_SCHEMA_VERSION
        or report["status"] != "ready"
        or report["launch_performed"] is not False
        or report["scientific_analysis_performed"] is not False
    ):
        raise ValueError("Week-8 preflight is not a ready schema-1 report")
    if report["control_root"] != str(_control_root()):
        raise ValueError("Week-8 preflight names a different common lease root")
    source = L._strict_keys(report["plan"], {"path", "sha256"}, what="plan")
    _project_path(source["path"], what="plan", directory=False)
    L._lower_sha256(source["sha256"], what="plan")
    plan_file, plan = _input_file(source["path"])
    if source != _bound_input(plan_file):
        raise ValueError("Week-8 plan changed since preflight")
    jobs = _batch_jobs(plan, report["batch_key"])
    manifest = B._manifest(jobs)
    if P._canonical_json_bytes(report["batch"]) != P._canonical_json_bytes(manifest):
        raise ValueError("Week-8 batch differs from exact activated jobs")
    binding = P.sha256_bytes(
        P._canonical_json_bytes(
            {"plan": source, "batch_key": report["batch_key"], "manifest": manifest}
        )
    )
    if report["binding_sha256"] != binding:
        raise ValueError("Week-8 preflight input/batch binding differs")
    environment = L._validate_environment(report["environment"])
    L._validate_device(report["device"])
    floor = (
        None
        if type(report["storage"]) is not dict
        else report["storage"].get("minimum_free_bytes")
    )
    if type(floor) is not int or floor != WEEK8_MINIMUM_FREE_BYTES:
        raise ValueError(
            "Week-8 preflight does not bind the exact 8-GiB storage floor"
        )
    roots = L._validate_storage(
        report["storage"],
        report_parent=report_path.parent,
        requested_output=_project_path(output_root, what="output", directory=True),
        requested_sync=_project_path(sync_root, what="sync", directory=True),
    )
    _protect_roots(
        roots,
        plan_file,
        batch_key=report["batch_key"],
        require_current_claim=True,
    )
    L._validate_sync_evidence(report, roots=roots, plan_sha256=binding)
    _same_document(
        Path(report["sync_canary"]["source_path"]),
        Path(report["sync_canary"]["destination_path"]),
    )
    _same_document(plan_file, roots["preflight"] / "week8_launch_plan.json")
    _same_document(plan_file, roots["sync"] / "week8_launch_plan.json")
    _same_document(report_path, roots["sync"] / WEEK8_PREFLIGHT_FILE)
    if report_path.read_bytes() != raw:
        raise ValueError("Week-8 preflight changed during verification")
    return ValidatedWeek8Preflight(
        report_path=report_path,
        report_sha256=P.sha256_bytes(raw),
        git_commit=environment["git"]["commit"],
        roots=roots,
        jobs=jobs,
        report=report,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "plan-path",
        "preflight-dir",
        "output-root",
        "staging-root",
        "sync-root",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--batch-key", required=True)
    parser.add_argument("--sync-destination-identity", required=True)
    run_week8_preflight(**vars(parser.parse_args(argv)))
    print("Week-8 readiness verified and copied; no fit launched.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
