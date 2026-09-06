"""Adversarial synthetic tests for the standard-library D-161 authority.

Every repository and marker is created under ``tmp_path``.  The suite never
opens or mutates production recovery evidence and never imports project code
through the authority under test.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "scripts" / "week8_recovery_raw_authority.py"
SPEC = importlib.util.spec_from_file_location(
    "week8_recovery_raw_authority_under_test", AUTHORITY_PATH
)
assert SPEC is not None and SPEC.loader is not None
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
assert isinstance(A, ModuleType)


@pytest.mark.skipif(os.name != "nt", reason="Windows preserves raw env-key spelling")
@pytest.mark.parametrize(
    "name",
    ("pythonhashseed", "bu_d161_invocation_digest", "git_config_count"),
)
def test_native_environment_reader_preserves_mis_cased_control_names(
    tmp_path: Path, name: str
) -> None:
    probe = tmp_path / "exact_environment_probe.py"
    probe.write_text(
        "import importlib.util, json, sys\n"
        "spec = importlib.util.spec_from_file_location('raw_probe', sys.argv[1])\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "wanted = sys.argv[2].upper()\n"
        "print(json.dumps([(k, v) for k, v in module.exact_environment_items() "
        "if k.upper() == wanted]))\n",
        encoding="utf-8",
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() != name.upper()
    }
    value = "0" if name == "pythonhashseed" else "synthetic-value"
    environment[name] = value
    completed = subprocess.run(
        [sys.executable, str(probe), str(AUTHORITY_PATH), name],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [[name, value]]


def _git_executable() -> Path:
    fixed = Path(
        "C:/Users/aladdin-alyanai/.cache/codex-runtimes/"
        "codex-primary-runtime/dependencies/native/git/mingw64/bin/git.exe"
    )
    if fixed.is_file():
        return fixed.resolve()
    discovered = shutil.which("git")
    if discovered is None:
        pytest.skip("Git is unavailable for the raw-authority contract tests")
    return Path(discovered).resolve()


def _setup_environment() -> dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if not name.upper().startswith("GIT_")
    }


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
        env=_setup_environment(),
        shell=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.decode("utf-8", errors="replace"))
    return completed.stdout


def _hostile_command(helper: Path, marker: Path, label: str) -> str:
    return f'"{sys.executable}" "{helper}" "{marker}" "{label}"'


def _install_hostile_local_config(repo: Path, marker_root: Path) -> list[Path]:
    marker_root.mkdir()
    git_dir = repo / ".git"
    helper = git_dir / "authority-hostile-helper.py"
    helper.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')\n"
        "raise SystemExit(17)\n",
        encoding="utf-8",
    )
    labels = ("fsmonitor", "pager", "clean", "process", "hook")
    markers = [marker_root / f"{label}.executed" for label in labels]
    commands = {label: _hostile_command(helper, marker, label) for label, marker in zip(labels, markers)}
    for key, value in (
        ("core.fsmonitor", commands["fsmonitor"]),
        ("core.pager", commands["pager"]),
        ("pager.ls-tree", commands["pager"]),
        ("filter.evil.clean", commands["clean"]),
        ("filter.evil.process", commands["process"]),
        ("core.hooksPath", commands["hook"]),
    ):
        _setup_git(repo, "config", "--local", key, value)
    info = git_dir / "info"
    info.mkdir(exist_ok=True)
    (info / "attributes").write_text(
        "*.py filter=evil diff=evil\n", encoding="utf-8"
    )
    return markers


@pytest.fixture
def hostile_repo(tmp_path: Path) -> tuple[Path, str, list[Path]]:
    repo = tmp_path / "authority-repository"
    repo.mkdir()
    _setup_git(repo, "init", "-q")
    _setup_git(repo, "config", "user.name", "Synthetic Authority")
    _setup_git(repo, "config", "user.email", "authority@example.invalid")
    (repo / ".gitignore").write_text(
        "src/json.py\n"
        "src/numpy.py\n"
        "src/*.pyc\n"
        "src/*.pyd\n"
        "src/shadow_package/\n",
        encoding="utf-8",
    )
    package = repo / "src" / "bu"
    package.mkdir(parents=True)
    (repo / "README.md").write_text("exact authority fixture\n", encoding="utf-8")
    (package / "__init__.py").write_text("# package\n", encoding="utf-8")
    (package / "module.py").write_text("VALUE = 7\n", encoding="utf-8")
    _setup_git(repo, "add", "--", ".")
    _setup_git(repo, "commit", "-q", "-m", "authority fixture")
    commit = _setup_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    _setup_git(repo, "checkout", "-q", "--detach", commit)
    markers = _install_hostile_local_config(repo, tmp_path / "hostile-markers")
    return repo, commit, markers


def _verify(repo: Path, commit: str) -> dict[str, object]:
    return A.verify_worktree(
        repo,
        git_executable=_git_executable(),
        expected_commit=commit,
        require_detached=True,
    )


def _verify_with_captured_python(repo: Path, commit: str) -> dict[str, object]:
    return A.verify_worktree(
        repo,
        git_executable=_git_executable(),
        expected_commit=commit,
        require_detached=True,
        capture_python=True,
    )


def _execution_authority(
    repo: Path, identity: dict[str, object]
) -> dict[str, object]:
    return {
        "execution": identity,
        "admission": {"execution_source": str(repo / "src")},
    }


def _assert_no_hostile_marker(markers: list[Path]) -> None:
    assert not [path for path in markers if path.exists()]


def test_exact_tree_uses_only_four_allowlisted_plumbing_queries_and_runs_no_helper(
    hostile_repo: tuple[Path, str, list[Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit, markers = hostile_repo
    observed: list[tuple[str, ...]] = []
    real_run = A.subprocess.run

    def recording_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        root_index = command.index("-C")
        observed.append(tuple(command[root_index + 2 :]))
        return real_run(command, **kwargs)

    monkeypatch.setattr(A.subprocess, "run", recording_run)
    result = _verify(repo, commit)
    assert result["git_commit"] == commit
    assert result["detached"] is True
    assert result["tracked_file_count"] == 4
    assert observed == [
        ("rev-parse", "--verify", "HEAD^{commit}"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("ls-tree", "-r", "-z", "--full-tree", commit),
        ("ls-files", "--stage", "-z"),
        ("rev-parse", "--verify", "HEAD^{commit}"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("ls-tree", "-r", "-z", "--full-tree", commit),
        ("ls-files", "--stage", "-z"),
    ]
    _assert_no_hostile_marker(markers)


@pytest.mark.parametrize(
    "mutation",
    ("modified", "staged", "deleted", "extra", "extra_directory"),
)
def test_every_worktree_or_index_difference_refuses_without_running_helpers(
    hostile_repo: tuple[Path, str, list[Path]], mutation: str
) -> None:
    repo, commit, markers = hostile_repo
    readme = repo / "README.md"
    if mutation == "modified":
        readme.write_text("unstaged difference\n", encoding="utf-8")
    elif mutation == "staged":
        readme.write_text("staged difference\n", encoding="utf-8")
        attributes = repo / ".git" / "info" / "attributes"
        hostile_attributes = attributes.read_bytes()
        attributes.unlink()
        try:
            _setup_git(repo, "add", "--", "README.md")
        finally:
            attributes.write_bytes(hostile_attributes)
    elif mutation == "deleted":
        readme.unlink()
    elif mutation == "extra":
        (repo / "untracked.txt").write_text("extra\n", encoding="utf-8")
    else:
        (repo / "empty-extra-directory").mkdir()
    with pytest.raises(A.AuthorityRefused):
        _verify(repo, commit)
    _assert_no_hostile_marker(markers)


@pytest.mark.parametrize(
    ("relative", "payload"),
    (
        ("src/json.py", "raise RuntimeError('json shadow executed')\n"),
        ("src/numpy.py", "raise RuntimeError('numpy shadow executed')\n"),
        ("src/cache.pyc", "not bytecode"),
        ("src/native.pyd", "not an extension"),
        ("src/shadow_package/__init__.py", "raise RuntimeError('package shadow')\n"),
    ),
)
def test_every_ignored_import_shadow_refuses_without_execution(
    hostile_repo: tuple[Path, str, list[Path]], relative: str, payload: str
) -> None:
    repo, commit, markers = hostile_repo
    shadow = repo / relative
    shadow.parent.mkdir(parents=True, exist_ok=True)
    shadow.write_text(payload, encoding="utf-8")
    side_effect = shadow.with_suffix(shadow.suffix + ".executed")
    assert not side_effect.exists()
    with pytest.raises(A.AuthorityRefused, match="files differ"):
        _verify(repo, commit)
    assert not side_effect.exists()
    _assert_no_hostile_marker(markers)


def test_tracked_hardlink_refuses(
    hostile_repo: tuple[Path, str, list[Path]], tmp_path: Path
) -> None:
    repo, commit, markers = hostile_repo
    alias = tmp_path / "outside-hardlink"
    try:
        os.link(repo / "README.md", alias)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")
    with pytest.raises(A.AuthorityRefused, match="hardlinked"):
        _verify(repo, commit)
    _assert_no_hostile_marker(markers)


def test_tracked_symlink_or_reparse_refuses(
    hostile_repo: tuple[Path, str, list[Path]], tmp_path: Path
) -> None:
    repo, commit, markers = hostile_repo
    tracked = repo / "README.md"
    target = tmp_path / "same-bytes-target"
    target.write_bytes(tracked.read_bytes())
    tracked.unlink()
    try:
        tracked.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(A.AuthorityRefused, match="linked or reparse"):
        _verify(repo, commit)
    _assert_no_hostile_marker(markers)


def test_reparse_attribute_is_a_fail_closed_plain_file_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "synthetic-reparse"
    candidate.write_bytes(b"plain bytes with a synthetic reparse attribute")
    monkeypatch.setattr(A, "_is_reparse", lambda info: True)
    with pytest.raises(A.AuthorityRefused, match="one-link plain file"):
        A._plain_file_info(candidate, what="synthetic reparse")


@pytest.mark.parametrize(
    "arguments",
    (
        ("status",),
        ("diff",),
        ("hash-object", "README.md"),
        ("ls-files",),
        ("ls-tree", "HEAD"),
        ("rev-parse", "HEAD"),
    ),
)
def test_git_query_allowlist_fails_closed(arguments: tuple[str, ...]) -> None:
    with pytest.raises(A.AuthorityRefused, match="allowlist"):
        A._validate_git_arguments(arguments)


def test_git_environment_removes_every_inherited_git_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "9")
    monkeypatch.setenv("git_config_key_0", "core.fsmonitor")
    git = _git_executable()
    environment = A._isolated_git_environment(git)
    assert set(environment) == {
        "GIT_ATTR_NOSYSTEM",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_SYSTEM",
        "GIT_EXEC_PATH",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_OPTIONAL_LOCKS",
        "GIT_PAGER",
        "GIT_TERMINAL_PROMPT",
        "GIT_TEMPLATE_DIR",
        "LC_ALL",
        "PATH",
        "SystemRoot",
        "WINDIR",
    }
    assert environment["GIT_ATTR_NOSYSTEM"] == "1"
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert environment["GIT_EXEC_PATH"] == str(git.parent)
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_PAGER"] == "cat"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_TEMPLATE_DIR"] == os.devnull
    assert environment["LC_ALL"] == "C"
    path_parts = environment["PATH"].split(os.pathsep)
    assert path_parts[0] == str(git.parent)
    assert environment["SystemRoot"] == environment["WINDIR"]
    assert os.environ.get("PATH") not in environment["PATH"]


def test_admitted_revalidator_is_a_public_standard_library_api() -> None:
    expected = {
        "admitted_execution_source_bytes",
        "admitted_execution_sources",
        "admitted_source_bytes",
        "admitted_sources",
        "revalidate_admitted_authority",
        "verified_source_finder",
        "verify_plain_tree",
    }
    assert expected <= set(A.__all__)
    assert all(callable(getattr(A, name)) for name in expected)


def test_tree_parser_refuses_symlinks_gitlinks_and_non_sha1_objects() -> None:
    for record in (
        b"120000 blob " + b"a" * 40 + b"\tlink\0",
        b"160000 commit " + b"a" * 40 + b"\tsubmodule\0",
        b"100644 blob " + b"a" * 64 + b"\tsha256-object\0",
    ):
        with pytest.raises(A.AuthorityRefused, match="non-plain"):
            A._parse_tree(record)


def test_plain_tree_identity_binds_file_bytes_and_empty_directories(
    tmp_path: Path,
) -> None:
    root = tmp_path / "dependency-tree"
    empty = root / "empty" / "nested"
    empty.mkdir(parents=True)
    payload = root / "payload.bin"
    payload.write_bytes(b"authority bytes")

    identity = A.verify_plain_tree(root)

    assert identity == A.verify_plain_tree(root)
    assert identity["path"] == str(root)
    assert identity["file_count"] == 1
    assert identity["directory_count"] == 2
    assert identity["total_bytes"] == len(b"authority bytes")
    assert identity["stability_observations"] == 2
    assert len(identity["inventory_digest"]) == 64


@pytest.mark.parametrize("mutation", ("content", "extra_file", "empty_directory"))
def test_plain_tree_identity_changes_for_every_inventory_dimension(
    tmp_path: Path, mutation: str
) -> None:
    root = tmp_path / "dependency-tree"
    root.mkdir()
    payload = root / "payload.bin"
    payload.write_bytes(b"before")
    original = A.verify_plain_tree(root)

    if mutation == "content":
        payload.write_bytes(b"after!")
    elif mutation == "extra_file":
        (root / "extra.bin").write_bytes(b"extra")
    else:
        (root / "empty").mkdir()

    changed = A.verify_plain_tree(root)
    assert changed["inventory_digest"] != original["inventory_digest"]
    if mutation == "content":
        assert changed["file_count"] == original["file_count"]
        assert changed["total_bytes"] == original["total_bytes"]
    elif mutation == "extra_file":
        assert changed["file_count"] == original["file_count"] + 1
    else:
        assert changed["directory_count"] == original["directory_count"] + 1


def test_plain_tree_refuses_hardlinks(tmp_path: Path) -> None:
    root = tmp_path / "dependency-tree"
    root.mkdir()
    payload = root / "payload.bin"
    payload.write_bytes(b"one-link only")
    alias = tmp_path / "outside-hardlink"
    try:
        os.link(payload, alias)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")

    with pytest.raises(A.AuthorityRefused, match="hardlinked"):
        A.verify_plain_tree(root)


def test_plain_tree_refuses_symlink_or_reparse_entries(tmp_path: Path) -> None:
    root = tmp_path / "dependency-tree"
    root.mkdir()
    target = tmp_path / "target.bin"
    target.write_bytes(b"target")
    link = root / "linked.bin"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(A.AuthorityRefused, match="linked or reparse"):
        A.verify_plain_tree(root)


def test_plain_tree_refuses_content_change_between_observations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "dependency-tree"
    root.mkdir()
    payload = root / "payload.bin"
    payload.write_bytes(b"first-observation")
    original = A._plain_tree_rows
    calls = 0

    def mutate_after_first_rows(
        files: dict[str, Path], directories: set[str]
    ) -> list[dict[str, object]]:
        nonlocal calls
        rows = original(files, directories)
        calls += 1
        if calls == 1:
            payload.write_bytes(b"second-observation")
        return rows

    monkeypatch.setattr(A, "_plain_tree_rows", mutate_after_first_rows)
    with pytest.raises(A.AuthorityRefused, match="stable observations"):
        A.verify_plain_tree(root)


def test_captured_execution_sources_are_complete_defensive_and_cache_bound(
    hostile_repo: tuple[Path, str, list[Path]],
) -> None:
    repo, commit, markers = hostile_repo
    identity = _verify_with_captured_python(repo, commit)
    authority = _execution_authority(repo, identity)

    sources = A.admitted_execution_sources(authority)
    expected = {
        relative: (repo / relative).read_bytes()
        for relative in ("src/bu/__init__.py", "src/bu/module.py")
    }
    assert sources == expected
    assert A.admitted_execution_source_bytes(
        authority, "src/bu/module.py"
    ) == expected["src/bu/module.py"]
    sources["src/bu/module.py"] = b"VALUE = 99\n"
    assert A.admitted_execution_sources(authority)[
        "src/bu/module.py"
    ] == expected["src/bu/module.py"]

    tampered = deepcopy(authority)
    tampered["execution"]["worktree_inventory_digest"] = "0" * 64
    with pytest.raises(A.AuthorityRefused, match="cache differs"):
        A.admitted_execution_sources(tampered)
    _assert_no_hostile_marker(markers)


def test_verified_execution_finder_executes_captured_bytes_not_later_disk_bytes(
    hostile_repo: tuple[Path, str, list[Path]], tmp_path: Path
) -> None:
    repo, commit, markers = hostile_repo
    bu = repo / "src" / "bu"
    identity = _verify_with_captured_python(repo, commit)
    authority = _execution_authority(repo, identity)
    finder = A.verified_source_finder(authority, "execution")
    captured = A.admitted_execution_source_bytes(authority, "src/bu/module.py")
    marker = tmp_path / "later-disk-bytes.executed"
    (bu / "module.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "VALUE = 99\n",
        encoding="utf-8",
    )

    specification = finder.find_spec("bu.module")
    assert specification is not None and specification.loader is not None
    assert finder.binding_marker == "week8_d161_verified_source_v2"
    assert specification.loader.binding_marker == finder.binding_marker
    assert specification.loader.tree_kind == "execution"
    assert specification.loader.source_sha256 == A.sha256_bytes(captured)
    assert specification.loader.git_blob == A.admitted_git_blob(
        authority, "execution", "src/bu/module.py"
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    assert module.VALUE == 7
    assert not marker.exists()
    assert finder.find_spec("json") is None
    with pytest.raises(ImportError, match="absent"):
        finder.find_spec("bu.missing")
    _assert_no_hostile_marker(markers)


def test_captured_execution_sources_survive_identical_reobservation(
    hostile_repo: tuple[Path, str, list[Path]],
) -> None:
    repo, commit, markers = hostile_repo
    first_identity = _verify_with_captured_python(repo, commit)
    first_authority = _execution_authority(repo, first_identity)
    expected = A.admitted_execution_sources(first_authority)

    second_identity = _verify_with_captured_python(repo, commit)
    second_authority = _execution_authority(repo, second_identity)
    assert second_identity == first_identity
    assert A.admitted_execution_sources(second_authority) == expected
    _assert_no_hostile_marker(markers)
