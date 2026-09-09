# Week 8 release verification

Date: 2026-09-01 (Asia/Riyadh)

Status: **historical GO for the pre-interruption implementation only; current
NO-GO until the D-161–D-168 recovery commit and its authoritative repository-wide
artifacts are recorded below.**  Production was unopened during the original
verification, but E2A epoch 001 has since produced 150 complete fits.

## Why the suite is partitioned

The current repository has 4,565 collected pytest nodes.  One monolithic
process cannot provide durable evidence on this host: two otherwise-green
traversals were externally ended before they could write JUnit XML.  The
exhaustive release run was therefore divided into non-overlapping file
partitions whose collected-node totals add back to 4,565.

Partition D required one further routing split.  The legacy repair-timing
guards require pytest scratch below the repository, whereas
`test_week8_launch.py`, `test_week8_monitor.py`, and
`test_week8_preflight.py` correctly reject synthetic storage roots that
overlap the immutable repository source.  The 22 compatible files ran with
repository-local scratch; those three files ran with scratch in the enclosing
authorized workspace but outside the repository.  The two clean selections
contain 782 and 88 nodes respectively and total the original 870 nodes.

## Authoritative evidence

| Partition | Collected nodes | Passed | Skipped | Subtests | JUnit SHA-256 |
|---|---:|---:|---:|---:|---|
| A | 1,442 | 1,437 | 5 | 0 | `31dd34efddae525c84fe0294b7fc9ee45184a9e02310085877de86e360fe7a1e` |
| B | 1,218 | 1,217 | 1 | 51 | `4ee3b756a54a2b5ab23b3ea74c9f5dd7669e8f8b08a91fd3ff5cfb1046de6e9e` |
| C, clean attempt 002 | 1,018 | 1,016 | 2 | 0 | `370522188d9acfb0954191b1279c3ef35c580cb94f750aeadc96446beb6e34bc` |
| D, repository route | 782 | 779 | 3 | 0 | `295733e03f3567e8afd36c3b740fffe650e409d99ae53fee6694f7a867cb9b2a` |
| D, workspace route, clean attempt 003 | 88 | 88 | 0 | 0 | `cf3dde5db4edb7a34fac3413c62a2e31b3f8292a93386015b5e78eee54d090c3` |
| E, current-schema 416-source replay | 17 | 17 | 0 | 0 | `e98548a2101198084486fc71960942b0b282d23b6e77cf326f7285a2512d5a59` |
| **Total** | **4,565** | **4,554** | **11** | **51** | six source XML files above |

JUnit contains 4,616 cases because Partition B represents the 51 subtests as
additional cases.  Every XML has zero failures and zero errors, and
`4,616 = 4,565 + 51`.

The 11 skips are all expected host/schema branches: three CUDA-device skips
on the frozen CPU-only host, seven Windows symlink-privilege skips, and one
vacuous identity-classification skip because no fields are currently excluded
from statistical identity.

The authoritative XML files are retained at:

- `.tmp/week8-partition-a-2026-09-01-attempt-001/partition-a.xml`;
- `.tmp/week8-partition-b-2026-09-01-attempt-001/partition-b.xml`;
- `.tmp/week8-partition-c-2026-09-01-attempt-002/partition-c.xml`;
- `.tmp/week8-partition-d-repo-2026-09-01-attempt-002/results.xml`;
- `D:/Aenv/pro/pro/.tmp/week8-partition-d-workspace-2026-09-01-attempt-003/partition-d-workspace.xml`;
- `.tmp/week8-partition-e-2026-09-01-attempt-001/pytest.xml`.

Each partition used the pinned virtual-environment interpreter, disabled
pytest's cache provider, redirected temporary files to a named project-local
root, hid CUDA/HIP, and recorded before/after Git state.  HEAD remained
`af011cd53a094c15c4dcf0bab6644fe0677a14f2` and the tracked Week 8 working
diff remained stable throughout the authoritative runs.

## Preserved non-authoritative attempts

The following are disclosed but are not substituted for the authoritative
evidence:

- the first full-suite base path was routed outside the repository and the
  legacy repair-timing guard correctly refused 15 tests;
- two later monolithic traversals were externally ended by host lifetime
  controls before JUnit publication, after green prefixes through 84% and 95%;
- Partition C attempt 001 included a sandbox launch denial and an incorrect
  970-node selection before a green 1,018-node run; clean attempt 002 replaced
  that chain with every command exiting zero;
- Partition D attempt 001 used one repository-local base path for all 870
  nodes, producing 58 failures and 18 setup errors solely in the three tests
  with the incompatible source-overlap guard; the two clean route-specific
  runs replaced it without changing a guard;
- D-workspace attempt 002 ran 88/88 tests green, but its post-test PowerShell
  summarizer exited nonzero when it queried an optional XML property under
  strict mode; clean attempt 003 replaced the entire evidence wrapper.

No production fit, label, report, exclusion decision, figure, reserve action,
or GPU operation occurred in any verification attempt.  No failed test was
retried as production, and no scientific boundary was weakened to make QA
pass.

## Pre-interruption release decision

The exhaustive current-tree test gate is satisfied.  The next permitted
actions are the focused post-documentation state/driver tests, validated
scratch cleanup, a clean implementation commit, and then the fixed production
sequence in `docs/week8_production_runbook.md` using that exact commit.

The focused post-documentation check then passed **91 tests with 2 expected
Windows symlink skips** in 41.26 seconds (93 collected cases, zero failures
and zero errors).  Its JUnit SHA-256 is
`bd66c987721178cf88cc80dad37abc56ccd943b1fea83965465f2f996798b9cc`.
It covered `test_project_state.py` and all three fixed production wrappers.
The clean implementation commit is therefore the next gate.

## D-161–D-168 recovery addendum

The release gate above covered the pre-interruption implementation.  After an
external host termination left E2A at 150 starts/149 syncs, D-161 requires a
separate focused gate before any lease or evidence mutation.  That gate must
cover the kernel-backed liveness helper, exact incident classifier, hidden
partial preservation, transition-lock ordering, old-lease orphan archive,
old-commit bootstrap isolation, 149 reuse + one sync-only +111 execute
accounting, two-checkpoint/523-event validation, second-interruption refusal,
stable terminal monitor, D-162's exact Windows launcher/interpreter-pair rule,
D-163's process-local Git trust, D-164's serialized lower-complete postmortem,
D-165's pre-import raw authority and distinct execution/finalizer commits, and
D-166's externally supplied controller commit, outer-bootstrap hash gate,
retained file handles, captured project/dependency importers, exact downstream
E2A routing and verified no-pickle nested fit child.  Synthetic tests are not
permission to mutate production; the committed recovery commit, release
receipt and final test artifact hashes will be recorded before `adjudicate`.

The latest pre-release integration run passed 211 tests before encountering
one stale synthetic inspector fixture; after that fixture was updated, the
inspector/raw-authority tail passed 49 tests with two expected Windows
link-privilege skips.  The separately delegated D-166 nested-boundary suite
then passed 24/24 tests, and two additional exact-environment/canonical-
invocation tests were added afterward.  The latest combined working-copy
matrix then passed **286 tests with two expected Windows link-privilege skips
in 158.60 seconds**.  Its JUnit SHA-256 is
`0ee8462227b1738372a5cd2b42e3b08335c03b798555932addcfda43dc1d74ff`.
These are working-copy checks only.
The authoritative release gate remains the clean-tree combined run plus an
independent read-only inspector after the final commit.

### D-167/D-168 candidate evidence

D-167 added the fixed native trust root, complete retained CPython startup
inventories, exact Git executable and retained two-process nested ownership.
D-168 then closed six fresh P1s before first use: inherited CLR startup
controls, CPython registry/environment startup, mutable executable stage bytes,
reused one-shot fit authority, historical bare Git and incomplete malformed-
startup cleanup.  The final candidate uses receipt V2, a fixed compressed stage
payload, exact cleared `cmd.exe` and native environments, exact
`-I -S -B -X utf8 -c`, schema 4 stage/startup propagation, fresh verified fit
contexts, authority-derived historical Git and retained launcher/base-child
cleanup.  No scientific condition, expected count or output was changed.

Two independent audits found no P0.  After pinning the raw helper to
`dd40628b2ab13507d741d597190606b108b48589372204edf342e6d628ef137d`
and outer literal to
`52a4d90f242fe58af53cf95985660f548d14047e838a463ac329aa63f047840e`,
all five consumers match.  The only process-audit P2—dynamic imported-alias
rebinding—was also fixed and gained direct adversarial coverage.

Four non-overlapping CPU-only working-copy gates are green:

| Partition | Passed | Skipped | Seconds | JUnit SHA-256 |
|---|---:|---:|---:|---|
| stage/receipt/native/raw | 86 | 3 | 47.38 | `e2b8b81572e72474607f52a2579bcdaf0399a3c22e3b14ca255d657a928c8734` |
| worker/nested/controller/inspector | 277 | 0 | 77.70 | `7990ea32eb83ed4ad1a574ef2af7672880d7be255d896201039c2c59b615b456` |
| entrypoint/startup | 47 | 0 | 323.98 | `fbde9658d55cb9425caaec32e7c1d78f69e939bc52b43da53a07148d94da02d4` |
| infrastructure/liveness/finalization/postmortem | 320 | 5 | 207.30 | `409217a5c14e1a1b3027a8bb9a768f3791d7ea3d71cc246b4d38303cfcb68d1a` |

These partitions overlap neither as a claim of repository-wide coverage nor as
permission to mutate production.  The final exact-tree full suite and its
artifact are the remaining software gate, followed by residue relocation,
clean commit, receipt V2, non-executable stage audit and independent status.
GPU, production mutation and scientific-output access remain zero.

## 2026-09-06 resumed implementation gate

The implementation gate is now reconciled: **5193 passed, 18 expected skips, 51 passing subtests; 5,211 distinct collected nodes, zero remaining failures/errors**. Every collected
identity has exactly one accepted terminal result. All runs used the same
source candidate; a documentation-only governance check follows this entry.
The clean commit, receipt V2, stage audits and independent status remain before
production. No recovery authority has been consumed at this checkpoint.

- Candidate manifest SHA-256: `cb103e0b92d91b9873f0989c570308c9bdf5c421cc5a5daf20c5d2e171948090`.
- Combined JUnit SHA-256: `4d4eea58e7987dc9d7e277c74c70c7e2148b8afd0e76958720a2611ab5193f97`.
- Complete provenance, per-partition hashes, skip reasons and targeted-rerun
  mapping: `D:/Aenv/pro2/resume-2026-09-05/qa/release-verification.json`.

The original batch08 attempt stopped before terminal publication;
four setup errors arose from timing fixtures requiring repository-local scratch.
The corrected disjoint routing moved those four nodes to the legacy partition.
Batch09 completed with257passes/4skips and one native-startup failure. An
independent whole-tree inventory found only an extra4413-byte
`Lib/json/__pycache__/tool.cpython-313.pyc`, dated2026-09-03. Omitting precisely
that entry reproduced the original frozen runtime hash exactly. With approval,
the file was moved to verified quarantine; no Python source, dependency, frozen
pin or project code changed. The targeted startup smoke then passed1/1.

The derived combined XML substitutes only that failed case with its passing,
same-candidate rerun. Its provenance explicitly retains the original nonzero
exit, original XML hash and replacement XML hash. Original XML files remain
unchanged; skips cannot replace failed cases. Batch03 wall time includes an
overnight Windows suspension. JUnit suite test counters include the51 passing
unittest subtests; primary testcase elements cover the5,211 collected nodes.
This corrects the historical wording that described those counters as extra
testcase elements. No scientific output was consulted during this QA.

The runbook's native runtime-directory spelling is corrected to the actual
tested `week8-d167-native-runtime-attempt-001`; the stage0 runtime remains d168.
This is documentation only. All existing scientific and one-use stop rules hold.

## 2026-09-08 controller contract correction (D-169)

Release `50251fb3cc63479677c2e19fc242cb6d809c9d05` passed its full gate, but
the independent stage-0 status refused before recovery with error SHA256
`92746c99701434df542af912a0c1b8b70b7a41f3cc35dc716c2085e7f4720323`:
`controller Python path/environment is not exact`. The controller required
six stale PYTHON names that the D-168 isolated launch deliberately omits.
The verified entrypoint adds only PYTHONPATH after admission. The controller
now validates that exact environment; isolation flags, pins, path digest and
unexpected-name rejection remain strict. No bootstrap file or pin changed.

The new real-entrypoint contract replay failed on the old guard with the same
error, then passed with all seven unexpected-variable cases after correction.
This is a real isolated producer/runtime replay into the controller guard;
the child validates its raw capability, while replay mocks only that private
capability validation in the parent. It is not a live production recovery test.
Fresh full gate: **5200 passed, 18 expected skips, 51 passing subtests; 5,218 distinct nodes, zero remaining failures/errors**.
The owner requested a quota pause on September6 during batch07attempt001.
That unfinished attempt is preserved and contributes no gate coverage;
September8 continuation verifies the same candidate and uses batch07attempt002.
Batch09 had one native-startup failure:25 extra bytecode caches had accumulated
in the shared base runtime on September6–7. Independent inventory found no
changed/missing file; excluding only those extras reproduced the original pin.
Approved quarantine preserved all25 files and restored the full frozen runtime
hash exactly. The one-node native smoke then passed on unchanged source. The
reconciler retains the original nonzero report and links its exact passing
replacement case; raw XML remains untouched. Proofs are in runtime-drift-2026-09-08
and runtime-drift-2026-09-08-restored. No interpreter source or pin changed.
Batch10attempt001 had22 failures at its required-empty stage0 fixture assertion.
The runtime contained only two DesktopCentral logs, timestamped during the
first September6 status invocation. Their process of origin was not observed.
Approved preservation moved those2 files (2630bytes) byte-identically into
`stage0-residue-2026-09-08`, leaving the same runtime parent empty. No agent
setting, startup environment, guard or production evidence changed. Full
batch10attempt002 passed284/3skip on unchanged source; the original failed
partition is explicitly disclosed and does not contribute duplicate coverage.
Separately, storage blocked the tail gate until an approved copy/hash/verify
relocation preserved77,616 retired first-release QA files (1,565,074,820bytes)
under `C:/Aenv/beyond-uncertainty-retired-qa-2026-09-08`. Only the verified old
scratch copies were removed from D:. The receipt and three inventories are in
`controller-contract-fix/retired-qa-relocation-2026-09-08`; this is synthetic QA,
not scientific evidence or an off-device backup. The 8GiB floor was unchanged.
Combined JUnit SHA256: `ade0273e0dda2436a2705fa8552daafb86c4a6e9fefb7f4556b4f023cbb290b0`.
Candidate manifest: `9266f9db1cecdb8bde4f0469d19b36fc0b28151e3cfc59481317f1fdf8530d48`.
Reports: `D:/Aenv/pro2/resume-2026-09-05/qa-cfix`; red/green regressions in `qa`.
The first release receipt and refused invocation remain intact; no recovery,
lease mutation, new fit, scientific-value consultation or GPU use occurred.
New documentation governance, clean commit, immutable attempt002 receipt/audit
and independent status remain before the sole D-161 recovery.

## 2026-09-09 inspector diagnostic release checkpoint (D-170)

Clean releasea9fba93729272e8d4c4369182ea19a0381691474 passed the corrected
5218-node gate and13 documentation checks. Its status attempt002 refused
before mutation because the shared Git runtime differed from its frozen pin.
Approved restoration preserved all94 existing files, restored29 entries from
the official Git2.53.0(3) MinGit64 archive and retained65 unchanged entries,
including git.exe. Two independent stable observations reproduced the original
94-file/0-directory/66,573,247-byte hash exactly:
`3c30659fe0591a527183f3f57951a3d2243d178fe606a9756edfed5eaa89e984`.
Official ZIP SHA256: `0d7c85a26e45668b35d0d0aeb763289376cfc039e55e0938a617ed0dfa32e433`.
Source: https://github.com/git-for-windows/git/releases/tag/v2.53.0.windows.3
Proofs, prior runtime and ZIP: `D:/Aenv/pro2/resume-2026-09-05/git-runtime-drift-2026-09-08`.
No pin, fitting source, scientific setting or Git executable changed.

Fresh status attempt003 then reached later checks and refused at2026-09-08
16:31:54Z with RecoveryRefused hash
`274f2b081a06958eea15df82d71a1f129824c0c1a63bc8984acabadafaa73a09`.
Direct/nested static-string and operational-template checks did not identify
its underlying cause. No adjudication, lease mutation or recovery occurred.
The refused receipts, audits and logs remain intact in attempt002/003 and
the corresponding `stage-results-002`/`stage-results-003` folders.

D-170 adds at most eight fixed controller function/line locations to CLI
refusals, without raw messages, traceback text or frame-local values. It also
adds operational diagnostics to inspector process refusals: exit code,
stdout/stderr byte counts and hashes, plus the exception category/reason hash
only from a bounded, exact-shape, canonical inspector refusal with both safety
flags false and an allowlisted exception category. Raw streams and scientific
values are never emitted. Invalid/extra/duplicate/oversized/unsafe responses
yield only stream fingerprints. Exit2, no automatic retry and all authority,
evidence, liveness and scientific checks remain unchanged. The original outer
error hash is retained. This improves diagnosis; it does not claim to fix the
unknown recovery refusal or certify production readiness.

The eight synthetic regression cases failed before the change, then passed
with three existing launch/refusal guard checks:11/11. The first partial
diagnostic gate passed2023/5skip through governance and batches01–04, then its
QA-only tree was stopped during batch05 to finish source-location diagnostics.
Those attempts remain preserved and contribute no coverage to this candidate.
Nine location-regression cases then failed before the final addition; all11
focused checks passed afterward. Fresh full gate:
**5208 passed, 18 expected skips, 51 passing subtests; 5,226 unique nodes, zero remaining failures/errors**. Combined JUnit: `15ffcb6806c73192fd76b57f9f2f5c287d3405b39bbecdca27c3e4e2b2bbc8e9`.
Candidate manifest: `cb26a2e7ee71fc93d75de5fa4e5c36afe476fbd2d4a6d1ea0a81f0fb88fe2185`.
Reports: `D:/Aenv/pro2/resume-2026-09-05/qa-inspector-diagnostics-v2`.
No earlier gate contributes coverage to this changed candidate.
Finish documentation governance, a new clean commit and fresh attempt004
receipt/status through the unchanged native ceremony. Preserve all earlier
attempts. The sole D-161 recovery remains unconsumed; external Sol review and
student own-voice prose remain open. GPU remains unused.
