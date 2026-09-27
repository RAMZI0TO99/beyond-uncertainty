"""Standard-library-only raw authority for the Week-8 D-161 recovery.

This module is loaded by absolute path only after its bytes have been bound by
the entrypoint.  It deliberately imports no project or third-party package.
Its Git surface is four read-only plumbing queries; working-tree truth comes
from Python's own byte hashing and exact filesystem enumeration, so repository
filters, pagers, hooks, and status helpers are never authority inputs.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any, Mapping, Sequence


RAW_AUTHORITY_SCHEMA_VERSION = 4
DECISION_ID = "D-161"
GATE_ENVIRONMENT_NAME = "BU_D161_ENTRYPOINT_GATE"
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_PLAIN_BLOB_MODES = frozenset({"100644", "100755"})
_CONFIG_KEYS = frozenset(
    {
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
        "pinned_local_appdata",
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
)
_STARTUP_PYTHON_ENVIRONMENT: dict[str, str] = {}
_AUTHORITY_RECORD_KEYS = frozenset(
    {
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
)
_RUNTIME_RECORD_KEYS = frozenset(
    {
        "flags",
        "startup_options",
        "entrypoint_path",
        "command",
        "python_environment",
        "startup_environment",
        "working_directory",
        "active_runtime",
        "preimport_sys_path_digest",
        "pinned_python",
        "pinned_base_python",
        "pinned_site_packages",
        "outer_bootstrap_literal_sha256",
        "entrypoint_source_sha256",
    }
)
_RUNTIME_FLAG_KEYS = frozenset(
    {
        "dont_write_bytecode",
        "ignore_environment",
        "isolated",
        "no_site",
        "no_user_site",
        "safe_path",
        "utf8_mode",
    }
)
_ACTIVE_RUNTIME_KEYS = frozenset(
    {"executable", "base_executable", "prefix", "base_prefix"}
)
_NATIVE_STARTUP_KEYS = frozenset(
    {
        "release_receipt_sha256",
        "native_launcher",
        "stage0_binding_sha256",
        "startup_binding_sha256",
        "native_powershell",
        "native_runtime",
        "startup_environment_sha256",
        "pinned_pyvenv",
        "pinned_venv_scripts",
        "pinned_base_runtime",
    }
)
_NATIVE_TREE_IDENTITY_KEYS = frozenset(
    {"path", "file_count", "directory_count", "total_bytes", "inventory_sha256"}
)
_FILE_IDENTITY_KEYS = frozenset({"path", "size", "sha256"})
_PLAIN_TREE_IDENTITY_KEYS = frozenset(
    {
        "path",
        "file_count",
        "directory_count",
        "total_bytes",
        "inventory_digest",
        "stability_observations",
        "captured_python_source_count",
        "retained_read_lock_count",
    }
)
_WORKTREE_IDENTITY_KEYS = frozenset(
    {
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
)
_ADMISSION_KEYS = frozenset(
    {"controller_source", "execution_source", "pinned_site_packages"}
)
_OBSERVED_WORKTREES: dict[str, dict[str, Any]] = {}
_OBSERVED_PLAIN_TREES: dict[str, dict[str, Any]] = {}
_RETAINED_FILE_HANDLES: dict[str, dict[str, int]] = {}


class AuthorityRefused(ValueError):
    """The pre-import authority could not be proved exactly."""


class VerifiedSourceLoader:
    """Execute one project module only from raw-authority-captured bytes."""

    binding_marker = "week8_d161_verified_source_v2"

    def __init__(
        self,
        *,
        fullname: str,
        path: Path,
        source: bytes,
        is_package: bool,
        tree_kind: str,
        git_blob: str,
        authority_tree_digest: str,
    ) -> None:
        self.name = fullname
        self.path = str(path)
        self._source = source
        self._is_package = is_package
        self.tree_kind = tree_kind
        self.git_blob = git_blob
        self.authority_tree_digest = authority_tree_digest
        self.source_sha256 = sha256_bytes(source)

    def create_module(self, specification: object) -> None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        module.__file__ = self.path
        module.__loader__ = self
        exec(
            compile(self._source, self.path, "exec", dont_inherit=True),
            module.__dict__,
        )

    def get_filename(self, fullname: str) -> str:
        if fullname != self.name:
            raise ImportError("verified source loader received another module")
        return self.path

    def get_code(self, fullname: str) -> object:
        if fullname != self.name:
            raise ImportError("verified source loader received another module")
        return compile(self._source, self.path, "exec", dont_inherit=True)

    def is_package(self, fullname: str) -> bool:
        if fullname != self.name:
            raise ImportError("verified source loader received another module")
        return self._is_package


class VerifiedSourceFinder:
    """Refuse disk fallback for every module in one verified ``bu`` tree."""

    binding_marker = VerifiedSourceLoader.binding_marker

    def __init__(
        self,
        *,
        authority: Mapping[str, Any],
        which: str,
        source_root: Path,
        captured: Mapping[str, bytes],
    ) -> None:
        if which not in {"controller", "execution"}:
            raise AuthorityRefused("verified source tree is not allowlisted")
        self.tree_kind = which
        self.authority_tree_digest = authority[which]["worktree_inventory_digest"]
        self._modules: dict[str, tuple[Path, bytes, bool, str]] = {}
        for relative, source in sorted(captured.items()):
            if not relative.startswith("src/bu/") or not relative.endswith(".py"):
                continue
            beneath = relative[len("src/") :]
            parts = beneath.split("/")
            is_package = parts[-1] == "__init__.py"
            module_parts = (
                parts[:-1] if is_package else [*parts[:-1], parts[-1][:-3]]
            )
            fullname = ".".join(module_parts)
            if not fullname or fullname in self._modules:
                raise AuthorityRefused("verified project module map is ambiguous")
            blob = admitted_git_blob(authority, which, relative)
            self._modules[fullname] = (
                source_root / beneath,
                source,
                is_package,
                blob,
            )
        if "bu" not in self._modules:
            raise AuthorityRefused("verified project module map lacks package root")

    def find_spec(
        self, fullname: str, path: object = None, target: object = None
    ) -> object:
        if fullname != "bu" and not fullname.startswith("bu."):
            return None
        row = self._modules.get(fullname)
        if row is None:
            raise ImportError(f"{fullname} is absent from verified project source")
        source_path, source, is_package, blob = row
        loader = VerifiedSourceLoader(
            fullname=fullname,
            path=source_path,
            source=source,
            is_package=is_package,
            tree_kind=self.tree_kind,
            git_blob=blob,
            authority_tree_digest=self.authority_tree_digest,
        )
        return importlib.util.spec_from_loader(
            fullname,
            loader,
            origin=str(source_path),
            is_package=is_package,
        )


class VerifiedDependencyLoader(importlib.machinery.SourceFileLoader):
    """Execute one third-party Python module only from captured site bytes."""

    binding_marker = "week8_d161_verified_dependency_source_v1"

    def __init__(
        self,
        *,
        fullname: str,
        path: Path,
        source: bytes,
        is_package: bool,
        authority_tree_digest: str,
        site_root: Path,
        rows: Mapping[str, Mapping[str, Any]],
    ) -> None:
        super().__init__(fullname, str(path))
        self.path = str(path)
        self._source = source
        self._is_package = is_package
        self.tree_kind = "pinned_site_packages"
        self.authority_tree_digest = authority_tree_digest
        self.source_sha256 = sha256_bytes(source)
        self._site_root = site_root
        self._rows = dict(rows)

    def create_module(self, specification: object) -> None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        module.__file__ = self.path
        module.__loader__ = self
        exec(
            compile(self._source, self.path, "exec", dont_inherit=True),
            module.__dict__,
        )

    def get_filename(self, fullname: str) -> str:
        if fullname != self.name:
            raise ImportError("verified dependency loader received another module")
        return self.path

    def get_code(self, fullname: str) -> object:
        if fullname != self.name:
            raise ImportError("verified dependency loader received another module")
        return compile(self._source, self.path, "exec", dont_inherit=True)

    def get_source(self, fullname: str) -> str:
        if fullname != self.name:
            raise ImportError("verified dependency loader received another module")
        try:
            return self._source.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ImportError("verified dependency source is not UTF-8") from exc

    def get_data(self, path: str) -> bytes:
        if type(path) is not str:
            raise OSError("verified dependency data path is not fixed")
        try:
            resolved = Path(path).resolve(strict=True)
            relative = resolved.relative_to(self._site_root).as_posix()
        except (OSError, ValueError) as exc:
            raise OSError("verified dependency data is outside site-packages") from exc
        row = self._rows.get(relative)
        if type(row) is not dict or row.get("kind") != "file":
            raise OSError("verified dependency data is absent from authority")
        data, identity = _read_plain_file_bytes(
            resolved, what=f"verified dependency data {relative}"
        )
        if (
            identity["size"] != row.get("size")
            or identity["sha256"] != row.get("sha256")
        ):
            raise OSError("verified dependency data identity differs")
        return data

    def set_data(self, path: str, data: bytes, *args: object, **kwargs: object) -> None:
        raise PermissionError("verified dependency loader is read-only")

    def is_package(self, fullname: str) -> bool:
        if fullname != self.name:
            raise ImportError("verified dependency loader received another module")
        return self._is_package


class VerifiedDependencyFinder:
    """Bind every executable import beneath the frozen site-packages tree."""

    binding_marker = VerifiedDependencyLoader.binding_marker

    def __init__(
        self,
        *,
        site_root: Path,
        inventory_digest: str,
        rows: Mapping[str, Mapping[str, Any]],
        python_sources: Mapping[str, bytes],
        retained_paths: frozenset[str],
    ) -> None:
        self.site_root = site_root
        self.authority_tree_digest = inventory_digest
        self._rows = dict(rows)
        self._python_sources = dict(python_sources)
        self._retained_paths = retained_paths

    def _relative_origin(self, origin: str) -> str | None:
        try:
            resolved = Path(origin).resolve(strict=True)
            relative = resolved.relative_to(self.site_root).as_posix()
        except (OSError, ValueError):
            return None
        return relative

    def find_spec(
        self, fullname: str, path: object = None, target: object = None
    ) -> object:
        specification = importlib.machinery.PathFinder.find_spec(
            fullname, path, target
        )
        if specification is None:
            return None
        origin = getattr(specification, "origin", None)
        if origin is None:
            locations = getattr(specification, "submodule_search_locations", None)
            if locations is None:
                return None
            for location in locations:
                if type(location) is not str:
                    raise ImportError("dependency namespace location is not fixed")
                try:
                    Path(location).resolve(strict=True).relative_to(self.site_root)
                except ValueError:
                    continue
                except OSError as exc:
                    raise ImportError(
                        "dependency namespace location is unavailable"
                    ) from exc
            return specification
        if type(origin) is not str or origin in {"built-in", "frozen"}:
            return None
        relative = self._relative_origin(origin)
        if relative is None:
            return None
        row = self._rows.get(relative)
        if type(row) is not dict or row.get("kind") != "file":
            raise ImportError(f"{fullname} is absent from verified dependencies")
        suffix = Path(relative).suffix.lower()
        if suffix in {".pyc", ".pyo"}:
            raise ImportError("verified dependencies forbid bytecode execution")
        if suffix == ".py":
            source = self._python_sources.get(relative)
            if type(source) is not bytes:
                raise ImportError("verified dependency source bytes are unavailable")
            if (
                len(source) != row.get("size")
                or sha256_bytes(source) != row.get("sha256")
            ):
                raise ImportError("verified dependency source identity differs")
            is_package = getattr(
                specification, "submodule_search_locations", None
            ) is not None
            loader = VerifiedDependencyLoader(
                fullname=fullname,
                path=self.site_root / Path(*relative.split("/")),
                source=source,
                is_package=is_package,
                authority_tree_digest=self.authority_tree_digest,
                site_root=self.site_root,
                rows=self._rows,
            )
            bound = importlib.util.spec_from_loader(
                fullname,
                loader,
                origin=str(self.site_root / Path(*relative.split("/"))),
                is_package=is_package,
            )
            if bound is None:
                raise ImportError("verified dependency specification is unavailable")
            if is_package:
                bound.submodule_search_locations = list(
                    specification.submodule_search_locations
                )
            return bound
        if relative not in self._retained_paths:
            raise ImportError("native dependency lacks a retained read lock")
        return specification


def canonical_json_bytes(value: object) -> bytes:
    """Return the one canonical JSON encoding used by authority records."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise AuthorityRefused("authority value is not canonical JSON") from exc
    return encoded


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _startup_environment_pairs(
    config: Mapping[str, Any],
) -> tuple[tuple[str, str], ...]:
    base_runtime = str(
        _absolute_path(config["pinned_base_runtime"], what="pinned base runtime")
    )
    native_runtime = str(
        _absolute_path(config["native_runtime"], what="native startup runtime")
    )
    local_appdata = str(
        _absolute_path(config["pinned_local_appdata"], what="pinned local appdata")
    )
    return (
        ("CUDA_VISIBLE_DEVICES", "-1"),
        ("HIP_VISIBLE_DEVICES", "-1"),
        ("LOCALAPPDATA", local_appdata),
        ("MKL_NUM_THREADS", "4"),
        ("NUMEXPR_NUM_THREADS", "4"),
        ("OMP_NUM_THREADS", "4"),
        ("OPENBLAS_NUM_THREADS", "4"),
        ("PATH", os.pathsep.join((base_runtime, "C:\\Windows\\System32", "C:\\Windows"))),
        ("SystemRoot", "C:\\Windows"),
        ("TEMP", native_runtime),
        ("TMP", native_runtime),
        ("TMPDIR", native_runtime),
        ("WINDIR", "C:\\Windows"),
    )


def _startup_environment_sha256(
    pairs: Sequence[tuple[str, str]],
) -> str:
    rows = ["WEEK8_D168_STARTUP_ENVIRONMENT_V2"]
    for name, value in pairs:
        if "=" in name or "\r" in value or "\n" in value:
            raise AuthorityRefused("native startup environment row is malformed")
        rows.append(f"{name}={value}")
    return sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def _native_tree_identity(root: Path) -> dict[str, Any]:
    """Reproduce the pre-Python launcher's ordinal TSV tree identity."""

    root = _plain_directory(root, what="native startup tree")

    def observe() -> tuple[dict[str, Any], tuple[tuple[str, str, int, str], ...]]:
        files, directories = _filesystem_inventory(root)
        rows: list[tuple[str, str, int, str]] = []
        for relative in directories:
            rows.append((relative, "D", 0, ""))
        for relative, path in files.items():
            identity = _hash_plain_file(
                path, what=f"native startup path {relative}", git_blob=False
            )
            rows.append(
                (relative, "F", identity["size"], identity["sha256"])
            )
        ordered = tuple(sorted(rows, key=lambda row: row[0]))
        payload = bytearray()
        for relative, kind, size, digest in ordered:
            if kind == "D":
                payload.extend(f"D\t{relative}\n".encode("utf-8"))
            else:
                payload.extend(
                    f"F\t{relative}\t{size}\t{digest}\n".encode("utf-8")
                )
        record = {
            "path": str(root),
            "file_count": len(files),
            "directory_count": len(directories),
            "total_bytes": sum(row[2] for row in ordered if row[1] == "F"),
            "inventory_sha256": sha256_bytes(bytes(payload)),
        }
        return record, ordered

    first, first_rows = observe()
    second, second_rows = observe()
    if first != second or first_rows != second_rows:
        raise AuthorityRefused("native startup tree changed between observations")
    return first


def _validate_native_tree_identity(
    value: object, *, what: str
) -> dict[str, Any]:
    record = _exact_mapping(value, keys=_NATIVE_TREE_IDENTITY_KEYS, what=what)
    path = _absolute_path(record["path"], what=f"{what} path")
    for name in ("file_count", "directory_count", "total_bytes"):
        _exact_nonnegative_integer(record[name], what=f"{what} {name}")
    digest = _exact_sha256(record["inventory_sha256"], what=f"{what} digest")
    return {
        "path": str(path),
        "file_count": record["file_count"],
        "directory_count": record["directory_count"],
        "total_bytes": record["total_bytes"],
        "inventory_sha256": digest,
    }


def _expected_native_tree(
    config: Mapping[str, Any], *, prefix: str, path_key: str
) -> dict[str, Any]:
    return {
        "path": str(_absolute_path(config[path_key], what=path_key)),
        "file_count": _exact_nonnegative_integer(
            config[f"{prefix}_file_count"], what=f"{prefix} file count"
        ),
        "directory_count": _exact_nonnegative_integer(
            config[f"{prefix}_directory_count"],
            what=f"{prefix} directory count",
        ),
        "total_bytes": _exact_nonnegative_integer(
            config[f"{prefix}_total_bytes"], what=f"{prefix} total bytes"
        ),
        "inventory_sha256": _exact_sha256(
            config[f"{prefix}_inventory_sha256"],
            what=f"{prefix} inventory SHA-256",
        ),
    }


def _startup_binding_sha256(
    config: Mapping[str, Any],
    *,
    command: str,
    entrypoint_sha256: str,
    helper_sha256: str,
    base_runtime: Mapping[str, Any],
    venv_scripts: Mapping[str, Any],
    startup_environment_sha256: str,
) -> str:
    rows = (
        "WEEK8_D168_STARTUP_BINDING_V2",
        f"powershell={config['native_powershell']}",
        f"receipt_sha256={config['release_receipt_sha256']}",
        f"native_launcher_sha256={config['native_launcher_sha256']}",
        f"stage0_binding_sha256={config['stage0_binding_sha256']}",
        f"controller_commit={config['controller_commit']}",
        f"outer_sha256={config['outer_bootstrap_literal_sha256']}",
        f"entry_sha256={entrypoint_sha256}",
        f"helper_sha256={helper_sha256}",
        f"command={command}",
        f"runtime_path={config['native_runtime']}",
        f"python_path={config['pinned_python']}",
        f"python_sha256={config['pinned_python_sha256']}",
        f"base_python_path={config['pinned_base_python']}",
        f"base_python_sha256={config['pinned_base_python_sha256']}",
        f"prefix_path={config['pinned_base_runtime']}",
        f"base_prefix_path={config['pinned_base_runtime']}",
        f"pyvenv_path={config['pinned_pyvenv']}",
        f"pyvenv_sha256={config['pinned_pyvenv_sha256']}",
        f"venv_scripts_path={venv_scripts['path']}",
        f"venv_scripts_file_count={venv_scripts['file_count']}",
        f"venv_scripts_directory_count={venv_scripts['directory_count']}",
        f"venv_scripts_total_bytes={venv_scripts['total_bytes']}",
        f"venv_scripts_inventory_sha256={venv_scripts['inventory_sha256']}",
        f"base_runtime_path={base_runtime['path']}",
        f"base_runtime_file_count={base_runtime['file_count']}",
        f"base_runtime_directory_count={base_runtime['directory_count']}",
        f"base_runtime_total_bytes={base_runtime['total_bytes']}",
        f"base_runtime_inventory_sha256={base_runtime['inventory_sha256']}",
        f"startup_environment_sha256={startup_environment_sha256}",
    )
    return sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def _validate_native_startup(
    config: Mapping[str, Any],
    *,
    command: str,
    entrypoint_sha256: str,
    helper_sha256: str,
) -> dict[str, Any]:
    receipt_sha256 = _exact_sha256(
        config["release_receipt_sha256"], what="release receipt SHA-256"
    )
    launcher_sha256 = _exact_sha256(
        config["native_launcher_sha256"], what="native launcher SHA-256"
    )
    stage0_binding_sha256 = _exact_sha256(
        config["stage0_binding_sha256"], what="stage-0 binding SHA-256"
    )
    configured_binding = _exact_sha256(
        config["startup_binding_sha256"], what="native startup binding SHA-256"
    )
    launcher_path = _absolute_path(
        config["native_launcher"], what="native launcher"
    )
    launcher = _file_identity(
        launcher_path,
        expected_sha256=launcher_sha256,
        what="native launcher",
    )
    powershell = _absolute_path(
        config["native_powershell"], what="native PowerShell host"
    )
    expected_powershell = Path(
        "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    ).resolve(strict=True)
    if powershell != expected_powershell:
        raise AuthorityRefused("native PowerShell host differs from the Windows trust root")

    pinned_python = _absolute_path(config["pinned_python"], what="pinned Python")
    base_python = _absolute_path(
        config["pinned_base_python"], what="pinned base Python"
    )
    base_root = _absolute_path(
        config["pinned_base_runtime"], what="pinned base runtime"
    )
    pyvenv_path = _absolute_path(config["pinned_pyvenv"], what="pyvenv.cfg")
    venv_scripts_root = _absolute_path(
        config["pinned_venv_scripts"], what="pinned venv Scripts"
    )
    if (
        base_python.parent != base_root
        or pinned_python.parent != venv_scripts_root
        or pyvenv_path.parent != venv_scripts_root.parent
    ):
        raise AuthorityRefused("native Python startup roots are not structurally fixed")
    pyvenv = _file_identity(
        pyvenv_path,
        expected_sha256=config["pinned_pyvenv_sha256"],
        what="pyvenv.cfg",
    )
    pyvenv_bytes, repeated_pyvenv = _read_plain_file_bytes(
        pyvenv_path, what="pyvenv.cfg semantics"
    )
    if repeated_pyvenv != pyvenv:
        raise AuthorityRefused("pyvenv.cfg changed before semantic validation")
    expected_pyvenv = (
        f"home = {base_root}\r\n"
        "include-system-site-packages = false\r\n"
        "version = 3.13.5\r\n"
        f"executable = {base_python}\r\n"
        f"command = {base_python} -m venv {venv_scripts_root.parent}\r\n"
    ).encode("utf-8")
    if pyvenv_bytes != expected_pyvenv:
        raise AuthorityRefused("pyvenv.cfg startup semantics differ")

    base_runtime = _native_tree_identity(base_root)
    venv_scripts = _native_tree_identity(venv_scripts_root)
    expected_base = _expected_native_tree(
        config,
        prefix="pinned_base_runtime",
        path_key="pinned_base_runtime",
    )
    expected_venv = _expected_native_tree(
        config,
        prefix="pinned_venv_scripts",
        path_key="pinned_venv_scripts",
    )
    if base_runtime != expected_base or venv_scripts != expected_venv:
        raise AuthorityRefused("native Python startup tree differs from fixed config")

    environment_pairs = _startup_environment_pairs(config)
    environment_sha256 = _startup_environment_sha256(environment_pairs)
    observed_binding = _startup_binding_sha256(
        config,
        command=command,
        entrypoint_sha256=entrypoint_sha256,
        helper_sha256=helper_sha256,
        base_runtime=base_runtime,
        venv_scripts=venv_scripts,
        startup_environment_sha256=environment_sha256,
    )
    original_arguments = tuple(getattr(sys, "orig_argv", ()))
    if (
        len(original_arguments) != 16
        or original_arguments[12] != receipt_sha256
        or original_arguments[13] != launcher_sha256
        or original_arguments[14] != stage0_binding_sha256
        or original_arguments[15] != configured_binding
        or observed_binding != configured_binding
    ):
        raise AuthorityRefused("native startup binding differs from the captured launch")

    native_runtime = _plain_directory(
        _absolute_path(config["native_runtime"], what="native startup runtime"),
        what="native startup runtime",
    )
    workspace = _absolute_path(
        config["controller_root"], what="controller root"
    ).parent
    if native_runtime.parent != workspace:
        raise AuthorityRefused("native runtime is not one direct project-local directory")
    runtime_files, runtime_directories = _filesystem_inventory(native_runtime)
    if runtime_files or runtime_directories:
        raise AuthorityRefused("native startup runtime was not empty before authority")

    return {
        "release_receipt_sha256": receipt_sha256,
        "native_launcher": launcher,
        "stage0_binding_sha256": stage0_binding_sha256,
        "startup_binding_sha256": observed_binding,
        "native_powershell": str(powershell),
        "native_runtime": str(native_runtime),
        "startup_environment_sha256": environment_sha256,
        "pinned_pyvenv": pyvenv,
        "pinned_venv_scripts": venv_scripts,
        "pinned_base_runtime": base_runtime,
    }


def seal_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Seal an exact-key record without accepting a caller-supplied digest."""

    if "record_digest" in payload:
        raise AuthorityRefused("unsealed authority payload contains record_digest")
    document = dict(payload)
    document["record_digest"] = sha256_bytes(canonical_json_bytes(document))
    return document


def _exact_mapping(value: object, *, keys: frozenset[str], what: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        raise AuthorityRefused(f"{what} keys differ from the fixed contract")
    return value


def _absolute_path(value: object, *, what: str) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        raise AuthorityRefused(f"{what} is not a fixed absolute path")
    path = Path(value)
    if not path.is_absolute() or str(path) != value:
        raise AuthorityRefused(f"{what} is not a fixed absolute path")
    return Path(os.path.abspath(path))


def _is_reparse(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def _lstat(path: Path, *, what: str) -> os.stat_result:
    try:
        return path.lstat()
    except OSError as exc:
        raise AuthorityRefused(f"{what} is unavailable") from exc


def _plain_directory(path: Path, *, what: str) -> Path:
    info = _lstat(path, what=what)
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
        raise AuthorityRefused(f"{what} is not a plain directory")
    try:
        return path.resolve(strict=True)
    except OSError as exc:
        raise AuthorityRefused(f"{what} cannot be resolved") from exc


def _plain_file_info(path: Path, *, what: str) -> os.stat_result:
    info = _lstat(path, what=what)
    if (
        stat.S_ISLNK(info.st_mode)
        or _is_reparse(info)
        or not stat.S_ISREG(info.st_mode)
        or int(getattr(info, "st_nlink", 0)) != 1
    ):
        raise AuthorityRefused(f"{what} is not a one-link plain file")
    return info


def _same_file_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
    return all(getattr(left, name, None) == getattr(right, name, None) for name in fields)


def _hash_plain_file(path: Path, *, what: str, git_blob: bool) -> dict[str, Any]:
    """Hash one stable, non-linked regular file without retaining its bytes."""

    before = _plain_file_info(path, what=what)
    sha256 = hashlib.sha256()
    sha1 = hashlib.sha1() if git_blob else None  # Git repository is frozen as SHA-1.
    if sha1 is not None:
        sha1.update(b"blob " + str(before.st_size).encode("ascii") + b"\0")
    try:
        with path.open("rb", buffering=0) as stream:
            opened = os.fstat(stream.fileno())
            if not _same_file_snapshot(before, opened) or _is_reparse(opened):
                raise AuthorityRefused(f"{what} changed before hashing")
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                sha256.update(chunk)
                if sha1 is not None:
                    sha1.update(chunk)
            after_open = os.fstat(stream.fileno())
    except AuthorityRefused:
        raise
    except OSError as exc:
        raise AuthorityRefused(f"{what} cannot be read") from exc
    after_path = _plain_file_info(path, what=what)
    if (
        not _same_file_snapshot(before, after_open)
        or not _same_file_snapshot(before, after_path)
    ):
        raise AuthorityRefused(f"{what} changed while hashing")
    result: dict[str, Any] = {
        "path": str(path.resolve(strict=True)),
        "size": int(before.st_size),
        "sha256": sha256.hexdigest(),
    }
    if sha1 is not None:
        result["git_blob"] = sha1.hexdigest()
    return result


def _read_plain_file_bytes(path: Path, *, what: str) -> tuple[bytes, dict[str, Any]]:
    """Read one stable plain file and retain exactly the bytes that were hashed."""

    before = _plain_file_info(path, what=what)
    try:
        with path.open("rb", buffering=0) as stream:
            opened = os.fstat(stream.fileno())
            if not _same_file_snapshot(before, opened) or _is_reparse(opened):
                raise AuthorityRefused(f"{what} changed before capture")
            data = stream.read()
            after_open = os.fstat(stream.fileno())
    except AuthorityRefused:
        raise
    except OSError as exc:
        raise AuthorityRefused(f"{what} cannot be captured") from exc
    after_path = _plain_file_info(path, what=what)
    if (
        len(data) != before.st_size
        or not _same_file_snapshot(before, after_open)
        or not _same_file_snapshot(before, after_path)
    ):
        raise AuthorityRefused(f"{what} changed while being captured")
    return data, {
        "path": str(path.resolve(strict=True)),
        "size": int(before.st_size),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _file_identity(path: Path, *, expected_sha256: str, what: str) -> dict[str, Any]:
    if type(expected_sha256) is not str or _HEX64.fullmatch(expected_sha256) is None:
        raise AuthorityRefused(f"{what} expected SHA256 is malformed")
    identity = _hash_plain_file(path, what=what, git_blob=False)
    if identity["sha256"] != expected_sha256:
        raise AuthorityRefused(f"{what} SHA256 differs")
    return identity


def _same_path(left: Path, right: Path, *, what: str) -> None:
    try:
        same = os.path.samefile(left, right)
    except OSError as exc:
        raise AuthorityRefused(f"{what} paths cannot be compared") from exc
    if not same:
        raise AuthorityRefused(f"{what} path differs")


def _isolated_git_environment(git_executable: Path) -> dict[str, str]:
    """Return the minimal fixed environment for raw Git plumbing.

    The executable is absolute, but on Windows its native dependencies are
    still resolved relative to the program directory and ``PATH``.  Never
    inherit an operator-controlled search path, HOME, pager, hooks or Git
    configuration into this pre-import boundary.
    """

    runtime = _plain_directory(git_executable.parent, what="pinned Git runtime")
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        get_windows = ctypes.WinDLL(
            "kernel32", use_last_error=True
        ).GetSystemWindowsDirectoryW
        get_windows.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        get_windows.restype = ctypes.c_uint32
        length = get_windows(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            raise OSError("native Windows directory query failed")
        system_root = _plain_directory(
            Path(buffer.value), what="native Windows system root"
        )
        system32 = _plain_directory(
            system_root / "System32", what="native Windows System32"
        )
    except (AttributeError, OSError) as exc:
        raise AuthorityRefused("Windows system runtime is unavailable") from exc
    return {
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
        "PATH": os.pathsep.join((str(runtime), str(system32), str(system_root))),
        "SystemRoot": str(system_root),
        "WINDIR": str(system_root),
    }


def _validate_git_arguments(arguments: Sequence[str]) -> None:
    exact = {
        ("rev-parse", "--verify", "HEAD^{commit}"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("ls-files", "--stage", "-z"),
    }
    candidate = tuple(arguments)
    tree_query = (
        len(candidate) == 5
        and candidate[:4] == ("ls-tree", "-r", "-z", "--full-tree")
        and _HEX40.fullmatch(candidate[4]) is not None
    )
    if candidate not in exact and not tree_query:
        raise AuthorityRefused("Git query is outside the raw-authority allowlist")


def _git_bytes(root: Path, git_executable: Path, *arguments: str) -> bytes:
    _validate_git_arguments(arguments)
    safe_root = _plain_directory(root, what="Git worktree")
    executable = _plain_file_info(git_executable, what="pinned Git executable")
    del executable
    command = [
        str(git_executable.resolve(strict=True)),
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
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_isolated_git_environment(git_executable),
            cwd=git_executable.parent,
            shell=False,
        )
    except OSError as exc:
        raise AuthorityRefused("pinned Git could not execute") from exc
    if completed.returncode != 0:
        raise AuthorityRefused(
            "raw Git query refused; stderr SHA256=" + sha256_bytes(completed.stderr)
        )
    return completed.stdout


def _one_text_line(data: bytes, *, what: str) -> str:
    try:
        value = data.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise AuthorityRefused(f"{what} is not canonical UTF-8") from exc
    if not value or "\n" in value or "\r" in value:
        raise AuthorityRefused(f"{what} is not one canonical line")
    return value


def _decode_repo_path(data: bytes, *, what: str) -> str:
    try:
        value = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AuthorityRefused(f"{what} path is not canonical UTF-8") from exc
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or value == ".git"
        or value.startswith(".git/")
    ):
        raise AuthorityRefused(f"{what} contains a non-canonical path")
    return value


def _parse_tree(data: bytes) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    records = data.split(b"\0")
    if records[-1:] != [b""]:
        raise AuthorityRefused("Git tree output lacks its terminal NUL")
    for record in records[:-1]:
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, raw_oid = metadata.split(b" ", 2)
            mode_text = mode.decode("ascii", errors="strict")
            object_type_text = object_type.decode("ascii", errors="strict")
            oid = raw_oid.decode("ascii", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise AuthorityRefused("Git tree output is malformed") from exc
        path = _decode_repo_path(raw_path, what="Git tree")
        if (
            mode_text not in _PLAIN_BLOB_MODES
            or object_type_text != "blob"
            or _HEX40.fullmatch(oid) is None
            or path in entries
        ):
            raise AuthorityRefused("Git tree contains a non-plain or duplicate entry")
        entries[path] = (mode_text, oid)
    if not entries:
        raise AuthorityRefused("Git tree is empty")
    return entries


def _parse_index(data: bytes) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    records = data.split(b"\0")
    if records[-1:] != [b""]:
        raise AuthorityRefused("Git index output lacks its terminal NUL")
    for record in records[:-1]:
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, raw_oid, stage = metadata.split(b" ", 2)
            mode_text = mode.decode("ascii", errors="strict")
            oid = raw_oid.decode("ascii", errors="strict")
            stage_text = stage.decode("ascii", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise AuthorityRefused("Git index output is malformed") from exc
        path = _decode_repo_path(raw_path, what="Git index")
        if (
            mode_text not in _PLAIN_BLOB_MODES
            or _HEX40.fullmatch(oid) is None
            or stage_text != "0"
            or path in entries
        ):
            raise AuthorityRefused("Git index contains a non-plain or unmerged entry")
        entries[path] = (mode_text, oid)
    return entries


def _expected_directories(paths: Sequence[str]) -> set[str]:
    expected: set[str] = set()
    for value in paths:
        parts = value.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            expected.add("/".join(parts[:index]))
    return expected


def _filesystem_inventory(
    root: Path, *, exclude_git_control: bool = False
) -> tuple[dict[str, Path], set[str]]:
    files: dict[str, Path] = {}
    directories: set[str] = set()

    def visit(directory: Path, relative: str) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda row: row.name)
        except OSError as exc:
            raise AuthorityRefused("worktree filesystem cannot be enumerated") from exc
        for entry in entries:
            if exclude_git_control and not relative and entry.name == ".git":
                continue
            if entry.name in {"", ".", ".."} or "/" in entry.name or "\\" in entry.name:
                raise AuthorityRefused("worktree filesystem contains a non-canonical name")
            child_relative = f"{relative}/{entry.name}" if relative else entry.name
            child = directory / entry.name
            info = _lstat(child, what=f"worktree path {child_relative}")
            if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
                raise AuthorityRefused("worktree contains a linked or reparse path")
            if stat.S_ISDIR(info.st_mode):
                directories.add(child_relative)
                visit(child, child_relative)
            elif stat.S_ISREG(info.st_mode):
                if int(getattr(info, "st_nlink", 0)) != 1:
                    raise AuthorityRefused("worktree contains a hardlinked file")
                files[child_relative] = child
            else:
                raise AuthorityRefused("worktree contains a non-plain path")

    visit(root, "")
    return files, directories


def _validate_git_control_path(root: Path) -> None:
    """Require the worktree's administrative pointer itself to be plain."""

    control = root / ".git"
    info = _lstat(control, what="Git control path")
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
        raise AuthorityRefused("Git control path is linked or reparse-backed")
    if stat.S_ISREG(info.st_mode):
        if int(getattr(info, "st_nlink", 0)) != 1:
            raise AuthorityRefused("Git control file is hardlinked")
        return
    if not stat.S_ISDIR(info.st_mode):
        raise AuthorityRefused("Git control path is not plain")


def _hash_tree_rows(
    files: Mapping[str, Path], tree: Mapping[str, tuple[str, str]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative, (mode, expected_oid) in sorted(tree.items()):
        identity = _hash_plain_file(
            files[relative], what=f"tracked path {relative}", git_blob=True
        )
        if identity["git_blob"] != expected_oid:
            raise AuthorityRefused("worktree bytes differ from the exact HEAD tree")
        if os.name != "nt":
            executable = bool(files[relative].stat().st_mode & 0o111)
            if executable != (mode == "100755"):
                raise AuthorityRefused("worktree executable mode differs from HEAD")
        rows.append(
            {
                "path": relative,
                "mode": mode,
                "git_blob": expected_oid,
                "sha256": identity["sha256"],
                "size": identity["size"],
            }
        )
    return rows


def _tree_digest(entries: Mapping[str, tuple[str, str]]) -> str:
    rows = [
        {"path": path, "mode": mode, "git_blob": oid}
        for path, (mode, oid) in sorted(entries.items())
    ]
    return sha256_bytes(canonical_json_bytes(rows))


def _plain_tree_rows(
    files: Mapping[str, Path], directories: set[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {"kind": "directory", "path": relative}
        for relative in sorted(directories)
    ]
    for relative, path in sorted(files.items()):
        identity = _hash_plain_file(
            path, what=f"dependency path {relative}", git_blob=False
        )
        rows.append(
            {
                "kind": "file",
                "path": relative,
                "size": identity["size"],
                "sha256": identity["sha256"],
            }
        )
    return rows


def _close_windows_handles(handles: Mapping[str, int]) -> None:
    if not handles:
        return
    if os.name != "nt":
        raise AuthorityRefused("retained dependency locks require Windows")
    try:
        import ctypes

        close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        for handle in handles.values():
            close_handle(ctypes.c_void_p(handle))
    except (AttributeError, OSError) as exc:
        raise AuthorityRefused("retained dependency locks cannot be released") from exc


def _retain_windows_read_locks(
    root: Path, files: Mapping[str, Path]
) -> dict[str, int]:
    """Deny later write/delete opens for every dependency file until exit."""

    if os.name != "nt":
        raise AuthorityRefused("retained dependency locks require Windows")
    root_key = str(root)
    existing = _RETAINED_FILE_HANDLES.get(root_key)
    if existing is not None:
        if set(existing) != set(files):
            raise AuthorityRefused("retained dependency-lock inventory differs")
        return existing
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
    except (AttributeError, OSError) as exc:
        raise AuthorityRefused("Windows dependency-lock API is unavailable") from exc
    generic_read = 0x80000000
    file_share_read = 0x00000001
    open_existing = 3
    normal_attributes = 0x00000080
    invalid_handle = ctypes.c_void_p(-1).value
    opened: dict[str, int] = {}
    try:
        for relative, path in sorted(files.items()):
            handle = create_file(
                str(path),
                generic_read,
                file_share_read,
                None,
                open_existing,
                normal_attributes,
                None,
            )
            if handle in {None, invalid_handle}:
                error = ctypes.get_last_error()
                raise AuthorityRefused(
                    "dependency read lock refused at "
                    + relative
                    + "; winerror="
                    + str(error)
                )
            opened[relative] = int(handle)
    except BaseException:
        _close_windows_handles(opened)
        raise
    _RETAINED_FILE_HANDLES[root_key] = opened
    return opened


def verify_plain_tree(
    root: Path,
    *,
    capture_python: bool = False,
    retain_read_locks: bool = False,
) -> dict[str, Any]:
    """Bind a dependency tree and optionally retain immutable execution bytes."""

    root = _plain_directory(root, what="dependency tree")
    first_files, first_directories = _filesystem_inventory(root)
    first_rows = _plain_tree_rows(first_files, first_directories)
    retained = (
        _retain_windows_read_locks(root, first_files) if retain_read_locks else {}
    )
    rows_by_path = {
        row["path"]: row for row in first_rows if row.get("kind") == "file"
    }
    captured_python: dict[str, bytes] = {}
    if capture_python:
        for relative, path in sorted(first_files.items()):
            if not relative.lower().endswith(".py"):
                continue
            source, identity = _read_plain_file_bytes(
                path, what=f"dependency source {relative}"
            )
            row = rows_by_path[relative]
            if (
                identity["size"] != row["size"]
                or identity["sha256"] != row["sha256"]
            ):
                raise AuthorityRefused("dependency source changed after inventory")
            captured_python[relative] = source
    second_files, second_directories = _filesystem_inventory(root)
    if (
        set(second_files) != set(first_files)
        or second_directories != first_directories
        or _plain_tree_rows(second_files, second_directories) != first_rows
    ):
        raise AuthorityRefused("dependency tree changed between stable observations")
    result = {
        "path": str(root),
        "file_count": len(first_files),
        "directory_count": len(first_directories),
        "total_bytes": sum(
            row["size"] for row in first_rows if row["kind"] == "file"
        ),
        "inventory_digest": sha256_bytes(canonical_json_bytes(first_rows)),
        "stability_observations": 2,
        "captured_python_source_count": len(captured_python),
        "retained_read_lock_count": len(retained),
    }
    _OBSERVED_PLAIN_TREES[str(root)] = {
        "inventory_digest": result["inventory_digest"],
        "rows": rows_by_path,
        "python_sources": captured_python,
        "retained_paths": frozenset(retained),
    }
    return result


def verify_worktree(
    root: Path,
    *,
    git_executable: Path,
    expected_commit: str | None,
    require_detached: bool,
    capture_python: bool = False,
    retain_read_locks: bool = False,
) -> dict[str, Any]:
    """Prove index and every worktree byte equal one exact HEAD tree."""

    root = _plain_directory(root, what="authority worktree")
    _validate_git_control_path(root)
    head = _one_text_line(
        _git_bytes(root, git_executable, "rev-parse", "--verify", "HEAD^{commit}"),
        what="Git HEAD",
    )
    if _HEX40.fullmatch(head) is None:
        raise AuthorityRefused("Git HEAD is not canonical lowercase SHA-1")
    if expected_commit is not None and head != expected_commit:
        raise AuthorityRefused("worktree is not at its frozen commit")
    branch = _one_text_line(
        _git_bytes(root, git_executable, "rev-parse", "--abbrev-ref", "HEAD"),
        what="Git branch",
    )
    detached = branch == "HEAD"
    if require_detached and not detached:
        raise AuthorityRefused("frozen execution worktree is not detached")
    tree = _parse_tree(
        _git_bytes(root, git_executable, "ls-tree", "-r", "-z", "--full-tree", head)
    )
    index = _parse_index(_git_bytes(root, git_executable, "ls-files", "--stage", "-z"))
    if index != tree:
        raise AuthorityRefused("Git index differs from the exact HEAD tree")
    actual_files, actual_directories = _filesystem_inventory(
        root, exclude_git_control=True
    )
    if set(actual_files) != set(tree):
        raise AuthorityRefused("worktree files differ from the exact HEAD tree")
    if actual_directories != _expected_directories(tuple(tree)):
        raise AuthorityRefused("worktree directories differ from the exact HEAD tree")
    file_rows = _hash_tree_rows(actual_files, tree)
    retained = (
        _retain_windows_read_locks(root, actual_files)
        if retain_read_locks
        else {}
    )
    second_files, second_directories = _filesystem_inventory(
        root, exclude_git_control=True
    )
    if set(second_files) != set(tree) or second_directories != actual_directories:
        raise AuthorityRefused("worktree inventory changed between authority observations")
    if _hash_tree_rows(second_files, tree) != file_rows:
        raise AuthorityRefused("worktree bytes changed between authority observations")
    captured_python: dict[str, bytes] = {}
    rows_by_path = {row["path"]: row for row in file_rows}
    if capture_python:
        for relative, path in sorted(second_files.items()):
            if not relative.endswith(".py"):
                continue
            data, identity = _read_plain_file_bytes(
                path, what=f"captured worktree source {relative}"
            )
            expected_row = rows_by_path[relative]
            if (
                identity["sha256"] != expected_row["sha256"]
                or identity["size"] != expected_row["size"]
            ):
                raise AuthorityRefused(
                    "captured worktree source differs from the stable inventory"
                )
            captured_python[relative] = data
        third_files, third_directories = _filesystem_inventory(
            root, exclude_git_control=True
        )
        if set(third_files) != set(tree) or third_directories != actual_directories:
            raise AuthorityRefused("worktree changed after source capture")
        if _hash_tree_rows(third_files, tree) != file_rows:
            raise AuthorityRefused("worktree bytes changed after source capture")
    second_head = _one_text_line(
        _git_bytes(root, git_executable, "rev-parse", "--verify", "HEAD^{commit}"),
        what="second Git HEAD",
    )
    second_branch = _one_text_line(
        _git_bytes(root, git_executable, "rev-parse", "--abbrev-ref", "HEAD"),
        what="second Git branch",
    )
    second_tree = _parse_tree(
        _git_bytes(
            root, git_executable, "ls-tree", "-r", "-z", "--full-tree", second_head
        )
    )
    second_index = _parse_index(
        _git_bytes(root, git_executable, "ls-files", "--stage", "-z")
    )
    if (
        second_head != head
        or second_branch != branch
        or second_tree != tree
        or second_index != index
    ):
        raise AuthorityRefused("Git authority changed between stable observations")
    result = {
        "path": str(root),
        "git_commit": head,
        "branch": branch,
        "detached": detached,
        "tracked_file_count": len(file_rows),
        "stability_observations": 2,
        "tracked_tree_digest": _tree_digest(tree),
        "worktree_inventory_digest": sha256_bytes(canonical_json_bytes(file_rows)),
        "retained_read_lock_count": len(retained),
    }
    _OBSERVED_WORKTREES[str(root)] = {
        "git_commit": head,
        "worktree_inventory_digest": result["worktree_inventory_digest"],
        "tree": dict(tree),
        "python_sources": captured_python,
        "retained_paths": frozenset(retained),
    }
    return result


def _observed_worktree(
    authority: Mapping[str, Any], which: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    if which not in {"controller", "execution"}:
        raise AuthorityRefused("observed worktree selector is not allowlisted")
    if type(authority) is not dict or type(authority.get(which)) is not dict:
        raise AuthorityRefused("preimport authority lacks an observed worktree")
    recorded = authority[which]
    path = recorded.get("path")
    if type(path) is not str or path not in _OBSERVED_WORKTREES:
        raise AuthorityRefused("observed worktree cache is unavailable")
    observed = _OBSERVED_WORKTREES[path]
    if (
        observed["git_commit"] != recorded.get("git_commit")
        or observed["worktree_inventory_digest"]
        != recorded.get("worktree_inventory_digest")
    ):
        raise AuthorityRefused("observed worktree cache differs from authority")
    return recorded, observed


def admitted_git_blob(
    authority: Mapping[str, Any], which: str, relative_path: str
) -> str:
    """Return one blob id from the exact raw tree without another Git process."""

    if (
        type(relative_path) is not str
        or not relative_path
        or relative_path.startswith("/")
        or "\\" in relative_path
        or relative_path.split("/") != [part for part in relative_path.split("/") if part not in {"", ".", ".."}]
    ):
        raise AuthorityRefused("admitted Git path is not canonical relative form")
    _, observed = _observed_worktree(authority, which)
    item = observed["tree"].get(relative_path)
    if type(item) is not tuple or len(item) != 2:
        raise AuthorityRefused("admitted Git path is absent from the exact tree")
    return item[1]


def admitted_source_bytes(
    authority: Mapping[str, Any], which: str, relative_path: str
) -> bytes:
    """Return Python bytes captured inside one stable raw tree observation."""

    admitted_git_blob(authority, which, relative_path)
    _, observed = _observed_worktree(authority, which)
    data = observed["python_sources"].get(relative_path)
    if type(data) is not bytes:
        raise AuthorityRefused("worktree source was not captured as Python bytes")
    return data


def admitted_sources(
    authority: Mapping[str, Any], which: str
) -> dict[str, bytes]:
    """Return a private copy of every stably captured Python file in one tree."""

    _, observed = _observed_worktree(authority, which)
    result: dict[str, bytes] = {}
    for relative, data in sorted(observed["python_sources"].items()):
        admitted_git_blob(authority, which, relative)
        if type(data) is not bytes:
            raise AuthorityRefused("captured worktree source has invalid bytes")
        result[relative] = data
    if not result:
        raise AuthorityRefused("captured worktree source inventory is empty")
    return result


def admitted_controller_source_bytes(
    authority: Mapping[str, Any], relative_path: str
) -> bytes:
    """Compatibility wrapper for one captured controller source."""

    return admitted_source_bytes(authority, "controller", relative_path)


def admitted_controller_sources(
    authority: Mapping[str, Any],
) -> dict[str, bytes]:
    """Compatibility wrapper for all captured controller sources."""

    return admitted_sources(authority, "controller")


def admitted_execution_source_bytes(
    authority: Mapping[str, Any], relative_path: str
) -> bytes:
    """Return one captured execution-tree Python source."""

    return admitted_source_bytes(authority, "execution", relative_path)


def admitted_execution_sources(
    authority: Mapping[str, Any],
) -> dict[str, bytes]:
    """Return all captured execution-tree Python sources."""

    return admitted_sources(authority, "execution")


_RELOCATION_HELPERS = (
    ('provenance', '_week8_d161_relocation_provenance',
     'src/bu/experiments/week8_relocation_provenance.py'),
    ('metadata', '_week8_d161_relocation_metadata', 'scripts/week8_relocation_metadata.py'),
)


def _helper_constant(value: object) -> object:
    """Snapshot only literal policy values, preserving exact numeric types."""
    if value is None or type(value) in (bool, int, float, str):
        return [type(value).__name__, value]
    if isinstance(value, Path):
        return [type(value).__name__, str(value)]
    if type(value) in (tuple, list, set, frozenset):
        rows = [_helper_constant(item) for item in value]
        if type(value) in (set, frozenset):rows.sort(key=canonical_json_bytes)
        return [type(value).__name__, rows]
    if type(value) is dict:
        return ['dict', sorted([[_helper_constant(key), _helper_constant(item)]
                               for key, item in value.items()], key=canonical_json_bytes)]
    # Other objects (compiled patterns/types/imports) are checked by identity.
    return ['identity', id(value)]


class VerifiedRelocationHelpers:
    """Two captured non-bu modules; validate before and after adapter scopes."""

    def __init__(self, authority: Mapping[str, Any], modules: dict[str, ModuleType]) -> None:
        self.modules = dict(modules)
        self._modules = dict(modules)
        self._namespaces: list[tuple[object, dict[str, object]]] = []
        self._functions: list[tuple[FunctionType, tuple[object, ...]]] = []
        self._constants: list[tuple[object, str, bytes]] = []
        self._rows: list[dict[str, str]] = []
        self._loaders: dict[str, VerifiedSourceLoader] = {}
        for role, name, relative in _RELOCATION_HELPERS:
            module = modules[role]
            self._loaders[role] = module.__loader__
            self._rows.append(self._row(authority, role, name, relative))
            namespaces: list[object] = [module]
            namespaces.extend(value for value in vars(module).values()
                              if isinstance(value, type) and value.__module__ == name)
            for namespace in namespaces:
                values = dict(vars(namespace))
                self._namespaces.append((namespace, values))
                for key, value in values.items():
                    function = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value
                    if type(function) is FunctionType and function.__module__ == name:
                        self._functions.append((function, self._function_state(function)))
                    if key.isupper():
                        self._constants.append((namespace, key, canonical_json_bytes(_helper_constant(value))))
        self.validate(authority)

    @staticmethod
    def _function_state(function: FunctionType) -> tuple[object, ...]:
        return (function.__code__, function.__defaults__,
                canonical_json_bytes(_helper_constant(function.__kwdefaults__)),
                canonical_json_bytes(_helper_constant(function.__annotations__)))

    def _row(self, authority: Mapping[str, Any], role: str, name: str, relative: str) -> dict[str, str]:
        recorded, _ = _observed_worktree(authority, 'controller')
        source = admitted_source_bytes(authority, 'controller', relative)
        return {'role':role, 'module_id':name, 'path':str(Path(recorded['path'])/relative),
                'source_sha256':sha256_bytes(source),
                'git_blob':admitted_git_blob(authority, 'controller', relative),
                'controller_tree_digest':recorded['worktree_inventory_digest']}

    def validate(self, authority: Mapping[str, Any]) -> dict[str, Any]:
        if set(self.modules) != set(self._modules) or any(
                self.modules[key] is not value for key, value in self._modules.items()):
            raise AuthorityRefused('relocation helper bundle modules changed')
        rows = []
        for role, name, relative in _RELOCATION_HELPERS:
            row = self._row(authority, role, name, relative)
            module, loader = self._modules[role], self._loaders[role]
            spec = getattr(module, '__spec__', None)
            if (type(module) is not ModuleType or sys.modules.get(name) is not module
                    or module.__name__ != name or module.__file__ != row['path']
                    or getattr(spec, 'name', None) != name or getattr(spec, 'origin', None) != row['path']
                    or getattr(spec, 'loader', None) is not loader or module.__loader__ is not loader
                    or type(loader) is not VerifiedSourceLoader or loader.name != name
                    or loader.path != row['path'] or loader.tree_kind != 'controller'
                    or loader.git_blob != row['git_blob'] or loader.source_sha256 != row['source_sha256']
                    or loader.authority_tree_digest != row['controller_tree_digest']
                    or loader._source != admitted_source_bytes(authority, 'controller', relative)):
                raise AuthorityRefused('relocation helper loaded identity differs from captured authority')
            rows.append(row)
        if rows != self._rows:
            raise AuthorityRefused('relocation helper controller authority changed')
        for namespace, expected in self._namespaces:
            current = vars(namespace)
            if set(current) != set(expected) or any(current[key] is not value for key, value in expected.items()):
                raise AuthorityRefused('relocation helper namespace changed')
        if any(self._function_state(function) != expected for function, expected in self._functions):
            raise AuthorityRefused('relocation helper function changed')
        if any(canonical_json_bytes(_helper_constant(getattr(namespace, key))) != expected
               for namespace, key, expected in self._constants):
            raise AuthorityRefused('relocation helper policy constant changed')
        return {'helper_schema_version':1, 'controller_commit':authority['controller']['git_commit'],
                'modules':[dict(row) for row in rows]}


def load_verified_relocation_helpers(authority: Mapping[str, Any]) -> VerifiedRelocationHelpers:
    """Load only the approved relocation helpers, never controller bu imports."""
    recorded, _ = _observed_worktree(authority, 'controller')
    admission = authority.get('admission')
    if type(admission) is not dict or admission.get('controller_source') != str(Path(recorded['path'])/'src'):
        raise AuthorityRefused('relocation helper controller source admission differs')
    captured = []
    for role, name, relative in _RELOCATION_HELPERS:
        if name in sys.modules:
            raise AuthorityRefused('relocation helper module name is already occupied')
        captured.append((role, name, relative, admitted_source_bytes(authority, 'controller', relative),
                         admitted_git_blob(authority, 'controller', relative)))
    before_bu = {name:module for name,module in sys.modules.items() if name == 'bu' or name.startswith('bu.')}
    modules: dict[str, ModuleType] = {}
    try:
        for role, name, relative, source, blob in captured:
            loader = VerifiedSourceLoader(fullname=name, path=Path(recorded['path'])/relative,
                source=source, is_package=False, tree_kind='controller', git_blob=blob,
                authority_tree_digest=recorded['worktree_inventory_digest'])
            spec = importlib.util.spec_from_loader(name, loader, origin=loader.path)
            if spec is None:raise AuthorityRefused('relocation helper specification is unavailable')
            module = importlib.util.module_from_spec(spec)
            modules[role] = module
            sys.modules[name] = module
            loader.exec_module(module)
        after_bu = {name:module for name,module in sys.modules.items() if name == 'bu' or name.startswith('bu.')}
        if set(after_bu) != set(before_bu) or any(after_bu[name] is not value for name,value in before_bu.items()):
            raise AuthorityRefused('relocation helpers changed the admitted bu module inventory')
        return VerifiedRelocationHelpers(authority, modules)
    except BaseException:
        for module in modules.values():
            if sys.modules.get(module.__name__) is module:del sys.modules[module.__name__]
        raise


def verified_source_finder(
    authority: Mapping[str, Any], which: str
) -> VerifiedSourceFinder:
    """Build a fail-closed importer over source bytes captured by raw authority."""

    if which not in {"controller", "execution"}:
        raise AuthorityRefused("verified source tree is not allowlisted")
    admission = authority.get("admission") if type(authority) is dict else None
    if type(admission) is not dict:
        raise AuthorityRefused("verified source admission is unavailable")
    source_key = f"{which}_source"
    source_root = _plain_directory(
        _absolute_path(admission.get(source_key), what=f"{which} source root"),
        what=f"{which} source root",
    )
    recorded, _ = _observed_worktree(authority, which)
    expected_root = Path(recorded["path"]) / "src"
    if source_root != expected_root or admission.get(source_key) != str(expected_root):
        raise AuthorityRefused("verified source root differs from raw authority")
    return VerifiedSourceFinder(
        authority=authority,
        which=which,
        source_root=source_root,
        captured=admitted_sources(authority, which),
    )


def verified_dependency_finder(
    authority: Mapping[str, Any],
) -> VerifiedDependencyFinder:
    """Build a site importer over captured source and retained native files."""

    if type(authority) is not dict or type(authority.get("runtime")) is not dict:
        raise AuthorityRefused("verified dependency authority is unavailable")
    recorded = authority["runtime"].get("pinned_site_packages")
    if type(recorded) is not dict:
        raise AuthorityRefused("verified dependency record is unavailable")
    path = recorded.get("path")
    if type(path) is not str or path not in _OBSERVED_PLAIN_TREES:
        raise AuthorityRefused("observed dependency cache is unavailable")
    observed = _OBSERVED_PLAIN_TREES[path]
    if observed.get("inventory_digest") != recorded.get("inventory_digest"):
        raise AuthorityRefused("observed dependency cache differs from authority")
    rows = observed.get("rows")
    python_sources = observed.get("python_sources")
    retained_paths = observed.get("retained_paths")
    if (
        type(rows) is not dict
        or type(python_sources) is not dict
        or type(retained_paths) is not frozenset
        or len(python_sources) != recorded.get("captured_python_source_count")
        or len(retained_paths) != recorded.get("retained_read_lock_count")
        or len(retained_paths) != recorded.get("file_count")
    ):
        raise AuthorityRefused("verified dependency execution binding is incomplete")
    return VerifiedDependencyFinder(
        site_root=_plain_directory(Path(path), what="verified site-packages root"),
        inventory_digest=recorded["inventory_digest"],
        rows=rows,
        python_sources=python_sources,
        retained_paths=retained_paths,
    )


def _validate_startup_environment(
    config: Mapping[str, Any],
    helper_path: Path,
    *,
    helper_sha256: str,
    entrypoint_path: Path,
    entrypoint_sha256: str,
    command: str,
) -> dict[str, Any]:
    original_arguments = tuple(getattr(sys, "orig_argv", ()))
    if (
        len(original_arguments) != 16
        or original_arguments[1:7] != ("-I", "-S", "-B", "-X", "utf8", "-c")
    ):
        raise AuthorityRefused("entrypoint requires the fixed outer-bootstrap shape")
    outer_literal = original_arguments[7]
    configured_outer_sha256 = _exact_sha256(
        config["outer_bootstrap_literal_sha256"],
        what="configured outer-bootstrap literal SHA256",
    )
    if (
        type(outer_literal) is not str
        or sha256_bytes(outer_literal.encode("utf-8")) != configured_outer_sha256
        or _exact_sha256(
            entrypoint_sha256, what="outer entrypoint source SHA256"
        )
        != original_arguments[8]
        or _exact_sha256(helper_sha256, what="outer helper source SHA256")
        != original_arguments[9]
    ):
        raise AuthorityRefused("outer-bootstrap source binding differs")
    controller_commit = config["controller_commit"]
    if (
        type(controller_commit) is not str
        or _HEX40.fullmatch(controller_commit) is None
        or original_arguments[10] != controller_commit
    ):
        raise AuthorityRefused("outer-bootstrap controller commit differs")
    controller = _absolute_path(config["controller_root"], what="controller root")
    expected_entrypoint = (
        controller / "scripts" / "week8_exp2a_recovery_entrypoint.py"
    )
    entrypoint_path = _absolute_path(str(entrypoint_path), what="recovery entrypoint")
    if (
        entrypoint_path != expected_entrypoint
        or type(command) is not str
        or command
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
        or original_arguments[11] != command
    ):
        raise AuthorityRefused(
            "raw authority requires the fixed outer-bound entrypoint and one command"
        )
    flags = {
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "ignore_environment": bool(getattr(sys.flags, "ignore_environment", False)),
        "isolated": bool(getattr(sys.flags, "isolated", False)),
        "no_site": bool(sys.flags.no_site),
        "no_user_site": bool(sys.flags.no_user_site),
        "safe_path": bool(getattr(sys.flags, "safe_path", False)),
        "utf8_mode": int(sys.flags.utf8_mode),
    }
    if flags != {
        "dont_write_bytecode": True,
        "ignore_environment": True,
        "isolated": True,
        "no_site": True,
        "no_user_site": True,
        "safe_path": True,
        "utf8_mode": 1,
    }:
        raise AuthorityRefused("entrypoint requires exact -I -S -B -X utf8 flags")
    expected_environment = dict(_startup_environment_pairs(config))
    observed_environment: dict[str, str] = {}
    observed_canonical_names: set[str] = set()
    for name, value in exact_environment_items():
        canonical_name = name.upper()
        if canonical_name in observed_canonical_names:
            raise AuthorityRefused("entrypoint startup environment has duplicate names")
        observed_canonical_names.add(canonical_name)
        observed_environment[name] = value
    if observed_environment != expected_environment:
        raise AuthorityRefused("entrypoint complete startup environment differs")
    observed_python = {
        name: value
        for name, value in observed_environment.items()
        if name.startswith("PYTHON")
    }
    if observed_python != _STARTUP_PYTHON_ENVIRONMENT:
        raise AuthorityRefused(
            "entrypoint startup Python environment differs or PYTHONPATH is present"
        )
    native_runtime = _absolute_path(
        config["native_runtime"], what="native startup runtime"
    )
    try:
        working_directory = Path.cwd().resolve(strict=True)
    except OSError as exc:
        raise AuthorityRefused("entrypoint working directory is unavailable") from exc
    if working_directory != native_runtime:
        raise AuthorityRefused("entrypoint working directory differs from native runtime")
    pinned_python = _absolute_path(config["pinned_python"], what="pinned Python")
    pinned_base = _absolute_path(
        config["pinned_base_python"], what="pinned base Python"
    )
    pinned_base_runtime = _absolute_path(
        config["pinned_base_runtime"], what="pinned base runtime"
    )
    pinned_pyvenv = _absolute_path(config["pinned_pyvenv"], what="pyvenv.cfg")
    pinned_venv_scripts = _absolute_path(
        config["pinned_venv_scripts"], what="pinned venv Scripts"
    )
    native_launcher_path = _absolute_path(
        config["native_launcher"], what="native launcher"
    )
    pinned_base_prefix = _absolute_path(
        config["pinned_base_runtime"], what="pinned base runtime"
    )
    _same_path(Path(sys.executable), pinned_python, what="active Python launcher")
    base_executable = getattr(sys, "_base_executable", None)
    if type(base_executable) is not str:
        raise AuthorityRefused("active base Python identity is unavailable")
    _same_path(Path(base_executable), pinned_base, what="active base Python")
    _same_path(Path(sys.prefix), pinned_base_prefix, what="active Python prefix")
    _same_path(
        Path(sys.base_prefix), pinned_base_prefix, what="active Python base prefix"
    )
    execution = _absolute_path(config["execution_root"], what="execution root")
    site = _absolute_path(config["pinned_site_packages"], what="pinned site-packages")
    forbidden = (controller, execution, site)
    for entry in sys.path:
        if type(entry) is not str or not entry:
            raise AuthorityRefused("pre-import sys.path contains a non-fixed entry")
        candidate = Path(os.path.abspath(entry))
        for root in forbidden:
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            raise AuthorityRefused("project or site path was admitted before verification")
        try:
            candidate.relative_to(pinned_base_prefix)
        except ValueError as exc:
            raise AuthorityRefused(
                "pre-import sys.path escaped the measured base runtime"
            ) from exc
    allowed_loaded = {
        helper_path.resolve(strict=True),
        (controller / "scripts" / "week8_exp2a_recovery_entrypoint.py").resolve(
            strict=True
        ),
    }
    for module in tuple(sys.modules.values()):
        if not isinstance(module, ModuleType):
            continue
        filename = getattr(module, "__file__", None)
        if type(filename) is not str:
            continue
        try:
            source = Path(filename).resolve(strict=True)
        except OSError:
            continue
        if source in allowed_loaded:
            continue
        for root in forbidden:
            try:
                source.relative_to(root)
            except ValueError:
                continue
            raise AuthorityRefused("project or third-party module loaded before verification")
        try:
            source.relative_to(pinned_base_prefix)
        except ValueError:
            try:
                source.relative_to(Path("C:/Windows"))
            except ValueError as exc:
                raise AuthorityRefused(
                    "pre-import module escaped the measured runtime and Windows root"
                ) from exc
    return {
        "flags": flags,
        "startup_options": list(original_arguments[1:6]),
        "entrypoint_path": str(entrypoint_path),
        "command": command,
        "python_environment": dict(sorted(observed_python.items())),
        "startup_environment": observed_environment,
        "working_directory": str(working_directory),
        "active_runtime": {
            "executable": str(pinned_python),
            "base_executable": str(pinned_base),
            "prefix": str(pinned_base_prefix),
            "base_prefix": str(pinned_base_prefix),
        },
        "preimport_sys_path_digest": sha256_bytes(canonical_json_bytes(sys.path)),
        "outer_bootstrap_literal_sha256": configured_outer_sha256,
        "entrypoint_source_sha256": entrypoint_sha256,
    }


def exact_environment_items() -> tuple[tuple[str, str], ...]:
    """Return the process environment without Windows' casing normalization.

    ``os.environ`` uppercases keys on Windows.  That makes it unsuitable for
    proving that a security-sensitive environment block used the canonical
    spelling.  Read the native environment block directly there; other hosts
    can use the ordinary case-preserving mapping.
    """

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
        raise AuthorityRefused("cannot open the native Windows environment") from exc
    if not pointer:
        raise AuthorityRefused("native Windows environment is unavailable")
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
                raise AuthorityRefused("native Windows environment entry is malformed")
            entries.append((entry[:separator], entry[separator + 1 :]))
    finally:
        if not free_environment(pointer):
            raise AuthorityRefused("cannot release the native Windows environment")
    return tuple(entries)


def verify_preimport_authority(
    config: Mapping[str, Any],
    *,
    helper_path: Path,
    helper_sha256: str,
    entrypoint_path: Path,
    entrypoint_sha256: str,
    command: str,
) -> dict[str, Any]:
    """Verify all D-161 authority before source/site path admission."""

    config = _exact_mapping(config, keys=_CONFIG_KEYS, what="authority config")
    helper_path = _absolute_path(str(helper_path), what="raw-authority helper")
    if _HEX64.fullmatch(helper_sha256) is None:
        raise AuthorityRefused("raw-authority helper SHA256 is malformed")
    native_startup = _validate_native_startup(
        config,
        command=command,
        entrypoint_sha256=entrypoint_sha256,
        helper_sha256=helper_sha256,
    )
    runtime = _validate_startup_environment(
        config,
        helper_path,
        helper_sha256=helper_sha256,
        entrypoint_path=entrypoint_path,
        entrypoint_sha256=entrypoint_sha256,
        command=command,
    )
    controller_root = _absolute_path(config["controller_root"], what="controller root")
    execution_root = _absolute_path(config["execution_root"], what="execution root")
    expected_helper = controller_root / "scripts" / "week8_recovery_raw_authority.py"
    if helper_path != expected_helper:
        raise AuthorityRefused("raw-authority helper path differs from its fixed location")
    helper = _file_identity(
        helper_path, expected_sha256=helper_sha256, what="raw-authority helper"
    )
    _file_identity(
        _absolute_path(str(entrypoint_path), what="recovery entrypoint"),
        expected_sha256=entrypoint_sha256,
        what="recovery entrypoint",
    )
    pinned_python = _absolute_path(config["pinned_python"], what="pinned Python")
    pinned_base = _absolute_path(
        config["pinned_base_python"], what="pinned base Python"
    )
    pinned_git = _absolute_path(config["pinned_git"], what="pinned Git")
    git_runtime_root = _absolute_path(
        config["pinned_git_runtime_root"], what="pinned Git runtime"
    )
    if pinned_git.parent != git_runtime_root:
        raise AuthorityRefused("pinned Git is outside its fixed runtime directory")
    python_identity = _file_identity(
        pinned_python,
        expected_sha256=config["pinned_python_sha256"],
        what="pinned Python",
    )
    base_identity = _file_identity(
        pinned_base,
        expected_sha256=config["pinned_base_python_sha256"],
        what="pinned base Python",
    )
    git_identity = _file_identity(
        pinned_git, expected_sha256=config["pinned_git_sha256"], what="pinned Git"
    )
    git_runtime_identity = verify_plain_tree(
        git_runtime_root, retain_read_locks=True
    )
    expected_git_runtime = {
        "inventory_digest": config["pinned_git_runtime_inventory_digest"],
        "file_count": config["pinned_git_runtime_file_count"],
        "directory_count": config["pinned_git_runtime_directory_count"],
        "total_bytes": config["pinned_git_runtime_total_bytes"],
    }
    _exact_sha256(
        expected_git_runtime["inventory_digest"],
        what="configured Git runtime inventory digest",
    )
    for name in ("file_count", "directory_count", "total_bytes"):
        _exact_nonnegative_integer(
            expected_git_runtime[name], what=f"configured Git runtime {name}"
        )
    if any(
        git_runtime_identity[name] != value
        for name, value in expected_git_runtime.items()
    ):
        raise AuthorityRefused("pinned Git runtime content differs from config")
    if (
        git_runtime_identity["captured_python_source_count"] != 0
        or git_runtime_identity["retained_read_lock_count"]
        != git_runtime_identity["file_count"]
    ):
        raise AuthorityRefused("pinned Git runtime execution binding is incomplete")
    _same_path(Path(sys.executable), pinned_python, what="active Python launcher")
    base_executable = getattr(sys, "_base_executable", None)
    if type(base_executable) is not str:
        raise AuthorityRefused("active base Python identity is unavailable")
    _same_path(Path(base_executable), pinned_base, what="active base Python")
    source = _plain_directory(controller_root / "src", what="controller source root")
    site_packages = _plain_directory(
        _absolute_path(config["pinned_site_packages"], what="pinned site-packages"),
        what="pinned site-packages",
    )
    site_identity = verify_plain_tree(
        site_packages, capture_python=True, retain_read_locks=True
    )
    expected_site = {
        "inventory_digest": config["pinned_site_packages_inventory_digest"],
        "file_count": config["pinned_site_packages_file_count"],
        "directory_count": config["pinned_site_packages_directory_count"],
        "total_bytes": config["pinned_site_packages_total_bytes"],
    }
    _exact_sha256(
        expected_site["inventory_digest"],
        what="configured site-packages inventory digest",
    )
    for name in ("file_count", "directory_count", "total_bytes"):
        _exact_nonnegative_integer(
            expected_site[name], what=f"configured site-packages {name}"
        )
    if any(site_identity[name] != value for name, value in expected_site.items()):
        raise AuthorityRefused("pinned site-packages content differs from config")
    if (
        site_identity["captured_python_source_count"] <= 0
        or site_identity["retained_read_lock_count"] != site_identity["file_count"]
    ):
        raise AuthorityRefused("pinned site-packages execution binding is incomplete")
    execution_commit = config["execution_commit"]
    if type(execution_commit) is not str or _HEX40.fullmatch(execution_commit) is None:
        raise AuthorityRefused("execution commit is not canonical lowercase SHA-1")
    controller = verify_worktree(
        controller_root,
        git_executable=pinned_git,
        expected_commit=config["controller_commit"],
        require_detached=False,
        capture_python=True,
        retain_read_locks=True,
    )
    execution = verify_worktree(
        execution_root,
        git_executable=pinned_git,
        expected_commit=execution_commit,
        require_detached=True,
        capture_python=True,
        retain_read_locks=True,
    )
    if (
        verify_plain_tree(git_runtime_root, retain_read_locks=True)
        != git_runtime_identity
    ):
        raise AuthorityRefused("pinned Git runtime changed across raw Git queries")
    return seal_record(
        {
            "raw_authority_schema_version": RAW_AUTHORITY_SCHEMA_VERSION,
            "record_type": "week8_d161_preimport_authority",
            "decision_id": DECISION_ID,
            "runtime": {
                **runtime,
                "pinned_python": python_identity,
                "pinned_base_python": base_identity,
                "pinned_site_packages": site_identity,
            },
            "native_startup": native_startup,
            "git": git_identity,
            "git_runtime": git_runtime_identity,
            "raw_authority_helper": helper,
            "controller": controller,
            "execution": execution,
            "admission": {
                "controller_source": str(source),
                "execution_source": str(execution_root / "src"),
                "pinned_site_packages": str(site_packages),
            },
            "scientific_outcomes_consulted": False,
            "scientific_values_emitted": False,
            "production_mutation_performed": False,
        }
    )


def _exact_nonnegative_integer(value: object, *, what: str) -> int:
    if type(value) is not int or value < 0:
        raise AuthorityRefused(f"{what} is not an exact non-negative integer")
    return value


def _exact_sha256(value: object, *, what: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise AuthorityRefused(f"{what} is not canonical lowercase SHA256")
    return value


def _validate_file_identity_record(value: object, *, what: str) -> dict[str, Any]:
    record = _exact_mapping(value, keys=_FILE_IDENTITY_KEYS, what=what)
    _absolute_path(record["path"], what=f"{what} path")
    _exact_nonnegative_integer(record["size"], what=f"{what} size")
    _exact_sha256(record["sha256"], what=f"{what} SHA256")
    return dict(record)


def _validate_plain_tree_identity_record(
    value: object, *, what: str
) -> dict[str, Any]:
    record = _exact_mapping(value, keys=_PLAIN_TREE_IDENTITY_KEYS, what=what)
    _absolute_path(record["path"], what=f"{what} path")
    for name in (
        "file_count",
        "directory_count",
        "total_bytes",
        "captured_python_source_count",
        "retained_read_lock_count",
    ):
        _exact_nonnegative_integer(record[name], what=f"{what} {name}")
    _exact_sha256(record["inventory_digest"], what=f"{what} inventory digest")
    if record["stability_observations"] != 2 or type(
        record["stability_observations"]
    ) is not int:
        raise AuthorityRefused(f"{what} lacks two stable observations")
    return dict(record)


def _validate_worktree_identity_record(
    value: object,
    *,
    what: str,
    expected_path: Path,
    expected_commit: str | None,
    require_detached: bool,
) -> dict[str, Any]:
    record = _exact_mapping(value, keys=_WORKTREE_IDENTITY_KEYS, what=what)
    path = _absolute_path(record["path"], what=f"{what} path")
    if path != expected_path:
        raise AuthorityRefused(f"{what} path differs from the fixed config")
    commit = record["git_commit"]
    if type(commit) is not str or _HEX40.fullmatch(commit) is None:
        raise AuthorityRefused(f"{what} commit is not canonical lowercase SHA-1")
    if expected_commit is not None and commit != expected_commit:
        raise AuthorityRefused(f"{what} commit differs from the fixed config")
    branch = record["branch"]
    if (
        type(branch) is not str
        or not branch
        or "\n" in branch
        or "\r" in branch
        or record["detached"] is not (branch == "HEAD")
    ):
        raise AuthorityRefused(f"{what} branch/detached identity is malformed")
    if require_detached and record["detached"] is not True:
        raise AuthorityRefused(f"{what} is not recorded as detached")
    if _exact_nonnegative_integer(
        record["tracked_file_count"], what=f"{what} tracked-file count"
    ) == 0:
        raise AuthorityRefused(f"{what} tracked-file count is empty")
    _exact_nonnegative_integer(
        record["retained_read_lock_count"], what=f"{what} retained-lock count"
    )
    if record["stability_observations"] != 2 or type(
        record["stability_observations"]
    ) is not int:
        raise AuthorityRefused(f"{what} lacks exactly two stability observations")
    _exact_sha256(record["tracked_tree_digest"], what=f"{what} tree digest")
    _exact_sha256(
        record["worktree_inventory_digest"], what=f"{what} inventory digest"
    )
    return dict(record)


def _validate_preimport_authority_record(
    authority: object,
    config: Mapping[str, Any],
    *,
    helper_path: Path,
    helper_sha256: str,
) -> dict[str, Any]:
    """Validate every key and the canonical seal before any re-observation."""

    config = _exact_mapping(config, keys=_CONFIG_KEYS, what="authority config")
    record = _exact_mapping(
        authority, keys=_AUTHORITY_RECORD_KEYS, what="preimport authority record"
    )
    supplied_digest = _exact_sha256(
        record["record_digest"], what="preimport authority record digest"
    )
    unsealed = {key: value for key, value in record.items() if key != "record_digest"}
    if supplied_digest != sha256_bytes(canonical_json_bytes(unsealed)):
        raise AuthorityRefused("preimport authority canonical digest differs")
    if (
        type(record["raw_authority_schema_version"]) is not int
        or record["raw_authority_schema_version"] != RAW_AUTHORITY_SCHEMA_VERSION
        or record["record_type"] != "week8_d161_preimport_authority"
        or type(record["record_type"]) is not str
        or record["decision_id"] != DECISION_ID
        or type(record["decision_id"]) is not str
        or record["scientific_outcomes_consulted"] is not False
        or record["scientific_values_emitted"] is not False
        or record["production_mutation_performed"] is not False
    ):
        raise AuthorityRefused("preimport authority identity or outcome policy differs")
    runtime = _exact_mapping(
        record["runtime"], keys=_RUNTIME_RECORD_KEYS, what="authority runtime"
    )
    flags = _exact_mapping(
        runtime["flags"], keys=_RUNTIME_FLAG_KEYS, what="authority runtime flags"
    )
    if dict(flags) != {
        "dont_write_bytecode": True,
        "ignore_environment": True,
        "isolated": True,
        "no_site": True,
        "no_user_site": True,
        "safe_path": True,
        "utf8_mode": 1,
    }:
        raise AuthorityRefused("preimport authority runtime flags differ")
    if type(runtime["startup_options"]) is not list or runtime[
        "startup_options"
    ] != ["-I", "-S", "-B", "-X", "utf8"]:
        raise AuthorityRefused("preimport authority startup options differ")
    python_environment = _exact_mapping(
        runtime["python_environment"],
        keys=frozenset(_STARTUP_PYTHON_ENVIRONMENT),
        what="preimport Python environment",
    )
    if dict(python_environment) != _STARTUP_PYTHON_ENVIRONMENT:
        raise AuthorityRefused("preimport Python environment proof differs")
    expected_startup_environment = dict(_startup_environment_pairs(config))
    startup_environment = _exact_mapping(
        runtime["startup_environment"],
        keys=frozenset(expected_startup_environment),
        what="preimport complete startup environment",
    )
    if dict(startup_environment) != expected_startup_environment:
        raise AuthorityRefused("preimport complete startup environment proof differs")
    working_directory = _absolute_path(
        runtime["working_directory"], what="recorded native working directory"
    )
    native_runtime_path = _absolute_path(
        config["native_runtime"], what="configured native runtime"
    )
    active_runtime = _exact_mapping(
        runtime["active_runtime"],
        keys=_ACTIVE_RUNTIME_KEYS,
        what="recorded active Python runtime",
    )
    expected_active_runtime = {
        "executable": str(
            _absolute_path(config["pinned_python"], what="pinned Python")
        ),
        "base_executable": str(
            _absolute_path(config["pinned_base_python"], what="pinned base Python")
        ),
        "prefix": str(
            _absolute_path(
                config["pinned_base_runtime"], what="pinned base runtime"
            )
        ),
        "base_prefix": str(
            _absolute_path(
                config["pinned_base_runtime"], what="pinned base runtime"
            )
        ),
    }
    if working_directory != native_runtime_path or dict(active_runtime) != expected_active_runtime:
        raise AuthorityRefused("recorded native runtime identity differs")
    _exact_sha256(
        runtime["preimport_sys_path_digest"], what="preimport sys.path digest"
    )
    if (
        _exact_sha256(
            runtime["outer_bootstrap_literal_sha256"],
            what="recorded outer-bootstrap literal SHA256",
        )
        != config["outer_bootstrap_literal_sha256"]
    ):
        raise AuthorityRefused("recorded outer-bootstrap literal differs from config")
    entrypoint_source_sha256 = _exact_sha256(
        runtime["entrypoint_source_sha256"],
        what="recorded entrypoint source SHA256",
    )
    python_record = _validate_file_identity_record(
        runtime["pinned_python"], what="recorded pinned Python"
    )
    base_record = _validate_file_identity_record(
        runtime["pinned_base_python"], what="recorded pinned base Python"
    )
    site_record = _validate_plain_tree_identity_record(
        runtime["pinned_site_packages"], what="recorded pinned site-packages"
    )
    git_record = _validate_file_identity_record(record["git"], what="recorded Git")
    git_runtime_record = _validate_plain_tree_identity_record(
        record["git_runtime"], what="recorded Git runtime"
    )
    helper_record = _validate_file_identity_record(
        record["raw_authority_helper"], what="recorded raw-authority helper"
    )
    native = _exact_mapping(
        record["native_startup"],
        keys=_NATIVE_STARTUP_KEYS,
        what="recorded native startup",
    )
    native_launcher_record = _validate_file_identity_record(
        native["native_launcher"], what="recorded native launcher"
    )
    pyvenv_record = _validate_file_identity_record(
        native["pinned_pyvenv"], what="recorded pyvenv.cfg"
    )
    venv_scripts_record = _validate_native_tree_identity(
        native["pinned_venv_scripts"], what="recorded venv Scripts"
    )
    base_runtime_record = _validate_native_tree_identity(
        native["pinned_base_runtime"], what="recorded base runtime"
    )
    expected_venv_scripts = _expected_native_tree(
        config,
        prefix="pinned_venv_scripts",
        path_key="pinned_venv_scripts",
    )
    expected_base_runtime = _expected_native_tree(
        config,
        prefix="pinned_base_runtime",
        path_key="pinned_base_runtime",
    )
    expected_environment_sha256 = _startup_environment_sha256(
        _startup_environment_pairs(config)
    )
    expected_binding_sha256 = _startup_binding_sha256(
        config,
        command=runtime["command"],
        entrypoint_sha256=entrypoint_source_sha256,
        helper_sha256=helper_sha256,
        base_runtime=base_runtime_record,
        venv_scripts=venv_scripts_record,
        startup_environment_sha256=expected_environment_sha256,
    )
    if (
        _exact_sha256(
            native["release_receipt_sha256"],
            what="recorded release receipt SHA-256",
        )
        != config["release_receipt_sha256"]
        or native_launcher_record["path"]
        != str(_absolute_path(config["native_launcher"], what="native launcher"))
        or native_launcher_record["sha256"] != config["native_launcher_sha256"]
        or _exact_sha256(
            native["stage0_binding_sha256"],
            what="recorded stage-0 binding SHA-256",
        )
        != config["stage0_binding_sha256"]
        or _exact_sha256(
            native["startup_binding_sha256"],
            what="recorded startup binding SHA-256",
        )
        != config["startup_binding_sha256"]
        or expected_binding_sha256 != config["startup_binding_sha256"]
        or str(
            _absolute_path(
                native["native_powershell"], what="recorded native PowerShell"
            )
        )
        != str(
            _absolute_path(
                config["native_powershell"], what="configured native PowerShell"
            )
        )
        or str(
            _absolute_path(native["native_runtime"], what="recorded native runtime")
        )
        != str(native_runtime_path)
        or _exact_sha256(
            native["startup_environment_sha256"],
            what="recorded startup environment SHA-256",
        )
        != expected_environment_sha256
        or pyvenv_record["path"]
        != str(_absolute_path(config["pinned_pyvenv"], what="pyvenv.cfg"))
        or pyvenv_record["sha256"] != config["pinned_pyvenv_sha256"]
        or venv_scripts_record != expected_venv_scripts
        or base_runtime_record != expected_base_runtime
    ):
        raise AuthorityRefused("recorded native startup differs from fixed authority")
    controller_root = _absolute_path(config["controller_root"], what="controller root")
    execution_root = _absolute_path(config["execution_root"], what="execution root")
    pinned_python = _absolute_path(config["pinned_python"], what="pinned Python")
    pinned_base = _absolute_path(
        config["pinned_base_python"], what="pinned base Python"
    )
    pinned_git = _absolute_path(config["pinned_git"], what="pinned Git")
    git_runtime_root = _absolute_path(
        config["pinned_git_runtime_root"], what="pinned Git runtime"
    )
    site_packages = _absolute_path(
        config["pinned_site_packages"], what="pinned site-packages"
    )
    helper_path = _absolute_path(str(helper_path), what="raw-authority helper")
    recorded_entrypoint = _absolute_path(
        runtime["entrypoint_path"], what="recorded recovery entrypoint"
    )
    if (
        recorded_entrypoint
        != controller_root / "scripts" / "week8_exp2a_recovery_entrypoint.py"
        or type(runtime["command"]) is not str
        or runtime["command"]
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
    ):
        raise AuthorityRefused("preimport entrypoint command identity differs")
    if _exact_sha256(helper_sha256, what="raw-authority helper argument SHA256") != (
        helper_record["sha256"]
    ):
        raise AuthorityRefused("raw-authority helper argument SHA256 differs")
    expected_helper = controller_root / "scripts" / "week8_recovery_raw_authority.py"
    expected_admission = {
        "controller_source": str(controller_root / "src"),
        "execution_source": str(execution_root / "src"),
        "pinned_site_packages": str(site_packages),
    }
    admission = _exact_mapping(
        record["admission"], keys=_ADMISSION_KEYS, what="authority admission"
    )
    if (
        helper_path != expected_helper
        or helper_record["path"] != str(expected_helper)
        or python_record["path"] != str(pinned_python)
        or python_record["sha256"] != config["pinned_python_sha256"]
        or base_record["path"] != str(pinned_base)
        or base_record["sha256"] != config["pinned_base_python_sha256"]
        or site_record["path"] != str(site_packages)
        or site_record["inventory_digest"]
        != config["pinned_site_packages_inventory_digest"]
        or site_record["file_count"] != config["pinned_site_packages_file_count"]
        or site_record["directory_count"]
        != config["pinned_site_packages_directory_count"]
        or site_record["total_bytes"] != config["pinned_site_packages_total_bytes"]
        or git_record["path"] != str(pinned_git)
        or git_record["sha256"] != config["pinned_git_sha256"]
        or pinned_git.parent != git_runtime_root
        or git_runtime_record["path"] != str(git_runtime_root)
        or git_runtime_record["inventory_digest"]
        != config["pinned_git_runtime_inventory_digest"]
        or git_runtime_record["file_count"]
        != config["pinned_git_runtime_file_count"]
        or git_runtime_record["directory_count"]
        != config["pinned_git_runtime_directory_count"]
        or git_runtime_record["total_bytes"]
        != config["pinned_git_runtime_total_bytes"]
        or dict(admission) != expected_admission
    ):
        raise AuthorityRefused("preimport static authority differs from fixed config")
    if (
        site_record["captured_python_source_count"] <= 0
        or site_record["retained_read_lock_count"] != site_record["file_count"]
        or git_runtime_record["captured_python_source_count"] != 0
        or git_runtime_record["retained_read_lock_count"]
        != git_runtime_record["file_count"]
    ):
        raise AuthorityRefused("recorded dependency execution binding is incomplete")
    execution_commit = config["execution_commit"]
    if type(execution_commit) is not str or _HEX40.fullmatch(execution_commit) is None:
        raise AuthorityRefused("execution commit is not canonical lowercase SHA-1")
    controller_record = _validate_worktree_identity_record(
        record["controller"],
        what="recorded controller worktree",
        expected_path=controller_root,
        expected_commit=config["controller_commit"],
        require_detached=False,
    )
    execution_record = _validate_worktree_identity_record(
        record["execution"],
        what="recorded execution worktree",
        expected_path=execution_root,
        expected_commit=execution_commit,
        require_detached=True,
    )
    if (
        controller_record["retained_read_lock_count"]
        != controller_record["tracked_file_count"]
        or execution_record["retained_read_lock_count"]
        != execution_record["tracked_file_count"]
    ):
        raise AuthorityRefused("recorded worktree execution locks are incomplete")
    entrypoint_identity = _file_identity(
        recorded_entrypoint,
        expected_sha256=entrypoint_source_sha256,
        what="recorded recovery entrypoint",
    )
    if entrypoint_identity["path"] != str(recorded_entrypoint):
        raise AuthorityRefused("recorded recovery entrypoint path differs")
    return json.loads(canonical_json_bytes(record).decode("ascii"))


def _reobserve_static_authority(
    validated: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    helper_path: Path,
    helper_sha256: str,
) -> dict[str, Any]:
    """Freshly re-observe every static trust root in a validated record."""

    runtime = validated["runtime"]
    controller_root = _absolute_path(config["controller_root"], what="controller root")
    execution_root = _absolute_path(config["execution_root"], what="execution root")
    pinned_python = _absolute_path(config["pinned_python"], what="pinned Python")
    pinned_base = _absolute_path(
        config["pinned_base_python"], what="pinned base Python"
    )
    pinned_base_runtime = _absolute_path(
        config["pinned_base_runtime"], what="pinned base runtime"
    )
    pinned_pyvenv = _absolute_path(config["pinned_pyvenv"], what="pyvenv.cfg")
    pinned_venv_scripts = _absolute_path(
        config["pinned_venv_scripts"], what="pinned venv Scripts"
    )
    native_launcher_path = _absolute_path(
        config["native_launcher"], what="native launcher"
    )
    pinned_git = _absolute_path(config["pinned_git"], what="pinned Git")
    git_runtime_root = _absolute_path(
        config["pinned_git_runtime_root"], what="pinned Git runtime"
    )
    if pinned_git.parent != git_runtime_root:
        raise AuthorityRefused("pinned Git is outside its fixed runtime directory")
    helper_path = _absolute_path(str(helper_path), what="raw-authority helper")
    fresh_python = _file_identity(
        pinned_python,
        expected_sha256=config["pinned_python_sha256"],
        what="pinned Python",
    )
    fresh_base = _file_identity(
        pinned_base,
        expected_sha256=config["pinned_base_python_sha256"],
        what="pinned base Python",
    )
    fresh_native_launcher = _file_identity(
        native_launcher_path,
        expected_sha256=config["native_launcher_sha256"],
        what="native launcher",
    )
    fresh_pyvenv = _file_identity(
        pinned_pyvenv,
        expected_sha256=config["pinned_pyvenv_sha256"],
        what="pyvenv.cfg",
    )
    fresh_base_runtime = _native_tree_identity(pinned_base_runtime)
    fresh_venv_scripts = _native_tree_identity(pinned_venv_scripts)
    fresh_git = _file_identity(
        pinned_git,
        expected_sha256=config["pinned_git_sha256"],
        what="pinned Git",
    )
    fresh_git_runtime = verify_plain_tree(
        git_runtime_root, retain_read_locks=True
    )
    fresh_helper = _file_identity(
        helper_path,
        expected_sha256=helper_sha256,
        what="raw-authority helper",
    )
    source = _plain_directory(controller_root / "src", what="controller source root")
    execution_source = _plain_directory(
        execution_root / "src", what="execution source root"
    )
    site_packages = _plain_directory(
        _absolute_path(config["pinned_site_packages"], what="pinned site-packages"),
        what="pinned site-packages",
    )
    fresh_site = verify_plain_tree(
        site_packages, capture_python=True, retain_read_locks=True
    )
    fresh_controller = verify_worktree(
        controller_root,
        git_executable=pinned_git,
        expected_commit=config["controller_commit"],
        require_detached=False,
        capture_python=True,
        retain_read_locks=True,
    )
    fresh_execution = verify_worktree(
        execution_root,
        git_executable=pinned_git,
        expected_commit=config["execution_commit"],
        require_detached=True,
        capture_python=True,
        retain_read_locks=True,
    )
    if (
        verify_plain_tree(git_runtime_root, retain_read_locks=True)
        != fresh_git_runtime
    ):
        raise AuthorityRefused("pinned Git runtime changed across raw Git queries")
    fresh_static = {
        "pinned_python": fresh_python,
        "pinned_base_python": fresh_base,
        "pinned_site_packages": fresh_site,
        "git": fresh_git,
        "git_runtime": fresh_git_runtime,
        "raw_authority_helper": fresh_helper,
        "native_startup": {
            **validated["native_startup"],
            "native_launcher": fresh_native_launcher,
            "pinned_pyvenv": fresh_pyvenv,
            "pinned_venv_scripts": fresh_venv_scripts,
            "pinned_base_runtime": fresh_base_runtime,
        },
        "controller": fresh_controller,
        "execution": fresh_execution,
        "admission": {
            "controller_source": str(source),
            "execution_source": str(execution_source),
            "pinned_site_packages": str(site_packages),
        },
    }
    original_static = {
        "pinned_python": runtime["pinned_python"],
        "pinned_base_python": runtime["pinned_base_python"],
        "pinned_site_packages": runtime["pinned_site_packages"],
        "git": validated["git"],
        "git_runtime": validated["git_runtime"],
        "raw_authority_helper": validated["raw_authority_helper"],
        "native_startup": validated["native_startup"],
        "controller": validated["controller"],
        "execution": validated["execution"],
        "admission": validated["admission"],
    }
    if fresh_static != original_static:
        raise AuthorityRefused("fresh static authority differs from preimport authority")
    return dict(validated)


def revalidate_recorded_static_authority(
    authority: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    helper_path: Path,
    helper_sha256: str,
) -> dict[str, Any]:
    """Revalidate historical static authority without requiring its runtime.

    The original startup flags, environment and path proof remain sealed
    evidence.  This path deliberately does not compare them with the current
    finalizer process; it freshly rehashes every static trust root instead.
    """

    validated = _validate_preimport_authority_record(
        authority,
        config,
        helper_path=helper_path,
        helper_sha256=helper_sha256,
    )
    config = _exact_mapping(config, keys=_CONFIG_KEYS, what="authority config")
    return _reobserve_static_authority(
        validated,
        config,
        helper_path=helper_path,
        helper_sha256=helper_sha256,
    )


def revalidate_admitted_authority(
    authority: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    helper_path: Path,
    helper_sha256: str,
) -> dict[str, Any]:
    """Revalidate a sealed pre-import authority after path admission.

    This boundary is safe for the imported controller and direct bootstrap
    worker.  It never reconstructs the no-``PYTHONPATH`` pre-import state.
    Instead it validates and preserves that sealed startup proof while
    independently re-observing every static file, launcher, Git, admission,
    index, tree, and raw worktree-byte identity.
    """

    validated = _validate_preimport_authority_record(
        authority,
        config,
        helper_path=helper_path,
        helper_sha256=helper_sha256,
    )
    config = _exact_mapping(config, keys=_CONFIG_KEYS, what="authority config")
    runtime = validated["runtime"]
    current_flags = {
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "ignore_environment": bool(getattr(sys.flags, "ignore_environment", False)),
        "isolated": bool(getattr(sys.flags, "isolated", False)),
        "no_site": bool(sys.flags.no_site),
        "no_user_site": bool(sys.flags.no_user_site),
        "safe_path": bool(getattr(sys.flags, "safe_path", False)),
        "utf8_mode": int(sys.flags.utf8_mode),
    }
    current_arguments = tuple(getattr(sys, "orig_argv", ()))
    if (
        current_flags != runtime["flags"]
        or len(current_arguments) < 7
        or list(current_arguments[1:6]) != runtime["startup_options"]
    ):
        raise AuthorityRefused("current runtime no longer matches the startup proof")
    pinned_python = _absolute_path(config["pinned_python"], what="pinned Python")
    pinned_base = _absolute_path(
        config["pinned_base_python"], what="pinned base Python"
    )
    _same_path(Path(sys.executable), pinned_python, what="active Python launcher")
    base_executable = getattr(sys, "_base_executable", None)
    if type(base_executable) is not str:
        raise AuthorityRefused("active base Python identity is unavailable")
    _same_path(Path(base_executable), pinned_base, what="active base Python")
    return _reobserve_static_authority(
        validated,
        config,
        helper_path=helper_path,
        helper_sha256=helper_sha256,
    )


__all__ = [
    "AuthorityRefused",
    "GATE_ENVIRONMENT_NAME",
    "admitted_execution_source_bytes",
    "admitted_execution_sources",
    "admitted_controller_source_bytes",
    "admitted_controller_sources",
    "admitted_git_blob",
    "admitted_source_bytes",
    "admitted_sources",
    "canonical_json_bytes",
    "exact_environment_items",
    "seal_record",
    "sha256_bytes",
    "revalidate_admitted_authority",
    "revalidate_recorded_static_authority",
    "verify_preimport_authority",
    "verify_plain_tree",
    "verified_dependency_finder",
    "verified_source_finder",
    "load_verified_relocation_helpers",
    "verify_worktree",
]
