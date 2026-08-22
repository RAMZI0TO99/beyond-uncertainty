"""The Week 5 Friday labelled-unit class-balancing procedure (S§W5 Fri).

Built on Sol's authorisation of 2026-08-22 as **completion of missed Week 5
scope** — not reserve consumption and not Week 6 execution. It may be exercised
on **synthetic labelled inputs only** until C-005's grouped splitter exists.

What it does, in the order Sol specified:

1. operates **independently within** each split — train, validation, held-out;
2. excludes **ambiguous and undiagnosed** units before balancing;
3. takes ``m = min(#D=0 units, #D=1 units)`` **within that split**;
4. selects exactly ``m`` units per class by a **deterministic stable hash** over
   the frozen seed, split name, label and ``unit_id``;
5. draws **at most** ``CRITIC_TRACE_CAP_PER_UNIT`` eligible traces per selected
   unit, without replacement, from a deterministic per-unit stream;
6. **refuses** a unit with zero eligible traces; **keeps** one with 1–49;
7. keeps ``X``, ``y`` and ``groups`` physically separate;
8. emits a manifest of what was selected, excluded and why;
9. asserts that **no comparison group spans splits** (D-039);
10. preserves the registered **unit-weighted** balanced-accuracy estimand.

**The cap is a maximum, not an eligibility threshold.** A small unit is kept
whole. Excluding it, or resampling it with replacement up to 50, would make unit
inclusion a function of trace count — which is not a registered criterion and
would quietly change the estimand.

**Never ``hash()``.** Python's builtin is randomised per process by
``PYTHONHASHSEED``, so a selection keyed on it is reproducible *within* a run and
irreproducible *across* runs, which is the worst of both: it looks deterministic
and is not. ``blake2b`` over the same fields is stable forever.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

import numpy as np

from .. import constants as K

#: Bumped when the manifest's fields or the selection's meaning change.
BALANCE_SCHEMA_VERSION = 1

#: The two decidable labels. Everything else is excluded before balancing.
ESTIMATION, HYPOTHESIS_CLASS = 0, 1
#: Labels that are not evidence about either repair and never enter the critic.
UNDECIDABLE = ("ambiguous", "undiagnosed")


@dataclass(frozen=True)
class LabelledUnit:
    """One labelled configuration-condition, as the balancer needs to see it."""

    unit_id: str
    label: int | str
    split: str
    comparison_group_id: str
    #: Indices of that unit's eligible failure traces. Never resampled.
    eligible_traces: tuple[int, ...]

    @property
    def n_eligible(self) -> int:
        return len(self.eligible_traces)


@dataclass
class BalancedSplit:
    """One split's selection, with X / y / groups kept physically apart (D-010)."""

    split: str
    X_trace_ids: list[int] = field(default_factory=list)
    y: list[int] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    unit_ids: list[str] = field(default_factory=list)


def _stable_key(*parts: object) -> int:
    """A process-stable ordering key. Explicitly not ``hash()``."""
    payload = "\x1f".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


def _trace_rng(unit_id: str, split: str) -> np.random.Generator:
    """A per-unit stream, derived from the frozen balance seed."""
    seed = _stable_key(K.CRITIC_BALANCE_SEED, "traces", split, unit_id) % (2**32)
    return np.random.default_rng(seed)


def _decidable(unit: LabelledUnit) -> bool:
    return unit.label not in UNDECIDABLE and unit.label in (ESTIMATION, HYPOTHESIS_CLASS)


def assert_groups_do_not_span_splits(units: Iterable[LabelledUnit]) -> None:
    """D-039: a comparison group may never straddle a split.

    Units in one group were *given related data by design*, so a group spanning
    a split leaks between train and held-out no matter how the traces are drawn.
    Checked here rather than assumed, because the balancer accepts split
    assignments it did not make.
    """
    seen: dict[str, str] = {}
    for u in units:
        if u.comparison_group_id in seen and seen[u.comparison_group_id] != u.split:
            raise ValueError(
                f"comparison group {u.comparison_group_id!r} spans splits "
                f"{seen[u.comparison_group_id]!r} and {u.split!r}. Units in one "
                "group share data by design (D-039), so this leaks across the "
                "split boundary regardless of which traces are drawn"
            )
        seen.setdefault(u.comparison_group_id, u.split)


def balance_split(
    units: Sequence[LabelledUnit],
    *,
    split: str,
    cap: int = K.CRITIC_TRACE_CAP_PER_UNIT,
) -> tuple[BalancedSplit, dict]:
    """Balance one split. Returns the selection and its manifest."""
    in_split = [u for u in units if u.split == split]
    excluded_undecidable = [u.unit_id for u in in_split if not _decidable(u)]
    decidable = [u for u in in_split if _decidable(u)]

    empty = [u.unit_id for u in decidable if u.n_eligible == 0]
    if empty:
        raise ValueError(
            f"{len(empty)} unit(s) in split {split!r} have zero eligible failure "
            f"traces: {sorted(empty)[:5]}. A unit that contributes no trace "
            "cannot be balanced over and must not be silently carried"
        )

    by_class = {
        ESTIMATION: [u for u in decidable if u.label == ESTIMATION],
        HYPOTHESIS_CLASS: [u for u in decidable if u.label == HYPOTHESIS_CLASS],
    }
    m = min(len(by_class[ESTIMATION]), len(by_class[HYPOTHESIS_CLASS]))

    selection = BalancedSplit(split=split)
    chosen: dict[int, list[str]] = {}
    per_unit_counts: dict[str, int] = {}
    for label, pool in by_class.items():
        ordered = sorted(
            pool, key=lambda u: _stable_key(K.CRITIC_BALANCE_SEED, split, label, u.unit_id)
        )
        picked = ordered[:m]
        chosen[label] = [u.unit_id for u in picked]
        for u in picked:
            traces = np.asarray(u.eligible_traces)
            if u.n_eligible > cap:
                idx = _trace_rng(u.unit_id, split).choice(u.n_eligible, size=cap,
                                                          replace=False)
                traces = traces[np.sort(idx)]
            per_unit_counts[u.unit_id] = len(traces)
            selection.X_trace_ids.extend(int(t) for t in traces)
            selection.y.extend([label] * len(traces))
            selection.groups.extend([u.comparison_group_id] * len(traces))
            selection.unit_ids.extend([u.unit_id] * len(traces))

    manifest = {
        "schema_version": BALANCE_SCHEMA_VERSION,
        "split": split,
        "cap": cap,
        "balance_seed": K.CRITIC_BALANCE_SEED,
        "units_per_class": m,
        "class_counts_before": {str(k): len(v) for k, v in by_class.items()},
        "selected_units": {str(k): sorted(v) for k, v in chosen.items()},
        "excluded_undecidable": sorted(excluded_undecidable),
        "excluded_by_balancing": sorted(
            u.unit_id for u in decidable
            if u.unit_id not in set(chosen[ESTIMATION]) | set(chosen[HYPOTHESIS_CLASS])
        ),
        "per_unit_trace_counts": dict(sorted(per_unit_counts.items())),
        "units_below_cap": sorted(k for k, v in per_unit_counts.items() if v < cap),
        "comparison_groups": sorted({u.comparison_group_id for u in units
                                     if u.unit_id in per_unit_counts}),
        "n_traces": len(selection.X_trace_ids),
    }
    return selection, manifest


def balance(
    units: Sequence[LabelledUnit],
    *,
    splits: Sequence[str] = ("train", "validation", "held_out"),
    cap: int = K.CRITIC_TRACE_CAP_PER_UNIT,
) -> tuple[dict[str, BalancedSplit], dict[str, dict]]:
    """Balance every split independently, after the cross-split group check."""
    assert_groups_do_not_span_splits(units)
    selections, manifests = {}, {}
    for split in splits:
        selections[split], manifests[split] = balance_split(units, split=split, cap=cap)
    return selections, manifests


def unit_weights(selection: BalancedSplit) -> Mapping[str, float]:
    """Per-trace weights that recover the **unit-weighted** estimand (D-044).

    Balanced accuracy is registered as equal weight per configuration-condition,
    not per trace. A unit capped at 50 and a unit contributing 7 must count the
    same, so each trace carries 1/(that unit's trace count). Returning the
    weights rather than pre-multiplying keeps the estimand visible at the call
    site instead of buried in the array.
    """
    counts: dict[str, int] = {}
    for uid in selection.unit_ids:
        counts[uid] = counts.get(uid, 0) + 1
    return {uid: 1.0 / n for uid, n in counts.items()}
