"""Verify or restore archived continuation bytes without importing project code."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile

REPO = Path(__file__).resolve().parents[1]
HEX = re.compile(r"^[0-9a-f]{64}$")
CHUNK = 1024 * 1024
MAX_GROUP_FILES = 200000
MAX_INDEX_BYTES = 128 * 1024 * 1024
TAR_BUFFER = 64 * 1024

def need(condition, message):
    if not condition:
        raise ValueError(message)

def closed_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result

def decode(data):
    return json.loads(data, object_pairs_hook=closed_object)

def safe_relative(value):
    need(isinstance(value, str) and value and "\\" not in value, "invalid archive path")
    path = PurePosixPath(value)
    need(bool(path.parts), "empty/dot archive path")
    need(not path.is_absolute() and all(part not in {"", ".", ".."} and ":" not in part for part in path.parts), "unsafe archive path")
    need(path.as_posix() == value and not any(part.rstrip(" .") != part for part in path.parts), "noncanonical archive path")
    for part in path.parts:
        stem = part.split(".", 1)[0].casefold()
        need(stem not in {"con", "prn", "aux", "nul", "clock$"} and not re.fullmatch(r"(?:com|lpt)[1-9]", stem), "Windows device name refused")
        need(not any(ord(char) < 32 or char in '<>"|?*' for char in part), "illegal Windows path character")
    return Path(*path.parts)

def long_path(path):
    value = str(path.absolute())
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        return Path("\\\\?\\" + value)
    return Path(value)

def sha_file(path):
    h = hashlib.sha256()
    size = 0
    with long_path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            h.update(block)
            size += len(block)
    return size, h.hexdigest()

def plain_path(path, directory=False):
    for position, component in enumerate((path, *path.parents)):
        actual = long_path(component)
        if not os.path.lexists(actual):
            continue
        info = actual.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400, "symlink/junction/reparse path refused: " + str(component))
        if position or directory:
            need(stat.S_ISDIR(info.st_mode), "non-directory path ancestor")

def validate_pin(pin):
    need(isinstance(pin, dict) and {"path", "bytes", "sha256"} <= set(pin), "missing payload byte pin")
    need(type(pin["bytes"]) is int and pin["bytes"] >= 0 and isinstance(pin["sha256"], str) and HEX.fullmatch(pin["sha256"]), "invalid payload byte pin")
    path = REPO / safe_relative(pin["path"])
    plain_path(path)
    need(path.is_file() and not path.is_symlink(), "missing/nonordinary payload: " + pin["path"])
    need(sha_file(path) == (pin["bytes"], pin["sha256"]), "payload SHA/size mismatch: " + pin["path"])
    return path

class PartsReader(io.RawIOBase):
    def __init__(self, paths):
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        if not len(buffer):
            return 0
        while True:
            if self.current is None:
                path = next(self.paths, None)
                if path is None:
                    return 0
                self.current = path.open("rb")
            count = self.current.readinto(buffer)
            if count:
                return count
            self.current.close()
            self.current = None

    def close(self):
        if self.current is not None:
            self.current.close()
        super().close()

def load_manifest():
    manifest = decode((REPO / "continuation/manifest.json").read_bytes())
    need(manifest["schema_version"] == 1 and manifest["record_type"] == "portable_byte_preserving_continuation_snapshot", "unsupported manifest")
    return manifest

def inputs(manifest):
    seen = set()
    directories = set()
    groups = []
    for group in manifest["bundles"]:
        need(group["format"] == "content_addressed_tar_gzip_multipart_v1", "unsupported archive format")
        paths = [validate_pin(part) for part in group["parts"]]
        need(type(group["file_count"]) is int and 0 <= group["file_count"] <= MAX_GROUP_FILES, "invalid/excessive group file count")
        index_limit = min(MAX_INDEX_BYTES, CHUNK + group["file_count"] * 1024)
        with gzip.open(validate_pin(group["index"]), "rb") as packed_index:
            index_bytes = packed_index.read(index_limit + 1)
            need(len(index_bytes) <= index_limit, "decompressed index exceeds bounded inventory size")
        index = decode(index_bytes)
        need(index["schema_version"] == 1 and len(index["files"]) == group["file_count"], "invalid file inventory")
        objects = defaultdict(list)
        for row in index["files"]:
            safe_relative(row["path"])
            normalized = row["path"].casefold()
            need(normalized != "portable_restore_receipt.json", "own restore receipt path is reserved")
            need(normalized not in seen, "duplicate/colliding logical archive path: " + row["path"])
            need(normalized not in directories, "file/directory path collision")
            pieces = normalized.split("/")
            for length in range(1, len(pieces)):
                prefix = "/".join(pieces[:length])
                need(prefix not in seen, "file used as a directory prefix")
                directories.add(prefix)
            seen.add(normalized)
            need(type(row["bytes"]) is int and row["bytes"] >= 0 and HEX.fullmatch(row["sha256"]), "invalid file pin")
            need(not objects[row["sha256"]] or objects[row["sha256"]][0]["bytes"] == row["bytes"], "conflicting sizes for one archived object")
            objects[row["sha256"]].append(row)
        need(len(objects) == group["distinct_object_count"], "invalid object count")
        need(sum(row["bytes"] for row in index["files"]) == group["raw_file_bytes"], "invalid group byte total")
        groups.append((group, paths, objects))
    need(sum(group[0]["file_count"] for group in groups) == manifest["selected_file_count"], "invalid total file count")
    need(type(manifest["raw_file_bytes"]) is int and sum(group[0]["raw_file_bytes"] for group in groups) == manifest["raw_file_bytes"], "invalid total raw file byte count")
    return groups

def verify_canonical():
    canonical = decode((REPO / "continuation/canonical-source.json").read_bytes())
    for row in canonical["files"]:
        validate_pin(row)
    return len(canonical["files"])

def directory_layout(manifest, groups):
    if "directory_layout" not in manifest:
        return []
    pin = manifest["directory_layout"]
    need(type(pin["directory_count"]) is int and 0 <= pin["directory_count"] <= 200000, "invalid directory inventory count")
    with gzip.open(validate_pin(pin), "rb") as source:
        data = source.read(MAX_INDEX_BYTES + 1)
    need(len(data) <= MAX_INDEX_BYTES, "directory inventory exceeds bound")
    record = decode(data)
    values = record["directories"]
    need(type(values) is list and all(type(value) is str for value in values), "directory inventory must be a list of strings")
    need(record["schema_version"] == 1 and len(values) == pin["directory_count"], "directory count mismatch")
    seen = set()
    files = {row["path"].casefold() for _, _, objects in groups for rows in objects.values() for row in rows}
    for value in values:
        safe_relative(value)
        name = value.casefold()
        need(name not in seen and name not in files and name != "portable_restore_receipt.json", "directory collides with a file or marker")
        seen.add(name)
        pieces = name.split("/")
        need(pieces[0] != "portable_restore_receipt.json", "directory is inside reserved receipt path")
        need(all("/".join(pieces[:length]) not in files for length in range(1, len(pieces))), "directory has file ancestor")
    return values

def restore_object(stream, rows, size, sha, destination):
    need(all(row["bytes"] == size for row in rows), "object size differs from logical file inventory")
    h = hashlib.sha256()
    total = 0
    handle = None
    first_target = None
    try:
        if destination is not None:
            first_target = long_path(destination / safe_relative(rows[0]["path"]))
            plain_path(destination, directory=True)
            plain_path(first_target)
            first_target.parent.mkdir(parents=True, exist_ok=True)
            plain_path(first_target)
            handle = first_target.open("xb")
        for block in iter(lambda: stream.read(CHUNK), b""):
            h.update(block)
            total += len(block)
            if handle is not None:
                handle.write(block)
        need(total == size and h.hexdigest() == sha, "archived object content mismatch: " + sha)
    finally:
        if handle is not None:
            handle.close()
    if destination is not None:
        for position, row in enumerate(rows):
            target = long_path(destination / safe_relative(row["path"]))
            if position:
                target.parent.mkdir(parents=True, exist_ok=True)
                plain_path(target)
                with first_target.open("rb") as source, target.open("xb") as copied:
                    shutil.copyfileobj(source, copied, length=CHUNK)
            if os.name != "nt":
                target.chmod(row.get("mode", 0o644) & 0o777)
            need(sha_file(target) == (row["bytes"], row["sha256"]), "restored byte readback mismatch: " + row["path"])

class TrackedTarReader:
    """Keep the last read-ahead block so TAR cannot hide nonzero trailing bytes."""
    def __init__(self, source):
        self.source = source
        self.total = 0
        self.tail = b""

    def read(self, size):
        need(0 <= size <= TAR_BUFFER, "unexpected unbounded TAR read")
        data = self.source.read(size)
        self.total += len(data)
        self.tail = (self.tail + data)[-TAR_BUFFER:]
        return data

    def finish(self, payload_end):
        tail_start = self.total - len(self.tail)
        need(tail_start <= payload_end <= self.total, "TAR end escaped bounded read-ahead buffer")
        need(not any(self.tail[payload_end - tail_start:]), "nonzero bytes after last TAR payload")
        padding = self.total - payload_end
        while True:
            block = self.source.read(TAR_BUFFER)
            if not block:
                break
            padding += len(block)
            need(padding <= TAR_BUFFER and not any(block), "invalid/excessive trailing TAR padding")
        need(1024 <= padding <= TAR_BUFFER, "missing/excessive TAR end markers")

def inspect_payloads(manifest, groups, destination=None):
    count = 0
    for group, paths, objects in groups:
        seen = set()
        with io.BufferedReader(PartsReader(paths), buffer_size=CHUNK) as joined:
            with gzip.GzipFile(fileobj=joined, mode="rb") as unzipped:
                tracked = TrackedTarReader(unzipped)
                payload_end = 0
                with tarfile.open(fileobj=tracked, mode="r|", bufsize=TAR_BUFFER) as archive:
                    for member in archive:
                        need(member.isfile() and member.name.startswith("objects/"), "unsafe/non-file TAR member")
                        need(member.offset == payload_end and member.offset_data == payload_end + 512, "unexpected hidden TAR header")
                        sha = member.name[len("objects/"):]
                        need(HEX.fullmatch(sha) and sha in objects and sha not in seen, "unknown/repeated archive object")
                        seen.add(sha)
                        with archive.extractfile(member) as stream:
                            restore_object(stream, objects[sha], member.size, sha, destination)
                        payload_end = member.offset_data + ((member.size + 511) // 512) * 512
                        count += len(objects[sha])
                tracked.finish(payload_end)
        need(seen == set(objects), "archive lacks declared objects")
        print(json.dumps({"verified_bundle": group["name"], "logical_files": group["file_count"]}), flush=True)
    need(count == manifest["selected_file_count"], "incomplete snapshot")
    return count

def verify_restored(manifest, groups, workspace):
    for _, _, objects in groups:
        for rows in objects.values():
            for row in rows:
                target = long_path(workspace / safe_relative(row["path"]))
                need(not target.is_symlink() and sha_file(target) == (row["bytes"], row["sha256"]), "restored workspace file differs: " + row["path"])
    pin = manifest["final_acceptance"]
    need(sha_file(workspace / safe_relative(pin["path"])) == (pin["bytes"], pin["sha256"]), "final STEP079 acceptance differs")

def resolve_path(manifest, value, workspace, document=None):
    normalized = value.replace("\\", "/")
    if document:
        doc = document.replace("\\", "/")
        for override in manifest.get("link_overrides", []):
            if override["document"] == doc and override["literal_target"] == normalized:
                return workspace / safe_relative(override["workspace_relative_path"])
        parent = workspace / safe_relative(doc)
        candidate = Path(os.path.abspath(parent.parent / normalized))
        need(candidate.is_relative_to(workspace.absolute()), "document target escapes workspace")
        return candidate
    for relative, original in manifest.get("external_path_map", {}).items():
        if normalized.casefold() == original.replace("\\", "/").casefold():
            return workspace / safe_relative(relative)
    prefixes = [manifest["original_workspace_root"].replace("\\", "/"), "D:/Aenv/pro/pro"]
    for prefix in prefixes:
        if normalized.casefold().startswith(prefix.casefold() + "/"):
            return workspace / safe_relative(normalized[len(prefix) + 1:])
    return workspace / safe_relative(normalized)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="hash all payloads and every archived object")
    verify.add_argument("--workspace", type=Path, help="also verify restored file bytes")
    restore = commands.add_parser("restore", help="materialize to a fresh empty destination; never execute archives")
    restore.add_argument("--destination", type=Path, required=True)
    resolve = commands.add_parser("resolve", help="map a preserved original path to a restored location")
    resolve.add_argument("original_path")
    resolve.add_argument("--workspace", type=Path, required=True)
    resolve.add_argument("--document", help="original document relative path, for historical relative-link repairs")
    args = parser.parse_args()
    manifest = load_manifest()
    if args.command == "resolve":
        result = resolve_path(manifest, args.original_path, args.workspace.absolute(), args.document)
        need(long_path(result).exists(), "mapped evidence is missing: " + str(result))
        print(result)
        return
    groups = inputs(manifest)
    directories = directory_layout(manifest, groups)
    canonical = verify_canonical()
    destination = None
    if args.command == "restore":
        destination = args.destination.absolute()
        plain_path(destination, directory=True)
        need(not destination.is_symlink(), "destination cannot be a symlink")
        need(not destination.exists() or destination.is_dir() and not any(destination.iterdir()), "destination must be new or empty; no overwrite/replay")
        destination.mkdir(parents=True, exist_ok=True)
        need(shutil.disk_usage(destination).free > manifest["raw_file_bytes"] + 64 * 1024 * 1024, "insufficient disk for complete restored bytes")
        for value in directories:
            target = destination / safe_relative(value)
            plain_path(target, directory=True)
            long_path(target).mkdir(parents=True, exist_ok=True)
    count = inspect_payloads(manifest, groups, destination)
    if destination is not None:
        verify_restored(manifest, groups, destination)
        marker = destination / "PORTABLE_RESTORE_RECEIPT.json"
        with marker.open("x", encoding="utf-8") as handle:
            json.dump({"created_utc": datetime.now(timezone.utc).isoformat(), "restored_files": count, "source_file_bytes_verified": True, "historical_native_identity_preserved": False, "project_code_executed": False, "runtime_or_case_authority_granted": False}, handle, indent=2)
    elif args.workspace:
        verify_restored(manifest, groups, args.workspace.absolute())
        need(all(long_path(args.workspace.absolute() / safe_relative(value)).is_dir() for value in directories), "restored directory layout incomplete")
    print(json.dumps({"verified_files": count, "canonical_source_files": canonical, "restored_destination": str(destination) if destination else None, "project_code_executed": False}), flush=True)

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, json.JSONDecodeError, tarfile.TarError) as error:
        print("Continuation verification refused: " + str(error), file=sys.stderr)
        raise SystemExit(1)
