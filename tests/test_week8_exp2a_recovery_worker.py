"""Synthetic-only tests for the one-use D-161 recovery bootstrap.

No fixture opens production evidence.  Every record, lease, checkpoint and
quarantine tree is fabricated beneath ``tmp_path``.  The scientific launcher is
always replaced by a small operational double.
"""

from __future__ import annotations

import base64
import copy
import importlib.machinery
import importlib.util
import json
import logging
import os
import pickle
import subprocess
import sys
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "scripts" / "week8_exp2a_recovery_worker.py"
SPEC = importlib.util.spec_from_file_location("d161_recovery_worker_under_test", WORKER_PATH)
assert SPEC is not None and SPEC.loader is not None
W = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(W)
REAL_VALIDATE_STARTUP_IMPORT_ISOLATION = W._validate_startup_import_isolation
REAL_VALIDATE_DEFAULT_IMPORT_MACHINERY = W._validate_default_import_machinery
REAL_PARENT_PROCESS_ATTESTATION = W._parent_process_attestation
REAL_VALIDATE_ENTRYPOINT_GATE = W._validate_entrypoint_gate
RAW_HELPER_SOURCE = (ROOT / "scripts" / "week8_recovery_raw_authority.py").read_bytes()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(W._json_file_bytes(value))


def _base(record_type: str) -> dict[str, Any]:
    return {
        "recovery_schema_version": W.RECOVERY_SCHEMA_VERSION,
        "recovery_id": W.RECOVERY_ID,
        "decision_id": W.DECISION_ID,
        "record_type": record_type,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
    }


def _publish(name: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    document = W._seal(payload)
    for path in W._record_paths(name):
        _write_json(path, document)
    return document, W._sha_bytes(W._json_file_bytes(document))


def _replace_twins(name: str, document: dict[str, Any]) -> tuple[dict[str, Any], str]:
    sealed = W._seal({key: value for key, value in document.items() if key != "record_digest"})
    for path in W._record_paths(name):
        path.unlink(missing_ok=True)
        _write_json(path, sealed)
    return sealed, W._sha_bytes(W._json_file_bytes(sealed))


@pytest.fixture
def scenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    # Lifecycle/transport tests isolate relocation admission; real captured-loader
    # and frozen reader scopes have their own adversarial integration fixtures.
    relocation = {"relocation_schema_version": 1, "attestation_sha256": "a" * 64,
                  "policy_sha256": "b" * 64, "pair_count": 304, "document_count": 629,
                  "helpers": {"helper_schema_version": 1, "synthetic": True}}
    monkeypatch.setattr(W, "_worker_relocation_admission", lambda authority: nullcontext())
    monkeypatch.setattr(W, "_admitted_relocation", lambda: (None, None, copy.deepcopy(relocation)))
    # The worker starts under ``-I -S -B -X utf8`` before any execution-tree ``bu`` import.
    # Keep this fixture order-independent when another test module imported the
    # controller-tree package earlier in the same pytest interpreter.
    for name in tuple(sys.modules):
        if name == "bu" or name.startswith("bu."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    workspace = tmp_path / "workspace"
    controller = workspace / "controller"
    execution = workspace / "execution"
    recovery = workspace / "recovery"
    recovery_copy = workspace / "recovery-copy"
    output = workspace / "output"
    sync = workspace / "sync"
    preparation = workspace / "preparation"
    runtime_temp = workspace / "runtime-temp"

    controller_module = controller / "src" / "bu" / "experiments" / "week8_exp2a_recovery.py"
    controller_package = controller / "src" / "bu" / "__init__.py"
    bootstrap = controller / "scripts" / "week8_exp2a_recovery_worker.py"
    inspector = controller / "scripts" / "week8_exp2a_recovery_inspector.py"
    entrypoint = controller / "scripts" / "week8_exp2a_recovery_entrypoint.py"
    fit_child = controller / "scripts" / "week8_exp2a_recovery_fit_child.py"
    raw_authority_helper = controller / "scripts" / "week8_recovery_raw_authority.py"
    native_launcher = controller / "scripts" / "week8_recovery_native_launcher.ps1"
    pinned_pyvenv = workspace / "synthetic-venv" / "pyvenv.cfg"
    pinned_venv_scripts = pinned_pyvenv.parent / "Scripts"
    pinned_base_runtime = workspace / "synthetic-base-runtime"
    native_powershell = workspace / "synthetic-windows" / "powershell.exe"
    native_runtime = workspace / "synthetic-native-runtime"
    git_runtime = workspace / "tools" / "git-runtime"
    git_executable = git_runtime / "git.exe"
    for path, data in (
        (controller_module, b"controller-source\n"),
        (controller_package, b"# synthetic controller bu package\n"),
        (bootstrap, b"bootstrap-source\n"),
        (inspector, b"inspector-source\n"),
        (entrypoint, b"entrypoint-source\n"),
        (fit_child, b"fit-child-source\n"),
        (raw_authority_helper, RAW_HELPER_SOURCE),
        (native_launcher, b"# synthetic native launcher\r\n"),
        (pinned_pyvenv, b"synthetic pyvenv authority\r\n"),
        (pinned_venv_scripts / "python.exe", b"synthetic venv launcher\n"),
        (pinned_venv_scripts / "activate.bat", b"synthetic activation helper\r\n"),
        (pinned_base_runtime / "python.exe", b"synthetic base launcher\n"),
        (pinned_base_runtime / "Lib" / "os.py", b"# synthetic standard library\n"),
        (native_powershell, b"synthetic native PowerShell host\n"),
        (git_executable, b"synthetic-git-executable\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    execution_sources = {
        "src/bu/__init__.py": b"# captured synthetic execution package\n",
        "src/bu/experiments/__init__.py": b"# captured experiments package\n",
        "src/bu/experiments/week8_exp2a_production.py": (
            b"from pathlib import Path\nWORKSPACE_ROOT = Path(__file__).resolve().parents[4]\n"
            b"PREFLIGHT_ROOT = WORKSPACE_ROOT / 'preflight'\n"
            b"OUTPUT_ROOT = WORKSPACE_ROOT / 'output'\n"
            b"SYNC_ROOT = WORKSPACE_ROOT / 'sync'\n"
        ),
        "src/bu/experiments/week8_exp2a_repair_launch.py": (
            b"PREFLIGHT_FILE = 'week8_preflight_report.json'\n"
            b"def _historical_lease_record(token):\n    return {'token': token}\n"
            b"def launch_exp2a_repairs(**kwargs):\n    return kwargs\n"
        ),
    }
    for relative, data in execution_sources.items():
        path = execution / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    runtime_temp.mkdir(parents=True)
    native_runtime.mkdir(parents=True)
    (output / W.START_DIRECTORY).mkdir(parents=True)
    (sync / W.START_DIRECTORY).mkdir(parents=True)
    (sync / "jobs").mkdir(parents=True)
    (preparation / "original" / "receipts").mkdir(parents=True)
    (preparation / "copy" / "receipts").mkdir(parents=True)
    for root in (recovery, recovery_copy):
        (root / "records").mkdir(parents=True)

    monkeypatch.setattr(W, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(W, "CONTROLLER_WORKTREE", controller)
    monkeypatch.setattr(W, "EXECUTION_WORKTREE", execution)
    monkeypatch.setattr(W, "CONTROLLER_MODULE", controller_module)
    monkeypatch.setattr(W, "BOOTSTRAP_SCRIPT", bootstrap)
    monkeypatch.setattr(W, "INSPECTOR_SCRIPT", inspector)
    monkeypatch.setattr(W, "ENTRYPOINT_SCRIPT", entrypoint)
    monkeypatch.setattr(W, "FIT_CHILD_SCRIPT", fit_child)
    monkeypatch.setattr(W, "RAW_AUTHORITY_HELPER", raw_authority_helper)
    monkeypatch.setattr(
        W,
        "EXPECTED_RAW_AUTHORITY_HELPER_SHA256",
        W._sha_file(raw_authority_helper),
    )
    monkeypatch.setattr(W, "PINNED_PYTHON", Path(sys.executable))
    monkeypatch.setattr(W, "PINNED_BASE_PYTHON", Path(sys._base_executable))
    monkeypatch.setattr(W, "PINNED_BASE_RUNTIME", pinned_base_runtime)
    monkeypatch.setattr(W, "PINNED_PYVENV", pinned_pyvenv)
    monkeypatch.setattr(W, "PINNED_VENV_SCRIPTS", pinned_venv_scripts)
    monkeypatch.setattr(W, "NATIVE_LAUNCHER", native_launcher)
    monkeypatch.setattr(W, "NATIVE_POWERSHELL", native_powershell)
    monkeypatch.setattr(W, "NATIVE_RUNTIME", native_runtime)
    monkeypatch.setattr(W, "PINNED_GIT", git_executable)
    monkeypatch.setattr(W, "PINNED_GIT_RUNTIME_ROOT", git_runtime)
    pinned_site_packages = workspace / ".venv" / "Lib" / "site-packages"
    pinned_site_packages.mkdir(parents=True)
    (pinned_site_packages / "synthetic_dependency.py").write_bytes(
        b"SYNTHETIC_DEPENDENCY = True\n"
    )
    monkeypatch.setattr(W, "PINNED_SITE_PACKAGES", pinned_site_packages)
    monkeypatch.setattr(W, "RUNTIME_TEMP", runtime_temp)
    monkeypatch.setattr(W, "RECOVERY_ROOT", recovery)
    monkeypatch.setattr(W, "RECOVERY_COPY_ROOT", recovery_copy)
    monkeypatch.setattr(W, "OUTPUT_ROOT", output)
    monkeypatch.setattr(W, "SYNC_ROOT", sync)
    monkeypatch.setattr(W, "PREPARATION_ROOT", preparation)
    monkeypatch.setattr(W, "PREPARATION_ORIGINAL_ROOT", preparation / "original")
    monkeypatch.setattr(W, "PREPARATION_COPY_ROOT", preparation / "copy")
    monkeypatch.setattr(W, "PREFLIGHT_ROOT", workspace / "preflight")
    monkeypatch.setattr(W, "__file__", str(bootstrap))
    finalization_guard = W._finalization_guard_path()
    finalization_guard.parent.mkdir(parents=True, exist_ok=True)
    finalization_guard.write_bytes(b"\0")
    monkeypatch.setattr(
        W,
        "_runtime_flags",
        lambda: {
            "dont_write_bytecode": True,
            "ignore_environment": True,
            "isolated": True,
            "no_site": True,
            "no_user_site": True,
            "safe_path": True,
            "utf8_mode": True,
        },
    )
    def synthetic_startup_isolation() -> None:
        if W._runtime_flags() != {
            "dont_write_bytecode": True,
            "ignore_environment": True,
            "isolated": True,
            "no_site": True,
            "no_user_site": True,
            "safe_path": True,
            "utf8_mode": True,
        }:
            raise W.BootstrapRefused("synthetic worker requires -I -S -B -X utf8")

    monkeypatch.setattr(
        W, "_validate_startup_import_isolation", synthetic_startup_isolation
    )
    monkeypatch.setattr(W, "_validate_default_import_machinery", lambda: None)

    controller_commit = "a" * 40
    raw_loader = importlib.machinery.SourceFileLoader(
        W.RAW_AUTHORITY_MODULE_NAME, str(raw_authority_helper.resolve())
    )
    raw_spec = importlib.util.spec_from_loader(W.RAW_AUTHORITY_MODULE_NAME, raw_loader)
    assert raw_spec is not None
    raw_module = importlib.util.module_from_spec(raw_spec)
    raw_module.__source_sha256__ = W._sha_file(raw_authority_helper)
    raw_loader.exec_module(raw_module)
    monkeypatch.setitem(sys.modules, W.RAW_AUTHORITY_MODULE_NAME, raw_module)

    git_runtime_identity = raw_module.verify_plain_tree(
        git_runtime, retain_read_locks=True
    )
    site_packages_identity = raw_module.verify_plain_tree(
        pinned_site_packages, capture_python=True, retain_read_locks=True
    )
    base_runtime_identity = raw_module._native_tree_identity(pinned_base_runtime)
    venv_scripts_identity = raw_module._native_tree_identity(pinned_venv_scripts)
    monkeypatch.setattr(W, "EXPECTED_PINNED_PYTHON_SHA256", W._sha_file(Path(sys.executable)))
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_BASE_PYTHON_SHA256",
        W._sha_file(Path(sys._base_executable)),
    )
    monkeypatch.setattr(
        W, "EXPECTED_PINNED_PYVENV_SHA256", W._sha_file(pinned_pyvenv)
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_BASE_RUNTIME_INVENTORY_SHA256",
        base_runtime_identity["inventory_sha256"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_BASE_RUNTIME_FILE_COUNT",
        base_runtime_identity["file_count"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_BASE_RUNTIME_DIRECTORY_COUNT",
        base_runtime_identity["directory_count"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_BASE_RUNTIME_TOTAL_BYTES",
        base_runtime_identity["total_bytes"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_VENV_SCRIPTS_INVENTORY_SHA256",
        venv_scripts_identity["inventory_sha256"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_VENV_SCRIPTS_FILE_COUNT",
        venv_scripts_identity["file_count"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_VENV_SCRIPTS_DIRECTORY_COUNT",
        venv_scripts_identity["directory_count"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_VENV_SCRIPTS_TOTAL_BYTES",
        venv_scripts_identity["total_bytes"],
    )
    monkeypatch.setattr(W, "EXPECTED_PINNED_GIT_SHA256", W._sha_file(git_executable))
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_GIT_RUNTIME_INVENTORY_DIGEST",
        git_runtime_identity["inventory_digest"],
    )
    monkeypatch.setattr(
        W, "EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT", git_runtime_identity["file_count"]
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_GIT_RUNTIME_DIRECTORY_COUNT",
        git_runtime_identity["directory_count"],
    )
    monkeypatch.setattr(
        W, "EXPECTED_PINNED_GIT_RUNTIME_TOTAL_BYTES", git_runtime_identity["total_bytes"]
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_SITE_PACKAGES_INVENTORY_DIGEST",
        site_packages_identity["inventory_digest"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_SITE_PACKAGES_FILE_COUNT",
        site_packages_identity["file_count"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_SITE_PACKAGES_DIRECTORY_COUNT",
        site_packages_identity["directory_count"],
    )
    monkeypatch.setattr(
        W,
        "EXPECTED_PINNED_SITE_PACKAGES_TOTAL_BYTES",
        site_packages_identity["total_bytes"],
    )

    monkeypatch.chdir(execution)
    for name in tuple(os.environ):
        if name.upper().startswith(("PYTHON", "GIT_", "BU_D161_")):
            monkeypatch.delenv(name, raising=False)
    required_env = {
        "CUDA_VISIBLE_DEVICES": "-1",
        "HIP_VISIBLE_DEVICES": "-1",
        "OMP_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4",
        "OPENBLAS_NUM_THREADS": "4",
        "NUMEXPR_NUM_THREADS": "4",
        "TEMP": str(runtime_temp.resolve()),
        "TMP": str(runtime_temp.resolve()),
        "TMPDIR": str(runtime_temp.resolve()),
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "PYTHONUTF8": "1",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_KEY_0": "safe.directory",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_VALUE_0": str(execution.resolve()),
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "",
        "GIT_TERMINAL_PROMPT": "0",
    }
    for name, value in required_env.items():
        monkeypatch.setenv(name, value)
    # ``SetEnvironmentVariableW(name, "")`` removes the native Windows entry,
    # while the synthetic contract intentionally models the controller's
    # explicit empty-value row.  Keep exact-name/casing behavior testable via
    # one dynamic, fixture-local environment view.
    monkeypatch.setattr(W, "_exact_environment_items", lambda: tuple(os.environ.items()))

    checkpoint_bytes = b"synthetic-old-checkpoint\n"
    checkpoint_sha = W._sha_bytes(checkpoint_bytes)
    monkeypatch.setattr(W, "EXPECTED_OLD_CHECKPOINT_SHA256", checkpoint_sha)
    for path in W._checkpoint_paths():
        path.write_bytes(checkpoint_bytes)

    lease = {
        "schema_version": W.EXECUTION_LEASE_SCHEMA_VERSION,
        "lease_name": "week7-production",
        "pid": W.OLD_LEASE_PID,
        "token": W.OLD_LEASE_TOKEN,
        "timestamp": 1.0,
        "timestamp_utc": "2026-09-01T00:00:00+00:00",
    }
    archive = W._orphan_archive_path()
    archive.parent.mkdir(parents=True)
    _write_json(archive, lease)
    lease_sha = W._sha_file(archive)
    monkeypatch.setattr(W, "EXPECTED_OLD_LEASE_SHA256", lease_sha)

    quarantine, quarantine_copy = W._quarantine_paths()
    quarantine.mkdir(parents=True)
    quarantine_copy.mkdir(parents=True)
    for index in range(11):
        payload = f"synthetic-partial-{index}".encode()
        (quarantine / f"file-{index:02d}.bin").write_bytes(payload)
        (quarantine_copy / f"file-{index:02d}.bin").write_bytes(payload)
    partial_rows = W._tree_inventory(quarantine, what="synthetic quarantine")
    partial_digest = W._sha_bytes(W._canonical(partial_rows))

    controller_pid = os.getpid()

    def file_identity(path: Path) -> dict[str, Any]:
        return {
            "path": str(path.resolve()),
            "size": path.stat().st_size,
            "sha256": W._sha_file(path),
        }

    helper_identity = {
        **file_identity(raw_authority_helper),
    }
    controller_source_paths = {
        "src/bu/__init__.py": controller_package,
        "src/bu/experiments/week8_exp2a_recovery.py": controller_module,
        "scripts/week8_exp2a_recovery_worker.py": bootstrap,
        "scripts/week8_exp2a_recovery_inspector.py": inspector,
        "scripts/week8_exp2a_recovery_entrypoint.py": entrypoint,
        "scripts/week8_exp2a_recovery_fit_child.py": fit_child,
        "scripts/week8_recovery_raw_authority.py": raw_authority_helper,
        "scripts/week8_recovery_native_launcher.ps1": native_launcher,
    }
    controller_sources = {
        relative: path.read_bytes() for relative, path in controller_source_paths.items()
    }
    controller_tree = {
        relative: ("100644", f"{index + 1:040x}")
        for index, relative in enumerate(sorted(controller_sources))
    }
    execution_tree = {
        relative: ("100644", f"{index + 101:040x}")
        for index, relative in enumerate(sorted(execution_sources))
    }
    controller_inventory_digest = W._sha_bytes(
        W._canonical_ascii(
            {
                relative: W._sha_bytes(data)
                for relative, data in sorted(controller_sources.items())
            }
        )
    )
    execution_inventory_digest = W._sha_bytes(
        W._canonical_ascii(
            {
                relative: W._sha_bytes(data)
                for relative, data in sorted(execution_sources.items())
            }
        )
    )
    raw_controller = {
        "path": str(controller.resolve()),
        "git_commit": controller_commit,
        "branch": "sol2-week8-recovery",
        "detached": False,
        "tracked_file_count": len(controller_tree),
        "stability_observations": 2,
        "tracked_tree_digest": "e" * 64,
        "worktree_inventory_digest": controller_inventory_digest,
        "retained_read_lock_count": len(controller_tree),
    }
    raw_execution = {
        "path": str(execution.resolve()),
        "git_commit": W.EXECUTION_COMMIT,
        "branch": "HEAD",
        "detached": True,
        "tracked_file_count": len(execution_tree),
        "stability_observations": 2,
        "tracked_tree_digest": "f" * 64,
        "worktree_inventory_digest": execution_inventory_digest,
        "retained_read_lock_count": len(execution_tree),
    }
    raw_module._OBSERVED_WORKTREES.clear()
    raw_module._OBSERVED_WORKTREES.update(
        {
            str(controller.resolve()): {
                "git_commit": controller_commit,
                "worktree_inventory_digest": controller_inventory_digest,
                "tree": controller_tree,
                "python_sources": controller_sources,
                "retained_paths": frozenset(controller_tree),
            },
            str(execution.resolve()): {
                "git_commit": W.EXECUTION_COMMIT,
                "worktree_inventory_digest": execution_inventory_digest,
                "tree": execution_tree,
                "python_sources": dict(execution_sources),
                "retained_paths": frozenset(execution_tree),
            },
        }
    )
    startup_environment_pairs = (
        ("CUDA_VISIBLE_DEVICES", "-1"),
        ("HIP_VISIBLE_DEVICES", "-1"),
        ("MKL_NUM_THREADS", "4"),
        ("NUMEXPR_NUM_THREADS", "4"),
        ("OMP_NUM_THREADS", "4"),
        ("OPENBLAS_NUM_THREADS", "4"),
        (
            "PATH",
            os.pathsep.join(
                (
                    str(pinned_base_runtime.resolve()),
                    "C:\\Windows\\System32",
                    "C:\\Windows",
                )
            ),
        ),
        ("PYTHONDONTWRITEBYTECODE", "1"),
        ("PYTHONHASHSEED", "0"),
        ("PYTHONIOENCODING", "utf-8"),
        ("PYTHONNOUSERSITE", "1"),
        ("PYTHONSAFEPATH", "1"),
        ("PYTHONUTF8", "1"),
        ("SystemRoot", "C:\\Windows"),
        ("TEMP", str(native_runtime.resolve())),
        ("TMP", str(native_runtime.resolve())),
        ("TMPDIR", str(native_runtime.resolve())),
        ("WINDIR", "C:\\Windows"),
    )
    startup_environment = dict(startup_environment_pairs)
    startup_environment_sha256 = raw_module._startup_environment_sha256(
        startup_environment_pairs
    )
    stage0_binding_sha256 = W._sha_bytes(b"synthetic stage0 binding\n")
    release_receipt_sha256 = W._sha_bytes(b"synthetic release receipt\n")
    startup_binding_sha256 = W._sha_bytes(
        W._canonical_ascii(
            {
                "record_type": "synthetic_native_startup_binding",
                "release_receipt_sha256": release_receipt_sha256,
                "native_launcher_sha256": W._sha_file(native_launcher),
                "startup_environment_sha256": startup_environment_sha256,
                "pinned_base_runtime": base_runtime_identity,
                "pinned_venv_scripts": venv_scripts_identity,
            }
        )
    )
    native_startup = {
        "stage0_binding_sha256": stage0_binding_sha256,
        "release_receipt_sha256": release_receipt_sha256,
        "native_launcher": file_identity(native_launcher),
        "startup_binding_sha256": startup_binding_sha256,
        "native_powershell": str(native_powershell.resolve()),
        "native_runtime": str(native_runtime.resolve()),
        "startup_environment_sha256": startup_environment_sha256,
        "pinned_pyvenv": file_identity(pinned_pyvenv),
        "pinned_venv_scripts": copy.deepcopy(venv_scripts_identity),
        "pinned_base_runtime": copy.deepcopy(base_runtime_identity),
    }
    raw_payload = {
        "raw_authority_schema_version": 4,
        "record_type": "week8_d161_preimport_authority",
        "decision_id": W.DECISION_ID,
        "runtime": {
            "flags": {
                "dont_write_bytecode": True,
                "ignore_environment": True,
                "isolated": True,
                "no_site": True,
                "no_user_site": True,
                "safe_path": True,
                "utf8_mode": True,
            },
            "startup_options": ["-I", "-S", "-B", "-X", "utf8"],
            "entrypoint_path": str(entrypoint.resolve()),
            "command": "recover",
            "python_environment": {
                "PYTHONHASHSEED": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
                "PYTHONUTF8": "1",
            },
            "startup_environment": startup_environment,
            "working_directory": str(native_runtime.resolve()),
            "active_runtime": {
                "executable": str(Path(sys.executable).resolve()),
                "base_executable": str(Path(sys._base_executable).resolve()),
                "prefix": str(pinned_base_runtime.resolve()),
                "base_prefix": str(pinned_base_runtime.resolve()),
            },
            "preimport_sys_path_digest": "1" * 64,
            "pinned_python": file_identity(Path(sys.executable)),
            "pinned_base_python": file_identity(Path(sys._base_executable)),
            "pinned_site_packages": site_packages_identity,
            "outer_bootstrap_literal_sha256": W.EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256,
            "entrypoint_source_sha256": W._sha_file(entrypoint),
        },
        "native_startup": native_startup,
        "git": file_identity(git_executable),
        "git_runtime": git_runtime_identity,
        "raw_authority_helper": helper_identity,
        "controller": raw_controller,
        "execution": raw_execution,
        "admission": {
            "controller_source": str((controller / "src").resolve()),
            "execution_source": str((execution / "src").resolve()),
            "pinned_site_packages": str(pinned_site_packages.resolve()),
        },
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }
    raw_authority = {
        **raw_payload,
        "record_digest": W._sha_bytes(W._canonical_ascii(raw_payload)),
    }

    def synthetic_revalidate(
        authority_value: object,
        config: object,
        *,
        helper_path: Path,
        helper_sha256: str,
    ) -> dict[str, Any]:
        assert config == W._raw_authority_config(
            controller_commit, raw_authority["native_startup"]
        )
        assert Path(helper_path).resolve() == raw_authority_helper.resolve()
        assert helper_sha256 == helper_identity["sha256"]
        assert authority_value == raw_authority
        return copy.deepcopy(raw_authority)

    monkeypatch.setattr(
        raw_module, "revalidate_admitted_authority", synthetic_revalidate
    )

    gate_payload = {
        "entrypoint_gate_schema_version": 4,
        "record_type": "week8_d161_entrypoint_gate",
        "decision_id": W.DECISION_ID,
        "command": "recover",
        "entrypoint": {
            "path": str(entrypoint.resolve()),
            "sha256": W._sha_file(entrypoint),
            "size": entrypoint.stat().st_size,
        },
        "raw_authority_helper": helper_identity,
        "raw_authority": raw_authority,
        "admitted_pythonpath": [
            str((controller / "src").resolve()),
            str(pinned_site_packages.resolve()),
        ],
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }
    gate = {**gate_payload, "record_digest": W._sha_bytes(W._canonical_ascii(gate_payload))}
    monkeypatch.setattr(W, "_validate_entrypoint_gate", lambda: gate)
    monkeypatch.setenv(
        W.ENTRYPOINT_GATE_ENVIRONMENT_NAME,
        W._canonical_ascii(gate).decode("ascii"),
    )
    authority = {
        "controller_worktree": {
            "path": str(controller.resolve()),
            "git_commit": controller_commit,
            "detached": False,
        },
        "execution_worktree": {
            "path": str(execution.resolve()),
            "git_commit": W.EXECUTION_COMMIT,
            "detached": True,
        },
        "controller_module": {
            "path": str(controller_module.resolve()),
            "sha256": W._sha_file(controller_module),
        },
        "bootstrap_worker": {
            "path": str(bootstrap.resolve()),
            "sha256": W._sha_file(bootstrap),
        },
        "recovery_inspector": {
            "path": str(inspector.resolve()),
            "sha256": W._sha_file(inspector),
        },
        "recovery_entrypoint": {
            "path": str(entrypoint.resolve()),
            "sha256": W._sha_file(entrypoint),
        },
        "raw_authority_helper": {
            "path": str(raw_authority_helper.resolve()),
            "sha256": W._sha_file(raw_authority_helper),
        },
        "preimport_authority": W._preimport_authority_binding(gate),
        "preimport_authority_record": copy.deepcopy(raw_authority),
        "pinned_python": {
            "path": str(Path(sys.executable).resolve()),
            "sha256": W._sha_file(Path(sys.executable)),
        },
        "base_python": {
            "path": str(Path(sys._base_executable).resolve()),
            "sha256": W._sha_file(Path(sys._base_executable)),
        },
        "git_executable": {
            "path": str(git_executable.resolve()),
            "sha256": W._sha_file(git_executable),
        },
        "git_runtime": copy.deepcopy(git_runtime_identity),
        "loaded_controller_modules": [
            {
                "module_id": "bu",
                "source_path": str(controller_package.resolve()),
                "source_sha256": W._sha_file(controller_package),
                "git_blob": controller_tree["src/bu/__init__.py"][1],
            },
            {
                "module_id": "bu.experiments.week8_exp2a_recovery",
                "source_path": str(controller_module.resolve()),
                "source_sha256": W._sha_file(controller_module),
                "git_blob": controller_tree[
                    "src/bu/experiments/week8_exp2a_recovery.py"
                ][1],
            },
        ],
    }

    bundle_payload = {
        "child_transport_schema_version": W.CHILD_TRANSPORT_SCHEMA_VERSION,
        "record_type": "week8_d161_verified_child_bundle",
        "logical_path": str(bootstrap.resolve()),
        "script_sha256": W._sha_file(bootstrap),
        "script_base64": base64.b64encode(bootstrap.read_bytes()).decode("ascii"),
        "raw_helper_path": str(raw_authority_helper.resolve()),
        "raw_helper_sha256": helper_identity["sha256"],
        "raw_helper_base64": base64.b64encode(raw_authority_helper.read_bytes()).decode(
            "ascii"
        ),
    }
    child_bundle_record = {
        **bundle_payload,
        "record_digest": W._sha_bytes(W._canonical_ascii(bundle_payload)),
    }
    child_bundle = W._canonical_ascii(child_bundle_record)
    child_transport = {
        "child_transport_schema_version": W.CHILD_TRANSPORT_SCHEMA_VERSION,
        "transport": "verified_source_stdin",
        "logical_path": str(bootstrap.resolve()),
        "source_sha256": W._sha_file(bootstrap),
        "raw_helper_sha256": helper_identity["sha256"],
        "bootstrap_literal_sha256": W.EXPECTED_CHILD_BOOTSTRAP_LITERAL_SHA256,
        "bundle_sha256": W._sha_bytes(child_bundle),
    }
    monkeypatch.setattr(
        W, "__transport_source_sha256__", child_transport["source_sha256"], raising=False
    )
    monkeypatch.setattr(
        W, "__transport_bundle_sha256__", child_transport["bundle_sha256"], raising=False
    )
    monkeypatch.setattr(
        W,
        "_parent_process_attestation",
        lambda value: {
            "pid": os.getppid(),
            "parent_pid": controller_pid,
            "kernel_executable_path": value["pinned_python"]["path"],
            "kernel_executable_sha256": value["pinned_python"]["sha256"],
            "creation_time_100ns": 123456789,
            "pinned_launcher": dict(value["pinned_python"]),
        },
    )
    monkeypatch.setattr(
        W,
        "_worker_process_attestation",
        lambda value: {
            "pid": os.getpid(),
            "kernel_executable_path": value["base_python"]["path"],
            "kernel_executable_sha256": value["base_python"]["sha256"],
            "creation_time_100ns": 123456790,
            "base_interpreter": dict(value["base_python"]),
        },
    )
    liveness = {"stability": {"verdict": "pass"}, "synthetic": True}
    liveness_rows = [{"sha256": W._sha_bytes(W._canonical(liveness)), "report": liveness}]
    hidden = {
        "name": W.HIDDEN_PARTIAL_NAME,
        "entry_count": len(partial_rows),
        "file_count": 11,
        "inventory": partial_rows,
        "inventory_digest": partial_digest,
    }
    inventory = W._seal(
        {
            "inventory_schema_version": 2,
            "execution_commit": W.EXECUTION_COMMIT,
            "relocation": copy.deepcopy(relocation),
            "control": {"synthetic": True},
            "lease": {
                "path": str(W._active_lease_path().resolve()),
                "sha256": lease_sha,
                "pid": W.OLD_LEASE_PID,
                "token": W.OLD_LEASE_TOKEN,
                "timestamp": lease["timestamp"],
                "timestamp_utc": lease["timestamp_utc"],
            },
            "checkpoint": {
                "token": W.OLD_LEASE_TOKEN,
                "sha256": checkpoint_sha,
                "checkpoint_digest": W.EXPECTED_OLD_CHECKPOINT_DIGEST,
                "execution_context_digest": "b" * 64,
            },
            "events": {
                "count": 299,
                "chain_digest": W.EXPECTED_OLD_EVENT_STREAM,
                "tail_file_sha256": W.EXPECTED_OLD_EVENT_TAIL_FILE,
                "kind_counts": {"attempt_started": 150, "job_synced": 149},
                "started_job_ids": [f"started-{index:03d}" for index in range(150)],
                "synced_job_ids": [f"synced-{index:03d}" for index in range(149)],
                "failure_count": 0,
            },
            "jobs": {
                "registered_count": 261,
                "local_completed": [{"job_id": f"local-{index:03d}"} for index in range(150)],
                "durable_completed": [{"job_id": f"durable-{index:03d}"} for index in range(149)],
                "untouched_job_ids": [f"untouched-{index:03d}" for index in range(111)],
                "orphan_job_id": W.ORPHAN_JOB_ID,
                "orphan_child_pid": W.ORPHAN_CHILD_PID,
                "hidden_partial": hidden,
            },
            "staging": {"quarantine": {"present": True, "entry_count": 0}},
            "lower_report_count": 0,
            "production_launch_receipt_present": False,
            "mechanical_source_validation_performed": True,
            "scientific_outcomes_consulted": False,
            "scientific_values_emitted": False,
        },
        "inventory_digest",
    )
    incident, incident_sha = _publish(
        W.INCIDENT_FILE,
        {
            **_base("incident"),
            "status": "outcome_blind_interruption_adjudicated",
            "automatic_retry_allowed": False,
            "authority": authority,
            "controller_process": {
                "pid": controller_pid,
                "kernel_executable_path": authority["base_python"]["path"],
                "kernel_executable_sha256": authority["base_python"]["sha256"],
                "creation_time_100ns": 123456788,
                "base_interpreter": dict(authority["base_python"]),
            },
            "inventory": inventory,
            "inventory_digest": inventory["inventory_digest"],
            "liveness_stability_reports": liveness_rows,
        },
    )
    terminal, terminal_sha = _publish(
        W.EPOCH001_TERMINAL_FILE,
        {
            **_base("epoch001_terminal"),
            "status": "externally_interrupted",
            "incident": {
                "record_digest": incident["record_digest"],
                "file_sha256": incident_sha,
                "inventory_digest": incident["inventory_digest"],
            },
            "execution_commit": W.EXECUTION_COMMIT,
            "lease_token": W.OLD_LEASE_TOKEN,
            "lease_pid": W.OLD_LEASE_PID,
            "orphan_job_id": W.ORPHAN_JOB_ID,
            "orphan_child_pid": W.ORPHAN_CHILD_PID,
            "counts": {"events": 299, "started": 150, "synced": 149, "unresolved_started": 1, "failed": 0},
            "lower_terminal_report_present": False,
            "normal_lease_release_present": False,
            "automatic_retry_allowed": False,
        },
    )
    transition_authorization = W._expected_transition_authorization(
        incident, incident_sha=incident_sha, terminal_sha=terminal_sha
    )
    intent, intent_sha = _publish(
        W.TRANSITION_INTENT_FILE,
        {
            **_base("transition_intent"),
            "status": "ownership_transition_intended",
            "authorization": transition_authorization,
            "liveness_stability_reports": liveness_rows,
        },
    )
    completion, completion_sha = _publish(
        W.TRANSITION_COMPLETION_FILE,
        {
            **_base("transition_completion"),
            "status": "ownership_transition_complete",
            "authorization": transition_authorization,
            "transition_intent": {"record_digest": intent["record_digest"], "file_sha256": intent_sha},
            "orphan_lease_archive": {
                "path": str(archive.resolve()),
                "sha256": lease_sha,
                "classification": "orphaned_after_liveness_proof",
            },
            "quarantine": {
                "original_path": str(quarantine.resolve()),
                "copy_path": str(quarantine_copy.resolve()),
                "inventory": partial_rows,
                "inventory_digest": partial_digest,
                "independent_copy": True,
            },
        },
    )
    prelaunch = W._prelaunch_state()
    claim_left, claim_right = W._record_paths(W.BOOTSTRAP_CLAIM_FILE)
    invocation, invocation_sha = _publish(
        W.BOOTSTRAP_INVOCATION_FILE,
        {
            **_base("bootstrap_invocation"),
            "status": "authorized_once",
            "incident": {
                "record_digest": incident["record_digest"],
                "file_sha256": incident_sha,
                "inventory_digest": incident["inventory_digest"],
            },
            "epoch001_terminal": {"record_digest": terminal["record_digest"], "file_sha256": terminal_sha},
            "transition_intent": {"record_digest": intent["record_digest"], "file_sha256": intent_sha},
            "transition_completion": {"record_digest": completion["record_digest"], "file_sha256": completion_sha},
            "authority": authority,
            "controller_process": {
                "pid": controller_pid,
                "kernel_executable_path": authority["base_python"]["path"],
                "kernel_executable_sha256": authority["base_python"]["sha256"],
                "creation_time_100ns": 123456788,
                "base_interpreter": dict(authority["base_python"]),
            },
            "runtime_temp": W._runtime_temp_directory_identity(),
            "child_transport": child_transport,
            "prelaunch_state": prelaunch,
            "prelaunch_state_digest": W._sha_bytes(W._canonical(prelaunch)),
            "claim_paths": {
                "original_path": str(claim_left.resolve()),
                "copy_path": str(claim_right.resolve()),
                "exclusive": True,
            },
            "automatic_retry_allowed": False,
        },
    )
    monkeypatch.setenv(W.INVOCATION_ENV, invocation["record_digest"])
    monkeypatch.setenv(
        W.CHILD_BUNDLE_ENVIRONMENT_NAME, child_transport["bundle_sha256"]
    )
    return SimpleNamespace(
        workspace=workspace,
        controller=controller,
        execution=execution,
        output=output,
        sync=sync,
        recovery=recovery,
        recovery_copy=recovery_copy,
        controller_module=controller_module,
        bootstrap=bootstrap,
        inspector=inspector,
        entrypoint=entrypoint,
        raw_authority_helper=raw_authority_helper,
        raw_module=raw_module,
        raw_authority=raw_authority,
        gate=gate,
        child_bundle=child_bundle,
        child_transport=child_transport,
        execution_sources=execution_sources,
        git_executable=git_executable,
        git_runtime=git_runtime,
        authority=authority,
        incident=incident,
        invocation=invocation,
        invocation_sha=invocation_sha,
    )


def _empty_output_capture() -> dict[str, Any]:
    empty = W._sha_bytes(b"")
    return {
        "stdout": {"sha256": empty, "byte_count": 0, "write_count": 0},
        "stderr": {"sha256": empty, "byte_count": 0, "write_count": 0},
    }


def _successful_lower() -> dict[str, Any]:
    return {
        "counts": dict(W.EXPECTED_COUNTS),
        "lease_token": "d" * 32,
        "report_sha256": "e" * 64,
        "script_sha256": W._sha_file(W.BOOTSTRAP_SCRIPT),
        "output_capture": _empty_output_capture(),
    }


@pytest.mark.parametrize("mutation", [None, "missing_process", "pid", "executable", "relocation", "legacy_inventory"])
def test_parent_published_incident_roundtrips_through_both_consumers(scenario, monkeypatch, mutation):
    from bu.experiments import week8_exp2a_recovery as C

    monkeypatch.setattr(C, "RECOVERY_ROOT", scenario.workspace / "parent-publication")
    monkeypatch.setattr(C, "RECOVERY_COPY_ROOT", scenario.workspace / "parent-publication-copy")
    monkeypatch.setattr(C.Plan, "WORKSPACE_ROOT", scenario.workspace)
    monkeypatch.setattr(C.Plan, "COMMON_LEASE_ROOT", scenario.workspace / "week7-production-control")
    hashes = {**C.EXPECTED_HASHES, "old_checkpoint": W.EXPECTED_OLD_CHECKPOINT_SHA256,
              "old_lease": W.EXPECTED_OLD_LEASE_SHA256}
    monkeypatch.setattr(C, "EXPECTED_HASHES", hashes)
    monkeypatch.setattr(C, "_controller_authority", lambda: scenario.authority)
    monkeypatch.setattr(C, "_capture_twice", lambda: (copy.deepcopy(scenario.incident["inventory"]), {}))
    monkeypatch.setattr(C, "_relocation_state", lambda: (None, W._admitted_relocation()[2]))
    monkeypatch.setattr(C, "_quiescent_liveness", lambda: scenario.incident["liveness_stability_reports"][0]["report"])
    # Only the OS observer is doubled; the actual parent process attestation
    # hashes the fixture interpreter and validates its exact record shape.
    monkeypatch.setattr(C.windows_liveness, "capture_windows_process_identity", lambda: {
        "pid": os.getpid(), "kernel_executable_path": scenario.authority["base_python"]["path"],
        "creation_time_100ns": 123456789,
    })
    result = C.adjudicate()
    assert result["status"] == "adjudicated"
    paths = C._record_paths(C.INCIDENT_FILE)
    document = C.read_json(paths[0])
    assert paths[0].read_bytes() == paths[1].read_bytes()
    C._validate_incident_contract(document)
    W._validate_incident(document)
    assert document["controller_process"]["pid"] == os.getpid()
    assert document["inventory"]["inventory_schema_version"] == 2
    if mutation is None:
        return
    if mutation == "missing_process": del document["controller_process"]
    elif mutation == "pid": document["controller_process"]["pid"] = True
    elif mutation == "executable": document["controller_process"]["kernel_executable_sha256"] = "f" * 64
    else:
        inventory = document["inventory"]
        if mutation == "relocation": inventory["relocation"]["policy_sha256"] = "f" * 64
        else: inventory["inventory_schema_version"] = 1
        document["inventory"] = C._seal({k: v for k, v in inventory.items() if k != "inventory_digest"}, "inventory_digest")
        document["inventory_digest"] = document["inventory"]["inventory_digest"]
    document = C._seal({k: v for k, v in document.items() if k != "record_digest"})
    for validate in (C._validate_incident_contract, W._validate_incident):
        with pytest.raises(ValueError):
            validate(document)


@pytest.mark.parametrize("mutation", [None, "return_copy", "body", "changed_twin", "wrong_binding"])
def test_worker_retains_only_its_verified_transition_for_children(scenario, mutation):
    chain = W._validate_full_chain(scenario.invocation, scenario.invocation_sha)
    invocation = copy.deepcopy(scenario.invocation)
    if mutation == "wrong_binding": invocation["transition_completion"]["file_sha256"] = "f" * 64
    def run():
        with W._authorized_orphan_transition(invocation, chain):
            assert W._admitted_orphan_transition() == scenario.invocation["transition_completion"]
            with pytest.raises(W.BootstrapRefused, match="already active"):
                with W._authorized_orphan_transition(invocation, chain):
                    pytest.fail("nested transition admission accepted")
            if mutation == "return_copy":
                observed = W._admitted_orphan_transition()
                observed["file_sha256"] = "f" * 64
                assert W._admitted_orphan_transition() == invocation["transition_completion"]
            if mutation == "body": raise ValueError("synthetic lower refusal")
            if mutation == "changed_twin": W._record_paths(W.TRANSITION_COMPLETION_FILE)[1].write_bytes(b"changed")
    if mutation in {None, "return_copy"}: run()
    else:
        with pytest.raises(ValueError): run()
    assert W._AUTHORIZED_ORPHAN_TRANSITION is None
    with pytest.raises(W.BootstrapRefused, match="not authorized"):
        W._admitted_orphan_transition()


def _install_synthetic_supervisor(
    launch: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> tuple[object, object]:
    """Install the exact historical seams required by the nested-fit adapter."""

    def original_run_isolated(callback: object, **kwargs: object) -> None:
        del callback, kwargs

    def original_get_context(method: str | None = None) -> object:
        del method
        return object()

    launch._fit_worker = lambda *args, **kwargs: None
    launch.run_isolated_attempt = original_run_isolated
    supervisor = SimpleNamespace(
        run_isolated_attempt=original_run_isolated,
        multiprocessing=SimpleNamespace(get_context=original_get_context),
        pickle=pickle,
    )
    monkeypatch.setitem(sys.modules, "bu.experiments.supervisor", supervisor)
    monkeypatch.setattr(
        W, "_verified_historical_git_state", lambda authority: nullcontext()
    )
    monkeypatch.setattr(W, "_worker_relocation_readers", lambda launch: nullcontext())
    return original_run_isolated, original_get_context


def _install_fake_loaded_modules(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Path]:
    relative_paths = {
        "bu": "src/bu/__init__.py",
        "bu.experiments": "src/bu/experiments/__init__.py",
        "bu.experiments.week8_exp2a_production": (
            "src/bu/experiments/week8_exp2a_production.py"
        ),
        "bu.experiments.week8_exp2a_repair_launch": (
            "src/bu/experiments/week8_exp2a_repair_launch.py"
        ),
    }
    finder = scenario.raw_module.verified_source_finder(
        scenario.raw_authority, "execution"
    )
    monkeypatch.setattr(sys, "meta_path", [finder, *W._default_meta_path()])
    monkeypatch.setattr(sys, "path_importer_cache", {})
    for name in relative_paths:
        importlib.import_module(name)
    return {
        name: scenario.execution / relative
        for name, relative in relative_paths.items()
    }


def test_fixed_runtime_root_matches_controller_contract() -> None:
    assert W.RUNTIME_TEMP == (
        W.WORKSPACE_ROOT
        / "week8-exp2a-recovery-runtime-2026-09-02-attempt-001"
    )


def test_authority_shape_matches_shared_controller_contract(
    scenario: SimpleNamespace,
) -> None:
    assert set(scenario.authority) == {
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
    assert set(scenario.authority["git_executable"]) == {"path", "sha256"}
    assert W._validate_authority_shape(scenario.authority) == scenario.authority


def test_schema_and_preimport_contract_is_current_and_complete(
    scenario: SimpleNamespace,
) -> None:
    assert W.RECOVERY_SCHEMA_VERSION == 3
    assert W.BOOTSTRAP_SCHEMA_VERSION == 4
    assert scenario.gate["entrypoint_gate_schema_version"] == 4
    assert scenario.raw_authority["raw_authority_schema_version"] == 4
    assert scenario.authority["preimport_authority_record"] == scenario.raw_authority
    assert scenario.authority["git_runtime"] == scenario.raw_authority["git_runtime"]
    controller_commit = scenario.raw_authority["controller"]["git_commit"]
    native_startup = scenario.raw_authority["native_startup"]
    config = W._raw_authority_config(controller_commit, native_startup)
    assert set(config) == scenario.raw_module._CONFIG_KEYS
    assert config["pinned_local_appdata"] == str(
        Path("C:/Users/aladdin-alyanai/AppData/Local")
    )
    assert set(config) == {
        "controller_root",
        "controller_commit",
        "stage0_binding_sha256",
        "release_receipt_sha256",
        "native_launcher_sha256",
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
        "pinned_local_appdata",
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
    compact = scenario.authority["preimport_authority"]
    assert {
        "stage0_binding_sha256",
        "release_receipt_sha256",
        "native_launcher_sha256",
        "startup_binding_sha256",
        "startup_environment_sha256",
        "base_runtime_inventory_sha256",
        "venv_scripts_inventory_sha256",
    } <= set(compact)
    assert compact["stage0_binding_sha256"] == native_startup[
        "stage0_binding_sha256"
    ]
    assert compact["release_receipt_sha256"] == native_startup[
        "release_receipt_sha256"
    ]
    assert compact["native_launcher_sha256"] == native_startup["native_launcher"][
        "sha256"
    ]
    assert compact["startup_binding_sha256"] == native_startup[
        "startup_binding_sha256"
    ]
    assert compact["startup_environment_sha256"] == native_startup[
        "startup_environment_sha256"
    ]
    assert compact["base_runtime_inventory_sha256"] == native_startup[
        "pinned_base_runtime"
    ]["inventory_sha256"]
    assert compact["venv_scripts_inventory_sha256"] == native_startup[
        "pinned_venv_scripts"
    ]["inventory_sha256"]


def test_stage0_binding_is_required_in_full_config_and_compact_binding(
    scenario: SimpleNamespace,
) -> None:
    native = copy.deepcopy(scenario.raw_authority["native_startup"])
    native.pop("stage0_binding_sha256")
    with pytest.raises(W.BootstrapRefused, match="native startup hashes"):
        W._raw_authority_config(
            scenario.raw_authority["controller"]["git_commit"], native
        )

    authority = copy.deepcopy(scenario.authority)
    authority["preimport_authority"].pop("stage0_binding_sha256")
    with pytest.raises(W.BootstrapRefused, match="preimport authority binding"):
        W._validate_authority_shape(authority)


def test_raw_authority_helper_must_be_preloaded_from_verified_bundle(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert W._load_raw_authority_module() is scenario.raw_module
    monkeypatch.delitem(sys.modules, W.RAW_AUTHORITY_MODULE_NAME)
    with pytest.raises(W.BootstrapRefused, match="was not preloaded"):
        W._load_raw_authority_module()


def test_preloaded_raw_authority_helper_source_digest_is_bound(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scenario.raw_module, "__source_sha256__", "0" * 64)
    with pytest.raises(W.BootstrapRefused, match="helper identity differs"):
        W._load_raw_authority_module()


def _exercise_real_entrypoint_gate(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    *,
    gate: dict[str, Any] | None = None,
    observed_raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = copy.deepcopy(scenario.gate if gate is None else gate)
    monkeypatch.setenv(
        W.ENTRYPOINT_GATE_ENVIRONMENT_NAME,
        W._canonical_ascii(selected).decode("ascii"),
    )
    raw_result = (
        copy.deepcopy(selected["raw_authority"])
        if observed_raw is None
        else copy.deepcopy(observed_raw)
    )
    monkeypatch.setattr(
        W,
        "_load_raw_authority_module",
        lambda: SimpleNamespace(
            revalidate_admitted_authority=lambda *args, **kwargs: raw_result
        ),
    )
    return REAL_VALIDATE_ENTRYPOINT_GATE()


def test_worker_revalidates_exact_entrypoint_gate_before_claim(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _exercise_real_entrypoint_gate(scenario, monkeypatch) == scenario.gate


def test_worker_entrypoint_gate_requires_recover_command(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = copy.deepcopy(scenario.gate)
    gate["command"] = "status"
    payload = {key: value for key, value in gate.items() if key != "record_digest"}
    gate["record_digest"] = W._sha_bytes(W._canonical_ascii(payload))
    with pytest.raises(W.BootstrapRefused, match="policy or digest differs"):
        _exercise_real_entrypoint_gate(scenario, monkeypatch, gate=gate)


def test_worker_entrypoint_gate_rejects_noncanonical_or_tampered_seal(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = copy.deepcopy(scenario.gate)
    gate["record_digest"] = "0" * 64
    with pytest.raises(W.BootstrapRefused, match="policy or digest differs"):
        _exercise_real_entrypoint_gate(scenario, monkeypatch, gate=gate)


def test_worker_entrypoint_gate_rejects_fresh_raw_authority_drift(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = copy.deepcopy(scenario.gate["raw_authority"])
    observed["execution"]["worktree_inventory_digest"] = "0" * 64
    with pytest.raises(W.BootstrapRefused, match="changed before bootstrap claim"):
        _exercise_real_entrypoint_gate(
            scenario, monkeypatch, observed_raw=observed
        )


def test_child_transport_is_verified_stdin_bound_to_executed_source(
    scenario: SimpleNamespace,
) -> None:
    row = scenario.invocation["child_transport"]
    assert row == scenario.child_transport
    assert row["child_transport_schema_version"] == 1
    assert row["transport"] == "verified_source_stdin"
    assert row["source_sha256"] == W._sha_file(scenario.bootstrap)
    assert row["raw_helper_sha256"] == W._sha_file(
        scenario.raw_authority_helper
    )
    assert row["bundle_sha256"] == W._sha_bytes(scenario.child_bundle)
    assert W.__transport_source_sha256__ == row["source_sha256"]
    assert W.__transport_bundle_sha256__ == row["bundle_sha256"]
    W._validate_invocation_shape(scenario.invocation)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("child_transport_schema_version", 2),
        ("transport", "disk_path"),
        ("logical_path", "D:/outside/worker.py"),
        ("source_sha256", "0" * 64),
        ("raw_helper_sha256", "1" * 64),
        ("bootstrap_literal_sha256", "2" * 64),
        ("bundle_sha256", "3" * 64),
    ],
)
def test_child_transport_tamper_refuses_before_claim(
    scenario: SimpleNamespace, field: str, value: object
) -> None:
    invocation = copy.deepcopy(scenario.invocation)
    invocation["child_transport"][field] = value
    with pytest.raises(W.BootstrapRefused, match="child transport policy differs"):
        W._validate_invocation_shape(invocation)


def test_executed_transport_source_digest_mismatch_refuses(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(W, "__transport_source_sha256__", "0" * 64)
    with pytest.raises(W.BootstrapRefused, match="child transport policy differs"):
        W._validate_invocation_shape(scenario.invocation)


def test_executed_transport_bundle_digest_mismatch_refuses(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(W, "__transport_bundle_sha256__", "0" * 64)
    with pytest.raises(W.BootstrapRefused, match="child transport policy differs"):
        W._validate_invocation_shape(scenario.invocation)


def test_runtime_temp_replacement_refuses_before_claim(
    scenario: SimpleNamespace,
) -> None:
    recorded = dict(scenario.invocation["runtime_temp"])
    W.RUNTIME_TEMP.rmdir()
    W.RUNTIME_TEMP.mkdir()
    replacement = W._runtime_temp_directory_identity()
    if replacement == recorded:
        pytest.skip("host filesystem did not expose replacement-directory identity")
    with pytest.raises(W.BootstrapRefused, match="runtime temp directory was replaced"):
        W._run()
    assert not W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert not W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def test_claim_exposes_exact_worker_and_controller_parent_relationship(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker_pid = 24680
    launcher_pid = 13579
    controller_pid = scenario.invocation["controller_process"]["pid"]
    monkeypatch.setattr(W.os, "getpid", lambda: worker_pid)
    monkeypatch.setattr(W.os, "getppid", lambda: launcher_pid)
    claim = W._claim_payload(scenario.invocation, scenario.invocation_sha)
    assert claim["worker"]["pid"] == worker_pid
    assert claim["worker"]["parent_pid"] == launcher_pid
    assert claim["worker"]["parent_process"] == {
        "pid": launcher_pid,
        "parent_pid": controller_pid,
        "kernel_executable_path": scenario.authority["pinned_python"]["path"],
        "kernel_executable_sha256": scenario.authority["pinned_python"]["sha256"],
        "creation_time_100ns": 123456789,
        "pinned_launcher": scenario.authority["pinned_python"],
    }
    assert claim["worker"]["process"]["pid"] == worker_pid


def test_parent_attestation_requires_kernel_identity_of_pinned_controller(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_pid = 97531
    controller_pid = 86420
    monkeypatch.setattr(W.os, "getppid", lambda: parent_pid)
    monkeypatch.setattr(W, "_windows_parent_pid", lambda pid: controller_pid)
    monkeypatch.setattr(
        W,
        "_windows_process_identity",
        lambda pid: {
            "pid": pid,
            "kernel_executable_path": str(Path(sys.executable).resolve()),
            "creation_time_100ns": 99887766,
        },
    )
    row = REAL_PARENT_PROCESS_ATTESTATION(scenario.authority)
    assert row["pid"] == parent_pid
    assert row["parent_pid"] == controller_pid
    assert row["creation_time_100ns"] == 99887766
    assert row["kernel_executable_path"] == str(Path(sys.executable).resolve())
    assert row["kernel_executable_sha256"] == W._sha_file(Path(sys.executable))

    other = scenario.workspace / "other-python.exe"
    other.write_bytes(b"not the pinned launcher")
    monkeypatch.setattr(
        W,
        "_windows_process_identity",
        lambda pid: {
            "pid": pid,
            "kernel_executable_path": str(other.resolve()),
            "creation_time_100ns": 99887766,
        },
    )
    with pytest.raises(W.BootstrapRefused, match="pinned launcher"):
        REAL_PARENT_PROCESS_ATTESTATION(scenario.authority)


def test_run_claims_before_launch_terminalizes_success_and_never_reuses(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    launches = 0

    def launch(authority: dict[str, Any]) -> dict[str, Any]:
        nonlocal launches
        launches += 1
        assert authority == scenario.authority
        assert all(path.is_file() for path in W._record_paths(W.BOOTSTRAP_CLAIM_FILE))
        assert not W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)
        return _successful_lower()

    monkeypatch.setattr(W, "_launch_once", launch)
    result = W._run()
    assert launches == 1
    assert set(result) == {
        "bootstrap_schema_version",
        "status",
        "counts",
        "lease_token",
        "report_sha256",
        "script_sha256",
        "output_capture",
        "invocation_record_digest",
        "invocation_file_sha256",
        "claim_record_digest",
        "claim_file_sha256",
        "terminal_record_digest",
        "terminal_file_sha256",
        "scientific_values_emitted",
    }
    assert result["bootstrap_schema_version"] == 4
    assert result["status"] == "complete"
    assert result["invocation_record_digest"] == scenario.invocation["record_digest"]
    claim, claim_sha = W._load_record(W.BOOTSTRAP_CLAIM_FILE, record_type="bootstrap_claim")
    terminal, terminal_sha = W._load_record(W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal")
    assert result["claim_record_digest"] == claim["record_digest"]
    assert result["claim_file_sha256"] == claim_sha
    assert result["terminal_record_digest"] == terminal["record_digest"]
    assert result["terminal_file_sha256"] == terminal_sha
    assert terminal["status"] == "complete"
    assert terminal["automatic_retry_allowed"] is False
    assert terminal["claim"] == {
        "record_digest": claim["record_digest"],
        "file_sha256": claim_sha,
        "twins_complete": True,
    }
    assert set(terminal["operational_result"]) == {
        "counts",
        "lease_token",
        "report_sha256",
        "script_sha256",
        "output_capture",
    }
    assert terminal["operational_result"]["output_capture"] == _empty_output_capture()
    assert result["output_capture"] == terminal["operational_result"]["output_capture"]

    monkeypatch.setenv(W.INVOCATION_ENV, scenario.invocation["record_digest"])
    with pytest.raises(W.BootstrapRefused, match="already claimed"):
        W._run()
    assert launches == 1


def test_post_claim_failure_gets_hashed_terminal_and_no_raw_reason(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "SCIENTIFIC_VALUE_SHOULD_NOT_APPEAR_0.12345"
    monkeypatch.setattr(W, "_validate_full_chain", lambda *args: (_ for _ in ()).throw(RuntimeError(secret)))
    with pytest.raises(W.ClaimedBootstrapRefused) as caught:
        W._run()
    output = caught.value.output
    assert output["status"] == "refused"
    assert "claim_record_digest" in output
    terminal, _ = W._load_record(W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal")
    assert terminal["status"] == "refused"
    assert terminal["claim"]["twins_complete"] is True
    raw = W._record_paths(W.BOOTSTRAP_TERMINAL_FILE)[0].read_text(encoding="utf-8")
    assert secret not in raw
    assert secret not in json.dumps(output)


def test_captured_lower_failure_terminalizes_only_stream_hashes_and_counts(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "RAW_LOWER_FAILURE_MUST_NOT_ESCAPE"
    capture = {
        "stdout": {
            "sha256": W._sha_bytes(secret.encode("utf-8")),
            "byte_count": len(secret.encode("utf-8")),
            "write_count": 1,
        },
        "stderr": {
            "sha256": W._sha_bytes(b""),
            "byte_count": 0,
            "write_count": 0,
        },
    }

    def launch(authority: dict[str, Any]) -> dict[str, Any]:
        raise W.CapturedLowerRefused(RuntimeError(secret), capture)

    monkeypatch.setattr(W, "_launch_once", launch)
    with pytest.raises(W.ClaimedBootstrapRefused) as caught:
        W._run()
    terminal, _ = W._load_record(
        W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal"
    )
    assert set(terminal["operational_result"]) == {
        "error_type",
        "reason_sha256",
        "output_capture",
    }
    assert terminal["operational_result"]["output_capture"] == capture
    assert caught.value.output["output_capture"] == capture
    serialized = json.dumps(
        {"terminal": terminal, "worker_output": caught.value.output}
    )
    assert secret not in serialized


@pytest.mark.parametrize(
    "artifact",
    ["checkpoint", "report", "recovery_completion", "launch_receipt", "active_lease"],
)
def test_every_prior_continuation_artifact_refuses_before_lower_launch(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
) -> None:
    if artifact == "checkpoint":
        for root in (W.OUTPUT_ROOT, W.SYNC_ROOT):
            (root / W.START_DIRECTORY / f"{'f' * 32}.json").write_text("{}", encoding="utf-8")
    elif artifact == "report":
        (W.OUTPUT_ROOT / W.REPORT_DIRECTORY).mkdir()
    elif artifact == "recovery_completion":
        W._record_paths(W.RECOVERY_COMPLETION_FILE)[0].write_text("{}", encoding="utf-8")
    elif artifact == "launch_receipt":
        W._launch_receipt_paths()[1].write_text("{}", encoding="utf-8")
    elif artifact == "active_lease":
        _write_json(
            W._active_lease_path(),
            {
                "schema_version": W.EXECUTION_LEASE_SCHEMA_VERSION,
                "lease_name": "week7-production",
                "pid": 999,
                "token": "9" * 32,
                "timestamp": 2.0,
                "timestamp_utc": "2026-09-02T00:00:00+00:00",
            },
        )
    launches = 0

    def launch(authority: dict[str, Any]) -> dict[str, Any]:
        nonlocal launches
        launches += 1
        assert authority == scenario.authority
        return _successful_lower()

    monkeypatch.setattr(W, "_launch_once", launch)
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert launches == 0
    assert W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    terminal, _ = W._load_record(W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal")
    assert terminal["status"] == "refused"


@pytest.mark.parametrize('target',['archive','active'])
@pytest.mark.parametrize('version',[1,2.0,True,'2',None])
def test_orphan_and_active_lease_require_exact_execution_schema(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, target: str, version: object,
) -> None:
    archive = W._orphan_archive_path()
    row = json.loads(archive.read_bytes())
    assert row['schema_version'] == 2
    if target == 'active':
        row.update({'token':'9'*32,'pid':os.getpid()})
        path = W._active_lease_path()
    else:path = archive
    row['schema_version'] = version
    _write_json(path,row)
    if target == 'archive':
        # Prove semantic rejection independently of the external file pin.
        monkeypatch.setattr(W,'EXPECTED_OLD_LEASE_SHA256',W._sha_file(path))
    with pytest.raises(W.BootstrapRefused,match='lease.*identity'):
        W._validate_orphan_archive(require_active_absent=False)


def test_orphan_reader_accepts_real_supervisor_lease_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bu.experiments.supervisor import acquire_batch_lease, SUPERVISOR_SCHEMA_VERSION
    root = tmp_path/'workspace'
    root.mkdir()
    monkeypatch.setattr(W,'WORKSPACE_ROOT',root)
    with acquire_batch_lease(root/'lease-producer',lease_name='week7-production') as lease:
        row = json.loads(lease.path.read_bytes())
        assert row['schema_version'] == SUPERVISOR_SCHEMA_VERSION == W.EXECUTION_LEASE_SCHEMA_VERSION == 2
        monkeypatch.setattr(W,'OLD_LEASE_TOKEN',row['token'])
        monkeypatch.setattr(W,'OLD_LEASE_PID',row['pid'])
        archive = W._orphan_archive_path()
        archive.parent.mkdir(parents=True)
        archive.write_bytes(lease.path.read_bytes())
        monkeypatch.setattr(W,'EXPECTED_OLD_LEASE_SHA256',W._sha_file(archive))
        assert W._validate_orphan_archive() == row
        with acquire_batch_lease(root/'week7-production-control',lease_name='week7-production'):
            assert W._validate_orphan_archive(require_active_absent=False) == row


@pytest.mark.parametrize("prior", ["claim", "terminal"])
def test_prior_claim_or_terminal_refuses_without_another_write(
    scenario: SimpleNamespace, prior: str
) -> None:
    name = W.BOOTSTRAP_CLAIM_FILE if prior == "claim" else W.BOOTSTRAP_TERMINAL_FILE
    W._record_paths(name)[0].write_text("preserved", encoding="utf-8")
    with pytest.raises(W.BootstrapRefused):
        W._run()
    other = W.BOOTSTRAP_TERMINAL_FILE if prior == "claim" else W.BOOTSTRAP_CLAIM_FILE
    assert not W._any_record_path(other)


def test_chain_twin_divergence_is_terminalized_after_claim(
    scenario: SimpleNamespace
) -> None:
    W._record_paths(W.INCIDENT_FILE)[1].write_bytes(b"different\n")
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    terminal, _ = W._load_record(W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal")
    assert terminal["status"] == "refused"


def test_old_token_ordinary_release_file_is_rejected_from_disk_after_claim(
    scenario: SimpleNamespace,
) -> None:
    _write_json(
        W._ordinary_old_release_path(),
        {"token": W.OLD_LEASE_TOKEN, "synthetic": True},
    )
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    terminal, _ = W._load_record(
        W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal"
    )
    assert terminal["status"] == "refused"


def test_invocation_cross_binding_drift_is_terminalized(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = copy.deepcopy(scenario.invocation)
    invocation["transition_completion"]["record_digest"] = "0" * 64
    invocation, _ = _replace_twins(W.BOOTSTRAP_INVOCATION_FILE, invocation)
    monkeypatch.setenv(W.INVOCATION_ENV, invocation["record_digest"])
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def test_quarantine_copy_drift_is_terminalized(
    scenario: SimpleNamespace
) -> None:
    _, copy_root = W._quarantine_paths()
    (copy_root / "file-00.bin").write_bytes(b"changed")
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def test_authority_requires_tracked_inspector_and_rechecks_after_claim(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_publish = W._exclusive_publish_twins

    def publish_then_drift(name: str, payload: dict[str, Any]):
        result = original_publish(name, payload)
        if name == W.BOOTSTRAP_CLAIM_FILE:
            scenario.inspector.write_bytes(b"drift-after-claim\n")
        return result

    monkeypatch.setattr(W, "_exclusive_publish_twins", publish_then_drift)
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    terminal, _ = W._load_record(W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal")
    assert terminal["status"] == "refused"


def test_missing_inspector_authority_row_refuses_before_claim(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = copy.deepcopy(scenario.invocation)
    del invocation["authority"]["recovery_inspector"]
    invocation, _ = _replace_twins(W.BOOTSTRAP_INVOCATION_FILE, invocation)
    monkeypatch.setenv(W.INVOCATION_ENV, invocation["record_digest"])
    with pytest.raises(W.BootstrapRefused, match="controller authority"):
        W._run()
    assert not W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)


def test_missing_git_executable_authority_row_refuses_before_claim(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = copy.deepcopy(scenario.invocation)
    del invocation["authority"]["git_executable"]
    invocation, _ = _replace_twins(W.BOOTSTRAP_INVOCATION_FILE, invocation)
    monkeypatch.setenv(W.INVOCATION_ENV, invocation["record_digest"])
    with pytest.raises(W.BootstrapRefused, match="controller authority"):
        W._run()
    assert not W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)


def test_missing_loaded_controller_modules_refuses_before_claim(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = copy.deepcopy(scenario.invocation)
    del invocation["authority"]["loaded_controller_modules"]
    invocation, _ = _replace_twins(W.BOOTSTRAP_INVOCATION_FILE, invocation)
    monkeypatch.setenv(W.INVOCATION_ENV, invocation["record_digest"])
    with pytest.raises(W.BootstrapRefused, match="controller authority"):
        W._run()
    assert not W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("source_sha256", "0" * 64, "differs from its sealed row"),
        ("git_blob", "1" * 40, "differs from its sealed row"),
    ],
)
def test_loaded_controller_module_attestation_is_revalidated_from_raw_capture(
    scenario: SimpleNamespace,
    field: str,
    value: str,
    match: str,
) -> None:
    authority = copy.deepcopy(scenario.authority)
    authority["loaded_controller_modules"][1][field] = value
    with pytest.raises(W.BootstrapRefused, match=match):
        W._validate_authority(authority)


def test_loaded_controller_module_id_must_match_its_source_path(
    scenario: SimpleNamespace,
) -> None:
    authority = copy.deepcopy(scenario.authority)
    authority["loaded_controller_modules"][1]["source_path"] = authority[
        "loaded_controller_modules"
    ][0]["source_path"]
    with pytest.raises(W.BootstrapRefused, match="path differs from its id"):
        W._validate_authority(authority)


def test_git_executable_hash_drift_refuses_before_claim(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = copy.deepcopy(scenario.invocation)
    invocation["authority"]["git_executable"]["sha256"] = "0" * 64
    invocation, _ = _replace_twins(W.BOOTSTRAP_INVOCATION_FILE, invocation)
    monkeypatch.setenv(W.INVOCATION_ENV, invocation["record_digest"])
    with pytest.raises(W.BootstrapRefused, match="Git executable authority differs"):
        W._run()
    assert not W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert not W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def test_worker_has_no_post_gate_git_process_surface(
    scenario: SimpleNamespace,
) -> None:
    assert not hasattr(W, "_git")
    assert not hasattr(W, "_worktree_row")
    assert scenario.authority["git_executable"] == {
        "path": scenario.raw_authority["git"]["path"],
        "sha256": scenario.raw_authority["git"]["sha256"],
    }
    assert scenario.authority["git_runtime"] == scenario.raw_authority["git_runtime"]
    assert W._validate_authority(scenario.authority) == scenario.authority


def test_git_runtime_inventory_drift_refuses_from_raw_authority(
    scenario: SimpleNamespace,
) -> None:
    authority = copy.deepcopy(scenario.authority)
    authority["git_runtime"]["inventory_digest"] = "0" * 64
    with pytest.raises(W.BootstrapRefused, match="Git runtime differs"):
        W._validate_authority(authority)


def test_inspector_absent_from_captured_controller_tree_refuses_before_claim(
    scenario: SimpleNamespace,
) -> None:
    cached = scenario.raw_module._OBSERVED_WORKTREES[str(scenario.controller.resolve())]
    cached["tree"].pop("scripts/week8_exp2a_recovery_inspector.py")
    cached["python_sources"].pop("scripts/week8_exp2a_recovery_inspector.py")
    with pytest.raises(ValueError, match="absent from the exact tree"):
        W._run()
    assert not W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert not W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def test_execution_tree_digest_drift_refuses_before_claim(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario.gate["raw_authority"]["execution"][
        "worktree_inventory_digest"
    ] = "0" * 64
    with pytest.raises(W.BootstrapRefused, match="full pre-import authority"):
        W._run()
    assert not W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert not W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PYTHONPATH", "outside"),
        ("TMPDIR", "wrong"),
        ("CUDA_VISIBLE_DEVICES", "0"),
        ("PYTHONDONTWRITEBYTECODE", "0"),
        ("PYTHON_AUDIT_INJECTION", "present"),
        ("GIT_CONFIG_COUNT", "2"),
        ("GIT_CONFIG_KEY_0", "safe.directory.other"),
        ("GIT_CONFIG_VALUE_0", "*"),
        ("GIT_CONFIG_KEY_1", "safe.directory"),
        ("GIT_CONFIG_PARAMETERS", "safe.directory=*"),
        ("GIT_DIR", "outside"),
        ("GIT_WORK_TREE", "outside"),
        ("GIT_INDEX_FILE", "outside.index"),
        ("GIT_OBJECT_DIRECTORY", "outside-objects"),
        ("GIT_ALTERNATE_OBJECT_DIRECTORIES", "outside-alternates"),
        ("GIT_COMMON_DIR", "outside-common"),
        ("GIT_NAMESPACE", "outside-namespace"),
        ("GIT_CONFIG_GLOBAL", "outside.gitconfig"),
        ("GIT_CONFIG_SYSTEM", "outside-system.gitconfig"),
        ("GIT_EXEC_PATH", "outside-bin"),
    ],
)
def test_unsanitized_environment_is_terminalized_after_claim(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


@pytest.mark.parametrize(
    "name",
    [
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_VALUE_0",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_OPTIONAL_LOCKS",
        "GIT_PAGER",
        "GIT_TERMINAL_PROMPT",
    ],
)
def test_missing_required_git_config_binding_is_terminalized_after_claim(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    monkeypatch.delenv(name)
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def test_git_config_binding_is_exact_and_fixed_to_execution_worktree(
    scenario: SimpleNamespace,
) -> None:
    observed = {
        name: value
        for name, value in os.environ.items()
        if name.upper().startswith("GIT_")
    }
    assert observed == {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_KEY_0": "safe.directory",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_VALUE_0": str(scenario.execution.resolve()),
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "",
        "GIT_TERMINAL_PROMPT": "0",
    }
    W._validate_sanitized_environment(scenario.invocation)


def test_mis_cased_git_config_variable_is_rejected(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = list(W._exact_environment_items())
    environment = [
        ("git_config_key_0", value) if name == "GIT_CONFIG_KEY_0" else (name, value)
        for name, value in environment
    ]
    monkeypatch.setattr(W, "_exact_environment_items", lambda: tuple(environment))
    with pytest.raises(W.BootstrapRefused, match="mis-cased"):
        W._validate_sanitized_environment(scenario.invocation)


@pytest.mark.parametrize(
    "name",
    [
        W.INVOCATION_ENV,
        W.ENTRYPOINT_GATE_ENVIRONMENT_NAME,
        W.CHILD_BUNDLE_ENVIRONMENT_NAME,
    ],
)
def test_mis_cased_d161_control_variable_is_rejected(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    environment = list(W._exact_environment_items())
    environment = [
        (name.lower(), value) if observed == name else (observed, value)
        for observed, value in environment
    ]
    monkeypatch.setattr(W, "_exact_environment_items", lambda: tuple(environment))
    with pytest.raises(W.BootstrapRefused, match="mis-cased"):
        W._validate_sanitized_environment(scenario.invocation)


@pytest.mark.parametrize(
    "missing_flag",
    [
        "dont_write_bytecode",
        "ignore_environment",
        "isolated",
        "no_site",
        "no_user_site",
        "safe_path",
        "utf8_mode",
    ],
)
def test_missing_isolation_flags_are_terminalized_after_claim(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    missing_flag: str,
) -> None:
    flags = {
        "dont_write_bytecode": True,
        "ignore_environment": True,
        "isolated": True,
        "no_site": True,
        "no_user_site": True,
        "safe_path": True,
        "utf8_mode": True,
    }
    flags[missing_flag] = False
    monkeypatch.setattr(W, "_runtime_flags", lambda: flags)
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def _configure_real_startup_isolation(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> Path:
    runtime = scenario.workspace / "base-runtime"
    for path in (runtime, runtime / "Lib", runtime / "DLLs"):
        path.mkdir(parents=True, exist_ok=True)
    archive = runtime / "python313.zip"
    archive.write_bytes(b"synthetic stdlib archive")
    synthetic_python = scenario.workspace / ".venv" / "Scripts" / "python.exe"
    synthetic_python.parent.mkdir(parents=True, exist_ok=True)
    synthetic_python.write_bytes(b"synthetic pinned Python")
    monkeypatch.setattr(W, "PINNED_PYTHON", synthetic_python)
    monkeypatch.setattr(
        W,
        "_runtime_flags",
        lambda: {
            "dont_write_bytecode": True,
            "ignore_environment": True,
            "isolated": True,
            "no_site": True,
            "no_user_site": True,
            "safe_path": True,
            "utf8_mode": True,
        },
    )
    monkeypatch.setattr(W, "_runtime_roots", lambda: (runtime.resolve(),))
    monkeypatch.setattr(W, "_validate_default_import_machinery", REAL_VALIDATE_DEFAULT_IMPORT_MACHINERY)
    monkeypatch.setattr(sys, "meta_path", list(W._default_meta_path()))
    monkeypatch.setattr(
        sys,
        "path",
        [str(archive.resolve()), str((runtime / "DLLs").resolve()), str((runtime / "Lib").resolve())],
    )
    monkeypatch.setattr(sys, "path_importer_cache", {})
    return runtime


def test_real_startup_isolation_accepts_only_default_i_s_s_p_state(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_real_startup_isolation(scenario, monkeypatch)
    REAL_VALIDATE_STARTUP_IMPORT_ISOLATION()


def test_real_startup_isolation_rejects_meta_path_injection(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_real_startup_isolation(scenario, monkeypatch)
    sys.meta_path.append(object())
    with pytest.raises(W.BootstrapRefused, match="meta path"):
        REAL_VALIDATE_STARTUP_IMPORT_ISOLATION()


def test_real_startup_isolation_rejects_preadmitted_site_packages(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_real_startup_isolation(scenario, monkeypatch)
    sys.path.append(str(W.PINNED_SITE_PACKAGES.resolve()))
    with pytest.raises(W.BootstrapRefused, match="non-standard import path"):
        REAL_VALIDATE_STARTUP_IMPORT_ISOLATION()


def test_pinned_dependencies_are_added_programmatically_after_isolation(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_real_startup_isolation(scenario, monkeypatch)
    monkeypatch.setattr(W, "_validate_startup_import_isolation", REAL_VALIDATE_STARTUP_IMPORT_ISOLATION)
    source, site_packages, inherited = W._admit_old_source_and_dependencies()
    assert source == (scenario.execution / "src").resolve()
    assert site_packages == W.PINNED_SITE_PACKAGES.resolve()
    assert sys.path == [str(source), *inherited, str(site_packages)]
    assert str(site_packages) not in inherited


def test_exclusive_claim_has_one_winner_under_real_filesystem_race(
    scenario: SimpleNamespace
) -> None:
    payload = W._claim_payload(scenario.invocation, scenario.invocation_sha)
    barrier = threading.Barrier(2)

    def contender() -> str:
        barrier.wait(timeout=5)
        try:
            W._exclusive_publish_twins(W.BOOTSTRAP_CLAIM_FILE, payload)
        except W.BootstrapRefused:
            return "refused"
        return "published"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(contender) for _ in range(2)]
        results = sorted(future.result() for future in futures)
    assert results == ["published", "refused"]
    W._load_record(W.BOOTSTRAP_CLAIM_FILE, record_type="bootstrap_claim")


def test_directory_fsync_reports_windows_limitation_truthfully(tmp_path: Path) -> None:
    performed = W._fsync_directory(tmp_path)
    assert type(performed) is bool
    if os.name == "nt":
        assert performed is False
    assert "no portable Windows directory-fsync" in W._fsync_directory.__doc__
    assert "does not claim" in W.__doc__


def test_partial_claim_consumes_invocation_and_gets_failure_terminal(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = W._exclusive_publish_file
    calls = 0

    def fail_second(path: Path, data: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise W.BootstrapRefused("synthetic second-twin failure")
        original(path, data)

    monkeypatch.setattr(W, "_exclusive_publish_file", fail_second)
    with pytest.raises(W.ClaimedBootstrapRefused) as caught:
        W._run()
    claim_paths = W._record_paths(W.BOOTSTRAP_CLAIM_FILE)
    assert claim_paths[0].is_file() and not claim_paths[1].exists()
    terminal, _ = W._load_record(W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal")
    assert terminal["claim"]["twins_complete"] is False
    surviving = claim_paths[0].read_bytes()
    assert terminal["claim"]["file_sha256"] == W._sha_bytes(surviving)
    assert terminal["claim"]["record_digest"] == json.loads(
        surviving.decode("utf-8")
    )["record_digest"]
    assert caught.value.output["status"] == "refused"


def test_both_claim_twins_written_but_initial_readback_failed_are_complete(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = W._same_bytes
    failed = False
    launches = 0

    def fail_claim_readback_once(left: Path, right: Path, *, what: str) -> str:
        nonlocal failed
        if what == W.BOOTSTRAP_CLAIM_FILE and not failed:
            failed = True
            assert left.is_file() and right.is_file()
            raise W.BootstrapRefused("synthetic claim read-back failure")
        return original(left, right, what=what)

    def launch(authority: dict[str, Any]) -> dict[str, Any]:
        nonlocal launches
        launches += 1
        return _successful_lower()

    monkeypatch.setattr(W, "_same_bytes", fail_claim_readback_once)
    monkeypatch.setattr(W, "_launch_once", launch)
    with pytest.raises(W.ClaimedBootstrapRefused):
        W._run()
    assert failed is True
    assert launches == 0
    claim, claim_sha = W._load_record(
        W.BOOTSTRAP_CLAIM_FILE, record_type="bootstrap_claim"
    )
    terminal, _ = W._load_record(
        W.BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal"
    )
    assert terminal["claim"] == {
        "record_digest": claim["record_digest"],
        "file_sha256": claim_sha,
        "twins_complete": True,
    }


def test_partial_terminal_publication_is_a_permanent_stop(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = W._exclusive_publish_file
    calls = 0

    def fail_second_terminal_twin(path: Path, data: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            raise W.BootstrapRefused("synthetic terminal copy failure")
        original(path, data)

    monkeypatch.setattr(W, "_exclusive_publish_file", fail_second_terminal_twin)
    monkeypatch.setattr(
        W,
        "_validate_full_chain",
        lambda *args: (_ for _ in ()).throw(W.BootstrapRefused("stop")),
    )
    with pytest.raises(W.BootstrapRefused, match="terminal publication failed"):
        W._run()
    terminal_paths = W._record_paths(W.BOOTSTRAP_TERMINAL_FILE)
    assert terminal_paths[0].is_file() and not terminal_paths[1].exists()

    monkeypatch.setenv(W.INVOCATION_ENV, scenario.invocation["record_digest"])
    with pytest.raises(W.BootstrapRefused, match="already claimed"):
        W._run()
    assert terminal_paths[0].is_file() and not terminal_paths[1].exists()


def test_losing_worker_never_terminalizes_another_workers_claim(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = W._exclusive_publish_twins

    def foreign_winner(name: str, payload: dict[str, Any]):
        if name != W.BOOTSTRAP_CLAIM_FILE:
            return original(name, payload)
        foreign = copy.deepcopy(payload)
        foreign["worker"]["pid"] += 1
        original(name, foreign)
        raise W.BootstrapRefused("synthetic losing worker")

    monkeypatch.setattr(W, "_exclusive_publish_twins", foreign_winner)
    with pytest.raises(W.BootstrapRefused, match="another worker"):
        W._run()
    assert W._any_record_path(W.BOOTSTRAP_CLAIM_FILE)
    assert not W._any_record_path(W.BOOTSTRAP_TERMINAL_FILE)


def test_fd_capture_contains_os_write_existing_handler_and_child_process(
    scenario: SimpleNamespace,
    capfd: pytest.CaptureFixture[str],
) -> None:
    stdout_bytes = b"PARENT_FD1\nCHILD_FD1\n"
    stderr_bytes = b"PARENT_FD2\nEXISTING_HANDLER\nCHILD_FD2\n"
    logger = logging.getLogger("d161-fd-capture-test")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    try:
        def operation() -> str:
            os.write(1, b"PARENT_FD1\n")
            os.write(2, b"PARENT_FD2\n")
            logger.info("EXISTING_HANDLER")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    "-s",
                    "-P",
                    "-c",
                    (
                        "import os; "
                        "os.write(1, b'CHILD_FD1\\n'); "
                        "os.write(2, b'CHILD_FD2\\n')"
                    ),
                ],
                check=False,
            )
            assert completed.returncode == 0
            return "complete"

        result, error, capture = W._capture_lower_output(operation)
    finally:
        logger.removeHandler(handler)
        handler.close()
    assert result == "complete"
    assert error is None
    assert capfd.readouterr() == ("", "")
    assert capture == {
        "stdout": {
            "sha256": W._sha_bytes(stdout_bytes),
            "byte_count": len(stdout_bytes),
            "write_count": 1,
        },
        "stderr": {
            "sha256": W._sha_bytes(stderr_bytes),
            "byte_count": len(stderr_bytes),
            "write_count": 1,
        },
    }
    assert list(W.RUNTIME_TEMP.iterdir()) == []
    assert "PARENT_FD1" not in json.dumps(capture)
    assert "CHILD_FD2" not in json.dumps(capture)


def test_fd_capture_cleanup_uncertainty_fails_closed_and_cleans_temp(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = W._flush_stream
    calls = 0

    def fail_first_cleanup_flush(stream: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("synthetic cleanup uncertainty")
        original(stream)

    monkeypatch.setattr(W, "_flush_stream", fail_first_cleanup_flush)
    _, error, capture = W._capture_lower_output(lambda: None)
    assert isinstance(error, W.BootstrapRefused)
    assert "cleanup or restoration" in str(error)
    assert capture == _empty_output_capture()
    assert list(W.RUNTIME_TEMP.iterdir()) == []


def test_exact_token_monkeypatch_delegates_others_and_restores(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    delegated: list[str] = []

    def original_lookup(token: str) -> dict[str, Any]:
        delegated.append(token)
        return {"delegated": token}

    launch = SimpleNamespace(
        _historical_lease_record=original_lookup,
        PREFLIGHT_FILE=W.PREFLIGHT_FILE,
    )
    production = SimpleNamespace(
        PREFLIGHT_ROOT=W.PREFLIGHT_ROOT,
        OUTPUT_ROOT=W.OUTPUT_ROOT,
        SYNC_ROOT=W.SYNC_ROOT,
        WORKSPACE_ROOT=W.WORKSPACE_ROOT,
    )
    new_token = "7" * 32
    stdout_text = "LOWER_STDOUT_SECRET"
    stderr_text = "LOWER_STDERR_SECRET"

    def lower(**kwargs: object) -> dict[str, Any]:
        print(stdout_text)
        print(stderr_text, file=sys.stderr)
        _write_json(
            W._active_lease_path(),
            {
                "schema_version": W.EXECUTION_LEASE_SCHEMA_VERSION,
                "lease_name": "week7-production",
                "pid": 12345,
                "token": new_token,
                "timestamp": 2.0,
                "timestamp_utc": "2026-09-02T00:00:00+00:00",
            },
        )
        old = launch._historical_lease_record(W.OLD_LEASE_TOKEN)
        assert old["token"] == W.OLD_LEASE_TOKEN
        assert launch._historical_lease_record("8" * 32) == {"delegated": "8" * 32}
        W._active_lease_path().unlink()
        report = W.OUTPUT_ROOT / W.REPORT_DIRECTORY / f"{new_token}.json"
        report_copy = W.SYNC_ROOT / W.REPORT_DIRECTORY / report.name
        _write_json(report, {"status": "complete"})
        _write_json(report_copy, {"status": "complete"})
        return {
            "status": "complete",
            "counts": dict(W.EXPECTED_COUNTS),
            "failure": None,
            "historical_retrained": False,
            "lease_release_failure": None,
            "released_lease": {"token": new_token, "history_path": "synthetic"},
            "report_path": str(report),
        }

    launch.launch_exp2a_repairs = lower
    original_run_isolated, _ = _install_synthetic_supervisor(launch, monkeypatch)
    monkeypatch.setattr(
        W,
        "_install_old_source_tree",
        lambda authority: (production, launch, scenario.gate),
    )
    monkeypatch.setattr(W, "_validate_execution_source_tree", lambda authority: None)
    monkeypatch.setattr(W, "_validate_loaded_bu_modules", lambda authority: None)
    monkeypatch.setenv(W.INVOCATION_ENV, scenario.invocation["record_digest"])
    result = W._launch_once(scenario.authority)
    assert result["lease_token"] == new_token
    assert delegated == ["8" * 32]
    assert launch._historical_lease_record is original_lookup
    assert launch.run_isolated_attempt is original_run_isolated
    assert W.INVOCATION_ENV not in os.environ
    assert capsys.readouterr() == ("", "")
    assert result["output_capture"] == {
        "stdout": {
            "sha256": W._sha_bytes(f"{stdout_text}\n".encode("utf-8")),
            "byte_count": len(f"{stdout_text}\n".encode("utf-8")),
            "write_count": 1,
        },
        "stderr": {
            "sha256": W._sha_bytes(f"{stderr_text}\n".encode("utf-8")),
            "byte_count": len(f"{stderr_text}\n".encode("utf-8")),
            "write_count": 1,
        },
    }
    assert stdout_text not in json.dumps(result)
    assert stderr_text not in json.dumps(result)
    assert list(W.RUNTIME_TEMP.iterdir()) == []


def test_monkeypatch_restores_on_lower_failure(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def original_lookup(token: str) -> dict[str, Any]:
        return {"token": token}

    secret = "LOWER_FAILURE_SECRET"

    def lower(**kwargs: object) -> dict[str, Any]:
        print(secret)
        print(secret, file=sys.stderr)
        raise RuntimeError(secret)

    launch = SimpleNamespace(
        _historical_lease_record=original_lookup,
        PREFLIGHT_FILE=W.PREFLIGHT_FILE,
        launch_exp2a_repairs=lower,
    )
    production = SimpleNamespace(
        PREFLIGHT_ROOT=W.PREFLIGHT_ROOT,
        OUTPUT_ROOT=W.OUTPUT_ROOT,
        SYNC_ROOT=W.SYNC_ROOT,
        WORKSPACE_ROOT=W.WORKSPACE_ROOT,
    )
    original_run_isolated, _ = _install_synthetic_supervisor(launch, monkeypatch)
    monkeypatch.setattr(
        W,
        "_install_old_source_tree",
        lambda authority: (production, launch, scenario.gate),
    )
    monkeypatch.setattr(W, "_validate_execution_source_tree", lambda authority: None)
    monkeypatch.setattr(W, "_validate_loaded_bu_modules", lambda authority: None)
    with pytest.raises(W.CapturedLowerRefused) as caught:
        W._launch_once(scenario.authority)
    assert launch._historical_lease_record is original_lookup
    assert launch.run_isolated_attempt is original_run_isolated
    assert capsys.readouterr() == ("", "")
    assert secret not in str(caught.value)
    assert secret not in json.dumps(caught.value.output_capture)
    assert caught.value.output_capture["stdout"]["byte_count"] > 0
    assert caught.value.output_capture["stderr"]["byte_count"] > 0
    assert list(W.RUNTIME_TEMP.iterdir()) == []


def test_old_source_install_refuses_any_preimported_bu_module(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = types.ModuleType("bu.synthetic_preload")
    monkeypatch.setitem(sys.modules, "bu.synthetic_preload", fake)
    with pytest.raises(W.BootstrapRefused, match="imported before"):
        W._install_old_source_tree(scenario.authority)


def test_loaded_bu_modules_use_verified_captured_execution_sources(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_loaded_modules(scenario, monkeypatch)
    W._validate_loaded_bu_modules(scenario.authority)
    for name in (
        "bu",
        "bu.experiments",
        "bu.experiments.week8_exp2a_production",
        "bu.experiments.week8_exp2a_repair_launch",
    ):
        loader = sys.modules[name].__loader__
        assert loader.binding_marker == "week8_d161_verified_source_v2"
        assert loader.tree_kind == "execution"
        assert loader.authority_tree_digest == scenario.raw_authority["execution"][
            "worktree_inventory_digest"
        ]


def test_loaded_bu_module_refuses_source_missing_from_raw_capture(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _install_fake_loaded_modules(scenario, monkeypatch)
    relative = paths[
        "bu.experiments.week8_exp2a_repair_launch"
    ].relative_to(scenario.execution).as_posix()
    cached = scenario.raw_module._OBSERVED_WORKTREES[str(scenario.execution.resolve())]
    cached["python_sources"].pop(relative)
    with pytest.raises(W.BootstrapRefused, match="lacks captured execution authority"):
        W._validate_loaded_bu_modules(scenario.authority)


def test_loaded_bu_module_refuses_loader_git_blob_not_equal_to_raw_capture(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_loaded_modules(scenario, monkeypatch)
    module = sys.modules["bu.experiments.week8_exp2a_repair_launch"]
    module.__loader__.git_blob = "1" * 40
    with pytest.raises(W.BootstrapRefused, match="captured execution source"):
        W._validate_loaded_bu_modules(scenario.authority)


def test_loaded_bu_module_refuses_loader_source_digest_drift(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_loaded_modules(scenario, monkeypatch)
    module = sys.modules["bu.experiments.week8_exp2a_repair_launch"]
    module.__loader__.source_sha256 = "0" * 64
    with pytest.raises(W.BootstrapRefused, match="captured execution source"):
        W._validate_loaded_bu_modules(scenario.authority)


def test_execution_import_uses_captured_bytes_after_disk_tamper(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = (
        scenario.execution
        / "src"
        / "bu"
        / "experiments"
        / "week8_exp2a_repair_launch.py"
    )
    target.write_text("DISK_TAMPER_EXECUTED = True\n", encoding="utf-8")
    _install_fake_loaded_modules(scenario, monkeypatch)
    module = sys.modules["bu.experiments.week8_exp2a_repair_launch"]
    assert module.PREFLIGHT_FILE == "week8_preflight_report.json"
    assert not hasattr(module, "DISK_TAMPER_EXECUTED")
    W._validate_loaded_bu_modules(scenario.authority)


@pytest.mark.parametrize("suffix", [".pyc", ".pyd"])
def test_loaded_bu_module_refuses_compiled_or_extension_source(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    paths = _install_fake_loaded_modules(scenario, monkeypatch)
    name = "bu.experiments.week8_exp2a_repair_launch"
    non_source = paths[name].with_suffix(suffix)
    non_source.write_bytes(b"synthetic non-source")
    loader = importlib.machinery.SourceFileLoader(name, str(non_source))
    sys.modules[name].__file__ = str(non_source)
    sys.modules[name].__loader__ = loader
    sys.modules[name].__spec__ = SimpleNamespace(origin=str(non_source), loader=loader)
    with pytest.raises(W.BootstrapRefused, match="import origin"):
        W._validate_loaded_bu_modules(scenario.authority)


def test_loaded_bu_module_rejects_nonstandard_source_loader(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_loaded_modules(scenario, monkeypatch)
    name = "bu.experiments.week8_exp2a_repair_launch"
    module = sys.modules[name]
    injected = object()
    module.__loader__ = injected
    module.__spec__.loader = injected
    with pytest.raises(W.BootstrapRefused, match="import origin"):
        W._validate_loaded_bu_modules(scenario.authority)


def test_loaded_bu_module_rejects_executed_function_filename_outside_source(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_loaded_modules(scenario, monkeypatch)
    name = "bu.experiments.week8_exp2a_repair_launch"
    namespace: dict[str, Any] = {"__name__": name}
    exec(
        compile("def injected():\n    return 1\n", "outside-injected.py", "exec"),
        namespace,
    )
    sys.modules[name].injected = namespace["injected"]
    with pytest.raises(W.BootstrapRefused, match="executed code filename"):
        W._validate_loaded_bu_modules(scenario.authority)


def test_execution_source_is_rechecked_before_and_after_import(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    production = SimpleNamespace(WORKSPACE_ROOT=W.WORKSPACE_ROOT)
    launch = SimpleNamespace()

    def validate_tree(authority: dict[str, Any], *args: object) -> None:
        events.append("tree")

    def import_module(name: str) -> object:
        events.append(f"import:{name}")
        if name.endswith("week8_exp2a_production"):
            return production
        return launch

    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "meta_path", list(W._default_meta_path()))
    monkeypatch.setattr(sys, "path_importer_cache", {})
    monkeypatch.setattr(W, "_validate_execution_source_tree", validate_tree)
    monkeypatch.setattr(
        W, "_validate_loaded_bu_modules", lambda authority: events.append("modules")
    )
    monkeypatch.setattr(W.importlib, "import_module", import_module)
    monkeypatch.setattr(
        W,
        "_verified_historical_git_state",
        lambda authority, **kwargs: nullcontext(),
    )
    dependency_finder = SimpleNamespace(
        binding_marker="week8_d161_verified_dependency_source_v1"
    )
    monkeypatch.setattr(
        scenario.raw_module,
        "verified_dependency_finder",
        lambda raw: dependency_finder,
    )
    assert W._install_old_source_tree(scenario.authority) == (
        production,
        launch,
        scenario.gate,
    )
    assert events == [
        "tree",
        "import:bu.runrecord",
        "import:bu.experiments.week8_exp2a_production",
        "import:bu.experiments.week8_exp2a_repair_launch",
        "tree",
        "modules",
    ]


def test_execution_source_is_rechecked_immediately_before_lower_launch(
    scenario: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    def lower(**kwargs: object) -> dict[str, Any]:
        events.append("lower")
        return {}

    launch = SimpleNamespace(
        _historical_lease_record=lambda token: {"token": token},
        PREFLIGHT_FILE=W.PREFLIGHT_FILE,
        launch_exp2a_repairs=lower,
    )
    production = SimpleNamespace(
        PREFLIGHT_ROOT=W.PREFLIGHT_ROOT,
        OUTPUT_ROOT=W.OUTPUT_ROOT,
        SYNC_ROOT=W.SYNC_ROOT,
        WORKSPACE_ROOT=W.WORKSPACE_ROOT,
    )
    _install_synthetic_supervisor(launch, monkeypatch)
    monkeypatch.setattr(
        W,
        "_install_old_source_tree",
        lambda authority: (
            events.append("install") or (production, launch, scenario.gate)
        ),
    )
    monkeypatch.setattr(
        W, "_validate_execution_source_tree", lambda authority: events.append("tree")
    )
    monkeypatch.setattr(
        W, "_validate_loaded_bu_modules", lambda authority: events.append("modules")
    )
    with pytest.raises(W.CapturedLowerRefused):
        W._launch_once(scenario.authority)
    assert events[:4] == ["install", "tree", "modules", "lower"]


def _install_historical_git_doubles(
    scenario: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    marker: Path,
    *,
    include_aliases: bool = True,
) -> tuple[list[types.ModuleType], object]:
    """Install exact-shape historical modules whose original Git call is hostile."""

    source = scenario.execution / "src" / "bu" / "runrecord.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# synthetic captured historical runrecord\n", encoding="utf-8")
    runrecord = types.ModuleType("bu.runrecord")
    runrecord.__file__ = str(source.resolve())
    runrecord.__dict__["marker"] = marker
    exec(
        compile(
            "class GitState:\n"
            " def __init__(self, commit, dirty, branch):\n"
            "  self.commit=commit; self.dirty=dirty; self.branch=branch\n"
            " @property\n"
            " def trustworthy(self):\n"
            "  return (not self.dirty) and len(self.commit)==40\n"
            "def git_state(repo=None):\n"
            " marker.write_text('HOSTILE_FSMONITOR_EXECUTED', encoding='ascii')\n"
            " return GitState('0'*40, True, 'hostile')\n",
            str(source.resolve()),
            "exec",
        ),
        runrecord.__dict__,
    )
    runrecord.PROJECT_ROOT = scenario.execution
    runrecord.__spec__ = SimpleNamespace(
        loader=SimpleNamespace(
            binding_marker="week8_d161_verified_source_v2",
            tree_kind="execution",
        )
    )
    original = runrecord.git_state
    packages = [types.ModuleType("bu"), types.ModuleType("bu.experiments")]
    aliases = [runrecord]
    if include_aliases:
        for name in (
            "bu.experiments.confirmatory",
            "bu.experiments.fit_evidence",
            "bu.experiments.preflight",
        ):
            module = types.ModuleType(name)
            module.git_state = original
            aliases.append(module)
    for module in [*packages, *aliases]:
        monkeypatch.setitem(sys.modules, module.__name__, module)
    return aliases, original


def test_verified_historical_git_adapter_blocks_hostile_local_fsmonitor_and_restores(
    scenario: SimpleNamespace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "hostile-fsmonitor-marker.txt"
    git_dir = scenario.execution / ".git"
    git_dir.mkdir(exist_ok=True)
    (git_dir / "config").write_text(
        "[core]\n\tfsmonitor = hostile-fsmonitor-helper.cmd\n",
        encoding="ascii",
    )
    aliases, original = _install_historical_git_doubles(
        scenario, monkeypatch, marker
    )

    with W._verified_historical_git_state(scenario.authority) as adapter:
        assert all(module.git_state is adapter for module in aliases)
        for module in aliases:
            state = module.git_state()
            assert type(state).__name__ == "GitState"
            assert state.commit == W.EXECUTION_COMMIT
            assert state.dirty is False
            assert state.branch == "HEAD"
            assert state.trustworthy is True
        state = aliases[0].git_state(scenario.execution)
        assert state.commit == W.EXECUTION_COMMIT
        with pytest.raises(W.BootstrapRefused, match="another repository"):
            aliases[0].git_state(tmp_path)
        assert not marker.exists()

    assert all(module.git_state is original for module in aliases)
    assert not marker.exists()


def test_verified_historical_git_adapter_detects_tamper_and_restores_best_effort(
    scenario: SimpleNamespace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aliases, original = _install_historical_git_doubles(
        scenario, monkeypatch, tmp_path / "must-not-exist.txt"
    )
    with pytest.raises(W.BootstrapRefused, match="restoration|binding"):
        with W._verified_historical_git_state(scenario.authority):
            aliases[-1].git_state = object()
    assert all(module.git_state is original for module in aliases)


def test_verified_historical_git_adapter_covers_import_time_aliases(
    scenario: SimpleNamespace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "import-time-hostile-git.txt"
    aliases, original = _install_historical_git_doubles(
        scenario, monkeypatch, marker, include_aliases=False
    )
    runrecord = aliases[0]
    imported: list[types.ModuleType] = []
    with W._verified_historical_git_state(
        scenario.authority, allow_imports=True
    ) as adapter:
        assert runrecord.git_state is adapter
        for name in (
            "bu.experiments.confirmatory",
            "bu.experiments.fit_evidence",
            "bu.experiments.preflight",
        ):
            module = types.ModuleType(name)
            module.git_state = runrecord.git_state
            monkeypatch.setitem(sys.modules, name, module)
            imported.append(module)
            state = module.git_state()
            assert state.commit == W.EXECUTION_COMMIT
            assert state.dirty is False
        assert not marker.exists()

    assert runrecord.git_state is original
    assert all(module.git_state is original for module in imported)
    assert not marker.exists()


def test_verified_historical_git_adapter_refuses_rebound_import_time_alias(
    scenario: SimpleNamespace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aliases, original = _install_historical_git_doubles(
        scenario, monkeypatch, tmp_path / "must-not-exist.txt"
    )
    imported = types.ModuleType("bu.experiments.dynamic_git_alias")

    with pytest.raises(W.BootstrapRefused, match="restoration failed") as caught:
        with W._verified_historical_git_state(
            scenario.authority, allow_imports=True
        ) as adapter:
            imported.git_state = adapter
            monkeypatch.setitem(sys.modules, imported.__name__, imported)
            imported.git_state = object()

    assert caught.value.__cause__ is not None
    assert "binding changed after import" in str(caught.value.__cause__)
    assert all(module.git_state is original for module in aliases)


def test_no_arguments_contract_emits_only_hashed_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["worker.py", "unexpected"])
    assert W.main() == 2
    value = json.loads(capsys.readouterr().out)
    assert set(value) == {
        "bootstrap_schema_version",
        "status",
        "error_type",
        "reason_sha256",
        "scientific_values_emitted",
    }
    assert value["status"] == "refused"
    assert value["scientific_values_emitted"] is False


def test_real_entrypoint_is_compatible_with_exact_startup_policy() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-X",
            "utf8",
            str(WORKER_PATH),
            "unexpected",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    assert completed.returncode == 2
    assert completed.stderr == ""
    lines = completed.stdout.splitlines()
    assert len(lines) == 1
    value = json.loads(lines[0])
    assert value["bootstrap_schema_version"] == 4
    assert value["status"] == "refused"
