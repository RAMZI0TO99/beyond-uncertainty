"""Source-reverified Experiment-1 visualisation: prepared, not auto-authorised.

This producer is deliberately absent from ``make_figures.FIGURES``. Only after
real-figure authorisation, with an absolute project-local MPLCONFIGDIR set BEFORE
Python imports matplotlib, the explicit Python invocation is::

    import json
    from pathlib import Path
    from bu.experiments.make_figures import experiment_1_figures
    sources = tuple(Path(p) for p in json.loads(
        Path("explicit-150-fit-paths.json").read_text(encoding="utf-8")))
    experiment_1_figures(
        Path("figures/experiment_1/attempt-001"), fit_directories=sources,
        expected_git_commit="<exact 40-hex execution commit>")

The JSON list names every fit directory; there is no discovery or default source
path. Keep TEMP/TMP and MPLCONFIGDIR project-local for this invocation. Sources
are reopened on EVERY call. Five configuration panels each show five seed lines
over all six sizes; there is no new normalisation, failure mask, seed/configuration
pooling, interval, trend test, hypothesis decision, or repair-label inference.

Two immutable PNGs and a versioned manifest bind every plotted scalar to source
path, fit identity/digests and commit. Validation, rendering and pre-existing
divergence checks finish before publication. Files use the durable exclusive
writers; the manifest is last. An I/O failure or concurrent publication may leave
a prefix of the PNGs; identical retries reverify sources and complete the set.
This is not claimed to be one atomic transaction across all three files.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import stat
import sys
from collections.abc import Sequence
from pathlib import Path

from .. import constants as K
from ..durable import (
    DivergentTargetError,
    DurabilityError,
    atomic_write_bytes,
    atomic_write_json,
    sha256_bytes,
)
from ..streams import confirmatory_seeds
from .experiment_1_evidence import (
    Experiment1Evidence,
    Experiment1Row,
    load_experiment_1_evidence,
)


# Bump when fields, plotted quantities, or their meaning change.
FIGURE_SCHEMA_VERSION = 1
MANIFEST_FILE = "experiment_1_figures.json"
_METRICS = (
    ("mean_error", "experiment_1_error_vs_data.png", "mean normalised movement error"),
    (
        "mean_disagreement", "experiment_1_disagreement_vs_data.png",
        "mean normalised pairwise disagreement",
    ),
)
_INTERPRETATION = (
    "Confirmatory data visualization only; not an H1 decision. "
    "Separate seed curves; no configuration pooling, trend test, interval, "
    "or repair-label inference."
)


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _paths(
    fit_directories: Sequence[Path], figures_dir: str | Path, commit: str
) -> tuple[tuple[Path, ...], Path, Path]:
    if type(commit) is not str or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("expected_git_commit must be an exact lowercase 40-hex commit")
    if (
        not isinstance(fit_directories, Sequence)
        or isinstance(fit_directories, (str, bytes))
        or len(fit_directories) != 150
        or any(not isinstance(path, Path) for path in fit_directories)
    ):
        raise ValueError("supply exactly 150 explicit fit directory Path objects, not rows")
    sources = tuple(path.resolve() for path in fit_directories)
    if len(set(sources)) != 150:
        raise ValueError("duplicate resolved fit directories")
    if not isinstance(figures_dir, (str, Path)) or not str(figures_dir).strip():
        raise ValueError("figures_dir must be an explicit output directory")
    output = Path(figures_dir).resolve()
    configured = os.environ.get("MPLCONFIGDIR")
    if not configured or not Path(configured).is_absolute():
        raise ValueError("set MPLCONFIGDIR to an explicit absolute project-local directory")
    cache = Path(configured).resolve()
    for destination in (output, cache):
        if any(_overlap(destination, source) for source in sources):
            raise ValueError("figure/cache output must not overlap an evidence directory")
        if destination.exists() and not destination.is_dir():
            raise ValueError(f"output/cache path is not a directory: {destination}")
    # A prior import can cache an outside location despite a later env change.
    matplotlib = sys.modules.get("matplotlib")
    if matplotlib is not None:
        for actual in (matplotlib.get_configdir(), matplotlib.get_cachedir()):
            if Path(actual).resolve() != cache:
                raise ValueError("set MPLCONFIGDIR before importing matplotlib")
    return sources, output, cache


def _rows(
    evidence: Experiment1Evidence, sources: tuple[Path, ...], commit: str
) -> tuple[Experiment1Row, ...]:
    """Consumer shape guards; never a replacement for the source loader."""
    if type(evidence) is not Experiment1Evidence or evidence.expected_git_commit != commit:
        raise ValueError("loader must return Experiment1Evidence bound to the exact commit")
    groups = evidence.comparison_group_ids
    seeds = tuple(confirmatory_seeds(K.SEEDS_HYPOTHESIS))
    sizes = tuple(K.DATA_SIZES)
    if (
        type(groups) is not tuple or len(groups) != 5
        or any(type(group) is not str or not group for group in groups)
        or len(set(groups)) != 5
        or evidence.seeds != seeds or evidence.data_sizes != sizes
        or len(seeds) != 5 or len(sizes) != 6
        or type(evidence.rows) is not tuple or len(evidence.rows) != 150
    ):
        raise ValueError("loader must return the complete five-configuration, five-seed grid")
    cells: set[tuple[str, int, int]] = set()
    paths: set[Path] = set()
    configurations: dict[str, tuple[str, str]] = {}
    for row in evidence.rows:
        if type(row) is not Experiment1Row:
            raise ValueError("loader rows must be exact Experiment1Row objects")
        if (
            type(row.seed) is not int or type(row.n_transitions) is not int
            or row.seed not in seeds or row.n_transitions not in sizes
            or row.comparison_group_id not in groups
        ):
            raise ValueError("unregistered configuration/seed/size in figure input")
        cell = (row.comparison_group_id, row.seed, row.n_transitions)
        if cell in cells:
            raise ValueError("duplicate configuration/seed/size in figure input")
        cells.add(cell)
        if not isinstance(row.source_path, Path):
            raise ValueError("row must identify a source Path")
        path = row.source_path.resolve()
        if path not in sources or path in paths:
            raise ValueError("figure rows must bind one-to-one to the requested source paths")
        paths.add(path)
        for field in ("execution_digest", "evaluation_pool_digest"):
            value = getattr(row, field)
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError(f"invalid source {field}")
        for field in ("causal_attribute", "layout", "fit_id", "unit_id", "config_id"):
            if type(getattr(row, field)) is not str or not getattr(row, field):
                raise ValueError(f"missing source identity {field}")
        configuration = (row.causal_attribute, row.layout)
        if configurations.setdefault(row.comparison_group_id, configuration) != configuration:
            raise ValueError("configuration metadata varies across a panel")
        for metric, _, _ in _METRICS:
            value = getattr(row, metric)
            if type(value) is not float or not math.isfinite(value) or value < 0:
                raise ValueError(f"{metric} must be a finite nonnegative verified float")
    expected = {(group, seed, size) for group in groups for seed in seeds for size in sizes}
    if cells != expected or paths != set(sources):
        raise ValueError("figure grid or source inventory is incomplete")
    return tuple(sorted(evidence.rows, key=lambda row: (
        row.comparison_group_id, row.seed, row.n_transitions
    )))


def _render_png(
    rows: tuple[Experiment1Row, ...], metric: str, ylabel: str, cache: Path
) -> bytes:
    """Render to memory with explicit local cache, deterministic style and Agg."""
    import matplotlib

    for actual in (matplotlib.get_configdir(), matplotlib.get_cachedir()):
        if Path(actual).resolve() != cache:
            raise ValueError("matplotlib did not honour the explicit MPLCONFIGDIR")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    # Ignore ambient styles and usetex/external helpers; no pyplot state.
    style = {key: value for key, value in matplotlib.rcParamsDefault.items() if key != "backend"}
    with matplotlib.rc_context(style):
        figure = Figure(figsize=(13, 8), dpi=140)
        FigureCanvasAgg(figure)
        axes = figure.subplots(2, 3).ravel()
        groups = sorted({row.comparison_group_id for row in rows})
        seeds = tuple(confirmatory_seeds(K.SEEDS_HYPOTHESIS))
        sizes = tuple(K.DATA_SIZES)
        for ax, group in zip(axes, groups):
            panel = [row for row in rows if row.comparison_group_id == group]
            by_cell = {(row.seed, row.n_transitions): row for row in panel}
            for seed in seeds:
                ax.plot(
                    sizes, [getattr(by_cell[seed, size], metric) for size in sizes],
                    marker="o", markersize=3, linewidth=1.2, label=f"seed {seed}",
                )
            ax.set_xscale("log")
            ax.set_xticks(sizes, labels=[str(size) for size in sizes], fontsize=8)
            ax.set_xlabel("training transitions (N)", fontsize=9)
            ax.set_ylabel(ylabel, fontsize=9)
            ax.set_ylim(bottom=0)
            ax.set_title(
                f"{panel[0].causal_attribute} causal / {panel[0].layout}\n{group}", fontsize=10
            )
            ax.grid(alpha=0.25)
        axes[-1].set_axis_off()
        handles, labels = axes[0].get_legend_handles_labels()
        axes[-1].legend(handles, labels, loc="center", title="Separate seed curves")
        figure.suptitle(f"Experiment 1: {ylabel} vs N", fontsize=13)
        figure.text(
            0.5, 0.025,
            "Confirmatory data visualization only - not an H1 decision.\n"
            "Five configurations kept separate; no pooled curve, interval, or trend test.",
            ha="center", fontsize=10,
        )
        figure.tight_layout(rect=(0, 0.08, 1, 0.94))
        buffer = io.BytesIO()
        try:
            figure.savefig(
                buffer, format="png", dpi=140,
                metadata={"Software": f"beyond-uncertainty Experiment-1 figures v{FIGURE_SCHEMA_VERSION}"},
            )
            return buffer.getvalue()
        finally:
            figure.clear()
            buffer.close()


def _existing_matches(path: Path, data: bytes) -> None:
    """Preflight EVERY destination before publishing the first artifact."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise DurabilityError(f"figure destination must be an independent regular file: {path}")
    if path.read_bytes() != data:
        raise DivergentTargetError(f"{path} already exists with different content; refusing overwrite")


def prepare_experiment_1_figures(
    fit_directories: Sequence[Path], *, expected_git_commit: str, figures_dir: str | Path
) -> list[Path]:
    """Reopen all sources each call; return two immutable PNGs and manifest last.

    Validation finishes before rendering/publication. Every pre-existing target
    is compared before any missing target is created. Atomic writers also refuse
    racing divergent targets. Sources are never replaced by cached/handmade rows.
    """
    sources, output, cache = _paths(fit_directories, figures_dir, expected_git_commit)
    evidence = load_experiment_1_evidence(sources, expected_git_commit=expected_git_commit)
    rows = _rows(evidence, sources, expected_git_commit)
    images = [
        (filename, metric, _render_png(rows, metric, ylabel, cache))
        for metric, filename, ylabel in _METRICS
    ]
    document = {
        "schema_version": FIGURE_SCHEMA_VERSION,
        "experiment": "exp1",
        "interpretation": _INTERPRETATION,
        "expected_git_commit": expected_git_commit,
        "comparison_group_ids": sorted(evidence.comparison_group_ids),
        "seeds": list(evidence.seeds),
        "data_sizes": list(evidence.data_sizes),
        "point_estimand": "equal-movement-row mean of verified normalised whole-pool values per fit",
        "aggregation": "none across seeds or configurations; one six-size line per seed per panel",
        "figures": [
            {"filename": filename, "metric": metric, "sha256": sha256_bytes(data)}
            for filename, metric, data in images
        ],
        "rows": [
            {
                "comparison_group_id": row.comparison_group_id,
                "causal_attribute": row.causal_attribute,
                "layout": row.layout,
                "seed": row.seed,
                "n_transitions": row.n_transitions,
                "unit_id": row.unit_id,
                "config_id": row.config_id,
                "fit_id": row.fit_id,
                "source_path": str(row.source_path.resolve()),
                "execution_digest": row.execution_digest,
                "evaluation_pool_digest": row.evaluation_pool_digest,
                "expected_git_commit": expected_git_commit,
                "mean_error": row.mean_error,
                "mean_disagreement": row.mean_disagreement,
            }
            for row in rows
        ],
    }
    manifest_bytes = (json.dumps(
        document, indent=2, sort_keys=True, allow_nan=False, ensure_ascii=False
    ) + "\n").encode("utf-8")
    for filename, _, data in images:
        _existing_matches(output / filename, data)
    _existing_matches(output / MANIFEST_FILE, manifest_bytes)
    written = [atomic_write_bytes(output / filename, data) for filename, _, data in images]
    written.append(atomic_write_json(output / MANIFEST_FILE, document))
    return written
