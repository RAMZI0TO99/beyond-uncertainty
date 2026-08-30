Patch series for the 2026-08-30 owner-authorised Sol2 session (DEV-015)
========================================================================

This directory contains exactly the three transferable commits described by
delta 67. The local parent `264138128fe221f9d5fc90d040be877fc2eaa3b9` is only
reconstructed snapshot history; it is NOT remote ancestry or Sol's review base.

Precondition in the REAL repository:

1. Checkout exact target `66edf4a11dce39b91974d5c331cca81424f83b6e`.
2. Follow `session_2026-08-29.patchseries/README.txt` exactly: verify committed
   preimage blobs and apply 0001, 0003, 0004, 0005, 0006, 0007, 0008 and 0009.
   Skip only snapshot-local 0002 as that README directs.
3. Require a clean tree and a green suite before continuing.

Then verify this directory against `PATCH_SHA256SUMS.txt` and apply, in order:

    git am 0001-*.patch 0002-*.patch 0003-*.patch

  0001  D-141 provenance, loader, C-005, gate and threshold evidence hardening
  0002  D-142/D-143 Week-6 harness, pure labels, leakage firewall and durable
        batch orchestration with pre-launch multi-role refusal
  0003  D-141..D-143, DEV-015, delta 67 and current handoff/state documentation

Do not use `git am --3way`. A context mismatch means the precondition is not the
reviewed tree and must be reconciled explicitly. After application, run the
full suite. The audited CPU-host result is 1,205 passed / 4 skipped / 0 failed
in 412.07 seconds; CUDA hosts may skip fewer device tests.

Generate `SOL_BUNDLE.txt` only in the REAL repository, cumulatively against
Sol's unchanged certified review base:

    EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=4e55291 ./scripts/sol_bundle.sh \
        src/bu/runrecord.py src/bu/metrics.py src/bu/stats/gate.py \
        src/bu/experiments/w4_threshold.py src/bu/experiments/confirmatory.py \
        src/bu/experiments/batch.py src/bu/experiments/labels.py \
        src/bu/critic/loading.py src/bu/critic/split.py \
        src/bu/critic/dataset.py > SOL_BUNDLE.txt

Deliver DELTA_TO_SOL.md (undelivered deltas 64–67) with that bundle. External
Sol remains the reviewer/certifier; “Sol2” is the student's implementation-role
label and does not imply certification.
