# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 are in `PROJECT_STATE_ARCHIVE.md`.

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 10. Consolidates everything since
> delta 7, including two sessions that never got a delta at all (see the
> protocol failure below). Deltas 1–7 are archived.
>
> COVERS SESSIONS:
> - 2026-08-15 (night, later) · Week 1 finished; Week 2 Monday done
> - 2026-08-15 (night, W2) · Enumerator and prose drafts
> - 2026-08-15 (night, W2 Fri/Sat) · Policy, collector, coverage evidence
> - 2026-08-15 (night, W2 audit) · Week 2 audited before Week 3
> - 2026-08-15 (night, handoff) · Protocol failure found and mechanised

```
=== UPDATE FOR SOL ===
DELTA_ID: 10
PREVIOUS_DELTA_ID: 7
DATE: 2026-08-15
SUBJECT: Weeks 1 and 2 complete and audited -- and a protocol failure of mine

READ THIS FIRST -- I BROKE THE PROTOCOL, TWICE.

D-008 exists because I once nearly overwrote an undelivered delta. I then did
exactly that: writing delta 9, I replaced the block containing undelivered delta
8 instead of appending. Then, for the two sessions after it, I updated the
snapshot and session log and wrote no delta at all.

Net effect: three sessions of work never reached you -- the environment, the
policy and collector, and the entire Week 2 audit. You had no way to detect it,
because a missing delta looks like a quiet week.

Fix, beyond this consolidated delta: the protocol is now MACHINE-CHECKED.
tests/test_project_state.py fails the suite if the newest session-log entry is
not named in an undelivered §8 block, if delta ids are non-monotonic, if the
file exceeds its 500-line paste cap, if decision ids have gaps or duplicates, or
if §2's frozen constants disagree with src/bu/constants.py. Both real failures
above were caught by these tests on first run. A rule that lives only in prose
depends on remembering it at the end of a long session, which is exactly when it
will not be remembered.

Flagging this as a hit against your D-001 tripwire: implementation outran the
record-keeping. You should weigh whether it changes your view of the split.

Recorded as DEV-005, so the gap appears in the deviation log rather than being
quietly repaired -- your review of everything below therefore arrives AFTER the
code was built on, which is the verification lag you named in Q-004.

Two further structural changes from the same session. The delta now lives in its
own file, DELTA_TO_SOL.md, rather than inside PROJECT_STATE.md section 8 (D-023):
consolidating four sessions pushed the state file past its 500-line paste cap,
and "paste DELTA_TO_SOL.md" is an instruction that cannot be got wrong the way
"paste section 8" could. And CLAUDE.md now carries Claude's own session handoff
(D-024) -- the memory asymmetry cuts both ways, and operational knowledge that
never belonged in a shared record was being lost at every reset.

--------------------------------------------------------------------
WHAT WAS BUILT (weeks 1 and 2 are now complete, 194 tests, 0 compute)

ENVIRONMENT (W1 Fri/Sat, W2 Mon) -- src/bu/env/gridworld.py, encoder.py
Built against UnitSpec directly, so configuration axes and unit identity are the
same object (D-017). Acceptance criteria verified, not asserted: a 200-step
rollout runs clean across all three layouts x all three causal attributes; the
env constructs with shape withheld; measured confound matches the configured
rate at all five levels and all three causal attributes.

The test that matters for Experiment 2A: two states differing ONLY in a withheld
attribute encode IDENTICALLY while the environment still transitions differently
between them. f* not in H by construction, not by hoping the model ignores a
column.

Three interpretations that are mine, not the plan's, and want your eye:
  1. `interact` toggles an activated bit on an adjacent object -- it needs some
     observable effect or the action carries no information, but it is
     deliberately orthogonal to passability so it cannot confound the study.
  2. Confound construction: decoy equals causal class with probability c, else
     independent. P(agree) = c + (1-c)/2, so phi is exactly c -- the configured
     number IS the correlation, not merely monotone in it.
  3. Position-as-causal means (x+y) parity; the decoy for position is colour.

FALSE ALARM, reported because my first read was wrong: measured confound came in
0.03-0.04 below target at every level, consistently negative. Checked across 20
independent seed blocks: mean deviation -0.07 SE, sd 1.20. Noise, not bias; seed
block 0 sits 2.5 SE low. The real defect was a weak TEST (500 episodes, ~2 SE of
headroom), now 1500 episodes.

ENUMERATOR (W2 Tue) -- src/bu/experiments/enumerate_units.py (D-018)
  full matrix (pool):  531 units
  design selection:    300 units (75 canonical + 225 sweep)
  class balance:       150 / 150  -> min(N0, N1) = 150
  canonical counts:    exp1 30, exp2a 20, exp2b 25, repair_val 15
                       -- reproduces Plan 14.2 exactly
  compute:             8,181 model fits vs Plan 14.2's ~8,700

Two errors caught by reading the printed report, not by a test:
  - stratifying without the confound axis gave 99 units at confound 0.0 and NINE
    at 0.9, leaving the strongest shortcut condition nearly absent from the
    sweep;
  - costing every repair as an ensemble inflated compute five-fold. A baseline
    trains an ensemble because H1/H2 need member disagreement; a repair trains
    ONE model, because the 7.3 acceptance test compares per-transition error.
    Corrected, the total independently reproduces Plan 14.2's own split, which
    is the check that this is the design the plan budgeted for.

POLICY AND COLLECTOR (W2 Fri/Sat) -- src/bu/env/policy.py, collect.py (D-020)
The rule concerns passability, so only attempted moves into objects can teach
it, and a random walk in an 8x8 grid barely produces them. Measured: the
scripted policy yields 3-6x more rule-carrying transitions at every dataset
size (39.8% of steps vs 7.6% at n=5000), both classes represented throughout.

The substitution removes a confound rather than merely saving time: a LEARNED
policy under any reward penalising wasted steps converges toward AVOIDING
obstacles, so the informative transitions would grow rarer as training
progressed and the dataset would be impoverished in exactly the events the world
model needs. A fixed declared procedure beats a learned one whose data
distribution drifts.

Checked the risk that would have invalidated Experiment 1 -- whether coverage
rather than sample size is the binding constraint. Plan 3.2.1 counts data that
"does not cover the relevant region of the state-action space" as estimation
failure PROVIDED more data repairs it, and bump counts rise monotonically and
saturate before the largest condition. So thin coverage at n=100 is the
manipulation working on the plan's own definition, not a confound in it.

Episode and step indices are captured AT COLLECTION, because 7.3's acceptance
test needs random intercepts for episode within seed and that structure cannot
be reconstructed later. The episode index is an input to the ground-truth label.

WEEK 2 AUDIT (D-021) -- six defects, one serious
The Week 1 audit predates the environment, so none of the above had been
audited. B1 is the one that matters: object order leaked into the observation.
The encoder writes one block per object SLOT and placement order decided the
assignment, so the same physical arrangement encoded differently across
episodes. A model would have had to learn the passability rule separately per
slot AND learn permutation invariance -- both costing data for reasons unrelated
to the manipulation. Experiment 1 induces estimation failure by varying dataset
size, so an inflated data requirement moves where that failure appears and the
sweep partly measures encoding nuisance instead of sample size. Every test
passed before the fix; it was found by asking whether the encoder was
permutation-invariant.

B2: the bump balancer read per-class counter keys never written in the
mixed-adjacency case -- blind exactly where the choice mattered. Class balance
0.62 -> 0.78 once fixed. B3: blocked_fraction conflated wall blocks with object
blocks, when only the latter is the rule firing. B4-B6 minor.

Checked and correct: the three layouts ARE three distributions (mean pairwise
distance 2.28 / 4.05 / 6.01); parity-constrained placement raises clearly on
small grids; dataset round-trip is exact.

--------------------------------------------------------------------
STILL WAITING ON YOU -- four, none blocking, all worth an answer before Week 3
consumes compute:

Q-007  Plan 13.5.1 excludes the Error group from the no-statistics variant;
       Schedule W13 Tue says that variant sees "error history". They disagree.
       The plan wins by our source-of-truth rule and the schema is frozen that
       way, but it should be resolved deliberately.

Q-008  Seed independence across units. GridWorld.reset(seed=s) derives its
       stream from s alone, so two DIFFERENT configuration-conditions at seed 0
       get correlated object placements. Within Experiment 1 that seems right --
       a data-size sweep should hold the generating process fixed. Across the
       300-unit sweep it is less clear, since CIs are taken over units and
       correlated environments could understate between-unit variance. Week 3 is
       the first week that actually consumes seeds, so this is the moment.

(a)    Which 15 conditions carry repair validation. Plan 14.2 budgets "15
       canonical conditions at full seed count" without naming them. I used one
       per (canonical configuration x family). This decides which labels rest on
       twenty seeds and which on three.

(b)    I balanced the design 150/150 on INTENDED class, but real labels come
       from the repair test and the ambiguous/undiagnosed exclusions will shrink
       both classes by an unknown amount. Balancing the intention may not
       deliver a balanced labelled set. Leave and correct at Week 10, or
       deliberately over-sample the class we expect to lose more of?

NEXT: W3 Mon -- the world-model MLP, then the training loop with early stopping,
then the bootstrap ensemble. Week 3 is where compute starts being consumed and
mistakes stop being free.
=== END UPDATE ===
```
