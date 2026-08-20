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

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 48 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-20 (W5 closeout) · Sol's rulings actioned, and a null that was hiding a defect
> - 2026-08-20 (W5 closeout, continued) · C-008 and C-003, the last unblocked work
> - 2026-08-20 (W5 closeout, C-007) · The seed policy reaches repair acceptance
> - 2026-08-20 (W5 Sat) · Sol's whole ruling actioned; Gate 1 signed off FAIL
> - 2026-08-20 (W5 Sat, correction pass) · Sol's delta-45 corrections
> - 2026-08-20 (W5 Sat, closeout patch) · A hole in my own guard
> - 2026-08-20 (W5 Sat, micro-closeout) · A seed could vanish and the result still said twenty

```
=== UPDATE FOR SOL ===
DELTA_ID: 48
PREVIOUS_DELTA_ID: 42
CONSOLIDATES_DELTA_IDS: 43, 44, 45, 46, 47
DATE: 2026-08-20
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your delta-47 non-finite guard is in, reproduced first -- and one part
         was worse than you stated. 811 passing, no xfail.

NOTE ON IDS: deltas 43 and 44 were written but never delivered, and your
ruling has since answered or superseded most of what they asked. Consolidated
here rather than sent alongside, so you read one coherent document instead of
three that contradict each other. Nothing in them is dropped.

--------------------------------------------------------------------
000. YOUR DELTA-47 NON-FINITE GUARD. REPRODUCED FIRST.

You were right, and one part is worse than you stated. Measured on a clean
20-seed 35%-repair input, BEFORE the guard:

  one entire seed set to NaN   effect -0.035383 vs a clean -0.035657,
                               interval half-width 0.003725 vs 0.003568,
                               and n_seeds STILL REPORTED 20
  37 scattered NaN rows        n_transitions STILL REPORTED 3,200
  +inf AND -inf                BOTH silently absorbed to the SAME finite
                               answer -- neither the clean value nor an error

That last one is the part you did not state: the two infinities are
INDISTINGUISHABLE in the output, so a sign error in an upstream error
computation would have been invisible. And the interval could have been formed
on nineteen seeds while the result claimed twenty -- at the boundary where
every repair label in the thesis is created.

THREE GUARDS, AT THREE LAYERS:
  _frame               refuses any non-finite error outright, naming the NaN
                       and infinite counts separately
  paired_differences   uses pivot() rather than pivot_table() as you preferred
                       -- pairing uniqueness is already validated so there is
                       nothing to aggregate, and an aggregating pivot would
                       quietly average away a duplicate pair instead of raising
                       -- and asserts the row count equals the validated pair
                       count
  _paired_seed_cluster asserts the post-grouping seed set EXACTLY equals the
                       input seed set and that every seed mean is finite, so
                       any other route by which a seed could vanish between
                       input and interval also fails closed

Ten tests: NaN and both infinities on each arm independently, a whole
non-finite seed, a refusal naming both kinds, pair-count preservation through
the pivot, and the seed set surviving the transformation.

The "a a fixed effect" typo was mine, and it spanned a line break -- which is
why it survived a grep for the phrase. Fixed.

--------------------------------------------------------------------
00. YOUR DELTA-46 CLOSEOUT PATCH. ALL FIVE ITEMS DONE.

>>> THE STAGE HOLE WAS REAL, AND I REPRODUCED IT BEFORE FIXING IT. <<<

_validate_registered_consumption treated every non-pilot stage as registered
and then derived the required seeds from that stage's own count. Measured:

    exp1                   five seeds 1000-1004 -> CREATED A LABEL, 400 rows
    threshold_calibration  five seeds 1000-1004 -> CREATED A LABEL, 400 rows

Both carry a registered stage and the right confirmatory seeds for it, so
every other clause was satisfied -- while the repair protocol had never been
run at all. Confirmatory evidence is not repair-acceptance evidence, exactly
as you said.

Label creation now requires stage == repair_validation AND the frozen 20
seeds. `pilot` remains for diagnostics that create no registered label. Every
other stage is refused BY NAME, with tests covering exp1,
threshold_calibration, exp2a and config_sweep.

THE FALLBACK API IS GONE. allow_fallback removed from acceptance_test
entirely, and the now-unused `warnings` import with it. You are right that a
dead option that still looks result-changing is worse than no option --
especially one named after a route that was explicitly withdrawn.

WORDING, FINISHED PROPERLY. "the fixed effect for repair condition" is now
"the equal-seed mean paired difference"; acceptance_test's docstring describes
the registered analysis rather than the old variance-component model; and the
permutation docs say "the seed-level t interval" rather than "the mixed
model's interval". The one remaining description of the old model is marked
explicitly as superseded history, per your allowance.

THRESHOLD RECORD VALIDATION FINISHED. recompute_threshold now also checks
evidence_contract_version, metric_schema_version, the recorded strata,
n_per_stratum, n_total, the complete balancing-rule field, reference
confound_rate and statistic, and each cell's recorded transition count against
its loaded array length. Nine new refusal tests, one per field.

DELTA CLEANED. The stale "QUESTION 2" about balancing is removed -- you are
right that it made this document simultaneously say the issue was settled and
ask you to settle it again.

--------------------------------------------------------------------
0. YOUR DELTA-45 CORRECTIONS -- ALL DONE.

I VERIFIED YOUR 2.5% DIRECTIONAL CORRECTION rather than taking it: a two-sided
95% interval excludes zero 5% of the time under the null, split between
directions, so the accepting direction is 2.5%. Admissible counts recompute
exactly as you gave them. I should say plainly that I had encoded your earlier
5% target without noticing the directionality myself.

>>> A CLAIM OF MINE, NARROWED ON YOUR INSTRUCTION. <<<

D-094 said the three variance components "become unidentifiable". You are
right that this overstates it. Shared intercepts cancelling from the paired
treatment contrast does NOT prove every variance component is mathematically
unidentifiable in long-form data. What I actually established, and all I claim
from here:

  - that specification was SINGULAR IN PRACTICE (LinAlgError at 250 and 1,000
    pairs)
  - COMPUTATIONALLY UNACCEPTABLE where it did fit (231 s; a 200-permutation
    null would be ~13 hours)
  - and it FAILED TO REPRESENT REPAIR-EFFECT HETEROGENEITY across seeds
    (SE understated up to 8.7x)

Those three facts justify the seed-cluster analysis. The stronger theoretical
claim is withdrawn from the ledger and the module docstring. D-100 records the
correction against D-094 rather than editing it.

THE ESTIMAND, NOW SELF-CONSISTENT. You caught that the effect equally weights
seed means while the practical-effect denominator weighted raw transitions --
a ratio of two differently-weighted quantities, which is the D-042/D-044 shape
exactly. Both sides now use mean_s(mean_i baseline[s,i]). The test builds seeds
with UNEQUAL transition counts so the two weightings genuinely differ, and
asserts the fixture distinguishes them BEFORE asserting the result -- otherwise
it could not fail.

EXACTLY THE FROZEN SEED SET, at the consumer where the label is created.
Confirmatory was necessary but not sufficient. Nineteen seeds, arbitrary
confirmatory seeds, or a subset chosen after the fact all fail closed by name.
The development-seed refusal runs FIRST, because D-034 is a permanent
exclusion and "the set is wrong" would describe the smaller problem.

NO FALLBACK in registered acceptance. It fails closed if the across-seed
interval cannot be formed, rather than switching the replication unit from
seeds to episodes on the strength of the observed data.

RESULT LANGUAGE CORRECTED throughout: an equal-seed mean paired difference and
its t interval. Not a fixed effect. Not a mixed model. Summary, verdict
reasons, field docs and module docstring all updated.

RERUN AS YOU REQUIRED -- all four pairing strengths still calibrated:
    pairing   1.0    0.9    0.5    0.0
    stat-only 7/200  5/200  5/200  5/200   (admissible 1..10)
    full rule 0/200  0/200  0/200  0/200
NO XFAIL RETURNED.

--------------------------------------------------------------------
1. C-008's LAST TWO EXPOSURES, AND THE THREE THRESHOLD BLOCKERS.

C-008. allow_dirty, threads and interop_threads are GONE from
run_confirmatory. You were right that both produce registered evidence under a
result-changing configuration absent from run identity -- the same defect as an
unrecorded thread count. Threading is frozen at 4/4 INSIDE the runner and
verified after pinning. Tests that fit anything now monkeypatch a clean git
state, which is honest; an override in the runner would not have been.

THRESHOLD BLOCKER 1 -- attempt names are a frozen attempt-NNN format, and
discovery uses THE SAME pattern that admits a name, so no permitted attempt
can be invisible to prior-attempt discovery. Paths, separators and free-form
names are refused.

THRESHOLD BLOCKER 2 -- an INVALID declaration must record a non-empty reason.
An empty file is a formality any re-run could satisfy.

THRESHOLD BLOCKER 3 -- you were right that recompute_threshold trusted too
much. It read the percentile, the method and the SELECTION out of the very
file whose number it was checking: the D-071 shape, a manifest checked only
against itself. Now every frozen constant is compared against the CODE
(percentile, method, seeds, strata, the exact 45-cell grid, uniqueness,
ensemble size, stage, threading, balancing seed, failure rule), the run-record
and member-record digests are verified, and THE DETERMINISTIC SELECTION IS
RECONSTRUCTED FROM THE STORED ARRAYS and compared with the recorded one rather
than reused -- so a hand-written selection cannot pass.

BALANCING KEPT EXACTLY AS YOU RULED. Global 95th percentile, method="linear",
strict >. Finding (a) needs no change -- a stratum with systematically larger
errors dominating the upper tail is a real property of the reference
distribution and P§7.5 is meant to expose it; no tail equalisation, no
stratum-specific thresholds. Finding (b) accepted with the rule unchanged.

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

  BOTH ARE SETTLED BY YOUR RULING and are recorded here as findings only, not
  as open questions: (a) needs no change -- a systematically-worse stratum
  dominating the upper tail is a real property of the reference distribution
  and P§7.5 is meant to expose it; (b) keeps the rule unchanged, the ~4%
  discard being acceptable because it was found before execution, is small,
  gives every stratum equal weight and has frozen selection semantics.

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

  tests             801 -> 811 passing, 2 skipped, 0 XFAILED
  acceptance model  7 ms/fit vs 231 s for the literal specification
  calibration       5-7/200 statistical-only (admissible 1-10) at every
                    pairing strength; 0/200 full rule
  repair budget     1,672 fits at K=1; K=5 would be 14,885 vs ~8,700 = 1.71x
  reserve           231 units, 120 class 0 / 111 class 1, digest frozen
  compute           real fits ONLY in temp directories on the cheapest
                    registered obligation. NO registered evidence, NO
                    threshold calibrated, NO data seen. W4 Friday NOT RUN.
  certified base    ca545ed. ce12998 and everything after NOT promoted.

WHAT I NEED: a ruling on this guard. Gate 1, the paired seed-cluster approach,
the balancing rule, the threshold runner and the confirmatory runner are all
SETTLED and I am not revisiting any of them. W4 FRIDAY REMAINS STOPPED;
46f71d5 is not promoted; base is ca545ed.
=== END UPDATE ===
```
