Patch series for the 2026-08-30/31 owner-authorised Sol2 work (DEV-015..019)
========================================================================

This directory contains exactly the eighteen transferable commits described by
deltas 67-69. The local parent `264138128fe221f9d5fc90d040be877fc2eaa3b9` is only
reconstructed snapshot history; it is NOT remote ancestry or Sol's review base.

Precondition in the REAL repository:

1. Checkout exact target `66edf4a11dce39b91974d5c331cca81424f83b6e`.
2. Follow `session_2026-08-29.patchseries/README.txt` exactly: verify committed
   preimage blobs and apply 0001, 0003, 0004, 0005, 0006, 0007, 0008 and 0009.
   Skip only snapshot-local 0002 as that README directs.
3. Require a clean tree and a green suite before continuing.

Then verify this directory against `PATCH_SHA256SUMS.txt` and apply, in order:

    git am 0001-*.patch 0002-*.patch 0003-*.patch 0004-*.patch 0005-*.patch \
        0006-*.patch 0007-*.patch 0008-*.patch 0009-*.patch 0010-*.patch \
        0011-*.patch 0012-*.patch 0013-*.patch 0014-*.patch 0015-*.patch \
        0016-*.patch 0017-*.patch 0018-*.patch

  0001  D-141 provenance, loader, C-005, gate and threshold evidence hardening
  0002  D-142/D-143 Week-6 harness, pure labels, leakage firewall and durable
        batch orchestration with pre-launch multi-role refusal
  0003  D-141..D-143, DEV-015, delta 67 and current handoff/state documentation
  0004  D-144 durable evidence, source-verifying repair-label pipeline,
        one-fit/many-role records, fresh-process supervision, exact preflight
        and private registered launch, with adversarial regression coverage
  0005  D-144/DEV-016 schedule correction, verification closeout, delta 67 and
        current Sol handoff documentation
  0006  D-146 crash-durable sync, commit-bound workers, token-only lease
        release, exact isolated smoke execution and evidence-only monitoring
  0007  D-145/D-146/DEV-017 owner authority, pre-execution audit, final
        verification evidence and current Sol handoff documentation
  0008  D-147 feature-repair encoded-pool correction and correction-only
        two-commit finalizer, with adversarial zero-fit regression coverage
  0009  D-147 fail-closed smoke execution, immutable-fit preservation, final
        verification evidence and current Sol handoff documentation
  0010  D-148 project-local correction evidence and read-only validation of
        the historical C-volume copy, with mutation-regression coverage
  0011  D-148 owner write boundary, final verification evidence and current
        Sol handoff documentation
  0012  D-149 zero-retraining smoke finalization, exact observed label/counts,
        project-copy integrity evidence and current Sol handoff documentation
  0013  D-150 complete 150-fit Experiment-1 execution, validated project-copy
        evidence, disclosed raw-tail inspection and Week-6 human boundary
  0014  D-151 strict >20% repair boundary correction, exact-boundary tests,
        AI-only Week-6 scaffold/reminder and source-only Week-7 readiness audit
  0015  D-152 phase-one scope audit: scheduled Phase A is complete/certified;
        pipeline PHASE 1 is per-condition and not global launch authority
  0016  D-153/DEV-018 verified Experiment-1 input and descriptive-figure tools;
        exact100 Exp2A/675 sweep baseline configuration preparation; synthetic
        integration/visual QA; project-local Git test isolation and handoff
  0017  D-154/D-155/DEV-019 fixed capacity-extension repair, explicit amended
        H1 reporting, source-bound report/replay, sweep-pairing execution guard,
        architecture-pricing refusal, preservation tests and forward designs
  0018  D-156 actual Experiment-1 report/figures, exact numbers and support,
        preserved finalization correction, AI draft and current Sol handoff

Patch0016 comes from local implementation commit
07b5fba51a6016932b476656edd6303a2ddd57dd. The .tmp/ ignore entry is deliberately
snapshot-local and excluded: the reconstructed .gitignore has no verified real
repository preimage. Packaging commits are not transferred as project history.
Patch0017 is implementation commit ee02542f814ae977fa15036393ca6ea2829aa4ee,
the clean revision used for D-156 analysis.
Patch0018 is documentation commit 8ea8c4279c06dd5e65b062c71d833d29c1ce560e.
The report writer pins exact bytes
of docs/week7_scientific_amendment.md: SHA256
4a856c65b4a0ae2f7b609d6dbf88f97e0489931498c26c165bd38b769a1e1707.
Preserve those bytes on transfer; a line-ending conversion must not silently
be treated as the frozen document. No new statistical look is authorized by
reapplying these patches. Week10 uses artifact-only replay of D-156.

Do not use `git am --3way`. A context mismatch means the precondition is not the
reviewed tree and must be reconciled explicitly. After application, run the
full suite. The D-154/D-155 CPU-host result is 2,293 passed / 7 skipped / 0 failed
in 1,679.75 seconds. XML SHA256:
6b8c98295b9fbb8765d088e52d6363e539884a98dca67ba3ffd148f67f92dab8.
The prior D-153 CPU-host result is 1,798 passed / 7 skipped / 0 failed
in 1,519.40 seconds. Skips were three CUDA checks, three Windows unprivileged-
symlink cases, and one intentionally vacuous identity-exclusion case.
The post-execution state/preflight/batch/launch/monitor closeout was 184 passed /
1 expected skip / 0 failed in 121.95 seconds.
The documentation-only D-152 state gate was 13 passed / 0 failed in 0.47 seconds.
The final D-153 state gate was 13 passed / 0 failed in 0.61 seconds.
The initial D-153 full run1796/7/1 exposed a temporary-directory assumption in
an existing test. The real-Git fixture was corrected, production was unchanged,
and the full run above includes the correction and the added composition test.

Keep TEMP, TMP, MPLCONFIGDIR and pytest --basetemp inside the project when
rechecking this owner's workspace. The owner resolved the missing repair/H1
choices through Sol2 (D-154); external Sol certification remains pending.
Week7 is not fully complete: ordinary labels, versioned sweep pairing, forward
symbolic anchors, reuse-aware launch/throughput and student prose remain.
One authorized real Exp1 report and two figures were generated (D-156), with
zero new training/labels/GPU. Do not describe that as full H1 confirmation.

RESULT SUPPLEMENT (not a replacement for original fit sources):
D:/Aenv/pro/pro/week7-analysis-2026-08-31-attempt-001-evidence.zip
SHA256 800b9a92698817058eeb846e358bb8d2dfd3e8910c1b8d543cbcb31b99ebeef9.
All seven ZIP members were checked byte-for-byte against the immutable artifacts.
Report SHA256:
82b0277af9be843e46ff7d5b53020e23f5eab4e7c68101bffe457b8a2e37f44b.
This includes the failed orchestration comparison and its explicit correction;
the original report/figures were not recomputed or replaced. All 150 original
source/copy attestations remained unchanged. Separate same-volume copies are
not an off-device backup. Exact results, masses, source/analysis commits and
artifact-only replay are in docs/week7_experiment_1_results.md.

Packaging verification: all eighteen patch hashes match; the old sixteen are
unchanged. Applying 0018 then 0017 in reverse to an isolated index initialized
from 8ea8c42 reproduced exactly the prior 34d4a74 tree, without touching the
working tree or normal index. This is local transfer verification, not proof
of remote ancestry or external Sol certification. The final document gate
passed 13 tests in 0.63 seconds after the independent artifact-only review.

Generate `SOL_BUNDLE.txt` only in the REAL repository, cumulatively against
Sol's unchanged certified review base:

    EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=4e55291 ./scripts/sol_bundle.sh \
        src/bu/runrecord.py src/bu/metrics.py src/bu/stats/gate.py \
        src/bu/stats/acceptance.py \
        src/bu/constants.py src/bu/config.py src/bu/stats/trend.py \
        src/bu/experiments/enumerate_units.py src/bu/experiments/w4_timing.py \
        src/bu/experiments/repair.py \
        src/bu/experiments/w4_threshold.py src/bu/experiments/confirmatory.py \
        src/bu/experiments/batch.py src/bu/experiments/labels.py \
        src/bu/durable.py src/bu/experiments/fit_evidence.py \
        src/bu/experiments/label_evidence.py src/bu/experiments/launch.py \
        src/bu/experiments/monitor.py \
        src/bu/experiments/experiment_1_evidence.py \
        src/bu/experiments/experiment_1_report.py \
        src/bu/experiments/experiment_1_figures.py \
        src/bu/experiments/week7_plan.py src/bu/experiments/make_figures.py \
        src/bu/experiments/preflight.py src/bu/experiments/repair_label_run.py \
        src/bu/experiments/repair_label_preflight.py \
        src/bu/experiments/repair_label_launch.py \
        src/bu/experiments/repair_label_finalize.py \
        src/bu/experiments/supervisor.py \
        src/bu/critic/loading.py src/bu/critic/split.py \
        src/bu/critic/dataset.py docs/week7_scientific_amendment.md \
        docs/week7_experiment_1_results.md docs/week7_results_draft.md > SOL_BUNDLE.txt

Deliver DELTA_TO_SOL.md (undelivered deltas 64–69) with that bundle and the
result supplement. External
Sol remains the reviewer/certifier; “Sol2” is the student's implementation-role
label and does not imply certification.
