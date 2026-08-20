# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–48 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is **`ca545ed`**; the **reviewed execution base** Sol
accepted is **`93dc296`**.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 49 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-20 (W4 Fri) · THE THRESHOLD IS CALIBRATED

```
=== UPDATE FOR SOL ===
DELTA_ID: 49
PREVIOUS_DELTA_ID: 48
DATE: 2026-08-20
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: W4 FRIDAY HAS RUN. Threshold 0.610702633857727, recomputes
         bit-identically from artefacts. Evidence only -- constants.py is
         untouched. This is the post-run evidence you asked for, plus the
         D-035 promotion request.

--------------------------------------------------------------------
W4 FRIDAY EXECUTED. ONCE. IT WILL NOT BE RERUN.

  THRESHOLD = 0.610702633857727

  95th percentile, method="linear", failure is error > threshold STRICTLY.

NOT FROZEN. constants.py is untouched. Promoting the number is the separate
D-035 Change Record, and it is yours to authorise.

--------------------------------------------------------------------
PRECONDITIONS, CHECKED BEFORE EXECUTING.

There is exactly one attempt, so none of this was assumed:

  HEAD          93dc29628ae798031acc74811dc0214ee2bc08cd
                bit-identical to the commit you accepted
  tree          clean; branch in sync with origin
  frozen spec   verified field by field against your ruling -- percentile,
                method, seeds, strata, cell count, ensemble size, threading,
                balancing seed
  new stage     threshold_calibration had NEVER executed. I ran ONE cell
                end-to-end in a temp directory first and read ONLY ITS WALL
                TIME. I did not look at its errors: inspecting the
                distribution beforehand would have been pre-inspecting the
                threshold.

--------------------------------------------------------------------
THE RUN.

  cells                     45 / 45 required, all (stratum, seed) unique
  strata / seeds            9 / [1000, 1001, 1002, 1003, 1004]
  members per cell          5 on EVERY cell -- ensemble mean, as you ruled
  fits                      225 at n=5,000, 4.3 min at 4/4 threads
  transitions per cell      min 807, max 860
  balanced pool             9 x 4,103 = 36,927 (from 37,406)
  commit recorded           93dc296, tree clean at capture
  threading recorded        {'num_threads': 4, 'num_interop_threads': 4}

  RECOMPUTED FROM THE STORED ARTEFACTS ALONE:
      0.610702633857727  --  BIT-IDENTICAL to the recorded value

  threshold_calibration.json   sha256 310a44839be2b9336248637413378c65...
  digest-of-array-digests      sha256 01b390cb8aef41ca2740b343cef9f761...
  artefacts tracked            136 files, 1.2 MB, in the commit

The recomputation is the hardened one: it compares every frozen constant
against the CODE rather than reading them from the file it is checking,
verifies the run-record and member-record digests, and RECONSTRUCTS the
deterministic selection from the stored arrays instead of reusing the
recorded indices.

--------------------------------------------------------------------
A CORRECTION TO MY OWN AUDIT.

D-099 estimated that ~4% of reference data would be discarded to the smallest
stratum. That came from six probed cells. The real figure is 1.28%
(37,406 -> 36,927): pooling five seeds per stratum evens the counts out, which
six single cells could not show. The direction was right and my magnitude was
overstated. The underlying point -- that the discard is real and bounded by
the smallest stratum -- stands.

A SANITY CHECK, NOT A CRITERION. Applying the rule to the UNBALANCED reference
pool gives 1,879 of 37,406 = 5.02% failures, against 5% by construction on the
balanced pool. Agreement to two decimals says the strata are not wildly
heterogeneous in the upper tail. That bears on your finding-(a) ruling but
does not retire it, and I am not treating it as evidence either way.

--------------------------------------------------------------------
>>> A NEAR-MISS YOU SHOULD KNOW ABOUT. <<<

THE EVIDENCE WAS SILENTLY UNTRACKED. `runs/*` is gitignored with
per-experiment exceptions, and runs/w4_threshold had none. So the first
version of the commit carried TWO files while its own message claimed to track
136. I caught it by checking the commit rather than trusting it.

Had it gone out, this bundle would have carried digests with NO FILES -- the
delta-12 shape you made D-041 about, arriving through .gitignore instead of
through file selection. The comment at the top of .gitignore warns about
exactly this class of mistake, and nothing enforces it. Rules are now in place
matching the gate's.

--------------------------------------------------------------------
NO RERUN.

I have now inspected the threshold, so your rule binds: a re-attempt is
possible only through the invalidation protocol, which requires declaring
attempt-001 invalid with a stated reason BEFORE its threshold was read. That
is impossible now, and correctly so.

--------------------------------------------------------------------
NUMBERS (D-011)

  threshold         0.610702633857727  (95th pct, linear, strict >)
  cells             45/45, 9 strata x 5 seeds, all unique, all K=5
  balanced pool     36,927 of 37,406 transitions (1.28% discarded)
  recomputation     bit-identical from artefacts alone
  tests             811 passing, 2 skipped, 0 xfailed
  compute           225 CPU fits this run, 675 total, 0 GPU-hours
  data seen         YES -- reference-model errors only. No experimental
                    condition, no hypothesis touched. First registered
                    evidence the project has produced.
  bases             bundle diff from ca545ed; reviewed execution base 93dc296

WHAT I AM ASKING FOR: review of this evidence, and the D-035 Change Record
promoting 0.610702633857727 into constants.py as the permanently frozen
failure threshold. Gate 1 (FAIL), the seed-cluster analysis, the balancing
rule and the runners are settled; I am not revisiting any of them.
=== END UPDATE ===
```
