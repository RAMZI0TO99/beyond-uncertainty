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
