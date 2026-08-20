"""The W4 Friday threshold runner, exercised without spending a single fit.

This calibration freezes a §2 constant permanently, and every failure set,
repair label and H2/H3 claim descends from it. Sol refused the first version
because its public API left result-changing degrees of freedom open, so most of
what these tests assert is what the API **cannot** be made to do.

Nothing here trains a model.
"""

from __future__ import annotations

import hashlib
import inspect
import json

import numpy as np
import pytest

from bu import constants as K
from bu.experiments import w4_threshold as T


# --- the API cannot change the number ---------------------------------------


def test_calibrate_takes_no_result_changing_argument():
    """Sol's refusal list, asserted as absences.

    `units=` could substitute arbitrary reference units; `score_fn=` could
    generate synthetic evidence indistinguishable from real calibration;
    `allow_dirty=True` could produce evidence that does not record its own
    ineligibility; `rng`, `n_per_stratum` and a seed tuple could all be changed
    without any eligibility verifier noticing.
    """
    params = set(inspect.signature(T.calibrate).parameters)
    assert params == {"out_dir", "attempt"}
    for forbidden in ("units", "score_fn", "allow_dirty", "rng", "n_per_stratum", "seeds"):
        assert forbidden not in params


def test_the_frozen_specification_is_what_sol_ruled():
    assert T.THRESHOLD_PERCENTILE == 95.0
    assert T.PERCENTILE_METHOD == "linear"
    assert T.THRESHOLD_SEEDS == (1000, 1001, 1002, 1003, 1004)
    assert T.REQUIRED_CELLS == 45
    assert T.THRESHOLD_THREADS == 4 and T.THRESHOLD_INTEROP_THREADS == 4
    assert T.BALANCE_RNG_SEED == 0
    assert T.REFERENCE_SIZE == 5000


def test_the_stage_is_distinct_from_experiment_one():
    """Reusing exp1 would give a threshold fit the SAME run_id as an exp1 fit."""
    from bu.config import STAGES, seeds_for

    assert T.THRESHOLD_STAGE == "threshold_calibration"
    assert T.THRESHOLD_STAGE in STAGES
    assert seeds_for(T.THRESHOLD_STAGE) == K.SEEDS_THRESHOLD == 5


def test_the_reference_ensemble_is_five_members_not_one():
    """Sol: the downstream mask uses the baseline ENSEMBLE MEAN.

    Calibrating a K=1 error distribution and applying it to K=5 means would
    change the statistic at the threshold boundary.
    """
    from bu.config import TrainConfig

    assert TrainConfig().ensemble_size == K.DEFAULT_ENSEMBLE_SIZE == 5
    src = inspect.getsource(T.score_reference_cell)
    assert "TrainConfig()" in src and "members.mean(dim=0)" in src


def test_the_reference_units_are_fully_observed_and_well_fit():
    for unit in T.reference_units():
        assert unit.withheld_features == ()
        assert unit.family == "estimation"
        assert unit.confound_rate == 0.0
        assert unit.n_transitions == max(K.DATA_SIZES)
    assert len({(u.layout, u.causal_attribute) for u in T.reference_units()}) == 9


# --- the failure rule --------------------------------------------------------


def test_failure_is_strictly_greater_than_the_threshold():
    """At `>=` a transition exactly on the threshold fails; at `>` it does not."""
    errors = np.array([0.4, 0.5, 0.6])
    assert list(T.is_failure(errors, 0.5)) == [False, False, True]


# --- balancing, via the helper that cannot produce an attempt ----------------


def synthetic_arrays(n=200, dominant=None):
    out = {}
    for layout, attr in T.reference_strata():
        if dominant == (layout, attr):
            out[(layout, attr)] = np.full(10_000, 99.0)
        else:
            out[(layout, attr)] = np.linspace(0.0, 1.0, n)
    return out


def test_the_helper_cannot_produce_a_calibration():
    """Sol: synthetic tests behind a helper whose output cannot be frozen."""
    value, selected, per = T._threshold_from_arrays(synthetic_arrays())
    assert isinstance(value, float) and isinstance(selected, dict) and isinstance(per, int)
    assert not isinstance(value, T.ThresholdCalibration)
    # `calibrate` is the ONLY producer of a writable calibration, and it is the
    # function with no result-changing arguments. Asserted on behaviour rather
    # than by grepping the source, which a docstring mention would defeat.
    assert T.write_attempt_producer() is T.calibrate


def test_every_stratum_contributes_equally():
    _, selected, per = T._threshold_from_arrays(synthetic_arrays(n=200))
    assert per == 200
    assert len(selected) == 9
    assert all(len(v) == per for v in selected.values())


def test_the_minimum_stratum_count_is_what_binds():
    arrays = synthetic_arrays(n=200)
    arrays[("sparse", "shape")] = np.linspace(0.0, 1.0, 37)
    _, selected, per = T._threshold_from_arrays(arrays)
    assert per == 37, "balancing must take the MINIMUM available stratum count"


def test_subsampling_is_without_replacement():
    _, selected, per = T._threshold_from_arrays(synthetic_arrays(n=50))
    for idx in selected.values():
        assert len(set(idx)) == len(idx)


def test_the_balancing_is_deterministic_at_rng_seed_zero():
    a = T._threshold_from_arrays(synthetic_arrays())
    b = T._threshold_from_arrays(synthetic_arrays())
    assert a[0] == b[0] and a[1] == b[1]


def test_balancing_caps_an_OVERSIZED_stratum_to_its_share():
    """What balancing actually does: row count, not tail influence."""
    arrays = synthetic_arrays(n=200)
    arrays[("uniform", "shape")] = np.linspace(0.0, 1.0, 10_000)
    _, selected, per = T._threshold_from_arrays(arrays)
    assert per == 200
    assert all(len(v) == 200 for v in selected.values()), (
        "an oversized stratum contributed more rows than its share"
    )


def test_balancing_does_NOT_cap_tail_influence_at_the_95th_percentile():
    """A measured limit of D-035's rule, recorded rather than assumed away.

    One stratum of nine is 11.1% of the balanced pool, and the top 5% is smaller
    than that. So a stratum whose errors are systematically the worst still
    determines the threshold outright -- the global number becomes that
    stratum's own 55th percentile, and balancing changes nothing about it.

    This is not a bug in the balancing; it is what equal-row balancing can and
    cannot buy at this percentile. It matters because P§7.5 forbids the failure
    set being a function of the construction label, and a systematically harder
    layout would reach the threshold by this route. Raised for Sol.
    """
    value, _, per = T._threshold_from_arrays(
        synthetic_arrays(n=200, dominant=("uniform", "shape"))
    )
    assert per == 200
    assert value == pytest.approx(99.0), (
        "if this no longer holds, the balancing rule or the percentile changed "
        "and the limitation recorded in D-097 needs revisiting"
    )


def test_non_finite_errors_invalidate_rather_than_being_dropped():
    """Sol: a crash or non-finite result invalidates the WHOLE attempt."""
    arrays = synthetic_arrays(n=50)
    arrays[("uniform", "shape")] = np.array([np.nan] * 50)
    with pytest.raises(ValueError, match="non-finite"):
        T._threshold_from_arrays(arrays)


def test_empty_input_is_refused():
    with pytest.raises(ValueError, match="nothing to calibrate"):
        T._threshold_from_arrays({})


# --- the attempt protocol ----------------------------------------------------


def test_a_second_attempt_is_refused_while_the_first_stands(tmp_path):
    (tmp_path / "attempt-001").mkdir()
    with pytest.raises(FileExistsError, match="has not been declared invalid"):
        T.assert_may_attempt(tmp_path, attempt="attempt-002")


def test_writing_over_an_existing_attempt_is_refused(tmp_path):
    (tmp_path / "attempt-001").mkdir()
    with pytest.raises(FileExistsError, match="written once"):
        T.assert_may_attempt(tmp_path, attempt="attempt-001")


def test_a_declared_invalid_attempt_permits_a_second(tmp_path):
    first = tmp_path / "attempt-001"
    first.mkdir()
    (first / T.INVALIDATION_FILE).write_text("aborted: wrong threading", encoding="utf-8")
    assert T.assert_may_attempt(tmp_path, attempt="attempt-002").name == "attempt-002"


def test_declaring_invalid_AFTER_reading_the_threshold_is_refused(tmp_path):
    """The ordering is the whole point of the protocol.

    Re-running after seeing a number you did not like, and keeping the second, is
    how a fixed threshold becomes a tuned one. The declaration must predate the
    file that holds the number.
    """
    import os, time

    first = tmp_path / "attempt-001"
    first.mkdir()
    result = first / "threshold_calibration.json"
    result.write_text("{}", encoding="utf-8")
    time.sleep(0.01)
    declaration = first / T.INVALIDATION_FILE
    declaration.write_text("changed my mind", encoding="utf-8")
    os.utime(declaration, (result.stat().st_mtime + 10, result.stat().st_mtime + 10))
    with pytest.raises(ValueError, match="AFTER its threshold was written"):
        T.assert_may_attempt(tmp_path, attempt="attempt-002")


# --- recomputation from stored artefacts -------------------------------------


def fake_attempt(tmp_path, n=40):
    """An attempt directory built from arrays and stub records -- no fitting."""
    attempt = tmp_path / "attempt-001"
    (attempt / "arrays").mkdir(parents=True)
    arrays, cells = {}, []
    rng = np.random.default_rng(7)
    for layout, attr in T.reference_strata():
        pooled = []
        for seed in T.THRESHOLD_SEEDS:
            errs = rng.random(n)
            name = f"{layout}-{attr}-s{seed}.npy"
            path = attempt / "arrays" / name
            np.save(path, errs)
            run_id = f"r-{layout}-{attr}-{seed}"
            rec = attempt / "records" / run_id
            rec.mkdir(parents=True)
            (rec / "run.json").write_text(f'{{"run_id": "{run_id}"}}', encoding="utf-8")
            (rec / "metrics.jsonl").write_text('{"member": 0}\n', encoding="utf-8")
            cells.append({
                "layout": layout, "causal_attribute": attr, "seed": seed,
                "n_transitions": n, "run_id": run_id,
                "config_id": "c", "unit_id": "u", "n_members": 5,
                "errors_file": f"arrays/{name}",
                "errors_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
                "run_record_digest": hashlib.sha256((rec / "run.json").read_bytes()).hexdigest(),
                "member_record_digest": hashlib.sha256((rec / "metrics.jsonl").read_bytes()).hexdigest(),
            })
            pooled.append(errs)
        arrays[(layout, attr)] = np.concatenate(pooled)
    threshold, selected, per = T._threshold_from_arrays(arrays)
    (attempt / "threshold_calibration.json").write_text(json.dumps({
        "threshold": threshold, "percentile": T.THRESHOLD_PERCENTILE,
        "percentile_method": T.PERCENTILE_METHOD, "required_cells": T.REQUIRED_CELLS,
        "seeds": list(T.THRESHOLD_SEEDS),
        "failure_rule": "error > threshold (strict)",
        "balance": {"rng_seed": T.BALANCE_RNG_SEED},
        "reference": {"stage": T.THRESHOLD_STAGE, "size": T.REFERENCE_SIZE,
                      "family": T.REFERENCE_FAMILY, "ensemble_size": 5},
        "threading": {"num_threads": T.THRESHOLD_THREADS,
                      "num_interop_threads": T.THRESHOLD_INTEROP_THREADS},
        "cells": cells, "selected_indices": selected,
    }, indent=2), encoding="utf-8")
    return attempt


def test_the_threshold_recomputes_from_stored_artefacts(tmp_path):
    """A number that cannot be recomputed by someone who was not there is a claim."""
    attempt = fake_attempt(tmp_path)
    stored = json.loads((attempt / "threshold_calibration.json").read_text())["threshold"]
    assert T.recompute_threshold(attempt) == pytest.approx(stored, abs=1e-12)


def test_a_tampered_error_array_is_refused_by_digest(tmp_path):
    attempt = fake_attempt(tmp_path)
    victim = next((attempt / "arrays").glob("*.npy"))
    np.save(victim, np.zeros(40))
    with pytest.raises(ValueError, match="not the ones the threshold was taken over"):
        T.recompute_threshold(attempt)


def test_a_missing_cell_is_refused_on_recomputation(tmp_path):
    attempt = fake_attempt(tmp_path)
    row = json.loads((attempt / "threshold_calibration.json").read_text())
    row["cells"].pop()
    (attempt / "threshold_calibration.json").write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="cells stored but"):
        T.recompute_threshold(attempt)


# --- it freezes nothing ------------------------------------------------------


def test_nothing_here_writes_constants():
    """Freezing is a Change Record (D-035), never a side effect of running this."""
    src = inspect.getsource(T)
    assert "constants.py" not in src.replace("`constants.py`", "")
    assert "open(" not in src


def test_a_fraction_typo_is_not_catchable_and_that_is_recorded_here():
    """The honest limit: 0.95 is a valid percentile and cannot be distinguished.

    Naming this test after a refusal it does not perform would be the
    assertion-easier-to-express trap (D-055). The mitigation is that the
    percentile is now a FROZEN CONSTANT reviewed by Sol, not a caller's argument.
    """
    assert T.THRESHOLD_PERCENTILE == 95.0
    assert "percentile" not in inspect.signature(T.calibrate).parameters


# --- the three execution blockers Sol named (delta 45) ----------------------


@pytest.mark.parametrize("bad", [
    "attempt-1", "attempt-0001", "attempt", "../attempt-001",
    "/tmp/attempt-001", "sub/attempt-001", "attempt-001x",
])
def test_a_free_form_attempt_name_is_refused(tmp_path, bad):
    """A name outside the frozen pattern sits outside prior-attempt discovery."""
    with pytest.raises(ValueError, match="frozen form attempt-NNN"):
        T.assert_may_attempt(tmp_path, attempt=bad)


def test_every_permitted_name_is_visible_to_discovery(tmp_path):
    """The bypass: if a permitted name were not discovered, the policy is void."""
    (tmp_path / "attempt-007").mkdir()
    with pytest.raises(FileExistsError, match="has not been declared invalid"):
        T.assert_may_attempt(tmp_path, attempt="attempt-008")


def test_an_empty_invalidation_file_is_refused(tmp_path):
    """A formality any re-run could satisfy is not a declaration."""
    first = tmp_path / "attempt-001"
    first.mkdir()
    (first / T.INVALIDATION_FILE).write_text("   \n", encoding="utf-8")
    with pytest.raises(ValueError, match="must record WHY"):
        T.assert_may_attempt(tmp_path, attempt="attempt-002")


@pytest.mark.parametrize("field, value, match", [
    ("percentile", 90.0, "percentile"),
    ("percentile_method", "nearest", "percentile method"),
    ("seeds", [1, 2, 3, 4, 5], "seed set"),
    ("failure_rule", "error >= threshold", "failure rule"),
])
def test_recompute_refuses_a_result_taken_under_a_different_rule(tmp_path, field, value, match):
    """It must not read the frozen spec out of the file it is checking."""
    attempt = fake_attempt(tmp_path)
    row = json.loads((attempt / "threshold_calibration.json").read_text())
    row[field] = value
    (attempt / "threshold_calibration.json").write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        T.recompute_threshold(attempt)


def test_recompute_refuses_a_hand_written_selection(tmp_path):
    """THE point of reconstructing rather than reusing the recorded indices."""
    attempt = fake_attempt(tmp_path)
    row = json.loads((attempt / "threshold_calibration.json").read_text())
    key = sorted(row["selected_indices"])[0]
    row["selected_indices"][key] = list(reversed(row["selected_indices"][key]))
    (attempt / "threshold_calibration.json").write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match the one the attempt recorded"):
        T.recompute_threshold(attempt)


def test_recompute_verifies_the_run_and_member_records(tmp_path):
    attempt = fake_attempt(tmp_path)
    row = json.loads((attempt / "threshold_calibration.json").read_text())
    victim = attempt / "records" / row["cells"][3]["run_id"] / "metrics.jsonl"
    victim.write_text('{"member": 99}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="does not match its recorded digest"):
        T.recompute_threshold(attempt)


def test_recompute_refuses_a_wrong_ensemble_size(tmp_path):
    attempt = fake_attempt(tmp_path)
    row = json.loads((attempt / "threshold_calibration.json").read_text())
    row["cells"][0]["n_members"] = 1
    (attempt / "threshold_calibration.json").write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="ensemble size other than"):
        T.recompute_threshold(attempt)


def test_recompute_refuses_unpinned_threading(tmp_path):
    attempt = fake_attempt(tmp_path)
    row = json.loads((attempt / "threshold_calibration.json").read_text())
    row["threading"]["num_interop_threads"] = 8
    (attempt / "threshold_calibration.json").write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="not the pinned"):
        T.recompute_threshold(attempt)
