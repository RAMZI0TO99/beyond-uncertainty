"""Configuration system.

Every experimental parameter lives in a Config and is written to the run record.
Nothing that affects a result may be passed on the command line without landing
in a Config first (Plan §13.7).

Three identities are derived from a Config, and the distinction between them is
load-bearing:

    unit_id    The configuration-condition. This is the statistical unit for
               every confidence interval in the thesis (Plan §10.7), and the
               unit at which class balancing happens (Plan §10.4). A failure
               condition and its repairs share a unit_id -- that shared identity
               is what makes a ground-truth label assignable at all (Plan §7.2).
    config_id  unit_id plus the arm (baseline, or which repair).
    run_id     config_id plus the seed. One run, one record, one metrics file.

Encoding the unit in the data model rather than in a later analysis script is
deliberate. "Which runs form one labelled unit" is then a property of the
config, not something reconstructed in Week 15 from directory names.

Schema stability
----------------
An identity is a hash over the config's fields, so adding a field changes every
id. SCHEMA_VERSION records which schema an id was computed under, and is written
to every run record. The schema freezes at the end of Week 2, when the
configuration axes are final (Schedule W2). No real run exists before Week 6.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import constants as K

#: Bump when a field is added to, removed from, or renamed in any identity
#: dataclass below. Ids are comparable only within one schema version.
SCHEMA_VERSION = 1

ARMS = ("baseline", "data_repair", "feature_repair", "capacity_repair")
FAMILIES = ("estimation", "missing_feature", "capacity")
FEATURES = ("shape", "colour", "position")


@dataclass(frozen=True)
class UnitSpec:
    """The configuration-condition: environment axes plus the manipulation.

    This is the statistical unit. Everything the repair arms hold fixed lives
    here; everything they vary is applied by :class:`Arm`.
    """

    # --- environment configuration axes (Plan §13.1.2) ---
    causal_attribute: str = "shape"
    confound_rate: float = 0.0
    layout: str = "uniform"
    grid_size: int = 8
    n_objects: int = 4

    # --- the failure condition ---
    family: str = "estimation"
    n_transitions: int = 5000
    withheld_features: tuple[str, ...] = ()
    hidden_size: int = 256

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(f"family must be one of {FAMILIES}, got {self.family!r}")
        if self.causal_attribute not in FEATURES:
            raise ValueError(f"causal_attribute must be one of {FEATURES}")
        for f in self.withheld_features:
            if f not in FEATURES:
                raise ValueError(f"unknown withheld feature {f!r}")
        if not 0.0 <= self.confound_rate <= 1.0:
            raise ValueError("confound_rate must lie in [0, 1]")


@dataclass(frozen=True)
class Arm:
    """Which arm of the repair protocol this run is (Plan §7.2).

    Each repair targets exactly one mechanism and they are never combined in a
    single intervention (Plan §8.3). That is enforced here rather than left to
    the caller's discipline.
    """

    kind: str = "baseline"

    def __post_init__(self) -> None:
        if self.kind not in ARMS:
            raise ValueError(f"arm must be one of {ARMS}, got {self.kind!r}")

    def resolve(self, unit: UnitSpec) -> UnitSpec:
        """Return the unit as this arm actually trains it."""
        if self.kind == "baseline":
            return unit
        if self.kind == "data_repair":
            # Multiplier is frozen at 10 and is not tuned per condition.
            return dataclasses.replace(
                unit, n_transitions=unit.n_transitions * K.DATA_REPAIR_MULTIPLIER
            )
        if self.kind == "feature_repair":
            if not unit.withheld_features:
                raise ValueError(
                    "feature_repair on a unit with no withheld features; "
                    "there is nothing to restore"
                )
            return dataclasses.replace(unit, withheld_features=())
        if self.kind == "capacity_repair":
            largest = max(K.HIDDEN_SIZES)
            if unit.hidden_size >= largest:
                raise ValueError(
                    f"capacity_repair on a unit already at hidden_size="
                    f"{unit.hidden_size}; there is no capacity to add"
                )
            return dataclasses.replace(unit, hidden_size=largest)
        raise AssertionError("unreachable")


@dataclass(frozen=True)
class TrainConfig:
    """Optimisation and ensemble settings. Not part of the unit identity."""

    lr: float = 1e-3
    batch_size: int = 128
    max_epochs: int = 500
    patience: int = 20
    val_fraction: float = 0.2
    ensemble_size: int = K.DEFAULT_ENSEMBLE_SIZE
    bootstrap_ratio: float = 1.0


@dataclass(frozen=True)
class Config:
    """A complete, self-sufficient description of one run."""

    unit: UnitSpec = field(default_factory=UnitSpec)
    arm: Arm = field(default_factory=Arm)
    train: TrainConfig = field(default_factory=TrainConfig)
    seed: int = 0
    tags: tuple[str, ...] = ()

    # --- identities ---

    @property
    def unit_id(self) -> str:
        return _hash(_to_plain(self.unit))

    @property
    def config_id(self) -> str:
        return _hash({"unit": _to_plain(self.unit), "arm": _to_plain(self.arm)})

    @property
    def run_id(self) -> str:
        return f"{self.config_id}-s{self.seed:03d}"

    @property
    def effective_unit(self) -> UnitSpec:
        """The unit as this arm trains it, after the repair is applied."""
        return self.arm.resolve(self.unit)

    # --- serialisation ---

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "unit": _to_plain(self.unit),
            "arm": _to_plain(self.arm),
            "train": _to_plain(self.train),
            "seed": self.seed,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Config:
        got = d.get("schema_version")
        if got != SCHEMA_VERSION:
            raise ValueError(
                f"config schema_version {got} != {SCHEMA_VERSION}; ids computed "
                "under different schemas are not comparable"
            )
        return cls(
            unit=UnitSpec(**{**d["unit"], "withheld_features": tuple(d["unit"]["withheld_features"])}),
            arm=Arm(**d["arm"]),
            train=TrainConfig(**d["train"]),
            seed=int(d["seed"]),
            tags=tuple(d.get("tags", ())),
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=True))
        return path

    @classmethod
    def load(cls, path: str | Path) -> Config:
        return cls.from_dict(yaml.safe_load(Path(path).read_text()))


# --- helpers --------------------------------------------------------------


def _to_plain(obj: Any) -> Any:
    """Dataclass -> plain JSON-able dict, with tuples as lists."""
    if dataclasses.is_dataclass(obj):
        return {k: _to_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (tuple, list)):
        return [_to_plain(v) for v in obj]
    return obj


def _hash(obj: Any) -> str:
    """Stable 12-hex-char content hash. Key order and float repr are canonical."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]
