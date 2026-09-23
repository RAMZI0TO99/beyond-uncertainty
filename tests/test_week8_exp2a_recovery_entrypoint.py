"""Subprocess contract tests for the D-161/D-167 pre-import entrypoint.

The positive path uses two synthetic Git repositories, a copied synthetic
Python installation/venv pair, and a stub controller.  Every subprocess starts
with the exact 12-entry D-168 environment and 16-item ``sys.orig_argv``;
production recovery evidence is neither opened nor changed.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT_PATH = ROOT / "scripts" / "week8_exp2a_recovery_entrypoint.py"
AUTHORITY_PATH = ROOT / "scripts" / "week8_recovery_raw_authority.py"
OUTER_BOOTSTRAP_PATH = ROOT / "scripts" / "week8_recovery_outer_bootstrap.txt"
WORKER_PATH = ROOT / "scripts" / "week8_exp2a_recovery_worker.py"
INSPECTOR_PATH = ROOT / "scripts" / "week8_exp2a_recovery_inspector.py"
FIT_CHILD_PATH = ROOT / "scripts" / "week8_exp2a_recovery_fit_child.py"
CONTROLLER_PATH = ROOT / "src" / "bu" / "experiments" / "week8_exp2a_recovery.py"
RUNBOOK_PATH = ROOT / "docs" / "week8_production_runbook.md"
SPEC = importlib.util.spec_from_file_location(
    "week8_exp2a_recovery_entrypoint_under_test", ENTRYPOINT_PATH
)
assert SPEC is not None and SPEC.loader is not None
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)
assert isinstance(E, ModuleType)

AUTHORITY_SPEC = importlib.util.spec_from_file_location(
    "week8_recovery_raw_authority_for_entrypoint_tests", AUTHORITY_PATH
)
assert AUTHORITY_SPEC is not None and AUTHORITY_SPEC.loader is not None
A = importlib.util.module_from_spec(AUTHORITY_SPEC)
AUTHORITY_SPEC.loader.exec_module(A)
assert isinstance(A, ModuleType)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _native_tree_identity(root: Path) -> dict[str, object]:
    """Independently reproduce the D-167 ordinal native-tree TSV digest."""

    root = root.resolve(strict=True)
    rows: list[tuple[str, str, int, str]] = []
    for path in root.rglob("*"):
        assert not path.is_symlink(), path
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            rows.append((relative, "D", 0, ""))
        elif path.is_file():
            rows.append((relative, "F", path.stat().st_size, _sha256(path)))
        else:  # pragma: no cover - the synthetic fixture creates only plain paths.
            raise AssertionError(f"non-plain synthetic native path: {path}")
    rows.sort(key=lambda row: row[0])
    payload = bytearray()
    for relative, kind, size, digest in rows:
        if kind == "D":
            payload.extend(f"D\t{relative}\n".encode("utf-8"))
        else:
            payload.extend(
                f"F\t{relative}\t{size}\t{digest}\n".encode("utf-8")
            )
    return {
        "path": str(root),
        "file_count": sum(kind == "F" for _, kind, _, _ in rows),
        "directory_count": sum(kind == "D" for _, kind, _, _ in rows),
        "total_bytes": sum(size for _, kind, size, _ in rows if kind == "F"),
        "inventory_sha256": _sha256_bytes(bytes(payload)),
    }


def _native_tree_config(
    prefix: str, identity: dict[str, object]
) -> dict[str, object]:
    return {
        f"{prefix}_inventory_sha256": identity["inventory_sha256"],
        f"{prefix}_file_count": identity["file_count"],
        f"{prefix}_directory_count": identity["directory_count"],
        f"{prefix}_total_bytes": identity["total_bytes"],
    }


def _startup_environment_pairs(
    config: dict[str, object],
) -> tuple[tuple[str, str], ...]:
    base_runtime = str(config["pinned_base_runtime"])
    native_runtime = str(config["native_runtime"])
    pairs = (
        ("CUDA_VISIBLE_DEVICES", "-1"),
        ("HIP_VISIBLE_DEVICES", "-1"),
        ("MKL_NUM_THREADS", "4"),
        ("NUMEXPR_NUM_THREADS", "4"),
        ("OMP_NUM_THREADS", "4"),
        ("OPENBLAS_NUM_THREADS", "4"),
        (
            "PATH",
            os.pathsep.join(
                (base_runtime, "C:\\Windows\\System32", "C:\\Windows")
            ),
        ),
        ("SystemRoot", "C:\\Windows"),
        ("TEMP", native_runtime),
        ("TMP", native_runtime),
        ("TMPDIR", native_runtime),
        ("WINDIR", "C:\\Windows"),
    )
    assert len(pairs) == 12
    assert len({name for name, _ in pairs}) == 12
    return pairs


def _startup_environment_sha256(config: dict[str, object]) -> str:
    rows = ["WEEK8_D168_STARTUP_ENVIRONMENT_V2"]
    rows.extend(f"{name}={value}" for name, value in _startup_environment_pairs(config))
    return _sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def _startup_binding_sha256(
    config: dict[str, object],
    *,
    command: str,
    entrypoint_sha256: str,
    helper_sha256: str,
    base_runtime: dict[str, object],
    venv_scripts: dict[str, object],
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
        f"startup_environment_sha256={_startup_environment_sha256(config)}",
    )
    return _sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


@pytest.fixture(scope="session")
def synthetic_native_python(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Build one fully copied native Python startup closure under basetemp."""

    if os.name != "nt":
        pytest.skip("the D-167 native startup contract is Windows-specific")
    assert sys.version_info[:3] == (3, 13, 5)
    fixture_root = tmp_path_factory.mktemp("d167-native-python")
    source_base = Path(sys._base_executable).resolve(strict=True).parent
    base_runtime = fixture_root / "base-runtime"
    shutil.copytree(source_base, base_runtime, copy_function=shutil.copyfile)
    base_python = base_runtime / Path(sys._base_executable).name
    assert base_python.is_file()

    venv_root = fixture_root / "synthetic-venv"
    venv_scripts = venv_root / "Scripts"
    venv_scripts.mkdir(parents=True)
    python = venv_scripts / Path(sys.executable).name
    shutil.copyfile(Path(sys.executable).resolve(strict=True), python)
    pyvenv = venv_root / "pyvenv.cfg"
    pyvenv.write_bytes(
        (
            f"home = {base_runtime}\r\n"
            "include-system-site-packages = false\r\n"
            "version = 3.13.5\r\n"
            f"executable = {base_python}\r\n"
            f"command = {base_python} -m venv {venv_root}\r\n"
        ).encode("utf-8")
    )

    base_identity = _native_tree_identity(base_runtime)
    venv_identity = _native_tree_identity(venv_scripts)
    assert A._native_tree_identity(base_runtime) == base_identity
    assert A._native_tree_identity(venv_scripts) == venv_identity
    return {
        "base_runtime": base_runtime.resolve(strict=True),
        "base_python": base_python.resolve(strict=True),
        "venv_root": venv_root.resolve(strict=True),
        "venv_scripts": venv_scripts.resolve(strict=True),
        "python": python.resolve(strict=True),
        "pyvenv": pyvenv.resolve(strict=True),
        "base_identity": base_identity,
        "venv_identity": venv_identity,
    }


def _plain_tree_config(prefix: str, root: Path) -> dict[str, object]:
    identity = A.verify_plain_tree(root)
    return {
        f"{prefix}_inventory_digest": identity["inventory_digest"],
        f"{prefix}_file_count": identity["file_count"],
        f"{prefix}_directory_count": identity["directory_count"],
        f"{prefix}_total_bytes": identity["total_bytes"],
    }


def _synthetic_outer_bootstrap(entrypoint: Path, helper: Path) -> str:
    literal = OUTER_BOOTSTRAP_PATH.read_bytes().decode("utf-8", errors="strict")
    literal = literal.replace(
        E.ENTRYPOINT_PATH.as_posix(), entrypoint.resolve().as_posix()
    ).replace(E.RAW_AUTHORITY_HELPER.as_posix(), helper.resolve().as_posix())
    assert entrypoint.resolve().as_posix() in literal
    assert helper.resolve().as_posix() in literal
    assert E.ENTRYPOINT_PATH.as_posix() not in literal
    assert E.RAW_AUTHORITY_HELPER.as_posix() not in literal
    return literal


def _literal_assignment(path: Path, name: str) -> object:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches: list[object] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            matches.append(ast.literal_eval(node.value))
    assert len(matches) == 1, f"expected one literal {name} in {path}"
    return matches[0]


def _git_executable() -> Path:
    fixed = Path(
        "D:/Aenv/pro2/runtimes/"
        "git/mingw64/bin/git.exe"
    )
    if fixed.is_file():
        return fixed.resolve()
    discovered = shutil.which("git")
    if discovered is None:
        pytest.skip("Git is unavailable for the entrypoint contract tests")
    return Path(discovered).resolve()


def _clean_environment(config: dict[str, object]) -> dict[str, str]:
    environment = dict(_startup_environment_pairs(config))
    assert len(environment) == 12
    assert "PYTHONPATH" not in environment
    assert not any(name.startswith("GIT_") for name in environment)
    assert E.GATE_ENVIRONMENT_NAME not in environment
    return environment


def _setup_git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        [
            str(_git_executable()),
            "--no-pager",
            "--no-optional-locks",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.fsmonitor=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-C",
            str(repo),
            *arguments,
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            name: value
            for name, value in os.environ.items()
            if not name.upper().startswith("GIT_")
        },
        shell=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.decode("utf-8", errors="replace"))
    return completed.stdout


def _initialize_repo(repo: Path, *, detach: bool) -> str:
    _setup_git(repo, "init", "-q")
    _setup_git(repo, "config", "user.name", "Synthetic Entrypoint")
    _setup_git(repo, "config", "user.email", "entrypoint@example.invalid")
    _setup_git(repo, "add", "--", ".")
    _setup_git(repo, "commit", "-q", "-m", "exact synthetic authority")
    commit = _setup_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    if detach:
        _setup_git(repo, "checkout", "-q", "--detach", commit)
    return commit


def _hostile_command(helper: Path, marker: Path, label: str) -> str:
    return f'"{sys.executable}" "{helper}" "{marker}" "{label}"'


def _install_hostile_config(repo: Path, marker_root: Path, prefix: str) -> list[Path]:
    marker_root.mkdir(parents=True, exist_ok=True)
    helper = repo / ".git" / "entrypoint-hostile-helper.py"
    helper.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')\n"
        "raise SystemExit(19)\n",
        encoding="utf-8",
    )
    labels = ("fsmonitor", "pager", "clean", "process", "hook")
    markers = [marker_root / f"{prefix}-{label}.executed" for label in labels]
    commands = {label: _hostile_command(helper, marker, label) for label, marker in zip(labels, markers)}
    for key, value in (
        ("core.fsmonitor", commands["fsmonitor"]),
        ("core.pager", commands["pager"]),
        ("pager.ls-files", commands["pager"]),
        ("filter.evil.clean", commands["clean"]),
        ("filter.evil.process", commands["process"]),
        ("core.hooksPath", commands["hook"]),
    ):
        _setup_git(repo, "config", "--local", key, value)
    info = repo / ".git" / "info"
    info.mkdir(exist_ok=True)
    (info / "attributes").write_text("*.py filter=evil diff=evil\n", encoding="utf-8")
    return markers


def _write_stub_controller(
    controller: Path,
    *,
    embedded_config: dict[str, object],
    controller_marker: Path,
    mode_file: Path,
    helper_sha256: str,
) -> None:
    scripts = controller / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    synthetic_entrypoint = scripts / ENTRYPOINT_PATH.name
    source = ENTRYPOINT_PATH.read_text(encoding="utf-8")
    anchor = '\nif __name__ == "__main__":  # pragma: no cover - subprocess contract\n'
    assert source.count(anchor) == 1
    config_json = json.dumps(
        embedded_config, sort_keys=True, separators=(",", ":")
    )
    synthetic_override = (
        "\n# Synthetic-only constants injected by the contract test fixture.\n"
        f"PRODUCTION_CONFIG = json.loads({config_json!r})\n"
        "CONTROLLER_ROOT = Path(PRODUCTION_CONFIG['controller_root'])\n"
        "EXECUTION_ROOT = Path(PRODUCTION_CONFIG['execution_root'])\n"
        "ENTRYPOINT_PATH = CONTROLLER_ROOT / 'scripts' / 'week8_exp2a_recovery_entrypoint.py'\n"
        "RAW_AUTHORITY_HELPER = CONTROLLER_ROOT / 'scripts' / 'week8_recovery_raw_authority.py'\n"
        f"RAW_AUTHORITY_HELPER_SHA256 = {helper_sha256!r}\n"
        "OUTER_BOOTSTRAP_LITERAL_SHA256 = PRODUCTION_CONFIG['outer_bootstrap_literal_sha256']\n"
    )
    synthetic_entrypoint.write_text(
        source.replace(anchor, synthetic_override + anchor), encoding="utf-8"
    )
    shutil.copyfile(AUTHORITY_PATH, scripts / AUTHORITY_PATH.name)
    package = controller / "src" / "bu" / "experiments"
    package.mkdir(parents=True)
    (controller / ".gitignore").write_text(
        "src/json.py\n"
        "src/numpy.py\n"
        "src/*.pyc\n"
        "src/*.pyd\n"
        "src/shadow_package/\n"
        "post-gate-extra.ignored\n",
        encoding="utf-8",
    )
    (package.parent / "__init__.py").write_text("# synthetic bu\n", encoding="utf-8")
    (package / "__init__.py").write_text("# synthetic experiments\n", encoding="utf-8")
    helper_path = scripts / AUTHORITY_PATH.name
    (package / "week8_exp2a_recovery.py").write_text(
        "import copy\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"_SYNTHETIC_CONFIG = json.loads({config_json!r})\n"
        f"_HELPER_PATH = Path({str(helper_path.resolve())!r})\n"
        f"_HELPER_SHA256 = {helper_sha256!r}\n"
        f"_MODE_FILE = Path({str(mode_file.resolve())!r})\n"
        f"_CONTROLLER_MARKER = Path({str(controller_marker.resolve())!r})\n"
        "def main(argv):\n"
        "    gate = json.loads(os.environ['BU_D161_ENTRYPOINT_GATE'])\n"
        "    authority = copy.deepcopy(gate['raw_authority'])\n"
        "    config = copy.deepcopy(_SYNTHETIC_CONFIG)\n"
        "    config['controller_commit'] = authority['controller']['git_commit']\n"
        "    config['release_receipt_sha256'] = authority['native_startup']['release_receipt_sha256']\n"
        "    config['native_launcher_sha256'] = authority['native_startup']['native_launcher']['sha256']\n"
        "    config['stage0_binding_sha256'] = authority['native_startup']['stage0_binding_sha256']\n"
        "    config['startup_binding_sha256'] = authority['native_startup']['startup_binding_sha256']\n"
        "    helper_path = _HELPER_PATH\n"
        "    helper_sha256 = _HELPER_SHA256\n"
        "    raw = sys.modules['_bu_week8_d161_raw_authority']\n"
        "    specification = globals().get('__spec__')\n"
        "    loader = getattr(specification, 'loader', None)\n"
        "    dependency_finder = next((item for item in sys.meta_path if getattr(item, 'binding_marker', None) == 'week8_d161_verified_dependency_source_v1'), None)\n"
        "    loader_record = {\n"
        "        'binding_marker': getattr(loader, 'binding_marker', None),\n"
        "        'tree_kind': getattr(loader, 'tree_kind', None),\n"
        "        'source_sha256': getattr(loader, 'source_sha256', None),\n"
        "        'git_blob': getattr(loader, 'git_blob', None),\n"
        "        'authority_tree_digest': getattr(loader, 'authority_tree_digest', None),\n"
        "        'dependency_binding_marker': getattr(dependency_finder, 'binding_marker', None),\n"
        "        'dependency_inventory_digest': getattr(dependency_finder, 'authority_tree_digest', None),\n"
        "    }\n"
        "    mode = _MODE_FILE.read_text(encoding='ascii').strip()\n"
        "    if mode == 'byte-drift':\n"
        "        target = Path(config['controller_root']) / '.gitignore'\n"
        "        target.write_text(target.read_text(encoding='utf-8') + '# drift\\n', encoding='utf-8')\n"
        "    elif mode == 'tree-drift':\n"
        "        (Path(config['controller_root']) / 'post-gate-extra.ignored').write_text('drift', encoding='utf-8')\n"
        "    elif mode == 'helper-drift':\n"
        "        helper_path.write_text(helper_path.read_text(encoding='utf-8') + '# drift\\n', encoding='utf-8')\n"
        "    elif mode == 'site-drift':\n"
        "        target = Path(config['pinned_site_packages']) / 'synthetic_dependency.py'\n"
        "        target.write_text(target.read_text(encoding='utf-8') + '# drift\\n', encoding='utf-8')\n"
        "    elif mode == 'digest-drift':\n"
        "        authority['controller']['branch'] = 'tampered'\n"
        "    elif mode == 'extra-key':\n"
        "        authority['unexpected'] = False\n"
        "        authority = raw.seal_record({key: value for key, value in authority.items() if key != 'record_digest'})\n"
        "    elif mode == 'startup-proof-drift':\n"
        "        authority['runtime']['startup_options'] = ['-I', '-S', '-P', '-s']\n"
        "        authority = raw.seal_record({key: value for key, value in authority.items() if key != 'record_digest'})\n"
        "    revalidated = raw.revalidate_admitted_authority(\n"
        "        authority, config, helper_path=helper_path, helper_sha256=helper_sha256\n"
        "    )\n"
        "    controller_runtime = {\n"
        "        'executable': sys.executable, 'base_executable': sys._base_executable,\n"
        "        'sys_path': list(sys.path),\n"
        "        'python_environment': {name: value for name, value in os.environ.items() if name.upper().startswith('PYTHON')},\n"
        "        'flags': {name: bool(getattr(sys.flags, name)) for name in ('dont_write_bytecode', 'ignore_environment', 'isolated', 'no_site', 'no_user_site', 'safe_path')},\n"
        "    }\n"
        "    controller_runtime['flags']['utf8_mode'] = int(sys.flags.utf8_mode)\n"
        "    _CONTROLLER_MARKER.write_text(\n"
        "        json.dumps({'argv': argv, 'gate': gate, 'loader': loader_record, 'revalidated': revalidated, 'controller_runtime': controller_runtime}, sort_keys=True),\n"
        "        encoding='utf-8',\n"
        "    )\n"
        "    return 0\n",
        encoding="utf-8",
    )


def _write_execution_tree(execution: Path) -> None:
    source = execution / "src" / "old_execution"
    source.mkdir(parents=True)
    (execution / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    (source / "__init__.py").write_text("# frozen execution\n", encoding="utf-8")
    (execution / "README.md").write_text("frozen synthetic execution\n", encoding="utf-8")


@pytest.fixture
def synthetic_launch(
    tmp_path: Path, synthetic_native_python: dict[str, Any]
) -> dict[str, Any]:
    controller = tmp_path / "controller"
    execution = tmp_path / "execution"
    site_packages = tmp_path / "pinned-site-packages"
    native_runtime = tmp_path / "native-runtime"
    mode_file = tmp_path / "revalidation-mode.txt"
    controller_marker = tmp_path / "controller-reached.json"
    controller.mkdir()
    execution.mkdir()
    site_packages.mkdir()
    native_runtime.mkdir()
    (site_packages / "empty_namespace").mkdir()
    (site_packages / "synthetic_dependency.py").write_text(
        "VALUE = 'pinned dependency'\n", encoding="utf-8"
    )
    scripts = controller / "scripts"
    scripts.mkdir()
    native_launcher = scripts / "week8_recovery_native_launcher.ps1"
    native_launcher.write_bytes(
        b"# synthetic D-167 native launcher; never executed\r\n"
    )
    _write_execution_tree(execution)
    execution_commit = _initialize_repo(execution, detach=True)
    synthetic_entrypoint = controller / "scripts" / ENTRYPOINT_PATH.name
    synthetic_helper = controller / "scripts" / AUTHORITY_PATH.name
    outer_literal = _synthetic_outer_bootstrap(
        synthetic_entrypoint, synthetic_helper
    )
    git = _git_executable()
    powershell = Path(
        "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    if not powershell.is_file():
        pytest.skip("the fixed Windows PowerShell trust-root host is unavailable")
    powershell = powershell.resolve(strict=True)
    python = synthetic_native_python["python"]
    base = synthetic_native_python["base_python"]
    base_runtime = synthetic_native_python["base_runtime"]
    pyvenv = synthetic_native_python["pyvenv"]
    venv_scripts = synthetic_native_python["venv_scripts"]
    config: dict[str, object] = {
        "controller_root": str(controller.resolve()),
        "controller_commit": "",
        "release_receipt_sha256": "",
        "native_launcher_sha256": "",
        "stage0_binding_sha256": "",
        "startup_binding_sha256": "",
        "execution_root": str(execution.resolve()),
        "execution_commit": execution_commit,
        "pinned_python": str(python),
        "pinned_base_python": str(base),
        "pinned_base_runtime": str(base_runtime),
        "pinned_pyvenv": str(pyvenv),
        "pinned_venv_scripts": str(venv_scripts),
        "native_launcher": str(native_launcher.resolve()),
        "native_powershell": str(powershell),
        "native_runtime": str(native_runtime.resolve()),
        "pinned_site_packages": str(site_packages.resolve()),
        "pinned_git": str(git),
        "pinned_git_runtime_root": str(git.parent),
        "pinned_python_sha256": _sha256(python),
        "pinned_base_python_sha256": _sha256(base),
        "pinned_pyvenv_sha256": _sha256(pyvenv),
        **_native_tree_config(
            "pinned_base_runtime", synthetic_native_python["base_identity"]
        ),
        **_native_tree_config(
            "pinned_venv_scripts", synthetic_native_python["venv_identity"]
        ),
        "pinned_git_sha256": _sha256(git),
        **_plain_tree_config("pinned_git_runtime", git.parent),
        **_plain_tree_config("pinned_site_packages", site_packages.resolve()),
        "outer_bootstrap_literal_sha256": _sha256_bytes(
            outer_literal.encode("utf-8")
        ),
    }
    assert set(config) == set(A._CONFIG_KEYS)
    helper_sha256 = _sha256(AUTHORITY_PATH)
    embedded_config = dict(config)
    _write_stub_controller(
        controller,
        embedded_config=embedded_config,
        controller_marker=controller_marker,
        mode_file=mode_file,
        helper_sha256=helper_sha256,
    )
    controller_commit = _initialize_repo(controller, detach=False)
    config["controller_commit"] = controller_commit
    config["release_receipt_sha256"] = _sha256_bytes(
        b"WEEK8_D167_SYNTHETIC_RELEASE_RECEIPT_V1\n"
    )
    config["native_launcher_sha256"] = _sha256(native_launcher)
    config["stage0_binding_sha256"] = _sha256_bytes(
        b"WEEK8_D168_SYNTHETIC_STAGE0_BINDING_V1\n"
    )
    config["startup_binding_sha256"] = _startup_binding_sha256(
        config,
        command="status",
        entrypoint_sha256=_sha256(synthetic_entrypoint),
        helper_sha256=_sha256(synthetic_helper),
        base_runtime=synthetic_native_python["base_identity"],
        venv_scripts=synthetic_native_python["venv_identity"],
    )
    assert config["startup_binding_sha256"] == A._startup_binding_sha256(
        config,
        command="status",
        entrypoint_sha256=_sha256(synthetic_entrypoint),
        helper_sha256=_sha256(synthetic_helper),
        base_runtime=synthetic_native_python["base_identity"],
        venv_scripts=synthetic_native_python["venv_identity"],
        startup_environment_sha256=_startup_environment_sha256(config),
    )
    assert _startup_environment_sha256(config) == A._startup_environment_sha256(
        _startup_environment_pairs(config)
    )
    marker_root = tmp_path / "hostile-markers"
    hostile_markers = [
        *_install_hostile_config(controller, marker_root, "controller"),
        *_install_hostile_config(execution, marker_root, "execution"),
    ]
    return {
        "controller": controller,
        "execution": execution,
        "entrypoint": synthetic_entrypoint,
        "helper": synthetic_helper,
        "outer_literal": outer_literal,
        "site_packages": site_packages,
        "config": config,
        "embedded_config": embedded_config,
        "python": python,
        "base_runtime_identity": synthetic_native_python["base_identity"],
        "venv_scripts_identity": synthetic_native_python["venv_identity"],
        "native_launcher": native_launcher,
        "native_runtime": native_runtime,
        "mode_file": mode_file,
        "hostile_markers": hostile_markers,
        "controller_marker": controller_marker,
    }


def _run_entrypoint(
    scenario: dict[str, Any],
    *,
    flags: tuple[str, ...] = ("-I", "-S", "-B", "-X", "utf8"),
    environment: dict[str, str] | None = None,
    revalidation_mode: str = "none",
    launch_path: Path | None = None,
    command: str = "status",
    extra_arguments: tuple[str, ...] = (),
    startup_binding_override: str | None = None,
    working_directory: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(
        _clean_environment(scenario["config"])
        if environment is None
        else environment
    )
    scenario["mode_file"].write_text(revalidation_mode + "\n", encoding="ascii")
    entrypoint = scenario["entrypoint"] if launch_path is None else launch_path
    outer_literal = (
        scenario["outer_literal"]
        if launch_path is None
        else _synthetic_outer_bootstrap(entrypoint, scenario["helper"])
    )
    entrypoint_sha256 = _sha256(entrypoint)
    helper_sha256 = _sha256(scenario["helper"])
    startup_binding_sha256 = _startup_binding_sha256(
        scenario["config"],
        command=command,
        entrypoint_sha256=entrypoint_sha256,
        helper_sha256=helper_sha256,
        base_runtime=scenario["base_runtime_identity"],
        venv_scripts=scenario["venv_scripts_identity"],
    )
    if startup_binding_override is not None:
        startup_binding_sha256 = startup_binding_override
    return subprocess.run(
        [
            str(scenario["python"]),
            *flags,
            "-c",
            outer_literal,
            entrypoint_sha256,
            helper_sha256,
            scenario["config"]["controller_commit"],
            command,
            scenario["config"]["release_receipt_sha256"],
            scenario["config"]["native_launcher_sha256"],
            scenario["config"]["stage0_binding_sha256"],
            startup_binding_sha256,
            *extra_arguments,
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=env,
        cwd=(
            scenario["native_runtime"]
            if working_directory is None
            else working_directory
        ),
        shell=False,
        timeout=180,
    )


def _commit_embedded_config_change(
    scenario: dict[str, Any], field: str, value: object
) -> None:
    """Commit one synthetic config defect without weakening Git adversaries."""

    entrypoint = scenario["entrypoint"]
    previous_config = dict(scenario["embedded_config"])
    changed_config = {**previous_config, field: value}
    previous_json = json.dumps(
        previous_config, sort_keys=True, separators=(",", ":")
    )
    changed_json = json.dumps(
        changed_config, sort_keys=True, separators=(",", ":")
    )
    previous_line = f"PRODUCTION_CONFIG = json.loads({previous_json!r})"
    changed_line = f"PRODUCTION_CONFIG = json.loads({changed_json!r})"
    source = entrypoint.read_text(encoding="utf-8")
    assert source.count(previous_line) == 1
    entrypoint.write_text(
        source.replace(previous_line, changed_line), encoding="utf-8"
    )

    # The hostile attributes are part of the adversarial raw-Git fixture, not
    # authority for this test-only preparation commit.  Remove and restore
    # them around ``git add`` so their configured process can never execute.
    attributes = scenario["controller"] / ".git" / "info" / "attributes"
    attributes_bytes = attributes.read_bytes()
    attributes.unlink()
    try:
        _setup_git(
            scenario["controller"],
            "add",
            "--",
            entrypoint.relative_to(scenario["controller"]).as_posix(),
        )
        _setup_git(
            scenario["controller"],
            "commit",
            "-q",
            "-m",
            f"synthetic mismatched {field}",
        )
    finally:
        attributes.write_bytes(attributes_bytes)
    controller_commit = _setup_git(
        scenario["controller"], "rev-parse", "HEAD"
    ).decode("ascii").strip()
    scenario["embedded_config"] = changed_config
    scenario["config"][field] = value
    scenario["config"]["controller_commit"] = controller_commit


def test_admitted_entrypoint_runtime_satisfies_real_controller_contract(
    synthetic_launch: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay the real isolated entrypoint's runtime through the controller guard."""
    from bu.experiments import week8_exp2a_recovery as recovery

    completed = _run_entrypoint(synthetic_launch)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    record = json.loads(synthetic_launch["controller_marker"].read_text(encoding="utf-8"))
    runtime = record["controller_runtime"]
    config = synthetic_launch["config"]
    for constant, field in (
        ("PINNED_PYTHON", "pinned_python"),
        ("PINNED_BASE_PYTHON", "pinned_base_python"),
        ("PINNED_SITE_PACKAGES", "pinned_site_packages"),
        ("CONTROLLER_WORKTREE", "controller_root"),
    ):
        monkeypatch.setattr(recovery, constant, Path(config[field]))
    monkeypatch.setattr(recovery, "EXPECTED_PINNED_PYTHON_SHA256", config["pinned_python_sha256"])
    monkeypatch.setattr(recovery, "EXPECTED_PINNED_BASE_PYTHON_SHA256", config["pinned_base_python_sha256"])
    for name in tuple(os.environ):
        if name.upper().startswith("PYTHON"):
            monkeypatch.delenv(name)
    for name, value in runtime["python_environment"].items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(recovery.sys, "executable", runtime["executable"])
    monkeypatch.setattr(recovery.sys, "_base_executable", runtime["base_executable"])
    monkeypatch.setattr(recovery.sys, "path", runtime["sys_path"])
    monkeypatch.setattr(recovery, "_controller_runtime_flags", lambda: runtime["flags"])
    # The child really validated its private raw capability. It cannot be
    # revalidated in this pytest process; replay only the runtime boundary here.
    assert record["revalidated"] == record["gate"]["raw_authority"]
    monkeypatch.setattr(recovery, "_validate_entrypoint_gate", lambda: record["gate"])
    assert recovery._validate_controller_runtime() is record["gate"]


def test_positive_exact_checkouts_reach_only_the_stub_controller(
    synthetic_launch: dict[str, Any]
) -> None:
    completed = _run_entrypoint(synthetic_launch)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert not [path for path in synthetic_launch["hostile_markers"] if path.exists()]
    record = json.loads(synthetic_launch["controller_marker"].read_text(encoding="utf-8"))
    assert record["argv"] == ["status"]
    gate = record["gate"]
    assert gate["entrypoint_gate_schema_version"] == 4
    assert gate["record_type"] == "week8_d161_entrypoint_gate"
    assert gate["command"] == "status"
    assert gate["scientific_outcomes_consulted"] is False
    assert gate["scientific_values_emitted"] is False
    authority = gate["raw_authority"]
    assert authority["raw_authority_schema_version"] == 4
    assert authority["admission"] == {
        "controller_source": str(synthetic_launch["controller"] / "src"),
        "execution_source": str(synthetic_launch["execution"] / "src"),
        "pinned_site_packages": str(synthetic_launch["site_packages"]),
    }
    assert gate["admitted_pythonpath"] == [
        authority["admission"]["controller_source"],
        authority["admission"]["pinned_site_packages"],
    ]
    config = synthetic_launch["config"]
    site_identity = authority["runtime"]["pinned_site_packages"]
    git_runtime_identity = authority["git_runtime"]
    native = authority["native_startup"]
    runtime = authority["runtime"]
    for name in ("inventory_digest", "file_count", "directory_count", "total_bytes"):
        assert site_identity[name] == config[f"pinned_site_packages_{name}"]
        assert git_runtime_identity[name] == config[f"pinned_git_runtime_{name}"]
    assert site_identity["captured_python_source_count"] == 1
    assert site_identity["retained_read_lock_count"] == site_identity["file_count"]
    assert git_runtime_identity["captured_python_source_count"] == 0
    assert (
        git_runtime_identity["retained_read_lock_count"]
        == git_runtime_identity["file_count"]
    )
    assert (
        authority["runtime"]["outer_bootstrap_literal_sha256"]
        == config["outer_bootstrap_literal_sha256"]
    )
    assert authority["runtime"]["entrypoint_source_sha256"] == _sha256(
        synthetic_launch["entrypoint"]
    )
    loader = record["loader"]
    assert loader["binding_marker"] == "week8_d161_verified_source_v2"
    assert loader["tree_kind"] == "controller"
    assert loader["source_sha256"] == _sha256(
        synthetic_launch["controller"]
        / "src"
        / "bu"
        / "experiments"
        / "week8_exp2a_recovery.py"
    )
    assert isinstance(loader["git_blob"], str) and len(loader["git_blob"]) == 40
    assert (
        loader["authority_tree_digest"]
        == authority["controller"]["worktree_inventory_digest"]
    )
    assert (
        loader["dependency_binding_marker"]
        == "week8_d161_verified_dependency_source_v1"
    )
    assert (
        loader["dependency_inventory_digest"]
        == site_identity["inventory_digest"]
    )
    assert record["revalidated"] == gate["raw_authority"]
    assert record["revalidated"]["runtime"]["startup_options"] == [
        "-I",
        "-S",
        "-B",
        "-X",
        "utf8",
    ]
    assert "PYTHONPATH" not in record["revalidated"]["runtime"]["python_environment"]
    assert runtime["startup_environment"] == _clean_environment(config)
    assert len(runtime["startup_environment"]) == 12
    assert runtime["working_directory"] == str(synthetic_launch["native_runtime"])
    assert runtime["active_runtime"] == {
        "executable": config["pinned_python"],
        "base_executable": config["pinned_base_python"],
        "prefix": config["pinned_base_runtime"],
        "base_prefix": config["pinned_base_runtime"],
    }
    assert native["release_receipt_sha256"] == config["release_receipt_sha256"]
    assert native["stage0_binding_sha256"] == config["stage0_binding_sha256"]
    assert native["startup_binding_sha256"] == config["startup_binding_sha256"]
    assert native["native_powershell"] == config["native_powershell"]
    assert native["native_runtime"] == config["native_runtime"]
    assert (
        native["startup_environment_sha256"]
        == _startup_environment_sha256(config)
    )
    assert native["native_launcher"] == {
        "path": str(synthetic_launch["native_launcher"]),
        "size": synthetic_launch["native_launcher"].stat().st_size,
        "sha256": config["native_launcher_sha256"],
    }
    assert native["pinned_pyvenv"] == {
        "path": config["pinned_pyvenv"],
        "size": Path(str(config["pinned_pyvenv"])).stat().st_size,
        "sha256": config["pinned_pyvenv_sha256"],
    }
    assert native["pinned_base_runtime"] == synthetic_launch[
        "base_runtime_identity"
    ]
    assert native["pinned_venv_scripts"] == synthetic_launch[
        "venv_scripts_identity"
    ]
    digest = gate.pop("record_digest")
    assert digest == hashlib.sha256(
        json.dumps(gate, sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


@pytest.mark.parametrize(
    "mode", ("byte-drift", "tree-drift", "helper-drift", "site-drift")
)
def test_post_gate_static_drift_refuses_before_controller_acceptance(
    synthetic_launch: dict[str, Any], mode: str
) -> None:
    completed = _run_entrypoint(synthetic_launch, revalidation_mode=mode)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()
    assert not [path for path in synthetic_launch["hostile_markers"] if path.exists()]


@pytest.mark.parametrize(
    "field",
    (
        "pinned_site_packages_inventory_digest",
        "pinned_git_runtime_inventory_digest",
        "pinned_base_runtime_inventory_sha256",
        "pinned_venv_scripts_inventory_sha256",
    ),
)
def test_schema_v4_refuses_mismatched_authority_tree_identity(
    synthetic_launch: dict[str, Any], field: str
) -> None:
    _commit_embedded_config_change(synthetic_launch, field, "0" * 64)
    completed = _run_entrypoint(synthetic_launch)
    assert completed.returncode == 2
    refusal = json.loads(completed.stdout)
    assert refusal["entrypoint_gate_schema_version"] == 4
    assert refusal["record_type"] == "week8_d161_entrypoint_refusal"
    assert refusal["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()


def test_raw_and_gate_schema_v4_have_one_exact_configuration_contract() -> None:
    assert A.RAW_AUTHORITY_SCHEMA_VERSION == 4
    assert E.ENTRYPOINT_GATE_SCHEMA_VERSION == 4
    assert set(E.PRODUCTION_CONFIG) == set(A._CONFIG_KEYS)
    assert {
        "pinned_git_runtime_root",
        "pinned_git_runtime_inventory_digest",
        "pinned_git_runtime_file_count",
        "pinned_git_runtime_directory_count",
        "pinned_git_runtime_total_bytes",
        "pinned_site_packages_inventory_digest",
        "pinned_site_packages_file_count",
        "pinned_site_packages_directory_count",
        "pinned_site_packages_total_bytes",
        "outer_bootstrap_literal_sha256",
        "release_receipt_sha256",
        "native_launcher_sha256",
        "stage0_binding_sha256",
        "startup_binding_sha256",
        "pinned_base_runtime",
        "pinned_pyvenv",
        "pinned_venv_scripts",
        "native_launcher",
        "native_powershell",
        "native_runtime",
        "pinned_pyvenv_sha256",
        "pinned_base_runtime_inventory_sha256",
        "pinned_base_runtime_file_count",
        "pinned_base_runtime_directory_count",
        "pinned_base_runtime_total_bytes",
        "pinned_venv_scripts_inventory_sha256",
        "pinned_venv_scripts_file_count",
        "pinned_venv_scripts_directory_count",
        "pinned_venv_scripts_total_bytes",
    } <= set(A._CONFIG_KEYS)
    assert set(A._ADMISSION_KEYS) == {
        "controller_source",
        "execution_source",
        "pinned_site_packages",
    }


def test_copied_entrypoint_is_refused_by_fixed_direct_argv_binding(
    synthetic_launch: dict[str, Any], tmp_path: Path
) -> None:
    copied = tmp_path / "copied-entrypoint.py"
    shutil.copyfile(synthetic_launch["entrypoint"], copied)
    completed = _run_entrypoint(synthetic_launch, launch_path=copied)
    assert completed.returncode == 2
    refusal = json.loads(completed.stdout)
    assert refusal["status"] == "refused"
    assert refusal["command"] == "status"
    assert not synthetic_launch["controller_marker"].exists()


@pytest.mark.parametrize(
    "mode", ("digest-drift", "extra-key", "startup-proof-drift")
)
def test_revalidation_refuses_tampered_or_noncanonical_original_authority(
    synthetic_launch: dict[str, Any], mode: str
) -> None:
    completed = _run_entrypoint(synthetic_launch, revalidation_mode=mode)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()
    assert not [path for path in synthetic_launch["hostile_markers"] if path.exists()]


def test_all_ignored_shadow_forms_refuse_before_any_shadow_or_helper_executes(
    synthetic_launch: dict[str, Any]
) -> None:
    source = synthetic_launch["controller"] / "src"
    shadow_marker = source.parent / "shadow-import.executed"
    effect = (
        "from pathlib import Path\n"
        f"Path({str(shadow_marker)!r}).write_text('executed', encoding='utf-8')\n"
    )
    for relative, data in (
        ("json.py", effect),
        ("numpy.py", effect),
        ("cache.pyc", "not bytecode"),
        ("native.pyd", "not extension code"),
        ("shadow_package/__init__.py", effect),
    ):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
    completed = _run_entrypoint(synthetic_launch)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not shadow_marker.exists()
    assert not synthetic_launch["controller_marker"].exists()
    assert not [path for path in synthetic_launch["hostile_markers"] if path.exists()]


@pytest.mark.parametrize(
    "flags",
    (
        ("-S", "-B", "-X", "utf8"),
        ("-I", "-B", "-X", "utf8"),
        ("-I", "-S", "-X", "utf8"),
        ("-I", "-S", "-B", "utf8"),
        ("-I", "-S", "-B", "-X"),
    ),
)
def test_each_required_python_flag_is_enforced(
    synthetic_launch: dict[str, Any], flags: tuple[str, ...]
) -> None:
    completed = _run_entrypoint(synthetic_launch, flags=flags)
    assert completed.returncode == 2
    assert not synthetic_launch["controller_marker"].exists()
    assert not [path for path in synthetic_launch["hostile_markers"] if path.exists()]


def test_orig_argv_refuses_a_seventeenth_item(
    synthetic_launch: dict[str, Any],
) -> None:
    completed = _run_entrypoint(
        synthetic_launch, extra_arguments=("unexpected-seventeenth-item",)
    )
    assert completed.returncode != 0
    assert not synthetic_launch["controller_marker"].exists()
    assert not [path for path in synthetic_launch["hostile_markers"] if path.exists()]


def test_startup_binding_hash_mismatch_is_refused(
    synthetic_launch: dict[str, Any],
) -> None:
    completed = _run_entrypoint(
        synthetic_launch, startup_binding_override="0" * 64
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()


def test_native_launcher_hash_mismatch_is_refused(
    synthetic_launch: dict[str, Any],
) -> None:
    synthetic_launch["config"]["native_launcher_sha256"] = "0" * 64
    completed = _run_entrypoint(synthetic_launch)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()


def test_complete_environment_refuses_an_unregistered_name(
    synthetic_launch: dict[str, Any],
) -> None:
    environment = _clean_environment(synthetic_launch["config"])
    environment["COMSPEC"] = "C:\\Windows\\System32\\cmd.exe"
    completed = _run_entrypoint(synthetic_launch, environment=environment)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()


def test_native_working_directory_is_exact(
    synthetic_launch: dict[str, Any],
) -> None:
    completed = _run_entrypoint(
        synthetic_launch, working_directory=synthetic_launch["execution"]
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()


def test_native_runtime_must_be_empty_before_authority(
    synthetic_launch: dict[str, Any],
) -> None:
    (synthetic_launch["native_runtime"] / "unexpected-residue").write_bytes(b"x")
    completed = _run_entrypoint(synthetic_launch)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()


def test_pythonpath_must_be_absent_at_process_start(
    synthetic_launch: dict[str, Any], tmp_path: Path
) -> None:
    environment = _clean_environment(synthetic_launch["config"])
    environment["PYTHONPATH"] = str((tmp_path / "benign-path").resolve())
    completed = _run_entrypoint(synthetic_launch, environment=environment)
    assert completed.returncode == 2
    assert not synthetic_launch["controller_marker"].exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows normalizes os.environ keys")
def test_mis_cased_startup_python_name_is_rejected_in_a_real_process(
    synthetic_launch: dict[str, Any],
) -> None:
    environment = _clean_environment(synthetic_launch["config"])
    environment["pythonhashseed"] = "0"
    completed = _run_entrypoint(synthetic_launch, environment=environment)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "refused"
    assert not synthetic_launch["controller_marker"].exists()


def test_helper_is_hash_bound_before_its_source_can_execute(tmp_path: Path) -> None:
    marker = tmp_path / "malicious-helper.executed"
    helper = tmp_path / "malicious-helper.py"
    helper.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    with pytest.raises(E.EntrypointRefused, match="SHA256 differs"):
        E._load_raw_authority(helper.resolve(), "0" * 64)
    assert not marker.exists()


def test_embedded_helper_digest_matches_every_consumer() -> None:
    helper_digest = _sha256(AUTHORITY_PATH)
    consumers = {
        "entrypoint": E.RAW_AUTHORITY_HELPER_SHA256,
        "worker": _literal_assignment(
            WORKER_PATH, "EXPECTED_RAW_AUTHORITY_HELPER_SHA256"
        ),
        "inspector": _literal_assignment(
            INSPECTOR_PATH, "EXPECTED_RAW_AUTHORITY_HELPER_SHA256"
        ),
        "fit_child": _literal_assignment(
            FIT_CHILD_PATH, "EXPECTED_RAW_AUTHORITY_HELPER_SHA256"
        ),
        "controller": _literal_assignment(
            CONTROLLER_PATH, "EXPECTED_RAW_AUTHORITY_HELPER_SHA256"
        ),
    }
    assert consumers == dict.fromkeys(consumers, helper_digest)
    assert E.RAW_AUTHORITY_HELPER.is_absolute()
    assert E.ENTRYPOINT_PATH.is_absolute()


def test_outer_bootstrap_literal_digest_matches_every_consumer() -> None:
    literal_digest = hashlib.sha256(OUTER_BOOTSTRAP_PATH.read_bytes()).hexdigest()
    consumers = {
        "entrypoint": E.OUTER_BOOTSTRAP_LITERAL_SHA256,
        "worker": _literal_assignment(
            WORKER_PATH, "EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256"
        ),
        "inspector": _literal_assignment(
            INSPECTOR_PATH, "EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256"
        ),
        "fit_child": _literal_assignment(
            FIT_CHILD_PATH, "EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256"
        ),
        "controller": _literal_assignment(
            CONTROLLER_PATH, "EXPECTED_OUTER_BOOTSTRAP_LITERAL_SHA256"
        ),
    }
    assert consumers == dict.fromkeys(consumers, literal_digest)


def test_runbook_routes_every_e2a_command_through_d168_stage_zero() -> None:
    source = RUNBOOK_PATH.read_text(encoding="utf-8")
    for command in (
        "status",
        "adjudicate",
        "recover",
        "seal",
        "monitor",
        "finalize",
        "report",
        "figures",
    ):
        assert f"stage0-{command}-audit.txt" in source
    assert "-m bu.experiments.week8_exp2a_production" not in source
    assert "$Incident = Get-Content" not in source
    assert "$RecoveryCommit = $Incident" not in source
    assert "week8_recovery_stage0.py" in source
    assert "week8_recovery_native_launcher.ps1" in source
    assert "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" in source
    assert "-EncodedCommand" in source
    assert "stage0_cmd_payload=" in source
    assert "audit record deliberately contains no executable command" in source
    assert "-I -S -B -X utf8" in source
    for token in (
        "FINAL_RECEIPT_SHA256",
        "FINAL_NATIVE_LAUNCHER_SHA256",
        "FINAL_OUTER_SHA256",
        "FINAL_ENTRYPOINT_SHA256",
        "FINAL_HELPER_SHA256",
        "FINAL_CONTROLLER_COMMIT",
        "stage0-source-sha256",
        "stage0-encoded-sha256",
        "stage0-environment-policy-sha256",
    ):
        assert token in source


def test_direct_entrypoint_imports_only_standard_library_before_authority() -> None:
    allowed = {
        "__future__",
        "hashlib",
        "importlib",
        "json",
        "os",
        "stat",
        "sys",
        "pathlib",
        "types",
        "typing",
    }
    tree = ast.parse(ENTRYPOINT_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".", 1)[0])
    assert imported <= allowed
    source = ENTRYPOINT_PATH.read_text(encoding="utf-8")
    assert "python -m" not in source.lower()
    assert "bu.experiments.week8_exp2a_recovery" in source


@pytest.mark.parametrize("command", tuple(sorted(E.COMMANDS)))
def test_only_the_fixed_commands_are_accepted(command: str) -> None:
    assert E._validate_command(command) == command


@pytest.mark.parametrize("command", (None, "", "pilot", "status --verbose", True, 7))
def test_every_other_command_is_refused(command: object) -> None:
    with pytest.raises(E.EntrypointRefused, match="allowlisted"):
        E._validate_command(command)
