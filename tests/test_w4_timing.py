"""The W4 Friday timing harness, rebuilt after Sol refused D-114 (D-116).

Wall time itself is not assertable. What is: the accounting the extrapolation
multiplies, the guards, and whether the stored attempt is internally coherent.

Two defects are pinned here because both actually shipped:
  * the first accounting summed obligations and reproduced **D-033's 375 phantom
    fits**, while also charging one fit per repair obligation instead of per seed;
  * the first reconciliation filtered candidate fits on **size** rather than on
    the unit, matching 1,464 plan entries against the 40 that ran.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from bu import constants as K
from bu.experiments.enumerate_units import design_units, execution_plan, total_model_fits
from bu.experiments.w4_timing import (
    ABLATION_ASSUMED_SIZE, MIN_REPETITIONS, SizeBenchmark, TIMING_STAGE,
    benchmark_sizes, design_accounting, extrapolate, reconcile,
    representative_condition,
)

ATTEMPT = pathlib.Path("runs/w4_timing/attempt-002/timing.json")


# --- the accounting ---------------------------------------------------------


def test_the_accounting_includes_ablations_and_matches_the_design():
    """Sol: ablations stay in the budget until a reduction is actually decided.

    The refused version subtracted them, so its total was 8,047 and "the design
    costs 6.40 hours" silently meant non-ablation training time only. This is
    also the D-033 regression: an off-by-375 must fail loudly.
    """
    acct = design_accounting()
    reference = total_model_fits(design_units())
    assert acct["ablations_included"] is True
    assert acct["total_fits"] == reference["total"] == 8_197, (
        f"{acct['total_fits']} fits against the design's {reference['total']} "
        f"including {reference['ablations']} ablations. Off by 375 means the "
        "accounting has re-acquired D-033's phantom fits"
    )
    assert acct["ablation_assumed_size"] == ABLATION_ASSUMED_SIZE


def test_collection_is_counted_per_condition_not_per_fit():
    acct = design_accounting()
    assert acct["total_collections"] == 2_947
    assert acct["total_collections"] < acct["total_fits"]


def test_data_repair_is_counted_at_its_ten_times_budget():
    acct = design_accounting()
    assert max(acct["fits_by_size"]) == 50_000
    assert acct["fits_by_size"][50_000] > 0


# --- guards -----------------------------------------------------------------


def test_the_harness_never_runs_at_a_registered_stage():
    assert TIMING_STAGE == "pilot"


def test_a_benchmark_below_the_repetition_floor_is_refused():
    with pytest.raises(ValueError, match="repetitions"):
        benchmark_sizes([100], device="cpu", reps=MIN_REPETITIONS - 1)


def _flat_bench(sizes, per_train=1.0, per_collect=0.1):
    out = {}
    for s in sizes:
        b = SizeBenchmark(n_transitions=s)
        b.train_reps_s = [per_train] * MIN_REPETITIONS
        b.collect_reps_s = [per_collect] * MIN_REPETITIONS
        out[s] = b
    return out


def test_extrapolation_charges_unmeasured_sizes_conservatively():
    """An unmeasured size is charged at the nearest measured size AT OR ABOVE."""
    bench = _flat_bench([100, 5000])
    bench[5000].train_reps_s = [10.0] * MIN_REPETITIONS
    acct = {"fits_by_size": {2500: 3}, "collections_by_size": {}}
    out = extrapolate(bench, acct, "median")
    assert out["training_s"] == pytest.approx(3 * 10.0 / K.DEFAULT_ENSEMBLE_SIZE)


def test_the_max_summary_is_never_below_the_median():
    bench = _flat_bench([5000])
    bench[5000].train_reps_s = [1.0, 2.0, 9.0]
    acct = {"fits_by_size": {5000: 10}, "collections_by_size": {5000: 2}}
    assert (extrapolate(bench, acct, "max")["total_s"]
            >= extrapolate(bench, acct, "median")["total_s"])


# --- the reconciliation defect that produced attempt-002 --------------------


def test_reconcile_filters_on_the_unit_not_on_its_size():
    unit = representative_condition()
    plan = execution_plan(design_units())
    mine = [f for f in plan if f.unit == unit]
    same_size = [f for f in plan if f.unit.n_transitions == unit.n_transitions]
    assert len(same_size) > 10 * len(mine), "fixture cannot detect a size filter"

    bench = _flat_bench([unit.n_transitions, unit.n_transitions * 10])
    observed = {
        "unit_n_transitions": unit.n_transitions,
        "seeds_run": sorted({f.seed for f in mine}),
        "arms": sorted({f.arm for f in mine}),
        "measured_s": 100.0,
    }
    out = reconcile(observed, bench, "median", unit=unit)
    expected = (sum(f.members for f in mine) * (1.0 / K.DEFAULT_ENSEMBLE_SIZE)
                + len(mine) * 0.1)
    assert out["predicted_s"] == pytest.approx(expected), (
        "the prediction does not correspond to the fits that actually ran"
    )


# --- the stored evidence ----------------------------------------------------


def test_the_stored_attempt_reconciles_and_is_honestly_labelled():
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    rec = json.loads(ATTEMPT.read_text())
    ratio = rec["reconciliation"]["median"]["ratio_measured_over_predicted"]
    assert 0.5 < ratio < 2.0, (
        f"measured/predicted = {ratio:.3f}: the end-to-end run and the bottom-up "
        "extrapolation disagree by more than a factor of two"
    )
    assert rec["execution_host"]["units"] == "LOCAL WALL-HOURS, not GPU-hours"
    assert rec["execution_host"]["described_by_plan_as"] == "Kaggle T4"
    assert rec["accounting"]["ablations_included"] is True
    assert rec["repetitions"] >= MIN_REPETITIONS
    assert rec["verdict_basis"].startswith("max")
    assert len(rec["raw_by_size"]) == len(design_accounting()["fits_by_size"])
    for row in rec["raw_by_size"]:
        assert len(row["train_reps_s"]) >= MIN_REPETITIONS


def test_the_conservative_total_is_the_one_under_the_trigger():
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    rec = json.loads(ATTEMPT.read_text())
    conservative = rec["extrapolation"]["max"]["total_hours"]
    assert conservative >= rec["extrapolation"]["median"]["total_hours"]
    assert conservative < rec["trigger_gpu_hours"], (
        "the conservative estimate is not under the escalation trigger"
    )


# --- audit findings (D-117) --------------------------------------------------


def test_a_size_above_every_benchmark_is_refused_not_discounted():
    """AUDIT: `_rate` ended `or [max(bench)]`, charging an unmeasured LARGER size
    at the largest MEASURED rate — optimistic, while its docstring claimed to be
    conservative. Unreachable in the current design, which is exactly why it
    would have survived until the design grew a larger size."""
    from bu.experiments.w4_timing import _rate
    bench = _flat_bench([100])
    with pytest.raises(ValueError, match="no benchmark at or above"):
        _rate(bench, 999_999, "median", "fit")


def test_the_stored_record_recomputes_through_the_projects_own_function():
    """AUDIT: JSON has no integer keys, so `fits_by_size` round-tripped as
    STRINGS and feeding a stored record back into `extrapolate` raised
    TypeError. The numbers were right; the record was not auditable without
    hand-coercing it, which is not what "auditable" means."""
    from bu.experiments.w4_timing import recompute_totals
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    stored = json.loads(ATTEMPT.read_text())["extrapolation"]
    got = recompute_totals(ATTEMPT)
    for how in ("median", "max"):
        assert got[how] == stored[how]["total_hours"], (
            f"{how}: recomputed {got[how]} against stored {stored[how]['total_hours']}"
        )


def test_load_record_restores_integer_size_keys():
    from bu.experiments.w4_timing import load_record
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    raw = json.loads(ATTEMPT.read_text())
    assert all(isinstance(k, str) for k in raw["accounting"]["fits_by_size"]), (
        "the raw JSON no longer has string keys, so this test guards nothing"
    )
    loaded = load_record(ATTEMPT)
    assert all(isinstance(k, int) for k in loaded["accounting"]["fits_by_size"])
