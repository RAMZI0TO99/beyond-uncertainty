"""Behavioral and Windows integration tests for fixed D-168 stage 0."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
STAGE0_SCRIPT = ROOT / "scripts" / "week8_recovery_stage0.py"
RECEIPT_SCRIPT = ROOT / "scripts" / "week8_recovery_release_receipt.py"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert isinstance(module, ModuleType)
    return module


S = _load("d168_stage0_under_test", STAGE0_SCRIPT)
R = _load("d168_receipt_under_test", RECEIPT_SCRIPT)
PROJECT_ROOT = Path("D:/Aenv/pro2")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project_local(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    try:
        absolute.relative_to(PROJECT_ROOT)
    except ValueError as exc:  # pragma: no cover - harness safety failure
        raise AssertionError("pytest scratch must be project-local") from exc
    return absolute


def _ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _empty_fixed_runtime() -> None:
    runtime = _project_local(S.STAGE0_RUNTIME)
    runtime.mkdir(parents=False, exist_ok=True)
    assert runtime.is_dir() and not runtime.is_symlink()
    assert list(runtime.iterdir()) == []


def _fixture(
    tmp_path: Path,
    *,
    command: str = "status",
    release_variant: int = 1,
) -> dict[str, object]:
    _empty_fixed_runtime()
    tmp_path.mkdir(parents=True, exist_ok=True)
    launcher = _project_local(tmp_path / "synthetic-launcher.ps1")
    receipt = _project_local(tmp_path / "synthetic-receipt-v2.txt")
    marker = _project_local(tmp_path / "launcher-marker.txt")
    launcher.write_text(
        "param([string] $ReleaseReceipt,[string] $ReceiptSha256,"
        "[string] $LauncherSha256,[string] $Command)\n"
        "$Outcome='mutated'\n"
        f"try {{ [IO.File]::WriteAllText({_ps(str(launcher))},'tamper') }} "
        "catch { $Outcome='blocked' }\n"
        "$Rows=@([Environment]::GetEnvironmentVariables().GetEnumerator() | "
        "Sort-Object Name | ForEach-Object { $_.Name+'='+[string]$_.Value })\n"
        f"[IO.File]::WriteAllText({_ps(str(marker))},"
        "$Outcome+'|'+$Command+'|'+($Rows -join \"`n\"))\n",
        encoding="utf-8",
        newline="\n",
    )
    launcher_sha = _sha(launcher)
    receipt.write_bytes(
        R.render_release_receipt(
            controller_commit=f"{release_variant:x}" * 40,
            native_launcher_sha256=launcher_sha,
            outer_sha256=f"{release_variant + 1:x}" * 64,
            entry_sha256=f"{release_variant + 2:x}" * 64,
            helper_sha256=f"{release_variant + 3:x}" * 64,
            stage0_source_sha256=S.STAGE0_SOURCE_SHA256,
            stage0_encoded_sha256=S.STAGE0_ENCODED_SHA256,
            stage0_environment_policy_sha256=(
                S.STAGE0_ENVIRONMENT_POLICY_SHA256
            ),
        )
    )
    kwargs = {
        "launcher_path": str(launcher),
        "receipt_path": str(receipt),
        "launcher_sha256": launcher_sha,
        "receipt_sha256": _sha(receipt),
        "command": command,
    }
    return {
        "launcher": launcher,
        "receipt": receipt,
        "marker": marker,
        "kwargs": kwargs,
    }


def _command_line(fixture: dict[str, object]) -> str:
    kwargs = fixture["kwargs"]
    assert isinstance(kwargs, dict)
    envelope = S.render_stage0_envelope(**kwargs)
    return S.render_stage0_cmd_command_line(envelope=envelope)


def _run(
    command_line: str,
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command_line,
        executable=str(S.CMD),
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=False,
        timeout=45,
    )


def _replace_once(command_line: str, old: str, new: str) -> str:
    assert command_line.count(old) == 1
    return command_line.replace(old, new, 1)


def test_fixed_source_policy_hashes_and_cmd_limit_are_exact(tmp_path: Path) -> None:
    first = _fixture(tmp_path / "first", command="status")
    second_path = tmp_path / "second"
    second_path.mkdir()
    second = _fixture(second_path, command="seal", release_variant=5)
    first_kwargs = first["kwargs"]
    second_kwargs = second["kwargs"]
    assert isinstance(first_kwargs, dict) and isinstance(second_kwargs, dict)

    first_envelope = S.render_stage0_envelope(**first_kwargs)
    second_envelope = S.render_stage0_envelope(**second_kwargs)
    assert first_envelope != second_envelope
    assert S.render_stage0_source() == S.STAGE0_SOURCE
    assert hashlib.sha256(S.STAGE0_SOURCE.encode("utf-8")).hexdigest() == (
        S.STAGE0_SOURCE_SHA256
    )
    assert hashlib.sha256(S.STAGE0_ENCODED_COMMAND.encode("ascii")).hexdigest() == (
        S.STAGE0_ENCODED_SHA256
    )
    assert base64.b64decode(S.STAGE0_ENCODED_COMMAND, validate=True).decode(
        "utf-16le"
    ) == S.STAGE0_SOURCE
    assert hashlib.sha256(S.STAGE0_ENVIRONMENT_POLICY_BYTES).hexdigest() == (
        S.STAGE0_ENVIRONMENT_POLICY_SHA256
    )
    for envelope in (first_envelope, second_envelope):
        command_line = S.render_stage0_cmd_command_line(envelope=envelope)
        actual_length = len(command_line)
        assert actual_length <= S.CMD_COMMAND_LINE_LIMIT
        assert actual_length < 8191


@pytest.mark.parametrize("command", sorted(S.COMMANDS))
def test_every_operation_changes_only_the_envelope(
    tmp_path: Path, command: str
) -> None:
    fixture = _fixture(tmp_path, command=command)
    kwargs = fixture["kwargs"]
    assert isinstance(kwargs, dict)
    envelope = S.render_stage0_envelope(**kwargs)
    decoded = base64.b64decode(envelope, validate=True).decode("ascii")
    assert f"c={command}\n" in decoded
    assert S.render_stage0_source() == S.STAGE0_SOURCE
    assert S.STAGE0_SOURCE_SHA256 == hashlib.sha256(
        S.render_stage0_source().encode("utf-8")
    ).hexdigest()


def test_policy_cli_prints_only_canonical_fixed_hashes() -> None:
    completed = subprocess.run(
        [sys.executable, str(STAGE0_SCRIPT), "--policy"],
        check=False,
        capture_output=True,
        text=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stderr == b""
    assert completed.stdout == S.render_stage0_policy()
    assert b"command=" not in completed.stdout
    assert b"receipt" not in completed.stdout


def test_normal_cli_keeps_executable_payload_only_on_stdout(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    kwargs = fixture["kwargs"]
    assert isinstance(kwargs, dict)
    output = _project_local(tmp_path / "stage0-cli-audit.txt")
    completed = subprocess.run(
        [
            sys.executable,
            str(STAGE0_SCRIPT),
            "--output",
            str(output),
            "--launcher-path",
            str(kwargs["launcher_path"]),
            "--receipt-path",
            str(kwargs["receipt_path"]),
            "--launcher-sha256",
            str(kwargs["launcher_sha256"]),
            "--receipt-sha256",
            str(kwargs["receipt_sha256"]),
            "--command",
            str(kwargs["command"]),
        ],
        check=False,
        capture_output=True,
        text=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stderr == b""
    assert b"stage0_record_sha256=" in completed.stdout
    assert b"stage0_cmd_payload=" in completed.stdout
    record = output.read_bytes()
    assert b"stage0_cmd_payload=" not in record
    assert S.STAGE0_ENCODED_COMMAND.encode("ascii") not in record
    os.chmod(output, stat.S_IWRITE | stat.S_IREAD)


@pytest.mark.skipif(os.name != "nt", reason="explicit non-Windows exclusion")
def test_actual_cmd_clears_hostile_environment_and_retains_both_files(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    command_line = _command_line(fixture)
    hostile_cwd = _project_local(tmp_path / "hostile-cwd")
    hostile_cwd.mkdir()
    hostile = dict(os.environ)
    hostile.update(
        {
            "COR_ENABLE_PROFILING": "1",
            "COR_PROFILER": "{11111111-1111-1111-1111-111111111111}",
            "COR_PROFILER_PATH": str(hostile_cwd / "cor-profiler.dll"),
            "CORECLR_ENABLE_PROFILING": "1",
            "CORECLR_PROFILER": "{22222222-2222-2222-2222-222222222222}",
            "CORECLR_PROFILER_PATH": str(hostile_cwd / "core-profiler.dll"),
            "DOTNET_ENABLE_PROFILING": "1",
            "DOTNET_STARTUP_HOOKS": str(hostile_cwd / "hook.dll"),
            "PATH": str(hostile_cwd),
            "PSModulePath": str(hostile_cwd),
            "TEMP": str(hostile_cwd),
            "TMP": str(hostile_cwd),
            "TMPDIR": str(hostile_cwd),
            "WEEK8_ATTACKER_EXTRA": "must-disappear",
        }
    )
    completed = _run(command_line, cwd=hostile_cwd, environment=hostile)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")

    launcher = fixture["launcher"]
    marker = fixture["marker"]
    assert isinstance(launcher, Path) and isinstance(marker, Path)
    assert launcher.read_text(encoding="utf-8").startswith("param(")
    outcome, command, rows_text = marker.read_text(encoding="utf-8").split("|", 2)
    assert outcome == "blocked"
    assert command == "status"
    observed = dict(row.split("=", 1) for row in rows_text.splitlines())
    kwargs = fixture["kwargs"]
    assert isinstance(kwargs, dict)
    expected = dict(S.STAGE0_FIXED_ENVIRONMENT)
    expected[S.STAGE0_ENVELOPE_ENVIRONMENT] = S.render_stage0_envelope(**kwargs)
    assert observed == expected
    assert not any(
        name.upper().startswith(("COR_", "CORECLR_", "DOTNET_"))
        for name in observed
    )
    assert len(command_line) < 8191


@pytest.mark.skipif(os.name != "nt", reason="explicit non-Windows exclusion")
@pytest.mark.parametrize(
    "target", ("receipt", "envelope", "payload", "launcher", "command")
)
def test_tampering_refuses_before_synthetic_launcher_marker(
    tmp_path: Path, target: str
) -> None:
    fixture = _fixture(tmp_path)
    command_line = _command_line(fixture)
    marker = fixture["marker"]
    launcher = fixture["launcher"]
    receipt = fixture["receipt"]
    kwargs = fixture["kwargs"]
    assert isinstance(marker, Path)
    assert isinstance(launcher, Path)
    assert isinstance(receipt, Path)
    assert isinstance(kwargs, dict)
    envelope = S.render_stage0_envelope(**kwargs)

    if target == "receipt":
        receipt.write_bytes(receipt.read_bytes() + b"tampered")
    elif target == "launcher":
        launcher.write_bytes(launcher.read_bytes() + b"# tampered\n")
    elif target == "envelope":
        replacement = ("B" if envelope[0] != "B" else "C") + envelope[1:]
        command_line = _replace_once(command_line, envelope, replacement)
    elif target == "command":
        raw = base64.b64decode(envelope, validate=True)
        assert b"c=status\n" in raw
        changed = base64.b64encode(raw.replace(b"c=status\n", b"c=seal\n"))
        command_line = _replace_once(
            command_line, envelope, changed.decode("ascii")
        )
    else:
        encoded = S.STAGE0_ENCODED_COMMAND
        index = len(encoded) // 2
        replacement = "A" if encoded[index] != "A" else "B"
        command_line = _replace_once(
            command_line,
            encoded,
            encoded[:index] + replacement + encoded[index + 1 :],
        )

    completed = _run(command_line, cwd=_project_local(tmp_path))
    assert completed.returncode != 0
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="explicit non-Windows exclusion")
def test_audit_record_is_non_executable_read_only_and_never_consumed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    kwargs = fixture["kwargs"]
    marker = fixture["marker"]
    assert isinstance(kwargs, dict) and isinstance(marker, Path)
    output = _project_local(tmp_path / "stage0-status.txt")
    digest, cmd_payload = S._create_stage0_record(output=str(output), **kwargs)
    payload = output.read_bytes()
    assert digest == hashlib.sha256(payload).hexdigest()
    assert b"EncodedCommand" not in payload
    assert b"stage0_cmd_payload" not in payload
    assert b"invocation=" not in payload
    assert S.STAGE0_ENCODED_COMMAND.encode("ascii") not in payload
    assert cmd_payload == S.render_stage0_cmd_payload(
        envelope=S.render_stage0_envelope(**kwargs)
    )
    with pytest.raises(OSError):
        output.write_bytes(b"ordinary overwrite must fail")
    os.chmod(output, stat.S_IWRITE | stat.S_IREAD)
    output.write_bytes(b"malicious archived record that is never read")

    completed = _run(_command_line(fixture), cwd=_project_local(tmp_path))
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert marker.exists()
    assert output.read_bytes().startswith(b"malicious archived")


def test_stage0_record_is_exclusive_and_preserves_first_bytes(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    kwargs = fixture["kwargs"]
    assert isinstance(kwargs, dict)
    output = _project_local(tmp_path / "stage0-once.txt")
    S.create_stage0_record(output=str(output), **kwargs)
    before = output.read_bytes()
    with pytest.raises(S.Stage0Refused, match="already exists"):
        S.create_stage0_record(output=str(output), **kwargs)
    assert output.read_bytes() == before
    os.chmod(output, stat.S_IWRITE | stat.S_IREAD)


@pytest.mark.parametrize("command", [True, "STATUS", "pilot", ""])
def test_stage0_refuses_non_allowlisted_command(
    tmp_path: Path, command: object
) -> None:
    fixture = _fixture(tmp_path)
    kwargs = dict(fixture["kwargs"])
    kwargs["command"] = command
    with pytest.raises(S.Stage0Refused, match="not allowlisted"):
        S.render_stage0_envelope(**kwargs)
