"""Named random streams (D-030, Sol's Q-008 ruling).

Every source of randomness in the project draws from a **named** stream derived
by hashing, rather than from one generator seeded with an integer. The reason is
not tidiness -- it is that two different requirements pull in opposite
directions and a single seed cannot serve both.

**Independence across units.** Every confidence interval in the thesis is taken
over configuration-conditions (Plan §10.7). If two different units at seed 0
receive correlated object placements -- which they did, because
``GridWorld.reset(seed=s)`` derived its stream from ``s`` alone -- then the
between-unit variance those intervals rest on is understated.

**Pairing within a comparison.** But a data-size sweep is supposed to hold the
generating process fixed and vary only the amount of data; a capacity sweep is
supposed to train on the same datasets; a repair must be evaluated on the same
recorded failure set as its baseline. Hashing everything by
``(unit_id, arm, stage, seed, purpose)`` would deliver independence and destroy
all of that.

So the key depends on what the stream is *for*:

* **Data-generating streams** (environment, policy) key on a
  ``comparison_group_id`` -- the unit's identity with **only the manipulated
  axis removed**. Experiment 1's six dataset sizes therefore share one stream
  and their datasets are nested prefixes of each other; Experiment 2B's five
  capacities train on the same data; Experiment 2A's four confound levels draw
  the same underlying uniforms, so the manipulation changes the confound
  mechanism and nothing else.
* **Model-side streams** (bootstrap, initialisation) key on ``unit_id``, plus
  the ensemble member, because members must differ from one another.
* Sweep-only units have no comparison group, so their key is ``unit_id`` and
  they are independent of everything.

**``arm`` is never part of any key.** A baseline and its repairs must see the
same environment stream and the same recorded failure set (Plan §7.2, step 4) --
that is what makes the acceptance test paired. Note that the key is built from
the *unresolved* unit, so a data repair's 10x dataset is a nested extension of
the baseline's rather than a different draw.

``stage`` is never part of any key either, which is what makes a fit's identity
``(unit, arm, seed)`` and lets one fit discharge several obligations (D-033).
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from . import constants as K
from .config import UNIT_IDENTITY_FIELDS, Config, UnitSpec, _to_plain

#: Versions the derivation below. Streams are comparable only within one
#: version, and it is recorded in every run record. Bump whenever the key
#: construction, the purpose list or the hashing changes -- the numbers a run
#: draws are not reproducible across versions.
STREAM_VERSION = 1

#: The four named streams. Separated so that, for example, drawing a different
#: number of bootstrap samples cannot shift the environment a model trains on.
PURPOSES: tuple[str, ...] = ("env", "policy", "bootstrap", "init")

#: Streams that generate *data*. These key on the comparison group, so that
#: common random numbers survive inside a paired comparison.
DATA_PURPOSES: frozenset[str] = frozenset({"env", "policy"})

#: The axis each canonical experiment manipulates, and therefore the only field
#: removed when forming its comparison group. Preregistered here: which axis is
#: excluded decides which runs share randomness, and deciding that after seeing
#: results would be a researcher degree of freedom of exactly the kind Plan
#: §10.6 exists to close.
MANIPULATED_AXIS: dict[str, str] = {
    "exp1": "n_transitions",
    "exp2a": "confound_rate",
    "exp2b": "hidden_size",
}

#: Which canonical comparison a unit's repair-validation runs belong to. A
#: ladder rung is a rung *of* one of the three experiments, and it should share
#: randomness with that experiment rather than form a group of its own.
_FAMILY_COMPARISON: dict[str, str] = {
    "estimation": "exp1",
    "missing_feature": "exp2a",
    "capacity": "exp2b",
}


def comparison_stage(unit: UnitSpec, stage: str) -> str:
    """The comparison a run participates in, which is not always its stage."""
    if stage in ("repair_validation", "exp3_repairs"):
        return _FAMILY_COMPARISON[unit.family]
    return stage


def comparison_group_id(unit: UnitSpec, stage: str) -> str:
    """Identity of the set of units that share data-generating randomness.

    The unit's registered identity fields with the manipulated axis removed. A
    stage that manipulates nothing -- the configuration sweep -- has no group,
    and falls back to the unit itself, which is the independence case.
    """
    axis = MANIPULATED_AXIS.get(comparison_stage(unit, stage))
    if axis is None:
        return Config(unit=unit).unit_id

    payload = {
        "stream_version": STREAM_VERSION,
        "comparison": comparison_stage(unit, stage),
        "excluded_axis": axis,
        "fields": {
            name: _to_plain(getattr(unit, name))
            for name in UNIT_IDENTITY_FIELDS
            if name != axis
        },
    }
    return _digest(payload)[:12]


def stream_key(
    unit: UnitSpec, stage: str, purpose: str, *, member: int | None = None
) -> dict[str, Any]:
    """The full, inspectable key a stream is derived from.

    Returned rather than hidden so a run record can state exactly what its
    randomness was a function of, and so a reviewer can check that ``arm`` and
    ``stage`` are absent.
    """
    if purpose not in PURPOSES:
        raise ValueError(f"unknown stream purpose {purpose!r}; expected {PURPOSES}")

    key: dict[str, Any] = {
        "stream_version": STREAM_VERSION,
        "purpose": purpose,
    }
    if purpose in DATA_PURPOSES:
        key["group"] = comparison_group_id(unit, stage)
    else:
        key["unit"] = Config(unit=unit).unit_id
    if member is not None:
        key["member"] = int(member)
    return key


def stream(
    unit: UnitSpec,
    stage: str,
    purpose: str,
    seed: int,
    *,
    member: int | None = None,
) -> np.random.Generator:
    """A generator for one named purpose.

    Args:
        unit: the **unresolved** unit. Passing ``effective_unit`` would put the
            repair into the key and break the pairing the acceptance test needs.
        stage: the experimental obligation, used only to find the comparison
            group. It never enters the key itself.
        purpose: one of :data:`PURPOSES`.
        seed: the run's seed. See :func:`is_confirmatory` -- seeds below
            ``CONFIRMATORY_SEED_BASE`` are development data and may not enter a
            confirmatory result (D-034).
        member: ensemble member index, for model-side streams.
    """
    key = dict(stream_key(unit, stage, purpose, member=member), seed=int(seed))
    digest = _digest(key)
    return np.random.default_rng(int(digest[:32], 16))


def is_confirmatory(seed: int) -> bool:
    """Whether a seed may contribute to a confirmatory result (D-034)."""
    return seed >= K.CONFIRMATORY_SEED_BASE


def confirmatory_seeds(n: int) -> tuple[int, ...]:
    """The first ``n`` seeds of the confirmatory range."""
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    return tuple(K.CONFIRMATORY_SEED_BASE + i for i in range(n))


def _digest(payload: dict[str, Any]) -> str:
    import json

    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()
