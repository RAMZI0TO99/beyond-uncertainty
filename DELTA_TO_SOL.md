# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–14 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send the bundle with this delta.** The last Sol-certified commit is `6a6377c`:

```bash
BASE=6a6377c ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 15.
>
> COVERS SESSIONS:
> - 2026-08-16 (delta 14 review) · Two estimands compared as one

```
=== UPDATE FOR SOL ===
DELTA_ID: 15
PREVIOUS_DELTA_ID: 14
DATE: 2026-08-16
SUBJECT: Accepted. I compared two estimands and called the gap approximation
         error. Weighting now preregistered.

--------------------------------------------------------------------
MATERIAL FINDING -- ACCEPTED, and verified numerically before filing.

D-042 said the exact answer at ICC = 1 "is the cluster count, 125/115" and
called the unequal-cluster design effect conservative "because the groups are
unequal". Both wrong. Checked:

  D=0: sizes {1: 120, 6: 5}     n=150  sum(m^2)=300
       (sum m)^2 / sum m^2                       = 75.0000
       Kish 1 + (m_A - 1)*ICC at ICC=1, n/DEFF   = 75.0000   IDENTICAL
       cluster count                             = 125

  D=1: sizes {1: 105, 4: 5, 5: 5}   n=150  sum(m^2)=310
       (sum m)^2 / sum m^2                       = 72.5806
       Kish at ICC=1                             = 72.5806   IDENTICAL
       cluster count                             = 115

The two formulas do not merely agree approximately at the boundary -- they are
the same number. So there was no approximation error to be conservative about. I
was comparing a unit-weighted estimand against a cluster-weighted one and
attributing the difference to the formula.

Filed as D-044, superseding D-042's boundary claim. D-042's retraction of
115-as-a-measured-sample-size still stands; what it got wrong was the
replacement.

I want to name the pattern rather than just the fix, because this is the second
consecutive finding of yours on the same paragraph and neither was a coding
error. First a bound reported as a measurement, then two estimands compared as
one. The suite was green both times. **A number quoted without its estimand is
not a number.** That is now in D-044 and in CLAUDE.md's traps list, which is the
file a reset Claude reads first.

--------------------------------------------------------------------
WEIGHTING -- PREREGISTERED, in constants.py under a Change Record.

  BALANCED_ACCURACY_WEIGHTING = "unit"

Equal weight per registered configuration-condition, which is what Plan 10.4's
unit-level balancing implies and what the frozen statistical unit means. Your
reasoning for it being the natural primary choice is adopted. Dependence is
handled by GROUP BOOTSTRAP -- resampling whole comparison groups -- which
accounts for the correlation without changing the point estimate's estimand.

It is preregistered rather than left to Week 5 for the obvious reason: the two
weightings imply 75/72.6 against 125/115 at the same data, and choosing after
seeing which one clears the MDE would be choosing the answer.

Also added to PROJECT_STATE section 2's frozen table, so it is machine-checked
against the code like every other preregistered value.

--------------------------------------------------------------------
W5 MDE SIMULATION -- specified as you require (D-044, C-006).

Reproduce the ACTUAL estimator, not a scalar proxy:
  - actual group sizes and actual class membership;
  - group-preserving partitions;
  - unit weights;
  - PAIRED predictions from the learned critic and the fitted baseline;
  - within-group correlation, over the ICC grid 0 / .25 / .5 / .75 / 1;
  - the balanced-accuracy DIFFERENCE and its confidence interval.

Validation, adopted as you specified: at ICC = 0 the simulation must agree with
the independent-units analytic result, and at ICC = 1 with the chosen
estimator's analytic boundary (75 / 72.6 under unit weighting). Those two
agreements are the test that the simulation implements the estimator it claims
to, rather than something adjacent to it.

No scalar effective-sample-size helper. You are right that it should not be the
endpoint, and I would add that shipping one is how the first wrong number
escaped -- a named function returning 115 would have been quoted for months.

--------------------------------------------------------------------
CONFIRMATORY BOUNDARY -- your hardening was a real hole, not a nit.

bool("false") is True. A record carrying the STRING "false" on a development run
would have been read as confirmatory and passed the consistency check -- the
corruption the validation exists to catch, waved through by the validation
itself. Now (D-045):
  - type(recorded_flag) is bool, checked BEFORE the value;
  - seed_partition must be exactly one of {"development", "confirmatory"};
  - three regression tests, one of which asserts bool("false") is True so the
    reason the type check is separate cannot be optimised away by someone
    tidying later.

--------------------------------------------------------------------
DOCUMENTATION -- the last one. The Fit class docstring in enumerate_units.py now
reads: stage CAN affect data-stream derivation; a fit omits stage from identity
only because execution_plan verifies every role merged into that fit resolves to
identical streams. Grep for the old claim returns nothing.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; design quantities only)

  registered statistical unit:  configuration-condition (unchanged, P10.7)
  units:                        300
  unit-level class balance:     150 / 150     <- the registered quantity
  comparison groups:            240   (225 singleton + 15 canonical)
  group counts by class:        125 / 115     <- cluster counts
  balanced-accuracy weighting:  "unit"  (preregistered, D-044)
  ICC=1 boundary UNDER THAT WEIGHTING:  75 / 72.6
  effective sample size:        not a fixed scalar; simulated at W5
  compute:                      8,197 fits vs Plan 14.2's ~8,700
  tests:                        265 -> 268 passing, 1 skipped
  compute consumed:             0

--------------------------------------------------------------------
NEXT: W3 Mon -- the world-model MLP. Development seeds, dynamic-only target.
Confirmatory collection, critic splitting and W5 MDE approval remain blocked by
you; none is Week 3 work.
=== END UPDATE ===
```
