# PROJECT STATE — *Beyond Uncertainty*

**Bachelor's thesis · Diagnosing When Embodied World Models Need More Data or a Different Model**

This is the shared working file for the project. It is written by Claude, reviewed by Sol, and carried between sessions by the student. **It travels with `DECISIONS.md`** — the decisions ledger moved there when this file outgrew its paste cap (D-037), and §3 below indexes it. If a fact about this project is not in one of the two, it does not survive the end of a Claude session.

**The memory asymmetry — read this before anything else.** Sol runs in one continuous session and never forgets. Claude is closed and reopened repeatedly and starts each session blank. This file exists primarily so **Claude can reconstruct** what Sol simply remembers. Two consequences:

- Claude reads this file **first, in full**, at the start of every session — before touching code, before answering anything.
- Sol is **not** re-fed the whole file each time. Sol gets `DELTA_TO_SOL.md`. Re-pasting everything wastes the student's effort and buries new information in text Sol already has.

**Corollary — Sol is the continuity check on Claude.** If Claude returns after a reset and contradicts something settled weeks ago, Sol is the one who will notice. That is a real duty, not a courtesy.

**Paste rule.** This file must stay small enough to paste into a chat window. Target ≤ 500 lines. When §7 grows past that, move closed phases to `PROJECT_STATE_ARCHIVE.md` and leave a one-line pointer. Never let this file become the thing nobody reads.

**Source of truth.** The two plan documents are authoritative for *design*; this file is authoritative for *state*. Where they conflict on design, the plan wins and the conflict goes in §4 as a deviation. This file never silently overrides the plan.

- Claude's operational handoff, read first at session start: `CLAUDE.md`
- Plan: `docs/thesis_project_plan_v1_2.docx` (v1.2, design frozen) — cited below as **P§n**
- Schedule: `docs/thesis_day_by_day_schedule_v1_2.docx` (v1.2, 20 weeks) — cited below as **S§Wn**

---

## 0. How to use this file

**Claude — session start.** Before anything else, including for a question that looks trivial: read this file in full, then `DECISIONS.md` (§1 where you are, §2 what you may not change, §3's index points into the ledger, §4–§5 deviations and gates); check §1's *Last updated* against today and say so if it is over a week stale — a stale snapshot is how a reset agent confidently redoes finished work; check §6 for anything Sol asked for that is unactioned; then tell the student in two lines where things stand and what you think is next, and wait.

**Claude — session end.** (1) Rewrite §1 so it is true now. (2) Append a §7 session-log entry. (3) Append any new §3 decisions, §4 deviations, §5 gate records. (4) Update `DELTA_TO_SOL.md` — append if undelivered, replace only once delivered (D-008, D-023), naming the session under `COVERS SESSIONS`; it is the only channel through which Sol learns anything. (5) Run the suite: `tests/test_project_state.py` enforces (1)–(4) mechanically (D-022), and if it fails, **fix the file, not the test**. From the first real result onward every delta reporting one carries a `NUMBERS` block (D-011): unit counts including `min(N₀, N₁)`, seeds and policy, point estimate, interval *and what it was taken over*, ambiguous and undiagnosed counts, and which test ran — prose alone leaves Sol unable to audit anything, which is the same as having no reviewer.

**Never edit a past entry in §3, §4, §5 or §7.** Corrections are new entries referencing the old one. §1 and §8 are the only sections that get overwritten.

**Sol.** Onboarded once with `SOL_BRIEF.md` and this file in full, then continuous; thereafter receives only `DELTA_TO_SOL.md`. Returns verdict blocks in the brief's format and does not rewrite this file — the student pastes them back and Claude files them into §6 or §3. If Sol's session is ever lost, re-onboard with `SOL_BRIEF.md` + this whole file, saying explicitly that it follows a session loss.

**Student.** To Sol: `DELTA_TO_SOL.md` only (first time or after a Sol session loss: `SOL_BRIEF.md` + this whole file). To Claude: the whole file at every session start, then Sol's verdict blocks as they arrive. Keep this file in version control so its own history is diffable.

---

## 1. Snapshot — *rewritten each session, always current*

| | |
|---|---|
| **Last updated** | 2026-08-17 |
| **Updated by** | Claude |
| **Phase** | Phase A — infrastructure |
| **Current week / day** | **Weeks 1–3 CERTIFIED and frozen at `9c0d89d`** (D-067); documentation continuation certified at `7dbcd32`. **W4 Mon CERTIFIED at `a84cf6c`**; the gate wrapper Tuesday requires is built (D-070). Fifteen Sol reviews actioned. **Next: W4 Tue**, gate day 1 — the first cell that spends compute. Week 1 Monday is **today** — roughly two weeks ahead of calendar (DEV-002) |
| **Next gate** | **Gate 1**, Week 5 Saturday = **2026-09-19** |
| **Repository** | [`RAMZI0TO99/beyond-uncertainty`](https://github.com/RAMZI0TO99/beyond-uncertainty) — **private**. See *Revision* row for the exact state |
| **Revision** | `main` — HEAD at the end of §7's latest entry, tree **clean**. **Certified base: `9c0d89d`** — Sol certified it on 2026-08-17, covering the whole chain from `2875e60` through the pilot, the audit and D-061 … D-066. **Set `BASE=a84cf6c` for the next bundle** — Sol certified it as the documentation continuation so this housekeeping is not re-sent; the frozen *implementation* remains `9c0d89d` (D-043, D-067) |
| **Tests** | **483 passing, 2 skipped** (CUDA tests run only where a device exists; the two-GPU test skips on this machine and is declared unverified) (the CUDA test runs only where a device exists). Includes golden `unit_id` values, the Experiment 2A aliasing property, D-030's stream pairing, gradient isolation between the heads, and — new — that MC-dropout samples actually **vary** and that a second pilot run cannot touch the first one's evidence |
| **Compute used** | **0 GPU-hours** of ~110–145 budgeted (trigger ≈ 120, P§14.3). Every fit so far ran on **CPU**. Two sub-second GPU tests now run in the suite (~68 MiB) to cover the CUDA RNG fork and seeding — the student's other workload has finished and the card is at ~0.9/16 GB |
| **Design scale** | 300 units (the statistical unit) in **240 comparison groups** · unit-level class balance **150/150**, group counts 125/115 · **8,197 model fits** vs P§14.2's ~8,700 |

**Hypothesis status**

| | Claim | Status | Decided at |
|---|---|---|---|
| H1 | Ensemble disagreement tracks estimation failure | Not tested | Gate check W4, verdict W10 Mon |
| H2 | Disagreement-to-error ratio is low under hypothesis-class failure | Not tested | W10 Tue → **Gate 2** |
| H3 | Learned critic beats fitted (error, disagreement) rule by > 5 pts | Not tested | W15 Fri |

**Done — Weeks 1 and 2, every "Done when" criterion verified rather than asserted.**
Detail is in `PROJECT_STATE_ARCHIVE.md` §7 and in the decisions below.
- **Week 1** — repo, `constants.py` (D-005), config and three identities (D-006), run records, JSONL logging, gridworld, masking encoder. Audited: seven defects (D-015), version bump under a Change Record (D-016).
- **Week 2** — confound parameter, enumerator (D-018), scripted policy and collector with coverage evidence (D-020), both prose cells drafted (D-019, awaiting the student's rewrite). Audited: six defects (D-021).
- **Sol's earlier rulings implemented** — identity registry (D-009), `stage` in run identity (D-012), critic whitelist frozen (D-013).
- **All eight of Sol's 2026-08-16 reviews actioned in full** (D-025 … D-057). Every verdict was CHALLENGED; every finding was independently verified before anything changed, and every one stood. The second found 375 fits of phantom compute. The fourth and fifth were both about **my reasoning rather than the code**, on the same paragraph: a worst-case bound reported as a measurement (D-042), then two different estimands compared as if one approximated the other (D-044).
- **Week 3 Mon–Wed built** (D-046, D-049, D-050) and then **substantially corrected** across Sol's sixth, seventh and eighth reviews (D-051 … D-057). The correction is the important part: the behaviour policy was **non-stationary across episodes**, so dataset size was confounded with behaviour distribution; validation was carved from a nested prefix, so the held-out set was a function of dataset size *and* a "100-transition" condition trained on 50; and N=100 had one training episode, making its episode bootstrap degenerate. All three fixed and verified.
- **D-030's named streams are built** (`src/bu/streams.py`), verified on the pairing properties rather than merely present: Experiment 1's datasets are nested prefixes, 2A/2B levels share a group, units in **different comparison groups** are independent at equal seeds — units inside one group are correlated by design (D-039, corrected by D-042 and D-044). `arm` never affects stream identity; raw `stage` is absent from a key but can reach data-stream *derivation* via `comparison_stage`, which is why `execution_plan` verifies that every role merged into one fit resolves to identical streams (D-038).

**In flight:** nothing running. **No compute consumed.**

**Next actions — Week 3, the world model.**
0. **W3 Mon — DONE and Sol-ruled** (D-046, D-047, D-048). Criterion met across all five capacity levels and all four withholding configurations. Beyond it: blocked movement transitions carry **1.67×** the position error of free moves; `interact` is deterministic and predictable in every canonical condition (0 aliased successors) but aliased when position is withheld — a second mechanism behind D-026.
1. **W3 Tue — DONE** (D-049). Trains 5,000 transitions, early-stops at epoch 10 of 31 in 1.5s CPU, curve reaching `load_runs()`. Split by episode and **strided**, all of D-047's constraints implemented. Measured: a transition-level split is **4.5–8.7× optimistic**, worst at small n.
2. **W3 Wed — DONE** (D-050). Five members on 5,000 transitions in 8.0s CPU; per-member validation errors 0.0034–0.0061, sd 0.0010, each drawing ~50 of 80 training episodes. **Raised Q-011.**
3. **W3 Fri and Sat — DONE** (D-058, corrected by **D-059**). 90 fits on CPU, rerun with per-transition export. **Error falls monotonically in N; disagreement does not** — it peaks at N=250, direction reproduced in all three seeds paired (+0.179, +0.360, +0.102). Measured **per member**: at N=100 members range 0.219–0.639 of the target's variation, at N=250 0.220–0.836, at N=5,000 0.939–0.974. The mechanism is **heterogeneous contraction, not collapse** — disagreement peaks where the spread across members is widest. The lowest whole-pool ratio is at N=100 (0.462), but that is **not** the registered H2 ratio, which is defined over the failure set and needs the W4 Fri threshold.
4. **W3 closeout — DONE** (D-061, D-062, D-063), on Sol's review of deltas 27–28. Two serious findings, both verified first and **one of them different from how it was stated**: the MC-dropout fix restored state without re-enabling dropout (measured on a real dropout model: **exactly zero** disagreement under the old path), and the rerun hazard was reachable through a *different-scope* rerun rather than the append path, which `write_run_record` already blocked. Scale ruling adopted and the pilot's numbers reproduce **exactly**. No second trunk.
5. **W4 Mon — DONE** (D-068, D-069). The trend test is one function for both stages, built under Sol's rule **frozen before it saw data**, with 22 tests. On the pilot: **rho = −0.9429, 95% CI [−0.9429, −0.8286], PASS** on development seeds. The N=250 peak costs exactly one of fifteen pairwise inversions and weakens rho naturally, as Sol predicted — nothing removed, nothing smoothed. **The interval is coarse, and that is the finding:** the 27 resamples take only **two** distinct values, so it is the full support rather than a tight estimate. Development evidence about the pipeline, **not** a measurement of H1 and **not** the gate.
6. **W4 Tue — NEXT, and it is the first cell that spends compute.** Gate day 1: the three predeclared configurations × **five** development seeds × six sizes = **90 ensembles / 450 fits**. The wrapper is built and tested (D-070): it refuses anything that is not exactly that shape, refuses confirmatory seeds, and passes rung 0 **only if all three configurations pass** — no majority vote, no pooled curve. **Ask the student before starting it.** Then record the verdict *and the rung*. **C-010 must be built before W4 Friday**, the first cell that can violate the D-061 scale rule.

**No open questions.** Q-011 closed by D-053 (episode bootstrap primary). Q-010 closed by D-047: the auxiliary head is detached, both losses are action-conditional, and three unrecorded result-affecting knobs are gone. Position loss improved 0.002242 → 0.000931 at the same budget. **D-047's open item is closed** by D-063: the real loop never closed the gap at any size or member, Sol ruled against a second trunk, and the detached head is now a **non-decisional diagnostic** — barred from the trunk, from early stopping and checkpoint selection, from the failure set, from repair labels and from the critic's residual.

**Blocked on:** **W4 Tuesday's gate, deliberately.** Two gates on it, neither technical: Sol has not yet reviewed the wrapper's eligibility and aggregation rules (delta 34, undelivered), and the student has not said which device to spend. The rules are what make Tuesday's number a *verdict*, and they are cheaper to change before a number exists than after — the verification-lag failure Q-004 names. Still blocked, correctly, and the boundaries travel *with* the certification rather than being relaxed by it: **confirmatory execution** and **repair validation** (C-008, C-009); **the masked failure-set analysis until C-010 is built — required before W4 Friday**; **MC-dropout rung 3**, which needs an explicit architectural decision because `WorldModel` has no dropout; **critic splitting** and **W5 MDE approval** (C-003, C-005, C-006). No open questions.

**Standing watch — Sol's tripwire on D-001.** Sol endorsed the role split conditionally, and DEV-005 was a hit against that condition. Sol weighed it on 2026-08-16 and **kept the split**, on the grounds that the mechanised protocol tests improve the arrangement more than reassigning implementation would. The watch stays live: consequential design decisions go into a delta **and get delivered** before dependent code is built on them, and Claude flags any decision it believes meets that bar at the moment of making it. D-030 is the current test of that — decided, filed, and deliberately left unbuilt.

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
| Balanced-accuracy weighting | **unit** — equal weight per configuration-condition; group-bootstrap intervals | D-044 |
| Confirmatory seed base | **1000** — every seed below it is pilot data, permanently excluded | D-034 |
| Stream version | **3** — separate validation and evaluation data streams | D-052 |
| Episode length | **10** steps | D-052 |
| Validation / evaluation pools | **40 / 100** complete episodes, fixed and shared | D-052 |
| Normalising scale | the **full movement evaluation pool**, measured **before any failure mask**, then reused for every subset, member and dataset size sharing that pool | D-061 |
| Bootstrap | **episode-level block bootstrap**, primary for H1/H2 | D-053 |
| Bootstrap sensitivities | transition-level and init-only: **W3 Fri pilot only**, never a verdict, not in the 8,197 | D-054 |
| H1 trend test | Spearman's rho, disagreement vs the **six** registered sizes; **negative** expected; passes only if the **whole** 95% interval is below zero | D-068 |
| Trend interval | **exact** paired seed-block bootstrap — 3³ = 27 / 5⁵ = 3,125 enumerated, no RNG; quantile method `linear` | D-068 |
| Trend partitions | W4 gate **development only**, W10 verdict **confirmatory only**, never pooled, same mathematics | D-068 |
| W4 gate eligibility | exactly **3 predeclared configurations** (shape-causal, confound 0, one per layout) × exactly **5 development seeds** × all six sizes | D-070 |
| W4 gate aggregation | **all three configurations must pass**; no majority vote, no pooled curve; rung recorded with the verdict | D-070 |
| Policy | adaptive counters **reset every episode**; overrides rejected on confirmatory seeds | D-051, D-054 |
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

## 3. Decisions ledger — *moved to its own file*

The records live in **`DECISIONS.md`** (D-037), append-only and complete.
Nothing is archived or condensed — the ledger simply outgrew this file's
500-line paste cap, and the cap is load-bearing: past it, nobody reads this.
The index below carries every id, so a decision cannot go missing from view.

**The student carries `PROJECT_STATE.md` *and* `DECISIONS.md` to Claude.**

| id | date | decision | Sol |
|---|---|---|---|
| **D-001** | 2026-08-13 | Working protocol between Claude and Sol | pending |
| **D-002** | 2026-08-13 | Schedule anchored to Monday 2026-08-17 | pending |
| **D-003** | 2026-08-13 | Sol is continuous, Claude is not — deltas, not re-pastes | pending |
| **D-004** | 2026-08-15 | Submission date is not a constraint; the plan is followed as anchored | n/a |
| **D-005** | 2026-08-15 | The preregistration lives in one file, in code | pending |
| **D-006** | 2026-08-15 | Three identities, with the statistical unit in the data model | pending |
| **D-007** | 2026-08-15 | The Experiment 2A confound conditions are units *within* the sweep, not additional to it | Sol's |
| **D-008** | 2026-08-15 | §8 accumulates until delivered | pending |
| **D-009** | 2026-08-15 | Statistical identity is a registered, versioned field list | Sol's |
| **D-012** | 2026-08-15 | Stage is part of run identity, never of unit identity | finding Sol's |
| **D-013** | 2026-08-15 | The critic feature whitelist is frozen now, not in Week 6 | part |
| **D-014** | 2026-08-15 | Ledger order: a past correction, and the rule going forward | finding Sol's |
| **D-015** | 2026-08-15 | Week 1 audit — seven defects found and fixed | pending |
| **D-016** | 2026-08-15 | Change Record — IDENTITY_VERSION 1 → 2, SCHEMA_VERSION 1 → 2 | pending |
| **D-017** | 2026-08-15 | Gridworld is built against `UnitSpec` directly | pending |
| **D-018** | 2026-08-15 | The configuration sweep is a balanced sample, not the full crossing | pending |
| **D-019** | 2026-08-15 | Thesis prose is drafted by Claude and rewritten by the student | pending |
| **D-020** | 2026-08-15 | The PPO substitution is evidenced, not asserted | pending |
| **D-021** | 2026-08-15 | Week 2 audit — six defects found and fixed | pending |
| **D-022** | 2026-08-15 | The collaboration protocol is machine-checked | pending |
| **D-023** | 2026-08-15 | Sol's delta gets its own file | pending |
| **D-024** | 2026-08-15 | `CLAUDE.md` is Claude's session handoff | pending |
| **D-011** | 2026-08-15 | Deltas carry numbers, not summaries, once results exist | pending |
| **D-010** | 2026-08-15 | The leakage firewall whitelists critic features; it never blacklists metadata | pending |
| **D-025** | 2026-08-16 | Repair validation is the manipulation ladder, and repairs share their baseline's seeds | part |
| **D-026** | 2026-08-16 | Position-causal conditions leave the canonical set | finding Sol's |
| **D-027** | 2026-08-16 | The encoder assigns slots by the descriptor it writes | finding Sol's |
| **D-028** | 2026-08-16 | The protocol tests are hardened where they were decorative | part |
| **D-029** | 2026-08-16 | Q-007 closed — "no explicit statistics", and a tightened negative control | Sol's |
| **D-030** | 2026-08-16 | Q-008 closed — named streams, with pairing preserved inside canonical comparisons | Sol's |
| **D-031** | 2026-08-16 | Intended-class balance is kept, with a predeclared reserve | Sol's |
| **D-032** | 2026-08-16 | The world model predicts the dynamic components, and the primary error is agent position | Sol's |
| **D-033** | 2026-08-16 | One fit, several roles — stage labels must not create compute | finding Sol's |
| **D-034** | 2026-08-16 | Change Record — `CONFIRMATORY_SEED_BASE = 1000`, and everything below it is pilot data | finding Sol's |
| **D-035** | 2026-08-16 | One global failure threshold, calibrated on a balanced reference pool | Sol's |
| **D-036** | 2026-08-16 | Sol is given the generated bundle, never a folder copy | finding Sol's |
| **D-037** | 2026-08-16 | The decisions ledger moves to its own file | Sol's |
| **D-038** | 2026-08-16 | A multi-role fit must resolve to one set of streams | finding Sol's |
| **D-039** | 2026-08-16 | Comparison groups are the clustering every split and interval must respect | Sol's |
| **D-040** | 2026-08-16 | The pilot boundary is enforced, not merely checkable | finding Sol's |
| **D-041** | 2026-08-16 | The bundle selects its own contents | finding Sol's |
| **D-042** | 2026-08-16 | Correction to D-039 — 115 is a worst-case bound, not the effective sample size | Sol's |
| **D-043** | 2026-08-16 | A bundle base must be Sol-*certified*, not merely reviewed | finding Sol's |
| **D-044** | 2026-08-16 | Correction to D-042 — the ICC = 1 boundary is a property of the estimator | Sol's |
| **D-045** | 2026-08-16 | Recorded metadata is validated by type, then by value | finding Sol's |
| **D-046** | 2026-08-16 | The world model, and what in it is an interpretation | pending |
| **D-047** | 2026-08-16 | Q-010 closed — detached auxiliary head, action-conditional losses | Sol's |
| **D-048** | 2026-08-16 | Two tests replaced for asserting less than they claimed | finding Sol's |
| **D-049** | 2026-08-16 | The training loop, and the split that makes early stopping honest | pending |
| **D-050** | 2026-08-16 | The bootstrap ensemble, and what members are allowed to differ in | pending |
| **D-051** | 2026-08-16 | The behaviour policy is stationary across episodes | finding Sol's |
| **D-052** | 2026-08-16 | Three disjoint pools, and a shorter episode | finding Sol's |
| **D-053** | 2026-08-16 | Q-011 closed — episode bootstrap primary, alternatives are sensitivities | Sol's |
| **D-054** | 2026-08-16 | Frozen data-generation procedure, bounded sensitivity scope, a claim withdrawn | finding Sol's |
| **D-055** | 2026-08-16 | Three blockers: repair pairing, evaluation exclusion, confirmatory overrides | finding Sol's |
| **D-056** | 2026-08-16 | The repair split reaches training, and the size guard reaches `collect()` | finding Sol's |
| **D-057** | 2026-08-16 | Pools must belong to the run that trains on them; a third tautological test | finding Sol's |
| **D-058** | 2026-08-16 | W3 Friday's pilot, and the first thing it found | pending |
| **D-059** | 2026-08-16 | Correction to D-058 — what the pilot measured, and what it did not | finding Sol's |
| **D-060** | 2026-08-16 | Week 3 audit — seven defects, and Sol's auxiliary conditional answered | pending |
| **D-061** | 2026-08-17 | The normalising scale is the evaluation pool's, fixed before any mask | Sol's ruling |
| **D-062** | 2026-08-17 | Two fixes that fixed the symptom — MC-dropout inference, and rerunnable evidence | findings Sol's |
| **D-063** | 2026-08-17 | No second trunk; the activation head is a non-decisional diagnostic | Sol's ruling |
| **D-064** | 2026-08-17 | Corrections to D-061 and D-062 — a claim narrowed, and an isolation that was CPU-only | findings Sol's |
| **D-065** | 2026-08-17 | The seeding was wider than the fork — device-local seeding | finding Sol's |
| **D-066** | 2026-08-17 | One bundle file, and a delta that names the commit it describes | finding Sol's |
| **D-067** | 2026-08-17 | Week 3 certified and frozen at `9c0d89d`, with its boundaries | **certified** |
| **D-068** | 2026-08-17 | Change Record — the H1 trend test's reading rule, frozen before it saw data | Sol's ruling |
| **D-069** | 2026-08-17 | W4 Monday — the trend test built, and what it says about the pilot | **certified** |
| **D-070** | 2026-08-17 | Sol's three rulings, and the gate wrapper Tuesday needs | Sol's rulings |

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

### DEV-005 · 2026-08-15 · Three sessions reached Sol late
**Deviation:** the deltas for the environment build, the policy/collector build, and the Week 2 audit were not delivered to Sol at the time. Delta 8 was overwritten; the two following sessions produced no delta at all. All three are consolidated into delta 10.
**Why it is recorded rather than quietly fixed:** the schedule's deviation log exists so that decisions are not reconstructed from memory in Week 18, and a three-session gap in the review record is exactly the kind of thing that would otherwise vanish. Sol reviewed none of that work at the time it was done, so its review of delta 10 arrives after the code was built on — which is the verification lag Sol itself warned about.
**Goes in methodology:** **no** — process, not design. But it belongs in any honest account of how the review protocol actually ran.

### DEV-004 · 2026-08-15 · W2 Mon's confound parameter built during Week 1
**Deviation:** the confound-rate parameter (Schedule W2 Mon) and the three procedural layouts (W2 Tue) were implemented alongside the Week 1 Friday environment rather than in their scheduled cells.
**Why:** they are parameters *of* the generator. Building the generator without them and adding them two days later means writing it twice and risking drift between the config contract and what is actually generated. The W2 Mon acceptance criterion was run as specified and passes.
**Goes in methodology:** **no** — ordering only; no design change.

### DEV-006 · 2026-08-16 · Position-causal conditions are not canonical Experiment 2A
**Deviation:** the five canonical (causal attribute, layout) configurations cover shape and colour only. Position-causal conditions run in the three-seed configuration sweep as a declared robustness configuration, not as canonical Experiment 2A conditions.
**Why:** withholding position removes object *occupancy* rather than an attribute of a visible object — measured 37.5% aliased (observation, action) keys against 10.0% for shape and colour, with the key space 26× smaller. It is a different structural failure, and P§8.2.1's manipulation is about an unrepresentable rule. See D-026.
**Goes in methodology:** **yes** — it bounds what Experiment 2A's result is a result about, and the measurement behind it belongs with the claim.

### DEV-007 · 2026-08-16 · The primary error is agent position on movement transitions
**Deviation:** P§10.2's primary metric — held-out one-step prediction error, `E_t = ||s_{t+1} − f_θ(s_t, a_t)||` — is computed on the **next agent position only**, over **movement-action transitions only**, grid-normalised. Activation error is reported separately as a secondary metric; static components never enter the score.
**Why:** the plan leaves the dimension set of that norm unspecified, and averaging over all of them dilutes the manipulated mechanism ~15-fold and rescales it between families as the observation width changes with withholding. See D-032 for the measurements.
**Goes in methodology:** **yes** — it defines what every reported error number in the thesis means.

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
| Q-011 | Bootstrap granularity is not free for H1: disagreement is its dependent variable. | 2026-08-16 | **Closed** → D-053. Sol: episode-level block bootstrap is the fixed primary method; transition-level is a labelled secondary that may not overturn a verdict or be used to pick the friendlier curve; an initialisation-only ensemble is the better sensitivity because it isolates the source of disagreement |
| Q-010 | The auxiliary loss and the primary task share a trunk. | 2026-08-16 | **Closed** → D-047. Sol: detach the auxiliary head, make both losses action-conditional, remove the weighting knob. **My framing was wrong** — activation was 97.7% of the *loss* but only 16–36% of the *trunk gradient*; loss share is not gradient share |
| Q-009 | What does the world model predict, and is the failure threshold comparable across families? | 2026-08-16 | **Closed** → D-032 (dynamic components; primary error on agent position over movement transitions) and D-035 (one global threshold on a balanced reference pool) |
| Q-008 | Seed independence across units: shared environment streams at the same seed. | 2026-08-15 | **Closed** → D-030. Sol: named streams, independent across sweep units, but common random numbers preserved inside explicitly paired canonical comparisons via a preregistered `comparison_group_id`. `arm` never in the failure-set stream. **Decided, not yet built** — first Week 3 task |
| Q-007 | Plan/schedule contradiction on whether the no-statistics critic variant sees error history. | 2026-08-15 | **Closed** → D-029. Sol: P§12.1 and P§13.5.1 are internally inconsistent; keep the schema, rename the variant **"no explicit statistics"**, and tighten the W13 negative control to exclude `predicted_vs_actual_state` as well |

**For Claude** — things Sol or the student wants implemented, checked or measured.

| # | Item | Raised by | Status |
|---|---|---|---|
| C-001 | File decisions for Q-007, Q-008, the fifteen-condition repair subset and class replenishment; correct the twenty-seed repair schedule and compute estimate; add cross-attribute transition-aliasing tests. Blocking for training, not for implementation | Sol, 2026-08-16 | **Done** → D-025 … D-031, `tests/test_aliasing.py` |
| C-002 | Build the D-030 named-stream module | Sol, 2026-08-16 | **Done** → `src/bu/streams.py`, `tests/test_streams.py` |
| C-004 | File the dynamic-target decision; correct the baseline accounting; mark inspected data as pilot; implement named streams; regenerate the Sol bundle | Sol, 2026-08-16 (delta 11) | **Done** → D-032 … D-036 |
| C-005 | Grouped dataset partitioning for the critic splitter — a comparison group never spans a split | Sol, 2026-08-16 (delta 12) | **Open** — key and report built (D-039); splitter is W6/W11 |
| C-006 | Week 5 MDE simulation: reproduce the **actual paired balanced-accuracy estimator** — real group sizes and class membership, group-preserving partitions, unit weights, paired critic-vs-baseline predictions, ICC grid — and validate against the analytic result at ICC = 0 **and** ICC = 1 | Sol, 2026-08-16 (deltas 12–14) | **Open** — fully specified in D-044; due W5 Thu |
| C-007 | Pass `require_confirmatory=True` in threshold calibration, repair acceptance and every critic loader as each is built | Sol, 2026-08-16 (delta 12) | **Open** — guard built (D-040); call sites are W4–W11 |
| C-008 | **Build the confirmatory runner**, which must own: episode bootstrap only, registered configuration and arm, matching pools and run identity, confirmatory seed policy, complete run records. `bootstrap_episodes()` + `train(train_index=…)` still bypasses the `train_ensemble` guard | Sol, 2026-08-16 (cert of 2875e60) | **Open** — blocks confirmatory execution and repair validation |
| C-009 | Runner hardening: reject `source_unit is None` in `assert_pools_match()` rather than ignoring it, and check each dataset's `stream_version` against the run's | Sol, 2026-08-16 | **Open** — non-blocking; current `collect_pools` output already satisfies both |
| C-003 | Predeclare the D-031 reserve draw order | Sol, 2026-08-16 | **Open** — due W5 Thu with the MDE simulation |
| C-010 | **W4 runner call-site invariants**, required tests: build the `NormalisationScale` from the full movement evaluation pool **before** the failure mask exists, and reuse **that object** for the whole-pool and masked statistics; and select **one immutable attempt** explicitly rather than loading a tree. Exact reproduction of the pilot does not validate the masked call site (D-064) | Sol, 2026-08-17 | **Open** — blocks W4 Fri |

---

## 7. Session log — *append-only, newest last*

Entries before this one are in `PROJECT_STATE_ARCHIVE.md`; **20 archived, 1 kept here** — Week 3's six close entries were archived when it was certified and frozen at `9c0d89d` (D-067). Nothing is condensed; the archive is complete.

### 2026-08-17 (W3 certified) · Week 3 frozen at `9c0d89d` · Claude
**Did:** Sol certified `9c0d89d`, covering the complete chain from `2875e60` through the pilot, the audit and D-061 … D-066. **Week 3 is closed and frozen** (D-067). Filed the certification, its accepted conclusions and — the part that matters more — its **boundaries**, which travel with it and are not relaxed by it: no confirmatory execution, no repair validation (C-008, C-009), **no masked failure-set analysis until C-010 exists, required before W4 Friday**, and MC-dropout rung 3 needs an explicit architectural decision because `WorldModel` has no dropout. Cleared Sol's non-blocking housekeeping: `CLAUDE.md` said 440/1 and now says 442/2, alongside the new base and status.
**What the six-review close actually cost, and where.** Every finding was verified before anything changed and every one stood. But only two were code defects reachable by a user; **three were about claims rather than code** — an invariance that does not hold for a vector, an enforcement a type cannot provide, and an isolation that held only on the hardware it was tested on — and one was **packaging**, where the right bundle existed and the wrong one was sent. The sentences were consistently more expensive to get right than the code was.
**Standing corrections now live in `CLAUDE.md`:** restoring state is not fixing a mechanism; verify a finding's *route*, not just its conclusion; and a test written against the machine it runs on can pass in the one configuration where the defect cancels.
**Result:** 442 tests, 2 skipped. **Zero GPU-hours** of the ~110–145 budgeted.
**Next:** W4 Mon — the trend test. Read it knowing the pilot's disagreement curve peaks at N=250, which is what a rank correlation over six sizes is most sensitive to.

---

### 2026-08-17 (W4 Mon) · The trend test, under a rule frozen before it saw data · Claude
**Did:** Sol certified `7dbcd32` as the documentation continuation — use it as the next `BASE`; the frozen *implementation* stays `9c0d89d` — and **authorised W4 Mon under a fully specified reading rule** (D-068). Built `src/bu/stats/trend.py`: one function for the W4 gate and the W10 verdict, 22 tests covering every clause Sol required plus the partition boundary.
**The rule was frozen first, and that is the point.** Spearman's rho over **all six** registered sizes, negative expected, **pass only if the whole 95% interval is below zero**, undefined or constant fails, out-of-order points carry no separate veto. The interval is an **exact** paired seed-block bootstrap — 27 or 3,125 ordered tuples enumerated, **no RNG at all**, quantile method declared in code. Removing N=100 or N=250, smoothing, or switching to Kendall are each forbidden by name.
**On the pilot** (development seeds — Schedule W4 Mon's criterion, **not** the gate): **rho = −0.9429, 95% CI [−0.9429, −0.8286], PASS.** Sol's prediction held exactly: the N=250 peak costs **one** of fifteen pairwise inversions, weakening rho from −1.0 naturally, with nothing removed.
**The limitation is the more useful result.** With three seeds the 27 resamples take only **two** distinct values (−0.9429 ×20, −0.8286 ×7), so the "95% interval" *is* the full support — its narrowness is a property of three consistent seeds, not evidence of precision. At five seeds the support is 3,125 and the quantiles mean something. Flagged for Sol before Tuesday, because if gate day 1 also runs at three seeds it inherits the same coarseness.
**One loophole closed while testing.** The size grid is now required to be exactly the six registered sizes. Without it the grid is a keyword argument, and a five-point statistic over a trimmed grid is indistinguishable from the registered one in every artefact carrying it — the "drop the awkward small end" move arriving through a parameter rather than a decision. Found because the first version of that test passed for the wrong reason.
**Result:** 442 → 464 tests, 2 skipped. **Zero GPU-hours.**
**Next:** W4 Tue, gate day 1 — five seeds across three configurations, recording the verdict **and the rung**.

---

### 2026-08-17 (W4 Mon closeout) · Three rulings, and the gate wrapper Tuesday needs · Claude
**Did:** Sol **certified `a84cf6c`** as the W4 Monday trend-test implementation and ruled on all three open questions (D-070). Built `src/bu/stats/gate.py` — the wrapper that makes a gate verdict *authorised* rather than merely computed.
**Ruling 1 — do not move the statistical rule after seeing the two-atom interval.** Separate the *statistical result* from *gate eligibility* instead: the three-seed pilot satisfies the frozen rule and cannot be a gate verdict. The wrapper requires exactly three predeclared configurations × exactly five development seeds × six sizes, and **rung 0 passes only if all three configurations pass** — no majority vote, no pooled curve, because configuration sensitivity is itself a reliability failure. The three configurations are predeclared with their **18 exact `config_id`s frozen as golden values**: a configuration spans six units, not one, and deriving the ids at run time would let an identity change silently redirect the gate (the D-016 lesson).
**Ruling 2 — keep the exact six-size refusal.** No legitimate subset caller exists for the registered statistic; an exploratory subset analysis must be a separately named descriptive function returning no `TrendResult` and no verdict.
**Ruling 3 — a correction to my reasoning, not the code.** Undefined replicates still fail closed and are never dropped — dropping them would condition the distribution on the statistic being defined and could **manufacture** a directional interval. But I had justified it by calling a flat curve "the strongest possible evidence against a trend", and Sol is right that it can equally come from **cancellation between opposing non-constant curves**. A test now builds exactly that: slopes −0.1, −0.3, +0.2 where one resample cancels to flat, **the point estimate is a perfect −1.0, and the result still fails** — which is why dropping the undefined replicates would have been dangerous rather than merely untidy.
**Result:** 464 → 483 tests, 2 skipped. **Zero GPU-hours.**
**Next:** W4 Tue, gate day 1 — 90 ensembles / 450 fits, the first real compute. Ask before starting it.

## 8. → TO SOL — *moved to its own file*

The delta Sol receives lives in **`DELTA_TO_SOL.md`** (D-023). It was moved out
because consolidating four sessions pushed this file past its 500-line paste
cap, and the two files have different audiences anyway: this one is Claude's
reconstruction of state, that one is Sol's feed.

It also removes an instruction that was easy to get wrong. "Paste §8" meant
scrolling to find a section boundary; "paste `DELTA_TO_SOL.md`" does not.

**Current status:** see the delivery flag at the top of `DELTA_TO_SOL.md`.
