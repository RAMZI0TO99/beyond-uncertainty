"""Focused tests for the fixed zero-compute Week-8 exclusion wrapper."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from bu.durable import atomic_write_json, read_json, sha256_file
from bu.experiments import week8_exclusion_production as P


COMMIT = "c" * 40


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _manifest() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for seed, base, base_sha, data, data_sha, model, model_sha in P.PINNED_CONDITIONS:
        rows.extend(
            (
                {
                    "seed": seed,
                    "arm": "baseline",
                    "fit_id": base,
                    "expected_commit": P.EXPECTED_LIBRARY_COMMIT,
                    "execution_digest": base_sha,
                },
                {
                    "seed": seed,
                    "arm": "data_repair",
                    "fit_id": data,
                    "expected_commit": P.EXPECTED_LIBRARY_COMMIT,
                    "execution_digest": data_sha,
                },
                {
                    "seed": seed,
                    "arm": "capacity_repair",
                    "fit_id": model,
                    "expected_commit": P.EXPECTED_LIBRARY_COMMIT,
                    "execution_digest": model_sha,
                },
            )
        )
    return {
        "schema_version": 1,
        "artifact_type": "week7_first_sweep_label_completion",
        "status": "complete",
        "library_commit": P.EXPECTED_LIBRARY_COMMIT,
        "label_file": P.ORDINARY_SWEEP_LABEL_EVIDENCE_FILE,
        "label_sha256": P.EXPECTED_LABEL_SHA256,
        "unit_id": P.Exclusion.FIRST_SWEEP_BATCH_1_UNIT_ID,
        "physical_source_fits": 9,
        "seeds": [1000, 1001, 1002],
        "w8_exclusion_analysis_run": False,
        "sources": rows,
    }


def _summary(source: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "week8_sweep_exclusion_schema_version": 1,
        "kind": "synthetic_source_bound_exclusion_report",
        "batch": {"expected_unit_ids": [P.Exclusion.FIRST_SWEEP_BATCH_1_UNIT_ID]},
        "sources": [
            {
                "label_path": str(Path(source.path).resolve()),
                "label_file_sha256": P.EXPECTED_LABEL_SHA256,
                "label_record_sha256": "a" * 64,
                "verified_label_runs": [],
            }
        ],
        "opaque_synthetic_payload": {"same_for_both_authorities": True},
    }
    payload["source_inventory_sha256"] = _digest(payload["sources"])
    payload["report_digest"] = _digest(payload)
    return payload


@pytest.fixture
def fixed_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, list[Path]]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    original = workspace / "week7-first-sweep-label-2026-08-31-attempt-001"
    copied = (
        workspace
        / "week7-first-sweep-label-2026-08-31-attempt-001-project-evidence"
    )
    output = workspace / "week8-exclusion-2026-09-01-attempt-001"
    output_copy = (
        workspace / "week8-exclusion-2026-09-01-attempt-001-project-evidence"
    )
    monkeypatch.setattr(P, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(P, "LABEL_ORIGINAL_ROOT", original)
    monkeypatch.setattr(P, "LABEL_COPY_ROOT", copied)
    monkeypatch.setattr(P, "OUTPUT_ROOT", output)
    monkeypatch.setattr(P, "OUTPUT_COPY_ROOT", output_copy)
    monkeypatch.setattr(P.Exclusion, "WORKSPACE_ROOT", workspace)

    label_bytes = b'{"synthetic":"portable historical label"}\n'
    for root in (original, copied):
        (root / "sources").mkdir(parents=True)
        for row in P.PINNED_CONDITIONS:
            for name in (row[1], row[3], row[5]):
                (root / "sources" / name).mkdir()
        (root / P.ORDINARY_SWEEP_LABEL_EVIDENCE_FILE).write_bytes(label_bytes)
    monkeypatch.setattr(
        P,
        "EXPECTED_LABEL_SHA256",
        hashlib.sha256(label_bytes).hexdigest(),
    )
    manifest = _manifest()
    for root in (original, copied):
        atomic_write_json(root / P.FINALIZATION_MANIFEST_FILE, manifest)
    manifest_sha = sha256_file(original / P.FINALIZATION_MANIFEST_FILE)
    monkeypatch.setattr(P, "EXPECTED_FINALIZATION_MANIFEST_SHA256", manifest_sha)

    calls: list[Path] = []

    def summarize(labels: object, *, expected_unit_ids: object) -> dict[str, Any]:
        assert expected_unit_ids == P.Exclusion.FIRST_SWEEP_BATCH_1_UNIT_IDS
        assert type(labels) is tuple and len(labels) == 1
        source = labels[0]
        calls.append(Path(source.path).resolve())
        return _summary(source)

    def write_report(
        labels: object, *, expected_unit_ids: object, path: Path
    ) -> dict[str, Any]:
        document = summarize(labels, expected_unit_ids=expected_unit_ids)
        atomic_write_json(path, document)
        return document

    def load_report(
        path: Path, *, labels: object, expected_unit_ids: object
    ) -> dict[str, Any]:
        expected = summarize(labels, expected_unit_ids=expected_unit_ids)
        observed = read_json(path)
        if observed != expected:
            raise ValueError("synthetic lower-boundary report mismatch")
        return expected

    monkeypatch.setattr(P.Exclusion, "summarize_sweep_exclusion", summarize)
    monkeypatch.setattr(P.Exclusion, "write_sweep_exclusion_report", write_report)
    monkeypatch.setattr(P.Exclusion, "load_sweep_exclusion_report", load_report)
    monkeypatch.setattr(
        P,
        "git_state",
        lambda: P.GitState(commit=COMMIT, dirty=False, branch="synthetic"),
    )
    return workspace, calls


def test_constants_pin_exact_attempt_001_authorities() -> None:
    assert P.WORKSPACE_ROOT == Path("D:/Aenv/pro2")
    assert P.LABEL_ORIGINAL_ROOT == Path(
        "D:/Aenv/pro2/week7-first-sweep-label-2026-08-31-attempt-001"
    )
    assert P.LABEL_COPY_ROOT == Path(
        "D:/Aenv/pro2/"
        "week7-first-sweep-label-2026-08-31-attempt-001-project-evidence"
    )
    assert P.OUTPUT_ROOT == Path(
        "D:/Aenv/pro2/week8-exclusion-2026-09-01-attempt-001"
    )
    assert P.OUTPUT_COPY_ROOT == Path(
        "D:/Aenv/pro2/week8-exclusion-2026-09-01-attempt-001-project-evidence"
    )
    assert P.EXPECTED_LABEL_SHA256 == (
        "bf96e423a9e41d811683b58adc9a51136210d4664c0a4cec040096f06217e9f6"
    )
    assert P.EXPECTED_FINALIZATION_MANIFEST_SHA256 == (
        "430839f3094bfb1ecaf18b1220ae43e0d7597b00627aff12c57863c3cdc19d26"
    )
    assert P.EXPECTED_LIBRARY_COMMIT == "1f302d1a05425827229e6ba3f41010a2b003c6f1"
    assert P.Config(unit=P.FIRST_SWEEP_UNIT).unit_id == "0184fbfcd8b9"


def test_nine_sources_and_execution_hashes_are_frozen_exactly() -> None:
    assert tuple(row[0] for row in P.PINNED_CONDITIONS) == (1000, 1001, 1002)
    assert len({name for row in P.PINNED_CONDITIONS for name in (row[1], row[3], row[5])}) == 9
    assert all(
        len(digest) == 64
        for row in P.PINNED_CONDITIONS
        for digest in (row[2], row[4], row[6])
    )
    assert P._manifest_inventory() == {
        (1000, "baseline", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[0][2]),
        (1000, "data_repair", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[0][4]),
        (1000, "capacity_repair", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[0][6]),
        (1001, "baseline", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[1][2]),
        (1001, "data_repair", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[1][4]),
        (1001, "capacity_repair", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[1][6]),
        (1002, "baseline", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[2][2]),
        (1002, "data_repair", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[2][4]),
        (1002, "capacity_repair", P.EXPECTED_LIBRARY_COMMIT, P.PINNED_CONDITIONS[2][6]),
    }


def test_publish_reopens_both_authorities_and_writes_independent_evidence(
    fixed_layout: tuple[Path, list[Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, calls = fixed_layout
    commit_checks: list[P.GitState] = []

    def clean_state() -> P.GitState:
        state = P.GitState(commit=COMMIT, dirty=False, branch="synthetic")
        commit_checks.append(state)
        return state

    monkeypatch.setattr(P, "git_state", clean_state)
    result = P.publish(expected_git_commit=COMMIT)
    assert result == {
        "command": "publish",
        "status": "complete",
        "report_sha256": result["report_sha256"],
        "receipt_sha256": result["receipt_sha256"],
    }
    original_label = (
        workspace
        / "week7-first-sweep-label-2026-08-31-attempt-001"
        / P.ORDINARY_SWEEP_LABEL_EVIDENCE_FILE
    ).resolve()
    copied_label = (
        workspace
        / "week7-first-sweep-label-2026-08-31-attempt-001-project-evidence"
        / P.ORDINARY_SWEEP_LABEL_EVIDENCE_FILE
    ).resolve()
    assert original_label in calls and copied_label in calls
    assert calls.count(copied_label) >= 3

    report = P.OUTPUT_ROOT / P.REPORT_FILE
    report_copy = P.OUTPUT_COPY_ROOT / P.REPORT_FILE
    receipt = P.OUTPUT_ROOT / P.BINDING_FILE
    receipt_copy = P.OUTPUT_COPY_ROOT / P.BINDING_FILE
    assert report.read_bytes() == report_copy.read_bytes()
    assert receipt.read_bytes() == receipt_copy.read_bytes()
    assert not os.path.samefile(report, report_copy)
    assert not os.path.samefile(receipt, receipt_copy)
    assert result["report_sha256"] == sha256_file(report)
    assert result["receipt_sha256"] == sha256_file(receipt)

    binding = read_json(receipt)
    assert binding["status"] == "complete"
    assert binding["reporting_git_commit"] == COMMIT
    assert binding["source_authorities"]["original"]["label"]["sha256"] == P.EXPECTED_LABEL_SHA256
    assert binding["source_authorities"]["independent_copy"]["finalization_manifest"]["sha256"] == P.EXPECTED_FINALIZATION_MANIFEST_SHA256
    assert binding["source_authorities"]["original"]["expected_library_commit"] == P.EXPECTED_LIBRARY_COMMIT
    assert binding["publication"]["report_sha256"] == result["report_sha256"]
    assert binding["execution"] == {
        "physical_fits_executed": 0,
        "models_trained": 0,
        "new_labels_created": 0,
        "source_discovery_performed": False,
    }
    assert len(commit_checks) == 3


def test_reporting_commit_validator_refuses_invalid_dirty_mismatched_or_nonstate(
    fixed_layout: tuple[Path, list[Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert P._require_current_clean_reporting_commit(COMMIT) == COMMIT
    with pytest.raises(ValueError, match="40-hex"):
        P._require_current_clean_reporting_commit("C" * 40)
    for state in (
        P.GitState(commit=COMMIT, dirty=True, branch="synthetic"),
        P.GitState(commit="d" * 40, dirty=False, branch="synthetic"),
        object(),
    ):
        monkeypatch.setattr(P, "git_state", lambda state=state: state)
        with pytest.raises(ValueError, match="clean trustworthy|non-GitState"):
            P._require_current_clean_reporting_commit(COMMIT)
    assert not P.OUTPUT_ROOT.exists()
    assert not P.OUTPUT_COPY_ROOT.exists()


@pytest.mark.parametrize("which", ["original", "copy"])
def test_preexisting_output_root_is_refused_before_source_reopen(
    fixed_layout: tuple[Path, list[Path]], which: str
) -> None:
    _, calls = fixed_layout
    target = P.OUTPUT_ROOT if which == "original" else P.OUTPUT_COPY_ROOT
    target.mkdir()
    marker = target / "preserve.txt"
    marker.write_text("user-owned", encoding="utf-8")
    with pytest.raises(ValueError, match="preexisting"):
        P.publish(expected_git_commit=COMMIT)
    assert marker.read_text(encoding="utf-8") == "user-owned"
    assert calls == []


@pytest.mark.parametrize("relationship", ["same", "nested", "source"])
def test_overlapping_output_layout_is_refused_without_writes(
    fixed_layout: tuple[Path, list[Path]],
    monkeypatch: pytest.MonkeyPatch,
    relationship: str,
) -> None:
    workspace, calls = fixed_layout
    if relationship == "same":
        monkeypatch.setattr(P, "OUTPUT_COPY_ROOT", P.OUTPUT_ROOT)
    elif relationship == "nested":
        monkeypatch.setattr(
            P,
            "OUTPUT_COPY_ROOT",
            P.OUTPUT_ROOT / "week8-exclusion-2026-09-01-attempt-001-project-evidence",
        )
    else:
        monkeypatch.setattr(
            P,
            "OUTPUT_ROOT",
            P.LABEL_ORIGINAL_ROOT / "week8-exclusion-2026-09-01-attempt-001",
        )
    with pytest.raises(ValueError, match="layout|disjoint"):
        P.publish(expected_git_commit=COMMIT)
    assert calls == []
    assert not (workspace / "unexpected-output").exists()


def test_link_or_reparse_output_is_refused(
    fixed_layout: tuple[Path, list[Path]], tmp_path: Path
) -> None:
    _, calls = fixed_layout
    target = tmp_path / "link-target"
    target.mkdir()
    try:
        os.symlink(target, P.OUTPUT_ROOT, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable on this host")
    with pytest.raises(ValueError, match="link/reparse|preexisting"):
        P.publish(expected_git_commit=COMMIT)
    assert calls == []


@pytest.mark.parametrize("authority", ["original", "copy"])
def test_wrong_label_sha_is_refused_before_publication(
    fixed_layout: tuple[Path, list[Path]], authority: str
) -> None:
    root = P.LABEL_ORIGINAL_ROOT if authority == "original" else P.LABEL_COPY_ROOT
    (root / P.ORDINARY_SWEEP_LABEL_EVIDENCE_FILE).write_bytes(b"changed")
    with pytest.raises(ValueError, match="label SHA256|bytes differ"):
        P.publish(expected_git_commit=COMMIT)
    assert not P.OUTPUT_ROOT.exists()
    assert not P.OUTPUT_COPY_ROOT.exists()


@pytest.mark.parametrize("authority", ["original", "copy"])
def test_wrong_manifest_sha_or_commit_is_refused(
    fixed_layout: tuple[Path, list[Path]], authority: str
) -> None:
    root = P.LABEL_ORIGINAL_ROOT if authority == "original" else P.LABEL_COPY_ROOT
    manifest = read_json(root / P.FINALIZATION_MANIFEST_FILE)
    manifest["library_commit"] = "d" * 40
    (root / P.FINALIZATION_MANIFEST_FILE).write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="manifest SHA256|authority fields|bytes differ"):
        P.publish(expected_git_commit=COMMIT)
    assert not P.OUTPUT_ROOT.exists()


def test_independent_source_semantic_divergence_is_refused_before_output(
    fixed_layout: tuple[Path, list[Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = P.Exclusion.summarize_sweep_exclusion

    def divergent(labels: object, *, expected_unit_ids: object) -> dict[str, Any]:
        result = original(labels, expected_unit_ids=expected_unit_ids)
        source = labels[0]
        if Path(source.path).parent == P.LABEL_COPY_ROOT:
            result["opaque_synthetic_payload"]["same_for_both_authorities"] = False
        return result

    monkeypatch.setattr(P.Exclusion, "summarize_sweep_exclusion", divergent)
    with pytest.raises(ValueError, match="derive different reports"):
        P.publish(expected_git_commit=COMMIT)
    assert not P.OUTPUT_ROOT.exists()
    assert not P.OUTPUT_COPY_ROOT.exists()


def test_source_change_during_publication_fails_closed(
    fixed_layout: tuple[Path, list[Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    original_write = P.Exclusion.write_sweep_exclusion_report

    def mutate_after_write(*args: object, **kwargs: object) -> dict[str, Any]:
        result = original_write(*args, **kwargs)
        (P.LABEL_COPY_ROOT / P.ORDINARY_SWEEP_LABEL_EVIDENCE_FILE).write_bytes(
            b"changed during publication"
        )
        return result

    monkeypatch.setattr(P.Exclusion, "write_sweep_exclusion_report", mutate_after_write)
    with pytest.raises(ValueError, match="label SHA256|bytes differ"):
        P.publish(expected_git_commit=COMMIT)
    assert not (P.OUTPUT_ROOT / P.BINDING_FILE).exists()


def test_cli_has_one_fixed_command_and_prints_no_observed_values(
    fixed_layout: tuple[Path, list[Path]], capsys: pytest.CaptureFixture[str]
) -> None:
    parser = P._parser()
    choices = next(
        action.choices
        for action in parser._actions
        if hasattr(action, "choices") and action.choices
    )
    assert set(choices) == {"publish"}
    with pytest.raises(SystemExit):
        parser.parse_args(["publish", "--output-root", "elsewhere"])
    with pytest.raises(SystemExit):
        P.main(["publish"])
    assert P.main(["publish", "--expected-git-commit", COMMIT]) == 0
    output = capsys.readouterr().out
    document = json.loads(output)
    assert set(document) == {
        "command",
        "status",
        "report_sha256",
        "receipt_sha256",
    }
    lowered = output.lower()
    for forbidden in (
        "observed_0",
        "observed_1",
        "ambiguous",
        "undiagnosed",
        "exclusion_rate",
        "shortfall",
    ):
        assert forbidden not in lowered


def test_cli_hashes_exception_text_and_emits_no_traceback(
    fixed_layout: tuple[Path, list[Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "SECRET_OBSERVED_LABEL_AND_SOURCE_MESSAGE"

    def fail(*, expected_git_commit: str) -> dict[str, Any]:
        assert expected_git_commit == COMMIT
        raise ValueError(secret)

    monkeypatch.setattr(P, "publish", fail)
    assert P.main(["publish", "--expected-git-commit", COMMIT]) == 1
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document == P._operational_failure("publish", ValueError(secret))
    assert set(document) == {
        "command",
        "status",
        "failure_type",
        "failure_sha256",
    }
    combined = captured.out + captured.err
    assert secret not in combined
    assert "traceback" not in combined.lower()


@pytest.mark.parametrize("exception", [KeyboardInterrupt("stop"), SystemExit(9)])
def test_cli_does_not_catch_process_control_exceptions(
    fixed_layout: tuple[Path, list[Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exception: BaseException,
) -> None:
    def stop(*, expected_git_commit: str) -> dict[str, Any]:
        assert expected_git_commit == COMMIT
        raise exception

    monkeypatch.setattr(P, "publish", stop)
    with pytest.raises(type(exception)):
        P.main(["publish", "--expected-git-commit", COMMIT])
    captured = capsys.readouterr()
    assert captured.out == ""


def test_module_has_no_discovery_compute_or_forbidden_import_boundary() -> None:
    path = Path(P.__file__)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                calls.append(function.id)
            elif isinstance(function, ast.Attribute):
                calls.append(function.attr)
    assert not any("reserve" in name for name in imports)
    assert not any(name in {"glob", "rglob", "iterdir", "walk"} for name in calls)
    assert not any(
        name
        in {
            "fit",
            "fit_model",
            "launch",
            "run_experiment",
            "train",
            "train_model",
        }
        for name in calls
    )
    assert "week8_launch" not in source
    assert "fit_evidence" not in source
    assert "runrecord" in imports
