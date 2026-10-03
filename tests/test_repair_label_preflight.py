"""Synthetic tests for the no-compute Week-6 smoke preflight."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bu.config import UnitSpec
from bu.experiments import repair_label_preflight as PF
from bu.experiments import repair_label_run as R
from bu.runrecord import GitState, TRACKED_PACKAGES


COMMIT = "a" * 40


@pytest.fixture
def roots(tmp_path):
    values = {
        name: tmp_path / name
        for name in ("preflight", "output", "staging", "sync")
    }
    for path in values.values():
        path.mkdir()
    return values


@pytest.fixture
def ready_environment(monkeypatch):
    versions = {name: f"test-{index}" for index, name in enumerate(TRACKED_PACKAGES)}
    monkeypatch.setattr(
        PF.P,
        "_verify_environment",
        lambda: (GitState(COMMIT, False, "main"), versions, dict(versions)),
    )
    monkeypatch.setattr(
        PF.P,
        "_verify_device",
        lambda route: {
            "frozen_route": "cpu",
            "requested_route": route,
            "available": route == "cpu",
        },
    )
    return versions


def _run(roots):
    return PF.run_repair_label_preflight(
        preflight_dir=roots["preflight"],
        output_root=roots["output"],
        staging_root=roots["staging"],
        sync_root=roots["sync"],
        sync_destination_identity="test-mounted-destination",
        execution_route="cpu",
        minimum_free_bytes=0,
    )


def test_preflight_publishes_exact_plan_and_readback_copies_before_compute(
    roots, ready_environment
):
    report = _run(roots)

    assert report["status"] == "ready"
    assert report["launch_performed"] is False
    assert report["plan"]["unit_id"] == R.WEEK6_SMOKE_UNIT_ID
    assert report["plan"]["seeds"] == list(range(1000, 1020))
    assert report["plan"]["arms"] == [
        "baseline",
        "data_repair",
        "feature_repair",
    ]
    assert report["plan"]["fit_count"] == 60
    plan = json.loads(
        (roots["output"] / R.REPAIR_LABEL_PLAN_FILE).read_text(encoding="utf-8")
    )
    assert [(row["seed"], row["arm"]) for row in plan["fit_order"]] == [
        (seed, arm)
        for seed in range(1000, 1020)
        for arm in ("baseline", "data_repair", "feature_repair")
    ]
    sync_dir = roots["sync"] / PF.REPAIR_LABEL_SYNC_DIRECTORY
    assert (sync_dir / R.REPAIR_LABEL_PLAN_FILE).read_bytes() == (
        roots["output"] / R.REPAIR_LABEL_PLAN_FILE
    ).read_bytes()
    assert (sync_dir / PF.REPAIR_LABEL_PREFLIGHT_FILE).read_bytes() == (
        roots["preflight"] / PF.REPAIR_LABEL_PREFLIGHT_FILE
    ).read_bytes()
    assert not (roots["output"] / R.FIT_DIRECTORY).exists()


def test_preflight_is_idempotent_only_for_identical_plan(roots, ready_environment):
    first = _run(roots)
    second = _run(roots)
    assert second == first

    plan_path = roots["output"] / R.REPAIR_LABEL_PLAN_FILE
    document = json.loads(plan_path.read_text(encoding="utf-8"))
    document["seeds"][0] = 999
    plan_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="differs from the exact registered plan"):
        _run(roots)


def test_preflight_refuses_wrong_registered_unit_before_fit_directory(
    roots, ready_environment, monkeypatch
):
    monkeypatch.setattr(
        R,
        "registered_week6_smoke_unit",
        lambda: UnitSpec(family="estimation"),
    )
    with pytest.raises(ValueError, match="only predeclared unit"):
        _run(roots)
    assert not (roots["output"] / R.FIT_DIRECTORY).exists()


def test_preflight_refuses_wrong_seed_or_arm_order(
    roots, ready_environment, monkeypatch
):
    original = R._plan_document

    def reordered(*args, **kwargs):
        document = original(*args, **kwargs)
        document["fit_order"][0], document["fit_order"][1] = (
            document["fit_order"][1],
            document["fit_order"][0],
        )
        return document

    monkeypatch.setattr(R, "_plan_document", reordered)
    with pytest.raises(ValueError, match="exact 20 x"):
        _run(roots)


def test_preflight_refuses_overlapping_root_aliases(roots, ready_environment):
    roots["staging"] = roots["output"]
    with pytest.raises(ValueError, match="distinct and non-overlapping"):
        _run(roots)


def test_preflight_refuses_torn_or_divergent_plan_sync(
    roots, ready_environment
):
    sync_dir = roots["sync"] / PF.REPAIR_LABEL_SYNC_DIRECTORY
    sync_dir.mkdir()
    (sync_dir / R.REPAIR_LABEL_PLAN_FILE).write_text(
        '{"partial":true}\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="different content"):
        _run(roots)


def test_public_preflight_cli_has_no_unit_seed_arm_or_executor_arguments():
    destinations = {action.dest for action in PF.build_parser()._actions}
    assert {
        "unit",
        "unit_id",
        "seed",
        "seeds",
        "arm",
        "executor",
        "sync_adapter",
    }.isdisjoint(destinations)
