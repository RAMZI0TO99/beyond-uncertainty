"""C-008: the confirmatory runner — the only sanctioned path to a thesis number.

Sol raised this at the certification of `2875e60` and it has blocked confirmatory
execution and repair validation ever since. The runner must **own** five rules
rather than trust callers to observe them: episode bootstrap only, a registered
configuration and arm, matching pools and run identity, the confirmatory seed
policy, and complete run records.

**What "own" means here.** Every rule below is either structural or a refusal at
this entry point — none is a comment asking a caller to behave:

* **Episode bootstrap only.** There is deliberately **no granularity
  parameter**. A parameter that accepts one value is weaker than no parameter,
  because it invites a caller to pass something else and reads as a knob. The
  rule is additionally enforced at the resampling site itself
  (`bootstrap_episodes`), which every path must go through — that is the bypass
  `train_ensemble` used to confess in its own docstring, now closed (D-053,
  D-054).
* **Confirmatory seeds only.** D-034 makes every seed below
  `CONFIRMATORY_SEED_BASE` development data, permanently excluded. Refused here,
  not filtered later: a development fit that reaches an analysis has already
  spent the compute and already carries the identity.
* **Registered stage and arm.** `pilot` is refused outright — it has no seed
  policy and never enters a claim.
* **Matching pools.** `assert_pools_match` refuses pools generated for a
  different run (D-057), which is how a baseline pool once trained under a
  repair identity.
* **Complete records.** The run record carries the canonical `Config`, the
  derived identities, the granularity actually used, the evaluation-pool digest,
  the normalisation and the threading configuration, so the evidence contract
  can verify a claim rather than take one (D-072, contract v2).

**It does not decide anything.** It fits, scores and records. Verdicts are
`bu.stats`; labels are the repair path. A runner that also judged would be the
place where a rule could be quietly relaxed to make a number appear.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from ..config import Arm, Config, STAGE_SEEDS, TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..metrics import RunLogger
from ..models.ensemble import assert_pools_match, train_ensemble
from ..models.uncertainty import ScaledEvaluation
from ..models.world_model import MOVEMENT_ACTIONS
from ..streams import is_confirmatory
from ..stats.gate import METRIC_SCHEMA_VERSION
from .w4_gate import _pin_threading, torch_threading

#: The one bootstrap granularity a confirmatory fit may use (D-053).
CONFIRMATORY_GRANULARITY = "episode"

#: Stages that can never carry a confirmatory obligation.
FORBIDDEN_STAGES = ("pilot",)


@dataclass(frozen=True)
class ConfirmatoryRun:
    """One completed confirmatory fit, and the record that lets it be checked."""

    run_id: str
    config_id: str
    unit_id: str
    fit_id: str
    stage: str
    arm: str
    seed: int
    n_train: int
    member_count: int
    mean_disagreement: float
    record_dir: Path
    run: dict

    def as_row(self) -> dict:
        return dict(self.run)


def _digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _digest_pool(pools) -> str:
    """Identify the evaluation pool by its contents, not by its label."""
    h = hashlib.sha256()
    for arr in (pools.evaluation.obs, pools.evaluation.action,
                pools.evaluation.next_obs, pools.evaluation.episode):
        h.update(np.ascontiguousarray(arr).tobytes())
    return h.hexdigest()


def check_confirmatory(*, stage: str, seed: int, arm: str, unit: UnitSpec) -> None:
    """Every refusal this runner owns, in one place a test can call directly."""
    if stage not in STAGE_SEEDS:
        raise ValueError(f"unknown stage {stage!r}; expected one of {tuple(STAGE_SEEDS)}")
    if stage in FORBIDDEN_STAGES:
        raise ValueError(
            f"stage {stage!r} cannot carry a confirmatory obligation: it has no "
            "registered seed policy and never enters a claim (D-012, D-034)"
        )
    if not is_confirmatory(seed):
        raise ValueError(
            f"seed {seed} is development data. D-034 permanently excludes every "
            "seed below CONFIRMATORY_SEED_BASE from confirmatory results, "
            "threshold calibration, repair acceptance and the critic. Refused "
            "before the fit rather than filtered after it -- a development fit "
            "that reaches an analysis has already spent its compute and already "
            "carries its identity"
        )
    # Raises if this arm cannot apply to this unit (no feature to restore, no
    # capacity headroom). Checked before any pool is drawn.
    Arm(arm).resolve(unit)


def run_confirmatory(
    unit: UnitSpec,
    *,
    stage: str,
    seed: int,
    arm: str = "baseline",
    out_dir: str | Path,
    train: TrainConfig | None = None,
    threads: int = 4,
    interop_threads: int = 4,
) -> ConfirmatoryRun:
    """Fit one confirmatory ensemble and write a complete run record.

    There is no ``granularity`` argument. Episode block bootstrap is the fixed
    primary method for H1 and H2 (D-053) and this runner exists partly to make
    that unroutable-around rather than merely documented.
    """
    check_confirmatory(stage=stage, seed=seed, arm=arm, unit=unit)
    _pin_threading(threads, interop_threads)

    config = Config(unit=unit, arm=Arm(arm), seed=seed, stage=stage,
                    train=train or TrainConfig())
    pools = collect_pools(unit, stage=stage, seed=seed, arm=arm)
    assert_pools_match(pools, unit=unit, arm=arm, stage=stage, seed=seed)
    pool_digest = _digest_pool(pools)

    root = Path(out_dir)
    extra = {
        "granularity": CONFIRMATORY_GRANULARITY,
        "seed_partition": "confirmatory",
        "evaluation_pool_digest": pool_digest,
        "threading": torch_threading(),
    }
    with RunLogger.start(config, root=root, extra=extra) as logger:
        ensemble = train_ensemble(
            unit, pools, config.train, stage=stage, seed=seed, arm=arm,
            granularity=CONFIRMATORY_GRANULARITY, logger=logger,
        )

    obs = torch.as_tensor(pools.evaluation.obs)
    action = torch.as_tensor(pools.evaluation.action)
    next_obs = torch.as_tensor(pools.evaluation.next_obs)
    move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
    members = ensemble.member_predictions(obs[move], action[move])
    targets = ensemble.members[0].targets(next_obs[move])[0]

    # No mask, and none can be supplied: the scale is the full movement pool's,
    # measured before any failure set exists (D-061, C-010).
    evaluation = ScaledEvaluation.from_pool(
        members, targets, n_transitions=unit.n_transitions, seed=seed
    )
    summary = evaluation.whole_pool()

    record_dir = root / config.run_id
    run = {
        "config": config.to_dict(),
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        "fit_id": config.fit_id,
        "layout": unit.layout,
        "n_transitions": unit.n_transitions,
        "seed": seed,
        "arm": arm,
        "stage": stage,
        "seed_partition": "confirmatory",
        "granularity": CONFIRMATORY_GRANULARITY,
        "member_count": config.train.ensemble_size,
        "member_indices": list(range(config.train.ensemble_size)),
        "member_record_digest": _digest_file(record_dir / "metrics.jsonl"),
        "run_record_digest": _digest_file(record_dir / "run.json"),
        "evaluation_pool_id": f"{unit.layout}-s{seed:03d}",
        "evaluation_pool_digest": pool_digest,
        "normalisation": evaluation.scale.as_row(),
        # Read from the gate, not from the run record's own schema field:
        # a record attesting its own schema version proves nothing (D-073).
        "metric_schema_version": METRIC_SCHEMA_VERSION,
        "threading": torch_threading(),
        "mean_disagreement": summary.as_row()["mean_disagreement"],
        "n_train": len(pools.train),
    }
    (record_dir / "confirmatory.json").write_text(
        json.dumps(run, indent=2), encoding="utf-8"
    )
    return ConfirmatoryRun(
        run_id=config.run_id, config_id=config.config_id, unit_id=config.unit_id,
        fit_id=config.fit_id, stage=stage, arm=arm, seed=seed,
        n_train=len(pools.train), member_count=config.train.ensemble_size,
        mean_disagreement=float(run["mean_disagreement"]),
        record_dir=record_dir, run=run,
    )
