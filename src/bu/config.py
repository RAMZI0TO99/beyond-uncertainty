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

Statistical identity is registered, not inferred
------------------------------------------------
Statistical identity and configuration schema are different concepts, and this
module keeps them apart (Sol, Q-005). Only fields that define an *independent
configuration-condition* may affect ``unit_id``. Those fields are named
explicitly in ``UNIT_IDENTITY_FIELDS``; everything deliberately excluded is
named in ``UNIT_NON_IDENTITY_FIELDS``.

Two mechanisms keep that boundary honest rather than aspirational:

* Import-time exhaustiveness. Every field of ``UnitSpec`` must appear in exactly
  one of the two lists. Adding a field without classifying it raises on import,
  so the question "does this change the statistical unit?" cannot be skipped.
* Tests that the classification is *true*, not merely declared: varying any
  registered identity field must change ``unit_id``, and varying any excluded
  field must not.

``IDENTITY_VERSION`` versions the registry and is recorded in every run record.
``SCHEMA_VERSION`` separately versions the serialisation format; a field may be
added to the config without disturbing any existing id, provided it is
classified as non-identity-bearing.

Adding an identity-bearing axis does still change every id -- it genuinely
enlarges the space of units. The axes freeze at the end of Week 2 and no real
run exists before Week 6, so no label is ever at risk.
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

#: Versions the *serialisation format*. Bump when a field is added, removed or
#: renamed anywhere in the config, identity-bearing or not.
SCHEMA_VERSION = 1

#: Versions the *statistical identity registry* below. Bump only when the set of
#: identity-bearing fields changes -- that is, when the space of configuration-
#: conditions itself changes. Ids are comparable only within one identity
#: version, and it is recorded in every run record.
IDENTITY_VERSION = 1

ARMS = ("baseline", "data_repair", "feature_repair", "capacity_repair")

#: Execution stages, and the seed count each requires (Plan §14.2).
#:
#: A unit is one statistical unit but may carry SEVERAL execution obligations:
#: a canonical condition can enter an H1/H2 claim at five seeds *and* canonical
#: repair validation at twenty. Those overlap on seeds 0-4, so without the stage
#: in the run identity the two would collide -- and the five seeds supporting an
#: H1/H2 claim could no longer be told apart from the twenty behind a repair
#: label. Deduplicate units by ``unit_id``; never deduplicate stage obligations.
STAGE_SEEDS: dict[str, int | None] = {
    "exp1": K.SEEDS_HYPOTHESIS,
    "exp2a": K.SEEDS_HYPOTHESIS,
    "exp2b": K.SEEDS_HYPOTHESIS,
    "config_sweep": K.SEEDS_SWEEP,
    "repair_validation": K.SEEDS_REPAIR_VALIDATION,
    "exp3_repairs": K.SEEDS_SWEEP,
    "ablation": K.SEEDS_ABLATION,
    "pilot": None,  # exploratory; no seed policy, never enters a claim
}
STAGES = tuple(STAGE_SEEDS)


def seeds_for(stage: str) -> int | None:
    """The preregistered seed count for a stage (Plan §14.2)."""
    if stage not in STAGE_SEEDS:
        raise ValueError(f"unknown stage {stage!r}; expected one of {STAGES}")
    return STAGE_SEEDS[stage]
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


#: The registered statistical identity of a configuration-condition. A change to
#: any of these is a different unit; a change to anything else is not.
#:
#: Order is fixed and is part of the hash input, so reordering this tuple is a
#: change to IDENTITY_VERSION, not a cosmetic edit.
UNIT_IDENTITY_FIELDS: tuple[str, ...] = (
    # environment configuration axes (Plan §13.1.2)
    "causal_attribute",
    "confound_rate",
    "layout",
    "grid_size",
    "n_objects",
    # the failure condition -- the manipulation that defines the cell
    "family",
    "n_transitions",
    "withheld_features",
    "hidden_size",
)

#: Fields of UnitSpec deliberately excluded from statistical identity. Empty
#: today: every field above is a genuine axis of the design. Anything added here
#: needs a reason recorded in PROJECT_STATE.md §3, because excluding a field
#: means two configs differing in it collapse to one unit.
UNIT_NON_IDENTITY_FIELDS: tuple[str, ...] = ()

#: Which arm distinguishes runs within a unit. The arm is not part of unit_id --
#: that is the whole point: a failure condition and its repairs are one unit.
ARM_IDENTITY_FIELDS: tuple[str, ...] = ("kind",)
ARM_NON_IDENTITY_FIELDS: tuple[str, ...] = ()

#: Config-level fields that feed a unit's identity, and those that deliberately
#: do not. Registered for the same reason as the UnitSpec lists: a field added
#: to Config must not become identity-bearing by accident, and one that should
#: be identity-bearing must not be silently dropped.
CONFIG_IDENTITY_FIELDS: tuple[str, ...] = ("unit", "arm")
CONFIG_NON_IDENTITY_FIELDS: tuple[str, ...] = ("train", "seed", "stage", "tags")


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
    #: Which experimental obligation this run discharges. Part of run identity,
    #: never of unit identity -- see STAGE_SEEDS.
    stage: str = "pilot"
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.stage not in STAGE_SEEDS:
            raise ValueError(f"unknown stage {self.stage!r}; expected one of {STAGES}")

    # --- identities ---

    @property
    def unit_id(self) -> str:
        """Identity of the configuration-condition -- the statistical unit.

        Hashes only the fields registered in UNIT_IDENTITY_FIELDS, in that
        order, together with IDENTITY_VERSION. Nothing else in the config can
        influence it.
        """
        return _hash(_identity_payload(self.unit, UNIT_IDENTITY_FIELDS))

    @property
    def config_id(self) -> str:
        """unit_id plus which arm of the repair protocol."""
        return _hash(
            {
                "unit": _identity_payload(self.unit, UNIT_IDENTITY_FIELDS),
                "arm": _identity_payload(self.arm, ARM_IDENTITY_FIELDS),
            }
        )

    @property
    def run_id(self) -> str:
        """config_id + stage + seed. One run, one record, one metrics file.

        The stage is in here because one unit can owe runs to more than one
        experimental obligation at overlapping seeds; without it, the five seeds
        behind an H1/H2 claim and the first five of twenty behind a repair label
        would be the same run.
        """
        return f"{self.config_id}-{self.stage}-s{self.seed:03d}"

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


def _identity_payload(obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    """The registered identity-bearing fields of ``obj``, and nothing else."""
    return {
        "identity_version": IDENTITY_VERSION,
        "fields": {name: _to_plain(getattr(obj, name)) for name in fields},
    }


def classification_of(cls: type) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (identity, non_identity) field registries for a config dataclass."""
    registries = {
        UnitSpec: (UNIT_IDENTITY_FIELDS, UNIT_NON_IDENTITY_FIELDS),
        Arm: (ARM_IDENTITY_FIELDS, ARM_NON_IDENTITY_FIELDS),
        Config: (CONFIG_IDENTITY_FIELDS, CONFIG_NON_IDENTITY_FIELDS),
    }
    return registries[cls]


def _assert_classification_exhaustive() -> None:
    """Every config field is classified as identity-bearing or not.

    Runs at import. A field added without being classified is a silent change
    to what counts as an independent configuration-condition, which would
    invalidate the power calculation and every confidence interval taken over
    units -- so it fails loudly, immediately, at the point of editing.
    """
    for cls in (UnitSpec, Arm, Config):
        identity, excluded = classification_of(cls)
        declared = set(identity) | set(excluded)
        actual = {f.name for f in dataclasses.fields(cls)}

        overlap = set(identity) & set(excluded)
        if overlap:
            raise RuntimeError(
                f"{cls.__name__}: {sorted(overlap)} classified as both "
                "identity-bearing and non-identity-bearing"
            )
        if unclassified := actual - declared:
            raise RuntimeError(
                f"{cls.__name__}: field(s) {sorted(unclassified)} are not "
                "classified. Add each to the identity registry or to the "
                "explicit exclusion list, and record the reason in "
                "PROJECT_STATE.md §3. Does this field define an independent "
                "configuration-condition?"
            )
        if phantom := declared - actual:
            raise RuntimeError(
                f"{cls.__name__}: registry names {sorted(phantom)}, which are "
                "not fields of the dataclass"
            )


_assert_classification_exhaustive()
