"""Render the fixed D-168 pre-PowerShell authority ceremony.

The committed PowerShell source and its UTF-16LE Base64 payload never vary.
Release and command values exist only in one checksum-framed Base64 envelope.
The audit record is create-once/read-only evidence and is never executable;
the executable cmd payload exists only in renderer memory and on stdout.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import stat
import sys
import zlib
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path("D:/Aenv/pro/pro")
CMD = Path("C:/Windows/System32/cmd.exe")
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
STAGE0_RUNTIME = Path(
    "D:/Aenv/pro/pro/week8-d168-stage0-runtime-attempt-001"
)
STAGE0_ENVELOPE_ENVIRONMENT = "WEEK8_D168_STAGE0_ENVELOPE"
STAGE0_ENVELOPE_HEADER = "WEEK8_D168_STAGE0_ENVELOPE_V1"
STAGE0_AUDIT_HEADER = "WEEK8_D168_STAGE0_AUDIT_RECORD_V2"
RECEIPT_HEADER = "WEEK8_D168_RELEASE_RECEIPT_V2"
COMMANDS = frozenset(
    {
        "status",
        "adjudicate",
        "recover",
        "seal",
        "monitor",
        "finalize",
        "report",
        "figures",
    }
)
CMD_COMMAND_LINE_LIMIT = 8191

STAGE0_FIXED_ENVIRONMENT = (
    ("ComSpec", r"C:\Windows\System32\cmd.exe"),
    ("PATH", r"C:\Windows\System32;C:\Windows"),
    ("PathEXT", ".CPL"),
    (
        "PSModulePath",
        r"C:\Program Files\WindowsPowerShell\Modules;"
        r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules",
    ),
    ("SystemRoot", r"C:\Windows"),
    ("TEMP", str(STAGE0_RUNTIME)),
    ("TMP", str(STAGE0_RUNTIME)),
    ("TMPDIR", str(STAGE0_RUNTIME)),
    ("WINDIR", r"C:\Windows"),
)
STAGE0_ENVIRONMENT_POLICY_HEADER = (
    "WEEK8_D168_STAGE0_ENVIRONMENT_POLICY_V1"
)
_POLICY_PAIRS = tuple(
    sorted(
        (
            *STAGE0_FIXED_ENVIRONMENT,
            (STAGE0_ENVELOPE_ENVIRONMENT, "<CANONICAL_BASE64_ENVELOPE>"),
        ),
        key=lambda pair: pair[0],
    )
)
STAGE0_ENVIRONMENT_POLICY_BYTES = (
    STAGE0_ENVIRONMENT_POLICY_HEADER
    + "\n"
    + "".join(f"{name}={value}\n" for name, value in _POLICY_PAIRS)
).encode("ascii")
STAGE0_ENVIRONMENT_POLICY_SHA256 = hashlib.sha256(
    STAGE0_ENVIRONMENT_POLICY_BYTES
).hexdigest()

_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_HEX40 = re.compile(r"[0-9a-f]{40}\Z", re.ASCII)
_REPARSE = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
_READONLY = int(getattr(stat, "FILE_ATTRIBUTE_READONLY", 0x1))


class Stage0Refused(ValueError):
    """The fixed stage-0 ceremony could not be rendered exactly."""


def _ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _build_stage0_source() -> str:
    commands = "|".join(sorted(COMMANDS))
    envelope_pattern = (
        rf"\A{STAGE0_ENVELOPE_HEADER}\n"
        rf"r=([ -~]+)\nR=([0-9a-f]{{64}})\n"
        rf"l=([ -~]+)\nL=([0-9a-f]{{64}})\n"
        rf"c=({commands})\nh=([0-9a-f]{{64}})\n\z"
    )
    receipt_pattern = (
        rf"\A{RECEIPT_HEADER}\n"
        r"controller_commit=([0-9a-f]{40})\n"
        r"native_launcher_sha256=([0-9a-f]{64})\n"
        r"outer_sha256=([0-9a-f]{64})\n"
        r"entry_sha256=([0-9a-f]{64})\n"
        r"helper_sha256=([0-9a-f]{64})\n"
        r"stage0_source_sha256=([0-9a-f]{64})\n"
        r"stage0_encoded_sha256=([0-9a-f]{64})\n"
        r"stage0_environment_policy_sha256=([0-9a-f]{64})\n\z"
    )
    return rf"""$ErrorActionPreference='Stop';Set-StrictMode -Version 3
$U=New-Object Text.UTF8Encoding($false,$true)
function D8H($b){{$x=[Security.Cryptography.SHA256]::Create();return ([BitConverter]::ToString($x.ComputeHash($b))).Replace('-','').ToLowerInvariant()}}
$W={_ps(str(POWERSHELL))};$R={_ps(str(STAGE0_RUNTIME))};$N={_ps(STAGE0_ENVELOPE_ENVIRONMENT)};$Q={_ps(STAGE0_ENVIRONMENT_POLICY_SHA256)}
$d=Get-Item -Force $R;$o=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName;if($o -ine $W){{throw 11}};if($PSVersionTable.PSVersion.ToString() -notlike '5.1*'){{throw 12}};if((Get-Location).Path -ine $R){{throw 13}};if(-not $d.PSIsContainer -or ($d.Attributes -band 1024)){{throw 14}};if(@(Get-ChildItem -Force $R).Count){{throw 15}}
$E=[Environment]::GetEnvironmentVariables();$a=[string[]]@($E.Keys);[Array]::Sort($a,[StringComparer]::Ordinal);$p={_ps(STAGE0_ENVIRONMENT_POLICY_HEADER)}+"`n";foreach($k in $a){{$v=[string]$E[$k];if($k -ceq $N){{$v='<CANONICAL_BASE64_ENVELOPE>'}};$p+="$k=$v`n"}};if((D8H ($U.GetBytes($p))) -cne $Q){{throw 2}}
$m=[regex]::Match([Environment]::CommandLine,'(?i)-EncodedCommand\s+([A-Za-z0-9+/]+={{0,2}})\s*$');if(-not $m.Success){{throw 3}};$Z=$m.Groups[1].Value;$b=[Convert]::FromBase64String($Z);if([Convert]::ToBase64String($b) -cne $Z){{throw 3}};$ZH=D8H ([Text.Encoding]::ASCII.GetBytes($Z));$SH=D8H ($U.GetBytes([Text.Encoding]::Unicode.GetString($b)))
$X=[string]$E[$N];$b=[Convert]::FromBase64String($X);if([Convert]::ToBase64String($b) -cne $X){{throw 4}};$T=$U.GetString($b);if((D8H ([Text.Encoding]::ASCII.GetBytes($T))) -cne (D8H $b)){{throw 4}};$m=[regex]::Match($T,{_ps(envelope_pattern)});if(-not $m.Success){{throw 4}};$i=$T.LastIndexOf('h=');if((D8H ($U.GetBytes($T.Substring(0,$i)))) -cne $m.Groups[6].Value){{throw 4}};$RP=$m.Groups[1].Value;$RS=$m.Groups[2].Value;$LP=$m.Groups[3].Value;$LS=$m.Groups[4].Value;$C=$m.Groups[5].Value
function O($p,$h){{$f=[IO.Path]::GetFullPath($p);if($f -cne $p -or -not $f.StartsWith({_ps(str(PROJECT_ROOT) + os.sep)},5)){{throw 5}};$i=Get-Item -Force -LiteralPath $f;if($i.PSIsContainer -or ($i.Attributes -band 1024)){{throw 5}};$s=[IO.File]::Open($f,3,1,1);$b=[IO.File]::ReadAllBytes($f);if((D8H $b) -cne $h){{$s.Dispose();throw 5}};[pscustomobject]@{{S=$s;B=$b}}}}
$A=$null;$F=$null;try{{$A=O $LP $LS;$F=O $RP $RS;$Y=$U.GetString($F.B);if((D8H ([Text.Encoding]::ASCII.GetBytes($Y))) -cne $RS){{throw 6}};$m=[regex]::Match($Y,{_ps(receipt_pattern)});if(-not $m.Success -or $m.Groups[2].Value -cne $LS -or $m.Groups[6].Value -cne $SH -or $m.Groups[7].Value -cne $ZH -or $m.Groups[8].Value -cne $Q){{throw 6}};& ([ScriptBlock]::Create($U.GetString($A.B))) -ReleaseReceipt $Y -ReceiptSha256 $RS -LauncherSha256 $LS -Command $C;if(-not $?){{throw 7}}}}finally{{if($F){{$F.S.Dispose()}};if($A){{$A.S.Dispose()}}}}
"""


STAGE0_BODY = _build_stage0_source()
_compressor = zlib.compressobj(level=9, wbits=-15)
_compressed_body = _compressor.compress(STAGE0_BODY.encode("utf-8"))
_compressed_body += _compressor.flush()
_body_base64 = base64.b64encode(_compressed_body).decode("ascii")
STAGE0_SOURCE = (
    "$ErrorActionPreference='Stop';"
    f"$b=[Convert]::FromBase64String('{_body_base64}');"
    "$m=New-Object IO.MemoryStream;$m.Write($b,0,$b.Length);$m.Position=0;"
    "$d=New-Object IO.Compression.DeflateStream($m,"
    "[IO.Compression.CompressionMode]::Decompress);"
    "$r=New-Object IO.StreamReader($d);iex $r.ReadToEnd()"
)
STAGE0_ENCODED_COMMAND = base64.b64encode(
    STAGE0_SOURCE.encode("utf-16le")
).decode("ascii")
STAGE0_SOURCE_SHA256 = hashlib.sha256(STAGE0_SOURCE.encode("utf-8")).hexdigest()
STAGE0_ENCODED_SHA256 = hashlib.sha256(
    STAGE0_ENCODED_COMMAND.encode("ascii")
).hexdigest()


def render_stage0_source() -> str:
    """Return the release- and command-independent committed source."""

    return STAGE0_SOURCE


def render_stage0_policy() -> bytes:
    """Return canonical ASCII/LF hashes consumed by the release ceremony."""

    return (
        "WEEK8_D168_STAGE0_POLICY_V1\n"
        f"stage0_source_sha256={STAGE0_SOURCE_SHA256}\n"
        f"stage0_encoded_sha256={STAGE0_ENCODED_SHA256}\n"
        f"stage0_environment_policy_sha256={STAGE0_ENVIRONMENT_POLICY_SHA256}\n"
    ).encode("ascii")


def _plain_directory_chain(path: Path, *, what: str) -> None:
    for component in reversed((path, *path.parents)):
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise Stage0Refused(f"{what} parent chain is unavailable") from exc
        if (
            stat.S_ISLNK(metadata.st_mode)
            or int(getattr(metadata, "st_file_attributes", 0)) & _REPARSE
            or not stat.S_ISDIR(metadata.st_mode)
        ):
            raise Stage0Refused(f"{what} parent chain is linked or non-plain")


def _plain_project_file(value: object, *, what: str) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        raise Stage0Refused(f"{what} must be one absolute project-local file")
    path = Path(value)
    lexical = Path(os.path.abspath(value))
    if not path.is_absolute() or path != lexical:
        raise Stage0Refused(f"{what} must be one absolute project-local file")
    try:
        lexical.relative_to(Path(os.path.abspath(PROJECT_ROOT)))
    except ValueError as exc:
        raise Stage0Refused(f"{what} is outside the project") from exc
    if any(ord(character) > 0x7F or ord(character) < 0x20 for character in str(lexical)):
        raise Stage0Refused(f"{what} path must be printable ASCII")
    _plain_directory_chain(lexical.parent, what=what)
    try:
        metadata = lexical.lstat()
    except OSError as exc:
        raise Stage0Refused(f"{what} is unavailable") from exc
    if (
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0)) & _REPARSE
        or not stat.S_ISREG(metadata.st_mode)
        or int(getattr(metadata, "st_nlink", 0)) != 1
    ):
        raise Stage0Refused(f"{what} is not one-link plain file")
    return lexical


def _sha(value: object, *, what: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise Stage0Refused(f"{what} is not canonical lowercase SHA-256")
    return value


def _parse_receipt_for_stage0(payload: bytes) -> dict[str, str]:
    try:
        text = payload.decode("ascii", errors="strict")
    except UnicodeError as exc:
        raise Stage0Refused("release receipt is not strict ASCII") from exc
    names = (
        "controller_commit",
        "native_launcher_sha256",
        "outer_sha256",
        "entry_sha256",
        "helper_sha256",
        "stage0_source_sha256",
        "stage0_encoded_sha256",
        "stage0_environment_policy_sha256",
    )
    lines = text.split("\n")
    if len(lines) != 10 or lines[0] != RECEIPT_HEADER or lines[-1] != "":
        raise Stage0Refused("release receipt V2 framing differs")
    values: dict[str, str] = {}
    for expected, row in zip(names, lines[1:-1], strict=True):
        parts = row.split("=")
        if len(parts) != 2 or parts[0] != expected:
            raise Stage0Refused("release receipt V2 field order differs")
        values[expected] = parts[1]
    if _HEX40.fullmatch(values["controller_commit"]) is None:
        raise Stage0Refused("release receipt controller commit differs")
    if any(_HEX64.fullmatch(values[name]) is None for name in names[1:]):
        raise Stage0Refused("release receipt hash field differs")
    if values["stage0_source_sha256"] != STAGE0_SOURCE_SHA256:
        raise Stage0Refused("release receipt stage-0 source binding differs")
    if values["stage0_encoded_sha256"] != STAGE0_ENCODED_SHA256:
        raise Stage0Refused("release receipt stage-0 encoded binding differs")
    if (
        values["stage0_environment_policy_sha256"]
        != STAGE0_ENVIRONMENT_POLICY_SHA256
    ):
        raise Stage0Refused("release receipt environment-policy binding differs")
    return values


def render_stage0_envelope(
    *,
    launcher_path: object,
    receipt_path: object,
    launcher_sha256: object,
    receipt_sha256: object,
    command: object,
) -> str:
    """Return the strict canonical Base64 value for the sole dynamic variable."""

    launcher = _plain_project_file(launcher_path, what="native launcher")
    receipt = _plain_project_file(receipt_path, what="release receipt")
    launcher_digest = _sha(launcher_sha256, what="native launcher SHA-256")
    receipt_digest = _sha(receipt_sha256, what="release receipt SHA-256")
    launcher_bytes = launcher.read_bytes()
    receipt_bytes = receipt.read_bytes()
    if hashlib.sha256(launcher_bytes).hexdigest() != launcher_digest:
        raise Stage0Refused("native launcher bytes differ from supplied SHA-256")
    if hashlib.sha256(receipt_bytes).hexdigest() != receipt_digest:
        raise Stage0Refused("release receipt bytes differ from supplied SHA-256")
    if type(command) is not str or command not in COMMANDS:
        raise Stage0Refused("stage-0 command is not allowlisted")
    receipt_values = _parse_receipt_for_stage0(receipt_bytes)
    if receipt_values["native_launcher_sha256"] != launcher_digest:
        raise Stage0Refused("release receipt does not bind the native launcher")

    body = (
        f"{STAGE0_ENVELOPE_HEADER}\n"
        f"r={receipt}\n"
        f"R={receipt_digest}\n"
        f"l={launcher}\n"
        f"L={launcher_digest}\n"
        f"c={command}\n"
    ).encode("ascii", errors="strict")
    payload = body + f"h={hashlib.sha256(body).hexdigest()}\n".encode("ascii")
    encoded = base64.b64encode(payload).decode("ascii")
    if base64.b64encode(base64.b64decode(encoded, validate=True)).decode() != encoded:
        raise Stage0Refused("internal stage-0 envelope is noncanonical")
    return encoded


def _cmd_batch(envelope: str) -> str:
    if (
        type(envelope) is not str
        or not envelope
        or re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", envelope, re.ASCII) is None
    ):
        raise Stage0Refused("stage-0 envelope is not canonical Base64")
    disable = (
        'set "COR_ENABLE_PROFILING="',
        'set "CORECLR_ENABLE_PROFILING="',
        'set "DOTNET_ENABLE_PROFILING="',
        f'set "ComSpec={CMD}"',
    )
    clear = '(for /f "tokens=1 delims==" %G in (\'set\') do @set "%G=")'
    install = tuple(f'set "{name}={value}"' for name, value in STAGE0_FIXED_ENVIRONMENT)
    install += (f'set "{STAGE0_ENVELOPE_ENVIRONMENT}={envelope}"',)
    batch = "&".join((*disable, clear, *install))
    batch += f'&cd /d "{STAGE0_RUNTIME}"&&'
    batch += (
        f'"{POWERSHELL}" -NoLogo -NoProfile -NonInteractive '
        f"-EncodedCommand {STAGE0_ENCODED_COMMAND}"
    )
    return batch


def render_stage0_cmd_command_line(*, envelope: object) -> str:
    """Return the verbatim CreateProcess command line for absolute cmd.exe.

    ``subprocess.list2cmdline`` must not be used for cmd.exe: its CRT-style
    backslash-quote escaping is not cmd syntax.  Callers pass this string with
    ``executable=str(CMD)`` so the absolute image is selected independently.
    """

    if type(envelope) is not str:
        raise Stage0Refused("stage-0 envelope is not a string")
    line = f"{CMD} /d /q /v:off /c {_cmd_batch(envelope)}"
    if len(line) > CMD_COMMAND_LINE_LIMIT:
        raise Stage0Refused("stage-0 cmd command line exceeds 8191 characters")
    return line


def render_stage0_cmd_payload(*, envelope: object) -> str:
    """Return the verbatim in-memory CreateProcess/cmd payload."""

    return render_stage0_cmd_command_line(envelope=envelope)


def _render_stage0_artifacts(**kwargs: object) -> tuple[bytes, str, str]:
    envelope = render_stage0_envelope(**kwargs)
    cmd_payload = render_stage0_cmd_payload(envelope=envelope)
    command_line_length = len(render_stage0_cmd_command_line(envelope=envelope))
    payload = (
        f"{STAGE0_AUDIT_HEADER}\n"
        "execution_source=renderer_stdout_memory_only\n"
        "record_role=non_executable_audit_evidence\n"
        f"requested_operation={kwargs['command']}\n"
        f"receipt_sha256={kwargs['receipt_sha256']}\n"
        f"native_launcher_sha256={kwargs['launcher_sha256']}\n"
        f"stage0_source_sha256={STAGE0_SOURCE_SHA256}\n"
        f"stage0_encoded_sha256={STAGE0_ENCODED_SHA256}\n"
        f"stage0_environment_policy_sha256={STAGE0_ENVIRONMENT_POLICY_SHA256}\n"
        f"envelope_sha256={hashlib.sha256(envelope.encode('ascii')).hexdigest()}\n"
        f"cmd_command_line_length={command_line_length}\n"
    ).encode("ascii")
    return payload, cmd_payload, envelope


def render_stage0_record(**kwargs: object) -> bytes:
    return _render_stage0_artifacts(**kwargs)[0]


def _create_stage0_record(*, output: object, **kwargs: object) -> tuple[str, str]:
    if type(output) is not str or not output:
        raise Stage0Refused("stage-0 output path is invalid")
    path = Path(output)
    lexical = Path(os.path.abspath(output))
    if not path.is_absolute() or path != lexical:
        raise Stage0Refused("stage-0 output must be absolute and canonical")
    try:
        lexical.relative_to(Path(os.path.abspath(PROJECT_ROOT)))
    except ValueError as exc:
        raise Stage0Refused("stage-0 output is outside the project") from exc
    _plain_directory_chain(lexical.parent, what="stage-0 output")
    payload, cmd_payload, _ = _render_stage0_artifacts(**kwargs)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(lexical, flags, 0o400)
    except FileExistsError as exc:
        raise Stage0Refused("stage-0 output already exists") from exc
    try:
        view = memoryview(payload)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise Stage0Refused("stage-0 output write stopped")
            view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(lexical, stat.S_IREAD)
    if lexical.read_bytes() != payload:
        raise Stage0Refused("stage-0 output verification differs")
    metadata = lexical.stat()
    if os.name == "nt":
        if not int(getattr(metadata, "st_file_attributes", 0)) & _READONLY:
            raise Stage0Refused("stage-0 output is not read-only")
    elif metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise Stage0Refused("stage-0 output is not read-only")
    return hashlib.sha256(payload).hexdigest(), cmd_payload


def create_stage0_record(*, output: object, **kwargs: object) -> str:
    return _create_stage0_record(output=output, **kwargs)[0]


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--policy", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--launcher-path")
    parser.add_argument("--receipt-path")
    parser.add_argument("--launcher-sha256")
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--command", choices=sorted(COMMANDS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _argument_parser()
    args = parser.parse_args(argv)
    if args.policy:
        if any(
            value is not None
            for value in (
                args.output,
                args.launcher_path,
                args.receipt_path,
                args.launcher_sha256,
                args.receipt_sha256,
                args.command,
            )
        ):
            parser.error("--policy accepts no release or command arguments")
        sys.stdout.buffer.write(render_stage0_policy())
        return 0
    missing = [
        name
        for name, value in (
            ("--output", args.output),
            ("--launcher-path", args.launcher_path),
            ("--receipt-path", args.receipt_path),
            ("--launcher-sha256", args.launcher_sha256),
            ("--receipt-sha256", args.receipt_sha256),
            ("--command", args.command),
        )
        if value is None
    ]
    if missing:
        parser.error("the following arguments are required: " + ", ".join(missing))
    try:
        digest, cmd_payload = _create_stage0_record(
            output=args.output,
            launcher_path=args.launcher_path,
            receipt_path=args.receipt_path,
            launcher_sha256=args.launcher_sha256,
            receipt_sha256=args.receipt_sha256,
            command=args.command,
        )
    except (OSError, Stage0Refused) as exc:
        parser.exit(2, f"stage-0 record refused: {exc}\n")
    sys.stdout.write(f"stage0_record_sha256={digest}\n")
    sys.stdout.write(f"stage0_cmd_payload={cmd_payload}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
