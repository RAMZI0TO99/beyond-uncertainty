# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–22 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `81781d3` is the last *reviewed* base — there
is still no fully certified commit:

```bash
BASE=81781d3 ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 23.
>
> COVERS SESSIONS:
> - 2026-08-16 (bundle 81781d3 review) · The repair fix that never reached training

```
=== UPDATE FOR SOL ===
DELTA_ID: 23
PREVIOUS_DELTA_ID: 22
DATE: 2026-08-16
SUBJECT: All three confirmed. The second one would have failed every capacity
         repair silently, and my own tests could not have caught it.

--------------------------------------------------------------------
BLOCKER 2 FIRST, because it is the one that mattered.

You said train_ensemble() still takes one unit for both the model and the
streams. Verified, and the failure mode is worse than "inconsistent":

  arm                model hidden   what the repair specifies
  capacity_repair              16                        256

The capacity repair BUILT THE ORIGINAL SMALL NETWORK. Nothing raised. The run
would have completed, logged a validation error, and every capacity condition
would have been labelled "repair failed" -- on a model that was never repaired.
That is a false ground-truth label generated silently, which is the single worst
failure this design can have.

Feature repair failed differently, on the input schema: the pool carried the
restored 30-dim observation while the model was built for the withheld 22.

FIX (D-056): train_ensemble(unit, pools, ..., arm=) resolves the EFFECTIVE unit
for WorldModel and keeps the UNRESOLVED unit for every named stream -- the same
split the pools already had. Verified per arm:

  arm                model hidden   obs width   train n
  baseline                     16          30       500
  capacity_repair             256          30       500
  feature_repair               32          30       500   (baseline is 22)
  data_repair                  32          30      2500   (baseline is 250)

And the other half still holds: evaluation actions and agent trajectories are
identical between each repair and its baseline.

WHY MY TESTS COULD NOT HAVE CAUGHT IT: they tested COLLECTION. The defect was in
TRAINING. Your instruction to add one-epoch training tests per arm is exactly
the gap -- those now exist, parametrised over all four arms.

--------------------------------------------------------------------
BLOCKER 1 -- CONFIRMED. I said the override path was closed. It was closed in
one of two places.

  collect(unit, 99, stage="exp1", seed=1000)                     -> 99  NOT BLOCKED
  collect(unit, 99, stage="exp1", seed=1000, pool="evaluation")  -> 99  NOT BLOCKED

A confirmatory evaluation pool of arbitrary size, reachable directly. FIX:
expected_size(effective, pool, episode_length) gives each pool exactly one legal
confirmatory size and collect() enforces it itself. Tested on DIRECT calls for
all three pools; development seeds are still free to choose.

--------------------------------------------------------------------
BLOCKER 3 -- CONFIRMED. A repaired dataset could not reconstruct its own stream.

TransitionDataset.unit held the effective unit; the stream was keyed on the
unresolved one; and neither the source unit, the arm nor the stage was recorded.
So a feature-repair dataset was genuinely indistinguishable from a baseline
whose unit already had those features -- exactly as you said.

Now recorded and round-tripped: source_unit, effective unit, arm, stage, pool,
episode_length, stream_version. Tested per arm.

--------------------------------------------------------------------
WORDING, both corrected.

The granularity guard is a guard on train_ensemble(), NOT proof that every
confirmatory path is closed. bootstrap_episodes() plus train(train_index=...)
still bypasses it, and the confirmatory runner must own the rule when it exists.
The error message itself now says this, so the next reader of that code does not
inherit my overstatement.

And 9bdb22a was a REVIEWED base, not a fully certified commit. There is still no
fully certified commit. Corrected in the delta header and in CLAUDE.md.

--------------------------------------------------------------------
NUMBERS
  capacity repair, model hidden:     16 -> 256   (was silently unrepaired)
  feature repair, input width:       22 -> 30
  data repair, training transitions: 250 -> 2500
  confirmatory size guard:           now in collect(), all three pools
  dataset provenance fields:         7, round-tripped, tested per arm
  tests:                             367 -> 385 passing, 1 skipped
  compute consumed:                  0 GPU-hours

NEXT: the W3 Friday development pilot on development seeds, which you have
permitted. Confirmatory execution and repair validation stay blocked until you
have bundled these.
=== END UPDATE ===
```
