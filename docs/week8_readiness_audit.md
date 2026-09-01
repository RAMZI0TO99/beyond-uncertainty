# Week 8 readiness audit

**Status:** pre-production implementation complete; final repository-wide
verification is in progress and no Week 8 fit has been launched by this
record.  **Calendar:** Week 3 Tuesday, 2026-09-01.  Week 8 is being pulled
forward under the owner's instruction; the schedule dates are not being
rewritten.  External Sol review remains pending.

## Scope fixed before the remaining Week 8 outcomes

The authoritative Week 8 schedule requires four machine-work products:

1. finish and label the 20 Experiment 2A conditions;
2. report the already completed first sweep group's exclusion outcome without
   treating the planning assumption as an observed rate;
3. prepare and launch the exact 25-condition Experiment 2B baseline inventory;
4. prepare and launch only configuration-sweep batch 2, the second complete
   comparison group in the already frozen lexicographic partition.

The student's approximately 500-word missing-feature results section is a
separate own-voice obligation.  A drafting aid and reminder may be prepared,
but machine work must not claim that the student wrote it.

## Reconciled starting evidence

- Experiment 2A has 100 source-bound five-seed baseline obligations: 95 fits
  from the completed Week 7 batch and five overlapping Week 6 smoke fits.  The
  smoke execution also contains the same unit's other 15 higher-seed baselines
  and all 40 repairs; all 60 smoke fits are existing evidence.
- Four Experiment 2A units are canonical repair-validation units and require
  seeds 1000--1019.  One of them (`d5baeb907ac3`) already has all 60 arm/seed
  fits from the Week 6 smoke.  The three remaining validation units therefore
  need 45 higher-seed baselines and 120 repairs.  The other 16 units retain
  seeds 1000--1002 for their ordinary repair labels and need 96 repairs.
- Every Experiment 2A unit has the two independent registered interventions
  `data_repair` and `feature_repair`.  The complete design is 416 physical fits
  and 1,056 member-model trainings.  Existing evidence contributes 155 fits
  and 615 trainings; the exact outstanding workload is **261 physical fits and
  441 member-model trainings**.  Repeating the smoke's 55 additional fits
  would duplicate registered identities and is prohibited.
- Sweep batch 1 has one attempted unit and one observed `undiagnosed` label.
  Its exact pre-reserve report is attempted 1, excluded 1, pooled exclusion
  rate 1.0, N0 = 0, N1 = 0, ambiguous = 0, undiagnosed = 1.  The registered
  planning assumption was 0.00, so the pre-reserve shortfall is one unit.  This
  is a one-unit batch result, not a population-rate estimate.
- Experiment 2B is exactly 25 baseline units (hidden widths 16, 32, 64, 128,
  256 crossed with five canonical configurations), five seeds each: 125
  physical fits and 625 member-model trainings.
- Sweep batch 2 is exactly three baseline fits at seeds 1000--1002 for unit and
  comparison-group id `029dd4484382`.  It remains disjoint from the completed
  first group.

If all scheduled non-reserve work is executed, Week 8 adds 389 physical fits
and 1,081 member-model trainings: 261/441 for Experiment 2A, 125/625 for
Experiment 2B, and 3/15 for sweep batch 2.

## Frozen execution boundaries

- Production is CPU-only (`CONFIRMATORY_DEVICE = "cpu"`).  The available GPU
  is not an alternative route and will not be used.
- Every new fit requires a clean, exact Git commit, an immutable plan and
  preflight, one fresh child process, project-local output/staging/independent
  copy roots, the launch-pinned storage floor, and the common production lease.
- Existing fit bytes are reopened and verified; unavailable history is never
  replaced by silent retraining.
- Finalizers do no training.  They rederive labels, statistics and figures
  from independently pinned sources and publish immutable source manifests.
- The first-sweep exclusion report is produced before any reserve action.  The
  predeclared reserve remains behind its separate authorization/review gate;
  no reserve unit is drawn merely because the observed batch-1 exclusion
  differs from the planning assumption.
- Real critic splitting remains closed: the split seed/targets/floors are not
  registered, and Week 8 does not need to open that boundary.

## Scientific reporting boundary

The primary H2 quantity remains the per-seed ratio of means on the strict
baseline failure set, using normalized movement error and the frozen 1e-6
denominator floor.  A condition report is the arithmetic mean and sample
standard deviation of seed ratios; transitions are never pooled across seeds.
The within-seed Pearson correlation is secondary and cannot decide H2.

Week 8 may report Experiment 2A labels, per-seed ratios, condition summaries,
correlations, and descriptive figures.  It must not issue the Week 10 H2
verdict: the repair-verified cross-class comparison also needs Experiment 1 and
Experiment 2B.  Sign consistency is implemented and tested as a
source-independent metric, but remains unapplied in Week 8; it must not
manufacture a high/low threshold from the already observed outcomes.

## Resolved implementation readiness

At audit start the repository already had the low-level repair, evidence,
ordinary-label and H2 diagnostic machinery.  The following missing boundaries
are now implemented and adversarially tested before production:

- an exact Experiment 2A repair plan, source ledger, CPU preflight and launcher;
- a no-compute finalizer covering the mixed 20-seed/3-seed label inventory;
- a source-bound Experiment 2A diagnostic/figure report;
- a canonical reader and immutable pre-reserve exclusion report for the first
  sweep label;
- an exact Week 8 baseline launch plan that enables Experiment 2B and only
  sweep batch 2;
- a fully specified and tested sign-consistency summary.

The public production surface is now three fixed wrappers: one for the seven
E2A phases, one for no-compute exclusion publication, and one for the serial
E2B/sweep-002 baseline sequence.  They pin all attempt-001 roots, the common
lease, CPU 4/4 execution, the exact 8 GiB floor and 3,600-second fit timeout;
they refuse partial or failed attempt history instead of retrying it.  Lower
generic launch CLIs are not an authorized Week 8 operator surface.

Current-tree scoped verification includes 583 passed, 5 expected skips and 51
subtests in the integrated Week 8 matrix, plus 32/0 in the final E2A wrapper
rerun after its literal production-root guard was added.  The deliberately
long 416-source report composition was also exercised independently; the final
full repository release gate is now complete: 4,565 collected nodes yielded
4,554 passed, 11 expected skips, 51 subtests, zero failures and zero errors
across six authoritative JUnit files.  The exact partition/routing proof and
SHA-256 manifest are in `docs/week8_release_verification.md`.  A clean
implementation commit remains required before any production-root creation.

These implementations do not grant permission to change constants, labels,
seeds, the sweep order, or the scientific estimand.
