# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–37 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is now **`2efad258`** — Sol certified it on 2026-08-18 and it subsumes
the three uncertified intermediates.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=2efad258 ./scripts/sol_bundle.sh \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 38 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-18 (W4 Tue) · Rung 0 passes

```
=== UPDATE FOR SOL ===
DELTA_ID: 38
PREVIOUS_DELTA_ID: 37
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: RUNG 0 PASSES, all three configurations. Ladder stopped as you
         instructed. The interval needs reading carefully -- see below.

--------------------------------------------------------------------
PRE-FLIGHT, AS YOU REQUIRED.

  tree clean, HEAD 2efad258af7638b2657c44bb80a7e753743cfa03
  git_state() dirty: False        allow_dirty: NOT used
  registered defaults only, no overrides

--------------------------------------------------------------------
THE RUN.

  attempt id        w4-gate-r00-93bec8081d97-4f58c24f213c
  path              runs/w4_gate/rung-00-93bec8081d97/attempt-001/
  commit            2efad258af7638b2657c44bb80a7e753743cfa03
  rung spec hash    93bec8081d97
  manifest sha256   0fee9444a24792d357bb5d55f2d239e78a3afdaf7fd33516dbf471527933b942
  verdict  sha256   c0d92221b03c690df7eb55b898eba31438a62f084738dd0d584dbbc0b5d9dc89
  shape             3 configurations x 5 dev seeds x 6 sizes = 90 ensembles
  fits              450
  runtime           4m 52s CPU (0.65 s/fit)
  recompute()       EXACT equality with the serialised verdict
  post-run suite    548 passing, 2 skipped

--------------------------------------------------------------------
VERDICT: RUNG 0 (ensemble) -- PASS. ALL THREE.

  configuration     rho          95% interval           verdict
  uniform        -0.9429    [-0.9429, -0.9429]           PASS
  clustered      -0.9429    [-0.9429, -0.8286]           PASS
  sparse         -0.9429    [-0.9429, -0.9429]           PASS

  aggregate: PASS -- all three configurations pass the registered
  directional rule. No majority vote was needed or applied.

LADDER STOPPED. Rungs 1 and 2 not run, per your instruction.

--------------------------------------------------------------------
WHY ALL THREE RHOS ARE IDENTICAL. IT IS THE STATISTIC, NOT A COINCIDENCE.

Spearman reads ranks only, and all three mean curves carry the SAME rank
pattern: falling except a peak at N=250. -0.9429 is exactly one adjacent
transposition from perfect reversal -- the N=250 peak costing one of fifteen
pairwise inversions, exactly as you predicted before any of this ran and
exactly what D-069 measured at three seeds.

--------------------------------------------------------------------
THE INTERVAL. DO NOT READ THE POINT INTERVALS AS ZERO UNCERTAINTY.

The exact paired bootstrap is DISCRETE WITH VERY FEW ATOMS. Enumerated over
all 3125 resamples:

  configuration    -0.9429    -0.8286    -0.7714   distinct
  uniform           98.37%      1.63%         --      2
  clustered         81.86%     17.82%      0.32%      3
  sparse            97.86%      2.14%         --      2

Uniform and sparse are degenerate ONLY JUST: their second atom sits at 1.63%
and 2.14% against the 2.5% quantile threshold. SPARSE IS WITHIN 0.36
PERCENTAGE POINTS of its upper bound flipping to -0.8286.

The VERDICT is unaffected by any of this -- every atom in every configuration
is far below zero, so the registered rule passes whichever atom the quantile
lands on. But the WIDTH is not a precision claim, and I am flagging it because
[-0.9429, -0.9429] reads like one. This is D-069's coarseness finding again:
five seeds take the support from 27 to 3125 without adding many distinct
values, because it is a rank correlation over six points.

--------------------------------------------------------------------
THE N=250 PEAK REPRODUCES IN 14 OF 15 CURVES.

Disagreement is NOT monotone in dataset size. It peaks at N=250 in fourteen of
the fifteen seed-configuration curves. The exception is CLUSTERED SEED 4,
which peaks at N=500 with N=250 falling BELOW N=100 -- a different shape.
Kept and reported, not smoothed.

The gate passes because Spearman tolerates exactly one inversion. I want to be
explicit that this is a reliability result about the ESTIMATOR and not H1's
verdict, which is W10 on confirmatory seeds.

--------------------------------------------------------------------
TWO HOUSEKEEPING FIXES, AND A MEASUREMENT ERROR OF MINE.

1. I first serialised the verdict INTO the attempt directory -- mutating
   evidence after its manifest was written. Moved beside it as
   verdict-attempt-001.json; the attempt re-verifies unchanged.

2. The whole attempt is now TRACKED IN GIT -- manifest, rows, 90 run records,
   450 metric streams, 1.2 MB. This widens the pilot's manifest-and-rows-only
   exception deliberately: the contract's trust boundary IS those digests, and
   untracked, a fresh clone could read every claim and verify none of them.
   Tell me if you would rather it stayed local.

3. I told you rung 0 would be "minutes on CPU", then corrected that to ~50
   minutes by scaling the W3 pilot's 10-min/90-fit rate. IT WAS 4m 52s. The
   original estimate was right and my correction was wrong. The pilot is ~10x
   slower per fit because it also writes per-transition exports, per-member
   activation reports, spread diagnostics and figures. I scaled a rate without
   asking what it was a rate OF -- the D-044 mistake in a new costume.

WHAT I AM ASKING YOU TO ATTACK
  1. Whether a point interval arising from a 1.63% atom should be REPORTED as
     [-0.9429, -0.9429] at all, or whether the atom structure must travel with
     it in the thesis. I lean to the latter.
  2. Clustered seed 4. One curve in fifteen with a different shape, on a
     development seed. Worth a look now, or noise to be left alone until W10?
  3. Whether tracking 1.2 MB of evidence in git is right, or whether the
     manifest and rows alone were the correct boundary. Note the side effect I
     hit immediately: a bundle spanning that commit came out at 32,000 lines
     and was unusable, so runs/ is excluded from the diff again. The evidence
     is in the repo but not in your bundle -- the digests above are how you
     check it, not the files.
=== END UPDATE ===
```
