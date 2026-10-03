"""Create one canonical Week 8 D-168 release receipt (schema V2).

This standalone standard-library writer does not import project code or invoke
Git. It creates the destination exactly once, fsyncs it, and verifies the
closed file's identity, bytes, and digest through a fresh descriptor.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path("D:/Aenv/pro2")
RECEIPT_HEADER = "WEEK8_D168_RELEASE_RECEIPT_V2"
RECEIPT_FIELDS = (
    "controller_commit",
    "native_launcher_sha256",
    "outer_sha256",
    "entry_sha256",
    "helper_sha256",
    "stage0_source_sha256",
    "stage0_encoded_sha256",
    "stage0_environment_policy_sha256",
)

_LOWER_HEX_40 = re.compile(r"[0-9a-f]{40}\Z", re.ASCII)
_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_REPARSE = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


class ReleaseReceiptRefused(ValueError):
    """The V2 receipt could not be rendered under its frozen contract."""


def _canonical_hex(value: object, *, length: int, what: str) -> str:
    pattern = _LOWER_HEX_40 if length == 40 else _LOWER_HEX_64
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ReleaseReceiptRefused(
            f"{what} must be exactly {length} lowercase hexadecimal characters"
        )
    return value


def render_release_receipt(
    *,
    controller_commit: object,
    native_launcher_sha256: object,
    outer_sha256: object,
    entry_sha256: object,
    helper_sha256: object,
    stage0_source_sha256: object,
    stage0_encoded_sha256: object,
    stage0_environment_policy_sha256: object,
) -> bytes:
    """Return the sole canonical ASCII/LF V2 receipt representation."""

    values = {
        "controller_commit": _canonical_hex(
            controller_commit, length=40, what="controller_commit"
        ),
        "native_launcher_sha256": _canonical_hex(
            native_launcher_sha256,
            length=64,
            what="native_launcher_sha256",
        ),
        "outer_sha256": _canonical_hex(
            outer_sha256, length=64, what="outer_sha256"
        ),
        "entry_sha256": _canonical_hex(
            entry_sha256, length=64, what="entry_sha256"
        ),
        "helper_sha256": _canonical_hex(
            helper_sha256, length=64, what="helper_sha256"
        ),
        "stage0_source_sha256": _canonical_hex(
            stage0_source_sha256, length=64, what="stage0_source_sha256"
        ),
        "stage0_encoded_sha256": _canonical_hex(
            stage0_encoded_sha256, length=64, what="stage0_encoded_sha256"
        ),
        "stage0_environment_policy_sha256": _canonical_hex(
            stage0_environment_policy_sha256,
            length=64,
            what="stage0_environment_policy_sha256",
        ),
    }
    text = RECEIPT_HEADER + "\n"
    text += "".join(f"{name}={values[name]}\n" for name in RECEIPT_FIELDS)
    payload = text.encode("ascii", errors="strict")
    if b"\r" in payload or payload.startswith(b"\xef\xbb\xbf"):
        raise ReleaseReceiptRefused("internal receipt encoding is not ASCII/LF")
    return payload


def _is_reparse(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        int(getattr(metadata, "st_file_attributes", 0)) & _REPARSE
    )


def _fixed_project_output(value: object) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        raise ReleaseReceiptRefused("output must be an absolute project-local path")
    candidate = Path(value)
    lexical = Path(os.path.abspath(value))
    if not candidate.is_absolute() or candidate != lexical:
        raise ReleaseReceiptRefused("output must be an absolute project-local path")
    try:
        relative = lexical.relative_to(Path(os.path.abspath(PROJECT_ROOT)))
    except ValueError as exc:
        raise ReleaseReceiptRefused("output path is outside D:/Aenv/pro2") from exc
    if not relative.parts:
        raise ReleaseReceiptRefused("output must be a file below D:/Aenv/pro2")
    return lexical


def _path_identity(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(stat.S_IFMT(metadata.st_mode)),
        int(getattr(metadata, "st_file_attributes", 0)),
    )


def _file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (*_path_identity(metadata), int(metadata.st_size))


def _plain_parent_chain(
    path: Path,
) -> tuple[tuple[Path, tuple[int, int, int, int]], ...]:
    chain = tuple(reversed((path.parent, *path.parent.parents)))
    snapshots: list[tuple[Path, tuple[int, int, int, int]]] = []
    for component in chain:
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise ReleaseReceiptRefused(
                f"output parent chain is unavailable at {component}"
            ) from exc
        if _is_reparse(metadata):
            raise ReleaseReceiptRefused(
                f"output parent chain contains a linked or reparse component: {component}"
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise ReleaseReceiptRefused(
                f"output parent is not a plain directory: {component}"
            )
        snapshots.append((component, _path_identity(metadata)))
    return tuple(snapshots)


def _verify_parent_chain(
    snapshots: tuple[tuple[Path, tuple[int, int, int, int]], ...],
) -> None:
    for component, expected in snapshots:
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise ReleaseReceiptRefused(
                f"output parent chain changed at {component}"
            ) from exc
        if (
            _is_reparse(metadata)
            or not stat.S_ISDIR(metadata.st_mode)
            or _path_identity(metadata) != expected
        ):
            raise ReleaseReceiptRefused(f"output parent chain changed at {component}")


def _plain_single_link_file(metadata: os.stat_result, *, what: str) -> None:
    if _is_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise ReleaseReceiptRefused(f"{what} is not a plain regular file")
    if int(getattr(metadata, "st_nlink", 0)) != 1:
        raise ReleaseReceiptRefused(f"{what} is not a single-link file")


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("receipt write made no progress")
        remaining = remaining[written:]


def _reread_and_verify(
    path: Path,
    *,
    expected_payload: bytes,
    expected_file_identity: tuple[int, int, int, int, int],
) -> str:
    try:
        before = path.lstat()
    except OSError as exc:
        raise ReleaseReceiptRefused("created receipt cannot be re-inspected") from exc
    _plain_single_link_file(before, what="created receipt")
    if _file_identity(before) != expected_file_identity:
        raise ReleaseReceiptRefused("created receipt changed before verification")

    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOINHERIT", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ReleaseReceiptRefused("created receipt cannot be reopened") from exc
    chunks: list[bytes] = []
    try:
        opened = os.fstat(descriptor)
        _plain_single_link_file(opened, what="reopened receipt")
        if _file_identity(opened) != expected_file_identity:
            raise ReleaseReceiptRefused("reopened receipt is not the created file")
        while True:
            chunk = os.read(descriptor, 4096)
            if not chunk:
                break
            chunks.append(chunk)
        if _file_identity(os.fstat(descriptor)) != expected_file_identity:
            raise ReleaseReceiptRefused("receipt changed while being verified")
    finally:
        os.close(descriptor)

    actual_payload = b"".join(chunks)
    actual_digest = hashlib.sha256(actual_payload).digest()
    if (
        actual_payload != expected_payload
        or actual_digest != hashlib.sha256(expected_payload).digest()
    ):
        raise ReleaseReceiptRefused("receipt bytes or SHA-256 verification failed")
    try:
        final = path.lstat()
    except OSError as exc:
        raise ReleaseReceiptRefused("verified receipt cannot be re-inspected") from exc
    _plain_single_link_file(final, what="verified receipt")
    if _file_identity(final) != expected_file_identity:
        raise ReleaseReceiptRefused("receipt changed after verification")
    return actual_digest.hex()


def create_release_receipt(
    *,
    output: object,
    controller_commit: object,
    native_launcher_sha256: object,
    outer_sha256: object,
    entry_sha256: object,
    helper_sha256: object,
    stage0_source_sha256: object,
    stage0_encoded_sha256: object,
    stage0_environment_policy_sha256: object,
) -> str:
    """Exclusively create and independently verify one V2 receipt."""

    payload = render_release_receipt(
        controller_commit=controller_commit,
        native_launcher_sha256=native_launcher_sha256,
        outer_sha256=outer_sha256,
        entry_sha256=entry_sha256,
        helper_sha256=helper_sha256,
        stage0_source_sha256=stage0_source_sha256,
        stage0_encoded_sha256=stage0_encoded_sha256,
        stage0_environment_policy_sha256=stage0_environment_policy_sha256,
    )
    path = _fixed_project_output(output)
    parents = _plain_parent_chain(path)
    if os.path.lexists(path):
        try:
            existing = path.lstat()
        except OSError as exc:
            raise ReleaseReceiptRefused("output already exists and is unreadable") from exc
        if _is_reparse(existing):
            raise ReleaseReceiptRefused(
                "output already exists as a linked or reparse path"
            )
        raise ReleaseReceiptRefused("output already exists")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOINHERIT", 0))
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ReleaseReceiptRefused("output already exists") from exc
    except OSError as exc:
        raise ReleaseReceiptRefused("receipt cannot be created exclusively") from exc
    try:
        opened = os.fstat(descriptor)
        _plain_single_link_file(opened, what="new receipt")
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        written = os.fstat(descriptor)
        _plain_single_link_file(written, what="written receipt")
        if int(written.st_size) != len(payload):
            raise ReleaseReceiptRefused("receipt write was not complete")
        created_identity = _file_identity(written)
    finally:
        os.close(descriptor)

    _verify_parent_chain(parents)
    digest = _reread_and_verify(
        path,
        expected_payload=payload,
        expected_file_identity=created_identity,
    )
    _verify_parent_chain(parents)
    return digest


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one immutable Week 8 D-168 V2 release receipt.",
        allow_abbrev=False,
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--controller-commit", required=True)
    parser.add_argument("--native-launcher-sha256", required=True)
    parser.add_argument("--outer-sha256", required=True)
    parser.add_argument("--entry-sha256", required=True)
    parser.add_argument("--helper-sha256", required=True)
    parser.add_argument("--stage0-source-sha256", required=True)
    parser.add_argument("--stage0-encoded-sha256", required=True)
    parser.add_argument("--stage0-environment-policy-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _argument_parser()
    arguments = parser.parse_args(argv)
    try:
        create_release_receipt(
            output=arguments.output,
            controller_commit=arguments.controller_commit,
            native_launcher_sha256=arguments.native_launcher_sha256,
            outer_sha256=arguments.outer_sha256,
            entry_sha256=arguments.entry_sha256,
            helper_sha256=arguments.helper_sha256,
            stage0_source_sha256=arguments.stage0_source_sha256,
            stage0_encoded_sha256=arguments.stage0_encoded_sha256,
            stage0_environment_policy_sha256=(
                arguments.stage0_environment_policy_sha256
            ),
        )
    except (ReleaseReceiptRefused, OSError) as exc:
        parser.exit(2, f"release receipt refused: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
