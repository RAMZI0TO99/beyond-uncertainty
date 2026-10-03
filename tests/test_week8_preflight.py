"""Synthetic operational tests for the exact Week-8 readiness gate."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import atomic_write_json, read_json
from bu.experiments import preflight as P
from bu.experiments import week8_plan as LP
from bu.experiments import week8_preflight as PF
from bu.runrecord import GitState


@pytest.fixture(scope="module")
def registered():
    plan = LP.build_week8_launch_plan()
    return plan, {
        "exp2b": LP.experiment_2b_baseline_jobs(),
        "sweep-002": LP.sweep_002_baseline_jobs(),
    }


@pytest.fixture(params=("exp2b", "sweep-002"))
def case(tmp_path, monkeypatch, request, registered):
    plan_document, jobs = registered
    plan = atomic_write_json(tmp_path / "inputs" / LP.WEEK8_PLAN_FILE, plan_document)
    roots = {
        name: tmp_path / name for name in ("preflight", "output", "staging", "sync")
    }
    for root in roots.values():
        root.mkdir()
    (tmp_path / PF.COMMON_CONTROL_DIRECTORY).mkdir()
    pins = P._pinned_package_versions()
    monkeypatch.setattr(PF, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(P, "git_state", lambda: GitState("b" * 40, False, "main"))
    monkeypatch.setattr(P, "package_versions", lambda: dict(pins))
    monkeypatch.setattr(P, "_device_available", lambda device: device == "cpu")
    monkeypatch.setattr(
        P.shutil,
        "disk_usage",
        lambda root: SimpleNamespace(free=PF.WEEK8_MINIMUM_FREE_BYTES + 1_000_000),
    )

    def input_file(path):
        checked = PF._project_path(path, what="plan", directory=False)
        if read_json(checked) != plan_document:
            raise ValueError("synthetic plan changed")
        return checked, plan_document

    def batch_jobs(document, key):
        if document != plan_document or key not in jobs:
            raise ValueError("Week-8 authorizes only exp2b and sweep-002")
        return jobs[key]

    monkeypatch.setattr(PF, "_input_file", input_file)
    monkeypatch.setattr(PF, "_batch_jobs", batch_jobs)
    arguments = {
        "plan_path": plan,
        "batch_key": request.param,
        "preflight_dir": roots["preflight"],
        "output_root": roots["output"],
        "staging_root": roots["staging"],
        "sync_root": roots["sync"],
        "sync_destination_identity": "independent-project-local-week8-copy",
    }
    return roots, arguments


def _run(case):
    roots, arguments = case
    PF.run_week8_preflight(**arguments)
    return roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE


def _rewrite_both(case, change):
    roots, _ = case
    path = roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE
    document = read_json(path)
    change(document)
    raw = PF.L._pretty_json_bytes(document)
    path.write_bytes(raw)
    (roots["sync"] / path.name).write_bytes(raw)


def test_preflight_is_cpu_clean_commit_exact_batch_and_independently_copied(case):
    path = _run(case)
    roots, arguments = case
    validated = PF.validate_week8_preflight(
        path, output_root=roots["output"], sync_root=roots["sync"]
    )
    expected = 125 if arguments["batch_key"] == "exp2b" else 3
    assert len(validated.jobs) == expected
    assert validated.git_commit == "b" * 40
    assert validated.report["device"]["frozen_route"] == "cpu"
    assert (
        validated.report["storage"]["minimum_free_bytes"]
        == PF.WEEK8_MINIMUM_FREE_BYTES
    )
    assert validated.report["launch_performed"] is False
    assert validated.report["scientific_analysis_performed"] is False
    for name in (
        PF.WEEK8_PREFLIGHT_FILE,
        "week8_launch_plan.json",
        P.SYNC_CANARY_FILE,
    ):
        local, copy = roots["preflight"] / name, roots["sync"] / name
        assert local.read_bytes() == copy.read_bytes()
        assert not os.path.samefile(local, copy)
    assert tuple(roots["output"].iterdir()) == ()
    assert tuple(roots["staging"].iterdir()) == ()
    claim = (
        roots["preflight"].parent
        / PF.COMMON_CONTROL_DIRECTORY
        / PF.ROOT_CLAIM_DIRECTORY
        / f"{arguments['batch_key']}.json"
    )
    assert read_json(claim)["roots"] == {
        name: str(roots[name].resolve())
        for name in sorted(roots)
    }


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(week8_preflight_schema_version=True),
        lambda d: d.update(status="complete"),
        lambda d: d.update(launch_performed=True),
        lambda d: d.update(scientific_analysis_performed=True),
        lambda d: d.update(extra=True),
        lambda d: d.update(batch_key="sweep-003"),
        lambda d: d.update(binding_sha256="0" * 64),
        lambda d: d["batch"]["jobs"].pop(),
        lambda d: d["plan"].update(sha256="0" * 64),
        lambda d: d["environment"]["git"].update(commit="c" * 40),
        lambda d: d["device"].update(requested_route="cuda"),
        lambda d: d["storage"].update(minimum_free_bytes=True),
        lambda d: d["storage"].update(
            minimum_free_bytes=PF.WEEK8_MINIMUM_FREE_BYTES - 1
        ),
        lambda d: d["storage"].update(
            minimum_free_bytes=float(PF.WEEK8_MINIMUM_FREE_BYTES)
        ),
    ],
)
def test_resigned_preflight_mutation_refuses(case, change):
    path = _run(case)
    _rewrite_both(case, change)
    roots, _ = case
    with pytest.raises(ValueError):
        PF.validate_week8_preflight(
            path, output_root=roots["output"], sync_root=roots["sync"]
        )


def test_original_plan_and_independent_copies_are_reopened(case):
    path = _run(case)
    roots, arguments = case
    arguments["plan_path"].write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        PF.validate_week8_preflight(
            path, output_root=roots["output"], sync_root=roots["sync"]
        )


@pytest.mark.parametrize(
    "name", [PF.WEEK8_PREFLIGHT_FILE, "week8_launch_plan.json", P.SYNC_CANARY_FILE]
)
def test_missing_independent_readiness_evidence_refuses(case, name):
    path = _run(case)
    roots, _ = case
    (roots["sync"] / name).unlink()
    with pytest.raises(ValueError):
        PF.validate_week8_preflight(
            path, output_root=roots["output"], sync_root=roots["sync"]
        )


def test_hardlinked_canary_refuses(case):
    path = _run(case)
    roots, _ = case
    copy = roots["sync"] / P.SYNC_CANARY_FILE
    copy.unlink()
    os.link(roots["preflight"] / P.SYNC_CANARY_FILE, copy)
    with pytest.raises(ValueError, match="hard-linked|aliases"):
        PF.validate_week8_preflight(
            path, output_root=roots["output"], sync_root=roots["sync"]
        )


def test_dirty_commit_and_non_cpu_route_refuse_before_report(case, monkeypatch):
    roots, arguments = case
    monkeypatch.setattr(P, "git_state", lambda: GitState("b" * 40, True, "main"))
    with pytest.raises(ValueError, match="trustworthy"):
        PF.run_week8_preflight(**arguments)
    assert not (roots["preflight"] / PF.WEEK8_PREFLIGHT_FILE).exists()


def test_storage_floor_is_not_a_public_override(case):
    roots, arguments = case
    with pytest.raises(ValueError, match="frozen at exactly"):
        PF.run_week8_preflight(**arguments, minimum_free_bytes=0)
    with pytest.raises(ValueError, match="frozen at exactly"):
        PF.run_week8_preflight(
            **arguments,
            minimum_free_bytes=float(PF.WEEK8_MINIMUM_FREE_BYTES),
        )
    assert tuple(roots["preflight"].iterdir()) == ()


def test_overlap_outside_workspace_and_unauthorized_batch_refuse(case, monkeypatch):
    roots, arguments = case
    with pytest.raises(ValueError, match="non-overlapping"):
        PF.run_week8_preflight(**{**arguments, "sync_root": roots["output"]})
    with pytest.raises(ValueError, match="only exp2b and sweep-002"):
        PF.run_week8_preflight(**{**arguments, "batch_key": "sweep-003"})
    monkeypatch.setattr(PF, "WORKSPACE_ROOT", roots["output"])
    with pytest.raises(ValueError, match="inside the project"):
        PF.run_week8_preflight(**arguments)


def test_historical_source_root_is_refused_before_any_evidence_write(
    case, monkeypatch
):
    roots, arguments = case
    historical = roots["preflight"].parent / "week7-immutable-source"
    historical.mkdir()
    monkeypatch.setattr(
        P,
        "_run_sync_canary",
        lambda **kwargs: pytest.fail("canary ran before historical-root refusal"),
    )
    with pytest.raises(ValueError, match="immutable historical/source"):
        PF.run_week8_preflight(**{**arguments, "output_root": historical})
    assert tuple(roots["preflight"].iterdir()) == ()
    assert tuple(roots["sync"].iterdir()) == ()


def test_monitor_history_root_is_protected_before_any_evidence_write(
    case, monkeypatch
):
    roots, arguments = case
    monitor = roots["preflight"].parent / "week8-monitor-exp2b-history"
    monitor.mkdir()
    monkeypatch.setattr(
        P,
        "_run_sync_canary",
        lambda **kwargs: pytest.fail("canary ran before monitor-history refusal"),
    )
    with pytest.raises(ValueError, match="immutable historical/source"):
        PF.run_week8_preflight(**{**arguments, "output_root": monitor})
    assert tuple(roots["preflight"].iterdir()) == ()
    assert tuple(roots["sync"].iterdir()) == ()


def test_first_root_claim_requires_every_destination_to_be_empty(case, monkeypatch):
    roots, arguments = case
    marker = roots["output"] / "pre-existing.txt"
    marker.write_text("unrelated history\n", encoding="utf-8")
    monkeypatch.setattr(
        P,
        "_run_sync_canary",
        lambda **kwargs: pytest.fail("canary ran before pristine-root refusal"),
    )
    with pytest.raises(ValueError, match="must be empty"):
        PF.run_week8_preflight(**arguments)
    assert marker.read_text(encoding="utf-8") == "unrelated history\n"
    claim_dir = (
        roots["preflight"].parent
        / PF.COMMON_CONTROL_DIRECTORY
        / PF.ROOT_CLAIM_DIRECTORY
    )
    assert not claim_dir.exists()


def test_cross_batch_root_claim_refuses_reuse_before_any_new_evidence(
    case, monkeypatch
):
    roots, arguments = case
    PF.run_week8_preflight(**arguments)
    other_key = "sweep-002" if arguments["batch_key"] == "exp2b" else "exp2b"
    fresh = {
        name: roots["preflight"].parent / f"other-{name}"
        for name in ("preflight", "staging", "sync")
    }
    for root in fresh.values():
        root.mkdir()
    monkeypatch.setattr(
        P,
        "_run_sync_canary",
        lambda **kwargs: pytest.fail("canary ran before cross-batch refusal"),
    )
    with pytest.raises(ValueError, match="claimed"):
        PF.run_week8_preflight(
            **{
                **arguments,
                "batch_key": other_key,
                "preflight_dir": fresh["preflight"],
                "output_root": roots["output"],
                "staging_root": fresh["staging"],
                "sync_root": fresh["sync"],
            }
        )
    assert tuple(fresh["preflight"].iterdir()) == ()
    assert tuple(fresh["sync"].iterdir()) == ()


def test_windows_reparse_root_is_refused_before_claim_or_canary(
    case, monkeypatch
):
    roots, arguments = case
    target = roots["staging"].absolute()
    original = Path.lstat

    def marked(path: Path):
        info = original(path)
        if path.absolute() == target:
            return SimpleNamespace(
                st_mode=info.st_mode,
                st_file_attributes=getattr(
                    stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
                ),
                st_nlink=info.st_nlink,
            )
        return info

    monkeypatch.setattr(Path, "lstat", marked)
    monkeypatch.setattr(
        P,
        "_run_sync_canary",
        lambda **kwargs: pytest.fail("canary ran after reparse detection"),
    )
    with pytest.raises(ValueError, match="link/reparse"):
        PF.run_week8_preflight(**arguments)
    claim_dir = (
        roots["preflight"].parent
        / PF.COMMON_CONTROL_DIRECTORY
        / PF.ROOT_CLAIM_DIRECTORY
    )
    assert not claim_dir.exists()
