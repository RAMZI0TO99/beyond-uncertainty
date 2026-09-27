"""Verified nested fit-child bootstrap for the Week-8 D-161 recovery.

D-166 closes the process boundary left by the historical supervisor's Windows
``multiprocessing`` spawn.  This file is executed from raw-authority-captured
bytes after the same captured raw helper has been preloaded.  It admits no
project or third-party import until the sealed D-161 gate, the one-use child
invocation, both worktrees, the pinned interpreter/dependency trees, Git, and
its own transport bytes have all been revalidated.

The child calls only the historical fixed ``_fit_worker`` callback and returns
the historical supervisor protocol through one exclusively created result
file.  It never pickles or unpickles a callback or payload and never writes to
stdout or stderr.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import importlib.machinery
import json
import os
import re
import stat
import sys
import time
import traceback
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any


FIT_CHILD_INVOCATION_SCHEMA_VERSION = 3
FIT_CHILD_STARTUP_SCHEMA_VERSION = 1
FIT_CHILD_STARTUP_TIMEOUT_SECONDS = 300.0
ENTRYPOINT_GATE_SCHEMA_VERSION = 4
RAW_AUTHORITY_SCHEMA_VERSION = 4
DECISION_ID = "D-161"
EXECUTION_COMMIT = "4515d5165756c8d1669d38d2ee854fa1051b1017"

INVOCATION_BASE64_ENVIRONMENT_NAME = "BU_D161_FIT_CHILD_INVOCATION_BASE64"
INVOCATION_SHA256_ENVIRONMENT_NAME = "BU_D161_FIT_CHILD_INVOCATION_SHA256"
ENTRYPOINT_GATE_ENVIRONMENT_NAME = "BU_D161_ENTRYPOINT_GATE"
CHILD_BUNDLE_ENVIRONMENT_NAME = "BU_D161_CHILD_BUNDLE_SHA256"
RAW_AUTHORITY_MODULE_NAME = "_bu_week8_d161_raw_authority"

WORKSPACE_ROOT = Path("D:/Aenv/pro2")
CONTROLLER_WORKTREE = WORKSPACE_ROOT / "week8-recovery-controller-worktree"
EXECUTION_WORKTREE = WORKSPACE_ROOT / "week8-e2a-execution-4515-worktree"
CONTROLLER_SOURCE = CONTROLLER_WORKTREE / "src"
EXECUTION_SOURCE = EXECUTION_WORKTREE / "src"
FIT_CHILD_SCRIPT = (
    CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_fit_child.py"
)
ENTRYPOINT_SCRIPT = (
    CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_entrypoint.py"
)
RAW_AUTHORITY_HELPER = (
    CONTROLLER_WORKTREE / "scripts" / "week8_recovery_raw_authority.py"
)
PINNED_PYTHON = WORKSPACE_ROOT / "pro2" / ".venv" / "Scripts" / "python.exe"
PINNED_BASE_PYTHON = Path(
    "D:/Aenv/pro2/runtimes/week8-python313-frozen-001/python.exe"
)
PINNED_BASE_RUNTIME = PINNED_BASE_PYTHON.parent
PINNED_PYVENV = WORKSPACE_ROOT / "pro2" / ".venv" / "pyvenv.cfg"
PINNED_VENV_SCRIPTS = PINNED_PYTHON.parent
NATIVE_LAUNCHER = CONTROLLER_WORKTREE / "scripts" / "week8_recovery_native_launcher.ps1"
NATIVE_POWERSHELL = Path(
    "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)
NATIVE_RUNTIME = WORKSPACE_ROOT / "week8-d167-native-runtime-attempt-001"
PINNED_SITE_PACKAGES = (
    WORKSPACE_ROOT / "pro2" / ".venv" / "Lib" / "site-packages"
)
PINNED_GIT = Path(
    "D:/Aenv/pro2/runtimes/"
    "git/mingw64/bin/git.exe"
)
PINNED_GIT_RUNTIME_ROOT = PINNED_GIT.parent
STAGING_ATTEMPT_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-staging" / "staging"
)
RUNTIME_TEMP = (
    WORKSPACE_ROOT / "week8-exp2a-recovery-runtime-2026-09-02-attempt-001"
)

EXPECTED_PINNED_PYTHON_SHA256 = (
    "935016795f3e6908e75acbc2040a01e2e4cdb494a57c42f63a0d6eedb2372256"
)
EXPECTED_PINNED_BASE_PYTHON_SHA256 = (
    "5341746f92483a93e44c313de830f2fba2956f0759094404a16b2fed06c9a2ed"
)
EXPECTED_PINNED_PYVENV_SHA256 = (
    "e4d43703e6bfd6ad7296ee63e3441af275a4b8a89d72796b316f6458f120e418"
)
EXPECTED_PINNED_BASE_RUNTIME_INVENTORY_SHA256 = (
    "0a5aff918e4a46fae2427a593261f8e3640ba439ba4ffebf5081b15eb7df6760"
)
EXPECTED_PINNED_BASE_RUNTIME_FILE_COUNT = 5_368
EXPECTED_PINNED_BASE_RUNTIME_DIRECTORY_COUNT = 504
EXPECTED_PINNED_BASE_RUNTIME_TOTAL_BYTES = 155_022_742
EXPECTED_PINNED_VENV_SCRIPTS_INVENTORY_SHA256 = (
    "baa95b3f7e3e50a9b388fca6c4fd238fb55fc2e62f4cdc07c1b7c57caa9a54ad"
)
EXPECTED_PINNED_VENV_SCRIPTS_FILE_COUNT = 22
EXPECTED_PINNED_VENV_SCRIPTS_DIRECTORY_COUNT = 0
EXPECTED_PINNED_VENV_SCRIPTS_TOTAL_BYTES = 2_145_329
EXPECTED_PINNED_GIT_SHA256 = (
    "c115a66a1bede6694b513af420cc90f8775be03666a54d1ecb82d6196b929fe9"
)
EXPECTED_PINNED_GIT_RUNTIME_INVENTORY_DIGEST = (
    "3c30659fe0591a527183f3f57951a3d2243d178fe606a9756edfed5eaa89e984"
)
EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT = 94
EXPECTED_PINNED_GIT_RUNTIME_DIRECTORY_COUNT = 0
EXPECTED_PINNED_GIT_RUNTIME_TOTAL_BYTES = 66_573_247
EXPECTED_PINNED_SITE_PACKAGES_INVENTORY_DIGEST = (
    "b113ca128ef007b485fd458c88a780226872fe957d71a9a988442db4f012855b"
)
EXPECTED_PINNED_SITE_PACKAGES_FILE_COUNT = 34_514
EXPECTED_PINNED_SITE_PACKAGES_DIRECTORY_COUNT = 3_183
EXPECTED_PINNED_SITE_PACKAGES_TOTAL_BYTES = 1_019_075_506

# These two values are replaced and frozen by the controller release step
# after this new tracked source has settled.  Until then every live invocation
# fails closed while ordinary syntax and unit-test collection remain possible.
EXPECTED_RAW_AUTHORITY_HELPER_SHA256 = (
    "9067c7572692a4f0bc779488613c0e81f82233d8145bc1bb795e34f176e523aa"
)
EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256 = (
    "73d6f0e5cb126ffde136a3746b620236c847b3791a3eec688ddbd649ab304a3e"
)

_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_RESULT_NAME = re.compile(r"fit-child-result-([0-9a-f]{64})\.json\Z")
_STARTUP_NAME = re.compile(r"fit-child-startup-([0-9a-f]{64})\.json\Z")
_STARTUP_ACK_NAME = re.compile(
    r"fit-child-startup-ack-([0-9a-f]{64})\.json\Z"
)
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_INVOCATION_KEYS = {
    "fit_child_invocation_schema_version",
    "record_type",
    "attempt_dir",
    "payload",
    "result_path",
    "startup_path",
    "startup_ack_path",
    "entrypoint_gate_digest",
    "child_bundle_sha256",
    "relocation",
    "orphan_transition",
    "invocation_digest",
}
_GATE_KEYS = {
    "entrypoint_gate_schema_version",
    "record_type",
    "decision_id",
    "command",
    "entrypoint",
    "raw_authority_helper",
    "raw_authority",
    "admitted_pythonpath",
    "scientific_outcomes_consulted",
    "scientific_values_emitted",
    "production_mutation_performed",
    "record_digest",
}
_RAW_RECORD_KEYS = {
    "raw_authority_schema_version",
    "record_type",
    "decision_id",
    "runtime",
    "native_startup",
    "git",
    "git_runtime",
    "raw_authority_helper",
    "controller",
    "execution",
    "admission",
    "scientific_outcomes_consulted",
    "scientific_values_emitted",
    "production_mutation_performed",
    "record_digest",
}
_WORKTREE_KEYS = {
    "path",
    "git_commit",
    "branch",
    "detached",
    "tracked_file_count",
    "stability_observations",
    "tracked_tree_digest",
    "worktree_inventory_digest",
    "retained_read_lock_count",
}


class FitChildRefused(ValueError):
    """The D-166 nested fit child could not prove its fixed authority."""


def _canonical_ascii(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise FitChildRefused("fit-child value is not canonical JSON") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _expect_keys(value: object, keys: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise FitChildRefused(f"{what} has missing or extra fields")
    return value


def _expect_sha256(value: object, *, what: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise FitChildRefused(f"{what} is not a canonical lowercase SHA256")
    return value


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FitChildRefused(f"fit-child JSON repeats key {key!r}")
        result[key] = value
    return result


def _strict_json_object(encoded: bytes, *, what: str) -> dict[str, Any]:
    try:
        text = encoded.decode("ascii", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicate_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                FitChildRefused(f"{what} contains non-finite JSON")
            ),
        )
    except FitChildRefused:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FitChildRefused(f"{what} is not strict ASCII JSON") from exc
    if type(value) is not dict:
        raise FitChildRefused(f"{what} is not an exact object")
    if encoded != _canonical_ascii(value):
        raise FitChildRefused(f"{what} is not canonical ASCII JSON")
    return value


def _is_reparse(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        int(getattr(metadata, "st_file_attributes", 0))
        & _FILE_ATTRIBUTE_REPARSE_POINT
    )


def _fixed_absolute_path(value: object, *, what: str) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        raise FitChildRefused(f"{what} is not a fixed absolute path")
    path = Path(value)
    if (
        not path.is_absolute()
        or str(path) != value
        or path != Path(os.path.abspath(path))
    ):
        raise FitChildRefused(f"{what} is not a fixed absolute path")
    return path


def _plain_directory(path: Path, *, what: str) -> Path:
    """Resolve one existing directory while rejecting linked ancestors."""

    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise FitChildRefused(f"{what} is unavailable") from exc
    if resolved != path:
        raise FitChildRefused(f"{what} resolves to another path")
    for component in (path, *path.parents):
        if not os.path.lexists(component):
            continue
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise FitChildRefused(f"{what} cannot be inspected") from exc
        if _is_reparse(metadata):
            raise FitChildRefused(f"{what} contains a linked or reparse component")
        if component == path and not stat.S_ISDIR(metadata.st_mode):
            raise FitChildRefused(f"{what} is not a plain directory")
    return resolved


def _validate_protocol_path(
    value: object,
    *,
    pattern: re.Pattern[str],
    what: str,
) -> Path:
    path = _fixed_absolute_path(value, what=what)
    runtime = _plain_directory(RUNTIME_TEMP, what="fixed D-161 runtime temp")
    if path.parent != runtime or pattern.fullmatch(path.name) is None:
        raise FitChildRefused(
            f"{what} is not one fixed direct runtime-temp child"
        )
    if os.path.lexists(path):
        raise FitChildRefused(f"{what} is already occupied")
    return path


def _validate_result_path(value: object) -> Path:
    return _validate_protocol_path(
        value, pattern=_RESULT_NAME, what="fit-child result path"
    )


def _validate_attempt_dir(value: object) -> Path:
    path = _fixed_absolute_path(value, what="fit-child attempt directory")
    staging = _plain_directory(
        STAGING_ATTEMPT_ROOT, what="registered Week-8 attempt staging root"
    )
    attempt = _plain_directory(path, what="fit-child attempt directory")
    if attempt.parent != staging or attempt == staging:
        raise FitChildRefused(
            "fit-child attempt is not a direct child of the registered staging root"
        )
    return attempt


def _decode_invocation() -> tuple[dict[str, Any], Path, Path, Path]:
    encoded = os.environ.get(INVOCATION_BASE64_ENVIRONMENT_NAME)
    expected_sha = _expect_sha256(
        os.environ.get(INVOCATION_SHA256_ENVIRONMENT_NAME),
        what="fit-child invocation environment SHA256",
    )
    if type(encoded) is not str or not encoded:
        raise FitChildRefused("fit-child invocation base64 is absent")
    try:
        encoded_bytes = encoded.encode("ascii", errors="strict")
        decoded = base64.b64decode(encoded_bytes, validate=True)
    except (UnicodeError, ValueError) as exc:
        raise FitChildRefused("fit-child invocation is not strict base64") from exc
    if base64.b64encode(decoded) != encoded_bytes:
        raise FitChildRefused("fit-child invocation base64 is not canonical")
    if _sha256_bytes(decoded) != expected_sha:
        raise FitChildRefused("fit-child invocation environment SHA256 differs")
    document = _expect_keys(
        _strict_json_object(decoded, what="fit-child invocation"),
        _INVOCATION_KEYS,
        what="fit-child invocation",
    )
    if decoded != _canonical_ascii(document):
        raise FitChildRefused("fit-child invocation JSON is not canonical")
    # Validate the sole publication target before later authority checks.  If
    # any later check refuses, the parent can still receive python_exception.
    result_path = _validate_result_path(document["result_path"])
    startup_path = _validate_protocol_path(
        document["startup_path"],
        pattern=_STARTUP_NAME,
        what="fit-child startup path",
    )
    startup_ack_path = _validate_protocol_path(
        document["startup_ack_path"],
        pattern=_STARTUP_ACK_NAME,
        what="fit-child startup acknowledgment path",
    )
    tokens = {
        _RESULT_NAME.fullmatch(result_path.name).group(1),  # type: ignore[union-attr]
        _STARTUP_NAME.fullmatch(startup_path.name).group(1),  # type: ignore[union-attr]
        _STARTUP_ACK_NAME.fullmatch(startup_ack_path.name).group(1),  # type: ignore[union-attr]
    }
    if len(tokens) != 1 or len({result_path, startup_path, startup_ack_path}) != 3:
        raise FitChildRefused("fit-child protocol paths do not share one token")
    return document, result_path, startup_path, startup_ack_path


def _validate_invocation(document: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    if (
        type(document["fit_child_invocation_schema_version"]) is not int
        or document["fit_child_invocation_schema_version"]
        != FIT_CHILD_INVOCATION_SCHEMA_VERSION
        or document["record_type"]
        != "week8_d161_verified_fit_child_invocation"
        or type(document["payload"]) is not dict
    ):
        raise FitChildRefused("fit-child invocation policy differs")
    if type(document["relocation"]) is not dict:
        raise FitChildRefused("fit-child relocation binding is not an object")
    transition = _expect_keys(document["orphan_transition"], {"record_digest", "file_sha256"},
                              what="fit-child orphan transition")
    for name in transition:
        _expect_sha256(transition[name], what=f"fit-child orphan transition {name}")
    for key in (
        "entrypoint_gate_digest",
        "child_bundle_sha256",
        "invocation_digest",
    ):
        _expect_sha256(document[key], what=f"fit-child invocation {key}")
    unsealed = {
        key: value for key, value in document.items() if key != "invocation_digest"
    }
    if document["invocation_digest"] != _sha256_bytes(_canonical_ascii(unsealed)):
        raise FitChildRefused("fit-child invocation digest differs")
    attempt = _validate_attempt_dir(document["attempt_dir"])
    return attempt, document["payload"]


def _windows_parent_pid(pid: int) -> int:
    if os.name != "nt" or type(pid) is not int or pid <= 0:
        raise FitChildRefused("fit-child process parentage requires Windows")
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid = ctypes.c_void_p(-1).value
    if snapshot is None or int(snapshot) == invalid:
        raise FitChildRefused("fit-child process snapshot failed")
    parent: int | None = None
    close_failed = False
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise FitChildRefused("fit-child process enumeration failed")
        while True:
            if int(entry.th32ProcessID) == pid:
                parent = int(entry.th32ParentProcessID)
                break
            entry.dwSize = ctypes.sizeof(entry)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        if not kernel32.CloseHandle(snapshot):
            close_failed = True
    if close_failed or parent is None or parent <= 0:
        raise FitChildRefused("fit-child process parent is unavailable")
    return parent


def _windows_process_identity(
    pid: int,
    *,
    expected_path: Path,
    expected_sha256: str,
    what: str,
) -> dict[str, Any]:
    if os.name != "nt" or type(pid) is not int or pid <= 0:
        raise FitChildRefused(f"{what} identity requires one positive Windows PID")
    import ctypes
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        raise FitChildRefused(f"{what} cannot be opened")
    close_failed = False
    try:
        capacity = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(capacity.value)
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(capacity)
        ):
            raise FitChildRefused(f"{what} executable is unavailable")
        creation = FileTime()
        exit_time = FileTime()
        kernel_time = FileTime()
        user_time = FileTime()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            raise FitChildRefused(f"{what} creation time is unavailable")
        creation_time = (int(creation.high) << 32) | int(creation.low)
        observed = Path(buffer.value).resolve(strict=True)
        expected = expected_path.resolve(strict=True)
        if (
            creation_time <= 0
            or observed != expected
            or not os.path.samefile(observed, expected)
            or _sha256_bytes(observed.read_bytes()) != expected_sha256
        ):
            raise FitChildRefused(f"{what} differs from the pinned executable")
        result = {
            "pid": pid,
            "parent_pid": _windows_parent_pid(pid),
            "creation_time_100ns": creation_time,
            "kernel_executable_path": str(observed),
            "kernel_executable_sha256": expected_sha256,
        }
    finally:
        if not kernel32.CloseHandle(handle):
            close_failed = True
    if close_failed:
        raise FitChildRefused(f"{what} handle could not be closed")
    return result


def _startup_record(invocation: Mapping[str, Any]) -> dict[str, Any]:
    launcher_pid = os.getppid()
    fit_pid = os.getpid()
    launcher = _windows_process_identity(
        launcher_pid,
        expected_path=PINNED_PYTHON,
        expected_sha256=EXPECTED_PINNED_PYTHON_SHA256,
        what="fit-child launcher",
    )
    fit = _windows_process_identity(
        fit_pid,
        expected_path=PINNED_BASE_PYTHON,
        expected_sha256=EXPECTED_PINNED_BASE_PYTHON_SHA256,
        what="fit-child interpreter",
    )
    if fit_pid == launcher_pid or fit["parent_pid"] != launcher_pid:
        raise FitChildRefused("fit-child interpreter is not the launcher's child")
    payload = {
        "fit_child_startup_schema_version": FIT_CHILD_STARTUP_SCHEMA_VERSION,
        "record_type": "week8_d161_fit_child_startup",
        "invocation_digest": invocation["invocation_digest"],
        "launcher": launcher,
        "fit_interpreter": fit,
    }
    return {
        **payload,
        "record_digest": _sha256_bytes(_canonical_ascii(payload)),
    }


def _publish_startup_hello(
    path: Path, invocation: Mapping[str, Any]
) -> dict[str, Any]:
    startup = _startup_record(invocation)
    _publish_protocol(path, startup)
    return startup


def _await_startup_ack(
    invocation: Mapping[str, Any],
    startup: Mapping[str, Any],
    *,
    timeout: float | None = None,
) -> None:
    path = _fixed_absolute_path(
        invocation["startup_ack_path"],
        what="fit-child startup acknowledgment",
    )
    startup_path = _fixed_absolute_path(
        invocation["startup_path"], what="fit-child startup record"
    )
    wait_seconds = FIT_CHILD_STARTUP_TIMEOUT_SECONDS if timeout is None else timeout
    if type(wait_seconds) not in {int, float} or wait_seconds < 0:
        raise FitChildRefused("fit-child startup acknowledgment timeout is invalid")
    deadline = time.monotonic() + float(wait_seconds)
    while not os.path.lexists(path):
        if time.monotonic() >= deadline:
            raise FitChildRefused("fit-child startup acknowledgment timed out")
        time.sleep(0.005)
    plain = _fixed_absolute_path(str(path), what="fit-child startup acknowledgment")
    info = plain.lstat()
    if _is_reparse(info) or int(getattr(info, "st_nlink", 0)) != 1:
        raise FitChildRefused("fit-child startup acknowledgment is linked")
    raw = plain.read_bytes()
    ack = _expect_keys(
        _strict_json_object(raw, what="fit-child startup acknowledgment"),
        {
            "fit_child_startup_schema_version",
            "record_type",
            "invocation_digest",
            "startup_record_digest",
            "launcher_creation",
            "fit_interpreter_creation",
            "record_digest",
        },
        what="fit-child startup acknowledgment",
    )
    unsealed = {key: value for key, value in ack.items() if key != "record_digest"}
    expected_launcher = {
        "pid": startup["launcher"]["pid"],
        "creation_time_100ns": startup["launcher"]["creation_time_100ns"],
    }
    expected_fit = {
        "pid": startup["fit_interpreter"]["pid"],
        "creation_time_100ns": startup["fit_interpreter"]["creation_time_100ns"],
    }
    if (
        raw != _canonical_ascii(ack)
        or ack["fit_child_startup_schema_version"]
        != FIT_CHILD_STARTUP_SCHEMA_VERSION
        or ack["record_type"] != "week8_d161_fit_child_startup_ack"
        or ack["invocation_digest"] != invocation["invocation_digest"]
        or ack["startup_record_digest"] != startup["record_digest"]
        or ack["launcher_creation"] != expected_launcher
        or ack["fit_interpreter_creation"] != expected_fit
        or ack["record_digest"] != _sha256_bytes(_canonical_ascii(unsealed))
    ):
        raise FitChildRefused("fit-child startup acknowledgment differs")
    plain.unlink()
    startup_path.unlink()


def _load_bound_raw_authority() -> ModuleType:
    module = sys.modules.get(RAW_AUTHORITY_MODULE_NAME)
    if type(module) is not ModuleType:
        raise FitChildRefused(
            "raw-authority helper was not preloaded from captured bytes"
        )
    specification = getattr(module, "__spec__", None)
    loader = getattr(specification, "loader", None)
    try:
        module_path = Path(module.__file__).resolve(strict=True)
    except (AttributeError, OSError, TypeError) as exc:
        raise FitChildRefused("preloaded raw-authority path is unavailable") from exc
    if (
        module_path != RAW_AUTHORITY_HELPER.resolve(strict=True)
        or type(loader) is not importlib.machinery.SourceFileLoader
        or getattr(module, "__source_sha256__", None)
        != EXPECTED_RAW_AUTHORITY_HELPER_SHA256
    ):
        raise FitChildRefused("preloaded raw-authority helper identity differs")
    return module


def _raw_authority_config(
    controller_commit: str, native_startup: Mapping[str, Any]
) -> dict[str, Any]:
    if type(controller_commit) is not str or _HEX40.fullmatch(controller_commit) is None:
        raise FitChildRefused("sealed controller commit is not canonical")
    if type(native_startup) is not dict:
        raise FitChildRefused("native startup authority is unavailable")
    launcher = native_startup.get("native_launcher")
    values = (
        native_startup.get("release_receipt_sha256"),
        launcher.get("sha256") if type(launcher) is dict else None,
        native_startup.get("stage0_binding_sha256"),
        native_startup.get("startup_binding_sha256"),
    )
    if any(type(value) is not str or _HEX64.fullmatch(value) is None for value in values):
        raise FitChildRefused("native startup hashes are malformed")
    (
        receipt_sha256,
        launcher_sha256,
        stage0_binding_sha256,
        startup_binding_sha256,
    ) = values
    return {
        "controller_root": str(CONTROLLER_WORKTREE),
        "controller_commit": controller_commit,
        "release_receipt_sha256": receipt_sha256,
        "native_launcher_sha256": launcher_sha256,
        "stage0_binding_sha256": stage0_binding_sha256,
        "startup_binding_sha256": startup_binding_sha256,
        "execution_root": str(EXECUTION_WORKTREE),
        "execution_commit": EXECUTION_COMMIT,
        "pinned_python": str(PINNED_PYTHON),
        "pinned_base_python": str(PINNED_BASE_PYTHON),
        "pinned_base_runtime": str(PINNED_BASE_RUNTIME),
        "pinned_pyvenv": str(PINNED_PYVENV),
        "pinned_venv_scripts": str(PINNED_VENV_SCRIPTS),
        "native_launcher": str(NATIVE_LAUNCHER),
        "native_powershell": str(NATIVE_POWERSHELL),
        "native_runtime": str(NATIVE_RUNTIME),
        "pinned_site_packages": str(PINNED_SITE_PACKAGES),
        "pinned_git": str(PINNED_GIT),
        "pinned_git_runtime_root": str(PINNED_GIT_RUNTIME_ROOT),
        "pinned_python_sha256": EXPECTED_PINNED_PYTHON_SHA256,
        "pinned_base_python_sha256": EXPECTED_PINNED_BASE_PYTHON_SHA256,
        "pinned_pyvenv_sha256": EXPECTED_PINNED_PYVENV_SHA256,
        "pinned_base_runtime_inventory_sha256": EXPECTED_PINNED_BASE_RUNTIME_INVENTORY_SHA256,
        "pinned_base_runtime_file_count": EXPECTED_PINNED_BASE_RUNTIME_FILE_COUNT,
        "pinned_base_runtime_directory_count": EXPECTED_PINNED_BASE_RUNTIME_DIRECTORY_COUNT,
        "pinned_base_runtime_total_bytes": EXPECTED_PINNED_BASE_RUNTIME_TOTAL_BYTES,
        "pinned_venv_scripts_inventory_sha256": EXPECTED_PINNED_VENV_SCRIPTS_INVENTORY_SHA256,
        "pinned_venv_scripts_file_count": EXPECTED_PINNED_VENV_SCRIPTS_FILE_COUNT,
        "pinned_venv_scripts_directory_count": EXPECTED_PINNED_VENV_SCRIPTS_DIRECTORY_COUNT,
        "pinned_venv_scripts_total_bytes": EXPECTED_PINNED_VENV_SCRIPTS_TOTAL_BYTES,
        "pinned_git_sha256": EXPECTED_PINNED_GIT_SHA256,
        "pinned_git_runtime_inventory_digest": (
            EXPECTED_PINNED_GIT_RUNTIME_INVENTORY_DIGEST
        ),
        "pinned_git_runtime_file_count": EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT,
        "pinned_git_runtime_directory_count": (
            EXPECTED_PINNED_GIT_RUNTIME_DIRECTORY_COUNT
        ),
        "pinned_git_runtime_total_bytes": EXPECTED_PINNED_GIT_RUNTIME_TOTAL_BYTES,
        "pinned_site_packages_inventory_digest": (
            EXPECTED_PINNED_SITE_PACKAGES_INVENTORY_DIGEST
        ),
        "pinned_site_packages_file_count": EXPECTED_PINNED_SITE_PACKAGES_FILE_COUNT,
        "pinned_site_packages_directory_count": (
            EXPECTED_PINNED_SITE_PACKAGES_DIRECTORY_COUNT
        ),
        "pinned_site_packages_total_bytes": EXPECTED_PINNED_SITE_PACKAGES_TOTAL_BYTES,
        "outer_bootstrap_literal_sha256": (
            EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256
        ),
    }


def _validate_control_environment(
    raw_module: ModuleType, invocation: Mapping[str, Any]
) -> None:
    """Require the exact inherited D-161 controls plus two child controls."""

    exact_items = getattr(raw_module, "exact_environment_items", None)
    if not callable(exact_items):
        raise FitChildRefused("exact environment API is unavailable")
    gate_text = os.environ.get(ENTRYPOINT_GATE_ENVIRONMENT_NAME)
    bundle_sha = _expect_sha256(
        os.environ.get(CHILD_BUNDLE_ENVIRONMENT_NAME),
        what="fit-child bundle environment SHA256",
    )
    invocation_bytes = _canonical_ascii(dict(invocation))
    required = {
        "CUDA_VISIBLE_DEVICES": "-1",
        "HIP_VISIBLE_DEVICES": "-1",
        "OMP_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4",
        "OPENBLAS_NUM_THREADS": "4",
        "NUMEXPR_NUM_THREADS": "4",
        "TEMP": str(RUNTIME_TEMP.resolve(strict=True)),
        "TMP": str(RUNTIME_TEMP.resolve(strict=True)),
        "TMPDIR": str(RUNTIME_TEMP.resolve(strict=True)),
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
        "GIT_CONFIG_VALUE_0": str(EXECUTION_WORKTREE.resolve(strict=True)),
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "",
        "GIT_TERMINAL_PROMPT": "0",
        ENTRYPOINT_GATE_ENVIRONMENT_NAME: gate_text,
        CHILD_BUNDLE_ENVIRONMENT_NAME: bundle_sha,
        INVOCATION_BASE64_ENVIRONMENT_NAME: base64.b64encode(
            invocation_bytes
        ).decode("ascii"),
        INVOCATION_SHA256_ENVIRONMENT_NAME: _sha256_bytes(invocation_bytes),
    }
    if type(gate_text) is not str or not gate_text:
        raise FitChildRefused("fit child lacks the sealed D-161 entrypoint gate")
    try:
        observed_items = exact_items()
    except (OSError, TypeError, ValueError) as exc:
        raise FitChildRefused("exact child environment cannot be read") from exc
    observed: dict[str, tuple[str, str]] = {}
    approved_python = {name for name in required if name.startswith("PYTHON")}
    approved_git = {name for name in required if name.startswith("GIT_")}
    approved_bu = {name for name in required if name.startswith("BU_D161_")}
    for item in observed_items:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
        ):
            raise FitChildRefused("exact child environment contains an invalid entry")
        name, value = item
        canonical_name = name.upper()
        controlled = canonical_name in required or canonical_name.startswith(
            ("PYTHON", "GIT_", "BU_D161_")
        )
        if controlled:
            if canonical_name in observed:
                raise FitChildRefused("exact child environment duplicates a control")
            observed[canonical_name] = (name, value)
        if canonical_name.startswith("PYTHON") and (
            name != canonical_name or canonical_name not in approved_python
        ):
            raise FitChildRefused("child retained an unapproved Python control")
        if canonical_name.startswith("GIT_") and (
            name != canonical_name or canonical_name not in approved_git
        ):
            raise FitChildRefused("child retained an unapproved Git control")
        if canonical_name.startswith("BU_D161_") and (
            name != canonical_name or canonical_name not in approved_bu
        ):
            raise FitChildRefused("child retained an unapproved D-161 control")
    for name, expected in required.items():
        if type(expected) is not str or observed.get(name) != (name, expected):
            raise FitChildRefused(f"exact child environment differs at {name}")


def _file_identity(
    value: object, *, expected_path: Path, expected_sha256: str | None, what: str
) -> dict[str, Any]:
    row = _expect_keys(value, {"path", "sha256", "size"}, what=what)
    if (
        row["path"] != str(expected_path.resolve(strict=True))
        or type(row["size"]) is not int
        or row["size"] <= 0
        or _expect_sha256(row["sha256"], what=f"{what} SHA256")
        != row["sha256"]
        or (expected_sha256 is not None and row["sha256"] != expected_sha256)
    ):
        raise FitChildRefused(f"{what} identity differs")
    return row


def _validate_entrypoint_gate(
    raw_module: ModuleType, invocation: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    encoded = os.environ.get(ENTRYPOINT_GATE_ENVIRONMENT_NAME)
    if type(encoded) is not str or not encoded:
        raise FitChildRefused("fit child lacks the sealed D-161 entrypoint gate")
    try:
        encoded_bytes = encoded.encode("ascii", errors="strict")
    except UnicodeError as exc:
        raise FitChildRefused("entrypoint gate is not ASCII") from exc
    gate = _expect_keys(
        _strict_json_object(encoded_bytes, what="entrypoint gate"),
        _GATE_KEYS,
        what="entrypoint gate",
    )
    unsealed_gate = {
        key: value for key, value in gate.items() if key != "record_digest"
    }
    gate_digest = _expect_sha256(gate["record_digest"], what="entrypoint gate digest")
    if (
        type(gate["entrypoint_gate_schema_version"]) is not int
        or gate["entrypoint_gate_schema_version"] != ENTRYPOINT_GATE_SCHEMA_VERSION
        or gate["record_type"] != "week8_d161_entrypoint_gate"
        or gate["decision_id"] != DECISION_ID
        or gate["command"] != "recover"
        or gate_digest != _sha256_bytes(_canonical_ascii(unsealed_gate))
        or gate_digest != invocation["entrypoint_gate_digest"]
        or gate["scientific_outcomes_consulted"] is not False
        or gate["scientific_values_emitted"] is not False
        or gate["production_mutation_performed"] is not False
    ):
        raise FitChildRefused("entrypoint gate policy or digest differs")

    entrypoint = _file_identity(
        gate["entrypoint"],
        expected_path=ENTRYPOINT_SCRIPT,
        expected_sha256=None,
        what="D-161 entrypoint",
    )
    helper = _file_identity(
        gate["raw_authority_helper"],
        expected_path=RAW_AUTHORITY_HELPER,
        expected_sha256=EXPECTED_RAW_AUTHORITY_HELPER_SHA256,
        what="D-161 raw-authority helper",
    )
    expected_pythonpath = [
        str(CONTROLLER_SOURCE.resolve(strict=True)),
        str(PINNED_SITE_PACKAGES.resolve(strict=True)),
    ]
    if gate["admitted_pythonpath"] != expected_pythonpath:
        raise FitChildRefused("entrypoint admitted Python paths differ")

    raw = _expect_keys(
        gate["raw_authority"], _RAW_RECORD_KEYS, what="raw-authority record"
    )
    unsealed_raw = {key: value for key, value in raw.items() if key != "record_digest"}
    if (
        type(raw["raw_authority_schema_version"]) is not int
        or raw["raw_authority_schema_version"] != RAW_AUTHORITY_SCHEMA_VERSION
        or raw["record_type"] != "week8_d161_preimport_authority"
        or raw["decision_id"] != DECISION_ID
        or raw["raw_authority_helper"] != helper
        or _expect_sha256(raw["record_digest"], what="raw-authority digest")
        != _sha256_bytes(_canonical_ascii(unsealed_raw))
        or raw["scientific_outcomes_consulted"] is not False
        or raw["scientific_values_emitted"] is not False
        or raw["production_mutation_performed"] is not False
    ):
        raise FitChildRefused("raw-authority record policy or digest differs")
    runtime = raw.get("runtime")
    if (
        type(runtime) is not dict
        or runtime.get("command") != "recover"
        or runtime.get("entrypoint_source_sha256") != entrypoint["sha256"]
    ):
        raise FitChildRefused("raw-authority runtime binding differs")
    controller = _expect_keys(
        raw["controller"], _WORKTREE_KEYS, what="raw controller worktree"
    )
    execution = _expect_keys(
        raw["execution"], _WORKTREE_KEYS, what="raw execution worktree"
    )
    controller_commit = controller["git_commit"]
    if (
        type(controller_commit) is not str
        or _HEX40.fullmatch(controller_commit) is None
        or controller["path"] != str(CONTROLLER_WORKTREE.resolve(strict=True))
        or execution["path"] != str(EXECUTION_WORKTREE.resolve(strict=True))
        or execution["git_commit"] != EXECUTION_COMMIT
        or execution["detached"] is not True
        or execution["branch"] != "HEAD"
    ):
        raise FitChildRefused("sealed worktree authority differs")

    revalidate = getattr(raw_module, "revalidate_recorded_static_authority", None)
    if not callable(revalidate):
        raise FitChildRefused("static raw-authority revalidation API is unavailable")
    try:
        observed = revalidate(
            raw,
            _raw_authority_config(controller_commit, raw.get("native_startup")),
            helper_path=RAW_AUTHORITY_HELPER,
            helper_sha256=EXPECTED_RAW_AUTHORITY_HELPER_SHA256,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise FitChildRefused("recorded static authority revalidation refused") from exc
    if type(observed) is not dict or _canonical_ascii(observed) != _canonical_ascii(raw):
        raise FitChildRefused("recorded static authority changed")
    return gate, raw


def _validate_transport(
    raw_module: ModuleType,
    raw: Mapping[str, Any],
    invocation: Mapping[str, Any],
) -> None:
    bundle_sha = _expect_sha256(
        os.environ.get(CHILD_BUNDLE_ENVIRONMENT_NAME),
        what="fit-child bundle environment SHA256",
    )
    if (
        globals().get("__transport_bundle_sha256__") != bundle_sha
        or invocation["child_bundle_sha256"] != bundle_sha
    ):
        raise FitChildRefused("fit-child bundle transport digest differs")
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    if not callable(admitted_source):
        raise FitChildRefused("raw captured-source API is unavailable")
    try:
        captured = admitted_source(
            raw,
            "controller",
            "scripts/week8_exp2a_recovery_fit_child.py",
        )
    except (OSError, TypeError, ValueError) as exc:
        raise FitChildRefused("fit-child captured source is unavailable") from exc
    expected_source_sha = _sha256_bytes(captured)
    try:
        logical_path = Path(__file__).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise FitChildRefused("fit-child logical path is unavailable") from exc
    if (
        logical_path != FIT_CHILD_SCRIPT.resolve(strict=True)
        or globals().get("__transport_source_sha256__") != expected_source_sha
    ):
        raise FitChildRefused("fit-child verified-source transport differs")


def _install_verified_execution(
    raw_module: ModuleType, raw: Mapping[str, Any]
) -> tuple[object, object]:
    if any(name == "bu" or name.startswith("bu.") for name in sys.modules):
        raise FitChildRefused("bu was imported before execution-source admission")
    execution_source = EXECUTION_SOURCE.resolve(strict=True)
    site_packages = PINNED_SITE_PACKAGES.resolve(strict=True)
    forbidden = {
        CONTROLLER_SOURCE.resolve(strict=True),
        execution_source,
        site_packages,
    }
    inherited_standard_library = tuple(sys.path)
    for value in inherited_standard_library:
        if type(value) is not str or not value:
            raise FitChildRefused("inherited standard-library path is not fixed")
        try:
            candidate = Path(value).resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise FitChildRefused("inherited standard-library path is invalid") from exc
        if candidate in forbidden:
            raise FitChildRefused("project or site path was admitted before authority")

    source_finder_api = getattr(raw_module, "verified_source_finder", None)
    dependency_finder_api = getattr(raw_module, "verified_dependency_finder", None)
    if not callable(source_finder_api) or not callable(dependency_finder_api):
        raise FitChildRefused("verified execution-import API is unavailable")
    try:
        source_finder = source_finder_api(raw, "execution")
        dependency_finder = dependency_finder_api(raw)
    except (OSError, TypeError, ValueError) as exc:
        raise FitChildRefused("verified execution importers are unavailable") from exc
    if (
        getattr(source_finder, "binding_marker", None)
        != "week8_d161_verified_source_v2"
        or getattr(dependency_finder, "binding_marker", None)
        != "week8_d161_verified_dependency_source_v1"
    ):
        raise FitChildRefused("verified execution importer marker differs")

    previous_meta_path = tuple(sys.meta_path)
    sys.path[:] = [
        str(execution_source),
        *inherited_standard_library,
        str(site_packages),
    ]
    sys.meta_path[:] = [source_finder, dependency_finder, *previous_meta_path]
    if (
        sys.meta_path[:2] != [source_finder, dependency_finder]
        or tuple(sys.meta_path[2:]) != previous_meta_path
        or sys.path
        != [str(execution_source), *inherited_standard_library, str(site_packages)]
    ):
        raise FitChildRefused("verified execution import machinery was not installed")
    importlib.invalidate_caches()
    return source_finder, dependency_finder


def _validate_isolated_runtime() -> None:
    """Require CPython isolated mode before any project source is imported."""

    observed = {
        "dont_write_bytecode": int(getattr(sys.flags, "dont_write_bytecode", 0)),
        "isolated": int(getattr(sys.flags, "isolated", 0)),
        "ignore_environment": int(getattr(sys.flags, "ignore_environment", 0)),
        "no_site": int(getattr(sys.flags, "no_site", 0)),
        "no_user_site": int(getattr(sys.flags, "no_user_site", 0)),
        "safe_path": int(getattr(sys.flags, "safe_path", 0)),
        "utf8_mode": int(getattr(sys.flags, "utf8_mode", 0)),
    }
    if observed != {
        "dont_write_bytecode": 1,
        "isolated": 1,
        "ignore_environment": 1,
        "no_site": 1,
        "no_user_site": 1,
        "safe_path": 1,
        "utf8_mode": 1,
    }:
        raise FitChildRefused(
            "fit child requires Python -I -S -B -X utf8 before project import"
        )


def _import_fixed_fit_worker(source_finder: object) -> Any:
    try:
        launch = importlib.import_module(
            "bu.experiments.week8_exp2a_repair_launch"
        )
    except (ImportError, OSError, TypeError, ValueError) as exc:
        raise FitChildRefused("historical repair launcher import refused") from exc
    specification = getattr(launch, "__spec__", None)
    loader = getattr(specification, "loader", None)
    expected_path = (
        EXECUTION_SOURCE
        / "bu"
        / "experiments"
        / "week8_exp2a_repair_launch.py"
    ).resolve(strict=True)
    try:
        observed_path = Path(launch.__file__).resolve(strict=True)
    except (AttributeError, OSError, TypeError) as exc:
        raise FitChildRefused("historical repair launcher path is unavailable") from exc
    if (
        observed_path != expected_path
        or getattr(loader, "binding_marker", None)
        != "week8_d161_verified_source_v2"
        or getattr(loader, "tree_kind", None) != "execution"
        or getattr(source_finder, "binding_marker", None)
        != "week8_d161_verified_source_v2"
    ):
        raise FitChildRefused("historical repair launcher lacks verified authority")
    callback = getattr(launch, "_fit_worker", None)
    if not callable(callback):
        raise FitChildRefused("historical fixed _fit_worker is unavailable")
    for name, module in tuple(sys.modules.items()):
        if name != "bu" and not name.startswith("bu."):
            continue
        module_loader = getattr(getattr(module, "__spec__", None), "loader", None)
        if (
            getattr(module_loader, "binding_marker", None)
            != "week8_d161_verified_source_v2"
            or getattr(module_loader, "tree_kind", None) != "execution"
        ):
            raise FitChildRefused(f"loaded project module {name} is not verified")
    return callback


def _historical_execution_git_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return the raw-authority-proven frozen Git identity, or fail closed."""

    if type(raw) is not dict:
        raise FitChildRefused("historical Git adapter lacks raw authority")
    execution = raw.get("execution")
    if type(execution) is not dict:
        raise FitChildRefused("historical Git adapter lacks execution authority")
    if (
        execution.get("path") != str(EXECUTION_WORKTREE.resolve(strict=True))
        or execution.get("git_commit") != EXECUTION_COMMIT
        or execution.get("branch") != "HEAD"
        or execution.get("detached") is not True
        or type(execution.get("worktree_inventory_digest")) is not str
        or _HEX64.fullmatch(execution["worktree_inventory_digest"]) is None
        or type(execution.get("stability_observations")) is not int
        or execution["stability_observations"] < 2
    ):
        raise FitChildRefused("historical Git execution authority differs")
    return execution


def _historical_git_bindings(
    original: FunctionType, *, allow_incomplete: bool
) -> list[ModuleType]:
    """Find every already-imported exact alias of runrecord.git_state."""

    bindings: list[ModuleType] = []
    for name, module in sorted(tuple(sys.modules.items())):
        if name != "bu" and not name.startswith("bu."):
            continue
        if type(module) is not ModuleType:
            raise FitChildRefused(f"historical Git module {name} is not exact")
        namespace = vars(module)
        if "git_state" not in namespace:
            continue
        if namespace["git_state"] is original:
            bindings.append(module)
    required = {
        "bu.runrecord",
        "bu.experiments.confirmatory",
        "bu.experiments.fit_evidence",
        "bu.experiments.preflight",
    }
    if (
        not allow_incomplete
        and not required.issubset({module.__name__ for module in bindings})
    ):
        raise FitChildRefused("historical Git binding inventory is incomplete")
    return bindings


@contextmanager
def _verified_historical_git_state(
    raw: Mapping[str, Any], *, allow_imports: bool = False
):
    """Temporarily replace every frozen bare-Git call with sealed authority.

    The historical tree remains byte-for-byte unchanged.  During this one fit,
    each imported alias receives the same exact adapter, which returns the
    clean detached execution identity already proven by raw authority.  No Git
    process, repository config, hook, or fsmonitor helper is consulted.
    """

    execution = _historical_execution_git_row(raw)
    runrecord = sys.modules.get("bu.runrecord")
    if type(runrecord) is not ModuleType:
        raise FitChildRefused("historical runrecord module is unavailable")
    expected_source = (EXECUTION_SOURCE / "bu" / "runrecord.py").resolve(strict=True)
    loader = getattr(getattr(runrecord, "__spec__", None), "loader", None)
    original = getattr(runrecord, "git_state", None)
    git_state_type = getattr(runrecord, "GitState", None)
    project_root = getattr(runrecord, "PROJECT_ROOT", None)
    if (
        type(original) is not FunctionType
        or original.__module__ != "bu.runrecord"
        or original.__name__ != "git_state"
        or original.__qualname__ != "git_state"
        or original.__defaults__ != (None,)
        or original.__kwdefaults__ is not None
        or original.__closure__ is not None
        or original.__code__.co_argcount != 1
        or original.__code__.co_posonlyargcount != 0
        or original.__code__.co_kwonlyargcount != 0
        or Path(original.__code__.co_filename).resolve() != expected_source
        or type(git_state_type) is not type
        or git_state_type.__module__ != "bu.runrecord"
        or git_state_type.__name__ != "GitState"
        or not isinstance(project_root, Path)
        or project_root.resolve() != EXECUTION_WORKTREE.resolve(strict=True)
        or getattr(loader, "binding_marker", None)
        != "week8_d161_verified_source_v2"
        or getattr(loader, "tree_kind", None) != "execution"
    ):
        raise FitChildRefused("historical git_state identity or shape differs")
    preexisting_git_states: dict[ModuleType, object] = {}
    for name, module in sorted(tuple(sys.modules.items())):
        if name != "bu" and not name.startswith("bu."):
            continue
        if type(module) is not ModuleType:
            raise FitChildRefused(f"historical Git module {name} is not exact")
        if "git_state" in vars(module):
            preexisting_git_states[module] = vars(module)["git_state"]
    unseen_binding = object()
    bindings = _historical_git_bindings(original, allow_incomplete=allow_imports)

    def verified_git_state(repo: str | Path | None = None) -> Any:
        if repo is not None:
            if type(repo) is not str and not isinstance(repo, Path):
                raise FitChildRefused("historical git_state repository type differs")
            try:
                repository = Path(repo).resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise FitChildRefused(
                    "historical git_state repository is unavailable"
                ) from exc
            if repository != EXECUTION_WORKTREE.resolve(strict=True):
                raise FitChildRefused("historical git_state requested another repository")
        current = _historical_execution_git_row(raw)
        for module in bindings:
            if vars(module).get("git_state") is not verified_git_state:
                raise FitChildRefused("historical Git adapter changed during fit")
        if vars(runrecord).get("GitState") is not git_state_type:
            raise FitChildRefused("historical GitState type changed during fit")
        state = git_state_type(
            commit=current["git_commit"], dirty=False, branch=current["branch"]
        )
        if type(state) is not git_state_type:
            raise FitChildRefused("historical Git adapter returned another type")
        return state

    for module in bindings:
        module.git_state = verified_git_state
    if any(vars(module).get("git_state") is not verified_git_state for module in bindings):
        for module in bindings:
            module.git_state = original
        raise FitChildRefused("historical Git adapter could not be installed exactly")
    body_error: BaseException | None = None
    try:
        yield verified_git_state
    except BaseException as exc:
        body_error = exc
        raise
    finally:
        restore_error: BaseException | None = None
        try:
            if any(
                vars(module).get("git_state") is not verified_git_state
                for module in bindings
            ):
                raise FitChildRefused(
                    "historical Git adapter changed before restoration"
                )
            current_bindings: list[ModuleType] = []
            for name, module in sorted(tuple(sys.modules.items())):
                if name != "bu" and not name.startswith("bu."):
                    continue
                if type(module) is not ModuleType:
                    raise FitChildRefused(
                        f"historical Git module {name} changed during fit"
                    )
                namespace = vars(module)
                if "git_state" not in namespace:
                    continue
                current_value = namespace["git_state"]
                prior_value = preexisting_git_states.get(module, unseen_binding)
                if prior_value is original or prior_value is unseen_binding:
                    if current_value is not verified_git_state:
                        raise FitChildRefused(
                            "historical Git binding changed after import"
                        )
                    current_bindings.append(module)
                elif current_value is not prior_value:
                    raise FitChildRefused(
                        "unrelated historical Git binding changed during fit"
                    )
            required = {
                "bu.runrecord",
                "bu.experiments.confirmatory",
                "bu.experiments.fit_evidence",
                "bu.experiments.preflight",
            }
            if not required.issubset(
                {module.__name__ for module in current_bindings}
            ):
                raise FitChildRefused(
                    "historical Git binding inventory is incomplete after import"
                )
            for module in current_bindings:
                module.git_state = original
            if any(vars(module).get("git_state") is not original for module in bindings):
                raise FitChildRefused("historical Git adapter was not restored exactly")
        except BaseException as exc:
            restore_error = exc
            for module in bindings:
                try:
                    module.git_state = original
                except BaseException:
                    pass
            for name, module in tuple(sys.modules.items()):
                if (
                    (name == "bu" or name.startswith("bu."))
                    and type(module) is ModuleType
                    and vars(module).get("git_state") is verified_git_state
                ):
                    try:
                        module.git_state = original
                    except BaseException:
                        pass
        if restore_error is not None:
            if body_error is not None:
                raise FitChildRefused(
                    "historical Git adapter restoration failed after fit refusal"
                ) from restore_error
            raise FitChildRefused(
                "historical Git adapter restoration failed"
            ) from restore_error


def _success_message(result: object) -> dict[str, str]:
    if not isinstance(result, Mapping):
        raise TypeError(
            "isolated job callback must return a mapping for job_result.json"
        )
    result_json = json.dumps(
        dict(result),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return {"kind": "success", "result_json": result_json}


def _exception_message(exc: Exception) -> dict[str, str]:
    return {
        "kind": "python_exception",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }


def _publish_protocol(path: Path, message: Mapping[str, Any]) -> None:
    """Publish one complete canonical object atomically with no overwrite."""

    payload = _canonical_ascii(dict(message))
    runtime = _plain_directory(RUNTIME_TEMP, what="fixed D-161 runtime temp")
    if path.parent != runtime or not (
        _RESULT_NAME.fullmatch(path.name) is not None
        or _STARTUP_NAME.fullmatch(path.name) is not None
    ):
        raise FitChildRefused("fit-child result path changed before publication")
    if os.name != "nt":
        raise FitChildRefused("fit-child protocol publication requires Windows")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if os.path.lexists(temporary) or os.path.lexists(path):
        raise FitChildRefused("fit-child protocol publication path is occupied")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(temporary, flags, 0o600)
    except OSError as exc:
        raise FitChildRefused("fit-child protocol result cannot be created") from exc
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("zero-byte fit-child protocol write")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except OSError as exc:
        raise FitChildRefused("fit-child protocol result cannot be fsynced") from exc
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
    try:
        # On the fixed Windows host os.rename is an atomic no-overwrite move.
        os.rename(temporary, path)
    except OSError as exc:
        raise FitChildRefused("fit-child protocol result cannot be published") from exc


def _silence_standard_streams() -> None:
    """Make the nested protocol file the process's only output channel."""

    try:
        descriptor = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(descriptor, 1)
            os.dup2(descriptor, 2)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise FitChildRefused("fit-child stdout/stderr cannot be sealed") from exc


@contextmanager
def _fit_relocation_scope(raw_module: ModuleType, raw: Mapping[str, Any],
                          invocation: Mapping[str, Any], callback: Any):
    if type(raw_module) is not ModuleType or sys.modules.get(RAW_AUTHORITY_MODULE_NAME) is not raw_module:
        raise FitChildRefused("fit-child relocation raw module differs")
    helpers = raw_module.load_verified_relocation_helpers(raw)
    helper_binding = helpers.validate(raw)
    metadata = helpers.modules["metadata"]
    access = metadata.load_registered_access(helpers.modules["provenance"])
    binding = {
        "relocation_schema_version": 1, "attestation_sha256": access.attestation_sha256,
        "policy_sha256": metadata.POLICY_SHA256, "pair_count": metadata.EXPECTED_PAIR_COUNT,
        "document_count": metadata.EXPECTED_DOCUMENT_COUNT, "helpers": helper_binding,
    }
    if _canonical_ascii(binding) != _canonical_ascii(invocation["relocation"]):
        raise FitChildRefused("fit-child own relocation admission differs from worker")
    Launch = importlib.import_module("bu.experiments.week8_exp2a_repair_launch")
    Storage = importlib.import_module("bu.experiments.prefit_storage")
    if Launch._fit_worker is not callback:
        raise FitChildRefused("relocation scope received another scientific callback")
    history = metadata.OrphanLeaseReader(access, Launch, invocation["orphan_transition"])
    sources = metadata.SourceReaders(access, Launch.W, Launch.S)
    preflight = metadata.PreflightReaders(access, sources, Launch, Storage)
    checkpoints = metadata.CheckpointReaders(access, preflight)
    completed = metadata.CompletedJobReaders(access, checkpoints)
    try:
        with history.installed(), sources.installed(), preflight.installed(), checkpoints.installed(), completed.installed():
            history.lookup(metadata.OLD_LEASE_TOKEN)
            try:
                yield
            finally:
                history.lookup(metadata.OLD_LEASE_TOKEN)
    finally:
        if (
            sys.modules.get(RAW_AUTHORITY_MODULE_NAME) is not raw_module
            or helpers.validate(raw) != helper_binding
            or access.attestation_sha256 != binding["attestation_sha256"]
            or Launch._fit_worker is not callback
        ):
            raise FitChildRefused("fit-child relocation authority changed across fit")


def main() -> int:
    _silence_standard_streams()
    _validate_isolated_runtime()
    invocation, result_path, startup_path, startup_ack_path = _decode_invocation()
    try:
        attempt_dir, payload = _validate_invocation(invocation)
        startup = _publish_startup_hello(startup_path, invocation)
        _await_startup_ack(invocation, startup)
        raw_module = _load_bound_raw_authority()
        _validate_control_environment(raw_module, invocation)
        _gate, raw = _validate_entrypoint_gate(raw_module, invocation)
        _validate_transport(raw_module, raw, invocation)
        source_finder, _dependency_finder = _install_verified_execution(
            raw_module, raw
        )
        try:
            importlib.import_module("bu.runrecord")
        except (ImportError, OSError, TypeError, ValueError) as exc:
            raise FitChildRefused("historical runrecord import refused") from exc
        with _verified_historical_git_state(raw, allow_imports=True):
            callback = _import_fixed_fit_worker(source_finder)
            with _fit_relocation_scope(raw_module, raw, invocation, callback):
                message = _success_message(callback(Path(attempt_dir), payload))
    except Exception as exc:
        message = _exception_message(exc)
    _publish_protocol(result_path, message)
    return 0


if __name__ == "__main__":  # pragma: no cover - fixed subprocess contract
    raise SystemExit(main())
