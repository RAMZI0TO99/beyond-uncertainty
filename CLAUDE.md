# CLAUDE.md — operational handoff

You are Claude, working on a Bachelor's thesis in AI with a student and a second
agent called Sol. **You have no memory of previous sessions.** This file and
`PROJECT_STATE.md` are how you recover. Read both before doing anything.

---

## First five minutes, in order

1. **Read `PROJECT_STATE.md` top to bottom.** §1 is where the project stands, §2
   is what you may not change, §3–§5 are what past-you already decided.
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
or repeat, if `PROJECT_STATE.md` exceeds 500 lines, if decision ids have gaps,
or if §2's frozen constants disagree with `src/bu/constants.py`.

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
  §3 naming the constant, the new value, the reason, and *whether data has been
  seen*. If data has been seen, the answer is almost certainly no.
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
.venv/bin/python -m pytest -q                      # 204 passing, 1 skipped
.venv/bin/python -m bu.experiments.enumerate_units # design matrix report
./scripts/sol_bundle.sh src/bu/config.py           # verification bundle for Sol
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
  models/ stats/    empty — Week 3 and Weeks 4–5
```

**The three identities, which most analysis discipline follows from:**
`unit_id` is the configuration-condition — the statistical unit for every
confidence interval, **shared by a failure condition and all its repair arms**,
which is what makes a label assignable. `config_id` adds the arm. `run_id` adds
stage *and* seed — stage matters because one unit can owe five seeds to an H1/H2
claim and twenty to repair validation, overlapping on seeds 0–4.

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

---

## Where the project stands

Weeks 1 and 2 complete and audited, and Sol's 2026-08-16 review actioned in
full (D-025 … D-031). **Zero compute consumed** — nothing has trained. Gate 1
is 2026-09-19. Design: 300 units, 150/150, **8,572 fits** against ~8,700.

**Next: Week 3, the world model — but two things come first.**

1. **Build the D-030 named-stream module.** Sol answered Q-008: named streams
   for environment / policy / bootstrap / weight-init, `(unit_id, seed, purpose)`
   for sweep-only units, a preregistered `comparison_group_id` for paired
   canonical comparisons, and `arm` **never** in the failure-set stream. It is
   decided and *unbuilt*, and W3 Wed's ensemble is the first consumer.
2. **Settle Q-009 before the MLP.** 26 of 30 output dims never change within an
   episode; an identity predictor scores MSE 0.0047 and 92.6% of its residual is
   the two agent-position dims. So the rule lives in 2 of 30 dims, and obs dim
   differs by family (30 vs 22), so the error *scale* differs between families
   for encoding reasons. P§10.1's failure threshold freezes permanently W4 Fri.

Then W3 Mon the MLP, W3 Tue the training loop — **split by episode, not by
transition**, or early stopping leaks — W3 Wed the bootstrap ensemble, W3 Fri
disagreement metrics and the first curves.

Week 3 is where compute starts being consumed and mistakes stop being free.
