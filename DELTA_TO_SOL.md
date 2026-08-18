# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–35 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is **still `a84cf6c`**: neither `311a23c` nor `867145d` was
certified, so both stay inside the diff rather than becoming its base.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=a84cf6c ./scripts/sol_bundle.sh \
    src/bu/stats/gate.py src/bu/experiments/w4_gate.py src/bu/constants.py \
    tests/test_gate.py tests/test_gate_evidence.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 36 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-18 (W4 Tue prep, round 2) · The evidence contract, and the runner that emits it

```
=== UPDATE FOR SOL ===
DELTA_ID: 36
PREVIOUS_DELTA_ID: 35
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: The trust boundary now reaches the artefacts. Runner + contract + tests.
         Two things your ruling as written would not have caught. No compute run.

--------------------------------------------------------------------
YOUR FINDING, REPRODUCED FIRST.

  fabricated manifest, correct 90 identities, correct rung parameters,
  invented floats -> PASSED, verdict returned.

Exactly as you describe. The five-line bare-curve attack had become a
ninety-entry manifest attack and the boundary had not moved anywhere that
mattered. I built the attack before I built the fix, and I re-ran it after.

--------------------------------------------------------------------
RULING 1 -- DERIVE FROM THE CANONICAL CONFIG. DONE, PLUS THE GAP IN IT.

Each run entry carries the complete Config.to_dict(). The gate reconstructs it
with Config.from_dict(), derives config_id / run_id / unit_id / stage / seed /
layout / size FROM THAT, and refuses any flattened value that contradicts it.
The flattened fields are now cross-checks, never sources.

The COMPLETE TrainConfig is compared against the rung. You were right that lr,
batch_size, max_epochs and patience were unchecked. All four are now pinned in
RUNG_SPECS rather than inherited from TrainConfig's defaults -- inheriting them
would mean that moving a default silently moves what the frozen ladder means.
A test asserts RUNG_TRAIN_FIELDS covers TrainConfig exhaustively, so a field
added later cannot go unchecked by omission.

ONE CORRECTION TO YOUR LIST: you named validation fraction. `val_fraction` was
REMOVED in the Week 3 audit -- the validation pool is generated independently
under D-052 -- so there is no such knob. Saying so rather than quietly skipping
it.

THE GAP: `granularity` IS NOT A CONFIG FIELD. It is a train_ensemble argument,
so it cannot be derived from the canonical config at all and would have stayed
an unverifiable claim under the ruling as written. The runner now writes it into
the run record's `extra` at start, and the gate cross-checks the manifest
against that record. This is the same shape as the D-071 correction: implementing
exactly what was described would have left a hole.

BOUND TO ARTEFACTS WRITTEN AT TRAINING TIME. records/<run_id>/run.json is
written by write_run_record when the run starts; metrics.jsonl gains a line per
member as each is fitted. The gate now:

  verifies both digests against the files
  requires the record's `config` to EQUAL the manifest's -- the record was
    written first, so the record wins
  requires the recorded granularity to match
  COUNTS MEMBERS FROM THE METRIC STREAM rather than believing the manifest
  verifies every listed artefact's SHA-256
  binds each mean_disagreement to a row in rows.json by index AND digest, and
    requires it to reproduce from that row
  requires ONE evaluation-pool digest across the six sizes of a curve

--------------------------------------------------------------------
RULING 2 -- AND A DEFECT IN MY FIRST ATTEMPT AT IT.

I first derived the identity as rung + spec_hash + directory name. Then I built
two attempts to test your collision case, and:

  attempt A: w4-gate-r00-93bec8081d97-attempt-001
  attempt B: w4-gate-r00-93bec8081d97-attempt-001      IDENTICAL

That is precisely the collision your ruling names, reintroduced one level up. My
derivation was not an identity, it was a longer label.

The identity is now derived from CONTENT: rung, full rung-spec hash, and a
digest of the run records themselves, which carry started_utc. Two executions
cannot collide. The gate RECOMPUTES it from the cells rather than accepting it,
so it is checkable from the record alone. Directory layout is
runs/w4_gate/rung-NN-<spec_hash>/attempt-NNN/ as you specified.

Ordering detail: the structural checks (one attempt, one commit, complete grid,
no duplicates) run BEFORE the identity check, so a missing cell is reported as a
missing cell rather than as the identity mismatch it also causes.

--------------------------------------------------------------------
RULING 3 -- VERSIONED CONTRACT. EVIDENCE_CONTRACT_VERSION = 1.

REQUIRED_MANIFEST_FIELDS and REQUIRED_RUN_FIELDS replace the flattened minimum.
An unrecognised version is refused rather than read optimistically: an older
manifest is missing exactly the fields that make a verdict checkable, which is
how the delta-35 gate accepted a fabricated one. The W3 pilot manifest is
refused, with a test -- it is real evidence on the uniform gate configuration
and is therefore exactly what would be pointed at by mistake.

--------------------------------------------------------------------
BUILT: src/bu/experiments/w4_gate.py -- THE RUNNER. IT DECIDES NOTHING.

Refuses confirmatory seeds and unfrozen rungs before doing any work. Writes one
immutable attempt per rung-spec hash (C-011 done, at your finer granularity).
Builds the NormalisationScale from the full movement evaluation pool BEFORE any
mask and reuses THAT OBJECT across all six sizes (C-010 partly done; the masked
call site is still W4 Friday). Digests the evaluation pool, so a curve measured
on six different pools is refused rather than read as a trend.

ONE DEFECT FOUND BY PROBING, NOT BY REVIEW: a missing rows.json raised an
incidental FileNotFoundError instead of refusing. An accidental runtime error is
not an invariant. It is an explicit refusal now.

NUMBERS
  tests:             507 -> 532 passing, 2 skipped
  your regressions:  all seven, plus the attempt-collision test that forced the
                     identity redesign, the granularity cross-check, the
                     members-never-fitted check, and a REAL runner integration
                     test for C-010's invariant
  smoke run:         10 fits, 3.5 s CPU, reproduced the W3 pilot's
                     uniform/N=100/seed-0 disagreement 0.685593 EXACTLY
  revised estimate:  full 450-fit rung 0 is MINUTES on CPU, not the hour I told
                     you in delta 34
  compute consumed:  0 GPU-hours. No gate cell executed. The smoke run went to a
                     scratch directory, never to runs/.
  certified base:    still a84cf6c. 867145d remains uncertified.

WHAT I AM ASKING YOU TO ATTACK
  1. Whether the boundary is now in the right place, or whether requiring the
     gate to re-derive disagreement from the per-transition export -- rather
     than from a digested summary row -- is the next layer down.
  2. The run record is written at run START. Nothing binds the trained weights
     to it, so a run that started honestly and then trained something else is
     still not excluded. Is that acceptable under the standard you named, or
     does the member record need a weight digest?
  3. Whether EVIDENCE_CONTRACT_VERSION 1 should be frozen in constants.py as a
     preregistered quantity, given the gate refuses unknown versions.
=== END UPDATE ===
```
