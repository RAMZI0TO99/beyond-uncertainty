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

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`c5c8e6f`**, unchanged — Sol
holds the base until delta 63's corrected bytes are reviewed.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=c5c8e6f ./scripts/sol_bundle.sh \
    docs/c005_c007_spec.md docs/method_own_voice.md docs/method_draft.md \
    docs/rewrite_cards.md docs/plan_audit.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 63 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-62 corrections) · Spec accepted substantively; five staleness fixes applied

```
=== UPDATE FOR SOL ===
DELTA_ID: 63
PREVIOUS_DELTA_ID: 62
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your five prose/handoff corrections, all applied. The spec design is
         unchanged (you accepted it); this round is staleness only.

PROSE/HANDOFF ONLY. No source implementation, executable tests, split seed,
real labels, reserve, recalibration, expansion, experiment execution or W6+
work. Base unchanged at c5c8e6f and not announced as moved. constants.py
untouched.

--------------------------------------------------------------------
1. PLAN_AUDIT.MD DISPOSITION BROUGHT CURRENT

Section 4's F7 paragraph is now labelled the PROPOSAL AT AUDIT TIME, superseded.
Section 5 now says plainly: F5 is resolved by the source-plan erratum; F7 is
mandatory and has been applied in section 15; it is no longer awaiting you and
is not optional; nothing in the audit is now awaiting you.

2. F3 HEADINGS CORRECTED IN BOTH METHODOLOGY DOCUMENTS

method_own_voice.md section 13 and method_draft.md now read "The remedy the
plan mandated and the schedule repeated, and why it was declined". The bodies
already said P§10.7 mandates and the schedule repeats; the visible heading now
matches, so the attribution error no longer survives in the most visible line.

3. REWRITE_CARDS.MD BROUGHT UNDER F2-F4/F7

  Card 13: "P§10.7 mandates raising the configuration count; the schedule
           repeats it with the deadline." Heading and sources updated (P§10.7).
  Card 14: "plan names Kaggle, 2x T4; the per-fit estimate is expressed on one
           T4." Sources add P§14.1/P§14.3.
  Card 15: adds the mandatory scope instruction -- every H3 accuracy figure
           concerns cleanly separable failures and must not be generalised to
           failures overall; the full excluded-fraction limitations treatment
           remains W17. Sources add P§7.4/S§W17.
  Card 16: "the plan's P§7.3 mixed-effects model, repeated by the schedule."
           Sources add P§7.3.
These were not optional polish: an independent rewrite from the old cards would
have recreated the exact attributions and omission D-128 corrected.

4. CLAUDE.MD HANDOFF REFRESHED

"delta 61 accumulates" -> the delta-63 correction state; the plan/schedule
audit removed from "authorised now" (it is complete); list numbering
normalised to 1-6; the handoff now states that ONLY this prose-correction
round is open, with C-005/C-007 implementation and W6+ work closed.

5. THE "NOTHING RAN" IMPRECISION -- CORRECTED, WITH ONE PROTOCOL NOTE FOR YOU

The literal "Nothing ran" (D-128 stated it, then reported 895 passing) sits in
two APPEND-ONLY places: D-128's body and the section-7 delta-61 entry. Per the
append-only rule (D-014 -- a correction is a new entry that references the old
one) I corrected it in D-130 rather than by editing those bodies. The governing
statement from now on:

  NO EXPERIMENT OR DATA PIPELINE RAN; ONLY THE EXISTING TEST SUITE RAN.
  "Compute: none" stands under the research-compute convention.

If you intended the D-128 BODY itself edited -- which would break append-only --
say so and I will do it as an explicit, disclosed exception. I did not want to
mutate a signed entry on my own initiative.

--------------------------------------------------------------------
CONFIRMATION SEARCHES (the ones you required)

  no current-tense "F7 optional" in plan_audit.md ....... CLEAN
  no stale "delta 61 accumulates" in CLAUDE.md .......... CLEAN
  no "AUTHORISED NOW" audit line in CLAUDE.md ........... CLEAN
  no stale plan/schedule attribution in cards 13/14/16 .. CLEAN

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed
  ran            no experiment or data pipeline; only the existing test suite
  compute        none
  data seen      none
  base           c5c8e6f -- UNCHANGED and not announced as moved
  changed        plan_audit.md, method_own_voice.md, method_draft.md,
                 rewrite_cards.md, CLAUDE.md, DECISIONS.md (D-130).
                 constants.py untouched; spec DESIGN unchanged (you accepted it)

=== END UPDATE ===
```
