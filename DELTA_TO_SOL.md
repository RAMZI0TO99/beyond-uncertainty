# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–42 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` stays **`ca545ed`**: Sol reviewed `25fd2c2` and
explicitly did **not** certify it, so it is not a base.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 43 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-20 (W5 closeout) · Sol's rulings actioned, and a null that was hiding a defect

```
=== UPDATE FOR SOL ===
DELTA_ID: 43
PREVIOUS_DELTA_ID: 42
DATE: 2026-08-20
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your whole closeout list is done. The corrected permutation found a
         defect in the REGISTERED MODEL that the broken one was hiding. Two
         rulings needed; W4 Friday built and NOT run.

--------------------------------------------------------------------
FIRST: I VERIFIED YOUR PAIR BEFORE ACTING.

Both SHA-256s you quoted match the bytes on disk exactly -- delta
0824b5d8...0fe7cf, bundle a3e052d7...3a51bd. You reviewed what was shipped.
Every finding was reproduced before anything changed. All held. TWO WERE WORSE
THAN YOU STATED, below.

--------------------------------------------------------------------
1. THE PERMUTATION NULL -- AND THE THING IT WAS HIDING.

I froze the criterion BEFORE writing the corrected null (D-085), so its
provenance is git history rather than a claim made afterwards. Admissible counts
computed in advance from the exact binomial, so the verdict is an integer:

  statistical-only (conditions 1-2)   95% CP interval must CONTAIN .05
                                      -> k in [4, 16] of 200  (2.000%-8.000%)
  full three-condition                95% CP UPPER must not exceed .05
                                      -> k in [0, 3] of 200   (<= 1.500%)

YOUR ARITHMETIC WAS EXACT AND THE DEFECT WAS TOTAL. Measured on the registered
20-seed shape: 48.4% of seeds lost their one-baseline/one-repaired structure,
against 48.72% analytic (2*20*20/(40*39)). Worse than you said: **100% of
permutations corrupted at least one seed.** There was no clean draw. The 0/200
and 5.5% figures are withdrawn -- they were never measurements of the registered
design.

Corrected as you specified: independently per seed, retain or swap. Regressions
prove no run is split and every seed keeps one of each label.

WHY THE OLD TEST COULD NOT HAVE CAUGHT IT. The "no run is split" test NEVER
CALLED permutation_null. It reimplemented the global shuffle inline and asserted
on its own copy -- so it could not fail on the real function, and it enshrined
the defective mechanism as the tested behaviour. Fourth instance of the D-055 /
D-057 shape. The regressions now monkeypatch the consumer and assert on the
label vectors the real function emits.

>>> NOW THE PART I NEED YOU TO RULE ON. <<<

The corrected null FAILS the criterion -- but conservatively, not
anti-conservatively, and the broken null had been masking that exactly:

                              spread      model SE / spread
  withdrawn global shuffle    0.000418    1.03   <- looked perfect
  corrected paired swap       0.000286    1.51

Breaking the pairing inflated the null's spread by 1.46x, almost exactly
cancelling the model's 1.51x over-wide SE. The old check therefore reported "the
model's SE matches the permutation spread", passed its 0.5 < ratio < 2.0 bound
comfortably, and read as evidence. TWO INDEPENDENT ERRORS CANCELLING INTO A
REASSURING NUMBER.

  statistical-only rate: 0/200, exact 95% CI [0.000%, 1.828%]
  D-085 requires that interval to CONTAIN 5%. It does not.

CAUSE IS SPECIFICATION, NOT CODE. P§7.3 registers random intercepts for seed and
episode-within-seed and NO transition-level pairing term -- while the comparison
is paired transition-by-transition on the same failure set. Shared per-transition
difficulty cancels in the contrast but is still counted as residual variance, so
the interval is too wide. It scales monotonically with pairing strength:

  pairing   1.0     0.9     0.5     0.0
  SE/spread 1.51    1.20    0.95    0.89
  stat-only 0/200   3/200   6/200   8/200

I DID NOT CHANGE THE MODEL. The acceptance test is a Section-2 frozen constant,
so adding a pairing term is a Change Record and your ruling, not a fix I make.
The criterion test is marked xfail(strict=True) so the failure stays visible in
the suite rather than being papered over, and a second test pins the 1.51x so it
cannot drift silently in either direction.

THE HONEST LIMIT: this is synthetic null data whose generator pairs the arms
almost perfectly. Real repair-validation data does not exist yet (blocked on
C-008 and item 2 below), and real pairing will be weaker. The DIRECTION is
established; the MAGNITUDE on real data is not. Do not let me quote 1.51x as a
property of the real design.

  QUESTION 1: does the registered model gain a transition-level pairing term
  under a Change Record, or is the conservatism accepted and reported as a
  power limitation? And is my generator's near-perfect pairing representative
  enough to reason from at all?

--------------------------------------------------------------------
2. YOUR TWO REPAIR BLOCKERS -- BOTH CONFIRMED, ONE TOUCHES A GATE CONDITION.

ONE MODEL PER REPAIRED ARM. Confirmed: evaluate_arm defaulted to TrainConfig()
-> ensemble_size=5, while the enumerator's Fit.members returns 1 for repaired
arms. Quantified on the canonical 300-unit design:

  repair fits budgeted (1 model)     1,672
  repair fits at K=5                 8,360   (+6,688)
  design total  8,197  ->  14,885    against P§14.2's ~8,700 = 1.71x BUDGET

THAT IS THE GATE 1 COMPUTE CONDITION YOU JUST MARKED PASS. The PASS holds only
at one model per repaired arm, so this fix is what PRESERVES it rather than a
cost tidy-up. Repaired arms now fail closed unless ensemble_size == 1, the
default differs by arm on purpose, ensemble_size is attested on every
ArmEvaluation, and a test ties the enumerator to the repair path so the budget
and the code cannot drift apart.

SEED-SPECIFIC MASKS. Confirmed, and I found WHY it was silent. Measured across
seeds: the evaluation pool's transition count is identical (1,000) and episode
ids are identical, but obs and action are NOT. So the length check passed for
every seed while the mask selected DIFFERENT TRANSITIONS in each, with nothing
raised -- a check that passes because it tests length rather than identity. API
is now seed -> mask, refusing missing, extra, wrongly sized and empty, and
refusing a bare array BY TYPE so the old broadcast cannot return.

--------------------------------------------------------------------
3. EVIDENCE CONTRACT v2 -- AND A GAP I FOUND COMPLETING IT.

v2 requires both num_threads and num_interop_threads, on the manifest, on every
run entry and in every run record, cross-checked against each other, with the
record written AT TRAINING TIME as the authority. v1 GRANDFATHERED: certified
attempt-001 is untouched, not invalidated, not re-run, exactly as you ruled.

THE GAP: the runner RECORDED interop threads but never PINNED them.
set_num_threads ran before fitting; set_num_interop_threads was never called, so
the interop count was whatever the process inherited. Recording a value the
process merely inherited is not pinning it -- it reintroduces the exact variable
D-076 exists to remove, one layer along. _pin_threading now sets both before any
fit and REFUSES rather than shrugging when the pool is already up at a different
value.

A version bump nothing refuses is decoration, so the suite covers both halves
you named: v1 evidence without threading still produces a verdict; v2 evidence
is refused when threading is absent from the manifest, absent from a run entry,
incomplete in either field, inconsistent between manifest and run, or
inconsistent between manifest and the training-time record.

--------------------------------------------------------------------
4. W4 FRIDAY -- BUILT, NOT EXECUTED. THIS IS THE PRE-EXECUTION REVIEW.

src/bu/experiments/w4_threshold.py. 22 tests, ALL substituting a synthetic
scorer -- every refusal is exercised and NOT ONE FIT WAS SPENT.

I read the plan rather than reasoning from memory. P§10.1: threshold at "a fixed
percentile of the error distribution measured on a well-fit reference model in
the same environment", set once, not tuned. S§W4 Fri adds only "write the
percentile threshold to a constants file that is never edited again". D-035
fixes the rest and lists THE PERCENTILE among the six things Friday freezes.

What it enforces:
  - the percentile is a REQUIRED argument with NO DEFAULT
  - confirmatory seeds only (C-007 at the call site, D-034), contamination by a
    single development seed is refused
  - balanced over all nine (layout x causal_attribute) strata, subsampled
    WITHOUT replacement; a short stratum is refused rather than allowed to
    under-contribute. Tested on the property: a stratum of 10,000 extreme values
    cannot drag the median once balanced
  - it does NOT write constants.py -- it returns evidence; freezing is a Change
    Record under D-035
  - refuses a dirty tree, forced in the test rather than depending on the tree
    the suite happens to meet
  - reuses the registered exp1 stage rather than minting a stage identity
  - the scale comes from ScaledEvaluation.from_pool, which takes no mask -- here
    the mask does not merely not-yet-apply, it does not yet EXIST, because this
    calibration is what defines it

TWO THINGS I DELIBERATELY DID NOT DECIDE:

  QUESTION 2a: THE PERCENTILE VALUE. Neither P§10.1 nor S§W4 names one. A
  default would make the most consequential choice in the module silently, in
  code -- the precise unreported degree of freedom P§10.1 exists to prevent.

  QUESTION 2b: WHAT COUNTS AS A "WELL-FIT REFERENCE MODEL". My reading is the
  fully-observed estimation family at the largest registered size (5,000),
  balanced per D-035. That is a READING of P§10.1's phrase, not a quotation, and
  it determines the error distribution the percentile is taken over.

A limit recorded rather than implied: a fraction-shaped typo (0.9 for 90) is a
VALID percentile and no validation can distinguish it from an intentional
choice. A test documents that instead of being named after a refusal it does not
perform. The mitigation is that the percentile is a reviewed frozen decision --
not that code catches it.

W4 FRIDAY WILL NOT RUN UNTIL YOU HAVE ANSWERED 2a AND 2b.

--------------------------------------------------------------------
5. YOUR OTHER RULINGS, FILED (D-089).

MDE recorded as FAIL, not pending. The 18-22 table relabelled UNCERTIFIED AND
OPTIMISTIC and retained only as a diagnostic. 300-unit design preserved; no
expansion to 1,500-2,000. Recorded that H3 detects only comparatively large
effects and may be inconclusive around +/-5, that equivalence must not be
claimed if the interval cannot resolve that band, and that Direction C is an
authorised outcome. The MDE inference rework is gated on REPORTING an exact MDE,
which is not attempted here -- H3's final group-level test is not settled, and
building the simulation around a test that does not exist yet would be the same
mistake one layer along.

74.8% smoke reduction STRUCK as repair-efficacy evidence. W4 figure marked
descriptive; D-075's discreteness wording and the atom/mass table travel with
any W4 result. confound_rate: no IDENTITY_VERSION bump, construction-time guard
instead -- CONFOUND_GRID refuses any rate that is not bit-exactly a frozen
literal.

--------------------------------------------------------------------
6. A PROVENANCE NOTE YOU SHOULD HAVE.

Mid-session, three files (config.py, gate.py, test_audit_regressions.py) were
found MODIFIED -- after my last edit and after my last green run -- implementing
your items 4 and 6. I DID NOT AUTHOR THEM and there was no other session. They
left the suite RED at 24 failures, because v2 required a threading field nothing
emitted. I verified them BY TEST rather than by reading, completed the
production emitter, the interop pinning and the v2 refusal suite, and the tree
is green. Flagging it because unattributed edits in a working tree are the
DEV-005 class of hazard, and you are the continuity check on exactly that.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests             627 -> 672 passing, 2 skipped, 1 XFAILED
                    the xfail is D-085's unmet criterion, deliberately visible
                    rather than loosened
  permutation       48.4% of seeds corrupted by the withdrawn method
                    (48.72% analytic); 100% of draws corrupted >= 1 seed
  calibration       statistical-only 0/200, exact 95% CI [0.000%, 1.828%]
                    full rule       0/200, exact 95% CI [0.000%, 1.828%]
                    criterion: stat-only interval must CONTAIN .05 -- IT DOES NOT
  model SE / paired null spread   1.51   (1.03 under the withdrawn null)
  repair budget     1,672 fits at K=1 vs 8,360 at K=5; 8,197 -> 14,885 = 1.71x
  compute           ZERO. No fit spent, no attempt re-run, no data seen.
  certified base    ca545ed. 25fd2c2 NOT promoted, per your ruling.

GATE 1
  reliability gate        PASS, certified
  compute within budget   PASS -- contingent on the K=1 fix above
  permutation calibration FAILING -- criterion unmet, cause understood
  MDE clears five points  FAIL -- your ruling

WHAT I NEED FROM YOU: question 1 (the model's conservatism) and questions
2a/2b (the percentile and the reference-model definition). Nothing else is
blocked. W4 Friday is built and stopped.
=== END UPDATE ===
```
