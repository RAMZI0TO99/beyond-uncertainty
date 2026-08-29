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

import hashlib
import subprocess
import json
import pathlib

import pytest

from bu import constants as K
from bu.experiments.enumerate_units import design_units, execution_plan, total_model_fits
from bu.experiments.w4_timing import (
    ABLATION_ASSUMED_SIZE, MIN_REPETITIONS, SizeBenchmark, TIMING_STAGE,
    TIMING_SCHEMA_VERSION,
    benchmark_sizes, design_accounting, extrapolate, reconcile,
    representative_condition,
)

def _latest_attempt() -> pathlib.Path | None:
    """The newest delivered timing attempt. attempt-002 is superseded: its record
    names a commit that predates the harness it ran, with a dirty tree."""
    found = sorted(pathlib.Path("runs/w4_timing").glob("attempt-*/timing.json"))
    return found[-1] if found else None


ATTEMPT = _latest_attempt() or pathlib.Path("runs/w4_timing/attempt-999/timing.json")


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


def test_no_cross_unit_verdict_is_drawn_against_the_gpu_hour_trigger():
    """Sol, delta 54: the record says its units are LOCAL WALL-HOURS and the
    program then asserted them under a GPU-hour trigger.

    An earlier version of this test asserted `conservative < trigger_gpu_hours`.
    That is a **cross-unit comparison turned into a PASS**, in the one harness
    that exists because a compute condition was already adjudicated on a proxy
    for the quantity it names. The trigger stays as registered-plan metadata; no
    ratio and no verdict are derived from it.
    """
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    rec = json.loads(ATTEMPT.read_text())
    if "comparison_status" not in rec:
        pytest.skip("superseded attempt predates the cross-unit fix")
    assert rec["comparison_status"] == "not adjudicable across hosts"
    assert "registered_trigger_gpu_hours" in rec
    assert "trigger_gpu_hours" not in rec, (
        "the bare field name invites exactly the comparison Sol refused"
    )
    conservative = rec["local_estimate_wall_hours"]["max"]
    assert conservative >= rec["local_estimate_wall_hours"]["median"]



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


def test_the_delivered_attempt_identifies_the_code_that_produced_it():
    """Sol, delta 54: attempt-002 recorded commit f0ac645 with tree_clean=false,
    and f0ac645 PREDATES the harness rebuild. The executed code could not be
    recovered from the record, and tracking the JSON afterwards does not repair
    source provenance."""
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    rec = json.loads(ATTEMPT.read_text())
    if "source_commit" not in rec:
        pytest.skip("superseded attempt predates provenance capture")
    assert rec["source_tree_clean_before_run"] is True, (
        "the delivered attempt ran from a dirty tree, so the harness that "
        "produced it cannot be recovered from its own record"
    )
    assert len(rec["source_commit"]) == 40
    digest = ATTEMPT.parent / "timing.json.sha256"
    assert digest.exists(), "no digest beside the record"


def test_the_digest_sidecar_actually_matches_the_record():
    """Sol, delta 55: the check above asserts only that the FILE EXISTS.

    A sidecar holding the wrong hash, a stale hash, or the word "banana" passed
    it. That is the D-071 shape — a check that passes because the thing it
    checks is missing — in the one artefact whose whole purpose is provenance.
    """
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    sidecar = ATTEMPT.parent / "timing.json.sha256"
    if not sidecar.exists():
        pytest.skip("superseded attempt predates digest capture")
    recorded = sidecar.read_text().split()[0].strip().lower()
    actual = hashlib.sha256(ATTEMPT.read_bytes()).hexdigest()
    assert recorded == actual, (
        f"sidecar records {recorded} but the record hashes to {actual}. The "
        "digest is the only thing binding this file to what Sol certified"
    )


def test_a_wrong_digest_would_be_caught():
    """Could the test above fail? Proved, not assumed (D-055)."""
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    actual = hashlib.sha256(ATTEMPT.read_bytes()).hexdigest()
    assert actual != "banana", "the comparison must be against a real digest"
    assert actual != "0" * 64


def test_certified_attempt_carries_its_schema_correction():
    """attempt-003 stores schema_version 1 but holds version-2 provenance fields.

    It is CERTIFIED and immutable, so the correction is a note beside it. The
    note must be tracked — an untracked correction is the D-041 shape again, and
    `.gitignore`'s attempt allowlist would have swallowed it.
    """
    if not ATTEMPT.exists():
        pytest.skip("timing evidence not present in this checkout")
    rec = json.loads(ATTEMPT.read_text())
    if rec.get("schema_version") == TIMING_SCHEMA_VERSION:
        return  # a future record written under the corrected version
    note = ATTEMPT.parent / "SCHEMA_CORRECTION.md"
    assert note.exists(), (
        f"{ATTEMPT.parent.name} stores schema_version "
        f"{rec.get('schema_version')} while TIMING_SCHEMA_VERSION is "
        f"{TIMING_SCHEMA_VERSION}, and carries no correction note"
    )
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(note)],
                             capture_output=True, text=True)
    assert tracked.returncode == 0, f"{note} exists but is not tracked by git"


def test_git_helper_fails_closed():
    """It swallowed the return code — and the failure is not an empty string.

    `git rev-parse <bad-ref>` echoes the unresolvable ref to stdout and exits
    128, so the old helper returned a plausible-looking 20-character string.
    """
    from bu.experiments.w4_timing import _git
    with pytest.raises(RuntimeError, match="failed with code"):
        _git("rev-parse", "definitely-not-a-ref-xyz")


@pytest.mark.parametrize("bad", [
    "definitely-not-a-ref-xyz",   # what the old helper actually returned
    "",                           # what it was assumed to return
    "60a726e",                    # a short hash
    "60a726ee3c453fea8f177b2fc7c613e1ae0479f",    # 39 chars
    "60a726ee3c453fea8f177b2fc7c613e1ae0479fez",  # 41, non-hex
    "60A726EE3C453FEA8F177B2FC7C613E1AE0479FE",   # uppercase
])
def test_only_a_real_commit_is_accepted_as_provenance(bad):
    from bu.experiments.w4_timing import _require_commit
    with pytest.raises(RuntimeError, match="not a 40-character"):
        _require_commit(bad)


def test_a_real_commit_passes_the_provenance_guard():
    """Rejecting bad values must not also reject the value actually used."""
    from bu.experiments.w4_timing import _git, _require_commit
    head = _git("rev-parse", "HEAD")
    assert _require_commit(head) == head
