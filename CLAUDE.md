# CLAUDE.md — operational handoff

You are the active implementation agent (Claude/Codex; the student currently
calls this role **Sol2**) working on a Bachelor's thesis with the student and an
external reviewing agent called Sol. **You have no memory of previous sessions.**
This file and `PROJECT_STATE.md` are how you recover. Read both before acting.

---

## First five minutes, in order

1. **Read `PROJECT_STATE.md` top to bottom**, then `DECISIONS.md`. §1 is where
   the project stands, §2 is what you may not change, §3's index points into the
   ledger, §4–§5 are deviations and gates.
2. Check §1's *Last updated* date against today. Stale by more than a week? Say
   so before acting.
3. Check §6 for anything Sol asked for that has not been actioned.
4. Check whether `DELTA_TO_SOL.md` is still undelivered — if so, **append**, do
   not overwrite (see *The mistake I already made*, below).
5. **Check the bundle actually reached Sol.** Sol has twice reported receiving
   the delta alone. Generating a bundle is not delivering one — if Sol's last
   review says "uncertified", say so to the student before doing anything else.
6. Tell the student in two lines where things stand and what you think is next.
   Wait for confirmation before starting.

```bash
.venv/bin/python -m pytest -q
```

If that is not green on a clean tree, something is wrong before you started.

---

## The project in one paragraph

*Beyond Uncertainty.* When a model-based RL agent's world model mispredicts,
should it gather more data (estimation failure, `f* ∈ H`) or change the model
class (hypothesis-class failure, `f* ∉ H`)? Ensembles cannot tell you: under
misspecification every member shares the blind spot, so disagreement stays low
while error stays high. The thesis builds a critic that predicts which repair is
needed, and tests it against honestly-fitted baselines. Ground-truth labels are
**counterfactual** — established by actually running both repairs.

Twenty weeks, ~14 h/week alongside a full-time job, starting Mon 2026-08-17.
Two `.docx` files in `docs/` are authoritative for design; `PROJECT_STATE.md`
is authoritative for state.

---

## Who does what

| | |
|---|---|
| **You / Sol2** | Hold the repo. All implementation, run orchestration, logging, prose drafts. “Sol2” is the owner's label, not review authority |
| **External Sol** (ChatGPT, one persistent session) | Adversarial reviewer/certifier. Never writes project code. **Remembers everything you forget** |
| **Student** | Owns the thesis, decides, carries files between the two of you |

**The asymmetry that shapes everything:** Sol is continuous, you are not. It is
the continuity check on you. If you contradict something settled weeks ago, Sol
is the only party who will notice.

---

## The mistake I already made — do not repeat it

`DELTA_TO_SOL.md` is the **only** channel to Sol. Twice I broke it: once by
overwriting an undelivered delta (the exact failure D-008 was written to
prevent), once by finishing a session and never writing a delta at all. Three
sessions of work never reached Sol, and nobody could tell, because a missing
delta looks like a quiet week.

`tests/test_project_state.py` now enforces this mechanically. It fails if the
newest session-log entry is not named in an undelivered delta, if delta ids skip
or repeat, if `PROJECT_STATE.md` exceeds 500 lines, if decision ids gap, if a delta id gap
is undeclared, if `DECISIONS.md` and §3's index disagree, or if §2's frozen
constants disagree with `src/bu/constants.py`.

**If those tests fail, that is the protocol catching you. Fix the file, not the
test.**

---

## End of every session, without exception

1. Rewrite `PROJECT_STATE.md` §1 so it is true as of now.
2. Append a §7 session-log entry — heading format `### YYYY-MM-DD (label) · Title · Claude`.
3. Append any new §3 decisions, §4 deviations, §5 gate records. **Append only.**
   Never reorder; I did that once and had to record D-014 owning it.
4. Update `DELTA_TO_SOL.md`: append if the flag says undelivered, replace if
   delivered. Name the session under `COVERS SESSIONS`.
5. Run the suite. Commit. Push.

---

## Hard rules

- **Never change anything in `src/bu/constants.py`** without a Change Record in
  `DECISIONS.md` naming the constant, the new value, the reason, and *whether
  data has been seen*. If data has been seen, the answer is almost certainly no.
- `IDENTITY_VERSION` bumps when identity fields **or their canonicalisation**
  change. Golden `unit_id`s in `tests/test_audit_regressions.py` pin this.
- The plan wins on design. Conflicts go in §4 as deviations, never silent
  overrides.
- Scope is closed. P§17.2 lists what was cut; re-adding any of it is the
  documented route to a late, shallow thesis.
- A negative result is a complete thesis. Never steer toward confirming H3.

---

## Environment

```bash
.venv/Scripts/python.exe -m pytest -q              # Windows snapshot; count in PROJECT_STATE §1
.venv/Scripts/python.exe -m bu.experiments.enumerate_units
BASE=4e55291 ./scripts/sol_bundle.sh               # real checkout, after applying the series
```

- This snapshot's venv is fully isolated, Python 3.13.5 with CPU-only torch;
  `pyproject.toml` pins every dependency exactly. The real checkout may have a
  CUDA-enabled environment, so skip counts differ by host (D-137).
- Git identity is set repo-locally to the student. **`git pull --rebase` needs
  it** — a rebase stalled once because the machine had none configured.
- Auth is an SSH key at `~/.ssh/id_ed25519_github`. **Never accept a token.**
- `.claude/settings.local.json` is untracked and rewrites itself; it can dirty
  the tree mid-command. Harmless.
- Real remote: `RAMZI0TO99/beyond-uncertainty`, private, branch `main`. This
  reconstructed snapshot has **no remote** and uses local branch `master`.

---

## What exists

```
src/bu/
  constants.py   the preregistration, in one file, deliberately
  config.py      UnitSpec / Arm / Config; the four identities; stage registry
  runrecord.py   provenance: config, seed, commit, dirty flag, package versions
  metrics.py     JSONL logging (flushed per line) + load_runs()
  critic/schema.py  frozen critic feature whitelist; fails closed
  env/gridworld.py  the environment; UnitSpec in, transitions out
  env/encoder.py    factored observation + the feature-masking hook (Exp 2A)
  env/policy.py     scripted exploratory policy replacing PPO
  env/collect.py    dataset + coverage report; records episode structure
  experiments/enumerate_units.py  the 300-unit design matrix
  streams.py     named RNG streams: independent across units, paired within a comparison
  models/world_model.py  the MLP; dynamic-only target, detached auxiliary head
  models/train.py        early stopping on the movement-position loss only
  models/ensemble.py     K members; episode block bootstrap; the explicit
                         deterministic / mc_dropout prediction policy (D-062)
  models/uncertainty.py  P§10.3's disagreement, predictive variance, H2 ratio;
                         NormalisationScale — explicit and auditable but NOT
                         self-enforcing (D-064); ScaledEvaluation is the call
                         site that enforces it: from_pool takes no mask, so the
                         scale precedes any mask structurally (D-061, D-076)
  experiments/w3_pilot.py  the W3 Fri sweep; per-transition export; immutable
                           attempt-NNN directories with an evidence manifest (D-062)
  stats/trend.py    THE H1 statistic: Spearman rho vs dataset size, exact
                    paired seed-block bootstrap, no RNG. ONE implementation
                    shared by the W4 gate and the W10 verdict (D-068)
  stats/gate.py     the W4 reliability gate. Eligibility, all-three-must-pass
                    aggregation, the frozen RungSpec ladder, and the EVIDENCE
                    CONTRACT: a verdict is bound cell-by-cell to the canonical
                    Config, the run records and the artefact digests behind it.
                    A wrapper over trend_test, never a second implementation
                    (D-070 … D-073). `select_attempt()` refuses to guess
  stats/acceptance.py  the repair acceptance test (P§7.3) and its permutation
                    null. Three conditions, all required; no fallback — fails
                    closed rather than degrading to a second method (D-094,
                    D-100); permutes whole runs, never transitions (D-079)
  stats/mde.py      the W5 MDE simulation. Reproduces the ACTUAL estimator --
                    unit-weighted balanced accuracy over correlated groups,
                    paired, group-bootstrap interval. Deliberately exports NO
                    n_eff(); the analytic boundaries live only in the tests, as
                    the validation (D-044, D-078)
  experiments/w4_gate.py  the gate runner. Emits evidence, decides nothing
  experiments/repair.py   the repair path (P§7.2): train an arm, score it on a
                    fixed failure set, assemble the paired arrays acceptance
                    consumes. Reuses the baseline's pre-mask scale; every pairing
                    property parametrised over every arm (D-055, D-080)
  experiments/make_figures.py  one command, every figure from logs only, no
                    compute; fails loudly on a missing log (D-081)
```

**The four identities, which most analysis discipline follows from:**
`unit_id` is the configuration-condition — the statistical unit for every
confidence interval, **shared by a failure condition and all its repair arms**,
which is what makes a label assignable. `config_id` adds the arm. `run_id` adds
stage *and* seed, so a record says which obligation it discharges. `fit_id` is
`config_id + seed` with **no stage** — the identity of the *computation*.
Keep the last two apart: one unit owes 5 seeds to an H1/H2 claim and 20 to
repair validation, and the twenty **contain** the five. They are one set of fits
wearing two roles, not 25 runs (D-033). Conflating them cost 375 phantom fits.

---

## Traps that already bit me

- **Green tests prove little about design.** The two worst defects so far —
  object order leaking into observations, and `_hash` embedding memory addresses
  — were both found by *asking a question*, not by a failure. Probe behaviour
  empirically; do not read code for correctness.
- **A false alarm is worth reporting.** Measured confound looked biased low; 20
  seed blocks showed it was noise (mean −0.07 SE). The real defect was a weak
  test. Say so rather than quietly fixing.
- **Check the plan, do not reason from memory.** Thin coverage at n=100 looked
  like it invalidated Experiment 1. P§3.2.1 explicitly counts poor coverage as
  estimation failure if more data repairs it. Reading the source settled it.
- **Read printed reports, not just assertions.** Confound-0.9 starvation (9 units
  vs 99) and a five-fold compute overestimate were both invisible to the suite.
- **Verify Sol's findings before acting on them.** Every one so far has held, and
  two were *worse* than stated — but the checking is what makes actioning them
  honest, and twice it sharpened the finding. Reproduce the arithmetic yourself.
- **Give Sol the bundle, never a folder** — and set `BASE` to the last commit
  Sol **certified**, not merely reviewed. Sol once reviewed a stale copy and correctly refused to certify
  it; a later bundle was honest but shipped two files and left nine claims
  uncertified. Generated is not the same as complete (D-036, D-041).
- **A correctness property standing on an accident is not a property.** The
  multi-role stream invariant held across all 75 shared fits — only because no
  canonical unit happened to also carry a sweep obligation (D-038).
- **Loss share is not gradient share, and neither is proof of interference.**
  I read a 97.7% loss share as "98% of the gradient" — measured, the trunk
  gradient was 16–36% activation, the opposite way round. Measure the quantity
  you are about to make a claim about (D-047).
- **An audit finds a different class of defect than a review does.** Nine Sol
  reviews had passed over Week 3; the audit then found seven defects, three
  serious — including one that moves the registered H2 endpoint by 4.6%. Sol
  reviews what you *report* plus a diff; only probing the running system finds
  the rest (D-015, D-021, D-060).
- **A fix in one layer is not a fix.** The unresolved/effective unit split was
  implemented in collection and never carried into training, so a capacity
  repair silently built the *unrepaired* model — nothing raised, and every
  capacity condition would have been labelled "repair failed" (D-056). When a
  distinction matters, grep for every place it should appear.
- **Test the property, not the mechanism that currently delivers it.** Three
  times now, each written *because* Sol asked for property tests: "evaluation
  can't reach selection" asserted a *parameter name* did not exist; the pool
  non-overlap test checked value overlap while claiming episode comparison; a
  stream test compared `unit` with `Arm("baseline").resolve(unit)`, which is
  the same object. The failure is writing the assertion easiest to express from
  inside the implementation instead of the one that states the claim. Ask: could
  this test fail? (D-055, D-057).
- **One arm passing is not evidence about another.** Repair pairing held for
  data and capacity repair because their experiments exclude the field those
  repairs change. Feature repair changes a field 2A does not exclude, and broke.
  Parametrise over every arm (D-055).
- **Restoring the state is not fixing the mechanism.** The W3 audit found
  `member_predictions` leaving models in eval mode, and fixed it by saving and
  restoring `model.training` — while still running the forward pass under
  `eval()`. Under MC-dropout that is still zero disagreement; measured against
  the old path, **exactly** 0.000e+00. The test passed because it asserted on
  the flag the fix touched. Ask what the mechanism is *for*, then test that
  (D-062).
- **Verify the mechanism of a finding, not only its conclusion.** Sol's rerun
  finding was right about the end state and wrong about the route: the append
  path it named is unreachable through `RunLogger.start`, and the same damage
  arrives through a *different-scope* rerun instead. Had I fixed only what was
  described, the hole would have stayed open (D-062).
- **A null result never proves the null.** I reported "+1.1 SE by episode index"
  as though it established IID episodes. It is *consistent* with them. Where a
  property is structural, assert the structure (D-054).
- **A check that passes because the thing it checks is missing is not a check.**
  Sol refused the gate three times over one shape of defect: identities stamped
  onto whatever was handed in; a manifest checked only against itself; then six
  fields the contract *required to be present* and never compared. Each time the
  fix moved the boundary one layer and stopped short of execution. Ask what
  would have to be true for this check to fail (D-071 … D-073).
- **Correcting a right number to a wrong one still counts as being wrong.** I
  estimated rung 0 at "minutes on CPU", then "corrected" it to ~50 minutes by
  scaling the W3 pilot's rate. It was 4 m 52 s — the first estimate was right.
  The pilot is ~10× slower per fit because it also writes per-transition
  exports and figures. I scaled a rate without asking what it was a rate *of*.
- **Ask whether an assertion could fail.** I wrote
  `assert X is not Y or True` — a tautology — into the very delta where I told
  Sol I had avoided that failure mode (D-055, again, in D-073).
- **Thread count is not numerically neutral.** Re-running certified cells at 4
  threads instead of 8 moved a result by 0.19%. Reduction order differs. Record
  the threading with any result you intend to be reproducible (D-076).
- **A number without its estimand is not a number.** Two consecutive Sol
  findings, both on the same paragraph and neither a coding error: I reported
  `min(N₀,N₁) = 115` as *the* effective sample size when it was a bound
  (D-042), then compared a unit-weighted and a cluster-weighted result and
  called the gap approximation error (D-044). The suite was green throughout
  and the wrong numbers reached five files and a delivered delta. Say what is
  being weighted, or say nothing.

---

## Where the project stands

*Last session: **2026-08-30**. Week 1 Monday was 2026-08-17, so by the calendar
it is **Week 2 Sunday** — the project runs roughly **3 weeks ahead** (DEV-002).
Gate 2's date is 2026-10-24, and gates never move.*

**START HERE — read this before touching anything.**

**2026-08-30 SOL2 UPDATE (read D-133…D-147 and DEV-013…017 before older
claims):** exact Config/Git/run/fit provenance and serialized gate/threshold
evidence were hardened. Week-6 software now includes a source-reverifying
persisted 20-seed repair-label pipeline, one-fit/many-role evidence, a physical
X/y/groups leakage boundary, fresh-process isolation, exact preflight, private
registered launch, crash-durable sync, live-lease protection and evidence-only
monitoring. D-144 corrects the first blocker reading:
**173/300 units lack a model-repair arm, but that is Week-7+/whole-design work,
not a blocker to the registered Week-6 smoke unit or baseline Experiment 1**;
the 30/150 multi-role fits are represented once. C-007 reaches persisted-label evidence
but still lacks the final label-to-`SplitCandidate` bridge. **Deltas 64–67 are
undelivered.** Exact real patch target
`66edf4a11dce39b91974d5c331cca81424f83b6e`; Sol review base `4e55291`.

**Verification:** D-146 stopped the launch with every execution root empty and
fixed five pre-execution gaps. D-147 then corrected a real fail-closed feature-
encoding finalizer defect. The current repository-wide gate passed **1,668
tests, skipped 7 and failed 0 in 1,445.85 s** on the CPU-only Windows host. The
seven skips are three CUDA checks, three unprivileged Windows-symlink cases and
one intentionally vacuous identity case.

**Weeks 1–3 are certified and frozen at `9c0d89d`. WEEKS 4 AND 5 ARE COMPLETE
AND CERTIFIED** (D-120, 2026-08-23). Calendar time is Week 2 Sunday; scheduled
Week 6 begins 2026-09-21. The owner opened Week 6 **readiness** early under
DEV-015/016 and then explicitly authorised real confirmatory execution on the
disclosed frozen local CPU under D-145/DEV-017. Preflight precedes every fit;
the week remains incomplete until execution closes. Certified base is `4e55291`;
no later certified commit may be inferred.

**The prose closeout is CERTIFIED** (D-125): D-121 … D-124, with four documents
accepted **in stated roles**. `docs/method_own_voice.md` is a **student-confirmed
assisted draft — NOT final independently authored thesis prose**;
`docs/method_draft.md` is **scaffolding**; `docs/decision_briefing.md` is
**subordinate to the ledger**; `docs/rewrite_cards.md` is checked guidance.
**Before anything enters the thesis the student must do an independent rewrite
pass, strip the interview/provenance apparatus, and keep only wording they can
personally explain and defend.**

**Scope now:** the student authorised Week-6 integration under DEV-013…016 and
real CPU execution under D-145/DEV-017; external Sol has not reviewed it. The
registered smoke/label and Experiment-1 paths may run only after exact preflight.
Reserve, split registration, threshold changes and expansion remain stopped.
Delta 67 asks Sol to audit the resulting evidence and restart policy. D-146
records the independent stop-before-launch audit and D-147 the first real
fail-closed execution correction. Missing
whole-design model repairs and the final label-to-critic bridge remain later
rulings, not guessed prerequisites.

**W4/W5 are now certified complete (D-120), but preserve the lesson:** that
claim was made prematurely before D-113 checked the schedule's *Done when*
column and found missing work. **The ledger tracks decisions; it does not track
cells.** Verify schedule coverage before declaring a week complete.

**The failure threshold is FROZEN and CERTIFIED:**
`FAILURE_THRESHOLD = 0.610702633857727` in `src/bu/constants.py` (D-107,
certified by D-109). 95th percentile, `method="linear"`, failure is **strictly
greater** — and two calibration transitions sit exactly at the value, so the
strict boundary decides real labels. **Never recalibrate, round, make it
per-layout, or add a caller override.** `ScaledEvaluation.failure_mask()` is the
registered construction and takes no threshold.

**W4 Friday's timing is COMPLETE and attempt-003 is CERTIFIED** (D-119). Sol
verified the record itself — recomputing from the raw repetitions — and ruled it
complete under DEV-011. **No fourth timing attempt is required.** The W5
micro-closeout went back as delta 56, which Sol **certified** (D-120,
2026-08-23) — **Weeks 4 and 5 are complete.**

**Gate 1 = FAIL** (D-098), on the five-point MDE. Reliability PASS, permutation
calibration PASS. **Condition 2 (compute) is NOT ADJUDICABLE across hosts — it
is NOT a PASS** (D-119); it was called "compute PASS" here for several sessions
and that is exactly the dimensional error the harness now refuses to print. Sol
was explicit the gate must **never** be renamed a pass — the MDE failure is
independent. It is **not** the condition-1 pivot: H1's machinery works; what
failed is power. The unchanged **300-unit design continues** under a recorded
power limitation, with **Direction C authorised**.

**Expansion is refused, and the arithmetic matters — including its units.**
A **rough diagnostic extrapolation** suggests on the order of **1,500–2,000
HELD-OUT** units — *not a computed sample-size requirement*, and not total
units. Against 60–80 held out of 300 that is an approximate **5,625–10,000
total, an 18.75×–33.3×** unit-count extrapolation carrying no host. **Do
not convert it into hours and compare it against the 120-hour trigger** — I did,
twice, writing "130–232 local wall-hours against a 120-hour trigger", which puts
**local CPU wall-hours** against a **GPU-hour** trigger. The budget ground rests
on the **registered GPU-hour design estimate and the scope decision**, never on
that arithmetic. I once also wrote "5–6×" by comparing held-out units to the
total design and used it to argue Sol's budget ground away; it was false
(D-115). **Both of Sol's grounds stand.**

**Compute is measured, and is local.** The design costs **5.72 / 6.91 local
wall-hours** (median / conservative maximum) — **not GPU-hours**. The plan names
a Kaggle T4 and **nothing has ever run there** (DEV-011). Local wall-hours and
GPU-hours are different units and **must never be compared as a PASS**; the
record says `comparison_status: not adjudicable across hosts`.

### Gate 1 failed; the exact final-inference MDE remains unsettled

C-006 is built and both D-044 validations pass. Its diagnostic says the design
does not resolve a five-point balanced-accuracy difference at 80% power; at the
scheduled held-out counts its **uncertified optimistic table is 18–22 points**.
Gate 1 is already a signed FAIL (D-098).

**Sample size is the driver in that diagnostic, not correlation.** At ICC = 0
it is still 18 points (19.8 analytic vs 19.0 simulated). Pairing takes it to 8.0
at correlation 0.99; holding out all 300 units gives 6.0 paired. The often-cited
**1,500–2,000 held-out** figure is a rough extrapolation, not a computed
sample-size requirement.

**The current table is optimistic for its Wald procedure** (D-082): its type-I
error is 0.06–0.09 instead of 0.05 at ~20–40 clusters. **Do not infer an exact
"true MDE" or its direction for H3's final procedure**; that procedure is not
registered yet. D-089 permits the table only as a diagnostic and gates any
exact report on the final group-level inference and a validated null size.

### W4 Tuesday's result, certified

**Rung 0 PASSES** on all three configurations (D-074, D-075). rho = **−0.9429**
for uniform, clustered and sparse alike; 90 ensembles / **450 fits in 4 m 52 s**
on CPU. The ladder is **stopped** — rungs 1 and 2 are not to be run.

**Never print a zero-width interval bare.** Two of the three intervals are a
single point, and that is **quantile discreteness, not zero sampling
uncertainty**: the exact bootstrap has only 2–3 distinct values because Spearman
over six sizes has highly discrete support. Sol's sentence for the thesis is
quoted verbatim in D-075 and the atom/mass table must travel with it.

**Clustered seed 4 is reported, not investigated.** 14 of 15 curves peak at
N=250; that one peaks at N=500. Sol ruled: no extra seeds, no smoothing, no
rerun, no estimator change — investigating now would be post-result
exploration. Confirmation waits for W10's confirmatory seeds.

### The evidence contract, and why it took four rounds

The W4 gate went through **four** Sol reviews before certification, each finding
the trust boundary one layer short of execution: bare curves stamped with the
golden ids; then a self-consistent flattened manifest a 90-entry fabrication
still passed; then six fields the contract *advertised* but never compared. All
reproduced before being fixed. The lesson worth carrying: **a check that passes
because the thing it checks is missing is not a check** (D-071 … D-073).

`reliability_gate(evidence, *, rung)` now reconstructs each run from its
canonical `Config`, checks the **complete** `TrainConfig` against the frozen
rung, cross-checks the manifest against run records and metric streams written
at training time, verifies artefact digests, and requires each disagreement to
reproduce from the row it names. `runs/w4_gate/` evidence is **tracked in git**
(1.2 MB) because digests without files cannot be verified from a fresh clone.

**Threading is not numerically neutral and was unrecorded** (D-076). Re-running
certified cells at 4 threads instead of 8 reproduced N=100 exactly and moved
N=250 by 0.19%. Now recorded **additively** — making it a required field would
invalidate the certified attempt, which is Sol's call (delta 40).

**Zero GPU-hours.** Prior official experimental compute is **675 CPU member
fits**: 450 W4 gate plus 225 W4 threshold calibration. D-147 adds **60 Week-6
physical sidecars / 140 member-model trainings**, pending Sol, with no retry or
rerun. These are confirmatory smoke evidence, not development diagnostics.

### Next, in order

1. Preserve D-147 correction commit `7be59bd` plus its governance closeout as
   patches 0008–0009; no finalization may precede a clean package state.
2. Run the zero-fit correction finalizer over all 60 immutable sidecars from
   fit commit `750266c7…`; verify and synchronize only label plus four counts.
3. Recheck Experiment-1's still-empty roots, run immutable preflight, and safely launch the
   150-job Experiment-1 plan with immutable start evidence and monitoring;
   preserve source evidence and a separate-volume synchronized copy.
4. Deliver undelivered deltas **64–67** to external Sol with exact execution
   counts; request review of D-141…D-147 and the restart/host deviation.
5. Complete the student's explain-and-defend walkthrough and preserve
   DEV-012's 0.00 zero-inflation planning convention exactly; it is
   not observed, estimated or pilot-derived.

**Owner authority now covers only the registered Week-6 smoke/label and
Experiment-1 paths.** Do not choose missing model repairs, invent baseline
roles, duplicate multi-role fits, recalibrate the threshold, expand the design,
consume reserve units, or use the splitter/balancer on real inputs.

### What exists in Week 3

- **`models/world_model.py`** — predicts next agent position and activation bits
  only; static attributes are deterministic passthrough and never enter the loss
  (D-032). The auxiliary head reads a **detached** trunk and both losses are
  **action-conditional** — position on movement steps, activation on `interact`
  (D-047). `WorldModel(unit, rng)` requires an `init`-stream generator; depth is
  frozen at 2; there is no loss-weighting knob.
- **`models/train.py`** — takes **separate train and validation datasets**, early
  stopping on the movement-position validation loss **only**, best checkpoint
  restored, no global grad-norm clip, batch order from the `batch` stream
  (D-049, restructured by D-052).
- **`models/ensemble.py`** — K members; **episode block bootstrap** of the
  training pool is the fixed primary for H1/H2, transition-level is a labelled
  secondary that may not overturn a verdict, `"none"` gives an
  initialisation-only sensitivity (D-050, D-053).
- **`collect_pools()`** — three physically separate draws (D-052). Training is
  **exactly the registered N**; validation (40 episodes) and evaluation (100)
  are fixed and byte-identical across every dataset size. Never carve validation
  out of training again: doing so made the held-out set a function of N *and*
  made a "100-transition" condition train on 50.

### Open, and what each blocks

- **The D-035 threshold promotion is CLOSED**, not open. Sol authorised it
  (D-107) and certified it (D-109) on 2026-08-22 after independently verifying
  135 digests and recomputing the percentile to a binary-identical float. This
  bullet described delta 50 as carrying "the only live blocker" for several
  sessions after that was false, then said the live delta was 56 after that too
  had been certified (D-120) — **the live undelivered deltas are 64–67**.
  Deltas 39–63 are all answered or certified (D-089, D-100 … D-102, D-106,
  D-111, D-118 … D-120, D-125, D-131).
- **W4 Friday has run** (D-103) and **will not be rerun** — the threshold has
  been inspected, so Sol's invalidation protocol can no longer be satisfied. The
  number is **frozen and certified**: the D-035 promotion into `constants.py`
  was executed as the D-107 Change Record and certified by Sol (D-109) —
  nothing about the threshold is outstanding. Freezing it was the most
  irreversible act in the project so far, and it is done.
- **Numbers taken before D-051/D-052 are void.** D-020's coverage evidence and
  the Q-011 disagreement measurements were both taken under the non-stationary
  policy and the derived split. Re-measure; do not quote them.
- **D-047's open item is closed** by D-063. The real loop never beat the copy
  baseline — 0 of 15 fits, in every slice at every size — Sol ruled against a
  second trunk, and the head is now a **non-decisional diagnostic**: barred from
  the trunk, from early stopping and checkpoint selection, from the failure set,
  from repair labels and from the critic's residual. Do not resurrect it.
- **The normalising scale is preregistered** (D-061, wording corrected by D-064)
  and **C-010 now enforces it** (D-076). `ScaledEvaluation.from_pool` takes no
  mask, so the scale precedes any mask structurally rather than by ordering, and
  `masked()` reuses that identical object. **Do not add a `scale=None`
  convenience back**, and do not repeat the withdrawn claim that a mask "has
  nothing to recompute from".
- **Repair efficacy may not show on position error.** The recovered repair path
  (D-080) was probed end-to-end on all three arms and the pairing invariants
  hold at real training — including feature repair, the D-055 danger arm. But on
  a `shape`-withheld smoke unit, feature and capacity repair moved position
  error **not at all** while data repair moved it 74.8%. A static attribute
  plausibly does not affect movement dynamics, so for missing-feature failures,
  repair efficacy may need reading on the **activation** task, not position
  alone. Tentative — a whole-pool smoke test with no threshold — but check it
  when real repair validation runs (P§7.3, the failure set needs W4 Friday).
- **C-005 / C-007 / Week 6** — built early under DEV-013…017 and awaiting Sol.
  C-005 has complete feasibility and positive type/seed guards. C-007 now has a
  persisted fit-to-label evidence boundary, but its final label-to-
  `SplitCandidate` bridge is future work. Week-6 current registered software is
  implementation-complete and fail-closed. D-146 adds commit-bound workers,
  crash-durable synchronization, token-only lease release, a fixed production
  smoke launcher/count artifact and an evidence-only Experiment-1 monitor. The
  owner supplied execution authority and selected the frozen CPU route. D-147's
  preflight and all 60 smoke sidecars completed and synchronized; first label
  finalization failed closed on an incorrect feature-encoding equality rule.
  The zero-fit correction is green, no label exists yet, and external
  certification remains pending (D-141…D-147).

Still blocked by Sol, correctly: registered split seed/targets, real critic
splitting, reserve use and later whole-design repair coverage. Owner-authorised
Week-6 smoke/Experiment-1 collection is the disclosed DEV-017 exception.
**The MDE is not among them — that claim was stale.** Sol ruled on all three
questions in **D-089**: the simulation is a **diagnostic**, not H3's estimator;
MDE-vs-margin is a **necessary sensitivity check and explicitly not an
equivalence test**; and reporting an *exact* MDE is **gated on H3's final
inference existing**, which is W15 work, not on any closeout. What is genuinely
unsettled is **H3's final test**, and the exact-MDE report waits on it.

### Three things that will bite if forgotten

**Seeds.** Confirmatory runs use seeds ≥ `CONFIRMATORY_SEED_BASE` (1000).
Everything below is development data, permanently excluded from confirmatory
results, threshold calibration, repair acceptance and the critic (D-034). Week 3
runs low seeds deliberately. Analyses that reach the thesis pass
`require_confirmatory=True` to `load_runs()`.

**Effective sample size.** Never quote one without naming the estimand. The
weighting is preregistered as `BALANCED_ACCURACY_WEIGHTING = "unit"` (D-044);
under it the ICC = 1 boundary is 75/72.6. The cluster counts 125/115 belong to an
equal-cluster-weighted estimand the thesis does not use. The registered
statistical unit is still the configuration-condition and unit-level balance is
still 150/150. Power is **simulated** at W5 — there is deliberately no `n_eff()`.

**Comparison groups.** Units sharing one were *given* related data by design, so
a group must never span a critic split or a CV fold (D-039).
