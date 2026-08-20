"""Regressions from the Week 1 audit (2026-08-15).

One test per defect found. Each names the failure it prevents, because a
regression test whose purpose is forgotten gets deleted the first time it is
inconvenient.
"""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from bu.config import IDENTITY_VERSION, SCHEMA_VERSION, Arm, Config, UnitSpec, _hash
from bu.critic.schema import assert_no_forbidden_columns
from bu.metrics import RunLogger, load_runs
from bu.runrecord import read_run_record

# --- A1. stage was dropped by serialisation, defeating D-012 --------------


def test_stage_survives_a_dict_roundtrip():
    """to_dict() omitted stage, so a reloaded config silently became "pilot"."""
    cfg = Config(unit=UnitSpec(), stage="repair_validation", seed=3)
    back = Config.from_dict(cfg.to_dict())
    assert back.stage == "repair_validation"
    assert back.run_id == cfg.run_id
    assert back == cfg


def test_stage_survives_a_yaml_roundtrip(tmp_path):
    cfg = Config(unit=UnitSpec(), stage="exp2b", seed=1)
    assert Config.load(cfg.save(tmp_path / "c.yaml")).stage == "exp2b"


def test_run_record_states_the_stage(tmp_path):
    """Otherwise the stage exists only inside the run_id string."""
    cfg = Config(unit=UnitSpec(), stage="repair_validation", seed=3)
    RunLogger.start(cfg, root=tmp_path).close()
    rec = read_run_record(tmp_path / cfg.run_id)
    assert rec["stage"] == "repair_validation"
    assert Config.from_dict(rec["config"]).run_id == rec["run_id"]


def test_analysis_can_separate_the_two_obligations_of_one_unit(tmp_path):
    """The point of D-012, end to end.

    A unit's five H1/H2 seeds and the first five of its twenty repair-validation
    seeds are the same unit, arm and seed. Only the stage separates them, so
    without a stage column the analysis cannot tell which runs support which
    claim.
    """
    unit = UnitSpec(family="missing_feature", withheld_features=("shape",))
    for stage in ("exp2a", "repair_validation"):
        for seed in range(3):
            with RunLogger.start(
                Config(unit=unit, stage=stage, seed=seed), root=tmp_path
            ) as log:
                log.log(step=0, err=1.0)

    df = load_runs(tmp_path)
    assert "stage" in df.columns
    assert df["unit_id"].nunique() == 1, "one statistical unit throughout"
    assert set(df["stage"]) == {"exp2a", "repair_validation"}
    assert len(df[df["stage"] == "exp2a"]) == 3
    assert df[df["stage"] == "exp2a"]["seed"].tolist() == [0, 1, 2]


def test_stage_cannot_reach_the_critic():
    with pytest.raises(ValueError):
        assert_no_forbidden_columns(["stage"])


# --- A2. the hash had a repr fallback that embedded memory addresses ------


def test_hash_refuses_values_it_cannot_represent():
    """`default=repr` made unit_id depend on a memory address.

    It hid well: a freed address is usually reused immediately, so two hashes
    taken in sequence often agreed and the bug looked absent.
    """

    class Opaque:
        pass

    with pytest.raises(TypeError, match="JSON-representable"):
        _hash({"x": Opaque()})


def test_unit_id_is_identical_in_a_separate_process():
    """The old version of this test compared a value with itself."""
    code = (
        "from bu.config import Config, UnitSpec;"
        "print(Config(unit=UnitSpec(confound_rate=0.5)).unit_id)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == Config(unit=UnitSpec(confound_rate=0.5)).unit_id


# --- A3. semantically identical conditions produced different units -------


def test_int_and_float_spellings_are_one_unit():
    """0 and 0.0 hashed differently, splitting a condition into two units."""
    assert Config(unit=UnitSpec(confound_rate=0)).unit_id == (
        Config(unit=UnitSpec(confound_rate=0.0)).unit_id
    )
    assert Config(unit=UnitSpec(grid_size=8)).unit_id == (
        Config(unit=UnitSpec(grid_size=8.0)).unit_id
    )


def test_withheld_feature_order_does_not_create_a_second_unit():
    a = Config(unit=UnitSpec(withheld_features=("shape", "colour")))
    b = Config(unit=UnitSpec(withheld_features=("colour", "shape")))
    assert a.unit_id == b.unit_id


def test_a_repeated_withheld_feature_is_not_a_new_unit():
    a = Config(unit=UnitSpec(withheld_features=("shape",)))
    b = Config(unit=UnitSpec(withheld_features=("shape", "shape")))
    assert a.unit_id == b.unit_id
    assert b.unit.withheld_features == ("shape",)


def test_canonicalisation_happens_at_construction():
    # `confound_rate=0` rather than `1`: an int still exercises the int -> float
    # coercion this test is about, and 0.0 is a member of the frozen grid, which
    # the D-083 guard now requires. 1.0 never was a design value.
    u = UnitSpec(confound_rate=0, grid_size=8.0, withheld_features=("shape", "colour"))
    assert isinstance(u.confound_rate, float)
    assert u.confound_rate == 0.0
    assert isinstance(u.grid_size, int)
    assert u.withheld_features == ("colour", "shape")


# --- A4. invalid values were silently accepted as new units ---------------


def test_a_layout_typo_raises_instead_of_inventing_a_unit():
    """"unifrom" would have become a real configuration-condition."""
    with pytest.raises(ValueError, match="layout must be one of"):
        UnitSpec(layout="unifrom")


@pytest.mark.parametrize(
    "field", ["grid_size", "n_objects", "n_transitions", "hidden_size"]
)
def test_non_positive_sizes_are_refused(field):
    with pytest.raises(ValueError, match="must be positive"):
        UnitSpec(**{field: 0})


# --- A5. arrays were stringified into the metrics log ---------------------


def test_arrays_log_as_numbers_not_as_a_string(tmp_path):
    """Per-dimension error (Plan §10.3) is exactly this shape.

    Stringified, it writes without complaint, reloads as "[0.1 0.2 0.3]", and
    fails only when a figure much later tries arithmetic on it.
    """
    cfg = Config(unit=UnitSpec(), stage="pilot")
    with RunLogger.start(cfg, root=tmp_path) as log:
        log.log(step=0, per_dim_error=np.array([0.1, 0.2, 0.3]), scalar=np.float64(2.5))

    row = json.loads((tmp_path / cfg.run_id / "metrics.jsonl").read_text().strip())
    assert row["per_dim_error"] == [0.1, 0.2, 0.3]
    assert row["scalar"] == 2.5


def test_runs_in_nested_directories_are_still_found(tmp_path):
    """A batch runner grouping runs by stage must not make them invisible."""
    cfg = Config(unit=UnitSpec(), stage="exp1", seed=0)
    with RunLogger.start(cfg, root=tmp_path / "batch_07") as log:
        log.log(step=0, err=1.0)
    assert len(load_runs(tmp_path)) == 1


# --- A6. identity must not drift silently ---------------------------------

#: Golden ids under IDENTITY_VERSION 2. If a change to canonicalisation or to
#: the hash alters these, that is a change to what a statistical unit *is* --
#: it needs an IDENTITY_VERSION bump and a Change Record, not a green suite.
GOLDEN_UNIT_IDS = {
    "default": "8d3643edf353",
    "exp2a_c50": "399e994df8b7",
    "capacity_16": "da0b7fb0d265",
}


def test_unit_ids_match_their_golden_values():
    assert IDENTITY_VERSION == 2, "golden ids are pinned to identity version 2"
    cases = {
        "default": UnitSpec(),
        "exp2a_c50": UnitSpec(
            family="missing_feature", withheld_features=("shape",), confound_rate=0.5
        ),
        "capacity_16": UnitSpec(family="capacity", hidden_size=16),
    }
    actual = {name: Config(unit=u).unit_id for name, u in cases.items()}
    assert actual == GOLDEN_UNIT_IDS, (
        "unit_id changed. If that was intended, bump IDENTITY_VERSION, record a "
        "Change Record in DECISIONS.md, and update these values. If it "
        "was not intended, something silently altered what a unit means."
    )


def test_schema_version_is_two_after_the_stage_addition():
    assert SCHEMA_VERSION == 2


def test_rejecting_an_old_schema_version():
    cfg = Config(unit=UnitSpec()).to_dict()
    cfg["schema_version"] = 1
    with pytest.raises(ValueError, match="schema_version"):
        Config.from_dict(cfg)


def test_arms_still_share_a_unit_after_canonicalisation():
    """The property everything else rests on, re-checked post-change."""
    unit = UnitSpec(family="missing_feature", withheld_features=("shape",))
    ids = {Config(unit=unit, arm=Arm(k)).unit_id for k in ("baseline", "data_repair", "feature_repair")}
    assert len(ids) == 1


# --- D-083's latent float-identity risk, now guarded at construction ------


def test_a_computed_confound_rate_is_refused_rather_than_forking_a_unit():
    """The measured D-083 risk: `0.1 + 0.2` is not `0.3` and mints a new unit.

    Sol ruled against bumping IDENTITY_VERSION for a latent risk and asked for a
    construction-time guard instead, so this is the check that keeps identity
    stable by REFUSING the off-grid value rather than by quantising it.
    """
    assert 0.1 + 0.2 != 0.3, "the premise of this test no longer holds"
    with pytest.raises(ValueError, match="not an exact member of the frozen grid"):
        UnitSpec(confound_rate=0.1 + 0.2)


def test_every_grid_literal_is_accepted():
    """The guard must not refuse the design's own values."""
    from bu import constants as K

    for rate in set(K.CONFOUND_LEVELS_2A) | set(K.CONFOUND_LEVELS_SWEEP):
        assert UnitSpec(confound_rate=rate).confound_rate == rate
