"""Architecture-aware *development* CPU pricing for the D-154 repair inventory.

This is additive to ``w4_timing``: its historical records, size-only rates and
width-512 refusal are untouched. A group is an EXACT effective architecture and
training-transition count, never a nearest-size or width-scaled proxy. Inventory
comes from ``execution_plan(design_units())`` (not the larger candidate pool).
Repairs are single models; data repair pays for its actual tenfold training pool.

Public surface:
* ``repair_inventory(scope)`` and ``benchmark_cases(scope)`` are source-only;
* ``run_benchmarks(attempt, group_ids=..., scope=...)`` runs one fresh, bounded
  process per case, with the frozen CPU **4 intra-op / 4 inter-op** route;
* ``build_timing_record`` permits explicitly incomplete measurement coverage;
* ``project_repairs`` refuses unless EVERY exact group in its scope is measured;
* ``load_timing_record`` verifies the file digest and rederives all accounting.
* Separately typed E1-baseline counterparts are ``baseline_inventory``,
  ``run_baseline_benchmarks``, ``project_baselines``, ``build_baseline_timing_record``
  and ``load_baseline_timing_record``. CLI ``--baseline`` selects ONLY the 90
  still-owed E1 baseline ensembles, at the six shape/uniform reference sizes.
  These baseline measurements NEVER enter a repair record or reuse old rates.

Default scope is E1 repairs plus ALL 638 extension fits: twelve representative
cases, not 638 benchmarks. One representative per group is chosen from E1 first,
then by unit id / arm, without reading outcomes. Each case gets one warm-up and
three measured single-model runs at development seeds 0 / (1, 2, 3). No epochs,
patience, model width or other training parameter is shortened or tuned.

IMPORTANT: maxima are empirical conservative summaries, NOT runtime bounds.
Architecture equality does not imply identical early stopping across layouts,
causes or confounds. Collection and training are timed; production prediction,
anchor/evidence serialization, epoch logging, launch/sync/recovery and concurrency
are NOT. No scientific result is emitted and no GPU-hour gate is adjudicated.
These are gross repair-only requirements, not remaining work, baseline costs or
the whole thesis budget (which still includes its 150 unpriced ablations).
The legacy D-155 production repair guard is not bypassed by a pilot benchmark.

Inspect without compute::

    python -m bu.experiments.repair_timing --list-cases

Explicitly run one printed group id from a clean pinned checkout::

    python -m bu.experiments.repair_timing --attempt .tmp/repair-timing/attempt-001 \
        --group GROUP_ID --timeout-seconds 1800

Combine immutable records (no compute)::

    python -m bu.experiments.repair_timing --combine A/timing.json B/timing.json \
        --output .tmp/repair-timing/combined.json

Only this module's new record schema accepts these measurements. Do not insert
them into historical ``w4_timing`` records. Interrupted attempts keep their start
record and completed case files; they never acquire a successful final record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import torch

from .. import constants as K
from ..config import Arm, Config
from ..durable import atomic_write_bytes, sha256_file
from ..env.collect import collect_pools
from ..env.encoder import ObservationEncoder
from ..env.gridworld import N_ACTIONS
from ..models.ensemble import train_ensemble
from ..models.world_model import ARCHITECTURE, dynamic_layout
from ..runrecord import PROJECT_ROOT, TRACKED_PACKAGES
from ..streams import STREAM_VERSION, is_confirmatory
from . import confirmatory as C
from . import preflight as P
from .enumerate_units import design_units, execution_plan, experiment_1_units
from .w4_timing import MIN_REPETITIONS, TIMING_STAGE, WARMUP_RUNS
from .w4_timing import _reference_unit

REPAIR_TIMING_SCHEMA_VERSION = 1
SCOPES = ("e1_and_extension", "e1_repairs", "extension", "all_repairs")
DEFAULT_SCOPE = "e1_and_extension"
WARMUP_SEED = 0
MEASUREMENT_SEEDS = tuple(range(1, MIN_REPETITIONS + 1))
DEFAULT_TIMEOUT_SECONDS = 1800
BASELINE_TIMING_SCHEMA_VERSION = 1
LIMITATIONS = (
    "LOCAL CPU WALL-HOURS, not GPU-hours; no cross-host gate verdict",
    "Gross repair-only inventory, not remaining work or whole-project costs",
    "Baselines and the unchanged 150 ablations are excluded, not zero-priced",
    "Exact architecture/size groups; one deterministic representative per group",
    "Early stopping and collection cost can vary within each group",
    "Maximum observed repetition is not a worst-case bound or confidence interval",
    "Timed: collect_pools plus train_ensemble, bootstrap and early stopping included",
    "Not timed: predictions, anchors, evidence/epoch logging, launch, copy, recovery",
    "No concurrent-job scaling, corrected pairing overhead, or confirmed launch readiness",
    "Host load and thermal effects are uncontrolled; CPU timings are local observations",
    "Development pilot only; no labels, failure masks, outcome selection or tuning",
)
BASELINE_LIMITATIONS = (
    LIMITATIONS[0],
    "Only the 90 higher-seed E1 baseline ensembles / 450 member models are priced",
    "Repairs, original 150 E1 baselines and ablations are excluded, not zero-priced",
    *LIMITATIONS[3:],
)


def _json(value: object) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           allow_nan=False, ensure_ascii=False) + "\n").encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"repair timing requires strict JSON: {exc}") from exc


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def _same(actual: object, expected: object, what: str) -> None:
    if _json(actual) != _json(expected):
        raise ValueError(f"{what} differs from the registered repair timing contract")


def _scope_fits(scope: str, plan: tuple, e1: set[str]) -> tuple:
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}, got {scope!r}")
    return tuple(f for f in plan if f.arm != "baseline" and (
        scope == "all_repairs"
        or (scope in {"e1_repairs", "e1_and_extension"}
            and Config(unit=f.unit).unit_id in e1)
        or (scope in {"extension", "e1_and_extension"}
            and f.arm == "capacity_extension_repair")
    ))


def _architecture(unit) -> dict:
    encoder = ObservationEncoder(unit.n_objects, unit.grid_size, unit.withheld_features)
    layout = dynamic_layout(encoder)
    return {
        **ARCHITECTURE,
        "hidden_size": unit.hidden_size,
        "observation_dim": encoder.size,
        "input_dim": encoder.size + N_ACTIONS,
        "action_dim": N_ACTIONS,
        "position_outputs": len(layout.position),
        "activation_outputs": len(layout.activation),
        "parameter_dtype": "torch.float32",
    }


def _key(fit) -> dict:
    effective = Arm(fit.arm).resolve(fit.unit)
    return {"architecture": _architecture(effective),
            "n_transitions": effective.n_transitions}


def _fit_record(fit) -> dict:
    train = C.CONFIRMATORY_TRAIN if fit.arm == "baseline" else C.REPAIRED_TRAIN
    config = Config(unit=fit.unit, arm=Arm(fit.arm), train=train,
                    stage=fit.roles[0], seed=fit.seed)
    return {"ordinal_fit_id": fit.fit_id, "seed_index": fit.seed,
            "roles": list(fit.roles), "members": fit.members,
            "config": config.to_dict()}


def _contract() -> dict:
    # No caller can turn a repair into an ensemble or override the runner knobs.
    if C.REPAIRED_TRAIN.ensemble_size != 1 or WARMUP_RUNS != 1:
        raise ValueError("repair timing requires one-model repairs and one warm-up")
    seeds = (WARMUP_SEED, *MEASUREMENT_SEEDS)
    if (len(MEASUREMENT_SEEDS) < MIN_REPETITIONS or len(set(seeds)) != len(seeds)
            or any(type(s) is not int or s < 0 or is_confirmatory(s) for s in seeds)):
        raise ValueError("timing seeds must be distinct development seeds below the boundary")
    if C.CONFIRMATORY_DEVICE != "cpu":
        raise ValueError("this timing schema prices only the frozen CPU route")
    return {
        "schema_version": REPAIR_TIMING_SCHEMA_VERSION,
        "stage": TIMING_STAGE, "seed_partition": "development",
        "device": C.CONFIRMATORY_DEVICE,
        "threading": {"num_threads": C.CONFIRMATORY_THREADS,
                      "num_interop_threads": C.CONFIRMATORY_INTEROP_THREADS},
        "train": asdict(C.REPAIRED_TRAIN),
        "granularity": C.CONFIRMATORY_GRANULARITY,
        "stream_version": STREAM_VERSION,
        "warmup_seed": WARMUP_SEED, "measurement_seeds": list(MEASUREMENT_SEEDS),
        "episode_length": K.EPISODE_LENGTH,
        "validation_episodes": K.VALIDATION_EPISODES,
        "evaluation_episodes": K.EVALUATION_EPISODES,
        "representative_rule": "E1 first, then lexicographic unit_id and arm; no outcomes",
    }


def repair_inventory(scope: str = "all_repairs") -> dict:
    """Derive exact config/seed counts; never read existing fits or outcomes.

    ``seed_indices`` are the enumeration's ordinal requirements, NOT new data
    seeds. The benchmark's actual development seeds are separately recorded.
    Baselines are included in the full execution-plan binding, not in pricing.
    """
    contract = _contract()
    plan = execution_plan(design_units())
    e1 = {Config(unit=u).unit_id for u in experiment_1_units()}
    selected = _scope_fits(scope, plan, e1)
    full_rows = sorted((_fit_record(f) for f in plan), key=lambda r: r["ordinal_fit_id"])
    if len({r["ordinal_fit_id"] for r in full_rows}) != len(full_rows):
        raise ValueError("execution plan contains duplicate physical fit requirements")
    all_repairs = [f for f in plan if f.arm != "baseline"]
    representatives = {}
    for fit in sorted(all_repairs, key=lambda f: (
            Config(unit=f.unit).unit_id not in e1, Config(unit=f.unit).unit_id, f.arm)):
        representatives.setdefault(_digest(_key(fit)), fit)
    grouped: dict[str, dict] = {}
    for fit in selected:
        if fit.members != 1:
            raise ValueError("repair inventory contains a non-single-model fit")
        key = _key(fit)
        gid = _digest(key)
        group = grouped.setdefault(gid, {
            "group_id": gid, **key, "model_fits": 0, "collection_events": 0,
            "configs": {},
        })
        group["model_fits"] += fit.members
        group["collection_events"] += 1
        config = Config(unit=fit.unit, arm=Arm(fit.arm), train=C.REPAIRED_TRAIN)
        entry = group["configs"].setdefault(config.config_id, {
            "unit_id": config.unit_id, "config_id": config.config_id,
            "unit": asdict(fit.unit), "effective_unit": asdict(config.effective_unit),
            "arm": fit.arm, "members": fit.members,
            "requirements": [],
        })
        entry["requirements"].append({"seed_index": fit.seed, "roles": list(fit.roles)})
    groups = []
    for gid, group in sorted(grouped.items()):
        group["configs"] = [group["configs"][cid] for cid in sorted(group["configs"])]
        for entry in group["configs"]:
            entry["requirements"].sort(key=lambda r: r["seed_index"])
        reference = representatives[gid]
        representative = Config(unit=reference.unit, arm=Arm(reference.arm),
                                train=C.REPAIRED_TRAIN, stage=TIMING_STAGE,
                                seed=WARMUP_SEED)
        group["benchmark_case"] = {"group_id": gid, **_key(reference),
                                   "config": representative.to_dict()}
        groups.append(group)
    record = {
        "scope": scope, "contract": contract,
        "registered_execution_plan_sha256": _digest(full_rows),
        "groups": groups,
        "model_fits": sum(g["model_fits"] for g in groups),
        "collection_events": sum(g["collection_events"] for g in groups),
        "configuration_count": sum(len(g["configs"]) for g in groups),
        "extension_model_fits": sum(f.members for f in selected
                                    if f.arm == "capacity_extension_repair"),
        "model_fits_by_arm": dict(sorted(Counter(f.arm for f in selected).items())),
        "all_registered_repair_models": sum(f.members for f in all_repairs),
        "baselines_included": False, "ablations_included": False,
        "ablation_allowance_not_priced": 150,
        "limitations": list(LIMITATIONS),
    }
    # JSON normalization makes in-memory and reloaded records identical, including
    # the tuples in UnitSpec. No default=str/repr provenance escape hatch.
    return json.loads(_json({**record, "inventory_sha256": _digest(record)}))


def benchmark_cases(scope: str = DEFAULT_SCOPE) -> tuple[dict, ...]:
    """Minimal exact-group coverage; deterministic and outcome-independent."""
    return tuple(g["benchmark_case"] for g in repair_inventory(scope)["groups"])


def baseline_inventory() -> dict:
    """The exact 90 still-owed E1 ensembles, not an arbitrary baseline subset.

    Reuses W4's shape/uniform/full-observation source reference, NOT its old
    Linux measurements. Each of the six reference units owes indices 5..19;
    original indices 0..4 are deliberately excluded and must never be retrained
    for timing. Benchmarks use development seeds, separately from those demands.
    """
    if (K.DEFAULT_ENSEMBLE_SIZE, K.SEEDS_HYPOTHESIS, K.CONFIRMATORY_SEED_BASE,
            C.CONFIRMATORY_TRAIN.ensemble_size) != (5, 5, 1000, 5):
        raise ValueError("baseline timing requires the exact registered 90-ensemble E1 policy")
    contract = {**_contract(), "schema_version": BASELINE_TIMING_SCHEMA_VERSION,
                "timing_kind": "e1_baseline_ensembles",
                "train": asdict(C.CONFIRMATORY_TRAIN),
                "representative_rule": "registered shape/uniform E1 reference per exact size"}
    plan = execution_plan(design_units())
    e1 = {Config(unit=u).unit_id for u in experiment_1_units()}
    selected = [f for f in plan if f.arm == "baseline" and f.seed >= K.SEEDS_HYPOTHESIS
                and Config(unit=f.unit).unit_id in e1]
    full_rows = sorted((_fit_record(f) for f in plan), key=lambda r: r["ordinal_fit_id"])
    if len({r["ordinal_fit_id"] for r in full_rows}) != len(full_rows):
        raise ValueError("execution plan contains duplicate physical fit requirements")
    sizes = tuple(sorted({f.unit.n_transitions for f in selected}))
    if len(selected) != 90 or sizes != (100, 250, 500, 1000, 2500, 5000):
        raise ValueError("baseline timing requires exactly 90 ensembles at six registered sizes")
    groups = []
    for size in sizes:
        reference = _reference_unit(size)
        config = Config(unit=reference, arm=Arm("baseline"), train=C.CONFIRMATORY_TRAIN,
                        stage=TIMING_STAGE, seed=WARMUP_SEED)
        fits = sorted((f for f in selected if f.unit.n_transitions == size), key=lambda f: f.seed)
        if (len(fits) != 15 or [f.seed for f in fits] != list(range(5, 20))
                or any(f.unit != reference or f.members != 5
                       or f.roles != ("repair_validation",) for f in fits)):
            raise ValueError("baseline timing demands differ from the shape/uniform 15-seed ladder")
        key = {"architecture": _architecture(reference), "n_transitions": size,
               "members": 5, "arm": "baseline"}
        gid = _digest(key)
        groups.append({"group_id": gid, **key, "ensemble_jobs": 15,
                       "model_fits": 75, "collection_events": 15,
                       "requirements": [_fit_record(f) for f in fits],
                       "benchmark_case": {"group_id": gid, **key, "config": config.to_dict()}})
    record = {"scope": "e1_baselines", "contract": contract,
              "registered_execution_plan_sha256": _digest(full_rows), "groups": groups,
              "ensemble_jobs": 90, "model_fits": 450, "collection_events": 90,
              "configuration_count": 6, "original_e1_baselines_included": False,
              "repairs_included": False, "ablations_included": False,
              "limitations": list(BASELINE_LIMITATIONS)}
    return json.loads(_json({**record, "inventory_sha256": _digest(record)}))


def _validate_baseline_trial(row: object, seed: int) -> None:
    if type(row) is not dict or set(row) != {"seed", "collection_s", "training_s", "epochs_run"}:
        raise ValueError("baseline timing repetition has missing or unknown fields")
    epochs = row["epochs_run"]
    if (type(epochs) is not list or len(epochs) != 5
            or any(type(e) is not int or not 1 <= e <= C.CONFIRMATORY_TRAIN.max_epochs for e in epochs)):
        raise ValueError("baseline timing needs five valid member epoch counts")
    # Seed/time validation is shared; the single-model epoch field is not.
    _validate_trial({**row, "epochs_run": epochs[0]}, seed)


def _validate_baseline_benchmarks(benchmarks: Sequence[dict], inventory: dict) -> dict[str, dict]:
    if type(inventory) is not dict or not isinstance(benchmarks, (list, tuple)):
        raise ValueError("baseline inventory and benchmarks must be explicit records")
    _same(inventory, baseline_inventory(), "baseline inventory")
    cases = {g["group_id"]: g["benchmark_case"] for g in inventory["groups"]}
    fields = {"schema_version", "artifact_type", "group_id", "case", "contract",
              "registered_execution_plan_sha256", "environment_before",
              "environment_after", "warmup", "repetitions"}
    out, shared_environment = {}, None
    for row in benchmarks:
        if type(row) is not dict or set(row) != fields:
            raise ValueError("baseline benchmark has missing or unknown fields; repair records cannot enter")
        gid = row["group_id"]
        if type(gid) is not str or gid not in cases or gid in out:
            raise ValueError("baseline benchmark has an unknown or duplicate exact group")
        _same(row["schema_version"], BASELINE_TIMING_SCHEMA_VERSION, "baseline timing schema")
        _same(row["artifact_type"], "development_e1_baseline_case", "baseline case type")
        _same(row["case"], cases[gid], "baseline representative architecture/size")
        _same(row["contract"], inventory["contract"], "baseline training/seed contract")
        _same(row["registered_execution_plan_sha256"],
              inventory["registered_execution_plan_sha256"], "baseline execution plan binding")
        _validate_environment(row["environment_before"])
        _validate_environment(row["environment_after"])
        _same(row["environment_after"], row["environment_before"], "baseline before/after provenance")
        if shared_environment is not None:
            _same(row["environment_before"], shared_environment, "combined baseline host/commit/runtime")
        shared_environment = row["environment_before"]
        _validate_baseline_trial(row["warmup"], WARMUP_SEED)
        if type(row["repetitions"]) is not list or len(row["repetitions"]) != len(MEASUREMENT_SEEDS):
            raise ValueError("baseline benchmark lacks the exact three measured repetitions")
        for trial, seed in zip(row["repetitions"], MEASUREMENT_SEEDS):
            _validate_baseline_trial(trial, seed)
        out[gid] = row
    return out


def _baseline_projection(inventory: dict, measured: dict[str, dict], how: str) -> dict:
    if how not in ("median", "max"):
        raise ValueError("summary must be 'median' or 'max'")
    summary = statistics.median if how == "median" else max
    contributions = []
    for group in inventory["groups"]:
        gid = group["group_id"]
        if gid not in measured:
            raise ValueError(f"missing exact baseline ensemble measurement at n={group['n_transitions']}")
        reps = measured[gid]["repetitions"]
        # Measured training_s is a FIVE-member ensemble duration: never multiply
        # it by the 75 member models (fivefold inflation) or collect five times.
        train = group["ensemble_jobs"] * summary(r["training_s"] for r in reps)
        collect = group["collection_events"] * summary(r["collection_s"] for r in reps)
        contributions.append({"group_id": gid, "ensemble_jobs": group["ensemble_jobs"],
                              "model_fits": group["model_fits"],
                              "collection_events": group["collection_events"],
                              "training_s": train, "collection_s": collect})
    train = sum(c["training_s"] for c in contributions)
    collect = sum(c["collection_s"] for c in contributions)
    if not math.isfinite(train + collect):
        raise ValueError("baseline projected duration overflowed")
    return {"scope": "e1_baselines", "summary": how, "ensemble_jobs": 90,
            "model_fits": 450, "collection_events": 90, "training_s": train,
            "collection_s": collect, "total_s": train + collect,
            "local_wall_hours": (train + collect) / 3600, "contributions": contributions,
            "limitations": list(BASELINE_LIMITATIONS)}


def project_baselines(inventory: dict, benchmarks: Sequence[dict], how: str = "max") -> dict:
    """Price exactly 90 ensembles only with complete six-case coverage."""
    return _baseline_projection(inventory, _validate_baseline_benchmarks(benchmarks, inventory), how)


def build_baseline_timing_record(benchmarks: Sequence[dict]) -> dict:
    inventory = baseline_inventory()
    measured = _validate_baseline_benchmarks(benchmarks, inventory)
    if not measured:
        raise ValueError("no baseline benchmarks: enumeration is not timing evidence")
    missing = sorted({g["group_id"] for g in inventory["groups"]} - set(measured))
    return {"schema_version": BASELINE_TIMING_SCHEMA_VERSION,
            "artifact_type": "development_e1_baseline_cpu_timing", "inventory": inventory,
            "benchmarks": [measured[gid] for gid in sorted(measured)],
            "missing_group_ids": missing, "complete_scope_coverage": not missing,
            "extrapolation": None if missing else {
                how: _baseline_projection(inventory, measured, how) for how in ("median", "max")},
            "limitations": list(BASELINE_LIMITATIONS)}


def write_baseline_timing_record(path: str | Path, record: dict) -> Path:
    _same(record, build_baseline_timing_record(record.get("benchmarks", [])), "baseline timing record")
    target = _inside_project(path)
    atomic_write_bytes(target, _json(record))
    atomic_write_bytes(target.with_name(target.name + ".sha256"),
                       (sha256_file(target) + "\n").encode("ascii"))
    return target


def load_baseline_timing_record(path: str | Path) -> dict:
    """Strict separate reader; old W4 and repair-only schemas cannot pass."""
    target = _inside_project(path)
    if target.is_dir():
        target = _inside_project(target / "timing.json")
    sidecar = _inside_project(target.with_name(target.name + ".sha256"))
    if sidecar.read_text(encoding="ascii") != sha256_file(target) + "\n":
        raise ValueError("baseline timing digest sidecar does not match artifact bytes")
    record = json.loads(target.read_bytes())
    _same(record, build_baseline_timing_record(record.get("benchmarks", [])), "stored baseline timing record")
    return record


def _environment(*, pin: bool = False) -> dict:
    state, versions, pins = P._verify_environment()
    if pin:
        C._pin_threading(C.CONFIRMATORY_THREADS, C.CONFIRMATORY_INTEROP_THREADS)
    threading = C.torch_threading()
    _same(threading, _contract()["threading"], "actual CPU threading")
    if torch.get_default_dtype() != torch.float32:
        raise ValueError("CPU repair timing requires default torch.float32")
    if torch.device(torch.get_default_device()).type != "cpu":
        raise ValueError("CPU repair timing requires the default CPU device")
    return {
        "source_commit": state.commit, "source_tree_clean": True,
        "packages": versions, "pins": pins,
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(), "machine": platform.machine(),
        "hostname": platform.node(), "logical_cpu_count": os.cpu_count(),
        "device": "cpu", "threading": threading, "dtype": "torch.float32",
    }


def _validate_environment(env: object) -> None:
    fields = {"source_commit", "source_tree_clean", "packages", "pins", "platform",
              "processor", "python", "machine", "hostname", "logical_cpu_count",
              "device", "threading", "dtype"}
    if type(env) is not dict or set(env) != fields:
        raise ValueError("timing environment has missing or unknown provenance fields")
    commit = env["source_commit"]
    if (type(commit) is not str or len(commit) != 40
            or any(c not in "0123456789abcdef" for c in commit)):
        raise ValueError("timing source_commit must be a full lowercase Git commit")
    if env["source_tree_clean"] is not True:
        raise ValueError("timing source tree was not clean")
    for field in ("platform", "processor", "python", "machine", "hostname"):
        if type(env[field]) is not str or not env[field]:
            raise ValueError(f"timing environment lacks {field}")
    if type(env["logical_cpu_count"]) is not int or env["logical_cpu_count"] < 1:
        raise ValueError("timing environment lacks a valid logical_cpu_count")
    pins = P._pinned_package_versions()
    if set(pins) != set(TRACKED_PACKAGES):
        raise ValueError("pin registry does not cover exactly the tracked packages")
    _same(env["pins"], pins, "runtime pins")
    _same(env["packages"], pins, "observed packages")
    _same(env["threading"], _contract()["threading"], "recorded CPU threading")
    if env["device"] != "cpu" or env["dtype"] != "torch.float32":
        raise ValueError("timing must identify the frozen CPU / float32 route")


def _validate_trial(row: object, seed: int) -> None:
    if type(row) is not dict or set(row) != {"seed", "collection_s", "training_s", "epochs_run"}:
        raise ValueError("raw timing repetition has missing or unknown fields")
    if type(row["seed"]) is not int or row["seed"] != seed or is_confirmatory(row["seed"]):
        raise ValueError("timing repetition does not use its fixed development seed")
    for name in ("collection_s", "training_s"):
        value = row[name]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite positive raw duration")
    epochs = row["epochs_run"]
    if type(epochs) is not int or not 1 <= epochs <= C.REPAIRED_TRAIN.max_epochs:
        raise ValueError("epochs_run must be a valid frozen-training stopping count")


def _validate_benchmarks(benchmarks: Sequence[dict], inventory: dict) -> dict[str, dict]:
    # Re-derive, including all config/role/seed counts. A re-signed altered count
    # or architecture is still not registered accounting.
    if type(inventory) is not dict:
        raise ValueError("repair inventory must be a record")
    if not isinstance(benchmarks, (list, tuple)):
        raise ValueError("benchmarks must be an explicit sequence of records")
    _same(inventory, repair_inventory(inventory.get("scope")), "repair inventory")
    cases = {g["group_id"]: g["benchmark_case"] for g in repair_inventory()["groups"]}
    out = {}
    shared_environment = None
    fields = {"schema_version", "group_id", "case", "contract",
              "registered_execution_plan_sha256", "environment_before",
              "environment_after", "warmup", "repetitions"}
    for record in benchmarks:
        if type(record) is not dict or set(record) != fields:
            raise ValueError("benchmark has missing or unknown fields")
        gid = record["group_id"]
        if type(gid) is not str or gid not in cases or gid in out:
            raise ValueError("benchmark has an unknown or duplicate architecture/size group")
        _same(record["schema_version"], REPAIR_TIMING_SCHEMA_VERSION, "timing schema")
        _same(record["case"], cases[gid], "benchmark architecture/size representative")
        _same(record["contract"], inventory["contract"], "benchmark training/seed contract")
        _same(record["registered_execution_plan_sha256"],
              inventory["registered_execution_plan_sha256"], "execution plan binding")
        _validate_environment(record["environment_before"])
        _validate_environment(record["environment_after"])
        _same(record["environment_after"], record["environment_before"],
              "before/after source and runtime provenance")
        if shared_environment is not None:
            _same(record["environment_before"], shared_environment,
                  "combined benchmark host/commit/runtime")
        shared_environment = record["environment_before"]
        _validate_trial(record["warmup"], WARMUP_SEED)
        reps = record["repetitions"]
        if type(reps) is not list or len(reps) != len(MEASUREMENT_SEEDS):
            raise ValueError("benchmark lacks exactly the registered measured repetitions")
        for trial, seed in zip(reps, MEASUREMENT_SEEDS):
            _validate_trial(trial, seed)
        out[gid] = record
    return out


def _projection(inventory: dict, measured: dict[str, dict], how: str) -> dict:
    if how not in ("median", "max"):
        raise ValueError("summary must be 'median' or 'max'")
    summary = statistics.median if how == "median" else max
    contributions = []
    for group in inventory["groups"]:
        gid = group["group_id"]
        if gid not in measured:
            raise ValueError(
                "missing exact architecture/size measurement: "
                f"width={group['architecture']['hidden_size']}, "
                f"input={group['architecture']['input_dim']}, "
                f"n={group['n_transitions']}, group={gid}; no scaled or nearest-size rates"
            )
        reps = measured[gid]["repetitions"]
        train = group["model_fits"] * summary(r["training_s"] for r in reps)
        collect = group["collection_events"] * summary(r["collection_s"] for r in reps)
        contributions.append({"group_id": gid, "model_fits": group["model_fits"],
                              "collection_events": group["collection_events"],
                              "training_s": train, "collection_s": collect})
    train = sum(c["training_s"] for c in contributions)
    collect = sum(c["collection_s"] for c in contributions)
    if not math.isfinite(train + collect):
        raise ValueError("projected duration overflowed; finite raw measurements are required")
    return {"scope": inventory["scope"], "summary": how, "training_s": train,
            "collection_s": collect, "total_s": train + collect,
            "local_wall_hours": (train + collect) / 3600,
            "model_fits": inventory["model_fits"], "contributions": contributions,
            "limitations": list(LIMITATIONS)}


def project_repairs(inventory: dict, benchmarks: Sequence[dict], how: str = "max") -> dict:
    """Price only a completely measured exact scope; refuses partial coverage."""
    return _projection(inventory, _validate_benchmarks(benchmarks, inventory), how)


def build_timing_record(benchmarks: Sequence[dict], scope: str = DEFAULT_SCOPE) -> dict:
    """Bind raw timings to all counts, explicitly distinguishing incomplete cover."""
    inventory = repair_inventory(scope)
    measured = _validate_benchmarks(benchmarks, inventory)
    if not measured:
        raise ValueError("no benchmarks: an inventory alone is not timing evidence")
    needed = {g["group_id"] for g in inventory["groups"]}
    missing = sorted(needed - set(measured))
    return {
        "schema_version": REPAIR_TIMING_SCHEMA_VERSION,
        "artifact_type": "development_repair_cpu_timing",
        "inventory": inventory,
        "benchmarks": [measured[gid] for gid in sorted(measured)],
        "missing_group_ids": missing, "complete_scope_coverage": not missing,
        "extrapolation": (None if missing else {
            how: _projection(inventory, measured, how) for how in ("median", "max")
        }),
        "limitations": list(LIMITATIONS),
    }


def _inside_project(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    root = PROJECT_ROOT.resolve(strict=True)
    # Refuse reparse aliases, not merely aliases escaping the resolved root.
    for part in (candidate, *candidate.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError(f"timing path must not use symlinks/junctions: {part}")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError("timing files and scratch must stay inside the project folder")
    return resolved


def write_timing_record(path: str | Path, record: dict) -> Path:
    """Immutable payload + digest; altered derived fields fail before any write."""
    _same(record, build_timing_record(record.get("benchmarks", []),
                                    record.get("inventory", {}).get("scope")),
          "timing record")
    target = _inside_project(path)
    atomic_write_bytes(target, _json(record))
    atomic_write_bytes(target.with_name(target.name + ".sha256"),
                       (sha256_file(target) + "\n").encode("ascii"))
    return target


def load_timing_record(path: str | Path) -> dict:
    """Verify bytes AND regenerate counts/projections; a re-signed lie fails."""
    target = _inside_project(path)
    if target.is_dir():
        target = _inside_project(target / "timing.json")
    sidecar = _inside_project(target.with_name(target.name + ".sha256"))
    if sidecar.read_text(encoding="ascii") != sha256_file(target) + "\n":
        raise ValueError("timing digest sidecar does not match artifact bytes")
    record = json.loads(target.read_bytes())
    _same(record, build_timing_record(record.get("benchmarks", []),
                                    record.get("inventory", {}).get("scope")),
          "stored timing record")
    return record


def _time_once(case: dict, seed: int) -> dict:
    return _measure_case(case, seed, baseline=False)


def _time_baseline_once(case: dict, seed: int) -> dict:
    return _measure_case(case, seed, baseline=True)


def _measure_case(case: dict, seed: int, *, baseline: bool) -> dict:
    if type(seed) is not int or seed not in (WARMUP_SEED, *MEASUREMENT_SEEDS):
        raise ValueError("only the fixed development timing seeds may run")
    config = Config.from_dict(case["config"])
    if (config.arm.kind == "baseline") is not baseline:
        raise ValueError("benchmark arm is on the wrong baseline/repair timing road")
    train = C.CONFIRMATORY_TRAIN if baseline else C.REPAIRED_TRAIN
    _same(asdict(config.train), asdict(train), "benchmark fixed training config")
    _same(C.torch_threading(), _contract()["threading"], "actual CPU threading")
    start = time.perf_counter()
    pools = collect_pools(config.unit, stage=TIMING_STAGE, seed=seed,
                          arm=config.arm.kind)
    collected = time.perf_counter()
    ensemble = train_ensemble(
        config.unit, pools, train, stage=TIMING_STAGE, seed=seed,
        arm=config.arm.kind, granularity=C.CONFIRMATORY_GRANULARITY,
        logger=None, device=C.CONFIRMATORY_DEVICE,
    )
    trained = time.perf_counter()
    members = 5 if baseline else 1
    if len(ensemble.members) != members or len(ensemble.results) != members:
        raise ValueError(f"benchmark did not train exactly {members} member models")
    result = {"seed": seed, "collection_s": collected - start,
              "training_s": trained - collected,
              "epochs_run": ([r.epochs_run for r in ensemble.results] if baseline
                             else ensemble.results[0].epochs_run)}
    (_validate_baseline_trial if baseline else _validate_trial)(result, seed)
    return result


def _benchmark_group(group_id: str, *, receipt_dir: str | Path) -> dict:
    """Worker-only fixed case; no caller-supplied architecture/train/seed knobs."""
    return _benchmark_with_receipts(group_id, receipt_dir=receipt_dir, baseline=False)


def _benchmark_baseline_group(group_id: str, *, receipt_dir: str | Path) -> dict:
    return _benchmark_with_receipts(group_id, receipt_dir=receipt_dir, baseline=True)


def _benchmark_with_receipts(group_id: str, *, receipt_dir: str | Path, baseline: bool) -> dict:
    inventory = baseline_inventory() if baseline else repair_inventory()
    cases = {g["group_id"]: g["benchmark_case"] for g in inventory["groups"]}
    if group_id not in cases:
        raise ValueError("unknown registered benchmark group")
    receipts = _inside_project(receipt_dir)
    if receipts.exists():
        raise FileExistsError(f"immutable benchmark receipts already exist: {receipts}")
    case = cases[group_id]
    before = _environment(pin=True)
    _validate_environment(before)
    receipts.mkdir(parents=True, exist_ok=False)
    start = {"case": case, "contract": inventory["contract"],
             "registered_execution_plan_sha256": inventory["registered_execution_plan_sha256"],
             "environment_before": before, "status": "started, not completed"}
    atomic_write_bytes(receipts / "start.json", _json(start))

    def measure(seed: int, phase: str) -> dict:
        trial = (_time_baseline_once if baseline else _time_once)(case, seed)
        (_validate_baseline_trial if baseline else _validate_trial)(trial, seed)
        # Persist OUTSIDE the timed interval. On interruption, prior samples
        # survive, but they are not a complete benchmark or a production fit.
        atomic_write_bytes(receipts / f"{phase}-s{seed:03d}.json", _json({
            "case_sha256": _digest(case), "phase": phase, "trial": trial,
        }))
        return trial

    warmup = measure(WARMUP_SEED, "warmup")
    repetitions = [measure(seed, "measured") for seed in MEASUREMENT_SEEDS]
    after = _environment()
    record = {
        "schema_version": (BASELINE_TIMING_SCHEMA_VERSION if baseline else REPAIR_TIMING_SCHEMA_VERSION),
        "group_id": group_id,
        "case": case, "contract": inventory["contract"],
        "registered_execution_plan_sha256": inventory["registered_execution_plan_sha256"],
        "environment_before": before, "environment_after": after,
        "warmup": warmup, "repetitions": repetitions,
    }
    if baseline:
        record["artifact_type"] = "development_e1_baseline_case"
    (_validate_baseline_benchmarks if baseline else _validate_benchmarks)([record], inventory)
    return record


def _worker_command(group_id: str, output: Path, env: dict[str, str], *, baseline: bool = False) -> list[str]:
    """Launch the REAL Python process, not a Windows venv redirector child.

    Mirrors stdlib multiprocessing.popen_spawn_win32 (bpo-35797). Killing only
    the venv redirector on timeout can leave the real interpreter running. The
    launcher environment marker preserves the venv's sys.executable/site path.
    The worker trains in-process and deliberately creates no further processes.
    """
    executable = sys.executable
    base = getattr(sys, "_base_executable", executable)
    if sys.platform == "win32" and os.path.normcase(executable) != os.path.normcase(base):
        env["__PYVENV_LAUNCHER__"] = executable
        executable = base
    return [executable, "-m", "bu.experiments.repair_timing",
            "--worker-baseline-group" if baseline else "--worker-group",
            group_id, "--output", str(output)]


def run_benchmarks(attempt: str | Path, *, group_ids: Sequence[str],
                   scope: str = DEFAULT_SCOPE,
                   timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> Path:
    """Explicit opt-in compute; fresh CPU process per case, timeout includes warm-up.

    Destination must be new and ignored by Git, so persisting the attempt cannot
    dirty the source being measured. Failed/timeout attempts are never reused or
    overwritten. Output/cache/temp files are confined to that project directory.
    """
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 86400:
        raise ValueError("timeout_seconds must be an integer in [1, 86400]")
    inventory = repair_inventory(scope)
    return _run_timing_workers(attempt, group_ids=group_ids, inventory=inventory,
                               timeout_seconds=timeout_seconds, baseline=False)


def run_baseline_benchmarks(attempt: str | Path, *, group_ids: Sequence[str],
                            timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> Path:
    """Six-case baseline route, opt-in only; no caller training or seed knobs."""
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 86400:
        raise ValueError("timeout_seconds must be an integer in [1, 86400]")
    return _run_timing_workers(attempt, group_ids=group_ids, inventory=baseline_inventory(),
                               timeout_seconds=timeout_seconds, baseline=True)


def _run_timing_workers(attempt: str | Path, *, group_ids: Sequence[str], inventory: dict,
                        timeout_seconds: int, baseline: bool) -> Path:
    available = {g["group_id"] for g in inventory["groups"]}
    if (not group_ids or any(type(g) is not str or g not in available for g in group_ids)
            or len(group_ids) != len(set(group_ids))):
        raise ValueError("request nonempty, distinct exact group ids from the selected scope")
    root = _inside_project(attempt)
    if root.exists():
        raise FileExistsError(f"immutable timing attempt already exists: {root}")
    relative = (root / "timing.json").relative_to(PROJECT_ROOT.resolve())
    ignored = subprocess.run(["git", "check-ignore", "--quiet", "--", relative.as_posix()],
                             cwd=PROJECT_ROOT, capture_output=True, check=False)
    if ignored.returncode != 0:
        raise ValueError("benchmark destination must be Git-ignored (use .tmp/repair-timing)")
    before = _environment(pin=True)
    root.mkdir(parents=True, exist_ok=False)
    start = {"schema_version": REPAIR_TIMING_SCHEMA_VERSION, "inventory": inventory,
             "environment": before, "group_ids": sorted(group_ids),
             "per_group_timeout_seconds": timeout_seconds,
             "max_worker_wall_seconds": timeout_seconds * len(group_ids),
             "status": "started, not evidence of completion"}
    atomic_write_bytes(root / "start.json", _json(start))
    scratch = root / "scratch"
    scratch.mkdir()
    env = dict(os.environ)
    env.update(TEMP=str(scratch), TMP=str(scratch), TMPDIR=str(scratch),
               MPLCONFIGDIR=str(scratch), PYTHONDONTWRITEBYTECODE="1")
    records = []
    for gid in sorted(group_ids):
        output = root / (gid + ".json")
        command = _worker_command(gid, output, env, baseline=baseline)
        # Regular files rather than PIPE keep potentially long logs bounded in
        # parent memory and preserve child failures. The direct interpreter is
        # subprocess.run's timeout kill target; no detached helpers/children.
        with (root / (gid + ".stdout.log")).open("xb") as stdout, \
                (root / (gid + ".stderr.log")).open("xb") as stderr:
            completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env,
                                       stdout=stdout, stderr=stderr, check=False,
                                       timeout=timeout_seconds)
        if completed.returncode != 0:
            raise ValueError(f"timing worker failed for {gid}; attempt and logs preserved")
        record = (load_baseline_timing_record if baseline else load_timing_record)(output)
        if len(record["benchmarks"]) != 1 or record["benchmarks"][0]["group_id"] != gid:
            raise ValueError("timing worker returned the wrong requested group")
        measured = record["benchmarks"][0]
        _same(measured["environment_before"], before, "worker vs launch provenance")
        records.append(measured)
    _same(_environment(), before, "launch before/after provenance")
    if baseline:
        return write_baseline_timing_record(root / "timing.json", build_baseline_timing_record(records))
    return write_timing_record(root / "timing.json", build_timing_record(records, inventory["scope"]))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=SCOPES, default=DEFAULT_SCOPE)
    parser.add_argument("--baseline", action="store_true",
                        help="separate six-case adapter for the 90 higher-seed E1 baseline ensembles")
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--attempt")
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--all-cases", action="store_true",
                        help="explicitly benchmark every exact group in --scope")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--combine", nargs="+")
    parser.add_argument("--output")
    parser.add_argument("--worker-group", help=argparse.SUPPRESS)
    parser.add_argument("--worker-baseline-group", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    modes = (args.list_cases, args.attempt is not None, args.combine is not None,
             args.worker_group is not None, args.worker_baseline_group is not None)
    if sum(modes) != 1:
        parser.error("choose exactly one of --list-cases, --attempt, or --combine")
    baseline = args.baseline or args.worker_baseline_group is not None
    if baseline and (args.scope != DEFAULT_SCOPE or args.worker_group is not None):
        parser.error("baseline timing cannot use a repair scope or repair worker")
    if args.list_cases:
        inventory = baseline_inventory() if baseline else repair_inventory(args.scope)
        for group in inventory["groups"]:
            print(f"{group['group_id']}  width={group['architecture']['hidden_size']} "
                  f"input={group['architecture']['input_dim']} n={group['n_transitions']} "
                  f"models={group['model_fits']}")
    elif args.worker_group or args.worker_baseline_group:
        if not args.output:
            parser.error("worker requires --output")
        # Reject a path escape before any benchmark work starts.
        output = _inside_project(args.output)
        if output.exists():
            raise FileExistsError(f"immutable worker result already exists: {output}")
        benchmark = (_benchmark_baseline_group if baseline else _benchmark_group)(
            args.worker_baseline_group if baseline else args.worker_group,
            receipt_dir=output.with_name(output.stem + "-receipts"))
        if baseline:
            write_baseline_timing_record(output, build_baseline_timing_record([benchmark]))
        else:
            write_timing_record(output, build_timing_record([benchmark], "all_repairs"))
    elif args.combine:
        if not args.output:
            parser.error("--combine requires --output")
        loader = load_baseline_timing_record if baseline else load_timing_record
        records = [b for path in args.combine for b in loader(path)["benchmarks"]]
        if baseline:
            print(write_baseline_timing_record(args.output, build_baseline_timing_record(records)))
        else:
            print(write_timing_record(args.output, build_timing_record(records, args.scope)))
    else:
        if args.group and args.all_cases:
            parser.error("choose --group or --all-cases, not both")
        cases = ([g["benchmark_case"] for g in baseline_inventory()["groups"]]
                 if baseline else benchmark_cases(args.scope))
        gids = ([c["group_id"] for c in cases]
                if args.all_cases else args.group)
        if baseline:
            print(run_baseline_benchmarks(args.attempt, group_ids=gids, timeout_seconds=args.timeout_seconds))
        else:
            print(run_benchmarks(args.attempt, group_ids=gids, scope=args.scope,
                                 timeout_seconds=args.timeout_seconds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
