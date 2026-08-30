"""Week 6's pure repair-outcome-to-observed-label mapping (Plan Table 2).

This module performs one deliberately small job: it maps two already-decided,
exact boolean repair outcomes to the registered observed label.  It is **not**
the repair-evidence adapter.  In particular, it cannot establish that either
boolean came from the registered repair stage, the complete confirmatory seed
set, the recorded failure masks, or the acceptance procedure.  Callers must not
use this pure mapping as evidence that C-007 is closed end to end.

The two label concepts remain separate: ``intended_class`` records how a unit
was constructed, while ``observed_label`` is derived from the two repair
outcomes.  They deliberately use disjoint value sets at this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, TypeAlias

from ..critic.split import INTENDED_CLASSES

ObservedLabel: TypeAlias = Literal[0, 1, "ambiguous", "undiagnosed"]


def _require_nonblank_identity(value: object, *, field_name: str) -> str:
    """Return an identity only when it is an exact, non-blank string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} must be a non-blank string, got {value!r} "
            f"({type(value).__name__})"
        )
    return value


def _require_exact_bool(value: object, *, field_name: str) -> bool:
    """Refuse truthy/falsy substitutes for a recorded repair outcome."""
    if type(value) is not bool:
        raise ValueError(
            f"{field_name} must be an exact boolean repair outcome, got "
            f"{value!r} ({type(value).__name__}); values are never coerced"
        )
    return value


def observed_label(
    data_repair_works: bool,
    model_repair_works: bool,
) -> ObservedLabel:
    """Apply Plan Table 2 to two already-established repair outcomes.

    ``data only -> 0``; ``model only -> 1``; ``both -> ambiguous``; and
    ``neither -> undiagnosed``.  This function validates types, not evidence
    provenance; see the module-level warning.
    """
    data = _require_exact_bool(
        data_repair_works, field_name="data_repair_works"
    )
    model = _require_exact_bool(
        model_repair_works, field_name="model_repair_works"
    )
    if data and model:
        return "ambiguous"
    if data:
        return 0
    if model:
        return 1
    return "undiagnosed"


@dataclass(frozen=True)
class LabelAssignment:
    """One immutable application of the pure Table 2 mapping.

    The observed label is computed in ``__post_init__`` rather than accepted
    from the caller, so a record cannot carry outcomes and a contradictory
    label.  This record still does not attest where the outcome booleans came
    from and is not a substitute for the missing evidence adapter.
    """

    unit_id: str
    comparison_group_id: str
    intended_class: str
    data_repair_works: bool
    model_repair_works: bool
    observed_label: ObservedLabel = field(init=False)

    def __post_init__(self) -> None:
        _require_nonblank_identity(self.unit_id, field_name="unit_id")
        _require_nonblank_identity(
            self.comparison_group_id, field_name="comparison_group_id"
        )
        if not isinstance(self.intended_class, str) or (
            self.intended_class not in INTENDED_CLASSES
        ):
            raise ValueError(
                f"intended_class must be one of {INTENDED_CLASSES}, got "
                f"{self.intended_class!r} ({type(self.intended_class).__name__}); "
                "it is construction provenance, not an observed integer label"
            )
        label = observed_label(
            self.data_repair_works,
            self.model_repair_works,
        )
        object.__setattr__(self, "observed_label", label)


@dataclass(frozen=True)
class LabelCounts:
    """Exact counts of all four observed-label outcomes."""

    observed_0: int
    observed_1: int
    ambiguous: int
    undiagnosed: int

    @property
    def total(self) -> int:
        return self.observed_0 + self.observed_1 + self.ambiguous + self.undiagnosed

    def as_dict(self) -> dict[int | str, int]:
        """Return a fresh, explicit label-to-count mapping."""
        return {
            0: self.observed_0,
            1: self.observed_1,
            "ambiguous": self.ambiguous,
            "undiagnosed": self.undiagnosed,
        }


def summarize_assignments(assignments: Iterable[LabelAssignment]) -> LabelCounts:
    """Count every valid assignment once, refusing duplicate unit identities."""
    counts: dict[int | str, int] = {
        0: 0,
        1: 0,
        "ambiguous": 0,
        "undiagnosed": 0,
    }
    seen: set[str] = set()
    for position, assignment in enumerate(assignments):
        if type(assignment) is not LabelAssignment:
            raise ValueError(
                f"assignment at position {position} must be an exact "
                f"LabelAssignment, got {type(assignment).__name__}"
            )
        if assignment.unit_id in seen:
            raise ValueError(
                f"duplicate unit_id {assignment.unit_id!r}; one statistical "
                "unit must be counted exactly once"
            )
        seen.add(assignment.unit_id)
        counts[assignment.observed_label] += 1
    return LabelCounts(
        observed_0=counts[0],
        observed_1=counts[1],
        ambiguous=counts["ambiguous"],
        undiagnosed=counts["undiagnosed"],
    )
