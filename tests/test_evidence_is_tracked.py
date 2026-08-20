"""Evidence that a verifier reads must be IN THE REPOSITORY, not merely on disk.

Written after a near-miss on 2026-08-20 (D-103). `runs/*` is gitignored with
per-experiment exceptions, and `runs/w4_threshold` had none — so the commit
carrying the W4 Friday calibration shipped **two** files while its own message
claimed one hundred and thirty-six. It was caught by inspecting the commit
rather than trusting it.

Had it gone out, the bundle would have carried digests with no files: the
delta-12 failure D-041 exists to prevent, arriving through `.gitignore` instead
of through file selection. The comment at the top of `.gitignore` warns about
exactly this class of mistake and nothing enforced it. This does.

**The property, stated carefully.** Not "everything under `runs/` is tracked" —
D-075 ruling 3 deliberately tracks only the W3 pilot's manifest and rows, and
deliberately excludes checkpoints and per-transition exports. The property is
narrower and is the one that matters: **every file whose digest a tracked
evidence record attests, and which a verifier reads back to check that digest,
must itself be tracked.** Otherwise the verdict is uncheckable from a fresh
clone, which is the whole reason the digests are there.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Evidence whose digests a verifier reads back. The W3 pilot is deliberately
#: absent: it tracks its manifest and rows only, and nothing recomputes a
#: verdict from its exports (D-075 ruling 3).
VERIFIED_EVIDENCE = ("runs/w4_gate", "runs/w4_threshold")


def tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return set(out.stdout.split())


def evidence_records() -> list[Path]:
    found = []
    for root in VERIFIED_EVIDENCE:
        base = ROOT / root
        if not base.exists():
            continue
        found += sorted(base.rglob("threshold_calibration.json"))
        found += sorted(base.rglob("manifest.json"))
    return found


def referenced_paths(record: Path) -> set[str]:
    """Every repository path this record attests a digest for."""
    row = json.loads(record.read_text(encoding="utf-8"))
    attempt = record.parent
    out: set[str] = set()

    def add(p: Path) -> None:
        out.add(str(p.relative_to(ROOT)))

    for cell in row.get("cells", []) + row.get("runs", []):
        if "errors_file" in cell:
            add(attempt / cell["errors_file"])
        run_id = cell.get("run_id")
        if run_id and ("run_record_digest" in cell or "member_record_digest" in cell):
            add(attempt / "records" / run_id / "run.json")
            add(attempt / "records" / run_id / "metrics.jsonl")
    return out


def test_there_is_evidence_to_check():
    """A vacuous pass would be indistinguishable from a passing check."""
    records = evidence_records()
    assert records, "no evidence records found; this whole module would be vacuous"
    assert any("w4_threshold" in str(r) for r in records)
    assert any("w4_gate" in str(r) for r in records)


@pytest.mark.parametrize("record", evidence_records(), ids=lambda p: str(p.parent.name))
def test_the_evidence_record_itself_is_tracked(record):
    """The near-miss: a new experiment directory is swallowed by `runs/*`."""
    rel = str(record.relative_to(ROOT))
    assert rel in tracked_files(), (
        f"{rel} exists on disk but is NOT tracked by git. `runs/*` is ignored "
        "with per-experiment exceptions, so a new experiment directory is "
        "swallowed silently -- add rules for it in .gitignore (D-103)"
    )


@pytest.mark.parametrize("record", evidence_records(), ids=lambda p: str(p.parent.name))
def test_every_digested_artefact_is_tracked(record):
    """Digests without files cannot be verified from a fresh clone (D-075)."""
    tracked = tracked_files()
    referenced = referenced_paths(record)
    assert referenced, f"{record} references no artefacts; the check would be vacuous"
    missing = sorted(p for p in referenced if p not in tracked)
    assert not missing, (
        f"{len(missing)} artefact(s) whose digests {record.name} attests are not "
        f"tracked, e.g. {missing[:3]}. A verdict nobody can recompute from a clone "
        "is a claim, not evidence"
    )


@pytest.mark.parametrize("record", evidence_records(), ids=lambda p: str(p.parent.name))
def test_every_digested_artefact_exists_on_disk(record):
    """Tracked-but-absent is the same hole from the other side."""
    missing = [p for p in referenced_paths(record) if not (ROOT / p).exists()]
    assert not missing, f"{len(missing)} attested artefact(s) missing: {missing[:3]}"


def test_the_check_would_fail_if_an_artefact_were_untracked(tmp_path):
    """Could this module fail? Yes. Shown, rather than asserted.

    Builds a record referencing a file that is not in the repository at all and
    confirms the same comparison rejects it -- so the passing cases above are
    passing on merit and not because the comparison is inert.
    """
    fake = tmp_path / "attempt-001"
    (fake / "arrays").mkdir(parents=True)
    (fake / "arrays" / "x.npy").write_bytes(b"0")
    (fake / "threshold_calibration.json").write_text(json.dumps({
        "cells": [{"errors_file": "arrays/x.npy", "run_id": "r",
                   "run_record_digest": "d", "member_record_digest": "d"}]
    }), encoding="utf-8")

    referenced = {
        str((fake / "arrays" / "x.npy")),
        str((fake / "records" / "r" / "run.json")),
        str((fake / "records" / "r" / "metrics.jsonl")),
    }
    assert not (referenced & tracked_files()), (
        "a record outside the repository was treated as tracked"
    )
