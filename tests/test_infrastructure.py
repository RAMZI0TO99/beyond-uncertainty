"""Week 1 acceptance tests.

Each test corresponds to a "Done when" criterion from Schedule Week 1, plus the
identity invariants the labelling protocol depends on.
"""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu import constants as K
from bu.config import (
    IDENTITY_VERSION,
    UNIT_IDENTITY_FIELDS,
    UNIT_NON_IDENTITY_FIELDS,
    Arm,
    Config,
    TrainConfig,
    STAGES,
    UnitSpec,
    classification_of,
    seeds_for,
)
from bu.metrics import RunLogger, load_runs
from bu.runrecord import PROJECT_ROOT, GitState, git_state, read_run_record

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


def test_one_unit_can_carry_several_stage_obligations(tmp_path):
    """A unit is one statistical unit but may owe runs to several stages.

    Sol's material finding: a canonical condition enters an H1/H2 claim at five
    seeds AND canonical repair validation at twenty, which overlap on seeds 0-4.
    Without the stage in the run identity those are the same run, and the five
    seeds behind an H1/H2 claim could not be separated from the twenty behind a
    repair label.
    """
    unit = UnitSpec(family="missing_feature", withheld_features=("shape",))
    h2 = Config(unit=unit, stage="exp2a", seed=3)
    repair = Config(unit=unit, stage="repair_validation", seed=3)

    assert h2.unit_id == repair.unit_id, "still one statistical unit"
    assert h2.config_id == repair.config_id, "same unit, same arm"
    assert h2.run_id != repair.run_id, "but distinct runs, separately recorded"

    # ...and both can be written without colliding on disk.
    RunLogger.start(h2, root=tmp_path).close()
    RunLogger.start(repair, root=tmp_path).close()
    df = load_runs(tmp_path)
    assert df.empty or df["unit_id"].nunique() == 1


def test_stage_seed_policy_matches_the_preregistration():
    """Plan §14.2's three seed counts, bound to the stages that require them."""
    assert seeds_for("exp1") == seeds_for("exp2a") == seeds_for("exp2b") == 5
    assert seeds_for("repair_validation") == 20
    assert seeds_for("config_sweep") == seeds_for("exp3_repairs") == 3
    assert seeds_for("ablation") == 5
    assert seeds_for("pilot") is None, "exploratory work carries no claim"


def test_unknown_stage_is_refused():
    with pytest.raises(ValueError, match="unknown stage"):
        Config(stage="whatever")
    with pytest.raises(ValueError, match="unknown stage"):
        seeds_for("whatever")


def test_stage_is_not_part_of_unit_identity():
    unit = UnitSpec()
    ids = {Config(unit=unit, stage=s).unit_id for s in STAGES}
    assert len(ids) == 1, "stage is an execution obligation, not a design axis"


def test_unit_id_ignores_training_hyperparameters():
    """Optimiser settings are not an experimental condition."""
    unit = UnitSpec()
    a = Config(unit=unit, train=TrainConfig(lr=1e-3))
    b = Config(unit=unit, train=TrainConfig(lr=3e-4))
    assert a.unit_id == b.unit_id


# --- the identity registry is honest, not merely declared (Sol, Q-005) -----


def test_every_config_field_is_classified():
    """Adding a field without classifying it must fail loudly."""
    for cls in (UnitSpec, Arm, Config):
        identity, excluded = classification_of(cls)
        actual = {f.name for f in dataclasses.fields(cls)}
        assert set(identity) | set(excluded) == actual
        assert not set(identity) & set(excluded)


def test_unclassified_field_is_rejected_at_import():
    """The exhaustiveness check is real: simulate forgetting to classify."""
    import bu.config as cfg

    original = cfg.UNIT_IDENTITY_FIELDS
    try:
        cfg.UNIT_IDENTITY_FIELDS = tuple(f for f in original if f != "confound_rate")
        with pytest.raises(RuntimeError, match="not classified"):
            cfg._assert_classification_exhaustive()
    finally:
        cfg.UNIT_IDENTITY_FIELDS = original
    cfg._assert_classification_exhaustive()  # restored


@pytest.mark.parametrize("field_name", UNIT_IDENTITY_FIELDS)
def test_each_identity_field_actually_changes_the_unit(field_name):
    """A field is only identity-bearing if varying it yields a different unit.

    This is the test that makes the registry a claim about behaviour rather
    than a comment. Sol's condition on Q-005 was a classification that is
    "tested equivalently", not merely documented.
    """
    base = UnitSpec()
    alternatives = {
        "causal_attribute": "colour",
        "confound_rate": 0.75,
        "layout": "clustered",
        "grid_size": 12,
        "n_objects": 6,
        "family": "capacity",
        "n_transitions": 250,
        "withheld_features": ("shape",),
        "hidden_size": 32,
    }
    varied = dataclasses.replace(base, **{field_name: alternatives[field_name]})
    assert getattr(varied, field_name) != getattr(base, field_name), "bad fixture"
    assert Config(unit=varied).unit_id != Config(unit=base).unit_id, (
        f"{field_name} is registered as identity-bearing but varying it does "
        "not change unit_id"
    )


@pytest.mark.parametrize("field_name", UNIT_NON_IDENTITY_FIELDS or ["__none__"])
def test_excluded_fields_do_not_change_the_unit(field_name):
    """Symmetric check. Vacuous while the exclusion list is empty, live after."""
    if field_name == "__none__":
        pytest.skip("no fields are currently excluded from statistical identity")
    base = UnitSpec()
    varied = dataclasses.replace(base, **{field_name: _perturb(getattr(base, field_name))})
    assert Config(unit=varied).unit_id == Config(unit=base).unit_id


def _perturb(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + 1
    if isinstance(value, str):
        return value + "_x"
    if isinstance(value, tuple):
        return value + ("extra",)
    raise TypeError(f"no perturbation defined for {type(value)}")


def test_identity_survives_a_non_identity_schema_addition():
    """A field classified as non-identity-bearing must not disturb existing ids.

    Simulated by hashing the registered payload directly: the id depends on the
    registry, not on the dataclass's full field set.
    """
    from bu.config import _identity_payload

    before = Config(unit=UnitSpec()).unit_id
    payload = _identity_payload(UnitSpec(), UNIT_IDENTITY_FIELDS)
    assert set(payload["fields"]) == set(UNIT_IDENTITY_FIELDS)
    assert payload["identity_version"] == IDENTITY_VERSION
    assert Config(unit=UnitSpec()).unit_id == before


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


def test_a_clean_looking_uncommitted_state_is_not_trustworthy():
    """P§13.7 requires an exact commit, not merely an empty status output.

    Outside a repository, ``git status --porcelain`` writes its error to
    stderr and stdout is empty.  Treating that as a clean tree would make a
    git-less export look more trustworthy than a dirty repository.
    """
    state = GitState(commit="UNCOMMITTED", dirty=False, branch="unknown")
    assert state.trustworthy is False


@pytest.mark.parametrize("commit", [None, "a" * 39, "A" * 40, "not-a-sha"])
def test_malformed_commit_identifiers_are_never_trustworthy(commit):
    state = GitState(commit=commit, dirty=False, branch="unknown")
    assert state.identifies_commit is False
    assert state.trustworthy is False


def test_git_state_outside_a_repository_fails_closed(tmp_path, monkeypatch):
    """Exercise real Git failure even with project-local pytest scratch.

    --basetemp may live inside this checkout. Prevent Git from discovering the
    enclosing project instead of assuming pytest always uses an outside path.
    No subprocess result or production provenance function is mocked.
    """
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent.resolve()))
    state = git_state(tmp_path)
    assert state.commit == "UNCOMMITTED"
    assert state.dirty is True
    assert state.trustworthy is False


@pytest.mark.parametrize(
    "failed_command",
    [
        ("rev-parse", "HEAD"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("status", "--porcelain"),
    ],
)
def test_git_state_command_failures_are_dirty_and_untrustworthy(
    monkeypatch, tmp_path, failed_command
):
    """No failed Git probe may be mistaken for evidence of a clean tree."""
    sha = b"a" * 40

    def fake_run(command, *, cwd, capture_output, check):
        assert Path(cwd) == tmp_path
        args = tuple(command[1:])
        outputs = {
            ("rev-parse", "HEAD"): sha,
            ("rev-parse", "--abbrev-ref", "HEAD"): (
                "feature/na\N{LATIN SMALL LETTER I WITH DIAERESIS}ve".encode()
            ),
            ("status", "--porcelain"): b"",
        }
        return SimpleNamespace(
            stdout=outputs[args],
            returncode=128 if args == failed_command else 0,
        )

    monkeypatch.setattr("bu.runrecord.subprocess.run", fake_run)
    state = git_state(tmp_path)

    assert state.dirty is True
    assert state.trustworthy is False
    if failed_command == ("rev-parse", "HEAD"):
        assert state.commit == "UNCOMMITTED"
    if failed_command == ("rev-parse", "--abbrev-ref", "HEAD"):
        assert state.branch == "unknown"
    else:
        assert state.branch == "feature/na\N{LATIN SMALL LETTER I WITH DIAERESIS}ve"


def test_git_state_ignores_stdout_from_a_failed_command(monkeypatch, tmp_path):
    """Plausible stdout does not rescue a nonzero Git return code."""

    def fake_run(command, *, cwd, capture_output, check):
        args = tuple(command[1:])
        if args == ("rev-parse", "HEAD"):
            return SimpleNamespace(stdout=b"b" * 40, returncode=7)
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return SimpleNamespace(stdout=b"main", returncode=0)
        return SimpleNamespace(stdout=b"", returncode=0)

    monkeypatch.setattr("bu.runrecord.subprocess.run", fake_run)
    state = git_state(tmp_path)
    assert state.commit == "UNCOMMITTED"
    assert state.dirty is True
    assert state.trustworthy is False


def test_git_state_default_is_bound_to_the_installed_project(monkeypatch):
    """Changing the caller's CWD cannot silently change provenance scope."""
    working_directories = []

    def fake_run(command, *, cwd, capture_output, check):
        working_directories.append(Path(cwd))
        args = tuple(command[1:])
        if args == ("rev-parse", "HEAD"):
            return SimpleNamespace(stdout=b"c" * 40, returncode=0)
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return SimpleNamespace(stdout=b"main", returncode=0)
        return SimpleNamespace(stdout=b"", returncode=0)

    monkeypatch.setattr("bu.runrecord.subprocess.run", fake_run)
    state = git_state()

    assert working_directories == [PROJECT_ROOT, PROJECT_ROOT, PROJECT_ROOT]
    assert state.commit == "c" * 40
    assert state.trustworthy is True


def test_run_logger_default_uses_installed_project_root(
    monkeypatch, tmp_path
):
    """RunLogger's historical ``repo='.'`` default is project-root bound."""
    working_directories = []

    def fake_run(command, *, cwd, capture_output, check):
        working_directories.append(Path(cwd))
        args = tuple(command[1:])
        if args == ("rev-parse", "HEAD"):
            return SimpleNamespace(stdout=b"d" * 40, returncode=0)
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return SimpleNamespace(stdout=b"main", returncode=0)
        return SimpleNamespace(stdout=b"", returncode=0)

    monkeypatch.setattr("bu.runrecord.subprocess.run", fake_run)
    cfg = Config(unit=UnitSpec(), seed=0)
    RunLogger.start(cfg, root=tmp_path).close()
    rec = read_run_record(tmp_path / cfg.run_id)

    assert working_directories == [PROJECT_ROOT, PROJECT_ROOT, PROJECT_ROOT]
    assert rec["git"]["commit"] == "d" * 40
    assert rec["git"]["trustworthy"] is True


def test_an_explicit_dot_repository_is_not_reinterpreted(monkeypatch, tmp_path):
    """Only the omitted default binds to PROJECT_ROOT; explicit paths survive."""
    working_directories = []

    def fake_run(command, *, cwd, capture_output, check):
        working_directories.append(Path(cwd))
        args = tuple(command[1:])
        if args == ("rev-parse", "HEAD"):
            return SimpleNamespace(stdout=b"e" * 40, returncode=0)
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return SimpleNamespace(stdout=b"main", returncode=0)
        return SimpleNamespace(stdout=b"", returncode=0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("bu.runrecord.subprocess.run", fake_run)
    state = git_state(".")
    assert state.trustworthy is True
    assert working_directories == [Path("."), Path("."), Path(".")]


def test_git_state_preserves_clean_real_repository_behavior(tmp_path):
    """A successful probe of a clean checkout still identifies its commit."""
    repo = tmp_path / "clean-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, check=True
    )
    tracked = repo / "tracked.txt"
    tracked.write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "base"], cwd=repo, check=True,
        capture_output=True,
    )

    state = git_state(repo)

    assert state.identifies_commit is True
    assert state.dirty is False
    assert state.branch != "unknown"
    assert state.trustworthy is True


def test_dirty_diff_preserves_utf8_bytes_on_windows(tmp_path):
    """Provenance capture must not decode a Git patch through cp1252."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"],
                   cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo,
                   check=True)
    tracked = repo / "tracked.txt"
    tracked.write_text("plain\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True,
                   capture_output=True)
    tracked.write_text("unicode en dash – survives\n", encoding="utf-8")
    expected = subprocess.run(
        ["git", "diff", "HEAD"], cwd=repo, check=True, capture_output=True
    ).stdout

    cfg = Config(unit=UnitSpec(), seed=0)
    RunLogger.start(cfg, root=tmp_path / "runs", repo=repo).close()
    assert (tmp_path / "runs" / cfg.run_id / "dirty.diff").read_bytes() == expected


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
