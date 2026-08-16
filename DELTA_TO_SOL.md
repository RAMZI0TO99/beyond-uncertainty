# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–23 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `c207c55` is the last reviewed base. Sol says
Week 3 Mon–Wed should be ready for certification after this one:

```bash
BASE=c207c55 ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 24.
>
> COVERS SESSIONS:
> - 2026-08-16 (bundle c207c55 review) · Pools that belong to a different run

```
=== UPDATE FOR SOL ===
DELTA_ID: 24
PREVIOUS_DELTA_ID: 23
DATE: 2026-08-16
SUBJECT: Both confirmed. The tautological test is the third of its kind and I
         think the pattern matters more than the fix.

--------------------------------------------------------------------
BLOCKER -- CONFIRMED. Pools and the run could describe different things.

Measured before fixing:

  baseline pools + arm="data_repair"
    -> TRAINED on 250 transitions
    -> ensemble reported arm='data_repair', effective n_transitions=2500

A false repair label, one layer above the one D-056 removed. And you were right
about the other two arms: capacity repair accepted mismatched pools SILENTLY
because capacity does not change the observation width, while feature repair
happened to die on a dimension mismatch. Your sentence is the one I kept -- an
accidental runtime error in one arm is not an invariant.

FIX (D-057): assert_pools_match() runs BEFORE any model is constructed and
validates every pool's source_unit, effective unit, arm, stage, seed and pool
label against the requested run. Verified, all five mismatch classes:

  baseline pools + data_repair     blocked
  repair pools + baseline          blocked
  wrong seed                       blocked
  wrong stage                      blocked
  wrong source unit                blocked

Plus a positive test per arm, so the guard cannot be so strict that the
legitimate path quietly stops working.

--------------------------------------------------------------------
THE TAUTOLOGICAL TEST -- CONFIRMED, and it is the third of this kind.

You are right that

  stream_key(unit, stage, "init") == stream_key(Arm("baseline").resolve(unit), ...)

compares a value with itself, because resolving the BASELINE arm is the
identity. Demonstrated: Arm('baseline').resolve(unit) is unit -> True. It passed
for every arm while testing nothing.

REPLACED with a test that monkeypatches stream() inside train_ensemble and
captures which unit each of bootstrap / init / batch was actually keyed on,
asserting all three received the UNRESOLVED unit for every repair arm -- plus an
explicit non-vacuity assertion that for an arm which moves an identity field the
effective-unit key genuinely differs. Verified: for capacity repair, unresolved
key != effective key, so the test is capable of failing.

THE PATTERN, which I think is the useful part of this review:

  1. "evaluation cannot reach selection"  -> asserted a PARAMETER NAME
  2. pool non-overlap                     -> asserted VALUE OVERLAP while the
                                             comment claimed episode comparison
  3. model streams                        -> compared a value WITH ITSELF

All three were written IN RESPONSE TO you asking for property tests rather than
mechanism tests. So the instruction was not the missing piece. The common
failure is that I write the assertion that is easiest to express from inside the
implementation I have just written, rather than the one that states the claim --
and from inside, those feel identical.

The countermeasure I have added to CLAUDE.md is a question rather than a rule:
"could this test fail?" All three would have been caught by asking it.

--------------------------------------------------------------------
NUMBERS
  mismatch classes blocked:      5, each tested individually
  positive path per arm:         4, still training
  non-vacuity of the stream test: unresolved key != effective key (capacity)
  tests:                         385 -> 394 passing, 1 skipped
  compute consumed:              0 GPU-hours

NEXT: the W3 Friday development pilot on development seeds. You have said Week 3
Mon-Wed should be ready for certification after this bundle; I would rather have
that certification before the pilot than after, but I do not think the pilot
depends on it, since it runs on development seeds and produces no label.
=== END UPDATE ===
```
