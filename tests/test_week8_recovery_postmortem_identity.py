"""Synthetic controller-identity binding tests for D-161 postmortem recovery.

The suite exercises only the recovery-layer relationship between an already
classified two-snapshot report and the separately captured controller process.
No production path or evidence record is opened.  The Windows gate is replaced
at its public assertion boundary so malformed cross-object bindings cannot be
rejected earlier for an unrelated classifier reason.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from bu.experiments import week8_exp2a_recovery as R


CONTROLLER_PID = 4_321
CONTROLLER_CREATION = 132_537_600_000_000_001
WORKER_PID = 8_765
WORKER_CREATION = 132_537_599_000_000_001


def _liveness_row(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "sha256": R.sha256_bytes(R._canonical(report)),
        "report": report,
    }


def _case_variant(path: str) -> str:
    return "".join(
        character.swapcase() if character.isalpha() else character
        for character in path
    )


@pytest.fixture
def postmortem_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    launcher = tmp_path / "PinnedVenv" / "Scripts" / "python.exe"
    base = tmp_path / "PinnedBase" / "Python313" / "python.exe"
    alternate_base = tmp_path / "OtherBase" / "Python313" / "python.exe"
    alternate_launcher = tmp_path / "OtherVenv" / "Scripts" / "python.exe"
    for path, data in (
        (launcher, b"synthetic pinned launcher"),
        (base, b"synthetic pinned base interpreter"),
        (alternate_base, b"synthetic alternate base interpreter"),
        (alternate_launcher, b"synthetic alternate launcher"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    launcher_path = str(launcher.resolve())
    base_path = str(base.resolve())
    authority = {
        "pinned_python": {
            "path": launcher_path,
            "sha256": R.sha256_file(launcher),
        }
    }
    controller_process = {
        "pid": CONTROLLER_PID,
        "kernel_executable_path": base_path,
        "kernel_executable_sha256": R.sha256_file(base),
        "creation_time_100ns": CONTROLLER_CREATION,
        "base_interpreter": {
            "path": base_path,
            "sha256": R.sha256_file(base),
        },
    }
    claim = {
        "worker": {
            "process": {
                "pid": WORKER_PID,
                "creation_time_100ns": WORKER_CREATION,
                "kernel_executable_path": str(tmp_path / "worker-python.exe"),
            }
        }
    }
    expected_worker = R._postmortem_worker_expectation(claim)

    def controller_classification() -> dict[str, Any]:
        return {
            "pid": CONTROLLER_PID,
            "declared_sys_executable_path": launcher_path,
            "normalized_sys_executable_path": os.path.normcase(launcher_path),
            "observed_creation_time_filetime": str(CONTROLLER_CREATION),
            "observed_executable_path": base_path,
            "classification": "running",
            "reason": "controller_pid_handle_and_python_image_confirmed",
        }

    def snapshot(index: int) -> dict[str, Any]:
        return {
            "observation_index": index,
            "controller": {
                "pid": CONTROLLER_PID,
                "declared_sys_executable_path": launcher_path,
            },
            "recorded_processes": [copy.deepcopy(expected_worker)],
            "classification": {"controller": controller_classification()},
        }

    report = {
        "expected_controller_sys_executable_path": launcher_path,
        "normalized_expected_controller_sys_executable_path": os.path.normcase(
            launcher_path
        ),
        "snapshots": [snapshot(1), snapshot(2)],
        "stability": {
            "verdict": "pass",
            "all_recorded_processes_dead_twice": True,
            "controller_same_process": True,
        },
    }

    def accept_classified_report(value: dict[str, Any]) -> dict[str, Any]:
        return value

    monkeypatch.setattr(
        R.windows_liveness,
        "assert_windows_stability_gate",
        accept_classified_report,
    )

    def validate(candidate: dict[str, Any]) -> dict[str, Any]:
        return R._validate_postmortem_liveness(
            _liveness_row(candidate),
            claim=claim,
            controller_process=controller_process,
            authority=authority,
        )

    return SimpleNamespace(
        report=report,
        validate=validate,
        authority=authority,
        controller_process=controller_process,
        claim=claim,
        launcher=launcher,
        base=base,
        alternate_base=alternate_base,
        alternate_launcher=alternate_launcher,
    )


def test_exact_controller_projection_is_accepted(
    postmortem_identity: SimpleNamespace,
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    result = postmortem_identity.validate(report)
    assert result == _liveness_row(report)


@pytest.mark.parametrize("snapshot_index", (0, 1))
def test_creation_time_drift_in_each_snapshot_is_refused_independently(
    postmortem_identity: SimpleNamespace, snapshot_index: int
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    report["snapshots"][snapshot_index]["classification"]["controller"][
        "observed_creation_time_filetime"
    ] = str(CONTROLLER_CREATION + snapshot_index + 1)
    with pytest.raises(R.RecoveryRefused):
        postmortem_identity.validate(report)


@pytest.mark.parametrize("snapshot_index", (0, 1))
def test_kernel_path_drift_in_each_snapshot_is_refused(
    postmortem_identity: SimpleNamespace, snapshot_index: int
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    report["snapshots"][snapshot_index]["classification"]["controller"][
        "observed_executable_path"
    ] = str(postmortem_identity.alternate_base.resolve())
    with pytest.raises(R.RecoveryRefused):
        postmortem_identity.validate(report)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda report, path: report["snapshots"][0]["controller"].update(
            declared_sys_executable_path=path
        ),
        lambda report, path: report["snapshots"][1]["controller"].update(
            declared_sys_executable_path=path
        ),
        lambda report, path: report["snapshots"][0]["classification"][
            "controller"
        ].update(declared_sys_executable_path=path),
        lambda report, path: report["snapshots"][1]["classification"][
            "controller"
        ].update(declared_sys_executable_path=path),
    ),
)
def test_declared_launcher_drift_is_refused_at_every_snapshot_projection(
    postmortem_identity: SimpleNamespace,
    mutate: Callable[[dict[str, Any], str], None],
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    mutate(report, str(postmortem_identity.alternate_launcher.resolve()))
    with pytest.raises(R.RecoveryRefused):
        postmortem_identity.validate(report)


def test_top_level_expected_launcher_drift_is_refused(
    postmortem_identity: SimpleNamespace,
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    report["expected_controller_sys_executable_path"] = str(
        postmortem_identity.alternate_launcher.resolve()
    )
    with pytest.raises(R.RecoveryRefused):
        postmortem_identity.validate(report)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda snapshot: snapshot["controller"].update(pid=CONTROLLER_PID + 1),
        lambda snapshot: snapshot["classification"]["controller"].update(
            pid=CONTROLLER_PID + 1
        ),
    ),
)
@pytest.mark.parametrize("snapshot_index", (0, 1))
def test_pid_drift_is_refused_in_raw_and_classified_controller_rows(
    postmortem_identity: SimpleNamespace,
    snapshot_index: int,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    mutate(report["snapshots"][snapshot_index])
    with pytest.raises(R.RecoveryRefused):
        postmortem_identity.validate(report)


def test_tampered_report_with_recomputed_sha_is_still_refused(
    postmortem_identity: SimpleNamespace,
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    report["snapshots"][0]["classification"]["controller"][
        "observed_creation_time_filetime"
    ] = str(CONTROLLER_CREATION - 1)
    row = _liveness_row(report)
    assert row["sha256"] == R.sha256_bytes(R._canonical(row["report"]))
    with pytest.raises(R.RecoveryRefused):
        R._validate_postmortem_liveness(
            row,
            claim=postmortem_identity.claim,
            controller_process=postmortem_identity.controller_process,
            authority=postmortem_identity.authority,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
def test_case_equivalent_windows_process_paths_are_accepted(
    postmortem_identity: SimpleNamespace,
) -> None:
    report = copy.deepcopy(postmortem_identity.report)
    launcher_variant = _case_variant(
        postmortem_identity.authority["pinned_python"]["path"]
    )
    base_variant = _case_variant(
        postmortem_identity.controller_process["kernel_executable_path"]
    )
    report["expected_controller_sys_executable_path"] = launcher_variant
    for snapshot in report["snapshots"]:
        snapshot["controller"]["declared_sys_executable_path"] = launcher_variant
        snapshot["classification"]["controller"][
            "declared_sys_executable_path"
        ] = launcher_variant
        snapshot["classification"]["controller"][
            "observed_executable_path"
        ] = base_variant
    postmortem_identity.controller_process[
        "kernel_executable_path"
    ] = base_variant
    result = postmortem_identity.validate(report)
    assert result == _liveness_row(report)
