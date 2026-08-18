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

from dataclasses import dataclass
from typing import Mapping

from .. import constants as K
from ..config import Config, UnitSpec
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
    description: str

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
            "ensemble_size": self.ensemble_size,
            "bootstrap_ratio": self.bootstrap_ratio,
            "granularity": self.granularity,
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

#: The experimental obligation the gate's runs discharge. In run identity, so a
#: run borrowed from another stage cannot be presented as gate evidence.
GATE_STAGE = "exp1"

#: What an attempt manifest must carry per run for the gate to read it. Absent
#: fields fail closed rather than defaulting: a default here would silently
#: manufacture the very provenance this type exists to verify.
REQUIRED_RUN_FIELDS: tuple[str, ...] = (
    "layout",
    "n_transitions",
    "seed",
    "config_id",
    "run_id",
    "stage",
    "seed_partition",
    "ensemble_size",
    "bootstrap_ratio",
    "granularity",
    "mean_disagreement",
)


@dataclass(frozen=True)
class EvidenceCell:
    """One (layout, seed, size) cell, bound to the run that produced it."""

    layout: str
    seed: int
    size: int
    disagreement: float
    config_id: str
    run_id: str
    stage: str
    partition: str
    ensemble_size: int
    bootstrap_ratio: float
    granularity: str
    attempt: str
    commit: str

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.layout, self.seed, self.size)

    def as_row(self) -> dict:
        return {
            "layout": self.layout,
            "seed": self.seed,
            "size": self.size,
            "disagreement": self.disagreement,
            "config_id": self.config_id,
            "run_id": self.run_id,
            "stage": self.stage,
            "partition": self.partition,
            "ensemble_size": self.ensemble_size,
            "bootstrap_ratio": self.bootstrap_ratio,
            "granularity": self.granularity,
            "attempt": self.attempt,
            "commit": self.commit,
        }

    @classmethod
    def from_row(cls, row: Mapping) -> "EvidenceCell":
        return cls(**{k: row[k] for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class GateEvidence:
    """The 90 cells behind one rung's verdict, verified before it is computed."""

    cells: tuple[EvidenceCell, ...]

    @property
    def attempt(self) -> str:
        return self.cells[0].attempt

    @property
    def commit(self) -> str:
        return self.cells[0].commit

    def verify(self, spec: RungSpec) -> None:
        """Refuse anything that is not authorised gate evidence. Every clause fails closed."""
        if not self.cells:
            raise ValueError("no evidence cells; the gate has nothing to verify")

        # One attempt, one commit. A verdict assembled from two runs is not a
        # verdict about either (D-062's immutable-attempt rule).
        attempts = {c.attempt for c in self.cells}
        commits = {c.commit for c in self.cells}
        if len(attempts) != 1:
            raise ValueError(
                f"evidence spans {len(attempts)} attempts {sorted(attempts)}; a gate "
                "verdict is computed from exactly one immutable attempt (D-062)"
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

        for cell in self.cells:
            self._verify_cell(cell, spec)

    @staticmethod
    def _verify_cell(cell: EvidenceCell, spec: RungSpec) -> None:
        size_index = K.DATA_SIZES.index(cell.size)
        golden = GATE_CONFIG_IDS[cell.layout][size_index]
        if cell.config_id != golden:
            raise ValueError(
                f"cell {cell.key} carries config_id {cell.config_id!r}, but the frozen "
                f"identity for {cell.layout} at N={cell.size} is {golden!r}. Evidence "
                "from a different configuration cannot be issued the golden ids "
                "(D-071)"
            )
        if cell.stage != GATE_STAGE:
            raise ValueError(
                f"cell {cell.key} has stage {cell.stage!r}; the gate reads "
                f"{GATE_STAGE!r} runs. A run discharging a different obligation is "
                "not gate evidence (D-012)"
            )
        expected_run_id = f"{golden}-{GATE_STAGE}-s{cell.seed:03d}"
        if cell.run_id != expected_run_id:
            raise ValueError(
                f"cell {cell.key} names run_id {cell.run_id!r}, which is not the "
                f"identity its own fields imply ({expected_run_id!r}). The record and "
                "the evidence disagree about which run this is"
            )
        if seed_partition(cell.seed) != "development" or cell.partition != "development":
            raise ValueError(
                f"cell {cell.key} is partition {cell.partition!r} / "
                f"{seed_partition(cell.seed)!r}. The reliability gate is "
                "development-only: spending confirmatory seeds on estimator "
                "selection consumes the evidence W10 needs (D-034, D-068)"
            )
        # The rung check that identity cannot do. See the note above: rungs 0-2
        # share config_id, run_id and fit_id, so this is the only place a
        # substituted rung is detectable at all.
        actual = (cell.ensemble_size, cell.bootstrap_ratio, cell.granularity)
        wanted = (spec.ensemble_size, spec.bootstrap_ratio, spec.granularity)
        if actual != wanted:
            raise ValueError(
                f"cell {cell.key} was trained at ensemble_size={cell.ensemble_size}, "
                f"bootstrap_ratio={cell.bootstrap_ratio}, granularity="
                f"{cell.granularity!r}, but rung {spec.rung} is frozen at "
                f"ensemble_size={spec.ensemble_size}, "
                f"bootstrap_ratio={spec.bootstrap_ratio}, "
                f"granularity={spec.granularity!r}. These parameters are NOT in any "
                "identity, so nothing else in the project would have noticed (D-071)"
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
            "attempt": self.attempt,
            "commit": self.commit,
            "n_cells": len(self.cells),
            "cells": [c.as_row() for c in sorted(self.cells, key=lambda c: c.key)],
        }

    @classmethod
    def from_record(cls, row: Mapping) -> "GateEvidence":
        """Rebuild from :meth:`as_row`, so a serialised verdict can be recomputed."""
        return cls(cells=tuple(EvidenceCell.from_row(c) for c in row["cells"]))

    @classmethod
    def from_attempt(cls, attempt_dir) -> "GateEvidence":
        """Read one immutable attempt directory. Missing fields fail closed."""
        import json
        from pathlib import Path

        attempt_dir = Path(attempt_dir)
        manifest = json.loads((attempt_dir / "manifest.json").read_text())
        for field in ("attempt", "commit", "dirty", "runs"):
            if field not in manifest:
                raise ValueError(
                    f"{attempt_dir}/manifest.json has no {field!r}; it is not a gate "
                    "evidence manifest. The gate will not infer provenance it was not "
                    "given (D-071)"
                )
        if manifest["dirty"]:
            raise ValueError(
                f"{attempt_dir} was produced from a dirty tree (commit "
                f"{manifest['commit'][:7]}); a verdict must name one reproducible code "
                "state"
            )
        cells = []
        for run in manifest["runs"]:
            missing = [f for f in REQUIRED_RUN_FIELDS if f not in run]
            if missing:
                raise ValueError(
                    f"run {run.get('run_id', '<unnamed>')} in {attempt_dir} is missing "
                    f"{missing}. Gate evidence must carry its own provenance and "
                    "training specification -- the W3 pilot manifest predates this and "
                    "is correctly refused here (D-071)"
                )
            cells.append(
                EvidenceCell(
                    layout=run["layout"],
                    seed=run["seed"],
                    size=run["n_transitions"],
                    disagreement=run["mean_disagreement"],
                    config_id=run["config_id"],
                    run_id=run["run_id"],
                    stage=run["stage"],
                    partition=run["seed_partition"],
                    ensemble_size=run["ensemble_size"],
                    bootstrap_ratio=run["bootstrap_ratio"],
                    granularity=run["granularity"],
                    attempt=manifest["attempt"],
                    commit=manifest["commit"],
                )
            )
        return cls(cells=tuple(cells))


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
