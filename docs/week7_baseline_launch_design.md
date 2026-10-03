# Week-7 baseline launch — implementation design, not launch authority/evidence

2026-08-31, Sol2, following an independent read-only review. This document
records the next engineering step under the owner's continuing authorization.
No launch adapter or result is implied by this design.

## Fixed inventory and historical reuse

The D-153 preparation remains immutable: 100 Experiment-2A requirements and
675 sweep baseline requirements, rederived from the registered execution plan.
Its file SHA-256 is
`9b380e4bbefa4d3c1c5a52e6ab89f8b63cac42dbfaf90cf5b19419fcc9152044`.

Five Experiment-2A baselines overlap the completed smoke: unit `d5baeb907ac3`,
fits `f011e07e0a65-s1000` through `f011e07e0a65-s1004`, execution stage `exp2a`,
roles `exp2a` and `repair_validation`. Reverify their original source evidence
against the independently pinned historical execution commit and their separate
project-local copies. Missing or corrupt reuse evidence must stop, not permit
replacement training. These are five satisfied requirements, never five new
executions or new results. The additional smoke seeds are not Exp2A jobs.

Keep the five references outside the next batch directories. The existing
batch engine uses one execution commit and checkpoint journal per batch; placing
old fits into a new batch would misrepresent their provenance. Schedule exactly
the other 95 requirements at the new clean execution commit.

## Proposed fixed operational sweep partition

Derive all 675 baseline jobs, group by `group_of(unit, stage_of(unit))`, sort
group IDs lexicographically, then unit ID and seed. The registered sweep has
225 singleton comparison groups. One complete group (three seeds) per batch
preserves all units and groups and yields 225 deterministic batches. This
ordering must be fixed without consulting outcomes and the complete partition
must be serialized and rederived, not only its first member.

The first group is unit `0184fbfcd8b9`: position-causal, uniform, confound 0.9,
capacity family, width 64, 5,000 transitions, fully observed. Its baseline fits
are `cc428cf4ab47-s1000`, `cc428cf4ab47-s1001`, `cc428cf4ab47-s1002`, with stage
and sole role `config_sweep`. This is an operational order, not a selected
scientific subset. All remaining 672 baselines stay owed. The initial proposed
execution scope is 95 new Exp2A fits plus that complete first sweep group.

This proposal is not yet a frozen execution artifact: the implementation must
produce and validate the complete configuration-bound manifest before launch.

## Narrow adapters, unchanged historical launchers

1. `week7_launch_plan`: exact preparation binding, five reuse obligations,
   95 new Exp2A jobs, complete sweep partition, strict configuration comparison
   even when a forged document carries a recomputed digest.
2. `week7_sources`: original-commit, identity, role, sidecar and tree-digest
   reconciliation; independently verify copies; reopen at launch/resume and
   completion. Never trust a source's own commit claim as the expected commit.
3. `week7_preflight`: reuse package/device/storage checks but validate this
   exact plan; project containment, separate non-aliasing roots, same-volume
   staging/output, durable copy and readback of plan, ledger, report and canary.
4. `week7_launch`: exact preflight revalidation, common live lease, matching
   local/durable Week7 start receipts, then the existing fixed production
   executor with fit-evidence verification, mandatory fresh-process timeout,
   staging and durable incremental copies. No executor override. Preserve
   checkpoint recovery, quarantine and token-checked release.

Integration requirement from D-155's follow-up review: new sweep baselines must
capture contemporaneous train/validation/evaluation and symbolic-state anchors
before training, and bind them to completed fit evidence afterwards. Make the
companion artifacts mandatory at launch/recovery. See
`sweep_pairing_and_ordinary_labels_design.md`; the encoder's object ordering
means feature restoration cannot be checked by simply deleting columns.
This added evidence-capture interface is not yet built. Do not launch the first
sweep batch with an avoidable requirement for later historical reconstruction.

Existing Experiment-1 and smoke public entry points remain exact and unchanged;
their restrictions must not be relaxed to admit the new jobs. Reuse the lower
level batch engine behind a new narrow boundary, not the synthetic interface.

## Required verification before compute

Use fabricated evidence to exercise exact inventory and role checks, full
partition coverage/order, old-commit reuse under a new launcher commit, and
zero executor calls for reused fits. Reject absent/changed sources, forged
digests, dirty or changed Git, package/device drift, aliases, lease conflicts
and age-only recovery. Cover interrupted publication/copying, timeout and
resume without refitting. Regression-test historical launch restrictions.

D-155 refuses sweep **repairs**, not baselines. Its versioned pairing correction
and the three-seed repair-label adapter remain separate required work. Baseline
completion alone supplies no observed repair labels or exclusion counts.

All writes, scratch, caches and copies stay inside `D:/Aenv/pro/pro`. New CPU
use must be announced before execution. Source reads at reconciliation access
experimental payloads internally; metadata-only checks are not a substitute.
