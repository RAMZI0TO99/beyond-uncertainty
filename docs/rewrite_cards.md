# Section cards for the methodology rewrite

**For the student. One card per section of `docs/method_draft.md` (17). Write
each section fresh from its card, in your own words, without the draft open —
then hand me the text and I check it against the ledger. The cards say what a
section must contain and what it must never say; they do not give you sentences
to copy. Where a number appears, its estimand appears with it — quote both or
neither.**

Sources are D-numbers in `DECISIONS.md`. Where this file and the ledger
disagree, the ledger wins.

---

## 1 · Environment design rationale *(W1 Thu)*
**Must say:** why a gridworld with factored observations — failure modes must be
*constructible* (estimation vs hypothesis-class) and labels *counterfactual*;
the environment is built against `UnitSpec` directly (D-017). **The causal
attribute governs PASSABILITY during movement** (shape causal → triangles
passable, squares block; colour causal → red passable, blue blocks).
**`interact` toggles the first adjacent object's activation and is deliberately
ORTHOGONAL to passability** — no attribute governs it; it exists so the action
has an observable effect, and activation is an auxiliary diagnostic only.
**Must not say:** "only triangles can be activated", or anything implying
activation is the transition rule the primary model must discover.
**Must not say:** anything implying the environment was tuned after seeing model
behaviour.
**Sources:** D-017, D-027, P§5.

## 2 · The configuration axes *(W2 Thu)*
**Must say:** each axis exists to *manufacture* a failure class or confound it
(size/data for estimation; withheld features / capacity for hypothesis-class;
confound axis to stress the critic). The sweep is a **balanced sample, not the
full crossing** (D-018), with intended-class balance kept by a **predeclared
reserve** (D-031, order committed in D-092).
**Must not say:** "all combinations"; that reserve draws are ad hoc.
**Sources:** D-018, D-031, D-092, D-007.

## 3 · The behaviour policy, and why it is not PPO *(W2 Sat)*
**Must say:** scripted exploratory policy replaced PPO; the substitution is
**evidenced, not asserted** (D-020) — but the original coverage evidence was
taken under a non-stationary policy and is **void**; the policy is now
**stationary across episodes** (D-051) and the evidence re-measured.
**Must not say:** quote any pre-D-051/D-052 number (D-020's coverage table is
void). Never claim episode-IID was *proven* — see card 4.
**Sources:** D-020, D-051, D-052.

## 4 · Correction to the behaviour-policy evidence *(D-051/D-054)*
**Must say:** what changed and why the correction is recorded rather than
silently fixed. The "+1.1 SE by episode index" result is **consistent with**
IID episodes, not proof of them — **a null result never proves the null**;
where a property is structural, the structure is asserted (D-054).
**Must not say:** "we verified episodes are IID".
**Sources:** D-051, D-054.

## 5 · What the first curves look like *(W3 Sat)*
**Must say:** written before any formal test; error falls with data, ensembles
agree more as data grows; explicitly descriptive, development seeds only.
**Must not say:** anything that reads as an H1 verdict — the trend test came
later, and confirmatory seeds have never been touched.
**Sources:** D-058, **read D-059's correction first**.

## 6 · The normalising scale *(D-061/D-064/D-076)*
**Must say:** per-dimension scale built from the **full movement evaluation
pool, before any failure mask exists**; the same object reused for whole-pool
and masked statistics — structurally, because `from_pool` takes no mask
(D-076). Preregistered (D-061, wording corrected by D-064).
**Must not say:** the withdrawn claim that a mask "has nothing to recompute
from" (D-064); anything implying the scale is recomputed per subset.
**Sources:** D-061, D-064, D-076.

## 7 · What the error is, and what it is not *(DEV-007/D-032 — mandated)*
**Must say:** primary error is **agent position on movement transitions**;
model predicts **dynamic components only**, static attributes are deterministic
passthrough and never enter the loss; activation is action-conditional on
`interact`. The auxiliary activation head is a **non-decisional diagnostic**
(D-063): detached trunk, barred from early stopping, checkpoint selection, the
failure set, repair labels, and the critic's residual.
**Must not say:** loss share as gradient share (the 97.7% loss / 16–36%
gradient inversion, D-047); anything reviving the head.
**Sources:** D-032, D-047, D-063, DEV-007.

## 8 · Why position-causal conditions are not canonical 2A *(DEV-006/D-026 — mandated)*
**Must say:** hiding shape or colour leaves the scene fully visible and makes the
*rule* unrepresentable — the failure 2A is about. Hiding **position** is a
different structural failure: position says **where** an object is (shape,
colour, activation and the object slots stay visible, so the object does not
disappear), and removing it makes **distinct spatial states encode
identically** — **causal aliasing**. Measured: **37.5%** of (observation,
action) keys aliased against **10.0%** for shape and colour, in a key space
**26× smaller**. So those conditions left the canonical Experiment 2A set and
run as a declared robustness configuration; recorded as a deviation, not
silently dropped. It **bounds the claim**: 2A is a result about withheld
*attributes of visible objects*.
**Must not say:** that position tells the model an object **exists** at all;
that the model fails because the rule became unrepresentable (it fails because
it cannot tell two situations apart); or that withholding position merely
"changes movement dynamics" — that is not the certified reason.
**Sources:** D-026, DEV-006.

## 9 · The reliability gate, and the rung it passed at *(W4 Tue, D-074/D-075 — mandated)*
**Must say:** rho = **−0.9429** on all three predeclared configurations
(uniform, clustered, sparse); 90 ensembles / 450 fits, 4 m 52 s CPU; ladder
**stopped**, rungs 1–2 not run. **Development seeds — the gate is passed, the
hypothesis is not tested.** Zero-width intervals: include Sol's sentence
(quoted verbatim in D-075) — exact paired bootstrap over all 3,125 resamples,
2–3 atoms, **quantile discreteness, not zero sampling uncertainty** — and the
atom/mass table travels with it. Clustered seed 4 is **reported, not
investigated** (14/15 curves peak at N=250; that one at N=500); confirmation
waits for W10's untouched confirmatory seeds.
**Must not say:** a bare `[−0.9429, −0.9429]`; any smoothing, added seeds, or
estimator change; the W3 pilot as a comparable per-fit workload (it is ~10×
slower because it writes per-transition exports).
**Sources:** D-068, D-074, D-075.

## 10 · The failure threshold *(W4 Fri, D-103/D-107)*
**Must say:** `FAILURE_THRESHOLD = 0.610702633857727`, **permanently frozen**
(D-107, certified D-109). Failure is **strictly greater** — at equality a
transition is NOT a failure, and **two calibration transitions sit exactly at
the value**, so the boundary decides real labels. Estimand, in full:
ensemble-mean normalised movement error, K=5, fully observed n=5,000 reference
models, no confound, nine layout × causal-attribute strata, seeds 1000–1004,
equal stratum weighting by deterministic minimum-count subsampling at RNG seed
0, 95th percentile, `method="linear"`. Sol verified independently to a
bit-identical float.
**Must not say:** rounded values; per-layout thresholds; any recalibration
path — the invalidation protocol can no longer be satisfied and that door is
closed permanently.
**Sources:** D-035, D-097, D-103, D-106, D-107, D-109.

## 11 · Limitation: failure prevalence is not uniform across layouts *(D-108/D-109)*
**Must say:** the measured 5.5× spread (1.58%–8.77%, ordered clustered <
uniform < sparse) **stands as a measurement**. Preferred framing: *the same
global threshold applies everywhere, but the observed prevalence differs by
layout* — the threshold's definition and meaning do not change. Analysis rule
registered by Sol in D-109.
**Must not say:** that it is "mostly normalisation-scale driven" — that is
D-108's **withdrawn** mechanism claim; D-109 preserves the measurement, not its
explanation. Also: the 5.02% unbalanced-pool check bears on **weighting**, never
on between-strata homogeneity.
**Must not say:** **D-108's causal interpretation — it is withdrawn** (D-109).
Report the measurement, not the mechanism story.
**Sources:** D-108, **D-109 controls**.

## 12 · What this design can and cannot detect *(Gate 1)*
**Must say:** four conditions: reliability **PASS**; compute **NOT
ADJUDICABLE** — measured 5.72/6.91 **local wall-hours** vs a **120 GPU-hour**
trigger on a device never used, neither pass nor fail; permutation calibration
**PASS**; MDE **FAIL**. At **first mention**, call 18–22 pp a **provisional,
optimistic diagnostic** estimate under the scheduled sample — never "the
smallest difference the design can detect". The Wald rule over-rejects
(6.1–9.2% vs nominal 5%), and **the final exact MDE is not yet known**: it waits
on H3's final group-level inference and its null calibration. Sample size is the driver (ICC = 0 still gives 18). α = 0.05
two-sided is a recorded deviation (DEV-008). MDE-vs-margin is a **necessary
sensitivity check, not an equivalence test**; no *exact* MDE until H3's final
inference exists. H3 may be inconclusive around ±5 and that is a reportable
outcome.
**Must not say:** "compute PASS" (**D-098's signed record still says it — cite
the corrected value, D-119/D-120**); any hours-vs-trigger comparison; "the
study is underpowered" without the diagnostic framing.
**Sources:** D-078, D-082, D-089, D-098, DEV-008, D-119, D-120.

## 13 · The remedy the schedule prescribed, and why it was declined *(DEV-010 — mandated)*
**Must say:** the schedule said *raise the configuration count now*; it was not
raised — deliberately, on review. A **rough diagnostic extrapolation** suggests
on the order of **1,500–2,000 held-out** units vs 60–80 scheduled — **not a
computed sample-size requirement**. Preserving the fraction gives an
**approximate 5,625–10,000 total, 18.75×–33.3×**, explicitly a **unit-count
extrapolation carrying no execution host**. Refusal grounds: registered scope, and a
budget position resting on the registered GPU-hour design estimate plus the
scope decision. The limitation is carried forward, not repaired.
**Must not say:** the multiplier converted into hours against the 120-hour
trigger (**the error made twice, D-115 → D-119**); the withdrawn "5–6×".
**Sources:** DEV-010, D-089, D-115, D-119.

## 14 · Where the results were produced *(DEV-011 — mandated)*
**Must say:** plan says Kaggle T4 / GPU-hours; **every fit ever run is local
CPU**, zero GPU-hours, no Kaggle job ever submitted. Certified timing:
**5.72 / 6.91 local wall-hours** (median / conservative max). Thread count is
recorded because it is **not numerically neutral** (4 vs 8 threads moved one
certified cell 0.19% — reduction order). Timing evidence is provenance-bound:
exact source commit, clean tree required, content digest verified in review.
**Must not say:** any local-figure-as-GPU-hours statement.
**Sources:** DEV-011, D-076, D-116, D-119.

## 15 · The exclusion-rate assumption *(DEV-012 — mandated)*
**Must say:** schedule wanted pilot-rate inflation; **no pilot rate existed**.
Registered convention, ratified before any real labels: **0.00 — a
zero-inflation planning convention, not an empirical prediction**; target
`ceil(300/(1−0.00)) = 300`; no anticipatory oversampling. Observed estimand:
**(ambiguous + undiagnosed) / all attempted labelled units**, pooled and by
intended class. Any exclusion > 0 ⇒ assumption missed ⇒ report the shortfall
first, then the predeclared D-092 reserve under its gate. Critic sample sizes
are surviving `min(N₀, N₁)`, never attempted totals.
**Must not say:** zero as **observed, estimated, or pilot-derived** — Sol's
exact prohibition.
**Sources:** DEV-012, D-092, D-119, D-120.

## 16 · The repair-acceptance test *(DEV-009, D-094/D-100 — mandated)*
**Must say:** the schedule's mixed-effects model is replaced — the literal
specification is **degenerate** for this design (D-094); the registered test is
three conditions, **all required**, on paired per-transition errors, reduced to
an **equal-seed mean paired difference with a t interval on `n_seeds − 1` df**,
with a permutation null that **permutes whole paired runs and seeds, never
transitions** (D-079).
**Must not say:** that an episode-mean fallback exists or is an alternative —
**there is no fallback** (D-100/D-101 removed it, and removed the option to
request one). Invalid, degenerate or non-finite inputs **fail closed**. Calibration: 5–7/200
against an admissible [1, 10], full rule 0/200 (D-098 c3).
**Must not say:** that the mixed model was "approximated" — it was replaced,
under a Change Record, and the deviation says why.
**Sources:** DEV-009, D-079, D-085, D-086, D-094, D-100.

## 17 · One unit, several roles *(W2 Wed, D-007 — mandated)*
**Must say:** the four identities and what each is for; the statistical unit is
the **configuration-condition**, shared by a failure condition and its repair
arms — that is what makes a label assignable. Seed obligations are **not uniform**: canonical
**repair-validation** units run **20** seeds; where such a unit *also* serves an
H1/H2 role the **5** hypothesis seeds are **contained within** those 20 — one
set of fits wearing two roles, not 25 runs (D-033; conflating them once produced
375 phantom fits); **sweep-only** units run **3** seeds and carry neither
obligation. Preserve the distinction between `run_id` obligations and
deduplicated `fit_id` computations. Comparison groups **never span a split or fold** (D-039).
Confirmatory seeds ≥ 1000; everything below is permanently development data
(D-034).
**Must not say:** an effective sample size without its estimand — under the
registered `"unit"` weighting the ICC=1 boundary is **75/72.6**; the cluster
counts 125/115 belong to an estimand the thesis does not use (D-044).
**Sources:** D-006, D-007, D-012, D-033, D-034, D-039, D-044.

---

**Workflow:** pick a card, write the section fresh, send me the text. I check
it against the ledger and flag errors — I do not rewrite your sentences.
