"""Regenerate every figure so far, from logs only (S§W5 Fri, P§13.7).

**One command, every figure, no compute.** P§13.7 requires that every figure in
the thesis be regenerable from logs together with the provenance that explains
them. This is that command. It reads the **immutable attempt directories** — it
never trains anything and never reads memory — so a figure can always be traced
back to the run records behind it.

**It fails loudly on a missing log.** "Every figure from logs only" means that
if a log a figure needs is absent, the right behaviour is to say so, not to
quietly produce a smaller set that looks complete. A reader who asked for every
figure and got four has no way to know a fifth was skipped.

**Each figure carries what it is.** The W3 curves are development-seed looks, not
H1 claims; the W4 figure is the certified reliability-gate result, and its title
says so, including the warning D-075 attaches to it — the zero-width intervals
are quantile discreteness, not zero uncertainty, so the figure does not draw
error bars that would imply a precision the exact bootstrap does not have.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import constants as K
from ..stats.gate import GATE_LAYOUTS, RungSpec, select_attempt
from . import w3_pilot


def _load_w3_rows(rows_path: Path) -> list[w3_pilot.PilotRow]:
    """Reconstruct PilotRow objects from a logged rows.json (fields match)."""
    raw = json.loads(rows_path.read_text())
    return [w3_pilot.PilotRow(**row) for row in raw]


def w3_pilot_figures(figures_dir: Path) -> list[Path]:
    """The two W3 development-seed curves, via the pilot's own figure code."""
    rows_path = Path("runs/w3_pilot/attempt-001/rows.json")
    if not rows_path.exists():
        raise FileNotFoundError(
            f"{rows_path} is not present, so the W3 pilot figures cannot be "
            "regenerated from logs. The pilot manifest and rows are tracked in git "
            "for exactly this reason (D-062); a checkout missing them is incomplete"
        )
    return w3_pilot.figures(_load_w3_rows(rows_path), out_dir=figures_dir)


def w4_gate_figure(figures_dir: Path) -> list[Path]:
    """The certified rung-0 trend: mean disagreement vs dataset size, per layout.

    Reads the immutable attempt for rung 0 chosen by its frozen spec hash, so the
    figure is of *that* evidence and not whatever attempt happens to sort last
    (`select_attempt` refuses to guess). No error bars: the exact paired
    bootstrap is discrete with two or three atoms, so a bar would imply a
    sampling precision the interval does not carry (D-075).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    spec = RungSpec.for_rung(0)
    root = Path("runs/w4_gate") / f"rung-{spec.rung:02d}-{spec.spec_hash}"
    if not root.exists():
        raise FileNotFoundError(
            f"{root} is not present, so the W4 gate figure cannot be regenerated. "
            "The rung-0 evidence is tracked in git (D-074); a checkout missing it "
            "cannot reproduce the certified result"
        )
    attempt = select_attempt(root)
    rows = json.loads((attempt / "rows.json").read_text())

    # Aggregate to one point per (layout, size): the across-seed mean, which is
    # the curve the trend test reads (D-068).
    sizes = list(K.DATA_SIZES)
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    for layout in GATE_LAYOUTS:
        means = []
        for n in sizes:
            vals = [
                r["uncertainty"]["mean_disagreement"]
                for r in rows
                if r["layout"] == layout and r["n_transitions"] == n
            ]
            if len(vals) != len(K.GATE_SEEDS):
                raise ValueError(
                    f"{layout} N={n}: found {len(vals)} seeds, expected "
                    f"{len(K.GATE_SEEDS)}. The figure is of the full registered grid "
                    "or it is not the certified result"
                )
            means.append(sum(vals) / len(vals))
        ax.plot(sizes, means, marker="o", label=layout)

    ax.set_xscale("log")
    ax.set_xlabel("training transitions (N)")
    ax.set_ylabel("mean pairwise disagreement")
    ax.set_title(
        "W4 reliability gate — rung 0 PASS (rho = -0.9429, all three)\n"
        "development seeds; disagreement is NOT monotone (peak at N=250)",
        fontsize=9,
    )
    ax.legend(title="configuration", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / "w4_gate_disagreement_vs_data.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return [path]


#: Every figure, keyed by a short name. Adding a cell that produces a figure
#: means adding it here, so "every figure" stays enumerable rather than being
#: whatever the thesis author remembers to run.
FIGURES = {
    "w3_pilot": w3_pilot_figures,
    "w4_gate": w4_gate_figure,
}


def main(figures_dir: str | Path = "figures") -> list[Path]:
    """Regenerate every registered figure. Returns the paths written."""
    figures_dir = Path(figures_dir)
    written: list[Path] = []
    for name, producer in FIGURES.items():
        paths = producer(figures_dir)
        for path in paths:
            print(f"  [{name}] wrote {path}")
            written.append(path)
    print(f"\n  {len(written)} figures regenerated from logs into {figures_dir}/")
    return written


if __name__ == "__main__":  # pragma: no cover
    main()
