# DECISIONS — *Beyond Uncertainty*

The decisions ledger. **Append-only**: never reorder, never edit a past entry —
a correction is a new entry that references the old one (D-014). Split out of
`PROJECT_STATE.md` §3 so that file stays under its paste cap (D-037); §3 keeps a
one-line index of everything here, and the two are checked against each other by
`tests/test_project_state.py`.

Every decision a future reader would otherwise have to reconstruct. Format:

```
### D-nnn · YYYY-MM-DD · <short title>
**Decision:** what was decided.
**Why:** the reasoning, including what was rejected.
**Plan ref:** P§n / S§Wn, or "not covered by the plan".
**Reviewed by Sol:** yes / no / pending.
```

---

### D-nnn · YYYY-MM-DD · <short title>
**Decision:** what was decided.
**Why:** the reasoning, including what was rejected.
**Plan ref:** P§n / S§Wn, or "not covered by the plan".
**Reviewed by Sol:** yes / no / pending.
```

### D-001 · 2026-08-13 · Working protocol between Claude and Sol
**Decision:** Claude holds the repository and does all implementation, run orchestration and logging. Sol acts as adversarial reviewer and methodological guardian, and does not write project code. This file is the sole shared state.
**Why:** the asymmetry is real — Claude has filesystem and execution access, Sol does not. Duplicating implementation across two agents would produce divergent code with no merge path. Adversarial review is also the process that produced the plan documents in the first place, so it is the role with demonstrated value here.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** pending — this is the first thing Sol should push back on if the split looks wrong.

### D-002 · 2026-08-13 · Schedule anchored to Monday 2026-08-17
**Decision:** Week 1 Monday is 2026-08-17. All week numbers in this file resolve to the calendar dates in §2.
**Why:** the schedule is day-numbered and explicitly startable on any Monday; a fixed anchor is needed so gate dates are real dates rather than relative offsets.
**Plan ref:** S "How to use this schedule".
**Reviewed by Sol:** pending.

### D-003 · 2026-08-13 · Sol is continuous, Claude is not — deltas, not re-pastes
**Decision:** Sol runs in one persistent session for the life of the project and is updated with §8 deltas only. Claude is reset repeatedly and reads this entire file at the start of every session. Sol holds the continuity duty: catching a reset Claude that contradicts a settled decision.
**Why:** the two agents have opposite memory profiles, and a protocol that ignores that wastes the student's effort in both directions — re-pasting the full file to Sol buries new information in text it already has, while giving Claude only a delta leaves it without the decisions it is most likely to unknowingly violate.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** pending.

### D-004 · 2026-08-15 · Submission date is not a constraint; the plan is followed as anchored
**Decision:** Q-002 is closed. The Weeks 18–20 collision with Christmas and New Year, and the 2027-01-01 submission Friday, are accepted. No shift, no re-anchoring. The plan and schedule are followed as built.
**Why:** the student's explicit instruction. There is no external deadline pressure on the submission date, so the cost of the collision is convenience rather than risk, and re-anchoring would buy nothing that the catch-up days do not already provide.
**Plan ref:** S "How to use this schedule".
**Reviewed by Sol:** not required — this is the student's call, recorded rather than reviewed.

### D-005 · 2026-08-15 · The preregistration lives in one file, in code
**Decision:** every preregistered value from §2 lives in `src/bu/constants.py` and nowhere else. Modules import from it; no module restates a value. Changing anything there requires a §3 Change Record naming the constant, the new value, the reason, and whether data has been seen.
**Why:** this is the failure the plan itself already suffered once. In v1.1 a withdrawn two-sigma acceptance rule survived in Sections 8.3 and 13.6 after being replaced in 7.3, and would have produced a different ground-truth label depending on which section the implementation happened to follow. Constants scattered across modules fail the same way and are harder to spot than prose. Concentrating them makes any drift a one-file git diff that Sol can review.
**Plan ref:** P§7.3, P§10.6.
**Reviewed by Sol:** pending.

### D-006 · 2026-08-15 · Three identities, with the statistical unit in the data model
**Decision:** a `Config` derives three ids. `unit_id` hashes the configuration-condition (environment axes plus the failure condition) and is **shared by a failure condition and all of its repair arms**. `config_id` adds the arm. `run_id` adds the seed. Repair arms are represented as transformations of a unit rather than as separate configs, and each is checked to change exactly one mechanism.
**Why:** the configuration-condition is the statistical unit for every confidence interval and the level at which class balancing happens (P§10.7, P§10.4). Making it a hash over the config means the unit travels with the data instead of being reconstructed in Week 15 from directory names or filename conventions. The shared `unit_id` across arms is what makes a ground-truth label assignable at all — a label is a statement about a condition, derived from how its repairs behaved (P§7.2). Enforcing "each repair changes exactly one mechanism" in code rather than by discipline implements P§8.3's critical separation directly.
**Known limitation:** ids are hashes over the config schema, so adding a configuration axis changes every id. `SCHEMA_VERSION` is recorded in every run record and the schema freezes at the end of Week 2, when the axes are final. No real run exists before Week 6, so no label is at risk.
**Plan ref:** P§7.2, P§8.3, P§10.4, P§10.7.
**Reviewed by Sol:** pending — this is the design decision with the longest reach, and the one most worth attacking now.

### D-007 · 2026-08-15 · The Experiment 2A confound conditions are units *within* the sweep, not additional to it
**Decision:** the four non-zero confound levels of Experiment 2A (0.25 / 0.5 / 0.75 / 0.9) identify configuration-conditions that also exist in the configuration sweep. They are **the same units**, run at a higher seed count, not additional independent units. Q-003 closed.
**Why:** Sol's ruling (`SOL ANSWER · Q-003`, high confidence): a configuration-condition must have one stable identity; counting the same unit twice would inflate the effective sample size and invalidate the power and confidence-interval calculations. Extra seeds on the canonical 2A subset strengthen the repeated measurements behind those units without creating new labels.
**Independently checked against the plan's own arithmetic:** P§14.2 budgets 30 + 20 + 25 = 75 canonical configuration-conditions plus ~225 further ones, totalling ~300 — which is P§10.7's target. The 2A units are therefore already inside the 300, not on top of it. Sol's ruling and the plan's run-count table agree.
**Implementation consequence:** the Week 2 enumerator must **deduplicate by `unit_id`**, and seed count becomes a property of a unit's role (5 for units entering an H1/H2 claim, 3 for sweep-only units, 20 for canonical repair validation) rather than a property of a separate run list. D-006's content-hashed `unit_id` makes this deduplication automatic rather than a naming convention that has to be policed.
**Would change it:** evidence that the 2A conditions differ on another preregistered configuration axis and are therefore genuinely distinct units.
**Plan ref:** P§8.2.1, P§13.1.2, P§14.2, P§10.7.
**Reviewed by Sol:** **yes — this decision is Sol's.**

### D-008 · 2026-08-15 · §8 accumulates until delivered
**Decision:** §8 carries a **Delivered to Sol** flag. It is overwritten only when the previous delta has been marked delivered; otherwise the new session's content is appended to the undelivered block.
**Why:** found in practice on the first cycle. Sol answered Q-001 to Q-003 from delta #1 while delta #2 sat undelivered in §8; a plain overwrite would have destroyed delta #2 and Sol would never have learned about D-004 to D-006 or the Week 1 build. The whole point of §8 is that it is the only channel to Sol, which makes silent loss in it the worst failure the protocol can have.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** pending.

### D-009 · 2026-08-15 · Statistical identity is a registered, versioned field list
**Decision:** Sol's Q-005 ruling adopted in full, including the stronger form it named as "what would change my mind". `unit_id` now hashes only the fields listed in `UNIT_IDENTITY_FIELDS`, in a fixed order, together with a new `IDENTITY_VERSION`. Every field of `UnitSpec` and `Arm` must appear in exactly one of an identity list or an explicit exclusion list, checked **at import time**, so a field added without being classified raises immediately. `IDENTITY_VERSION` is separate from `SCHEMA_VERSION` and both are written to every run record, along with the registered field list itself.
**Why:** statistical identity and configuration schema are different concepts, and the previous implementation conflated them — it hashed all of `UnitSpec`, so any future field became identity-bearing by default. Defaulting to "identity-bearing" is the dangerous direction: it silently changes what counts as an independent configuration-condition, which invalidates the power calculation and every confidence interval taken over units.
**Beyond the ruling:** the classification is tested, not merely documented. A parametrised test asserts that varying **each** registered identity field genuinely changes `unit_id`, with the symmetric test for excluded fields, and another test verifies the exhaustiveness check actually fires. That was Sol's stated condition for a stronger position than versioning alone.
**Current state:** all nine `UnitSpec` fields are identity-bearing; the exclusion list is empty. That is the honest answer today — every field is a real axis of the design — and the machinery exists so the first non-identity field is a reviewed decision rather than an accident.
**Plan ref:** P§10.7, P§10.4.
**Reviewed by Sol:** **yes — this decision is Sol's.** Implementation not yet reviewed.

### D-012 · 2026-08-15 · Stage is part of run identity, never of unit identity
**Decision:** `Config` gains a `stage` field (`exp1`, `exp2a`, `exp2b`, `config_sweep`, `repair_validation`, `exp3_repairs`, `ablation`, `pilot`) and `run_id` becomes `config_id + stage + seed`. `unit_id` and `config_id` are unchanged. `STAGE_SEEDS` binds each stage to its preregistered seed count, so P§14.2's policy is enforced in code rather than remembered. Config-level fields are now covered by the same import-time classification check as `UnitSpec` and `Arm`.
**Why:** Sol's material finding, and it was a live bug rather than a tidiness point. A canonical condition can enter an H1/H2 claim at five seeds *and* canonical repair validation at twenty. Those overlap on seeds 0–4, so `unit + arm + seed` was not unique: the two obligations produced the same `run_id`, which would have either raised on write or silently merged them. Worse, the five seeds supporting an H1/H2 claim could no longer be distinguished from the first five of the twenty behind a repair label — and those support different claims. A unit remains **one** statistical unit with **several** execution obligations; deduplicate units by `unit_id`, never deduplicate stage obligations.
**Correction to D-007:** its implementation note said seed count is "a property of a unit's role". That was wrong in a way that mattered — a unit can hold more than one role at once. Seed count is a property of the *(unit, stage)* pair.
**Plan ref:** P§14.2, P§7.3, P§11.2.
**Reviewed by Sol:** finding is Sol's; the fix is not yet reviewed.

### D-013 · 2026-08-15 · The critic feature whitelist is frozen now, not in Week 6
**Decision:** `src/bu/critic/schema.py` registers `CRITIC_FEATURE_SCHEMA` with `CRITIC_SCHEMA_VERSION`, transcribed verbatim from P§13.5.1, together with the four ablation variants, an explicit `FORBIDDEN_FIELDS` set, forbidden prefixes, and `assert_no_forbidden_columns()` for use at the pipeline boundary. Coherence is checked at import. Sol's required tests are implemented, including that `load_runs()` output is rejected wholesale and that renaming a forbidden field does not launder it.
**Why:** Sol's Q-006 position was to freeze before the Week 6 firewall is accepted, with the stated exception that if the schema already exists and is stable, freeze it now. P§13.5.1 specifies all four groups and their per-variant retention completely, so that condition is met. Freezing now means the critic's input space is fixed before any labelled data or H1/H2 result could influence which features look useful — the same argument that fixes the falsification criteria in advance, applied to feature selection.
**Not yet built (Week 6/11):** the X / y / groups separation as three physically distinct structures. The schema is the contract; the extractor enforces it later. Recorded here so it is not mistaken for done.
**Plan ref:** P§7.5, P§12.1, P§13.5.1, P§16.
**Reviewed by Sol:** design is Sol's; the implementation is not yet reviewed.

### D-014 · 2026-08-15 · Ledger order: a past correction, and the rule going forward
**Decision:** decision records are appended in the order they are made and are never moved again. Going forward this is absolute.
**Why:** Sol flagged D-011 appearing above D-010. The cause is worth recording rather than quietly fixing: earlier in the same session Claude *deliberately* reordered the ledger to put D-008 back in numeric sequence after inserting D-009 and D-010 above it. That was a tidiness impulse applied to an append-only record, which is exactly the wrong instinct — an append-only log is evidence, and its value comes from nobody rearranging it. Per Sol's instruction the existing out-of-sequence entries are left where they are; this entry is the correction.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** finding is Sol's.

### D-015 · 2026-08-15 · Week 1 audit — seven defects found and fixed
**Decision:** a line-by-line audit of all Week 1 code before Week 2 begins. Seven defects found, all fixed, each with a named regression test in `tests/test_audit_regressions.py`.

| # | Defect | Severity | Why it mattered |
|---|---|---|---|
| A1 | `to_dict()` omitted `stage` | **Serious** | Defeated D-012 for anything persisted. A round-trip silently reset the stage to `pilot`; the run record never stated it; `load_runs()` had no `stage` column. The fix for Sol's material finding worked only for the directory name |
| A2 | `_hash` used `default=repr` | **Serious** | For any non-JSON value, `repr` embeds a **memory address**, so `unit_id` would differ per process. It hides well — a freed address is usually reused, so two hashes taken in sequence often agree and the bug looks absent |
| A3 | No value canonicalisation | **Serious** | `0` and `0.0` hashed differently, as did `("shape","colour")` and `("colour","shape")`, and a repeated feature made a third. One condition could occupy several units, **inflating the very unit count the power calculation rests on** |
| A4 | `layout` unvalidated, sizes unchecked | Material | `layout="unifrom"` was accepted and became a real configuration-condition. A typo silently enlarging the design |
| A5 | Arrays stringified in the log | Material | `np.array([.1,.2,.3])` logged as the string `"[0.1 0.2 0.3]"`. Writes fine, reloads as text, fails only when a figure does arithmetic. Per-dimension error (P§10.3) is exactly this shape |
| A6 | `glob("*/run.json")` one level deep | Minor | A batch runner grouping runs into subdirectories would make them invisible to analysis — silently, as fewer rows |
| A7 | Cross-process test was a tautology | Minor | It compared a value with itself. Replaced with a real subprocess check plus **golden `unit_id` values**, so identity cannot drift without a test failing |

**Also hardened:** impossible repairs (feature repair with nothing withheld, capacity repair already at maximum) now fail when the config is built rather than hours later mid-batch on Kaggle; `require_clean_git` tolerates an older record; `matplotlib` and `PyYAML` joined the tracked package versions.
**Result:** 68 → 90 tests. Fresh-clone install re-verified, and the golden `unit_id` reproduces in a clean checkout.
**Plan ref:** P§10.7 (A1, A3), P§13.7 (A2, A5), P§10.3 (A5).
**Reviewed by Sol:** pending — A1, A2 and A3 are each worth its scepticism.

### D-016 · 2026-08-15 · Change Record — IDENTITY_VERSION 1 → 2, SCHEMA_VERSION 1 → 2
**Constants changed:** `IDENTITY_VERSION` 1 → 2, `SCHEMA_VERSION` 1 → 2. Required by D-005 and D-009, which say a version bump is a reviewed decision rather than an edit.
**Has any data been seen?** **No.** No experiment has run, no compute has been consumed, no label exists. Only test fixtures in temporary directories were ever written. This is the one window in which such a change is free.
**Why `IDENTITY_VERSION`:** the identity *field set* is unchanged, but A3 changed how values are canonicalised before hashing, so ids computed before and after are not comparable. That is precisely what the version exists to signal. Leaving it at 1 while ids changed would be worse than the original bug.
**Why `SCHEMA_VERSION`:** `stage` was added to `Config` in D-012 without bumping — an oversight, now corrected together with A1.
**Effect:** every `unit_id` changed. Nothing depends on the old values; golden ids are pinned under version 2 so the next change cannot pass unnoticed.
**Reviewed by Sol:** pending.

### D-017 · 2026-08-15 · Gridworld is built against `UnitSpec` directly
**Decision:** `GridWorld` takes a `UnitSpec` as its constructor argument rather than loose keyword parameters, so the environment's configuration axes and the statistical unit's identity are literally the same object. The confound-rate parameter (W2 Mon) and the three layouts (W2 Tue) were built now, with the Week 1 environment, rather than bolted on across Week 2.
**Why:** two reasons. A condition cannot then be described one way in the config and generated another — the class of bug where a run record says `confound_rate=0.75` and the generator quietly used something else. And `UnitSpec` already carried `causal_attribute`, `confound_rate` and `layout` from D-006, so building the environment without them would have meant retrofitting the generator two days later, which is how the two drift apart.
**Design choices worth recording, because they are interpretations rather than quotations:**
- **`interact` toggles an `activated` bit on an adjacent object.** The action needs *some* observable effect or a world model learns it is the identity and the action carries no information. It is deliberately orthogonal to passability, because giving it any influence on the transition rule would confound the manipulation under study.
- **Confound construction.** The decoy attribute equals the causal class with probability *c*, otherwise it is independent. Then P(agree) = c + (1−c)/2 and the phi coefficient is exactly *c*, so the configured number **is** the correlation rather than merely monotone in it.
- **Position as a causal attribute** means (x+y) parity, and placement is constrained to match. The decoy for position is colour.
**Plan ref:** P§2.2, P§13.1.2, P§13.1.3, P§19.
**Reviewed by Sol:** pending.

### D-018 · 2026-08-15 · The configuration sweep is a balanced sample, not the full crossing
**Decision:** the enumerator exposes the **full matrix** (531 units) as a pool, and `design_units()` selects the 300 the design runs: the 75 canonical conditions plus 225 sweep units chosen by deterministic round-robin over (family × causal attribute × layout × confound) strata, rotated within strata so manipulation levels spread too, and balanced so the two intended classes come out 150/150.
**Why:** the full crossing costs ~25,000 model fits against P§14.2's ~8,700 — roughly 3× the budget. P§14.2's "~225 further configuration-conditions" already implies a sample rather than an exhaustive product; this makes that explicit and reproducible. Selection is deterministic with no RNG, so the chosen set is a function of the design: reproducible from the code alone, and diffable when Week 5's MDE simulation changes the count.
**Two things the first implementation got wrong, both caught by inspecting the printed report rather than by a test:**
- Stratifying without the confound axis gave 99 units at confound 0.0 and **9** at 0.9. The enumeration loops confound outermost, so truncation simply took the low levels — leaving the strongest shortcut condition, where the decoy is most tempting and most wrong, almost absent from the sweep.
- Costing every repair arm as a full ensemble inflated the compute estimate five-fold. A baseline trains an ensemble because H1 and H2 need member disagreement; a **repair trains a single model**, because the P§7.3 acceptance test compares per-transition error and needs no spread. With the accounting corrected the design lands at **8,181 fits against ~8,700** — which also independently reproduces P§14.2's own arithmetic, and is the check that this enumeration is the design the plan budgeted for rather than a different one of similar size.
**Interpretation recorded:** P§14.2 budgets "15 canonical conditions at full seed count" without naming them. Implemented as one representative per (canonical configuration × family) = 15, which spreads the twenty-seed budget across all three failure families rather than concentrating it in one.
**Provisional:** 300 is P§10.7's floor, not a final answer. Week 5 Thursday's MDE simulation sets the real count, inflated by the observed exclusion rate.
**Plan ref:** P§10.7, P§14.2, P§14.3, P§8.2.1.
**Reviewed by Sol:** pending.

### D-019 · 2026-08-15 · Thesis prose is drafted by Claude and rewritten by the student
**Decision:** Claude drafts each week's prose cell into `docs/method_draft.md`; the student rewrites it into their own voice. Drafts are explicitly marked as scaffolding.
**Why:** the student's instruction. Reacting to prose is faster than producing it cold, which matters at ~14 h/week. The rewrite is not optional: the student defends these sentences, and Sol's verification-lag warning applies to prose as much as to code — text absorbed by editing is understood, text accepted unread is not.
**Plan ref:** S§W1 Thu, S§W2 Thu, and the schedule's warning that leaving writing to Month 5 does not fit the available hours.
**Reviewed by Sol:** pending.

### D-020 · 2026-08-15 · The PPO substitution is evidenced, not asserted
**Decision:** DEV-001's substitution of a scripted exploratory policy for PPO is now written into the methodology with measured evidence (`docs/method_draft.md`, W2 Sat section). The policy is a coverage-biased random walk that seeks adjacent objects, attempts to enter them, and periodically interacts. Every dataset carries a per-condition `CoverageReport`.
**Why the policy is shaped this way:** the transition rule is about **passability**, so it can only be learned from transitions where the agent tried to enter an occupied cell — and a uniform random walk in an 8×8 grid barely produces them. Measured: the scripted policy yields **3–6× more** rule-carrying transitions at every dataset size, 39.8% of steps versus 7.6% at n=5000.
**The confound the substitution removes, which is a point in its favour rather than an excuse:** a learned policy under any reward penalising wasted steps would converge toward *avoiding* obstacles, so the informative transitions would grow rarer as training progressed and the dataset would be systematically impoverished in exactly the events the world model needs. A fixed, declared procedure is easier to defend than a learned one whose data distribution drifts.
**Checked against the plan rather than assumed:** at n=100 the coverage report says the dataset is *not* adequate. That could have meant Experiment 1's "estimation failure" family was measuring exploration quality rather than sample size — which would make H1 test the wrong proposition. P§3.2.1 settles it: estimation failure explicitly includes data that "does not cover the relevant region of the state-action space", **provided more data from the same generating process repairs it**. Bump counts rise monotonically with dataset size and saturate well before the largest condition, so the criterion is met and thin coverage at n=100 is the manipulation working, on the plan's own definition.
**Also recorded:** episode and step indices are captured at collection, because P§7.3's acceptance test needs random intercepts for episode within seed and that structure cannot be reconstructed afterwards. The episode index is an input to the ground-truth label, not bookkeeping.
**Plan ref:** P§13.2, P§3.2.1, P§7.3.
**Reviewed by Sol:** pending.

### D-021 · 2026-08-15 · Week 2 audit — six defects found and fixed
**Decision:** line-by-line audit of everything built since the Week 1 audit, which predates the environment: `gridworld.py`, `encoder.py`, `policy.py`, `collect.py`, `enumerate_units.py`. Six defects, all fixed, each with a named regression test in `tests/test_audit_w2_regressions.py`.

| # | Defect | Severity | Why it mattered |
|---|---|---|---|
| B1 | **Object order leaked into the observation** | **Serious** | The encoder writes one block per object *slot*, and placement order decided which object got which slot. The same physical arrangement therefore encoded differently across episodes, so a model had to learn the passability rule separately per slot **and** learn permutation invariance on top — both costing data for reasons unrelated to the manipulation. Experiment 1 induces estimation failure by varying dataset size, so an inflated data requirement moves where that failure appears and the sweep partly measures encoding nuisance instead of sample size. Fixed by canonicalising object order in `GridState` |
| B2 | Bump balancer read a counter nobody wrote | Material | `visits` is keyed by the *aggregate* context, which is `"both"` when two adjacent objects disagree; the balancer looked up per-class keys that were never incremented in that case — blind exactly where the choice between a passable and a blocking object matters. Fixed with a dedicated `bump_visits`. Class balance at n=5000 improved from 0.62 to 0.78 |
| B3 | `blocked_fraction` conflated walls with objects | Material | Only an object block is the passability rule firing; a wall block is not the manipulation. Reported as one number, the rule's prevalence was unreadable. Now separate, and the four transition outcomes sum to exactly 1 |
| B4 | Literal `4` for the interact action | Minor | A magic number that silently breaks if action ids change |
| B5 | `design_units()` could drop a repair-validation obligation | Minor | A missing unit would lose a 20-seed obligation with no trace, and every label resting on it would fall back to three seeds. Now raises |
| B6 | Serialisation used `__dict__`; dead import | Minor | Works today, breaks the moment `UnitSpec` gains `__slots__` |

**Checked and found correct:** the three layouts really are three distributions (mean pairwise distance 2.28 / 4.05 / 6.01); parity-constrained placement raises clearly on grids too small; dataset round-trip preserves the unit exactly including tuple fields; agent-on-passable-object is consistent.
**Result:** 180 → 194 tests. Fresh-clone install re-verified; golden `unit_id` and the 300-unit / 8,181-fit design both reproduce in a clean checkout.
**Note on B1:** no `IDENTITY_VERSION` bump is needed — object ordering affects observations, not unit identity. No data exists to invalidate either way.
**Plan ref:** P§3.2.1, P§8.2.1, P§13.1.2, P§14.2.
**Reviewed by Sol:** pending.

### D-022 · 2026-08-15 · The collaboration protocol is machine-checked
**Decision:** `tests/test_project_state.py` enforces the protocol as part of the suite. It fails if the newest session-log entry is not named in an undelivered delta; if delta ids skip, repeat or go backwards; if `PROJECT_STATE.md` exceeds its 500-line paste cap; if decision ids have gaps or duplicates; if a deviation id repeats; if §2's frozen-constant table disagrees with `src/bu/constants.py`; or if an open question has no status.
**Why — this is a correction, not an improvement.** I broke the protocol twice. Writing delta 9 I *replaced* the block containing undelivered delta 8 rather than appending, which is precisely the failure D-008 was written to prevent, and D-008 was itself written after catching that same mistake once already. Then for the two sessions after it I updated §1 and §7 and wrote no delta at all. Three sessions — the environment, the policy and collector, and the whole Week 2 audit — never reached Sol. Neither party could detect it, because a missing delta is indistinguishable from a quiet week.
**The lesson generalises:** a rule that lives only in prose depends on being remembered at the end of a long session, which is exactly when it will not be. Both real failures were caught by these tests on their first run.
**Against Sol's tripwire:** Sol endorsed the role split conditionally, on implementation not outrunning review. This is a hit against that condition — implementation outran the record-keeping — and it is flagged to Sol as such rather than quietly repaired.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** pending.

### D-023 · 2026-08-15 · Sol's delta gets its own file
**Decision:** the delta moved from §8 into `DELTA_TO_SOL.md`. §8 is now a pointer.
**Why:** consolidating four sessions pushed `PROJECT_STATE.md` past its paste cap, and the cap is load-bearing rather than cosmetic — past it the file stops being read. The two files also have genuinely different audiences: this one is Claude's reconstruction of state, that one is Sol's feed. It removes an instruction that was easy to get wrong as well: "paste §8" required finding a section boundary in a 500-line file, "paste `DELTA_TO_SOL.md`" does not.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** pending.

### D-024 · 2026-08-15 · `CLAUDE.md` is Claude's session handoff
**Decision:** operational knowledge — the first-five-minutes checklist, environment commands, hard rules, the traps already hit — lives in `CLAUDE.md`, which the harness loads automatically at session start. `PROJECT_STATE.md` keeps project state; `CLAUDE.md` keeps working knowledge.
**Why:** the memory asymmetry cuts both ways. Sol needs deltas because it already has the history; Claude needs the opposite — the operational context that never belonged in a shared record. Things like "a rebase stalled because git had no identity", "green tests proved nothing about the two worst defects", and "never accept a token" are not project state, but a reset Claude that does not know them will lose time rediscovering them or, worse, repeat them.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** pending.

### D-011 · 2026-08-15 · Deltas carry numbers, not summaries, once results exist
**Decision:** from the first real result, every §8 delta reporting one includes a `NUMBERS` block: total units and per-class counts including `min(N₀, N₁)`, seed count and applicable policy, point estimate, 95% interval **and explicitly what it was taken over**, ambiguous and undiagnosed counts as fractions, and which test ran including any fallback triggered. Sol is instructed to treat a missing line as a finding rather than an oversight.
**Why:** Phase A is infrastructure, which prose conveys adequately. From Week 6 Sol's duties are entirely about numbers — whether an interval was taken over units or transitions, whether power was computed on `min(N₀, N₁)` or the total, whether the excluded fractions were reported at all. A prose summary such as "H2 reproduced across seeds" is unauditable, and an unauditable report reduces the reviewer to agreeing. Deciding the format now, while no result exists, means it cannot later be shaped around a result that would look better without a particular line.
**Plan ref:** P§10.4, P§10.6, P§10.7, P§7.3, P§7.4.
**Reviewed by Sol:** pending.

### D-010 · 2026-08-15 · The leakage firewall whitelists critic features; it never blacklists metadata
**Decision:** the Week 6 Wednesday firewall will be built as a **whitelist** of permitted critic features. Blacklisting construction metadata is rejected as an approach.
**Why:** found while implementing `load_runs()`, which attaches `family` and every `unit_*` axis to each row. Those are exactly the things P§7.5 forbids the critic from seeing — the construction label, the dataset size, the capacity setting. The frame is correct for the experimenter and wrong for the critic. A blacklist fails open every time a column is added, and P§16 rates this leakage as *"silent invalidation of all critic results"* whose early warning sign is implausibly high accuracy in Month 3 — that is, detected late, after work has been built on it. A whitelist fails closed. Warning recorded in the `load_runs` docstring so it is read at the point of use.
**Plan ref:** P§7.5, P§12.1, P§16.
**Reviewed by Sol:** pending — flagged proactively, before the firewall is built.

### D-025 · 2026-08-16 · Repair validation is the manipulation ladder, and repairs share their baseline's seeds
**Decision:** two changes, from one Sol finding and one Sol answer. (a) `repair_validation_units()` is the **complete manipulation ladder at one preregistered reference configuration** — 6 dataset sizes + 4 confound levels + 5 capacity levels = 15, at `REFERENCE_CONFIG = ("shape", "uniform")`, P§2.2's worked example. (b) Repair arms of a repair-validation unit run at **20 seeds**, not 3. `repair_stage_of()` and `repair_obligations()` make the seed count a property of the (unit, arm) pair, and `total_model_fits()` sums those obligations instead of assuming a policy.
**Why (a):** the previous reading took one representative per (canonical configuration × family) and landed on `n=100`, confound `0.9`, `hidden_size=16` — the extreme of every manipulation, where a repair either obviously works or obviously does not. Twenty seeds bought precision exactly where the answer was least in doubt, while the borderline rungs, where P§7.4's ambiguous and undiagnosed outcomes actually arise, stayed on three. The three-seed sweep already supplies configuration diversity; the twenty-seed budget exists to buy precise repair effects. 6+4+5 is also the only natural source of P§14.2's number 15.
**Why (b):** P§7.2 repeats the unrepaired condition *and its repairs* across the full seed count, and P§7.3's acceptance test is **paired** per transition within seed. A 20-seed baseline against a 3-seed repair does not have the pairing the test rests on for 17 of the 20 — and that test creates every label in the thesis. The accountant hid it: charging all repairs at 3 seeds understated the design.
**Effect:** 8,181 → **8,572** fits against P§14.2's ~8,700 (128 headroom). Unit count, class balance and canonical counts unchanged. Sol's projected 8,606 differs only because the ladder carries 23 repair arms where the old fifteen carried 25.
**Tested:** four tests, including the invariant rather than the numbers — for every repair-validation unit, baseline seeds == repair seeds.
**Plan ref:** P§7.2, P§7.3, P§14.2.
**Reviewed by Sol:** finding and answer are Sol's; the implementation is not yet reviewed.

### D-026 · 2026-08-16 · Position-causal conditions leave the canonical set
**Decision:** `CANONICAL_PAIRS` replaces `("position", "uniform")` with `("colour", "clustered")`. Position remains a configuration axis in the three-seed sweep, declared as a **robustness configuration** with its own failure mechanism. Five configurations are retained, so P§14.2's 30 + 20 + 25 = 75 arithmetic is untouched.
**Why:** Experiment 2A withholds whichever attribute is causal, and withholding *position* is not the same manipulation. Measured on the exhaustive two-object state space, running every state through `transition()`: shape and colour masking each leave **10.0%** of (observation, action) keys ambiguous; position masking collapses the key space **26-fold** and leaves **37.5%** ambiguous. The cause is that withholding position deletes the object-position block outright — the model cannot see *where* objects are, so it cannot represent that a move was into an object at all. That is unobservable state, not an unrepresentable rule. Mixing the two inside one canonical claim would mean every 2A result has to be read per-attribute.
**Rejected:** keeping it with a documented caveat (Sol permitted this) — the caveat does not make H2's canonical conditions one mechanism. Dropping position entirely — a larger deviation than the finding requires, and it loses an axis P§13.1.2 lists.
**Decided by:** the student, on the measurement above.
**Plan ref:** P§8.2.1, P§13.1.2, P§14.2. Recorded as **DEV-006**.
**Reviewed by Sol:** finding is Sol's; this resolution is not yet reviewed.

### D-027 · 2026-08-16 · The encoder assigns slots by the descriptor it writes
**Decision:** `ObservationEncoder.encode` sorts objects by the block values it is about to write, rather than relying on `GridState`'s raster order.
**Why:** raster order is a function of position, so with `position` withheld the slot assignment still carried positional information into an observation claiming to carry none — two arrangements differing only in where objects sat could encode differently through slot order alone. Withholding must remove an attribute from the input space *entirely* (P§8.2.1); a partial leak weakens the manipulation. Sorting on the written descriptor makes the observation a function of the multiset of visible descriptors and nothing else, and ties are objects whose blocks are byte-identical, so order among them is unobservable **by construction** rather than by convention.
**Relation to B1:** this strengthens B1's fix rather than replacing it. B1 required slot assignment to be a deterministic function of the state; it still is. Raster order satisfied that but only hid order-nuisance when position was visible.
**No `IDENTITY_VERSION` bump:** slot assignment affects observations, not unit identity. No data exists either way.
**Plan ref:** P§8.2.1.
**Reviewed by Sol:** finding is Sol's; the fix is not yet reviewed.

### D-028 · 2026-08-16 · The protocol tests are hardened where they were decorative
**Decision:** three fixes to `tests/test_project_state.py`. `read_text(encoding="utf-8")` on both files; session coverage checks **every** session since the undelivered block was opened, not only the newest; a delta id gap must be declared via `CONSOLIDATES_DELTA_IDS` or `LOST_DELTA_IDS`.
**Why:** each corresponds to a claim D-022 made that was not true. On Windows the default encoding is CP-1252, so all ten protocol tests **errored** while the suite still reported the project's own numbers as passing — a protocol check that runs on one machine is not a protocol check. Checking only the newest session would have passed the original failure, where two consecutive sessions wrote no delta and only the second would ever have been examined. And D-022 claimed skipped ids fail the suite; `DELTA_ID: 10` after `PREVIOUS_DELTA_ID: 7` passed, because the test checked ordering and uniqueness only. The new test failed on that gap on its first run.
**The general lesson, again:** a test that has never seen the failure it claims to catch is a claim, not a check. All three of these were written *after* a real failure and still did not cover it.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** findings are Sol's.

### D-029 · 2026-08-16 · Q-007 closed — "no explicit statistics", and a tightened negative control
**Decision:** Sol's ruling adopted. The critic ablation variant keeps the frozen P§13.5.1 schema but is **named and described as "no explicit statistics"**, not "no error information": it drops engineered error magnitude, persistence and trend, and the ensemble uncertainty statistics, while retaining latent state, actions, state/action history and the raw predicted-vs-actual state. Separately, the W13 construction-leakage negative control receives latent and context features but **not** `predicted_vs_actual_state`, engineered errors or uncertainty signals.
**Why:** P§12.1 and P§13.5.1 are internally inconsistent, so the disagreement was never merely plan-versus-schedule. The retained raw residual trace lets a model learn an error representation, so a strong result there cannot be reported as succeeding "without error" — only without *explicitly supplied* error and uncertainty statistics. The control tightening is the sharper half: without it the control can reconstruct prediction error while claiming to exclude it, which would make the leakage control fail silently in the direction that looks like success.
**Would change it:** a statement in the authoritative plan that "error history" means the engineered Error group specifically.
**Plan ref:** P§12.1, P§13.5.1, S§W13 Tue.
**Reviewed by Sol:** **yes — this decision is Sol's** (high confidence).

### D-030 · 2026-08-16 · Q-008 closed — named streams, with pairing preserved inside canonical comparisons
**Decision:** Sol's ruling adopted. Four **named streams** — environment generation, policy decisions, bootstrap sampling, weight initialisation. Sweep-only units derive each from `(unit_id, seed, purpose)`. Explicitly paired canonical comparisons derive from a preregistered `comparison_group_id` that excludes only the manipulated axis, so common random numbers survive where they are wanted: Experiment 1's data sizes share a generating stream as nested prefixes, Experiment 2B's capacity levels train on the same datasets, Experiment 2A's confound levels share underlying draws. `arm` is **never** in the failure-set stream — baseline and repairs must be evaluated on the same recorded failure set (P§7.2 step 4).
**Why:** hashing everything by `(unit_id, arm, stage, seed, purpose)` removes unwanted cross-unit correlation but also destroys the pairing the design depends on. Independence is wanted *across* units, because confidence intervals are taken over units and correlated environments would understate between-unit variance; it is not wanted *within* a comparison, where holding the generating process fixed is the point of the manipulation.
**NOT YET IMPLEMENTED.** `GridWorld.reset` still derives its stream from the seed alone and `collect()` from `seed * 100_000 + episode`. This is filed as decided and unbuilt, deliberately visible: W3 Wed's bootstrap ensemble is the first consumer of a stream, so the module is the **first** Week 3 task, before the MLP.
**Would change it:** an analysis plan modelling all cross-unit dependence from shared streams and showing unit-level intervals stay calibrated.
**Plan ref:** P§5.4, P§7.2, P§11.2.
**Reviewed by Sol:** **yes — this decision is Sol's** (high confidence).

### D-031 · 2026-08-16 · Intended-class balance is kept, with a predeclared reserve
**Decision:** Sol's ruling adopted. The design stays balanced **150/150 on intended class**; no class is over-sampled in anticipation of differential exclusion. Instead: a deterministic reserve order is predeclared within each intended class and configuration stratum; Week 5 inflates the raw count using the pilot exclusion rate the schedule requires; Gate 2 assesses `min(N₀, N₁)` on repair-verified labels; and any shortfall is filled from the predeclared reserve **without inspecting critic performance**.
**Why:** expected differential exclusion is currently a guess, and over-sampling from a guess introduces exactly the kind of unreported researcher degree of freedom P§10.6 exists to prevent. Drawing from a reserve fixed in advance is a preregistered contingency; drawing after seeing which class survived is not. Note also that excess units in the larger surviving class cannot repair a shortage in the smaller one — balanced accuracy uses equal numbers of observed labelled units.
**Not yet built:** the reserve order itself. Due W5 Thu with the MDE simulation, which is when the real count is set.
**Plan ref:** P§10.4, P§10.6, P§10.7, P§7.4.
**Reviewed by Sol:** **yes — this decision is Sol's** (high confidence).

### D-032 · 2026-08-16 · The world model predicts the dynamic components, and the primary error is agent position
**Decision:** Sol's ruling adopted. The model predicts **next agent position** and **next object-activation bits**. Static object positions, shapes and colours are deterministic passthrough when a full next state is reconstructed, and **never enter the training loss or the scientific error score**. The **primary** one-step error is on next agent position, computed on **movement-action transitions only**, in grid-normalised coordinates. Activation error is an auxiliary output and a secondary metric, reported separately rather than averaged into the primary score. The same agent-position definition applies to rollout errors at horizons 1, 3 and 5 (P§10.2).
**Why:** measured, not assumed — 26 of 30 output dimensions never change within an episode, an identity predictor scores MSE 0.0047, and 92.6% of its residual error is the two agent-position dimensions. Full-state averaged MSE therefore hides the passability failure behind dimensions any model copies immediately, **and changes scale when withholding changes the observation width** (30 dims visible, 22 with shape withheld) — so the error scale would differ between the estimation and missing-feature families for encoding reasons rather than experimental ones. A full delta target was rejected: static deltas are zeros and reproduce the same dilution in another form, and for agent position next-state and delta prediction carry equivalent residual information, so next-state is simpler and stays aligned with the plan.
**Plan ref:** P§10.2, P§10.3. Narrowing recorded as **DEV-007**. Closes Q-009 together with D-035.
**Reviewed by Sol:** **yes — this decision is Sol's.**

### D-033 · 2026-08-16 · One fit, several roles — stage labels must not create compute
**Decision:** `Config.fit_id` (`config_id + seed`, no stage) identifies the computation; `execution_plan()` emits each distinct fit once, carrying **every** stage role it discharges; `total_model_fits()` counts the plan rather than summing obligations.
**Why:** Sol's material finding, verified exactly. Summing stage obligations charged a repair-validation unit's baseline at 25 seeds — 5 for its canonical stage plus 20 for validation — when the twenty *contain* the five. **375 fits of phantom compute**, and worse than the arithmetic: the schedule would have executed those five twice. They are the same fit because nothing distinguishing the two obligations reaches the computation — D-030 keeps stage out of every stream, so the runs would be bit-identical.
**Correction to D-012:** D-012 put stage in `run_id` so the five seeds behind an H1/H2 claim could be told from the first five of twenty behind a repair label. That identity purpose stands and is unchanged. What was wrong was the execution consequence — that distinguishable *records* require distinct *runs*. A fit carries roles; it is not duplicated per role. D-030, filed one session earlier, is what makes this provable rather than merely plausible.
**Effect:** 8,572 → **8,197** fits against P§14.2's ~8,700. Repairs unchanged at 1,672 (23 validation arms × 20, 404 others × 3).
**Plan ref:** P§14.2, P§7.2.
**Reviewed by Sol:** finding is Sol's; the fix is not yet reviewed.

### D-034 · 2026-08-16 · Change Record — `CONFIRMATORY_SEED_BASE = 1000`, and everything below it is pilot data
**Constant added:** `CONFIRMATORY_SEED_BASE = 1000`. Confirmatory runs use seeds 1000+; **every seed below it is development/pilot data**, permanently excluded from confirmatory runs, failure-threshold calibration, repair acceptance, and critic training or evaluation.
**Has any data been seen?** **No experimental data.** No model has trained, no label exists, zero compute consumed. Development datasets have been collected and inspected — which is exactly what this record is about.
**Why:** Sol's pilot-separation requirement, and it is not hypothetical. Two design decisions were taken *after* looking at collected data: the Week 2 coverage evidence behind the PPO substitution (D-020), and the identity-predictor probe that produced D-032. Data that shaped a design choice cannot also test it.
**Why an offset rather than an inventory:** an inventory of tainted datasets has to be maintained correctly forever and fails silently when someone forgets an entry. An offset puts everything ever inspected during development below the line by construction. It costs nothing now and cannot be done later.
**Plan ref:** P§10.6, P§4.2, S§W4 Fri.
**Reviewed by Sol:** requirement is Sol's; this implementation is not yet reviewed.

### D-035 · 2026-08-16 · One global failure threshold, calibrated on a balanced reference pool
**Decision:** Sol's ruling adopted. **One** threshold across the estimation, missing-feature and capacity families — never one per family or per withheld-feature schema. Calibrated once from a balanced pool of well-fit, fully-observed reference **movement** transitions, balanced over the preregistered environment strata (layout, causal attribute) so no single reference configuration dominates. Frozen at W4 Fri: the exact error formula, the included action types, the reference configurations, the balancing procedure, the percentile, and the resulting numerical value. Thereafter the identical number applies to every condition. Layout-specific results may appear as sensitivity analysis and **may not redefine the primary failure set**.
**Why:** family-specific percentiles would mechanically normalise away genuine differences in failure prevalence, and would make the failure set partly a function of the construction label — which is the leakage P§7.5 forbids, arriving through the threshold rather than through a feature column. Balancing the calibration pool is what makes a single global threshold defensible once D-032 has fixed the error to one scale.
**Plan ref:** P§10.1, P§7.5, S§W4 Fri. Closes Q-009 with D-032.
**Reviewed by Sol:** **yes — this decision is Sol's.**

### D-036 · 2026-08-16 · Sol is given the generated bundle, never a folder copy
**Decision:** what travels to Sol for verification is `scripts/sol_bundle.sh` output, which states the commit hash, the dirty flag and the test result it was generated from. A raw folder copy is not an acceptable substitute.
**Why:** found in practice. Sol's delta-11 review could not certify the 222-test claim because the transferred folder was **stale** — dated 2026-08-15, still carrying the old extreme-condition repair selection, with `test_aliasing.py` and the UTF-8 changes absent and no `.git` directory to check against. Sol correctly declined to certify and said so. The bundle would have caught it in its first three lines; a folder cannot, because nothing in it states which commit it is. An adversarial reviewer verifying a stale copy is worse than one verifying nothing, because the verification looks like it happened.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** finding is Sol's.

### D-037 · 2026-08-16 · The decisions ledger moves to its own file
**Decision:** §3's decision records move to `DECISIONS.md`, append-only, complete. §3 keeps a **one-line index** of every id, date, title and Sol-review status, so nothing becomes invisible. The student carries `PROJECT_STATE.md` **and** `DECISIONS.md` to Claude.
**Why:** the ledger is the fastest-growing section and it had pushed `PROJECT_STATE.md` past its 500-line paste cap, which D-023 established is load-bearing rather than cosmetic — past it the file stops being read. This is **not** archiving: nothing is dropped, condensed or moved out of sight, and Sol's instruction never to archive decisions is respected. It is the same split already made for §8 (D-023), for the same reason and with the same shape. Index growth is one line per decision instead of a dozen, so the cap now holds for the remaining seventeen weeks.
**Enforced:** `tests/test_project_state.py` checks that `DECISIONS.md` ids stay unique and contiguous and that **every** id appears in §3's index — so a decision cannot be filed into one file and lost from the other.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** pending.

---

### D-038 · 2026-08-16 · A multi-role fit must resolve to one set of streams
**Decision:** `assert_roles_share_one_stream()` runs inside `execution_plan()`. If two roles attached to one fit resolve to different `env`, `policy`, `bootstrap` or `init` keys, plan construction **raises**. Tested exhaustively over the plan and against a constructed violation.
**Why:** Sol's finding, and the correction it makes to my own wording. I wrote that stage "never enters any key". That is true of a key's *contents* and false of its *derivation*: `comparison_group_id` hashes `comparison_stage(unit, stage)`, so stage reaches data-stream identity indirectly. D-033 deduplicates on `(unit, arm, seed)`, so if two roles needed different data the deduplication would be wrong rather than economical — it would silently merge two fits requiring different datasets.
**Measured:** the invariant holds today across all 75 multi-role fits — but only because no canonical unit also carries a `config_sweep` obligation. That is a property of this enumeration, not of the design, and `("exp1", "config_sweep")` on one unit genuinely does resolve to two different `env` streams. "Happens to hold" is what makes this a check rather than a comment.
**Plan ref:** not covered by the plan; follows from P§7.2 and P§14.2.
**Reviewed by Sol:** finding is Sol's; the fix is not yet reviewed.

### D-039 · 2026-08-16 · Comparison groups are the clustering every split and interval must respect
**Decision:** `group_of(unit, stage)` is the partitioning key for all downstream statistics, and `comparison_groups()` reports the structure. Three consequences are binding: a comparison group stays **entirely** within one critic partition or CV fold; the Week 5 MDE simulation resolves over **groups**, not over 300 unit ids; H1/H2 comparisons inside a group are paired or blocked, never treated as independent draws. Class balancing stays at unit level but is performed subject to the group constraint, and D-031's reserve draw must preserve groups too.
**Why:** the cost of the common-random-number design Sol prescribed in D-030. Units sharing a group were deliberately given related or nested data — that is what the pairing buys — so they are not independent. Splitting them randomly would put near-identical trajectories on both sides of a critic split and inflate H3.
**Measured, and the part that goes beyond the finding:** the 75 canonical units collapse into **15** groups (Sol's estimate, exact); the 225 sweep units stay singletons; 300 units → **240** independent groups. More consequentially, the design's intended-class balance is **150/150 at unit level but 125/115 at group level**, so `min(N₀, N₁)` — the quantity P§10.7 makes power depend on — falls from 150 to **115**, a 23% reduction. The design advertises a balance it does not have at the level that is actually independent. This is now printed by the enumerator rather than left to be discovered in Week 5.
**Not yet built:** the grouped splitter (Week 6/11) and the grouped MDE simulation (W5 Thu). The key and the report exist so neither can be written in ignorance of the clustering.
**Plan ref:** P§10.4, P§10.7, S§W5 Thu.
**Reviewed by Sol:** **yes — this decision is Sol's**, extended with the group-level balance measurement.

### D-040 · 2026-08-16 · The pilot boundary is enforced, not merely checkable
**Decision:** `assert_confirmatory(seeds, what=...)` fails closed on any development seed, **and on a mixed batch**. Run records carry `seed_partition` and `confirmatory`; `load_runs()` gains `require_confirmatory=`; `seed_partition` is a column in the analysis frame. Development seeds below 1000 stay fully usable for MLP debugging and pipeline tests — that is what the range is for.
**Why:** Sol's finding. D-034 declared the boundary and built a namespace that made exclusion *easy to check*, which is not the same as *impossible to violate* — `stream()` still accepted development seeds normally, and every downstream analysis would have had to remember. A mixed batch fails rather than silently dropping the development rows, because dropping them leaves an analysis quietly computed on fewer units than it reports.
**Still to wire:** threshold calibration, repair acceptance and the critic loaders do not exist yet (W4–W11). Each must pass `require_confirmatory=True`; the guard exists so that is a one-line obligation rather than a design question.
**Plan ref:** P§10.6, P§4.2.
**Reviewed by Sol:** finding is Sol's; this implementation is not yet reviewed.

### D-041 · 2026-08-16 · The bundle selects its own contents
**Decision:** `sol_bundle.sh` prints the review base, the exact arguments it was invoked with, a `git diff --stat` manifest against that base, and the complete diff — none of which the caller chooses. `BASE=<rev>` sets the review base.
**Why:** Sol's finding, and it retires a claim of mine that was too strong. The script's own comment said it "cannot flatter" because it is generated rather than hand-written. Generation is not enough: the delta-12 bundle shipped a clean commit and two files, leaving nine implementation claims uncertified — an honest bundle that still misrepresented the work by omission. What the caller picks is now surrounded by what the caller cannot pick.
**Also corrected:** the claim that commit, dirty flag and test result are the bundle's "first three lines" was simply false — they were near the top. They are now literally the first three lines.
**Plan ref:** not covered by the plan. Extends D-036.
**Reviewed by Sol:** finding is Sol's.

### D-042 · 2026-08-16 · Correction to D-039 — 115 is a worst-case bound, not the effective sample size
**Correction:** D-039 stated that `min(N₀, N₁)` "falls from 150 to 115, a 23% reduction". That is wrong and this entry supersedes it. The registered statistical unit **remains the configuration-condition** (P§10.7, frozen in §2), unit-level intended-class balance **remains 150/150**, and 125/115 are **cluster counts, not class counts**.
**Why the original was wrong:** common random numbers make units within a group *correlated*; they collapse a group to one observation only if the within-group correlation is exactly 1. 115 is therefore the value under perfect dependence — a conservative lower bound — not a measured effective sample size. Independent weight initialisation and bootstrap streams (which key on `unit_id`, not the group) may reduce that correlation substantially, and by how much cannot be known from the group structure alone.
**The error is worth naming precisely**, because it is a failure mode this project is otherwise well defended against: I took a bound, dropped the qualifier, and reported it as a result — then propagated it into `PROJECT_STATE.md`, `CLAUDE.md`, the enumerator's printed report, a test docstring and a delta. Every one of those said 150/150 was a balance "the design does not have", which is false: it has it, at the level where it is registered. A number that travels that fast is exactly the kind that needs its qualifier attached to it, not near it.
**The statement of record:** *"The design contains 300 registered units nested in 240 comparison groups. Unit-level intended-class balance is 150/150; group counts are 125/115. Effective sample size is not fixed by those counts and will be estimated or sensitivity-analysed using within-group correlation in the Week 5 MDE simulation."*
**What D-039 keeps, unchanged and still binding:** comparison groups stay intact across critic partitions and CV folds; H1/H2 ladder comparisons are paired or blocked; uncertainty intervals resample or cluster at the comparison-group level; reserve draws preserve groups.
**The Week 5 MDE procedure (C-006):** simulate unit outcomes **nested within** comparison groups. Before pilot estimates exist, run an ICC sensitivity grid at 0, 0.25, 0.5, 0.75, 1. After the eligible pilot, use its estimated ICC and **retain** the sensitivity results rather than replacing them. A closed form is not sufficient here and the arithmetic shows why: applying the standard unequal-cluster design effect (`1 + (m_A − 1)·ICC`, `m_A = Σm²/Σm`) gives 72.6 effective units per class at ICC = 1, while the exact answer at ICC = 1 is the cluster count, 115. The approximation is conservative at the boundary because the groups are unequal, which is precisely why this is simulated rather than solved.
**Not a change to the statistical unit.** Rewriting the unit from configuration-condition to comparison group would require its own design Change Record and reconciliation with P§10.7. That is not proposed.
**Plan ref:** P§10.4, P§10.7, S§W5 Thu. Supersedes the effective-sample-size claim in D-039.
**Reviewed by Sol:** **yes — the correction is Sol's.**

### D-043 · 2026-08-16 · A bundle base must be Sol-*certified*, not merely reviewed
**Decision:** `BASE` for `sol_bundle.sh` is the last commit Sol **certified**, not the last one it saw. A one-time supplemental bundle closes the range Sol reviewed but declined to certify. The script's guidance and `CLAUDE.md` say "certified" throughout.
**Why:** Sol's finding, and it is a genuine hole rather than a wording preference. Delta 13's bundle used `BASE=b099e60`, which correctly evidenced everything *after* that commit — but Sol had declined to certify several changes *inside* b099e60, because delta 12's bundle shipped only two selected files. Using a challenged commit as a base silently inherits its gap and makes it permanent: the range is never diffed again by anyone.
**Two wording claims retired**, both of which Sol showed were literally false. The caller chooses `BASE` and therefore the diff range, so the manifest is *not* "not chosen by the caller" — the protection is that the chosen base is **printed and reviewable**. And commit, tree status and test result are not "the first three lines"; the heading, commit and tree status are, with the test output further down. The bundle now claims only what it does.
**Plan ref:** not covered by the plan. Extends D-036 and D-041.
**Reviewed by Sol:** finding is Sol's.

### D-044 · 2026-08-16 · Correction to D-042 — the ICC = 1 boundary is a property of the estimator, not of the design
**Correction:** D-042 said "the exact answer at ICC = 1 is the cluster count, 115" and called the unequal-cluster design effect "conservative at the boundary because the groups are unequal". Both are wrong, and this entry supersedes them. The boundary depends on **how the estimator weights**, and nothing else.
**The arithmetic, checked:** for a **unit-weighted** mean under the exchangeable equal-variance model, `n_eff = (Σm)² / Σm²`. D=0: `150² / 300 = 75.0`. D=1: `150² / 310 = 72.58`. The Kish design effect `1 + (m_A − 1)·ICC` with `m_A = Σm²/Σm` evaluates at ICC = 1 to exactly the same numbers — they are **identical, not approximate**. So 75 / 72.6 is not a conservative approximation of anything; it is *the* result for a unit-weighted estimand. The cluster counts 125 / 115 are the boundary for an **equal-cluster-weighted** estimand, which weights a six-unit canonical group the same as one sweep unit — a different estimand.
**What I actually did wrong, stated precisely:** I compared two estimands and attributed the gap to approximation error. Sol's earlier description of 115 as "a conservative lower bound" was too broad for the same reason, and Sol says so; but the overreach that reached the repo was mine, and this is the second correction in two reviews to the same paragraph. The lesson is not about clustering formulas — it is that a number quoted without its estimand is not a number.
**Preregistered, so it cannot be chosen later by which value is convenient:** `BALANCED_ACCURACY_WEIGHTING = "unit"` in `constants.py`. Equal weight per registered configuration-condition, which is what P§10.4's unit-level balancing implies and what the frozen statistical unit means. Dependence is handled by **group-bootstrap** intervals — resampling whole comparison groups — which accounts for the correlation without changing the point estimate's estimand.
**The Week 5 MDE simulation (C-006), fully specified.** It must reproduce *that* estimator rather than a scalar proxy: actual group sizes; actual class membership; group-preserving partitions; unit weights; **paired** predictions from the learned critic and the fitted baseline; within-group correlation; and the balanced-accuracy *difference* with its confidence interval. Validation: at ICC = 0 the simulation must agree with the independent-units analytic result, and at ICC = 1 with the chosen estimator's analytic boundary (75 / 72.6 under unit weighting). Those two agreements are the test that the simulation implements the estimator it claims to.
**No scalar helper.** Power for the paired balanced-accuracy comparison is simulated directly. A function returning an effective sample size is how the first wrong number escaped, and naming it would invite the same misuse.
**Plan ref:** P§10.4, P§10.7, S§W5 Thu. Supersedes D-042's ICC = 1 boundary claim; D-042's retraction of 115-as-measured stands.
**Reviewed by Sol:** **yes — the correction is Sol's.**

### D-045 · 2026-08-16 · Recorded metadata is validated by type, then by value
**Decision:** `load_runs()` requires `seed_partition` to be one of `{"development", "confirmatory"}` and `confirmatory` to be an actual JSON boolean — `type(x) is bool` — before comparing either against the seed.
**Why:** Sol's finding. The check used `bool(recorded_flag)`, and `bool("false")` is `True`. A record carrying the string `"false"` on a development run would therefore have been read as confirmatory and passed the consistency check — the corruption the validation exists to catch, waved through by the validation itself. A truthiness test on a field whose whole purpose is to be compared for equality is a category error, not a style preference.
**Plan ref:** not covered by the plan. Hardens D-040, D-042.
**Reviewed by Sol:** finding is Sol's.

### D-046 · 2026-08-16 · The world model, and what in it is an interpretation
**Decision:** `src/bu/models/world_model.py`. An MLP over `[observation ‖ one-hot action]` with two heads — position (MSE) and activation logits (binary cross-entropy) — built from a `UnitSpec`, initialised from the `init` stream, with the dynamic/static split derived from `encoder.blocks` rather than hardcoded.
**Choices that are mine rather than the plan's, recorded because a future reader would otherwise have to guess:**
- **Two hidden layers, ReLU.** The schedule says "MLP" and fixes only the hidden *size*, which is the swept axis. Depth is held constant so Experiment 2B varies one thing.
- **Action enters as a one-hot concatenation**, not an embedding. Five actions; an embedding would add a learned table with nothing to generalise over.
- **Heads derived from the encoder.** Observation width is 30 with everything visible and 22 with shape withheld, so a hardcoded width would be silently wrong for exactly the Experiment 2A conditions the thesis is about.
- **Logits, not probabilities**, so the loss can use `binary_cross_entropy_with_logits`.
- **`predict_next_obs` copies statics outside the loss.** This is what makes "the model predicts the next state" true in P§10.2's sense while D-032's exclusion still holds.
**Verified rather than assumed:** the primary error does track the manipulated mechanism — after a short fit, blocked movement transitions carry **1.67×** the position error of free moves (0.0798 against 0.0478 over 565 blocked and 1,040 free transitions). If that ratio were ~1, the headline metric would not be measuring passability at all, and no shape test would have told us.
**Plan ref:** S§W3 Mon, P§10.2. Implements D-032 and DEV-007.
**Reviewed by Sol:** pending.

### D-047 · 2026-08-16 · Q-010 closed — the auxiliary head is detached and both losses are action-conditional
**Correction first.** Q-010 claimed the optimiser "spends ~2% of its gradient on the passability rule". That was inferred from loss share and is **wrong by roughly an order of magnitude, in the opposite direction**. Measured: activation was 97.7% of the scalar loss but only **16–36%** of the trunk-gradient norm, so the position task dominated the trunk throughout. Loss values and gradient norms are different quantities and I treated one as evidence for the other. Retracted with it: that activation had been *shown* to inflate the position task's data requirement, and that interference with the shared representation had been demonstrated. Neither had.
**What the measurement does support:** cosine similarity between the two trunk gradients was **−0.06 to −0.16** across training — mildly *opposed*, so real interference exists. Small, but removable at no cost.
**Decision (Sol's ruling, adopted exactly):**
1. The position task **owns the trunk**. The auxiliary head reads `activation_head(h.detach())`, so it can learn while its loss cannot move the representation the position head reads.
2. **Both losses are action-conditional.** Position MSE trains on movement transitions only; activation BCE on `interact` transitions only. A move never toggles a bit and an `interact` never moves the agent, so training either head on the other's transitions teaches a known no-op — the same objection as full-state MSE, applied per action instead of per dimension.
3. `predict_next_obs` gains matching **action-conditional passthroughs**, alongside the static one.
4. **No second trunk.** It would raise per-fit cost across 8,197 fits, and Sol's conditional for it is not met — see the open item below.
**Knobs removed, all three unrecorded and result-affecting:** `activation_weight` (no methodological work left once gradients are separated and the losses are disjoint), `n_layers` (frozen at `N_HIDDEN_LAYERS = 2` and published in `ARCHITECTURE`), and the optional `rng` (now mandatory — an optional generator is one a caller forgets, and the fallback was torch's global RNG, which would make weights depend on process history rather than on `(unit_id, seed, member)`).
**Measured after the change:** position loss improved **0.002242 → 0.000931** at the same budget, which is what owning the trunk buys.
**Open item for W3 Tue, recorded rather than resolved:** the detached head is at 0.2575 against a copy baseline of 0.1652 after 3,000 epochs — **worse than copying**, improving slowly. That is evidence of difficulty, not of incapability, and the real training loop does not exist yet. Sol's conditional for a second trunk turns on this and must not be decided from a hand-rolled loop.
**And it is not an information floor.** The INTERACT aliasing check Sol required: fully-observed, shape-withheld and colour-withheld conditions all show **zero** aliased successors — the interact rule is deterministic *and* the observation determines which bit flips. Only position-withheld aliases it. So residual activation error in a canonical 2A condition is a learning shortfall, and "irreducible" may not be claimed.
**Training-loop consequences, binding on W3 Tue:** early stopping and checkpoint selection use **movement-position validation loss only**; activation loss is logged separately and never determines stopping; any scheduler monitors the primary loss; **no global gradient-norm clip** across both parameter groups, since a large activation-head gradient could rescale the trunk gradient indirectly — per-group clipping or none; fail loudly on a batch with no movement transitions; ensure activation batches contain `interact` transitions.
**Plan ref:** P§10.2, P§10.3. Supersedes Q-010; refines D-032 and D-046.
**Reviewed by Sol:** **yes — the ruling is Sol's**, and the gradient-share correction is Sol's.

### D-048 · 2026-08-16 · Two tests replaced for asserting less than they claimed
**Decision:** Sol's test corrections implemented. `test_a_perfect_position_prediction_scores_zero` could range over an **empty mask** — it zeroed the head and checked only targets that happened to equal zero, and interior grid positions may supply none, so it could pass vacuously. It now substitutes the actual target, asserts the mask is non-empty, and carries a control that the real model is not accidentally perfect. `test_the_loss_never_sees_a_static_dimension` tested a proxy — it counted loss terms. It now perturbs static target dimensions and asserts both loss terms are **byte-identical**, with a control perturbing a dynamic target and asserting only its own term moves.
**Why it is worth a record:** both were written in the same session as the code they cover, both passed, and neither would have caught its own failure. That is the third time in this project a green test has certified nothing — the same lesson as the `_hash` memory-address defect and the object-order leak. A test written alongside its implementation inherits the implementation's assumptions.
**Also added:** gradient-isolation tests asserting the activation loss produces **zero** gradient norm in the trunk and position head and vice versa — a structural property that needs no measurement, unlike the claim it replaces.
**Plan ref:** not covered by the plan.
**Reviewed by Sol:** corrections are Sol's.

### D-049 · 2026-08-16 · The training loop, and the split that makes early stopping honest
**Decision:** `src/bu/models/train.py`. Early stopping on the **movement-position validation loss only**, held-out split taken at the **episode** level by **striding** rather than by contiguous tail, best checkpoint restored before returning, both loss terms logged per epoch, no gradient clipping, and minibatch order drawn from a new named `batch` stream.
**Why an episode split — measured, not argued.** A transition-level split reports a validation loss **4.5–8.7× lower on the same data**: 0.00144 against 0.01250 at n=250, 0.00095 against 0.00765 at n=1000, 0.00075 against 0.00338 at n=5000. Transitions inside an episode are near-duplicates, so a transition split validates on rows it effectively trained on. **The optimism is worst at small n** — 8.70× at 250 against 4.54× at 5000 — which is the direction that corrupts Experiment 1 specifically: the error-versus-data curve would flatten at the small-data end and estimation failure would appear in the wrong place. The leaky split also ran 237 epochs at n=250 against 27, because it kept "improving" on leaked data.
**Why strided rather than the last k%.** `ExploratoryPolicy` carries its coverage counters *across* episodes, so its behaviour drifts through a collection: measured over 100 episodes, the fraction of transitions that moved the agent falls from **0.543** in the first fifth to **0.476** in the last, with the action distribution shifting too. A contiguous tail split would hold out a distribution the model never trained on and call the gap generalisation. Striding also keeps the held-out episodes **identical across dataset sizes** — the datasets are nested prefixes (D-030), so Experiment 1's six conditions now differ in training data alone rather than also in what they are scored against.
**D-047's constraints, all implemented:** stopping and checkpoint selection read `val_position` and nothing else; activation is logged and never watched; no scheduler (and if one is added it must monitor the primary loss); **no global gradient-norm clip**, because one clip spanning both parameter groups would let a large activation-head gradient rescale the trunk gradient and reintroduce through the optimiser the coupling the detach removes; a split with no movement transitions raises rather than producing a loss curve and a "trained" model with no signal — the failure that looks most like success.
**Change Record — `STREAM_VERSION` 1 → 2.** `batch` added to `PURPOSES` (minibatch order changes the fitted model, and torch's global RNG would make a fit depend on process history — the defect D-047 removed from initialisation). The derivation is unchanged and purpose is part of every key, so nothing would have collided; but `STREAM_VERSION`'s own docstring says a change to the purpose list is a bump, and honouring a rule only when convenient is how it stops being one. **Has data been seen?** No confirmatory data exists; zero compute consumed. The bump is free now and would not be later.
**Verified:** a full 5,000-transition fit early-stops at epoch 10 of 31 in 1.5s on CPU, with the curve reaching `load_runs()` as one record per epoch.
**Plan ref:** S§W3 Tue, P§7.3, P§3.2.1. Implements D-047's training-loop constraints.
**Reviewed by Sol:** pending — the episode-split measurement and the `STREAM_VERSION` bump are both worth its attention.

### D-050 · 2026-08-16 · The bootstrap ensemble, and what members are allowed to differ in
**Decision:** `src/bu/models/ensemble.py`. `config.ensemble_size` members, each drawing from three separate named streams at `member=k` — `bootstrap` (which training data), `init` (starting weights), `batch` (minibatch order). Bootstrapping touches the **training split only**; the held-out episodes are identical for every member. Per-member validation error is logged **per member**, never aggregated. Default resampling granularity is **episode-level** — a block bootstrap.
**Why the validation set is shared:** per-member errors computed on different data would not be comparable to one another, and Week 3 Friday compares them. This is asserted rather than assumed.
**Why three streams rather than one:** the ensemble is the measurement instrument — H1 and H2 are both claims about mean pairwise disagreement, so anything changing how members differ changes the dependent variable. Separate streams mean diversity can later be attributed to its source, and that changing the resampling scheme cannot silently shift the weights members start from.
**Why episode-level by default:** the same reason the split is episode-level (D-049). Transitions inside an episode are near-duplicates, so resampling rows individually leaves every member holding essentially every episode — measured, a transition bootstrap retains >90% of training episodes while an episode bootstrap retains ~63%, the classic bootstrap share.
**Members are order-independent.** A member refitted alone reproduces the ensemble's member exactly, because nothing about member *k* depends on members 0…k−1. Without that, re-running one failed member of a batch would silently produce a model the run record does not describe.
**Verified:** five members on 5,000 transitions in 8.0s on CPU; per-member validation errors 0.0034–0.0061, sd 0.0010; each member drew ~50 of 80 training episodes.
**Raised Q-011** — resampling granularity is not a free choice for H1; see the open question.
**Plan ref:** S§W3 Wed, P§9.1, P§10.3, P§14.2.
**Reviewed by Sol:** pending.

### D-051 · 2026-08-16 · The behaviour policy is stationary across episodes
**Correction.** D-049 treated the policy's cross-episode drift as a *splitting* problem and claimed striding handled it. Sol showed it is a **data-generation** problem, and striding does not touch it. `ExploratoryPolicy` carried its coverage counters across episodes, so later episodes came from a different behaviour distribution than earlier ones — and because Experiment 1's datasets are nested prefixes, **dataset size was confounded with behaviour**.
**Measured, and worse than either of us stated.** Over one collection, by prefix: moved fraction 0.340 → 0.527, rule-carrying transitions per step **0.520 → 0.280**, and the action distribution at N=100 was `[0.46, 0.15, 0.10, 0.15, 0.14]` against a near-uniform `[0.22, 0.20, 0.19, 0.19, 0.19]` at N=5000. The N=100 condition was not "less data" — it was data from a barely-warmed-up policy with nearly double the informative-transition density. H1's data-size sweep would have varied two things at once.
**Fix:** `ExploratoryPolicy.reset()` clears the adaptive counters, and `collect()` calls it at the start of every episode. Fixed action probabilities and the within-episode coverage logic are retained; only cross-episode adaptation is removed.
**Verified as stationarity, not asserted.** Averaged over 40 seeds, moved fraction by *episode index* shows no systematic pattern — episode 0 at 0.5895 against 0.5614 for episodes 5+, a difference of **+1.1 SE**. Episodes are now IID draws. Coverage after the change still holds: at N=5000, bumps 919 pass / 1065 block and (shape, action) coverage 100%.
**D-020's evidence is superseded in part.** The PPO-substitution coverage measurements were taken under the non-stationary policy. The conclusion survives — coverage is adequate at large N and thin at small N, which P§3.2.1 counts as estimation failure — but the numbers must be re-reported from the stationary policy in the methodology.
**Plan ref:** P§13.2, P§3.2.1. Corrects D-049's exchangeability claim.
**Reviewed by Sol:** finding is Sol's; the fix is not yet reviewed.

### D-052 · 2026-08-16 · Three disjoint pools, and a shorter episode
**Decision:** training, validation and evaluation are **three physically separate draws** from their own named streams — `env`/`policy`, `val_env`/`val_policy`, `eval_env`/`eval_policy`. `collect_pools()` returns all three. **`EPISODE_LENGTH` 50 → 10.**
**Why separate pools:** Sol's finding, verified. Carving validation from a nested prefix gave N=250 one validation episode and N=5000 twenty, so dataset size changed the validation composition, its sample size, the early-stopping noise and the chance of a lucky checkpoint — worst at small N, which is where Experiment 1's conclusion is decided. It also spent the registered N on validation: a "100-transition" condition **trained on 50**. The registered N is now training transitions only. Verified: train = exactly N at every size, validation = 400 transitions and evaluation = 1,000, both byte-identical across N = 100 / 250 / 1000 / 5000.
**Why a shorter episode:** at length 50, N=100 held two episodes and, after the old internal split, **one** training episode — an episode bootstrap over one episode has exactly one possible sample, so ensemble diversity there came from initialisation alone. At length 10 it holds ten. Measured cost at N=5000: rule-carrying transitions 748/1177 → 712/1123 and (shape, action) coverage 100% either way. The independence is bought for ~5% of the informative transitions. Verified at N=100: members now draw 4–9 unique episodes of 10.
**Change Records:** `EPISODE_LENGTH` added at 10 (was a module default of 50); `VALIDATION_EPISODES = 40`; `EVALUATION_EPISODES = 100`; `STREAM_VERSION` 2 → 3 for the four new purposes. **Has data been seen?** No confirmatory data exists and zero compute has been consumed.
**Plan ref:** P§10.1, P§10.2, S§W3. Supersedes D-049's strided split.
**Reviewed by Sol:** requirement is Sol's; this implementation is not yet reviewed.

### D-053 · 2026-08-16 · Q-011 closed — episode bootstrap is primary, and the alternatives are labelled sensitivities
**Decision:** Sol's ruling. **Episode-level block bootstrap is the fixed primary method** for H1 and H2: resample complete training episodes with replacement, never resample validation or evaluation, score every member on the identical fixed evaluation pool, keep initialisation, bootstrap and batch order on separate streams. Transition-level bootstrap is retained only as a **clearly labelled secondary sensitivity** — H1's verdict uses episode bootstrap alone, failure to reproduce under transition bootstrap does not overturn it, and the sensitivity may not be used to pick the more favourable curve. An **initialisation-only** ensemble (`granularity="none"`) is added as the better sensitivity, because it isolates how much disagreement comes from weights rather than blurring the two sources.
**Why transition-level cannot decide a verdict:** it treats correlated transitions as exchangeable and retains **>90%** of training episodes against ~63% for the block bootstrap, so it suppresses the data-resampling component of disagreement — the component H1 is about.
**The measurement that raised it:** disagreement by dataset size, one seed, was 0.1437 / 0.1836 / 0.0766 (episode) against 0.1101 / 0.1037 / 0.0612 (transition) at N = 250 / 1000 / 5000. The ratio 1.30× / 1.77× / 1.25× is not constant, so granularity bends the curve W4 Mon's trend test runs on rather than scaling it. **Those numbers predate D-051 and D-052 and are not to be reused** — they were taken under a non-stationary policy and a split-derived validation set.
**Plan ref:** P§9.1, P§10.3, S§W4 Mon.
**Reviewed by Sol:** **yes — the ruling is Sol's.**

### D-054 · 2026-08-16 · Frozen data-generation procedure, a bounded sensitivity scope, and a claim withdrawn
**Three of Sol's clarifications, all accepted.**

**(a) Stationarity is structural, and I overstated it.** D-051 reported "+1.1 SE by episode index" as though it established IID episodes. A null diagnostic never proves the null. The correct justification is *structural*: environment state resets independently, every adaptive counter resets, action probabilities and within-episode rules are fixed, and no mutable state other than independent RNG progression crosses an episode boundary. The statement of record: *"the revised generator is designed to produce IID episodes conditional on configuration and seed; the episode-index diagnostic found no material residual drift."* Two structural tests replace the appeal to the diagnostic — that no mutable policy state survives `reset()`, and that an episode's actions do not depend on how many episodes preceded it from identical state and RNG state.
**Stronger evidence than either, found while verifying episode length:** the rule-carrying transition rate is now **flat in N** — 0.227 / 0.252 / 0.250 at N = 100 / 1,000 / 5,000 over eight seeds, against 0.520 / 0.355 / 0.280 before. A confound that ran with dataset size no longer does.

**(b) The data-generation procedure is frozen and recorded.** `EPISODE_LENGTH = 10`, `VALIDATION_EPISODES = 40`, `EVALUATION_EPISODES = 100`, the six pool stream purposes, and the per-episode policy reset are all preregistered in `constants.py` and mirrored into §2. `episode_length` may still be overridden **below** `CONFIRMATORY_SEED_BASE`, is recorded on the dataset and survives a save/load round trip, and **raises** on a confirmatory seed. A procedure that a caller can change silently is not frozen.
**Episode length verified before freezing**, as Sol required, over eight development seeds: rule-carrying rate, pass/block balance, action coverage, unique episodes per bootstrap member (0.655 / 0.639 / 0.634 — the classic ~63% at *every* N, including 100), and disagreement variance at N = 100 (CV 0.12 over five seeds).

**(c) The bootstrap sensitivities have a declared scope, and it is the narrow one.** Episode block bootstrap is primary **across the registered design**. Transition-level and initialisation-only ensembles are **development diagnostics in the W3 Friday pilot only**: they do not enter a confirmatory verdict and they are not in the 8,197-fit execution plan. Sol's warning is the reason — applied to every H1/H2 condition they would add thousands of fits and invalidate the compute estimate, and a capability existing in `granularity=` is not a decision to use it. Running them on a preregistered canonical subset as formal ablations remains available, but requires charging the fits to the ablation allowance and updating the compute schedule **first**.
**Transition bootstrap is never described as an equally valid alternative.** It is a diagnostic showing how disagreement changes when temporal dependence is ignored.

**D-020's methodology evidence is superseded**, not silently replaced: `docs/method_draft.md` now carries the stationary-generator figures and states explicitly that the earlier development measurement was taken under a different generator. The qualitative substitution argument is unaffected and still supported.
**Plan ref:** P§13.2, P§3.2.1, P§14.2, P§14.3. Corrects D-051's stationarity claim; bounds D-053's sensitivities.
**Reviewed by Sol:** clarifications are Sol's; this implementation is not yet reviewed.

### D-055 · 2026-08-16 · Three blockers, two of them tests that checked a mechanism and claimed a property
**Sol's three blockers on `9bdb22a`, all verified before fixing, all confirmed.**

**(1) Feature repair broke the paired failure set.** `collect_pools` used one unit for both stream identity and environment construction, so resolving a repair changed the stream key. Measured: `data_repair` and `capacity_repair` preserved the key (Experiment 1 excludes `n_transitions` from its comparison group, 2B excludes `hidden_size`) — but `feature_repair` changes `withheld_features`, which 2A does **not** exclude, so the repair drew a **different** environment, validation and evaluation pool from its own baseline. P§7.2 requires a repair to be scored on the same recorded failure set; it was not.
**Fix:** stream identity now derives from the **unresolved** unit while the environment and encoder use the **effective** one. Tested for all three arms, compared on the **latent** trajectory — actions, episode indices and agent positions — because restoring a feature changes the observation width and byte equality of encoded observations is the wrong test.
**Why my test missed it:** it covered `data_repair` only. Two arms working was not evidence about the third, and the one that failed was the one whose repair touches an identity field its own experiment does not exclude.

**(2) "Evaluation cannot reach model selection" was false.** My test asserted that `train` has no parameter *named* `evaluation`. The pools share a type, so `train(model, pools.train, pools.evaluation, ...)` simply ran — verified, `n_validation=1000` — and every reported number would have been selected on. **Fix:** `TransitionDataset` carries its `pool`, and `train` requires `train_data.pool == "train"` and `validation.pool == "validation"`. Provenance is checked instead of the signature.
**This is the second time in two reviews** I wrote a test that checked a mechanism and claimed a property, in a test written *because* Sol asked for properties. Recorded as a pattern, not an incident.

**(3) The frozen procedure had open confirmatory paths.** A confirmatory caller could override `n_transitions`, inject a policy without `reset()`, or pass `granularity="transition"`. The last is the worst: granularity is not part of `Config`, so a non-primary fit would have occupied the **same recorded identity** as the primary one. All three now raise on a confirmatory seed and remain available below `CONFIRMATORY_SEED_BASE`.

**Two further corrections.**
*Provenance:* loading a record without `episode_length` used to stamp it with the current constant, so a dataset generated at 50 would be relabelled 10 — the opposite of a provenance guarantee. It now raises. *Reset regression test:* it only noticed non-empty dicts, lists and sets, so a scalar counter or array would have passed. Replaced with an explicit allowlist of permitted persistent fields plus a spy asserting `collect()` calls `reset()` exactly once per episode.
*Byte-identity claims* across dataset sizes now compare every array, not only `obs`.
**Plan ref:** P§7.2, P§10.1, P§14.2. Corrects D-052's implementation and D-054's override closure.
**Reviewed by Sol:** findings are Sol's; these fixes are not yet reviewed.

### D-056 · 2026-08-16 · The repair split reaches training, and the size guard reaches `collect()`
**Three more blockers from Sol on `81781d3`, all verified before fixing, all confirmed.**

**(1) `collect()` accepted any size on a confirmatory seed.** The guard lived only in `collect_pools`, so `collect(unit, 99, stage="exp1", seed=1000)` succeeded — and so did the same call with `pool="evaluation"`, minting a 99-transition confirmatory evaluation pool. My delta said the override path was closed; it was closed in one of two places. **Fix:** `expected_size(effective, pool, episode_length)` gives each pool exactly one legal confirmatory size, and `collect()` enforces it directly. Tested on direct calls for all three pools.

**(2) The unresolved/effective split never reached training, and this was the serious one.** `train_ensemble` took one unit and used it for the model *and* the streams. Measured: with the unresolved unit a **capacity repair built the original `hidden=16` network** — the repair was never applied, **nothing raised**, and every capacity condition would have been labelled "repair failed" on a model that was never repaired. Feature repair failed differently, on the input schema. With the effective unit the model was right but the streams moved off the baseline's.
**Fix:** `train_ensemble(unit, pools, ..., arm=)` resolves the effective unit for `WorldModel` and keeps the unresolved unit for every named stream — the same split the pools already used. Verified per arm: baseline `hidden=16`; capacity repair `hidden=256`; feature repair input 30 dims against the baseline's 22; data repair 2,500 training transitions against 250. `Ensemble` now carries `unit`, `effective_unit` and `arm`.
**Why pool tests did not catch it:** they tested *collection*. The defect was in *training*. Sol asked for one-epoch training tests per arm, which is what now exists.

**(3) Repaired datasets could not reconstruct their own stream.** `TransitionDataset.unit` held the effective unit while the stream was keyed on the unresolved one, and neither the source unit, the arm nor the stage was recorded — so a feature-repair dataset was indistinguishable from a baseline whose unit already had those features. **Fix:** `source_unit`, `arm`, `stage` and `stream_version` are recorded and round-trip, alongside `pool` and `episode_length`.

**Wording narrowed, per Sol.** The `granularity` guard is a guard on `train_ensemble`, not proof that every confirmatory path is closed — `bootstrap_episodes()` plus `train(train_index=...)` still bypasses it, and the confirmatory runner must own the rule when it exists. The error message says so. Also corrected: `9bdb22a` was a *reviewed* base, not a fully certified commit.
**Plan ref:** P§7.2, P§7.3, P§8.3, P§14.2. Completes D-055.
**Reviewed by Sol:** findings are Sol's; these fixes are not yet reviewed.

### D-057 · 2026-08-16 · Pools must belong to the run that trains on them — and a third tautological test
**Two findings from Sol on `c207c55`, both verified, both confirmed.**

**(1) Pools and the ensemble could disagree about the arm.** `arm` reaches `collect_pools` and `train_ensemble` independently, and nothing checked that they agreed. Measured: baseline pools plus `arm="data_repair"` **trained on 250 transitions** while the ensemble reported the data-repair identity with its effective 2,500. That is a false repair label of exactly the kind D-056 removed, arriving one layer up — the run records one condition and trains on another.
Capacity repair accepted mismatched pools silently, because capacity does not change the observation width. Feature repair happened to die on a dimension mismatch, and Sol's point about that is the one worth keeping: **an accidental runtime error in one arm is not an invariant.**
**Fix:** `assert_pools_match()` runs before any model is built and validates every pool's `source_unit`, effective `unit`, `arm`, `stage`, `seed` and pool label against the requested run. Five mismatch classes tested — baseline pools with a repair arm, repair pools with baseline, wrong seed, wrong stage, wrong source unit — plus a positive test per arm so the guard cannot be so strict that the legitimate path breaks.

**(2) The model-stream test was tautological — the third of this kind.** It asserted `stream_key(unit, …) == stream_key(Arm("baseline").resolve(unit), …)`. Resolving the *baseline* arm returns the unit unchanged, so it compared a value with itself and passed for every arm while testing nothing.
**Fix:** the test now monkeypatches `stream` inside `train_ensemble` and captures which unit each of `bootstrap`, `init` and `batch` was actually keyed on, asserting all three received the **unresolved** unit for every repair arm. It also asserts **non-vacuity** — for an arm that moves an identity field, the effective-unit key genuinely differs, so the test is capable of failing.
**The pattern, now three deep:** "evaluation cannot reach selection" checked a parameter name; the pool non-overlap test checked value overlap while claiming episode comparison; this one compared a value with itself. All three were written *in response to* Sol asking for property tests. The common failure is writing the assertion that is easiest to express from inside the implementation rather than the one that states the claim.
**Plan ref:** P§7.2, P§8.3. Completes D-055 and D-056.
**Reviewed by Sol:** findings are Sol's; these fixes are not yet reviewed.

### D-058 · 2026-08-16 · W3 Friday's pilot, and the first thing it found
**Decision:** `models/uncertainty.py` implements P§10.3's definitions — mean pairwise disagreement, ensemble predictive variance, per-dimension normalised error, and the H2 ratio as a **ratio of means** computed per seed with a `1e-6` denominator floor and aggregated across seeds only after dividing. `experiments/w3_pilot.py` runs the sweep and regenerates both curves from logged rows.
**Executed:** 6 sizes × 3 development seeds × 5 members = **90 fits**, on CPU at 4 threads. The student's GPU was at 14.2/16.4 GB under another workload; it was not touched. **Still zero GPU-hours.**
**The finding, and it is not about the shape of a curve.** Error falls monotonically with N. **Disagreement does not** — it peaks at N = 250 and is *lower* at N = 100 than at N = 250, reproducibly across seeds and in an independent earlier probe at a different hidden size.
**Measured mechanism:** at N = 100 the ensemble's mean prediction has sd 0.065 against the targets' 0.220 — 29% of the variation in what it is predicting, rising to 96% by N = 5,000. The members have not learned different wrong answers; they have collapsed toward the *same* near-constant, so they agree because there is nothing yet to disagree about.
**Why it matters:** high error with low disagreement is **the H2 signature**, and here an *estimation* failure produced it — in a condition where the model class is adequate and more data demonstrably repairs the problem. The ratio is lowest at N = 100 (0.462), below every other size. If it replicates at five seeds on confirmatory data it does not falsify H2, but it bounds it: the ratio would not discriminate failure types at the extreme of estimation failure, and a critic trained across such conditions would be learning a signature that points both ways.
**Status of the number: exploratory.** Three development seeds, one configuration, permanently excluded from every confirmatory result (D-034). No H1 or H2 claim is made, and the printed report says so in its own text. W4 Mon's rank-correlation trend test is the instrument.
**Consequences recorded rather than acted on:** the W4 Mon trend test must be read knowing the curve is non-monotone at the small end, and W5's MDE simulation should know which conditions sit in the collapsed regime, because their disagreement has a different mechanism from the rest of the sweep.
**Plan ref:** S§W3 Fri, S§W3 Sat, P§10.3, P§4.2.
**Reviewed by Sol:** pending — the collapse finding is the part worth attacking.

### D-059 · 2026-08-16 · Correction to D-058 — what the pilot actually measured, and what it did not
**Four findings from Sol, all verified, all confirmed. Two of them withdraw claims I made.**

**(1) That number is not the registered H2 ratio.** P§10.3 defines the endpoint over a condition's **failure set** — transitions above the W4 Friday threshold, which does not exist yet. The pilot took *every movement transition*. So 0.462 is an **exploratory whole-pool disagreement/error ratio**, and calling it "the H2 signature" was wrong. The printed report, the methodology and the figures now label it as such in their own text, and the ratio column carries an explicit footnote.

**(2) "Estimation failure" was a construction label, not a verified one.** P§7.1 is explicit that a condition is labelled by what repairs it, established by the counterfactual protocol — and repair validation has not run. The sentence "an estimation failure produced the H2 signature" asserted both halves without either. Replaced with "small-data condition" and "estimation-**design** condition" throughout.

**(3) The per-transition export the schedule required was missing.** S§W3 Fri says disagreement and predictive variance are *"exported per transition"*; `rows.json` held one summary per (N, seed). Without the transition level, failure-set filtering, the local error/disagreement correlation and independent regeneration of the registered endpoint are all impossible after the fact. `per_transition_table()` now exports error, disagreement, predictive variance, episode and step per transition, and **the 90 fits were rerun** because the predictions had not been retained.

**(4) The collapse mechanism was not evidenced — and the inference was invalid.** I compared the sd of the **ensemble mean** with the targets' and concluded that members had "all collapsed toward the same near-constant". Sol pointed out that members which vary can cancel in their average. Verified with a constructed counterexample: ensemble-mean sd **0.051** while individual members have sd **2.556**. The inference does not go through.
**Measured properly, per member, the story is different and better.** Member prediction sd as a fraction of the targets': at N=100 the ensemble mean sits at 0.231 but members range **0.219 to 0.639**; at N=250 they range **0.220 to 0.836**; by N=5,000 they have converged at 0.939–0.974. So it is **heterogeneity, not collapse** — at the smallest sizes some members learn the rule and others do not, the ensemble mean is flatter than any individual member because they partly cancel, and disagreement peaks at N=250 precisely where the spread across members is widest. That is a cleaner mechanism than the one I claimed, and it is the one the data supports.

**Statistical wording.** "The N=250 sd is smaller than the gap" does not establish that a result is not a seed artefact. The report now gives the **paired within-seed differences** — +0.179, +0.360, +0.102 — and says only that the direction reproduced in all three development seeds.

**Three code corrections.** The development-seed `assert` became a `ValueError`, because assertions vanish under `-O` and are not a safety boundary. The pairwise-convention docstring claimed ordered and unordered means differ by a factor of two; they are **identical** when each is normalised by its own pair count, verified against an explicit enumeration, and the two-member test could not have distinguished them — it now checks against an enumeration at k=5. The denominator-floor test used zero error *and* zero disagreement, so it never exercised the floor; it now places members symmetrically around the targets, giving exactly zero error with large disagreement.
**Scope narrowed:** `uncertainty.py` does not implement P§10.3's per-condition error/disagreement correlation, and no longer claims to.

**What survives from D-058:** the curves, the non-monotone disagreement, the paired direction across three seeds, and the observation that a small-data condition showed the lowest whole-pool ratio in the sweep. What does not: that it was the H2 signature, that the condition is a verified estimation failure, and that the members collapsed.
**Plan ref:** P§7.1, P§10.1, P§10.3, S§W3 Fri. Supersedes D-058's interpretation.
**Reviewed by Sol:** findings are Sol's; these corrections are not yet reviewed.

### D-060 · 2026-08-16 · Week 3 audit — seven defects, and Sol's auxiliary conditional answered
**Decision:** a line-by-line behavioural audit of everything built in Week 3, before Week 4 builds a gate verdict on it. The precedent is D-015 and D-021, both of which found defects the suite was green on. Nine Sol reviews are not a substitute: Sol reviews what is *reported* plus a diff, and cannot probe running code.

| # | Defect | Severity | Why it mattered |
|---|---|---|---|
| W3-1 | **The normalising scale is recomputed from whatever subset is passed in** | **Serious** | P§10.3 requires per-dimension normalised error but never says *which set* defines the normalisation. Measured: scale is [0.229, 0.224] over the full evaluation pool and [0.294, 0.348] over its worst 5%. Because the scale is a **vector**, it does not cancel between the ratio's numerator and denominator — so the **registered H2 endpoint itself** shifts by up to **4.6%** with a choice nobody made. H2's verdict compares ratios across families |
| W3-2 | **Pilot outputs carried no provenance** | **Serious** | The pilot wrote bare JSON and `.npz`, bypassing `RunLogger` entirely — no commit, no dirty flag, no package versions, no `seed_partition`. P§13.7 requires every figure regenerable from logs *with* the provenance that explains them, and Week 1 built exactly that machinery |
| W3-3 | Activation report used `members[0]` only | Material | One member of five, undocumented — and D-047's conditional is about the detached head in general, so a single member could have been the best or worst of them |
| W3-4 | **`member_predictions` left every model in eval mode** | **Serious, latent** | Inert for this MLP. But P§9.3 plans **MC-dropout** as reliability-gate fallback B2 — "dropout at test time". Under it, a model left in eval mode returns deterministic predictions with **exactly zero disagreement**, which reads as "MC-dropout also fails H1" and triggers a false pivot at the very gate the fallback exists for |
| W3-5 | `TrainConfig.val_fraction` was dead | Minor | Nothing referenced it after D-052 replaced the split with pools. A knob that does nothing still tells a reader a split happens here |
| W3-6 | `train_index` was unvalidated, and **torch wraps negative indices silently** | Material | `x[[-1]]` returns the last row rather than raising. A resample producing a negative index would train on the wrong rows and surface, if at all, as an unrelated error much later — the failure mode reported was "no interact transitions" |
| W3-7 | Dead import | Trivial | — |

**Checked and found correct**, so the audit is not only a defect list: best-checkpoint restoration on all three exit paths (early stop, max epochs, single epoch); patience counting from the best epoch; the five members sharing no bootstrap draw, initialisation or batch order, before or after training; member results independent of `ensemble_size`; Experiment 1's training pools still exact nested prefixes after the three-pool restructure; the data repair extending rather than redrawing; validation and evaluation byte-identical across sizes **and arms**; **zero** shared (obs, action) pairs between training and evaluation; action-conditional passthrough correct for all five actions and row-wise on mixed batches; the trunk isolated under `predict_next_obs` as well as under `losses`; the block bootstrap genuinely duplicating whole episodes (multiplicities 1–4, 63% distinct); the final partial minibatch used; no NaN or inf anywhere; 300 units, 150/150, 8,197 fits unchanged; per-transition exports reproducing every summary exactly.

**D-047's conditional is now answered.** Across all five members and every dataset size, the detached auxiliary head **never** beats its copy baseline: 0 of 3 seeds at every size, best individual member 0.225 against a 0.169 baseline, and it does not improve with data (≈0.25 from N=500 up). Sol's condition for reconsidering the architecture is met. **The compute is not the obstacle** — a second trunk is ~1.98× the parameters and takes the design from ~1.6 to ~3.2 CPU-hours. **The recommendation is to downgrade rather than to spend it**: activation carries no hypothesis, D-032 already made it a secondary metric, and P§10.2's primary error excludes it. Recorded for Sol rather than decided here, per D-047.
**Plan ref:** P§9.3, P§10.2, P§10.3, P§13.7.
**Reviewed by Sol:** pending — W3-1 changes a registered endpoint and is the one to attack.


---

### D-061 · 2026-08-17 · Sol's ruling — the normalisation scale is the evaluation pool's, fixed before any mask
**Decision (Sol's, adopted in full).** The per-dimension normalising scale is the **target standard deviation computed once from the full fixed evaluation pool, restricted to the eligible movement-transition domain, before any failure mask is applied**. For every condition and seed: compute it from the full movement evaluation pool; reuse that exact vector for the whole-pool *and* the failure-subset calculations; reuse it across every ensemble member and every dataset size sharing that evaluation pool; persist it in the result artefacts; and make it impossible for masking to trigger a recomputation. The registered H2 statistic is then evaluated over the registered failure set **in the pool's units**. The scale is never computed from the failure subset.

**Why it needed a ruling rather than a fix.** P§10.3 requires per-dimension normalised error and does not say which set defines the normalisation. That is a preregistration gap, not an implementation gap, and the W3 audit measured what it costs: the endpoint moves by up to **4.6%** at a 5% failure set on the choice of scale alone (pool scale [0.229, 0.224] against top-5% scale [0.294, 0.348]). W4 Friday's failure set is exactly such a subset, and H2's verdict compares ratios across families, so a wobble of that size is not cosmetic.

**How it is enforced.** `NormalisationScale` (`models/uncertainty.py`) is the only accepted scale in the summary path, its only constructor is `from_evaluation_pool()`, and it records `n_reference` — how many transitions it was measured over. `summarise()`, `normalised_error()` and `per_transition_table()` no longer accept a missing scale: the old `scale=None → recompute from whatever you were handed` default *was* the defect, so it is gone rather than deprecated. A caller holding a masked subset has nothing to build a scale from except the pool. The vector, its reference count, its domain and its source are persisted into `rows.json`, into every `.npz` export and into the attempt manifest, so a number cannot travel without its units — the D-042/D-044 failure mode, arriving through a different quantity.

**A correction carried into the artefacts.** Three files stated that the *ratio* is invariant to the scale choice because numerator and denominator share it. That is false: a **scalar** scale cancels, a **per-dimension** one divides each dimension by a different amount, reshaping both vectors so their norms have no common factor. The claim is corrected in `models/uncertainty.py`, in `tests/test_pools.py`'s own docstring, and in the delta — in the artefacts themselves, not only here.

**Numerically, nothing in the W3 pilot moves.** The pilot scores the whole movement evaluation pool, so pool scale and scored-set scale coincide; the rerun reproduces every published figure to the digit. D-061 pins that, and takes effect at W4 Fri when a mask first exists.
**Plan ref:** P§10.1, P§10.2, P§10.3.
**Reviewed by Sol:** **Sol's ruling.** Adopted as stated; the recommendation Claude offered was the one Sol chose.

### D-062 · 2026-08-17 · Two fixes that fixed the symptom — MC-dropout inference, and rerunnable evidence
**Decision:** both W3 audit fixes are reopened and replaced with mechanism-level ones. **Verified before changing anything, and one of the two findings is different from how it was stated.**

**1. The MC-dropout fix did not fix MC-dropout — Sol is exactly right.** `member_predictions()` saved and restored `model.training` but still called `model.eval()` before the forward pass, so under P§9.3's fallback B2 the dropout layers were **off while predictions were generated**. Restoring the mode afterwards fixes a state side effect, not stochastic inference. Reproduced against the old code path on a model with a real dropout layer: sample spread and mean pairwise disagreement both **exactly 0.000e+00**, against 0.298 and 0.547 under the replacement. Zero, not small — indistinguishable from the estimator genuinely failing H1, at the one gate the fallback exists to rescue.

Replaced by an explicit `PredictionMode`: `"deterministic"` evaluates in `eval()`; `"mc_dropout"` puts dropout layers **back** into training behaviour for each no-gradient pass and leaves everything else in inference behaviour — which is what test-time dropout is, and is not `model.train()` (that would also switch batch-norm to batch statistics, a different estimator). Modes are restored per **submodule**, since the policy changes them independently. `mc_dropout_predictions()` returns `(n_samples, batch, dims)`, the shape the disagreement metric already consumes, so rung 3 changes where members come from and nothing about H1's definition. Sampling forks torch's RNG rather than advancing it, so selecting rung 3 cannot shift any other draw in the process.

**Requesting MC-dropout from a model with no dropout layers now raises.** `WorldModel` has none, so rung 3 at the W4 gate is an explicit architectural change and will be told so, rather than silently returning zero disagreement. That guard is the part that would actually have saved the gate.

**2. The rerun hazard is real, and reachable by a different route than the one described.** Sol's mechanism — append-mode stream plus a record index restarting at zero — is real **at the class level**: two writes of five records into one directory produce ten lines numbered 0–4, 0–4. Measured. But `RunLogger.start` never reaches it: `write_run_record` rejects a duplicate `run_id` first, and a same-scope pilot rerun was **rejected before writing anything**, files byte-identical afterwards. What *is* reachable is the same end state by another path: a rerun at a **different set of sizes** shares no `run_id`, so nothing is rejected — measured, two run records and two exports on disk while `rows.json` described only the second. One directory, two executions' evidence, no marking of which was which. Sol's conclusion stands; the route is different, and the difference matters because the fix has to cover both.

Fixed at three layers, because a fix in one layer is not a fix (D-056): `RunLogger` refuses to append by default and, when an append is explicitly requested, **continues** the counter instead of restarting it; the pilot writes into a fresh `attempt-NNN` directory created with a non-`exist_ok` `mkdir` and never reopens one; and `load_runs()` raises when one `run_id` appears in two directories — attempts share run identities by construction, so a tree containing several would silently double every record behind every interval.

**Evidence, not assertion.** Each attempt carries `manifest.json`: manifest version, commit, dirty flag, branch, package versions, parameters, run and member-record counts, the normalisation vector per seed, every run's four identities, and every artefact with its `sha256`, size and provenance. "Immutable" has to be checkable by someone else, so the digests are recorded rather than the property claimed. The delivered attempt is verified by the suite against its own manifest — 18 runs, 90 member records — instead of on Claude's word in a delta.

**Prior evidence, and a second thing this exposed.** The pre-closeout flat layout under `runs/w3_pilot/` is superseded by a fresh attempt that reproduces **every** published number to the digit under the same seeds — all four uncertainty fields at all six sizes and all three seeds, and all 90 member validation errors — which is what confirms D-061 pins the pilot's numbers rather than changing them. The flat files are **moved, not deleted**, to `runs/w3_pilot/pre_d062/`: two copies of one set of `run_id`s in the load path is the mixed-evidence state this decision removes, and `load_runs()` now says so out loud.

But `runs/` and `figures/` are in `.gitignore`, so **none of that evidence has ever been in git** — an earlier draft of this record asserted it was, which was wrong and is corrected here. It means the manifest Sol asked for could not have travelled in a bundle at all. The compact artefacts — `manifest.json` and `rows.json`, 64 KB together — are therefore now tracked by explicit `.gitignore` exception, and they carry the counts independently: 18 run entries with their four identities each, and 18 rows × 5 member validation errors = 90 fits. The bulky run records, transition exports and figures stay untracked and regenerable, digested in the manifest.
**Note on provenance:** an attempt generated *before* the commit that contains its code necessarily records `dirty=true`. The delivered attempt is therefore regenerated **after** the closeout commit, so its record names a real commit and a clean tree.
**Plan ref:** P§9.3, P§13.7, P§14.4.
**Reviewed by Sol:** both findings Sol's. Fixes pending review; the corrected account of finding 2 is flagged for attack.

### D-063 · 2026-08-17 · Sol's ruling — no second trunk; the activation head is a non-decisional diagnostic
**Decision (Sol's, adopted).** Do **not** build a second activation-prediction trunk. The observed auxiliary results do not justify doubling the predictive architecture or the compute, especially as activation prediction is no part of H1 or H2 and the architecture question has now been examined on development evidence. The existing **detached** head is retained only as a secondary audit diagnostic, under five restrictions: it cannot affect the primary trunk; it cannot affect primary early stopping or checkpoint selection; it cannot define the failure set; it cannot affect H1, H2, repair labels, or the primary residual the critic reads; and the copy-current-activation baseline remains mandatory. This closes the conditional D-047 left open.

**What is now reported, per member and in aggregate:** all four views rather than the combined interaction slice alone — changed activation transitions, interaction transitions with **no** activation change, all interaction transitions, and the copy baseline. The baseline is reported **per slice**, because copying is exactly right on a no-change transition and exactly wrong on a changed one, so a single pooled baseline number describes the change rate more than it describes either model. It is model-independent by construction — it reads the current bit only — so it is one number per condition rather than per member.

**The conclusion, stated at the width the evidence supports:** the detached head did not reliably outperform the copy baseline, and it is retained as a non-decisional diagnostic. That is **not** evidence for or against any H1/H2 mechanism, and no result in the thesis turns on it.
**Plan ref:** P§9.3, P§10.2, D-032, D-047.
**Reviewed by Sol:** **Sol's ruling**, matching the recommendation in delta 28.

### D-064 · 2026-08-17 · Corrections to D-061 and D-062 — a claim narrowed, and an isolation that was CPU-only
**Decision:** two claims made in the Week 3 closeout are corrected, both found by Sol on review of delta 29, and both are about **what was claimed** rather than about what the code does for the Week 3 numbers.

**1. "Enforced by construction" was too strong.** D-061 and the module docstring said `NormalisationScale` makes a subset-derived scale impossible and that "a mask has no route to recompute it". It does not. The dataclass constructor is public, `from_evaluation_pool()` accepts any 2-D tensor including a masked one, and the low-level metric functions still take raw tensors. What is true and now stated: the **registered summary path requires an explicit scale and will not invent one**, so a subset can no longer be normalised *by accident*; the W3 pilot builds the scale from the full movement evaluation pool; and the W4 runner **must** build it before producing the failure mask and reuse the same object for the whole-pool and masked calculations. That is a **call-site invariant**, and it belongs in the W4 runner's required tests (C-010), not in a claim this module can make alone.

Since it cannot be prevented at the type, it is made **auditable**: `n_reference` records how many transitions the vector was measured over, so a subset-derived scale is visible in every artefact carrying it. A test now asserts that a masked construction records the mask's size (10, not 200) and produces a different vector — the property the previous test's *name* claimed while asserting something weaker.

**2. The RNG isolation claim held on CPU only.** `mc_dropout_predictions` forked with `torch.random.fork_rng(devices=[])`. `fork_rng` always forks the CPU generator but forks device generators **only for the devices it is handed**, so on a GPU the CUDA generator kept advancing — and the reliability gate's fallback estimator is precisely the thing that would be run on a GPU. Verified rather than assumed, on this machine's CUDA device: under the old call `torch.cuda.get_rng_state()` was **not** preserved across a sampling call; under the fix it is, and the samples still vary. The devices are now derived from the model's parameters and buffers and from the input tensors, a call spanning two accelerator types raises rather than forking one of them, and the CPU-only path is unchanged (`(None, [])`). The test that claimed "the global RNG is untouched" is renamed to the CPU claim it actually made, and a CUDA test covers the device case when a device exists; the derivation itself is covered on any machine using meta tensors.

**Sol's four rulings on delta 29's questions, recorded:** the corrected account of the rerun defect is accepted; the per-slice copy baseline is accepted and preferred, the exact-zero unchanged-transition baseline being what makes the auxiliary result legible; the duplicate-`run_id` guard belongs in `load_runs` as defence in depth, **and** the confirmatory runner must additionally select one immutable attempt explicitly (C-010); and exact reproduction is valid evidence that D-061 **pins** the Week 3 numbers, because the scored set here is the complete movement evaluation pool — but it does **not** validate the future masked call site, which must be tested in the W4 runner.

**Also.** The closeout bundle excluded `runs/` and snapshotted only the manifest, so Sol could see the artefact digests and the counters but not the 18 summary rows, the 90 validation errors, the per-member auxiliary values or the per-row normalisation metadata. A test passing on the producing machine is not a substitute for the evidence file in the reviewer's hands — the same lesson as D-036 and D-041, arriving one level down: the exclusion mechanism built to keep the bundle reviewable had removed the evidence the bundle existed to deliver. `rows.json` is included explicitly from now on.

**The compact-base exception is allowed for this closeout only.** Sol: certification still forms one chain from `2875e60`, and this is not permission to use reviewed-but-uncertified bases routinely.
**Plan ref:** P§9.3, P§10.3, P§13.7.
**Reviewed by Sol:** both corrections are Sol's findings on delta 29. No experiment was rerun; the 90 fits stand.

### D-065 · 2026-08-17 · The seeding was wider than the fork — device-local seeding
**Decision:** `mc_dropout_predictions` seeds **only** the generators its `fork_rng` will restore. `torch.default_generator.manual_seed(seed)` for the CPU, then each derived accelerator device individually; devices absent from `forkable_devices()` are never seeded.

**The defect, found by Sol on delta 30 and reproduced before changing anything.** D-064 fixed the *fork* to cover the devices in use, and left the *seeding* using `torch.manual_seed`, which is a convenience that seeds the CPU generator **and every accelerator device's** generator. The two sets no longer matched, so the call reseeded generators nothing would restore:

* a **CPU** MC-dropout call on a CUDA machine forks the CPU generator alone, then reseeds every CUDA device. Measured on this machine: `torch.cuda.get_rng_state()` was **not** preserved across a call whose computation never touched the GPU at all;
* a call on **cuda:0** of a multi-GPU machine forks device 0 and reseeds devices 1, 2, …, which are never put back.

**Why the D-064 test missed it, which is the part worth keeping.** The CUDA test checked the one device that was both seeded *and* forked — the single case where the mismatch cancels. It was written against the machine it ran on rather than against the claim, and the claim was "the global RNG is untouched". This is the same defect class as D-055 and D-057 — an assertion that cannot fail in the configuration it runs in — arriving through *hardware* rather than through code. A single-GPU machine cannot distinguish "seeds what it forks" from "seeds everything and forks one thing".

**Tests.** A CPU-only call now asserts **every** CUDA device's state is unchanged — this runs on the development machine and is the case that failed before the fix. A two-device test asserts used and unused devices are both untouched; it **skips here** and is recorded as skipped rather than presented as passing, because this machine has one GPU. `seed_locally` is additionally tested directly on any machine: the CPU generator moves, no device generator does, and a `"meta"` device type seeds nothing rather than looking for a module that does not exist. Stochasticity and seed reproducibility are retained and now also asserted **on the device** — device-local seeding costs neither.

**Also.** `CLAUDE.md`'s operational overview still told the next Claude that `NormalisationScale` "is the only accepted argument … so a failure mask has nothing to recompute from" — the exact model D-064 withdrew, in the one file a reset Claude reads first. Replaced with the explicit-and-auditable claim and a pointer to C-010. The `PROJECT_STATE.md` §7 entry that carries the old wording is **not** edited: §7 is append-only (D-014), and the entry immediately following it withdraws the claim by name.
**Plan ref:** P§9.3.
**Reviewed by Sol:** Sol's finding on delta 30. The multi-GPU case is unverified on the development machine and is declared as such.

### D-066 · 2026-08-17 · One bundle file, and a delta that names the commit it describes
**Decision:** the generated bundle has **one** canonical name, `SOL_BUNDLE.txt`, and every delta carries a `BUNDLE_COMMIT:` line naming the commit its bundle must report. If the bundle's header disagrees with that line, Sol refuses the pair before reviewing content.

**What happened.** Delta 31 was correct and its bundle was correctly generated at `4a6e4dd`. Sol received `sol_bundle_microcloseout.txt` at `08391ae` — the *previous* bundle — and reviewed a delta describing code the bundle did not contain. Three files named `sol_bundle_closeout.txt`, `sol_bundle_microcloseout.txt` and `sol_bundle_rng_patch.txt` sat side by side in the repository root, generated ninety minutes apart, all with plausible names. Picking the wrong one was the likely outcome, not an unlucky one.

**Whose failure this is.** Mine, and it is the same failure as D-036 and D-041 in a third costume. Those said: generating a bundle is not delivering one, and a bundle that selects its own contents can still mislead. This one says **a bundle that cannot be told apart from a stale sibling is not delivered either.** The student did nothing wrong; the packaging made the error available. Each previous instance was fixed by making the artefact better, and each time the *handover* stayed unguarded.

**Two changes, one removing the ambiguity and one making a mismatch detectable:**

* one file name, overwritten each time, so "the bundle" is unambiguous and a stale copy cannot survive beside a fresh one. The old per-session names are deleted; they are regenerable from one command and are not evidence — the evidence is `attempt-001` and git;
* the **bundle names its delta** — `DELTA_ID` and the delta file's sha256, in the bundle's header. The two are produced at different moments by different commands, so nothing else tied them together; now the reviewer can refuse a mismatched pair in one comparison without trusting either producer.

  The obvious version of this does not work, and I found that out by using it. Stamping the *commit* into the *delta* changes the delta, which changes the commit — so the stamped line always names its own predecessor, and mine was one commit stale the moment it was written. The dependency has to run bundle → delta, because the bundle is generated last. Recorded because the broken version looks correct and I would otherwise reach for it again.

**And a check before sending.** The eight properties Sol listed for this bundle — new commit, clean tree, the expected test counts, the named implementation and tests, the corrected wording — are verified **against the generated file**, mechanically, rather than by looking at it. On the first run that check failed item two: the tree was dirty because `.gitignore` had not been committed yet, which is precisely the kind of thing an eye slides past.
**Plan ref:** P§13.7.
**Reviewed by Sol:** the mismatch was Sol's finding. Sol's provisional rulings on delta 31 stand: the two-device test may remain skipped and **explicitly unverified**, provided the implementation-level test proves `seed_locally()` touches only the CPU generator and the derived indices; and the append-only `PROJECT_STATE.md` §7 and D-061 entries stay intact, with `CLAUDE.md` carrying only the corrected description.

### D-067 · 2026-08-17 · Week 3 certified and frozen at `9c0d89d`, with its boundaries
**Decision:** Sol certified `9c0d89d75b89ce911a705959e5595a61d4cda678` on 2026-08-17. **Week 3 is closed and frozen.** The certification covers the complete chain from the previously certified `2875e60` through the Week 3 pilot, the audit, the interpretation corrections and closeout decisions **D-061 … D-066**. `9c0d89d` is the new certified base and the `BASE` for every subsequent bundle (D-043).

**The Week 3 conclusions Sol accepted, stated at the width they are allowed:**

* the pilot is **exploratory development evidence**, not an H1 or H2 verdict;
* D-061 fixes normalisation to the **full movement evaluation pool before masking**, and the W3 numbers are **unchanged** by it because the scored set equals that pool;
* **no second activation trunk**; the detached head stays non-decisional, and it beat its paired copy baseline in **0 of 90** member/slice comparisons;
* the pilot evidence is **18 runs and 90 member results** with immutable-attempt provenance;
* MC-dropout is an explicit stochastic prediction policy that **fails closed** on the current dropout-free `WorldModel`.

**The boundaries, which travel with the certification and are not softened by it:**

| Still not authorised | Owner |
|---|---|
| Confirmatory execution | C-008, the confirmatory runner |
| Repair-validation execution | C-008 |
| Runner hardening — `source_unit is None`, per-dataset `stream_version` | C-009 |
| Masked failure-set analysis | **C-010, required before W4 Friday** |
| MC-dropout rung 3 on the current architecture | an explicit development-stage architectural decision; `WorldModel` has no dropout |

**C-010 restated, because W4 Friday is the first cell that can violate it:** construct the `NormalisationScale` from the full movement evaluation pool **before** the failure mask exists, reuse **that same object** for the whole-pool and masked statistics, and select **one immutable attempt** explicitly rather than loading a tree.

**What is now unblocked:** Week 4 Monday's trend-test implementation, within those boundaries.

**On the review round that produced this.** Six Sol reviews across Week 3's close (deltas 27–31). Every finding was verified before anything changed, and every one stood — but two arrived at conclusions Sol had reached by a different route than the one described (D-062's rerun path, and my own account of it), and three were about **claims rather than code**: an invariance that does not hold for a vector, an enforcement a type cannot provide, and an isolation that held only on the hardware it was tested on. The code defects were cheaper to fix than the sentences were to get right.
**Plan ref:** P§9.3, P§10.3, P§13.7, P§14.2.
**Reviewed by Sol:** **certification issued.** New certified base `9c0d89d`.

### D-068 · 2026-08-17 · Change Record — the H1 trend test's reading rule, frozen before it saw data
**Change Record.** New constants in `src/bu/constants.py`: `TREND_EXPECTED_DIRECTION = "negative"`, `TREND_PASS_REQUIRES_UPPER_BOUND_BELOW = 0.0`, `TREND_BOOTSTRAP = "exact_paired_seed_block"`, `TREND_QUANTILE_METHOD = "linear"`. **Has data been seen?** The Week 3 development pilot exists and its disagreement curve is known to be non-monotone at the small end. **That is exactly why the rule was fixed by Sol in advance, and why it is recorded here before the function was applied to anything.** No confirmatory data exists.

**The rule (Sol's, adopted verbatim).** Spearman's rho between ascending dataset size and mean pairwise disagreement, over **all six** preregistered sizes. Expected direction **negative**. **Pass only when the entire 95% interval lies below zero** — containing or touching zero fails, entirely above zero is a *reversal* and fails, a constant curve or undefined coefficient fails. Individual out-of-order points carry **no separate veto** beyond their effect on rho and its interval.

**Explicitly forbidden**, because each converts an inconvenient result into a passing one: removing N=100 or N=250, smoothing the curve, switching to Kendall, or adding a separate monotonic-order rule. P§4.2 says ordinary non-monotonicity in six observed means is not itself the criterion. The N=250 peak should weaken the statistic naturally — **that is evidence, not an exception to repair**.

**The interval.** A paired seed-block bootstrap: one seed's complete six-size curve is one block, because the six sizes within a seed are nested prefixes and not independent (D-030). Resample seeds with replacement, average across selected seeds at each size, recompute rho on the six means, take the 2.5th and 97.5th percentiles. With 3 development and 5 confirmatory seeds the space is **enumerated exactly** — 3³ = 27 and 5⁵ = 3,125 ordered tuples, which reproduces the ordinary bootstrap's multinomial multiplicities by construction. **No bootstrap RNG exists**, so there is no seed to record, drift or forget, and a registered endpoint cannot differ between two runs of it. The quantile method is declared in code rather than left to a library default that has changed across numpy versions.

The point estimate is rho on the **across-seed mean curve**. Per-seed curves and per-seed rho are diagnostics and do not enter the pass rule: a "3 of 5 seeds show it" reading is the unreliable-positive Gate 2 exists to refuse.

**The partition boundary, frozen with it.** W4 gate: **development seeds only** — it is estimator selection, and using confirmatory seeds to choose whether to keep the ensemble would consume confirmatory evidence during method selection. W10 verdict: **confirmatory seeds only**. Same statistic, interval, direction and pass rule at both. The partition argument validates and labels the input and **must not change the mathematics**. Development and confirmatory seeds are **never pooled**, and the W4 coefficient is never quoted as the H1 result. Once the gate selects a rung, that choice is frozen before confirmatory execution; if the default ensemble fails and a fallback passes, H1 is recorded as **falsified for the ensemble** and the fallback becomes the predeclared secondary path.

**One thing the implementation refuses that the rule only implies.** The size grid must be exactly the six registered sizes. Without that check the grid is an argument, and a five-point statistic computed over a trimmed grid is indistinguishable from the registered one in every artefact carrying it — the "drop the awkward small end" move, arriving through a keyword rather than through a decision. Found while writing the test for it, because the first version of that test passed for the wrong reason.
**Plan ref:** P§4.2, P§10.3, P§11.3, S§W4 Mon, S§W10 Mon.
**Reviewed by Sol:** **Sol's ruling**, adopted verbatim; the grid check is mine.

### D-069 · 2026-08-17 · W4 Monday — the trend test built, and what it says about the pilot
**Decision:** `src/bu/stats/trend.py` implements D-068's rule as one function used by both stages, with 22 tests covering every clause Sol required plus the partition boundary. Applied to the **development pilot** — which is what Schedule W4 Mon asks for, and is **not** the Week 4 gate (that is Tuesday, five seeds across three configurations).

| | |
|---|---|
| rho (across-seed mean curve) | **−0.9429** |
| 95% interval | **[−0.9429, −0.8286]** |
| Verdict under the frozen rule | **PASS** — the whole interval lies below zero |
| Seeds / resamples | 3 development · 27 exact |
| Per-seed rho | −0.9429, −0.8286, −0.9429 |

**Sol's prediction held.** The N=250 peak costs exactly **one** of fifteen pairwise inversions, weakening rho from −1.0 to −0.9429 — weakened naturally, with nothing removed or smoothed, and the interval stays wholly negative.

**The limitation, which matters more than the verdict.** With three seeds the exact bootstrap has **27 resamples taking only two distinct values** — −0.9429 with multiplicity 20 and −0.8286 with multiplicity 7. So the "95% interval" here *is* the full support of the distribution: the 2.5th percentile is its minimum and the 97.5th its maximum. The interval is **coarse**, not tight, and its narrowness is a property of having three highly consistent seeds rather than evidence of precision. At five confirmatory seeds the support is 3,125 and the quantiles become meaningful. **This number is development evidence about the pipeline, not a measurement of H1**, and the same coarseness will apply to the Week 4 Tuesday gate if it too runs at three seeds — worth settling before Tuesday rather than after.
**Plan ref:** P§4.2, S§W4 Mon.
**Reviewed by Sol:** pending — the coarse-interval limitation is the thing to attack.

### D-070 · 2026-08-17 · Sol's three rulings, and the gate wrapper Tuesday needs
**Decision:** Sol certified `a84cf6c` as the W4 Monday trend-test implementation and ruled on all three open questions. All three adopted; the third is a correction to my reasoning rather than to the code.

**Ruling 1 — minimum seeds. Do not change the statistical pass rule after seeing the two-atom interval.** Distinguish instead between a *statistical result* and *gate eligibility*: the three-seed pilot satisfies the frozen directional rule and can expose behaviour, but **cannot produce an authorised gate verdict**. The requirement goes in a wrapper, not in the mathematical core, so the legitimate three-seed diagnostic keeps working. Built as `src/bu/stats/gate.py`, requiring exactly three predeclared configurations, exactly five development seeds each, all six sizes, one `trend_test` per configuration, and no missing, substituted or additional seeds.

**Aggregation, fixed before anything runs: rung 0 passes only if all three configurations pass.** No majority vote, no pooled curve. All three coefficients and intervals are reported. If one fails, the rung fails and the ladder begins — *this is a reliability gate, and configuration sensitivity is itself a failure of reliability.* The rung and estimator name travel with the verdict, and a pass at rung 3 or 4 prints that H1 is **falsified for ensembles** (P§11.3).

**The three configurations, predeclared with their exact identities** — shape-causal, confound 0, one per layout, so the causal rule and confounding are held fixed and only the layout varies. A configuration spans **six units**, not one, because `n_transitions` is an identity field and the curve runs across them:

| layout | config_ids, N = 100 … 5000 |
|---|---|
| uniform | `ea25c6151f4d` `0d36ad29332c` `320bc9ee4f21` `daaba764439a` `00608aa75f91` `d9c4c70b4678` |
| clustered | `3daf1dcda5ac` `802912059512` `a91c2fa273e6` `970c22a075e6` `92ff27a2439d` `f35fdc40f563` |
| sparse | `523dc25c40fa` `8b9b5956a71b` `463729da740b` `2390f6786b20` `14d78f124c26` `d11d4bbd54af` |

They are **frozen as golden values with a test that regenerates them**. Derived at run time, a change to identity canonicalisation would silently redirect the gate at different units while the record still named the old ones — the D-016 lesson. `GATE_CAUSAL_ATTRIBUTE`, `GATE_CONFOUND_RATE`, `GATE_LAYOUTS`, `GATE_SEEDS` and `GATE_AGGREGATION` are in `constants.py`, because they are preregistered choices and that file is the preregistration.

**Ruling 2 — keep the exact six-size grid refusal.** There is no legitimate subset caller for the registered statistic. A future exploratory analysis over fewer sizes must be a **separately named descriptive function** returning neither a `TrendResult` nor a registered verdict. Documented in the module rather than left as a guard whose reason a later reader must reconstruct.

**Ruling 3 — a correction to my explanation, not to the behaviour.** Undefined replicates still fail closed and are never dropped: dropping them would condition the bootstrap distribution on the statistic being defined and could **manufacture a directional interval from the survivors**. But my stated reason was wrong. I had called a constant curve "the strongest possible evidence against a trend"; Sol pointed out it can equally arise through **cancellation between opposing non-constant seed curves**, which says nothing about direction. The reason now reads: *at least one paired seed-block resample produces an undefined rank correlation, so the registered bootstrap interval is undefined and the reliability result fails closed.*

A test now constructs exactly that case — three non-constant curves at slopes −0.1, −0.3 and +0.2, where the resample {0, 0, 2} cancels to flat. **The point estimate is a perfect −1.0 and the result still fails**, which is precisely why dropping the undefined replicates would have been dangerous: the survivors would have formed a tidy negative interval.
**Plan ref:** P§4.2, P§11.3, S§W4 Tue–Thu.
**Reviewed by Sol:** all three rulings Sol's; `a84cf6c` certified. The wrapper is pending review before Tuesday runs.

### D-071 · 2026-08-18 · Sol's two blockers on the gate wrapper — the verdict is now bound to its evidence, and the ladder is frozen
**Decision:** Sol reviewed the wrapper at `311a23c`, accepted the mathematics, the eligibility rule, the aggregation rule and the cancellation regression test, and **refused to certify it as the executable Tuesday gate** on two blockers. Both verified before anything changed. Both real; the first is **worse than stated**, and there is a third consequence neither of us had named.

**Blocker 1 — the evidence was never bound to the frozen identities.** `reliability_gate()` accepted bare curves indexed only by layout, seed and size, then attached the eighteen golden `config_id`s to the result without checking that those curves came from those configurations. Reproduced before fixing, and the reproduction is sharper than the finding: **five lines of invented floats returned `passed=True`, carrying all eighteen golden ids, with no model ever fitted.** The verdict was byte-indistinguishable in every artefact from an authorised one. Not "could receive an apparently authorised verdict" — did, and passed.

**The consequence neither of us had named: rungs 0, 1 and 2 are indistinguishable by every identity in this project.** `ensemble_size` and `bootstrap_ratio` are deliberately outside `UNIT_IDENTITY_FIELDS`, so a rung-1 run of a cell has the **same `config_id`, the same `run_id` and the same `fit_id`** as the rung-0 run it replaces — verified directly. So the check Sol asked for, "actual config_id against the corresponding golden ID", is **necessary but not sufficient**: it passes unchanged for rung-1 evidence presented as rung 0. The rung is verifiable only against the training parameters recorded in the run record, which `Config.to_dict()` does carry. `GateEvidence._verify_cell` therefore checks both, and a test asserts the identity collapse so that if the rungs ever *become* identity-bearing, the provenance story is revisited rather than silently changing.

A second consequence, recorded for Wednesday: because `run_id` is identical across rungs and `write_run_record` refuses to overwrite, a rung-1 run **cannot** be written into the same tree as rung 0. That is fail-closed and correct, but it means the ladder needs one immutable attempt directory per rung, settled before Wednesday rather than discovered by a `FileExistsError` mid-run.

**Built:** `GateEvidence` / `EvidenceCell`. The public `reliability_gate(evidence, *, rung)` verifies every cell before computing anything — layout, size, development seed, `config_id` against the golden value, `run_id` against the identity its own fields imply, stage, partition, the rung's training specification, and **one attempt and one commit** across all ninety cells, with no cell missing, duplicated or unregistered. The curve-only path is now the private `_gate_from_curves`, reachable only through it; a raw dict is refused with an explicit `TypeError` rather than an incidental `AttributeError`, because an accidental runtime error is not an invariant. `GateEvidence.from_attempt()` reads one immutable attempt directory and **fails closed on any missing field** — defaulting one would manufacture exactly the provenance the type exists to verify. It refuses a dirty tree, and it correctly refuses the W3 pilot's own manifest, which predates the required fields.

**Blocker 2 — rung identity could contradict the recorded estimator.** `reliability_gate(curves, rung=0, estimator="mc_dropout")` was accepted and produced a record claiming rung 0 while naming a rung-3 estimator. The free-form override is **removed**: the estimator and every training parameter now come from a frozen `RungSpec` selected **solely by rung**. The property tested is not that the argument is gone but that no serialised claim about the estimator is load-bearing anywhere — a tampered `estimator` field in a saved record does not survive `recompute()`.

**Raw curves are recorded (Sol's answer 2), and the necessity was verified.** `TrendResult` keeps `mean_curve` and `per_seed_rho`, and the 5×6 matrix is recoverable from neither, so the exact paired bootstrap genuinely cannot be rebuilt from a saved verdict without them. The record now carries all ninety raw cells with their source run and config ids, the derived mean curve, each configuration's rho, exact interval and verdict, the aggregate verdict, the rung specification and the attempt/commit provenance. `recompute(row)` re-runs the entire path — verification included — from the record alone.

**Change Record — the fallback ladder, frozen before rung 0 runs.** Sol's answer 3: freeze the rung parameters before observing the rung-0 result, otherwise Wednesday chooses the repair after having watched Tuesday fail. Cumulative, each rung changing one parameter:

| rung | estimator | ensemble_size | bootstrap_ratio | granularity |
|---|---|---|---|---|
| 0 | ensemble | 5 | 1.0 | episode |
| 1 | ensemble | 10 | 1.0 | episode |
| 2 | episode **subbagging** | 10 | **0.5** | episode |
| 3 | mc_dropout | *deliberately not frozen* | | |
| 4 | last_layer_laplace | *deliberately not frozen* | | |

**Data seen: none.** Zero GPU-hours, no gate cell executed. Rungs 3 and 4 are secondary estimators whose method-specific parameters are frozen before either is executed, not now; `RungSpec.for_rung(3)` raises. Reaching rung 3 still means H1 is falsified for ensembles (P§11.3), and `WorldModel` has no dropout, so it stays an architectural decision rather than a run (D-062).

**Pre-data semantic correction to P§11.3 (rung 2).** The plan says to raise inter-member diversity by *increasing* the bootstrap ratio. In the implemented API `bootstrap_ratio` is with-replacement draws over episode count, so expected unique-pool coverage is 1 − e^−ratio — **measured 0.395 at 0.5, 0.635 at 1.0, 0.866 at 2.0**. Raising the ratio makes members cover more of the same pool and therefore **more alike**, the opposite of the plan's stated intent. Rung 2 subbags at 0.5, which is the parameter move that actually implements what the plan asks for. Recorded as a correction rather than applied silently, and asserted by a test so that a future edit "restoring" the literal wording fails.

**Verified, not assumed:** every claim above was reproduced before the change — the fabricated-curve PASS, the rung/estimator contradiction, the identity collapse across rungs, the coverage arithmetic, and the non-recoverability of the raw matrix from `TrendResult`.
**Tests:** 483 → **507 passing**, 2 skipped. All five regressions Sol required, plus the rung-identity collapse, the pilot-manifest refusal, the dirty-tree refusal and the recomputability round trip.
**Plan ref:** P§11.3, S§W4 Tue–Thu.
**Reviewed by Sol:** blockers Sol's, 2026-08-18. `311a23c` explicitly **not** certified; certified base remains `a84cf6c`. **No Tuesday compute until this is reviewed.**

### D-072 · 2026-08-18 · The evidence contract — the trust boundary reaches execution, and the W4 runner that emits it
**Decision:** Sol reviewed delta 35, accepted the frozen rungs, the subbagging correction, the removal of the estimator override, the 90-cell grid, the raw-curve serialisation and recomputation, every refusal added in D-071, and the rung-identity discovery — and **again refused to certify** (`867145d`), on one finding: the binding was to *claims*, not to execution.

**Verified first, and it reproduces exactly as Sol describes.** `from_attempt()` read flattened manifest fields and checked only that they agreed with one another. A fabricated manifest carrying the correct 90 identities, the correct rung parameters and invented floats **passed and returned PASS**. The five-line bare-curve attack of D-071 had become a ninety-entry manifest attack; the boundary had moved and never reached the artefacts.

**Ruling 1 — derive from the canonical config; check the whole training configuration.** Each run entry now carries the complete `Config.to_dict()`. The gate reconstructs it with `Config.from_dict()`, derives `config_id`, `run_id`, `unit_id`, stage, seed, layout and size from *that*, and refuses any independently-supplied flattened value that contradicts it. The **complete** `TrainConfig` is compared against the rung's frozen specification — Sol's point that `lr`, `batch_size`, `max_epochs` and `patience` were unchecked was correct, and all four are now pinned in `RUNG_SPECS` rather than inherited from `TrainConfig`'s defaults, so moving a default cannot silently move what the ladder means. A test asserts `RUNG_TRAIN_FIELDS` covers `TrainConfig` exhaustively, so a field added later cannot go unchecked. *(Sol's list also named validation fraction; `val_fraction` was removed in the Week 3 audit under D-052, so there is no such knob. Reported rather than silently skipped.)*

**The gap in the ruling as stated: `granularity` is not a `Config` field.** It is a `train_ensemble` argument, so it cannot be derived from the canonical config at all and would have remained an unverifiable claim. The runner now writes it into the run record's `extra` at start, and the gate cross-checks the manifest against that record — the same shape of correction as D-071's, where implementing only what was described would have left a hole.

**The manifest is now cross-checked against artefacts written at training time.** `records/<run_id>/run.json` is written by `write_run_record` when the run starts and `metrics.jsonl` gains a line per member as each is fitted. The gate verifies both digests, requires the record's `config` to equal the manifest's, requires the recorded `granularity` to match, and **counts members from the metric stream** rather than believing the manifest's count. Every listed artefact's SHA-256 is checked against the file. Each `mean_disagreement` is bound to a row in `rows.json` by index and digest, and must reproduce from it.

**Ruling 2 — attempt identity, and a defect in my first derivation.** Sol: "Do not use the bare string `attempt-001` as the evidence identity. Two different directories can both be named `attempt-001`." I first derived `w4-gate-r{rung}-{spec_hash}-{directory name}` — and building two attempts proved that derivation **produces the same id for both**, which is the very collision the ruling names. The identity is now derived from the *content*: rung, full rung-spec hash, and a digest of the run records themselves, which carry `started_utc`. Two executions cannot collide, and the gate recomputes the id from the cells rather than accepting it. The structural checks run first, so a missing or duplicated cell reports as that rather than as the identity mismatch it also causes.

**Ruling 3 — a versioned evidence contract.** `EVIDENCE_CONTRACT_VERSION = 1`. `REQUIRED_MANIFEST_FIELDS` and `REQUIRED_RUN_FIELDS` replace the old flattened minimum; an unrecognised version is refused rather than read optimistically, because an older manifest is missing exactly the fields that make a verdict checkable. The W3 pilot's own manifest is correctly refused, and there is a test asserting it — it is real evidence sitting on the uniform gate configuration, so it is exactly what would be pointed at by mistake.

**Built: `src/bu/experiments/w4_gate.py`**, the runner, which emits the contract and decides nothing. It refuses confirmatory seeds and unfrozen rungs before doing any work, writes one immutable attempt under `runs/w4_gate/rung-NN-<spec_hash>/attempt-NNN/` (discharging **C-011** at the granularity Sol asked for), builds the `NormalisationScale` from the full movement evaluation pool **before any mask** and reuses that object across all six sizes, and digests the evaluation pool so that a curve measured on six different pools is refused rather than read as a trend. **C-010 is partly discharged**: the scale-before-mask and reuse invariants are implemented and tested on the real path; the *masked* call site is still W4 Friday's work.

**Measured, not asserted:** a smoke run of 10 fits took 3.5 s on CPU, and reproduced the W3 pilot's uniform/N=100/seed-0 disagreement of 0.685593 exactly. Extrapolating from the pilot's larger sizes, the full 450-fit rung 0 is minutes on CPU, not the hour previously estimated.
**Tests:** 507 → **532 passing**, 2 skipped. All seven regressions Sol required, plus the attempt-collision test that forced the identity redesign, the granularity cross-check, the members-never-fitted check, and a real runner integration test for C-010's invariant. One further defect found by probing rather than by review: a missing `rows.json` raised an incidental `FileNotFoundError` instead of refusing — an accidental runtime error is not an invariant, and it is now an explicit refusal.
**Data seen: none.** Zero GPU-hours. No gate cell executed; the only compute spent was 10 CPU fits smoke-testing the machinery, written to a scratch directory and never to `runs/`.
**Plan ref:** P§11.3, P§13.7, S§W4 Tue–Thu.
**Reviewed by Sol:** finding Sol's, 2026-08-18. `867145d` **not** certified; certified base remains `a84cf6c`. **No Tuesday compute until the runner and contract are reviewed.**

### D-073 · 2026-08-18 · The closeout — six advertised checks that were not being performed
**Decision:** Sol reviewed delta 36 and **accepted the architecture**: canonical `Config` reconstruction as the source of identity, complete `TrainConfig` freezing, the `val_fraction` correction, granularity attested outside `Config`, run and member records reaching the execution boundary, source-row binding, evaluation-pool consistency, content-derived attempt identity, and the runner/verdict separation. `4e92fda` is accepted **in design** but still not certified, because several fields the contract advertised were decorative. All six items verified present before fixing.

**Answers to the three questions, and what they settle.**

- **A digested summary row is sufficient for Tuesday.** Per-transition exports are not required to authorise the gate — the registered verdict is recomputable from the 90 raw disagreement cells, each bound to a runner-produced summary row. They stay optional diagnostics. *No work; the boundary is where it should be.*
- **Weight digests are not required, and the reasoning matters more than the answer.** A checkpoint digest proves a weight file did not change; it does **not** prove the weights were trained under the declared configuration. Requiring 450 checkpoints would add storage without closing the "runner deliberately trained something else" attack. The project's trust model protects against **accidental substitution, stale evidence, mixed executions and post-run mutation** — not a malicious author fabricating every layer consistently. Clean commit + canonical configuration + training-time run record + per-member completion records is the standard. *This is now the written answer to the question I raised in delta 36; the gap is real and deliberately out of scope.*
- **`EVIDENCE_CONTRACT_VERSION` is not a preregistered scientific quantity.** It is a schema compatibility version, and `constants.py` is the preregistration — everything in it is frozen before data, which is the *opposite* of the property a schema version needs. Moved out, together with `MANIFEST_VERSION` and a newly separated `METRIC_SCHEMA_VERSION`, into `bu.stats.gate`: the reader is what must refuse an unknown version, so the version belongs with the reader.

**The six closeout items, each a field the contract required to be present without ever comparing it.**

1. **Manifest version and frozen spec.** `manifest_version` was required and never compared; nor were `rung` or `rung_spec`. All four now checked, and the optional `spec=` argument can no longer make a contradictory manifest rung decorative — naming a rung the evidence is not now refuses.
2. **Training-time attestations.** The run record's `extra` carries five — granularity, rung, rung-spec hash, evaluation-pool digest and cell — and only granularity was checked, so a manifest could **borrow an honest run record while changing the pool it claimed to evaluate on, or the obligation the run discharged.** All five are now cross-checked, and a missing one fails closed.
3. **Normalisation bound to the source row.** The old check established only that the manifest reported one scale across the six sizes — not that it was the scale the bound row was computed under. The scale already travels inside the summary row, so exact equality is now required against it.
4. **Attempt identity over completed evidence.** Run records are written *before* training, so hashing them alone meant two evidence sets with identical copied start records but different member streams or rows would share an identity. The identity now hashes run-record, member-record, row and evaluation-pool digests per run — all four already travel in `EvidenceCell`, so it stays recomputable from the record alone.
5. **Declared counts and versions.** `n_member_records` is verified against the streams; each run's `member_count` against its own stream; `metric_schema_version` against a separately defined constant rather than `config.SCHEMA_VERSION`, which evolves independently; and each artefact's recorded byte count against its actual size.
6. **Dirty execution refused before training, not after.** `run()` recorded a dirty tree, performed all the fits, and the verifier then refused the result — 450 fits spent producing evidence that could never be used. It now fails immediately after `git_state()`, before the attempt directory exists. An explicit `allow_dirty` exists for tests and **cannot** make dirty evidence usable: the manifest still records it and the verifier still refuses, so the safety property stays with the reader.

**Ordering, twice.** The identity check now runs *after* the structural and per-run checks in both `verify()` and `from_attempt()`. A truncated metric stream also changes the attempt identity, so checking identity first reported an identity mismatch and hid the actual defect.

**One test of my own was a tautology.** `assert METRIC_SCHEMA_VERSION is not SCHEMA_VERSION or True` cannot fail — the D-055 failure mode, written into the very delta where I had described avoiding it. Replaced with the property: move the gate's version and watch the refusal move with it. The two constants are equal today, which is exactly why comparing the numbers would have asserted nothing.
**Tests:** 532 → **548 passing**, 2 skipped.
**Data seen: none.** Zero GPU-hours; no gate cell executed.
**Plan ref:** P§11.3, S§W4 Tue.
**Reviewed by Sol:** items Sol's, 2026-08-18. Sol's condition: if the micro-closeout passes, **rung-0 compute can begin immediately, on CPU**.

### D-074 · 2026-08-18 · W4 Tuesday — rung 0 passes, and what the interval actually is
**Decision:** Sol **certified `2efad258`** as the Week 4 Tuesday reliability-gate implementation and evidence contract, subsuming the three uncertified intermediate commits, and authorised rung-0 execution on CPU at the registered defaults. Run executed and **rung 0 PASSES**. Per Sol's instruction the ladder **stops**: rungs 1 and 2 are not run.

**Pre-flight, as Sol required:** tree clean, HEAD at `2efad258af7638b2657c44bb80a7e753743cfa03`, `git_state()` reporting `dirty: False`, no `allow_dirty`.

| | |
|---|---|
| attempt | `w4-gate-r00-93bec8081d97-4f58c24f213c` |
| path | `runs/w4_gate/rung-00-93bec8081d97/attempt-001/` |
| commit | `2efad258af7638b2657c44bb80a7e753743cfa03` |
| rung spec hash | `93bec8081d97` |
| manifest sha256 | `0fee9444a247…` |
| verdict sha256 | `c0d92221b03c…` |
| shape | 3 configurations × 5 development seeds × 6 sizes = 90 ensembles / **450 fits** |
| runtime | **4 m 52 s** on CPU, 0.65 s per fit |
| post-run suite | **548 passing, 2 skipped** |
| `recompute()` | **exact equality** with the serialised verdict |

**Verdict — rung 0 (ensemble): PASS, all three configurations.**

| configuration | rho | 95% interval | verdict |
|---|---|---|---|
| uniform | −0.9429 | [−0.9429, −0.9429] | PASS |
| clustered | −0.9429 | [−0.9429, −0.8286] | PASS |
| sparse | −0.9429 | [−0.9429, −0.9429] | PASS |

**The three rhos are identical, and that is a property of the statistic, not a coincidence.** Spearman reads ranks only, and all three mean curves carry the *same rank pattern*: monotone falling except a peak at N=250. −0.9429 is exactly one adjacent transposition from perfect reversal — the N=250 peak costing one of fifteen pairwise inversions, precisely as D-069 found at three seeds and as Sol predicted before any of it ran.

**What the interval is, said properly.** Two of the three intervals are a single point, and that must not be read as zero uncertainty. The exact paired bootstrap is **discrete with very few atoms** — the enumerated distribution over all 3,125 resamples:

| configuration | −0.9429 | −0.8286 | −0.7714 | distinct values |
|---|---|---|---|---|
| uniform | 98.37% | 1.63% | — | 2 |
| clustered | 81.86% | 17.82% | 0.32% | 3 |
| sparse | 97.86% | 2.14% | — | 2 |

Uniform and sparse are degenerate **only just**: their second atom sits at 1.63% and 2.14% against the 2.5% quantile threshold. Sparse is within 0.36 percentage points of its upper bound flipping to −0.8286. **The verdict does not depend on this at all** — every atom in every configuration is far below zero, so the registered rule passes under any of them — but the reported *width* does, and a reader taking [−0.9429, −0.9429] as a precise estimate would be wrong. This is the same coarseness D-069 reported at three seeds; five seeds enlarge the support from 27 to 3,125 without adding many distinct values, because the statistic is a rank correlation over six points.

**The N=250 peak reproduces almost everywhere.** In **14 of the 15** seed-configuration curves, disagreement peaks at N=250 rather than falling monotonically. The exception is **clustered seed 4**, whose peak is at N=500 with N=250 falling *below* N=100 — a different shape, kept and reported rather than smoothed. Disagreement is therefore **not** monotone in dataset size; the gate passes because Spearman tolerates exactly one inversion. This is a reliability result about the *estimator*, not H1's verdict, which is W10 on confirmatory seeds.

**Two housekeeping corrections.** The verdict was first serialised *into* the attempt directory, which mutates evidence after its manifest is written; it now lives beside the attempt as `verdict-attempt-001.json`, and the attempt re-verifies unchanged. And the whole attempt — manifest, rows, all 90 run records and 450 metric streams, 1.2 MB — is now **tracked in git**, a deliberate widening of the pilot's manifest-and-rows-only exception: the contract's trust boundary *is* those digests, and untracked, a fresh clone could read every claim and verify none of them.

**A measurement error of mine, corrected.** I told Sol in delta 36 that rung 0 would be "minutes on CPU", then corrected that to ~50 minutes by scaling the W3 pilot's 10-minute/90-fit rate. The actual time was 4 m 52 s: **the original estimate was right and the correction was wrong.** The pilot is ~10× slower per fit because it also computes per-transition exports, per-member activation reports, spread diagnostics and figures. I scaled a rate without asking what it was a rate *of*.
**Data seen:** development seeds only (0–4), permanently excluded from confirmatory results, threshold calibration, repair acceptance and the critic (D-034).
**Plan ref:** P§11.3, S§W4 Tue.
**Reviewed by Sol:** `2efad258` certified 2026-08-18 and authorised for execution. The verdict itself awaits review in delta 38.

### D-075 · 2026-08-18 · Sol's rulings on the rung-0 result, and the wording the thesis must carry
**Decision:** Sol **certified the rung-0 result** and `ca545ed` as the stored Week 4 Tuesday result, which becomes the next review base. The gate passes at rung 0 on all three predeclared configurations independently; the ladder is correctly stopped and rungs 1 and 2 are not to be run. Three rulings, all adopted.

**Ruling 1 — report the point intervals exactly, with the atom structure beside them.** Do **not** widen or replace the registered intervals after seeing their discreteness: they are the correct exact percentile intervals under the frozen procedure, and changing them after seeing the data is precisely what preregistration exists to prevent. But `[−0.9429, −0.9429]` **must never appear without its explanation**. Sol's wording, to go into the thesis results text verbatim or near-verbatim:

> "Exact paired seed-block bootstrap percentile intervals were computed over all 3,125 resamples. Because Spearman correlation over six dataset sizes has highly discrete support, the bootstrap distributions contained only two or three distinct values. A zero-width percentile interval therefore reflects quantile discreteness, not zero sampling uncertainty."

The atom/mass table goes in the results text, a footnote or the supplement — it is **necessary for honest interpretation**, not optional colour. The registered conclusion is unchanged because every atom in every configuration is strictly negative: the pass does not depend on which atom contains the 97.5th percentile.

**Ruling 2 — do not investigate clustered seed 4 now.** Keep and report the curve exactly as observed. The evidence checks found no integrity failure, the paired procedure already includes the seed, and the all-three gate passes with it in. Targeted investigation now would be **post-result exploration** and could invite a model change on the strength of one development curve. **Do not** add seeds, smooth the curve, rerun the cell, or alter the estimator. Record it descriptively — 14 of 15 curves peak at N=250; clustered seed 4 peaks at N=500 with N=250 below N=100; the across-seed clustered trend still passes — and leave substantive confirmation to W10's untouched confirmatory seeds. If the shape recurs there, discuss it as configuration/seed heterogeneity.

**Ruling 3 — tracking the 1.2 MB of evidence in git is correct.** The verifier depends on the run records and member streams; tracking only their digests while discarding the files would leave a fresh checkout able to read every claim and verify none. Keep tracked: manifest, rows, 90 run records, 450 member metric records, serialised verdict. **Do not** add checkpoints or per-transition exports solely for this gate. Keeping `runs/` bodies out of ordinary bundle diffs is acceptable because the omission is explicit, every omitted file is listed with its digest, the files exist in the certified commit, the compact verdict is in the delta, and this certification makes `ca545ed` the base so later bundles will not carry the evidence diff again.

**Housekeeping accepted:** moving the verdict beside the attempt was correct — an attempt must contain only the evidence its manifest covers, and derived verdicts belong outside it. The runtime correction is accepted: report the measured **4 m 52 s** CPU runtime and state that the W3 pilot was **not a comparable per-fit workload**, because it also wrote per-transition exports, per-member activation reports, spread diagnostics and figures.

**W4 Tuesday is complete.** Proceed to the next scheduled work item without running fallback estimators and without a special clustered-seed-4 investigation.
**Plan ref:** P§11.3, S§W4 Tue.
**Reviewed by Sol:** all three rulings Sol's, 2026-08-18. `ca545ed` certified.

### D-076 · 2026-08-18 · C-010 built — the masked call site, and a reproducibility defect found while proving it neutral
**Decision:** C-010 is discharged. `ScaledEvaluation` (in `models/uncertainty.py`) is the call site D-064 said the rule needed, and `select_attempt()` is the explicit single-attempt selection. Neither required a new scientific decision: D-061 already ruled the rule, and this is its enforcement.

**Why a type and not a convention.** D-064 was explicit that `NormalisationScale` *cannot* make a subset-derived scale impossible — the constructor is public and `from_evaluation_pool` accepts whatever tensor it is handed. So the guarantee is structural instead: `from_pool` is the only constructor and **takes no mask**, so the scale is built before the object is capable of receiving one; `masked()` reuses `self.scale`, the identical object, and there is no parameter by which a caller could supply another. There is deliberately no `scale=None` convenience on this path, and a test asserts that passing one is a `TypeError`.

**The invariant is tested as load-bearing, not merely present.** One test computes the registered masked summary and the subset-scaled one and asserts the H2 ratio **differs** — if both choices ever gave the same answer, the rule would be doing no work and should be revisited rather than quietly kept. `masked()` also refuses an empty mask (a mean over nothing is nan, and a silently empty failure set is how nan reaches a registered endpoint), a wrong-length mask, and an index tensor in place of a boolean — a wrong-length index tensor selects the wrong rows without erroring, a wrong-length boolean cannot.

**`select_attempt()` refuses to guess.** Given a rung directory holding more than one attempt it names them and requires a choice. There is no "latest": a second attempt exists precisely because something was wrong with the first, and sort order would be a guess presented as a default.

**The runner now goes through this path**, and the refactor was proved numerically neutral against the certified evidence rather than assumed to be — which is how the following was found.

**A reproducibility defect, found by probing (not review, not a test failure).** Re-running two certified cells through the refactored path reproduced N=100 **exactly** and N=250 **not**: mean disagreement 0.863375 → 0.864995, a 0.19% move. The refactor was not the cause. The cause is **thread count** — the certified run used `--threads 8`, the comparison run the default 4, and different thread counts change the order of floating-point reductions. At N=100 the difference happened to vanish; at N=250 it did not. Re-running at 8 threads reproduced both cells exactly, confirming the refactor is neutral and the threading is the variable.

**Nothing recorded the thread count.** The certified attempt was reproducible only by someone who already knew how it had been invoked — a gap in an evidence contract whose entire purpose is that a verdict be checkable by someone who was not there. `torch_threading()` now records `num_threads` and `num_interop_threads` into both the run record's `extra` and the manifest.

**Recorded additively, and deliberately not enforced.** It is **not** in `REQUIRED_RUN_FIELDS`, because making it required would immediately invalidate the certified `attempt-001`, which does not carry it. Whether reproducibility metadata becomes a required contract field — and whether the certified attempt must therefore be regenerated — is **Sol's call, not mine**, and is the open question in delta 40. The certified attempt still verifies unchanged, and a regression test asserts it will keep doing so: if a later change to the reader breaks the stored W4 Tuesday result, that needs a Change Record rather than a test update.

**Not done, deliberately:** no characterisation of whether the *verdict* is robust to thread count. That would mean re-running the cell, and Sol's D-075 ruling against post-result reruns was written for a reason. The verdict stands on the stored evidence, which verifies; whether it reproduces bit-for-bit at another thread count is a question I am raising rather than answering.
**Tests:** 548 → **563 passing**, 2 skipped. Includes a regression that the certified rung-0 attempt still loads, verifies and returns PASS at rho ≈ −0.9429 on all three configurations.
**Data seen:** none beyond the already-certified W4 Tue evidence. Zero GPU-hours; the probe cost 15 CPU fits in a scratch directory.
**Plan ref:** P§10.1, P§10.3, S§W4 Fri.
**Reviewed by Sol:** not yet — delta 40. W4 Friday must not run before it is.

### D-077 · 2026-08-18 · C-009 — the pool guard's two opt-outs closed
**Decision:** `assert_pools_match()` now refuses a dataset whose `source_unit` is **unrecorded**, and one whose `stream_version` differs from the running registry. Both were Sol's, filed as C-009 on 2026-08-16 and marked non-blocking because `collect_pools`' own output already satisfied them.

**Why "already satisfied" was not a reason to leave them.** The clause read `if dataset.source_unit is not None and dataset.source_unit != unit`, which makes the strongest check in the guard **opt-out**: a dataset that never recorded where it came from skipped the one clause that catches a pool borrowed from another condition. Absent provenance is not matching provenance. The same shape as D-071's flattened fields — a check that passes because the thing it checks is missing.

**Stream version matters more than it looks.** D-052 bumped `STREAM_VERSION` *because the pools themselves changed*: validation used to be carved from a nested training prefix, so a "100-transition" condition trained on 50. A pool generated under the previous registry is a different experiment wearing this one's identity, and nothing compared the two.

**Found by the suite being silent.** Adding both refusals broke **no existing test**, which is the point: nothing in 563 tests exercised either path, so both were unguarded and untested at once. Three regressions added, including one asserting well-formed pools still pass — a guard that refuses everything is not a guard.
**Tests:** 563 → **565 passing**, 2 skipped. (A fourth test was added and one existing helper renamed: my new `_pools` helper shadowed a module-level `_pools` defined 600 lines above, breaking nine unrelated tests until renamed. Caught immediately by the suite.)
**Plan ref:** hardens D-052, D-057.
**Reviewed by Sol:** item is Sol's (C-009); the implementation is in delta 40.

### D-078 · 2026-08-18 · C-006 built, and the MDE does not clear the five-point margin
**Decision:** C-006 is built (`src/bu/stats/mde.py`, `tests/test_mde.py`), to D-044's specification: the actual group sizes and class membership, group-preserving held-out draws, unit weights, paired predictions, within-group correlation, and the balanced-accuracy **difference** with a group-bootstrap interval. There is deliberately **no `n_eff()`** — D-044 ruled that naming one would invite the misuse that produced the first wrong number, so the analytic effective sample sizes appear only in the tests, as the validation.

**Both validations D-044 required pass.** At ICC = 0 the simulated SD of the difference matches the independent-units analytic result; at ICC = 1 it matches the unit-weighted boundary, and a separate test asserts that boundary is **75.00 / 72.58** — recomputed from the live design matrix, so if the design ever changes, every power statement derived from it fails loudly rather than going stale. The group-bootstrap interval is separately checked for calibration, and the false-positive rate at zero effect is under 10%: a bootstrap that understated the spread would report power the design does not have.

**A clarification worth recording, because I misread it first.** D-044's "D = 0" and "D = 1" are the **classes**, not design effects. Class 0 is 150 units in 125 comparison groups (120 singletons and five of size six), Σm² = 300, so n_eff at ICC = 1 is 150²/300 = 75.00. Class 1 is 150 units in 115 groups (105 singletons, five of size four, five of size five), Σm² = 310, giving 72.58. Verified against the enumerator. **No comparison group spans both classes**, so a group-preserving partition is automatically class-preserving — which the splitter (C-005) may rely on.

**THE RESULT: the design does not clear the five-point margin, and it is not close.** At the scheduled held-out counts (S§W5's N = 20/40/60/80), the minimum detectable balanced-accuracy difference at 80% power is:

| held out | min(N₀,N₁) | ICC 0 | ICC 0.25 | ICC 0.5 | ICC 0.75 | ICC 1 |
|---|---|---|---|---|---|---|
| 20 | 10 | 28 | 28 | 28 | 28 | 28 |
| 41 | 20 | 23 | 24 | 24 | 25 | 26 |
| 60 | 30 | 20 | 21 | 21 | 21 | 22 |
| 80 | 40 | 18 | 19 | 20 | 21 | 22 |

**Sample size is the driver, not correlation.** Even at ICC = 0 — no within-group dependence at all — the MDE at 80 held-out units is **18 points against a 5-point margin**. The conclusion therefore does not rest on the ICC assumption, which is the parameter least knowable before data.

**Checked against hand arithmetic rather than trusted.** Independent units, 40 per class, baseline 0.70: SD of the difference is 0.0705, so the 80%-power MDE is 2.802 × 0.0705 = **19.8 points**, against 19.0 simulated. At 300 held out the analytic gives 9.8 against 11.0 simulated at ICC 0.25. The simulation is measuring what the formula measures.

**Every lever was tested, and none rescues it.** Pairing between the critic and the fitted baseline is the largest: at 80 held out it moves the MDE from 19.0 (independent) to 11.5 at correlation 0.9 and 8.0 at 0.99 — still above 5. Higher baseline accuracy helps slightly (11.5 → 8.0 going from 0.70 to 0.90). Holding out **all 300 units** — impossible, as it leaves the critic no training data — gives 10.5 unpaired and 6.0 at pairing 0.9.

**What would clear it**, with the design's shape preserved:

| held out | pairing 0 | pairing 0.5 | pairing 0.9 |
|---|---|---|---|
| 150 | 14 | 12 | 8 |
| 300 | 11 | 9 | 6 |
| 600 | 8 | 7 | **5** |
| 1200 | 6 | **5** | 3 |

Clearing five points on the conservative (unpaired) assumption needs on the order of **1,500–2,000 held-out units**, against the 60–80 the schedule anticipates and the 300 total the design enumerates — a roughly twenty-fold gap in held-out count.

**This is exactly what P§10.7 and Gate 1 exist to find, and it is found in Week 4 rather than Week 15.** S§W5: *"If the MDE does not clear five percentage points, raise the configuration count now. It costs Kaggle time, not your time. Discovering this in Week 15 costs the thesis."* P§14.3's remedy is configuration count — **never seeds**, withdrawn as a lever in Plan v1.2, and never the reliability protocol.

**I am not acting on it.** Raising the configuration count is a scope and compute decision that belongs to the student and to Sol, and it interacts with the 8,197-fit budget and the ~120 GPU-hour escalation trigger. Two things also need adversarial review before anyone acts: whether the simulated estimand is the one H3's test will actually use, and whether the plan's framing — MDE as a difference-detection quantity compared against an *equivalence* margin — is the right comparison at all.
**Stated assumptions, because the answer depends on them:** power 0.80 (P§10.7, verbatim); **α = 0.05 two-sided, which the plan does not state** — chosen for consistency with the 95% intervals used in P§7.3 and D-068, and recorded as DEV-008; baseline accuracy 0.70 unless swept; system pairing 0 as the conservative default; the ICC parameter is a **latent** correlation, so the induced binary correlation is lower in between the two validated endpoints.
**Tests:** 566 → **581 passing**, 2 skipped.
**Data seen:** none. This is a simulation over the design matrix; no run records were read and no compute was spent on fits.
**Plan ref:** P§4.2, P§10.4, P§10.7, P§14.3, S§W5 Thu. Implements C-006 as specified by D-044.
**Reviewed by Sol:** **not yet, and this one must be** — delta 41.

### D-079 · 2026-08-18 · W5 Tue and Wed — the acceptance test and its permutation null
**Decision:** Built `src/bu/stats/acceptance.py`: the repair acceptance test (P§7.3, S§W5 Tue) and the permutation null that calibrates it (S§W5 Wed). Both validated on **synthetic data with a known truth**, which is exactly what S§W5 Tue's "done when" asks for — no run records, no compute, nothing frozen. Neither needed a Sol ruling: P§7.3 specifies the test and §2 already carries it as a frozen constant.

**Three conditions, all required, each shown able to refuse on its own.** A negative fixed effect; a 95% interval excluding zero; and a reduction clearing the **20% minimum practical effect**. A 35% simulated reduction is accepted and its size recovered to within 5 points. A 5% reduction over 3,200 transitions — statistically unmissable, interval comfortably excluding zero — is **refused**, which is what condition three is for: it stops a large enough sample manufacturing a "successful" repair out of a negligible one. A repair in the wrong direction is refused on direction, not on interval width.

**The model is per-transition, not five summary numbers.** Fixed effect for repair, random intercept for seed, and a variance component for **episode within seed** — episode identity is scoped to its seed, because episode 0 of seed 0 and episode 0 of seed 1 are different episodes (D-052), and pooling them would put transitions from different seeds in one group. A test asserts that scoping.

**The fallback is specification, not rescue.** When the registered model does not converge, the data collapse to episode means and the same three conditions apply there. The result records `method`, because "passed under the fallback" and "passed under the registered model" are different claims; `allow_fallback=False` makes non-convergence an error rather than a silent substitution. If neither converges the result **fails closed** — an unestimated effect is not a null one.

**The permutation null permutes at the right level, and that is the whole point.** P§7.3: labels move "at the level of the repair assignment within condition, never across episodes or transitions, which would destroy the dependence structure". The unit of permutation is therefore the **run** — every transition in one (seed, arm) block moves together, and the number of repaired runs is preserved. A transition-level shuffle would break exactly the correlation the model exists to account for, producing a null far too narrow and a test that *looks* better calibrated than it is. A test asserts no run is ever split.

**The result, measured on null data (no true repair effect): a false-positive rate of 0 in 200 permutations.** But **0% is the wrong number to quote alone**, and finding out why was the useful part. Counting only the two *statistical* conditions, the permuted acceptance rate is **5.5% against a nominal 5%** — that is the number establishing the mixed model's interval is correctly sized under the real dependence structure. The 20% practical floor then adds conservatism on top. Quoting 0% without that would credit the model with a calibration the floor was providing: the same shape of error as D-042's bound-reported-as-a-measurement.

**A flaky test of my own, replaced rather than loosened.** I first asserted the two-condition rate lay strictly between 0 and 20% at 60 permutations. Distinguishing 5% from 0% at n=60 needs luck — 0.95⁶⁰ ≈ 4.6% of runs see zero acceptances — and it duly failed. Rather than widen the bound until it passed, the test now checks the property directly: the model's standard error must match the permutation spread within a factor of two. Cheaper, and it tests the claim rather than an estimate of it.

**Gate 1 standing after this.** Of its four conditions: reliability gate **passed** (D-074, certified); compute **within budget** (450 CPU fits, zero GPU-hours against a ~120 GPU-hour trigger); permutation null **calibrated** (here); MDE **does not clear five points** (D-078, and the one needing Sol).
**Tests:** 581 → **597 passing**, 2 skipped.
**Data seen:** none. Synthetic throughout.
**Plan ref:** P§7.3, S§W5 Tue–Wed. Implements the §2 acceptance-test row.
**Reviewed by Sol:** not yet — delta 42.

### D-080 · 2026-08-18 · A recovered W5 Monday repair path, found uncommitted
**Decision:** `src/bu/experiments/repair.py` and `tests/test_repair.py` were present but **untracked** at the start of this session — a previous session built the W5 Monday repair path, wrote 22 tests for it, and never committed it. That is the DEV-005 failure class (work that does not reach the record). **Correction to the first draft of this entry:** I initially wrote that pytest was already counting these 22 tests. That is false, and I verified it — removing the two files gives **597 passing**, restoring them gives **619**, so the 22 were *not* in the "597" figures reported in deltas 39–42. `test_repair.py` was silently failing to collect in the full-suite runs (its import chain was broken before C-010 built `ScaledEvaluation`, and it stayed uncounted afterwards for a reason I could not fully reconstruct — so I state only what the remove/restore test proves rather than a mechanism I cannot verify). Committing both files protects the work from a `git clean` and makes the tracked tree match the 619 the suite now reports.

**I did not write these files, so I reviewed them before vouching for them.** Read both in full; ran all 22 tests (pass in 1.4 s); and probed the module end-to-end on a real four-arm training run rather than trusting its own tests — the repair path feeds `bu.stats.acceptance` correctly, and 10× data repair yields a 74.8% error reduction on a development-seed smoke test. Confirmed it touches no frozen constant, produces no confirmatory data, and writes no run record (`evaluate_arm` takes no logger).

**What it is.** W5 Monday's "three repair functions callable": `applicable_arms` reports which repairs a unit can receive without raising; `evaluate_arm` trains one arm and scores every movement transition, **reusing the baseline's pre-mask scale** (D-061, C-010) and refusing a repaired arm handed no scale; `acceptance_inputs` assembles the paired arrays the acceptance test consumes. Every pairing property is parametrised over **every applicable arm**, per D-055 — the file's own docstring cites that lesson, which is part of why it reads as genuine project work rather than a stray draft.

**What it depends on that did not exist when it was written.** It imports `ScaledEvaluation`, which this session built for C-010 (D-076). So at session start it was un-importable — a draft written against planned machinery. That it now composes cleanly is a point in its favour, not a coincidence to lean on: the end-to-end probe is the evidence, not the import resolving.

**Not yet reviewed by Sol, and why not via a delta.** The delta channel is at its 400-line cap with deltas 39–42 undelivered (the student is out of Sol credit until the 20th). Rather than cram or overwrite, this rides the **complete git diff since `ca545ed`**, which the bundle carries in full and which already includes this ledger entry — so Sol sees both the code and its provenance. A dedicated delta narrating W5 Monday joins the next batch after 39–42 are delivered.
**Tests:** **597 → 619 passing**, 2 skipped. The jump is these 22 repair tests, which now collect and are counted; deltas 39–42 report figures up to 597 that did not include them, and a reconciliation note in the delta file flags the change so it matches the bundle Sol runs.
**Data seen:** none. The end-to-end probe was a development-seed smoke test, in memory, no records written.
**Plan ref:** P§7.2, S§W5 Mon.
**Reviewed by Sol:** not yet — carried in the diff, narrated in the delta after delivery.

### D-081 · 2026-08-18 · W5 Friday — the figure-regeneration command
**Decision:** `src/bu/experiments/make_figures.py`. One command regenerates every figure so far **from the immutable attempt directories only** — no training, no memory, no compute (S§W5 Fri, P§13.7). A `FIGURES` registry maps each cell to its producer, so "every figure" is enumerable rather than being whatever the thesis author remembers to run; adding a figure-producing cell means adding it here.

**Two properties make "from logs only" a guarantee, both tested.** It produces the **whole** registered set — the two W3 development-seed curves plus the certified W4 gate trend — and it **fails loudly** when a log it needs is absent rather than silently producing a smaller set that reads as complete. A reader who asked for every figure and got four cannot tell a fifth was skipped.

**The W4 figure is honest about what it is.** It reads the rung-0 attempt chosen by its frozen spec hash through `select_attempt` (which refuses to guess between attempts, C-010), refuses an incomplete grid — a four-seed mean is not the certified five-seed one — and draws **no error bars**, because the exact paired bootstrap is discrete with two or three atoms and a bar would imply a sampling precision the interval does not carry (D-075). Verified visually: three curves, all peaking at N=250, the non-monotone finding D-074 records.

**Figures are gitignored; the ability to regenerate them is tracked.** The PNGs are a deliberate output, never a side effect of a run — so the script and its tests are committed and `figures/` stays ignored.
**Tests:** 619 → **626 passing**, 2 skipped.
**Data seen:** none. Plotting only, from tracked logs.
**Plan ref:** S§W5 Fri, P§13.7.
**Reviewed by Sol:** not yet — rides the diff since `ca545ed`; delta prose joins the next batch after delivery.

### D-082 · 2026-08-18 · Audit of the unreviewed statistical modules — two findings, one fixed
**Decision:** With no unblocked deliverable left, audited the code Sol has not reviewed — `mde.py`, `acceptance.py`, `repair.py` — in the project's audit tradition (D-015, D-021, D-060), probing behaviour empirically rather than reading for correctness. Two real findings; both were found by asking a question, not by a failing test. Everything asserted below was measured.

**FINDING 1 (`mde.py`) — the power test is anti-conservative, so the MDEs are optimistic. Reported, not fixed.** The MDE's whole meaning rests on the power calculation having correct type-I error. Measured directly at delta = 0: the rejection rate is **0.061–0.092, not 0.05**, and it worsens with ICC (0.09 at ICC = 1). Two causes: (a) `simulate()` rejects when `|difference| > 1.96 × bootstrap_SE` — a **Wald/normal approximation**, whereas D-044 specifies **group-bootstrap percentile intervals**; a percentile interval is better calibrated (measured) but still (b) anti-conservative at these cluster counts (~20–40 groups per class), the classic few-clusters problem. **Direction matters and is reassuring for the headline:** an anti-conservative test overstates power, so the true MDE is *larger* than the reported 18–22 points — the design is even less able to clear five points, so D-078's Gate-1-at-risk conclusion is **strengthened, not weakened.** But the reported numbers are for a test that (i) is not the one D-044 registers and (ii) over-rejects. **Not fixed here on purpose:** the MDE inference procedure is exactly what Sol must rule on, and delta 41 already flags the MDE framing as needing review; switching the interval (Wald → percentile → few-cluster-robust) changes the numbers and is a methodological choice that belongs in that ruling, not a silent edit before it. If Sol judges the whole MDE-vs-equivalence-margin framing wrong, the interval question is moot anyway.

**FINDING 2 (`acceptance.py`) — the model omitted the seed random intercept P§7.3 requires. Fixed.** P§7.3 and this function's own docstring specify random intercepts for **seed and episode within seed**. Measured: the fitted model's seed random-effect covariance (`cov_re`) was **empty** — passing `vc_formula` without `re_formula` makes statsmodels **drop its default group intercept**, leaving only the episode component. The seed-level correlation was unmodelled. **Why no test caught it:** the repair effect is paired within episode, so the seed intercept cancels in the contrast and the CI is **identical with or without it** (verified: half-width 0.000667 both ways) — no verdict changes, which is precisely the D-055 trap of a property that reads correct because the thing it omits does not happen to bite. Fixed by requesting `re_formula="1"` explicitly; a regression test asserts the seed intercept is present, and it was confirmed non-vacuous (fails on revert, passes on restore).

**Clean passes, recorded so they are not re-audited.** `repair.py` applies repairs for real (D-056 axis): capacity repair trains the larger model (74,502 vs 6,342 params), feature repair widens the input, config_ids differ, and pairing holds end-to-end on all three arms. `mde.py`'s `projected_pool` preserves the design effect exactly across scales (design-effect ratio identical at 150 and 600 per class), so the 1,500–2,000-unit projection stands. `mde.py`'s ICC columns are honestly labelled **latent** ICC; the induced binary-correctness correlation is lower (latent 0.5 → binary ~0.28), which only strengthens "sample size is the driver, not correlation".
**Tests:** 626 → **627 passing**, 2 skipped (the seed-intercept regression). Finding 2's fix is CI-neutral, so no existing result moves.
**Data seen:** none. All probes were synthetic or over the design matrix; no run records read, no fits logged.
**Plan ref:** P§7.3, P§10.4, P§10.7. Audits C-006 (D-078), D-079, D-080.
**Reviewed by Sol:** not yet — rides the diff since `ca545ed`. **Finding 1 is material to the delta-41 MDE ruling** and must be read with it.
