"""Does the ONE global failure threshold mean the same thing in every stratum?

D-035 fixed a single threshold across all families and conditions. Its stated
justification is that balancing the calibration pool makes one threshold
defensible "once D-032 has fixed the error to one scale". This probe asks
whether the error really is on one scale -- and finds it is not, because D-061
fixes the normalising scale to each *evaluation pool*, and those pools differ
systematically by layout.

No training and no fits: `targets()` is a pure slice of `next_obs`, and the
scale is a std over those targets, so this reads the environment only.

The raw error is BOUNDED, not approximated (the D-042 lesson -- a bound reported
as a measurement is how two wrong numbers reached five files). Since
normalised = ||delta / (s_x, s_y)||, the raw norm ||delta|| lies exactly in
[normalised * min(s), normalised * max(s)].

Run:  .venv/bin/python scripts/probe_threshold_heterogeneity.py
"""

import json, pathlib, numpy as np, torch
from bu import constants as K
from bu.env.collect import collect_pools
from bu.env.encoder import ObservationEncoder
from bu.models.world_model import dynamic_layout
from bu.models.uncertainty import per_dimension_scale
from bu.experiments.w4_threshold import (
    reference_units, reference_strata, THRESHOLD_SEEDS, THRESHOLD_STAGE, MOVEMENT_ACTIONS,
)

sc = {}
for unit, key in zip(reference_units(), reference_strata()):
    enc = ObservationEncoder(n_objects=unit.n_objects, grid_size=unit.grid_size,
                             withheld=unit.withheld_features)
    pos = list(dynamic_layout(enc).position)
    for seed in THRESHOLD_SEEDS:
        p = collect_pools(unit, stage=THRESHOLD_STAGE, seed=seed, arm="baseline")
        a = torch.as_tensor(p.evaluation.action)
        mv = torch.isin(a, torch.as_tensor(MOVEMENT_ACTIONS))
        s = per_dimension_scale(torch.as_tensor(p.evaluation.next_obs)[mv][:, pos])
        sc[(key[0], key[1], seed)] = (float(s.min()), float(s.max()))

d = pathlib.Path('runs/w4_threshold/attempt-001')
rec = json.loads((d/'threshold_calibration.json').read_text())
lo, hi, fail = {}, {}, {}
for c in rec['cells']:
    k = (c['layout'], c['causal_attribute'], c['seed'])
    e = np.load(d / c['errors_file']); m = e.mean()
    lo.setdefault(c['layout'], []).append(m * sc[k][0])
    hi.setdefault(c['layout'], []).append(m * sc[k][1])
    fail.setdefault(c['layout'], []).append((e > K.FAILURE_THRESHOLD).mean())

print(f"{'layout':<12}{'RAW error (rigorous bound)':>34}{'failure rate':>15}")
B = {}
for lay in ('clustered','uniform','sparse'):
    a, b, f = np.mean(lo[lay]), np.mean(hi[lay]), np.mean(fail[lay])
    B[lay] = (a, b)
    print(f"{lay:<12}{'['+format(a,'.5f')+', '+format(b,'.5f')+']':>34}{100*f:>14.2f}%")

print("\nDo the raw-error intervals overlap?")
for x, y in (('clustered','uniform'), ('uniform','sparse'), ('clustered','sparse')):
    ov = not (B[x][1] < B[y][0] or B[y][1] < B[x][0])
    fr = np.mean(fail[x]) / np.mean(fail[y])
    print(f"  {x:<10} vs {y:<10} overlap={ov!s:<6} failure-rate ratio {fr:.2f}x")

print("\nWorst case FOR the 'genuine difficulty' explanation:")
c_lo, u_hi = B['clustered'][0], B['uniform'][1]
print(f"  clustered raw is at MOST {100*(B['clustered'][1]/B['uniform'][0]-1):+.1f}% above uniform,")
print(f"  and at LEAST {100*(c_lo/u_hi-1):+.1f}% -- yet its failure rate is "
      f"{np.mean(fail['clustered'])/np.mean(fail['uniform']):.2f}x.")
