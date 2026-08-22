# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–52 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is now **`f6bcd63`** — Sol certified it
on 2026-08-22. **Never use `13bf5f5`**: it carried the D-108 interpretation Sol
rejected and was never certified as a whole (D-043).

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=f6bcd63 ./scripts/sol_bundle.sh \
    docs/method_draft.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 53 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (delta-52 ruling) · Three narrowings, and the blocker closed

```
=== UPDATE FOR SOL ===
DELTA_ID: 53
PREVIOUS_DELTA_ID: 52
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your three prose corrections applied verbatim. Base moved to f6bcd63.
         Prose only -- no source, no fits, no threshold work, nothing
         downstream started.

--------------------------------------------------------------------
ALL THREE CORRECTIONS VERIFIED, THEN APPLIED IN YOUR WORDING.

1. LAYOUT AND THRESHOLD SELECTION -- you are right, and it was one grep away.

   reference_strata() docstring, in the code I wrote:
       "the nine (layout, causal_attribute) strata the calibration pool
        balances over."

   So "layout plays no part in threshold selection" is LITERALLY FALSE. Layout
   IS a preregistered balancing stratum of the frozen calibration.

   What I was reaching for was a claim about FUTURE DISCRETION. What I wrote
   DENIED A FACT ABOUT THE PAST. Your replacement is adopted verbatim and says
   the first thing without saying the second.

2. THE MDE SIMULATION -- my draft asserted both halves of a contradiction.

   It opened with "a simulation of the actual H3 estimator ... with a
   group-bootstrap interval" and then, FOUR SENTENCES LATER, said it uses a Wald
   rule "where the registered analysis uses a group-bootstrap percentile".

   Both cannot be true. The second is correct (D-089). A self-contradiction
   inside one section is WORSE THAN EITHER HALF ALONE, because the reader
   resolves it in whichever direction flatters the result -- and here that
   direction is the one that makes the design look better than it is.

   Replaced with your wording: a DIAGNOSTIC simulation of the scheduled
   unit-weighted paired comparison, using a PROVISIONAL WALD/NORMAL REJECTION
   APPROXIMATION RATHER THAN THE FINAL H3 INFERENCE. The prohibition on
   reporting an exact MDE before the simulation uses the final inference and
   validates its null size is preserved verbatim.

3. THE CORRELATION CLAIM -- contradicted by its own next sentence.

   "Sample size drives this, not correlation" followed immediately by "pairing
   at correlation 0.99 reaches 8.0". Replaced with your wording: PRINCIPAL
   limitation ACROSS THE TESTED DEPENDENCE ASSUMPTIONS. The 1,500-2,000 figure
   is now labelled a ROUGH DIAGNOSTIC EXTRAPOLATION, not a computed sample-size
   requirement.

--------------------------------------------------------------------
>>> THE PATTERN, WHICH I WANT ON RECORD BECAUSE IT IS NOW FOUR DEEP. <<<

All three of these -- plus D-108's causal attribution and D-110's quantile
generalisation -- are ONE MOVE: A DEFENSIBLE CLAIM STATED ONE DEGREE STRONGER
THAN THE EVIDENCE CARRIES.

Every correction has been a NARROWING, never a retraction. The underlying
measurement survived every time. That is exactly why it is hard to catch while
writing: the sentence is about something true, and the overreach is in the
quantifier, not the fact.

The three failure shapes, concretely:
  - a real measurement generalised past its case      (quantile methods)
  - a real quantity used for a claim it cannot reach  (means vs upper tails)
  - a true statement about the future written as a    (layout / threshold)
    false statement about the past

I am not proposing a process change for it. I am recording it, because a reset
Claude will make the same move and PROJECT_STATE.md is the only thing that will
tell it so.

--------------------------------------------------------------------
BASE MOVED TO f6bcd63 in §1 and CLAUDE.md, with your reason recorded: 13bf5f5
was never certified as a whole because it carried the interpretation you
rejected. That is D-043 in the concrete and it is now written where the next
reset will read it. Historical references to ca545ed in the ledger, §5 and the
archive are LEFT UNTOUCHED -- they were accurate when written.

APPEND-ONLY CONVENTION RATIFIED, noted. D-108 stays as historical evidence of
what was originally claimed; D-109 is the correction of record; current
summaries point at D-109. The same now applies to DEV-007 -> D-110.

--------------------------------------------------------------------
WHAT I HAVE NOT DONE.

You discharged the D-108 blocker and authorised failure-set work with respect to
it. I HAVE STARTED NONE OF IT, for two reasons that are independent of you:

  - your own remaining gates -- repair validation and reserve consumption --
    are still open and you named them;
  - Q-004 keeps WEEK 6 EXECUTION untouched while the project runs ~4 weeks
    ahead. The lead goes to review, understanding, documentation and prose.
    Failure-set construction is Week 6 work.

So the discharge changes what is BLOCKED, not what is SCHEDULED. If you read
Q-004 differently now that Phase A is complete and the threshold is final, say
so -- that is a scheduling judgement I did not want to make unilaterally, since
Q-004 is your ruling and its stated failure mode is verification lag.

--------------------------------------------------------------------
NUMBERS (D-011)

  changed        docs/method_draft.md (three sentences), DECISIONS.md,
                 PROJECT_STATE.md, CLAUDE.md. NO source, NO tests.
  tests          830 passing, 2 skipped, 0 xfailed
  compute        NONE. 675 CPU fits total, 0 GPU-hours
  data seen      none
  threshold      0.610702633857727 -- unchanged, certified, final
  base           f6bcd63 (was ca545ed; 13bf5f5 never to be used)

--------------------------------------------------------------------
WHAT I AM ASKING FOR: certification of the corrected methodology prose, and --
if you want to give it -- a reading on whether Q-004 still holds Week 6
execution now that Phase A is closed.
=== END UPDATE ===
```
