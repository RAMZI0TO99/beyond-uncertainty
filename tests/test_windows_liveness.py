"""Synthetic, platform-safe tests for Windows recovery liveness evidence."""

from __future__ import annotations

import copy
import ctypes
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence

import pytest

import bu.experiments.windows_liveness as liveness
from bu.experiments.windows_liveness import (
    ProcessLivenessError,
    RecordedProcess,
    assert_windows_stability_gate,
    capture_windows_process_identity,
    capture_windows_process_snapshot,
    capture_windows_process_stability,
    classify_windows_process_snapshot,
    classify_windows_process_stability,
)


CONTROLLER_PID = 100
CONTROLLER_PATH = r"C:\recovery\.venv\Scripts\python.exe"
BASE_PYTHON_PATH = r"C:\Python313\python.exe"
LAUNCHER_PID = 50


def process(pid: int, parent_pid: int, exe_name: str) -> dict[str, object]:
    return {"pid": pid, "parent_pid": parent_pid, "exe_name": exe_name}


def probe(
    pid: int,
    status: str,
    *,
    creation: int | None = None,
    path: str | None = None,
    error_stage: str | None = None,
    winerror: int | None = None,
    close_winerror: int | None = None,
) -> dict[str, object]:
    wait_code = {
        "running": liveness.WAIT_TIMEOUT,
        "signaled": liveness.WAIT_OBJECT_0,
    }.get(status)
    if status == "not_found":
        error_stage = "OpenProcess"
        winerror = liveness.ERROR_INVALID_PARAMETER
    return {
        "pid": pid,
        "status": status,
        "creation_time_filetime": None if creation is None else str(creation),
        "executable_path": path,
        "wait_code": wait_code,
        "error_stage": error_stage,
        "winerror": winerror,
        "close_winerror": close_winerror,
    }


def running_probe(
    pid: int,
    creation: int,
    path: str = CONTROLLER_PATH,
) -> dict[str, object]:
    return probe(pid, "running", creation=creation, path=path)


def test_kernel_identity_defaults_to_current_pid(monkeypatch):
    current_pid = 321
    kernel_path = r"C:\Python313\python.exe"
    api = FakeProcessApi(
        [],
        {current_pid: running_probe(current_pid, 123456789, kernel_path)},
    )
    monkeypatch.setattr(liveness.os, "getpid", lambda: current_pid)

    identity = capture_windows_process_identity(_api=api)

    assert identity == {
        "pid": current_pid,
        "kernel_executable_path": kernel_path,
        "creation_time_100ns": 123456789,
    }
    assert set(identity) == {
        "pid",
        "kernel_executable_path",
        "creation_time_100ns",
    }
    assert api.queried == [current_pid]


def test_kernel_identity_probes_the_exact_explicit_pid():
    pid = 654
    kernel_path = r"\\server\share\python.exe"
    api = FakeProcessApi([], {pid: running_probe(pid, 987654321, kernel_path)})

    identity = capture_windows_process_identity(pid, _api=api)

    assert identity == {
        "pid": pid,
        "kernel_executable_path": kernel_path,
        "creation_time_100ns": 987654321,
    }
    assert api.queried == [pid]


@pytest.mark.parametrize(
    ("status", "kwargs"),
    [
        ("not_found", {}),
        ("signaled", {"creation": 1000, "path": CONTROLLER_PATH}),
        (
            "error",
            {"error_stage": "GetProcessTimes", "winerror": 5},
        ),
        (
            "error",
            {
                "error_stage": "CloseHandle",
                "winerror": 6,
                "close_winerror": 6,
            },
        ),
    ],
)
def test_kernel_identity_refuses_every_nonrunning_outcome(status, kwargs):
    pid = 321
    api = FakeProcessApi([], {pid: probe(pid, status, **kwargs)})

    with pytest.raises(ProcessLivenessError, match="requires a running process"):
        capture_windows_process_identity(pid, _api=api)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("wait_code"),
        lambda value: value.update(pid=999),
        lambda value: value.update(creation_time_filetime="0001"),
        lambda value: value.update(creation_time_filetime="0"),
        lambda value: value.update(creation_time_filetime=1000),
        lambda value: value.update(creation_time_filetime=str(1 << 64)),
        lambda value: value.update(executable_path="python.exe"),
        lambda value: value.update(executable_path=r"\python.exe"),
        lambda value: value.update(executable_path="/python.exe"),
        lambda value: value.update(executable_path=""),
        lambda value: value.update(executable_path="C:\\bad\x00python.exe"),
        lambda value: value.update(wait_code=liveness.WAIT_OBJECT_0),
        lambda value: value.update(close_winerror=6),
    ],
)
def test_kernel_identity_refuses_malformed_or_noncanonical_evidence(mutation):
    pid = 321
    observation = running_probe(pid, 1000, CONTROLLER_PATH)
    mutation(observation)
    api = FakeProcessApi([], {pid: observation})

    with pytest.raises(ProcessLivenessError):
        capture_windows_process_identity(pid, _api=api)


@pytest.mark.parametrize("bad_pid", [True, False, 0, -1, 1 << 32, "321", 1.0])
def test_kernel_identity_refuses_invalid_pid_before_api_access(bad_pid):
    api = FakeProcessApi([], {})

    with pytest.raises(ProcessLivenessError, match="exact positive DWORD"):
        capture_windows_process_identity(bad_pid, _api=api)
    assert api.queried == []


def test_kernel_identity_wraps_backend_exceptions_as_closed_refusal():
    class RaisingApi:
        def probe_process(self, pid):
            raise OSError(f"planted failure for {pid}")

    with pytest.raises(ProcessLivenessError, match="kernel identity probe") as caught:
        capture_windows_process_identity(321, _api=RaisingApi())
    assert isinstance(caught.value.__cause__, OSError)


def test_kernel_identity_has_no_production_path_override():
    pid = 321
    kernel_path = r"C:\kernel-reported\python.exe"
    api = FakeProcessApi([], {pid: running_probe(pid, 1000, kernel_path)})

    with pytest.raises(TypeError, match="unexpected keyword"):
        capture_windows_process_identity(
            pid,
            _api=api,
            _kernel_executable_path=r"C:\forged\python.exe",
        )

    assert api.queried == []


class FakeProcessApi:
    def __init__(
        self,
        entries: Sequence[Mapping[str, object]],
        probes: Mapping[int, Mapping[str, object]],
    ) -> None:
        self.entries = [dict(entry) for entry in entries]
        self.probes = {pid: dict(value) for pid, value in probes.items()}
        self.queried: list[int] = []

    def enumerate_processes(self) -> list[dict[str, object]]:
        return copy.deepcopy(self.entries)

    def probe_process(self, pid: int) -> dict[str, object]:
        self.queried.append(pid)
        return copy.deepcopy(self.probes[pid])


class SequencedFakeProcessApi:
    """Expose one synthetic process table per Toolhelp capture."""

    def __init__(
        self,
        rounds: Sequence[
            tuple[
                Sequence[Mapping[str, object]],
                Mapping[int, Mapping[str, object]],
            ]
        ],
    ) -> None:
        self.rounds = [
            (
                [dict(entry) for entry in entries],
                {pid: dict(probe_value) for pid, probe_value in probes.items()},
            )
            for entries, probes in rounds
        ]
        self.enumeration_count = 0
        self.active_round = -1
        self.queried_by_round: list[list[int]] = []

    def enumerate_processes(self) -> list[dict[str, object]]:
        if self.enumeration_count >= len(self.rounds):
            raise AssertionError("unexpected extra Toolhelp capture")
        self.active_round = self.enumeration_count
        self.enumeration_count += 1
        self.queried_by_round.append([])
        return copy.deepcopy(self.rounds[self.active_round][0])

    def probe_process(self, pid: int) -> dict[str, object]:
        if self.active_round < 0:
            raise AssertionError("probe occurred before Toolhelp capture")
        self.queried_by_round[self.active_round].append(pid)
        return copy.deepcopy(self.rounds[self.active_round][1][pid])


def base_entries() -> list[dict[str, object]]:
    return [
        process(400, 4, "explorer.exe"),
        process(CONTROLLER_PID, 50, "python.exe"),
        process(50, 4, "powershell.exe"),
        process(4, 0, "System"),
    ]


def launcher_entries(
    *, launcher_pid: int = LAUNCHER_PID, launcher_name: str = "python.exe"
) -> list[dict[str, object]]:
    return [
        process(400, 4, "explorer.exe"),
        process(CONTROLLER_PID, launcher_pid, "python.exe"),
        process(launcher_pid, 4, launcher_name),
        process(4, 0, "System"),
    ]


def base_probes(**extra: Mapping[str, object]) -> dict[int, Mapping[str, object]]:
    result: dict[int, Mapping[str, object]] = {
        CONTROLLER_PID: running_probe(CONTROLLER_PID, 1000),
    }
    result.update({int(pid): value for pid, value in extra.items()})
    return result


def capture(
    recorded: Sequence[RecordedProcess],
    entries: Sequence[Mapping[str, object]],
    probes: Mapping[int, Mapping[str, object]],
    *,
    controller_sys_executable_path: str = CONTROLLER_PATH,
) -> tuple[dict[str, object], FakeProcessApi]:
    api = FakeProcessApi(entries, probes)
    snapshot = capture_windows_process_snapshot(
        recorded,
        controller_pid=CONTROLLER_PID,
        _api=api,
        _controller_sys_executable_path=controller_sys_executable_path,
    )
    return snapshot, api


def capture_stability(
    recorded: Sequence[RecordedProcess],
    rounds: Sequence[
        tuple[
            Sequence[Mapping[str, object]],
            Mapping[int, Mapping[str, object]],
        ]
    ],
    *,
    controller_sys_executable_path: str = CONTROLLER_PATH,
) -> tuple[dict[str, object], SequencedFakeProcessApi]:
    api = SequencedFakeProcessApi(rounds)
    report = capture_windows_process_stability(
        recorded,
        controller_pid=CONTROLLER_PID,
        _api=api,
        _controller_sys_executable_path=controller_sys_executable_path,
    )
    return report, api


def stability(report: Mapping[str, object]) -> Mapping[str, object]:
    value = report["stability"]
    assert isinstance(value, Mapping)
    return value


def classification(snapshot: Mapping[str, object]) -> Mapping[str, object]:
    value = snapshot["classification"]
    assert isinstance(value, Mapping)
    return value


def assert_fake_stability_gate(
    report: Mapping[str, object],
    *,
    expected_path: str = CONTROLLER_PATH,
) -> dict[str, object]:
    """Use the private expected-path seam only for synthetic evidence."""

    return liveness._assert_windows_stability_gate(
        report,
        expected_controller_sys_executable_path=expected_path,
    )


def recorded_rows(snapshot: Mapping[str, object]) -> list[Mapping[str, object]]:
    rows = classification(snapshot)["recorded_processes"]
    assert isinstance(rows, list)
    return rows


def test_absent_legacy_owner_is_dead_proven_and_snapshot_is_strict_json():
    owner_pid = 200
    snapshot, api = capture(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        base_entries(),
        base_probes(**{str(owner_pid): probe(owner_pid, "not_found")}),
    )

    assert api.queried == [CONTROLLER_PID, owner_pid]
    assert recorded_rows(snapshot) == [
        {
            "record_id": "lease-owner",
            "pid": owner_pid,
            "role": "owner",
            "creation_time_filetime": None,
            "executable_path": None,
            "snapshot_present": False,
            "observed_creation_time_filetime": None,
            "observed_executable_path": None,
            "classification": "dead_proven",
            "reason": "absent_from_toolhelp_and_openprocess",
            "blocks_snapshot_clear": False,
        }
    ]
    assert classification(snapshot)["verdict"] == "snapshot_clear"
    assert classification(snapshot)[
        "complete_native_descendant_absence_claimed"
    ] is False
    assert classification(snapshot)["other_python_processes"] == []
    encoded = json.dumps(snapshot, sort_keys=True, allow_nan=False)
    assert json.loads(encoded) == snapshot


def test_single_snapshot_is_explicitly_non_authorizing():
    owner_pid = 200
    snapshot, _ = capture(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        base_entries(),
        base_probes(**{str(owner_pid): probe(owner_pid, "not_found")}),
    )

    assert classification(snapshot)["verdict"] == "snapshot_clear"
    with pytest.raises(ProcessLivenessError, match="two snapshots"):
        assert_windows_stability_gate(snapshot)


def test_two_snapshot_python_worker_gate_passes_without_native_absence_claim():
    owner_pid = 200
    unrelated_native_pid = 900
    entries = base_entries() + [
        process(unrelated_native_pid, 1, "native-helper.exe")
    ]
    probes = base_probes(**{str(owner_pid): probe(owner_pid, "not_found")})
    report, api = capture_stability(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        [(entries, probes), (entries, probes)],
    )

    assert api.enumeration_count == 2
    assert api.queried_by_round == [
        [CONTROLLER_PID, owner_pid],
        [CONTROLLER_PID, owner_pid],
    ]
    result = stability(report)
    assert result["verdict"] == "pass"
    assert result["owners_absent_twice"] is True
    assert result["all_visible_descendants_dead_twice"] is True
    assert result["no_other_live_or_ambiguous_python_twice"] is True
    assert result["controller_launcher_required"] is False
    assert result["controller_launcher_stable"] is True
    assert result["controller_launcher"] is None
    assert report["complete_native_descendant_absence_claimed"] is False
    assert "cannot prove absence of arbitrary native descendants" in report[
        "native_descendant_limitation"
    ]
    assert report["python_discovery_scope"] == (
        "canonical_python_pypy_executable_leaf_names_only"
    )
    assert report["scientific_process_command_invariant"] == (
        "D-161:pinned_python.exe"
    )
    assert "does not classify arbitrary renamed native images" in report[
        "native_descendant_limitation"
    ]
    for snapshot in report["snapshots"]:
        snapshot_result = classification(snapshot)
        assert snapshot_result["python_discovery_scope"] == (
            "canonical_python_pypy_executable_leaf_names_only"
        )
        assert snapshot_result["scientific_process_command_invariant"] == (
            "D-161:pinned_python.exe"
        )
    assert result["unresolved_unrelated_ancestry"] == [
        {
            "observation_index": 1,
            "pid": unrelated_native_pid,
            "classification": "unrelated_missing",
        },
        {
            "observation_index": 2,
            "pid": unrelated_native_pid,
            "classification": "unrelated_missing",
        },
    ]
    assert assert_fake_stability_gate(report) == report


def test_stable_direct_parent_venv_launcher_is_the_only_python_exemption():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, api = capture_stability(
        [owner],
        [(launcher_entries(), probes), (launcher_entries(), probes)],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    assert api.queried_by_round == [
        [LAUNCHER_PID, CONTROLLER_PID, owner_pid],
        [LAUNCHER_PID, CONTROLLER_PID, owner_pid],
    ]
    for snapshot in report["snapshots"]:
        snapshot_result = classification(snapshot)
        candidate = snapshot_result["controller_launcher_candidate"]
        assert candidate["pid"] == LAUNCHER_PID
        assert candidate["relation"] == "controller_launcher_candidate"
        assert snapshot_result["other_python_processes"] == []
        launcher_row = next(
            row
            for row in snapshot_result["python_processes"]
            if row["pid"] == LAUNCHER_PID
        )
        assert launcher_row["relation"] == "controller_launcher_candidate"

    result = stability(report)
    assert result["controller_launcher_required"] is True
    assert result["controller_launcher_stable"] is True
    assert result["controller_launcher"] == {
        "pid": LAUNCHER_PID,
        "controller_pid": CONTROLLER_PID,
        "observed_creation_time_filetime": "500",
        "observed_executable_path": CONTROLLER_PATH,
        "normalized_executable_path": (
            r"c:\recovery\.venv\scripts\python.exe"
        ),
        "classification": "live",
        "relation": "controller_launcher",
        "reason": "stable_direct_parent_venv_launcher",
    }
    assert result["verdict"] == "pass"


def test_launcher_created_at_same_filetime_as_controller_is_ambiguous_and_refuses():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 1000, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }

    report, _ = capture_stability(
        [owner],
        [(launcher_entries(), probes), (launcher_entries(), probes)],
    )

    for snapshot in report["snapshots"]:
        snapshot_result = classification(snapshot)
        assert snapshot_result["controller_launcher_candidate"] is None
        assert snapshot_result["controller_launcher_rejection_reason"] == (
            "direct_parent_creation_not_before_controller_pid_reuse_ambiguous"
        )
        assert snapshot_result["other_python_processes"] == [LAUNCHER_PID]
    result = stability(report)
    assert result["controller_launcher_stable"] is False
    assert result["no_other_live_or_ambiguous_python_twice"] is False
    assert result["verdict"] == "refuse"


def test_launcher_newer_than_controller_is_pid_reuse_and_refuses():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 1001, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }

    report, _ = capture_stability(
        [owner],
        [(launcher_entries(), probes), (launcher_entries(), probes)],
    )

    for snapshot in report["snapshots"]:
        snapshot_result = classification(snapshot)
        assert snapshot_result["controller_launcher_candidate"] is None
        assert snapshot_result["controller_launcher_rejection_reason"] == (
            "direct_parent_creation_not_before_controller_pid_reuse_ambiguous"
        )
        assert snapshot_result["other_python_processes"] == [LAUNCHER_PID]
        assert (
            "controller_launcher:"
            "direct_parent_creation_not_before_controller_pid_reuse_ambiguous"
            in snapshot_result["refusal_reasons"]
        )
    result = stability(report)
    assert result["controller_launcher_stable"] is False
    assert result["no_other_live_or_ambiguous_python_twice"] is False
    assert result["verdict"] == "refuse"


@pytest.mark.parametrize(
    "capture_call",
    [
        lambda: capture_windows_process_snapshot(
            [],
            controller_pid=CONTROLLER_PID,
            _controller_sys_executable_path=CONTROLLER_PATH,
        ),
        lambda: capture_windows_process_stability(
            [],
            controller_pid=CONTROLLER_PID,
            _controller_sys_executable_path=CONTROLLER_PATH,
        ),
    ],
)
def test_production_capture_cannot_override_actual_sys_executable(capture_call):
    with pytest.raises(
        ProcessLivenessError,
        match="override is permitted only with an injected fake process API",
    ):
        capture_call()


def test_explicit_real_backend_instance_cannot_use_path_override():
    api = liveness._WindowsProcessApi.__new__(liveness._WindowsProcessApi)

    with pytest.raises(
        ProcessLivenessError,
        match="override is permitted only with an injected fake process API",
    ):
        capture_windows_process_snapshot(
            [],
            controller_pid=CONTROLLER_PID,
            _api=api,
            _controller_sys_executable_path=CONTROLLER_PATH,
        )


def test_forged_agreed_snapshot_paths_cannot_pass_public_reclassification(
    monkeypatch,
):
    owner_pid = 200
    forged_launcher_path = r"C:\forged\.venv\Scripts\python.exe"
    actual_path = r"C:\actual\.venv\Scripts\python.exe"
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, forged_launcher_path
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [(launcher_entries(), probes), (launcher_entries(), probes)],
        controller_sys_executable_path=forged_launcher_path,
    )
    assert stability(report)["verdict"] == "pass"
    assert all(
        snapshot["controller"]["declared_sys_executable_path"]
        == forged_launcher_path
        for snapshot in report["snapshots"]
    )
    monkeypatch.setattr(liveness.sys, "executable", actual_path)

    with pytest.raises(
        ProcessLivenessError,
        match="does not match the expected actual sys.executable path",
    ):
        classify_windows_process_stability(*report["snapshots"])
    with pytest.raises(
        ProcessLivenessError,
        match="does not match the expected actual sys.executable path",
    ):
        assert_windows_stability_gate(report)

    assert (
        assert_fake_stability_gate(report, expected_path=forged_launcher_path)
        == report
    )


def test_unrelated_python_still_refuses_with_valid_launcher():
    owner_pid = 200
    unrelated_pid = 300
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    entries = launcher_entries() + [process(unrelated_pid, 4, "python.exe")]
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, CONTROLLER_PATH
        ),
        unrelated_pid: running_probe(
            unrelated_pid, 3000, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [(entries, probes), (entries, probes)],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    for snapshot in report["snapshots"]:
        assert classification(snapshot)["other_python_processes"] == [
            unrelated_pid
        ]
    result = stability(report)
    assert result["controller_launcher_stable"] is True
    assert result["no_other_live_or_ambiguous_python_twice"] is False
    assert result["verdict"] == "refuse"


def test_same_path_python_that_is_not_direct_parent_is_never_exempted():
    owner_pid = 200
    same_path_pid = 300
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    entries = base_entries() + [process(same_path_pid, 4, "python.exe")]
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        same_path_pid: running_probe(
            same_path_pid, 3000, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [(entries, probes), (entries, probes)],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    result = stability(report)
    assert result["controller_launcher_required"] is True
    assert result["controller_launcher_stable"] is False
    assert result["controller_launcher"] is None
    assert result["no_other_live_or_ambiguous_python_twice"] is False
    assert result["verdict"] == "refuse"


def test_ambiguous_direct_parent_is_not_a_launcher_and_refuses():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: probe(
            LAUNCHER_PID,
            "error",
            error_stage="OpenProcess",
            winerror=5,
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [(launcher_entries(), probes), (launcher_entries(), probes)],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    for snapshot in report["snapshots"]:
        snapshot_result = classification(snapshot)
        assert snapshot_result["controller_launcher_candidate"] is None
        assert snapshot_result["ambiguous_python_processes"] == [LAUNCHER_PID]
    result = stability(report)
    assert result["controller_launcher_stable"] is False
    assert result["verdict"] == "refuse"


def test_launcher_creation_identity_drift_between_snapshots_refuses():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    first_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    second_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 501, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [
            (launcher_entries(), first_probes),
            (launcher_entries(), second_probes),
        ],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    result = stability(report)
    assert result["controller_launcher_stable"] is False
    assert result["controller_launcher"] is None
    assert (
        "stability:controller_launcher_missing_ambiguous_or_drifted"
        in result["refusal_reasons"]
    )
    assert result["verdict"] == "refuse"


def test_launcher_pid_drift_between_snapshots_refuses():
    owner_pid = 200
    second_launcher_pid = 51
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    first_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    second_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        second_launcher_pid: running_probe(
            second_launcher_pid, 500, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [
            (launcher_entries(), first_probes),
            (
                launcher_entries(launcher_pid=second_launcher_pid),
                second_probes,
            ),
        ],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    result = stability(report)
    assert result["controller_launcher_stable"] is False
    assert result["controller_launcher"] is None
    assert result["verdict"] == "refuse"


def test_launcher_kernel_path_drift_between_snapshots_refuses():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    first_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    second_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, r"D:\different\python.exe"
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [
            (launcher_entries(), first_probes),
            (launcher_entries(), second_probes),
        ],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    second = classification(report["snapshots"][1])
    assert second["controller_launcher_candidate"] is None
    assert second["other_python_processes"] == [LAUNCHER_PID]
    result = stability(report)
    assert result["controller_launcher_stable"] is False
    assert result["verdict"] == "refuse"


def test_launcher_must_be_live_and_present_in_both_snapshots():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    first_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    second_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: probe(
            LAUNCHER_PID,
            "signaled",
            creation=500,
            path=CONTROLLER_PATH,
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [
            (launcher_entries(), first_probes),
            (launcher_entries(), second_probes),
        ],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    result = stability(report)
    assert result["controller_launcher_stable"] is False
    assert result["verdict"] == "refuse"


def test_launcher_path_normalization_accepts_only_equivalent_paths():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    declared = r"C:\Recovery\.VENV\Scripts\python.exe"
    first_path = r"c:/recovery/.venv/scripts/PYTHON.EXE"
    second_path = r"C:\RECOVERY\.VENV\SCRIPTS\python.exe"
    first_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(LAUNCHER_PID, 500, first_path),
        owner_pid: probe(owner_pid, "not_found"),
    }
    second_probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(LAUNCHER_PID, 500, second_path),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [
            (launcher_entries(), first_probes),
            (launcher_entries(), second_probes),
        ],
        controller_sys_executable_path=declared,
    )

    result = stability(report)
    assert result["controller_launcher_stable"] is True
    assert result["verdict"] == "pass"


def test_recorded_process_pid_cannot_be_exempted_as_controller_launcher():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    recorded_parent = RecordedProcess(
        "recorded-parent", LAUNCHER_PID, 500, CONTROLLER_PATH
    )
    probes = {
        CONTROLLER_PID: running_probe(
            CONTROLLER_PID, 1000, BASE_PYTHON_PATH
        ),
        LAUNCHER_PID: running_probe(
            LAUNCHER_PID, 500, CONTROLLER_PATH
        ),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner, recorded_parent],
        [(launcher_entries(), probes), (launcher_entries(), probes)],
        controller_sys_executable_path=CONTROLLER_PATH,
    )

    for snapshot in report["snapshots"]:
        assert classification(snapshot)["controller_launcher_candidate"] is None
        assert classification(snapshot)["other_python_processes"] == [
            LAUNCHER_PID
        ]
    assert stability(report)["verdict"] == "refuse"


def test_owner_merely_signaled_in_first_snapshot_does_not_close_spawn_race():
    owner_pid = 200
    owner_path = r"C:\recovery\owner.exe"
    owner = RecordedProcess(
        "lease-owner", owner_pid, 2000, owner_path, role="owner"
    )
    first_entries = base_entries() + [process(owner_pid, 4, "owner.exe")]
    first_probes = base_probes(
        **{
            str(owner_pid): probe(
                owner_pid,
                "signaled",
                creation=2000,
                path=owner_path,
            )
        }
    )
    second_probes = base_probes(
        **{str(owner_pid): probe(owner_pid, "not_found")}
    )
    report, _ = capture_stability(
        [owner],
        [(first_entries, first_probes), (base_entries(), second_probes)],
    )

    snapshots = report["snapshots"]
    assert classification(snapshots[0])["verdict"] == "snapshot_clear"
    assert classification(snapshots[1])["verdict"] == "snapshot_clear"
    result = stability(report)
    assert result["owners_absent_twice"] is False
    assert result["verdict"] == "refuse"
    assert (
        "stability:owner:lease-owner:not_absent_in_snapshot_1"
        in result["refusal_reasons"]
    )


def test_owner_absent_first_but_present_second_refuses():
    owner_pid = 200
    owner_path = r"C:\recovery\owner.exe"
    owner = RecordedProcess(
        "lease-owner", owner_pid, 2000, owner_path, role="owner"
    )
    first_probes = base_probes(
        **{str(owner_pid): probe(owner_pid, "not_found")}
    )
    second_entries = base_entries() + [process(owner_pid, 4, "owner.exe")]
    second_probes = base_probes(
        **{
            str(owner_pid): running_probe(owner_pid, 2000, owner_path)
        }
    )
    report, _ = capture_stability(
        [owner],
        [(base_entries(), first_probes), (second_entries, second_probes)],
    )

    result = stability(report)
    assert result["owners_absent_twice"] is False
    assert result["verdict"] == "refuse"
    assert (
        "stability:owner:lease-owner:not_absent_in_snapshot_2"
        in result["refusal_reasons"]
    )


def test_other_python_appearing_in_second_snapshot_refuses_stability():
    owner_pid = 200
    other_pid = 300
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    first_probes = base_probes(
        **{str(owner_pid): probe(owner_pid, "not_found")}
    )
    second_entries = base_entries() + [process(other_pid, 50, "python_d.exe")]
    second_probes = base_probes(
        **{
            str(owner_pid): probe(owner_pid, "not_found"),
            str(other_pid): running_probe(
                other_pid, 3000, r"C:\Python313\python_d.exe"
            ),
        }
    )
    report, _ = capture_stability(
        [owner],
        [(base_entries(), first_probes), (second_entries, second_probes)],
    )

    result = stability(report)
    assert result["no_other_live_or_ambiguous_python_twice"] is False
    assert result["verdict"] == "refuse"


def test_controller_must_be_same_kernel_process_in_both_snapshots():
    owner_pid = 200
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    first_probes = {
        CONTROLLER_PID: running_probe(CONTROLLER_PID, 1000),
        owner_pid: probe(owner_pid, "not_found"),
    }
    second_probes = {
        CONTROLLER_PID: running_probe(CONTROLLER_PID, 1001),
        owner_pid: probe(owner_pid, "not_found"),
    }
    report, _ = capture_stability(
        [owner],
        [(base_entries(), first_probes), (base_entries(), second_probes)],
    )

    result = stability(report)
    assert result["controller_same_process"] is False
    assert result["verdict"] == "refuse"
    assert "stability:controller_identity_changed" in result["refusal_reasons"]


def test_live_visible_descendant_in_either_snapshot_refuses_stability():
    owner_pid = 200
    child_pid = 201
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    entries = base_entries() + [process(child_pid, owner_pid, "native-child.exe")]
    first_probes = base_probes(
        **{
            str(owner_pid): probe(owner_pid, "not_found"),
            str(child_pid): running_probe(
                child_pid, 3000, r"C:\recovery\native-child.exe"
            ),
        }
    )
    second_probes = base_probes(
        **{
            str(owner_pid): probe(owner_pid, "not_found"),
            str(child_pid): probe(child_pid, "not_found"),
        }
    )
    report, _ = capture_stability(
        [owner],
        [(entries, first_probes), (entries, second_probes)],
    )

    result = stability(report)
    assert result["all_visible_descendants_dead_twice"] is False
    assert result["verdict"] == "refuse"


def test_stability_reclassification_does_not_trust_stored_pass():
    owner_pid = 200
    other_pid = 300
    owner = RecordedProcess("lease-owner", owner_pid, role="owner")
    entries = base_entries() + [process(other_pid, 50, "python.exe")]
    probes = base_probes(
        **{
            str(owner_pid): probe(owner_pid, "not_found"),
            str(other_pid): running_probe(
                other_pid, 3000, r"C:\Python\python.exe"
            ),
        }
    )
    report, _ = capture_stability([owner], [(entries, probes), (entries, probes)])
    report["stability"] = {"verdict": "pass", "refusal_reasons": []}

    with pytest.raises(ProcessLivenessError, match="refused recovery"):
        assert_fake_stability_gate(report)


def test_stability_requires_an_explicit_recorded_owner_role():
    worker_pid = 200
    worker = RecordedProcess("worker", worker_pid)
    probes = base_probes(
        **{str(worker_pid): probe(worker_pid, "not_found")}
    )
    first, _ = capture([worker], base_entries(), probes)
    second = copy.deepcopy(first)
    second["observation_index"] = 2

    with pytest.raises(ProcessLivenessError, match="at least one recorded owner"):
        liveness._classify_windows_process_stability(
            first,
            second,
            expected_controller_sys_executable_path=CONTROLLER_PATH,
        )


def test_recorded_process_with_matching_identity_is_live_and_refused():
    owner_pid = 200
    owner_path = r"C:\recovery\.venv\Scripts\python.exe"
    entries = base_entries() + [process(owner_pid, 1, "python.exe")]
    snapshot, _ = capture(
        [
            RecordedProcess(
                "lease-owner", owner_pid, 2000, owner_path, role="owner"
            )
        ],
        entries,
        base_probes(
            **{str(owner_pid): running_probe(owner_pid, 2000, owner_path)}
        ),
    )

    row = recorded_rows(snapshot)[0]
    assert row["classification"] == "live"
    assert row["reason"] == "recorded_process_is_still_running"
    result = classification(snapshot)
    assert result["verdict"] == "snapshot_refuse"
    assert result["other_python_processes"] == [owner_pid]


def test_running_legacy_pid_without_creation_identity_is_ambiguous():
    owner_pid = 200
    entries = base_entries() + [process(owner_pid, 1, "worker.exe")]
    snapshot, _ = capture(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        entries,
        base_probes(
            **{
                str(owner_pid): running_probe(
                    owner_pid, 2000, r"C:\recovery\worker.exe"
                )
            }
        ),
    )

    row = recorded_rows(snapshot)[0]
    assert row["classification"] == "ambiguous"
    assert row["reason"] == "running_pid_has_no_recorded_creation_filetime"
    assert classification(snapshot)["verdict"] == "snapshot_refuse"


def test_pid_reuse_is_explicit_and_conservatively_refused():
    owner_pid = 200
    entries = base_entries() + [process(owner_pid, 1, "worker.exe")]
    snapshot, _ = capture(
        [
            RecordedProcess(
                "lease-owner", owner_pid, 1999, r"C:\recovery\worker.exe"
            )
        ],
        entries,
        base_probes(
            **{
                str(owner_pid): running_probe(
                    owner_pid, 2000, r"C:\recovery\worker.exe"
                )
            }
        ),
    )

    row = recorded_rows(snapshot)[0]
    assert row["classification"] == "pid_reused"
    assert row["reason"] == "running_pid_creation_filetime_differs"
    assert row["blocks_snapshot_clear"] is True
    assert classification(snapshot)["verdict"] == "snapshot_refuse"


@pytest.mark.parametrize(
    ("status", "entry_present", "reason"),
    [
        ("error", True, "OpenProcess_failed"),
        ("running", False, "toolhelp_and_openprocess_disagree"),
    ],
)
def test_access_or_snapshot_api_ambiguity_fails_closed(
    status: str, entry_present: bool, reason: str
):
    owner_pid = 200
    entries = base_entries()
    if entry_present:
        entries.append(process(owner_pid, 1, "worker.exe"))
    owner_probe = (
        probe(
            owner_pid,
            "error",
            error_stage="OpenProcess",
            winerror=5,
        )
        if status == "error"
        else running_probe(owner_pid, 2000, r"C:\recovery\worker.exe")
    )
    snapshot, _ = capture(
        [RecordedProcess("lease-owner", owner_pid, 2000, role="owner")],
        entries,
        base_probes(**{str(owner_pid): owner_probe}),
    )

    row = recorded_rows(snapshot)[0]
    assert row["classification"] == "ambiguous"
    assert row["reason"] == reason
    assert classification(snapshot)["verdict"] == "snapshot_refuse"


def test_process_that_exits_between_snapshot_and_open_is_dead_proven():
    worker_pid = 201
    entries = base_entries() + [process(worker_pid, CONTROLLER_PID, "worker.exe")]
    snapshot, _ = capture(
        [RecordedProcess("last-worker", worker_pid, 3000)],
        entries,
        base_probes(**{str(worker_pid): probe(worker_pid, "not_found")}),
    )

    row = recorded_rows(snapshot)[0]
    assert row["classification"] == "dead_proven"
    assert row["reason"] == "exited_after_toolhelp_snapshot"
    assert classification(snapshot)["verdict"] == "snapshot_clear"


def test_signaled_process_handle_is_dead_proven():
    worker_pid = 201
    worker_path = r"C:\recovery\worker.exe"
    entries = base_entries() + [process(worker_pid, CONTROLLER_PID, "worker.exe")]
    snapshot, _ = capture(
        [RecordedProcess("last-worker", worker_pid, 3000, worker_path)],
        entries,
        base_probes(
            **{
                str(worker_pid): probe(
                    worker_pid,
                    "signaled",
                    creation=3000,
                    path=worker_path,
                )
            }
        ),
    )

    assert recorded_rows(snapshot)[0]["classification"] == "dead_proven"
    assert classification(snapshot)["verdict"] == "snapshot_clear"


def test_non_python_descendant_is_probed_and_live_descendant_refuses():
    owner_pid = 200
    child_pid = 201
    child_path = r"C:\recovery\native-helper.exe"
    entries = base_entries() + [
        process(child_pid, owner_pid, "native-helper.exe")
    ]
    snapshot, api = capture(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        entries,
        base_probes(
            **{
                str(owner_pid): probe(owner_pid, "not_found"),
                str(child_pid): running_probe(child_pid, 3000, child_path),
            }
        ),
    )

    assert api.queried == [CONTROLLER_PID, owner_pid, child_pid]
    result = classification(snapshot)
    assert result["live_descendant_processes"] == [child_pid]
    assert result["ambiguous_descendant_processes"] == []
    assert result["descendant_processes"] == [
        {
            "pid": child_pid,
            "parent_pid": owner_pid,
            "ancestry_path": [child_pid, owner_pid],
            "recorded_ancestor_pid": owner_pid,
            "observed_creation_time_filetime": "3000",
            "observed_executable_path": child_path,
            "classification": "live",
            "reason": "process_handle_is_unsignaled",
            "blocks_snapshot_clear": True,
        }
    ]
    assert result["verdict"] == "snapshot_refuse"
    assert f"descendant:{child_pid}:process_handle_is_unsignaled" in result[
        "refusal_reasons"
    ]


def test_transitive_descendants_must_each_be_positively_dead():
    owner_pid = 200
    child_pid = 201
    grandchild_pid = 202
    child_path = r"C:\recovery\child.exe"
    grandchild_path = r"C:\recovery\grandchild.exe"
    entries = base_entries() + [
        process(child_pid, owner_pid, "child.exe"),
        process(grandchild_pid, child_pid, "grandchild.exe"),
    ]
    snapshot, api = capture(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        entries,
        base_probes(
            **{
                str(owner_pid): probe(owner_pid, "not_found"),
                str(child_pid): probe(
                    child_pid,
                    "signaled",
                    creation=3000,
                    path=child_path,
                ),
                str(grandchild_pid): probe(
                    grandchild_pid,
                    "signaled",
                    creation=3001,
                    path=grandchild_path,
                ),
            }
        ),
    )

    assert api.queried == [CONTROLLER_PID, owner_pid, child_pid, grandchild_pid]
    result = classification(snapshot)
    assert [row["ancestry_path"] for row in result["descendant_processes"]] == [
        [child_pid, owner_pid],
        [grandchild_pid, child_pid, owner_pid],
    ]
    assert [row["classification"] for row in result["descendant_processes"]] == [
        "dead_proven",
        "dead_proven",
    ]
    assert result["verdict"] == "snapshot_clear"


def test_descendant_that_exits_after_toolhelp_snapshot_is_positively_dead():
    owner_pid = 200
    child_pid = 201
    entries = base_entries() + [process(child_pid, owner_pid, "worker.exe")]
    snapshot, _ = capture(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        entries,
        base_probes(
            **{
                str(owner_pid): probe(owner_pid, "not_found"),
                str(child_pid): probe(child_pid, "not_found"),
            }
        ),
    )

    descendant = classification(snapshot)["descendant_processes"][0]
    assert descendant["classification"] == "dead_proven"
    assert descendant["reason"] == "exited_after_toolhelp_snapshot"
    assert classification(snapshot)["verdict"] == "snapshot_clear"


def test_cycle_that_repeats_recorded_owner_chain_refuses():
    owner_pid = 200
    child_pid = 201
    owner_path = r"C:\recovery\owner.exe"
    child_path = r"C:\recovery\child.exe"
    entries = base_entries() + [
        process(owner_pid, child_pid, "owner.exe"),
        process(child_pid, owner_pid, "child.exe"),
    ]
    snapshot, api = capture(
        [
            RecordedProcess(
                "lease-owner", owner_pid, 2000, owner_path, role="owner"
            )
        ],
        entries,
        base_probes(
            **{
                str(owner_pid): probe(
                    owner_pid,
                    "signaled",
                    creation=2000,
                    path=owner_path,
                ),
                str(child_pid): probe(
                    child_pid,
                    "signaled",
                    creation=2001,
                    path=child_path,
                ),
            }
        ),
    )

    assert api.queried == [CONTROLLER_PID, owner_pid, child_pid]
    result = classification(snapshot)
    assert result["ancestry_ambiguities"] == [
        {
            "recorded_pid": owner_pid,
            "ancestry_path": [owner_pid, child_pid, owner_pid],
            "classification": "cycle",
            "terminal_pid": owner_pid,
        },
    ]
    assert result["verdict"] == "snapshot_refuse"
    assert (
        f"ancestry:recorded:{owner_pid}:cycle:{owner_pid}"
        in result["refusal_reasons"]
    )


def test_missing_link_in_present_recorded_owner_chain_refuses():
    owner_pid = 200
    missing_parent_pid = 999
    owner_path = r"C:\recovery\owner.exe"
    entries = base_entries() + [
        process(owner_pid, missing_parent_pid, "owner.exe")
    ]
    snapshot, api = capture(
        [
            RecordedProcess(
                "lease-owner", owner_pid, 2000, owner_path, role="owner"
            )
        ],
        entries,
        base_probes(
            **{
                str(owner_pid): probe(
                    owner_pid,
                    "signaled",
                    creation=2000,
                    path=owner_path,
                ),
            }
        ),
    )

    assert api.queried == [CONTROLLER_PID, owner_pid]
    result = classification(snapshot)
    assert result["ancestry_ambiguities"] == [
        {
            "recorded_pid": owner_pid,
            "ancestry_path": [owner_pid, missing_parent_pid],
            "classification": "missing",
            "terminal_pid": missing_parent_pid,
        }
    ]
    assert result["verdict"] == "snapshot_refuse"
    assert (
        f"ancestry:recorded:{owner_pid}:missing:{missing_parent_pid}"
        in result["refusal_reasons"]
    )


def test_unrelated_missing_and_cyclic_parent_chains_are_not_candidates():
    owner_pid = 200
    missing_pid = 500
    cycle_left = 501
    cycle_right = 502
    entries = base_entries() + [
        process(missing_pid, 999, "unrelated-missing.exe"),
        process(cycle_left, cycle_right, "unrelated-left.exe"),
        process(cycle_right, cycle_left, "unrelated-right.exe"),
    ]
    snapshot, api = capture(
        [RecordedProcess("lease-owner", owner_pid, role="owner")],
        entries,
        base_probes(**{str(owner_pid): probe(owner_pid, "not_found")}),
    )

    assert api.queried == [CONTROLLER_PID, owner_pid]
    result = classification(snapshot)
    assert result["ancestry_ambiguities"] == []
    unresolved = {
        row["pid"]: row["classification"]
        for row in result["ancestry_assessments"]
        if row["pid"] in {missing_pid, cycle_left, cycle_right}
    }
    assert unresolved == {
        missing_pid: "unrelated_missing",
        cycle_left: "unrelated_cycle",
        cycle_right: "unrelated_cycle",
    }
    assert result["verdict"] == "snapshot_clear"


def test_other_python_process_is_detected_but_controller_is_excluded():
    other_pid = 300
    entries = base_entries() + [process(other_pid, 50, "PythonW.EXE")]
    snapshot, _ = capture(
        [],
        entries,
        base_probes(
            **{
                str(other_pid): running_probe(
                    other_pid, 3000, r"C:\Python311\pythonw.exe"
                )
            }
        ),
    )

    result = classification(snapshot)
    assert result["other_python_processes"] == [other_pid]
    assert result["ambiguous_python_processes"] == []
    assert result["verdict"] == "snapshot_refuse"
    python_rows = result["python_processes"]
    assert [row["pid"] for row in python_rows] == [CONTROLLER_PID, other_pid]
    assert [row["relation"] for row in python_rows] == ["controller", "other"]


@pytest.mark.parametrize(
    "image_name",
    [
        "python_d.exe",
        "pythonw_d.exe",
        "python3.13_d.exe",
        "pythonw3.13_d.exe",
        "python313_d.exe",
        "pypy_d.exe",
        "pypy3.10.exe",
        "pypy3.10_d.exe",
        "PYPY3.11_D.EXE",
    ],
)
def test_debug_and_versioned_python_images_are_detected(image_name):
    other_pid = 300
    entries = base_entries() + [process(other_pid, 50, image_name)]
    snapshot, api = capture(
        [],
        entries,
        base_probes(
            **{
                str(other_pid): running_probe(
                    other_pid, 3000, rf"C:\Python\{image_name}"
                )
            }
        ),
    )

    assert api.queried == [CONTROLLER_PID, other_pid]
    assert classification(snapshot)["other_python_processes"] == [other_pid]
    assert classification(snapshot)["verdict"] == "snapshot_refuse"


@pytest.mark.parametrize(
    "image_name",
    ["python.dll", "not-python.exe", "pypython.exe", "pypy-helper.exe"],
)
def test_non_python_image_names_are_not_promoted_to_python_candidates(image_name):
    assert liveness._python_candidate(image_name) is False


def test_controller_uses_kernel_python_image_not_venv_redirector_path():
    base_python = r"C:\Users\user\Python313\python.exe"
    snapshot, _ = capture(
        [],
        base_entries(),
        {CONTROLLER_PID: running_probe(CONTROLLER_PID, 1000, base_python)},
    )

    controller = classification(snapshot)["controller"]
    assert controller["classification"] == "running"
    assert controller["observed_executable_path"] == base_python
    assert controller["reason"] == (
        "controller_pid_handle_and_python_image_confirmed"
    )
    assert classification(snapshot)["verdict"] == "snapshot_clear"


def test_inaccessible_other_python_process_is_ambiguity_not_absence():
    other_pid = 300
    entries = base_entries() + [process(other_pid, 50, "python3.11.exe")]
    snapshot, _ = capture(
        [],
        entries,
        base_probes(
            **{
                str(other_pid): probe(
                    other_pid,
                    "error",
                    error_stage="OpenProcess",
                    winerror=5,
                )
            }
        ),
    )

    result = classification(snapshot)
    assert result["other_python_processes"] == []
    assert result["ambiguous_python_processes"] == [other_pid]
    assert result["verdict"] == "snapshot_refuse"


def test_exited_other_python_candidate_does_not_block_snapshot_clear():
    other_pid = 300
    entries = base_entries() + [process(other_pid, 50, "python.exe")]
    snapshot, _ = capture(
        [],
        entries,
        base_probes(**{str(other_pid): probe(other_pid, "not_found")}),
    )

    result = classification(snapshot)
    assert result["other_python_processes"] == []
    assert result["ambiguous_python_processes"] == []
    assert result["verdict"] == "snapshot_clear"


@pytest.mark.parametrize(
    "controller_probe",
    [
        probe(
            CONTROLLER_PID,
            "error",
            error_stage="QueryFullProcessImageNameW",
            winerror=5,
        ),
        running_probe(CONTROLLER_PID, 1000, r"D:\wrong\not-python.exe"),
    ],
)
def test_controller_identity_ambiguity_refuses(controller_probe):
    snapshot, _ = capture([], base_entries(), {CONTROLLER_PID: controller_probe})

    controller = classification(snapshot)["controller"]
    assert controller["classification"] == "ambiguous"
    assert classification(snapshot)["verdict"] == "snapshot_refuse"


def test_toolhelp_and_handle_executable_mismatch_refuses():
    worker_pid = 200
    entries = base_entries() + [process(worker_pid, 1, "worker.exe")]
    snapshot, _ = capture(
        [RecordedProcess("worker", worker_pid, 2000)],
        entries,
        base_probes(
            **{
                str(worker_pid): running_probe(
                    worker_pid, 2000, r"C:\recovery\different.exe"
                )
            }
        ),
    )

    assert recorded_rows(snapshot)[0]["reason"] == (
        "toolhelp_and_handle_executable_disagree"
    )
    assert classification(snapshot)["verdict"] == "snapshot_refuse"


def test_capture_is_sorted_and_independent_of_input_iteration_order():
    first = RecordedProcess("worker-b", 202)
    second = RecordedProcess("worker-a", 201)
    entries = base_entries() + [process(900, 1, "not-python.exe")]
    probes = base_probes(
        **{
            "201": probe(201, "not_found"),
            "202": probe(202, "not_found"),
        }
    )
    left, left_api = capture([first, second], list(reversed(entries)), probes)
    right, right_api = capture([second, first], entries, probes)

    assert left == right
    assert left_api.queried == [CONTROLLER_PID, 201, 202]
    assert right_api.queried == [CONTROLLER_PID, 201, 202]
    assert [row["pid"] for row in left["toolhelp_processes"]] == [
        4,
        50,
        100,
        400,
        900,
    ]
    assert [row["record_id"] for row in left["recorded_processes"]] == [
        "worker-a",
        "worker-b",
    ]


def test_reclassification_does_not_trust_stored_verdict():
    other_pid = 300
    entries = base_entries() + [process(other_pid, 50, "python.exe")]
    snapshot, _ = capture(
        [],
        entries,
        base_probes(
            **{
                str(other_pid): running_probe(
                    other_pid, 3000, r"C:\Python\python.exe"
                )
            }
        ),
    )
    snapshot["classification"] = {
        "verdict": "snapshot_clear",
        "refusal_reasons": [],
    }

    classified = classify_windows_process_snapshot(snapshot)

    assert classification(classified)["verdict"] == "snapshot_refuse"
    assert classification(classified)["other_python_processes"] == [other_pid]


def test_duplicate_record_ids_refused_before_api_access():
    api = FakeProcessApi(base_entries(), base_probes())
    with pytest.raises(ProcessLivenessError, match="duplicate recorded process"):
        capture_windows_process_snapshot(
            [RecordedProcess("worker", 200), RecordedProcess("worker", 201)],
            controller_pid=CONTROLLER_PID,
            _api=api,
        )
    assert api.queried == []


def test_reused_worker_pid_can_have_distinct_records_and_one_probe():
    worker_pid = 200
    snapshot, api = capture(
        [
            RecordedProcess("worker-attempt-1", worker_pid),
            RecordedProcess("worker-attempt-2", worker_pid),
        ],
        base_entries(),
        base_probes(**{str(worker_pid): probe(worker_pid, "not_found")}),
    )

    assert api.queried == [CONTROLLER_PID, worker_pid]
    assert [row["classification"] for row in recorded_rows(snapshot)] == [
        "dead_proven",
        "dead_proven",
    ]


@pytest.mark.parametrize(
    "bad",
    [
        RecordedProcess,
        "lease-owner",
        object(),
    ],
)
def test_non_recorded_process_elements_are_refused(bad):
    api = FakeProcessApi(base_entries(), base_probes())
    with pytest.raises(ProcessLivenessError, match="exact RecordedProcess|sequence"):
        capture_windows_process_snapshot(
            bad if isinstance(bad, str) else [bad],
            controller_pid=CONTROLLER_PID,
            _api=api,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"record_id": "", "pid": 1},
        {"record_id": "owner", "pid": True},
        {"record_id": "owner", "pid": 0},
        {"record_id": "owner", "pid": 1, "creation_time_filetime": True},
        {"record_id": "owner", "pid": 1, "creation_time_filetime": 0},
        {"record_id": "owner", "pid": 1, "executable_path": ""},
        {"record_id": "owner", "pid": 1, "executable_path": "bad\x00path"},
        {"record_id": "owner", "pid": 1, "role": "lease"},
        {"record_id": "owner", "pid": 1, "role": True},
    ],
)
def test_recorded_process_validation_is_exact(kwargs):
    with pytest.raises(ProcessLivenessError):
        RecordedProcess(**kwargs)


def test_duplicate_toolhelp_pid_refused_as_incomplete_snapshot():
    entries = base_entries() + [process(CONTROLLER_PID, 9, "python.exe")]
    api = FakeProcessApi(entries, base_probes())
    with pytest.raises(ProcessLivenessError, match="duplicate PID"):
        capture_windows_process_snapshot(
            [],
            controller_pid=CONTROLLER_PID,
            _api=api,
        )


def test_empty_toolhelp_snapshot_refused():
    api = FakeProcessApi([], {})
    with pytest.raises(ProcessLivenessError, match="snapshot is empty"):
        capture_windows_process_snapshot(
            [],
            controller_pid=CONTROLLER_PID,
            _api=api,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(status="not_found", winerror=5),
        lambda value: value.update(status="running", wait_code=0),
        lambda value: value.update(status="error", error_stage=None, winerror=None),
        lambda value: value.update(creation_time_filetime="0001"),
        lambda value: value.update(pid=True),
        lambda value: value.update(extra="not allowed"),
    ],
)
def test_malformed_probe_evidence_is_refused(mutation):
    controller_probe = running_probe(CONTROLLER_PID, 1000)
    mutation(controller_probe)
    api = FakeProcessApi(base_entries(), {CONTROLLER_PID: controller_probe})
    with pytest.raises(ProcessLivenessError):
        capture_windows_process_snapshot(
            [],
            controller_pid=CONTROLLER_PID,
            _api=api,
        )


@pytest.mark.parametrize(
    "field",
    [
        "pid",
        "status",
        "creation_time_filetime",
        "executable_path",
        "wait_code",
        "error_stage",
        "winerror",
        "close_winerror",
    ],
)
@pytest.mark.parametrize("unhashable", [[], {}])
def test_unhashable_probe_fields_are_normalized_to_liveness_error(
    field,
    unhashable,
):
    controller_probe = running_probe(CONTROLLER_PID, 1000)
    controller_probe[field] = unhashable
    api = FakeProcessApi(base_entries(), {CONTROLLER_PID: controller_probe})

    with pytest.raises(ProcessLivenessError):
        capture_windows_process_snapshot(
            [],
            controller_pid=CONTROLLER_PID,
            _api=api,
        )


def test_probe_set_must_exactly_cover_required_pids_on_reclassification():
    snapshot, _ = capture([], base_entries(), base_probes())
    snapshot["probes"].append(probe(999, "not_found"))

    with pytest.raises(ProcessLivenessError, match="exactly cover"):
        classify_windows_process_snapshot(snapshot)


def test_real_backend_refuses_non_windows_before_loading_a_library(monkeypatch):
    monkeypatch.setattr(liveness.sys, "platform", "linux")
    with pytest.raises(ProcessLivenessError, match="requires Windows"):
        liveness._WindowsProcessApi()


@pytest.mark.skipif(
    sys.platform != "win32"
    or os.environ.get("BU_RUN_LIVE_WINDOWS_LIVENESS_TEST") != "1",
    reason="opt-in live Windows kernel probe",
)
def test_live_backend_exercises_full_two_snapshot_stability_gate():
    api = liveness._WindowsProcessApi()

    observation = api.probe_process(os.getpid())

    assert observation["status"] == "running"
    assert observation["creation_time_filetime"] is not None
    kernel_path = observation["executable_path"]
    assert isinstance(kernel_path, str)
    assert liveness._python_candidate(kernel_path) is True

    completed_owner = subprocess.Popen(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "exit", "0"]
    )
    completed_owner_pid = completed_owner.pid
    assert completed_owner.wait(timeout=10) == 0
    completed_owner._handle.Close()
    deadline = time.monotonic() + 5.0
    while True:
        owner_present = any(
            int(entry["pid"]) == completed_owner_pid
            for entry in api.enumerate_processes()
        )
        owner_probe = api.probe_process(completed_owner_pid)
        if not owner_present and owner_probe["status"] == "not_found":
            break
        if time.monotonic() >= deadline:
            pytest.fail(
                "completed live-test owner did not become absent from both "
                "Toolhelp and OpenProcess"
            )
        time.sleep(0.02)
    report = capture_windows_process_stability(
        [
            RecordedProcess(
                "live-completed-owner",
                completed_owner_pid,
                role="owner",
            )
        ],
        controller_pid=os.getpid(),
        _api=api,
    )
    assert assert_windows_stability_gate(report) == report

    result = stability(report)
    assert result["owners_absent_twice"] is True
    assert result["controller_same_process"] is True
    if result["controller_launcher_required"]:
        assert result["controller_launcher_stable"] is True
        launcher = result["controller_launcher"]
        assert launcher["relation"] == "controller_launcher"
        launcher_pid = launcher["pid"]
        for snapshot in report["snapshots"]:
            snapshot_result = classification(snapshot)
            assert launcher_pid not in snapshot_result["other_python_processes"]
            assert launcher_pid not in snapshot_result[
                "ambiguous_python_processes"
            ]

    unrelated_or_ambiguous = {
        pid
        for snapshot in report["snapshots"]
        for key in (
            "other_python_processes",
            "ambiguous_python_processes",
        )
        for pid in classification(snapshot)[key]
    }
    if unrelated_or_ambiguous:
        assert result["verdict"] == "refuse"
        assert result["no_other_live_or_ambiguous_python_twice"] is False
    else:
        assert result["verdict"] == "pass"
        assert result["no_other_live_or_ambiguous_python_twice"] is True


class FakeFunction:
    """Callable that also accepts ctypes ``argtypes``/``restype`` attributes."""

    def __init__(self, callback):
        self.callback = callback
        self.calls: list[tuple[object, ...]] = []
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        self.calls.append(args)
        return self.callback(*args)


class FakeKernel32:
    def __init__(self) -> None:
        self.last_error = 0
        self.next_calls = 0
        self.CreateToolhelp32Snapshot = FakeFunction(lambda flags, pid: 123)
        self.Process32FirstW = FakeFunction(self._first)
        self.Process32NextW = FakeFunction(self._next)
        self.OpenProcess = FakeFunction(lambda access, inherit, pid: 456)
        self.GetProcessTimes = FakeFunction(self._times)
        self.QueryFullProcessImageNameW = FakeFunction(self._image)
        self.WaitForSingleObject = FakeFunction(
            lambda handle, milliseconds: liveness.WAIT_TIMEOUT
        )
        self.CloseHandle = FakeFunction(lambda handle: 1)
        self.SetLastError = FakeFunction(self._set_error)
        self.GetLastError = FakeFunction(lambda: self.last_error)

    def _set_error(self, value):
        self.last_error = int(value)

    def _first(self, handle, entry_pointer):
        del handle
        entry = ctypes.cast(
            entry_pointer, ctypes.POINTER(liveness._PROCESSENTRY32W)
        ).contents
        entry.th32ProcessID = 100
        entry.th32ParentProcessID = 50
        entry.szExeFile = "python.exe"
        return 1

    def _next(self, handle, entry_pointer):
        del handle, entry_pointer
        self.next_calls += 1
        self.last_error = liveness.ERROR_NO_MORE_FILES
        return 0

    def _times(self, handle, creation_pointer, exit_pointer, kernel_pointer, user_pointer):
        del handle, exit_pointer, kernel_pointer, user_pointer
        creation = ctypes.cast(
            creation_pointer, ctypes.POINTER(liveness._FILETIME)
        ).contents
        creation.dwHighDateTime = 2
        creation.dwLowDateTime = 3
        return 1

    def _image(self, handle, flags, buffer, length_pointer):
        del handle, flags
        value = CONTROLLER_PATH
        buffer.value = value
        length = ctypes.cast(
            length_pointer, ctypes.POINTER(liveness.wintypes.DWORD)
        ).contents
        length.value = len(value)
        return 1


def mocked_windows_api() -> tuple[liveness._WindowsProcessApi, FakeKernel32]:
    kernel = FakeKernel32()
    api = liveness._WindowsProcessApi.__new__(liveness._WindowsProcessApi)
    api._kernel32 = kernel
    api._configure_signatures()
    return api, kernel


def test_ctypes_backend_uses_complete_toolhelp_enumeration_calls():
    api, kernel = mocked_windows_api()

    rows = api.enumerate_processes()

    assert rows == [{"pid": 100, "parent_pid": 50, "exe_name": "python.exe"}]
    assert len(kernel.CreateToolhelp32Snapshot.calls) == 1
    assert kernel.CreateToolhelp32Snapshot.calls[0] == (
        liveness.TH32CS_SNAPPROCESS,
        0,
    )
    assert len(kernel.Process32FirstW.calls) == 1
    assert len(kernel.Process32NextW.calls) == 1
    assert kernel.next_calls == 1
    assert kernel.CloseHandle.calls[-1] == (123,)


@pytest.mark.parametrize("exception_type", [RuntimeError, KeyboardInterrupt])
def test_toolhelp_handle_is_closed_in_finally_for_every_exception(exception_type):
    api, kernel = mocked_windows_api()

    def fail_after_snapshot(handle, entry_pointer):
        del handle, entry_pointer
        raise exception_type("planted enumeration interruption")

    kernel.Process32FirstW = FakeFunction(fail_after_snapshot)

    with pytest.raises(exception_type, match="planted enumeration interruption"):
        api.enumerate_processes()
    assert kernel.CloseHandle.calls == [(123,)]


@pytest.mark.parametrize("exception_type", [RuntimeError, KeyboardInterrupt])
def test_probe_openprocess_exception_has_no_handle_to_close(exception_type):
    api, kernel = mocked_windows_api()

    def fail_open(access, inherit, pid):
        del access, inherit, pid
        raise exception_type("planted OpenProcess interruption")

    kernel.OpenProcess = FakeFunction(fail_open)

    with pytest.raises(exception_type, match="planted OpenProcess interruption"):
        api.probe_process(CONTROLLER_PID)
    assert kernel.CloseHandle.calls == []


@pytest.mark.parametrize(
    "stage",
    [
        "GetProcessTimes",
        "QueryFullProcessImageNameW",
        "WaitForSingleObject",
    ],
)
@pytest.mark.parametrize("exception_type", [RuntimeError, KeyboardInterrupt])
def test_probe_handle_is_closed_when_each_post_open_api_stage_raises(
    stage,
    exception_type,
):
    api, kernel = mocked_windows_api()

    def interrupt(*args):
        del args
        raise exception_type(f"planted {stage} interruption")

    setattr(kernel, stage, FakeFunction(interrupt))

    with pytest.raises(exception_type, match=f"planted {stage} interruption"):
        api.probe_process(CONTROLLER_PID)
    assert kernel.CloseHandle.calls == [(456,)]


@pytest.mark.parametrize("exception_type", [RuntimeError, KeyboardInterrupt])
def test_probe_closehandle_exception_is_attempted_and_propagated(exception_type):
    api, kernel = mocked_windows_api()

    def interrupt_close(handle):
        del handle
        raise exception_type("planted CloseHandle interruption")

    kernel.CloseHandle = FakeFunction(interrupt_close)

    with pytest.raises(exception_type, match="planted CloseHandle interruption"):
        api.probe_process(CONTROLLER_PID)
    assert kernel.CloseHandle.calls == [(456,)]


def test_ctypes_backend_uses_all_handle_identity_and_liveness_calls():
    api, kernel = mocked_windows_api()

    result = api.probe_process(CONTROLLER_PID)

    expected_creation = str((2 << 32) | 3)
    assert result == running_probe(CONTROLLER_PID, int(expected_creation))
    assert kernel.OpenProcess.calls == [
        (
            liveness.PROCESS_QUERY_LIMITED_INFORMATION | liveness.SYNCHRONIZE,
            False,
            CONTROLLER_PID,
        )
    ]
    assert len(kernel.GetProcessTimes.calls) == 1
    assert len(kernel.QueryFullProcessImageNameW.calls) == 1
    assert kernel.WaitForSingleObject.calls == [(456, 0)]
    assert kernel.CloseHandle.calls[-1] == (456,)


def test_ctypes_backend_open_access_denial_is_preserved_not_treated_as_absent():
    api, kernel = mocked_windows_api()
    kernel.OpenProcess = FakeFunction(lambda access, inherit, pid: 0)
    kernel.last_error = 5
    # OpenProcess follows a SetLastError(0), so plant the failure atomically.
    def denied(access, inherit, pid):
        del access, inherit, pid
        kernel.last_error = 5
        return 0

    kernel.OpenProcess = FakeFunction(denied)

    result = api.probe_process(200)

    assert result == probe(
        200,
        "error",
        error_stage="OpenProcess",
        winerror=5,
    )
    assert kernel.CloseHandle.calls == []


def test_ctypes_backend_close_failure_turns_successful_probe_into_ambiguity():
    api, kernel = mocked_windows_api()
    def close_failed(handle):
        del handle
        kernel.last_error = 6
        return 0
    kernel.CloseHandle = FakeFunction(close_failed)

    result = api.probe_process(CONTROLLER_PID)

    assert result["status"] == "error"
    assert result["error_stage"] == "CloseHandle"
    assert result["winerror"] == 6
    assert result["close_winerror"] == 6


def test_public_surface_is_deliberately_small():
    assert liveness.__all__ == [
        "WINDOWS_LIVENESS_SCHEMA_VERSION",
        "ProcessLivenessError",
        "RecordedProcess",
        "assert_windows_stability_gate",
        "capture_windows_process_identity",
        "capture_windows_process_snapshot",
        "capture_windows_process_stability",
        "classify_windows_process_snapshot",
        "classify_windows_process_stability",
    ]
