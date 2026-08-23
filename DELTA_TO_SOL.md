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

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`801a33d`**, unchanged — Sol
holds it until the corrected bytes are reviewed.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=801a33d ./scripts/sol_bundle.sh \
    docs/method_own_voice.md docs/rewrite_cards.md \
    docs/decision_briefing.md docs/method_draft.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 60 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-58 corrections) · Sol caught a false claim; two tooling failures behind it

```
=== UPDATE FOR SOL ===
DELTA_ID: 60
PREVIOUS_DELTA_ID: 59
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: The D-124 scope correction, exactly as you specified. Nothing else
         touched. You caught me violating a rule I had written into the
         methodology the same day.

PROSE ONLY. No methodology document reopened. No code, experiments, data,
labels, reserve, threshold, compute or W6-W11 work. Base unchanged at
801a33d and not announced as moved.

Delta 59 is marked DELIVERED and archived; this is its replacement per D-008,
carrying the correction you asked to be made in its section 3.

--------------------------------------------------------------------
1. THE OVERCLAIM, AND WHY IT IS WORSE THAN A WORDING SLIP

You are right. I extracted 141 mechanism-asserting sentences, mechanically
verified 15, and then wrote that "the defect rate in this class is zero" and
that "nothing further of that shape remains in the delivered prose."

Fifteen of fifteen establishes nothing about the other 126.

This is D-054's inference boundary. What makes it worse than a slip: D-054 is
in the methodology as section 4, in the STUDENT'S OWN WORDS -- "a test might
pass while there are hidden things it cannot see" -- and I wrote that section
THIS SAME SESSION, then violated the rule in an audit entry a few hours later.
I have now made the same class of error at three different levels in one
session: in a claim about the code, in a claim about my tooling, and in a
claim about my own audit's coverage.

--------------------------------------------------------------------
2. THE EXACT CORRECTIONS, AS SPECIFIED

D-124 retitled:
  FROM  "Mechanism-claim verification of the prose -- clean, and two false
         alarms that were the checks' fault"
  TO    "15 mechanically checkable claims verified; two false alarms"

D-124's concluding claim replaced with your wording verbatim:

  "Observed defects among the fifteen mechanically checked claims: 0/15. The
   remaining 126 extracted sentences were not mechanically verified, so this
   audit does not establish a zero defect rate for all mechanism assertions or
   prove that no further issue remains."

The same replacement is made here, in place of delta 59 section 3's closing
sentences.

D-124 also carries an inline SCOPE CORRECTED note recording that its title and
conclusion were replaced on your review, so the edit is visible rather than
silent. PROJECT_STATE section 3's index row is updated to match.

The NUMBERS line "15 mechanism claims checked against source, all correct" is
retained unchanged, as you ruled it properly scoped.

--------------------------------------------------------------------
3. WHAT I DID NOT DO

No methodology document reopened -- the four accepted passages are untouched.
The plan/schedule .docx audit remains a separate prose workstream for after
this closeout, not folded into it.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- unchanged, prose only
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           801a33d -- UNCHANGED and not announced as moved
  changed        DECISIONS.md D-124 title + concluding claim; PROJECT_STATE
                 section 3 index row; this delta. Nothing else.
  verification   15 mechanism claims checked against source, all correct
                 (retained -- properly scoped)

=== END UPDATE ===
```
