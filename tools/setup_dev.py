#!/usr/bin/env python3
"""Create a fresh Windows development environment without importing the project."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import sysconfig
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "requirements" / "windows-cp313-cpu.txt"
YAML_WHEEL = ROOT / "requirements" / "wheels" / "pyyaml-6.0.1-cp313-cp313-win_amd64.whl"
YAML_WHEEL_SHA256 = "46900b1b0a8ef0f7e11b98d8ca7754a61b29f819421f745f9217af1c3b813b36"
PYPI = "https://pypi.org/simple"
CPU_INDEX = "https://download.pytorch.org/whl/cpu"
# The inspected cp313 Torch2.13.0+cpu wheel has a171-unit license member.
# Adding \Lib\site-packages\ gives190; a65-unit target leaves4 below259.
LEGACY_WINDOWS_TARGET_UNITS = 65
OBSERVED_TORCH_INSTALLED_SUFFIX_UNITS = 190
PROTECTED_REPO_DIRECTORIES = frozenset({".git", ".continuation", "continuation", "docs", "runs", "src", "tests", "scripts", "tools", "requirements"})


class SetupError(RuntimeError):
    """A refusal or failed external packaging command."""


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def requirements() -> dict[str, str]:
    result = {}
    allowed_options = {f"--index-url {PYPI}", f"--extra-index-url {CPU_INDEX}"}
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--"):
            if line not in allowed_options:
                raise SetupError(f"Unexpected package index option in {SNAPSHOT.name}")
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if match is None:
            raise SetupError(f"Expected a single exact version pin: {line!r}")
        name, version = canonical_name(match[1]), match[2]
        if name in result:
            raise SetupError(f"Duplicate distribution pin: {name}")
        result[name] = version
    if len(result) != 37 or result.get("torch") != "2.13.0+cpu" or result.get("pyyaml") != "6.0.1":
        raise SetupError("The recorded37-distribution Windows CPU snapshot is incomplete")
    return result


def plain_ancestors(path: Path) -> None:
    for item in (path, *path.parents):
        if not os.path.lexists(item):
            continue
        info = item.lstat()
        if item.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise SetupError(f"Symlink or reparse path refused: {item}")
        if not stat.S_ISDIR(info.st_mode):
            raise SetupError(f"Environment path has a non-directory ancestor: {item}")


def environment_path(value: Path | None) -> Path:
    candidate = ROOT / ".venv" if value is None else value.expanduser()
    path = Path(os.path.abspath(candidate))
    plain_ancestors(path)
    if path == ROOT or path in ROOT.parents:
        raise SetupError("An environment cannot replace the checkout or an ancestor")
    if path.is_relative_to(ROOT):
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] in PROTECTED_REPO_DIRECTORIES:
            raise SetupError("An environment cannot be created inside Source or restored evidence")
    return path


def verify_wheel() -> None:
    if YAML_WHEEL.is_symlink() or not YAML_WHEEL.is_file():
        raise SetupError("The retained PyYAML development wheel is missing or not a regular file")
    info = YAML_WHEEL.lstat()
    if info.st_nlink != 1 or getattr(info, "st_file_attributes", 0) & 0x400:
        raise SetupError("The retained PyYAML wheel must be an ordinary single-link file")
    if info.st_size != 45474 or hashlib.sha256(YAML_WHEEL.read_bytes()).hexdigest() != YAML_WHEEL_SHA256:
        raise SetupError("The retained PyYAML wheel failed its exact byte/SHA256 verification")


def windows_long_paths_enabled() -> bool | None:
    """Read the Windows setting without changing registry or system configuration."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\FileSystem",
                            0, winreg.KEY_READ) as key:
            value, kind = winreg.QueryValueEx(key, "LongPathsEnabled")
        return kind == winreg.REG_DWORD and type(value) is int and value == 1
    except (ImportError, OSError):
        return None


def windows_path_preflight(target: Path) -> None:
    enabled = windows_long_paths_enabled()
    target_units = len(str(target).encode("utf-16-le")) // 2
    if enabled is not True and target_units > LEGACY_WINDOWS_TARGET_UNITS:
        state = "disabled" if enabled is False else "unavailable"
        raise SetupError(
            f"Windows long-path support is {state}; this environment target is {target_units} UTF-16 units. "
            f"The pinned Torch wheel can add {OBSERVED_TORCH_INSTALLED_SUFFIX_UNITS} units for an installed license path. "
            f"Use a new target of at most {LEGACY_WINDOWS_TARGET_UNITS} units, for example --venv D:/bu-dev. "
            "No environment was created. Any earlier failed environment remains unchanged; choose a fresh path."
        )
    print(f"Windows path preflight: target={target_units} UTF-16 units; "
          f"LongPathsEnabled={enabled}; conservative legacy limit={LEGACY_WINDOWS_TARGET_UNITS}", flush=True)


def check_environment(target: Path, expected: dict[str, str]) -> dict:
    """Read distribution metadata and torch's version literals; never launch/import it."""
    config = target / "pyvenv.cfg"
    if not config.is_file():
        raise SetupError(f"No environment configuration at {target}")
    config_values = {}
    for line in config.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            config_values[key.strip()] = value.strip()
    if not config_values.get("version", "").startswith("3.13."):
        raise SetupError("The Windows CPU snapshot requires a Python3.13 environment")
    site = target / "Lib" / "site-packages"
    if not site.is_dir():
        raise SetupError("Windows Lib/site-packages is absent")
    observed = {}
    project_origin = None
    for distribution in importlib.metadata.distributions(path=[str(site)]):
        name = canonical_name(distribution.metadata.get("Name", ""))
        if name in observed:
            raise SetupError(f"Duplicate installed distribution metadata: {name}")
        observed[name] = distribution.version
        if name == "beyond-uncertainty":
            origin_text = distribution.read_text("direct_url.json")
            project_origin = json.loads(origin_text) if origin_text else None
    # The preserved torch METADATA omits +cpu; its Source version literal is exact.
    torch_version = None
    cuda = "unobserved"
    torch_source = site / "torch" / "version.py"
    if torch_source.is_file():
        for statement in ast.parse(torch_source.read_bytes()).body:
            if isinstance(statement, ast.Assign):
                for name in statement.targets:
                    if isinstance(name, ast.Name) and isinstance(statement.value, ast.Constant):
                        if name.id == "__version__":
                            torch_version = statement.value.value
                        elif name.id == "cuda":
                            cuda = statement.value.value
            elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                if isinstance(statement.value, ast.Constant):
                    if statement.target.id == "__version__":
                        torch_version = statement.value.value
                    elif statement.target.id == "cuda":
                        cuda = statement.value.value
    mismatches = []
    for name, wanted in expected.items():
        actual = observed.get(name)
        if name == "torch":
            matches = actual in {"2.13.0", "2.13.0+cpu"} and torch_version == wanted and cuda is None
        else:
            matches = actual == wanted
        if not matches:
            mismatches.append({"distribution": name, "expected": wanted, "observed": actual})
    if observed.get("beyond-uncertainty") != "0.1.0":
        mismatches.append({"distribution": "beyond-uncertainty", "expected": "0.1.0 editable checkout", "observed": observed.get("beyond-uncertainty")})
    editable_root_matches = False
    if (isinstance(project_origin, dict) and isinstance(project_origin.get("dir_info"), dict)
            and project_origin["dir_info"].get("editable") is True and isinstance(project_origin.get("url"), str)):
        parsed = urlsplit(project_origin["url"])
        if parsed.scheme == "file" and not parsed.netloc and not parsed.query and not parsed.fragment:
            decoded = unquote(parsed.path)
            if sys.platform == "win32" and re.match(r"^/[A-Za-z]:/", decoded):
                decoded = decoded[1:]
            editable_root_matches = Path(os.path.abspath(decoded)) == ROOT
    if not editable_root_matches:
        mismatches.append({"distribution": "beyond-uncertainty editable origin", "expected": str(ROOT), "observed": "missing or different checkout"})
    return {"environment": str(target), "python_version_metadata": config_values["version"],
            "expected_pinned_distribution_count": len(expected), "installed_distribution_count": len(observed),
            "torch_Source_version_literal": torch_version, "torch_Source_cuda_literal": cuda,
            "editable_project_root_matches_this_checkout": editable_root_matches,
            "mismatches": mismatches, "metadata_only": True, "project_imports_or_tests_run": False}


def run(command: list[str], environment: dict[str, str]) -> None:
    print("Packaging command:", subprocess.list2cmdline(command), flush=True)
    try:
        subprocess.run(command, cwd=ROOT, env=environment, check=True, shell=False)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SetupError("Packaging command failed; the partially created environment is retained. " + str(exc)) from exc


def install(target: Path, custom_path: bool) -> None:
    if (sys.platform != "win32" or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 13) or sysconfig.get_platform() != "win-amd64"):
        raise SetupError("Installation requires general-host Windows x64 CPython3.13; other platforms need a separate environment")
    if sys.prefix != sys.base_prefix:
        raise SetupError("Run setup with a general-host Python3.13 outside an existing virtual environment")
    windows_path_preflight(target)
    if os.path.lexists(target):
        if not custom_path or not target.is_dir() or any(target.iterdir()):
            raise SetupError("Existing environment/directory refused. Use --check, or choose a new --venv path")
    else:
        target.mkdir(parents=True, exist_ok=False)
    # Exclusive reservation prevents a second installer from sharing this target.
    reservation = target / ".setup-dev-owner.json"
    with reservation.open("x", encoding="utf-8") as handle:
        json.dump({"tool": "setup_dev.py", "project_root": str(ROOT), "general_host_python": sys.executable}, handle)
        handle.write("\n")
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIP_CONFIG_FILE"] = os.devnull
    for key in list(environment):
        if key.startswith("PIP_") and key != "PIP_CONFIG_FILE":
            del environment[key]
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    run([sys.executable, "-I", "-S", "-B", "-m", "venv", str(target)], environment)
    python = target / "Scripts" / "python.exe"
    pip = [str(python), "-I", "-B", "-m", "pip", "--disable-pip-version-check", "--no-input"]
    run(pip + ["install", "--no-compile", "--only-binary=:all:", "--index-url", PYPI,
               "pip==26.2.1", "setuptools==84.0.0"], environment)
    verify_wheel()
    run(pip + ["install", "--no-compile", "--no-index", "--no-deps", str(YAML_WHEEL)], environment)
    run(pip + ["install", "--no-compile", "--only-binary=:all:", "--no-build-isolation",
               "--index-url", PYPI, "--extra-index-url", CPU_INDEX, "-r", str(SNAPSHOT),
               "-e", str(ROOT) + "[dev]"], environment)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, help="New custom environment path; an explicitly selected empty directory is allowed")
    parser.add_argument("--check", action="store_true", help="Read existing environment metadata only; no interpreter launch or changes")
    arguments = parser.parse_args(argv)
    try:
        expected = requirements()
        target = environment_path(arguments.venv)
        verify_wheel()
        if not arguments.check:
            install(target, arguments.venv is not None)
        result = check_environment(target, expected)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1 if result["mismatches"] else 0
    except (SetupError, OSError, ValueError) as exc:
        print(f"Setup refused/failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
