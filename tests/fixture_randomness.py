"""Test-only input generation; fabricated confirmatory metadata is NOT data.

Evidence-boundary fixtures need registered seed metadata to exercise refusals,
but must not consume the corresponding research input streams. Install this
only alongside explicit fake provenance and untrained model doubles. Nothing
in the production package imports this helper or remaps a study seed.
"""

from bu import constants as K
from bu.env import collect
from bu.streams import DATA_PURPOSES


def use_development_input_streams(monkeypatch):
    original = collect.stream
    calls = []

    def development_stream(unit, stage, purpose, seed, *, member=None):
        if purpose not in DATA_PURPOSES or member is not None:
            raise ValueError("fixture isolation is for input streams only")
        if type(seed) is not int:
            raise ValueError("fixture input seed must be an exact integer")
        actual_seed = seed - K.CONFIRMATORY_SEED_BASE if seed >= K.CONFIRMATORY_SEED_BASE else seed
        if not 0 <= actual_seed < K.CONFIRMATORY_SEED_BASE:
            raise ValueError("fixture seed cannot be mapped into the development partition")
        calls.append((seed, actual_seed, purpose))
        return original(unit, stage, purpose, actual_seed)

    monkeypatch.setattr(collect, "stream", development_stream)
    return calls
