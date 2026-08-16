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

