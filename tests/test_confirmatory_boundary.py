"""The pilot boundary at the analysis boundary (D-040, D-042).

D-040 built the guard; Sol's next review pointed out that the tests exercised
the helper directly and never demonstrated that ``load_runs`` -- the actual
entry point every analysis goes through -- enforces anything. A guard that is
never shown to fire at the boundary it protects is a claim about the boundary,
not a property of it.

The distinction that these pin: the **numerical seed is authoritative**. The
``seed_partition`` and ``confirmatory`` fields in a run record are a convenience
for reading, and if they ever disagree with the seed the record has been altered
and the analysis must stop rather than pick a side.
"""

from __future__ import annotations

import json

import pytest

from bu import constants as K
from bu.config import Config, UnitSpec
from bu.metrics import RunLogger, load_runs
from bu.streams import confirmatory_seeds


def _run(root, seed: int, stage: str = "exp1") -> Config:
    cfg = Config(unit=UnitSpec(n_transitions=100), seed=seed, stage=stage)
    with RunLogger.start(cfg, root=root) as log:
        log.log(epoch=0, split="val", error=0.5)
    return cfg


def test_a_confirmatory_directory_loads(tmp_path):
    for seed in confirmatory_seeds(3):
        _run(tmp_path, seed)
    df = load_runs(tmp_path, require_confirmatory=True)
    assert len(df) == 3
    assert set(df["seed_partition"]) == {"confirmatory"}


def test_a_development_directory_is_rejected(tmp_path):
    for seed in (0, 1):
        _run(tmp_path, seed)
    with pytest.raises(ValueError, match="development seeds"):
        load_runs(tmp_path, require_confirmatory=True)


def test_a_mixed_directory_is_rejected(tmp_path):
    """The case a per-run check catches only by luck of iteration order."""
    _run(tmp_path, K.CONFIRMATORY_SEED_BASE)
    _run(tmp_path, 0)
    with pytest.raises(ValueError, match="development seeds"):
        load_runs(tmp_path, require_confirmatory=True)


def test_development_data_still_loads_without_the_flag(tmp_path):
    """Week 3 debugging depends on this: the range exists to be usable."""
    _run(tmp_path, 0)
    df = load_runs(tmp_path)
    assert len(df) == 1
    assert set(df["seed_partition"]) == {"development"}


def test_seed_partition_is_exposed_as_a_column(tmp_path):
    _run(tmp_path, 0)
    _run(tmp_path, K.CONFIRMATORY_SEED_BASE)
    df = load_runs(tmp_path)
    assert dict(zip(df["seed"], df["seed_partition"])) == {
        0: "development",
        K.CONFIRMATORY_SEED_BASE: "confirmatory",
    }


def test_a_record_whose_metadata_disagrees_with_its_seed_raises(tmp_path):
    """The seed is authoritative, and disagreement is a stop, not a vote."""
    cfg = _run(tmp_path, 0)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    data["seed_partition"] = "confirmatory"  # a lie
    data["confirmatory"] = True
    record.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError, match="seed 0 is 'development'"):
        load_runs(tmp_path)


def test_the_confirmatory_flag_is_checked_too(tmp_path):
    cfg = _run(tmp_path, 0)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    data["confirmatory"] = True  # partition left honest; flag lies
    record.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError, match="records confirmatory=True"):
        load_runs(tmp_path)


def test_the_check_fires_even_without_require_confirmatory(tmp_path):
    """An altered record is a defect whatever the analysis asked for."""
    cfg = _run(tmp_path, K.CONFIRMATORY_SEED_BASE)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    data["seed_partition"] = "development"
    record.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError):
        load_runs(tmp_path, require_confirmatory=False)
