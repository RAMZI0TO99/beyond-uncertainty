"""Synthetic metric and persisted-source tests; no actual H2 is computed."""

from dataclasses import replace

import numpy as np
import pytest

from bu import constants as K
from bu.experiments import fit_evidence as F
from bu.experiments import h2_diagnostics as H
from bu.experiments.enumerate_units import design_units
from test_fit_evidence import _completed_run


def test_failure_set_is_strict_and_ratio_is_ratio_of_means():
    error = np.array([0.1, K.FAILURE_THRESHOLD, 1.0, 4.0])
    disagreement = np.array([99., 99., 1., 2.])
    row = H._failure_metrics(error, disagreement)
    assert row['n_failure'] == 2
    assert row['ratio_of_means'] == pytest.approx(1.5 / 2.5)
    assert row['ratio_of_means'] != pytest.approx(np.mean([1., .5]))
    assert row['pearson_r'] == pytest.approx(1.)


def test_pearson_not_rank_correlation():
    error, disagreement = np.array([1., 2., 3., 9.]), np.array([1., 4., 5., 6.])
    row = H._failure_metrics(error, disagreement)
    assert row['pearson_r'] == pytest.approx(np.corrcoef(error, disagreement)[0, 1])
    assert row['pearson_r'] < .9


@pytest.mark.parametrize('error,disagreement,reason', [
    ([1.], [1.], 'fewer_than_two_failure_transitions'),
    ([1., 1.], [1., 2.], 'constant_error_or_disagreement'),
    ([1., 2.], [0., 0.], 'constant_error_or_disagreement'),
])
def test_undefined_correlation_is_not_zero(error, disagreement, reason):
    row = H._failure_metrics(np.array(error), np.array(disagreement))
    assert row['pearson_r'] is None
    assert row['correlation_undefined_reason'] == reason


def test_empty_failure_set_blocks():
    with pytest.raises(ValueError, match='empty strict'):
        H._failure_metrics(np.array([0., K.FAILURE_THRESHOLD]), np.array([1., 2.]))


@pytest.mark.parametrize('bad', [[], [1], np.array([]), np.array([1]),
    np.array([-1.]), np.array([np.nan]), np.array([np.inf]), np.array([[1.]])])
@pytest.mark.parametrize('field', [0, 1])
def test_invalid_arrays_refused(bad, field):
    values = [np.array([1.]), np.array([1.])]
    values[field] = bad
    with pytest.raises(ValueError):
        H._failure_metrics(*values)


def test_mismatched_rows_refused():
    with pytest.raises(ValueError, match='identical'):
        H._failure_metrics(np.array([1., 2.]), np.array([1.]))


def test_finite_extreme_values_do_not_overflow_means_or_pearson():
    row = H._failure_metrics(np.array([1e307, 1e308]), np.array([1e308, 1e307]))
    assert row['ratio_of_means'] == pytest.approx(1.)
    assert row['pearson_r'] == pytest.approx(-1.)


@pytest.fixture
def persisted(tmp_path):
    completed, spec = _completed_run(tmp_path)
    F.write_fit_evidence(completed, fit_dir=tmp_path)
    fit = F.load_fit_evidence(tmp_path, expected_git_commit='b' * 40)
    return H.BaselineDiagnosticSource(tmp_path, 'b' * 40, fit.execution_digest), fit


def test_real_reader_source_binding_and_no_verdict(persisted):
    source, fit = persisted
    row = H.baseline_failure_diagnostic(source, unit=fit.unit, seed=fit.seed)
    assert row['normalisation'] == fit.scale.as_row()
    assert row['n_failure'] == len(fit.error)
    assert row['ratio_of_means'] == pytest.approx(1 / 3)
    assert row['pearson_r'] == pytest.approx(1.)
    assert row['observed_repair_label'] is None and row['h2_verdict'] is None


@pytest.mark.parametrize('field,value', [('expected_git_commit', 'c' * 40),
    ('expected_execution_digest', 'c' * 64), ('expected_execution_digest', 'bad')])
def test_independent_source_pins_are_required(persisted, field, value):
    source, fit = persisted
    with pytest.raises(ValueError):
        H.baseline_failure_diagnostic(replace(source, **{field: value}), unit=fit.unit, seed=fit.seed)


@pytest.mark.parametrize('seed', [True, 0, 999, 1020, '1000', 1000.])
def test_exact_registered_seeds_only(persisted, seed):
    source, fit = persisted
    with pytest.raises(ValueError, match='seed'):
        H.baseline_failure_diagnostic(source, unit=fit.unit, seed=seed)


def test_changed_source_bytes_cannot_reuse_cached_summary(persisted):
    source, fit = persisted
    H.baseline_failure_diagnostic(source, unit=fit.unit, seed=fit.seed)
    path = next(source.path.rglob('metrics.jsonl'))
    path.write_bytes(path.read_bytes() + b'{}\n')
    with pytest.raises(ValueError):
        H.baseline_failure_diagnostic(source, unit=fit.unit, seed=fit.seed)


@pytest.mark.parametrize('ratios', [[1., 2., 3., 4., 5.], [0.] * 5, [1e308] * 5])
def test_mean_sample_sd_across_seeds_not_pooled_transitions(monkeypatch, ratios):
    unit = design_units()[0]
    sources = [object() for _ in range(5)]
    seen = []
    def one(source, *, unit, seed):
        seen.append((source, seed))
        return {'ratio_of_means': ratios[seed - 1000], 'n_failure': (seed - 999) * 100,
                'pearson_r': None}
    monkeypatch.setattr(H, 'baseline_failure_diagnostic', one)
    row = H.condition_failure_diagnostics(sources, unit=unit)
    assert seen == list(zip(sources, range(1000, 1005)))
    scale = max(ratios)
    expected_mean = scale * np.mean(np.array(ratios) / scale) if scale else 0.
    expected_sd = scale * np.std(np.array(ratios) / scale, ddof=1) if scale else 0.
    assert row['ratio_mean_across_seeds'] == pytest.approx(expected_mean)
    assert row['ratio_sample_sd_across_seeds'] == pytest.approx(expected_sd)
    assert row['ratio_sd_ddof'] == 1
    assert row['transitions_pooled_across_seeds'] is False
    assert row['correlations_aggregated'] is False and row['h2_verdict'] is None


@pytest.mark.parametrize('sources', [[], [None] * 3, [None] * 6, iter([None] * 5)])
def test_incomplete_or_extra_seed_inventory_refused(sources):
    with pytest.raises(ValueError, match='ordered registered'):
        H.condition_failure_diagnostics(sources, unit=design_units()[0])
