"""Create a byte-preserving, deduplicated continuation snapshot. No project imports."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile

ROOT = Path(r"D:\Aenv\pro2")
REPO = ROOT / "github-portable-20261012-001"
OUT = ROOT / "WORK/github-portability-20261012-001"
DEST = REPO / "continuation"
PART_SIZE = 32 * 1024 * 1024
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", "node_modules", "%LOCALAPPDATA%", ".tmp_schedule_render"}
PRIVATE_NAMES = {".git", ".env", ".github_token", "credentials.json", "id_rsa", "id_ed25519", "settings.local.json"}
PATTERNS = [re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,}"), re.compile(rb"github_pat_[A-Za-z0-9_]{50,}"), re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"), re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\r?\n(?:[A-Za-z0-9+/=]+\r?\n){1,}-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")]
token_file = Path(r"C:\Users\aladdin-alyanai\.github_token")
private_token = token_file.read_bytes().strip() if token_file.is_file() else b""
public_allowlist_path = OUT / "PUBLIC_CPYTHON_TEST_KEY_ALLOWLIST_001.json"
public_allowlist = json.loads(public_allowlist_path.read_bytes()) if public_allowlist_path.is_file() else {}

def winpath(path):
    value = os.path.abspath(path)
    return Path("\\\\?\\" + value) if os.name == "nt" and not value.startswith("\\\\?\\") else Path(value)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def json_data(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")

def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
    if path.read_bytes() != data:
        raise RuntimeError("write/readback mismatch: " + str(path))

def pin(path):
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return {"path": path.relative_to(REPO).as_posix(), "bytes": size, "sha256": h.hexdigest()}

def stable_read(path):
    target = winpath(path)
    plain_ancestors(path)
    before = target.lstat()
    if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 1024:
        raise RuntimeError("nonordinary input: " + str(path))
    data = target.read_bytes()
    after = target.lstat()
    keys = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, key) != getattr(after, key) for key in keys) or len(data) != before.st_size:
        raise RuntimeError("input changed while read: " + str(path))
    possible_key = PATTERNS[-1].search(data) is not None
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError:
        relative = ""
    public_key_fixture = relative in public_allowlist and public_allowlist[relative]["sha256"] == digest(data) and public_allowlist[relative]["bytes"] == len(data)
    if any(pattern.search(data) for pattern in PATTERNS[:-1]) or private_token and private_token in data or possible_key and not public_key_fixture:
        raise RuntimeError("potential credential in input; contents withheld: " + str(path))
    return data, before.st_mode & 0o777

def plain_ancestors(path):
    absolute = Path(os.path.abspath(path))
    for position, component in enumerate((absolute, *absolute.parents)):
        actual = winpath(component)
        info = actual.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise RuntimeError("reparse input or ancestor refused: " + str(component))
        if position and not stat.S_ISDIR(info.st_mode):
            raise RuntimeError("non-directory input ancestor: " + str(component))

class MultipartWriter:
    def __init__(self, name):
        self.name = name
        self.file = None
        self.parts = []
        self.part_size = 0
        self.total = 0

    def writable(self):
        return True

    def tell(self):
        return self.total

    def write(self, data):
        start = 0
        while start < len(data):
            if self.file is None:
                path = DEST / "bundles" / f"{self.name}.tar.gz.part{len(self.parts):03d}"
                path.parent.mkdir(parents=True, exist_ok=True)
                self.file = path.open("xb")
                self.parts.append(path)
                self.part_size = 0
            take = min(len(data) - start, PART_SIZE - self.part_size)
            self.file.write(data[start:start + take])
            start += take
            self.part_size += take
            self.total += take
            if self.part_size == PART_SIZE:
                self.file.close()
                self.file = None
        return len(data)

    def flush(self):
        if self.file is not None:
            self.file.flush()

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

def collect(inclusions, exclusions, preserve_bytecode=False, directory_inventory=None):
    files = {}
    omitted = Counter()
    excluded = [Path(value) for value in exclusions]
    for relative in inclusions:
        base = ROOT / relative
        plain_ancestors(base)
        if not base.exists():
            raise RuntimeError("selected input missing: " + relative)
        if base.is_file():
            if base.name.casefold() in {name.casefold() for name in PRIVATE_NAMES} or base.name.casefold().startswith(".env."):
                omitted[relative] += 1
                continue
            if any(Path(relative) == item or item in Path(relative).parents for item in excluded) and relative != "WORK/github-portability-20261012-001/source-history.bundle":
                omitted[relative] += 1
                continue
            entries = [base]
        else:
            entries = []
            for current, dirs, names in os.walk(winpath(base), followlinks=False):
                ordinary_current = Path(str(current).removeprefix("\\\\?\\"))
                if directory_inventory is not None:
                    directory_inventory.add(ordinary_current.relative_to(ROOT).as_posix())
                retained = []
                for name in sorted(dirs):
                    child = ordinary_current / name
                    rel = child.relative_to(ROOT)
                    skip_name = name.casefold() in {item.casefold() for item in SKIP_DIRS} and not (preserve_bytecode and name.casefold() == "__pycache__")
                    retired_tree = name == "trees" and "qa-residue" in rel.parent.name
                    if skip_name or retired_tree or any(rel == item or item in rel.parents for item in excluded):
                        omitted[rel.as_posix()] += 1
                        continue
                    if getattr(winpath(child).lstat(), "st_file_attributes", 0) & 1024:
                        raise RuntimeError("reparse directory in selected input: " + str(child))
                    retained.append(name)
                dirs[:] = retained
                for name in sorted(names):
                    child = ordinary_current / name
                    rel = child.relative_to(ROOT)
                    if name.casefold() in {item.casefold() for item in PRIVATE_NAMES} or name.casefold().startswith(".env.") or any(rel == item or item in rel.parents for item in excluded):
                        omitted[rel.as_posix()] += 1
                        continue
                    entries.append(child)
        for path in entries:
            rel = path.relative_to(ROOT).as_posix()
            files[rel] = path
    return sorted(files.items()), dict(omitted)

def archive_group(name, files, external=None):
    writer = MultipartWriter(name)
    rows = []
    objects = {}
    raw_total = 0
    with gzip.GzipFile(filename="", mode="wb", fileobj=writer, mtime=0, compresslevel=6) as zipped:
        with tarfile.open(fileobj=zipped, mode="w|", format=tarfile.USTAR_FORMAT) as archive:
            for position, (relative, path) in enumerate(files):
                data, mode = stable_read(path)
                sha = digest(data)
                row = {"path": relative, "bytes": len(data), "sha256": sha, "mode": mode}
                if external and relative in external:
                    row["original_absolute_path"] = external[relative]
                rows.append(row)
                raw_total += len(data)
                if sha not in objects:
                    info = tarfile.TarInfo("objects/" + sha)
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(data))
                    objects[sha] = len(data)
                if (position + 1) % 2500 == 0:
                    print(json.dumps({"progress": name, "files": position + 1, "selected": len(files), "raw_bytes": raw_total}), flush=True)
    writer.close()
    inventory = {"schema_version": 1, "files": rows}
    index_path = DEST / "indexes" / (name + ".json.gz")
    put(index_path, gzip.compress(json_data(inventory), compresslevel=9, mtime=0))
    return {"name": name, "format": "content_addressed_tar_gzip_multipart_v1", "index": pin(index_path), "parts": [pin(path) for path in writer.parts], "file_count": len(rows), "raw_file_bytes": raw_total, "distinct_object_count": len(objects), "distinct_object_bytes": sum(objects.values()), "compressed_payload_bytes": writer.total}

def canonical_source():
    source = ROOT / "week8-recovery-controller-worktree"
    command = ["git", "-c", "safe.directory=" + source.as_posix(), "-C", str(source), "archive", "--format=tar", "17ef387136062c0254c96982b9f7124acbff096b"]
    result = subprocess.run(command, capture_output=True, check=True)
    rows = []
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        for member in archive:
            if not member.isfile():
                continue
            name = member.name
            if name in {"README.md", ".gitignore", "CLAUDE.md", "PROJECT_STATE.md"}:
                continue
            data = archive.extractfile(member).read()
            target = REPO / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if os.name != "nt":
                target.chmod(member.mode)
            rows.append({"path": name, "bytes": len(data), "sha256": digest(data), "git_mode": "100755" if member.mode & 0o111 else "100644", "origin": "accepted_controller_commit_17ef387"})
    for name in ("CLAUDE.md", "PROJECT_STATE.md"):
        data, mode = stable_read(source / name)
        (REPO / name).write_bytes(data)
        rows.append({"path": name, "bytes": len(data), "sha256": digest(data), "git_mode": "100644", "origin": "exact_uncommitted_STEP079_primary_snapshot"})
    path = DEST / "canonical-source.json"
    data = json_data({"schema_version": 1, "original_controller_commit": "17ef387136062c0254c96982b9f7124acbff096b", "source_identity_or_tests_requalified": False, "files": rows})
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError("existing own canonical Source manifest differs")
    else:
        put(path, data)

def reuse_complete_group(name, files):
    path = DEST / "indexes" / (name + ".json.gz")
    if not path.is_file():
        return None
    rows = json.loads(gzip.decompress(path.read_bytes()))["files"]
    if {row["path"] for row in rows} != {relative for relative, _ in files}:
        raise RuntimeError("completed own group selection differs: " + name)
    source_by_path = dict(files)
    objects = {}
    for row in rows:
        data, mode = stable_read(source_by_path[row["path"]])
        if len(data) != row["bytes"] or digest(data) != row["sha256"] or mode != row["mode"]:
            raise RuntimeError("completed own group Source bytes differ: " + row["path"])
        objects[row["sha256"]] = row["bytes"]
    parts = sorted((DEST / "bundles").glob(name + ".tar.gz.part*"))
    if not parts:
        raise RuntimeError("completed own group has no payload")
    return {"name": name, "format": "content_addressed_tar_gzip_multipart_v1", "index": pin(path), "parts": [pin(part) for part in parts], "file_count": len(rows), "raw_file_bytes": sum(row["bytes"] for row in rows), "distinct_object_count": len(objects), "distinct_object_bytes": sum(objects.values()), "compressed_payload_bytes": sum(part.stat().st_size for part in parts)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reuse-complete-own-groups", action="store_true", help="Rehash retained finished own groups; never replay old project tools")
    args = parser.parse_args()
    config = json.loads(args.config.read_bytes())
    if (DEST / "manifest.json").exists() or (DEST / "bundles").exists() and not args.reuse_complete_own_groups:
        raise RuntimeError("fresh publication payload namespace required")
    canonical_source()
    groups = []
    excluded = {}
    for group in config["groups"]:
        files, omissions = collect(group["include"], config.get("exclude", []), group.get("preserve_bytecode", False))
        excluded.update(omissions)
        retained = reuse_complete_group(group["name"], files) if args.reuse_complete_own_groups else None
        groups.append(retained if retained else archive_group(group["name"], files))
    external_files = []
    external_map = {}
    for relative, source in config["external_files"].items():
        external_files.append((relative, Path(source)))
        external_map[relative] = source
    if external_files:
        groups.append(archive_group("external-peer-records", sorted(external_files), external_map))
    manifest = {"schema_version": 1, "record_type": "portable_byte_preserving_continuation_snapshot", "created_utc": datetime.now(timezone.utc).isoformat(), "repository": "RAMZI0TO99/beyond-uncertainty", "original_workspace_root": str(ROOT), "milestone": "STEP079", "final_acceptance": {"path": "WORK/resume-20261007-001/generation/observer010_lease009_root_001/ROOT_SOURCE025_STEP079_ACTUAL_SIX_DOCUMENT_CREATION_DIFFERENT_AUDIT_FINAL_ADOPTION_001.json", "sha256": "1fea9a3865abdf6c6754c8a544880709a43f1a77341e8405fb53248703c99341", "bytes": 53679}, "original_scientific_commit": "4515d5165756c8d1669d38d2ee854fa1051b1017", "original_controller_commit": "17ef387136062c0254c96982b9f7124acbff096b", "original_week7_commit": "4782c90ce0e66fb46768f08d5080a27590a51a48", "bundles": groups, "selected_file_count": sum(group["file_count"] for group in groups), "raw_file_bytes": sum(group["raw_file_bytes"] for group in groups), "payload_bytes": sum(group["compressed_payload_bytes"] for group in groups), "maximum_part_bytes": PART_SIZE, "excluded_named_paths": config.get("exclude", []), "omitted_installed_environment_cache_and_private_paths": excluded, "restored_bytes_are_content_evidence_not_historical_native_identity": True, "historical_Source_leases_and_case_authority_are_not_reissued": True, "project_code_fixtures_science_or_training_executed": False, "secret_scan": {"bounded_patterns": len(PATTERNS), "actual_private_credential_match_check": bool(private_token), "operational_credential_matches": 0, "public_CPython_test_key_files_officially_classified_and_archived_unchanged": public_allowlist}, "link_overrides": config.get("link_overrides", []), "external_path_map": external_map}
    put(DEST / "manifest.json", json_data(manifest))
    put(OUT / "PORTABLE_PAYLOAD_PREPARATION_RECEIPT_001.json", json_data({"manifest": pin(DEST / "manifest.json"), "file_count": manifest["selected_file_count"], "raw_file_bytes": manifest["raw_file_bytes"], "payload_bytes": manifest["payload_bytes"], "source_or_scientific_execution": False}))
    print(json.dumps({"manifest": pin(DEST / "manifest.json"), "file_count": manifest["selected_file_count"], "payload_bytes": manifest["payload_bytes"]}), flush=True)

if __name__ == "__main__":
    main()
