# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–32 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is `7dbcd32`, the documentation continuation Sol
certified; the frozen implementation remains `9c0d89d`:

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=7dbcd32 ./scripts/sol_bundle.sh \
    src/bu/stats/trend.py tests/test_trend.py src/bu/constants.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 33 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-17 (W4 Mon) · The trend test, under a rule frozen before it saw data

```
=== UPDATE FOR SOL ===
DELTA_ID: 33
PREVIOUS_DELTA_ID: 32
DATE: 2026-08-17
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: W4 Mon built to your frozen rule. It passes on the pilot -- and the
         interval is coarse in a way you should rule on before Tuesday.

--------------------------------------------------------------------
THE FUNCTION, BUILT TO THE RULE YOU FROZE (D-068)

src/bu/stats/trend.py. One function, both stages, 22 tests. Every clause you
specified is implemented as written:

  statistic     Spearman's rho, ascending size vs mean pairwise disagreement
  grid          ALL SIX registered sizes
  direction     negative expected
  pass rule     the ENTIRE 95% interval below zero. Touching zero fails.
                Entirely above zero is REVERSED and fails. Constant or
                undefined fails.
  no veto       out-of-order points act only through rho and its interval
  interval      exact paired seed-block bootstrap, ordered tuples enumerated:
                3^3 = 27, 5^5 = 3125. NO RNG EXISTS.
  quantiles     2.5 / 97.5, method="linear", declared in code
  point est.    rho on the across-seed mean curve
  diagnostics   per-seed curves and per-seed rho, reported, NOT a vote

Your nine required tests all exist, plus: rho checked against scipy including
ties, the partition boundary, and that the partition label cannot change the
mathematics -- same curve at development and confirmatory seeds returns an
identical rho, interval and verdict.

ONE THING I ADDED THAT YOU DID NOT ASK FOR. The size grid must be exactly the
six registered sizes. Without that check the grid is a keyword argument, and a
five-point statistic computed over a trimmed grid is INDISTINGUISHABLE from the
registered one in every artefact that carries it -- the "drop the awkward small
end" move arriving through a parameter instead of a decision. I found it because
my first version of that test passed for the wrong reason.

--------------------------------------------------------------------
APPLIED TO THE PILOT -- DEVELOPMENT SEEDS, AND NOT THE GATE.

  rho (across-seed mean curve)   -0.9429
  95% interval                   [-0.9429, -0.8286]
  verdict under the frozen rule  PASS -- the whole interval lies below zero
  seeds / resamples              3 development / 27 exact
  per-seed rho                   -0.9429, -0.8286, -0.9429

  mean curve:  N=100 0.6014 | 250 0.8150 | 500 0.5502 | 1000 0.4159 |
               2500 0.2685 | 5000 0.2127

YOUR PREDICTION HELD EXACTLY. The N=250 peak costs ONE of fifteen pairwise
inversions. rho weakens from -1.0 to -0.9429 naturally, with nothing removed and
nothing smoothed, and the interval stays wholly negative.

--------------------------------------------------------------------
THE LIMITATION, WHICH I THINK MATTERS MORE THAN THE VERDICT.

The 27 resamples take only TWO DISTINCT VALUES:

  -0.942857  x20 of 27
  -0.828571  x7 of 27

So the "95% interval" here IS THE FULL SUPPORT of the distribution -- the 2.5th
percentile is its minimum and the 97.5th is its maximum. Its narrowness is a
property of having three highly consistent seeds, not evidence of precision.
With three blocks the exact bootstrap simply cannot resolve a tail.

I am not proposing a change to the rule. I am flagging it because SCHEDULE W4
TUESDAY RUNS THE GATE AT FIVE SEEDS ACROSS THREE CONFIGURATIONS, and at five
seeds the support is 3,125 and the quantiles mean something. If any part of
Tuesday ends up running at three seeds, it inherits this coarseness, and I would
rather that be a decision than a discovery.

Question: does the pass rule need a minimum-seed condition attached to it, or is
"the whole interval below zero" acceptable even when the interval has two atoms?
The rule as frozen would pass a three-seed result whose distribution has no tail
to speak of.

--------------------------------------------------------------------
BOUNDARIES OBSERVED

  W4 gate      development seeds only. The pilot run above is exactly that,
               and it is NOT the gate -- Tuesday is.
  W10 verdict  confirmatory only. Same function, and the partition argument
               is validated, never inferred, never pooled. Tested.
  H1 result    the coefficient above is NEVER quoted as the H1 result.
  C-010        still queued ahead of W4 Fri. Monday creates no failure mask,
               and the trend test never touches the scale.

NUMBERS
  rho / interval:       -0.9429, [-0.9429, -0.8286], PASS (development)
  distinct resamples:   2 of 27 -- the coarseness above
  pairwise inversions:  1 of 15, from the N=250 peak
  tests:                442 -> 464 passing, 2 skipped
  compute consumed:     0 GPU-hours

WHAT I AM ASKING YOU TO ATTACK
  1. The two-atom interval. Does the frozen pass rule need a minimum-seed
     condition, and if so is it three or five?
  2. Whether requiring the exact six-size grid is right, or whether a legitimate
     future caller needs a subset I have now made impossible.
  3. Whether "undefined coefficient anywhere in the resample distribution fails"
     is the correct handling, or whether only an undefined POINT estimate should
     fail while undefined resamples are dropped.
=== END UPDATE ===
```
