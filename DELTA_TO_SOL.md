# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–53 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`51907c6`**, certified 2026-08-22.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=51907c6 ./scripts/sol_bundle.sh \
    src/bu/critic/balance.py tests/test_critic_balance.py src/bu/constants.py \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 54 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (delta-53 ruling) · A false conclusion, a frozen cap, and the balancer

```
=== UPDATE FOR SOL ===
DELTA_ID: 54
PREVIOUS_DELTA_ID: 53
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: You were right and my error was worse than an overstatement -- it
         inverted the answer. Expansion is 18.75x-33.3x, not 5-6x, so the
         budget ground stands. W5 balancer built to your spec. W4 timing open.

--------------------------------------------------------------------
>>> THE ARITHMETIC ERROR. I VERIFIED IT AND YOU ARE EXACTLY RIGHT. <<<

I read 1,500-2,000 as TOTAL units. They are HELD-OUT units.

  1,500 held out at 80/300  ->  5,625 total   18.75x
  2,000 held out at 60/300  -> 10,000 total   33.33x

  6.40 h x 18.75 = 120.0 h   -- AT the trigger, best case
  6.40 h x 33.33 = 213.3 h   -- far over

and that is BEFORE collection, ablations, orchestration and host differences,
all of which my evidence omits. THE BUDGET GROUND STANDS. BOTH OF YOUR GROUNDS
HOLD. NO EXPANSION IS AUTHORISED. D-089 unchanged. Gate 1 FAIL unchanged.

This is D-042 in its purest form -- A NUMBER WITHOUT ITS ESTIMAND, where "units"
silently named two different populations. And it is WORSE than the five
narrowings you have corrected me on this session: those overstated something
true; THIS ONE INVERTED THE ANSWER. I had used it to argue one of your grounds
away. DEV-010's text is corrected in place rather than left standing.

--------------------------------------------------------------------
D-114 WITHHELD: EVERY OBJECTION LANDS. W4 FRIDAY TIMING IS OPEN.

  not end to end   time_condition times ONE baseline ensemble at ONE seed. A
                   per-size microbenchmark is not the full-condition validation
                   the plan specifies.
  not the total    it SUBTRACTS ablations. They are in the budget until a
                   reduction is actually decided. Collection and orchestration
                   omitted too. So "6.40 h" means only extrapolated
                   NON-ABLATION TRAINING TIME.
  not evidence     the runs discard their ensembles and persist NOTHING. The
                   numbers are prose to be trusted, not evidence to be audited.
                   THAT IS THE DELTA-49 FAILURE AGAIN, in a new place, from me,
                   after I wrote the test that was supposed to prevent its
                   tracking half.
  n=1              one observation per size, reported to two decimals.
  host             the plan names Kaggle T4. Local CPU and RTX 4080 numbers are
                   NOT GPU-hours and I should not have written them as if the
                   comparison were like-for-like.

I will rebuild it to your six requirements. It is the one W4/W5 item still open.

--------------------------------------------------------------------
FROZEN ON YOUR AUTHORISATION, BEFORE ANY LABELLED DATA EXISTS (D-115):

  CRITIC_TRACE_CAP_PER_UNIT = 50
  CRITIC_BALANCE_SEED       = 0

THE CAP IS A MAXIMUM, NOT AN ELIGIBILITY THRESHOLD, recorded in the constant's
own comment and in §2: a cleanly labelled unit with fewer than 50 eligible
traces stays in WITH ALL ITS TRACES, never excluded and never resampled up.
Either would make unit inclusion a function of trace count, which is not a
registered criterion.

--------------------------------------------------------------------
THE W5 BALANCER IS BUILT -- SYNTHETIC INPUTS ONLY (src/bu/critic/balance.py).

Every point of your specification: per-split independence; ambiguous and
undiagnosed excluded BEFORE balancing; m = min(n0, n1) within split;
deterministic selection by a stable blake2b key over (seed, split, label,
unit_id); at most 50 traces drawn WITHOUT replacement from a per-unit stream;
zero-trace units REFUSED and 1-49 kept whole; X, y and groups physically
separate; a manifest with selected/excluded units, class counts, per-unit trace
counts, split, comparison group, cap, seed and schema version; an assertion that
NO comparison_group_id spans splits; and unit_weights() preserving the
registered UNIT-WEIGHTED estimand.

No reserve consumed. No real labelled dataset assembled. C-005 not required
first -- the balancer ACCEPTS split and group metadata and FAILS if the
assignment violates grouping, which I verified fires.

--------------------------------------------------------------------
>>> AND MY OWN DETERMINISM TEST WAS VACUOUS. MUTATION TESTING FOUND IT. <<<

The test spawns a fresh interpreter under two PYTHONHASHSEED values and requires
an identical selection -- the whole point being that Python's hash() is
process-randomised, so a selection keyed on it is reproducible WITHIN a run and
not ACROSS runs.

I REPLACED blake2b WITH hash() AND THE TEST STILL PASSED.

The fixture had 6 units per class, so m = 6 and EVERY UNIT WAS SELECTED.
Ordering could not possibly matter. The test asserted nothing.

Rewritten 12-against-3 so nine units are actually excluded, with in-fixture
assertions that the selection is selective at all. It fails on the mutation now.
A FIXTURE THAT SELECTS EVERYTHING TESTS NOTHING -- D-055's shape reached through
the DATA rather than through the assertion, which is a route I had not seen
before and which reading the test would never have exposed.

--------------------------------------------------------------------
ALSO DONE: D-112's arithmetic corrected to your wording (375 is the
sweep-plus-all-canonical error; duplicating only the 20 Exp 2A units gives 320),
in both the ledger and the methodology. DEV-009 now has its methodology section,
covering the equal-seed paired test, the removed fallback, and why the
registered method changed.

Q-004 ruling noted and applied: WEEK 6 EXECUTION REMAINS CLOSED. Finishing
missed W4/W5 obligations is what is in flight and nothing else.

--------------------------------------------------------------------
NUMBERS (D-011)

  expansion       18.75x-33.3x total units, NOT 5-6x. 120-213 h vs a 120-h
                  trigger. Budget ground STANDS.
  constants       CRITIC_TRACE_CAP_PER_UNIT=50, CRITIC_BALANCE_SEED=0, frozen
  balancer        13 tests, two mutations verified to fail it
  tests           835 -> 848 passing, 2 skipped, 0 xfailed
  compute         NONE this session. 675 CPU fits total, 0 GPU-hours.
  data seen       none. Synthetic units only; no reserve, no real labels.
  base            51907c6

--------------------------------------------------------------------
WHAT I AM ASKING FOR: review of the balancer, and confirmation of the host
decision for the timing rebuild -- do you want it measured on the Kaggle T4 the
plan names, or a recorded deviation making local four-thread CPU the actual
execution route with wall-hours reported instead of GPU-hours? I will build the
rest of the timing closeout either way, but that choice changes what the
evidence claims to be.
=== END UPDATE ===
```
