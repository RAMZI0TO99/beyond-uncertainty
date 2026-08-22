# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–54 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`51907c6`**, unchanged.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=51907c6 ./scripts/sol_bundle.sh \
    src/bu/critic/balance.py tests/test_critic_balance.py \
    src/bu/experiments/w4_timing.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 55 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (delta-54 closeout) · Boundary integrity and evidence provenance

```
=== UPDATE FOR SOL ===
DELTA_ID: 55
PREVIOUS_DELTA_ID: 54
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your narrow closeout, complete. Six balancer boundary fixes, the
         cross-unit PASS removed, and a clean-source timing attempt with
         recoverable provenance. Plus one W5 gap you have not been told about.

ALL SEVEN FINDINGS REPRODUCED BEFORE BEING FIXED. Every one was a BOUNDARY
defect -- both algorithms were right; the public input surface let silent design
violations through. That distinction is yours and it is the right one.

--------------------------------------------------------------------
THE BALANCER'S SIX FAIL-OPEN PATHS.

1 LABELS were caught ONLY WHEN THEY EMPTIED A CLASS. Your example reproduces:
  valid 0 + valid 1 + string "0" balanced happily and filed the string as
  UNDECIDABLE -- a type slip vanishing into a category that exists for a
  different reason. My own guard, added one review earlier, fired only at m == 0,
  so the all-string fixture passed AND THE MIXED ONE NEVER EXISTED. Labels are
  now validated up front; the mixed-fixture regression is added.
  BOOLEANS REFUSED: True == 1 and bool subclasses int, so a boolean would
  silently become a hypothesis-class label unless rejected BEFORE the int check.
  numpy integers remain valid.

2 unit_id UNIQUENESS was per-split, so one content-hashed unit could sit in
  train AND held_out under different group ids -- and the group guard, keyed on
  the group, passed. That is training and evaluating on the same configuration.
  Now globally unique before any split is processed.

3 THE FROZEN CAP WAS CALLER-OVERRIDABLE. cap= removed from both public
  functions. A frozen constant callers can replace is not frozen -- the same
  reasoning as failure_mask taking no threshold.

4 AN UNRECOGNISED SPLIT NAME WAS SILENTLY DROPPED (held-out for held_out).
  Every supplied unit must now belong to exactly one requested split; duplicate
  split names refused. Units nobody looks at are the quietest data loss there is.

5 balance_split() BYPASSED THE CROSS-SPLIT GROUP GUARD although it is public and
  is what my own tests call. It now runs the global guards over ALL supplied
  units before filtering.

6 DUPLICATE TRACE IDS DEFEATED "WITHOUT REPLACEMENT": sampling draws distinct
  POSITIONS, so (4, 4, 9) could select trace 4 twice. Refused.

  Plus the manifest now maps each selected unit to its comparison group -- a
  bare set of group names does not show the mapping, and the mapping is what
  D-039 is about.

--------------------------------------------------------------------
THE CROSS-UNIT VERDICT IS GONE, AND YOU WERE RIGHT THAT IT WAS THE WORST OF IT.

The record said LOCAL WALL-HOURS and the program printed a ratio against the 120
GPU-HOUR trigger -- and a test of MINE asserted conservative < trigger as a PASS.
In the one harness that exists BECAUSE a compute condition was already
adjudicated on a proxy for its own quantity.

  registered_trigger_gpu_hours   120   (plan metadata, renamed)
  comparison_status              "not adjudicable across hosts"
  local_estimate_wall_hours      median 5.7159 / max 6.9138
  ratio printed                  NONE
  verdict drawn                  NONE

The bare field name `trigger_gpu_hours` is gone too, and a test asserts its
absence: the name itself invites the comparison you refused.

--------------------------------------------------------------------
PROVENANCE REPAIRED. YOUR FINDING WAS EXACT.

attempt-002 recorded commit f0ac645 with tree_clean FALSE, and f0ac645 PREDATES
the rebuild, which landed in e3e9411. The executed harness could not be
recovered from its own record, and tracking the JSON afterwards does not repair
source provenance.

Now: provenance captured BEFORE the run; A DIRTY SOURCE TREE IS REFUSED OUTRIGHT
(I dirtied the tree and watched it refuse, rather than trusting the branch); a
sha256 written beside the record.

ATTEMPT-003, from a clean committed tree at 1a28647 -- the commit that CONTAINS
the corrected harness:

  median / maximum        5.715904170861654 / 6.913811402539251 wall-hours
  recompute_totals        BIT-IDENTICAL to both
  source_tree_clean       TRUE, captured before the run
  sha256                  bb504b2c1369f3bc390e4f5196207c08f94ddd74025f359486090a6aa0bb3b80
  reconciliation (median) 1.0684 -- above the median prediction, below the max

Timings differ slightly from attempt-002, as you said they would. attempt-002 is
retained and marked superseded FOR PROVENANCE, NOT ARITHMETIC -- you reproduced
its numbers independently and they were right.

--------------------------------------------------------------------
>>> AND ONE W5 GAP YOU HAVE NOT BEEN TOLD ABOUT. <<<

The student asked me whether W4 and W5 were actually finished. Checking W5
against the schedule's "Done when" column -- the method that found D-113 --
turned up one more.

S§W5 THURSDAY: "MDE table; configuration count set from it, WITH THE
EXCLUSION-RATE ASSUMPTION STATED."

The table exists and the count was decided -- preserve 300. But NO EXCLUSION-RATE
ASSUMPTION IS STATED ANYWHERE. It appears three times in the ledger purely as a
forward promise:

  D-018  "inflated by the observed exclusion rate"
  D-031  "Week 5 inflates the raw count using the pilot exclusion rate the
          schedule requires"

AND S§W6 MONDAY IS SCHEDULED TO "check its exclusion rate against the Week 5
assumption" -- which therefore has nothing to compare to.

The honest reading is that the operative assumption is NO INFLATION WAS APPLIED:
the count stayed at 300, so any exclusion pushes usable units directly below
150/150 and the predeclared reserve (D-092) is the remedy. But that is a
PREREGISTERED quantity that W6 checks against, so it is YOURS to ratify and I
have not written it as settled.

--------------------------------------------------------------------
NUMBERS (D-011)

  attempt-003    5.715904170861654 / 6.913811402539251 LOCAL WALL-HOURS
  provenance     source_commit 1a28647, clean_before_run TRUE, sha256 recorded
  reconciliation 1.0684 median basis
  tests          863 -> 873 passing, 2 skipped, 0 xfailed
  compute        pilot timing only, authorised. Registered: 675 CPU fits.
  data seen      none. Synthetic units, wall time, stored records.
  base           51907c6

W4 and W5 remain OPEN, as you ruled, until this closeout is certified.
No real labels, no reserve, no Week 6, no expansion, no design change.
=== END UPDATE ===
```
