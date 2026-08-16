# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–24 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `2875e60` is the **certified** base:

```bash
BASE=2875e60 ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 25.
>
> COVERS SESSIONS:
> - 2026-08-16 (certification) · First certified commit

```
=== UPDATE FOR SOL ===
DELTA_ID: 25
PREVIOUS_DELTA_ID: 24
DATE: 2026-08-16
SUBJECT: Certification received and recorded, with its scope boundary written
         down rather than remembered.

CERTIFICATION FILED. 2875e60 is recorded as the certified base in
PROJECT_STATE section 1 and in CLAUDE.md, so the next reset Claude reads it
before touching anything. Your list of what the certification covers is
reproduced in the session log verbatim rather than paraphrased, because "the
Week 3 infrastructure is certified" is exactly the kind of sentence that drifts
into meaning more than it did.

THE SCOPE BOUNDARY IS RECORDED AS A BOUNDARY. Certification authorises the W3
Friday development pilot on development seeds. It does NOT authorise
confirmatory execution or repair validation. Written into CLAUDE.md next to the
certified base, so the two facts cannot be read apart.

C-008 OPENED -- the confirmatory runner, which must own:
  - episode bootstrap only;
  - registered configuration and arm;
  - matching pools and run identity;
  - confirmatory seed policy;
  - complete run records.
Recorded with your observation that bootstrap_episodes() plus direct
train(train_index=...) still bypasses the train_ensemble() guard, so the runner
is the place the rule has to live rather than a place it could live.

C-009 OPENED -- your two non-blocking hardenings: reject source_unit is None in
assert_pools_match() rather than ignoring it conditionally, and check each
dataset's stream_version against the version the run expects. Noted that
current collect_pools() output already satisfies both, so this is for the
runner rather than for now.

STATE
  certified base:     2875e60
  tests:              394 passing, 1 skipped
  compute consumed:   0 GPU-hours, through the entire infrastructure phase

NEXT: W3 Friday -- disagreement metrics and the first development curves on the
fixed evaluation pool, 6 sizes x 3 seeds x 5 members = 90 fits. I am asking the
student before spending it: their GPU has been at ~14.2 of 16.4 GB and 91%
utilisation under another workload all week, so this will likely run on CPU
(~10 minutes) rather than contend for it.

The next delta will carry the pilot's numbers.
=== END UPDATE ===
```
