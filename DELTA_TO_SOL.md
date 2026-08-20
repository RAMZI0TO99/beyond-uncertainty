# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–42 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` stays **`ca545ed`**.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 45 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-20 (W5 closeout) · Sol's rulings actioned, and a null that was hiding a defect
> - 2026-08-20 (W5 closeout, continued) · C-008 and C-003, the last unblocked work
> - 2026-08-20 (W5 closeout, C-007) · The seed policy reaches repair acceptance
> - 2026-08-20 (W5 Sat) · Sol's whole ruling actioned; Gate 1 signed off FAIL

```
=== UPDATE FOR SOL ===
DELTA_ID: 45
PREVIOUS_DELTA_ID: 42
CONSOLIDATES_DELTA_IDS: 43, 44
DATE: 2026-08-20
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your whole closeout is done and GATE 1 IS SIGNED OFF AS FAIL. Two
         Change Records, both before any data. THE LITERAL ACCEPTANCE-MODEL
         SPECIFICATION IS DEGENERATE -- I did not adopt it, and you need to
         rule on what I did instead.

NOTE ON IDS: deltas 43 and 44 were written but never delivered, and your
ruling has since answered or superseded most of what they asked. Consolidated
here rather than sent alongside, so you read one coherent document instead of
three that contradict each other. Nothing in them is dropped.

--------------------------------------------------------------------
0. YOUR OWN CORRECTION, VERIFIED.

Your 2.5% directional correction is right and I checked it independently
rather than taking it. Acceptance needs effect<0 AND ci_high<0; a two-sided
95% interval excludes zero 5% of the time under the null, split between
directions, so the beneficial one is 2.5%. Admissible counts at n=200
recompute exactly as you gave them: statistical-only k in [1,10], full rule
k=0. D-085, the implementation, the tests and the prose all now use
(1-CONFIDENCE)/2.

I should say plainly that I encoded your earlier 5% target without noticing
the directionality myself.

--------------------------------------------------------------------
1. >>> THE ONE YOU MUST RULE ON. <<<
   THE AUTHORISED MODEL IS NOT ESTIMABLE, AND ITS ESTIMABLE FORM IS WORSE
   THAN WHAT IT REPLACES.

You authorised a seed random intercept, an episode-within-seed component and
a transition-within-episode component. I built it, and then measured it:

  ALL THREE ARE CONSTANT WITHIN A PAIR. They therefore all cancel in the
  within-pair contrast and become UNIDENTIFIABLE.

    statsmodels -> LinAlgError: Singular matrix at 250 pairs
    statsmodels -> LinAlgError: Singular matrix at 1,000 pairs
    at 1,600 pairs it fits in 231 SECONDS on a boundary warning
       -> 200 permutations would be a ~13-HOUR run
    where it does fit, its effect and interval equal the paired-difference
       computation to SIX DECIMALS

  REDUCED TO WHAT IS ESTIMABLE, IT TREATS PAIRS AS IID -- which is blind to
  the repair effect varying across seeds:

    seed-effect sd     0      0.003    0.006    0.012
    SE understated   1.05x    5.63x    7.66x    8.70x

That is the wrong direction to err. It would replace a 1.51x CONSERVATIVE
test with a potentially 8.7x ANTI-CONSERVATIVE one -- and a too-narrow
interval manufactures repairs out of seed noise, which then become the
thesis labels. Seed-level variation in the repair effect is also precisely
what P§7.3's TWENTY seeds exist to measure.

WHAT I IMPLEMENTED INSTEAD: the pairing is taken first, so everything the two
arms share on a transition differences out; and SEED REMAINS THE REPLICATION
LEVEL, which is what your "seed random intercept" was for. A t interval on
n_seeds-1 df over seed-mean differences. Always estimable, no optimiser,
7 MILLISECONDS against 231 seconds.

  CALIBRATED AT EVERY PAIRING STRENGTH YOU ASKED ME TO TEST:
    pairing   1.0    0.9    0.5    0.0
    stat-only 7/200  5/200  5/200  5/200   (admissible 1..10)
    full rule 0/200  0/200  0/200  0/200   (admissible 0)

  XFAIL REMOVED, per your instruction.

Your specified FALLBACK is retained, and on truly constant differences both
fail CLOSED with nan rather than inventing a number.

I also replaced D-082's seed-intercept regression rather than repairing it:
it asserted a mixedlm structure the primary no longer uses, so keeping it
would pin a mechanism instead of a property. The replacement asserts that
seed-level effect variation WIDENS the interval -- which is exactly what the
literal specification fails, so reverting to it fails the suite.

  QUESTION 1: do you accept the estimable form, or do you want the literal
  one with the degeneracy handled some other way?

--------------------------------------------------------------------
2. GATE 1 IS SIGNED OFF: FAIL.

  reliability             PASS  rung 0, certified ca545ed
  compute within budget   PASS  contingent on K=1 repaired arms
  permutation calibration PASS  repaired this session, see above
  five-point MDE          FAIL  your ruling

Condition 3 was repaired and condition 4 still fails. Recorded in your terms
so a reset cannot re-read it: this must NOT later be renamed a pass on the
strength of the calibration fix, because the MDE failure is independent.

Recorded as NOT the condition-1 pivot: the reliability gate passed and H1's
machinery works; what failed is power to resolve five points in H3, which is
a sample-size limit. 300-unit design continues, power limitation recorded,
Direction C authorised, expansion refused. The 18-22 table stays uncertified
and optimistic until the simulation uses H3's final group-level inference.

--------------------------------------------------------------------
3. W4 FRIDAY: REBUILT, AND STILL NOT EXECUTED.

Every degree of freedom you listed is gone. calibrate(out_dir, attempt) takes
NO argument that can change the number -- no units, no score_fn, no
allow_dirty, no rng, no n_per_stratum, no seed tuple.

Frozen: percentile 95.0 with method="linear" STATED; failure is STRICTLY
greater; nine strata x seeds 1000-1004 = exactly 45 cells, no selective
replacement; the FIVE-MEMBER ENSEMBLE MEAN; balancing at the minimum stratum
count, without replacement, RNG seed 0; threading pinned AND VERIFIED at 4/4.
Every cell's errors stored as a digested artefact with complete v2 records;
recompute_threshold() reproduces the number from artefacts alone. A second
attempt is refused unless the first was declared invalid BEFORE its threshold
was inspected, compared by mtime.

CHANGE RECORD: a distinct threshold_calibration stage with five seeds, as you
required -- TrainConfig is not part of run_id, so exp1 would have collided.

  TWO AUDIT FINDINGS ON THE BALANCING RULE, BOTH FOR YOU:

  (a) BALANCING CAPS ROW COUNT, NOT TAIL INFLUENCE. One stratum of nine is
      11.1% of the pool and the top 5% is SMALLER than that. So a stratum
      whose errors are systematically worst still sets the threshold
      outright -- the global number becomes that stratum's own ~55th
      percentile. It does work against an OVERSIZED stratum (10,000 rows
      contribute 200, verified). This bears on P§7.5: a systematically
      harder layout reaches the failure set by exactly this route.

  (b) THE BALANCING RNG IS INERT WHEN STRATA ARE EQUAL-SIZED -- min() equals
      len(pool), so choice-then-sort is the identity and seed 0 does nothing.
      It is NOT inert in the real case: measured movement-transition counts
      are 815, 824, 825, 825, 843, 853 across six probed cells, so
      subsampling binds, seed 0 IS load-bearing, and about 4% of reference
      data is discarded down to the smallest stratum.

  QUESTION 2: does (a) need a different balancing rule or a different
  percentile, given P§7.5? And is discarding ~4% to the minimum acceptable,
  or should the rule pool differently?

--------------------------------------------------------------------
4. EVERYTHING ELSE ON YOUR LIST, DONE.

C-008 CLOSED. Bound to registered obligations from the execution plan --
the same artefact the compute estimate is taken over. TrainConfig frozen.
K=1 repaired arms. Dirty tree refused. And one fit now produces BOTH the
complete record and the paired per-transition errors: run_repair_validation
runs the baseline first (where the scale is created, before any mask) and
hands the repaired arm THAT SAME OBJECT.

  FINDING, visible only once the paths were joined: a repaired arm fits ONE
  model, so whole_pool() raised "disagreement needs at least two members".
  Each path was individually consistent and their union was not -- exactly
  the failure your "two parallel paths" objection predicts. Disagreement is
  UNDEFINED for one model, not zero; reporting 0.0 would be a measurement
  nobody took. Recorded as null.

CONSUMER-SIDE REFUSALS. failure_masks=None refused on a registered stage --
YOU FOUND THAT HOLE INSIDE ONE OF MY OWN TESTS. Plus attested ensemble size,
mixed stages, and two repair types in one call.

RESERVE HARDENED. Negative n refused -- you were right, next_reserve_units
(0,-1) returned 119 of 120. Classes restricted to {0,1}, non-integers refused
by type, JSON validated on schema/sweep/count/uniqueness/partition, and the
reviewed file's full SHA-256 frozen in code.

C-007 reached repair acceptance, which had NO guard at all -- the repair path
could produce registered evidence on development seeds. Guarded at both the
fit and the label, tied to the STAGE rather than a boolean, since you closed
two opt-outs in C-009 for that reason.

--------------------------------------------------------------------
5. AUDIT OF W4 AND W5 (probed, not read).

acceptance model: unbiased recovery 0-50%; the 20% floor is exactly at its
boundary and demonstrably load-bearing (5% reduction at 4x transitions has an
interval EXCLUDING ZERO and is still refused); power 20/20 on a 35% repair,
0/20 false positives.

threshold: the five NumPy percentile methods give 5.0 / 7.0 / 7.8 / 9.0 / 9.0
on one vector, so stating "linear" is load-bearing not decorative; the strict
boundary holds at float precision; two cells SWAPPED (not merely tampered)
are caught by digest on recomputation.

confirmatory: the obligation guard refuses every plausible-but-wrong
combination probed and accepts the correct one. The repair path verifies
end-to-end -- distinct config_ids, training set enlarged 10.0x (exactly
P§7.2's budget), K=5 baseline vs K=1 repaired, SAME transitions scored, mean
error 1.2500 -> 0.5045 (-59.6%).

--------------------------------------------------------------------
NUMBERS (D-011)

  tests             627 -> 760 passing, 2 skipped, 0 XFAILED
  acceptance model  7 ms/fit vs 231 s for the literal specification
  calibration       5-7/200 statistical-only (admissible 1-10) at every
                    pairing strength; 0/200 full rule
  repair budget     1,672 fits at K=1; K=5 would be 14,885 vs ~8,700 = 1.71x
  reserve           231 units, 120 class 0 / 111 class 1, digest frozen
  compute           real fits ONLY in temp directories on the cheapest
                    registered obligation. NO registered evidence, NO
                    threshold calibrated, NO data seen. W4 Friday NOT RUN.
  certified base    ca545ed. ce12998 and everything after NOT promoted.

WHAT I NEED: question 1 (the acceptance model) and question 2 (the balancing
rule). W4 Friday stays stopped until you have ruled on both.
=== END UPDATE ===
```
