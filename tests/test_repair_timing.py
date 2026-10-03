"""Synthetic timing observations only: this suite NEVER benchmarks or trains.

Inventory is real source-only enumeration. Wall times, clean-environment records
and worker completions below are deliberately fabricated to exercise refusal
and accounting, not measurements and never deliverable timing evidence.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu import constants as K
from bu.config import Arm, Config
from bu.experiments import repair_timing as T
from bu.experiments.enumerate_units import design_units, execution_plan, experiment_1_units
from bu.experiments.w4_timing import design_accounting, extrapolate
from bu.runrecord import GitState


@pytest.fixture(autouse=True)
def never_train(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("timing tests must never collect or train actual data/models")
    monkeypatch.setattr(T, "collect_pools", forbidden)
    monkeypatch.setattr(T, "train_ensemble", forbidden)


@pytest.fixture(scope="module")
def inventories():
    return {scope: T.repair_inventory(scope) for scope in T.SCOPES}


def fake_environment():
    pins = T.P._pinned_package_versions()
    return {"source_commit": "a" * 40, "source_tree_clean": True,
            "packages": pins, "pins": dict(pins), "platform": "synthetic-test-host",
            "processor": "synthetic-cpu", "python": "3.13.5", "machine": "synthetic",
            "hostname": "synthetic-machine", "logical_cpu_count": 8,
            "device": "cpu", "threading": {"num_threads": 4, "num_interop_threads": 4},
            "dtype": "torch.float32"}


def fake_benchmark(group: dict, inventory: dict) -> dict:
    def trial(seed, c, t):
        return {"seed": seed, "collection_s": c, "training_s": t, "epochs_run": 23}
    return {
        "schema_version": T.REPAIR_TIMING_SCHEMA_VERSION,
        "group_id": group["group_id"], "case": copy.deepcopy(group["benchmark_case"]),
        "contract": copy.deepcopy(inventory["contract"]),
        "registered_execution_plan_sha256": inventory["registered_execution_plan_sha256"],
        "environment_before": fake_environment(), "environment_after": fake_environment(),
        "warmup": trial(0, 999.0, 999.0),
        "repetitions": [trial(s, float(s), 10.0 * s) for s in T.MEASUREMENT_SEEDS],
    }


@pytest.fixture(scope="module")
def fake_all(inventories):
    inventory = inventories["all_repairs"]
    return [fake_benchmark(g, inventory) for g in inventory["groups"]]


@pytest.fixture
def fast_registry(monkeypatch, inventories):
    """Reuse source-derived snapshots only in consumer tests, not inventory tests."""
    def inventory(scope="all_repairs"):
        if scope not in inventories:
            raise ValueError("unknown timing scope")
        return copy.deepcopy(inventories[scope])
    monkeypatch.setattr(T, "repair_inventory", inventory)


def test_registered_inventory_prices_every_repair_exactly_once(inventories):
    actual = inventories["all_repairs"]
    plan = [f for f in execution_plan(design_units()) if f.arm != "baseline"]
    assert actual["model_fits"] == actual["collection_events"] == len(plan) == 2310
    assert actual["configuration_count"] == 600
    assert actual["extension_model_fits"] == 638
    assert len(actual["groups"]) == 17
    expected = {(Config(unit=f.unit, arm=Arm(f.arm)).config_id, f.seed, f.roles) for f in plan}
    observed = [(cfg["config_id"], r["seed_index"], tuple(r["roles"]))
                for g in actual["groups"] for cfg in g["configs"]
                for r in cfg["requirements"]]
    assert len(observed) == len(set(observed))
    assert set(observed) == expected
    assert actual["all_registered_repair_models"] == 2310
    assert actual["baselines_included"] is actual["ablations_included"] is False
    assert actual["ablation_allowance_not_priced"] == 150


@pytest.mark.parametrize("scope,count,groups,extensions", [
    ("e1_and_extension", 830, 12, 638), ("e1_repairs", 384, 12, 192),
    ("extension", 638, 6, 638), ("all_repairs", 2310, 17, 638),
])
def test_scopes_are_exact_and_the_default_covers_all_d154_additions(
        inventories, scope, count, groups, extensions):
    got = inventories[scope]
    assert got["model_fits"] == count
    assert len(got["groups"]) == groups
    assert got["extension_model_fits"] == extensions
    assert got["registered_execution_plan_sha256"] == \
        inventories["all_repairs"]["registered_execution_plan_sha256"]


def test_data_repair_uses_tenfold_size_and_effective_input_width(inventories):
    data = []
    for group in inventories["all_repairs"]["groups"]:
        for cfg in group["configs"]:
            effective = cfg["effective_unit"]
            assert effective["n_transitions"] == group["n_transitions"]
            assert effective["hidden_size"] == group["architecture"]["hidden_size"]
            if cfg["arm"] == "data_repair":
                data.append(cfg)
                assert effective["n_transitions"] == cfg["unit"]["n_transitions"] * 10
    assert max(c["effective_unit"]["n_transitions"] for c in data) == 50000
    masked = [g for g in inventories["all_repairs"]["groups"]
              if g["architecture"]["observation_dim"] == 22]
    assert len(masked) == 1
    assert masked[0]["architecture"]["input_dim"] == 27
    assert masked[0]["n_transitions"] == 50000
    assert masked[0]["model_fits"] == 176
    for g in inventories["all_repairs"]["groups"]:
        assert g["architecture"]["n_hidden_layers"] == 2
        assert g["architecture"]["position_outputs"] == 2
        assert g["architecture"]["activation_outputs"] == 4


def test_same_size_different_architectures_are_never_merged(inventories):
    groups = inventories["all_repairs"]["groups"]
    at_50000 = [g for g in groups if g["n_transitions"] == 50000]
    assert len(at_50000) == 6  # five widths, plus width-256 masked input
    assert len({g["group_id"] for g in at_50000}) == 6
    assert {g["architecture"]["hidden_size"] for g in at_50000} == set(K.HIDDEN_SIZES)


def test_representatives_are_fixed_registered_original_units_and_real_arms(inventories):
    e1 = {Config(unit=u).unit_id for u in experiment_1_units()}
    all_groups = inventories["all_repairs"]["groups"]
    for group in all_groups:
        case = group["benchmark_case"]
        config = Config.from_dict(case["config"])
        assert config.arm.kind != "baseline"
        assert config.train == T.C.REPAIRED_TRAIN
        assert config.stage == "pilot" and config.seed == 0
        assert config.effective_unit.n_transitions == group["n_transitions"]
        assert T._architecture(config.effective_unit) == group["architecture"]
        candidates = group["configs"]
        expected = min(candidates, key=lambda c: (c["unit_id"] not in e1,
                                                 c["unit_id"], c["arm"]))
        assert config.config_id == expected["config_id"]
    # Scope changes accounting, never cherry-picks a faster representative.
    global_cases = {g["group_id"]: g["benchmark_case"] for g in all_groups}
    for inventory in inventories.values():
        for group in inventory["groups"]:
            assert group["benchmark_case"] == global_cases[group["group_id"]]


def test_inventory_and_case_order_are_independent_of_enumerator_order(monkeypatch, inventories):
    real_plan = T.execution_plan
    monkeypatch.setattr(T, "execution_plan", lambda units: tuple(reversed(real_plan(units))))
    assert T.repair_inventory() == inventories["all_repairs"]


def test_duplicate_enumerator_requirements_fail_closed(monkeypatch):
    plan = execution_plan(design_units())
    monkeypatch.setattr(T, "execution_plan", lambda units: (*plan, plan[0]))
    with pytest.raises(ValueError, match="duplicate"):
        T.repair_inventory()


def test_exact_frozen_train_and_four_four_threads(inventories):
    contract = inventories["all_repairs"]["contract"]
    assert contract["train"] == asdict(T.C.REPAIRED_TRAIN)
    assert contract["train"]["ensemble_size"] == 1
    assert contract["train"]["max_epochs"] == 500
    assert contract["threading"] == {"num_threads": 4, "num_interop_threads": 4}
    assert contract["device"] == "cpu"
    assert contract["stage"] == "pilot" and contract["seed_partition"] == "development"
    assert contract["measurement_seeds"] == [1, 2, 3]


@pytest.mark.parametrize("seeds", [(1000, 1001, 1002), (True, 2, 3), (1, 1, 2), (1, 2), (0, 1, 2)])
def test_timing_contract_refuses_non_development_or_incomplete_seeds(monkeypatch, seeds):
    monkeypatch.setattr(T, "MEASUREMENT_SEEDS", seeds)
    with pytest.raises(ValueError, match="development"):
        T._contract()


def test_complete_full_repair_projection_uses_raw_medians_and_maxima(
        fast_registry, inventories, fake_all):
    for how, seconds in (("median", 22.0), ("max", 33.0)):
        got = T.project_repairs(inventories["all_repairs"], fake_all, how)
        assert got["total_s"] == 2310 * seconds
        assert got["local_wall_hours"] == 2310 * seconds / 3600
        assert len(got["contributions"]) == 17
    # Warm-up takes 1998 seconds in our fixture: if it leaks in, this fails.
    assert T.project_repairs(inventories["extension"], fake_all)["total_s"] == 638 * 33


def test_all_d154_models_need_width512_measurements(fast_registry, inventories, fake_all):
    legacy_widths = [b for b in fake_all if b["case"]["architecture"]["hidden_size"] != 512]
    for scope in ("extension", "e1_repairs", "e1_and_extension", "all_repairs"):
        with pytest.raises(ValueError, match="missing exact.*width=512"):
            T.project_repairs(inventories[scope], legacy_widths)


def test_no_nearest_size_pricing_even_at_identical_width(fast_registry, inventories, fake_all):
    missing = next(b for b in fake_all if b["case"]["architecture"]["hidden_size"] == 512
                   and b["case"]["n_transitions"] == 100)
    rest = [b for b in fake_all if b["group_id"] != missing["group_id"]]
    with pytest.raises(ValueError, match="no scaled or nearest-size"):
        T.project_repairs(inventories["extension"], rest)


def test_partial_record_does_not_claim_unmeasured_plan_costs(fast_registry, fake_all):
    record = T.build_timing_record([fake_all[0]])
    assert record["complete_scope_coverage"] is False
    assert len(record["missing_group_ids"]) == 11
    assert record["extrapolation"] is None
    complete = T.build_timing_record(fake_all, "all_repairs")
    assert complete["complete_scope_coverage"] is True
    assert complete["missing_group_ids"] == []
    assert complete["extrapolation"]["max"]["model_fits"] == 2310


def test_default_minimal_cases_cannot_price_whole_repair_plan(fast_registry, inventories, fake_all):
    ids = {g["group_id"] for g in inventories[T.DEFAULT_SCOPE]["groups"]}
    subset = [b for b in fake_all if b["group_id"] in ids]
    assert T.build_timing_record(subset)["complete_scope_coverage"] is True
    with pytest.raises(ValueError, match="missing exact"):
        T.project_repairs(inventories["all_repairs"], subset)


@pytest.mark.parametrize("how", ["maximum", "MEAN", "", None, True])
def test_unknown_summary_is_not_silently_max(fast_registry, inventories, fake_all, how):
    with pytest.raises(ValueError, match="summary"):
        T.project_repairs(inventories["all_repairs"], fake_all, how)


def test_resigned_inventory_changes_still_fail_closed(fast_registry, inventories, fake_all):
    record = copy.deepcopy(inventories["all_repairs"])
    record["groups"][0]["model_fits"] += 1
    body = {k: v for k, v in record.items() if k != "inventory_sha256"}
    record["inventory_sha256"] = T._digest(body)
    with pytest.raises(ValueError, match="repair inventory differs"):
        T.project_repairs(record, fake_all)


@pytest.mark.parametrize("field,value", [
    ("source_commit", "short"), ("source_tree_clean", False), ("source_tree_clean", 1),
    ("threading", {"num_threads": 8, "num_interop_threads": 4}),
    ("threading", {"num_threads": 4, "num_interop_threads": 8}),
    ("device", "cuda"), ("dtype", "torch.float64"), ("processor", ""),
    ("hostname", ""), ("logical_cpu_count", True), ("logical_cpu_count", 0),
])
def test_invalid_runtime_provenance_refused(fast_registry, fake_all, field, value):
    bad = copy.deepcopy(fake_all[0])
    for side in ("environment_before", "environment_after"):
        bad[side][field] = value
    with pytest.raises(ValueError):
        T.build_timing_record([bad])


def test_pins_cannot_be_redeclared_to_match_wrong_runtime(fast_registry, fake_all):
    bad = copy.deepcopy(fake_all[0])
    for side in ("environment_before", "environment_after"):
        bad[side]["packages"]["torch"] = "made-up"
        bad[side]["pins"]["torch"] = "made-up"
    with pytest.raises(ValueError, match="runtime pins"):
        T.build_timing_record([bad])


def test_actual_packages_must_match_pins(fast_registry, fake_all):
    bad = copy.deepcopy(fake_all[0])
    bad["environment_before"]["packages"]["numpy"] = "old"
    with pytest.raises(ValueError, match="observed packages"):
        T.build_timing_record([bad])


def test_mixed_commits_or_hosts_cannot_share_a_projection(fast_registry, fake_all):
    for field, value in (("source_commit", "b" * 40), ("processor", "other-cpu"),
                         ("hostname", "a-different-device")):
        rows = copy.deepcopy(fake_all[:2])
        for side in ("environment_before", "environment_after"):
            rows[1][side][field] = value
        with pytest.raises(ValueError, match="combined benchmark"):
            T.build_timing_record(rows)


def test_source_changes_during_measurement_refused(fast_registry, fake_all):
    bad = copy.deepcopy(fake_all[0])
    bad["environment_after"]["source_commit"] = "b" * 40
    with pytest.raises(ValueError, match="before/after"):
        T.build_timing_record([bad])


@pytest.mark.parametrize("field,value", [
    ("training_s", 0), ("training_s", -1), ("collection_s", True),
    ("training_s", float("nan")), ("collection_s", float("inf")),
    ("seed", 1000), ("seed", True), ("epochs_run", 0), ("epochs_run", 501),
    ("epochs_run", 1.0),
])
def test_invalid_raw_repetitions_refused(fast_registry, fake_all, field, value):
    bad = copy.deepcopy(fake_all[0])
    bad["repetitions"][0][field] = value
    with pytest.raises(ValueError):
        T.build_timing_record([bad])


@pytest.mark.parametrize("mutation", ["short_reps", "warmup_seed", "architecture", "size",
                                       "train", "plan", "schema", "extra_field"])
def test_missing_or_substituted_measurement_contracts_refused(fast_registry, fake_all, mutation):
    bad = copy.deepcopy(fake_all[0])
    if mutation == "short_reps":
        bad["repetitions"].pop()
    elif mutation == "warmup_seed":
        bad["warmup"]["seed"] = 1000
    elif mutation == "architecture":
        bad["case"]["architecture"]["hidden_size"] = 256
    elif mutation == "size":
        bad["case"]["n_transitions"] *= 10
    elif mutation == "train":
        bad["contract"]["train"]["max_epochs"] = 1
    elif mutation == "plan":
        bad["registered_execution_plan_sha256"] = "0" * 64
    elif mutation == "schema":
        bad["schema_version"] = True
    else:
        bad["best_validation_error"] = 0.0
    with pytest.raises(ValueError):
        T.build_timing_record([bad])


def test_duplicate_missing_or_unknown_benchmarks_refused(fast_registry, fake_all):
    with pytest.raises(ValueError, match="duplicate"):
        T.build_timing_record([fake_all[0], fake_all[0]])
    with pytest.raises(ValueError, match="no benchmarks"):
        T.build_timing_record([])
    bad = copy.deepcopy(fake_all[0])
    bad["group_id"] = "unknown"
    with pytest.raises(ValueError, match="unknown"):
        T.build_timing_record([bad])


def test_legacy_width512_refusal_and_old_size_rates_are_unchanged():
    with pytest.raises(ValueError, match="architecture-aware"):
        extrapolate({}, design_accounting(), "max")


def test_round_trip_digest_and_derived_projection(fast_registry, fake_all, tmp_path):
    record = T.build_timing_record(fake_all, "all_repairs")
    path = T.write_timing_record(tmp_path / "timing.json", record)
    assert T.load_timing_record(path) == record
    assert path.with_name("timing.json.sha256").read_text().strip() == T.sha256_file(path)
    # Identical retry is safe and immutable; different records cannot replace it.
    assert T.write_timing_record(path, record) == path
    altered = copy.deepcopy(record)
    altered["benchmarks"][0]["repetitions"][0]["training_s"] = 123.0
    rebuilt = T.build_timing_record(altered["benchmarks"], "all_repairs")
    with pytest.raises(ValueError, match="different|divergent|differs"):
        T.write_timing_record(path, rebuilt)


def test_payload_tampering_is_caught_even_after_resigning(fast_registry, fake_all, tmp_path):
    record = T.build_timing_record(fake_all, "all_repairs")
    record["extrapolation"]["max"]["total_s"] = 1.0
    path = tmp_path / "forged.json"
    path.write_bytes(T._json(record))
    path.with_name(path.name + ".sha256").write_text(T.sha256_file(path) + "\n")
    with pytest.raises(ValueError, match="stored timing record"):
        T.load_timing_record(path)
    with pytest.raises(ValueError, match="timing record"):
        T.write_timing_record(tmp_path / "also-forged.json", record)
    assert not (tmp_path / "also-forged.json").exists()


def test_wrong_sidecar_is_not_accepted(fast_registry, fake_all, tmp_path):
    path = T.write_timing_record(tmp_path / "timing.json", T.build_timing_record(fake_all[:1]))
    path.with_name(path.name + ".sha256").write_text("0" * 64 + "\n")
    with pytest.raises(ValueError, match="digest"):
        T.load_timing_record(path)


def test_directory_loading_checks_the_artifact_itself_for_aliases(
        fast_registry, fake_all, tmp_path, monkeypatch):
    target = T.write_timing_record(tmp_path / "timing.json", T.build_timing_record(fake_all[:1]))
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == target or original(p))
    with pytest.raises(ValueError, match="symlinks/junctions"):
        T.load_timing_record(tmp_path)


def test_paths_must_stay_inside_project():
    for path in (T.PROJECT_ROOT, T.PROJECT_ROOT.parent / "outside-timing.json"):
        with pytest.raises(ValueError, match="inside the project"):
            T._inside_project(path)


def test_time_once_uses_actual_repair_single_model_and_fixed_cpu_route(monkeypatch, inventories):
    case = next(g["benchmark_case"] for g in inventories["all_repairs"]["groups"]
                if g["architecture"]["hidden_size"] == 512)
    calls = []
    pools = object()
    config = Config.from_dict(case["config"])
    monkeypatch.setattr(T.C, "torch_threading", lambda: {"num_threads": 4, "num_interop_threads": 4})
    clock = iter([1.0, 3.0, 8.0])
    monkeypatch.setattr(T.time, "perf_counter", lambda: next(clock))
    def collect(unit, **kwargs):
        calls.append(("collect", unit, kwargs))
        return pools
    def train(unit, actual_pools, train, **kwargs):
        calls.append(("train", unit, kwargs))
        assert actual_pools is pools and train == T.C.REPAIRED_TRAIN
        return SimpleNamespace(members=[object()], results=[SimpleNamespace(epochs_run=45)])
    monkeypatch.setattr(T, "collect_pools", collect)
    monkeypatch.setattr(T, "train_ensemble", train)
    got = T._time_once(case, 1)
    assert got == {"seed": 1, "collection_s": 2.0, "training_s": 5.0, "epochs_run": 45}
    assert calls[0][1] == config.unit and calls[1][1] == config.unit
    assert config.unit.hidden_size == 256  # NOT replaced with resolved unit stream keys
    assert calls[0][2] == {"stage": "pilot", "seed": 1, "arm": "capacity_extension_repair"}
    assert calls[1][2] == {"stage": "pilot", "seed": 1, "arm": "capacity_extension_repair",
                            "granularity": "episode", "logger": None, "device": "cpu"}


@pytest.mark.parametrize("seed", [1000, -1, True, 1.0, 4])
def test_time_once_refuses_unregistered_seeds_before_collect(seed):
    with pytest.raises(ValueError, match="fixed development"):
        T._time_once({}, seed)


def test_worker_has_one_warmup_three_reps_and_before_after_provenance(
        fast_registry, monkeypatch, fake_all, tmp_path):
    expected = fake_all[0]
    events = []
    def environment(*, pin=False):
        events.append(("environment", pin))
        return fake_environment()
    def time_once(case, seed):
        events.append(("measure", seed))
        assert case == expected["case"]
        return copy.deepcopy(expected["warmup"] if seed == 0 else expected["repetitions"][seed - 1])
    monkeypatch.setattr(T, "_environment", environment)
    monkeypatch.setattr(T, "_time_once", time_once)
    receipts = tmp_path / "receipts"
    assert T._benchmark_group(expected["group_id"], receipt_dir=receipts) == expected
    assert events == [("environment", True), ("measure", 0), ("measure", 1),
                      ("measure", 2), ("measure", 3), ("environment", False)]
    assert len(list(receipts.glob("*.json"))) == 5
    sample = json.loads((receipts / "measured-s001.json").read_bytes())
    assert sample["trial"] == expected["repetitions"][0]
    assert sample["case_sha256"] == T._digest(expected["case"])


def test_bad_worker_environment_fails_before_measurement(fast_registry, monkeypatch, fake_all, tmp_path):
    def bad_environment(**kwargs):
        raise ValueError("dirty source")
    monkeypatch.setattr(T, "_environment", bad_environment)
    monkeypatch.setattr(T, "_time_once", lambda *a: pytest.fail("must fail before timing"))
    with pytest.raises(ValueError, match="dirty source"):
        T._benchmark_group(fake_all[0]["group_id"], receipt_dir=tmp_path / "no-receipts")
    assert not (tmp_path / "no-receipts").exists()


def test_interrupted_group_retains_completed_repetition_receipts(
        fast_registry, monkeypatch, fake_all, tmp_path):
    benchmark = fake_all[0]
    monkeypatch.setattr(T, "_environment", lambda **kwargs: fake_environment())
    def interrupted(case, seed):
        if seed == 2:
            raise RuntimeError("synthetic interruption")
        return benchmark["warmup"] if seed == 0 else benchmark["repetitions"][0]
    monkeypatch.setattr(T, "_time_once", interrupted)
    receipts = tmp_path / "interrupted-receipts"
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        T._benchmark_group(benchmark["group_id"], receipt_dir=receipts)
    assert {p.name for p in receipts.glob("*.json")} == {
        "start.json", "warmup-s000.json", "measured-s001.json"}


def test_finite_raw_times_cannot_overflow_projection(fast_registry, inventories, fake_all):
    rows = copy.deepcopy(fake_all)
    for row in rows:
        for rep in row["repetitions"]:
            rep["training_s"] = 1e308
    with pytest.raises(ValueError, match="overflowed"):
        T.project_repairs(inventories["all_repairs"], rows)


def test_live_environment_pins_and_verifies_four_four_threads(monkeypatch):
    pins = T.P._pinned_package_versions()
    monkeypatch.setattr(T.P, "_verify_environment", lambda: (GitState("a" * 40, False, "test"), pins, pins))
    calls = []
    monkeypatch.setattr(T.C, "_pin_threading", lambda a, b: calls.append((a, b)))
    monkeypatch.setattr(T.C, "torch_threading", lambda: {"num_threads": 4, "num_interop_threads": 4})
    monkeypatch.setattr(T.torch, "get_default_dtype", lambda: T.torch.float32)
    monkeypatch.setattr(T.torch, "get_default_device", lambda: "cpu")
    env = T._environment(pin=True)
    assert calls == [(4, 4)]
    T._validate_environment(env)
    monkeypatch.setattr(T.C, "torch_threading", lambda: {"num_threads": 8, "num_interop_threads": 4})
    with pytest.raises(ValueError, match="actual CPU threading"):
        T._environment(pin=True)


@pytest.mark.parametrize("kind", ["device", "dtype"])
def test_nonfrozen_default_torch_route_refused(monkeypatch, kind):
    pins = T.P._pinned_package_versions()
    monkeypatch.setattr(T.P, "_verify_environment", lambda: (GitState("a" * 40, False, "test"), pins, pins))
    monkeypatch.setattr(T.C, "torch_threading", lambda: {"num_threads": 4, "num_interop_threads": 4})
    monkeypatch.setattr(T.torch, "get_default_dtype", lambda: T.torch.float64 if kind == "dtype" else T.torch.float32)
    monkeypatch.setattr(T.torch, "get_default_device", lambda: "cuda" if kind == "device" else "cpu")
    with pytest.raises(ValueError, match="CPU|float32"):
        T._environment()


def mock_worker(monkeypatch, fake_all, *, timeout=False, wrong_group=False):
    by_group = {r["group_id"]: r for r in fake_all}
    calls = []
    monkeypatch.setattr(T, "_environment", lambda **kwargs: fake_environment())
    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[0] == "git":
            return SimpleNamespace(returncode=0)
        assert "--worker-group" in command
        if timeout:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        gid = command[command.index("--worker-group") + 1]
        destination = command[command.index("--output") + 1]
        selected = fake_all[1] if wrong_group else by_group[gid]
        T.write_timing_record(destination, T.build_timing_record([selected], "all_repairs"))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(T.subprocess, "run", run)
    return calls


def test_launcher_is_explicit_bounded_fresh_process_and_project_local(
        fast_registry, monkeypatch, fake_all, tmp_path):
    calls = mock_worker(monkeypatch, fake_all)
    gid = fake_all[0]["group_id"]
    attempt = tmp_path / "attempt-001"
    result = T.run_benchmarks(attempt, group_ids=[gid], timeout_seconds=42)
    assert result == attempt / "timing.json"
    assert T.load_timing_record(result)["complete_scope_coverage"] is False
    start = json.loads((attempt / "start.json").read_bytes())
    assert start["per_group_timeout_seconds"] == start["max_worker_wall_seconds"] == 42
    assert start["environment"] == fake_environment()
    process, kwargs = calls[1]
    expected = (T.sys._base_executable if T.sys.platform == "win32" else T.sys.executable)
    assert process[:3] == [expected, "-m", "bu.experiments.repair_timing"]
    assert kwargs["timeout"] == 42
    assert kwargs["cwd"] == T.PROJECT_ROOT
    assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    for name in ("TEMP", "TMP", "TMPDIR", "MPLCONFIGDIR"):
        assert Path(kwargs["env"][name]).is_relative_to(attempt)
    with pytest.raises(FileExistsError):
        T.run_benchmarks(attempt, group_ids=[gid])


def test_windows_worker_bypasses_redirector_but_preserves_venv(monkeypatch, tmp_path):
    monkeypatch.setattr(T.sys, "platform", "win32")
    monkeypatch.setattr(T.sys, "executable", "D:/project/.venv/Scripts/python.exe")
    monkeypatch.setattr(T.sys, "_base_executable", "C:/Python313/python.exe")
    env = {}
    command = T._worker_command("group", tmp_path / "output.json", env)
    assert command[0] == "C:/Python313/python.exe"
    assert env["__PYVENV_LAUNCHER__"] == "D:/project/.venv/Scripts/python.exe"


def test_nonwindows_worker_uses_current_interpreter_without_launcher_marker(monkeypatch, tmp_path):
    monkeypatch.setattr(T.sys, "platform", "linux")
    env = {}
    assert T._worker_command("group", tmp_path / "output.json", env)[0] == T.sys.executable
    assert "__PYVENV_LAUNCHER__" not in env


def test_direct_child_really_keeps_current_virtual_environment(tmp_path):
    """A harmless interpreter probe, NOT a benchmark or training invocation."""
    env = dict(os.environ)
    env.update(PYTHONDONTWRITEBYTECODE="1", TEMP=str(tmp_path), TMP=str(tmp_path),
               TMPDIR=str(tmp_path), MPLCONFIGDIR=str(tmp_path))
    command = T._worker_command("unused", tmp_path / "not-written.json", env)
    probe = subprocess.run(
        [command[0], "-c", "import json,sys; print(json.dumps([sys.executable, sys.prefix]))"],
        cwd=T.PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=30, check=True,
    )
    executable, prefix = json.loads(probe.stdout)
    assert os.path.normcase(executable) == os.path.normcase(T.sys.executable)
    assert os.path.normcase(prefix) == os.path.normcase(T.sys.prefix)
    assert not (tmp_path / "not-written.json").exists()


def test_timeout_keeps_start_and_logs_without_success_record(
        fast_registry, monkeypatch, fake_all, tmp_path):
    mock_worker(monkeypatch, fake_all, timeout=True)
    gid = fake_all[0]["group_id"]
    attempt = tmp_path / "timeout-attempt"
    with pytest.raises(subprocess.TimeoutExpired):
        T.run_benchmarks(attempt, group_ids=[gid], timeout_seconds=1)
    assert (attempt / "start.json").is_file()
    assert (attempt / (gid + ".stderr.log")).is_file()
    assert not (attempt / "timing.json").exists()


def test_substituted_worker_group_cannot_complete_launch(fast_registry, monkeypatch, fake_all, tmp_path):
    mock_worker(monkeypatch, fake_all, wrong_group=True)
    attempt = tmp_path / "wrong-worker"
    with pytest.raises(ValueError, match="wrong requested group"):
        T.run_benchmarks(attempt, group_ids=[fake_all[0]["group_id"]])
    assert not (attempt / "timing.json").exists()


@pytest.mark.parametrize("seconds", [0, -1, True, 1.5, 86401])
def test_bad_timeout_never_starts_compute(tmp_path, seconds):
    with pytest.raises(ValueError, match="timeout_seconds"):
        T.run_benchmarks(tmp_path / "no-start", group_ids=[], timeout_seconds=seconds)
    assert not (tmp_path / "no-start").exists()


@pytest.mark.parametrize("groups", [[], ["unknown"]])
def test_missing_or_unknown_groups_fail_before_io(fast_registry, tmp_path, groups):
    with pytest.raises(ValueError, match="nonempty, distinct exact"):
        T.run_benchmarks(tmp_path / "no-start", group_ids=groups)
    assert not (tmp_path / "no-start").exists()


def test_unignored_attempt_refused_before_environment_or_files(
        fast_registry, monkeypatch, fake_all, tmp_path):
    monkeypatch.setattr(T.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))
    monkeypatch.setattr(T, "_environment", lambda **k: pytest.fail("must refuse before environment"))
    with pytest.raises(ValueError, match="Git-ignored"):
        T.run_benchmarks(tmp_path / "bad-output", group_ids=[fake_all[0]["group_id"]])
    assert not (tmp_path / "bad-output").exists()


def test_list_cli_never_starts_a_benchmark(fast_registry, monkeypatch, capsys):
    monkeypatch.setattr(T, "run_benchmarks", lambda *a, **k: pytest.fail("list must not run"))
    assert T.main(["--list-cases"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 12
    assert sum("width=512" in line for line in lines) == 6


def test_cli_requires_explicit_compute_mode():
    with pytest.raises(SystemExit):
        T.main([])


def test_combine_cli_verifies_sources_without_compute(
        fast_registry, monkeypatch, fake_all, tmp_path):
    paths = [T.write_timing_record(tmp_path / f"part-{i}.json", T.build_timing_record([b]))
             for i, b in enumerate(fake_all[:2])]
    monkeypatch.setattr(T, "run_benchmarks", lambda *a, **k: pytest.fail("combine must not run"))
    output = tmp_path / "combined.json"
    assert T.main(["--combine", *(str(p) for p in paths), "--output", str(output)]) == 0
    assert len(T.load_timing_record(output)["benchmarks"]) == 2


# Separate narrow E1-baseline contract. These observations are also synthetic.


@pytest.fixture(scope="module")
def baseline_inventory():
    return T.baseline_inventory()


@pytest.fixture(scope="module")
def fake_baselines(baseline_inventory):
    result = []
    for group in baseline_inventory["groups"]:
        row = fake_benchmark(group, baseline_inventory)
        row["artifact_type"] = "development_e1_baseline_case"
        for trial in [row["warmup"], *row["repetitions"]]:
            trial["epochs_run"] = [23, 24, 25, 26, 27]
        result.append(row)
    return result


@pytest.fixture
def fast_baseline(monkeypatch, baseline_inventory):
    monkeypatch.setattr(T, "baseline_inventory", lambda: copy.deepcopy(baseline_inventory))


def test_baseline_inventory_is_exact_90_higher_seed_ensembles(baseline_inventory):
    inv = baseline_inventory
    assert inv["ensemble_jobs"] == inv["collection_events"] == 90
    assert inv["model_fits"] == 450
    assert inv["configuration_count"] == len(inv["groups"]) == 6
    assert inv["original_e1_baselines_included"] is False
    assert inv["repairs_included"] is inv["ablations_included"] is False
    assert inv["contract"]["train"] == asdict(T.C.CONFIRMATORY_TRAIN)
    assert inv["contract"]["threading"] == {"num_threads": 4, "num_interop_threads": 4}
    for group in inv["groups"]:
        assert group["ensemble_jobs"] == group["collection_events"] == 15
        assert group["model_fits"] == 75
        assert group["architecture"]["hidden_size"] == 256
        assert group["architecture"]["observation_dim"] == 30
        config = Config.from_dict(group["benchmark_case"]["config"])
        assert config.unit == T._reference_unit(group["n_transitions"])
        assert config.unit.layout == "uniform" and config.unit.causal_attribute == "shape"
        assert config.unit.withheld_features == () and config.stage == "pilot"
        assert config.arm.kind == "baseline" and config.train.ensemble_size == 5
        assert [r["seed_index"] for r in group["requirements"]] == list(range(5, 20))
        assert all(r["roles"] == ["repair_validation"] for r in group["requirements"])
    assert sum(len(g["requirements"]) for g in inv["groups"]) == 90


def test_baseline_inventory_binds_same_full_plan_but_cannot_collide_with_repairs(
        baseline_inventory, inventories):
    assert baseline_inventory["registered_execution_plan_sha256"] == \
        inventories["all_repairs"]["registered_execution_plan_sha256"]
    baseline_ids = {g["group_id"] for g in baseline_inventory["groups"]}
    repair_ids = {g["group_id"] for g in inventories["all_repairs"]["groups"]}
    assert not baseline_ids & repair_ids


def test_baseline_counts_refuse_missing_or_duplicate_higher_seed_jobs(monkeypatch):
    plan = execution_plan(design_units())
    index = next(i for i, f in enumerate(plan) if f.arm == "baseline" and f.seed == 19
                 and f.unit == T._reference_unit(100))
    monkeypatch.setattr(T, "execution_plan", lambda units: plan[:index] + plan[index + 1:])
    with pytest.raises(ValueError, match="exactly 90"):
        T.baseline_inventory()
    monkeypatch.setattr(T, "execution_plan", lambda units: (*plan, plan[index]))
    with pytest.raises(ValueError, match="duplicate"):
        T.baseline_inventory()


@pytest.mark.parametrize("how,seconds", [("median", 22.0), ("max", 33.0)])
def test_baseline_projection_charges_ensembles_not_members_and_collects_once(
        fast_baseline, baseline_inventory, fake_baselines, how, seconds):
    projection = T.project_baselines(baseline_inventory, fake_baselines, how)
    assert projection["ensemble_jobs"] == 90 and projection["model_fits"] == 450
    assert projection["total_s"] == 90 * seconds
    assert projection["collection_s"] == 90 * (2 if how == "median" else 3)
    assert len(projection["contributions"]) == 6


def test_baseline_projection_requires_all_six_exact_groups(fast_baseline, baseline_inventory, fake_baselines):
    with pytest.raises(ValueError, match="missing exact baseline"):
        T.project_baselines(baseline_inventory, fake_baselines[1:])
    partial = T.build_baseline_timing_record(fake_baselines[:1])
    assert partial["complete_scope_coverage"] is False
    assert partial["extrapolation"] is None and len(partial["missing_group_ids"]) == 5


def test_baseline_and_repair_records_reject_each_other(fast_baseline, fast_registry, fake_all, fake_baselines):
    with pytest.raises(ValueError, match="repair records cannot enter"):
        T.build_baseline_timing_record(fake_all)
    with pytest.raises(ValueError, match="missing or unknown fields"):
        T.build_timing_record(fake_baselines)


@pytest.mark.parametrize("bad", [[], [23], [23] * 4, [23] * 6, [True] * 5, [501] * 5, 23])
def test_baseline_trials_require_exactly_five_valid_epoch_counts(fast_baseline, fake_baselines, bad):
    row = copy.deepcopy(fake_baselines[0])
    row["repetitions"][0]["epochs_run"] = bad
    with pytest.raises(ValueError, match="five valid member"):
        T.build_baseline_timing_record([row])


@pytest.mark.parametrize("mutation", ["architecture", "members", "training", "seed",
                                       "commit", "threads", "plan", "kind", "repetitions"])
def test_baseline_measurement_substitution_fails_closed(fast_baseline, fake_baselines, mutation):
    row = copy.deepcopy(fake_baselines[0])
    if mutation == "architecture":
        row["case"]["architecture"]["hidden_size"] = 512
    elif mutation == "members":
        row["case"]["members"] = 1
    elif mutation == "training":
        row["contract"]["train"]["max_epochs"] = 1
    elif mutation == "seed":
        row["repetitions"][0]["seed"] = 1005
    elif mutation == "commit":
        row["environment_after"]["source_commit"] = "b" * 40
    elif mutation == "threads":
        row["environment_before"]["threading"]["num_interop_threads"] = 8
    elif mutation == "plan":
        row["registered_execution_plan_sha256"] = "0" * 64
    elif mutation == "kind":
        row["artifact_type"] = "development_repair_case"
    else:
        row["repetitions"].pop()
    with pytest.raises(ValueError):
        T.build_baseline_timing_record([row])


def test_baseline_duplicate_empty_unknown_groups_and_mixed_hosts_refused(fast_baseline, fake_baselines):
    with pytest.raises(ValueError, match="duplicate"):
        T.build_baseline_timing_record([fake_baselines[0], fake_baselines[0]])
    with pytest.raises(ValueError, match="no baseline benchmarks"):
        T.build_baseline_timing_record([])
    unknown = copy.deepcopy(fake_baselines[0])
    unknown["group_id"] = "unknown"
    with pytest.raises(ValueError, match="unknown"):
        T.build_baseline_timing_record([unknown])
    rows = copy.deepcopy(fake_baselines[:2])
    for side in ("environment_before", "environment_after"):
        rows[1][side]["hostname"] = "different-host"
    with pytest.raises(ValueError, match="combined baseline"):
        T.build_baseline_timing_record(rows)


def test_resigned_baseline_inventory_is_not_authority(fast_baseline, baseline_inventory, fake_baselines):
    changed = copy.deepcopy(baseline_inventory)
    changed["groups"][0]["ensemble_jobs"] = 1
    changed["inventory_sha256"] = T._digest({k: v for k, v in changed.items() if k != "inventory_sha256"})
    with pytest.raises(ValueError, match="baseline inventory"):
        T.project_baselines(changed, fake_baselines)


def test_baseline_record_round_trip_and_resigned_projection_tampering(
        fast_baseline, fake_baselines, tmp_path):
    record = T.build_baseline_timing_record(fake_baselines)
    target = T.write_baseline_timing_record(tmp_path / "timing.json", record)
    assert T.load_baseline_timing_record(tmp_path) == record
    assert record["complete_scope_coverage"] is True
    assert T.write_baseline_timing_record(target, record) == target
    changed = copy.deepcopy(record)
    changed["extrapolation"]["max"]["total_s"] = 0.0
    forged = tmp_path / "forged.json"
    forged.write_bytes(T._json(changed))
    forged.with_name(forged.name + ".sha256").write_text(T.sha256_file(forged) + "\n")
    with pytest.raises(ValueError, match="stored baseline timing record"):
        T.load_baseline_timing_record(forged)


def test_baseline_loader_refuses_the_certified_legacy_linux_record():
    path = T.PROJECT_ROOT / "runs/w4_timing/attempt-003/timing.json"
    with pytest.raises(ValueError, match="no baseline benchmarks"):
        T.load_baseline_timing_record(path)


def test_baseline_time_once_runs_one_five_member_ensemble(monkeypatch, baseline_inventory):
    case = baseline_inventory["groups"][0]["benchmark_case"]
    monkeypatch.setattr(T.C, "torch_threading", lambda: {"num_threads": 4, "num_interop_threads": 4})
    clock = iter([1.0, 3.0, 13.0])
    monkeypatch.setattr(T.time, "perf_counter", lambda: next(clock))
    calls = []
    def collect(unit, **kwargs):
        calls.append("collect")
        assert kwargs == {"stage": "pilot", "seed": 1, "arm": "baseline"}
        return "synthetic pools"
    def train(unit, pools, config, **kwargs):
        calls.append("train")
        assert pools == "synthetic pools" and config == T.C.CONFIRMATORY_TRAIN
        assert config.ensemble_size == 5 and kwargs["device"] == "cpu"
        return SimpleNamespace(members=[object()] * 5,
                               results=[SimpleNamespace(epochs_run=e) for e in range(21, 26)])
    monkeypatch.setattr(T, "collect_pools", collect)
    monkeypatch.setattr(T, "train_ensemble", train)
    assert T._time_baseline_once(case, 1) == {
        "seed": 1, "collection_s": 2.0, "training_s": 10.0, "epochs_run": [21, 22, 23, 24, 25]}
    assert calls == ["collect", "train"]


def test_baseline_worker_preserves_all_four_receipts(fast_baseline, monkeypatch, fake_baselines, tmp_path):
    row = fake_baselines[0]
    seen = []
    monkeypatch.setattr(T, "_environment", lambda **kw: fake_environment())
    def measure(case, seed):
        seen.append(seed)
        return copy.deepcopy(row["warmup"] if seed == 0 else row["repetitions"][seed - 1])
    monkeypatch.setattr(T, "_time_baseline_once", measure)
    root = tmp_path / "baseline-receipts"
    assert T._benchmark_baseline_group(row["group_id"], receipt_dir=root) == row
    assert seen == [0, 1, 2, 3] and len(list(root.glob("*.json"))) == 5


def test_baseline_launcher_uses_separate_bounded_worker(fast_baseline, monkeypatch, fake_baselines, tmp_path):
    row = fake_baselines[0]
    seen = []
    monkeypatch.setattr(T, "_environment", lambda **kw: fake_environment())
    def run(command, **kwargs):
        if command[0] == "git":
            return SimpleNamespace(returncode=0)
        seen.append((command, kwargs))
        assert "--worker-baseline-group" in command and "--worker-group" not in command
        output = Path(command[command.index("--output") + 1])
        T.write_baseline_timing_record(output, T.build_baseline_timing_record([row]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(T.subprocess, "run", run)
    output = T.run_baseline_benchmarks(tmp_path / "baseline-attempt", group_ids=[row["group_id"]],
                                       timeout_seconds=30)
    record = T.load_baseline_timing_record(output)
    assert len(record["benchmarks"]) == 1 and record["complete_scope_coverage"] is False
    assert len(seen) == 1 and seen[0][1]["timeout"] == 30


def test_baseline_cli_lists_six_without_compute(fast_baseline, monkeypatch, capsys):
    monkeypatch.setattr(T, "run_baseline_benchmarks", lambda *a, **kw: pytest.fail("list must not train"))
    assert T.main(["--baseline", "--list-cases"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 6
    with pytest.raises(SystemExit):
        T.main(["--baseline", "--list-cases", "--scope", "e1_repairs"])


def test_baseline_cli_all_cases_is_explicit_six_case_request(fast_baseline, monkeypatch, tmp_path):
    requests = []
    monkeypatch.setattr(T, "run_baseline_benchmarks", lambda path, **kw: requests.append((path, kw)))
    assert T.main(["--baseline", "--attempt", str(tmp_path / "not-run"), "--all-cases"]) == 0
    assert len(requests) == 1 and len(requests[0][1]["group_ids"]) == 6
    assert requests[0][1]["timeout_seconds"] == 1800
    assert not (tmp_path / "not-run").exists()
