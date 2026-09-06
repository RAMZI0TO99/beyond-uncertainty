"""Read-only old-source inspector for the single D-161 E2A incident.

The script accepts no arguments.  It imports ``bu`` only from the clean,
detached execution worktree at commit 4515d516 and uses that historical
source to validate the frozen checkpoint, event prefix, and completed fit
trees.  Its sole stdout value is one strict JSON object containing operational
identifiers, process identifiers, counts, and cryptographic digests.  It does
not publish, repair, copy, move, or delete production evidence.

Some historical validators mechanically decode diagnostic arrays.  Their
values are never consulted by this inspector and are never emitted.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


INSPECTOR_SCHEMA_VERSION = 1
EXECUTION_COMMIT = "4515d5165756c8d1669d38d2ee854fa1051b1017"
OLD_LEASE_TOKEN = "c66ea75437c043ba9a1113e0a31d2f8d"
OLD_LEASE_PID = 48_960
ORPHAN_JOB_ID = "178f4ef3ae1e-s1001"
ORPHAN_CHILD_PID = 29_480
HIDDEN_PARTIAL_NAME = ".178f4ef3ae1e-s1001.19rl_x0_.partial"

WORKSPACE_ROOT = Path("D:/Aenv/pro/pro")
CONTROLLER_WORKTREE = WORKSPACE_ROOT / "week8-recovery-controller-worktree"
EXECUTION_WORKTREE = WORKSPACE_ROOT / "week8-e2a-execution-4515-worktree"
EXECUTION_SOURCE = EXECUTION_WORKTREE / "src"
PINNED_PYTHON = WORKSPACE_ROOT / "pro2" / ".venv" / "Scripts" / "python.exe"
PINNED_BASE_PYTHON = Path(
    "C:/Users/aladdin-alyanai/AppData/Local/Programs/Python/Python313/python.exe"
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
    "C:/Users/aladdin-alyanai/.cache/codex-runtimes/codex-primary-runtime/"
    "dependencies/native/git/mingw64/bin/git.exe"
)
RAW_AUTHORITY_HELPER = (
    CONTROLLER_WORKTREE / "scripts" / "week8_recovery_raw_authority.py"
)
ENTRYPOINT_GATE_ENVIRONMENT_NAME = "BU_D161_ENTRYPOINT_GATE"
RAW_AUTHORITY_MODULE_NAME = "_bu_week8_d161_raw_authority"
EXPECTED_PINNED_PYTHON_SHA256 = (
    "935016795f3e6908e75acbc2040a01e2e4cdb494a57c42f63a0d6eedb2372256"
)
EXPECTED_PINNED_BASE_PYTHON_SHA256 = (
    "5341746f92483a93e44c313de830f2fba2956f0759094404a16b2fed06c9a2ed"
)
EXPECTED_PINNED_PYVENV_SHA256 = (
    "be7ef6e263b1f7242a8ce45cf329e96896d2d5d54e7fc565acb94fb722f66d71"
)
EXPECTED_PINNED_BASE_RUNTIME_INVENTORY_SHA256 = (
    "0a5aff918e4a46fae2427a593261f8e3640ba439ba4ffebf5081b15eb7df6760"
)
EXPECTED_PINNED_BASE_RUNTIME_FILE_COUNT = 5_368
EXPECTED_PINNED_BASE_RUNTIME_DIRECTORY_COUNT = 504
EXPECTED_PINNED_BASE_RUNTIME_TOTAL_BYTES = 155_022_742
EXPECTED_PINNED_VENV_SCRIPTS_INVENTORY_SHA256 = (
    "1b9814979baf41e16ba3f9a7e754e55fd650bd786338e6ebb3b88441e0ef4c56"
)
EXPECTED_PINNED_VENV_SCRIPTS_FILE_COUNT = 22
EXPECTED_PINNED_VENV_SCRIPTS_DIRECTORY_COUNT = 0
EXPECTED_PINNED_VENV_SCRIPTS_TOTAL_BYTES = 2_145_386
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
    "ec8a9ffd7ec91e6fb0234a3e2545a8ab4f41758ada574f5e1a7471409cd6febb"
)
EXPECTED_PINNED_SITE_PACKAGES_FILE_COUNT = 34_514
EXPECTED_PINNED_SITE_PACKAGES_DIRECTORY_COUNT = 3_183
EXPECTED_PINNED_SITE_PACKAGES_TOTAL_BYTES = 1_019_096_855
EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256 = (
    "52a4d90f242fe58af53cf95985660f548d14047e838a463ac329aa63f047840e"
)
EXPECTED_RAW_AUTHORITY_HELPER_SHA256 = (
    "dd40628b2ab13507d741d597190606b108b48589372204edf342e6d628ef137d"
)
PREPARATION_ORIGINAL_ROOT = (
    WORKSPACE_ROOT
    / "week8-execution-preparation-2026-09-01-attempt-001"
    / "exp2a-original"
)
PREPARATION_COPY_ROOT = (
    WORKSPACE_ROOT
    / "week8-execution-preparation-2026-09-01-attempt-001"
    / "exp2a-project-evidence"
)
PREFLIGHT_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-preflight"
OUTPUT_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-output"
STAGING_ROOT = WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-staging"
SYNC_ROOT = (
    WORKSPACE_ROOT / "week8-exp2a-2026-09-01-attempt-001-project-evidence"
)

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
EXPECTED_COUNTS = {
    "events": 299,
    "started": 150,
    "synced": 149,
    "local_completed": 150,
    "durable_completed": 149,
    "untouched": 111,
    "partial_files": 11,
    "orphan_local_files": 15,
}

_HEX32 = re.compile(r"[0-9a-f]{32}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class InspectorRefused(ValueError):
    """Historical source or frozen incident evidence is not exact."""


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
        raise InspectorRefused("inspector evidence must be strict JSON") from exc


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise InspectorRefused("an inspected file could not be hashed") from exc
    return digest.hexdigest()


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
        raise InspectorRefused("inspector authority is not canonical JSON") from exc


def _raw_authority_config(
    controller_commit: str, native_startup: Mapping[str, Any]
) -> dict[str, Any]:
    if type(controller_commit) is not str or _HEX40.fullmatch(controller_commit) is None:
        raise InspectorRefused("controller authority commit is malformed")
    if type(native_startup) is not dict:
        raise InspectorRefused("native startup authority is unavailable")
    launcher = native_startup.get("native_launcher")
    values = (
        native_startup.get("release_receipt_sha256"),
        launcher.get("sha256") if type(launcher) is dict else None,
        native_startup.get("stage0_binding_sha256"),
        native_startup.get("startup_binding_sha256"),
    )
    if any(type(value) is not str or _HEX64.fullmatch(value) is None for value in values):
        raise InspectorRefused("native startup hashes are malformed")
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


def _load_bound_raw_authority() -> ModuleType:
    module = sys.modules.get(RAW_AUTHORITY_MODULE_NAME)
    if type(module) is not ModuleType:
        raise InspectorRefused(
            "raw-authority helper was not preloaded from the verified child bundle"
        )
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
        raise InspectorRefused("preloaded raw-authority helper identity differs")
    return module


def _validate_entrypoint_authority() -> dict[str, Any]:
    encoded = os.environ.get(ENTRYPOINT_GATE_ENVIRONMENT_NAME)
    if type(encoded) is not str or not encoded:
        raise InspectorRefused("inspector lacks the D-161 entrypoint gate")
    try:
        gate = json.loads(encoded)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InspectorRefused("inspector entrypoint gate is not strict JSON") from exc
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
    if type(gate) is not dict or set(gate) != expected_keys:
        raise InspectorRefused("inspector entrypoint gate shape differs")
    unsealed = {key: value for key, value in gate.items() if key != "record_digest"}
    if (
        encoded != _canonical_ascii(gate).decode("ascii")
        or gate["entrypoint_gate_schema_version"] != 4
        or gate["record_type"] != "week8_d161_entrypoint_gate"
        or gate["decision_id"] != "D-161"
        or gate["command"] not in {"status", "adjudicate", "recover"}
        or gate["record_digest"] != _sha_bytes(_canonical_ascii(unsealed))
        or gate["scientific_outcomes_consulted"] is not False
        or gate["scientific_values_emitted"] is not False
        or gate["production_mutation_performed"] is not False
    ):
        raise InspectorRefused("inspector entrypoint gate policy differs")
    module = _load_bound_raw_authority()
    revalidate = getattr(module, "revalidate_admitted_authority", None)
    if not callable(revalidate):
        raise InspectorRefused("raw-authority revalidation API is unavailable")
    try:
        observed = revalidate(
            gate["raw_authority"],
            _raw_authority_config(
                gate["raw_authority"]["controller"].get("git_commit"),
                gate["raw_authority"].get("native_startup"),
            ),
            helper_path=RAW_AUTHORITY_HELPER,
            helper_sha256=EXPECTED_RAW_AUTHORITY_HELPER_SHA256,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise InspectorRefused("inspector raw authority revalidation refused") from exc
    if _canonical_ascii(observed) != _canonical_ascii(gate["raw_authority"]):
        raise InspectorRefused("inspector raw authority changed")
    return gate


def _strict_object(value: object, keys: set[str], *, what: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise InspectorRefused(f"{what} has missing or extra fields")
    return value


def _is_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & flag)


def _plain_path(path: Path, *, directory: bool, what: str) -> Path:
    absolute = Path(os.path.abspath(path))
    for component in reversed((absolute, *absolute.parents)):
        if not os.path.lexists(component):
            continue
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise InspectorRefused(f"cannot inspect {what} path") from exc
        if _is_reparse(metadata):
            raise InspectorRefused(f"{what} contains a link/reparse component")
        if component != absolute and not stat.S_ISDIR(metadata.st_mode):
            raise InspectorRefused(f"{what} has a non-directory parent")
    try:
        resolved = absolute.resolve(strict=True)
        workspace = WORKSPACE_ROOT.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InspectorRefused(f"{what} is unavailable") from exc
    if resolved == workspace or not resolved.is_relative_to(workspace):
        raise InspectorRefused(f"{what} is outside the fixed workspace")
    metadata = resolved.lstat()
    if _is_reparse(metadata):
        raise InspectorRefused(f"{what} is a link/reparse point")
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(metadata.st_mode):
        raise InspectorRefused(f"{what} has the wrong filesystem type")
    return resolved


def _plain_tree_inventory(root: Path, *, what: str) -> list[dict[str, Any]]:
    root = _plain_path(root, directory=True, what=what)
    rows: list[dict[str, Any]] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(directory_names):
            child = current_path / name
            metadata = child.lstat()
            if _is_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise InspectorRefused(f"{what} has a linked/special directory")
            rows.append(
                {"kind": "directory", "path": child.relative_to(root).as_posix()}
            )
        for name in sorted(file_names):
            child = current_path / name
            metadata = child.lstat()
            if _is_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
                raise InspectorRefused(f"{what} has a linked/special file")
            rows.append(
                {
                    "kind": "file",
                    "path": child.relative_to(root).as_posix(),
                    "size": metadata.st_size,
                    "sha256": _sha_file(child),
                }
            )
    return sorted(rows, key=lambda row: (row["path"], row["kind"]))


def _content_digest(rows: list[dict[str, Any]]) -> str:
    return _sha_bytes(_canonical(rows))


def _validate_execution_source(gate: Mapping[str, Any]) -> None:
    if Path(__file__).resolve() != (
        CONTROLLER_WORKTREE / "scripts" / "week8_exp2a_recovery_inspector.py"
    ).resolve(strict=True):
        raise InspectorRefused("inspector logical source path differs")
    raw_module = _load_bound_raw_authority()
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    if not callable(admitted_source):
        raise InspectorRefused("raw captured-source API is unavailable")
    expected_script_sha = _sha_bytes(
        admitted_source(
            gate["raw_authority"],
            "controller",
            "scripts/week8_exp2a_recovery_inspector.py",
        )
    )
    bundle_sha = os.environ.get("BU_D161_CHILD_BUNDLE_SHA256")
    if (
        globals().get("__transport_source_sha256__") != expected_script_sha
        or globals().get("__transport_bundle_sha256__") != bundle_sha
        or type(bundle_sha) is not str
        or _HEX64.fullmatch(bundle_sha) is None
    ):
        raise InspectorRefused("inspector verified-source transport differs")
    _plain_path(EXECUTION_WORKTREE, directory=True, what="execution worktree")
    _plain_path(EXECUTION_SOURCE, directory=True, what="execution source")
    execution = gate["raw_authority"].get("execution")
    if type(execution) is not dict or execution.get("git_commit") != EXECUTION_COMMIT:
        raise InspectorRefused("execution worktree commit differs")
    if execution.get("path") != str(EXECUTION_WORKTREE.resolve(strict=True)):
        raise InspectorRefused("execution worktree path differs")
    if execution.get("detached") is not True or execution.get("branch") != "HEAD":
        raise InspectorRefused("execution worktree is not detached")


def _install_old_source(gate: Mapping[str, Any]) -> tuple[object, object]:
    if any(name == "bu" or name.startswith("bu.") for name in sys.modules):
        raise InspectorRefused("bu was imported before historical-source isolation")
    source = EXECUTION_SOURCE.resolve(strict=True)
    site_packages = PINNED_SITE_PACKAGES.resolve(strict=True)
    for entry in sys.path:
        candidate = Path(entry or os.curdir)
        try:
            if candidate.resolve() == source:
                raise InspectorRefused("historical source was already present on sys.path")
        except OSError:
            continue
    inherited_standard_library = tuple(sys.path)
    sys.path[:] = [str(source), *inherited_standard_library, str(site_packages)]
    raw_module = _load_bound_raw_authority()
    finder_api = getattr(raw_module, "verified_source_finder", None)
    dependency_finder_api = getattr(
        raw_module, "verified_dependency_finder", None
    )
    if not callable(finder_api) or not callable(dependency_finder_api):
        raise InspectorRefused("verified execution-import API is unavailable")
    try:
        finder = finder_api(gate["raw_authority"], "execution")
        dependency_finder = dependency_finder_api(gate["raw_authority"])
    except (OSError, TypeError, ValueError) as exc:
        raise InspectorRefused("verified execution importer is unavailable") from exc
    if getattr(finder, "binding_marker", None) != "week8_d161_verified_source_v2":
        raise InspectorRefused("verified execution importer identity differs")
    if (
        getattr(dependency_finder, "binding_marker", None)
        != "week8_d161_verified_dependency_source_v1"
    ):
        raise InspectorRefused("verified dependency importer identity differs")
    sys.meta_path[:0] = [finder, dependency_finder]
    return finder, dependency_finder


def _verify_loaded_bu_modules(
    gate: Mapping[str, Any], finder: object, dependency_finder: object
) -> list[dict[str, str]]:
    source = EXECUTION_SOURCE.resolve(strict=True)
    raw = gate["raw_authority"]
    raw_module = _load_bound_raw_authority()
    admitted_source = getattr(raw_module, "admitted_source_bytes", None)
    admitted_blob = getattr(raw_module, "admitted_git_blob", None)
    if not callable(admitted_source) or not callable(admitted_blob):
        raise InspectorRefused("raw execution-source APIs are unavailable")
    expected_meta = (
        finder,
        dependency_finder,
        importlib.machinery.BuiltinImporter,
        importlib.machinery.FrozenImporter,
        importlib.machinery.PathFinder,
    )
    if tuple(sys.meta_path) != expected_meta:
        raise InspectorRefused("verified execution finders are not installed exactly")
    rows: list[dict[str, str]] = []
    for name, module in sorted(sys.modules.items()):
        if name != "bu" and not name.startswith("bu."):
            continue
        if not isinstance(module, ModuleType):
            raise InspectorRefused("a loaded bu entry is not a module")
        filename = getattr(module, "__file__", None)
        if type(filename) is not str:
            raise InspectorRefused("a loaded bu module has no source file")
        try:
            path = Path(filename).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise InspectorRefused("a loaded bu module source is unavailable") from exc
        if not path.is_relative_to(source):
            raise InspectorRefused("a bu module was loaded outside the detached source")
        specification = getattr(module, "__spec__", None)
        loader = getattr(specification, "loader", None)
        relative = path.relative_to(EXECUTION_WORKTREE.resolve()).as_posix()
        try:
            source_bytes = admitted_source(raw, "execution", relative)
            git_blob = admitted_blob(raw, "execution", relative)
        except (OSError, TypeError, ValueError) as exc:
            raise InspectorRefused("a loaded bu module lacks raw source authority") from exc
        if (
            getattr(loader, "binding_marker", None)
            != "week8_d161_verified_source_v2"
            or getattr(module, "__loader__", None) is not loader
            or getattr(loader, "tree_kind", None) != "execution"
            or getattr(loader, "source_sha256", None) != _sha_bytes(source_bytes)
            or getattr(loader, "git_blob", None) != git_blob
            or getattr(loader, "authority_tree_digest", None)
            != raw["execution"]["worktree_inventory_digest"]
        ):
            raise InspectorRefused("a loaded bu module differs from verified bytes")
        rows.append(
            {"module_id": name, "source_sha256": _sha_bytes(source_bytes)}
        )
    if not rows or rows[0]["module_id"] != "bu":
        raise InspectorRefused("historical bu package was not loaded")
    return rows


def _same_file_bytes(left: Path, right: Path, *, what: str) -> str:
    left = _plain_path(left, directory=False, what=f"{what} original")
    right = _plain_path(right, directory=False, what=f"{what} copy")
    try:
        if os.path.samefile(left, right):
            raise InspectorRefused(f"{what} copies alias one object")
        left_bytes = left.read_bytes()
        right_bytes = right.read_bytes()
    except OSError as exc:
        raise InspectorRefused(f"{what} copies could not be compared") from exc
    if left_bytes != right_bytes:
        raise InspectorRefused(f"{what} copies differ")
    return _sha_bytes(left_bytes)


def _directory_names(path: Path, *, what: str) -> list[str]:
    directory = _plain_path(path, directory=True, what=what)
    return sorted(child.name for child in directory.iterdir())


def _validate_fixed_roots(P: Any, Plan: Any) -> None:
    expected = {
        "workspace": WORKSPACE_ROOT,
        "preparation_original": PREPARATION_ORIGINAL_ROOT,
        "preparation_copy": PREPARATION_COPY_ROOT,
        "preflight": PREFLIGHT_ROOT,
        "output": OUTPUT_ROOT,
        "staging": STAGING_ROOT,
        "sync": SYNC_ROOT,
    }
    observed = {
        "workspace": P.WORKSPACE_ROOT,
        "preparation_original": P.PREPARATION_ORIGINAL_ROOT,
        "preparation_copy": P.PREPARATION_COPY_ROOT,
        "preflight": P.PREFLIGHT_ROOT,
        "output": P.OUTPUT_ROOT,
        "staging": P.STAGING_ROOT,
        "sync": P.SYNC_ROOT,
    }
    for key in expected:
        if Path(observed[key]).resolve() != Path(expected[key]).resolve():
            raise InspectorRefused(f"historical {key} root differs from D-161")
    if Path(Plan.WORKSPACE_ROOT).resolve() != WORKSPACE_ROOT.resolve():
        raise InspectorRefused("historical plan workspace differs from D-161")


def _validate_control(
    P: Any, Plan: Any, Launch: Any
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    P._validate_fixed_layout()
    phase_pins = {
        "prepare": "prepare_receipt",
        "preflight": "preflight_receipt",
        "launch-control": "launch_control_receipt",
    }
    for phase, pin in phase_pins.items():
        receipt = P._load_receipt(phase)
        if receipt.get("_file_sha256") != EXPECTED_HASHES[pin]:
            raise InspectorRefused(f"historical {phase} receipt differs")
    if P._receipt_present("launch"):
        raise InspectorRefused("launch receipt exists before recovery")
    control = P._load_control(EXECUTION_COMMIT, monitor_only=True)
    if control.get("_file_sha256") != EXPECTED_HASHES["launch_control_receipt"]:
        raise InspectorRefused("historical launch control differs")

    plan_path = PREPARATION_ORIGINAL_ROOT / Plan.PLAN_FILE
    plan_copy = PREPARATION_COPY_ROOT / Plan.PLAN_FILE
    if _same_file_bytes(plan_path, plan_copy, what="repair plan") != EXPECTED_HASHES["plan_file"]:
        raise InspectorRefused("historical plan file differs")
    plan = P.read_json(plan_path)
    Plan.validate_exp2a_repair_plan(plan)
    if plan.get("plan_digest") != EXPECTED_PLAN_DIGEST:
        raise InspectorRefused("historical plan digest differs")

    ledger_path = PREPARATION_ORIGINAL_ROOT / P.Sources.SOURCE_LEDGER_FILE
    ledger_copy = PREPARATION_COPY_ROOT / P.Sources.SOURCE_LEDGER_FILE
    if _same_file_bytes(ledger_path, ledger_copy, what="source ledger") != EXPECTED_HASHES["source_ledger_file"]:
        raise InspectorRefused("historical source ledger differs")
    preflight = PREFLIGHT_ROOT / Launch.PREFLIGHT_FILE
    preflight_copy = SYNC_ROOT / Launch.PREFLIGHT_FILE
    if _same_file_bytes(preflight, preflight_copy, what="preflight report") != EXPECTED_HASHES["preflight_report"]:
        raise InspectorRefused("historical preflight report differs")

    checkpoint, checkpoint_sha = P._checkpoint_material(control)
    if checkpoint is None or checkpoint_sha != EXPECTED_HASHES["old_checkpoint"]:
        raise InspectorRefused("historical checkpoint differs")
    lease = checkpoint.get("lease")
    if (
        type(lease) is not dict
        or lease.get("token") != OLD_LEASE_TOKEN
        or lease.get("sha256") != EXPECTED_HASHES["old_lease"]
        or checkpoint.get("checkpoint_digest") != EXPECTED_OLD_CHECKPOINT_DIGEST
        or checkpoint.get("environment", {}).get("git_commit") != EXECUTION_COMMIT
    ):
        raise InspectorRefused("historical checkpoint identity differs")

    active_lease = (
        Plan.COMMON_LEASE_ROOT
        / "leases"
        / f"{Plan.COMMON_LEASE_NAME}.lease.json"
    )
    active_lease = _plain_path(
        active_lease, directory=False, what="historical active lease"
    )
    if _sha_file(active_lease) != EXPECTED_HASHES["old_lease"]:
        raise InspectorRefused("historical active lease hash differs")
    lease_record = _strict_object(
        P.read_json(active_lease),
        {
            "schema_version",
            "lease_name",
            "pid",
            "token",
            "timestamp",
            "timestamp_utc",
        },
        what="historical active lease",
    )
    if (
        lease_record["lease_name"] != Plan.COMMON_LEASE_NAME
        or lease_record["pid"] != OLD_LEASE_PID
        or lease_record["token"] != OLD_LEASE_TOKEN
    ):
        raise InspectorRefused("historical active lease identity differs")

    events, failures = P._events_material(control, checkpoint)
    if failures or any(
        row.get("kind") in {"attempt_failed", "sync_pending", "complete"}
        for row in events
    ):
        raise InspectorRefused("historical event prefix contains terminal failure")
    if len(events) != EXPECTED_COUNTS["events"]:
        raise InspectorRefused("historical event count differs")
    chain = _sha_bytes(_canonical([row["event_digest"] for row in events]))
    if chain != EXPECTED_HASHES["old_event_stream"]:
        raise InspectorRefused("historical event chain differs")
    tail = OUTPUT_ROOT / Launch.EVENT_DIRECTORY / "000298.json"
    if _sha_file(_plain_path(tail, directory=False, what="event tail")) != EXPECTED_HASHES["old_event_tail_file"]:
        raise InspectorRefused("historical event tail differs")
    return control, checkpoint, events, lease_record


def _attempt_row(Supervisor: Any, read_json: Any, job_id: str, local: Path) -> dict[str, Any]:
    attempt_path = _plain_path(local / Supervisor.ATTEMPT_FILE, directory=False, what="attempt record")
    receipt_path = _plain_path(local / Supervisor.RECEIPT_FILE, directory=False, what="attempt receipt")
    attempt = read_json(attempt_path)
    receipt = read_json(receipt_path)
    if (
        type(attempt) is not dict
        or type(receipt) is not dict
        or attempt.get("job_id") != job_id
        or receipt.get("job_id") != job_id
        or attempt.get("attempt_token") != receipt.get("attempt_token")
        or type(attempt.get("attempt_token")) is not str
        or _HEX32.fullmatch(attempt["attempt_token"]) is None
        or attempt.get("parent_pid") != OLD_LEASE_PID
        or receipt.get("parent_pid") != OLD_LEASE_PID
        or receipt.get("status") != "success"
        or receipt.get("exit_code") != 0
        or receipt.get("error_type") is not None
        or receipt.get("error") is not None
        or receipt.get("published") is not True
        or type(receipt.get("child_pid")) is not int
        or receipt["child_pid"] <= 0
    ):
        raise InspectorRefused(f"attempt receipt differs for {job_id}")
    return {
        "attempt_receipt_sha256": _sha_file(receipt_path),
        "child_pid": receipt["child_pid"],
    }


def _inspect_jobs(P: Any, Plan: Any, Launch: Any, B: Any, Supervisor: Any, read_json: Any, checkpoint: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    roster = [job.job_id for job in Plan.new_exp2a_jobs()]
    if len(roster) != 261 or len(set(roster)) != 261:
        raise InspectorRefused("historical roster is not exactly 261 jobs")
    started = [row["job_id"] for row in events if row["kind"] == "attempt_started"]
    synced = {row["job_id"]: row for row in events if row["kind"] == "job_synced"}
    if (
        len(started) != EXPECTED_COUNTS["started"]
        or len(set(started)) != len(started)
        or len(synced) != EXPECTED_COUNTS["synced"]
        or set(started) - set(synced) != {ORPHAN_JOB_ID}
    ):
        raise InspectorRefused("historical start/sync roster differs")

    local_root = _plain_path(OUTPUT_ROOT / "jobs", directory=True, what="local jobs")
    durable_root = _plain_path(SYNC_ROOT / "jobs", directory=True, what="durable jobs")
    local_names = _directory_names(local_root, what="local jobs")
    durable_names = _directory_names(durable_root, what="durable jobs")
    if set(local_names) != set(started):
        raise InspectorRefused("local jobs differ from the 150 started jobs")
    durable_visible = {name for name in durable_names if not name.startswith(".")}
    durable_hidden = [name for name in durable_names if name.startswith(".")]
    if durable_visible != set(synced) or durable_hidden != [HIDDEN_PARTIAL_NAME]:
        raise InspectorRefused("durable jobs/partial roster differs")

    checkpoint_path = OUTPUT_ROOT / Plan.START_DIRECTORY / f"{OLD_LEASE_TOKEN}.json"
    request = {
        "checkpoint_path": checkpoint_path,
        "checkpoint_sha256": EXPECTED_HASHES["old_checkpoint"],
        "expected_git_commit": EXECUTION_COMMIT,
    }
    local_rows: list[dict[str, Any]] = []
    for job_id in sorted(started):
        validated = Launch.validate_local_completed_exp2a_job(job_id, **request)
        if type(validated) is not dict:
            raise InspectorRefused(f"historical local validator failed for {job_id}")
        tree_digest = validated.get("source_tree_digest")
        execution_digest = validated.get("execution_digest")
        if (
            type(tree_digest) is not str
            or _HEX64.fullmatch(tree_digest) is None
            or type(execution_digest) is not str
            or _HEX64.fullmatch(execution_digest) is None
            or B._job_tree_digest(local_root / job_id) != tree_digest
        ):
            raise InspectorRefused(f"historical local digest differs for {job_id}")
        attempt = _attempt_row(Supervisor, read_json, job_id, local_root / job_id)
        local_rows.append(
            {
                "job_id": job_id,
                "tree_digest": tree_digest,
                "execution_digest": execution_digest,
                **attempt,
            }
        )
    orphan = next(row for row in local_rows if row["job_id"] == ORPHAN_JOB_ID)
    if orphan["child_pid"] != ORPHAN_CHILD_PID:
        raise InspectorRefused("orphan child PID differs")

    durable_rows: list[dict[str, Any]] = []
    for job_id, event in sorted(synced.items()):
        reconciled = Launch.reconcile_completed_exp2a_job(job_id, **request)
        if type(reconciled) is not dict:
            raise InspectorRefused(f"historical durable validator failed for {job_id}")
        # The public reconciler returns the complete source-pair attestation;
        # ``job_synced`` intentionally stores only these three digest fields.
        # Compare the exact event projection, not unlike record shapes.
        event_projection = {
            name: reconciled.get(name)
            for name in (
                "execution_digest",
                "source_tree_digest",
                "copy_evidence_digest",
            )
        }
        if event_projection != event["data"]:
            raise InspectorRefused(f"historical durable validator differs for {job_id}")
        local = local_root / job_id
        durable = durable_root / job_id
        local_digest = B._job_tree_digest(local)
        durable_digest = B._job_tree_digest(durable)
        copy_digest = B._copy_evidence_digest(local, durable)
        if (
            local_digest != durable_digest
            or reconciled.get("source_tree_digest") != local_digest
            or reconciled.get("copy_evidence_digest") != copy_digest
        ):
            raise InspectorRefused(f"historical durable tree differs for {job_id}")
        durable_rows.append(
            {
                "job_id": job_id,
                "tree_digest": local_digest,
                "execution_digest": reconciled["execution_digest"],
                "copy_evidence_digest": copy_digest,
            }
        )

    untouched = sorted(set(roster) - set(started))
    if len(untouched) != EXPECTED_COUNTS["untouched"]:
        raise InspectorRefused("historical untouched roster differs")
    for job_id in untouched:
        if os.path.lexists(local_root / job_id) or os.path.lexists(durable_root / job_id):
            raise InspectorRefused("an untouched job has canonical evidence")

    partial_rows = _plain_tree_inventory(
        durable_root / HIDDEN_PARTIAL_NAME,
        what="historical hidden partial",
    )
    local_orphan_rows = _plain_tree_inventory(
        local_root / ORPHAN_JOB_ID,
        what="historical orphan local tree",
    )
    partial_files = {
        row["path"]: row for row in partial_rows if row["kind"] == "file"
    }
    local_files = {
        row["path"]: row for row in local_orphan_rows if row["kind"] == "file"
    }
    if (
        len(local_files) != EXPECTED_COUNTS["orphan_local_files"]
        or len(partial_files) != EXPECTED_COUNTS["partial_files"]
        or any(local_files.get(path) != row for path, row in partial_files.items())
    ):
        raise InspectorRefused("hidden partial is not an exact local-tree subset")

    return {
        "roster_count": len(roster),
        "local_completed": local_rows,
        "durable_completed": durable_rows,
        "untouched_job_ids": untouched,
        "orphan_job_id": ORPHAN_JOB_ID,
        "orphan_child_pid": ORPHAN_CHILD_PID,
        "hidden_partial": {
            "name": HIDDEN_PARTIAL_NAME,
            "file_count": len(partial_files),
            "orphan_local_file_count": len(local_files),
            "inventory_digest": _content_digest(partial_rows),
        },
    }


def _validate_empty_staging(P: Any) -> dict[str, int]:
    root = _plain_path(STAGING_ROOT, directory=True, what="attempt staging root")
    names = _directory_names(root, what="attempt staging root")
    if any(name not in {"staging", "quarantine"} for name in names):
        raise InspectorRefused("attempt staging root has an unknown entry")
    counts: dict[str, int] = {}
    for name in ("staging", "quarantine"):
        path = root / name
        if os.path.lexists(path):
            entries = _directory_names(path, what=f"attempt {name}")
            if entries:
                raise InspectorRefused(f"attempt {name} is not empty")
            counts[f"{name}_count"] = 0
        else:
            counts[f"{name}_count"] = 0
    return counts


def _run() -> dict[str, Any]:
    gate = _validate_entrypoint_authority()
    _validate_execution_source(gate)
    finder, dependency_finder = _install_old_source(gate)

    from bu import durable  # type: ignore[import-not-found]
    from bu.experiments import batch as B  # type: ignore[import-not-found]
    from bu.experiments import supervisor as Supervisor  # type: ignore[import-not-found]
    from bu.experiments import week8_exp2a_production as P  # type: ignore[import-not-found]
    from bu.experiments import week8_exp2a_repair_launch as Launch  # type: ignore[import-not-found]
    from bu.experiments import week8_exp2a_repairs as Plan  # type: ignore[import-not-found]

    _validate_fixed_roots(P, Plan)
    _, checkpoint, events, active_lease = _validate_control(P, Plan, Launch)
    jobs = _inspect_jobs(
        P,
        Plan,
        Launch,
        B,
        Supervisor,
        durable.read_json,
        checkpoint,
        events,
    )
    staging = _validate_empty_staging(P)
    report_root = OUTPUT_ROOT / Launch.REPORT_DIRECTORY
    report_copy_root = SYNC_ROOT / Launch.REPORT_DIRECTORY
    report_names = (
        _directory_names(report_root, what="lower report directory")
        if os.path.lexists(report_root)
        else []
    )
    report_copy_names = (
        _directory_names(report_copy_root, what="lower report copy directory")
        if os.path.lexists(report_copy_root)
        else []
    )
    if report_names or report_copy_names:
        raise InspectorRefused("historical incident unexpectedly has a lower report")

    started = [row["job_id"] for row in events if row["kind"] == "attempt_started"]
    synced = [row["job_id"] for row in events if row["kind"] == "job_synced"]
    modules = _verify_loaded_bu_modules(gate, finder, dependency_finder)
    fresh_gate = _validate_entrypoint_authority()
    if fresh_gate["record_digest"] != gate["record_digest"]:
        raise InspectorRefused("raw authority changed across inspector imports")
    payload = {
        "inspector_schema_version": INSPECTOR_SCHEMA_VERSION,
        "status": "complete",
        "execution_commit": EXECUTION_COMMIT,
        "control": {
            "hashes": dict(EXPECTED_HASHES),
            "plan_digest": EXPECTED_PLAN_DIGEST,
            "checkpoint": {
                "token": OLD_LEASE_TOKEN,
                "file_sha256": EXPECTED_HASHES["old_checkpoint"],
                "checkpoint_digest": checkpoint["checkpoint_digest"],
                "execution_context_digest": checkpoint["execution_context_digest"],
                "lease_sha256": checkpoint["lease"]["sha256"],
            },
            "active_lease": {
                "token": active_lease["token"],
                "pid": active_lease["pid"],
                "sha256": EXPECTED_HASHES["old_lease"],
            },
        },
        "events": {
            "count": len(events),
            "chain_digest": _sha_bytes(
                _canonical([row["event_digest"] for row in events])
            ),
            "tail_file_sha256": EXPECTED_HASHES["old_event_tail_file"],
            "kind_counts": dict(
                sorted(Counter(row["kind"] for row in events).items())
            ),
            "started_job_ids": sorted(started),
            "synced_job_ids": sorted(synced),
        },
        "jobs": jobs,
        "staging": staging,
        "lower_report_count": 0,
        "production_launch_receipt_present": False,
        "loaded_bu_modules": modules,
        "scientific_files_opened": True,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }
    return {**payload, "inspector_digest": _sha_bytes(_canonical(payload))}


def main() -> int:
    if len(sys.argv) != 1:
        refusal = {
            "inspector_schema_version": INSPECTOR_SCHEMA_VERSION,
            "status": "refused",
            "reason_sha256": _sha_bytes(b"inspector accepts no arguments"),
            "scientific_values_emitted": False,
            "production_mutation_performed": False,
        }
        print(json.dumps(refusal, sort_keys=True, separators=(",", ":")))
        return 2
    try:
        result = _run()
    except BaseException as exc:
        refusal = {
            "inspector_schema_version": INSPECTOR_SCHEMA_VERSION,
            "status": "refused",
            "error_type": type(exc).__name__,
            "reason_sha256": _sha_bytes(str(exc).encode("utf-8")),
            "scientific_values_emitted": False,
            "production_mutation_performed": False,
        }
        print(json.dumps(refusal, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
