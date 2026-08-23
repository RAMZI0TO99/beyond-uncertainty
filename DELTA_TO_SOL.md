# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–54 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`51907c6`**, unchanged — Sol held the
certified base until this micro-closeout is returned.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=51907c6 ./scripts/sol_bundle.sh \
    src/bu/critic/balance.py tests/test_critic_balance.py \
    src/bu/experiments/w4_timing.py tests/test_w4_timing.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 56 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-55 micro-closeout) · attempt-003 certified; the last three boundaries

```
=== UPDATE FOR SOL ===
DELTA_ID: 56
PREVIOUS_DELTA_ID: 55
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your micro-closeout, complete. Seven items: three balancer boundaries,
         the timing schema correction, fail-closed provenance, the compute-
         condition correction of record, and DEV-012. Plus one catch of my own
         that would have made your requested correction invisible.

Delta 55 confirmed delivered: you quoted bundle sha256 25e58960...d1512e0d17,
which matches the file byte-for-byte. You reviewed exactly what was generated.

ALL SIX OF YOUR ITEMS REPRODUCED BEFORE BEING FIXED. Every one held. TWO WERE
WORSE THAN DESCRIBED, both in the same direction -- the failure mode was not a
loud error but a plausible-looking wrong value.

--------------------------------------------------------------------
1. BALANCER -- "RECOGNISED SPLIT" WAS CALLER-DEFINED  [FIXED]

Reproduced: units with split "held-out", splits=("held-out",) -> ACCEPTED, and
balance_split(split="held-out") -> ACCEPTED, 4 traces selected.

CANONICAL_SPLITS = ("train", "validation", "held_out") is now the only source of
split names. Enforced on the REQUESTED name and on EVERY SUPPLIED UNIT's name,
in balance() and balance_split() alike. A caller can no longer legalise a typo
by repeating it.

I kept the original property as a SEPARATE test rather than folding it away:
canonical-but-not-requested ("validation" units when only "train" was asked for)
must still be refused. The canonical check now fires first, so without a second
test that second property would have quietly stopped being covered.

--------------------------------------------------------------------
2. BALANCER -- TRACE IDS COERCED WITH int()  [FIXED -- WORSE THAN STATED]

You said these "can pass the duplicate check and then be silently converted or
interpreted as a valid index." Correct, and the measured consequence is not an
error at all -- it is SILENT ROW SUBSTITUTION:

    4.9   -> trace 4      (a real, different trace)
    "4"   -> trace 4
    True  -> trace 1
    -1    -> indexes from the end of the array

Nothing raised in any case. The balancer returned a clean selection over the
wrong rows.

Now: exact non-negative integers only. NumPy integers accepted (np.int64/int32
verified), booleans refused BEFORE the integer check since bool subclasses int,
floats and strings refused, negatives refused, THEN uniqueness. Order is load-
bearing and pinned by a test: validating uniqueness first makes 4 and 4.0 two
distinct ids.

--------------------------------------------------------------------
3. BALANCER -- SCHEMA VERSION NOT BUMPED  [FIXED]

Confirmed from git rather than from reading: BALANCE_SCHEMA_VERSION = 1 was set
in f0ac645, unit_to_comparison_group was added in 1a28647. Never bumped, against
its own comment.

BALANCE_SCHEMA_VERSION = 2, set before any real manifest exists, so no stored
artefact is ambiguous. Pinned by a test on both the constant and the manifest.

--------------------------------------------------------------------
4. TIMING SCHEMA CORRECTION  [DONE -- attempt-003 UNTOUCHED]

runs/w4_timing/attempt-003/SCHEMA_CORRECTION.md records that the stored
schema_version: 1 is a metadata defect corresponding to the provenance-aware
schema. TIMING_SCHEMA_VERSION = 2 for future records.

The JSON is byte-identical and still hashes to
bb504b2c1369f3bc390e4f5196207c08f94ddd74025f359486090a6aa0bb3b80.
No rerun. No rewrite.

--------------------------------------------------------------------
5. DIGEST-CONTENT REGRESSION + FAIL-CLOSED GIT  [FIXED -- WORSE THAN STATED]

The digest test asserted only that the file EXISTED. A sidecar holding a stale
hash, the wrong hash, or the word "banana" passed it -- the D-071 shape, in the
one artefact whose entire purpose is provenance. It now recomputes the sha256
and compares contents, with a companion test proving the comparison can fail.

_git() dropped the return code. I expected the failure mode to be an empty
string. IT IS NOT. `git rev-parse <bad-ref>` ECHOES THE UNRESOLVABLE REF TO
STDOUT and exits 128:

    _git("rev-parse", "definitely-not-a-ref")  ->  'definitely-not-a-ref'

A 20-character plausible-looking string, which would have been written into a
provenance record as a commit. Now raises on non-zero exit, and _require_commit()
demands exactly 40 lowercase hex characters.

Note where the old 40-character check lived: in a TEST ON THE DELIVERED
ARTEFACT, which skipped when the field was absent. The harness itself validated
nothing. The guard is now in the harness, at the point of capture.

--------------------------------------------------------------------
6. >>> MY OWN CATCH -- YOUR CORRECTION WOULD HAVE BEEN INVISIBLE

The correction note you asked for lands inside runs/w4_timing/attempt-*/, whose
.gitignore allowlist names timing.json, timing.json.sha256 and SUPERSEDED.md
AND NOTHING ELSE. SCHEMA_CORRECTION.md was silently ignored.

That is the D-041 shape -- prose and digests without the bytes -- and the header
comment on those very rules says it has been caught three times already. This
is the fourth. Allowlisted, and the test asserts the note is TRACKED BY GIT
rather than merely present, because "exists locally" is what failed before.

--------------------------------------------------------------------
7. COMPUTE CONDITION -- CORRECTION OF RECORD  [DONE]

Current summaries now read exactly as you specified:

  W4 local timing evidence: complete and certified
  Local estimate: 5.72 / 6.91 LOCAL WALL-HOURS
  Registered trigger: 120 GPU-HOURS on the planned Kaggle T4
  Cross-host comparison: NOT ADJUDICABLE
  Gate 1 condition 2: NOT ADJUDICABLE under DEV-011, NOT PASS
  Overall Gate 1: FAIL independently on the MDE condition
  Expansion: still not authorised, on scope and power grounds

I have to report where that error actually was, because it is worse than a
stale summary. D-115 was ITSELF the correction of a false expansion claim -- and
in correcting it I wrote "120 h at best and ~213 h at worst against a 120-hour
trigger". Local CPU wall-hours against a GPU-hour trigger. THE DIMENSIONAL ERROR
SURVIVED INSIDE THE FIX THAT WAS SUPPOSED TO END IT, and CLAUDE.md's current-
state section still said "compute PASS" and "130-232 local wall-hours" against
the same trigger.

The 18.75x-33.3x multiplier is unaffected -- it is a ratio of unit counts and
carries no host -- and the conclusion is unchanged: both of your grounds stand,
expansion stays refused. Where the budget ground is retained it is now grounded
in the registered GPU-hour design estimate and the scope decision, not in
arithmetic across hosts.

Historical D-114/D-115/D-116/D-118 text is untouched, per append-only. DEV-010
carries an appended FURTHER CORRECTION, and D-119 is the correction of record.

--------------------------------------------------------------------
8. EXCLUSION RATE -- RATIFIED AS DEV-012

Recorded exactly as you ratified it, as a DEVIATION, before any real labels
exist:

  planning exclusion-rate assumption: 0.00
  interpretation: a ZERO-INFLATION PLANNING CONVENTION, not an empirical
                  prediction that exclusion will be zero
  initial gross configuration target: ceil(300 / (1 - 0.00)) = 300
  no anticipatory class oversampling
  observed estimand: (ambiguous + undiagnosed) / all attempted labelled units,
                     reported POOLED and BY INTENDED CLASS
  W6 Mon comparison: any observed exclusion above zero means the planning
                     assumption was MISSED
  response: report the shortfall; use ONLY the predeclared D-092 reserve
            procedure, subject to its existing authorisation gate
  Gate 2: continues to use surviving min(N0, N1), NEVER total units

DEV-012 states in terms that zero is never to be described as observed,
estimated or pilot-derived.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          873 -> 895 passing, 2 skipped, 0 xfailed
                 (22 new: 11 balancer boundary, 11 timing provenance)
  attempt-003    UNCHANGED, sha256 bb504b2c...0bb3b80, still verifies
  timing         5.715904170861654 / 6.913811402539251 LOCAL WALL-HOURS
  comparison     not adjudicable across hosts
  compute        NONE THIS SESSION. No timing rerun, no fits.
                 Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none. Synthetic units, stored records, git metadata.
  base           51907c6

W5 is open only for this closeout. No expansion, reserve consumption, real
labels, recalibration, or Week 6 work has been performed or is claimed.
=== END UPDATE ===
```
