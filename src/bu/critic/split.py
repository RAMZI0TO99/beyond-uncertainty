"""C-005 — the grouped critic splitter (docs/c005_c007_spec.md; D-128, D-129).

Partitions attempted labelled configuration-conditions into the three canonical
splits so the clustering the design created is respected: units given related
data by design — a comparison group — never straddle a train/evaluation
boundary (D-039). The spec's four ordered steps, kept **distinct** (Sol,
delta 61 — eligibility and balancing must never be silently combined):

1. **split ALL attempted units** by whole comparison group, so every unit has
   complete provenance — ambiguous and undiagnosed included;
2. **report** ambiguous and undiagnosed counts **per split**;
3. **exclude ineligible labels** at an explicit eligibility boundary
   (:func:`eligible_units`) — only observed ``0``/``1`` records pass;
4. hand only the surviving observed-decidable records to the UNMODIFIED
   certified balancer (``bu.critic.balance``), which balances and performs no
   eligibility selection along this path.

The distinction this module is built on (D-128): ``intended_class`` is
**construction provenance** — the axis a unit was *built* on — and is
deliberately a named string. ``observed_label`` is the **repair-derived critic
target** — integers ``0``/``1`` or ``"ambiguous"``/``"undiagnosed"``. The two
value sets are disjoint on purpose, so a transposed field fails validation
loudly in both directions instead of silently swapping. Everything about
balance, adequacy and ``min(N0, N1)`` is decided on the **observed** label;
intended class is a reporting diagnostic only.

Split names are imported from ``balance.CANONICAL_SPLITS``, never redefined —
two sources for three names is how a ``held-out``/``held_out`` typo becomes
silent data loss (Sol, delta 54/55). The keyed ordering hash is
``balance._stable_key`` — imported rather than reimplemented, so the project
has exactly one blake2b keying implementation; a private import was judged the
lesser evil against a second copy that could drift (D-115: never ``hash()``,
which is process-randomised). Every guard raises ``ValueError``, never a bare
``assert`` — assertions vanish under ``-O`` (D-059). The manifest schema is
versioned from 1 before any real manifest exists (D-121).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from numbers import Integral
from typing import Iterable, Mapping, Sequence

from .. import constants as K
from ..config import STAGES
from ..streams import assert_confirmatory
from .balance import (
    CANONICAL_SPLITS,
    ESTIMATION,
    HYPOTHESIS_CLASS,
    UNDECIDABLE,
    LabelledUnit,
    _stable_key,
    assert_canonical_splits,
)

#: Versions the split manifest. Bumped whenever fields OR their meaning change,
#: **before** any real manifest exists — the D-121 lesson, learned on version 1
#: of the balance schema, which changed its accepted-input semantics without a
#: bump and left a stored artefact ambiguous.
SPLIT_SCHEMA_VERSION = 1

#: The two construction-provenance values (D-128). DELIBERATELY strings, not
#: the integers 0/1: ``observed_label`` uses integers (plus ``ambiguous`` /
#: ``undiagnosed``), so the two class concepts have disjoint value sets and a
#: transposed field fails validation loudly in both directions instead of
#: silently swapping — the exact conflation Sol's delta-61 review corrected.
INTENDED_CLASSES: tuple[str, str] = ("estimation", "hypothesis_class")


@dataclass(frozen=True)
class SplitCandidate:
    """One attempted labelled configuration-condition, as the splitter sees it.

    ``intended_class`` is construction provenance (one of
    :data:`INTENDED_CLASSES`); ``observed_label`` is the repair-derived critic
    target (``0`` | ``1`` | ``"ambiguous"`` | ``"undiagnosed"``, plan Table 2).
    They are different concepts with deliberately disjoint value sets, stated
    once in the spec's opening section and enforced here (D-128).
    """

    unit_id: str
    comparison_group_id: str
    intended_class: str
    observed_label: int | str
    #: Provenance C-007 needs: the stage that produced the labelling runs.
    stage: str
    #: Seeds used by labelling; all must be confirmatory (D-034).
    label_seeds: tuple[int, ...]


@dataclass(frozen=True)
class ObservedTarget:
    """An inclusive per-split, per-OBSERVED-class allocation range."""

    lo: int
    hi: int


@dataclass(frozen=True)
class SplitFloor:
    """An adequacy floor stated on surviving observed-decidable units (DEV-012).

    Field names carry ``observed`` so no adequacy statement can be read as
    intended-class (D-128; the spec's manifest rule).
    """

    #: Lower bound on N0 + N1 surviving observed-decidable units.
    min_surviving_observed: int
    #: Lower bound on min(N0, N1) ON OBSERVED LABELS (the W5 MDE floor).
    min_observed_per_class: int


@dataclass(frozen=True)
class SplitTargets:
    """The registered per-split allocation parameters (D-115 precedent).

    Numeric values are deliberately NOT fixed here — the spec defers them to
    their own Change Record — so the object is a caller argument for synthetic
    exercise. ``floors`` must contain ``held_out`` (P§10.7's floor is mandatory
    there); train/validation floors apply only if separately registered and are
    never inferred.
    """

    observed: Mapping[str, Mapping[int, ObservedTarget]]
    floors: Mapping[str, SplitFloor]


# --- validation, all fail-closed before any output exists --------------------


def _require_exact_int(value: object, *, what: str) -> int:
    """An exact non-boolean non-negative integer, refused otherwise.

    The delta-55 lesson applied outside trace ids: ``True == 1`` and ``4.9``
    truncates, so booleans are refused BEFORE the integer check and floats are
    never coerced.
    """
    if isinstance(value, bool):
        raise ValueError(
            f"{what} is the boolean {value!r}. `True == 1` in Python and `bool` "
            "subclasses `int`, so a boolean would silently become the integer 1 "
            "(Sol, delta 54/55; D-059 fail-closed discipline)"
        )
    if not isinstance(value, Integral):
        raise ValueError(
            f"{what} is {value!r} ({type(value).__name__}); it must be an exact "
            "integer. A float truncates and a string parses, neither of which "
            "raises (Sol, delta 55)"
        )
    if int(value) < 0:
        raise ValueError(f"{what} is negative ({int(value)}); counts and bounds "
                         "on units cannot be negative (Sol, delta 55)")
    return int(value)


def validate_targets(targets: SplitTargets) -> None:
    """Refuse malformed or non-canonical targets before anything is assigned.

    A missing split cannot lawfully absorb units when assignment is total and
    exclusive, and an extra name is non-canonical — the delta-54/55 mirror of
    the balancer's split-name history.
    """
    if not isinstance(targets, SplitTargets):
        raise ValueError(
            f"targets must be a SplitTargets, got {type(targets).__name__}. A "
            "bare mapping is refused positively rather than dying in an "
            "AttributeError (D-054)"
        )
    if not isinstance(targets.observed, Mapping):
        raise ValueError(
            f"targets.observed must be a mapping, got "
            f"{type(targets.observed).__name__} (D-054)"
        )
    if not isinstance(targets.floors, Mapping):
        raise ValueError(
            f"targets.floors must be a mapping, got "
            f"{type(targets.floors).__name__} (D-054)"
        )
    assert_canonical_splits(targets.observed.keys())
    if set(targets.observed.keys()) != set(CANONICAL_SPLITS):
        missing = sorted(set(CANONICAL_SPLITS) - set(targets.observed.keys()))
        raise ValueError(
            f"targets declare no observed range for split(s) {missing}. "
            "Assignment is total and exclusive over all attempted units, so a "
            "split without a declared range cannot lawfully absorb units "
            "(docs/c005_c007_spec.md; D-039, D-118)"
        )
    for split_name, ranges in targets.observed.items():
        if not isinstance(ranges, Mapping):
            raise ValueError(
                f"targets[{split_name!r}] must map observed classes to "
                f"ObservedTarget values, got {type(ranges).__name__} (D-054)"
            )
        keys = set()
        for cls in ranges:
            keys.add(_require_exact_int(cls, what=f"targets[{split_name!r}] class key"))
        if keys != {ESTIMATION, HYPOTHESIS_CLASS}:
            raise ValueError(
                f"targets[{split_name!r}] declares observed class keys "
                f"{sorted(keys)}; they must be exactly the integers "
                f"{{{ESTIMATION}, {HYPOTHESIS_CLASS}}} — targets are stated on "
                "OBSERVED labels, never on intended classes (D-128)"
            )
        for cls, rng in ranges.items():
            if not isinstance(rng, ObservedTarget):
                raise ValueError(
                    f"targets[{split_name!r}][{cls}] must be an ObservedTarget, "
                    f"got {type(rng).__name__} (D-054)"
                )
            lo = _require_exact_int(rng.lo, what=f"targets[{split_name!r}][{cls}].lo")
            hi = _require_exact_int(rng.hi, what=f"targets[{split_name!r}][{cls}].hi")
            if lo > hi:
                raise ValueError(
                    f"targets[{split_name!r}][{cls}] has lo={lo} > hi={hi}; an "
                    "empty range can never be hit and would refuse every "
                    "allocation while looking like a declared target"
                )
    assert_canonical_splits(targets.floors.keys())
    if "held_out" not in targets.floors:
        raise ValueError(
            "targets.floors lacks 'held_out'. The held-out floor on surviving "
            "observed-decidable units is the registered adequacy requirement "
            "(P§10.7, DEV-012) and must be declared; train/validation floors "
            "are optional and are NEVER inferred from it "
            "(docs/c005_c007_spec.md)"
        )
    for split_name, floor in targets.floors.items():
        if not isinstance(floor, SplitFloor):
            raise ValueError(
                f"floors[{split_name!r}] must be a SplitFloor, got "
                f"{type(floor).__name__} (D-054)"
            )
        min_surviving = _require_exact_int(
            floor.min_surviving_observed,
            what=f"floors[{split_name!r}].min_surviving_observed",
        )
        min_class = _require_exact_int(
            floor.min_observed_per_class,
            what=f"floors[{split_name!r}].min_observed_per_class",
        )
        hi0 = int(targets.observed[split_name][ESTIMATION].hi)
        hi1 = int(targets.observed[split_name][HYPOTHESIS_CLASS].hi)
        if min_class > min(hi0, hi1):
            raise ValueError(
                f"floors[{split_name!r}].min_observed_per_class={min_class} "
                f"exceeds an observed-class upper bound (hi0={hi0}, hi1={hi1}); "
                "the registration is intrinsically contradictory before any "
                "groups are allocated"
            )
        if min_surviving > hi0 + hi1:
            raise ValueError(
                f"floors[{split_name!r}].min_surviving_observed={min_surviving} "
                f"exceeds hi0+hi1={hi0 + hi1}; the registration is "
                "intrinsically contradictory before allocation"
            )


def validate_candidates(candidates: Sequence[SplitCandidate]) -> None:
    """Refuse malformed input before any output exists (delta-54/55 history)."""
    if not candidates:
        raise ValueError(
            "refusing to split zero attempted units: an empty mapping is "
            "returned by a splitter that ran perfectly, so nothing downstream "
            "would raise — it would simply assign nothing (D-117, D-118)"
        )
    seen: set[str] = set()
    for c in candidates:
        if not isinstance(c, SplitCandidate):
            raise ValueError(
                f"candidate {c!r} is a {type(c).__name__}, not a SplitCandidate. "
                "Unknown input shapes are refused positively rather than dying "
                "in an AttributeError (D-054)"
            )
        if not isinstance(c.unit_id, str) or not c.unit_id.strip():
            raise ValueError(
                f"candidate unit_id {c.unit_id!r} is not a non-blank string. "
                "The statistical-unit content hash must travel as an explicit "
                "identifier; an empty or non-string id cannot be joined safely "
                "(D-033, D-054)"
            )
        if c.unit_id in seen:
            raise ValueError(
                f"duplicate unit_id {c.unit_id!r}. `unit_id` is a content hash, "
                "so this is one statistical unit twice; assigned twice it could "
                "reach two splits — training and evaluating on the same "
                "configuration (Sol, delta 54; D-033, D-039)"
            )
        seen.add(c.unit_id)
        if isinstance(c.observed_label, bool):
            raise ValueError(
                f"unit {c.unit_id!r} has boolean observed_label "
                f"{c.observed_label!r}. `True == 1` in Python, so this would "
                "silently become a hypothesis-class OBSERVED label. Use the "
                f"integers {ESTIMATION} and {HYPOTHESIS_CLASS} (Sol, delta 54; "
                "D-128)"
            )
        if not (
            (isinstance(c.observed_label, Integral)
             and int(c.observed_label) in (ESTIMATION, HYPOTHESIS_CLASS))
            or c.observed_label in UNDECIDABLE
        ):
            raise ValueError(
                f"unit {c.unit_id!r} has observed_label {c.observed_label!r} "
                f"({type(c.observed_label).__name__}). Valid observed labels "
                f"are the integers {ESTIMATION} and {HYPOTHESIS_CLASS}, or "
                f"{' / '.join(UNDECIDABLE)}. A string '0' is NOT the integer 0 "
                "and must not be quietly treated as undecidable (Sol, delta 54; "
                "D-128)"
            )
        if isinstance(c.intended_class, (bool, Integral)) or (
            c.intended_class not in INTENDED_CLASSES
        ):
            raise ValueError(
                f"unit {c.unit_id!r} has intended_class {c.intended_class!r} "
                f"({type(c.intended_class).__name__}). intended_class is "
                "construction provenance and is deliberately a named string "
                f"from {list(INTENDED_CLASSES)}, not an integer, so it can "
                "never be transposed with the observed repair-derived label "
                "(D-128)"
            )
        if (not isinstance(c.comparison_group_id, str)
                or not c.comparison_group_id.strip()):
            raise ValueError(
                f"unit {c.unit_id!r} has comparison_group_id "
                f"{c.comparison_group_id!r}. A blank or non-string group id "
                "would silently make a unit its own group and evade the D-039 "
                "clustering the splitter exists to respect"
            )
        if not isinstance(c.stage, str) or c.stage == "unknown" or c.stage not in STAGES:
            raise ValueError(
                f"unit {c.unit_id!r} carries stage {c.stage!r}, which is "
                f"missing, 'unknown', or not a registered stage {list(STAGES)}. "
                "Stage metadata is refused, not defaulted (C-007; D-034)"
            )
        if c.stage == "pilot":
            raise ValueError(
                f"unit {c.unit_id!r} carries stage 'pilot'. Pilot output travels "
                "the development road and dead-ends before every critic path, "
                "even when someone used a confirmatory-range seed (C-007; D-034)"
            )
        if not isinstance(c.label_seeds, tuple) or not c.label_seeds:
            raise ValueError(
                f"unit {c.unit_id!r} has label_seeds {c.label_seeds!r}; a "
                "non-empty tuple of seeds is required. A unit with no recorded "
                "labelling seeds has provenance that cannot be classified and "
                "is refused, not defaulted (C-007; D-034)"
            )
        for s in c.label_seeds:
            _require_exact_int(s, what=f"unit {c.unit_id!r} label seed")
        assert_confirmatory(
            c.label_seeds, what=f"split candidate {c.unit_id!r} (a critic path)"
        )


def assert_intended_class_purity(candidates: Iterable[SplitCandidate]) -> None:
    """Refuse a comparison group spanning two INTENDED classes.

    A group carries one intended class by construction — units in one group are
    built on one axis — so mixing is a construction-integrity error. OBSERVED
    label mixing within a group is scientific information and is never refused
    (docs/c005_c007_spec.md assignment semantics; D-128). Shape mirrors
    ``balance.assert_groups_do_not_span_splits``.
    """
    seen: dict[str, str] = {}
    for c in candidates:
        prior = seen.setdefault(c.comparison_group_id, c.intended_class)
        if prior != c.intended_class:
            raise ValueError(
                f"comparison group {c.comparison_group_id!r} mixes intended "
                f"classes {sorted({prior, c.intended_class})}: a "
                "construction-integrity error — units in one group are built "
                "on one axis (D-128, D-039). OBSERVED-label mixing within a "
                "group is scientific information and is never refused"
            )


def input_digest(candidates: Sequence[SplitCandidate]) -> str:
    """sha256 over the canonical JSON of the records, sorted by unit_id.

    Public so the D-072 manifest cross-check can recompute the digest from the
    bytes delivered, independently of the manifest that reports it.
    """
    records = [
        {
            "unit_id": c.unit_id,
            "comparison_group_id": c.comparison_group_id,
            "intended_class": c.intended_class,
            "observed_label": (c.observed_label if isinstance(c.observed_label, str)
                               else int(c.observed_label)),
            "stage": c.stage,
            "label_seeds": [int(s) for s in c.label_seeds],
        }
        for c in sorted(candidates, key=lambda c: c.unit_id)
    ]
    blob = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _split_seed() -> int:
    """The registered split seed, fail-closed when unregistered.

    ``constants.py`` is not modified by this implementation: the spec names
    CRITIC_SPLIT_SEED as requiring its own Change Record in DECISIONS.md
    (D-115 precedent), and a defaulted or caller-supplied seed is a frozen
    constant callers can replace, which is not frozen (Sol, delta 54).
    """
    seed = getattr(K, "CRITIC_SPLIT_SEED", None)
    if seed is None or isinstance(seed, bool) or not isinstance(seed, Integral):
        raise ValueError(
            "the split seed is not yet registered: bu.constants.CRITIC_SPLIT_SEED "
            f"is {seed!r}. It requires its own Change Record in DECISIONS.md "
            "naming the constant (docs/c005_c007_spec.md 'Registered "
            "parameters'; D-115). Refusing to allocate without it — a defaulted "
            "seed is a caller-invisible degree of freedom (Sol, delta 54)"
        )
    if int(seed) < 0:
        raise ValueError(
            f"bu.constants.CRITIC_SPLIT_SEED is negative ({int(seed)}). A "
            "registered RNG seed must be a non-negative exact integer; refusing "
            "to reinterpret it through hashing or platform-specific RNG behavior"
        )
    return int(seed)


# --- the deterministic constrained allocator ---------------------------------


def _observed_value(label: int | str) -> int | str:
    """The validated label, integers normalised to plain int."""
    return int(label) if isinstance(label, Integral) else label


def _group_profiles(candidates: Sequence[SplitCandidate]) -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for c in candidates:
        p = profiles.setdefault(
            c.comparison_group_id,
            {"n0": 0, "n1": 0, "ambiguous": 0, "undiagnosed": 0, "units": []},
        )
        obs = _observed_value(c.observed_label)
        if obs == ESTIMATION:
            p["n0"] += 1
        elif obs == HYPOTHESIS_CLASS:
            p["n1"] += 1
        else:
            p[obs] += 1
        p["units"].append(c.unit_id)
    return profiles


def split_units(
    candidates: Sequence[SplitCandidate],
    *,
    targets: SplitTargets,
) -> tuple[dict[str, str], dict]:
    """Assign every attempted unit to exactly one canonical split.

    There is deliberately NO seed parameter and NO split-name parameter: the
    seed comes only from the registered constant (:func:`_split_seed`) and the
    names only from ``balance.CANONICAL_SPLITS`` (Sol, delta 54/55).

    THE REGISTERED DETERMINISTIC PROCEDURE. The unit of assignment is the whole
    comparison group (D-039); allocation targets the surviving OBSERVED
    decidable counts, never intended-class counts (D-128); the blake2b key is a
    tie-breaker among otherwise-equivalent choices only, never the allocation
    rule (D-115 — never Python's ``hash()``):

    * Floors fold into effective lower bounds: ``min_observed_per_class``
      raises both observed classes' ``lo``; ``min_surviving_observed`` adds a
      pair-sum bound on N0 + N1.
    * Phase 0 — aggregate feasibility. Per observed class ``c``, the available
      total ``A_c`` must satisfy ``sum(lo_eff) <= A_c <= sum(hi)`` (assignment
      is total, so an excess over ``sum(hi)`` is as infeasible as a deficit).
      Refused with the exact deficit or excess.
    * Phase 1 — canonical-order greedy. Groups sort by
      ``(-(n0+n1), -max(n0, n1), blake2b(seed, 'order', group))``; each is
      assigned to the split minimising ``(overshoot beyond hi, -reduction of
      lo_eff/floor deficits, blake2b(seed, 'assign', group, split))``. Groups
      with no decidable units score identically everywhere and land purely on
      the tie-break — the genuine-tie path.
    * Phase 2 — deterministic first-improvement repair. Enumerate
      (group, other-split) moves in canonical order, apply the first move
      strictly reducing the total violation V (lo_eff deficits + hi excesses +
      floor pair-sum deficits), loop to fixpoint.
    * Phase 3 — V == 0 succeeds. If the single-move repair stalls, a complete
      binary feasibility model (SciPy/HiGHS, already pinned by the project)
      decides the same whole-group constraints. A feasible witness replaces
      the local minimum; only solver-proven infeasibility is refused. This is
      required because a feasible assignment may require a swap whose two
      individual moves are not strictly improving. No group splitting, no
      resampling, no duplication, no partial output.

    Every post-condition is then recomputed FROM THE RETURNED MAPPING and the
    manifest is recounted from (assignment, candidates) — never copied from
    allocator state — so the D-072 cross-check holds by construction.

    Returns ``(unit_id -> split over ALL attempted units, manifest)``.
    """
    validate_targets(targets)
    validate_candidates(candidates)
    assert_intended_class_purity(candidates)
    seed = _split_seed()

    ranges: dict[str, dict[int, tuple[int, int]]] = {
        s: {int(c): (int(r.lo), int(r.hi)) for c, r in targets.observed[s].items()}
        for s in CANONICAL_SPLITS
    }
    floors: dict[str, tuple[int, int]] = {
        s: (int(f.min_surviving_observed), int(f.min_observed_per_class))
        for s, f in targets.floors.items()
    }
    lo_eff: dict[str, dict[int, int]] = {
        s: {
            c: max(ranges[s][c][0], floors[s][1] if s in floors else 0)
            for c in (ESTIMATION, HYPOTHESIS_CLASS)
        }
        for s in CANONICAL_SPLITS
    }
    pair_floor: dict[str, int] = {s: floors[s][0] for s in floors}

    profiles = _group_profiles(candidates)

    # Phase 0 — aggregate feasibility, per observed class.
    available = {
        ESTIMATION: sum(p["n0"] for p in profiles.values()),
        HYPOTHESIS_CLASS: sum(p["n1"] for p in profiles.values()),
    }
    for c in (ESTIMATION, HYPOTHESIS_CLASS):
        lo_sum = sum(lo_eff[s][c] for s in CANONICAL_SPLITS)
        hi_sum = sum(ranges[s][c][1] for s in CANONICAL_SPLITS)
        if available[c] < lo_sum:
            raise ValueError(
                f"infeasible targets, proven in aggregate: observed class {c} "
                f"has {available[c]} decidable unit(s) available across all "
                "attempted groups, but the effective lower bounds (declared lo "
                f"raised by registered floors) sum to {lo_sum} — exact deficit "
                f"{lo_sum - available[c]}. Refusing rather than splitting a "
                "group or rebalancing: no resampling, no duplication, no "
                "partial output (docs/c005_c007_spec.md; D-039)"
            )
        if available[c] > hi_sum:
            raise ValueError(
                f"infeasible targets, proven in aggregate: observed class {c} "
                f"has {available[c]} decidable unit(s) that must all be "
                "assigned (assignment is total), but the declared upper bounds "
                f"sum to {hi_sum} — exact excess {available[c] - hi_sum} must "
                "overshoot some split's hi. Refusing: no resampling, no "
                "duplication, no partial output (docs/c005_c007_spec.md; D-039)"
            )

    # Phase 1 — canonical-order greedy.
    order = sorted(
        profiles,
        key=lambda g: (
            -(profiles[g]["n0"] + profiles[g]["n1"]),
            -max(profiles[g]["n0"], profiles[g]["n1"]),
            _stable_key(seed, "order", g),
            g,
        ),
    )
    counts: dict[str, dict[int, int]] = {
        s: {ESTIMATION: 0, HYPOTHESIS_CLASS: 0} for s in CANONICAL_SPLITS
    }

    def deficit(split: str, cnt: Mapping[int, int]) -> int:
        d = sum(
            max(0, lo_eff[split][c] - cnt[c]) for c in (ESTIMATION, HYPOTHESIS_CLASS)
        )
        if split in pair_floor:
            d += max(0, pair_floor[split] - (cnt[ESTIMATION] + cnt[HYPOTHESIS_CLASS]))
        return d

    def excess(split: str, cnt: Mapping[int, int]) -> int:
        return sum(
            max(0, cnt[c] - ranges[split][c][1])
            for c in (ESTIMATION, HYPOTHESIS_CLASS)
        )

    group_assign: dict[str, str] = {}
    for g in order:
        p = profiles[g]

        def placement_key(split: str) -> tuple[int, int, int]:
            after = {
                ESTIMATION: counts[split][ESTIMATION] + p["n0"],
                HYPOTHESIS_CLASS: counts[split][HYPOTHESIS_CLASS] + p["n1"],
            }
            overshoot = excess(split, after) - excess(split, counts[split])
            reduction = deficit(split, counts[split]) - deficit(split, after)
            return (overshoot, -reduction, _stable_key(seed, "assign", g, split))

        best = min(CANONICAL_SPLITS, key=placement_key)
        group_assign[g] = best
        counts[best][ESTIMATION] += p["n0"]
        counts[best][HYPOTHESIS_CLASS] += p["n1"]

    # Phase 2 — deterministic first-improvement repair, to fixpoint.
    def total_violation(cnts: Mapping[str, Mapping[int, int]]) -> int:
        return sum(deficit(s, cnts[s]) + excess(s, cnts[s]) for s in CANONICAL_SPLITS)

    violation = total_violation(counts)
    while violation > 0:
        moved = False
        for g in order:
            p = profiles[g]
            current = group_assign[g]
            for s in CANONICAL_SPLITS:
                if s == current:
                    continue
                trial = {sp: dict(counts[sp]) for sp in CANONICAL_SPLITS}
                trial[current][ESTIMATION] -= p["n0"]
                trial[current][HYPOTHESIS_CLASS] -= p["n1"]
                trial[s][ESTIMATION] += p["n0"]
                trial[s][HYPOTHESIS_CLASS] += p["n1"]
                new_violation = total_violation(trial)
                if new_violation < violation:
                    counts = trial
                    group_assign[g] = s
                    violation = new_violation
                    moved = True
                    break
            if moved:
                break
        if not moved:
            break

    # Phase 3 — a stalled single-move repair is not proof of infeasibility.
    # Ask the complete binary model before issuing that scientific claim.
    if violation > 0:
        solved = _complete_assignment(
            profiles, ranges, lo_eff, floors, seed=seed, order=order
        )
        if solved is not None:
            group_assign = solved
            counts = {
                s: {ESTIMATION: 0, HYPOTHESIS_CLASS: 0}
                for s in CANONICAL_SPLITS
            }
            for group, split in group_assign.items():
                counts[split][ESTIMATION] += profiles[group]["n0"]
                counts[split][HYPOTHESIS_CLASS] += profiles[group]["n1"]
            violation = total_violation(counts)
            if violation != 0:
                raise ValueError(
                    "complete allocator returned a witness that violates the "
                    "registered constraints; refusing internal solver drift "
                    "before any output exists (D-059, D-072)"
                )

    if violation > 0:
        lines = []
        for s in CANONICAL_SPLITS:
            for c in (ESTIMATION, HYPOTHESIS_CLASS):
                lo, hi = ranges[s][c]
                got = counts[s][c]
                delta = (f"shortfall {lo_eff[s][c] - got}" if got < lo_eff[s][c]
                         else f"excess {got - hi}" if got > hi else "within range")
                lines.append(
                    f"  split {s!r} observed class {c}: lo={lo} "
                    f"(effective {lo_eff[s][c]}), hi={hi}, achieved={got}, {delta}"
                )
        for s in sorted(floors):
            surv = counts[s][ESTIMATION] + counts[s][HYPOTHESIS_CLASS]
            min_class = min(counts[s][ESTIMATION], counts[s][HYPOTHESIS_CLASS])
            lines.append(
                f"  floor {s!r}: registered min surviving observed-decidable "
                f"{floors[s][0]}, achieved {surv}; registered min(N0, N1) ON "
                f"OBSERVED LABELS {floors[s][1]}, achieved {min_class}"
            )
        raise ValueError(
            "infeasible whole-group targets: the complete binary feasibility "
            "model proved there is no assignment satisfying every declared "
            "observed range and floor. No group was split, nothing was "
            "resampled or duplicated, and no partial output exists "
            "(docs/c005_c007_spec.md; D-039):\n"
            + "\n".join(lines)
        )

    unit_assign = {
        c.unit_id: group_assign[c.comparison_group_id] for c in candidates
    }
    _assert_postconditions(unit_assign, group_assign, candidates, ranges,
                           lo_eff, floors)
    manifest = _build_manifest(unit_assign, group_assign, candidates, ranges,
                               floors, seed)
    return unit_assign, manifest


def _complete_assignment(
    profiles: Mapping[str, Mapping[str, object]],
    ranges: Mapping[str, Mapping[int, tuple[int, int]]],
    lo_eff: Mapping[str, Mapping[int, int]],
    floors: Mapping[str, tuple[int, int]],
    *,
    seed: int,
    order: Sequence[str],
) -> dict[str, str] | None:
    """Complete whole-group feasibility check after heuristic repair stalls.

    One binary variable says whether group ``g`` is assigned to split ``s``.
    Constraints encode exactly one split per group, every observed-class range,
    and every registered surviving-count floor. HiGHS returns either a witness
    or a proof of infeasibility; numerical or limit failures are refused as
    indeterminate rather than mislabeled infeasible. A stable-hash linear
    objective selects reproducibly among feasible witnesses but never changes
    feasibility (D-115).
    """
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix

    groups = tuple(order)
    splits = tuple(CANONICAL_SPLITS)
    n_vars = len(groups) * len(splits)
    n_rows = len(groups) + 2 * len(splits) + len(floors)
    matrix = lil_matrix((n_rows, n_vars), dtype=float)
    lower = np.full(n_rows, -np.inf, dtype=float)
    upper = np.full(n_rows, np.inf, dtype=float)

    def column(group_index: int, split_index: int) -> int:
        return group_index * len(splits) + split_index

    row = 0
    for gi in range(len(groups)):
        for si in range(len(splits)):
            matrix[row, column(gi, si)] = 1.0
        lower[row] = upper[row] = 1.0
        row += 1

    for si, split in enumerate(splits):
        for cls, profile_key in ((ESTIMATION, "n0"),
                                 (HYPOTHESIS_CLASS, "n1")):
            for gi, group in enumerate(groups):
                matrix[row, column(gi, si)] = float(profiles[group][profile_key])
            lower[row] = float(lo_eff[split][cls])
            upper[row] = float(ranges[split][cls][1])
            row += 1

    for split, (min_surviving, _) in sorted(floors.items()):
        si = splits.index(split)
        for gi, group in enumerate(groups):
            matrix[row, column(gi, si)] = float(
                profiles[group]["n0"] + profiles[group]["n1"]
            )
        lower[row] = float(min_surviving)
        row += 1

    objective = np.array([
        _stable_key(seed, "complete", group, split) / float(2**64)
        for group in groups
        for split in splits
    ])
    result = milp(
        c=objective,
        integrality=np.ones(n_vars, dtype=np.int8),
        bounds=Bounds(np.zeros(n_vars), np.ones(n_vars)),
        constraints=LinearConstraint(matrix.tocsr(), lower, upper),
        options={"presolve": True},
    )
    if result.status == 2:  # HiGHS: proven infeasible.
        return None
    if not result.success or result.x is None:
        raise ValueError(
            f"complete whole-group allocator ended indeterminate "
            f"(status={result.status}, message={result.message!r}); refusing "
            "to call a solver failure infeasible (D-039, D-059)"
        )

    assignment: dict[str, str] = {}
    for gi, group in enumerate(groups):
        values = [result.x[column(gi, si)] for si in range(len(splits))]
        chosen = [si for si, value in enumerate(values) if value > 0.5]
        if len(chosen) != 1:
            raise ValueError(
                f"complete allocator returned non-integral assignment for "
                f"group {group!r}: {values!r}; refusing solver drift (D-059)"
            )
        assignment[group] = splits[chosen[0]]
    return assignment


def _assert_postconditions(
    unit_assign: Mapping[str, str],
    group_assign: Mapping[str, str],
    candidates: Sequence[SplitCandidate],
    ranges: Mapping[str, Mapping[int, tuple[int, int]]],
    lo_eff: Mapping[str, Mapping[int, int]],
    floors: Mapping[str, tuple[int, int]],
) -> None:
    """Recompute every invariant FROM THE RETURNED MAPPING, never allocator
    state. Internal, and still ValueError rather than assert: assertions
    vanish under ``-O`` (D-059)."""
    cand_ids = {c.unit_id for c in candidates}
    if set(unit_assign.keys()) != cand_ids:
        raise ValueError(
            "post-condition violated: the returned mapping is not total and "
            "exclusive over the attempted units (D-039, D-059)"
        )
    group_seen: dict[str, str] = {}
    recount: dict[str, dict[int, int]] = {
        s: {ESTIMATION: 0, HYPOTHESIS_CLASS: 0} for s in CANONICAL_SPLITS
    }
    for c in candidates:
        split = unit_assign[c.unit_id]
        if split not in CANONICAL_SPLITS:
            raise ValueError(
                f"post-condition violated: unit {c.unit_id!r} mapped to "
                f"non-canonical split {split!r} (D-059)"
            )
        prior = group_seen.setdefault(c.comparison_group_id, split)
        if prior != split:
            raise ValueError(
                f"post-condition violated: comparison group "
                f"{c.comparison_group_id!r} landed in both {prior!r} and "
                f"{split!r} — the unit of assignment is the whole group "
                "(D-039, D-059)"
            )
        if group_assign.get(c.comparison_group_id) != split:
            raise ValueError(
                "post-condition violated: unit and group mappings disagree "
                "(D-059)"
            )
        obs = _observed_value(c.observed_label)
        if obs in (ESTIMATION, HYPOTHESIS_CLASS):
            recount[split][obs] += 1
    for s in CANONICAL_SPLITS:
        for cls in (ESTIMATION, HYPOTHESIS_CLASS):
            got = recount[s][cls]
            if not (lo_eff[s][cls] <= got <= ranges[s][cls][1]):
                raise ValueError(
                    f"post-condition violated: split {s!r} observed class "
                    f"{cls} achieved {got}, outside "
                    f"[{lo_eff[s][cls]}, {ranges[s][cls][1]}] recomputed from "
                    "the returned mapping (D-059)"
                )
    for s, (min_surv, min_class) in floors.items():
        surv = recount[s][ESTIMATION] + recount[s][HYPOTHESIS_CLASS]
        got_min = min(recount[s][ESTIMATION], recount[s][HYPOTHESIS_CLASS])
        if surv < min_surv or got_min < min_class:
            raise ValueError(
                f"post-condition violated: split {s!r} floor unmet on the "
                f"returned mapping — surviving observed-decidable {surv} vs "
                f"registered {min_surv}, min(N0, N1) on observed labels "
                f"{got_min} vs registered {min_class} (DEV-012, D-059)"
            )


def _build_manifest(
    unit_assign: Mapping[str, str],
    group_assign: Mapping[str, str],
    candidates: Sequence[SplitCandidate],
    ranges: Mapping[str, Mapping[int, tuple[int, int]]],
    floors: Mapping[str, tuple[int, int]],
    seed: int,
) -> dict:
    """Recount everything from (assignment, candidates) — never from allocator
    state — so manifest counts are recomputable from mapping + inputs (D-072).
    Every adequacy field names OBSERVED labels explicitly; intended-class
    counts are construction diagnostics only (D-128)."""
    per_split: dict[str, dict] = {
        s: {
            "attempted_units": 0,
            "observed_decidable_0": 0,
            "observed_decidable_1": 0,
            "ambiguous": 0,
            "undiagnosed": 0,
            "intended_class_counts": {name: 0 for name in INTENDED_CLASSES},
        }
        for s in CANONICAL_SPLITS
    }
    for c in candidates:
        entry = per_split[unit_assign[c.unit_id]]
        entry["attempted_units"] += 1
        obs = _observed_value(c.observed_label)
        if obs == ESTIMATION:
            entry["observed_decidable_0"] += 1
        elif obs == HYPOTHESIS_CLASS:
            entry["observed_decidable_1"] += 1
        else:
            entry[obs] += 1
        entry["intended_class_counts"][c.intended_class] += 1
    for s in CANONICAL_SPLITS:
        entry = per_split[s]
        entry["surviving_observed_decidable"] = (
            entry["observed_decidable_0"] + entry["observed_decidable_1"]
        )
        entry["observed_min_class_count"] = min(
            entry["observed_decidable_0"], entry["observed_decidable_1"]
        )
    return {
        "schema_version": SPLIT_SCHEMA_VERSION,
        "split_seed": seed,
        "input_digest": input_digest(candidates),
        "n_attempted_units": len(candidates),
        "n_groups": len(group_assign),
        "targets": {
            s: {str(c): list(ranges[s][c]) for c in (ESTIMATION, HYPOTHESIS_CLASS)}
            for s in CANONICAL_SPLITS
        },
        "floors": {
            s: {"min_surviving_observed": floors[s][0],
                "min_observed_per_class": floors[s][1]}
            for s in sorted(floors)
        },
        # The mapping, not a bare set of names — the mapping is what D-039 is
        # about and a name set cannot be cross-checked (D-118).
        "group_to_split": dict(sorted(group_assign.items())),
        "unit_to_split": dict(sorted(unit_assign.items())),
        "per_split": per_split,
        "floor_adequacy": {
            s: {
                "registered_min_surviving_observed": floors[s][0],
                "achieved_surviving_observed":
                    per_split[s]["surviving_observed_decidable"],
                "registered_min_observed_per_class": floors[s][1],
                "achieved_observed_min_class_count":
                    per_split[s]["observed_min_class_count"],
            }
            for s in sorted(floors)
        },
    }


split_units.__critic_consumer__ = "critic.split_units"


# --- the eligibility boundary (spec step 3) ----------------------------------


def eligible_units(
    candidates: Sequence[SplitCandidate],
    assignment: Mapping[str, str],
    traces_by_unit: Mapping[str, Sequence[int]],
) -> list[LabelledUnit]:
    """THE eligibility boundary: only observed-decidable (0/1) records pass.

    Ambiguous and undiagnosed units are excluded HERE, before the balancer
    sees anything, so the certified balancer balances and performs no
    eligibility selection along this path (Sol, delta 61; docs/c005_c007_spec.md
    step 3). Trace-id validity and every downstream guard stay the balancer's —
    one implementation, not a restatement (D-055).

    Join errors fail closed: a stale or hand-edited assignment must not
    silently drop or invent units, and a missing trace inventory must not
    masquerade as a zero-trace unit.
    """
    validate_candidates(candidates)
    assert_intended_class_purity(candidates)
    if not isinstance(assignment, Mapping):
        raise ValueError(
            f"assignment must be a mapping, got {type(assignment).__name__}; "
            "unknown join shapes fail closed (D-054)"
        )
    if not isinstance(traces_by_unit, Mapping):
        raise ValueError(
            f"traces_by_unit must be a mapping, got "
            f"{type(traces_by_unit).__name__}; unknown join shapes fail closed "
            "(D-054)"
        )
    cand_ids = {c.unit_id for c in candidates}
    missing = sorted(cand_ids - set(assignment.keys()))
    if missing:
        raise ValueError(
            f"assignment is missing unit(s) {missing[:5]}"
            f"{' ...' if len(missing) > 5 else ''}. Units the assignment never "
            "saw are the quietest possible data loss; a stale mapping is "
            "refused, not tolerated (Sol, delta 54; D-039)"
        )
    unknown = sorted(set(assignment.keys()) - cand_ids)
    if unknown:
        raise ValueError(
            f"assignment names unknown unit(s) {unknown[:5]}"
            f"{' ...' if len(unknown) > 5 else ''}: the join between splitter "
            "output and candidates is wrong end to end and must not proceed "
            "(Sol, delta 54; D-039)"
        )
    assert_canonical_splits(assignment.values())
    stray_traces = sorted(set(traces_by_unit.keys()) - cand_ids)
    if stray_traces:
        raise ValueError(
            f"traces_by_unit names unit(s) {stray_traces[:5]}"
            f"{' ...' if len(stray_traces) > 5 else ''} that are not among the "
            "candidates: an inventory keyed on unknown ids means the join is "
            "wrong end to end (D-054)"
        )
    out: list[LabelledUnit] = []
    for c in sorted(candidates, key=lambda c: c.unit_id):
        obs = _observed_value(c.observed_label)
        if obs not in (ESTIMATION, HYPOTHESIS_CLASS):
            continue
        if c.unit_id not in traces_by_unit:
            raise ValueError(
                f"observed-decidable unit {c.unit_id!r} is absent from "
                "traces_by_unit. Refusing to default a missing trace inventory "
                "to zero traces: a failed join is not a zero-trace unit, and "
                "the balancer's zero-trace refusal must fire on real "
                "zero-trace units, not on join bugs (D-054)"
            )
        out.append(
            LabelledUnit(
                unit_id=c.unit_id,
                label=obs,
                split=assignment[c.unit_id],
                comparison_group_id=c.comparison_group_id,
                eligible_traces=tuple(traces_by_unit[c.unit_id]),
            )
        )
    return out


eligible_units.__critic_consumer__ = "critic.eligible_units"
