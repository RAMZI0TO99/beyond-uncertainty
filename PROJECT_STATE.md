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
4. **Rewrite §8** — the delta the student hands to Sol. This is not optional; it is the only channel through which Sol learns what happened.

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
| **Last updated** | 2026-08-13 (setup session, before Week 1) |
| **Updated by** | Claude |
| **Phase** | Pre-start — Phase A begins Week 1 |
| **Current week / day** | Not started. Week 1 Monday = **2026-08-17** |
| **Next gate** | **Gate 1**, Week 5 Saturday = **2026-09-19** |
| **Repository** | Not yet created. Week 1 Monday deliverable |
| **Compute used** | 0 of ~110–145 GPU-h budget (escalation trigger ≈ 120, P§14.3) |

**Hypothesis status**

| | Claim | Status | Decided at |
|---|---|---|---|
| H1 | Ensemble disagreement tracks estimation failure | Not tested | Gate check W4, verdict W10 Mon |
| H2 | Disagreement-to-error ratio is low under hypothesis-class failure | Not tested | W10 Tue → **Gate 2** |
| H3 | Learned critic beats fitted (error, disagreement) rule by > 5 pts | Not tested | W15 Fri |

**Done:** nothing yet — project not started.

**In flight:** nothing.

**Next three actions:**
1. W1 Mon — repository init, folder structure, pinned deps (torch, gymnasium, numpy, scipy, statsmodels, pandas), first commit.
2. W1 Tue — config system + run-record writer (full config, seed, git commit hash to disk).
3. W1 Wed — structured JSONL metric logging + `load_runs()` helper.

**Blocked on:** nothing.

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
| Q-001 | Is the Claude/Sol split in D-001 the right one, or does it under-use Sol? | 2026-08-13 | Open |
| Q-002 | Weeks 18–20 (draft assembly → submission) run 14 Dec – 3 Jan, with submission Friday landing on **New Year's Day 2027**. Should the whole schedule shift a week earlier, should the buffer be front-loaded into Phase D, or is this acceptable? This is a decision to take **now**, while it is free. | 2026-08-13 | Open |
| Q-003 | The W2 Wed confound double-booking (P§8.2.1 makes the four non-zero confound levels the Exp 2A conditions; P§13.1.2 also makes confound a configuration axis). Are those the same units or additional ones? The schedule requires the decision be made in code and recorded. | 2026-08-13 | Open — due W2 Wed |

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

---

## 8. → TO SOL — *latest delta · overwritten each session · this is the only thing the student pastes to Sol*

Everything below is new since Sol was last updated. Copy the whole block.

```
=== UPDATE FOR SOL · 2026-08-13 · Pre-start (setup session) ===

STATE: Not started. Week 1 Monday = 2026-08-17. Next gate: Gate 1, Sat 2026-09-19.
Repository not yet created. 0 of ~110-145 GPU-h used.

WHAT HAPPENED:
- Claude read both plan documents (Plan v1.2, Schedule v1.2) in full.
- Working protocol agreed (D-001): Claude holds the repository and does all
  implementation; Sol is adversarial reviewer and methodological guardian and
  does not write project code. PROJECT_STATE.md is the sole shared state.
- Schedule anchored to Monday 2026-08-17 (D-002). All gate dates now resolve to
  real dates.
- Memory asymmetry recorded (D-003): Sol runs continuously and remembers; Claude
  is closed and reopened and starts blank. Sol is therefore the continuity check
  on Claude, and receives deltas rather than the whole file.

DECISIONS TO REVIEW: D-001, D-002, D-003 — all marked "Sol review pending".

OPEN QUESTIONS FOR YOU:
- Q-001: Is the Claude/Sol split in D-001 right, or does it under-use you?
- Q-002: Weeks 18-20 run 14 Dec - 3 Jan; submission Friday falls on New Year's
  Day 2027. Shift the start a week earlier, front-load buffer into Phase D, or
  accept? Free to decide now, expensive to discover in December.
- Q-003: The Week 2 confound double-booking. P§8.2.1 makes the four non-zero
  confound levels (0.25/0.5/0.75/0.9) the Experiment 2A conditions; P§13.1.2
  also makes confound a configuration axis. Same units or additional ones?
  Due Week 2 Wednesday; it changes the labelled unit count.

NEXT ACTION: W1 Mon (2026-08-17) — repository init, folder structure, pinned
dependencies (torch, gymnasium, numpy, scipy, statsmodels, pandas), first commit.
=== END UPDATE ===
```
