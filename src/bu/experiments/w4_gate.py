"""The Week 4 reliability gate runner (S§W4 Tue, Plan §11.3).

**This module produces evidence; it does not decide anything.** The verdict is
`bu.stats.gate.reliability_gate`, which reads what this writes and re-derives
every claim from the canonical configuration and the artefacts on disk. The two
are deliberately separate: a runner that both generated and blessed its own
numbers is exactly the arrangement Sol refused to certify twice (D-071, D-072).

What the evidence contract exists to prevent
--------------------------------------------
Two rounds of review closed two versions of the same hole. First the gate took
bare curves and stamped the golden identities onto whatever it was handed --
five lines of invented floats returned PASS. Then it read a flattened manifest
and checked only that the manifest agreed with itself, so a *longer* fabrication
passed just as cleanly. The trust boundary had moved but never reached the
execution evidence.

So every run this module writes carries, and the gate independently re-derives:

* the complete canonical ``Config`` -- identity is derived from it, never taken
  from a flattened field that merely claims to agree;
* the **complete** ``TrainConfig``, not only the two fields a rung varies: a run
  altered through learning rate or patience would otherwise pass;
* ``granularity``, which is a ``train_ensemble`` argument rather than a
  ``TrainConfig`` field and therefore cannot be derived from the config at all --
  it is attested in the run record, written when the run started;
* the evaluation pool's digest, so that a curve evaluated on a *different* pool
  at each dataset size is refused rather than being read as a trend;
* the normalising scale, built before any mask and reused across the six sizes
  (D-061, C-010);
* per-member records, so a claimed ensemble that was never fitted is visible;
* the source row each disagreement was computed from, and digests for every
  artefact, so "immutable attempt" is checkable rather than asserted.

Compute
-------
The full gate is 3 layouts x 5 development seeds x 6 sizes = **90 ensembles**.
At rung 0 that is 450 fits; at rungs 1 and 2, 900. Nothing here runs on import,
and the runner refuses confirmatory seeds outright.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from .. import constants as K
from ..config import Config, UnitSpec
from ..env.collect import collect_pools
from ..models.world_model import MOVEMENT_ACTIONS
from ..metrics import RunLogger
from ..models.ensemble import train_ensemble
from ..models.uncertainty import NormalisationScale, summarise
from ..runrecord import git_state

from ..stats.gate import (
    GATE_CAUSAL_ATTRIBUTE, GATE_CONFOUND_RATE, GATE_LAYOUTS, GATE_SEEDS,
    CELL, GATE_STAGE, MANIFEST_VERSION, METRIC_SCHEMA_VERSION, EVIDENCE_CONTRACT_VERSION,
    GateEvidence, RungSpec,
)
from .w3_pilot import new_attempt_dir

# MANIFEST_VERSION, METRIC_SCHEMA_VERSION, EVIDENCE_CONTRACT_VERSION and CELL are
# defined in `bu.stats.gate`: the reader is what must refuse an unknown version,
# so the version belongs with the reader (D-073).


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _row_digest(row: dict) -> str:
    return _sha256_bytes(json.dumps(row, sort_keys=True, separators=(",", ":")).encode())


def evaluation_pool_digest(pools) -> str:
    """A digest of the evaluation pool itself.

    D-052 fixes the evaluation pool across dataset sizes; this makes that
    checkable rather than trusted. If the six sizes of one curve ever carry
    different digests, the gate refuses the curve -- because disagreement
    measured on six different pools is not a trend in dataset size.
    """
    h = hashlib.sha256()
    for name in ("obs", "action", "next_obs", "episode", "step"):
        array = np.ascontiguousarray(getattr(pools.evaluation, name))
        h.update(name.encode())
        h.update(str(array.dtype).encode())
        h.update(str(array.shape).encode())
        h.update(array.tobytes())
    return h.hexdigest()


def gate_units(layout: str, n: int, hidden_size: int = 256) -> UnitSpec:
    return UnitSpec(
        causal_attribute=GATE_CAUSAL_ATTRIBUTE,
        layout=layout,
        confound_rate=GATE_CONFOUND_RATE,
        family="estimation",
        n_transitions=n,
        hidden_size=hidden_size,
    )


@dataclass
class CellResult:
    """One (layout, seed, size) cell's evidence, before it is written out."""

    run: dict
    row: dict


def run_cell(
    *,
    layout: str,
    seed: int,
    n: int,
    spec: RungSpec,
    attempt: Path,
    scales: dict[tuple[str, int], NormalisationScale],
    pool_digests: dict[tuple[str, int], str],
    hidden_size: int = 256,
) -> CellResult:
    """Fit one ensemble and return its evidence. Writes into ``attempt`` only."""
    if seed >= K.CONFIRMATORY_SEED_BASE:
        # A ValueError, not an assert: assertions vanish under -O, so they are
        # not a safety boundary (D-059).
        raise ValueError(
            f"seed {seed} is confirmatory; the reliability gate is development-only "
            f"(< {K.CONFIRMATORY_SEED_BASE}, D-034, D-068)"
        )

    unit = gate_units(layout, n, hidden_size=hidden_size)
    pools = collect_pools(unit, stage=GATE_STAGE, seed=seed)
    digest = evaluation_pool_digest(pools)
    key = (layout, seed)
    if key in pool_digests and pool_digests[key] != digest:
        raise RuntimeError(
            f"{layout} seed {seed}: the evaluation pool changed between dataset "
            f"sizes ({pool_digests[key][:12]}... then {digest[:12]}...). D-052 fixes "
            "it across sizes, so every cross-size comparison would be on different "
            "data."
        )
    pool_digests.setdefault(key, digest)

    config = Config(unit=unit, seed=seed, stage=GATE_STAGE, train=spec.train_config())
    # `granularity` is not a Config field, so the run record is the only place it
    # is independently attested. The gate cross-checks the manifest against this.
    extra = {
        "granularity": spec.granularity,
        "rung": spec.rung,
        "rung_spec_hash": spec.spec_hash,
        "evaluation_pool_digest": digest,
        "cell": CELL,
    }
    with RunLogger.start(config, root=attempt / "records", extra=extra) as logger:
        ensemble = train_ensemble(
            unit, pools, spec.train_config(), stage=GATE_STAGE, seed=seed,
            granularity=spec.granularity, logger=logger,
        )

    obs = torch.as_tensor(pools.evaluation.obs)
    action = torch.as_tensor(pools.evaluation.action)
    next_obs = torch.as_tensor(pools.evaluation.next_obs)
    move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
    members = ensemble.member_predictions(obs[move], action[move])
    targets = ensemble.members[0].targets(next_obs[move])[0]

    # C-010 / D-061: the scale is built from the FULL movement evaluation pool,
    # before any failure mask exists, and the SAME OBJECT is reused for every
    # size sharing the pool. W4 Friday's masked statistics must reuse it too.
    scale = scales.get(key)
    if scale is None:
        scale = NormalisationScale.from_evaluation_pool(targets)
        scales[key] = scale

    summary = summarise(members, targets, n_transitions=n, seed=seed, scale=scale)
    row = {
        "layout": layout,
        "n_transitions": n,
        "seed": seed,
        "uncertainty": summary.as_row(),
        "val_position_errors": list(ensemble.val_position_errors),
        "epochs": [r.epochs_run for r in ensemble.results],
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
    }
    record_dir = attempt / "records" / config.run_id
    run = {
        "config": config.to_dict(),
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        "layout": layout,
        "n_transitions": n,
        "seed": seed,
        "stage": config.stage,
        "seed_partition": "development",
        "granularity": spec.granularity,
        "member_count": spec.ensemble_size,
        "member_indices": list(range(spec.ensemble_size)),
        "member_record_digest": _sha256_file(record_dir / "metrics.jsonl"),
        "run_record_digest": _sha256_file(record_dir / "run.json"),
        "evaluation_pool_id": f"{layout}-s{seed:03d}",
        "evaluation_pool_digest": digest,
        "normalisation": scale.as_row(),
        "metric_schema_version": METRIC_SCHEMA_VERSION,
        "mean_disagreement": summary.as_row()["mean_disagreement"],
        # row_index / row_digest are filled once rows.json is ordered.
        "row_index": -1,
        "row_digest": "",
    }
    return CellResult(run=run, row=row)


def write_manifest(
    attempt: Path,
    *,
    spec: RungSpec,
    cells: list[CellResult],
    git,
    artifacts: list[dict],
) -> dict:
    """The evidence contract, written once. Never reopened (D-062)."""
    from ..runrecord import package_versions

    rows = [c.row for c in cells]
    (attempt / "rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    for index, cell in enumerate(cells):
        cell.run["row_index"] = index
        cell.run["row_digest"] = _row_digest(rows[index])

    n_members = 0
    for record in sorted((attempt / "records").glob("*/metrics.jsonl")):
        n_members += sum(1 for line in record.read_text().splitlines() if line.strip())

    artifacts = list(artifacts) + [
        {
            "path": "rows.json",
            "sha256": _sha256_file(attempt / "rows.json"),
            "bytes": (attempt / "rows.json").stat().st_size,
        }
    ]

    manifest = {
        "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
        "manifest_version": MANIFEST_VERSION,
        "attempt_id": GateEvidence.content_id(
            [
                [c.run[f] for f in GateEvidence.IDENTITY_DIGESTS]
                for c in cells
            ],
            rung=spec.rung, spec_hash=spec.spec_hash,
        ),
        "attempt": attempt.name,
        "cell": CELL,
        "rung": spec.rung,
        "rung_spec": spec.as_row(),
        "rung_spec_hash": spec.spec_hash,
        "seed_partition": "development",
        "commit": git.commit,
        "dirty": git.dirty,
        "branch": git.branch,
        "packages": package_versions(),
        "n_runs": len(cells),
        "n_member_records": n_members,
        "runs": [c.run for c in cells],
        "artifacts": artifacts,
    }
    path = attempt / "manifest.json"
    if path.exists():
        raise FileExistsError(f"{path} already exists; attempts are written once")
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run(
    *,
    rung: int = 0,
    layouts: tuple[str, ...] = GATE_LAYOUTS,
    seeds: tuple[int, ...] = GATE_SEEDS,
    sizes: tuple[int, ...] = K.DATA_SIZES,
    hidden_size: int = 256,
    threads: int = 4,
    out_dir: str | Path | None = None,
    verbose: bool = True,
    allow_dirty: bool = False,
) -> Path:
    """Run one rung of the gate and write one immutable attempt. Returns its path.

    The defaults are the registered grid: 3 x 5 x 6 = 90 ensembles. The
    parameters exist so a test can exercise the machinery at a smaller shape --
    the resulting evidence is then correctly **refused** by the gate, which
    requires the exact grid.
    """
    torch.set_num_threads(threads)
    spec = RungSpec.for_rung(rung)
    # Captured before anything is written: reading git state afterwards would
    # report the tree dirty because of this attempt's own output (D-062).
    git = git_state()
    if git.dirty and not allow_dirty:
        # The verifier refuses a dirty attempt afterwards, which means the fits
        # were spent producing evidence that could never be used. Fail here
        # instead: rung 0 is 450 fits (Sol, D-073).
        raise ValueError(
            f"the working tree is dirty at commit {git.commit[:7]}; a gate verdict "
            "must name one reproducible code state. Refusing before any fit rather "
            "than after all of them -- commit or stash first."
        )
    # `allow_dirty` saves the compute check only. It cannot make dirty evidence
    # usable: the manifest still records `dirty`, and the verifier still refuses
    # it, so the safety property lives with the reader either way.
    root = Path(out_dir) if out_dir else Path("runs/w4_gate") / f"rung-{rung:02d}-{spec.spec_hash}"
    attempt = new_attempt_dir(root)

    scales: dict[tuple[str, int], NormalisationScale] = {}
    pool_digests: dict[tuple[str, int], str] = {}
    cells: list[CellResult] = []
    total = len(layouts) * len(seeds) * len(sizes)
    for layout in layouts:
        for seed in seeds:
            for n in sizes:
                if verbose:
                    print(f"  [{len(cells) + 1:>3}/{total}] {layout} seed {seed} N={n}", flush=True)
                cells.append(
                    run_cell(
                        layout=layout, seed=seed, n=n, spec=spec, attempt=attempt,
                        scales=scales, pool_digests=pool_digests, hidden_size=hidden_size,
                    )
                )

    write_manifest(attempt, spec=spec, cells=cells, git=git, artifacts=[])
    if verbose:
        print(f"\n  wrote {attempt}")
        print(f"  rung {spec.rung} ({spec.estimator}), spec hash {spec.spec_hash}")
        print(f"  {len(cells)} cells, {len(cells) * spec.ensemble_size} fits")
    return attempt


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rung", type=int, default=0)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    run(rung=args.rung, threads=args.threads)
