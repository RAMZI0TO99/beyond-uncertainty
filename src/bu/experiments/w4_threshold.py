"""W4 Friday: calibrate the failure threshold, once, and never again (P§10.1).

**This is the most irreversible act in the project.** P§10.1 sets the failure
threshold at a fixed percentile of the error distribution on a well-fit
reference model, "set once, in Month 1, on reference data, and not tuned
afterwards", precisely so it cannot become an unreported degree of freedom.
Every failure set, every repair label and therefore every H2 and H3 claim is
downstream of the number this produces.

Sol refused the first version of this runner because its public API left several
**result-changing degrees of freedom** open: substitutable reference units, an
injectable scorer that could generate synthetic evidence indistinguishable from
real calibration, `allow_dirty`, and free choice of seeds, RNG and balancing
count -- none of them checked by an eligibility verifier, and none recorded in a
way that would reveal the substitution afterwards. That is the shape D-071 …
D-073 kept finding in the gate: the trust boundary stopping one layer short of
execution.

So this version takes **no arguments that can change the number**. The reference
set, the seeds, the balancing rule, the RNG, the percentile and its
interpolation method are all frozen constants; the only inputs are where to
write and whether this is a declared re-attempt.

The frozen specification (Sol, ruling on deltas 43–44)
------------------------------------------------------
* **Percentile 95.0**, `numpy` method **"linear"** stated explicitly rather than
  inherited, since a library default that changes would silently move the
  threshold.
* A transition is a failure when its registered normalised error is **strictly
  greater** than the threshold.
* Reference model: **fully observed estimation family, largest registered size
  (5,000), no confound, registered architecture**, all **nine** layout ×
  causal-attribute strata, **exactly confirmatory seeds 1000–1004** — the
  **45 cells** are required exactly, and a crash, non-finite result or incomplete
  fit **invalidates the whole attempt** rather than allowing selective
  replacement of an inconvenient cell.
* The **five-member baseline ensemble and its ensemble-mean error**, not a single
  model: the downstream failure mask is defined from the unrepaired baseline
  ensemble mean, so calibrating a K=1 error distribution and applying it to K=5
  means would change the statistic at the threshold boundary.
* Balancing, frozen: pool each stratum's five seeds, take the **minimum**
  available stratum count, subsample **without replacement** using **RNG seed 0**.
* Threading pinned at **4 intra-op / 4 inter-op** and recorded.
* One **immutable attempt directory**; a second attempt is refused unless the
  first has been **formally declared invalid before its threshold was inspected**.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from .. import constants as K
from ..config import Config, FEATURES, LAYOUTS, TrainConfig, UnitSpec
from ..env.collect import collect_pools
from ..metrics import RunLogger
from ..models.ensemble import assert_pools_match, train_ensemble
from ..models.uncertainty import ScaledEvaluation, normalised_error
from ..models.world_model import MOVEMENT_ACTIONS
from ..runrecord import git_state
from ..stats.gate import EVIDENCE_CONTRACT_VERSION, METRIC_SCHEMA_VERSION
from ..streams import confirmatory_seeds
from .w4_gate import _pin_threading, torch_threading

#: A distinct obligation, registered in `STAGE_SEEDS` (D-097). Reusing `exp1`
#: would have given a threshold fit the SAME `run_id` as the Experiment 1 fit at
#: that unit and seed, because `TrainConfig` is not part of run identity.
THRESHOLD_STAGE = "threshold_calibration"

#: The reference condition. Frozen; not a parameter.
REFERENCE_FAMILY = "estimation"
REFERENCE_SIZE = max(K.DATA_SIZES)
REFERENCE_CONFOUND_RATE = 0.0

#: Exactly these seeds. Not a count, not a range -- the actual tuple.
THRESHOLD_SEEDS: tuple[int, ...] = confirmatory_seeds(K.SEEDS_THRESHOLD)

#: The percentile, and the interpolation method, both stated.
THRESHOLD_PERCENTILE = 95.0
PERCENTILE_METHOD = "linear"

#: Balancing, frozen (Sol): minimum available stratum count, without
#: replacement, RNG seed 0.
BALANCE_RNG_SEED = 0

#: Threading, pinned and recorded.
THRESHOLD_THREADS = 4
THRESHOLD_INTEROP_THREADS = 4

#: The only permitted attempt-directory names. A frozen format, because prior
#: attempts are discovered by pattern: a caller who could pass any name (or a
#: path) could step outside the search and bypass the one-attempt policy
#: entirely (Sol, delta 45).
ATTEMPT_NAME = re.compile(r"^attempt-\d{3}$")

#: The file that declares a prior attempt invalid. It must exist BEFORE a second
#: attempt runs, and it must have been written before the first attempt's
#: threshold was read -- see `assert_may_attempt`.
INVALIDATION_FILE = "INVALID"


def reference_strata() -> tuple[tuple[str, str], ...]:
    """The nine (layout, causal_attribute) strata the calibration pool balances over."""
    return tuple((layout, attr) for layout in LAYOUTS for attr in FEATURES)


def reference_units() -> tuple[UnitSpec, ...]:
    """One fully-observed, well-fit reference unit per stratum. Frozen."""
    return tuple(
        UnitSpec(
            family=REFERENCE_FAMILY, layout=layout, causal_attribute=attr,
            confound_rate=REFERENCE_CONFOUND_RATE, n_transitions=REFERENCE_SIZE,
            withheld_features=(),
        )
        for layout, attr in reference_strata()
    )


#: The exact cell grid: nine strata x five seeds.
REQUIRED_CELLS = len(reference_strata()) * len(THRESHOLD_SEEDS)


def is_failure(error, threshold: float):
    """A transition fails when its error is **strictly greater** than the threshold.

    Stated in one place because the boundary is a real decision: at `>=` a
    transition exactly on the threshold is a failure, at `>` it is not, and the
    frozen number is a percentile of a continuous distribution where ties are
    possible after rounding through JSON.
    """
    return np.asarray(error) > threshold


@dataclass(frozen=True)
class ReferenceCell:
    """One (stratum, seed) reference fit: its errors and the record behind them."""

    layout: str
    causal_attribute: str
    seed: int
    errors: np.ndarray
    run_id: str
    config_id: str
    unit_id: str
    n_members: int

    @property
    def stratum(self) -> tuple[str, str]:
        return (self.layout, self.causal_attribute)

    def __len__(self) -> int:
        return int(self.errors.shape[0])


@dataclass(frozen=True)
class ThresholdCalibration:
    """The calibrated number, and everything needed to recompute or refuse it."""

    threshold: float
    percentile: float
    percentile_method: str
    n_per_stratum: int
    n_total: int
    strata: tuple[tuple[str, str], ...]
    seeds: tuple[int, ...]
    commit: str
    threading: dict
    cells: tuple[dict, ...]
    selected_indices: dict

    def as_row(self) -> dict:
        return {
            "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
            "metric_schema_version": METRIC_SCHEMA_VERSION,
            "threshold": self.threshold,
            "percentile": self.percentile,
            "percentile_method": self.percentile_method,
            "failure_rule": "error > threshold (strict)",
            "n_per_stratum": self.n_per_stratum,
            "n_total": self.n_total,
            "strata": [list(s) for s in self.strata],
            "seeds": list(self.seeds),
            "required_cells": REQUIRED_CELLS,
            "commit": self.commit,
            "threading": self.threading,
            "reference": {
                "family": REFERENCE_FAMILY, "size": REFERENCE_SIZE,
                "confound_rate": REFERENCE_CONFOUND_RATE,
                "stage": THRESHOLD_STAGE,
                "ensemble_size": K.DEFAULT_ENSEMBLE_SIZE,
                "statistic": "ensemble-mean normalised movement error",
            },
            "balance": {
                "rule": "pool each stratum's seeds, take the minimum available "
                        "stratum count, subsample without replacement",
                "rng_seed": BALANCE_RNG_SEED,
            },
            "cells": list(self.cells),
            "selected_indices": self.selected_indices,
        }

    def summary(self) -> str:
        return (
            f"FAILURE THRESHOLD (NOT FROZEN UNTIL A CHANGE RECORD SAYS SO)\n"
            f"  percentile {self.percentile} ({self.percentile_method})  ->  "
            f"threshold {self.threshold:.6f}\n"
            f"  a transition fails when error > threshold, strictly\n"
            f"  {len(self.strata)} strata x {self.n_per_stratum} transitions "
            f"= {self.n_total}, from {len(self.cells)} cells\n"
            f"  seeds {list(self.seeds)}, commit {self.commit[:7]}, "
            f"threads {self.threading}\n"
            f"  This number is EVIDENCE. Promoting it to a constant is a Change "
            f"Record under D-035."
        )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _threshold_from_arrays(arrays: dict, rng_seed: int = BALANCE_RNG_SEED) -> tuple[float, dict, int]:
    """The frozen balancing and percentile, as a **pure** function of error arrays.

    Private and deliberately unable to produce an attempt. It returns a bare
    float, a selection map and a count -- never a `ThresholdCalibration` and
    never anything `write_attempt` will accept. That is Sol's requirement that
    synthetic tests sit behind a helper *whose output cannot be frozen*: a test
    can exercise the balancing and the percentile without any route by which a
    synthetic number could be written out as a calibration.

    Args:
        arrays: ``{(layout, attr): 1-D error array}``, already pooled over seeds.
    """
    if not arrays:
        raise ValueError("no reference errors; there is nothing to calibrate on")
    available = min(len(v) for v in arrays.values())
    if available <= 0:
        raise ValueError("a stratum contributed no transitions")
    rng = np.random.default_rng(rng_seed)
    selected, drawn = {}, []
    for stratum in sorted(arrays):
        pool = np.asarray(arrays[stratum], dtype=float)
        idx = np.sort(rng.choice(len(pool), size=available, replace=False))
        selected["|".join(stratum)] = idx.tolist()
        drawn.append(pool[idx])
    pooled = np.concatenate(drawn)
    if not np.all(np.isfinite(pooled)):
        raise ValueError(
            "the pooled reference errors contain non-finite values. A crash or a "
            "non-finite fit invalidates the whole attempt rather than allowing the "
            "inconvenient cell to be dropped (Sol)"
        )
    threshold = float(np.percentile(pooled, THRESHOLD_PERCENTILE, method=PERCENTILE_METHOD))
    return threshold, selected, available


def assert_may_attempt(root: Path, *, attempt: str) -> Path:
    """One immutable attempt directory, and a re-attempt protocol with teeth.

    A second attempt is refused unless the first carries an `INVALID` declaration
    **written before its threshold was inspected**. That ordering is the whole
    point: re-running after seeing a number you did not like, and keeping the
    second, is how a "fixed" threshold becomes a tuned one. The declaration
    records that the first attempt was abandoned for a stated reason, and it must
    predate the file that holds the number.
    """
    if not isinstance(attempt, str) or not ATTEMPT_NAME.match(attempt):
        raise ValueError(
            f"attempt name {attempt!r} is not of the frozen form attempt-NNN. "
            "Prior attempts are discovered by that pattern, so a free-form name -- "
            "or a path -- would sit outside the search and bypass the one-attempt "
            "policy entirely"
        )
    root = Path(root)
    target = root / attempt
    if target.exists():
        raise FileExistsError(
            f"{target} already exists. Attempts are written once (P§10.1); a "
            "second calibration overwriting the first is how a fixed threshold "
            "becomes a tuned one"
        )
    # Every permitted name matches ATTEMPT_NAME, and discovery uses the same
    # pattern -- so no permitted attempt can be invisible to this search.
    prior = sorted(
        d for d in (root.iterdir() if root.exists() else [])
        if d.is_dir() and ATTEMPT_NAME.match(d.name)
    )
    for earlier in prior:
        declaration = earlier / INVALIDATION_FILE
        result = earlier / "threshold_calibration.json"
        if not declaration.exists():
            raise FileExistsError(
                f"{earlier.name} exists and has not been declared invalid. Write "
                f"{INVALIDATION_FILE} into it, with the reason, BEFORE reading its "
                "threshold -- a re-attempt after seeing a number you did not like is "
                "a tuned threshold, whatever it is called"
            )
        if not declaration.read_text(encoding="utf-8").strip():
            raise ValueError(
                f"{earlier.name}/{INVALIDATION_FILE} is empty. The declaration must "
                "record WHY the attempt was abandoned: an empty file is a formality "
                "that any re-run could satisfy, which is exactly what the one-attempt "
                "policy exists to prevent"
            )
        if result.exists() and declaration.stat().st_mtime > result.stat().st_mtime:
            raise ValueError(
                f"{earlier.name} was declared invalid AFTER its threshold was "
                "written, so the declaration cannot be distinguished from a reaction "
                "to the number. That attempt stands; this one is refused"
            )
    return target


def score_reference_cell(unit: UnitSpec, *, seed: int, attempt: Path) -> ReferenceCell:
    """Train one reference ensemble, write its record, return its errors.

    The **five-member baseline ensemble and its ensemble-mean error** (Sol): the
    downstream failure mask is defined from the unrepaired baseline ensemble
    mean, so a K=1 error distribution would be a different statistic at the
    threshold boundary.
    """
    config = Config(unit=unit, seed=seed, stage=THRESHOLD_STAGE, train=TrainConfig())
    pools = collect_pools(unit, stage=THRESHOLD_STAGE, seed=seed, arm="baseline")
    assert_pools_match(pools, unit=unit, arm="baseline", stage=THRESHOLD_STAGE, seed=seed)

    extra = {
        "granularity": "episode",
        "seed_partition": "confirmatory",
        "cell": "W4 Fri -- threshold calibration",
        "threading": torch_threading(),
    }
    with RunLogger.start(config, root=attempt / "records", extra=extra) as logger:
        ensemble = train_ensemble(
            unit, pools, config.train, stage=THRESHOLD_STAGE, seed=seed,
            arm="baseline", granularity="episode", logger=logger,
        )

    obs = torch.as_tensor(pools.evaluation.obs)
    action = torch.as_tensor(pools.evaluation.action)
    next_obs = torch.as_tensor(pools.evaluation.next_obs)
    move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
    members = ensemble.member_predictions(obs[move], action[move])
    targets = ensemble.members[0].targets(next_obs[move])[0]
    # No mask exists yet -- this calibration is what defines one (D-061, C-010).
    scale = ScaledEvaluation.from_pool(
        members, targets, n_transitions=unit.n_transitions, seed=seed
    ).scale
    errors = normalised_error(members.mean(dim=0), targets, scale).detach().numpy()
    if not np.all(np.isfinite(errors)):
        raise ValueError(
            f"non-finite errors in cell {unit.layout}/{unit.causal_attribute} seed "
            f"{seed}. This invalidates the whole attempt; cells are not replaced "
            "selectively (Sol)"
        )
    return ReferenceCell(
        layout=unit.layout, causal_attribute=unit.causal_attribute, seed=seed,
        errors=errors, run_id=config.run_id, config_id=config.config_id,
        unit_id=config.unit_id, n_members=config.train.ensemble_size,
    )


def calibrate(out_dir: str | Path, *, attempt: str = "attempt-001") -> ThresholdCalibration:
    """Calibrate the failure threshold. **Returns evidence; freezes nothing.**

    Takes no argument that can change the number. The reference set, the seeds,
    the balancing rule, the RNG, the percentile and its method are frozen
    constants; `out_dir` says where to write and `attempt` names the directory.
    There is no `units`, no `score_fn`, no `allow_dirty`, no `rng` and no
    `n_per_stratum` -- Sol refused the previous version for exactly those.

    Promoting the returned number to a constant remains a deliberate human act
    under a Change Record (D-035). This function never edits `constants.py`.
    """
    target = assert_may_attempt(Path(out_dir), attempt=attempt)

    git = git_state()
    if git.dirty:
        raise ValueError(
            f"the working tree is dirty at commit {git.commit[:7]}. This threshold is "
            "frozen permanently and every failure set in the thesis descends from it, "
            "so it must name one reproducible code state. There is deliberately no "
            "override: evidence that does not record its own ineligibility is worse "
            "than no evidence."
        )

    _pin_threading(THRESHOLD_THREADS, THRESHOLD_INTEROP_THREADS)
    threading = torch_threading()
    if (threading["num_threads"] != THRESHOLD_THREADS
            or threading["num_interop_threads"] != THRESHOLD_INTEROP_THREADS):
        raise ValueError(
            f"threading is {threading}, not the pinned "
            f"{THRESHOLD_THREADS}/{THRESHOLD_INTEROP_THREADS}. Thread count changes "
            "the reduction order (D-076), so an attempt cannot be produced under a "
            "configuration it did not choose"
        )

    target.mkdir(parents=True)
    (target / "arrays").mkdir()

    cells: list[ReferenceCell] = []
    for unit in reference_units():
        for seed in THRESHOLD_SEEDS:
            cells.append(score_reference_cell(unit, seed=seed, attempt=target))

    if len(cells) != REQUIRED_CELLS:
        raise ValueError(
            f"{len(cells)} reference cells, not the required {REQUIRED_CELLS} "
            f"({len(reference_strata())} strata x {len(THRESHOLD_SEEDS)} seeds). "
            "The grid is exact: a missing or duplicated cell changes which errors "
            "the percentile is taken over"
        )
    seen = {(c.layout, c.causal_attribute, c.seed) for c in cells}
    if len(seen) != REQUIRED_CELLS:
        raise ValueError("duplicate (stratum, seed) cells; the grid must be exact")

    # Store every cell's errors as an immutable artefact, digested, so the
    # threshold can be recomputed by someone who was not there.
    records = []
    pooled: dict[tuple[str, str], list[np.ndarray]] = {}
    for cell in cells:
        name = f"{cell.layout}-{cell.causal_attribute}-s{cell.seed}.npy"
        path = target / "arrays" / name
        np.save(path, cell.errors)
        records.append({
            "layout": cell.layout, "causal_attribute": cell.causal_attribute,
            "seed": cell.seed, "n_transitions": len(cell),
            "run_id": cell.run_id, "config_id": cell.config_id,
            "unit_id": cell.unit_id, "n_members": cell.n_members,
            "errors_file": f"arrays/{name}", "errors_digest": _sha256_file(path),
            "run_record_digest": _sha256_file(target / "records" / cell.run_id / "run.json"),
            "member_record_digest": _sha256_file(target / "records" / cell.run_id / "metrics.jsonl"),
        })
        pooled.setdefault(cell.stratum, []).append(cell.errors)

    arrays = {k: np.concatenate(v) for k, v in pooled.items()}
    threshold, selected, per_stratum = _threshold_from_arrays(arrays)

    calibration = ThresholdCalibration(
        threshold=threshold, percentile=THRESHOLD_PERCENTILE,
        percentile_method=PERCENTILE_METHOD, n_per_stratum=per_stratum,
        n_total=per_stratum * len(arrays), strata=tuple(sorted(arrays)),
        seeds=THRESHOLD_SEEDS, commit=git.commit, threading=threading,
        cells=tuple(records), selected_indices=selected,
    )
    (target / "threshold_calibration.json").write_text(
        json.dumps(calibration.as_row(), indent=2), encoding="utf-8"
    )
    return calibration


def recompute_threshold(attempt_dir: str | Path) -> float:
    """Reproduce the threshold from the stored artefacts, trusting almost nothing.

    Sol, delta 45: the previous version trusted too much of the result JSON. It
    read the percentile, the method and the selection out of the very file whose
    number it was meant to check — so an attempt that recorded a different
    percentile, a short grid, or a hand-written selection would have "recomputed"
    perfectly. That is the D-071 shape: a manifest checked only against itself.

    Now every frozen constant is compared against the code rather than read from
    the file, and the deterministic selection is **reconstructed from the stored
    arrays** and compared with what the attempt recorded, instead of being reused.
    """
    attempt = Path(attempt_dir)
    row = json.loads((attempt / "threshold_calibration.json").read_text(encoding="utf-8"))

    def expect(key, want, what):
        got = row.get(key)
        if got != want:
            raise ValueError(
                f"{what}: the attempt records {got!r} but the frozen specification "
                f"is {want!r}. The number was not taken under the registered rule"
            )

    expect("percentile", THRESHOLD_PERCENTILE, "percentile")
    expect("percentile_method", PERCENTILE_METHOD, "percentile method")
    expect("required_cells", REQUIRED_CELLS, "required cell count")
    expect("seeds", list(THRESHOLD_SEEDS), "seed set")
    expect("failure_rule", "error > threshold (strict)", "failure rule")
    if row.get("balance", {}).get("rng_seed") != BALANCE_RNG_SEED:
        raise ValueError("the attempt records a different balancing RNG seed")
    ref = row.get("reference", {})
    for key, want in (("stage", THRESHOLD_STAGE), ("size", REFERENCE_SIZE),
                      ("family", REFERENCE_FAMILY),
                      ("ensemble_size", K.DEFAULT_ENSEMBLE_SIZE)):
        if ref.get(key) != want:
            raise ValueError(
                f"reference {key}: attempt records {ref.get(key)!r}, frozen is {want!r}"
            )
    thr = row.get("threading", {})
    if (thr.get("num_threads") != THRESHOLD_THREADS
            or thr.get("num_interop_threads") != THRESHOLD_INTEROP_THREADS):
        raise ValueError(
            f"threading {thr} is not the pinned "
            f"{THRESHOLD_THREADS}/{THRESHOLD_INTEROP_THREADS}; thread count changes "
            "the reduction order (D-076)"
        )

    cells = row["cells"]
    if len(cells) != REQUIRED_CELLS:
        raise ValueError(f"{len(cells)} cells stored but {REQUIRED_CELLS} required")
    keys = {(c["layout"], c["causal_attribute"], c["seed"]) for c in cells}
    if len(keys) != REQUIRED_CELLS:
        raise ValueError("duplicate (stratum, seed) cells in the attempt")
    if {(c["layout"], c["causal_attribute"]) for c in cells} != set(reference_strata()):
        raise ValueError("the stored strata are not the nine registered ones")
    if {c["seed"] for c in cells} != set(THRESHOLD_SEEDS):
        raise ValueError("the stored seeds are not the registered set")
    bad_k = [c for c in cells if c.get("n_members") != K.DEFAULT_ENSEMBLE_SIZE]
    if bad_k:
        raise ValueError(
            f"{len(bad_k)} cell(s) record an ensemble size other than "
            f"{K.DEFAULT_ENSEMBLE_SIZE}; the threshold is defined on the baseline "
            "ensemble mean"
        )

    pooled: dict[tuple[str, str], list[np.ndarray]] = {}
    for cell in sorted(cells, key=lambda c: (c["layout"], c["causal_attribute"], c["seed"])):
        path = attempt / cell["errors_file"]
        if _sha256_file(path) != cell["errors_digest"]:
            raise ValueError(
                f"{cell['errors_file']} has a digest the attempt does not record. "
                "The stored errors are not the ones the threshold was taken over"
            )
        records = attempt / "records" / cell["run_id"]
        for name, field in (("run.json", "run_record_digest"),
                            ("metrics.jsonl", "member_record_digest")):
            target = records / name
            if not target.exists():
                raise ValueError(f"{cell['run_id']}/{name} is missing from the attempt")
            if _sha256_file(target) != cell[field]:
                raise ValueError(
                    f"{cell['run_id']}/{name} does not match its recorded digest"
                )
        pooled.setdefault((cell["layout"], cell["causal_attribute"]), []).append(
            np.load(path)
        )

    arrays = {k: np.concatenate(v) for k, v in pooled.items()}
    value, selected, _ = _threshold_from_arrays(arrays)

    recorded = {k: list(v) for k, v in row["selected_indices"].items()}
    if {k: list(v) for k, v in selected.items()} != recorded:
        raise ValueError(
            "the deterministic selection reconstructed from the stored arrays does "
            "not match the one the attempt recorded. The recorded indices are not "
            "reused here precisely so that a hand-written selection cannot pass"
        )
    if not np.isclose(value, row["threshold"], rtol=0, atol=1e-12):
        raise ValueError(
            f"recomputed {value!r} but the attempt records {row['threshold']!r}. "
            "The stored artefacts do not reproduce the number they attest"
        )
    return value


def write_attempt_producer():
    """The only function that can produce a writable calibration.

    Exists so a test can assert that fact behaviourally rather than by grepping
    source, which any docstring mention would defeat. If a second producer is
    ever added, this stops being true and the test that reads it should fail.
    """
    return calibrate
