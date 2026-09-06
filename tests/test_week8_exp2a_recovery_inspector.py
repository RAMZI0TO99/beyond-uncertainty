"""Synthetic tests for the fixed, read-only D-161 old-source inspector."""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from bu.durable import atomic_write_bytes


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "week8_exp2a_recovery_inspector.py"
)
SPEC = importlib.util.spec_from_file_location("d161_recovery_inspector_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
I = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(I)


def _entrypoint_gate(command: str) -> dict[str, Any]:
    raw = {
        "raw_authority_schema_version": 4,
        "record_digest": "a" * 64,
        "controller": {"git_commit": "d" * 40},
        "native_startup": {
            "release_receipt_sha256": "1" * 64,
            "native_launcher": {"sha256": "2" * 64},
            "stage0_binding_sha256": "4" * 64,
            "startup_binding_sha256": "3" * 64,
        },
    }
    payload = {
        "entrypoint_gate_schema_version": 4,
        "record_type": "week8_d161_entrypoint_gate",
        "decision_id": "D-161",
        "command": command,
        "entrypoint": {"path": "synthetic", "sha256": "b" * 64},
        "raw_authority_helper": {"path": "synthetic", "sha256": "c" * 64},
        "raw_authority": raw,
        "admitted_pythonpath": ["synthetic"],
        "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }
    payload["record_digest"] = I._sha_bytes(I._canonical_ascii(payload))
    return payload


@pytest.mark.parametrize("command", ("status", "adjudicate", "recover"))
def test_inspector_accepts_exactly_recovery_read_commands(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _entrypoint_gate(command)
    raw_module = SimpleNamespace(
        revalidate_admitted_authority=lambda raw, config, **kwargs: raw
    )
    monkeypatch.setattr(I, "_load_bound_raw_authority", lambda: raw_module)
    monkeypatch.setenv(
        I.ENTRYPOINT_GATE_ENVIRONMENT_NAME,
        I._canonical_ascii(gate).decode("ascii"),
    )
    assert I._validate_entrypoint_authority() == gate


@pytest.mark.parametrize(
    "command",
    ("seal", "monitor", "finalize", "report", "figures", "worker"),
)
def test_inspector_rejects_every_non_inspection_command(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _entrypoint_gate(command)
    monkeypatch.setenv(
        I.ENTRYPOINT_GATE_ENVIRONMENT_NAME,
        I._canonical_ascii(gate).decode("ascii"),
    )
    with pytest.raises(I.InspectorRefused, match="policy differs"):
        I._validate_entrypoint_authority()


def test_inspector_has_one_authoritative_source_ledger_pin_and_no_write_api() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count(
        "2265cbcece1033ce4d0f3df2e4b093d497c6815d5cb0592a511a6515f9fd7379"
    ) == 1
    assert "EXPECTED_HASHES[\"source_ledger_file\"] =" not in source
    tree = ast.parse(source)
    top_level_bu_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and (node.module == "bu" or str(node.module).startswith("bu."))
    ]
    assert top_level_bu_imports == []
    assert "def _git(" not in source
    assert "import subprocess" not in source
    forbidden_calls = {
        "atomic_write_bytes",
        "atomic_write_json",
        "copy",
        "copy2",
        "copytree",
        "mkdir",
        "replace",
        "rename",
        "rmdir",
        "unlink",
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert forbidden_calls.isdisjoint(called)


def test_all_loaded_bu_modules_must_resolve_inside_detached_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    execution = tmp_path / "execution"
    source = execution / "src"
    package = source / "bu"
    package.mkdir(parents=True)
    root_file = package / "__init__.py"
    child_file = package / "child.py"
    root_file.write_text("# synthetic\n", encoding="utf-8")
    child_file.write_text("# synthetic\n", encoding="utf-8")
    monkeypatch.setattr(I, "EXECUTION_WORKTREE", execution)
    monkeypatch.setattr(I, "EXECUTION_SOURCE", source)
    for name in tuple(sys.modules):
        if name == "bu" or name.startswith("bu."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    sources = {
        "src/bu/__init__.py": root_file.read_bytes(),
        "src/bu/child.py": child_file.read_bytes(),
    }
    blobs = {
        "src/bu/__init__.py": "1" * 40,
        "src/bu/child.py": "2" * 40,
    }
    tree_digest = "3" * 64
    finder = SimpleNamespace(
        binding_marker="week8_d161_verified_source_v2"
    )
    dependency_finder = SimpleNamespace(
        binding_marker="week8_d161_verified_dependency_source_v1"
    )

    def loaded(name: str, path: Path, relative: str) -> ModuleType:
        loader = SimpleNamespace(
            binding_marker="week8_d161_verified_source_v2",
            tree_kind="execution",
            source_sha256=I._sha_bytes(sources[relative]),
            git_blob=blobs[relative],
            authority_tree_digest=tree_digest,
        )
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__loader__ = loader
        module.__spec__ = SimpleNamespace(loader=loader)
        return module

    root_module = loaded("bu", root_file, "src/bu/__init__.py")
    child_module = loaded("bu.child", child_file, "src/bu/child.py")
    monkeypatch.setitem(sys.modules, "bu", root_module)
    monkeypatch.setitem(sys.modules, "bu.child", child_module)
    monkeypatch.setattr(
        sys,
        "meta_path",
        [
            finder,
            dependency_finder,
            importlib.machinery.BuiltinImporter,
            importlib.machinery.FrozenImporter,
            importlib.machinery.PathFinder,
        ],
    )
    raw_module = SimpleNamespace(
        admitted_source_bytes=lambda raw, tree, relative: sources[relative],
        admitted_git_blob=lambda raw, tree, relative: blobs[relative],
    )
    monkeypatch.setattr(I, "_load_bound_raw_authority", lambda: raw_module)
    gate = {
        "raw_authority": {
            "execution": {"worktree_inventory_digest": tree_digest}
        }
    }
    rows = I._verify_loaded_bu_modules(gate, finder, dependency_finder)
    assert [row["module_id"] for row in rows] == ["bu", "bu.child"]
    child_module.__spec__.loader.source_sha256 = "4" * 64
    with pytest.raises(I.InspectorRefused, match="differs from verified bytes"):
        I._verify_loaded_bu_modules(gate, finder, dependency_finder)
    child_module.__spec__.loader.source_sha256 = I._sha_bytes(
        sources["src/bu/child.py"]
    )
    child_module.__spec__.loader.binding_marker = "unbound-loader"
    with pytest.raises(I.InspectorRefused, match="differs from verified bytes"):
        I._verify_loaded_bu_modules(gate, finder, dependency_finder)


def _synthetic_job_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Any, Any, Any, Any, Any, list[dict[str, Any]], list[str]]:
    workspace = tmp_path / "workspace"
    output = workspace / "output"
    sync = workspace / "sync"
    local_root = output / "jobs"
    durable_root = sync / "jobs"
    local_root.mkdir(parents=True)
    durable_root.mkdir(parents=True)
    monkeypatch.setattr(I, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(I, "OUTPUT_ROOT", output)
    monkeypatch.setattr(I, "SYNC_ROOT", sync)

    jobs = [f"job-{index:03d}" for index in range(261)]
    jobs[149] = I.ORPHAN_JOB_ID
    started = jobs[:150]
    synced = jobs[:149]
    for job_id in started:
        (local_root / job_id).mkdir()
    for job_id in synced:
        (durable_root / job_id).mkdir()
    partial = durable_root / I.HIDDEN_PARTIAL_NAME
    partial.mkdir()
    for index in range(15):
        atomic_write_bytes(
            local_root / I.ORPHAN_JOB_ID / f"f{index:02d}.bin",
            f"value-{index}".encode(),
        )
    for index in range(11):
        atomic_write_bytes(
            partial / f"f{index:02d}.bin", f"value-{index}".encode()
        )

    tree_digests = {job_id: f"{index + 1:064x}" for index, job_id in enumerate(jobs)}
    execution_digests = {
        job_id: f"{index + 1000:064x}" for index, job_id in enumerate(jobs)
    }
    copy_digests = {
        job_id: f"{index + 2000:064x}" for index, job_id in enumerate(jobs)
    }
    local_calls: list[str] = []
    durable_calls: list[str] = []

    class Plan:
        START_DIRECTORY = "starts"

        @staticmethod
        def new_exp2a_jobs() -> tuple[SimpleNamespace, ...]:
            return tuple(SimpleNamespace(job_id=job_id) for job_id in jobs)

    class Launch:
        @staticmethod
        def validate_local_completed_exp2a_job(job_id: str, **request: Any) -> dict[str, str]:
            local_calls.append(job_id)
            return {
                "source_tree_digest": tree_digests[job_id],
                "execution_digest": execution_digests[job_id],
            }

        @staticmethod
        def reconcile_completed_exp2a_job(job_id: str, **request: Any) -> dict[str, Any]:
            durable_calls.append(job_id)
            return {
                "job": {"job_id": job_id},
                "source_kind": "synthetic",
                "source_path": f"synthetic-local/{job_id}",
                "copy_path": f"synthetic-copy/{job_id}",
                "expected_git_commit": I.EXECUTION_COMMIT,
                "execution_digest": execution_digests[job_id],
                "sidecar_sha256": f"{jobs.index(job_id) + 4000:064x}",
                "source_tree_digest": tree_digests[job_id],
                "copy_tree_digest": tree_digests[job_id],
                "copy_evidence_digest": copy_digests[job_id],
                "independent_files": True,
            }

    class B:
        @staticmethod
        def _job_tree_digest(path: Path) -> str:
            return tree_digests[path.name]

        @staticmethod
        def _copy_evidence_digest(source: Path, destination: Path) -> str:
            assert source.name == destination.name
            return copy_digests[source.name]

    class Supervisor:
        ATTEMPT_FILE = "attempt.json"
        RECEIPT_FILE = "receipt.json"

    P = SimpleNamespace()
    events: list[dict[str, Any]] = [
        {"kind": "attempt_started", "job_id": job_id} for job_id in started
    ]
    events.extend(
        {
            "kind": "job_synced",
            "job_id": job_id,
            "data": {
                "execution_digest": execution_digests[job_id],
                "source_tree_digest": tree_digests[job_id],
                "copy_evidence_digest": copy_digests[job_id],
            },
        }
        for job_id in synced
    )

    def attempt_row(
        supervisor: object, reader: object, job_id: str, local: Path
    ) -> dict[str, Any]:
        return {
            "attempt_receipt_sha256": f"{jobs.index(job_id) + 3000:064x}",
            "child_pid": I.ORPHAN_CHILD_PID if job_id == I.ORPHAN_JOB_ID else 1,
        }

    monkeypatch.setattr(I, "_attempt_row", attempt_row)
    return P, Plan, Launch, B, Supervisor, events, [*local_calls, *durable_calls]


def test_old_launch_validators_cover_exact_150_local_and_149_durable_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    P, Plan, Launch, B, Supervisor, events, _ = _synthetic_job_fixture(
        tmp_path, monkeypatch
    )
    local_calls: list[str] = []
    durable_calls: list[str] = []
    original_local = Launch.validate_local_completed_exp2a_job
    original_durable = Launch.reconcile_completed_exp2a_job

    def local(job_id: str, **request: Any) -> dict[str, str]:
        local_calls.append(job_id)
        return original_local(job_id, **request)

    def durable(job_id: str, **request: Any) -> dict[str, str]:
        durable_calls.append(job_id)
        return original_durable(job_id, **request)

    Launch.validate_local_completed_exp2a_job = staticmethod(local)
    Launch.reconcile_completed_exp2a_job = staticmethod(durable)
    result = I._inspect_jobs(
        P, Plan, Launch, B, Supervisor, lambda path: {}, {}, events
    )
    assert len(local_calls) == 150
    assert len(set(local_calls)) == 150
    assert len(durable_calls) == 149
    assert len(set(durable_calls)) == 149
    assert result["hidden_partial"]["file_count"] == 11
    assert result["hidden_partial"]["orphan_local_file_count"] == 15
    assert len(result["untouched_job_ids"]) == 111


def test_inspector_refuses_orphan_local_tree_other_than_fifteen_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    P, Plan, Launch, B, Supervisor, events, _ = _synthetic_job_fixture(
        tmp_path, monkeypatch
    )
    (I.OUTPUT_ROOT / "jobs" / I.ORPHAN_JOB_ID / "f14.bin").unlink()
    with pytest.raises(I.InspectorRefused, match="hidden partial"):
        I._inspect_jobs(P, Plan, Launch, B, Supervisor, lambda path: {}, {}, events)


def test_cli_emits_one_canonical_json_line_and_never_raw_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result = {
        "inspector_schema_version": 1,
        "status": "complete",
        "scientific_values_emitted": False,
        "production_mutation_performed": False,
    }
    monkeypatch.setattr(I, "_run", lambda: result)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    assert I.main() == 0
    output = capsys.readouterr().out
    assert output == json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"

    secret = "synthetic scientific detail must not be printed"
    monkeypatch.setattr(
        I,
        "_run",
        lambda: (_ for _ in ()).throw(I.InspectorRefused(secret)),
    )
    assert I.main() == 2
    refusal = capsys.readouterr().out
    assert secret not in refusal
    assert json.loads(refusal)["status"] == "refused"


def test_cli_rejects_every_argument() -> None:
    original = sys.argv
    try:
        sys.argv = [str(SCRIPT), "--output-root", "elsewhere"]
        assert I.main() == 2
    finally:
        sys.argv = original
