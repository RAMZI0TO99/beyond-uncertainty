"""Incident-specific D-161 recovery for the interrupted Week-8 E2A launch.

This is deliberately not a generic resume facility.  It recognizes one frozen
incident, publishes outcome-blind evidence before changing ownership state,
and permits one continuation epoch.  The scientific worker remains the code at
the original clean execution commit; this controller only adjudicates the
orphaned lease/publication window and validates the resulting evidence.

The four CLI commands accept no paths:

``adjudicate``
    Validate the exact interrupted state twice and publish immutable twin
    incident and epoch-001 terminal records.
``recover``
    Revalidate under the lease-transition lock, archive the orphan lease,
    quarantine the one known destination partial, and invoke the fixed
    bootstrap worker once.
``seal``
    Validate the complete two-epoch history, publish a twin completion record,
    and publish the production ``launch`` receipt with an explicit recovery
    field.
``status``
    Report only the operational state.  Terminal validation may mechanically
    hash quarantined scientific files, but never consults or emits their values.

All evidence records contain identities, paths, counts, and cryptographic
digests only.  Mechanical source validation can decode diagnostic arrays, but
their values are never consulted in a recovery decision and are never emitted.
Repair labels, ratios, exclusions, and H2 statistics are likewise neither used
nor serialized here.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

from ..durable import (
    atomic_write_bytes,
    atomic_write_json,
    fsync_directory,
    read_json,
    sha256_bytes,
    sha256_file,
)
from . import batch as B
from . import week8_exp2a_production as P
from . import week8_exp2a_repair_launch as Launch
from . import week8_exp2a_repairs as Plan
from . import windows_liveness
from . import supervisor as Supervisor


RECOVERY_SCHEMA_VERSION = 3
RECOVERY_ID = "week8-exp2a-d161-2026-09-02-attempt-001"
DECISION_ID = "D-161"
EXECUTION_COMMIT = "4515d5165756c8d1669d38d2ee854fa1051b1017"

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
PINNED_LOCAL_APPDATA = Path("C:/Users/aladdin-alyanai/AppData/Local")
PINNED_BASE_RUNTIME = PINNED_BASE_PYTHON.parent
PINNED_PYVENV = WORKSPACE_ROOT / "pro2" / ".venv" / "pyvenv.cfg"
PINNED_VENV_SCRIPTS = PINNED_PYTHON.parent
NATIVE_LAUNCHER = (
    CONTROLLER_WORKTREE / "scripts" / "week8_recovery_native_launcher.ps1"
)
NATIVE_POWERSHELL = Path(
    "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)
NATIVE_RUNTIME = WORKSPACE_ROOT / "week8-d167-native-runtime-attempt-001"
PINNED_SITE_PACKAGES = WORKSPACE_ROOT / "pro2" / ".venv" / "Lib" / "site-packages"
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
EXPECTED_RAW_AUTHORITY_HELPER_SHA256 = (
    "9067c7572692a4f0bc779488613c0e81f82233d8145bc1bb795e34f176e523aa"
)
ENTRYPOINT_GATE_ENVIRONMENT_NAME = "BU_D161_ENTRYPOINT_GATE"
CHILD_BUNDLE_ENVIRONMENT_NAME = "BU_D161_CHILD_BUNDLE_SHA256"
RAW_AUTHORITY_MODULE_NAME = "_bu_week8_d161_raw_authority"
BOOTSTRAP_SCRIPT = CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_worker.py"
INSPECTOR_SCRIPT = (
    CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_inspector.py"
)
ENTRYPOINT_SCRIPT = (
    CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_entrypoint.py"
)
RAW_AUTHORITY_HELPER = (
    CONTROLLER_WORKTREE / "scripts" / "week8_recovery_raw_authority.py"
)
CONTROLLER_MODULE = (
    CONTROLLER_WORKTREE
    / "src"
    / "bu"
    / "experiments"
    / "week8_exp2a_recovery.py"
)
RUNTIME_TEMP = (
    WORKSPACE_ROOT / "week8-exp2a-recovery-runtime-2026-09-02-attempt-001"
)
INSPECTOR_RUNTIME_TEMP = (
    WORKSPACE_ROOT
    / "week8-exp2a-recovery-inspector-runtime-2026-09-02-attempt-001"
)
RECOVERY_ROOT = WORKSPACE_ROOT / "week8-exp2a-recovery-2026-09-02-attempt-001"
RECOVERY_COPY_ROOT = (
    WORKSPACE_ROOT
    / "week8-exp2a-recovery-2026-09-02-attempt-001-project-evidence"
)

# D-177 reviewed controller-succession pins.  The incident authority was
# recorded by the D-175 controller commit; recovery can only run from its
# verified reviewed successor.  The succession is admitted only through this
# exact release record, its reviewed candidate manifest, and a fresh walk of
# the current controller worktree that equals that manifest's rows.
RELEASE_SESSION_ROOT = WORKSPACE_ROOT / "resume-2026-09-28-001"
RELEASE008_RECORD = "controller-release-008-proposal017.json"
RELEASE008_SHA256 = (
    "8ba1ce7e8f802cc6df1235d28b1b13b6b84ac995215d8c6393d5b794564d5569"
)
RELEASE008_MANIFEST = (
    RELEASE_SESSION_ROOT / "d175-doc-proposal-017" / "candidate-after.json"
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

BOOTSTRAP_CONTRACT_SCHEMA_VERSION = 4
CHILD_TRANSPORT_SCHEMA_VERSION = 1
CHILD_BOOTSTRAP_LITERAL = (
    "import base64,hashlib,importlib.machinery,importlib.util,json,os,sys\n"
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
CHILD_BOOTSTRAP_LITERAL_SHA256 = hashlib.sha256(
    CHILD_BOOTSTRAP_LITERAL.encode("utf-8")
).hexdigest()

EXPECTED_HASHES: dict[str, str] = {
    "plan_file": "9790d3ec9a93c8fcb0eb82dc96e2da3fe44607a96f26cd64755612e6cbd3197f",
    "source_ledger_file": "2265cbcece1033ce4d0f3df2e4b093d497c6815d5cb0592a511a6515f9fd7379",
    "prepare_receipt": "53605da944ff9bd80752fd254d960deed19064c42b07e75bce51acaedb7ebfbc",
    "preflight_receipt": "dd9ee61ff31078a85e02a3cb7a455b7cb374568a5094f0084bf7ed90d65f90a6",
    "preflight_report": "2001b4043c2a38db79db51035cf38b2777474a8f8624b6f5526fd37d554c9a0a",
    "launch_control_receipt": "28baf2f3e13a33d6a1c2f64b2d34f17d8bd3dbd48d0a60d1b6105252388e10be",
    "old_checkpoint": "a8dc8652d4000753a4b7e3731bbecaf09d448f72d56d98bdb15610188c583169",
    "old_lease": "ac3879395be164ea6b57dc10382e93236eacb7a76b222897bddbda58d2597f70",
    "old_event_stream": "13207af2f0a1d461cf471acc7dc9eeef03b6113dda3712acd778d5e4bf4dfc45",
    "old_event_tail_file": "cd49822ee99ddd909596d314a99e4749944580fdb4176a7e76bf43f9ef02b2ac",
}
EXPECTED_PLAN_DIGEST = "ef9364923722d103e6a09f1cc9bf826bf06917361e0c96c5004ab692df95612d"
EXPECTED_OLD_CHECKPOINT_DIGEST = (
    "3ec6d54d1bb0434bd7d4a28ee5d4c55fc3d1955f0d20a8577f267537d4f9cee5"
)
EXPECTED_INITIAL_COUNTS = {
    "events": 299,
    "started": 150,
    "synced": 149,
    "local_completed": 150,
    "durable_completed": 149,
    "untouched": 111,
    "partial_files": 11,
    "orphan_local_files": 15,
}
EXPECTED_RECOVERY_COUNTS = {
    "executed": 111,
    "resumed": 150,
    "synced": 261,
    "total": 261,
}
EXPECTED_FINAL_COUNTS = {
    "checkpoints": 2,
    "events": 523,
    "started": 261,
    "synced": 261,
    "complete": 1,
    "local_completed": 261,
    "durable_completed": 261,
}

_HEX32 = re.compile(r"[0-9a-f]{32}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN_FILE = re.compile(r"([0-9a-f]{32})\.json\Z")
_EVENT_FILE = re.compile(r"[0-9]{6}\.json\Z")


class RecoveryRefused(ValueError):
    """The one-use D-161 state machine cannot safely advance."""


_INSPECTOR_DIAGNOSTIC_ERROR_TYPES = frozenset({
    "InspectorRefused", "AuthorityRefused", "ValueError", "TypeError",
    "RuntimeError", "OSError", "PermissionError", "FileNotFoundError",
    "ImportError", "ModuleNotFoundError", "AttributeError", "KeyError",
    "NameError", "AssertionError", "UnicodeDecodeError", "JSONDecodeError",
    "Exception",
})


def _valid_authority_failure_fingerprints(value: object) -> bool:
    if type(value) is not list or not 1 <= len(value) <= 4:
        return False
    for error in value:
        if (
            type(error) is not dict
            or set(error) != {"error_type", "reason_sha256", "locations"}
            or type(error["error_type"]) is not str
            or error["error_type"] not in _INSPECTOR_DIAGNOSTIC_ERROR_TYPES
            or type(error["reason_sha256"]) is not str
            or _HEX64.fullmatch(error["reason_sha256"]) is None
            or type(error["locations"]) is not list or len(error["locations"]) > 4
        ):
            return False
        for location in error["locations"]:
            if (
                type(location) is not dict or set(location) != {"source", "line"}
                or type(location["source"]) is not str
                or location["source"] not in {"inspector", "raw_authority"}
                or type(location["line"]) is not int
                or not 0 < location["line"] <= 1_000_000
            ):
                return False
    return True


class _InspectorProcessRefused(RecoveryRefused):
    """Retain operational fingerprints without exposing captured child output."""

    def __init__(self, stdout: bytes, stderr: bytes, returncode: int) -> None:
        stdout_sha = sha256_bytes(stdout)
        stderr_sha = sha256_bytes(stderr)
        super().__init__(
            "old-source inspector refused; "
            f"stdout SHA256={stdout_sha}, stderr SHA256={stderr_sha}"
        )
        self.inspector_failure: dict[str, Any] = {
            "returncode": returncode,
            "stdout": {"bytes": len(stdout), "sha256": stdout_sha},
            "stderr": {"bytes": len(stderr), "sha256": stderr_sha},
            "inspector_refusal": None,
        }
        if len(stdout) > 4096:
            return
        try:
            refusal = _strict_json_line(stdout.decode("utf-8"), what="inspector refusal")
        except (UnicodeError, ValueError, TypeError, RecursionError):
            return
        keys = {
            "inspector_schema_version", "status", "error_type", "reason_sha256",
            "scientific_values_emitted", "production_mutation_performed",
        }
        if (
            type(refusal) is not dict or set(refusal) not in (keys, keys | {"authority_failure"})
            or type(refusal["inspector_schema_version"]) is not int
            or refusal["inspector_schema_version"] != 2
            or refusal["status"] != "refused"
            or refusal["scientific_values_emitted"] is not False
            or refusal["production_mutation_performed"] is not False
            or type(refusal["reason_sha256"]) is not str
            or _HEX64.fullmatch(refusal["reason_sha256"]) is None
            or type(refusal["error_type"]) is not str
            or refusal["error_type"] not in _INSPECTOR_DIAGNOSTIC_ERROR_TYPES
            or ("authority_failure" in refusal and not _valid_authority_failure_fingerprints(refusal["authority_failure"]))
        ):
            return
        self.inspector_failure["inspector_refusal"] = {
            "error_type": refusal["error_type"],
            "reason_sha256": refusal["reason_sha256"],
        }
        if "authority_failure" in refusal:
            self.inspector_failure["inspector_refusal"]["authority_failure"] = refusal["authority_failure"]


def _controller_refusal_locations(exc: BaseException) -> list[dict[str, Any]]:
    """Report only fixed controller source locations, never messages or locals."""
    locations = []
    trace = exc.__traceback__
    while trace is not None:
        code = trace.tb_frame.f_code
        if Path(code.co_filename) == Path(__file__):
            locations.append({"function": code.co_name, "line": trace.tb_lineno})
        trace = trace.tb_next
    return locations[-8:]


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
        raise RecoveryRefused("D-161 evidence must be strict JSON") from exc


def _canonical_ascii(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise RecoveryRefused("D-161 entrypoint evidence must be canonical ASCII JSON") from exc


def _seal(payload: Mapping[str, Any], field: str = "record_digest") -> dict[str, Any]:
    document = dict(payload)
    if field in document:
        raise RecoveryRefused(f"cannot seal a document already containing {field!r}")
    return {**document, field: sha256_bytes(_canonical(document))}


def _validate_seal(
    value: object, *, field: str = "record_digest", what: str
) -> dict[str, Any]:
    if type(value) is not dict or field not in value:
        raise RecoveryRefused(f"{what} is not a sealed object")
    digest = value[field]
    if type(digest) is not str or _HEX64.fullmatch(digest) is None:
        raise RecoveryRefused(f"{what} has a noncanonical digest")
    expected = _seal({key: item for key, item in value.items() if key != field}, field)
    if _canonical(value) != _canonical(expected):
        raise RecoveryRefused(f"{what} content digest differs")
    return value


def _expect_keys(value: object, keys: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise RecoveryRefused(f"{what} has missing or extra fields")
    return value


def _expect_sha(value: object, *, what: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise RecoveryRefused(f"{what} must be canonical lowercase SHA256")
    return value


def _exact_nonnegative(value: object, *, what: str) -> int:
    if type(value) is not int or value < 0:
        raise RecoveryRefused(f"{what} must be an exact non-negative integer")
    return value


def _same_bytes(left: Path, right: Path, *, what: str) -> str:
    for path in (left, right):
        if not os.path.lexists(path):
            raise RecoveryRefused(f"{what} twin is missing: {path}")
        info = path.lstat()
        attributes = int(getattr(info, "st_file_attributes", 0))
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or attributes & reparse
            or info.st_nlink != 1
        ):
            raise RecoveryRefused(
                f"{what} twin is not an independent plain file: {path}"
            )
    try:
        if os.path.samefile(left, right):
            raise RecoveryRefused(f"{what} twins alias one filesystem object")
    except OSError as exc:
        raise RecoveryRefused(f"cannot compare {what} twin identity: {exc}") from exc
    left_bytes = left.read_bytes()
    right_bytes = right.read_bytes()
    if left_bytes != right_bytes:
        raise RecoveryRefused(f"{what} twins differ")
    digest = sha256_bytes(left_bytes)
    if sha256_file(left) != digest or sha256_file(right) != digest:
        raise RecoveryRefused(f"{what} changed during read-back")
    return digest


def _ensure_recovery_root(path: Path) -> Path:
    candidate = Plan._project_path(path, directory=True, existing=os.path.lexists(path))
    candidate.mkdir(parents=True, exist_ok=True)
    return Plan._project_path(candidate, directory=True)


def _record_paths(name: str) -> tuple[Path, Path]:
    if name not in {
        INCIDENT_FILE,
        EPOCH001_TERMINAL_FILE,
        TRANSITION_INTENT_FILE,
        TRANSITION_COMPLETION_FILE,
        RECOVERY_COMPLETION_FILE,
        BOOTSTRAP_INVOCATION_FILE,
        BOOTSTRAP_CLAIM_FILE,
        BOOTSTRAP_TERMINAL_FILE,
        BOOTSTRAP_POSTMORTEM_FILE,
    }:
        raise RecoveryRefused(f"unknown D-161 record name {name!r}")
    return RECOVERY_ROOT / "records" / name, RECOVERY_COPY_ROOT / "records" / name


def _twin_presence(name: str) -> tuple[bool, bool]:
    """Return physical twin presence without erasing partial-stop evidence."""

    return tuple(os.path.lexists(path) for path in _record_paths(name))  # type: ignore[return-value]


def _record_presence(name: str) -> bool:
    present = _twin_presence(name)
    if any(present) and not all(present):
        raise RecoveryRefused(f"{name} has only one immutable twin")
    return all(present)


def _finalization_guard_path() -> Path:
    active = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / f"{Plan.COMMON_LEASE_NAME}.lease.json"
    )
    return active.with_name(f".{Plan.COMMON_LEASE_NAME}.lease-transition.lock")


def _validate_finalization_guard_file(path: Path, handle: Any) -> None:
    try:
        path_info = path.lstat()
        handle_info = os.fstat(handle.fileno())
    except OSError as exc:
        raise RecoveryRefused("cannot attest the recovery finalization guard") from exc
    attributes = int(getattr(path_info, "st_file_attributes", 0))
    if (
        stat.S_ISLNK(path_info.st_mode)
        or attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        or not stat.S_ISREG(path_info.st_mode)
        or not stat.S_ISREG(handle_info.st_mode)
        or int(getattr(path_info, "st_nlink", 0)) != 1
        or int(getattr(handle_info, "st_nlink", 0)) != 1
        or any(
            getattr(path_info, name, None) != getattr(handle_info, name, None)
            for name in ("st_dev", "st_ino")
        )
    ):
        raise RecoveryRefused("recovery finalization guard identity is unsafe")


@contextmanager
def _finalization_lock():
    """Serialize worker-terminal versus controller-postmortem publication."""

    path = _finalization_guard_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(path):
            initial = path.lstat()
            if (
                stat.S_ISLNK(initial.st_mode)
                or int(getattr(initial, "st_file_attributes", 0))
                & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
                or not stat.S_ISREG(initial.st_mode)
                or int(getattr(initial, "st_nlink", 0)) != 1
            ):
                raise RecoveryRefused("recovery finalization guard is unsafe")
        handle = path.open("a+b")
    except RecoveryRefused:
        raise
    except OSError as exc:
        raise RecoveryRefused("cannot open the recovery finalization guard") from exc
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
        except RecoveryRefused:
            raise
        except OSError as exc:
            raise RecoveryRefused("cannot acquire the recovery finalization guard") from exc
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
                raise RecoveryRefused(
                    "cannot release the recovery finalization guard"
                ) from exc


def _publish_twins(name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    document = _seal(payload)
    left, right = _record_paths(name)
    _ensure_recovery_root(left.parent)
    _ensure_recovery_root(right.parent)
    if os.path.lexists(left) or os.path.lexists(right):
        raise RecoveryRefused(f"immutable twin record already exists: {name}")
    _write_json_exclusive(left, document)
    _write_json_exclusive(right, document)
    _same_bytes(left, right, what=name)
    if read_json(left) != document or read_json(right) != document:
        raise RecoveryRefused(f"{name} changed after immutable publication")
    return document


def _write_json_exclusive(path: Path, document: Mapping[str, Any]) -> None:
    data = _canonical(dict(document)) + b"\n"
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
    except FileExistsError as exc:
        raise RecoveryRefused(f"immutable record already exists: {path.name}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # A partial exclusive record is itself durable stop evidence.  It is
        # deliberately not removed or retried.
        raise
    fsync_directory(path.parent)


def _publish_twins_exclusive(
    name: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    document = _seal(payload)
    left, right = _record_paths(name)
    _ensure_recovery_root(left.parent)
    _ensure_recovery_root(right.parent)
    if os.path.lexists(left) or os.path.lexists(right):
        raise RecoveryRefused(f"one-use record already exists: {name}")
    _write_json_exclusive(left, document)
    _write_json_exclusive(right, document)
    _same_bytes(left, right, what=name)
    if read_json(left) != document or read_json(right) != document:
        raise RecoveryRefused(f"{name} changed after exclusive publication")
    return document


def _validate_recovery_record(
    document: object, *, name: str, record_type: str
) -> dict[str, Any]:
    document = _validate_seal(document, what=name)
    if (
        document.get("recovery_schema_version") != RECOVERY_SCHEMA_VERSION
        or document.get("recovery_id") != RECOVERY_ID
        or document.get("decision_id") != DECISION_ID
        or document.get("record_type") != record_type
        or document.get("scientific_outcomes_consulted") is not False
        or document.get("scientific_values_emitted") is not False
    ):
        raise RecoveryRefused(f"{name} identity or outcome-blind policy differs")
    return document


def _load_available_twins(
    name: str, *, record_type: str
) -> tuple[dict[str, Any], str, bool]:
    """Validate every surviving twin and report whether both are present.

    Claim and terminal publication is deliberately exclusive and sequential.
    A host stop can therefore leave one immutable file.  Such a file is
    durable terminal evidence, not an absent record and never a retry opening.
    """

    left, right = _record_paths(name)
    presence = _twin_presence(name)
    if not any(presence):
        raise RecoveryRefused(f"{name} is absent")
    if all(presence):
        digest = _same_bytes(left, right, what=name)
        document = _validate_recovery_record(
            read_json(left), name=name, record_type=record_type
        )
        if read_json(right) != document:
            raise RecoveryRefused(f"{name} twin changed after validation")
        return document, digest, True

    surviving = left if presence[0] else right
    try:
        before = surviving.lstat()
    except OSError as exc:
        raise RecoveryRefused(f"cannot inspect surviving {name}") from exc
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or int(getattr(before, "st_file_attributes", 0)) & reparse
        or int(getattr(before, "st_nlink", 0)) != 1
    ):
        raise RecoveryRefused(
            f"surviving {name} is not an independent plain file"
        )
    data = surviving.read_bytes()
    digest = sha256_bytes(data)
    document = _validate_recovery_record(
        read_json(surviving), name=name, record_type=record_type
    )
    try:
        after = surviving.lstat()
    except OSError as exc:
        raise RecoveryRefused(f"surviving {name} disappeared") from exc
    if (
        sha256_file(surviving) != digest
        or any(
            getattr(before, field, None) != getattr(after, field, None)
            for field in (
                "st_dev",
                "st_ino",
                "st_size",
                "st_mtime_ns",
                "st_nlink",
                "st_file_attributes",
            )
        )
    ):
        raise RecoveryRefused(f"surviving {name} changed during validation")
    return document, digest, False


def _load_twins(name: str, *, record_type: str) -> tuple[dict[str, Any], str]:
    document, digest, complete = _load_available_twins(
        name, record_type=record_type
    )
    if not complete:
        raise RecoveryRefused(f"{name} has only one immutable twin")
    return document, digest


def _raw_authority_config(
    controller_commit: str, native_startup: Mapping[str, Any]
) -> dict[str, Any]:
    if type(controller_commit) is not str or _HEX40.fullmatch(controller_commit) is None:
        raise RecoveryRefused("controller authority commit is malformed")
    if type(native_startup) is not dict:
        raise RecoveryRefused("native startup authority is unavailable")
    launcher = native_startup.get("native_launcher")
    receipt_sha256 = native_startup.get("release_receipt_sha256")
    stage0_binding_sha256 = native_startup.get("stage0_binding_sha256")
    startup_binding_sha256 = native_startup.get("startup_binding_sha256")
    launcher_sha256 = launcher.get("sha256") if type(launcher) is dict else None
    if any(
        type(value) is not str or _HEX64.fullmatch(value) is None
        for value in (
            receipt_sha256,
            launcher_sha256,
            stage0_binding_sha256,
            startup_binding_sha256,
        )
    ):
        raise RecoveryRefused("native startup hashes are malformed")
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
        "pinned_local_appdata": str(PINNED_LOCAL_APPDATA),
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
        raise RecoveryRefused(f"{what} is unavailable") from exc
    attributes = int(getattr(before, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or attributes & reparse
        or before.st_nlink != 1
        or row["path"] != str(resolved)
        or type(row["size"]) is not int
        or row["size"] != before.st_size
    ):
        raise RecoveryRefused(f"{what} identity differs")
    observed_sha = sha256_file(path)
    try:
        after = path.lstat()
    except OSError as exc:
        raise RecoveryRefused(f"{what} disappeared during validation") from exc
    if (
        observed_sha != row["sha256"]
        or (expected_sha256 is not None and observed_sha != expected_sha256)
        or any(
            getattr(before, name, None) != getattr(after, name, None)
            for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
        )
    ):
        raise RecoveryRefused(f"{what} changed or has another SHA256")
    return row


def _read_bound_plain_bytes(
    path: Path, *, expected_sha256: str, what: str
) -> tuple[bytes, dict[str, Any]]:
    """Capture exactly the one-link bytes that were identity-checked."""

    try:
        before = path.lstat()
    except OSError as exc:
        raise RecoveryRefused(f"{what} is unavailable") from exc
    attributes = int(getattr(before, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or attributes & reparse
        or int(getattr(before, "st_nlink", 0)) != 1
    ):
        raise RecoveryRefused(f"{what} is not a one-link plain file")
    try:
        with path.open("rb", buffering=0) as stream:
            opened = os.fstat(stream.fileno())
            data = stream.read()
            after_open = os.fstat(stream.fileno())
        after_path = path.lstat()
    except OSError as exc:
        raise RecoveryRefused(f"{what} cannot be captured") from exc
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
    if (
        len(data) != before.st_size
        or any(
            getattr(before, name, None) != getattr(observed, name, None)
            for observed in (opened, after_open, after_path)
            for name in fields
        )
        or int(getattr(after_path, "st_file_attributes", 0)) & reparse
    ):
        raise RecoveryRefused(f"{what} changed during capture")
    digest = sha256_bytes(data)
    if digest != expected_sha256:
        raise RecoveryRefused(f"{what} SHA256 differs")
    return data, {
        "path": str(path.resolve(strict=True)),
        "sha256": digest,
        "size": len(data),
    }


def _load_static_raw_authority_module() -> ModuleType:
    """Execute the fixed helper from the exact bytes captured here."""

    source, _ = _read_bound_plain_bytes(
        RAW_AUTHORITY_HELPER,
        expected_sha256=EXPECTED_RAW_AUTHORITY_HELPER_SHA256,
        what="D-161 static raw-authority helper",
    )
    name = "_bu_week8_d161_static_raw_authority"
    loader = importlib.machinery.SourceFileLoader(name, str(RAW_AUTHORITY_HELPER))
    specification = importlib.util.spec_from_loader(name, loader)
    if specification is None:
        raise RecoveryRefused("static raw-authority helper lacks a specification")
    module = importlib.util.module_from_spec(specification)
    module.__dict__["__source_sha256__"] = sha256_bytes(source)
    sys.modules[name] = module
    try:
        exec(
            compile(
                source,
                str(RAW_AUTHORITY_HELPER),
                "exec",
                dont_inherit=True,
            ),
            module.__dict__,
        )
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _validate_entrypoint_gate() -> dict[str, Any]:
    """Validate and re-run the stdlib-only authority admitted by the entrypoint."""

    encoded = os.environ.get(ENTRYPOINT_GATE_ENVIRONMENT_NAME)
    if type(encoded) is not str or not encoded:
        raise RecoveryRefused("D-161 controller must enter through the fixed entrypoint")
    try:
        gate = json.loads(
            encoded,
            object_pairs_hook=_no_duplicate_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RecoveryRefused("entrypoint gate contains non-finite JSON")
            ),
        )
    except RecoveryRefused:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryRefused("entrypoint gate is not strict JSON") from exc
    expected_keys = {
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
    gate = _expect_keys(gate, expected_keys, what="entrypoint gate")
    if encoded != _canonical_ascii(gate).decode("ascii"):
        raise RecoveryRefused("entrypoint gate is not canonical JSON")
    unsealed = {key: value for key, value in gate.items() if key != "record_digest"}
    if (
        gate["entrypoint_gate_schema_version"] != 4
        or gate["record_type"] != "week8_d161_entrypoint_gate"
        or gate["decision_id"] != DECISION_ID
        or gate["command"]
        not in {
            "adjudicate",
            "recover",
            "seal",
            "status",
            "monitor",
            "finalize",
            "report",
            "figures",
        }
        or gate["record_digest"] != sha256_bytes(_canonical_ascii(unsealed))
        or gate["scientific_outcomes_consulted"] is not False
        or gate["scientific_values_emitted"] is not False
        or gate["production_mutation_performed"] is not False
    ):
        raise RecoveryRefused("entrypoint gate policy or digest differs")
    entrypoint = _gate_file_identity(
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
    del entrypoint
    expected_paths = [
        str((CONTROLLER_WORKTREE / "src").resolve(strict=True)),
        str(PINNED_SITE_PACKAGES.resolve(strict=True)),
    ]
    if gate["admitted_pythonpath"] != expected_paths:
        raise RecoveryRefused("entrypoint admitted Python paths differ")
    raw = gate["raw_authority"]
    if type(raw) is not dict or raw.get("raw_authority_helper") != helper:
        raise RecoveryRefused("entrypoint raw authority binding differs")
    module = sys.modules.get(RAW_AUTHORITY_MODULE_NAME)
    if type(module) is not ModuleType:
        raise RecoveryRefused("raw-authority helper is not loaded as one exact module")
    specification = getattr(module, "__spec__", None)
    loader = getattr(specification, "loader", None)
    if (
        type(getattr(module, "__file__", None)) is not str
        or Path(module.__file__).resolve(strict=True)
        != RAW_AUTHORITY_HELPER.resolve(strict=True)
        or type(loader) is not importlib.machinery.SourceFileLoader
        or getattr(module, "__source_sha256__", None)
        != EXPECTED_RAW_AUTHORITY_HELPER_SHA256
    ):
        raise RecoveryRefused("loaded raw-authority helper identity differs")
    revalidate = getattr(module, "revalidate_admitted_authority", None)
    if not callable(revalidate):
        raise RecoveryRefused("raw-authority revalidation API is unavailable")
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
        raise RecoveryRefused("raw authority revalidation refused") from exc
    if _canonical_ascii(observed) != _canonical_ascii(raw):
        raise RecoveryRefused("raw authority changed after path admission")
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
        "release_receipt_sha256": native["release_receipt_sha256"],
        "native_launcher_sha256": native["native_launcher"]["sha256"],
        "stage0_binding_sha256": native["stage0_binding_sha256"],
        "startup_binding_sha256": native["startup_binding_sha256"],
        "startup_environment_sha256": native["startup_environment_sha256"],
        "base_runtime_inventory_sha256": native["pinned_base_runtime"][
            "inventory_sha256"
        ],
        "venv_scripts_inventory_sha256": native["pinned_venv_scripts"][
            "inventory_sha256"
        ],
    }


_CROSS_LAUNCH_COMMAND_BOUND_BINDINGS = (
    "raw_authority_record_digest",
    "stage0_binding_sha256",
    "startup_binding_sha256",
)


def _cross_launch_authority_projection(authority: Mapping[str, Any]) -> bytes:
    """Canonical command-invariant view of a controller authority record.

    The pre-import authority binds the launch command: ``runtime.command``
    plus the command-derived stage0/startup binding digests and the record
    digest that covers them.  The incident authority is written by the
    adjudicate launch, so a later recover, seal or post-recovery launch can
    only be attested against it after projecting those fields away.  Each
    record's own integrity stays fully verified: the sealed record digest
    is checked when the entrypoint gate is parsed, so removing the
    launch-command variance removes no verification.
    """
    binding = {
        key: value
        for key, value in authority["preimport_authority"].items()
        if key not in _CROSS_LAUNCH_COMMAND_BOUND_BINDINGS
    }
    raw = authority["preimport_authority_record"]
    startup = {
        key: value
        for key, value in raw["native_startup"].items()
        if key not in _CROSS_LAUNCH_COMMAND_BOUND_BINDINGS[1:]
    }
    runtime = {
        key: value for key, value in raw["runtime"].items() if key != "command"
    }
    record = {
        key: value
        for key, value in raw.items()
        if key not in {"runtime", "native_startup", "record_digest"}
    }
    record["runtime"] = runtime
    record["native_startup"] = startup
    projected = {
        key: value
        for key, value in authority.items()
        if key not in {"preimport_authority", "preimport_authority_record"}
    }
    projected["preimport_authority"] = binding
    projected["preimport_authority_record"] = record
    return _canonical(projected)


# Controller-identity fields that a reviewed controller release legitimately
# rotates.  They are stripped from BOTH sides of the second, succession-only
# projection; every remaining field must still match exactly.  Stripping more
# than this set would silently accept unrelated authority drift.
_SUCCESSION_RECORD_IDENTITY_KEYS = frozenset(
    {
        "controller",
        "execution",
        "git",
        "git_runtime",
        "raw_authority_helper",
    }
)
_SUCCESSION_TOP_LEVEL_IDENTITY_KEYS = frozenset(
    {
        "controller_module",
        "bootstrap_worker",
        "recovery_inspector",
        "recovery_entrypoint",
        "raw_authority_helper",
        "controller_worktree",
        "execution_worktree",
        "git_runtime",
        "loaded_controller_modules",
    }
)
# Release-rotated controller-identity digests that live inside the compact
# pre-import binding and the raw record's native-startup/runtime sections.
# Each is derived from the controller's own commit, release receipt or
# tracked source bytes, so a reviewed succession rotates it; every one is
# independently re-attested by the pinned release record, the reviewed
# manifest walk, Git ancestry and the current side's own live gate.
_SUCCESSION_BINDING_IDENTITY_KEYS = frozenset(
    {
        "controller_tree_digest",
        "release_receipt_sha256",
        "native_launcher_sha256",
        "entrypoint_sha256",
        "raw_authority_helper_sha256",
    }
)
_SUCCESSION_STARTUP_IDENTITY_KEYS = frozenset(
    {
        "release_receipt_sha256",
        "native_launcher",
    }
)
_SUCCESSION_RUNTIME_IDENTITY_KEYS = frozenset(
    {
        "entrypoint_source_sha256",
        "outer_bootstrap_literal_sha256",
    }
)
_RECOVERY_CONTROLLER_MODULE_ID = "bu.experiments.week8_exp2a_recovery"
_RELEASE_CANDIDATE_FOLDERS = ("src", "tests", "scripts", "docs")


def _succession_authority_projection(authority: Mapping[str, Any]) -> bytes:
    """Canonical controller-succession view of a controller authority record.

    Same shape as the cross-launch projection, with the controller-identity
    fields also projected away from both sides: the raw-record controller,
    execution, Git and helper identities; the top-level captured source
    identities, worktree rows, Git runtime and loaded-module inventory; and
    the release-rotated controller digests inside the compact binding and
    the raw record's native-startup/runtime sections.  The loaded-module
    inventory is attested separately because its recovery-module row is
    legitimately derived from each side's own controller source.
    """

    binding = {
        key: value
        for key, value in authority["preimport_authority"].items()
        if key not in _CROSS_LAUNCH_COMMAND_BOUND_BINDINGS
        and key not in _SUCCESSION_BINDING_IDENTITY_KEYS
    }
    raw = authority["preimport_authority_record"]
    startup = {
        key: value
        for key, value in raw["native_startup"].items()
        if key not in _CROSS_LAUNCH_COMMAND_BOUND_BINDINGS[1:]
        and key not in _SUCCESSION_STARTUP_IDENTITY_KEYS
    }
    runtime = {
        key: value
        for key, value in raw["runtime"].items()
        if key != "command" and key not in _SUCCESSION_RUNTIME_IDENTITY_KEYS
    }
    record = {
        key: value
        for key, value in raw.items()
        if key not in {"runtime", "native_startup", "record_digest"}
    }
    record["runtime"] = runtime
    record["native_startup"] = startup
    record = {
        key: value
        for key, value in record.items()
        if key not in _SUCCESSION_RECORD_IDENTITY_KEYS
    }
    projected = {
        key: value
        for key, value in authority.items()
        if key not in {"preimport_authority", "preimport_authority_record"}
    }
    projected = {
        key: value
        for key, value in projected.items()
        if key not in _SUCCESSION_TOP_LEVEL_IDENTITY_KEYS
    }
    projected["preimport_authority"] = binding
    projected["preimport_authority_record"] = record
    return _canonical(projected)


def _lineage_git_is_ancestor(incident_commit: str, current_commit: str) -> bool:
    """One read-only ancestry query against the controller's own pinned Git.

    Uses the same isolated pinned-Git subprocess discipline as the verified
    raw-authority helper: exact executable hash, fixed ``-c`` controls with
    ``safe.directory`` scoped to the controller worktree, a minimal inherited
    environment, and refusal on any stderr or failed exit.  ``merge-base
    --is-ancestor`` exits zero only when the incident commit is an ancestor
    of the current commit.
    """

    if (
        type(incident_commit) is not str
        or _HEX40.fullmatch(incident_commit) is None
        or type(current_commit) is not str
        or _HEX40.fullmatch(current_commit) is None
    ):
        return False
    try:
        executable = PINNED_GIT.resolve(strict=True)
        runtime = PINNED_GIT_RUNTIME_ROOT.resolve(strict=True)
        safe_root = CONTROLLER_WORKTREE.resolve(strict=True)
        if sha256_file(executable) != EXPECTED_PINNED_GIT_SHA256:
            return False
        windows_root = Path("C:/Windows").resolve(strict=True)
        system32 = (windows_root / "System32").resolve(strict=True)
        environment = {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_EXEC_PATH": str(runtime),
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_TEMPLATE_DIR": os.devnull,
            "LC_ALL": "C",
            "PATH": os.pathsep.join(
                (str(runtime), str(system32), str(windows_root))
            ),
            "SystemRoot": str(windows_root),
            "WINDIR": str(windows_root),
        }
        command = [
            str(executable),
            "--no-pager",
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-c",
            f"safe.directory={safe_root}",
            "-C",
            str(safe_root),
            "merge-base",
            "--is-ancestor",
            incident_commit,
            current_commit,
        ]
        completed = subprocess.run(
            command,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            cwd=str(runtime),
            shell=False,
        )
    except (OSError, ValueError):
        return False
    return completed.returncode == 0 and completed.stderr == b""


def _release_candidate_rows() -> list[list[str]]:
    """Fresh reviewed-release candidate walk of the controller worktree.

    Mirrors the reviewed D-175 proposal walk exactly: every plain file under
    ``src``, ``tests``, ``scripts`` and ``docs`` except ``__pycache__``
    entries, plus every plain top-level file except ``.git``, each row a
    ``[posix-relative-path, sha256]`` pair in the reviewed order.
    """

    root = CONTROLLER_WORKTREE.resolve(strict=True)
    rows: list[list[str]] = []
    for folder in _RELEASE_CANDIDATE_FOLDERS:
        inventory = _plain_tree_inventory(
            root / folder, what=f"D-177 release candidate {folder}"
        )
        file_rows = [
            row
            for row in _file_rows(inventory)
            if "__pycache__" not in row["path"].split("/")
        ]
        # The reviewed proposal walk enumerates ``sorted(base.rglob("*"))``,
        # whose pathlib ordering case-folds on Windows; mirror that order.
        file_rows.sort(key=lambda row: row["path"].casefold())
        for row in file_rows:
            rows.append([f"{folder}/{row['path']}", row["sha256"]])
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    for child in sorted(root.iterdir()):
        if child.name == ".git" or not child.is_file():
            continue
        info = child.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or int(getattr(info, "st_file_attributes", 0)) & reparse
            or info.st_nlink != 1
        ):
            raise RecoveryRefused(
                "D-177 release candidate top-level entry is not plain"
            )
        rows.append([child.name, sha256_file(child)])
    if len(rows) != len({row[0] for row in rows}):
        raise RecoveryRefused("D-177 release candidate walk repeats a path")
    return rows


def _pinned_release_record() -> dict[str, Any]:
    """Load the one pinned controller release record by exact hash."""

    data, _identity = _read_bound_plain_bytes(
        RELEASE_SESSION_ROOT / RELEASE008_RECORD,
        expected_sha256=RELEASE008_SHA256,
        what="D-177 pinned controller release record",
    )
    record = json.loads(data.decode("utf-8", errors="strict"))
    if type(record) is not dict:
        raise RecoveryRefused("D-177 pinned release record is not an object")
    return record


def _release_manifest_binds_current_worktree(
    record: Mapping[str, Any],
) -> bool:
    """Bind the reviewed manifest bytes to a fresh walk of this worktree."""

    expected_manifest_sha256 = record.get("FinalCandidateManifestSha256")
    if (
        type(expected_manifest_sha256) is not str
        or _HEX64.fullmatch(expected_manifest_sha256) is None
    ):
        return False
    data, _identity = _read_bound_plain_bytes(
        RELEASE008_MANIFEST,
        expected_sha256=expected_manifest_sha256,
        what="D-177 reviewed release candidate manifest",
    )
    rows = json.loads(data.decode("utf-8", errors="strict"))
    if type(rows) is not list or not rows:
        return False
    for row in rows:
        if (
            type(row) is not list
            or len(row) != 2
            or not all(type(item) is str for item in row)
            or _HEX64.fullmatch(row[1]) is None
        ):
            return False
    return _release_candidate_rows() == rows


def _succession_loaded_modules_attestation(
    current_authority: Mapping[str, Any],
    incident_authority: Mapping[str, Any],
) -> bool:
    """Attest the loaded-module inventories across a controller succession.

    Both inventories must have the same shape and length, every module row
    other than the recovery controller module itself must be byte-identical,
    and each side's recovery-module row must carry that side's own captured
    controller-module digest.
    """

    inventories = (
        current_authority["loaded_controller_modules"],
        incident_authority["loaded_controller_modules"],
    )
    authorities = (current_authority, incident_authority)
    parsed: list[dict[str, dict[str, Any]]] = []
    for rows in inventories:
        if type(rows) is not list or not rows:
            return False
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            if (
                type(row) is not dict
                or set(row) != {"module_id", "source_path", "source_sha256", "git_blob"}
                or type(row["module_id"]) is not str
                or not row["module_id"]
                or row["module_id"] in by_id
                or type(row["source_path"]) is not str
                or type(row["source_sha256"]) is not str
                or _HEX64.fullmatch(row["source_sha256"]) is None
                or type(row["git_blob"]) is not str
                or _HEX40.fullmatch(row["git_blob"]) is None
            ):
                return False
            by_id[row["module_id"]] = row
        parsed.append(by_id)
    if len(parsed[0]) != len(parsed[1]) or set(parsed[0]) != set(parsed[1]):
        return False
    for module_id, row in parsed[0].items():
        if module_id == _RECOVERY_CONTROLLER_MODULE_ID:
            continue
        if row != parsed[1][module_id]:
            return False
    for by_id, authority in zip(parsed, authorities):
        recovery_row = by_id.get(_RECOVERY_CONTROLLER_MODULE_ID)
        controller_module = authority.get("controller_module")
        if (
            type(recovery_row) is not dict
            or type(controller_module) is not dict
            or recovery_row["source_sha256"] != controller_module.get("sha256")
        ):
            return False
    return True


def _reviewed_controller_succession(
    current_authority: Mapping[str, Any],
    incident_authority: Mapping[str, Any],
) -> bool:
    """Accept exactly one reviewed controller-succession step, or nothing.

    The current controller must descend from the incident controller in the
    controller worktree's own Git, the pinned release record must prove that
    exact parent/child succession with no remote push and committed blobs
    matching the reviewed worktree bytes, its reviewed candidate manifest
    must bind byte-for-byte to a fresh walk of the current worktree, every
    non-controller-identity authority field must still match exactly, and
    the loaded-module inventories must satisfy the succession attestation.
    Any anomaly refuses.
    """

    incident_commit = incident_authority["controller_worktree"]["git_commit"]
    current_commit = current_authority["controller_worktree"]["git_commit"]
    if incident_commit == current_commit:
        return False
    if not _lineage_git_is_ancestor(incident_commit, current_commit):
        return False
    record = _pinned_release_record()
    if (
        record.get("ParentCommit") != incident_commit
        or record.get("ControllerCommit") != current_commit
        or record.get("RemotePushPerformed") is not False
        or record.get("CommittedBlobsMatchReviewedWorktreeBytes") is not True
    ):
        return False
    if not _release_manifest_binds_current_worktree(record):
        return False
    if _succession_authority_projection(
        current_authority
    ) != _succession_authority_projection(incident_authority):
        return False
    return _succession_loaded_modules_attestation(
        current_authority, incident_authority
    )


def _authority_lineage_matches(
    current_authority: Mapping[str, Any],
    incident_authority: Mapping[str, Any],
) -> bool:
    """Cross-launch authority gate for the D-177 reviewed-succession era.

    Accepts the same controller unchanged (the D-176 command-invariant
    projection equality) or exactly the reviewed controller succession
    proved by the pinned release record, the worktree's own Git ancestry,
    the reviewed candidate manifest, exact equality of every remaining
    authority field, and the loaded-module succession attestation.  Any
    anomaly returns False so callers keep their unchanged refusal.
    """

    try:
        if _cross_launch_authority_projection(
            current_authority
        ) == _cross_launch_authority_projection(incident_authority):
            return True
        return _reviewed_controller_succession(current_authority, incident_authority)
    except (KeyError, IndexError, TypeError, ValueError, OSError, RecursionError):
        return False


def _controller_runtime_flags() -> dict[str, bool | int]:
    return {
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "ignore_environment": bool(getattr(sys.flags, "ignore_environment", False)),
        "isolated": bool(getattr(sys.flags, "isolated", False)),
        "no_site": bool(sys.flags.no_site),
        "no_user_site": bool(sys.flags.no_user_site),
        "safe_path": bool(getattr(sys.flags, "safe_path", False)),
        "utf8_mode": int(sys.flags.utf8_mode),
    }


def _validate_controller_runtime() -> dict[str, Any]:
    """Bind the controller to the exact isolated pinned interpreter launch."""

    current = Path(sys.executable)
    try:
        pinned = PINNED_PYTHON.resolve(strict=True)
        base = PINNED_BASE_PYTHON.resolve(strict=True)
        current = current.resolve(strict=True)
        site_packages = PINNED_SITE_PACKAGES.resolve(strict=True)
        source = (CONTROLLER_WORKTREE / "src").resolve(strict=True)
        same = os.path.samefile(current, pinned)
        same_base = os.path.samefile(Path(sys._base_executable), base)
    except OSError as exc:
        raise RecoveryRefused("cannot resolve the pinned controller runtime") from exc
    if (
        not same
        or not same_base
        or sha256_file(pinned) != EXPECTED_PINNED_PYTHON_SHA256
        or sha256_file(base) != EXPECTED_PINNED_BASE_PYTHON_SHA256
        or _controller_runtime_flags()
        != {
            "dont_write_bytecode": True,
            "ignore_environment": True,
            "isolated": True,
            "no_site": True,
            "no_user_site": True,
            "safe_path": True,
            "utf8_mode": 1,
        }
    ):
        raise RecoveryRefused(
            "controller requires the exact pinned Python under -I -S -B -X utf8"
        )
    expected_pythonpath = os.pathsep.join((str(source), str(site_packages)))
    # D-168 clears all PYTHON* names before startup; the exact flags above
    # govern isolation. The verified entrypoint adds only PYTHONPATH as
    # post-admission metadata after explicitly installing the admitted paths.
    required_environment = {
        "PYTHONPATH": expected_pythonpath,
    }
    observed_python_names = {
        name for name in os.environ if name.upper().startswith("PYTHON")
    }
    gate = _validate_entrypoint_gate()
    raw_runtime = gate["raw_authority"]["runtime"]
    admitted_middle = list(sys.path[1:-1]) if len(sys.path) >= 3 else []
    if (
        observed_python_names != set(required_environment)
        or any(os.environ.get(name) != value for name, value in required_environment.items())
        or len(sys.path) < 3
        or Path(sys.path[0]).resolve() != source
        or Path(sys.path[-1]).resolve() != site_packages
        or sha256_bytes(_canonical_ascii(admitted_middle))
        != raw_runtime.get("preimport_sys_path_digest")
    ):
        raise RecoveryRefused("controller Python path/environment is not exact")
    return gate


def _validate_loaded_controller_modules(
    raw_authority: Mapping[str, Any], raw_module: ModuleType
) -> list[dict[str, str]]:
    """Prove every loaded ``bu`` module executed captured controller bytes."""

    admitted_blob = getattr(raw_module, "admitted_git_blob", None)
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    if not callable(admitted_blob) or not callable(admitted_source):
        raise RecoveryRefused("raw-authority source lookup API is unavailable")

    root = CONTROLLER_WORKTREE.resolve(strict=True)
    source_root = (root / "src").resolve(strict=True)
    for candidate in source_root.iterdir():
        if candidate.name == "bu":
            continue
        if candidate.suffix.lower() == ".py" or (
            candidate.is_dir() and (candidate / "__init__.py").is_file()
        ):
            raise RecoveryRefused(
                "controller source root contains a non-bu import shadow"
            )
    for name, module in sorted(sys.modules.items()):
        if name == "bu" or name.startswith("bu.") or not isinstance(module, ModuleType):
            continue
        filename = getattr(module, "__file__", None)
        if type(filename) is not str:
            continue
        try:
            path = Path(filename).resolve(strict=True)
        except OSError:
            continue
        if path.is_relative_to(source_root):
            # The parent relocation scope loads this one captured source under
            # a private, non-bu name before the command handler runs.  Its
            # bundle validates the exact module, loader, source bytes and Git
            # identity against raw authority at every use.
            state = _ACTIVE_RELOCATION
            if (
                name == "_week8_d161_relocation_provenance"
                and path
                == (source_root / "bu/experiments/week8_relocation_provenance.py").resolve(
                    strict=True
                )
                and type(state) is tuple
                and len(state) == 6
                and state[0] is raw_module
                and _canonical_ascii(state[1]) == _canonical_ascii(raw_authority)
                and type(getattr(state[2], "modules", None)) is dict
                and state[2].modules.get("provenance") is module
            ):
                _relocation_state()
                continue
            raise RecoveryRefused(
                f"loaded non-bu module {name} came from controller source root"
            )
    rows: list[dict[str, str]] = []
    for name, module in sorted(sys.modules.items()):
        if name != "bu" and not name.startswith("bu."):
            continue
        if not isinstance(module, ModuleType):
            raise RecoveryRefused(f"loaded {name} is not an exact module")
        filename = getattr(module, "__file__", None)
        specification = getattr(module, "__spec__", None)
        origin = getattr(specification, "origin", None)
        loader = getattr(specification, "loader", None)
        if type(filename) is not str or type(origin) is not str:
            raise RecoveryRefused(f"loaded {name} lacks a source identity")
        try:
            path = Path(filename).resolve(strict=True)
            origin_path = Path(origin).resolve(strict=True)
        except OSError as exc:
            raise RecoveryRefused(f"loaded {name} source cannot be resolved") from exc
        if (
            path != origin_path
            or path.suffix.lower() != ".py"
            or not path.is_relative_to(source_root)
            or getattr(loader, "binding_marker", None)
            != "week8_d161_verified_source_v2"
            or getattr(module, "__loader__", None) is not loader
            or getattr(loader, "name", None) != name
            or Path(str(getattr(loader, "path", ""))).resolve() != path
        ):
            raise RecoveryRefused(
                f"loaded {name} was not executed by the bound controller source loader"
            )
        relative = path.relative_to(root).as_posix()
        try:
            head_blob = admitted_blob(raw_authority, "controller", relative)
            captured = admitted_source(raw_authority, "controller", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise RecoveryRefused(
                f"loaded {name} is absent from raw controller authority"
            ) from exc
        if type(head_blob) is not str or _HEX40.fullmatch(head_blob) is None:
            raise RecoveryRefused(f"loaded {name} has no canonical raw Git blob")
        source_sha = sha256_bytes(captured)
        if getattr(loader, "source_sha256", None) != source_sha:
            raise RecoveryRefused(f"loaded {name} differs from captured controller bytes")
        rows.append(
            {
                "module_id": name,
                "source_path": str(path),
                "source_sha256": source_sha,
                "git_blob": head_blob,
            }
        )
    module_ids = {row["module_id"] for row in rows}
    if not {
        "bu",
        "bu.experiments.week8_exp2a_recovery",
    }.issubset(module_ids):
        raise RecoveryRefused("required controller modules were not source-attested")
    return rows


def _controller_authority() -> dict[str, Any]:
    gate = _validate_controller_runtime()
    raw = gate["raw_authority"]
    raw_module = sys.modules.get(RAW_AUTHORITY_MODULE_NAME)
    if type(raw_module) is not ModuleType:
        raise RecoveryRefused("raw-authority helper module is unavailable")
    admitted_blob = getattr(raw_module, "admitted_git_blob", None)
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    if not callable(admitted_blob) or not callable(admitted_source):
        raise RecoveryRefused("raw-authority source lookup API is unavailable")
    controller = {
        "path": raw["controller"]["path"],
        "git_commit": raw["controller"]["git_commit"],
        "detached": raw["controller"]["detached"],
    }
    execution = {
        "path": raw["execution"]["path"],
        "git_commit": raw["execution"]["git_commit"],
        "detached": raw["execution"]["detached"],
    }
    if execution["git_commit"] != EXECUTION_COMMIT or execution["detached"] is not True:
        raise RecoveryRefused("raw execution authority differs from D-161")
    expected_module = CONTROLLER_MODULE.resolve()
    if Path(__file__).resolve() != expected_module:
        raise RecoveryRefused("controller was not imported from the fixed worktree")
    for path, what in (
        (CONTROLLER_MODULE, "recovery controller"),
        (BOOTSTRAP_SCRIPT, "recovery bootstrap"),
        (INSPECTOR_SCRIPT, "old-source inspector"),
        (ENTRYPOINT_SCRIPT, "recovery entrypoint"),
        (RAW_AUTHORITY_HELPER, "raw-authority helper"),
        (PINNED_PYTHON, "pinned interpreter"),
        (PINNED_BASE_PYTHON, "pinned base interpreter"),
    ):
        if not path.is_file():
            raise RecoveryRefused(f"{what} is unavailable at its fixed path")
    for relative in (
        "src/bu/experiments/week8_exp2a_recovery.py",
        "scripts/week8_exp2a_recovery_worker.py",
        "scripts/week8_exp2a_recovery_inspector.py",
        "scripts/week8_exp2a_recovery_entrypoint.py",
        "scripts/week8_recovery_raw_authority.py",
    ):
        try:
            blob = admitted_blob(raw, "controller", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise RecoveryRefused(
                f"{relative} is not committed controller source"
            ) from exc
        if type(blob) is not str or _HEX40.fullmatch(blob) is None:
            raise RecoveryRefused(f"{relative} has no canonical raw Git blob")
    loaded_modules = _validate_loaded_controller_modules(raw, raw_module)

    def captured_identity(relative: str, path: Path) -> dict[str, str]:
        try:
            source_bytes = admitted_source(raw, "controller", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise RecoveryRefused(
                f"captured controller source is unavailable: {relative}"
            ) from exc
        return {
            "path": str(path.resolve(strict=True)),
            "sha256": sha256_bytes(source_bytes),
        }

    return {
        "controller_worktree": controller,
        "execution_worktree": execution,
        "controller_module": captured_identity(
            "src/bu/experiments/week8_exp2a_recovery.py", CONTROLLER_MODULE
        ),
        "bootstrap_worker": captured_identity(
            "scripts/week8_exp2a_recovery_worker.py", BOOTSTRAP_SCRIPT
        ),
        "recovery_inspector": captured_identity(
            "scripts/week8_exp2a_recovery_inspector.py", INSPECTOR_SCRIPT
        ),
        "recovery_entrypoint": captured_identity(
            "scripts/week8_exp2a_recovery_entrypoint.py", ENTRYPOINT_SCRIPT
        ),
        "raw_authority_helper": captured_identity(
            "scripts/week8_recovery_raw_authority.py", RAW_AUTHORITY_HELPER
        ),
        "preimport_authority": _preimport_authority_binding(gate),
        "preimport_authority_record": raw,
        "pinned_python": {
            "path": raw["runtime"]["pinned_python"]["path"],
            "sha256": raw["runtime"]["pinned_python"]["sha256"],
        },
        "base_python": {
            "path": raw["runtime"]["pinned_base_python"]["path"],
            "sha256": raw["runtime"]["pinned_base_python"]["sha256"],
        },
        "git_executable": {
            "path": raw["git"]["path"],
            "sha256": raw["git"]["sha256"],
        },
        "git_runtime": raw["git_runtime"],
        "loaded_controller_modules": loaded_modules,
    }


def _assert_current_controller_authority(
    incident: Mapping[str, Any],
) -> dict[str, Any]:
    """Re-attest the clean controller before any completion is trusted."""

    current = _controller_authority()
    if not _authority_lineage_matches(current, incident["authority"]):
        raise RecoveryRefused("current controller authority differs from the incident")
    return current


def _assert_current_static_controller_authority(
    incident: Mapping[str, Any],
) -> dict[str, Any]:
    """Re-attest immutable controller authority outside the live recovery gate.

    Ordinary monitor/finalize/report/figures processes cannot reproduce the
    historical pre-import runtime.  They must nevertheless prove every static
    byte, tree, dependency and Git-runtime identity recorded by adjudication.
    """

    authority = incident.get("authority")
    if type(authority) is not dict:
        raise RecoveryRefused("incident controller authority is malformed")
    raw = authority.get("preimport_authority_record")
    if type(raw) is not dict:
        raise RecoveryRefused("incident lacks the full pre-import authority record")
    module = _load_static_raw_authority_module()
    revalidate = getattr(module, "revalidate_recorded_static_authority", None)
    admitted_source = getattr(module, "admitted_source_bytes", None)
    admitted_blob = getattr(module, "admitted_git_blob", None)
    if not all(callable(value) for value in (revalidate, admitted_source, admitted_blob)):
        raise RecoveryRefused("static raw-authority APIs are unavailable")
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
        raise RecoveryRefused("recorded static authority revalidation refused") from exc
    if _canonical_ascii(observed) != _canonical_ascii(raw):
        raise RecoveryRefused("recorded static authority changed")

    controller = {
        "path": raw["controller"]["path"],
        "git_commit": raw["controller"]["git_commit"],
        "detached": raw["controller"]["detached"],
    }
    execution = {
        "path": raw["execution"]["path"],
        "git_commit": raw["execution"]["git_commit"],
        "detached": raw["execution"]["detached"],
    }
    if authority.get("controller_worktree") != controller or authority.get(
        "execution_worktree"
    ) != execution:
        raise RecoveryRefused("incident worktree authority differs from raw authority")

    source_contract = {
        "controller_module": (
            "src/bu/experiments/week8_exp2a_recovery.py",
            CONTROLLER_MODULE,
        ),
        "bootstrap_worker": (
            "scripts/week8_exp2a_recovery_worker.py",
            BOOTSTRAP_SCRIPT,
        ),
        "recovery_inspector": (
            "scripts/week8_exp2a_recovery_inspector.py",
            INSPECTOR_SCRIPT,
        ),
        "recovery_entrypoint": (
            "scripts/week8_exp2a_recovery_entrypoint.py",
            ENTRYPOINT_SCRIPT,
        ),
        "raw_authority_helper": (
            "scripts/week8_recovery_raw_authority.py",
            RAW_AUTHORITY_HELPER,
        ),
    }
    for key, (relative, path) in source_contract.items():
        try:
            source_bytes = admitted_source(raw, "controller", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise RecoveryRefused(f"incident source authority is unavailable: {key}") from exc
        expected = {
            "path": str(path.resolve(strict=True)),
            "sha256": sha256_bytes(source_bytes),
        }
        if authority.get(key) != expected:
            raise RecoveryRefused(f"incident source authority differs: {key}")

    expected_binding = {
        "raw_authority_schema_version": raw["raw_authority_schema_version"],
            "entrypoint_schema_version": 4,
        "entrypoint_sha256": authority["recovery_entrypoint"]["sha256"],
        "raw_authority_helper_sha256": raw["raw_authority_helper"]["sha256"],
        "raw_authority_record_digest": raw["record_digest"],
        "controller_tree_digest": raw["controller"]["worktree_inventory_digest"],
        "execution_tree_digest": raw["execution"]["worktree_inventory_digest"],
        "git_runtime_inventory_digest": raw["git_runtime"]["inventory_digest"],
            "site_packages_inventory_digest": raw["runtime"]["pinned_site_packages"][
                "inventory_digest"
            ],
            "stage0_binding_sha256": raw["native_startup"][
                "stage0_binding_sha256"
            ],
        "release_receipt_sha256": raw["native_startup"][
            "release_receipt_sha256"
        ],
        "native_launcher_sha256": raw["native_startup"]["native_launcher"][
            "sha256"
        ],
        "startup_binding_sha256": raw["native_startup"][
            "startup_binding_sha256"
        ],
        "startup_environment_sha256": raw["native_startup"][
            "startup_environment_sha256"
        ],
        "base_runtime_inventory_sha256": raw["native_startup"][
            "pinned_base_runtime"
        ]["inventory_sha256"],
        "venv_scripts_inventory_sha256": raw["native_startup"][
            "pinned_venv_scripts"
        ]["inventory_sha256"],
    }
    if authority.get("preimport_authority") != expected_binding:
        raise RecoveryRefused("incident compact pre-import binding differs")
    if authority.get("pinned_python") != {
        "path": raw["runtime"]["pinned_python"]["path"],
        "sha256": raw["runtime"]["pinned_python"]["sha256"],
    } or authority.get("base_python") != {
        "path": raw["runtime"]["pinned_base_python"]["path"],
        "sha256": raw["runtime"]["pinned_base_python"]["sha256"],
    }:
        raise RecoveryRefused("incident Python authority differs from raw authority")
    if authority.get("git_executable") != {
        "path": raw["git"]["path"],
        "sha256": raw["git"]["sha256"],
    } or authority.get("git_runtime") != raw["git_runtime"]:
        raise RecoveryRefused("incident Git authority differs from raw authority")

    rows = authority.get("loaded_controller_modules")
    if type(rows) is not list or not rows:
        raise RecoveryRefused("incident loaded-controller inventory is malformed")
    seen: set[str] = set()
    root = CONTROLLER_WORKTREE.resolve(strict=True)
    for row in rows:
        if type(row) is not dict or set(row) != {
            "module_id",
            "source_path",
            "source_sha256",
            "git_blob",
        }:
            raise RecoveryRefused("incident loaded-controller row is malformed")
        name = row["module_id"]
        if type(name) is not str or name in seen:
            raise RecoveryRefused("incident loaded-controller module id is malformed")
        seen.add(name)
        try:
            source_path = Path(row["source_path"]).resolve(strict=True)
            relative = source_path.relative_to(root).as_posix()
            source_bytes = admitted_source(raw, "controller", relative)
            blob = admitted_blob(raw, "controller", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise RecoveryRefused("incident loaded-controller source is unavailable") from exc
        if (
            row["source_sha256"] != sha256_bytes(source_bytes)
            or row["git_blob"] != blob
        ):
            raise RecoveryRefused("incident loaded-controller row differs from raw authority")
    if not {"bu", "bu.experiments.week8_exp2a_recovery"}.issubset(seen):
        raise RecoveryRefused("incident loaded-controller inventory is incomplete")
    return observed


def _runtime_temp_directory_identity(path: Path, *, what: str) -> dict[str, Any]:
    try:
        root = Plan._project_path(path, directory=True)
        info = root.lstat()
    except (OSError, TypeError, ValueError) as exc:
        raise RecoveryRefused(f"{what} identity is unavailable") from exc
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    birth_ns = int(getattr(info, "st_birthtime_ns", info.st_ctime_ns))
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or attributes & reparse
        or info.st_nlink != 1
        or type(info.st_dev) is not int
        or info.st_dev < 0
        or type(info.st_ino) is not int
        or info.st_ino <= 0
        or birth_ns <= 0
    ):
        raise RecoveryRefused(f"{what} is not one stable plain directory")
    return {
        "path": str(root.resolve(strict=True)),
        "st_dev": int(info.st_dev),
        "st_ino": int(info.st_ino),
        "birth_time_ns": birth_ns,
        "file_attributes": attributes,
        "link_count": int(info.st_nlink),
    }


def _prepare_empty_runtime_temp(path: Path, *, what: str) -> Path:
    """Create or revalidate one fixed, empty, plain project-local temp root."""

    try:
        if os.path.lexists(path):
            root = Plan._project_path(path, directory=True)
        else:
            root = Plan._project_path(path, directory=True, existing=False)
            root.mkdir(parents=False, exist_ok=False)
            fsync_directory(root.parent)
        Supervisor._require_plain_tree(root, what=what)
    except (OSError, TypeError, ValueError) as exc:
        raise RecoveryRefused(f"{what} is not a fixed plain project directory") from exc
    if any(root.iterdir()):
        raise RecoveryRefused(f"{what} must be empty before use")
    _runtime_temp_directory_identity(root, what=what)
    return root


def _verified_child_bundle(
    *, relative_path: str, logical_path: Path
) -> tuple[bytes, dict[str, Any]]:
    """Build one canonical stdin bundle from raw-authority-captured bytes."""

    gate = _validate_controller_runtime()
    raw = gate["raw_authority"]
    raw_module = sys.modules.get(RAW_AUTHORITY_MODULE_NAME)
    if type(raw_module) is not ModuleType:
        raise RecoveryRefused("raw-authority helper is unavailable for child capture")
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    if not callable(admitted_source):
        raise RecoveryRefused("raw-authority captured-source API is unavailable")
    expected_path = CONTROLLER_WORKTREE / Path(relative_path)
    if logical_path != expected_path or not relative_path.startswith(
        ("scripts/week8_exp2a_recovery_", "scripts/week8_recovery_raw_authority")
    ):
        raise RecoveryRefused("verified child path is outside the fixed allowlist")
    try:
        script_source = admitted_source(raw, "controller", relative_path)
        helper_source = admitted_source(
            raw, "controller", "scripts/week8_recovery_raw_authority.py"
        )
    except (OSError, TypeError, ValueError) as exc:
        raise RecoveryRefused("verified child source capture is unavailable") from exc
    script_sha = sha256_bytes(script_source)
    helper_sha = sha256_bytes(helper_source)
    if helper_sha != EXPECTED_RAW_AUTHORITY_HELPER_SHA256:
        raise RecoveryRefused("captured child helper differs from its fixed digest")
    payload = {
        "child_transport_schema_version": CHILD_TRANSPORT_SCHEMA_VERSION,
        "record_type": "week8_d161_verified_child_bundle",
        "logical_path": str(logical_path.resolve(strict=True)),
        "script_sha256": script_sha,
        "script_base64": base64.b64encode(script_source).decode("ascii"),
        "raw_helper_path": str(RAW_AUTHORITY_HELPER.resolve(strict=True)),
        "raw_helper_sha256": helper_sha,
        "raw_helper_base64": base64.b64encode(helper_source).decode("ascii"),
    }
    payload["record_digest"] = sha256_bytes(_canonical_ascii(payload))
    bundle = _canonical_ascii(payload)
    return bundle, {
        "child_transport_schema_version": CHILD_TRANSPORT_SCHEMA_VERSION,
        "transport": "verified_source_stdin",
        "logical_path": payload["logical_path"],
        "source_sha256": script_sha,
        "raw_helper_sha256": helper_sha,
        "bootstrap_literal_sha256": CHILD_BOOTSTRAP_LITERAL_SHA256,
        "bundle_sha256": sha256_bytes(bundle),
    }


def _validate_child_transport(
    value: object, *, logical_path: Path, what: str
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
        what=what,
    )
    if (
        row["child_transport_schema_version"] != CHILD_TRANSPORT_SCHEMA_VERSION
        or type(row["child_transport_schema_version"]) is not int
        or row["transport"] != "verified_source_stdin"
        or row["logical_path"] != str(logical_path.resolve(strict=True))
        or row["raw_helper_sha256"] != EXPECTED_RAW_AUTHORITY_HELPER_SHA256
        or row["bootstrap_literal_sha256"] != CHILD_BOOTSTRAP_LITERAL_SHA256
    ):
        raise RecoveryRefused(f"{what} policy differs")
    for name in (
        "source_sha256",
        "raw_helper_sha256",
        "bootstrap_literal_sha256",
        "bundle_sha256",
    ):
        _expect_sha(row[name], what=f"{what} {name}")
    return row


def _sanitized_subprocess_environment(
    runtime_temp: Path,
    *,
    invocation_digest: str | None = None,
    child_bundle_digest: str | None = None,
) -> dict[str, str]:
    """Build a small inherited environment with every Python path input reset."""

    inherited = {
        name: value
        for name, value in os.environ.items()
        if name.upper()
        in {
            "APPDATA",
            "COMSPEC",
            "NUMBER_OF_PROCESSORS",
            "OS",
            "PATHEXT",
            "PROCESSOR_ARCHITECTURE",
            "PROGRAMDATA",
            "SYSTEMDRIVE",
            "SYSTEMROOT",
            "USERNAME",
            "USERPROFILE",
            "WINDIR",
        }
    }
    fixed = {
        # The native parent clears profile variables. Keep injected OS-agent
        # logs out of the exact execution tree, including nested fit children.
        "LOCALAPPDATA": str(PINNED_LOCAL_APPDATA),
        "CUDA_VISIBLE_DEVICES": "-1",
        # The detached execution worktree was created by the sandbox identity,
        # while the pinned interpreter runs as the host account.  Authorize
        # only that exact path for nested historical Git queries; never mutate
        # user or global Git configuration.
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_KEY_0": "safe.directory",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_VALUE_0": str(EXECUTION_WORKTREE.resolve(strict=True)),
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "",
        "GIT_TERMINAL_PROMPT": "0",
        "HIP_VISIBLE_DEVICES": "-1",
        "OMP_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4",
        "OPENBLAS_NUM_THREADS": "4",
        "NUMEXPR_NUM_THREADS": "4",
        "PAGER": "",
        "PATH": str(PINNED_GIT.parent.resolve(strict=True)),
        "TEMP": str(runtime_temp.resolve()),
        "TMP": str(runtime_temp.resolve()),
        "TMPDIR": str(runtime_temp.resolve()),
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "PYTHONUTF8": "1",
    }
    entrypoint_gate = os.environ.get(ENTRYPOINT_GATE_ENVIRONMENT_NAME)
    if type(entrypoint_gate) is not str or not entrypoint_gate:
        raise RecoveryRefused("entrypoint gate is absent from bootstrap environment")
    fixed[ENTRYPOINT_GATE_ENVIRONMENT_NAME] = entrypoint_gate
    if invocation_digest is not None:
        _expect_sha(invocation_digest, what="bootstrap invocation digest")
        fixed["BU_D161_INVOCATION_DIGEST"] = invocation_digest
    if child_bundle_digest is not None:
        _expect_sha(child_bundle_digest, what="verified child bundle digest")
        fixed[CHILD_BUNDLE_ENVIRONMENT_NAME] = child_bundle_digest
    return {**inherited, **fixed}


def _downstream_git_environment(gate: Mapping[str, Any]) -> dict[str, str]:
    """Build the exact process-local Git environment admitted by raw authority."""

    raw = gate.get("raw_authority")
    if type(raw) is not dict:
        raise RecoveryRefused("downstream Git requires raw authority")
    git = raw.get("git")
    runtime_record = raw.get("git_runtime")
    runtime = PINNED_GIT_RUNTIME_ROOT.resolve(strict=True)
    executable = PINNED_GIT.resolve(strict=True)
    if (
        type(git) is not dict
        or git.get("path") != str(executable)
        or git.get("sha256") != EXPECTED_PINNED_GIT_SHA256
        or type(runtime_record) is not dict
        or runtime_record.get("path") != str(runtime)
        or runtime_record.get("inventory_digest")
        != EXPECTED_PINNED_GIT_RUNTIME_INVENTORY_DIGEST
        or runtime_record.get("file_count") != EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT
        or runtime_record.get("directory_count")
        != EXPECTED_PINNED_GIT_RUNTIME_DIRECTORY_COUNT
        or runtime_record.get("total_bytes")
        != EXPECTED_PINNED_GIT_RUNTIME_TOTAL_BYTES
        or runtime_record.get("stability_observations") != 2
        or runtime_record.get("retained_read_lock_count")
        != EXPECTED_PINNED_GIT_RUNTIME_FILE_COUNT
    ):
        raise RecoveryRefused("downstream Git differs from locked raw authority")
    windows_root = Path("C:/Windows").resolve(strict=True)
    system32 = (windows_root / "System32").resolve(strict=True)
    safe_root = CONTROLLER_WORKTREE.resolve(strict=True)
    entries = (
        ("safe.directory", str(safe_root)),
        ("core.fsmonitor", "false"),
        ("core.untrackedCache", "false"),
        ("core.hooksPath", os.devnull),
        ("core.attributesFile", os.devnull),
    )
    environment = {
        "BU_RUNRECORD_GIT_EXECUTABLE": str(executable),
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": str(len(entries)),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_EXEC_PATH": str(runtime),
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_TEMPLATE_DIR": os.devnull,
        "LC_ALL": "C",
        "PAGER": "",
        "PATH": os.pathsep.join((str(runtime), str(system32), str(windows_root))),
        "SYSTEMROOT": str(windows_root),
        "WINDIR": str(windows_root),
    }
    for index, (key, value) in enumerate(entries):
        environment[f"GIT_CONFIG_KEY_{index}"] = key
        environment[f"GIT_CONFIG_VALUE_{index}"] = value
    return environment


@contextmanager
def _verified_downstream_git_environment(
    gate: Mapping[str, Any],
) -> Iterator[None]:
    """Install only locked Git controls for one downstream operation."""

    desired = _downstream_git_environment(gate)
    exact_names = {
        "BU_RUNRECORD_GIT_EXECUTABLE",
        "LC_ALL",
        "PAGER",
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
    }

    def managed(name: str) -> bool:
        upper = name.upper()
        return upper.startswith("GIT_") or upper in exact_names

    previous = tuple(
        (name, value) for name, value in os.environ.items() if managed(name)
    )
    controlled = tuple(name for name, _ in previous)
    try:
        for name in controlled:
            del os.environ[name]
        os.environ.update(desired)
        observed = {
            name: value for name, value in os.environ.items() if managed(name)
        }
        if observed != desired:
            raise RecoveryRefused("process-local downstream Git environment differs")
        yield
        repeated = {
            name: value for name, value in os.environ.items() if managed(name)
        }
        if repeated != desired:
            raise RecoveryRefused("downstream operation changed its Git environment")
    finally:
        for name in tuple(os.environ):
            if managed(name):
                del os.environ[name]
        for name, value in previous:
            os.environ[name] = value


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryRefused(f"subprocess JSON repeats key {key!r}")
        result[key] = value
    return result


def _strict_json_line(stdout: str, *, what: str) -> dict[str, Any]:
    lines = stdout.splitlines()
    if len(lines) != 1 or not lines[0]:
        raise RecoveryRefused(f"{what} did not emit exactly one JSON line")
    try:
        value = json.loads(
            lines[0],
            object_pairs_hook=_no_duplicate_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RecoveryRefused(f"{what} emitted non-finite JSON")
            ),
        )
    except RecoveryRefused:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryRefused(f"{what} output is not strict JSON") from exc
    if type(value) is not dict or _canonical(value).decode("utf-8") != lines[0]:
        raise RecoveryRefused(f"{what} output is not canonical strict JSON")
    return value


def _validate_output_capture(value: object, *, what: str) -> dict[str, Any]:
    """Validate hash/count-only containment of lower stdout and stderr."""

    capture = _expect_keys(value, {"stdout", "stderr"}, what=what)
    for stream_name in ("stdout", "stderr"):
        row = _expect_keys(
            capture[stream_name],
            {"sha256", "byte_count", "write_count"},
            what=f"{what} {stream_name}",
        )
        _expect_sha(row["sha256"], what=f"{what} {stream_name} SHA256")
        for count_name in ("byte_count", "write_count"):
            _exact_nonnegative(
                row[count_name], what=f"{what} {stream_name} {count_name}"
            )
    return capture


_ACTIVE_RELOCATION: tuple[Any, ...] | None = None


def _relocation_state() -> tuple[Any, dict[str, Any]]:
    """Return this parent's admitted provenance, never a child's assertion."""
    state = _ACTIVE_RELOCATION
    if type(state) is not tuple or len(state) != 6:
        raise RecoveryRefused("parent relocation readers are not admitted")
    raw_module, raw, helpers, access, binding, _ = state
    if sys.modules.get(RAW_AUTHORITY_MODULE_NAME) is not raw_module:
        raise RecoveryRefused("parent relocation raw authority module changed")
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
        raise RecoveryRefused("parent relocation helper or evidence binding changed")
    return access, observed


def _parent_readers() -> dict[str, Any]:
    _relocation_state()
    state = _ACTIVE_RELOCATION
    if state is None:
        raise RecoveryRefused("parent relocation scope disappeared")
    readers = state[5]
    if type(readers) is not dict or set(readers) != {"sources", "preflight", "checkpoints", "completed", "events", "controls", "released"}:
        raise RecoveryRefused("parent admitted reader inventory differs")
    for reader in readers.values():
        reader._assert_installed()
    return dict(readers)


def validate_relocated_finalization_inventory(
    verified: object,
    ledger: Mapping[str, Any],
    *,
    checkpoint_path: Path,
    checkpoint_sha256: str,
    ledger_sha256: str,
    expected_execution_commit: str,
) -> None:
    """Independently bind downstream current rows to this parent's provenance.

    A released inventory's origin assertions cannot authorize themselves. Reopen
    the exact checkpoint and all pairs through the parent's captured readers;
    the finalizer still performs its original independent per-pair validation.
    """
    readers = _parent_readers()
    if (
        expected_execution_commit != EXECUTION_COMMIT
        or ledger_sha256 != readers["sources"].ledger_sha256
    ):
        raise RecoveryRefused("finalization execution or historical ledger pin differs")
    document = _expect_keys(
        verified,
        {"start", "ledger", "roots", "sources", "pending_new_fit_ids", "relocation", "source_provenance"},
        what="relocated finalization inventory",
    )
    start = document["start"]
    if (
        type(start) is not dict
        or type(start.get("exp2a_repair_start_schema_version")) is not int
        or start["exp2a_repair_start_schema_version"] != 2
        or _canonical(start.get("relocation")) != _canonical(readers["checkpoints"].relocation_binding())
        or _canonical(document["relocation"]) != _canonical(start["relocation"])
        or _canonical(document["ledger"]) != _canonical(ledger)
    ):
        raise RecoveryRefused("finalization inventory differs from admitted relocation or ledger")
    fresh = readers["released"].load_inventory(
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
        expected_execution_commit=expected_execution_commit,
    )
    roots = document["roots"]
    if (
        type(roots) is not dict or set(roots) != set(fresh["roots"])
        or any(type(roots[key]) is not type(path) or roots[key] != path
               for key, path in fresh["roots"].items())
        or _canonical({k:v for k,v in document.items() if k != "roots"})
        != _canonical({k:v for k,v in fresh.items() if k != "roots"})
    ):
        raise RecoveryRefused("finalization inventory differs from independently reopened provenance")
    _parent_readers()


@contextmanager
def _parent_orphan_history() -> Iterator[None]:
    original = Launch._historical_lease_record
    if not callable(original):
        raise RecoveryRefused("parent historical lease lookup is unavailable")
    def exact_lookup(token: str) -> dict[str, Any]:
        if token == OLD_LEASE_TOKEN:
            return historical_orphan_lease_record(token)
        return original(token)
    Launch._historical_lease_record = exact_lookup
    try:
        yield
    finally:
        changed = Launch._historical_lease_record is not exact_lookup
        Launch._historical_lease_record = original
        if changed or Launch._historical_lease_record is not original:
            raise RecoveryRefused("parent historical lease lookup changed or failed restoration")


@contextmanager
def _parent_relocation(gate: Mapping[str, Any]) -> Iterator[None]:
    """Install captured metadata readers only after native runtime admission."""
    global _ACTIVE_RELOCATION
    if _ACTIVE_RELOCATION is not None:
        raise RecoveryRefused("parent relocation scope is already active")
    raw_module = sys.modules.get(RAW_AUTHORITY_MODULE_NAME)
    if type(raw_module) is not ModuleType or type(gate.get("raw_authority")) is not dict:
        raise RecoveryRefused("parent relocation raw authority is unavailable")
    raw = gate["raw_authority"]
    helpers = raw_module.load_verified_relocation_helpers(raw)
    helper_binding = helpers.validate(raw)
    metadata = helpers.modules["metadata"]
    access = metadata.load_registered_access(helpers.modules["provenance"])
    from . import prefit_storage as Storage

    sources = metadata.SourceReaders(access, Plan, Launch.S)
    preflight = metadata.PreflightReaders(access, sources, Launch, Storage)
    checkpoints = metadata.CheckpointReaders(access, preflight)
    completed = metadata.CompletedJobReaders(access, checkpoints)
    events = metadata.EventReaders(access, checkpoints)
    controls = metadata.ControlReaders(access, P, events)
    released = metadata.ReleasedInventoryReader(access, completed)
    binding = {
        "relocation_schema_version": 1,
        "attestation_sha256": access.attestation_sha256,
        "policy_sha256": metadata.POLICY_SHA256,
        "pair_count": metadata.EXPECTED_PAIR_COUNT,
        "document_count": metadata.EXPECTED_DOCUMENT_COUNT,
        "helpers": helper_binding,
    }
    with _parent_orphan_history(), sources.installed(), preflight.installed(), checkpoints.installed(), completed.installed(), events.installed(), controls.installed(), released.installed():
        readers = {"sources": sources, "preflight": preflight, "checkpoints": checkpoints,
                   "completed": completed, "events": events, "controls": controls, "released": released}
        _ACTIVE_RELOCATION = (raw_module, raw, helpers, access, binding, readers)
        try:
            _relocation_state()
            yield
        finally:
            try:
                _relocation_state()
            finally:
                _ACTIVE_RELOCATION = None
    if helpers.validate(raw) != helper_binding:
        raise RecoveryRefused("parent relocation helpers changed after restoration")


def _validate_inspector_material(value: object) -> dict[str, Any]:
    document = _expect_keys(
        value,
        {
            "inspector_schema_version",
            "status",
            "execution_commit",
            "relocation",
            "control",
            "events",
            "jobs",
            "staging",
            "lower_report_count",
            "production_launch_receipt_present",
            "loaded_bu_modules",
            "scientific_files_opened",
            "scientific_outcomes_consulted",
            "scientific_values_emitted",
            "production_mutation_performed",
            "inspector_digest",
        },
        what="old-source inspector result",
    )
    digest = _expect_sha(
        document["inspector_digest"], what="old-source inspector digest"
    )
    payload = {
        key: item for key, item in document.items() if key != "inspector_digest"
    }
    if digest != sha256_bytes(_canonical(payload)):
        raise RecoveryRefused("old-source inspector content digest differs")
    _, relocation = _relocation_state()
    if _canonical(document["relocation"]) != _canonical(relocation):
        raise RecoveryRefused("parent/old-source relocation admission differs")
    if (
        document["inspector_schema_version"] != 2
        or document["status"] != "complete"
        or document["execution_commit"] != EXECUTION_COMMIT
        or document["lower_report_count"] != 0
        or document["production_launch_receipt_present"] is not False
        or document["scientific_files_opened"] is not True
        or document["scientific_outcomes_consulted"] is not False
        or document["scientific_values_emitted"] is not False
        or document["production_mutation_performed"] is not False
    ):
        raise RecoveryRefused("old-source inspector policy/identity differs")
    control = _expect_keys(
        document["control"],
        {"hashes", "plan_digest", "checkpoint", "active_lease"},
        what="old-source inspector control",
    )
    checkpoint = _expect_keys(
        control["checkpoint"],
        {
            "token",
            "file_sha256",
            "checkpoint_digest",
            "execution_context_digest",
            "lease_sha256",
        },
        what="old-source inspector checkpoint",
    )
    active_lease = _expect_keys(
        control["active_lease"],
        {"token", "pid", "sha256"},
        what="old-source inspector active lease",
    )
    events = _expect_keys(
        document["events"],
        {
            "count",
            "chain_digest",
            "tail_file_sha256",
            "kind_counts",
            "started_job_ids",
            "synced_job_ids",
        },
        what="old-source inspector events",
    )
    jobs = _expect_keys(
        document["jobs"],
        {
            "roster_count",
            "local_completed",
            "durable_completed",
            "untouched_job_ids",
            "orphan_job_id",
            "orphan_child_pid",
            "hidden_partial",
        },
        what="old-source inspector jobs",
    )
    partial = _expect_keys(
        jobs["hidden_partial"],
        {
            "name",
            "file_count",
            "orphan_local_file_count",
            "inventory_digest",
        },
        what="old-source inspector hidden partial",
    )
    staging = _expect_keys(
        document["staging"],
        {"staging_count", "quarantine_count"},
        what="old-source inspector staging",
    )
    local_rows = jobs["local_completed"]
    durable_rows = jobs["durable_completed"]
    untouched = jobs["untouched_job_ids"]
    if (
        control["hashes"] != EXPECTED_HASHES
        or control["plan_digest"] != EXPECTED_PLAN_DIGEST
        or checkpoint["token"] != OLD_LEASE_TOKEN
        or checkpoint["file_sha256"]
        != EXPECTED_HASHES["old_checkpoint"]
        or checkpoint["checkpoint_digest"]
        != EXPECTED_OLD_CHECKPOINT_DIGEST
        or _HEX64.fullmatch(str(checkpoint["execution_context_digest"])) is None
        or checkpoint["lease_sha256"] != EXPECTED_HASHES["old_lease"]
        or active_lease
        != {
            "token": OLD_LEASE_TOKEN,
            "pid": OLD_LEASE_PID,
            "sha256": EXPECTED_HASHES["old_lease"],
        }
        or events["count"] != EXPECTED_INITIAL_COUNTS["events"]
        or events["chain_digest"] != EXPECTED_HASHES["old_event_stream"]
        or events["tail_file_sha256"]
        != EXPECTED_HASHES["old_event_tail_file"]
        or events["kind_counts"] != {"attempt_started": 150, "job_synced": 149}
        or type(events["started_job_ids"]) is not list
        or len(events["started_job_ids"]) != 150
        or not all(type(item) is str for item in events["started_job_ids"])
        or len(set(events["started_job_ids"])) != 150
        or type(events["synced_job_ids"]) is not list
        or len(events["synced_job_ids"]) != 149
        or not all(type(item) is str for item in events["synced_job_ids"])
        or len(set(events["synced_job_ids"])) != 149
        or jobs["roster_count"] != 261
        or type(local_rows) is not list
        or len(local_rows)
        != EXPECTED_INITIAL_COUNTS["local_completed"]
        or type(durable_rows) is not list
        or len(durable_rows)
        != EXPECTED_INITIAL_COUNTS["durable_completed"]
        or type(untouched) is not list
        or len(untouched) != EXPECTED_INITIAL_COUNTS["untouched"]
        or not all(type(item) is str for item in untouched)
        or len(set(untouched)) != EXPECTED_INITIAL_COUNTS["untouched"]
        or jobs["orphan_job_id"] != ORPHAN_JOB_ID
        or jobs["orphan_child_pid"] != ORPHAN_CHILD_PID
        or partial["name"] != HIDDEN_PARTIAL_NAME
        or partial["file_count"] != EXPECTED_INITIAL_COUNTS["partial_files"]
        or partial["orphan_local_file_count"]
        != EXPECTED_INITIAL_COUNTS["orphan_local_files"]
        or _HEX64.fullmatch(str(partial["inventory_digest"])) is None
        or staging != {"staging_count": 0, "quarantine_count": 0}
    ):
        raise RecoveryRefused("old-source inspector accounting differs from D-161")
    seen_local: set[str] = set()
    for row in local_rows:
        row = _expect_keys(
            row,
            {
                "job_id",
                "tree_digest",
                "execution_digest",
                "attempt_receipt_sha256",
                "child_pid",
            },
            what="old-source inspector local row",
        )
        if (
            type(row["job_id"]) is not str
            or not row["job_id"]
            or row["job_id"] in seen_local
            or any(
                _HEX64.fullmatch(str(row[name])) is None
                for name in (
                    "tree_digest",
                    "execution_digest",
                    "attempt_receipt_sha256",
                )
            )
            or type(row["child_pid"]) is not int
            or row["child_pid"] <= 0
        ):
            raise RecoveryRefused("old-source inspector local row is malformed")
        seen_local.add(row["job_id"])
    seen_durable: set[str] = set()
    for row in durable_rows:
        row = _expect_keys(
            row,
            {
                "job_id",
                "tree_digest",
                "execution_digest",
                "copy_evidence_digest",
                "historical_copy_evidence_digest",
                "relocation_pair_key",
            },
            what="old-source inspector durable row",
        )
        if (
            type(row["job_id"]) is not str
            or not row["job_id"]
            or row["job_id"] in seen_durable
            or type(row["relocation_pair_key"]) is not str
            or not row["relocation_pair_key"]
            or any(
                _HEX64.fullmatch(str(row[name])) is None
                for name in (
                    "tree_digest",
                    "execution_digest",
                    "copy_evidence_digest",
                    "historical_copy_evidence_digest",
                )
            )
        ):
            raise RecoveryRefused("old-source inspector durable row is malformed")
        seen_durable.add(row["job_id"])
    if (
        set(events["started_job_ids"]) != seen_local
        or set(events["synced_job_ids"]) != seen_durable
        or set(events["started_job_ids"]) - set(events["synced_job_ids"])
        != {ORPHAN_JOB_ID}
    ):
        raise RecoveryRefused("old-source inspector roster bindings differ")
    modules = document["loaded_bu_modules"]
    if type(modules) is not list or not modules:
        raise RecoveryRefused("old-source inspector module inventory is empty")
    module_ids: set[str] = set()
    for row in modules:
        if (
            type(row) is not dict
            or set(row) != {"module_id", "source_sha256"}
            or type(row["module_id"]) is not str
            or not (
                row["module_id"] == "bu"
                or row["module_id"].startswith("bu.")
            )
            or row["module_id"] in module_ids
            or _HEX64.fullmatch(str(row["source_sha256"])) is None
        ):
            raise RecoveryRefused("old-source inspector module inventory is malformed")
        module_ids.add(row["module_id"])
    if "bu" not in module_ids:
        raise RecoveryRefused("old-source inspector omitted the bu package root")
    return document


def _run_old_source_inspector() -> dict[str, Any]:
    runtime = _prepare_empty_runtime_temp(
        INSPECTOR_RUNTIME_TEMP, what="D-161 inspector runtime temp"
    )
    bundle, transport = _verified_child_bundle(
        relative_path="scripts/week8_exp2a_recovery_inspector.py",
        logical_path=INSPECTOR_SCRIPT,
    )
    environment = _sanitized_subprocess_environment(
        runtime, child_bundle_digest=transport["bundle_sha256"]
    )
    try:
        completed = subprocess.run(
            [
                str(PINNED_PYTHON),
                "-I",
                "-S",
                "-B",
                "-X",
                "utf8",
                "-c",
                CHILD_BOOTSTRAP_LITERAL,
            ],
            cwd=EXECUTION_WORKTREE,
            env=environment,
            check=False,
            input=bundle,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
    except OSError as exc:
        raise RecoveryRefused("could not start fixed old-source inspector") from exc
    try:
        stdout = completed.stdout.decode("utf-8", errors="strict")
        stderr = completed.stderr.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RecoveryRefused("old-source inspector emitted non-UTF-8 bytes") from exc
    if completed.returncode != 0 or stderr:
        raise _InspectorProcessRefused(
            completed.stdout, completed.stderr, completed.returncode
        )
    result = _validate_inspector_material(
        _strict_json_line(stdout, what="old-source inspector")
    )
    if any(runtime.iterdir()):
        raise RecoveryRefused("old-source inspector left runtime temp evidence")
    return result


def _plain_tree_inventory(root: Path, *, what: str) -> list[dict[str, Any]]:
    if not os.path.lexists(root):
        raise RecoveryRefused(f"{what} is missing: {root}")
    try:
        Supervisor._require_plain_tree(root, what=what)
    except (OSError, ValueError) as exc:
        raise RecoveryRefused(str(exc)) from exc
    rows: list[dict[str, Any]] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(directory_names):
            child = current_path / name
            rows.append(
                {
                    "kind": "directory",
                    "path": child.relative_to(root).as_posix(),
                }
            )
        for name in sorted(file_names):
            child = current_path / name
            info = child.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise RecoveryRefused(f"{what} has unsupported entry {child}")
            rows.append(
                {
                    "kind": "file",
                    "path": child.relative_to(root).as_posix(),
                    "size": info.st_size,
                    "sha256": sha256_file(child),
                }
            )
    return sorted(rows, key=lambda row: (row["path"], row["kind"]))


def _tree_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(_canonical(list(rows)))


def _file_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if row.get("kind") == "file"]


def _directory_entries(path: Path, *, what: str) -> list[Path]:
    if not os.path.lexists(path):
        return []
    try:
        directory = Plan._project_path(path, directory=True)
    except ValueError as exc:
        raise RecoveryRefused(str(exc)) from exc
    return sorted(directory.iterdir(), key=lambda item: item.name)


def _plain_regular_file(path: Path, *, what: str) -> Path:
    try:
        return Plan._project_path(path, directory=False)
    except (OSError, ValueError) as exc:
        raise RecoveryRefused(f"{what} is not a plain project-local file") from exc


def _plain_future_file(path: Path, *, what: str) -> Path:
    if os.path.lexists(path):
        raise RecoveryRefused(f"{what} already exists")
    try:
        parent = Plan._project_path(path.parent, directory=True)
        candidate = Plan._project_path(path, directory=False, existing=False)
    except (OSError, ValueError) as exc:
        raise RecoveryRefused(f"{what} path is not plain/project-local") from exc
    if candidate.parent != parent:
        raise RecoveryRefused(f"{what} parent changed during validation")
    return candidate


def _validate_empty_attempt_staging() -> dict[str, Any]:
    root = Plan._project_path(P.STAGING_ROOT, directory=True)
    allowed = {"staging", "quarantine"}
    top = _directory_entries(root, what="attempt staging root")
    if any(path.name not in allowed for path in top):
        raise RecoveryRefused("attempt staging root contains an unknown entry")
    result: dict[str, Any] = {}
    for name in sorted(allowed):
        path = root / name
        entries = _directory_entries(path, what=f"attempt {name}")
        if entries:
            raise RecoveryRefused(f"attempt {name} contains preserved evidence")
        result[name] = {"present": path.is_dir(), "entry_count": 0}
    return result


def _event_chain_digest(events: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(_canonical([event["event_digest"] for event in events]))


def _validate_initial_controls() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    P._validate_fixed_layout()
    if P.WORKSPACE_ROOT.resolve() != WORKSPACE_ROOT.resolve():
        raise RecoveryRefused("production workspace is not the fixed D-161 workspace")
    phase_hashes = {
        "prepare": "prepare_receipt",
        "preflight": "preflight_receipt",
        "launch-control": "launch_control_receipt",
    }
    receipts: dict[str, Any] = {}
    for phase, expected_name in phase_hashes.items():
        receipt = P._load_receipt(phase)
        if receipt["_file_sha256"] != EXPECTED_HASHES[expected_name]:
            raise RecoveryRefused(f"{phase} receipt hash differs from D-161")
        receipts[phase] = receipt
    if P._receipt_present("launch"):
        raise RecoveryRefused("production launch receipt already exists before recovery")
    control = P._load_control(EXECUTION_COMMIT, monitor_only=True)
    if control["_file_sha256"] != EXPECTED_HASHES["launch_control_receipt"]:
        raise RecoveryRefused("launch control changed after D-161")

    fixed_files = {
        "plan_file": (
            P.PREPARATION_ORIGINAL_ROOT / Plan.PLAN_FILE,
            P.PREPARATION_COPY_ROOT / Plan.PLAN_FILE,
        ),
        "source_ledger_file": (
            P.PREPARATION_ORIGINAL_ROOT / P.Sources.SOURCE_LEDGER_FILE,
            P.PREPARATION_COPY_ROOT / P.Sources.SOURCE_LEDGER_FILE,
        ),
        "preflight_report": (
            P.PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE,
            P.SYNC_ROOT / Launch.PREFLIGHT_FILE,
        ),
    }
    pins: dict[str, Any] = {}
    for name, (left, right) in fixed_files.items():
        digest = _same_bytes(left, right, what=name)
        if digest != EXPECTED_HASHES[name]:
            raise RecoveryRefused(f"{name} hash differs from D-161")
        pins[name] = {
            "original": str(left.resolve()),
            "copy": str(right.resolve()),
            "sha256": digest,
        }
    plan = read_json(fixed_files["plan_file"][0])
    Plan.validate_exp2a_repair_plan(plan)
    if plan.get("plan_digest") != EXPECTED_PLAN_DIGEST:
        raise RecoveryRefused("registered E2A plan digest differs from D-161")

    checkpoint, checkpoint_sha = P._checkpoint_material(control)
    if checkpoint is None or checkpoint_sha != EXPECTED_HASHES["old_checkpoint"]:
        raise RecoveryRefused("the exact epoch-001 checkpoint is unavailable")
    if (
        checkpoint["lease"]["token"] != OLD_LEASE_TOKEN
        or checkpoint["lease"]["sha256"] != EXPECTED_HASHES["old_lease"]
        or checkpoint["checkpoint_digest"] != EXPECTED_OLD_CHECKPOINT_DIGEST
        or checkpoint["environment"].get("git_commit") != EXECUTION_COMMIT
    ):
        raise RecoveryRefused("epoch-001 checkpoint identity differs from D-161")

    events, failures = P._events_material(control, checkpoint)
    if failures or any(
        event["kind"] in {"attempt_failed", "sync_pending", "complete"}
        for event in events
    ):
        raise RecoveryRefused("epoch-001 event stream contains terminal/failure evidence")
    if len(events) != EXPECTED_INITIAL_COUNTS["events"]:
        raise RecoveryRefused("epoch-001 event count differs from 299")
    if _event_chain_digest(events) != EXPECTED_HASHES["old_event_stream"]:
        raise RecoveryRefused("epoch-001 event-chain digest differs from D-161")
    tail_path = P.OUTPUT_ROOT / Launch.EVENT_DIRECTORY / "000298.json"
    if sha256_file(tail_path) != EXPECTED_HASHES["old_event_tail_file"]:
        raise RecoveryRefused("epoch-001 tail event file changed")

    report_dirs = (
        P.OUTPUT_ROOT / Launch.REPORT_DIRECTORY,
        P.SYNC_ROOT / Launch.REPORT_DIRECTORY,
    )
    if any(_directory_entries(path, what="lower report directory") for path in report_dirs):
        raise RecoveryRefused("epoch-001 unexpectedly has a lower terminal report")
    return {"receipts": receipts, "pins": pins}, checkpoint, events


def _validate_attempt_receipt(job_id: str, local: Path) -> dict[str, Any]:
    attempt = _expect_keys(
        read_json(local / Supervisor.ATTEMPT_FILE),
        {
            "schema_version",
            "job_id",
            "attempt_token",
            "parent_pid",
            "started_at",
            "timeout_seconds",
        },
        what="epoch-001 attempt record",
    )
    receipt = read_json(local / Supervisor.RECEIPT_FILE)
    required = {
        "schema_version",
        "job_id",
        "attempt_token",
        "status",
        "parent_pid",
        "child_pid",
        "started_at",
        "finished_at",
        "elapsed_seconds",
        "timeout_seconds",
        "exit_code",
        "error_type",
        "error",
        "result_digest",
        "job_tree_digest",
        "published",
    }
    receipt = _expect_keys(receipt, required, what="epoch-001 attempt receipt")
    if (
        attempt["schema_version"] != Supervisor.SUPERVISOR_SCHEMA_VERSION
        or receipt["schema_version"] != Supervisor.SUPERVISOR_SCHEMA_VERSION
        or attempt["job_id"] != job_id
        or receipt["job_id"] != job_id
        or type(attempt["attempt_token"]) is not str
        or _HEX32.fullmatch(attempt["attempt_token"]) is None
        or receipt["attempt_token"] != attempt["attempt_token"]
        or attempt["parent_pid"] != OLD_LEASE_PID
        or receipt["parent_pid"] != OLD_LEASE_PID
        or receipt["status"] != "success"
        or receipt["exit_code"] != 0
        or receipt["error_type"] is not None
        or receipt["error"] is not None
        or receipt["published"] is not True
        or type(receipt["child_pid"]) is not int
        or receipt["child_pid"] <= 0
    ):
        raise RecoveryRefused(f"completed epoch-001 attempt is not exact: {job_id}")
    result = read_json(local / Supervisor.RESULT_FILE)
    result_digest = sha256_bytes(Supervisor._canonical_json_bytes(result))
    payload_digest = Supervisor._job_tree_digest(local)
    if (
        receipt["result_digest"] != result_digest
        or receipt["job_tree_digest"] != payload_digest
    ):
        raise RecoveryRefused(f"attempt receipt payload digest differs: {job_id}")
    return receipt


def _validate_completed_local(
    job_id: str, *, inspector_row: Mapping[str, Any]
) -> dict[str, Any]:
    local = P.OUTPUT_ROOT / "jobs" / job_id
    rows = _plain_tree_inventory(local, what=f"local completed tree {job_id}")
    digest = B._job_tree_digest(local)
    if (
        inspector_row.get("job_id") != job_id
        or inspector_row.get("tree_digest") != digest
        or _HEX64.fullmatch(str(inspector_row.get("execution_digest"))) is None
    ):
        raise RecoveryRefused(f"local tree digest changed for {job_id}")
    receipt = _validate_attempt_receipt(job_id, local)
    row = {
        "job_id": job_id,
        "tree_digest": digest,
        "tree_inventory_digest": _tree_digest(rows),
        "execution_digest": inspector_row["execution_digest"],
        "attempt_receipt_sha256": sha256_file(local / Supervisor.RECEIPT_FILE),
        "child_pid": receipt["child_pid"],
    }
    if any(row[key] != inspector_row.get(key) for key in (
        "job_id",
        "tree_digest",
        "execution_digest",
        "attempt_receipt_sha256",
        "child_pid",
    )):
        raise RecoveryRefused(f"parent/old-source local accounting differs for {job_id}")
    return row


def _control_tree_inventories() -> dict[str, Any]:
    roots = {
        "preparation_original": P.PREPARATION_ORIGINAL_ROOT,
        "preparation_copy": P.PREPARATION_COPY_ROOT,
        "preflight": P.PREFLIGHT_ROOT,
        "checkpoint_original": P.OUTPUT_ROOT / Plan.START_DIRECTORY,
        "checkpoint_copy": P.SYNC_ROOT / Plan.START_DIRECTORY,
        "events_original": P.OUTPUT_ROOT / Launch.EVENT_DIRECTORY,
        "events_copy": P.SYNC_ROOT / Launch.EVENT_DIRECTORY,
        "reports_original": P.OUTPUT_ROOT / Launch.REPORT_DIRECTORY,
        "reports_copy": P.SYNC_ROOT / Launch.REPORT_DIRECTORY,
    }
    result: dict[str, Any] = {}
    for name, path in roots.items():
        if not os.path.lexists(path):
            if name.startswith("reports_"):
                result[name] = {"present": False, "inventory_digest": None}
                continue
            raise RecoveryRefused(f"required control tree is missing: {name}")
        rows = _plain_tree_inventory(path, what=f"D-161 control tree {name}")
        result[name] = {
            "present": True,
            "entry_count": len(rows),
            "inventory_digest": _tree_digest(rows),
        }
    return result


def _validate_partial_subset(local: Path, partial: Path) -> dict[str, Any]:
    local_rows = _plain_tree_inventory(local, what="orphan local tree")
    partial_rows = _plain_tree_inventory(partial, what="orphan hidden partial")
    local_files = {row["path"]: row for row in _file_rows(local_rows)}
    partial_files = _file_rows(partial_rows)
    if len(local_files) != EXPECTED_INITIAL_COUNTS["orphan_local_files"]:
        raise RecoveryRefused("orphan local tree file count differs from D-161")
    if len(partial_files) != EXPECTED_INITIAL_COUNTS["partial_files"]:
        raise RecoveryRefused("orphan partial file count differs from D-161")
    for row in partial_files:
        expected = local_files.get(row["path"])
        if expected != row:
            raise RecoveryRefused(
                "orphan destination partial is not an exact byte-identical subset"
            )
    return {
        "name": HIDDEN_PARTIAL_NAME,
        "entry_count": len(partial_rows),
        "file_count": len(partial_files),
        "inventory": partial_rows,
        "inventory_digest": _tree_digest(partial_rows),
    }


def _validate_lease(active: Path) -> dict[str, Any]:
    if sha256_file(active) != EXPECTED_HASHES["old_lease"]:
        raise RecoveryRefused("active epoch-001 lease bytes changed")
    lease = _expect_keys(
        read_json(active),
        {
            "schema_version",
            "lease_name",
            "pid",
            "token",
            "timestamp",
            "timestamp_utc",
        },
        what="active epoch-001 lease",
    )
    if (
        lease["schema_version"] != Supervisor.SUPERVISOR_SCHEMA_VERSION
        or lease["lease_name"] != Plan.COMMON_LEASE_NAME
        or lease["pid"] != OLD_LEASE_PID
        or lease["token"] != OLD_LEASE_TOKEN
    ):
        raise RecoveryRefused("active lease identity differs from D-161")
    return {
        "path": str(active.resolve()),
        "sha256": EXPECTED_HASHES["old_lease"],
        "pid": OLD_LEASE_PID,
        "token": OLD_LEASE_TOKEN,
        "timestamp": lease["timestamp"],
        "timestamp_utc": lease["timestamp_utc"],
    }


def _validate_preserved_durable_pair(
    job_id: str, event: Mapping[str, Any], inspected: Mapping[str, Any],
    local: Path, durable: Path, access: Any,
) -> dict[str, Any]:
    observation = access.historical_pair_at(local, durable)
    local_inventory = _plain_tree_inventory(local, what=f"durable source tree {job_id}")
    durable_inventory = _plain_tree_inventory(durable, what=f"durable copy tree {job_id}")
    local_digest = B._job_tree_digest(local)
    durable_digest = B._job_tree_digest(durable)
    if local_digest != durable_digest or local_inventory != durable_inventory:
        raise RecoveryRefused(f"local/durable tree digest differs for {job_id}")
    copy_digest = B._copy_evidence_digest(local, durable)
    operational = {
        "execution_digest": inspected.get("execution_digest"),
        "source_tree_digest": inspected.get("tree_digest"),
        "copy_evidence_digest": observation.historical_copy_digest,
    }
    if (
        event["data"] != operational
        or inspected.get("tree_digest") != local_digest
        or local_digest != observation.policy.content_digest
        or copy_digest != inspected.get("copy_evidence_digest")
        or copy_digest != observation.observed_copy_digest
        or inspected.get("historical_copy_evidence_digest") != observation.historical_copy_digest
        or inspected.get("relocation_pair_key") != observation.policy.key
    ):
        raise RecoveryRefused(f"copy evidence digest differs for {job_id}")
    if access.historical_pair_at(local, durable) != observation:
        raise RecoveryRefused(f"relocation pair changed during parent rehash: {job_id}")
    return {
        "job_id": job_id,
        "tree_digest": local_digest,
        "tree_inventory_digest": _tree_digest(local_inventory),
        "execution_digest": inspected["execution_digest"],
        "copy_evidence_digest": copy_digest,
        "historical_copy_evidence_digest": observation.historical_copy_digest,
        "relocation_pair_key": observation.policy.key,
    }


def _capture_outcome_blind_inventory(
    inspection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _assert_no_old_normal_release()
    if inspection is None:
        inspection = _run_old_source_inspector()
    inspection = _validate_inspector_material(dict(inspection))
    access, relocation = _relocation_state()
    inspector_local = {
        row["job_id"]: row for row in inspection["jobs"]["local_completed"]
    }
    inspector_durable = {
        row["job_id"]: row for row in inspection["jobs"]["durable_completed"]
    }
    if (
        len(inspector_local) != EXPECTED_INITIAL_COUNTS["local_completed"]
        or len(inspector_durable) != EXPECTED_INITIAL_COUNTS["durable_completed"]
    ):
        raise RecoveryRefused("old-source inspector repeats a completed job identity")
    controls, checkpoint, events = _validate_initial_controls()
    jobs = Plan.new_exp2a_jobs()
    job_ids = [job.job_id for job in jobs]
    if len(job_ids) != 261 or len(set(job_ids)) != 261:
        raise RecoveryRefused("registered E2A roster is not 261 unique jobs")

    started = [event["job_id"] for event in events if event["kind"] == "attempt_started"]
    synced_events = {
        event["job_id"]: event for event in events if event["kind"] == "job_synced"
    }
    if (
        len(started) != EXPECTED_INITIAL_COUNTS["started"]
        or len(set(started)) != len(started)
        or len(synced_events) != EXPECTED_INITIAL_COUNTS["synced"]
        or set(started) - set(synced_events) != {ORPHAN_JOB_ID}
    ):
        raise RecoveryRefused("epoch-001 start/sync accounting differs from D-161")
    parent_event_accounting = {
        "count": len(events),
        "chain_digest": _event_chain_digest(events),
        "tail_file_sha256": EXPECTED_HASHES["old_event_tail_file"],
        "kind_counts": dict(
            sorted(Counter(event["kind"] for event in events).items())
        ),
        "started_job_ids": sorted(started),
        "synced_job_ids": sorted(synced_events),
    }
    if _canonical(parent_event_accounting) != _canonical(inspection["events"]):
        raise RecoveryRefused("parent/old-source event accounting differs")
    inspected_checkpoint = inspection["control"]["checkpoint"]
    if (
        inspected_checkpoint["execution_context_digest"]
        != checkpoint["execution_context_digest"]
        or inspected_checkpoint["lease_sha256"]
        != checkpoint["lease"]["sha256"]
    ):
        raise RecoveryRefused("parent/old-source checkpoint accounting differs")

    local_jobs_root = Plan._project_path(P.OUTPUT_ROOT / "jobs", directory=True)
    durable_jobs_root = Plan._project_path(P.SYNC_ROOT / "jobs", directory=True)
    local_entries = _directory_entries(local_jobs_root, what="local jobs")
    durable_entries = _directory_entries(durable_jobs_root, what="durable jobs")
    local_names = {path.name for path in local_entries if not path.name.startswith(".")}
    durable_names = {path.name for path in durable_entries if not path.name.startswith(".")}
    hidden = [path for path in durable_entries if path.name.startswith(".")]
    if local_names != set(started) or any(path.name.startswith(".") for path in local_entries):
        raise RecoveryRefused("local jobs do not exactly equal the 150 started fits")
    if durable_names != set(synced_events):
        raise RecoveryRefused("durable jobs do not exactly equal the 149 sync events")
    if [path.name for path in hidden] != [HIDDEN_PARTIAL_NAME]:
        raise RecoveryRefused("durable jobs contain unknown hidden/partial evidence")

    local_rows: list[dict[str, Any]] = []
    for job_id in sorted(started):
        local_rows.append(
            _validate_completed_local(
                job_id,
                inspector_row=inspector_local.get(job_id, {}),
            )
        )
    orphan_row = next(row for row in local_rows if row["job_id"] == ORPHAN_JOB_ID)
    if orphan_row["child_pid"] != ORPHAN_CHILD_PID:
        raise RecoveryRefused("orphan successful receipt names a different child PID")

    durable_rows: list[dict[str, Any]] = []
    for job_id, event in sorted(synced_events.items()):
        inspected = inspector_durable.get(job_id)
        if type(inspected) is not dict:
            raise RecoveryRefused(f"old-source durable row is missing for {job_id}")
        local = local_jobs_root / job_id
        durable = durable_jobs_root / job_id
        durable_rows.append(
            _validate_preserved_durable_pair(job_id, event, inspected, local, durable, access)
        )

    untouched = sorted(set(job_ids) - set(started))
    if len(untouched) != EXPECTED_INITIAL_COUNTS["untouched"]:
        raise RecoveryRefused("untouched E2A job count differs from 111")
    for job_id in untouched:
        if any(
            os.path.lexists(root / "jobs" / job_id)
            for root in (P.OUTPUT_ROOT, P.SYNC_ROOT)
        ):
            raise RecoveryRefused(f"untouched job already has canonical evidence: {job_id}")

    staging = _validate_empty_attempt_staging()
    control_trees = _control_tree_inventories()
    partial = _validate_partial_subset(
        local_jobs_root / ORPHAN_JOB_ID,
        durable_jobs_root / HIDDEN_PARTIAL_NAME,
    )
    inspected_partial = inspection["jobs"]["hidden_partial"]
    if (
        inspected_partial.get("name") != partial["name"]
        or inspected_partial.get("file_count") != partial["file_count"]
        or inspected_partial.get("orphan_local_file_count")
        != EXPECTED_INITIAL_COUNTS["orphan_local_files"]
        or inspected_partial.get("inventory_digest")
        != partial["inventory_digest"]
    ):
        raise RecoveryRefused("parent/old-source hidden-partial accounting differs")
    active = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / f"{Plan.COMMON_LEASE_NAME}.lease.json"
    )
    lease = _validate_lease(active)
    if inspection["control"]["active_lease"] != {
        "token": lease["token"],
        "pid": lease["pid"],
        "sha256": lease["sha256"],
    }:
        raise RecoveryRefused("parent/old-source active-lease accounting differs")
    archive = _orphan_archive_path()
    if os.path.lexists(archive):
        raise RecoveryRefused("orphan lease archive exists before transition")

    inventory = {
        "inventory_schema_version": 2,
        "execution_commit": EXECUTION_COMMIT,
        "relocation": relocation,
        "control": {
            "hashes": dict(EXPECTED_HASHES),
            "plan_digest": EXPECTED_PLAN_DIGEST,
            "old_checkpoint_digest": EXPECTED_OLD_CHECKPOINT_DIGEST,
            "pins": controls["pins"],
            "tree_inventories": control_trees,
            "old_source_inspector": {
                "inspector_digest": inspection["inspector_digest"],
                "scientific_files_opened": True,
                "scientific_outcomes_consulted": False,
                "scientific_values_emitted": False,
            },
        },
        "lease": lease,
        "checkpoint": {
            "token": OLD_LEASE_TOKEN,
            "sha256": EXPECTED_HASHES["old_checkpoint"],
            "checkpoint_digest": checkpoint["checkpoint_digest"],
            "execution_context_digest": checkpoint["execution_context_digest"],
        },
        "events": {
            "count": len(events),
            "chain_digest": _event_chain_digest(events),
            "tail_file_sha256": EXPECTED_HASHES["old_event_tail_file"],
            "kind_counts": dict(sorted(Counter(event["kind"] for event in events).items())),
            "started_job_ids": sorted(started),
            "synced_job_ids": sorted(synced_events),
            "failure_count": 0,
        },
        "jobs": {
            "registered_count": len(job_ids),
            "local_completed": sorted(local_rows, key=lambda row: row["job_id"]),
            "durable_completed": sorted(durable_rows, key=lambda row: row["job_id"]),
            "untouched_job_ids": untouched,
            "orphan_job_id": ORPHAN_JOB_ID,
            "orphan_child_pid": ORPHAN_CHILD_PID,
            "hidden_partial": partial,
        },
        "staging": staging,
        "lower_report_count": 0,
        "production_launch_receipt_present": False,
        "mechanical_source_validation_performed": True,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
    }
    return _seal(inventory, "inventory_digest")


def _quiescent_liveness() -> dict[str, Any]:
    recorded = (
        windows_liveness.RecordedProcess(
            "epoch001_lease_owner", OLD_LEASE_PID, role="owner"
        ),
        windows_liveness.RecordedProcess(
            "orphan_completed_worker", ORPHAN_CHILD_PID, role="worker"
        ),
    )
    try:
        report = windows_liveness.capture_windows_process_stability(recorded)
        classified = windows_liveness.assert_windows_stability_gate(report)
    except windows_liveness.ProcessLivenessError as exc:
        raise RecoveryRefused(f"Windows liveness refused recovery: {exc}") from exc
    stability = classified.get("stability", {})
    if (
        type(stability) is not dict
        or stability.get("verdict") != "pass"
        or stability.get("controller_launcher_required") is not True
        or stability.get("controller_launcher_stable") is not True
        or type(stability.get("controller_launcher")) is not dict
    ):
        raise RecoveryRefused("Windows liveness did not return a passing stability gate")
    return dict(classified)


def _capture_twice() -> tuple[dict[str, Any], dict[str, Any]]:
    inspection = _run_old_source_inspector()
    first = _capture_outcome_blind_inventory(inspection)
    second = _capture_outcome_blind_inventory(inspection)
    if _canonical(first) != _canonical(second):
        raise RecoveryRefused("two outcome-blind incident inventories are not equal")
    return first, inspection


def _base_record(record_type: str) -> dict[str, Any]:
    return {
        "recovery_schema_version": RECOVERY_SCHEMA_VERSION,
        "recovery_id": RECOVERY_ID,
        "decision_id": DECISION_ID,
        "record_type": record_type,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
    }


def _validate_liveness_rows(value: object, *, what: str) -> None:
    if type(value) is not list or not value:
        raise RecoveryRefused(f"{what} must contain liveness evidence")
    for index, item in enumerate(value):
        row = _expect_keys(item, {"sha256", "report"}, what=f"{what}[{index}]")
        if type(row["report"]) is not dict:
            raise RecoveryRefused(f"{what}[{index}] report is not an object")
        if (
            _expect_sha(row["sha256"], what=f"{what}[{index}] SHA256")
            != sha256_bytes(_canonical(row["report"]))
            or row["report"].get("stability", {}).get("verdict") != "pass"
        ):
            raise RecoveryRefused(f"{what}[{index}] is not a passing stability proof")


def _validate_incident_contract(document: Mapping[str, Any]) -> None:
    _expect_keys(
        document,
        set(_base_record("incident"))
        | {
            "status",
            "automatic_retry_allowed",
            "authority",
            "controller_process",
            "inventory",
            "inventory_digest",
            "liveness_stability_reports",
            "record_digest",
        },
        what="incident record",
    )
    if (
        document["status"] != "outcome_blind_interruption_adjudicated"
        or document["automatic_retry_allowed"] is not False
    ):
        raise RecoveryRefused("incident status or retry policy differs")
    _validate_controller_process_attestation(
        document["controller_process"], base=document["authority"]["base_python"],
        what="incident controller process",
    )
    inventory = _validate_seal(
        document["inventory"], field="inventory_digest", what="incident inventory"
    )
    if document["inventory_digest"] != inventory["inventory_digest"]:
        raise RecoveryRefused("incident inventory binding differs")
    _expect_keys(
        inventory,
        {
            "inventory_schema_version",
            "execution_commit",
            "relocation",
            "control",
            "lease",
            "checkpoint",
            "events",
            "jobs",
            "staging",
            "lower_report_count",
            "production_launch_receipt_present",
            "mechanical_source_validation_performed",
            "scientific_outcomes_consulted",
            "scientific_values_emitted",
            "inventory_digest",
        },
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
        raise RecoveryRefused("incident inventory fixed state differs")
    _, relocation = _relocation_state()
    if _canonical(inventory["relocation"]) != _canonical(relocation):
        raise RecoveryRefused("incident relocation admission differs")
    lease = _expect_keys(
        inventory["lease"],
        {"path", "sha256", "pid", "token", "timestamp", "timestamp_utc"},
        what="incident lease",
    )
    checkpoint = _expect_keys(
        inventory["checkpoint"],
        {"token", "sha256", "checkpoint_digest", "execution_context_digest"},
        what="incident checkpoint",
    )
    events = _expect_keys(
        inventory["events"],
        {
            "count",
            "chain_digest",
            "tail_file_sha256",
            "kind_counts",
            "started_job_ids",
            "synced_job_ids",
            "failure_count",
        },
        what="incident events",
    )
    jobs = _expect_keys(
        inventory["jobs"],
        {
            "registered_count",
            "local_completed",
            "durable_completed",
            "untouched_job_ids",
            "orphan_job_id",
            "orphan_child_pid",
            "hidden_partial",
        },
        what="incident jobs",
    )
    hidden = _expect_keys(
        jobs["hidden_partial"],
        {"name", "entry_count", "file_count", "inventory", "inventory_digest"},
        what="incident hidden partial",
    )
    if (
        lease["path"]
        != str(
            (
                Plan.COMMON_LEASE_ROOT
                / "leases"
                / f"{Plan.COMMON_LEASE_NAME}.lease.json"
            ).resolve()
        )
        or lease["sha256"] != EXPECTED_HASHES["old_lease"]
        or lease["pid"] != OLD_LEASE_PID
        or lease["token"] != OLD_LEASE_TOKEN
        or checkpoint["token"] != OLD_LEASE_TOKEN
        or checkpoint["sha256"] != EXPECTED_HASHES["old_checkpoint"]
        or checkpoint["checkpoint_digest"] != EXPECTED_OLD_CHECKPOINT_DIGEST
        or _HEX64.fullmatch(str(checkpoint["execution_context_digest"])) is None
        or events["count"] != EXPECTED_INITIAL_COUNTS["events"]
        or events["chain_digest"] != EXPECTED_HASHES["old_event_stream"]
        or events["tail_file_sha256"] != EXPECTED_HASHES["old_event_tail_file"]
        or events["kind_counts"] != {"attempt_started": 150, "job_synced": 149}
        or type(events["started_job_ids"]) is not list
        or len(events["started_job_ids"]) != 150
        or type(events["synced_job_ids"]) is not list
        or len(events["synced_job_ids"]) != 149
        or events["failure_count"] != 0
        or jobs["registered_count"] != 261
        or type(jobs["local_completed"]) is not list
        or len(jobs["local_completed"]) != 150
        or type(jobs["durable_completed"]) is not list
        or len(jobs["durable_completed"]) != 149
        or type(jobs["untouched_job_ids"]) is not list
        or len(jobs["untouched_job_ids"]) != 111
        or jobs["orphan_job_id"] != ORPHAN_JOB_ID
        or jobs["orphan_child_pid"] != ORPHAN_CHILD_PID
        or hidden["name"] != HIDDEN_PARTIAL_NAME
        or hidden["file_count"] != 11
        or type(hidden["entry_count"]) is not int
        or hidden["entry_count"] < hidden["file_count"]
        or type(hidden["inventory"]) is not list
        or sha256_bytes(_canonical(hidden["inventory"]))
        != hidden["inventory_digest"]
    ):
        raise RecoveryRefused("incident record differs from the exact D-161 state")
    _validate_liveness_rows(
        document["liveness_stability_reports"], what="incident liveness"
    )


def adjudicate() -> dict[str, Any]:
    """Publish the immutable incident and externally interrupted epoch record."""

    if _record_presence(TRANSITION_INTENT_FILE) or _record_presence(
        TRANSITION_COMPLETION_FILE
    ):
        raise RecoveryRefused("ownership transition already began; adjudication is closed")
    authority_before = _controller_authority()
    if _record_presence(INCIDENT_FILE):
        incident, incident_sha = _load_twins(INCIDENT_FILE, record_type="incident")
        current, _ = _capture_twice()
        if _canonical(current) != _canonical(incident["inventory"]):
            raise RecoveryRefused("existing incident no longer matches the frozen state")
        authority = _controller_authority()
        if (
            _canonical(authority) != _canonical(authority_before)
            or _canonical(authority) != _canonical(incident["authority"])
        ):
            raise RecoveryRefused("controller authority changed during adjudication")
        liveness = _quiescent_liveness()
        if not _record_presence(EPOCH001_TERMINAL_FILE):
            _publish_epoch001_terminal(incident, incident_sha)
        terminal, terminal_sha = _load_twins(
            EPOCH001_TERMINAL_FILE, record_type="epoch001_terminal"
        )
        return {
            "command": "adjudicate",
            "status": "adjudicated",
            "incident_sha256": incident_sha,
            "epoch001_terminal_sha256": terminal_sha,
            "liveness_verdicts": [liveness["stability"]["verdict"]],
        }

    inventory, _ = _capture_twice()
    authority = _controller_authority()
    if _canonical(authority) != _canonical(authority_before):
        raise RecoveryRefused("controller authority changed during adjudication")
    liveness = _quiescent_liveness()
    payload = {
            **_base_record("incident"),
            "status": "outcome_blind_interruption_adjudicated",
            "automatic_retry_allowed": False,
            "authority": authority,
            "controller_process": _controller_process_attestation(authority),
            "inventory": inventory,
            "inventory_digest": inventory["inventory_digest"],
            "liveness_stability_reports": [
                {
                    "sha256": sha256_bytes(_canonical(liveness)),
                    "report": liveness,
                }
            ],
        }
    _validate_incident_contract(_seal(payload))
    incident = _publish_twins(INCIDENT_FILE, payload)
    _validate_incident_contract(incident)
    incident_sha = sha256_file(_record_paths(INCIDENT_FILE)[0])
    terminal = _publish_epoch001_terminal(incident, incident_sha)
    return {
        "command": "adjudicate",
        "status": "adjudicated",
        "incident_sha256": incident_sha,
        "epoch001_terminal_sha256": sha256_file(
            _record_paths(EPOCH001_TERMINAL_FILE)[0]
        ),
        "event_count": terminal["counts"]["events"],
        "liveness_verdicts": ["pass"],
    }


def _publish_epoch001_terminal(
    incident: Mapping[str, Any], incident_file_sha256: str
) -> dict[str, Any]:
    _assert_no_old_normal_release()
    return _publish_twins(
        EPOCH001_TERMINAL_FILE,
        _epoch001_terminal_payload(incident, incident_file_sha256),
    )


def _epoch001_terminal_payload(
    incident: Mapping[str, Any], incident_file_sha256: str
) -> dict[str, Any]:
    inventory = incident["inventory"]
    return {
        **_base_record("epoch001_terminal"),
        "status": "externally_interrupted",
        "incident": {
            "record_digest": incident["record_digest"],
            "file_sha256": incident_file_sha256,
            "inventory_digest": incident["inventory_digest"],
        },
        "execution_commit": EXECUTION_COMMIT,
        "lease_token": OLD_LEASE_TOKEN,
        "lease_pid": OLD_LEASE_PID,
        "orphan_job_id": ORPHAN_JOB_ID,
        "orphan_child_pid": ORPHAN_CHILD_PID,
        "counts": {
            "events": inventory["events"]["count"],
            "started": len(inventory["events"]["started_job_ids"]),
            "synced": len(inventory["events"]["synced_job_ids"]),
            "unresolved_started": 1,
            "failed": 0,
        },
        "lower_terminal_report_present": False,
        "normal_lease_release_present": False,
        "automatic_retry_allowed": False,
    }


def _old_normal_release_path() -> Path:
    return (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / "history"
        / f"{Plan.COMMON_LEASE_NAME}.{OLD_LEASE_TOKEN}.released.json"
    )


def _assert_no_old_normal_release() -> None:
    if os.path.lexists(_old_normal_release_path()):
        raise RecoveryRefused(
            "the frozen orphan token has forbidden normal release history"
        )


def _orphan_archive_path() -> Path:
    return (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / "history"
        / (
            f"{Plan.COMMON_LEASE_NAME}.{OLD_LEASE_TOKEN}."
            "orphaned-after-liveness-proof.json"
        )
    )


def _orphan_archive_binding_path() -> Path:
    path = _orphan_archive_path()
    if os.path.lexists(path):
        return _plain_regular_file(path, what="D-161 orphan lease archive")
    return _plain_future_file(path, what="D-161 orphan lease archive")


def historical_orphan_lease_record(token: str) -> dict[str, Any]:
    """Return the exact historical-lease row authorized by D-161.

    This public seam is intentionally narrower than the lower launcher's
    ordinary history lookup.  Callers must use it only for the one frozen
    orphan token and delegate every other token to the ordinary implementation.
    """

    if type(token) is not str or token != OLD_LEASE_TOKEN:
        raise RecoveryRefused("D-161 orphan history recognizes only the frozen token")
    _load_transition_completion()
    archive = _plain_regular_file(
        _orphan_archive_path(), what="D-161 orphan lease archive"
    )
    record = _expect_keys(
        read_json(archive),
        {
            "schema_version",
            "lease_name",
            "pid",
            "token",
            "timestamp",
            "timestamp_utc",
        },
        what="D-161 orphan lease archive",
    )
    if (
        record["schema_version"] != Supervisor.SUPERVISOR_SCHEMA_VERSION
        or record["lease_name"] != Plan.COMMON_LEASE_NAME
        or record["pid"] != OLD_LEASE_PID
        or record["token"] != OLD_LEASE_TOKEN
        or sha256_file(archive) != EXPECTED_HASHES["old_lease"]
    ):
        raise RecoveryRefused("D-161 orphan lease archive identity differs")
    active = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / f"{Plan.COMMON_LEASE_NAME}.lease.json"
    )
    return {
        "path": str(active.resolve()),
        "sha256": EXPECTED_HASHES["old_lease"],
        "name": Plan.COMMON_LEASE_NAME,
        "token": OLD_LEASE_TOKEN,
        "started_at": record["timestamp_utc"],
    }


def _quarantine_paths() -> tuple[Path, Path]:
    return (
        RECOVERY_ROOT / "quarantine" / HIDDEN_PARTIAL_NAME,
        RECOVERY_COPY_ROOT / "quarantine" / HIDDEN_PARTIAL_NAME,
    )


def _copy_tree_exclusive(source: Path, destination: Path) -> None:
    rows = _plain_tree_inventory(source, what="quarantine source")
    if os.path.lexists(destination):
        raise RecoveryRefused("independent quarantine destination already exists")
    _ensure_recovery_root(destination.parent)
    destination.mkdir()
    for row in rows:
        target = destination / row["path"]
        if row["kind"] == "directory":
            target.mkdir(parents=True, exist_ok=False)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(target, (source / row["path"]).read_bytes())
    fsync_directory(destination)


def _independent_equal_trees(left: Path, right: Path) -> list[dict[str, Any]]:
    left_rows = _plain_tree_inventory(left, what="quarantine original")
    right_rows = _plain_tree_inventory(right, what="quarantine copy")
    if left_rows != right_rows:
        raise RecoveryRefused("quarantine original/copy content inventories differ")
    for row in _file_rows(left_rows):
        left_file = left / row["path"]
        right_file = right / row["path"]
        try:
            if os.path.samefile(left_file, right_file):
                raise RecoveryRefused("quarantine files are not independent objects")
        except OSError as exc:
            raise RecoveryRefused(f"cannot compare quarantine file identity: {exc}") from exc
    return left_rows


def _archive_orphan_lease(active: Path, archive: Path) -> None:
    active = _plain_regular_file(active, what="active orphan lease")
    archive = _plain_future_file(archive, what="orphan lease archive")
    if sha256_file(active) != EXPECTED_HASHES["old_lease"]:
        raise RecoveryRefused("lease changed immediately before orphan archival")
    Supervisor._archive_file_exclusive(active, archive)
    if os.path.lexists(active) or sha256_file(archive) != EXPECTED_HASHES["old_lease"]:
        raise RecoveryRefused("orphan lease archival did not preserve exact bytes")


def _quarantine_partial(source: Path, expected: Mapping[str, Any]) -> dict[str, Any]:
    original, copy = _quarantine_paths()
    before = _plain_tree_inventory(source, what="pre-transition hidden partial")
    if _canonical(before) != _canonical(expected["inventory"]):
        raise RecoveryRefused("hidden partial changed immediately before quarantine")
    for target in (original, copy):
        if os.path.lexists(target):
            raise RecoveryRefused("quarantine target already exists")
    _ensure_recovery_root(original.parent)
    os.replace(source, original)
    fsync_directory(source.parent)
    fsync_directory(original.parent)
    after_move = _plain_tree_inventory(original, what="moved hidden partial")
    if before != after_move:
        raise RecoveryRefused("hidden partial bytes changed during quarantine move")
    _copy_tree_exclusive(original, copy)
    rows = _independent_equal_trees(original, copy)
    return {
        "original_path": str(original.resolve()),
        "copy_path": str(copy.resolve()),
        "inventory": rows,
        "inventory_digest": _tree_digest(rows),
        "independent_copy": True,
    }


def _transition_material(
    incident: Mapping[str, Any], incident_sha: str, terminal_sha: str
) -> dict[str, Any]:
    authority = incident["authority"]
    return {
        "incident": {
            "record_digest": incident["record_digest"],
            "file_sha256": incident_sha,
            "inventory_digest": incident["inventory_digest"],
        },
        "epoch001_terminal_file_sha256": terminal_sha,
        "controller_commit": authority["controller_worktree"]["git_commit"],
        "controller_module": authority["controller_module"],
        "bootstrap_worker": authority["bootstrap_worker"],
        "recovery_inspector": authority["recovery_inspector"],
        "execution_worktree": authority["execution_worktree"],
        "pinned_python": authority["pinned_python"],
        "old_lease": incident["inventory"]["lease"],
        "orphan_archive_path": str(_orphan_archive_binding_path().resolve()),
        "hidden_partial": incident["inventory"]["jobs"]["hidden_partial"],
        "automatic_retry_allowed": False,
    }


def _load_adjudication() -> tuple[dict[str, Any], str, dict[str, Any], str]:
    _assert_no_old_normal_release()
    incident, incident_sha = _load_twins(INCIDENT_FILE, record_type="incident")
    _validate_incident_contract(incident)
    terminal, terminal_sha = _load_twins(
        EPOCH001_TERMINAL_FILE, record_type="epoch001_terminal"
    )
    expected_terminal = _seal(_epoch001_terminal_payload(incident, incident_sha))
    if _canonical(terminal) != _canonical(expected_terminal):
        raise RecoveryRefused("epoch-001 terminal does not bind the incident")
    return incident, incident_sha, terminal, terminal_sha


def _load_transition_records_only() -> tuple[dict[str, Any], str]:
    """Validate immutable transition records without opening quarantined payloads."""

    completion, digest = _load_twins(
        TRANSITION_COMPLETION_FILE, record_type="transition_completion"
    )
    intent, intent_sha = _load_twins(
        TRANSITION_INTENT_FILE, record_type="transition_intent"
    )
    incident, incident_sha, _, terminal_sha = _load_adjudication()
    expected_authorization = _transition_material(
        incident, incident_sha, terminal_sha
    )
    _expect_keys(
        intent,
        set(_base_record("transition_intent"))
        | {
            "status",
            "authorization",
            "liveness_stability_reports",
            "record_digest",
        },
        what="transition intent",
    )
    _validate_liveness_rows(
        intent["liveness_stability_reports"], what="transition intent liveness"
    )
    _expect_keys(
        completion,
        set(_base_record("transition_completion"))
        | {
            "status",
            "authorization",
            "transition_intent",
            "orphan_lease_archive",
            "quarantine",
            "record_digest",
        },
        what="transition completion",
    )
    intent_binding = _expect_keys(
        completion["transition_intent"],
        {"record_digest", "file_sha256"},
        what="transition completion intent binding",
    )
    if (
        intent_binding["record_digest"] != intent["record_digest"]
        or intent_binding["file_sha256"] != intent_sha
        or completion["status"] != "ownership_transition_complete"
        or intent.get("status") != "ownership_transition_intended"
        or _canonical(intent.get("authorization"))
        != _canonical(expected_authorization)
        or _canonical(completion.get("authorization"))
        != _canonical(expected_authorization)
    ):
        raise RecoveryRefused("transition completion does not bind its intent")
    return completion, digest


def _load_transition_completion() -> tuple[dict[str, Any], str]:
    completion, digest = _load_transition_records_only()
    archive = _plain_regular_file(
        _orphan_archive_path(), what="D-161 orphan lease archive"
    )
    active = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / f"{Plan.COMMON_LEASE_NAME}.lease.json"
    )
    if os.path.lexists(active):
        active = _plain_regular_file(active, what="active shared lease")
        if read_json(active).get("token") == OLD_LEASE_TOKEN:
            raise RecoveryRefused(
                "orphan lease remains active after transition completion"
            )
    archive_row = _expect_keys(
        completion.get("orphan_lease_archive"),
        {"path", "sha256", "classification"},
        what="transition orphan archive binding",
    )
    if (
        Path(archive_row["path"]).resolve() != archive.resolve()
        or archive_row["sha256"] != EXPECTED_HASHES["old_lease"]
        or archive_row["classification"] != "orphaned_after_liveness_proof"
        or sha256_file(archive) != EXPECTED_HASHES["old_lease"]
    ):
        raise RecoveryRefused("orphan lease archive changed after transition")
    original, copy = _quarantine_paths()
    rows = _independent_equal_trees(original, copy)
    quarantine = _expect_keys(
        completion.get("quarantine"),
        {
            "original_path",
            "copy_path",
            "inventory",
            "inventory_digest",
            "independent_copy",
        },
        what="transition quarantine binding",
    )
    if (
        Path(quarantine["original_path"]).resolve() != original.resolve()
        or Path(quarantine["copy_path"]).resolve() != copy.resolve()
        or quarantine["independent_copy"] is not True
        or quarantine["inventory"] != rows
        or _tree_digest(rows) != quarantine["inventory_digest"]
    ):
        raise RecoveryRefused("quarantined partial changed after transition")
    return completion, digest


def _lower_reports() -> dict[str, tuple[Path, Path, dict[str, Any], str]]:
    local_dir = P.OUTPUT_ROOT / Launch.REPORT_DIRECTORY
    copy_dir = P.SYNC_ROOT / Launch.REPORT_DIRECTORY
    local = {path.name: path for path in _directory_entries(local_dir, what="lower reports")}
    copied = {path.name: path for path in _directory_entries(copy_dir, what="lower report copies")}
    if set(local) != set(copied):
        raise RecoveryRefused("lower report original/copy inventories differ")
    result: dict[str, tuple[Path, Path, dict[str, Any], str]] = {}
    for name in sorted(local):
        match = _TOKEN_FILE.fullmatch(name)
        if match is None:
            raise RecoveryRefused("lower report has a noncanonical filename")
        digest = _same_bytes(local[name], copied[name], what=f"lower report {name}")
        document = read_json(local[name])
        if read_json(copied[name]) != document:
            raise RecoveryRefused("lower report changed after twin validation")
        result[match.group(1)] = (local[name], copied[name], document, digest)
    return result


def _record_binding(
    document: Mapping[str, Any], file_sha256: str, *, inventory: bool = False
) -> dict[str, str]:
    row = {
        "record_digest": _expect_sha(
            document.get("record_digest"), what="record binding digest"
        ),
        "file_sha256": _expect_sha(file_sha256, what="record binding file SHA256"),
    }
    if inventory:
        row["inventory_digest"] = _expect_sha(
            document.get("inventory_digest"), what="record inventory digest"
        )
    return row


def _bootstrap_prelaunch_state() -> dict[str, Any]:
    local = P.OUTPUT_ROOT / Plan.START_DIRECTORY / f"{OLD_LEASE_TOKEN}.json"
    copied = P.SYNC_ROOT / Plan.START_DIRECTORY / f"{OLD_LEASE_TOKEN}.json"
    for directory, what in (
        (local.parent, "local checkpoint directory"),
        (copied.parent, "checkpoint copy directory"),
    ):
        if [path.name for path in _directory_entries(directory, what=what)] != [
            local.name
        ]:
            raise RecoveryRefused("continuation checkpoint already exists")
    checkpoint_sha = _same_bytes(local, copied, what="epoch-001 checkpoint")
    if checkpoint_sha != EXPECTED_HASHES["old_checkpoint"]:
        raise RecoveryRefused("epoch-001 checkpoint changed before invocation")
    for report_root in (
        P.OUTPUT_ROOT / Launch.REPORT_DIRECTORY,
        P.SYNC_ROOT / Launch.REPORT_DIRECTORY,
    ):
        if os.path.lexists(report_root):
            raise RecoveryRefused("continuation lower-report path already exists")
    if _record_presence(RECOVERY_COMPLETION_FILE):
        raise RecoveryRefused("recovery completion exists before invocation")
    if P._receipt_present("launch"):
        raise RecoveryRefused("production launch receipt exists before invocation")
    active = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / f"{Plan.COMMON_LEASE_NAME}.lease.json"
    )
    if os.path.lexists(active):
        raise RecoveryRefused("an active shared lease exists before invocation")
    return {
        "old_checkpoint": {
            "token": OLD_LEASE_TOKEN,
            "path": str(local.resolve()),
            "copy_path": str(copied.resolve()),
            "sha256": checkpoint_sha,
            "checkpoint_digest": EXPECTED_OLD_CHECKPOINT_DIGEST,
        },
        "continuation_checkpoint_tokens": [],
        "lower_report_tokens": [],
        "recovery_completion_present": False,
        "production_launch_receipt_present": False,
        "active_shared_lease_present": False,
    }


def _bootstrap_invocation_payload(
    incident: Mapping[str, Any],
    incident_sha: str,
    terminal: Mapping[str, Any],
    terminal_sha: str,
    intent: Mapping[str, Any],
    intent_sha: str,
    transition: Mapping[str, Any],
    transition_sha: str,
    prelaunch: Mapping[str, Any],
    controller_process: Mapping[str, Any],
    runtime_temp: Mapping[str, Any],
    child_transport: Mapping[str, Any],
) -> dict[str, Any]:
    claim_left, claim_right = _record_paths(BOOTSTRAP_CLAIM_FILE)
    return {
        **_base_record("bootstrap_invocation"),
        "status": "authorized_once",
        "incident": _record_binding(incident, incident_sha, inventory=True),
        "epoch001_terminal": _record_binding(terminal, terminal_sha),
        "transition_intent": _record_binding(intent, intent_sha),
        "transition_completion": _record_binding(transition, transition_sha),
        "authority": incident["authority"],
        "controller_process": dict(controller_process),
        "runtime_temp": dict(runtime_temp),
        "child_transport": dict(child_transport),
        "prelaunch_state": dict(prelaunch),
        "prelaunch_state_digest": sha256_bytes(_canonical(prelaunch)),
        "claim_paths": {
            "original_path": str(claim_left.resolve()),
            "copy_path": str(claim_right.resolve()),
            "exclusive": True,
        },
        "automatic_retry_allowed": False,
    }


def _load_bootstrap_invocation() -> tuple[dict[str, Any], str]:
    document, file_sha = _load_twins(
        BOOTSTRAP_INVOCATION_FILE, record_type="bootstrap_invocation"
    )
    expected_keys = set(_base_record("bootstrap_invocation")) | {
        "status",
        "incident",
        "epoch001_terminal",
        "transition_intent",
        "transition_completion",
        "authority",
        "controller_process",
        "runtime_temp",
        "child_transport",
        "prelaunch_state",
        "prelaunch_state_digest",
        "claim_paths",
        "automatic_retry_allowed",
        "record_digest",
    }
    _expect_keys(document, expected_keys, what="bootstrap invocation")
    _validate_controller_process_attestation(
        document["controller_process"],
        base=document["authority"]["base_python"],
        what="bootstrap invocation controller",
    )
    child_transport = _validate_child_transport(
        document["child_transport"],
        logical_path=BOOTSTRAP_SCRIPT,
        what="bootstrap invocation child transport",
    )
    if child_transport["source_sha256"] != document["authority"][
        "bootstrap_worker"
    ]["sha256"]:
        raise RecoveryRefused("bootstrap child transport differs from authority")
    runtime_identity = _runtime_temp_directory_identity(
        RUNTIME_TEMP, what="bootstrap invocation runtime temp"
    )
    if _canonical(document["runtime_temp"]) != _canonical(runtime_identity):
        raise RecoveryRefused("bootstrap invocation runtime temp identity differs")
    if (
        document["status"] != "authorized_once"
        or document["automatic_retry_allowed"] is not False
        or document["prelaunch_state_digest"]
        != sha256_bytes(_canonical(document["prelaunch_state"]))
    ):
        raise RecoveryRefused("bootstrap invocation policy or state digest differs")
    prelaunch = _expect_keys(
        document["prelaunch_state"],
        {
            "old_checkpoint",
            "continuation_checkpoint_tokens",
            "lower_report_tokens",
            "recovery_completion_present",
            "production_launch_receipt_present",
            "active_shared_lease_present",
        },
        what="bootstrap invocation prelaunch state",
    )
    old_checkpoint = _expect_keys(
        prelaunch["old_checkpoint"],
        {"token", "path", "copy_path", "sha256", "checkpoint_digest"},
        what="bootstrap invocation old checkpoint",
    )
    old_local = (
        P.OUTPUT_ROOT / Plan.START_DIRECTORY / f"{OLD_LEASE_TOKEN}.json"
    )
    old_copy = P.SYNC_ROOT / Plan.START_DIRECTORY / f"{OLD_LEASE_TOKEN}.json"
    expected_old = {
        "token": OLD_LEASE_TOKEN,
        "path": str(old_local.resolve()),
        "copy_path": str(old_copy.resolve()),
        "sha256": EXPECTED_HASHES["old_checkpoint"],
        "checkpoint_digest": EXPECTED_OLD_CHECKPOINT_DIGEST,
    }
    if (
        old_checkpoint != expected_old
        or prelaunch["continuation_checkpoint_tokens"] != []
        or prelaunch["lower_report_tokens"] != []
        or prelaunch["recovery_completion_present"] is not False
        or prelaunch["production_launch_receipt_present"] is not False
        or prelaunch["active_shared_lease_present"] is not False
    ):
        raise RecoveryRefused("bootstrap invocation prelaunch state differs")
    left, right = _record_paths(BOOTSTRAP_CLAIM_FILE)
    if document["claim_paths"] != {
        "original_path": str(left.resolve()),
        "copy_path": str(right.resolve()),
        "exclusive": True,
    }:
        raise RecoveryRefused("bootstrap invocation claim paths differ")
    incident, incident_sha, epoch_terminal, epoch_terminal_sha = _load_adjudication()
    transition, transition_sha = _load_transition_completion()
    intent, intent_sha = _load_twins(
        TRANSITION_INTENT_FILE, record_type="transition_intent"
    )
    expected_bindings = {
        "incident": _record_binding(incident, incident_sha, inventory=True),
        "epoch001_terminal": _record_binding(
            epoch_terminal, epoch_terminal_sha
        ),
        "transition_intent": _record_binding(intent, intent_sha),
        "transition_completion": _record_binding(transition, transition_sha),
    }
    if (
        any(document[name] != binding for name, binding in expected_bindings.items())
        or _canonical(document["authority"])
        != _canonical(incident["authority"])
    ):
        raise RecoveryRefused("bootstrap invocation does not bind the full recovery chain")
    return document, file_sha


def _validate_bootstrap_claim_document(
    claim: Mapping[str, Any],
    *,
    invocation: Mapping[str, Any],
    invocation_sha: str,
) -> None:
    expected_keys = set(_base_record("bootstrap_claim")) | {
        "status",
        "invocation",
        "transition_completion",
        "prelaunch_state_digest",
        "worker",
        "claim_paths",
        "exclusive_create",
        "automatic_retry_allowed",
        "record_digest",
    }
    _expect_keys(claim, expected_keys, what="bootstrap claim")
    worker = _expect_keys(
        claim["worker"],
        {
            "pid",
            "parent_pid",
            "process",
            "parent_process",
            "bootstrap_worker",
            "pinned_python",
        },
        what="bootstrap claim worker",
    )
    pinned = invocation["authority"]["pinned_python"]
    parent = _validate_process_attestation(
        worker["parent_process"],
        pinned=pinned,
        what="bootstrap claim parent process",
    )
    worker_process = _validate_controller_process_attestation(
        worker["process"],
        base=invocation["authority"]["base_python"],
        what="bootstrap worker process",
    )
    if (
        claim["status"] != "claimed_before_lower_import_or_launch"
        or claim["invocation"]
        != _record_binding(invocation, invocation_sha)
        or claim["transition_completion"]
        != invocation["transition_completion"]
        or claim["prelaunch_state_digest"]
        != invocation["prelaunch_state_digest"]
        or claim["claim_paths"] != invocation["claim_paths"]
        or claim["exclusive_create"] is not True
        or claim["automatic_retry_allowed"] is not False
        or type(worker["pid"]) is not int
        or worker["pid"] <= 0
        or type(worker["parent_pid"]) is not int
        or worker["parent_pid"] <= 0
        or worker_process["pid"] != worker["pid"]
        or parent["pid"] != worker["parent_pid"]
        or parent["parent_pid"] != invocation["controller_process"]["pid"]
        or worker["bootstrap_worker"]
        != invocation["authority"]["bootstrap_worker"]
        or worker["pinned_python"] != pinned
    ):
        raise RecoveryRefused("bootstrap claim does not consume the invocation exactly")


def _load_bootstrap_claim_available(
    invocation: Mapping[str, Any], invocation_sha: str
) -> tuple[dict[str, Any], str, bool]:
    claim, claim_sha, twins_complete = _load_available_twins(
        BOOTSTRAP_CLAIM_FILE, record_type="bootstrap_claim"
    )
    _validate_bootstrap_claim_document(
        claim, invocation=invocation, invocation_sha=invocation_sha
    )
    return claim, claim_sha, twins_complete


def _load_bootstrap_claim(
    invocation: Mapping[str, Any], invocation_sha: str
) -> tuple[dict[str, Any], str]:
    claim, claim_sha, twins_complete = _load_bootstrap_claim_available(
        invocation, invocation_sha
    )
    if not twins_complete:
        raise RecoveryRefused("bootstrap claim has only one immutable twin")
    return claim, claim_sha


def _validate_bootstrap_terminal_document(
    terminal: Mapping[str, Any],
    *,
    invocation: Mapping[str, Any],
    invocation_sha: str,
    claim: Mapping[str, Any] | None,
    claim_sha: str | None,
    claim_twins_complete: bool | None,
) -> None:
    expected_keys = set(_base_record("bootstrap_terminal")) | {
        "status",
        "bootstrap_schema_version",
        "invocation",
        "claim",
        "operational_result",
        "automatic_retry_allowed",
        "record_digest",
    }
    _expect_keys(terminal, expected_keys, what="bootstrap terminal")
    observed_claim = _expect_keys(
        terminal["claim"],
        {"record_digest", "file_sha256", "twins_complete"},
        what="bootstrap terminal claim binding",
    )
    _expect_sha(
        observed_claim["record_digest"],
        what="bootstrap terminal claim record digest",
    )
    _expect_sha(
        observed_claim["file_sha256"],
        what="bootstrap terminal claim file SHA256",
    )
    if type(observed_claim["twins_complete"]) is not bool:
        raise RecoveryRefused("bootstrap terminal claim completeness is not boolean")
    if claim is not None:
        if claim_sha is None or claim_twins_complete is None:
            raise RecoveryRefused("bootstrap terminal claim validation is incomplete")
        expected_claim = {
            "record_digest": claim["record_digest"],
            "file_sha256": claim_sha,
            "twins_complete": claim_twins_complete,
        }
        if observed_claim != expected_claim:
            raise RecoveryRefused("bootstrap terminal does not bind its claim exactly")
    if (
        terminal["bootstrap_schema_version"] != BOOTSTRAP_CONTRACT_SCHEMA_VERSION
        or terminal["status"] not in {"complete", "refused"}
        or terminal["invocation"] != _record_binding(invocation, invocation_sha)
        or terminal["automatic_retry_allowed"] is not False
        or type(terminal["operational_result"]) is not dict
    ):
        raise RecoveryRefused("bootstrap terminal does not bind its claim exactly")
    operational = terminal["operational_result"]
    if terminal["status"] == "complete":
        _expect_keys(
            operational,
            {
                "counts",
                "lease_token",
                "report_sha256",
                "script_sha256",
                "output_capture",
            },
            what="bootstrap terminal completion",
        )
        _validate_output_capture(
            operational["output_capture"], what="bootstrap terminal output capture"
        )
        if (
            operational["counts"] != EXPECTED_RECOVERY_COUNTS
            or type(operational["lease_token"]) is not str
            or _HEX32.fullmatch(operational["lease_token"]) is None
            or operational["lease_token"] == OLD_LEASE_TOKEN
            or _expect_sha(
                operational["report_sha256"], what="terminal report SHA256"
            )
            != operational["report_sha256"]
            or operational["script_sha256"]
            != invocation["authority"]["bootstrap_worker"]["sha256"]
        ):
            raise RecoveryRefused("bootstrap complete terminal accounting differs")
    else:
        refusal_keys = {"error_type", "reason_sha256"}
        if "output_capture" in operational:
            refusal_keys.add("output_capture")
        _expect_keys(
            operational,
            refusal_keys,
            what="bootstrap refusal terminal",
        )
        if "output_capture" in operational:
            _validate_output_capture(
                operational["output_capture"],
                what="bootstrap refusal output capture",
            )
        if (
            type(operational["error_type"]) is not str
            or not operational["error_type"]
            or _HEX64.fullmatch(str(operational["reason_sha256"])) is None
        ):
            raise RecoveryRefused("bootstrap refusal terminal is malformed")


def _load_bootstrap_terminal_available(
    invocation: Mapping[str, Any],
    invocation_sha: str,
    claim: Mapping[str, Any] | None,
    claim_sha: str | None,
    *,
    claim_twins_complete: bool | None,
) -> tuple[dict[str, Any], str, bool]:
    terminal, terminal_sha, terminal_twins_complete = _load_available_twins(
        BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal"
    )
    _validate_bootstrap_terminal_document(
        terminal,
        invocation=invocation,
        invocation_sha=invocation_sha,
        claim=claim,
        claim_sha=claim_sha,
        claim_twins_complete=claim_twins_complete,
    )
    return terminal, terminal_sha, terminal_twins_complete


def _load_bootstrap_terminal(
    invocation: Mapping[str, Any],
    invocation_sha: str,
    claim: Mapping[str, Any],
    claim_sha: str,
) -> tuple[dict[str, Any], str]:
    terminal, terminal_sha, terminal_twins_complete = (
        _load_bootstrap_terminal_available(
            invocation,
            invocation_sha,
            claim,
            claim_sha,
            claim_twins_complete=True,
        )
    )
    if not terminal_twins_complete:
        raise RecoveryRefused("bootstrap terminal has only one immutable twin")
    return terminal, terminal_sha


def _claimed_worker_lifecycle(
    claim: Mapping[str, Any], *, process: subprocess.Popen[str] | None = None
) -> str:
    pid = claim["worker"]["pid"]
    if (
        process is not None
        and process.pid == claim["worker"]["parent_pid"]
        and process.poll() is None
    ):
        return "running"
    process_row = claim["worker"]["process"]
    recorded = windows_liveness.RecordedProcess(
        "epoch002_bootstrap_worker",
        pid,
        creation_time_filetime=process_row["creation_time_100ns"],
        executable_path=process_row["kernel_executable_path"],
        role="worker",
    )
    try:
        snapshot = windows_liveness.capture_windows_process_snapshot((recorded,))
    except windows_liveness.ProcessLivenessError as exc:
        raise RecoveryRefused("bootstrap worker liveness is ambiguous") from exc
    rows = snapshot.get("classification", {}).get("recorded_processes", [])
    if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
        raise RecoveryRefused("bootstrap worker liveness result is malformed")
    classification = rows[0].get("classification")
    if classification == "dead_proven":
        return "dead"
    if classification in {"live", "ambiguous", "pid_reused"}:
        return "live_or_identity_ambiguous"
    raise RecoveryRefused("bootstrap worker liveness classification is unknown")


def _postmortem_runtime_temp_attestation(
    expected_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Attest the fixed runtime directory without creating or cleaning it.

    A controller may close the narrow lower-complete/terminal-missing window
    only when the worker left no capture file or other runtime residue.  The
    check deliberately stops at the first directory entry and never opens,
    decodes, deletes, or repairs residual content.
    """

    path = RUNTIME_TEMP
    try:
        if not os.path.lexists(path):
            raise RecoveryRefused("postmortem runtime temp is missing")
        before = _runtime_temp_directory_identity(
            path, what="postmortem runtime temp"
        )
        if _canonical(before) != _canonical(expected_identity):
            raise RecoveryRefused(
                "postmortem runtime temp directory identity changed"
            )
        root = Path(before["path"])
        with os.scandir(root) as entries:
            if next(entries, None) is not None:
                raise RecoveryRefused(
                    "postmortem runtime temp is not exactly empty"
                )
        after = _runtime_temp_directory_identity(
            path, what="postmortem runtime temp"
        )
        if _canonical(after) != _canonical(before):
            raise RecoveryRefused(
                "postmortem runtime temp changed during empty-directory proof"
            )
    except RecoveryRefused:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise RecoveryRefused(
            "postmortem runtime temp cannot be attested as empty"
        ) from exc
    return {
        **before,
        "entry_count": 0,
        "inventory_digest": sha256_bytes(_canonical([])),
    }


def _postmortem_worker_expectation(claim: Mapping[str, Any]) -> dict[str, Any]:
    process_row = claim["worker"]["process"]
    return {
        "record_id": "epoch002_bootstrap_worker",
        "pid": process_row["pid"],
        # The claimed bootstrap owns the one-use epoch.  The liveness gate's
        # owner role is therefore the precise process-lifecycle role here,
        # even though the bootstrap contract calls the process a worker.
        "role": "owner",
        "creation_time_filetime": str(process_row["creation_time_100ns"]),
        "executable_path": process_row["kernel_executable_path"],
    }


def _same_resolved_process_path(left: object, right: object, *, what: str) -> bool:
    if type(left) is not str or type(right) is not str:
        raise RecoveryRefused(f"{what} is not a pair of process paths")
    try:
        left_path = Path(left).resolve(strict=True)
        right_path = Path(right).resolve(strict=True)
    except OSError as exc:
        raise RecoveryRefused(f"{what} cannot be resolved") from exc
    return os.path.normcase(str(left_path)) == os.path.normcase(str(right_path))


def _validate_postmortem_liveness(
    value: object,
    *,
    claim: Mapping[str, Any],
    controller_process: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    row = _expect_keys(value, {"sha256", "report"}, what="postmortem liveness")
    if type(row["report"]) is not dict:
        raise RecoveryRefused("postmortem liveness report is not an object")
    if (
        _expect_sha(row["sha256"], what="postmortem liveness SHA256")
        != sha256_bytes(_canonical(row["report"]))
    ):
        raise RecoveryRefused("postmortem liveness report hash differs")
    try:
        classified = windows_liveness.assert_windows_stability_gate(row["report"])
    except windows_liveness.ProcessLivenessError as exc:
        raise RecoveryRefused(
            "postmortem liveness does not prove the worker dead twice"
        ) from exc
    if _canonical(classified) != _canonical(row["report"]):
        raise RecoveryRefused("postmortem liveness classification is not canonical")
    stability = classified.get("stability", {})
    expected_worker = _postmortem_worker_expectation(claim)
    snapshots = classified.get("snapshots")
    pinned_python = _expect_keys(
        authority.get("pinned_python"),
        {"path", "sha256"},
        what="postmortem pinned Python authority",
    )
    base_python = _expect_keys(
        controller_process.get("base_interpreter"),
        {"path", "sha256"},
        what="postmortem controller base interpreter",
    )
    if (
        type(stability) is not dict
        or stability.get("verdict") != "pass"
        or stability.get("all_recorded_processes_dead_twice") is not True
        or stability.get("controller_same_process") is not True
        or type(snapshots) is not list
        or len(snapshots) != 2
        or not _same_resolved_process_path(
            classified.get("expected_controller_sys_executable_path"),
            pinned_python["path"],
            what="postmortem expected controller launcher",
        )
        or not _same_resolved_process_path(
            controller_process.get("kernel_executable_path"),
            base_python["path"],
            what="postmortem controller kernel/base path",
        )
        or controller_process.get("kernel_executable_sha256")
        != base_python["sha256"]
        or sha256_file(Path(base_python["path"])) != base_python["sha256"]
    ):
        raise RecoveryRefused("postmortem liveness proof is incomplete")
    for expected_index, snapshot in enumerate(snapshots, start=1):
        snapshot_controller = (
            snapshot.get("controller") if type(snapshot) is dict else None
        )
        classification = (
            snapshot.get("classification") if type(snapshot) is dict else None
        )
        classified_controller = (
            classification.get("controller")
            if type(classification) is dict
            else None
        )
        if (
            type(snapshot) is not dict
            or snapshot.get("observation_index") != expected_index
            or snapshot.get("recorded_processes") != [expected_worker]
            or type(snapshot_controller) is not dict
            or snapshot_controller.get("pid") != controller_process["pid"]
            or not _same_resolved_process_path(
                snapshot_controller.get("declared_sys_executable_path"),
                pinned_python["path"],
                what=f"postmortem snapshot {expected_index} declared launcher",
            )
            or type(classified_controller) is not dict
            or classified_controller.get("pid") != controller_process["pid"]
            or classified_controller.get("classification") != "running"
            or classified_controller.get("observed_creation_time_filetime")
            != str(controller_process["creation_time_100ns"])
            or not _same_resolved_process_path(
                classified_controller.get("observed_executable_path"),
                controller_process["kernel_executable_path"],
                what=f"postmortem snapshot {expected_index} kernel executable",
            )
            or not _same_resolved_process_path(
                classified_controller.get("declared_sys_executable_path"),
                pinned_python["path"],
                what=f"postmortem snapshot {expected_index} classified launcher",
            )
        ):
            raise RecoveryRefused(
                "postmortem liveness proof is not bound to the claimed worker"
            )
    return row


def _postmortem_worker_death_proof(
    claim: Mapping[str, Any], *, authority: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Capture the worker's absence twice and bind the observing controller."""

    process_row = claim["worker"]["process"]
    recorded = (
        windows_liveness.RecordedProcess(
            "epoch002_bootstrap_worker",
            process_row["pid"],
            creation_time_filetime=process_row["creation_time_100ns"],
            executable_path=process_row["kernel_executable_path"],
            role="owner",
        ),
    )
    controller_process = _controller_process_attestation(authority)
    try:
        report = windows_liveness.capture_windows_process_stability(
            recorded, controller_pid=controller_process["pid"]
        )
        classified = windows_liveness.assert_windows_stability_gate(report)
    except windows_liveness.ProcessLivenessError as exc:
        raise RecoveryRefused(
            "postmortem liveness did not prove the worker dead twice"
        ) from exc
    if _canonical(classified) != _canonical(report):
        raise RecoveryRefused("postmortem liveness report changed on reclassification")
    liveness = {
        "sha256": sha256_bytes(_canonical(report)),
        "report": dict(report),
    }
    _validate_postmortem_liveness(
        liveness,
        claim=claim,
        controller_process=controller_process,
        authority=authority,
    )
    return controller_process, liveness


def _postmortem_lower_binding(material: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "material_sha256": sha256_bytes(_canonical(material)),
        "counts": dict(material["counts"]),
        "new_lease_token": material["new_token"],
        "lower_report_sha256": material["lower_report"]["sha256"],
        "event_chain_digest": material["events"]["chain_digest"],
        "job_tree_digest_set": material["jobs"]["tree_digest_set"],
    }


def _bootstrap_postmortem_payload(
    *,
    incident: Mapping[str, Any],
    invocation: Mapping[str, Any],
    invocation_sha: str,
    claim: Mapping[str, Any],
    claim_sha: str,
    material: Mapping[str, Any],
    controller_process: Mapping[str, Any],
    liveness: Mapping[str, Any],
    runtime_temp: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **_base_record("bootstrap_postmortem_completion"),
        "bootstrap_schema_version": BOOTSTRAP_CONTRACT_SCHEMA_VERSION,
        "status": "complete_without_worker_terminal",
        "incident": {
            "record_digest": incident["record_digest"],
            "controller_authority_sha256": sha256_bytes(
                _canonical(incident["authority"])
            ),
        },
        "invocation": _record_binding(invocation, invocation_sha),
        "claim": {
            **_record_binding(claim, claim_sha),
            "twins_complete": True,
        },
        "controller_process": dict(controller_process),
        "worker_death": {
            "verdict": "dead_proven_twice",
            "worker": _postmortem_worker_expectation(claim),
            "liveness": dict(liveness),
        },
        "terminal_presence": {"original": False, "copy": False},
        "runtime_temp": dict(runtime_temp),
        "lower_completion": _postmortem_lower_binding(material),
        "output_capture": {
            "availability": "unavailable",
            "reason": "worker_exited_after_lower_completion_before_terminal_publication",
            "stdout": None,
            "stderr": None,
        },
        "automatic_retry_allowed": False,
    }


def _validate_bootstrap_postmortem_document(
    document: Mapping[str, Any],
    *,
    incident: Mapping[str, Any],
    invocation: Mapping[str, Any],
    invocation_sha: str,
    claim: Mapping[str, Any],
    claim_sha: str,
    material: Mapping[str, Any],
) -> None:
    expected_keys = set(_base_record("bootstrap_postmortem_completion")) | {
        "bootstrap_schema_version",
        "status",
        "incident",
        "invocation",
        "claim",
        "controller_process",
        "worker_death",
        "terminal_presence",
        "runtime_temp",
        "lower_completion",
        "output_capture",
        "automatic_retry_allowed",
        "record_digest",
    }
    _expect_keys(document, expected_keys, what="bootstrap postmortem completion")
    controller_process = _validate_controller_process_attestation(
        document["controller_process"],
        base=incident["authority"]["base_python"],
        what="postmortem controller process",
    )
    death = _expect_keys(
        document["worker_death"],
        {"verdict", "worker", "liveness"},
        what="postmortem worker death",
    )
    if death["verdict"] != "dead_proven_twice":
        raise RecoveryRefused("postmortem worker death verdict differs")
    _validate_postmortem_liveness(
        death["liveness"],
        claim=claim,
        controller_process=controller_process,
        authority=incident["authority"],
    )
    expected_runtime = _postmortem_runtime_temp_attestation(
        invocation["runtime_temp"]
    )
    expected = _seal(
        _bootstrap_postmortem_payload(
            incident=incident,
            invocation=invocation,
            invocation_sha=invocation_sha,
            claim=claim,
            claim_sha=claim_sha,
            material=material,
            controller_process=controller_process,
            liveness=death["liveness"],
            runtime_temp=expected_runtime,
        )
    )
    if _canonical(document) != _canonical(expected):
        raise RecoveryRefused(
            "bootstrap postmortem completion differs from exact revalidation"
        )


def _load_bootstrap_postmortem_available(
    *,
    incident: Mapping[str, Any],
    invocation: Mapping[str, Any],
    invocation_sha: str,
    claim: Mapping[str, Any],
    claim_sha: str,
    material: Mapping[str, Any],
) -> tuple[dict[str, Any], str, bool]:
    document, file_sha, twins_complete = _load_available_twins(
        BOOTSTRAP_POSTMORTEM_FILE,
        record_type="bootstrap_postmortem_completion",
    )
    _validate_bootstrap_postmortem_document(
        document,
        incident=incident,
        invocation=invocation,
        invocation_sha=invocation_sha,
        claim=claim,
        claim_sha=claim_sha,
        material=material,
    )
    return document, file_sha, twins_complete


_PERMANENT_BOOTSTRAP_STOP_STATES = frozenset(
    {
        "partial_invocation",
        "history_without_invocation",
        "invocation_unclaimed",
        "partial_claim",
        "partial_terminal",
        "partial_claim_and_terminal",
        "partial_claim_terminal_refused",
        "partial_claim_terminal_complete",
        "partial_claim_and_postmortem",
        "terminal_without_claim",
        "partial_terminal_without_claim",
        "postmortem_without_complete_claim",
        "partial_postmortem",
        "terminal_and_postmortem_conflict",
        "terminal_refused",
        "claimed_worker_dead_second_interruption",
        "claimed_worker_dead_noncomplete_terminal",
    }
)


def _is_permanent_bootstrap_stop(state: str) -> bool:
    return state in _PERMANENT_BOOTSTRAP_STOP_STATES


def _bootstrap_state(
    *, process: subprocess.Popen[str] | None = None
) -> dict[str, Any]:
    invocation_presence = _twin_presence(BOOTSTRAP_INVOCATION_FILE)
    claim_presence = _twin_presence(BOOTSTRAP_CLAIM_FILE)
    terminal_presence = _twin_presence(BOOTSTRAP_TERMINAL_FILE)
    postmortem_presence = _twin_presence(BOOTSTRAP_POSTMORTEM_FILE)
    if any(terminal_presence) and any(postmortem_presence):
        _load_available_twins(
            BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal"
        )
        _load_available_twins(
            BOOTSTRAP_POSTMORTEM_FILE,
            record_type="bootstrap_postmortem_completion",
        )
        return {
            "state": "terminal_and_postmortem_conflict",
            "terminal_twins_present": sum(terminal_presence),
            "postmortem_twins_present": sum(postmortem_presence),
            "automatic_retry_allowed": False,
        }
    if any(invocation_presence) and not all(invocation_presence):
        invocation, invocation_sha, _ = _load_available_twins(
            BOOTSTRAP_INVOCATION_FILE, record_type="bootstrap_invocation"
        )
        return {
            "state": "partial_invocation",
            "invocation": invocation,
            "invocation_file_sha256": invocation_sha,
            "automatic_retry_allowed": False,
        }
    if not all(invocation_presence):
        if any(claim_presence):
            _load_available_twins(
                BOOTSTRAP_CLAIM_FILE, record_type="bootstrap_claim"
            )
        if any(terminal_presence):
            _load_available_twins(
                BOOTSTRAP_TERMINAL_FILE, record_type="bootstrap_terminal"
            )
        if any(postmortem_presence):
            _load_available_twins(
                BOOTSTRAP_POSTMORTEM_FILE,
                record_type="bootstrap_postmortem_completion",
            )
        if any(claim_presence) or any(terminal_presence) or any(postmortem_presence):
            return {
                "state": "history_without_invocation",
                "claim_twins_present": sum(claim_presence),
                "terminal_twins_present": sum(terminal_presence),
                "postmortem_twins_present": sum(postmortem_presence),
                "automatic_retry_allowed": False,
            }
        return {"state": "not_invoked", "automatic_retry_allowed": False}
    invocation, invocation_sha = _load_bootstrap_invocation()
    if not any(claim_presence):
        if any(postmortem_presence):
            postmortem, postmortem_sha, _ = _load_available_twins(
                BOOTSTRAP_POSTMORTEM_FILE,
                record_type="bootstrap_postmortem_completion",
            )
            return {
                "state": "postmortem_without_complete_claim",
                "invocation": invocation,
                "postmortem": postmortem,
                "postmortem_file_sha256": postmortem_sha,
                "automatic_retry_allowed": False,
            }
        if any(terminal_presence):
            terminal, terminal_sha, terminal_twins_complete = (
                _load_bootstrap_terminal_available(
                    invocation,
                    invocation_sha,
                    None,
                    None,
                    claim_twins_complete=None,
                )
            )
            return {
                "state": (
                    "terminal_without_claim"
                    if terminal_twins_complete
                    else "partial_terminal_without_claim"
                ),
                "invocation": invocation,
                "terminal": terminal,
                "terminal_file_sha256": terminal_sha,
                "automatic_retry_allowed": False,
            }
        return {
            "state": "invocation_unclaimed",
            "invocation": invocation,
            "automatic_retry_allowed": False,
        }
    claim, claim_sha, claim_twins_complete = _load_bootstrap_claim_available(
        invocation, invocation_sha
    )
    if any(terminal_presence):
        terminal, terminal_sha, terminal_twins_complete = (
            _load_bootstrap_terminal_available(
                invocation,
                invocation_sha,
                claim,
                claim_sha,
                claim_twins_complete=claim_twins_complete,
            )
        )
        if not claim_twins_complete and not terminal_twins_complete:
            state = "partial_claim_and_terminal"
        elif not claim_twins_complete:
            state = "partial_claim_terminal_" + terminal["status"]
        elif not terminal_twins_complete:
            state = "partial_terminal"
        else:
            state = (
                "terminal_complete"
                if terminal["status"] == "complete"
                else "terminal_refused"
            )
        return {
            "state": state,
            "invocation": invocation,
            "claim": claim,
            "claim_twins_complete": claim_twins_complete,
            "terminal": terminal,
            "terminal_file_sha256": terminal_sha,
            "terminal_twins_complete": terminal_twins_complete,
            "automatic_retry_allowed": False,
        }
    if any(postmortem_presence):
        if not claim_twins_complete:
            postmortem, postmortem_sha, _ = _load_available_twins(
                BOOTSTRAP_POSTMORTEM_FILE,
                record_type="bootstrap_postmortem_completion",
            )
            return {
                "state": "partial_claim_and_postmortem",
                "invocation": invocation,
                "claim": claim,
                "postmortem": postmortem,
                "postmortem_file_sha256": postmortem_sha,
                "automatic_retry_allowed": False,
            }
        incident, _, _, _ = _load_adjudication()
        material = _validate_lower_completion(incident)
        postmortem, postmortem_sha, twins_complete = (
            _load_bootstrap_postmortem_available(
                incident=incident,
                invocation=invocation,
                invocation_sha=invocation_sha,
                claim=claim,
                claim_sha=claim_sha,
                material=material,
            )
        )
        return {
            "state": "postmortem_complete" if twins_complete else "partial_postmortem",
            "invocation": invocation,
            "invocation_file_sha256": invocation_sha,
            "claim": claim,
            "claim_file_sha256": claim_sha,
            "postmortem": postmortem,
            "postmortem_file_sha256": postmortem_sha,
            "postmortem_twins_complete": twins_complete,
            "material": material,
            "automatic_retry_allowed": False,
        }
    if not claim_twins_complete:
        return {
            "state": "partial_claim",
            "invocation": invocation,
            "claim": claim,
            "claim_file_sha256": claim_sha,
            "claim_twins_complete": False,
            "automatic_retry_allowed": False,
        }
    lifecycle = _claimed_worker_lifecycle(claim, process=process)
    if lifecycle in {"running", "live_or_identity_ambiguous"}:
        return {
            "state": "claimed_worker_" + lifecycle,
            "invocation": invocation,
            "claim": claim,
            "automatic_retry_allowed": False,
        }
    reports = _lower_reports()
    if not reports:
        return {
            "state": "claimed_worker_dead_second_interruption",
            "invocation": invocation,
            "claim": claim,
            "automatic_retry_allowed": False,
        }
    if len(reports) != 1 or next(iter(reports.values()))[2].get("status") != "complete":
        return {
            "state": "claimed_worker_dead_noncomplete_terminal",
            "invocation": invocation,
            "claim": claim,
            "automatic_retry_allowed": False,
        }
    incident, _, _, _ = _load_adjudication()
    _assert_current_controller_authority(incident)
    try:
        material = _validate_lower_completion(incident)
    except RecoveryRefused:
        return {
            "state": "claimed_worker_dead_noncomplete_terminal",
            "invocation": invocation,
            "claim": claim,
            "automatic_retry_allowed": False,
        }
    runtime_temp = _postmortem_runtime_temp_attestation(
        invocation["runtime_temp"]
    )
    controller_process, liveness = _postmortem_worker_death_proof(
        claim, authority=incident["authority"]
    )
    return {
        "state": "postmortem_seal_required",
        "invocation": invocation,
        "invocation_file_sha256": invocation_sha,
        "claim": claim,
        "claim_file_sha256": claim_sha,
        "material": material,
        "controller_process": controller_process,
        "liveness": liveness,
        "runtime_temp": runtime_temp,
        "automatic_retry_allowed": False,
    }


def _second_interruption_present() -> bool:
    if not _record_presence(TRANSITION_COMPLETION_FILE):
        return False
    state = _bootstrap_state()["state"]
    return _is_permanent_bootstrap_stop(state)


def _validate_spawned_worker_identity(
    claim: Mapping[str, Any], process: subprocess.Popen[str]
) -> None:
    """Bind a successful claim to this controller's exact spawned process."""

    worker = claim["worker"]
    if (
        worker["parent_pid"] != process.pid
        or worker["parent_process"]["parent_pid"] != os.getpid()
    ):
        raise RecoveryRefused("bootstrap claim does not identify the spawned worker")


def _validate_process_attestation(
    value: object,
    *,
    pinned: object,
    what: str,
) -> dict[str, Any]:
    launcher = _expect_keys(pinned, {"path", "sha256"}, what=f"{what} launcher")
    row = _expect_keys(
        value,
        {
            "pid",
            "parent_pid",
            "kernel_executable_path",
            "kernel_executable_sha256",
            "creation_time_100ns",
            "pinned_launcher",
        },
        what=what,
    )
    if (
        type(row["pid"]) is not int
        or row["pid"] <= 0
        or type(row["parent_pid"]) is not int
        or row["parent_pid"] <= 0
        or type(row["kernel_executable_path"]) is not str
        or Path(row["kernel_executable_path"]).resolve()
        != Path(launcher["path"]).resolve()
        or _expect_sha(row["kernel_executable_sha256"], what=f"{what} executable hash")
        != launcher["sha256"]
        or type(row["creation_time_100ns"]) is not int
        or row["creation_time_100ns"] <= 0
        or row["pinned_launcher"] != launcher
    ):
        raise RecoveryRefused(f"{what} does not identify the pinned controller")
    return row


def _validate_controller_process_attestation(
    value: object, *, base: object, what: str
) -> dict[str, Any]:
    interpreter = _expect_keys(base, {"path", "sha256"}, what=f"{what} interpreter")
    row = _expect_keys(
        value,
        {
            "pid",
            "kernel_executable_path",
            "kernel_executable_sha256",
            "creation_time_100ns",
            "base_interpreter",
        },
        what=what,
    )
    if (
        type(row["pid"]) is not int
        or row["pid"] <= 0
        or type(row["kernel_executable_path"]) is not str
        or Path(row["kernel_executable_path"]).resolve()
        != Path(interpreter["path"]).resolve()
        or _expect_sha(row["kernel_executable_sha256"], what=f"{what} executable hash")
        != interpreter["sha256"]
        or type(row["creation_time_100ns"]) is not int
        or row["creation_time_100ns"] <= 0
        or row["base_interpreter"] != interpreter
    ):
        raise RecoveryRefused(f"{what} does not identify the pinned base interpreter")
    return row


def _controller_process_attestation(authority: Mapping[str, Any]) -> dict[str, Any]:
    """Capture this invocation's durable kernel process identity."""

    try:
        identity = windows_liveness.capture_windows_process_identity()
    except windows_liveness.ProcessLivenessError as exc:
        raise RecoveryRefused("cannot attest the bootstrap controller process") from exc
    base = authority["base_python"]
    row = {
        **identity,
        "kernel_executable_sha256": sha256_file(
            Path(identity["kernel_executable_path"])
        ),
        "base_interpreter": dict(base),
    }
    return _validate_controller_process_attestation(
        row, base=base, what="bootstrap invocation controller"
    )


def _invoke_bootstrap() -> dict[str, Any]:
    incident, incident_sha, epoch_terminal, epoch_terminal_sha = _load_adjudication()
    completion, completion_sha = _load_transition_completion()
    intent, intent_sha = _load_twins(
        TRANSITION_INTENT_FILE, record_type="transition_intent"
    )
    if _bootstrap_state()["state"] != "not_invoked":
        raise RecoveryRefused("the one-use bootstrap invocation was already consumed")
    authority = _controller_authority()
    if not _authority_lineage_matches(authority, incident["authority"]):
        raise RecoveryRefused("controller authority differs before bootstrap invocation")
    bundle, child_transport = _verified_child_bundle(
        relative_path="scripts/week8_exp2a_recovery_worker.py",
        logical_path=BOOTSTRAP_SCRIPT,
    )
    if child_transport["source_sha256"] != authority["bootstrap_worker"]["sha256"]:
        raise RecoveryRefused("bootstrap transport differs from controller authority")
    runtime = _prepare_empty_runtime_temp(
        RUNTIME_TEMP, what="D-161 recovery runtime temp"
    )
    runtime_identity = _runtime_temp_directory_identity(
        runtime, what="D-161 recovery runtime temp"
    )
    prelaunch = _bootstrap_prelaunch_state()
    controller_process = _controller_process_attestation(authority)
    invocation = _publish_twins_exclusive(
        BOOTSTRAP_INVOCATION_FILE,
        _bootstrap_invocation_payload(
            incident,
            incident_sha,
            epoch_terminal,
            epoch_terminal_sha,
            intent,
            intent_sha,
            completion,
            completion_sha,
            prelaunch,
            controller_process,
            runtime_identity,
            child_transport,
        ),
    )
    invocation_digest = invocation["record_digest"]
    environment = _sanitized_subprocess_environment(
        runtime,
        invocation_digest=invocation_digest,
        child_bundle_digest=child_transport["bundle_sha256"],
    )
    # This is deliberately the final operation before process creation.  It
    # rechecks Git state and every tracked source/interpreter hash after the
    # one-use invocation is durable.
    final_authority = _controller_authority()
    if (
        _canonical(final_authority) != _canonical(authority)
        or not _authority_lineage_matches(final_authority, incident["authority"])
    ):
        raise RecoveryRefused("controller authority changed before bootstrap spawn")
    try:
        process = subprocess.Popen(
            [
                str(PINNED_PYTHON),
                "-I",
                "-S",
                "-B",
                "-X",
                "utf8",
                "-c",
                CHILD_BOOTSTRAP_LITERAL,
            ],
            cwd=EXECUTION_WORKTREE,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
    except OSError as exc:
        raise RecoveryRefused("could not start fixed recovery bootstrap") from exc
    stdout, stderr = process.communicate(input=bundle)
    try:
        stdout_text = stdout.decode("utf-8", errors="strict")
        stderr_text = stderr.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RecoveryRefused("bootstrap emitted non-UTF-8 bytes") from exc
    state = _bootstrap_state(process=process)
    if state["state"] == "postmortem_seal_required":
        _validate_spawned_worker_identity(state["claim"], process)
        return {
            "bootstrap_schema_version": BOOTSTRAP_CONTRACT_SCHEMA_VERSION,
            "status": "postmortem_seal_required",
            "lease_token": state["material"]["new_token"],
            "scientific_values_emitted": False,
        }
    if process.returncode != 0:
        raise RecoveryRefused(
            "the one authorized recovery epoch stopped; no re-entry is allowed; "
            f"stdout SHA256={sha256_bytes(stdout)}, stderr SHA256={sha256_bytes(stderr)}"
        )
    if stderr_text:
        raise RecoveryRefused(
            "bootstrap emitted stderr; stderr SHA256=" + sha256_bytes(stderr)
        )
    if state["state"] != "terminal_complete":
        raise RecoveryRefused("bootstrap exited zero without a complete terminal record")
    _validate_spawned_worker_identity(state["claim"], process)
    result = _strict_json_line(stdout_text, what="bootstrap")
    result = _expect_keys(
        result,
        {
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
        },
        what="bootstrap result",
    )
    claim = state["claim"]
    terminal = state["terminal"]
    output_capture = _validate_output_capture(
        result["output_capture"], what="bootstrap result output capture"
    )
    if (
        result["bootstrap_schema_version"] != BOOTSTRAP_CONTRACT_SCHEMA_VERSION
        or result["status"] != "complete"
        or result["counts"] != EXPECTED_RECOVERY_COUNTS
        or result["lease_token"] == OLD_LEASE_TOKEN
        or _HEX32.fullmatch(result["lease_token"]) is None
        or _HEX64.fullmatch(result["report_sha256"]) is None
        or result["script_sha256"] != child_transport["source_sha256"]
        or result["invocation_record_digest"] != invocation["record_digest"]
        or result["invocation_file_sha256"]
        != sha256_file(_record_paths(BOOTSTRAP_INVOCATION_FILE)[0])
        or result["claim_record_digest"] != claim["record_digest"]
        or result["claim_file_sha256"]
        != sha256_file(_record_paths(BOOTSTRAP_CLAIM_FILE)[0])
        or result["terminal_record_digest"] != terminal["record_digest"]
        or result["terminal_file_sha256"] != state["terminal_file_sha256"]
        or output_capture != terminal["operational_result"]["output_capture"]
        or result["scientific_values_emitted"] is not False
    ):
        raise RecoveryRefused("bootstrap result does not prove the exact recovery epoch")
    return result


def recover() -> dict[str, Any]:
    """Consume the one D-161 transition and run the continuation epoch once."""

    incident, incident_sha, _, terminal_sha = _load_adjudication()
    if _record_presence(RECOVERY_COMPLETION_FILE) or P._receipt_present("launch"):
        raise RecoveryRefused("recovery is already sealed; re-entry is prohibited")
    intent_present = _record_presence(TRANSITION_INTENT_FILE)
    transition_present = _record_presence(TRANSITION_COMPLETION_FILE)
    if intent_present and not transition_present:
        raise RecoveryRefused("ownership transition was interrupted; re-entry is prohibited")
    if transition_present:
        _load_transition_completion()
        bootstrap_state = _bootstrap_state()["state"]
        if bootstrap_state == "not_invoked":
            bootstrap = _invoke_bootstrap()
            material = _validate_lower_completion(incident)
            if bootstrap["lease_token"] != material["new_token"]:
                raise RecoveryRefused(
                    "bootstrap token differs from validated lower evidence"
                )
            return {
                "command": "recover",
                "status": "recovery_complete_ready_to_seal",
                "counts": material["counts"],
                "new_lease_token": material["new_token"],
            }
        if bootstrap_state in {
            "claimed_worker_running",
            "claimed_worker_live_or_identity_ambiguous",
        }:
            return {
                "command": "recover",
                "status": "continuation_epoch_running_or_identity_ambiguous",
                "automatic_retry_allowed": False,
                "scientific_values_emitted": False,
            }
        if _is_permanent_bootstrap_stop(bootstrap_state):
            raise RecoveryRefused("the continuation epoch was interrupted; no second recovery")
        if bootstrap_state in {"postmortem_seal_required", "postmortem_complete"}:
            raise RecoveryRefused(
                "the continuation invocation was consumed; use seal, never recover again"
            )
        material = _validate_lower_completion(incident)
        return {
            "command": "recover",
            "status": "recovery_complete_ready_to_seal",
            "counts": material["counts"],
            "new_lease_token": material["new_token"],
        }

    initial_authority = _controller_authority()
    if not _authority_lineage_matches(initial_authority, incident["authority"]):
        raise RecoveryRefused("controller authority differs from the incident record")
    active = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / f"{Plan.COMMON_LEASE_NAME}.lease.json"
    )
    guard = Supervisor._lease_guard_path(active, Plan.COMMON_LEASE_NAME)
    with Supervisor._lease_transition_lock(guard):
        if _record_presence(TRANSITION_INTENT_FILE) or _record_presence(
            TRANSITION_COMPLETION_FILE
        ):
            raise RecoveryRefused(
                "ownership transition was consumed by another controller"
            )
        transition = _transition_material(incident, incident_sha, terminal_sha)
        current, _ = _capture_twice()
        if _canonical(current) != _canonical(incident["inventory"]):
            raise RecoveryRefused("production state changed after incident adjudication")
        final_authority = _controller_authority()
        if (
            _canonical(final_authority) != _canonical(initial_authority)
            or not _authority_lineage_matches(
                final_authority, incident["authority"]
            )
        ):
            raise RecoveryRefused("controller authority changed before transition intent")
        liveness = _quiescent_liveness()
        intent = _publish_twins(
            TRANSITION_INTENT_FILE,
            {
                **_base_record("transition_intent"),
                "status": "ownership_transition_intended",
                "authorization": transition,
                "liveness_stability_reports": [
                    {
                        "sha256": sha256_bytes(_canonical(liveness)),
                        "report": liveness,
                    }
                ],
            },
        )
        intent_sha = sha256_file(_record_paths(TRANSITION_INTENT_FILE)[0])
        archive = _orphan_archive_path()
        _archive_orphan_lease(active, archive)
        partial_source = P.SYNC_ROOT / "jobs" / HIDDEN_PARTIAL_NAME
        quarantine = _quarantine_partial(
            partial_source,
            incident["inventory"]["jobs"]["hidden_partial"],
        )
        completion = _publish_twins(
            TRANSITION_COMPLETION_FILE,
            {
                **_base_record("transition_completion"),
                "status": "ownership_transition_complete",
                "authorization": transition,
                "transition_intent": {
                    "record_digest": intent["record_digest"],
                    "file_sha256": intent_sha,
                },
                "orphan_lease_archive": {
                    "path": str(archive.resolve()),
                    "sha256": sha256_file(archive),
                    "classification": "orphaned_after_liveness_proof",
                },
                "quarantine": quarantine,
            },
        )
    bootstrap = _invoke_bootstrap()
    material = _validate_lower_completion(incident)
    if bootstrap["lease_token"] != material["new_token"]:
        raise RecoveryRefused("bootstrap token differs from validated lower evidence")
    return {
        "command": "recover",
        "status": "recovery_complete_ready_to_seal",
        "transition_digest": completion["record_digest"],
        "counts": material["counts"],
        "new_lease_token": material["new_token"],
    }


def _checkpoint_documents() -> dict[str, tuple[dict[str, Any], str]]:
    readers = _parent_readers()
    checkpoint_reader, controls = readers["checkpoints"], readers["controls"]
    # Completion is a released-state operation; an active token must not be
    # accepted through the ordinary historical lookup's active-lease branch.
    Launch._no_active_lease()
    local_dir = P.OUTPUT_ROOT / Plan.START_DIRECTORY
    copy_dir = P.SYNC_ROOT / Plan.START_DIRECTORY
    local = {path.name: path for path in _directory_entries(local_dir, what="checkpoints")}
    copied = {path.name: path for path in _directory_entries(copy_dir, what="checkpoint copies")}
    names = set(local)
    old_name = f"{OLD_LEASE_TOKEN}.json"
    if names != set(copied):
        raise RecoveryRefused("checkpoint original/copy inventories differ")
    if len(names) != EXPECTED_FINAL_COUNTS["checkpoints"] or old_name not in names:
        raise RecoveryRefused("completed recovery must contain exactly the original and one new checkpoint")
    if any(_TOKEN_FILE.fullmatch(name) is None for name in names):
        raise RecoveryRefused("checkpoint filename is not a canonical token")
    new_name = next(iter(names - {old_name}))
    new_token = Path(new_name).stem
    control = P._load_control(EXECUTION_COMMIT, monitor_only=True)
    old, old_sha = controls.historical_checkpoint_material(control)
    if (
        old_sha != EXPECTED_HASHES["old_checkpoint"]
        or old["checkpoint_digest"] != EXPECTED_OLD_CHECKPOINT_DIGEST
        or old["exp2a_repair_start_schema_version"] != 1
        or old["plan_digest"] != EXPECTED_PLAN_DIGEST
        or old["preflight"]["sha256"] != EXPECTED_HASHES["preflight_report"]
        or old["source_ledger"]["sha256"] != EXPECTED_HASHES["source_ledger_file"]
        or old["lease"]["token"] != OLD_LEASE_TOKEN
        or old["lease"]["sha256"] != EXPECTED_HASHES["old_lease"]
        or _same_bytes(local[old_name], copied[old_name], what="original checkpoint") != old_sha
        or _canonical(read_json(local[old_name])) != _canonical(old)
    ):
        raise RecoveryRefused("original checkpoint is not preserved exactly")
    lease = Launch._historical_lease_record(new_token)
    expected, expected_context = checkpoint_reader._new_document(old, lease)
    document, raw = checkpoint_reader._current_twins(Path(Plan.START_DIRECTORY) / new_name)
    context_name = checkpoint_reader.relocation_binding()["context_file"]
    context, _ = checkpoint_reader._current_twins(Path(context_name))
    if (
        _canonical(document) != _canonical(expected)
        or _canonical(context) != _canonical(expected_context)
        or document["execution_context_digest"] == old["execution_context_digest"]
        or lease["token"] != new_token
        or document["exp2a_repair_start_schema_version"] != 2
    ):
        raise RecoveryRefused("relocated checkpoint/context differs from original scientific settings or admitted provenance")
    digest = _same_bytes(local[new_name], copied[new_name], what="relocated checkpoint")
    if digest != sha256_bytes(raw):
        raise RecoveryRefused("relocated checkpoint changed during independent validation")
    if (
        {p.name for p in _directory_entries(local_dir, what="checkpoints")} != names
        or {p.name for p in _directory_entries(copy_dir, what="checkpoint copies")} != names
        or controls.historical_checkpoint_material(control) != (old, old_sha)
        or checkpoint_reader._current_twins(Path(Plan.START_DIRECTORY) / new_name) != (document, raw)
        or checkpoint_reader._current_twins(Path(context_name))[0] != context
        or Launch._historical_lease_record(new_token) != lease
    ):
        raise RecoveryRefused("two-epoch checkpoint evidence changed during validation")
    Launch._no_active_lease()
    return {OLD_LEASE_TOKEN: (old, old_sha), new_token: (document, digest)}

def _final_events(
    checkpoints: Mapping[str, tuple[Mapping[str, Any], str]]
) -> tuple[list[dict[str, Any]], str, str, dict[str, str]]:
    readers = _parent_readers()
    event_reader, checkpoint_reader = readers["events"], readers["checkpoints"]
    new_tokens = set(checkpoints) - {OLD_LEASE_TOKEN}
    if OLD_LEASE_TOKEN not in checkpoints or len(checkpoints) != 2 or len(new_tokens) != 1:
        raise RecoveryRefused("recovery has other than one original and one continuation token")
    new_token = next(iter(new_tokens))
    contexts = {token: _expect_sha(row[0]["execution_context_digest"], what="recovery event context")
                for token, row in checkpoints.items()}
    if contexts[OLD_LEASE_TOKEN] == contexts[new_token]:
        raise RecoveryRefused("relocated event epoch must have a distinct verified context")
    local_dir = P.OUTPUT_ROOT / Launch.EVENT_DIRECTORY
    copy_dir = P.SYNC_ROOT / Launch.EVENT_DIRECTORY
    local = {path.name: path for path in _directory_entries(local_dir, what="events")}
    copied = {path.name: path for path in _directory_entries(copy_dir, what="event copies")}
    names = sorted(local)
    if set(local) != set(copied) or names != [
        f"{index:06d}.json" for index in range(EXPECTED_FINAL_COUNTS["events"])
    ]:
        raise RecoveryRefused("completed recovery event stream is not exact/contiguous")
    checkpoint_digests = {
        token: row[0]["checkpoint_digest"] for token, row in checkpoints.items()
    }
    digest_to_token = {value: token for token, value in checkpoint_digests.items()}
    events: list[dict[str, Any]] = []
    previous = None
    started: dict[str, str] = {}
    synced: set[str] = set()
    kinds: Counter[str] = Counter()
    all_jobs = {job.job_id for job in Plan.new_exp2a_jobs()}
    for index, name in enumerate(names):
        _same_bytes(local[name], copied[name], what=f"event {name}")
        row = read_json(local[name])
        expected_token = OLD_LEASE_TOKEN if index < 299 else new_token
        observed = (event_reader.historical_event(index) if index < 299 else
                    checkpoint_reader._current_twins(Path(Launch.EVENT_DIRECTORY) / name)[0])
        if _canonical(row) != _canonical(observed):
            raise RecoveryRefused("parent event differs from its independently verified epoch document")
        # Use the same original seal/schema primitive with the independently
        # verified epoch context. No fitting/environment admission is performed.
        event_reader._original_validate(
            row,
            index=index,
            previous=previous,
            context_digest=contexts[expected_token],
        )
        kind = row["kind"]
        job_id = row["job_id"]
        kinds[kind] += 1
        if kind == "attempt_started":
            token = digest_to_token.get(row["data"]["checkpoint_digest"])
            if token is None or job_id in started or job_id not in all_jobs:
                raise RecoveryRefused("recovery event has duplicate/unknown start")
            if token != expected_token:
                raise RecoveryRefused("recovery start binds the wrong checkpoint epoch")
            started[job_id] = token
        elif kind == "job_synced":
            if job_id not in started or job_id in synced:
                raise RecoveryRefused("recovery sync lacks one unique start")
            synced.add(job_id)
        elif kind in {"attempt_failed", "sync_pending"}:
            raise RecoveryRefused("recovery event stream contains a failure")
        elif kind == "complete":
            if index != EXPECTED_FINAL_COUNTS["events"] - 1 or synced != all_jobs:
                raise RecoveryRefused("completion event does not terminate exact roster")
        events.append(row)
        previous = row["event_digest"]
    expected_kinds = {
        "attempt_started": EXPECTED_FINAL_COUNTS["started"],
        "job_synced": EXPECTED_FINAL_COUNTS["synced"],
        "complete": EXPECTED_FINAL_COUNTS["complete"],
    }
    if dict(kinds) != expected_kinds or set(started) != all_jobs or synced != all_jobs:
        raise RecoveryRefused("final event accounting differs from 261/261/1")
    old_started = {job_id for job_id, token in started.items() if token == OLD_LEASE_TOKEN}
    if (
        len(old_started) != 150
        or ORPHAN_JOB_ID not in old_started
        or len({job_id for job_id, token in started.items() if token == new_token}) != 111
    ):
        raise RecoveryRefused("completed jobs were retrained or untouched jobs were omitted")
    if _event_chain_digest(events[:299]) != EXPECTED_HASHES["old_event_stream"]:
        raise RecoveryRefused("epoch-001 event prefix changed during recovery")
    if sha256_file(local_dir / "000298.json") != EXPECTED_HASHES["old_event_tail_file"]:
        raise RecoveryRefused("epoch-001 event tail changed during recovery")
    if event_reader._inventory() != tuple(names):
        raise RecoveryRefused("final event inventory changed during parent validation")
    for index, name in enumerate(names):
        observed = (event_reader.historical_event(index) if index < 299 else
                    checkpoint_reader._current_twins(Path(Launch.EVENT_DIRECTORY) / name)[0])
        if _canonical(observed) != _canonical(events[index]):
            raise RecoveryRefused("final event changed during parent validation")
    return events, _event_chain_digest(events), new_token, started


def _validate_new_lower_report(
    new_token: str,
    checkpoints: Mapping[str, tuple[Mapping[str, Any], str]],
) -> dict[str, Any]:
    reports = _lower_reports()
    if set(reports) != {new_token}:
        raise RecoveryRefused("recovery must have exactly one continuation lower report")
    local, copied, document, digest = reports[new_token]
    document = _expect_keys(
        document,
        {
            "exp2a_repair_launch_schema_version",
            "status",
            "counts",
            "failure",
            "historical_retrained",
            "preflight",
            "checkpoint",
            "released_lease",
            "lease_release_failure",
        },
        what="continuation lower report",
    )
    if (
        document["exp2a_repair_launch_schema_version"] != 1
        or document["status"] != "complete"
        or document["counts"] != EXPECTED_RECOVERY_COUNTS
        or document["failure"] is not None
        or document["historical_retrained"] is not False
        or document["lease_release_failure"] is not None
    ):
        raise RecoveryRefused("continuation lower report is not exact completion")
    if document["preflight"] != {
        "path": str((P.PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE).resolve()),
        "sha256": EXPECTED_HASHES["preflight_report"],
    }:
        raise RecoveryRefused("continuation lower report changed its preflight pin")
    checkpoint_path = P.OUTPUT_ROOT / Plan.START_DIRECTORY / f"{new_token}.json"
    if document["checkpoint"] != {
        "path": str(checkpoint_path.resolve()),
        "sha256": checkpoints[new_token][1],
    }:
        raise RecoveryRefused("lower report does not bind the continuation checkpoint")
    history = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / "history"
        / f"{Plan.COMMON_LEASE_NAME}.{new_token}.released.json"
    )
    if document["released_lease"] != {
        "token": new_token,
        "history_path": str(history),
    }:
        raise RecoveryRefused("lower report does not bind normal continuation release")
    history = _plain_regular_file(
        history, what="continuation released lease history"
    )
    history_sha = sha256_file(history)
    checkpoint_lease = checkpoints[new_token][0]["lease"]
    lease = _expect_keys(
        read_json(history),
        {
            "schema_version",
            "lease_name",
            "pid",
            "token",
            "timestamp",
            "timestamp_utc",
        },
        what="continuation released lease",
    )
    if (
        lease["schema_version"] != Supervisor.SUPERVISOR_SCHEMA_VERSION
        or lease["lease_name"] != Plan.COMMON_LEASE_NAME
        or lease["token"] != new_token
        or lease["timestamp_utc"] != checkpoint_lease["started_at"]
        or history_sha != checkpoint_lease["sha256"]
    ):
        raise RecoveryRefused(
            "continuation release history is not the checkpoint-bound lease"
        )
    return {
        "path": str(local.resolve()),
        "copy_path": str(copied.resolve()),
        "sha256": digest,
        "released_lease": document["released_lease"],
        "released_lease_sha256": history_sha,
        "released_lease_record": lease,
        "checkpoint_lease": dict(checkpoint_lease),
        "lease_pid": lease["pid"],
    }


def _validate_final_job_trees(
    incident: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    started: Mapping[str, str],
    checkpoints: Mapping[str, tuple[Mapping[str, Any], str]],
    lower: Mapping[str, Any],
) -> dict[str, Any]:
    jobs = Plan.new_exp2a_jobs()
    all_ids = {job.job_id for job in jobs}
    local_root = Plan._project_path(P.OUTPUT_ROOT / "jobs", directory=True)
    durable_root = Plan._project_path(P.SYNC_ROOT / "jobs", directory=True)
    local_entries = _directory_entries(local_root, what="final local jobs")
    durable_entries = _directory_entries(durable_root, what="final durable jobs")
    if (
        {path.name for path in local_entries} != all_ids
        or {path.name for path in durable_entries} != all_ids
        or any(path.name.startswith(".") for path in (*local_entries, *durable_entries))
    ):
        raise RecoveryRefused("final canonical roots are not exactly 261 jobs")
    old_digests = {
        row["job_id"]: row["tree_digest"]
        for row in incident["inventory"]["jobs"]["local_completed"]
    }
    old_durable = {row["job_id"]: row for row in incident["inventory"]["jobs"]["durable_completed"]}
    if (
        len(old_digests) != 150 or len(old_durable) != 149
        or set(old_digests) - set(old_durable) != {ORPHAN_JOB_ID}
        or set(old_durable) != set(incident["inventory"]["events"]["synced_job_ids"])
    ):
        raise RecoveryRefused("preserved final job inventory differs from the exact incident")
    access, _ = _relocation_state()
    synced = {
        event["job_id"]: event["data"]
        for event in events
        if event["kind"] == "job_synced"
    }
    final_digests: list[dict[str, str]] = []
    for job_id in sorted(all_ids):
        local = local_root / job_id
        durable = durable_root / job_id
        sync = synced.get(job_id)
        if type(sync) is not dict:
            raise RecoveryRefused(f"final sync event is missing for {job_id}")
        if job_id in old_durable:
            preserved = _validate_preserved_durable_pair(job_id, {"data": sync}, old_durable[job_id], local, durable, access)
            if _canonical(preserved) != _canonical(old_durable[job_id]):
                raise RecoveryRefused(f"preserved copy evidence changed from the incident: {job_id}")
            local_digest = preserved["tree_digest"]
        else:
            local_digest = B._job_tree_digest(local)
            if B._job_tree_digest(durable) != local_digest:
                raise RecoveryRefused(f"final local/durable tree differs for {job_id}")
            copy_digest = B._copy_evidence_digest(local, durable)
            if sync.get("source_tree_digest") != local_digest:
                raise RecoveryRefused(f"final sync event tree digest differs for {job_id}")
            if sync.get("copy_evidence_digest") != copy_digest:
                raise RecoveryRefused(f"final sync copy digest differs for {job_id}")
        checkpoint_token = started.get(job_id)
        if checkpoint_token not in checkpoints:
            raise RecoveryRefused(f"final job lacks one checkpoint-bound start: {job_id}")
        result = _expect_keys(
            read_json(local / Supervisor.RESULT_FILE),
            {
                "exp2a_repair_result_schema_version",
                "job",
                "expected_git_commit",
                "checkpoint_digest",
                "execution_context_digest",
                "fit_evidence_digest",
                "baseline_source",
            },
            what="final E2A job result",
        )
        if (
            result["expected_git_commit"] != EXECUTION_COMMIT
            or result["checkpoint_digest"]
            != checkpoints[checkpoint_token][0]["checkpoint_digest"]
            or result["execution_context_digest"]
            != checkpoints[checkpoint_token][0]["execution_context_digest"]
            or result["fit_evidence_digest"] != sync.get("execution_digest")
        ):
            raise RecoveryRefused(f"final job result provenance differs for {job_id}")
        attempt = read_json(local / Supervisor.ATTEMPT_FILE)
        receipt = read_json(local / Supervisor.RECEIPT_FILE)
        expected_parent = (
            OLD_LEASE_PID if checkpoint_token == OLD_LEASE_TOKEN else lower["lease_pid"]
        )
        if (
            type(attempt) is not dict
            or type(receipt) is not dict
            or attempt.get("job_id") != job_id
            or receipt.get("job_id") != job_id
            or attempt.get("attempt_token") != receipt.get("attempt_token")
            or attempt.get("parent_pid") != expected_parent
            or receipt.get("parent_pid") != expected_parent
            or receipt.get("status") != "success"
            or receipt.get("exit_code") != 0
            or receipt.get("published") is not True
            or receipt.get("result_digest")
            != sha256_bytes(Supervisor._canonical_json_bytes(result))
            or receipt.get("job_tree_digest") != Supervisor._job_tree_digest(local)
        ):
            raise RecoveryRefused(f"final successful attempt receipt differs for {job_id}")
        if job_id in old_digests and local_digest != old_digests[job_id]:
            raise RecoveryRefused(f"epoch-001 completed tree changed: {job_id}")
        final_digests.append({"job_id": job_id, "tree_digest": local_digest})
    _validate_empty_attempt_staging()
    return {
        "local_completed": len(final_digests),
        "durable_completed": len(final_digests),
        "old_completed_unchanged": len(old_digests),
        "tree_digest_set": sha256_bytes(_canonical(final_digests)),
    }


def _validate_lower_completion(incident: Mapping[str, Any]) -> dict[str, Any]:
    transition, transition_sha = _load_transition_completion()
    checkpoints = _checkpoint_documents()
    events, stream_digest, new_token, started = _final_events(checkpoints)
    lower = _validate_new_lower_report(new_token, checkpoints)
    jobs = _validate_final_job_trees(
        incident, events, started, checkpoints, lower
    )
    if (
        jobs["old_completed_unchanged"] != 150
        or len(events) != EXPECTED_FINAL_COUNTS["events"]
    ):
        raise RecoveryRefused("completed recovery accounting is not exact")
    return {
        "counts": dict(EXPECTED_RECOVERY_COUNTS),
        "new_token": new_token,
        "checkpoints": {
            token: {
                "path": str(
                    (P.OUTPUT_ROOT / Plan.START_DIRECTORY / f"{token}.json").resolve()
                ),
                "copy_path": str(
                    (P.SYNC_ROOT / Plan.START_DIRECTORY / f"{token}.json").resolve()
                ),
                "sha256": row[1],
                "checkpoint_digest": row[0]["checkpoint_digest"],
            }
            for token, row in sorted(checkpoints.items())
        },
        "events": {
            "count": len(events),
            "chain_digest": stream_digest,
            "old_prefix_chain_digest": EXPECTED_HASHES["old_event_stream"],
            "failure_count": 0,
        },
        "jobs": jobs,
        "lower_report": lower,
        "transition": {
            "record_digest": transition["record_digest"],
            "file_sha256": transition_sha,
        },
    }


def _validate_completed_bootstrap(material: Mapping[str, Any]) -> dict[str, Any]:
    """Reopen and bind the exact one-use bootstrap completion chain."""

    state = _bootstrap_state()
    if state["state"] not in {"terminal_complete", "postmortem_complete"}:
        raise RecoveryRefused(
            "completed recovery lacks the exact complete bootstrap record chain"
        )
    invocation = state["invocation"]
    claim = state["claim"]
    common = {
        "invocation": _record_binding(
            invocation, sha256_file(_record_paths(BOOTSTRAP_INVOCATION_FILE)[0])
        ),
        "claim": _record_binding(
            claim, sha256_file(_record_paths(BOOTSTRAP_CLAIM_FILE)[0])
        ),
    }
    if state["state"] == "postmortem_complete":
        if _canonical(state["material"]) != _canonical(material):
            raise RecoveryRefused(
                "bootstrap postmortem does not bind the revalidated lower completion"
            )
        return {
            "kind": "controller_postmortem",
            **common,
            "postmortem": _record_binding(
                state["postmortem"],
                sha256_file(_record_paths(BOOTSTRAP_POSTMORTEM_FILE)[0]),
            ),
        }
    terminal = state["terminal"]
    operational = terminal["operational_result"]
    if (
        operational["counts"] != material["counts"]
        or operational["lease_token"] != material["new_token"]
        or operational["report_sha256"] != material["lower_report"]["sha256"]
    ):
        raise RecoveryRefused(
            "bootstrap terminal does not bind the revalidated lower completion"
        )
    return {
        "kind": "worker_terminal",
        **common,
        "terminal": _record_binding(
            terminal, sha256_file(_record_paths(BOOTSTRAP_TERMINAL_FILE)[0])
        ),
    }


def _completion_payload(material: Mapping[str, Any], incident: Mapping[str, Any]) -> dict[str, Any]:
    transition, transition_sha = _load_transition_completion()
    return {
        **_base_record("recovery_completion"),
        "status": "complete",
        "incident": {
            "record_digest": incident["record_digest"],
            "file_sha256": sha256_file(_record_paths(INCIDENT_FILE)[0]),
            "inventory_digest": incident["inventory_digest"],
        },
        "transition": {
            "record_digest": transition["record_digest"],
            "file_sha256": transition_sha,
        },
        "bootstrap": _validate_completed_bootstrap(material),
        "execution_commit": EXECUTION_COMMIT,
        "controller_commit": incident["authority"]["controller_worktree"]["git_commit"],
        "counts": dict(material["counts"]),
        "new_lease_token": material["new_token"],
        "checkpoints": material["checkpoints"],
        "events": material["events"],
        "jobs": material["jobs"],
        "lower_report": material["lower_report"],
        "automatic_retry_allowed": False,
        "second_interruption_present": False,
    }


def _production_launch_payload(
    completion: Mapping[str, Any], completion_sha: str
) -> dict[str, Any]:
    new_token = completion["new_lease_token"]
    checkpoint = completion["checkpoints"][new_token]
    lower = completion["lower_report"]
    control = P._load_control(EXECUTION_COMMIT, monitor_only=True)
    return {
        "expected_git_commit": EXECUTION_COMMIT,
        "control_receipt_sha256": control["_file_sha256"],
        "lease_token": new_token,
        "checkpoint": {
            "path": checkpoint["path"],
            "copy_path": checkpoint["copy_path"],
            "sha256": checkpoint["sha256"],
            "independent_copy": True,
        },
        "launch_report": {
            "path": lower["path"],
            "copy_path": lower["copy_path"],
            "sha256": lower["sha256"],
            "independent_copy": True,
        },
        "status": "complete",
        "lower_counts": dict(EXPECTED_RECOVERY_COUNTS),
        "released_lease": lower["released_lease"],
        "counts": {
            "physical_fits": 261,
            "member_models": 441,
            "historical_retrained": 0,
        },
        "recovery": {
            "schema_version": RECOVERY_SCHEMA_VERSION,
            "decision_id": DECISION_ID,
            "recovery_id": RECOVERY_ID,
            "completion_record_digest": completion["record_digest"],
            "completion_file_sha256": completion_sha,
            "epoch_count": 2,
            "event_count": EXPECTED_FINAL_COUNTS["events"],
            "old_completed_tree_count_unchanged": 150,
            "automatic_retry_allowed": False,
        },
    }


def _validate_recovery_completion_record(
    incident: Mapping[str, Any], material: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    completion, completion_sha = _load_twins(
        RECOVERY_COMPLETION_FILE, record_type="recovery_completion"
    )
    expected = _seal(_completion_payload(material, incident))
    if _canonical(completion) != _canonical(expected):
        raise RecoveryRefused("recovery completion record differs from revalidation")
    return completion, completion_sha


def _validate_production_launch_receipt(
    completion: Mapping[str, Any], completion_sha: str
) -> dict[str, Any]:
    receipt = P._load_receipt("launch")
    expected_payload = _production_launch_payload(completion, completion_sha)
    if (
        receipt["status"] != "complete"
        or receipt["purpose"] != "bind_d161_recovered_261_fit_e2a_repair_launch"
        or _canonical(receipt["payload"]) != _canonical(expected_payload)
    ):
        raise RecoveryRefused("production launch receipt does not bind D-161 recovery")
    return receipt


def recovery_monitor_material() -> dict[str, Any]:
    """Return the stable terminal monitor material for a recovered launch.

    Live recovery monitoring is deliberately unsupported: this function fails
    closed until both checkpoints, all 523 events, and the successful second
    lower report are present.  Full transition validation mechanically hashes
    the quarantined partial bytes; no decoded value is consulted or emitted.
    """

    incident, _, _, _ = _load_adjudication()
    completed_material = _validate_lower_completion(incident)
    transition, _ = _load_transition_completion()
    checkpoints = _checkpoint_documents()
    events, stream_digest, new_token, _ = _final_events(checkpoints)
    lower = _validate_new_lower_report(new_token, checkpoints)
    _validate_completed_bootstrap(completed_material)
    control = P._load_control(EXECUTION_COMMIT, monitor_only=True)
    second = checkpoints[new_token][0]
    document = {
        "week8_exp2a_monitor_schema_version": P.MONITOR_SCHEMA_VERSION,
        "purpose": "outcome_blind_read_only_exp2a_operational_snapshot",
        "status": "complete",
        "control": {
            "original_path": control["receipt_paths"]["original"],
            "copy_path": control["receipt_paths"]["copy"],
            "sha256": control["_file_sha256"],
            "receipt_digest": control["receipt_digest"],
        },
        "checkpoint": {
            "token": new_token,
            "sha256": checkpoints[new_token][1],
            "checkpoint_digest": second["checkpoint_digest"],
        },
        "event_stream": {
            "event_count": len(events),
            "last_event_digest": events[-1]["event_digest"],
            "stream_sha256": stream_digest,
        },
        "terminal_report": {
            "token": new_token,
            "status": "complete",
            "sha256": lower["sha256"],
            "counts": dict(EXPECTED_RECOVERY_COUNTS),
            "failure_sha256": None,
            "released_lease": True,
        },
        "counts": {
            "expected": 261,
            "started": 261,
            "synced": 261,
            "failed": 0,
            "sync_pending": 0,
            "remaining": 0,
        },
        "preserved_failures": [],
        "failure_text_included": False,
        "scientific_files_opened": True,
        "automatic_repair_performed": False,
    }
    # Rechecking the transition here prevents a caller from presenting a
    # terminal event stream detached from the one authorized recovery epoch.
    if transition["status"] != "ownership_transition_complete":
        raise RecoveryRefused("recovery monitor lacks the completed transition")
    return Plan._seal(document, "snapshot_digest")


def validate_completed_recovery(
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the complete D-161 history for future production integration.

    No caller path or scientific value reaches this boundary.  ``payload`` is
    the recovery-aware launch payload supplied by ``production._load_launch``;
    when omitted, this function loads and verifies the immutable launch receipt
    itself.
    """

    if payload is not None and not isinstance(payload, Mapping):
        raise RecoveryRefused("recovery launch payload must be a mapping or null")
    incident, _, _, _ = _load_adjudication()
    # A payload is supplied only by the fixed E2A consumer while it is invoked
    # through this same captured-byte entrypoint.  That consumer independently
    # proves its clean finalizer commit and then checks the execution/controller
    # pair below.  Requiring a second nested gate inside that callback would
    # make the fixed monitor/finalize/report/figures commands recurse.
    # Direct recovery-side validation (payload omitted) retains the full live
    # authority re-attestation.
    if payload is None:
        _assert_current_controller_authority(incident)
    else:
        _assert_current_static_controller_authority(incident)
    material = _validate_lower_completion(incident)
    completion, completion_sha = _validate_recovery_completion_record(
        incident, material
    )
    receipt = None
    expected_payload = _production_launch_payload(completion, completion_sha)
    if payload is None:
        receipt = _validate_production_launch_receipt(completion, completion_sha)
    elif _canonical(dict(payload)) != _canonical(expected_payload):
        raise RecoveryRefused(
            "caller-supplied launch payload differs from the completed recovery"
        )
    return {
        "status": "complete",
        "decision_id": DECISION_ID,
        "execution_commit": EXECUTION_COMMIT,
        "controller_commit": completion["controller_commit"],
        "counts": dict(completion["counts"]),
        "new_lease_token": completion["new_lease_token"],
        "event_count": completion["events"]["count"],
        "old_completed_tree_count_unchanged": completion["jobs"][
            "old_completed_unchanged"
        ],
        "launch_receipt_sha256": None if receipt is None else receipt["_file_sha256"],
        "scientific_values_emitted": False,
    }


def seal() -> dict[str, Any]:
    """Seal exact completion and publish the recovery-aware launch receipt."""

    incident, _, _, _ = _load_adjudication()
    _assert_current_controller_authority(incident)
    bootstrap = _bootstrap_state()
    bootstrap_state = bootstrap["state"]
    if _is_permanent_bootstrap_stop(bootstrap_state):
        raise RecoveryRefused("the continuation epoch stopped; sealing is prohibited")
    if bootstrap_state == "postmortem_seal_required":
        # The worker terminal and controller postmortem are different filenames,
        # so O_EXCL alone cannot choose between them.  Reuse the stable lease
        # transition guard and repeat every mutable proof while holding it.
        with _finalization_lock():
            finalization_present = any(
                _twin_presence(BOOTSTRAP_TERMINAL_FILE)
            ) or any(_twin_presence(BOOTSTRAP_POSTMORTEM_FILE))
            if not finalization_present:
                fresh = _bootstrap_state()
                if fresh["state"] != "postmortem_seal_required":
                    raise RecoveryRefused(
                        "bootstrap state changed under the finalization guard"
                    )
                if _canonical(fresh["material"]) != _canonical(
                    bootstrap["material"]
                ):
                    raise RecoveryRefused(
                        "lower completion changed before postmortem seal"
                    )
                if any(_twin_presence(BOOTSTRAP_TERMINAL_FILE)) or any(
                    _twin_presence(BOOTSTRAP_POSTMORTEM_FILE)
                ):
                    raise RecoveryRefused(
                        "bootstrap finalization appeared during guarded revalidation"
                    )
                _publish_twins_exclusive(
                    BOOTSTRAP_POSTMORTEM_FILE,
                    _bootstrap_postmortem_payload(
                        incident=incident,
                        invocation=fresh["invocation"],
                        invocation_sha=fresh["invocation_file_sha256"],
                        claim=fresh["claim"],
                        claim_sha=fresh["claim_file_sha256"],
                        material=fresh["material"],
                        controller_process=fresh["controller_process"],
                        liveness=fresh["liveness"],
                        runtime_temp=fresh["runtime_temp"],
                    ),
                )
        bootstrap = _bootstrap_state()
        if bootstrap["state"] != "postmortem_complete":
            if _is_permanent_bootstrap_stop(bootstrap["state"]):
                raise RecoveryRefused(
                    "bootstrap finalization stopped while postmortem waited"
                )
            if bootstrap["state"] != "terminal_complete":
                raise RecoveryRefused("postmortem publication did not seal exactly")
    elif bootstrap_state not in {"terminal_complete", "postmortem_complete"}:
        raise RecoveryRefused("recovery is not complete and ready to seal")
    material = _validate_lower_completion(incident)
    if _record_presence(RECOVERY_COMPLETION_FILE):
        completion, completion_sha = _validate_recovery_completion_record(
            incident, material
        )
    else:
        completion = _publish_twins(
            RECOVERY_COMPLETION_FILE, _completion_payload(material, incident)
        )
        completion_sha = sha256_file(_record_paths(RECOVERY_COMPLETION_FILE)[0])
    payload = _production_launch_payload(completion, completion_sha)
    if P._receipt_present("launch"):
        _validate_production_launch_receipt(completion, completion_sha)
    else:
        P._publish_receipt(
            "launch",
            status="complete",
            purpose="bind_d161_recovered_261_fit_e2a_repair_launch",
            payload=payload,
        )
    result = validate_completed_recovery()
    return {"command": "seal", **result}


def status() -> dict[str, Any]:
    """Return one operational state without exposing scientific values."""

    if _record_presence(RECOVERY_COMPLETION_FILE):
        if P._receipt_present("launch"):
            result = validate_completed_recovery()
            return {"command": "status", "state": "sealed", **result}
        incident, _, _, _ = _load_adjudication()
        material = _validate_lower_completion(incident)
        _validate_recovery_completion_record(incident, material)
        return {
            "command": "status",
            "state": "completion_record_present_launch_receipt_missing",
            "scientific_values_emitted": False,
        }
    if _record_presence(TRANSITION_COMPLETION_FILE):
        _load_transition_completion()
        bootstrap = _bootstrap_state()
        bootstrap_state = bootstrap["state"]
        if _is_permanent_bootstrap_stop(bootstrap_state):
            return {
                "command": "status",
                "state": "stopped_after_second_interruption",
                "automatic_retry_allowed": False,
                "scientific_values_emitted": False,
            }
        if bootstrap_state in {
            "claimed_worker_running",
            "claimed_worker_live_or_identity_ambiguous",
        }:
            return {
                "command": "status",
                "state": "continuation_epoch_running_or_identity_ambiguous",
                "automatic_retry_allowed": False,
                "scientific_values_emitted": False,
            }
        if bootstrap_state == "not_invoked":
            return {
                "command": "status",
                "state": "transition_complete_ready_for_one_invocation",
                "automatic_retry_allowed": False,
                "scientific_values_emitted": False,
            }
        if bootstrap_state in {
            "terminal_complete",
            "postmortem_seal_required",
            "postmortem_complete",
        }:
            incident, _, _, _ = _load_adjudication()
            material = _validate_lower_completion(incident)
            return {
                "command": "status",
                "state": (
                    "recovery_complete_postmortem_seal_required"
                    if bootstrap_state == "postmortem_seal_required"
                    else "recovery_complete_ready_to_seal"
                ),
                "bootstrap_completion_kind": (
                    "controller_postmortem"
                    if bootstrap_state.startswith("postmortem")
                    else "worker_terminal"
                ),
                "counts": material["counts"],
                "scientific_values_emitted": False,
            }
        raise RecoveryRefused("bootstrap state classifier returned an unknown state")
    if _record_presence(TRANSITION_INTENT_FILE):
        return {
            "command": "status",
            "state": "stopped_during_ownership_transition",
            "automatic_retry_allowed": False,
            "scientific_values_emitted": False,
        }
    if _record_presence(INCIDENT_FILE) or _record_presence(EPOCH001_TERMINAL_FILE):
        _load_adjudication()
        return {
            "command": "status",
            "state": "adjudicated_ready_for_one_recovery_epoch",
            "automatic_retry_allowed": False,
            "scientific_values_emitted": False,
        }
    # Before adjudication, status is the independent, read-only release gate.
    # It deliberately repeats the same fixed old-source inspection, double
    # inventory, and Windows liveness checks that adjudication will require,
    # but it publishes no recovery record and changes no production evidence.
    inventory, inspection = _capture_twice()
    liveness = _quiescent_liveness()
    hidden_partial = inventory["jobs"]["hidden_partial"]
    return {
        "command": "status",
        "state": "not_adjudicated",
        "independent_inspection_performed": True,
        "mechanical_source_validation_performed": True,
        "inventory_digest": inventory["inventory_digest"],
        "inspector_digest": inspection["inspector_digest"],
        "liveness_digest": sha256_bytes(_canonical(liveness)),
        "liveness_verdict": liveness["stability"]["verdict"],
        "counts": {
            "events": inventory["events"]["count"],
            "started": len(inventory["events"]["started_job_ids"]),
            "synced": len(inventory["events"]["synced_job_ids"]),
            "local_completed": len(inventory["jobs"]["local_completed"]),
            "durable_completed": len(inventory["jobs"]["durable_completed"]),
            "untouched": len(inventory["jobs"]["untouched_job_ids"]),
            "partial_files": hidden_partial["file_count"],
            "orphan_local_files": inspection["jobs"]["hidden_partial"][
                "orphan_local_file_count"
            ],
        },
        "automatic_retry_allowed": False,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }


def _run_postrecovery_command(
    command: str,
    *,
    gate: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one fixed E2A consumer under the same captured-byte entrypoint."""

    if command not in {"monitor", "finalize", "report", "figures"}:
        raise RecoveryRefused("post-recovery command is not allowlisted")
    incident, _, _, _ = _load_adjudication()
    authority = _assert_current_controller_authority(incident)
    controller_commit = authority["controller_worktree"]["git_commit"]
    capability = P._D166_CONTROLLER_CAPABILITY
    handlers = {
        "monitor": lambda: P.monitor(_d166_capability=capability),
        "finalize": lambda: P.finalize(
            expected_git_commit=controller_commit,
            expected_execution_commit=EXECUTION_COMMIT,
            _d166_capability=capability,
        ),
        "report": lambda: P.report(
            expected_git_commit=controller_commit,
            _d166_capability=capability,
        ),
        "figures": lambda: P.figures(
            expected_git_commit=controller_commit,
            _d166_capability=capability,
        ),
    }
    with _verified_downstream_git_environment(gate):
        result = handlers[command]()
    if type(result) is not dict or result.get("command") != command:
        raise RecoveryRefused("post-recovery command returned another contract")
    _assert_current_controller_authority(incident)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "adjudicate",
            "recover",
            "seal",
            "status",
            "monitor",
            "finalize",
            "report",
            "figures",
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        gate = _validate_controller_runtime()
        if gate.get("command") != arguments.command:
            raise RecoveryRefused(
                "entrypoint gate command differs from controller command"
            )
        handlers = {
            "adjudicate": adjudicate,
            "recover": recover,
            "seal": seal,
            "status": status,
            "monitor": lambda: _run_postrecovery_command("monitor", gate=gate),
            "finalize": lambda: _run_postrecovery_command("finalize", gate=gate),
            "report": lambda: _run_postrecovery_command("report", gate=gate),
            "figures": lambda: _run_postrecovery_command("figures", gate=gate),
        }
        with _parent_relocation(gate):
            result = handlers[arguments.command]()
    except (OSError, TypeError, ValueError) as exc:
        refusal = {
            "command": arguments.command,
            "status": "refused",
            "error_type": type(exc).__name__,
            "error_sha256": sha256_bytes(str(exc).encode("utf-8")),
            "controller_locations": _controller_refusal_locations(exc),
            "automatic_retry_allowed": False,
            "scientific_values_emitted": False,
        }
        if isinstance(exc, _InspectorProcessRefused):
            refusal["inspector_failure"] = exc.inspector_failure
        print(json.dumps(refusal, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI contract
    raise SystemExit(main())
