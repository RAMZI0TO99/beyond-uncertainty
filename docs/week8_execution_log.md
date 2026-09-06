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

## 2026-09-02 — E2A epoch-001 external interruption and D-161 freeze

The fixed E2A prepare and preflight completed at clean execution commit
`4515d5165756c8d1669d38d2ee854fa1051b1017`; receipt SHA-256 values are
prepare `53605da944ff9bd80752fd254d960deed19064c42b07e75bce51acaedb7ebfbc`,
preflight `dd9ee61ff31078a85e02a3cb7a455b7cb374568a5094f0084bf7ed90d65f90a6`
and launch control
`28baf2f3e13a33d6a1c2f64b2d34f17d8bd3dbd48d0a60d1b6105252388e10be`.
The bound plan, source ledger, preflight report and first checkpoint SHA-256
values are respectively `9790d3ec9a93c8fcb0eb82dc96e2da3fe44607a96f26cd64755612e6cbd3197f`,
`2265cbcece1033ce4d0f3df2e4b093d497c6815d5cb0592a511a6515f9fd7379`,
`2001b4043c2a38db79db51035cf38b2777474a8f8624b6f5526fd37d554c9a0a`
and `a8dc8652d4000753a4b7e3731bbecaf09d448f72d56d98bdb15610188c583169`.

The host externally ended the blocking launcher before normal finalization.
The old active lease remains token `c66ea75437c043ba9a1113e0a31d2f8d`,
PID 48960, SHA-256
`ac3879395be164ea6b57dc10382e93236eacb7a76b222897bddbda58d2597f70`.
No terminal lower report or public launch receipt exists.  A stable read-only
validation found 299 contiguous twin events, 150 starts, 149 syncs, zero
explicit failures, stream SHA-256
`13207af2f0a1d461cf471acc7dc9eeef03b6113dda3712acd778d5e4bf4dfc45`.
The unresolved local-only job is `178f4ef3ae1e-s1001`; its successful receipt
names child PID 29480 and hashes to
`5f33bcad381c88fc29782c7e9cf33b3676e733180164bef125fed5fc8123ad84`.
An interrupted hidden durable partial contains 11/15 files and 53,180/66,204
bytes, every present file byte-identical to local.  Ordinary staging and
quarantine are empty; 111 jobs are untouched.

Two independent audits and main review concluded that current code must remain
stopped.  D-161 now records one owner-authorized, outcome-blind recovery path:
commit/test a recovery controller first, prove process death without using
lease age, seal the incident in independent twins, archive the old lease with
explicit orphan status, preserve the partial, reuse 150 complete jobs and run
only 111 untouched jobs from the original clean source.  GPU use remains zero.
No label, metric, ratio, exclusion result or H2 verdict was opened in deciding
this path.  Actual recovery results will be appended under a new decision; the
D-161 text remains immutable.

## 2026-09-02 — D-162/D-163 host-identity and Git-authority hardening

A live process probe showed that Windows keeps the pinned virtual-environment
launcher alive as the direct parent of the executing base interpreter.  D-162
therefore binds the recovery controller to that exact two-process identity and
keeps every other visible or ambiguous Python/PyPy process blocking.  The
rule is creation-time, kernel-path, parent-relation and two-snapshot exact; it
is not a general launcher exemption.

Two read-only old-source inspector attempts then refused safely because the
host account did not own the sandbox-created worktree and because historical
source performed a nested Git check without the same trust binding.  Their
reason digests are recorded in D-163.  No production root changed and neither
attempt emitted a scientific value.  Process-local exact `safe.directory`
binding was added for the one fixed execution worktree; no global, system or
repository Git configuration was changed.  Inspector attempt 007 subsequently
completed in terminal output only and independently classified the frozen
state as 299 events, 150 complete local jobs, 149 durable jobs, 111 untouched
jobs and one eleven-file hidden partial, with all outcome/values/mutation flags
false.  It did not publish a production artifact; a clean-commit attempt is
still required.

## 2026-09-02 — D-164/D-165 recovery release hardening

Independent adversarial review found two final trust gaps before production.
First, a completely finished lower epoch could lose the worker response in a
check-then-publish race with controller sealing.  D-164 adds one shared,
persistent, identity-checked finalization lock and permits only a lower-complete
postmortem whose worker death, current controller identity, unchanged empty
runtime directory and full lower evidence are re-proved while that lock is
held.  It never fabricates the missing worker terminal and cannot resume an
incomplete epoch.  Real subprocess tests exercise worker-terminal versus
postmortem serialization, partial twins, hard links, directories and reparse
points.

Second, project import and Git porcelain occurred too early to be the root of
authority for a one-use recovery.  D-165 adds a direct standard-library
entrypoint and a separately hash-pinned raw verifier.  Before source or
site-packages are admitted, it binds the entrypoint, helper, both Python
executables, Git executable and both complete worktrees.  Raw Git plumbing and
two independent exact filesystem/byte inventories reject tracked/index drift,
untracked or ignored entries, links, extra directories and unstable bytes.
The helper SHA-256 frozen into the entrypoint is
`69b7771dbe6ae8858b600e68fb64f9810d1a574aecf1c09d5d4a952a749e46d6`
after the Windows-native environment-casing correction.
Controller and worker revalidate the sealed, command-bound gate; the worker
does so before consuming its one-use invocation.

Focused authority/entrypoint QA passed **47 tests with one expected Windows
symlink-privilege skip in 113.24 s**.  The controller/worker/postmortem matrix
then reached 194 passes and two expected skips with one failure caused only by
a new test expecting an older refusal phrase; the corrected assertion passed
alone.  This interrupted QA chain is retained but is not the final release
artifact.  A fresh combined matrix, the integration/full governance gate and
their hashes remain required after the independent audits and documentation
are closed.  Production remains exactly at epoch 001: no recovery record,
lease transition, event, fit, label, result or GPU operation was created by
this hardening work.

## 2026-09-02 — D-166 external release and nested-child hardening

Two further independent audits found that D-165 still allowed a direct script
launch, learned the controller commit from inside that trust domain, released
verified paths after inventory, and delegated each Windows fit to the old
native `multiprocessing` spawn.  The runbook also bypassed the recovery gate
for E2A monitor/finalize/report/figures.  All were corrected before the first
accepted recovery command.  D-166 records the externally hash-checked outer
`-c` bootstrap, externally supplied final controller commit, cleared child
environment, retained read handles for every admitted worktree/Git/site file,
captured project/dependency importers, and one verified nested fit child per
new job.  The historical picklability check is now identity-only and performs
no pickle serialization; lower timeout, receipt, quarantine and publication
logic remains frozen at execution commit 4515d516.

Working-copy verification after the controller-commit and retained-lock
changes passed 211 tests before one stale inspector fixture stopped the run.
After correcting only that synthetic fixture, the inspector/raw-authority tail
passed 49 tests with two expected Windows link-privilege skips.  A separately
delegated nested-child suite passed 24/24 tests; exact child-control environment
and noncanonical invocation cases were then added.  These are pre-release
checks, not the final clean-tree artifact.  Current frozen launch hashes are:
outer literal `35758e8e9d11bd7e193ad4886ffe1b5b78e521b73e6979aa04091056292ba348`,
raw helper `cf4727d6acd5e0a1e3f72e685c7f20d0fa8bfe563bfbf14f594bfb711ac8c767`,
entrypoint `146d306dbe1654c652c67b59f149f09baf9dc65ead959826450e345fa25a007d`
and nested bootstrap literal
`955844586e94136ee1f96f6809c49239a5bd0c6d1eaca7e6d16ebaa292250e73`.
An actual pinned-site read-only benchmark took 75.464 seconds for 34,514 files,
3,183 directories and 1,019,096,855 bytes (inventory digest
`ec8a9ffd7ec91e6fb0234a3e2545a8ab4f41758ada574f5e1a7471409cd6febb`),
captured 10,498 Python sources and retained 34,514 read handles.  The pinned
Git runtime check bound 94 files/66,573,247 bytes and retained 94 handles.
After those additions, the combined controller/entrypoint/worker/inspector/
raw-authority/nested-child matrix passed **286 tests with two expected Windows
link-privilege skips in 158.60 seconds**; its project-external JUnit SHA-256 is
`0ee8462227b1738372a5cd2b42e3b08335c03b798555932addcfda43dc1d74ff`.

The production snapshot remains unchanged at 299 events, 150 starts, 149
syncs, one complete local-only job, one preserved eleven-file hidden partial
and 111 untouched jobs.  No recovery record, lease transition, fit, scientific
value or GPU operation occurred.  The release remains NO-GO until the final
combined tests, clean commit, post-commit release receipt and independent
clean-commit inspector all succeed.

## 2026-09-02 — D-167/D-168 startup and historical-fit closure

Three independent pre-production reviews stopped D-166 before any recovery
command.  D-167 added the fixed inbox Windows PowerShell trust root, complete
retained CPython startup inventories, exact absolute Git and two-process nested
ownership.  Two fresh audits then found six further P1s: inherited CLR startup
controls, non-isolated CPython startup, a writable executable stage record, one
verified context reused across all planned fits, historical bare Git and an
unretained base child on malformed startup.  D-168 closes all six with one
release-independent compressed stage source, exact cleared `cmd.exe`
environment, receipt V2 and aggregate stage binding, exact
`-I -S -B -X utf8 -c`, raw/gate schema 4, fresh one-use contexts, a scoped
historical Git adapter and retained launcher/base-child cleanup.

The startup auditor reported no P0 and only the two deliberately deferred
raw/outer digest pins plus one stale runbook assertion.  Final pins are raw
helper `dd40628b2ab13507d741d597190606b108b48589372204edf342e6d628ef137d`
and outer literal
`52a4d90f242fe58af53cf95985660f548d14047e838a463ac329aa63f047840e`;
all five consumers match.  The process/Git auditor reported no P0/P1 and one
non-blocking dynamic-alias P2.  That P2 was also closed: newly imported aliases
are inventoried, rebinding fails closed and best-effort cleanup removes any
remaining adapter.  Its three direct adversarial checks passed.

The final working-copy focused gates are CPU-only:

- fixed stage/receipt/native/raw: **86 passed, 3 expected capability skips** in
  47.38 s; JUnit SHA-256
  `e2b8b81572e72474607f52a2579bcdaf0399a3c22e3b14ca255d657a928c8734`;
- worker/nested-fit/controller/inspector: **277 passed** in 77.70 s; JUnit
  SHA-256 `7990ea32eb83ed4ad1a574ef2af7672880d7be255d896201039c2c59b615b456`;
- full entrypoint/startup: **47 passed** in 323.98 s; JUnit SHA-256
  `fbde9658d55cb9425caaec32e7c1d78f69e939bc52b43da53a07148d94da02d4`;
- neighboring infrastructure/liveness/finalization/postmortem regression:
  **320 passed, 5 expected capability skips** in 207.30 s; JUnit SHA-256
  `409217a5c14e1a1b3027a8bb9a768f3791d7ea3d71cc246b4d38303cfcb68d1a`.

The immutable stage source, encoded payload and exact-environment-policy hashes
are respectively
`f076b94a3318dd0d4c9344381a9c5005946c119014e0351b15109c94f41c0cb5`,
`ba7d5bb992a6f66dbb6f825c911eefbf9f94fc62e0f5577d3d441b06fd5e130c`
and `13ded44c5df93186af2fa8c7cdc714d74941d91fc14102d5c80b05e0c5b021f3`.
Production remains unchanged at 299 events/150 starts/149 syncs/111 untouched;
no lease, fit, result or scientific value changed and GPU use remains zero.
The repository-wide clean-tree gate, release commit, V2 receipt, stage records
and independent status are still required before adjudication.

## 2026-09-06 — Full implementation QA and runtime-cache restoration

5193 passed, 18 expected skips, 51 passing subtests; 5,211 distinct collected nodes, zero remaining failures/errors. Operational evidence is retained at
`D:/Aenv/pro2/resume-2026-09-05`; see the dated release-verification addendum.
The interrupted batch08 route issue and batch09 native-smoke failure remain
disclosed. Quarantining one independently identified extra4413-byte Python cache
restored the original complete runtime hash; the targeted smoke passed without
source/dependency/pin changes. No recovery command, fit or scientific-output
inspection occurred. Documentation governance, residue relocation, clean commit,
receipt/stage records and independent status remain before production. Delta79
carries this checkpoint; reviewer certification and student own-voice work remain
open. This entry is a software-release checkpoint, not a scientific result.
