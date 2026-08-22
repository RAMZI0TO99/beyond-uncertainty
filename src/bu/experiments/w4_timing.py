"""The Week 4 Friday timing harness (S§W4 Fri), rebuilt to Sol's requirements.

**Why it was rebuilt.** The first version (D-114) was refused certification, and
every objection was right: it timed one baseline ensemble at one seed rather
than a full condition; it **subtracted ablations**, which stay in the budget
until a reduction is actually decided; it omitted collection; it took **one**
observation per size and reported it to two decimals; it **persisted nothing**,
so its numbers were prose to be trusted rather than evidence to be audited; and
it called local CPU and RTX 4080 measurements "GPU-hours" when the plan names a
Kaggle T4 as the host.

This version:

* includes **every registered fit, ablations included** (8,197, not 8,047);
* includes **collection**, which is paid once per (unit, arm, seed) condition —
  2,947 of them — not once per fit;
* takes a **warm-up plus at least three repetitions** per size, keeps every raw
  observation, and reports **median and maximum**;
* runs **one representative registered condition end to end through its whole
  seed and repair obligation** and reconciles that against the bottom-up
  extrapolation, which is the check the microbenchmark cannot perform on itself;
* **persists an immutable record** with commit, tree state, host, versions,
  device and threads, every raw repetition, the accounting, and the derivation;
* **states the execution host honestly**. The plan names Kaggle T4. Everything
  this project has ever run has run locally, so the number below is **local
  wall-hours, not GPU-hours**, and DEV-011 records that the local four-thread
  CPU is the actual execution route.

**The verdict is taken on the conservative summary** — the maximum observed —
not on the median and not on a single run.

Still true, and still the reason this is not one scaled rate: per-fit cost varies
by more than an order of magnitude across the registered sizes, and data repair
trains at ``DATA_REPAIR_MULTIPLIER`` × its base, so 50,000 appears in the design
even though the largest *registered* size is 5,000.

Run:  .venv/bin/python -m bu.experiments.w4_timing --attempt runs/w4_timing/attempt-001
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import platform
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch

from .. import constants as K
from ..config import Arm, TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..models.ensemble import train_ensemble
from ..runrecord import package_versions
from .enumerate_units import (
    design_units, execution_plan, repair_obligations, total_model_fits,
)

#: Never a registered stage. A timing run must not be able to enter a claim.
TIMING_STAGE = "pilot"
#: Bumped if the record's fields or their meaning change.
TIMING_SCHEMA_VERSION = 1
#: Discarded runs before timing begins, so allocator and cache warm-up is not
#: charged to the first size measured.
WARMUP_RUNS = 1
#: Sol's floor. More is better; fewer is not a measurement.
MIN_REPETITIONS = 3
#: Ablations are a Plan §14.2 line item that is not sized until Week 14. They
#: are charged at the dominant registered size and the assumption is recorded
#: rather than hidden; the sensitivity is reported alongside.
ABLATION_ASSUMED_SIZE = 5_000


@dataclass
class SizeBenchmark:
    """Every raw observation at one training size. Nothing is averaged away."""

    n_transitions: int
    train_reps_s: list[float] = field(default_factory=list)
    collect_reps_s: list[float] = field(default_factory=list)
    members: int = K.DEFAULT_ENSEMBLE_SIZE

    def per_fit(self, how: str) -> float:
        f = statistics.median if how == "median" else max
        return f(self.train_reps_s) / self.members

    def per_collection(self, how: str) -> float:
        f = statistics.median if how == "median" else max
        return f(self.collect_reps_s)

    def as_record(self) -> dict:
        return {
            "n_transitions": self.n_transitions,
            "members": self.members,
            "train_reps_s": self.train_reps_s,
            "collect_reps_s": self.collect_reps_s,
            "train_median_s": statistics.median(self.train_reps_s),
            "train_max_s": max(self.train_reps_s),
            "per_fit_median_s": self.per_fit("median"),
            "per_fit_max_s": self.per_fit("max"),
            "per_collection_median_s": self.per_collection("median"),
            "per_collection_max_s": self.per_collection("max"),
        }


def _reference_unit(n_transitions: int) -> UnitSpec:
    return UnitSpec(
        family="estimation", layout="uniform", causal_attribute="shape",
        confound_rate=0.0, n_transitions=n_transitions, withheld_features=(),
    )


def _time_once(unit: UnitSpec, *, seed: int, device: str) -> tuple[float, float]:
    """(collect_s, train_s) for one condition. Reads the clock and nothing else."""
    torch.manual_seed(0)
    t0 = time.perf_counter()
    pools = collect_pools(unit, stage=TIMING_STAGE, seed=seed, arm="baseline")
    t1 = time.perf_counter()
    with torch.device(device):
        ensemble = train_ensemble(
            unit, pools, TrainConfig(), stage=TIMING_STAGE, seed=seed,
            arm="baseline", granularity="episode", logger=None,
        )
    if device == "cuda":
        torch.cuda.synchronize()
    t2 = time.perf_counter()
    del ensemble, pools
    return t1 - t0, t2 - t1


def benchmark_sizes(sizes, *, device: str, reps: int) -> dict[int, SizeBenchmark]:
    """Warm up once, then take `reps` observations at each size."""
    if reps < MIN_REPETITIONS:
        raise ValueError(f"{reps} repetitions; Sol's floor is {MIN_REPETITIONS}")
    for _ in range(WARMUP_RUNS):
        _time_once(_reference_unit(min(sizes)), seed=0, device=device)
    out: dict[int, SizeBenchmark] = {}
    for size in sizes:
        b = SizeBenchmark(n_transitions=size)
        for rep in range(reps):
            c, t = _time_once(_reference_unit(size), seed=rep, device=device)
            b.collect_reps_s.append(c)
            b.train_reps_s.append(t)
        out[size] = b
    return out


def design_accounting() -> dict:
    """Fits and collection events the registered design owes, by training size.

    Built on ``execution_plan`` (deduplicated by fit identity, stage-aware), not
    on ``obligations`` — the first version re-derived it and reproduced D-033's
    375 phantom fits. **Ablations are included**, charged at
    ``ABLATION_ASSUMED_SIZE`` with the assumption recorded.
    """
    plan = execution_plan(design_units())
    fits: collections.Counter = collections.Counter()
    collections_by_size: collections.Counter = collections.Counter()
    for fit in plan:
        size = Arm(fit.arm).resolve(fit.unit).n_transitions
        fits[size] += fit.members
        collections_by_size[size] += 1
    reference = total_model_fits(design_units())
    fits[ABLATION_ASSUMED_SIZE] += reference["ablations"]
    return {
        "fits_by_size": dict(sorted(fits.items())),
        "collections_by_size": dict(sorted(collections_by_size.items())),
        "total_fits": sum(fits.values()),
        "total_collections": sum(collections_by_size.values()),
        "ablations_included": True,
        "ablations": reference["ablations"],
        "ablation_assumed_size": ABLATION_ASSUMED_SIZE,
        "plan_total_model_fits": reference,
    }


def _rate(bench: dict[int, SizeBenchmark], size: int, how: str, kind: str) -> float:
    """Nearest measured size **at or above** ``size`` — conservative, never below.

    **Refuses rather than falling back.** The first version ended
    ``or [max(bench)]``, so a size larger than anything measured was charged at
    the *largest measured* rate — which is **optimistic, not conservative**, and
    flatly contradicted this docstring. It was unreachable in the real design,
    where every size the plan uses is measured, and that is exactly why it would
    have survived: an unreachable branch whose comment is wrong stays wrong until
    the day the design grows a larger size, and then under-charges silently.
    """
    at_or_above = [s for s in sorted(bench) if s >= size]
    if not at_or_above:
        raise ValueError(
            f"no benchmark at or above n={size:,}; the largest measured is "
            f"n={max(bench):,}. Charging it at a smaller size's rate would "
            "understate the budget, and this harness exists because a compute "
            "condition was already signed off on an optimistic proxy"
        )
    b = bench[at_or_above[0]]
    return b.per_fit(how) if kind == "fit" else b.per_collection(how)


def extrapolate(bench: dict[int, SizeBenchmark], acct: dict, how: str) -> dict:
    """Total wall seconds for the whole design, training AND collection."""
    train = sum(n * _rate(bench, s, how, "fit") for s, n in acct["fits_by_size"].items())
    coll = sum(n * _rate(bench, s, how, "collection")
               for s, n in acct["collections_by_size"].items())
    return {
        "summary": how,
        "training_s": train,
        "collection_s": coll,
        "total_s": train + coll,
        "total_hours": (train + coll) / 3600,
    }


def representative_condition() -> UnitSpec:
    """The largest repair-validation unit: 20 seeds, a baseline ensemble and a
    10x data-repair arm. It is the dominant registered size and the only shape
    that exercises seeds and repairs together."""
    ro = [o for o in repair_obligations(design_units()) if o.stage == "repair_validation"]
    return max((o.unit for o in ro), key=lambda u: u.n_transitions)


def run_full_condition(unit: UnitSpec, *, device: str, seeds: int | None = None) -> dict:
    """One registered condition END TO END through its whole seed/repair obligation.

    This is the check the per-size benchmark cannot perform on itself: it
    measures the real orchestration — every seed, every arm, collection included
    — so the bottom-up extrapolation can be reconciled against something that
    actually ran.
    """
    plan = [f for f in execution_plan(design_units()) if f.unit == unit]
    if seeds is not None:
        keep = sorted({f.seed for f in plan})[:seeds]
        plan = [f for f in plan if f.seed in keep]

    t0 = time.perf_counter()
    fits = 0
    for fit in plan:
        effective = Arm(fit.arm).resolve(fit.unit)
        pools = collect_pools(fit.unit, stage=TIMING_STAGE, seed=fit.seed, arm=fit.arm)
        with torch.device(device):
            cfg = TrainConfig(ensemble_size=fit.members)
            ens = train_ensemble(
                fit.unit, pools, cfg, stage=TIMING_STAGE, seed=fit.seed,
                arm=fit.arm, granularity="episode", logger=None,
            )
        if device == "cuda":
            torch.cuda.synchronize()
        fits += len(ens.members)
        del ens, pools
    elapsed = time.perf_counter() - t0
    return {
        "unit_n_transitions": unit.n_transitions,
        "arms": sorted({f.arm for f in plan}),
        "seeds_run": sorted({f.seed for f in plan}),
        "conditions": len(plan),
        "fits": fits,
        "measured_s": elapsed,
        "sizes_trained_at": sorted({Arm(f.arm).resolve(f.unit).n_transitions for f in plan}),
    }


def reconcile(observed: dict, bench: dict[int, SizeBenchmark], how: str,
              *, unit: UnitSpec) -> dict:
    """Predict the full-condition run bottom-up and compare with what it took.

    **Filters on the unit itself, not on its size.** The first version matched
    ``f.unit.n_transitions == 5000``, which is every unit at that size — 1,464
    plan entries and 4,552 fits against the 40 entries and 120 fits that
    actually ran, a **37.9x** inflation that showed up as a measured/predicted
    ratio of 0.03. The reconciliation caught it, which is what it is for; it
    simply caught a defect in itself rather than in the extrapolation.
    """
    plan = [f for f in execution_plan(design_units())
            if f.unit == unit
            and f.seed in set(observed["seeds_run"])
            and f.arm in set(observed["arms"])]
    predicted = 0.0
    for fit in plan:
        size = Arm(fit.arm).resolve(fit.unit).n_transitions
        predicted += fit.members * _rate(bench, size, how, "fit")
        predicted += _rate(bench, size, how, "collection")
    return {
        "summary": how,
        "predicted_s": predicted,
        "measured_s": observed["measured_s"],
        "ratio_measured_over_predicted": observed["measured_s"] / predicted if predicted else None,
    }


def load_record(path: str | Path) -> dict:
    """Read a persisted timing record with its integer size keys restored.

    **JSON has no integer keys.** `accounting.fits_by_size` and
    `collections_by_size` round-trip as *strings*, so feeding a stored record
    straight back into :func:`extrapolate` raises ``TypeError`` on ``s >= size``.
    The stored numbers are correct — re-derived through this loader they
    reproduce bit-identically — but Sol's requirement is that a Gate 1 result be
    **auditable without trusting copied prose**, and a record that cannot be fed
    back through the project's own function is not that. This is the loader.
    """
    target = Path(path)
    if target.is_dir():
        target = target / "timing.json"   # `recompute_threshold` takes an attempt
    if not target.exists():               # directory; accept either, like it does
        raise FileNotFoundError(f"no timing record at {target}")
    record = json.loads(target.read_text())
    acct = record["accounting"]
    for field_name in ("fits_by_size", "collections_by_size"):
        acct[field_name] = {int(k): v for k, v in acct[field_name].items()}
    return record


def benchmarks_from_record(record: dict) -> dict[int, SizeBenchmark]:
    """Rebuild the per-size benchmarks from a record's raw observations."""
    out: dict[int, SizeBenchmark] = {}
    for row in record["raw_by_size"]:
        b = SizeBenchmark(n_transitions=row["n_transitions"], members=row["members"])
        b.train_reps_s = list(row["train_reps_s"])
        b.collect_reps_s = list(row["collect_reps_s"])
        out[b.n_transitions] = b
    return out


def recompute_totals(path: str | Path) -> dict[str, float]:
    """Reproduce a stored record's headline totals from its own raw observations.

    The timing analogue of ``recompute_threshold``: it trusts the raw
    repetitions and recomputes everything derived from them.
    """
    record = load_record(path)
    bench = benchmarks_from_record(record)
    return {how: extrapolate(bench, record["accounting"], how)["total_hours"]
            for how in ("median", "max")}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def build_record(bench, acct, device, threads, full, recon,
                 *, source_commit: str, source_tree_clean_before_run: bool) -> dict:
    return {
        "schema_version": TIMING_SCHEMA_VERSION,
        # Captured BEFORE the run, not after. attempt-002 recorded a commit that
        # predated the harness it executed, with tree_clean false -- so the code
        # that produced it could not be recovered from its own record (Sol,
        # delta 54). Tracking the JSON afterwards does not repair provenance.
        "source_commit": source_commit,
        "source_tree_clean_before_run": source_tree_clean_before_run,
        "commit": source_commit,
        "tree_clean": source_tree_clean_before_run,
        "execution_host": {
            "described_by_plan_as": "Kaggle T4",
            "actual": "local workstation (DEV-011)",
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "device": device,
            "torch_threads": threads,
            "cuda_device": torch.cuda.get_device_name(0) if device == "cuda" else None,
            "units": "LOCAL WALL-HOURS, not GPU-hours",
        },
        "packages": package_versions(),
        "stage": TIMING_STAGE,
        "warmup_runs": WARMUP_RUNS,
        "repetitions": len(next(iter(bench.values())).train_reps_s),
        "raw_by_size": [b.as_record() for _, b in sorted(bench.items())],
        "accounting": acct,
        "extrapolation": {
            "median": extrapolate(bench, acct, "median"),
            "max": extrapolate(bench, acct, "max"),
        },
        "full_condition": full,
        "reconciliation": {"median": recon["median"], "max": recon["max"]},
        # Registered-plan metadata, NOT a threshold this record is tested against.
        "registered_trigger_gpu_hours": K.COMPUTE_ESCALATION_TRIGGER_GPU_HOURS,
        "comparison_status": "not adjudicable across hosts",
        "local_estimate_wall_hours": {
            "median": extrapolate(bench, acct, "median")["total_hours"],
            "max": extrapolate(bench, acct, "max")["total_hours"],
        },
        "verdict_basis": "max (conservative), LOCAL WALL-HOURS; no cross-unit verdict",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", default="runs/w4_timing/attempt-001")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--reps", type=int, default=MIN_REPETITIONS)
    ap.add_argument("--allow-dirty", action="store_true",
                    help="permit a dirty source tree; the record is then NOT "
                         "deliverable evidence")
    ap.add_argument("--condition-seeds", type=int, default=None,
                    help="limit the full-condition run to the first N seeds")
    args = ap.parse_args()

    torch.set_num_threads(args.threads)

    # Provenance is captured BEFORE anything runs, and a dirty source tree is
    # refused outright: a timing record whose commit does not identify the
    # harness that produced it is not evidence, whatever is tracked afterwards.
    source_commit = _git("rev-parse", "HEAD")
    source_clean = _git("status", "--porcelain") == ""
    if not source_clean and not args.allow_dirty:
        raise SystemExit(
            "REFUSING: the source tree is dirty, so this record could not "
            "identify the code that produced it. Commit first, then run. "
            "(--allow-dirty for throwaway experiments that will not be delivered.)"
        )

    acct = design_accounting()
    sizes = sorted(acct["fits_by_size"])

    print(f"W4 FRIDAY TIMING, rebuilt (S§W4 Fri; D-114 refused, D-116)")
    print(f"host: LOCAL, {args.device}, {args.threads} threads -- WALL-HOURS, not "
          f"GPU-hours (plan names Kaggle T4; see DEV-011)")
    print(f"design: {acct['total_fits']:,} fits INCLUDING {acct['ablations']} ablations, "
          f"{acct['total_collections']:,} collection events\n")

    bench = benchmark_sizes(sizes, device=args.device, reps=args.reps)
    print(f"{'size':>8}{'fits':>8}{'colls':>7}{'fit med':>10}{'fit max':>10}{'coll med':>10}")
    for s in sizes:
        b = bench[s]
        print(f"{s:>8,}{acct['fits_by_size'][s]:>8,}"
              f"{acct['collections_by_size'].get(s,0):>7,}"
              f"{b.per_fit('median'):>10.3f}{b.per_fit('max'):>10.3f}"
              f"{b.per_collection('median'):>10.3f}")

    unit = representative_condition()
    print(f"\nfull condition end to end: n={unit.n_transitions:,}, "
          f"{'all' if args.condition_seeds is None else args.condition_seeds} seeds ...")
    full = run_full_condition(unit, device=args.device, seeds=args.condition_seeds)
    recon = {h: reconcile(full, bench, h, unit=unit) for h in ("median", "max")}
    print(f"  {full['fits']} fits over {full['conditions']} conditions, arms {full['arms']}")
    print(f"  measured {full['measured_s']:.1f} s   predicted "
          f"{recon['median']['predicted_s']:.1f} s (median) / "
          f"{recon['max']['predicted_s']:.1f} s (max)")
    print(f"  measured/predicted = {recon['median']['ratio_measured_over_predicted']:.2f} "
          f"(median basis)")

    for how in ("median", "max"):
        e = extrapolate(bench, acct, how)
        print(f"\n  {how.upper():6} total {e['total_hours']:.2f} LOCAL WALL-HOURS "
              f"(train {e['training_s']/3600:.2f} h + collect {e['collection_s']/3600:.2f} h)")
    print(f"\n  registered trigger: {K.COMPUTE_ESCALATION_TRIGGER_GPU_HOURS} GPU-hours "
          f"(plan metadata, Kaggle T4)")
    print("  COMPARISON STATUS: NOT ADJUDICABLE ACROSS HOSTS. No ratio is printed and")
    print("  no verdict is drawn: local CPU wall-hours and Kaggle GPU-hours are")
    print("  different units, and the prose already concedes it (DEV-011). Turning")
    print("  that concession into a PASS would be the thing this harness exists to")
    print("  stop -- a compute condition adjudicated on a proxy for its own quantity.")

    record = build_record(bench, acct, args.device, args.threads, full, recon,
                          source_commit=source_commit,
                          source_tree_clean_before_run=source_clean)
    out = Path(args.attempt)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "timing.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; attempts are immutable")
    payload = json.dumps(record, indent=2, sort_keys=True, default=str)
    path.write_text(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    (out / "timing.json.sha256").write_text(digest + "\n")
    print(f"\nevidence written: {path}")
    print(f"  source_commit {source_commit}  clean_before_run {source_clean}")
    print(f"  sha256        {digest}")


if __name__ == "__main__":
    main()
