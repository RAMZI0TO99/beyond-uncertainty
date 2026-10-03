"""Read-only relocation attestations; no recovery authority or historical bypass.

The caller supplies a reviewed policy independently of the record being checked.
Old copy digests are retained as historical claims, never returned as freshly
observed identities. Consumers must revalidate immediately before use under the
production liveness/transition rules: two observations are not a filesystem lock.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


class RelocationRefused(ValueError):
    """The fixed mapping, bytes or current identities do not match."""


@dataclass(frozen=True)
class Pair:
    key: str
    logical_source: str
    logical_copy: str
    source: str
    copy: str
    content_digest: str
    historical_copy_digest: str


@dataclass(frozen=True)
class Document:
    path: str
    sha256: str


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RelocationRefused(message)


def _sha(value: str) -> None:
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             "invalid digest in trusted policy")


def _relative(value: str) -> tuple[str, ...]:
    _require(type(value) is str and bool(value), "empty relative path")
    parts = value.split("/")
    _require(PurePosixPath(value).as_posix() == value and not value.startswith("/"),
             "noncanonical relative path")
    for part in parts:
        _require(bool(part) and part not in {".", ".."} and
                 not any(c in part for c in '\\:*?"<>|') and
                 not any(ord(c) < 32 for c in part) and
                 not part.endswith((" ", ".")) and
                 re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part) is None,
                 "unsafe relative path")
    return tuple(parts)


def _logical(value: str) -> tuple[str, ...]:
    _require(type(value) is str, "logical path must be text")
    old = PureWindowsPath("D:/Aenv/pro/pro")
    path = PureWindowsPath(value)
    _require(path.is_absolute() and path.is_relative_to(old), "foreign logical root")
    relative = path.relative_to(old).as_posix()
    return tuple(p.casefold() for p in _relative(relative))


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink, info.st_mode)


def _object_identity(info: os.stat_result) -> tuple[int, ...]:
    # Windows CPython 3.13 lstat/fstat can expose different ctime semantics.
    # Compare birthtime across APIs; retain ctime for same-API before/after checks.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_nlink, info.st_mode, getattr(info, "st_birthtime_ns", 0))


def _plain(path: Path, *, directory: bool) -> os.stat_result:
    info = path.lstat()
    _require(not stat.S_ISLNK(info.st_mode) and
             not getattr(info, "st_file_attributes", 0) & 0x400,
             "link or reparse evidence")
    _require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
             "evidence has wrong file type")
    _require(info.st_ino > 0, "filesystem identity unavailable")
    if not directory:
        _require(info.st_nlink == 1, "hardlinked evidence")
    return info


def _chain(path: Path) -> None:
    for component in (*reversed(path.parents), path):
        _plain(component, directory=True)


def _file(path: Path) -> dict[str, Any]:
    before = _plain(path, directory=False)
    with path.open("rb") as stream:
        handle_before = os.fstat(stream.fileno())
        _require(_object_identity(handle_before) == _object_identity(before),
                 "file changed before read")
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
        _require(_identity(os.fstat(stream.fileno())) == _identity(handle_before),
                 "file changed during read")
    _require(_identity(_plain(path, directory=False)) == _identity(before),
             "file changed after read")
    return {"size": before.st_size, "sha256": sha, "device": before.st_dev,
            "inode": before.st_ino, "mtime_ns": before.st_mtime_ns,
            "ctime_ns": before.st_ctime_ns}


def _tree(path: Path) -> dict[str, Any]:
    _chain(path)
    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []

    def visit(folder: Path) -> None:
        before = _plain(folder, directory=True)
        children = sorted(folder.iterdir(), key=lambda p: p.name)
        names = [p.name for p in children]
        _require(len({n.casefold() for n in names}) == len(names), "case-aliased names")
        for child in children:
            _relative(child.relative_to(path).as_posix())
            info = child.lstat()
            _require(not stat.S_ISLNK(info.st_mode) and
                     not getattr(info, "st_file_attributes", 0) & 0x400, "linked tree entry")
            if stat.S_ISDIR(info.st_mode):
                visit(child)
            else:
                files.append({"path": child.relative_to(path).as_posix(), **_file(child)})
        _require(_identity(_plain(folder, directory=True)) == _identity(before) and
                 sorted(p.name for p in folder.iterdir()) == names, "directory changed during read")
        directories.append({"path": folder.relative_to(path).as_posix(),
                            "device": before.st_dev, "inode": before.st_ino,
                            "mtime_ns": before.st_mtime_ns, "ctime_ns": before.st_ctime_ns})

    visit(path)
    _chain(path)
    _require(bool(files), "empty evidence tree")
    # The old content digest covers files, not empty directories. Admit only
    # directory structure required by those hashed filenames.
    for row in directories:
        _require(row["path"] == "." or any(
            file["path"].startswith(row["path"] + "/") for file in files
        ), "unregistered empty directory")
    return {"files": sorted(files, key=lambda r: r["path"]),
            "directories": sorted(directories, key=lambda r: r["path"])}


def _validate_policy(pairs: tuple[Pair, ...], documents: tuple[Document, ...]) -> None:
    _require(bool(pairs) and bool(documents), "empty trusted policy")
    _require(all(type(p) is Pair and type(p.key) is str for p in pairs), "invalid pair")
    _require(len({p.key for p in pairs}) == len(pairs), "duplicate pair key")
    physical: list[tuple[str, ...]] = []
    logical: list[tuple[str, ...]] = []
    for pair in pairs:
        _require(type(pair) is Pair and type(pair.key) is str and bool(pair.key), "invalid pair")
        _sha(pair.content_digest)
        _sha(pair.historical_copy_digest)
        physical.extend(tuple(p.casefold() for p in _relative(v)) for v in (pair.source, pair.copy))
        logical.extend(_logical(v) for v in (pair.logical_source, pair.logical_copy))
    for rows in (physical, logical):
        ordered = sorted(rows)
        _require(all(b[:len(a)] != a for a, b in zip(ordered, ordered[1:])),
                 "duplicate or overlapping evidence roots")
    document_paths = []
    for document in documents:
        _require(type(document) is Document, "invalid document policy")
        _sha(document.sha256)
        parts = tuple(p.casefold() for p in _relative(document.path))
        _require(not any(parts[:len(p)] == p for p in physical), "document overlaps evidence tree")
        document_paths.append(parts)
    _require(len(set(document_paths)) == len(document_paths), "duplicate document path")


def _observe(workspace: Path, pairs: tuple[Pair, ...], documents: tuple[Document, ...]) -> dict[str, Any]:
    _chain(workspace)
    root_stat = _plain(workspace, directory=True)
    rows = []
    seen: set[tuple[int, int]] = set()
    for pair in sorted(pairs, key=lambda p: p.key):
        source = _tree(workspace.joinpath(*_relative(pair.source)))
        copy = _tree(workspace.joinpath(*_relative(pair.copy)))
        for tree in (source, copy):
            for row in tree["files"] + tree["directories"]:
                identity = (row["device"], row["inode"])
                _require(identity not in seen, "filesystem object reused across mappings")
                seen.add(identity)
        a, b = source["files"], copy["files"]
        content = lambda items: [{k:r[k] for k in ("path", "size", "sha256")} for r in items]
        _require(content(a) == content(b) and digest(content(a)) == pair.content_digest,
                 "content differs from frozen evidence")
        observed = digest([{"path": x["path"], "source_device": x["device"],
                            "source_inode": x["inode"], "destination_device": y["device"],
                            "destination_inode": y["inode"], "sha256": x["sha256"]}
                           for x, y in zip(a, b, strict=True)])
        rows.append({"policy": asdict(pair), "source_inventory": source,
                     "copy_inventory": copy, "observed_copy_digest": observed,
                     "historical_identity_reproduced": observed == pair.historical_copy_digest})
    docs = []
    for document in sorted(documents, key=lambda d: d.path):
        path = workspace.joinpath(*_relative(document.path))
        _chain(path.parent)
        row = _file(path)
        _require(row["sha256"] == document.sha256, "historical document content differs")
        identity = (row["device"], row["inode"])
        _require(identity not in seen, "document aliases another evidence object")
        seen.add(identity)
        docs.append({"policy": asdict(document), "inventory": row})
    _chain(workspace)
    after = _plain(workspace, directory=True)
    _require((after.st_dev, after.st_ino) == (root_stat.st_dev, root_stat.st_ino), "workspace identity changed")
    return {"schema_version": 1, "record_type": "week8_relocation_provenance",
            "workspace": str(workspace), "workspace_device": root_stat.st_dev,
            "workspace_inode": root_stat.st_ino, "pairs": rows, "documents": docs}


def build_record(workspace: Path, pairs: tuple[Pair, ...], documents: tuple[Document, ...]) -> bytes:
    """Capture twice against separately supplied, trusted evidence bindings."""
    try:
        _require(workspace.is_absolute() and ".." not in workspace.parts, "invalid workspace path")
        _validate_policy(pairs, documents)
        before = _observe(workspace, pairs, documents)
        after = _observe(workspace, pairs, documents)
        _require(before == after, "evidence changed between observations")
        return canonical(before)
    except OSError as exc:
        raise RelocationRefused("evidence unavailable during observation") from exc


def verify_record(raw: bytes, expected_sha256: str, workspace: Path,
                  pairs: tuple[Pair, ...], documents: tuple[Document, ...]) -> dict[str, Any]:
    """Verify an externally pinned record and rescan its exact trusted mapping.

    Equality to reconstructed canonical bytes also rejects unknown/duplicate JSON
    keys, noncanonical encodings and a record that tries to declare its own policy.
    """
    _sha(expected_sha256)
    _require(hashlib.sha256(raw).hexdigest() == expected_sha256, "relocation record hash differs")
    expected = build_record(workspace, pairs, documents)
    _require(raw == expected, "relocation record differs from current trusted observation")
    return json.loads(expected)


@dataclass(frozen=True)
class HistoricalFile:
    """Original bytes at a verified current location; no rewritten JSON view."""

    logical_path: str
    physical_path: Path
    raw: bytes
    sha256: str
    attestation_sha256: str

    def document(self) -> dict[str, Any]:
        def object_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in items:
                _require(key not in result, "duplicate historical document key")
                result[key] = value
            return result

        def nonfinite(value: str) -> Any:
            raise RelocationRefused("nonfinite historical document")

        try:
            value = json.loads(self.raw, object_pairs_hook=object_pairs, parse_constant=nonfinite)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RelocationRefused("historical file is not JSON") from exc
        _require(type(value) is dict, "historical document is not an object")
        return value


@dataclass(frozen=True)
class PairObservation:
    """Explicit bridge, not a replacement copy-evidence digest."""

    policy: Pair
    source: Path
    copy: Path
    historical_copy_digest: str
    observed_copy_digest: str
    attestation_sha256: str


class EvidenceAccess:
    """Read only exactly registered historical files and current evidence pairs.

    Initialization verifies the whole externally pinned record and policy. Every
    subsequent file/pair access rechecks its pinned current identity and bytes.
    This object grants no production capability and never resolves an unknown
    path by searching, prefix fallback, symlink or archive discovery.
    """

    def __init__(self, raw: bytes, expected_sha256: str, workspace: Path,
                 pairs: tuple[Pair, ...], documents: tuple[Document, ...]) -> None:
        self._raw = raw
        self._digest = expected_sha256
        self._workspace = workspace
        self._pairs = pairs
        self._documents = documents
        record = verify_record(raw, expected_sha256, workspace, pairs, documents)
        self._files: dict[tuple[str, ...], tuple[str, Path, dict[str, Any]]] = {}
        self._physical_files: dict[Path, tuple[str, ...]] = {}
        self._pair_rows: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
        self._physical_pairs: dict[tuple[Path, Path], tuple[tuple[str, ...], tuple[str, ...]]] = {}

        def bind_file(logical: str, path: Path, inventory: dict[str, Any]) -> None:
            key = _logical(logical)
            _require(key not in self._files and path not in self._physical_files,
                     "duplicate logical or physical file binding")
            self._files[key] = (logical, path, dict(inventory))
            self._physical_files[path] = key

        for row in record["pairs"]:
            policy = Pair(**row["policy"])
            key = (_logical(policy.logical_source), _logical(policy.logical_copy))
            source, copy = workspace / policy.source, workspace / policy.copy
            self._pair_rows[key] = row
            self._physical_pairs[(source, copy)] = key
            for logical, physical, inventory in (
                (policy.logical_source, source, row["source_inventory"]),
                (policy.logical_copy, copy, row["copy_inventory"]),
            ):
                for file in inventory["files"]:
                    name = file["path"]
                    bind_file(str(PureWindowsPath(logical) / name), physical / name,
                              {k:v for k,v in file.items() if k != "path"})
        old = PureWindowsPath("D:/Aenv/pro/pro")
        archive = "project 2(ongoing)/"
        for row in record["documents"]:
            relative = row["policy"]["path"]
            logical = relative[len(archive):] if relative.startswith(archive) else relative
            bind_file(str(old / logical), workspace / relative, row["inventory"])

    @property
    def attestation_sha256(self) -> str:
        return self._digest

    def revalidate(self) -> None:
        verify_record(self._raw, self._digest, self._workspace, self._pairs, self._documents)

    def registered_pair_policy(self, logical_source: str, logical_copy: str) -> Pair:
        """Return the immutable expected mapping, NOT a current verification."""
        key = (_logical(logical_source), _logical(logical_copy))
        _require(key in self._pair_rows, "unregistered historical pair policy")
        return Pair(**self._pair_rows[key]["policy"])

    def _read(self, key: tuple[str, ...]) -> HistoricalFile:
        _require(key in self._files, "unregistered historical file")
        logical, path, expected = self._files[key]
        try:
            _chain(path.parent)
            _require(_file(path) == expected, "historical file identity or bytes changed")
            raw = path.read_bytes()
            _require(hashlib.sha256(raw).hexdigest() == expected["sha256"],
                     "historical bytes changed during access")
            _require(_file(path) == expected, "historical file changed after access")
            _chain(path.parent)
        except OSError as exc:
            raise RelocationRefused("registered historical file unavailable") from exc
        return HistoricalFile(logical, path, raw, expected["sha256"], self._digest)

    def historical_file(self, logical_path: str) -> HistoricalFile:
        return self._read(_logical(logical_path))

    def historical_file_at(self, physical_path: Path) -> HistoricalFile:
        _require(physical_path.is_absolute() and ".." not in physical_path.parts,
                 "invalid physical historical path")
        key = self._physical_files.get(physical_path)
        _require(key is not None, "unregistered physical historical file")
        return self._read(key)

    def has_historical_file(self, physical_path: Path) -> bool:
        """Policy membership only; even a changed/missing registered file is True.

        Consumers must then call historical_file_at to verify it. A document
        cannot opt out of preservation by claiming to belong to a later epoch.
        No filesystem discovery or current-verification claim is performed.
        """
        _require(physical_path.is_absolute() and ".." not in physical_path.parts,
                 "invalid physical historical path")
        return physical_path in self._physical_files

    def _pair(self, key: tuple[tuple[str, ...], tuple[str, ...]]) -> PairObservation:
        _require(key in self._pair_rows, "unregistered historical pair")
        row = self._pair_rows[key]
        policy = Pair(**row["policy"])
        source, copy = self._workspace / policy.source, self._workspace / policy.copy
        try:
            # Full matching inventories include device/inode, timestamps and
            # file hashes. No historical digest is treated as a current one.
            for _ in range(2):
                _require(_tree(source) == row["source_inventory"] and
                         _tree(copy) == row["copy_inventory"],
                         "registered pair changed after attestation")
        except OSError as exc:
            raise RelocationRefused("registered historical pair unavailable") from exc
        return PairObservation(policy, source, copy, policy.historical_copy_digest,
                               row["observed_copy_digest"], self._digest)

    def historical_pair(self, logical_source: str, logical_copy: str) -> PairObservation:
        return self._pair((_logical(logical_source), _logical(logical_copy)))

    def historical_pair_at(self, source: Path, copy: Path) -> PairObservation:
        _require(all(p.is_absolute() and ".." not in p.parts for p in (source, copy)),
                 "invalid physical pair path")
        key = self._physical_pairs.get((source, copy))
        _require(key is not None, "unregistered physical historical pair")
        return self._pair(key)
