"""Synthetic contract tests for the D-161 postmortem completion window.

These tests model the one narrow interruption in which the lower recovery has
completed but the bootstrap worker died before publishing its terminal record.
Every path is relocated beneath ``tmp_path``.  No production record, process,
scientific result, network resource, or GPU is opened by this suite.

The valid invocation and claim are produced with the existing worker-contract
helpers from :mod:`test_week8_exp2a_recovery`.  The tests otherwise exercise
the controller's state classifier and public ``seal``/``recover`` boundaries,
so they do not prescribe a private implementation helper.
"""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import week8_exp2a_recovery as R
from test_week8_exp2a_recovery import (
    NEW_TOKEN,
    _publish_worker_contract_claim,
    _publish_worker_contract_terminal,
    _worker_contract_invocation,
    recovery_worker,
    relocated,
)


POSTMORTEM_NAME = "bootstrap-postmortem-completion.json"
@dataclass
class PostmortemScenario:
    workspace: Path
    recovery_worker: Any
    invocation: dict[str, Any]
    invocation_sha: str
    claim: dict[str, Any]
    claim_sha: str
    incident: dict[str, Any]
    material: dict[str, Any]
    stability_proof: dict[str, Any]
    authority_observations: list[tuple[bool, bool]] = field(default_factory=list)
    stability_captures: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(
        default_factory=list
    )
    stability_assertions: list[dict[str, Any]] = field(default_factory=list)
    lower_completion_calls: list[dict[str, Any]] = field(default_factory=list)
    receipt_publications: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(
        default_factory=list
    )


def _postmortem_name() -> str:
    """Fail with a focused contract message until the controller adds the name."""

    value = getattr(R, "BOOTSTRAP_POSTMORTEM_FILE", None)
    assert value == POSTMORTEM_NAME
    return value


def _postmortem_paths() -> tuple[Path, Path]:
    return R._record_paths(_postmortem_name())


def _walk(value: object) -> Iterator[object]:
    yield value
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def _contains(value: object, target: object) -> bool:
    return any(item == target for item in _walk(value))


def _nested_keys(value: object) -> list[str]:
    return [item for item in _walk(value) if isinstance(item, str)]


def _workspace_inventory(root: Path) -> dict[str, tuple[Any, ...]]:
    """Inventory files, directories, and reparse points without following them."""

    inventory: dict[str, tuple[Any, ...]] = {}
    reparse_mask = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

    def visit(directory: Path) -> None:
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                attributes = int(getattr(info, "st_file_attributes", 0))
                if entry.is_symlink() or attributes & reparse_mask:
                    try:
                        target = os.readlink(path)
                    except OSError:
                        target = "<opaque-reparse-point>"
                    inventory[relative] = ("reparse", target, attributes)
                elif stat.S_ISDIR(info.st_mode):
                    inventory[relative] = ("directory",)
                    visit(path)
                elif stat.S_ISREG(info.st_mode):
                    inventory[relative] = (
                        "file",
                        info.st_size,
                        sha256_file(path),
                        int(getattr(info, "st_nlink", 0)),
                        attributes,
                    )
                else:
                    inventory[relative] = ("other", info.st_mode)

    visit(root)
    return inventory


def _assert_refused_without_write(
    scenario: PostmortemScenario,
    action: Callable[[], object],
    *,
    match: str | None = None,
) -> None:
    before = _workspace_inventory(scenario.workspace)
    with pytest.raises(R.RecoveryRefused, match=match):
        action()
    assert _workspace_inventory(scenario.workspace) == before


def _terminal_presence_is_exactly_absent(value: object) -> bool:
    if isinstance(value, dict):
        booleans = list(value.values())
    elif isinstance(value, (list, tuple)):
        booleans = list(value)
    else:
        return False
    return len(booleans) == 2 and all(item is False for item in booleans)


def _valid_stability_proof() -> dict[str, Any]:
    """Small strict-JSON stand-in for an already classified two-snapshot proof."""

    return {
        "schema_version": R.windows_liveness.WINDOWS_LIVENESS_SCHEMA_VERSION,
        "platform": "windows",
        "protocol": "two_snapshot_python_worker_gate",
        "snapshots": [],
        "stability": {
            "verdict": "pass",
            "controller_same_process": True,
            "owners_absent_twice": True,
            "all_recorded_processes_dead_twice": True,
            "all_visible_descendants_dead_twice": True,
            "no_other_live_or_ambiguous_python_twice": True,
            "no_recorded_chain_ambiguity_twice": True,
            "refusal_reasons": [],
        },
    }


@pytest.fixture
def postmortem_scenario(
    relocated: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_worker: Any,
) -> PostmortemScenario:
    invocation, invocation_sha = _worker_contract_invocation(
        relocated, recovery_worker
    )
    claim, claim_sha = _publish_worker_contract_claim(
        recovery_worker,
        invocation,
        invocation_sha,
        twins=2,
    )
    incident = {
        "record_digest": "a" * 64,
        "inventory_digest": "b" * 64,
        "authority": invocation["authority"],
    }
    material = {
        "counts": dict(R.EXPECTED_RECOVERY_COUNTS),
        "new_token": NEW_TOKEN,
        "checkpoints": {
            "c" * 32: {
                "path": str((relocated / "old-checkpoint.json").resolve()),
                "copy_path": str(
                    (relocated / "old-checkpoint-copy.json").resolve()
                ),
                "sha256": "1" * 64,
                "checkpoint_digest": "2" * 64,
            },
            NEW_TOKEN: {
                "path": str((relocated / "new-checkpoint.json").resolve()),
                "copy_path": str(
                    (relocated / "new-checkpoint-copy.json").resolve()
                ),
                "sha256": "3" * 64,
                "checkpoint_digest": "4" * 64,
            },
        },
        "events": {
            "count": R.EXPECTED_FINAL_COUNTS["events"],
            "chain_digest": "5" * 64,
            "old_prefix_chain_digest": R.EXPECTED_HASHES["old_event_stream"],
            "failure_count": 0,
        },
        "jobs": {
            "local_completed": 261,
            "durable_completed": 261,
            "old_completed_unchanged": 150,
            "tree_digest_set": "6" * 64,
        },
        "lower_report": {
            "path": str((relocated / "report.json").resolve()),
            "copy_path": str((relocated / "report-copy.json").resolve()),
            "sha256": "b" * 64,
            "record_digest": "7" * 64,
            "released_lease": True,
        },
        "transition": {
            "record_digest": "8" * 64,
            "file_sha256": "9" * 64,
        },
    }
    proof = _valid_stability_proof()
    scenario = PostmortemScenario(
        workspace=relocated,
        recovery_worker=recovery_worker,
        invocation=invocation,
        invocation_sha=invocation_sha,
        claim=claim,
        claim_sha=claim_sha,
        incident=incident,
        material=material,
        stability_proof=proof,
    )

    # The completion payload hashes the incident's first twin.  Its full
    # historical validation remains mocked at the explicit adjudication seam.
    for path in R._record_paths(R.INCIDENT_FILE):
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, {"synthetic": "incident-file"})

    monkeypatch.setattr(
        R,
        "_load_bootstrap_invocation",
        lambda: (scenario.invocation, scenario.invocation_sha),
    )
    monkeypatch.setattr(
        R,
        "_load_adjudication",
        lambda: (scenario.incident, "d" * 64, {}, "e" * 64),
    )
    monkeypatch.setattr(
        R,
        "_claimed_worker_lifecycle",
        lambda value, process=None: "dead",
    )
    monkeypatch.setattr(
        R,
        "_lower_reports",
        lambda: {
            NEW_TOKEN: (
                Path(scenario.material["lower_report"]["path"]),
                Path(scenario.material["lower_report"]["copy_path"]),
                {"status": "complete"},
                scenario.material["lower_report"]["sha256"],
            )
        },
    )

    def assert_authority(value: dict[str, Any]) -> dict[str, Any]:
        assert value is scenario.incident
        constant = getattr(R, "BOOTSTRAP_POSTMORTEM_FILE", None)
        presence = (
            (False, False)
            if constant is None
            else tuple(os.path.lexists(path) for path in R._record_paths(constant))
        )
        scenario.authority_observations.append(presence)  # type: ignore[arg-type]
        return value["authority"]

    monkeypatch.setattr(R, "_assert_current_controller_authority", assert_authority)
    monkeypatch.setattr(
        R,
        "_controller_process_attestation",
        lambda authority: dict(scenario.invocation["controller_process"]),
    )

    def validate_lower(value: dict[str, Any]) -> dict[str, Any]:
        assert value is scenario.incident
        scenario.lower_completion_calls.append(value)
        return scenario.material

    monkeypatch.setattr(R, "_validate_lower_completion", validate_lower)

    def capture_stability(
        recorded: object, **kwargs: Any
    ) -> dict[str, Any]:
        rows = tuple(recorded)  # type: ignore[arg-type]
        scenario.stability_captures.append((rows, dict(kwargs)))
        assert len(rows) == 1
        row = rows[0]
        worker = scenario.claim["worker"]["process"]
        assert row.record_id == "epoch002_bootstrap_worker"
        assert row.pid == worker["pid"]
        assert row.creation_time_filetime == worker["creation_time_100ns"]
        assert Path(row.executable_path).resolve() == Path(
            worker["kernel_executable_path"]
        ).resolve()
        assert kwargs.get("controller_pid") == os.getpid()
        expected_worker = {
            "record_id": row.record_id,
            "pid": row.pid,
            "role": row.role,
            "creation_time_filetime": str(row.creation_time_filetime),
            "executable_path": row.executable_path,
        }
        controller_pid = scenario.invocation["controller_process"]["pid"]
        controller_process = scenario.invocation["controller_process"]
        pinned_path = scenario.invocation["authority"]["pinned_python"]["path"]
        scenario.stability_proof["expected_controller_sys_executable_path"] = (
            pinned_path
        )
        scenario.stability_proof["snapshots"] = [
            {
                "observation_index": index,
                "synthetic": True,
                "recorded_processes": [expected_worker],
                "controller": {
                    "pid": controller_pid,
                    "declared_sys_executable_path": pinned_path,
                },
                "classification": {
                    "controller": {
                        "pid": controller_pid,
                        "declared_sys_executable_path": pinned_path,
                        "observed_creation_time_filetime": str(
                            controller_process["creation_time_100ns"]
                        ),
                        "observed_executable_path": controller_process[
                            "kernel_executable_path"
                        ],
                        "classification": "running",
                    }
                },
            }
            for index in (1, 2)
        ]
        return scenario.stability_proof

    def assert_stability(report: dict[str, Any]) -> dict[str, Any]:
        assert report == scenario.stability_proof
        scenario.stability_assertions.append(report)
        return report

    monkeypatch.setattr(
        R.windows_liveness,
        "capture_windows_process_stability",
        capture_stability,
    )
    monkeypatch.setattr(
        R.windows_liveness,
        "assert_windows_stability_gate",
        assert_stability,
    )
    monkeypatch.setattr(
        R,
        "_load_transition_completion",
        lambda: ({"record_digest": "8" * 64}, "9" * 64),
    )
    monkeypatch.setattr(
        R.P,
        "_load_control",
        lambda commit, monitor_only=True: {"_file_sha256": "f" * 64},
    )
    monkeypatch.setattr(R.P, "_receipt_present", lambda phase: False)

    def publish_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        scenario.receipt_publications.append((args, kwargs))
        return {"receipt_digest": "1" * 64}

    monkeypatch.setattr(R.P, "_publish_receipt", publish_receipt)
    monkeypatch.setattr(
        R,
        "validate_completed_recovery",
        lambda payload=None: {
            "status": "complete",
            "scientific_values_emitted": False,
        },
    )
    return scenario


def test_postmortem_contract_versions_and_fixed_record_name() -> None:
    assert R.BOOTSTRAP_CONTRACT_SCHEMA_VERSION == 4
    assert R.RECOVERY_SCHEMA_VERSION == 3
    assert _postmortem_name() == POSTMORTEM_NAME


def test_lower_complete_kill_window_requires_postmortem_seal(
    postmortem_scenario: PostmortemScenario,
) -> None:
    before = _workspace_inventory(postmortem_scenario.workspace)
    state = R._bootstrap_state()
    assert state["state"] == "postmortem_seal_required"
    assert state["automatic_retry_allowed"] is False
    assert _workspace_inventory(postmortem_scenario.workspace) == before
    assert postmortem_scenario.authority_observations == [(False, False)]
    assert postmortem_scenario.lower_completion_calls == [
        postmortem_scenario.incident
    ]
    assert len(postmortem_scenario.stability_captures) == 1
    assert len(postmortem_scenario.stability_assertions) == 2
    assert all(
        proof == postmortem_scenario.stability_proof
        for proof in postmortem_scenario.stability_assertions
    )


def test_worker_death_proof_uses_the_owner_role_required_by_the_stability_gate(
    postmortem_scenario: PostmortemScenario,
) -> None:
    state = R._bootstrap_state()
    assert state["state"] == "postmortem_seal_required"
    rows, _ = postmortem_scenario.stability_captures[0]
    assert len(rows) == 1
    assert rows[0].record_id == "epoch002_bootstrap_worker"
    assert rows[0].role == "owner"


def test_seal_publishes_exact_postmortem_then_recovery_completion(
    postmortem_scenario: PostmortemScenario,
) -> None:
    result = R.seal()
    assert result["status"] == "complete"

    left, right = _postmortem_paths()
    assert left.is_file() and right.is_file()
    assert not os.path.samefile(left, right)
    assert left.read_bytes() == right.read_bytes()
    postmortem = read_json(left)
    assert postmortem == read_json(right)
    assert postmortem["recovery_schema_version"] == 3
    assert postmortem["bootstrap_schema_version"] == 4
    assert postmortem["record_type"] == "bootstrap_postmortem_completion"
    assert postmortem["status"] == "complete_without_worker_terminal"
    assert postmortem["automatic_retry_allowed"] is False
    assert postmortem["scientific_outcomes_consulted"] is False
    assert postmortem["scientific_values_emitted"] is False
    assert postmortem["invocation"] == R._record_binding(
        postmortem_scenario.invocation,
        postmortem_scenario.invocation_sha,
    )
    assert postmortem["claim"] == {
        **R._record_binding(
            postmortem_scenario.claim,
            postmortem_scenario.claim_sha,
        ),
        "twins_complete": True,
    }
    assert _terminal_presence_is_exactly_absent(postmortem["terminal_presence"])
    assert not any(os.path.lexists(path) for path in R._record_paths(R.BOOTSTRAP_TERMINAL_FILE))

    capture = postmortem["output_capture"]
    assert capture["availability"] == "unavailable"
    assert isinstance(capture["reason"], str) and capture["reason"]
    assert "worker" in capture["reason"] and "terminal" in capture["reason"]
    assert capture["stdout"] is None
    assert capture["stderr"] is None
    assert "sha256" not in _nested_keys(capture)
    assert "terminal" not in postmortem

    material_digest = R.sha256_bytes(R._canonical(postmortem_scenario.material))
    assert _contains(postmortem, material_digest)
    assert _contains(postmortem, postmortem_scenario.material["counts"])
    assert _contains(postmortem, postmortem_scenario.material["new_token"])
    assert _contains(
        postmortem,
        postmortem_scenario.material["lower_report"]["sha256"],
    )
    assert _contains(postmortem, postmortem_scenario.stability_proof)
    authority_digest = R.sha256_bytes(
        R._canonical(postmortem_scenario.incident["authority"])
    )
    assert _contains(postmortem, authority_digest)
    assert postmortem_scenario.authority_observations
    assert postmortem_scenario.authority_observations[0] == (False, False)

    state = R._bootstrap_state()
    assert state["state"] == "postmortem_complete"
    binding = R._validate_completed_bootstrap(postmortem_scenario.material)
    assert _contains(binding, postmortem["record_digest"])
    assert _contains(binding, sha256_file(left))

    completion_left, completion_right = R._record_paths(R.RECOVERY_COMPLETION_FILE)
    assert completion_left.is_file() and completion_right.is_file()
    assert not os.path.samefile(completion_left, completion_right)
    completion = read_json(completion_left)
    assert completion == read_json(completion_right)
    assert completion["recovery_schema_version"] == 3
    assert _contains(completion["bootstrap"], postmortem["record_digest"])
    assert _contains(completion["bootstrap"], sha256_file(left))


def test_authority_drift_refuses_before_postmortem_write(
    postmortem_scenario: PostmortemScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def drift(value: object) -> dict[str, Any]:
        raise R.RecoveryRefused("current controller authority differs")

    monkeypatch.setattr(R, "_assert_current_controller_authority", drift)
    _assert_refused_without_write(
        postmortem_scenario,
        R.seal,
        match="authority differs",
    )


@pytest.mark.parametrize("classification", ("live", "ambiguous"))
def test_live_or_ambiguous_worker_refuses_before_postmortem_write(
    postmortem_scenario: PostmortemScenario,
    monkeypatch: pytest.MonkeyPatch,
    classification: str,
) -> None:
    postmortem_scenario.stability_proof["stability"] = {
        "verdict": "refuse",
        "refusal_reasons": [f"synthetic_worker_{classification}"],
    }

    def refuse(report: object) -> dict[str, Any]:
        raise R.windows_liveness.ProcessLivenessError(
            f"bootstrap worker is {classification}"
        )

    monkeypatch.setattr(
        R.windows_liveness,
        "assert_windows_stability_gate",
        refuse,
    )
    _assert_refused_without_write(postmortem_scenario, R.seal)


@pytest.mark.parametrize("runtime_state", ("missing", "nonempty", "reparse"))
def test_runtime_temp_must_already_be_plain_and_exactly_empty(
    postmortem_scenario: PostmortemScenario,
    runtime_state: str,
) -> None:
    runtime = R.RUNTIME_TEMP
    if runtime_state == "missing":
        runtime.rmdir()
    elif runtime_state == "nonempty":
        (runtime / "residual.bin").write_bytes(b"worker-residual")
    else:
        runtime.rmdir()
        target = postmortem_scenario.workspace / "synthetic-reparse-target"
        target.mkdir()
        try:
            os.symlink(target, runtime, target_is_directory=True)
        except OSError:
            command = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d",
                "/c",
                "mklink",
                "/J",
                str(runtime),
                str(target),
            ]
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                pytest.skip("this host cannot create a synthetic directory reparse point")
    _assert_refused_without_write(postmortem_scenario, R.seal)


def test_empty_runtime_temp_replacement_is_identity_drift(
    postmortem_scenario: PostmortemScenario,
) -> None:
    runtime = R.RUNTIME_TEMP
    recorded = dict(postmortem_scenario.invocation["runtime_temp"])
    runtime.rmdir()
    runtime.mkdir()
    replacement = R._runtime_temp_directory_identity(
        runtime, what="replacement synthetic runtime temp"
    )
    if replacement == recorded:
        pytest.skip("host filesystem did not expose replacement-directory identity")
    _assert_refused_without_write(
        postmortem_scenario,
        R.seal,
        match="identity changed",
    )


def test_incomplete_lower_completion_refuses_before_postmortem_write(
    postmortem_scenario: PostmortemScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def incomplete(value: object) -> dict[str, Any]:
        raise R.RecoveryRefused("lower completion is incomplete")

    monkeypatch.setattr(R, "_validate_lower_completion", incomplete)
    _assert_refused_without_write(
        postmortem_scenario,
        R.seal,
    )


def _partial_postmortem_document() -> dict[str, Any]:
    return R._seal(
        {
            **R._base_record("bootstrap_postmortem_completion"),
            "bootstrap_schema_version": 4,
            "status": "complete_without_worker_terminal",
            "automatic_retry_allowed": False,
        }
    )


def test_partial_postmortem_twin_is_a_permanent_refusal_without_repair(
    postmortem_scenario: PostmortemScenario,
) -> None:
    left, _ = _postmortem_paths()
    left.parent.mkdir(parents=True, exist_ok=True)
    partial = _partial_postmortem_document()
    atomic_write_json(left, partial)
    _assert_refused_without_write(postmortem_scenario, R.seal)


def test_hardlinked_partial_postmortem_twin_is_a_permanent_refusal(
    postmortem_scenario: PostmortemScenario,
) -> None:
    left, _ = _postmortem_paths()
    left.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(left, _partial_postmortem_document())
    alias = postmortem_scenario.workspace / "postmortem-hardlink-alias.json"
    os.link(left, alias)
    _assert_refused_without_write(
        postmortem_scenario,
        R.seal,
        match="independent plain file",
    )


def test_reparse_partial_postmortem_twin_is_a_permanent_refusal(
    postmortem_scenario: PostmortemScenario,
) -> None:
    left, _ = _postmortem_paths()
    left.parent.mkdir(parents=True, exist_ok=True)
    target = postmortem_scenario.workspace / "postmortem-reparse-target.json"
    atomic_write_json(target, _partial_postmortem_document())
    try:
        os.symlink(target, left, target_is_directory=False)
    except OSError as exc:
        pytest.skip(f"host cannot create a file reparse point: {exc}")
    _assert_refused_without_write(
        postmortem_scenario,
        R.seal,
        match="independent plain file",
    )


def test_postmortem_and_worker_terminal_conflict_is_a_permanent_refusal(
    postmortem_scenario: PostmortemScenario,
) -> None:
    R.seal()
    _publish_worker_contract_terminal(
        postmortem_scenario.recovery_worker,
        postmortem_scenario.invocation,
        postmortem_scenario.invocation_sha,
        postmortem_scenario.claim,
        postmortem_scenario.claim_sha,
        claim_twins_complete=True,
        terminal_twins=2,
        status="complete",
    )
    _assert_refused_without_write(postmortem_scenario, R.seal)


@pytest.mark.parametrize("tamper", ("digest", "fabricated-output"))
def test_malformed_or_tampered_postmortem_is_never_trusted_or_rewritten(
    postmortem_scenario: PostmortemScenario,
    tamper: str,
) -> None:
    R.seal()
    left, right = _postmortem_paths()
    document = read_json(left)
    payload = {
        key: value for key, value in document.items() if key != "record_digest"
    }
    if tamper == "digest":
        payload["status"] = "tampered"
        malformed = {**payload, "record_digest": document["record_digest"]}
    else:
        payload["output_capture"] = {
            "availability": "available",
            "reason": "fabricated-after-worker-death",
            "stdout": {"sha256": "1" * 64},
            "stderr": {"sha256": "2" * 64},
        }
        malformed = R._seal(payload)
    # Deliberately emulate out-of-band corruption of already immutable evidence.
    # The durable writer correctly refuses overwrites, so corruption must bypass
    # that API in this synthetic adversarial test.
    malformed_bytes = R._canonical(malformed) + b"\n"
    left.write_bytes(malformed_bytes)
    right.write_bytes(malformed_bytes)
    _assert_refused_without_write(postmortem_scenario, R._bootstrap_state)


def test_recover_cannot_retry_the_postmortem_seal_required_window(
    postmortem_scenario: PostmortemScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_presence = R._record_presence

    def presence(name: str) -> bool:
        if name in {R.TRANSITION_INTENT_FILE, R.TRANSITION_COMPLETION_FILE}:
            return True
        return original_presence(name)

    monkeypatch.setattr(R, "_record_presence", presence)
    monkeypatch.setattr(
        R,
        "_invoke_bootstrap",
        lambda: pytest.fail("postmortem evidence must never launch a retry"),
    )
    _assert_refused_without_write(postmortem_scenario, R.recover)
