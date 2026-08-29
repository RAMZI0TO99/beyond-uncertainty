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

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch

from .. import constants as K
from ..config import Config, TrainConfig, UnitSpec
from ..metrics import RunLogger
from ..runrecord import GitState, git_state, package_versions
from ..env.collect import collect_pools
from ..models.ensemble import train_ensemble
from ..models.uncertainty import (
    NormalisationScale, UncertaintySummary, across_seeds, per_transition_table,
    spread_diagnostic, summarise,
)
from ..models.world_model import MOVEMENT_ACTIONS, activation_report

#: One configuration, as the schedule specifies. The reference configuration
#: (D-025), so the pilot looks at the conditions the ladder will later validate.
PILOT_CAUSAL, PILOT_LAYOUT = "shape", "uniform"

#: Development seeds. Not confirmatory, deliberately and permanently (D-034).
PILOT_SEEDS = (0, 1, 2)

#: Each execution writes into its own ``attempt-NNN`` directory and never into
#: an existing one (D-062).
ATTEMPT_PREFIX = "attempt-"
#: Bump when the manifest's field set changes, so a reader can tell which
#: contract an old attempt was written under.
MANIFEST_VERSION = 1


@dataclass
class PilotRow:
    n_transitions: int
    seed: int
    uncertainty: dict
    val_position_errors: list[float]
    activation: dict
    spread: dict
    epochs: list[int]
    #: Which run record these numbers came from, so a row in ``rows.json`` can
    #: be joined to its provenance without matching on (size, seed) by eye.
    run_id: str = ""
    config_id: str = ""
    unit_id: str = ""


@dataclass
class PilotAttempt:
    """One execution of the pilot, and the immutable directory it wrote."""

    rows: list[PilotRow]
    attempt_dir: Path
    manifest: dict = field(default_factory=dict)


def new_attempt_dir(out_dir: str | Path) -> Path:
    """Create the next unused ``attempt-NNN`` under ``out_dir``, or fail.

    **Why not just reuse the directory** (D-062). Sol's finding: the pilot's
    outputs are a mix of append-only and overwrite. Metric streams are appended,
    while ``rows.json``, the figures and the transition exports are overwritten,
    so one directory could end up holding a summary describing one execution
    beside run records and exports from another — with nothing marking which was
    which. Reproduced: a rerun at a *different* set of sizes left two run records
    and two exports on disk while ``rows.json`` described only the second.

    ``mkdir`` without ``exist_ok`` is the guard: it is atomic, so two processes
    racing for the same number cannot both win, and an attempt directory is
    never opened twice by construction.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    used = [
        int(p.name[len(ATTEMPT_PREFIX):])
        for p in out.glob(f"{ATTEMPT_PREFIX}*")
        if p.is_dir() and p.name[len(ATTEMPT_PREFIX):].isdigit()
    ]
    attempt = out / f"{ATTEMPT_PREFIX}{max(used, default=0) + 1:03d}"
    attempt.mkdir()  # deliberately not exist_ok
    return attempt


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    *,
    sizes: tuple[int, ...] = K.DATA_SIZES,
    seeds: tuple[int, ...] = PILOT_SEEDS,
    hidden_size: int = 256,
    threads: int = 4,
    out_dir: str | Path = "runs/w3_pilot",
    verbose: bool = True,
) -> PilotAttempt:
    """Fit ``len(sizes) * len(seeds)`` ensembles and export the curves.

    Writes into a fresh ``attempt-NNN`` directory under ``out_dir`` and never
    into an existing one, so a rerun can neither append to another execution's
    metric stream nor overwrite its exports (D-062). Every artefact is listed in
    ``manifest.json`` with its digest and the provenance needed to check it.
    """
    torch.set_num_threads(threads)
    # Captured before anything is written. `git status --porcelain` counts
    # untracked files, and this attempt's own compact artefacts are tracked by
    # exception (D-062) -- so reading the git state at the *end* would report
    # the tree as dirty because of the run's own output, and every attempt would
    # permanently disclaim its own commit.
    git = git_state()
    attempt = new_attempt_dir(out_dir)
    out = attempt

    # One scale per evaluation pool, computed before anything is masked, reused
    # across every dataset size and member that shares the pool (D-061). Keyed by
    # seed because that is what the evaluation pool varies with -- D-052 fixes it
    # across sizes and arms -- and the equality check below is the proof of that
    # rather than a restatement of it.
    scales: dict[int, NormalisationScale] = {}
    artifacts: list[dict] = []

    rows: list[PilotRow] = []
    for n in sizes:
        for seed in seeds:
            if seed >= K.CONFIRMATORY_SEED_BASE:
                # A ValueError, not an assert: assertions vanish under -O, so
                # they are not a safety boundary (D-059).
                raise ValueError(
                    f"seed {seed} is confirmatory; this pilot is development-only "
                    f"(< {K.CONFIRMATORY_SEED_BASE}, D-034)"
                )
            unit = UnitSpec(
                causal_attribute=PILOT_CAUSAL,
                layout=PILOT_LAYOUT,
                confound_rate=0.0,
                family="estimation",
                n_transitions=n,
                hidden_size=hidden_size,
            )
            pools = collect_pools(unit, stage="exp1", seed=seed)
            # Through RunLogger, so the run record carries the commit, the dirty
            # flag, the package versions and the seed partition (W3-2). P§13.7
            # requires every figure to be regenerable from logs *with* the
            # provenance that explains them; the first version of this pilot
            # wrote bare JSON and had none of it.
            config = Config(unit=unit, seed=seed, stage="exp1")
            with RunLogger.start(config, root=out / "records") as logger:
                ensemble = train_ensemble(
                    unit, pools, TrainConfig(), stage="exp1", seed=seed, logger=logger
                )

            obs = torch.as_tensor(pools.evaluation.obs)
            action = torch.as_tensor(pools.evaluation.action)
            next_obs = torch.as_tensor(pools.evaluation.next_obs)

            # Movement transitions only -- the primary error's domain (DEV-007).
            move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
            members = ensemble.member_predictions(obs[move], action[move])
            targets = ensemble.members[0].targets(next_obs[move])[0]

            # D-061. The scale comes from the FULL movement evaluation pool,
            # before any failure mask, and is then reused verbatim. Here the
            # scored set *is* the pool -- the failure mask arrives at W4 Fri --
            # so this pins the current numbers rather than changing them.
            scale = NormalisationScale.from_evaluation_pool(targets)
            if seed in scales:
                if not torch.equal(scales[seed].vector, scale.vector):
                    raise RuntimeError(
                        f"the evaluation pool's scale moved between dataset sizes "
                        f"at seed {seed}: {scales[seed].vector.tolist()} then "
                        f"{scale.vector.tolist()}. D-052 fixes the evaluation pool "
                        "across sizes, so this means it is no longer fixed and "
                        "every cross-size comparison is in different units."
                    )
                scale = scales[seed]
            else:
                scales[seed] = scale

            summary = summarise(members, targets, n_transitions=n, seed=seed, scale=scale)
            spread = spread_diagnostic(members, targets)
            # Across every member, not member 0 (W3-3). D-047's conditional is
            # about the detached head in general, and one member of five could
            # be the best or the worst of them.
            reports = [
                activation_report(model, obs, action, next_obs)
                for model in ensemble.members
            ]
            report = _activation_slices(reports)

            # The schedule requires PER-TRANSITION export; summaries are derived
            # from it, never the other way round (D-059).
            table = per_transition_table(
                members, targets,
                episode=pools.evaluation.episode[move.numpy()],
                step=pools.evaluation.step[move.numpy()],
                scale=scale,
            )
            export = out / f"transitions_n{n}_seed{seed}.npz"
            np.savez_compressed(export, **table)

            rows.append(
                PilotRow(
                    n_transitions=n,
                    seed=seed,
                    uncertainty=summary.as_row(),
                    val_position_errors=list(ensemble.val_position_errors),
                    activation=report,
                    spread=spread.as_row(),
                    epochs=[r.epochs_run for r in ensemble.results],
                    run_id=config.run_id,
                    config_id=config.config_id,
                    unit_id=config.unit_id,
                )
            )
            artifacts.append(
                {
                    "path": export.name,
                    "kind": "per_transition_export",
                    "sha256": _sha256(export),
                    "bytes": export.stat().st_size,
                    "run_id": config.run_id,
                    "config_id": config.config_id,
                    "unit_id": config.unit_id,
                    "seed": seed,
                    "n_transitions": n,
                    "n_rows": int(len(table["error"])),
                    **scale.as_row(),
                }
            )
            if verbose:
                print(
                    f"  n={n:<5} seed={seed}  err={summary.mean_error:.4f}  "
                    f"disagreement={summary.mean_disagreement:.4f}  "
                    f"ratio={summary.ratio:.4f}  epochs={rows[-1].epochs}"
                )

    rows_path = out / "rows.json"
    rows_path.write_text(
        json.dumps([asdict(r) for r in rows], indent=2), encoding="utf-8"
    )
    artifacts.append(
        {
            "path": rows_path.name,
            "kind": "summary",
            "sha256": _sha256(rows_path),
            "bytes": rows_path.stat().st_size,
            "n_rows": len(rows),
        }
    )

    for path in figures(rows, out_dir=out):
        artifacts.append(
            {
                "path": path.name,
                "kind": "figure",
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "regenerable_from": rows_path.name,
            }
        )

    manifest = write_manifest(
        out,
        git=git,
        artifacts=artifacts,
        rows=rows,
        scales=scales,
        parameters={
            "sizes": list(sizes),
            "seeds": list(seeds),
            "hidden_size": hidden_size,
            "causal_attribute": PILOT_CAUSAL,
            "layout": PILOT_LAYOUT,
            "confound_rate": 0.0,
            "ensemble_size": TrainConfig().ensemble_size,
        },
    )
    if verbose:
        print(f"\n  attempt {out.name}: {manifest['n_runs']} run records, "
              f"{manifest['n_member_records']} member records, "
              f"{len(artifacts)} artefacts manifested")
    return PilotAttempt(rows=rows, attempt_dir=out, manifest=manifest)


def write_manifest(
    attempt_dir: str | Path,
    *,
    git: GitState | None = None,
    artifacts: list[dict],
    rows: list[PilotRow],
    scales: dict[int, NormalisationScale],
    parameters: dict,
) -> dict:
    """The evidence manifest: what was written, and what explains it (D-062).

    P§13.7 requires every figure to be regenerable from logs *with* the
    provenance that explains them. The run records already carry commit, dirty
    flag, package versions and seed partition per run; this ties the derived
    artefacts -- summaries, figures, transition exports -- to those runs, so a
    reviewer can check the claimed run and member counts against the directory
    instead of taking them from a delta.

    Digests are recorded because "immutable" has to be checkable: an attempt
    directory is never reopened by this module, and the manifest is how someone
    else confirms nothing else reopened it either.
    """
    attempt = Path(attempt_dir)
    records = sorted(p for p in (attempt / "records").glob("*/run.json"))
    member_records = 0
    for record in records:
        metrics = record.parent / "metrics.jsonl"
        if metrics.exists():
            member_records += sum(
                1 for line in metrics.read_text().splitlines() if line.strip()
            )

    git = git or git_state()
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "attempt": attempt.name,
        "cell": "W3 Fri -- exploratory data-size sweep",
        "seed_partition": "development",
        "commit": git.commit,
        "dirty": git.dirty,
        "branch": git.branch,
        "packages": package_versions(),
        "parameters": parameters,
        "n_runs": len(records),
        "n_member_records": member_records,
        "normalisation": {
            str(seed): scale.as_row() for seed, scale in sorted(scales.items())
        },
        "runs": [
            {
                "run_id": r.run_id,
                "config_id": r.config_id,
                "unit_id": r.unit_id,
                "seed": r.seed,
                "n_transitions": r.n_transitions,
            }
            for r in rows
        ],
        "artifacts": artifacts,
    }
    path = attempt / "manifest.json"
    if path.exists():
        raise FileExistsError(f"{path} already exists; attempts are written once")
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _activation_slices(reports: list) -> dict:
    """All four views of the auxiliary task, per member and aggregate (D-063).

    Sol asked for the four rather than the combined interaction slice alone:
    changed transitions, interaction transitions with no change, all interaction
    transitions, and the copy-current-activation baseline. The baseline is
    reported per slice, and it is **model-independent** — it reads the current
    bit and nothing else — so it is one number per condition rather than per
    member.

    The conclusion this feeds is deliberately narrow: the detached head did not
    reliably beat copying, and it is retained as a **non-decisional diagnostic**.
    It is not evidence about H1 or H2, which are claims about position error and
    disagreement (D-032, DEV-007).
    """
    def per_member(attr: str) -> list[float]:
        return [float(getattr(r, attr)) for r in reports]

    def mean(attr: str) -> float:
        return float(np.mean(per_member(attr)))

    slices = {
        "all_interact": "error_interact",
        "changed": "error_changed",
        "unchanged": "error_interact_unchanged",
    }
    out: dict = {
        "n_interact": reports[0].n_interact,
        "n_changed": reports[0].n_changed,
        "n_unchanged": reports[0].n_interact - reports[0].n_changed,
        "copy_baseline": {
            "all_interact": reports[0].copy_baseline_interact,
            "changed": reports[0].copy_baseline_changed,
            "unchanged": reports[0].copy_baseline_unchanged,
        },
        "copy_baseline_is_model_independent": True,
    }
    for name, attr in slices.items():
        out[f"error_{name}_per_member"] = per_member(attr)
        out[f"error_{name}_mean"] = mean(attr)
    baseline = reports[0].copy_baseline_interact
    out["beats_copy_baseline"] = bool(mean("error_interact") < baseline)
    out["members_beating_copy_baseline"] = int(
        sum(1 for v in per_member("error_interact") if v < baseline)
    )
    # Retained for readers of the older rows.json schema.
    out["error_interact_per_member"] = per_member("error_interact")
    out["error_changed_per_member"] = per_member("error_changed")
    out["error_interact_mean"] = mean("error_interact")
    out["copy_baseline_interact"] = baseline
    return out


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
        "*** ratio* is an EXPLORATORY WHOLE-POOL disagreement/error ratio over all",
        "    movement transitions. It is NOT the registered H2 endpoint, which is",
        "    defined over the FAILURE SET (P10.1/10.3) and needs the W4 Fri",
        "    threshold that does not exist yet (D-059). ***",
        "",
        f"{'N':>6} {'error':>18} {'disagreement':>18} {'pred. variance':>18} {'ratio*':>16}",
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

    # Paired per-seed differences, because three seeds cannot carry an
    # inferential claim and "the sd is smaller than the gap" is not one (D-059).
    lines += ["", "Disagreement, paired within seed (N=250 minus N=100):"]
    for seed in sorted({r.seed for r in rows}):
        small = next((r for r in rows if r.n_transitions == 100 and r.seed == seed), None)
        larger = next((r for r in rows if r.n_transitions == 250 and r.seed == seed), None)
        if small and larger:
            delta = (larger.uncertainty["mean_disagreement"]
                     - small.uncertainty["mean_disagreement"])
            lines.append(f"  seed {seed}: {delta:+.4f}")
    lines.append("  Direction reproduced across all three development seeds if all "
                 "three are positive. That is the whole claim.")

    lines += ["", "Member-level spread as a fraction of the targets' (D-059):",
              f"{'N':>6} {'ensemble mean':>14} {'min member':>12} {'max member':>12}"]
    for n in sorted({r.n_transitions for r in rows}):
        rs = [r for r in rows if r.n_transitions == n]
        em = np.mean([r.spread["ensemble_mean_sd"] / max(r.spread["target_sd"], 1e-6) for r in rs])
        ratios = [x for r in rs for x in r.spread["member_sd_ratios"]]
        lines.append(f"{n:>6} {em:>14.3f} {min(ratios):>12.3f} {max(ratios):>12.3f}")
    lines.append("  A collapse claim needs EVERY member small, not just their mean.")

    # All four auxiliary views, each against its own baseline (D-063). The
    # decision they support is that the detached head stays as a diagnostic and
    # gets no second trunk -- so the numbers behind it are printed in full
    # rather than summarised into the one slice that happened to be reported.
    lines += [
        "",
        "Auxiliary activation head -- four views, copy baseline per slice (D-063):",
        "  NON-DECISIONAL DIAGNOSTIC. Activation carries no hypothesis: H1 and H2",
        "  are claims about position error and disagreement. Nothing here may",
        "  reach the failure set, early stopping, repair labels or the critic.",
        f"{'N':>6} {'slice':>12} {'members mean':>13} {'best member':>12} "
        f"{'copy baseline':>14} {'beat':>6}",
    ]
    for n in sorted({r.n_transitions for r in rows}):
        rs = [r for r in rows if r.n_transitions == n]
        for name in ("all_interact", "changed", "unchanged"):
            values = [v for r in rs for v in r.activation[f"error_{name}_per_member"]]
            baselines = [r.activation["copy_baseline"][name] for r in rs]
            baseline = float(np.mean(baselines))
            beat = sum(1 for v in values if v < baseline)
            lines.append(
                f"{n:>6} {name:>12} {np.mean(values):>13.4f} {min(values):>12.4f} "
                f"{baseline:>14.4f} {beat:>3}/{len(values):<2}"
            )
    lines.append(
        "  Copying is exactly right on a no-change transition and exactly wrong "
        "on a\n  changed one, which is why each slice carries its own baseline."
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
    attempt = run()
    print()
    print(report(attempt.rows))
    print()
    print(f"  evidence: {attempt.attempt_dir}/manifest.json")
    # The attempt directory is the immutable record. The repository's figures/
    # copies are for the thesis and are regenerated deliberately, never as a
    # side effect of a run.
    for path in figures(attempt.rows):
        print(f"  wrote {path}")
