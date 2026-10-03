# Week 8 sign-consistency specification

**Status:** fixed by D-160 before applying this metric to Experiment 2A or any
cross-family H2 evidence.  The E2A smoke unit's observed repair label was
already known.  This is therefore a post-outcome and post-collection
clarification, not an original preregistration and not an H2 verdict.

## Why this clarification exists

P§10.5 calls sign consistency “the fraction of independent runs in which the
H2 signature (high error with low disagreement) is reproduced”, and P§11.2
requires all five runs.  The plan does not provide an absolute high-error or
low-disagreement cutoff, a class aggregation rule, equality handling, or
missing-data behavior.  Those choices are result-changing and therefore are
fixed here before the metric is applied.

## Exact calculation

1. “High error” is membership in the already frozen strict baseline failure
   set: normalized movement error `> FAILURE_THRESHOLD`.  No second threshold
   is introduced.
2. “Low disagreement” is relative through the registered per-seed ratio of
   means: mean pairwise disagreement divided by
   `max(mean normalized error, 1e-6)` on that same failure set.
3. Only source-verified observed repair labels exact integer 0 and 1 are
   eligible.  Intended/construction class is never substituted for an observed
   label.  Ambiguous, undiagnosed or absent labels cannot be silently treated
   as a class.
4. Each eligible configuration-condition has equal weight.  Transition count,
   failure count and comparison-group size do not weight the descriptive mean.
5. For each exact seed 1000, 1001, 1002, 1003 and 1004, calculate the arithmetic
   mean unit ratio in observed class 0 and observed class 1.  Define
   `delta = mean_ratio_observed_1 - mean_ratio_observed_0`.
6. A seed reproduces the signature only when `delta < 0`.  Equality is not a
   reproduction.
7. Sign consistency is the number of reproducing seeds divided by five.
   Reliability is met only at 5/5.  A pattern in 3/5 is unreliable, not a weak
   positive.

## Fail-closed conditions

The complete calculation refuses duplicate unit/seed rows, a unit whose label
or comparison group changes across seeds, missing or extra seeds, either empty
observed class, nonfinite/negative ratios, non-exact labels, malformed
identities, or an undefined ratio.  The evidence adapter that supplies rows
must first account for its complete registered label inventory so omitting an
ambiguous/undiagnosed unit cannot masquerade as complete provenance.

Comparison-group IDs are retained for later group-aware inference, but this
metric does not pair, cluster, resample, test or form an interval.  It is a
reliability component only.  The Week 10 H2 adjudication must join all eligible
repair-verified families and is not permitted in a Week 8 Experiment 2A report.

## Exposure disclosure

The E1 trend result, E1 labels, first-sweep undiagnosed label and the E2A smoke
unit's observed repair label are known; all five-seed E2A baselines have
already been collected.  The remaining nineteen E2A repair labels and all E2A
H2 ratios had not been opened in this work before this rule was written.  The
rule preserves the plan's ratio endpoint and five-run requirement but fills an
underspecified aggregation boundary after an E2A outcome and after collection.
External Sol review is pending.
