# Week 7 implementation — Sol2

Date: 2026-08-31. External Sol review: deferred by the owner, not granted.

## Authority and boundary recorded before implementation

The owner explicitly instructed: “kepp on to the next i will tell sol to review
later on.” This prospectively supersedes D-151/D-152's requirement to wait for
external review before reversible Week-7 implementation. It does not supply
missing scientific specifications. The student's independent Week-6 prose
remains an open human task, carried alongside the engineering work.

This increment builds and synthetically verifies:

1. A read-only Experiment-1 evidence adapter for the exact 150 registered fits,
   retaining five separate configuration curves rather than choosing an
   unregistered pooled endpoint.
2. Configuration preparation for Experiment 2A and the registered sweep's
   baseline fits, derived from the existing execution plan. Preparation is not
   a launch, a new obligation, or evidence that a fit is still owed.

No new model repair, split parameter, seed, threshold, endpoint, sample size,
or reserve decision is made. No real Experiment-1 payload, figure, trend,
hypothesis verdict, or new repair label is opened in this increment. Tests may
use the CPU on fabricated evidence; no experimental training or GPU work is
planned. All generated files and test scratch directories stay inside the
project workspace. Historical evidence is untouched.

## Implementation and verification

Configuration preparation passed 24 tests in 34.19 s. Its immutable output is
`D:\Aenv\pro\pro\week7-preparation-2026-08-31\week7_baseline_preparation.json`
(933,784 bytes), file SHA-256
`9b380e4bbefa4d3c1c5a52e6ab89f8b63cac42dbfaf90cf5b19419fcc9152044`;
internal plan digest
`b5c3a312c4c540104c6cfd7d93da70f22290b25fb37ef2b374f780eea0ccb6d1`.
This is the full required baseline inventory, not a chosen first sweep batch
or an outstanding-job list. It adds no repairs and starts no training.

The first documentation gate caught delta 68 inserted after delta 64 because
the append patch matched a repeated end marker. The new block was moved to the
true end; 13 tests then passed in 0.64 s. All previous delta bodies (64–67)
were mechanically compared against HEAD with whitespace normalised and were
unchanged. Delta 67's line wrapping alone was compacted to preserve the paste
cap. The completed Week-6 session entry was archived verbatim, not deleted.

An agent-coordination interruption temporarily made all three workers
unreachable. Their saved files were preserved. The agents were resumed using
the same identities and told to verify test completion rather than count an
interrupted command as passing. No experimental run was restarted. The
project-local `.tmp/` scratch directory was added to `.gitignore`; no scientific
evidence is stored there or excluded from tracking by this change.

Evidence/figure integration verification remains in progress. Final results
will be appended here and to D-153 / delta 68 before handoff.

Independent source audit of configuration preparation found no substantive
defect: all 775 fit requirements and 795 role assignments match the existing
registry, including the five smoke overlaps. Eight independently re-signed
malformed plans were refused. This audit did not rerun the reported test suite
and did not inspect experimental payloads.

The evidence-reader worker completed **61 tests in 134.39 s** after recovery;
the interrupted run is not counted. Its full 150-sidecar integration fixture
uses the unmodified production writer/reader on fabricated inputs, while
consumer-adversary tests explicitly stub the inner reader. All five
configurations, five seeds, six sizes and 30 multi-role fits are checked.
Cross-size pairing compares the stored float64 scale vector, preserving bits
that the existing reader's float32 convenience tensor could round away.
No real experimental evidence was opened. The public result is an immutable
snapshot, not a reusable token permitting later consumers to skip source reload.

Figure verification: **41 passed in 11.30 s** with no pre-set MPLCONFIGDIR;
**48 passed in 17.79 s** with the existing figure tests run first. Main review
caught the initial external-cache-environment dependency; the test fixture now
sets its own project-local cache and handles matplotlib imported by older
tests. Production still refuses a conflicting cached location. Figure tests
stub the evidence reader, exercise actual Agg rendering and all 150 plotted
values, and check provenance, byte-identical regeneration, source-refusal
propagation and immutable publication. Default figure generation remains W3/W4
only; the new entry is explicit opt-in and was not used on real evidence.

Both synthetic PNGs were visually checked: five configuration panels, all five
seed lines and six sizes, readable labels/legend, and the non-H1 caption.
Review copies and an explicit fabricated-data disclaimer are in
`D:\Aenv\pro\pro\week7-synthetic-review-2026-08-31`. They are not thesis results.
The full suite is running on CPU with all scratch, plotting cache and its XML
report in the project. An unrelated project's CPU processes were identified
and left untouched; they are not part of this project's compute accounting.

Main added one post-collection composition test: the fabricated 150-sidecar
fixture goes through both real readers and the real PNG renderer, with only
the plotting-cache environment adapted. It checks 150 actual reader calls,
manifest identities/digests and source byte/timestamp preservation. Because it
was added after the full suite collected its tests, it will be run separately
and its result reported separately rather than silently folded into that run.

Packaging note: `.gitignore` was reconstructed for this snapshot, not verified
against the real repository's preimage. Its new `.tmp/` entry is therefore a
local packaging change, excluded from the transferable implementation patch.
All scientific code, tests and progress records will be transferred normally.

The first full run exposed an older test-fixture assumption:
`test_git_state_outside_a_repository_fails_closed` expected pytest scratch to
sit outside every repository. With the owner's required project-local scratch,
Git correctly discovered this checkout and the test failed. A focused run
reproduced it. The fixture now sets a Git discovery ceiling at its temporary
parent and removes explicit Git-directory overrides for that test only. Real
Git subprocesses and all three fail-closed assertions are unchanged; production
code is untouched. Infrastructure regression: **47 passed, 1 skipped in
14.16 s**. This correction is included in the transferable patch, not hidden as
a test exclusion. The full run continues to collect any other failures.

The added composition test passed **1 test in 86.01 s**, including fabrication
of its 150-sidecar fixture. Both readers and the PNG renderer were real; all
150 sources were reopened, both output digests matched, and every source byte
digest and timestamp remained unchanged. No stub supplied scientific rows in
this composition test. Its XML report is
`pro2/.tmp/week7-full-suite/composition.xml` (verification only, not scientific
evidence). The previous 61-reader and 41-figure focused counts remain separate
and are not added together with overlapping reruns.

First full-suite result: **1,796 passed, 7 skipped, 1 failed in 1,508.53 s**.
The only failure was the reproduced/fixed non-repository fixture described
above. Its old definition had already been collected before the correction.
That run did not include the subsequently added composition test. A fresh full
run of the corrected tree, including that test, is now running; the first run
is not being relabelled as green. Reports are kept separately as `results.xml`
and `results-final.xml` under `pro2/.tmp/week7-full-suite/`.

## Final verification and handoff

The fresh corrected full suite passed **1,798 tests, skipped 7, failed 0 in
1,519.40 s**. The report records 1,805 total cases, zero failures and zero
errors. Its SHA-256 is
`99cc93d9f3f27c63786cf78c062ef4752e590e812b75ca72d4f8427f68cbb10d`.
The skips are three unavailable CUDA checks, three Windows unprivileged
symlink cases, and one intentionally vacuous identity case. This final run
includes the extra composition test and the corrected Git fixture.

The full suite uses its existing synthetic/development fixtures and certified
tracked logs; those checks are not new registered experimental runs. No real
Experiment-1 result, figure, trend, repair label or new experimental training
was produced. CPU validation is finished and this work used no GPU.

The source/tests/documentation form transferable patch 0016 after the existing
fifteen patches. The snapshot-only `.tmp/` ignore entry stays in the local
packaging commit. Delta 68 and D-153 record both the successful result and the
earlier failures/recovery. External Sol has not reviewed or certified them.

Current plan position: **Phase B, Week-7 engineering**; these interfaces are
complete, not the whole week. The student's Week-6 prose and the scientific
choices in `week7_open_decisions.md` remain open. No missing choice was guessed
to manufacture week completion.
