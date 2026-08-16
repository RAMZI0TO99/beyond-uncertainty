# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–26 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `2875e60` is the **certified** base:

```bash
BASE=2875e60 ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_IDs 27 and 28, accumulated (D-008).
>
> COVERS SESSIONS:
> - 2026-08-16 (delta 26 review) · Two claims withdrawn, and a better mechanism found
> - 2026-08-16 (W3 audit) · Seven defects, one of which moves a registered endpoint

```
=== UPDATE FOR SOL ===
DELTA_ID: 27
PREVIOUS_DELTA_ID: 26
DATE: 2026-08-16
SUBJECT: You were right on all four. Two of my claims are withdrawn, and the
         measurement you forced is a better result than the one I reported.

--------------------------------------------------------------------
WITHDRAWN 1 -- that was not the registered H2 ratio.

Plan 10.3 defines the endpoint over a condition's FAILURE SET. The pilot took
every movement transition, and the W4 Friday threshold does not exist yet. So
0.462 is an EXPLORATORY WHOLE-POOL disagreement/error ratio and calling it "the
H2 signature" was wrong.

Relabelled in the printed report, the methodology paragraph and the ratio
column's footnote -- in the artefacts themselves, not only in the ledger, so the
number cannot travel without the qualifier.

WITHDRAWN 2 -- "estimation failure" was a construction label.

Plan 7.1 labels a condition by what repairs it, established by the
counterfactual protocol. Repair validation has not run. My sentence asserted
both halves without either. Now "small-data condition" and "estimation-DESIGN
condition" throughout.

--------------------------------------------------------------------
THE INVALID INFERENCE -- and this is where your review earned its keep.

I compared the sd of the ENSEMBLE MEAN against the targets' and concluded the
members had "all collapsed toward the same near-constant". You pointed out that
members which vary can cancel in their average. Verified with a constructed
counterexample:

     ensemble-mean prediction sd : 0.0512
     individual member sd (mean) : 2.5561

The inference simply does not go through.

MEASURED PER MEMBER, the answer is different and better. Member prediction sd as
a fraction of the targets':

     N     ensemble mean   least-contracted   most-contracted
   100             0.231              0.639             0.219
   250             0.538              0.836             0.220
   500             0.737              0.832             0.738
  1000             0.823              0.904             0.813
  2500             0.899              0.921             0.893
  5000             0.950              0.974             0.939

It is HETEROGENEITY, NOT COLLAPSE. At N=100 most members contract sharply but at
least one keeps 64% of the target's variation, and the ensemble mean is flatter
than any individual member -- so part of its flatness really was cancellation,
exactly as you said. At N=250 the spread across members is widest, 0.220 to
0.836, and that is precisely where disagreement peaks: members disagree most
when some have learned the rule and others have not. By N=5000 they have
converged and disagreement is low because they are all right rather than because
they are all flat.

That is a cleaner mechanism than the one I claimed, and I would not have found
it without the correction.

--------------------------------------------------------------------
PER-TRANSITION EXPORT -- was missing, now exists.

You are right that the schedule requires it literally and rows.json held only
summaries. per_transition_table() now writes error, disagreement, predictive
variance, episode and step per transition, one file per (N, seed), 18 files. The
90 fits WERE RERUN, since the predictions had not been retained -- as you
anticipated.

Summaries are now derived from the transition table rather than standing in
for it.

--------------------------------------------------------------------
STATISTICAL WORDING -- corrected.

"The N=250 sd is smaller than the gap" does not establish anything about seed
artefacts. Paired within-seed differences, disagreement(250) - disagreement(100):

     seed 0   +0.1794
     seed 1   +0.3598
     seed 2   +0.1017

The direction reproduced in all three development seeds. That is the whole
claim, and the report now says exactly that and no more.

--------------------------------------------------------------------
CODE AND TEST CORRECTIONS -- all four.

  - assert -> ValueError. You are right that assertions vanish under -O and are
    not a safety boundary.
  - The pairwise-convention docstring claimed ordered and unordered means differ
    by a factor of two. They are IDENTICAL when each is normalised by its own
    pair count; verified against an explicit enumeration. The two-member test
    could not have distinguished them, as you said -- it now enumerates at k=5.
  - The denominator-floor test had zero error AND zero disagreement, so it never
    exercised the floor. It now places members symmetrically around the targets:
    error exactly zero, disagreement large, ratio == numerator / 1e-6.
  - uncertainty.py no longer claims to implement all of 10.3. The per-condition
    error/disagreement correlation is not implemented and is named as absent.

--------------------------------------------------------------------
WHAT SURVIVES FROM D-058, stated plainly so the record is not ambiguous:
the curves; the non-monotone disagreement; the paired direction across three
seeds; and that a small-data condition showed the lowest whole-pool ratio in the
sweep. WHAT DOES NOT: that it was the H2 signature, that the condition is a
verified estimation failure, and that the members collapsed.

NUMBERS
  member sd / target sd at N=100:   0.219 to 0.639  (NOT uniform collapse)
  paired disagreement deltas:       +0.179, +0.360, +0.102
  per-transition files exported:    18
  tests:                            410 -> 413 passing, 1 skipped
  compute consumed:                 0 GPU-hours
  certified base:                   2875e60, unchanged

NEXT: W4 Mon -- the trend test, read knowing the curve is non-monotone at the
small end.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 28
PREVIOUS_DELTA_ID: 27
DATE: 2026-08-16
SUBJECT: Week 3 audited. Seven defects. One of them moves the registered H2
         endpoint, and your auxiliary conditional is now answered.

--------------------------------------------------------------------
WHY AN AUDIT WHEN YOU HAVE REVIEWED NINE TIMES

D-015 and D-021 each found defects the suite was green on, and both ran before
the next week began. Your reviews and an audit find different classes of thing:
you review what I REPORT plus a diff, and cannot probe running code. Every worst
defect in this project was found by asking a question of the running system.

--------------------------------------------------------------------
W3-1 -- SERIOUS, AND IT IS YOURS TO RULE ON.

Plan 10.3 requires per-dimension normalised error. It never says WHICH SET
defines the normalisation. The code recomputed the scale from whatever targets
it was handed.

I assumed the ratio was invariant to this -- numerator and denominator share the
scale, so it should cancel. IT DOES NOT, because the scale is a VECTOR, not a
scalar: dividing each dimension by a different amount reshapes both vectors and
their norms do not share a common factor. Measured on pilot data:

  failure set   ratio (pool scale)   ratio (subset scale)   diff
        100%              0.9865                 0.9865     0.0%
         20%              0.5920                 0.5999     1.3%
         10%              0.5120                 0.5287     3.3%
          5%              0.4348                 0.4548     4.6%

  pool scale   [0.229, 0.224]
  top-5% scale [0.294, 0.348]

So the REGISTERED H2 ENDPOINT moves by up to 4.6% with a choice nobody made,
and W4 Friday's failure set is exactly such a subset. H2's verdict compares
ratios across families, so a wobble of that size in the endpoint is not
cosmetic.

I have made the scale an explicit parameter defaulting to the current
behaviour, and pinned it to the evaluation pool in the pilot. But WHICH set
defines it is a preregistration question, not an implementation one. My
recommendation is the full evaluation pool, fixed once per condition, so that
restricting to a failure set changes what is measured but not the units it is
measured in. I would rather you ruled than that I chose.

--------------------------------------------------------------------
W3-2 -- SERIOUS. The pilot had no provenance.

It wrote bare JSON and .npz, bypassing RunLogger entirely: no commit hash, no
dirty flag, no package versions, no seed_partition. Plan 13.7 requires every
figure regenerable from logs WITH the provenance that explains them, and Week 1
built exactly that machinery. Now routed through RunLogger -- 90 member records
over 18 runs, each carrying commit, dirty flag, 8 package versions and
partition=development.

W3-4 -- SERIOUS AND LATENT. member_predictions left every model in eval mode.

Inert for this MLP. But Plan 9.3 plans MC-DROPOUT as reliability-gate fallback
B2 -- "dropout at test time". Under that estimator a model silently left in eval
mode returns DETERMINISTIC predictions with EXACTLY ZERO DISAGREEMENT. That
would read as "MC-dropout also fails H1" and trigger a false pivot at the very
gate the fallback exists for. Mode is now saved and restored.

W3-6 -- MATERIAL. train_index was unvalidated, and torch WRAPS negative indices
silently: x[[-1]] returns the last row rather than raising. A resample producing
one would train on the wrong rows; the error it actually produced was "no
interact transitions", which points nowhere near the cause.

W3-3 (activation report used 1 member of 5), W3-5 (dead val_fraction knob after
D-052), W3-7 (dead import). All fixed, all with regression tests.

--------------------------------------------------------------------
CHECKED AND CORRECT -- half the value of an audit is the list that did not move.

Checkpoint restoration on all three exit paths; patience counting from the best
epoch; five members sharing no bootstrap, init or batch stream before OR after
training; member results independent of ensemble_size; Experiment 1's training
pools still EXACT nested prefixes after the three-pool restructure; the data
repair extending rather than redrawing; validation and evaluation byte-identical
across sizes AND arms; ZERO shared (obs, action) pairs between training and
evaluation; action-conditional passthrough correct for all five actions and
row-wise on mixed batches; trunk isolated under predict_next_obs as well as
losses; the block bootstrap genuinely duplicating whole episodes (multiplicities
1-4, 63% distinct); the final partial minibatch used; no NaN or inf; 300 units,
150/150, 8,197 fits unchanged; and every per-transition export reproducing its
summary exactly.

--------------------------------------------------------------------
YOUR AUXILIARY CONDITIONAL (D-047) -- ANSWERED, ACROSS ALL FIVE MEMBERS.

     N    copy baseline   members mean   best member   beats copy
   100           0.1693         0.4613        0.3766        0 / 3
   250           0.1693         0.3171        0.2248        0 / 3
   500           0.1693         0.2499        0.2268        0 / 3
  1000           0.1693         0.2545        0.2381        0 / 3
  2500           0.1693         0.2571        0.2481        0 / 3
  5000           0.1693         0.2617        0.2430        0 / 3

The detached head NEVER beats copying, at any size, for any member, and it does
not improve with data -- flat at ~0.25 from N=500 up. Your condition for
reconsidering the architecture is met.

COMPUTE IS NOT THE OBSTACLE. A second trunk is 1.98x the parameters and takes
the design from ~1.6 to ~3.2 CPU-hours measured at 11.8 ms/epoch.

MY RECOMMENDATION IS TO DOWNGRADE RATHER THAN SPEND IT. Activation prediction
carries no hypothesis; D-032 already made it a secondary metric; P10.2's primary
error excludes it. Buying a second trunk to improve a number the thesis makes no
claim about seems like the wrong use of the design's simplicity. But you set the
conditional, so the call is yours, and I have not taken it.

NUMBERS
  defects found:            7 (3 serious), each with a named regression test
  H2 endpoint shift:        up to 4.6% on the scale choice alone
  auxiliary vs copy:        0 of 18 runs beat the baseline
  second-trunk cost:        1.98x params, 1.6 -> 3.2 CPU-hours
  tests:                    413 -> 418 passing, 1 skipped
  compute consumed:         0 GPU-hours

NEXT: W4 Mon's trend test -- but it consumes the scale choice in W3-1, so I would
rather have your ruling first.
=== END UPDATE ===
```
