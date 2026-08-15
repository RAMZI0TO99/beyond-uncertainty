"""Week 1 acceptance tests.

Each test corresponds to a "Done when" criterion from Schedule Week 1, plus the
identity invariants the labelling protocol depends on.
"""

from __future__ import annotations

import dataclasses

import pytest

from bu import constants as K
from bu.config import Arm, Config, TrainConfig, UnitSpec
from bu.metrics import RunLogger, load_runs
from bu.runrecord import read_run_record

# --- identity semantics (Plan §10.7, §7.2) --------------------------------


def test_unit_id_is_shared_across_repair_arms():
    """A failure condition and its repairs are one statistical unit.

    This is what makes a ground-truth label assignable: the repairs must be
    attributable to the condition they repair.
    """
    unit = UnitSpec(family="missing_feature", withheld_features=("shape",), n_transitions=500)
    base = Config(unit=unit, arm=Arm("baseline"))
    data = Config(unit=unit, arm=Arm("data_repair"))
    feat = Config(unit=unit, arm=Arm("feature_repair"))

    assert base.unit_id == data.unit_id == feat.unit_id
    # ...but the arms are distinguishable runs.
    assert len({base.config_id, data.config_id, feat.config_id}) == 3


def test_seed_is_part_of_run_identity_but_not_unit_identity():
    unit = UnitSpec()
    a, b = Config(unit=unit, seed=0), Config(unit=unit, seed=1)
    assert a.run_id != b.run_id
    assert a.unit_id == b.unit_id
    assert a.config_id == b.config_id


def test_unit_id_ignores_training_hyperparameters():
    """Optimiser settings are not an experimental condition."""
    unit = UnitSpec()
    a = Config(unit=unit, train=TrainConfig(lr=1e-3))
    b = Config(unit=unit, train=TrainConfig(lr=3e-4))
    assert a.unit_id == b.unit_id


def test_unit_id_is_stable_across_processes():
    """Ids are content hashes, not object ids -- they must not drift."""
    assert Config(unit=UnitSpec(confound_rate=0.5)).unit_id == "".join(
        Config(unit=UnitSpec(confound_rate=0.5)).unit_id
    )
    assert Config(unit=UnitSpec(confound_rate=0.5)).unit_id != Config(
        unit=UnitSpec(confound_rate=0.75)
    ).unit_id


# --- the frozen constants are enforced, not merely documented -------------


def test_data_repair_multiplier_is_the_frozen_value():
    unit = UnitSpec(n_transitions=500)
    resolved = Arm("data_repair").resolve(unit)
    assert resolved.n_transitions == 500 * K.DATA_REPAIR_MULTIPLIER
    assert K.DATA_REPAIR_MULTIPLIER == 10


def test_repairs_never_combine_mechanisms():
    """Each repair changes exactly one thing (Plan §8.3)."""
    unit = UnitSpec(family="missing_feature", withheld_features=("shape",), hidden_size=32)
    for arm in ("data_repair", "feature_repair", "capacity_repair"):
        changed = {
            k
            for k, v in dataclasses.asdict(Arm(arm).resolve(unit)).items()
            if v != dataclasses.asdict(unit)[k]
        }
        assert len(changed) == 1, f"{arm} changed {changed}"


def test_meaningless_repairs_are_refused():
    with pytest.raises(ValueError, match="nothing to restore"):
        Arm("feature_repair").resolve(UnitSpec(withheld_features=()))
    with pytest.raises(ValueError, match="no capacity to add"):
        Arm("capacity_repair").resolve(UnitSpec(hidden_size=max(K.HIDDEN_SIZES)))


def test_invalid_specifications_are_rejected():
    with pytest.raises(ValueError):
        UnitSpec(family="nonsense")
    with pytest.raises(ValueError):
        UnitSpec(confound_rate=1.5)
    with pytest.raises(ValueError):
        Arm("magic_repair")


# --- Week 1 Tue: "a dummy run writes a complete, reloadable record" -------


def test_config_roundtrips_through_yaml(tmp_path):
    cfg = Config(
        unit=UnitSpec(family="missing_feature", withheld_features=("shape",), confound_rate=0.75),
        arm=Arm("data_repair"),
        seed=7,
        tags=("pilot",),
    )
    back = Config.load(cfg.save(tmp_path / "c.yaml"))
    assert back == cfg
    assert back.run_id == cfg.run_id


def test_run_record_is_complete_and_reloadable(tmp_path):
    cfg = Config(unit=UnitSpec(n_transitions=250), seed=3)
    with RunLogger.start(cfg, root=tmp_path) as log:
        log.log(epoch=0, mse=1.0)

    rec = read_run_record(tmp_path / cfg.run_id)
    assert rec["run_id"] == cfg.run_id
    assert rec["seed"] == 3
    assert rec["config"]["unit"]["n_transitions"] == 250
    assert rec["git"]["commit"]
    assert "dirty" in rec["git"]
    assert rec["env"]["packages"]["torch"] != "MISSING"
    assert Config.from_dict(rec["config"]) == cfg


def test_repair_arm_is_visible_in_the_record(tmp_path):
    cfg = Config(unit=UnitSpec(n_transitions=500), arm=Arm("data_repair"))
    RunLogger.start(cfg, root=tmp_path).close()
    rec = read_run_record(tmp_path / cfg.run_id)
    assert rec["effective_unit"]["n_transitions"] == 5000
    assert rec["arm_changed"] == {"n_transitions": 5000}


def test_duplicate_run_id_is_refused(tmp_path):
    cfg = Config(unit=UnitSpec(), seed=0)
    RunLogger.start(cfg, root=tmp_path).close()
    with pytest.raises(FileExistsError):
        RunLogger.start(cfg, root=tmp_path)


# --- Week 1 Wed: "three dummy runs load into one dataframe" ---------------


def test_three_runs_load_into_one_dataframe(tmp_path):
    unit = UnitSpec(n_transitions=1000)
    for seed in range(3):
        cfg = Config(unit=unit, seed=seed)
        with RunLogger.start(cfg, root=tmp_path) as log:
            for epoch in range(4):
                log.log(epoch=epoch, split="val", mse=1.0 / (epoch + 1))

    df = load_runs(tmp_path)
    assert len(df) == 12
    assert df["run_id"].nunique() == 3
    assert df["unit_id"].nunique() == 1, "one condition, three seeds, one unit"
    assert set(df["seed"]) == {0, 1, 2}
    assert df.columns[0] == "run_id"
    assert df["unit_n_transitions"].eq(1000).all()


def test_load_runs_on_empty_root_returns_empty_frame(tmp_path):
    df = load_runs(tmp_path)
    assert df.empty
    assert "unit_id" in df.columns


def test_logging_is_flushed_line_by_line(tmp_path):
    """A killed Kaggle session must not take the results with it (Plan §14.4)."""
    cfg = Config(unit=UnitSpec(), seed=0)
    log = RunLogger.start(cfg, root=tmp_path)
    log.log(epoch=0, mse=0.5)
    # Deliberately not closed -- simulate the process dying here.
    assert len(load_runs(tmp_path)) == 1


def test_empty_log_record_is_refused(tmp_path):
    with RunLogger.start(Config(), root=tmp_path) as log:
        with pytest.raises(ValueError):
            log.log()
