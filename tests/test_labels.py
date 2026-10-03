"""Week 6 pure label mapping tests; all outcomes are synthetic booleans."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bu.experiments.labels import (
    LabelAssignment,
    observed_label,
    summarize_assignments,
)


@pytest.mark.parametrize(
    ("data_works", "model_works", "expected"),
    [
        (True, False, 0),
        (False, True, 1),
        (True, True, "ambiguous"),
        (False, False, "undiagnosed"),
    ],
)
def test_plan_table_2_is_exhaustive(data_works, model_works, expected):
    assert observed_label(data_works, model_works) == expected


@pytest.mark.parametrize("bad", [0, 1, None, "true", [], object()])
@pytest.mark.parametrize("which", ["data", "model"])
def test_outcomes_must_be_exact_booleans(bad, which):
    kwargs = {"data_repair_works": True, "model_repair_works": False}
    kwargs[f"{which}_repair_works"] = bad
    with pytest.raises(ValueError, match="exact boolean"):
        observed_label(**kwargs)


def assignment(uid="u1", group="g1", intended="estimation", data=True, model=False):
    return LabelAssignment(
        unit_id=uid,
        comparison_group_id=group,
        intended_class=intended,
        data_repair_works=data,
        model_repair_works=model,
    )


def test_assignment_derives_label_and_is_immutable():
    record = assignment()
    assert record.observed_label == 0
    with pytest.raises(FrozenInstanceError):
        record.observed_label = 1


@pytest.mark.parametrize("field", ["unit_id", "comparison_group_id"])
@pytest.mark.parametrize("bad", ["", "   ", 7, None])
def test_assignment_refuses_invalid_identities(field, bad):
    kwargs = {"uid": "u1", "group": "g1"}
    kwargs["uid" if field == "unit_id" else "group"] = bad
    with pytest.raises(ValueError, match=field):
        assignment(**kwargs)


@pytest.mark.parametrize("bad", [0, 1, True, "", "observed_0"])
def test_assignment_keeps_intended_class_distinct_from_observed_label(bad):
    with pytest.raises(ValueError, match="intended_class"):
        assignment(intended=bad)


def test_exact_summary_counts_every_outcome_once():
    records = [
        assignment("u0", "g0", data=True, model=False),
        assignment("u1", "g1", data=False, model=True),
        assignment("ua", "ga", data=True, model=True),
        assignment("un", "gn", data=False, model=False),
        assignment("u0b", "g0b", data=True, model=False),
    ]
    summary = summarize_assignments(records)
    assert summary.as_dict() == {0: 2, 1: 1, "ambiguous": 1, "undiagnosed": 1}
    assert summary.total == len(records)


def test_summary_refuses_duplicate_statistical_units():
    with pytest.raises(ValueError, match="duplicate unit_id"):
        summarize_assignments([assignment("same"), assignment("same", "g2")])


def test_summary_refuses_non_assignment_objects():
    with pytest.raises(ValueError, match="LabelAssignment"):
        summarize_assignments([{"unit_id": "u1"}])


def test_empty_summary_is_exactly_zero():
    summary = summarize_assignments([])
    assert summary.as_dict() == {0: 0, 1: 0, "ambiguous": 0, "undiagnosed": 0}
    assert summary.total == 0


def test_api_warns_that_mapping_does_not_prove_repair_evidence():
    import bu.experiments.labels as labels

    warning = labels.__doc__.lower()
    assert "not" in warning and "evidence adapter" in warning
    assert "c-007" in warning and "end to end" in warning
