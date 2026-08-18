"""The Week 4 reliability gate (Schedule W4 Tue–Thu, Plan §11.3).

**A wrapper, never a second implementation.** :func:`bu.stats.trend.trend_test`
stays the single mathematical implementation, used here and again by the Week 10
verdict. This module adds only what makes a *gate verdict* authorised rather
than merely computed — eligibility, aggregation, and the rung on the record.

Eligibility, and why it is separate from the statistic (D-070)
---------------------------------------------------------------
The W4 Monday pilot satisfied the frozen directional rule at three seeds. That
is a **statistical result about the implementation**, not a gate verdict, and
the distinction is load-bearing: at three seeds the exact bootstrap has 27
resamples taking two distinct values, so its interval is the full support rather
than a tight estimate. Sol's ruling is to keep the mathematics untouched and put
the requirement here instead:

* **exactly three predeclared configurations** — shape-causal, confound 0, one
  per layout, so the causal rule and the confounding are held fixed and only the
  layout varies;
* **exactly five development seeds** for each, none missing, substituted or
  added;
* all six registered dataset sizes (enforced downstream by ``trend_test``);
* one ``trend_test`` result per configuration.

Aggregation is fixed here too, before any of it runs: **rung 0 passes only if
all three configuration-level tests pass.** No majority vote. No pooled curve
across configurations. If one fails, the rung fails and the ladder begins —
because this is a *reliability* gate, and configuration sensitivity is itself a
failure of reliability.

The rung is part of the record, not a footnote
-----------------------------------------------
"Passed with the default ensemble" and "passed only after substituting
MC-dropout" are different robustness statements about identical downstream
numbers (S§W4). If the gate passes only at rung 3 or 4, H1 is recorded as
**falsified for ensembles** and every downstream result becomes a secondary path
about that estimator (P§11.3). So the rung and the estimator name travel with
the verdict.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .. import constants as K
from ..config import Config, TrainConfig, UnitSpec
from ..streams import seed_partition
from .trend import TrendResult, trend_test

#: The fallback ladder (S§W4 Tue-Thu). Rung 0 is the default ensemble; reaching
#: rung 3 or 4 means H1 is falsified *for ensembles* even though a gate verdict
#: exists (P§11.3). Names only -- the executable parameters are in
#: ``constants.RUNG_SPECS``, frozen before rung 0 ran (D-071).
RUNGS: dict[int, str] = K.RUNG_NAMES


@dataclass(frozen=True)
class RungSpec:
    """The frozen training specification for one rung (D-071).

    Selected **solely by rung**. There is no free-form estimator argument and no
    way to override a parameter: before this existed,
    ``reliability_gate(curves, rung=0, estimator="mc_dropout")`` was accepted
    and produced a record claiming rung 0 while naming a rung-3 estimator. The
    estimator name was decorative -- it labelled the record without selecting
    anything -- so nothing could ever have detected the contradiction downstream.
    """

    rung: int
    estimator: str
    ensemble_size: int
    bootstrap_ratio: float
    granularity: str
    lr: float
    batch_size: int
    max_epochs: int
    patience: int
    description: str

    def train_config(self) -> TrainConfig:
        """The complete frozen `TrainConfig`, not just the two rung fields.

        Built from the spec rather than from `TrainConfig`'s defaults: if a
        default moved, a run at the new value would otherwise still satisfy the
        old frozen ladder (D-072).
        """
        return TrainConfig(**{f: getattr(self, f) for f in K.RUNG_TRAIN_FIELDS})

    @property
    def spec_hash(self) -> str:
        """Identity of the full specification, not merely the rung number.

        Sol: an attempt directory keyed by rung number alone collides with
        evidence generated under an earlier definition of that rung. Keying by
        the hash means a redefinition cannot silently inherit old evidence.
        """
        payload = json.dumps(
            {"rung": self.rung, "estimator": self.estimator,
             "granularity": self.granularity,
             **{f: getattr(self, f) for f in K.RUNG_TRAIN_FIELDS}},
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:12]

    @classmethod
    def for_rung(cls, rung: int) -> "RungSpec":
        """The frozen spec, or a refusal. Never an inferred or defaulted one."""
        if rung in K.RUNG_PARAMETERS_UNFROZEN:
            raise ValueError(
                f"rung {rung} ({K.RUNG_NAMES[rung]}) is a secondary estimator whose "
                "method-specific parameters are deliberately NOT frozen yet. Sol's "
                "ruling: freeze them before it is executed, not while reading a "
                "failed rung below it. Reaching rung 3 also means H1 is recorded as "
                "falsified for ensembles (P§11.3), and `WorldModel` has no dropout, "
                "so it is an architectural decision rather than a run (D-062)."
            )
        if rung not in K.RUNG_SPECS:
            raise ValueError(f"rung must be one of {sorted(K.RUNG_SPECS)}, got {rung}")
        spec = K.RUNG_SPECS[rung]
        return cls(rung=rung, **spec)

    def as_row(self) -> dict:
        return {
            "rung": self.rung,
            "estimator": self.estimator,
            "granularity": self.granularity,
            "spec_hash": self.spec_hash,
            **{f: getattr(self, f) for f in K.RUNG_TRAIN_FIELDS},
            "description": self.description,
        }


#: The three predeclared gate configurations, recorded **before** execution
#: (D-070). Shape-causal at confound 0 throughout: the manipulation and the
#: confounding are held fixed so the gate tests the *estimator* across layouts
#: rather than confounding the two.
#: These live in ``constants.py`` — they are preregistered choices, not
#: implementation details, and that file is the preregistration (D-070).
GATE_CAUSAL_ATTRIBUTE = K.GATE_CAUSAL_ATTRIBUTE
GATE_CONFOUND_RATE = K.GATE_CONFOUND_RATE
GATE_LAYOUTS: tuple[str, ...] = K.GATE_LAYOUTS
GATE_SEEDS: tuple[int, ...] = K.GATE_SEEDS

#: The exact `config_id` each configuration spans, one per registered dataset
#: size, frozen here **before Tuesday's run**. A configuration is six units, not
#: one, because `n_transitions` is an identity field — the trend test reads a
#: curve *across* those six. Golden values: if identity canonicalisation ever
#: changes, the test that regenerates them fails loudly rather than the gate
#: silently describing different units (the D-016 / IDENTITY_VERSION lesson).
GATE_CONFIG_IDS: dict[str, tuple[str, ...]] = {
    "uniform": (
        "ea25c6151f4d",  # N=100
        "0d36ad29332c",  # N=250
        "320bc9ee4f21",  # N=500
        "daaba764439a",  # N=1000
        "00608aa75f91",  # N=2500
        "d9c4c70b4678",  # N=5000
    ),
    "clustered": (
        "3daf1dcda5ac",  # N=100
        "802912059512",  # N=250
        "a91c2fa273e6",  # N=500
        "970c22a075e6",  # N=1000
        "92ff27a2439d",  # N=2500
        "f35fdc40f563",  # N=5000
    ),
    "sparse": (
        "523dc25c40fa",  # N=100
        "8b9b5956a71b",  # N=250
        "463729da740b",  # N=500
        "2390f6786b20",  # N=1000
        "14d78f124c26",  # N=2500
        "d11d4bbd54af",  # N=5000
    ),
}


def gate_units(layout: str, hidden_size: int = 256) -> tuple[UnitSpec, ...]:
    """The six units one gate configuration spans, one per registered size."""
    if layout not in GATE_LAYOUTS:
        raise ValueError(f"layout must be one of {GATE_LAYOUTS}, got {layout!r}")
    return tuple(
        UnitSpec(
            causal_attribute=GATE_CAUSAL_ATTRIBUTE,
            layout=layout,
            confound_rate=GATE_CONFOUND_RATE,
            family="estimation",
            n_transitions=n,
            hidden_size=hidden_size,
        )
        for n in K.DATA_SIZES
    )


def gate_config_ids(layout: str) -> tuple[str, ...]:
    """Derive the config ids for a layout, for checking against the frozen set."""
    return tuple(
        Config(unit=unit, seed=0, stage="exp1").config_id for unit in gate_units(layout)
    )


@dataclass(frozen=True)
class GateResult:
    """One rung's verdict, with everything needed to report it honestly."""

    #: The frozen training specification. The estimator name comes from here and
    #: from nowhere else, so it cannot contradict the rung (D-071).
    spec: RungSpec
    passed: bool
    reason: str
    #: One per configuration, in ``GATE_LAYOUTS`` order. Preserved rather than
    #: reduced: all three coefficients and intervals are reported (D-070).
    per_configuration: dict[str, TrendResult]
    seeds: tuple[int, ...]
    config_ids: dict[str, tuple[str, ...]]
    #: Every raw per-seed curve, bound to its source run. Sol: "the exact paired
    #: bootstrap cannot be reconstructed from the mean curve alone" -- verified,
    #: `TrendResult` keeps `mean_curve` and `per_seed_rho`, from neither of which
    #: the 5x6 matrix is recoverable. So the evidence travels with the verdict.
    evidence: GateEvidence

    @property
    def rung(self) -> int:
        return self.spec.rung

    @property
    def estimator(self) -> str:
        return self.spec.estimator

    def as_row(self) -> dict:
        return {
            "rung": self.rung,
            "estimator": self.estimator,
            "rung_spec": self.spec.as_row(),
            "evidence": self.evidence.as_row(),
            "passed": self.passed,
            "reason": self.reason,
            "seeds": list(self.seeds),
            "partition": "development",
            "aggregation": K.GATE_AGGREGATION,
            "configurations": {
                name: result.as_row() for name, result in self.per_configuration.items()
            },
            "config_ids": {k: list(v) for k, v in self.config_ids.items()},
        }

    def summary(self) -> str:
        lines = [
            f"W4 RELIABILITY GATE — rung {self.rung} ({self.estimator}): "
            f"{'PASS' if self.passed else 'FAIL'}",
            f"  {self.reason}",
            f"  seeds {list(self.seeds)} (development) · all three configurations "
            "must pass · no majority vote, no pooled curve",
            "",
            f"  {'configuration':>14} {'rho':>9} {'95% interval':>24} {'verdict':>8}",
        ]
        for name, result in self.per_configuration.items():
            interval = f"[{result.ci_low:+.4f}, {result.ci_high:+.4f}]"
            lines.append(
                f"  {name:>14} {result.rho:>9.4f} {interval:>24} "
                f"{'PASS' if result.passed else 'FAIL':>8}"
            )
        if self.rung >= 3:
            lines += [
                "",
                "  *** Reached rung 3 or 4. H1 is recorded as FALSIFIED FOR",
                "      ENSEMBLES, and every downstream result is a secondary",
                "      path about this estimator (P§11.3). ***",
            ]
        return "\n".join(lines)


def _validate_eligibility(
    curves_by_configuration: Mapping[str, Mapping[int, Mapping[int, float]]],
    rung: int,
) -> None:
    """Refuse anything that is not an authorised gate run (D-070).

    Every clause is a refusal. A gate verdict computed from four configurations,
    or from three seeds, or from a substituted seed, is a number that looks
    exactly like an authorised one in every artefact that carries it.
    """
    if rung not in RUNGS:
        raise ValueError(f"rung must be one of {sorted(RUNGS)}, got {rung}")

    names = tuple(curves_by_configuration)
    if set(names) != set(GATE_LAYOUTS):
        raise ValueError(
            f"the gate runs exactly the three predeclared configurations "
            f"{GATE_LAYOUTS}, got {names}. Extra or substituted configurations "
            "change what the gate is a statement about (D-070)."
        )

    for name in GATE_LAYOUTS:
        seeds = tuple(sorted(curves_by_configuration[name]))
        if seeds != GATE_SEEDS:
            raise ValueError(
                f"configuration {name!r} carries seeds {seeds}; the gate requires "
                f"exactly {GATE_SEEDS} — five development seeds, none missing, "
                "substituted or added. The three-seed W4 Monday pilot is an "
                "implementation diagnostic and is not a gate result (D-070)."
            )
        for seed in seeds:
            # Belt and braces: trend_test checks this too, but a gate that
            # consumed confirmatory evidence during estimator selection is the
            # one failure that cannot be undone afterwards.
            if seed_partition(seed) != "development":
                raise ValueError(
                    f"configuration {name!r} carries seed {seed}, which is "
                    f"{seed_partition(seed)!r}. The reliability gate is "
                    "development-only (D-034, D-068)."
                )


def _gate_from_curves(
    curves_by_configuration: Mapping[str, Mapping[int, Mapping[int, float]]],
    *,
    spec: RungSpec,
    evidence: GateEvidence,
) -> GateResult:
    """The mathematics and the aggregation, once the evidence is verified.

    **Private.** Sol's ruling: this "may remain as a private mathematical helper,
    but it must not produce the authorised gate artefact by itself." It is
    reachable only through :func:`reliability_gate`, which will not construct a
    ``GateEvidence`` it has not verified.

    Returns:
        The verdict, with every configuration's coefficient and interval kept.
    """
    _validate_eligibility(curves_by_configuration, spec.rung)

    results = {
        name: trend_test(curves_by_configuration[name], partition="development")
        for name in GATE_LAYOUTS
    }

    failed = [name for name, result in results.items() if not result.passed]
    passed = not failed
    if passed:
        reason = "all three configurations pass the registered directional rule"
    else:
        reason = (
            f"{len(failed)} of 3 configurations failed ({', '.join(failed)}). "
            "A reliability gate requires all three: sensitivity to configuration "
            "is itself a failure of reliability, and there is no majority vote"
        )

    return GateResult(
        spec=spec,
        evidence=evidence,
        passed=passed,
        reason=reason,
        per_configuration=results,
        seeds=GATE_SEEDS,
        config_ids={name: GATE_CONFIG_IDS[name] for name in GATE_LAYOUTS},
    )


# --------------------------------------------------------------------------
# Evidence binding (D-071)
#
# Sol, 2026-08-18: the curve-only function "accepts bare curves indexed only by
# layout, seed, and size. It then attaches the frozen 18 config_id values to the
# result without verifying that those curves came from those configurations."
#
# Reproduced before fixing, and it is worse than the finding says: five lines of
# invented floats of the right shape produced a **PASS**, carrying all eighteen
# golden ids, with no model ever fitted. The verdict was indistinguishable in
# every artefact from an authorised one.
#
# Worse still, and not in the finding: rungs 0, 1 and 2 are indistinguishable by
# EVERY identity in this project. `ensemble_size` and `bootstrap_ratio` are
# deliberately non-identity fields (UNIT_IDENTITY_FIELDS), so a rung-1 run has
# the same config_id, the same run_id and the same fit_id as the rung-0 run it
# replaces. Checking config_id against the golden list is therefore NECESSARY
# BUT NOT SUFFICIENT: it passes unchanged for rung-1 evidence presented as rung
# 0. The rung must be verified against the training parameters recorded in the
# run record, which `Config.to_dict()` does carry.
# --------------------------------------------------------------------------

#: The evidence contract this gate reads. An unrecognised version is refused
#: rather than read optimistically: an older manifest is missing exactly the
#: fields that make a verdict checkable (D-072). These are compatibility
#: versions, deliberately not preregistered constants (D-073).
EVIDENCE_CONTRACT_VERSION = 1

#: The manifest layout. Bumped when fields move; separate from the contract
#: version because the contract can tighten without the layout changing.
MANIFEST_VERSION = 1

#: The metric-row schema of `metrics.jsonl`. Kept apart from
#: `config.SCHEMA_VERSION`: the run-record schema and the per-member metric
#: schema evolve independently, and reusing one for the other would make a
#: bump to either silently invalidate evidence about the other (D-073).
METRIC_SCHEMA_VERSION = 1

#: The experimental cell these runs discharge, attested in each run record so a
#: manifest cannot borrow an honest run from a different obligation.
CELL = "W4 Tue -- reliability gate"

#: The experimental obligation the gate's runs discharge. In run identity, so a
#: run borrowed from another stage cannot be presented as gate evidence.
GATE_STAGE = "exp1"

#: Manifest-level fields the contract requires. A manifest missing any of them
#: is refused, not read optimistically.
REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = (
    "evidence_contract_version", "manifest_version", "attempt_id", "attempt",
    "cell", "rung", "rung_spec", "rung_spec_hash", "commit", "dirty", "branch",
    "packages", "seed_partition", "n_runs", "n_member_records", "runs", "artifacts",
)

#: Per-run fields. ``config`` is the complete canonical ``Config.to_dict()``:
#: every identity and training claim below it is *derived* from that and only
#: cross-checked against the flattened copy, which is what closes the
#: fabricated-manifest hole (D-072).
REQUIRED_RUN_FIELDS: tuple[str, ...] = (
    "config", "run_id", "config_id", "unit_id", "layout", "n_transitions",
    "seed", "stage", "seed_partition", "granularity", "member_count",
    "member_indices", "member_record_digest", "run_record_digest",
    "evaluation_pool_id", "evaluation_pool_digest", "normalisation",
    "metric_schema_version", "row_index", "row_digest", "mean_disagreement",
)


@dataclass(frozen=True)
class EvidenceCell:
    """One (layout, seed, size) cell, bound to the run and artefacts behind it."""

    layout: str
    seed: int
    size: int
    disagreement: float
    #: The complete canonical `Config.to_dict()`. The source of truth for every
    #: identity and training claim in this cell.
    config: dict
    config_id: str
    run_id: str
    unit_id: str
    stage: str
    partition: str
    granularity: str
    member_count: int
    member_indices: tuple[int, ...]
    member_record_digest: str
    run_record_digest: str
    evaluation_pool_id: str
    evaluation_pool_digest: str
    normalisation: dict
    metric_schema_version: int
    row_index: int
    row_digest: str
    attempt_id: str
    attempt: str
    commit: str

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.layout, self.seed, self.size)

    def reconstruct(self) -> Config:
        """The canonical configuration, rebuilt from its own serialised form."""
        try:
            return Config.from_dict(self.config)
        except Exception as exc:  # noqa: BLE001 -- reported, never swallowed
            raise ValueError(
                f"cell {self.key} carries a `config` that will not reconstruct: "
                f"{type(exc).__name__}: {exc}. The gate derives identity from the "
                "canonical config; a config it cannot rebuild is not evidence (D-072)"
            ) from exc

    def as_row(self) -> dict:
        row = {f: getattr(self, f) for f in self.__dataclass_fields__}
        row["member_indices"] = list(self.member_indices)
        return row

    @classmethod
    def from_row(cls, row: Mapping) -> "EvidenceCell":
        fields = {k: row[k] for k in cls.__dataclass_fields__}
        fields["member_indices"] = tuple(fields["member_indices"])
        return cls(**fields)


@dataclass(frozen=True)
class GateEvidence:
    """The 90 cells behind one rung's verdict, verified before it is computed."""

    cells: tuple[EvidenceCell, ...]
    contract_version: int = EVIDENCE_CONTRACT_VERSION

    @property
    def attempt(self) -> str:
        return self.cells[0].attempt

    @property
    def attempt_id(self) -> str:
        return self.cells[0].attempt_id

    @property
    def commit(self) -> str:
        return self.cells[0].commit

    #: What each run contributes to the attempt's identity. Run records are
    #: written *before* training, so hashing them alone let two evidence sets
    #: with identical copied start records but different member streams or rows
    #: share an identity (Sol, D-073). All four travel in `EvidenceCell`, so the
    #: identity stays recomputable from the record alone.
    IDENTITY_DIGESTS: tuple[str, ...] = (
        "run_record_digest", "member_record_digest", "row_digest",
        "evaluation_pool_digest",
    )

    @staticmethod
    def content_id(entries, *, rung: int, spec_hash: str) -> str:
        """The attempt's identity, derived from the runs it actually contains.

        Sol: "Do not use the bare string attempt-001 as the evidence identity.
        Two different directories can both be named attempt-001." They can also
        both be `w4-gate-r00-<spec_hash>-attempt-001`, which is what a first
        attempt at this derivation produced -- verified by building two.

        Hashing the run records makes the identity a function of the execution
        -- `run.json` carries `started_utc` -- but run records are written
        *before* training, so on their own they do not cover what the run
        produced. The member stream, the source row and the evaluation pool are
        included for that reason: an attempt that started identically and then
        produced different numbers gets a different identity.

        Args:
            entries: one tuple per run, in ``IDENTITY_DIGESTS`` order.
        """
        payload = "\n".join(sorted("|".join(str(f) for f in e) for e in entries))
        digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return f"w4-gate-r{rung:02d}-{spec_hash}-{digest}"

    # -- structural verification, all of it computable from the record alone --

    def verify(self, spec: RungSpec) -> None:
        """Refuse anything that is not authorised gate evidence. Every clause fails closed."""
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError(
                f"evidence declares contract version {self.contract_version}; this "
                f"gate reads version {EVIDENCE_CONTRACT_VERSION}. An unrecognised "
                "version is refused rather than read optimistically -- an older "
                "manifest is missing exactly the fields that make a verdict "
                "checkable (D-072)"
            )
        if not self.cells:
            raise ValueError("no evidence cells; the gate has nothing to verify")

        # One attempt, one commit. A verdict assembled from two runs is not a
        # verdict about either (D-062's immutable-attempt rule). The identity is
        # the globally unique attempt_id, never the bare "attempt-001" label:
        # two directories can both be called that.
        ids = {c.attempt_id for c in self.cells}
        commits = {c.commit for c in self.cells}
        if len(ids) != 1:
            raise ValueError(
                f"evidence spans {len(ids)} attempts {sorted(ids)}; a gate verdict is "
                "computed from exactly one immutable attempt (D-062)"
            )
        if len(commits) != 1:
            raise ValueError(
                f"evidence spans {len(commits)} commits {sorted(commits)}; one verdict, "
                "one code state"
            )
        # The grid, exactly: no cell missing, none duplicated, none extra.
        expected = {
            (layout, seed, size)
            for layout in GATE_LAYOUTS
            for seed in GATE_SEEDS
            for size in K.DATA_SIZES
        }
        seen: dict[tuple[str, int, int], EvidenceCell] = {}
        for cell in self.cells:
            if cell.key in seen:
                raise ValueError(
                    f"duplicate evidence for {cell.key}: run_ids {seen[cell.key].run_id} "
                    f"and {cell.run_id}. Which one the verdict used would be decided by "
                    "iteration order"
                )
            seen[cell.key] = cell
        if set(seen) != expected:
            missing = sorted(expected - set(seen))
            extra = sorted(set(seen) - expected)
            raise ValueError(
                f"evidence grid is not the registered one: {len(missing)} missing "
                f"{missing[:4]}, {len(extra)} unregistered {extra[:4]}. The gate is "
                f"exactly {len(GATE_LAYOUTS)}x{len(GATE_SEEDS)}x{len(K.DATA_SIZES)} "
                f"= {len(expected)} cells (D-070)"
            )

        # After the structural checks, so a missing or duplicated cell is
        # reported as that rather than as an identity mismatch it also causes.
        expected_id = self.content_id(
            [[getattr(c, f) for f in self.IDENTITY_DIGESTS] for c in self.cells],
            rung=spec.rung, spec_hash=spec.spec_hash,
        )
        if self.attempt_id != expected_id:
            raise ValueError(
                f"attempt_id {self.attempt_id!r} is not the identity its own runs imply "
                f"({expected_id!r}). It encodes the rung, the full rung-spec hash and a "
                "digest of the run records themselves -- keying by rung number, or by "
                "the bare directory label, lets two distinct executions share an "
                "identity (D-072)"
            )

        for cell in self.cells:
            self._verify_cell(cell, spec)
        self._verify_evaluation_pools(seen)

    @staticmethod
    def _verify_cell(cell: EvidenceCell, spec: RungSpec) -> None:
        # Everything below is derived from the canonical config. The flattened
        # fields are then required to AGREE with it -- they are never the source.
        config = cell.reconstruct()
        derived = {
            "config_id": config.config_id,
            "run_id": config.run_id,
            "unit_id": config.unit_id,
            "seed": config.seed,
            "stage": config.stage,
            "layout": config.unit.layout,
            "n_transitions": config.unit.n_transitions,
        }
        claimed = {
            "config_id": cell.config_id,
            "run_id": cell.run_id,
            "unit_id": cell.unit_id,
            "seed": cell.seed,
            "stage": cell.stage,
            "layout": cell.layout,
            "n_transitions": cell.size,
        }
        disagreements = {k: (derived[k], claimed[k]) for k in derived if derived[k] != claimed[k]}
        if disagreements:
            raise ValueError(
                f"cell {cell.key}: the manifest's flattened fields contradict its own "
                f"canonical config {disagreements}. The config is the source of truth; "
                "an independently supplied value that disagrees with it is refused "
                "(D-072)"
            )

        size_index = K.DATA_SIZES.index(cell.size)
        golden = GATE_CONFIG_IDS[cell.layout][size_index]
        if config.config_id != golden:
            raise ValueError(
                f"cell {cell.key} reconstructs to config_id {config.config_id!r}, but "
                f"the frozen identity for {cell.layout} at N={cell.size} is {golden!r}. "
                "Evidence from a different configuration cannot be issued the golden "
                "ids (D-071)"
            )
        if config.stage != GATE_STAGE:
            raise ValueError(
                f"cell {cell.key} has stage {config.stage!r}; the gate reads "
                f"{GATE_STAGE!r} runs. A run discharging a different obligation is not "
                "gate evidence (D-012)"
            )
        if config.arm.kind != "baseline":
            raise ValueError(
                f"cell {cell.key} carries arm {config.arm.kind!r}; the gate reads "
                "unrepaired baseline runs"
            )
        if seed_partition(config.seed) != "development" or cell.partition != "development":
            raise ValueError(
                f"cell {cell.key} is partition {cell.partition!r} / "
                f"{seed_partition(config.seed)!r}. The reliability gate is "
                "development-only: spending confirmatory seeds on estimator selection "
                "consumes the evidence W10 needs (D-034, D-068)"
            )

        # The COMPLETE training configuration, not only the rung's two fields.
        # Sol: a run altered through learning rate, batch size, epoch budget or
        # patience would otherwise pass. And the rungs are indistinguishable by
        # every identity in this project (D-071), so this is the only check that
        # can tell them apart at all.
        if config.train != spec.train_config():
            differing = {
                f: (getattr(config.train, f), getattr(spec.train_config(), f))
                for f in K.RUNG_TRAIN_FIELDS
                if getattr(config.train, f) != getattr(spec.train_config(), f)
            }
            raise ValueError(
                f"cell {cell.key} was trained under a TrainConfig that is not rung "
                f"{spec.rung}'s frozen specification; differing (actual, frozen): "
                f"{differing}. None of these fields is in any identity, so nothing "
                "else in the project would have noticed (D-071, D-072)"
            )
        # `granularity` is a `train_ensemble` argument, not a `TrainConfig` field,
        # so it cannot be derived from the config at all. It is verified against
        # the run record's own copy in `from_attempt`, and pinned here.
        if cell.granularity != spec.granularity:
            raise ValueError(
                f"cell {cell.key} used bootstrap granularity {cell.granularity!r}; "
                f"rung {spec.rung} is frozen at {spec.granularity!r}. A transition-level "
                "resample is a labelled secondary sensitivity and may never determine a "
                "verdict (D-053)"
            )
        if cell.member_count != spec.ensemble_size:
            raise ValueError(
                f"cell {cell.key} reports {cell.member_count} members; rung {spec.rung} "
                f"is frozen at {spec.ensemble_size}"
            )
        if tuple(cell.member_indices) != tuple(range(spec.ensemble_size)):
            raise ValueError(
                f"cell {cell.key} names member indices {list(cell.member_indices)}; "
                f"rung {spec.rung} expects {list(range(spec.ensemble_size))}. A curve "
                "computed over a subset of members is not the registered estimator"
            )
        if not cell.member_record_digest or not cell.run_record_digest:
            raise ValueError(
                f"cell {cell.key} does not bind its disagreement to any run or member "
                "artefact. An unbound number is a claim, not evidence (D-072)"
            )

    @staticmethod
    def _verify_evaluation_pools(seen: Mapping[tuple[str, int, int], EvidenceCell]) -> None:
        """One fixed evaluation pool per curve, across all six sizes.

        Sol: "a curve evaluated on a different pool at each dataset size is not
        the registered six-size trend, even if every training identity is
        correct." D-052 makes the pools byte-identical across sizes by
        construction; this asserts the property rather than trusting it.
        """
        for layout in GATE_LAYOUTS:
            for seed in GATE_SEEDS:
                cells = [seen[(layout, seed, size)] for size in K.DATA_SIZES]
                pools = {(c.evaluation_pool_id, c.evaluation_pool_digest) for c in cells}
                if len(pools) != 1:
                    raise ValueError(
                        f"{layout} seed {seed}: the six sizes were evaluated on "
                        f"{len(pools)} different evaluation pools {sorted(pools)}. The "
                        "registered trend compares disagreement across dataset size on "
                        "ONE fixed pool (D-052); across different pools it is not the "
                        "registered statistic"
                    )
                scales = {json.dumps(c.normalisation, sort_keys=True) for c in cells}
                if len(scales) != 1:
                    raise ValueError(
                        f"{layout} seed {seed}: the six sizes carry {len(scales)} "
                        "different normalising scales. D-061 registers ONE scale, "
                        "measured on the full movement evaluation pool and reused for "
                        "every subset, member and dataset size sharing that pool"
                    )

    def curves(self) -> dict[str, dict[int, dict[int, float]]]:
        """``{layout: {seed: {size: disagreement}}}`` -- what the statistic reads."""
        out: dict[str, dict[int, dict[int, float]]] = {
            layout: {seed: {} for seed in GATE_SEEDS} for layout in GATE_LAYOUTS
        }
        for cell in self.cells:
            out[cell.layout][cell.seed][cell.size] = cell.disagreement
        return out

    def as_row(self) -> dict:
        """Every raw cell, so the verdict is recomputable without the run records."""
        return {
            "evidence_contract_version": self.contract_version,
            "attempt_id": self.attempt_id,
            "attempt": self.attempt,
            "commit": self.commit,
            "n_cells": len(self.cells),
            "cells": [c.as_row() for c in sorted(self.cells, key=lambda c: c.key)],
        }

    @classmethod
    def from_record(cls, row: Mapping) -> "GateEvidence":
        """Rebuild from :meth:`as_row`, so a serialised verdict can be recomputed."""
        return cls(
            cells=tuple(EvidenceCell.from_row(c) for c in row["cells"]),
            contract_version=row.get("evidence_contract_version", -1),
        )

    # -- filesystem verification, which only `from_attempt` can perform --------

    @classmethod
    def from_attempt(cls, attempt_dir, *, spec: "RungSpec | None" = None) -> "GateEvidence":
        """Read one immutable attempt directory and check it against its artefacts.

        Structural checks live in :meth:`verify`, which works from the record
        alone. The checks here need the filesystem: artefact digests, and that
        each claimed mean disagreement actually reproduces from the source row
        it names.
        """
        attempt_dir = Path(attempt_dir)
        manifest_path = attempt_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"{attempt_dir} has no manifest.json; it is not an attempt")
        manifest = json.loads(manifest_path.read_text())

        missing = [f for f in REQUIRED_MANIFEST_FIELDS if f not in manifest]
        if missing:
            raise ValueError(
                f"{attempt_dir}/manifest.json is missing {missing}. The gate will not "
                "infer provenance it was not given: every absent field is one the "
                "verdict cannot be checked against (D-072)"
            )
        version = manifest["evidence_contract_version"]
        if version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError(
                f"{attempt_dir} declares evidence contract version {version}; this gate "
                f"reads version {EVIDENCE_CONTRACT_VERSION}"
            )
        if manifest["dirty"]:
            raise ValueError(
                f"{attempt_dir} was produced from a dirty tree (commit "
                f"{manifest['commit'][:7]}); a verdict must name one reproducible code "
                "state"
            )

        if manifest["manifest_version"] != MANIFEST_VERSION:
            raise ValueError(
                f"{attempt_dir} declares manifest_version "
                f"{manifest['manifest_version']}; this gate reads "
                f"{MANIFEST_VERSION}. The field said unknown versions are refused, "
                "so it must actually refuse them (D-073)"
            )
        # The `spec` argument must never let a contradictory manifest rung become
        # decorative: if a caller names a rung, the evidence must be that rung's.
        if spec is not None and spec.rung != manifest["rung"]:
            raise ValueError(
                f"{attempt_dir} is rung {manifest['rung']} evidence, but it is being "
                f"read as rung {spec.rung}. The manifest's rung is not advisory"
            )
        spec = spec or RungSpec.for_rung(manifest["rung"])
        if manifest["rung"] != spec.rung:
            raise ValueError(
                f"{attempt_dir} declares rung {manifest['rung']}, which is not the "
                f"frozen rung {spec.rung} being applied"
            )
        if manifest["rung_spec"] != spec.as_row():
            differing = {
                k: (manifest["rung_spec"].get(k), v)
                for k, v in spec.as_row().items()
                if manifest["rung_spec"].get(k) != v
            }
            raise ValueError(
                f"{attempt_dir} carries a rung_spec that is not the frozen one; "
                f"differing (manifest, frozen): {differing}. The recorded "
                "specification and the specification being enforced must be the "
                "same object of belief (D-073)"
            )
        if manifest["rung_spec_hash"] != spec.spec_hash:
            raise ValueError(
                f"{attempt_dir} claims rung spec hash {manifest['rung_spec_hash']!r}; "
                f"the frozen rung {spec.rung} hashes to {spec.spec_hash!r}. Either the "
                "evidence was generated under a different definition of this rung, or "
                "the ladder has been edited since (D-072)"
            )
        cls._verify_artifacts(attempt_dir, manifest["artifacts"])

        rows_path = attempt_dir / "rows.json"
        if not rows_path.exists():
            raise ValueError(
                f"{attempt_dir} has no rows.json, so no run's disagreement can be "
                "reproduced from the data it was computed on. An incidental "
                "FileNotFoundError here would be an accident; this is a refusal (D-072)"
            )
        rows = json.loads(rows_path.read_text())
        cells = []
        for run in manifest["runs"]:
            missing = [f for f in REQUIRED_RUN_FIELDS if f not in run]
            if missing:
                raise ValueError(
                    f"run {run.get('run_id', '<unnamed>')} in {attempt_dir} is missing "
                    f"{missing}. Gate evidence must carry its complete canonical config "
                    "and bind its number to a source artefact -- the W3 pilot manifest "
                    "predates this and is correctly refused here (D-072)"
                )
            cls._verify_bound_row(attempt_dir, run, rows)
            cls._verify_run_record(attempt_dir, run, spec)
            cells.append(
                EvidenceCell(
                    layout=run["layout"], seed=run["seed"], size=run["n_transitions"],
                    disagreement=run["mean_disagreement"], config=run["config"],
                    config_id=run["config_id"], run_id=run["run_id"],
                    unit_id=run["unit_id"], stage=run["stage"],
                    partition=run["seed_partition"], granularity=run["granularity"],
                    member_count=run["member_count"],
                    member_indices=tuple(run["member_indices"]),
                    member_record_digest=run["member_record_digest"],
                    run_record_digest=run["run_record_digest"],
                    evaluation_pool_id=run["evaluation_pool_id"],
                    evaluation_pool_digest=run["evaluation_pool_digest"],
                    normalisation=run["normalisation"],
                    metric_schema_version=run["metric_schema_version"],
                    row_index=run["row_index"], row_digest=run["row_digest"],
                    attempt_id=manifest["attempt_id"], attempt=manifest["attempt"],
                    commit=manifest["commit"],
                )
            )
        # After the per-run checks, so a truncated metric stream reports as that
        # rather than as the identity mismatch it also produces.
        expected_id = cls.content_id(
            [[r.get(f, "") for f in cls.IDENTITY_DIGESTS] for r in manifest["runs"]],
            rung=spec.rung, spec_hash=spec.spec_hash,
        )
        if manifest["attempt_id"] != expected_id:
            raise ValueError(
                f"{attempt_dir}: attempt_id {manifest['attempt_id']!r} disagrees with "
                f"the runs it contains (expected {expected_id!r})"
            )
        if attempt_dir.name != manifest["attempt"]:
            raise ValueError(
                f"{attempt_dir} contains a manifest describing {manifest['attempt']!r}. "
                "The directory and the record it holds must be the same attempt"
            )

        total_members = sum(c.member_count for c in cells)
        if total_members != manifest["n_member_records"]:
            raise ValueError(
                f"{attempt_dir}: manifest declares n_member_records="
                f"{manifest['n_member_records']} but its runs account for "
                f"{total_members} verified members"
            )
        if len(cells) != manifest["n_runs"]:
            raise ValueError(
                f"{attempt_dir}: manifest declares n_runs={manifest['n_runs']} but "
                f"carries {len(cells)} run entries"
            )
        return cls(cells=tuple(cells), contract_version=version)

    @staticmethod
    def _verify_artifacts(attempt_dir: Path, artifacts: list) -> None:
        """Every listed artefact must still hash to what the manifest recorded."""
        for art in artifacts:
            for field in ("path", "sha256", "bytes"):
                if field not in art:
                    raise ValueError(
                        f"{attempt_dir}: artifact entry {art} has no {field!r}"
                    )
            path = attempt_dir / art["path"]
            if not path.exists():
                raise ValueError(
                    f"{attempt_dir}: manifest lists {art['path']!r} but it is not there. "
                    "An attempt is immutable; a missing artefact means it was not"
                )
            size = path.stat().st_size
            if size != art["bytes"]:
                raise ValueError(
                    f"{attempt_dir}/{art['path']} is {size} bytes; the manifest "
                    f"recorded {art['bytes']}"
                )
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != art["sha256"]:
                raise ValueError(
                    f"{attempt_dir}/{art['path']} has digest {actual[:12]}..., but the "
                    f"manifest recorded {art['sha256'][:12]}.... The artefact changed "
                    "after the manifest was written, so the evidence is not what the "
                    "record describes (D-062)"
                )

    @staticmethod
    def _verify_run_record(attempt_dir: Path, run: Mapping, spec: "RungSpec") -> None:
        """Cross-check the manifest against the record written at training time.

        This is the actual trust boundary. A manifest is a summary the runner
        wrote; ``records/<run_id>/run.json`` was written by ``write_run_record``
        when the run started, and ``metrics.jsonl`` gained one line per member as
        each was fitted. A fabricated manifest can claim anything, but it cannot
        make these agree with it without also fabricating them -- and the digests
        it must then carry are checked against the files themselves.
        """
        record_dir = attempt_dir / "records" / run["run_id"]
        record_path = record_dir / "run.json"
        if not record_path.exists():
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} has no run record at "
                f"records/{run['run_id']}/run.json. The manifest describes a run that "
                "left no trace of having happened (D-072)"
            )
        digest = hashlib.sha256(record_path.read_bytes()).hexdigest()
        if digest != run["run_record_digest"]:
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']}'s record hashes to {digest[:12]}..., "
                f"but the manifest recorded {run['run_record_digest'][:12]}..."
            )
        record = json.loads(record_path.read_text())
        if record.get("config") != run["config"]:
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']}'s manifest config differs from the "
                "config in its own run record. The record was written when the run "
                "started; the manifest is a later summary, so the record wins (D-072)"
            )
        # All five attestations, not only granularity. Otherwise a manifest can
        # borrow an honest run record while changing the evaluation pool or the
        # experimental obligation the run was discharging (Sol, D-073).
        extra = record.get("extra") or {}
        attested = {
            "granularity": run["granularity"],
            "rung": spec.rung,
            "rung_spec_hash": spec.spec_hash,
            "evaluation_pool_digest": run["evaluation_pool_digest"],
            "cell": CELL,
        }
        for field, expected in attested.items():
            if field not in extra:
                raise ValueError(
                    f"{attempt_dir}: run {run['run_id']}'s record carries no "
                    f"{field!r} attestation. It is written at training time and is "
                    "what stops a manifest borrowing an honest run record (D-073)"
                )
            if extra[field] != expected:
                raise ValueError(
                    f"{attempt_dir}: run {run['run_id']} presents {field}="
                    f"{expected!r}, but its run record attests {extra[field]!r}. The "
                    "record was written when the run started, so the record wins"
                )
        metrics_path = record_dir / "metrics.jsonl"
        if not metrics_path.exists():
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} has no metrics.jsonl, so its "
                f"claimed {run['member_count']} members left no per-member evidence"
            )
        digest = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
        if digest != run["member_record_digest"]:
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']}'s member records hash to "
                f"{digest[:12]}..., but the manifest recorded "
                f"{run['member_record_digest'][:12]}..."
            )
        members = [
            json.loads(line)
            for line in metrics_path.read_text().splitlines()
            if line.strip()
        ]
        member_indices = sorted(
            m["member"] for m in members if "member" in m
        )
        if run["member_count"] != len(member_indices):
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} declares "
                f"{run['member_count']} members but its metric stream holds "
                f"{len(member_indices)}. The count is verified against the stream, "
                "never taken from the manifest (D-073)"
            )
        if run["metric_schema_version"] != METRIC_SCHEMA_VERSION:
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} declares metric schema "
                f"{run['metric_schema_version']}; this gate reads "
                f"{METRIC_SCHEMA_VERSION}"
            )
        if member_indices != sorted(run["member_indices"]):
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} claims members "
                f"{sorted(run['member_indices'])}, but its metric stream holds "
                f"{member_indices}. The claimed ensemble is not the one that was fitted"
            )

    @staticmethod
    def _verify_bound_row(attempt_dir: Path, run: Mapping, rows: list) -> None:
        """The claimed disagreement must reproduce from the row it names."""
        index = run["row_index"]
        if not isinstance(index, int) or not 0 <= index < len(rows):
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} binds to row {index}, which is not "
                f"in rows.json (length {len(rows)})"
            )
        row = rows[index]
        digest = hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if digest != run["row_digest"]:
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} names row {index} with digest "
                f"{run['row_digest'][:12]}..., but that row now hashes to "
                f"{digest[:12]}.... The source row changed after the manifest was written"
            )
        # The scale that produced this row travels inside it, so requiring
        # equality establishes that the manifest's normalisation is the one the
        # summary was actually computed with -- not merely that it is constant
        # across sizes (Sol, D-073).
        uncertainty = row.get("uncertainty", {})
        row_scale = {
            k: uncertainty[k] for k in run["normalisation"] if k in uncertainty
        }
        if row_scale != run["normalisation"]:
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} reports normalisation "
                f"{run['normalisation']}, but the source row it binds to was computed "
                f"under {row_scale}. D-061 registers one scale per evaluation pool; "
                "a manifest that reports a different one is not describing this number"
            )
        source = uncertainty.get("mean_disagreement")
        if source is None:
            raise ValueError(
                f"{attempt_dir}: row {index} carries no mean_disagreement to reproduce "
                f"run {run['run_id']}'s claim from"
            )
        if source != run["mean_disagreement"]:
            raise ValueError(
                f"{attempt_dir}: run {run['run_id']} claims mean_disagreement "
                f"{run['mean_disagreement']!r}, but its bound source row holds "
                f"{source!r}. The manifest's number is not the one that was measured "
                "(D-072)"
            )


def reliability_gate(evidence: GateEvidence, *, rung: int) -> GateResult:
    """**The** gate. Verify the evidence, then compute the verdict from it.

    This is the only function that produces an authorised gate artefact. There
    is no ``estimator`` argument and no way to pass curves directly: the
    estimator is derived from the frozen :class:`RungSpec` selected by ``rung``,
    and the curves are read out of evidence that has already been checked cell
    by cell against the golden identities, the run records and the rung's
    training specification.

    Args:
        evidence: one immutable attempt's 90 cells, each naming its source run.
        rung: which rung of the ladder. Selects the frozen training spec; a rung
            whose parameters are not yet frozen is refused (D-071).

    Returns:
        The verdict, carrying the rung spec and every raw cell that produced it.
    """
    if not isinstance(evidence, GateEvidence):
        raise TypeError(
            "the gate takes verified GateEvidence, not "
            f"{type(evidence).__name__}. Passing curves directly is the defect "
            "D-071 closed: bare floats of the right shape produced a PASS "
            "carrying the golden config ids with nothing ever fitted. Build "
            "evidence with GateEvidence.from_attempt(); an incidental "
            "AttributeError here would be an accident, not a refusal."
        )
    spec = RungSpec.for_rung(rung)
    evidence.verify(spec)
    return _gate_from_curves(evidence.curves(), spec=spec, evidence=evidence)


def recompute(row: Mapping) -> GateResult:
    """Recompute a serialised verdict from its own record alone (Sol, D-071).

    "The final gate JSON must be independently recomputable without consulting
    informal logs." This reads back :meth:`GateResult.as_row` and re-runs the
    whole path -- verification included -- from the raw cells it carries.
    """
    return reliability_gate(
        GateEvidence.from_record(row["evidence"]), rung=row["rung"]
    )


def select_attempt(root, *, attempt: str | None = None) -> Path:
    """Name **one** immutable attempt explicitly. Never pick one silently (C-010).

    D-064's second obligation. Loading "the attempt directory" from a tree that
    holds several is how a verdict ends up describing a run nobody chose --
    ``attempt-001`` and ``attempt-002`` differ precisely because something was
    wrong with one of them, and "the latest" is a guess dressed as a default.

    Args:
        root: the rung directory, e.g. ``runs/w4_gate/rung-00-<spec_hash>``.
        attempt: the directory name. Optional **only** when exactly one exists.
    """
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")
    attempts = sorted(p.name for p in root.glob("attempt-*") if p.is_dir())
    if not attempts:
        raise ValueError(f"{root} holds no attempt-NNN directory")
    if attempt is None:
        if len(attempts) > 1:
            raise ValueError(
                f"{root} holds {len(attempts)} attempts {attempts}; name the one you "
                "mean. There is no 'latest': a second attempt exists because "
                "something was wrong with the first, and choosing by sort order "
                "would be a guess presented as a default (C-010, D-062)"
            )
        attempt = attempts[0]
    if attempt not in attempts:
        raise ValueError(f"{root} has no attempt {attempt!r}; it holds {attempts}")
    return root / attempt
