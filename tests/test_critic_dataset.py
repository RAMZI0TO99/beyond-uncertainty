"""Adversarial tests for the Week 6 critic leakage firewall."""

from __future__ import annotations

import pandas as pd
import pytest

from bu.critic.dataset import CriticDataset
from bu.critic.schema import CRITIC_SCHEMA_VERSION, features_for


def frames(*, variant="statistics_only"):
    index = pd.Index(["trace-a", "trace-b"], name="trace_id")
    X = pd.DataFrame(
        {
            feature: [float(i), float(i + 1)]
            for i, feature in enumerate(features_for(variant))
        },
        index=index,
    )
    y = pd.Series([0, 1], index=index, name="observed_label")
    groups = pd.DataFrame(
        {
            "unit_id": ["u0", "u1"],
            "comparison_group_id": ["g0", "g1"],
            "seed": [1000, 1001],
        },
        index=index,
    )
    return X, y, groups


def test_dataset_records_frozen_variant_and_schema_version():
    X, y, groups = frames()
    dataset = CriticDataset(X, y, groups, variant="statistics_only")
    assert dataset.variant == "statistics_only"
    assert dataset.schema_version == CRITIC_SCHEMA_VERSION


@pytest.mark.parametrize(
    "offender",
    ["observed_label", "y", "unit_id", "comparison_group_id", "seed", "mystery"],
)
def test_labels_metadata_and_unknown_columns_cannot_enter_x(offender):
    X, y, groups = frames()
    X[offender] = [0, 0]
    with pytest.raises(ValueError, match="cannot enter X"):
        CriticDataset(X, y, groups, variant="statistics_only")


def test_x_must_contain_every_variant_feature_in_registered_order():
    X, y, groups = frames()
    with pytest.raises(ValueError, match="missing"):
        CriticDataset(
            X.drop(columns=["error_magnitude"]),
            y,
            groups,
            variant="statistics_only",
        )
    with pytest.raises(ValueError, match="ordered feature tuple"):
        CriticDataset(X.loc[:, list(reversed(X.columns))], y, groups,
                      variant="statistics_only")


@pytest.mark.parametrize("target", ["y", "groups"])
def test_index_misalignment_fails_instead_of_reindexing(target):
    X, y, groups = frames()
    if target == "y":
        y = y.iloc[::-1]
    else:
        groups = groups.iloc[::-1]
    with pytest.raises(ValueError, match="indices must match exactly"):
        CriticDataset(X, y, groups, variant="statistics_only")


def test_duplicate_x_index_is_refused():
    X, y, groups = frames()
    duplicate = pd.Index(["same", "same"])
    X.index = duplicate
    y.index = duplicate
    groups.index = duplicate
    with pytest.raises(ValueError, match="index must be unique"):
        CriticDataset(X, y, groups, variant="statistics_only")


def test_empty_dataset_is_refused_not_validated_vacuously():
    X, y, groups = frames()
    with pytest.raises(ValueError, match="dataset is empty"):
        CriticDataset(X.iloc[0:0], y.iloc[0:0], groups.iloc[0:0],
                      variant="statistics_only")


@pytest.mark.parametrize("missing", ["unit_id", "comparison_group_id"])
def test_groups_requires_both_identity_columns(missing):
    X, y, groups = frames()
    with pytest.raises(ValueError, match="missing required identity"):
        CriticDataset(X, y, groups.drop(columns=[missing]),
                      variant="statistics_only")


@pytest.mark.parametrize("column", ["unit_id", "comparison_group_id"])
@pytest.mark.parametrize("bad", ["", "   ", None, 7])
def test_group_identities_are_nonblank_strings(column, bad):
    X, y, groups = frames()
    groups.loc[groups.index[0], column] = bad
    with pytest.raises(ValueError, match="non-blank string"):
        CriticDataset(X, y, groups, variant="statistics_only")


def test_one_unit_cannot_map_to_two_comparison_groups():
    X, y, groups = frames()
    groups["unit_id"] = ["same-unit", "same-unit"]
    with pytest.raises(ValueError, match="maps to both comparison groups"):
        CriticDataset(X, y, groups, variant="statistics_only")


@pytest.mark.parametrize("valid", [0, 1, "ambiguous", "undiagnosed"])
def test_every_registered_observed_label_is_valid(valid):
    X, y, groups = frames()
    y = y.astype(object)
    y.iloc[0] = valid
    CriticDataset(X, y, groups, variant="statistics_only")


@pytest.mark.parametrize("bad", [True, False, 2, -1, "0", "unknown", None, 0.0])
def test_invalid_observed_labels_fail_closed(bad):
    X, y, groups = frames()
    y = y.astype(object)
    y.iloc[0] = bad
    with pytest.raises(ValueError, match="observed label"):
        CriticDataset(X, y, groups, variant="statistics_only")


def test_caller_mutation_cannot_cross_into_dataset_including_nested_features():
    X, y, groups = frames(variant="full")
    X["state_history"] = [[{"x": 1}], [{"x": 2}]]
    dataset = CriticDataset(X, y, groups, variant="full")

    X.at["trace-a", "state_history"][0]["x"] = 999
    X.at["trace-a", "error_magnitude"] = 999
    y.at["trace-a"] = 1
    groups.at["trace-a", "unit_id"] = "changed"

    assert dataset.X.at["trace-a", "state_history"] == [{"x": 1}]
    assert dataset.X.at["trace-a", "error_magnitude"] == 0.0
    assert dataset.y.at["trace-a"] == 0
    assert dataset.groups.at["trace-a", "unit_id"] == "u0"


def test_returned_copies_cannot_mutate_the_internal_boundary():
    X, y, groups = frames()
    dataset = CriticDataset(X, y, groups, variant="statistics_only")
    exposed = dataset.X
    exposed.at["trace-a", "error_magnitude"] = 123
    assert dataset.X.at["trace-a", "error_magnitude"] == 0.0


def test_model_input_returns_x_alone_and_no_live_internal_reference():
    X, y, groups = frames()
    dataset = CriticDataset(X, y, groups, variant="statistics_only")
    model_X = dataset.model_input()

    assert tuple(model_X.columns) == features_for("statistics_only")
    assert not {"observed_label", "unit_id", "comparison_group_id", "seed"} & set(
        model_X.columns
    )
    model_X.iloc[0, 0] = 999
    assert dataset.model_input().iloc[0, 0] == X.iloc[0, 0]


@pytest.mark.parametrize(
    ("X_value", "y_value", "groups_value", "message"),
    [([], pd.Series(dtype=object), pd.DataFrame(), "X must"),
     (pd.DataFrame(), [], pd.DataFrame(), "y must"),
     (pd.DataFrame(), pd.Series(dtype=object), [], "groups must")],
)
def test_container_types_fail_closed(X_value, y_value, groups_value, message):
    with pytest.raises(ValueError, match=message):
        CriticDataset(X_value, y_value, groups_value, variant="statistics_only")
