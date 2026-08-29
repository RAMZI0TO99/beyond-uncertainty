"""Tests for the frozen critic feature whitelist.

The list of required tests is Sol's, from its Q-006 answer. Each one names a
way the leakage boundary could fail while still looking correct.
"""

from __future__ import annotations

import pytest

from bu.config import Arm, Config, UnitSpec
from bu.critic.schema import (
    ALLOWED_FEATURES,
    CRITIC_FEATURE_SCHEMA,
    CRITIC_SCHEMA_VERSION,
    FORBIDDEN_FIELDS,
    VARIANTS,
    assert_no_forbidden_columns,
    features_for,
    is_permitted,
)
from bu.metrics import RunLogger, load_runs


def test_every_allowed_feature_is_explicitly_registered():
    registered = {f for g in CRITIC_FEATURE_SCHEMA for f in g.features}
    assert ALLOWED_FEATURES == registered
    assert registered, "the whitelist must not be empty"


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_FIELDS))
def test_forbidden_fields_cannot_enter_x(forbidden):
    """Repair outcome, construction family, dataset size, capacity, arm, seed,
    labels and every configuration axis (Plan §7.5)."""
    assert not is_permitted(forbidden)
    with pytest.raises(ValueError, match="rejected by the critic feature whitelist"):
        assert_no_forbidden_columns([forbidden])


def test_an_unknown_column_is_refused_not_passed_through():
    """The whitelist fails closed. This is the property a blacklist lacks."""
    assert not is_permitted("some_future_column_nobody_thought_about")
    with pytest.raises(ValueError):
        assert_no_forbidden_columns(["some_future_column_nobody_thought_about"])


def test_load_runs_output_is_rejected_wholesale(tmp_path):
    """The experimenter's frame must never be handed to the critic intact.

    This is the concrete version of the risk: load_runs() legitimately carries
    family and every unit_* axis, and a pipeline that forwards it unfiltered
    would leak without any single line looking wrong.
    """
    cfg = Config(unit=UnitSpec(n_transitions=500), arm=Arm("baseline"), stage="pilot")
    with RunLogger.start(cfg, root=tmp_path) as log:
        log.log(epoch=0, mse=0.3)

    df = load_runs(tmp_path)
    with pytest.raises(ValueError) as exc:
        assert_no_forbidden_columns(df.columns)
    message = str(exc.value)
    assert "family" in message
    assert any("unit_" in part for part in message.split())


def test_renaming_a_forbidden_field_does_not_launder_it():
    """Sol: features derived from forbidden metadata are rejected, not renamed."""
    for disguised in ("unit_n_transitions", "construction_family", "repair_outcome"):
        assert not is_permitted(disguised)


def test_statistics_only_matches_b1s_two_features():
    """Plan §12.1 / v1.2 correction: the statistics-only variant must carry
    exactly B1's features, or the Plan §8.4 contrast confounds architecture
    with feature count."""
    assert features_for("statistics_only") == ("error_magnitude", "ensemble_disagreement")


def test_no_magnitude_variant_drops_only_the_magnitude():
    feats = features_for("no_magnitude")
    assert "error_magnitude" not in feats
    assert "error_persistence" in feats and "error_trend" in feats
    assert "ensemble_disagreement" in feats


def test_no_statistics_variant_drops_error_and_uncertainty_groups():
    feats = features_for("no_statistics")
    assert not {"error_magnitude", "ensemble_disagreement"} & set(feats)
    assert "wm_hidden_activations" in feats
    assert "state_history" in feats


@pytest.mark.parametrize("variant", VARIANTS)
def test_every_variant_is_a_subset_of_the_whitelist(variant):
    assert set(features_for(variant)) <= ALLOWED_FEATURES
    assert features_for(variant), f"{variant} has no features"


def test_full_variant_is_the_whole_whitelist():
    assert set(features_for("full")) == ALLOWED_FEATURES


def test_schema_version_is_recorded():
    assert isinstance(CRITIC_SCHEMA_VERSION, int)


def test_unknown_variant_is_refused():
    with pytest.raises(ValueError, match="unknown variant"):
        features_for("whatever_helps")
