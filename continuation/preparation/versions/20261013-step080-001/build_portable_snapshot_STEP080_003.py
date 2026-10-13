"""Create a byte-preserving, deduplicated continuation snapshot. No project imports."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import tarfile

ROOT = Path(r"D:\Aenv\pro2")
REPO = ROOT / "github-portable-20261012-001"
OUT = ROOT / "WORK/github-portability-20261013-step080-001"
DEST = REPO / "continuation/snapshots/20261013-step080-001"
PART_SIZE = 32 * 1024 * 1024
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", "node_modules", "%LOCALAPPDATA%", ".tmp_schedule_render"}
PRIVATE_NAMES = {".git", ".env", ".github_token", "credentials.json", "id_rsa", "id_ed25519", "settings.local.json"}
PATTERNS = [re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,}"), re.compile(rb"github_pat_[A-Za-z0-9_]{50,}"), re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"), re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\r?\n(?:[A-Za-z0-9+/=]+\r?\n){1,}-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")]
token_file = Path(r"C:\Users\aladdin-alyanai\.github_token")
private_token = token_file.read_bytes().strip() if token_file.is_file() else b""
public_allowlist_path = ROOT / "WORK/github-portability-20261012-001/PUBLIC_CPYTHON_TEST_KEY_ALLOWLIST_001.json"
public_allowlist_raw = public_allowlist_path.read_bytes()
if len(public_allowlist_raw) != 8124 or hashlib.sha256(public_allowlist_raw).hexdigest() != "b7d6f3f876135b3638328a49078b2f56856bee392b8251d3a692edab5b2a5aad":
    raise RuntimeError("exact inherited public CPython fixture allowlist differs")
public_allowlist = json.loads(public_allowlist_raw)

def paired(path):
    for position, component in enumerate((path, *path.parents)):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024 or position and not stat.S_ISDIR(info.st_mode):
            raise RuntimeError("nonordinary acceptance path/ancestor: " + str(component))
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2097152:
        raise RuntimeError("original2MiB acceptance input cap refused")
    fields = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
                           info.st_mode, info.st_nlink, getattr(info, "st_file_attributes", 0), getattr(info, "st_birthtime_ns", 0))
    with path.open("rb") as handle:
        fd_before = os.fstat(handle.fileno())
        if not stat.S_ISREG(fd_before.st_mode) or fd_before.st_nlink != 1 or not 0 < fd_before.st_size <= 2097152:
            raise RuntimeError("original2MiB acceptance descriptor cap refused")
        first = handle.read(2097153)
        fd_mid = os.fstat(handle.fileno())
        handle.seek(0)
        second = handle.read(2097153)
        fd_after = os.fstat(handle.fileno())
    after = path.lstat()
    if first != second or len(first) != before.st_size or len(first) != fd_before.st_size:
        raise RuntimeError("paired acceptance bytes differ")
    if fields(before) != fields(after) or fields(fd_before) != fields(fd_mid) or fields(fd_before) != fields(fd_after):
        raise RuntimeError("acceptance PATH9/descriptor9 stability refused")
    if any(fields(before)[index] != fields(fd_before)[index] for index in (0, 1, 2, 3, 6, 7, 8)):
        raise RuntimeError("seven shared acceptance identity fields differ")
    return first

# Compact actual stage prerequisites. These are byte/Source checks, never scientific or runtime admission.
SOURCE030 = {"path": str(ROOT / "WORK/resume-20261013-001/coordination/ROOT_SOURCE_COMPUTE_ACCEPTANCE_030.json"),
             "sha256": "2ec413ea7fa3e3a6222136f803b0e8ce746699bb34830f2329eb079794b46b90", "bytes": 13262}
REVIEWERS = {"/root/source_review", "/root/checker_metadata_writer", "/root/actual_record_checker", "/root/owner_docs_review", "/root/runtime_audit"}
ROLES = ["checker_dependency_audit", "checker_protocol", "checker_manifest"]
PENDING = ["phase_peer", "binding", "pipeline_peer", "checker_config", "checker_peer", "table", "constructor", "constructor_manifest", "constructor_review", "selector"]
PRIMARY = [
    ("AGENTS", "AGENTS.md", "prepend", "15fefc95ef50e3f98bd3073750a484458ba7254962367d2b7d74741bba806e7b", 356468),
    ("START_HERE", "START_HERE.md", "prepend", "bee0e7550cc282da3d6f88146ce06efae5131e940d194b084f4b4a32047f0e8c", 149166),
    ("HANDOFF", "HANDOFF.md", "prepend", "879bffb328551febb415a3a5224814ea59c5699d8ca64a480174ade18fc7a8c5", 193478),
    ("PROJECT_STATE", "week8-recovery-controller-worktree/PROJECT_STATE.md", "prepend", "0cae678d001b18b49edb389210de1aaf2a1c2cc151d6b76d60c53842e07ef74d", 209161),
    ("CLAUDE", "week8-recovery-controller-worktree/CLAUDE.md", "prepend", "5189330d1ebb26598801d38c404515f4d851316f7e290195ec141ebb5e564a81", 185891),
    ("SESSION", "resume-2026-09-28-001/SESSION.md", "append", "710f9ce00eaf2b386e35761c4776b79eab3911dc129c4403d1bb53594ccf46d5", 522957),
]

def need(condition, message):
    if not condition:
        raise RuntimeError(message)

def prerequisite_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path

def prerequisite(expected, raw_value=False):
    need(type(expected) is dict and set(expected) == {"path", "sha256", "bytes"}, "closed actual prerequisite f3 required")
    raw = paired(prerequisite_path(expected["path"]))
    need(len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"], "actual prerequisite pin differs")
    return raw if raw_value else json.loads(raw)

def contains(value, wanted):
    return value == wanted or type(value) is dict and any(contains(item, wanted) for item in value.values()) or type(value) is list and any(contains(item, wanted) for item in value)

def utc_ns(value):
    moment = datetime.fromisoformat(value)
    need(moment.tzinfo is not None and moment.utcoffset() == timedelta(0), "actual aware UTC time required")
    elapsed = moment - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (elapsed.days * 86400 + elapsed.seconds) * 1000000000 + elapsed.microseconds * 1000

def reviewed(support, subjects):
    need(type(support) is dict and set(support) == {"different_review", "Root_adoption"}, "actual review/adoption support2 required")
    review = prerequisite(support["different_review"])
    adoption = prerequisite(support["Root_adoption"])
    need(review.get("reviewer") in REVIEWERS and review.get("reviewer") not in {"/root", "/root/portable_docs_writer"},
         "credible genuinely different reviewer required")
    need(review.get("checks_failed") == 0 and type(review.get("verdict")) is str and review["verdict"].startswith("PASS"),
         "actual successful different Source review required")
    need(review.get("target_execution") is False and review.get("operational_authority") is False and review.get("Source030") == SOURCE030,
         "exact current Source030 Source-only review required")
    full_pin = review.get("full_proof")
    full = prerequisite(full_pin)
    checks = full.get("checks")
    need(full.get("reviewer") == review["reviewer"] and full.get("Source030") == SOURCE030
         and full.get("target_execution") is False and full.get("operational_authority") is False
         and full.get("checks_failed") == 0 and full.get("verdict") == review["verdict"], "actual pinned full proof identity/scope differs")
    need(type(checks) is list and len(checks) > 0 and all(type(row) is dict and row.get("passed") is True for row in checks)
         and type(full.get("serialized_check_count")) is int and full["serialized_check_count"] == len(checks)
         and review.get("serialized_check_count") == len(checks)
         and type(full.get("actual_input_count")) is int and full["actual_input_count"] > 0
         and review.get("actual_input_count") == full["actual_input_count"], "real full-proof checks/counts do not reconcile")
    need(all(contains(review, item) and contains(full, item) for item in subjects), "actual review/full-proof subject f3 coverage differs")
    need(adoption.get("author") == "/root" and type(adoption.get("verdict")) is str and adoption["verdict"].startswith("ACCEPT")
         and adoption.get("target_execution") is False and adoption.get("operational_authority") is False
         and adoption.get("Source030") == SOURCE030, "actual current Source030 Root ACCEPT decision required")
    need(contains(adoption, support["different_review"]) and contains(adoption, full_pin)
         and all(contains(adoption, item) for item in subjects), "separate actual Root ACCEPT review/proof/subject joins differ")
    reviewed_ns = utc_ns(review["created_utc"])
    proof_ns = utc_ns(full["created_utc"])
    adopted_ns = utc_ns(adoption["created_utc"])
    now_ns = utc_ns(datetime.now(timezone.utc).isoformat())
    need(proof_ns <= reviewed_ns <= adopted_ns <= now_ns, "actual full-proof/review/Root-adoption chronology differs")
    for expected in subjects:
        path = prerequisite_path(expected["path"])
        raw = paired(path)
        born_ns = path.lstat().st_birthtime_ns
        need(len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"], "review subject bytes changed during chronology guard")
        need(type(born_ns) is int and 0 < born_ns <= proof_ns, "actual subject birth must precede the full Source review")
        if Path(expected["path"]).suffix.casefold() == ".json":
            body = json.loads(raw)
            if type(body) is dict and "created_utc" in body:
                need(utc_ns(body["created_utc"]) <= proof_ns, "actual subject record time must precede review")
    return review, adoption

def accepted_stage(adoption_pin, expected_record_type):
    adoption = prerequisite(adoption_pin)
    need(adoption.get("author") == "/root" and adoption.get("Source030") == SOURCE030
         and type(adoption.get("verdict")) is str and adoption["verdict"].startswith("ACCEPT")
         and adoption.get("target_execution") is False and adoption.get("operational_authority") is False,
         "actual current Source030 Root stage ACCEPT required")
    subject_pin = adoption.get("subject")
    subject = prerequisite(subject_pin)
    need(subject.get("record_type") == expected_record_type and subject.get("author") == "/root"
         and subject.get("Source030") == SOURCE030 and subject.get("target_execution") is False
         and subject.get("operational_authority") is False, "actual accepted stage subject semantics differ")
    review_pin = adoption.get("different_review")
    review = prerequisite(review_pin)
    need(adoption.get("full_proof") == review.get("full_proof"), "Root stage adoption must pin actual full proof")
    reviewed({"different_review": review_pin, "Root_adoption": adoption_pin}, [subject_pin])
    return subject

def actual_packaging_stages(triplet_adoption_pin, final_adoption_pin):
    triplet = accepted_stage(triplet_adoption_pin, "Root_Source030_checker022_triplet_actual_static_publication_outcome")
    need(triplet.get("actual_three_role_static_publication_complete") is True and triplet.get("canonical_roles") == ROLES
         and triplet.get("selected_canonical_path_count") == 35 and triplet.get("selected_role_count") == 45
         and triplet.get("pending_roles") == PENDING and triplet.get("scientific_authority") is False,
         "actual completed35/45 triplet required before packaging")
    support_rows = triplet.get("canonical_acceptance_support")
    need(type(support_rows) is list and len(support_rows) == 3, "actual three canonical supports required")
    for row, role in zip(support_rows, ROLES):
        need(type(row) is dict and set(row) == {"role", "canonical", "author_receipt", "publication", "different_review", "Root_adoption", "complete_predecessor_inverse_retained"}
             and row["role"] == role and row["complete_predecessor_inverse_retained"] is True, "actual closed7 role support differs")
        canonical = prerequisite(row["canonical"], True)
        publication = prerequisite(row["publication"])
        author = prerequisite(row["author_receipt"])
        need(publication.get("author") == "/root" and publication.get("role") == role and publication.get("Source030") == SOURCE030
             and publication.get("canonical_publication") is True and publication.get("canonical") == row["canonical"]
             and publication.get("author_receipt") == row["author_receipt"] and publication.get("target_execution") is False
             and publication.get("operational_authority") is False and publication.get("Native_Parser_invoked") is False,
             "actual canonical publication support differs")
        need(author.get("role") == role and author.get("Source030") == SOURCE030 and author.get("canonical_publication") is False
             and prerequisite(author["draft"], True) == canonical, "actual canonical/draft bytes differ")
        reviewed({name: row[name] for name in ("different_review", "Root_adoption")}, [row["canonical"], row["publication"], row["author_receipt"]])
    publication = accepted_stage(final_adoption_pin, "Root_STEP080_actual_six_document_publication_receipt")
    need(publication.get("all_six_complete_STEP079_bytes_retained") is True
         and publication.get("exact_order_five_prepends_then_SESSION_append") is True
         and publication.get("scientific_authority") is False, "actual accepted additive six-document publication required")
    documents = publication.get("documents")
    need(type(documents) is list and len(documents) == 6, "actual six primary publication rows required")
    for row, (name, relative, mode, before_sha, before_bytes) in zip(documents, PRIMARY):
        expected_path = str(ROOT / relative)
        need((row.get("name"), row.get("path"), row.get("mode")) == (name, expected_path, mode)
             and row["before"] == {"path": expected_path, "sha256": before_sha, "bytes": before_bytes}, "actual six primary path/order/before pins differ")
        current = prerequisite(row["published"], True)
        need(row["published"]["path"] == expected_path and current == prerequisite(row["candidate"], True), "current accepted primary/candidate bytes differ")
        before = prerequisite(row["complete_before_copy"], True)
        need(len(before) == before_bytes and hashlib.sha256(before).hexdigest() == before_sha, "complete STEP079 before copy differs")
        addition = prerequisite(row["addition"], True)
        need(current == (addition + before if mode == "prepend" else before + addition), "whole additive primary equation differs")
    return triplet, publication

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

def put_or_verify_owned(path, data):
    if path.exists():
        existing, _ = stable_read(path)
        if existing != data:
            raise RuntimeError("existing current owned metadata differs: " + str(path))
    else:
        put(path, data)

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

def repository_input(pin_value):
    path = REPO / pin_value["path"]
    data, _ = stable_read(path)
    if len(data) != pin_value["bytes"] or digest(data) != pin_value["sha256"]:
        raise RuntimeError("prior managed snapshot pin differs: " + str(path))
    return data

def workspace_input(pin_value):
    path = ROOT / pin_value["path"]
    data, _ = stable_read(path)
    if len(data) != pin_value["bytes"] or digest(data) != pin_value["sha256"]:
        raise RuntimeError("actual acceptance pin differs: " + str(path))
    return data

def canonical_source(config):
    # Preserve ordinary code from the already accepted controller commit; no project import or Git archive execution.
    prior_raw = repository_input(config["prior_canonical_source"])
    prior = json.loads(prior_raw)
    rows = []
    for old_row in prior["files"]:
        name = old_row["path"]
        row = dict(old_row)
        if name in {"CLAUDE.md", "PROJECT_STATE.md"}:
            data, _ = stable_read(ROOT / "week8-recovery-controller-worktree" / name)
            row.update(bytes=len(data), sha256=digest(data), origin="exact_accepted_STEP080_primary_snapshot")
            # Root's separately reviewed managed publication promotes these same bytes later.
        else:
            data, _ = stable_read(REPO / name)
            if len(data) != old_row["bytes"] or digest(data) != old_row["sha256"]:
                raise RuntimeError("accepted ordinary Source changed: " + name)
        rows.append(row)
    value = {"schema_version": 1, "original_controller_commit": prior["original_controller_commit"],
             "source_identity_or_tests_requalified": False, "files": rows}
    path = DEST / "canonical-source.json"
    put_or_verify_owned(path, json_data(value))
    return pin(path)

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reuse-complete-own-groups", action="store_true", help="Rehash only finished current owned groups; no project tools")
    args = parser.parse_args()
    config = json.loads(args.config.read_bytes())
    if config["schema_version"] != 1 or config["milestone"] != "STEP080" or config["output_namespace"] != DEST.relative_to(REPO).as_posix():
        raise RuntimeError("exact reviewed STEP080 selection/namespace required")
    adoption_raw = workspace_input(config["Source030_Root_gate_adoption"])
    adoption = json.loads(adoption_raw)
    if digest(adoption_raw) != "8f7a98b619552bc33f14654a72654bc6a33c1ed1a10ab8a9f379b46c76e76b1d" or len(adoption_raw) != 7075:
        raise RuntimeError("genuine adopted Source030 bytes required")
    if datetime.now(timezone.utc) < datetime.fromisoformat(adoption["interval_start"]):
        raise RuntimeError("Source030 interval has not begun")
    if datetime.now(timezone.utc) + timedelta(seconds=60) >= datetime.fromisoformat(adoption["interval_end"]):
        raise RuntimeError("Source030 original60-second publication reserve refused")
    workspace_input(config["actual_triplet_acceptance"])
    workspace_input(config["final_acceptance"])
    actual_packaging_stages(config["actual_triplet_acceptance"], config["final_acceptance"])
    if (DEST / "manifest.json").exists() or (DEST / "bundles").exists() and not args.reuse_complete_own_groups:
        raise RuntimeError("fresh publication payload namespace required")
    OUT.mkdir(parents=True, exist_ok=True)
    # Freeze every inclusion and reject cross-group aliases before any payload publication.
    selected = []
    all_paths = set()
    directories = set()
    excluded = {}
    for group in config["groups"]:
        files, omissions = collect(group["include"], config.get("exclude", []), group.get("preserve_bytecode", False), directories)
        for relative, _ in files:
            if relative.casefold() in all_paths:
                raise RuntimeError("duplicate logical snapshot path: " + relative)
            all_paths.add(relative.casefold())
        excluded.update(omissions)
        selected.append((group, files))
    external_files = []
    external_map = {}
    for relative, source in config["external_files"].items():
        if relative.casefold() in all_paths:
            raise RuntimeError("duplicate external logical path: " + relative)
        all_paths.add(relative.casefold())
        external_files.append((relative, Path(source)))
        external_map[relative] = source
        parts = relative.split("/")
        directories.update("/".join(parts[:length]) for length in range(1, len(parts)))
    canonical = canonical_source(config)
    groups = []
    for group, files in selected:
        retained = reuse_complete_group(group["name"], files) if args.reuse_complete_own_groups else None
        groups.append(retained if retained else archive_group(group["name"], files))
    if external_files:
        groups.append(archive_group("external-peer-records", sorted(external_files), external_map))
    inventory = {"schema_version": 1, "directories": sorted(directories)}
    index_path = DEST / "indexes/directory-layout.json.gz"
    put_or_verify_owned(index_path, gzip.compress(json_data(inventory), compresslevel=9, mtime=0))
    layout = {**pin(index_path), "directory_count": len(directories), "filesystem_identity_or_old_authority_reproduced": False}
    # Keep exact previous pointer bytes in this new immutable namespace before Root promotes the current pointers.
    put_or_verify_owned(DEST / "history/STEP079-manifest.json", repository_input(config["prior_manifest"]))
    put_or_verify_owned(DEST / "history/STEP079-canonical-source.json", repository_input(config["prior_canonical_source"]))
    manifest = {"schema_version": 1, "record_type": "portable_byte_preserving_continuation_snapshot", "created_utc": datetime.now(timezone.utc).isoformat(),
                "repository": "RAMZI0TO99/beyond-uncertainty", "original_workspace_root": str(ROOT), "milestone": "STEP080",
                "final_acceptance": config["final_acceptance"], "actual_triplet_acceptance": config["actual_triplet_acceptance"],
                "Source030_Root_gate_adoption": config["Source030_Root_gate_adoption"],
                "original_scientific_commit": "4515d5165756c8d1669d38d2ee854fa1051b1017", "original_controller_commit": "17ef387136062c0254c96982b9f7124acbff096b", "original_week7_commit": "4782c90ce0e66fb46768f08d5080a27590a51a48",
                "bundles": groups, "directory_layout": layout, "canonical_source_manifest": canonical,
                "selected_file_count": sum(group["file_count"] for group in groups), "raw_file_bytes": sum(group["raw_file_bytes"] for group in groups), "payload_bytes": sum(group["compressed_payload_bytes"] for group in groups),
                "maximum_part_bytes": PART_SIZE, "excluded_named_paths": config.get("exclude", []), "omitted_installed_environment_cache_and_private_paths": excluded,
                "restored_bytes_are_content_evidence_not_historical_native_identity": True, "historical_Source_leases_and_case_authority_are_not_reissued": True,
                "project_code_fixtures_science_or_training_executed": False,
                "secret_scan": {"bounded_patterns": len(PATTERNS), "actual_private_credential_match_check": bool(private_token), "operational_credential_matches": 0,
                                "public_CPython_test_key_files_officially_classified_and_archived_unchanged": public_allowlist},
                "link_overrides": config.get("link_overrides", []), "external_path_map": external_map}
    if datetime.now(timezone.utc) + timedelta(seconds=60) >= datetime.fromisoformat(adoption["interval_end"]):
        raise RuntimeError("Source030 reserve refused before final manifest publication")
    put(DEST / "manifest.json", json_data(manifest))
    receipt = {"manifest": pin(DEST / "manifest.json"), "canonical_source": canonical, "directory_layout": layout,
               "file_count": manifest["selected_file_count"], "raw_file_bytes": manifest["raw_file_bytes"], "payload_bytes": manifest["payload_bytes"],
               "source_or_scientific_execution": False, "active_pointer_promotion_by_Root_required": True}
    put(OUT / "PORTABLE_PAYLOAD_PREPARATION_RECEIPT_001.json", json_data(receipt))
    print(json.dumps(receipt), flush=True)

if __name__ == "__main__":
    main()
