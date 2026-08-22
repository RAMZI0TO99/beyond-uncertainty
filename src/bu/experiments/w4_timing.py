"""The Week 4 Friday timing harness (S§W4 Fri) — measure, then extrapolate.

**Why this exists, late.** W4 Friday has *two* tasks. The threshold calibration
was done and certified; this one — *"measure one full condition end to end and
extrapolate total GPU-hours against the ~120-hour estimate"* — was never built,
and Gate 1's compute condition was nevertheless signed **PASS** on a *fit count*
(14,885 against ~8,700). A fit count is not GPU-hours, and the conversion is
exactly what this measures (D-113).

The schedule is blunt that this is not a formality: the budget is **110–145
GPU-hours against a ~120 trigger**, and *"the Week 4 timing harness is a gate,
not a formality — as specified, the design sits at the edge of the budget with
no meaningful headroom."*

**It reads wall time and nothing else.** No errors, no disagreement, no
predictions are inspected — the same discipline D-103 used when it timed one
cell before the threshold run. Everything runs at `stage="pilot"`, which carries
no seed policy and can never enter a claim, into a scratch directory. **No
registered evidence is written and no result is produced.**

**It does not extrapolate from one rate.** Per-fit cost varies strongly with the
training size, and data repair trains at ``DATA_REPAIR_MULTIPLIER`` × the base.
Scaling a single measured rate is the documented way to turn a right number into
a wrong one, so this measures a rate *per training size* and then weights those
rates by the design's actual obligation structure, resolving each repair arm to
the size it really trains at.

Run:  .venv/bin/python -m bu.experiments.w4_timing
"""

from __future__ import annotations

import argparse
import collections
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import torch

from .. import constants as K
from ..config import Arm, Config, TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..models.ensemble import train_ensemble
from .enumerate_units import design_units, execution_plan, total_model_fits

#: Never a registered stage. Timing runs must not be able to enter a claim.
TIMING_STAGE = "pilot"


@dataclass(frozen=True)
class Measurement:
    """Wall time for one full condition, broken into its phases."""

    n_transitions: int
    device: str
    collect_s: float
    train_s: float
    members: int

    @property
    def total_s(self) -> float:
        return self.collect_s + self.train_s

    @property
    def per_fit_s(self) -> float:
        """Training only, per member — the quantity the design multiplies."""
        return self.train_s / self.members

    @property
    def collect_per_condition_s(self) -> float:
        """Collection is paid once per condition, not once per member."""
        return self.collect_s


def time_condition(unit: UnitSpec, *, seed: int, device: str) -> Measurement:
    """One condition end to end: collect the pools, then fit the ensemble.

    Only ``time.perf_counter`` is read. The ensemble is discarded.
    """
    torch.manual_seed(0)
    train_cfg = TrainConfig()

    t0 = time.perf_counter()
    pools = collect_pools(unit, stage=TIMING_STAGE, seed=seed, arm="baseline")
    t1 = time.perf_counter()

    with torch.device(device):
        ensemble = train_ensemble(
            unit, pools, train_cfg, stage=TIMING_STAGE, seed=seed,
            arm="baseline", granularity="episode", logger=None,
        )
    if device == "cuda":
        torch.cuda.synchronize()
    t2 = time.perf_counter()

    members = len(ensemble.members)
    del ensemble
    return Measurement(
        n_transitions=unit.n_transitions, device=device,
        collect_s=t1 - t0, train_s=t2 - t1, members=members,
    )


def _reference_unit(n_transitions: int) -> UnitSpec:
    """A canonical, fully observed unit at the given training size."""
    return UnitSpec(
        family="estimation", layout="uniform", causal_attribute="shape",
        confound_rate=0.0, n_transitions=n_transitions, withheld_features=(),
    )


def design_fits_by_size() -> collections.Counter:
    """Every fit the registered design owes, keyed by the size it TRAINS at.

    **Built on ``execution_plan``, not on ``obligations``, and that is the whole
    point.** The first version of this function summed obligations directly and
    got 6,750 baseline fits against the design's 6,375 — **the exact 375 phantom
    fits of D-033**, because a repair-validation unit's baseline was counted at
    twenty-five seeds when the twenty contain the five. It also charged one fit
    per repair *obligation* instead of per seed, undercounting the repair side.
    Two errors in opposite directions, in a function whose only job is counting.

    ``execution_plan`` is already deduplicated by fit identity and stage-aware,
    and ``total_model_fits`` reproduces Plan §14.2's split from it. Re-deriving
    that arithmetic here would be a second implementation of a number the
    project has already been wrong about once.

    Repair arms are resolved through :class:`Arm`, so data repair is counted at
    its ``DATA_REPAIR_MULTIPLIER`` budget rather than at the base size.
    """
    fits: collections.Counter = collections.Counter()
    for fit in execution_plan(design_units()):
        effective = Arm(fit.arm).resolve(fit.unit)
        fits[effective.n_transitions] += fit.members
    return fits


def extrapolate(rates: dict[int, float], fits: collections.Counter) -> dict[int, float]:
    """Seconds per size, using the nearest measured size at or above each one.

    A size with no measurement is charged at the closest measured size that is
    at least as large, which is conservative rather than optimistic.
    """
    out: dict[int, float] = {}
    measured = sorted(rates)
    for size, count in fits.items():
        at_or_above = [m for m in measured if m >= size] or [measured[-1]]
        out[size] = count * rates[at_or_above[0]]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=None,
                        help="cpu, cuda, or omit to measure both where available")
    parser.add_argument("--threads", type=int, default=None,
                        help="torch intra-op threads. The certified W4 runs used "
                             "4 (D-076); the machine default is much higher, and "
                             "timing is NOT thread-neutral even though the "
                             "numerics question D-076 raised is separate.")
    args = parser.parse_args()
    if args.threads:
        torch.set_num_threads(args.threads)
        torch.set_num_interop_threads(args.threads) if hasattr(
            torch, "set_num_interop_threads") else None

    devices = [args.device] if args.device else (
        ["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"]
    )
    fits = design_fits_by_size()
    sizes = sorted(fits)
    total_fits = sum(fits.values())

    print("W4 FRIDAY TIMING HARNESS (S§W4 Fri, built late — D-113)")
    print("Wall time only. stage='pilot'. No registered evidence written.\n")
    print(f"registered design: {total_fits:,} fits across sizes {sizes}")
    print(f"budget: {K.COMPUTE_ESCALATION_TRIGGER_GPU_HOURS} GPU-hour escalation "
          f"trigger (P§14.3); schedule states 110-145 GPU-h\n")

    for device in devices:
        if device == "cuda" and not torch.cuda.is_available():
            print(f"-- {device}: unavailable, skipped\n")
            continue
        name = torch.cuda.get_device_name(0) if device == "cuda" else "CPU"
        print(f"-- {device} ({name}) "
              f"threads={torch.get_num_threads()} ------------------------")
        print(f"{'train size':>11}{'collect s':>11}{'train s':>10}"
              f"{'per-fit s':>11}{'design fits':>13}")
        rates: dict[int, float] = {}
        with tempfile.TemporaryDirectory():
            for size in sizes:
                m = time_condition(_reference_unit(size), seed=0, device=device)
                rates[size] = m.per_fit_s
                print(f"{size:>11,}{m.collect_s:>11.2f}{m.train_s:>10.2f}"
                      f"{m.per_fit_s:>11.3f}{fits[size]:>13,}")

        seconds = extrapolate(rates, fits)
        total_h = sum(seconds.values()) / 3600
        print(f"\n  EXTRAPOLATED TRAINING TIME: {total_h:.2f} hours "
              f"({sum(seconds.values()):,.0f} s over {total_fits:,} fits)")
        trigger = K.COMPUTE_ESCALATION_TRIGGER_GPU_HOURS
        print(f"  against the {trigger}-hour escalation trigger: "
              f"{total_h / trigger:.4f}x  ->  "
              f"{'WITHIN' if total_h < trigger else 'OVER'} budget")
        print(f"  headroom factor: {trigger / total_h:,.0f}x\n" if total_h else "\n")

    print("Training time only; collection is measured and reported per condition")
    print("but is not multiplied by member count. Measured on THIS machine, not")
    print("on Kaggle, which the schedule names as the execution host.")


if __name__ == "__main__":
    main()
