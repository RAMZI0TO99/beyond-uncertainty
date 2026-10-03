"""Small crash-safe filesystem primitives for immutable scientific evidence.

The functions in this module deliberately separate two durability patterns:

* immutable artefacts are fully written and synced in a unique temporary file,
  then published without ever replacing an existing destination; and
* journals append one compact JSON object per newline and sync every record.

An existing immutable destination is accepted only when its bytes are exactly
the bytes the caller asked to publish. This makes retry after an uncertain
outcome idempotent while preserving evidence if another writer used the same
name for different content.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class DurabilityError(ValueError):
    """Evidence could not be read or persisted without ambiguity."""


class DivergentTargetError(DurabilityError):
    """An immutable destination already contains different bytes."""


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA256 hex digest of exact bytes."""

    if type(data) is not bytes:
        raise TypeError(f"data must be exact bytes, got {type(data).__name__}")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Return the SHA256 digest of a file without loading it all into memory."""

    target = Path(path)
    digest = hashlib.sha256()
    try:
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DurabilityError(f"cannot hash {target}: {exc}") from exc
    return digest.hexdigest()


def fsync_directory(path: str | Path) -> bool:
    """Sync directory metadata where the host supports directory ``fsync``.

    ``True`` means the call was made successfully. Windows and filesystems that
    explicitly report directory syncing as unsupported return ``False``. Other
    I/O failures remain errors rather than being mistaken for unsupported I/O.
    """

    directory = Path(path)
    if os.name == "nt":
        return False

    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        descriptor = os.open(directory, flags)
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EINVAL, errno.ENOTSUP}:
            return False
        raise DurabilityError(f"cannot open directory {directory} for fsync: {exc}") from exc
    try:
        try:
            os.fsync(descriptor)
        except OSError as exc:
            if exc.errno in {errno.EBADF, errno.EINVAL, errno.ENOTSUP}:
                return False
            raise DurabilityError(f"cannot fsync directory {directory}: {exc}") from exc
    finally:
        os.close(descriptor)
    return True


def _destination(path: str | Path) -> tuple[Path, Path]:
    target = Path(path)
    if target.name in {"", ".", ".."}:
        raise DurabilityError(f"destination must name a file, got {target}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        directory = target.parent.resolve(strict=True)
    except OSError as exc:
        raise DurabilityError(f"cannot prepare destination directory for {target}: {exc}") from exc
    if not directory.is_dir():
        raise DurabilityError(f"destination parent is not a directory: {directory}")
    return directory / target.name, directory


def _unlink_temp(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise DurabilityError(f"cannot clean temporary file {path}: {exc}") from exc


def _existing_bytes(path: Path) -> bytes:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise DurabilityError(
                f"immutable destination must be a regular file, got {path}"
            )
        return path.read_bytes()
    except DurabilityError:
        raise
    except OSError as exc:
        raise DurabilityError(f"cannot inspect existing destination {path}: {exc}") from exc


def atomic_write_bytes(path: str | Path, data: bytes) -> Path:
    """Exclusively publish immutable bytes and return the destination path.

    The temporary file is uniquely named in the resolved destination directory,
    flushed, and synced before publication. ``os.link`` supplies the crucial
    create-if-absent operation: unlike replacement-oriented rename APIs, it can
    never overwrite an existing evidence file. A hard-link failure other than
    an existing destination fails closed rather than using an unsafe fallback.
    """

    if type(data) is not bytes:
        raise TypeError(f"data must be exact bytes, got {type(data).__name__}")

    target, directory = _destination(path)
    temporary: Path | None = None
    descriptor: int | None = None
    try:
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.", suffix=".tmp", dir=directory
            )
            temporary = Path(temporary_name)
        except OSError as exc:
            raise DurabilityError(
                f"cannot create temporary file beside {target}: {exc}"
            ) from exc

        # Do not trust a temporary-file provider to honour ``dir`` silently.
        # This also keeps future refactors from introducing path traversal.
        try:
            temporary_parent = temporary.resolve(strict=True).parent
        except OSError as exc:
            raise DurabilityError(f"cannot resolve temporary file {temporary}: {exc}") from exc
        if temporary_parent != directory:
            raise DurabilityError(
                f"temporary file escaped destination directory: {temporary}"
            )

        try:
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                descriptor = None
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise DurabilityError(f"cannot durably write temporary file for {target}: {exc}") from exc

        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError:
            existing = _existing_bytes(target)
            if existing != data:
                raise DivergentTargetError(
                    f"{target} already exists with different content; refusing overwrite"
                )
            # The earlier publication may have succeeded even if its caller did
            # not observe success. Sync metadata again on the idempotent retry.
            fsync_directory(directory)
            return target
        except OSError as exc:
            raise DurabilityError(
                f"cannot atomically publish {target} without overwrite: {exc}"
            ) from exc

        # The destination now names the synced inode. Remove the private name
        # and sync both directory metadata changes where supported.
        _unlink_temp(temporary)
        temporary = None
        fsync_directory(directory)
        return target
    finally:
        if descriptor is not None:
            os.close(descriptor)
        _unlink_temp(temporary)


def _json_bytes(value: Any, *, pretty: bool) -> bytes:
    try:
        if pretty:
            text = json.dumps(
                value, indent=2, sort_keys=True, allow_nan=False, ensure_ascii=False
            )
        else:
            text = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                ensure_ascii=False,
            )
    except (TypeError, ValueError) as exc:
        raise DurabilityError(f"value is not strict JSON: {exc}") from exc
    return (text + "\n").encode("utf-8")


def atomic_write_json(path: str | Path, value: Any) -> Path:
    """Canonically encode and exclusively publish one strict JSON document."""

    return atomic_write_bytes(path, _json_bytes(value, pretty=True))


def _reject_constant(token: str) -> Any:
    raise DurabilityError(f"non-finite JSON number {token!r} is not allowed")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DurabilityError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _decode_json(raw: bytes, *, source: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DurabilityError(f"{source} is not valid UTF-8: {exc}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
        )
    except DurabilityError:
        raise
    except json.JSONDecodeError as exc:
        raise DurabilityError(f"{source} is not valid JSON: {exc}") from exc


def read_json(path: str | Path) -> Any:
    """Read one strict UTF-8 JSON document or fail with a contextual error."""

    target = Path(path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise DurabilityError(f"cannot read JSON document {target}: {exc}") from exc
    return _decode_json(raw, source=str(target))


def append_jsonl(path: str | Path, record: Mapping[str, Any]) -> None:
    """Append and sync one strict JSON object plus its commit newline.

    A pre-existing file whose final record lacks a newline is refused. Appending
    to it would join a new object to an uncommitted fragment and turn a
    recoverable torn tail into permanent interior corruption.
    """

    if not isinstance(record, Mapping):
        raise TypeError(f"record must be a mapping, got {type(record).__name__}")
    line = _json_bytes(dict(record), pretty=False)
    target, directory = _destination(path)
    if target.exists() and target.is_symlink():
        raise DurabilityError(f"JSONL journal cannot be a symbolic link: {target}")

    flags = os.O_APPEND | os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = not target.exists()
    descriptor: int | None = None
    try:
        descriptor = os.open(target, flags, 0o666)
    except OSError as exc:
        raise DurabilityError(f"cannot open JSONL journal {target}: {exc}") from exc
    try:
        with os.fdopen(descriptor, "r+b", buffering=0, closefd=True) as handle:
            descriptor = None
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise DurabilityError(
                    f"JSONL journal must be a regular file: {target}"
                )
            if info.st_size:
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    raise DurabilityError(
                        f"JSONL journal {target} has an unterminated final record; "
                        "refusing to append"
                    )
            written = handle.write(line)
            if written != len(line):
                raise DurabilityError(
                    f"short append to {target}: wrote {written} of {len(line)} bytes"
                )
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise DurabilityError(f"cannot durably append JSONL record to {target}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if created:
        fsync_directory(directory)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read a strict JSONL journal, ignoring only an unterminated final record.

    The newline is the commit marker. Therefore a final byte sequence without
    one is conservatively omitted, whether or not those bytes happen to form
    valid JSON. Every newline-terminated record—including the final one—and
    every earlier record must be valid UTF-8 JSON object data.
    """

    target = Path(path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise DurabilityError(f"cannot read JSONL journal {target}: {exc}") from exc
    if not raw:
        return []

    parts = raw.split(b"\n")
    # A missing newline demonstrates that the final fragment was not committed.
    complete = parts[:-1]

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(complete, 1):
        if not line:
            raise DurabilityError(
                f"{target} line {line_number} is empty, not a JSON object"
            )
        value = _decode_json(line, source=f"{target} line {line_number}")
        if type(value) is not dict:
            raise DurabilityError(
                f"{target} line {line_number} is {type(value).__name__}, "
                "not a JSON object"
            )
        records.append(value)
    return records


def recover_unterminated_jsonl(
    path: str | Path,
    *,
    evidence_dir: str | Path,
) -> Path | None:
    """Preserve and remove one uncommitted JSONL tail so appends can resume.

    A newline is this module's commit marker.  Bytes after the last newline are
    therefore not a journal record, but silently discarding them would erase
    crash evidence.  This function first publishes the exact fragment under
    its SHA256 in ``evidence_dir``, then truncates the journal to its last
    committed prefix.  A concurrent change is refused before truncation.
    """

    target = Path(path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise DurabilityError(f"cannot inspect JSONL journal {target}: {exc}") from exc
    if not raw or raw.endswith(b"\n"):
        return None
    if target.is_symlink() or not target.is_file():
        raise DurabilityError(f"JSONL journal must be a regular file: {target}")

    boundary = raw.rfind(b"\n") + 1
    fragment = raw[boundary:]
    digest = sha256_bytes(fragment)
    preserved = Path(evidence_dir) / f"{target.name}.{digest}.torn"
    atomic_write_bytes(preserved, fragment)

    try:
        with target.open("r+b", buffering=0) as handle:
            if handle.read() != raw:
                raise DurabilityError(
                    f"JSONL journal {target} changed during torn-tail recovery"
                )
            handle.truncate(boundary)
            handle.flush()
            os.fsync(handle.fileno())
    except DurabilityError:
        raise
    except OSError as exc:
        raise DurabilityError(
            f"cannot truncate uncommitted JSONL tail in {target}: {exc}"
        ) from exc
    fsync_directory(target.parent)
    return preserved
