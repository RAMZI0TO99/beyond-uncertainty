"""Deterministic, fail-closed Windows process-liveness evidence.

Week 8 recovery must never treat lease age as evidence that an owner died.
This module takes complete Toolhelp process snapshots and then probes every
recorded PID, the current controller, every visible recorded-PID descendant,
and every Python-looking process with kernel handles.  Returned objects contain
only strict JSON values, use stable ordering, and deliberately contain no
wall-clock timestamp.

The helper is read-only.  It cannot terminate a process, release a lease, or
write recovery evidence.  Callers must persist the returned snapshot through
the project's immutable evidence primitives while holding the appropriate
transition lock.

One snapshot can report only ``snapshot_clear``; it can never authorize
recovery.  The two-snapshot Week 8 gate reports ``pass`` only when:

* the controller is positively identified as the same live Python process;
* every recorded owner is absent from Toolhelp and ``OpenProcess`` twice;
* every other recorded process is positively dead in both observations;
* every Toolhelp descendant of a recorded PID is positively dead;
* no recorded-owner/worker ancestry contains a cycle or a missing link;
* no recorded PID is reused or otherwise ambiguous; and
* no other live or ambiguously inspectable Python process is present.

Toolhelp cannot prove the absence of arbitrary native descendants through an
unrelated missing parent chain.  The gate therefore makes the narrower claim
justified by this project's architecture: every scientific worker is Python,
all visible descendants are checked, and no other Python process survives or
is ambiguous in either observation.  Discovery recognizes only canonical
Python/PyPy executable leaf names; it deliberately does not guess that an
arbitrarily renamed native image is Python.  D-161 separately fixes every
scientific-process command to the pinned ``python.exe``, which is the
architecture invariant that makes this narrow discovery rule sufficient.  The
gate never claims complete native-process descendant absence.  An inaccessible
handle, an unexpected Win32 return value, inconsistent Toolhelp/handle
evidence, or a PID lacking the recorded creation ``FILETIME`` while still
occupied all fail closed.
"""

from __future__ import annotations

import ctypes
import json
import ntpath
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ctypes import wintypes


WINDOWS_LIVENESS_SCHEMA_VERSION = 1

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x00001000
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF
ERROR_INVALID_PARAMETER = 87
ERROR_NO_MORE_FILES = 18
MAX_PATH = 260
MAX_LONG_PATH = 32768

_MAX_DWORD = (1 << 32) - 1
_MAX_FILETIME = (1 << 64) - 1
_RECORD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}\Z")
_PYTHON_EXECUTABLE = re.compile(
    r"(?:pythonw?|pypy)(?:\d+(?:\.\d+)*)?(?:_d)?\.exe\Z",
    re.IGNORECASE,
)

_PROBE_KEYS = {
    "pid",
    "status",
    "creation_time_filetime",
    "executable_path",
    "wait_code",
    "error_stage",
    "winerror",
    "close_winerror",
}
_RAW_SNAPSHOT_KEYS = {
    "schema_version",
    "platform",
    "controller",
    "observation_index",
    "recorded_processes",
    "toolhelp_processes",
    "probes",
}


class ProcessLivenessError(ValueError):
    """Liveness could not be established without ambiguity."""


@dataclass(frozen=True)
class RecordedProcess:
    """Expected identity of one lease owner or supervised worker.

    ``creation_time_filetime`` is the raw unsigned 64-bit creation FILETIME
    from ``GetProcessTimes``.  It is optional only for legacy evidence.  A
    running PID without this value is ambiguous and therefore blocks the
    stability gate.  FILETIME values are emitted as decimal strings so no
    JSON consumer can silently round a 64-bit process identity.
    """

    record_id: str
    pid: int
    creation_time_filetime: int | None = None
    executable_path: str | None = None
    role: str = "worker"

    def __post_init__(self) -> None:
        _validate_record_id(self.record_id)
        _validate_pid(self.pid, what=f"recorded process {self.record_id!r} PID")
        if self.creation_time_filetime is not None:
            _validate_filetime(
                self.creation_time_filetime,
                what=f"recorded process {self.record_id!r} creation FILETIME",
            )
        if self.executable_path is not None:
            _validate_path(
                self.executable_path,
                what=f"recorded process {self.record_id!r} executable path",
            )
        if type(self.role) is not str or self.role not in {"owner", "worker"}:
            raise ProcessLivenessError(
                f"recorded process {self.record_id!r} role must be 'owner' "
                f"or 'worker', got {self.role!r}"
            )


class _ProcessApi(Protocol):
    def enumerate_processes(self) -> Sequence[Mapping[str, object]]: ...

    def probe_process(self, pid: int) -> Mapping[str, object]: ...


class _FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class _PROCESSENTRY32W(ctypes.Structure):
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
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


def _validate_record_id(value: object) -> str:
    if type(value) is not str or not _RECORD_ID.fullmatch(value):
        raise ProcessLivenessError(
            "record_id must be a safe nonempty identifier of at most 200 "
            f"characters, got {value!r}"
        )
    return value


def _validate_pid(value: object, *, what: str, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if type(value) is not int or not minimum <= value <= _MAX_DWORD:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ProcessLivenessError(
            f"{what} must be an exact {qualifier} DWORD integer, got {value!r}"
        )
    return value


def _validate_filetime(value: object, *, what: str) -> int:
    if type(value) is not int or not 0 < value <= _MAX_FILETIME:
        raise ProcessLivenessError(
            f"{what} must be an exact positive unsigned 64-bit integer, got {value!r}"
        )
    return value


def _validate_path(value: object, *, what: str) -> str:
    if type(value) is not str or not value or "\x00" in value:
        raise ProcessLivenessError(
            f"{what} must be a nonempty NUL-free string, got {value!r}"
        )
    return value


def _validate_error_code(value: object, *, what: str) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_DWORD:
        raise ProcessLivenessError(
            f"{what} must be an exact non-negative DWORD integer, got {value!r}"
        )
    return value


def _filetime_value(value: _FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _normalise_windows_path(value: str) -> str:
    return ntpath.normcase(ntpath.normpath(value.replace("/", "\\")))


def _paths_equal(left: str, right: str) -> bool:
    return _normalise_windows_path(left) == _normalise_windows_path(right)


def _validate_absolute_windows_path(value: object, *, what: str) -> str:
    path = _validate_path(value, what=what)
    if not ntpath.isabs(path):
        raise ProcessLivenessError(f"{what} must be absolute")
    return path


def _handle_value(handle: object) -> int:
    if handle is None:
        return 0
    if type(handle) is int:
        return handle
    value = ctypes.cast(handle, ctypes.c_void_p).value
    return 0 if value is None else int(value)


class _WindowsProcessApi:
    """Thin ctypes binding whose observations are normalized before return."""

    def __init__(self) -> None:
        if sys.platform != "win32" or not hasattr(ctypes, "WinDLL"):
            raise ProcessLivenessError(
                "real process-liveness capture requires Windows; pass a mocked "
                "API only in platform-safe tests"
            )
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_signatures()

    def _configure_signatures(self) -> None:
        kernel32 = self._kernel32
        kernel32.CreateToolhelp32Snapshot.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel32.Process32FirstW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_PROCESSENTRY32W),
        ]
        kernel32.Process32FirstW.restype = wintypes.BOOL
        kernel32.Process32NextW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_PROCESSENTRY32W),
        ]
        kernel32.Process32NextW.restype = wintypes.BOOL
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_FILETIME),
            ctypes.POINTER(_FILETIME),
            ctypes.POINTER(_FILETIME),
            ctypes.POINTER(_FILETIME),
        ]
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.SetLastError.argtypes = [wintypes.DWORD]
        kernel32.SetLastError.restype = None
        kernel32.GetLastError.argtypes = []
        kernel32.GetLastError.restype = wintypes.DWORD

    def _clear_error(self) -> None:
        self._kernel32.SetLastError(0)

    def _last_error(self) -> int:
        return int(self._kernel32.GetLastError())

    def _close(self, handle: object) -> int | None:
        self._clear_error()
        if self._kernel32.CloseHandle(handle):
            return None
        return self._last_error()

    def enumerate_processes(self) -> list[dict[str, object]]:
        self._clear_error()
        handle = self._kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        invalid_handle = ctypes.c_void_p(-1).value
        if _handle_value(handle) in {0, invalid_handle}:
            code = self._last_error()
            raise ProcessLivenessError(
                "CreateToolhelp32Snapshot failed with Win32 error " f"{code}"
            )

        entries: list[dict[str, object]] = []
        try:
            entry = _PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
            self._clear_error()
            available = bool(self._kernel32.Process32FirstW(handle, ctypes.byref(entry)))
            if not available:
                code = self._last_error()
                if code != ERROR_NO_MORE_FILES:
                    raise ProcessLivenessError(
                        f"Process32FirstW failed with Win32 error {code}"
                    )
            while available:
                entries.append(
                    {
                        "pid": int(entry.th32ProcessID),
                        "parent_pid": int(entry.th32ParentProcessID),
                        "exe_name": str(entry.szExeFile),
                    }
                )
                entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
                self._clear_error()
                available = bool(
                    self._kernel32.Process32NextW(handle, ctypes.byref(entry))
                )
                if not available:
                    code = self._last_error()
                    if code != ERROR_NO_MORE_FILES:
                        raise ProcessLivenessError(
                            f"Process32NextW failed with Win32 error {code}"
                        )
        finally:
            # This must run for *every* exception type, including failures in
            # Python-side normalization or a future refactor.  Leaking the
            # Toolhelp handle would make the observer itself unreliable.
            close_error = self._close(handle)
            if close_error is not None:
                raise ProcessLivenessError(
                    "CloseHandle for the Toolhelp snapshot failed with Win32 "
                    f"error {close_error}"
                )
        return entries

    @staticmethod
    def _empty_probe(pid: int) -> dict[str, object]:
        return {
            "pid": pid,
            "status": "error",
            "creation_time_filetime": None,
            "executable_path": None,
            "wait_code": None,
            "error_stage": None,
            "winerror": None,
            "close_winerror": None,
        }

    def probe_process(self, pid: int) -> dict[str, object]:
        _validate_pid(pid, what="probe PID", allow_zero=True)
        result = self._empty_probe(pid)
        access = PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
        self._clear_error()
        handle = self._kernel32.OpenProcess(access, False, pid)
        if _handle_value(handle) == 0:
            code = self._last_error()
            result["error_stage"] = "OpenProcess"
            result["winerror"] = code
            result["status"] = (
                "not_found" if code == ERROR_INVALID_PARAMETER else "error"
            )
            return result

        try:
            creation = _FILETIME()
            exit_time = _FILETIME()
            kernel = _FILETIME()
            user = _FILETIME()
            self._clear_error()
            if not self._kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                result["error_stage"] = "GetProcessTimes"
                result["winerror"] = self._last_error()
                return result
            result["creation_time_filetime"] = str(_filetime_value(creation))

            buffer = ctypes.create_unicode_buffer(MAX_LONG_PATH)
            length = wintypes.DWORD(len(buffer))
            self._clear_error()
            if not self._kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(length)
            ):
                result["error_stage"] = "QueryFullProcessImageNameW"
                result["winerror"] = self._last_error()
                return result
            if int(length.value) <= 0 or int(length.value) >= len(buffer):
                result["error_stage"] = "QueryFullProcessImageNameW"
                result["winerror"] = 0
                return result
            result["executable_path"] = buffer.value[: int(length.value)]

            self._clear_error()
            wait_code = int(self._kernel32.WaitForSingleObject(handle, 0))
            result["wait_code"] = wait_code
            if wait_code == WAIT_OBJECT_0:
                result["status"] = "signaled"
            elif wait_code == WAIT_TIMEOUT:
                result["status"] = "running"
            else:
                result["status"] = "error"
                result["error_stage"] = "WaitForSingleObject"
                result["winerror"] = (
                    self._last_error() if wait_code == WAIT_FAILED else 0
                )
        finally:
            close_error = self._close(handle)
            if close_error is not None:
                result["status"] = "error"
                result["error_stage"] = "CloseHandle"
                result["winerror"] = close_error
                result["close_winerror"] = close_error
        return result


def _capture_controller_executable_path(
    api: _ProcessApi | None,
    override: str | None,
) -> str:
    """Bind production capture to this interpreter; permit only fake injection."""

    if override is not None and (
        api is None or isinstance(api, _WindowsProcessApi)
    ):
        raise ProcessLivenessError(
            "controller sys.executable override is permitted only with an "
            "injected fake process API"
        )
    value = sys.executable if override is None else override
    return _validate_absolute_windows_path(
        value,
        what="controller declared sys.executable path",
    )


def _expectation_json(item: RecordedProcess) -> dict[str, object]:
    return {
        "record_id": item.record_id,
        "pid": item.pid,
        "role": item.role,
        "creation_time_filetime": (
            None
            if item.creation_time_filetime is None
            else str(item.creation_time_filetime)
        ),
        "executable_path": item.executable_path,
    }


def _normalise_recorded_processes(
    values: Sequence[RecordedProcess],
) -> list[dict[str, object]]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ProcessLivenessError(
            "recorded_processes must be a sequence of RecordedProcess objects"
        )
    result: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, value in enumerate(values):
        if type(value) is not RecordedProcess:
            raise ProcessLivenessError(
                "recorded_processes element "
                f"{index} must be an exact RecordedProcess, got "
                f"{type(value).__name__}"
            )
        if value.record_id in seen_ids:
            raise ProcessLivenessError(
                f"duplicate recorded process id {value.record_id!r}"
            )
        seen_ids.add(value.record_id)
        result.append(_expectation_json(value))
    return sorted(result, key=lambda row: (int(row["pid"]), str(row["record_id"])))


def _normalise_process_entries(
    values: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ProcessLivenessError("Toolhelp process inventory must be a sequence")
    result: list[dict[str, object]] = []
    seen: set[int] = set()
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise ProcessLivenessError(
                f"Toolhelp entry {index} must be a mapping"
            )
        if set(value) != {"pid", "parent_pid", "exe_name"}:
            raise ProcessLivenessError(
                f"Toolhelp entry {index} has an unexpected schema"
            )
        pid = _validate_pid(
            value["pid"], what=f"Toolhelp entry {index} PID", allow_zero=True
        )
        parent_pid = _validate_pid(
            value["parent_pid"],
            what=f"Toolhelp entry {index} parent PID",
            allow_zero=True,
        )
        exe_name = value["exe_name"]
        if type(exe_name) is not str or not exe_name or "\x00" in exe_name:
            raise ProcessLivenessError(
                f"Toolhelp entry {index} executable name must be nonempty and NUL-free"
            )
        if pid in seen:
            raise ProcessLivenessError(
                f"Toolhelp process snapshot contains duplicate PID {pid}"
            )
        seen.add(pid)
        result.append(
            {"pid": pid, "parent_pid": parent_pid, "exe_name": exe_name}
        )
    if not result:
        raise ProcessLivenessError(
            "Toolhelp process snapshot is empty; completeness is ambiguous"
        )
    return sorted(result, key=lambda row: int(row["pid"]))


def _validate_optional_decimal_filetime(value: object, *, what: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value.isascii() or not value.isdecimal():
        raise ProcessLivenessError(
            f"{what} must be a canonical decimal string or null, got {value!r}"
        )
    if value != str(int(value)):
        raise ProcessLivenessError(
            f"{what} must not contain signs or leading zeroes, got {value!r}"
        )
    _validate_filetime(int(value), what=what)
    return value


def _normalise_probe(value: Mapping[str, object], *, expected_pid: int) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ProcessLivenessError(
            f"probe for PID {expected_pid} has an unexpected schema"
        )
    try:
        probe_keys = set(value)
    except (TypeError, ValueError) as exc:
        raise ProcessLivenessError(
            f"probe for PID {expected_pid} has unhashable or malformed keys"
        ) from exc
    if probe_keys != _PROBE_KEYS:
        raise ProcessLivenessError(
            f"probe for PID {expected_pid} has an unexpected schema"
        )
    pid = _validate_pid(value["pid"], what="probe PID", allow_zero=True)
    if pid != expected_pid:
        raise ProcessLivenessError(
            f"probe requested PID {expected_pid} but returned PID {pid}"
        )
    status = value["status"]
    if type(status) is not str or status not in (
        "not_found",
        "running",
        "signaled",
        "error",
    ):
        raise ProcessLivenessError(
            f"probe for PID {pid} has invalid status {status!r}"
        )
    creation = _validate_optional_decimal_filetime(
        value["creation_time_filetime"],
        what=f"probe PID {pid} creation FILETIME",
    )
    path = value["executable_path"]
    if path is not None:
        _validate_path(path, what=f"probe PID {pid} executable path")
    wait_code = value["wait_code"]
    if wait_code is not None:
        _validate_error_code(wait_code, what=f"probe PID {pid} wait code")
    error_stage = value["error_stage"]
    if error_stage is not None and (
        type(error_stage) is not str
        or error_stage
        not in (
            "OpenProcess",
            "GetProcessTimes",
            "QueryFullProcessImageNameW",
            "WaitForSingleObject",
            "CloseHandle",
        )
    ):
        raise ProcessLivenessError(
            f"probe for PID {pid} has invalid error stage {error_stage!r}"
        )
    winerror = value["winerror"]
    if winerror is not None:
        _validate_error_code(winerror, what=f"probe PID {pid} Win32 error")
    close_winerror = value["close_winerror"]
    if close_winerror is not None:
        _validate_error_code(
            close_winerror, what=f"probe PID {pid} CloseHandle error"
        )

    if status == "not_found":
        if (
            error_stage != "OpenProcess"
            or winerror != ERROR_INVALID_PARAMETER
            or creation is not None
            or path is not None
            or wait_code is not None
            or close_winerror is not None
        ):
            raise ProcessLivenessError(
                f"probe for PID {pid} has malformed not_found evidence"
            )
    elif status in {"running", "signaled"}:
        expected_wait = WAIT_TIMEOUT if status == "running" else WAIT_OBJECT_0
        if (
            creation is None
            or path is None
            or wait_code != expected_wait
            or error_stage is not None
            or winerror is not None
            or close_winerror is not None
        ):
            raise ProcessLivenessError(
                f"probe for PID {pid} has malformed {status} evidence"
            )
    else:
        if error_stage is None or winerror is None:
            raise ProcessLivenessError(
                f"probe for PID {pid} error lacks API stage and Win32 code"
            )
        if error_stage == "CloseHandle" and close_winerror != winerror:
            raise ProcessLivenessError(
                f"probe for PID {pid} has inconsistent CloseHandle errors"
            )

    return {
        "pid": pid,
        "status": status,
        "creation_time_filetime": creation,
        "executable_path": path,
        "wait_code": wait_code,
        "error_stage": error_stage,
        "winerror": winerror,
        "close_winerror": close_winerror,
    }


def capture_windows_process_identity(
    pid: int | None = None,
    *,
    _api: _ProcessApi | None = None,
) -> dict[str, object]:
    """Capture one running process's kernel-issued identity.

    ``pid`` defaults to the current process.  Production always obtains the
    executable path from ``QueryFullProcessImageNameW`` through the existing
    Win32 backend; there is deliberately no path override.  ``_api`` is a
    private injection seam for platform-safe synthetic tests.

    A result is returned only when the exact requested PID is running, its
    creation ``FILETIME`` is a canonical positive value, its executable path
    is absolute, and the process handle closed successfully.
    """

    target_pid = os.getpid() if pid is None else pid
    _validate_pid(target_pid, what="kernel identity PID")
    api = _WindowsProcessApi() if _api is None else _api
    try:
        raw_probe = api.probe_process(target_pid)
        probe = _normalise_probe(raw_probe, expected_pid=target_pid)
    except ProcessLivenessError:
        raise
    except Exception as exc:
        raise ProcessLivenessError(
            f"kernel identity probe for PID {target_pid} failed"
        ) from exc

    if probe["status"] != "running":
        raise ProcessLivenessError(
            f"kernel identity probe for PID {target_pid} requires a running "
            f"process, got {probe['status']!r}"
        )

    creation_text = probe["creation_time_filetime"]
    if type(creation_text) is not str:  # guaranteed by _normalise_probe
        raise ProcessLivenessError(
            f"kernel identity probe for PID {target_pid} lacks creation FILETIME"
        )
    creation_time = _validate_filetime(
        int(creation_text),
        what=f"kernel identity PID {target_pid} creation FILETIME",
    )
    kernel_path = _validate_absolute_windows_path(
        probe["executable_path"],
        what=f"kernel identity PID {target_pid} executable path",
    )
    if not ntpath.splitdrive(kernel_path)[0]:
        raise ProcessLivenessError(
            f"kernel identity PID {target_pid} executable path must include "
            "an absolute drive or UNC share"
        )
    return {
        "pid": target_pid,
        "kernel_executable_path": kernel_path,
        "creation_time_100ns": creation_time,
    }


def _python_candidate(exe_name: str) -> bool:
    leaf = ntpath.basename(exe_name)
    return bool(_PYTHON_EXECUTABLE.fullmatch(leaf))


def _ancestry_assessments(
    entries: Sequence[Mapping[str, object]],
    *,
    recorded_pids: set[int],
) -> list[dict[str, object]]:
    """Resolve every non-recorded Toolhelp entry against recorded PID roots.

    A parent PID equal to a recorded PID is a descendant even when that
    recorded process is absent from the current snapshot.  Missing and cyclic
    chains which never reach a recorded PID are retained in the inventory as
    unrelated unresolved chains, but do not become recovery candidates: real
    Windows snapshots commonly contain processes whose original parent has
    already exited.
    """

    by_pid = {int(entry["pid"]): entry for entry in entries}
    result: list[dict[str, object]] = []
    for entry in entries:
        pid = int(entry["pid"])
        if pid in recorded_pids:
            continue
        path = [pid]
        seen = {pid}
        parent_pid = int(entry["parent_pid"])
        while True:
            if parent_pid == 0:
                ancestry_classification = "rooted"
                terminal_pid = 0
                if path[-1] != 0:
                    path.append(0)
                break
            path.append(parent_pid)
            if parent_pid in recorded_pids:
                ancestry_classification = "descendant"
                terminal_pid = parent_pid
                break
            if parent_pid in seen:
                ancestry_classification = "unrelated_cycle"
                terminal_pid = parent_pid
                break
            seen.add(parent_pid)
            parent = by_pid.get(parent_pid)
            if parent is None:
                ancestry_classification = "unrelated_missing"
                terminal_pid = parent_pid
                break
            parent_pid = int(parent["parent_pid"])
        result.append(
            {
                "pid": pid,
                "parent_pid": int(entry["parent_pid"]),
                "ancestry_path": path,
                "classification": ancestry_classification,
                "terminal_pid": terminal_pid,
            }
        )
    return sorted(result, key=lambda row: int(row["pid"]))


def _recorded_chain_ambiguities(
    entries: Sequence[Mapping[str, object]],
    *,
    recorded_pids: set[int],
) -> list[dict[str, object]]:
    """Return only missing/cyclic ancestry rooted at present recorded PIDs.

    This is intentionally narrower than treating every missing Windows parent
    as suspect.  A recorded PID absent from Toolhelp is adjudicated by its
    handle probe.  When it is present, however, its own ancestry is a genuine
    recorded-owner/worker chain and a missing link or repetition is retained
    as fail-closed ambiguity.
    """

    by_pid = {int(entry["pid"]): entry for entry in entries}
    result: list[dict[str, object]] = []
    for recorded_pid in sorted(recorded_pids):
        recorded_entry = by_pid.get(recorded_pid)
        if recorded_entry is None:
            continue
        path = [recorded_pid]
        seen = {recorded_pid}
        parent_pid = int(recorded_entry["parent_pid"])
        while parent_pid != 0:
            path.append(parent_pid)
            if parent_pid in seen:
                result.append(
                    {
                        "recorded_pid": recorded_pid,
                        "ancestry_path": path,
                        "classification": "cycle",
                        "terminal_pid": parent_pid,
                    }
                )
                break
            seen.add(parent_pid)
            parent = by_pid.get(parent_pid)
            if parent is None:
                result.append(
                    {
                        "recorded_pid": recorded_pid,
                        "ancestry_path": path,
                        "classification": "missing",
                        "terminal_pid": parent_pid,
                    }
                )
                break
            parent_pid = int(parent["parent_pid"])
    return result


def _entry_probe_consistency(
    entry: Mapping[str, object] | None,
    probe: Mapping[str, object],
) -> tuple[str, str]:
    status = str(probe["status"])
    if entry is None:
        if status == "not_found":
            return "dead", "absent_from_toolhelp_and_openprocess"
        return "ambiguous", "toolhelp_and_openprocess_disagree"
    if status == "not_found":
        return "dead", "exited_after_toolhelp_snapshot"
    if status == "error":
        return "ambiguous", f"{probe['error_stage']}_failed"
    path = str(probe["executable_path"])
    if ntpath.basename(path).casefold() != str(entry["exe_name"]).casefold():
        return "ambiguous", "toolhelp_and_handle_executable_disagree"
    if status == "signaled":
        return "dead", "process_handle_is_signaled"
    return "running", "process_handle_is_unsignaled"


def _classify_recorded(
    expectation: Mapping[str, object],
    entry: Mapping[str, object] | None,
    probe: Mapping[str, object],
) -> dict[str, object]:
    state, reason = _entry_probe_consistency(entry, probe)
    classification = "ambiguous"
    if state == "dead":
        classification = "dead_proven"
    elif state == "ambiguous":
        classification = "ambiguous"
    else:
        expected_creation = expectation["creation_time_filetime"]
        actual_creation = probe["creation_time_filetime"]
        if expected_creation is None:
            classification = "ambiguous"
            reason = "running_pid_has_no_recorded_creation_filetime"
        elif expected_creation != actual_creation:
            classification = "pid_reused"
            reason = "running_pid_creation_filetime_differs"
        else:
            expected_path = expectation["executable_path"]
            actual_path = str(probe["executable_path"])
            if expected_path is not None and not _paths_equal(
                str(expected_path), actual_path
            ):
                classification = "ambiguous"
                reason = "matching_process_time_but_executable_path_differs"
            else:
                classification = "live"
                reason = "recorded_process_is_still_running"
    return {
        **dict(expectation),
        "snapshot_present": entry is not None,
        "observed_creation_time_filetime": probe["creation_time_filetime"],
        "observed_executable_path": probe["executable_path"],
        "classification": classification,
        "reason": reason,
        "blocks_snapshot_clear": classification != "dead_proven",
    }


def _strict_json_round_trip(value: object) -> None:
    """Defend the evidence boundary against non-JSON or non-finite values."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        )
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProcessLivenessError(f"liveness snapshot is not strict JSON: {exc}") from exc
    if decoded != value:
        raise ProcessLivenessError(
            "liveness snapshot changes under a strict JSON round trip"
        )


def classify_windows_process_snapshot(
    snapshot: Mapping[str, object],
) -> dict[str, object]:
    """Validate and classify a raw or previously classified snapshot.

    The returned mapping is a fresh strict-JSON object with a replaced
    ``classification`` section.  Reclassification is therefore deterministic
    and never trusts an earlier verdict stored alongside the raw observations.
    A single snapshot is non-authorizing and necessarily carries its captured
    declaration; the public two-snapshot classifier and assertion gate bind
    that declaration to the current process's actual ``sys.executable``.
    """

    if not isinstance(snapshot, Mapping):
        raise ProcessLivenessError("liveness snapshot must be a mapping")
    raw = {key: value for key, value in snapshot.items() if key != "classification"}
    if set(raw) != _RAW_SNAPSHOT_KEYS:
        raise ProcessLivenessError("liveness snapshot has an unexpected schema")
    if (
        type(raw["schema_version"]) is not int
        or raw["schema_version"] != WINDOWS_LIVENESS_SCHEMA_VERSION
    ):
        raise ProcessLivenessError("unsupported Windows liveness schema version")
    if raw["platform"] != "windows":
        raise ProcessLivenessError("liveness snapshot platform must be 'windows'")
    observation_index = raw["observation_index"]
    if type(observation_index) is not int or observation_index not in {1, 2}:
        raise ProcessLivenessError("observation_index must be exact integer 1 or 2")

    controller = raw["controller"]
    if not isinstance(controller, Mapping) or set(controller) != {
        "pid",
        "declared_sys_executable_path",
    }:
        raise ProcessLivenessError("controller record has an unexpected schema")
    controller_pid = _validate_pid(controller["pid"], what="controller PID")
    declared_sys_executable_path = _validate_absolute_windows_path(
        controller["declared_sys_executable_path"],
        what="controller declared sys.executable path",
    )
    normalized_sys_executable_path = _normalise_windows_path(
        declared_sys_executable_path
    )

    recorded_raw = raw["recorded_processes"]
    if not isinstance(recorded_raw, list):
        raise ProcessLivenessError("recorded_processes must be a JSON array")
    recorded: list[dict[str, object]] = []
    seen_record_ids: set[str] = set()
    for index, value in enumerate(recorded_raw):
        if not isinstance(value, Mapping) or set(value) != {
            "record_id",
            "pid",
            "role",
            "creation_time_filetime",
            "executable_path",
        }:
            raise ProcessLivenessError(
                f"recorded process {index} has an unexpected schema"
            )
        record_id = _validate_record_id(value["record_id"])
        if record_id in seen_record_ids:
            raise ProcessLivenessError(f"duplicate recorded process id {record_id!r}")
        seen_record_ids.add(record_id)
        pid = _validate_pid(value["pid"], what=f"recorded process {record_id!r} PID")
        role = value["role"]
        if type(role) is not str or role not in {"owner", "worker"}:
            raise ProcessLivenessError(
                f"recorded process {record_id!r} role must be 'owner' or 'worker'"
            )
        creation = _validate_optional_decimal_filetime(
            value["creation_time_filetime"],
            what=f"recorded process {record_id!r} creation FILETIME",
        )
        path = value["executable_path"]
        if path is not None:
            _validate_path(path, what=f"recorded process {record_id!r} executable path")
        recorded.append(
            {
                "record_id": record_id,
                "pid": pid,
                "role": role,
                "creation_time_filetime": creation,
                "executable_path": path,
            }
        )
    recorded.sort(key=lambda row: (int(row["pid"]), str(row["record_id"])))

    entries_raw = raw["toolhelp_processes"]
    if not isinstance(entries_raw, list):
        raise ProcessLivenessError("toolhelp_processes must be a JSON array")
    entries = _normalise_process_entries(entries_raw)
    entries_by_pid = {int(row["pid"]): row for row in entries}
    recorded_pids = {int(row["pid"]) for row in recorded}
    ancestry = _ancestry_assessments(entries, recorded_pids=recorded_pids)
    ancestry_by_pid = {int(row["pid"]): row for row in ancestry}
    recorded_chain_ambiguities = _recorded_chain_ambiguities(
        entries, recorded_pids=recorded_pids
    )
    descendant_pids = {
        int(row["pid"])
        for row in ancestry
        if row["classification"] == "descendant"
    }

    python_pids = {
        int(row["pid"])
        for row in entries
        if _python_candidate(str(row["exe_name"]))
    }
    required_probe_pids = (
        {controller_pid}
        | python_pids
        | recorded_pids
        | descendant_pids
    )
    probes_raw = raw["probes"]
    if not isinstance(probes_raw, list):
        raise ProcessLivenessError("probes must be a JSON array")
    probes: list[dict[str, object]] = []
    probes_by_pid: dict[int, dict[str, object]] = {}
    for index, value in enumerate(probes_raw):
        if not isinstance(value, Mapping):
            raise ProcessLivenessError(f"probe {index} must be a mapping")
        pid_value = value.get("pid")
        pid = _validate_pid(pid_value, what=f"probe {index} PID", allow_zero=True)
        if pid in probes_by_pid:
            raise ProcessLivenessError(f"duplicate process probe for PID {pid}")
        probe = _normalise_probe(value, expected_pid=pid)
        probes.append(probe)
        probes_by_pid[pid] = probe
    if set(probes_by_pid) != required_probe_pids:
        raise ProcessLivenessError(
            "process probes do not exactly cover controller, recorded, "
            "visible-descendant, and Python-candidate PIDs"
        )
    probes.sort(key=lambda row: int(row["pid"]))

    controller_entry = entries_by_pid.get(controller_pid)
    controller_probe = probes_by_pid[controller_pid]
    controller_state, controller_reason = _entry_probe_consistency(
        controller_entry, controller_probe
    )
    controller_classification = "ambiguous"
    controller_kernel_path = controller_probe["executable_path"]
    if (
        controller_state == "running"
        and type(controller_kernel_path) is str
        and _python_candidate(controller_kernel_path)
    ):
        controller_classification = "running"
        controller_reason = "controller_pid_handle_and_python_image_confirmed"
    elif controller_state == "running":
        controller_reason = "controller_kernel_image_is_not_python"

    launcher_candidate: dict[str, object] | None = None
    launcher_rejection_reason: str | None = None
    launcher_rejection_pid: int | None = None
    if (
        controller_classification == "running"
        and controller_entry is not None
        and type(controller_kernel_path) is str
        and not _paths_equal(
            declared_sys_executable_path, controller_kernel_path
        )
    ):
        parent_pid = int(controller_entry["parent_pid"])
        parent_entry = entries_by_pid.get(parent_pid)
        if (
            parent_pid > 0
            and parent_pid != controller_pid
            and parent_pid not in recorded_pids
            and parent_entry is not None
            and _python_candidate(str(parent_entry["exe_name"]))
        ):
            parent_probe = probes_by_pid[parent_pid]
            parent_state, _ = _entry_probe_consistency(
                parent_entry, parent_probe
            )
            parent_kernel_path = parent_probe["executable_path"]
            if (
                parent_state == "running"
                and type(parent_kernel_path) is str
                and _paths_equal(
                    declared_sys_executable_path, parent_kernel_path
                )
            ):
                parent_creation = int(str(parent_probe["creation_time_filetime"]))
                controller_creation = int(
                    str(controller_probe["creation_time_filetime"])
                )
                if parent_creation >= controller_creation:
                    launcher_rejection_pid = parent_pid
                    launcher_rejection_reason = (
                        "direct_parent_creation_not_before_controller_"
                        "pid_reuse_ambiguous"
                    )
                else:
                    launcher_candidate = {
                        "pid": parent_pid,
                        "controller_pid": controller_pid,
                        "observed_creation_time_filetime": parent_probe[
                            "creation_time_filetime"
                        ],
                        "observed_executable_path": parent_kernel_path,
                        "normalized_executable_path": _normalise_windows_path(
                            parent_kernel_path
                        ),
                        "classification": "live",
                        "relation": "controller_launcher_candidate",
                        "reason": (
                            "direct_parent_live_python_matches_declared_"
                            "sys_executable_and_is_strictly_older_than_controller"
                        ),
                    }

    recorded_classifications = [
        _classify_recorded(
            expectation,
            entries_by_pid.get(int(expectation["pid"])),
            probes_by_pid[int(expectation["pid"])],
        )
        for expectation in recorded
    ]

    descendant_classifications: list[dict[str, object]] = []
    live_descendants: list[int] = []
    ambiguous_descendants: list[int] = []
    for descendant_pid in sorted(descendant_pids):
        descendant_entry = entries_by_pid[descendant_pid]
        descendant_probe = probes_by_pid[descendant_pid]
        state, reason = _entry_probe_consistency(
            descendant_entry, descendant_probe
        )
        if state == "dead":
            descendant_classification = "dead_proven"
        elif state == "running":
            descendant_classification = "live"
            live_descendants.append(descendant_pid)
        else:
            descendant_classification = "ambiguous"
            ambiguous_descendants.append(descendant_pid)
        ancestry_row = ancestry_by_pid[descendant_pid]
        descendant_classifications.append(
            {
                "pid": descendant_pid,
                "parent_pid": descendant_entry["parent_pid"],
                "ancestry_path": ancestry_row["ancestry_path"],
                "recorded_ancestor_pid": ancestry_row["terminal_pid"],
                "observed_creation_time_filetime": descendant_probe[
                    "creation_time_filetime"
                ],
                "observed_executable_path": descendant_probe[
                    "executable_path"
                ],
                "classification": descendant_classification,
                "reason": reason,
                "blocks_snapshot_clear": descendant_classification
                != "dead_proven",
            }
        )

    ancestry_ambiguities = [dict(row) for row in recorded_chain_ambiguities]

    python_classifications: list[dict[str, object]] = []
    other_python: list[int] = []
    ambiguous_python: list[int] = []
    for pid in sorted(python_pids):
        entry = entries_by_pid[pid]
        probe = probes_by_pid[pid]
        state, reason = _entry_probe_consistency(entry, probe)
        relation = "controller" if pid == controller_pid else "other"
        if relation == "controller":
            state = controller_classification
            reason = controller_reason
        elif launcher_candidate is not None and pid == launcher_candidate["pid"]:
            relation = "controller_launcher_candidate"
            state = "running"
            reason = str(launcher_candidate["reason"])
        elif launcher_rejection_pid is not None and pid == launcher_rejection_pid:
            reason = str(launcher_rejection_reason)
        if relation == "other" and state == "running":
            other_python.append(pid)
        elif relation == "other" and state == "ambiguous":
            ambiguous_python.append(pid)
        python_classifications.append(
            {
                "pid": pid,
                "parent_pid": entry["parent_pid"],
                "exe_name": entry["exe_name"],
                "observed_creation_time_filetime": probe[
                    "creation_time_filetime"
                ],
                "observed_executable_path": probe["executable_path"],
                "relation": relation,
                "classification": state,
                "reason": reason,
            }
        )

    refusal_reasons: list[str] = []
    if controller_classification != "running":
        refusal_reasons.append(f"controller:{controller_reason}")
    for row in recorded_classifications:
        if bool(row["blocks_snapshot_clear"]):
            refusal_reasons.append(f"recorded:{row['record_id']}:{row['reason']}")
    for row in descendant_classifications:
        if bool(row["blocks_snapshot_clear"]):
            refusal_reasons.append(f"descendant:{row['pid']}:{row['reason']}")
    for row in ancestry_ambiguities:
        refusal_reasons.append(
            f"ancestry:recorded:{row['recorded_pid']}:"
            f"{row['classification']}:"
            f"{row['terminal_pid']}"
        )
    refusal_reasons.extend(f"other_python:{pid}:running" for pid in other_python)
    refusal_reasons.extend(
        f"other_python:{pid}:ambiguous" for pid in ambiguous_python
    )
    if launcher_rejection_reason is not None:
        refusal_reasons.append(
            f"controller_launcher:{launcher_rejection_reason}"
        )
    refusal_reasons = sorted(set(refusal_reasons))

    classification = {
        "controller": {
            "pid": controller_pid,
            "declared_sys_executable_path": declared_sys_executable_path,
            "normalized_sys_executable_path": normalized_sys_executable_path,
            "observed_creation_time_filetime": controller_probe[
                "creation_time_filetime"
            ],
            "observed_executable_path": controller_probe["executable_path"],
            "classification": controller_classification,
            "reason": controller_reason,
        },
        "controller_launcher_candidate": launcher_candidate,
        "controller_launcher_rejection_reason": launcher_rejection_reason,
        "recorded_processes": recorded_classifications,
        "ancestry_assessments": ancestry,
        "ancestry_ambiguities": ancestry_ambiguities,
        "descendant_processes": descendant_classifications,
        "live_descendant_processes": live_descendants,
        "ambiguous_descendant_processes": ambiguous_descendants,
        "python_processes": python_classifications,
        "other_python_processes": other_python,
        "ambiguous_python_processes": ambiguous_python,
        "refusal_reasons": refusal_reasons,
        "assurance_scope": "week8_python_worker_architecture",
        "python_discovery_scope": (
            "canonical_python_pypy_executable_leaf_names_only"
        ),
        "scientific_process_command_invariant": "D-161:pinned_python.exe",
        "complete_native_descendant_absence_claimed": False,
        "verdict": "snapshot_clear" if not refusal_reasons else "snapshot_refuse",
    }
    result = {
        "schema_version": WINDOWS_LIVENESS_SCHEMA_VERSION,
        "platform": "windows",
        "observation_index": observation_index,
        "controller": {
            "pid": controller_pid,
            "declared_sys_executable_path": declared_sys_executable_path,
        },
        "recorded_processes": recorded,
        "toolhelp_processes": entries,
        "probes": probes,
        "classification": classification,
    }
    _strict_json_round_trip(result)
    return result


def capture_windows_process_snapshot(
    recorded_processes: Sequence[RecordedProcess],
    *,
    controller_pid: int | None = None,
    _api: _ProcessApi | None = None,
    _observation_index: int = 1,
    _controller_sys_executable_path: str | None = None,
) -> dict[str, object]:
    """Capture one observation which cannot by itself authorize recovery.

    ``_api`` is a private dependency-injection seam for synthetic tests.  A
    production caller must omit it, which selects the ctypes Win32 backend.
    """

    pid = os.getpid() if controller_pid is None else controller_pid
    declared_sys_executable_path = _capture_controller_executable_path(
        _api,
        _controller_sys_executable_path,
    )
    _validate_pid(pid, what="controller PID")
    if type(_observation_index) is not int or _observation_index not in {1, 2}:
        raise ProcessLivenessError("_observation_index must be exact integer 1 or 2")
    recorded = _normalise_recorded_processes(recorded_processes)
    api = _WindowsProcessApi() if _api is None else _api
    entries = _normalise_process_entries(api.enumerate_processes())
    ancestry = _ancestry_assessments(
        entries,
        recorded_pids={int(row["pid"]) for row in recorded},
    )
    ancestry_candidate_pids = {
        int(row["pid"])
        for row in ancestry
        if row["classification"] == "descendant"
    }
    query_pids = (
        {pid}
        | {int(row["pid"]) for row in recorded}
        | ancestry_candidate_pids
        | {
            int(row["pid"])
            for row in entries
            if _python_candidate(str(row["exe_name"]))
        }
    )
    probes = [
        _normalise_probe(api.probe_process(query_pid), expected_pid=query_pid)
        for query_pid in sorted(query_pids)
    ]
    raw = {
        "schema_version": WINDOWS_LIVENESS_SCHEMA_VERSION,
        "platform": "windows",
        "observation_index": _observation_index,
        "controller": {
            "pid": pid,
            "declared_sys_executable_path": declared_sys_executable_path,
        },
        "recorded_processes": recorded,
        "toolhelp_processes": entries,
        "probes": probes,
    }
    return classify_windows_process_snapshot(raw)


def _classify_windows_process_stability(
    first_snapshot: Mapping[str, object],
    second_snapshot: Mapping[str, object],
    *,
    expected_controller_sys_executable_path: str,
) -> dict[str, object]:
    """Classify two observations under the Week 8 Python-worker gate.

    A pass is intentionally narrower than complete native-descendant proof.
    It relies on the frozen architecture in which every scientific worker is
    Python, while also checking every descendant still visible in Toolhelp.
    """

    expected_controller_path = _validate_absolute_windows_path(
        expected_controller_sys_executable_path,
        what="expected actual controller sys.executable path",
    )
    first = classify_windows_process_snapshot(first_snapshot)
    second = classify_windows_process_snapshot(second_snapshot)
    if first["observation_index"] != 1 or second["observation_index"] != 2:
        raise ProcessLivenessError(
            "stability requires independently captured observations indexed 1 and 2"
        )
    if first["controller"] != second["controller"]:
        raise ProcessLivenessError("stability observations name different controllers")
    declared_controller_path = first["controller"][
        "declared_sys_executable_path"
    ]
    if not _paths_equal(
        str(declared_controller_path), expected_controller_path
    ):
        raise ProcessLivenessError(
            "snapshot-declared controller sys.executable path does not match "
            "the expected actual sys.executable path"
        )
    if first["recorded_processes"] != second["recorded_processes"]:
        raise ProcessLivenessError(
            "stability observations use different recorded-process expectations"
        )

    recorded = first["recorded_processes"]
    if not isinstance(recorded, list):  # classifier guarantees this
        raise ProcessLivenessError("recorded-process evidence is malformed")
    owner_ids = sorted(
        str(row["record_id"])
        for row in recorded
        if isinstance(row, Mapping) and row.get("role") == "owner"
    )
    if not owner_ids:
        raise ProcessLivenessError(
            "two-snapshot stability requires at least one recorded owner"
        )

    first_classification = first["classification"]
    second_classification = second["classification"]
    if not isinstance(first_classification, Mapping) or not isinstance(
        second_classification, Mapping
    ):
        raise ProcessLivenessError("snapshot classification is malformed")

    first_controller = first_classification["controller"]
    second_controller = second_classification["controller"]
    if not isinstance(first_controller, Mapping) or not isinstance(
        second_controller, Mapping
    ):
        raise ProcessLivenessError("controller classification is malformed")
    controller_same_process = (
        first_controller["classification"] == "running"
        and second_controller["classification"] == "running"
        and first_controller["observed_creation_time_filetime"]
        == second_controller["observed_creation_time_filetime"]
        and first_controller["observed_executable_path"]
        == second_controller["observed_executable_path"]
    )

    first_declared_path = str(first_controller["declared_sys_executable_path"])
    second_declared_path = str(second_controller["declared_sys_executable_path"])
    first_controller_path = first_controller["observed_executable_path"]
    second_controller_path = second_controller["observed_executable_path"]
    first_launcher_required = (
        type(first_controller_path) is str
        and not _paths_equal(first_declared_path, first_controller_path)
    )
    second_launcher_required = (
        type(second_controller_path) is str
        and not _paths_equal(second_declared_path, second_controller_path)
    )
    controller_launcher_required = (
        first_launcher_required or second_launcher_required
    )

    first_launcher_candidate = first_classification[
        "controller_launcher_candidate"
    ]
    second_launcher_candidate = second_classification[
        "controller_launcher_candidate"
    ]
    for index, candidate in (
        (1, first_launcher_candidate),
        (2, second_launcher_candidate),
    ):
        if candidate is not None and not isinstance(candidate, Mapping):
            raise ProcessLivenessError(
                f"snapshot {index} controller launcher candidate is malformed"
            )

    controller_launcher: dict[str, object] | None = None
    controller_launcher_stable = False
    if not controller_launcher_required:
        controller_launcher_stable = (
            first_launcher_candidate is None
            and second_launcher_candidate is None
        )
    elif isinstance(first_launcher_candidate, Mapping) and isinstance(
        second_launcher_candidate, Mapping
    ):
        launcher_identity_fields = (
            "pid",
            "observed_creation_time_filetime",
            "normalized_executable_path",
        )
        controller_launcher_stable = all(
            first_launcher_candidate[field]
            == second_launcher_candidate[field]
            for field in launcher_identity_fields
        )
        if controller_launcher_stable:
            controller_launcher = {
                "pid": first_launcher_candidate["pid"],
                "controller_pid": first_launcher_candidate["controller_pid"],
                "observed_creation_time_filetime": first_launcher_candidate[
                    "observed_creation_time_filetime"
                ],
                "observed_executable_path": first_launcher_candidate[
                    "observed_executable_path"
                ],
                "normalized_executable_path": first_launcher_candidate[
                    "normalized_executable_path"
                ],
                "classification": "live",
                "relation": "controller_launcher",
                "reason": "stable_direct_parent_venv_launcher",
            }

    def classified_rows(
        snapshot_classification: Mapping[str, object], key: str
    ) -> list[Mapping[str, object]]:
        rows = snapshot_classification[key]
        if not isinstance(rows, list) or not all(
            isinstance(row, Mapping) for row in rows
        ):
            raise ProcessLivenessError(f"{key} classification is malformed")
        return rows

    first_recorded = {
        str(row["record_id"]): row
        for row in classified_rows(first_classification, "recorded_processes")
    }
    second_recorded = {
        str(row["record_id"]): row
        for row in classified_rows(second_classification, "recorded_processes")
    }
    owner_absence: list[dict[str, object]] = []
    for owner_id in owner_ids:
        first_owner = first_recorded[owner_id]
        second_owner = second_recorded[owner_id]
        first_absent = (
            first_owner["classification"] == "dead_proven"
            and first_owner["reason"] == "absent_from_toolhelp_and_openprocess"
            and first_owner["snapshot_present"] is False
        )
        second_absent = (
            second_owner["classification"] == "dead_proven"
            and second_owner["reason"] == "absent_from_toolhelp_and_openprocess"
            and second_owner["snapshot_present"] is False
        )
        owner_absence.append(
            {
                "record_id": owner_id,
                "first_absent": first_absent,
                "second_absent": second_absent,
            }
        )
    owners_absent_twice = all(
        row["first_absent"] is True and row["second_absent"] is True
        for row in owner_absence
    )

    all_recorded_dead_twice = all(
        row["classification"] == "dead_proven"
        for row in (*first_recorded.values(), *second_recorded.values())
    )
    first_descendants = classified_rows(
        first_classification, "descendant_processes"
    )
    second_descendants = classified_rows(
        second_classification, "descendant_processes"
    )
    all_visible_descendants_dead_twice = all(
        row["classification"] == "dead_proven"
        for row in (*first_descendants, *second_descendants)
    )
    no_other_python_twice = all(
        not snapshot_classification["other_python_processes"]
        and not snapshot_classification["ambiguous_python_processes"]
        for snapshot_classification in (first_classification, second_classification)
    )
    no_recorded_chain_ambiguity_twice = all(
        not snapshot_classification["ancestry_ambiguities"]
        for snapshot_classification in (first_classification, second_classification)
    )

    unresolved_unrelated_ancestry = sorted(
        {
            (index, int(row["pid"]), str(row["classification"]))
            for index, snapshot_classification in (
                (1, first_classification),
                (2, second_classification),
            )
            for row in classified_rows(
                snapshot_classification, "ancestry_assessments"
            )
            if row["classification"]
            in {"unrelated_missing", "unrelated_cycle"}
        }
    )

    refusal_reasons = [
        f"snapshot_1:{reason}"
        for reason in first_classification["refusal_reasons"]
    ] + [
        f"snapshot_2:{reason}"
        for reason in second_classification["refusal_reasons"]
    ]
    if not controller_same_process:
        refusal_reasons.append("stability:controller_identity_changed")
    if first_launcher_required != second_launcher_required:
        refusal_reasons.append("stability:controller_launcher_mode_drifted")
    if not controller_launcher_stable:
        refusal_reasons.append(
            "stability:controller_launcher_missing_ambiguous_or_drifted"
        )
    for row in owner_absence:
        if row["first_absent"] is not True:
            refusal_reasons.append(
                f"stability:owner:{row['record_id']}:not_absent_in_snapshot_1"
            )
        if row["second_absent"] is not True:
            refusal_reasons.append(
                f"stability:owner:{row['record_id']}:not_absent_in_snapshot_2"
            )
    if not all_recorded_dead_twice:
        refusal_reasons.append("stability:not_all_recorded_processes_dead_twice")
    if not all_visible_descendants_dead_twice:
        refusal_reasons.append("stability:not_all_visible_descendants_dead_twice")
    if not no_other_python_twice:
        refusal_reasons.append("stability:other_or_ambiguous_python_present")
    if not no_recorded_chain_ambiguity_twice:
        refusal_reasons.append("stability:recorded_chain_ambiguity_present")
    refusal_reasons = sorted(set(str(reason) for reason in refusal_reasons))

    result = {
        "schema_version": WINDOWS_LIVENESS_SCHEMA_VERSION,
        "platform": "windows",
        "protocol": "two_snapshot_python_worker_gate",
        "assurance_scope": "week8_python_worker_architecture",
        "expected_controller_sys_executable_path": expected_controller_path,
        "normalized_expected_controller_sys_executable_path": (
            _normalise_windows_path(expected_controller_path)
        ),
        "python_discovery_scope": (
            "canonical_python_pypy_executable_leaf_names_only"
        ),
        "scientific_process_command_invariant": "D-161:pinned_python.exe",
        "complete_native_descendant_absence_claimed": False,
        "native_descendant_limitation": (
            "Toolhelp missing parent chains cannot prove absence of arbitrary "
            "native descendants; discovery recognizes only canonical Python/"
            "PyPy executable leaf names and does not classify arbitrary renamed "
            "native images; D-161 separately fixes every scientific process "
            "command to the pinned python.exe"
        ),
        "snapshots": [first, second],
        "stability": {
            "controller_same_process": controller_same_process,
            "controller_launcher_required": controller_launcher_required,
            "controller_launcher_stable": controller_launcher_stable,
            "controller_launcher": controller_launcher,
            "owner_absence": owner_absence,
            "owners_absent_twice": owners_absent_twice,
            "all_recorded_processes_dead_twice": all_recorded_dead_twice,
            "all_visible_descendants_dead_twice": (
                all_visible_descendants_dead_twice
            ),
            "no_other_live_or_ambiguous_python_twice": no_other_python_twice,
            "no_recorded_chain_ambiguity_twice": (
                no_recorded_chain_ambiguity_twice
            ),
            "unresolved_unrelated_ancestry": [
                {
                    "observation_index": index,
                    "pid": pid,
                    "classification": ancestry_classification,
                }
                for index, pid, ancestry_classification in unresolved_unrelated_ancestry
            ],
            "refusal_reasons": refusal_reasons,
            "verdict": "pass" if not refusal_reasons else "refuse",
        },
    }
    _strict_json_round_trip(result)
    return result


def classify_windows_process_stability(
    first_snapshot: Mapping[str, object],
    second_snapshot: Mapping[str, object],
) -> dict[str, object]:
    """Reclassify two snapshots bound to this process's real executable path."""

    return _classify_windows_process_stability(
        first_snapshot,
        second_snapshot,
        expected_controller_sys_executable_path=sys.executable,
    )


def capture_windows_process_stability(
    recorded_processes: Sequence[RecordedProcess],
    *,
    controller_pid: int | None = None,
    _api: _ProcessApi | None = None,
    _controller_sys_executable_path: str | None = None,
) -> dict[str, object]:
    """Capture two sequential kernel observations and apply the narrow gate."""

    expected_controller_path = _capture_controller_executable_path(
        _api,
        _controller_sys_executable_path,
    )
    api = _WindowsProcessApi() if _api is None else _api
    first = capture_windows_process_snapshot(
        recorded_processes,
        controller_pid=controller_pid,
        _api=api,
        _observation_index=1,
        _controller_sys_executable_path=_controller_sys_executable_path,
    )
    second = capture_windows_process_snapshot(
        recorded_processes,
        controller_pid=controller_pid,
        _api=api,
        _observation_index=2,
        _controller_sys_executable_path=_controller_sys_executable_path,
    )
    return _classify_windows_process_stability(
        first,
        second,
        expected_controller_sys_executable_path=expected_controller_path,
    )


def _assert_windows_stability_gate(
    report: Mapping[str, object],
    *,
    expected_controller_sys_executable_path: str,
) -> dict[str, object]:
    """Private validation seam; public assertion always supplies sys.executable."""

    if not isinstance(report, Mapping) or not isinstance(report.get("snapshots"), list):
        raise ProcessLivenessError("stability report must contain two snapshots")
    snapshots = report["snapshots"]
    if len(snapshots) != 2 or not all(
        isinstance(snapshot, Mapping) for snapshot in snapshots
    ):
        raise ProcessLivenessError("stability report must contain two snapshots")
    classified = _classify_windows_process_stability(
        snapshots[0],
        snapshots[1],
        expected_controller_sys_executable_path=(
            expected_controller_sys_executable_path
        ),
    )
    stability = classified["stability"]
    if not isinstance(stability, Mapping):  # classifier creates this
        raise ProcessLivenessError("stability classification is malformed")
    if stability["verdict"] != "pass":
        reasons = stability["refusal_reasons"]
        raise ProcessLivenessError(
            "Windows two-snapshot stability gate refused recovery: "
            + ", ".join(str(reason) for reason in reasons)
        )
    return classified


def assert_windows_stability_gate(
    report: Mapping[str, object],
) -> dict[str, object]:
    """Require a pass after binding historical evidence to ``sys.executable``."""

    return _assert_windows_stability_gate(
        report,
        expected_controller_sys_executable_path=sys.executable,
    )


__all__ = [
    "WINDOWS_LIVENESS_SCHEMA_VERSION",
    "ProcessLivenessError",
    "RecordedProcess",
    "assert_windows_stability_gate",
    "capture_windows_process_identity",
    "capture_windows_process_snapshot",
    "capture_windows_process_stability",
    "classify_windows_process_snapshot",
    "classify_windows_process_stability",
]
