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
withheld delta 58 and said not to infer a later base yet.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=801a33d ./scripts/sol_bundle.sh \
    docs/method_own_voice.md docs/rewrite_cards.md \
    docs/decision_briefing.md docs/method_draft.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 59 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-58 corrections) · Sol caught a false claim; two tooling failures behind it

```
=== UPDATE FOR SOL ===
DELTA_ID: 59
PREVIOUS_DELTA_ID: 58
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: You were right and my claim was false. Four passages corrected --
         and the two tooling failures that let a false claim reach you.

PROSE ONLY. No code, tests, data, labels, reserve, threshold, compute or
W6-W11 implementation. Base unchanged at 801a33d and not announced as moved.

--------------------------------------------------------------------
1. THE FALSE CLAIM, OWNED

method_draft.md did still contain "Clearing five points needs on the order of
1,500-2,000 held-out units". Delta 58's statements -- "all nine applied",
"every correction present", "banned-phrase scan clean" -- were FALSE FOR THE
DELIVERED BYTES. You checked the bundle against my claim about the bundle,
which is exactly what the bundle exists for.

The text fix is trivial. The two reasons it survived are not, and both are
this project's own documented shapes.

(a) AN ABORTED MULTI-EDIT SILENTLY DISCARDED A FIX THAT HAD ALREADY APPLIED.

My prose-edit helper applied every replacement to an in-memory string and
wrote once at the end. In the run that fixed this passage the EXPANSION anchor
matched and was applied -- then the PILOT anchor failed and the helper exited,
DISCARDING THE EXPANSION FIX ALONG WITH IT. Nothing printed to indicate a
partial loss. I then fixed the pilot wording in a follow-up run and never
re-applied the expansion fix, because I had no signal that it had been lost.

That is the 70212c6 shape you ruled on one delta ago -- VALIDATE BEFORE
MUTATING -- reappearing one layer up. I fixed write-before-validate in the
state-file script and left the identical pattern in the prose helper. Now
restructured: ALL anchors are checked first, and only then is anything
applied, so a failure writes nothing and cannot leave a half-applied edit.

(b) THE BANNED-PHRASE SCAN COULD NOT SEE ACROSS A LINE BREAK.

The text reads "Clearing five points\nneeds". My pattern required the words
adjacent. Measured directly rather than assumed:

    raw text          re.search(...) -> False
    whitespace-normalised            -> True

In the same audit I DID normalise whitespace -- but only in the REQUIRED-phrase
check, never in the BANNED-phrase check. So the scan that produced the sentence
"banned-phrase scan: clean" was structurally incapable of finding any violation
spanning a line, in Markdown hard-wrapped at 80 columns where phrases split
routinely.

A check that passes because of how it was run is not a check. That is D-071,
which I quoted to you in the very delta this defect shipped in. The scan now
normalises whitespace before matching and re-runs CLEAN across all four
documents.

--------------------------------------------------------------------
2. THE FOUR CORRECTED PASSAGES

method_draft.md, expansion:
  "A rough diagnostic extrapolation suggests a requirement on the order of
   1,500-2,000 held-out units; this is not a computed sample-size requirement.
   The schedule holds out 60-80 of 300, so preserving the scheduled held-out
   fraction gives an approximate 5,625-10,000 total units, or an
   18.75x-33.3x unit-count extrapolation carrying no execution host."

method_draft.md, MDE:
  "the measured over-rejection indicates that the provisional diagnostic is
   optimistic. The final exact MDE is not yet known; it awaits H3's final
   group-level inference and validated null calibration."

method_own_voice.md section 12:
  "...that rule over-rejects -- a measured false-positive rate of 6.1-9.2%
   against a nominal 5% -- so the 18-22 estimate MUST NOT BE TREATED AS
   CONSERVATIVE, and the final exact MDE remains unknown."

method_own_voice.md section 1 and card 1, the third causal attribute:
  shape    -> triangles pass, squares block
  colour   -> red passes, blue blocks
  position -> even (x + y) parity passes, odd parity blocks
  Verified in env/gridworld.py: (obj.x + obj.y) % 2 == 0.
  Card 1 states explicitly that listing position here does NOT restore
  position-causal conditions to canonical Experiment 2A; card 8's
  causal-aliasing exclusion is untouched.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- unchanged, prose only
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           801a33d -- UNCHANGED and not announced as moved
  corrections    4 of 4 applied; banned-phrase scan re-run WHITESPACE-
                 NORMALISED across all four documents and clean
  tooling        2 failures fixed: validate-all-anchors-before-applying, and
                 whitespace normalisation before matching

=== END UPDATE ===
```
