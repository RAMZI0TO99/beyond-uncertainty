# attempt-001 is SUPERSEDED by attempt-002 — do not cite its reconciliation

The **raw measurements here are valid**: the benchmark repetitions and the
full-condition wall time all happened as recorded.

**One derived field is wrong.** `reconciliation` was computed by a version of
`reconcile()` that filtered candidate fits on `n_transitions == 5000` — which is
*every* unit at that size, 1,464 plan entries and 4,552 fits, rather than the 40
entries and 120 fits of the single unit that actually ran. That is a **37.9×**
inflation and it appears here as a measured/predicted ratio of **0.03**.

Corrected in `reconcile(..., unit=...)`. Re-derived from this attempt's own raw
data, the ratio is **1.028** (median basis) — 480.1 s predicted against 493.7 s
measured. attempt-002 re-runs everything with the fixed code.

Kept rather than deleted, because attempts are immutable and because the
discrepancy is the clearest evidence in the project that the reconciliation step
does its job: it caught a defect, in itself.
