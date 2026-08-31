"""Synthetic-only Experiment-1 adapter tests; no training or real evidence.

Inventory/consumer adversaries explicitly replace the inner loader with test
objects. The separate on-disk fixture fabricates all 150 registered sidecars
using test_fit_evidence's source-document pattern; integration tests use the
UNMODIFIED production writer/reader and registry. Fabricated seeds/commits are
provenance test data, not experimental results. pytest temp roots must remain
under the project workspace (see the session's invocation).
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import numpy as np
import pytest
import torch

import test_fit_evidence as fixture_source
from bu import constants as K
from bu.experiments import experiment_1_evidence as E
from bu.experiments import fit_evidence as F
from bu.experiments.batch import experiment_1_jobs
from bu.experiments.enumerate_units import design_units, execution_plan
from bu.models.uncertainty import NormalisationScale
from bu.streams import comparison_group_id


COMMIT = "b" * 40


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


@pytest.fixture(scope="module")
def jobs():
    return experiment_1_jobs()


class _StubStore:
    """Inventory-only test double: returned objects are NOT source evidence."""

    def __init__(self, root, jobs):
        self.entries = {}
        self.calls = []
        for index, job in enumerate(jobs):
            path = (root / f"arbitrary-name-{index}").resolve()
            cfg = job.config
            group = comparison_group_id(job.unit, "exp1")
            action = np.tile(np.arange(K.EPISODE_LENGTH) % 4, K.EVALUATION_EPISODES)
            episode = np.repeat(np.arange(K.EVALUATION_EPISODES), K.EPISODE_LENGTH)
            step = np.tile(np.arange(K.EPISODE_LENGTH), K.EVALUATION_EPISODES)
            # Different configurations/seeds intentionally have different pools
            # and scales. Sizes WITHIN a configuration/seed stay paired.
            offset = int(group[:2], 16) + job.seed - K.CONFIRMATORY_SEED_BASE
            scale = NormalisationScale(torch.tensor([1.0 + offset, 2.0]), len(episode))
            error = np.linspace(0.1, 0.3, len(episode)) + job.unit.n_transitions / 10000
            disagreement = error / 3
            self.entries[path] = F.VerifiedFitEvidence(
                fit_dir=path,
                unit=job.unit,
                arm=job.arm,
                seed=job.seed,
                roles=job.roles,
                execution_stage=job.stage,
                unit_id=cfg.unit_id,
                config_id=cfg.config_id,
                fit_id=job.job_id,
                execution_run_id=cfg.run_id,
                execution_digest=_hash(job.job_id),
                evaluation_pool_digest=_hash(f"{group}:{job.seed}"),
                diagnostics=MappingProxyType({
                    "evaluation_action": action,
                    "disagreement": disagreement,
                    "scale": np.asarray(scale.as_row()["scale"], dtype=np.float64),
                }),
                error=error,
                episode=episode,
                step=step,
                scale=scale,
                n_train=job.unit.n_transitions,
                ensemble_size=cfg.train.ensemble_size,
            )
        self.paths = tuple(self.entries)

    def load(self, path, *, expected_git_commit):
        self.calls.append((path, expected_git_commit))
        return self.entries[path]

    def replace_first(self, **changes):
        path = self.paths[0]
        self.entries[path] = replace(self.entries[path], **changes)


@pytest.fixture
def stub(tmp_path, monkeypatch, jobs):
    store = _StubStore(tmp_path, jobs)
    monkeypatch.setattr(E, "load_fit_evidence", store.load)
    return store


def test_exact_grid_preserves_configuration_and_multirole_identity(stub, jobs):
    grid = E.load_experiment_1_evidence(stub.paths[::-1], expected_git_commit=COMMIT)
    assert type(grid) is E.Experiment1Evidence
    assert grid.expected_git_commit == COMMIT
    assert grid.seeds == (1000, 1001, 1002, 1003, 1004)
    assert grid.data_sizes == (100, 250, 500, 1000, 2500, 5000)
    assert len(grid.comparison_group_ids) == 5
    assert len(grid.rows) == 150
    assert {r.fit_id for r in grid.rows} == {j.job_id for j in jobs}
    assert sum(len(r.roles) == 2 for r in grid.rows) == 30
    assert len(stub.calls) == 150
    assert {commit for _, commit in stub.calls} == {COMMIT}
    assert tuple((r.comparison_group_id, r.seed, r.n_transitions) for r in grid.rows) == tuple(
        sorted((r.comparison_group_id, r.seed, r.n_transitions) for r in grid.rows)
    )
    for row in grid.rows:
        source = stub.entries[row.source_path]
        assert row.mean_error == float(np.mean(source.error, dtype=np.float64))
        assert row.mean_disagreement == float(np.mean(source.diagnostics["disagreement"], dtype=np.float64))
        assert row.execution_digest == source.execution_digest
        assert row.causal_attribute == row.unit.causal_attribute
        assert row.layout == row.unit.layout
        assert row.n_movement == len(row.episode) == len(row.step)
    # Pairing is required only within group+seed, not across groups or seeds.
    assert len({r.evaluation_pool_digest for r in grid.rows}) == 25


def test_result_is_immutable_and_detached_from_loader_arrays(stub):
    grid = E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)
    row = grid.rows[0]
    with pytest.raises(FrozenInstanceError):
        grid.rows = ()
    with pytest.raises(FrozenInstanceError):
        row.mean_error = 0
    with pytest.raises(FrozenInstanceError):
        row.scale.vector = (0, 0)
    with pytest.raises(TypeError):
        row.episode[0] = 999
    source = stub.entries[row.source_path]
    source.error[:] = 999
    source.episode[:] = 999
    source.step[:] = 999
    source.diagnostics["evaluation_action"][:] = 999
    source.diagnostics["scale"][:] = 999
    source.scale.vector[:] = 999
    assert row.mean_error < 1
    assert row.episode[0] == row.step[0] == row.evaluation_action[0] == 0
    assert row.scale.vector[1] == 2.0


@pytest.mark.parametrize("bad", [None, "", "b" * 39, "b" * 41, "B" * 40, "g" * 40, "main", True, 1000])
def test_public_commit_guard_precedes_even_a_monkeypatched_loader(stub, bad):
    with pytest.raises(ValueError, match="expected_git_commit"):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=bad)
    assert stub.calls == []


def test_commit_is_a_required_keyword(stub):
    with pytest.raises(TypeError, match="expected_git_commit"):
        E.load_experiment_1_evidence(stub.paths)
    assert stub.calls == []


@pytest.mark.parametrize("kind", ["partial", "empty", "extra", "duplicate_path", "alias"])
def test_inventory_rejected_before_opening_sources(stub, kind):
    paths = list(stub.paths)
    if kind == "partial":
        paths.pop()
    elif kind == "empty":
        paths = []
    elif kind == "extra":
        paths.append(paths[0].parent / "unexpected")
    elif kind == "duplicate_path":
        paths[-1] = paths[0]
    else:
        paths[-1] = paths[0] / ".." / paths[0].name
    with pytest.raises(ValueError, match="exactly 150|duplicate fit directory"):
        E.load_experiment_1_evidence(paths, expected_git_commit=COMMIT)
    assert stub.calls == []


@pytest.mark.parametrize("kind", ["single_path", "string", "generator", "string_element", "verified", "grid"])
def test_only_explicit_path_sequences_are_accepted(stub, kind):
    if kind == "single_path":
        bad = stub.paths[0]
    elif kind == "string":
        bad = str(stub.paths[0])
    elif kind == "generator":
        bad = iter(stub.paths)
    else:
        bad = list(stub.paths)
        if kind == "string_element":
            bad[0] = str(bad[0])
        elif kind == "verified":
            bad[0] = stub.entries[bad[0]]
        else:
            bad[0] = E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)
            stub.calls.clear()
    with pytest.raises(ValueError, match="Path objects"):
        E.load_experiment_1_evidence(bad, expected_git_commit=COMMIT)
    assert stub.calls == []


def test_duplicate_fit_under_different_directory_is_not_a_missing_cell(stub):
    first, last = stub.paths[0], stub.paths[-1]
    stub.entries[last] = replace(stub.entries[first], fit_dir=last)
    with pytest.raises(ValueError, match="duplicate Experiment-1 physical fit"):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("fit_id", "unregistered-s1000"),
        ("fit_id", []),
        ("unit_id", "f" * 12),
        ("config_id", "f" * 12),
        ("arm", "data_repair"),
        ("seed", 0),
        ("seed", 1005),
        ("seed", 1000.0),
        ("roles", ("exp1", "pilot")),
        ("roles", ["exp1"]),
        ("execution_stage", "pilot"),
        ("execution_run_id", "invented"),
        ("n_train", 1),
        ("ensemble_size", 1),
        ("execution_digest", "bad"),
        ("evaluation_pool_digest", "BAD"),
    ],
)
def test_consumer_checks_exact_job_identity_and_digest(stub, field, bad):
    stub.replace_first(**{field: bad})
    with pytest.raises(ValueError, match=f"{field}|unregistered"):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)


def test_same_identifier_cannot_cover_a_different_unit(stub):
    first = stub.entries[stub.paths[0]]
    stub.replace_first(unit=replace(first.unit, grid_size=first.unit.grid_size + 1))
    with pytest.raises(ValueError, match="unit does not equal"):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)


def test_source_path_is_checked(stub):
    stub.replace_first(fit_dir=stub.paths[-1])
    with pytest.raises(ValueError, match="different source path"):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)


def test_loader_result_must_be_exact_verified_type(stub):
    stub.entries[stub.paths[0]] = SimpleNamespace(fit_id="invented")
    with pytest.raises(ValueError, match="exact VerifiedFitEvidence"):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)


@pytest.mark.parametrize("field", ["evaluation_pool_digest", "scale", "episode", "step", "evaluation_action"])
def test_six_size_pairing_is_checked_separately_for_every_identity(stub, field):
    fit = stub.entries[stub.paths[0]]
    if field == "evaluation_pool_digest":
        stub.replace_first(evaluation_pool_digest="f" * 64)
    elif field == "scale":
        diagnostics = dict(fit.diagnostics)
        diagnostics["scale"] = diagnostics["scale"].copy()
        # Deliberately below float32 precision: the torch convenience scale
        # would hide this mismatch; the persisted float64 identity must not.
        diagnostics["scale"][1] += 1e-10
        stub.replace_first(diagnostics=diagnostics)
    elif field == "evaluation_action":
        diagnostics = dict(fit.diagnostics)
        diagnostics[field] = (diagnostics[field] + 1) % 4
        stub.replace_first(diagnostics=diagnostics)
    else:
        stub.replace_first(**{field: np.roll(getattr(fit, field), 1)})
    with pytest.raises(ValueError, match=f"paired Experiment-1 {field} differs"):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)


@pytest.mark.parametrize("field", ["error", "disagreement"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_invalid_numeric_arrays_are_not_summarised(stub, field, bad):
    fit = stub.entries[stub.paths[0]]
    (fit.error if field == "error" else fit.diagnostics[field])[0] = bad
    with pytest.raises(ValueError, match=field):
        E.load_experiment_1_evidence(stub.paths, expected_git_commit=COMMIT)


def _make_sidecar(root, job):
    """Fabricate source documents for one arbitrary REGISTERED job, never fit."""
    planned = SimpleNamespace(unit=job.unit, arm=job.arm, seed=job.seed - K.CONFIRMATORY_SEED_BASE)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(fixture_source, "_registered_shared_fit", lambda: planned)
        completed, _ = fixture_source._completed_run(root)
    group = comparison_group_id(job.unit, "exp1")
    pool_digest = _hash(f"synthetic:{group}:{job.seed}")
    # Nonbinary-exact float64 values test that result scale identity is copied
    # from the source diagnostic rather than the reader's float32 tensor.
    scale_values = [1.234567891 + int(group[:2], 16), 2.345678912]
    scale = NormalisationScale(torch.tensor(scale_values, dtype=torch.float64), len(completed.evaluation.error))
    diagnostics = dict(completed.diagnostics)
    diagnostics["scale"] = np.asarray(scale_values, dtype=np.float64)
    completed = replace(completed, diagnostics=diagnostics, evaluation=replace(completed.evaluation, scale=scale))

    def mutate(run, confirmation):
        run["extra"]["evaluation_pool_digest"] = pool_digest
        confirmation["evaluation_pool_digest"] = pool_digest
        confirmation["normalisation"] = scale.as_row()

    completed = fixture_source._rewrite_unsealed_sources(completed, mutate)
    F.write_fit_evidence(completed, fit_dir=root)


@pytest.fixture(scope="module")
def disk_grid(tmp_path_factory, jobs):
    root = tmp_path_factory.mktemp("synthetic-exp1-sidecars")
    for index, job in enumerate(jobs):
        _make_sidecar(root / f"source-{index:03d}", job)
    return tuple(root / f"source-{index:03d}" for index in range(len(jobs)))


def _tree_fingerprint(paths):
    return {
        path: (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
        for root in paths for path in root.rglob("*") if path.is_file()
    }


def test_full_150_sidecar_integration_uses_real_loader_without_training_or_writes(disk_grid, monkeypatch):
    def no_training(*args, **kwargs):
        raise AssertionError("an input adapter must never train")

    monkeypatch.setattr(F, "run_confirmatory", no_training)
    assert E.load_fit_evidence is F.load_fit_evidence
    before = _tree_fingerprint(disk_grid)
    grid = E.load_experiment_1_evidence(disk_grid[::-1], expected_git_commit=COMMIT)
    assert len(grid.rows) == 150
    assert len({r.evaluation_pool_digest for r in grid.rows}) == 25
    assert sum(len(r.roles) == 2 for r in grid.rows) == 30
    row = grid.rows[0]
    verified = F.load_fit_evidence(row.source_path, expected_git_commit=COMMIT)
    assert row.mean_error == float(np.mean(verified.error, dtype=np.float64))
    assert row.mean_disagreement == float(np.mean(verified.diagnostics["disagreement"], dtype=np.float64))
    assert row.scale.vector == tuple(verified.diagnostics["scale"])
    assert row.scale.vector != tuple(float(v) for v in verified.scale.vector)
    assert row.episode == tuple(verified.episode)
    assert row.step == tuple(verified.step)
    assert row.evaluation_action == tuple(verified.diagnostics["evaluation_action"])
    assert row.execution_digest == verified.execution_digest
    assert _tree_fingerprint(disk_grid) == before


def test_real_loader_refuses_mixed_execution_commits(disk_grid, tmp_path):
    other = tmp_path / "same-fit-other-commit"
    shutil.copytree(disk_grid[0], other)
    fixture_source._resign_physical_sources(
        other, lambda run, confirmation: run["git"].update(commit="c" * 40)
    )
    # First prove this is internally valid evidence at the other clean commit.
    F.load_fit_evidence(other, expected_git_commit="c" * 40)
    with pytest.raises(ValueError, match="Git commit does not equal"):
        E.load_experiment_1_evidence((other, *disk_grid[1:]), expected_git_commit=COMMIT)


def test_repeated_load_reopens_and_rejects_tampered_source(disk_grid, tmp_path):
    changed = tmp_path / "tampered-fit"
    shutil.copytree(disk_grid[0], changed)
    paths = (changed, *disk_grid[1:])
    E.load_experiment_1_evidence(paths, expected_git_commit=COMMIT)
    error_path = changed / "evaluation" / "error.npy"
    error_path.write_bytes(error_path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="artifact 'error' bytes"):
        E.load_experiment_1_evidence(paths, expected_git_commit=COMMIT)


def test_real_partial_sidecar_is_not_an_inventory_cell(disk_grid, tmp_path):
    partial = tmp_path / "partial"
    partial.mkdir()
    with pytest.raises(ValueError, match="legacy or partial evidence"):
        E.load_experiment_1_evidence((partial, *disk_grid[1:]), expected_git_commit=COMMIT)


def test_real_registered_non_experiment1_fit_is_refused(disk_grid, tmp_path):
    planned = next(
        fit for fit in execution_plan(design_units())
        if fit.arm == "baseline" and "exp1" not in fit.roles and fit.seed == 0
    )
    job = SimpleNamespace(
        unit=planned.unit, arm=planned.arm, seed=K.CONFIRMATORY_SEED_BASE
    )
    other = tmp_path / "registered-but-not-exp1"
    _make_sidecar(other, job)
    assert "exp1" not in F.load_fit_evidence(other, expected_git_commit=COMMIT).roles
    with pytest.raises(ValueError, match="unregistered Experiment-1 fit"):
        E.load_experiment_1_evidence((other, *disk_grid[1:]), expected_git_commit=COMMIT)


@pytest.mark.parametrize("field", ["evaluation_pool_digest", "scale"])
def test_internally_valid_real_sidecar_still_must_pair_across_sizes(disk_grid, tmp_path, field):
    changed = tmp_path / f"unpaired-{field}"
    shutil.copytree(disk_grid[0], changed)
    if field == "evaluation_pool_digest":
        def mutate(run, confirmation):
            run["extra"][field] = "f" * 64
            confirmation[field] = "f" * 64

        fixture_source._resign_physical_sources(
            changed, mutate, mutate_procedure=lambda p: p.update({field: "f" * 64})
        )
    else:
        vector = np.asarray(
            fixture_source._sidecar(changed)["procedure"]["normalisation"]["scale"],
            dtype=np.float64,
        )
        vector[1] += 1e-10
        fixture_source._replace_diagnostic(changed, "scale", vector)

        def mutate(run, confirmation):
            confirmation["normalisation"]["scale"] = vector.tolist()

        fixture_source._resign_physical_sources(
            changed, mutate,
            mutate_procedure=lambda p: p["normalisation"].update(scale=vector.tolist()),
        )
    F.load_fit_evidence(changed, expected_git_commit=COMMIT)
    with pytest.raises(ValueError, match=f"paired Experiment-1 {field} differs"):
        E.load_experiment_1_evidence((changed, *disk_grid[1:]), expected_git_commit=COMMIT)


def test_figure_consumer_reopens_all_150_real_reader_sources(disk_grid, tmp_path, monkeypatch):
    """Composition test: fabricated sidecars -> actual reader -> actual PNGs.

    The other figure tests isolate their reader. This final integration check
    leaves BOTH scientific readers and the Agg renderer real; only matplotlib's
    cached filesystem location is adapted if an earlier test imported it.
    """
    import json
    from bu.experiments import make_figures as MF
    from test_experiment_1_figures import local_plotting_cache

    # Reuse the standalone-safe environment setup, not any evidence stub.
    local_plotting_cache.__wrapped__(monkeypatch)
    calls = []
    real_reader = E.load_fit_evidence
    assert real_reader is F.load_fit_evidence

    def traced_reader(path, *, expected_git_commit):
        calls.append((path, expected_git_commit))
        return real_reader(path, expected_git_commit=expected_git_commit)

    def no_training(*args, **kwargs):
        raise AssertionError("figure regeneration must not train")

    monkeypatch.setattr(E, "load_fit_evidence", traced_reader)
    monkeypatch.setattr(F, "run_confirmatory", no_training)
    before = _tree_fingerprint(disk_grid)
    paths = MF.experiment_1_figures(
        tmp_path / "source-verified-figures",
        fit_directories=disk_grid,
        expected_git_commit=COMMIT,
    )
    assert len(calls) == 150
    assert set(calls) == {(path.resolve(), COMMIT) for path in disk_grid}
    document = json.loads(paths[-1].read_text(encoding="utf-8"))
    assert len(document["rows"]) == 150
    assert len({row["fit_id"] for row in document["rows"]}) == 150
    assert {row["source_path"] for row in document["rows"]} == {
        str(path.resolve()) for path in disk_grid
    }
    for artifact, path in zip(document["figures"], paths[:2], strict=True):
        data = path.read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(data) > 1000
        assert artifact["sha256"] == hashlib.sha256(data).hexdigest()
    assert _tree_fingerprint(disk_grid) == before
