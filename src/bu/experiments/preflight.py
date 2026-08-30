"""Fail-closed preflight for the unattended Experiment-1 launch.

This module verifies readiness; it never executes a fit.  Its only filesystem
mutations are an immutable local canary, the adapter's copy of that canary, and
an immutable ``preflight_report.json`` inside a caller-selected preflight
directory.  Output and staging roots are inspected without probe writes.

The sync boundary is deliberately stronger than a callback that merely returns
without raising.  The adapter must publish the exact canary at the prescribed
destination and return a typed, versioned receipt.  The preflight then reads the
destination back and verifies its identity, path, size, and SHA256 digest.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import stat
import sys
import tomllib
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch

from .. import constants as K
from ..durable import atomic_write_bytes, atomic_write_json, sha256_bytes, sha256_file
from ..runrecord import (
    PROJECT_ROOT,
    TRACKED_PACKAGES,
    GitState,
    git_state,
    package_versions,
)
from .batch import BatchJob, experiment_1_jobs
from .confirmatory import CONFIRMATORY_DEVICE


PREFLIGHT_SCHEMA_VERSION = 1
SYNC_RECEIPT_SCHEMA_VERSION = 1
PREFLIGHT_REPORT_FILE = "preflight_report.json"
SYNC_CANARY_FILE = "preflight_sync_canary.json"


@dataclass(frozen=True)
class SyncCanaryReceipt:
    """The adapter's attestation for one read-back-verifiable canary copy."""

    schema_version: int
    destination_identity: str
    destination_path: str
    sha256: str
    size_bytes: int


SyncCanaryAdapter = Callable[[Path, Path, str], SyncCanaryReceipt]


def sync_canary_to_mounted_directory(
    source: Path,
    destination: Path,
    destination_identity: str,
) -> SyncCanaryReceipt:
    """Copy one canary to the prescribed mounted destination and attest it."""

    data = Path(source).read_bytes()
    atomic_write_bytes(Path(destination), data)
    copied = Path(destination).resolve(strict=True)
    return SyncCanaryReceipt(
        schema_version=SYNC_RECEIPT_SCHEMA_VERSION,
        destination_identity=destination_identity,
        destination_path=str(copied),
        sha256=sha256_bytes(data),
        size_bytes=len(data),
    )


def _canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"preflight value is not strict JSON: {exc}") from exc
    return (text + "\n").encode("utf-8")


def _normalise_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _pinned_package_versions() -> dict[str, str]:
    """Read exact runtime pins for every recorded package from pyproject.toml."""

    path = PROJECT_ROOT / "pyproject.toml"
    try:
        with path.open("rb") as handle:
            document = tomllib.load(handle)
        dependencies = document["project"]["dependencies"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read project dependency pins from {path}: {exc}") from exc
    if type(dependencies) is not list or any(type(item) is not str for item in dependencies):
        raise ValueError("pyproject project.dependencies must be a list of strings")

    exact: dict[str, str] = {}
    for dependency in dependencies:
        match = re.fullmatch(
            r"([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)==([^\s;]+)",
            dependency,
        )
        if match is None:
            continue
        name, version = match.groups()
        key = _normalise_distribution(name)
        if key in exact:
            raise ValueError(f"duplicate exact dependency pin for {name!r}")
        exact[key] = version

    pins: dict[str, str] = {}
    for package in TRACKED_PACKAGES:
        key = _normalise_distribution(package)
        if key not in exact:
            raise ValueError(
                f"tracked package {package!r} has no exact == pin in {path}"
            )
        pins[package] = exact[key]
    return pins


def _verify_environment() -> tuple[GitState, dict[str, str], dict[str, str]]:
    state = git_state()
    if type(state) is not GitState:
        raise ValueError(f"git_state returned {type(state).__name__}, not GitState")
    if not state.identifies_commit:
        raise ValueError(
            f"project Git state does not name a lowercase 40-hex commit: {state.commit!r}"
        )
    if state.dirty or not state.trustworthy:
        raise ValueError(
            f"project Git state is not a clean trustworthy commit "
            f"(commit={state.commit!r}, dirty={state.dirty!r})"
        )

    pins = _pinned_package_versions()
    observed = package_versions()
    if not isinstance(observed, Mapping):
        raise ValueError("package_versions did not return a mapping")
    versions: dict[str, str] = {}
    mismatches: list[str] = []
    for package in TRACKED_PACKAGES:
        value = observed.get(package)
        if type(value) is not str:
            mismatches.append(f"{package}: observed {value!r}, pinned {pins[package]!r}")
            continue
        versions[package] = value
        if value != pins[package]:
            mismatches.append(f"{package}: observed {value!r}, pinned {pins[package]!r}")
    if mismatches:
        raise ValueError(
            "tracked package versions do not match exact pyproject pins: "
            + "; ".join(mismatches)
        )
    return state, versions, pins


def _device_available(device: str) -> bool:
    """Return whether the exact frozen torch route can execute a trivial tensor."""

    try:
        parsed = torch.device(device)
    except (RuntimeError, TypeError, ValueError):
        return False
    if parsed.type == "cuda" and not torch.cuda.is_available():
        return False
    if parsed.type == "mps":
        backend = getattr(torch.backends, "mps", None)
        if backend is None or not backend.is_available():
            return False
    try:
        torch.empty(0, device=parsed)
    except (RuntimeError, AssertionError, OSError):
        return False
    return True


def _verify_device(execution_route: str) -> dict[str, Any]:
    if type(execution_route) is not str or not execution_route:
        raise ValueError("execution_route must be a nonempty exact string")
    if execution_route != CONFIRMATORY_DEVICE:
        raise ValueError(
            f"requested execution route {execution_route!r} is not the frozen "
            f"confirmatory route {CONFIRMATORY_DEVICE!r}"
        )
    available = _device_available(CONFIRMATORY_DEVICE)
    if available is not True:
        raise ValueError(
            f"frozen confirmatory device {CONFIRMATORY_DEVICE!r} is unavailable"
        )
    return {
        "frozen_route": CONFIRMATORY_DEVICE,
        "requested_route": execution_route,
        "available": True,
    }


def _verify_plan(jobs: Sequence[BatchJob]) -> dict[str, Any]:
    if not isinstance(jobs, Sequence) or isinstance(jobs, (str, bytes)):
        raise ValueError("experiment_1_jobs must return a sequence")
    if len(jobs) != 150:
        raise ValueError(
            f"Experiment-1 plan has {len(jobs)} jobs, not the registered 150"
        )
    if any(type(job) is not BatchJob for job in jobs):
        raise ValueError("Experiment-1 plan contains a non-exact BatchJob")

    fit_ids = [job.config.fit_id for job in jobs]
    if any(job.job_id != fit_id for job, fit_id in zip(jobs, fit_ids, strict=True)):
        raise ValueError("Experiment-1 job identity is not its fit_id")
    if len(set(fit_ids)) != 150:
        raise ValueError("Experiment-1 plan does not contain 150 unique fit ids")

    seeds = tuple(range(K.CONFIRMATORY_SEED_BASE, K.CONFIRMATORY_SEED_BASE + 5))
    seed_counts = Counter(job.seed for job in jobs)
    if set(seed_counts) != set(seeds) or any(seed_counts[seed] != 30 for seed in seeds):
        raise ValueError(
            f"Experiment-1 seeds/counts are {dict(sorted(seed_counts.items()))}, "
            f"not exactly 30 jobs at each of {list(seeds)}"
        )

    if any(job.stage != "exp1" or job.arm != "baseline" for job in jobs):
        raise ValueError("Experiment-1 plan must contain only exp1 baseline jobs")
    role_counts = Counter(job.roles for job in jobs)
    expected_role_counts = {
        ("exp1",): 120,
        ("exp1", "repair_validation"): 30,
    }
    if dict(role_counts) != expected_role_counts:
        raise ValueError(
            f"Experiment-1 role inventory is {dict(role_counts)!r}, not "
            f"{expected_role_counts!r}"
        )

    cell_counts = Counter((job.unit.n_transitions, job.seed) for job in jobs)
    expected_cells = {
        (size, seed): 5 for size in K.DATA_SIZES for seed in seeds
    }
    if dict(cell_counts) != expected_cells:
        raise ValueError("Experiment-1 plan is not exactly 6 sizes x 5 configurations x 5 seeds")

    records = sorted((job.as_record() for job in jobs), key=lambda item: item["fit_id"])
    digest = sha256_bytes(
        _canonical_json_bytes(
            {"preflight_plan_schema_version": 1, "jobs": records}
        )
    )
    return {
        "fit_count": 150,
        "unique_fit_count": 150,
        "multi_role_fit_count": 30,
        "seeds": list(seeds),
        "sizes": list(K.DATA_SIZES),
        "configurations_per_size_seed": 5,
        "sha256": digest,
    }


def _resolved_root(path: str | Path, *, name: str, minimum_free_bytes: int) -> tuple[Path, dict[str, Any]]:
    try:
        root = Path(path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"{name} does not resolve to an existing root: {path!r}: {exc}") from exc
    if not root.is_dir():
        raise ValueError(f"{name} is not a directory: {root}")
    if not os.access(root, os.W_OK):
        raise ValueError(f"{name} is not writable: {root}")
    try:
        free = shutil.disk_usage(root).free
    except OSError as exc:
        raise ValueError(f"cannot inspect free bytes for {name} {root}: {exc}") from exc
    if type(free) is not int or free < minimum_free_bytes:
        raise ValueError(
            f"{name} has {free!r} free bytes, below required {minimum_free_bytes}"
        )
    return root, {"path": str(root), "writable": True, "free_bytes": free}


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _verify_storage(
    *,
    preflight_dir: str | Path,
    output_root: str | Path,
    staging_root: str | Path,
    sync_root: str | Path,
    minimum_free_bytes: int,
) -> tuple[dict[str, Path], dict[str, Any]]:
    if type(minimum_free_bytes) is not int or minimum_free_bytes < 0:
        raise ValueError("minimum_free_bytes must be an exact finite nonnegative integer")

    requested = {
        "preflight": preflight_dir,
        "output": output_root,
        "staging": staging_root,
        "sync": sync_root,
    }
    roots: dict[str, Path] = {}
    snapshots: dict[str, Any] = {}
    for name, path in requested.items():
        root, snapshot = _resolved_root(
            path, name=f"{name}_root", minimum_free_bytes=minimum_free_bytes
        )
        roots[name] = root
        snapshots[name] = snapshot

    names = tuple(roots)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            if _overlap(roots[left_name], roots[right_name]):
                raise ValueError(
                    f"resolved roots must be distinct and non-overlapping: "
                    f"{left_name}={roots[left_name]} and "
                    f"{right_name}={roots[right_name]}"
                )
    return roots, {
        "minimum_free_bytes": minimum_free_bytes,
        "roots": snapshots,
    }


def _validate_destination_identity(value: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(
            "sync_destination_identity must be a nonempty exact string without "
            "leading or trailing whitespace"
        )
    return value


def _verify_regular_file(path: Path, *, what: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {what} {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{what} must be a regular non-symlink file: {path}")


def _run_sync_canary(
    *,
    roots: Mapping[str, Path],
    plan_digest: str,
    destination_identity: str,
    adapter: SyncCanaryAdapter,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not callable(adapter):
        raise ValueError("sync_canary adapter must be callable")
    canary_value = {
        "canary_schema_version": 1,
        "destination_identity": destination_identity,
        "plan_sha256": plan_digest,
    }
    canary_bytes = _canonical_json_bytes(canary_value)
    source = roots["preflight"] / SYNC_CANARY_FILE
    atomic_write_bytes(source, canary_bytes)
    _verify_regular_file(source, what="local sync canary")
    digest = sha256_bytes(canary_bytes)
    destination = roots["sync"] / SYNC_CANARY_FILE

    try:
        receipt = adapter(source, destination, destination_identity)
    except Exception as exc:
        raise ValueError(f"sync canary adapter failed: {exc}") from exc
    if type(receipt) is not SyncCanaryReceipt:
        raise ValueError(
            f"sync canary adapter returned {type(receipt).__name__}, not "
            "an exact SyncCanaryReceipt"
        )
    if (
        type(receipt.schema_version) is not int
        or receipt.schema_version != SYNC_RECEIPT_SCHEMA_VERSION
    ):
        raise ValueError(
            f"sync receipt schema {receipt.schema_version!r} is not "
            f"{SYNC_RECEIPT_SCHEMA_VERSION}"
        )
    if receipt.destination_identity != destination_identity:
        raise ValueError("sync receipt names the wrong destination identity")
    if type(receipt.destination_path) is not str:
        raise ValueError("sync receipt destination_path must be a string")
    try:
        receipt_path = Path(receipt.destination_path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"sync receipt destination does not exist: {exc}") from exc
    if receipt_path != destination:
        raise ValueError(
            f"sync receipt path {receipt_path} is not the prescribed destination {destination}"
        )
    if type(receipt.sha256) is not str or receipt.sha256 != digest:
        raise ValueError("sync receipt does not bind the exact canary SHA256")
    if type(receipt.size_bytes) is not int or receipt.size_bytes != len(canary_bytes):
        raise ValueError("sync receipt does not bind the exact canary byte count")

    _verify_regular_file(destination, what="synced canary")
    if sha256_file(source) != digest or source.read_bytes() != canary_bytes:
        raise ValueError("local sync canary changed during the adapter call")
    if destination.stat().st_size != len(canary_bytes) or sha256_file(destination) != digest:
        raise ValueError("synced canary bytes do not match the local canary")

    return (
        {
            "source_path": str(source),
            "destination_path": str(destination),
            "sha256": digest,
            "size_bytes": len(canary_bytes),
        },
        asdict(receipt),
    )


def run_experiment_1_preflight(
    *,
    preflight_dir: str | Path,
    output_root: str | Path,
    staging_root: str | Path,
    sync_root: str | Path,
    sync_destination_identity: str,
    sync_canary: SyncCanaryAdapter,
    execution_route: str,
    minimum_free_bytes: int,
) -> dict[str, Any]:
    """Verify and persist readiness without launching any Experiment-1 fit.

    All roots must already exist.  The report is immutable: an idempotent retry
    with byte-identical evidence succeeds, while a changed report in the same
    preflight directory is refused by :func:`bu.durable.atomic_write_json`.
    """

    destination_identity = _validate_destination_identity(sync_destination_identity)
    plan = _verify_plan(experiment_1_jobs())
    state, versions, pins = _verify_environment()
    device = _verify_device(execution_route)
    roots, storage = _verify_storage(
        preflight_dir=preflight_dir,
        output_root=output_root,
        staging_root=staging_root,
        sync_root=sync_root,
        minimum_free_bytes=minimum_free_bytes,
    )
    canary, receipt = _run_sync_canary(
        roots=roots,
        plan_digest=plan["sha256"],
        destination_identity=destination_identity,
        adapter=sync_canary,
    )

    report: dict[str, Any] = {
        "preflight_schema_version": PREFLIGHT_SCHEMA_VERSION,
        "status": "ready",
        "launch_performed": False,
        "plan": plan,
        "environment": {
            "git": {
                "commit": state.commit,
                "branch": state.branch,
                "dirty": state.dirty,
                "trustworthy": state.trustworthy,
            },
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": versions,
            "exact_pins": pins,
        },
        "device": device,
        "storage": storage,
        "sync_canary": canary,
        "sync_receipt": receipt,
    }
    atomic_write_json(roots["preflight"] / PREFLIGHT_REPORT_FILE, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit no-launch preflight command-line contract."""

    parser = argparse.ArgumentParser(
        prog="python -m bu.experiments.preflight",
        description=(
            "Verify the exact Experiment-1 plan and mounted sync destination "
            "without launching a fit."
        ),
    )
    parser.add_argument("--preflight-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--staging-root", required=True, type=Path)
    parser.add_argument("--sync-root", required=True, type=Path)
    parser.add_argument("--sync-destination-identity", required=True)
    parser.add_argument("--execution-route", default=CONFIRMATORY_DEVICE)
    parser.add_argument("--minimum-free-bytes", required=True, type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run preflight only, print the immutable report, and never launch."""

    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        report = run_experiment_1_preflight(
            preflight_dir=arguments.preflight_dir,
            output_root=arguments.output_root,
            staging_root=arguments.staging_root,
            sync_root=arguments.sync_root,
            sync_destination_identity=arguments.sync_destination_identity,
            sync_canary=sync_canary_to_mounted_directory,
            execution_route=arguments.execution_route,
            minimum_free_bytes=arguments.minimum_free_bytes,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main(argv)
    raise SystemExit(main())
