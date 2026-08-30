Patch series for the 2026-08-30 owner-authorised Sol2 session (DEV-015)
========================================================================

This directory contains exactly the fifteen transferable commits described by
delta 67. The local parent `264138128fe221f9d5fc90d040be877fc2eaa3b9` is only
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
        0011-*.patch 0012-*.patch 0013-*.patch 0014-*.patch 0015-*.patch

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

Do not use `git am --3way`. A context mismatch means the precondition is not the
reviewed tree and must be reconciled explicitly. After application, run the
full suite. The audited CPU-host result is 1,671 passed / 7 skipped / 0 failed
in 1,722.04 seconds. Skips were three CUDA checks, three Windows unprivileged-
symlink cases, and one intentionally vacuous identity-exclusion case.
The post-execution state/preflight/batch/launch/monitor closeout was 184 passed /
1 expected skip / 0 failed in 121.95 seconds.
The documentation-only D-152 state gate was 13 passed / 0 failed in 0.47 seconds.

Generate `SOL_BUNDLE.txt` only in the REAL repository, cumulatively against
Sol's unchanged certified review base:

    EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=4e55291 ./scripts/sol_bundle.sh \
        src/bu/runrecord.py src/bu/metrics.py src/bu/stats/gate.py \
        src/bu/stats/acceptance.py \
        src/bu/experiments/w4_threshold.py src/bu/experiments/confirmatory.py \
        src/bu/experiments/batch.py src/bu/experiments/labels.py \
        src/bu/durable.py src/bu/experiments/fit_evidence.py \
        src/bu/experiments/label_evidence.py src/bu/experiments/launch.py \
        src/bu/experiments/monitor.py \
        src/bu/experiments/preflight.py src/bu/experiments/repair_label_run.py \
        src/bu/experiments/repair_label_preflight.py \
        src/bu/experiments/repair_label_launch.py \
        src/bu/experiments/repair_label_finalize.py \
        src/bu/experiments/supervisor.py \
        src/bu/critic/loading.py src/bu/critic/split.py \
        src/bu/critic/dataset.py > SOL_BUNDLE.txt

Deliver DELTA_TO_SOL.md (undelivered deltas 64–67) with that bundle. External
Sol remains the reviewer/certifier; “Sol2” is the student's implementation-role
label and does not imply certification.
