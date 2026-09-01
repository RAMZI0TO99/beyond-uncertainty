# Week 8 execution log

**Calendar:** Week 3 Tuesday, 2026-09-01.  **Scheduled work being performed:**
bounded Week 8 machine work under D-160/DEV-022.  Schedule dates and Gate 2 are
unchanged.  External Sol review and student own-voice prose remain open.

## 2026-09-01 — source-only readiness audit

Four independent read-only audits covered Experiment 2A repairs/finalization,
H2 reporting and sign consistency, Experiment 2B plus sweep-002 execution, and
the Week 8 exclusion/reserve boundary.  Main independently checked the frozen
plan/schedule, source directories, completed reports, registered enumerator,
low-level evidence APIs, repository status and storage.

The audit corrected preliminary E2A accounting before launch.  Week 6 already
contains all 60 fits for one E2A validation unit.  Exact E2A totals are 416
physical fits / 1,056 model trainings, with 155 / 615 existing and **261 / 441
new**.  Combined with E2B 125 / 625 and sweep-002 3 / 15, the bounded Week 8
new inventory is **389 physical fits / 1,081 model trainings**.

The first sweep label is one undiagnosed attempted hypothesis-class unit.  Its
pre-reserve arithmetic is attempted 1, excluded 1, rate 1.0, N0 0, N1 0,
ambiguous 0, undiagnosed 1, min(N0,N1) 0.  A source-reverified report is being
built.  No reserve API was called; the separate reserve gate remains closed.

The plan's sign-consistency phrase was underspecified.  D-160 and
`docs/week8_sign_consistency_spec.md` fix its exact observed-class, equal-unit,
five-seed ratio calculation before application.  D-160 also discloses and
resolves the Word-table batch-size 256 versus established frozen runner 128
conflict in favor of preserving the already used 128 procedure.

Implementation is additive and parallel across disjoint files.  At this entry
no Week 8 fit, label, ratio, figure or H2 verdict has been produced; CPU/GPU
experimental use is zero.  The project remains on the frozen CPU route.

## 2026-09-01 — adversarial pre-production review

An additional independent review ran after the first pure reporting modules
were green (141 scoped tests).  It found no critical defect, but it correctly
flagged that the E2A smoke label is itself an already-known E2A outcome.  D-160,
DEV-022 and both Week 8 reporting specifications now say explicitly that the
sign rule is post-outcome/post-collection, while the remaining nineteen E2A
labels and all E2A H2 ratios had not yet been opened in this work.

The review also identified a complete-inventory requirement for the real sign
adapter, ineffective link checking caused by resolving paths before `lstat`, a
missing project-local/disjoint report-output boundary, a self-confirming first
sweep identity test and two small sign-test blind spots.  These are being
closed before production.  The pure sign function remains only a mathematical
component: no real sign result may be computed unless the source-bound E2A
report adapter first proves the complete registered label and diagnostic
inventory, including excluded labels.  No scientific outcome was opened while
making these corrections.

## 2026-09-01 — project-local QA correction

One synthetic reporting test invocation inherited the operating system's
default temporary directory.  It was interrupted before completion when this
was noticed; it performed no study fit and wrote no production evidence.  All
remaining main and delegated QA is explicitly redirected to uniquely named
scratch roots below `D:/Aenv/pro/pro`, in accordance with the owner's
project-local-only instruction.  The interrupted invocation is not counted as
a passing test or as scientific compute.

## 2026-09-01 — launch-release audit stop

Independent release audits returned **NO-GO before root creation** despite
correct scientific inventories.  The baseline path still allowed caller-set
storage/timeout values, its generic journal could restart a preserved failed
fit, earlier monitor roots were not protected from later root claims, and one
role-drift shape was not rejected.  The E2A wrapper did not yet reconcile a
terminal lower launch report in its monitor, and a second invocation could
create a checkpoint history that its own monitor rejected.  It also lacked a
clean-commit pin for figure rendering and sanitized CLI failure output.

The corrections are complete: exact 8 GiB/3,600-second Week-8 limits,
Week-8-specific no-retry enforcement, monitor-root preservation, exact-role
guards, one-attempt/idempotent E2A handoff recovery, terminal-report
monitoring, clean renderer provenance and failure-message hashing.  Fixed E2A,
exclusion and serial baseline operator wrappers now remove caller-selected
paths and lower-level launch discretion.  These are operational evidence
changes only; no seed, job, model, label, ratio or outcome rule changed, and
all production attempt-001 roots remain absent.

## 2026-09-01 — pre-production verification checkpoint

Focused release matrices passed 249 tests with 3 expected skips for the shared
baseline engine, 213 with 3 skips across both fixed production wrappers, and 53
for E2A report/figure authority boundaries.  The current integrated Week 8
matrix then passed **583 tests, 5 expected skips and 51 subtests in 840.84 s**;
it deliberately deselected the expensive 416-source composition replay.  That
replay had separately passed **1 test in 2,147.61 s**, proving the harness and
full source join, but preceded the repair-plan schema-v2 accounting addition
and is therefore not substituted for the final current-tree full suite.  A
post-root-guard E2A wrapper rerun passed **32 tests in 15.61 s**.

All counted QA temporary paths were redirected below `D:/Aenv/pro/pro`.  No
production fit, label, ratio, figure, exclusion report or reserve operation has
run; no active Week 8 root claim or common lease exists; GPU use remains zero.
The next release gate is one full current-tree repository suite, followed by a
clean implementation commit.  Only that commit may be supplied to the fixed
production commands in `docs/week8_production_runbook.md`.

## 2026-09-01 — full-suite QA routing refusal and correction

The first full-suite release attempt incorrectly placed pytest's base scratch
under the wider `D:/Aenv/pro/pro` workspace rather than inside the repository.
At 68--69%, the legacy repair-timing suite correctly refused those paths: its
15 failures all had the same project-root guard cause, with 114 neighboring
tests passing.  The execution session later ended at 82% before pytest could
publish its XML, so the attempt is incomplete and is not counted as a full
suite result.

This was a QA-routing error, not a production-code defect.  No guard was
weakened.  The exact repair-timing suite was rerun with OS and pytest scratch
under the Git-ignored repository `.tmp` directory and passed **129 tests in
8.88 s**.  The final full-suite rerun uses that same repository-local routing.
The failed and corrected diagnostic roots remain project-local pending
post-verification cleanup; no production root, fit, label or GPU was touched.

## 2026-09-01 — host-lifetime verification stops

A corrected interactive full run, now using repository-local `.tmp`, passed
the former 68--69% refusal point and remained green through 84%.  The unified
terminal host then ended the process at its long-session ceiling before XML
publication.  A hidden detached attempt was added to remove that ceiling.  It
passed the same timing block, all long recovery sections and reached 95% with
zero-byte stderr.  While executing
`test_real_released_finalization_and_report_boundaries_join_end_to_end`, both
the detached wrapper and pytest worker were externally terminated without an
exit marker or XML.  Neither interrupted traversal is counted as a full-suite
result, regardless of the passing prefixes.

The small stdout/start records are retained in ignored project-local QA
evidence; only their reproducible fixture trees are eligible for cleanup.
Source files were unchanged throughout both traversals, and no production
root, lease, fit, label, report, reserve action or GPU use occurred.  The next
full run is delegated to an isolated agent process with repository-local temp,
one XML report and a required SHA-256/exit-code handoff.  Production remains
blocked until that complete result is independently read back.

## 2026-09-01 — exhaustive release gate complete

The isolated full-suite verification is complete.  Six authoritative JUnit
files cover five non-overlapping partitions, with Partition D split across two
scratch routes because its legacy and Week 8 path guards have intentionally
incompatible placement requirements.  Their exact aggregate is **4,565
collected nodes, 4,554 passed, 11 expected skips, 51 subtests, zero failures
and zero errors**.  JUnit contains 4,616 cases because its count includes the
51 subtests.  The current-schema 416-source E2A composition replay passed
17/17 as part of this result.

The 11 skips comprise three unavailable-CUDA branches, seven unavailable
Windows-symlink branches and one empty excluded-identity-field branch.  All
authoritative runs hid CUDA/HIP, kept scratch below the authorized workspace,
and left HEAD, status and the tracked working diff stable.  Exact selections,
routing corrections, artifact paths and six XML SHA-256 values are recorded
in `docs/week8_release_verification.md`.

The first all-in-one Partition D route is retained as failed QA evidence: its
58 failures and 18 errors were all caused by placing three synthetic Week 8
storage suites beneath immutable repository source.  No guard was changed.
Clean route-specific attempts passed 779/3-skip across 782 nodes and 88/88
across the remaining nodes.  A post-test XML-summary error in an earlier green
88-node attempt was also replaced by a fully zero-exit evidence chain.

Production remains unopened.  The release gate now permits only the small
post-documentation checks, scratch cleanup, clean implementation commit and
fixed-wrapper production sequence.

The focused post-documentation state and fixed-wrapper matrix subsequently
passed **91 tests with 2 expected Windows symlink skips in 41.26 s**.  Its
93-case JUnit file has SHA-256
`bd66c987721178cf88cc80dad37abc56ccd943b1fea83965465f2f996798b9cc`.
No production root or GPU was used.
