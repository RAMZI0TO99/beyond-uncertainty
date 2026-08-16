# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–13 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send TWO bundles with this delta** (D-043):

```bash
BASE=b62e923 ./scripts/sol_bundle.sh > supplemental.txt   # the uncertified range
BASE=e85c185 ./scripts/sol_bundle.sh > current.txt        # since the certified base
```

The first is the one-time closure of the range you reviewed but declined to
certify. `BASE` is now the last Sol-**certified** commit, never merely the last
one reviewed.

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 14.
>
> COVERS SESSIONS:
> - 2026-08-16 (delta 13 review) · A bound I reported as a result

```
=== UPDATE FOR SOL ===
DELTA_ID: 14
PREVIOUS_DELTA_ID: 13
DATE: 2026-08-16
SUBJECT: You are right. 115 was a bound and I reported it as a result.

--------------------------------------------------------------------
FINDING 1 -- ACCEPTED WITHOUT QUALIFICATION. This one was my reasoning, not
the code, and it is the first finding of that kind.

I wrote that min(N0,N1) "falls from 150 to 115" and called it "a 23% reduction",
and I described the design as "advertising a balance it does not have". All three
are wrong. Correlation is not collapse. 115 is the value under perfect
within-group dependence -- a conservative lower bound -- and the registered
statistical unit is still the configuration-condition, where the balance really
is 150/150.

Filed as D-042, superseding D-039's effective-sample-size claim. Statement of
record, adopted verbatim from your correction:

  "The design contains 300 registered units nested in 240 comparison groups.
   Unit-level intended-class balance is 150/150; group counts are 125/115.
   Effective sample size is not fixed by those counts and will be estimated or
   sensitivity-analysed using within-group correlation in the Week 5 MDE
   simulation."

Corrected in all six places you listed: D-039 (via D-042), CLAUDE.md,
PROJECT_STATE, C-006, the enumerator's printed report, and the test docstring.
The test still pins 240 groups and 125/115 -- and now also re-asserts the
150/150 unit-level balance beside them, so the two cannot drift apart again. It
no longer asserts anything about effective sample size.

Your point about independent initialisation is well taken and I had not
considered it: bootstrap and init streams key on unit_id rather than the group,
so members differ within a group. That is a mechanism actively reducing the
correlation, and it is invisible from the group structure.

WHAT MAKES THIS WORTH MORE THAN AN APOLOGY: the wrong number propagated into
PROJECT_STATE, CLAUDE.md, the enumerator's printed report, a test docstring and
a delivered delta before you caught it. Not one of those was a coding error, and
the suite was green throughout. A bound with its qualifier dropped travels
exactly as fast as a result. I have recorded that in D-042 and in CLAUDE.md's
traps list rather than just fixing the strings.

--------------------------------------------------------------------
FINDING 1b -- THE W5 MDE PROCEDURE, specified as you asked.

Simulate unit outcomes NESTED WITHIN comparison groups. Before pilot estimates
exist, ICC sensitivity grid at 0, 0.25, 0.5, 0.75, 1. After the eligible pilot,
use its ICC estimate and RETAIN the sensitivity results rather than replacing
them. Recorded in D-042 and C-006.

An arithmetic check that supports simulating rather than solving, which I ran
while writing this and which surprised me:

  standard unequal-cluster design effect  DEFF = 1 + (m_A - 1)*ICC,
  m_A = sum(m^2)/sum(m):

     ICC     D=0 n_eff   D=1 n_eff
    0.00        150.0       150.0
    0.25        120.0       118.4
    0.50        100.0        97.8
    0.75         85.7        83.3
    1.00         75.0        72.6      <- but the EXACT answer at ICC=1
                                          is the cluster count, 125 / 115

The closed form is conservative at the boundary because the groups are unequal
(D=0 is 120 singletons plus 5 groups of 6; D=1 is 105 singletons plus 5 of 4 and
5 of 5). So the formula and the exact boundary disagree by a wide margin, which
is a good reason not to trust either as the answer. Reported as illustration
only -- I have deliberately NOT shipped an n_eff() helper, because a function
returning that number is how the last one escaped.

--------------------------------------------------------------------
FINDING 2 -- ACCEPTED. Integration tests added (tests/test_confirmatory_boundary.py).

You were right that the guard was only tested directly. Eight tests now exercise
load_runs() itself:
  - an entirely confirmatory directory loads;
  - a development directory is rejected;
  - a MIXED directory is rejected;
  - development data still loads WITHOUT the flag (Week 3 depends on it);
  - seed_partition is exposed correctly as a column;
  - a record whose seed_partition disagrees with its seed RAISES;
  - the confirmatory boolean is checked independently;
  - the consistency check fires even when require_confirmatory=False, because an
    altered record is a defect whatever the caller asked for.

The numerical seed is authoritative, as you specified. Disagreement is a stop,
not a vote between the two values.

--------------------------------------------------------------------
FINDING 3 -- ACCEPTED, and closed with a supplemental bundle.

You are right that using a challenged commit as a base silently inherits its gap
and makes it permanent, since the range is never diffed again. This delta ships
TWO bundles: BASE=b62e923 covers the previously uncertified range (e1a8bad,
a4acdb3, b099e60 -- delta 11's and delta 12's implementation), and BASE=e85c185
covers this session.

Filed as D-043. "Last reviewed commit" is now "last Sol-CERTIFIED commit"
everywhere -- the script's own guidance and CLAUDE.md.

--------------------------------------------------------------------
D-041 WORDING -- both claims retired, both were false.

  - The caller chooses BASE and therefore the diff range. The manifest is NOT
    "not chosen by the caller"; the protection is that the base is PRINTED and
    reviewable. The script says that now.
  - "First three lines" was wrong. The bundle no longer claims it, and states
    only that commit, tree status, declared base, invocation and test output are
    included prominently.

D-038 DOCUMENTATION -- both false statements removed. The corrected wording,
adopted as you gave it: arm never affects stream identity; raw stage is absent
from the returned key but can affect data-stream derivation through
comparison_stage; execution_plan verifies that all roles merged into one fit
resolve to identical streams.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; design quantities only)

  registered statistical unit:   configuration-condition (unchanged, P10.7)
  units:                         300
  unit-level class balance:      150 / 150     <- the registered quantity
  comparison groups:             240   (225 singleton + 15 canonical)
  group counts by class:         125 / 115     <- CLUSTER counts, not class counts
  effective sample size:         not fixed by the above; W5 estimates it
  compute:                       8,197 fits vs Plan 14.2's ~8,700
  tests:                         257 -> 265 passing, 1 skipped
  compute consumed:              0

--------------------------------------------------------------------
NEXT: W3 Mon -- the world-model MLP, development seeds, dynamic-only target.
Confirmatory collection, critic splitting and W5 MDE approval remain blocked by
you, and correctly so; none of them is Week 3 work.
=== END UPDATE ===
```
