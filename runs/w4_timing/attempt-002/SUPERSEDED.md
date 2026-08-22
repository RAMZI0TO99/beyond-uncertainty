# attempt-002 is SUPERSEDED by attempt-003 — provenance, not arithmetic

**The numbers here are correct and Sol reproduced them independently**: median
5.680282265679057 and maximum 6.953883384414214 local wall-hours, and a
reconciliation of measured 489.227503418002 s against 455.8492904200682 s
(median) and 572.9759819160098 s (maximum).

**What is wrong is provenance.** This record says:

    commit:     f0ac645d8a14337b24ddd82364baf46e5daf1012
    tree_clean: false

`f0ac645` **predates the timing rebuild**, which landed in `e3e9411`. So the
record was produced by an unidentified dirty working tree, and the exact harness
that generated it cannot be recovered from the commit it names. Tracking the
JSON afterwards does not repair that (Sol, delta 54).

attempt-003 re-runs from a clean, committed source tree and records
`source_commit` and `source_tree_clean_before_run` captured **before** the run,
with a SHA-256 beside the record. Its timings will differ slightly; timing
variation is expected and does not indicate disagreement.

Retained rather than deleted, because attempts are immutable.
