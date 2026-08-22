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
> - 2026-08-22 (W4 timing rebuilt) · Week 4 is complete
> - 2026-08-22 (W4/W5 audit) · Six findings in code that was specified, tested, and never probed

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
WHAT I AM ASKING FOR: review of the balancer and of the rebuilt timing evidence.

--------------------------------------------------------------------
--------------------------------------------------------------------
APPENDED (D-008: still undelivered). W4 FRIDAY TIMING IS REBUILT (D-116).

I did not wait for a further ruling: you wrote "you are authorised to complete
W4 timing with pilot-only compute". And the host question had only ONE branch
available -- there is no Kaggle access from this machine -- which is exactly the
case you said to handle with a deviation. DEV-011 now records that EVERY FIT
THIS PROJECT HAS EVER RUN HAS RUN LOCALLY and the plan's Kaggle T4 has never
been used. If you wanted the first branch, the answer is that I cannot reach it.

ALL SIX REQUIREMENTS:

  every registered fit          8,197 INCLUDING the 150 ablations, matching
                                total_model_fits exactly (was 8,047)
  collection + orchestration    2,947 collection events, counted per
                                (unit, arm, seed) condition, not per fit
  warm-up + >=3 reps            1 discarded warm-up, 3 reps per size, EVERY
                                raw observation kept in the record
  median AND maximum            both; THE VERDICT IS TAKEN ON THE MAXIMUM
  full condition, reconciled    largest repair-validation unit: 20 seeds,
                                baseline ensemble + 10x data-repair arm,
                                120 fits over 40 conditions, run end to end
  persist raw evidence          runs/w4_timing/attempt-002/timing.json, TRACKED
  honest host                   LOCAL WALL-HOURS, NOT GPU-HOURS

  RESULT   5.68 wall-hours median / 6.95 CONSERVATIVE, vs a 120-hour trigger
  RECONCILIATION  measured 489.2 s   predicted 455.8 s (median), 573.0 s (max)
                  -> measured is 7% ABOVE the median and BELOW the maximum, so
                     the conservative basis is conservative IN FACT.

--------------------------------------------------------------------
>>> THE RECONCILIATION CAUGHT A DEFECT -- IN ITSELF. <<<

attempt-001 reported measured/predicted = 0.03. That is not a modelling failure.
reconcile() filtered candidate fits on `n_transitions == 5000`, which is EVERY
unit at that size: 1,464 plan entries and 4,552 fits against the 40 entries and
120 fits that actually ran. A 37.9x INFLATION.

Corrected and re-derived from attempt-001's OWN raw data: ratio 1.028.

attempt-001 is kept, with a SUPERSEDED.md stating exactly this, because attempts
are immutable and because it is the clearest evidence in this project that an
end-to-end reconciliation does work a microbenchmark CANNOT do on itself. You
required that step; it paid for itself immediately.

--------------------------------------------------------------------
>>> AND THE EVIDENCE WAS SILENTLY UNTRACKED. THE THIRD TIME. <<<

`runs/*` swallowed runs/w4_timing/ exactly as it swallowed runs/w4_threshold/
in D-103, and as file selection swallowed delta 12's artefacts in D-041.

THREE OCCURRENCES, THREE DIFFERENT MECHANISMS, ONE SHAPE: a claim that ships
without the file behind it. Caught this time by running `git check-ignore`
before committing rather than trusting the commit -- which is only a habit,
not a mechanism, and I note that D-104's test covers attested-digest files and
would not have caught this one.

--------------------------------------------------------------------
WHAT THE NUMBER IS NOT: local wall-hours on four CPU threads, on a workstation,
NOT GPU-hours on a Kaggle T4. A cross-host comparison, informative about order
of magnitude and not like-for-like. Ablations are charged at an assumed n=5,000
because P§14.2 does not size them until Week 14; the assumption is in the record.

NOTHING HERE REVISES GATE 1, still FAIL. Condition 2's RECORDED BASIS is now a
measurement rather than a fit count; whether to re-adjudicate is yours.

NOTHING HERE REVIVES EXPANSION. D-115 fixed that arithmetic: 18.75x-33.3x is
130-232 wall-hours on this measurement -- firmer against the budget now that
ablations and collection are counted, not weaker.

--------------------------------------------------------------------
W4 IS COMPLETE. W5's only open item is your review of the balancer.

  tests      848 -> 855 passing, 2 skipped, 0 xfailed
  compute    pilot timing only, ~35 min over two attempts. Registered compute
             unchanged: 675 CPU fits.
  data seen  none. Wall time only; every run discarded its ensembles.

--------------------------------------------------------------------
--------------------------------------------------------------------
APPENDED (D-008: still undelivered). THE AUDIT YOU HAVE NOT SEEN (D-117).

The student asked for W4 and W5 to be AUDITED before this reached you. So I
probed the new code rather than re-reading it. balance.py and the rebuilt
w4_timing.py had been SPECIFIED BY YOU POINT BY POINT and covered by 23 passing
tests of mine, AND NEVER PROBED -- which is exactly the condition D-105 found
gate.py in, four of your reviews deep.

SIX FINDINGS. ALL FIXED. NONE WAS A CODING ERROR IN THE ORDINARY SENSE.

>>> 1. THE BALANCER FAILED OPEN ON THE CASE GATE 2 EXISTS TO DETECT. <<<

With one class absent from a split, m = min(n0, n1) = 0, the loop selected
nothing, and the balancer REPORTED SUCCESS WITH AN EMPTY EVALUATION SET.

This is not hypothetical. Gate 2's second condition is literally whether the
surviving per-class unit count still clears the MDE requirement, and D-089
records that usable class counts may shrink once ambiguous and undiagnosed
units are excluded. A starved split is an ANTICIPATED outcome.

And every comparable place in this project already fails closed: masked()
refuses an empty mask because "a mean over nothing is nan"; acceptance refuses
non-finite errors (D-102); trend refuses non-finite curves. THIS WAS THE ONE
THAT DID NOT. It now refuses, and the message names both routes -- genuine class
starvation, or labels that are not the integers 0 and 1.

2. STRING LABELS "0"/"1" WERE SILENTLY UNDECIDABLE, so an upstream type slip
   produced an empty split with no signal. Subsumed by the guard above. I
   checked the other half too and it is fine: NUMPY INTEGERS ARE ACCEPTED,
   which matters because a label-assignment step will emit them.

3. A DUPLICATE unit_id COLLAPSED SILENTLY. per_unit_trace_counts and
   unit_weights are keyed by unit_id, so two entries sharing one merge into a
   single row -- under-reporting the manifest and COUNTING TWO UNITS AS ONE
   under the registered UNIT-WEIGHTED estimand (D-044). Now refused.

>>> 4. THE TIMING RECORD COULD NOT BE RE-DERIVED BY MACHINE. <<<

You required a Gate 1 result be "auditable without trusting copied prose". JSON
HAS NO INTEGER KEYS, so fits_by_size round-trips as STRINGS and feeding the
stored record back into extrapolate() raises TypeError.

THE NUMBERS WERE RIGHT -- coerced, they reproduce BIT-IDENTICALLY at 5.680282 h
and 6.953883 h -- but a record only a human can re-derive by hand is not
auditable in the sense you meant. Added load_record / benchmarks_from_record /
recompute_totals, the timing analogue of recompute_threshold, with a test that
the stored record reproduces through them. It also now accepts an ATTEMPT
DIRECTORY like its sibling does; I found that by passing one and getting
IsADirectoryError, which was my probe error and a real inconsistency both.

5. _rate's FALLBACK WAS OPTIMISTIC WHILE ITS DOCSTRING CLAIMED CONSERVATIVE. It
   ended `or [max(bench)]`, charging a size larger than anything measured at the
   LARGEST MEASURED rate. UNREACHABLE in the current design -- and that is
   exactly why it would have survived: an unreachable branch with a wrong
   comment stays wrong until the design grows a larger size, and then
   under-charges silently, in the one harness that exists BECAUSE a compute
   condition was already signed off on an optimistic proxy. Now refuses.

--------------------------------------------------------------------
REGRESSIONS RE-VERIFIED after every change, which D-105 says matters most:

  W4 Tue certified gate    passed=True, 90 cells, commit 2efad25
  W4 Fri threshold         recomputes to 0.610702633857727 EXACTLY
  W4 Fri timing            recomputes under the trigger

--------------------------------------------------------------------
WHAT I THINK THIS SAYS. Six findings in code YOU specified and I tested. Each
was A GUARD THAT WAS ABSENT, A CLAIM THAT DID NOT MATCH BEHAVIOUR, OR EVIDENCE
THAT COULD NOT BE RE-DERIVED. That is the same class as D-099 and D-105, and it
is why this project audits AFTER reviewing rather than instead of it. Your
specification was not the weak point and neither were the tests; the weak point
was that nobody had made the code do anything unexpected.

  tests      855 -> 863 passing, 2 skipped, 0 xfailed
  compute    NONE. Registered compute unchanged: 675 CPU fits.
  data seen  none. Synthetic units and stored records only.
=== END UPDATE ===
```
