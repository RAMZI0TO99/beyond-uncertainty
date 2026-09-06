# Week 8 readiness audit

**Current status (supersedes the pre-interruption readiness finding below):
NO-GO pending the final D-161–D-168 repository-wide gate and a clean recovery
commit.**
The original readiness audit was completed before production opened.  E2A
epoch 001 has since generated 150 complete fits and was externally interrupted;
the preserved incident is described in the final section.  **Calendar:** Week 3
Wednesday, 2026-09-02.  Week 8 is being pulled forward under the owner's
instruction; schedule dates are unchanged and external Sol review is pending.

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

The original scheduled non-reserve scope was 389 physical fits and 1,081
member-model trainings: 261/441 for Experiment 2A, 125/625 for Experiment 2B,
and 3/15 for sweep batch 2.  After the 150/270 complete E2A fits in epoch 001,
the remaining executable scope is 239 physical fits and 811 member-model
trainings: E2A 111/171, E2B 125/625 and sweep-002 3/15.

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

The public production surface is now four fixed wrappers: the ordinary E2A
wrapper, the one-incident-only D-161 recovery controller, the no-compute
exclusion publisher, and the serial E2B/sweep-002 baseline wrapper.  They pin
all attempt-001 roots, the common lease, CPU 4/4 execution, the exact 8 GiB
floor and 3,600-second fit timeout.  The three ordinary wrappers refuse partial
or failed attempt history instead of retrying it; the fourth recognizes only
the one exact D-161 incident under its one-use record protocol.  Lower generic
launch CLIs are not an authorized Week 8 operator surface.

Current-tree scoped verification includes 583 passed, 5 expected skips and 51
subtests in the integrated Week 8 matrix, plus 32/0 in the final E2A wrapper
rerun after its literal production-root guard was added.  The deliberately
long 416-source report composition was also exercised independently; the final
full repository release gate is now complete: 4,565 collected nodes yielded
4,554 passed, 11 expected skips, 51 subtests, zero failures and zero errors
across six authoritative JUnit files.  The exact partition/routing proof and
SHA-256 manifest are in `docs/week8_release_verification.md`.  Those results
govern the pre-interruption tree.  A separate authoritative recovery gate and
clean recovery commit are required before any D-161 production mutation.

These implementations do not grant permission to change constants, labels,
seeds, the sweep order, or the scientific estimand.

## 2026-09-02 D-161/D-162 recovery gate

The first fixed E2A launch was externally terminated after its host process
had run for about 64 minutes.  Normal `finally` handling did not publish a
terminal lower report or release the common lease.  The stable outcome-blind
snapshot proves 299 matching events: 150 unique starts, 149 unique syncs, no
failure/sync-pending event and no completion.  The one unresolved job,
`178f4ef3ae1e-s1001`, has a complete successful local canonical tree and no
durable canonical tree.  Its interrupted durable publication left one hidden
eleven-file partial whose bytes are a strict equal subset of the fifteen-file
local tree.  There are 111 wholly untouched jobs.  No metric, label, ratio or
H2 value was consulted in deriving this classification.

The ordinary fixed wrapper correctly refuses this state.  D-161 authorizes a
single, incident-specific recovery only after a committed controller passes
kernel-backed process-liveness checks, exact twin/control validation, stable
double inventory, partial preservation and adversarial tests.  The controller
must archive—not normally release—the old lease, preserve the partial in two
independent quarantine roots, reuse all 150 complete fits, and allow only the
111 untouched jobs to reach a worker.  A one-sided or partial bootstrap
invocation, worker claim or worker terminal twin is permanent stop evidence;
it is never deleted, repaired, republished or rerun.  Expected terminal lower counts are
111 executed, 150 resumed and 261 synchronized.  Any second interruption,
failure, ambiguous process query or evidence drift is terminal.  Live E2A
monitoring is disabled while recovery events change; one stable terminal
monitor is required afterward.

This incident does not change the E2A scientific inventory, CPU 4/4 route,
batch size 128, timeout, storage floor, sources, roots, estimands or downstream
scope.  The original execution source remains clean at
`4515d5165756c8d1669d38d2ee854fa1051b1017` in a dedicated project-local
worktree; the recovery implementation receives its own later commit identity.

## D-164–D-168 release-hardening gate

The recovery now has two further mandatory boundaries discovered before any
recovery mutation.  Worker-terminal publication and a lower-complete
controller postmortem share one persistent identity-checked finalization lock.
The postmortem is admissible only after the entire lower completion, worker
claim, exact current controller, worker death and unchanged empty runtime
directory are re-proved while that lock is held.  An incomplete lower epoch,
one-sided terminal/postmortem evidence or a replaced guard/runtime object is a
permanent stop; no missing worker terminal is fabricated.

Recovery must also enter through the fixed absolute D-165 standard-library
script under the pinned interpreter and literal `-S -s -P`, with no startup
`PYTHONPATH`.  Before importing project code or site-packages, its hash-pinned
helper proves both worktrees from raw Git plumbing plus two exact filesystem
and byte inventories, as well as the exact Python/Git executables.  The sealed
gate is command-bound and is revalidated by the controller and, before claim,
the worker.  Ignored/untracked files, links, unstable bytes, wrong commands,
path admission or environment drift all refuse.

D-166 strengthens that path before first use.  The direct script is no longer
an operator surface: an externally hash-checked outer `-c` bootstrap receives
the entrypoint/helper hashes and final controller commit as hard-coded release
arguments under a fully cleared environment.  Raw authority retains read
handles for every admitted controller, execution, Git-runtime and site file;
captured project/dependency loaders execute verified Python bytes.  Every
nested fit repeats static authority under pinned `-S -s -P`, bypasses native
`multiprocessing` spawn and pickle serialization, calls only the historical
fixed fit worker, and returns the historical protocol through an atomic
no-overwrite result file.  All four post-recovery E2A commands use the same
outer gate.  The final commit is recorded in a separate post-commit release
receipt because a commit cannot contain its own identity.

Focused tests for these boundaries are green, but readiness remains **NO-GO**
until the fresh combined recovery/integration/governance matrix is complete,
its artifacts are hashed, all ignored QA residue is moved outside the
controller worktree, the exact tree is clean and committed, and the final
read-only production inspector succeeds from that clean commit.  None of the
hardening work changed epoch 001, opened a scientific value or used the GPU.

D-167 and D-168 supersede only the unconsumed startup mechanics above.  The
first executable authority is now a fixed compressed stage source run through
absolute `cmd.exe` with an exact cleared ten-entry environment, strict receipt
V2 and the inbox PowerShell host.  The native launcher creates an exact
twelve-entry controller environment.  Every Python boundary—including nested
fits—uses exact `-I -S -B -X utf8 -c`; raw/gate schema 4 binds the stage and
startup aggregate through the controller, inspector, worker and fit child.
Each historical fit receives a fresh verified context; retained launcher and
base-interpreter handles are cleaned before any malformed-start refusal; and
frozen historical Git calls are served from sealed authority without starting
Git or consulting repository-local configuration.

Two independent D-168 audits found no P0.  Their two deferred P1 digest pins
and one runbook-contract P2 are closed, and the process audit's non-blocking P2
dynamic-alias edge is also fixed and tested.  Current focused evidence is
86/3 stage/receipt/native/raw, 277/0 worker/nested/controller/inspector, 47/0
entrypoint/startup and 320/5 neighboring regression, all CPU-only and green.
These remain working-copy evidence until the exact repository-wide candidate
passes, ignored QA residue is removed from the worktree, and the release commit
plus post-commit receipt/status prove the clean revision.  Production remains
299 events, 150 starts, 149 syncs and 111 untouched jobs; GPU use remains zero.
