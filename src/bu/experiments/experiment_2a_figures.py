"""Offline deterministic figures from one immutable Experiment-2A report.

This module never opens fit or label evidence.  The externally digest-pinned
JSON report is validated through :mod:`experiment_2a_report`, then every plotted
scalar is copied from that report into an in-memory render payload.  Three PNGs
are rendered before any publication, every destination is preflighted, and the
digest manifest is published last.  The report's strict source-path grammar is
also used to derive and protect every complete immutable authority root.
"""

from __future__ import annotations

import io
import json
import math
import os
import stat
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

from ..durable import (
    DivergentTargetError,
    DurabilityError,
    atomic_write_bytes,
    atomic_write_json,
    sha256_bytes,
)
from . import experiment_2a_report as R


FIGURE_SCHEMA_VERSION = 1
MANIFEST_FILE = "experiment_2a_figures.json"
FOREST_FILE = "experiment_2a_repair_effect_forest.png"
RATIO_FILE = "experiment_2a_ratio_by_confound.png"
PEARSON_FILE = "experiment_2a_secondary_pearson_heatmap.png"

_INTERPRETATION = (
    "Experiment-2A descriptive family figures only. Repair labels are observed "
    "classes; seed ratios are not pooled; Pearson is secondary/non-decisional; "
    "sign consistency and the H2 verdict remain unapplied."
)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"figure payload is not strict JSON: {exc}") from exc


def _hash(value: Any) -> str:
    import hashlib

    return hashlib.sha256(_canonical(value)).hexdigest()


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _paths(report_path: Path, figures_dir: str | Path) -> tuple[Path, Path, Path]:
    report = R._project_path(
        report_path,
        what="Experiment-2A source report",
        kind="file",
        must_exist=True,
    )
    if not isinstance(figures_dir, (str, Path)) or not str(figures_dir).strip():
        raise ValueError("figures_dir must be an explicit output directory")
    output = R._project_path(
        Path(figures_dir),
        what="Experiment-2A figure output",
        kind="directory",
        must_exist=False,
    )
    configured = os.environ.get("MPLCONFIGDIR")
    if not configured or not Path(configured).is_absolute():
        raise ValueError("set MPLCONFIGDIR to an explicit absolute project-local directory")
    cache = R._project_path(
        Path(configured),
        what="matplotlib cache",
        kind="directory",
        must_exist=False,
    )
    if any(
        _overlap(left, right)
        for left, right in ((output, report), (cache, report), (output, cache))
    ):
        raise ValueError("figure output, source report, and matplotlib cache must be pairwise disjoint")
    matplotlib = sys.modules.get("matplotlib")
    if matplotlib is not None:
        for actual in (matplotlib.get_configdir(), matplotlib.get_cachedir()):
            if Path(actual).resolve() != cache:
                raise ValueError("set MPLCONFIGDIR before importing matplotlib")
    return report, output, cache


def _repair_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "effect": value["effect"],
        "ci_low": value["ci_low"],
        "ci_high": value["ci_high"],
        "passed": value["passed"],
        "reason": value["reason"],
    }


def _plot_data(report: dict[str, Any]) -> dict[str, Any]:
    forest: list[dict[str, Any]] = []
    pearson: list[dict[str, Any]] = []
    panels: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in report["units"]:
        repair = row["repair_evidence"]
        diagnostic = row["h2_diagnostics"]
        causal = row["configuration"]["causal_attribute"]
        layout = row["configuration"]["layout"]
        label = repair["observed_label"]
        label_text = str(label)
        forest.append(
            {
                "unit_index": row["unit_index"],
                "unit_id": row["unit_id"],
                "causal_attribute": causal,
                "layout": layout,
                "confound_rate": row["confound_rate"],
                "observed_label": label,
                "display_label": (
                    f"{row['unit_index'] + 1:02d} {causal}/{layout} "
                    f"c={row['confound_rate']:.2f} | obs={label_text}"
                ),
                "data_repair": _repair_projection(repair["data_repair"]),
                "feature_repair": _repair_projection(repair["feature_repair"]),
            }
        )
        seed_rows = diagnostic["per_seed"]
        panels.setdefault((causal, layout), []).append(
            {
                "unit_id": row["unit_id"],
                "confound_rate": row["confound_rate"],
                "seed_ratios": [item["ratio_of_means"] for item in seed_rows],
                "ratio_mean": diagnostic["ratio_mean_across_seeds"],
                "ratio_sample_sd": diagnostic["ratio_sample_sd_across_seeds"],
            }
        )
        pearson.append(
            {
                "unit_index": row["unit_index"],
                "unit_id": row["unit_id"],
                "display_label": (
                    f"{row['unit_index'] + 1:02d} {causal}/{layout} "
                    f"c={row['confound_rate']:.2f}"
                ),
                "values": [item["pearson_r"] for item in seed_rows],
                "undefined_reasons": [
                    item["correlation_undefined_reason"] for item in seed_rows
                ],
            }
        )
    ratio_panels = []
    for (causal, layout), rows in panels.items():
        ordered = sorted(rows, key=lambda item: item["confound_rate"])
        ratio_panels.append(
            {
                "causal_attribute": causal,
                "layout": layout,
                "confound_rates": [item["confound_rate"] for item in ordered],
                "unit_ids": [item["unit_id"] for item in ordered],
                "seeds": list(report["registered_inventory"]["seeds"]),
                "seed_lines": [
                    [item["seed_ratios"][seed_index] for item in ordered]
                    for seed_index in range(5)
                ],
                "means": [item["ratio_mean"] for item in ordered],
                "sample_sds": [item["ratio_sample_sd"] for item in ordered],
            }
        )
    if len(forest) != 20 or len(pearson) != 20 or len(ratio_panels) != 5:
        raise ValueError("validated report did not yield the exact E2A plotting inventory")
    return {
        "forest": forest,
        "ratio_panels": ratio_panels,
        "pearson": pearson,
        "seeds": list(report["registered_inventory"]["seeds"]),
        "h2_verdict": None,
    }


def _manifest_path(row: object, field: str, *, what: str) -> Path:
    if type(row) is not dict:
        raise ValueError(f"{what} must be an exact source-manifest object")
    return R._manifest_project_path(row.get(field), what=f"{what} {field}")


def _manifest_identity(row: object, field: str, *, what: str) -> str:
    if type(row) is not dict:
        raise ValueError(f"{what} must be an exact source-manifest object")
    value = row.get(field)
    if type(value) is not str or not value:
        raise ValueError(f"{what} {field} must be a nonblank string")
    return value


def _relative_is(path: Path, root: Path, *parts: str) -> bool:
    try:
        return path.relative_to(root) == Path(*parts)
    except ValueError:
        return False


def _historical_pair_roots(
    source: Path,
    copy: Path,
    *,
    fit_id: str,
) -> tuple[Path, Path]:
    """Derive one historical original/copy root from its exact job suffix."""

    if _overlap(source, copy):
        raise ValueError("historical source and copy paths must be disjoint")
    if any(path.name != fit_id or path.parent.name != "jobs" for path in (source, copy)):
        raise ValueError(
            "historical fit source paths must end in jobs/<fit_id>"
        )
    shared = 0
    for left, right in zip(reversed(source.parts), reversed(copy.parts), strict=False):
        if left != right:
            break
        shared += 1
    suffix = source.parts[len(source.parts) - shared :]
    if (
        shared not in (2, 3)
        or suffix[-2:] != ("jobs", fit_id)
        or (shared == 3 and not suffix[0])
    ):
        raise ValueError(
            "historical source/copy paths do not expose one exact shared job suffix"
        )
    source_root = source
    copy_root = copy
    for _ in range(shared):
        source_root = source_root.parent
        copy_root = copy_root.parent
    if _overlap(source_root, copy_root):
        raise ValueError("historical execution and copy roots must be disjoint")
    if not (
        _relative_is(source, source_root, *suffix)
        and _relative_is(copy, copy_root, *suffix)
    ):
        raise ValueError("historical fit paths cannot be assigned to exact roots")
    return source_root, copy_root


def _immutable_authority_roots(
    report_path: Path,
    report: dict[str, Any],
) -> set[Path]:
    """Derive every complete immutable root without reopening scientific data.

    The strict report has two path grammars: finalized labels/fits live below
    ``<root>/<unit_id>/{label_evidence.json,sources/<fit_id>}``, while the 32
    historical-only diagnostic baselines end in ``jobs/<fit_id>`` with an
    optional shared batch directory.  Every recorded path must map to exactly
    one root; path drift is an integrity failure, never permission to infer a
    broader ancestor.
    """

    if type(report) is not dict:
        raise ValueError("figure report must be an exact object")
    manifests = report.get("source_manifests")
    if type(manifests) is not dict:
        raise ValueError("figure report lacks exact source manifests")
    collections: dict[str, list[dict[str, Any]]] = {}
    for key in (
        "baseline_diagnostics",
        "repair_validation_labels",
        "ordinary_labels",
    ):
        rows = manifests.get(key)
        if type(rows) is not list or any(type(row) is not dict for row in rows):
            raise ValueError(f"figure report source manifest {key} is malformed")
        collections[key] = rows

    label_rows = (
        collections["repair_validation_labels"]
        + collections["ordinary_labels"]
    )
    if not label_rows:
        raise ValueError("figure report has no finalized label source paths")

    finalized_sources: set[Path] = set()
    finalized_copies: set[Path] = set()
    recorded_paths: set[Path] = set()
    for row in label_rows:
        unit_id = _manifest_identity(row, "unit_id", what="label source row")
        source = _manifest_path(row, "source_path", what="label source row")
        copy = _manifest_path(row, "copy_path", what="label source row")
        if any(
            path.name != "label_evidence.json" or path.parent.name != unit_id
            for path in (source, copy)
        ):
            raise ValueError(
                "finalized label paths must be <authority>/<unit_id>/label_evidence.json"
            )
        finalized_sources.add(source.parents[1])
        finalized_copies.add(copy.parents[1])
        recorded_paths.update((source, copy))
    if len(finalized_sources) != 1 or len(finalized_copies) != 1:
        raise ValueError("label paths do not identify one exact finalized export/copy pair")
    finalized_source = next(iter(finalized_sources))
    finalized_copy = next(iter(finalized_copies))
    if _overlap(finalized_source, finalized_copy):
        raise ValueError("finalized export and copy roots must be disjoint")

    for row in label_rows:
        unit_id = _manifest_identity(row, "unit_id", what="label source row")
        refs = row.get("fit_sources")
        if type(refs) is not list:
            raise ValueError("label source row lacks exact fit_sources")
        for ref in refs:
            fit_id = _manifest_identity(ref, "fit_id", what="label fit source")
            source = _manifest_path(ref, "source_path", what="label fit source")
            copy = _manifest_path(ref, "copy_path", what="label fit source")
            if not (
                _relative_is(
                    source, finalized_source, unit_id, "sources", fit_id
                )
                and _relative_is(
                    copy, finalized_copy, unit_id, "sources", fit_id
                )
            ):
                raise ValueError(
                    "label fit path cannot be assigned to its exact finalized authority root"
                )
            recorded_paths.update((source, copy))

    historical_pairs: set[tuple[Path, Path]] = set()
    finalized_baselines = 0
    historical_baselines = 0
    for row in collections["baseline_diagnostics"]:
        unit_id = _manifest_identity(row, "unit_id", what="baseline source row")
        fit_id = _manifest_identity(row, "fit_id", what="baseline source row")
        source = _manifest_path(row, "source_path", what="baseline source row")
        copy = _manifest_path(row, "copy_path", what="baseline source row")
        source_is_finalized = _relative_is(
            source, finalized_source, unit_id, "sources", fit_id
        )
        copy_is_finalized = _relative_is(
            copy, finalized_copy, unit_id, "sources", fit_id
        )
        if source_is_finalized and copy_is_finalized:
            finalized_baselines += 1
        elif any(
            path == root or path.is_relative_to(root)
            for path in (source, copy)
            for root in (finalized_source, finalized_copy)
        ):
            raise ValueError(
                "baseline fit path is inside a finalized root but has a noncanonical layout"
            )
        else:
            historical_pairs.add(
                _historical_pair_roots(source, copy, fit_id=fit_id)
            )
            historical_baselines += 1
        recorded_paths.update((source, copy))
    if (finalized_baselines, historical_baselines) != (68, 32):
        raise ValueError(
            "baseline paths do not partition into exact 68 finalized/32 historical sources"
        )
    if not historical_pairs:
        raise ValueError("figure report exposes no historical execution/copy roots")

    historical_source_to_copy: dict[Path, Path] = {}
    historical_copy_to_source: dict[Path, Path] = {}
    for source_root, copy_root in historical_pairs:
        if (
            source_root in historical_source_to_copy
            and historical_source_to_copy[source_root] != copy_root
        ) or (
            copy_root in historical_copy_to_source
            and historical_copy_to_source[copy_root] != source_root
        ):
            raise ValueError("historical paths do not identify exact authority-root pairs")
        historical_source_to_copy[source_root] = copy_root
        historical_copy_to_source[copy_root] = source_root

    source_roots = {
        finalized_source,
        finalized_copy,
        *(root for pair in historical_pairs for root in pair),
    }
    for left, right in combinations(source_roots, 2):
        if _overlap(left, right):
            raise ValueError("scientific authority roots overlap and are ambiguous")
    for path in recorded_paths:
        matches = [
            root
            for root in source_roots
            if path != root and path.is_relative_to(root)
        ]
        if len(matches) != 1:
            raise ValueError(
                "recorded scientific source path cannot be assigned to one exact authority root"
            )

    report_root = report_path.parent
    for source_root in source_roots:
        if _overlap(report_root, source_root):
            raise ValueError("report and scientific authority roots must be disjoint")
    return {report_root, *source_roots}


def _matplotlib(cache: Path):
    import matplotlib

    for actual in (matplotlib.get_configdir(), matplotlib.get_cachedir()):
        if Path(actual).resolve() != cache:
            raise ValueError("matplotlib did not honour the explicit MPLCONFIGDIR")
    return matplotlib


def _png(figure, *, software: str) -> bytes:
    buffer = io.BytesIO()
    try:
        figure.savefig(
            buffer,
            format="png",
            dpi=140,
            metadata={"Software": software},
        )
        return buffer.getvalue()
    finally:
        figure.clear()
        buffer.close()


def _render_forest(rows: list[dict[str, Any]], cache: Path) -> bytes:
    matplotlib = _matplotlib(cache)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    style = {key: value for key, value in matplotlib.rcParamsDefault.items() if key != "backend"}
    with matplotlib.rc_context(style):
        figure = Figure(figsize=(13, 11), dpi=140)
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        y_positions = list(range(len(rows)))
        specifications = (
            ("data_repair", -0.18, "#1f77b4", "10x data repair"),
            ("feature_repair", 0.18, "#d62728", "feature restoration"),
        )
        for key, offset, color, legend in specifications:
            first = True
            for y, row in zip(y_positions, rows, strict=True):
                result = row[key]
                label = legend if first else None
                first = False
                if result["effect"] is None:
                    ax.scatter(
                        [0.0], [y + offset], marker="x", color=color,
                        s=35, label=label, zorder=3,
                    )
                    continue
                effect = result["effect"]
                low = result["ci_low"]
                high = result["ci_high"]
                ax.errorbar(
                    [effect], [y + offset],
                    xerr=[[effect - low], [high - effect]],
                    fmt="o" if result["passed"] else "s",
                    markersize=4.5,
                    markerfacecolor=color if result["passed"] else "white",
                    markeredgecolor=color,
                    ecolor=color,
                    elinewidth=1.1,
                    capsize=2,
                    label=label,
                    zorder=3,
                )
        ax.axvline(0.0, color="black", linewidth=0.9, linestyle="--")
        ax.set_yticks(y_positions, labels=[row["display_label"] for row in rows], fontsize=7.5)
        ax.invert_yaxis()
        ax.set_xlabel("paired repair effect (repaired - unrepaired); 95% interval")
        ax.set_title("Experiment 2A: repair effects for all 20 missing-feature units")
        ax.grid(axis="x", alpha=0.25)
        ax.legend(loc="best", title="Filled circle = accepted; square = not accepted; x = undefined")
        figure.text(
            0.5,
            0.015,
            "Observed labels are shown in row names. Effects are descriptive; no H2 verdict.",
            ha="center",
            fontsize=9,
        )
        figure.tight_layout(rect=(0, 0.035, 1, 1))
        return _png(
            figure,
            software=f"beyond-uncertainty Experiment-2A figures v{FIGURE_SCHEMA_VERSION}",
        )


def _render_ratio(panels: list[dict[str, Any]], cache: Path) -> bytes:
    matplotlib = _matplotlib(cache)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    style = {key: value for key, value in matplotlib.rcParamsDefault.items() if key != "backend"}
    with matplotlib.rc_context(style):
        figure = Figure(figsize=(14, 8.5), dpi=140)
        FigureCanvasAgg(figure)
        axes = figure.subplots(2, 3).ravel()
        for ax, panel in zip(axes, panels, strict=False):
            x = panel["confound_rates"]
            for seed, values in zip(panel["seeds"], panel["seed_lines"], strict=True):
                ax.plot(
                    x,
                    values,
                    marker="o",
                    markersize=3,
                    linewidth=1.0,
                    alpha=0.72,
                    label=f"seed {seed}",
                )
            ax.errorbar(
                x,
                panel["means"],
                yerr=panel["sample_sds"],
                color="black",
                marker="D",
                markersize=4,
                linewidth=1.5,
                capsize=3,
                label="mean +/- sample SD",
                zorder=5,
            )
            ax.set_xticks(x, labels=[f"{value:.2f}" for value in x])
            ax.set_ylim(bottom=0)
            ax.set_xlabel("confound rate")
            ax.set_ylabel("failure-set disagreement/error ratio")
            ax.set_title(f"{panel['causal_attribute']} causal / {panel['layout']}")
            ax.grid(alpha=0.25)
        axes[-1].set_axis_off()
        handles, labels = axes[0].get_legend_handles_labels()
        axes[-1].legend(handles, labels, loc="center", title="No pooled configuration curve")
        figure.suptitle("Experiment 2A: registered ratio by confound, all seed curves", fontsize=13)
        figure.text(
            0.5,
            0.025,
            "Five configurations remain separate. No absolute 'low' cutoff and no H2 verdict.",
            ha="center",
            fontsize=9.5,
        )
        figure.tight_layout(rect=(0, 0.06, 1, 0.95))
        return _png(
            figure,
            software=f"beyond-uncertainty Experiment-2A figures v{FIGURE_SCHEMA_VERSION}",
        )


def _render_pearson(rows: list[dict[str, Any]], seeds: list[int], cache: Path) -> bytes:
    matplotlib = _matplotlib(cache)
    import numpy as np
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    values = np.full((20, 5), np.nan, dtype=float)
    for row_index, row in enumerate(rows):
        for seed_index, value in enumerate(row["values"]):
            if value is not None:
                values[row_index, seed_index] = value
    style = {key: value for key, value in matplotlib.rcParamsDefault.items() if key != "backend"}
    with matplotlib.rc_context(style):
        figure = Figure(figsize=(10.5, 11), dpi=140)
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        colormap = matplotlib.colormaps["coolwarm"].with_extremes(bad="#d9d9d9")
        image = ax.imshow(
            np.ma.masked_invalid(values),
            aspect="auto",
            interpolation="nearest",
            cmap=colormap,
            vmin=-1,
            vmax=1,
        )
        for row_index in range(20):
            for seed_index in range(5):
                if not math.isfinite(values[row_index, seed_index]):
                    ax.text(seed_index, row_index, "x", ha="center", va="center", color="black", fontsize=9)
        ax.set_xticks(range(5), labels=[str(seed) for seed in seeds])
        ax.set_yticks(range(20), labels=[row["display_label"] for row in rows], fontsize=7.5)
        ax.set_xlabel("confirmatory seed")
        ax.set_ylabel("registered Experiment-2A unit")
        ax.set_title("Secondary/non-decisional Pearson correlation on the strict failure set")
        colorbar = figure.colorbar(image, ax=ax, fraction=0.035, pad=0.03)
        colorbar.set_label("Pearson r")
        figure.text(
            0.5,
            0.015,
            "Grey cells marked x are explicitly undefined. Correlations are not averaged or used for H2.",
            ha="center",
            fontsize=9,
        )
        figure.tight_layout(rect=(0, 0.035, 1, 1))
        return _png(
            figure,
            software=f"beyond-uncertainty Experiment-2A figures v{FIGURE_SCHEMA_VERSION}",
        )


def _existing_matches(path: Path, data: bytes) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise DurabilityError(f"cannot inspect figure destination {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise DurabilityError(f"figure destination must be an independent regular file: {path}")
    try:
        existing = path.read_bytes()
    except OSError as exc:
        raise DurabilityError(f"cannot read figure destination {path}: {exc}") from exc
    if existing != data:
        raise DivergentTargetError(f"{path} already exists with different content; refusing overwrite")


def prepare_experiment_2a_figures(
    report_path: Path,
    *,
    expected_report_sha256: str,
    figures_dir: str | Path,
) -> list[Path]:
    """Render three offline PNGs and publish their digest manifest last."""

    report, output, cache = _paths(report_path, figures_dir)
    document = R.load_experiment_2a_report(
        report, expected_sha256=expected_report_sha256
    )
    authorities = _immutable_authority_roots(report, document)
    if any(
        _overlap(destination, authority)
        for destination in (output, cache)
        for authority in authorities
    ):
        raise ValueError(
            "figure output and matplotlib cache must be disjoint from every immutable authority root"
        )
    plot_data = _plot_data(document)
    rendered = [
        (FOREST_FILE, "repair_effect_forest", _render_forest(plot_data["forest"], cache)),
        (RATIO_FILE, "ratio_by_confound", _render_ratio(plot_data["ratio_panels"], cache)),
        (
            PEARSON_FILE,
            "secondary_pearson_heatmap",
            _render_pearson(plot_data["pearson"], plot_data["seeds"], cache),
        ),
    ]
    manifest: dict[str, Any] = {
        "experiment_2a_figure_schema_version": FIGURE_SCHEMA_VERSION,
        "kind": "offline_experiment_2a_figures",
        "interpretation": _INTERPRETATION,
        "source_report_sha256": expected_report_sha256,
        "source_report_payload_sha256": document["payload_sha256"],
        "plot_data_sha256": _hash(plot_data),
        "unit_count": 20,
        "seed_count": 5,
        "figure_count": 3,
        "figures": [
            {"filename": filename, "kind": kind, "sha256": sha256_bytes(data)}
            for filename, kind, data in rendered
        ],
        "sign_consistency": None,
        "h2_verdict": None,
    }
    manifest["payload_sha256"] = _hash(manifest)
    manifest_bytes = (
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    for filename, _, data in rendered:
        _existing_matches(output / filename, data)
    _existing_matches(output / MANIFEST_FILE, manifest_bytes)
    written = [atomic_write_bytes(output / filename, data) for filename, _, data in rendered]
    written.append(atomic_write_json(output / MANIFEST_FILE, manifest))
    return written
