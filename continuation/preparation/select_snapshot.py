"""Select all continuation metadata/source and saved science; exclude named caches."""
import json
from pathlib import Path

ROOT = Path(r"D:\Aenv\pro2")
OUT = ROOT / "WORK/github-portability-20261012-001"
excluded = ["WORK/github-portability-20261012-001", "WORK/github-closeout-20261003-001/git_askpass.ps1", "WORK/github-closeout-20261003-001/git_askpass.cmd", "resume-2026-09-05/autonomous-2026-09-19-185105/copy-probe-archives-001/copy-default-profile-001.zip", "resume-2026-09-05/autonomous-2026-09-19-185105/copy-probe-archives-001/copy-torch-profile-001.zip", "resume-2026-09-05/git-runtime-drift-2026-09-08/MinGit-2.53.0.3-64-bit.zip"]
for name in ("relocated-controller-qa", "relocated-controller-qa-cfix", "relocated-controller-qa-inspector-diagnostics-v2"):
    for leaf in ("dot-tmp", "dot-pytest-cache", "src-bu-bytecode", "src-bu-critic-bytecode"):
        excluded.append("resume-2026-09-05/" + name + "/" + leaf)
excluded += ["resume-2026-09-05/child-profile-fix/runtime-isolation-proof-2026-09-19/probe-venv", "resume-2026-09-05/autonomous-2026-09-19-185105/compiler-temp"]
root_files = [p.name for p in ROOT.iterdir() if p.is_file()]
resumes = sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("resume-"))
work = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "WORK").iterdir() if p.is_dir() and p.name != "github-portability-20261012-001")
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
session = ROOT / "resume-2026-09-28-001/SESSION.md"
text = session.read_text(encoding="utf-8")
import re
targets = re.findall(r"\]\(([^)]+)\)", text)
overrides = []
for target in sorted(set(targets)):
    target = target.split("#", 1)[0]
    candidate = session.parent / target
    mapped = None
    if target.startswith("WORK/") and not candidate.is_file() and (ROOT / target).is_file():
        mapped = target
    if target in {"keepawake-30h-002/BOUND_REVIEW_002.md", "keepawake-30h-002/BINDING_MANIFEST_002.json", "CANDIDATE_REVIEW_001_STATIC_REPORT.md"}:
        mapped = "resume-2026-10-01-30h-001/" + target
    if mapped:
        overrides.append({"document": "resume-2026-09-28-001/SESSION.md", "literal_target": target, "workspace_relative_path": mapped})
if len(overrides) != 28:
    raise RuntimeError("expected exact28 known historical SESSION repairs, found " + str(len(overrides)))
groups = [
    {"name": "working-continuation", "include": sorted(root_files + resumes + work + ["relocation-2026-09-19"] + direct_scratch)},
    {"name": "source-checkouts", "include": checkouts},
    {"name": "saved-scientific-assets", "include": sorted(saved_root + saved_collection)},
    {"name": "frozen-runtime-reference", "include": ["runtimes/week8-python313-frozen-001"], "preserve_bytecode": True},
    {"name": "source-git-history", "include": ["WORK/github-portability-20261012-001/source-history.bundle"]},
]
# The single Git bundle is an explicit inclusion despite the live preparation directory exclusion.
config = {"groups": groups, "exclude": excluded, "external_files": external, "link_overrides": overrides}
path = OUT / "SNAPSHOT_SELECTION_001.json"
with path.open("x", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps({"config": str(path), "groups": len(groups), "selected_roots": sum(len(g["include"]) for g in groups), "link_overrides": len(overrides), "external_records": len(external)}))
