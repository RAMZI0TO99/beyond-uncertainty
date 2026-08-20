"""W4 Friday: calibrate the failure threshold, once, and never again (P§10.1).

**This is the most irreversible act in the project.** P§10.1 sets the failure
threshold at a fixed percentile of the error distribution on a well-fit
reference model, "set once, in Month 1, on reference data, and not tuned
afterwards", precisely so it cannot become an unreported degree of freedom. Every
failure set, every repair label and therefore every H2 and H3 claim is downstream
of the number this produces.

So this module is built to be **hard to run by accident and impossible to run
vaguely**:

* the **percentile is a required argument with no default**. It is the single
  most consequential choice here, and neither P§10.1 nor S§W4 names a value --
  the plan says "a fixed percentile" and the schedule says to write it to a
  constants file. A default would make that choice silently, in code, which is
  the exact failure D-035 lists the percentile among the things W4 Friday must
  *freeze deliberately*.
* it calibrates on **confirmatory seeds only**. D-034 permanently excludes every
  seed below `CONFIRMATORY_SEED_BASE` from threshold calibration, and C-007
  requires the guard at this call site rather than a comment about it.
* it **does not write `constants.py`**. It returns evidence. Promoting a number
  to a frozen constant is a deliberate human act under a Change Record (D-035),
  not a side effect of running a script.
* it refuses a **dirty tree**, like the gate: a threshold that cannot name one
  reproducible code state is not calibrated, it is merely computed.

What is deliberately NOT decided here
-------------------------------------
Two things this module takes as inputs because the plan does not determine them,
and inventing either would be exactly the unreported degree of freedom P§10.1
exists to prevent:

1. **the percentile value** -- see above;
2. **what counts as a "well-fit reference model"** -- this module's answer is the
   fully-observed estimation family at the largest registered dataset size,
   balanced over the preregistered strata per D-035. That is a reading of
   P§10.1's "well-fit... in the same environment", not a quotation of it.

Both are flagged for Sol before execution. The machinery below is complete and
tested; the two values are not chosen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch

from .. import constants as K
from ..config import Config, FEATURES, LAYOUTS, TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..models.ensemble import assert_pools_match, train_ensemble
from ..models.uncertainty import ScaledEvaluation, normalised_error
from ..models.world_model import MOVEMENT_ACTIONS
from ..runrecord import git_state

#: Reused rather than minted: a fully-observed estimation unit at the largest
#: registered size IS an Experiment 1 unit, so no new stage identity is created.
THRESHOLD_STAGE = "exp1"

#: The reference condition. "Well-fit" is read as the largest registered dataset
#: size; "fully observed" as the estimation family with nothing withheld and no
#: confound. D-035 requires balance over the preregistered environment strata so
#: that no single reference configuration dominates the percentile.
REFERENCE_FAMILY = "estimation"
REFERENCE_SIZE = max(K.DATA_SIZES)
REFERENCE_CONFOUND_RATE = 0.0


def reference_strata() -> tuple[tuple[str, str], ...]:
    """(layout, causal_attribute) -- the strata the calibration pool balances over."""
    return tuple((layout, attr) for layout in LAYOUTS for attr in FEATURES)


def reference_units() -> tuple[UnitSpec, ...]:
    """One fully-observed, well-fit reference unit per stratum."""
    return tuple(
        UnitSpec(
            family=REFERENCE_FAMILY,
            layout=layout,
            causal_attribute=attr,
            confound_rate=REFERENCE_CONFOUND_RATE,
            n_transitions=REFERENCE_SIZE,
            withheld_features=(),
        )
        for layout, attr in reference_strata()
    )


@dataclass(frozen=True)
class StratumErrors:
    """One reference cell's normalised movement errors, and what produced them."""

    layout: str
    causal_attribute: str
    seed: int
    errors: np.ndarray
    run_id: str
    config_id: str
    unit_id: str

    def __len__(self) -> int:
        return int(self.errors.shape[0])


@dataclass(frozen=True)
class ThresholdCalibration:
    """The calibrated number, and everything needed to audit or refuse it."""

    threshold: float
    percentile: float
    n_per_stratum: int
    strata: tuple[tuple[str, str], ...]
    seeds: tuple[int, ...]
    n_total: int
    commit: str
    cells: tuple[dict, ...] = field(default=())

    def as_row(self) -> dict:
        return {
            "threshold": self.threshold,
            "percentile": self.percentile,
            "n_per_stratum": self.n_per_stratum,
            "n_strata": len(self.strata),
            "strata": [list(s) for s in self.strata],
            "seeds": list(self.seeds),
            "n_total": self.n_total,
            "commit": self.commit,
            "reference_family": REFERENCE_FAMILY,
            "reference_size": REFERENCE_SIZE,
            "stage": THRESHOLD_STAGE,
            "cells": list(self.cells),
        }

    def summary(self) -> str:
        return (
            f"FAILURE THRESHOLD (NOT YET FROZEN)\n"
            f"  percentile {self.percentile}  ->  threshold {self.threshold:.6f}\n"
            f"  balanced pool: {len(self.strata)} strata x {self.n_per_stratum} "
            f"transitions = {self.n_total}\n"
            f"  seeds {list(self.seeds)} (confirmatory), commit {self.commit[:7]}\n"
            f"  This number is EVIDENCE, not a constant. Freezing it into "
            f"constants.py is a Change Record under D-035."
        )


def _require_confirmatory(seeds) -> tuple[int, ...]:
    """C-007 at this call site. D-034 excludes development seeds permanently."""
    seeds = tuple(int(s) for s in seeds)
    if not seeds:
        raise ValueError("no seeds; there is nothing to calibrate on")
    development = [s for s in seeds if s < K.CONFIRMATORY_SEED_BASE]
    if development:
        raise ValueError(
            f"seeds {development} are below CONFIRMATORY_SEED_BASE "
            f"({K.CONFIRMATORY_SEED_BASE}). D-034 permanently excludes development "
            "seeds from threshold calibration: the threshold is frozen forever, so "
            "calibrating it on pilot data would bake development noise into every "
            "failure set the thesis reports"
        )
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"duplicate seeds {seeds}; each seed contributes once")
    return seeds


def score_reference_cell(unit: UnitSpec, *, seed: int) -> StratumErrors:
    """Train one reference model and return its normalised movement errors.

    The scale is built by `ScaledEvaluation.from_pool`, which takes no mask, so
    it is measured on the FULL movement evaluation pool before any failure mask
    exists -- which is the point, because the mask does not exist yet: it is what
    this calibration is about to define (D-061, C-010).
    """
    config = Config(
        unit=unit, seed=seed, stage=THRESHOLD_STAGE,
        train=TrainConfig(ensemble_size=1),
    )
    pools = collect_pools(unit, stage=THRESHOLD_STAGE, seed=seed, arm="baseline")
    assert_pools_match(pools, unit=unit, arm="baseline", stage=THRESHOLD_STAGE, seed=seed)
    ensemble = train_ensemble(
        unit, pools, config.train, stage=THRESHOLD_STAGE, seed=seed,
        arm="baseline", granularity="episode",
    )
    obs = torch.as_tensor(pools.evaluation.obs)
    action = torch.as_tensor(pools.evaluation.action)
    next_obs = torch.as_tensor(pools.evaluation.next_obs)
    move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))

    members = ensemble.member_predictions(obs[move], action[move])
    targets = ensemble.members[0].targets(next_obs[move])[0]
    scale = ScaledEvaluation.from_pool(
        members, targets, n_transitions=unit.n_transitions, seed=seed
    ).scale
    errors = normalised_error(members.mean(dim=0), targets, scale)
    return StratumErrors(
        layout=unit.layout, causal_attribute=unit.causal_attribute, seed=seed,
        errors=errors.detach().numpy(), run_id=config.run_id,
        config_id=config.config_id, unit_id=config.unit_id,
    )


def balance(cells: list[StratumErrors], *, n_per_stratum: int | None = None,
            rng: np.random.Generator | None = None) -> tuple[np.ndarray, int]:
    """Equal transitions per stratum, so no configuration dominates (D-035).

    Pooling raw errors would weight each stratum by how many transitions it
    happened to produce, which makes the threshold a function of the design's
    incidental composition rather than of the error distribution. Strata are
    subsampled to a common count instead, without replacement.
    """
    if not cells:
        raise ValueError("no reference cells; there is nothing to balance")
    by_stratum: dict[tuple[str, str], list[np.ndarray]] = {}
    for c in cells:
        by_stratum.setdefault((c.layout, c.causal_attribute), []).append(c.errors)
    pooled = {k: np.concatenate(v) for k, v in by_stratum.items()}

    available = min(len(v) for v in pooled.values())
    n = available if n_per_stratum is None else int(n_per_stratum)
    if n <= 0:
        raise ValueError(f"n_per_stratum must be positive, got {n}")
    if n > available:
        short = sorted(k for k, v in pooled.items() if len(v) < n)
        raise ValueError(
            f"n_per_stratum={n} exceeds the {available} transitions available in "
            f"stratum(a) {short}. Sampling with replacement, or letting the short "
            "stratum contribute everything it has, would silently unbalance the "
            "pool the threshold is defined on (D-035)"
        )
    rng = rng or np.random.default_rng(0)
    drawn = [
        pooled[k][rng.choice(len(pooled[k]), size=n, replace=False)]
        for k in sorted(pooled)
    ]
    return np.concatenate(drawn), n


def calibrate(
    *,
    percentile: float,
    seeds,
    n_per_stratum: int | None = None,
    units: tuple[UnitSpec, ...] | None = None,
    score_fn=None,
    allow_dirty: bool = False,
    rng: np.random.Generator | None = None,
) -> ThresholdCalibration:
    """Calibrate the failure threshold. **Returns evidence; freezes nothing.**

    Args:
        percentile: REQUIRED, in (0, 100). P§10.1 fixes the threshold at a
            percentile of the reference error distribution but does not name it,
            and D-035 lists it among the things W4 Friday freezes deliberately.
            There is no default on purpose.
        seeds: confirmatory seeds only (D-034), enforced.
        score_fn: how one reference cell is scored. Defaults to the real training
            path. A test may substitute a synthetic scorer to exercise the
            balancing, refusal and percentile logic **without spending compute** --
            the calibration itself is never run that way.
    """
    if percentile is None:
        raise ValueError("percentile is required")
    if not 0.0 < float(percentile) < 100.0:
        raise ValueError(
            f"percentile must lie in (0, 100), got {percentile!r}. It is a "
            "percentile of the reference error distribution (P§10.1), not a "
            "fraction and not an error value"
        )
    seeds = _require_confirmatory(seeds)

    git = git_state()
    if git.dirty and not allow_dirty:
        raise ValueError(
            f"the working tree is dirty at commit {git.commit[:7]}. This threshold is "
            "frozen permanently and every failure set in the thesis descends from it, "
            "so it must name one reproducible code state. Commit or stash first."
        )

    units = units or reference_units()
    score = score_fn or score_reference_cell
    cells = [score(unit, seed=seed) for unit in units for seed in seeds]

    pooled, n = balance(cells, n_per_stratum=n_per_stratum, rng=rng)
    threshold = float(np.percentile(pooled, float(percentile)))
    strata = tuple(sorted({(c.layout, c.causal_attribute) for c in cells}))
    return ThresholdCalibration(
        threshold=threshold,
        percentile=float(percentile),
        n_per_stratum=n,
        strata=strata,
        seeds=seeds,
        n_total=int(pooled.shape[0]),
        commit=git.commit,
        cells=tuple(
            {"layout": c.layout, "causal_attribute": c.causal_attribute,
             "seed": c.seed, "n_transitions": len(c), "run_id": c.run_id,
             "config_id": c.config_id, "unit_id": c.unit_id}
            for c in cells
        ),
    )


def write_evidence(calibration: ThresholdCalibration, out_dir: str | Path) -> Path:
    """Write the calibration evidence once. Never overwrites, never edits constants."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "threshold_calibration.json"
    if path.exists():
        raise FileExistsError(
            f"{path} already exists. The threshold is calibrated once (P§10.1); a "
            "second calibration overwriting the first is how a 'fixed' number "
            "becomes a tuned one"
        )
    path.write_text(json.dumps(calibration.as_row(), indent=2), encoding="utf-8")
    return path
