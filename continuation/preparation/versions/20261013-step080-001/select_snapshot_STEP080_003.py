"""Select all continuation metadata/source and saved science; exclude named caches."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import stat
from pathlib import Path

ROOT = Path(r"D:\Aenv\pro2")
OUT = ROOT / "WORK/github-portability-20261013-step080-001"
REPO = ROOT / "github-portable-20261012-001"
DEST = REPO / "continuation/snapshots/20261013-step080-001"
GATE_ADOPTION = ROOT / "WORK/resume-20261013-001/generation/ROOT_SOURCE030_GENUINE_GATE_DIFFERENT_SOURCE_REVIEW_ADOPTION_001.json"
GATE_ADOPTION_SHA256 = "8f7a98b619552bc33f14654a72654bc6a33c1ed1a10ab8a9f379b46c76e76b1d"
GATE_ADOPTION_BYTES = 7075

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

def actual_pin(path, expected_sha256, expected_bytes):
    raw = paired(path)
    if len(raw) != expected_bytes or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise RuntimeError("actual acceptance bytes differ: " + str(path))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": expected_sha256, "bytes": expected_bytes}

parser = argparse.ArgumentParser(description=__doc__)
for name in ("triplet-acceptance", "final-acceptance"):
    parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--" + name + "-bytes", type=int, required=True)
args = parser.parse_args()
adoption_pin = actual_pin(GATE_ADOPTION, GATE_ADOPTION_SHA256, GATE_ADOPTION_BYTES)
adoption = json.loads(paired(GATE_ADOPTION))
if datetime.now(timezone.utc) < datetime.fromisoformat(adoption["interval_start"]):
    raise RuntimeError("Source030 interval has not begun")
if datetime.now(timezone.utc) + timedelta(seconds=60) >= datetime.fromisoformat(adoption["interval_end"]):
    raise RuntimeError("Source030 original60-second publication reserve refused")
triplet = actual_pin(args.triplet_acceptance, args.triplet_acceptance_sha256, args.triplet_acceptance_bytes)
final = actual_pin(args.final_acceptance, args.final_acceptance_sha256, args.final_acceptance_bytes)
actual_packaging_stages(triplet, final)
OUT.mkdir(parents=True, exist_ok=True)

excluded = ["WORK/github-portability-20261012-001", "WORK/github-portability-20261013-step080-001", "WORK/github-closeout-20261003-001/git_askpass.ps1", "WORK/github-closeout-20261003-001/git_askpass.cmd", "resume-2026-09-05/autonomous-2026-09-19-185105/copy-probe-archives-001/copy-default-profile-001.zip", "resume-2026-09-05/autonomous-2026-09-19-185105/copy-probe-archives-001/copy-torch-profile-001.zip", "resume-2026-09-05/git-runtime-drift-2026-09-08/MinGit-2.53.0.3-64-bit.zip"]
for name in ("relocated-controller-qa", "relocated-controller-qa-cfix", "relocated-controller-qa-inspector-diagnostics-v2"):
    for leaf in ("dot-tmp", "dot-pytest-cache", "src-bu-bytecode", "src-bu-critic-bytecode"):
        excluded.append("resume-2026-09-05/" + name + "/" + leaf)
excluded += ["resume-2026-09-05/child-profile-fix/runtime-isolation-proof-2026-09-19/probe-venv", "resume-2026-09-05/autonomous-2026-09-19-185105/compiler-temp"]
root_files = [p.name for p in ROOT.iterdir() if p.is_file()]
resumes = sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("resume-"))
work = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "WORK").iterdir() if p.is_dir() and p.name not in {"github-portability-20261012-001", "github-portability-20261013-step080-001"})
checkouts = ["pro2", "week8-recovery-controller-worktree", "week8-e2a-execution-4515-worktree", "week7-guard-integration-worktree"]
saved_root = sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name.startswith(("week7-", "week8-")) and p.name not in checkouts)
collection = ROOT / "project 2(ongoing)"
saved_collection = sorted(p.relative_to(ROOT).as_posix() for p in collection.iterdir() if p.is_dir() and (p.name.startswith(("week6-", "week7-", "week8-")) or p.name == "_collection"))
saved_collection += [p.relative_to(ROOT).as_posix() for p in collection.iterdir() if p.is_file()]
for base in checkouts + saved_root + saved_collection:
    path = ROOT / base
    if path.is_dir() and (path / ".tmp").is_dir():
        excluded.append(base + "/.tmp")
direct_scratch = []
for child in (ROOT / ".tmp").iterdir():
    if child.is_dir():
        direct_scratch += [p.relative_to(ROOT).as_posix() for p in child.iterdir() if p.is_file()]
direct_scratch.append(".tmp/synthetic/week8-d176-publication-validation-003/result.json")
external = {
    "external/pro3/runs/coordination/pro2_request_pro3_quiet_interval_003.json": r"D:\Aenv\pro3\runs\coordination\pro2_request_pro3_quiet_interval_003.json",
    "external/pro3/runs/coordination/windows_qualification_20261003_v3/host_job_conflict_root_cause_001.md": r"D:\Aenv\pro3\runs\coordination\windows_qualification_20261003_v3\host_job_conflict_root_cause_001.md",
    "external/pro3/runs/coordination/PRO2_URGENT_COORDINATION_20261001_005.md": r"D:\Aenv\pro3\runs\coordination\PRO2_URGENT_COORDINATION_20261001_005.md",
    "external/pro3/runs/coordination/PRO2_COORDINATION_RESPONSE_20261001_006.md": r"D:\Aenv\pro3\runs\coordination\PRO2_COORDINATION_RESPONSE_20261001_006.md",
    "external/pro3/runs/coordination/PRO3_COORDINATION_ACK_20261001_006.md": r"D:\Aenv\pro3\runs\coordination\PRO3_COORDINATION_ACK_20261001_006.md",
}
for number, day in ((26, "20261012"), (27, "20261012"), (28, "20261012"), (30, "20261013")):
    relative = f"external/pro3/runs/coordination/pro2_source{number:03d}_scheduling_{day}_v1/pro2_source{number:03d}_response_001.json"
    original = rf"D:\Aenv\pro3\runs\coordination\pro2_source{number:03d}_scheduling_{day}_v1\pro2_source{number:03d}_response_001.json"
    retained = ROOT / f"WORK/resume-{day}-001/coordination/PRO3_GENUINE_SOURCE{number:03d}_RESPONSE_RETAINED_COPY_001.json"
    if not Path(original).is_file() or not retained.is_file() or paired(Path(original)) != paired(retained):
        raise RuntimeError("born peer response/retained copy mismatch: " + original)
    external[relative] = original
# Source029 is an unfulfilled expired request, not an invented peer response.
# Carry the exact28 historical repairs. The separately accepted additive SESSION retains every old byte.
prior_manifest_path = REPO / "continuation/manifest.json"
prior_manifest_raw = paired(prior_manifest_path)
overrides = json.loads(prior_manifest_raw)["link_overrides"]
if len(overrides) != 28 or any(set(row) != {"document", "literal_target", "workspace_relative_path"}
                             or row["document"] != "resume-2026-09-28-001/SESSION.md"
                             or not (ROOT / row["workspace_relative_path"]).is_file() for row in overrides):
    raise RuntimeError("exact28 inherited SESSION repairs or their mapped bytes are missing")
groups = [
    {"name": "working-continuation", "include": sorted(root_files + resumes + work + ["relocation-2026-09-19"] + direct_scratch)},
    {"name": "source-checkouts", "include": checkouts},
    {"name": "saved-scientific-assets", "include": sorted(saved_root + saved_collection)},
    {"name": "frozen-runtime-reference", "include": ["runtimes/week8-python313-frozen-001"], "preserve_bytecode": True},
    {"name": "source-git-history", "include": ["WORK/github-portability-20261012-001/source-history.bundle"]},
]
# The single Git bundle is an explicit inclusion despite the live preparation directory exclusion.
required_current_roots = {"WORK/resume-20261012-001", "WORK/resume-20261013-001"}
if not required_current_roots <= set(work):
    raise RuntimeError("current continuation evidence roots are missing")
prior_manifest = REPO / "continuation/manifest.json"
prior_canonical = REPO / "continuation/canonical-source.json"
config = {"schema_version": 1, "milestone": "STEP080", "groups": groups, "exclude": excluded,
          "external_files": external, "link_overrides": overrides,
          "Source030_Root_gate_adoption": adoption_pin,
          "actual_triplet_acceptance": triplet, "final_acceptance": final,
          "prior_manifest": {"path": prior_manifest.relative_to(REPO).as_posix(), "sha256": hashlib.sha256(prior_manifest_raw).hexdigest(), "bytes": len(prior_manifest_raw)},
          "prior_canonical_source": {"path": prior_canonical.relative_to(REPO).as_posix(), "sha256": hashlib.sha256(paired(prior_canonical)).hexdigest(), "bytes": len(paired(prior_canonical))},
          "output_namespace": DEST.relative_to(REPO).as_posix(),
          "required_current_evidence_roots": sorted(required_current_roots),
          "selected_three_roles_and_six_document_acceptance_are_actual_late_inputs": True,
          "project_code_fixtures_science_or_training_executed": False}
path = OUT / "SNAPSHOT_SELECTION_001.json"
with path.open("x", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps({"config": str(path), "groups": len(groups), "selected_roots": sum(len(g["include"]) for g in groups), "link_overrides": len(overrides), "external_records": len(external)}))
