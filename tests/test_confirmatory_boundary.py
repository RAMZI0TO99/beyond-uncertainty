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


def test_a_non_boolean_confirmatory_flag_is_rejected(tmp_path):
    """`bool("false")` is True, so a truthiness check waves through the exact
    corruption this validation exists to catch (D-045)."""
    cfg = _run(tmp_path, 0)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    data["confirmatory"] = "false"  # truthy string meaning the opposite
    record.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError, match="must be a JSON boolean"):
        load_runs(tmp_path)


def test_an_unrecognised_seed_partition_is_rejected(tmp_path):
    cfg = _run(tmp_path, 0)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    data["seed_partition"] = "Development"  # not one of the permitted strings
    record.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError, match="not one of"):
        load_runs(tmp_path)


@pytest.mark.parametrize("bad_partition", [True, ["confirmatory"]])
def test_seed_partition_must_be_an_exact_string(tmp_path, bad_partition):
    cfg = _run(tmp_path, 0)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    data["seed_partition"] = bad_partition
    record.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError, match="not one of"):
        load_runs(tmp_path)


def test_a_truthy_non_boolean_would_have_passed_the_old_check(tmp_path):
    """Pins why the type check is separate from the value check.

    Without it, "false" on a development run compares equal to
    is_confirmatory(seed) == False only after coercion -- and bool("false") is
    True, so it did not even do that. It passed as confirmatory.
    """
    assert bool("false") is True
    assert type("false") is not bool


def _rewrite_record(root, cfg: Config, change) -> None:
    record = root / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    change(data)
    record.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("field,bad_value", [
    ("unit_id", "rewritten-unit"),
    ("config_id", "rewritten-config"),
    ("run_id", "rewritten-run"),
    ("fit_id", "rewritten-fit"),
    ("seed", 1001),
    ("stage", "exp2a"),
])
def test_every_top_level_identity_is_checked_against_reconstructed_config(
        tmp_path, field, bad_value):
    cfg = _run(tmp_path, 1000)

    def change(data):
        data[field] = bad_value

    _rewrite_record(tmp_path, cfg, change)
    with pytest.raises(RuntimeError, match=field):
        load_runs(tmp_path)


def test_fit_id_is_reconstructed_for_schema_v2_records(tmp_path):
    """Historical records without the duplicate remain loadable."""
    cfg = _run(tmp_path, 1000)
    _rewrite_record(tmp_path, cfg, lambda data: data.pop("fit_id"))
    frame = load_runs(tmp_path)
    assert frame.loc[0, "fit_id"] == cfg.fit_id


def test_new_run_records_duplicate_the_computation_identity(tmp_path):
    cfg = _run(tmp_path, 1000)
    record = json.loads((tmp_path / cfg.run_id / "run.json").read_text())
    assert record["fit_id"] == cfg.fit_id


def test_seed_partition_fields_cannot_launder_a_changed_top_level_seed(tmp_path):
    """This is the concrete C-007 bypass: rewriting only the convenient top
    fields must not turn a development Config into a confirmatory run."""
    cfg = _run(tmp_path, 999)

    def change(data):
        data["seed"] = 1000
        data["seed_partition"] = "confirmatory"
        data["confirmatory"] = True

    _rewrite_record(tmp_path, cfg, change)
    with pytest.raises(RuntimeError, match="top-level seed=1000.*config.seed=999"):
        load_runs(tmp_path, require_confirmatory=True)


@pytest.mark.parametrize("location,bad_value", [
    ("top", True),
    ("top", "1000"),
    ("config", True),
    ("config", "1000"),
])
def test_seed_identity_rejects_bool_and_string_coercion(
        tmp_path, location, bad_value):
    cfg = _run(tmp_path, 1000)

    def change(data):
        if location == "top":
            data["seed"] = bad_value
        else:
            data["config"]["seed"] = bad_value

    _rewrite_record(tmp_path, cfg, change)
    with pytest.raises(RuntimeError, match="exact JSON integer"):
        load_runs(tmp_path)


def test_config_reconstruction_is_type_sensitive_beyond_seed(tmp_path):
    cfg = _run(tmp_path, 1000)

    def change(data):
        # UnitSpec ordinarily canonicalises this float back to int 100, and
        # Python equality alone would then treat the spellings as identical.
        data["config"]["unit"]["n_transitions"] = 100.0

    _rewrite_record(tmp_path, cfg, change)
    with pytest.raises(RuntimeError, match="coercive identity laundering"):
        load_runs(tmp_path)


def test_requested_run_ids_refuse_missing_and_metricless_members(tmp_path):
    good = _run(tmp_path, 1000)
    metricless = Config(unit=UnitSpec(n_transitions=100), seed=1001, stage="exp1")
    RunLogger.start(metricless, root=tmp_path).close()

    with pytest.raises(RuntimeError, match="missing run_id.*does-not-exist"):
        load_runs(tmp_path, run_ids=[good.run_id, "does-not-exist"])
    with pytest.raises(RuntimeError, match="no metric rows.*s1001"):
        load_runs(tmp_path, run_ids=[good.run_id, metricless.run_id])


@pytest.mark.parametrize("requested", ["one-run-id", [""], [True]])
def test_requested_run_id_inventory_requires_nonblank_strings(tmp_path, requested):
    with pytest.raises((TypeError, RuntimeError), match="run_ids|nonblank"):
        load_runs(tmp_path, run_ids=requested)


@pytest.mark.parametrize("field,bad_value", [
    ("trustworthy", "false"),
    ("trustworthy", 1),
    ("dirty", "false"),
    ("dirty", 0),
])
def test_require_clean_git_rejects_truthy_or_equal_non_booleans(
        tmp_path, field, bad_value):
    cfg = _run(tmp_path, 1000)

    def change(data):
        data["git"]["dirty"] = False
        data["git"]["trustworthy"] = True
        data["git"][field] = bad_value

    _rewrite_record(tmp_path, cfg, change)
    with pytest.raises(RuntimeError, match="exact JSON booleans"):
        load_runs(tmp_path, require_clean_git=True)


def test_require_clean_git_accepts_exact_clean_booleans(tmp_path):
    cfg = _run(tmp_path, 1000)

    def change(data):
        data["git"]["dirty"] = False
        data["git"]["trustworthy"] = True

    _rewrite_record(tmp_path, cfg, change)
    assert len(load_runs(tmp_path, require_clean_git=True)) == 1


@pytest.mark.parametrize("flag", [1, "true", None])
def test_loader_policy_flags_are_exact_booleans(tmp_path, flag):
    with pytest.raises(TypeError, match="exact bool"):
        load_runs(tmp_path, require_clean_git=flag)
    with pytest.raises(TypeError, match="exact bool"):
        load_runs(tmp_path, require_confirmatory=flag)
