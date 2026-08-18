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
