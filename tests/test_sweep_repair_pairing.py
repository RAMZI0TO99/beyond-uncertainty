"""D-155: fail closed at execution, without rewriting the unpaired sweep design.

Only source-defined units, identities and stream keys are inspected. Every
execution test stops at a stub before any data collection, output or training.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import Mock

import pytest
import torch

from bu import constants as K
from bu.config import Config
from bu.experiments import confirmatory as C
from bu.experiments.enumerate_units import (
    canonical_units,
    design_units,
    execution_plan,
    stage_of,
)
from bu.runrecord import GitState
from bu.streams import DATA_PURPOSES, PURPOSES, STREAM_VERSION, stream_key


DESIGN = design_units()
CANONICAL = canonical_units()
CANONICAL_IDS = {Config(unit=unit).unit_id for unit in CANONICAL}
SWEEP = tuple(unit for unit in DESIGN if Config(unit=unit).unit_id not in CANONICAL_IDS)
PLAN = execution_plan(DESIGN)
REPAIRS_BY_UNIT = defaultdict(list)
for _fit in PLAN:
    if _fit.arm != "baseline":
        REPAIRS_BY_UNIT[Config(unit=_fit.unit).unit_id].append(_fit)

CONF = K.CONFIRMATORY_SEED_BASE
SCALE = C.NormalisationScale(vector=torch.ones(1), n_reference=1)
# Never created: even output-path construction is stubbed. No temp location
# outside the project or experiment-payload directory is needed by these tests.
OUT_DIR = Path(__file__).resolve().parents[1] / ".sweep-pairing-test-output"


class _ReachedPools(RuntimeError):
    """A valid preflight reached the pool boundary; no pool is actually drawn."""


@pytest.fixture(autouse=True)
def boundary_stubs(monkeypatch):
    stubs = {}
    for name in (
        "git_state", "_pin_threading", "torch_threading", "collect_pools",
        "collect_pools_with_anchors",
        "assert_pools_match", "_digest_pool", "Path", "train_ensemble",
        "_digest_file", "atomic_write_json",
    ):
        stubs[name] = Mock(side_effect=AssertionError(f"unexpected boundary: {name}"))
        monkeypatch.setattr(C, name, stubs[name])
    stubs["logger"] = Mock(side_effect=AssertionError("unexpected output logger"))
    monkeypatch.setattr(C.RunLogger, "start", stubs["logger"])
    yield stubs
    for name in (
        "assert_pools_match", "_digest_pool", "Path", "train_ensemble",
        "_digest_file", "atomic_write_json", "logger",
    ):
        stubs[name].assert_not_called()


def _allow_until_pools(stubs):
    """Stub unrelated preconditions so a decorative/missing guard cannot hide."""
    for name, result in (
        ("git_state", GitState(commit="c" * 40, dirty=False, branch="main")),
        ("_pin_threading", None),
        ("torch_threading", {
            "num_threads": C.CONFIRMATORY_THREADS,
            "num_interop_threads": C.CONFIRMATORY_INTEROP_THREADS,
        }),
    ):
        stubs[name].side_effect = None
        stubs[name].return_value = result
    stubs["collect_pools"].side_effect = _ReachedPools
    stubs["collect_pools_with_anchors"].side_effect = _ReachedPools


def _assert_wrong_pairing(error, unit, stage, purposes):
    message = str(error.value)
    assert "Wrong pairing" in message
    assert Config(unit=unit).unit_id in message
    assert repr(stage) in message
    assert "authoritative baseline stage" in message
    assert "mismatched data stream keys" in message
    for purpose in purposes:
        assert repr(purpose) in message
    assert "explicit versioned procedure decision is needed" in message
    assert "D-155" in message


def test_design_counts_and_all_obligations_remain_inventory():
    """Not executing a registered obligation must never remove it from the plan."""
    assert len(DESIGN) == 300
    assert len(CANONICAL) == 75
    assert len(SWEEP) == 225
    expected = set()
    counts = Counter()
    for fit in PLAN:
        unit_id = Config(unit=fit.unit).unit_id
        category = (
            "baseline" if fit.arm == "baseline"
            else "canonical_repair" if unit_id in CANONICAL_IDS else "sweep_repair"
        )
        for role in fit.roles:
            C.assert_registered_obligation(
                fit.unit, arm=fit.arm, stage=role, seed=CONF + fit.seed,
            )
            expected.add((unit_id, fit.arm, role, fit.seed))
            counts[category] += 1
    assert counts == {"baseline": 1350, "canonical_repair": 960, "sweep_repair": 1350}
    assert len(PLAN) == 3585  # 1,275 baseline fits; 75 carry two roles.
    assert len(expected) == 3660
    assert C._registered_obligations() == frozenset(expected)
    assert {fit.roles for fit in PLAN if fit.arm == "capacity_extension_repair"} == {
        ("exp3_repairs",), ("repair_validation",),
    }


@pytest.mark.parametrize("unit", SWEEP, ids=lambda unit: Config(unit=unit).unit_id)
def test_all_225_sweep_units_refused_at_execution_before_io_or_training(unit, boundary_stubs):
    """All arms and all three seeds: 1,350 refusals, not just one example per unit."""
    assert stage_of(unit) == "config_sweep"
    assert {
        purpose for purpose in DATA_PURPOSES
        if stream_key(unit, "config_sweep", purpose) != stream_key(unit, "exp3_repairs", purpose)
    } == DATA_PURPOSES
    registered_before = C._registered_obligations()
    fits = REPAIRS_BY_UNIT[Config(unit=unit).unit_id]
    assert len(fits) == 6
    for fit in fits:
        assert fit.roles == ("exp3_repairs",)
        # This is registered inventory, even though its execution is unsafe.
        C.assert_registered_obligation(unit, arm=fit.arm, stage=fit.roles[0], seed=CONF + fit.seed)
        with pytest.raises(ValueError) as error:
            C.run_confirmatory(
                unit, stage=fit.roles[0], seed=CONF + fit.seed, arm=fit.arm,
                scale=SCALE, out_dir=OUT_DIR,
            )
        _assert_wrong_pairing(error, unit, "exp3_repairs", DATA_PURPOSES)
        assert "'config_sweep'" in str(error.value)
    for stub in boundary_stubs.values():
        stub.assert_not_called()
    assert C._registered_obligations() == registered_before


@pytest.mark.parametrize("unit", CANONICAL, ids=lambda unit: Config(unit=unit).unit_id)
def test_all_75_canonical_units_keep_valid_registered_repairs(unit, boundary_stubs):
    """All 960 canonical repair fits, including both capacity-extension stages."""
    _allow_until_pools(boundary_stubs)
    fits = REPAIRS_BY_UNIT[Config(unit=unit).unit_id]
    assert len(fits) in (6, 40)
    for fit in fits:
        stage = fit.roles[0]
        assert all(
            stream_key(unit, stage_of(unit), purpose) == stream_key(unit, stage, purpose)
            for purpose in DATA_PURPOSES
        )
        C._assert_repair_pairing(unit, arm=fit.arm, stage=stage)
        with pytest.raises(_ReachedPools):
            C.run_confirmatory(
                unit, stage=stage, seed=CONF + fit.seed, arm=fit.arm,
                scale=SCALE, out_dir=OUT_DIR,
            )
        boundary_stubs["collect_pools"].assert_called_with(
            unit, stage=stage, seed=CONF + fit.seed, arm=fit.arm,
        )
    assert boundary_stubs["collect_pools"].call_count == len(fits)


def test_every_baseline_role_remains_unblocked_by_repair_guard(boundary_stubs, monkeypatch):
    """All 1,350 roles reach collection; sweep additionally captures anchors."""
    _allow_until_pools(boundary_stubs)
    # Baselines must not even derive a repair-pairing stage or stream key.
    forbidden = Mock(side_effect=AssertionError("baseline entered repair pairing"))
    monkeypatch.setattr(C, "stage_of", forbidden)
    monkeypatch.setattr(C, "stream_key", forbidden)
    count = 0
    for fit in PLAN:
        if fit.arm != "baseline":
            continue
        for role in fit.roles:
            C._assert_repair_pairing(fit.unit, arm="baseline", stage=role)
            with pytest.raises(_ReachedPools):
                C.run_confirmatory(
                    fit.unit, stage=role, seed=CONF + fit.seed,
                    out_dir=OUT_DIR, _fit_roles=fit.roles,
                )
            count += 1
    assert count == 1350
    assert boundary_stubs["collect_pools"].call_count == 675
    assert boundary_stubs["collect_pools_with_anchors"].call_count == 675
    forbidden.assert_not_called()


@pytest.mark.parametrize("purpose", sorted(DATA_PURPOSES))
def test_each_data_purpose_independently_refuses_in_helper_and_execution(
    purpose, boundary_stubs, monkeypatch,
):
    """Even one changed key field must bite; checking only env/group is insufficient."""
    unit = CANONICAL[0]
    stage = REPAIRS_BY_UNIT[Config(unit=unit).unit_id][0].roles[0]
    baseline_stage = stage_of(unit)
    calls = []

    def changed_key(got_unit, got_stage, got_purpose):
        assert got_unit is unit  # Not Arm.resolve(unit), including for data repair.
        calls.append((got_stage, got_purpose))
        key = stream_key(got_unit, got_stage, got_purpose)
        if got_stage == stage and got_purpose == purpose:
            key = dict(key, stream_version=key["stream_version"] + 1)
        return key

    monkeypatch.setattr(C, "stream_key", changed_key)
    expected_calls = [(s, p) for p in sorted(DATA_PURPOSES) for s in (baseline_stage, stage)]
    with pytest.raises(ValueError) as error:
        C._assert_repair_pairing(unit, arm="data_repair", stage=stage)
    _assert_wrong_pairing(error, unit, stage, [purpose])
    assert calls == expected_calls
    calls.clear()
    with pytest.raises(ValueError) as error:
        C.run_confirmatory(
            unit, arm="data_repair", stage=stage, seed=CONF, scale=SCALE, out_dir=OUT_DIR,
        )
    _assert_wrong_pairing(error, unit, stage, [purpose])
    assert calls == expected_calls
    for stub in boundary_stubs.values():
        stub.assert_not_called()


def test_guard_uses_stage_of_not_a_family_inference(monkeypatch):
    unit = CANONICAL[0]
    authoritative_stage = Mock(return_value="config_sweep")
    monkeypatch.setattr(C, "stage_of", authoritative_stage)
    with pytest.raises(ValueError, match="authoritative baseline stage 'config_sweep'"):
        C._assert_repair_pairing(unit, arm="data_repair", stage="repair_validation")
    authoritative_stage.assert_called_once_with(unit)


def test_registration_refuses_before_pairing_is_considered(monkeypatch):
    unit = SWEEP[0]
    forbidden = Mock(side_effect=AssertionError("pairing ran before registration"))
    monkeypatch.setattr(C, "_assert_repair_pairing", forbidden)
    with pytest.raises(ValueError, match="not a registered obligation"):
        C.run_confirmatory(
            unit, arm="data_repair", stage="exp3_repairs", seed=CONF + K.SEEDS_SWEEP,
            scale=SCALE, out_dir=OUT_DIR,
        )
    forbidden.assert_not_called()


def test_pairing_refusal_does_not_hide_behind_missing_scale():
    with pytest.raises(ValueError, match="Wrong pairing"):
        C.run_confirmatory(
            SWEEP[0], arm="data_repair", stage="exp3_repairs", seed=CONF, out_dir=OUT_DIR,
        )


def test_disabling_guard_reaches_pools_for_the_same_wrong_pair(boundary_stubs, monkeypatch):
    """Mutation control: an unused helper or a no-op check cannot pass this suite."""
    _allow_until_pools(boundary_stubs)
    kwargs = dict(
        arm="data_repair", stage="exp3_repairs", seed=CONF, scale=SCALE, out_dir=OUT_DIR,
    )
    with pytest.raises(ValueError, match="Wrong pairing"):
        C.run_confirmatory(SWEEP[0], **kwargs)
    boundary_stubs["git_state"].assert_not_called()
    boundary_stubs["collect_pools"].assert_not_called()
    monkeypatch.setattr(C, "_assert_repair_pairing", lambda *args, **kw: None)
    with pytest.raises(_ReachedPools):
        C.run_confirmatory(SWEEP[0], **kwargs)
    boundary_stubs["collect_pools"].assert_called_once_with(
        SWEEP[0], stage="exp3_repairs", seed=CONF, arm="data_repair",
    )


def test_all_8100_legacy_stream_keys_remain_unchanged():
    """Pre-guard fingerprint: 300 units x 3 stages x all 9 existing purposes.

    Includes the mismatched sweep repair keys on purpose: a safety refusal is
    not authorization to silently reinterpret historical streams or stages.
    """
    assert STREAM_VERSION == 3
    rows = [
        [Config(unit=unit).unit_id, stage, purpose, stream_key(unit, stage, purpose)]
        for unit in sorted(DESIGN, key=lambda unit: Config(unit=unit).unit_id)
        for stage in (stage_of(unit), "repair_validation", "exp3_repairs")
        for purpose in PURPOSES
    ]
    assert len(rows) == 8100
    digest = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == "fd97e6c4ca59db074c34f823dc90fd857a5122a97533e7b9a23dcd25878d6d9f"
