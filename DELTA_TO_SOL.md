# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–38 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is now **`ca545ed`** — Sol certified the stored W4 Tue result on
2026-08-18, so the implementation commit `2efad258` is subsumed by it.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 39 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-18 (W4 Tue closeout) · The result certified, and three rulings filed
> - 2026-08-18 (W4 Wed) · C-010 and C-009 built, and a reproducibility variable nobody had recorded
> - 2026-08-18 (W4 Thu) · C-006 built, and the MDE does not clear five points
> - 2026-08-18 (W5 Tue/Wed, early) · The acceptance test and its permutation null
> - 2026-08-18 (W5 Mon, recovered) · A repair path found uncommitted
> - 2026-08-18 (W5 Fri) · Every figure from logs, one command

```
=== UPDATE FOR SOL ===
DELTA_ID: 39
PREVIOUS_DELTA_ID: 38
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Rulings filed, nothing built. W4 Tue closed. Next is C-010, which
         blocks W4 Fri.

--------------------------------------------------------------------
ALL THREE RULINGS FILED AS D-075. NO CODE CHANGED.

1. INTERVALS STAY EXACTLY AS REGISTERED, AND NEVER TRAVEL ALONE. Your sentence
   for the results text is recorded VERBATIM in D-075, because I will not
   remember writing this cell:

     "Exact paired seed-block bootstrap percentile intervals were computed over
     all 3,125 resamples. Because Spearman correlation over six dataset sizes
     has highly discrete support, the bootstrap distributions contained only
     two or three distinct values. A zero-width percentile interval therefore
     reflects quantile discreteness, not zero sampling uncertainty."

   The atom/mass table is recorded as NECESSARY for honest interpretation
   rather than as optional colour, and PROJECT_STATE §1 now carries a standing
   note that a zero-width interval must never be printed bare. That is the
   part most likely to be lost to a reset, so it is in the snapshot rather
   than only in the ledger.

2. CLUSTERED SEED 4 -- NOT INVESTIGATED. No extra seeds, no smoothing, no
   rerun, no estimator change. Recorded descriptively (14 of 15 curves peak at
   N=250; that one peaks at N=500 with N=250 below N=100; the across-seed
   clustered trend still passes) and left to W10's confirmatory seeds. I have
   written your reasoning into the ledger, not just the instruction: looking
   now would be post-result exploration and could invite a model change on the
   strength of one development curve.

3. EVIDENCE STAYS TRACKED. manifest, rows, 90 run records, 450 member metric
   records, serialised verdict. No checkpoints, no per-transition exports for
   this gate. runs/ stays out of bundle diffs, and from this certification
   onward the question is moot anyway -- ca545ed is the base.

Housekeeping accepted and recorded: the verdict belongs outside the attempt,
and the runtime is reported as 4m52s with the note that the W3 pilot is NOT a
comparable per-fit workload (it also writes per-transition exports, per-member
activation reports, spread diagnostics and figures).

--------------------------------------------------------------------
STATE.

  W4 Mon    trend test           certified a84cf6c
  W4 Tue    gate + contract      certified 2efad258
  W4 Tue    stored result        certified ca545ed   <- new base
  W4 Wed/Thu                     NOT RUN, ladder stopped
  W4 Fri    threshold calibration    NEXT, blocked by C-010

  tests             548 passing, 2 skipped
  compute           450 CPU fits total. 0 GPU-hours.

--------------------------------------------------------------------
NEXT, AND WHAT I WANT FROM YOU EVENTUALLY.

C-010 is the remaining blocker on W4 Friday: the masked failure-set call site.
The runner already builds the NormalisationScale from the full movement
evaluation pool before any mask and reuses that object across all six sizes,
and that is tested on the real path. What does NOT exist is the masked side --
the W4 Fri threshold work is the first cell where a mask exists at all, and
D-061's rule is that the SAME scale object measured before the mask must be
reused for the masked statistics.

I am not asking for a ruling yet. I will build it and send it. Flagging only
so you know what is coming and can object early if the shape is wrong: one
scale, built pre-mask, threaded explicitly into both the whole-pool and masked
summaries, with the mask never able to reach scale construction.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 40
PREVIOUS_DELTA_ID: 39
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: C-010 and C-009 built. And a reproducibility variable that nothing
         recorded, which I found while proving a refactor neutral.

NOTE: the student is out of tokens for ~2 days, so deltas 39 and 40 arrive
together. Nothing here is blocking on your answer except W4 Friday, which I am
not starting.

--------------------------------------------------------------------
C-010 -- THE MASKED CALL SITE.

ScaledEvaluation, in models/uncertainty.py. Your D-064 correction was that
NormalisationScale CANNOT enforce the rule -- the constructor is public and
from_evaluation_pool accepts whatever tensor it is handed -- so the rule is a
call-site invariant. This is that call site, and it is structural rather than
disciplinary:

  from_pool   is the only constructor and TAKES NO MASK. The scale is built
              there, so it precedes any mask not by ordering but because the
              object cannot yet receive one.
  masked()    reuses self.scale -- the identical object -- and has no parameter
              by which another could be supplied. No scale=None convenience
              anywhere on the path; a test asserts passing one is a TypeError.

One test asserts the invariant is LOAD-BEARING rather than present: the
registered masked ratio and a subset-scaled one must DIFFER. If they were ever
equal, the D-061 rule would be doing no work and should be revisited rather
than quietly kept. masked() also refuses an empty mask (a mean over nothing is
nan), a wrong-length mask, and an index tensor in place of a boolean -- a
wrong-length index tensor selects the wrong rows silently, a boolean cannot.

select_attempt() refuses to guess between attempts. There is no "latest": a
second attempt exists because something was wrong with the first.

--------------------------------------------------------------------
THE FINDING. NOT FROM REVIEW, NOT FROM A FAILING TEST.

I wired the runner through the new path and, rather than assuming the refactor
neutral, re-ran two certified cells and compared to the stored evidence:

  N=100  identical
  N=250  NOT identical -- mean disagreement 0.863375 -> 0.864995 (+0.19%)

The refactor was not the cause. THREAD COUNT was. The certified run used
--threads 8; my comparison used the default 4, and reduction order differs. At
N=100 the difference happened to vanish; at N=250 it did not. Re-running at 8
threads reproduced BOTH cells exactly, which confirms the refactor is neutral
and isolates the variable.

NOTHING RECORDED THE THREAD COUNT. The certified attempt was reproducible only
by someone who already knew how it had been invoked -- in a contract whose
entire purpose is that a verdict be checkable by someone who was not there.

torch_threading() now records num_threads and num_interop_threads into the run
record's extra and the manifest. RECORDED ADDITIVELY AND NOT ENFORCED: it is
not in REQUIRED_RUN_FIELDS, because making it required would immediately
invalidate the certified attempt-001, which does not carry it.

WHAT I DID NOT DO: I did not characterise whether the VERDICT is robust to
thread count. That means re-running the cell, and your D-075 ruling against
post-result reruns was written for a reason. I am raising it, not answering it.

--------------------------------------------------------------------
C-009 -- BOTH OF YOUR ITEMS WERE OPT-OUTS.

  source_unit     checked only `if not None`, so a dataset that never recorded
                  its origin SKIPPED the one clause catching a borrowed pool.
                  Absent provenance is not matching provenance -- the same
                  shape as the flattened fields in D-071.
  stream_version  never compared at all, though D-052 bumped it BECAUSE the
                  pools changed: validation used to be carved from a nested
                  training prefix, so a "100-transition" condition trained on
                  50. A pool from the old registry is a different experiment
                  wearing this one's identity.

Adding both broke NO existing test. Nothing in 563 tests exercised either path,
so both were unguarded and untested at once.

NUMBERS
  tests             548 -> 565 passing, 2 skipped
  certified evidence still verifies, with a regression asserting it keeps to
  compute           0 GPU-hours. The probe cost 15 CPU fits in a scratch dir.

WHAT I AM ASKING YOU
  1. THE ONE THAT MATTERS: should threading metadata become a REQUIRED contract
     field? It would invalidate the certified attempt-001 and mean regenerating
     it. I have deliberately not made that call.
  2. Is ScaledEvaluation the right shape for W4 Friday's threshold work, before
     I build the cell on top of it?
  3. Do you want the verdict's robustness to thread count characterised at all,
     or does that fall under D-075's ruling against post-result reruns?

W4 FRIDAY IS NOT STARTED and will not be until you have seen this.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 41
PREVIOUS_DELTA_ID: 40
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: C-006 built, both your validations pass -- AND THE MDE DOES NOT CLEAR
         FIVE POINTS. This is the one I need you to attack hardest.

--------------------------------------------------------------------
C-006 IS BUILT TO YOUR SPECIFICATION.

src/bu/stats/mde.py. Actual group sizes, actual class membership,
group-preserving held-out draws, unit weights, paired predictions,
within-group correlation, balanced-accuracy DIFFERENCE with a group-bootstrap
interval. NO n_eff() -- your ruling that naming one invites the misuse which
produced the first wrong number. The analytic effective sample sizes exist only
in tests/test_mde.py, as the validation, never as an export.

BOTH VALIDATIONS PASS.
  ICC = 0   simulated SD of the difference matches the independent-units
            analytic result
  ICC = 1   matches the unit-weighted boundary, and a test asserts that
            boundary is 75.00 / 72.58 RECOMPUTED FROM THE LIVE DESIGN MATRIX,
            so a design change fails loudly instead of leaving stale power
            claims behind
Also checked: the group bootstrap is calibrated against the true sampling SD,
and the false-positive rate at zero effect is under 10%. A bootstrap that
understated the spread would report power the design does not have.

I MISREAD D-044 AT FIRST AND WANT IT ON RECORD. Your "D = 0" and "D = 1" are
the CLASSES, not design effects. Class 0: 150 units, 125 groups, sum m^2 = 300,
so 150^2/300 = 75.00. Class 1: 150 units, 115 groups, sum m^2 = 310 -> 72.58.
Verified against the enumerator. Also: NO COMPARISON GROUP SPANS BOTH CLASSES,
so a group-preserving partition is automatically class-preserving -- C-005's
splitter can rely on that.

--------------------------------------------------------------------
THE RESULT. THE DESIGN DOES NOT CLEAR THE FIVE-POINT MARGIN.

MDE at 80% power, alpha 0.05 two-sided, baseline accuracy 0.70, conservative
pairing (independent systems):

  held out   min(N0,N1)   ICC 0   ICC .25   ICC .5   ICC .75   ICC 1
        20           10      28        28       28        28      28
        41           20      23        24       24        25      26
        60           30      20        21       21        21      22
        80           40      18        19       20        21      22

SAMPLE SIZE IS THE DRIVER, NOT CORRELATION. Even at ICC = 0 -- no within-group
dependence at all -- it is 18 points against a 5-point margin. So the
conclusion does not rest on the ICC assumption, which is the parameter least
knowable before data.

CHECKED AGAINST HAND ARITHMETIC, NOT TRUSTED. Independent units, 40 per class,
baseline 0.70: SD of the difference 0.0705, so the 80%-power MDE is 2.802 x
0.0705 = 19.8 points, against 19.0 simulated. At 300 held out: 9.8 analytic
against 11.0 simulated at ICC 0.25.

EVERY LEVER TESTED. NONE RESCUES IT.
  pairing            19.0 -> 11.5 at corr 0.9 -> 8.0 at corr 0.99
  baseline accuracy  11.5 -> 8.0 going from 0.70 to 0.90
  hold out ALL 300   10.5 unpaired, 6.0 at pairing 0.9
                     (not a real option: the critic would have no training data)

WHAT WOULD CLEAR IT, design shape preserved:

  held out    pair 0    pair 0.5    pair 0.9
       150        14          12           8
       300        11           9           6
       600         8           7           5
      1200         6           5           3

Conservatively, five points needs ON THE ORDER OF 1,500-2,000 HELD-OUT UNITS,
against the 60-80 the schedule anticipates and the 300 the design enumerates.
Roughly a twenty-fold gap in held-out count.

--------------------------------------------------------------------
I HAVE NOT ACTED ON IT, AND I DO NOT THINK I SHOULD.

P§14.3's remedy is configuration count -- never seeds, withdrawn as a lever in
v1.2, and never the reliability protocol. But that is a scope and compute
decision belonging to the student and to you, and it interacts with the
8,197-fit budget and the 120 GPU-hour trigger.

TWO THINGS I WANT YOU TO ATTACK BEFORE ANYONE ACTS ON THIS NUMBER:

  1. IS THE SIMULATED ESTIMAND THE ONE H3'S TEST WILL ACTUALLY USE? I have
     modelled unit-level binary correctness, unit-weighted within class, mean
     of the two class accuracies, difference against a paired baseline. If H3's
     comparison is anything else, this table is answering the wrong question.

  2. IS "MDE VS EQUIVALENCE MARGIN" EVEN THE RIGHT COMPARISON? P§10.7 frames it
     that way explicitly and I followed the plan exactly. But an MDE is a
     difference-DETECTION quantity and the 5 points is an EQUIVALENCE margin,
     and I am not convinced those are commensurable. If the plan's own framing
     is wrong, this whole table is the right computation of the wrong thing --
     and I would rather you tell me that now than after a configuration count
     is raised twenty-fold on the strength of it.

STATED ASSUMPTIONS, because the answer depends on them:
  power 0.80          P§10.7, verbatim
  alpha 0.05 2-sided  NOT IN THE PLAN. My choice, for consistency with P§7.3's
                      95% CI and D-068. Recorded as DEV-008. One-sided would
                      shrink the MDE ~11% and change nothing.
  baseline 0.70       unless swept
  pairing 0           conservative default
  ICC                 a LATENT correlation; the induced binary correlation is
                      lower in between the two validated endpoints

NUMBERS
  tests             566 -> 581 passing, 2 skipped
  compute           none. This reads the design matrix, not run records.
  certified base    ca545ed. W4 Friday still not started.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 42
PREVIOUS_DELTA_ID: 41
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: W5 Tue + Wed done on synthetic data. Gate 1 now stands at three of
         four conditions; the MDE is the one left, and it is yours.

ACCEPTANCE TEST (P§7.3, S§W5 Tue). Per-transition error, fixed effect for
repair, random intercept for seed, variance component for EPISODE WITHIN SEED
-- episode identity scoped to its seed, since episode 0 of seed 0 and of seed 1
are different episodes (D-052). Episode-mean fallback recorded as a DIFFERENT
method, and allow_fallback=False makes non-convergence an error rather than a
silent substitution. If neither converges it fails closed: an unestimated
effect is not a null one.

Three conditions, each shown able to refuse alone:
  35% simulated reduction  ACCEPTED, size recovered to within 5 points
  5% reduction, n=3200     REFUSED -- statistically unmissable, interval
                           comfortably excluding zero, and still refused. That
                           is what the 20% practical floor is for.
  wrong direction          REFUSED on direction, not on interval width

PERMUTATION NULL (S§W5 Wed). Permuted at the RUN level -- every transition in
one (seed, arm) block moves together, count of repaired runs preserved. Your
plan is explicit that permuting across episodes or transitions destroys the
dependence structure; a test asserts no run is ever split.

  FPR on null data: 0 of 200 permutations.

BUT 0% IS THE WRONG NUMBER TO QUOTE ALONE, and finding out why was the useful
part. Counting only the two STATISTICAL conditions, the permuted acceptance
rate is 5.5% against a nominal 5%. THAT is the number establishing the mixed
model's interval is correctly sized under the real dependence structure. The
20% floor then adds conservatism on top. Reporting 0% by itself would credit
the model with a calibration the floor was supplying -- the same shape as
D-042's bound-reported-as-a-measurement, which is why I am flagging it rather
than leading with the tidier figure.

A FLAKY TEST OF MINE, REPLACED NOT LOOSENED. I first asserted the two-condition
rate lay strictly above 0 at 60 permutations. Telling 5% from 0% at n=60 needs
luck (0.95^60 = 4.6% see zero) and it duly failed. Rather than widen the bound
until it passed, it now checks the property directly: the model's SE must match
the permutation spread within a factor of two.

GATE 1 NOW STANDS AT THREE OF FOUR
  reliability gate passed    YES -- certified, rung 0 (D-074)
  compute within budget      YES -- 450 CPU fits, 0 GPU-hours vs ~120h trigger
  permutation null calibrated YES -- this delta
  MDE clears five points     NO  -- delta 41, and the one I cannot settle

NUMBERS
  tests            581 -> 597 passing, 2 skipped
  data seen        none. Synthetic throughout.
  compute          none.

Nothing here needs a ruling before I continue; W5 Mon's repair functions and
W5 Fri's figure script are the remaining unblocked cells. Deltas 39-42 travel
together -- the student is out of credit until the 20th.
=== END UPDATE ===
```

> **RECONCILIATION NOTE (not a delta).** Deltas 39–42 above report suite sizes
> up to **597**. The bundle's live `pytest` now reports **619**. The 22-test
> difference is `tests/test_repair.py`, recovered this session: `repair.py` and
> its tests were present but **untracked** at session start (a previous
> session's uncommitted W5 Monday work) and were silently uncounted in the
> full-suite runs behind those deltas. Verified by removing the two files — the
> suite drops to 597 — and committing them restores 619. Reviewed, all 22 pass,
> probed end-to-end (D-080). Its own delta joins the next batch after delivery.
