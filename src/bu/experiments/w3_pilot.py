"""Week 3 Friday: the exploratory data-size sweep.

*"Mean pairwise disagreement and predictive variance, exported per transition.
Exploratory data-size sweep at one configuration (100 / 250 / 500 / 1000 / 2500
/ 5000, three seeds) and plot both curves. Three seeds is correct here — this is
a look, not an H1 claim."*

The schedule's last sentence is the load-bearing one and is repeated in every
output this module produces. Three seeds cannot support H1; H1 needs five, the
preregistered trend test (W4 Mon), and confirmatory seeds. What this cell is for
is seeing the shape of the curves before any formal test is run on them, so that
W3 Saturday's paragraph is written from data rather than from expectation.

Everything here runs on **development seeds** (< ``CONFIRMATORY_SEED_BASE``) and
is permanently excluded from confirmatory results, threshold calibration, repair
acceptance and the critic (D-034). Sol approved exactly this scope.

Metrics come from the **fixed evaluation pool** (D-052), which no early stopping
or checkpoint selection ever touched.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch

from .. import constants as K
from ..config import TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..models.ensemble import train_ensemble
from ..models.uncertainty import UncertaintySummary, across_seeds, summarise
from ..models.world_model import activation_report, primary_error

#: One configuration, as the schedule specifies. The reference configuration
#: (D-025), so the pilot looks at the conditions the ladder will later validate.
PILOT_CAUSAL, PILOT_LAYOUT = "shape", "uniform"

#: Development seeds. Not confirmatory, deliberately and permanently (D-034).
PILOT_SEEDS = (0, 1, 2)


@dataclass
class PilotRow:
    n_transitions: int
    seed: int
    uncertainty: dict
    val_position_errors: list[float]
    activation: dict
    epochs: list[int]


def run(
    *,
    sizes: tuple[int, ...] = K.DATA_SIZES,
    seeds: tuple[int, ...] = PILOT_SEEDS,
    hidden_size: int = 256,
    threads: int = 4,
    out_dir: str | Path = "runs/w3_pilot",
    verbose: bool = True,
) -> list[PilotRow]:
    """Fit ``len(sizes) * len(seeds)`` ensembles and export the curves."""
    torch.set_num_threads(threads)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows: list[PilotRow] = []
    for n in sizes:
        for seed in seeds:
            assert seed < K.CONFIRMATORY_SEED_BASE, "the pilot is development-only"
            unit = UnitSpec(
                causal_attribute=PILOT_CAUSAL,
                layout=PILOT_LAYOUT,
                confound_rate=0.0,
                family="estimation",
                n_transitions=n,
                hidden_size=hidden_size,
            )
            pools = collect_pools(unit, stage="exp1", seed=seed)
            ensemble = train_ensemble(
                unit, pools, TrainConfig(), stage="exp1", seed=seed
            )

            obs = torch.as_tensor(pools.evaluation.obs)
            action = torch.as_tensor(pools.evaluation.action)
            next_obs = torch.as_tensor(pools.evaluation.next_obs)

            # Movement transitions only -- the primary error's domain (DEV-007).
            from ..models.world_model import MOVEMENT_ACTIONS

            move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
            members = ensemble.member_predictions(obs[move], action[move])
            targets = ensemble.members[0].targets(next_obs[move])[0]

            summary = summarise(members, targets, n_transitions=n, seed=seed)
            report = activation_report(ensemble.members[0], obs, action, next_obs)

            rows.append(
                PilotRow(
                    n_transitions=n,
                    seed=seed,
                    uncertainty=summary.as_row(),
                    val_position_errors=list(ensemble.val_position_errors),
                    activation=asdict(report),
                    epochs=[r.epochs_run for r in ensemble.results],
                )
            )
            if verbose:
                print(
                    f"  n={n:<5} seed={seed}  err={summary.mean_error:.4f}  "
                    f"disagreement={summary.mean_disagreement:.4f}  "
                    f"ratio={summary.ratio:.4f}  epochs={rows[-1].epochs}"
                )

    (out / "rows.json").write_text(
        json.dumps([asdict(r) for r in rows], indent=2), encoding="utf-8"
    )
    return rows


def curves(rows: list[PilotRow], sizes: tuple[int, ...] = K.DATA_SIZES) -> dict:
    """Aggregate to one point per dataset size, across seeds."""
    out = {}
    for n in sizes:
        seeds = [
            UncertaintySummary(**r.uncertainty) for r in rows if r.n_transitions == n
        ]
        if seeds:
            out[n] = across_seeds(seeds)
    return out


def report(rows: list[PilotRow]) -> str:
    """The printed summary. Carries the schedule's caveat in its own text."""
    aggregated = curves(rows)
    lines = [
        "WEEK 3 FRIDAY -- EXPLORATORY DATA-SIZE SWEEP",
        "=" * 68,
        f"configuration: {PILOT_CAUSAL}-causal, {PILOT_LAYOUT} layout, confound 0.0",
        f"seeds: {PILOT_SEEDS} (DEVELOPMENT -- excluded from every confirmatory result)",
        "metrics on the fixed evaluation pool; movement transitions only",
        "",
        "*** THIS IS A LOOK, NOT AN H1 CLAIM. Three seeds cannot support one. ***",
        "",
        f"{'N':>6} {'error':>18} {'disagreement':>18} {'pred. variance':>18} {'ratio':>16}",
        "-" * 68,
    ]
    for n, agg in aggregated.items():
        lines.append(
            f"{n:>6} "
            f"{agg['mean_error_mean']:>9.4f}±{agg['mean_error_sd']:<8.4f}"
            f"{agg['mean_disagreement_mean']:>9.4f}±{agg['mean_disagreement_sd']:<8.4f}"
            f"{agg['mean_predictive_variance_mean']:>9.4f}±{agg['mean_predictive_variance_sd']:<8.4f}"
            f"{agg['ratio_mean']:>8.4f}±{agg['ratio_sd']:<7.4f}"
        )

    errors = [aggregated[n]["mean_error_mean"] for n in aggregated]
    dis = [aggregated[n]["mean_disagreement_mean"] for n in aggregated]
    lines += [
        "",
        "Monotonicity, reported as description rather than as a test:",
        f"  error decreasing in N:        {all(a >= b for a, b in zip(errors, errors[1:]))}",
        f"  disagreement decreasing in N: {all(a >= b for a, b in zip(dis, dis[1:]))}",
        "  (W4 Mon's rank-correlation trend test is the actual instrument.)",
    ]
    return "\n".join(lines)


def figures(rows: list[PilotRow], out_dir: str | Path = "figures") -> list[Path]:
    """Two curves, regenerated from the logged rows rather than from memory."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    aggregated = curves(rows)
    sizes = list(aggregated)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []

    for key, label, filename in [
        ("mean_error", "held-out error (per-dimension normalised)", "w3_error_vs_data.png"),
        ("mean_disagreement", "mean pairwise disagreement", "w3_disagreement_vs_data.png"),
    ]:
        means = [aggregated[n][f"{key}_mean"] for n in sizes]
        sds = [aggregated[n][f"{key}_sd"] for n in sizes]
        fig, ax = plt.subplots(figsize=(5.5, 3.6))
        ax.errorbar(sizes, means, yerr=sds, marker="o", capsize=3)
        ax.set_xscale("log")
        ax.set_xlabel("training transitions (N)")
        ax.set_ylabel(label)
        ax.set_title(f"{label} vs dataset size\ndevelopment seeds — a look, not an H1 claim",
                     fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        path = out / filename
        fig.savefig(path, dpi=140)
        plt.close(fig)
        written.append(path)
    return written


if __name__ == "__main__":  # pragma: no cover
    rows = run()
    print()
    print(report(rows))
    print()
    for path in figures(rows):
        print(f"  wrote {path}")
