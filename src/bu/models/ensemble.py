"""The bootstrap ensemble (Schedule W3 Wed).

The ensemble is not a modelling convenience here -- it *is* the measurement
instrument. H1 and H2 are both claims about **mean pairwise disagreement**
between members, so anything that changes how members differ changes the
dependent variable directly. Every choice below is therefore a methodological
one wearing implementation clothes.

Two sources of member diversity, both from named streams
--------------------------------------------------------
* **Bootstrap resampling** of the training data (`bootstrap` stream);
* **independent initialisation** (`init` stream), plus independent minibatch
  order (`batch` stream).

Keeping them in separate streams matters: it means the ensemble's diversity can
later be attributed, and that changing the resampling scheme cannot silently
shift the weights members start from.

The validation set is shared and never resampled
------------------------------------------------
Bootstrapping touches the **training** split only. Every member is scored on the
same held-out episodes, because per-member validation errors that were computed
on different data would not be comparable to one another -- and Week 3 Friday
compares them.

Resampling granularity is a live question (Q-011)
-------------------------------------------------
Default is **episode-level** (a block bootstrap), for the same reason the split
is episode-level: transitions inside an episode are near-duplicates, so
resampling them individually produces members whose datasets differ far less
than their nominal sample counts suggest. But the choice is not free of
consequence for H1, and it is flagged rather than settled -- see Q-011 and the
measurement in the delta.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Literal

import numpy as np
import torch
import torch.nn as nn

from .. import constants as K
from ..config import Arm, TrainConfig, UnitSpec
from ..env.collect import Pools, TransitionDataset
from ..streams import STREAM_VERSION, is_confirmatory, stream
from .train import TrainResult, episode_indices, train
from .world_model import WorldModel

Granularity = Literal["episode", "transition", "none"]

#: How predictions are generated. **An explicit policy, not a default** (D-062).
#:
#: * ``"deterministic"`` — the estimator H1 and H2 are stated over: a plain
#:   ensemble, every member evaluated with dropout and batch-norm in inference
#:   behaviour.
#: * ``"mc_dropout"`` — P§9.3's reliability-gate fallback B2, *"dropout at test
#:   time"*. Dropout layers stay **active** during each no-gradient forward
#:   pass; everything else is still in inference behaviour.
PredictionMode = Literal["deterministic", "mc_dropout"]


def dropout_modules(model: nn.Module) -> list[nn.Module]:
    """Every dropout layer in ``model``, of any dimensionality."""
    return [m for m in model.modules() if isinstance(m, nn.modules.dropout._DropoutNd)]


@contextmanager
def prediction_mode(model: nn.Module, mode: PredictionMode) -> Iterator[None]:
    """Put ``model`` in the inference behaviour ``mode`` names, then restore it.

    **Why this is not just ``model.eval()``** (D-062). The W3 audit found
    ``member_predictions`` leaving members in eval mode and fixed the *state
    leak* by saving and restoring ``model.training``. Sol pointed out that this
    did not fix the mechanism it was written for: the forward pass still ran
    under ``eval()``, so under MC-dropout the dropout layers were **off** and the
    estimator would return deterministic predictions with exactly **zero
    disagreement**. That reads as "MC-dropout also fails H1" and triggers a false
    pivot at the very gate the fallback exists for. Restoring the mode afterwards
    is necessary and was never sufficient.

    So: ``eval()`` for everything, then dropout put **back** into training
    behaviour when the mode asks for it — which is what test-time dropout is, and
    which is not the same thing as calling ``model.train()`` (that would also
    switch batch-norm to batch statistics, an unrelated change to the estimator).

    Requesting ``"mc_dropout"`` from a model with **no dropout layers raises**.
    Silence there is the whole defect: an architecture without dropout returns
    identical samples, and a zero-disagreement result is indistinguishable from
    a real negative. The current :class:`WorldModel` has no dropout, so rung 3
    at the Week 4 gate must add one deliberately and will be told so.

    Modes are restored **per submodule**, not from the top-level flag: this
    function changes submodules independently, so ``model.train(was_training)``
    would not put a partially-mixed model back as it found it.
    """
    if mode not in ("deterministic", "mc_dropout"):
        raise ValueError(
            f"unknown prediction mode {mode!r}; expected 'deterministic' or "
            "'mc_dropout'"
        )

    saved = {module: module.training for module in model.modules()}
    try:
        model.eval()
        if mode == "mc_dropout":
            layers = dropout_modules(model)
            if not layers:
                raise ValueError(
                    "mode='mc_dropout' on a model with no dropout layers. Every "
                    "sample would be identical and disagreement would be exactly "
                    "zero, which is indistinguishable from the estimator failing "
                    "H1 (P§9.3 fallback B2, D-062). Add dropout to the "
                    "architecture before selecting this estimator."
                )
            for layer in layers:
                layer.train()
        yield
    finally:
        for module, was_training in saved.items():
            module.training = was_training


def forkable_devices(
    model: nn.Module, *tensors: torch.Tensor
) -> tuple[str | None, list[int]]:
    """The non-CPU device type and indices this computation actually touches.

    ``fork_rng`` always forks the **CPU** generator, and forks device generators
    only for the devices it is handed. ``fork_rng(devices=[])`` therefore
    isolates the CPU RNG and silently leaves a CUDA generator advancing — so the
    isolation claim held only on CPU, which is where it was tested (D-064).

    Returns ``(None, [])`` for a purely CPU computation, which keeps the
    CPU-only path exactly as it was. Raises if one call spans two accelerator
    types, because a single ``fork_rng`` cannot cover both and quietly forking
    one of them is the defect this function exists to remove.
    """
    devices = {p.device for p in model.parameters()}
    devices |= {b.device for b in model.buffers()}
    devices |= {t.device for t in tensors}

    accelerators = sorted(
        {(d.type, d.index or 0) for d in devices if d.type != "cpu"}
    )
    if not accelerators:
        return None, []
    types = {device_type for device_type, _ in accelerators}
    if len(types) > 1:
        raise ValueError(
            f"MC-dropout spans more than one accelerator type ({sorted(types)}); "
            "one fork_rng cannot isolate both generators"
        )
    device_type = types.pop()
    return device_type, sorted({index for _, index in accelerators})


def seed_locally(seed: int, device_type: str | None, devices: list[int]) -> None:
    """Seed **only** the generators a matching ``fork_rng`` will restore (D-065).

    ``torch.manual_seed`` is a convenience that seeds the CPU generator *and
    every accelerator device's* generator. Pairing it with a fork that
    snapshotted only the devices in use leaves the rest permanently reseeded:

    * a **CPU** MC-dropout call on a CUDA machine forks the CPU generator only,
      then reseeds every CUDA device — measured, `torch.cuda.get_rng_state()`
      was not preserved across a CPU-only call;
    * a call on **cuda:0** of a multi-GPU machine forks device 0 and reseeds
      devices 1, 2, … which are never restored.

    The single-GPU CUDA test missed both, because the one device it checked was
    both seeded *and* forked. So this seeds the CPU default generator directly
    rather than through the all-device helper, and then each derived device
    individually — every generator touched here is one the fork will put back.
    """
    torch.default_generator.manual_seed(seed)
    if device_type is None or device_type == "meta":
        return
    module = torch.get_device_module(device_type)
    for index in devices:
        with module.device(index):
            module.manual_seed(seed)


def mc_dropout_predictions(
    model: nn.Module,
    obs: torch.Tensor,
    action: torch.Tensor,
    *,
    n_samples: int,
    seed: int | None = None,
) -> torch.Tensor:
    """``(n_samples, batch, position_dims)`` stochastic forward passes (P§9.3).

    Rung 3 of the reliability-gate ladder replaces the *ensemble* with repeated
    stochastic passes through **one** model, so the returned tensor has the shape
    :func:`~bu.models.uncertainty.pairwise_disagreement` already consumes and the
    disagreement metric is unchanged. Nothing about H1's definition moves; only
    where the members come from.

    ``seed`` forks torch's RNG rather than advancing it, so sampling here cannot
    shift any other stream and a rung-3 verdict is reproducible. Two things have
    to line up for that to be true, and each was wrong once:

    * the **fork** covers the CPU generator and the generator of every
      accelerator device the model or its inputs live on. ``fork_rng`` forks CPU
      always but device generators only for those it is given, so the original
      ``devices=[]`` isolated CPU and left a CUDA generator advancing (D-064);
    * the **seeding** touches only those same generators. ``torch.manual_seed``
      seeds every device, so pairing it with a narrower fork reseeded devices
      nothing would restore — including on a purely CPU call (D-065).

    The gate's fallback estimator is exactly the thing that would be run on a
    GPU, which is why neither was acceptable as a CPU-only guarantee.
    """
    if n_samples < 2:
        raise ValueError(
            f"MC-dropout needs at least two samples to have any disagreement, "
            f"got {n_samples}"
        )
    device_type, devices = forkable_devices(model, obs, action)
    fork: dict[str, Any] = {"devices": devices}
    if device_type is not None:
        fork["device_type"] = device_type

    outputs = []
    with prediction_mode(model, "mc_dropout"):
        with torch.random.fork_rng(**fork):
            if seed is not None:
                # Device-local, so the set of generators seeded is exactly the
                # set this fork restores (D-065).
                seed_locally(seed, device_type, devices)
            with torch.no_grad():
                for _ in range(n_samples):
                    position, _ = model(obs, action)
                    outputs.append(position)
    return torch.stack(outputs)


def bootstrap_episodes(
    dataset: TransitionDataset,
    rng: np.random.Generator,
    *,
    seed: int,
    granularity: Granularity = "episode",
    ratio: float = 1.0,
) -> np.ndarray:
    """Transition indices for one member's resample of the **training** pool.

    **The confirmatory rule lives here, not only at `train_ensemble`.** It used
    to sit at that entry point alone, which left `bootstrap_episodes()` plus
    `train(train_index=...)` as a way around it -- and the docstring there said
    so honestly rather than claiming a closure it did not have. The guard has
    moved to where the resampling actually happens, so there is no path that
    resamples a confirmatory pool without passing it (C-008, D-053, D-056).

    `seed` is **required** for that reason: a caller cannot resample without
    declaring whose seed it is, which is what makes the rule unroutable-around
    rather than merely stated.

    Args:
        granularity: ``"episode"`` draws whole episodes with replacement -- a
            block bootstrap, and the **primary method** for H1 and H2 (D-053).
            ``"transition"`` draws rows, which treats correlated transitions as
            exchangeable and retains nearly every episode, suppressing the
            data-resampling component of disagreement. It is a labelled
            secondary sensitivity only and never determines a verdict.
        ratio: resample size as a fraction of the training pool.
    """
    if ratio <= 0:
        raise ValueError(f"bootstrap ratio must be positive, got {ratio}")
    if granularity != "episode" and is_confirmatory(seed):
        raise ValueError(
            f"granularity={granularity!r} on confirmatory seed {seed}. Episode "
            "block bootstrap is the fixed primary method for H1 and H2 (D-053). "
            "The other schemes are development diagnostics from the W3 Friday "
            "pilot, are not in the 8,197-fit plan (D-054), and are not part of "
            "Config or run identity -- so a non-primary confirmatory fit would "
            "occupy the same recorded identity as the primary one."
        )

    if granularity == "transition":
        n = max(1, int(round(len(dataset) * ratio)))
        return np.sort(rng.choice(len(dataset), size=n, replace=True))

    if granularity == "none":
        # Initialisation-only ensemble: every member sees the whole pool, so
        # all disagreement comes from weights. A cleaner sensitivity than a
        # transition bootstrap, because it isolates the source rather than
        # blurring it (Sol, Q-011).
        return np.arange(len(dataset))

    if granularity != "episode":
        raise ValueError(f"unknown bootstrap granularity {granularity!r}")

    by_episode = episode_indices(dataset)
    episodes = np.array(sorted(by_episode))
    n = max(1, int(round(len(episodes) * ratio)))
    drawn = rng.choice(episodes, size=n, replace=True)
    return np.concatenate([by_episode[int(e)] for e in drawn])


def assert_pools_match(
    pools: Pools, *, unit: UnitSpec, arm: str, stage: str, seed: int
) -> None:
    """The pools must have been generated for *this* run (D-057).

    ``arm`` reaches ``collect_pools`` and ``train_ensemble`` independently, so
    nothing stopped a caller pairing baseline pools with a repair arm. Measured
    before this guard existed: baseline pools plus ``arm="data_repair"`` trained
    on **250** transitions while the ensemble reported the data-repair identity
    with its effective 2,500 — a false repair label of exactly the kind D-056
    was meant to remove, arriving one layer up.

    Capacity repair accepted mismatched pools without complaint, because
    capacity does not change the observation width. Feature repair happened to
    die on a dimension mismatch — but an accidental runtime error in one arm is
    not an invariant, which is the whole reason this is a check rather than a
    convention.
    """
    expected_effective = Arm(arm).resolve(unit)
    for role in ("train", "validation", "evaluation"):
        dataset = getattr(pools, role)
        problems: list[str] = []
        if dataset.pool != role:
            problems.append(f"pool={dataset.pool!r}, expected {role!r}")
        if dataset.source_unit is None:
            # C-009. Ignoring a missing source_unit made the strongest check
            # here opt-out: a dataset that simply never recorded which unit it
            # came from passed the one clause that would have caught a pool
            # borrowed from another condition. Absent provenance is not
            # matching provenance.
            problems.append(
                "source_unit is not recorded, so it cannot be checked against the "
                "requested unit; a pool without provenance is not a pool known to "
                "belong to this run"
            )
        elif dataset.source_unit != unit:
            problems.append("source_unit differs from the requested unit")
        if dataset.stream_version != STREAM_VERSION:
            # C-009. The pools and the run must have been generated under one
            # stream registry: D-052 bumped STREAM_VERSION precisely because the
            # validation and evaluation streams changed, so a pool from the
            # previous version is a different experiment wearing this one's
            # identity.
            problems.append(
                f"stream_version={dataset.stream_version}, but this run is generating "
                f"under {STREAM_VERSION}"
            )
        if dataset.unit != expected_effective:
            problems.append(f"effective unit differs from Arm({arm!r}).resolve(unit)")
        if dataset.arm != arm:
            problems.append(f"arm={dataset.arm!r}, expected {arm!r}")
        if dataset.stage != stage:
            problems.append(f"stage={dataset.stage!r}, expected {stage!r}")
        if dataset.seed != seed:
            problems.append(f"seed={dataset.seed}, expected {seed}")
        if problems:
            raise ValueError(
                f"the {role} pool was not generated for this run: "
                + "; ".join(problems)
                + ". Pools and the ensemble must describe the same "
                "(unit, arm, stage, seed), or a run records one condition and "
                "trains on another (D-057)."
            )


@dataclass
class Ensemble:
    """K models fitted to the same condition, differing only by their streams."""

    #: The unresolved unit -- what keyed the streams.
    unit: UnitSpec
    #: What was actually built and trained.
    effective_unit: UnitSpec
    arm: str
    members: tuple[WorldModel, ...]
    results: tuple[TrainResult, ...]
    granularity: Granularity

    def __len__(self) -> int:
        return len(self.members)

    @property
    def val_position_errors(self) -> tuple[float, ...]:
        """Per-member held-out position loss, on the shared validation set."""
        return tuple(r.best_val_position for r in self.results)

    def member_predictions(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        *,
        mode: PredictionMode = "deterministic",
    ) -> torch.Tensor:
        """``(n_members, batch, position_dims)`` predicted next agent positions.

        Only the position head: H1 and H2 are claims about disagreement on the
        quantity the manipulated mechanism moves (D-032, DEV-007). Disagreement
        metrics themselves are Week 3 Friday; this is the tensor they read.

        ``mode`` selects the inference behaviour explicitly (D-062). The default
        is the registered estimator; ``"mc_dropout"`` draws one stochastic pass
        per member and **raises** on a dropout-free architecture rather than
        returning a silently deterministic answer. See :func:`prediction_mode`.
        """
        outputs = []
        for model in self.members:
            with prediction_mode(model, mode):
                with torch.no_grad():
                    position, _ = model(obs, action)
            outputs.append(position)
        return torch.stack(outputs)


def train_ensemble(
    unit: UnitSpec,
    pools: Pools,
    config: TrainConfig | None = None,
    *,
    stage: str,
    seed: int,
    arm: str = "baseline",
    granularity: Granularity = "episode",
    logger: Any | None = None,
) -> Ensemble:
    """Fit ``config.ensemble_size`` members and log each one's validation error.

    ``unit`` is the **unresolved** unit and ``arm`` the repair applied to it —
    the same split the pools use, and for the same reason (D-056):

    * the **effective** unit builds the model, so a capacity repair actually
      gets the larger network and a feature repair gets the wider input;
    * the **unresolved** unit keys every named stream, so a repair's members
      initialise, resample and batch exactly as its baseline's did.

    Passing one unit for both was silently wrong in opposite directions. With
    the unresolved unit a capacity repair trained the *original small model* —
    the repair was never applied, no error was raised, and every capacity
    condition would have been labelled "repair failed". With the effective unit
    the model was right but the streams moved.

    Only the **training** pool is resampled. Validation and evaluation are fixed
    and shared, so per-member errors are comparable and the evaluation set is
    identical across members, dataset sizes and conditions (D-052).
    """
    config = config or TrainConfig()
    effective = Arm(arm).resolve(unit)
    assert_pools_match(pools, unit=unit, arm=arm, stage=stage, seed=seed)
    if granularity != "episode" and is_confirmatory(seed):
        raise ValueError(
            f"granularity={granularity!r} on confirmatory seed {seed}. Episode "
            "block bootstrap is the fixed primary method (D-053); the other "
            "schemes are development diagnostics for the Week 3 Friday pilot "
            "and are not in the 8,197-fit plan (D-054). They are also not part "
            "of Config or run identity, so a non-primary confirmatory fit would "
            "occupy the same recorded identity as the primary one.\n\n"
            "Kept as the earlier, better-situated refusal. The rule itself now "
            "lives in bootstrap_episodes(), which every resampling path must go "
            "through, so this is defence in depth rather than the only guard "
            "(C-008)."
        )

    members: list[WorldModel] = []
    results: list[TrainResult] = []

    for k in range(config.ensemble_size):
        index = bootstrap_episodes(
            pools.train,
            stream(unit, stage, "bootstrap", seed, member=k),
            seed=seed,
            granularity=granularity,
            ratio=config.bootstrap_ratio,
        )
        model = WorldModel(effective, stream(unit, stage, "init", seed, member=k))
        result = train(
            model,
            pools.train,
            pools.validation,
            config,
            rng=stream(unit, stage, "batch", seed, member=k),
            train_index=index,
        )
        members.append(model)
        results.append(result)

        if logger is not None:
            # Per-member validation error is the schedule's acceptance
            # criterion, and it is logged per member rather than aggregated:
            # the spread across members is the quantity H1 and H2 are about,
            # and a mean would discard exactly it.
            n_unique = len(np.unique(pools.train.episode[index]))
            logger.log(
                member=k,
                val_position=result.best_val_position,
                best_epoch=result.best_epoch,
                epochs_run=result.epochs_run,
                stopped_early=result.stopped_early,
                n_train=len(index),
                n_unique_train_episodes=n_unique,
                granularity=granularity,
                arm=arm,
            )

    return Ensemble(
        unit=unit,
        effective_unit=effective,
        arm=arm,
        members=tuple(members),
        results=tuple(results),
        granularity=granularity,
    )


def default_ensemble_size() -> int:
    """Plan §14.2's default, swept at 3/5/10 in the Week 14 ablation."""
    return K.DEFAULT_ENSEMBLE_SIZE
