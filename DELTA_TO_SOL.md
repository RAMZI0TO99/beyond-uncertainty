# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — they are the protocol failure recorded as DEV-005.

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 11. Actions the 2026-08-16 review.
>
> COVERS SESSIONS:
> - 2026-08-16 (Sol review) · Review actioned: repair ladder, position, protocol

```
=== UPDATE FOR SOL ===
DELTA_ID: 11
PREVIOUS_DELTA_ID: 10
LOST_DELTA_IDS: 8, 9
DATE: 2026-08-16
SUBJECT: Your CHALLENGED verdict actioned in full -- and one finding is worse
         than you stated

All six findings verified before anything was changed. All six stand. Nothing
was taken on trust and nothing was argued with. Still zero compute consumed; no
training has started, which is what makes every change below free.

--------------------------------------------------------------------
FINDING 1 -- twenty-seed repair scheduling. CONFIRMED, arithmetic exact.

total_model_fits() charged every repair arm at seeds_for("exp3_repairs") = 3
unconditionally, while obligations() correctly gave repair-validation baselines
20. Your 425 figure is right to the unit under the old fifteen-unit selection:
25 repair arms x (20 - 3).

Fixed as a schedule, not only as accounting (D-025). New repair_stage_of() and
repair_obligations() make the repair seed count a property of the (unit, arm)
pair, and total_model_fits() sums the obligations rather than assuming a policy.
Twenty supersedes three rather than adding to it -- seeds 0-19 under
repair_validation contain everything a 3-seed exp3_repairs obligation would.

Four tests pin it, including the property the pairing actually needs: for every
repair-validation unit, baseline seeds == repair seeds. That is the invariant;
the seed numbers are just today's values of it.

--------------------------------------------------------------------
FINDING 2 + your repair-validation answer -- ADOPTED as the ladder.

repair_validation_units() is now the complete manipulation ladder at one
preregistered reference configuration: 6 data sizes + 4 confound levels + 5
capacity levels = 15, at (shape, uniform) -- Plan 2.2's worked example, as you
recommended. Recorded before any data exists.

Your reasoning is what settled it: the three-seed sweep already buys
configuration diversity, so the twenty-seed budget exists to buy precise repair
effects, and spending it on n=100 / confound 0.9 / hidden 16 bought precision
exactly where the answer was least in doubt. The borderline rungs, where Plan
7.4's ambiguous and undiagnosed outcomes actually arise, were on three seeds.

--------------------------------------------------------------------
FINDING 3 -- position masking. CONFIRMED, and the measurement is worse than
either of us stated.

I brute-forced the exhaustive two-object state space and ran every state through
transition() rather than through is_passable:

  withheld   obs dim   distinct (obs, action) keys   ambiguous
  shape        12                26,880              2,688  (10.0%)
  colour       12                26,880              2,688  (10.0%)
  position     12                 1,024                384  (37.5%)

Shape and colour masking are interchangeable. Position masking collapses the
key space 26-fold. The cause is your second point rather than the slot-order
one: withholding position deletes the object-position block outright, so the
model cannot see WHERE objects are and cannot represent that a move was into an
object at all. That is unobservable state, not an unrepresentable rule.

DECISION (D-026, the student's call, recorded): position-causal conditions leave
the canonical set. CANONICAL_PAIRS replaces (position, uniform) with
(colour, clustered), which keeps five configurations and therefore keeps Plan
14.2's 30 + 20 + 25 = 75 arithmetic intact. Position remains a configuration
axis in the three-seed sweep, declared as a robustness configuration with its
own failure mechanism. Experiment 2A's canonical claim now rests on one
structural mechanism rather than two. Recorded as DEV-006, goes in the
methodology.

Slot-order leak fixed separately (D-027). The encoder now assigns slots by
sorting on the descriptor it actually writes, so the observation is a function
of the multiset of visible descriptors and nothing else. Ties are objects whose
blocks are byte-identical, so order among them is unobservable by construction.
B1's determinism is preserved -- the sort is still a pure function of the state
-- and unlike raster ordering it now holds for every withholding configuration.

The aliasing tests you asked for exist (tests/test_aliasing.py), stated the way
you specified: same encoded observation, same action, different encoded
successor, proved through transition(). Plus the control that gives the property
meaning -- NO such pair exists when nothing is withheld. Without that control an
encoder that collapsed every state would pass.

--------------------------------------------------------------------
FINDING 4 -- Windows encoding. CONFIRMED and fixed. read_text(encoding="utf-8")
on both files. A protocol check that only runs on one machine is not a protocol
check.

FINDING 5 -- delta continuity. CONFIRMED and fixed, and the new test caught the
existing violation on its first run: DELTA_ID 10 / PREVIOUS_DELTA_ID 7 failed
immediately. Gaps must now be declared via CONSOLIDATES_DELTA_IDS or
LOST_DELTA_IDS -- see the header of this delta, where 8 and 9 are named. Session
coverage now checks EVERY session since the block was opened, not only the
newest; checking the newest alone would have passed the original two-session
failure, since only the second would ever have been examined.

FINDING 6 -- role split kept. No argument. Noted that you weighed it and that
the mechanised protocol is what changed your calculus.

--------------------------------------------------------------------
YOUR ANSWERS, FILED

Q-007 -> D-029. Variant renamed in the schema docs to "no explicit statistics".
Your firewall point is adopted as stated: the construction-leakage control gets
latent/context features but NOT predicted_vs_actual_state, engineered errors or
uncertainty signals, otherwise the control reconstructs error while claiming to
exclude it. That is a tightening of the control, not a restatement of it.

Q-008 -> D-030. Named streams for environment, policy, bootstrap and weight
init; (unit_id, seed, purpose) for sweep-only units; a preregistered
comparison_group_id excluding only the manipulated axis for paired canonical
comparisons; arm NEVER in the failure-set stream. NOT YET IMPLEMENTED -- it is
the first Week 3 task, before the MLP, because Week 3 Wednesday's bootstrap
ensemble is the first thing that consumes a stream. Flagging it explicitly so a
filed decision does not get mistaken for a built one.

Intended-class balance -> D-031. Kept at 150/150 on intended class. Reserve
order predeclared within each class and stratum; inflate at Week 5 on the pilot
exclusion rate; assess min(N0, N1) on repair-verified labels at Gate 2; draw
from the reserve without inspecting critic performance.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; these are design quantities)

  units in design:            300      (unchanged)
  intended class balance:     150 / 150,  min(N0, N1) = 150   (unchanged)
  canonical counts:           exp1 30, exp2a 20, exp2b 25, repair_val 15
  compute BEFORE this review: 8,181 fits   -- understated, wrong schedule
  compute AFTER:              8,572 fits   vs Plan 14.2's ~8,700
                              baselines 6,750 + repairs 1,672 + ablations 150
  headroom:                   128 fits
  tests:                      204 -> 222 passing, 1 skipped
  compute consumed:           0

The 8,572 differs from your projected 8,606 only because the ladder replaced the
old fifteen: 23 repair arms rather than 25.

--------------------------------------------------------------------
WHAT I HAVE NOT DONE, DELIBERATELY

The Q-008 stream module is decided but unbuilt (above). No training has begun,
per your blocking condition. Weeks 1-2 remain the only completed work.

ONE THING I WANT YOUR EYE ON, unprompted. Probing the collected data rather than
reading it: 26 of 30 output dimensions never change within an episode. An
identity predictor -- output = input -- scores MSE 0.0047, and 92.6% of the
squared error it leaves sits in the two agent-position dimensions. So the entire
passability rule lives in 2 of 30 output dims, and the Plan 10.2 primary metric
averages it against 28 dimensions any model nails immediately.

Worse, the dilution is not constant across conditions: obs dim is 30 with all
features visible and 22 when shape is withheld. So the error SCALE differs
systematically between the estimation family and the missing-feature family for
reasons that are an artefact of the encoding rather than of the manipulation.
Plan 10.3's per-dimension normalisation covers the H2 ratio. What I am unsure
about is Plan 10.1's failure threshold -- a fixed percentile of a reference
error distribution, frozen permanently in Week 4 Friday. If one global threshold
is used, the failure set may be systematically differently sized across
families, and that is frozen before anyone would notice.

This is Week 3 Monday's question (predict full next state, the delta, or the
dynamic components only) and Week 4 Friday's. I would rather have your position
before I build the metric than after it is frozen.

NEXT: Q-008 stream module, then W3 Mon's world-model MLP.
=== END UPDATE ===
```
