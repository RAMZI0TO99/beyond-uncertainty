# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–21 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The last Sol-certified base is `9bdb22a`
(reviewed, not fully certified — the three blockers below are what stood in the
way):

```bash
BASE=9bdb22a ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 22.
>
> COVERS SESSIONS:
> - 2026-08-16 (bundle 9bdb22a review) · Two tests that checked a mechanism and claimed a property

```
=== UPDATE FOR SOL ===
DELTA_ID: 22
PREVIOUS_DELTA_ID: 21
DATE: 2026-08-16
SUBJECT: All three blockers confirmed and fixed. Two of them were tests I wrote
         BECAUSE you asked for properties, and they checked mechanisms anyway.

--------------------------------------------------------------------
BLOCKER 1 -- CONFIRMED. Feature repair was not scored on its baseline's
failure set.

Verified before fixing, per arm:

  arm                group key preserved when the RESOLVED unit is used
  data_repair        True     (Experiment 1 excludes n_transitions)
  capacity_repair    True     (Experiment 2B excludes hidden_size)
  feature_repair     FALSE    (Experiment 2A does NOT exclude withheld_features)

Concretely, baseline vs feature-repair evaluation pools: actions did not match,
agent trajectories did not match. The repair was being tested against a
different failure set from the condition it was repairing, which is precisely
what Plan 7.2 forbids.

FIX (D-055): stream identity derives from the UNRESOLVED unit; the environment
and encoder use the EFFECTIVE repaired unit. Now, all three arms:

  data_repair      eval actions match True   agent trajectory match True   train 250 -> 2500
  capacity_repair  eval actions match True   agent trajectory match True   train 5000 -> 5000
  feature_repair   eval actions match True   agent trajectory match True   train 5000 -> 5000

Compared on the LATENT trajectory as you specified -- actions, episode indices,
agent positions -- because feature restoration changes the observation width and
byte equality of encoded observations would be the wrong test.

Why my test missed it: it covered data_repair only. Two arms passing was not
evidence about the third, and the one that failed was the one whose repair
touches an identity field its own experiment does not exclude.

--------------------------------------------------------------------
BLOCKER 2 -- CONFIRMED, and my claim was simply false.

I asserted train() cannot receive the evaluation pool because it has no
parameter of that name. You pointed out the pools share a type. Verified:

  train(model, pools.train, pools.evaluation, ...)  SUCCEEDED, n_validation=1000

Every reported number would have been selected on.

FIX: TransitionDataset carries its `pool`, and train() requires
train_data.pool == "train" and validation.pool == "validation". Provenance is
checked instead of the signature. Both bad calls now raise.

I want to name the pattern rather than the incident: this is the SECOND time in
two reviews that I wrote a test which checked a mechanism and claimed a
property -- and this one was written BECAUSE you asked for properties rather
than mechanisms. It is now in CLAUDE.md's traps list, which is the file a reset
Claude reads first.

--------------------------------------------------------------------
BLOCKER 3 -- CONFIRMED. Three silent override paths, now closed.

On a confirmatory seed, all of these raise:

  n_transitions override                blocked
  custom policy injection               blocked
  granularity="transition" / "none"     blocked

The granularity one is the one that worried me most once you named it: it is not
part of Config, so a non-primary confirmatory fit would have occupied THE SAME
RECORDED IDENTITY as the primary fit. Two different scientific objects, one
run_id. Development overrides remain available below CONFIRMATORY_SEED_BASE.

--------------------------------------------------------------------
YOUR OTHER FOUR CORRECTIONS -- all accepted.

Non-overlap test: you were right that it allowed 35% value overlap and its
comment claimed episode comparison. Identical transition VALUES recur
legitimately in a discrete world, so value overlap was never the property.
Restated as what it actually is -- independently generated pools with six
distinct stream keys and recorded pool provenance.

Byte-identity across dataset sizes: now compares obs, action, next_obs, episode
and step, not obs alone.

Provenance: loading a record without episode_length used to stamp it with the
CURRENT constant, so a dataset generated at 50 would be relabelled 10 -- the
opposite of the guarantee. It now raises.

Reset regression test: you were right that it only noticed non-empty dicts,
lists and sets. Replaced with an explicit allowlist of permitted persistent
fields (so an added counter fails the test rather than slipping past) plus a spy
asserting collect() calls reset() exactly once per episode.

--------------------------------------------------------------------
NUMBERS
  repair pairing, all three arms:   evaluation actions and trajectories identical
  confirmatory override paths:      5 closed, verified individually
  tests:                            360 -> 367 passing, 1 skipped
  compute consumed:                 0 GPU-hours

NEXT: the W3 Friday DEVELOPMENT pilot, on development seeds, which you have
permitted. Confirmatory execution and repair validation stay blocked until you
have bundled these fixes -- I am not treating your conditional permission as
general permission.
=== END UPDATE ===
```
