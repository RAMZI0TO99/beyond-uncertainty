"""Production Experiment-1 launch-boundary tests; no real fit is executed."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_bytes, read_json
from bu.experiments import batch as B
from bu.experiments import launch as L
from bu.experiments import preflight as P
from bu.experiments.supervisor import LeaseConflictError
from bu.runrecord import GitState


@pytest.fixture(scope="module")
def registered_jobs():
    """Cache the exact plan; enumerating it is deterministic and read-only."""

    return B.experiment_1_jobs()


@pytest.fixture
def roots(tmp_path):
    """Four physically separate synthetic roots required by preflight."""

    values = {
        name: tmp_path / name
        for name in ("preflight", "output", "staging", "sync")
    }
    for path in values.values():
        path.mkdir()
    return values


@pytest.fixture(autouse=True)
def green_host(monkeypatch):
    """Freeze a clean current host without changing production validation."""

    pins = P._pinned_package_versions()
    monkeypatch.setattr(
        P, "git_state", lambda: GitState(commit="a" * 40, dirty=False, branch="main")
    )
    monkeypatch.setattr(P, "package_versions", lambda: dict(pins))
    monkeypatch.setattr(P, "_device_available", lambda route: route == "cpu")
    monkeypatch.setattr(
        P.shutil, "disk_usage", lambda path: SimpleNamespace(free=10_000_000)
    )


@pytest.fixture(autouse=True)
def forbid_real_batch(monkeypatch):
    """Make every test explicitly replace the fit-launching boundary."""

    def forbidden(*args, **kwargs):
        raise AssertionError("test reached the real run_batch boundary")

    monkeypatch.setattr(B, "_run_registered_batch", forbidden)


def verified_sync(source: Path, destination: Path, identity: str):
    """Synthetic mounted-directory canary adapter with byte evidence."""

    data = source.read_bytes()
    atomic_write_bytes(destination, data)
    return P.SyncCanaryReceipt(
        schema_version=P.SYNC_RECEIPT_SCHEMA_VERSION,
        destination_identity=identity,
        destination_path=str(destination.resolve()),
        sha256=P.sha256_bytes(data),
        size_bytes=len(data),
    )


def ready_preflight(roots):
    """Create genuine immutable preflight evidence with synthetic roots."""

    report = P.run_experiment_1_preflight(
        preflight_dir=roots["preflight"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        sync_destination_identity="synthetic-mounted-store",
        sync_canary=verified_sync,
        execution_route="cpu",
        minimum_free_bytes=0,
    )
    return roots["preflight"] / P.PREFLIGHT_REPORT_FILE, report


def complete_batch(jobs) -> B.BatchReport:
    """Return a fully accounted synthetic report for the supplied exact plan."""

    return B.BatchReport(
        batch_id=B._manifest(jobs)["batch_id"],
        total=len(jobs),
        executed=len(jobs),
        resumed=0,
        synced=len(jobs),
        failed=0,
        sync_failed=0,
    )


def rewrite_report(path: Path, change) -> None:
    """Canonically rewrite synthetic evidence to exercise semantic refusal."""

    value = read_json(path)
    change(value)
    path.write_bytes(
        (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                allow_nan=False,
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def install_complete_batch(monkeypatch, calls):
    """Install a recording fake that proves no production executor is passed."""

    def fake(jobs, **kwargs):
        calls.append((tuple(jobs), dict(kwargs)))
        return complete_batch(tuple(jobs))

    monkeypatch.setattr(B, "_run_registered_batch", fake)


def test_launch_uses_exact_plan_default_executor_spawn_timeout_and_mounted_sync(
    monkeypatch, roots, registered_jobs
):
    report_path, preflight = ready_preflight(roots)
    calls = []
    install_complete_batch(monkeypatch, calls)
    sync_calls = []
    sentinel_sync = object()

    def mounted(destination):
        sync_calls.append(Path(destination))
        return sentinel_sync

    monkeypatch.setattr(B, "sync_to_directory", mounted)

    report = L.launch_experiment_1(
        preflight_report=report_path,
        output_root=roots["output"],
        sync_root=roots["sync"],
        attempt_timeout_seconds=3600,
    )

    assert len(calls) == 1
    jobs, arguments = calls[0]
    assert jobs == registered_jobs
    assert arguments == {
        "root": roots["output"].resolve(),
            "sync": sentinel_sync,
            "attempt_timeout_seconds": 3600.0,
            "attempt_staging_root": roots["staging"].resolve(),
        }
    assert "executor" not in arguments
    assert sync_calls == [roots["sync"].resolve()]
    assert report["status"] == "complete"
    assert report["launch_performed"] is True
    assert report["preflight"]["plan_sha256"] == preflight["plan"]["sha256"]
    assert report["execution"] == {
        "attempt_timeout_seconds": 3600.0,
        "stale_lease_after_seconds": None,
        "fresh_process_per_attempt": True,
        "separate_same_volume_staging": True,
        "default_executor": True,
        "mounted_directory_sync": True,
    }
    assert report["batch"]["total"] == 150
    assert report["batch"]["complete"] is True
    persisted = read_json(report["report_path"])
    assert persisted == report
    assert Path(report["lease"]["released_history_path"]).is_file()


def test_validation_itself_is_read_only_and_returns_bound_roots(roots):
    report_path, preflight = ready_preflight(roots)
    output_before = tuple(roots["output"].iterdir())

    validated = L.validate_ready_preflight(
        report_path,
        output_root=roots["output"],
        sync_root=roots["sync"],
    )

    assert tuple(roots["output"].iterdir()) == output_before == ()
    assert validated.plan_sha256 == preflight["plan"]["sha256"]
    assert validated.git_commit == "a" * 40
    assert validated.output_root == roots["output"].resolve()
    assert validated.staging_root == roots["staging"].resolve()
    assert validated.sync_root == roots["sync"].resolve()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: value.update(status="stale"), "not an unconsumed ready"),
        (lambda value: value.update(launch_performed=True), "not an unconsumed ready"),
        (lambda value: value.update(extra_field=True), "fields differ"),
        (
            lambda value: value["plan"].update(sha256="0" * 64),
            "not the current exact",
        ),
        (
            lambda value: value["environment"].update(python="0.0.0"),
            "not the current clean",
        ),
        (
            lambda value: value["device"].update(frozen_route="cuda"),
            "not the current frozen",
        ),
        (
            lambda value: value["storage"]["roots"]["output"].update(
                writable=False
            ),
            "was not writable",
        ),
        (
            lambda value: value["sync_receipt"].update(sha256="f" * 64),
            "does not bind",
        ),
    ],
)
def test_forged_ready_report_is_refused_before_lease_or_batch(
    monkeypatch, roots, change, message
):
    report_path, _ = ready_preflight(roots)
    rewrite_report(report_path, change)
    lease_calls = []
    batch_calls = []

    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: lease_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        B,
        "_run_registered_batch",
        lambda *args, **kwargs: batch_calls.append((args, kwargs)),
    )

    with pytest.raises(ValueError, match=message):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert lease_calls == []
    assert batch_calls == []
    assert not (roots["output"] / L.LAUNCH_REPORT_DIRECTORY).exists()
    assert not (roots["output"] / "leases").exists()


def test_noncanonical_report_bytes_are_refused_before_launch(monkeypatch, roots):
    report_path, report = ready_preflight(roots)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    calls = []
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: calls.append(True))

    with pytest.raises(ValueError, match="not the canonical immutable encoding"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert calls == []


def test_changed_current_commit_is_refused_before_launch(monkeypatch, roots):
    report_path, _ = ready_preflight(roots)
    monkeypatch.setattr(
        P, "git_state", lambda: GitState(commit="b" * 40, dirty=False, branch="main")
    )
    calls = []
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: calls.append(True))

    with pytest.raises(ValueError, match="not the current clean"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert calls == []


def test_dirty_current_git_is_refused_before_launch(monkeypatch, roots):
    report_path, _ = ready_preflight(roots)
    monkeypatch.setattr(
        P, "git_state", lambda: GitState(commit="a" * 40, dirty=True, branch="main")
    )
    calls = []
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: calls.append(True))

    with pytest.raises(ValueError, match="not a clean trustworthy commit"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert calls == []


def test_changed_current_package_is_refused_before_launch(monkeypatch, roots):
    report_path, _ = ready_preflight(roots)
    observed = P._pinned_package_versions()
    observed["numpy"] = "0.0.0"
    monkeypatch.setattr(P, "package_versions", lambda: observed)
    calls = []
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: calls.append(True))

    with pytest.raises(ValueError, match="do not match exact pyproject pins"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert calls == []


def test_changed_current_plan_is_refused_before_lease_or_batch(monkeypatch, roots):
    report_path, _ = ready_preflight(roots)
    jobs = B.experiment_1_jobs()
    monkeypatch.setattr(B, "experiment_1_jobs", lambda: jobs[:-1])
    lease_calls = []
    batch_calls = []
    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: lease_calls.append(True),
    )
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: batch_calls.append(True))

    with pytest.raises(ValueError, match="149 jobs"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert lease_calls == []
    assert batch_calls == []


def test_plan_change_after_preflight_validation_is_refused_before_lease(
    monkeypatch, roots, registered_jobs
):
    report_path, _ = ready_preflight(roots)
    real_validate = L.validate_ready_preflight
    validation_returns = []

    def validate_then_change_plan(*args, **kwargs):
        validated = real_validate(*args, **kwargs)
        validation_returns.append(True)
        monkeypatch.setattr(B, "experiment_1_jobs", lambda: registered_jobs[:-1])
        return validated

    lease_calls = []
    batch_calls = []
    monkeypatch.setattr(L, "validate_ready_preflight", validate_then_change_plan)
    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: lease_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        B, "_run_registered_batch", lambda *args, **kwargs: batch_calls.append((args, kwargs))
    )

    with pytest.raises(ValueError, match="149 jobs"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert validation_returns == [True]
    assert lease_calls == []
    assert batch_calls == []


def test_report_change_after_preflight_validation_is_refused_before_lease(
    monkeypatch, roots
):
    report_path, _ = ready_preflight(roots)
    real_validate = L.validate_ready_preflight
    validation_returns = []

    def validate_then_change_report(*args, **kwargs):
        validated = real_validate(*args, **kwargs)
        validation_returns.append(True)
        validated.report_path.write_bytes(validated.report_path.read_bytes() + b" ")
        return validated

    lease_calls = []
    batch_calls = []
    monkeypatch.setattr(L, "validate_ready_preflight", validate_then_change_report)
    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: lease_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        B, "_run_registered_batch", lambda *args, **kwargs: batch_calls.append((args, kwargs))
    )

    with pytest.raises(ValueError, match="changed after validation"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert validation_returns == [True]
    assert lease_calls == []
    assert batch_calls == []


def test_environment_change_after_preflight_validation_is_refused_before_lease(
    monkeypatch, roots
):
    report_path, _ = ready_preflight(roots)
    real_validate = L.validate_ready_preflight
    validation_returns = []

    def validate_then_dirty_environment(*args, **kwargs):
        validated = real_validate(*args, **kwargs)
        validation_returns.append(True)
        monkeypatch.setattr(
            P,
            "git_state",
            lambda: GitState(commit="a" * 40, dirty=True, branch="main"),
        )
        return validated

    lease_calls = []
    batch_calls = []
    monkeypatch.setattr(
        L, "validate_ready_preflight", validate_then_dirty_environment
    )
    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: lease_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        B, "_run_registered_batch", lambda *args, **kwargs: batch_calls.append((args, kwargs))
    )

    with pytest.raises(ValueError, match="not a clean trustworthy commit"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert validation_returns == [True]
    assert lease_calls == []
    assert batch_calls == []


def test_changed_mounted_canary_is_refused_before_launch(monkeypatch, roots):
    report_path, _ = ready_preflight(roots)
    (roots["sync"] / P.SYNC_CANARY_FILE).write_bytes(b"changed\n")
    calls = []
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: calls.append(True))

    with pytest.raises(ValueError, match="mounted preflight sync canary"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert calls == []


def test_requested_roots_must_be_the_preflight_roots(monkeypatch, roots, tmp_path):
    report_path, _ = ready_preflight(roots)
    wrong_output = tmp_path / "other-output"
    wrong_output.mkdir()
    calls = []
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: calls.append(True))

    with pytest.raises(ValueError, match="requested output_root differs"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=wrong_output,
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert calls == []


def test_cross_volume_preflight_staging_is_refused_before_lease_or_batch(
    monkeypatch, roots
):
    report_path, _ = ready_preflight(roots)
    real_identity = L._filesystem_identity

    def planted_identity(path):
        if Path(path) == roots["staging"].resolve():
            return 999, "synthetic-staging-volume"
        return real_identity(Path(path))

    lease_calls = []
    batch_calls = []
    monkeypatch.setattr(L, "_filesystem_identity", planted_identity)
    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: lease_calls.append(True),
    )
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: batch_calls.append(True))

    with pytest.raises(ValueError, match="share one filesystem volume"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert lease_calls == []
    assert batch_calls == []


@pytest.mark.parametrize("timeout", [True, 0, -1, float("inf"), float("nan")])
def test_bad_attempt_timeout_refuses_before_preflight_or_lease(
    monkeypatch, roots, timeout
):
    report_path, _ = ready_preflight(roots)
    validation_calls = []
    lease_calls = []
    monkeypatch.setattr(
        L,
        "validate_ready_preflight",
        lambda *args, **kwargs: validation_calls.append(True),
    )
    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: lease_calls.append(True),
    )

    with pytest.raises(ValueError, match="finite positive"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=timeout,
        )
    assert validation_calls == []
    assert lease_calls == []


@pytest.mark.parametrize("stale", [True, 0, -1, float("inf"), float("nan")])
def test_bad_stale_recovery_bound_refuses_before_preflight(monkeypatch, roots, stale):
    report_path, _ = ready_preflight(roots)
    validation_calls = []
    monkeypatch.setattr(
        L,
        "validate_ready_preflight",
        lambda *args, **kwargs: validation_calls.append(True),
    )

    with pytest.raises(ValueError, match="finite positive"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
            stale_lease_after_seconds=stale,
        )
    assert validation_calls == []


def test_explicit_stale_recovery_bound_is_forwarded(monkeypatch, roots):
    report_path, _ = ready_preflight(roots)
    batch_calls = []
    install_complete_batch(monkeypatch, batch_calls)
    lease_calls = []

    class FakeLease:
        token = "synthetic-lease-token"

        def release(self):
            destination = roots["output"] / "synthetic-released-lease.json"
            destination.write_text("{}\n", encoding="utf-8")
            return destination

    def acquire(root, **kwargs):
        lease_calls.append((Path(root), kwargs))
        return FakeLease()

    monkeypatch.setattr(L, "acquire_batch_lease", acquire)

    report = L.launch_experiment_1(
        preflight_report=report_path,
        output_root=roots["output"],
        sync_root=roots["sync"],
        attempt_timeout_seconds=10,
        stale_lease_after_seconds=300,
    )

    assert lease_calls == [
        (
            roots["output"].resolve(),
            {
                "lease_name": L.EXPERIMENT_1_LEASE_NAME,
                "stale_after_seconds": 300.0,
            },
        )
    ]
    assert report["execution"]["stale_lease_after_seconds"] == 300.0


def test_lease_conflict_prevents_batch_and_launch_report(monkeypatch, roots):
    report_path, _ = ready_preflight(roots)
    calls = []
    monkeypatch.setattr(
        L,
        "acquire_batch_lease",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            LeaseConflictError("synthetic owner holds lease")
        ),
    )
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: calls.append(True))

    with pytest.raises(LeaseConflictError, match="synthetic owner"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert calls == []
    assert not (roots["output"] / L.LAUNCH_REPORT_DIRECTORY).exists()


def test_malformed_batch_report_releases_lease_but_is_not_persisted(
    monkeypatch, roots
):
    report_path, _ = ready_preflight(roots)
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: {"forged": True})

    with pytest.raises(ValueError, match="not an exact BatchReport"):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )
    assert not (roots["output"] / L.LAUNCH_REPORT_DIRECTORY).exists()
    released = roots["output"] / "leases" / "history"
    assert len(tuple(released.glob("*.released.json"))) == 1


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        pytest.param(
            {"batch_id": "wrong-plan"},
            "wrong exact plan",
            id="wrong-batch-id",
        ),
        pytest.param(
            {"executed": True},
            "executed must be a nonnegative integer",
            id="boolean-count",
        ),
        pytest.param(
            {"failed": -1},
            "failed must be a nonnegative integer",
            id="negative-count",
        ),
        pytest.param(
            {"total": 149, "executed": 149, "synced": 149},
            "wrong total job count",
            id="wrong-total",
        ),
        pytest.param(
            {"executed": 149, "synced": 149},
            "does not account for every",
            id="incomplete-accounting",
        ),
        pytest.param(
            {"executed": 149, "synced": 150, "failed": 1},
            "sync counts exceed",
            id="impossible-sync-counts",
        ),
    ],
)
def test_typed_invalid_batch_report_is_released_and_never_persisted(
    monkeypatch, roots, changes, message
):
    report_path, _ = ready_preflight(roots)
    jobs = B.experiment_1_jobs()
    invalid = replace(complete_batch(jobs), **changes)
    monkeypatch.setattr(B, "_run_registered_batch", lambda *args, **kwargs: invalid)

    with pytest.raises(ValueError, match=message):
        L.launch_experiment_1(
            preflight_report=report_path,
            output_root=roots["output"],
            sync_root=roots["sync"],
            attempt_timeout_seconds=10,
        )

    assert not (roots["output"] / L.LAUNCH_REPORT_DIRECTORY).exists()
    released = roots["output"] / "leases" / "history"
    assert len(tuple(released.glob("*.released.json"))) == 1


def test_cli_parses_all_production_boundaries_and_prints_report(
    monkeypatch, capsys, tmp_path
):
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return {"status": "complete", "launch_id": "synthetic"}

    monkeypatch.setattr(L, "launch_experiment_1", fake)
    result = L.main(
        [
            "--preflight-report",
            str(tmp_path / "preflight_report.json"),
            "--output-root",
            str(tmp_path / "output"),
            "--sync-root",
            str(tmp_path / "sync"),
            "--attempt-timeout-seconds",
            "7200",
            "--stale-lease-after-seconds",
            "600",
        ]
    )

    assert result == 0
    assert calls == [
        {
            "preflight_report": tmp_path / "preflight_report.json",
            "output_root": tmp_path / "output",
            "sync_root": tmp_path / "sync",
            "attempt_timeout_seconds": 7200.0,
            "stale_lease_after_seconds": 600.0,
        }
    ]
    assert json.loads(capsys.readouterr().out) == {
        "status": "complete",
        "launch_id": "synthetic",
    }


def test_cli_omits_stale_recovery_unless_operator_supplies_it(
    monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        L,
        "launch_experiment_1",
        lambda **kwargs: calls.append(kwargs) or {"status": "incomplete"},
    )

    result = L.main(
        [
            "--preflight-report",
            str(tmp_path / "preflight_report.json"),
            "--output-root",
            str(tmp_path / "output"),
            "--sync-root",
            str(tmp_path / "sync"),
            "--attempt-timeout-seconds",
            "10",
        ]
    )

    assert result == 2
    assert calls[0]["stale_lease_after_seconds"] is None


def test_cli_validation_error_is_a_nonzero_parse_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        L,
        "launch_experiment_1",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("not ready")),
    )

    with pytest.raises(SystemExit) as caught:
        L.main(
            [
                "--preflight-report",
                str(tmp_path / "preflight_report.json"),
                "--output-root",
                str(tmp_path / "output"),
                "--sync-root",
                str(tmp_path / "sync"),
                "--attempt-timeout-seconds",
                "10",
            ]
        )
    assert caught.value.code == 2
