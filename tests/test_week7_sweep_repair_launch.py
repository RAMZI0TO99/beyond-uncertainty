"""Synthetic six-repair orchestration only; no production collection/training.

The registered first unit, RP contract derivation, immutable file IO, leases,
event histories, timing reader and copy verification are real. Scientific
baseline/repair readers and the isolated process are explicit fixture doubles.
Those scientific readers and real process cleanup have their separate suites.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import platform
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from bu.config import Arm, Config
from bu.durable import atomic_write_json, read_json, sha256_file
from bu.models.uncertainty import NormalisationScale
from bu.experiments import week7_sweep_repair_launch as S
from bu.experiments import supervisor as V
from test_repair_timing import fake_benchmark


COMMIT = "d" * 40
BASE_COMMIT = "b" * 40
TIMING_COMMIT = "a" * 40


@pytest.fixture(autouse=True)
def no_training(monkeypatch):
    def prohibited(*args, **kwargs):
        pytest.fail("launcher tests must never invoke actual collection/training")
    for module, name in ((S.E, "train_ensemble"), (S.RT, "train_ensemble"),
                         (S.RP, "collect_anchored_repair_pools")):
        monkeypatch.setattr(module, name, prohibited)


def test_exact_registered_first_unit_three_baselines_and_six_obligations():
    jobs = S._first_baselines()
    assert [j.job_id for j in jobs] == [f"cc428cf4ab47-s{s}" for s in (1000, 1001, 1002)]
    unit = jobs[0].unit
    assert Config(unit=unit).unit_id == "0184fbfcd8b9"
    assert (unit.family, unit.hidden_size, unit.n_transitions) == ("capacity", 64, 5000)
    specs = [S.RP.registered_sweep_repair_spec(unit, arm=a, seed=s)
             for s in S.SEEDS for a in S.ARMS]
    assert len({s.fit_id for s in specs}) == 6
    assert all(s.roles == ("exp3_repairs",) for s in specs)


class SizedPool:
    def __init__(self, unit, seed, size):
        self.unit, self.seed, self.size = unit, seed, size
    def __len__(self):
        return self.size


@pytest.fixture
def setup(tmp_path, monkeypatch):
    jobs = S._first_baselines()
    inventory = S.RT.repair_inventory("all_repairs")
    # Cache source-derived metadata only, never outputs or evidence verification.
    monkeypatch.setattr(S, "_first_baselines", lambda: jobs)
    original_inventory = S.RT.repair_inventory
    monkeypatch.setattr(S.RT, "repair_inventory", lambda scope="all_repairs":
                        copy.deepcopy(inventory) if scope == "all_repairs" else original_inventory(scope))
    monkeypatch.setattr(S.W, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(S.W, "COMMON_LEASE_ROOT", tmp_path / "control")
    for name in ("control", "output", "staging", "sync", "originals", "copies", "timing"):
        (tmp_path / name).mkdir()
    calls = {"baseline_reads": [], "anchor_reads": [], "repair_reads": [], "fits": [], "supervisor": []}
    scale = NormalisationScale(torch.tensor([.2, .3]), 800)
    baselines = []
    for job in jobs:
        source = tmp_path / "originals" / job.job_id
        target = tmp_path / "copies" / job.job_id
        source.mkdir()
        digest = hashlib.sha256(f"synthetic baseline {job.seed}".encode()).hexdigest()
        anchor_digest = hashlib.sha256(f"synthetic anchor {job.seed}".encode()).hexdigest()
        doc = {"synthetic_only": True, "seed": job.seed, "unit_id": job.config.unit_id,
               "commit": BASE_COMMIT, "execution_digest": digest, "anchor_sha256": anchor_digest}
        atomic_write_json(source / "synthetic_baseline.json", doc)
        shutil.copytree(source, target)
        baselines.append(S.BaselineSource(job.seed, source, target, BASE_COMMIT, digest, anchor_digest))
    def baseline_loader(path, *, expected_git_commit=None):
        path = Path(path)
        row = read_json(path / "synthetic_baseline.json")
        if row["commit"] != expected_git_commit:
            raise ValueError("synthetic independently expected baseline commit mismatch")
        job = next(j for j in jobs if j.seed == row["seed"])
        calls["baseline_reads"].append(path)
        return S.F.VerifiedFitEvidence(path, job.unit, "baseline", job.seed, ("config_sweep",),
            "config_sweep", row["unit_id"], job.config.config_id, job.job_id, job.config.run_id,
            row["execution_digest"], "e" * 64, {}, np.zeros(1), np.zeros(1), np.zeros(1),
            scale, job.unit.n_transitions, 5)
    def anchor_loader(path, *, expected_git_commit):
        fit = baseline_loader(path, expected_git_commit=expected_git_commit)
        row = read_json(Path(path) / "synthetic_baseline.json")
        calls["anchor_reads"].append(Path(path))
        return SimpleNamespace(anchor_sha256=row["anchor_sha256"], source_commit=expected_git_commit,
            scale=scale, pools=SimpleNamespace(train=SizedPool(fit.unit, fit.seed, 5000),
                validation=SizedPool(fit.unit, fit.seed, 400), evaluation=SizedPool(fit.unit, fit.seed, 1000)))
    monkeypatch.setattr(S.F, "load_fit_evidence", baseline_loader)
    monkeypatch.setattr(S.F, "validate_sweep_pool_anchors", anchor_loader)
    def environment(commit):
        if commit != COMMIT:
            raise ValueError("synthetic current clean Git commit mismatch")
        return {"git_commit": COMMIT, "source_commit": COMMIT, "device": "cpu",
                "threading": {"num_threads": 4, "num_interop_threads": 4}, "source_tree_clean": True}
    monkeypatch.setattr(S, "_environment", environment)
    needed = {S.RT._digest({"architecture": S.RT._architecture(Arm(a).resolve(jobs[0].unit)),
                          "n_transitions": Arm(a).resolve(jobs[0].unit).n_transitions}) for a in S.ARMS}
    rows = [fake_benchmark(g, inventory) for g in inventory["groups"] if g["group_id"] in needed]
    host = {"platform": platform.platform(), "processor": platform.processor() or platform.machine(),
            "python": platform.python_version(), "machine": platform.machine(),
            "hostname": platform.node(), "logical_cpu_count": os.cpu_count()}
    for row in rows:
        for key in ("environment_before", "environment_after"):
            row[key].update(host)
    timing_path = tmp_path / "timing" / "timing.json"
    S.RT.write_timing_record(timing_path, S.RT.build_timing_record(rows, scope="all_repairs"))
    timing = S.TimingPin(timing_path, sha256_file(timing_path), TIMING_COMMIT)
    kwargs = dict(baselines=tuple(baselines), timing=timing, expected_git_commit=COMMIT,
        output_root=tmp_path / "output", staging_root=tmp_path / "staging", sync_root=tmp_path / "sync",
        attempt_timeout_seconds=17.0, minimum_free_bytes=1, sync_destination_identity="synthetic-mounted-copy")

    def paired_loader(path, **expected):
        path = Path(path)
        calls["repair_reads"].append(path)
        row = read_json(path / "synthetic_paired.json")
        if expected["expected_git_commit"] != row["commit"]:
            raise ValueError("synthetic independently expected repair commit mismatch")
        contract = S.RP.registered_sweep_pairing(expected["unit"], arm=expected["arm"], seed=expected["seed"],
            **{k: expected[k] for k in ("baseline_source", "expected_baseline_commit", "expected_baseline_execution_digest")})
        if row["contract_sha256"] != contract.contract_sha256:
            raise ValueError("synthetic paired contract changed")
        return S.E.VerifiedPairedRepair(path, contract.unit, contract.arm, contract.seed,
            contract.physical_fit_id, contract.physical_run_id, contract.obligation_fit_id,
            contract.obligation_run_id, S.E._config(contract).config_id, row["execution_digest"],
            contract, {}, scale, Arm(contract.arm).resolve(contract.unit).n_transitions)
    def paired_runner(*, out_dir, **expected):
        path = Path(out_dir)
        contract = S.RP.registered_sweep_pairing(expected["unit"], arm=expected["arm"], seed=expected["seed"],
            **{k: expected[k] for k in ("baseline_source", "expected_baseline_commit", "expected_baseline_execution_digest")})
        calls["fits"].append(contract.physical_fit_id)
        atomic_write_json(path / "synthetic_paired.json", {"synthetic_only": True,
            "commit": expected["expected_git_commit"], "contract_sha256": contract.contract_sha256,
            "execution_digest": hashlib.sha256(contract.canonical_json + b"synthetic execution").hexdigest()})
        return paired_loader(path, **expected)
    monkeypatch.setattr(S.E, "load_paired_repair_evidence", paired_loader)
    monkeypatch.setattr(S.E, "run_paired_repair", paired_runner)

    def isolated(callback, *, root, staging_root, job_id, payload, timeout_seconds):
        assert callback is S._fit_worker and timeout_seconds == 17.
        calls["supervisor"].append(job_id)
        token = hashlib.sha256(job_id.encode()).hexdigest()[:32]
        attempt = Path(staging_root) / "staging" / f"{job_id}.{token}"
        attempt.mkdir(parents=True)
        stamp = V._utc_now()
        parent_pid = os.getpid()
        envelope = dict(schema_version=V.SUPERVISOR_SCHEMA_VERSION, job_id=job_id,
                        attempt_token=token, parent_pid=parent_pid, started_at=stamp, timeout_seconds=17.)
        atomic_write_json(attempt / V.ATTEMPT_FILE, envelope)
        # Simulate the child boundary only; the fixed production callback itself
        # runs, reopening the real start/context/events/source-copy metadata.
        proxy = SimpleNamespace(path=os.path, getpid=lambda: parent_pid + 100000, cpu_count=os.cpu_count)
        with monkeypatch.context() as child:
            child.setattr(S, "os", proxy)
            result = callback(attempt, payload)
        atomic_write_json(attempt / V.RESULT_FILE, result)
        atomic_write_json(attempt / V.RECEIPT_FILE, dict(envelope, status="success", child_pid=parent_pid + 100000,
            finished_at=V._utc_now(), elapsed_seconds=.1, exit_code=0, error_type=None, error=None,
            result_digest=S.B._result_digest(result), job_tree_digest=V._job_tree_digest(attempt), published=True))
        destination = Path(root) / "jobs" / job_id
        destination.parent.mkdir(exist_ok=True)
        attempt.rename(destination)
        return V.AttemptOutcome(job_id, token, "success", destination, destination, 0, published=True)
    monkeypatch.setattr(S, "run_isolated_attempt", isolated)
    return SimpleNamespace(root=tmp_path, kwargs=kwargs, calls=calls, timing_rows=rows,
                           inventory=inventory, isolated=isolated)


def test_preparation_exact_six_jobs_and_relevant_positive_group_timings(setup):
    ctx = S.prepare_first_sweep_repairs(**setup.kwargs)
    assert len(ctx["jobs"]) == 6
    assert all(j["physical_fit_id"].startswith("ps1-") for j in ctx["jobs"])
    assert all(j["physical_fit_id"] != j["obligation_fit_id"] for j in ctx["jobs"])
    assert {j["config"]["seed"] for j in ctx["jobs"]} == {1000, 1001, 1002}
    assert {j["config"]["arm"]["kind"] for j in ctx["jobs"]} == set(S.ARMS)
    assert ctx["budget"]["total_s"] == 198.
    assert len(ctx["budget"]["contributions"]) == 2
    assert [c["model_fits"] for c in ctx["budget"]["contributions"]] == [3, 3]
    assert all(c["training_s"] > 0 and c["collection_s"] > 0 for c in ctx["budget"]["contributions"])
    assert not list((setup.root / "output").iterdir())
    assert setup.calls["fits"] == []


def test_all_six_fixed_workers_then_new_lease_resumes_without_retraining(setup):
    first = S.launch_first_sweep_repairs(**setup.kwargs)
    assert first["status"] == "complete"
    assert first["counts"] == dict(executed=6, resumed=0, synced=6, total=6)
    assert len(setup.calls["fits"]) == 6
    context = read_json(setup.root / "output" / S.CONTEXT_FILE)
    original_results = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                        for p in (setup.root / "output" / "jobs").rglob("job_result.json")}
    second = S.launch_first_sweep_repairs(**setup.kwargs)
    assert second["counts"] == dict(executed=0, resumed=6, synced=6, total=6)
    assert len(setup.calls["fits"]) == 6
    assert first["execution_context_digest"] == second["execution_context_digest"]
    assert first["released_lease"]["token"] != second["released_lease"]["token"]
    assert original_results == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in original_results}
    assert len(S._load_events(context)) == 13
    assert Path(first["released_lease"]["history_path"]).is_file()
    assert not (S.W.COMMON_LEASE_ROOT / "leases" / f"{S.W.COMMON_LEASE_NAME}.lease.json").exists()


def test_sync_failure_only_copies_completed_fit_under_new_lease(setup, monkeypatch):
    publish = S.B._publish_job_tree
    monkeypatch.setattr(S.B, "_publish_job_tree", lambda *a: (_ for _ in ()).throw(ValueError("synthetic copy interruption")))
    with pytest.raises(ValueError, match="copy interruption"):
        S.launch_first_sweep_repairs(**setup.kwargs)
    assert len(setup.calls["fits"]) == 1
    result = next((setup.root / "output" / "jobs").rglob("job_result.json"))
    before = result.read_bytes(), result.stat().st_mtime_ns
    monkeypatch.setattr(S.B, "_publish_job_tree", publish)
    report = S.launch_first_sweep_repairs(**setup.kwargs)
    assert report["counts"] == dict(executed=5, resumed=1, synced=6, total=6)
    assert len(setup.calls["fits"]) == 6
    assert (result.read_bytes(), result.stat().st_mtime_ns) == before


@pytest.mark.parametrize("error", [RuntimeError("synthetic failed child"), KeyboardInterrupt("synthetic stopped child")])
def test_failed_or_interrupted_attempt_is_truthfully_preserved_and_never_retried(setup, monkeypatch, error):
    stopped = []
    def interrupted(*args, **kwargs):
        # Central supervisor owns real termination; emulate its contract that
        # propagation happens only after child termination has finished.
        stopped.append(True)
        raise error
    monkeypatch.setattr(S, "run_isolated_attempt", interrupted)
    with pytest.raises(type(error)):
        S.launch_first_sweep_repairs(**setup.kwargs)
    assert stopped == [True]
    report = read_json(next((setup.root / "output" / S.REPORT_DIRECTORY).glob("*.json")))
    assert report["failure"]["type"] == type(error).__name__
    assert report["status"] == "incomplete"
    monkeypatch.setattr(S, "run_isolated_attempt", setup.isolated)
    with pytest.raises(ValueError, match="prior failed"):
        S.launch_first_sweep_repairs(**setup.kwargs)
    assert setup.calls["fits"] == []


@pytest.mark.parametrize("field,value", [("attempt_timeout_seconds", None), ("attempt_timeout_seconds", 0),
    ("attempt_timeout_seconds", True), ("attempt_timeout_seconds", float("inf")),
    ("minimum_free_bytes", 0), ("minimum_free_bytes", True),
    ("expected_git_commit", "c" * 40), ("sync_destination_identity", " ")])
def test_bad_launch_parameters_refuse_before_any_attempt(setup, field, value):
    with pytest.raises(ValueError):
        S.launch_first_sweep_repairs(**{**setup.kwargs, field: value})
    assert setup.calls["fits"] == []


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra_seed", "boolean", "list", "wrong_type"])
def test_baseline_inventory_cannot_be_changed(setup, mutation):
    sources = setup.kwargs["baselines"]
    changed = {"missing": sources[:2], "duplicate": (sources[0], sources[0], sources[2]),
        "extra_seed": (sources[0], sources[1], replace(sources[2], seed=1003)),
        "boolean": (replace(sources[0], seed=True), *sources[1:]),
        "list": list(sources), "wrong_type": (None, *sources[1:])}[mutation]
    with pytest.raises(ValueError):
        S.prepare_first_sweep_repairs(**{**setup.kwargs, "baselines": changed})
    assert setup.calls["fits"] == []


@pytest.mark.parametrize("field,value", [("expected_git_commit", "c" * 40),
    ("expected_execution_digest", "c" * 64), ("expected_anchor_sha256", "c" * 64)])
def test_independent_source_pins_cannot_be_self_attested(setup, field, value):
    sources = setup.kwargs["baselines"]
    with pytest.raises(ValueError):
        S.prepare_first_sweep_repairs(**{**setup.kwargs,
            "baselines": (replace(sources[0], **{field: value}), *sources[1:])})


def test_alias_source_copy_and_changed_durable_bytes_refuse(setup):
    sources = setup.kwargs["baselines"]
    with pytest.raises(ValueError, match="separate"):
        S.prepare_first_sweep_repairs(**{**setup.kwargs,
            "baselines": (replace(sources[0], copy_path=sources[0].source_path), *sources[1:])})
    (Path(sources[0].copy_path) / "synthetic_baseline.json").write_bytes(b"changed durable bytes")
    with pytest.raises(ValueError):
        S.prepare_first_sweep_repairs(**setup.kwargs)


@pytest.mark.parametrize("kind", ["missing_group", "wrong_scope", "wrong_commit", "wrong_host", "wrong_sha"])
def test_timing_requires_exact_relevant_groups_and_host_pins(setup, kind):
    rows = copy.deepcopy(setup.timing_rows)
    path = setup.root / "timing" / "alternative.json"
    scope = "all_repairs"
    if kind == "missing_group":
        rows.pop()
    if kind == "wrong_host":
        for row in rows:
            for key in ("environment_before", "environment_after"):
                row[key]["hostname"] = "different host"
    if kind == "wrong_scope":
        scope = "e1_repairs"
    S.RT.write_timing_record(path, S.RT.build_timing_record(rows, scope=scope))
    pin = S.TimingPin(path, "0" * 64 if kind == "wrong_sha" else sha256_file(path),
                      "c" * 40 if kind == "wrong_commit" else TIMING_COMMIT)
    with pytest.raises(ValueError):
        S.prepare_first_sweep_repairs(**{**setup.kwargs, "timing": pin})


@pytest.mark.parametrize("left,right", [("output_root", "sync_root"), ("staging_root", "output_root")])
def test_overlap_execution_roots_refused(setup, left, right):
    with pytest.raises(ValueError, match="overlap"):
        S.prepare_first_sweep_repairs(**{**setup.kwargs, left: setup.kwargs[right]})


def test_protected_baseline_and_common_lease_root_refused(setup):
    for path in (setup.kwargs["baselines"][0].source_path, S.W.COMMON_LEASE_ROOT):
        with pytest.raises(ValueError, match="overlap"):
            S.prepare_first_sweep_repairs(**{**setup.kwargs, "output_root": path})


def test_common_lease_conflict_never_launches_or_releases_other_owner(setup):
    lease = V.acquire_batch_lease(S.W.COMMON_LEASE_ROOT, lease_name=S.W.COMMON_LEASE_NAME)
    try:
        with pytest.raises(V.LeaseConflictError):
            S.launch_first_sweep_repairs(**setup.kwargs)
        assert read_json(lease.path)["token"] == lease.token
        assert setup.calls["fits"] == []
    finally:
        lease.release()


@pytest.mark.parametrize("where", ["staging", "quarantine", "durable_only", "unknown_job"])
def test_unknown_and_partial_attempts_do_not_retrain(setup, where):
    ctx = S.prepare_first_sweep_repairs(**setup.kwargs)
    job = S._job(ctx, ctx["jobs"][0]["physical_fit_id"])
    path = (setup.root / "staging" / where / f"{job.job_id}.{'f' * 32}" if where in {"staging", "quarantine"}
            else setup.root / "sync" / "jobs" / (job.job_id if where == "durable_only" else "unknown"))
    path.mkdir(parents=True)
    with pytest.raises(ValueError, match="prior|unknown|retrain"):
        S.launch_first_sweep_repairs(**setup.kwargs)
    assert setup.calls["fits"] == []


def test_recovery_preserves_durable_only_event_tail_but_refuses_divergence(setup):
    S.launch_first_sweep_repairs(**setup.kwargs)
    context = read_json(setup.root / "output" / S.CONTEXT_FILE)
    local = setup.root / "output" / S.EVENT_DIRECTORY / "000012.json"
    before = local.read_bytes()
    local.unlink()
    assert len(S._load_events(context)) == 13 and local.read_bytes() == before
    local.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        S._load_events(context)


@pytest.mark.parametrize("artifact", ["job_result.json", "attempt_receipt.json", "attempt.json", "synthetic_paired.json"])
def test_completed_local_corruption_never_becomes_new_training(setup, artifact):
    S.launch_first_sweep_repairs(**setup.kwargs)
    path = next((setup.root / "output" / "jobs").glob(f"*/{artifact}"))
    path.write_bytes(b"{}")
    with pytest.raises((ValueError, KeyError)):
        S.launch_first_sweep_repairs(**setup.kwargs)
    assert len(setup.calls["fits"]) == 6


def test_stable_context_cannot_adopt_other_timeout_or_source_paths(setup):
    S.launch_first_sweep_repairs(**setup.kwargs)
    with pytest.raises(ValueError, match="different content"):
        S.launch_first_sweep_repairs(**{**setup.kwargs, "attempt_timeout_seconds": 18.})
    assert len(setup.calls["fits"]) == 6


def test_public_surface_has_no_executor_contract_or_bypass_knob(setup):
    parameters = inspect.signature(S.launch_first_sweep_repairs).parameters
    assert set(parameters) == {"baselines", "timing", "expected_git_commit", "output_root", "staging_root",
        "sync_root", "attempt_timeout_seconds", "minimum_free_bytes", "sync_destination_identity"}
    for key in ("executor", "jobs", "contracts", "seed", "require_fit_evidence", "skip_pairing"):
        with pytest.raises(TypeError):
            S.launch_first_sweep_repairs(**setup.kwargs, **{key: None})


def test_raw_windows_reparse_ancestor_is_rejected_before_resolution(setup, monkeypatch):
    ancestor = setup.root / "originals"
    real_lstat = Path.lstat
    def lstat(path):
        result = real_lstat(path)
        if path == ancestor:
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
        return result
    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ValueError, match="link/reparse"):
        S.prepare_first_sweep_repairs(**setup.kwargs)
    assert setup.calls["fits"] == []


@pytest.mark.parametrize("relative", [S.START_DIRECTORY, S.EVENT_DIRECTORY, S.REPORT_DIRECTORY])
def test_raw_control_write_reparse_parent_refused_before_any_write(setup, monkeypatch, relative):
    roots = {name: setup.root / name for name in ("output", "sync")}
    ancestor = roots["sync"] / relative
    ancestor.mkdir()
    real_lstat = Path.lstat
    def lstat(path):
        result = real_lstat(path)
        return (SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
                if path == ancestor else result)
    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ValueError, match="link/reparse"):
        S._twins(roots, Path(relative) / "test.json", {"synthetic_only": True})
    assert list(ancestor.iterdir()) == []
    assert not (roots["output"] / relative).exists()


def test_unconfirmed_supervisor_cleanup_retains_lease_and_writes_failure_report(setup, monkeypatch):
    # Exercise the real central lease guard without starting a process. The
    # sentinel is parent-local unknown-worker state, not an age-based lease.
    sentinel = object()
    def uncertain(*args, **kwargs):
        V._WORKERS_REQUIRING_REAP.add(sentinel)
        raise KeyboardInterrupt("synthetic worker cleanup unconfirmed")
    monkeypatch.setattr(S, "run_isolated_attempt", uncertain)
    try:
        with pytest.raises(V.LeaseConflictError, match="cleanup is incomplete"):
            S.launch_first_sweep_repairs(**setup.kwargs)
        report = read_json(next((setup.root / "output" / S.REPORT_DIRECTORY).glob("*.json")))
        assert report["status"] == "incomplete"
        assert report["failure"]["type"] == "KeyboardInterrupt"
        assert report["released_lease"] is None
        detail = report["lease_release_failure"]
        assert detail["automatic_recovery_allowed"] is False
        assert read_json(Path(detail["active_path"]))["token"] == detail["token"]
        assert setup.calls["fits"] == []
    finally:
        V._WORKERS_REQUIRING_REAP.discard(sentinel)


def test_successful_job_cannot_adopt_a_different_genuine_start(setup):
    S.launch_first_sweep_repairs(**setup.kwargs)
    S.launch_first_sweep_repairs(**setup.kwargs)
    context = read_json(setup.root / "output" / S.CONTEXT_FILE)
    job = S._job(context, context["jobs"][0]["physical_fit_id"])
    original = read_json(setup.root / "output" / "jobs" / job.job_id / V.RESULT_FILE)["start_digest"]
    other = next(read_json(p)["start_digest"] for p in (setup.root / "output" / S.START_DIRECTORY).glob("*.json")
                 if read_json(p)["start_digest"] != original)
    with pytest.raises(ValueError, match="actual prior start"):
        S._completed(context, job, start_digest=other)
    assert len(setup.calls["fits"]) == 6


def test_complete_local_fit_does_not_hide_a_prior_unknown_attempt(setup):
    S.launch_first_sweep_repairs(**setup.kwargs)
    context = read_json(setup.root / "output" / S.CONTEXT_FILE)
    job_id = context["jobs"][0]["physical_fit_id"]
    (setup.root / "staging" / "quarantine" / f"{job_id}.{'f' * 32}").mkdir(parents=True)
    with pytest.raises(ValueError, match="prior/unknown"):
        S.launch_first_sweep_repairs(**setup.kwargs)
    assert len(setup.calls["fits"]) == 6
