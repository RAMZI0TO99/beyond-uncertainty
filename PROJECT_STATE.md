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
| **Last updated** | 2026-08-20 |
| **Updated by** | Claude |
| **Phase** | Phase A — infrastructure |
| **Current week / day** | **Sol ruled on deltas 39–42: PARTIAL ACCEPTANCE, and `25fd2c2` is explicitly NOT certified** (D-089). Certified base remains **`ca545ed`**. Sol's entire required closeout is **built** (D-085 … D-090): paired permutation with its criterion frozen first, one model per repaired arm, seed-specific masks, evidence contract v2 with v1 grandfathered, the rulings filed, and the **W4 Friday threshold runner built and NOT executed**. **Two rulings now block everything**: the acceptance model's conservatism, and W4 Friday's percentile plus reference-model definition. Week 1 Monday was 2026-08-17 — roughly **three** weeks ahead of calendar (DEV-002) |
| **Next gate** | **Gate 1 SIGNED OFF 2026-08-20 — FAIL** on the MDE condition (D-098); next is **Gate 2**, Week 10 Saturday = **2026-10-24** |
| **Repository** | [`RAMZI0TO99/beyond-uncertainty`](https://github.com/RAMZI0TO99/beyond-uncertainty) — **private**. See *Revision* row for the exact state |
| **Revision** | `main` — HEAD at the end of §7's latest entry, tree **clean**. **Certified base: `ca545ed`** — Sol certified the stored W4 Tuesday result on 2026-08-18. The chain: `9c0d89d` (Week 3 implementation, frozen) → `7dbcd32` (docs) → `a84cf6c` (W4 Mon trend test) → `2efad258` (W4 Tue gate + evidence contract) → `ca545ed` (the stored result). Three intermediate commits were reviewed and explicitly **not** certified; `2efad258` subsumes them. **Set `BASE=ca545ed` for the next bundle** (D-043, D-067, D-075) |
| **Tests** | **672 passing, 2 skipped, 1 xfailed** (the two GPU tests skip where no device exists). **The xfail is deliberate and load-bearing**: D-085's frozen calibration criterion is *not* met, and it is marked `xfail(strict=True)` so the open failure stays visible in the suite rather than being loosened away. If it ever passes, the suite says so |
| **Compute used** | **0 GPU-hours** · first real spend: **450 CPU fits in 4 m 52 s** (W4 Tue rung 0) of ~110–145 budgeted (trigger ≈ 120, P§14.3). Every fit so far ran on **CPU**. Two sub-second GPU tests now run in the suite (~68 MiB) to cover the CUDA RNG fork and seeding — the student's other workload has finished and the card is at ~0.9/16 GB |
| **Design scale** | 300 units (the statistical unit) in **240 comparison groups** · unit-level class balance **150/150**, group counts 125/115 · **8,197 model fits** vs P§14.2's ~8,700 |

**Hypothesis status**

| | Claim | Status | Decided at |
|---|---|---|---|
| H1 | Ensemble disagreement tracks estimation failure | **W4 gate PASSED at rung 0, certified** on development seeds (D-074, D-075); hypothesis not tested | Gate check W4 **done**, verdict W10 Mon |
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
6. **W4 Tue — DONE. Rung 0 PASSES** (D-074). All three configurations, on the certified commit with a clean tree: **rho = −0.9429** for every one, intervals [−0.9429, −0.9429] (uniform), [−0.9429, −0.8286] (clustered), [−0.9429, −0.9429] (sparse). 90 ensembles / 450 fits in **4 m 52 s** on CPU; `recompute()` exact; suite green after. Per Sol the ladder **stops here** — rungs 1 and 2 are not run. **Read the interval correctly:** the exact bootstrap is discrete with 2–3 atoms, and uniform and sparse are degenerate only just (second atom at 1.63% and 2.14% against a 2.5% threshold). The *verdict* is unaffected — every atom is far below zero — but the width is not a precision claim. **The N=250 peak reproduces in 14 of 15 curves**; clustered seed 4 peaks at N=500 instead. Disagreement is **not** monotone in dataset size; the test passes because Spearman tolerates one inversion.
7. **W4 Fri — NEXT, and blocked on Sol.** Threshold calibration is the first cell where a failure mask exists, so the first that can violate the D-061 scale rule. **C-010 is now built** (D-076) — `ScaledEvaluation.from_pool` takes no mask, so the scale precedes any mask structurally — but Sol has not reviewed it (delta 40), and W4 Friday **permanently freezes a §2 constant**. Wednesday and Thursday went to C-006, C-009 and C-010; per Q-004 the gain from the stopped ladder goes to review and obligations, **never** to scope.

**GATE 1 IS SIGNED OFF: FAIL** (D-098, §5). Reliability **PASS** (rung 0,
certified). Compute **PASS**, contingent on one model per repaired arm.
Permutation calibration **PASS** — repaired this session by the D-094 Change
Record. Five-point MDE **FAIL**, and Sol was explicit this must **not** later be
renamed a pass now that condition 3 is fixed: the MDE failure is independent of
it. **This is not the condition-1 pivot** — H1's machinery works; what failed is
the design's power to resolve five points in H3, a sample-size limit. The
unchanged **300-unit design continues** under a recorded power limitation, with
**Direction C authorised**. Expansion to the 1,500–2,000 held-out units five
points would need is refused as incompatible with registered scope. The 18–22
table stays **uncertified and optimistic** until the simulation uses H3's final
group-level inference with its null size validated against .05.

**Two things the thesis must carry, recorded now because a reset loses them** (D-075):
- **Never print a zero-width interval bare.** `[−0.9429, −0.9429]` reflects **quantile discreteness, not zero sampling uncertainty** — the bootstrap distribution has only 2–3 distinct values because Spearman over six sizes has highly discrete support. Sol's sentence for the results text is quoted verbatim in D-075, and the atom/mass table must travel with it.
- **Clustered seed 4 is reported, not investigated.** 14 of 15 curves peak at N=250; that one peaks at N=500 with N=250 below N=100. Sol ruled: no extra seeds, no smoothing, no rerun, no estimator change — investigating now would be post-result exploration. Substantive confirmation waits for W10's confirmatory seeds.

**No open questions.** Q-011 closed by D-053 (episode bootstrap primary). Q-010 closed by D-047: the auxiliary head is detached, both losses are action-conditional, and three unrecorded result-affecting knobs are gone. Position loss improved 0.002242 → 0.000931 at the same budget. **D-047's open item is closed** by D-063: the real loop never closed the gap at any size or member, Sol ruled against a second trunk, and the detached head is now a **non-decisional diagnostic** — barred from the trunk, from early stopping and checkpoint selection, from the failure set, from repair labels and from the critic's residual.

**Blocked on: Sol, and nothing else.** There is **no unblocked work left**. Waiting: **W4 Friday** (the percentile and the reference-model definition, D-090 — and it permanently freezes a §2 constant); the **Gate 1 verdict**, whose permutation condition turns on the acceptance model's conservatism (D-086); **repair validation**, now that C-008 and D-087 are done; and anything built on the **predeclared reserve order** (D-092), which is a predeclaration and so goes to Sol before it is used. Still correctly out of scope: **MC-dropout rung 3**, deliberately unfrozen and needing an architectural decision because `WorldModel` has no dropout, and **critic splitting** (C-005), which is W6/W11 work.

**Standing watch — Sol's tripwire on D-001.** Sol endorsed the role split conditionally, and DEV-005 was a hit against that condition. Sol weighed it on 2026-08-16 and **kept the split**, on the grounds that the mechanised protocol tests improve the arrangement more than reassigning implementation would. The watch stays live: consequential design decisions go into a delta **and get delivered** before dependent code is built on them, and Claude flags any decision it believes meets that bar at the moment of making it. D-030 is the current test of that — decided, filed, and deliberately left unbuilt.

---

## 2. Frozen constants — *changing any of these requires a §3 Change Record and a Sol review*

These are the preregistered quantities. They are fixed **before** data collection and are not revised after seeing data. Their whole purpose is to be un-adjustable later.

| Constant | Value | Source |
|---|---|---|
| Data-repair budget | **10×** the failure-condition dataset, same generating process | P§7.2 |
| Repair acceptance | Negative fixed effect, 95% CI excluding zero, **and** ≥ **20%** relative reduction in mean per-transition error | P§7.3 |
| Acceptance test | **Equal-seed mean paired difference, t interval on `n_seeds − 1` df**; equal-seed denominator; **no fallback** — fails closed. *Changed under D-094 and D-100, Sol-authorised, before any data was seen* | P§7.3, D-094, D-100 |
| H3 equivalence margin | **±5 percentage points** balanced accuracy | P§4.2 |
| Seeds — H1/H2 conditions (Exp 1, 2A, 2B) | **5** | P§14.2 |
| Seeds — canonical repair validation | **20** | P§7.3, P§14.2 |
| Seeds — configuration sweep & its repairs | **3** | P§14.2 |
| Seeds — ablations | **5** | P§14.2 |
| Seeds — threshold calibration | **5** — added under D-097, Sol-authorised, before any data | S§W4 Fri, D-097 |
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
| W4 gate evidence | every cell bound to its source run: golden `config_id`, implied `run_id`, stage, partition, rung training spec, **one attempt and one commit**; no cell missing, duplicated or unregistered | D-071 |
| Ladder rung 0 | ensemble · `ensemble_size` **5** · `bootstrap_ratio` **1.0** · episode | D-071 |
| Ladder rung 1 | ensemble · `ensemble_size` **10** · `bootstrap_ratio` **1.0** · episode | D-071 |
| Ladder rung 2 | episode **subbagging** · `ensemble_size` **10** · `bootstrap_ratio` **0.5** — *lowered*, see the P§11.3 semantic correction | D-071 |
| Ladder rungs 3–4 | secondary estimators; parameters **deliberately unfrozen** until immediately before execution; `RungSpec.for_rung(3)` raises | D-071 |
| Rung training spec | the **complete** `TrainConfig` is frozen per rung — `lr`, `batch_size`, `max_epochs`, `patience` too, not only the two a rung varies | D-072 |
| Evidence contract | version **1**: canonical `Config` per run, derived identities, complete `TrainConfig`, granularity attested in the run record, evaluation-pool digest, normalisation, member records, bound source row, artefact digests | D-072 |
| Attempt identity | rung + rung-spec hash + a digest of the run-record, **member-record, row and evaluation-pool** digests; never the directory label, and never the start records alone | D-072, D-073 |
| Schema versions | `EVIDENCE_CONTRACT_VERSION`, `MANIFEST_VERSION`, `METRIC_SCHEMA_VERSION` live in `bu.stats.gate`, **not** in `constants.py` — they are compatibility versions that must stay evolvable, the opposite of a preregistered quantity | D-073 |
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
| **D-071** | 2026-08-18 | Sol's two blockers — the verdict bound to its evidence, and the ladder frozen before rung 0 runs | Sol's blockers |
| **D-072** | 2026-08-18 | The evidence contract — the trust boundary reaches execution, and the W4 runner that emits it | Sol's finding |
| **D-073** | 2026-08-18 | The closeout — six advertised checks that were not being performed; architecture accepted | Sol's closeout |
| **D-074** | 2026-08-18 | W4 Tuesday — rung 0 passes on all three configurations, and what the interval actually is | Result |
| **D-075** | 2026-08-18 | Sol's rulings on the result, and the wording the thesis must carry about zero-width intervals | Sol's rulings |
| **D-076** | 2026-08-18 | C-010 built — the masked call site, and a reproducibility defect found while proving it neutral | Obligation |
| **D-077** | 2026-08-18 | C-009 — the pool guard's two opt-outs closed | Sol's item |
| **D-078** | 2026-08-18 | C-006 built — and the MDE does **not** clear the five-point margin | **Result — Gate 1 risk** |
| **D-079** | 2026-08-18 | W5 Tue/Wed — the acceptance test and its permutation null, calibrated | Deliverable |
| **D-080** | 2026-08-18 | A recovered W5 Monday repair path, found uncommitted (DEV-005 class) | Recovery |
| **D-081** | 2026-08-18 | W5 Friday — the figure-regeneration command, every figure from logs | Deliverable |
| **D-082** | 2026-08-18 | Audit of unreviewed stats — MDE power test anti-conservative (report); acceptance seed intercept missing (fixed) | **Audit** |
| **D-083** | 2026-08-18 | Audit continued — streams and identities sound; latent confound_rate float-identity risk | **Audit** |
| **D-084** | 2026-08-18 | Audit closeout — detached head verified exact; scope and verdict (foundations sound) | **Audit** |
| **D-085** | 2026-08-20 | The permutation null's calibration criterion, frozen before the corrected null exists | Sol's ruling |
| **D-086** | 2026-08-20 | The corrected permutation null, and the defect it had been hiding | **Finding** |
| **D-087** | 2026-08-20 | Sol's two repair blockers — one model per repaired arm, seed-specific masks | Sol's blockers |
| **D-088** | 2026-08-20 | Evidence contract v2 — threading required, v1 grandfathered, and a pinning gap | Sol's ruling |
| **D-089** | 2026-08-20 | Sol's rulings on deltas 39–42 filed — MDE is FAIL; `ca545ed` stays the base | **Sol's verdict** |
| **D-090** | 2026-08-20 | The W4 Friday threshold runner — built, not executed, two choices left open | **For Sol** |
| **D-091** | 2026-08-20 | C-008 — the confirmatory runner, and the bypass it was asked to close | Deliverable |
| **D-092** | 2026-08-20 | C-003 — the reserve draw order, predeclared before it is needed | **Predeclaration** |
| **D-093** | 2026-08-20 | C-007 at the repair-acceptance call site; provenance note corrected | Sol's item |
| **D-094** | 2026-08-20 | **CHANGE RECORD** — acceptance model gains the pairing; literal spec found degenerate | **Sol-authorised** |
| **D-095** | 2026-08-20 | Sol's consumer-side repair refusals, and the reserve predeclaration guards | Sol's items |
| **D-096** | 2026-08-20 | C-008 closed — one fit, both products; single-model arms have no disagreement | Deliverable |
| **D-097** | 2026-08-20 | **CHANGE RECORD** — `threshold_calibration` stage; runner rebuilt; balancing limit found | **For Sol** |
| **D-098** | 2026-08-20 | **GATE 1 — FAIL**, signed off on Sol's ruling; not a pivot | **Sol's verdict** |
| **D-099** | 2026-08-20 | Audit of W4/W5 — probed; two findings on the threshold's balancing rule | **Audit** |
| **D-100** | 2026-08-20 | Sol's delta-45 corrections; D-094's theoretical claim narrowed | Sol's items |

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

### Gate 1 — signed off 2026-08-20, ahead of its 2026-09-19 date — **VERDICT: FAIL**

**Sol's ruling on deltas 43–44, recorded here so it cannot be softened by a reset.**

| # | condition | verdict |
|---|---|---|
| 1 | Reliability gate passed, rung recorded | **PASS** — rung 0, certified at `ca545ed` (D-074, D-075) |
| 2 | Compute estimate within budget | **PASS** — *contingent* on one model per repaired arm (D-087). At the old default the design cost 14,885 fits against ~8,700, i.e. 1.71× |
| 3 | Permutation null shows the test is calibrated | **PASS** — after the D-094 Change Record. 200 permutations, statistical-only 5–7/200 against an admissible [1, 10]; full rule 0/200. Calibrated at **every** pairing strength tested |
| 4 | MDE resolves a 5-point difference on `min(N₀, N₁)` | **FAIL** — 18–22 points at the scheduled held-out counts, and those numbers are *optimistic* (D-078, D-082, D-089) |

**Gate 1 FAILS on condition 4, and would fail regardless of condition 3.** Sol was
explicit that this must not later be renamed a pass now that the permutation
calibration is repaired: the MDE failure is independent of it.

**What Sol ruled, and what happens next.** Do **not** expand to the 1,500–2,000
held-out units that clearing five points would need — that is incompatible with
the registered scope and budget. **Preserve the 300-unit design.** Record that H3
can detect only comparatively large effects and may be **inconclusive around ±5
points**, and never claim equivalence the final interval cannot resolve.
**Direction C is an authorised thesis outcome.** The project continues on the
unchanged design under an explicit, recorded power limitation — rather than
manufacturing a pass by moving the margin or expanding scope.

**This is not the pivot of condition 1.** The reliability gate passed; H1's
machinery works. What failed is the design's power to resolve a five-point
difference in H3, which is a sample-size limit no engineering fixes.

**The exact 18–22 table is uncertified and explicitly optimistic** (D-089): it
uses a Wald `1.96 × SE` rule where D-044 registers a group-bootstrap percentile,
and its measured null rejection is 6.1–9.2%. Before any *exact* MDE is reported,
the simulation must use the same final group-level inference H3 will use, with
its null size validated against .05 under Monte-Carlo uncertainty.

### Gate 1 — original criteria, as written at the start
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
| ~~C-006~~ | Week 5 MDE simulation: reproduce the **actual paired balanced-accuracy estimator** — real group sizes and class membership, group-preserving partitions, unit weights, paired critic-vs-baseline predictions, ICC grid — and validate against the analytic result at ICC = 0 **and** ICC = 1 | Sol, 2026-08-16 (deltas 12–14) | **Done** → D-078. Both validations pass. **The MDE does not clear five points** — 18–22 pp at the scheduled held-out counts. Awaiting Sol (delta 41) |
| C-007 | Pass `require_confirmatory=True` in threshold calibration, repair acceptance and every critic loader as each is built | Sol, 2026-08-16 (delta 12) | **Threshold calibration (D-090) and repair acceptance (D-093) done**; critic loaders remain, W6–W11. Tied to the *stage*, never a boolean — a probe labels itself `pilot` rather than exempting itself |
| ~~C-008~~ | **Build the confirmatory runner**, which must own: episode bootstrap only, registered configuration and arm, matching pools and run identity, confirmatory seed policy, complete run records. `bootstrap_episodes()` + `train(train_index=…)` still bypasses the `train_ensemble` guard | Sol, 2026-08-16 (cert of 2875e60) | **Done** → D-091 (guard) and **D-096** (integration): bound to registered obligations, frozen TrainConfig, K=1 repaired arms, dirty-tree refusal, and one fit producing both the record and the paired per-transition errors |
| C-009 | Runner hardening: reject `source_unit is None` in `assert_pools_match()` rather than ignoring it, and check each dataset's `stream_version` against the run's | Sol, 2026-08-16 | **Done** → D-077. Both were opt-outs, and adding them broke no test — nothing had exercised either path |
| C-011 | ~~**One immutable attempt directory per rung.**~~ `ensemble_size` and `bootstrap_ratio` are non-identity, so a rung-1 run has the *same* `run_id` as the rung-0 run it replaces and `write_run_record` will refuse to overwrite it. Fail-closed and correct, but it must be settled before Wednesday rather than found as a `FileExistsError` mid-run | Claude, 2026-08-18 (D-071) | **Done** → D-072, at the finer granularity Sol ruled: one directory per **rung-spec hash**, `runs/w4_gate/rung-NN-<hash>/attempt-NNN/` |
| ~~C-003~~ | Predeclare the D-031 reserve draw order | Sol, 2026-08-16 | **Done** → D-092, committed as `reserve_order.json`: 231 units, 120/111 by intended class. The obvious derivation was wrong — `select_sweep` is a superset as it grows but **not prefix-stable**, so the order comes from the set difference per step |
| C-010 | **W4 runner call-site invariants**, required tests: build the `NormalisationScale` from the full movement evaluation pool **before** the failure mask exists, and reuse **that object** for the whole-pool and masked statistics; and select **one immutable attempt** explicitly rather than loading a tree. Exact reproduction of the pilot does not validate the masked call site (D-064) | Sol, 2026-08-17 | **Done** → D-076: `ScaledEvaluation` is the call site — `from_pool` takes no mask so the scale precedes any mask structurally, `masked()` reuses that identical object, and `select_attempt()` refuses to guess. Awaiting Sol in delta 40; **W4 Fri must not run before that** |

---

## 7. Session log — *append-only, newest last*

Entries before this one are in `PROJECT_STATE_ARCHIVE.md`; **34 archived, 1 kept here** — Week 3's six close entries were archived when it was certified and frozen at `9c0d89d` (D-067). Nothing is condensed; the archive is complete.

*(W3 certification through the W4 Tuesday gate rounds — the trend test, Sol's two blockers, and the evidence contract — moved to `PROJECT_STATE_ARCHIVE.md` when this file passed its 500-line paste cap. Six entries, 2026-08-17 to 2026-08-18; the decisions they produced are D-068 … D-072 and remain indexed in §3.)*

*(The W4 Tuesday gate result, its certification closeout, and the W4 Wednesday obligations — four entries, 2026-08-18 — were archived on 2026-08-20 for the same reason. They produced D-071 … D-077, all indexed in §3. W4 Tuesday is certified at `ca545ed`.)*

### DEV-008 · 2026-08-18 · The MDE simulation's significance level is not in the plan
**Deviation:** P§10.7 fixes power at eighty percent but does not state a significance level. The C-006 simulation uses **α = 0.05, two-sided**.
**Why:** consistency with every other interval in the project — repair acceptance is a 95% CI excluding zero (P§7.3), and the H1 trend test is a 95% interval (D-068). A one-sided test would shrink the MDE by about 11% and change no conclusion.
**Goes in methodology:** **yes.** It is an assumption the reported MDE depends on, and the MDE is a Gate 1 condition. Stated rather than absorbed silently.

*(W4 Thursday's MDE and the W5 Mon/Tue/Wed/Fri cells — four entries, 2026-08-18 — were archived on 2026-08-20 when Gate 1 was signed off, which supersedes them. They produced D-078 … D-081, all indexed in §3.)*

### 2026-08-20 (W5 closeout) · Sol's rulings actioned, and a null that was hiding a defect · Claude

**Sol returned PARTIAL ACCEPTANCE on deltas 39–42 and did NOT certify `25fd2c2`.** The certified base remains **`ca545ed`**. Delivery integrity checked both ways first: the delta and bundle SHA-256s Sol quoted match the bytes on disk exactly, so Sol reviewed what was shipped. Every finding was verified before anything changed, and all held — two were **worse** than stated.

**Did, in Sol's required order** (D-085 … D-090):
1. **Froze the calibration criterion before writing the corrected null** (D-085), so its provenance is history rather than a claim. Admissible counts computed in advance: statistical-only **k ∈ [4, 16]** of 200, full rule **k ∈ [0, 3]**.
2. **Paired within-seed permutation** (D-086). The withdrawn global shuffle corrupted **48.4%** of seeds (48.72% analytic) and **every** permutation broke at least one seed — the 0/200 and 5.5% figures were never measurements of the registered design.
3. **One model per repaired arm**, **seed-specific failure masks** (D-087).
4. **Evidence contract v2** — threading required and cross-checked, **v1 grandfathered** so certified `attempt-001` is untouched (D-088).
5. **Sol's rulings filed**, Gate 1's standing recorded (D-089).
6. **W4 Friday threshold runner built and NOT executed** (D-090), returned for the pre-execution review Sol asked for.

**THE FINDING — two errors were cancelling.** The corrected null exposed that the registered P§7.3 model has **no transition-level pairing term** while the comparison is paired transition-by-transition, so its SE is **1.51×** the true paired null spread and the test is **conservative**. The broken permutation had been hiding this exactly: breaking the pairing inflated the null's spread by **1.46×**, cancelling the over-wide SE to a reassuring ratio of **1.03** that passed its bound comfortably. Statistical-only rate **0/200, CI [0.000%, 1.828%]** — D-085 requires it to contain 5%. **Not fixed:** the acceptance model is a §2 frozen constant, so it is a Change Record and Sol's ruling. Marked `xfail(strict=True)` so the failure stays visible, with the 1.51× pinned by a test. Measured on synthetic data whose generator pairs the arms almost perfectly — the **direction** is established, the **magnitude on real data** is not.

**Also found:** the runner **recorded** interop threads but never **pinned** them (D-088); and repaired arms at the default K=5 would cost **8,360 fits against 1,672 budgeted**, taking the design to **14,885 vs ~8,700 — 1.71× budget**, which is the Gate 1 compute condition Sol had just marked PASS (D-087).

**A provenance note.** `config.py`, `gate.py` and `tests/test_audit_regressions.py` were found **modified mid-session** — after this session's last edit and last green run — implementing Sol's items 4 and 6. **I did not author them** and `list_sessions` showed no other session. They left the suite **red at 24 failures** (v2 required a `threading` field nothing emitted). I verified them by test rather than by reading, completed the production emitter, the interop pinning and the whole v2 refusal suite, and the tree is green again. Recorded because unattributed edits in a working tree are the DEV-005 class of hazard.

**Tests:** 627 → **672 passing**, 2 skipped, **1 xfailed** (D-085's unmet criterion, deliberately visible). **Compute: zero.** No fit spent, no attempt re-run, no data seen.

**Next:** deliver delta 43 with one clean bundle against `ca545ed`. Two questions must reach Sol — the acceptance model's conservatism, and W4 Friday's percentile and reference-model definition. **W4 Friday still must not execute.**

### 2026-08-20 (W5 closeout, continued) · C-008 and C-003, the last unblocked work · Claude

**Cleared the two open items that needed no ruling**, so that everything now waiting is genuinely waiting on Sol.

**C-008 — the confirmatory runner** (D-091). Sol raised this at `2875e60`'s certification and named it again in the delta-42 ruling as a precondition for any repair-validation evidence. The bypass `train_ensemble` used to **confess in its own docstring** — `bootstrap_episodes()` + `train(train_index=…)` — is closed at the **resampling site**, with `seed` now a *required* argument there: a caller cannot resample without declaring whose seed it is. That candid docstring is why the hole was findable at all. The change immediately caught real misuse: `tests/test_ensemble.py` had been exercising transition and initialisation-only bootstraps on **seed 1000, a confirmatory seed**, and nothing had objected. The runner has **no `granularity` parameter at all** — a parameter accepting one value invites a caller to pass another. A test caught `metric_schema_version` missing from the emitted record, which would have left a confirmatory run unverifiable by the evidence contract.

**C-003 — the reserve draw order** (D-092), committed as `reserve_order.json`: **231 units, 120 of intended class 0 and 111 of class 1.** The obvious derivation was wrong and would have been silently wrong: `select_sweep(k)` is a strict **superset** of `select_sweep(k−1)` but is **not prefix-stable**, so reading a draw order off list position produces a plausible, deterministic, incorrect commitment. The order comes from the **set difference at each step**, which is stable; admitted units alternate intended class, giving a balanced per-class order. `next_reserve_units(intended_class, n)` takes a class and a count **and nothing else**, so D-031's "without inspecting critic performance" is a property of the signature rather than a rule to remember, and over-drawing is refused because extending a reserve after seeing a shortfall is choosing rather than drawing.

**Tests:** 672 → **705 passing**, 2 skipped, 1 xfailed. **Compute: zero** beyond one tiny synthetic fit in a temp directory — no registered run, no logged result, no data seen.

**There is now no unblocked work left.** W4 Friday, the Gate 1 verdict, repair validation and anything built on the reserve order all wait on Sol.

### 2026-08-20 (W5 closeout, C-007) · The seed policy reaches repair acceptance · Claude

**C-007's widest remaining hole closed** (D-093). Repair acceptance had **no** confirmatory guard, so the repair path could produce registered repair-validation evidence on development seeds — and repair acceptance is where every label in the thesis is created. Guarded at **both** layers: `evaluate_arm` before the fit, and `acceptance_inputs` where the label actually comes into existence, since evaluations can be constructed without the producer. Tied to the **stage**, not a boolean: a probe must label itself `pilot` rather than exempt itself, because D-077 already had to close two opt-outs that existed for exactly that reason.

**Provenance correction.** The student reports that **an earlier session was interrupted**, which is the likely source of the three files found modified mid-session and recorded as unexplained in the previous entry and in delta 43. Recorded as *reported*, not verified — `list_sessions` returns nothing even including archived sessions. The classification is unchanged and sharpened: an interrupted session leaving uncommitted work is exactly the DEV-005 / D-080 pattern.

**Tests:** 705 → **709 passing**, 2 skipped, 1 xfailed. **Compute: zero.** Still no unblocked work left.

### 2026-08-20 (W5 Sat) · Sol's whole ruling actioned; Gate 1 signed off FAIL · Claude

**All seven of Sol's closeout items done, plus the audit** (D-094 … D-099). Every finding verified before actioning; Sol's own corrected D-085 target checked independently and confirmed.

**Two Change Records, both before any data was seen.** **D-094** — the acceptance model gains the pairing. **The literal specification turned out to be degenerate**: a seed intercept, an episode component and a transition-within-episode component are all constant within a pair, so all three cancel in the contrast and become unidentifiable — `LinAlgError: Singular matrix` at 250 and 1,000 pairs, and 231 s where it fits, which would make 200 permutations a 13-hour run. Reduced to what *is* estimable it treats pairs as **iid**, blind to seed-level effect variation, with SE up to **8.7× too small**. That would have swapped a 1.51× conservative test for an anti-conservative one — the worse direction, since a narrow interval manufactures repairs out of seed noise and those become labels. Implemented instead: pair first, seed stays the replication level, t on n−1 df — **7 ms against 231 s**, and calibrated at every pairing strength (5–7/200 against an admissible [1, 10]). **D-097** — a distinct `threshold_calibration` stage, because `TrainConfig` is not in `run_id` and reusing `exp1` would have collided identities.

**Gate 1 signed off: FAIL** (D-098). Condition 3 was repaired this session and condition 4 still fails; Sol was explicit it must not later be renamed a pass. **Not** the condition-1 pivot — H1's machinery works; what failed is power. The 300-unit design continues under a recorded limitation, Direction C authorised.

**The W4 Friday runner is rebuilt and NOT executed** (D-097), which is what Sol asked to see. `calibrate()` now takes no argument that can change the number.

**Audit found two methodological limits of the balancing rule** (D-099), both raised rather than assumed away: it caps row count but **not tail influence** at the 95th percentile, where one stratum of nine is 11.1% of the pool; and its RNG is inert when strata are equal-sized, though real movement counts vary (815–853) so seed 0 does bind and ~4% of reference data is discarded to the smallest stratum.

**Tests:** 745 → **760 passing**, 2 skipped, **0 xfailed**. **Compute:** real fits only in temp directories on the cheapest registered obligation; **no registered evidence, no threshold calibrated, no data seen.**

### 2026-08-20 (W5 Sat, correction pass) · Sol's delta-45 corrections · Claude

**Sol accepted the paired seed-cluster analysis in principle and Gate 1's FAIL**, then listed narrow corrections. All done (D-100); no new experimental data was needed.

**A claim of mine narrowed.** D-094 said the three variance components "become unidentifiable". Sol is right that this overstates it — shared intercepts cancelling from the paired contrast does not prove mathematical unidentifiability in long-form data. What was established, and all that is claimed now: that specification was **singular in practice**, **computationally unacceptable** where it fit, and **failed to represent repair-effect heterogeneity**. Enough to justify the analysis without the stronger claim.

**The estimand made self-consistent**: the effect equally weights seed means, but the denominator was weighting raw transitions — the D-042/D-044 shape. Both sides now use `mean_s(mean_i baseline[s,i])`, with a test whose fixture gives seeds unequal counts so the two weightings genuinely differ.

**Exactly the frozen 20-seed set** is now required where the label is created; nineteen seeds or an after-the-fact subset is a different experiment. **No fallback** in registered acceptance — it fails closed rather than switching replication from seeds to episodes on the strength of the data. **Result language corrected** throughout.

**C-008's last two exposures closed**: `allow_dirty` and caller-chosen thread counts are gone, threading frozen at 4/4 inside the runner. **Threshold**: attempt names frozen to `attempt-NNN` so no permitted name escapes prior-attempt discovery; `INVALID` must state a reason; and `recompute_threshold` no longer reads the frozen spec out of the file it is checking — it compares every constant against the code, verifies run and member digests, and **reconstructs** the deterministic selection rather than reusing the recorded one.

**Rerun as required:** all four pairing-strength calibrations still calibrated. **Tests:** 760 → **786 passing**, 2 skipped, **0 xfailed**. **W4 Friday remains stopped.**
