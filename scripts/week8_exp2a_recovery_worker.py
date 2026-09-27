"""One-use bootstrap for the D-161 Week-8 E2A continuation epoch.

The controller publishes one sealed ``bootstrap-invocation.json`` twin and
passes only its record digest in ``BU_D161_INVOCATION_DIGEST``.  This process
validates its own source, interpreter and controller authority, then consumes
the invocation by publishing ``bootstrap-claim.json`` with an exclusive
create.  A claim is permanent: a complete claim, a one-sided claim, or a prior
terminal record all prohibit another lower launch.

Only after the claim files have been file-fsynced and exclusively linked does
this module import ``bu`` from the clean detached execution worktree.  POSIX
directory fsync is attempted and reported truthfully by the helper; Python has
no portable Windows directory-fsync operation, so Windows does not claim that
extra durability guarantee.  Three exact, temporary adapters bind the
historical lease lookup, replace the historical spawn context with the
verified D-166 child transport, and replace its picklability probe with an
identity-only validator that never serializes a callback or payload.  Lower stdout and
stderr are captured at the process descriptor and Windows standard-handle
boundary, reduced to hash/count evidence, and removed from the fixed runtime
temp before return.  Success and every
post-claim failure publish an independently copied, sealed operational
``bootstrap-terminal.json``.  No record or stdout object contains scientific
values, labels, ratios, exclusions, H2 statistics, or raw lower output.
"""

from __future__ import annotations

import errno
import base64
import hashlib
import importlib
import importlib.machinery
import importlib.util
import io
import json
import logging
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import types
import zipimport
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


BOOTSTRAP_SCHEMA_VERSION = 4
RECOVERY_SCHEMA_VERSION = 3
RECOVERY_ID = "week8-exp2a-d161-2026-09-02-attempt-001"
DECISION_ID = "D-161"
EXECUTION_COMMIT = "4515d5165756c8d1669d38d2ee854fa1051b1017"
# supervisor.py at the exact frozen execution commit, also used by epoch001.
EXECUTION_LEASE_SCHEMA_VERSION = 2
INVOCATION_ENV = "BU_D161_INVOCATION_DIGEST"
ENTRYPOINT_GATE_ENVIRONMENT_NAME = "BU_D161_ENTRYPOINT_GATE"
CHILD_BUNDLE_ENVIRONMENT_NAME = "BU_D161_CHILD_BUNDLE_SHA256"
FIT_CHILD_INVOCATION_ENVIRONMENT_NAME = "BU_D161_FIT_CHILD_INVOCATION_BASE64"
FIT_CHILD_INVOCATION_DIGEST_ENVIRONMENT_NAME = "BU_D161_FIT_CHILD_INVOCATION_SHA256"
RAW_AUTHORITY_MODULE_NAME = "_bu_week8_d161_raw_authority"
CHILD_TRANSPORT_SCHEMA_VERSION = 1
FIT_CHILD_INVOCATION_SCHEMA_VERSION = 3
FIT_CHILD_STARTUP_SCHEMA_VERSION = 1
FIT_CHILD_STARTUP_TIMEOUT_SECONDS = 300.0
EXPECTED_CHILD_BOOTSTRAP_LITERAL_SHA256 = (
    "b5859376695dbccb07c49d6b2c2d620024eef2aa25cc05220223cc8273e4756c"
)
FIT_CHILD_BOOTSTRAP_LITERAL = (
    "import sys\n"
    "if sys.flags.isolated!=1 or sys.flags.ignore_environment!=1 or sys.flags.no_site!=1 or sys.flags.no_user_site!=1 or sys.flags.safe_path!=1 or sys.flags.dont_write_bytecode!=1 or sys.flags.utf8_mode!=1: raise ValueError('child interpreter startup policy differs')\n"
    "import base64,hashlib,importlib.machinery,importlib.util,json,os\n"
    "def _pairs(p):\n"
    " d={}\n"
    " for k,v in p:\n"
    "  if k in d: raise ValueError('duplicate child-bundle key')\n"
    "  d[k]=v\n"
    " return d\n"
    "b=sys.stdin.buffer.read()\n"
    "e=os.environ.get('BU_D161_CHILD_BUNDLE_SHA256','')\n"
    "if hashlib.sha256(b).hexdigest()!=e: raise ValueError('child bundle digest differs')\n"
    "x=json.loads(b.decode('ascii'),object_pairs_hook=_pairs,parse_constant=lambda t:(_ for _ in ()).throw(ValueError('non-finite child bundle')))\n"
    "if type(x) is not dict or set(x)!={'child_transport_schema_version','record_type','logical_path','script_sha256','script_base64','raw_helper_path','raw_helper_sha256','raw_helper_base64','record_digest'}: raise ValueError('child bundle shape differs')\n"
    "u={k:v for k,v in x.items() if k!='record_digest'}\n"
    "c=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')\n"
    "if b!=c(x) or x['child_transport_schema_version']!=1 or x['record_type']!='week8_d161_verified_child_bundle' or hashlib.sha256(c(u)).hexdigest()!=x['record_digest']: raise ValueError('child bundle policy differs')\n"
    "h=base64.b64decode(x['raw_helper_base64'],validate=True);s=base64.b64decode(x['script_base64'],validate=True)\n"
    "if hashlib.sha256(h).hexdigest()!=x['raw_helper_sha256'] or hashlib.sha256(s).hexdigest()!=x['script_sha256']: raise ValueError('child source hash differs')\n"
    "n='_bu_week8_d161_raw_authority';l=importlib.machinery.SourceFileLoader(n,x['raw_helper_path']);q=importlib.util.spec_from_loader(n,l)\n"
    "if q is None: raise ValueError('raw helper specification unavailable')\n"
    "m=importlib.util.module_from_spec(q);m.__source_sha256__=x['raw_helper_sha256'];sys.modules[n]=m;exec(compile(h,x['raw_helper_path'],'exec',dont_inherit=True),m.__dict__)\n"
    "sys.argv=[x['logical_path']];globals()['__file__']=x['logical_path'];globals()['__transport_source_sha256__']=x['script_sha256'];globals()['__transport_bundle_sha256__']=e\n"
    "exec(compile(s,x['logical_path'],'exec',dont_inherit=True),globals(),globals())\n"
)
if (
    hashlib.sha256(FIT_CHILD_BOOTSTRAP_LITERAL.encode("utf-8")).hexdigest()
    != EXPECTED_CHILD_BOOTSTRAP_LITERAL_SHA256
):
    raise RuntimeError("nested fit-child bootstrap literal differs")

OLD_LEASE_TOKEN = "c66ea75437c043ba9a1113e0a31d2f8d"
OLD_LEASE_PID = 48_960
ORPHAN_JOB_ID = "178f4ef3ae1e-s1001"
ORPHAN_CHILD_PID = 29_480
HIDDEN_PARTIAL_NAME = ".178f4ef3ae1e-s1001.19rl_x0_.partial"

WORKSPACE_ROOT = Path("D:/Aenv/pro2")
CONTROLLER_WORKTREE = WORKSPACE_ROOT / "week8-recovery-controller-worktree"
EXECUTION_WORKTREE = WORKSPACE_ROOT / "week8-e2a-execution-4515-worktree"
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
PINNED_GIT = Path(
    "D:/Aenv/pro2/runtimes/"
    "git/mingw64/bin/git.exe"
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
PINNED_GIT_RUNTIME_ROOT = PINNED_GIT.parent
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
EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256 = (
    "73d6f0e5cb126ffde136a3746b620236c847b3791a3eec688ddbd649ab304a3e"
)
PINNED_SITE_PACKAGES = (
    WORKSPACE_ROOT / "pro2" / ".venv" / "Lib" / "site-packages"
)
CONTROLLER_MODULE = (
    CONTROLLER_WORKTREE
    / "src"
    / "bu"
    / "experiments"
    / "week8_exp2a_recovery.py"
)
BOOTSTRAP_SCRIPT = CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_worker.py"
INSPECTOR_SCRIPT = CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_inspector.py"
FIT_CHILD_SCRIPT = (
    CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_fit_child.py"
)
ENTRYPOINT_SCRIPT = (
    CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_entrypoint.py"
)
RAW_AUTHORITY_HELPER = (
    CONTROLLER_WORKTREE / "scripts" / "week8_recovery_raw_authority.py"
)
EXPECTED_RAW_AUTHORITY_HELPER_SHA256 = (
    "9067c7572692a4f0bc779488613c0e81f82233d8145bc1bb795e34f176e523aa"
)
RUNTIME_TEMP = WORKSPACE_ROOT / "week8-exp2a-recovery-runtime-2026-09-02-attempt-001"

RECOVERY_ROOT = WORKSPACE_ROOT / "week8-exp2a-recovery-2026-09-02-attempt-001"
RECOVERY_COPY_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-recovery-2026-09-02-attempt-001-project-evidence"
)
INCIDENT_FILE = "incident.json"
EPOCH001_TERMINAL_FILE = "epoch-001-terminal.json"
TRANSITION_INTENT_FILE = "transition-intent.json"
TRANSITION_COMPLETION_FILE = "transition-completion.json"
RECOVERY_COMPLETION_FILE = "recovery-completion.json"
BOOTSTRAP_INVOCATION_FILE = "bootstrap-invocation.json"
BOOTSTRAP_CLAIM_FILE = "bootstrap-claim.json"
BOOTSTRAP_TERMINAL_FILE = "bootstrap-terminal.json"
BOOTSTRAP_POSTMORTEM_FILE = "bootstrap-postmortem-completion.json"

OUTPUT_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-output"
SYNC_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-project-evidence"
PREPARATION_ROOT = WORKSPACE_ROOT / "week8-execution-preparation-2026-09-01-attempt-001"
PREPARATION_ORIGINAL_ROOT = PREPARATION_ROOT / "exp2a-original"
PREPARATION_COPY_ROOT = PREPARATION_ROOT / "exp2a-project-evidence"
PREFLIGHT_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-preflight"
START_DIRECTORY = "week8_exp2a_repair_starts"
REPORT_DIRECTORY = "week8_exp2a_repair_reports"
PREFLIGHT_FILE = "week8_preflight_report.json"

EXPECTED_OLD_LEASE_SHA256 = "ac3879395be164ea6b57dc10382e93236eacb7a76b222897bddbda58d2597f70"
EXPECTED_OLD_CHECKPOINT_SHA256 = "a8dc8652d4000753a4b7e3731bbecaf09d448f72d56d98bdb15610188c583169"
EXPECTED_OLD_CHECKPOINT_DIGEST = "3ec6d54d1bb0434bd7d4a28ee5d4c55fc3d1955f0d20a8577f267537d4f9cee5"
EXPECTED_OLD_EVENT_STREAM = "13207af2f0a1d461cf471acc7dc9eeef03b6113dda3712acd778d5e4bf4dfc45"
EXPECTED_OLD_EVENT_TAIL_FILE = "cd49822ee99ddd909596d314a99e4749944580fdb4176a7e76bf43f9ef02b2ac"
EXPECTED_COUNTS = {"executed": 111, "resumed": 150, "synced": 261, "total": 261}

_HEX32 = re.compile(r"[0-9a-f]{32}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_FIT_RESULT_NAME = re.compile(r"fit-child-result-([0-9a-f]{64})\.json\Z")
_FIT_STARTUP_NAME = re.compile(r"fit-child-startup-([0-9a-f]{64})\.json\Z")
_FIT_STARTUP_ACK_NAME = re.compile(
    r"fit-child-startup-ack-([0-9a-f]{64})\.json\Z"
)
_BU_MODULE_ID = re.compile(r"bu(?:\.[A-Za-z_]\w*)*\Z")
_REPARSE_POINT = 0x0400
_BASE_KEYS = {
    "recovery_schema_version",
    "recovery_id",
    "decision_id",
    "record_type",
    "scientific_outcomes_consulted",
    "scientific_values_emitted",
}


class BootstrapRefused(ValueError):
    """The fixed one-use bootstrap cannot safely advance."""


class ClaimedBootstrapRefused(BootstrapRefused):
    """A consumed invocation failed and has an operational terminal record."""

    def __init__(self, output: Mapping[str, Any]):
        super().__init__("the consumed D-161 invocation terminated with refusal")
        self.output = dict(output)


class CapturedLowerRefused(BootstrapRefused):
    """A lower launch/refusal whose streams have only hash/count evidence."""

    def __init__(self, error: BaseException, output_capture: Mapping[str, Any]):
        super().__init__(f"contained lower launch refused with {type(error).__name__}")
        self.output_capture = dict(output_capture)


_CAPTURE_FILENAMES = {
    "stdout": ".lower-stdout.capture",
    "stderr": ".lower-stderr.capture",
}
_CAPTURE_CHUNK_BYTES = 1024 * 1024
_STANDARD_FDS = {"stdout": 1, "stderr": 2}
_WINDOWS_STD_HANDLE_IDS = {"stdout": -11, "stderr": -12}


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BootstrapRefused("bootstrap evidence must be strict JSON") from exc


def _canonical_ascii(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise BootstrapRefused("bootstrap authority must be canonical ASCII JSON") from exc


def _json_file_bytes(value: object) -> bytes:
    return _canonical(value) + b"\n"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise BootstrapRefused(f"cannot hash required file {path}") from exc
    return digest.hexdigest()


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BootstrapRefused(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_bytes().decode("utf-8"),
            object_pairs_hook=_no_duplicate_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                BootstrapRefused(f"non-finite JSON value {token!r}")
            ),
        )
    except BootstrapRefused:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapRefused(f"cannot read strict JSON {path}") from exc
    if type(value) is not dict:
        raise BootstrapRefused(f"{path} must contain one JSON object")
    return value


def _expect_keys(value: object, keys: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise BootstrapRefused(f"{what} has missing or extra fields")
    return value


def _expect_sha(value: object, *, what: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise BootstrapRefused(f"{what} is not canonical lowercase SHA256")
    return value


def _seal(payload: Mapping[str, Any], field: str = "record_digest") -> dict[str, Any]:
    if field in payload:
        raise BootstrapRefused(f"cannot seal an object already containing {field!r}")
    document = dict(payload)
    return {**document, field: _sha_bytes(_canonical(document))}


def _validate_seal(value: object, *, field: str = "record_digest", what: str) -> dict[str, Any]:
    if type(value) is not dict or field not in value:
        raise BootstrapRefused(f"{what} is not a sealed object")
    _expect_sha(value[field], what=f"{what} {field}")
    expected = _seal({key: item for key, item in value.items() if key != field}, field)
    if _canonical(value) != _canonical(expected):
        raise BootstrapRefused(f"{what} content digest differs")
    return value


def _is_reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & _REPARSE_POINT)


def _plain_file(path: Path, *, what: str) -> Path:
    if not os.path.lexists(path):
        raise BootstrapRefused(f"{what} is missing")
    try:
        info = path.lstat()
    except OSError as exc:
        raise BootstrapRefused(f"cannot inspect {what}") from exc
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISREG(info.st_mode):
        raise BootstrapRefused(f"{what} is not a plain regular file")
    return path


def _plain_directory(path: Path, *, what: str) -> Path:
    if not os.path.lexists(path):
        raise BootstrapRefused(f"{what} is missing")
    try:
        info = path.lstat()
    except OSError as exc:
        raise BootstrapRefused(f"cannot inspect {what}") from exc
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
        raise BootstrapRefused(f"{what} is not a plain directory")
    return path


def _capture_root() -> Path:
    """Return the one authorized empty root for transient lower stream bytes."""

    root = _plain_directory(RUNTIME_TEMP, what="project-local runtime temp").resolve()
    try:
        root.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError as exc:
        raise BootstrapRefused("runtime temp escaped the project workspace") from exc
    try:
        if any(root.iterdir()):
            raise BootstrapRefused("project-local recovery runtime temp is not empty")
    except OSError as exc:
        raise BootstrapRefused("cannot inspect project-local recovery runtime temp") from exc
    return root


def _capture_file_evidence(path: Path, *, stream_name: str) -> dict[str, Any]:
    """Hash one closed capture file without retaining or returning its bytes.

    ``write_count`` is a legacy bootstrap-schema field.  At the descriptor
    boundary producer write calls cannot be recovered truthfully (the OS may
    merge or split them), so it records the deterministic count of non-empty
    chunks consumed by this digest pass.  ``byte_count`` remains the exact
    number of captured bytes.
    """

    digest = hashlib.sha256()
    byte_count = 0
    digest_chunk_count = 0
    try:
        with _plain_file(path, what=f"lower {stream_name} capture").open("rb") as handle:
            while chunk := handle.read(_CAPTURE_CHUNK_BYTES):
                digest.update(chunk)
                byte_count += len(chunk)
                digest_chunk_count += 1
        if path.stat().st_size != byte_count:
            raise BootstrapRefused(f"lower {stream_name} capture size changed while hashing")
    except BootstrapRefused:
        raise
    except OSError as exc:
        raise BootstrapRefused(f"cannot hash lower {stream_name} capture") from exc
    return {
        "sha256": digest.hexdigest(),
        "byte_count": byte_count,
        "write_count": digest_chunk_count,
    }


def _windows_standard_handles() -> dict[str, int]:
    if os.name != "nt":
        return {}
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetStdHandle.argtypes = [ctypes.c_ulong]
    kernel32.GetStdHandle.restype = ctypes.c_void_p
    invalid = ctypes.c_void_p(-1).value
    result: dict[str, int] = {}
    for stream_name, identifier in _WINDOWS_STD_HANDLE_IDS.items():
        handle = kernel32.GetStdHandle(ctypes.c_ulong(identifier & 0xFFFFFFFF))
        numeric = 0 if handle is None else int(handle)
        if numeric == invalid:
            raise BootstrapRefused(
                f"cannot read the Windows {stream_name} standard handle"
            )
        result[stream_name] = numeric
    return result


def _set_windows_standard_handle(stream_name: str, handle: int) -> None:
    if os.name != "nt":
        return
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.SetStdHandle.argtypes = [ctypes.c_ulong, ctypes.c_void_p]
    kernel32.SetStdHandle.restype = ctypes.c_int
    identifier = _WINDOWS_STD_HANDLE_IDS[stream_name]
    if not kernel32.SetStdHandle(
        ctypes.c_ulong(identifier & 0xFFFFFFFF), ctypes.c_void_p(handle)
    ):
        raise BootstrapRefused(
            f"cannot set the Windows {stream_name} standard handle"
        )


def _os_handle_for_fd(descriptor: int) -> int:
    if os.name != "nt":
        return descriptor
    import msvcrt

    try:
        handle = msvcrt.get_osfhandle(descriptor)
    except OSError as exc:
        raise BootstrapRefused("cannot resolve a Windows capture handle") from exc
    if handle == -1:
        raise BootstrapRefused("Windows capture handle is invalid")
    return int(handle)


def _flush_stream(stream: object) -> None:
    flush = getattr(stream, "flush", None)
    if callable(flush):
        flush()


def _logging_handlers() -> list[logging.StreamHandler[Any]]:
    loggers: list[logging.Logger] = [logging.getLogger()]
    for candidate in logging.Logger.manager.loggerDict.values():
        if isinstance(candidate, logging.Logger):
            loggers.append(candidate)
    handlers: list[logging.StreamHandler[Any]] = []
    seen: set[int] = set()
    for logger in loggers:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and id(handler) not in seen:
                seen.add(id(handler))
                handlers.append(handler)
    return handlers


def _capture_lower_output(
    operation: Callable[[], object],
) -> tuple[object, BaseException | None, dict[str, Any]]:
    """Run ``operation`` behind process-wide descriptor/Windows-handle capture.

    File descriptors 1 and 2, Python's current stream objects, standard
    logging handlers, native writes, and inheriting child processes all target
    two private files beneath ``RUNTIME_TEMP``.  The files are closed, hashed,
    counted, and removed before this function returns.  Restoration or cleanup
    uncertainty always replaces an otherwise successful result with refusal.
    """

    root = _capture_root()
    paths = {
        name: root / filename for name, filename in _CAPTURE_FILENAMES.items()
    }
    capture_fds: dict[str, int] = {}
    saved_fds: dict[str, int] = {}
    saved_windows: dict[str, int] = {}
    replacement_streams: dict[str, io.TextIOWrapper] = {}
    saved_streams = {"stdout": sys.stdout, "stderr": sys.stderr}
    rebound_handlers: list[tuple[logging.StreamHandler[Any], object]] = []
    result: object = None
    operation_error: BaseException | None = None
    cleanup_errors: list[BaseException] = []

    try:
        for stream in saved_streams.values():
            _flush_stream(stream)
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        for stream_name, path in paths.items():
            capture_fds[stream_name] = os.open(path, flags, 0o600)
            os.set_inheritable(capture_fds[stream_name], True)
        saved_windows = _windows_standard_handles()
        for stream_name, standard_fd in _STANDARD_FDS.items():
            saved_fds[stream_name] = os.dup(standard_fd)
            os.set_inheritable(saved_fds[stream_name], False)
        for stream_name, standard_fd in _STANDARD_FDS.items():
            os.dup2(capture_fds[stream_name], standard_fd, inheritable=True)
            _set_windows_standard_handle(
                stream_name, _os_handle_for_fd(standard_fd)
            )
        for stream_name, standard_fd in _STANDARD_FDS.items():
            binary = os.fdopen(
                os.dup(standard_fd), "wb", buffering=0, closefd=True
            )
            replacement_streams[stream_name] = io.TextIOWrapper(
                binary,
                encoding="utf-8",
                errors="backslashreplace",
                newline="",
                line_buffering=True,
                write_through=True,
            )
        sys.stdout = replacement_streams["stdout"]
        sys.stderr = replacement_streams["stderr"]
        for handler in _logging_handlers():
            stream = getattr(handler, "stream", None)
            for stream_name, saved_stream in saved_streams.items():
                if stream is saved_stream:
                    handler.setStream(replacement_streams[stream_name])
                    rebound_handlers.append((handler, saved_stream))
                    break
        try:
            result = operation()
        except BaseException as exc:
            operation_error = exc
    except BaseException as exc:
        operation_error = exc
    finally:
        for handler, stream in reversed(rebound_handlers):
            try:
                handler.setStream(stream)
            except BaseException as exc:
                cleanup_errors.append(exc)
        for stream in (*replacement_streams.values(), *saved_streams.values()):
            try:
                _flush_stream(stream)
            except BaseException as exc:
                cleanup_errors.append(exc)
        sys.stdout = saved_streams["stdout"]
        sys.stderr = saved_streams["stderr"]
        for stream in replacement_streams.values():
            try:
                stream.close()
            except BaseException as exc:
                cleanup_errors.append(exc)
        for stream_name, standard_fd in _STANDARD_FDS.items():
            saved_fd = saved_fds.get(stream_name)
            if saved_fd is not None:
                try:
                    os.dup2(saved_fd, standard_fd, inheritable=True)
                except BaseException as exc:
                    cleanup_errors.append(exc)
        for stream_name, handle in saved_windows.items():
            try:
                _set_windows_standard_handle(stream_name, handle)
            except BaseException as exc:
                cleanup_errors.append(exc)
        for descriptor in (*capture_fds.values(), *saved_fds.values()):
            try:
                os.close(descriptor)
            except BaseException as exc:
                cleanup_errors.append(exc)

    output_capture: dict[str, Any] = {}
    for stream_name, path in paths.items():
        try:
            output_capture[stream_name] = _capture_file_evidence(
                path, stream_name=stream_name
            )
        except BaseException as exc:
            cleanup_errors.append(exc)
    for path in paths.values():
        try:
            path.unlink(missing_ok=True)
        except BaseException as exc:
            cleanup_errors.append(exc)
    try:
        if any(root.iterdir()):
            cleanup_errors.append(
                BootstrapRefused("project-local recovery runtime temp was not cleaned")
            )
    except BaseException as exc:
        cleanup_errors.append(exc)
    if set(output_capture) != {"stdout", "stderr"}:
        raise BootstrapRefused(
            "file-descriptor capture did not produce complete stream evidence"
        )
    if cleanup_errors:
        operation_error = BootstrapRefused(
            "file-descriptor capture cleanup or restoration failed"
        )
    return result, operation_error, output_capture


def _same_bytes(left: Path, right: Path, *, what: str) -> str:
    _plain_file(left, what=f"{what} original")
    _plain_file(right, what=f"{what} copy")
    try:
        if os.path.samefile(left, right):
            raise BootstrapRefused(f"{what} twins alias one filesystem object")
        left_bytes = left.read_bytes()
        right_bytes = right.read_bytes()
    except OSError as exc:
        raise BootstrapRefused(f"cannot compare {what} twins") from exc
    if left_bytes != right_bytes:
        raise BootstrapRefused(f"{what} twins differ")
    digest = _sha_bytes(left_bytes)
    if _sha_file(left) != digest or _sha_file(right) != digest:
        raise BootstrapRefused(f"{what} changed during read-back")
    return digest


def _record_paths(name: str) -> tuple[Path, Path]:
    allowed = {
        INCIDENT_FILE,
        EPOCH001_TERMINAL_FILE,
        TRANSITION_INTENT_FILE,
        TRANSITION_COMPLETION_FILE,
        RECOVERY_COMPLETION_FILE,
        BOOTSTRAP_INVOCATION_FILE,
        BOOTSTRAP_CLAIM_FILE,
        BOOTSTRAP_TERMINAL_FILE,
        BOOTSTRAP_POSTMORTEM_FILE,
    }
    if name not in allowed:
        raise BootstrapRefused(f"unknown bootstrap record name {name!r}")
    return RECOVERY_ROOT / "records" / name, RECOVERY_COPY_ROOT / "records" / name


def _any_record_path(name: str) -> bool:
    return any(os.path.lexists(path) for path in _record_paths(name))


def _finalization_guard_path() -> Path:
    active = _active_lease_path()
    return active.with_name(".week7-production.lease-transition.lock")


def _validate_finalization_guard_file(path: Path, handle: Any) -> None:
    try:
        path_info = path.lstat()
        handle_info = os.fstat(handle.fileno())
    except OSError as exc:
        raise BootstrapRefused("cannot attest the recovery finalization guard") from exc
    if (
        stat.S_ISLNK(path_info.st_mode)
        or _is_reparse(path_info)
        or not stat.S_ISREG(path_info.st_mode)
        or not stat.S_ISREG(handle_info.st_mode)
        or int(getattr(path_info, "st_nlink", 0)) != 1
        or int(getattr(handle_info, "st_nlink", 0)) != 1
        or any(
            getattr(path_info, name, None) != getattr(handle_info, name, None)
            for name in ("st_dev", "st_ino")
        )
    ):
        raise BootstrapRefused("recovery finalization guard identity is unsafe")


@contextmanager
def _finalization_lock():
    """Serialize terminal publication against the controller postmortem."""

    path = _finalization_guard_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(path):
            initial = path.lstat()
            if (
                stat.S_ISLNK(initial.st_mode)
                or _is_reparse(initial)
                or not stat.S_ISREG(initial.st_mode)
                or int(getattr(initial, "st_nlink", 0)) != 1
            ):
                raise BootstrapRefused("recovery finalization guard is unsafe")
        handle = path.open("a+b")
    except BootstrapRefused:
        raise
    except OSError as exc:
        raise BootstrapRefused("cannot open the recovery finalization guard") from exc
    with handle:
        try:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            _validate_finalization_guard_file(path, handle)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:  # pragma: no cover - non-Windows CI only
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except BootstrapRefused:
            raise
        except OSError as exc:
            raise BootstrapRefused("cannot acquire the recovery finalization guard") from exc
        try:
            handle.seek(0)
            _validate_finalization_guard_file(path, handle)
            yield
        finally:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:  # pragma: no cover - non-Windows CI only
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError as exc:
                raise BootstrapRefused(
                    "cannot release the recovery finalization guard"
                ) from exc


def _load_record(name: str, *, record_type: str) -> tuple[dict[str, Any], str]:
    left, right = _record_paths(name)
    file_sha = _same_bytes(left, right, what=name)
    document = _validate_seal(_read_json(left), what=name)
    if _read_json(right) != document:
        raise BootstrapRefused(f"{name} changed after twin validation")
    for key, expected in {
        "recovery_schema_version": RECOVERY_SCHEMA_VERSION,
        "recovery_id": RECOVERY_ID,
        "decision_id": DECISION_ID,
        "record_type": record_type,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
    }.items():
        if document.get(key) != expected:
            raise BootstrapRefused(f"{name} identity or outcome-blind policy differs")
    return document, file_sha


def _fsync_directory(path: Path) -> bool:
    """Best-effort directory fsync, reporting whether it was actually done.

    Python exposes no portable Windows directory-fsync operation.  On Windows
    this therefore returns ``False`` after the record file itself has been
    fsynced; it must never be described as directory-durable.  POSIX platforms
    return ``True`` only when ``fsync`` on the opened directory succeeds.
    """
    if os.name == "nt":
        return False
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        os.fsync(descriptor)
        return True
    except OSError as exc:
        if exc.errno not in {errno.EACCES, errno.EBADF, errno.EINVAL, errno.ENOTSUP}:
            raise BootstrapRefused("cannot sync bootstrap record directory") from exc
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _exclusive_publish_file(path: Path, data: bytes) -> None:
    parent = _plain_directory(path.parent, what=f"{path.name} parent")
    if os.path.lexists(path):
        raise BootstrapRefused(f"{path.name} already exists; invocation is consumed")
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise BootstrapRefused(f"{path.name} was claimed concurrently; invocation is consumed") from exc
        except OSError as exc:
            raise BootstrapRefused(f"cannot exclusively publish {path.name}") from exc
        temporary.unlink()
        temporary = None
        _fsync_directory(parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as exc:
                raise BootstrapRefused("cannot clean private bootstrap record") from exc


def _exclusive_publish_twins(name: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    document = _seal(payload)
    data = _json_file_bytes(document)
    left, right = _record_paths(name)
    if os.path.lexists(left) or os.path.lexists(right):
        raise BootstrapRefused(f"{name} already exists; invocation cannot be reused")
    _exclusive_publish_file(left, data)
    _exclusive_publish_file(right, data)
    file_sha = _same_bytes(left, right, what=name)
    if _read_json(left) != document or _read_json(right) != document:
        raise BootstrapRefused(f"{name} differs after exclusive publication")
    return document, file_sha


def _git_executable_row(value: object) -> dict[str, Any]:
    row = _expect_keys(value, {"path", "sha256"}, what="Git executable")
    if type(row["path"]) is not str:
        raise BootstrapRefused("Git executable path is not a string")
    path = Path(row["path"])
    if not path.is_absolute():
        raise BootstrapRefused("Git executable path is not absolute")
    resolved = _plain_file(path, what="Git executable").resolve()
    if path != resolved:
        raise BootstrapRefused("Git executable path is not the resolved authority path")
    if _expect_sha(row["sha256"], what="Git executable hash") != _sha_file(resolved):
        raise BootstrapRefused("Git executable authority differs")
    return row


def _source_row(value: object, *, path: Path, what: str) -> dict[str, Any]:
    row = _expect_keys(value, {"path", "sha256"}, what=what)
    _plain_file(path, what=what)
    if (
        type(row["path"]) is not str
        or Path(row["path"]).resolve() != path.resolve()
        or _expect_sha(row["sha256"], what=f"{what} hash") != _sha_file(path)
    ):
        raise BootstrapRefused(f"{what} authority differs")
    return row


def _controller_module_rows_shape(value: object) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise BootstrapRefused("loaded controller modules are not a non-empty list")
    rows: list[dict[str, Any]] = []
    module_ids: list[str] = []
    for index, value_row in enumerate(value):
        row = _expect_keys(
            value_row,
            {"module_id", "source_path", "source_sha256", "git_blob"},
            what=f"loaded controller module[{index}]",
        )
        module_id = row["module_id"]
        source_path = row["source_path"]
        if type(module_id) is not str or _BU_MODULE_ID.fullmatch(module_id) is None:
            raise BootstrapRefused(
                f"loaded controller module[{index}] id is not canonical"
            )
        if type(source_path) is not str or not Path(source_path).is_absolute():
            raise BootstrapRefused(
                f"loaded controller module[{index}] source path is not absolute"
            )
        _expect_sha(
            row["source_sha256"],
            what=f"loaded controller module[{index}] source hash",
        )
        if type(row["git_blob"]) is not str or _HEX40.fullmatch(row["git_blob"]) is None:
            raise BootstrapRefused(
                f"loaded controller module[{index}] Git blob is not canonical"
            )
        module_ids.append(module_id)
        rows.append(row)
    if module_ids != sorted(module_ids) or len(set(module_ids)) != len(module_ids):
        raise BootstrapRefused("loaded controller module ids are not unique and sorted")
    if module_ids[0] != "bu" or "bu.experiments.week8_exp2a_recovery" not in module_ids:
        raise BootstrapRefused("required controller modules were not source-attested")
    return rows


def _expected_module_source(module_id: str, source_root: Path) -> set[Path]:
    parts = module_id.split(".")
    module_path = source_root.joinpath(*parts)
    return {
        module_path.with_suffix(".py").resolve(),
        (module_path / "__init__.py").resolve(),
    }


def _validate_controller_module_rows(
    value: object, raw: Mapping[str, Any], raw_module: types.ModuleType
) -> list[dict[str, Any]]:
    """Validate controller-module rows under the already revalidated raw tree."""

    rows = _controller_module_rows_shape(value)
    root = _plain_directory(
        CONTROLLER_WORKTREE, what="controller worktree"
    ).resolve()
    source_root = _plain_directory(
        root / "src", what="controller source root"
    ).resolve()
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    admitted_blob = getattr(raw_module, "admitted_git_blob", None)
    if not callable(admitted_source) or not callable(admitted_blob):
        raise BootstrapRefused("raw controller-source APIs are unavailable")
    for row in rows:
        module_id = row["module_id"]
        source = _plain_file(
            Path(row["source_path"]), what=f"loaded controller module {module_id}"
        ).resolve()
        if source not in _expected_module_source(module_id, source_root):
            raise BootstrapRefused(
                f"loaded controller module {module_id} path differs from its id"
            )
        try:
            source.relative_to(root)
        except ValueError as exc:
            raise BootstrapRefused(
                f"loaded controller module {module_id} escaped the controller tree"
            ) from exc
        if source.suffix.lower() != ".py":
            raise BootstrapRefused(
                f"loaded controller module {module_id} source is not Python"
            )
        relative = source.relative_to(root).as_posix()
        try:
            source_bytes = admitted_source(raw, "controller", relative)
            git_blob = admitted_blob(raw, "controller", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise BootstrapRefused(
                f"loaded controller module {module_id} lacks raw source authority"
            ) from exc
        if (
            row["source_path"] != str(source)
            or row["source_sha256"] != _sha_bytes(source_bytes)
            or row["git_blob"] != git_blob
        ):
            raise BootstrapRefused(
                f"loaded controller module {module_id} differs from its sealed row"
            )
    return rows


def _worktree_authority_from_raw(
    value: object, raw: object, *, what: str
) -> dict[str, Any]:
    row = _expect_keys(value, {"path", "git_commit", "detached"}, what=what)
    if type(raw) is not dict:
        raise BootstrapRefused(f"raw {what} authority is not an object")
    expected = {
        "path": raw.get("path"),
        "git_commit": raw.get("git_commit"),
        "detached": raw.get("detached"),
    }
    if row != expected:
        raise BootstrapRefused(f"{what} differs from pre-import raw authority")
    return row


def _raw_authority_config(
    controller_commit: str, native_startup: Mapping[str, Any]
) -> dict[str, Any]:
    if type(controller_commit) is not str or _HEX40.fullmatch(controller_commit) is None:
        raise BootstrapRefused("controller authority commit is malformed")
    if type(native_startup) is not dict:
        raise BootstrapRefused("native startup authority is unavailable")
    launcher = native_startup.get("native_launcher")
    values = (
        native_startup.get("stage0_binding_sha256"),
        native_startup.get("release_receipt_sha256"),
        launcher.get("sha256") if type(launcher) is dict else None,
        native_startup.get("startup_binding_sha256"),
    )
    if any(type(value) is not str or _HEX64.fullmatch(value) is None for value in values):
        raise BootstrapRefused("native startup hashes are malformed")
    (
        stage0_binding_sha256,
        receipt_sha256,
        launcher_sha256,
        startup_binding_sha256,
    ) = values
    return {
        "controller_root": str(CONTROLLER_WORKTREE),
        "controller_commit": controller_commit,
        "stage0_binding_sha256": stage0_binding_sha256,
        "release_receipt_sha256": receipt_sha256,
        "native_launcher_sha256": launcher_sha256,
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
        "pinned_git_runtime_inventory_digest": EXPECTED_PINNED_GIT_RUNTIME_INVENTORY_DIGEST,
        "pinned_git_runtime_file_count": EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT,
        "pinned_git_runtime_directory_count": EXPECTED_PINNED_GIT_RUNTIME_DIRECTORY_COUNT,
        "pinned_git_runtime_total_bytes": EXPECTED_PINNED_GIT_RUNTIME_TOTAL_BYTES,
        "pinned_site_packages_inventory_digest": EXPECTED_PINNED_SITE_PACKAGES_INVENTORY_DIGEST,
        "pinned_site_packages_file_count": EXPECTED_PINNED_SITE_PACKAGES_FILE_COUNT,
        "pinned_site_packages_directory_count": EXPECTED_PINNED_SITE_PACKAGES_DIRECTORY_COUNT,
        "pinned_site_packages_total_bytes": EXPECTED_PINNED_SITE_PACKAGES_TOTAL_BYTES,
        "outer_bootstrap_literal_sha256": EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256,
    }


def _gate_file_identity(
    value: object,
    *,
    path: Path,
    expected_sha256: str | None,
    what: str,
) -> dict[str, Any]:
    row = _expect_keys(value, {"path", "sha256", "size"}, what=what)
    try:
        before = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise BootstrapRefused(f"{what} is unavailable") from exc
    if (
        stat.S_ISLNK(before.st_mode)
        or _is_reparse(before)
        or not stat.S_ISREG(before.st_mode)
        or int(getattr(before, "st_nlink", 0)) != 1
        or row["path"] != str(resolved)
        or type(row["size"]) is not int
        or row["size"] != before.st_size
    ):
        raise BootstrapRefused(f"{what} identity differs")
    observed_sha = _sha_file(path)
    try:
        after = path.lstat()
    except OSError as exc:
        raise BootstrapRefused(f"{what} disappeared during validation") from exc
    if (
        observed_sha != row["sha256"]
        or (expected_sha256 is not None and observed_sha != expected_sha256)
        or any(
            getattr(before, name, None) != getattr(after, name, None)
            for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
        )
    ):
        raise BootstrapRefused(f"{what} changed or has another SHA256")
    return row


def _load_raw_authority_module() -> types.ModuleType:
    module = sys.modules.get(RAW_AUTHORITY_MODULE_NAME)
    if type(module) is not types.ModuleType:
        raise BootstrapRefused(
            "raw-authority helper was not preloaded from the verified child bundle"
        )
    specification = getattr(module, "__spec__", None)
    if (
        type(getattr(module, "__file__", None)) is not str
        or Path(module.__file__).resolve(strict=True)
        != RAW_AUTHORITY_HELPER.resolve(strict=True)
        or type(getattr(specification, "loader", None))
        is not importlib.machinery.SourceFileLoader
        or getattr(module, "__source_sha256__", None)
        != EXPECTED_RAW_AUTHORITY_HELPER_SHA256
    ):
        raise BootstrapRefused("loaded raw-authority helper identity differs")
    return module


def _validate_entrypoint_gate() -> dict[str, Any]:
    """Revalidate the stdlib-only authority before a one-use claim exists."""

    encoded = os.environ.get(ENTRYPOINT_GATE_ENVIRONMENT_NAME)
    if type(encoded) is not str or not encoded:
        raise BootstrapRefused("bootstrap must inherit the fixed D-161 entrypoint gate")
    try:
        gate = json.loads(
            encoded,
            object_pairs_hook=_no_duplicate_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                BootstrapRefused("entrypoint gate contains non-finite JSON")
            ),
        )
    except BootstrapRefused:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapRefused("entrypoint gate is not strict JSON") from exc
    gate = _expect_keys(
        gate,
        {
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
        },
        what="entrypoint gate",
    )
    if encoded != _canonical_ascii(gate).decode("ascii"):
        raise BootstrapRefused("entrypoint gate is not canonical JSON")
    unsealed = {key: item for key, item in gate.items() if key != "record_digest"}
    if (
        gate["entrypoint_gate_schema_version"] != 4
        or gate["record_type"] != "week8_d161_entrypoint_gate"
        or gate["decision_id"] != DECISION_ID
        or gate["command"] != "recover"
        or gate["record_digest"] != _sha_bytes(_canonical_ascii(unsealed))
        or gate["scientific_outcomes_consulted"] is not False
        or gate["scientific_values_emitted"] is not False
        or gate["production_mutation_performed"] is not False
    ):
        raise BootstrapRefused("entrypoint gate policy or digest differs")
    _gate_file_identity(
        gate["entrypoint"],
        path=ENTRYPOINT_SCRIPT,
        expected_sha256=None,
        what="D-161 entrypoint",
    )
    helper = _gate_file_identity(
        gate["raw_authority_helper"],
        path=RAW_AUTHORITY_HELPER,
        expected_sha256=EXPECTED_RAW_AUTHORITY_HELPER_SHA256,
        what="D-161 raw-authority helper",
    )
    expected_paths = [
        str((CONTROLLER_WORKTREE / "src").resolve(strict=True)),
        str(PINNED_SITE_PACKAGES.resolve(strict=True)),
    ]
    if gate["admitted_pythonpath"] != expected_paths:
        raise BootstrapRefused("entrypoint admitted Python paths differ")
    raw = gate["raw_authority"]
    if type(raw) is not dict or raw.get("raw_authority_helper") != helper:
        raise BootstrapRefused("entrypoint raw authority binding differs")
    module = _load_raw_authority_module()
    revalidate = getattr(module, "revalidate_admitted_authority", None)
    if not callable(revalidate):
        raise BootstrapRefused("raw-authority revalidation API is unavailable")
    try:
        observed = revalidate(
            raw,
            _raw_authority_config(
                raw["controller"].get("git_commit"), raw.get("native_startup")
            ),
            helper_path=RAW_AUTHORITY_HELPER,
            helper_sha256=EXPECTED_RAW_AUTHORITY_HELPER_SHA256,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise BootstrapRefused("raw authority revalidation refused") from exc
    if _canonical_ascii(observed) != _canonical_ascii(raw):
        raise BootstrapRefused("raw authority changed before bootstrap claim")
    return gate


def _preimport_authority_binding(gate: Mapping[str, Any]) -> dict[str, Any]:
    raw = gate["raw_authority"]
    native = raw["native_startup"]
    return {
        "raw_authority_schema_version": raw["raw_authority_schema_version"],
        "entrypoint_schema_version": gate["entrypoint_gate_schema_version"],
        "entrypoint_sha256": gate["entrypoint"]["sha256"],
        "raw_authority_helper_sha256": gate["raw_authority_helper"]["sha256"],
        "raw_authority_record_digest": raw["record_digest"],
        "controller_tree_digest": raw["controller"]["worktree_inventory_digest"],
        "execution_tree_digest": raw["execution"]["worktree_inventory_digest"],
        "git_runtime_inventory_digest": raw["git_runtime"]["inventory_digest"],
        "site_packages_inventory_digest": raw["runtime"]["pinned_site_packages"][
            "inventory_digest"
        ],
        "stage0_binding_sha256": native["stage0_binding_sha256"],
        "release_receipt_sha256": native["release_receipt_sha256"],
        "native_launcher_sha256": native["native_launcher"]["sha256"],
        "startup_binding_sha256": native["startup_binding_sha256"],
        "startup_environment_sha256": native["startup_environment_sha256"],
        "base_runtime_inventory_sha256": native["pinned_base_runtime"][
            "inventory_sha256"
        ],
        "venv_scripts_inventory_sha256": native["pinned_venv_scripts"][
            "inventory_sha256"
        ],
    }


def _validate_authority(value: object) -> dict[str, Any]:
    gate = _validate_entrypoint_gate()
    raw = gate["raw_authority"]
    authority = _expect_keys(
        value,
        {
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
        },
        what="controller authority",
    )
    git_row = _git_executable_row(authority["git_executable"])
    if git_row != {
        "path": raw["git"]["path"],
        "sha256": raw["git"]["sha256"],
    }:
        raise BootstrapRefused("Git executable differs from pre-import raw authority")
    if authority["git_runtime"] != raw["git_runtime"]:
        raise BootstrapRefused("Git runtime differs from pre-import raw authority")
    if _canonical_ascii(authority["preimport_authority_record"]) != _canonical_ascii(
        raw
    ):
        raise BootstrapRefused("full pre-import authority record differs")
    _worktree_authority_from_raw(
        authority["controller_worktree"], raw["controller"], what="controller worktree"
    )
    execution_row = _worktree_authority_from_raw(
        authority["execution_worktree"], raw["execution"], what="execution worktree"
    )
    if execution_row["git_commit"] != EXECUTION_COMMIT or execution_row["detached"] is not True:
        raise BootstrapRefused("execution worktree differs from D-161")
    raw_module = _load_raw_authority_module()
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    if not callable(admitted_source):
        raise BootstrapRefused("raw captured-source API is unavailable")
    for key, relative, path in (
        (
            "controller_module",
            "src/bu/experiments/week8_exp2a_recovery.py",
            CONTROLLER_MODULE,
        ),
        ("bootstrap_worker", "scripts/week8_exp2a_recovery_worker.py", BOOTSTRAP_SCRIPT),
        (
            "recovery_inspector",
            "scripts/week8_exp2a_recovery_inspector.py",
            INSPECTOR_SCRIPT,
        ),
        (
            "recovery_entrypoint",
            "scripts/week8_exp2a_recovery_entrypoint.py",
            ENTRYPOINT_SCRIPT,
        ),
        (
            "raw_authority_helper",
            "scripts/week8_recovery_raw_authority.py",
            RAW_AUTHORITY_HELPER,
        ),
    ):
        expected = {
            "path": str(path.resolve(strict=True)),
            "sha256": _sha_bytes(admitted_source(raw, "controller", relative)),
        }
        if authority[key] != expected:
            raise BootstrapRefused(f"{key} differs from captured controller bytes")
    _validate_controller_module_rows(
        authority["loaded_controller_modules"], raw, raw_module
    )
    if Path(__file__).resolve() != BOOTSTRAP_SCRIPT.resolve():
        raise BootstrapRefused("running bootstrap is not the fixed authorized source")
    if globals().get("__transport_source_sha256__") != authority[
        "bootstrap_worker"
    ]["sha256"]:
        raise BootstrapRefused("running bootstrap differs from verified transport bytes")
    if authority["preimport_authority"] != _preimport_authority_binding(gate):
        raise BootstrapRefused("controller authority does not bind the entrypoint proof")
    for authority_name, raw_name in (
        ("pinned_python", "pinned_python"),
        ("base_python", "pinned_base_python"),
    ):
        sealed = authority[authority_name]
        raw_file = raw["runtime"][raw_name]
        if sealed != {"path": raw_file["path"], "sha256": raw_file["sha256"]}:
            raise BootstrapRefused(
                f"{authority_name} differs from pre-import raw authority"
            )
    return authority


def _validate_execution_source_tree(
    authority: Mapping[str, Any], gate: Mapping[str, Any] | None = None
) -> None:
    """Re-attest the detached checkout through the raw plumbing boundary."""

    if gate is None:
        gate = _validate_entrypoint_gate()
    row = _worktree_authority_from_raw(
        authority["execution_worktree"],
        gate["raw_authority"]["execution"],
        what="execution worktree",
    )
    if row["git_commit"] != EXECUTION_COMMIT or row["detached"] is not True:
        raise BootstrapRefused("execution worktree differs from D-161")


def _validate_verified_import_machinery(
    finder: object, dependency_finder: object
) -> None:
    if tuple(sys.meta_path) != (
        finder,
        dependency_finder,
        *_default_meta_path(),
    ):
        raise BootstrapRefused("verified execution finders are not installed exactly")
    if getattr(finder, "binding_marker", None) != "week8_d161_verified_source_v2":
        raise BootstrapRefused("verified execution finder identity differs")
    if (
        getattr(dependency_finder, "binding_marker", None)
        != "week8_d161_verified_dependency_source_v1"
    ):
        raise BootstrapRefused("verified dependency finder identity differs")
    allowed_cache_types = (importlib.machinery.FileFinder, zipimport.zipimporter)
    for cached in sys.path_importer_cache.values():
        if cached is not None and type(cached) not in allowed_cache_types:
            raise BootstrapRefused("bootstrap importer cache contains a custom finder")


def _walk_code_objects(code: types.CodeType) -> list[types.CodeType]:
    result = [code]
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            result.extend(_walk_code_objects(value))
    return result


def _module_defined_code_objects(
    module_name: str, module: types.ModuleType
) -> list[types.CodeType]:
    result: list[types.CodeType] = []
    seen: set[int] = set()

    for value in vars(module).values():
        if isinstance(value, types.FunctionType) and value.__module__ == module_name:
            for code in _walk_code_objects(value.__code__):
                if id(code) not in seen:
                    seen.add(id(code))
                    result.append(code)
    return result


def _validate_loaded_bu_modules(
    authority: Mapping[str, Any], gate_before: Mapping[str, Any] | None = None
) -> None:
    if gate_before is None:
        gate_before = _validate_entrypoint_gate()
    raw = gate_before["raw_authority"]
    raw_module = _load_raw_authority_module()
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    admitted_blob = getattr(raw_module, "admitted_git_blob", None)
    if not callable(admitted_source) or not callable(admitted_blob):
        raise BootstrapRefused("raw execution-source APIs are unavailable")
    required = {
        "bu.experiments.week8_exp2a_production",
        "bu.experiments.week8_exp2a_repair_launch",
    }
    loaded = {
        name
        for name in sys.modules
        if name == "bu" or name.startswith("bu.")
    }
    if not required.issubset(loaded):
        raise BootstrapRefused("required old execution modules are not loaded")
    for name in sorted(loaded):
        module = sys.modules[name]
        if type(module) is not types.ModuleType:
            raise BootstrapRefused(f"loaded {name} is not an exact module")
        module_file = getattr(module, "__file__", None)
        if type(module_file) is not str:
            raise BootstrapRefused(f"loaded {name} has no old-source file identity")
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        loader = getattr(spec, "loader", None)
        source = Path(module_file).resolve()
        if (
            type(origin) is not str
            or Path(origin).resolve() != source
            or getattr(loader, "binding_marker", None)
            != "week8_d161_verified_source_v2"
            or getattr(module, "__loader__", None) is not loader
            or getattr(loader, "name", None) != name
            or Path(str(getattr(loader, "path", ""))).resolve() != source
            or getattr(loader, "tree_kind", None) != "execution"
            or getattr(loader, "authority_tree_digest", None)
            != raw["execution"]["worktree_inventory_digest"]
        ):
            raise BootstrapRefused(f"loaded {name} import origin differs from its source")
        if source.suffix != ".py" or not source.is_relative_to(
            EXECUTION_WORKTREE.resolve()
        ):
            raise BootstrapRefused(f"loaded {name} escaped exact old source")
        relative = source.relative_to(EXECUTION_WORKTREE.resolve()).as_posix()
        try:
            source_bytes = admitted_source(raw, "execution", relative)
            git_blob = admitted_blob(raw, "execution", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise BootstrapRefused(
                f"loaded {name} lacks captured execution authority"
            ) from exc
        if (
            getattr(loader, "source_sha256", None) != _sha_bytes(source_bytes)
            or getattr(loader, "git_blob", None) != git_blob
        ):
            raise BootstrapRefused(
                f"loaded {name} differs from captured execution source"
            )
        code_objects = _module_defined_code_objects(name, module)
        if any(Path(code.co_filename).resolve() != source for code in code_objects):
            raise BootstrapRefused(
                f"loaded {name} executed code filename escaped its tracked source"
            )
    gate_after = _validate_entrypoint_gate()
    if gate_after["record_digest"] != gate_before["record_digest"]:
        raise BootstrapRefused("raw authority changed across old-source validation")


def _runtime_flags() -> dict[str, bool]:
    return {
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "ignore_environment": bool(getattr(sys.flags, "ignore_environment", False)),
        "isolated": bool(getattr(sys.flags, "isolated", False)),
        "no_site": bool(sys.flags.no_site),
        "no_user_site": bool(sys.flags.no_user_site),
        "safe_path": bool(getattr(sys.flags, "safe_path", False)),
        "utf8_mode": bool(sys.flags.utf8_mode),
    }


def _default_meta_path() -> tuple[object, object, object]:
    return (
        importlib.machinery.BuiltinImporter,
        importlib.machinery.FrozenImporter,
        importlib.machinery.PathFinder,
    )


def _runtime_roots() -> tuple[Path, ...]:
    roots = {
        Path(sys.base_prefix).resolve(),
        Path(sys.base_exec_prefix).resolve(),
    }
    return tuple(sorted(roots, key=str))


def _is_beneath(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _validate_default_import_machinery() -> None:
    if tuple(sys.meta_path) != _default_meta_path():
        raise BootstrapRefused("bootstrap meta path is not the CPython -S default")
    allowed_cache_types = (importlib.machinery.FileFinder, zipimport.zipimporter)
    for finder in sys.path_importer_cache.values():
        if finder is not None and type(finder) not in allowed_cache_types:
            raise BootstrapRefused("bootstrap importer cache contains a custom finder")


def _validate_startup_import_isolation() -> None:
    if _runtime_flags() != {
        "dont_write_bytecode": True,
        "ignore_environment": True,
        "isolated": True,
        "no_site": True,
        "no_user_site": True,
        "safe_path": True,
        "utf8_mode": True,
    }:
        raise BootstrapRefused("bootstrap requires Python -I -S -B -X utf8")
    _validate_default_import_machinery()
    roots = _runtime_roots()
    observed: list[Path] = []
    for index, entry in enumerate(sys.path):
        if type(entry) is not str or not entry:
            raise BootstrapRefused(f"bootstrap sys.path[{index}] is not an absolute path")
        candidate = Path(entry)
        if not candidate.is_absolute():
            raise BootstrapRefused(f"bootstrap sys.path[{index}] is not absolute")
        resolved = candidate.resolve()
        if (
            not _is_beneath(resolved, roots)
            or any(part.lower() in {"site-packages", "dist-packages"} for part in resolved.parts)
        ):
            raise BootstrapRefused("bootstrap inherited a non-standard import path")
        observed.append(resolved)
    if len(set(observed)) != len(observed):
        raise BootstrapRefused("bootstrap inherited duplicate import paths")
    expected_site = PINNED_PYTHON.parent.parent / "Lib" / "site-packages"
    if PINNED_SITE_PACKAGES.resolve() != expected_site.resolve():
        raise BootstrapRefused("pinned dependency path differs from pinned Python")
    if PINNED_SITE_PACKAGES.resolve() in observed:
        raise BootstrapRefused("pinned dependencies were admitted before the claim")


def _admit_old_source_and_dependencies() -> tuple[Path, Path, list[str]]:
    """Add exactly old ``src`` and pinned venv dependencies after the claim."""

    _validate_startup_import_isolation()
    source = _plain_directory(
        EXECUTION_WORKTREE / "src", what="old execution source"
    ).resolve()
    site_packages = _plain_directory(
        PINNED_SITE_PACKAGES, what="pinned venv site-packages"
    ).resolve()
    inherited = list(sys.path)
    sys.path[:] = [str(source), *inherited, str(site_packages)]
    if sys.path[0] != str(source) or sys.path[-1] != str(site_packages):
        raise BootstrapRefused("old import roots were not installed exactly")
    if len(sys.path) != len(inherited) + 2 or len(set(sys.path)) != len(sys.path):
        raise BootstrapRefused("old import roots contain aliases or duplicates")
    _validate_default_import_machinery()
    return source, site_packages, inherited


def _validate_current_interpreter(authority: Mapping[str, Any]) -> None:
    row = authority["pinned_python"]
    current = Path(sys.executable)
    _plain_file(current, what="current interpreter")
    try:
        same = os.path.samefile(current, PINNED_PYTHON)
    except OSError as exc:
        raise BootstrapRefused("cannot compare current and pinned interpreter") from exc
    if not same or current.resolve() != Path(row["path"]).resolve() or _sha_file(current) != row["sha256"]:
        raise BootstrapRefused("current interpreter differs from pinned authority")
    base_row = authority["base_python"]
    base = _plain_file(Path(sys._base_executable), what="current base interpreter")
    if (
        base.resolve() != Path(base_row["path"]).resolve()
        or _sha_file(base) != base_row["sha256"]
    ):
        raise BootstrapRefused("current base interpreter differs from authority")
    _validate_startup_import_isolation()


def _exact_environment_items() -> tuple[tuple[str, str], ...]:
    """Read exact environment-key spelling, bypassing Windows normalization."""

    if os.name != "nt":
        return tuple(os.environ.items())
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_environment = kernel32.GetEnvironmentStringsW
        get_environment.argtypes = []
        get_environment.restype = ctypes.c_void_p
        free_environment = kernel32.FreeEnvironmentStringsW
        free_environment.argtypes = [ctypes.c_void_p]
        free_environment.restype = ctypes.c_int
        pointer = get_environment()
    except (AttributeError, OSError) as exc:
        raise BootstrapRefused("cannot open the native Windows environment") from exc
    if not pointer:
        raise BootstrapRefused("native Windows environment is unavailable")
    entries: list[tuple[str, str]] = []
    offset = 0
    width = ctypes.sizeof(ctypes.c_wchar)
    try:
        while True:
            entry = ctypes.wstring_at(pointer + offset * width)
            if entry == "":
                break
            offset += len(entry) + 1
            separator = entry.find("=", 1 if entry.startswith("=") else 0)
            if separator <= 0:
                raise BootstrapRefused("native Windows environment entry is malformed")
            entries.append((entry[:separator], entry[separator + 1 :]))
    finally:
        if not free_environment(pointer):
            raise BootstrapRefused("cannot release the native Windows environment")
    return tuple(entries)


def _validate_sanitized_environment(invocation: Mapping[str, Any]) -> None:
    gate = _validate_entrypoint_gate()
    raw_environment = _exact_environment_items()
    required = {
        "CUDA_VISIBLE_DEVICES": "-1",
        "HIP_VISIBLE_DEVICES": "-1",
        "OMP_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4",
        "OPENBLAS_NUM_THREADS": "4",
        "NUMEXPR_NUM_THREADS": "4",
        "TEMP": str(RUNTIME_TEMP.resolve()),
        "TMP": str(RUNTIME_TEMP.resolve()),
        "TMPDIR": str(RUNTIME_TEMP.resolve()),
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
        "GIT_CONFIG_VALUE_0": str(EXECUTION_WORKTREE.resolve()),
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "",
        "GIT_TERMINAL_PROMPT": "0",
        ENTRYPOINT_GATE_ENVIRONMENT_NAME: _canonical_ascii(gate).decode("ascii"),
        INVOCATION_ENV: invocation["record_digest"],
        CHILD_BUNDLE_ENVIRONMENT_NAME: invocation["child_transport"][
            "bundle_sha256"
        ],
    }
    approved_python = {name for name in required if name.startswith("PYTHON")}
    approved_git = {name for name in required if name.startswith("GIT_")}
    observed_controls: dict[str, tuple[str, str]] = {}
    for item in raw_environment:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
        ):
            raise BootstrapRefused("exact process environment contains an invalid entry")
        name, value = item
        canonical_name = name.upper()
        if canonical_name in required or canonical_name.startswith(
            ("PYTHON", "GIT_", "BU_D161_")
        ):
            if canonical_name in observed_controls:
                raise BootstrapRefused(
                    f"sanitized bootstrap environment duplicated {canonical_name}"
                )
            observed_controls[canonical_name] = (name, value)
        if canonical_name.startswith("PYTHON") and (
            name != canonical_name or canonical_name not in approved_python
        ):
            raise BootstrapRefused(
                f"sanitized bootstrap environment retained unapproved {canonical_name}"
            )
        if canonical_name.startswith("GIT_") and (
            name != canonical_name or canonical_name not in approved_git
        ):
            raise BootstrapRefused(
                "sanitized bootstrap environment retained unapproved or "
                f"mis-cased {canonical_name}"
            )
        if canonical_name.startswith("BU_D161_") and (
            name != canonical_name
            or canonical_name
            not in {
                INVOCATION_ENV,
                ENTRYPOINT_GATE_ENVIRONMENT_NAME,
                CHILD_BUNDLE_ENVIRONMENT_NAME,
            }
        ):
            raise BootstrapRefused(
                "sanitized bootstrap environment retained unapproved or "
                f"mis-cased {canonical_name}"
            )
    for name, expected in required.items():
        if observed_controls.get(name) != (name, expected):
            raise BootstrapRefused(f"sanitized bootstrap environment differs at {name}")
    _plain_directory(RUNTIME_TEMP, what="project-local runtime temp")
    try:
        if any(RUNTIME_TEMP.iterdir()):
            raise BootstrapRefused("project-local recovery runtime temp is not empty")
    except OSError as exc:
        raise BootstrapRefused("cannot inspect project-local recovery runtime temp") from exc
    try:
        RUNTIME_TEMP.resolve().relative_to(WORKSPACE_ROOT.resolve())
    except ValueError as exc:
        raise BootstrapRefused("runtime temp escaped the project workspace") from exc
    try:
        if not os.path.samefile(Path.cwd(), EXECUTION_WORKTREE):
            raise BootstrapRefused("bootstrap cwd differs from detached execution worktree")
    except OSError as exc:
        raise BootstrapRefused("cannot validate bootstrap cwd") from exc


def _runtime_temp_directory_identity() -> dict[str, Any]:
    root = _plain_directory(RUNTIME_TEMP, what="project-local runtime temp")
    try:
        info = root.lstat()
    except OSError as exc:
        raise BootstrapRefused("runtime temp identity is unavailable") from exc
    attributes = int(getattr(info, "st_file_attributes", 0))
    birth_ns = int(getattr(info, "st_birthtime_ns", info.st_ctime_ns))
    if (
        info.st_nlink != 1
        or type(info.st_dev) is not int
        or info.st_dev < 0
        or type(info.st_ino) is not int
        or info.st_ino <= 0
        or birth_ns <= 0
    ):
        raise BootstrapRefused("runtime temp is not one stable plain directory")
    return {
        "path": str(root.resolve(strict=True)),
        "st_dev": int(info.st_dev),
        "st_ino": int(info.st_ino),
        "birth_time_ns": birth_ns,
        "file_attributes": attributes,
        "link_count": int(info.st_nlink),
    }


def _validate_runtime_temp_identity(value: object) -> dict[str, Any]:
    row = _expect_keys(
        value,
        {
            "path",
            "st_dev",
            "st_ino",
            "birth_time_ns",
            "file_attributes",
            "link_count",
        },
        what="invocation runtime temp identity",
    )
    if _canonical(row) != _canonical(_runtime_temp_directory_identity()):
        raise BootstrapRefused("invocation runtime temp directory was replaced")
    return row


def _binding(value: object, *, what: str, inventory: bool = False) -> dict[str, Any]:
    keys = {"record_digest", "file_sha256"}
    if inventory:
        keys.add("inventory_digest")
    row = _expect_keys(value, keys, what=what)
    for key in keys:
        _expect_sha(row[key], what=f"{what} {key}")
    return row


def _validate_liveness_rows(value: object, *, what: str) -> None:
    if type(value) is not list or not value:
        raise BootstrapRefused(f"{what} must contain liveness evidence")
    for index, item in enumerate(value):
        row = _expect_keys(item, {"sha256", "report"}, what=f"{what}[{index}]")
        if type(row["report"]) is not dict:
            raise BootstrapRefused(f"{what}[{index}] report is not an object")
        if _expect_sha(row["sha256"], what=f"{what}[{index}] hash") != _sha_bytes(_canonical(row["report"])):
            raise BootstrapRefused(f"{what}[{index}] digest differs")
        if row["report"].get("stability", {}).get("verdict") != "pass":
            raise BootstrapRefused(f"{what}[{index}] is not a passing stability proof")


def _active_lease_path() -> Path:
    return WORKSPACE_ROOT / "week7-production-control" / "leases" / "week7-production.lease.json"


def _orphan_archive_path() -> Path:
    return WORKSPACE_ROOT / "week7-production-control" / "leases" / "history" / f"week7-production.{OLD_LEASE_TOKEN}.orphaned-after-liveness-proof.json"


def _ordinary_old_release_path() -> Path:
    return (
        WORKSPACE_ROOT
        / "week7-production-control"
        / "leases"
        / "history"
        / f"week7-production.{OLD_LEASE_TOKEN}.released.json"
    )


def _assert_old_normal_release_absent() -> None:
    if os.path.lexists(_ordinary_old_release_path()):
        raise BootstrapRefused(
            "the frozen old lease token has an ordinary release record"
        )


def _quarantine_paths() -> tuple[Path, Path]:
    return RECOVERY_ROOT / "quarantine" / HIDDEN_PARTIAL_NAME, RECOVERY_COPY_ROOT / "quarantine" / HIDDEN_PARTIAL_NAME


_ACTIVE_RELOCATION: tuple[Any, ...] | None = None
_AUTHORIZED_ORPHAN_TRANSITION: tuple[bytes, dict[str, str]] | None = None


def _admitted_orphan_transition() -> dict[str, str]:
    state = _AUTHORIZED_ORPHAN_TRANSITION
    if type(state) is not tuple or len(state) != 2:
        raise BootstrapRefused("orphan transition is not authorized for child launch")
    canonical, binding = state
    document, file_sha = _load_record(TRANSITION_COMPLETION_FILE, record_type="transition_completion")
    if (
        _canonical(document) != canonical
        or {"record_digest": document["record_digest"], "file_sha256": file_sha} != binding
        or document.get("status") != "ownership_transition_complete"
    ):
        raise BootstrapRefused("authorized orphan transition changed before child launch")
    return dict(binding)


@contextmanager
def _authorized_orphan_transition(invocation: Mapping[str, Any], chain: Mapping[str, Any]):
    """Retain only the transition already verified by this worker's full chain."""
    global _AUTHORIZED_ORPHAN_TRANSITION
    if _AUTHORIZED_ORPHAN_TRANSITION is not None:
        raise BootstrapRefused("orphan transition authorization is already active")
    binding = _expect_keys(invocation["transition_completion"], {"record_digest", "file_sha256"},
                           what="authorized orphan transition binding")
    for name in binding: _expect_sha(binding[name], what=f"orphan transition {name}")
    _AUTHORIZED_ORPHAN_TRANSITION = (_canonical(chain["transition_completion"]), dict(binding))
    try:
        _admitted_orphan_transition()
        yield
    finally:
        try:
            _admitted_orphan_transition()
        finally:
            _AUTHORIZED_ORPHAN_TRANSITION = None


def _admitted_relocation() -> tuple[Any, Any, dict[str, Any]]:
    state = _ACTIVE_RELOCATION
    if type(state) is not tuple or len(state) != 5:
        raise BootstrapRefused("worker relocation helpers are not admitted")
    raw_module, raw, helpers, access, binding = state
    if sys.modules.get(RAW_AUTHORITY_MODULE_NAME) is not raw_module:
        raise BootstrapRefused("worker relocation raw authority module changed")
    metadata = helpers.modules["metadata"]
    observed = {
        "relocation_schema_version": 1,
        "attestation_sha256": access.attestation_sha256,
        "policy_sha256": metadata.POLICY_SHA256,
        "pair_count": metadata.EXPECTED_PAIR_COUNT,
        "document_count": metadata.EXPECTED_DOCUMENT_COUNT,
        "helpers": helpers.validate(raw),
    }
    if _canonical(observed) != _canonical(binding):
        raise BootstrapRefused("worker relocation helper or evidence binding changed")
    return metadata, access, observed


@contextmanager
def _worker_relocation_admission(authority: Mapping[str, Any]):
    """Verify captured stdlib-only helpers before consuming the sole claim."""
    global _ACTIVE_RELOCATION
    if _ACTIVE_RELOCATION is not None:
        raise BootstrapRefused("worker relocation admission is already active")
    gate = _validate_entrypoint_gate()
    raw = gate["raw_authority"]
    if _canonical(raw) != _canonical(authority.get("preimport_authority_record")):
        raise BootstrapRefused("worker relocation raw authority differs from invocation")
    raw_module = _load_raw_authority_module()
    helpers = raw_module.load_verified_relocation_helpers(raw)
    helper_binding = helpers.validate(raw)
    metadata = helpers.modules["metadata"]
    access = metadata.load_registered_access(helpers.modules["provenance"])
    binding = {
        "relocation_schema_version": 1,
        "attestation_sha256": access.attestation_sha256,
        "policy_sha256": metadata.POLICY_SHA256,
        "pair_count": metadata.EXPECTED_PAIR_COUNT,
        "document_count": metadata.EXPECTED_DOCUMENT_COUNT,
        "helpers": helper_binding,
    }
    _ACTIVE_RELOCATION = (raw_module, raw, helpers, access, binding)
    try:
        _admitted_relocation()
        yield
    finally:
        try:
            _admitted_relocation()
        finally:
            _ACTIVE_RELOCATION = None


@contextmanager
def _worker_relocation_readers(Launch: Any):
    metadata, access, binding = _admitted_relocation()
    Storage = importlib.import_module("bu.experiments.prefit_storage")
    sources = metadata.SourceReaders(access, Launch.W, Launch.S)
    preflight = metadata.PreflightReaders(access, sources, Launch, Storage)
    checkpoints = metadata.CheckpointReaders(access, preflight)
    completed = metadata.CompletedJobReaders(access, checkpoints)
    events = metadata.EventReaders(access, checkpoints)
    reuse = metadata.ReuseReader(access, completed, events)
    try:
        with sources.installed(), preflight.installed(), checkpoints.installed(), completed.installed(), events.installed(), reuse.installed():
            yield
    finally:
        if _canonical(_admitted_relocation()[2]) != _canonical(binding):
            raise BootstrapRefused("worker relocation binding changed across lower launch")


def _validate_incident(document: Mapping[str, Any]) -> None:
    _expect_keys(
        document,
        _BASE_KEYS | {"status", "automatic_retry_allowed", "authority", "controller_process", "inventory", "inventory_digest", "liveness_stability_reports", "record_digest"},
        what="incident record",
    )
    if document["status"] != "outcome_blind_interruption_adjudicated" or document["automatic_retry_allowed"] is not False:
        raise BootstrapRefused("incident status or retry policy differs")
    _controller_process_shape(
        document["controller_process"],
        authority=document["authority"],
        what="incident controller process",
    )
    inventory = _validate_seal(document["inventory"], field="inventory_digest", what="incident inventory")
    if document["inventory_digest"] != inventory["inventory_digest"]:
        raise BootstrapRefused("incident inventory binding differs")
    _expect_keys(
        inventory,
        {"inventory_schema_version", "execution_commit", "relocation", "control", "lease", "checkpoint", "events", "jobs", "staging", "lower_report_count", "production_launch_receipt_present", "mechanical_source_validation_performed", "scientific_outcomes_consulted", "scientific_values_emitted", "inventory_digest"},
        what="incident inventory",
    )
    if (
        inventory["inventory_schema_version"] != 2
        or inventory["execution_commit"] != EXECUTION_COMMIT
        or inventory["lower_report_count"] != 0
        or inventory["production_launch_receipt_present"] is not False
        or inventory["mechanical_source_validation_performed"] is not True
        or inventory["scientific_outcomes_consulted"] is not False
        or inventory["scientific_values_emitted"] is not False
    ):
        raise BootstrapRefused("incident inventory fixed state differs")
    if _canonical(inventory["relocation"]) != _canonical(_admitted_relocation()[2]):
        raise BootstrapRefused("incident relocation admission differs from worker")
    lease = _expect_keys(inventory["lease"], {"path", "sha256", "pid", "token", "timestamp", "timestamp_utc"}, what="incident lease")
    if lease["path"] != str(_active_lease_path().resolve()) or lease["sha256"] != EXPECTED_OLD_LEASE_SHA256 or lease["pid"] != OLD_LEASE_PID or lease["token"] != OLD_LEASE_TOKEN:
        raise BootstrapRefused("incident lease differs from D-161")
    checkpoint = _expect_keys(inventory["checkpoint"], {"token", "sha256", "checkpoint_digest", "execution_context_digest"}, what="incident checkpoint")
    if checkpoint["token"] != OLD_LEASE_TOKEN or checkpoint["sha256"] != EXPECTED_OLD_CHECKPOINT_SHA256 or checkpoint["checkpoint_digest"] != EXPECTED_OLD_CHECKPOINT_DIGEST or _HEX64.fullmatch(str(checkpoint["execution_context_digest"])) is None:
        raise BootstrapRefused("incident checkpoint differs from D-161")
    events = _expect_keys(inventory["events"], {"count", "chain_digest", "tail_file_sha256", "kind_counts", "started_job_ids", "synced_job_ids", "failure_count"}, what="incident events")
    if (
        events["count"] != 299
        or events["chain_digest"] != EXPECTED_OLD_EVENT_STREAM
        or events["tail_file_sha256"] != EXPECTED_OLD_EVENT_TAIL_FILE
        or events["kind_counts"] != {"attempt_started": 150, "job_synced": 149}
        or type(events["started_job_ids"]) is not list
        or len(events["started_job_ids"]) != 150
        or type(events["synced_job_ids"]) is not list
        or len(events["synced_job_ids"]) != 149
        or events["failure_count"] != 0
    ):
        raise BootstrapRefused("incident event prefix differs from D-161")
    jobs = _expect_keys(inventory["jobs"], {"registered_count", "local_completed", "durable_completed", "untouched_job_ids", "orphan_job_id", "orphan_child_pid", "hidden_partial"}, what="incident jobs")
    if (
        jobs["registered_count"] != 261
        or type(jobs["local_completed"]) is not list
        or len(jobs["local_completed"]) != 150
        or type(jobs["durable_completed"]) is not list
        or len(jobs["durable_completed"]) != 149
        or type(jobs["untouched_job_ids"]) is not list
        or len(jobs["untouched_job_ids"]) != 111
        or jobs["orphan_job_id"] != ORPHAN_JOB_ID
        or jobs["orphan_child_pid"] != ORPHAN_CHILD_PID
    ):
        raise BootstrapRefused("incident job accounting differs from D-161")
    hidden = _expect_keys(jobs["hidden_partial"], {"name", "entry_count", "file_count", "inventory", "inventory_digest"}, what="incident hidden partial")
    if hidden["name"] != HIDDEN_PARTIAL_NAME or hidden["file_count"] != 11 or type(hidden["entry_count"]) is not int or hidden["entry_count"] < hidden["file_count"] or type(hidden["inventory"]) is not list or _sha_bytes(_canonical(hidden["inventory"])) != hidden["inventory_digest"]:
        raise BootstrapRefused("incident hidden partial differs from D-161")
    _validate_liveness_rows(document["liveness_stability_reports"], what="incident liveness")


def _validate_epoch_terminal(document: Mapping[str, Any], *, incident: Mapping[str, Any], incident_sha: str) -> None:
    _expect_keys(
        document,
        _BASE_KEYS | {"status", "incident", "execution_commit", "lease_token", "lease_pid", "orphan_job_id", "orphan_child_pid", "counts", "lower_terminal_report_present", "normal_lease_release_present", "automatic_retry_allowed", "record_digest"},
        what="epoch-001 terminal",
    )
    expected_incident = {"record_digest": incident["record_digest"], "file_sha256": incident_sha, "inventory_digest": incident["inventory_digest"]}
    if (
        document["status"] != "externally_interrupted"
        or document["incident"] != expected_incident
        or document["execution_commit"] != EXECUTION_COMMIT
        or document["lease_token"] != OLD_LEASE_TOKEN
        or document["lease_pid"] != OLD_LEASE_PID
        or document["orphan_job_id"] != ORPHAN_JOB_ID
        or document["orphan_child_pid"] != ORPHAN_CHILD_PID
        or document["counts"] != {"events": 299, "started": 150, "synced": 149, "unresolved_started": 1, "failed": 0}
        or document["lower_terminal_report_present"] is not False
        or document["normal_lease_release_present"] is not False
        or document["automatic_retry_allowed"] is not False
    ):
        raise BootstrapRefused("epoch-001 terminal does not bind the incident")
    _assert_old_normal_release_absent()


def _expected_transition_authorization(incident: Mapping[str, Any], *, incident_sha: str, terminal_sha: str) -> dict[str, Any]:
    authority = incident["authority"]
    return {
        "incident": {"record_digest": incident["record_digest"], "file_sha256": incident_sha, "inventory_digest": incident["inventory_digest"]},
        "epoch001_terminal_file_sha256": terminal_sha,
        "controller_commit": authority["controller_worktree"]["git_commit"],
        "controller_module": authority["controller_module"],
        "bootstrap_worker": authority["bootstrap_worker"],
        "recovery_inspector": authority["recovery_inspector"],
        "execution_worktree": authority["execution_worktree"],
        "pinned_python": authority["pinned_python"],
        "old_lease": incident["inventory"]["lease"],
        "orphan_archive_path": str(_orphan_archive_path().resolve()),
        "hidden_partial": incident["inventory"]["jobs"]["hidden_partial"],
        "automatic_retry_allowed": False,
    }


def _validate_transition_intent(document: Mapping[str, Any], *, expected_authorization: Mapping[str, Any]) -> None:
    _expect_keys(document, _BASE_KEYS | {"status", "authorization", "liveness_stability_reports", "record_digest"}, what="transition intent")
    if document["status"] != "ownership_transition_intended" or _canonical(document["authorization"]) != _canonical(expected_authorization):
        raise BootstrapRefused("transition intent authorization differs")
    _validate_liveness_rows(document["liveness_stability_reports"], what="transition intent liveness")


def _tree_inventory(root: Path, *, what: str) -> list[dict[str, Any]]:
    root = _plain_directory(root, what=what)
    rows: list[dict[str, Any]] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(directory_names):
            child = _plain_directory(current_path / name, what=f"{what} directory")
            rows.append({"kind": "directory", "path": child.relative_to(root).as_posix()})
        for name in sorted(file_names):
            child = _plain_file(current_path / name, what=f"{what} file")
            info = child.lstat()
            rows.append({"kind": "file", "path": child.relative_to(root).as_posix(), "size": info.st_size, "sha256": _sha_file(child)})
    return sorted(rows, key=lambda row: (row["path"], row["kind"]))


def _validate_quarantine(row: object, *, incident: Mapping[str, Any]) -> dict[str, Any]:
    quarantine = _expect_keys(row, {"original_path", "copy_path", "inventory", "inventory_digest", "independent_copy"}, what="transition quarantine")
    original, copy = _quarantine_paths()
    if Path(quarantine["original_path"]).resolve() != original.resolve() or Path(quarantine["copy_path"]).resolve() != copy.resolve() or quarantine["independent_copy"] is not True:
        raise BootstrapRefused("quarantine paths or copy policy differ")
    left_rows = _tree_inventory(original, what="quarantine original")
    right_rows = _tree_inventory(copy, what="quarantine copy")
    if left_rows != right_rows or left_rows != quarantine["inventory"]:
        raise BootstrapRefused("quarantine twin inventories differ")
    hidden = incident["inventory"]["jobs"]["hidden_partial"]
    if left_rows != hidden["inventory"]:
        raise BootstrapRefused("quarantine no longer equals the incident partial")
    digest = _sha_bytes(_canonical(left_rows))
    if digest != quarantine["inventory_digest"] or digest != hidden["inventory_digest"]:
        raise BootstrapRefused("quarantine inventory digest differs")
    for item in left_rows:
        if item["kind"] == "file":
            try:
                if os.path.samefile(original / item["path"], copy / item["path"]):
                    raise BootstrapRefused("quarantine files are not independent objects")
            except OSError as exc:
                raise BootstrapRefused("cannot compare quarantine file identity") from exc
    if os.path.lexists(SYNC_ROOT / "jobs" / HIDDEN_PARTIAL_NAME):
        raise BootstrapRefused("pre-transition hidden partial still exists")
    return quarantine


def _validate_orphan_archive(*, require_active_absent: bool = True) -> dict[str, Any]:
    _assert_old_normal_release_absent()
    archive = _plain_file(_orphan_archive_path(), what="orphan lease archive")
    if _sha_file(archive) != EXPECTED_OLD_LEASE_SHA256:
        raise BootstrapRefused("orphan lease archive hash differs")
    record = _expect_keys(_read_json(archive), {"schema_version", "lease_name", "pid", "token", "timestamp", "timestamp_utc"}, what="orphan lease archive")
    if type(record["schema_version"]) is not int or record["schema_version"] != EXECUTION_LEASE_SCHEMA_VERSION or record["lease_name"] != "week7-production" or record["pid"] != OLD_LEASE_PID or record["token"] != OLD_LEASE_TOKEN or type(record["timestamp_utc"]) is not str:
        raise BootstrapRefused("orphan lease archive identity differs")
    active = _active_lease_path()
    if os.path.lexists(active):
        if require_active_absent:
            raise BootstrapRefused("an active shared lease exists before continuation")
        active_record = _expect_keys(
            _read_json(_plain_file(active, what="continuation active lease")),
            {"schema_version", "lease_name", "pid", "token", "timestamp", "timestamp_utc"},
            what="continuation active lease",
        )
        if (
            type(active_record["schema_version"]) is not int
            or active_record["schema_version"] != EXECUTION_LEASE_SCHEMA_VERSION
            or active_record["lease_name"] != "week7-production"
            or type(active_record["pid"]) is not int
            or active_record["pid"] <= 0
            or type(active_record["token"]) is not str
            or _HEX32.fullmatch(active_record["token"]) is None
            or active_record["token"] == OLD_LEASE_TOKEN
        ):
            raise BootstrapRefused("active continuation lease identity is not distinct")
    return record


def _validate_transition_completion(
    document: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    intent_sha: str,
    expected_authorization: Mapping[str, Any],
    incident: Mapping[str, Any],
) -> None:
    _expect_keys(document, _BASE_KEYS | {"status", "authorization", "transition_intent", "orphan_lease_archive", "quarantine", "record_digest"}, what="transition completion")
    if document["status"] != "ownership_transition_complete" or _canonical(document["authorization"]) != _canonical(expected_authorization) or document["transition_intent"] != {"record_digest": intent["record_digest"], "file_sha256": intent_sha}:
        raise BootstrapRefused("transition completion does not bind its intent")
    archive_row = _expect_keys(document["orphan_lease_archive"], {"path", "sha256", "classification"}, what="orphan lease archive binding")
    archive = _orphan_archive_path()
    if Path(archive_row["path"]).resolve() != archive.resolve() or archive_row["sha256"] != EXPECTED_OLD_LEASE_SHA256 or archive_row["classification"] != "orphaned_after_liveness_proof":
        raise BootstrapRefused("orphan lease archive binding differs")
    _validate_orphan_archive()
    _validate_quarantine(document["quarantine"], incident=incident)


def _checkpoint_paths() -> tuple[Path, Path]:
    name = f"{OLD_LEASE_TOKEN}.json"
    return OUTPUT_ROOT / START_DIRECTORY / name, SYNC_ROOT / START_DIRECTORY / name


def _launch_receipt_paths() -> tuple[Path, Path]:
    return PREPARATION_ORIGINAL_ROOT / "receipts" / "launch.json", PREPARATION_COPY_ROOT / "receipts" / "launch.json"


def _directory_entries(path: Path, *, what: str) -> list[Path]:
    path = _plain_directory(path, what=what)
    try:
        return sorted(path.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise BootstrapRefused(f"cannot enumerate {what}") from exc


def _prelaunch_state() -> dict[str, Any]:
    _assert_old_normal_release_absent()
    local_checkpoint, copy_checkpoint = _checkpoint_paths()
    for root, what in ((local_checkpoint.parent, "local checkpoint directory"), (copy_checkpoint.parent, "checkpoint copy directory")):
        entries = _directory_entries(root, what=what)
        if [entry.name for entry in entries] != [local_checkpoint.name]:
            raise BootstrapRefused("continuation checkpoint already exists")
    checkpoint_sha = _same_bytes(local_checkpoint, copy_checkpoint, what="epoch-001 checkpoint")
    if checkpoint_sha != EXPECTED_OLD_CHECKPOINT_SHA256:
        raise BootstrapRefused("epoch-001 checkpoint hash differs")
    for path in (OUTPUT_ROOT / REPORT_DIRECTORY, SYNC_ROOT / REPORT_DIRECTORY):
        if os.path.lexists(path):
            raise BootstrapRefused("a continuation lower-report path already exists")
    if _any_record_path(RECOVERY_COMPLETION_FILE):
        raise BootstrapRefused("recovery completion already exists")
    if any(os.path.lexists(path) for path in _launch_receipt_paths()):
        raise BootstrapRefused("production launch receipt already exists")
    if os.path.lexists(_active_lease_path()):
        raise BootstrapRefused("an active shared lease exists before continuation")
    return {
        "old_checkpoint": {
            "token": OLD_LEASE_TOKEN,
            "path": str(local_checkpoint.resolve()),
            "copy_path": str(copy_checkpoint.resolve()),
            "sha256": checkpoint_sha,
            "checkpoint_digest": EXPECTED_OLD_CHECKPOINT_DIGEST,
        },
        "continuation_checkpoint_tokens": [],
        "lower_report_tokens": [],
        "recovery_completion_present": False,
        "production_launch_receipt_present": False,
        "active_shared_lease_present": False,
    }


def _claim_paths_row(value: object) -> dict[str, Any]:
    row = _expect_keys(value, {"original_path", "copy_path", "exclusive"}, what="claim paths")
    left, right = _record_paths(BOOTSTRAP_CLAIM_FILE)
    if Path(row["original_path"]).resolve() != left.resolve() or Path(row["copy_path"]).resolve() != right.resolve() or row["exclusive"] is not True:
        raise BootstrapRefused("invocation claim paths differ")
    return row


def _validate_authority_shape(value: object) -> dict[str, Any]:
    authority = _expect_keys(
        value,
        {
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
        },
        what="controller authority",
    )
    for name in ("controller_worktree", "execution_worktree"):
        row = _expect_keys(
            authority[name], {"path", "git_commit", "detached"}, what=name
        )
        if (
            type(row["path"]) is not str
            or type(row["git_commit"]) is not str
            or _HEX40.fullmatch(row["git_commit"]) is None
            or type(row["detached"]) is not bool
        ):
            raise BootstrapRefused(f"{name} authority shape differs")
    for name in (
        "controller_module",
        "bootstrap_worker",
        "recovery_inspector",
        "recovery_entrypoint",
        "raw_authority_helper",
        "pinned_python",
        "base_python",
        "git_executable",
    ):
        row = _expect_keys(authority[name], {"path", "sha256"}, what=name)
        if type(row["path"]) is not str:
            raise BootstrapRefused(f"{name} authority path is not a string")
        _expect_sha(row["sha256"], what=f"{name} authority hash")
    preimport = _expect_keys(
        authority["preimport_authority"],
        {
            "raw_authority_schema_version",
            "entrypoint_schema_version",
            "entrypoint_sha256",
            "raw_authority_helper_sha256",
            "raw_authority_record_digest",
            "controller_tree_digest",
            "execution_tree_digest",
            "git_runtime_inventory_digest",
            "site_packages_inventory_digest",
            "stage0_binding_sha256",
            "release_receipt_sha256",
            "native_launcher_sha256",
            "startup_binding_sha256",
            "startup_environment_sha256",
            "base_runtime_inventory_sha256",
            "venv_scripts_inventory_sha256",
        },
        what="preimport authority binding",
    )
    if (
        preimport["raw_authority_schema_version"] != 4
        or preimport["entrypoint_schema_version"] != 4
    ):
        raise BootstrapRefused("preimport authority schema differs")
    for name in (
        "entrypoint_sha256",
        "raw_authority_helper_sha256",
        "raw_authority_record_digest",
        "controller_tree_digest",
        "execution_tree_digest",
        "git_runtime_inventory_digest",
        "site_packages_inventory_digest",
        "stage0_binding_sha256",
        "release_receipt_sha256",
        "native_launcher_sha256",
        "startup_binding_sha256",
        "startup_environment_sha256",
        "base_runtime_inventory_sha256",
        "venv_scripts_inventory_sha256",
    ):
        _expect_sha(preimport[name], what=f"preimport authority {name}")
    _controller_module_rows_shape(authority["loaded_controller_modules"])
    if type(authority["preimport_authority_record"]) is not dict:
        raise BootstrapRefused("full preimport authority is not an object")
    if type(authority["git_runtime"]) is not dict:
        raise BootstrapRefused("Git runtime authority is not an object")
    return authority


def _child_transport_row(
    value: object, *, authority: Mapping[str, Any]
) -> dict[str, Any]:
    row = _expect_keys(
        value,
        {
            "child_transport_schema_version",
            "transport",
            "logical_path",
            "source_sha256",
            "raw_helper_sha256",
            "bootstrap_literal_sha256",
            "bundle_sha256",
        },
        what="bootstrap child transport",
    )
    if (
        row["child_transport_schema_version"] != CHILD_TRANSPORT_SCHEMA_VERSION
        or type(row["child_transport_schema_version"]) is not int
        or row["transport"] != "verified_source_stdin"
        or row["logical_path"] != str(BOOTSTRAP_SCRIPT.resolve())
        or row["source_sha256"] != authority["bootstrap_worker"]["sha256"]
        or row["raw_helper_sha256"] != EXPECTED_RAW_AUTHORITY_HELPER_SHA256
        or row["bootstrap_literal_sha256"]
        != EXPECTED_CHILD_BOOTSTRAP_LITERAL_SHA256
        or globals().get("__transport_source_sha256__") != row["source_sha256"]
        or globals().get("__transport_bundle_sha256__") != row["bundle_sha256"]
    ):
        raise BootstrapRefused("bootstrap child transport policy differs")
    for name in (
        "source_sha256",
        "raw_helper_sha256",
        "bootstrap_literal_sha256",
        "bundle_sha256",
    ):
        _expect_sha(row[name], what=f"bootstrap child transport {name}")
    return row


def _validate_invocation_shape(document: Mapping[str, Any]) -> None:
    _expect_keys(
        document,
        _BASE_KEYS | {"status", "incident", "epoch001_terminal", "transition_intent", "transition_completion", "authority", "controller_process", "runtime_temp", "child_transport", "prelaunch_state", "prelaunch_state_digest", "claim_paths", "automatic_retry_allowed", "record_digest"},
        what="bootstrap invocation",
    )
    if document["status"] != "authorized_once" or document["automatic_retry_allowed"] is not False:
        raise BootstrapRefused("bootstrap invocation policy differs")
    _binding(document["incident"], what="invocation incident", inventory=True)
    _binding(document["epoch001_terminal"], what="invocation epoch terminal")
    _binding(document["transition_intent"], what="invocation transition intent")
    _binding(document["transition_completion"], what="invocation transition completion")
    _expect_sha(document["prelaunch_state_digest"], what="prelaunch state digest")
    if type(document["prelaunch_state"]) is not dict or document["prelaunch_state_digest"] != _sha_bytes(_canonical(document["prelaunch_state"])):
        raise BootstrapRefused("invocation prelaunch state digest differs")
    _validate_authority_shape(document["authority"])
    _child_transport_row(document["child_transport"], authority=document["authority"])
    _controller_process_shape(
        document["controller_process"],
        authority=document["authority"],
        what="invocation controller process",
    )
    _validate_runtime_temp_identity(document["runtime_temp"])
    _claim_paths_row(document["claim_paths"])


def _controller_process_shape(
    value: object, *, authority: Mapping[str, Any], what: str
) -> dict[str, Any]:
    row = _expect_keys(
        value,
        {"pid", "kernel_executable_path", "kernel_executable_sha256", "creation_time_100ns", "base_interpreter"},
        what=what,
    )
    base = _expect_keys(
        authority["base_python"], {"path", "sha256"}, what=f"{what} interpreter"
    )
    if (
        type(row["pid"]) is not int
        or row["pid"] <= 0
        or type(row["kernel_executable_path"]) is not str
        or Path(row["kernel_executable_path"]).resolve()
        != Path(base["path"]).resolve()
        or _expect_sha(row["kernel_executable_sha256"], what=f"{what} hash")
        != base["sha256"]
        or type(row["creation_time_100ns"]) is not int
        or row["creation_time_100ns"] <= 0
        or row["base_interpreter"] != base
    ):
        raise BootstrapRefused(f"{what} differs from the pinned controller")
    return row


def _load_authorized_invocation() -> tuple[dict[str, Any], str]:
    digest = os.environ.get(INVOCATION_ENV)
    if type(digest) is not str or _HEX64.fullmatch(digest) is None:
        raise BootstrapRefused("the sole invocation digest environment value is absent")
    document, file_sha = _load_record(BOOTSTRAP_INVOCATION_FILE, record_type="bootstrap_invocation")
    _validate_invocation_shape(document)
    if document["record_digest"] != digest:
        raise BootstrapRefused("invocation environment digest differs from its record")
    _validate_authority(document["authority"])
    if _any_record_path(BOOTSTRAP_CLAIM_FILE):
        raise BootstrapRefused("bootstrap invocation was already claimed")
    if _any_record_path(BOOTSTRAP_TERMINAL_FILE):
        raise BootstrapRefused("bootstrap invocation already has a terminal record")
    if _any_record_path(BOOTSTRAP_POSTMORTEM_FILE):
        raise BootstrapRefused("bootstrap invocation already has a postmortem record")
    return document, file_sha


def _validate_full_chain(invocation: Mapping[str, Any], invocation_sha: str) -> dict[str, Any]:
    observed_authority = _validate_authority(invocation["authority"])
    _validate_current_interpreter(observed_authority)
    _validate_sanitized_environment(invocation)
    incident, incident_sha = _load_record(INCIDENT_FILE, record_type="incident")
    _validate_incident(incident)
    if _canonical(incident["authority"]) != _canonical(invocation["authority"]):
        raise BootstrapRefused("invocation authority differs from incident authority")
    terminal, terminal_sha = _load_record(EPOCH001_TERMINAL_FILE, record_type="epoch001_terminal")
    _validate_epoch_terminal(terminal, incident=incident, incident_sha=incident_sha)
    expected_authorization = _expected_transition_authorization(incident, incident_sha=incident_sha, terminal_sha=terminal_sha)
    intent, intent_sha = _load_record(TRANSITION_INTENT_FILE, record_type="transition_intent")
    _validate_transition_intent(intent, expected_authorization=expected_authorization)
    completion, completion_sha = _load_record(TRANSITION_COMPLETION_FILE, record_type="transition_completion")
    _validate_transition_completion(completion, intent=intent, intent_sha=intent_sha, expected_authorization=expected_authorization, incident=incident)
    expected_bindings = {
        "incident": {"record_digest": incident["record_digest"], "file_sha256": incident_sha, "inventory_digest": incident["inventory_digest"]},
        "epoch001_terminal": {"record_digest": terminal["record_digest"], "file_sha256": terminal_sha},
        "transition_intent": {"record_digest": intent["record_digest"], "file_sha256": intent_sha},
        "transition_completion": {"record_digest": completion["record_digest"], "file_sha256": completion_sha},
    }
    for key, expected in expected_bindings.items():
        if invocation[key] != expected:
            raise BootstrapRefused(f"invocation does not bind {key}")
    observed_prelaunch = _prelaunch_state()
    if _canonical(observed_prelaunch) != _canonical(invocation["prelaunch_state"]) or invocation["prelaunch_state_digest"] != _sha_bytes(_canonical(observed_prelaunch)):
        raise BootstrapRefused("actual prelaunch state differs from invocation")
    reloaded, reloaded_sha = _load_record(BOOTSTRAP_INVOCATION_FILE, record_type="bootstrap_invocation")
    if _canonical(reloaded) != _canonical(invocation) or reloaded_sha != invocation_sha:
        raise BootstrapRefused("invocation changed after claim")
    return {"incident": incident, "transition_completion": completion, "prelaunch_state": observed_prelaunch}


def _windows_process_identity(pid: int) -> dict[str, Any]:
    if os.name != "nt":
        raise BootstrapRefused("bootstrap parent attestation requires Windows")
    if type(pid) is not int or pid <= 0:
        raise BootstrapRefused("bootstrap parent pid is not positive")
    import ctypes
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [
            ("low", wintypes.DWORD),
            ("high", wintypes.DWORD),
        ]

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

    process = kernel32.OpenProcess(0x1000, False, pid)
    if not process:
        raise BootstrapRefused("cannot open bootstrap parent process")
    close_failed = False
    try:
        capacity = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(capacity.value)
        if not kernel32.QueryFullProcessImageNameW(
            process, 0, buffer, ctypes.byref(capacity)
        ):
            raise BootstrapRefused("cannot query bootstrap parent executable")
        creation = FileTime()
        exit_time = FileTime()
        kernel_time = FileTime()
        user_time = FileTime()
        if not kernel32.GetProcessTimes(
            process,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            raise BootstrapRefused("cannot query bootstrap parent creation time")
        creation_time = (int(creation.high) << 32) | int(creation.low)
        if creation_time <= 0:
            raise BootstrapRefused("bootstrap parent creation time is not positive")
        path = _plain_file(
            Path(buffer.value), what="bootstrap parent executable"
        ).resolve()
        result = {
            "pid": pid,
            "kernel_executable_path": str(path),
            "creation_time_100ns": creation_time,
        }
    finally:
        if not kernel32.CloseHandle(process):
            close_failed = True
    if close_failed:
        raise BootstrapRefused("cannot close bootstrap parent process handle")
    return result


def _windows_parent_pid(pid: int) -> int:
    """Return one process's kernel snapshot parent PID without third parties."""

    if os.name != "nt":
        raise BootstrapRefused("bootstrap parent relation requires Windows")
    if type(pid) is not int or pid <= 0:
        raise BootstrapRefused("bootstrap launcher PID is not positive")
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
        raise BootstrapRefused("cannot snapshot bootstrap launcher parentage")
    parent_pid: int | None = None
    close_failed = False
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise BootstrapRefused("cannot enumerate bootstrap launcher parentage")
        while True:
            if int(entry.th32ProcessID) == pid:
                parent_pid = int(entry.th32ParentProcessID)
                break
            entry.dwSize = ctypes.sizeof(entry)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        if not kernel32.CloseHandle(snapshot):
            close_failed = True
    if close_failed:
        raise BootstrapRefused("cannot close bootstrap parentage snapshot")
    if parent_pid is None or parent_pid <= 0:
        raise BootstrapRefused("bootstrap launcher parent was not found exactly")
    return parent_pid


def _windows_child_pids(parent_pid: int) -> list[int]:
    """Return one stable process-snapshot view of a launcher's direct children."""

    if os.name != "nt" or type(parent_pid) is not int or parent_pid <= 0:
        raise BootstrapRefused("fit-child launcher PID is not positive")
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
        raise BootstrapRefused("cannot snapshot fit-child parentage")
    children: list[int] = []
    close_failed = False
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise BootstrapRefused("cannot enumerate fit-child parentage")
        while True:
            if int(entry.th32ParentProcessID) == parent_pid:
                children.append(int(entry.th32ProcessID))
            entry.dwSize = ctypes.sizeof(entry)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        if not kernel32.CloseHandle(snapshot):
            close_failed = True
    if close_failed:
        raise BootstrapRefused("cannot close fit-child parentage snapshot")
    return sorted(children)


class _RetainedWindowsProcessHandle:
    """One PID-reuse-safe owned process handle retained through final death."""

    def __init__(self, identity: Mapping[str, Any], *, what: str) -> None:
        import ctypes
        from ctypes import wintypes

        self.what = what
        self.identity = dict(identity)
        self._closed = False
        self._exitcode: int | None = None
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x00100000 | 0x1000 | 0x0001, False, identity["pid"])
        if not handle:
            raise BootstrapRefused(f"cannot retain {what} process handle")
        self._handle = handle
        try:
            observed = _windows_process_identity(identity["pid"])
            if (
                observed != {
                    "pid": identity["pid"],
                    "kernel_executable_path": identity["kernel_executable_path"],
                    "creation_time_100ns": identity["creation_time_100ns"],
                }
                or _windows_parent_pid(identity["pid"]) != identity["parent_pid"]
            ):
                raise BootstrapRefused(f"{what} changed before handle retention")
        except BaseException:
            self.close()
            raise

    def _kernel32(self) -> Any:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        return kernel32

    def is_alive(self) -> bool:
        if self._exitcode is not None or self._closed:
            return False
        result = int(self._kernel32().WaitForSingleObject(self._handle, 0))
        if result == 0x00000102:
            return True
        if result != 0:
            raise BootstrapRefused(f"cannot query {self.what} process state")
        self._capture_exitcode()
        return False

    def _capture_exitcode(self) -> int:
        if self._exitcode is not None:
            return self._exitcode
        import ctypes
        from ctypes import wintypes

        code = wintypes.DWORD()
        if not self._kernel32().GetExitCodeProcess(self._handle, ctypes.byref(code)):
            raise BootstrapRefused(f"cannot query {self.what} exit code")
        self._exitcode = int(code.value)
        return self._exitcode

    @property
    def exitcode(self) -> int | None:
        return None if self.is_alive() else self._capture_exitcode()

    def wait(self, timeout: float | None) -> bool:
        if self._closed or self._exitcode is not None:
            return True
        milliseconds = 0xFFFFFFFF if timeout is None else max(0, min(0xFFFFFFFE, int(timeout * 1000)))
        result = int(self._kernel32().WaitForSingleObject(self._handle, milliseconds))
        if result == 0x00000102:
            return False
        if result != 0:
            raise BootstrapRefused(f"cannot wait for {self.what}")
        self._capture_exitcode()
        return True

    def terminate(self, exit_code: int = 1) -> None:
        if self.is_alive() and not self._kernel32().TerminateProcess(
            self._handle, exit_code
        ):
            raise BootstrapRefused(f"cannot terminate {self.what}")

    def kill(self) -> None:
        self.terminate(9)

    def close(self) -> None:
        if self._closed:
            return
        if not self._kernel32().CloseHandle(self._handle):
            raise BootstrapRefused(f"cannot close {self.what} process handle")
        self._closed = True


def _open_owned_windows_process(pid: int) -> _RetainedWindowsProcessHandle:
    """Open one retained process object from its current kernel identity."""

    identity = _windows_process_identity(pid)
    identity["parent_pid"] = _windows_parent_pid(pid)
    identity["kernel_executable_sha256"] = _sha_file(
        Path(identity["kernel_executable_path"])
    )
    return _RetainedWindowsProcessHandle(identity, what=f"owned PID {pid}")


def _parent_process_attestation(authority: Mapping[str, Any]) -> dict[str, Any]:
    parent_pid = os.getppid()
    identity = _windows_process_identity(parent_pid)
    controller_pid = _windows_parent_pid(parent_pid)
    pinned_row = _expect_keys(
        authority["pinned_python"], {"path", "sha256"}, what="pinned launcher"
    )
    pinned_path = _plain_file(PINNED_PYTHON, what="pinned launcher").resolve()
    observed_path = _plain_file(
        Path(identity["kernel_executable_path"]),
        what="bootstrap parent executable",
    ).resolve()
    try:
        same = os.path.samefile(observed_path, pinned_path)
    except OSError as exc:
        raise BootstrapRefused("cannot compare bootstrap parent and pinned launcher") from exc
    pinned_sha = _expect_sha(pinned_row["sha256"], what="pinned launcher hash")
    if (
        parent_pid != identity["pid"]
        or not same
        or observed_path != pinned_path
        or type(pinned_row["path"]) is not str
        or Path(pinned_row["path"]).resolve() != pinned_path
        or _sha_file(observed_path) != pinned_sha
    ):
        raise BootstrapRefused("bootstrap parent differs from the pinned launcher")
    creation_time = identity["creation_time_100ns"]
    if type(creation_time) is not int or creation_time <= 0:
        raise BootstrapRefused("bootstrap parent creation time is not canonical")
    return {
        "pid": parent_pid,
        "parent_pid": controller_pid,
        "kernel_executable_path": str(observed_path),
        "kernel_executable_sha256": pinned_sha,
        "creation_time_100ns": creation_time,
        "pinned_launcher": dict(pinned_row),
    }


def _worker_process_attestation(authority: Mapping[str, Any]) -> dict[str, Any]:
    identity = _windows_process_identity(os.getpid())
    base = authority["base_python"]
    row = {
        **identity,
        "kernel_executable_sha256": _sha_file(
            Path(identity["kernel_executable_path"])
        ),
        "base_interpreter": dict(base),
    }
    return _controller_process_shape(
        row, authority=authority, what="bootstrap worker process"
    )


def _claim_payload(invocation: Mapping[str, Any], invocation_sha: str) -> dict[str, Any]:
    authority = invocation["authority"]
    parent = _parent_process_attestation(authority)
    if parent["parent_pid"] != invocation["controller_process"]["pid"]:
        raise BootstrapRefused(
            "bootstrap launcher is not a child of the invocation controller"
        )
    worker_process = _worker_process_attestation(authority)
    return {
        **{key: invocation[key] for key in _BASE_KEYS},
        "record_type": "bootstrap_claim",
        "status": "claimed_before_lower_import_or_launch",
        "invocation": {"record_digest": invocation["record_digest"], "file_sha256": invocation_sha},
        "transition_completion": dict(invocation["transition_completion"]),
        "prelaunch_state_digest": invocation["prelaunch_state_digest"],
        "worker": {
            "pid": os.getpid(),
            "parent_pid": parent["pid"],
            "process": worker_process,
            "parent_process": parent,
            "bootstrap_worker": dict(authority["bootstrap_worker"]),
            "pinned_python": dict(authority["pinned_python"]),
        },
        "claim_paths": dict(invocation["claim_paths"]),
        "exclusive_create": True,
        "automatic_retry_allowed": False,
    }


def _validate_claim(document: Mapping[str, Any], *, invocation: Mapping[str, Any], invocation_sha: str) -> None:
    if _canonical(document) != _canonical(_seal(_claim_payload(invocation, invocation_sha))):
        raise BootstrapRefused("published claim differs from this worker invocation")


def _validate_output_capture(value: object) -> dict[str, Any]:
    capture = _expect_keys(value, {"stdout", "stderr"}, what="lower output capture")
    for stream_name in ("stdout", "stderr"):
        row = _expect_keys(
            capture[stream_name],
            {"sha256", "byte_count", "write_count"},
            what=f"lower {stream_name} capture",
        )
        _expect_sha(row["sha256"], what=f"lower {stream_name} hash")
        for count_name in ("byte_count", "write_count"):
            if type(row[count_name]) is not int or row[count_name] < 0:
                raise BootstrapRefused(
                    f"lower {stream_name} {count_name} is not a non-negative integer"
                )
        expected_chunks = (
            row["byte_count"] + _CAPTURE_CHUNK_BYTES - 1
        ) // _CAPTURE_CHUNK_BYTES
        if row["write_count"] != expected_chunks:
            raise BootstrapRefused(
                f"lower {stream_name} digest-chunk count differs from byte count"
            )
    return capture


def _classify_claim_publication(
    intended_claim: Mapping[str, Any],
) -> tuple[dict[str, Any], str, bool]:
    """Classify the exact on-disk claim state after any publication outcome.

    One exact surviving twin is sufficient to consume the invocation and bind
    a refusal terminal, but it is never reported as a complete twin pair.
    Two exact, independent files are complete even if the publisher's original
    read-back operation failed.  Any foreign or unreadable occupant is left
    untouched and is not terminalized by this worker.
    """
    expected = _json_file_bytes(intended_claim)
    expected_sha = _sha_bytes(expected)
    paths = _record_paths(BOOTSTRAP_CLAIM_FILE)
    present: list[Path] = []
    for path in paths:
        if not os.path.lexists(path):
            continue
        present.append(path)
        try:
            observed = _plain_file(path, what="existing bootstrap claim").read_bytes()
        except OSError as exc:
            raise BootstrapRefused("cannot classify existing bootstrap claim") from exc
        if observed != expected or _sha_file(path) != expected_sha:
            raise BootstrapRefused("another worker consumed the one-use invocation")
    if not present:
        raise BootstrapRefused("claim publication failed before creating a claim")
    if len(present) == 2:
        try:
            if os.path.samefile(present[0], present[1]):
                raise BootstrapRefused("bootstrap claim twins alias one filesystem object")
        except OSError as exc:
            raise BootstrapRefused("cannot classify bootstrap claim independence") from exc
    return dict(intended_claim), expected_sha, len(present) == 2


def _fit_child_bundle(authority: Mapping[str, Any]) -> tuple[bytes, str]:
    """Capture the nested fit bootstrap and raw helper from controller authority."""

    raw = authority.get("preimport_authority_record")
    if type(raw) is not dict:
        raise BootstrapRefused("nested fit child lacks pre-import authority")
    module = _load_raw_authority_module()
    admitted_source = getattr(module, "admitted_source_bytes", None)
    if not callable(admitted_source):
        raise BootstrapRefused("nested fit child lacks captured-source authority")
    try:
        script_source = admitted_source(
            raw, "controller", "scripts/week8_exp2a_recovery_fit_child.py"
        )
        helper_source = admitted_source(
            raw, "controller", "scripts/week8_recovery_raw_authority.py"
        )
    except (OSError, TypeError, ValueError) as exc:
        raise BootstrapRefused("nested fit-child sources are unavailable") from exc
    helper_sha = _sha_bytes(helper_source)
    if helper_sha != EXPECTED_RAW_AUTHORITY_HELPER_SHA256:
        raise BootstrapRefused("nested fit-child helper digest differs")
    payload = {
        "child_transport_schema_version": CHILD_TRANSPORT_SCHEMA_VERSION,
        "record_type": "week8_d161_verified_child_bundle",
        "logical_path": str(FIT_CHILD_SCRIPT.resolve(strict=True)),
        "script_sha256": _sha_bytes(script_source),
        "script_base64": base64.b64encode(script_source).decode("ascii"),
        "raw_helper_path": str(RAW_AUTHORITY_HELPER.resolve(strict=True)),
        "raw_helper_sha256": helper_sha,
        "raw_helper_base64": base64.b64encode(helper_source).decode("ascii"),
    }
    payload["record_digest"] = _sha_bytes(_canonical_ascii(payload))
    bundle = _canonical_ascii(payload)
    return bundle, _sha_bytes(bundle)


def _fit_process_row(
    value: object,
    *,
    expected_path: Path,
    expected_sha256: str,
    retained_identity: Mapping[str, Any],
    what: str,
) -> dict[str, Any]:
    row = _expect_keys(
        value,
        {
            "pid",
            "parent_pid",
            "creation_time_100ns",
            "kernel_executable_path",
            "kernel_executable_sha256",
        },
        what=what,
    )
    if (
        type(row["pid"]) is not int
        or row["pid"] <= 0
        or type(row["parent_pid"]) is not int
        or row["parent_pid"] <= 0
        or type(row["creation_time_100ns"]) is not int
        or row["creation_time_100ns"] <= 0
        or type(row["kernel_executable_path"]) is not str
        or Path(row["kernel_executable_path"]).resolve() != expected_path.resolve()
        or row["kernel_executable_sha256"] != expected_sha256
    ):
        raise BootstrapRefused(f"{what} identity differs")
    if (
        type(retained_identity) is not dict
        or set(retained_identity)
        != {
            "pid",
            "parent_pid",
            "creation_time_100ns",
            "kernel_executable_path",
            "kernel_executable_sha256",
        }
        or any(retained_identity[key] != row[key] for key in retained_identity)
    ):
        raise BootstrapRefused(f"{what} retained kernel identity differs")
    return row


def _read_fit_startup(
    path: Path,
    *,
    invocation_digest: str,
    launcher_pid: int,
    authority: Mapping[str, Any],
    launcher_identity: Mapping[str, Any],
    fit_identity: Mapping[str, Any],
) -> dict[str, Any]:
    target = _plain_file(path, what="nested fit startup protocol")
    info = target.lstat()
    if _is_reparse(info) or int(getattr(info, "st_nlink", 0)) != 1:
        raise BootstrapRefused("nested fit startup protocol is linked")
    raw = target.read_bytes()
    document = _expect_keys(
        _read_json(target),
        {
            "fit_child_startup_schema_version",
            "record_type",
            "invocation_digest",
            "launcher",
            "fit_interpreter",
            "record_digest",
        },
        what="nested fit startup protocol",
    )
    if raw != _canonical_ascii(document):
        raise BootstrapRefused("nested fit startup protocol is not canonical")
    unsealed = {key: value for key, value in document.items() if key != "record_digest"}
    if (
        document["fit_child_startup_schema_version"]
        != FIT_CHILD_STARTUP_SCHEMA_VERSION
        or document["record_type"] != "week8_d161_fit_child_startup"
        or document["invocation_digest"] != invocation_digest
        or document["record_digest"] != _sha_bytes(_canonical_ascii(unsealed))
    ):
        raise BootstrapRefused("nested fit startup protocol policy differs")
    pinned_launcher = _expect_keys(
        authority.get("pinned_python"),
        {"path", "sha256"},
        what="nested fit sealed launcher",
    )
    pinned_base = _expect_keys(
        authority.get("base_python"),
        {"path", "sha256"},
        what="nested fit sealed interpreter",
    )
    launcher = _fit_process_row(
        document["launcher"],
        expected_path=Path(pinned_launcher["path"]),
        expected_sha256=pinned_launcher["sha256"],
        retained_identity=launcher_identity,
        what="nested fit launcher",
    )
    fit = _fit_process_row(
        document["fit_interpreter"],
        expected_path=Path(pinned_base["path"]),
        expected_sha256=pinned_base["sha256"],
        retained_identity=fit_identity,
        what="nested fit interpreter",
    )
    if (
        launcher["pid"] != launcher_pid
        or launcher["parent_pid"] != os.getpid()
        or fit["pid"] == launcher_pid
        or fit["parent_pid"] != launcher_pid
        or _windows_child_pids(launcher_pid) != [fit["pid"]]
    ):
        raise BootstrapRefused("nested fit startup parentage differs")
    return document


def _publish_fit_startup_ack(
    path: Path,
    *,
    invocation_digest: str,
    startup: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = _plain_directory(RUNTIME_TEMP, what="nested fit runtime temp")
    if (
        path.parent != runtime
        or _FIT_STARTUP_ACK_NAME.fullmatch(path.name) is None
        or os.path.lexists(path)
    ):
        raise BootstrapRefused("nested fit startup acknowledgment path differs")
    payload = {
        "fit_child_startup_schema_version": FIT_CHILD_STARTUP_SCHEMA_VERSION,
        "record_type": "week8_d161_fit_child_startup_ack",
        "invocation_digest": invocation_digest,
        "startup_record_digest": startup["record_digest"],
        "launcher_creation": {
            "pid": startup["launcher"]["pid"],
            "creation_time_100ns": startup["launcher"]["creation_time_100ns"],
        },
        "fit_interpreter_creation": {
            "pid": startup["fit_interpreter"]["pid"],
            "creation_time_100ns": startup["fit_interpreter"]["creation_time_100ns"],
        },
    }
    document = {**payload, "record_digest": _sha_bytes(_canonical_ascii(payload))}
    encoded = _canonical_ascii(document)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_BINARY", 0))
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        remaining = memoryview(encoded)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("zero-byte startup acknowledgment write")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.rename(temporary, path)
    except OSError as exc:
        raise BootstrapRefused("cannot publish nested fit startup acknowledgment") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if os.path.lexists(temporary):
            temporary.unlink()
    return document


class _VerifiedFitReceive:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.closed = False

    def poll(self, timeout: float = 0.0) -> bool:
        if self.closed:
            raise BootstrapRefused("nested fit result receiver is closed")
        deadline = time.monotonic() + max(0.0, float(timeout))
        while True:
            if os.path.lexists(self.path):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.005, max(0.0, deadline - time.monotonic())))

    def recv(self) -> dict[str, Any]:
        if self.closed:
            raise BootstrapRefused("nested fit result receiver is closed")
        path = _plain_file(self.path, what="nested fit protocol result")
        info = path.lstat()
        if int(getattr(info, "st_nlink", 0)) != 1 or _is_reparse(info):
            raise BootstrapRefused("nested fit protocol result is linked")
        raw = path.read_bytes()
        message = _read_json(path)
        if raw != _canonical_ascii(message):
            raise BootstrapRefused("nested fit protocol result is not canonical")
        if message.get("kind") == "success":
            _expect_keys(message, {"kind", "result_json"}, what="nested fit success")
            if type(message["result_json"]) is not str:
                raise BootstrapRefused("nested fit success result is not JSON text")
        elif message.get("kind") == "python_exception":
            _expect_keys(
                message,
                {"kind", "error_type", "error", "traceback"},
                what="nested fit exception",
            )
            if any(type(message[name]) is not str for name in ("error_type", "error", "traceback")):
                raise BootstrapRefused("nested fit exception fields are malformed")
        else:
            raise BootstrapRefused("nested fit protocol kind differs")
        path.unlink()
        _fsync_directory(path.parent)
        return message

    def close(self) -> None:
        self.closed = True


class _VerifiedFitSend:
    def __init__(self, path: Path) -> None:
        self.path = path

    def close(self) -> None:
        return None


class _VerifiedFitProcess:
    def __init__(
        self,
        *,
        context: "_VerifiedFitContext",
        target: object,
        args: tuple[object, ...],
        name: str,
    ) -> None:
        if target is not context.supervisor._spawn_worker or len(args) != 4:
            raise BootstrapRefused("nested fit process target differs")
        callback, attempt_dir, payload, connection = args
        if (
            callback is not context.launch._fit_worker
            or type(attempt_dir) is not str
            or type(payload) is not dict
            or connection is not context.pending_send
            or type(name) is not str
            or not name.startswith("bu-job-")
        ):
            raise BootstrapRefused("nested fit process arguments differ")
        self.context = context
        self.attempt_dir = attempt_dir
        self.payload = payload
        self.name = name
        self._process: subprocess.Popen[bytes] | None = None
        self._fit_pid: int | None = None
        self._launcher_handle: _RetainedWindowsProcessHandle | None = None
        self._fit_handle: _RetainedWindowsProcessHandle | None = None

    @property
    def pid(self) -> int | None:
        return self._fit_pid

    @property
    def exitcode(self) -> int | None:
        if self._fit_handle is None or self._launcher_handle is None:
            return None
        if self._fit_handle.is_alive() or self._launcher_handle.is_alive():
            return None
        return self._fit_handle.exitcode

    def _retain_launcher_immediately(
        self, process: subprocess.Popen[bytes]
    ) -> None:
        """Own and validate the venv launcher before sending it any input."""

        if self._launcher_handle is not None:
            raise BootstrapRefused("nested fit launcher was already retained")
        handle = _open_owned_windows_process(process.pid)
        self._launcher_handle = handle
        expected = _expect_keys(
            self.context.authority.get("pinned_python"),
            {"path", "sha256"},
            what="nested fit sealed launcher",
        )
        identity = handle.identity
        if (
            set(identity)
            != {
                "pid",
                "parent_pid",
                "creation_time_100ns",
                "kernel_executable_path",
                "kernel_executable_sha256",
            }
            or identity["pid"] != process.pid
            or identity["parent_pid"] != os.getpid()
            or Path(identity["kernel_executable_path"]).resolve()
            != Path(expected["path"]).resolve()
            or identity["kernel_executable_sha256"] != expected["sha256"]
        ):
            raise BootstrapRefused("nested fit retained launcher identity differs")

    def _retain_fit_from_parent_snapshot(self, *, required: bool) -> bool:
        """Retain the launcher's one direct base-Python child independently."""

        if self._fit_handle is not None:
            return True
        launcher = self._launcher_handle
        if launcher is None:
            raise BootstrapRefused("nested fit launcher is not retained")
        launcher_pid = launcher.identity["pid"]
        children = _windows_child_pids(launcher_pid)
        if not children:
            if required:
                raise BootstrapRefused("nested fit launcher has no base interpreter child")
            return False
        if len(children) != 1:
            raise BootstrapRefused("nested fit launcher child inventory differs")
        child_pid = children[0]
        handle = _open_owned_windows_process(child_pid)
        self._fit_handle = handle
        self._fit_pid = child_pid
        expected = _expect_keys(
            self.context.authority.get("base_python"),
            {"path", "sha256"},
            what="nested fit sealed interpreter",
        )
        identity = handle.identity
        if (
            set(identity)
            != {
                "pid",
                "parent_pid",
                "creation_time_100ns",
                "kernel_executable_path",
                "kernel_executable_sha256",
            }
            or identity["pid"] != child_pid
            or identity["parent_pid"] != launcher_pid
            or Path(identity["kernel_executable_path"]).resolve()
            != Path(expected["path"]).resolve()
            or identity["kernel_executable_sha256"] != expected["sha256"]
            or _windows_child_pids(launcher_pid) != [child_pid]
        ):
            raise BootstrapRefused("nested fit retained interpreter identity differs")
        return True

    @staticmethod
    def _stop_retained_handle(
        handle: _RetainedWindowsProcessHandle, *, what: str, close: bool = True
    ) -> None:
        """Terminate, prove death through the retained handle, then close it."""

        try:
            if handle.is_alive():
                handle.terminate()
            if not handle.wait(2.0):
                handle.kill()
                if not handle.wait(2.0):
                    raise BootstrapRefused(f"{what} survived forced termination")
            if handle.is_alive():
                raise BootstrapRefused(f"{what} remained alive after termination")
        finally:
            if close:
                handle.close()

    def _cleanup_failed_start(self) -> None:
        """Own and stop every direct child before stopping the retained launcher."""

        launcher = self._launcher_handle
        process = self._process
        errors: list[BaseException] = []
        extra_children: list[_RetainedWindowsProcessHandle] = []
        if launcher is not None and self._fit_handle is None:
            deadline = time.monotonic() + 2.0
            while True:
                try:
                    if self._retain_fit_from_parent_snapshot(required=False):
                        break
                except BaseException as exc:
                    errors.append(exc)
                    break
                try:
                    launcher_alive = launcher.is_alive()
                except BaseException as exc:
                    errors.append(exc)
                    break
                if not launcher_alive or time.monotonic() >= deadline:
                    break
                time.sleep(0.005)

        # Take one independent parent/child snapshot while the retained launcher
        # still exists.  Any unexpected direct child is still ours and is
        # retained for cleanup before the launcher can be terminated.
        if launcher is not None:
            try:
                known = self._fit_handle.identity["pid"] if self._fit_handle else None
                for pid in _windows_child_pids(launcher.identity["pid"]):
                    if pid == known:
                        continue
                    extra_children.append(_open_owned_windows_process(pid))
                if extra_children:
                    errors.append(
                        BootstrapRefused("nested fit launcher had unexpected direct children")
                    )
            except BaseException as exc:
                errors.append(exc)

        child_handles = [
            *([self._fit_handle] if self._fit_handle is not None else []),
            *extra_children,
        ]
        for handle in child_handles:
            try:
                self._stop_retained_handle(
                    handle, what=f"nested fit interpreter PID {handle.identity['pid']}"
                )
            except BaseException as exc:
                errors.append(exc)
        self._fit_handle = None
        self._fit_pid = None

        if launcher is not None:
            try:
                self._stop_retained_handle(
                    launcher, what="nested fit launcher", close=False
                )
                # With launcher death proven and its process object still
                # retained, no new child can be created and its PID cannot be
                # confused with a later lifecycle.  Reap any child that crossed
                # the pre-termination snapshot boundary.
                late_children = _windows_child_pids(launcher.identity["pid"])
                for pid in late_children:
                    late = _open_owned_windows_process(pid)
                    try:
                        self._stop_retained_handle(
                            late, what=f"late nested fit child PID {pid}"
                        )
                    except BaseException as exc:
                        errors.append(exc)
            except BaseException as exc:
                errors.append(exc)
            finally:
                try:
                    launcher.close()
                except BaseException as exc:
                    errors.append(exc)
                self._launcher_handle = None
        elif process is not None:
            try:
                for pid in _windows_child_pids(process.pid):
                    child = _open_owned_windows_process(pid)
                    self._stop_retained_handle(
                        child, what=f"unretained launcher child PID {pid}"
                    )
            except BaseException as exc:
                errors.append(exc)
        if launcher is None and process is not None and process.poll() is None:
            try:
                process.kill()
            except BaseException as exc:
                errors.append(exc)
        if process is not None:
            try:
                process.wait(timeout=2.0)
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise BootstrapRefused("nested fit failed-start cleanup was not exact") from errors[0]

    def _bind_startup(
        self,
        process: subprocess.Popen[bytes],
        *,
        invocation_digest: str,
    ) -> None:
        startup_path = self.context.startup_path
        ack_path = self.context.startup_ack_path
        if startup_path is None or ack_path is None:
            raise BootstrapRefused("nested fit startup paths are unavailable")
        deadline = time.monotonic() + FIT_CHILD_STARTUP_TIMEOUT_SECONDS
        while not os.path.lexists(startup_path):
            if process.poll() is not None:
                raise BootstrapRefused("nested fit launcher exited before startup proof")
            self._retain_fit_from_parent_snapshot(required=False)
            if time.monotonic() >= deadline:
                raise BootstrapRefused("nested fit startup proof timed out")
            time.sleep(0.005)
        self._retain_fit_from_parent_snapshot(required=True)
        if self._launcher_handle is None or self._fit_handle is None:
            raise BootstrapRefused("nested fit retained process ownership is incomplete")
        startup = _read_fit_startup(
            startup_path,
            invocation_digest=invocation_digest,
            launcher_pid=process.pid,
            authority=self.context.authority,
            launcher_identity=dict(self._launcher_handle.identity),
            fit_identity=dict(self._fit_handle.identity),
        )
        for handle, expected in (
            (self._launcher_handle, startup["launcher"]),
            (self._fit_handle, startup["fit_interpreter"]),
        ):
            if any(
                handle.identity.get(key) != expected[key]
                for key in (
                    "pid",
                    "parent_pid",
                    "creation_time_100ns",
                    "kernel_executable_path",
                    "kernel_executable_sha256",
                )
            ):
                raise BootstrapRefused("nested fit retained handle identity differs")
        _publish_fit_startup_ack(
            ack_path,
            invocation_digest=invocation_digest,
            startup=startup,
        )

    def start(self) -> None:
        if self._process is not None:
            raise BootstrapRefused("nested fit process was already started")
        result_path = self.context.pending_send.path
        invocation = {
            "fit_child_invocation_schema_version": FIT_CHILD_INVOCATION_SCHEMA_VERSION,
            "record_type": "week8_d161_verified_fit_child_invocation",
            "attempt_dir": self.attempt_dir,
            "payload": self.payload,
            "result_path": str(result_path),
            "startup_path": str(self.context.startup_path),
            "startup_ack_path": str(self.context.startup_ack_path),
            "entrypoint_gate_digest": self.context.gate["record_digest"],
            "child_bundle_sha256": self.context.bundle_sha256,
            "relocation": _admitted_relocation()[2],
            "orphan_transition": _admitted_orphan_transition(),
        }
        invocation["invocation_digest"] = _sha_bytes(_canonical_ascii(invocation))
        invocation_bytes = _canonical_ascii(invocation)
        environment = dict(os.environ)
        environment[CHILD_BUNDLE_ENVIRONMENT_NAME] = self.context.bundle_sha256
        environment[FIT_CHILD_INVOCATION_ENVIRONMENT_NAME] = base64.b64encode(
            invocation_bytes
        ).decode("ascii")
        environment[FIT_CHILD_INVOCATION_DIGEST_ENVIRONMENT_NAME] = _sha_bytes(
            invocation_bytes
        )
        process = subprocess.Popen(
            [
                str(PINNED_PYTHON),
                "-I",
                "-S",
                "-B",
                "-X",
                "utf8",
                "-c",
                FIT_CHILD_BOOTSTRAP_LITERAL,
            ],
            cwd=EXECUTION_WORKTREE,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._process = process
        try:
            self._retain_launcher_immediately(process)
            if process.stdin is None:
                raise BootstrapRefused("nested fit child lacks bundle stdin")
            process.stdin.write(self.context.bundle)
            process.stdin.close()
            self._bind_startup(
                process,
                invocation_digest=invocation["invocation_digest"],
            )
        except BaseException as exc:
            try:
                self._cleanup_failed_start()
            except BaseException as cleanup_exc:
                raise BootstrapRefused(
                    "nested fit startup refused and cleanup could not be proven"
                ) from cleanup_exc
            raise exc

    def is_alive(self) -> bool:
        if self._fit_handle is None or self._launcher_handle is None:
            return self._process is not None and self._process.poll() is None
        return self._fit_handle.is_alive() or self._launcher_handle.is_alive()

    def join(self, timeout: float | None = None) -> None:
        if self._process is None:
            raise BootstrapRefused("nested fit process was not started")
        if self._fit_handle is None or self._launcher_handle is None:
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                return
            return
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
        self._fit_handle.wait(remaining)
        remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
        self._launcher_handle.wait(remaining)
        if not self._fit_handle.is_alive() and not self._launcher_handle.is_alive():
            fit_exit = self._fit_handle.exitcode
            launcher_exit = self._launcher_handle.exitcode
            if fit_exit is None or launcher_exit is None:
                raise BootstrapRefused("nested fit exit codes are unavailable")
            try:
                self._process.wait(timeout=0)
            except subprocess.TimeoutExpired:
                raise BootstrapRefused("launcher handle died before Popen observed death")
            self._fit_handle.close()
            self._launcher_handle.close()

    def terminate(self) -> None:
        if self._fit_handle is not None:
            self._fit_handle.terminate()
        if self._launcher_handle is not None:
            self._launcher_handle.terminate()
        elif self._process is not None:
            self._process.terminate()

    def kill(self) -> None:
        if self._fit_handle is not None:
            self._fit_handle.kill()
        if self._launcher_handle is not None:
            self._launcher_handle.kill()
        elif self._process is not None:
            self._process.kill()


class _VerifiedFitContext:
    def __init__(
        self,
        *,
        authority: Mapping[str, Any],
        gate: Mapping[str, Any],
        launch: Any,
        supervisor: Any,
    ) -> None:
        self.authority = authority
        self.gate = gate
        self.launch = launch
        self.supervisor = supervisor
        self.bundle, self.bundle_sha256 = _fit_child_bundle(authority)
        self.pending_receive: _VerifiedFitReceive | None = None
        self.pending_send: _VerifiedFitSend | None = None
        self.startup_path: Path | None = None
        self.startup_ack_path: Path | None = None
        self._consumed = False
        self._process_created = False

    def Pipe(self, duplex: bool = False) -> tuple[_VerifiedFitReceive, _VerifiedFitSend]:
        if duplex is not False:
            raise BootstrapRefused("nested fit protocol must be one-way")
        if self._consumed:
            raise BootstrapRefused("nested fit context is one-use only")
        self._consumed = True
        token = hashlib.sha256(os.urandom(32)).hexdigest()
        path = RUNTIME_TEMP / f"fit-child-result-{token}.json"
        self.startup_path = RUNTIME_TEMP / f"fit-child-startup-{token}.json"
        self.startup_ack_path = RUNTIME_TEMP / f"fit-child-startup-ack-{token}.json"
        if any(
            os.path.lexists(candidate)
            for candidate in (path, self.startup_path, self.startup_ack_path)
        ):
            raise BootstrapRefused("nested fit protocol path already exists")
        self.pending_receive = _VerifiedFitReceive(path)
        self.pending_send = _VerifiedFitSend(path)
        return self.pending_receive, self.pending_send

    def Process(
        self, *, target: object, args: tuple[object, ...], name: str
    ) -> _VerifiedFitProcess:
        if self.pending_send is None:
            raise BootstrapRefused("nested fit protocol was not initialized")
        if self._process_created:
            raise BootstrapRefused("nested fit process is one-use only")
        self._process_created = True
        return _VerifiedFitProcess(
            context=self, target=target, args=args, name=name
        )


def _install_old_source_tree(
    authority: Mapping[str, Any]
) -> tuple[Any, Any, dict[str, Any]]:
    for name in tuple(sys.modules):
        if name == "bu" or name.startswith("bu."):
            raise BootstrapRefused("bu was imported before the exclusive claim")
    old_root, site_packages, inherited = _admit_old_source_and_dependencies()
    admitted = [str(old_root), *inherited, str(site_packages)]
    gate = _validate_entrypoint_gate()
    _validate_execution_source_tree(authority, gate)
    raw_module = _load_raw_authority_module()
    finder_api = getattr(raw_module, "verified_source_finder", None)
    dependency_finder_api = getattr(
        raw_module, "verified_dependency_finder", None
    )
    if not callable(finder_api) or not callable(dependency_finder_api):
        raise BootstrapRefused("verified execution-import API is unavailable")
    try:
        finder = finder_api(gate["raw_authority"], "execution")
        dependency_finder = dependency_finder_api(gate["raw_authority"])
    except (OSError, TypeError, ValueError) as exc:
        raise BootstrapRefused("verified execution importer is unavailable") from exc
    sys.meta_path[:0] = [finder, dependency_finder]
    try:
        importlib.import_module("bu.runrecord")
    except (ImportError, OSError, TypeError, ValueError) as exc:
        raise BootstrapRefused("historical runrecord import refused") from exc
    with _verified_historical_git_state(authority, allow_imports=True):
        P = importlib.import_module("bu.experiments.week8_exp2a_production")
        Launch = importlib.import_module("bu.experiments.week8_exp2a_repair_launch")
        if sys.path != admitted:
            raise BootstrapRefused("old-source import changed the admitted import paths")
        _validate_verified_import_machinery(finder, dependency_finder)
        _validate_execution_source_tree(authority)
        _validate_loaded_bu_modules(authority)
    if P.WORKSPACE_ROOT.resolve() != WORKSPACE_ROOT.resolve():
        raise BootstrapRefused("old production package resolved another workspace")
    return P, Launch, gate


def _historical_orphan_record(Launch: Any, token: str) -> dict[str, Any]:
    if token != OLD_LEASE_TOKEN:
        raise BootstrapRefused("orphan-history adapter received another token")
    record = _validate_orphan_archive(require_active_absent=False)
    return {"path": str(_active_lease_path()), "sha256": EXPECTED_OLD_LEASE_SHA256, "name": "week7-production", "token": OLD_LEASE_TOKEN, "started_at": record["timestamp_utc"]}


def _historical_execution_git_row(authority: Mapping[str, Any]) -> dict[str, Any]:
    """Return the clean detached execution identity already sealed by authority."""

    raw = authority.get("preimport_authority_record")
    if type(raw) is not dict:
        raise BootstrapRefused("historical Git adapter lacks raw authority")
    execution = raw.get("execution")
    if type(execution) is not dict:
        raise BootstrapRefused("historical Git adapter lacks execution authority")
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
        raise BootstrapRefused("historical Git execution authority differs")
    return execution


def _historical_git_bindings(
    original: types.FunctionType, *, allow_incomplete: bool
) -> list[types.ModuleType]:
    """Find every imported historical alias of the exact runrecord callable."""

    bindings: list[types.ModuleType] = []
    for name, module in sorted(tuple(sys.modules.items())):
        if name != "bu" and not name.startswith("bu."):
            continue
        if type(module) is not types.ModuleType:
            raise BootstrapRefused(f"historical Git module {name} is not exact")
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
        raise BootstrapRefused("historical Git binding inventory is incomplete")
    return bindings


@contextmanager
def _verified_historical_git_state(
    authority: Mapping[str, Any], *, allow_imports: bool = False
):
    """Replace historical bare Git with the raw-authority-proven clean state.

    The adapter is scoped to one lower recovery call, covers every already
    imported ``git_state`` alias, and restores all aliases exactly.  It never
    starts Git, so repository-local hooks and ``core.fsmonitor`` cannot execute.
    """

    execution = _historical_execution_git_row(authority)
    runrecord = sys.modules.get("bu.runrecord")
    if type(runrecord) is not types.ModuleType:
        raise BootstrapRefused("historical runrecord module is unavailable")
    expected_source = (
        EXECUTION_WORKTREE / "src" / "bu" / "runrecord.py"
    ).resolve(strict=True)
    loader = getattr(getattr(runrecord, "__spec__", None), "loader", None)
    original = getattr(runrecord, "git_state", None)
    git_state_type = getattr(runrecord, "GitState", None)
    project_root = getattr(runrecord, "PROJECT_ROOT", None)
    if (
        type(original) is not types.FunctionType
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
        raise BootstrapRefused("historical git_state identity or shape differs")
    preexisting_git_states: dict[types.ModuleType, object] = {}
    for name, module in sorted(tuple(sys.modules.items())):
        if name != "bu" and not name.startswith("bu."):
            continue
        if type(module) is not types.ModuleType:
            raise BootstrapRefused(f"historical Git module {name} is not exact")
        if "git_state" in vars(module):
            preexisting_git_states[module] = vars(module)["git_state"]
    unseen_binding = object()
    bindings = _historical_git_bindings(original, allow_incomplete=allow_imports)

    def verified_git_state(repo: str | Path | None = None) -> Any:
        if repo is not None:
            if type(repo) is not str and not isinstance(repo, Path):
                raise BootstrapRefused("historical git_state repository type differs")
            try:
                repository = Path(repo).resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise BootstrapRefused(
                    "historical git_state repository is unavailable"
                ) from exc
            if repository != EXECUTION_WORKTREE.resolve(strict=True):
                raise BootstrapRefused("historical git_state requested another repository")
        current = _historical_execution_git_row(authority)
        for module in bindings:
            if vars(module).get("git_state") is not verified_git_state:
                raise BootstrapRefused("historical Git adapter changed during recovery")
        if vars(runrecord).get("GitState") is not git_state_type:
            raise BootstrapRefused("historical GitState type changed during recovery")
        state = git_state_type(
            commit=current["git_commit"], dirty=False, branch=current["branch"]
        )
        if type(state) is not git_state_type:
            raise BootstrapRefused("historical Git adapter returned another type")
        return state

    for module in bindings:
        module.git_state = verified_git_state
    if any(vars(module).get("git_state") is not verified_git_state for module in bindings):
        for module in bindings:
            module.git_state = original
        raise BootstrapRefused("historical Git adapter could not be installed exactly")
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
                raise BootstrapRefused(
                    "historical Git adapter changed before restoration"
                )
            current_bindings: list[types.ModuleType] = []
            for name, module in sorted(tuple(sys.modules.items())):
                if name != "bu" and not name.startswith("bu."):
                    continue
                if type(module) is not types.ModuleType:
                    raise BootstrapRefused(
                        f"historical Git module {name} changed during recovery"
                    )
                namespace = vars(module)
                if "git_state" not in namespace:
                    continue
                current_value = namespace["git_state"]
                prior_value = preexisting_git_states.get(module, unseen_binding)
                if prior_value is original or prior_value is unseen_binding:
                    if current_value is not verified_git_state:
                        raise BootstrapRefused(
                            "historical Git binding changed after import"
                        )
                    current_bindings.append(module)
                elif current_value is not prior_value:
                    raise BootstrapRefused(
                        "unrelated historical Git binding changed during recovery"
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
                raise BootstrapRefused(
                    "historical Git binding inventory is incomplete after import"
                )
            for module in current_bindings:
                module.git_state = original
            if any(vars(module).get("git_state") is not original for module in bindings):
                raise BootstrapRefused("historical Git adapter was not restored exactly")
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
                    and type(module) is types.ModuleType
                    and vars(module).get("git_state") is verified_git_state
                ):
                    try:
                        module.git_state = original
                    except BaseException:
                        pass
        if restore_error is not None:
            if body_error is not None:
                raise BootstrapRefused(
                    "historical Git adapter restoration failed after lower refusal"
                ) from restore_error
            raise BootstrapRefused(
                "historical Git adapter restoration failed"
            ) from restore_error


def _launch_once(authority: Mapping[str, Any]) -> dict[str, Any]:
    os.environ.pop(INVOCATION_ENV, None)
    P, Launch, gate = _install_old_source_tree(authority)
    Supervisor = importlib.import_module("bu.experiments.supervisor")
    original_lookup = Launch._historical_lease_record
    original_run_isolated = Launch.run_isolated_attempt
    original_get_context = Supervisor.multiprocessing.get_context
    original_pickle = Supervisor.pickle
    if (
        not callable(original_lookup)
        or not callable(original_run_isolated)
        or original_run_isolated is not Supervisor.run_isolated_attempt
        or not callable(original_get_context)
        or original_pickle is not sys.modules.get("pickle")
        or not callable(getattr(original_pickle, "dumps", None))
    ):
        raise BootstrapRefused("old historical launch seams differ")
    def exact_orphan_lookup(token: str) -> dict[str, Any]:
        if token == OLD_LEASE_TOKEN:
            return _historical_orphan_record(Launch, token)
        return original_lookup(token)

    def verified_run_isolated(callback: object, **kwargs: object) -> object:
        if callback is not Launch._fit_worker:
            raise BootstrapRefused("old launcher requested another fit callback")
        expected_payload = kwargs.get("payload")
        fit_context = _VerifiedFitContext(
            authority=authority,
            gate=gate,
            launch=Launch,
            supervisor=Supervisor,
        )

        def verified_get_context(method: str | None = None) -> _VerifiedFitContext:
            if method != "spawn":
                raise BootstrapRefused("old supervisor requested another start method")
            return fit_context

        def verified_no_pickle_dumps(
            value: object, *args: object, **options: object
        ) -> bytes:
            if (
                args
                or options
                or type(value) is not tuple
                or len(value) != 2
                or value[0] is not callback
                or value[1] is not expected_payload
            ):
                raise BootstrapRefused("historical picklability probe differs")
            return b"D-166 identity-only validation; no pickle serialization"

        if (
            Supervisor.multiprocessing.get_context is not original_get_context
            or Supervisor.pickle is not original_pickle
        ):
            raise BootstrapRefused("historical process seams changed before fit launch")
        Supervisor.multiprocessing.get_context = verified_get_context
        Supervisor.pickle = types.SimpleNamespace(dumps=verified_no_pickle_dumps)
        try:
            return original_run_isolated(callback, **kwargs)
        finally:
            Supervisor.multiprocessing.get_context = original_get_context
            Supervisor.pickle = original_pickle
            if (
                Supervisor.multiprocessing.get_context is not original_get_context
                or Supervisor.pickle is not original_pickle
            ):
                raise BootstrapRefused("historical process seams were not restored")

    before_keys = set(vars(Launch))
    Launch._historical_lease_record = exact_orphan_lookup
    Launch.run_isolated_attempt = verified_run_isolated
    if set(vars(Launch)) != before_keys:
        raise BootstrapRefused("old-module monkeypatch changed module shape")
    result: object = None
    lower_error: BaseException | None = None
    output_capture: dict[str, Any] | None = None
    capture_error: BaseException | None = None
    restore_error: BaseException | None = None
    try:
        _assert_old_normal_release_absent()
        _validate_execution_source_tree(authority)
        _validate_loaded_bu_modules(authority)
        def lower_with_verified_git() -> object:
            with _verified_historical_git_state(authority), _worker_relocation_readers(Launch):
                return Launch.launch_exp2a_repairs(
                    preflight_report=P.PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE,
                    output_root=P.OUTPUT_ROOT,
                    sync_root=P.SYNC_ROOT,
                    expected_git_commit=EXECUTION_COMMIT,
                )

        result, lower_error, output_capture = _capture_lower_output(
            lower_with_verified_git
        )
    except BaseException as exc:
        capture_error = exc
    finally:
        try:
            Launch._historical_lease_record = original_lookup
            Launch.run_isolated_attempt = original_run_isolated
            Supervisor.multiprocessing.get_context = original_get_context
            Supervisor.pickle = original_pickle
        except BaseException as exc:
            restore_error = exc
    if capture_error is not None:
        raise capture_error
    if output_capture is None:
        raise BootstrapRefused("lower output capture did not return evidence")
    if restore_error is not None:
        raise CapturedLowerRefused(
            BootstrapRefused("historical lease seam could not be restored"),
            output_capture,
        ) from restore_error
    if (
        Launch._historical_lease_record is not original_lookup
        or Launch.run_isolated_attempt is not original_run_isolated
        or Supervisor.multiprocessing.get_context is not original_get_context
        or Supervisor.pickle is not original_pickle
    ):
        raise CapturedLowerRefused(
            BootstrapRefused("historical launch seams were not restored"), output_capture
        )
    if lower_error is not None:
        raise CapturedLowerRefused(lower_error, output_capture) from lower_error
    try:
        _assert_old_normal_release_absent()
        _validate_execution_source_tree(authority)
        _validate_loaded_bu_modules(authority)
        if type(result) is not dict or result.get("counts") != EXPECTED_COUNTS:
            raise BootstrapRefused("old lower launcher returned different recovery counts")
        if result.get("status") != "complete" or result.get("failure") is not None or result.get("historical_retrained") is not False or result.get("lease_release_failure") is not None:
            raise BootstrapRefused("old lower launcher did not complete exactly")
        released = result.get("released_lease")
        if type(released) is not dict or type(released.get("token")) is not str or _HEX32.fullmatch(released["token"]) is None or released["token"] == OLD_LEASE_TOKEN:
            raise BootstrapRefused("continuation lease release is not exact")
        report = _plain_file(Path(result.get("report_path", "")), what="lower report")
        expected_report = OUTPUT_ROOT / REPORT_DIRECTORY / f"{released['token']}.json"
        copy_report = SYNC_ROOT / REPORT_DIRECTORY / expected_report.name
        if report.resolve() != expected_report.resolve():
            raise BootstrapRefused("old lower launcher returned an unexpected report path")
        report_sha = _same_bytes(report, copy_report, what="continuation lower report")
    except BaseException as exc:
        raise CapturedLowerRefused(exc, output_capture) from exc
    return {
        "counts": dict(EXPECTED_COUNTS),
        "lease_token": released["token"],
        "report_sha256": report_sha,
        "script_sha256": str(globals()["__transport_source_sha256__"]),
        "output_capture": output_capture,
    }


def _terminal_payload(
    *,
    status: str,
    invocation: Mapping[str, Any],
    invocation_sha: str,
    claim: Mapping[str, Any],
    claim_sha: str,
    claim_twins_complete: bool,
    operational_result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **{key: invocation[key] for key in _BASE_KEYS},
        "record_type": "bootstrap_terminal",
        "status": status,
        "bootstrap_schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "invocation": {"record_digest": invocation["record_digest"], "file_sha256": invocation_sha},
        "claim": {"record_digest": claim["record_digest"], "file_sha256": claim_sha, "twins_complete": claim_twins_complete},
        "operational_result": dict(operational_result),
        "automatic_retry_allowed": False,
    }


def _publish_terminal_twins(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Choose worker terminal as the sole finalization family under one lock."""

    with _finalization_lock():
        if _any_record_path(BOOTSTRAP_TERMINAL_FILE):
            raise BootstrapRefused("a bootstrap terminal path already exists")
        if _any_record_path(BOOTSTRAP_POSTMORTEM_FILE):
            raise BootstrapRefused(
                "controller postmortem already won bootstrap finalization"
            )
        return _exclusive_publish_twins(BOOTSTRAP_TERMINAL_FILE, payload)


def _success_output(
    *, result: Mapping[str, Any], invocation: Mapping[str, Any], invocation_sha: str,
    claim: Mapping[str, Any], claim_sha: str, terminal: Mapping[str, Any], terminal_sha: str,
) -> dict[str, Any]:
    return {
        "bootstrap_schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "status": "complete",
        "counts": dict(result["counts"]),
        "lease_token": result["lease_token"],
        "report_sha256": result["report_sha256"],
        "script_sha256": result["script_sha256"],
        "output_capture": dict(_validate_output_capture(result["output_capture"])),
        "invocation_record_digest": invocation["record_digest"],
        "invocation_file_sha256": invocation_sha,
        "claim_record_digest": claim["record_digest"],
        "claim_file_sha256": claim_sha,
        "terminal_record_digest": terminal["record_digest"],
        "terminal_file_sha256": terminal_sha,
        "scientific_values_emitted": False,
    }


def _failure_output(
    *, error: BaseException, invocation: Mapping[str, Any] | None = None,
    invocation_sha: str | None = None, claim: Mapping[str, Any] | None = None,
    claim_sha: str | None = None, terminal: Mapping[str, Any] | None = None,
    terminal_sha: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "bootstrap_schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "status": "refused",
        "error_type": type(error).__name__,
        "reason_sha256": _sha_bytes(str(error).encode("utf-8")),
        "scientific_values_emitted": False,
    }
    if invocation is not None and invocation_sha is not None:
        result.update({"invocation_record_digest": invocation["record_digest"], "invocation_file_sha256": invocation_sha})
    if claim is not None and claim_sha is not None:
        result.update({"claim_record_digest": claim["record_digest"], "claim_file_sha256": claim_sha})
    if terminal is not None and terminal_sha is not None:
        result.update({"terminal_record_digest": terminal["record_digest"], "terminal_file_sha256": terminal_sha})
    if isinstance(error, CapturedLowerRefused):
        result["output_capture"] = dict(
            _validate_output_capture(error.output_capture)
        )
    return result


def _terminalize_failure(
    error: BaseException,
    *, invocation: Mapping[str, Any], invocation_sha: str,
    claim: Mapping[str, Any], claim_sha: str, claim_twins_complete: bool,
) -> ClaimedBootstrapRefused:
    operational = {"error_type": type(error).__name__, "reason_sha256": _sha_bytes(str(error).encode("utf-8"))}
    if isinstance(error, CapturedLowerRefused):
        operational["output_capture"] = dict(
            _validate_output_capture(error.output_capture)
        )
    terminal, terminal_sha = _publish_terminal_twins(
        _terminal_payload(
            status="refused", invocation=invocation, invocation_sha=invocation_sha,
            claim=claim, claim_sha=claim_sha, claim_twins_complete=claim_twins_complete,
            operational_result=operational,
        ),
    )
    return ClaimedBootstrapRefused(
        _failure_output(error=error, invocation=invocation, invocation_sha=invocation_sha, claim=claim, claim_sha=claim_sha, terminal=terminal, terminal_sha=terminal_sha)
    )


def _run() -> dict[str, Any]:
    invocation, invocation_sha = _load_authorized_invocation()
    with _worker_relocation_admission(invocation["authority"]):
        return _run_authorized(invocation, invocation_sha)


def _run_authorized(invocation: Mapping[str, Any], invocation_sha: str) -> dict[str, Any]:
    claim_payload = _claim_payload(invocation, invocation_sha)
    intended_claim = _seal(claim_payload)
    try:
        claim, claim_sha = _exclusive_publish_twins(BOOTSTRAP_CLAIM_FILE, claim_payload)
    except BaseException as exc:
        if _any_record_path(BOOTSTRAP_CLAIM_FILE):
            try:
                classified_claim, classified_sha, twins_complete = (
                    _classify_claim_publication(intended_claim)
                )
            except BootstrapRefused as classification_exc:
                raise BootstrapRefused(
                    "another worker or an unverifiable claim permanently consumed the one-use invocation"
                ) from classification_exc
            try:
                raise _terminalize_failure(
                    exc, invocation=invocation, invocation_sha=invocation_sha,
                    claim=classified_claim, claim_sha=classified_sha,
                    claim_twins_complete=twins_complete,
                )
            except ClaimedBootstrapRefused:
                raise
            except BaseException as terminal_exc:
                raise BootstrapRefused(
                    "exclusive claim became partial and terminal publication failed; "
                    f"terminal error SHA256={_sha_bytes(str(terminal_exc).encode('utf-8'))}"
                ) from terminal_exc
        raise
    try:
        classified_claim, classified_sha, claim_twins_complete = (
            _classify_claim_publication(intended_claim)
        )
    except BootstrapRefused as exc:
        raise BootstrapRefused(
            "published claim could not be classified exactly; invocation remains consumed"
        ) from exc
    published_claim, published_sha = claim, claim_sha
    claim, claim_sha = classified_claim, classified_sha
    try:
        if not claim_twins_complete:
            raise BootstrapRefused("exclusive claim publication returned a partial claim")
        if _canonical(published_claim) != _canonical(claim) or published_sha != claim_sha:
            raise BootstrapRefused("claim publication result differs from actual claim files")
        _validate_claim(claim, invocation=invocation, invocation_sha=invocation_sha)
        chain = _validate_full_chain(invocation, invocation_sha)
        if _any_record_path(BOOTSTRAP_TERMINAL_FILE) or _any_record_path(
            BOOTSTRAP_POSTMORTEM_FILE
        ):
            raise BootstrapRefused(
                "bootstrap terminal or postmortem exists before lower launch"
            )
        with _authorized_orphan_transition(invocation, chain):
            result = _launch_once(invocation["authority"])
        output_capture = _validate_output_capture(result.get("output_capture"))
        operational = {
            "counts": dict(result["counts"]), "lease_token": result["lease_token"],
            "report_sha256": result["report_sha256"], "script_sha256": result["script_sha256"],
            "output_capture": dict(output_capture),
        }
        terminal, terminal_sha = _publish_terminal_twins(
            _terminal_payload(
                status="complete", invocation=invocation, invocation_sha=invocation_sha,
                claim=claim, claim_sha=claim_sha,
                claim_twins_complete=claim_twins_complete,
                operational_result=operational,
            ),
        )
        return _success_output(
            result=result, invocation=invocation, invocation_sha=invocation_sha,
            claim=claim, claim_sha=claim_sha, terminal=terminal, terminal_sha=terminal_sha,
        )
    except ClaimedBootstrapRefused:
        raise
    except BaseException as exc:
        try:
            raise _terminalize_failure(
                exc, invocation=invocation, invocation_sha=invocation_sha,
                claim=claim, claim_sha=claim_sha,
                claim_twins_complete=claim_twins_complete,
            )
        except ClaimedBootstrapRefused:
            raise
        except BaseException as terminal_exc:
            raise BootstrapRefused(
                "claimed invocation failed and terminal publication failed; "
                f"terminal error SHA256={_sha_bytes(str(terminal_exc).encode('utf-8'))}"
            ) from terminal_exc


def main() -> int:
    if len(sys.argv) != 1:
        print(json.dumps(_failure_output(error=BootstrapRefused("bootstrap accepts no arguments")), sort_keys=True, separators=(",", ":")))
        return 2
    try:
        result = _run()
    except ClaimedBootstrapRefused as exc:
        print(json.dumps(exc.output, sort_keys=True, separators=(",", ":")))
        return 2
    except BaseException as exc:
        print(json.dumps(_failure_output(error=exc), sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
