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
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import torch

from functools import lru_cache

from .. import constants as K
from ..config import Arm, Config, STAGE_SEEDS, TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..metrics import RunLogger
from ..models.ensemble import assert_pools_match, train_ensemble
from ..models.uncertainty import NormalisationScale, ScaledEvaluation, normalised_error
from ..models.world_model import MOVEMENT_ACTIONS
from ..runrecord import git_state
from ..streams import is_confirmatory
from .enumerate_units import execution_plan
from .repair import ArmEvaluation, REPAIR_ENSEMBLE_SIZE, REPAIR_STAGE
from ..stats.gate import METRIC_SCHEMA_VERSION
from .w4_gate import _pin_threading, torch_threading

#: The one bootstrap granularity a confirmatory fit may use (D-053).
CONFIRMATORY_GRANULARITY = "episode"

#: Stages that can never carry a confirmatory obligation.
FORBIDDEN_STAGES = ("pilot",)

#: The frozen primary training configuration. Sol required this be fixed rather
#: than accepted from a caller: a confirmatory number produced under an
#: unregistered optimisation is not the registered experiment, and `TrainConfig`
#: is deliberately not part of `run_id` (D-072), so two different configurations
#: would occupy the SAME recorded identity.
CONFIRMATORY_TRAIN = TrainConfig()

#: Repaired arms fit one model (P§14.2); baselines fit the registered ensemble.
REPAIRED_TRAIN = TrainConfig(ensemble_size=REPAIR_ENSEMBLE_SIZE)


@lru_cache(maxsize=1)
def _registered_obligations() -> frozenset:
    """Every (unit, arm, stage, seed-index) the design actually registers.

    Built from `execution_plan()`, which is the artefact the compute estimate is
    taken over -- so "registered" here means the same thing it means in the
    budget, rather than a second opinion about what the design contains.
    """
    out = set()
    for fit in execution_plan():
        unit_id = Config(unit=fit.unit).unit_id
        for role in fit.roles:
            out.add((unit_id, fit.arm, role, fit.seed))
    return frozenset(out)


def assert_registered_obligation(unit: UnitSpec, *, arm: str, stage: str, seed: int) -> None:
    """Refuse a (unit, arm, stage, seed) the design does not register.

    Sol's delta-44 finding: the runner accepted arbitrary unit/stage
    combinations. A confirmatory fit that discharges no registered obligation is
    compute spent outside the design that still writes a record indistinguishable
    from one inside it.
    """
    index = seed - K.CONFIRMATORY_SEED_BASE
    key = (Config(unit=unit).unit_id, arm, stage, index)
    if key not in _registered_obligations():
        raise ValueError(
            f"({Config(unit=unit).unit_id}, arm={arm!r}, stage={stage!r}, "
            f"seed={seed}) is not a registered obligation. The execution plan does "
            "not contain it, so this fit would discharge nothing while writing a "
            "record indistinguishable from one that does. Check the unit is in the "
            "design, the arm applies, and the seed index is within the stage's "
            "registered seed count"
        )


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
    #: The per-transition scoring from THIS fit. Sol's delta-44 requirement: the
    #: repair path consumes this rather than training a second time, so the
    #: number and the record provably describe the same model.
    evaluation: ArmEvaluation | None = None

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
    scale: NormalisationScale | None = None,
    threads: int = 4,
    interop_threads: int = 4,
    allow_dirty: bool = False,
) -> ConfirmatoryRun:
    """Fit one confirmatory ensemble, score it, and write a complete run record.

    **One fit, both products.** Sol's delta-44 ruling: a repair-validation number
    must come from a single fit that simultaneously carries complete evidence and
    produces the paired per-transition errors. Training once for the record and
    again for the scoring is two parallel paths, and nothing would guarantee the
    number and the record describe the same model. So this returns an
    :class:`~bu.experiments.repair.ArmEvaluation` alongside the record, and the
    repair path consumes it rather than re-training.

    There is no ``granularity`` argument and no ``train`` argument. Episode block
    bootstrap is the fixed primary method (D-053), and the training configuration
    is frozen (`CONFIRMATORY_TRAIN`) because `TrainConfig` is not part of
    ``run_id`` -- two different optimisations would occupy the same identity.

    Args:
        scale: the baseline's scale, to be reused by a repaired arm (D-061).
            Pass ``None`` only for the baseline, which is where it is created.
    """
    check_confirmatory(stage=stage, seed=seed, arm=arm, unit=unit)
    assert_registered_obligation(unit, arm=arm, stage=stage, seed=seed)

    if arm != "baseline" and scale is None:
        raise ValueError(
            f"arm {arm!r} was given no scale. The normalising scale is measured "
            "once on the baseline's full movement evaluation pool, before any "
            "mask, and reused for every arm sharing that pool (D-061)"
        )

    git = git_state()
    if git.dirty and not allow_dirty:
        raise ValueError(
            f"the working tree is dirty at commit {git.commit[:7]}. A confirmatory "
            "fit is evidence for a thesis claim and must name one reproducible "
            "code state. Refusing before the fit rather than after it."
        )

    _pin_threading(threads, interop_threads)
    train = CONFIRMATORY_TRAIN if arm == "baseline" else REPAIRED_TRAIN
    config = Config(unit=unit, arm=Arm(arm), seed=seed, stage=stage, train=train)
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
    if scale is not None:
        evaluation = replace(evaluation, scale=scale)

    # A REPAIRED arm fits one model (P§14.2), so it has no member spread and no
    # disagreement to report -- the quantity is undefined, not zero. Only surfaced
    # once the recorded path and the repair-scoring path were actually joined,
    # which is the integration defect Sol's "two parallel paths" objection
    # predicts: each path was individually consistent and their union was not.
    # The acceptance test needs per-transition ERROR, never disagreement (D-063
    # bars disagreement from repair labels anyway), so this is recorded as absent
    # rather than fabricated.
    has_members = config.train.ensemble_size > 1
    summary = evaluation.whole_pool() if has_members else None
    keep = move.numpy()
    per_transition = ArmEvaluation(
        arm=arm, seed=seed,
        error=normalised_error(members.mean(dim=0), targets, evaluation.scale)
        .detach().numpy(),
        episode=pools.evaluation.episode[keep], step=pools.evaluation.step[keep],
        scale=evaluation.scale, config_id=config.config_id, run_id=config.run_id,
        n_train=len(pools.train), ensemble_size=config.train.ensemble_size,
        stage=stage,
    )

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
        "mean_disagreement": (
            summary.as_row()["mean_disagreement"] if summary is not None else None
        ),
        "n_train": len(pools.train),
    }
    (record_dir / "confirmatory.json").write_text(
        json.dumps(run, indent=2), encoding="utf-8"
    )
    return ConfirmatoryRun(
        run_id=config.run_id, config_id=config.config_id, unit_id=config.unit_id,
        fit_id=config.fit_id, stage=stage, arm=arm, seed=seed,
        n_train=len(pools.train), member_count=config.train.ensemble_size,
        mean_disagreement=(
            float(run["mean_disagreement"]) if run["mean_disagreement"] is not None
            else float("nan")
        ),
        record_dir=record_dir, run=run, evaluation=per_transition,
    )


def run_repair_validation(
    unit: UnitSpec,
    *,
    seed: int,
    arm: str,
    out_dir: str | Path,
    allow_dirty: bool = False,
) -> tuple[ConfirmatoryRun, ConfirmatoryRun]:
    """One baseline and one repaired arm, both recorded, both scored from THEIR OWN fit.

    This is what closes C-008. Previously the complete-record path
    (`run_confirmatory`) and the per-transition repair-scoring path
    (`repair.evaluate_arm`) trained separately, so a repair-validation number and
    the evidence attesting it came from two different models with nothing
    guaranteeing they matched. Sol: *"Two parallel paths do not satisfy C-008."*

    Order matters and is not incidental. The baseline runs first because it is
    where the normalising scale is created, from its full movement evaluation
    pool before any mask exists; the repaired arm is then handed **that same
    scale object** rather than measuring its own, which is the D-061 rule that
    `ScaledEvaluation` exists to make structural.

    Returns both runs. The caller passes their `.evaluation` values to
    `acceptance_inputs`, which re-checks the pairing, the stage, the attested
    ensemble size and the failure masks before any label is built (D-095).
    """
    if arm == "baseline":
        raise ValueError(
            "run_repair_validation compares a repair against its baseline; pass the "
            "repaired arm and the baseline is run for you, in the order the scale "
            "rule requires"
        )
    baseline = run_confirmatory(
        unit, stage=REPAIR_STAGE, seed=seed, arm="baseline", out_dir=out_dir,
        allow_dirty=allow_dirty,
    )
    repaired = run_confirmatory(
        unit, stage=REPAIR_STAGE, seed=seed, arm=arm, out_dir=out_dir,
        scale=baseline.evaluation.scale, allow_dirty=allow_dirty,
    )
    if baseline.evaluation.scale is not repaired.evaluation.scale:
        raise AssertionError(
            "the two arms carry different scale objects; D-061 requires one scale, "
            "measured on the baseline's full movement pool, reused verbatim"
        )
    return baseline, repaired
