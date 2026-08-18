# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–36 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** The bundle is **always `SOL_BUNDLE.txt`**, and
its header names the delta it belongs to — check that line matches before
sending (D-066). `BASE` is **still `a84cf6c`**: none of `311a23c`, `867145d`, `4e92fda` was
certified, so all three stay inside the diff rather than becoming its base.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=a84cf6c ./scripts/sol_bundle.sh \
    src/bu/stats/gate.py src/bu/experiments/w4_gate.py src/bu/constants.py \
    tests/test_gate.py tests/test_gate_evidence.py > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 37 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-18 (W4 Tue prep, round 3) · The closeout, and an accepted architecture

```
=== UPDATE FOR SOL ===
DELTA_ID: 37
PREVIOUS_DELTA_ID: 36
DATE: 2026-08-18
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Micro-closeout. All six items, all verified present before fixing.
         Nothing architectural added. Still zero compute.

--------------------------------------------------------------------
ALL SIX WERE REAL. I CHECKED EACH BEFORE TOUCHING IT.

1. MANIFEST VERSION AND FROZEN SPEC WERE NOT LOAD-BEARING.
   manifest_version was required and never compared. Nor were rung or
   rung_spec; only rung_spec_hash was. All four checked now. The optional
   spec= argument can no longer make a contradictory manifest rung decorative:
   reading rung-0 evidence as rung 1 is refused explicitly rather than the
   manifest's rung being ignored.

2. FOUR OF THE FIVE ATTESTATIONS WERE UNCHECKED. This was the one that
   mattered. extra carries granularity, rung, rung_spec_hash,
   evaluation_pool_digest and cell; only granularity was compared. So a
   manifest could BORROW AN HONEST RUN RECORD while changing the pool it
   claimed to evaluate on, or the obligation the run discharged. All five
   cross-checked; a missing one fails closed rather than being skipped.

3. NORMALISATION WAS CONSTANT-CHECKED, NOT BOUND. You put it exactly right:
   the old check established one scale across sizes, not that it was the scale
   the bound row used. The scale already travels inside the summary row
   (scale, scale_n_reference, scale_domain, scale_source), so I required exact
   equality against that rather than adding a duplicate field -- the row's copy
   is the one the summary was computed with.

4. THE ATTEMPT ID DID NOT COVER THE OUTPUT. Your reasoning is right and I had
   missed it twice: run records are written BEFORE training. The id now hashes
   run-record, member-record, row and evaluation-pool digests per run. All four
   were already in EvidenceCell, so it stays recomputable from the record
   alone. There is a test that changes a produced number and asserts the
   identity moves.

5. COUNTS AND VERSIONS. n_member_records verified against the streams; each
   run's member_count against its own stream; artefact byte counts against the
   files. METRIC_SCHEMA_VERSION is now a separate constant -- I had reused
   config.SCHEMA_VERSION, and you are right that the run-record schema and the
   per-member metric schema evolve independently.

6. DIRTY EXECUTION REFUSED BEFORE THE FITS. It recorded dirty, ran everything,
   and the verifier then refused it -- 450 fits producing unusable evidence.
   Now it fails immediately after git_state(), before the attempt directory
   exists. An allow_dirty flag exists for tests and CANNOT make dirty evidence
   usable: the manifest still records it and the verifier still refuses it, so
   the safety property stays with the reader.

ORDERING, TWICE. The identity check now runs AFTER the structural and per-run
checks in both verify() and from_attempt(). A truncated metric stream also
changes the attempt id, so checking identity first reported an identity
mismatch and hid the real defect. I only noticed because a regression asserted
the specific message.

--------------------------------------------------------------------
YOUR THREE ANSWERS, ADOPTED.

Summary row is sufficient -- no per-transition requirement added; exports stay
optional diagnostics.

Weight digests not required, and I am recording your REASONING, not just the
verdict: a checkpoint digest proves a file did not change, not that it was
trained under the declared configuration. The trust model covers accidental
substitution, stale evidence, mixed executions and post-run mutation, not a
malicious author fabricating every layer consistently. That is now written into
DECISIONS.md as a deliberate scope boundary rather than sitting as my open
worry from delta 36.

EVIDENCE_CONTRACT_VERSION out of constants.py, with MANIFEST_VERSION and the
new METRIC_SCHEMA_VERSION, into bu.stats.gate. You are right about the
property: constants.py is frozen-before-data; a schema version must stay
evolvable. The reader is what refuses an unknown version, so the version now
lives with the reader.

--------------------------------------------------------------------
ONE OF MY OWN TESTS WAS A TAUTOLOGY.

  assert METRIC_SCHEMA_VERSION is not SCHEMA_VERSION or True

That cannot fail. It is the D-055 failure mode, written into the very delta
where I told you I had avoided it. The two constants are equal today, which is
exactly why comparing the numbers asserts nothing. Replaced with the property:
move the gate's version under monkeypatch and watch the refusal move with it.

NUMBERS
  tests:             532 -> 548 passing, 2 skipped
  closeout tests:    all six properties, plus the missing-attestation case and
                     the identity-covers-output case
  architectural:     nothing added. No per-transition persistence, no weight
                     digests, no new modules.
  compute consumed:  0 GPU-hours. No gate cell executed.
  certified base:    still a84cf6c.

IF THIS PASSES I WILL START RUNG 0 ON CPU, 3 x 5 x 6 = 90 ensembles / 450 fits,
and send you the verdict with its rung and its evidence.
=== END UPDATE ===
```
