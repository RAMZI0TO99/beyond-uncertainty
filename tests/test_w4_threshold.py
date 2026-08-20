"""The W4 Friday threshold runner, exercised without spending a single fit.

This calibration freezes a §2 constant permanently, and every failure set,
repair label and H2/H3 claim descends from it. Sol's instruction was to build it
and return it for pre-execution review, so these tests exist to show what the
machinery refuses -- not to produce a number.

Every test here substitutes a synthetic scorer. Nothing below trains a model.
"""

from __future__ import annotations

import numpy as np
import pytest

from bu import constants as K
from bu.experiments import w4_threshold as T

CONF = (K.CONFIRMATORY_SEED_BASE, K.CONFIRMATORY_SEED_BASE + 1)


def fake_scorer(values_by_stratum=None, n=200):
    """A scorer that spends no compute. Errors are deterministic per stratum."""
    def score(unit, *, seed):
        key = (unit.layout, unit.causal_attribute)
        base = (values_by_stratum or {}).get(key, 1.0)
        return T.StratumErrors(
            layout=unit.layout, causal_attribute=unit.causal_attribute, seed=seed,
            errors=np.linspace(0.0, base, n), run_id=f"r-{key}-{seed}",
            config_id="c", unit_id="u",
        )
    return score


def calibrate(**kw):
    kw.setdefault("percentile", 90.0)
    kw.setdefault("seeds", CONF)
    kw.setdefault("score_fn", fake_scorer())
    kw.setdefault("allow_dirty", True)
    return T.calibrate(**kw)


# --- the percentile is a deliberate choice, not a default -------------------


def test_the_percentile_has_no_default():
    """P§10.1 does not name it and D-035 lists it among W4 Friday's freezes.

    A default would make the single most consequential choice in this module
    silently, in code. `calibrate` must not be callable without it.
    """
    with pytest.raises(TypeError):
        T.calibrate(seeds=CONF, score_fn=fake_scorer(), allow_dirty=True)


@pytest.mark.parametrize("bad", [0.0, 100.0, -5.0, 150.0])
def test_a_percentile_outside_the_open_unit_range_is_refused(bad):
    with pytest.raises(ValueError, match="percentile must lie in"):
        calibrate(percentile=bad)


def test_a_fraction_typo_is_NOT_catchable_and_that_is_recorded_here():
    """The honest limit of the guard, stated rather than implied.

    0.9 is a plausible typo for 90 and would put the threshold near the bottom of
    the error distribution, labelling almost everything a failure. It is also a
    perfectly valid percentile, so no validation can distinguish it from an
    intentional choice. Naming this test after a refusal it does not perform
    would be the assertion-easier-to-express trap (D-055); the mitigation is that
    the percentile is a reviewed, frozen decision, not that code catches it.
    """
    assert calibrate(percentile=0.9).threshold < calibrate(percentile=90.0).threshold


# --- C-007: confirmatory seeds only (D-034) ---------------------------------


def test_development_seeds_are_refused():
    """D-034 excludes them permanently, and this threshold is frozen forever."""
    with pytest.raises(ValueError, match="below CONFIRMATORY_SEED_BASE"):
        calibrate(seeds=(0, 1, 2))


def test_a_single_development_seed_among_confirmatory_ones_is_refused():
    """The guard must catch contamination, not just an all-development call."""
    with pytest.raises(ValueError, match=r"\[7\]"):
        calibrate(seeds=(K.CONFIRMATORY_SEED_BASE, 7))


def test_duplicate_seeds_are_refused():
    with pytest.raises(ValueError, match="duplicate seeds"):
        calibrate(seeds=(K.CONFIRMATORY_SEED_BASE, K.CONFIRMATORY_SEED_BASE))


def test_no_seeds_is_refused():
    with pytest.raises(ValueError, match="nothing to calibrate"):
        calibrate(seeds=())


# --- the balanced pool (D-035) ----------------------------------------------


def test_every_stratum_contributes_equally():
    """Otherwise the threshold is a function of incidental pool composition."""
    result = calibrate()
    assert len(result.strata) == 9
    assert result.n_total == result.n_per_stratum * 9


def test_a_short_stratum_is_refused_rather_than_quietly_under_contributing():
    cells = [
        T.StratumErrors(layout=l, causal_attribute=a, seed=CONF[0],
                        errors=np.zeros(5 if (l, a) == ("sparse", "shape") else 100),
                        run_id="r", config_id="c", unit_id="u")
        for l, a in T.reference_strata()
    ]
    with pytest.raises(ValueError, match="exceeds the 5 transitions available"):
        T.balance(cells, n_per_stratum=50)


def test_balancing_never_samples_with_replacement():
    """With replacement, a short stratum would silently pass the count check."""
    cells = [
        T.StratumErrors(layout=l, causal_attribute=a, seed=CONF[0],
                        errors=np.arange(100, dtype=float), run_id="r",
                        config_id="c", unit_id="u")
        for l, a in T.reference_strata()
    ]
    pooled, n = T.balance(cells, n_per_stratum=100)
    per = np.split(pooled, 9)
    for chunk in per:
        assert len(np.unique(chunk)) == 100


def test_a_dominant_stratum_cannot_drag_the_threshold():
    """The property balancing exists for, asserted on the number itself."""
    lopsided = [
        T.StratumErrors(layout=l, causal_attribute=a, seed=CONF[0],
                        errors=(np.full(10_000, 99.0) if (l, a) == ("uniform", "shape")
                                else np.linspace(0.0, 1.0, 100)),
                        run_id="r", config_id="c", unit_id="u")
        for l, a in T.reference_strata()
    ]
    pooled, n = T.balance(lopsided, n_per_stratum=100)
    assert n == 100
    # One stratum of 100 nines among 900 values cannot move the 50th percentile.
    assert float(np.percentile(pooled, 50)) < 1.0


# --- the number is evidence, not a constant ---------------------------------


def test_the_percentile_is_actually_applied():
    result = calibrate(percentile=50.0, score_fn=fake_scorer({}, n=101))
    assert result.threshold == pytest.approx(0.5, abs=1e-9)


def test_calibrating_does_not_write_constants():
    """Freezing is a Change Record (D-035), never a side effect of running this."""
    from pathlib import Path
    import bu.constants as C

    path = Path(C.__file__)
    before = path.read_bytes()
    calibrate()
    assert path.read_bytes() == before


def test_evidence_is_written_once(tmp_path):
    result = calibrate()
    T.write_evidence(result, tmp_path)
    with pytest.raises(FileExistsError, match="calibrated once"):
        T.write_evidence(result, tmp_path)


def test_the_evidence_records_what_would_be_needed_to_refuse_it(tmp_path):
    import json

    result = calibrate()
    row = json.loads(T.write_evidence(result, tmp_path).read_text())
    for key in ("threshold", "percentile", "n_per_stratum", "seeds", "commit",
                "reference_family", "reference_size", "stage", "cells"):
        assert key in row, f"{key} missing; the number could not be audited"
    assert len(row["cells"]) == 9 * len(CONF)


def test_a_dirty_tree_is_refused(monkeypatch):
    """The gate's rule, for a stronger reason: this one cannot be re-run.

    Forced rather than depending on the tree the suite happens to run against,
    so the refusal is exercised on every machine (D-028's lesson).
    """
    from bu.runrecord import GitState

    monkeypatch.setattr(T, "git_state",
                        lambda: GitState(commit="b" * 40, dirty=True, branch="main"))
    with pytest.raises(ValueError, match="dirty"):
        T.calibrate(percentile=90.0, seeds=CONF, score_fn=fake_scorer(),
                    allow_dirty=False)


# --- the reference condition ------------------------------------------------


def test_the_reference_units_are_fully_observed_and_well_fit():
    """P§10.1's 'well-fit reference model in the same environment', as read here."""
    for unit in T.reference_units():
        assert unit.withheld_features == ()
        assert unit.family == "estimation"
        assert unit.confound_rate == 0.0
        assert unit.n_transitions == max(K.DATA_SIZES)


def test_the_reference_set_covers_every_stratum_exactly_once():
    units = T.reference_units()
    seen = {(u.layout, u.causal_attribute) for u in units}
    assert len(units) == len(seen) == 9


def test_the_stage_is_a_registered_one_and_not_newly_minted():
    from bu.config import STAGES

    assert T.THRESHOLD_STAGE in STAGES
