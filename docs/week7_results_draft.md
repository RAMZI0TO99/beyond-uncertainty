# Week-7 estimation-family results — AI draft for student rewriting

**Authorship:** written by Sol2, not the student's independent work. The student
must check, rewrite and defend it. Numerical tables and exact bootstrap masses
in `week7_experiment_1_results.md` must accompany the final results text.

## Draft

Experiment 1 examined whether ensemble disagreement decreased as the available
training data increased within the registered estimation-family conditions.
The analysis retained five separate configurations: shape-causal environments
with uniform, sparse and clustered layouts, and colour-causal environments
with uniform and clustered layouts. Each configuration covered six dataset
sizes from 100 to 5,000 transitions and five confirmatory seeds, 1000–1004.
The resulting 150 baseline fits represent 30 configuration-conditions, not
150 independent statistical units. No additional models were trained for this
analysis, and fits serving more than one registered obligation were counted once.

For each configuration, the primary trend statistic was Spearman's correlation
between dataset size and the across-seed mean disagreement curve. Confidence
intervals used the existing exact paired seed-block bootstrap: all 3,125 ordered
resamples of the five seeds, with linear percentile quantiles. Resampling kept
each seed's complete six-size curve together. Configurations were neither pooled
nor selected according to their results. Error trends were computed by the same
method but treated only as diagnostics, rather than an additional hypothesis
criterion or a substitute for a disagreement result.

All five configurations met the fixed disagreement criterion: the entire
pointwise 95% interval lay below zero. Estimated correlations were -0.942857
for shape/uniform, shape/clustered and colour/uniform, and -0.828571 for
shape/sparse and colour/clustered. Every interval's upper endpoint was
-0.828571. The lower endpoint was -0.942857 for shape/uniform and
colour/clustered, and -1.000000 for the other configurations. These results
support a negative rank trend across dataset sizes. They do not establish
that disagreement decreases at every adjacent size or in every individual
seed: the separate plotted curves show variation, especially at small sizes.

Diagnostic error correlations were -1.000000 in every configuration, with
percentile intervals [-1.000000, -1.000000]. These zero-width intervals must
not be interpreted as zero sampling uncertainty. With only six ranked sizes
and five seeds, the bootstrap statistic has highly discrete support. The
accompanying support table therefore reports every observed coefficient and
its probability mass, including the small non--1 mass for colour/uniform
error. No undefined coefficient or bootstrap resample occurred. Enumerating
every resample removes Monte Carlo approximation; it does not guarantee exact
frequentist interval coverage.

The reporting timing and all-five summary were explicitly amended after data
collection and partial prior exposure. Development and calibration findings,
the separate smoke label and two disclosed per-fit summaries were already
known. The amendment was fixed before this coefficient analysis, but it was
not a fully blinded pre-data registration. Consequently, the conjunction is
reported as an amended operational summary, not a newly calibrated global
test or a simultaneous confidence statement.

Finally, the baseline trends do not establish that these conditions are
repair-confirmed estimation failures. Their observed labels require completed
paired data and model repairs; missing repairs are pending, not undiagnosed
outcomes or exclusions. Full interpretation of H1 remains linked to the
scheduled repair validation and Week-10 review of this same immutable report.
No new seeds, estimator changes, smoothing, preferred subset or repair-width
adjustments are introduced in response to these results.

## Student tasks still open

- Rewrite and explain the results above in your own voice; preserve the
  exposure, discrete-interval and missing-label limitations.
- Complete the separate Week-6 approximately 400-word account of the labelling
  protocol and fixed 10x data-repair budget, then explain and defend it.
- Carry the cumulative handoff and evidence to external Sol. Sol2's name and
  the owner's authorization do not constitute external certification.

Week 7 is not fully closed: paired labels, launch/throughput work and the human
writing obligations remain separate from the completed coefficient/figure work.
