# Week 8 Experiment 2A reporting specification

**Fixed after the E2A smoke unit's observed repair label was already known, but
before opening the remaining nineteen Experiment 2A labels or any E2A H2
diagnostic in this work.**  The baseline fits also already exist, so this is a
disclosed post-outcome and post-collection reporting specification under
D-160, not pristine preregistration.

## Evidence inventory

The report must bind exactly 20 registered missing-feature units: five
canonical causal-attribute/layout configurations crossed with confound rates
0.25, 0.50, 0.75 and 0.90.  Every baseline diagnostic uses seeds 1000--1004.
Four shape/uniform units use the canonical 20-seed repair-validation label;
the other 16 use the registered ordinary three-seed label.  The one fully
completed smoke unit remains historical evidence and is not recomputed.

Every fit, label and project-copy reference is supplied explicitly and reopened
against an independently fixed execution commit and digest.  The report is
derived from sources; it does not discover directories or accept cached scalar
summaries as authority.

## Quantities reported

For every unit and seed:

- strict baseline failure count and failure-mask digest;
- failure-set mean normalized movement error;
- failure-set mean pairwise disagreement;
- the registered ratio of means with denominator floor 1e-6;
- the within-seed Pearson correlation and an explicit undefined reason where
  applicable.

For every unit, report the arithmetic mean and sample standard deviation
(ddof=1) of the five seed ratios.  Transitions are never pooled before division
and correlations are never averaged.  Repair evidence supplies observed label,
both repair effects, 95% intervals, relative reductions and acceptance reasons.
Ambiguous and undiagnosed labels remain visible.

The report also includes exact counts pooled and by intended class.  It states
`h2_verdict: null`.  Experiment 2A alone cannot decide H2; the Week 10 contrast
requires repair-verified observed classes across all canonical families.

## Scheduled checks, without outcome steering

The Week 8 schedule asks whether error remains high at the largest data size,
ten-times data repair fails, feature restoration passes and the ratio is low.
The report answers these as descriptive observed results, using the frozen
failure threshold and repair rule.  It does not assume they pass.  Experiment
2A has no data-size sweep, so no error-persistence trend or data-sweep claim is
made.

“Low ratio” has no new absolute cutoff.  Unit ratios are displayed and later
enter the relative observed-class comparison fixed in
`docs/week8_sign_consistency_spec.md`.  If Experiment 2A does not contain both
observed classes, sign consistency is not computed from this family alone; the
missing class is reported rather than supplied by intended class.

## Figures

1. **Repair-effect forest:** all 20 units, data and feature effect with 95%
   intervals, observed label and acceptance state.
2. **Ratio by confound:** five configuration panels, four confound conditions,
   all five seed points/lines plus mean and sample SD.  No pooled configuration
   curve and no H2 verdict.
3. **Secondary Pearson heatmap:** 20 units by five seeds, with undefined cells
   visibly marked and the panel labeled secondary/non-decisional.

If whole-pool error or failure prevalence is shown, it is named as such.
Failure-set mean error is not presented as evidence that error is “high” merely
because selecting by the threshold makes that statement tautological.

All figure scalars must be contained in and digest-bound to the immutable JSON
report.  Figure generation is offline and deterministic; it cannot reopen fits
or change a report.
