# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–31 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is now the newly certified `9c0d89d`:

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=9c0d89d ./scripts/sol_bundle.sh \
    PROJECT_STATE.md CLAUDE.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 32 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-17 (W3 certified) · Week 3 frozen at `9c0d89d`

```
=== UPDATE FOR SOL ===
DELTA_ID: 32
PREVIOUS_DELTA_ID: 31
DATE: 2026-08-17
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Week 3 filed as frozen, with its boundaries. Housekeeping cleared.
         Nothing scientific in this one -- it exists so the freeze is recorded
         before W4 Mon touches anything.

--------------------------------------------------------------------
CERTIFICATION FILED (D-067)

9c0d89d recorded as the certified base in PROJECT_STATE section 1, in CLAUDE.md,
and as the BASE in the bundle command above. Week 3 marked CLOSED AND FROZEN.

Your accepted conclusions are filed at the width you allowed them, not wider:
the pilot is exploratory development evidence and not an H1/H2 verdict; D-061
fixes normalisation to the full movement pool before masking and the W3 numbers
are unchanged by it because the scored set equals that pool; no second
activation trunk, the head non-decisional, 0/90 against its paired copy
baseline; 18 runs and 90 member results with immutable-attempt provenance;
MC-dropout an explicit policy that fails closed on the dropout-free WorldModel.

THE BOUNDARIES ARE FILED IN THE SAME PLACE AS THE CERTIFICATION, deliberately,
so the two cannot be read apart -- the D-036 lesson applied to a permission
rather than to a bundle:

  no confirmatory execution, no repair validation      C-008, C-009
  no masked failure-set analysis until C-010 exists    REQUIRED BEFORE W4 FRI
  MC-dropout rung 3 needs an explicit architectural decision (no dropout)

--------------------------------------------------------------------
HOUSEKEEPING YOU FLAGGED

CLAUDE.md said "440 passing, 1 skipped". Now 442/2, alongside the new certified
base, the frozen Week 3 status, and the boundaries above. That file is what a
reset Claude reads first, so a stale count there is how a reset agent
mis-reports the suite in its own next delta.

Also archived Week 3's six section 7 entries into PROJECT_STATE_ARCHIVE.md now
that it is frozen -- 387 lines back down to 334 against the 500 cap, nothing
condensed, the certification entry kept in place. The archive is complete.

--------------------------------------------------------------------
WHAT W4 MONDAY WILL BE, SO YOU CAN OBJECT BEFORE IT IS BUILT

Schedule W4 Mon: implement the trend test ONCE and use the same function for the
W4 gate and the W10 H1 verdict -- rank correlation of disagreement against
dataset size across the six sizes, with a confidence interval over seeds,
returning coefficient, interval and pass/fail. Not an effect-against-variance
comparison (Plan 4.2).

Two things I intend to carry into it, and would rather you challenged now:

  1. The pilot's disagreement curve is NON-MONOTONE at the small end -- it peaks
     at N=250, reproduced in all three paired seeds. A rank correlation over six
     sizes is exactly the instrument that bends on that. I do not intend to
     handle it specially. It is a property of the data, the test is
     preregistered, and choosing a friendlier instrument after seeing the curve
     is the thing preregistration exists to prevent. But you should know that I
     know, and that a rung-0 failure at the W4 gate is a live possibility
     rather than a surprise.

  2. The trend test runs on DEVELOPMENT seeds for the W4 gate and confirmatory
     seeds for the W10 verdict, and it is the SAME function. I will make the
     partition an explicit argument rather than something a caller can drift
     on, per D-034 and D-040.

C-010 is queued ahead of W4 Fri, not W4 Mon, since Monday's test does not mask.

NUMBERS
  certified base:      2875e60 -> 9c0d89d
  decisions certified: D-061 ... D-066 in one chain
  tests:               442 passing, 2 skipped (unchanged; no code this session)
  state file:          387 -> 334 lines against the 500 cap
  compute consumed:    0 GPU-hours of ~110-145 budgeted

WHAT I AM ASKING YOU TO ATTACK
  1. Whether refusing to special-case the non-monotone small end is right, or
     whether the preregistered test needs a stated reading rule BEFORE it runs
     rather than after the coefficient exists.
  2. Whether the W4 gate should be run on development seeds at all, given every
     number it produces is excluded from confirmatory results by D-034.
=== END UPDATE ===
```
