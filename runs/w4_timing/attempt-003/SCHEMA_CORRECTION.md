# Correction of record — attempt-003's `schema_version`

**Filed 2026-08-23 (D-119), on Sol's delta-55 ruling. The record is CERTIFIED
and UNCHANGED.**

`timing.json` stores `"schema_version": 1`. **That is a metadata defect.** The
record carries fields that version 1 never had:

- `source_commit`
- `source_tree_clean_before_run`
- `comparison_status`

These were introduced by the delta-54 provenance repair, and
`TIMING_SCHEMA_VERSION` was not bumped at the time. The stored `1` should be
read as **the provenance-aware schema**, which is now named
`TIMING_SCHEMA_VERSION = 2` in `src/bu/experiments/w4_timing.py`.

**Why this file exists instead of an edit.** Sol independently verified the
record — source commit `1a2864784b446b7e97230f3a9d1a35a27d7f489e`, clean tree
before execution, the raw repetition arithmetic, and the digest — and certified
it. Rewriting the JSON would invalidate the sha256 Sol checked and destroy the
provenance the attempt exists to establish. **No fourth timing attempt is
required and none was run.**

The record's digest is unchanged and still verifies:

```
bb504b2c1369f3bc390e4f5196207c08f94ddd74025f359486090a6aa0bb3b80  timing.json
```

**The result is unaffected.** 5.715904170861654 / 6.913811402539251 **local
wall-hours**, reconciliation 1.0684. Per DEV-011 these are local wall-hours and
are **not adjudicable** against the registered 120 **GPU-hour** trigger.
