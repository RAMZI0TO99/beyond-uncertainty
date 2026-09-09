"""Synthetic-only tests for the incident-specific D-161 recovery controller.

No production root, lease, fit, metric, label, ratio, exclusion, or H2 result is
opened by this suite.  Fixed paths are relocated under ``tmp_path`` and the
scientific source validator plus Windows process observer are mocked at their
explicit boundaries.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from bu import runrecord as RR
from bu.durable import atomic_write_bytes, atomic_write_json, read_json, sha256_file
from bu.experiments import week8_exp2a_recovery as R


NEW_TOKEN = "d" * 32
CONTEXT = "c" * 64
OLD_CHECKPOINT_DIGEST = "a" * 64
NEW_CHECKPOINT_DIGEST = "b" * 64


def _synthetic_native_startup() -> dict[str, Any]:
    """Return the minimal schema-4 startup proof used by synthetic fixtures."""

    return {
        "release_receipt_sha256": "0" * 64,
        "native_launcher": {"sha256": "1" * 64},
        "stage0_binding_sha256": "6" * 64,
        "startup_binding_sha256": "2" * 64,
        "startup_environment_sha256": "3" * 64,
        "pinned_base_runtime": {"inventory_sha256": "4" * 64},
        "pinned_venv_scripts": {"inventory_sha256": "5" * 64},
    }


def _synthetic_compact_preimport_binding(
    *,
    entrypoint_sha256: str,
    raw_helper_sha256: str,
    raw_record_digest: str,
    controller_tree_digest: str,
    execution_tree_digest: str,
    git_runtime_inventory_digest: str,
    site_packages_inventory_digest: str,
    native_startup: dict[str, Any],
) -> dict[str, Any]:
    return {
        "raw_authority_schema_version": 4,
        "entrypoint_schema_version": 4,
        "entrypoint_sha256": entrypoint_sha256,
        "raw_authority_helper_sha256": raw_helper_sha256,
        "raw_authority_record_digest": raw_record_digest,
        "controller_tree_digest": controller_tree_digest,
        "execution_tree_digest": execution_tree_digest,
        "git_runtime_inventory_digest": git_runtime_inventory_digest,
        "site_packages_inventory_digest": site_packages_inventory_digest,
        "release_receipt_sha256": native_startup["release_receipt_sha256"],
        "native_launcher_sha256": native_startup["native_launcher"]["sha256"],
        "stage0_binding_sha256": native_startup["stage0_binding_sha256"],
        "startup_binding_sha256": native_startup["startup_binding_sha256"],
        "startup_environment_sha256": native_startup[
            "startup_environment_sha256"
        ],
        "base_runtime_inventory_sha256": native_startup[
            "pinned_base_runtime"
        ]["inventory_sha256"],
        "venv_scripts_inventory_sha256": native_startup[
            "pinned_venv_scripts"
        ]["inventory_sha256"],
    }


def test_controller_has_no_duplicate_git_authority_surface() -> None:
    """Git/tree observation belongs exclusively to the raw-authority helper."""

    for obsolete_name in (
        "_git",
        "_resolved_git_executable",
        "_isolated_git_environment",
        "_worktree_identity",
    ):
        assert not hasattr(R, obsolete_name)


def test_raw_authority_config_binds_git_runtime_and_dependency_tree() -> None:
    controller_commit = "2" * 40
    native_startup = _synthetic_native_startup()
    config = R._raw_authority_config(controller_commit, native_startup)
    assert set(config) == {
        "controller_root",
        "controller_commit",
        "release_receipt_sha256",
        "native_launcher_sha256",
        "stage0_binding_sha256",
        "startup_binding_sha256",
        "execution_root",
        "execution_commit",
        "pinned_python",
        "pinned_base_python",
        "pinned_base_runtime",
        "pinned_pyvenv",
        "pinned_venv_scripts",
        "native_launcher",
        "native_powershell",
        "native_runtime",
        "pinned_site_packages",
        "pinned_git",
        "pinned_git_runtime_root",
        "pinned_python_sha256",
        "pinned_base_python_sha256",
        "pinned_pyvenv_sha256",
        "pinned_base_runtime_inventory_sha256",
        "pinned_base_runtime_file_count",
        "pinned_base_runtime_directory_count",
        "pinned_base_runtime_total_bytes",
        "pinned_venv_scripts_inventory_sha256",
        "pinned_venv_scripts_file_count",
        "pinned_venv_scripts_directory_count",
        "pinned_venv_scripts_total_bytes",
        "pinned_git_sha256",
        "pinned_git_runtime_inventory_digest",
        "pinned_git_runtime_file_count",
        "pinned_git_runtime_directory_count",
        "pinned_git_runtime_total_bytes",
        "pinned_site_packages_inventory_digest",
        "pinned_site_packages_file_count",
        "pinned_site_packages_directory_count",
        "pinned_site_packages_total_bytes",
        "outer_bootstrap_literal_sha256",
    }
    assert config["controller_commit"] == controller_commit
    assert (
        config["release_receipt_sha256"]
        == native_startup["release_receipt_sha256"]
    )
    assert (
        config["native_launcher_sha256"]
        == native_startup["native_launcher"]["sha256"]
    )
    assert (
        config["stage0_binding_sha256"]
        == native_startup["stage0_binding_sha256"]
    )
    assert (
        config["startup_binding_sha256"]
        == native_startup["startup_binding_sha256"]
    )
    assert config["pinned_git"] == str(R.PINNED_GIT)
    assert config["pinned_git_runtime_root"] == str(R.PINNED_GIT_RUNTIME_ROOT)
    assert config["pinned_git_sha256"] == R.EXPECTED_PINNED_GIT_SHA256
    assert (
        config["pinned_site_packages_inventory_digest"]
        == R.EXPECTED_PINNED_SITE_PACKAGES_INVENTORY_DIGEST
    )
    assert (
        config["outer_bootstrap_literal_sha256"]
        == R.EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256
    )


def test_child_environment_overrides_ambient_executable_search_and_git_hooks(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "99")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "hostile-helper")
    monkeypatch.setenv("PATH", str(relocated / "hostile-bin"))
    environment = R._sanitized_subprocess_environment(R.RUNTIME_TEMP)
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_COUNT"] == "1"
    assert environment["GIT_CONFIG_KEY_0"] == "safe.directory"
    assert environment["GIT_CONFIG_VALUE_0"] == str(
        R.EXECUTION_WORKTREE.resolve()
    )
    assert environment["PATH"] == str(R.PINNED_GIT.parent.resolve())
    assert environment["PAGER"] == ""
    assert environment["GIT_PAGER"] == ""


def test_controller_source_root_refuses_non_bu_import_shadow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = tmp_path / "controller"
    source = controller / "src"
    source.mkdir(parents=True)
    atomic_write_bytes(source / "json.py", b"raise RuntimeError('shadow')\n")
    monkeypatch.setattr(R, "CONTROLLER_WORKTREE", controller)
    raw_module = SimpleNamespace(
        admitted_git_blob=lambda *args: "a" * 40,
        admitted_source_bytes=lambda *args: b"synthetic",
    )
    with pytest.raises(R.RecoveryRefused, match="non-bu import shadow"):
        R._validate_loaded_controller_modules({}, raw_module)


def test_controller_modules_require_bound_loader_marker_and_source_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = tmp_path / "controller"
    source = controller / "src"
    package = source / "bu"
    recovery_package = package / "experiments"
    recovery_package.mkdir(parents=True)
    root_file = package / "__init__.py"
    recovery_file = recovery_package / "week8_exp2a_recovery.py"
    atomic_write_bytes(root_file, b"# synthetic bu\n")
    atomic_write_bytes(recovery_file, b"# synthetic recovery\n")
    sources = {
        "src/bu/__init__.py": root_file.read_bytes(),
        "src/bu/experiments/week8_exp2a_recovery.py": (
            recovery_file.read_bytes()
        ),
    }
    monkeypatch.setattr(R, "CONTROLLER_WORKTREE", controller)
    for name in tuple(sys.modules):
        if name == "bu" or name.startswith("bu."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    def bound_module(name: str, path: Path, relative: str) -> ModuleType:
        loader = SimpleNamespace(
            binding_marker="week8_d161_verified_source_v2",
            name=name,
            path=str(path),
            source_sha256=R.sha256_bytes(sources[relative]),
        )
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__loader__ = loader
        module.__spec__ = SimpleNamespace(
            origin=str(path),
            loader=loader,
        )
        return module

    root_module = bound_module("bu", root_file, "src/bu/__init__.py")
    recovery_module = bound_module(
        "bu.experiments.week8_exp2a_recovery",
        recovery_file,
        "src/bu/experiments/week8_exp2a_recovery.py",
    )
    monkeypatch.setitem(sys.modules, "bu", root_module)
    monkeypatch.setitem(
        sys.modules,
        "bu.experiments.week8_exp2a_recovery",
        recovery_module,
    )
    raw_module = SimpleNamespace(
        admitted_source_bytes=lambda raw, tree, relative: sources[relative],
        admitted_git_blob=lambda raw, tree, relative: "a" * 40,
    )
    rows = R._validate_loaded_controller_modules({}, raw_module)
    assert [row["module_id"] for row in rows] == [
        "bu",
        "bu.experiments.week8_exp2a_recovery",
    ]

    recovery_module.__spec__.loader.source_sha256 = "b" * 64
    with pytest.raises(R.RecoveryRefused, match="captured controller bytes"):
        R._validate_loaded_controller_modules({}, raw_module)
    recovery_module.__spec__.loader.source_sha256 = R.sha256_bytes(
        sources["src/bu/experiments/week8_exp2a_recovery.py"]
    )
    recovery_module.__spec__.loader.binding_marker = "unbound-loader"
    with pytest.raises(R.RecoveryRefused, match="bound controller source loader"):
        R._validate_loaded_controller_modules({}, raw_module)


@pytest.fixture(scope="module")
def recovery_worker() -> Any:
    """Load the actual sibling worker so contract records have one producer."""

    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "week8_exp2a_recovery_worker.py"
    )
    specification = importlib.util.spec_from_file_location(
        "week8_exp2a_recovery_worker_contract", path
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def relocated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    controller = workspace / "week8-recovery-controller-worktree"
    execution = workspace / "week8-e2a-execution-4515-worktree"
    controller.mkdir()
    execution.mkdir()
    python = workspace / "python.exe"
    site_packages = workspace / "site-packages"
    bootstrap = controller / "scripts" / "week8_exp2a_recovery_worker.py"
    inspector = controller / "scripts" / "week8_exp2a_recovery_inspector.py"
    entrypoint = controller / "scripts" / "week8_exp2a_recovery_entrypoint.py"
    raw_authority_helper = controller / "scripts" / "week8_recovery_raw_authority.py"
    module = controller / "src" / "bu" / "experiments" / "week8_exp2a_recovery.py"
    for path in (python, bootstrap, inspector, entrypoint, raw_authority_helper, module):
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(path, b"synthetic-controller-source")
    site_packages.mkdir()

    monkeypatch.setattr(R, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(R, "CONTROLLER_WORKTREE", controller)
    monkeypatch.setattr(R, "EXECUTION_WORKTREE", execution)
    monkeypatch.setattr(R, "PINNED_PYTHON", python)
    monkeypatch.setattr(R, "PINNED_BASE_PYTHON", python)
    monkeypatch.setattr(R, "PINNED_SITE_PACKAGES", site_packages)
    monkeypatch.setattr(R, "BOOTSTRAP_SCRIPT", bootstrap)
    monkeypatch.setattr(R, "INSPECTOR_SCRIPT", inspector)
    monkeypatch.setattr(R, "ENTRYPOINT_SCRIPT", entrypoint)
    monkeypatch.setattr(R, "RAW_AUTHORITY_HELPER", raw_authority_helper)
    monkeypatch.setattr(
        R,
        "EXPECTED_RAW_AUTHORITY_HELPER_SHA256",
        sha256_file(raw_authority_helper),
    )
    monkeypatch.setattr(R, "CONTROLLER_MODULE", module)
    monkeypatch.setattr(R, "RUNTIME_TEMP", workspace / "runtime-temp")
    monkeypatch.setattr(
        R, "INSPECTOR_RUNTIME_TEMP", workspace / "inspector-runtime-temp"
    )
    monkeypatch.setattr(R, "RECOVERY_ROOT", workspace / "recovery")
    monkeypatch.setattr(R, "RECOVERY_COPY_ROOT", workspace / "recovery-copy")
    monkeypatch.setenv(R.ENTRYPOINT_GATE_ENVIRONMENT_NAME, "synthetic-entrypoint-gate")
    monkeypatch.setattr(R.Plan, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(
        R.Plan, "COMMON_LEASE_ROOT", workspace / "week7-production-control"
    )
    finalization_guard = R._finalization_guard_path()
    finalization_guard.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(finalization_guard, b"\0")
    monkeypatch.setattr(R.P, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(R.P, "OUTPUT_ROOT", workspace / "output")
    monkeypatch.setattr(R.P, "SYNC_ROOT", workspace / "sync")
    monkeypatch.setattr(R.P, "STAGING_ROOT", workspace / "staging")
    for path in (R.P.OUTPUT_ROOT, R.P.SYNC_ROOT, R.P.STAGING_ROOT):
        path.mkdir(parents=True)
    return workspace


def _base(record_type: str) -> dict[str, Any]:
    return {
        **R._base_record(record_type),
        "status": "synthetic",
    }


def _worker_contract_invocation(
    relocated: Path,
    recovery_worker: Any,
) -> tuple[dict[str, Any], str]:
    recovery_worker.RECOVERY_ROOT = R.RECOVERY_ROOT
    recovery_worker.RECOVERY_COPY_ROOT = R.RECOVERY_COPY_ROOT
    recovery_worker.RUNTIME_TEMP = R.RUNTIME_TEMP
    recovery_worker.BOOTSTRAP_SCRIPT = R.BOOTSTRAP_SCRIPT
    recovery_worker.RAW_AUTHORITY_HELPER = R.RAW_AUTHORITY_HELPER
    recovery_worker.EXPECTED_RAW_AUTHORITY_HELPER_SHA256 = sha256_file(
        R.RAW_AUTHORITY_HELPER
    )
    recovery_worker.EXPECTED_CHILD_BOOTSTRAP_LITERAL_SHA256 = (
        R.CHILD_BOOTSTRAP_LITERAL_SHA256
    )
    R.RUNTIME_TEMP.mkdir(parents=True, exist_ok=True)
    git_executable = relocated / "git.exe"
    atomic_write_bytes(git_executable, b"synthetic-git-executable")
    claim_left, claim_right = R._record_paths(R.BOOTSTRAP_CLAIM_FILE)
    native_startup = _synthetic_native_startup()
    compact_binding = _synthetic_compact_preimport_binding(
        entrypoint_sha256=sha256_file(R.ENTRYPOINT_SCRIPT),
        raw_helper_sha256=sha256_file(R.RAW_AUTHORITY_HELPER),
        raw_record_digest="b" * 64,
        controller_tree_digest="c" * 64,
        execution_tree_digest="d" * 64,
        git_runtime_inventory_digest="e" * 64,
        site_packages_inventory_digest="f" * 64,
        native_startup=native_startup,
    )
    authority = {
        "controller_worktree": {
            "path": str(R.CONTROLLER_WORKTREE.resolve()),
            "git_commit": "1" * 40,
            "detached": False,
        },
        "execution_worktree": {
            "path": str(R.EXECUTION_WORKTREE.resolve()),
            "git_commit": R.EXECUTION_COMMIT,
            "detached": True,
        },
        "controller_module": {
            "path": str(R.CONTROLLER_MODULE.resolve()),
            "sha256": sha256_file(R.CONTROLLER_MODULE),
        },
        "bootstrap_worker": {
            "path": str(R.BOOTSTRAP_SCRIPT.resolve()),
            "sha256": sha256_file(R.BOOTSTRAP_SCRIPT),
        },
        "recovery_inspector": {
            "path": str(R.INSPECTOR_SCRIPT.resolve()),
            "sha256": sha256_file(R.INSPECTOR_SCRIPT),
        },
        "recovery_entrypoint": {
            "path": str(R.ENTRYPOINT_SCRIPT.resolve()),
            "sha256": sha256_file(R.ENTRYPOINT_SCRIPT),
        },
        "raw_authority_helper": {
            "path": str(R.RAW_AUTHORITY_HELPER.resolve()),
            "sha256": sha256_file(R.RAW_AUTHORITY_HELPER),
        },
        "preimport_authority": compact_binding,
        "preimport_authority_record": {
            "raw_authority_schema_version": 4,
            "native_startup": native_startup,
        },
        "pinned_python": {
            "path": str(R.PINNED_PYTHON.resolve()),
            "sha256": sha256_file(R.PINNED_PYTHON),
        },
        "base_python": {
            "path": str(R.PINNED_BASE_PYTHON.resolve()),
            "sha256": sha256_file(R.PINNED_BASE_PYTHON),
        },
        "git_executable": {
            "path": str(git_executable.resolve()),
            "sha256": sha256_file(git_executable),
        },
        "git_runtime": {},
        "loaded_controller_modules": [
            {
                "module_id": "bu",
                "source_path": str(R.CONTROLLER_MODULE.resolve()),
                "source_sha256": sha256_file(R.CONTROLLER_MODULE),
                "git_blob": "e" * 40,
            },
            {
                "module_id": "bu.experiments.week8_exp2a_recovery",
                "source_path": str(R.CONTROLLER_MODULE.resolve()),
                "source_sha256": sha256_file(R.CONTROLLER_MODULE),
                "git_blob": "f" * 40,
            },
        ],
    }
    controller_process = {
        "pid": os.getpid(),
        "kernel_executable_path": authority["base_python"]["path"],
        "kernel_executable_sha256": authority["base_python"]["sha256"],
        "creation_time_100ns": 1,
        "base_interpreter": dict(authority["base_python"]),
    }
    recovery_worker._parent_process_attestation = lambda observed_authority: {
        "pid": os.getppid(),
        "parent_pid": controller_process["pid"],
        "kernel_executable_path": observed_authority["pinned_python"]["path"],
        "kernel_executable_sha256": observed_authority["pinned_python"]["sha256"],
        "creation_time_100ns": 1,
        "pinned_launcher": dict(observed_authority["pinned_python"]),
    }
    recovery_worker._worker_process_attestation = lambda observed_authority: {
        "pid": os.getpid(),
        "kernel_executable_path": observed_authority["base_python"]["path"],
        "kernel_executable_sha256": observed_authority["base_python"]["sha256"],
        "creation_time_100ns": 2,
        "base_interpreter": dict(observed_authority["base_python"]),
    }
    prelaunch = {"synthetic": "old-checkpoint-bound"}
    child_transport = {
        "child_transport_schema_version": (
            recovery_worker.CHILD_TRANSPORT_SCHEMA_VERSION
        ),
        "transport": "verified_source_stdin",
        "logical_path": str(recovery_worker.BOOTSTRAP_SCRIPT.resolve()),
        "source_sha256": authority["bootstrap_worker"]["sha256"],
        "raw_helper_sha256": (
            recovery_worker.EXPECTED_RAW_AUTHORITY_HELPER_SHA256
        ),
        "bootstrap_literal_sha256": (
            recovery_worker.EXPECTED_CHILD_BOOTSTRAP_LITERAL_SHA256
        ),
        "bundle_sha256": "0" * 64,
    }
    recovery_worker.__transport_source_sha256__ = child_transport[
        "source_sha256"
    ]
    recovery_worker.__transport_bundle_sha256__ = child_transport[
        "bundle_sha256"
    ]
    payload = {
        **R._base_record("bootstrap_invocation"),
        "status": "authorized_once",
        "incident": {
            "record_digest": "2" * 64,
            "file_sha256": "3" * 64,
            "inventory_digest": "4" * 64,
        },
        "epoch001_terminal": {
            "record_digest": "5" * 64,
            "file_sha256": "6" * 64,
        },
        "transition_intent": {
            "record_digest": "7" * 64,
            "file_sha256": "8" * 64,
        },
        "transition_completion": {
            "record_digest": "9" * 64,
            "file_sha256": "a" * 64,
        },
        "authority": authority,
        "controller_process": controller_process,
        "runtime_temp": R._runtime_temp_directory_identity(
            R.RUNTIME_TEMP, what="synthetic recovery runtime temp"
        ),
        "child_transport": child_transport,
        "prelaunch_state": prelaunch,
        "prelaunch_state_digest": R.sha256_bytes(R._canonical(prelaunch)),
        "claim_paths": {
            "original_path": str(claim_left.resolve()),
            "copy_path": str(claim_right.resolve()),
            "exclusive": True,
        },
        "automatic_retry_allowed": False,
    }
    invocation = R._publish_twins_exclusive(R.BOOTSTRAP_INVOCATION_FILE, payload)
    invocation_sha = sha256_file(
        R._record_paths(R.BOOTSTRAP_INVOCATION_FILE)[0]
    )
    recovery_worker._validate_invocation_shape(invocation)
    return invocation, invocation_sha


def _publish_worker_contract_claim(
    recovery_worker: Any,
    invocation: dict[str, Any],
    invocation_sha: str,
    *,
    twins: int,
) -> tuple[dict[str, Any], str]:
    claim = recovery_worker._seal(
        recovery_worker._claim_payload(invocation, invocation_sha)
    )
    paths = R._record_paths(R.BOOTSTRAP_CLAIM_FILE)
    for path in paths[:twins]:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, claim)
    return claim, sha256_file(paths[0])


def _publish_worker_contract_terminal(
    recovery_worker: Any,
    invocation: dict[str, Any],
    invocation_sha: str,
    claim: dict[str, Any],
    claim_sha: str,
    *,
    claim_twins_complete: bool,
    terminal_twins: int,
    status: str,
) -> dict[str, Any]:
    empty_sha256 = R.sha256_bytes(b"")
    output_capture = {
        "stdout": {
            "sha256": empty_sha256,
            "byte_count": 0,
            "write_count": 0,
        },
        "stderr": {
            "sha256": empty_sha256,
            "byte_count": 0,
            "write_count": 0,
        },
    }
    operational = (
        {
            "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
            "lease_token": NEW_TOKEN,
            "report_sha256": "b" * 64,
            "script_sha256": invocation["authority"]["bootstrap_worker"]["sha256"],
            "output_capture": output_capture,
        }
        if status == "complete"
        else {"error_type": "SyntheticRefusal", "reason_sha256": "c" * 64}
    )
    terminal = recovery_worker._seal(
        recovery_worker._terminal_payload(
            status=status,
            invocation=invocation,
            invocation_sha=invocation_sha,
            claim=claim,
            claim_sha=claim_sha,
            claim_twins_complete=claim_twins_complete,
            operational_result=operational,
        )
    )
    for path in R._record_paths(R.BOOTSTRAP_TERMINAL_FILE)[:terminal_twins]:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, terminal)
    return terminal


def test_fixed_identity_and_cli_have_no_caller_paths() -> None:
    assert R.EXECUTION_COMMIT == "4515d5165756c8d1669d38d2ee854fa1051b1017"
    assert R.OLD_LEASE_TOKEN == "c66ea75437c043ba9a1113e0a31d2f8d"
    assert R.OLD_LEASE_PID == 48960
    assert R.ORPHAN_JOB_ID == "178f4ef3ae1e-s1001"
    assert R.ORPHAN_CHILD_PID == 29480
    assert R.HIDDEN_PARTIAL_NAME == ".178f4ef3ae1e-s1001.19rl_x0_.partial"
    assert R.RECOVERY_SCHEMA_VERSION == 3
    assert R.BOOTSTRAP_CONTRACT_SCHEMA_VERSION == 4
    assert R.CHILD_TRANSPORT_SCHEMA_VERSION == 1
    assert R.RUNTIME_TEMP.name == (
        "week8-exp2a-recovery-runtime-2026-09-02-attempt-001"
    )
    parser = R._parser()
    choices = next(
        action.choices
        for action in parser._actions
        if getattr(action, "choices", None)
    )
    assert set(choices) == {
        "adjudicate",
        "recover",
        "seal",
        "status",
        "monitor",
        "finalize",
        "report",
        "figures",
    }
    with pytest.raises(SystemExit):
        parser.parse_args(["recover", "--output-root", "elsewhere"])


def test_controller_and_worker_pin_the_same_recovery_runtime_temp() -> None:
    worker_source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "week8_exp2a_recovery_worker.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(worker_source)
    worker_runtime_names = [
        node.value.right.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "RUNTIME_TEMP"
            for target in node.targets
        )
        and isinstance(node.value, ast.BinOp)
        and isinstance(node.value.right, ast.Constant)
        and isinstance(node.value.right.value, str)
    ]
    assert worker_runtime_names == [R.RUNTIME_TEMP.name]


def test_controller_and_worker_share_raw_schema_4_authority_without_duplicate_git(
    relocated: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: Any,
) -> None:
    git_executable = relocated / "git.exe"
    atomic_write_bytes(git_executable, b"synthetic-resolved-git")
    source_bytes = {
        "src/bu/experiments/week8_exp2a_recovery.py": (
            R.CONTROLLER_MODULE.read_bytes()
        ),
        "scripts/week8_exp2a_recovery_worker.py": R.BOOTSTRAP_SCRIPT.read_bytes(),
        "scripts/week8_exp2a_recovery_inspector.py": R.INSPECTOR_SCRIPT.read_bytes(),
        "scripts/week8_exp2a_recovery_entrypoint.py": R.ENTRYPOINT_SCRIPT.read_bytes(),
        "scripts/week8_recovery_raw_authority.py": R.RAW_AUTHORITY_HELPER.read_bytes(),
    }
    native_startup = _synthetic_native_startup()
    raw = {
        "raw_authority_schema_version": 4,
        "record_digest": "1" * 64,
        "native_startup": native_startup,
        "controller": {
            "path": str(R.CONTROLLER_WORKTREE.resolve()),
            "git_commit": "2" * 40,
            "detached": False,
            "worktree_inventory_digest": "3" * 64,
        },
        "execution": {
            "path": str(R.EXECUTION_WORKTREE.resolve()),
            "git_commit": R.EXECUTION_COMMIT,
            "detached": True,
            "worktree_inventory_digest": "4" * 64,
        },
        "raw_authority_helper": {
            "path": str(R.RAW_AUTHORITY_HELPER.resolve()),
            "sha256": sha256_file(R.RAW_AUTHORITY_HELPER),
        },
        "runtime": {
            "pinned_python": {
                "path": str(R.PINNED_PYTHON.resolve()),
                "sha256": sha256_file(R.PINNED_PYTHON),
            },
            "pinned_base_python": {
                "path": str(R.PINNED_BASE_PYTHON.resolve()),
                "sha256": sha256_file(R.PINNED_BASE_PYTHON),
            },
            "pinned_site_packages": {"inventory_digest": "5" * 64},
        },
        "git": {
            "path": str(git_executable.resolve()),
            "sha256": sha256_file(git_executable),
        },
        "git_runtime": {"inventory_digest": "6" * 64},
    }
    gate = {
        "entrypoint_gate_schema_version": 4,
        "entrypoint": {
            "path": str(R.ENTRYPOINT_SCRIPT.resolve()),
            "sha256": sha256_file(R.ENTRYPOINT_SCRIPT),
        },
        "raw_authority_helper": dict(raw["raw_authority_helper"]),
        "raw_authority": raw,
    }
    raw_module = ModuleType("synthetic_raw_authority")
    raw_module.admitted_source_bytes = (  # type: ignore[attr-defined]
        lambda observed, tree, relative: source_bytes[relative]
    )
    raw_module.admitted_git_blob = (  # type: ignore[attr-defined]
        lambda observed, tree, relative: "e" * 40
    )
    monkeypatch.setitem(sys.modules, R.RAW_AUTHORITY_MODULE_NAME, raw_module)
    monkeypatch.setattr(R, "_validate_controller_runtime", lambda: gate)
    monkeypatch.setattr(R, "__file__", str(R.CONTROLLER_MODULE))
    loaded_modules = [
        {
            "module_id": "bu",
            "source_path": str(R.CONTROLLER_MODULE.resolve()),
            "source_sha256": sha256_file(R.CONTROLLER_MODULE),
            "git_blob": "e" * 40,
        },
        {
            "module_id": "bu.experiments.week8_exp2a_recovery",
            "source_path": str(R.CONTROLLER_MODULE.resolve()),
            "source_sha256": sha256_file(R.CONTROLLER_MODULE),
            "git_blob": "f" * 40,
        },
    ]
    monkeypatch.setattr(
        R,
        "_validate_loaded_controller_modules",
        lambda observed, module: loaded_modules,
    )
    authority = R._controller_authority()
    assert set(authority) == {
        "controller_worktree",
        "execution_worktree",
        "controller_module",
        "bootstrap_worker",
        "recovery_inspector",
        "recovery_entrypoint",
        "raw_authority_helper",
        "preimport_authority",
        "preimport_authority_record",
        "pinned_python",
        "base_python",
        "git_executable",
        "git_runtime",
        "loaded_controller_modules",
    }
    assert authority["git_executable"] == {
        "path": str(git_executable.resolve()),
        "sha256": sha256_file(git_executable),
    }
    assert authority["loaded_controller_modules"] == loaded_modules
    assert authority["preimport_authority_record"] is raw
    assert authority["preimport_authority"]["raw_authority_schema_version"] == 4
    assert authority["preimport_authority"]["entrypoint_schema_version"] == 4
    assert authority["preimport_authority"] == _synthetic_compact_preimport_binding(
        entrypoint_sha256=sha256_file(R.ENTRYPOINT_SCRIPT),
        raw_helper_sha256=sha256_file(R.RAW_AUTHORITY_HELPER),
        raw_record_digest=raw["record_digest"],
        controller_tree_digest=raw["controller"]["worktree_inventory_digest"],
        execution_tree_digest=raw["execution"]["worktree_inventory_digest"],
        git_runtime_inventory_digest=raw["git_runtime"]["inventory_digest"],
        site_packages_inventory_digest=raw["runtime"]["pinned_site_packages"][
            "inventory_digest"
        ],
        native_startup=native_startup,
    )
    recovery_worker._validate_authority_shape(authority)


def test_full_static_downstream_authority_revalidates_all_recorded_sources(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package_init = R.CONTROLLER_WORKTREE / "src" / "bu" / "__init__.py"
    package_init.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(package_init, b"# synthetic package\n")
    source_paths = {
        "src/bu/__init__.py": package_init,
        "src/bu/experiments/week8_exp2a_recovery.py": R.CONTROLLER_MODULE,
        "scripts/week8_exp2a_recovery_worker.py": R.BOOTSTRAP_SCRIPT,
        "scripts/week8_exp2a_recovery_inspector.py": R.INSPECTOR_SCRIPT,
        "scripts/week8_exp2a_recovery_entrypoint.py": R.ENTRYPOINT_SCRIPT,
        "scripts/week8_recovery_raw_authority.py": R.RAW_AUTHORITY_HELPER,
    }
    source_bytes = {
        relative: path.read_bytes() for relative, path in source_paths.items()
    }
    native_startup = _synthetic_native_startup()
    raw = {
        "raw_authority_schema_version": 4,
        "record_digest": "1" * 64,
        "native_startup": native_startup,
        "raw_authority_helper": {
            "path": str(R.RAW_AUTHORITY_HELPER.resolve()),
            "sha256": R.sha256_bytes(
                source_bytes["scripts/week8_recovery_raw_authority.py"]
            ),
        },
        "controller": {
            "path": str(R.CONTROLLER_WORKTREE.resolve()),
            "git_commit": "2" * 40,
            "detached": False,
            "worktree_inventory_digest": "3" * 64,
        },
        "execution": {
            "path": str(R.EXECUTION_WORKTREE.resolve()),
            "git_commit": R.EXECUTION_COMMIT,
            "detached": True,
            "worktree_inventory_digest": "4" * 64,
        },
        "runtime": {
            "pinned_python": {
                "path": str(R.PINNED_PYTHON.resolve()),
                "sha256": sha256_file(R.PINNED_PYTHON),
            },
            "pinned_base_python": {
                "path": str(R.PINNED_BASE_PYTHON.resolve()),
                "sha256": sha256_file(R.PINNED_BASE_PYTHON),
            },
            "pinned_site_packages": {"inventory_digest": "5" * 64},
        },
        "git": {
            "path": str((relocated / "git.exe").resolve()),
            "sha256": "6" * 64,
        },
        "git_runtime": {"inventory_digest": "7" * 64},
    }
    atomic_write_bytes(relocated / "git.exe", b"synthetic-git")

    def identity(relative: str, path: Path) -> dict[str, str]:
        return {
            "path": str(path.resolve()),
            "sha256": R.sha256_bytes(source_bytes[relative]),
        }

    authority = {
        "controller_worktree": {
            key: raw["controller"][key]
            for key in ("path", "git_commit", "detached")
        },
        "execution_worktree": {
            key: raw["execution"][key]
            for key in ("path", "git_commit", "detached")
        },
        "controller_module": identity(
            "src/bu/experiments/week8_exp2a_recovery.py", R.CONTROLLER_MODULE
        ),
        "bootstrap_worker": identity(
            "scripts/week8_exp2a_recovery_worker.py", R.BOOTSTRAP_SCRIPT
        ),
        "recovery_inspector": identity(
            "scripts/week8_exp2a_recovery_inspector.py", R.INSPECTOR_SCRIPT
        ),
        "recovery_entrypoint": identity(
            "scripts/week8_exp2a_recovery_entrypoint.py", R.ENTRYPOINT_SCRIPT
        ),
        "raw_authority_helper": identity(
            "scripts/week8_recovery_raw_authority.py", R.RAW_AUTHORITY_HELPER
        ),
        "preimport_authority": _synthetic_compact_preimport_binding(
            entrypoint_sha256=R.sha256_bytes(
                source_bytes["scripts/week8_exp2a_recovery_entrypoint.py"]
            ),
            raw_helper_sha256=raw["raw_authority_helper"]["sha256"],
            raw_record_digest=raw["record_digest"],
            controller_tree_digest=raw["controller"][
                "worktree_inventory_digest"
            ],
            execution_tree_digest=raw["execution"][
                "worktree_inventory_digest"
            ],
            git_runtime_inventory_digest=raw["git_runtime"]["inventory_digest"],
            site_packages_inventory_digest=raw["runtime"][
                "pinned_site_packages"
            ]["inventory_digest"],
            native_startup=native_startup,
        ),
        "preimport_authority_record": raw,
        "pinned_python": dict(raw["runtime"]["pinned_python"]),
        "base_python": dict(raw["runtime"]["pinned_base_python"]),
        "git_executable": dict(raw["git"]),
        "git_runtime": raw["git_runtime"],
        "loaded_controller_modules": [
            {
                "module_id": "bu",
                "source_path": str(package_init.resolve()),
                "source_sha256": R.sha256_bytes(
                    source_bytes["src/bu/__init__.py"]
                ),
                "git_blob": "8" * 40,
            },
            {
                "module_id": "bu.experiments.week8_exp2a_recovery",
                "source_path": str(R.CONTROLLER_MODULE.resolve()),
                "source_sha256": R.sha256_bytes(
                    source_bytes[
                        "src/bu/experiments/week8_exp2a_recovery.py"
                    ]
                ),
                "git_blob": "8" * 40,
            },
        ],
    }
    raw_module = SimpleNamespace(
        revalidate_recorded_static_authority=lambda observed, config, **kwargs: observed,
        admitted_source_bytes=lambda observed, tree, relative: source_bytes[
            relative
        ],
        admitted_git_blob=lambda observed, tree, relative: "8" * 40,
    )
    monkeypatch.setattr(R, "_load_static_raw_authority_module", lambda: raw_module)
    incident = {"authority": authority}
    assert R._assert_current_static_controller_authority(incident) is raw

    authority["loaded_controller_modules"][1]["source_sha256"] = "9" * 64
    with pytest.raises(R.RecoveryRefused, match="row differs from raw authority"):
        R._assert_current_static_controller_authority(incident)


def test_twin_records_are_strict_independent_and_divergence_refuses(
    relocated: Path,
) -> None:
    document = R._publish_twins(R.INCIDENT_FILE, _base("incident"))
    loaded, digest = R._load_twins(R.INCIDENT_FILE, record_type="incident")
    assert loaded == document
    assert digest == sha256_file(R._record_paths(R.INCIDENT_FILE)[0])
    left, right = R._record_paths(R.INCIDENT_FILE)
    assert not left.samefile(right)
    right.write_text("{}\n", encoding="utf-8")
    with pytest.raises(R.RecoveryRefused, match="twins differ"):
        R._load_twins(R.INCIDENT_FILE, record_type="incident")


def test_each_recovery_twin_refuses_an_external_hard_link(tmp_path: Path) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    alias = tmp_path / "external-alias.json"
    atomic_write_bytes(left, b"{}\n")
    atomic_write_bytes(right, b"{}\n")
    os.link(left, alias)
    with pytest.raises(R.RecoveryRefused, match="independent plain file"):
        R._same_bytes(left, right, what="synthetic")


def test_all_recovery_twin_publications_have_one_filesystem_winner(
    relocated: Path,
) -> None:
    payload = _base("incident")
    for path in R._record_paths(R.INCIDENT_FILE):
        R._ensure_recovery_root(path.parent)
    barrier = threading.Barrier(2)

    def publish() -> str:
        barrier.wait(timeout=5)
        try:
            R._publish_twins(R.INCIDENT_FILE, payload)
        except R.RecoveryRefused:
            return "refused"
        return "published"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(lambda _: publish(), range(2)))
    assert results == ["published", "refused"]
    R._load_twins(R.INCIDENT_FILE, record_type="incident")


def test_bootstrap_invocation_twins_are_one_use_and_exclusive(
    relocated: Path,
) -> None:
    payload = {
        **R._base_record("bootstrap_invocation"),
        "status": "synthetic",
    }
    first = R._publish_twins_exclusive(R.BOOTSTRAP_INVOCATION_FILE, payload)
    assert first["record_digest"] == R._seal(payload)["record_digest"]
    with pytest.raises(R.RecoveryRefused, match="one-use record already exists"):
        R._publish_twins_exclusive(R.BOOTSTRAP_INVOCATION_FILE, payload)


def test_bootstrap_rechecks_authority_immediately_before_safe_spawn(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actions: list[str] = []
    authority = {
        "bootstrap_worker": {
            "path": str(R.BOOTSTRAP_SCRIPT.resolve()),
            "sha256": "a" * 64,
        },
        "base_python": {
            "path": str(Path(sys._base_executable).resolve()),
            "sha256": "f" * 64,
        },
    }
    incident = {"authority": authority}
    invocation = {"record_digest": "1" * 64}
    claim = {
        "record_digest": "2" * 64,
        "worker": {
            "pid": 5678,
            "parent_pid": 1234,
            "parent_process": {"parent_pid": os.getpid()},
        },
    }
    empty_output_capture = {
        stream: {
            "sha256": R.sha256_bytes(b""),
            "byte_count": 0,
            "write_count": 0,
        }
        for stream in ("stdout", "stderr")
    }
    terminal = {
        "record_digest": "3" * 64,
        "operational_result": {"output_capture": empty_output_capture},
    }
    monkeypatch.setattr(
        R,
        "_load_adjudication",
        lambda: (incident, "4" * 64, {"record_digest": "5" * 64}, "6" * 64),
    )
    monkeypatch.setattr(
        R, "_load_transition_completion", lambda: ({"record_digest": "7" * 64}, "8" * 64)
    )
    monkeypatch.setattr(
        R,
        "_load_twins",
        lambda name, record_type: ({"record_digest": "9" * 64}, "0" * 64),
    )
    states = [
        {"state": "not_invoked"},
        {
            "state": "terminal_complete",
            "claim": claim,
            "terminal": terminal,
            "terminal_file_sha256": "f" * 64,
        },
    ]
    monkeypatch.setattr(R, "_bootstrap_state", lambda **kwargs: states.pop(0))

    def observed_authority() -> dict[str, Any]:
        actions.append("authority")
        return authority

    monkeypatch.setattr(R, "_controller_authority", observed_authority)
    child_bundle = b'{"synthetic":"verified-worker-source"}'
    child_transport = {
        "child_transport_schema_version": R.CHILD_TRANSPORT_SCHEMA_VERSION,
        "transport": "verified_source_stdin",
        "logical_path": str(R.BOOTSTRAP_SCRIPT.resolve()),
        "source_sha256": "a" * 64,
        "raw_helper_sha256": R.EXPECTED_RAW_AUTHORITY_HELPER_SHA256,
        "bootstrap_literal_sha256": R.CHILD_BOOTSTRAP_LITERAL_SHA256,
        "bundle_sha256": R.sha256_bytes(child_bundle),
    }
    monkeypatch.setattr(
        R,
        "_verified_child_bundle",
        lambda **kwargs: (child_bundle, child_transport),
    )
    monkeypatch.setattr(
        R,
        "_prepare_empty_runtime_temp",
        lambda path, what: R.RUNTIME_TEMP,
    )
    R.RUNTIME_TEMP.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        R,
        "_controller_process_attestation",
        lambda observed: {"synthetic": "controller-process"},
    )
    monkeypatch.setattr(R, "_bootstrap_prelaunch_state", lambda: {})
    monkeypatch.setattr(R, "_bootstrap_invocation_payload", lambda *args: {})

    def publish(name: str, payload: object) -> dict[str, str]:
        actions.append("publish-invocation")
        return invocation

    monkeypatch.setattr(R, "_publish_twins_exclusive", publish)
    monkeypatch.setattr(
        R,
        "_sanitized_subprocess_environment",
        lambda runtime, **kwargs: {"SAFE": "1"},
    )

    output = {
        "bootstrap_schema_version": 4,
        "status": "complete",
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "lease_token": NEW_TOKEN,
        "report_sha256": "b" * 64,
        "script_sha256": "a" * 64,
        "invocation_record_digest": invocation["record_digest"],
        "invocation_file_sha256": "d" * 64,
        "claim_record_digest": claim["record_digest"],
        "claim_file_sha256": "e" * 64,
        "terminal_record_digest": terminal["record_digest"],
        "terminal_file_sha256": "f" * 64,
        "output_capture": empty_output_capture,
        "scientific_values_emitted": False,
    }

    class Process:
        pid = 1234
        returncode = 0

        def communicate(self, *, input: bytes) -> tuple[bytes, bytes]:
            assert input == child_bundle
            return (
                json.dumps(output, sort_keys=True, separators=(",", ":")).encode(),
                b"",
            )

    def popen(*args: Any, **kwargs: Any) -> Process:
        actions.append("spawn")
        assert args[0] == [
            str(R.PINNED_PYTHON),
            "-I",
            "-S",
            "-B",
            "-X",
            "utf8",
            "-c",
            R.CHILD_BOOTSTRAP_LITERAL,
        ]
        assert str(R.BOOTSTRAP_SCRIPT) not in args[0]
        assert kwargs["stdin"] is R.subprocess.PIPE
        assert kwargs["text"] is False
        return Process()

    monkeypatch.setattr(R.subprocess, "Popen", popen)

    def digest(path: Path) -> str:
        if Path(path) == R.BOOTSTRAP_SCRIPT:
            return "a" * 64
        names = {
            R.BOOTSTRAP_INVOCATION_FILE: "d" * 64,
            R.BOOTSTRAP_CLAIM_FILE: "e" * 64,
        }
        return names.get(Path(path).name, "f" * 64)

    monkeypatch.setattr(R, "sha256_file", digest)
    result = R._invoke_bootstrap()
    assert result["lease_token"] == NEW_TOKEN
    assert actions == [
        "authority",
        "publish-invocation",
        "authority",
        "spawn",
    ]


def test_inspector_child_uses_verified_stdin_and_dash_c_not_script_execution(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = R.INSPECTOR_RUNTIME_TEMP
    runtime.mkdir(parents=True, exist_ok=True)
    bundle = b'{"synthetic":"verified-inspector-source"}'
    transport = {
        "bundle_sha256": R.sha256_bytes(bundle),
        "source_sha256": "1" * 64,
    }
    monkeypatch.setattr(
        R, "_prepare_empty_runtime_temp", lambda path, what: runtime
    )
    monkeypatch.setattr(
        R,
        "_verified_child_bundle",
        lambda **kwargs: (bundle, transport),
    )
    monkeypatch.setattr(
        R,
        "_sanitized_subprocess_environment",
        lambda path, **kwargs: {"SAFE": "1"},
    )
    expected = {"status": "complete"}
    monkeypatch.setattr(R, "_validate_inspector_material", lambda value: expected)

    def run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        assert command == [
            str(R.PINNED_PYTHON),
            "-I",
            "-S",
            "-B",
            "-X",
            "utf8",
            "-c",
            R.CHILD_BOOTSTRAP_LITERAL,
        ]
        assert str(R.INSPECTOR_SCRIPT) not in command
        assert kwargs["input"] == bundle
        assert kwargs["text"] is False
        return SimpleNamespace(
            returncode=0,
            stdout=b'{"status":"complete"}\n',
            stderr=b"",
        )

    monkeypatch.setattr(R.subprocess, "run", run)
    assert R._run_old_source_inspector() == expected


@pytest.mark.parametrize(
    "case", ["valid", "stderr", "malformed", "extra", "duplicate", "unsafe_flags", "oversized", "unknown_type"]
)
def test_inspector_process_refusal_exposes_only_bounded_operational_fingerprints(
    relocated: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], case: str,
) -> None:
    secret = "SYNTHETIC_PRIVATE_VALUE_MUST_NOT_ESCAPE"
    reason_sha = R.sha256_bytes(secret.encode())
    child = {
        "inspector_schema_version": 1, "status": "refused",
        "error_type": "InspectorRefused", "reason_sha256": reason_sha,
        "scientific_values_emitted": False, "production_mutation_performed": False,
    }
    if case == "extra":
        child["value"] = secret
    elif case == "unsafe_flags":
        child["scientific_values_emitted"] = True
    elif case == "unknown_type":
        child["error_type"] = secret
    stdout = (json.dumps(child, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if case == "malformed":
        stdout = secret.encode()
    elif case == "duplicate":
        stdout = stdout.replace(b'{', b'{"status":"refused",', 1)
    elif case == "oversized":
        stdout = secret.encode() * 200
    stderr = secret.encode() if case == "stderr" else b""
    returncode = 0 if case == "stderr" else 2
    monkeypatch.setattr(R, "_validate_controller_runtime", lambda: {"command": "status"})
    monkeypatch.setattr(R, "status", R._run_old_source_inspector)
    monkeypatch.setattr(R, "_prepare_empty_runtime_temp", lambda path, what: relocated)
    monkeypatch.setattr(R, "_verified_child_bundle", lambda **kwargs: (b"fixture", {"bundle_sha256": "1" * 64}))
    monkeypatch.setattr(R, "_sanitized_subprocess_environment", lambda *args, **kwargs: {})
    monkeypatch.setattr(R.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=returncode, stdout=stdout, stderr=stderr
    ))
    assert R.main(["status"]) == 2
    output = capsys.readouterr().out
    assert secret not in output
    result = json.loads(output)
    assert result["status"] == "refused"
    assert result["automatic_retry_allowed"] is False
    assert result["scientific_values_emitted"] is False
    old_message = (
        f"old-source inspector refused; stdout SHA256={R.sha256_bytes(stdout)}, "
        f"stderr SHA256={R.sha256_bytes(stderr)}"
    )
    assert result["error_sha256"] == R.sha256_bytes(old_message.encode())
    assert 1 <= len(result["controller_locations"]) <= 8
    assert any(row["function"] == "_run_old_source_inspector" for row in result["controller_locations"])
    assert all(set(row) == {"function", "line"} and type(row["line"]) is int and row["line"] > 0 for row in result["controller_locations"])
    assert result["inspector_failure"] == {
        "returncode": returncode,
        "stdout": {"bytes": len(stdout), "sha256": R.sha256_bytes(stdout)},
        "stderr": {"bytes": len(stderr), "sha256": R.sha256_bytes(stderr)},
        "inspector_refusal": {"error_type": "InspectorRefused", "reason_sha256": reason_sha}
            if case in {"valid", "stderr"} else None,
    }


def test_spawned_worker_identity_binds_pid_and_controller_parent() -> None:
    class Process:
        pid = 1234

    claim = {
        "worker": {
            "pid": 5678,
            "parent_pid": 1234,
            "parent_process": {"parent_pid": os.getpid()},
        }
    }
    R._validate_spawned_worker_identity(claim, Process())  # type: ignore[arg-type]
    claim["worker"]["parent_pid"] = 4321
    with pytest.raises(R.RecoveryRefused, match="spawned worker"):
        R._validate_spawned_worker_identity(claim, Process())  # type: ignore[arg-type]
    claim["worker"] = {
        "pid": 5678,
        "parent_pid": 1234,
        "parent_process": {"parent_pid": os.getpid() + 1},
    }
    with pytest.raises(R.RecoveryRefused, match="spawned worker"):
        R._validate_spawned_worker_identity(claim, Process())  # type: ignore[arg-type]


def test_record_claims_are_truthful_about_mechanical_validation() -> None:
    record = R._base_record("incident")
    assert record["scientific_outcomes_consulted"] is False
    assert record["scientific_values_emitted"] is False
    assert "scientific_files_opened" not in record
    assert "scientific_outcomes_read" not in record


def test_capture_cycle_runs_old_inspector_once_and_two_parent_rehashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    inspection = {"inspector_digest": "a" * 64}
    inventories = [{"capture": 1}, {"capture": 1}]

    def inspect() -> dict[str, Any]:
        calls.append("inspect")
        return inspection

    def capture(value: object) -> dict[str, int]:
        assert value is inspection
        calls.append("parent-rehash")
        return inventories.pop(0)

    monkeypatch.setattr(R, "_run_old_source_inspector", inspect)
    monkeypatch.setattr(R, "_capture_outcome_blind_inventory", capture)
    observed, source = R._capture_twice()
    assert observed == {"capture": 1}
    assert source is inspection
    assert calls == ["inspect", "parent-rehash", "parent-rehash"]


def test_sanitized_environment_uses_fixed_empty_project_temp_and_no_python_path(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", "synthetic-hostile-import-root")
    runtime = R._prepare_empty_runtime_temp(
        R.RUNTIME_TEMP, what="synthetic recovery runtime"
    )
    environment = R._sanitized_subprocess_environment(
        runtime, invocation_digest="a" * 64
    )
    assert environment["TEMP"] == str(runtime.resolve())
    assert environment["TMP"] == str(runtime.resolve())
    assert environment["TMPDIR"] == str(runtime.resolve())
    assert environment["BU_D161_INVOCATION_DIGEST"] == "a" * 64
    assert environment["GIT_CONFIG_COUNT"] == "1"
    assert environment["GIT_CONFIG_KEY_0"] == "safe.directory"
    assert environment["GIT_CONFIG_VALUE_0"] == str(R.EXECUTION_WORKTREE.resolve())
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["PYTHONSAFEPATH"] == "1"
    assert environment[R.ENTRYPOINT_GATE_ENVIRONMENT_NAME] == "synthetic-entrypoint-gate"
    assert "PYTHONPATH" not in environment
    atomic_write_bytes(runtime / "unexpected.tmp", b"x")
    with pytest.raises(R.RecoveryRefused, match="must be empty"):
        R._prepare_empty_runtime_temp(runtime, what="synthetic recovery runtime")


@pytest.mark.parametrize(
    ("unexpected_name", "unexpected_value"),
    [
        ("PYTHONSTARTUP", "hostile.py"),
        ("PYTHONHASHSEED", "0"),
        ("PYTHONDONTWRITEBYTECODE", "1"),
        ("PYTHONIOENCODING", "utf-8"),
        ("PYTHONNOUSERSITE", "1"),
        ("PYTHONSAFEPATH", "1"),
        ("PYTHONUTF8", "1"),
    ],
)
def test_controller_runtime_requires_exact_pinned_isolated_launch(
    relocated: Path, monkeypatch: pytest.MonkeyPatch,
    unexpected_name: str, unexpected_value: str,
) -> None:
    site_packages = R.PINNED_SITE_PACKAGES
    site_packages.mkdir(exist_ok=True)
    source = (R.CONTROLLER_WORKTREE / "src").resolve()
    expected_environment = {
        "PYTHONPATH": f"{source}{R.os.pathsep}{site_packages.resolve()}",
    }
    for name in tuple(R.os.environ):
        if name.upper().startswith("PYTHON"):
            monkeypatch.delenv(name, raising=False)
    for name, value in expected_environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(R.sys, "executable", str(R.PINNED_PYTHON))
    monkeypatch.setattr(R.sys, "_base_executable", str(R.PINNED_BASE_PYTHON))
    admitted_middle = [str((relocated / "stdlib").resolve())]
    monkeypatch.setattr(
        R.sys,
        "path",
        [str(source), *admitted_middle, str(site_packages.resolve())],
    )
    monkeypatch.setattr(
        R,
        "EXPECTED_PINNED_PYTHON_SHA256",
        sha256_file(R.PINNED_PYTHON),
    )
    monkeypatch.setattr(
        R,
        "EXPECTED_PINNED_BASE_PYTHON_SHA256",
        sha256_file(R.PINNED_BASE_PYTHON),
    )
    monkeypatch.setattr(
        R,
        "_controller_runtime_flags",
        lambda: {
            "dont_write_bytecode": True,
            "ignore_environment": True,
            "isolated": True,
            "no_site": True,
            "no_user_site": True,
            "safe_path": True,
            "utf8_mode": 1,
        },
    )
    gate = {
        "synthetic": "entrypoint-gate",
        "raw_authority": {
            "runtime": {
                "preimport_sys_path_digest": R.sha256_bytes(
                    R._canonical_ascii(admitted_middle)
                )
            }
        },
    }
    monkeypatch.setattr(R, "_validate_entrypoint_gate", lambda: gate)
    assert R._validate_controller_runtime() is gate
    monkeypatch.setenv(unexpected_name, unexpected_value)
    with pytest.raises(R.RecoveryRefused, match="environment is not exact"):
        R._validate_controller_runtime()


def test_frozen_old_token_normal_release_path_always_refuses(
    relocated: Path,
) -> None:
    path = R._old_normal_release_path()
    path.parent.mkdir(parents=True)
    atomic_write_bytes(path, b"synthetic-forbidden-release")
    with pytest.raises(R.RecoveryRefused, match="forbidden normal release"):
        R._assert_no_old_normal_release()


def test_windows_liveness_refusal_precedes_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        R.windows_liveness,
        "capture_windows_process_stability",
        lambda recorded: {"synthetic": "ambiguous"},
    )

    def refuse(snapshot: object) -> dict[str, object]:
        raise R.windows_liveness.ProcessLivenessError("ambiguous process handle")

    monkeypatch.setattr(R.windows_liveness, "assert_windows_stability_gate", refuse)
    with pytest.raises(R.RecoveryRefused, match="liveness refused"):
        R._quiescent_liveness()


def test_windows_liveness_is_mocked_and_requires_quiescent_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []

    def capture(recorded: object) -> dict[str, object]:
        captured.extend(recorded)  # type: ignore[arg-type]
        return {
            "stability": {
                "verdict": "pass",
                "controller_launcher_required": True,
                "controller_launcher_stable": True,
                "controller_launcher": {"relation": "controller_launcher"},
            }
        }

    monkeypatch.setattr(R.windows_liveness, "capture_windows_process_stability", capture)
    monkeypatch.setattr(
        R.windows_liveness,
        "assert_windows_stability_gate",
        lambda snapshot: snapshot,
    )
    result = R._quiescent_liveness()
    assert result["stability"]["verdict"] == "pass"
    assert [(row.record_id, row.pid, row.role) for row in captured] == [
        ("epoch001_lease_owner", 48960, "owner"),
        ("orphan_completed_worker", 29480, "worker"),
    ]


def test_d161_liveness_requires_the_exact_d162_two_process_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    single_process_pass = {
        "stability": {
            "verdict": "pass",
            "controller_launcher_required": False,
            "controller_launcher_stable": True,
            "controller_launcher": None,
        }
    }
    monkeypatch.setattr(
        R.windows_liveness,
        "capture_windows_process_stability",
        lambda recorded: single_process_pass,
    )
    monkeypatch.setattr(
        R.windows_liveness,
        "assert_windows_stability_gate",
        lambda snapshot: snapshot,
    )
    with pytest.raises(R.RecoveryRefused, match="passing stability gate"):
        R._quiescent_liveness()


def test_partial_is_moved_unchanged_and_copied_independently(
    relocated: Path,
) -> None:
    source = R.P.SYNC_ROOT / "jobs" / R.HIDDEN_PARTIAL_NAME
    source.mkdir(parents=True)
    atomic_write_bytes(source / "one.bin", b"one")
    atomic_write_bytes(source / "nested" / "two.bin", b"two")
    before = R._plain_tree_inventory(source, what="synthetic partial")
    result = R._quarantine_partial(source, {"inventory": before})
    original, copied = R._quarantine_paths()
    assert not source.exists()
    assert R._plain_tree_inventory(original, what="original") == before
    assert R._plain_tree_inventory(copied, what="copy") == before
    assert not (original / "one.bin").samefile(copied / "one.bin")
    assert result["independent_copy"] is True
    assert result["inventory_digest"] == R._tree_digest(before)


def test_partial_subset_rejects_any_different_byte(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = relocated / "local"
    partial = relocated / "partial"
    local.mkdir()
    partial.mkdir()
    for index in range(15):
        atomic_write_bytes(local / f"f{index:02d}.bin", f"value-{index}".encode())
    for index in range(11):
        value = b"different" if index == 5 else f"value-{index}".encode()
        atomic_write_bytes(partial / f"f{index:02d}.bin", value)
    with pytest.raises(R.RecoveryRefused, match="byte-identical subset"):
        R._validate_partial_subset(local, partial)


def test_recovery_mutation_order_is_intent_archive_quarantine_completion_then_worker(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actions: list[str] = []
    authority = {"controller": "synthetic"}
    inventory = {"jobs": {"hidden_partial": {"inventory": []}}}
    incident = {
        "authority": authority,
        "inventory": inventory,
        "record_digest": "1" * 64,
        "inventory_digest": "2" * 64,
    }
    monkeypatch.setattr(
        R,
        "_load_adjudication",
        lambda: (incident, "3" * 64, {"status": "externally_interrupted"}, "4" * 64),
    )
    monkeypatch.setattr(R, "_record_presence", lambda name: False)
    monkeypatch.setattr(R.P, "_receipt_present", lambda phase: False)
    def controller_authority() -> dict[str, str]:
        actions.append("authority")
        return authority

    monkeypatch.setattr(R, "_controller_authority", controller_authority)

    def capture() -> tuple[dict[str, Any], dict[str, Any]]:
        actions.append("revalidate")
        return inventory, {"inspector_digest": "9" * 64}

    monkeypatch.setattr(R, "_capture_twice", capture)
    monkeypatch.setattr(R, "_transition_material", lambda *args: {"auth": True})
    monkeypatch.setattr(
        R,
        "_quiescent_liveness",
        lambda: actions.append("liveness")
        or {"stability": {"verdict": "pass"}},
    )

    def publish(name: str, payload: object) -> dict[str, Any]:
        actions.append(f"publish:{name}")
        return {"record_digest": ("5" if "intent" in name else "6") * 64}

    monkeypatch.setattr(R, "_publish_twins", publish)
    monkeypatch.setattr(R, "sha256_file", lambda path: "7" * 64)
    monkeypatch.setattr(
        R.Supervisor, "_lease_guard_path", lambda active, name: relocated / "guard"
    )

    @contextmanager
    def lock(path: Path):
        actions.append("lock:enter")
        yield
        actions.append("lock:exit")

    monkeypatch.setattr(R.Supervisor, "_lease_transition_lock", lock)
    monkeypatch.setattr(
        R, "_archive_orphan_lease", lambda active, archive: actions.append("archive")
    )

    def quarantine(source: Path, expected: object) -> dict[str, Any]:
        actions.append("quarantine")
        return {"inventory_digest": "8" * 64}

    monkeypatch.setattr(R, "_quarantine_partial", quarantine)

    def bootstrap() -> dict[str, Any]:
        actions.append("bootstrap")
        return {"lease_token": NEW_TOKEN}

    monkeypatch.setattr(R, "_invoke_bootstrap", bootstrap)

    def complete(value: object) -> dict[str, Any]:
        actions.append("validate-complete")
        return {
            "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
            "new_token": NEW_TOKEN,
        }

    monkeypatch.setattr(R, "_validate_lower_completion", complete)
    result = R.recover()
    assert result["status"] == "recovery_complete_ready_to_seal"
    assert actions == [
        "authority",
        "lock:enter",
        "revalidate",
        "authority",
        "liveness",
        f"publish:{R.TRANSITION_INTENT_FILE}",
        "archive",
        "quarantine",
        f"publish:{R.TRANSITION_COMPLETION_FILE}",
        "lock:exit",
        "bootstrap",
        "validate-complete",
    ]


@pytest.mark.parametrize(
    "bootstrap_state",
    (
        "claimed_worker_dead_second_interruption",
        "partial_claim",
        "partial_terminal",
        "partial_claim_and_terminal",
        "partial_claim_terminal_refused",
        "partial_claim_terminal_complete",
        "terminal_refused",
    ),
)
def test_terminal_or_partial_history_is_a_hard_stop_without_bootstrap_reentry(
    monkeypatch: pytest.MonkeyPatch,
    bootstrap_state: str,
) -> None:
    incident = {"authority": {}, "inventory": {}}
    monkeypatch.setattr(
        R,
        "_load_adjudication",
        lambda: (incident, "1" * 64, {}, "2" * 64),
    )
    monkeypatch.setattr(
        R,
        "_record_presence",
        lambda name: name
        in {R.TRANSITION_INTENT_FILE, R.TRANSITION_COMPLETION_FILE},
    )
    monkeypatch.setattr(R.P, "_receipt_present", lambda phase: False)
    monkeypatch.setattr(R, "_load_transition_completion", lambda: ({}, "3" * 64))
    monkeypatch.setattr(
        R,
        "_bootstrap_state",
        lambda: {"state": bootstrap_state},
    )
    monkeypatch.setattr(
        R,
        "_invoke_bootstrap",
        lambda: pytest.fail("a second bootstrap attempt must never occur"),
    )
    with pytest.raises(R.RecoveryRefused, match="no second recovery"):
        R.recover()


@pytest.mark.parametrize(
    ("claim_twins", "terminal_twins", "terminal_status", "expected_state"),
    (
        (1, 0, None, "partial_claim"),
        (2, 1, "refused", "partial_terminal"),
        (2, 1, "complete", "partial_terminal"),
        (1, 1, "refused", "partial_claim_and_terminal"),
        (1, 1, "complete", "partial_claim_and_terminal"),
        (1, 2, "refused", "partial_claim_terminal_refused"),
        (1, 2, "complete", "partial_claim_terminal_complete"),
        (2, 2, "refused", "terminal_refused"),
        (2, 2, "complete", "terminal_complete"),
    ),
)
def test_worker_produced_records_drive_exact_controller_state_classification(
    relocated: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: Any,
    claim_twins: int,
    terminal_twins: int,
    terminal_status: str | None,
    expected_state: str,
) -> None:
    invocation, invocation_sha = _worker_contract_invocation(
        relocated, recovery_worker
    )
    claim, claim_sha = _publish_worker_contract_claim(
        recovery_worker,
        invocation,
        invocation_sha,
        twins=claim_twins,
    )
    if terminal_status is not None:
        _publish_worker_contract_terminal(
            recovery_worker,
            invocation,
            invocation_sha,
            claim,
            claim_sha,
            claim_twins_complete=claim_twins == 2,
            terminal_twins=terminal_twins,
            status=terminal_status,
        )
    monkeypatch.setattr(
        R,
        "_load_bootstrap_invocation",
        lambda: (invocation, invocation_sha),
    )
    monkeypatch.setattr(
        R,
        "_claimed_worker_lifecycle",
        lambda *args, **kwargs: pytest.fail(
            "partial or terminal evidence must be classified before liveness"
        ),
    )
    state = R._bootstrap_state()
    assert state["state"] == expected_state
    assert state["automatic_retry_allowed"] is False
    if expected_state == "terminal_complete":
        assert not R._is_permanent_bootstrap_stop(expected_state)
    else:
        assert R._is_permanent_bootstrap_stop(expected_state)


def test_worker_partial_claim_terminal_binding_must_say_twins_incomplete(
    relocated: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: Any,
) -> None:
    invocation, invocation_sha = _worker_contract_invocation(
        relocated, recovery_worker
    )
    claim, claim_sha = _publish_worker_contract_claim(
        recovery_worker, invocation, invocation_sha, twins=1
    )
    terminal = _publish_worker_contract_terminal(
        recovery_worker,
        invocation,
        invocation_sha,
        claim,
        claim_sha,
        claim_twins_complete=False,
        terminal_twins=2,
        status="refused",
    )
    payload = {key: value for key, value in terminal.items() if key != "record_digest"}
    payload["claim"] = {**payload["claim"], "twins_complete": True}
    malformed = recovery_worker._seal(payload)
    for path in R._record_paths(R.BOOTSTRAP_TERMINAL_FILE):
        path.unlink()
        atomic_write_json(path, malformed)
    monkeypatch.setattr(
        R,
        "_load_bootstrap_invocation",
        lambda: (invocation, invocation_sha),
    )
    with pytest.raises(R.RecoveryRefused, match="bind its claim exactly"):
        R._bootstrap_state()


def test_right_only_worker_claim_is_also_a_permanent_partial_claim(
    relocated: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: Any,
) -> None:
    invocation, invocation_sha = _worker_contract_invocation(
        relocated, recovery_worker
    )
    claim, _ = _publish_worker_contract_claim(
        recovery_worker, invocation, invocation_sha, twins=1
    )
    left, right = R._record_paths(R.BOOTSTRAP_CLAIM_FILE)
    left.unlink()
    atomic_write_json(right, claim)
    monkeypatch.setattr(
        R,
        "_load_bootstrap_invocation",
        lambda: (invocation, invocation_sha),
    )
    state = R._bootstrap_state()
    assert state["state"] == "partial_claim"
    assert R._is_permanent_bootstrap_stop(state["state"])


def test_worker_claimed_live_process_is_not_a_second_interruption(
    relocated: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: Any,
) -> None:
    invocation, invocation_sha = _worker_contract_invocation(
        relocated, recovery_worker
    )
    _publish_worker_contract_claim(
        recovery_worker, invocation, invocation_sha, twins=2
    )
    monkeypatch.setattr(
        R,
        "_load_bootstrap_invocation",
        lambda: (invocation, invocation_sha),
    )
    monkeypatch.setattr(
        R, "_claimed_worker_lifecycle", lambda value, process=None: "running"
    )
    monkeypatch.setattr(
        R,
        "_lower_reports",
        lambda: pytest.fail("a live worker must be classified before reports"),
    )
    state = R._bootstrap_state()
    assert state["state"] == "claimed_worker_running"
    assert not R._is_permanent_bootstrap_stop(state["state"])


def test_worker_claim_with_lower_complete_and_no_terminal_remains_sealable(
    relocated: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: Any,
) -> None:
    invocation, invocation_sha = _worker_contract_invocation(
        relocated, recovery_worker
    )
    _publish_worker_contract_claim(
        recovery_worker, invocation, invocation_sha, twins=2
    )
    monkeypatch.setattr(
        R,
        "_load_bootstrap_invocation",
        lambda: (invocation, invocation_sha),
    )
    monkeypatch.setattr(
        R, "_claimed_worker_lifecycle", lambda value, process=None: "dead"
    )
    monkeypatch.setattr(
        R,
        "_lower_reports",
        lambda: {
            NEW_TOKEN: (
                relocated / "report.json",
                relocated / "report-copy.json",
                {"status": "complete"},
                "d" * 64,
            )
        },
    )
    incident = {"authority": {"synthetic": True}}
    material = {
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "new_token": NEW_TOKEN,
        "lower_report": {"sha256": "d" * 64},
        "events": {"chain_digest": "e" * 64},
        "jobs": {"tree_digest_set": "f" * 64},
    }
    controller_process = {"pid": os.getpid()}
    liveness = {"sha256": "a" * 64, "report": {"synthetic": True}}
    runtime_temp = {
        "path": str(R.RUNTIME_TEMP.resolve()),
        "entry_count": 0,
        "inventory_digest": R.sha256_bytes(R._canonical([])),
    }
    monkeypatch.setattr(
        R, "_load_adjudication", lambda: (incident, "1" * 64, {}, "2" * 64)
    )
    monkeypatch.setattr(
        R,
        "_assert_current_controller_authority",
        lambda value: value["authority"],
    )
    monkeypatch.setattr(R, "_validate_lower_completion", lambda value: material)
    monkeypatch.setattr(
        R, "_postmortem_runtime_temp_attestation", lambda expected: runtime_temp
    )
    monkeypatch.setattr(
        R,
        "_postmortem_worker_death_proof",
        lambda value, authority: (controller_process, liveness),
    )
    state = R._bootstrap_state()
    assert state["state"] == "postmortem_seal_required"
    assert state["material"] == material
    assert state["runtime_temp"] == runtime_temp
    assert not R._is_permanent_bootstrap_stop(state["state"])

    monkeypatch.setattr(
        R,
        "_record_presence",
        lambda name: name == R.TRANSITION_COMPLETION_FILE,
    )
    monkeypatch.setattr(R, "_bootstrap_state", lambda: state)
    assert R._second_interruption_present() is False


def test_status_does_not_mask_corrupt_evidence_after_complete_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        R,
        "_record_presence",
        lambda name: name == R.TRANSITION_COMPLETION_FILE,
    )
    monkeypatch.setattr(R, "_load_transition_completion", lambda: ({}, "1" * 64))
    monkeypatch.setattr(R, "_bootstrap_state", lambda: {"state": "terminal_complete"})
    monkeypatch.setattr(R, "_load_adjudication", lambda: ({}, "2", {}, "3"))
    monkeypatch.setattr(
        R,
        "_validate_lower_completion",
        lambda incident: (_ for _ in ()).throw(
            R.RecoveryRefused("corrupt complete terminal evidence")
        ),
    )
    with pytest.raises(R.RecoveryRefused, match="corrupt complete terminal"):
        R.status()


def test_preadjudication_status_is_the_full_independent_read_only_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory = {
        "inventory_digest": "1" * 64,
        "events": {
            "count": 299,
            "started_job_ids": [f"started-{index}" for index in range(150)],
            "synced_job_ids": [f"synced-{index}" for index in range(149)],
        },
        "jobs": {
            "local_completed": [{} for _ in range(150)],
            "durable_completed": [{} for _ in range(149)],
            "untouched_job_ids": [f"untouched-{index}" for index in range(111)],
            "hidden_partial": {"file_count": 11},
        },
    }
    inspection = {
        "inspector_digest": "2" * 64,
        "jobs": {"hidden_partial": {"orphan_local_file_count": 15}},
    }
    liveness = {"stability": {"verdict": "pass"}, "synthetic": True}
    calls: list[str] = []
    monkeypatch.setattr(R, "_record_presence", lambda name: False)
    monkeypatch.setattr(
        R,
        "_capture_twice",
        lambda: (calls.append("inspect") or (inventory, inspection)),
    )
    monkeypatch.setattr(
        R,
        "_quiescent_liveness",
        lambda: (calls.append("liveness") or liveness),
    )

    result = R.status()

    assert calls == ["inspect", "liveness"]
    assert result == {
        "command": "status",
        "state": "not_adjudicated",
        "independent_inspection_performed": True,
        "mechanical_source_validation_performed": True,
        "inventory_digest": "1" * 64,
        "inspector_digest": "2" * 64,
        "liveness_digest": R.sha256_bytes(R._canonical(liveness)),
        "liveness_verdict": "pass",
        "counts": {
            "events": 299,
            "started": 150,
            "synced": 149,
            "local_completed": 150,
            "durable_completed": 149,
            "untouched": 111,
            "partial_files": 11,
            "orphan_local_files": 15,
        },
        "automatic_retry_allowed": False,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }


def _locked_git_gate() -> dict[str, object]:
    git = R.PINNED_GIT.resolve(strict=True)
    runtime = R.PINNED_GIT_RUNTIME_ROOT.resolve(strict=True)
    return {
        "raw_authority": {
            "git": {"path": str(git), "sha256": R.EXPECTED_PINNED_GIT_SHA256},
            "git_runtime": {
                "path": str(runtime),
                "inventory_digest": R.EXPECTED_PINNED_GIT_RUNTIME_INVENTORY_DIGEST,
                "file_count": R.EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT,
                "directory_count": R.EXPECTED_PINNED_GIT_RUNTIME_DIRECTORY_COUNT,
                "total_bytes": R.EXPECTED_PINNED_GIT_RUNTIME_TOTAL_BYTES,
                "stability_observations": 2,
                "retained_read_lock_count": R.EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT,
            },
        }
    }


def _managed_downstream_environment_items() -> tuple[tuple[str, str], ...]:
    exact_names = {
        "BU_RUNRECORD_GIT_EXECUTABLE",
        "LC_ALL",
        "PAGER",
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
    }
    return tuple(
        (name, value)
        for name, value in os.environ.items()
        if name.upper().startswith("GIT_") or name.upper() in exact_names
    )


def test_downstream_git_environment_is_exact_locked_and_restores_only_managed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "operator-controlled")
    monkeypatch.setenv("BU_SYNTHETIC_UNMANAGED", "before")
    before = _managed_downstream_environment_items()
    desired = R._downstream_git_environment(_locked_git_gate())

    with R._verified_downstream_git_environment(_locked_git_gate()):
        observed = dict(_managed_downstream_environment_items())
        assert observed == desired
        assert Path(os.environ["PATH"].split(os.pathsep)[0]).samefile(
            R.PINNED_GIT_RUNTIME_ROOT
        )
        os.environ["BU_SYNTHETIC_UNMANAGED"] = "changed-inside"

    assert _managed_downstream_environment_items() == before
    assert os.environ["BU_SYNTHETIC_UNMANAGED"] == "changed-inside"


def test_downstream_git_environment_has_one_exact_safe_directory() -> None:
    environment = R._downstream_git_environment(_locked_git_gate())
    count = int(environment["GIT_CONFIG_COUNT"])
    entries = [
        (
            environment[f"GIT_CONFIG_KEY_{index}"],
            environment[f"GIT_CONFIG_VALUE_{index}"],
        )
        for index in range(count)
    ]

    assert [
        entry for entry in entries if entry[0].casefold() == "safe.directory"
    ] == [
        ("safe.directory", str(R.CONTROLLER_WORKTREE.resolve(strict=True)))
    ]


def test_downstream_git_environment_removes_and_restores_hostile_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("gIt_CoNfIg_PaRaMeTeRs", "hostile-but-preserved")
    before = _managed_downstream_environment_items()
    original = [
        item for item in before if item[0].upper() == "GIT_CONFIG_PARAMETERS"
    ]
    assert len(original) == 1

    with R._verified_downstream_git_environment(_locked_git_gate()):
        assert not any(
            name.upper() == "GIT_CONFIG_PARAMETERS" for name in os.environ
        )

    assert _managed_downstream_environment_items() == before
    assert [
        item
        for item in _managed_downstream_environment_items()
        if item[0].upper() == "GIT_CONFIG_PARAMETERS"
    ] == original


@pytest.mark.parametrize("exit_mode", ("handler-exception", "tamper"))
def test_downstream_git_environment_restores_after_exception_or_tamper(
    exit_mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "hostile-before-handler")
    before = _managed_downstream_environment_items()

    if exit_mode == "handler-exception":
        with pytest.raises(RuntimeError, match="synthetic handler failure"):
            with R._verified_downstream_git_environment(_locked_git_gate()):
                os.environ["GIT_PAGER"] = "tampered-before-exception"
                raise RuntimeError("synthetic handler failure")
    else:
        with pytest.raises(R.RecoveryRefused, match="changed its Git environment"):
            with R._verified_downstream_git_environment(_locked_git_gate()):
                os.environ["GIT_PAGER"] = "operator-pager"

    assert _managed_downstream_environment_items() == before


def test_downstream_git_environment_rejects_unlocked_runtime_record() -> None:
    gate = _locked_git_gate()
    gate["raw_authority"]["git_runtime"]["retained_read_lock_count"] = 93  # type: ignore[index]
    with pytest.raises(R.RecoveryRefused, match="locked raw authority"):
        R._downstream_git_environment(gate)


@pytest.mark.parametrize(
    ("command", "expected_kwargs"),
    [
        ("monitor", {}),
        (
            "finalize",
            {
                "expected_git_commit": "d" * 40,
                "expected_execution_commit": R.EXECUTION_COMMIT,
            },
        ),
        ("report", {"expected_git_commit": "d" * 40}),
        ("figures", {"expected_git_commit": "d" * 40}),
    ],
)
def test_postrecovery_controller_supplies_the_process_local_d166_capability(
    command: str,
    expected_kwargs: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incident = {"authority": {"controller_worktree": {"git_commit": "d" * 40}}}
    authority_calls: list[dict[str, object]] = []
    observed: list[dict[str, object]] = []
    monkeypatch.setattr(
        R,
        "_load_adjudication",
        lambda: (incident, "1" * 64, {}, "2" * 64),
    )
    monkeypatch.setattr(
        R,
        "_assert_current_controller_authority",
        lambda value: authority_calls.append(value) or value["authority"],
    )

    def handler(**kwargs: object) -> dict[str, object]:
        observed.append(kwargs)
        return {"command": command, "status": "synthetic-complete"}

    monkeypatch.setattr(R.P, command, handler)
    result = R._run_postrecovery_command(command, gate=_locked_git_gate())

    assert result["command"] == command
    assert authority_calls == [incident, incident]
    assert len(observed) == 1
    capability = observed[0].pop("_d166_capability")
    assert capability is R.P._D166_CONTROLLER_CAPABILITY
    assert observed == [expected_kwargs]


def test_postrecovery_real_runrecord_git_state_uses_captured_absolute_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incident = {"authority": {"controller_worktree": {"git_commit": "d" * 40}}}
    calls: list[tuple[tuple[str, ...], str, tuple[tuple[str, str], ...]]] = []
    outputs = {
        ("rev-parse", "HEAD"): b"d" * 40,
        ("rev-parse", "--abbrev-ref", "HEAD"): b"main",
        ("status", "--porcelain"): b"",
    }
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "hostile-before-runrecord")
    before = _managed_downstream_environment_items()
    monkeypatch.setattr(
        R,
        "_load_adjudication",
        lambda: (incident, "1" * 64, {}, "2" * 64),
    )
    monkeypatch.setattr(
        R,
        "_assert_current_controller_authority",
        lambda value: value["authority"],
    )

    def fake_run(
        argv: list[str],
        *,
        cwd: str,
        capture_output: bool,
        check: bool,
    ) -> SimpleNamespace:
        assert capture_output is True
        assert check is False
        arguments = tuple(argv[1:])
        calls.append((tuple(argv), cwd, _managed_downstream_environment_items()))
        return SimpleNamespace(stdout=outputs[arguments], returncode=0)

    monkeypatch.setattr(RR.subprocess, "run", fake_run)

    def handler(**kwargs: object) -> dict[str, object]:
        assert kwargs == {"_d166_capability": R.P._D166_CONTROLLER_CAPABILITY}
        state = RR.git_state()
        assert state == RR.GitState(commit="d" * 40, dirty=False, branch="main")
        return {"command": "monitor", "status": "synthetic-complete"}

    monkeypatch.setattr(R.P, "monitor", handler)
    result = R._run_postrecovery_command("monitor", gate=_locked_git_gate())

    captured_git = str(R.PINNED_GIT.resolve(strict=True))
    assert result == {"command": "monitor", "status": "synthetic-complete"}
    assert [call[0][1:] for call in calls] == list(outputs)
    assert {call[0][0] for call in calls} == {captured_git}
    assert all(Path(call[0][0]).is_absolute() for call in calls)
    assert {call[1] for call in calls} == {str(RR.PROJECT_ROOT)}
    assert all(
        dict(call[2])["BU_RUNRECORD_GIT_EXECUTABLE"] == captured_git
        for call in calls
    )
    assert all(
        not any(name.upper() == "GIT_CONFIG_PARAMETERS" for name, _ in call[2])
        for call in calls
    )
    assert _managed_downstream_environment_items() == before


def _event(
    sequence: int,
    previous: str | None,
    kind: str,
    job_id: str | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    return R.Plan._seal(
        {
            "event_schema_version": 1,
            "sequence": sequence,
            "previous_digest": previous,
            "execution_context_digest": CONTEXT,
            "kind": kind,
            "job_id": job_id,
            "data": data,
        },
        "event_digest",
    )


def _write_final_event_fixture(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    duplicate_new_start: bool = False,
) -> tuple[dict[str, tuple[dict[str, Any], str]], list[str]]:
    jobs = [f"job-{index:03d}" for index in range(261)]
    jobs[149] = R.ORPHAN_JOB_ID
    monkeypatch.setattr(
        R.Plan,
        "new_exp2a_jobs",
        lambda: tuple(SimpleNamespace(job_id=job_id) for job_id in jobs),
    )
    local_dir = R.P.OUTPUT_ROOT / R.Launch.EVENT_DIRECTORY
    copy_dir = R.P.SYNC_ROOT / R.Launch.EVENT_DIRECTORY
    local_dir.mkdir(parents=True)
    copy_dir.mkdir(parents=True)
    events: list[dict[str, Any]] = []

    def append(kind: str, job_id: str | None, data: dict[str, Any]) -> None:
        row = _event(
            len(events),
            None if not events else events[-1]["event_digest"],
            kind,
            job_id,
            data,
        )
        events.append(row)
        name = f"{row['sequence']:06d}.json"
        atomic_write_json(local_dir / name, row)
        atomic_write_json(copy_dir / name, row)

    sync = {
        "execution_digest": "e" * 64,
        "source_tree_digest": "f" * 64,
        "copy_evidence_digest": "9" * 64,
    }
    for job_id in jobs[:149]:
        append("attempt_started", job_id, {"checkpoint_digest": OLD_CHECKPOINT_DIGEST})
        append("job_synced", job_id, dict(sync))
    append(
        "attempt_started", jobs[149], {"checkpoint_digest": OLD_CHECKPOINT_DIGEST}
    )
    append("job_synced", jobs[149], dict(sync))
    for index, job_id in enumerate(jobs[150:]):
        if duplicate_new_start and index == 0:
            job_id = jobs[0]
        append("attempt_started", job_id, {"checkpoint_digest": NEW_CHECKPOINT_DIGEST})
        append("job_synced", job_id, dict(sync))
    append(
        "complete",
        None,
        {"synced_physical_fits": 261, "historical_sources_reverified": 155},
    )
    expected = dict(R.EXPECTED_HASHES)
    expected["old_event_stream"] = R._event_chain_digest(events[:299])
    expected["old_event_tail_file"] = sha256_file(local_dir / "000298.json")
    monkeypatch.setattr(R, "EXPECTED_HASHES", expected)
    checkpoints = {
        R.OLD_LEASE_TOKEN: (
            {
                "checkpoint_digest": OLD_CHECKPOINT_DIGEST,
                "execution_context_digest": CONTEXT,
            },
            "1" * 64,
        ),
        NEW_TOKEN: (
            {
                "checkpoint_digest": NEW_CHECKPOINT_DIGEST,
                "execution_context_digest": CONTEXT,
            },
            "2" * 64,
        ),
    }
    return checkpoints, jobs


def test_final_event_accounting_proves_150_reused_111_new_and_no_retraining(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoints, jobs = _write_final_event_fixture(relocated, monkeypatch)
    events, digest, new_token, started = R._final_events(checkpoints)
    assert len(events) == 523
    assert new_token == NEW_TOKEN
    assert len(started) == 261
    assert sum(token == R.OLD_LEASE_TOKEN for token in started.values()) == 150
    assert sum(token == NEW_TOKEN for token in started.values()) == 111
    assert started[R.ORPHAN_JOB_ID] == R.OLD_LEASE_TOKEN
    assert digest == R._event_chain_digest(events)
    assert set(started) == set(jobs)


def test_duplicate_start_in_continuation_is_retraining_and_refuses(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoints, _ = _write_final_event_fixture(
        relocated, monkeypatch, duplicate_new_start=True
    )
    with pytest.raises(R.RecoveryRefused, match="duplicate/unknown start"):
        R._final_events(checkpoints)


def test_epoch2_release_history_is_hash_and_full_checkpoint_lease_bound(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_local = relocated / "report.json"
    report_copy = relocated / "report-copy.json"
    atomic_write_json(report_local, {"synthetic": True})
    atomic_write_json(report_copy, {"synthetic": True})
    history = (
        R.Plan.COMMON_LEASE_ROOT
        / "leases"
        / "history"
        / f"{R.Plan.COMMON_LEASE_NAME}.{NEW_TOKEN}.released.json"
    )
    lease = {
        "schema_version": R.Supervisor.SUPERVISOR_SCHEMA_VERSION,
        "lease_name": R.Plan.COMMON_LEASE_NAME,
        "pid": 4321,
        "token": NEW_TOKEN,
        "timestamp": 1.0,
        "timestamp_utc": "2026-09-02T00:00:00Z",
    }
    history.parent.mkdir(parents=True)
    atomic_write_json(history, lease)
    checkpoint_path = R.P.OUTPUT_ROOT / R.Plan.START_DIRECTORY / f"{NEW_TOKEN}.json"
    checkpoint = {
        "lease": {
            "path": str(
                (
                    R.Plan.COMMON_LEASE_ROOT
                    / "leases"
                    / f"{R.Plan.COMMON_LEASE_NAME}.lease.json"
                ).resolve()
            ),
            "sha256": sha256_file(history),
            "name": R.Plan.COMMON_LEASE_NAME,
            "token": NEW_TOKEN,
            "started_at": lease["timestamp_utc"],
        }
    }
    report = {
        "exp2a_repair_launch_schema_version": 1,
        "status": "complete",
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "failure": None,
        "historical_retrained": False,
        "preflight": {
            "path": str((R.P.PREFLIGHT_ROOT / R.Launch.PREFLIGHT_FILE).resolve()),
            "sha256": R.EXPECTED_HASHES["preflight_report"],
        },
        "checkpoint": {"path": str(checkpoint_path.resolve()), "sha256": "2" * 64},
        "released_lease": {"token": NEW_TOKEN, "history_path": str(history)},
        "lease_release_failure": None,
    }
    monkeypatch.setattr(
        R,
        "_lower_reports",
        lambda: {NEW_TOKEN: (report_local, report_copy, report, "4" * 64)},
    )
    material = R._validate_new_lower_report(
        NEW_TOKEN, {NEW_TOKEN: (checkpoint, "2" * 64)}
    )
    assert material["released_lease_sha256"] == checkpoint["lease"]["sha256"]
    assert material["released_lease_record"] == lease
    checkpoint["lease"]["sha256"] = "0" * 64
    with pytest.raises(R.RecoveryRefused, match="checkpoint-bound"):
        R._validate_new_lower_report(
            NEW_TOKEN, {NEW_TOKEN: (checkpoint, "2" * 64)}
        )


def test_launch_payload_preserves_base_contract_and_adds_only_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        R.P,
        "_load_control",
        lambda commit, monitor_only: {"_file_sha256": "a" * 64},
    )
    completion = {
        "record_digest": "b" * 64,
        "new_lease_token": NEW_TOKEN,
        "checkpoints": {
            NEW_TOKEN: {
                "path": "second-checkpoint.json",
                "copy_path": "second-checkpoint-copy.json",
                "sha256": "c" * 64,
            }
        },
        "lower_report": {
            "path": "second-report.json",
            "copy_path": "second-report-copy.json",
            "sha256": "d" * 64,
            "released_lease": {
                "token": NEW_TOKEN,
                "history_path": "second.released.json",
            },
        },
    }
    payload = R._production_launch_payload(completion, "e" * 64)
    base_keys = {
        "expected_git_commit",
        "control_receipt_sha256",
        "lease_token",
        "checkpoint",
        "launch_report",
        "status",
        "lower_counts",
        "released_lease",
        "counts",
    }
    assert set(payload) == base_keys | {"recovery"}
    assert payload["expected_git_commit"] == R.EXECUTION_COMMIT
    assert payload["checkpoint"]["path"] == "second-checkpoint.json"
    assert payload["launch_report"]["path"] == "second-report.json"
    assert payload["lower_counts"] == {
        "executed": 111,
        "resumed": 150,
        "synced": 261,
        "total": 261,
    }


def test_completed_bootstrap_chain_is_bound_to_lower_completion(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = {"record_digest": "1" * 64}
    claim = {"record_digest": "2" * 64}
    terminal = {
        "record_digest": "3" * 64,
        "operational_result": {
            "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
            "lease_token": NEW_TOKEN,
            "report_sha256": "4" * 64,
        },
    }
    for name, document in (
        (R.BOOTSTRAP_INVOCATION_FILE, invocation),
        (R.BOOTSTRAP_CLAIM_FILE, claim),
        (R.BOOTSTRAP_TERMINAL_FILE, terminal),
    ):
        for path in R._record_paths(name):
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(path, document)
    monkeypatch.setattr(
        R,
        "_bootstrap_state",
        lambda: {
            "state": "terminal_complete",
            "invocation": invocation,
            "claim": claim,
            "terminal": terminal,
        },
    )
    material = {
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "new_token": NEW_TOKEN,
        "lower_report": {"sha256": "4" * 64},
    }
    bindings = R._validate_completed_bootstrap(material)
    assert set(bindings) == {"kind", "invocation", "claim", "terminal"}
    assert bindings["kind"] == "worker_terminal"
    assert all(
        bindings[key]["file_sha256"] == sha256_file(R._record_paths(name)[0])
        for name, key in (
            (R.BOOTSTRAP_INVOCATION_FILE, "invocation"),
            (R.BOOTSTRAP_CLAIM_FILE, "claim"),
            (R.BOOTSTRAP_TERMINAL_FILE, "terminal"),
        )
    )
    terminal["operational_result"]["lease_token"] = "e" * 32
    with pytest.raises(R.RecoveryRefused, match="revalidated lower completion"):
        R._validate_completed_bootstrap(material)
    monkeypatch.setattr(R, "_bootstrap_state", lambda: {"state": "partial_terminal"})
    with pytest.raises(R.RecoveryRefused, match="complete bootstrap record chain"):
        R._validate_completed_bootstrap(material)


def test_completion_payload_includes_revalidated_bootstrap_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = {
        "invocation": {"record_digest": "1" * 64, "file_sha256": "2" * 64},
        "claim": {"record_digest": "3" * 64, "file_sha256": "4" * 64},
        "terminal": {"record_digest": "5" * 64, "file_sha256": "6" * 64},
    }
    monkeypatch.setattr(
        R,
        "_load_transition_completion",
        lambda: ({"record_digest": "7" * 64}, "8" * 64),
    )
    observed: list[dict[str, Any]] = []
    monkeypatch.setattr(
        R,
        "_validate_completed_bootstrap",
        lambda material: observed.append(dict(material)) or bootstrap,
    )
    material = {
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "new_token": NEW_TOKEN,
        "checkpoints": {},
        "events": {"count": 523},
        "jobs": {"old_completed_unchanged": 150},
        "lower_report": {"sha256": "9" * 64},
    }
    incident = {
        "record_digest": "a" * 64,
        "inventory_digest": "b" * 64,
        "authority": {"controller_worktree": {"git_commit": "c" * 40}},
    }
    monkeypatch.setattr(R, "sha256_file", lambda path: "d" * 64)
    payload = R._completion_payload(material, incident)
    assert payload["bootstrap"] == bootstrap
    assert observed == [material]


def test_public_validator_accepts_payload_and_rejects_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = {"controller_worktree": {"git_commit": "a" * 40}}
    incident = {"record_digest": "1" * 64, "authority": authority}
    material = {"new_token": NEW_TOKEN}
    completion = {
        "controller_commit": "2" * 40,
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "new_lease_token": NEW_TOKEN,
        "events": {"count": 523},
        "jobs": {"old_completed_unchanged": 150},
    }
    expected = {"recovery": "exact"}
    monkeypatch.setattr(
        R, "_load_adjudication", lambda: (incident, "3" * 64, {}, "4" * 64)
    )
    monkeypatch.setattr(R, "_validate_lower_completion", lambda value: material)
    monkeypatch.setattr(
        R,
        "_validate_recovery_completion_record",
        lambda value, observed: (completion, "5" * 64),
    )
    monkeypatch.setattr(
        R, "_production_launch_payload", lambda value, digest: expected
    )
    static_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        R,
        "_assert_current_static_controller_authority",
        lambda value: static_calls.append(value) or authority,
    )
    monkeypatch.setattr(
        R,
        "_assert_current_controller_authority",
        lambda value: pytest.fail("supplied payload must not invoke the live gate"),
    )
    result = R.validate_completed_recovery(expected)
    assert result["counts"] == R.EXPECTED_RECOVERY_COUNTS
    assert result["scientific_values_emitted"] is False
    with pytest.raises(R.RecoveryRefused, match="caller-supplied"):
        R.validate_completed_recovery({"recovery": "drifted"})
    assert static_calls == [incident, incident]


def test_public_validator_without_payload_invokes_live_gate_not_static_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incident = {"record_digest": "1" * 64, "authority": {}}
    material = {"new_token": NEW_TOKEN}
    completion = {
        "controller_commit": "2" * 40,
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "new_lease_token": NEW_TOKEN,
        "events": {"count": 523},
        "jobs": {"old_completed_unchanged": 150},
    }
    live_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        R, "_load_adjudication", lambda: (incident, "3" * 64, {}, "4" * 64)
    )
    monkeypatch.setattr(
        R,
        "_assert_current_controller_authority",
        lambda value: live_calls.append(value) or {},
    )
    monkeypatch.setattr(
        R,
        "_assert_current_static_controller_authority",
        lambda value: pytest.fail("payload=None must invoke the live gate"),
    )
    monkeypatch.setattr(R, "_validate_lower_completion", lambda value: material)
    monkeypatch.setattr(
        R,
        "_validate_recovery_completion_record",
        lambda value, observed: (completion, "5" * 64),
    )
    monkeypatch.setattr(
        R, "_production_launch_payload", lambda value, digest: {"recovery": "exact"}
    )
    monkeypatch.setattr(
        R,
        "_validate_production_launch_receipt",
        lambda value, digest: {"_file_sha256": "6" * 64},
    )
    result = R.validate_completed_recovery()
    assert live_calls == [incident]
    assert result["launch_receipt_sha256"] == "6" * 64


def test_completion_validation_rejects_changed_controller_authority_before_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incident = {"authority": {"controller_worktree": {"git_commit": "a" * 40}}}
    monkeypatch.setattr(
        R, "_load_adjudication", lambda: (incident, "1" * 64, {}, "2" * 64)
    )
    monkeypatch.setattr(
        R,
        "_assert_current_static_controller_authority",
        lambda value: (_ for _ in ()).throw(
            R.RecoveryRefused("static controller authority differs")
        ),
    )
    monkeypatch.setattr(
        R,
        "_assert_current_controller_authority",
        lambda value: pytest.fail("supplied payload must not invoke the live gate"),
    )
    monkeypatch.setattr(
        R,
        "_validate_lower_completion",
        lambda value: pytest.fail("lower completion opened after authority drift"),
    )
    with pytest.raises(R.RecoveryRefused, match="static controller authority differs"):
        R.validate_completed_recovery({})


def test_recovery_monitor_material_is_terminal_only_and_standard_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpoints = {
        R.OLD_LEASE_TOKEN: (
            {"checkpoint_digest": OLD_CHECKPOINT_DIGEST},
            "1" * 64,
        ),
        NEW_TOKEN: (
            {"checkpoint_digest": NEW_CHECKPOINT_DIGEST},
            "2" * 64,
        ),
    }
    events = [{"event_digest": f"{index:064x}"} for index in range(523)]
    monkeypatch.setattr(R, "_load_adjudication", lambda: ({}, "a", {}, "b"))
    monkeypatch.setattr(
        R,
        "_load_transition_completion",
        lambda: ({"status": "ownership_transition_complete"}, "c" * 64),
    )
    monkeypatch.setattr(
        R,
        "_load_transition_records_only",
        lambda: pytest.fail("monitor must use the full transition validator"),
    )
    monkeypatch.setattr(R, "_checkpoint_documents", lambda: checkpoints)
    completed_material = {
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "new_token": NEW_TOKEN,
        "lower_report": {"sha256": "4" * 64},
    }
    monkeypatch.setattr(
        R, "_validate_lower_completion", lambda incident: completed_material
    )
    monkeypatch.setattr(
        R,
        "_final_events",
        lambda value: (events, "3" * 64, NEW_TOKEN, {}),
    )
    monkeypatch.setattr(
        R,
        "_validate_new_lower_report",
        lambda token, value: {"sha256": "4" * 64},
    )
    bootstrap_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        R,
        "_validate_completed_bootstrap",
        lambda material: bootstrap_calls.append(dict(material)) or {},
    )
    monkeypatch.setattr(
        R.P,
        "_load_control",
        lambda commit, monitor_only: {
            "receipt_paths": {"original": "control", "copy": "control-copy"},
            "_file_sha256": "5" * 64,
            "receipt_digest": "6" * 64,
        },
    )
    document = R.recovery_monitor_material()
    assert document["status"] == "complete"
    assert document["event_stream"]["event_count"] == 523
    assert document["counts"]["remaining"] == 0
    assert document["scientific_files_opened"] is True
    assert "snapshot_digest" in document
    assert bootstrap_calls == [completed_material]


def test_historical_orphan_lookup_is_exact_token_only(
    relocated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(R, "_load_transition_completion", lambda: ({}, "a" * 64))
    archive = relocated / "a" / "orphan.json"
    monkeypatch.setattr(R, "_orphan_archive_path", lambda: archive)
    lease = {
        "schema_version": R.Supervisor.SUPERVISOR_SCHEMA_VERSION,
        "lease_name": R.Plan.COMMON_LEASE_NAME,
        "pid": R.OLD_LEASE_PID,
        "token": R.OLD_LEASE_TOKEN,
        "timestamp": 1.0,
        "timestamp_utc": "2026-09-01T00:00:00Z",
    }
    archive.parent.mkdir(parents=True)
    atomic_write_json(archive, lease)
    hashes = dict(R.EXPECTED_HASHES)
    hashes["old_lease"] = sha256_file(archive)
    monkeypatch.setattr(R, "EXPECTED_HASHES", hashes)
    row = R.historical_orphan_lease_record(R.OLD_LEASE_TOKEN)
    assert row["token"] == R.OLD_LEASE_TOKEN
    assert row["started_at"] == lease["timestamp_utc"]
    with pytest.raises(R.RecoveryRefused, match="only the frozen token"):
        R.historical_orphan_lease_record("0" * 32)


def test_bootstrap_source_monkeypatches_only_two_frozen_launch_seams() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "week8_exp2a_recovery_worker.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    launch_attribute_writes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "Launch"
            ):
                launch_attribute_writes.append(target.attr)
    assert launch_attribute_writes == [
        "_historical_lease_record",
        "run_isolated_attempt",
        "_historical_lease_record",
        "run_isolated_attempt",
    ]


def test_cli_normalizes_validation_oserror_without_message_or_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "synthetic-validation-detail-must-not-be-emitted"
    monkeypatch.setattr(
        R, "_validate_controller_runtime", lambda: {"command": "status"}
    )
    monkeypatch.setattr(R, "status", lambda: (_ for _ in ()).throw(OSError(secret)))
    assert R.main(["status"]) == 2
    output = capsys.readouterr().out
    assert secret not in output
    document = json.loads(output)
    assert document["status"] == "refused"
    assert document["error_type"] == "OSError"
    assert [row["function"] for row in document["controller_locations"]] == ["main"]
    assert len(document["error_sha256"]) == 64
    assert document["scientific_values_emitted"] is False


def test_cli_refuses_entrypoint_gate_for_another_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        R, "_validate_controller_runtime", lambda: {"command": "status"}
    )
    monkeypatch.setattr(
        R,
        "recover",
        lambda: pytest.fail("mismatched entrypoint command reached recovery"),
    )
    assert R.main(["recover"]) == 2
    document = json.loads(capsys.readouterr().out)
    assert document["command"] == "recover"
    assert document["status"] == "refused"
    assert document["automatic_retry_allowed"] is False
