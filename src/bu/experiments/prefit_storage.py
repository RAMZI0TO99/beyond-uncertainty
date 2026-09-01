"""Read-only, source-bound storage checks immediately before new fit attempts.

Operational only: the minimum comes from already validated launch evidence,
never a new constant or caller override. This is a point-in-time floor, not a
reservation or a prediction of the next fit's size. No evidence is rewritten.
The launch adapters remain responsible for source authority, workspace bounds,
historical-root protection, full provenance and lease validation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

from ..durable import _decode_json


def _keys(value, expected, what):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f"pre-fit storage: malformed {what}")
    return value


def _path(value, *, directory):
    """Check every raw ancestor before resolution, including Windows junctions."""
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError("pre-fit storage: path must be an absolute canonical path")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("pre-fit storage: relative path refused")
    try:
        for part in reversed((path, *path.parents)):
            info = part.lstat()
            if (stat.S_ISLNK(info.st_mode) or
                    getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise ValueError(f"pre-fit storage: link/reparse path refused: {part}")
            want_directory = part != path or directory
            if not (stat.S_ISDIR(info.st_mode) if want_directory else stat.S_ISREG(info.st_mode)):
                raise ValueError(f"pre-fit storage: wrong path type: {part}")
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"pre-fit storage: cannot inspect {path}: {exc}") from exc
    if str(value) != str(resolved):
        raise ValueError("pre-fit storage: path is not its exact canonical spelling")
    return resolved


def _digest(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("pre-fit storage: an independent lowercase SHA256 is required")
    return value


def _read(path):
    path = _path(path, directory=False)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"pre-fit storage: cannot read bound source: {exc}") from exc
    return path, raw


def _minimum(value, *, positive=False):
    # Preserve preflight's existing nonnegative-int policy; sweep requires >0.
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError("pre-fit storage: invalid source minimum_free_bytes")
    return value


def _check_roots(recorded, actual, minimum):
    _keys(actual, recorded, "execution roots")
    checked = {}
    for name, value in recorded.items():
        if type(value) is not str or str(actual[name]) != value:
            raise ValueError(f"pre-fit storage: {name} differs from the bound source root")
        checked[name] = _path(value, directory=True)
    ordered = list(checked.items())
    for index, (name, root) in enumerate(ordered):
        for other_name, other in ordered[index + 1:]:
            if root.is_relative_to(other) or other.is_relative_to(root):
                raise ValueError(f"pre-fit storage: overlapping {name}/{other_name} roots")
    # Inspect every distinct recorded root, even when several share a volume.
    # Historical free_bytes is NOT used as the current capacity observation.
    for name, root in ordered:
        try:
            if not os.access(root, os.W_OK):
                raise ValueError(f"pre-fit storage: {name} is no longer writable")
            free = getattr(shutil.disk_usage(root), "free", None)
        except OSError as exc:
            raise ValueError(f"pre-fit storage: cannot inspect {name} capacity: {exc}") from exc
        if type(free) is not int or free < minimum:
            raise ValueError(
                f"pre-fit storage: {name} has {free!r} free bytes, below required {minimum}; "
                "new child refused before attempt_started"
            )


def check_preflight_storage(source_path, source_sha256, *, roots):
    """Reopen the launch-pinned preflight bytes; derive its exact roots/floor."""
    expected = _digest(source_sha256)
    path, raw = _read(source_path)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("pre-fit storage: preflight changed from the original launch pin")
    document = _decode_json(raw, source=str(path))
    schemas = {
        "week7_exp1_repair_preflight.json": "exp1_repair_preflight_schema_version",
        "week7_preflight_report.json": "week7_preflight_schema_version",
        "week8_preflight_report.json": "week8_preflight_schema_version",
    }
    schema = schemas.get(path.name)
    if (schema is None or type(document) is not dict or
            type(document.get(schema)) is not int or document[schema] != 1 or
            document.get("status") != "ready" or document.get("launch_performed") is not False):
        raise ValueError("pre-fit storage: unsupported ready preflight source")
    storage = _keys(document.get("storage"), {"minimum_free_bytes", "roots"}, "storage")
    minimum = _minimum(storage["minimum_free_bytes"])
    snapshots = _keys(storage["roots"], {"preflight", "output", "staging", "sync"}, "source roots")
    recorded = {}
    for name, snapshot in snapshots.items():
        _keys(snapshot, {"path", "writable", "free_bytes"}, f"{name} snapshot")
        if (snapshot["writable"] is not True or type(snapshot["free_bytes"]) is not int or
                snapshot["free_bytes"] < minimum):
            raise ValueError("pre-fit storage: invalid historical storage snapshot")
        recorded[name] = snapshot["path"]
    if recorded["preflight"] != str(path.parent):
        raise ValueError("pre-fit storage: report is outside its bound preflight root")
    _check_roots(recorded, roots, minimum)


@dataclass(frozen=True)
class PreflightStorageGuard:
    """Private batch hand-off; no callback, executor or floor override.

    Roots are an immutable tuple captured by a validated Week-7/8 launcher.
    The common engine also binds its actual output/staging arguments at use.
    Merely constructing this object performs no capacity check, so completed
    fits still reach existing recovery/sync paths without a new-child check.
    """

    source_path: Path
    source_sha256: str
    roots: tuple[tuple[str, Path], ...]

    def check(self, *, output_root, staging_root):
        if (type(self.roots) is not tuple or len(self.roots) != 4 or
                any(type(row) is not tuple or len(row) != 2 or type(row[0]) is not str
                    for row in self.roots)):
            raise ValueError("pre-fit storage: malformed bound root tuple")
        roots = dict(self.roots)
        _keys(roots, {"preflight", "output", "staging", "sync"}, "bound roots")
        if (str(output_root) != str(roots["output"]) or
                str(staging_root) != str(roots["staging"])):
            raise ValueError("pre-fit storage: batch roots differ from the bound preflight")
        check_preflight_storage(self.source_path, self.source_sha256, roots=roots)


def check_sweep_context_storage(source_path, context_digest, *, roots):
    """Use the start's independent context digest, not the file's claimed pin."""
    expected = _digest(context_digest)
    path, raw = _read(source_path)
    document = _decode_json(raw, source=str(path))
    if (path.name != "week7_sweep_repair_context.json" or type(document) is not dict or
            type(document.get("sweep_repair_launch_schema_version")) is not int or
            document["sweep_repair_launch_schema_version"] != 1 or
            document.get("purpose") != "exact_first_sweep_six_paired_repairs" or
            document.get("execution_context_digest") != expected):
        raise ValueError("pre-fit storage: unsupported or unbound sweep context")
    payload = {k: v for k, v in document.items() if k != "execution_context_digest"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           allow_nan=False, ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != expected:
        raise ValueError("pre-fit storage: sweep context changed from its launch start")
    recorded = _keys(document.get("roots"), {"output", "staging", "sync"}, "sweep roots")
    minimum = _minimum(document.get("minimum_free_bytes"), positive=True)
    if str(path.parent) != recorded["output"]:
        raise ValueError("pre-fit storage: context is outside its bound output root")
    _check_roots(recorded, roots, minimum)
