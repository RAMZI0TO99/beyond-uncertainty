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
> - 2026-08-22 (methodology closeout) · The last mandated section
> - 2026-08-22 (schedule check) · Weeks 4 and 5 are not complete

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

--------------------------------------------------------------------
--------------------------------------------------------------------
APPENDED (D-008: still undelivered). THE LAST MANDATED SECTION (D-112).

§4 lists five things the schedule REQUIRES in the methodology. Four are now
drafted. The fifth -- the W2 decision on whether the Experiment 2A conditions
are drawn from the configuration sweep or are ADDITIONAL to it (D-007, closing
your Q-003) -- had no prose at all. It does now.

THE ARITHMETIC WAS CHECKED IN CODE, NOT QUOTED FROM THE LEDGER:

  canonical_units()        75      of which experiment_2a_units() = 20
  sweep_candidates()       full matrix MINUS the canonical ids, so the 225
                           sweep draws cannot collide with them
  design_units()           300, with 300 DISTINCT unit_ids, canonical a subset
  naive double count       375 against a registered 300

375-vs-300 is the concrete size of the inflation D-007 exists to prevent, and
every confidence interval computed on that count would be too narrow. The
section says so, and says why seed count is a property of a unit's ROLE rather
than of a run list -- the same distinction D-033 records as having cost 375
phantom fits when it was got wrong in the other direction.

THE REMAINING TWO ITEMS ON §4's LIST -- a repair-budget or configuration-count
reduction, and a cut experiment -- HAVE NOT HAPPENED. Nothing to write, and I am
not writing placeholder prose for events that may never occur.

So §4's mandate is discharged as far as events allow. Prose stays scaffolding
for the student to rewrite (D-019).

  tests     830 passing, 2 skipped, 0 xfailed
  compute   NONE. 675 CPU fits total, 0 GPU-hours
  changed   docs/method_draft.md, DECISIONS.md, PROJECT_STATE.md. No source.

--------------------------------------------------------------------
--------------------------------------------------------------------
APPENDED (D-008: still undelivered).

>>> WEEKS 4 AND 5 ARE NOT COMPLETE. §1 HAS BEEN WRONG FOR SESSIONS. <<<

I checked "Weeks 1-5 are complete" against the SCHEDULE DOCUMENT instead of
against the ledger's memory of it. Three things are outstanding and one sits
under a condition you have already signed (D-113).

1. W4 FRIDAY IS HALF DONE, AND THE MISSING HALF IS A GATE 1 CONDITION.

   S§W4 Fri has TWO tasks. The threshold calibration -- done, certified. And:

       "Timing harness: measure one full condition end to end and extrapolate
        total GPU-hours against the ~120-hour estimate."

   NO TIMING HARNESS EXISTS. The only artefact is the constant
   COMPUTE_ESCALATION_TRIGGER_GPU_HOURS = 120.

   GATE 1 CONDITION 2 WAS SIGNED **PASS** ANYWAY, on this basis (§5):
       "At the old default the design cost 14,885 fits against ~8,700, 1.71x."

   THAT IS A FIT COUNT, NOT GPU-HOURS. The conversion between them is precisely
   what the harness was specified to measure. ZERO GPU-HOURS HAVE EVER BEEN
   SPENT -- every fit to date is CPU. The schedule is unusually blunt that this
   is not a formality: budget 110-145 GPU-h against a ~120 trigger, and "the
   Week 4 timing harness is a gate, not a formality -- as specified, the design
   sits at the edge of the budget with no meaningful headroom."

   A CUDA device IS present (RTX 4080 SUPER), so the measurement is available.
   It has simply never been taken. A COMPUTE CONDITION PASSED ON A PROXY FOR THE
   QUANTITY IT NAMES.

2. W5 FRIDAY IS HALF DONE. The figure script exists. The other task --

       "fix the class-balance procedure in code at the labelled-unit level:
        equal numbers of labelled configuration-conditions per class within each
        split, then a fixed cap of traces drawn per selected unit"

   -- HAS NO IMPLEMENTATION. The only `balance` in src/bu is _balanced_accuracy
   in mde.py, which is the METRIC, not the sampling procedure. D-031 and D-092
   cover INTENDED-class balance and the reserve draw order: related, but this is
   balance at the LABELLED-unit level, WITHIN EACH SPLIT, plus a trace cap.
   S§W11 Mon explicitly assumes it exists -- "using the Week 5 procedure".

3. A DEVIATION THAT WAS NEVER WRITTEN, now DEV-009. S§W5 Tue specifies a
   statsmodels MIXEDLM with random intercepts for seed and episode-within-seed
   AND an episode-mean fallback. What we run is an equal-seed mean paired
   difference with a t interval and NO fallback (D-094, D-100). You authorised
   it before data was seen and it is in §2 and the ledger -- but NOT in §4, and
   "mixed-effects" appeared ZERO times in PROJECT_STATE.md. A registered
   analysis method replaced by a different one, absent from the deviation log,
   is the silent override the rule forbids.

--------------------------------------------------------------------
WHY THIS STAYED INVISIBLE, WHICH I THINK MATTERS MORE THAN THE ITEMS.

Every one of these sits BESIDE something done well and reported at length. The
threshold calibration is the most heavily reviewed artefact in this project and
it SHARES A CELL with the harness nobody built. The acceptance change went
through four of your review rounds and two Change Records, and none of them --
mine or yours -- asked where its deviation record was.

THE LEDGER TRACKS DECISIONS. IT DOES NOT TRACK CELLS. Nothing in the protocol
suite checks schedule coverage, and §1's "Weeks 1-5 are complete" was true of
the INTENT and was carried forward unverified for many sessions. That is a
different failure from the ones you have been catching in me: not an overstated
claim, but an UNCHECKED one.

--------------------------------------------------------------------
WHAT I DID AND DID NOT DO.

DEV-009 is WRITTEN -- a missing deviation record is a recording obligation and
mine to discharge.

I did NOT build or run the timing harness. It would RE-OPEN A SIGNED GATE 1
CONDITION, which is yours to reopen, and it would be this project's first GPU
compute.

I did NOT build the class-balance procedure. It sits inside the
RESERVE-CONSUMPTION area you still have gated.

ASKING: how you want both handled, and whether Gate 1's compute condition should
be re-assessed against a measured extrapolation rather than a fit count.
=== END UPDATE ===
```
