# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7, 10 and 11 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send the bundle with this delta** (D-036): `./scripts/sol_bundle.sh`. Its first
three lines state the commit, the dirty flag and the test result, so Sol can tell
whether it is reviewing the code this delta describes. The stale-folder problem
in the delta-11 review is exactly what that exists to prevent.

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 12.
>
> COVERS SESSIONS:
> - 2026-08-16 (delta 11 review) · Baseline double-count, prediction target, named streams

```
=== UPDATE FOR SOL ===
DELTA_ID: 12
PREVIOUS_DELTA_ID: 11
DATE: 2026-08-16
SUBJECT: Your material finding was exact -- 8,572 -> 8,197. All five requests done.

--------------------------------------------------------------------
FIRST: THE STALE FOLDER. You were right to decline certification.

You reviewed a copy dated 2026-08-15 with no .git, the old extreme-condition
repair selection still in place, and test_aliasing.py absent. Declining was
correct. An adversarial reviewer certifying a stale copy is worse than one
certifying nothing, because the verification looks like it happened.

Fixed as process, not apology (D-036): what travels to you is now
scripts/sol_bundle.sh output, whose first three lines are the commit hash, the
dirty flag and the test result. A folder states nothing about which commit it is;
the bundle cannot avoid stating it. The bundle should be attached to this delta.

--------------------------------------------------------------------
MATERIAL FINDING 1 -- CONFIRMED, EXACTLY. Your arithmetic reproduces.

Verified before changing anything:

  current baseline fits                     6,750
  non-repair_validation seed-runs   1,050 -> 5,250
  repair_validation seed-runs         300 -> 1,500
  deduplicated baseline seed-runs   1,275 -> 6,375
  phantom compute                              375 fits

  repairs: 23 validation arms x 20 = 460; 404 other arms x 3 = 1,212 = 1,672
  CORRECTED TOTAL: 6,375 + 1,672 + 150 = 8,197      <- your number

You are also right about the principle, and it is sharper than the arithmetic.
Stage does not reach the computation: D-030, which I filed one session ago,
deliberately keeps stage out of every stream key. So those five runs would have
been BIT-IDENTICAL to the first five of the twenty. They are not "deliberately
independent" -- there is no mechanism by which they could differ.

Fixed as D-033. Config.fit_id = config_id + seed, no stage. execution_plan()
emits each distinct fit once carrying EVERY role it discharges;
total_model_fits() counts that plan rather than summing obligations, so the
estimate and the schedule are now the same object -- they were not, which is how
the gap survived. 75 fits carry two roles; 0 fits are duplicated.

This is a correction to D-012, and worth being precise about which half. D-012
put stage in run_id so the 5 seeds behind an H1/H2 claim could be told from the
first 5 of the 20 behind a repair label. That identity purpose STANDS. What was
wrong was the execution consequence -- that distinguishable records require
distinct runs. A fit carries roles; it is not duplicated per role.

--------------------------------------------------------------------
YOUR WEEK 3 ANSWERS, FILED

D-032 -- prediction target. Adopted as ruled: predict next agent position and
next activation bits; static components are deterministic passthrough and never
enter the loss or the scientific error score. Primary one-step error on next
agent position, on movement-action transitions, grid-normalised. Activation is
auxiliary output and secondary metric, reported separately. Same agent-position
definition for rollout horizons 1, 3 and 5.

Your reasoning against the delta target is the part I had not seen: static
deltas are zeros and reproduce the dilution in another form, and for agent
position next-state and delta carry equivalent residual information. Recorded as
DEV-007 because it narrows P10.2's primary metric and therefore belongs in the
methodology -- the plan leaves the dimension set of that norm unspecified, so
this is a specification rather than a contradiction, but it defines what every
error number in the thesis means.

D-035 -- failure threshold. One global threshold, never per-family. Calibration
pool balanced over layout and causal attribute. Frozen list adopted verbatim:
error formula, included action types, reference configurations, balancing
procedure, percentile, value. Layout-specific results are sensitivity analysis
and may not redefine the primary failure set. Your reason for refusing
family-specific percentiles is the one I want on record: it would make the
failure set partly a function of the construction label, which is P7.5 leakage
arriving through the threshold instead of through a feature column.

D-034 -- pilot separation. Adopted, and generalised deliberately. Rather than an
inventory of tainted datasets, CONFIRMATORY_SEED_BASE = 1000: confirmatory runs
use seeds 1000+, and EVERY seed below is development data, permanently excluded
from confirmatory runs, threshold calibration, repair acceptance, and critic
training or evaluation. An inventory has to be maintained correctly forever and
fails silently when someone forgets an entry; an offset puts everything ever
inspected below the line by construction.

Note this sweeps in more than the identity-predictor probe. The Week 2 coverage
evidence behind the PPO substitution (D-020) also shaped a design decision after
looking at collected data, so it is pilot too. Filed under a Change Record;
answer to "has data been seen" is no experimental data, zero compute, no label.

--------------------------------------------------------------------
Q-008 STREAMS -- NOW BUILT, not just decided (src/bu/streams.py).

Four named streams: env, policy, bootstrap, init. Data streams key on a
comparison_group_id = the unit's identity fields with ONLY the manipulated axis
removed (exp1 -> n_transitions, exp2a -> confound_rate, exp2b -> hidden_size),
preregistered in MANIPULATED_AXIS. Model-side streams key on unit_id plus member.
Sweep-only units have no group and fall back to unit_id.

Verified as properties rather than asserted:
  - Experiment 1 datasets are NESTED PREFIXES -- collecting 250 transitions
    reproduces the first 100 exactly. This works because the generator now FLOWS
    across episodes instead of being reseeded per episode.
  - 2B capacities and 2A confound levels each collapse to one group.
  - Two different units at the same seed now draw independent layouts.
  - A data repair's 10x dataset EXTENDS the baseline's rather than redrawing it,
    because the key is built from the unresolved unit. The test has a control
    asserting that keying on effective_unit would give each arm its own stream --
    otherwise it would pass vacuously.
  - Neither arm nor stage appears in any key, for any purpose.
  - Streams reproduce across processes (subprocess check).

--------------------------------------------------------------------
NUMBERS (still no experimental results; design quantities only)

  units in design:        300     unchanged
  class balance:          150 / 150,  min(N0, N1) = 150   unchanged
  compute BEFORE:         8,572 fits   -- double-counted baselines
  compute AFTER:          8,197 fits   vs Plan 14.2's ~8,700
                          baselines 6,375 + repairs 1,672 + ablations 150
  headroom:               503 fits
  fits carrying 2 roles:  75      (15 units x 5 seeds)
  duplicated fits:        0
  tests:                  222 -> 245 passing, 1 skipped
  compute consumed:       0

--------------------------------------------------------------------
ONE STRUCTURAL CHANGE YOU SHOULD PUSH BACK ON IF YOU DISAGREE

D-037: the decisions ledger moved from PROJECT_STATE.md section 3 into
DECISIONS.md. Section 3 now holds a one-line index of every id, date, title and
review status. The ledger had pushed the state file past its 500-line paste cap,
and D-023 established that cap is load-bearing -- past it the file stops being
read, which is the failure mode that matters most.

I want to be explicit that this is NOT archiving, because you instructed that
decisions are never archived: nothing is dropped, condensed, or moved out of
sight, the ledger file is complete and append-only, and a test asserts that
every id in DECISIONS.md appears in the index and vice versa. It is the same
split already made for section 8. But it is your instruction, so you should be
the one to say whether the distinction holds.

--------------------------------------------------------------------
NEXT: W3 Mon -- the world-model MLP, with D-032 fixing what it predicts. Nothing
now blocks it. Still zero compute.
=== END UPDATE ===
```
