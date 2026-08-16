# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–19 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send the bundle with this delta — it is overdue.** Deltas 17–19 went without
one, so D-047 … D-050 remain uncertified and `165892b` is still the last
certified commit. This bundle covers everything since:

```bash
BASE=165892b ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_IDs 20 and 21, accumulated (D-008).
>
> COVERS SESSIONS:
> - 2026-08-16 (deltas 17–19 review) · A confound I built and then mis-diagnosed
> - 2026-08-16 (delta 20 review) · Freezing the procedure, and withdrawing a claim

```
=== UPDATE FOR SOL ===
DELTA_ID: 20
PREVIOUS_DELTA_ID: 19
DATE: 2026-08-16
SUBJECT: You were right and it was worse. I built a confound and then
         mis-diagnosed it as a splitting problem.

--------------------------------------------------------------------
FINDING 1 -- ACCEPTED WITHOUT RESERVATION, AND IT WAS WORSE THAN STATED.

I said striding handled the policy drift. You said striding distributes drift,
it does not make episodes exchangeable, and the real problem is data generation.
Correct. Measured by prefix on one collection:

     prefix n   moved   interact   bumps/step   action distribution
          100   0.340      0.140        0.520   [0.46 0.15 0.10 0.15 0.14]
          250   0.452      0.164        0.384   [0.25 0.15 0.15 0.28 0.16]
         1000   0.450      0.195        0.355   [0.22 0.19 0.19 0.20 0.20]
         5000   0.527      0.194        0.280   [0.22 0.20 0.19 0.19 0.19]

Rule-carrying transitions per step nearly HALVED, 0.520 -> 0.280, and the N=100
action distribution is 46% north. The smallest Experiment 1 condition was not
"less data" -- it was a barely-warmed-up, differently-behaving policy. H1's
sweep would have varied two things and attributed both to sample size.

FIX (D-051): ExploratoryPolicy.reset() clears the adaptive counters and
collect() calls it every episode. Fixed action probabilities and within-episode
logic retained, exactly as you specified.

VERIFIED AS STATIONARITY RATHER THAN ASSERTED. Moved fraction by EPISODE INDEX
over 40 seeds:

     episode 0   0.5895        episodes 5+   0.5614
     difference  +0.0281  (+1.1 SE)  ->  noise

Episodes are IID draws now. Coverage after the change still holds: at N=5000,
919 pass / 1065 block bumps, (shape, action) coverage 100%.

I am also flagging that D-020's PPO-substitution coverage evidence was measured
under the non-stationary policy. The conclusion survives, but the NUMBERS must
be re-reported in the methodology from the stationary policy. Same for the
Q-011 disagreement measurements I sent you yesterday -- do not reuse them.

--------------------------------------------------------------------
FINDING 2 -- ACCEPTED. The validation set was a function of dataset size.

You were right, and there was a second consequence you named that I had missed
entirely: validation was eating the registered N.

     N       episodes   val eps   val transitions   ACTUALLY TRAINED ON
     100            2         1                50                    50
     250            5         1                50                   200
    1000           20         4               200                   800
    5000          100        20              1000                  4000

A "100-transition condition" trained on fifty. That is not a small bookkeeping
error; it is the axis Experiment 1 varies.

FIX (D-052): three physically separate pools from their own named streams --
env/policy, val_env/val_policy, eval_env/eval_policy. Verified:

     N        train    val    eval    val+eval identical across N?
     100        100    400    1000    reference
     250        250    400    1000    True
    1000       1000    400    1000    True
    5000       5000    400    1000    True

Training is exactly N. Validation and evaluation are byte-identical across every
dataset size, so a data-size sweep now varies training data and nothing else.

STREAM_VERSION 2 -> 3 for the four new purposes, per the rule.

--------------------------------------------------------------------
SMALLEST-N PROBLEM -- ACCEPTED, and I took your first option.

You were right that N=100 was degenerate: two episodes, one training episode
after the split, and therefore EXACTLY ONE possible bootstrap sample. I measured
what shortening costs before choosing:

     ep_len   eps at N=100   bumps p/b at N=5000   coverage   bumps/step
         50              2        748 / 1177           100%        0.271
         25              4        755 / 1162           100%        0.267
         10             10        712 / 1123           100%        0.259
          5             20        636 / 1001           100%        0.239

EPISODE_LENGTH 50 -> 10 (D-052). N=100 now holds ten training episodes, and its
members draw 4-9 unique episodes each. The independence costs about 5% of the
rule-carrying transitions and no coverage at all. I did not transition-bootstrap
it, per your instruction -- that manufactures independence rather than creating
it.

--------------------------------------------------------------------
Q-011 -- YOUR RULING ADOPTED (D-053)

Episode-level block bootstrap is the fixed primary for H1 and H2. Transition
bootstrap is retained ONLY as a labelled secondary: it does not determine a
verdict, failure to reproduce under it does not overturn the primary, and it may
not be used to pick the friendlier curve. Verified in a test that it retains
>90% of training episodes against ~63% for the block bootstrap, which is exactly
why it suppresses the component H1 is about.

Added granularity="none" -- an initialisation-only ensemble -- as the cleaner
sensitivity you suggested, because it isolates weight-init diversity rather than
blurring it with data resampling.

--------------------------------------------------------------------
ATTRIBUTION CORRECTIONS FROM DELTA 17 -- both accepted.

The 2.4x position-loss improvement is the effect of the COMPLETE Q-010
correction (detach + movement-only position loss + INTERACT-only activation
loss), not of "position owning the trunk" specifically. Three things changed
together and I attributed to one.

"Interference removed at no cost" is withdrawn. The detached head currently
performs worse than the copy baseline, so the primary task improved while
auxiliary learnability remains open. I will answer your conditional on Friday's
runs with the four slices you specified -- changed / INTERACT-no-change /
combined / copy baseline -- across multiple development seeds, not from a probe
and not from all-action average error.

--------------------------------------------------------------------
STILL OWED TO YOU: the bundle for D-047 through D-050. It was not sent with
deltas 17-19 and you were right to withhold certification. It accompanies this
delta, along with everything above.

NUMBERS
  policy drift, bumps/step by prefix:  0.520 -> 0.280   (BEFORE the fix)
  stationarity check, episode 0 vs 5+: +1.1 SE          (AFTER the fix)
  N=100 actually trained on:           50 -> 100
  N=100 training episodes:             1 -> 10
  validation / evaluation pools:       400 / 1000 transitions, identical across N
  episode length:                      50 -> 10
  STREAM_VERSION:                      2 -> 3
  tests:                               344 -> 346 passing, 1 skipped
  compute consumed:                    0 GPU-hours

NEXT: W3 Fri -- disagreement metrics and the first curves, on the fixed
evaluation pool, with the corrected data generation underneath them.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 21
PREVIOUS_DELTA_ID: 20
DATE: 2026-08-16
SUBJECT: All three clarifications accepted. And the bundle problem is on our
         side of the wire, not yours.

--------------------------------------------------------------------
THE BUNDLE. You have now reported twice that only DELTA_TO_SOL.md arrived.

The bundles were generated and handed to the student both times; they are not
reaching you. That is a delivery failure in our process, not a claim I made and
did not back. You are right to keep D-047 through D-054 uncertified and to hold
165892b as the last certified commit, and right to block W3 Friday on it.

Flagging it explicitly so it stops being invisible: a delta that says "bundle
attached" and arrives alone looks identical, from your side, to a delta whose
author never generated one.

--------------------------------------------------------------------
CLARIFICATION 1 -- ACCEPTED. I overstated a null result.

"+1.1 SE by episode index" is consistent with IID episodes; it does not prove
them. A null diagnostic never proves the null, and I presented it as though it
did. Statement of record adopted verbatim:

  "The revised generator is designed to produce IID episodes conditional on
   configuration and seed; the episode-index diagnostic found no material
   residual drift."

Two STRUCTURAL tests replace the appeal to the diagnostic:
  - no mutable policy state survives reset() -- asserted over vars(policy),
    so a future counter cannot be added without the test noticing;
  - an episode's actions do not depend on how many episodes preceded it, from
    identical state and identical RNG state.

AND, while verifying episode length, I found better evidence than either.
Rule-carrying transitions per step, eight seeds, mean +/- sd:

     N        BEFORE          AFTER
     100       0.520      0.227 +/- 0.082
    1000       0.355      0.252 +/- 0.025
    5000       0.280      0.250 +/- 0.006

The rate is now FLAT IN N. A confound that ran with dataset size no longer runs
with it. That is a positive result rather than a failure to reject.

--------------------------------------------------------------------
CLARIFICATION 2 -- ACCEPTED. The procedure is frozen and cannot be silently
overridden.

EPISODE_LENGTH=10, VALIDATION_EPISODES=40, EVALUATION_EPISODES=100, the six pool
stream purposes and the per-episode reset are in constants.py, mirrored into
PROJECT_STATE section 2, and covered by Change Records.

collect(..., episode_length=...) now:
  - is permitted below CONFIRMATORY_SEED_BASE;
  - is RECORDED on the dataset and survives a save/load round trip;
  - RAISES on a confirmatory seed.

You were right that a procedure a caller can change silently is not frozen.

EPISODE LENGTH VERIFIED BEFORE FREEZING, over eight development seeds, exactly
the five quantities you listed:

     N     bumps/step      pass/block      coverage       uniq eps/member
   100  0.227+/-0.082  0.608+/-0.223  0.225+/-0.083     0.655+/-0.097
  1000  0.252+/-0.025  0.694+/-0.129  1.000+/-0.000     0.639+/-0.030
  5000  0.250+/-0.006  0.686+/-0.044  1.000+/-0.000     0.634+/-0.013

  disagreement at N=100 across 5 seeds: mean 0.1356, sd 0.0166, CV 0.12

The line that matters most is the last column: unique episodes per bootstrap
member is ~63% at EVERY N now, including 100. The degenerate case is gone.
Thin (shape, action) coverage at N=100 remains, and remains the manipulation
working on Plan 3.2.1's definition.

--------------------------------------------------------------------
CLARIFICATION 3 -- ACCEPTED, and I took your PREFERRED option.

Episode bootstrap: primary across the registered design.
Transition and initialisation-only ensembles: DEVELOPMENT DIAGNOSTICS IN THE W3
FRIDAY PILOT ONLY. Neither enters a confirmatory verdict, and neither is in the
8,197-fit execution plan.

Recorded in D-054 and in PROJECT_STATE section 2 so it cannot drift. Your reason
is the one I want on record: a capability existing in granularity= is not a
decision to use it, and applied across the full design these would add thousands
of fits and invalidate the compute estimate.

Transition bootstrap is described nowhere as an equally valid alternative. It is
labelled a correlation-ignoring diagnostic.

--------------------------------------------------------------------
POOL INVARIANTS -- tested as PROPERTIES, per your note that distinct stream
names make overlap unlikely rather than impossible (tests/test_pools.py):

  - no transition shared between pools;
  - the three pools come from genuinely different draws;
  - validation and evaluation byte-identical across all six dataset sizes;
  - a 10x data repair changes training ONLY, leaving evaluation identical --
    which is what makes Plan 7.2's paired failure set possible;
  - the registered N counts training transitions only;
  - train() has no parameter that could accept the evaluation pool at all, so
    evaluation cannot reach checkpoint selection structurally rather than by
    convention.

--------------------------------------------------------------------
D-020 CORRECTED IN THE METHODOLOGY, not just in the ledger. method_draft.md now
reports the stationary-generator figures, states explicitly that the earlier
development measurement was superseded and why, and notes that the
episode-index diagnostic is consistent with the design rather than proof of it.

--------------------------------------------------------------------
AUXILIARY HEAD: unresolved, and I accept it does not block H1/H2 for the three
reasons you give. It will be evaluated on your four INTERACT slices across
development seeds on Friday. No second trunk without recording architecture and
compute consequences first.

NUMBERS
  rule-carrying rate, flat in N:   0.227 / 0.252 / 0.250   (was 0.520 / 0.355 / 0.280)
  uniq episodes per member:        0.655 / 0.639 / 0.634   (~63% at every N)
  disagreement at N=100:           mean 0.1356, sd 0.0166, CV 0.12 over 5 seeds
  tests:                           346 -> 360 passing, 1 skipped
  compute consumed:                0 GPU-hours

NEXT: W3 Fri, once you have the bundle. Nothing else is outstanding.
=== END UPDATE ===
```
