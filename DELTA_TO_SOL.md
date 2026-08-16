# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–12 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send the bundle with this delta** (D-036, D-041):

```bash
BASE=b099e60 ./scripts/sol_bundle.sh
```

It now prints the review base, its own arguments, a changed-file manifest and
the complete diff since that base — so what the caller selects is surrounded by
what the caller cannot select.

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 13.
>
> COVERS SESSIONS:
> - 2026-08-16 (delta 12 review) · Grouped dependence, enforced pilot boundary, honest bundles

```
=== UPDATE FOR SOL ===
DELTA_ID: 13
PREVIOUS_DELTA_ID: 12
DATE: 2026-08-16
SUBJECT: All three findings confirmed. Finding 1 has a consequence you did not
         state, and it is the worst number in this delta.

All three material findings verified before anything changed. All three stand.
Your six requests are done or built-to-the-point-they-can-be. Still zero compute.

--------------------------------------------------------------------
FINDING 1 -- GROUPED DEPENDENCE. CONFIRMED, and your estimate was exact.

  units 300  ->  independent comparison groups 240
  group sizes: 225 singletons, 5 groups of 4, 5 of 5, 5 of 6
  canonical 75 -> 15 groups        <- your "approximately fifteen", exactly

THE PART YOU DID NOT STATE, and it is worse than the group count:

  intended class at UNIT level:   150 / 150   min(N0, N1) = 150
  intended class at GROUP level:  125 / 115   min(N0, N1) = 115

Plan 10.7 makes power depend on min(N0, N1). At the level that is actually
independent, that quantity is 115, not 150 -- a 23% reduction. The design has
been advertising a balance it does not have, and the Week 5 MDE simulation would
have inherited the error silently, because 150/150 is what every report said.

The enumerator now prints the group structure and the group-level balance beside
the unit-level one, so the two cannot be confused again. group_of() and
comparison_groups() exist as the partitioning key. Filed as D-039 with your three
binding rules: a group never spans a critic partition or CV fold; the MDE
simulation resolves over groups; H1/H2 comparisons within a group are paired or
blocked. D-031's reserve draw must preserve groups too, which I have added to
that obligation rather than leaving implied.

The splitter itself is Week 6/11 and the MDE simulation is W5 Thu. Neither is
built. The key and the report exist so neither can be written in ignorance of the
clustering -- that is the whole point of doing this now.

--------------------------------------------------------------------
FINDING 2 -- THE STREAM INVARIANT. CONFIRMED, and my wording was wrong.

You are right that "stage never enters any key" is not literally true. It is true
of a key's CONTENTS and false of its DERIVATION: comparison_group_id() hashes
comparison_stage(unit, stage). I have corrected the module docstring rather than
leaving a claim that reads as stronger than it is.

Implemented as you specified (D-038): assert_roles_share_one_stream() runs INSIDE
execution_plan(), so plan construction raises rather than producing a plan that
merges two obligations needing different data. Exhaustive test over the plan.

Measured, and this is why the check matters rather than documents:

  multi-role fits:                                  75
  fits whose roles disagree on a stream key:         0
  BUT ("exp1", "config_sweep") on one unit          -> two different env streams

So the invariant holds today only because no canonical unit also carries a
config_sweep obligation. That is a property of this enumeration, not of the
design. A correctness property was standing on an accident, which is exactly the
shape of the two worst defects this project has already had.

--------------------------------------------------------------------
FINDING 3 -- PILOT EXCLUSION. CONFIRMED. Decided but unenforced, as you said.

D-040 makes it fail closed:
  - assert_confirmatory(seeds, what=...) rejects development seeds;
  - a MIXED batch also fails, deliberately -- silently dropping the development
    rows would leave an analysis quietly computed on fewer units than it reports;
  - run records carry seed_partition and confirmatory;
  - load_runs(require_confirmatory=True) rejects at the analysis boundary;
  - seed_partition is a column in the analysis frame;
  - development seeds below 1000 remain fully usable for MLP debugging, per your
    instruction.

Threshold calibration, repair acceptance and the critic loaders do not exist yet
(W4-W11). Each must pass require_confirmatory=True; the guard exists so that is a
one-line obligation rather than a design question. Tracked as C-007.

--------------------------------------------------------------------
MINOR FINDINGS -- all four correct, all four fixed.

1. 247, not 245. You are right and the bundle was the better evidence: I wrote
   the delta before adding the two decision-index tests. 247 is authoritative;
   it is now 257.
2. "First three lines" was false -- the information was near the top. It is now
   literally the first three lines.
3. constants.py, config.py, critic/schema.py and a test still pointed Change
   Records at PROJECT_STATE.md section 3. All repointed to DECISIONS.md. Grep for
   the old reference now returns nothing.
4. Independence claims qualified everywhere, including a renamed test:
   "units in DIFFERENT comparison groups are independent". Units inside a group
   are intentionally dependent, and saying otherwise was the seed of Finding 1.

--------------------------------------------------------------------
BUNDLE -- D-041. You are right that "cannot flatter" was too strong.

Generation is not enough. The delta-12 bundle was honest and still
misrepresented the work by omission: a clean commit, two files, nine claims
uncertified. sol_bundle.sh now prints the review base, the exact arguments it was
invoked with, a git diff --stat manifest against that base, and the COMPLETE
diff. The caller still chooses which files to append in full; the caller does not
choose the manifest or the diff.

This delta's bundle should be generated with BASE=b099e60, which is the commit
you reviewed for delta 12.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; design quantities only)

  units:                     300
  comparison groups:         240   (225 singleton + 15 canonical)
  min(N0,N1) at unit level:  150
  min(N0,N1) at group level: 115   <- the one that governs power
  compute:                   8,197 fits vs Plan 14.2's ~8,700
                             baselines 6,375 + repairs 1,672 + ablations 150
  multi-role fits:           75, all stream-compatible, 0 duplicated
  tests:                     247 -> 257 passing, 1 skipped
  compute consumed:          0

--------------------------------------------------------------------
WHAT I HAVE NOT BUILT, AND WHY

The grouped critic splitter (W6/W11) and the grouped MDE simulation (W5 Thu).
Both are weeks away and both now have the key they need. I am flagging them as
C-005 and C-006 rather than building them early, because building an MDE
simulation before Week 5's pilot exists would be guessing at the exclusion rate
it is supposed to measure.

NEXT: W3 Mon -- the world-model MLP, development seeds, dynamic-only target, per
your permission to proceed.
=== END UPDATE ===
```
