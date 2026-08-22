# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–50 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** The evidence archive does **not** need
resending — Sol verified it on delta 50 and closed the delivery requirement. The
bundle header names the delta it belongs to; check that line matches before
sending (D-066). `BASE` is still **`ca545ed`** until Sol certifies this closeout.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    src/bu/constants.py src/bu/models/uncertainty.py tests/test_failure_threshold.py \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 51 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (D-035 promotion) · The failure threshold is permanently frozen
> - 2026-08-22 (post-promotion probe) · One threshold, nine prevalences

```
=== UPDATE FOR SOL ===
DELTA_ID: 51
PREVIOUS_DELTA_ID: 50
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: D-035 APPLIED. FAILURE_THRESHOLD = 0.610702633857727 is frozen in
         constants.py. Narrow patch only, nothing downstream built. This is
         the closeout bundle you required before failure sets or repair labels.

--------------------------------------------------------------------
THE PROMOTION IS APPLIED, EXACTLY AS AUTHORISED.

  FAILURE_THRESHOLD = 0.610702633857727

  in src/bu/constants.py. Exact, unrounded, permanently frozen.
  repr  0.610702633857727
  hex   0x1.38ae040000000p-1
  type  plain Python float, not a numpy scalar -- a numpy scalar would carry
        a dtype into every downstream comparison and could silently demote a
        float64 comparison to float32.

Your five instructions, each discharged:

  1 exact constant, not rounded          DONE, pinned by test at bit level
  2 no caller-selectable override        DONE, see below
  3 strict > boundary preserved          DONE, and it is NOT academic
  4 regression tests, constant+boundary  DONE, 11 tests, proved falsifiable
  5 ledger + state files updated         DONE, D-107; §2 now says FROZEN

--------------------------------------------------------------------
>>> THE STRICT BOUNDARY DECIDES REAL LABELS. <<<

TWO TRANSITIONS IN THE CALIBRATION POOL SIT EXACTLY AT THE THRESHOLD.

Under `>` they are not failures. Under `>=` they would be. I measured this
rather than assuming the boundary was a formality, and it changes how the
regression test had to be written -- see the weak-test admission below.

--------------------------------------------------------------------
NO CALLER-SELECTABLE OVERRIDE.

ScaledEvaluation.failure_mask() takes NO arguments. The reasoning is C-010's
exactly, which you ruled on in D-076: from_pool takes no mask so the scale
cannot be subset-derived; failure_mask takes no threshold so the failure set
cannot be re-cut. A value a caller can pass is a degree of freedom somebody
eventually uses.

It scores the ENSEMBLE MEAN PREDICTION -- what the calibration measured --
NOT the mean of the members' errors. Those are different numbers, and using
the second while calibrating on the first would move the failure rate off 5%
with nothing raised. Pinned by a test that also asserts the two definitions
still differ on its fixture, so it cannot go vacuous.

--------------------------------------------------------------------
VERIFIED AGAINST YOUR EVIDENCE, NOT ASSERTED.

  95th pct of the stored balanced pool   EQUALS the constant exactly
  balanced pool                          36,927 = 9 x 4,103
  failures on it                         1,846 = 4.9991%
  your unbalanced sanity check           1,879 / 37,406  -- REPRODUCES
  transitions exactly at the boundary    2

--------------------------------------------------------------------
THE TESTS WERE PROVED FALSIFIABLE BY MUTATION.

Each mutation fails EXACTLY ONE test, which is the coverage claim:

  round the constant to 0.6107026338577   -> exactness test fails
  change `>` to `>=`                      -> boundary test fails
  add threshold=None override             -> no-override test fails

The no-override test asserts by CALLING failure_mask with a threshold and
requiring TypeError, not by inspecting the signature for an absent parameter
name. That second shape is what D-055 and D-057 were written about and it
passes whether or not the property holds.

--------------------------------------------------------------------
>>> TWO WEAK CHECKS OF MY OWN, CAUGHT BEFORE THEY SHIPPED. <<<

I am reporting these because you would have found them, and because the
pattern is the one you have named four times now.

(a) MY FIRST BOUNDARY TEST WAS A TEST OF PYTHON. It asserted `errors > t` on
    a tensor the test itself constructed. That exercises the comparison
    operator and would have passed no matter what failure_mask did -- it was
    not connected to the implementation at all. Rewritten to drive the real
    constructor: the pool is [-1, 1, -1, 1], whose population std is exactly
    1.0, so the scale is exactly 1 and the error is exactly the offset. One
    transition's error is then EXACTLY the threshold after the real scale and
    error computation. It also asserts the fixture is still exact, so it
    cannot silently stop testing the boundary.

(b) MY NEW §2-vs-CODE CHECK WAS VACUOUS. I added the threshold to
    test_frozen_constants_match_the_code, which searches the WHOLE state
    file. The value appears FIVE times in it. I proved this by rounding §2's
    row to `0.6107` -- AND THE TEST STILL PASSED. Now scoped to §2 alone and
    shown to fail. This is D-071 and D-105's shape again: a check that passes
    because the thing it checks is somewhere else.

--------------------------------------------------------------------
A PROCESS FAILURE, ON RECORD.

Proving falsifiability the first time, I mutated constants.py and
uncertainty.py and restored them with `git checkout` -- while the promotion
patch was STILL UNCOMMITTED. The restore reverted to HEAD and destroyed it.
Retyped in full; nothing was lost, and the suite would have caught a partial
restore. GIT CHECKOUT RESTORES TO THE LAST COMMIT, NOT TO THE STATE YOU WERE
IN. Mutation-test against committed work or a copy. Redone that way.

--------------------------------------------------------------------
SCOPE HELD.

NO failure set built. NO repair label built. NO downstream analysis. Gate 1's
signed FAIL, the seed-cluster acceptance analysis and every prior scope ruling
are untouched. No rerun -- the attempt is final.

HOUSEKEEPING: PROJECT_STATE.md hit its 500-line paste cap, so the three
delivered 2026-08-20 entries moved to PROJECT_STATE_ARCHIVE.md in full,
nothing condensed, with a pointer left in §7. The file is 482 lines.

--------------------------------------------------------------------
NUMBERS (D-011)

  constant          0.610702633857727  (hex 0x1.38ae040000000p-1)
  boundary          strictly greater; 2 transitions sit exactly at it
  balanced pool     1,846 / 36,927 = 4.9991% failures
  unbalanced check  1,879 / 37,406 = 5.0233%
  tests             819 -> 830 passing, 2 skipped, 0 xfailed (11 new)
  compute           NONE this session. 675 CPU fits total, 0 GPU-hours
  data seen         none beyond D-103's recorded calibration
  bases             bundle diff from ca545ed; execution base 93dc296

--------------------------------------------------------------------
WHAT I AM ASKING FOR: certification of this closeout, which is the gate you
set before downstream failure sets or repair labels. I have started nothing
downstream and will not until you certify.

--------------------------------------------------------------------
--------------------------------------------------------------------
APPENDED AFTER THE ABOVE (D-008: this delta was still undelivered).

TAKEN WHILE THE CLOSEOUT IS WITH YOU, under Q-004 -- review and understanding,
NEVER scope. No code changed. Nothing downstream built.

>>> A FINDING THAT NEEDS YOUR RULING BEFORE ANY FAILURE SET EXISTS. <<<

THE ONE GLOBAL THRESHOLD DOES NOT MEAN ONE THING.

D-035 rules out family-specific thresholds because they would "make the failure
set partly a function of the construction label -- which is the leakage P§7.5
forbids". Its justification is that balancing makes one threshold defensible
"ONCE D-032 HAS FIXED THE ERROR TO ONE SCALE".

So I asked whether the error is on one scale. IT IS NOT. D-061 fixes the
normalising scale to each EVALUATION POOL, and every unit has its own. Those
two rules had never been checked against each other.

MEASURED, NO TRAINING AND NO FITS. targets() is a pure slice of next_obs, so
the scale is a std over the environment alone. Nine strata x five seeds, the
exact cells the threshold was calibrated on:

                scale     failure rate      raw error (BOUNDED)
  clustered    0.2018        8.77%          [0.05737, 0.06032]
  uniform      0.2226        4.68%          [0.05704, 0.05929]
  sparse       0.2475        1.58%          [0.05318, 0.05495]

  scale spread across strata      33-36%, ORDERED SYSTEMATICALLY BY LAYOUT
  failure-rate spread             5.53x   (behind a pooled 5%)
  RAW error spread                1.09x

A smaller scale inflates the normalised error, so prevalence is ordered
inversely to the scale. The pooled 5% hides a 5.5-fold difference.

IT IS MOSTLY THE NORMALISATION, NOT DIFFICULTY. The raw error is BOUNDED, not
approximated: normalised = ||delta / (s_x, s_y)||, so ||delta|| lies exactly in
[normalised * min(s), normalised * max(s)].

  CLUSTERED vs UNIFORM -- the decisive pair. Their raw-error intervals OVERLAP.
  Clustered's raw error is AT MOST +5.7% above uniform's and could be -3.2%
  BELOW it. Its failure rate is 1.87x.

WHY IT MATTERS: the failure set is what H2 is defined over and what H3's critic
must predict. Layout -- a registered design factor -- enters the label through
the scale. That is the leakage D-035 excludes, arriving through a different
door.

--------------------------------------------------------------------
A CORRECTION I OWE YOU, ON DELTA 49.

I wrote that the unbalanced pool giving 5.02% against 5% by construction meant
"the strata are not wildly heterogeneous in the upper tail".

THAT INFERENCE IS INVALID. Balancing discards only 1.28% of rows, so the two
pools are very nearly the SAME POOL -- the agreement is arithmetic, not
evidence. A pooled rate carries no information about per-stratum dispersion.
The strata ARE wildly heterogeneous: 5.53x. I hedged it at the time ("not
treating it as evidence either way"), which limits the damage but does not make
the reasoning sound.

--------------------------------------------------------------------
CAUGHT IN MY OWN PROBE, BEFORE THE NUMBER LEFT THE MACHINE.

The first version used mean(scale) and described the two dimensions as agreeing
to ~1%. They differ by up to ~5%. Replaced the point estimate with the exact
interval. D-042's lesson applied in time rather than after -- which is the only
reason the clustered-vs-uniform claim above is stated as an overlap rather than
as a spurious precise ratio.

--------------------------------------------------------------------
RELATED TO, BUT NOT THE SAME AS, WHAT YOU ALREADY HOLD.

D-097 finding (a) and D-099 raise that balancing caps ROW COUNT, NOT TAIL
INFLUENCE, so a systematically-worst stratum can set the threshold's VALUE.
This is the downstream consequence and a different claim: GIVEN the value, the
resulting PREVALENCE is 5.5x heterogeneous and mostly an artefact of per-pool
normalisation.

--------------------------------------------------------------------
I HAVE NOT ACTED ON IT, AND CANNOT.

The threshold is frozen and must not be recalibrated, so this cannot be fixed by
changing it. Whether the remedy is a recorded methodological limitation, layout
carried as a covariate, a stratified analysis, or something else is YOUR ruling.
It belongs BEFORE any failure set or repair label is built, which is exactly
where the project now sits -- so this is a second thing blocking, alongside the
certification.

  reproduce   scripts/probe_threshold_heterogeneity.py  (committed, no fits)
  tests       830 passing, 2 skipped, 0 xfailed
  compute     NONE. 675 CPU fits total, 0 GPU-hours
  data seen   D-103's recorded reference errors, plus evaluation-pool target
              statistics. No experimental condition, no hypothesis.
=== END UPDATE ===
```
