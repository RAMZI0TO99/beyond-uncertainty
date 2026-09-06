"""Synthetic-only tests for the fixed Week-8 E2A production driver.

No production fit, label, report or figure is opened here.  Lower scientific
layers are replaced at their public boundaries where needed; receipt, fixed
path, monitor-chain and command-dispatch behavior is exercised directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_json, read_json, sha256_bytes, sha256_file
from bu.experiments import week8_exp2a_production as P
from bu.experiments import week8_exp2a_recovery as Recovery


COMMIT = "c" * 40


@pytest.fixture
def fixed_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(P, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(P.Plan, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(P.Plan, "COMMON_LEASE_ROOT", root / "week7-production-control")
    replacements = {
        "PREPARATION_ROOT": root / "week8-execution-preparation-2026-09-01-attempt-001",
        "PREFLIGHT_ROOT": root / "week8-exp2a-2026-09-01-attempt-001-preflight",
        "OUTPUT_ROOT": root / "week8-exp2a-2026-09-01-attempt-001-output",
        "STAGING_ROOT": root / "week8-exp2a-2026-09-01-attempt-001-staging",
        "SYNC_ROOT": root / "week8-exp2a-2026-09-01-attempt-001-project-evidence",
        "LABEL_EXPORT_ROOT": root / "week8-exp2a-labels-2026-09-01-attempt-001",
        "LABEL_COPY_ROOT": root
        / "week8-exp2a-labels-2026-09-01-attempt-001-project-evidence",
        "REPORT_ROOT": root / "week8-exp2a-report-2026-09-01-attempt-001",
        "REPORT_COPY_ROOT": root
        / "week8-exp2a-report-2026-09-01-attempt-001-project-evidence",
        "FIGURE_ROOT": root / "week8-exp2a-figures-2026-09-01-attempt-001",
        "FIGURE_CACHE_ROOT": root
        / "week8-exp2a-figures-2026-09-01-attempt-001-mpl-cache",
        # Keep relocated Windows test paths short enough for tempfile's extra
        # atomic-publication suffix.  The production-name test below exercises
        # the real fixed constants outside this fixture.
        "MONITOR_ROOT": root / "monitor",
        "MONITOR_COPY_ROOT": root / "monitor-copy",
    }
    replacements["PREPARATION_ORIGINAL_ROOT"] = (
        replacements["PREPARATION_ROOT"] / "exp2a-original"
    )
    replacements["PREPARATION_COPY_ROOT"] = (
        replacements["PREPARATION_ROOT"] / "exp2a-project-evidence"
    )
    for name, value in replacements.items():
        monkeypatch.setattr(P, name, value)
    monkeypatch.delenv("MPLCONFIGDIR", raising=False)
    return root


def _environment(commit: str) -> dict[str, object]:
    return {
        "git_commit": commit,
        "device": {
            "frozen_route": "cpu",
            "requested_route": "cpu",
            "available": True,
        },
        "num_threads": 4,
        "num_interop_threads": 4,
    }


def _stub_prepare(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(P.Launch, "_environment", _environment)

    def write_plan(directory: Path) -> Path:
        return atomic_write_json(
            Path(directory) / P.Plan.PLAN_FILE,
            {"plan_digest": "a" * 64, "kind": "synthetic_outcome_free_plan"},
        )

    def load_plan(path: Path) -> dict[str, str]:
        document = read_json(path)
        assert document["kind"] == "synthetic_outcome_free_plan"
        return document

    def write_ledger(directory: Path) -> Path:
        return atomic_write_json(
            Path(directory) / P.Sources.SOURCE_LEDGER_FILE,
            {"ledger_digest": "b" * 64, "reused_fit_count": 155},
        )

    monkeypatch.setattr(P.Plan, "write_exp2a_repair_plan", write_plan)
    monkeypatch.setattr(P.Plan, "load_exp2a_repair_plan", load_plan)
    monkeypatch.setattr(P.Sources, "write_exp2a_source_ledger", write_ledger)


def _prepare(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    _stub_prepare(monkeypatch)
    return P.prepare(expected_git_commit=COMMIT)


def _stub_preflight(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    calls: dict[str, object] = {}

    def run(**kwargs: object) -> dict[str, object]:
        calls.update(kwargs)
        document = {
            "status": "ready",
            "binding_sha256": "d" * 64,
            "inputs": {},
        }
        atomic_write_json(P.PREFLIGHT_ROOT / P.Launch.PREFLIGHT_FILE, document)
        atomic_write_json(P.SYNC_ROOT / P.Launch.PREFLIGHT_FILE, document)
        return document

    def validate(path: Path, **kwargs: object) -> SimpleNamespace:
        assert Path(path) == P.PREFLIGHT_ROOT / P.Launch.PREFLIGHT_FILE
        assert kwargs == {
            "output_root": P.OUTPUT_ROOT,
            "sync_root": P.SYNC_ROOT,
            "expected_git_commit": COMMIT,
        }
        return SimpleNamespace(report=read_json(path))

    monkeypatch.setattr(P.Launch, "run_exp2a_repair_preflight", run)
    monkeypatch.setattr(P.Launch, "validate_exp2a_repair_preflight", validate)
    return calls


def _preflight(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    _prepare(monkeypatch)
    _stub_preflight(monkeypatch)
    return P.preflight(expected_git_commit=COMMIT)


def _write_released_lease(token: str) -> Path:
    path = (
        P.Plan.COMMON_LEASE_ROOT
        / "leases"
        / "history"
        / f"{P.Plan.COMMON_LEASE_NAME}.{token}.released.json"
    )
    atomic_write_json(
        path,
        {
            "schema_version": P.Launch.SUPERVISOR_SCHEMA_VERSION,
            "lease_name": P.Plan.COMMON_LEASE_NAME,
            "pid": 4242,
            "token": token,
            "timestamp": 1.0,
            "timestamp_utc": "2026-09-01T00:00:00Z",
        },
    )
    return path


def _write_lower_report(
    *,
    token: str,
    checkpoint: dict[str, object] | None,
    status: str = "complete",
    counts: dict[str, int] | None = None,
    failure: dict[str, str] | None = None,
    release_failure: dict[str, object] | None = None,
) -> dict[str, object]:
    control = P._load_control(monitor_only=True)
    history = None if release_failure is not None else _write_released_lease(token)
    document = {
        "exp2a_repair_launch_schema_version": 1,
        "status": status,
        "counts": counts
        or {"executed": 261, "resumed": 0, "synced": 261, "total": 261},
        "failure": failure,
        "historical_retrained": False,
        "preflight": {
            "path": control["payload"]["preflight"]["path"],
            "sha256": control["payload"]["preflight"]["sha256"],
        },
        "checkpoint": (
            None
            if checkpoint is None
            else {
                "path": str(
                    P.OUTPUT_ROOT / P.Plan.START_DIRECTORY / f"{token}.json"
                ),
                "sha256": sha256_file(
                    P.OUTPUT_ROOT / P.Plan.START_DIRECTORY / f"{token}.json"
                ),
            }
        ),
        "released_lease": (
            None
            if history is None
            else {"token": token, "history_path": str(history)}
        ),
        "lease_release_failure": release_failure,
    }
    for root in (P.OUTPUT_ROOT, P.SYNC_ROOT):
        atomic_write_json(
            root / P.Launch.REPORT_DIRECTORY / f"{token}.json", document
        )
    return document


def _synthetic_launch(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    _preflight(monkeypatch)
    token = "1" * 32

    def run(**kwargs: object) -> dict[str, object]:
        original, copied = P._receipt_paths("launch-control")
        assert original.exists() and copied.exists(), "control must predate blocking call"
        assert kwargs == {
            "preflight_report": P.PREFLIGHT_ROOT / P.Launch.PREFLIGHT_FILE,
            "output_root": P.OUTPUT_ROOT,
            "sync_root": P.SYNC_ROOT,
            "expected_git_commit": COMMIT,
        }
        checkpoint = _write_real_shape_checkpoint(token=token)
        local_start = P.OUTPUT_ROOT / P.Plan.START_DIRECTORY / f"{token}.json"
        local_report = P.OUTPUT_ROOT / P.Launch.REPORT_DIRECTORY / f"{token}.json"
        report = _write_lower_report(
            token=token, checkpoint=checkpoint, status="complete"
        )
        return {**report, "report_path": str(local_report)}

    monkeypatch.setattr(P.Launch, "launch_exp2a_repairs", run)
    return P.launch(expected_git_commit=COMMIT)


def _arm_control(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    _preflight(monkeypatch)
    preflight = P._load_preflight(COMMIT)
    return P._publish_receipt(
        "launch-control",
        status="armed_before_blocking_launch",
        purpose="outcome_blind_control_identity_published_before_blocking_launch",
        payload=P._control_payload(COMMIT, preflight),
    )


def _write_real_shape_checkpoint(*, token: str = "2" * 32) -> dict[str, object]:
    control = P._load_control(monitor_only=True)
    payload = control["payload"]
    start = {
        "exp2a_repair_start_schema_version": P.Launch.START_SCHEMA_VERSION,
        "purpose": "source_verified_week8_exp2a_repair_start",
        "plan_digest": payload["plan_digest"],
        "preflight": {
            "path": payload["preflight"]["path"],
            "sha256": payload["preflight"]["sha256"],
            "binding_sha256": "d" * 64,
        },
        "source_ledger": {
            "path": payload["source_ledger"]["path"],
            "sha256": payload["source_ledger"]["sha256"],
            "ledger_digest": "b" * 64,
        },
        "environment": _environment(COMMIT),
        "roots": payload["roots"],
        "attempt_timeout_seconds": P.ATTEMPT_TIMEOUT_SECONDS,
        "lease": {
            "path": str(
                P.Plan.COMMON_LEASE_ROOT
                / "leases"
                / f"{P.Plan.COMMON_LEASE_NAME}.lease.json"
            ),
            "sha256": "e" * 64,
            "name": P.Plan.COMMON_LEASE_NAME,
            "token": token,
            "started_at": "synthetic-operational-time",
        },
        "fixed_worker": "bu.experiments.week8_exp2a_repair_launch._fit_worker",
        "supervisor_required": "bu.experiments.supervisor.run_isolated_attempt",
        "automatic_retry_allowed": False,
    }
    context = P.Launch._execution_context(start)
    document = P.Plan._seal(
        {**start, "execution_context_digest": context["execution_context_digest"]},
        "checkpoint_digest",
    )
    for root in (P.OUTPUT_ROOT, P.SYNC_ROOT):
        atomic_write_json(root / P.Plan.START_DIRECTORY / f"{token}.json", document)
    return document


def _event(
    *,
    sequence: int,
    previous: str | None,
    context: str,
    kind: str,
    job_id: str | None,
    data: dict[str, object],
) -> dict[str, object]:
    return P.Plan._seal(
        {
            "event_schema_version": 1,
            "sequence": sequence,
            "previous_digest": previous,
            "execution_context_digest": context,
            "kind": kind,
            "job_id": job_id,
            "data": data,
        },
        "event_digest",
    )


def _write_event(row: dict[str, object]) -> None:
    name = f"{row['sequence']:06d}.json"
    for root in (P.OUTPUT_ROOT, P.SYNC_ROOT):
        atomic_write_json(root / P.Launch.EVENT_DIRECTORY / name, row)


def _finalization_document() -> dict[str, object]:
    counts = {
        "registered_units": 20,
        "twenty_seed_units": 4,
        "three_seed_units": 16,
        "labelled_units": 20,
        "pending_units": 0,
        "blocked_units": 0,
        "observed": {
            "observed_0": 0,
            "observed_1": 0,
            "ambiguous": 0,
            "undiagnosed": 20,
        },
        "historical_fits_preserved": 155,
        "historical_fits_required": 123,
        "non_label_historical_fits": 32,
        "new_fit_obligations": 261,
        "label_required_fits": 384,
        "verified_source_pairs": 384,
        "pending_new_fits": 0,
        "exported_fit_trees_per_root": 384,
        "executed_fits": 0,
        "retrained_fits": 0,
    }
    return P.Plan._seal(
        {
            "week8_exp2a_label_finalization_schema_version": P.Finalize.FINALIZATION_SCHEMA_VERSION,
            "purpose": "exact_week8_experiment2a_label_finalization",
            "status": "complete",
            "inputs": {"synthetic": True},
            "finalizer": {"git_commit": COMMIT},
            "plan_digest": "a" * 64,
            "ledger_digest": "b" * 64,
            "execution_context_digest": "c" * 64,
            "source_inventory_digest": "d" * 64,
            "roots": {"synthetic": True},
            "counts": counts,
            "pending_new_fit_ids": [],
            "non_label_existing_fit_ids": [f"old-{index:02d}" for index in range(32)],
            "units": [{"unit_id": f"unit-{index:02d}"} for index in range(20)],
        },
        "manifest_digest",
    )


def _write_reporting_binding(
    inputs: object,
    *,
    report_path: Path,
    report_copy_path: Path,
    binding_receipt_path: Path,
    count_overrides: dict[str, int] | None = None,
) -> dict[str, object]:
    report_document = {"synthetic": "descriptive report", "h2_verdict": None}
    atomic_write_json(report_path, report_document)
    atomic_write_json(report_copy_path, report_document)
    digest = sha256_file(report_path)
    document = P.Plan._seal(
        {
            "week8_exp2a_reporting_adapter_schema_version": P.Reporting.REPORTING_ADAPTER_SCHEMA_VERSION,
            "purpose": "bind_rederived_week8_exp2a_sources_to_descriptive_report",
            "status": "complete",
            "binding_receipt_path": str(binding_receipt_path.resolve()),
            "fits_executed": 0,
            "labels_created": 0,
            "sign_consistency_applied": False,
            "h2_verdict": None,
            "reporting_environment": {"git_commit": COMMIT},
            "upstream": {
                "plan": {"path": "synthetic", "sha256": "a" * 64},
                "source_ledger": {"path": "synthetic", "sha256": "b" * 64},
                "checkpoint": {"path": "synthetic", "sha256": "c" * 64},
                "expected_execution_commit": COMMIT,
                "expected_finalizer_commit": COMMIT,
                "expected_reporting_commit": COMMIT,
                "finalization": {
                    "export_manifest_path": "synthetic",
                    "durable_manifest_path": "synthetic-copy",
                    "sha256": inputs.expected_finalization_manifest_sha256,
                    "manifest_digest": "d" * 64,
                },
            },
            "report": {
                "path": str(report_path.resolve()),
                "copy_path": str(report_copy_path.resolve()),
                "sha256": digest,
                "payload_sha256": "e" * 64,
                "source_inventory_sha256": "f" * 64,
                "independent_copy": True,
            },
            "counts": {**P._REPORTING_COUNTS, **(count_overrides or {})},
        },
        "receipt_digest",
    )
    atomic_write_json(binding_receipt_path, document)
    return document


def test_production_constants_are_exact_attempt_001() -> None:
    assert P._REGISTERED_WORKSPACE_ROOT == Path("D:/Aenv/pro/pro")
    assert P.WORKSPACE_ROOT == Path("D:/Aenv/pro/pro")
    assert {name: path.name for name, path in P._fixed_roots().items()} == {
        "preparation": "week8-execution-preparation-2026-09-01-attempt-001",
        "preparation_original": "exp2a-original",
        "preparation_copy": "exp2a-project-evidence",
        "preflight": "week8-exp2a-2026-09-01-attempt-001-preflight",
        "output": "week8-exp2a-2026-09-01-attempt-001-output",
        "staging": "week8-exp2a-2026-09-01-attempt-001-staging",
        "sync": "week8-exp2a-2026-09-01-attempt-001-project-evidence",
        "label_export": "week8-exp2a-labels-2026-09-01-attempt-001",
        "label_copy": "week8-exp2a-labels-2026-09-01-attempt-001-project-evidence",
        "report": "week8-exp2a-report-2026-09-01-attempt-001",
        "report_copy": "week8-exp2a-report-2026-09-01-attempt-001-project-evidence",
        "figures": "week8-exp2a-figures-2026-09-01-attempt-001",
        "figure_cache": "week8-exp2a-figures-2026-09-01-attempt-001-mpl-cache",
        "monitor": "week8-exp2a-monitor-2026-09-01-attempt-001",
        "monitor_copy": "week8-exp2a-monitor-2026-09-01-attempt-001-project-evidence",
    }
    assert P.PREPARATION_ORIGINAL_ROOT.parent == P.PREPARATION_ROOT
    assert P.PREPARATION_COPY_ROOT.parent == P.PREPARATION_ROOT
    assert all(
        path.parent == P.WORKSPACE_ROOT
        for name, path in P._fixed_roots().items()
        if name not in {"preparation_original", "preparation_copy"}
    )
    assert P.ATTEMPT_TIMEOUT_SECONDS == 3600.0
    assert P.MINIMUM_FREE_BYTES == 8_589_934_592
    assert P.Plan.COMMON_LEASE_NAME == "week7-production"


def test_cli_has_exact_seven_subcommands_and_no_path_arguments() -> None:
    parser = P._parser()
    choices = next(
        action.choices for action in parser._actions if hasattr(action, "choices") and action.choices
    )
    assert set(choices) == {
        "prepare",
        "preflight",
        "launch",
        "monitor",
        "finalize",
        "report",
        "figures",
    }
    with pytest.raises(SystemExit):
        parser.parse_args(["prepare", "--output-root", "elsewhere"])


def test_prepare_publishes_plan_ledger_receipt_and_independent_copies(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _prepare(monkeypatch)
    assert result["status"] == "complete"
    receipt = P._load_prepare(COMMIT)
    for key in ("plan", "source_ledger"):
        row = receipt["payload"][key]
        assert Path(row["path"]).read_bytes() == Path(row["copy_path"]).read_bytes()
        assert row["sha256"] == sha256_file(row["path"])
        assert Path(row["path"]).stat().st_ino != Path(row["copy_path"]).stat().st_ino
    assert receipt["payload"]["execution_authorized"] is False
    assert receipt["payload"]["route"]["gpu_used"] is False


def test_preflight_uses_only_frozen_values_and_automatic_preparation_pins(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare(monkeypatch)
    calls = _stub_preflight(monkeypatch)
    result = P.preflight(expected_git_commit=COMMIT)
    assert result["status"] == "ready"
    assert calls["attempt_timeout_seconds"] == 3600.0
    assert calls["minimum_free_bytes"] == 8_589_934_592
    assert calls["sync_destination_identity"] == P.SYNC_DESTINATION_IDENTITY
    assert calls["plan_path"] == P.PREPARATION_ORIGINAL_ROOT / P.Plan.PLAN_FILE
    assert calls["source_ledger_path"] == (
        P.PREPARATION_ORIGINAL_ROOT / P.Sources.SOURCE_LEDGER_FILE
    )
    assert P._load_preflight(COMMIT)["payload"]["shared_lease"]["name"] == "week7-production"


def test_launch_control_exists_before_blocking_lower_launch(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _synthetic_launch(monkeypatch)
    assert result["status"] == "complete"
    control = P._load_control(COMMIT)
    assert control["status"] == "armed_before_blocking_launch"
    assert control["payload"]["expected_physical_fits"] == 261
    assert control["payload"]["expected_member_models"] == 441
    assert control["payload"]["automatic_retry_allowed"] is False
    assert P._load_launch(COMMIT)["payload"]["checkpoint"]["sha256"]


def test_existing_valid_launch_receipt_is_idempotent_without_lower_reentry(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _synthetic_launch(monkeypatch)
    monkeypatch.setattr(
        P.Launch,
        "launch_exp2a_repairs",
        lambda **kwargs: pytest.fail("completed launch was re-entered"),
    )
    second = P.launch(expected_git_commit=COMMIT)
    assert second == first
    assert len(list((P.OUTPUT_ROOT / P.Plan.START_DIRECTORY).glob("*.json"))) == 1
    assert len(list((P.OUTPUT_ROOT / P.Launch.REPORT_DIRECTORY).glob("*.json"))) == 1


def test_lost_response_recovers_one_exact_complete_lower_report_without_fitting(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    token = "3" * 32
    checkpoint = _write_real_shape_checkpoint(token=token)
    _write_lower_report(token=token, checkpoint=checkpoint)
    monkeypatch.setattr(
        P.Launch,
        "launch_exp2a_repairs",
        lambda **kwargs: pytest.fail("lost-response recovery entered fitting"),
    )
    result = P.launch(expected_git_commit=COMMIT)
    assert result["status"] == "complete"
    handoff = P._load_launch(COMMIT)
    assert handoff["payload"]["lower_counts"] == {
        "executed": 261,
        "resumed": 0,
        "synced": 261,
        "total": 261,
    }


def test_checkpoint_without_terminal_report_blocks_lower_reentry(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    _write_real_shape_checkpoint(token="4" * 32)
    monkeypatch.setattr(
        P.Launch,
        "launch_exp2a_repairs",
        lambda **kwargs: pytest.fail("preserved checkpoint entered fitting"),
    )
    with pytest.raises(ValueError, match="checkpoint.*will not be rerun"):
        P.launch(expected_git_commit=COMMIT)


def test_incomplete_lower_report_blocks_launch_and_overrides_monitor_blindly(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    token = "5" * 32
    secret = "SECRET TERMINAL SCIENTIFIC FAILURE TEXT"
    _write_lower_report(
        token=token,
        checkpoint=None,
        status="incomplete",
        counts={"executed": 0, "resumed": 0, "synced": 0, "total": 261},
        failure={"type": "SyntheticFailure", "message": secret},
    )
    monkeypatch.setattr(
        P.Launch,
        "launch_exp2a_repairs",
        lambda **kwargs: pytest.fail("stopped report entered fitting"),
    )
    with pytest.raises(ValueError, match="incomplete/interrupted"):
        P.launch(expected_git_commit=COMMIT)
    result = P.monitor()
    assert result["status"] == "stopped_with_preserved_failure"
    snapshot_text = Path(result["snapshot_path"]).read_text(encoding="utf-8")
    snapshot = read_json(result["snapshot_path"])
    assert secret not in snapshot_text
    assert snapshot["terminal_report"]["status"] == "incomplete"
    assert snapshot["terminal_report"]["failure_sha256"]
    assert snapshot["failure_text_included"] is False


def test_complete_lower_report_with_wrong_counts_never_becomes_handoff(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    token = "6" * 32
    checkpoint = _write_real_shape_checkpoint(token=token)
    _write_lower_report(
        token=token,
        checkpoint=checkpoint,
        counts={"executed": 260, "resumed": 0, "synced": 260, "total": 261},
    )
    monkeypatch.setattr(
        P.Launch,
        "launch_exp2a_repairs",
        lambda **kwargs: pytest.fail("wrong accounting entered fitting"),
    )
    with pytest.raises(ValueError, match="complete lower launch report"):
        P.launch(expected_git_commit=COMMIT)
    assert not P._receipt_present("launch")


def test_complete_lower_report_with_resumed_fit_never_becomes_handoff(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    token = "7" * 32
    checkpoint = _write_real_shape_checkpoint(token=token)
    _write_lower_report(
        token=token,
        checkpoint=checkpoint,
        counts={"executed": 260, "resumed": 1, "synced": 261, "total": 261},
    )
    monkeypatch.setattr(
        P.Launch,
        "launch_exp2a_repairs",
        lambda **kwargs: pytest.fail("resumed accounting entered fitting"),
    )
    with pytest.raises(ValueError, match="complete lower launch report"):
        P.launch(expected_git_commit=COMMIT)
    assert not P._receipt_present("launch")


def test_monitor_waits_without_discovering_or_creating_scientific_files(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    monkeypatch.setattr(
        P.Launch,
        "_load_events",
        lambda *args, **kwargs: pytest.fail("mutating event loader was called"),
    )
    monkeypatch.setattr(
        P.Finalize,
        "load_exp2a_label_finalization",
        lambda *args, **kwargs: pytest.fail("label reader was called"),
    )
    monkeypatch.setattr(
        P.Fit,
        "load_fit_evidence",
        lambda *args, **kwargs: pytest.fail("fit reader was called"),
    )
    monkeypatch.setattr(
        P.Reporting,
        "write_source_bound_exp2a_report",
        lambda *args, **kwargs: pytest.fail("report writer was called"),
    )
    monkeypatch.setattr(
        P.Figures,
        "prepare_experiment_2a_figures",
        lambda *args, **kwargs: pytest.fail("figure reader was called"),
    )
    result = P.monitor()
    assert result["status"] == "awaiting_checkpoint"
    assert result["counts"] == {
        "expected": 261,
        "started": 0,
        "synced": 0,
        "failed": 0,
        "sync_pending": 0,
        "remaining": 261,
    }
    assert not (P.OUTPUT_ROOT / "jobs").exists()
    assert P.validate_monitor_snapshot(result["snapshot_path"])["scientific_files_opened"] is False


def test_monitor_hashes_failure_text_and_never_persists_or_prints_it(
    fixed_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _arm_control(monkeypatch)
    checkpoint = _write_real_shape_checkpoint()
    job_id = P.Plan.new_exp2a_jobs()[0].job_id
    started = _event(
        sequence=0,
        previous=None,
        context=checkpoint["execution_context_digest"],
        kind="attempt_started",
        job_id=job_id,
        data={"checkpoint_digest": checkpoint["checkpoint_digest"]},
    )
    secret = "SECRET LABEL RATIO SCIENTIFIC OUTCOME"
    failed = _event(
        sequence=1,
        previous=started["event_digest"],
        context=checkpoint["execution_context_digest"],
        kind="attempt_failed",
        job_id=job_id,
        data={"type": "SyntheticFailure", "message": secret},
    )
    _write_event(started)
    _write_event(failed)
    monkeypatch.setattr(
        P.Launch,
        "_load_events",
        lambda *args, **kwargs: pytest.fail("mutating event loader was called"),
    )
    result = P.monitor()
    printed = json.dumps(result) + capsys.readouterr().out
    local_bytes = Path(result["snapshot_path"]).read_text(encoding="utf-8")
    assert secret not in printed
    assert secret not in local_bytes
    snapshot = read_json(result["snapshot_path"])
    assert snapshot["status"] == "stopped_with_preserved_failure"
    assert snapshot["preserved_failures"][0]["failure_sha256"]
    assert snapshot["failure_text_included"] is False
    assert P.validate_monitor_snapshot(result["snapshot_path"]) == snapshot


def test_monitor_rejects_missing_event_twin_without_healing_it(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    checkpoint = _write_real_shape_checkpoint()
    job_id = P.Plan.new_exp2a_jobs()[0].job_id
    row = _event(
        sequence=0,
        previous=None,
        context=checkpoint["execution_context_digest"],
        kind="attempt_started",
        job_id=job_id,
        data={"checkpoint_digest": checkpoint["checkpoint_digest"]},
    )
    path = P.OUTPUT_ROOT / P.Launch.EVENT_DIRECTORY / "000000.json"
    atomic_write_json(path, row)
    missing = P.SYNC_ROOT / P.Launch.EVENT_DIRECTORY / "000000.json"
    with pytest.raises(ValueError, match="inventories differ"):
        P.monitor()
    assert path.exists()
    assert not missing.exists(), "read-only monitor must not heal a missing twin"


def test_monitor_snapshot_is_revalidatable_and_stale_after_source_change(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    checkpoint = _write_real_shape_checkpoint()
    first = P.monitor()
    assert P.validate_monitor_snapshot(first["snapshot_path"])["status"] == "running"
    job_id = P.Plan.new_exp2a_jobs()[0].job_id
    _write_event(
        _event(
            sequence=0,
            previous=None,
            context=checkpoint["execution_context_digest"],
            kind="attempt_started",
            job_id=job_id,
            data={"checkpoint_digest": checkpoint["checkpoint_digest"]},
        )
    )
    with pytest.raises(ValueError, match="stale"):
        P.validate_monitor_snapshot(first["snapshot_path"])


def test_monitor_rejects_snapshot_destination_outside_fixed_roots(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm_control(monkeypatch)
    document = P._monitor_material()
    outside = fixed_workspace / "outside.json"
    atomic_write_json(outside, document)
    with pytest.raises(ValueError, match="outside"):
        P.validate_monitor_snapshot(outside)


def test_finalize_automatically_carries_plan_ledger_checkpoint_and_commits(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _synthetic_launch(monkeypatch)
    observed: dict[str, object] = {}

    def finish(inputs: object, *, export_root: Path, durable_copy_root: Path):
        observed["inputs"] = inputs
        assert export_root == P.LABEL_EXPORT_ROOT
        assert durable_copy_root == P.LABEL_COPY_ROOT
        document = _finalization_document()
        document["units"][0]["secret_observed_label"] = 1
        document = P.Plan._seal(
            {key: value for key, value in document.items() if key != "manifest_digest"},
            "manifest_digest",
        )
        atomic_write_json(export_root / P.Finalize.MANIFEST_FILE, document)
        atomic_write_json(durable_copy_root / P.Finalize.MANIFEST_FILE, document)
        return document

    monkeypatch.setattr(P.Finalize, "finalize_exp2a_labels", finish)
    monkeypatch.setattr(
        P.Finalize,
        "load_exp2a_label_finalization",
        lambda *args, **kwargs: read_json(P.LABEL_EXPORT_ROOT / P.Finalize.MANIFEST_FILE),
    )
    result = P.finalize(expected_git_commit=COMMIT)
    inputs = observed["inputs"]
    prepare_receipt = P._load_prepare(COMMIT)
    launch_receipt = P._load_launch(COMMIT)
    assert inputs.plan_sha256 == prepare_receipt["payload"]["plan"]["sha256"]
    assert inputs.source_ledger_sha256 == prepare_receipt["payload"]["source_ledger"]["sha256"]
    assert inputs.checkpoint_sha256 == launch_receipt["payload"]["checkpoint"]["sha256"]
    assert inputs.expected_execution_commit == COMMIT
    assert inputs.expected_finalizer_commit == COMMIT
    assert "secret_observed_label" not in json.dumps(result)

    loaded_finalize = P._load_receipt("finalize")
    forged_body = {
        key: value
        for key, value in loaded_finalize.items()
        if key not in {"_file_sha256", "receipt_digest"}
    }
    forged_payload = dict(forged_body["payload"])
    forged_payload["expected_finalizer_commit"] = "d" * 40
    forged_body["payload"] = forged_payload
    forged = P.Plan._seal(forged_body, "receipt_digest")
    forged["_file_sha256"] = loaded_finalize["_file_sha256"]
    load_receipt = P._load_receipt
    monkeypatch.setattr(
        P,
        "_load_receipt",
        lambda phase: forged if phase == "finalize" else load_receipt(phase),
    )
    with pytest.raises(ValueError, match="ordinary E2A launch requires identical"):
        P._load_finalize("d" * 40)


def test_finalize_rejects_cross_commit_pair_for_ordinary_launch(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _synthetic_launch(monkeypatch)
    finalizer_commit = "d" * 40
    with pytest.raises(ValueError, match="ordinary E2A launch requires identical"):
        P.finalize(
            expected_git_commit=finalizer_commit,
            expected_execution_commit=COMMIT,
        )
    assert not P._receipt_present("finalize")


def test_execution_finalizer_pair_exception_is_exactly_d161_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller_commit = "d" * 40
    ordinary = {"payload": {"expected_git_commit": COMMIT}}
    with pytest.raises(ValueError, match="ordinary E2A launch requires identical"):
        P._validate_execution_finalizer_pair(
            ordinary,
            execution_commit=COMMIT,
            finalizer_commit=controller_commit,
        )

    recovery_payload = {
        "expected_git_commit": COMMIT,
        "recovery": {"decision_id": "D-161"},
    }
    recovered = {"payload": recovery_payload}
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        Recovery,
        "validate_completed_recovery",
        lambda value: calls.append(dict(value))
        or {
            "status": "complete",
            "execution_commit": COMMIT,
            "controller_commit": controller_commit,
        },
    )
    P._validate_execution_finalizer_pair(
        recovered,
        execution_commit=COMMIT,
        finalizer_commit=controller_commit,
    )
    assert calls == [recovery_payload]
    with pytest.raises(ValueError, match="exact execution/controller commit pair"):
        P._validate_execution_finalizer_pair(
            recovered,
            execution_commit=COMMIT,
            finalizer_commit="e" * 40,
        )


def test_load_launch_delegates_exact_recovery_payload(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "expected_git_commit": COMMIT,
        "recovery": {"decision_id": "D-161"},
    }
    receipt = P._publish_receipt(
        "launch",
        status="complete",
        purpose="bind_d161_recovered_261_fit_e2a_repair_launch",
        payload=payload,
    )
    seen: list[dict[str, object]] = []
    monkeypatch.setattr(
        Recovery,
        "validate_completed_recovery",
        lambda value: seen.append(dict(value))
        or {
            "status": "complete",
            "execution_commit": COMMIT,
            "controller_commit": "d" * 40,
        },
    )
    assert P._load_launch(COMMIT) == receipt
    assert seen == [payload]


@pytest.mark.parametrize(
    "record_name",
    [
        Recovery.INCIDENT_FILE,
        Recovery.EPOCH001_TERMINAL_FILE,
        Recovery.TRANSITION_INTENT_FILE,
        Recovery.TRANSITION_COMPLETION_FILE,
        Recovery.BOOTSTRAP_INVOCATION_FILE,
        Recovery.BOOTSTRAP_CLAIM_FILE,
        Recovery.BOOTSTRAP_TERMINAL_FILE,
        Recovery.RECOVERY_COMPLETION_FILE,
    ],
)
@pytest.mark.parametrize("twin_index", [0, 1])
def test_monitor_routes_every_one_sided_recovery_record_to_recovery_validator(
    fixed_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    record_name: str,
    twin_index: int,
) -> None:
    monkeypatch.setattr(Recovery, "RECOVERY_ROOT", fixed_workspace / "recovery")
    monkeypatch.setattr(
        Recovery, "RECOVERY_COPY_ROOT", fixed_workspace / "recovery-copy"
    )
    monkeypatch.setattr(Recovery, "WORKSPACE_ROOT", fixed_workspace)
    path = Recovery._record_paths(record_name)[twin_index]
    path.parent.mkdir(parents=True)
    path.write_text("present", encoding="utf-8")
    expected = {
        "week8_exp2a_monitor_schema_version": P.MONITOR_SCHEMA_VERSION,
        "status": "complete",
        "snapshot_digest": "f" * 64,
    }
    calls: list[bool] = []
    monkeypatch.setattr(
        Recovery,
        "recovery_monitor_material",
        lambda: calls.append(True) or expected,
    )
    assert P._monitor_material() == expected
    assert calls == [True]


def test_monitor_real_recovery_validator_refuses_partial_bootstrap_twin(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Recovery, "RECOVERY_ROOT", fixed_workspace / "recovery")
    monkeypatch.setattr(
        Recovery, "RECOVERY_COPY_ROOT", fixed_workspace / "recovery-copy"
    )
    monkeypatch.setattr(Recovery, "WORKSPACE_ROOT", fixed_workspace)
    claim, _ = Recovery._record_paths(Recovery.BOOTSTRAP_CLAIM_FILE)
    claim.parent.mkdir(parents=True)
    claim.write_text("partial", encoding="utf-8")
    monkeypatch.setattr(
        P,
        "_load_control",
        lambda *args, **kwargs: pytest.fail("ordinary monitor path was entered"),
    )
    with pytest.raises(Recovery.RecoveryRefused):
        P._monitor_material()


def test_relocated_monitor_ignores_recovery_records_from_another_workspace(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign = fixed_workspace / "foreign"
    monkeypatch.setattr(Recovery, "WORKSPACE_ROOT", foreign)
    monkeypatch.setattr(Recovery, "RECOVERY_ROOT", foreign / "recovery")
    monkeypatch.setattr(Recovery, "RECOVERY_COPY_ROOT", foreign / "recovery-copy")
    incident, _ = Recovery._record_paths(Recovery.INCIDENT_FILE)
    incident.parent.mkdir(parents=True)
    incident.write_text("foreign", encoding="utf-8")
    monkeypatch.setattr(
        Recovery,
        "recovery_monitor_material",
        lambda: pytest.fail("foreign recovery evidence was consulted"),
    )
    control = _arm_control(monkeypatch)
    document = P._monitor_material()
    assert document["status"] == "awaiting_checkpoint"
    assert document["control"]["sha256"] == control["_file_sha256"]


def test_finalize_rejects_lower_manifest_with_wrong_384_accounting(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _synthetic_launch(monkeypatch)

    def finish(inputs: object, *, export_root: Path, durable_copy_root: Path):
        document = _finalization_document()
        document["counts"]["exported_fit_trees_per_root"] = 383
        document = P.Plan._seal(
            {key: value for key, value in document.items() if key != "manifest_digest"},
            "manifest_digest",
        )
        atomic_write_json(export_root / P.Finalize.MANIFEST_FILE, document)
        atomic_write_json(durable_copy_root / P.Finalize.MANIFEST_FILE, document)
        return document

    monkeypatch.setattr(P.Finalize, "finalize_exp2a_labels", finish)
    monkeypatch.setattr(
        P.Finalize,
        "load_exp2a_label_finalization",
        lambda *args, **kwargs: read_json(P.LABEL_EXPORT_ROOT / P.Finalize.MANIFEST_FILE),
    )
    with pytest.raises(ValueError, match="exported_fit_trees_per_root"):
        P.finalize(expected_git_commit=COMMIT)
    assert not P._receipt_present("finalize")


def test_report_and_figures_use_automatic_manifest_and_report_sha_handoffs(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _synthetic_launch(monkeypatch)

    def finish(inputs: object, *, export_root: Path, durable_copy_root: Path):
        document = _finalization_document()
        atomic_write_json(export_root / P.Finalize.MANIFEST_FILE, document)
        atomic_write_json(durable_copy_root / P.Finalize.MANIFEST_FILE, document)
        return document

    monkeypatch.setattr(P.Finalize, "finalize_exp2a_labels", finish)
    monkeypatch.setattr(
        P.Finalize,
        "load_exp2a_label_finalization",
        lambda *args, **kwargs: read_json(P.LABEL_EXPORT_ROOT / P.Finalize.MANIFEST_FILE),
    )
    P.finalize(expected_git_commit=COMMIT)
    observed: dict[str, object] = {}

    def write_report(inputs: object, **kwargs: Path):
        observed["publication"] = inputs
        return _write_reporting_binding(inputs, **kwargs)

    monkeypatch.setattr(P.Reporting, "write_source_bound_exp2a_report", write_report)
    monkeypatch.setattr(
        P.Figures.R,
        "load_experiment_2a_report",
        lambda *args, **kwargs: {"h2_verdict": None},
    )
    report_result = P.report(expected_git_commit=COMMIT)
    finalize_receipt = P._load_finalize(COMMIT)
    publication = observed["publication"]
    assert publication.expected_finalization_manifest_sha256 == (
        finalize_receipt["payload"]["manifest"]["sha256"]
    )
    report_receipt = P._load_report()
    expected_report_sha = report_receipt["payload"]["report"]["sha256"]
    assert report_result["receipt_sha256"] == report_receipt["_file_sha256"]

    def render(report_path: Path, *, expected_report_sha256: str, figures_dir: Path):
        assert report_path == Path(report_receipt["payload"]["report"]["path"])
        assert expected_report_sha256 == expected_report_sha
        assert figures_dir == P.FIGURE_ROOT
        paths = []
        rows = []
        for name in (P.Figures.FOREST_FILE, P.Figures.RATIO_FILE, P.Figures.PEARSON_FILE):
            path = figures_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = f"synthetic png:{name}".encode()
            path.write_bytes(data)
            paths.append(path)
            rows.append(
                {"filename": name, "kind": f"synthetic:{name}", "sha256": sha256_bytes(data)}
            )
        manifest_document = P.Plan._seal(
            {
                "experiment_2a_figure_schema_version": P.Figures.FIGURE_SCHEMA_VERSION,
                "kind": "offline_experiment_2a_figures",
                "interpretation": "synthetic outcome-free figure fixture",
                "source_report_sha256": expected_report_sha256,
                "source_report_payload_sha256": "a" * 64,
                "plot_data_sha256": "b" * 64,
                "unit_count": 20,
                "seed_count": 5,
                "figure_count": 3,
                "figures": rows,
                "sign_consistency": None,
                "h2_verdict": None,
            },
            "payload_sha256",
        )
        manifest = atomic_write_json(
            figures_dir / P.Figures.MANIFEST_FILE,
            manifest_document,
        )
        return [*paths, manifest]

    monkeypatch.setattr(P.Figures, "prepare_experiment_2a_figures", render)
    figure_result = P.figures(expected_git_commit=COMMIT)
    assert figure_result["status"] == "complete"
    figure_receipt = P._load_receipt("figures")
    assert figure_receipt["payload"]["source_report"]["sha256"] == expected_report_sha
    assert figure_receipt["payload"]["renderer_commit"] == COMMIT
    assert figure_receipt["payload"]["counts"] == {
        "units": 20,
        "seeds": 5,
        "figures": 3,
    }
    assert Path(P.FIGURE_CACHE_ROOT).is_dir()


def test_report_rejects_lower_binding_with_wrong_416_accounting(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _synthetic_launch(monkeypatch)

    def finish(inputs: object, *, export_root: Path, durable_copy_root: Path):
        document = _finalization_document()
        atomic_write_json(export_root / P.Finalize.MANIFEST_FILE, document)
        atomic_write_json(durable_copy_root / P.Finalize.MANIFEST_FILE, document)
        return document

    monkeypatch.setattr(P.Finalize, "finalize_exp2a_labels", finish)
    monkeypatch.setattr(
        P.Finalize,
        "load_exp2a_label_finalization",
        lambda *args, **kwargs: read_json(P.LABEL_EXPORT_ROOT / P.Finalize.MANIFEST_FILE),
    )
    P.finalize(expected_git_commit=COMMIT)

    def wrong_binding(inputs: object, **kwargs: Path):
        return _write_reporting_binding(
            inputs, **kwargs, count_overrides={"union_fits": 415}
        )

    monkeypatch.setattr(P.Reporting, "write_source_bound_exp2a_report", wrong_binding)
    with pytest.raises(ValueError, match="416/384"):
        P.report(expected_git_commit=COMMIT)
    assert not P._receipt_present("report")


@pytest.mark.parametrize(
    "command,requires_commit",
    [
        ("prepare", True),
        ("preflight", True),
        ("launch", True),
        ("monitor", False),
        ("finalize", True),
        ("report", True),
        ("figures", True),
    ],
)
def test_main_dispatches_each_command_without_path_or_scientific_output(
    command: str,
    requires_commit: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, object]] = []

    def handler(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {
            "command": command,
            "status": "ready",
            "receipt_sha256": "f" * 64,
        }

    monkeypatch.setattr(P, command.replace("-", "_"), handler)
    argv = [command]
    if requires_commit:
        argv.extend(["--expected-git-commit", COMMIT])
    assert P.main(argv) == 0
    expected = {"expected_git_commit": COMMIT} if requires_commit else {}
    assert calls == [expected]
    output = capsys.readouterr().out
    assert "label" not in output.lower()
    assert "ratio" not in output.lower()
    assert "scientific" not in output.lower()


def test_main_forwards_recovery_execution_commit_only_to_finalize(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    controller_commit = "d" * 40
    calls: list[dict[str, object]] = []

    def handler(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {"command": "finalize", "status": "complete"}

    monkeypatch.setattr(P, "finalize", handler)
    assert (
        P.main(
            [
                "finalize",
                "--expected-git-commit",
                controller_commit,
                "--expected-execution-commit",
                COMMIT,
            ]
        )
        == 0
    )
    assert calls == [
        {
            "expected_git_commit": controller_commit,
            "expected_execution_commit": COMMIT,
        }
    ]
    assert "label" not in capsys.readouterr().out.lower()


@pytest.mark.parametrize(
    ("command", "kwargs"),
    [
        ("monitor", {}),
        ("finalize", {"expected_git_commit": COMMIT}),
        ("report", {"expected_git_commit": COMMIT}),
        ("figures", {"expected_git_commit": COMMIT}),
    ],
)
def test_registered_e2a_downstream_functions_refuse_without_d166_capability(
    command: str,
    kwargs: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(P, "_d166_controller_capability_required", lambda: True)
    handler = getattr(P, command)
    with pytest.raises(ValueError, match="captured controller capability"):
        handler(**kwargs)


def test_exact_d166_capability_is_identity_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(P, "_d166_controller_capability_required", lambda: True)
    P._require_d166_controller_capability(P._D166_CONTROLLER_CAPABILITY)
    with pytest.raises(ValueError, match="captured controller capability"):
        P._require_d166_controller_capability(object())


def test_main_sanitizes_exception_text_and_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "SECRET LABEL RATIO OUTCOME PATH"

    def fail(**kwargs: object) -> dict[str, object]:
        raise ValueError(secret)

    monkeypatch.setattr(P, "prepare", fail)
    assert P.main(["prepare", "--expected-git-commit", COMMIT]) == 1
    output = capsys.readouterr().out
    assert secret not in output
    assert "traceback" not in output.lower()
    document = json.loads(output)
    assert document == {
        "command": "prepare",
        "error": {
            "type": "ValueError",
            "sha256": sha256_bytes(
                P._canonical({"type": "ValueError", "message": secret})
            ),
        },
        "status": "stopped_with_preserved_failure",
    }


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(7)])
def test_main_does_not_swallow_process_control_exceptions(
    error: BaseException, monkeypatch: pytest.MonkeyPatch
) -> None:
    def stop(**kwargs: object) -> dict[str, object]:
        raise error

    monkeypatch.setattr(P, "prepare", stop)
    with pytest.raises(type(error)):
        P.main(["prepare", "--expected-git-commit", COMMIT])


def test_phase_receipt_divergence_fails_closed(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare(monkeypatch)
    _, copied = P._receipt_paths("prepare")
    copied.unlink()
    atomic_write_json(copied, {"different": True})
    with pytest.raises(ValueError, match="bytes differ"):
        P._load_prepare(COMMIT)


def test_wrong_commit_and_nonfixed_layout_fail_before_lower_work(
    fixed_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare(monkeypatch)
    with pytest.raises(ValueError, match="differs"):
        P._load_prepare("d" * 40)
    monkeypatch.setattr(P, "OUTPUT_ROOT", fixed_workspace / "elsewhere" / "output")
    with pytest.raises(ValueError, match="exact attempt-001 layout"):
        P._load_prepare(COMMIT)
