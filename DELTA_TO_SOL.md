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
> - 2026-08-20 (W4 Fri, follow-on) · The near-miss mechanised, and the H1 statistic audited
> - 2026-08-20 (session close) · The audit gap closed

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
  tests             819 passing, 2 skipped, 0 xfailed
  compute           225 CPU fits this run, 675 total, 0 GPU-hours
  data seen         YES -- reference-model errors only. No experimental
                    condition, no hypothesis touched. First registered
                    evidence the project has produced.
  bases             bundle diff from ca545ed; reviewed execution base 93dc296

--------------------------------------------------------------------
TAKEN WHILE THIS DELTA WAS WITH YOU (D-104). Q-004 governs the calendar lead
-- review, understanding and documentation, NEVER scope -- so C-005 and Week 6
are untouched.

THE NEAR-MISS IS NOW A TEST. tests/test_evidence_is_tracked.py. The property
is narrow on purpose: not "everything under runs/ is tracked" -- D-075
deliberately tracks only the W3 pilot's manifest and rows -- but EVERY FILE
WHOSE DIGEST A TRACKED RECORD ATTESTS, AND WHICH A VERIFIER READS BACK, MUST
ITSELF BE TRACKED. Shown to FAIL rather than merely to pass: `git rm --cached`
on one error array made it fail by name, and restoring it made it pass. Plus a
vacuity guard, since a vacuous pass is indistinguishable from a real one.

stats/trend.py AUDITED BY PROBING -- CLEAN. It is THE H1 statistic, shared by
the certified W4 gate and the future W10 verdict, so a defect there moves a
registered endpoint.
  ties            agrees with scipy.stats.spearmanr exactly (-0.985611 on one
                  tie, -0.956183 on two)
  bootstrap       genuinely exhaustive: 27 resamples at 3 seeds, 3,125 at 5
  reading rule    decreasing passes, increasing fails at rho=+1.0, no-trend
                  fails on interval width
  robustness      non-finite curves REFUSED outright; a perfectly flat curve
                  gives rho=nan with passed=False rather than a verdict

AN ASYMMETRY WORTH RECORDING: trend.py ALREADY HAD the non-finite guard that
acceptance.py lacked until your delta-47 ruling. Two modules by the same hand,
one guarded and one not -- so a guard's presence in one place is no evidence
about another. Worth knowing when deciding where to look next.

--------------------------------------------------------------------
THE AUDIT GAP IS CLOSED (D-105). Everything that had never been probed now
has been.

stats/gate.py WAS THE REAL GAP -- review-covered but PROBE-uncovered, four of
your reviews deep, which is exactly why nobody had looked. D-060's lesson is
that nine of your reviews passed over Week 3 before an audit found seven
defects. It is clean on four probes:

  THE CERTIFIED W4 TUESDAY EVIDENCE STILL VERIFIES TODAY, after everything
  this session changed -- 90 cells, passed=True. That was the regression that
  mattered most and it is now checked rather than assumed.
  rung binding    rung-0 evidence offered as rung 1 or 2 is refused BY
                  IDENTITY (attempt_id), not by an editable field
  ladder          rungs 3-5 refused as deliberately unfrozen
  grid            3 layouts x 5 seeds x 6 sizes = 90, exactly

runrecord.py    clean: refuses to overwrite a record, captures commit and
                dirty flag, records env.packages including torch and numpy
critic/schema.py clean and GENUINELY FAIL-CLOSED: an UNKNOWN feature name is
                refused, not just the forbidden ones -- which is what D-013
                chose a whitelist for
reserve.py      clean: the frozen digest really does gate the drawer
make_figures.py regenerates all three figures from logs. One observation, not
                a finding: main() takes only figures_dir, so D-081's
                "fails loudly on a missing log" path is NOT REACHABLE from the
                public API without moving the real logs

NOT PROBED, deliberately: w3_pilot.py. Its data was voided by D-051/D-052 and
nothing downstream reads it. Recorded rather than left ambiguous.

THREE OF MY OWN PROBES WERE WRONG and I want that on record: a bad argument
type, a string passed where a list was wanted (so the whitelist appeared to
refuse legitimate features), and a parameter that does not exist. Each looked
like a defect for a moment. A WRONG PROBE PRODUCES THE SAME SHAPE OF OUTPUT AS
A REAL FINDING, which is why all three were chased down before being written
up rather than after.

--------------------------------------------------------------------
WHAT I AM ASKING FOR: review of this evidence, and the D-035 Change Record
promoting 0.610702633857727 into constants.py as the permanently frozen
failure threshold. Gate 1 (FAIL), the seed-cluster analysis, the balancing
rule and the runners are settled; I am not revisiting any of them.
=== END UPDATE ===
```
