# D-155 follow-up — pairing and ordinary labels (design only)

2026-08-31, Sol2. Independent read-only review; no implementation, experimental
payload inspection, test or training in this design pass. D-154's choices remain
fixed. This is not a certified procedure or evidence that the guard is cleared.

## Separate baseline-anchored sweep procedure

Keep every legacy stream function, version-3 key and canonical evidence meaning
unchanged. Retain D-155's refusal in the legacy runner. Add a narrow registered
procedure for sweep-only repairs that distinguishes the `exp3_repairs`
obligation from the `config_sweep` data-generation stage. The latter anchors
all six data-purpose keys; model-purpose keys remain based on the original unit.
No caller-selected stage or bypass flag is appropriate.

A versioned contract must bind original unit, arm, seed, baseline identity,
independently expected baseline commit and evidence digest, normalization,
data/model stream keys and dataset-compatibility evidence. Paths must not define
the contract: a verified independent copy is the same scientific anchor.

Retain Config-derived identities as obligation references. Corrected physical
executions need procedure-qualified fit/run identities bound to the baseline
execution digest. A legacy repair with the same Config fit ID cannot satisfy
this new procedure. Introduce a separate evidence schema and strict reader;
never teach the legacy schema to accept contradictory stage/identity meanings.
Launch, checkpoints, deduplication, copying and recovery must use the qualified
physical identity while accounting still counts each scientific obligation once.

Candidate modules are `repair_pairing.py` (registered contract and pool
collection) and `paired_repair_evidence.py` (execution, persisted evidence and
strict reload). Reuse necessary execution/scoring helpers only with regression
coverage preserving legacy defaults. Ordinary `RunLogger.start(Config)` cannot
stamp procedure-qualified physical identity without a truthful new record path.

## Dataset compatibility, not key equality alone

Data repair needs an exact original-training-data prefix in the 10x pool and
unchanged validation/evaluation. Capacity repair needs unchanged raw pools.
Feature restoration needs the same underlying trajectories/targets, with the
restored data projected through the baseline encoding; equal action/episode/
step arrays alone are insufficient. All arms retain the baseline full-pool
normalization before failure masks.

Current sidecars do not contemporaneously bind complete training/validation
pools. For genuinely old evidence, deterministic reconstruction requires the
original generating source and environment, and a new external-to-source anchor
artifact must distinguish reconstructed from contemporaneous digests. Missing
compatibility blocks execution, never authorizes retraining or editing a source.

Before future sweep baseline collection, require contemporaneous anchor capture
in the new baseline launch path. No sweep baseline is documented as completed
in this session's source inventory. Do not create avoidable provenance gaps
and then rely on a reconstruction that could have been captured originally.
The read-only addendum identified the capture hook; it is not implemented here.

Add a versioned collection entry point sharing the existing loop. Capture each
symbolic `(state, action, next_state, episode, step)` immediately after the
environment transition, without consuming randomness, altering policy state
or collecting extra transitions. Before training, persist train/validation/
evaluation arrays and full symbolic anchors, bind their metadata/digests, and
verify them against the exact pool objects consumed. After fit completion,
publish a separate binding of anchor digest to fit-evidence digest, avoiding
circular hashing. Companion artifacts preserve legacy baseline Config IDs and
fit schema; the new sweep launcher and recovery boundary require them.

The existing dataset retains encoded observations and ordered transition IDs,
but not latent GridStates. Full symbolic states must capture agent position
and every object's position, shape, colour and activation. **Do not project by
merely deleting feature columns:** the encoder sorts object slots by visible
descriptors, so feature restoration can reorder them. Re-encode identical
symbolic states through each arm's encoder and compare exact arrays. Keep all
latent anchors experimenter-only, outside both model inputs and critic X.

## Separate ordinary-unit label boundary

`ordinary_label_evidence.py` should derive eligibility from the registered
`exp3_repairs` obligation, covering 285 units rather than only 225 sweep units:

| Conditions | Original baseline role | Required label seeds |
|---|---|---|
| 15 canonical validation conditions (existing boundary) | `repair_validation` projection | 1000–1019 |
| 60 other canonical conditions | `exp1`, `exp2a` or `exp2b` | 1000–1002 |
| 225 sweep-only conditions | `config_sweep` | 1000–1002 |

Require nine verified sources for an ordinary label: three arms at three seeds.
Reuse original baseline roles/commits, not fabricated `exp3_repairs` baseline
projections. Canonical ordinary repairs retain their valid old procedure;
sweep repairs require the new contract. Keep the existing 20-seed public label
API exact. A private shared array-assembly helper may be extracted, but public
stage/pairing checks must not be weakened.

The existing equal-seed acceptance test already supports three seeds (two
degrees of freedom); retain its thresholds, weighting, fail-closed behavior
and four-way label mapping. Group by the authoritative baseline stage, not the
repair stage. Missing/unperformed repairs are pending; invalid evidence or an
empty required failure set is blocked. Neither state is an observed ambiguous
or undiagnosed label, and neither supplies an exclusion rate or critic input.

## Tests before execution

Preserve the 8,100-key legacy fingerprint, Config identities, canonical role
projections and exact 20-seed refusals. Cover all sweep units, assigned arms and
seeds; compare actual datasets, prefixes and feature projections. Reject wrong
commits/anchors, rewritten contracts, missing compatibility or changed scales
before training. Prove qualified identity separation, copy stability, cross-
schema refusal and resume without refitting. Reopen all nine sources on label
creation/reload; test missing, duplicate, extra/development seeds and all pending
states. C-007 remains incomplete until the final label-to-critic bridge is
independently verified.

No additional scientific choice was identified for this correction or the
already-registered three-seed inference. Changing empty-failure-set treatment,
eligibility, inference or seed counts would require a separate amendment.
