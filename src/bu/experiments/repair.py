"""The repair path (P§7.2, S§W5 Mon): train an arm, score it on a fixed failure set.

**This module evaluates repairs. It does not decide whether one worked** — that
is `bu.stats.acceptance` — and it does not decide which transitions failed. The
failure set arrives as an explicit mask, because the threshold defining it is
calibrated once at W4 Friday on a reference model and then **frozen permanently**
(§2, P§10.1). A repair path that could compute its own failure set could move it.

What makes the comparison paired
--------------------------------
Step 4 of P§7.2 evaluates every repair on the **same recorded failure set** as
the unrepaired condition, so the acceptance test is paired per transition within
seed rather than a comparison of summary numbers. Three things have to hold for
that to be true, and all three are verified rather than assumed:

* **the same transitions.** `collect_pools` keys the validation and evaluation
  streams on the *unresolved* unit, so a baseline and all of its repairs draw
  the same evaluation pool (D-055). Measured: episode, step and action arrays
  are identical across all four arms.
* **the same prediction targets.** Feature repair restores a withheld feature,
  so its observation encoding is **wider** — 22 columns against 22, and 30 after
  restoration. The *targets* are the dynamic components (D-032), and those are
  identical across arms. This is the arm D-055 records as having broken a pairing
  test before; the property that actually matters holds, and there is a test
  asserting it rather than a comment claiming it.
* **the same normalising scale.** Built from the baseline's full movement
  evaluation pool **before any mask** and reused for the repaired arm and for
  the masked subset (D-061, C-010). Because the targets are identical across
  arms, the arms' own scales coincide — but the code reuses one object rather
  than relying on that coincidence, which is what D-038 warns about: a property
  standing on an accident is not a property.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .. import constants as K
from ..config import ARMS, Arm, Config, TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..models.ensemble import assert_pools_match, train_ensemble
from ..models.uncertainty import NormalisationScale, ScaledEvaluation, normalised_error
from ..models.world_model import MOVEMENT_ACTIONS

#: The stage repair validation runs under, at the 20 seeds §2 freezes.
REPAIR_STAGE = "repair_validation"


def applicable_arms(unit: UnitSpec) -> tuple[str, ...]:
    """Which repairs this unit can actually receive.

    Not every repair applies to every condition: feature repair needs something
    withheld, capacity repair needs headroom. `Arm.resolve` already refuses the
    impossible ones; this reports them without raising, so a caller enumerating
    a design does not have to catch exceptions to find out.
    """
    out = []
    for kind in ARMS:
        if kind == "baseline":
            continue
        try:
            Arm(kind).resolve(unit)
        except ValueError:
            continue
        out.append(kind)
    return tuple(out)


@dataclass(frozen=True)
class ArmEvaluation:
    """One arm's per-transition error over the movement evaluation pool."""

    arm: str
    seed: int
    #: ``(n_movement,)`` normalised per-transition error.
    error: np.ndarray
    episode: np.ndarray
    step: np.ndarray
    scale: NormalisationScale
    config_id: str
    run_id: str
    n_train: int

    def __len__(self) -> int:
        return int(self.error.shape[0])


def evaluate_arm(
    unit: UnitSpec,
    *,
    arm: str,
    seed: int,
    train: TrainConfig | None = None,
    granularity: str = "episode",
    scale: NormalisationScale | None = None,
    stage: str = REPAIR_STAGE,
) -> ArmEvaluation:
    """Train one arm and score every movement transition in the evaluation pool.

    Args:
        scale: the baseline's scale, to be **reused**. Pass ``None`` only for the
            baseline arm itself, which is where the scale is created. A repaired
            arm scored in its own units is the D-061 defect (see `ScaledEvaluation`).
    """
    if arm != "baseline" and scale is None:
        raise ValueError(
            f"arm {arm!r} was given no scale. The normalising scale is measured once "
            "on the baseline's full movement evaluation pool, before any mask, and "
            "reused for every arm and subset sharing that pool (D-061). A repaired "
            "arm scored in its own units is exactly the defect that ruling closed"
        )

    effective = Arm(arm).resolve(unit)
    pools = collect_pools(unit, stage=stage, seed=seed, arm=arm)
    assert_pools_match(pools, unit=unit, arm=arm, stage=stage, seed=seed)

    config = Config(unit=unit, arm=Arm(arm), seed=seed, stage=stage, train=train or TrainConfig())
    ensemble = train_ensemble(
        unit, pools, config.train, stage=stage, seed=seed, arm=arm,
        granularity=granularity,
    )

    obs = torch.as_tensor(pools.evaluation.obs)
    action = torch.as_tensor(pools.evaluation.action)
    next_obs = torch.as_tensor(pools.evaluation.next_obs)
    move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))

    members = ensemble.member_predictions(obs[move], action[move])
    targets = ensemble.members[0].targets(next_obs[move])[0]

    if scale is None:
        # Created here, from the FULL movement pool, before any mask exists.
        scale = ScaledEvaluation.from_pool(
            members, targets, n_transitions=unit.n_transitions, seed=seed
        ).scale
    error = normalised_error(members.mean(dim=0), targets, scale)

    keep = move.numpy()
    return ArmEvaluation(
        arm=arm, seed=seed, error=error.detach().numpy(),
        episode=pools.evaluation.episode[keep], step=pools.evaluation.step[keep],
        scale=scale, config_id=config.config_id, run_id=config.run_id,
        n_train=len(pools.train),
    )


def acceptance_inputs(
    baseline: list[ArmEvaluation],
    repaired: list[ArmEvaluation],
    *,
    failure_mask: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Assemble the paired arrays `acceptance_test` consumes.

    Args:
        failure_mask: boolean over the movement evaluation pool — **the recorded
            failure set**, identical for both arms (P§7.2 step 4). ``None`` scores
            the whole pool, which is a diagnostic and **not** the registered
            acceptance comparison.
    """
    if len(baseline) != len(repaired):
        raise ValueError(
            f"{len(baseline)} baseline evaluations against {len(repaired)} repaired; "
            "the acceptance test is paired and needs the same seeds on both arms"
        )
    if not baseline:
        raise ValueError("no evaluations; there is nothing to compare")

    errors, arms, seeds, episodes = [], [], [], []
    for base, rep in zip(
        sorted(baseline, key=lambda e: e.seed), sorted(repaired, key=lambda e: e.seed)
    ):
        if base.seed != rep.seed:
            raise ValueError(
                f"seed {base.seed} on the baseline is paired with {rep.seed} on the "
                "repaired arm; the comparison is per seed"
            )
        if base.arm != "baseline":
            raise ValueError(f"the baseline list carries arm {base.arm!r}")
        if len(base) != len(rep):
            raise ValueError(
                f"seed {base.seed}: {len(base)} baseline transitions against "
                f"{len(rep)}. The arms were not scored on the same evaluation pool, "
                "so the comparison is not paired (D-055)"
            )
        if not np.array_equal(base.episode, rep.episode) or not np.array_equal(base.step, rep.step):
            raise ValueError(
                f"seed {base.seed}: the arms' transitions are not the same transitions. "
                "The evaluation pool is keyed on the unresolved unit precisely so that "
                "they are (D-055)"
            )
        if base.scale is not rep.scale:
            raise ValueError(
                f"seed {base.seed}: the arms carry different scale objects. D-061 "
                "requires one scale, measured on the baseline's full movement pool "
                "before any mask, reused verbatim"
            )
        mask = _validated_mask(failure_mask, len(base), base.seed)
        for source, flag in ((base, 0), (rep, 1)):
            errors.append(source.error[mask])
            arms.append(np.full(int(mask.sum()), flag))
            seeds.append(np.full(int(mask.sum()), source.seed))
            episodes.append(source.episode[mask])
    return {
        "errors": np.concatenate(errors),
        "repair": np.concatenate(arms),
        "seed": np.concatenate(seeds),
        "episode": np.concatenate(episodes),
    }


def _validated_mask(failure_mask, n, seed) -> np.ndarray:
    if failure_mask is None:
        return np.ones(n, dtype=bool)
    mask = np.asarray(failure_mask)
    if mask.dtype != np.bool_:
        raise ValueError(
            f"failure_mask must be boolean, got {mask.dtype}. An index array of the "
            "wrong length selects the wrong transitions without erroring"
        )
    if mask.shape != (n,):
        raise ValueError(
            f"failure_mask has shape {mask.shape}; seed {seed} has {n} movement "
            "transitions. A mask built against a different pool scores a different set "
            "than the one it names"
        )
    if not mask.any():
        raise ValueError(
            f"the failure set is empty at seed {seed}. A mean over nothing is nan, and "
            "a silently empty failure set is how nan reaches a registered endpoint"
        )
    return mask
