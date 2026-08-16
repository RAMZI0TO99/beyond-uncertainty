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
5. Tell the student in two lines where things stand and what you think is next.
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
.venv/bin/python -m pytest -q                      # 344 passing, 1 skipped
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
  models/train.py        episode-strided split, early stopping on position only
  models/ensemble.py     K members from the bootstrap / init / batch streams
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
- **A number without its estimand is not a number.** Two consecutive Sol
  findings, both on the same paragraph and neither a coding error: I reported
  `min(N₀,N₁) = 115` as *the* effective sample size when it was a bound
  (D-042), then compared a unit-weighted and a cluster-weighted result and
  called the gap approximation error (D-044). The suite was green throughout
  and the wrong numbers reached five files and a delivered delta. Say what is
  being weighted, or say nothing.

---

## Where the project stands

Weeks 1 and 2 complete and audited, and **all three** of Sol's 2026-08-16
reviews actioned in full (D-025 … D-041). **Zero compute consumed** — nothing has
trained. Gate 1 is 2026-09-19. Design: 300 units, **240 comparison groups**,
**8,197 fits** against ~8,700. No open questions.

**The statistical unit is still the configuration-condition** — 150/150 on
intended class, and that is the registered quantity (P§10.7, §2). Units sharing
a comparison group are **correlated, not collapsed**: 300 units sit in 240
groups, and 125/115 are *cluster* counts.

**Do not quote any effective sample size without naming the estimand.** The
weighting is preregistered as `BALANCED_ACCURACY_WEIGHTING = "unit"` (D-044),
under which the ICC = 1 boundary is 75/72.6; the cluster counts 125/115 are the
boundary for an equal-cluster-weighted estimand, which the thesis does not use.
Power is **simulated directly** at W5 — there is deliberately no `n_eff()`
helper. A comparison group must never span a critic split or a CV fold.

**Next: Week 3, the world model. Nothing blocks it.**

W3 Mon the MLP — **D-032 fixes what it predicts**: next agent position and
activation bits only; static object attributes are deterministic passthrough and
never enter the loss or the error score. The primary error is on agent position,
over movement transitions, grid-normalised; activation is a secondary metric.
This is not a stylistic choice — 26 of 30 output dims never change within an
episode, so full-state MSE dilutes the passability rule ~15-fold and rescales it
between families as withholding changes the observation width (30 dims vs 22).

**W3 Mon is done** (D-046, D-047). The model predicts agent position and
activation bits; the auxiliary head reads a **detached** trunk and both losses
are **action-conditional** — position on movement steps, activation on
`interact` steps. `WorldModel(unit, rng)` requires a generator from the `init`
stream; depth is frozen at 2 and there is no loss-weighting knob.

W3 Tue the training loop, and **D-047 binds it**: stop on movement-position
validation loss only, never on activation; no global grad-norm clip across both
parameter groups; fail loudly on a batch with no movement transitions; split
**by episode, not by transition**, or early stopping leaks. Open item carried
in: the detached head is worse than its copy baseline (0.2575 vs 0.1652) after
a hand-rolled 3,000 epochs — Sol's conditional for a second trunk turns on
whether a real loop closes that, and must not be settled from a probe.

**W3 Tue and Wed are done** (D-049, D-050). Split is **by episode and strided**
— a transition split measured 4.5–8.7× optimistic, worst at small n, which is
the direction that corrupts Experiment 1. Ensemble members draw from three
separate streams so diversity can be attributed.

**W3 Fri is the first cell that consumes real compute** — 6 sizes × 3 seeds × 5
members = 90 fits, ~30s on a free GPU or ~10 min CPU. **Ask the student before
starting it**; their GPU has been at ~14/16 GB under another workload all week.

**Q-011 is open and blocks nothing yet, but it blocks W4 Mon's trend test.**
Bootstrap granularity changes disagreement — H1's dependent variable — and the
episode/transition ratio is *not constant across n* (1.30× / 1.77× / 1.25×), so
it bends the curve the trend test runs on rather than merely scaling it.

**Confirmatory runs use seeds ≥ `CONFIRMATORY_SEED_BASE` (1000).** Everything
below is pilot data and may never enter a confirmatory result, the threshold
calibration, repair acceptance, or the critic (D-034). Week 3 development runs
at low seeds deliberately. Pass `require_confirmatory=True` to `load_runs()` in
every analysis that reaches the thesis (D-040).

Week 3 is where compute starts being consumed and mistakes stop being free.
