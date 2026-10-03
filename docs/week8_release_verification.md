# D-177 release verification — 2026-10-02

**STAGED DOCUMENTATION.** This section supersedes stale D-176 queues below while preserving their original bytes. It records requirements and observed history; it is not a governance021 result, clean release, postcommit admission or native013 verdict. See [production runbook](week8_production_runbook.md), [current state](../PROJECT_STATE.md) and [decisions](../DECISIONS.md).

## Preserved predecessor and failed candidate evidence

D-176 is locally released at `597eb048a1bc441030bfcd88b70fdf9c56f882d0` with release008/proposal017 record SHA256 `8ba1ce7e8f802cc6df1235d28b1b13b6b84ac995215d8c6393d5b794564d5569` and released 263-row manifest `d21390e122bfec0ae34b84fc2f83064bb2715f6a8f69d491881e303e06297f39`. Its complete gate007 and release checks do not certify later source. Attempt012 status/adjudicate/pre-recover passed; recover refused pre-mutation and is spent. The existing epoch-001→002 transition is not authorization to create another epoch.

## Exact D-177 candidate acceptance

**Gate008: COMPLETE over the exact two-file candidate.** The driver (`5577dde3e097f47d26ea276a6a318ff5ecc5b15b4cc29b9e4de4b2c5757f72c7`) with the preserved failed attempt `7e49bc2611bf8eb0eb80b99457cbd025bb05f82a33c0fbb0d1cf67ce8f51c7e4` (g8-b09-other-001; frozen-base pyc drift repaired once, receipt `bfc0699d8efc9a8e38499009934e3f068e457471b345d8942d87eecc976e3221`) and continuation `5133c2795eccef8071d4bea109ea7da7ec3241be600ddd804d7a74f6bd5ab6ce` (start `726385633f4b10a4ab737aba7d1a1679094402aa03787ff02511d6f3b2e945ad`, finished `20404a8230403bc0303b5502a46f3ef17bbe324d1c189d2497fe2c1fbaadea72`) accepted 45/45 partitions and 5,569 collected nodes: **5,550 passed, 19 expected Windows symlink-privilege skips, 51 passing subtests, zero failures/errors**. Release-verification report SHA256 `7153cd8c9a94306bad97741a259bb50144f2d1918d1e5ba9efd0fd897e11547c`; combined JUnit `f1fb144a9e30320a8f8f5d00bc7ffe3891a7658c90e8a61a0e2af8a4b58db96e`; plan `5fe7ed0fe6f94792b6c84d5991aae9bc9b40cbc2bead7a9c4126dd962093411b`; collection r34-collect-004 result `017f43cd2ef1bd14bf990f5ce0ff61ae69327f556c30ac5097d5b48bfd5e2f97` with candidate-before == candidate-after; candidate manifest `4e9bcede341db914feae2b80607295a5fbea30ea90386bf8defca28c7350ed30` == live worktree; prior gate007 report `469aa1c1d89d10235bd43d003b656054e5fe16d985c2eecc04b2dc7f910127c5`. The seven added lineage nodes (`test_lineage_matches_reviewed_succession`, `test_lineage_matches_same_controller`, `test_lineage_refuses_extra_field_drift`, `test_lineage_refuses_loaded_module_inventory_drift`, `test_lineage_refuses_manifest_drift`, `test_lineage_refuses_tampered_record`, `test_lineage_refuses_unrelated_commit`) pass. Gate008 ran at controller HEAD `597eb048a1bc441030bfcd88b70fdf9c56f882d0` under the reviewed 30-hour owner record `3ea2fb0aa19fb4526c93fa8429d140b415a0afe118f62fe1691067d7945b2eff`; it confers no post-gate authority by itself.

Remaining acceptance: reviewed proposal018 docs apply, fresh 14-case governance021, runtime016, residue017, inspection009, commit009 and the independently reviewed postcommit admission each require separate fresh reviewed one-use helpers. The final 263-row manifest may differ from `4e9bcede341db914feae2b80607295a5fbea30ea90386bf8defca28c7350ed30` only in the seven documentation rows; both D-177 source/test rows stay byte-identical. Frozen4515 science, evidence trees, relocation policy, runtime/flags/env and modes stay exact.

## Fresh013 native acceptance and scope

After the clean release and independent postcommit review, distinct wrappers must bind the actual reviewed facts plus the current owner record `3ea2fb0aa19fb4526c93fa8429d140b415a0afe118f62fe1691067d7945b2eff`, deadline **2026-10-02T22:36:15Z**. Retain historical pins separately. Original seven-hour adjudication/390-minute recovery reserves impose strict GO cutoffs **2026-10-02T15:36:15Z** / **2026-10-02T16:06:15Z**. Whole-ceremony coordinated quiet global Python/PyPy host, original empty-startup, 8 GiB disk, exact evidence/lease/transition state, two-snapshot PID liveness and all native runtime controls remain. The planned reuse150/execute111 recovery has not completed; 150 local-complete/149 synced/111 untouched/299 events are unchanged. Gate1 remains FAIL on power; H2/H3 untested, external Sol review and student prose open. No outcomes consulted, science changed or public action.

---

# D-176 release verification — 2026-10-01

**STAGED DOCUMENTATION.** This section supersedes stale D-174/D-175 queues below while preserving their original bytes. It records requirements and observed history; it is not a governance019 result, clean release, postcommit admission or native013 verdict. See [production runbook](week8_production_runbook.md), [current state](../PROJECT_STATE.md) and [decisions](../DECISIONS.md).

## Preserved predecessor and failed candidate evidence

D-175 is locally released at `ea9c28aa82a1e8559e9c67e62b06dac7f5cea9b7` with release007/proposal016 record SHA256 `1be0b739a9d9a66fe857a6a9b59b9ece7421d4e146ee2eac8b95f2bb6f90a75d` and released 263-row manifest `e0364b12684c4a03df4993d716d7003fb56ec356f263de3aa8c4e4c42112fe6a`. Its complete gate006 and release checks do not certify later source. Attempt012 status/adjudicate/pre-recover passed; recover refused pre-mutation and is spent. Original schema-3 incident/terminal and byte-identical twins retain `30607bbcc65c4bef9ba1857c89c2c0c97c9f8b4230189191c2a8ebcc4a5d6e8b` / `a4334cd6308d1f8c8cf6a6b95a25624e62e08fd0a4066a45481267ee5d4dc749`. The existing epoch-001→002 transition is not authorization to create another epoch.

## Exact D-176 candidate acceptance

**Gate007: COMPLETE over the exact two-file candidate.** The driver (`72a3fe51e0783ecad5bdb6bf2daab0ca39461c259abbca67d6c441f92762ed4c`) accepted 45/45 partitions and 5,562 collected nodes: **5,543 passed, 19 expected Windows symlink-privilege skips, 51 passing subtests, zero failures/errors**. Release-verification report SHA256 `469aa1c1d89d10235bd43d003b656054e5fe16d985c2eecc04b2dc7f910127c5`; combined JUnit `508f6456846da066fe7045aa6c99bfc51eefa933442010f1b482582ee19dd312`; plan `a680ecd1073f329056ea8d0043219e565b571978468f6f441f2b83898104b6d1`; collection r32-collect-003 result `25e054f9734771828b44b26759771a2293a891ba3f57059f5b9bde59b816b1a0` with candidate-before == candidate-after; candidate manifest `e83cbc6666aecb0e896530a1164c9d30f418583bd74f02715e0cdcfd11f60dd9` == live worktree; prior gate006 report `12bfde2c9999f2c4d532341cbdde65d49130e1747f21b68960feaac64857caa3`. The two added nodes (`test_cross_launch_authority_projection_detects_real_drift`, `test_cross_launch_authority_projection_ignores_command_bound_fields`) pass. Gate007 ran under the historical Oct2 owner record `0e90115586f4bc427258f08842123de50ea83226afc83c5910d36b20de99c0bb`; it confers no post-gate authority by itself.

Remaining acceptance: reviewed proposal017 docs apply, fresh 14-case governance019, runtime015, residue016, inspection008, commit008 and the independently reviewed postcommit admission each require separate fresh reviewed one-use helpers. The final 263-row manifest may differ from `e83cbc6666aecb0e896530a1164c9d30f418583bd74f02715e0cdcfd11f60dd9` only in the seven documentation rows; both D-176 source/test rows stay byte-identical. Frozen4515 science, evidence trees, relocation policy, runtime/flags/env and modes stay exact.

## Fresh013 native acceptance and scope

After the clean release and independent postcommit review, distinct wrappers must bind the actual reviewed facts plus the current owner record `3ea2fb0aa19fb4526c93fa8429d140b415a0afe118f62fe1691067d7945b2eff`, deadline **2026-10-02T22:36:15Z**. Retain historical pins separately. Original seven-hour adjudication/390-minute recovery reserves impose strict GO cutoffs **2026-10-02T15:36:15Z** / **2026-10-02T16:06:15Z**. Whole-ceremony coordinated quiet global Python/PyPy host, original empty-startup, 8 GiB disk, exact evidence/lease/transition state, two-snapshot PID liveness and all native runtime controls remain. The planned reuse150/execute111 recovery has not completed; 150 local-complete/149 synced/111 untouched/299 events are unchanged. Gate1 remains FAIL on power; H2/H3 untested, external Sol review and student prose open. No outcomes consulted, science changed or public action.

---

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

## 2026-09-20 local relocation and recovery integration checkpoint (D-171)

The owner requested all project files/dependencies under D:/Aenv/pro2 and
authorized local-only continuation, including the disclosed provenance amendment.
The earlier5c0daa2 release/status004 and interrupted diagnostic/profile gates are
preserved. No old attempt supplies QA coverage for this changed candidate. The
old D:/Aenv/pro/pro namespace is not recreated: strings in original evidence are
logical historical identities, resolved only through the explicit pinned map.

Relocation audits found304/304 source pairs content-identical and independent,
but0/304 reproduced historical filesystem-copy identities. The September19
same-volume rename separately preserved its before/after identities; the earlier
mismatch cause/time remains unknown. The amended contract preserves old claims
and records present observations separately. Attestation002 binds155 earlier
source pairs plus149synced E2A pairs,9700files and629documents. RecordSHA256:
dd3f546bfa05c4df1cef653fc2ea7e3602cb50ad5506775286d50b79b6f6d187;
policySHA256:a25fa279a5ccce335ac04b31ecba209c38f2fa77a3f67db14356e228348095dc.
No original evidence is rewritten to make old identities appear current.

The consolidated venv retains its exact versions; the documented29 relocation
edits to launch/config/package records are explicit new runtime bindings, not
package upgrades. Base Python and Git bytes remain unchanged. Frozen detached
4515scientific source remains clean. Shared child LOCALAPPDATA is explicit and
project-local. Bounded nested diagnostics preserve status004's refusal without
raw exception data. Restored operational lease namespace contains original
lease bytes/ownership; restoration was not a liveness proof or ownership change.

Two stdlib helpers load only from raw-authority captured controller bytes under
fixed non-bu names. Parent, inspector, worker and fit child independently admit
the pinned attestation and scoped metadata readers. Original scientific source
validators, fit callback, parameters and supervised process protocol remain.
Worker-authorized transition bindings are sealed into child invocation3; child
reopens exact transition twins and orphan archive, forbids ordinary old release,
and delegates other lease tokens. Parent uses its existing full transition proof.
Initial inspection remains outcome-blind. Final validation proves original
schema1/new schema2 checkpoints, distinct contexts,299old/224new events,150old/
111new starts,261syncs and1completion. The149original sync identities remain
historical; orphan+111new copies require current identities. All150old trees and
receipt/result bindings remain checked. Label collection independently reopens
the released inventory through parent admission before its original per-pair
validation;416obligations/384labels/32nonlabel existing fits remain unchanged.

Focused QA is recorded in resume-2026-09-05/qa-relocation and the autonomous
session handoff. Latest labels/entrypoint check: 78 passed in 1348.55s (0:22:28). Parent final checks
had141passes then an existing30s isolated-profile timeout; unchanged isolated
recheck3passed. Finaljob identity checks10passed. Child protocol212, frozenchild22,
capturedhelper19 and other focused tests are separate overlapping evidence, not
a complete gate. Failed fixtures and attempts are retained with their corrections.
The synthetic profile-routing test now waits at most120seconds instead of30;
its path/output assertions and all production timeouts are unchanged. This
accommodates observed host delays and does not diagnose their underlying cause.
Current rawhelperSHA20a9be7eb663c8431f975dd0de3c822817e31a3b07001221ee0b6de5973483e3
is pinned by all five consumers. OuterSHA73d6f0e5cb126ffde136a3746b620236c847b3791a3eec688ddbd649ab304a3e.

A fresh complete exact-candidate gate, governance, clean local commit, immutable
V2 receipt/stage audits and fresh native status remain required. No production
status005,adjudication,leaseownershiptransition,recovery,new scientific fit,outcome
consultation or public action has occurred in this continuation. The sole recovery
is unconsumed. PreserveCPU4/4,GPU0,batch128,timeout3600,8GiB floor and one recovery/
no automatic retry. External Sol certification and student prose remain open;
this record is not a scientific verdict. Do not push, publish, deploy or send.


## 2026-09-20 QA runtime correction and native-copy investigation

Fresh collection contained5555nodes. Gate001 accepted governance13, batch01
401pass/4host-capability skips and batch02539pass, with unchanged candidate bytes.
Batch03 terminated with Windows0xc00000fd during a synthetic fixture's
shutil.copy2/CopyFile2 call. Its252progress markers have no terminal JUnit and
are not accepted coverage. All failed output remains. The attempted driver-stop
command found the driver already gone and did not terminate any process.

A separate full runtime audit found90changed standard-library pyc files, with
no added/missing files or changes in Scripts/Git/site. The critic-balance
cross-process test replaced its environment and omitted-B, dropping inherited
no-bytecode protection. It now passes-B explicitly without changing its seed
comparison or assertions. Changed caches were preserved and exact originals
restored; no cache was regenerated as authority and no runtime pin changed.
runtime-release-002 independently verified allfour trees twice against their
reviewed inventories and the29declared venv relocation edits. The original
shared C: installation was read only. Post-focused checks also prove all5368
base files remain exact. Frozen4515science and all production evidence unchanged.

Focused qa-environment-repair-001 reproduced the native fault after101markers;
no complete focused result is claimed. Two fresh identical122-node selections
then passed:002 with a diagnostic project-local LOCALAPPDATA in492.78s,003 with
the original C:user profile in401.43s; both candidate inventories unchanged.
Thus the evidence does not establish a profile cause or justify changing the
production profile/copy implementation. The native failure remains intermittent.
Windows crash metadata identifies KERNELBASE; both captured stacks contain
thousands of repeated addresses in ManageEngine Endpoint DLP's injected library.
This is strong diagnostic evidence, not a symbolized/unwound stack or proof of
root-cause elimination. No security software was disabled, patched or removed.
Two independent synthetic copy probes each verified100copies/27200files with
unchanged sources, with and without CPU4/4 PyTorch; they are not release gates.

Eight dumps were proved to belong to project processes and moved from C: into
autonomous-2026-09-19-185105/crash-dumps-001 and002 with every hash verified.
Diagnostics and all receipts remain private. Active runbook stage0 literals now
match the relocated policy; historical records keep their original values.
Clarification to D-171's preceding wording: the production child's explicit
LOCALAPPDATA is C:/Users/aladdin-alyanai/AppData/Local, outside its execution
tree; it was not moved into the project. Diagnostic002's profile was temporary.

Fresh complete exact-candidate gate002, final governance, clean local release,
immutable attempt005 native status and all original liveness/count guards remain
required. No status005,adjudication,ownershiptransition,recovery,newfit,outcome
consultation or public action has occurred. D-161 remains exactly one recovery.


## 2026-09-20 complete relocation gate and preserved failure history

Fresh fullgate002 reconciled all22partitions: 5536 passed, 19 expected skips, 51 passing subtests; 5,555 unique nodes, zero remaining failures/errors. Combined JUnit SHA256=a26ce16652ce08271a06ac334d2613d445a6c549a2f4cfee13cf36e0369360d2. The failed batch09attempt001 (163pass/1child-exit timeout) contributes no gate coverage; diagnostic15pass/2hostskips is separate, and fresh262-node batch09attempt002 passed258/4hostskips on the unchanged candidate. The timeout cause remains unproved. The first continuation helper stopped before QA because LF/CRLF manifest serialization differed; all263rows were identical, and continuation002 corrected only that orchestration comparison. All failed/diagnostic attempts remain preserved. Final documentation governance, fresh runtime verification, clean local commit and immutable native attempt005 status/counts/liveness remain before the unconsumed sole recovery. No production fit, adjudication, ownership transition, outcome consultation, GPU or public action; external Sol review/student prose remain open.

Gate receipts: resume-2026-09-05/autonomous-2026-09-19-185105/full-gate-002/release-verification.json and release-junit.xml; individual immutable reports are under resume-2026-09-05/qa-relocation. Every accepted partition matches candidate manifest 08651ad1dece659f29cc128886613040ee301aac0e1b01a865db43a09470644a. Gate001 and the earlier native-copy diagnostic crash remain disclosed above; green QA does not establish elimination of the injected-library/native-copy intermittence. Production profile, security software, frozen4515science, evidence and scientific rules are unchanged. Only seven documentation files change after this gate; their before/after bytes are preserved in docs-final-gate002-001 outside the controller. Separate final governance/runtime/commit receipts must establish each subsequent milestone; this document does not claim them.

## 2026-09-23 owner-resumed local release revalidation

The September20 owner stop was explicitly lifted. The paused263-file controller candidate and clean frozen4515 checkout matched the stop handoff. Fresh runtime-release-004 verified all four pinned runtime trees twice, their reviewed relocation differences and pyvenv pin. The active runbook's production LOCALAPPDATA sentence is corrected to the original C:/Users/aladdin-alyanai/AppData/Local pin; only diagnostic002 used a project-local profile. This is an eighth documentation difference from the full-gate collection. The September20 seven-document receipt and all prior QA evidence remain unchanged. Fresh postcorrection governance, local release inspection/commit and independent native status are required before the single recovery. No production action or public delivery occurred in this revalidation.

## 2026-09-23 local release b84 and native status005 refusal

After the September20 stop was lifted, the reviewed 263-file candidate and frozen4515 checkout matched their stop pins. Runtime-release-004 and -005 verified all four pinned inventories twice; documentation correction governance passed14/14. A fresh release inspection bound the fullgate002 reports, corrected documents, runtime and exact Git changes. The clean local controller release is b84b6b35caf9f6043e859531e6ce5cb71bcc8ab8, with 46 reviewed committed files and no remote push. See resume-2026-09-23-001/controller-release.json and preserved inspection/commit receipts.

The distinct native attempt005 has receipt SHA256 b9586fcfdf686e8e982eae04da59bc9dcdf255d44358a0a51c3d1d4d4b09e866 and stage audit SHA256 77a71603eccb22c11cb5ade64d7dddfd6a966ed31689e6b67f51f16794988f03. It invoked status once and exited 1 at 2026-09-23T15:07:01Z. The bounded result was _InspectorProcessRefused, nested InspectorRefused, with reason SHA256 504ced0a507507dc5bb2eda7c98f01ab46c69d83252a08afd81a9996f63402ee; no automatic retry. That is exactly the hash of the old-source inspector message that its verified execution finders are not installed exactly. No counts or liveness verdict was emitted. Attempt005 stdout/stderr, receipt and audit are immutable; full hashes and interpretation are in resume-2026-09-23-001/STATUS005_FINDING.md. No adjudication, lease transition, recovery, fit or outcome consultation followed.

An isolated pinned-runtime pandas import reproduced an appended six.moves virtual finder after the five originally expected entries. The status005 process did not record its finder list, so this is a narrow inferred cause. D-172 changes only inspector admission for exactly that one tail finder when it is bound to captured, hash-checked pinned six.py and the verified dependency loader. Other finder changes still refuse. Fresh focused QA passed2 and inspector/relocation suite34 on the uncommitted candidate; these overlap and are not a complete release gate. A new exact-candidate full gate, governance, runtime verification, clean local release and immutable attempt006 native status with original counts/liveness are required before the single D-161 recovery. Scientific source, production profile, pinned dependencies, original evidence, lease and no-retry policy remain unchanged. External Sol review/student prose remain open; no public action.

## 2026-09-23 D-172 exact-candidate full gate

D-172 gate003 reconciled all 22 fixed-candidate partitions: 5537 passed, 19 expected skips, 51 passing subtests across 5,556 unique nodes, with zero remaining failures/errors. Combined JUnit SHA256 ae7bfe5c1fb2bb624147a2fd3efc8eca3ec704ced9612939c34bea37b7400aa7. The native batch03-001 stack-overflow attempt contributes no coverage; fresh batch03-002 passed all 640 nodes. Its crash dumps and event records are preserved. The crash's exact root cause is unproved. Verifier002 stopped before report creation on a BOM-prefixed PowerShell JSON record; distinct verifier003 decoded those preserved bytes and reconciled the complete gate. Documentation governance, runtime audit, clean local release and distinct native attempt006 status/counts/liveness remain before the sole unconsumed D-161 recovery. Candidate manifest SHA256 81126abfba2c6efe6e245909c15e7def3874db1c62d321e3dfdc89e1e1dc4f00. Individual accepted JUnit/results and failed-attempt evidence are under resume-2026-09-23-001/full-gate-003 and resume-2026-09-05/qa-relocation. No production status006, adjudication, lease transition, recovery, fit, outcome consultation, GPU or public action occurred during this gate.

## 2026-09-27 D-173 native startup and exact-candidate gate

The clean local D-172 release 1e14ef696c6d80cbc81a659a2032e9775ad7e799 invoked native status006 once. It refused before counts/liveness with exact reason digest 8654e6c2d919f2d75a54777db1bf565061ff698ab78a4d2f3825441a3a444b92 for a nonempty native startup runtime. Injected DesktopCentral/Endpoint DLP logs appeared under a literal `%LOCALAPPDATA%` directory when the native launcher's exact environment omitted that variable; the logs and attempt006 streams are preserved. D-173 pins native `LOCALAPPDATA` to the already reviewed original C user profile and admits exactly 13 native environment rows. The required-empty startup check and original liveness, evidence, lease and one-use recovery guards remain in force. This is an operational correction; status007 has not yet established production acceptance. D-173 gate004 reconciled 5,557 distinct nodes across 45 accepted QA operations: 5538 passed, 19 expected Windows symlink-privilege skips, 51 passing subtests and zero remaining failures/errors. Combined JUnit SHA256 f5e62413492e43faabadfb0d273e5b2ea999f57d9e3393271804f8a7c088d3ad. The Windows stack-overflow attempts batch01-001, batch03-001 and the final test_gate_evidence file group have no accepted coverage; their reports and host events are preserved, and the fault's exact cause remains unproved. Continuation002 paused before batch08 solely for the 10 GiB start buffer; its 18 prior accepted receipts were retained. Continuation003 accepted batch08, then a 3,500-second batch09 timeout was excluded. Continuation004 accepted the isolated long test, then paused for disk space; continuation005 completed the other two exact batch09 groups and untouched nodes through new02-00 before another disk-buffer pause. Continuation006 accepted new02-01 through new02-03, then paused for disk space. Continuation007 accepted new03 through new06, then its final 66-node file group crashed during fixture copying; continuation008 covered those 66 nodes in eleven fresh six-node groups. The same fixed source candidate was checked throughout. Candidate manifest SHA256 efd7e2c24cf87457ba6b7ee84024d5ecb0d5a8dcb1866d13da47340c94eaea3a. Full accepted JUnit and excluded crash/timeout/pause evidence are in resume-2026-09-27-001/full-gate-004 and individual immutable QA reports in resume-2026-09-05/qa-relocation. Old synthetic QA scratch was stored in hashed, fully read-back-verified archives before reclaim; internal hardlink pairs were verified and their original NTFS IDs recorded, not claimed to be reproducible. Post-gate documentation governance14/14, four-tree pinned runtime audit, QA residue preservation, clean local release, distinct immutable attempt007 and independent native status with original counts/liveness remain before adjudication or the sole D-161 recovery. No fit, scientific outcome consultation, push, publication, deployment or external message occurred in this gate.

## 2026-09-27 D-174 raw-authority config correction

Clean local D-173 release `50e6a789153b0454b8808bf4e9fa9979853a22bb` invoked native status007 once. Attempt007 is final: it refused before counts/liveness with exact reason SHA256 `55e1fb7027ffa46e70b455b071caf7f12adf612a5d48a4f1e4c7f5a07b0d63f5` for `authority config keys differ from the fixed contract`. The refusal occurred while the inspector revalidated the sealed entrypoint gate, before static authority re-observation; no scientific values were emitted. Its receipt, audit, stdout, stderr and exit code are preserved. D-174 adds the already pinned original C user `LOCALAPPDATA` path as `pinned_local_appdata` in the inspector, bootstrap worker and nested fit child raw-authority config builders, with contract regressions for all three. This corrects their missing config key without relaxing the raw authority mapping, changing the path, or altering scientific settings. D-174 gate005 reconciled 5,559 distinct nodes across 45 accepted QA operations: 5,540 passed, 19 expected Windows symlink-privilege skips, 51 passing subtests and zero failures/errors. Combined JUnit SHA256 042a7628388b3745682421cd89966cf011bc15b225008d88788e5d18348229c3; candidate manifest SHA256 2dff5f7d5a5faae9b8646d4b9982c373e046befb8e6462df0927be07c2cdd094. The D-173 gate004 and release remain separate preserved evidence; they do not certify this changed candidate. This documentation update is bound to the complete gate005 report and accepted JUnit. The complete exact-candidate gate005 is the prerequisite; documentation governance, all four pinned runtime inventories, controller QA-residue preservation and a clean local release remain required before distinct native attempt008. Recheck the original empty-startup, 8 GiB, evidence, lease and global no-unrelated-Python liveness guards. Any attempt008 refusal is final. No adjudication, lease transition, recovery, fit, outcome consultation or public action has occurred. D-161's sole recovery remains unconsumed.

## 2026-09-28 D-175 proposed exact-helper correction and release requirements

D-174 gate005 and clean local release c0e97606a20f66b8b379bd42666b3a3e392d146f are preserved. Native status010 passed its mechanical verdict once, but the sole native adjudicate010 invocation finally refused with RecoveryRefused and automatic retry false. The exact ten-file refusal record SHA256 is 409cf5248f7c7a392d7136667d9d0909ae39a1f64d9695af04160269a1f29ad9; error SHA256 28fe21d125fe37ca07a99d284433d3dda3d68f012885150237847facad1d20c6 matches the message naming the non-bu _week8_d161_relocation_provenance helper at the controller source root. No incident, terminal, transition or recovery record was observed. The old lease, lock and 11-file hidden partial remained intact, and D-161's sole recovery was unconsumed. Preserve all attempt010 files and do not replay any status or adjudication transport.

D-175 changes only admission of that exact active relocation helper after its original validation; unrelated source-root shadows must still refuse. The verified complete gate006 result is: D-175 gate006 reconciled 5,560 distinct nodes across 45 accepted QA operations: 5,541 passed, 19 expected Windows symlink-privilege skips, 51 passing subtests and zero failures/errors. Combined JUnit SHA256 8609635798966799bdf6c24320f98f7e6621e608c06723649a0331cda7cc7ced; candidate manifest SHA256 fc05526d22b99fb6c52e0977a8aa29c8b9a506ffe7e9b76986af7489e8999c23. This gate is separate from D-174 gate005 and cannot inherit its pass. Document governance, all four pinned runtime inventories, accepted/failed QA-residue readback, source/doc inspection and a clean exact local controller commit remain subsequent gates. Only after these may a distinct create-once status011 receipt/stage audit and independent passing status verdict support a distinct adjudicate011. A refusal ends that one-use command. Original 8 GiB, empty startup, exact evidence and lease, global Python/PyPy, two-snapshot PID liveness and no-retry controls remain. The owner-supervised local/private window ends 2026-09-29 08:00 UTC; no public action is authorized. No recovery, fit, outcome consultation, push or publication occurred in this correction proposal.
