"""Offline fabricated-report tests for Experiment-2A figures.

The scientific source readers are never called here.  A fabricated, immutable
report object is returned by the report-reader boundary and real Agg rendering
exercises only report-contained scalars.  Strict report parsing is covered by
test_experiment_2a_report; this suite tests the offline consumer boundary.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import stat
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import DivergentTargetError
from bu.experiments import experiment_2a_figures as F
from bu.experiments import experiment_2a_report as R


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@pytest.fixture(autouse=True)
def local_plotting_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "_PROJECT_ROOT", tmp_path.resolve())
    cache = tmp_path / "experiment-2a-figure-mpl"
    monkeypatch.setenv("MPLCONFIGDIR", str(cache.resolve()))
    import matplotlib

    for name in ("get_configdir", "get_cachedir"):
        getter = getattr(matplotlib, name)
        if Path(getter()).resolve() != cache.resolve():
            actual = getter.__wrapped__()
            assert Path(actual).resolve() == cache.resolve()
            monkeypatch.setattr(matplotlib, name, lambda value=actual: value)


def _repair(passed: bool, offset: float) -> dict:
    effect = -0.35 - offset if passed else -0.08 + offset
    return {
        "effect": effect,
        "ci_low": effect - 0.08,
        "ci_high": effect + (0.08 if passed else 0.12),
        "passed": passed,
        "reason": "fabricated accepted" if passed else "fabricated not accepted",
    }


def _fabricated_report(project_root: Path) -> dict:
    units = []
    for index, unit in enumerate(R._registered_units()):
        observed = (0, 1, "ambiguous", "undiagnosed")[index % 4]
        seed_rows = []
        ratios = []
        for seed_index, seed in enumerate(range(1000, 1005)):
            ratio = float(0.06 + index * 0.004 + seed_index * 0.003)
            ratios.append(ratio)
            undefined = (index + seed_index) % 9 == 0
            seed_rows.append(
                {
                    "seed": seed,
                    "ratio_of_means": ratio,
                    "pearson_r": None if undefined else float(-0.6 + 0.25 * seed_index),
                    "correlation_undefined_reason": (
                        "constant_error_or_disagreement" if undefined else None
                    ),
                }
            )
        mean, sd = R._mean_sd(ratios)
        units.append(
            {
                "unit_index": index,
                "unit_id": R._unit_id(unit),
                "configuration": {
                    "causal_attribute": unit.causal_attribute,
                    "layout": unit.layout,
                },
                "confound_rate": float(unit.confound_rate),
                "repair_evidence": {
                    "observed_label": observed,
                    "data_repair": _repair(index % 2 == 0, index / 1000),
                    "feature_repair": _repair(index % 3 == 0, index / 900),
                },
                "h2_diagnostics": {
                    "per_seed": seed_rows,
                    "ratio_mean_across_seeds": mean,
                    "ratio_sample_sd_across_seeds": sd,
                },
                "h2_verdict": None,
            }
        )
    unit_ids = [row["unit_id"] for row in units]
    authority_parent = project_root / "immutable-authorities"
    finalized_export = authority_parent / "finalized-export"
    finalized_copy = authority_parent / "finalized-copy"
    historical_execution = authority_parent / "historical-execution"
    historical_copy = authority_parent / "historical-copy"
    baseline_diagnostics = []
    for index in range(68):
        unit_id = unit_ids[index % len(unit_ids)]
        fit_id = f"finalized-baseline-{index:03d}"
        baseline_diagnostics.append(
            {
                "unit_id": unit_id,
                "fit_id": fit_id,
                "source_path": str(
                    finalized_export / unit_id / "sources" / fit_id
                ),
                "copy_path": str(
                    finalized_copy / unit_id / "sources" / fit_id
                ),
            }
        )
    for index in range(32):
        unit_id = unit_ids[index % len(unit_ids)]
        fit_id = f"historical-baseline-{index:03d}"
        baseline_diagnostics.append(
            {
                "unit_id": unit_id,
                "fit_id": fit_id,
                "source_path": str(
                    historical_execution / "fixed-batch" / "jobs" / fit_id
                ),
                "copy_path": str(
                    historical_copy / "fixed-batch" / "jobs" / fit_id
                ),
            }
        )
    first = baseline_diagnostics[0]
    return {
        "registered_inventory": {"seeds": list(range(1000, 1005))},
        "units": units,
        "source_manifests": {
            "baseline_diagnostics": baseline_diagnostics,
            "repair_validation_labels": [
                {
                    "unit_id": first["unit_id"],
                    "source_path": str(
                        finalized_export
                        / first["unit_id"]
                        / "label_evidence.json"
                    ),
                    "copy_path": str(
                        finalized_copy
                        / first["unit_id"]
                        / "label_evidence.json"
                    ),
                    "fit_sources": [
                        {
                            "fit_id": first["fit_id"],
                            "source_path": first["source_path"],
                            "copy_path": first["copy_path"],
                        }
                    ],
                }
            ],
            "ordinary_labels": [],
        },
        "payload_sha256": "d" * 64,
        "sign_consistency": None,
        "h2_verdict": None,
    }


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    report_path = tmp_path / "source" / "experiment_2a_report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_bytes(b"fabricated immutable report bytes\n")
    state = SimpleNamespace(
        report=_fabricated_report(tmp_path.resolve()),
        report_path=report_path,
        report_sha256=_digest(report_path.read_bytes()),
        output=tmp_path / "figures",
        authorities={
            "report": report_path.parent.resolve(),
            "finalized_export": (
                tmp_path / "immutable-authorities" / "finalized-export"
            ).resolve(),
            "finalized_copy": (
                tmp_path / "immutable-authorities" / "finalized-copy"
            ).resolve(),
            "historical_execution": (
                tmp_path / "immutable-authorities" / "historical-execution"
            ).resolve(),
            "historical_copy": (
                tmp_path / "immutable-authorities" / "historical-copy"
            ).resolve(),
        },
        calls=[],
        failure=None,
    )

    def loader(path, *, expected_sha256):
        state.calls.append((Path(path).resolve(), expected_sha256))
        if state.failure is not None:
            raise state.failure
        return deepcopy(state.report)

    monkeypatch.setattr(F.R, "load_experiment_2a_report", loader)
    return state


def _produce(state):
    return F.prepare_experiment_2a_figures(
        state.report_path,
        expected_report_sha256=state.report_sha256,
        figures_dir=state.output,
    )


@pytest.fixture
def cheap_render(monkeypatch):
    calls = []

    def forest(rows, cache):
        calls.append(("forest", rows))
        return b"fabricated forest png"

    def ratio(rows, cache):
        calls.append(("ratio", rows))
        return b"fabricated ratio png"

    def pearson(rows, seeds, cache):
        calls.append(("pearson", rows, seeds))
        return b"fabricated pearson png"

    monkeypatch.setattr(F, "_render_forest", forest)
    monkeypatch.setattr(F, "_render_ratio", ratio)
    monkeypatch.setattr(F, "_render_pearson", pearson)
    return calls


def test_plot_payload_contains_exact_twenty_unit_and_five_panel_scalars(synthetic):
    payload = F._plot_data(synthetic.report)
    assert len(payload["forest"]) == 20
    assert len(payload["ratio_panels"]) == 5
    assert len(payload["pearson"]) == 20
    assert payload["seeds"] == list(range(1000, 1005))
    assert payload["h2_verdict"] is None
    for panel in payload["ratio_panels"]:
        assert panel["confound_rates"] == [0.25, 0.5, 0.75, 0.9]
        assert len(panel["unit_ids"]) == 4
        assert len(panel["seed_lines"]) == 5
        assert all(len(line) == 4 for line in panel["seed_lines"])
        assert len(panel["means"]) == len(panel["sample_sds"]) == 4


def test_real_render_writes_three_pngs_and_manifest_last(synthetic):
    from PIL import Image

    paths = _produce(synthetic)
    assert [path.name for path in paths] == [
        F.FOREST_FILE,
        F.RATIO_FILE,
        F.PEARSON_FILE,
        F.MANIFEST_FILE,
    ]
    assert synthetic.calls == [(synthetic.report_path.resolve(), synthetic.report_sha256)]
    manifest = json.loads(paths[-1].read_text(encoding="utf-8"))
    assert manifest["figure_count"] == 3
    assert manifest["unit_count"] == 20 and manifest["seed_count"] == 5
    assert manifest["source_report_sha256"] == synthetic.report_sha256
    assert manifest["source_report_payload_sha256"] == synthetic.report["payload_sha256"]
    assert manifest["plot_data_sha256"] == F._hash(F._plot_data(synthetic.report))
    assert manifest["sign_consistency"] is None and manifest["h2_verdict"] is None
    assert "secondary/non-decisional" in manifest["interpretation"]
    for path, item in zip(paths[:3], manifest["figures"], strict=True):
        assert item["filename"] == path.name
        assert item["sha256"] == _digest(path.read_bytes())
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert "Creation Time" not in image.info
    assert set(item.name for item in synthetic.output.iterdir()) == set(path.name for path in paths)


def test_real_render_is_byte_identical_on_offline_retry(synthetic):
    first = _produce(synthetic)
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in first}
    second = _produce(synthetic)
    assert len(synthetic.calls) == 2
    assert {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in second} == before


def test_undefined_pearson_cells_are_visibly_marked(synthetic, monkeypatch):
    from matplotlib.figure import Figure

    texts = []
    original = Figure.savefig

    def capture(figure, *args, **kwargs):
        if "Pearson" in " ".join(axis.get_title() for axis in figure.axes):
            texts.extend(text.get_text() for axis in figure.axes for text in axis.texts)
        return original(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    _produce(synthetic)
    assert "x" in texts


@pytest.mark.parametrize("failure", [
    ValueError("report digest changed"),
    ValueError("report payload invalid"),
    FileNotFoundError("report missing"),
])
def test_report_reader_refusal_precedes_render_and_output(synthetic, cheap_render, failure):
    synthetic.failure = failure
    with pytest.raises(type(failure), match=str(failure)):
        _produce(synthetic)
    assert cheap_render == []
    assert not synthetic.output.exists()


def test_rendering_uses_only_report_reader_not_scientific_sources(synthetic, cheap_render):
    source = inspect.getsource(F.prepare_experiment_2a_figures)
    for forbidden in (
        "load_fit_evidence",
        "load_label_evidence",
        "load_ordinary_label_evidence",
        "condition_failure_diagnostics",
    ):
        assert forbidden not in source
    paths = _produce(synthetic)
    assert len(paths) == 4 and len(cheap_render) == 3


@pytest.mark.parametrize("filename", [F.FOREST_FILE, F.RATIO_FILE, F.PEARSON_FILE, F.MANIFEST_FILE])
def test_any_divergent_destination_blocks_all_new_publication(synthetic, cheap_render, filename):
    synthetic.output.mkdir()
    existing = synthetic.output / filename
    existing.write_bytes(b"preserve divergent artifact")
    with pytest.raises(DivergentTargetError, match="different content"):
        _produce(synthetic)
    assert list(synthetic.output.iterdir()) == [existing]
    assert existing.read_bytes() == b"preserve divergent artifact"


def test_second_renderer_failure_leaves_no_partial_artifacts(synthetic, monkeypatch):
    monkeypatch.setattr(F, "_render_forest", lambda rows, cache: b"first image")
    monkeypatch.setattr(
        F,
        "_render_ratio",
        lambda rows, cache: (_ for _ in ()).throw(RuntimeError("renderer failed")),
    )
    monkeypatch.setattr(F, "_render_pearson", lambda rows, seeds, cache: b"third image")
    with pytest.raises(RuntimeError, match="renderer failed"):
        _produce(synthetic)
    assert not synthetic.output.exists()


def test_missing_matplotlib_configuration_refuses_before_report_read(synthetic, monkeypatch):
    monkeypatch.delenv("MPLCONFIGDIR")
    with pytest.raises(ValueError, match="MPLCONFIGDIR"):
        _produce(synthetic)
    assert synthetic.calls == [] and not synthetic.output.exists()


def test_figure_output_cannot_overlap_source_report(synthetic, cheap_render):
    synthetic.output = synthetic.report_path.parent
    with pytest.raises(ValueError, match="pairwise disjoint"):
        _produce(synthetic)
    assert synthetic.calls == [] and cheap_render == []


def test_figure_output_and_matplotlib_cache_must_be_disjoint(
    synthetic, cheap_render, monkeypatch
):
    monkeypatch.setenv("MPLCONFIGDIR", str(synthetic.output))
    with pytest.raises(ValueError, match="pairwise disjoint"):
        _produce(synthetic)
    assert synthetic.calls == [] and cheap_render == []


def test_figure_output_must_be_disjoint_from_recorded_scientific_sources(
    synthetic, cheap_render
):
    source = Path(
        synthetic.report["source_manifests"]["baseline_diagnostics"][0]["source_path"]
    )
    synthetic.output = source / "figures"
    with pytest.raises(ValueError, match="immutable authority root"):
        _produce(synthetic)
    # The immutable report is read, but rendering/publication never begins.
    assert len(synthetic.calls) == 1 and cheap_render == []
    assert not synthetic.output.exists()


def test_complete_immutable_authority_roots_are_derived_exactly(synthetic):
    assert F._immutable_authority_roots(
        synthetic.report_path.resolve(), synthetic.report
    ) == set(synthetic.authorities.values())


def _redirect_matplotlib_cache(monkeypatch, path: Path) -> None:
    monkeypatch.setenv("MPLCONFIGDIR", str(path))
    import matplotlib

    monkeypatch.setattr(matplotlib, "get_configdir", lambda: str(path))
    monkeypatch.setattr(matplotlib, "get_cachedir", lambda: str(path))


@pytest.mark.parametrize("destination", ["output", "cache"])
@pytest.mark.parametrize(
    "authority_name",
    [
        "report",
        "finalized_export",
        "finalized_copy",
        "historical_execution",
        "historical_copy",
    ],
)
def test_output_and_cache_refuse_sibling_below_every_complete_authority_root(
    synthetic, cheap_render, monkeypatch, destination, authority_name
):
    candidate = synthetic.authorities[authority_name] / "new-sibling-artifact"
    if destination == "output":
        synthetic.output = candidate
    else:
        _redirect_matplotlib_cache(monkeypatch, candidate)
    with pytest.raises(ValueError, match="immutable authority root"):
        _produce(synthetic)
    assert len(synthetic.calls) == 1 and cheap_render == []
    assert not candidate.exists()


@pytest.mark.parametrize("destination", ["output", "cache"])
@pytest.mark.parametrize("relation", ["at", "above"])
def test_output_and_cache_refuse_at_or_above_an_immutable_authority_root(
    synthetic, cheap_render, monkeypatch, destination, relation
):
    authority = synthetic.authorities["finalized_export"]
    candidate = authority if relation == "at" else authority.parent
    if destination == "output":
        synthetic.output = candidate
    else:
        _redirect_matplotlib_cache(monkeypatch, candidate)
    with pytest.raises(ValueError, match="immutable authority root"):
        _produce(synthetic)
    assert len(synthetic.calls) == 1 and cheap_render == []
    assert not candidate.exists()


def test_unassignable_source_path_fails_closed_before_render(
    synthetic, cheap_render
):
    row = synthetic.report["source_manifests"]["baseline_diagnostics"][-1]
    row["source_path"] = str(
        synthetic.authorities["historical_execution"]
        / "unregistered-layout"
        / row["fit_id"]
    )
    with pytest.raises(ValueError, match="historical fit source paths"):
        _produce(synthetic)
    assert len(synthetic.calls) == 1 and cheap_render == []
    assert not synthetic.output.exists()


def test_figure_output_must_stay_inside_project(synthetic, cheap_render):
    synthetic.output = R._PROJECT_ROOT.parent / f"{R._PROJECT_ROOT.name}-outside-figures"
    with pytest.raises(ValueError, match="inside project root"):
        _produce(synthetic)
    assert synthetic.calls == [] and cheap_render == []
    assert not synthetic.output.exists()


@pytest.mark.parametrize(
    ("mode", "attributes"),
    [
        (stat.S_IFLNK, 0),
        (stat.S_IFDIR, getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)),
    ],
)
def test_figure_output_refuses_lexical_symlink_or_reparse_component(
    synthetic, cheap_render, monkeypatch, mode, attributes
):
    synthetic.output.mkdir()
    blocked = synthetic.output
    original_lstat = Path.lstat

    def fake_lstat(self):
        if Path(self) == blocked:
            return SimpleNamespace(st_mode=mode, st_file_attributes=attributes, st_nlink=1)
        return original_lstat(self)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ValueError, match="symlink or reparse"):
        _produce(synthetic)
    assert synthetic.calls == [] and cheap_render == []


def test_manifest_payload_digest_binds_all_figure_hashes(synthetic, cheap_render):
    paths = _produce(synthetic)
    manifest = json.loads(paths[-1].read_text(encoding="utf-8"))
    payload = {key: value for key, value in manifest.items() if key != "payload_sha256"}
    assert manifest["payload_sha256"] == F._hash(payload)
    assert [item["kind"] for item in manifest["figures"]] == [
        "repair_effect_forest",
        "ratio_by_confound",
        "secondary_pearson_heatmap",
    ]
