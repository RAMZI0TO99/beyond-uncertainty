"""The configuration-condition matrix (Schedule W2 Tue).

Enumerates every statistical unit the design can draw on, and records which
experimental obligations each one owes.

Two distinctions carry the whole module:

**Configuration vs configuration-condition.** A *configuration* is a setting of
the environment axes -- causal attribute, layout, confound rate. A
*configuration-condition* adds the manipulation that defines the experimental
cell: how much data, which feature is withheld, how much capacity. The
configuration-condition is the statistical unit (Plan §10.7), and it is what
this module enumerates.

**Family vs label.** Every unit here carries a `family` describing how it was
*constructed*. That is not its label. Plan §7.1 is explicit: a condition is
labelled by what actually repairs it, established by running both repairs, and
where construction and repair outcome disagree the repair outcome wins. The
families below are the intended conditions; the labels do not exist until
Week 9. Nothing in this module may be read as a label.

Deduplication (D-007)
---------------------
Sol's Q-003 ruling: the four Experiment 2A confound levels identify units that
also exist in the configuration sweep. They are the same units run at a higher
seed count, not additional ones -- counting them twice would inflate the
effective sample size and invalidate the power calculation. So units are
deduplicated by ``unit_id``, and a unit that serves several purposes accumulates
several *stage obligations* rather than becoming several units.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .. import constants as K
from ..config import LAYOUTS, STAGE_SEEDS, Config, UnitSpec, seeds_for

#: Environment axes. Their product is the configuration space (Plan §13.1.2).
CAUSAL_ATTRIBUTES = ("shape", "colour", "position")
CONFOUND_LEVELS = K.CONFOUND_LEVELS_SWEEP  # 0.0 / 0.25 / 0.5 / 0.75 / 0.9

#: The five canonical (causal attribute, layout) pairs carrying Experiments 1,
#: 2A and 2B, chosen to cover every layout and every causal attribute while
#: giving shape -- the Plan §2.2 worked example -- all three layouts.
#: Plan §14.2 budgets "5 configs" for each canonical experiment; this is that
#: choice made explicit rather than left to whatever the code happened to pick.
CANONICAL_PAIRS: tuple[tuple[str, str], ...] = (
    ("shape", "uniform"),
    ("shape", "clustered"),
    ("shape", "sparse"),
    ("colour", "uniform"),
    ("position", "uniform"),
)

#: Confound used for the canonical Experiment 1 and 2B conditions. Zero, so the
#: estimation and capacity families are not entangled with a shortcut the model
#: could exploit -- those experiments supply complete features, and the decoy
#: correlation is Experiment 2A's manipulation, not theirs.
CANONICAL_CONFOUND = 0.0


@dataclass(frozen=True)
class Obligation:
    """One (unit, stage) pair and the seed count it requires.

    Seed count is a property of the pair, never of the unit alone -- the
    correction D-012 records. A canonical condition owes five seeds to an H1/H2
    claim and twenty to repair validation, and those are different obligations
    on one statistical unit.
    """

    unit: UnitSpec
    stage: str

    @property
    def unit_id(self) -> str:
        return Config(unit=self.unit).unit_id

    @property
    def seeds(self) -> int:
        n = seeds_for(self.stage)
        if n is None:
            raise ValueError(f"stage {self.stage!r} carries no seed policy")
        return n


# --- the canonical experiments (Plan §14.2: 30 + 20 + 25 = 75) ------------


def experiment_1_units() -> tuple[UnitSpec, ...]:
    """Estimation failure: 5 configurations x 6 dataset sizes = 30."""
    return tuple(
        UnitSpec(
            causal_attribute=causal,
            layout=layout,
            confound_rate=CANONICAL_CONFOUND,
            family="estimation",
            n_transitions=n,
        )
        for causal, layout in CANONICAL_PAIRS
        for n in K.DATA_SIZES
    )


def experiment_2a_units() -> tuple[UnitSpec, ...]:
    """Missing feature: 5 configurations x 4 non-zero confounds = 20.

    Here the confound level *is* the condition (Plan §8.2.1), which is why the
    configuration for 2A is a (causal, layout) pair rather than a triple. Run at
    the largest dataset size so data insufficiency is ruled out as an
    explanation (Plan §8.2.1).
    """
    return tuple(
        UnitSpec(
            causal_attribute=causal,
            layout=layout,
            confound_rate=c,
            family="missing_feature",
            withheld_features=(causal,),
            n_transitions=max(K.DATA_SIZES),
        )
        for causal, layout in CANONICAL_PAIRS
        for c in K.CONFOUND_LEVELS_2A
    )


def experiment_2b_units() -> tuple[UnitSpec, ...]:
    """Capacity: 5 configurations x 5 hidden sizes = 25, at largest data."""
    return tuple(
        UnitSpec(
            causal_attribute=causal,
            layout=layout,
            confound_rate=CANONICAL_CONFOUND,
            family="capacity",
            hidden_size=h,
            n_transitions=max(K.DATA_SIZES),
        )
        for causal, layout in CANONICAL_PAIRS
        for h in K.HIDDEN_SIZES
    )


def canonical_units() -> tuple[UnitSpec, ...]:
    return experiment_1_units() + experiment_2a_units() + experiment_2b_units()


# --- the full matrix ------------------------------------------------------


def full_matrix() -> tuple[UnitSpec, ...]:
    """Every configuration-condition the design can draw on, deduplicated.

    The product of confound x layout x causal attribute x manipulation level
    (Schedule W2 Tue). Larger than the ~300 the design needs: Week 5's
    minimum-detectable-effect simulation sets the count that is actually run
    (Plan §10.7), and fixing it here would pre-empt that decision.
    """
    units: list[UnitSpec] = []

    for causal in CAUSAL_ATTRIBUTES:
        for layout in LAYOUTS:
            for confound in CONFOUND_LEVELS:
                base = dict(
                    causal_attribute=causal, layout=layout, confound_rate=confound
                )
                # estimation: vary the dataset size
                for n in K.DATA_SIZES:
                    units.append(UnitSpec(**base, family="estimation", n_transitions=n))
                # capacity: vary the hidden size at the largest dataset
                for h in K.HIDDEN_SIZES:
                    units.append(
                        UnitSpec(
                            **base,
                            family="capacity",
                            hidden_size=h,
                            n_transitions=max(K.DATA_SIZES),
                        )
                    )
                # missing feature: only meaningful where a decoy can substitute
                # for the withheld cause, so the zero-confound level is excluded
                # (Plan §8.2.1 names the four non-zero levels).
                if confound in K.CONFOUND_LEVELS_2A:
                    units.append(
                        UnitSpec(
                            **base,
                            family="missing_feature",
                            withheld_features=(causal,),
                            n_transitions=max(K.DATA_SIZES),
                        )
                    )

    return deduplicate(units + list(canonical_units()))


def deduplicate(units: list[UnitSpec] | tuple[UnitSpec, ...]) -> tuple[UnitSpec, ...]:
    """Collapse to distinct statistical units, preserving first-seen order.

    D-007: the same configuration-condition reached by two routes is one unit.
    Content-hashed ``unit_id`` makes this exact rather than a naming convention.
    """
    seen: set[str] = set()
    out: list[UnitSpec] = []
    for u in units:
        uid = Config(unit=u).unit_id
        if uid not in seen:
            seen.add(uid)
            out.append(u)
    return tuple(out)


# --- selecting what actually runs -----------------------------------------


def sweep_candidates() -> tuple[UnitSpec, ...]:
    """Full matrix minus the canonical units: the pool the sweep draws from."""
    canonical_ids = {Config(unit=u).unit_id for u in canonical_units()}
    return tuple(u for u in full_matrix() if Config(unit=u).unit_id not in canonical_ids)


def _intended_class(unit: UnitSpec) -> int:
    """0 if the construction intends estimation failure, 1 if hypothesis-class.

    "Intended" is load-bearing: the real label comes from the repair test in
    Week 9 (Plan §7.1). This is only used to keep the *design* balanced, never
    to label anything.
    """
    return 0 if unit.family == "estimation" else 1


def _round_robin(pool: tuple[UnitSpec, ...], n: int) -> list[UnitSpec]:
    """Take ``n`` units, spread evenly over strata and over levels within them.

    Two rotations, both deliberate:

    * across strata -- (family, causal, layout, confound), so a truncated draw
      stays balanced on every axis. Confound has to be in the key: without it a
      truncated draw took 99 units at 0.0 and 9 at 0.9, because the enumeration
      loops confound outermost.
    * within a stratum -- each stratum starts at a different offset in the level
      list, so the manipulation levels (dataset size, hidden size) also spread.
      Without the offset every stratum contributes its smallest level first and
      the sweep piles up at one end of each manipulation.

    Deterministic, no RNG: the selection is a function of the design, so it is
    reproducible from the code and diffable when the count changes.
    """
    strata: dict[tuple, list[UnitSpec]] = {}
    for u in pool:
        strata.setdefault(
            (u.family, u.causal_attribute, u.layout, u.confound_rate), []
        ).append(u)

    keys = sorted(strata)
    out: list[UnitSpec] = []
    depth = 0
    while len(out) < n:
        progressed = False
        for i, key in enumerate(keys):
            items = strata[key]
            if depth < len(items):
                out.append(items[(depth + i) % len(items)])
                progressed = True
                if len(out) == n:
                    break
        if not progressed:
            break
        depth += 1
    return out


def select_sweep(
    n: int = 225,
    candidates: tuple[UnitSpec, ...] | None = None,
    *,
    balance_against: tuple[UnitSpec, ...] | None = None,
) -> tuple[UnitSpec, ...]:
    """Choose ``n`` sweep units, balanced across strata and across classes.

    The full crossing is ~3x the compute budget, so the sweep is sampled rather
    than exhaustive -- Plan §14.2 budgets "~225 further configuration-conditions"
    on top of the 75 canonical, for ~300 total (Plan §10.7).

    ``balance_against`` supplies units already committed (the canonical set), so
    the sweep can correct their class imbalance rather than inherit it. This
    matters directly: Plan §10.7 makes power depend on ``min(N0, N1)``, not the
    total, so an unbalanced design wastes the larger class entirely. The
    canonical set is 30 intended-estimation against 45 intended-hypothesis-class,
    and left uncorrected that skew propagates.
    """
    pool = sweep_candidates() if candidates is None else candidates
    if n >= len(pool):
        return pool

    committed = balance_against or ()
    have = {0: 0, 1: 0}
    for u in committed:
        have[_intended_class(u)] += 1

    # Aim for an equal split of the final total across the two intended classes.
    total = len(committed) + n
    target = total // 2
    want = {c: max(0, target - have[c]) for c in (0, 1)}
    shortfall = n - (want[0] + want[1])
    if shortfall > 0:  # rounding, or one class already over target
        want[0] += shortfall // 2
        want[1] += shortfall - shortfall // 2

    out: list[UnitSpec] = []
    for cls in (0, 1):
        by_class = tuple(u for u in pool if _intended_class(u) == cls)
        taken = _round_robin(by_class, min(want[cls], len(by_class)))
        out.extend(taken)

    # If one class ran out of candidates, top up from the other rather than
    # returning fewer units than asked for.
    if len(out) < n:
        chosen = {Config(unit=u).unit_id for u in out}
        rest = tuple(u for u in pool if Config(unit=u).unit_id not in chosen)
        out.extend(_round_robin(rest, n - len(out)))
    return tuple(out)


def design_units(n_sweep: int = 225) -> tuple[UnitSpec, ...]:
    """The units the design actually runs: canonical + a balanced sweep sample.

    ``n_sweep`` is provisional. Week 5 Thursday's minimum-detectable-effect
    simulation sets the real number, inflated by the observed exclusion rate
    (Plan §10.7, Schedule W5 Thu), and Plan §14.3 makes the unit count the only
    reduction lever left when compute runs over.
    """
    canonical = canonical_units()
    sweep = select_sweep(n_sweep, balance_against=canonical)
    units = deduplicate(list(canonical) + list(sweep))

    # A repair-validation unit missing from the design would drop a 20-seed
    # obligation silently, and every label resting on it would quietly fall
    # back to three seeds. Checked here rather than trusted.
    have = {Config(unit=u).unit_id for u in units}
    missing = [u for u in repair_validation_units() if Config(unit=u).unit_id not in have]
    if missing:
        raise RuntimeError(
            f"{len(missing)} repair-validation conditions are absent from the "
            "design; their 20-seed obligation would be lost without a trace"
        )
    return units


# --- stage obligations (D-007, D-012) -------------------------------------


def repair_validation_units() -> tuple[UnitSpec, ...]:
    """The 15 canonical conditions carrying repair validation at 20 seeds.

    Plan §14.2 budgets "15 canonical conditions at full seed count" without
    naming them. One representative per (canonical configuration x family)
    gives exactly 15, and spreads the twenty-seed budget across all three
    failure families rather than concentrating it in one. Recorded as an
    interpretation, not a quotation.
    """
    out: list[UnitSpec] = []
    for causal, layout in CANONICAL_PAIRS:
        out.append(
            UnitSpec(
                causal_attribute=causal, layout=layout, confound_rate=CANONICAL_CONFOUND,
                family="estimation", n_transitions=min(K.DATA_SIZES),
            )
        )
        out.append(
            UnitSpec(
                causal_attribute=causal, layout=layout, confound_rate=0.9,
                family="missing_feature", withheld_features=(causal,),
                n_transitions=max(K.DATA_SIZES),
            )
        )
        out.append(
            UnitSpec(
                causal_attribute=causal, layout=layout, confound_rate=CANONICAL_CONFOUND,
                family="capacity", hidden_size=min(K.HIDDEN_SIZES),
                n_transitions=max(K.DATA_SIZES),
            )
        )
    return tuple(out)


_CANONICAL_STAGE = {
    "estimation": "exp1",
    "missing_feature": "exp2a",
    "capacity": "exp2b",
}


def obligations(units: tuple[UnitSpec, ...] | None = None) -> tuple[Obligation, ...]:
    """Every (unit, stage) obligation implied by the design.

    A unit may appear more than once with different stages. That is the point:
    deduplicate units, never deduplicate obligations (D-007, D-012).
    """
    units = full_matrix() if units is None else units
    by_id = {Config(unit=u).unit_id: u for u in units}

    canonical_ids = {Config(unit=u).unit_id for u in canonical_units()}
    repair_ids = {Config(unit=u).unit_id for u in repair_validation_units()}

    out: list[Obligation] = []
    for uid, unit in by_id.items():
        if uid in canonical_ids:
            out.append(Obligation(unit, _CANONICAL_STAGE[unit.family]))
        else:
            out.append(Obligation(unit, "config_sweep"))
        if uid in repair_ids:
            out.append(Obligation(unit, "repair_validation"))
    return tuple(out)


def arms_for(unit: UnitSpec) -> tuple[str, ...]:
    """Which repair arms are meaningful for a unit.

    Data repair applies to everything. Model repair is whichever mechanism the
    condition actually restricted -- and the two are never combined in one
    intervention (Plan §8.3).
    """
    arms = ["baseline", "data_repair"]
    if unit.withheld_features:
        arms.append("feature_repair")
    if unit.hidden_size < max(K.HIDDEN_SIZES):
        arms.append("capacity_repair")
    return tuple(arms)


def total_model_fits(units: tuple[UnitSpec, ...] | None = None) -> dict[str, int]:
    """Model fits implied by the enumeration, split the way Plan §14.2 splits it.

    The accounting matters and is easy to get wrong. A *baseline* condition
    trains a full ensemble, because H1 and H2 need disagreement across members.
    A *repair* trains a single model: the acceptance test in Plan §7.3 is a
    comparison of per-transition error before and after, and needs no ensemble
    spread. Costing repairs as ensembles inflates the estimate five-fold and
    makes a design that fits look like one that does not.

    Reproducing Plan §14.2's own split is also the check that this enumeration
    is the design the plan budgeted for, rather than a different one of the
    same rough size.
    """
    units = full_matrix() if units is None else units
    baseline_fits = sum(
        ob.seeds * K.DEFAULT_ENSEMBLE_SIZE for ob in obligations(units)
    )
    repair_fits = sum(
        (len(arms_for(u)) - 1) * seeds_for("exp3_repairs") for u in units
    )
    return {
        "baseline_ensembles": baseline_fits,
        "repairs": repair_fits,
        "ablations": 150,  # Plan §14.2's line item; sized in Week 14
        "total": baseline_fits + repair_fits + 150,
    }


# --- reporting (W2 Tue: "prints the count by axis") -----------------------


def count_by_axis(units: tuple[UnitSpec, ...]) -> dict[str, Counter]:
    return {
        "causal_attribute": Counter(u.causal_attribute for u in units),
        "layout": Counter(u.layout for u in units),
        "confound_rate": Counter(u.confound_rate for u in units),
        "family": Counter(u.family for u in units),
        "n_transitions": Counter(u.n_transitions for u in units),
        "hidden_size": Counter(u.hidden_size for u in units),
    }


def summarise(units: tuple[UnitSpec, ...] | None = None) -> str:
    units = full_matrix() if units is None else units
    obs = obligations(units)

    lines = [
        "CONFIGURATION-CONDITION MATRIX",
        "=" * 60,
        f"distinct statistical units (unit_id): {len(units)}",
        f"  target from Plan §10.7:             >= {K.MIN_LABELLED_UNITS}"
        f"  ({'MET' if len(units) >= K.MIN_LABELLED_UNITS else 'NOT MET'})",
        "",
        "By axis",
        "-" * 60,
    ]
    for axis, counts in count_by_axis(units).items():
        rendered = "  ".join(f"{k}={v}" for k, v in sorted(counts.items(), key=lambda kv: str(kv[0])))
        lines.append(f"{axis:>18}: {rendered}")

    lines += ["", "Intended construction families -- NOT labels (Plan §7.1)", "-" * 60]
    fam = Counter(u.family for u in units)
    d0, d1 = fam["estimation"], fam["missing_feature"] + fam["capacity"]
    lines.append(f"  intended D=0 (estimation):        {d0}")
    lines.append(f"  intended D=1 (hypothesis-class):  {d1}")
    lines.append(f"  min(N0, N1) if labels matched construction: {min(d0, d1)}")
    lines.append("  Real labels come from the repair test in Week 9. Ambiguous and")
    lines.append("  undiagnosed cells will reduce both counts (Plan §7.4).")

    lines += ["", "Stage obligations -- units may hold several (D-007, D-012)", "-" * 60]
    by_stage = Counter(o.stage for o in obs)
    for stage in STAGE_SEEDS:
        if stage in by_stage:
            lines.append(
                f"{stage:>18}: {by_stage[stage]:>4} obligations"
                f"  x {seeds_for(stage)} seeds"
            )
    lines.append(f"{'total':>18}: {len(obs):>4} obligations over {len(units)} units")

    lines += ["", "Compute implied (Plan §14.2 accounting)", "-" * 60]
    fits = total_model_fits(units)
    lines.append(f"  baseline ensemble fits: {fits['baseline_ensembles']:>7,}")
    lines.append(f"  repair fits (1 model):  {fits['repairs']:>7,}")
    lines.append(f"  ablations:              {fits['ablations']:>7,}")
    lines.append(f"  total:                  {fits['total']:>7,}")
    lines.append(f"  Plan §14.2 budgets:     ~8,700")
    delta = fits["total"] - 8700
    if delta > 0:
        lines.append(f"  OVER by ~{delta:,}. The Week 5 MDE simulation sets the count")
        lines.append("  actually run; this matrix is the pool, not the plan (§10.7, §14.3).")
    else:
        lines.append(f"  WITHIN budget, with ~{-delta:,} fits of headroom.")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    print("### FULL MATRIX (the pool)\n")
    print(summarise(full_matrix()))
    print("\n\n### DESIGN AS SPECIFIED (canonical + ~225 sweep, Plan §14.2)\n")
    print(summarise(design_units()))
