# Week 7 — decisions still needed for scientific completion

Prepared by Sol2 on 2026-08-31. These are unresolved choices, not registrations
or proposed findings. The owner has deferred external Sol's review and opened
routine implementation (D-153/DEV-018). That permits building the supporting
software; it does not fill in a missing scientific specification.

## Repair labels cannot be inferred from Experiment-1 baselines

The existing source-only inventory identifies 173/300 design units without a
model-repair arm, including seven of the fifteen canonical repair-validation
units (D-143/D-144). Baseline-only results do not tell us whether either repair
passes. The implemented label path requires paired baseline, data repair and
one registered model repair with the required seed count.

Needed decision: specify how the no-model-repair conditions are to be handled
and register that rule before dependent execution. Neither declaring a no-op
to be a tested model repair, inventing a larger model, dropping conditions, nor
using intended class as an observed label is currently authorised. The new
configuration manifest deliberately adds none of these choices.

## H1 still needs an explicit production reporting rule

The registered statistic remains the existing Spearman trend with exact
paired-seed bootstrap. The new input boundary preserves all five configurations
and all five seeds over the six dataset sizes. It does not silently average
different configurations into a new endpoint or import the Week-4 all-three
gate rule as a five-configuration confirmatory rule.

Needed decision: confirm the configuration-level/global reporting rule and the
Week-7/Week-10 timing interpretation recorded in D-151. The schedule requests
coefficients/intervals in Week 7 and H1 evaluation in Week 10; an early interval
would expose the later decision even without a verdict label. Descriptive
plots are separately implemented, with no interval, hypothesis claim or repair
classification. No real Experiment-1 plot has been produced in D-153.

## Launch preparation is not launch readiness

The prepared file contains all 100 Experiment-2A and 675 sweep baseline
requirements, rather than an invented first sweep batch. Five Experiment-2A
baseline fits already exist in the Week-6 smoke and must be reconciled against
their original source-verified execution evidence. They must not be retrained
because a new stage or launcher wants them.

Needed engineering before launch: audited evidence reuse across the older fit
commit and the next execution commit; an explicit, immutable sweep batch
partition; and the same preflight, lease, process-isolation and incremental
copy checks used in Week 6. These are separate from deciding missing repairs.
No launch is requested by, or possible through, the preparation-file API.

## Human tasks remain separate

- Week 6: the student's independent approximately 400-word account of the
  labelling protocol and fixed 10× data-repair budget, followed by factual
  checking and an explain-and-defend pass.
- Week 7: the scheduled results prose must follow actual authorised analysis;
  it cannot be completed by describing synthetic tests as experimental results.

External Sol may accept, amend or reject this implementation. The record must
not call either week fully complete or certified while its required human or
scientific deliverables remain open.
