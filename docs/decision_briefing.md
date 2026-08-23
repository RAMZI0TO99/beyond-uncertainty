# The decisions, consolidated — a reading brief

**Written 2026-08-23 (D-120's allocation). Source: `DECISIONS.md`, D-001 … D-120.**

This exists because the ledger is 330 KB written across ~40 sessions, much of it
correcting earlier versions of itself, and **you cannot rewrite the methodology
in your own voice until you know what was actually settled.** It is a reading
aid, not a source of truth: **where this file and `DECISIONS.md` disagree, the
ledger wins.** Every claim here carries its D-number so you can go and check.

Read Parts 1, 4 and 5 before you write a word of methodology. Parts 2 and 3 are
the design. Part 6 is the one worth reading last and remembering longest.

---

## Part 1 — Frozen. These cannot move.

`src/bu/constants.py` is the preregistration, deliberately in one file. It is
one file because in Plan v1.1 a withdrawn acceptance rule survived in two
sections and would have produced **a different ground-truth label depending on
which section the implementation happened to read**. Scattered constants fail
the same way, silently.

Changing anything there needs a Change Record naming the constant, the value,
the reason, and **whether data has been seen**. If data has been seen the answer
is almost always no.

| Constant | Value | Why it is what it is |
|---|---|---|
| `FAILURE_THRESHOLD` | **0.610702633857727** | **The most irreversible number in the project.** Every failure set, every repair label, and therefore H2 and H3 descend from it (D-035 → D-103 → **D-107**, certified **D-109**) |
| `CONFIRMATORY_SEED_BASE` | 1000 | Everything below is pilot data, permanently excluded (D-034) |
| `EQUIVALENCE_MARGIN_PP` | 5.0 | H3's margin (Plan §4.2) |
| `MIN_PRACTICAL_EFFECT` | 0.20 | Relative, not absolute — error scales differ across configurations |
| `DATA_REPAIR_MULTIPLIER` | 10 | v1.0 said "substantially larger", an unreported degree of freedom |
| `SEEDS_HYPOTHESIS` / `_REPAIR_VALIDATION` / `_SWEEP` | 5 / 20 / 3 | Three counts, each load-bearing for a **different** claim |
| `CRITIC_TRACE_CAP_PER_UNIT` | 50 | A **maximum, not an eligibility threshold** (D-115) |
| `BALANCED_ACCURACY_WEIGHTING` | `"unit"` | Every configuration-condition weighted equally (D-044) |

### Three things about the threshold you must not get wrong

1. **Failure is *strictly greater* than the value.** At equality a transition is
   **not** a failure. This is registered definition, not convention — **two
   transitions in the calibration pool sit exactly at the value**, so the strict
   boundary decides real labels.
2. **It can never be recalibrated.** Sol's invalidation protocol requires
   declaring an attempt invalid *before* its threshold is read. It has been
   read. That door is closed permanently.
3. **Quote it with its estimand or not at all.** Ensemble-mean normalised
   movement error, K=5, fully observed n=5,000 reference models, no confound,
   nine layout × causal-attribute strata, seeds 1000–1004, equal stratum
   weighting by deterministic subsampling at RNG seed 0, 95th percentile,
   `method="linear"`. A number without its estimand is not a number.

### The trap that is not a constant

**Comparison groups.** Units sharing one were *given related data by design*, so
a group must **never** span a critic split or a CV fold (D-039). This is the
clustering every split and every interval has to respect.

---

## Part 2 — What the study actually is

When a model-based RL agent's world model mispredicts, should it **gather more
data** (estimation failure, `f* ∈ H`) or **change the model class**
(hypothesis-class failure, `f* ∉ H`)?

Ensembles cannot tell you. Under misspecification every member shares the blind
spot, so **disagreement stays low while error stays high**. The thesis builds a
critic that predicts which repair is needed and tests it against honestly-fitted
baselines. Ground-truth labels are **counterfactual** — established by actually
running both repairs.

| | Claim | Status |
|---|---|---|
| **H1** | Disagreement tracks estimation failure | Gate passed at rung 0 on dev seeds (D-074/D-075); **hypothesis not yet tested** |
| **H2** | Disagreement-to-error ratio is low under hypothesis-class failure | Not tested → Gate 2 |
| **H3** | Learned critic beats fitted (error, disagreement) rule by > 5 pts | Not tested → W15 |

**A negative result is a complete thesis.** Never steer toward confirming H3.

Key design decisions, compressed:

- **The sweep is a balanced sample, not the full crossing** (D-018), with a
  predeclared reserve for class balance (D-031, drawn order fixed in D-092).
- **The world model predicts dynamic components only**; static attributes are
  deterministic passthrough and never enter the loss. Primary error is **agent
  position on movement transitions** (D-032, DEV-007).
- **The auxiliary activation head is a non-decisional diagnostic** (D-047 →
  **D-063**): detached trunk, barred from early stopping, checkpoint selection,
  the failure set, repair labels and the critic's residual. **Do not resurrect
  it** — the real loop never beat the copy baseline, 0 of 15 fits.
- **Episode block bootstrap is the fixed primary** for H1/H2; transition-level
  is a labelled secondary that **may not overturn a verdict** (D-050, D-053).
- **Three physically disjoint pools** (D-052). Training is exactly the
  registered N; validation and evaluation are byte-identical across every
  dataset size. Carving validation out of training made a "100-transition"
  condition train on 50.
- **PPO was replaced by a scripted stationary policy**, evidenced rather than
  asserted (D-020, D-051).
- **The critic feature whitelist is frozen** and fails closed (D-010, D-013) —
  whitelist, never blacklist.

---

## Part 3 — The four identities

Most of the analysis discipline follows from these, so they are worth the two
minutes.

| Identity | What it adds | What it is for |
|---|---|---|
| `unit_id` | the configuration-condition | **The statistical unit for every confidence interval.** Shared by a failure condition and all its repair arms — which is what makes a label assignable |
| `config_id` | + the arm | which repair |
| `run_id` | + stage **and** seed | which obligation a record discharges |
| `fit_id` | `config_id` + seed, **no stage** | the identity of the *computation* |

**Keep the last two apart, and note the obligations are not uniform.** Canonical
**repair-validation** units run **20** seeds; where such a unit *also* carries an
H1/H2 role, **the twenty contain the five**. **Sweep-only** units run **3** and
carry neither. They are one set of fits wearing two roles, not 25 runs (D-033).
Conflating them once cost **375 phantom fits**.

---

## Part 4 — Where the study actually stands

**Weeks 1–5 are COMPLETE and certified** (D-120, base `801a33d`). No week is
open — first time since Week 3. Gate 2 is 2026-10-24 and gates never move.

### Gate 1 = FAIL, and the honest reading

| Condition | Verdict |
|---|---|
| 1 · Reliability | **PASS** — rung 0, rho = −0.9429, certified (D-074/D-075) |
| 2 · Compute | **NOT ADJUDICABLE across hosts. Not a PASS** (D-119/D-120) |
| 3 · Permutation calibration | **PASS** (D-085/D-086) |
| 4 · MDE resolves five points | **FAIL** — a **provisional, optimistic diagnostic** estimate of 18–22 points; **not an exact MDE** (D-078, D-089) |

> **SUPERSEDED — DO NOT CITE; controlling decisions: D-119/D-120.**
> D-098's own table reads *condition 2 = PASS*. That was the record on
> 2026-08-20 and it is **append-only, so it will always read that way**. It was
> corrected to **NOT ADJUDICABLE** by D-119 and D-120. **Cite the corrected
> value.** This is the single most likely place to quote a withdrawn claim,
> because the original sits in a signed gate record. The full correction map is
> at the front of `DECISIONS.md`.

**Gate 1 fails on the MDE, independently.** It must never be renamed a pass.

**It is not a pivot.** H1's machinery works; **what failed is power.** The
300-unit design continues under a recorded power limitation with **Direction C
authorised**.

**Sample size is the driver, not correlation.** At ICC = 0 the diagnostic is
still 18 points, so the conclusion does not rest on the parameter least knowable before
data. Every lever was tested: pairing reaches 8.0 at correlation 0.99; holding
out *all 300* units gives 6.0 paired.

**The diagnostic is optimistic** (D-082): the power test is anti-conservative —
type-I error 0.06–0.09 against 0.05 — because it uses a Wald `1.96×SE` rule
where D-044 registers a group-bootstrap percentile. **The final exact MDE is
not yet known**; it waits on H3's final group-level inference and its null
calibration. The qualitative risk — that the registered sample cannot resolve
±5 points — is real, not a simulation artefact.

**What the MDE is and is not** (D-089, and this is the sentence for the thesis):
MDE-versus-margin is a **necessary sensitivity check, not an equivalence test**.
The quantities share units, so an MDE above five points means the study cannot
resolve that region — but **MDE ≤ 5 would not by itself establish adequate
power**. And **no exact MDE may be reported** until the simulation uses H3's
final group-level inference with its null size validated. That is gated on
reporting, and **H3's final test is not settled**.

### Compute — say this exactly

- W4 local timing evidence: **complete and certified**
- Estimate: **5.72 / 6.91 local wall-hours**
- Registered trigger: **120 GPU-hours** on a planned Kaggle T4
- Cross-host comparison: **NOT ADJUDICABLE**
- **Zero GPU-hours have ever been spent.** 675 CPU fits total; nothing has ever
  run on Kaggle (DEV-011)

**Expansion is refused** on scope and power grounds. A **rough diagnostic
extrapolation** suggests on the order of **1,500–2,000 held-out** units against
60–80 scheduled — **not a computed sample-size requirement** — giving an
**approximate 18.75×–33.3×** unit-count extrapolation. **Never convert that into hours and compare it to the
120-hour trigger**; that is local CPU wall-hours against GPU-hours, and it is
the error that survived two attempts to fix it (D-115, corrected by D-119).

### The zero-inflation convention (DEV-012, certified)

Planning exclusion rate **0.00** — a **convention, not a measurement**. Target
`ceil(300/(1−0.00)) = 300`. Observed estimand is
`(ambiguous + undiagnosed) / all attempted labelled units`, reported pooled and
by intended class. **Any observed exclusion above zero means the assumption was
missed**; report the shortfall, then the D-092 reserve under its gate. Gate 2
uses surviving `min(N₀, N₁)`, **never total units**.

**Zero is never to be described as observed, estimated or pilot-derived.**

---

## Part 5 — Superseded. Read the correction, not the original.

**This is the part that will mislead you if you skip it.** These entries were
wrong and were corrected. Quoting the original in your methodology would put a
withdrawn claim in your thesis.

| Read this | Not this | What changed |
|---|---|---|
| **D-044** | D-039, D-042 | `min(N₀,N₁) = 115` was reported as *the* effective sample size; it is a **bound**. Then a unit-weighted and cluster-weighted result were compared and the gap called approximation error. **Never quote an n_eff without naming the estimand.** Under `"unit"` weighting the ICC=1 boundary is 75/72.6; the counts 125/115 belong to an estimand the thesis does not use |
| **D-109** | D-108 | Prevalence heterogeneity (5.5×) **stands as measured**; the *causal* reading is **withdrawn** |
| **D-119** | D-114, D-115, DEV-010 | Expansion first called "5–6×" (false, inverted the conclusion), corrected to 18.75×–33.3× — and the **correction itself** compared local wall-hours to GPU-hours |
| **D-063** | D-047's open item | Second trunk refused; head is a non-decisional diagnostic |
| **D-064** | D-061, D-062 | A claim narrowed; an "isolation" that was CPU-only |
| **D-059** | D-058 | What the pilot actually measured, versus what was claimed |
| **D-054** | — | "+1.1 SE by episode index" was reported as establishing IID episodes. It is only *consistent* with them. **A null result never proves the null** |

**Numbers taken before D-051/D-052 are void** — D-020's coverage evidence and
the Q-011 disagreement measurements were taken under the non-stationary policy
and the derived split. Re-measure; do not quote them.

**Zero-width intervals must never be printed bare** (D-075). Two of rung 0's
three intervals are a single point, and that is **quantile discreteness, not
zero sampling uncertainty** — Spearman over six sizes has 2–3 distinct values.
Sol's exact sentence is quoted in D-075 and the atom/mass table travels with it.

---

## Part 6 — The failure modes that keep recurring

Read this last, remember it longest. These are not anecdotes; **each cost real
work, and several nearly reached the thesis.**

**1. A check that passes because the thing it checks is missing is not a check.**
The evidence contract took **four** Sol reviews (D-071 … D-073): bare curves
stamped with golden ids; then a manifest self-consistent enough that a 90-entry
fabrication passed; then six fields the contract *advertised* and never
compared. Each fix moved the boundary one layer and stopped short of execution.
**Ask: what would have to be true for this check to fail?**

**2. Test the property, not the mechanism that currently delivers it.** Repeatedly
(D-055, D-057, D-073): a test asserting a *parameter name* did not exist; a
"non-overlap" test comparing values while claiming episodes; a stream test
comparing an object with itself; and `assert X is not Y or True` — a tautology —
written into the very delta claiming that failure mode had been avoided.

**3. Green tests prove little about design.** The two worst defects — object
order leaking into observations, and `_hash` embedding memory addresses — were
both found by **asking a question**, not by a failure.

**4. An audit finds a different class of defect than a review does.** Nine Sol
reviews passed over Week 3; the audit then found seven defects, three serious,
including one that moved the registered H2 endpoint by 4.6%. **Sol reviews what
you report plus a diff; only probing the running system finds the rest.**

**5. A number without its estimand is not a number.** Two consecutive findings on
one paragraph, neither a coding error (D-042, D-044). The suite was green
throughout and the wrong numbers reached five files and a delivered delta.

**6. A fix in one layer is not a fix.** The unresolved/effective unit split was
implemented in collection and never carried into training, so a capacity repair
silently built the *unrepaired* model — every capacity condition would have been
labelled "repair failed" (D-056).

**7. Restoring the state is not fixing the mechanism.** `member_predictions` was
"fixed" by saving and restoring `model.training` while still running the forward
pass under `eval()`. Under MC-dropout that is still **exactly** zero
disagreement (D-062).

**8. Correcting a right number to a wrong one still counts as being wrong.** Rung 0
was estimated at "minutes", "corrected" to ~50 minutes by scaling the pilot's
rate, and was actually **4 m 52 s**. The first estimate was right. The pilot is
~10× slower per fit because it also writes per-transition exports.

**9. Threading is not numerically neutral.** Re-running certified cells at 4
threads instead of 8 moved a result by 0.19%. Reduction order differs (D-076).

**10. Data consumption is a necessary bar, not a sufficient one.** Q-012, 2026-08-23:
I argued C-005/C-007 could be built because they touch no data. Sol: they are
**future-week implementation**, which is the verification lag Q-004 names.
**Completing W4/W5 obligations repaired omissions; it did not authorise pulling
later implementation forward.**

---

## Part 7 — Still open

| What | Status |
|---|---|
| **C-005** grouped critic splitter | Unbuilt. **W6–W11 work. Not authorised now** (Q-012/D-120) |
| **C-007** confirmatory guards in critic loaders | Unbuilt. Same bar |
| **H3's final test** | Not settled. The exact-MDE report is gated on it |
| **Confirmatory collection, critic splitting** | Blocked by Sol, correctly |
| **Week 6 execution** | Barred by Q-004 |

**Barred without a fresh Sol ruling:** recalibrating the threshold, expanding
the design, consuming reserve units, generating repair labels, running anything
on real labelled data. The balancer is **synthetic-inputs-only until C-005
exists**.

**Authorised now:** methodology prose in your own voice; consolidating certified
decisions; checking prose against plan and schedule; **prose-only** interface and
acceptance-criteria specs for C-005/C-007; read-only audits; resolving
contradictions before they become code.
