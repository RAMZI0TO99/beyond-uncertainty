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

#: The fallback ladder (S§W4 Tue–Thu). Rung 0 is the default ensemble; reaching
#: rung 3 or 4 means H1 is falsified *for ensembles* even though a gate verdict
#: exists (P§11.3).
RUNGS: dict[int, str] = {
    0: "ensemble",
    1: "ensemble_10",
    2: "bootstrap_ratio",
    3: "mc_dropout",
    4: "last_layer_laplace",
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

    rung: int
    estimator: str
    passed: bool
    reason: str
    #: One per configuration, in ``GATE_LAYOUTS`` order. Preserved rather than
    #: reduced: all three coefficients and intervals are reported (D-070).
    per_configuration: dict[str, TrendResult]
    seeds: tuple[int, ...]
    config_ids: dict[str, tuple[str, ...]]

    def as_row(self) -> dict:
        return {
            "rung": self.rung,
            "estimator": self.estimator,
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


def reliability_gate(
    curves_by_configuration: Mapping[str, Mapping[int, Mapping[int, float]]],
    *,
    rung: int,
    estimator: str | None = None,
) -> GateResult:
    """Run the registered trend test on each configuration and aggregate.

    Args:
        curves_by_configuration: ``{layout: {seed: {size: disagreement}}}`` for
            exactly the three predeclared layouts, each at exactly five
            development seeds.
        rung: which rung of the fallback ladder produced these curves. Recorded
            with the verdict, because "passed at rung 0" and "passed at rung 3"
            are different claims about the same downstream numbers.
        estimator: defaults to the ladder's name for that rung.

    Returns:
        The verdict, with every configuration's coefficient and interval kept.
    """
    _validate_eligibility(curves_by_configuration, rung)

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
        rung=rung,
        estimator=estimator or RUNGS[rung],
        passed=passed,
        reason=reason,
        per_configuration=results,
        seeds=GATE_SEEDS,
        config_ids={name: GATE_CONFIG_IDS[name] for name in GATE_LAYOUTS},
    )
