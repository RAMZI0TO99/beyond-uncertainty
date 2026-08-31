"""Synthetic-only figure preparation: no training and no real E1 payloads.

The loader is deliberately isolated with an immutable fabricated 150-row grid.
These tests prove figure/manifest/integration behaviour and refusal propagation,
not the authenticity of that fabricated grid. Real-reader synthetic-sidecar
integration belongs to test_experiment_1_evidence. The fixture supplies a local
matplotlib cache even without environment setup; it resets only cached location
getters if another test imported matplotlib first. Rendering remains real Agg.
Run with project-local TEMP/TMP and pytest --basetemp for local scratch files.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu import constants as K
from bu.durable import DivergentTargetError, DurabilityError
from bu.experiments import experiment_1_figures as F
from bu.experiments import make_figures as MF
from bu.experiments.batch import experiment_1_jobs
from bu.experiments.experiment_1_evidence import Experiment1Evidence, Experiment1Row, Experiment1Scale
from bu.streams import comparison_group_id, confirmatory_seeds


COMMIT = "c" * 40


def _digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


@pytest.fixture(autouse=True)
def local_plotting_cache(monkeypatch):
    """Standalone-safe and compatible with matplotlib imported by older tests.

    Preserve an inherited project-local cache. Otherwise choose one here, before
    importing matplotlib. Its location getters memoize their FIRST call with no
    cache_clear API; when an older test imported it first, re-evaluate the real
    undecorated location function under our env and cache that result for this
    test only. The explicit late-env-change refusal test still sees a cached
    value and exercises the production guard. No rendering function is stubbed.
    """
    project = Path(__file__).resolve().parents[1]
    configured = os.environ.get("MPLCONFIGDIR")
    cache = Path(configured).resolve() if configured else project / ".pytest_cache" / "figure-mpl"
    if not cache.is_relative_to(project):
        cache = project / ".pytest_cache" / "figure-mpl"
    monkeypatch.setenv("MPLCONFIGDIR", str(cache))
    import matplotlib

    for name in ("get_configdir", "get_cachedir"):
        getter = getattr(matplotlib, name)
        if Path(getter()).resolve() != cache:
            actual = getter.__wrapped__()
            assert Path(actual).resolve() == cache
            monkeypatch.setattr(matplotlib, name, lambda value=actual: value)


@pytest.fixture(scope="module")
def jobs():
    return experiment_1_jobs()


@pytest.fixture
def synthetic(tmp_path, monkeypatch, jobs):
    rows = []
    for index, job in enumerate(jobs):
        group = comparison_group_id(job.unit, "exp1")
        rows.append(Experiment1Row(
            causal_attribute=job.unit.causal_attribute,
            layout=job.unit.layout,
            comparison_group_id=group,
            seed=job.seed,
            n_transitions=job.unit.n_transitions,
            unit=job.unit,
            unit_id=job.config.unit_id,
            config_id=job.config.config_id,
            fit_id=job.job_id,
            arm=job.arm,
            roles=job.roles,
            execution_stage=job.stage,
            execution_run_id=job.config.run_id,
            source_path=(tmp_path / "synthetic-evidence" / job.job_id).resolve(),
            execution_digest=_digest(job.job_id),
            evaluation_pool_digest=_digest(f"{group}:{job.seed}"),
            scale=Experiment1Scale((1.0, 2.0), 2, "movement", "evaluation_pool"),
            episode=(0, 0), step=(0, 1), evaluation_action=(0, 1), n_movement=2,
            # Distinct arbitrary values: a missing/swapped seed cannot hide.
            mean_error=0.2 + index / 1000,
            mean_disagreement=0.03 + index / 2000,
        ))
    evidence = Experiment1Evidence(
        expected_git_commit=COMMIT,
        comparison_group_ids=tuple(sorted({row.comparison_group_id for row in rows})),
        seeds=tuple(confirmatory_seeds(K.SEEDS_HYPOTHESIS)),
        data_sizes=tuple(K.DATA_SIZES), rows=tuple(reversed(rows)),
    )
    state = SimpleNamespace(
        evidence=evidence, calls=[], sources=tuple(row.source_path for row in rows),
        output=tmp_path / "figures", failure=None,
    )

    def loader(paths, *, expected_git_commit):
        state.calls.append((tuple(paths), expected_git_commit))
        if state.failure is not None:
            raise state.failure
        return state.evidence

    monkeypatch.setattr(F, "load_experiment_1_evidence", loader)
    return state


def _produce(state):
    return F.prepare_experiment_1_figures(
        state.sources, expected_git_commit=COMMIT, figures_dir=state.output
    )


@pytest.fixture
def cheap_render(monkeypatch):
    """Boundary tests isolate rendering; real Agg is used by the first tests."""
    calls = []

    def render(rows, metric, ylabel, cache):
        calls.append((rows, metric))
        return b"synthetic-render:" + metric.encode("ascii")

    monkeypatch.setattr(F, "_render_png", render)
    return calls


def test_real_render_keeps_every_seed_scalar_and_configuration(synthetic, monkeypatch):
    from matplotlib.figure import Figure
    from PIL import Image

    captured = []
    savefig = Figure.savefig

    def inspect_then_save(figure, *args, **kwargs):
        captured.append([
            [(tuple(line.get_xdata()), tuple(line.get_ydata()), line.get_label())
             for line in axis.lines]
            for axis in figure.axes
        ])
        assert "not an H1 decision" in " ".join(t.get_text() for t in figure.texts)
        return savefig(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", inspect_then_save)
    paths = _produce(synthetic)
    assert len(paths) == 3 and paths[-1].name == F.MANIFEST_FILE
    assert synthetic.calls == [(synthetic.sources, COMMIT)]
    manifest = json.loads(paths[-1].read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert len(manifest["rows"]) == 150
    assert manifest["seeds"] == list(range(1000, 1005))
    assert manifest["data_sizes"] == list(K.DATA_SIZES)
    assert "not an H1 decision" in manifest["interpretation"]
    assert manifest["aggregation"].startswith("none across seeds or configurations")
    by_cell = {
        (row.comparison_group_id, row.seed, row.n_transitions): row
        for row in synthetic.evidence.rows
    }
    for metric_index, metric in enumerate(("mean_error", "mean_disagreement")):
        panels = captured[metric_index]
        assert len(panels) == 6 and panels[-1] == []
        for group_index, group in enumerate(synthetic.evidence.comparison_group_ids):
            lines = panels[group_index]
            assert len(lines) == 5
            for seed_index, seed in enumerate(synthetic.evidence.seeds):
                x, y, label = lines[seed_index]
                assert x == tuple(K.DATA_SIZES)
                assert y == tuple(getattr(by_cell[group, seed, n], metric) for n in K.DATA_SIZES)
                assert label == f"seed {seed}"
        with Image.open(paths[metric_index]) as image:
            assert image.format == "PNG" and image.size == (1820, 1120)
            assert "Creation Time" not in image.info
        artifact = manifest["figures"][metric_index]
        assert artifact["filename"] == paths[metric_index].name
        assert artifact["metric"] == metric
        assert artifact["sha256"] == hashlib.sha256(paths[metric_index].read_bytes()).hexdigest()
    for point in manifest["rows"]:
        row = by_cell[point["comparison_group_id"], point["seed"], point["n_transitions"]]
        assert point["source_path"] == str(row.source_path)
        for field in ("fit_id", "unit_id", "config_id", "execution_digest",
                      "evaluation_pool_digest", "mean_error", "mean_disagreement"):
            assert point[field] == getattr(row, field)
        assert point["expected_git_commit"] == COMMIT
    assert {path.name for path in synthetic.output.iterdir()} == {path.name for path in paths}


def test_real_render_is_byte_identical_and_reopens_on_each_call(synthetic):
    first = _produce(synthetic)
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in first}
    synthetic.evidence = replace(synthetic.evidence, rows=tuple(reversed(synthetic.evidence.rows)))
    second = _produce(synthetic)
    assert len(synthetic.calls) == 2
    assert {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in second} == before


@pytest.mark.parametrize("failure", [
    ValueError("source digest changed"), ValueError("mixed execution commit"),
    ValueError("wrong registered role"), FileNotFoundError("missing fit sidecar"),
])
def test_source_refusal_propagates_before_render_or_any_output(synthetic, cheap_render, failure):
    synthetic.failure = failure
    with pytest.raises(type(failure), match=str(failure)):
        _produce(synthetic)
    assert len(synthetic.calls) == 1 and cheap_render == []
    assert not synthetic.output.exists()


def test_existing_figures_never_allow_bypassing_a_changed_source(synthetic, cheap_render):
    paths = _produce(synthetic)
    before = {p.name: p.read_bytes() for p in paths}
    synthetic.failure = ValueError("source changed since previous figure")
    with pytest.raises(ValueError, match="source changed"):
        _produce(synthetic)
    assert len(synthetic.calls) == 2
    assert {p.name: p.read_bytes() for p in paths} == before


@pytest.mark.parametrize("change,match", [
    ({"mean_error": float("nan")}, "finite"),
    ({"mean_disagreement": float("inf")}, "finite"),
    ({"mean_error": -1.0}, "nonnegative"),
    ({"mean_disagreement": True}, "float"),
    ({"seed": True}, "unregistered"),
    ({"seed": 1}, "unregistered"),
    ({"n_transitions": 101}, "unregistered"),
    ({"execution_digest": "not-a-digest"}, "execution_digest"),
    ({"evaluation_pool_digest": "x" * 64}, "evaluation_pool_digest"),
    ({"layout": "changed"}, "metadata varies"),
])
def test_invalid_loader_row_is_refused_before_output(synthetic, cheap_render, change, match):
    rows = list(synthetic.evidence.rows)
    rows[0] = replace(rows[0], **change)
    synthetic.evidence = replace(synthetic.evidence, rows=tuple(rows))
    with pytest.raises(ValueError, match=match):
        _produce(synthetic)
    assert cheap_render == [] and not synthetic.output.exists()


@pytest.mark.parametrize("kind", ["missing", "duplicate", "commit", "groups", "seed-inventory", "source"])
def test_incomplete_or_misbound_grid_has_no_output(synthetic, cheap_render, kind):
    evidence = synthetic.evidence
    if kind == "missing":
        evidence = replace(evidence, rows=evidence.rows[:-1])
    elif kind == "duplicate":
        evidence = replace(evidence, rows=(evidence.rows[1],) + evidence.rows[1:])
    elif kind == "commit":
        evidence = replace(evidence, expected_git_commit="d" * 40)
    elif kind == "groups":
        evidence = replace(evidence, comparison_group_ids=evidence.comparison_group_ids[:-1])
    elif kind == "seed-inventory":
        evidence = replace(evidence, seeds=tuple(range(1001, 1006)))
    else:
        row = replace(evidence.rows[0], source_path=synthetic.output / "unknown")
        evidence = replace(evidence, rows=(row,) + evidence.rows[1:])
    synthetic.evidence = evidence
    with pytest.raises(ValueError):
        _produce(synthetic)
    assert cheap_render == [] and not synthetic.output.exists()


@pytest.mark.parametrize("kind", ["rows", "one-path", "duplicate-path", "missing-path", "short-commit"])
def test_public_entry_refuses_handmade_or_inexact_inputs(synthetic, cheap_render, kind):
    sources, commit = synthetic.sources, COMMIT
    if kind == "rows":
        sources = synthetic.evidence.rows
    elif kind == "one-path":
        sources = str(synthetic.sources[0])
    elif kind == "duplicate-path":
        sources = (sources[1],) + sources[1:]
    elif kind == "missing-path":
        sources = sources[:-1]
    else:
        commit = COMMIT[:7]
    with pytest.raises(ValueError):
        F.prepare_experiment_1_figures(sources, expected_git_commit=commit, figures_dir=synthetic.output)
    assert synthetic.calls == [] and cheap_render == [] and not synthetic.output.exists()


@pytest.mark.parametrize("relation", ["equal", "within", "ancestor", "cache"])
def test_output_and_cache_cannot_overlap_evidence(synthetic, cheap_render, monkeypatch, relation):
    if relation == "equal":
        synthetic.output = synthetic.sources[0]
    elif relation == "within":
        synthetic.output = synthetic.sources[0] / "figures"
    elif relation == "ancestor":
        synthetic.output = synthetic.sources[0].parent
    else:
        monkeypatch.setenv("MPLCONFIGDIR", str(synthetic.sources[0] / "cache"))
    with pytest.raises(ValueError, match="overlap"):
        _produce(synthetic)
    assert synthetic.calls == [] and cheap_render == [] and not synthetic.output.exists()


def test_missing_mpl_configuration_refuses_before_output(synthetic, cheap_render, monkeypatch):
    monkeypatch.delenv("MPLCONFIGDIR")
    with pytest.raises(ValueError, match="MPLCONFIGDIR"):
        _produce(synthetic)
    assert synthetic.calls == [] and not synthetic.output.exists()


def test_late_mpl_environment_change_cannot_hide_cached_location(synthetic, cheap_render, monkeypatch):
    import matplotlib

    inherited = Path(matplotlib.get_cachedir()).resolve()
    changed = synthetic.output.parent / "different-cache"
    assert changed != inherited
    monkeypatch.setenv("MPLCONFIGDIR", str(changed))
    with pytest.raises(ValueError, match="before importing matplotlib"):
        _produce(synthetic)
    assert synthetic.calls == [] and cheap_render == [] and not synthetic.output.exists()


@pytest.mark.parametrize("filename", [item[1] for item in F._METRICS] + [F.MANIFEST_FILE])
def test_any_divergent_artifact_is_refused_before_other_files(synthetic, cheap_render, filename):
    synthetic.output.mkdir()
    existing = synthetic.output / filename
    existing.write_bytes(b"preserve divergent artifact")
    with pytest.raises(DivergentTargetError, match="different content"):
        _produce(synthetic)
    assert list(synthetic.output.iterdir()) == [existing]
    assert existing.read_bytes() == b"preserve divergent artifact"


def test_nonregular_destination_refused_without_partial_outputs(synthetic, cheap_render):
    destination = synthetic.output / F.MANIFEST_FILE
    destination.mkdir(parents=True)
    with pytest.raises(DurabilityError, match="regular file"):
        _produce(synthetic)
    assert list(synthetic.output.iterdir()) == [destination]


def test_hardlinked_artifact_is_not_accepted_even_with_identical_bytes(synthetic, cheap_render):
    paths = _produce(synthetic)
    before = {path.name: path.read_bytes() for path in paths}
    os.link(paths[0], synthetic.output.parent / "hardlink-alias.png")
    with pytest.raises(DurabilityError, match="independent regular file"):
        _produce(synthetic)
    assert {path.name: path.read_bytes() for path in paths} == before


def test_second_render_failure_publishes_nothing(synthetic, monkeypatch):
    def render(rows, metric, ylabel, cache):
        if metric == "mean_disagreement":
            raise RuntimeError("renderer unavailable")
        return b"first synthetic PNG in memory"

    monkeypatch.setattr(F, "_render_png", render)
    with pytest.raises(RuntimeError, match="renderer unavailable"):
        _produce(synthetic)
    assert not synthetic.output.exists()


def test_explicit_integration_leaves_default_registry_unchanged(synthetic, cheap_render, monkeypatch):
    assert tuple(MF.FIGURES) == ("w3_pilot", "w4_gate")
    assert inspect.signature(F.prepare_experiment_1_figures).parameters["expected_git_commit"].default is inspect.Parameter.empty
    called = []
    monkeypatch.setattr(MF, "FIGURES", {"old": lambda path: called.append(path) or []})
    assert MF.main(synthetic.output) == []
    assert called == [synthetic.output] and synthetic.calls == []
    paths = MF.experiment_1_figures(
        synthetic.output, fit_directories=synthetic.sources, expected_git_commit=COMMIT
    )
    assert len(paths) == 3 and len(synthetic.calls) == 1
