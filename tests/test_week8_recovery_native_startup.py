"""Synthetic and Windows integration contracts for the D-168 native launch."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "week8_recovery_native_launcher.ps1"
RAW_HELPER = ROOT / "scripts" / "week8_recovery_raw_authority.py"
STAGE0_HELPER = ROOT / "scripts" / "week8_recovery_stage0.py"
INBOX_POWERSHELL = Path(
    "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)

SPEC = importlib.util.spec_from_file_location("d167_native_raw_under_test", RAW_HELPER)
assert SPEC is not None and SPEC.loader is not None
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
assert isinstance(A, ModuleType)

STAGE0_SPEC = importlib.util.spec_from_file_location(
    "d168_stage0_under_native_test", STAGE0_HELPER
)
assert STAGE0_SPEC is not None and STAGE0_SPEC.loader is not None
S = importlib.util.module_from_spec(STAGE0_SPEC)
STAGE0_SPEC.loader.exec_module(S)
assert isinstance(S, ModuleType)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manual_native_identity(root: Path) -> dict[str, object]:
    rows: list[tuple[str, str, int, str]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            rows.append((relative, "D", 0, ""))
        else:
            data = path.read_bytes()
            rows.append((relative, "F", len(data), hashlib.sha256(data).hexdigest()))
    payload = bytearray()
    for relative, kind, size, digest in sorted(rows):
        if kind == "D":
            payload.extend(f"D\t{relative}\n".encode())
        else:
            payload.extend(f"F\t{relative}\t{size}\t{digest}\n".encode())
    return {
        "path": str(root.resolve()),
        "file_count": sum(kind == "F" for _, kind, _, _ in rows),
        "directory_count": sum(kind == "D" for _, kind, _, _ in rows),
        "total_bytes": sum(size for _, kind, size, _ in rows if kind == "F"),
        "inventory_sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_native_tree_identity_matches_the_powershell_tsv_contract(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    (root / "Lib" / "nested").mkdir(parents=True)
    (root / "python.exe").write_bytes(b"launcher\x00")
    (root / "Lib" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "Lib" / "nested" / "native.pyd").write_bytes(b"native")

    assert A._native_tree_identity(root.resolve()) == _manual_native_identity(
        root.resolve()
    )


def test_native_tree_identity_refuses_a_linked_entry_where_supported(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    target = tmp_path / "target.bin"
    target.write_bytes(b"target")
    linked = root / "linked.bin"
    try:
        os.symlink(target, linked)
    except OSError as exc:
        pytest.skip(f"host policy does not permit synthetic links: {exc}")

    with pytest.raises(A.AuthorityRefused, match="linked or reparse"):
        A._native_tree_identity(root.resolve())


def test_launcher_source_is_windows_powershell_51_compatible_and_fail_closed() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    forbidden = (
        "[Convert]::ToHexString",
        "[IO.Path]::GetRelativePath",
        "[Diagnostics.ProcessStartInfo]::new",
        "$Info.ArgumentList",
        "$Info.Environment.Clear()",
    )
    assert not any(token in source for token in forbidden)
    for required in (
        "$Info.EnvironmentVariables.Clear()",
        "ConvertTo-Week8WindowsArgument",
        "FileShare]::Read",
        "$ExpectedBaseRuntimeFileCount = 5368",
        "$ExpectedVenvScriptsFileCount = 22",
        "$ExpectedPowerShell = 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'",
        "Read-Week8ReleaseReceipt",
        "WEEK8_D168_RELEASE_RECEIPT_V2",
        "Get-Week8Stage0BindingSha256",
        "stage0_binding_sha256=",
        "Get-Week8StartupBindingSha256",
    ):
        assert required in source


def test_native_stage0_environment_policy_is_byte_identical_to_fixed_stage0() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    function = source.split(
        "function Get-Week8Stage0BindingSha256", 1
    )[1].split("$Environment =", 1)[0]
    rows = re.findall(r"@\('([^']+)',\s*([^)]+)\)", function)
    pairs: list[tuple[str, str]] = []
    for name, expression in rows:
        if expression == "$Stage0Runtime":
            value = str(S.STAGE0_RUNTIME)
        else:
            assert expression.startswith("'") and expression.endswith("'")
            value = expression[1:-1]
        pairs.append((name, value))
    expected_pairs = sorted(S.STAGE0_FIXED_ENVIRONMENT, key=lambda pair: pair[0])
    assert pairs == expected_pairs
    policy_pairs = sorted(
        (
            *pairs,
            (S.STAGE0_ENVELOPE_ENVIRONMENT, "<CANONICAL_BASE64_ENVELOPE>"),
        ),
        key=lambda pair: pair[0],
    )
    policy = (
        "WEEK8_D168_STAGE0_ENVIRONMENT_POLICY_V1\n"
        + "".join(f"{name}={value}\n" for name, value in policy_pairs)
    ).encode("ascii")
    assert hashlib.sha256(policy).hexdigest() == S.STAGE0_ENVIRONMENT_POLICY_SHA256


@pytest.mark.skipif(os.name != "nt", reason="native startup is Windows-only")
def test_inbox_powershell_smoke_binds_exact_argv_environment_and_prefixes(
    tmp_path: Path,
) -> None:
    assert INBOX_POWERSHELL.is_file()
    runtime = tmp_path / "native-smoke-runtime"
    completed = subprocess.run(
        [
            str(INBOX_POWERSHELL),
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(LAUNCHER),
            "-StartupSmoke",
            "-SmokeRuntime",
            str(runtime),
        ],
        cwd=ROOT.parent,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    lines = [line for line in completed.stdout.splitlines() if line]
    assert len(lines) == 1
    report = json.loads(lines[0])
    assert report["argv"] == [
        "-c",
        "plain",
        "two words",
        'quote"inside',
        "trailing\\",
        "line1\nline2",
        "",
    ]
    original = report["orig_argv"]
    assert Path(original[0]).samefile(
        Path("D:/Aenv/pro2/pro2/.venv/Scripts/python.exe")
    )
    assert original[1:7] == ["-I", "-S", "-B", "-X", "utf8", "-c"]
    assert original[8:] == [
        "plain",
        "two words",
        'quote"inside',
        "trailing\\",
        "line1\nline2",
        "",
    ]
    assert isinstance(original[7], str) and "native_environment" in original[7]
    assert Path(report["cwd"]).samefile(runtime)
    assert Path(report["executable"]).samefile(
        Path("D:/Aenv/pro2/pro2/.venv/Scripts/python.exe")
    )
    base = Path(
        "D:/Aenv/pro2/runtimes/week8-python313-frozen-001"
    )
    assert Path(report["base_executable"]).samefile(base / "python.exe")
    assert Path(report["prefix"]).samefile(base)
    assert Path(report["base_prefix"]).samefile(base)
    expected_environment = [
        "CUDA_VISIBLE_DEVICES=-1",
        "HIP_VISIBLE_DEVICES=-1",
        "MKL_NUM_THREADS=4",
        "NUMEXPR_NUM_THREADS=4",
        "OMP_NUM_THREADS=4",
        "OPENBLAS_NUM_THREADS=4",
        f"PATH={base};C:\\Windows\\System32;C:\\Windows",
        "SystemRoot=C:\\Windows",
        f"TEMP={runtime}",
        f"TMP={runtime}",
        f"TMPDIR={runtime}",
        "WINDIR=C:\\Windows",
    ]
    assert report["native_environment"] == expected_environment
    assert list(runtime.iterdir()) == []


def test_release_artifact_paths_are_project_local_and_current() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert str(ROOT).replace("/", "\\") in source
    assert _sha(RAW_HELPER) != "0" * 64
