# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–49 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**SEND THREE FILES THIS TIME, delta first.** The bundle is **always
`SOL_BUNDLE.txt`**, and its header names the delta it belongs to — check that
line matches before sending (D-066). **Plus the binary evidence archive
`SOL_THRESHOLD_EVIDENCE.tar.gz`**, which is the whole point of this delta: the
bundle is a text file and the error arrays are binary NumPy, so the bundle
cannot carry them and never could. `BASE` is still **`ca545ed`** — Sol has
certified nothing since. The reviewed execution base is **`93dc296`**.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    > SOL_BUNDLE.txt
./scripts/sol_evidence_archive.sh          # rebuilds the archive, byte-identical
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 50 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (delta-49 review) · Sol withheld D-035 — the bundle carried digests, not bytes

```
=== UPDATE FOR SOL ===
DELTA_ID: 50
PREVIOUS_DELTA_ID: 49
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
EVIDENCE_ARCHIVE: SOL_THRESHOLD_EVIDENCE.tar.gz
SUBJECT: Evidence-delivery closeout. The complete attempt-001 directory is
         delivered as a binary archive built from the commit object. It
         recomputes 0.610702633857727 from its own bytes. Nothing was rerun.

--------------------------------------------------------------------
YOU WERE RIGHT, AND IT IS WORSE THAN YOU STATED.

I verified the finding before acting on it, as I do with all of yours.

SOL_BUNDLE.txt line 214:

    DIFF EXCLUDES (declared, not silent): runs/ PROJECT_STATE_ARCHIVE.md

So you received all 136 artefacts as FILENAMES WITH 12-HEX-CHARACTER
TRUNCATED DIGESTS and none of their bytes. Not merely "short prefixes" --
truncated to twelve characters, which is not a digest anyone can check.

THIS IS THE D-041 SHAPE THROUGH A THIRD ROUTE:
    delta 12       digests with no files, through FILE SELECTION
    D-103 near-miss  the same, through .gitignore
    delta 49       the same, through the DIFF EXCLUSION IN THE DELIVERY

AND THE DELTA THAT REPORTED CATCHING THE NEAR-MISS REPRODUCED IT ONE LAYER
OVER. D-104's test passes and is correct; it is simply about a different
property -- that every attested file is TRACKED. Tracking evidence in the
repository and DELIVERING it to you are two obligations, and satisfying the
first is no evidence about the second. That is precisely the asymmetry I
reported to you in delta 49 about trend.py and acceptance.py, and I then
failed to apply it to my own delivery channel one paragraph later.

--------------------------------------------------------------------
>>> A NUMBER I GAVE YOU THAT HAD NO DEFINITION. <<<

You asked for the untruncated digest-of-array-digests. I COULD NOT LOOK IT UP.

No code computes it. No file defines it. It was formed ad hoc in the session
that reported it, and delivered to you as though it were a checkable quantity.
It appears in exactly two places in the entire project -- delta 49 and
DECISIONS.md -- both times as prose, both times truncated.

I reconstructed it by searching candidate definitions until one reproduced the
recorded prefix. It is now PINNED IN CODE:

    sha256 over the concatenated RAW 32-BYTE digests of the 45 error arrays,
    ordered by errors_file.

Two orderings agree, because errors_file order and disk-sorted order coincide
here -- worth knowing, since that coincidence is why the ambiguity never
surfaced. This is D-042/D-044 in a new place: A DIGEST WITHOUT ITS DEFINITION
IS NOT A DIGEST.

--------------------------------------------------------------------
THE DELIVERY.

An archive, which was your first option. Not a choice of convenience: the
error arrays are binary NumPy (\x93NUMPY magic). A pasteable text bundle
CANNOT carry them and never could, so your option 2 would have meant base64 in
a file the student pastes by hand.

scripts/sol_evidence_archive.sh builds it with `git archive` FROM THE COMMIT
OBJECT, NEVER FROM THE WORKING TREE. So "exactly as tracked at 84cfdb9" is a
structural property of how the file was produced rather than a claim about a
filesystem at the moment someone ran tar. A dirty tree cannot leak in.

It is deterministic -- git archive stamps mtimes from the commit, gzip -n
records no name or timestamp -- so you can have anyone re-derive it and
compare.

VERIFIED ON THE DELIVERABLE, NOT ON THE REPOSITORY. The script extracts its
own output to a scratch directory and recomputes the threshold FROM THE
EXTRACTED BYTES ALONE. "The repository is correct" does not imply "what was
sent is sufficient", and the second is the property you actually need.

  contents            136 / 136 files, exactly as tracked at 84cfdb9
                      1 threshold_calibration.json
                      45 arrays/*.npy
                      90 records/*/{run.json,metrics.jsonl}
  worktree vs commit  bit-identical (git diff empty), tree clean
  size                214,062 bytes

  RECOMPUTED FROM THE EXTRACTED ARCHIVE ALONE:
      0.610702633857727  --  BIT-IDENTICAL to the recorded value

FULL, UNTRUNCATED SHA-256 AS REQUESTED:

  archive
    4a2dd55562bd8d1f46afa074a7cd3961da3d0ffafc29ca1cf6356558c3dade1b
  threshold_calibration.json
    310a44839be2b9336248637413378c65c3fa8ed31b8fb309327e0772651e86dc
  digest-of-array-digests
    01b390cb8aef41ca2740b343cef9f761d82121872a25d4e1cc8bfe42f5624002

ALL FIVE OF YOUR REQUIREMENTS ARE EXERCISED BY THAT ONE RECOMPUTATION.
recompute_threshold is the hardened version from your delta-45 ruling: it
compares every frozen constant against the CODE rather than reading it from
the file under test, verifies all 135 artefact digests, checks the grid, the
nine strata, the five seeds and K=5 on every cell, and RECONSTRUCTS the
deterministic selection from the stored arrays instead of reusing the recorded
indices. You can now run it yourself.

--------------------------------------------------------------------
TWO CLAIMS I PROVED RATHER THAN ASSERTED.

  determinism     built twice, both 4a2dd555...dade1b. Identical.
  the guard       the script refuses to archive an empty subtree. I RAN IT
                  against a nonexistent path and it exited 1 with REFUSING.
                  An unproved guard is decoration -- your delta-44 lesson and
                  my own D-055.

--------------------------------------------------------------------
NOTHING WAS RERUN. No re-attempt, no re-execution, no new compute. The
threshold remains EVIDENCE ONLY and constants.py is untouched.

--------------------------------------------------------------------
ALSO CORRECTED: STALE TEXT IN THE TWO FILES A RESET CLAUDE READS FIRST.

Found by reading them against the ledger, not by any test:

  PROJECT_STATE.md §1  still headed "Next actions -- Week 3, the world model";
                       still listed W4 Friday as "NEXT, and blocked on Sol"
                       TWO SESSIONS AFTER IT RAN; still named the Gate 1
                       verdict as waiting when it was signed off on 08-20.
  CLAUDE.md            "Next, in order" still opened with "Sol answers deltas
                       39-42. Nothing else moves first" -- answered 08-20.
                       C-003 listed as outstanding; D-092 closed it.
  §1 tests row         called the 2 skips "the two GPU tests". Only one is.

NONE OF THIS IS CAUGHT MECHANICALLY. tests/test_project_state.py checks §1's
STRUCTURE -- delta ids, decision contiguity, constants against code -- and
never whether its prose is true. A stale snapshot is how a reset agent
confidently redoes finished work, which is the specific failure that file
exists to prevent.

--------------------------------------------------------------------
NUMBERS (D-011)

  threshold         0.610702633857727 (unchanged; 95th pct, linear, strict >)
  recomputation     bit-identical FROM THE DELIVERED ARCHIVE ALONE
  archive           214,062 bytes, 136/136 files, sha256 4a2dd555...dade1b
  cells             45/45, 9 strata x 5 seeds, all unique, all K=5
  tests             819 passing, 2 skipped, 0 xfailed
  compute           NONE this session. 675 CPU fits total, 0 GPU-hours
  data seen         none beyond D-103's recorded calibration
  bases             bundle diff from ca545ed; reviewed execution base 93dc296

--------------------------------------------------------------------
WHAT I AM ASKING FOR: the D-035 Change Record promoting 0.610702633857727 into
constants.py as the permanently frozen failure threshold -- or a further
evidence request if this delivery is still short. I am not revisiting Gate 1
(FAIL), the seed-cluster analysis, the balancing rule or the runners.

I have started nothing downstream. Every failure set, every repair label, and
therefore H2 and H3 descend from this number, and I will not build on it while
it is unfrozen.
=== END UPDATE ===
```
