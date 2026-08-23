# CLAUDE.md — operational handoff

You are Claude, working on a Bachelor's thesis in AI with a student and a second
agent called Sol. **You have no memory of previous sessions.** This file and
`PROJECT_STATE.md` are how you recover. Read both before doing anything.

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
| **You** | Hold the repo. All implementation, run orchestration, logging, prose drafts |
| **Sol** (ChatGPT, one persistent session) | Adversarial reviewer. Never writes project code. **Remembers everything you forget** |
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
.venv/bin/python -m pytest -q                      # 895 passing, 2 skipped, 0 xfailed
.venv/bin/python -m bu.experiments.enumerate_units # design matrix report
BASE=c5c8e6f ./scripts/sol_bundle.sh              # bundle for Sol; c5c8e6f is CERTIFIED
```

- venv is `--system-site-packages` (reuses CUDA torch); `pyproject.toml` pins all.
- Git identity is set repo-locally to the student. **`git pull --rebase` needs
  it** — a rebase stalled once because the machine had none configured.
- Auth is an SSH key at `~/.ssh/id_ed25519_github`. **Never accept a token.**
- `.claude/settings.local.json` is untracked and rewrites itself; it can dirty
  the tree mid-command. Harmless.
- Remote: `RAMZI0TO99/beyond-uncertainty`, private, branch `main`.

---

## What exists

```
src/bu/
  constants.py   the preregistration, in one file, deliberately
  config.py      UnitSpec / Arm / Config; the three identities; stage registry
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
                    null. Three conditions, all required; episode-mean fallback
                    is a labelled different method; permutes whole runs, never
                    transitions (D-079)
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

*Last session: **2026-08-22**. Week 1 Monday was 2026-08-17, so by the calendar
it is **Week 1 Saturday** — the project runs roughly **4 weeks ahead** (DEV-002).
Gate 2's date is 2026-10-24, and gates never move.*

**START HERE — read this before touching anything.**

**Weeks 1–3 are certified and frozen at `9c0d89d`. WEEKS 4 AND 5 ARE COMPLETE
AND CERTIFIED** (D-120, 2026-08-23). **No week is open** — the first time since
Week 3. The certified base is **`c5c8e6f`**; Sol named that exact commit
(D-125) and said a later one **must not be inferred**.

**The prose closeout is CERTIFIED** (D-125): D-121 … D-124, with four documents
accepted **in stated roles**. `docs/method_own_voice.md` is a **student-confirmed
assisted draft — NOT final independently authored thesis prose**;
`docs/method_draft.md` is **scaffolding**; `docs/decision_briefing.md` is
**subordinate to the ledger**; `docs/rewrite_cards.md` is checked guidance.
**Before anything enters the thesis the student must do an independent rewrite
pass, strip the interview/provenance apparatus, and keep only wording they can
personally explain and defend.**

**Nothing is authorised to be built.** Q-012 was ruled **against** building
C-005/C-007: they do not consume data, but they are **future-week
implementation**, which is the verification lag Q-004 names. Sol's sentence —
*completing W4/W5 obligations repaired omissions; it did not authorise pulling
later implementation forward*. **Prose, review and read-only audit only. No
source code, no executable tests, no real data, no labels, no reserve.**

**Do not write anywhere that W4/W5 are finished until Sol certifies.** That
claim was already made prematurely once: §1 carried *"Weeks 1–5 are complete"*
for many sessions until D-113 checked the schedule's own *Done when* column and
found W4 Friday's timing harness and W5 Friday's balancer had never been built,
and that the acceptance-model change had no deviation record. **The ledger tracks
decisions; it does not track cells.** Nothing checks schedule coverage.

**The failure threshold is FROZEN and CERTIFIED:**
`FAILURE_THRESHOLD = 0.610702633857727` in `src/bu/constants.py` (D-107,
certified by D-109). 95th percentile, `method="linear"`, failure is **strictly
greater** — and two calibration transitions sit exactly at the value, so the
strict boundary decides real labels. **Never recalibrate, round, make it
per-layout, or add a caller override.** `ScaledEvaluation.failure_mask()` is the
registered construction and takes no threshold.

**W4 Friday's timing is COMPLETE and attempt-003 is CERTIFIED** (D-119). Sol
verified the record itself — recomputing from the raw repetitions — and ruled it
complete under DEV-011. **No fourth timing attempt is required.** **W5 is open
for one micro-closeout**, returned as **delta 56**, which is undelivered.

**Gate 1 = FAIL** (D-098), on the five-point MDE. Reliability PASS, permutation
calibration PASS. **Condition 2 (compute) is NOT ADJUDICABLE across hosts — it
is NOT a PASS** (D-119); it was called "compute PASS" here for several sessions
and that is exactly the dimensional error the harness now refuses to print. Sol
was explicit the gate must **never** be renamed a pass — the MDE failure is
independent. It is **not** the condition-1 pivot: H1's machinery works; what
failed is power. The unchanged **300-unit design continues** under a recorded
power limitation, with **Direction C authorised**.

**Expansion is refused, and the arithmetic matters — including its units.**
Clearing five points needs **1,500–2,000 HELD-OUT** units — not total. Against
60–80 held out of 300 that is **5,625–10,000 total units, 18.75×–33.3×**. That
multiplier is a ratio of **unit counts** and carries no host, so it stands. **Do
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

### ⚠ The biggest open thing: Gate 1 is at risk (D-078)

C-006 is built and both of D-044's validations pass — and the answer is that
**the design cannot resolve a five-point balanced-accuracy difference at 80%
power.** At the scheduled held-out counts the MDE is **18–22 points**.

**Sample size is the driver, not correlation.** At ICC = 0 it is still 18
points, so the conclusion does not rest on the parameter least knowable before
data. Checked against hand arithmetic (19.8 analytic vs 19.0 simulated). Every
lever tested: pairing takes it to 8.0 at correlation 0.99; holding out *all 300*
units gives 6.0 paired. Clearing five points conservatively needs on the order
of **1,500–2,000 held-out units** against the 60–80 scheduled.

**The numbers are if anything optimistic** (D-082 audit). The power test is
anti-conservative — type-I error 0.06–0.09 vs 0.05, worse at higher ICC —
because it uses a Wald `1.96×SE` rule rather than D-044's group-bootstrap
percentile, and both over-reject at ~20–40 clusters. So the true MDE is *larger*
than 18–22; the risk is real, not a simulation artefact.

**Do not act on this number.** P§14.3's remedy is configuration count — never
seeds — but that is the student's and Sol's decision, and **three** things need
adversarial review first: whether the simulated estimand is the one H3's test
will use, whether comparing an **MDE** against an **equivalence margin** is
coherent at all, and (D-082) which inference procedure the MDE should use, since
the current one over-rejects. The plan frames it that way (P§10.7) and the simulation follows
the plan exactly; if the framing is wrong, the table is the right computation of
the wrong thing.

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

**Zero GPU-hours.** The only compute ever spent is 450 CPU fits (W4 Tue) plus
~25 CPU fits of smoke and probe work in scratch directories.

### Next, in order

*Rewritten 2026-08-22 at session end. **This list has now gone stale three
times** — it has twice described work as blocked that had already run. Nothing
mechanical catches that, because the protocol suite checks §1's structure and
never its truth. **So read it as a dated snapshot, not as state.** If the ledger
disagrees, the ledger wins: check the highest D-number in `DECISIONS.md` and the
newest §7 entry in `PROJECT_STATE.md` before trusting anything here.*

**As of 2026-08-23, W4 and W5 are certified complete and NOTHING is authorised
to be built.** This is not a lull to fill with implementation — it is the
allocation Sol ruled.

1. **Do not build C-005 or C-007.** Q-012 is closed (D-120). I asked, reasoning
   they consume no data; Sol said no, because **data consumption is a necessary
   bar and not a sufficient one** — the operative question is whether the work
   is *this* week's obligation or a *later* week's. C-005/C-007 begin at their
   scheduled time or on a **fresh explicit authorisation**.
2. **What IS authorised:** methodology prose in the student's own voice,
   consolidating certified decisions, checking prose against plan and schedule,
   **prose-only** interface and acceptance-criteria specs for C-005/C-007,
   read-only audits, and resolving contradictions before they become code.
3. **The base is `c5c8e6f`** and **delta 61 accumulates** — Sol requires no
   closeout for delta 60, and the next bundle accompanies the next genuinely
   authorised work. Do not infer a later base; D-043 exists because a
   challenged commit was nearly used as one.
6. **AUTHORISED NOW: the plan/schedule `.docx` audit** (D-125) — read-only and
   prose-only. Compare the certified methodology against the source plan and
   schedule, record contradictions, propose prose corrections. **Not** a route
   into later-week implementation.
4. **The exclusion-rate assumption is settled** — ratified by Sol as **DEV-012**,
   a **zero-inflation planning convention** of 0.00, never to be described as
   observed, estimated or pilot-derived. **S§W6 Monday checks batch 1 against
   it**, so it must survive intact to Week 6.
5. **Week 6 execution stays closed.** Q-004 was re-ruled on 2026-08-22 and still
   bars it. Finishing missed W4/W5 obligations is authorised; starting Week 6 is
   not. C-005 and C-007 remain W6–W11 work. C-003, C-006, C-008 … C-011 are done.

**Do not, without a fresh Sol ruling:** recalibrate the threshold, expand the
design, consume reserve units, generate repair labels, or run anything on real
labelled data. The balancer is synthetic-inputs-only until C-005 exists.

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
  sessions after that was false — **the live delta is 56**. Deltas 39–55 are all
  answered (D-089, D-100 … D-102, D-106, D-111, D-118, D-119).
- **W4 Friday has run** (D-103) and **will not be rerun** — the threshold has
  been inspected, so Sol's invalidation protocol can no longer be satisfied. The
  number is calibrated but **not frozen**: promotion into `constants.py` is the
  outstanding D-035 Change Record. Freezing it remains the most irreversible act
  in the project so far.
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
- **C-005 / C-007** — the grouped critic splitter and the remaining
  confirmatory-guard call sites in the critic loaders. W6–W11 work. Everything
  else on the obligation list is **done**: C-003 (D-092), C-006 (D-078), C-008
  (D-096), C-009 (D-077), C-010 (D-076), C-011 (D-072).

Still blocked by Sol, correctly: confirmatory collection and critic splitting.
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
