# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite.

**Where the delivered deltas actually are** (corrected 2026-08-23, D-120 — the
line here previously claimed 10–54 were archived and they were not): deltas
**1–7 and 10–33** are in `PROJECT_STATE_ARCHIVE.md`; **8 and 9** never existed
as delivered blocks (DEV-005); **34–55** were replaced without being archived
and live only in **git history**, each at the commit that delivered it
(`git log -S "DELTA_ID: NN" -- DELTA_TO_SOL.md`); **56 onward** are archived on
replacement, as the convention always intended.

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`c5c8e6f`** — Sol certified
delta 60 on 2026-08-23 and named this exact commit. **Do not infer a later one.**

**Sol requires no further closeout for delta 60.** Delta 61 accumulates until
there is genuinely authorised work to report — currently the **plan/schedule
`.docx` audit**, which is read-only and prose-only.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=c5c8e6f ./scripts/sol_bundle.sh \
    <files changed by the next authorised work> > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 61 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-60 certification) · The prose closeout is CERTIFIED; base → `c5c8e6f`; the plan audit opens

```
=== UPDATE FOR SOL ===
DELTA_ID: 61
PREVIOUS_DELTA_ID: 60
DATE: 2026-08-23
BUNDLE_FILE: none yet -- accumulating; no closeout is required for delta 60
SUBJECT: Your delta-60 certification, filed as D-125. Base set to c5c8e6f.
         Nothing built.

Digests verified before filing, per the standing rule: your quoted bundle
sha256 76e531c6...6723a15 matches the delivered file byte-for-byte, the delta
digest e67c698c43f8 matches the bundle header, and your reviewed head is HEAD.

RECORDED EXACTLY AS YOU RULED:
  certified base   c5c8e6fd35c0ea7da17adb9fca1f4fb674c62e0b, BASE=c5c8e6f,
                   no later commit inferred
  closeout         D-121 ... D-124 certified as a cumulative prose closeout
  roles            method_own_voice.md  = student-confirmed ASSISTED draft,
                                          NOT final independently authored
                                          thesis prose
                   method_draft.md      = scaffolding, not final student prose
                   decision_briefing.md = reader-facing consolidation,
                                          SUBORDINATE to the ledger
                   rewrite_cards.md     = checked rewrite guidance
  standing         before anything enters the thesis the student performs the
                   independent rewrite pass, removes the interview/provenance
                   apparatus, and retains only wording they can personally
                   explain and defend
  unchanged        W4/W5 complete; Gate 1 FAIL on the MDE; condition 2 NOT
                   ADJUDICABLE, never PASS; Q-012 closed; no C-005/C-007, no
                   W6-W11 code, no executable tests, no real data, no labels,
                   no reserve, no threshold change, no expansion, no compute

>>> ONE DISCLOSURE, REPORTED RATHER THAN QUIETLY FIXED

Commit 7b19d2b's message claimed the new base was updated in CLAUDE.md. It was
not. The CLAUDE.md edit script aborted on a TypeError and wrote nothing, while
the commit -- a separate command, not a chain -- ran regardless. CLAUDE.md
continued to name 801a33d in three places, including the bundle command a
future session would copy. Fixed and verified in 4007d65: zero occurrences of
801a33d remain.

That is the THIRD variant of one failure this session: pytest piped into tail
masking a test failure (70212c6); a multi-edit discarding an already-applied
fix when a later anchor failed (D-123); and now an aborted edit followed by an
unconditional commit. Each time a guard existed and each time the SEQUENCING
let the outcome through. The rule I am adopting: an edit and its commit must
share a fate -- if the edit does not complete, the commit does not happen.

I am not asking you to re-review the certified bytes; c5c8e6f is unaffected,
since CLAUDE.md is operational handoff and not part of the certified prose set.

NEXT: the plan/schedule .docx audit, under D-120's allocation, read-only and
prose-only -- comparing the certified methodology against the source plan and
schedule, recording contradictions and proposing prose corrections, NOT
beginning later-week implementation. It has not been started; this delta will
carry its findings when it has.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- unchanged
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           c5c8e6f (moved from 801a33d on your certification)
  built          nothing

=== END UPDATE ===
```
