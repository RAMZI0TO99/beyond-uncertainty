# Week 7 per-fit storage safeguard — Sol2

This operational change preserves the existing source-bound storage floor. It
does not change a scientific constant, job inventory, seed, model, training
setting, fit identity, statistical rule, or existing evidence schema. External
Sol review remains pending.

## What changes

Before a new fit starts, the guard reopens the original launch-pinned preflight
or sweep context, checks the exact recorded roots, and measures free space
again. A changed document, changed root, linked/reparse path, unusable root,
malformed floor, or insufficient space refuses before a new attempt event or
child process. No failed fit is invented for work that never started.

| Route | New check |
| --- | --- |
| E1 repairs | Immediately before `attempt_started`, after existing recovery and environment checks. |
| E2A and first-sweep baselines | The fixed Week7 launcher always supplies a typed guard to the common engine's new-fit branch. |
| First-sweep repairs | Refresh capacity immediately before `attempt_started`, retaining the earlier full-context check and original start-bound context digest. |

The common engine's optional parameter is private. Legacy callers that do not
supply it keep their existing behavior; the fixed Week7 launcher does not omit
it. Existing complete-fit recovery paths remain before the new-child guard.
No retry, cross-commit continuation, lease override, evidence rewrite, or
storage-floor override is added. Other existing checks may still refuse a
recovery operation.

Production's recorded floor remains 8 GiB. The helper derives the floor from
the independently pinned source rather than embedding a new value. Existing
preflight nonnegative-integer and sweep positive-integer policies are retained.
The guard is a point-in-time check, not a capacity reservation, a prediction of
the next fit's size, or a monitor that terminates an already-running child.
It does not create a successful per-child storage receipt.

## Integration and provenance boundary

The already-completed first sweep and E1 production ran on clean
`1f302d1a05425827229e6ba3f41010a2b003c6f1`, without this new guard. Do not describe
the change as retroactive protection. E1's actual complete report records
474 executed/copied fits, zero resumed fits, no launch/release failure, and a
released lease. Its SHA256 is
`e7c526bda8dcd9d8ae6f94caa79f32e03021503261aeefd5e93b50a3f9ec4c26`.

While original-source label finalization ran, integration was isolated in
`D:/Aenv/pro/pro/week7-guard-integration-worktree`, branch
`sol2-week7-storage-guard`. The main checkout remained clean `master` at the
original execution commit. Tests explicitly import the isolated `src`; the
existing editable installation is not changed. No worktree switch or merge
into the main checkout is permitted until its original-source label creation
and independent readback both finish. The guarded revision also needs passing
verification before E2A starts.

E2A then requires a genuine new-source preflight at new roots. Preserve the
unstarted attempt001 readiness as historical metadata; a folder suffix is not
a failed-fit count. Do not use the old preflight under new code. CPU 4 intra-op
and 4 inter-op, the exact 95 new fits, five historical reuses, 3,600-second
per-fit timeout, and every scientific setting remain unchanged.

## Test scope and reporting limits

The original proposal supplies 31 isolated standard-library/AST-body tests.
An additive proposal supplies 17 actual-package integration cases with genuine
synthetic preflight/context metadata, original pins, real guards/journals/copy
checks, and explicit model/reader/supervisor doubles. They exercise low space
and resigned inputs before the first child and between children. Model
collection, training and real worker dispatch are blocked in these new cases.

The shared E1 fixture now constructs real preflight metadata instead of an
incomplete placeholder and retains its original validated object. Synthetic
timing/source doubles stay explicit. Temporary files live in the project cache.
Static proposal checks are not runtime integration results; actual commands,
failures, corrections and passing counts belong in the execution log.

Accounting has a separate path issue: the baseline engine's actual supervisor
base is `<registered staging root>/<batch_id>`, while E1/sweep repairs use their
staging root directly. Final accounting must check the real bases and retained
prior roots before reporting zero additional/unknown attempts. The unchanged
reporting-only accountant is not a scientific or mixed-source provenance
validator. Same-volume independent copies are not off-device backups.
