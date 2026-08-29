"""The frozen failure threshold (D-107, promoted under the D-035 Change Record).

Sol authorised the promotion on 2026-08-22 after independently extracting the
delivered evidence archive and recomputing the value with NumPy. Its
implementation instructions asked for regression tests on **the exact constant**
and on **boundary behaviour**, and this file is those.

Why the exactness matters enough to pin: every failure set, every repair label,
and therefore H2 and H3 descend from this single number. It is never
recalibrated -- the attempt is final and the threshold has been inspected, so
the invalidation protocol can no longer be satisfied. A rounded copy, or a
boundary that quietly became `>=`, would move a registered endpoint with nothing
raised.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest
import torch

from bu import constants as K
from bu.models.uncertainty import ScaledEvaluation, normalised_error

ATTEMPT = pathlib.Path("runs/w4_threshold/attempt-001")


# --- the constant itself ---------------------------------------------------


def test_the_threshold_is_the_exact_calibrated_value_unrounded():
    """Sol: "Add the exact full-precision constant. Do not round it."

    Compared against the literal *and* its bit pattern, because several decimal
    strings round-trip to different floats and `==` on a rounded copy can still
    pass at lower precision.
    """
    assert K.FAILURE_THRESHOLD == 0.610702633857727
    assert repr(K.FAILURE_THRESHOLD) == "0.610702633857727"
    assert K.FAILURE_THRESHOLD.hex() == "0x1.38ae040000000p-1"


def test_the_threshold_is_a_plain_float_not_a_numpy_scalar():
    """A numpy scalar would carry a dtype into every comparison downstream and
    could silently demote a float64 comparison to float32."""
    assert type(K.FAILURE_THRESHOLD) is float


# --- the boundary ----------------------------------------------------------
#
# "Failure" is error STRICTLY GREATER than the threshold. This is part of the
# registered definition, not a convention -- and it is not academic: two
# transitions in the calibration pool itself sit exactly at the value.


def test_a_transition_exactly_at_the_threshold_is_not_a_failure():
    assert not (K.FAILURE_THRESHOLD > K.FAILURE_THRESHOLD)


def test_the_boundary_is_strict_through_the_real_mask_constructor():
    """Driven through `failure_mask()`, not through a bare `>` in the test.

    An earlier version of this asserted `errors > t` on a tensor the test built
    itself, which tests Python's comparison operator and would pass no matter
    what `failure_mask` did. That is the shape D-055 and D-057 were written
    about. Here the pool is constructed so that one transition's error is
    **exactly** the threshold after the real scale and error computation, and
    the assertion runs on the mask the registered constructor returns — so
    changing `>` to `>=` in the implementation fails this test.

    The pool is `[-1, 1, -1, 1]`, whose population std is exactly 1.0, so the
    normalising scale is exactly 1 and the error is exactly the offset. The
    offsets are one-ULP-scale rather than literal `nextafter` neighbours: a
    single ULP at 0.61 is lost when the value round-trips through a target of
    magnitude 1, which is a property of the arithmetic and not of the rule.
    """
    t = K.FAILURE_THRESHOLD
    eps = 1e-12
    targets = torch.tensor([[-1.0], [1.0], [-1.0], [1.0]], dtype=torch.float64)
    offsets = torch.tensor([t, t + eps, t - eps, 0.0], dtype=torch.float64)
    predictions = targets + offsets.unsqueeze(1)
    ev = ScaledEvaluation.from_pool(
        predictions.unsqueeze(0).repeat(5, 1, 1), targets, n_transitions=4, seed=0
    )

    assert ev.scale.vector.item() == 1.0, "fixture broken: the scale is not 1"
    assert ev.ensemble_mean_error()[0].item() == t, (
        "fixture broken: the first transition's error is no longer EXACTLY the "
        "threshold, so this test would no longer exercise the boundary at all"
    )
    assert ev.failure_mask().tolist() == [False, True, False, False], (
        "the failure rule must be strictly greater: at exact equality the "
        "transition is not a failure"
    )


def test_the_calibration_pool_really_does_contain_boundary_transitions():
    """The strict rule decides real transitions, not a hypothetical one.

    If this ever reads zero, the boundary test above has stopped being a test of
    anything that happens and is only a test of Python's `>`.
    """
    if not ATTEMPT.exists():
        pytest.skip("calibration evidence not present in this checkout")
    record = json.loads((ATTEMPT / "threshold_calibration.json").read_text())
    errors = np.concatenate(
        [np.load(ATTEMPT / cell["errors_file"]) for cell in record["cells"]]
    )
    at_boundary = int((errors == np.float32(K.FAILURE_THRESHOLD)).sum())
    assert at_boundary > 0, (
        "no transition sits at the threshold, so the strict/non-strict "
        "distinction no longer changes any label in the calibration evidence"
    )


# --- the constant against the evidence it came from ------------------------


def test_the_constant_reproduces_the_calibration_evidence():
    """The promoted number must still be what the stored artefacts say.

    This is the regression that would catch the constant being edited to a
    plausible neighbouring value: it recomputes the percentile from the stored
    arrays and the recorded deterministic selection.
    """
    if not ATTEMPT.exists():
        pytest.skip("calibration evidence not present in this checkout")
    record = json.loads((ATTEMPT / "threshold_calibration.json").read_text())

    pooled: dict[str, list[np.ndarray]] = {}
    for cell in sorted(
        record["cells"], key=lambda c: (c["layout"], c["causal_attribute"], c["seed"])
    ):
        key = f"{cell['layout']}|{cell['causal_attribute']}"
        pooled.setdefault(key, []).append(np.load(ATTEMPT / cell["errors_file"]))

    selection = record["selected_indices"]
    balanced = np.concatenate(
        [
            np.concatenate(pooled[key])[np.asarray(selection[key])]
            for key in sorted(selection)
        ]
    )
    assert balanced.size == 36_927, "the balanced pool is not 9 x 4,103"
    assert np.percentile(balanced, 95.0, method="linear") == K.FAILURE_THRESHOLD

    failures = balanced > K.FAILURE_THRESHOLD
    assert failures.sum() == 1_846
    assert 0.0499 < failures.mean() < 0.0501, "the balanced pool is 5% by construction"


def test_the_unbalanced_sanity_check_still_reproduces():
    """Sol's independently computed 1,879 / 37,406 = 5.0232583%.

    **An arithmetic sanity check only, and NOT evidence about stratum
    homogeneity** (corrected under D-109 on Sol's ruling). An earlier version of
    this docstring said the agreement showed "the strata are not wildly
    heterogeneous in the upper tail". It shows nothing of the kind: balancing
    discards just 1.28% of rows, so the balanced and unbalanced pools are very
    nearly the same pool and their agreement is arithmetic. Per-layout
    prevalence in this same evidence differs by 5.53x (D-108).

    What it does check is that the frozen constant still cuts the recorded
    reference pool where it did. Pinned because Sol computed it separately.
    """
    if not ATTEMPT.exists():
        pytest.skip("calibration evidence not present in this checkout")
    record = json.loads((ATTEMPT / "threshold_calibration.json").read_text())
    errors = np.concatenate(
        [np.load(ATTEMPT / cell["errors_file"]) for cell in record["cells"]]
    )
    assert errors.size == 37_406
    assert int((errors > K.FAILURE_THRESHOLD).sum()) == 1_879


# --- the registered mask constructor ---------------------------------------


def _evaluation(seed: int = 0, pool: int = 400):
    g = torch.Generator().manual_seed(seed)
    targets = torch.randn(pool, 2, generator=g)
    members = torch.randn(5, pool, 2, generator=g) * 0.3 + targets
    return ScaledEvaluation.from_pool(members, targets, n_transitions=pool, seed=seed)


def test_the_mask_is_exactly_the_frozen_rule_applied_to_the_pool():
    ev = _evaluation()
    expected = normalised_error(ev.members.mean(dim=0), ev.targets, ev.scale) > (
        K.FAILURE_THRESHOLD
    )
    assert torch.equal(ev.failure_mask(), expected)
    assert ev.failure_mask().dtype == torch.bool


def test_no_caller_can_supply_a_threshold():
    """Sol required construction with **no caller-selectable override**.

    Asserted by *calling* it with one and requiring refusal, rather than by
    inspecting the signature for an absent parameter name -- that shape of
    assertion is what D-055 and D-057 were written about, and it passes whether
    or not the property holds. This fails the moment anyone adds
    `failure_mask(self, threshold=...)`.
    """
    ev = _evaluation()
    with pytest.raises(TypeError):
        ev.failure_mask(0.5)
    with pytest.raises(TypeError):
        ev.failure_mask(threshold=0.5)


def test_the_mask_scores_the_ensemble_mean_prediction_not_the_mean_member_error():
    """The two are different numbers, and the threshold was calibrated on the
    first. Masking with the second would silently move the failure rate."""
    ev = _evaluation()
    mean_of_errors = torch.stack(
        [normalised_error(m, ev.targets, ev.scale) for m in ev.members]
    ).mean(dim=0)
    assert not torch.allclose(ev.ensemble_mean_error(), mean_of_errors), (
        "the two error definitions coincide on this fixture, so this test can no "
        "longer detect the substitution it exists to detect"
    )
    assert torch.equal(ev.failure_mask(), ev.ensemble_mean_error() > K.FAILURE_THRESHOLD)


def test_an_empty_failure_set_fails_closed_rather_than_returning_nan():
    """A model that never exceeds the threshold has no failure set. `masked`
    refuses it instead of producing a nan summary (D-102's shape)."""
    g = torch.Generator().manual_seed(3)
    targets = torch.randn(200, 2, generator=g)
    ev = ScaledEvaluation.from_pool(
        targets.unsqueeze(0).repeat(5, 1, 1), targets, n_transitions=200, seed=0
    )
    mask = ev.failure_mask()
    assert not bool(mask.any()), "a perfect model should have no failures"
    with pytest.raises(ValueError, match="selects no transitions"):
        ev.masked(mask)
