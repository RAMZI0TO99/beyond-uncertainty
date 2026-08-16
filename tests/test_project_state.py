"""Invariants on PROJECT_STATE.md itself.

The collaboration protocol was written down, agreed, and then broken twice by
the person who wrote it -- once by overwriting an undelivered delta (the exact
failure D-008 was created to prevent) and once by skipping the delta entirely
for two consecutive sessions. Sol lost three sessions of work from the only
channel it has.

A rule that lives only in prose is a rule that depends on remembering it at the
end of a long session, which is precisely when it will be forgotten. These tests
move the protocol into the suite, so a violation fails like any other defect.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "PROJECT_STATE.md"
DELTA = ROOT / "DELTA_TO_SOL.md"
DECISIONS = ROOT / "DECISIONS.md"
MAX_LINES = 500


@pytest.fixture(scope="module")
def text() -> str:
    # encoding is explicit because these files are UTF-8 and the default is the
    # platform's: on Windows that is CP-1252, and every protocol test errored
    # there while the project's own numbers were reported as passing. A protocol
    # check that only runs on one machine is not a protocol check (D-028).
    return STATE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def delta_block() -> str:
    """Sol's feed lives in its own file (D-023); §8 is now a pointer to it."""
    assert DELTA.exists(), "DELTA_TO_SOL.md is missing -- Sol has no channel"
    return DELTA.read_text(encoding="utf-8")


def test_state_file_stays_pasteable(text: str):
    """The file exists to be pasted into a chat window. Past the cap it stops
    being read, and an unread shared record is worse than none."""
    n = len(text.splitlines())
    assert n <= MAX_LINES, (
        f"{n} lines, cap {MAX_LINES}. Archive closed session-log entries to "
        "PROJECT_STATE_ARCHIVE.md. Never archive decisions, deviations or gate "
        "records -- Sol's instruction."
    )


def _delivered(delta_block: str) -> bool:
    return "Delivered to Sol:** ☑" in delta_block or "Delivered to Sol:** [x]" in delta_block


def test_every_session_is_covered_by_a_delta(text: str, delta_block: str):
    """The failure this suite exists for.

    §8 is the only channel to Sol. A session that produced work but no delta is
    work Sol never learns about, and neither party notices until much later.

    Checks **every** session since the last delivery, not only the newest one
    (D-028). Checking the newest alone would have passed the exact failure that
    prompted these tests: two consecutive sessions wrote no delta, and only the
    second of them would ever have been examined.
    """
    if _delivered(delta_block):
        return  # delivered: the next session legitimately starts a fresh block

    sessions = re.findall(r"^### (20\d\d-\d\d-\d\d[^\n]*?) · Claude\s*$", text, re.M)
    assert sessions, "no session-log entries found"

    covered = [s for s in sessions if s in delta_block]
    assert covered, (
        "the undelivered delta names no session at all. Add the sessions it "
        "covers under COVERS SESSIONS, or tick the delivered box."
    )
    # Everything from the first covered session onward must also be covered:
    # a session appended after the block was opened but never added to it is
    # precisely the silent gap.
    missing = [s for s in sessions[sessions.index(covered[0]):] if s not in delta_block]
    assert not missing, (
        f"{len(missing)} session(s) since the undelivered delta was opened are "
        f"not named in it: {missing}. Either add them to COVERS SESSIONS, or "
        "tick the delivered box if Sol has already had it."
    )


def test_delta_identifiers_are_present_and_ordered(delta_block: str):
    ids = [int(m) for m in re.findall(r"^DELTA_ID:\s*(\d+)", delta_block, re.M)]
    assert ids, "§8 must carry at least one DELTA_ID"
    assert ids == sorted(ids), f"delta ids out of order: {ids}"
    assert len(set(ids)) == len(ids), f"duplicate delta ids: {ids}"
    assert len(re.findall(r"^PREVIOUS_DELTA_ID:", delta_block, re.M)) == len(ids)


def test_delta_chain_has_no_unexplained_gap(delta_block: str):
    """A skipped delta id must be declared, not merely survivable (D-028).

    D-022 claimed skipped ids fail the suite; they did not. ``DELTA_ID: 10``
    following ``PREVIOUS_DELTA_ID: 7`` passed, because the check tested ordering
    and uniqueness only. That gap was legitimate -- delta 10 consolidated three
    sessions whose deltas were lost -- but "legitimate" is exactly the judgement
    a machine check exists to stop being made silently.
    """
    pairs = re.findall(
        r"^DELTA_ID:\s*(\d+)\s*$\n^PREVIOUS_DELTA_ID:\s*(\d+)\s*$",
        delta_block,
        re.M,
    )
    assert pairs, "no DELTA_ID / PREVIOUS_DELTA_ID pair found"

    for current, previous in pairs:
        cur, prev = int(current), int(previous)
        assert cur > prev, f"delta {cur} claims to follow {prev}"
        if cur == prev + 1:
            continue
        skipped = set(range(prev + 1, cur))
        declared = {
            int(n)
            for line in re.findall(
                r"^(?:CONSOLIDATES_DELTA_IDS|LOST_DELTA_IDS):(.*)$", delta_block, re.M
            )
            for n in re.findall(r"\d+", line)
        }
        assert skipped <= declared, (
            f"delta {cur} follows {prev}, so {sorted(skipped - declared)} are "
            "unaccounted for. Add a CONSOLIDATES_DELTA_IDS or LOST_DELTA_IDS "
            "line naming them. A gap that nobody declared is indistinguishable "
            "from a delta Sol never received."
        )


def test_delivery_flag_is_present_and_unambiguous(delta_block: str):
    flags = re.findall(r"\*\*Delivered to Sol:\*\*\s*(☐|☑)", delta_block)
    assert len(flags) == 1, f"expected exactly one delivery flag, found {flags}"


@pytest.fixture(scope="module")
def decisions() -> str:
    assert DECISIONS.exists(), "DECISIONS.md is missing -- the ledger has no home"
    return DECISIONS.read_text(encoding="utf-8")


def test_decision_ids_are_unique_and_contiguous(decisions: str):
    ids = [int(m) for m in re.findall(r"^### D-(\d{3}) ·", decisions, re.M)]
    assert ids, "no decisions found"
    assert len(set(ids)) == len(ids), (
        f"duplicate decision ids: {sorted(i for i in ids if ids.count(i) > 1)}"
    )
    assert set(ids) == set(range(1, max(ids) + 1)), (
        f"gaps in the decision ledger: {sorted(set(range(1, max(ids) + 1)) - set(ids))}"
    )


def test_deviation_ids_are_unique(text: str):
    ids = re.findall(r"^### (DEV-\d{3}) ·", text, re.M)
    assert len(set(ids)) == len(ids), f"duplicate deviation ids: {ids}"


def test_frozen_constants_match_the_code(text: str):
    """§2 is the human-readable copy of src/bu/constants.py.

    Two statements of one preregistered value is how Plan v1.1's withdrawn
    two-sigma rule survived in two sections. If the table and the code disagree,
    one of them is wrong and nobody can tell which.
    """
    from bu import constants as K

    checks = {
        f"**{K.DATA_REPAIR_MULTIPLIER}×**": "data-repair multiplier",
        f"**{int(K.MIN_PRACTICAL_EFFECT * 100)}%**": "minimum practical effect",
        f"**±{K.EQUIVALENCE_MARGIN_PP:.0f} percentage points**": "equivalence margin",
        f"**{K.SEEDS_REPAIR_VALIDATION}**": "repair-validation seeds",
        f"**{K.MIN_LABELLED_UNITS}**": "minimum labelled units",
        f"**{K.CONFIRMATORY_SEED_BASE}**": "confirmatory seed base",
    }
    for needle, what in checks.items():
        assert needle in text, f"§2 does not state the code's {what} ({needle})"


def test_open_questions_have_a_status(text: str):
    rows = re.findall(r"^\| (Q-\d{3}) \|(.*)$", text, re.M)
    assert rows, "no open-questions table found"
    for qid, row in rows:
        assert row.count("|") >= 2, f"{qid} row is malformed"
        assert row.rsplit("|", 2)[-2].strip(), f"{qid} has no status"


def test_state_points_at_the_delta_file(text: str):
    """§8 must not drift back into holding content of its own."""
    assert "DELTA_TO_SOL.md" in text


def test_delta_file_is_pasteable(delta_block: str):
    n = len(delta_block.splitlines())
    assert n <= 400, f"{n} lines; split or deliver before it stops being read"


def test_every_decision_is_indexed_in_the_state_file(text: str, decisions: str):
    """The ledger split (D-037) must not let a decision fall out of view.

    §3 keeps a one-line index precisely so relocating the records is not
    archiving them. A record filed into DECISIONS.md but absent from the index
    would be invisible to anyone reading the pasted state file -- which is the
    failure the split was supposed to avoid, arriving by another route.
    """
    filed = set(re.findall(r"^### (D-\d{3}) ·", decisions, re.M))
    indexed = set(re.findall(r"\*\*(D-\d{3})\*\*", text))
    assert filed == indexed, {
        "filed but not indexed": sorted(filed - indexed),
        "indexed but not filed": sorted(indexed - filed),
    }


def test_the_state_file_points_at_the_ledger(text: str):
    assert "DECISIONS.md" in text
