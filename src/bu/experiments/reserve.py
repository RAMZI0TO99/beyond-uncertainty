"""C-003: the predeclared reserve draw order (D-031).

**A preregistration, not a mechanism.** D-031 keeps the design balanced 150/150
on *intended* class and refuses to over-sample in anticipation of differential
exclusion, because expected exclusion is a guess and over-sampling from a guess
is the unreported degree of freedom P§10.6 exists to prevent. The contingency
instead is a reserve whose **order is fixed in advance**, so that a Gate 2
shortfall is filled by a rule written before anyone knew which class survived.

Drawing after seeing which class survived is not a contingency; it is a choice.
That is the whole reason this file exists before it is needed.

How the order is derived, and why this way
------------------------------------------
The registered sweep selection `select_sweep(n, balance_against=canonical)` was
measured rather than assumed, and it has one property that makes it usable and
one that does not:

* **monotone in membership** — `select_sweep(k)` is a strict superset of
  `select_sweep(k-1)`, adding exactly one unit and removing none, for every step
  measured. So "the unit admitted at size k" is well defined.
* **NOT prefix-stable** — the returned *order* changes between calls at
  different n, so `select_sweep(k)[:225]` is not `select_sweep(225)`. Reading a
  draw order off the returned sequence would therefore have been wrong, and
  silently so.

The reserve order is consequently defined by the **set difference at each
step**, which is stable, rather than by list position, which is not. Measured:
the admitted units alternate intended class, so splitting the sequence by class
yields a balanced per-class draw order — which is what D-031 asks for, since a
shortfall is always in one class and excess in the other cannot repair it.

Nothing may be built on this order until Sol has ruled on it (C-003).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import Config, UnitSpec
from .enumerate_units import _intended_class, canonical_units, select_sweep

#: The registered sweep size the design runs. The reserve begins after it.
REGISTERED_SWEEP = 225

#: Where the predeclaration lives. Written once, committed, and thereafter read
#: rather than recomputed -- a predeclaration that is regenerated on demand is
#: not a predeclaration, because a change in the generator silently rewrites it.
PREDECLARATION = Path(__file__).resolve().parents[3] / "reserve_order.json"


def incremental_draw_order(start: int, stop: int) -> list[UnitSpec]:
    """Units admitted by the registered selection as it grows, in admission order.

    Defined by set difference per step, because the returned list order is not
    stable across sizes (see the module docstring). Refuses if a step ever
    removes a unit or adds more than one, since either would mean the order is
    not a draw order at all.
    """
    canonical = canonical_units()

    def at(n):
        return {Config(unit=u).unit_id: u for u in select_sweep(n, balance_against=canonical)}

    order: list[UnitSpec] = []
    prev = at(start)
    for k in range(start + 1, stop + 1):
        cur = at(k)
        added = set(cur) - set(prev)
        removed = set(prev) - set(cur)
        if removed:
            raise RuntimeError(
                f"step {k} removed {len(removed)} unit(s) from the selection. The "
                "reserve order assumes the registered selection only grows; if it "
                "does not, a predeclared order cannot be derived from it"
            )
        if len(added) != 1:
            if not added:
                break  # the pool is exhausted
            raise RuntimeError(
                f"step {k} admitted {len(added)} units at once, so 'the unit drawn "
                "at position k' is ambiguous and no draw order follows from it"
            )
        order.append(cur[next(iter(added))])
        prev = cur
    return order


def build_reserve_order(limit: int = 240) -> dict:
    """Compute the predeclaration. Slow and deliberate; run once, then read the file."""
    drawn = incremental_draw_order(REGISTERED_SWEEP, REGISTERED_SWEEP + limit)
    by_class: dict[int, list[str]] = {0: [], 1: []}
    for unit in drawn:
        by_class[_intended_class(unit)].append(Config(unit=unit).unit_id)
    return {
        "registered_sweep": REGISTERED_SWEEP,
        "n_reserve": len(drawn),
        "draw_order_all": [Config(unit=u).unit_id for u in drawn],
        "draw_order_by_intended_class": {str(k): v for k, v in by_class.items()},
    }


def load_reserve_order() -> dict:
    """Read the predeclaration. Never recomputes -- that is the point of it."""
    if not PREDECLARATION.exists():
        raise FileNotFoundError(
            f"{PREDECLARATION} is missing. The reserve order is a PREDECLARATION: "
            "it is read, not regenerated, because regenerating it lets a change in "
            "the selection code silently rewrite a commitment made in advance (D-031)"
        )
    return json.loads(PREDECLARATION.read_text(encoding="utf-8"))


def next_reserve_units(intended_class: int, n: int) -> tuple[str, ...]:
    """The next ``n`` reserve unit ids for one intended class, in predeclared order.

    Takes a class and a count and nothing else. It cannot see critic
    performance, repair-verified labels or which class did better, because it is
    not given them -- which is D-031's requirement made structural rather than
    promised.
    """
    order = load_reserve_order()["draw_order_by_intended_class"][str(int(intended_class))]
    if n > len(order):
        raise ValueError(
            f"asked for {n} reserve units of intended class {intended_class} but the "
            f"predeclaration holds {len(order)}. Extending it after seeing a shortfall "
            "would be drawing from a reserve chosen with knowledge of the result"
        )
    return tuple(order[:n])
