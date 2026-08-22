# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–52 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`f6bcd63`**, certified 2026-08-22.
**Never use `13bf5f5`** — it carried the D-108 interpretation Sol rejected and
was never certified as a whole (D-043).

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=f6bcd63 ./scripts/sol_bundle.sh \
    src/bu/experiments/w4_timing.py tests/test_w4_timing.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 53 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (delta-52 ruling) · Three narrowings, and the blocker closed
> - 2026-08-22 (methodology closeout) · The last mandated section
> - 2026-08-22 (schedule check) · Weeks 4 and 5 are not complete
> - 2026-08-22 (W4 Fri, part two) · The timing harness, eight sessions late
> - 2026-08-22 (W4 closeout) · Week 4 is complete, and a departure nobody logged

```
=== UPDATE FOR SOL ===
DELTA_ID: 53
PREVIOUS_DELTA_ID: 52
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your three corrections applied. Then I checked W4/W5 against the
         SCHEDULE and found them incomplete. W4 is now finished -- its missing
         timing harness is built and run. W5 needs three rulings from you.

NOTE ON FORM: this covers five sessions and hit §8's 400-line cap. Rather than
cram, the detail rides the bundle diff, which carries DECISIONS.md and
PROJECT_STATE.md in full -- D-078's precedent when the channel filled. Nothing
is dropped: D-111 … D-114 and DEV-009/DEV-010 are in the ledger you receive.

--------------------------------------------------------------------
1. YOUR THREE PROSE CORRECTIONS: APPLIED IN YOUR WORDING (D-111).

All three verified first. All three right.

  layout/threshold  "plays no part in threshold selection" was LITERALLY FALSE
                    and ONE GREP away: reference_strata()'s own docstring says
                    the pool balances over "(layout, causal_attribute) strata".
                    I was reaching for a claim about FUTURE DISCRETION and wrote
                    one that DENIED A FACT ABOUT THE PAST.
  MDE simulation    my draft asserted BOTH HALVES of a contradiction, four
                    sentences apart. A self-contradiction inside one section is
                    worse than either half alone: the reader resolves it in
                    whichever direction flatters the result.
  correlation       contradicted by its own next sentence.

THE PATTERN, NOW FIVE DEEP, and I want it on record because a reset will repeat
it: ALL of these -- plus D-108's causal attribution and D-110's quantile
generalisation -- are ONE MOVE, A DEFENSIBLE CLAIM STATED ONE DEGREE STRONGER
THAN THE EVIDENCE CARRIES. Every correction has been a NARROWING, never a
retraction. That is exactly why it is hard to catch while writing: the sentence
is about something true and the overreach sits in the quantifier.

Base moved to f6bcd63 in §1 and CLAUDE.md, with your reason recorded.
Append-only convention ratified, noted, and applied to DEV-007 -> D-110 too.

--------------------------------------------------------------------
2. THE LAST §4-MANDATED METHODOLOGY SECTION (D-112).

The W2 decision on whether the Exp 2A conditions are drawn from the sweep or are
ADDITIONAL to it (D-007, closing your Q-003) had no prose. It does now.
Arithmetic checked IN CODE: canonical 75 (of which 2A = 20), sweep_candidates is
the matrix MINUS canonical, design_units 300 with 300 distinct ids. Naive
double-counting gives 375 against 300. The remaining two §4 items -- a
repair-budget or configuration-count REDUCTION, and a cut experiment -- have not
happened, so nothing is written for them.

--------------------------------------------------------------------
>>> 3. THE STUDENT WANTS WEEKS 4 AND 5 FINISHED. THEIR WORDS, PASSED ON. <<<

So I checked whether they were, against the SCHEDULE DOCUMENT rather than the
ledger's memory of it. THEY WERE NOT (D-113). §1 had claimed "Weeks 1-5 are
complete" for many sessions.

  W4 FRI was HALF DONE. The cell has TWO tasks. Threshold: done. "Timing
  harness: measure one full condition end to end and extrapolate total
  GPU-hours": NEVER BUILT. And GATE 1 CONDITION 2 WAS SIGNED **PASS** ANYWAY, on
  "14,885 fits against ~8,700" -- A FIT COUNT, NOT GPU-HOURS.

  W5 FRI is HALF DONE. Figure script: done. The labelled-unit class-balance
  procedure with a per-unit trace cap: NO IMPLEMENTATION. S§W11 Mon explicitly
  assumes it exists ("using the Week 5 procedure").

  A DEVIATION NEVER WRITTEN, now DEV-009. S§W5 Tue specifies statsmodels MIXEDLM
  with an episode-mean fallback; we run an equal-seed paired difference with a t
  interval and NO fallback (D-094/D-100). You authorised it pre-data and it is in
  §2 and the ledger -- but "mixed-effects" appeared ZERO times in
  PROJECT_STATE.md.

WHY IT STAYED INVISIBLE, which matters more than the items: each gap sits BESIDE
something done well and reported at length. The threshold calibration is the most
reviewed artefact in this project and SHARES A CELL with the harness nobody
built. The acceptance change survived four of your rounds and two Change Records
without either of us asking where its deviation record was. THE LEDGER TRACKS
DECISIONS, NOT CELLS. Nothing checks schedule coverage.

--------------------------------------------------------------------
4. W4 FRIDAY'S TIMING HARNESS IS BUILT AND RUN. W4 IS NOW COMPLETE (D-114).

I did not ask first. My reasoning, challenge it if you disagree: it reads WALL
TIME AND NOTHING ELSE, at stage="pilot" which carries no seed policy and can
never enter a claim, writing no registered evidence. That is the discipline
D-103 used timing a cell before the threshold run, which you accepted. MEASURING
is mine; RE-ADJUDICATING A SIGNED GATE IS YOURS, and I have not done the second.

  configuration                        extrapolated    vs the 120-h trigger
  CPU, 4 threads (certified config)       6.40 h     0.053x   19x headroom
  CPU, 24 threads                         8.72 h     0.073x   14x headroom
  CUDA (RTX 4080 SUPER)                   7.92 h     0.066x   15x headroom

FEWER THREADS IS FASTER AND THE GPU BARELY HELPS -- it is a small MLP, so
synchronisation and launch overhead dominate. THE DESIGN IS EFFECTIVELY
CPU-BOUND AND THE GPU IS NOT THE RESOURCE THE BUDGET IS DENOMINATED IN.

The design is inside budget BY 14-19x and the direction holds in every
configuration. The schedule's premise -- "sits at the edge of the budget with no
meaningful headroom" -- was written about the PLAN'S SPECIFICATION and is NOT
TRUE of the implemented system (scripted policy per DEV-001, small MLP,
gridworld).

WHAT THE NUMBER IS NOT: training time only; collection measured per condition
(0.04 s at n=100 to 1.4 s at n=50,000) but not multiplied in; THIS machine, not
Kaggle. Extrapolated PER TRAINING SIZE, never one scaled rate -- which matters,
since data repair trains at 50,000 where a fit costs 20.5 s against 1.4 s at
5,000.

MY ACCOUNTING WAS WRONG FIRST, AND IT WAS D-033'S ERROR EXACTLY. Summing
obligations() gave 6,750 baseline fits against 6,375 -- THE 375 PHANTOM FITS,
the repair-validation baseline counted at twenty-five seeds when the twenty
contain the five -- while ALSO charging one fit per repair OBLIGATION instead of
per seed. Two errors, opposite directions, in a function whose only job is
counting. Rebuilt on execution_plan it reproduces 8,047 exactly. A SECOND
IMPLEMENTATION OF A NUMBER THE PROJECT HAS ALREADY BEEN WRONG ABOUT IS NOT A
SHORTCUT, IT IS THE BUG. Pinned by a test shown to fail on a deliberate
off-by-one.

W4 VERIFIED CELL BY CELL against the "Done when" column -- the column I
truncated first time, and where Friday's second task was hiding:

  Mon  trend test runs on Week 3 outputs           DONE  D-068/D-069
  Tue  "verdict AND RUNG written to the run log"   DONE  rung 0, certified
  Wed  only if Tuesday failed                      correctly NOT run
  Thu  only if Wednesday failed                    correctly NOT run
  Fri  "threshold frozen; MEASURED ESTIMATE
        COMPARED AGAINST THE TRIGGER"              DONE  D-107 + D-114
  Sat  ~400 words: outcome, rung, threshold        DONE  875 words

W5 REMAINS OPEN ON EXACTLY ONE CELL: Friday's class-balance procedure.

--------------------------------------------------------------------
>>> 5. CHECKING W4 TURNED UP A W5 DEPARTURE THAT WAS NEVER LOGGED (DEV-010). <<<

S§W5's focus note, on our exact situation, in the schedule's own words:

    "If the MDE does not clear five percentage points, RAISE THE CONFIGURATION
     COUNT NOW. It costs Kaggle time, not your time. Discovering this in Week 15
     costs the thesis."

The MDE does not clear five points. The count was not raised. THAT DEPARTURE
APPEARS NOWHERE IN §4 -- the deviation log the thesis methodology draws from.
D-078 quoted the instruction and D-089 records your refusal, but declining an
explicit scheduled remedy was never written as a deviation. It is now DEV-010.

BEING PRECISE, because you have corrected me five times for exactly this:

  I AM saying      the departure must be RECORDED. And the schedule pre-empts
                   the cost objection -- "it costs Kaggle time, not your time" --
                   which D-114 has now MEASURED AND CONFIRMED, not refuted.
  I AM saying      your BUDGET ground is measurably not binding: 6.40 h measured,
                   ~32-52 h for a 5-6x design, against a 120-hour trigger.
  I am NOT saying  you were wrong. 1,500-2,000 held-out units is a ~TWENTY-FOLD
                   gap -- that is not "raise the count", it is a different study,
                   which is a fair reading of "scope".
  I am NOT saying  expansion is advisable. I have started nothing.

YOUR SCOPE GROUND IS UNTOUCHED by the measurement: the twenty-week calendar, the
student's ~14 h/week, and generating 5-6x the data are all unaffected. If scope
alone still carries the refusal, say so and DEV-010 records it cleanly as a scope
decision rather than a scope-and-budget one.

--------------------------------------------------------------------
WHAT I NEED FROM YOU TO FINISH W5. FOUR RULINGS.

1. GATE 1 CONDITION 2 -- re-assess against the measured extrapolation, or leave
   the fit-count basis on the record? The VERDICT does not change; it passes
   either way. The recorded BASIS is currently a proxy for the quantity the
   condition names.

2. W5 FRIDAY'S CLASS-BALANCE PROCEDURE -- unbuilt, and I have not started it
   because it sits inside the reserve-consumption area you have gated. I need:
     - is the per-unit TRACE CAP a preregistered §2 quantity or an
       implementation choice? If preregistered, what value -- and it must be
       fixed before any labelled data exists;
     - does it require C-005's grouped splitter first? D-039 says a comparison
       group must never span a split, and this balances "within each split", so
       they look coupled -- but you have C-005 as W6/W11 work;
     - may it be built and tested on SYNTHETIC inputs now, as the MDE simulation
       was, given no labelled units exist yet?

3. DEV-010 -- does the refusal to expand rest on scope alone now that budget is
   measured, or do you want it re-argued?

4. Q-004 AND WEEK 6 -- does it still hold Week 6 execution now that Phase A is
   complete and the threshold is final? The student wants the weeks closed, so
   this is now a live scheduling question rather than a hypothetical.

--------------------------------------------------------------------
NUMBERS (D-011)

  W4                COMPLETE, verified cell by cell against "Done when"
  W5                one cell open: Friday's class-balance procedure
  timing            6.40 h at 4 threads / 8.72 h at 24 / 7.92 h CUDA
                    vs a 120-hour trigger -> 14-19x headroom
  design            8,047 non-ablation fits, reproduced from execution_plan
  threshold         0.610702633857727 -- unchanged, certified, final
  tests             830 -> 835 passing, 2 skipped, 0 xfailed
  compute           timing runs only, pilot stage, ~25 min. Registered compute
                    unchanged: 675 CPU fits, 0 GPU-hours.
  data seen         NONE. Wall time only; every timing run discarded its
                    ensemble and wrote nothing.
=== END UPDATE ===
```
