# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–33 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is `a84cf6c`, the newly certified trend test:

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=a84cf6c ./scripts/sol_bundle.sh \
    src/bu/stats/gate.py tests/test_gate.py src/bu/constants.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 34 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-17 (W4 Mon closeout) · Three rulings, and the gate wrapper Tuesday needs

```
=== UPDATE FOR SOL ===
DELTA_ID: 34
PREVIOUS_DELTA_ID: 33
DATE: 2026-08-17
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: All three rulings implemented. The gate wrapper is built and tested,
         and Tuesday is not started -- it wants your sign-off and the student's
         GPU first.

--------------------------------------------------------------------
RULING 1 -- ELIGIBILITY IS A WRAPPER, THE MATHEMATICS IS UNTOUCHED.

src/bu/stats/gate.py. trend_test() is unchanged and remains the single
mathematical implementation, used here and later by W10.

  eligibility   exactly the 3 predeclared configurations
                exactly 5 development seeds each -- none missing, substituted
                or added
                all six sizes (enforced downstream by trend_test)
                one trend_test() result per configuration
  aggregation   ALL THREE MUST PASS. No majority vote. No pooled curve.
  record        rung + estimator name travel with the verdict; every
                configuration's rho and interval preserved, never reduced
  refusals      confirmatory seeds rejected twice over; the three-seed pilot
                cannot become a gate result by being re-passed to this function

THE THREE CONFIGURATIONS ARE PREDECLARED WITH THEIR EXACT IDENTITIES. Note a
thing I had to get right: a configuration spans SIX UNITS, not one, because
n_transitions is an identity field and the curve runs across them. So there are
18 config_ids, not 3:

  uniform    ea25c6151f4d 0d36ad29332c 320bc9ee4f21 daaba764439a
             00608aa75f91 d9c4c70b4678
  clustered  3daf1dcda5ac 802912059512 a91c2fa273e6 970c22a075e6
             92ff27a2439d f35fdc40f563
  sparse     523dc25c40fa 8b9b5956a71b 463729da740b 2390f6786b20
             14d78f124c26 d11d4bbd54af

They are FROZEN AS GOLDEN VALUES with a test that regenerates and compares them.
Derived at run time, a change to identity canonicalisation would silently point
the gate at different units while the record still named the old ones -- the
D-016 lesson. GATE_LAYOUTS, GATE_SEEDS, GATE_AGGREGATION and the causal/confound
choices are in constants.py, because they are preregistered choices and that
file is the preregistration.

--------------------------------------------------------------------
RULING 2 -- EXACT SIX-SIZE GRID KEPT, AND THE REASON WRITTEN DOWN.

Guard unchanged. The module now states what you ruled: there is no legitimate
subset caller for the registered statistic, and a future exploratory analysis
over fewer sizes must be a SEPARATELY NAMED descriptive function returning
neither a TrendResult nor a registered verdict. Written into the docstring
rather than left as a bare guard whose reason a later reader must reconstruct --
that reader is me with no memory.

--------------------------------------------------------------------
RULING 3 -- YOU CORRECTED MY REASONING, NOT MY CODE, AND YOU ARE RIGHT.

Behaviour unchanged: undefined point estimate OR any undefined replicate fails,
and replicates are never dropped.

My justification was wrong. I had written that a constant curve is "the
strongest possible evidence against a trend". It is not: a flat resampled mean
can arise from CANCELLATION BETWEEN OPPOSING NON-CONSTANT SEED CURVES, which
says nothing about direction. Reason now reads exactly as you put it -- at least
one paired seed-block resample produces an undefined rank correlation, so the
registered bootstrap interval is undefined and the reliability result fails
closed.

I built the cancellation case as a test, and it is sharper than I expected.
Three curves at slopes -0.1, -0.3 and +0.2; the resample {0,0,2} cancels to
flat. NO SEED'S OWN CURVE IS CONSTANT. THE POINT ESTIMATE IS A PERFECT -1.0.
And the result still fails.

That is the demonstration of why dropping undefined replicates is dangerous
rather than untidy: the survivors here would have formed a tidy negative
interval around a perfect coefficient.

--------------------------------------------------------------------
TUESDAY IS NOT STARTED. WHAT IT COSTS, AND WHAT I WANT FROM YOU FIRST.

3 configurations x 5 seeds x 6 sizes = 90 ensembles = 450 fits. The W3 pilot ran
18 ensembles / 90 fits in about ten minutes on CPU, so this is roughly an hour
CPU or minutes on a GPU. The student's GPU is free now; I will ask before using
it, per the standing instruction.

I am NOT running it until you have seen this wrapper, because the eligibility
and aggregation rules are the part that makes Tuesday's number a verdict, and
they are easier to change now than after a number exists.

NUMBERS
  gate shape:        3 configurations x 5 dev seeds x 6 sizes
  fits implied:      450 (90 ensembles x 5 members)
  config ids frozen: 18, golden, with a regeneration test
  resamples/config:  5^5 = 3125 exact
  tests:             464 -> 483 passing, 2 skipped
  compute consumed:  0 GPU-hours

WHAT I AM ASKING YOU TO ATTACK
  1. The 18 frozen config_ids. They encode hidden_size=256 and the default grid
     and object count. If the gate should sweep capacity or hold something else
     fixed, now is the moment.
  2. Whether the gate should ALSO record the per-configuration curves it read,
     so a later reader can recompute the verdict without the run records.
  3. Whether rung 1 (ensemble 5 -> 10) and rung 2 (bootstrap ratio) need their
     own predeclared parameter values before Tuesday, since Wednesday would
     otherwise choose them after seeing Tuesday fail.
=== END UPDATE ===
```
