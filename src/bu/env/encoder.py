"""Factored symbolic observation encoder with a feature-masking hook.

Schedule W1 Sat. This is the mechanism for Experiment 2A: withholding an
attribute here removes it from the model's input space entirely, so
``f* ∉ H`` holds *by construction* rather than by hoping the model ignores a
column (Plan §8.2.1).

The distinction that makes the experiment work: withholding changes what the
**model can see**, never what the **environment does**. The gridworld keeps
using shape to decide passability while the encoder omits it, so the true
dynamics remain unrepresentable in the model's hypothesis class no matter how
much data is collected. That is the definition of hypothesis-class failure
(Plan §3.2.2), and it is why the manipulation belongs in the observation and
not in the transition rule.

The encoding is factored and fixed-width: one block per object per attribute,
in a documented order, so that a feature is a known slice rather than an index
someone has to rediscover in Week 11.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

import numpy as np

if TYPE_CHECKING:  # avoid a circular import at runtime
    from .gridworld import GridState

#: Attribute blocks, in encoding order, with their per-object width.
#:
#: position  x and y, normalised to [0, 1]
#: shape     one-hot over (triangle, square)
#: colour    one-hot over (red, blue)
BLOCK_WIDTHS: dict[str, int] = {"position": 2, "shape": 2, "colour": 2}
BLOCK_ORDER: tuple[str, ...] = ("position", "shape", "colour")

#: Always encoded, never withholdable: the agent's own position, and each
#: object's activated bit. Withholding an object *attribute* is the Experiment
#: 2A manipulation; hiding the agent from itself is not a manipulation the
#: design calls for.
AGENT_WIDTH = 2
ACTIVATED_WIDTH = 1


@dataclass(frozen=True)
class Block:
    """One named, contiguous slice of the observation vector."""

    name: str
    start: int
    stop: int

    @property
    def width(self) -> int:
        return self.stop - self.start

    def slice(self) -> slice:
        return slice(self.start, self.stop)


class ObservationEncoder:
    """Encode a :class:`GridState` as a fixed-width float32 vector.

    Args:
        n_objects: objects per episode; fixes the vector width.
        grid_size: used to normalise positions into [0, 1].
        withheld: attribute names removed from the observation entirely. This
            is the Experiment 2A mechanism -- the columns do not exist, rather
            than being present and zeroed, so the model cannot represent a rule
            that depends on them.
    """

    def __init__(
        self, n_objects: int, grid_size: int, withheld: Sequence[str] = ()
    ) -> None:
        unknown = set(withheld) - set(BLOCK_WIDTHS)
        if unknown:
            raise ValueError(
                f"cannot withhold {sorted(unknown)}; encodable attributes are "
                f"{sorted(BLOCK_WIDTHS)}"
            )
        if set(withheld) == set(BLOCK_WIDTHS):
            raise ValueError(
                "withholding every attribute leaves the model nothing to "
                "predict from; that is a broken condition, not a hard one"
            )

        self.n_objects = n_objects
        self.grid_size = grid_size
        #: Sorted so the encoding does not depend on the order they were given,
        #: matching the canonicalisation UnitSpec applies to withheld_features.
        self.withheld: tuple[str, ...] = tuple(sorted(set(withheld)))
        self.visible: tuple[str, ...] = tuple(
            b for b in BLOCK_ORDER if b not in self.withheld
        )
        self.blocks: tuple[Block, ...] = self._build_layout()
        self.size: int = self.blocks[-1].stop if self.blocks else 0

    def _build_layout(self) -> tuple[Block, ...]:
        blocks = [Block("agent_position", 0, AGENT_WIDTH)]
        cursor = AGENT_WIDTH
        for i in range(self.n_objects):
            for attribute in self.visible:
                width = BLOCK_WIDTHS[attribute]
                blocks.append(Block(f"object{i}_{attribute}", cursor, cursor + width))
                cursor += width
            blocks.append(Block(f"object{i}_activated", cursor, cursor + ACTIVATED_WIDTH))
            cursor += ACTIVATED_WIDTH
        return tuple(blocks)

    def block(self, name: str) -> Block:
        for b in self.blocks:
            if b.name == name:
                return b
        raise KeyError(
            f"no block {name!r}"
            + (f"; {name.split('_')[-1]!r} is withheld" if any(
                w in name for w in self.withheld) else "")
        )

    def encode(self, state: GridState) -> np.ndarray:
        """Encode a state as a function of its *visible* object descriptors only.

        Slots are assigned by sorting objects on the descriptor that is actually
        written, never on the underlying state. That distinction is the whole
        point, and it is a correction (D-027).

        ``GridState`` holds objects in raster order by position, which fixed B1
        -- placement order no longer decides slot assignment. But raster order
        is a function of position, so when ``position`` is withheld the slot
        assignment still carried positional information into an observation that
        is supposed to contain none: two arrangements differing only in where
        the objects sat could encode differently through slot order alone.
        Withholding must remove an attribute from the model's input space
        *entirely* (Plan §8.2.1), and a partial leak weakens exactly the
        manipulation Experiment 2A depends on.

        Sorting on the written descriptor makes the observation a function of
        the multiset of visible descriptors and nothing else. Ties are objects
        whose blocks are byte-identical, so the order among them is
        unobservable by construction rather than by convention -- and the
        determinism B1 required is preserved, since the sort is still a pure
        function of the state.
        """
        out = np.zeros(self.size, dtype=np.float32)
        scale = max(self.grid_size - 1, 1)

        out[0:AGENT_WIDTH] = (state.agent[0] / scale, state.agent[1] / scale)

        rows: list[tuple[float, ...]] = []
        for obj in state.objects[: self.n_objects]:
            values: list[float] = []
            for attribute in self.visible:
                values.extend(self._encode_attribute(obj, attribute, scale))
            values.append(float(obj.activated))
            rows.append(tuple(values))

        cursor = AGENT_WIDTH
        for row in sorted(rows):
            out[cursor : cursor + len(row)] = row
            cursor += len(row)
        return out

    @staticmethod
    def _encode_attribute(obj, attribute: str, scale: int) -> tuple[float, ...]:
        from .gridworld import COLOURS, SHAPES

        if attribute == "position":
            return (obj.x / scale, obj.y / scale)
        if attribute == "shape":
            return (float(obj.shape == SHAPES[0]), float(obj.shape == SHAPES[1]))
        if attribute == "colour":
            return (float(obj.colour == COLOURS[0]), float(obj.colour == COLOURS[1]))
        raise ValueError(f"unencodable attribute {attribute!r}")

    def describe(self) -> str:
        withheld = ", ".join(self.withheld) if self.withheld else "none"
        return (
            f"ObservationEncoder(dim={self.size}, objects={self.n_objects}, "
            f"visible={list(self.visible)}, withheld={withheld})"
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return self.describe()
