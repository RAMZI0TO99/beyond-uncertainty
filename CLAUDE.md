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
.venv/bin/python -m pytest -q                      # 394 passing, 1 skipped
.venv/bin/python -m bu.experiments.enumerate_units # design matrix report
BASE=<last-CERTIFIED-commit> ./scripts/sol_bundle.sh # verification bundle for Sol
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
  models/ensemble.py     K members; episode block bootstrap of the training pool
  stats/            empty — Weeks 4–5
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
- **A null result never proves the null.** I reported "+1.1 SE by episode index"
  as though it established IID episodes. It is *consistent* with them. Where a
  property is structural, assert the structure (D-054).
- **A number without its estimand is not a number.** Two consecutive Sol
  findings, both on the same paragraph and neither a coding error: I reported
  `min(N₀,N₁) = 115` as *the* effective sample size when it was a bound
  (D-042), then compared a unit-weighted and a cluster-weighted result and
  called the gap approximation error (D-044). The suite was green throughout
  and the wrong numbers reached five files and a delivered delta. Say what is
  being weighted, or say nothing.

---

## Where the project stands

*Last session: 2026-08-16. Week 1 Monday is 2026-08-17, so the project is
running roughly two weeks ahead of its own calendar (DEV-002).*

**Weeks 1 and 2 complete and audited. Week 3 Mon, Tue and Wed done** — then
substantially corrected by Sol's sixth and seventh reviews. Seven Sol reviews
actioned on 2026-08-16 (D-025 … D-054). **`2875e60` is the certified base** — Sol
certified the Week 3 Mon–Wed infrastructure on 2026-08-16, covering D-047 …
D-057 in full. Use it as `BASE` for the next bundle.

**Certification is scoped.** It authorises the W3 Friday development pilot on
development seeds. It does **not** authorise confirmatory execution or repair
validation: `bootstrap_episodes()` plus `train(train_index=…)` still bypasses
the `train_ensemble` granularity guard, and the confirmatory runner (C-008) must
own that rule plus registered configuration, matching pools, seed policy and
complete run records. **Sol permits the W3 Friday pilot on development seeds only**;
confirmatory execution and repair validation stay blocked until D-055 is
bundled from `BASE=9bdb22a`. Gate 1 is 2026-09-19. **Zero GPU-hours consumed** —
everything so far runs on CPU in seconds.

**The correction is the thing to understand before touching Week 3 code.** The
behaviour policy was **non-stationary across episodes**, and because Experiment
1's datasets are nested prefixes, *dataset size was confounded with behaviour
distribution* — rule-carrying transitions per step ran 0.520 at N=100 against
0.280 at N=5000. I had diagnosed this as a splitting problem and been wrong; it
was a data-generation problem. Fixed in D-051 and verified as stationarity
(+1.1 SE by episode index over 40 seeds), not asserted.

Design: **300 units** in **240 comparison groups**, **8,197 fits** against
P§14.2's ~8,700.

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

### Next: W3 Fri — and it is the first cell that spends compute

6 sizes × 3 seeds × 5 members = **90 fits**, ~30s on a free GPU or ~10 min CPU.
**Ask the student before starting it.** Their GPU has been at ~14/16 GB and 91%
under another workload all week; scan with `nvidia-smi` and stay off it unless
they say otherwise. Then W3 Sat: look at the curves and write down what you see
*before* any formal test.

### Open, and what each blocks

- **No open questions.** Q-011 closed by D-053.
- **Numbers taken before D-051/D-052 are void.** D-020's coverage evidence and
  the Q-011 disagreement measurements were both taken under the non-stationary
  policy and the derived split. Re-measure; do not quote them.
- **D-047's open item.** The detached auxiliary head sits at 0.2575 against a
  0.1652 copy baseline after a hand-rolled 3,000 epochs. Sol's conditional for a
  second trunk turns on whether the *real* loop closes that — answer it from
  Friday's runs, not from a probe.
- **C-005 / C-006 / C-007** — grouped critic splitter, the ICC-sensitive grouped
  MDE simulation, and passing `require_confirmatory=True` at each analysis call
  site as it is built. None is Week 3 work.

Still blocked by Sol, correctly: confirmatory collection, critic splitting, and
W5 MDE approval.

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
