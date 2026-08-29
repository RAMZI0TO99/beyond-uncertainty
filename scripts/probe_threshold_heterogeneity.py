"""Layout-conditioned failure prevalence under the frozen threshold.

**What this establishes, stated at the limit of what it can support** (Sol's
ruling on delta 51, filed as D-109):

    Under the frozen per-evaluation-pool normalisation, failure prevalence
    differs materially by layout in the calibration evidence. This establishes
    layout-conditioned BASE-RATE HETEROGENEITY and raises a measurement-
    invariance limitation. The aggregate mean-error bounds below do NOT identify
    how much of the tail difference is caused by normalisation versus by
    differences in the error distributions.

**What it does NOT establish**, and what an earlier version of this probe
wrongly claimed: that the threshold "does not mean one thing", that the spread
is "mostly normalisation rather than difficulty", or that this is P§7.5 leakage.
Prevalence is an UPPER-TAIL probability; overlapping bounds on MEANS cannot
determine why tails differ. And `layout` is already in `FORBIDDEN_FIELDS` in
`critic/schema.py`, so it cannot reach critic input X at all.

**Estimands are named, because a number without one is not a number** (D-042,
D-044). Prevalence is reported two ways -- they are different quantities:
  * cell-mean  -- unweighted mean of the 15 per-cell rates. This is what Sol
                  recomputed independently.
  * pooled-row -- one rate over all rows of that layout.
The raw-error figure is a BOUND ON THE LAYOUT-AVERAGED CELL-MEAN RAW NORM, not
the raw-error distribution and not a per-transition quantity.

The scale is reported as its **per-dimension range** across the layout's cells.
There is deliberately no single scalar "the scale": the scale is a vector, which
is why D-061 matters, and collapsing it to one number was how the withdrawn
claim got its spurious precision.

No training and no fits: `targets()` is a pure slice of `next_obs`, so the scale
is a std over the environment alone.

Run:  .venv/bin/python scripts/probe_threshold_heterogeneity.py
"""

import json
import pathlib

import numpy as np
import torch

from bu import constants as K
from bu.env.collect import collect_pools
from bu.env.encoder import ObservationEncoder
from bu.models.world_model import dynamic_layout
from bu.models.uncertainty import per_dimension_scale
from bu.experiments.w4_threshold import (
    reference_units, reference_strata, THRESHOLD_SEEDS, THRESHOLD_STAGE, MOVEMENT_ACTIONS,
)

ATTEMPT = pathlib.Path("runs/w4_threshold/attempt-001")
LAYOUTS = ("clustered", "uniform", "sparse")


def measure_scales() -> dict[tuple[str, str, int], tuple[float, float]]:
    """(min, max) of the per-dimension scale vector for every calibration cell."""
    out = {}
    for unit, key in zip(reference_units(), reference_strata()):
        enc = ObservationEncoder(n_objects=unit.n_objects, grid_size=unit.grid_size,
                                 withheld=unit.withheld_features)
        pos = list(dynamic_layout(enc).position)
        for seed in THRESHOLD_SEEDS:
            pools = collect_pools(unit, stage=THRESHOLD_STAGE, seed=seed, arm="baseline")
            action = torch.as_tensor(pools.evaluation.action)
            move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
            targets = torch.as_tensor(pools.evaluation.next_obs)[move][:, pos]
            s = per_dimension_scale(targets)
            out[(key[0], key[1], seed)] = (float(s.min()), float(s.max()))
    return out


def main() -> None:
    scales = measure_scales()
    record = json.loads((ATTEMPT / "threshold_calibration.json").read_text())
    errors = {
        (c["layout"], c["causal_attribute"], c["seed"]): np.load(ATTEMPT / c["errors_file"])
        for c in record["cells"]
    }

    print(f"threshold = {K.FAILURE_THRESHOLD!r}   (failure is error > threshold, strictly)\n")
    print(f"{'layout':<11}{'scale range (per-dim)':>24}{'prevalence':>13}{'prevalence':>13}"
          f"{'raw-norm bound':>22}")
    print(f"{'':<11}{'across its 15 cells':>24}{'cell-mean':>13}{'pooled-row':>13}"
          f"{'layout-avg cell mean':>22}")

    summary = {}
    for lay in LAYOUTS:
        cells = {k: v for k, v in errors.items() if k[0] == lay}
        s_lo = min(scales[k][0] for k in cells)
        s_hi = max(scales[k][1] for k in cells)
        cell_mean = float(np.mean([(e > K.FAILURE_THRESHOLD).mean() for e in cells.values()]))
        pooled = float((np.concatenate(list(cells.values())) > K.FAILURE_THRESHOLD).mean())
        lo = float(np.mean([e.mean() * scales[k][0] for k, e in cells.items()]))
        hi = float(np.mean([e.mean() * scales[k][1] for k, e in cells.items()]))
        summary[lay] = (cell_mean, pooled, lo, hi)
        print(f"{lay:<11}{f'[{s_lo:.5f}, {s_hi:.5f}]':>24}{100*cell_mean:>12.4f}%"
              f"{100*pooled:>12.4f}%{f'[{lo:.5f}, {hi:.5f}]':>22}")

    print("\nPREVALENCE RATIOS (cell-mean estimand, the one Sol recomputed)")
    for a, b in (("clustered", "uniform"), ("uniform", "sparse"), ("clustered", "sparse")):
        print(f"  {a:<10} / {b:<10} {summary[a][0]/summary[b][0]:.6f}x")

    print("\nRAW-NORM BOUNDS -- a bound on the LAYOUT-AVERAGED CELL-MEAN raw norm.")
    print("  These are means. Prevalence is an upper-tail probability, so overlap or")
    print("  separation here does NOT identify the cause of the prevalence spread.")
    for a, b in (("clustered", "uniform"), ("uniform", "sparse"), ("clustered", "sparse")):
        ov = not (summary[a][3] < summary[b][2] or summary[b][3] < summary[a][2])
        print(f"  {a:<10} vs {b:<10} bounds overlap = {ov}")

    print("\nCONCLUSION SUPPORTED: layout-conditioned base-rate heterogeneity, and a")
    print("measurement-invariance limitation. NOT a causal attribution to normalisation.")


if __name__ == "__main__":
    main()
