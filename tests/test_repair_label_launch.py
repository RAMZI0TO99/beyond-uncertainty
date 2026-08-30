"""Adversarial synthetic tests for the production smoke launcher.

No model is trained.  Isolated attempts are replaced at the supervisor handoff
with deterministic persisted-boundary doubles; the fixed callback and exact
payload are still asserted on every one of the 60 obligations.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest
import torch

from bu.config import Arm
from bu.experiments import repair_label_finalize as Finalize
from bu.experiments import repair_label_launch as L
from bu.experiments import repair_label_preflight as PF
from bu.experiments import repair_label_run as R
from bu.experiments.fit_evidence import VerifiedFitEvidence, registered_fit_spec
from bu.experiments.supervisor import AttemptOutcome
from bu.models.uncertainty import NormalisationScale
from bu.runrecord import GitState, TRACKED_PACKAGES


COMMIT = "a" * 40


class _SyntheticFits:
    def __init__(self):
        self.entries: dict[Path, VerifiedFitEvidence] = {}
        self.attempts: list[dict] = []
        self.loads: list[tuple[Path, str | None]] = []

    def persist(self, root: Path, payload: dict) -> VerifiedFitEvidence:
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        (root / "fit_evidence.json").write_text(
            json.dumps({"fit_id": payload["fit_id"]}) + "\n", encoding="utf-8"
        )
        unit = R.registered_week6_smoke_unit()
        spec = registered_fit_spec(
            unit, arm=payload["arm"], seed=payload["seed"]
        )
        scale = L._scale_from_row(payload["normalisation"])
        if scale is None:
            scale = NormalisationScale(
                torch.tensor([1.0 + payload["seed"] / 10000, 2.0]),
                n_reference=1000,
            )
        empty = np.asarray([1.0], dtype=np.float64)
        verified = VerifiedFitEvidence(
            fit_dir=root,
            unit=unit,
            arm=payload["arm"],
            seed=payload["seed"],
            roles=spec.roles,
            execution_stage=spec.execution_stage,
            unit_id=spec.unit_id,
            config_id=spec.config_id,
            fit_id=spec.fit_id,
            execution_run_id=spec.execution_run_id,
            execution_digest=hashlib.sha256(spec.fit_id.encode()).hexdigest(),
            evaluation_pool_digest=hashlib.sha256(
                (
                    f"pool:{payload['seed']}:feature-restored"
                    if payload["arm"] == "feature_repair"
                    else f"pool:{payload['seed']}:baseline"
                ).encode()
            ).hexdigest(),
            diagnostics=MappingProxyType({}),
            error=empty,
            episode=np.asarray([0]),
            step=np.asarray([0]),
            scale=scale,
            n_train=Arm(payload["arm"]).resolve(unit).n_transitions,
            ensemble_size=5 if payload["arm"] == "baseline" else 1,
        )
        self.entries[root] = verified
        return verified

    def load(self, path, *, expected_git_commit=None):
        resolved = Path(path).resolve()
        self.loads.append((resolved, expected_git_commit))
        if not (resolved / "fit_evidence.json").is_file():
            raise ValueError("synthetic sidecar missing")
        return self.entries[resolved]


@pytest.fixture
def roots(tmp_path):
    values = {
        name: tmp_path / name
        for name in ("preflight", "output", "staging", "sync")
    }
    for path in values.values():
        path.mkdir()
    return values


@pytest.fixture
def environment(monkeypatch):
    versions = {name: f"test-{index}" for index, name in enumerate(TRACKED_PACKAGES)}

    def current():
        return GitState(COMMIT, False, "main"), versions, dict(versions)

    monkeypatch.setattr(PF.P, "_verify_environment", current)
    monkeypatch.setattr(L.P, "_verify_environment", current)
    device = lambda route: {
        "frozen_route": "cpu",
        "requested_route": route,
        "available": route == "cpu",
    }
    monkeypatch.setattr(PF.P, "_verify_device", device)
    monkeypatch.setattr(L.P, "_verify_device", device)
    return current


@pytest.fixture
def ready_report(roots, environment):
    PF.run_repair_label_preflight(
        preflight_dir=roots["preflight"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        sync_destination_identity="synthetic-mounted-destination",
        execution_route="cpu",
        minimum_free_bytes=0,
    )
    return roots["preflight"] / PF.REPAIR_LABEL_PREFLIGHT_FILE


@pytest.fixture
def synthetic_execution(monkeypatch):
    store = _SyntheticFits()

    def isolated(callback, *, root, staging_root, job_id, payload, timeout_seconds):
        assert callback is L._fit_worker
        assert Path(staging_root).is_dir()
        assert timeout_seconds == 17.0
        assert payload["expected_git_commit"] == COMMIT
        assert payload["fit_id"] == job_id
        canonical = Path(root).resolve() / R.FIT_DIRECTORY / job_id
        store.attempts.append(dict(payload))
        store.persist(canonical, payload)
        return AttemptOutcome(
            job_id=job_id,
            attempt_token=f"attempt-{len(store.attempts)}",
            status="success",
            attempt_dir=canonical,
            canonical_dir=canonical,
            exit_code=0,
            published=True,
        )

    def build_label(conditions, *, path):
        rows = tuple(conditions)
        assert len(rows) == 20
        Path(path).write_text('{"synthetic":"label"}\n', encoding="utf-8")
        return {"synthetic": "label"}

    def write_counts(paths, *, path):
        assert len(tuple(paths)) == 1
        counts = {
            "label_count_schema_version": 1,
            "attempted": 1,
            "observed_0": 1,
            "observed_1": 0,
            "ambiguous": 0,
            "undiagnosed": 0,
            "count_digest": "b" * 64,
        }
        Path(path).write_text(json.dumps(counts) + "\n", encoding="utf-8")
        return counts

    monkeypatch.setattr(L, "run_isolated_attempt", isolated)
    monkeypatch.setattr(L, "load_fit_evidence", store.load)
    monkeypatch.setattr(R, "load_fit_evidence", store.load)
    monkeypatch.setattr(R, "build_label_evidence", build_label)
    monkeypatch.setattr(R, "write_label_evidence_counts", write_counts)
    return store


def _launch(ready_report, roots):
    return L.launch_repair_label_smoke(
        preflight_report=ready_report,
        output_root=roots["output"],
        sync_root=roots["sync"],
        attempt_timeout_seconds=17,
    )


def test_only_private_correction_validation_accepts_a_clean_new_commit(
    ready_report, roots, environment, monkeypatch
):
    _old_state, versions, pins = environment()

    def corrected_environment():
        return GitState("d" * 40, False, "main"), versions, pins

    monkeypatch.setattr(L.P, "_verify_environment", corrected_environment)
    with pytest.raises(ValueError, match="current clean pinned environment"):
        L.validate_repair_label_preflight(
            ready_report,
            output_root=roots["output"],
            sync_root=roots["sync"],
        )

    validated = L._validate_repair_label_preflight(
        ready_report,
        output_root=roots["output"],
        sync_root=roots["sync"],
        require_current_commit=False,
    )
    assert validated.git_commit == COMMIT


def test_project_finalizer_validates_historical_sync_strictly_read_only(
    ready_report, roots, environment, monkeypatch
):
    _old_state, versions, pins = environment()
    before = {
        path.relative_to(roots["sync"]): (
            path.stat().st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in roots["sync"].rglob("*")
        if path.is_file()
    }

    def corrected_environment():
        return GitState("d" * 40, False, "main"), versions, pins

    monkeypatch.setattr(Finalize.P, "_verify_environment", corrected_environment)
    validated = Finalize._validate_original_preflight_read_only(
        ready_report, output_root=roots["output"]
    )
    after = {
        path.relative_to(roots["sync"]): (
            path.stat().st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in roots["sync"].rglob("*")
        if path.is_file()
    }
    assert validated.git_commit == COMMIT
    assert after == before


def test_launch_executes_exact_order_binds_commit_syncs_each_and_counts_only(
    ready_report, roots, synthetic_execution
):
    report = _launch(ready_report, roots)

    assert [(row["seed"], row["arm"]) for row in synthetic_execution.attempts] == [
        (seed, arm)
        for seed in range(1000, 1020)
        for arm in ("baseline", "data_repair", "feature_repair")
    ]
    assert report["fit_count"] == 60
    assert report["executed_fits"] == 60
    assert report["resumed_fits"] == 0
    assert report["synced_fits"] == 60
    assert report["preflight"]["git_commit"] == COMMIT
    assert all(commit == COMMIT for _, commit in synthetic_execution.loads)
    # 60 parent post-attempt loads plus 60 independent finalization reloads.
    assert len(synthetic_execution.loads) == 120
    forbidden = {
        "excluded",
        "exclusion_rate",
        "registered_planning_exclusion_rate",
        "planning_assumption_missed",
    }
    assert forbidden.isdisjoint(report["counts"]["values"])
    sync_dir = roots["sync"] / PF.REPAIR_LABEL_SYNC_DIRECTORY
    assert len(list((sync_dir / R.FIT_DIRECTORY).iterdir())) == 60
    assert (sync_dir / "label_evidence.json").is_file()
    assert (sync_dir / "label_counts.json").is_file()


def test_launch_resume_reopens_and_resyncs_without_new_attempts(
    ready_report, roots, synthetic_execution
):
    first = _launch(ready_report, roots)
    synthetic_execution.attempts.clear()
    synthetic_execution.loads.clear()

    second = _launch(ready_report, roots)

    assert synthetic_execution.attempts == []
    assert second["executed_fits"] == 0
    assert second["resumed_fits"] == 60
    assert second["synced_fits"] == 60
    assert len(synthetic_execution.loads) == 120
    assert second["launch_id"] != first["launch_id"]


def test_partial_published_fit_refuses_before_attempt(
    ready_report, roots, synthetic_execution
):
    _, _, planned = R._registered_plan(
        R.registered_week6_smoke_unit(), roots["output"].resolve()
    )
    planned[0].path.mkdir(parents=True)
    (planned[0].path / "partial.txt").write_text("partial\n", encoding="utf-8")
    with pytest.raises(ValueError, match="partial, divergent"):
        _launch(ready_report, roots)
    assert synthetic_execution.attempts == []


def test_timeout_is_preserved_and_label_is_not_finalized(
    ready_report, roots, synthetic_execution, monkeypatch
):
    def timeout(callback, *, root, staging_root, job_id, payload, timeout_seconds):
        del callback, root, staging_root, payload, timeout_seconds
        attempt = roots["staging"] / "quarantine" / job_id
        attempt.mkdir(parents=True)
        return AttemptOutcome(
            job_id=job_id,
            attempt_token="timeout",
            status="timeout",
            attempt_dir=attempt,
            canonical_dir=None,
            exit_code=-15,
            error_type="TimeoutError",
            error="synthetic timeout",
        )

    monkeypatch.setattr(L, "run_isolated_attempt", timeout)
    with pytest.raises(ValueError, match="status='timeout'"):
        _launch(ready_report, roots)
    assert not (roots["output"] / "label_evidence.json").exists()
    assert not (roots["output"] / "label_counts.json").exists()


def test_launch_rejects_environment_commit_change_before_attempt(
    ready_report, roots, synthetic_execution, monkeypatch
):
    versions = {name: "changed" for name in TRACKED_PACKAGES}
    monkeypatch.setattr(
        L.P,
        "_verify_environment",
        lambda: (GitState("c" * 40, False, "main"), versions, dict(versions)),
    )
    with pytest.raises(ValueError, match="current clean pinned environment"):
        _launch(ready_report, roots)
    assert synthetic_execution.attempts == []


def test_launch_refuses_a_tampered_preflight_canary_before_attempt(
    ready_report, roots, synthetic_execution
):
    document = json.loads(Path(ready_report).read_text(encoding="utf-8"))
    document["sync_canary"]["sha256"] = "0" * 64
    Path(ready_report).write_text(json.dumps(document) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="sync canary"):
        _launch(ready_report, roots)

    assert synthetic_execution.attempts == []


def test_worker_forwards_exact_commit_to_fit_before_any_result_load(monkeypatch, tmp_path):
    unit = R.registered_week6_smoke_unit()
    spec = registered_fit_spec(unit, arm="baseline", seed=1000)
    calls = []

    def refuse_before_pool(*args, **kwargs):
        calls.append(kwargs["expected_git_commit"])
        raise ValueError("synthetic commit mismatch before pool")

    monkeypatch.setattr(L, "run_confirmatory_fit", refuse_before_pool)
    payload = {
        "worker_schema_version": 1,
        "unit_id": R.WEEK6_SMOKE_UNIT_ID,
        "seed": 1000,
        "arm": "baseline",
        "fit_id": spec.fit_id,
        "expected_git_commit": COMMIT,
        "normalisation": None,
    }
    with pytest.raises(ValueError, match="before pool"):
        L._fit_worker(tmp_path / "attempt", payload)
    assert calls == [COMMIT]


def test_torn_existing_sync_tree_is_refused_not_overwritten(
    ready_report, roots, synthetic_execution
):
    _, _, planned = R._registered_plan(
        R.registered_week6_smoke_unit(), roots["output"].resolve()
    )
    torn = (
        roots["sync"]
        / PF.REPAIR_LABEL_SYNC_DIRECTORY
        / R.FIT_DIRECTORY
        / planned[0].spec.fit_id
    )
    torn.mkdir(parents=True)
    (torn / "partial.txt").write_text("torn\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from the complete source tree"):
        _launch(ready_report, roots)
    assert (torn / "partial.txt").read_text(encoding="utf-8") == "torn\n"


def test_sync_tree_refuses_source_hardlinks_and_source_destination_alias(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    first = source / "first.bin"
    first.write_bytes(b"evidence")
    second = source / "second.bin"
    os.link(first, second)
    with pytest.raises(ValueError, match="hard-linked alias"):
        L._sync_tree(source, tmp_path / "copy")

    second.unlink()
    with pytest.raises(ValueError, match="aliases its source"):
        L._sync_tree(source, source)


def test_public_launch_cli_has_mandatory_timeout_and_no_executor_or_science_axes():
    parser = L.build_parser()
    actions = {action.dest: action for action in parser._actions}
    assert actions["attempt_timeout_seconds"].required is True
    assert {
        "unit",
        "unit_id",
        "seed",
        "seeds",
        "arm",
        "executor",
        "device",
        "stale_lease_after_seconds",
    }.isdisjoint(actions)
