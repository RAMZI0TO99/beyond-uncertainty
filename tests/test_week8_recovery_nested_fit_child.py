"""Synthetic/adversarial tests for the D-166 nested fit-child boundary.

Every file and authority object used by these tests is fabricated beneath
``tmp_path``.  The tests load the controller scripts as inert modules and do
not read or mutate Week-8 production evidence, staging, output, or sync trees.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "scripts" / "week8_exp2a_recovery_worker.py"
FIT_CHILD_PATH = ROOT / "scripts" / "week8_exp2a_recovery_fit_child.py"


def _load_script(name: str, path: Path) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


W = _load_script("d166_nested_worker_under_test", WORKER_PATH)
F = _load_script("d166_fit_child_under_test", FIT_CHILD_PATH)


def test_fit_child_raw_authority_config_matches_exact_contract() -> None:
    raw_module = _load_script(
        "d166_fit_child_raw_config_contract",
        ROOT / "scripts" / "week8_recovery_raw_authority.py",
    )
    native_startup = {
        "release_receipt_sha256": "1" * 64,
        "native_launcher": {"sha256": "2" * 64},
        "stage0_binding_sha256": "3" * 64,
        "startup_binding_sha256": "4" * 64,
    }
    config = F._raw_authority_config("a" * 40, native_startup)
    assert set(config) == raw_module._CONFIG_KEYS
    assert config["pinned_local_appdata"] == str(
        Path("C:/Users/aladdin-alyanai/AppData/Local")
    )


def _synthetic_relocation() -> dict[str, Any]:
    return {"relocation_schema_version": 1, "attestation_sha256": "1" * 64,
            "policy_sha256": "2" * 64, "pair_count": 304, "document_count": 629,
            "helpers": {"helper_schema_version": 1, "synthetic": True}}


@pytest.fixture(autouse=True)
def synthetic_worker_relocation_authority(monkeypatch):
    # This module exercises the native child protocol; admission and its fixed
    # evidence reads have separate real-reader/adversarial integration suites.
    monkeypatch.setattr(W, "_admitted_relocation", lambda: (None, None, _synthetic_relocation()))
    monkeypatch.setattr(W, "_admitted_orphan_transition", lambda: {
        "record_digest": "3" * 64, "file_sha256": "4" * 64})
    monkeypatch.setattr(W, "_worker_relocation_readers", lambda launch: nullcontext())


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sealed(value: dict[str, Any]) -> dict[str, Any]:
    document = dict(value)
    document["record_digest"] = _sha(_canonical(document))
    return document


def _fit_protocol_paths(root: Path, token: str = "a" * 64) -> dict[str, Path]:
    return {
        "startup_path": root / f"fit-child-startup-{token}.json",
        "startup_ack_path": root / f"fit-child-startup-ack-{token}.json",
        "result_path": root / f"fit-child-result-{token}.json",
    }


def _invocation_v3(
    root: Path,
    *,
    token: str = "a" * 64,
    attempt_dir: Path | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paths = _fit_protocol_paths(root, token)
    document: dict[str, Any] = {
        "fit_child_invocation_schema_version": 3,
        "record_type": "week8_d161_verified_fit_child_invocation",
        "attempt_dir": str(attempt_dir or (root / "attempt")),
        "payload": {} if payload is None else payload,
        "startup_path": str(paths["startup_path"]),
        "startup_ack_path": str(paths["startup_ack_path"]),
        "result_path": str(paths["result_path"]),
        "entrypoint_gate_digest": "b" * 64,
        "child_bundle_sha256": "c" * 64,
        "relocation": _synthetic_relocation(),
        "orphan_transition": {"record_digest": "3" * 64, "file_sha256": "4" * 64},
    }
    document["invocation_digest"] = _sha(_canonical(document))
    return document


def _startup_hello(
    invocation: dict[str, Any],
    *,
    launcher_pid: int = 4_321,
    fit_pid: int = 8_765,
    owner_pid: int | None = None,
    launcher_creation_time_100ns: int = 11_000,
    fit_creation_time_100ns: int = 22_000,
    launcher_path: Path | None = None,
    fit_path: Path | None = None,
    launcher_sha256: str = "d" * 64,
    fit_sha256: str = "e" * 64,
) -> dict[str, Any]:
    launcher_executable = (launcher_path or Path("C:/synthetic/venv/python.exe")).resolve()
    fit_executable = (fit_path or Path("C:/synthetic/base/python.exe")).resolve()
    return _sealed(
        {
            "fit_child_startup_schema_version": 1,
            "record_type": "week8_d161_fit_child_startup",
            "invocation_digest": invocation["invocation_digest"],
            "launcher": {
                "pid": launcher_pid,
                "parent_pid": os.getpid() if owner_pid is None else owner_pid,
                "creation_time_100ns": launcher_creation_time_100ns,
                "kernel_executable_path": str(launcher_executable),
                "kernel_executable_sha256": launcher_sha256,
            },
            "fit_interpreter": {
                "pid": fit_pid,
                "parent_pid": launcher_pid,
                "creation_time_100ns": fit_creation_time_100ns,
                "kernel_executable_path": str(fit_executable),
                "kernel_executable_sha256": fit_sha256,
            },
        }
    )


def _startup_ack(
    invocation: dict[str, Any], hello: dict[str, Any]
) -> dict[str, Any]:
    launcher = hello["launcher"]
    fit_interpreter = hello["fit_interpreter"]
    return _sealed(
        {
            "fit_child_startup_schema_version": 1,
            "record_type": "week8_d161_fit_child_startup_ack",
            "invocation_digest": invocation["invocation_digest"],
            "startup_record_digest": hello["record_digest"],
            "launcher_creation": {
                "pid": launcher["pid"],
                "creation_time_100ns": launcher["creation_time_100ns"],
            },
            "fit_interpreter_creation": {
                "pid": fit_interpreter["pid"],
                "creation_time_100ns": fit_interpreter["creation_time_100ns"],
            },
        }
    )


class _SyntheticProcessHandle:
    def __init__(
        self,
        pid: int,
        *,
        label: str,
        events: list[str],
        alive: bool = True,
        exitcode: int = 0,
        terminate_stops: bool = True,
    ) -> None:
        self.pid = pid
        self.label = label
        self.events = events
        self.alive = alive
        self._exitcode = None if alive else exitcode
        self.terminal_exitcode = exitcode
        self.terminate_stops = terminate_stops
        self.closed = False

    @property
    def exitcode(self) -> int | None:
        return self._exitcode

    def poll(self) -> int | None:
        return self._exitcode

    def is_alive(self) -> bool:
        return self.alive

    def wait(self, timeout: float | None = None) -> int | None:
        self.events.append(f"wait:{self.label}:{timeout}")
        return self._exitcode

    def join(self, timeout: float | None = None) -> None:
        self.events.append(f"join:{self.label}:{timeout}")

    def terminate(self) -> None:
        self.events.append(f"terminate:{self.label}")
        if self.terminate_stops:
            self.alive = False
            self._exitcode = self.terminal_exitcode

    def kill(self) -> None:
        self.events.append(f"kill:{self.label}")
        self.alive = False
        self._exitcode = self.terminal_exitcode

    def close(self) -> None:
        self.events.append(f"close:{self.label}")
        self.closed = True

    def close(self) -> None:
        self.events.append(f"close:{self.label}")


def _synthetic_child_bundle(tmp_path: Path) -> tuple[bytes, Path, Path]:
    helper_path = tmp_path / "synthetic_raw_helper.py"
    child_path = tmp_path / "synthetic_fit_child.py"
    helper_source = b"CAPTURED_HELPER = True\n"
    child_source = b"print('synthetic-child-ok')\n"
    helper_path.write_bytes(helper_source)
    child_path.write_bytes(child_source)
    payload = {
        "child_transport_schema_version": 1,
        "record_type": "week8_d161_verified_child_bundle",
        "logical_path": str(child_path),
        "script_sha256": _sha(child_source),
        "script_base64": base64.b64encode(child_source).decode("ascii"),
        "raw_helper_path": str(helper_path),
        "raw_helper_sha256": _sha(helper_source),
        "raw_helper_base64": base64.b64encode(helper_source).decode("ascii"),
    }
    payload["record_digest"] = _sha(_canonical(payload))
    return _canonical(payload), helper_path, child_path


def _run_generic_child(bundle: bytes, *, digest: str) -> subprocess.CompletedProcess[bytes]:
    environment = dict(os.environ)
    environment[W.CHILD_BUNDLE_ENVIRONMENT_NAME] = digest
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-X",
            "utf8",
            "-c",
            W.FIT_CHILD_BOOTSTRAP_LITERAL,
        ],
        input=bundle,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )


def test_fixed_generic_child_bootstrap_literal_hash_parity() -> None:
    encoded = W.FIT_CHILD_BOOTSTRAP_LITERAL.encode("utf-8")
    assert _sha(encoded) == W.EXPECTED_CHILD_BOOTSTRAP_LITERAL_SHA256
    assert "pickle" not in W.FIT_CHILD_BOOTSTRAP_LITERAL
    assert "multiprocessing" not in W.FIT_CHILD_BOOTSTRAP_LITERAL


def test_generic_child_bootstrap_accepts_canonical_digest_bound_stdin(
    tmp_path: Path,
) -> None:
    bundle, _helper_path, _child_path = _synthetic_child_bundle(tmp_path)
    completed = _run_generic_child(bundle, digest=_sha(bundle))
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    assert completed.stdout == b"synthetic-child-ok\r\n"


def test_pinned_startup_policy_ignores_shadow_pythonpath_cwd_and_encoding_claims(
    tmp_path: Path,
) -> None:
    shadow = tmp_path / "hostile-import-root"
    shadow.mkdir()
    hashlib_marker = tmp_path / "hashlib-shadow-executed.txt"
    encodings_marker = tmp_path / "encodings-shadow-executed.txt"
    (shadow / "hashlib.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(hashlib_marker)!r}).write_text('executed', encoding='ascii')\n"
        "raise RuntimeError('hostile hashlib shadow executed')\n",
        encoding="utf-8",
    )
    encodings = shadow / "encodings"
    encodings.mkdir()
    (encodings / "__init__.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(encodings_marker)!r}).write_text('executed', encoding='ascii')\n"
        "raise RuntimeError('hostile encodings shadow executed')\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(shadow)
    environment["PYTHONDONTWRITEBYTECODE"] = "0"
    environment["PYTHONIOENCODING"] = "cp1252"
    environment["PYTHONUTF8"] = "0"
    script = (
        "import hashlib,json,sys\n"
        "print(json.dumps({'hashlib':hashlib.__file__,'path':sys.path,"
        "'isolated':sys.flags.isolated,'ignore_environment':sys.flags.ignore_environment,"
        "'no_site':sys.flags.no_site,'no_user_site':sys.flags.no_user_site,"
        "'safe_path':sys.flags.safe_path,'dont_write_bytecode':sys.flags.dont_write_bytecode,"
        "'utf8_mode':sys.flags.utf8_mode,'stdout_encoding':sys.stdout.encoding},sort_keys=True))\n"
    )
    completed = subprocess.run(
        [
            str(W.PINNED_PYTHON),
            "-I",
            "-S",
            "-B",
            "-X",
            "utf8",
            "-c",
            script,
        ],
        cwd=shadow,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout)
    assert observed["isolated"] == 1
    assert observed["ignore_environment"] == 1
    assert observed["no_site"] == 1
    assert observed["no_user_site"] == 1
    assert observed["safe_path"] == 1
    assert observed["dont_write_bytecode"] == 1
    assert observed["utf8_mode"] == 1
    assert observed["stdout_encoding"].replace("-", "").lower() == "utf8"
    assert str(shadow.resolve()).casefold() not in {
        str(Path(value).resolve()).casefold() for value in observed["path"]
    }
    assert Path(observed["hashlib"]).resolve() != (shadow / "hashlib.py").resolve()
    assert not hashlib_marker.exists()
    assert not encodings_marker.exists()


def test_fit_child_accepts_exact_preimport_startup_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flags = SimpleNamespace(
        dont_write_bytecode=1,
        ignore_environment=1,
        isolated=1,
        no_site=1,
        no_user_site=1,
        safe_path=1,
        utf8_mode=1,
    )
    monkeypatch.setattr(F, "sys", SimpleNamespace(flags=flags))
    F._validate_isolated_runtime()


@pytest.mark.parametrize(
    "missing_flag",
    [
        "dont_write_bytecode",
        "ignore_environment",
        "isolated",
        "no_site",
        "no_user_site",
        "safe_path",
        "utf8_mode",
    ],
)
def test_fit_child_refuses_each_missing_preimport_startup_flag(
    monkeypatch: pytest.MonkeyPatch,
    missing_flag: str,
) -> None:
    values = {
        "dont_write_bytecode": 1,
        "ignore_environment": 1,
        "isolated": 1,
        "no_site": 1,
        "no_user_site": 1,
        "safe_path": 1,
        "utf8_mode": 1,
    }
    values[missing_flag] = 0
    monkeypatch.setattr(F, "sys", SimpleNamespace(flags=SimpleNamespace(**values)))
    with pytest.raises(F.FitChildRefused, match="-I -S -B -X utf8"):
        F._validate_isolated_runtime()


@pytest.mark.parametrize(
    "tamper",
    ["transport_digest", "noncanonical", "record_digest", "script_digest"],
)
def test_generic_child_bootstrap_rejects_unbound_or_noncanonical_stdin(
    tmp_path: Path, tamper: str
) -> None:
    bundle, _helper_path, _child_path = _synthetic_child_bundle(tmp_path)
    digest = _sha(bundle)
    if tamper == "transport_digest":
        digest = "0" * 64
    elif tamper == "noncanonical":
        bundle = b" " + bundle
        digest = _sha(bundle)
    else:
        document = json.loads(bundle.decode("ascii"))
        if tamper == "record_digest":
            document["record_digest"] = "0" * 64
        else:
            document["script_sha256"] = "0" * 64
            unsealed = {key: value for key, value in document.items() if key != "record_digest"}
            document["record_digest"] = _sha(_canonical(unsealed))
        bundle = _canonical(document)
        digest = _sha(bundle)

    completed = _run_generic_child(bundle, digest=digest)
    assert completed.returncode != 0
    assert completed.stdout == b""


def test_fit_child_rejects_noncanonical_invocation_json_before_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path.resolve()
    monkeypatch.setattr(F, "RUNTIME_TEMP", runtime)
    document = _invocation_v3(runtime)
    encoded = json.dumps(document, sort_keys=False, indent=1).encode("ascii")
    monkeypatch.setenv(
        F.INVOCATION_BASE64_ENVIRONMENT_NAME,
        base64.b64encode(encoded).decode("ascii"),
    )
    monkeypatch.setenv(F.INVOCATION_SHA256_ENVIRONMENT_NAME, _sha(encoded))
    with pytest.raises(F.FitChildRefused, match="not canonical"):
        F._decode_invocation()


def test_fit_child_accepts_exact_schema_v2_startup_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "runtime"
    staging = tmp_path / "staging"
    attempt = staging / "job.synthetic"
    runtime.mkdir()
    attempt.mkdir(parents=True)
    invocation = _invocation_v3(runtime, attempt_dir=attempt, payload={"seed": 1000})
    encoded = _canonical(invocation)
    monkeypatch.setattr(F, "RUNTIME_TEMP", runtime)
    monkeypatch.setattr(F, "STAGING_ATTEMPT_ROOT", staging)
    monkeypatch.setenv(
        F.INVOCATION_BASE64_ENVIRONMENT_NAME,
        base64.b64encode(encoded).decode("ascii"),
    )
    monkeypatch.setenv(F.INVOCATION_SHA256_ENVIRONMENT_NAME, _sha(encoded))

    decoded, result_path, startup_path, startup_ack_path = F._decode_invocation()
    validated_attempt, payload = F._validate_invocation(decoded)

    paths = _fit_protocol_paths(runtime)
    assert decoded == invocation
    assert result_path == paths["result_path"]
    assert startup_path == paths["startup_path"]
    assert startup_ack_path == paths["startup_ack_path"]
    assert validated_attempt == attempt
    assert payload == {"seed": 1000}


@pytest.mark.parametrize("field", ["startup_path", "startup_ack_path", "result_path"])
def test_fit_child_refuses_schema_v2_protocol_path_with_a_different_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    runtime = tmp_path / "runtime"
    staging = tmp_path / "staging"
    attempt = staging / "job.synthetic"
    runtime.mkdir()
    attempt.mkdir(parents=True)
    invocation = _invocation_v3(runtime, attempt_dir=attempt)
    prefix = {
        "startup_path": "fit-child-startup-",
        "startup_ack_path": "fit-child-startup-ack-",
        "result_path": "fit-child-result-",
    }[field]
    invocation[field] = str(runtime / f"{prefix}{'f' * 64}.json")
    unsealed = {key: value for key, value in invocation.items() if key != "invocation_digest"}
    invocation["invocation_digest"] = _sha(_canonical(unsealed))
    encoded = _canonical(invocation)
    monkeypatch.setattr(F, "RUNTIME_TEMP", runtime)
    monkeypatch.setattr(F, "STAGING_ATTEMPT_ROOT", staging)
    monkeypatch.setenv(
        F.INVOCATION_BASE64_ENVIRONMENT_NAME,
        base64.b64encode(encoded).decode("ascii"),
    )
    monkeypatch.setenv(F.INVOCATION_SHA256_ENVIRONMENT_NAME, _sha(encoded))

    with pytest.raises(F.FitChildRefused, match="token|protocol|path"):
        F._decode_invocation()


def _fit_child_control_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invocation: dict[str, Any],
) -> list[tuple[str, str]]:
    runtime = tmp_path / "runtime"
    execution = tmp_path / "execution"
    runtime.mkdir()
    execution.mkdir()
    monkeypatch.setattr(F, "RUNTIME_TEMP", runtime)
    monkeypatch.setattr(F, "EXECUTION_WORKTREE", execution)
    gate_text = '{"synthetic":"gate"}'
    bundle_sha = "e" * 64
    invocation_bytes = _canonical(invocation)
    monkeypatch.setenv(F.ENTRYPOINT_GATE_ENVIRONMENT_NAME, gate_text)
    monkeypatch.setenv(F.CHILD_BUNDLE_ENVIRONMENT_NAME, bundle_sha)
    return [
        ("CUDA_VISIBLE_DEVICES", "-1"),
        ("HIP_VISIBLE_DEVICES", "-1"),
        ("OMP_NUM_THREADS", "4"),
        ("MKL_NUM_THREADS", "4"),
        ("OPENBLAS_NUM_THREADS", "4"),
        ("NUMEXPR_NUM_THREADS", "4"),
        ("TEMP", str(runtime.resolve())),
        ("TMP", str(runtime.resolve())),
        ("TMPDIR", str(runtime.resolve())),
        ("PYTHONHASHSEED", "0"),
        ("PYTHONDONTWRITEBYTECODE", "1"),
        ("PYTHONIOENCODING", "utf-8"),
        ("PYTHONNOUSERSITE", "1"),
        ("PYTHONSAFEPATH", "1"),
        ("PYTHONUTF8", "1"),
        ("GIT_CONFIG_COUNT", "1"),
        ("GIT_CONFIG_GLOBAL", os.devnull),
        ("GIT_CONFIG_KEY_0", "safe.directory"),
        ("GIT_CONFIG_NOSYSTEM", "1"),
        ("GIT_CONFIG_VALUE_0", str(execution.resolve())),
        ("GIT_NO_REPLACE_OBJECTS", "1"),
        ("GIT_OPTIONAL_LOCKS", "0"),
        ("GIT_PAGER", ""),
        ("GIT_TERMINAL_PROMPT", "0"),
        (F.ENTRYPOINT_GATE_ENVIRONMENT_NAME, gate_text),
        (F.CHILD_BUNDLE_ENVIRONMENT_NAME, bundle_sha),
        (
            F.INVOCATION_BASE64_ENVIRONMENT_NAME,
            base64.b64encode(invocation_bytes).decode("ascii"),
        ),
        (F.INVOCATION_SHA256_ENVIRONMENT_NAME, _sha(invocation_bytes)),
    ]


def test_fit_child_requires_exact_control_environment_and_refuses_extra_bu(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = {"synthetic": "canonical"}
    rows = _fit_child_control_rows(tmp_path, monkeypatch, invocation)
    raw_module = SimpleNamespace(exact_environment_items=lambda: tuple(rows))
    F._validate_control_environment(raw_module, invocation)
    raw_module.exact_environment_items = lambda: tuple(
        [*rows, ("BU_D161_UNAPPROVED", "1")]
    )
    with pytest.raises(F.FitChildRefused, match="unapproved D-161 control"):
        F._validate_control_environment(raw_module, invocation)


def test_fit_boundary_has_no_pickle_or_native_process_constructor() -> None:
    worker_tree: ast.Module | None = None
    for path in (WORKER_PATH, FIT_CHILD_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if path == WORKER_PATH:
            worker_tree = tree
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "pickle" not in imported
    assert worker_tree is not None
    process_class = next(
        node
        for node in worker_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "_VerifiedFitProcess"
    )
    start_method = next(
        node
        for node in process_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "start"
    )
    called_names = {
        node.func.attr
        for node in ast.walk(start_method)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    popen_calls = [
        node
        for node in ast.walk(start_method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Popen"
    ]
    assert "Popen" in called_names
    assert len(popen_calls) == 1
    assert "Process" not in called_names
    assert "get_context" not in called_names
    worker_source = WORKER_PATH.read_text(encoding="utf-8")
    assert "taskkill" not in worker_source.lower()


def _fit_process_parts(tmp_path: Path) -> tuple[Any, Any, Any, tuple[object, ...]]:
    def spawn_worker(*args: object) -> None:
        del args

    def fit_worker(*args: object) -> None:
        del args

    paths = _fit_protocol_paths(tmp_path)
    send = W._VerifiedFitSend(paths["result_path"])
    context = SimpleNamespace(
        supervisor=SimpleNamespace(_spawn_worker=spawn_worker),
        launch=SimpleNamespace(_fit_worker=fit_worker),
        pending_send=send,
        startup_path=paths["startup_path"],
        startup_ack_path=paths["startup_ack_path"],
        pending_startup_receive=W._VerifiedFitReceive(paths["startup_path"]),
        pending_startup_ack=W._VerifiedFitSend(paths["startup_ack_path"]),
        authority={
            "pinned_python": {
                "path": str(Path("C:/synthetic/venv/python.exe").resolve()),
                "sha256": "d" * 64,
            },
            "base_python": {
                "path": str(Path("C:/synthetic/base/python.exe").resolve()),
                "sha256": "e" * 64,
            },
        },
    )
    args = (fit_worker, str(tmp_path / "attempt"), {"seed": 1000}, send)
    return context, spawn_worker, fit_worker, args


def _bind_synthetic_dual_process(
    process: Any,
    *,
    launcher: _SyntheticProcessHandle,
    fit_interpreter: _SyntheticProcessHandle,
) -> None:
    # These aliases keep the test focused on the Process API rather than one
    # private spelling for the two retained Windows process objects.
    process._process = launcher
    process._launcher = launcher
    process._launcher_process = launcher
    process._launcher_handle = launcher
    process._fit_process = fit_interpreter
    process._fit_interpreter = fit_interpreter
    process._fit_interpreter_process = fit_interpreter
    process._fit_handle = fit_interpreter
    process._fit_pid = fit_interpreter.pid
    process._started = True
    process._startup_complete = True


def test_verified_fit_process_enforces_exact_target_callback_and_arguments(
    tmp_path: Path,
) -> None:
    context, spawn_worker, fit_worker, args = _fit_process_parts(tmp_path)
    valid = W._VerifiedFitProcess(
        context=context,
        target=spawn_worker,
        args=args,
        name="bu-job-synthetic",
    )
    assert valid.attempt_dir == args[1]
    assert valid.payload is args[2]

    bad_cases = [
        (object(), args, "bu-job-synthetic"),
        (spawn_worker, (object(), *args[1:]), "bu-job-synthetic"),
        (spawn_worker, (fit_worker, Path(args[1]), args[2], args[3]), "bu-job-synthetic"),
        (spawn_worker, (fit_worker, args[1], SimpleNamespace(), args[3]), "bu-job-synthetic"),
        (spawn_worker, (*args[:3], object()), "bu-job-synthetic"),
        (spawn_worker, args, "other-name"),
        (spawn_worker, args[:-1], "bu-job-synthetic"),
    ]
    for target, observed_args, name in bad_cases:
        with pytest.raises(W.BootstrapRefused):
            W._VerifiedFitProcess(
                context=context,
                target=target,
                args=observed_args,
                name=name,
            )


def test_verified_fit_context_is_irrevocably_one_shot_after_pipe_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def spawn_worker(*args: object) -> None:
        del args

    def fit_worker(*args: object) -> None:
        del args

    bundle = b'{"synthetic":"bundle"}'
    monkeypatch.setattr(W, "RUNTIME_TEMP", tmp_path)
    monkeypatch.setattr(W, "_fit_child_bundle", lambda authority: (bundle, _sha(bundle)))
    context = W._VerifiedFitContext(
        authority={},
        gate={"record_digest": "b" * 64},
        launch=SimpleNamespace(_fit_worker=fit_worker),
        supervisor=SimpleNamespace(_spawn_worker=spawn_worker),
    )

    receive, send = context.Pipe(duplex=False)
    receive.close()
    send.close()

    with pytest.raises(W.BootstrapRefused, match="one|retry|used|initialized"):
        context.Pipe(duplex=False)


def test_verified_fit_process_liveness_and_exitcode_cover_both_owned_processes(
    tmp_path: Path,
) -> None:
    context, spawn_worker, _fit_worker, args = _fit_process_parts(tmp_path)

    def bound(
        *, launcher_alive: bool, fit_alive: bool, launcher_code: int, fit_code: int
    ) -> Any:
        events: list[str] = []
        process = W._VerifiedFitProcess(
            context=context,
            target=spawn_worker,
            args=args,
            name="bu-job-synthetic",
        )
        launcher = _SyntheticProcessHandle(
            4_321,
            label="launcher",
            events=events,
            alive=launcher_alive,
            exitcode=launcher_code,
        )
        fit_interpreter = _SyntheticProcessHandle(
            8_765,
            label="fit",
            events=events,
            alive=fit_alive,
            exitcode=fit_code,
        )
        _bind_synthetic_dual_process(
            process, launcher=launcher, fit_interpreter=fit_interpreter
        )
        return process

    launcher_dead = bound(
        launcher_alive=False, fit_alive=True, launcher_code=0, fit_code=7
    )
    assert launcher_dead.pid == 8_765
    assert launcher_dead.is_alive() is True
    assert launcher_dead.exitcode is None

    fit_dead = bound(
        launcher_alive=True, fit_alive=False, launcher_code=0, fit_code=7
    )
    assert fit_dead.pid == 8_765
    assert fit_dead.is_alive() is True
    assert fit_dead.exitcode is None

    both_dead = bound(
        launcher_alive=False, fit_alive=False, launcher_code=0, fit_code=7
    )
    assert both_dead.is_alive() is False
    assert both_dead.exitcode == 7


def test_verified_fit_process_uses_retained_handles_without_reopening_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, spawn_worker, _fit_worker, args = _fit_process_parts(tmp_path)
    process = W._VerifiedFitProcess(
        context=context,
        target=spawn_worker,
        args=args,
        name="bu-job-synthetic",
    )
    events: list[str] = []
    launcher = _SyntheticProcessHandle(
        4_321,
        label="launcher",
        events=events,
        alive=True,
        exitcode=1,
        terminate_stops=False,
    )
    fit_interpreter = _SyntheticProcessHandle(
        8_765,
        label="fit",
        events=events,
        alive=True,
        exitcode=1,
        terminate_stops=False,
    )
    _bind_synthetic_dual_process(
        process, launcher=launcher, fit_interpreter=fit_interpreter
    )

    def reopened(pid: int) -> dict[str, Any]:
        raise AssertionError(f"lifecycle reopened PID {pid} after startup binding")

    monkeypatch.setattr(W, "_windows_process_identity", reopened)
    monkeypatch.setattr(
        W,
        "_open_windows_process_handle",
        lambda pid: (_ for _ in ()).throw(
            AssertionError(f"lifecycle reopened PID {pid} after startup binding")
        ),
        raising=False,
    )
    monkeypatch.setattr(
        W,
        "_open_owned_windows_process",
        lambda pid: (_ for _ in ()).throw(
            AssertionError(f"lifecycle reopened PID {pid} after startup binding")
        ),
        raising=False,
    )

    process.terminate()
    assert events[:2] == ["terminate:fit", "terminate:launcher"]
    assert process.is_alive() is True

    process.kill()
    assert events[2:4] == ["kill:fit", "kill:launcher"]
    process.join(0.05)
    assert any(item.startswith(("wait:fit:", "join:fit:")) for item in events)
    assert any(
        item.startswith(("wait:launcher:", "join:launcher:")) for item in events
    )
    assert process.is_alive() is False
    assert process.exitcode == 1


def test_verified_fit_process_uses_only_pinned_isolated_literal_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, spawn_worker, _fit_worker, args = _fit_process_parts(tmp_path)
    bundle = b'{"synthetic":"bundle"}'
    context.bundle = bundle
    context.bundle_sha256 = _sha(bundle)
    context.gate = {"record_digest": "b" * 64}
    protocol_paths = _fit_protocol_paths(tmp_path, "c" * 64)
    context.pending_send.path = protocol_paths["result_path"]
    context.startup_path = protocol_paths["startup_path"]
    context.startup_ack_path = protocol_paths["startup_ack_path"]
    context.pending_startup_receive.path = protocol_paths["startup_path"]
    context.pending_startup_ack.path = protocol_paths["startup_ack_path"]
    pinned_python = tmp_path / "pinned-python.exe"
    base_python = tmp_path / "base-python.exe"
    pinned_python.write_bytes(b"synthetic pinned launcher")
    base_python.write_bytes(b"synthetic base interpreter")
    pinned_sha = _sha(pinned_python.read_bytes())
    base_sha = _sha(base_python.read_bytes())
    context.authority = {
        "pinned_python": {"path": str(pinned_python.resolve()), "sha256": pinned_sha},
        "base_python": {"path": str(base_python.resolve()), "sha256": base_sha},
    }
    execution = tmp_path / "execution"
    execution.mkdir()
    monkeypatch.setattr(W, "PINNED_PYTHON", pinned_python)
    monkeypatch.setattr(W, "PINNED_BASE_PYTHON", base_python)
    monkeypatch.setattr(W, "EXECUTION_WORKTREE", execution)
    monkeypatch.setattr(W, "RUNTIME_TEMP", tmp_path)
    monkeypatch.setattr(W, "FIT_CHILD_STARTUP_TIMEOUT_SECONDS", 0.1, raising=False)

    class InputSink:
        def __init__(self) -> None:
            self.data = b""
            self.closed = False

        def write(self, value: bytes) -> int:
            self.data += value
            return len(value)

        def close(self) -> None:
            self.closed = True

    class FakeProcess:
        def __init__(self) -> None:
            self.stdin = InputSink()
            self.pid = 4321
            self.killed = False

        def poll(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 0

        def kill(self) -> None:
            self.killed = True

        def terminate(self) -> None:
            return None

    observed: dict[str, Any] = {}
    fake = FakeProcess()
    launcher_handle = _SyntheticProcessHandle(
        4_321, label="launcher", events=[], alive=True, exitcode=0
    )
    fit_handle = _SyntheticProcessHandle(
        8_765, label="fit", events=[], alive=True, exitcode=0
    )
    launcher_handle.identity = {
        "pid": 4_321,
        "parent_pid": os.getpid(),
        "kernel_executable_path": str(pinned_python.resolve()),
        "kernel_executable_sha256": pinned_sha,
        "creation_time_100ns": 11_000,
    }
    fit_handle.identity = {
        "pid": 8_765,
        "parent_pid": 4_321,
        "kernel_executable_path": str(base_python.resolve()),
        "kernel_executable_sha256": base_sha,
        "creation_time_100ns": 22_000,
    }

    launcher_identity = dict(launcher_handle.identity)
    fit_identity = dict(fit_handle.identity)

    def process_identity(pid: int) -> dict[str, Any]:
        if pid == 4_321:
            return dict(launcher_identity)
        if pid == 8_765:
            return dict(fit_identity)
        raise AssertionError(f"unexpected process identity query for {pid}")

    def parent_pid(pid: int) -> int:
        if pid == 4_321:
            return os.getpid()
        if pid == 8_765:
            return 4_321
        raise AssertionError(f"unexpected parent query for {pid}")

    monkeypatch.setattr(W, "_windows_process_identity", process_identity)
    monkeypatch.setattr(W, "_windows_parent_pid", parent_pid)
    monkeypatch.setattr(W, "_windows_child_pids", lambda pid: [8_765])
    owned_handles = {4_321: launcher_handle, 8_765: fit_handle}
    monkeypatch.setattr(
        W, "_open_windows_process_handle", lambda pid: owned_handles[pid], raising=False
    )
    monkeypatch.setattr(
        W, "_open_owned_windows_process", lambda pid: owned_handles[pid], raising=False
    )

    def popen(command: list[str], **kwargs: object) -> FakeProcess:
        observed["command"] = command
        observed["kwargs"] = kwargs
        environment = kwargs["env"]
        encoded = environment[W.FIT_CHILD_INVOCATION_ENVIRONMENT_NAME]
        invocation = json.loads(
            base64.b64decode(encoded.encode("ascii"), validate=True).decode("ascii")
        )
        observed["invocation"] = invocation
        if "startup_path" in invocation and "startup_ack_path" in invocation:
            hello = _startup_hello(
                invocation,
                launcher_path=pinned_python,
                fit_path=base_python,
                launcher_sha256=pinned_sha,
                fit_sha256=base_sha,
            )
            Path(invocation["startup_path"]).write_bytes(_canonical(hello))
        return fake

    monkeypatch.setattr(W.subprocess, "Popen", popen)
    process = W._VerifiedFitProcess(
        context=context,
        target=spawn_worker,
        args=args,
        name="bu-job-synthetic",
    )
    process.start()

    assert observed["command"] == [
        str(pinned_python),
        "-I",
        "-S",
        "-B",
        "-X",
        "utf8",
        "-c",
        W.FIT_CHILD_BOOTSTRAP_LITERAL,
    ]
    assert str(W.FIT_CHILD_SCRIPT) not in observed["command"]
    assert not any(str(item).endswith(".py") for item in observed["command"][1:])
    assert observed["kwargs"]["cwd"] == execution
    assert observed["kwargs"]["stdin"] is subprocess.PIPE
    assert fake.stdin.data == bundle
    assert fake.stdin.closed is True

    environment = observed["kwargs"]["env"]
    encoded = environment[W.FIT_CHILD_INVOCATION_ENVIRONMENT_NAME]
    invocation_bytes = base64.b64decode(encoded.encode("ascii"), validate=True)
    assert base64.b64encode(invocation_bytes).decode("ascii") == encoded
    assert _sha(invocation_bytes) == environment[
        W.FIT_CHILD_INVOCATION_DIGEST_ENVIRONMENT_NAME
    ]
    invocation = json.loads(invocation_bytes.decode("ascii"))
    assert invocation_bytes == _canonical(invocation)
    assert invocation["fit_child_invocation_schema_version"] == 3
    assert invocation["relocation"] == _synthetic_relocation()
    assert invocation["orphan_transition"] == {"record_digest": "3" * 64, "file_sha256": "4" * 64}
    assert invocation["startup_path"] == str(protocol_paths["startup_path"])
    assert invocation["startup_ack_path"] == str(protocol_paths["startup_ack_path"])
    assert invocation["result_path"] == str(protocol_paths["result_path"])
    assert invocation["entrypoint_gate_digest"] == "b" * 64
    assert invocation["child_bundle_sha256"] == _sha(bundle)
    assert process.pid == 8_765
    assert process.pid != fake.pid

    ack_bytes = protocol_paths["startup_ack_path"].read_bytes()
    ack = json.loads(ack_bytes.decode("ascii"))
    hello = json.loads(protocol_paths["startup_path"].read_text(encoding="ascii"))
    assert ack_bytes == _canonical(ack)
    assert ack == _startup_ack(invocation, hello)


@pytest.mark.parametrize(
    "tamper",
    ["partial", "noncanonical", "wrong_digest", "extra_field"],
)
def test_verified_fit_process_refuses_malformed_startup_hello_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    context, spawn_worker, _fit_worker, args = _fit_process_parts(tmp_path)
    context.bundle = b'{"synthetic":"bundle"}'
    context.bundle_sha256 = _sha(context.bundle)
    context.gate = {"record_digest": "b" * 64}
    monkeypatch.setattr(W, "EXECUTION_WORKTREE", tmp_path)
    monkeypatch.setattr(W, "FIT_CHILD_STARTUP_TIMEOUT_SECONDS", 0.01, raising=False)
    launch_count = 0

    class InputSink:
        def write(self, value: bytes) -> int:
            return len(value)

        def close(self) -> None:
            return None

    class FakeLauncher:
        pid = 4_321
        stdin = InputSink()

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 0

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            return None

    def popen(command: list[str], **kwargs: object) -> FakeLauncher:
        nonlocal launch_count
        del command
        launch_count += 1
        environment = kwargs["env"]
        encoded = environment[W.FIT_CHILD_INVOCATION_ENVIRONMENT_NAME]
        invocation = json.loads(
            base64.b64decode(encoded.encode("ascii"), validate=True).decode("ascii")
        )
        hello = _startup_hello(invocation)
        if tamper == "partial":
            raw = b'{"fit_child_startup_schema_version":'
        elif tamper == "noncanonical":
            raw = b" " + _canonical(hello)
        else:
            if tamper == "wrong_digest":
                hello["record_digest"] = "0" * 64
            else:
                hello["unexpected"] = True
                unsealed = {
                    key: value for key, value in hello.items() if key != "record_digest"
                }
                hello["record_digest"] = _sha(_canonical(unsealed))
            raw = _canonical(hello)
        context.startup_path.write_bytes(raw)
        return FakeLauncher()

    monkeypatch.setattr(W.subprocess, "Popen", popen)
    process = W._VerifiedFitProcess(
        context=context,
        target=spawn_worker,
        args=args,
        name="bu-job-synthetic",
    )

    with pytest.raises(W.BootstrapRefused):
        process.start()
    assert launch_count == 1
    assert not context.startup_ack_path.exists()


def test_verified_fit_process_refuses_linked_startup_hello_without_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, spawn_worker, _fit_worker, args = _fit_process_parts(tmp_path)
    context.bundle = b'{"synthetic":"bundle"}'
    context.bundle_sha256 = _sha(context.bundle)
    context.gate = {"record_digest": "b" * 64}
    monkeypatch.setattr(W, "EXECUTION_WORKTREE", tmp_path)
    monkeypatch.setattr(W, "FIT_CHILD_STARTUP_TIMEOUT_SECONDS", 0.01, raising=False)
    backing = tmp_path / "startup-backing.json"
    events: list[str] = []
    launcher_handle = _SyntheticProcessHandle(
        4_321, label="launcher", events=events, alive=True, exitcode=1
    )
    fit_handle = _SyntheticProcessHandle(
        8_765, label="fit", events=events, alive=True, exitcode=1
    )
    launcher_handle.identity = {
        "pid": 4_321,
        "parent_pid": os.getpid(),
        "creation_time_100ns": 11_000,
        "kernel_executable_path": context.authority["pinned_python"]["path"],
        "kernel_executable_sha256": context.authority["pinned_python"]["sha256"],
    }
    fit_handle.identity = {
        "pid": 8_765,
        "parent_pid": 4_321,
        "creation_time_100ns": 22_000,
        "kernel_executable_path": context.authority["base_python"]["path"],
        "kernel_executable_sha256": context.authority["base_python"]["sha256"],
    }
    monkeypatch.setattr(W, "_windows_child_pids", lambda pid: [8_765])
    monkeypatch.setattr(
        W,
        "_open_owned_windows_process",
        lambda pid: {4_321: launcher_handle, 8_765: fit_handle}[pid],
    )

    class InputSink:
        def write(self, value: bytes) -> int:
            return len(value)

        def close(self) -> None:
            return None

    class FakeLauncher:
        pid = 4_321
        stdin = InputSink()

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 0

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            return None

    def popen(command: list[str], **kwargs: object) -> FakeLauncher:
        del command
        environment = kwargs["env"]
        encoded = environment[W.FIT_CHILD_INVOCATION_ENVIRONMENT_NAME]
        invocation = json.loads(
            base64.b64decode(encoded.encode("ascii"), validate=True).decode("ascii")
        )
        backing.write_bytes(_canonical(_startup_hello(invocation)))
        try:
            os.link(backing, context.startup_path)
        except OSError as exc:  # pragma: no cover - host filesystem capability
            pytest.skip(f"hard links unavailable on test filesystem: {exc}")
        return FakeLauncher()

    monkeypatch.setattr(W.subprocess, "Popen", popen)
    process = W._VerifiedFitProcess(
        context=context,
        target=spawn_worker,
        args=args,
        name="bu-job-synthetic",
    )

    with pytest.raises(W.BootstrapRefused, match="linked|startup"):
        process.start()
    assert backing.exists() and context.startup_path.exists()
    assert not context.startup_ack_path.exists()


@pytest.mark.skipif(os.name != "nt", reason="retained process handles require Windows")
def test_real_distinct_venv_launcher_and_base_child_are_both_reaped_pre_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, spawn_worker, _fit_worker, args = _fit_process_parts(tmp_path)
    paths = _fit_protocol_paths(tmp_path, "9" * 64)
    context.pending_send.path = paths["result_path"]
    context.startup_path = paths["startup_path"]
    context.startup_ack_path = paths["startup_ack_path"]
    context.bundle = b'{"synthetic":"bundle"}'
    context.bundle_sha256 = _sha(context.bundle)
    context.gate = {"record_digest": "b" * 64}
    context.authority = {
        "pinned_python": {
            "path": str(W.PINNED_PYTHON.resolve(strict=True)),
            "sha256": W._sha_file(W.PINNED_PYTHON),
        },
        "base_python": {
            "path": str(W.PINNED_BASE_PYTHON.resolve(strict=True)),
            "sha256": W._sha_file(W.PINNED_BASE_PYTHON),
        },
    }
    observed_pids = tmp_path / "distinct-processes.json"
    child_script = (
        "import base64,json,os,pathlib,time\n"
        f"p=pathlib.Path({str(observed_pids)!r})\n"
        "p.write_text(json.dumps({'fit_pid':os.getpid(),'launcher_pid':os.getppid()}),"
        "encoding='ascii')\n"
        f"i=json.loads(base64.b64decode(os.environ[{W.FIT_CHILD_INVOCATION_ENVIRONMENT_NAME!r}]).decode('ascii'))\n"
        "pathlib.Path(i['startup_path']).write_bytes(b'{')\n"
        "time.sleep(300)\n"
    )
    monkeypatch.setattr(W, "RUNTIME_TEMP", tmp_path)
    monkeypatch.setattr(W, "FIT_CHILD_BOOTSTRAP_LITERAL", child_script)
    monkeypatch.setattr(W, "FIT_CHILD_STARTUP_TIMEOUT_SECONDS", 10.0)
    process = W._VerifiedFitProcess(
        context=context,
        target=spawn_worker,
        args=args,
        name="bu-job-real-preack-cleanup",
    )

    with pytest.raises(W.BootstrapRefused, match="strict JSON|startup"):
        process.start()

    identities = json.loads(observed_pids.read_text(encoding="ascii"))
    assert identities["launcher_pid"] != identities["fit_pid"]
    assert process._launcher_handle is None
    assert process._fit_handle is None
    assert process.pid is None
    assert not paths["startup_ack_path"].exists()
    for pid in (identities["fit_pid"], identities["launcher_pid"]):
        with pytest.raises(W.BootstrapRefused):
            W._windows_process_identity(pid)


@pytest.mark.parametrize(
    "tamper",
    [
        "launcher_pid",
        "launcher_parent",
        "launcher_creation",
        "launcher_path",
        "launcher_hash",
        "fit_pid_equals_launcher",
        "fit_parent",
        "fit_creation",
        "fit_path",
        "fit_hash",
    ],
)
def test_verified_fit_process_refuses_unbound_startup_identity_without_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    context, spawn_worker, _fit_worker, args = _fit_process_parts(tmp_path)
    context.bundle = b'{"synthetic":"bundle"}'
    context.bundle_sha256 = _sha(context.bundle)
    context.gate = {"record_digest": "b" * 64}
    pinned_python = tmp_path / "pinned-python.exe"
    base_python = tmp_path / "base-python.exe"
    pinned_python.write_bytes(b"synthetic pinned launcher")
    base_python.write_bytes(b"synthetic base interpreter")
    pinned_sha = _sha(pinned_python.read_bytes())
    base_sha = _sha(base_python.read_bytes())
    context.authority = {
        "pinned_python": {"path": str(pinned_python.resolve()), "sha256": pinned_sha},
        "base_python": {"path": str(base_python.resolve()), "sha256": base_sha},
    }
    monkeypatch.setattr(W, "PINNED_PYTHON", pinned_python)
    monkeypatch.setattr(W, "PINNED_BASE_PYTHON", base_python)
    monkeypatch.setattr(W, "EXECUTION_WORKTREE", tmp_path)
    monkeypatch.setattr(W, "FIT_CHILD_STARTUP_TIMEOUT_SECONDS", 0.01, raising=False)
    events: list[str] = []
    launcher_handle = _SyntheticProcessHandle(
        4_321, label="launcher", events=events, alive=True, exitcode=1
    )
    fit_handle = _SyntheticProcessHandle(
        8_765, label="fit", events=events, alive=True, exitcode=1
    )
    launcher_handle.identity = {
        "pid": 4_321,
        "kernel_executable_path": str(pinned_python.resolve()),
        "creation_time_100ns": 11_000,
    }
    fit_handle.identity = {
        "pid": 8_765,
        "kernel_executable_path": str(base_python.resolve()),
        "creation_time_100ns": 22_000,
    }
    owned_handles = {4_321: launcher_handle, 8_765: fit_handle}
    monkeypatch.setattr(
        W, "_open_windows_process_handle", lambda pid: owned_handles[pid], raising=False
    )
    monkeypatch.setattr(
        W, "_open_owned_windows_process", lambda pid: owned_handles[pid], raising=False
    )

    def observed_identity(pid: int) -> dict[str, Any]:
        handle = owned_handles.get(pid)
        if handle is None:
            raise W.BootstrapRefused("synthetic startup PID is not owned")
        return dict(handle.identity)

    monkeypatch.setattr(
        W,
        "_windows_process_identity",
        observed_identity,
    )
    monkeypatch.setattr(
        W,
        "_windows_parent_pid",
        lambda pid: os.getpid() if pid == 4_321 else 4_321,
    )
    launch_count = 0

    class InputSink:
        def write(self, value: bytes) -> int:
            return len(value)

        def close(self) -> None:
            return None

    class FakeLauncher:
        pid = 4_321
        stdin = InputSink()
        alive = True

        def poll(self) -> int | None:
            return None if self.alive else 1

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 1

        def terminate(self) -> None:
            self.alive = False
            events.append("terminate:popen-launcher")

        def kill(self) -> None:
            self.alive = False
            events.append("kill:popen-launcher")

    def popen(command: list[str], **kwargs: object) -> FakeLauncher:
        nonlocal launch_count
        del command
        launch_count += 1
        environment = kwargs["env"]
        encoded = environment[W.FIT_CHILD_INVOCATION_ENVIRONMENT_NAME]
        invocation = json.loads(
            base64.b64decode(encoded.encode("ascii"), validate=True).decode("ascii")
        )
        hello = _startup_hello(
            invocation,
            launcher_path=pinned_python,
            fit_path=base_python,
            launcher_sha256=pinned_sha,
            fit_sha256=base_sha,
        )
        if tamper == "launcher_pid":
            hello["launcher"]["pid"] = 4_322
        elif tamper == "launcher_parent":
            hello["launcher"]["parent_pid"] = os.getpid() + 1
        elif tamper == "launcher_creation":
            hello["launcher"]["creation_time_100ns"] = 11_001
        elif tamper == "launcher_path":
            hello["launcher"]["kernel_executable_path"] = str(
                (tmp_path / "other-launcher.exe").resolve()
            )
        elif tamper == "launcher_hash":
            hello["launcher"]["kernel_executable_sha256"] = "0" * 64
        elif tamper == "fit_pid_equals_launcher":
            hello["fit_interpreter"]["pid"] = 4_321
        elif tamper == "fit_parent":
            hello["fit_interpreter"]["parent_pid"] = 4_320
        elif tamper == "fit_creation":
            hello["fit_interpreter"]["creation_time_100ns"] = 22_001
        elif tamper == "fit_path":
            hello["fit_interpreter"]["kernel_executable_path"] = str(
                (tmp_path / "other-fit.exe").resolve()
            )
        else:
            hello["fit_interpreter"]["kernel_executable_sha256"] = "0" * 64
        unsealed = {key: value for key, value in hello.items() if key != "record_digest"}
        hello["record_digest"] = _sha(_canonical(unsealed))
        context.startup_path.write_bytes(_canonical(hello))
        return FakeLauncher()

    monkeypatch.setattr(W.subprocess, "Popen", popen)
    process = W._VerifiedFitProcess(
        context=context,
        target=spawn_worker,
        args=args,
        name="bu-job-synthetic",
    )

    with pytest.raises(W.BootstrapRefused):
        process.start()
    assert launch_count == 1
    assert not context.startup_ack_path.exists()


def test_historical_spawn_request_is_diverted_without_calling_native_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    native_calls: list[object] = []
    native_pickle_calls: list[object] = []
    verified_context = object()

    def native_get_context(method: str | None = None) -> object:
        native_calls.append(method)
        raise AssertionError("native multiprocessing context must not be called")

    pickle_module = __import__("pickle")

    def native_pickle_dumps(value: object, *args: object, **kwargs: object) -> bytes:
        native_pickle_calls.append((value, args, kwargs))
        raise AssertionError("native pickle serialization must not be called")

    monkeypatch.setattr(pickle_module, "dumps", native_pickle_dumps)
    supervisor = SimpleNamespace(
        multiprocessing=SimpleNamespace(get_context=native_get_context),
        pickle=pickle_module,
    )

    def original_run_isolated(callback: object, **kwargs: object) -> None:
        events.append("historical-run-isolated")
        assert supervisor.pickle.dumps((callback, kwargs["payload"])).startswith(b"D-166")
        assert supervisor.multiprocessing.get_context("spawn") is verified_context

    supervisor.run_isolated_attempt = original_run_isolated

    def fit_worker(*args: object) -> None:
        del args

    def historical_lookup(token: str) -> dict[str, str]:
        return {"token": token}

    launch = SimpleNamespace(
        _fit_worker=fit_worker,
        _historical_lease_record=historical_lookup,
        run_isolated_attempt=original_run_isolated,
        PREFLIGHT_FILE="synthetic.json",
    )

    def lower(**kwargs: object) -> None:
        del kwargs
        launch.run_isolated_attempt(launch._fit_worker, payload={})
        raise RuntimeError("synthetic-stop-after-adapter")

    launch.launch_exp2a_repairs = lower
    production = SimpleNamespace(
        PREFLIGHT_ROOT=tmp_path,
        OUTPUT_ROOT=tmp_path / "output",
        SYNC_ROOT=tmp_path / "sync",
    )
    monkeypatch.setitem(sys.modules, "bu.experiments.supervisor", supervisor)
    monkeypatch.setattr(
        W,
        "_install_old_source_tree",
        lambda authority: (production, launch, {"record_digest": "d" * 64}),
    )
    monkeypatch.setattr(W, "_VerifiedFitContext", lambda **kwargs: verified_context)
    monkeypatch.setattr(W, "_assert_old_normal_release_absent", lambda: None)
    monkeypatch.setattr(W, "_validate_execution_source_tree", lambda authority: None)
    monkeypatch.setattr(W, "_validate_loaded_bu_modules", lambda authority: None)

    def capture(thunk: Any) -> tuple[None, BaseException, dict[str, object]]:
        try:
            thunk()
        except BaseException as exc:
            return None, exc, {}
        raise AssertionError("synthetic lower launch unexpectedly returned")

    monkeypatch.setattr(W, "_capture_lower_output", capture)
    monkeypatch.setattr(
        W, "_verified_historical_git_state", lambda authority: nullcontext()
    )
    with pytest.raises(W.CapturedLowerRefused):
        W._launch_once({})
    assert events == ["historical-run-isolated"]
    assert native_calls == []
    assert native_pickle_calls == []
    assert supervisor.multiprocessing.get_context is native_get_context
    assert supervisor.pickle is pickle_module
    assert launch.run_isolated_attempt is original_run_isolated


def test_historical_planned_attempt_cardinality_receives_fresh_one_use_contexts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contexts: list[Any] = []
    real_context_type = W._VerifiedFitContext
    bundle = b'{"synthetic":"bundle"}'
    monkeypatch.setattr(W, "RUNTIME_TEMP", tmp_path)
    monkeypatch.setattr(W, "_fit_child_bundle", lambda authority: (bundle, _sha(bundle)))

    def native_get_context(method: str | None = None) -> object:
        raise AssertionError(f"native multiprocessing context was called with {method!r}")

    supervisor = SimpleNamespace(
        multiprocessing=SimpleNamespace(get_context=native_get_context),
        pickle=__import__("pickle"),
    )

    def original_run_isolated(callback: object, **kwargs: object) -> None:
        assert supervisor.pickle.dumps((callback, kwargs["payload"])).startswith(b"D-166")
        context = supervisor.multiprocessing.get_context("spawn")
        receive, send = context.Pipe(duplex=False)
        receive.close()
        send.close()

    supervisor.run_isolated_attempt = original_run_isolated

    def fit_worker(*args: object) -> None:
        del args

    launch = SimpleNamespace(
        _fit_worker=fit_worker,
        _historical_lease_record=lambda token: {"token": token},
        run_isolated_attempt=original_run_isolated,
        PREFLIGHT_FILE="synthetic.json",
    )

    def lower(**kwargs: object) -> None:
        del kwargs
        for index in range(W.EXPECTED_COUNTS["executed"]):
            launch.run_isolated_attempt(launch._fit_worker, payload={"index": index})
        raise RuntimeError("synthetic-stop-after-planned-cardinality")

    launch.launch_exp2a_repairs = lower
    production = SimpleNamespace(
        PREFLIGHT_ROOT=tmp_path,
        OUTPUT_ROOT=tmp_path / "output",
        SYNC_ROOT=tmp_path / "sync",
    )

    def context_factory(**kwargs: object) -> Any:
        context = real_context_type(**kwargs)
        contexts.append(context)
        return context

    monkeypatch.setitem(sys.modules, "bu.experiments.supervisor", supervisor)
    monkeypatch.setattr(
        W,
        "_install_old_source_tree",
        lambda authority: (production, launch, {"record_digest": "d" * 64}),
    )
    monkeypatch.setattr(W, "_VerifiedFitContext", context_factory)
    monkeypatch.setattr(W, "_assert_old_normal_release_absent", lambda: None)
    monkeypatch.setattr(W, "_validate_execution_source_tree", lambda authority: None)
    monkeypatch.setattr(W, "_validate_loaded_bu_modules", lambda authority: None)
    monkeypatch.setattr(
        W, "_verified_historical_git_state", lambda authority: nullcontext()
    )

    def capture(thunk: Any) -> tuple[None, BaseException, dict[str, object]]:
        try:
            thunk()
        except BaseException as exc:
            return None, exc, {}
        raise AssertionError("synthetic lower launch unexpectedly returned")

    monkeypatch.setattr(W, "_capture_lower_output", capture)
    with pytest.raises(W.CapturedLowerRefused):
        W._launch_once({})

    assert len(contexts) == W.EXPECTED_COUNTS["executed"] == 111
    assert len({id(context) for context in contexts}) == len(contexts)
    for context in contexts:
        with pytest.raises(W.BootstrapRefused, match="one-use"):
            context.Pipe(duplex=False)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"kind":',
        b'{"kind": "success", "result_json": "{}"}',
        _canonical({"kind": "success", "result_json": 3}),
        _canonical({"kind": "unknown"}),
        _canonical(
            {
                "kind": "python_exception",
                "error_type": "ValueError",
                "error": 4,
                "traceback": "synthetic",
            }
        ),
    ],
    ids=["partial", "noncanonical", "malformed-success", "unknown-kind", "malformed-error"],
)
def test_result_receiver_rejects_partial_noncanonical_or_malformed_protocol(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "result.json"
    path.write_bytes(raw)
    receiver = W._VerifiedFitReceive(path)
    with pytest.raises(W.BootstrapRefused):
        receiver.recv()
    assert path.read_bytes() == raw


def test_result_receiver_rejects_linked_protocol(tmp_path: Path) -> None:
    backing = tmp_path / "backing.json"
    path = tmp_path / "linked-result.json"
    backing.write_bytes(_canonical({"kind": "success", "result_json": "{}"}))
    try:
        os.link(backing, path)
    except OSError as exc:  # pragma: no cover - host filesystem capability
        pytest.skip(f"hard links unavailable on test filesystem: {exc}")
    with pytest.raises(W.BootstrapRefused, match="linked"):
        W._VerifiedFitReceive(path).recv()
    assert path.exists() and backing.exists()


def test_result_receiver_accepts_canonical_protocol_and_cleans_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "result.json"
    message = {"kind": "success", "result_json": '{"seed":1000}'}
    path.write_bytes(_canonical(message))
    synced: list[Path] = []
    monkeypatch.setattr(W, "_fsync_directory", lambda value: synced.append(value) or False)
    assert W._VerifiedFitReceive(path).recv() == message
    assert not path.exists()
    assert synced == [tmp_path]


@pytest.mark.skipif(os.name != "nt", reason="publication contract is Windows-only")
def test_fit_child_protocol_publication_is_atomic_and_no_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path.resolve()
    path = runtime / f"fit-child-result-{'a' * 64}.json"
    message = {"kind": "success", "result_json": '{"ok":true}'}
    expected = _canonical(message)
    events: list[str] = []
    original_fsync = os.fsync
    original_rename = os.rename

    def fsync(descriptor: int) -> None:
        original_fsync(descriptor)
        events.append("fsync")

    def rename(source: str | bytes | Path, target: str | bytes | Path) -> None:
        assert events == ["fsync"]
        assert Path(source).read_bytes() == expected
        assert not Path(target).exists()
        events.append("rename")
        original_rename(source, target)

    monkeypatch.setattr(F, "RUNTIME_TEMP", runtime)
    monkeypatch.setattr(F.os, "fsync", fsync)
    monkeypatch.setattr(F.os, "rename", rename)
    F._publish_protocol(path, message)
    assert events == ["fsync", "rename"]
    assert path.read_bytes() == expected
    assert list(runtime.glob(".*.tmp")) == []

    with pytest.raises(F.FitChildRefused, match="occupied"):
        F._publish_protocol(path, {"kind": "success", "result_json": "{}"})
    assert path.read_bytes() == expected


def _synthetic_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    controller_commit: str,
) -> tuple[dict[str, Any], dict[str, Any], Any, list[dict[str, Any]]]:
    controller = tmp_path / "controller"
    execution = tmp_path / "execution"
    controller_source = controller / "src"
    execution_source = execution / "src"
    site_packages = tmp_path / "site-packages"
    scripts = controller / "scripts"
    for path in (controller_source, execution_source, site_packages, scripts):
        path.mkdir(parents=True, exist_ok=True)
    entrypoint = scripts / "entrypoint.py"
    helper = scripts / "raw_authority.py"
    entrypoint.write_bytes(b"ENTRYPOINT = True\n")
    helper.write_bytes(b"RAW_HELPER = True\n")
    entrypoint_sha = _sha(entrypoint.read_bytes())
    helper_sha = _sha(helper.read_bytes())
    execution_commit = "e" * 40

    monkeypatch.setattr(F, "CONTROLLER_WORKTREE", controller)
    monkeypatch.setattr(F, "EXECUTION_WORKTREE", execution)
    monkeypatch.setattr(F, "CONTROLLER_SOURCE", controller_source)
    monkeypatch.setattr(F, "EXECUTION_SOURCE", execution_source)
    monkeypatch.setattr(F, "PINNED_SITE_PACKAGES", site_packages)
    monkeypatch.setattr(F, "ENTRYPOINT_SCRIPT", entrypoint)
    monkeypatch.setattr(F, "RAW_AUTHORITY_HELPER", helper)
    monkeypatch.setattr(F, "EXPECTED_RAW_AUTHORITY_HELPER_SHA256", helper_sha)
    monkeypatch.setattr(F, "EXECUTION_COMMIT", execution_commit)

    def file_identity(path: Path, digest: str) -> dict[str, object]:
        return {"path": str(path.resolve()), "sha256": digest, "size": path.stat().st_size}

    def worktree_identity(
        path: Path, commit: str, *, detached: bool, branch: str
    ) -> dict[str, object]:
        return {
            "path": str(path.resolve()),
            "git_commit": commit,
            "branch": branch,
            "detached": detached,
            "tracked_file_count": 1,
            "stability_observations": 2,
            "tracked_tree_digest": "1" * 64,
            "worktree_inventory_digest": "2" * 64,
            "retained_read_lock_count": 1,
        }

    helper_identity = file_identity(helper, helper_sha)
    raw_payload = {
        "raw_authority_schema_version": F.RAW_AUTHORITY_SCHEMA_VERSION,
        "record_type": "week8_d161_preimport_authority",
        "decision_id": F.DECISION_ID,
        "runtime": {"command": "recover", "entrypoint_source_sha256": entrypoint_sha},
        "native_startup": {
            "stage0_binding_sha256": "6" * 64,
            "release_receipt_sha256": "3" * 64,
            "native_launcher": {"sha256": "4" * 64},
            "startup_binding_sha256": "5" * 64,
        },
        "git": {},
        "git_runtime": {},
        "raw_authority_helper": helper_identity,
        "controller": worktree_identity(
            controller, controller_commit, detached=False, branch="synthetic"
        ),
        "execution": worktree_identity(
            execution, execution_commit, detached=True, branch="HEAD"
        ),
        "admission": {},
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }
    raw = {**raw_payload, "record_digest": _sha(_canonical(raw_payload))}
    gate_payload = {
        "entrypoint_gate_schema_version": F.ENTRYPOINT_GATE_SCHEMA_VERSION,
        "record_type": "week8_d161_entrypoint_gate",
        "decision_id": F.DECISION_ID,
        "command": "recover",
        "entrypoint": file_identity(entrypoint, entrypoint_sha),
        "raw_authority_helper": helper_identity,
        "raw_authority": raw,
        "admitted_pythonpath": [str(controller_source.resolve()), str(site_packages.resolve())],
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }
    gate = {**gate_payload, "record_digest": _sha(_canonical(gate_payload))}
    invocation = {"entrypoint_gate_digest": gate["record_digest"]}
    monkeypatch.setenv(
        F.ENTRYPOINT_GATE_ENVIRONMENT_NAME, _canonical(gate).decode("ascii")
    )
    observed_configs: list[dict[str, Any]] = []

    def revalidate(
        observed_raw: dict[str, Any], config: dict[str, Any], **kwargs: object
    ) -> dict[str, Any]:
        del kwargs
        observed_configs.append(config)
        return observed_raw

    raw_module = SimpleNamespace(revalidate_recorded_static_authority=revalidate)
    return gate, invocation, raw_module, observed_configs


def test_fit_child_derives_and_validates_controller_commit_from_sealed_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller_commit = "c" * 40
    gate, invocation, raw_module, observed = _synthetic_gate(
        tmp_path, monkeypatch, controller_commit=controller_commit
    )
    returned_gate, returned_raw = F._validate_entrypoint_gate(raw_module, invocation)
    assert returned_gate == gate
    assert returned_raw == gate["raw_authority"]
    assert len(observed) == 1
    assert observed[0]["controller_commit"] == controller_commit
    assert observed[0]["execution_commit"] == F.EXECUTION_COMMIT


@pytest.mark.parametrize("bad_commit", ["C" * 40, "c" * 39, "g" * 40])
def test_fit_child_refuses_noncanonical_sealed_controller_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_commit: str
) -> None:
    gate, invocation, raw_module, observed = _synthetic_gate(
        tmp_path, monkeypatch, controller_commit=bad_commit
    )
    with pytest.raises(F.FitChildRefused, match="sealed worktree authority"):
        F._validate_entrypoint_gate(raw_module, invocation)
    assert gate["raw_authority"]["controller"]["git_commit"] == bad_commit
    assert observed == []


def test_fit_child_historical_git_adapter_blocks_hostile_fsmonitor_and_restores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    execution = tmp_path / "execution"
    source = execution / "src" / "bu" / "runrecord.py"
    source.parent.mkdir(parents=True)
    source.write_text("# synthetic captured historical runrecord\n", encoding="utf-8")
    git_dir = execution / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        "[core]\n\tfsmonitor = hostile-fit-child-helper.cmd\n", encoding="ascii"
    )
    marker = tmp_path / "fit-child-hostile-git-executed.txt"
    runrecord = ModuleType("bu.runrecord")
    runrecord.__file__ = str(source.resolve())
    runrecord.__dict__["marker"] = marker
    exec(
        compile(
            "class GitState:\n"
            " def __init__(self, commit, dirty, branch):\n"
            "  self.commit=commit; self.dirty=dirty; self.branch=branch\n"
            " @property\n"
            " def trustworthy(self):\n"
            "  return (not self.dirty) and len(self.commit)==40\n"
            "def git_state(repo=None):\n"
            " marker.write_text('HOSTILE_FSMONITOR_EXECUTED', encoding='ascii')\n"
            " return GitState('0'*40, True, 'hostile')\n",
            str(source.resolve()),
            "exec",
        ),
        runrecord.__dict__,
    )
    runrecord.PROJECT_ROOT = execution
    runrecord.__spec__ = SimpleNamespace(
        loader=SimpleNamespace(
            binding_marker="week8_d161_verified_source_v2",
            tree_kind="execution",
        )
    )
    original = runrecord.git_state
    aliases = [runrecord]
    for name in (
        "bu.experiments.confirmatory",
        "bu.experiments.fit_evidence",
        "bu.experiments.preflight",
    ):
        module = ModuleType(name)
        module.git_state = original
        aliases.append(module)
    for module in [ModuleType("bu"), ModuleType("bu.experiments"), *aliases]:
        monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(F, "EXECUTION_WORKTREE", execution)
    monkeypatch.setattr(F, "EXECUTION_SOURCE", execution / "src")
    raw = {
        "execution": {
            "path": str(execution.resolve()),
            "git_commit": F.EXECUTION_COMMIT,
            "branch": "HEAD",
            "detached": True,
            "worktree_inventory_digest": "a" * 64,
            "stability_observations": 2,
        }
    }

    with F._verified_historical_git_state(raw) as adapter:
        assert all(module.git_state is adapter for module in aliases)
        for module in aliases:
            state = module.git_state()
            assert type(state).__name__ == "GitState"
            assert state.commit == F.EXECUTION_COMMIT
            assert state.dirty is False
            assert state.branch == "HEAD"
            assert state.trustworthy is True
        assert not marker.exists()

    assert all(module.git_state is original for module in aliases)
    assert not marker.exists()

    imported = ModuleType("bu.experiments.dynamic_fit_git_alias")
    with pytest.raises(F.FitChildRefused, match="restoration failed") as caught:
        with F._verified_historical_git_state(raw, allow_imports=True) as adapter:
            imported.git_state = adapter
            monkeypatch.setitem(sys.modules, imported.__name__, imported)
            imported.git_state = object()
    assert caught.value.__cause__ is not None
    assert "binding changed after import" in str(caught.value.__cause__)
    assert all(module.git_state is original for module in aliases)


def test_source_and_dependency_finders_are_installed_before_any_bu_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller_source = tmp_path / "controller" / "src"
    execution_source = tmp_path / "execution" / "src"
    site_packages = tmp_path / "site-packages"
    inherited = tmp_path / "stdlib"
    for path in (controller_source, execution_source, site_packages, inherited):
        path.mkdir(parents=True)
    monkeypatch.setattr(F, "CONTROLLER_SOURCE", controller_source)
    monkeypatch.setattr(F, "EXECUTION_SOURCE", execution_source)
    monkeypatch.setattr(F, "PINNED_SITE_PACKAGES", site_packages)
    for name in tuple(sys.modules):
        if name == "bu" or name.startswith("bu."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    source_finder = SimpleNamespace(binding_marker="week8_d161_verified_source_v2")
    dependency_finder = SimpleNamespace(
        binding_marker="week8_d161_verified_dependency_source_v1"
    )
    api_events: list[str] = []
    raw_module = SimpleNamespace(
        verified_source_finder=lambda raw, tree: (
            api_events.append(f"source:{tree}") or source_finder
        ),
        verified_dependency_finder=lambda raw: (
            api_events.append("dependency") or dependency_finder
        ),
    )
    previous_meta_path = [object(), object()]
    monkeypatch.setattr(sys, "path", [str(inherited)])
    monkeypatch.setattr(sys, "meta_path", previous_meta_path.copy())
    monkeypatch.setattr(F.importlib, "invalidate_caches", lambda: api_events.append("invalidate"))

    assert F._install_verified_execution(raw_module, {}) == (
        source_finder,
        dependency_finder,
    )
    assert api_events == ["source:execution", "dependency", "invalidate"]
    assert sys.meta_path == [source_finder, dependency_finder, *previous_meta_path]
    assert sys.path == [
        str(execution_source.resolve()),
        str(inherited),
        str(site_packages.resolve()),
    ]
    assert not any(name == "bu" or name.startswith("bu.") for name in sys.modules)


def test_fit_child_main_installs_verified_finders_before_fixed_bu_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    @contextmanager
    def relocation_scope(module, raw, value, callback):
        assert module is raw_module and raw == {"raw": True} and value is invocation
        events.append("relocation-enter")
        try: yield
        finally: events.append("relocation-exit")
    monkeypatch.setattr(F, "_fit_relocation_scope", relocation_scope)
    invocation = _invocation_v3(tmp_path, payload={"seed": 1000})
    hello = _startup_hello(invocation)
    ack = _startup_ack(invocation, hello)
    source_finder = object()
    dependency_finder = object()
    previous_meta_path = [object()]
    monkeypatch.setattr(sys, "meta_path", previous_meta_path.copy())
    monkeypatch.setattr(F, "_silence_standard_streams", lambda: events.append("silence"))
    monkeypatch.setattr(
        F,
        "_decode_invocation",
        lambda: (
            invocation,
            Path(invocation["result_path"]),
            Path(invocation["startup_path"]),
            Path(invocation["startup_ack_path"]),
        ),
    )
    monkeypatch.setattr(
        F,
        "_validate_invocation",
        lambda document: (tmp_path / "attempt", {"seed": 1000}),
    )
    raw_module = SimpleNamespace()
    monkeypatch.setattr(F, "_load_bound_raw_authority", lambda: raw_module)
    monkeypatch.setattr(F, "_validate_control_environment", lambda module, invocation: None)
    monkeypatch.setattr(
        F,
        "_publish_startup_hello",
        lambda *args, **kwargs: events.append("startup") or hello,
        raising=False,
    )
    monkeypatch.setattr(
        F,
        "_await_startup_ack",
        lambda *args, **kwargs: events.append("ack") or ack,
        raising=False,
    )
    monkeypatch.setattr(
        F,
        "_validate_entrypoint_gate",
        lambda module, invocation: ({"gate": True}, {"raw": True}),
    )
    monkeypatch.setattr(
        F,
        "_validate_transport",
        lambda module, raw, invocation: events.append("transport"),
    )

    def install(module: object, raw: object) -> tuple[object, object]:
        del module, raw
        events.append("install")
        sys.meta_path[:0] = [source_finder, dependency_finder]
        return source_finder, dependency_finder

    def import_callback(observed_source_finder: object) -> Any:
        assert observed_source_finder is source_finder
        assert sys.meta_path[:2] == [source_finder, dependency_finder]
        events.append("import-bu")
        return lambda attempt, payload: {"seed": payload["seed"]}

    published: list[tuple[Path, dict[str, str]]] = []
    monkeypatch.setattr(F, "_install_verified_execution", install)
    monkeypatch.setattr(F, "_import_fixed_fit_worker", import_callback)
    monkeypatch.setattr(
        F.importlib, "import_module", lambda name: ModuleType(name)
    )
    monkeypatch.setattr(
        F, "_validate_isolated_runtime", lambda: events.append("isolated")
    )
    monkeypatch.setattr(
        F, "_verified_historical_git_state", lambda raw, **kwargs: nullcontext()
    )
    monkeypatch.setattr(
        F,
        "_publish_protocol",
        lambda path, message: published.append((path, dict(message))),
    )
    assert F.main() == 0
    assert events == [
        "silence",
        "isolated",
        "startup",
        "ack",
        "transport",
        "install",
        "import-bu",
        "relocation-enter",
        "relocation-exit",
    ]
    assert published == [
        (
            Path(invocation["result_path"]),
            {"kind": "success", "result_json": '{"seed":1000}'},
        )
    ]


def test_fit_child_no_ack_stops_before_gate_import_or_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = _invocation_v3(tmp_path, payload={"seed": 1000})
    hello = _startup_hello(invocation)
    events: list[str] = []
    published: list[dict[str, str]] = []
    callback_called = False
    monkeypatch.setattr(F, "FIT_CHILD_STARTUP_TIMEOUT_SECONDS", 0.0, raising=False)
    monkeypatch.setattr(F, "_silence_standard_streams", lambda: events.append("silence"))
    monkeypatch.setattr(
        F, "_validate_isolated_runtime", lambda: events.append("isolated")
    )
    monkeypatch.setattr(
        F,
        "_decode_invocation",
        lambda: (
            invocation,
            Path(invocation["result_path"]),
            Path(invocation["startup_path"]),
            Path(invocation["startup_ack_path"]),
        ),
    )
    monkeypatch.setattr(
        F,
        "_validate_invocation",
        lambda document: (tmp_path / "attempt", document["payload"]),
    )
    monkeypatch.setattr(F, "_load_bound_raw_authority", lambda: SimpleNamespace())
    monkeypatch.setattr(F, "_validate_control_environment", lambda *args: None)
    monkeypatch.setattr(
        F,
        "_publish_startup_hello",
        lambda *args, **kwargs: events.append("startup") or hello,
        raising=False,
    )

    def no_ack(*args: object, **kwargs: object) -> None:
        del args, kwargs
        events.append("no-ack")
        raise F.FitChildRefused("synthetic startup acknowledgment is absent")

    def gate(*args: object, **kwargs: object) -> None:
        del args, kwargs
        events.append("gate")
        raise AssertionError("gate validation ran before startup acknowledgment")

    def import_callback(*args: object, **kwargs: object) -> Any:
        del args, kwargs
        events.append("import-bu")

        def callback(*callback_args: object, **callback_kwargs: object) -> dict[str, int]:
            nonlocal callback_called
            del callback_args, callback_kwargs
            callback_called = True
            return {"seed": 1000}

        return callback

    monkeypatch.setattr(F, "_await_startup_ack", no_ack, raising=False)
    monkeypatch.setattr(F, "_validate_entrypoint_gate", gate)
    monkeypatch.setattr(F, "_import_fixed_fit_worker", import_callback)
    monkeypatch.setattr(
        F,
        "_publish_protocol",
        lambda path, message: published.append(dict(message)),
    )

    try:
        F.main()
    except F.FitChildRefused:
        pass

    assert events == ["silence", "isolated", "startup", "no-ack"]
    assert callback_called is False
    assert not any(message.get("kind") == "success" for message in published)


@pytest.mark.parametrize(
    "tamper",
    ["partial", "noncanonical", "wrong_digest", "extra_field"],
)
def test_fit_child_refuses_malformed_startup_ack_before_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    invocation = _invocation_v3(tmp_path)
    hello = _startup_hello(invocation)
    ack = _startup_ack(invocation, hello)
    startup_path = Path(invocation["startup_path"])
    ack_path = Path(invocation["startup_ack_path"])
    startup_path.write_bytes(_canonical(hello))
    if tamper == "partial":
        raw = b'{"fit_child_startup_schema_version":'
    elif tamper == "noncanonical":
        raw = b" " + _canonical(ack)
    else:
        if tamper == "wrong_digest":
            ack["record_digest"] = "0" * 64
        else:
            ack["unexpected"] = True
            unsealed = {key: value for key, value in ack.items() if key != "record_digest"}
            ack["record_digest"] = _sha(_canonical(unsealed))
        raw = _canonical(ack)
    ack_path.write_bytes(raw)
    monkeypatch.setattr(F, "RUNTIME_TEMP", tmp_path)
    await_ack = getattr(F, "_await_startup_ack", None)
    assert callable(await_ack), "fit child must expose the bounded startup-ack gate"

    with pytest.raises(F.FitChildRefused):
        await_ack(invocation, hello, timeout=0.0)
    assert ack_path.read_bytes() == raw
    assert startup_path.read_bytes() == _canonical(hello)


def test_fit_child_refuses_linked_startup_ack_before_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invocation = _invocation_v3(tmp_path)
    hello = _startup_hello(invocation)
    ack = _startup_ack(invocation, hello)
    startup_path = Path(invocation["startup_path"])
    ack_path = Path(invocation["startup_ack_path"])
    backing = tmp_path / "startup-ack-backing.json"
    startup_path.write_bytes(_canonical(hello))
    backing.write_bytes(_canonical(ack))
    try:
        os.link(backing, ack_path)
    except OSError as exc:  # pragma: no cover - host filesystem capability
        pytest.skip(f"hard links unavailable on test filesystem: {exc}")
    monkeypatch.setattr(F, "RUNTIME_TEMP", tmp_path)
    await_ack = getattr(F, "_await_startup_ack", None)
    assert callable(await_ack), "fit child must expose the bounded startup-ack gate"

    with pytest.raises(F.FitChildRefused, match="linked|ack"):
        await_ack(invocation, hello, timeout=0.0)
    assert backing.exists() and ack_path.exists() and startup_path.exists()
