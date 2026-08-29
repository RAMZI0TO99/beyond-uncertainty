# Beyond Uncertainty

Diagnosing when embodied world models need more data or a different model.

Bachelor's thesis code. When a model-based RL agent's world model mispredicts,
should it gather more experience (estimation failure, f\* ∈ H) or change the
model class (hypothesis-class failure, f\* ∉ H)? This repository builds the
environments, the failure families, the counterfactual repair protocol that
establishes ground-truth labels, and the learned diagnosis critic that predicts
which repair is required.

## Orientation

| File | What it is |
|---|---|
| `CLAUDE.md` | **Claude starts here.** Operational handoff: checklist, commands, hard rules, traps |
| `PROJECT_STATE.md` | Project state: snapshot, frozen constants, deviations, gates, open questions |
| `DECISIONS.md` | The decisions ledger, append-only. `PROJECT_STATE.md` §3 indexes it |
| `DELTA_TO_SOL.md` | The only thing the student pastes to Sol. Accumulates until delivered |
| `scripts/sol_bundle.sh` | Generated verification bundle: commit, tree state, tests, diff |
| `SOL_BRIEF.md` | Operating brief for the reviewing agent |
| `PROJECT_STATE_ARCHIVE.md` | Delivered deltas and closed session history |
| `docs/thesis_project_plan_v1_2.docx` | The research design. Authoritative for design |
| `docs/thesis_day_by_day_schedule_v1_2.docx` | The 20-week execution schedule |
| `src/bu/constants.py` | **The preregistration, in code.** Changing anything here needs a Change Record |

## Install

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Then see the design matrix the experiments draw on:

```bash
.venv/bin/python -m bu.experiments.enumerate_units
```

`--system-site-packages` reuses an existing CUDA-enabled torch rather than
downloading one. For a fully isolated environment drop the flag; `pyproject.toml`
pins every version.

## The four identities

Most of the analysis discipline in this project follows from these distinctions,
so they are worth understanding before reading any other module:

```python
from bu import Config, UnitSpec, Arm

unit = UnitSpec(family="missing_feature", withheld_features=("shape",), n_transitions=500)

Config(unit=unit, arm=Arm("baseline")).unit_id        # ─┐
Config(unit=unit, arm=Arm("data_repair")).unit_id     #  ├─ identical
Config(unit=unit, arm=Arm("feature_repair")).unit_id  # ─┘
```

- **`unit_id`** — the configuration-condition. This is the statistical unit for
  every confidence interval in the thesis, and the level at which class
  balancing happens. A failure condition and its repairs share one, which is
  what makes a ground-truth label assignable to it.
- **`config_id`** — `unit_id` plus which arm (baseline, or which repair).
- **`run_id`** — `config_id` plus **stage** and seed, so a record states which
  experimental obligation it discharges.
- **`fit_id`** — `config_id` plus the seed, with **no stage**: the identity of the
  *computation*. One unit can owe 5 seeds to an H1/H2 claim and 20 to repair
  validation, and the twenty **contain** the five — one set of fits wearing two
  roles, not 25 runs. Conflating `run_id` with `fit_id` once cost 375 phantom fits.

Confidence intervals are taken over `unit_id`, never over transitions. Units that
share a **comparison group** were deliberately given related data, so a group must
never span a train/test split — see `src/bu/streams.py`.

## Seeds

Confirmatory runs use seeds ≥ `CONFIRMATORY_SEED_BASE` (1000). **Every seed below
it is development data**, permanently excluded from confirmatory runs, threshold
calibration, repair acceptance and the critic. Analyses that reach the thesis pass
`require_confirmatory=True` to `load_runs()`.

## Running something

```python
from bu import Config, UnitSpec, RunLogger, load_runs

cfg = Config(unit=UnitSpec(n_transitions=1000), seed=0)
with RunLogger.start(cfg) as log:
    log.log(epoch=0, split="val", mse=0.42)

df = load_runs("runs")   # every run, long format, identity columns attached
```

`RunLogger.start` writes the run record before the first metric, so a log never
exists without the config, seed, commit hash and package versions that produced
it. Records flush line by line — a killed Kaggle session loses nothing already
written.

## Layout

```
src/bu/
  constants.py    preregistered values; one file, deliberately
  config.py       Config / UnitSpec / Arm and the three identities
  runrecord.py    provenance: config, seed, git commit, dirty flag, packages
  metrics.py      JSONL logging and load_runs()
  streams.py      named RNG streams: env / policy / bootstrap / init / batch
  env/            gridworld, masking encoder, policy, collector   (Weeks 1–2)
  models/         world model, training loop, bootstrap ensemble  (Week 3)
  stats/          trend test, acceptance test                     (Weeks 4–5)
  critic/         diagnosis critic and baselines                  (Weeks 11–12)
  experiments/    the 300-unit design matrix and drivers
runs/             run outputs — gitignored, regenerable
figures/          all regenerated from logs — gitignored
```
