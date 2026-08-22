"""The W5 Friday balancer (D-115), on SYNTHETIC labelled inputs only.

Sol authorised this as completion of missed Week 5 scope: not reserve
consumption, not Week 6 execution, and it may not touch real labels until C-005
exists. Every fixture here is fabricated.
"""

from __future__ import annotations

import pytest

from bu import constants as K
from bu.critic.balance import (
    ESTIMATION, HYPOTHESIS_CLASS, BalancedSplit, LabelledUnit,
    assert_groups_do_not_span_splits, balance, balance_split, unit_weights,
)


def unit(uid, label, split="train", group=None, n_traces=100):
    return LabelledUnit(
        unit_id=uid, label=label, split=split,
        comparison_group_id=group or f"g-{uid}",
        eligible_traces=tuple(range(n_traces)),
    )


# --- the cap is a maximum, not an eligibility threshold ---------------------


def test_a_unit_below_the_cap_is_kept_whole_not_excluded():
    """Sol was explicit. Excluding small units would make inclusion a function
    of trace count, which is not a registered criterion."""
    units = [unit("a", ESTIMATION, n_traces=7), unit("b", HYPOTHESIS_CLASS, n_traces=90)]
    sel, man = balance_split(units, split="train")
    assert "a" in man["per_unit_trace_counts"], "the small unit was dropped"
    assert man["per_unit_trace_counts"]["a"] == 7, "it was not kept whole"
    assert "a" in man["units_below_cap"]


def test_a_small_unit_is_never_resampled_up_to_the_cap():
    sel, _ = balance_split(
        [unit("a", ESTIMATION, n_traces=3), unit("b", HYPOTHESIS_CLASS, n_traces=3)],
        split="train")
    for uid in ("a", "b"):
        traces = [t for u, t in zip(sel.unit_ids, sel.X_trace_ids) if u == uid]
        assert len(traces) == 3
        assert len(set(traces)) == 3, "traces were drawn with replacement"


def test_a_large_unit_is_capped_exactly_at_the_frozen_value():
    sel, man = balance_split(
        [unit("a", ESTIMATION, n_traces=500), unit("b", HYPOTHESIS_CLASS, n_traces=500)],
        split="train")
    assert set(man["per_unit_trace_counts"].values()) == {K.CRITIC_TRACE_CAP_PER_UNIT}


def test_a_unit_with_no_eligible_traces_is_refused_not_carried():
    with pytest.raises(ValueError, match="zero eligible failure"):
        balance_split([unit("a", ESTIMATION, n_traces=0),
                       unit("b", HYPOTHESIS_CLASS, n_traces=9)], split="train")


# --- balancing --------------------------------------------------------------


def test_classes_are_balanced_at_the_minority_count_within_the_split():
    units = ([unit(f"e{i}", ESTIMATION) for i in range(7)]
             + [unit(f"h{i}", HYPOTHESIS_CLASS) for i in range(3)])
    _, man = balance_split(units, split="train")
    assert man["units_per_class"] == 3
    assert len(man["selected_units"][str(ESTIMATION)]) == 3
    assert len(man["selected_units"][str(HYPOTHESIS_CLASS)]) == 3


def test_ambiguous_and_undiagnosed_units_are_excluded_before_balancing():
    units = ([unit(f"e{i}", ESTIMATION) for i in range(3)]
             + [unit(f"h{i}", HYPOTHESIS_CLASS) for i in range(3)]
             + [unit("amb", "ambiguous"), unit("und", "undiagnosed")])
    _, man = balance_split(units, split="train")
    assert set(man["excluded_undecidable"]) == {"amb", "und"}
    assert man["units_per_class"] == 3, "undecidable units inflated the balance"


def test_splits_are_balanced_independently():
    units = ([unit(f"e{i}", ESTIMATION, "train") for i in range(5)]
             + [unit(f"h{i}", HYPOTHESIS_CLASS, "train") for i in range(2)]
             + [unit(f"E{i}", ESTIMATION, "held_out") for i in range(4)]
             + [unit(f"H{i}", HYPOTHESIS_CLASS, "held_out") for i in range(4)])
    _, mans = balance(units, splits=("train", "held_out"))
    assert mans["train"]["units_per_class"] == 2
    assert mans["held_out"]["units_per_class"] == 4, (
        "the held-out split was balanced against another split's minority count"
    )


# --- determinism, and the hash that must not be Python's --------------------


def test_selection_is_identical_across_processes():
    """`hash()` is randomised by PYTHONHASHSEED, so a selection keyed on it is
    reproducible within a run and not across runs. This runs the balancer in a
    fresh interpreter with a different seed and requires the same answer."""
    import json, subprocess, sys, textwrap
    script = textwrap.dedent("""
        import json, sys
        sys.path.insert(0, "src")
        from bu.critic.balance import LabelledUnit, balance_split, ESTIMATION, HYPOTHESIS_CLASS
        # DELIBERATELY IMBALANCED: 12 vs 3, so m=3 and only 3 of the 12 are
        # chosen. An earlier version used 6 vs 6, where every unit is selected
        # and the ordering never matters -- the test passed even when the key
        # was Python's randomised hash(), which is exactly what it exists to
        # catch. A fixture that selects everything tests nothing.
        units = ([LabelledUnit(f"e{i}", ESTIMATION, "train", f"ge{i}", tuple(range(80)))
                  for i in range(12)]
                 + [LabelledUnit(f"h{i}", HYPOTHESIS_CLASS, "train", f"gh{i}",
                                 tuple(range(80))) for i in range(3)])
        _, man = balance_split(units, split="train")
        assert man["units_per_class"] == 3, "fixture is not selective"
        assert len(man["excluded_by_balancing"]) == 9, "fixture excludes nothing"
        print(json.dumps(man["selected_units"], sort_keys=True))
    """)
    outs = set()
    for seed in ("0", "12345"):
        r = subprocess.run([sys.executable, "-c", script], capture_output=True,
                           text=True, env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"})
        assert r.returncode == 0, r.stderr
        outs.add(r.stdout.strip())
    assert len(outs) == 1, f"selection changed with PYTHONHASHSEED: {outs}"


def test_trace_draws_are_reproducible():
    units = [unit("a", ESTIMATION, n_traces=400), unit("b", HYPOTHESIS_CLASS, n_traces=400)]
    first, _ = balance_split(units, split="train")
    second, _ = balance_split(units, split="train")
    assert first.X_trace_ids == second.X_trace_ids


# --- D-039, and the estimand -------------------------------------------------


def test_a_comparison_group_spanning_splits_is_refused():
    units = [unit("a", ESTIMATION, "train", group="shared"),
             unit("b", HYPOTHESIS_CLASS, "held_out", group="shared")]
    with pytest.raises(ValueError, match="spans splits"):
        assert_groups_do_not_span_splits(units)


def test_balance_runs_the_group_check_rather_than_only_offering_it():
    units = [unit("a", ESTIMATION, "train", group="shared"),
             unit("b", HYPOTHESIS_CLASS, "held_out", group="shared")]
    with pytest.raises(ValueError, match="spans splits"):
        balance(units, splits=("train", "held_out"))


def test_x_y_and_groups_stay_the_same_length_and_separate():
    units = [unit("a", ESTIMATION, n_traces=9), unit("b", HYPOTHESIS_CLASS, n_traces=90)]
    sel, _ = balance_split(units, split="train")
    n = len(sel.X_trace_ids)
    assert len(sel.y) == n and len(sel.groups) == n and len(sel.unit_ids) == n
    assert isinstance(sel, BalancedSplit)


def test_unit_weights_recover_the_unit_weighted_estimand():
    """A 50-trace unit and a 7-trace unit must count equally (D-044)."""
    units = [unit("big", ESTIMATION, n_traces=400), unit("small", HYPOTHESIS_CLASS, n_traces=7)]
    sel, _ = balance_split(units, split="train")
    w = unit_weights(sel)
    totals = {}
    for uid in sel.unit_ids:
        totals[uid] = totals.get(uid, 0.0) + w[uid]
    assert pytest.approx(totals["big"]) == 1.0
    assert pytest.approx(totals["small"]) == 1.0


# --- audit findings (D-117), each shown to have been silent before ----------


def test_a_split_that_balances_to_zero_fails_closed():
    """AUDIT: this returned an EMPTY evaluation set and raised nothing.

    Not hypothetical. Gate 2's second condition is literally whether the
    surviving per-class unit count still clears the MDE requirement, and D-089
    records that usable class counts may shrink once ambiguous and undiagnosed
    units are excluded. A split starved of one class is an anticipated outcome,
    and it used to produce a silent empty set from a balancer that ran perfectly.
    """
    with pytest.raises(ValueError, match="ZERO units per class"):
        balance_split([unit("e1", ESTIMATION), unit("e2", ESTIMATION)], split="train")


def test_all_undecidable_units_also_fail_closed():
    with pytest.raises(ValueError, match="ZERO units per class"):
        balance_split([unit("a", "ambiguous"), unit("b", "undiagnosed")], split="train")


def test_string_labels_do_not_silently_empty_the_set():
    """AUDIT: '0' is not ESTIMATION, so string labels were silently undecidable
    and the whole split came back empty with no signal."""
    with pytest.raises(ValueError, match="ZERO units per class"):
        balance_split([unit("a", "0"), unit("b", "1")], split="train")


def test_numpy_integer_labels_are_accepted():
    """The other half of the same question: a label-assignment step will emit
    numpy integers, and those must NOT be treated as undecidable."""
    import numpy as np
    sel, man = balance_split(
        [unit("a", np.int64(ESTIMATION)), unit("b", np.int32(HYPOTHESIS_CLASS))],
        split="train")
    assert man["units_per_class"] == 1
    assert len(sel.X_trace_ids) > 0


def test_a_duplicate_unit_id_is_refused():
    """AUDIT: two entries sharing a unit_id collapsed into one manifest row and
    would merge in `unit_weights`, counting two units as one under the
    registered UNIT-weighted estimand (D-044)."""
    with pytest.raises(ValueError, match="duplicate unit_id"):
        balance_split([unit("dup", ESTIMATION), unit("dup", HYPOTHESIS_CLASS)],
                      split="train")


def test_selection_does_not_depend_on_input_order():
    """Probed clean, and pinned so it stays that way."""
    units = ([unit(f"e{i}", ESTIMATION) for i in range(10)]
             + [unit(f"h{i}", HYPOTHESIS_CLASS) for i in range(3)])
    a, _ = balance_split(units, split="train")
    b, _ = balance_split(list(reversed(units)), split="train")
    assert a.X_trace_ids == b.X_trace_ids and a.unit_ids == b.unit_ids


def test_two_units_draw_different_traces():
    """Probed clean: the per-unit stream really is per-unit."""
    sel, _ = balance_split([unit("alpha", ESTIMATION, n_traces=400),
                            unit("beta", HYPOTHESIS_CLASS, n_traces=400)], split="train")
    a = [t for u, t in zip(sel.unit_ids, sel.X_trace_ids) if u == "alpha"]
    b = [t for u, t in zip(sel.unit_ids, sel.X_trace_ids) if u == "beta"]
    assert a != b, "both units drew the same trace indices"
