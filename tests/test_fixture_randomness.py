"""Prove engineering fixtures cannot request actual confirmatory input RNGs."""

import numpy as np
import pytest

from bu.config import UnitSpec
from bu.env import collect
from fixture_randomness import use_development_input_streams


def test_fixture_requests_only_development_seeds_and_keeps_metadata(monkeypatch):
    called = []
    def sentinel(unit, stage, purpose, seed, *, member=None):
        assert 0 <= seed < 1000
        called.append(seed)
        return np.random.default_rng(seed)
    monkeypatch.setattr(collect, 'stream', sentinel)
    receipts = use_development_input_streams(monkeypatch)
    unit = UnitSpec(n_transitions=20)
    data = collect.collect(unit, seed=1001, stage='config_sweep')
    assert data.seed == 1001  # Explicitly fabricated evidence-boundary metadata.
    assert called == [1, 1]
    assert len(receipts) == 2 and all(actual == 1 for _, actual, _ in receipts)


def test_real_development_stream_is_used_without_reentering_confirmatory_partition(monkeypatch):
    original = collect.stream
    unit = UnitSpec(n_transitions=20)
    expected = original(unit, 'config_sweep', 'env', 2).random(10)
    use_development_input_streams(monkeypatch)
    actual = collect.stream(unit, 'config_sweep', 'env', 1002).random(10)
    assert np.array_equal(actual, expected)


@pytest.mark.parametrize('seed', [-1, 2000, True, '1000'])
def test_invalid_fixture_seed_refused(monkeypatch, seed):
    use_development_input_streams(monkeypatch)
    with pytest.raises(ValueError):
        collect.stream(UnitSpec(), 'config_sweep', 'env', seed)
