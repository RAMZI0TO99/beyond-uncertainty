# PROJECT STATE — *Beyond Uncertainty*

**Bachelor's thesis · Diagnosing When Embodied World Models Need More Data or a Different Model**

This is the single shared working file for the project. It is written by Claude, reviewed by Sol, and carried between sessions by the student. If a fact about this project is not in this file, it does not survive the end of a Claude session.

**The memory asymmetry — read this before anything else.** Sol runs in one continuous session and never forgets. Claude is closed and reopened repeatedly and starts each session blank. This file exists primarily so **Claude can reconstruct** what Sol simply remembers. Two consequences:

- Claude reads this file **first, in full**, at the start of every session — before touching code, before answering anything.
- Sol is **not** re-fed the whole file each time. Sol gets the delta in §8. Re-pasting everything to Sol wastes the student's effort and buries the new information in text Sol already has.

**Corollary — Sol is the continuity check on Claude.** If Claude returns after a reset and contradicts something settled weeks ago, Sol is the one who will notice. That is a real duty, not a courtesy.

**Paste rule.** This file must stay small enough to paste into a chat window. Target ≤ 500 lines. When §7 grows past that, move closed phases to `PROJECT_STATE_ARCHIVE.md` and leave a one-line pointer. Never let this file become the thing nobody reads.

**Source of truth.** The two plan documents are authoritative for *design*; this file is authoritative for *state*. Where they conflict on design, the plan wins and the conflict goes in §4 as a deviation. This file never silently overrides the plan.

- Plan: `thesis_project_plan_v1_2.docx` (v1.2, design frozen) — cited below as **P§n**
- Schedule: `thesis_day_by_day_schedule_v1_2.docx` (v1.2, 20 weeks) — cited below as **S§Wn**

---

## 0. How to use this file

### Claude — at the **start** of every session

Do this before anything else, in this order. No exceptions, including for a question that looks trivial.

1. Read this file top to bottom. §1 is where you are; §2 is what you are not allowed to change; §3–§5 are what past-you already decided.
2. Check §1's *Last updated* against today. If it is more than a week stale, say so to the student before acting — a stale snapshot is how a reset agent confidently redoes finished work.
3. Check §6 for anything Sol asked for that has not been actioned.
4. State back to the student, in two lines, where the project stands and what you believe the next action is. Wait for confirmation before starting work.

### Claude — at the **end** of every session

1. Rewrite §1 completely so it is true as of now.
2. Append a §7 session-log entry.
3. Append any new §3 decisions, §4 deviations, §5 gate records.
4. **Rewrite §8** — the delta the student hands to Sol. This is not optional; it is the only channel through which Sol learns what happened. **From the first real result onward, any delta reporting one carries a `NUMBERS` block** (D-011): unit counts including `min(N₀, N₁)`, seeds and which policy applies, point estimate, interval *and what it was taken over*, ambiguous and undiagnosed counts, and which test ran. Prose alone leaves Sol unable to audit anything, which is the same as having no reviewer.

Never edit a past entry in §3, §4, §5 or §7. Corrections are new entries that reference the old one. §1 and §8 are the only sections that get overwritten.

### Sol

Sol was onboarded once with `SOL_BRIEF.md` and this file in full, and runs continuously thereafter. From then on Sol receives only §8 deltas. Sol returns verdict blocks in the format given in the brief; Sol does not rewrite this file. The student pastes Sol's blocks back and Claude files them into §6 or §3.

If Sol's session is ever lost, re-onboard with `SOL_BRIEF.md` + this file in full, and say explicitly that it is a re-onboarding after a session loss.

### Student

Carry two things, in two directions:

- **To Sol:** §8 only. (First time, or after a Sol session loss: `SOL_BRIEF.md` + the whole file.)
- **To Claude:** the whole file, at the start of every session. Then Sol's verdict blocks as they arrive.

Keep the file in version control from Week 1 Tuesday, so its own history is recoverable and any drift is diffable.

---

## 1. Snapshot — *rewritten each session, always current*

| | |
|---|---|
| **Last updated** | 2026-08-15 |
| **Updated by** | Claude |
| **Phase** | Phase A — infrastructure |
| **Current week / day** | Week 1 Mon–Wed **complete, run early** (see DEV-002). Week 1 proper begins **2026-08-17** |
| **Next gate** | **Gate 1**, Week 5 Saturday = **2026-09-19** |
| **Repository** | [`RAMZI0TO99/beyond-uncertainty`](https://github.com/RAMZI0TO99/beyond-uncertainty) — **private**. See *Revision* row for the exact state |
| **Revision** | `main` — HEAD recorded at the end of §7's latest entry; tree **clean** at that commit. Regenerate ground truth with `scripts/sol_bundle.sh`, which reports hash and dirty flag together |
| **Tests** | **90 passing, 1 skipped**. Includes golden `unit_id` values, so a silent change to what a statistical unit means fails the suite |
| **Compute used** | 0 of ~110–145 GPU-h budget (escalation trigger ≈ 120, P§14.3) |

**Hypothesis status**

| | Claim | Status | Decided at |
|---|---|---|---|
| H1 | Ensemble disagreement tracks estimation failure | Not tested | Gate check W4, verdict W10 Mon |
| H2 | Disagreement-to-error ratio is low under hypothesis-class failure | Not tested | W10 Tue → **Gate 2** |
| H3 | Learned critic beats fitted (error, disagreement) rule by > 5 pts | Not tested | W15 Fri |

**Done:**
- **W1 Mon** — repo initialised, folder structure, deps pinned in `pyproject.toml`, first commit. *Done when: fresh clone installs and imports* — **verified** by cloning to a temp dir, building a venv, installing, importing, and running the suite.
- **W1 Tue** — config system (`src/bu/config.py`) and run-record writer (`src/bu/runrecord.py`). *Done when: a dummy run writes a complete, reloadable record* — **verified**.
- **W1 Wed** — JSONL metric logging and `load_runs()` (`src/bu/metrics.py`). *Done when: three dummy runs load into one dataframe* — **verified**.
- Additional, not in the schedule: `src/bu/constants.py`, the preregistered values in one file (D-005).
- **Sol's Q-005 ruling implemented** — registered, versioned statistical-identity field list with an import-time exhaustiveness check and tests that each registered field genuinely changes `unit_id` (D-009).
- Repository pushed to GitHub, private, SSH auth.
- **Sol's material finding fixed** — `stage` added to run identity (D-012). A unit can owe runs to several experimental obligations at overlapping seeds; without it they collided.
- **Critic feature whitelist frozen** (D-013), ahead of the Week 6 deadline, per Sol's Q-006.
- **Week 1 audit** (D-015): seven defects found and fixed before Week 2, three of them serious. `IDENTITY_VERSION` and `SCHEMA_VERSION` both bumped to 2 under a Change Record (D-016), while no data exists to invalidate.

**In flight:** nothing running. No compute consumed.

**Next three actions:**
1. **W1 Thu** — thesis prose, ~400 words: method section on environment design rationale (why custom gridworld, why symbolic state).
2. **W1 Fri** — gridworld core: 8×8 grid, boundary walls, objects with (shape, colour, position), four moves plus interact, deterministic shape-dependent transition rule, Gymnasium API. *Done when: a 200-step random rollout runs without error.*
3. **W1 Sat** — factored symbolic observation encoder with the feature-masking hook — the mechanism for Experiment 2A. *Done when: env constructs with the shape feature withheld.*

**Blocked on:** nothing. **Q-007** is the only open question — it is the one genuine plan/schedule contradiction found so far, and it is not due until Week 13.

**Standing watch — Sol's tripwire on D-001.** Sol endorsed the role split on the condition that it would revisit if *"important implementation or methodological decisions are repeatedly completed before Sol can review them."* That is a live risk in this arrangement, not a hypothetical: D-005 and D-006 were both built before Sol saw them. Mitigation: consequential design decisions go into a delta **and get delivered** before the code that depends on them is built on top of. Claude flags any decision it believes meets that bar at the moment of making it.

---

## 2. Frozen constants — *changing any of these requires a §3 Change Record and a Sol review*

These are the preregistered quantities. They are fixed **before** data collection and are not revised after seeing data. Their whole purpose is to be un-adjustable later.

| Constant | Value | Source |
|---|---|---|
| Data-repair budget | **10×** the failure-condition dataset, same generating process | P§7.2 |
| Repair acceptance | Negative fixed effect, 95% CI excluding zero, **and** ≥ **20%** relative reduction in mean per-transition error | P§7.3 |
| Acceptance test | Linear mixed-effects on per-transition error; random intercepts for seed and episode-within-seed; episode-mean fallback | P§7.3 |
| H3 equivalence margin | **±5 percentage points** balanced accuracy | P§4.2 |
| Seeds — H1/H2 conditions (Exp 1, 2A, 2B) | **5** | P§14.2 |
| Seeds — canonical repair validation | **20** | P§7.3, P§14.2 |
| Seeds — configuration sweep & its repairs | **3** | P§14.2 |
| Seeds — ablations | **5** | P§14.2 |
| Labelled configuration-conditions | ≥ **300**, ≥ **60** held out | P§10.7 |
| Statistical unit | The **configuration-condition** — throughout | P§10.7 |
| Failure threshold | Calibrated W4 Fri on a reference model, then **frozen permanently** | S§W4, P§10.1 |
| Compute escalation trigger | ≈ **120 GPU-hours** | P§14.3 |
| Reduction order when behind | catch-up day → ablations → full Exp 5 → configuration count (only to measured MDE) | S "When you fall behind" |
| **Seeds are not a reduction lever** | Withdrawn as an option in P v1.2 | P§14.3 |

**Calendar anchors** (Week 1 Monday = 2026-08-17)

| Milestone | Date |
|---|---|
| Week 1 Mon — start | 2026-08-17 |
| **Gate 1** — W5 Sat | 2026-09-19 |
| Phase B begins — W6 Mon | 2026-09-21 |
| **Gate 2** — W10 Sat | 2026-10-24 |
| Phase C begins — W11 Mon | 2026-10-26 |
| W15 Fri — H3 headline result | 2026-11-27 |
| W18 Mon — draft assembly begins | 2026-12-14 |
| W20 Fri — **submission** | 2027-01-01 |

---

## 3. Decisions ledger — *append-only*

Every decision that a future reader would otherwise have to reconstruct. Format:

```
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

---

## 4. Deviation log — *append-only · satisfies the schedule's mandated deviation log*

Anything not done as written, and why. **The schedule requires several of these to appear in the thesis methodology**: the reliability-gate rung reached, the PPO substitution, any repair-budget or configuration-count reduction, any cut experiment, and the W2 decision on whether the Experiment 2A conditions are drawn from the configuration sweep or are additional to it.

Format: `Week n Day | what was skipped or substituted | why | goes in methodology? yes/no`

### DEV-001 · Pre-start · Scripted exploratory policy replaces PPO
**Deviation:** PPO is replaced by a coverage-biased scripted exploratory policy with forced object interactions.
**Why:** P§13.2 permits the substitution and requires it to be recorded rather than hidden. PPO integration and tuning is one of the largest human-time sinks in the original Month 1, and the policy is explicitly not an object of study.
**Evidence required:** W2 Fri coverage metric over (shape, action) pairs; W2 Sat writes it into the methodology with the coverage figure.
**Goes in methodology:** **yes** — mandatory.

*(This deviation is inherited from the schedule document itself, which already made and justified it. Everything below this line is a live deviation, recorded as it happens.)*

### DEV-002 · Week 1 Mon–Wed run on 2026-08-15, two days early
**Deviation:** the Week 1 Monday, Tuesday and Wednesday cells were completed on Saturday 2026-08-15, before the 2026-08-17 start.
**Why:** all three are pure infrastructure — no compute consumed, no preregistered quantity touched, nothing that could bias a result. Doing them early converts Week 1's short days from typing into review, which is the scarcer resource now that implementation sits with Claude (see Q-004).
**Goes in methodology:** **no** — no bearing on any result.

### DEV-003 · 2026-08-15 · venv created with `--system-site-packages`
**Deviation:** the virtual environment reuses the system torch/numpy/scipy/pandas rather than installing isolated copies.
**Why:** avoids re-downloading a CUDA-enabled torch. `pyproject.toml` pins every version, and every run record captures the resolved versions actually in use, so reproducibility is preserved. A fully isolated environment is available by dropping the flag.
**Goes in methodology:** **no** — but the pinned versions do appear in the reproducibility section.

---

## 5. Gate records

A gate is signed off in writing, with the verdict and the evidence behind it, on the day it falls. **Slip is absorbed by catch-up days, never by moving a gate.**

### Gate 1 — Week 5 Saturday, 2026-09-19 — *not yet reached*
Four conditions, all must hold:
1. Reliability gate passed with some estimator, **and the rung recorded** (rung 0 = default ensemble). If passed only at rung 3 or 4, H1 is recorded as **falsified for ensembles** and all downstream results are reported as a secondary path about that estimator.
2. Measured compute estimate within budget (timing harness, W4 Fri, against the ≈120 GPU-h trigger).
3. Permutation null shows the repair-acceptance test is calibrated (W5 Wed, 200 permutations).
4. MDE simulation shows the evaluation set can resolve a 5-point balanced-accuracy difference — computed on `min(N₀, N₁)`, not the total.

*Failure of condition 1 at every rung ⇒ pivot to a characterisation study of why uncertainty estimation is unreliable in this setting. That is a complete thesis, and the decision is made here, not in Month 4.*

### Gate 2 — Week 10 Saturday, 2026-10-24 — *not yet reached*
Two conditions:
1. Does the H2 signature reproduce across seeds? A pattern present in 3 runs out of 5 is reported as **unreliable**, not as a weak positive. If it does not reproduce, execute the pivot — decided here, not in Month 4.
2. Does the surviving per-class unit count still clear the Week 5 MDE requirement? If not, launch more configurations **now** — this is the last week where that is cheap.

---

## 6. Open questions

**For Sol** — questions Claude wants adversarially reviewed. Sol answers in verdict-block format; answered items move to §3 as decisions.

| # | Question | Raised | Status |
|---|---|---|---|
| Q-001 | Is the Claude/Sol split in D-001 the right one, or does it under-use Sol? | 2026-08-13 | **Closed.** Sol: keep as written, high confidence. Would revisit if implementation or methodological decisions are repeatedly completed before Sol can review them — a standing tripwire, see §1 |
| Q-002 | Weeks 18–20 collide with Christmas / New Year; submission Friday is 2027-01-01. Shift or accept? | 2026-08-13 | **Closed** by student decision → D-004. Sol concurred |
| Q-003 | The W2 Wed confound double-booking. Same units or additional ones? | 2026-08-13 | **Closed** → D-007. Same units, run at higher seed count. Enumerator must dedupe by `unit_id` |
| Q-004 | Schedule capacity model now that Claude implements — hold dates, or compress? | 2026-08-15 | **Closed.** Sol agrees: hold every date and gate; spend the gain on review, understanding, documentation and prose, never scope. Names the failure mode as **verification lag** — implementation outrunning student and reviewer, leaving choices embedded in code before they are understood. Consequential methodological decisions must be *delivered before* dependent implementation proceeds; routine implementation need not wait |
| Q-005 | Should statistical identity be a registered field list rather than a schema hash? | 2026-08-15 | **Closed** → D-009. Sol: yes, explicit versioned identity list; `SCHEMA_VERSION` alone insufficient. Implemented in the stronger form Sol named — exhaustive classification, enforced at import, tested per field |
| Q-006 | Whitelist vs blacklist for the leakage firewall; and when to freeze it. | 2026-08-15 | **Closed** → D-013. Sol: whitelist, frozen before the Week 6 firewall is accepted, in a dedicated schema module rather than `constants.py`, with X / y / groups physically separate. Since P§13.5.1 fully specifies the features, Sol's "freeze it now" condition was met and it is frozen |
| Q-007 | **A genuine plan/schedule contradiction, found while freezing the schema.** P§13.5.1's table retains the Error group in *"Full; No-magnitude; Statistics-only"* — so the **no-statistics** variant drops error features entirely. But S§W13 Tue describes that variant as *"latent state, action and **error history** only"*. The two disagree on whether no-statistics sees error history. This changes what the variant means and therefore how the W13 construction-leakage control is read: if no-statistics has no error signal at all, a strong result there is far more surprising. Per our source-of-truth rule the plan wins, and the schema is frozen that way — but the disagreement should be resolved explicitly, not by default. | 2026-08-15 | **Open** — due before W13 Tue |

**For Claude** — things Sol or the student wants implemented, checked or measured.

| # | Item | Raised by | Status |
|---|---|---|---|
| — | *(none yet)* | | |

---

## 7. Session log — *append-only, newest last*

One entry per working session. Terse. The test of a good entry: someone reading only this section can tell what exists, what it does, and what state it was left in.

Format:

```
### YYYY-MM-DD · Week n Day · <hours> · <agent>
**Did:** what was actually built or run.
**Result:** what came out, including numbers.
**Left:** state at the end — what is running, what is half-finished.
**Next:** the single next action.
```

### 2026-08-13 · Pre-start · setup · Claude
**Did:** read both plan documents in full; established the working protocol with Sol (D-001); anchored the schedule to 2026-08-17 (D-002); recorded the memory asymmetry and the §8 delta channel (D-003); created this file and `SOL_BRIEF.md`.
**Result:** no project work yet. Three open questions raised in §6, one of them (Q-002, the Christmas/New Year collision at Weeks 18–20) worth settling before Week 1 rather than in December.
**Left:** repository not created. Folder currently holds the two plan documents and these two files.
**Next:** W1 Mon (2026-08-17) — repository init, folder structure, pinned dependencies, first commit.

### 2026-08-15 · Week 1 Mon–Wed (run early, DEV-002) · Claude
**Did:** built the project infrastructure. Repo initialised at `main`, venv, deps pinned in `pyproject.toml`. `src/bu/constants.py` (preregistration in code, D-005), `config.py` (three identities, D-006), `runrecord.py` (provenance incl. git dirty flag + stored diff), `metrics.py` (per-line-flushed JSONL + `load_runs()`). 16 acceptance tests in `tests/test_infrastructure.py`, one per schedule "Done when" criterion plus the identity and frozen-constant invariants. README written.
**Result:** all three Week 1 done-when criteria verified rather than assumed — fresh clone into a temp dir installs, imports and passes 16/16. Commit `233634f`. One real bug caught by the tests: tuple-valued config fields (`withheld_features`) were being broadcast by pandas as a column of values instead of a scalar; sequence fields now serialise to a canonical string so they survive groupby and CSV round-trips.
**Left:** nothing running, no compute consumed. `env/`, `models/`, `critic/`, `stats/`, `experiments/` exist as empty packages.
**Next:** W1 Thu — thesis prose, ~400 words on environment design rationale.

### 2026-08-15 (later) · Sol's first answers filed · Claude
**Did:** filed `SOL ANSWER` blocks for Q-001, Q-002 and Q-003. Q-003's ruling recorded as D-007 and independently checked against P§14.2's run-count arithmetic (30 + 20 + 25 canonical + ~225 sweep = ~300 = P§10.7's target), which agrees with it. Closed Q-001/Q-002/Q-003. Recorded Sol's D-001 tripwire as a standing watch item in §1.
**Result:** the Week 2 enumerator now has its rule — deduplicate by `unit_id`, and let seed count follow a unit's role rather than a separate run list. D-006's content hashing makes that automatic. Also found and closed a protocol hole: Sol had answered from delta #1 while delta #2 sat undelivered in §8, which a plain overwrite would have destroyed (D-008 — §8 now accumulates until marked delivered).
**Left:** Q-004 and Q-005 still unanswered — Sol has not yet seen delta #2. No code changed this session.
**Next:** deliver the merged §8 to Sol; W1 Thu prose.

### 2026-08-15 (evening) · Q-004/Q-005 filed, identity registry built, repo on GitHub · Claude
**Did:** pushed to GitHub (private, SSH). Implemented Sol's Q-005 ruling as D-009: `UNIT_IDENTITY_FIELDS` / `UNIT_NON_IDENTITY_FIELDS` registries, `IDENTITY_VERSION` separate from `SCHEMA_VERSION`, import-time exhaustiveness check, both versions plus the registered field list written into every run record. Added the tests Sol named as its condition — one per registered field, asserting that varying it genuinely changes `unit_id`, plus a test that the exhaustiveness check actually fires. Filed Q-004's answer and its verification-lag warning.
**Result:** 28 passing, 1 skipped (the exclusion-list test, vacuous until a field is excluded). All nine `UnitSpec` fields are identity-bearing today; the machinery exists so the first exclusion is a reviewed decision. Separately found a leakage vector while working: `load_runs()` attaches `family` and every `unit_*` axis to each row, and those are exactly what P§7.5 forbids the critic from seeing — recorded as D-010, whitelist not blacklist, raised as Q-006.
**Snag, resolved:** the GitHub repo had an initial commit with a `LICENSE`, and the machine had no git identity configured, which stalled a rebase mid-flight. Rebased rather than force-pushed so the MIT licence and its authorship line survive; no commit was lost. `.claude/settings.local.json` is now untracked — machine-local permission state does not belong in a shared repo. Repo git identity set to *Ramzi Alashmali / ai.research@sofa.ye*; change with `git config user.email` if a different address should own the commits.
**Left:** nothing running, no compute. Week 1 Thu–Sat outstanding.
**Next:** W1 Thu prose, then the gridworld core.

---

### 2026-08-15 (night) · Sol review actioned end to end · Claude
**Did:** worked Sol's `SOL REVIEW` of 2026-08-15 in full. Fixed the material finding as D-012 — `stage` is now part of `run_id`, `STAGE_SEEDS` binds P§14.2's seed policy to each stage in code, and Config-level fields joined the import-time classification check. Froze the critic feature whitelist as D-013 (`src/bu/critic/schema.py`), transcribed from P§13.5.1, with all of Sol's required tests. Recorded D-014 owning an earlier ledger reordering. Rewrote §1 for the stale-state finding, archived the five delivered deltas to `PROJECT_STATE_ARCHIVE.md`, and adopted `DELTA_ID` / `PREVIOUS_DELTA_ID`.
**Result:** 68 passing, 1 skipped, up from 28. The material finding was a live bug, not a tidiness point: `unit + arm + seed` was genuinely not unique, because a canonical condition owes five seeds to an H1/H2 claim and twenty to repair validation, overlapping on seeds 0–4. Two obligations resolved to one `run_id`. Also found a real plan/schedule contradiction while transcribing the schema — P§13.5.1 excludes the Error group from the no-statistics variant, S§W13 Tue says that variant sees "error history". Raised as Q-007; the plan wins by our source-of-truth rule and the schema is frozen accordingly, but it wants an explicit resolution.
**Left:** state file 329 → ~380 lines, back under the cap. Nothing running, no compute. Week 1 Thu–Sat outstanding.
**Next:** W1 Thu prose, then the gridworld core.
**HEAD at end of session:** recorded in the commit that carries this entry; `scripts/sol_bundle.sh` reports hash and dirty flag together.

### 2026-08-15 (late) · Week 1 audit before Week 2 · Claude
**Did:** audited every Week 1 file line by line, probing behaviour empirically rather than reading for correctness. Seven defects found and fixed (D-015), each with a named regression test. Bumped `IDENTITY_VERSION` and `SCHEMA_VERSION` to 2 under a Change Record (D-016).
**Result:** 68 → 90 tests. Three defects were serious. A1 meant D-012's fix for Sol's material finding existed only in the directory name — `stage` never reached the run record or the analysis frame. A2 meant `unit_id` embedded a **memory address** whenever a value lacked a JSON form; the first probe showed two distinct objects hashing *equal*, because the freed address had been reused, which is precisely how it would have survived casual testing. A3 meant `0` and `0.0`, and two orderings of `withheld_features`, produced different units — inflating the labelled unit count that the MDE and every confidence interval rest on. Fresh-clone install re-verified; the golden `unit_id` reproduces in a clean checkout.
**Left:** nothing running, no compute. Week 1 Thu–Sat outstanding. Q-007 still open.
**Next:** W1 Thu prose, then the gridworld core.

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 7. Delta 6 was delivered; deltas 1–5 are archived.

```
=== UPDATE FOR SOL ===
DELTA_ID: 7
PREVIOUS_DELTA_ID: 6
DATE: 2026-08-15 (late)
SUBJECT: Week 1 audit before Week 2 -- seven defects, three serious

The student asked for an audit of all Week 1 work before Week 2 starts. Every
file was re-read line by line and probed empirically rather than by inspection.
Seven defects. Each now has a named regression test. 68 -> 90 tests.

SERIOUS -- A1. to_dict() omitted `stage`, defeating D-012 for anything persisted.
Your material finding was fixed only in the directory name. A round-trip reset
the stage to "pilot", the run record never stated it, and load_runs() had no
stage column -- so an analysis could not separate a unit's five H1/H2 seeds from
the twenty behind its repair label, which is the exact thing your finding was
about. Fixed in to_dict/from_dict, promoted to a top-level run-record key, and
added as a load_runs column. There is now an end-to-end test that builds both
obligations on one unit and asserts the analysis can tell them apart.

SERIOUS -- A2. _hash used `default=repr`, embedding memory addresses.
Any value without a JSON form hashed via repr, which for a plain object contains
its address -- so unit_id would differ between processes. Worth noting how it
hid: the first probe returned EQUAL hashes for two distinct objects, because the
first had been freed and its address reused. Only holding both references alive
exposed it. The fallback is removed; _hash now raises with an explanatory
message. A real subprocess test replaces the previous cross-process test, which
compared a value with itself.

SERIOUS -- A3. No value canonicalisation, so one condition could occupy several
units. confound_rate 0 vs 0.0 hashed differently. ("shape","colour") and
("colour","shape") hashed differently. ("shape","shape") made a third. Every one
of those inflates the labelled unit count -- the quantity the MDE and every
confidence interval rest on. Fixed by canonicalising at construction: numerics
coerced to their declared type, withheld_features sorted and deduplicated.

MATERIAL -- A4. layout was unvalidated. layout="unifrom" was accepted and became
a genuine configuration-condition. Now a registered set, like family and
causal_attribute. Sizes must also be positive.

MATERIAL -- A5. numpy arrays were stringified into the metrics log --
np.array([.1,.2,.3]) written as the STRING "[0.1 0.2 0.3]". It writes without
complaint and reloads as text, failing only when a figure does arithmetic on it
much later. Per-dimension normalised error (Plan 10.3) is exactly this shape.

MINOR -- A6. run discovery was one directory deep, so a batch runner grouping
runs by stage would make them invisible -- silently, as fewer rows.
MINOR -- A7. golden unit_id values are now pinned, so identity cannot drift
without a test failing.

ALSO: impossible repairs now fail when the config is BUILT rather than hours
later mid-batch on Kaggle -- a spec error found mid-batch costs a session.

CHANGE RECORD -- D-016, and it needs your eye because it is exactly the kind of
change the preregistration discipline exists to police.
  IDENTITY_VERSION 1 -> 2, SCHEMA_VERSION 1 -> 2.
  Has any data been seen? NO. No run, no compute, no label. Only test fixtures.
  Why identity: the field SET is unchanged, but A3 changed canonicalisation, so
  ids before and after are not comparable. Leaving the version at 1 while ids
  changed would be worse than the original defect.
  Why schema: `stage` was added in D-012 without a bump -- an oversight, fixed.
  Every unit_id changed. Nothing depends on the old values.

This is the last moment such a change is free. From Week 6 it would not be.

NOT CHANGED, but worth your judgement: capacity_repair raises hidden_size to
max(HIDDEN_SIZES) = 256. Plan 8.2.2 says "increase capacity" without saying to
what. Going to the maximum is deterministic and makes the repair unambiguous,
but it is an interpretation, not a quotation. Say if you read it differently.

STILL OPEN: Q-007 (the Plan 13.5.1 vs Schedule W13 Tue contradiction about
whether the no-statistics variant sees error history).

Fresh-clone install re-verified; the golden unit_id reproduces in a clean
checkout. Request a bundle on src/bu/config.py and src/bu/metrics.py to audit
any of this rather than accept it.

NEXT ACTION: W1 Thu prose, then W1 Fri gridworld core.
=== END UPDATE ===
```
