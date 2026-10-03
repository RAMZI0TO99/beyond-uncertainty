# Week-7 secondary diagnostic — implementation choice, not new H2 evidence

2026-08-31, Sol2, under the owner's delegated scientific authority (D-154).
The original Word plan was read directly, without modifying it. P§4.2 makes
the error/disagreement correlation secondary: it cannot confirm or falsify H2
alone. P§10.3 names a per-condition correlation but does not choose Pearson
versus rank correlation, its aggregation across seeds, or its degenerate cases.

Fix those details now, before running the diagnostic: use ordinary Pearson
correlation of the existing per-transition normalized movement error and
pairwise disagreement, separately within each condition and seed, over that
baseline seed's strict recorded failure set (`error > FAILURE_THRESHOLD`).
Use the same set as the primary ratio, never normalize again after masking.
This characterizes local difficulty within the failure population; it does
not assert the same correlation would hold over the unselected whole pool.

The primary ratio remains mean disagreement / max(mean error, 1e-6), computed
within each seed. If condition-level summaries are later needed, report the
arithmetic mean and sample standard deviation (ddof=1) across all registered
seeds, not pooled transitions. Report each seed's correlation separately. No
aggregate correlation, Fisher transform, correlation p-value, confidence
interval or correlation-based H2 decision is introduced here. A constant
vector or fewer than two failures yields an explicitly undefined correlation,
not zero. An empty failure set blocks the diagnostic, as it blocks labels;
no replacement set or alternative threshold is used.

This clarifies a previously unspecified secondary measurement after existing
data collection and D-156 trend inspection. It is not claimed as pristine
pre-data preregistration. No new outcomes were consulted to choose the rule.
The implementation and synthetic tests do not run H2 or reopen the D-156
report. H2's class contrast still requires actual repair-verified labels and
its Week-10 analysis; construction labels cannot stand in for those outcomes.
