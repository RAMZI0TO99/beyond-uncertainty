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
MAX_CANONICAL_METADATA_BYTES = 2 * 1024 * 1024
MAX_OVERLAY_METADATA_BYTES = 64 * 1024
CANONICAL_PREFIX_OVERLAY_PATHS = frozenset({"PROJECT_STATE.md"})
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

def pin_relative_path(pin):
    need(isinstance(pin, dict) and {"path", "bytes", "sha256"} <= set(pin), "missing payload byte pin")
    need(type(pin["bytes"]) is int and pin["bytes"] >= 0 and isinstance(pin["sha256"], str) and HEX.fullmatch(pin["sha256"]), "invalid payload byte pin")
    return safe_relative(pin["path"])

def validate_pin(pin):
    path = REPO / pin_relative_path(pin)
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

def read_metadata(path, limit):
    plain_path(path)
    need(long_path(path).is_file(), "missing/nonordinary metadata: " + str(path))
    with long_path(path).open("rb") as handle:
        data = handle.read(limit + 1)
    need(len(data) <= limit, "metadata exceeds size bound: " + str(path))
    return decode(data)

def canonical_overlays(canonical):
    path = REPO / "continuation/canonical-source-overlays.json"
    plain_path(path)
    if not os.path.lexists(long_path(path)):
        return {}
    record = read_metadata(path, MAX_OVERLAY_METADATA_BYTES)
    need(type(record) is dict and set(record) == {"schema_version", "record_type", "overlays"}, "invalid canonical overlay metadata")
    need(type(record["schema_version"]) is int and record["schema_version"] == 1 and record["record_type"] == "canonical_source_document_prefix_overlays", "unsupported canonical overlay metadata")
    need(type(record["overlays"]) is list, "canonical overlays must be a list")
    overlays = {}
    fields = {"path", "frozen_bytes", "frozen_sha256", "prefix_bytes", "current_bytes", "current_sha256"}
    for row in record["overlays"]:
        need(type(row) is dict and set(row) == fields, "invalid canonical document overlay")
        name = row["path"]
        safe_relative(name)
        need(name in canonical, "overlay has unknown canonical path: " + name)
        need(name not in overlays, "duplicate canonical document overlay: " + name)
        need(name in CANONICAL_PREFIX_OVERLAY_PATHS and canonical[name].get("origin") == "exact_accepted_STEP080_primary_snapshot", "overlay is not an allowed frozen document: " + name)
        need(all(type(row[key]) is int and row[key] > 0 for key in ("frozen_bytes", "prefix_bytes", "current_bytes")), "invalid canonical overlay byte counts")
        need(all(type(row[key]) is str and HEX.fullmatch(row[key]) for key in ("frozen_sha256", "current_sha256")), "invalid canonical overlay hashes")
        need((row["frozen_bytes"], row["frozen_sha256"]) == (canonical[name]["bytes"], canonical[name]["sha256"]), "overlay changes the frozen canonical pin: " + name)
        need(row["current_bytes"] == row["prefix_bytes"] + row["frozen_bytes"], "overlay prefix/suffix byte counts disagree: " + name)
        overlays[name] = row
    return overlays

def verify_canonical_overlay(frozen, overlay):
    path = REPO / pin_relative_path(frozen)
    plain_path(path)
    need(long_path(path).is_file(), "missing/nonordinary overlay document: " + frozen["path"])
    current_hash = hashlib.sha256()
    suffix_hash = hashlib.sha256()
    total = 0
    suffix_bytes = 0
    with long_path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            start = min(len(block), max(0, overlay["prefix_bytes"] - total))
            total += len(block)
            need(total <= overlay["current_bytes"], "overlay document exceeds pinned size: " + frozen["path"])
            current_hash.update(block)
            suffix_hash.update(block[start:])
            suffix_bytes += len(block) - start
    need((total, current_hash.hexdigest()) == (overlay["current_bytes"], overlay["current_sha256"]), "current overlay document SHA/size mismatch: " + frozen["path"])
    need((suffix_bytes, suffix_hash.hexdigest()) == (frozen["bytes"], frozen["sha256"]), "frozen canonical document suffix differs: " + frozen["path"])

def verify_canonical():
    record = read_metadata(REPO / "continuation/canonical-source.json", MAX_CANONICAL_METADATA_BYTES)
    need(type(record) is dict and type(record.get("schema_version")) is int and record["schema_version"] == 1 and type(record.get("files")) is list, "invalid canonical source inventory")
    canonical = {}
    seen = set()
    for row in record["files"]:
        pin_relative_path(row)
        name = row["path"]
        need(name.casefold() not in seen, "duplicate/colliding canonical source path: " + name)
        seen.add(name.casefold())
        canonical[name] = row
    overlays = canonical_overlays(canonical)
    for name, row in canonical.items():
        if name in overlays:
            verify_canonical_overlay(row, overlays[name])
        else:
            validate_pin(row)
    return len(canonical)

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
