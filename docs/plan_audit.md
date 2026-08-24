# Plan/schedule audit — the certified methodology against its sources

**Authorised by Sol at the delta-60 certification (D-125): read-only,
prose-only — compare the certified methodology against the source plan and
schedule, record contradictions, propose prose corrections. Not later-week
implementation. Conducted 2026-08-23.**

**Sources:** `docs/thesis_project_plan_v1_2.docx` (P§) and
`docs/thesis_day_by_day_schedule_v1_2.docx` (S§), extracted to text with
python-docx, paragraphs and all tables. **Audited:** the four certified
documents in their stated roles (D-125). **Nothing was edited** — the four
certified snapshots are byte-identical to what Sol certified; every correction
below is a **proposal** for Sol's ruling, not an applied change.

**Method.** Every explicit P§/S§ citation and every sentence asserting "the
plan says / the schedule says" was extracted from the certified documents and
checked against the source text — read in full, not from memory, because all
three substantive errors of the delta-57 round came from writing about a
source without reading it.

---

## 1 · Verified — the claims that hold, with their source lines

| Claim in certified prose | Source | Verdict |
|---|---|---|
| ±5 pp equivalence margin, fixed before data; interval entirely inside ⇒ match, falsifies H3 | P§4.2 H3: *"fixed before data collection at five percentage points of balanced accuracy"* | ✓ exact |
| Data repair ×10, fixed in advance (v1.0 said "substantially larger") | P§7.2 | ✓ exact |
| 20% minimum practical effect, relative not absolute, fixed before data | P§7.3 | ✓ exact |
| 95% CI excluding zero + negative effect + practical floor, all required | P§7.3 | ✓ |
| Permutation null permutes repair assignment within condition, never transitions/episodes | P§7.3 | ✓ |
| Ambiguous = both repairs work → excluded; undiagnosed = neither → excluded, counts reported | P§7.4 label table | ✓ exact |
| Seed policy 5 (H1/H2) / 20 (canonical repair validation) / 3 (sweep, and Exp-3 repairs across it) / 5 (ablations) | P§14.2 | ✓ exact |
| ~8,700 fits; **110–145 GPU-hours**; trigger **~120**; *"a gate rather than a formality"*; *"no longer meaningful headroom"* | P§14.3 | ✓ exact |
| Seeds are never the reduction lever; the unit count gives, only against the measured MDE | P§14.3 | ✓ exact |
| 80% power fixed; **no significance level named** (DEV-008's premise) | P§10.7 final ¶ | ✓ |
| ≥300 labelled units, held-out floor **≥60**; sizing down permitted only against the measured MDE | P§10.7 | ✓ |
| Balancing at the labelled-unit level, per split, equal unit counts per class, then a fixed trace cap; CIs over held-out units, never transitions | P§10.4, S§W5 Fri, S§W15 Mon | ✓ |
| The balancer is S§W5 Fri scope (*"Fix the class-balance procedure in code"*); W15 Mon only *applies* the Week-5 procedure | S§W5 Fri, S§W15 Mon | ✓ — confirms the D-113/D-115 account |
| Gate 1's four conditions as scheduled | S§W5 Sat | ✓ |
| MDE simulated at N = 20/40/60/80 held out; power on **min(N₀,N₁)**, never the total | S§W5 Thu | ✓ |
| Exclusion-rate assumption: *"Inflate the configuration target by a pilot exclusion rate and record the assumption"*; W6 Mon *"check its exclusion rate against the Week 5 assumption"* | S§W5 Thu, S§W6 Mon | ✓ — DEV-012's premise |
| *"Raise the configuration count now. It costs Kaggle time, not your time. Discovering this in Week 15 costs the thesis."* | S§W5 Focus | ✓ verbatim |
| Trend test implemented **once**, same function for W4 gate and W10 verdict | S§W4 Mon | ✓ — D-068's one-implementation rule is the schedule's own |
| Threshold: percentile on a well-fit reference, written to *"a constants file that is never edited again"* | P§10.1, S§W4 Fri | ✓ (the percentile **value** is not in the plan; 95th was fixed by D-035/D-097 — prose attributes it correctly) |
| Six dataset sizes 100…5000 | P§8.1 table | ✓ |
| PPO specified; scripted policy an *"acceptable substitute … recorded rather than hidden"* | P§13.2 note | ✓ — the substitution story is plan-sanctioned |
| Four moves + `interact`; shape example (triangles passable, squares block) | P§13.1.2, P§2.2 | ✓ |
| Canonical 2A = four non-zero confound levels × five configurations; W2 Wed requires the same-vs-additional decision **in code** | P§8.2.1/Table 4, S§W2–W3 | ✓ — reconciles "four conditions" (plan) with "five canonical configurations" (D-026/DEV-006) |
| Direction C: inconclusive, reported *"alongside the minimum detectable effect… never written up as a negative result in disguise"* | P Table 7 | ✓ |
| Estimation failure includes poor coverage curable by more data | P§3.2.1 | ✓ |
| Word-count cells: W1 Thu ~400, W2 Thu ~400, W2 Sat ~300+figure, W4 Sat ~400 | S | ✓ |
| *"It runs on Kaggle while you are at work"* | S§W4 preamble | ✓ verbatim |
| The primary-error-on-movement definition is **not** in the plan — which is why it is a recorded deviation | plan text (absent), DEV-007 | ✓ consistent |

## 2 · Contradictions in the certified prose — corrections proposed, not applied

**F1 — §5 understates what was preregistered (the only finding that touches
substance).** `method_own_voice.md` §5: *"the formal reading rule for
Hypothesis 1 — which statistic, which direction, what counts as a pass — had
not yet been frozen."* **The plan froze most of that before Week 1.** P§4.2-H1
(revised in v1.2): falsified if the trend is absent or reversed, *"tested as a
rank correlation across the six data sizes with a confidence interval over
seeds that includes zero or lies in the wrong direction"*. The schedule repeats
it (change-notes; S§W4 Mon). What D-068 froze later was the **exact
implementation** — Spearman specifically, the exact paired seed-block
bootstrap, the entire-interval rule and degenerate cases — before the gate ran.
The irony runs the wrong way: the current sentence makes the project look
*less* preregistered than it was.
*Proposed replacement:* "Second, the rule. The plan had fixed the statistic and
its direction in advance — a rank correlation across the six sizes, with a
confidence interval over seeds. What had not yet been fixed when the curves
were drawn was the exact implementation of that rule: which coefficient, which
bootstrap, and what happens in boundary cases. That was frozen afterwards,
before the gate that used it ran, so that nobody could bend the remaining
freedom around a curve already seen."
*(Card 5's "the trend test came later" is literally true — the implementation
is S§W4 Mon — but should add "the plan had already fixed the statistic and
direction (P§4.2)".)*

**F2 — §16 and the draft attribute the mixed model to the schedule; it is the
plan's.** P§7.3 *is* the specification — mixed-effects on per-transition error,
random intercepts for seed and episode-within-seed, and the episode-mean
fallback as the *"equivalent and preferred fallback"*; S§W5 Tue repeats it with
the statsmodels detail. The plan is the design authority, and DEV-009 is a
deviation from **P§7.3**, not merely from a schedule cell.
*Proposed edit:* in `method_own_voice.md` §16 and `method_draft.md`'s DEV-009
section, "the schedule specified" → "the plan specified (P§7.3), and the
schedule repeated".

**F3 — §13 attributes the raise-the-count instruction to the schedule; the
plan mandates it.** P§10.7: *"If that value exceeds the five-point equivalence
margin … **the configuration count is raised until it does not**."* The
schedule's focus note is the vivid restatement. This matters because it makes
DEV-010 a recorded deviation **from the plan**, which is the stronger and more
honest statement.
*Proposed edit:* "The schedule anticipated this exact situation and gave an
instruction" → "The plan mandates the remedy (P§10.7…), and the schedule
repeats it with a deadline" (schedule quote kept as is).

**F4 — "a Kaggle T4" understates the planned resource.** P§14.1: *"Kaggle,
2× T4"*; the per-fit time basis is quoted *"on a T4"* (P§14.3).
*Proposed edit:* in §14 (both documents): "names a Kaggle T4" → "names Kaggle
T4s (2× T4), with per-fit times estimated on a T4". No number changes.

## 3 · Contradictions inside the sources — recorded for Sol, no prose change

**F5 — the plan disagrees with itself on what the causal rule governs.**
P§2.2: *"triangular objects are passable, square objects are not"* —
passability. P§13.1.2's family-A table row: *"Shape determines **interaction
outcome**; colour is sampled independently and is non-causal."* The
implementation and the certified prose follow §2.2 — the causal attribute
governs passability, and `interact` is deliberately orthogonal — and Sol's
delta-58 corrections enforced exactly that description. **No recorded decision
reconciles the two plan statements.** Proposed handling, for Sol to rule on: a
one-line note (deviation-log or methodology footnote) naming P§2.2 as the
governing statement and Table 13.1.2's row as loose wording, so a reader who
finds the table row does not conclude the implementation departed silently.

**F6 — plan Table 3 retains the v1.1-style falsifying wording** (*"flat or
non-monotonic, or the trend is within across-seed noise"*) that P§4.2 (v1.2)
explicitly replaced with the trend test, calling the old form a comparison of
*"quantities that are not on the same scale"*. §4.2 governs by its own
statement. Recorded so nobody later cites Table 3's wording as the criterion.

## 4 · Scheduled-later obligations confirmed, not yet due

**F7 — the P§7.4 conditioning statement is W17 prose.** The plan mandates the
thesis state that *"the reported diagnosis accuracy is accuracy on cleanly
separable failures, not on failures in general"*; the schedule places it in
the W17 Thu limitations cell (~600 words) with *"State the excluded fraction
next to it (P§7.4)"*. Absent from the certified methodology — **correctly**,
since it is scheduled later. Optional cheap insurance (D-113's lesson that
nothing checks schedule coverage): one forward-pointer sentence at the end of
`method_own_voice.md` §15. Proposed: "The exclusion counts also bound what the
final result can claim: every Hypothesis-3 number is accuracy on the cleanly
separable failures that survived these exclusions, and the thesis states this
conditioning explicitly where the result is reported (P§7.4)."

**F8 — held-out band.** The prose's "60–80 of 300" is the operative band: the
plan's floor is ≥60 held out of ≥300, the schedule's MDE cell simulates
N = 20/40/60/80. No change needed; recorded for precision.

## Sol's dispositions (delta 61 / D-128)

**D-126 accepted; all findings ruled.** F1 ACCEPT (applied). F2 ACCEPT — DEV-009
deviates from the plan (applied). F3 ACCEPT — DEV-010 deviates from the plan
(applied). F4 ACCEPT WITH PRECISION — "Kaggle, 2× T4", per-fit estimate may
stay "on a T4" (applied). F5 RULED — P§2.2 governs; P§13.1.2 is a source-plan
erratum, recorded in the correction index, no code change (applied). F6 ACCEPT
— Table 3 wording superseded by P§4.2, recorded as source erratum (applied).
F7 — pointer made **mandatory**; the forward scope sentence is now in §15
(applied). F8 ACCEPT, no change. The certified four documents were edited under
this authorisation; D-127 (the C-005/C-007 spec) was **not** accepted and is
corrected separately (D-128).

## 5 · Disposition

Nothing in the certified documents contradicts the sources in a way that
changes any number, verdict, or recorded deviation. The four textual
corrections (F1–F4) are attribution and precision fixes; F5 asks Sol to
reconcile a plan-internal inconsistency the implementation already resolved in
the direction of P§2.2; F7 is one optional sentence of insurance. All verified
rows in §1 stand as written.
