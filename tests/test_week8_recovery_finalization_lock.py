"""Synthetic contracts for the D-161 bootstrap finalization lock.

The controller postmortem and worker terminal use different immutable record
names.  These tests prove that their shared, project-local byte-range lock
chooses at most one family, that a single surviving twin blocks the opposite
family, and that unsafe guard identities fail before any finalization write.

Every mutable path is relocated beneath ``tmp_path``.  The subprocess test
loads only the stdlib bootstrap worker and never opens production evidence,
scientific outputs, the network, or a GPU.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator

import pytest

from bu.experiments import week8_exp2a_recovery as R


@dataclass(frozen=True)
class LockEnvironment:
    workspace: Path
    worker: ModuleType
    guard: Path


@pytest.fixture(scope="module")
def recovery_worker() -> ModuleType:
    """Load the actual standalone worker without importing execution-tree ``bu``."""

    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "week8_exp2a_recovery_worker.py"
    )
    specification = importlib.util.spec_from_file_location(
        "week8_recovery_finalization_lock_worker", path
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def lock_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: ModuleType,
) -> LockEnvironment:
    workspace = tmp_path / "workspace"
    recovery = workspace / "recovery"
    recovery_copy = workspace / "recovery-copy"
    for root in (recovery, recovery_copy):
        (root / "records").mkdir(parents=True)

    monkeypatch.setattr(R, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(R, "RECOVERY_ROOT", recovery)
    monkeypatch.setattr(R, "RECOVERY_COPY_ROOT", recovery_copy)
    monkeypatch.setattr(R.Plan, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(
        R.Plan,
        "COMMON_LEASE_ROOT",
        workspace / "week7-production-control",
    )

    worker = recovery_worker
    monkeypatch.setattr(worker, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(worker, "RECOVERY_ROOT", recovery)
    monkeypatch.setattr(worker, "RECOVERY_COPY_ROOT", recovery_copy)

    controller_guard = R._finalization_guard_path()
    worker_guard = worker._finalization_guard_path()
    assert controller_guard == worker_guard
    controller_guard.parent.mkdir(parents=True)
    controller_guard.write_bytes(b"\0")
    return LockEnvironment(workspace, worker, controller_guard)


def _paths(environment: LockEnvironment, name: str) -> tuple[Path, Path]:
    paths = environment.worker._record_paths(name)
    assert paths == R._record_paths(name)
    return paths


def _plant(
    environment: LockEnvironment,
    name: str,
    *,
    twins: int,
    data: bytes = b"synthetic-finalization-evidence\n",
) -> tuple[Path, ...]:
    assert twins in {1, 2}
    paths = _paths(environment, name)
    for path in paths[:twins]:
        path.write_bytes(data)
    return paths[:twins]


def _assert_absent(environment: LockEnvironment, name: str) -> None:
    assert not any(os.path.lexists(path) for path in _paths(environment, name))


def _assert_no_finalization(environment: LockEnvironment) -> None:
    _assert_absent(environment, environment.worker.BOOTSTRAP_TERMINAL_FILE)
    _assert_absent(environment, environment.worker.BOOTSTRAP_POSTMORTEM_FILE)


def _worker_invocation(worker: ModuleType) -> dict[str, Any]:
    return {
        "recovery_schema_version": worker.RECOVERY_SCHEMA_VERSION,
        "recovery_id": worker.RECOVERY_ID,
        "decision_id": worker.DECISION_ID,
        "record_type": "bootstrap_invocation",
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "record_digest": "0" * 64,
    }


def test_controller_and_worker_derive_and_enter_the_same_guard(
    lock_environment: LockEnvironment,
) -> None:
    worker = lock_environment.worker
    assert R._finalization_guard_path() == worker._finalization_guard_path()
    assert R._finalization_guard_path() == lock_environment.guard

    # Windows intentionally denies a second open of the byte-range-locked file,
    # so successful context entry is the portable assertion while it is held.
    with R._finalization_lock():
        pass
    with worker._finalization_lock():
        pass
    assert lock_environment.guard.read_bytes().startswith(b"\0")
    _assert_no_finalization(lock_environment)


@pytest.mark.parametrize("postmortem_twins", (1, 2))
@pytest.mark.parametrize("route", ("success", "refusal"))
def test_postmortem_blocks_success_and_refusal_terminal_publication(
    lock_environment: LockEnvironment,
    postmortem_twins: int,
    route: str,
) -> None:
    worker = lock_environment.worker
    planted = _plant(
        lock_environment,
        worker.BOOTSTRAP_POSTMORTEM_FILE,
        twins=postmortem_twins,
    )
    before = {path: path.read_bytes() for path in planted}

    with pytest.raises(worker.BootstrapRefused, match="postmortem"):
        if route == "success":
            worker._publish_terminal_twins(
                {"record_type": "synthetic-success-terminal"}
            )
        else:
            worker._terminalize_failure(
                worker.BootstrapRefused("synthetic lower refusal"),
                invocation=_worker_invocation(worker),
                invocation_sha="1" * 64,
                claim={"record_digest": "2" * 64},
                claim_sha="3" * 64,
                claim_twins_complete=True,
            )

    _assert_absent(lock_environment, worker.BOOTSTRAP_TERMINAL_FILE)
    assert {path: path.read_bytes() for path in planted} == before


@pytest.mark.parametrize("terminal_twins", (1, 2))
def test_terminal_winner_blocks_controller_postmortem_choice(
    lock_environment: LockEnvironment,
    monkeypatch: pytest.MonkeyPatch,
    terminal_twins: int,
) -> None:
    worker = lock_environment.worker
    planted = _plant(
        lock_environment,
        worker.BOOTSTRAP_TERMINAL_FILE,
        twins=terminal_twins,
    )
    before = {path: path.read_bytes() for path in planted}
    states = iter(
        (
            {"state": "postmortem_seal_required"},
            {
                "state": (
                    "partial_terminal" if terminal_twins == 1 else "terminal_refused"
                )
            },
        )
    )
    monkeypatch.setattr(R, "_load_adjudication", lambda: ({}, "1" * 64, {}, "2" * 64))
    monkeypatch.setattr(R, "_assert_current_controller_authority", lambda incident: {})
    monkeypatch.setattr(R, "_bootstrap_state", lambda: next(states))
    monkeypatch.setattr(
        R,
        "_publish_twins_exclusive",
        lambda *args, **kwargs: pytest.fail(
            "controller must not publish postmortem after a terminal path wins"
        ),
    )

    with pytest.raises(R.RecoveryRefused, match="stopped while postmortem waited"):
        R.seal()

    _assert_absent(lock_environment, worker.BOOTSTRAP_POSTMORTEM_FILE)
    assert {path: path.read_bytes() for path in planted} == before


@pytest.mark.parametrize("terminal_side", (0, 1))
def test_partial_terminal_is_not_repaired_by_worker_reentry(
    lock_environment: LockEnvironment,
    terminal_side: int,
) -> None:
    worker = lock_environment.worker
    terminal_paths = _paths(lock_environment, worker.BOOTSTRAP_TERMINAL_FILE)
    terminal_paths[terminal_side].write_bytes(b"partial-terminal\n")
    before = terminal_paths[terminal_side].read_bytes()

    with pytest.raises(worker.BootstrapRefused, match="terminal path"):
        worker._publish_terminal_twins({"record_type": "synthetic-reentry"})

    assert terminal_paths[terminal_side].read_bytes() == before
    assert not os.path.lexists(terminal_paths[1 - terminal_side])
    _assert_absent(lock_environment, worker.BOOTSTRAP_POSTMORTEM_FILE)


def test_worker_terminal_helper_holds_guard_across_twin_publication(
    lock_environment: LockEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = lock_environment.worker
    actions: list[str] = []
    original_lock = worker._finalization_lock

    @contextmanager
    def observed_lock() -> Iterator[None]:
        actions.append("lock-enter")
        with original_lock():
            yield
        actions.append("lock-exit")

    def publish(name: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        actions.append("publish")
        assert actions == ["lock-enter", "publish"]
        return payload, "4" * 64

    monkeypatch.setattr(worker, "_finalization_lock", observed_lock)
    monkeypatch.setattr(worker, "_exclusive_publish_twins", publish)
    document, digest = worker._publish_terminal_twins({"synthetic": True})
    assert document == {"synthetic": True}
    assert digest == "4" * 64
    assert actions == ["lock-enter", "publish", "lock-exit"]
    _assert_no_finalization(lock_environment)


def _wait_for_marker(process: subprocess.Popen[str], marker: Path) -> None:
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if marker.is_file():
            return
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(
                "worker lock subprocess exited before acquiring the guard; "
                f"stdout={stdout!r}, stderr={stderr!r}"
            )
        time.sleep(0.02)
    pytest.fail("worker lock subprocess did not acquire the guard in time")


def test_real_worker_process_serializes_controller_lock(
    lock_environment: LockEnvironment,
) -> None:
    worker_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "week8_exp2a_recovery_worker.py"
    )
    held = lock_environment.workspace / "child-held.marker"
    release = lock_environment.workspace / "child-release.marker"
    observed_guard = lock_environment.workspace / "child-guard.txt"
    child_source = """
import importlib.util
import sys
import time
from pathlib import Path

worker_path = Path(sys.argv[1])
workspace = Path(sys.argv[2])
held = Path(sys.argv[3])
release = Path(sys.argv[4])
observed_guard = Path(sys.argv[5])
spec = importlib.util.spec_from_file_location("d161_lock_child_worker", worker_path)
if spec is None or spec.loader is None:
    raise SystemExit(91)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.WORKSPACE_ROOT = workspace
with module._finalization_lock():
    observed_guard.write_text(str(module._finalization_guard_path()), encoding="utf-8")
    held.write_bytes(b"held")
    deadline = time.monotonic() + 10.0
    while not release.exists():
        if time.monotonic() >= deadline:
            raise SystemExit(92)
        time.sleep(0.02)
"""
    environment = dict(os.environ)
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": "-1",
            "HIP_VISIBLE_DEVICES": "-1",
            "OMP_NUM_THREADS": "4",
            "MKL_NUM_THREADS": "4",
            "OPENBLAS_NUM_THREADS": "4",
            "NUMEXPR_NUM_THREADS": "4",
            "PYTHONHASHSEED": "0",
        }
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-S",
            "-s",
            "-P",
            "-c",
            child_source,
            str(worker_path),
            str(lock_environment.workspace),
            str(held),
            str(release),
            str(observed_guard),
        ],
        cwd=lock_environment.workspace,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    try:
        _wait_for_marker(process, held)

        def release_child() -> None:
            time.sleep(0.30)
            release.write_bytes(b"release")

        releaser = threading.Thread(target=release_child, daemon=True)
        releaser.start()
        started = time.monotonic()
        with R._finalization_lock():
            elapsed = time.monotonic() - started
        releaser.join(timeout=2.0)
        assert not releaser.is_alive()
        stdout, stderr = process.communicate(timeout=10.0)
        assert process.returncode == 0, (stdout, stderr)
        assert elapsed >= 0.20
        assert Path(observed_guard.read_text(encoding="utf-8")) == lock_environment.guard
        _assert_no_finalization(lock_environment)
    finally:
        release.write_bytes(b"release")
        if process.poll() is None:
            try:
                process.communicate(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5.0)


@pytest.mark.parametrize("actor", ("controller", "worker"))
@pytest.mark.parametrize("guard_kind", ("directory", "hardlink"))
def test_unsafe_guard_refuses_without_finalization_write(
    lock_environment: LockEnvironment,
    actor: str,
    guard_kind: str,
) -> None:
    guard = lock_environment.guard
    guard.unlink()
    if guard_kind == "directory":
        guard.mkdir()
    else:
        target = lock_environment.workspace / "guard-hardlink-target"
        target.write_bytes(b"\0")
        os.link(target, guard)
        assert target.stat().st_nlink >= 2

    worker = lock_environment.worker
    action: Callable[[], Any]
    error: type[BaseException]
    if actor == "controller":
        action = R._finalization_lock
        error = R.RecoveryRefused
    else:
        action = worker._finalization_lock
        error = worker.BootstrapRefused

    with pytest.raises(error, match="guard"):
        with action():
            pytest.fail("unsafe finalization guard must never be entered")
    _assert_no_finalization(lock_environment)


@pytest.mark.parametrize("actor", ("controller", "worker"))
def test_reparse_guard_refuses_without_finalization_write_when_supported(
    lock_environment: LockEnvironment,
    actor: str,
) -> None:
    guard = lock_environment.guard
    guard.unlink()
    target = lock_environment.workspace / "guard-reparse-target"
    target.write_bytes(b"\0")
    try:
        os.symlink(target, guard)
    except OSError:
        pytest.skip("this host cannot create a file symlink/reparse point")

    worker = lock_environment.worker
    action: Callable[[], Any]
    error: type[BaseException]
    if actor == "controller":
        action = R._finalization_lock
        error = R.RecoveryRefused
    else:
        action = worker._finalization_lock
        error = worker.BootstrapRefused

    with pytest.raises(error, match="guard"):
        with action():
            pytest.fail("reparse finalization guard must never be entered")
    _assert_no_finalization(lock_environment)
