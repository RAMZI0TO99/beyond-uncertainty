# Week 7 readiness audit — source-only, no result inspection

**Date:** 2026-08-30  
**Author:** Sol2, for external Sol review  
**Scope:** repository source, tests, ledger, and the authoritative schedule only.
No Experiment-1 fit payload, result summary, metric row, figure, trend estimate,
repair verdict, or new label was opened or computed during this audit.

## Schedule boundary

The Week-7 schedule says:

- Monday: pull Experiment 1, run label assignment, and compute ambiguous and
  undiagnosed counts.
- Tuesday: regenerate Experiment-1 figures and run the Week-4 trend test on
  error and disagreement against dataset size.
- Wednesday onward: configure and then launch Experiment 2A and sweep batch 1,
  with a results-section prose obligation on Thursday.

This audit does not execute those rows. Week 6 remains formally open until the
student supplies the independent approximately 400-word own-voice explanation
recorded in D-150/D-151, and external Sol has not reviewed D-141 onward.

## Readiness findings

### 1. Monday's production label-assignment path is incomplete

`build_label_evidence()` and `summarize_label_evidence()` already implement a
source-reverifying 20-seed repair verdict and exact four-way counts. They need a
baseline, data-repair, and exactly one registered model-repair fit for every
seed. The current production orchestrator is deliberately restricted to the
single Week-6 smoke unit, while Experiment 1 produced the registered 150
baseline fits only. Baseline results alone cannot be converted into
repair-derived labels.

The unresolved inventory remains consequential beyond the smoke: 173 of 300
design units, including seven of fifteen canonical repair-validation units,
have no registered model-repair arm (D-143/D-144). No model repair may be
invented, and Experiment-1 labels or ambiguous/undiagnosed counts must not be
inferred from intended class.

### 2. Tuesday's Experiment-1 figure producer is absent

`src/bu/experiments/make_figures.py` currently registers Week-3 pilot and
Week-4 gate figures only. There is no source-bound Experiment-1 producer and no
integration test proving that a figure reopens the exact 150 immutable fits,
checks their identities/commit/roles, verifies the six-size × five-configuration
× five-seed inventory, and refuses partial or mixed evidence. Adding a plotting
function without that adapter would bypass the evidence boundary established in
D-141–D-150.

### 3. The trend statistic exists, but its production adapter does not

`src/bu/stats/trend.py::trend_test()` remains the one registered implementation
of the Spearman trend and exact paired-seed bootstrap. Its existing
`curves_from_rows()` input is the legacy row format, not verified Experiment-1
fit sidecars. No production adapter currently fixes and verifies how the five
configurations become one seed-by-size curve, requires exactly confirmatory
seeds 1000–1004, or binds every scalar to its fit evidence.

The schedule also needs interpretation before execution: Week 7 Tuesday asks
for trend coefficients and intervals, while Week 10 Monday assigns the H1
evaluation and verdict using the same test. Computing the full confirmatory
interval in Week 7 would reveal the later verdict even if the word “verdict”
were withheld. External Sol must rule whether Week 7 authorises that look, or
whether only a non-decisional figure/preparation step was intended.

### 4. The strict practical-effect boundary was inconsistent in code

The project plan states that a repair's reduction must **exceed** the frozen
20% minimum. The two executable verdict paths used `>= 0.20`, which would have
accepted exact equality. The assisted methodology prose already states the
strict rule. D-151 corrects both executable comparisons to `> 0.20` and adds
exact-boundary tests. The documented Week-6 smoke result is 22.5413% for the
accepted data repair and 4.4217% for the refused feature repair, so its label is
unchanged. External Sol is asked to review this conformance correction.

## Safe next actions and explicit stops

Safe before any further result access:

- deliver the cumulative patch series and D-141–D-151 to external Sol;
- obtain rulings on the missing model-repair assignments and Week-7/Week-10
  trend timing;
- specify, then test only on synthetic evidence, the Experiment-1 loader,
  aggregation, figure, and trend-report adapters;
- retain the fixed threshold, seeds, endpoints, and one trend implementation.

Stopped pending those rulings and the student closeout:

- no Experiment-1 scientific payload loading or figure generation;
- no confirmatory trend coefficient, interval, or H1 verdict;
- no repair-label production beyond the already completed immutable smoke;
- no Experiment 2A or sweep launch;
- no reserve draw, real critic split, or label-to-`SplitCandidate` bridge.
