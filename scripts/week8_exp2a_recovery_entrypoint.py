"""Pre-import authority entrypoint for the Week-8 D-161 recovery.

Launch this file directly with the fixed virtual-environment Python under
``-I -S -B -X utf8`` and with ``PYTHONPATH`` absent.  Only standard-library modules are
used until the raw helper has proved both checkouts, the launchers, Git, and
every worktree byte.  Project source and pinned site-packages are admitted only
after that proof is sealed into ``BU_D161_ENTRYPOINT_GATE``.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence


ENTRYPOINT_GATE_SCHEMA_VERSION = 4
DECISION_ID = "D-161"
GATE_ENVIRONMENT_NAME = "BU_D161_ENTRYPOINT_GATE"
WORKSPACE_ROOT = Path("D:/Aenv/pro2")
CONTROLLER_ROOT = WORKSPACE_ROOT / "week8-recovery-controller-worktree"
EXECUTION_ROOT = WORKSPACE_ROOT / "week8-e2a-execution-4515-worktree"
ENTRYPOINT_PATH = (
    CONTROLLER_ROOT / "scripts" / "week8_exp2a_recovery_entrypoint.py"
)
RAW_AUTHORITY_HELPER = (
    CONTROLLER_ROOT / "scripts" / "week8_recovery_raw_authority.py"
)
RAW_AUTHORITY_HELPER_SHA256 = (
    "9067c7572692a4f0bc779488613c0e81f82233d8145bc1bb795e34f176e523aa"
)
OUTER_BOOTSTRAP_LITERAL_SHA256 = (
    "73d6f0e5cb126ffde136a3746b620236c847b3791a3eec688ddbd649ab304a3e"
)
PINNED_PYTHON = WORKSPACE_ROOT / "pro2" / ".venv" / "Scripts" / "python.exe"
PINNED_BASE_PYTHON = Path(
    "D:/Aenv/pro2/runtimes/week8-python313-frozen-001/python.exe"
)
PINNED_BASE_RUNTIME = PINNED_BASE_PYTHON.parent
PINNED_PYVENV = WORKSPACE_ROOT / "pro2" / ".venv" / "pyvenv.cfg"
PINNED_VENV_SCRIPTS = PINNED_PYTHON.parent
NATIVE_LAUNCHER = (
    CONTROLLER_ROOT / "scripts" / "week8_recovery_native_launcher.ps1"
)
NATIVE_POWERSHELL = Path(
    "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)
NATIVE_RUNTIME = WORKSPACE_ROOT / "week8-d167-native-runtime-attempt-001"
PINNED_LOCAL_APPDATA = Path("C:/Users/aladdin-alyanai/AppData/Local")
PINNED_SITE_PACKAGES = (
    WORKSPACE_ROOT / "pro2" / ".venv" / "Lib" / "site-packages"
)
PINNED_GIT = Path(
    "D:/Aenv/pro2/runtimes/"
    "git/mingw64/bin/git.exe"
)
EXECUTION_COMMIT = "4515d5165756c8d1669d38d2ee854fa1051b1017"
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
COMMANDS = frozenset(
    {
        "adjudicate",
        "recover",
        "seal",
        "status",
        "monitor",
        "finalize",
        "report",
        "figures",
    }
)
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


PRODUCTION_CONFIG: dict[str, Any] = {
    "controller_root": str(CONTROLLER_ROOT),
    "controller_commit": "",
    "release_receipt_sha256": "",
    "native_launcher_sha256": "",
    "stage0_binding_sha256": "",
    "startup_binding_sha256": "",
    "execution_root": str(EXECUTION_ROOT),
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
    "outer_bootstrap_literal_sha256": OUTER_BOOTSTRAP_LITERAL_SHA256,
}


class EntrypointRefused(ValueError):
    """The standard-library authority entrypoint failed closed."""


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise EntrypointRefused("entrypoint value is not canonical JSON") from exc


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bound_file(
    path: Path, *, expected_sha256: str | None, what: str
) -> tuple[dict[str, Any], bytes]:
    """Bind one one-link plain file before any code is loaded from it."""

    if not path.is_absolute() or str(path) != str(Path(os.path.abspath(path))):
        raise EntrypointRefused(f"{what} path is not fixed and absolute")
    try:
        before = path.lstat()
    except OSError as exc:
        raise EntrypointRefused(f"{what} is unavailable") from exc
    attributes = int(getattr(before, "st_file_attributes", 0))
    if (
        stat.S_ISLNK(before.st_mode)
        or attributes & _FILE_ATTRIBUTE_REPARSE_POINT
        or not stat.S_ISREG(before.st_mode)
        or int(getattr(before, "st_nlink", 0)) != 1
    ):
        raise EntrypointRefused(f"{what} is not a one-link plain file")
    digest = hashlib.sha256()
    captured = bytearray()
    try:
        with path.open("rb", buffering=0) as stream:
            opened = os.fstat(stream.fileno())
            if any(
                getattr(before, name, None) != getattr(opened, name, None)
                for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
            ):
                raise EntrypointRefused(f"{what} changed before hashing")
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                captured.extend(chunk)
            after_open = os.fstat(stream.fileno())
    except EntrypointRefused:
        raise
    except OSError as exc:
        raise EntrypointRefused(f"{what} cannot be read") from exc
    try:
        after_path = path.lstat()
    except OSError as exc:
        raise EntrypointRefused(f"{what} disappeared while hashing") from exc
    for after in (after_open, after_path):
        if any(
            getattr(before, name, None) != getattr(after, name, None)
            for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
        ):
            raise EntrypointRefused(f"{what} changed while hashing")
    observed = digest.hexdigest()
    if expected_sha256 is not None and observed != expected_sha256:
        raise EntrypointRefused(f"{what} SHA256 differs")
    return (
        {
            "path": str(path.resolve(strict=True)),
            "sha256": observed,
            "size": int(before.st_size),
        },
        bytes(captured),
    )


def _load_raw_authority(
    helper_path: Path, expected_sha256: str
) -> tuple[ModuleType, dict[str, Any]]:
    """Accept only the helper captured and executed by the outer bootstrap."""

    identity, _ = _bound_file(
        helper_path,
        expected_sha256=expected_sha256,
        what="raw-authority helper",
    )
    module_name = "_bu_week8_d161_raw_authority"
    module = sys.modules.get(module_name)
    specification = getattr(module, "__spec__", None)
    if (
        type(module) is not ModuleType
        or type(getattr(specification, "loader", None))
        is not importlib.machinery.SourceFileLoader
        or type(getattr(module, "__file__", None)) is not str
        or Path(module.__file__).resolve(strict=True) != helper_path.resolve(strict=True)
        or getattr(module, "__source_sha256__", None) != expected_sha256
        or getattr(module, "__source_identity__", None) != identity
    ):
        raise EntrypointRefused("outer-bound raw-authority helper identity differs")
    return module, identity


def _seal_gate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "record_digest" in payload:
        raise EntrypointRefused("unsealed gate contains a digest")
    result = dict(payload)
    result["record_digest"] = _sha256_bytes(_canonical_json_bytes(result))
    return result


def _validate_command(command: object) -> str:
    if type(command) is not str or command not in COMMANDS:
        raise EntrypointRefused("entrypoint command is not allowlisted")
    return command


def _run_verified(
    command: str,
    *,
    config: Mapping[str, Any],
    helper_path: Path,
    expected_helper_sha256: str,
    entrypoint_path: Path,
) -> int:
    """Run one command after the complete pre-import authority succeeds.

    The keyword parameters are a synthetic-test seam.  The direct CLI passes
    only the immutable production constants below and exposes no path option.
    """

    command = _validate_command(command)
    controller_root = Path(str(config.get("controller_root", "")))
    fixed_entrypoint = controller_root / "scripts" / ENTRYPOINT_PATH.name
    if entrypoint_path != fixed_entrypoint:
        raise EntrypointRefused("entrypoint path differs from the fixed controller path")
    outer_literal_sha256 = globals().get("__outer_bootstrap_literal_sha256__")
    outer_entrypoint_sha256 = globals().get("__outer_entrypoint_source_sha256__")
    outer_helper_sha256 = globals().get("__outer_helper_source_sha256__")
    outer_controller_commit = globals().get("__outer_controller_commit__")
    outer_receipt_sha256 = globals().get("__outer_receipt_sha256__")
    outer_native_launcher_sha256 = globals().get(
        "__outer_native_launcher_sha256__"
    )
    outer_stage0_binding_sha256 = globals().get(
        "__outer_stage0_binding_sha256__"
    )
    outer_startup_binding_sha256 = globals().get(
        "__outer_startup_binding_sha256__"
    )
    outer_entrypoint_identity = globals().get("__outer_entrypoint_identity__")
    if (
        outer_literal_sha256 != config.get("outer_bootstrap_literal_sha256")
        or outer_helper_sha256 != expected_helper_sha256
        or type(outer_controller_commit) is not str
        or len(outer_controller_commit) != 40
        or any(character not in "0123456789abcdef" for character in outer_controller_commit)
        or config.get("controller_commit") not in {"", outer_controller_commit}
        or any(
            type(value) is not str
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in (
                outer_receipt_sha256,
                outer_native_launcher_sha256,
                outer_stage0_binding_sha256,
                outer_startup_binding_sha256,
            )
        )
        or config.get("release_receipt_sha256")
        not in {"", outer_receipt_sha256}
        or config.get("native_launcher_sha256")
        not in {"", outer_native_launcher_sha256}
        or config.get("stage0_binding_sha256")
        not in {"", outer_stage0_binding_sha256}
        or config.get("startup_binding_sha256")
        not in {"", outer_startup_binding_sha256}
        or type(outer_entrypoint_sha256) is not str
        or type(outer_entrypoint_identity) is not dict
    ):
        raise EntrypointRefused("outer-bootstrap binding is absent or differs")
    config = dict(config)
    config["controller_commit"] = outer_controller_commit
    config["release_receipt_sha256"] = outer_receipt_sha256
    config["native_launcher_sha256"] = outer_native_launcher_sha256
    config["stage0_binding_sha256"] = outer_stage0_binding_sha256
    config["startup_binding_sha256"] = outer_startup_binding_sha256
    entrypoint_identity, _ = _bound_file(
        entrypoint_path,
        expected_sha256=outer_entrypoint_sha256,
        what="recovery entrypoint",
    )
    if entrypoint_identity != outer_entrypoint_identity:
        raise EntrypointRefused("outer-bound entrypoint identity changed")
    raw_authority, helper_identity = _load_raw_authority(
        helper_path, expected_helper_sha256
    )
    verifier = getattr(raw_authority, "verify_preimport_authority", None)
    revalidator = getattr(raw_authority, "revalidate_admitted_authority", None)
    canonical = getattr(raw_authority, "canonical_json_bytes", None)
    if (
        not callable(verifier)
        or not callable(revalidator)
        or not callable(canonical)
    ):
        raise EntrypointRefused("raw-authority helper API differs")
    authority = verifier(
        dict(config),
        helper_path=helper_path,
        helper_sha256=expected_helper_sha256,
        entrypoint_path=entrypoint_path,
        entrypoint_sha256=outer_entrypoint_sha256,
        command=command,
    )
    if (
        type(authority) is not dict
        or authority.get("record_type") != "week8_d161_preimport_authority"
        or authority.get("decision_id") != DECISION_ID
        or authority.get("scientific_outcomes_consulted") is not False
        or authority.get("scientific_values_emitted") is not False
        or authority.get("production_mutation_performed") is not False
    ):
        raise EntrypointRefused("raw-authority result differs from the fixed contract")
    authority_without_digest = {
        key: value for key, value in authority.items() if key != "record_digest"
    }
    if authority.get("record_digest") != _sha256_bytes(canonical(authority_without_digest)):
        raise EntrypointRefused("raw-authority record digest differs")
    admission = authority.get("admission")
    if type(admission) is not dict or set(admission) != {
        "controller_source",
        "execution_source",
        "pinned_site_packages",
    }:
        raise EntrypointRefused("raw-authority admission record differs")
    source = Path(admission["controller_source"])
    execution_source = Path(admission["execution_source"])
    site_packages = Path(admission["pinned_site_packages"])
    expected_source = controller_root / "src"
    expected_execution_source = Path(str(config.get("execution_root", ""))) / "src"
    expected_site = Path(str(config.get("pinned_site_packages", "")))
    if (
        source != expected_source
        or execution_source != expected_execution_source
        or site_packages != expected_site
    ):
        raise EntrypointRefused("raw-authority admitted an unexpected Python path")
    if any(name == "bu" or name.startswith("bu.") for name in sys.modules):
        raise EntrypointRefused("project package was loaded before path admission")
    finder_api = getattr(raw_authority, "verified_source_finder", None)
    dependency_finder_api = getattr(
        raw_authority, "verified_dependency_finder", None
    )
    if not callable(finder_api) or not callable(dependency_finder_api):
        raise EntrypointRefused("raw-authority verified-import API differs")
    try:
        bound_finder = finder_api(authority, "controller")
        dependency_finder = dependency_finder_api(authority)
    except (OSError, TypeError, ValueError) as exc:
        raise EntrypointRefused("verified controller importer is unavailable") from exc
    if getattr(bound_finder, "binding_marker", None) != "week8_d161_verified_source_v2":
        raise EntrypointRefused("verified controller importer has another identity")
    if (
        getattr(dependency_finder, "binding_marker", None)
        != "week8_d161_verified_dependency_source_v1"
    ):
        raise EntrypointRefused("verified dependency importer has another identity")
    gate = _seal_gate(
        {
            "entrypoint_gate_schema_version": ENTRYPOINT_GATE_SCHEMA_VERSION,
            "record_type": "week8_d161_entrypoint_gate",
            "decision_id": DECISION_ID,
            "command": command,
            "entrypoint": entrypoint_identity,
            "raw_authority_helper": helper_identity,
            "raw_authority": authority,
            "admitted_pythonpath": [str(source), str(site_packages)],
            "scientific_outcomes_consulted": False,
            "scientific_values_emitted": False,
            "production_mutation_performed": False,
        }
    )
    inherited_standard_library = tuple(sys.path)
    sys.path[:] = [str(source), *inherited_standard_library, str(site_packages)]
    sys.meta_path[:0] = [bound_finder, dependency_finder]
    os.environ["PYTHONPATH"] = os.pathsep.join((str(source), str(site_packages)))
    os.environ[GATE_ENVIRONMENT_NAME] = _canonical_json_bytes(gate).decode("ascii")
    importlib = __import__("importlib")
    importlib.invalidate_caches()
    controller = importlib.import_module("bu.experiments.week8_exp2a_recovery")
    expected_module = source / "bu" / "experiments" / "week8_exp2a_recovery.py"
    specification = getattr(controller, "__spec__", None)
    if (
        type(getattr(controller, "__file__", None)) is not str
        or Path(controller.__file__).resolve(strict=True) != expected_module.resolve(
            strict=True
        )
        or getattr(
            getattr(specification, "loader", None), "binding_marker", None
        )
        != "week8_d161_verified_source_v2"
    ):
        raise EntrypointRefused("recovery controller source identity differs")
    controller_main = getattr(controller, "main", None)
    if not callable(controller_main):
        raise EntrypointRefused("recovery controller main is unavailable")
    result = controller_main([command])
    if type(result) is not int:
        raise EntrypointRefused("recovery controller returned a non-integer status")
    return result


def _refusal(command: object, exc: BaseException) -> dict[str, Any]:
    command_value = command if type(command) is str and command in COMMANDS else "invalid"
    return {
        "entrypoint_gate_schema_version": ENTRYPOINT_GATE_SCHEMA_VERSION,
        "record_type": "week8_d161_entrypoint_refusal",
        "decision_id": DECISION_ID,
        "command": command_value,
        "status": "refused",
        "error_type": type(exc).__name__,
        "error_sha256": _sha256_bytes(str(exc).encode("utf-8", errors="strict")),
        "automatic_retry_allowed": False,
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    command: object = arguments[0] if len(arguments) == 1 else None
    try:
        command = _validate_command(command)
        return _run_verified(
            command,
            config=PRODUCTION_CONFIG,
            helper_path=RAW_AUTHORITY_HELPER,
            expected_helper_sha256=RAW_AUTHORITY_HELPER_SHA256,
            entrypoint_path=ENTRYPOINT_PATH,
        )
    except (ImportError, OSError, TypeError, ValueError) as exc:
        print(_canonical_json_bytes(_refusal(command, exc)).decode("ascii"))
        return 2


if __name__ == "__main__":  # pragma: no cover - subprocess contract
    raise SystemExit(main())
