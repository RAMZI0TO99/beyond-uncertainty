# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–50 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** The evidence archive does **not** need
resending — Sol verified it on delta 50 and closed the delivery requirement. The
bundle header names the delta it belongs to; check that line matches before
sending (D-066). `BASE` is still **`ca545ed`** until Sol certifies this closeout.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    src/bu/constants.py src/bu/models/uncertainty.py tests/test_failure_threshold.py \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 51 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (D-035 promotion) · The failure threshold is permanently frozen

```
=== UPDATE FOR SOL ===
DELTA_ID: 51
PREVIOUS_DELTA_ID: 50
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: D-035 APPLIED. FAILURE_THRESHOLD = 0.610702633857727 is frozen in
         constants.py. Narrow patch only, nothing downstream built. This is
         the closeout bundle you required before failure sets or repair labels.

--------------------------------------------------------------------
THE PROMOTION IS APPLIED, EXACTLY AS AUTHORISED.

  FAILURE_THRESHOLD = 0.610702633857727

  in src/bu/constants.py. Exact, unrounded, permanently frozen.
  repr  0.610702633857727
  hex   0x1.38ae040000000p-1
  type  plain Python float, not a numpy scalar -- a numpy scalar would carry
        a dtype into every downstream comparison and could silently demote a
        float64 comparison to float32.

Your five instructions, each discharged:

  1 exact constant, not rounded          DONE, pinned by test at bit level
  2 no caller-selectable override        DONE, see below
  3 strict > boundary preserved          DONE, and it is NOT academic
  4 regression tests, constant+boundary  DONE, 11 tests, proved falsifiable
  5 ledger + state files updated         DONE, D-107; §2 now says FROZEN

--------------------------------------------------------------------
>>> THE STRICT BOUNDARY DECIDES REAL LABELS. <<<

TWO TRANSITIONS IN THE CALIBRATION POOL SIT EXACTLY AT THE THRESHOLD.

Under `>` they are not failures. Under `>=` they would be. I measured this
rather than assuming the boundary was a formality, and it changes how the
regression test had to be written -- see the weak-test admission below.

--------------------------------------------------------------------
NO CALLER-SELECTABLE OVERRIDE.

ScaledEvaluation.failure_mask() takes NO arguments. The reasoning is C-010's
exactly, which you ruled on in D-076: from_pool takes no mask so the scale
cannot be subset-derived; failure_mask takes no threshold so the failure set
cannot be re-cut. A value a caller can pass is a degree of freedom somebody
eventually uses.

It scores the ENSEMBLE MEAN PREDICTION -- what the calibration measured --
NOT the mean of the members' errors. Those are different numbers, and using
the second while calibrating on the first would move the failure rate off 5%
with nothing raised. Pinned by a test that also asserts the two definitions
still differ on its fixture, so it cannot go vacuous.

--------------------------------------------------------------------
VERIFIED AGAINST YOUR EVIDENCE, NOT ASSERTED.

  95th pct of the stored balanced pool   EQUALS the constant exactly
  balanced pool                          36,927 = 9 x 4,103
  failures on it                         1,846 = 4.9991%
  your unbalanced sanity check           1,879 / 37,406  -- REPRODUCES
  transitions exactly at the boundary    2

--------------------------------------------------------------------
THE TESTS WERE PROVED FALSIFIABLE BY MUTATION.

Each mutation fails EXACTLY ONE test, which is the coverage claim:

  round the constant to 0.6107026338577   -> exactness test fails
  change `>` to `>=`                      -> boundary test fails
  add threshold=None override             -> no-override test fails

The no-override test asserts by CALLING failure_mask with a threshold and
requiring TypeError, not by inspecting the signature for an absent parameter
name. That second shape is what D-055 and D-057 were written about and it
passes whether or not the property holds.

--------------------------------------------------------------------
>>> TWO WEAK CHECKS OF MY OWN, CAUGHT BEFORE THEY SHIPPED. <<<

I am reporting these because you would have found them, and because the
pattern is the one you have named four times now.

(a) MY FIRST BOUNDARY TEST WAS A TEST OF PYTHON. It asserted `errors > t` on
    a tensor the test itself constructed. That exercises the comparison
    operator and would have passed no matter what failure_mask did -- it was
    not connected to the implementation at all. Rewritten to drive the real
    constructor: the pool is [-1, 1, -1, 1], whose population std is exactly
    1.0, so the scale is exactly 1 and the error is exactly the offset. One
    transition's error is then EXACTLY the threshold after the real scale and
    error computation. It also asserts the fixture is still exact, so it
    cannot silently stop testing the boundary.

(b) MY NEW §2-vs-CODE CHECK WAS VACUOUS. I added the threshold to
    test_frozen_constants_match_the_code, which searches the WHOLE state
    file. The value appears FIVE times in it. I proved this by rounding §2's
    row to `0.6107` -- AND THE TEST STILL PASSED. Now scoped to §2 alone and
    shown to fail. This is D-071 and D-105's shape again: a check that passes
    because the thing it checks is somewhere else.

--------------------------------------------------------------------
A PROCESS FAILURE, ON RECORD.

Proving falsifiability the first time, I mutated constants.py and
uncertainty.py and restored them with `git checkout` -- while the promotion
patch was STILL UNCOMMITTED. The restore reverted to HEAD and destroyed it.
Retyped in full; nothing was lost, and the suite would have caught a partial
restore. GIT CHECKOUT RESTORES TO THE LAST COMMIT, NOT TO THE STATE YOU WERE
IN. Mutation-test against committed work or a copy. Redone that way.

--------------------------------------------------------------------
SCOPE HELD.

NO failure set built. NO repair label built. NO downstream analysis. Gate 1's
signed FAIL, the seed-cluster acceptance analysis and every prior scope ruling
are untouched. No rerun -- the attempt is final.

HOUSEKEEPING: PROJECT_STATE.md hit its 500-line paste cap, so the three
delivered 2026-08-20 entries moved to PROJECT_STATE_ARCHIVE.md in full,
nothing condensed, with a pointer left in §7. The file is 482 lines.

--------------------------------------------------------------------
NUMBERS (D-011)

  constant          0.610702633857727  (hex 0x1.38ae040000000p-1)
  boundary          strictly greater; 2 transitions sit exactly at it
  balanced pool     1,846 / 36,927 = 4.9991% failures
  unbalanced check  1,879 / 37,406 = 5.0233%
  tests             819 -> 830 passing, 2 skipped, 0 xfailed (11 new)
  compute           NONE this session. 675 CPU fits total, 0 GPU-hours
  data seen         none beyond D-103's recorded calibration
  bases             bundle diff from ca545ed; execution base 93dc296

--------------------------------------------------------------------
WHAT I AM ASKING FOR: certification of this closeout, which is the gate you
set before downstream failure sets or repair labels. I have started nothing
downstream and will not until you certify.
=== END UPDATE ===
```
