"""The critic's visible feature space, frozen.

Plan §7.5 separates what the critic sees from what it must not see, and requires
that the separation be enforced **in code, not by convention**, because leakage
here would be silent and fatal. Plan §16 rates it as "silent invalidation of all
critic results", with "implausibly high accuracy early in Month 3" as its early
warning -- that is, discovered only after work has been built on it.

This module is the whitelist. It fails closed: a column that is not registered
here cannot reach the critic, so adding anything to the experimenter's dataframe
is safe by default. A blacklist would fail open on exactly that event.

Frozen 2026-08-15, before any labelled data exists and before any H1/H2 result
could influence which features look useful (Sol, Q-006). The feature groups are
taken verbatim from Plan §13.5.1 and the variants from Plan §12.1. Changing
CRITIC_FEATURE_SCHEMA requires a Change Record in DECISIONS.md, and after
Week 6 it requires a reason that is not "the critic performs better without it".

Three structures, physically separate (Sol, Q-006)
--------------------------------------------------
    X       allowlisted critic-visible features, and nothing else
    y       the diagnosis label
    groups  unit_id / configuration / seed, used ONLY for splitting and for
            confidence intervals

Model-facing code accepts ``X`` alone. It never receives the output of
``load_runs()``, which legitimately carries construction metadata for the
experimenter's own analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Bump on any change to the registered feature set. Recorded in every critic
#: dataset artefact alongside the field list itself.
CRITIC_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class FeatureGroup:
    name: str
    features: tuple[str, ...]
    #: Which ablation variants retain this group (Plan §13.5.1, §12.1).
    retained_in: tuple[str, ...]


#: Verbatim from Plan §13.5.1.
CRITIC_FEATURE_SCHEMA: tuple[FeatureGroup, ...] = (
    FeatureGroup(
        name="error",
        features=("error_magnitude", "error_persistence", "error_trend"),
        retained_in=("full", "no_magnitude", "statistics_only"),
    ),
    FeatureGroup(
        name="uncertainty",
        features=("ensemble_disagreement", "ensemble_predictive_variance"),
        retained_in=("full", "no_magnitude", "statistics_only"),
    ),
    FeatureGroup(
        name="representational",
        features=("wm_hidden_activations", "predicted_vs_actual_state", "action_taken"),
        retained_in=("full", "no_magnitude", "no_statistics"),
    ),
    FeatureGroup(
        name="context",
        features=("state_history", "action_history"),
        retained_in=("full", "no_magnitude", "no_statistics"),
    ),
)

VARIANTS = ("full", "no_magnitude", "no_statistics", "statistics_only")

#: Per-variant feature removals *within* a retained group (Plan §13.5.1).
#: The statistics-only variant must end up with exactly B1's two features --
#: error magnitude and disagreement -- so that the Plan §8.4 contrast isolates
#: architecture rather than feature count. Error persistence was removed from it
#: in Plan v1.2 for precisely that reason.
VARIANT_FEATURE_OVERRIDES: dict[str, dict[str, tuple[str, ...]]] = {
    "no_magnitude": {
        "error": ("error_persistence", "error_trend"),
    },
    "statistics_only": {
        "error": ("error_magnitude",),
        "uncertainty": ("ensemble_disagreement",),
    },
}

#: Named explicitly so the prohibition is testable rather than implied.
#: Plan §7.5: the critic does not see the repair, the post-repair error, the
#: construction label, the dataset size, or the capacity setting.
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        # the counterfactual itself
        "label", "diagnosis", "y", "repair_outcome", "post_repair_error",
        "data_repair_works", "model_repair_works",
        # construction metadata
        "family", "arm", "stage", "config_id", "unit_id", "run_id", "seed",
        # every configuration axis (Plan §13.1.2), by unit_ prefix and by name
        "causal_attribute", "confound_rate", "layout", "grid_size", "n_objects",
        "n_transitions", "withheld_features", "hidden_size",
    }
)

#: Any column carrying this prefix is construction metadata by construction.
FORBIDDEN_PREFIXES: tuple[str, ...] = ("unit_", "construction_", "repair_")


def features_for(variant: str) -> tuple[str, ...]:
    """The exact ordered feature list a variant may see."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; expected one of {VARIANTS}")
    overrides = VARIANT_FEATURE_OVERRIDES.get(variant, {})
    out: list[str] = []
    for group in CRITIC_FEATURE_SCHEMA:
        if variant not in group.retained_in:
            continue
        out.extend(overrides.get(group.name, group.features))
    return tuple(out)


ALLOWED_FEATURES: frozenset[str] = frozenset(features_for("full"))


def is_permitted(column: str) -> bool:
    """True only for explicitly registered critic features.

    Fails closed: an unknown column is refused, not passed through.
    """
    if column in FORBIDDEN_FIELDS:
        return False
    if any(column.startswith(p) for p in FORBIDDEN_PREFIXES):
        return False
    return column in ALLOWED_FEATURES


def assert_no_forbidden_columns(columns: object) -> None:
    """Raise if any column would leak construction metadata into X.

    Call this at the boundary where critic features are built, on the way in.
    """
    offenders = sorted(c for c in columns if not is_permitted(str(c)))
    if offenders:
        raise ValueError(
            "columns rejected by the critic feature whitelist: "
            f"{offenders}. Either they are construction metadata (Plan §7.5), "
            "or they are new features that must be registered in "
            "CRITIC_FEATURE_SCHEMA and CRITIC_SCHEMA_VERSION bumped. "
            "Do not rename a forbidden field to get it through."
        )


def _assert_schema_is_coherent() -> None:
    """Checked at import, like the identity registry."""
    seen: set[str] = set()
    for group in CRITIC_FEATURE_SCHEMA:
        if dupes := seen & set(group.features):
            raise RuntimeError(f"feature(s) {sorted(dupes)} registered twice")
        seen |= set(group.features)
        for variant in group.retained_in:
            if variant not in VARIANTS:
                raise RuntimeError(f"{group.name} names unknown variant {variant!r}")

    if overlap := seen & FORBIDDEN_FIELDS:
        raise RuntimeError(
            f"{sorted(overlap)} are both allowed features and forbidden fields"
        )
    for feature in seen:
        if any(feature.startswith(p) for p in FORBIDDEN_PREFIXES):
            raise RuntimeError(f"allowed feature {feature!r} carries a forbidden prefix")

    for variant, overrides in VARIANT_FEATURE_OVERRIDES.items():
        if variant not in VARIANTS:
            raise RuntimeError(f"override for unknown variant {variant!r}")
        for group_name, features in overrides.items():
            group = next((g for g in CRITIC_FEATURE_SCHEMA if g.name == group_name), None)
            if group is None:
                raise RuntimeError(f"override for unknown group {group_name!r}")
            if extra := set(features) - set(group.features):
                raise RuntimeError(
                    f"{variant}/{group_name} override adds unregistered "
                    f"feature(s) {sorted(extra)}"
                )


_assert_schema_is_coherent()
