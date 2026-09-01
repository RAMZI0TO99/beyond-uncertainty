# Week 8 release verification

Date: 2026-09-01 (Asia/Riyadh)

Status: **GO for the clean implementation commit.**  Production was not
opened during verification.

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

## Release decision

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
