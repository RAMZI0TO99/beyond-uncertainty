"""Synthetic contract tests for the standalone D-168 V2 receipt writer."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "week8_recovery_release_receipt.py"
SPEC = importlib.util.spec_from_file_location(
    "week8_recovery_release_receipt_under_test",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)
assert isinstance(R, ModuleType)

PROJECT_ROOT = Path("D:/Aenv/pro2")
COMMIT = "1" * 40
NATIVE = "2" * 64
OUTER = "3" * 64
ENTRY = "4" * 64
HELPER = "5" * 64
STAGE0_SOURCE = "6" * 64
STAGE0_ENCODED = "7" * 64
STAGE0_POLICY = "8" * 64
EXPECTED = (
    "WEEK8_D168_RELEASE_RECEIPT_V2\n"
    f"controller_commit={COMMIT}\n"
    f"native_launcher_sha256={NATIVE}\n"
    f"outer_sha256={OUTER}\n"
    f"entry_sha256={ENTRY}\n"
    f"helper_sha256={HELPER}\n"
    f"stage0_source_sha256={STAGE0_SOURCE}\n"
    f"stage0_encoded_sha256={STAGE0_ENCODED}\n"
    f"stage0_environment_policy_sha256={STAGE0_POLICY}\n"
).encode("ascii")


def _project_local(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    try:
        absolute.relative_to(PROJECT_ROOT)
    except ValueError as exc:  # pragma: no cover - a harness safety failure
        raise AssertionError("pytest scratch must be project-local") from exc
    return absolute


def _arguments(output: Path) -> dict[str, object]:
    return {
        "output": str(_project_local(output)),
        "controller_commit": COMMIT,
        "native_launcher_sha256": NATIVE,
        "outer_sha256": OUTER,
        "entry_sha256": ENTRY,
        "helper_sha256": HELPER,
        "stage0_source_sha256": STAGE0_SOURCE,
        "stage0_encoded_sha256": STAGE0_ENCODED,
        "stage0_environment_policy_sha256": STAGE0_POLICY,
    }


def test_cli_creates_exact_ascii_lf_bytes_without_bom(tmp_path: Path) -> None:
    output = _project_local(tmp_path / "release-receipt.txt")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output",
            str(output),
            "--controller-commit",
            COMMIT,
            "--native-launcher-sha256",
            NATIVE,
            "--outer-sha256",
            OUTER,
            "--entry-sha256",
            ENTRY,
            "--helper-sha256",
            HELPER,
            "--stage0-source-sha256",
            STAGE0_SOURCE,
            "--stage0-encoded-sha256",
            STAGE0_ENCODED,
            "--stage0-environment-policy-sha256",
            STAGE0_POLICY,
        ],
        check=False,
        capture_output=True,
        text=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stdout == b""
    assert completed.stderr == b""
    assert output.read_bytes() == EXPECTED
    assert b"\r" not in EXPECTED
    assert not EXPECTED.startswith(b"\xef\xbb\xbf")


def test_create_returns_exact_digest(tmp_path: Path) -> None:
    output = _project_local(tmp_path / "digest-receipt.txt")
    digest = R.create_release_receipt(**_arguments(output))
    assert digest == hashlib.sha256(EXPECTED).hexdigest()
    assert output.read_bytes() == EXPECTED


def test_second_render_refuses_and_preserves_first_receipt(tmp_path: Path) -> None:
    output = _project_local(tmp_path / "one-use-receipt.txt")
    R.create_release_receipt(**_arguments(output))
    before = output.read_bytes()

    with pytest.raises(R.ReleaseReceiptRefused, match="already exists"):
        R.create_release_receipt(**_arguments(output))

    assert before == EXPECTED
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("controller_commit", True),
        ("controller_commit", "1" * 39),
        ("controller_commit", "A" * 40),
        ("controller_commit", "g" * 40),
        ("native_launcher_sha256", False),
        ("native_launcher_sha256", "2" * 63),
        ("native_launcher_sha256", "A" * 64),
        ("outer_sha256", None),
        ("outer_sha256", b"3" * 64),
        ("entry_sha256", "4" * 65),
        ("helper_sha256", "z" * 64),
        ("stage0_source_sha256", "6" * 63),
        ("stage0_encoded_sha256", "G" * 64),
        ("stage0_environment_policy_sha256", True),
    ],
)
def test_invalid_fields_refuse_before_creation(
    tmp_path: Path,
    field: str,
    invalid: object,
) -> None:
    output = _project_local(tmp_path / f"invalid-{field}.txt")
    arguments = _arguments(output)
    arguments[field] = invalid

    with pytest.raises(R.ReleaseReceiptRefused, match=field):
        R.create_release_receipt(**arguments)

    assert not os.path.lexists(output)


@pytest.mark.parametrize("invalid_output", [True, None, "relative-receipt.txt"])
def test_noncanonical_output_values_refuse(
    tmp_path: Path,
    invalid_output: object,
) -> None:
    arguments = _arguments(_project_local(tmp_path / "unused.txt"))
    arguments["output"] = invalid_output
    with pytest.raises(R.ReleaseReceiptRefused, match="absolute project-local"):
        R.create_release_receipt(**arguments)


def test_outside_project_path_refuses_without_writing() -> None:
    outside = Path("C:/week8-d167-synthetic-outside/receipt.txt")
    assert not os.path.lexists(outside)
    arguments = _arguments(PROJECT_ROOT / ".tmp" / "unused-receipt.txt")
    arguments["output"] = str(outside)

    with pytest.raises(R.ReleaseReceiptRefused, match="outside D:/Aenv/pro2"):
        R.create_release_receipt(**arguments)

    assert not os.path.lexists(outside)


def test_preexisting_file_is_refused_and_preserved(tmp_path: Path) -> None:
    output = _project_local(tmp_path / "preexisting.txt")
    original = b"do-not-overwrite\r\n"
    output.write_bytes(original)

    with pytest.raises(R.ReleaseReceiptRefused, match="already exists"):
        R.create_release_receipt(**_arguments(output))

    assert output.read_bytes() == original


def test_non_plain_parent_is_refused_and_preserved(tmp_path: Path) -> None:
    non_directory = _project_local(tmp_path / "not-a-directory")
    original = b"parent-file"
    non_directory.write_bytes(original)
    output = non_directory / "receipt.txt"

    with pytest.raises(R.ReleaseReceiptRefused, match="not a plain directory"):
        R.create_release_receipt(**_arguments(output))

    assert non_directory.read_bytes() == original
    assert not os.path.lexists(output)


def test_linked_or_reparse_parent_is_refused(tmp_path: Path) -> None:
    target = _project_local(tmp_path / "real-parent")
    target.mkdir()
    linked_parent = _project_local(tmp_path / "linked-parent")
    if os.name == "nt":
        command_line = (
            f'{Path("C:/Windows/System32/cmd.exe")} /d /q /v:off /c '
            f'mklink /J "{linked_parent}" "{target}"'
        )
        completed = subprocess.run(
            command_line,
            executable=str(Path("C:/Windows/System32/cmd.exe")),
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
    else:
        os.symlink(target, linked_parent, target_is_directory=True)

    output = linked_parent / "receipt.txt"
    with pytest.raises(R.ReleaseReceiptRefused, match="linked or reparse"):
        R.create_release_receipt(**_arguments(output))

    assert R._is_reparse(linked_parent.lstat())
    assert not os.path.lexists(target / "receipt.txt")
    if os.name == "nt":
        os.rmdir(linked_parent)
