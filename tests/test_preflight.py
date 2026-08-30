"""Experiment-1 unattended-launch preflight tests; no fit is ever executed."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_bytes
from bu.experiments import preflight as P
from bu.experiments.batch import experiment_1_jobs as registered_experiment_1_jobs
from bu.runrecord import GitState


@pytest.fixture(scope="module")
def registered_jobs():
    return registered_experiment_1_jobs()


@pytest.fixture
def roots(tmp_path):
    values = {
        name: tmp_path / name
        for name in ("preflight", "output", "staging", "sync")
    }
    for path in values.values():
        path.mkdir()
    return values


@pytest.fixture(autouse=True)
def green_host(monkeypatch):
    pins = P._pinned_package_versions()
    monkeypatch.setattr(
        P, "git_state", lambda: GitState(commit="a" * 40, dirty=False, branch="main")
    )
    monkeypatch.setattr(P, "package_versions", lambda: dict(pins))
    monkeypatch.setattr(P, "_device_available", lambda route: route == "cpu")
    monkeypatch.setattr(
        P.shutil, "disk_usage", lambda path: SimpleNamespace(free=10_000_000)
    )


def verified_sync(source: Path, destination: Path, identity: str):
    data = source.read_bytes()
    atomic_write_bytes(destination, data)
    return P.SyncCanaryReceipt(
        schema_version=P.SYNC_RECEIPT_SCHEMA_VERSION,
        destination_identity=identity,
        destination_path=str(destination.resolve()),
        sha256=P.sha256_bytes(data),
        size_bytes=len(data),
    )


def run_preflight(roots, **overrides):
    arguments = {
        "preflight_dir": roots["preflight"],
        "output_root": roots["output"],
        "staging_root": roots["staging"],
        "sync_root": roots["sync"],
        "sync_destination_identity": "synthetic-off-worker-store",
        "sync_canary": verified_sync,
        "execution_route": "cpu",
        "minimum_free_bytes": 0,
    }
    arguments.update(overrides)
    return P.run_experiment_1_preflight(**arguments)


def test_green_preflight_persists_complete_immutable_report_without_launching(roots):
    report = run_preflight(roots, minimum_free_bytes=1024)

    assert report["preflight_schema_version"] == P.PREFLIGHT_SCHEMA_VERSION
    assert report["status"] == "ready"
    assert report["launch_performed"] is False
    assert report["plan"] == {
        "fit_count": 150,
        "unique_fit_count": 150,
        "multi_role_fit_count": 30,
        "seeds": [1000, 1001, 1002, 1003, 1004],
        "sizes": [100, 250, 500, 1000, 2500, 5000],
        "configurations_per_size_seed": 5,
        "sha256": report["plan"]["sha256"],
    }
    assert len(report["plan"]["sha256"]) == 64
    assert report["environment"]["git"] == {
        "commit": "a" * 40,
        "branch": "main",
        "dirty": False,
        "trustworthy": True,
    }
    assert report["environment"]["packages"] == report["environment"]["exact_pins"]
    assert set(report["environment"]["packages"]) == set(P.TRACKED_PACKAGES)
    assert report["device"] == {
        "frozen_route": "cpu",
        "requested_route": "cpu",
        "available": True,
    }
    assert report["storage"]["minimum_free_bytes"] == 1024
    assert report["sync_receipt"]["destination_identity"] == (
        "synthetic-off-worker-store"
    )

    persisted = json.loads(
        (roots["preflight"] / P.PREFLIGHT_REPORT_FILE).read_text(encoding="utf-8")
    )
    assert persisted == report
    assert set(path.name for path in roots["preflight"].iterdir()) == {
        P.SYNC_CANARY_FILE,
        P.PREFLIGHT_REPORT_FILE,
    }
    assert set(path.name for path in roots["sync"].iterdir()) == {P.SYNC_CANARY_FILE}
    assert list(roots["output"].iterdir()) == []
    assert list(roots["staging"].iterdir()) == []


def test_identical_retry_is_idempotent(roots):
    first = run_preflight(roots)
    second = run_preflight(roots)
    assert first == second


def test_existing_different_report_is_never_overwritten(roots):
    run_preflight(roots)
    report_path = roots["preflight"] / P.PREFLIGHT_REPORT_FILE
    report_path.write_text('{"forged":true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="different content|overwrite"):
        run_preflight(roots)
    assert report_path.read_text(encoding="utf-8") == '{"forged":true}\n'


def test_plan_refuses_wrong_total(monkeypatch, roots, registered_jobs):
    monkeypatch.setattr(P, "experiment_1_jobs", lambda: registered_jobs[:-1])
    with pytest.raises(ValueError, match="149 jobs"):
        run_preflight(roots)


def test_plan_refuses_duplicate_fit_id(monkeypatch, roots, registered_jobs):
    jobs = list(registered_jobs)
    jobs[1] = jobs[0]
    monkeypatch.setattr(P, "experiment_1_jobs", lambda: tuple(jobs))
    with pytest.raises(ValueError, match="150 unique fit ids"):
        run_preflight(roots)


def test_plan_refuses_wrong_seed_inventory(monkeypatch, roots, registered_jobs):
    jobs = list(registered_jobs)
    index = next(i for i, item in enumerate(jobs) if item.roles == ("exp1",))
    jobs[index] = replace(jobs[index], seed=1005)
    monkeypatch.setattr(P, "experiment_1_jobs", lambda: tuple(jobs))
    with pytest.raises(ValueError, match="seeds/counts"):
        run_preflight(roots)


def test_plan_refuses_wrong_multi_role_count(monkeypatch, roots, registered_jobs):
    jobs = list(registered_jobs)
    index = next(i for i, item in enumerate(jobs) if item.roles == ("exp1",))
    jobs[index] = replace(jobs[index], roles=("exp1", "repair_validation"))
    monkeypatch.setattr(P, "experiment_1_jobs", lambda: tuple(jobs))
    with pytest.raises(ValueError, match="role inventory"):
        run_preflight(roots)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        pytest.param(
            {"stage": "exp2a", "roles": ("exp2a",)},
            "only exp1 baseline jobs",
            id="wrong-stage",
        ),
        pytest.param(
            {"arm": "data_repair"},
            "only exp1 baseline jobs",
            id="wrong-arm",
        ),
    ],
)
def test_plan_refuses_wrong_stage_or_arm(
    monkeypatch, roots, registered_jobs, changes, message
):
    jobs = list(registered_jobs)
    jobs[0] = replace(jobs[0], **changes)
    monkeypatch.setattr(P, "experiment_1_jobs", lambda: tuple(jobs))

    with pytest.raises(ValueError, match=message):
        run_preflight(roots)


def test_plan_refuses_wrong_six_by_five_by_five_cell_allocation(
    monkeypatch, roots, registered_jobs
):
    jobs = list(registered_jobs)
    jobs[0] = replace(
        jobs[0],
        unit=replace(jobs[0].unit, n_transitions=101),
    )
    monkeypatch.setattr(P, "experiment_1_jobs", lambda: tuple(jobs))

    with pytest.raises(ValueError, match="exactly 6 sizes x 5 configurations x 5 seeds"):
        run_preflight(roots)


def test_plan_refuses_non_batch_job(monkeypatch, roots, registered_jobs):
    jobs = list(registered_jobs)
    jobs[0] = object()
    monkeypatch.setattr(P, "experiment_1_jobs", lambda: tuple(jobs))
    with pytest.raises(ValueError, match="non-exact BatchJob"):
        run_preflight(roots)


@pytest.mark.parametrize(
    "state, message",
    [
        (GitState(commit="A" * 40, dirty=False, branch="main"), "40-hex"),
        (GitState(commit="a" * 39, dirty=False, branch="main"), "40-hex"),
        (GitState(commit="a" * 40, dirty=True, branch="main"), "not a clean"),
    ],
)
def test_git_provenance_refusals(monkeypatch, roots, state, message):
    monkeypatch.setattr(P, "git_state", lambda: state)
    with pytest.raises(ValueError, match=message):
        run_preflight(roots)


def test_git_state_must_be_typed(monkeypatch, roots):
    monkeypatch.setattr(P, "git_state", lambda: {"commit": "a" * 40})
    with pytest.raises(ValueError, match="not GitState"):
        run_preflight(roots)


@pytest.mark.parametrize("replacement", ["MISSING", "2.4.0", None])
def test_every_tracked_package_must_match_its_exact_pin(monkeypatch, roots, replacement):
    versions = P._pinned_package_versions()
    versions["numpy"] = replacement
    monkeypatch.setattr(P, "package_versions", lambda: versions)
    with pytest.raises(ValueError, match="numpy: observed"):
        run_preflight(roots)


def test_a_tracked_dependency_without_an_exact_pin_is_refused(monkeypatch, roots, tmp_path):
    project = tmp_path / "synthetic-project"
    project.mkdir()
    dependencies = [
        f'    "{name}{">=" if name == "numpy" else "=="}{version}",'
        for name, version in P._pinned_package_versions().items()
    ]
    (project / "pyproject.toml").write_text(
        "[project]\nname='synthetic'\nversion='0'\ndependencies=[\n"
        + "\n".join(dependencies)
        + "\n]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(P, "PROJECT_ROOT", project)
    with pytest.raises(ValueError, match="numpy.*no exact == pin"):
        run_preflight(roots)


def test_requested_route_must_equal_frozen_route(roots):
    with pytest.raises(ValueError, match="not the frozen"):
        run_preflight(roots, execution_route="cuda")


def test_frozen_device_must_be_available(monkeypatch, roots):
    monkeypatch.setattr(P, "_device_available", lambda route: False)
    with pytest.raises(ValueError, match="unavailable"):
        run_preflight(roots)


@pytest.mark.parametrize("route", [None, "", 1])
def test_execution_route_is_an_exact_nonempty_string(roots, route):
    with pytest.raises(ValueError, match="nonempty exact string"):
        run_preflight(roots, execution_route=route)


@pytest.mark.parametrize("minimum", [-1, True, 0.0, float("inf"), float("nan")])
def test_free_byte_requirement_is_finite_nonnegative_exact_integer(roots, minimum):
    with pytest.raises(ValueError, match="finite nonnegative integer"):
        run_preflight(roots, minimum_free_bytes=minimum)


def test_every_root_must_exist(roots, tmp_path):
    with pytest.raises(ValueError, match="does not resolve"):
        run_preflight(roots, output_root=tmp_path / "absent")


def test_every_root_must_be_a_directory(roots, tmp_path):
    file_path = tmp_path / "ordinary-file"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        run_preflight(roots, output_root=file_path)


def test_every_root_must_be_writable(monkeypatch, roots):
    real_access = P.os.access
    output = roots["output"].resolve()
    monkeypatch.setattr(
        P.os,
        "access",
        lambda path, mode: False if Path(path) == output else real_access(path, mode),
    )
    with pytest.raises(ValueError, match="output_root is not writable"):
        run_preflight(roots)


def test_every_root_must_have_required_free_bytes(monkeypatch, roots):
    monkeypatch.setattr(P.shutil, "disk_usage", lambda path: SimpleNamespace(free=99))
    with pytest.raises(ValueError, match="below required 100"):
        run_preflight(roots, minimum_free_bytes=100)


def test_equal_resolved_roots_are_refused(roots):
    with pytest.raises(ValueError, match="distinct and non-overlapping"):
        run_preflight(roots, staging_root=roots["output"])


def test_nested_resolved_roots_are_refused(roots):
    nested = roots["output"] / "nested"
    nested.mkdir()
    with pytest.raises(ValueError, match="distinct and non-overlapping"):
        run_preflight(roots, staging_root=nested)


@pytest.mark.parametrize("identity", [None, "", " destination", "destination ", 4])
def test_destination_identity_is_exact_and_nonempty(roots, identity):
    with pytest.raises(ValueError, match="destination_identity"):
        run_preflight(roots, sync_destination_identity=identity)


def test_sync_adapter_is_mandatory(roots):
    with pytest.raises(ValueError, match="must be callable"):
        run_preflight(roots, sync_canary=None)


@pytest.mark.parametrize("returned", [None, {}, True])
def test_sync_adapter_must_return_exact_typed_receipt(roots, returned):
    def adapter(source, destination, identity):
        atomic_write_bytes(destination, source.read_bytes())
        return returned

    with pytest.raises(ValueError, match="exact SyncCanaryReceipt"):
        run_preflight(roots, sync_canary=adapter)


def test_no_op_adapter_cannot_claim_sync(roots):
    def no_op(source, destination, identity):
        data = source.read_bytes()
        return P.SyncCanaryReceipt(
            P.SYNC_RECEIPT_SCHEMA_VERSION,
            identity,
            str(destination),
            P.sha256_bytes(data),
            len(data),
        )

    with pytest.raises(ValueError, match="does not exist"):
        run_preflight(roots, sync_canary=no_op)


@pytest.mark.parametrize(
    "field, replacement, message",
    [
        ("schema_version", 2, "receipt schema"),
        ("schema_version", True, "receipt schema"),
        ("destination_identity", "forged-destination", "wrong destination identity"),
        ("sha256", "0" * 64, "exact canary SHA256"),
        ("size_bytes", 0, "exact canary byte count"),
    ],
)
def test_forged_receipt_fields_are_refused(roots, field, replacement, message):
    def adapter(source, destination, identity):
        data = source.read_bytes()
        atomic_write_bytes(destination, data)
        values = {
            "schema_version": P.SYNC_RECEIPT_SCHEMA_VERSION,
            "destination_identity": identity,
            "destination_path": str(destination.resolve()),
            "sha256": P.sha256_bytes(data),
            "size_bytes": len(data),
        }
        values[field] = replacement
        return P.SyncCanaryReceipt(**values)

    with pytest.raises(ValueError, match=message):
        run_preflight(roots, sync_canary=adapter)


def test_receipt_path_cannot_escape_prescribed_destination(roots):
    def adapter(source, destination, identity):
        data = source.read_bytes()
        atomic_write_bytes(destination, data)
        other = destination.parent / "other-canary"
        atomic_write_bytes(other, data)
        return P.SyncCanaryReceipt(
            P.SYNC_RECEIPT_SCHEMA_VERSION,
            identity,
            str(other.resolve()),
            P.sha256_bytes(data),
            len(data),
        )

    with pytest.raises(ValueError, match="not the prescribed destination"):
        run_preflight(roots, sync_canary=adapter)


def test_receipt_cannot_attest_different_destination_bytes(roots):
    def adapter(source, destination, identity):
        data = source.read_bytes()
        atomic_write_bytes(destination, b"forged")
        return P.SyncCanaryReceipt(
            P.SYNC_RECEIPT_SCHEMA_VERSION,
            identity,
            str(destination.resolve()),
            P.sha256_bytes(data),
            len(data),
        )

    with pytest.raises(ValueError, match="synced canary bytes"):
        run_preflight(roots, sync_canary=adapter)


def test_adapter_failure_is_contextualised(roots):
    def adapter(source, destination, identity):
        raise OSError("planted transport failure")

    with pytest.raises(ValueError, match="planted transport failure"):
        run_preflight(roots, sync_canary=adapter)


def test_mounted_directory_adapter_copies_and_attests_exact_bytes(tmp_path):
    source = tmp_path / "source.json"
    destination = tmp_path / "mounted" / "canary.json"
    source.write_bytes(b'{"canary":true}\n')

    receipt = P.sync_canary_to_mounted_directory(
        source, destination, "mounted-test-store"
    )

    assert destination.read_bytes() == source.read_bytes()
    assert receipt.destination_identity == "mounted-test-store"
    assert receipt.destination_path == str(destination.resolve())
    assert receipt.sha256 == P.sha256_file(source)


def test_preflight_cli_runs_no_launch_and_prints_ready_report(
    monkeypatch, roots, capsys
):
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return {"status": "ready", "launch_performed": False}

    monkeypatch.setattr(P, "run_experiment_1_preflight", fake)
    code = P.main(
        [
            "--preflight-dir", str(roots["preflight"]),
            "--output-root", str(roots["output"]),
            "--staging-root", str(roots["staging"]),
            "--sync-root", str(roots["sync"]),
            "--sync-destination-identity", "mounted-store",
            "--minimum-free-bytes", "123",
        ]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["launch_performed"] is False
    assert calls[0]["sync_canary"] is P.sync_canary_to_mounted_directory
    assert calls[0]["minimum_free_bytes"] == 123
