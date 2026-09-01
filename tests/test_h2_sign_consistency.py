"""Synthetic-only tests for the pure H2 sign-consistency boundary."""

from dataclasses import replace
import sys

import pytest

from bu import constants as K
from bu.experiments import h2_sign_consistency as H
from bu.streams import confirmatory_seeds


def _id(value: int) -> str:
    return f"{value:012x}"


def _two_class_rows(mask: int = 31) -> list[H.H2SeedUnitRatio]:
    rows: list[H.H2SeedUnitRatio] = []
    for offset, seed in enumerate(H.H2_SIGN_SEEDS):
        rows.extend(
            [
                H.H2SeedUnitRatio(_id(1), _id(101), seed, 0, 1.0),
                H.H2SeedUnitRatio(
                    _id(2),
                    _id(102),
                    seed,
                    1,
                    0.5 if mask & (1 << offset) else 1.0,
                ),
            ]
        )
    return rows


def test_sign_seed_registry_is_independently_derived_from_frozen_h2_policy():
    assert H.H2_SIGN_SEEDS == tuple(confirmatory_seeds(K.SEEDS_HYPOTHESIS))
    assert H.H2_SIGN_SEEDS == (1000, 1001, 1002, 1003, 1004)


@pytest.mark.parametrize("mask", range(32))
def test_all_32_five_seed_sign_patterns(mask):
    result = H.compute_h2_sign_consistency(_two_class_rows(mask))
    expected_seeds = tuple(
        seed
        for offset, seed in enumerate(H.H2_SIGN_SEEDS)
        if mask & (1 << offset)
    )
    assert result.seeds == H.H2_SIGN_SEEDS
    assert result.reproduced_seeds == expected_seeds
    assert result.n_reproduced == mask.bit_count()
    assert result.denominator == 5
    assert result.sign_consistency == mask.bit_count() / 5
    assert result.reliability_met is (mask == 31)
    assert [row.reproduced for row in result.per_seed] == [
        bool(mask & (1 << offset)) for offset in range(5)
    ]
    assert all(
        row.delta_observed_1_minus_0 < 0
        if row.reproduced
        else row.delta_observed_1_minus_0 == 0
        for row in result.per_seed
    )
    assert result.h2_verdict is None
    assert result.inference_performed is False
    assert result.comparison_groups_used_for_pairing is False


def test_equal_unit_weighting_does_not_deduplicate_or_pair_groups():
    rows = []
    specifications = (
        (_id(1), _id(100), 0, 0.2),
        (_id(2), _id(200), 0, 1.0),
        (_id(3), _id(300), 1, 0.1),
        (_id(4), _id(300), 1, 0.4),
        (_id(5), _id(400), 1, 0.7),
    )
    for seed in H.H2_SIGN_SEEDS:
        rows.extend(
            H.H2SeedUnitRatio(unit, group, seed, label, ratio)
            for unit, group, label, ratio in specifications
        )

    result = H.compute_h2_sign_consistency(rows)
    for contrast in result.per_seed:
        assert contrast.n_observed_0 == 2
        assert contrast.n_observed_1 == 3
        assert contrast.mean_ratio_observed_0 == pytest.approx(0.6)
        assert contrast.mean_ratio_observed_1 == pytest.approx(0.4)
        assert contrast.delta_observed_1_minus_0 == pytest.approx(-0.2)
        assert contrast.reproduced is True
    assert result.unit_weighting == "equal_unit"
    assert result.comparison_groups_retained is True
    assert [unit.comparison_group_id for unit in result.eligible_units].count(
        _id(300)
    ) == 2


def test_positive_delta_is_explicitly_non_reproducing_not_only_equality():
    rows = [
        replace(row, ratio_of_means=1.5)
        if row.observed_label == 1
        else row
        for row in _two_class_rows()
    ]
    result = H.compute_h2_sign_consistency(rows)
    assert result.reproduced_seeds == ()
    assert all(row.delta_observed_1_minus_0 == 0.5 for row in result.per_seed)
    assert all(row.reproduced is False for row in result.per_seed)


def test_input_order_does_not_change_result():
    rows = _two_class_rows(21)
    assert H.compute_h2_sign_consistency(rows) == H.compute_h2_sign_consistency(
        list(reversed(rows))
    )


def test_finite_extreme_ratios_do_not_overflow_class_means():
    rows = _two_class_rows(0)
    maximum = float(sys.float_info.max)
    rows = [
        replace(row, ratio_of_means=maximum)
        for row in rows
    ]
    result = H.compute_h2_sign_consistency(rows)
    assert all(row.mean_ratio_observed_0 == maximum for row in result.per_seed)
    assert all(row.mean_ratio_observed_1 == maximum for row in result.per_seed)
    assert all(row.delta_observed_1_minus_0 == 0 for row in result.per_seed)


@pytest.mark.parametrize(
    "label",
    [True, False, -1, 2, 0.0, "0", "ambiguous", "undiagnosed",
     "estimation", "hypothesis_class", None],
)
def test_non_exact_or_non_observed_labels_block(label):
    rows = _two_class_rows()
    rows[0] = replace(rows[0], observed_label=label)
    with pytest.raises(ValueError, match="observed_label"):
        H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize(
    "ratio", [-0.1, float("nan"), float("inf"), -float("inf"), 0, 1, True,
              "1.0", None],
)
def test_malformed_ratio_blocks(ratio):
    rows = _two_class_rows()
    rows[0] = replace(rows[0], ratio_of_means=ratio)
    with pytest.raises(ValueError, match="ratio_of_means"):
        H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize("ratio", [0.0, -0.0, sys.float_info.max])
def test_finite_nonnegative_float_ratios_are_accepted(ratio):
    rows = _two_class_rows()
    rows[0] = replace(rows[0], ratio_of_means=ratio)
    H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize(
    "field,value",
    [
        ("unit_id", ""),
        ("unit_id", " " * 12),
        ("unit_id", "a" * 11),
        ("unit_id", "a" * 13),
        ("unit_id", "A" * 12),
        ("unit_id", 1),
        ("comparison_group_id", "group"),
        ("comparison_group_id", "0" * 11),
        ("comparison_group_id", "0" * 13),
        ("comparison_group_id", None),
    ],
)
def test_malformed_unit_or_group_identity_blocks(field, value):
    rows = _two_class_rows()
    rows[0] = replace(rows[0], **{field: value})
    with pytest.raises(ValueError, match=field):
        H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize("seed", [999, 1005, True, 1000.0, "1000", None])
def test_nonregistered_or_nonexact_seed_blocks(seed):
    rows = _two_class_rows()
    rows[0] = replace(rows[0], seed=seed)
    with pytest.raises(ValueError, match="seed"):
        H.compute_h2_sign_consistency(rows)


def test_duplicate_unit_seed_blocks():
    rows = _two_class_rows()
    with pytest.raises(ValueError, match="duplicate unit-seed"):
        H.compute_h2_sign_consistency(rows + [rows[0]])


def test_one_units_missing_seed_blocks_even_when_every_global_seed_exists():
    rows = _two_class_rows()
    rows = [row for row in rows if not (row.unit_id == _id(1) and row.seed == 1004)]
    with pytest.raises(ValueError, match="exact five-seed"):
        H.compute_h2_sign_consistency(rows)


def test_missing_entire_seed_blocks():
    rows = [row for row in _two_class_rows() if row.seed != 1002]
    with pytest.raises(ValueError, match="exact five-seed"):
        H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize(
    "field,value", [("comparison_group_id", _id(999)), ("observed_label", 1)]
)
def test_unit_metadata_cannot_change_across_seeds(field, value):
    rows = _two_class_rows()
    target = next(
        index
        for index, row in enumerate(rows)
        if row.unit_id == _id(1) and row.seed == 1001
    )
    rows[target] = replace(rows[target], **{field: value})
    with pytest.raises(ValueError, match="changes comparison group or observed label"):
        H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize("label", [0, 1])
def test_either_empty_observed_class_blocks(label):
    rows = [replace(row, observed_label=label) for row in _two_class_rows()]
    with pytest.raises(ValueError, match="both observed repair classes"):
        H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize("rows", [[], (), None, "rows", {}, iter(())])
def test_malformed_or_empty_collection_blocks(rows):
    with pytest.raises(ValueError, match="nonempty exact list or tuple"):
        H.compute_h2_sign_consistency(rows)


@pytest.mark.parametrize("replacement", [None, object(), {"intended_class": "estimation"}])
def test_raw_or_alternate_provenance_rows_block(replacement):
    rows = _two_class_rows()
    rows[0] = replacement
    with pytest.raises(ValueError, match="exact H2SeedUnitRatio"):
        H.compute_h2_sign_consistency(rows)


def test_row_subclasses_are_not_a_lenient_door():
    class AlternateRow(H.H2SeedUnitRatio):
        pass

    rows = _two_class_rows()
    first = rows[0]
    rows[0] = AlternateRow(
        first.unit_id,
        first.comparison_group_id,
        first.seed,
        first.observed_label,
        first.ratio_of_means,
    )
    with pytest.raises(ValueError, match="exact H2SeedUnitRatio"):
        H.compute_h2_sign_consistency(rows)
