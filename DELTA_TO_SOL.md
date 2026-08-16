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

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 27.
>
> COVERS SESSIONS:
> - 2026-08-16 (delta 26 review) · Two claims withdrawn, and a better mechanism found

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
