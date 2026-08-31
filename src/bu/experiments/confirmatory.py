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
from typing import NoReturn

from .. import constants as K
from ..config import Arm, Config, STAGE_SEEDS, TrainConfig, UnitSpec
from ..durable import atomic_write_json
from ..env.collect import collect_pools
from ..metrics import RunLogger
from ..models.ensemble import assert_pools_match, train_ensemble
from ..models.uncertainty import (
    NormalisationScale,
    ScaledEvaluation,
    normalised_error,
    per_transition_table,
)
from ..models.world_model import MOVEMENT_ACTIONS
from ..runrecord import git_state
from ..streams import (
    DATA_PURPOSES,
    assert_roles_share_one_stream,
    is_confirmatory,
    stream_key,
)
from .enumerate_units import design_units, execution_plan, stage_of
from .repair import (
    ArmEvaluation,
    REPAIR_ENSEMBLE_SIZE,
)
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

#: Threading, frozen inside the runner rather than accepted from a caller
#: (Sol, delta 45). It is result-changing (D-076) and absent from run identity,
#: so a caller-chosen value would file two different numbers under one id.
CONFIRMATORY_THREADS = 4
CONFIRMATORY_INTEROP_THREADS = 4

# The historical and certified execution route is CPU (DEV-011).  Leaving the
# device implicit would make a Kaggle worker silently run a different numerical
# procedure if a future caller changed the global default device.  This records
# and verifies the route without exposing a result-changing caller knob.
CONFIRMATORY_DEVICE = "cpu"


class _EpochLogger:
    """Bind an epoch-curve row to one ensemble member."""

    def __init__(self, logger: RunLogger, member: int) -> None:
        self._logger = logger
        self._member = member

    def log(self, **fields) -> None:
        self._logger.log(
            record_type="epoch", member=self._member, **fields
        )


@lru_cache(maxsize=1)
def _registered_obligations() -> frozenset:
    """Every (unit, arm, stage, seed-index) the design actually registers.

    Built from `execution_plan(design_units())` -- the registered 300-unit
    design, the artefact the compute estimate (D-033) and the certified timing
    harness (D-119) are taken over -- so "registered" here means the same thing
    it means in the budget. The argument is load-bearing: `execution_plan()`
    with no argument defaults to `full_matrix()`, the ~531-unit POOL the design
    draws on ("the pool, not the plan"), and a guard built from the pool
    accepted confirmatory fits on the 231 sweep units the design leaves out
    (D-133).
    """
    out = set()
    for fit in execution_plan(design_units()):
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


def _assert_repair_pairing(unit: UnitSpec, *, arm: str, stage: str) -> None:
    """Refuse unpaired repair execution without changing the registered inventory.

    D-155's safety guard is not a stream correction: sweep-only baselines use
    unit-keyed data while their repair stages currently select a family group.
    Compare the original, unresolved unit against its authoritative baseline
    stage; neither a repaired unit nor the repair's family supplies that stage.
    """
    if arm == "baseline":
        return
    baseline_stage = stage_of(unit)
    mismatched = [
        purpose
        for purpose in sorted(DATA_PURPOSES)
        if stream_key(unit, baseline_stage, purpose) != stream_key(unit, stage, purpose)
    ]
    if mismatched:
        raise ValueError(
            f"Wrong pairing for unit {Config(unit=unit).unit_id}, arm={arm!r}: "
            f"repair stage {stage!r} and authoritative baseline stage "
            f"{baseline_stage!r} have mismatched data stream keys for {mismatched}. "
            "Execution is refused before output, pool collection or training. "
            "An explicit versioned procedure decision is needed to correct this "
            "pairing (D-155); registration remains inventory, and this guard "
            "does not change stream meanings, stage identities or legacy recorded fits."
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
    #: Durable-fit writers persist this complete transition-level diagnostic
    #: inventory.  Repaired single-model arms carry error/episode/step and the
    #: scale; ensemble baselines additionally carry disagreement and predictive
    #: variance.  The arrays are not embedded in JSON.
    diagnostics: dict[str, np.ndarray] | None = None

    def as_row(self) -> dict:
        return dict(self.run)


def _digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _digest_pool(pools) -> str:
    """Identify the evaluation pool by its contents, not by its label."""
    h = hashlib.sha256()
    h.update(b"bu-evaluation-pool-digest-v2\0")
    arrays = (
        ("obs", pools.evaluation.obs),
        ("action", pools.evaluation.action),
        ("next_obs", pools.evaluation.next_obs),
        ("episode", pools.evaluation.episode),
    )
    for name, value in arrays:
        array = np.ascontiguousarray(value)
        header = json.dumps(
            {"name": name, "shape": list(array.shape), "dtype": array.dtype.str},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        data = array.tobytes()
        h.update(len(header).to_bytes(8, "big"))
        h.update(header)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
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
    _fit_roles: tuple[str, ...] | None = None,
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
    _assert_repair_pairing(unit, arm=arm, stage=stage)

    fit_roles = (stage,) if _fit_roles is None else _fit_roles
    if (
        type(fit_roles) is not tuple
        or not fit_roles
        or any(type(role) is not str for role in fit_roles)
        or fit_roles != tuple(sorted(set(fit_roles)))
        or stage not in fit_roles
    ):
        raise ValueError(
            f"_fit_roles must be a sorted unique nonempty tuple containing the "
            f"execution stage {stage!r}, got {fit_roles!r}"
        )
    for role in fit_roles:
        assert_registered_obligation(unit, arm=arm, stage=role, seed=seed)
    assert_roles_share_one_stream(unit, fit_roles)
    role_run_ids = {
        role: Config(
            unit=unit, arm=Arm(arm), seed=seed, stage=role,
            train=(CONFIRMATORY_TRAIN if arm == "baseline" else REPAIRED_TRAIN),
        ).run_id
        for role in fit_roles
    }

    if arm != "baseline" and scale is None:
        raise ValueError(
            f"arm {arm!r} was given no scale. The normalising scale is measured "
            "once on the baseline's full movement evaluation pool, before any "
            "mask, and reused for every arm sharing that pool (D-061)"
        )
    if arm == "baseline" and scale is not None:
        raise ValueError(
            "a baseline cannot accept a caller-supplied normalising scale. Its "
            "scale is measured once from its own full movement evaluation pool "
            "before any failure mask exists (D-061)"
        )

    git = git_state()
    if not git.trustworthy:
        raise ValueError(
            f"the working tree is not trustworthy at commit {git.commit!r} "
            f"(dirty={git.dirty}). A confirmatory fit is evidence for a thesis "
            "claim and must name one exact reproducible commit. There is "
            "deliberately no override (Sol, delta 45): an opt-out produces "
            "registered evidence under a configuration that is not represented "
            "in run identity, which is the same defect as an unrecorded thread "
            "count. A git-less tree reports UNCOMMITTED and is refused too."
        )

    _pin_threading(CONFIRMATORY_THREADS, CONFIRMATORY_INTEROP_THREADS)
    threading = torch_threading()
    if (threading["num_threads"] != CONFIRMATORY_THREADS
            or threading["num_interop_threads"] != CONFIRMATORY_INTEROP_THREADS):
        raise ValueError(
            f"threading is {threading}, not the frozen "
            f"{CONFIRMATORY_THREADS}/{CONFIRMATORY_INTEROP_THREADS}. Thread count "
            "changes the reduction order (D-076) and is not part of run identity, "
            "so a caller-chosen value would put two different numbers under one id."
        )
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
        "device": CONFIRMATORY_DEVICE,
        "fit_roles": list(fit_roles),
        "role_run_ids": role_run_ids,
    }
    with RunLogger.start(config, root=root, extra=extra) as logger:
        ensemble = train_ensemble(
            unit, pools, config.train, stage=stage, seed=seed, arm=arm,
            granularity=CONFIRMATORY_GRANULARITY,
            logger=logger,
            epoch_logger=lambda member: _EpochLogger(logger, member),
            device=CONFIRMATORY_DEVICE,
        )

    actual_devices = {
        parameter.device.type
        for member in ensemble.members
        for parameter in member.parameters()
    }
    if actual_devices != {CONFIRMATORY_DEVICE}:
        raise ValueError(
            f"confirmatory fit used devices {sorted(actual_devices)}, not the "
            f"frozen execution route {CONFIRMATORY_DEVICE!r}. Device changes "
            "floating-point execution and are not part of run identity"
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
    transition_error = normalised_error(
        members.mean(dim=0), targets, evaluation.scale
    ).detach().numpy()
    diagnostics: dict[str, np.ndarray] = {
        "episode": np.asarray(pools.evaluation.episode[keep]),
        "step": np.asarray(pools.evaluation.step[keep]),
        "error": transition_error,
        "scale": np.asarray(evaluation.scale.vector, dtype=np.float64),
        "scale_n_reference": np.asarray(evaluation.scale.n_reference),
        "scale_domain": np.asarray(evaluation.scale.domain),
        "scale_source": np.asarray(evaluation.scale.source),
    }
    if has_members:
        diagnostics = per_transition_table(
            members,
            targets,
            episode=pools.evaluation.episode[keep],
            step=pools.evaluation.step[keep],
            scale=evaluation.scale,
        )
    # The scored arrays above contain only movement transitions.  Persist the
    # complete action inventory as well, so the fit-evidence boundary can derive
    # that mask independently and refuse dropped, duplicated, reordered, or
    # otherwise post-selected movement rows.
    diagnostics["evaluation_action"] = np.asarray(pools.evaluation.action)
    per_transition = ArmEvaluation(
        arm=arm, seed=seed,
        error=transition_error,
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
        "device": CONFIRMATORY_DEVICE,
        "fit_roles": list(fit_roles),
        "role_run_ids": role_run_ids,
        "mean_disagreement": (
            summary.as_row()["mean_disagreement"] if summary is not None else None
        ),
        "mean_error": (
            summary.as_row()["mean_error"]
            if summary is not None
            else float(transition_error.mean())
        ),
        "mean_predictive_variance": (
            summary.as_row()["mean_predictive_variance"]
            if summary is not None else None
        ),
        "ratio": summary.as_row()["ratio"] if summary is not None else None,
        "n_train": len(pools.train),
    }
    atomic_write_json(record_dir / "confirmatory.json", run)
    return ConfirmatoryRun(
        run_id=config.run_id, config_id=config.config_id, unit_id=config.unit_id,
        fit_id=config.fit_id, stage=stage, arm=arm, seed=seed,
        n_train=len(pools.train), member_count=config.train.ensemble_size,
        mean_disagreement=(
            float(run["mean_disagreement"]) if run["mean_disagreement"] is not None
            else float("nan")
        ),
        record_dir=record_dir, run=run, evaluation=per_transition,
        diagnostics=diagnostics,
    )


def run_repair_validation(
    unit: UnitSpec,
    *,
    seed: int,
    arm: str,
    out_dir: str | Path,
) -> NoReturn:
    """Refuse the legacy pair runner that could refit one baseline per repair.

    The persisted repair-label orchestrator owns one baseline, both independent
    repairs, all twenty seeds, and their immutable source evidence.  Calling
    this historical pair helper once for each repair trained the same baseline
    twice and left neither call able to prove the complete label inventory.
    """

    del unit, seed, arm, out_dir
    raise ValueError(
        "run_repair_validation is disabled because pair-by-pair execution can "
        "duplicate a baseline fit and cannot attest the complete repair label. "
        "Use bu.experiments.repair_label_run.run_repair_label"
    )


def run_repair_condition(
    unit: UnitSpec,
    *,
    seed: int,
    out_dir: str | Path,
) -> NoReturn:
    """Refuse the obsolete one-seed, in-memory repair-condition path.

    A repair label is defined over the complete registered twenty-seed ladder
    and must remain independently reconstructable from immutable fit sidecars.
    This historical helper did neither: it returned three in-memory runs for one
    seed.  Keeping it executable would leave a bypass around the source-verified
    boundary in :func:`bu.experiments.repair_label_run.run_repair_label`.
    """

    del unit, seed, out_dir
    raise ValueError(
        "run_repair_condition is disabled because a one-seed in-memory result "
        "cannot be repair-label evidence. Use "
        "bu.experiments.repair_label_run.run_repair_label, which owns the exact "
        "20-seed x 3-arm plan and persists source-verifiable fit sidecars"
    )
