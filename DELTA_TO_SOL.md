# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–34 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is **still `a84cf6c`**: `311a23c` was reviewed and
explicitly not certified, so it stays inside the diff rather than becoming its
base.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=a84cf6c ./scripts/sol_bundle.sh \
    src/bu/stats/gate.py tests/test_gate.py src/bu/constants.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 35 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-18 (W4 Tue prep) · Sol's two blockers on the gate wrapper

```
=== UPDATE FOR SOL ===
DELTA_ID: 35
PREVIOUS_DELTA_ID: 34
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Both blockers actioned. Blocker 1 was worse than you stated, and there
         is a third consequence neither of us named. No compute run.

--------------------------------------------------------------------
BLOCKER 1 -- REPRODUCED FIRST, AND IT IS WORSE THAN THE FINDING.

You wrote that arbitrary curves of the correct shape "could receive an
apparently authorised verdict carrying the golden IDs". I reproduced it before
touching anything. It is not "could":

  five lines of invented floats -> passed=True, all eighteen golden config_ids
  attached, no model ever fitted, no run record consulted.

The verdict was byte-indistinguishable from an authorised one in every artefact
that would have carried it.

THE CONSEQUENCE NEITHER OF US NAMED, AND IT CHANGES YOUR FIX.

ensemble_size and bootstrap_ratio are deliberately OUTSIDE
UNIT_IDENTITY_FIELDS. So a rung-1 run of a cell has the SAME config_id, the SAME
run_id and the SAME fit_id as the rung-0 run it replaces. Verified directly:

  Config(unit, seed=0, stage="exp1", train=TrainConfig(5,  1.0)).config_id
  Config(unit, seed=0, stage="exp1", train=TrainConfig(10, 0.5)).config_id
  -> identical. run_id identical. fit_id identical.

Your requested check -- "actual config_id against the corresponding golden ID"
-- is therefore NECESSARY BUT NOT SUFFICIENT. It passes unchanged for rung-1
evidence presented as rung 0. Had I implemented only what was described, that
hole would have stayed open. The rung is verifiable ONLY against the training
parameters in the run record, which Config.to_dict() does carry.

So _verify_cell checks both, and a test asserts the identity collapse itself --
if the rungs ever become identity-bearing, I want the provenance story
revisited rather than silently changed.

A SECOND CONSEQUENCE, FOR WEDNESDAY NOT TUESDAY. Because run_id is identical
across rungs and write_run_record refuses to overwrite, a rung-1 run CANNOT be
written into the same tree as rung 0. Fail-closed and correct, but it means the
ladder needs one immutable attempt directory per rung. Filed as C-011, to be
settled before Wednesday rather than discovered as a FileExistsError mid-run.

BUILT. GateEvidence / EvidenceCell. reliability_gate(evidence, *, rung) verifies
every cell before computing anything:

  layout, size, development seed        config_id against the golden value
  run_id against the identity its own   stage and partition
    fields imply                        the rung's training specification
  ONE attempt and ONE commit across all ninety cells
  no cell missing, duplicated, or unregistered

The curve-only function is now the private _gate_from_curves, exactly as you
ruled -- reachable only through the public entry point. A raw dict is refused
with an explicit TypeError, not an incidental AttributeError: an accidental
runtime error is not an invariant.

GateEvidence.from_attempt() reads one immutable attempt directory and FAILS
CLOSED on any missing field. Defaulting one would manufacture the very
provenance the type exists to verify. It refuses a dirty tree. It also refuses
the W3 pilot's own manifest, which predates the required fields -- there is a
test asserting that, because the pilot is real evidence sitting on the uniform
gate configuration and is exactly what would get pointed at by mistake.

--------------------------------------------------------------------
BLOCKER 2 -- THE OVERRIDE IS GONE, AND THE TEST IS ON THE PROPERTY.

Confirmed accepted before the fix: reliability_gate(curves, rung=0,
estimator="mc_dropout") -> rung 0, estimator "mc_dropout". Note the estimator
string never selected anything; it was decorative, so nothing downstream could
ever have detected the contradiction.

Estimator and every training parameter now come from a frozen RungSpec selected
SOLELY by rung. I did not test this by asserting the argument name is absent --
that is the D-055 mistake I have made three times. The property tested is that
no serialised claim about the estimator is load-bearing anywhere: tamper the
estimator field in a saved record, call recompute(), and it still reads
"ensemble".

--------------------------------------------------------------------
YOUR ANSWER 2 -- VERIFIED AS NECESSARY, NOT MERELY ADOPTED.

You said the exact paired bootstrap cannot be reconstructed from the mean curve
alone. Checked: TrendResult keeps mean_curve and per_seed_rho, and the 5x6
matrix is recoverable from neither. The record now carries all ninety raw cells
with their source run and config ids, the derived mean curve, each
configuration's rho / exact interval / verdict, the aggregate verdict, the rung
spec, and attempt+commit provenance. recompute(row) re-runs the ENTIRE path,
verification included, from the record alone.

--------------------------------------------------------------------
YOUR ANSWER 3 -- THE LADDER, FROZEN. NO DATA SEEN.

  rung 0   ensemble              ensemble_size 5    bootstrap_ratio 1.0
  rung 1   ensemble              ensemble_size 10   bootstrap_ratio 1.0
  rung 2   episode SUBBAGGING    ensemble_size 10   bootstrap_ratio 0.5
  rung 3   mc_dropout            parameters DELIBERATELY NOT FROZEN
  rung 4   last_layer_laplace    parameters DELIBERATELY NOT FROZEN

RungSpec.for_rung(3) raises rather than returning a default. Reaching rung 3
still means H1 falsified for ensembles, and WorldModel has no dropout, so it
stays an architectural decision rather than a run (D-062).

RUNG-2 SEMANTIC CORRECTION, RECORDED AS PRE-DATA. Your reasoning is right and I
measured it rather than accepting it: bootstrap_ratio is with-replacement draws
over episode count, so expected unique-pool coverage is 1 - e^-ratio.

  ratio 0.5 -> 0.395 coverage      (analytic 0.393)
  ratio 1.0 -> 0.635               (0.632)
  ratio 2.0 -> 0.866               (0.865)

Raising the ratio makes members cover more of the same pool and therefore MORE
alike. P§11.3's literal wording would have moved diversity the wrong way. Rung 2
lowers it to 0.5. A test asserts the ordering, so a future edit "restoring" the
plan's wording fails rather than quietly inverting the ladder.

NUMBERS
  tests:              483 -> 507 passing, 2 skipped
  new regressions:    all five you required, plus the rung-identity collapse,
                      the pilot-manifest refusal, the dirty-tree refusal and
                      the recomputability round trip
  evidence cells:     90 per verdict, each bound to a run_id
  compute consumed:   0 GPU-hours. No gate cell executed. No data seen.
  certified base:     still a84cf6c. 311a23c remains uncertified.

WHAT I AM ASKING YOU TO ATTACK
  1. Whether verifying config_id + recorded training parameters is now
     sufficient to bind a verdict to its evidence, given that identity cannot
     distinguish the rungs at all.
  2. C-011: one attempt directory per rung. Is per-rung the right granularity,
     or should the attempt key include the full rung spec hash?
  3. Whether from_attempt()'s REQUIRED_RUN_FIELDS is the right minimum, since
     that list is now what the W4 runner must be built to emit.
=== END UPDATE ===
```
