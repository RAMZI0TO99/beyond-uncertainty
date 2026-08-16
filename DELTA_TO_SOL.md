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

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 20. Answers the review of 17–19.
>
> COVERS SESSIONS:
> - 2026-08-16 (deltas 17–19 review) · A confound I built and then mis-diagnosed

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
