# Week 7 scientific amendment — D-154

Decision owner: Sol2, acting on the project owner's explicit instruction on
2026-08-31: “you can resolve those scientific you have my permetion.”
External Sol review and certification remain pending. This is a prospective
amendment to unresolved specifications, not a claim of original preregistration.

## What was already known

The 300-condition design, development experiments, permanently frozen failure
threshold, one completed 20-seed smoke label, and 150 Experiment-1 baseline fits
already exist. D-149's smoke outcome is known. D-150 disclosed two raw per-fit
Experiment-1 summaries seen during collection. No new experimental result was
opened to choose this amendment. It would be false to describe this as a fully
blinded, pre-data registration. The original plan, decisions and evidence remain
unchanged and reviewable. Any new aggregate claim must carry this limitation.

## 1. Complete the missing model intervention, without replacing existing arms

Retain feature restoration where already registered, and retain the original
capacity repair to width 256 for lower-width conditions. For full-observation
conditions already at width 256, register a distinct arm:
`capacity_extension_repair`, with fixed hidden width **512** and unchanged depth,
training procedure, original dataset size, seed policy and evaluation pool.
It is a single model, not an ensemble, and is never combined with feature or
data repair. No other width is tried if it fails. No parameter is selected by
examining outcomes. `HIDDEN_SIZES` and all existing arm meanings stay unchanged.

Reason: P§7.2 requires a real hypothesis-class intervention on the original data
budget. The old enumeration supplied neither restoration nor capacity headroom
for 173 conditions. Doubling the existing ceiling is one explicit, finite
capacity intervention, not a no-op or a guarantee of realizability. Choosing a
new arm name preserves the interpretation and identities of historical fits;
changing what `capacity_repair` means would not. Removing those conditions or
assigning their intended labels would change the target population or fabricate
counterfactual evidence. An unperformed repair is not a failed repair.

Source-only inventory before implementation: 150 estimation-family and 23
capacity-family conditions, all full-observation/width 256; seven canonical
repair-validation conditions and 166 others. Extra work is **7×20 + 166×3 = 638
single-model fits**. Total model-training requirements become **8,835**, from
8,197, including the unchanged 150-fit ablation allowance. This is a count, not
a runtime estimate: wider models cost more, and timing must be measured before
their production batch. No samples, baseline fits, seeds or reserve conditions
are added. Existing fits must be reused after source verification.

The new arm is only applicable at full observation and width 256. Conditions
with multiple pre-existing applicable repairs still fail closed rather than
selecting the best observed arm. The actual 300-condition design must expose
exactly one model repair per condition after this change. Old Config, unit,
fit and run identifiers remain stable. New-arm evidence has new arm/fit IDs.

## 2. Experiment-1 reporting and timing

Analyze each of the five registered configurations separately, using all six
dataset sizes and exactly seeds 1000–1004. Call the existing `trend_test` on
disagreement; do not pool configurations or write a second estimator. The
negative direction, strict upper-CI-bound-below-zero rule, exact 5^5 paired-seed
bootstrap and linear quantiles remain unchanged. Also apply that same statistic
to error as the schedule requests, but label it diagnostic: it neither changes
nor supplies an additional veto to the disagreement reading rule.

The overall **amended descriptive decision summary** is “all five meet the
registered disagreement criterion” only if all five do. Otherwise report which
do not, without discarding any configuration or interpreting non-rejection as
proof of no relationship. This all-five summary is fixed here, not attributed
to D-068 or transplanted silently from the three-configuration Week-4 gate. It
is not a newly calibrated omnibus test, simultaneous confidence region or
pristine pre-data confirmatory claim. Individual intervals are pointwise and
the exact bootstrap enumeration is not exact frequentist coverage.

Permit one source-bound Week-7 coefficient/interval report, matching S§W7 Tue.
Persist its complete input provenance, per-configuration estimates, diagnostics,
bootstrap support/masses and this amendment's identity. Week 10 reviews that
same report and its limitations; it does not buy another statistical look,
new seeds, a preferred subset or a different estimator. Exact regeneration is
verification, not independent replication. Undefined coefficients are explicit
failures under D-068, never silently omitted or serialized as invalid JSON.

The trend report measures the Experiment-1 operational prediction; it does not
establish model adequacy or repair-derived class membership. The full H1
interpretation and Gate-2 deliberation remain Week-10 obligations, informed by
the scheduled repair validation, with original dates unchanged. Outcomes must
not tune the new repair width or any later design choice.

## 3. Labels, existing fits and launch scope

Baseline-only Experiment-1 fits cannot produce repair labels. Week-7 reporting
must distinguish completed labels from pending paired repairs; pending is not
`undiagnosed` and is not an exclusion count. Canonical 20-seed repair validation
remains Week 9. Sweep labels retain three seeds. No intended label substitutes
for Table 2's two observed repair outcomes.

Where a baseline already carries a hypothesis/sweep role, future label adapters
must verify and use that original role's evidence at the required overlapping
seeds; they must not invent an `exp3_repairs` baseline role or retrain it merely
to obtain that name. The adapter still needs implementation and audit. Existing
smoke and Experiment-1 fits retain their original execution commits.

The 775 prepared baseline requirements are not 775 outstanding jobs: five
Experiment-2A baselines already exist. Production launches still require exact
inventory/reuse reconciliation, clean commit, isolated workers, a lease,
durable independent project-local copy and a frozen batch manifest. This
amendment supplies scientific decisions, not evidence that those engineering
checks have already passed. Reserve use, critic split parameters, H3 inference,
threshold changes and extra seeds are outside it.

## Reporting and authorship

Record these departures in methodology and the Sol handoff. The student still
owes the independent Week-6 explanation/defense and later own-voice results
writing. Neither this document nor an AI draft satisfies that requirement.

The disclosure approach follows the [Center for Open Science guidance on
changes to preregistration](https://www.cos.io/blog/preregistration-plan-not-prison):
preserve the original plan, state what changed and why, and disclose what data
were already known. This local Git record is not an external OSF registration.

## Verification record

Implementation, independent review findings, test outcomes and any subsequent
result access will be recorded in `week7_scientific_amendment_log.md`. Until
those entries exist, this document records decisions, not completed execution.
