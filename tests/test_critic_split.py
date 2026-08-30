"""C-005, the grouped critic splitter, on SYNTHETIC inputs only (D-120, D-125).

Every fixture here is fabricated; no real label exists and none may be used
until authorised. All fixture label seeds are >= CONFIRMATORY_SEED_BASE (1000)
— the splitter itself enforces D-034 — except the fixtures deliberately
testing development-seed refusal. The adversarial purity fixture is labelled
*mixed INTENDED class*, never merely "mixed class": intended_class is
construction provenance and observed_label is the repair-derived target, and
conflating them is the exact defect Sol's delta-61 review corrected (D-128).

The split seed is not yet registered (its Change Record is future work), so
tests inject a synthetic value onto the bu.constants module object. That is
fixture injection, not a caller override — the public API exposes no seed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from bu import constants as K
from bu.config import STAGES
from bu.critic import balance
from bu.critic.balance import CANONICAL_SPLITS, UNDECIDABLE
from bu.critic.split import (
    INTENDED_CLASSES,
    SPLIT_SCHEMA_VERSION,
    ObservedTarget,
    SplitCandidate,
    SplitFloor,
    SplitTargets,
    assert_intended_class_purity,
    eligible_units,
    input_digest,
    split_units,
    validate_candidates,
    validate_targets,
)


def cand(uid, group, observed, intended="estimation", stage="exp1",
         seeds=(1000,)):
    return SplitCandidate(
        unit_id=uid, comparison_group_id=group, intended_class=intended,
        observed_label=observed, stage=stage, label_seeds=tuple(seeds),
    )


def uniform_targets(lo=1, hi=4, floors=None):
    return SplitTargets(
        observed={s: {0: ObservedTarget(lo, hi), 1: ObservedTarget(lo, hi)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(2, 1)} if floors is None else floors,
    )


def basic_candidates():
    """Six pair-groups (one observed 0, one observed 1 each; intended class
    varies BY group, never within one), one undecidable-only group, and one
    group mixing a decidable 0 with an ambiguous unit."""
    out = []
    for i in range(6):
        intended = "estimation" if i < 3 else "hypothesis_class"
        out.append(cand(f"u{i}a", f"g{i}", 0, intended))
        out.append(cand(f"u{i}b", f"g{i}", 1, intended))
    out.append(cand("u7a", "g7", "ambiguous"))
    out.append(cand("u7b", "g7", "undiagnosed"))
    out.append(cand("u8a", "g8", 0))
    out.append(cand("u8b", "g8", "ambiguous"))
    return out


@pytest.fixture
def split_seed(monkeypatch):
    """Inject a synthetic split seed: CRITIC_SPLIT_SEED has no Change Record
    yet, and the splitter fails closed without one."""
    monkeypatch.setattr(K, "CRITIC_SPLIT_SEED", 4242, raising=False)


def observed_counts(mapping, candidates):
    """Recomputed from the mapping and the inputs, never from the manifest."""
    counts = {s: {0: 0, 1: 0, "ambiguous": 0, "undiagnosed": 0}
              for s in CANONICAL_SPLITS}
    for c in candidates:
        key = c.observed_label if isinstance(c.observed_label, str) else int(
            c.observed_label)
        counts[mapping[c.unit_id]][key] += 1
    return counts


# --- assignment: total, exclusive, whole-group (D-039) -----------------------


def test_every_attempted_unit_receives_exactly_one_split(split_seed):
    candidates = basic_candidates()
    assert any(c.observed_label in UNDECIDABLE for c in candidates), \
        "fixture must contain undecidable units or totality is untested"
    mapping, _ = split_units(candidates, targets=uniform_targets())
    assert set(mapping.keys()) == {c.unit_id for c in candidates}
    assert set(mapping.values()) <= set(CANONICAL_SPLITS)
    by_group = {}
    for c in candidates:
        by_group.setdefault(c.comparison_group_id, set()).add(mapping[c.unit_id])
    assert all(len(splits) == 1 for splits in by_group.values()), (
        "a comparison group straddled a split boundary"
    )
    # The undecidable-only group also received a split (complete provenance).
    assert mapping["u7a"] in CANONICAL_SPLITS


def test_a_group_is_never_split_across_the_boundary_end_to_end(split_seed):
    """The splitter's own output feeds the balancer's public
    assert_groups_do_not_span_splits unmodified — one implementation, not a
    restatement (D-039)."""
    candidates = basic_candidates()
    assert any(
        sum(1 for c in candidates if c.comparison_group_id == g) > 1
        for g in {c.comparison_group_id for c in candidates}
    ), "fixture needs a multi-unit group or the invariant is vacuous"
    mapping, _ = split_units(candidates, targets=uniform_targets())
    traces = {c.unit_id: tuple(range(5)) for c in candidates}
    units = eligible_units(candidates, mapping, traces)
    balance.assert_groups_do_not_span_splits(units)  # must not raise


# --- observed vs intended, kept distinct (D-128) -----------------------------


def test_an_intended_pure_group_with_mixed_observed_outcomes_is_accepted(
        split_seed):
    """Observed-label mixing within a group is scientific information, never
    an integrity violation. Only INTENDED mixing is refused."""
    mix = [
        cand("m0", "gMix", 0, "hypothesis_class"),
        cand("m1", "gMix", 1, "hypothesis_class"),
        cand("m2", "gMix", "ambiguous", "hypothesis_class"),
        cand("m3", "gMix", "undiagnosed", "hypothesis_class"),
    ]
    assert {c.observed_label for c in mix} == {0, 1, "ambiguous", "undiagnosed"}
    others = []
    for i in range(5):
        others.append(cand(f"p{i}a", f"gp{i}", 0))
        others.append(cand(f"p{i}b", f"gp{i}", 1))
    mapping, manifest = split_units(mix + others, targets=uniform_targets(1, 3))
    split = mapping["m0"]
    assert all(mapping[c.unit_id] == split for c in mix)
    per = manifest["per_split"][split]
    assert per["ambiguous"] >= 1 and per["undiagnosed"] >= 1, (
        "the mixed group's observed counts never reached the manifest"
    )


def test_a_mixed_INTENDED_class_group_is_refused():
    """The fixture is labelled mixed INTENDED class, per the spec: a group is
    built on one axis, so intended mixing is a construction-integrity error."""
    mixed_intended = [
        cand("a", "gShared", 0, intended="estimation"),
        cand("b", "gShared", 0, intended="hypothesis_class"),
    ]
    assert len({c.intended_class for c in mixed_intended}) == 2
    assert len({c.observed_label for c in mixed_intended}) == 1, (
        "the fixture must mix ONLY the intended class, or the test cannot "
        "distinguish the two refusal grounds"
    )
    with pytest.raises(ValueError, match="intended"):
        assert_intended_class_purity(mixed_intended)
    with pytest.raises(ValueError, match="intended"):
        split_units(mixed_intended, targets=uniform_targets())


def test_allocation_targets_are_computed_on_observed_not_intended_counts(
        split_seed):
    """Every unit is built 'estimation' but half observe label 1: the fixture
    is infeasible under intended counts (no intended hypothesis_class exists),
    so a conflating allocator refuses — the direct D-128 defect."""
    candidates = []
    for i in range(6):
        candidates.append(cand(f"d{i}a", f"gd{i}", 0, "estimation"))
        candidates.append(cand(f"d{i}b", f"gd{i}", 1, "estimation"))
    assert all(c.intended_class == "estimation" for c in candidates)
    assert sum(1 for c in candidates if c.observed_label == 1) == 6, (
        "intended and observed counts must diverge or the test is vacuous"
    )
    mapping, manifest = split_units(candidates, targets=uniform_targets())
    counts = observed_counts(mapping, candidates)
    for s in CANONICAL_SPLITS:
        assert 1 <= counts[s][0] <= 4 and 1 <= counts[s][1] <= 4
        assert manifest["per_split"][s]["intended_class_counts"][
            "hypothesis_class"] == 0


def test_allocation_hits_observed_targets_within_declared_ranges(split_seed):
    candidates = basic_candidates()
    targets = uniform_targets()
    mapping, _ = split_units(candidates, targets=targets)
    counts = observed_counts(mapping, candidates)
    for s in CANONICAL_SPLITS:
        for cls in (0, 1):
            rng = targets.observed[s][cls]
            assert rng.lo <= counts[s][cls] <= rng.hi, (
                f"split {s} observed class {cls} landed outside the declared "
                "range"
            )
    assert sum(counts[s][0] for s in CANONICAL_SPLITS) == 7
    assert sum(counts[s][1] for s in CANONICAL_SPLITS) == 6


# --- floors, stated on surviving observed-decidable units (DEV-012) ----------


@pytest.mark.parametrize("floor,fragment", [
    # Pair-sum floor: attempted held-out counts could reach 6, but only 4
    # observed-decidable units exist in the whole fixture.
    (SplitFloor(min_surviving_observed=5, min_observed_per_class=1),
     "achieved 4"),
    # Per-class floor folded into effective lower bounds: only 2 observed-0
    # units exist against a registered 3.
    (SplitFloor(min_surviving_observed=0, min_observed_per_class=3),
     "deficit 1"),
])
def test_heldout_floor_is_enforced_on_surviving_observed_decidable_units(
        split_seed, floor, fragment):
    """An ambiguous-heavy allocation meets attempted counts and still fails
    the floor, because the floor is on SURVIVING observed-decidable units."""
    candidates = [
        cand("a0", "gA", 0), cand("a1", "gA", 1),
        cand("a2", "gA", "ambiguous"), cand("a3", "gA", "ambiguous"),
        cand("a4", "gA", "ambiguous"), cand("a5", "gA", "ambiguous"),
        cand("b0", "gB", 0), cand("b1", "gB", 1),
    ]
    assert sum(1 for c in candidates if c.observed_label in UNDECIDABLE) >= 4, (
        "the fixture must be ambiguous-heavy or attempted and surviving "
        "counts do not diverge"
    )
    targets = SplitTargets(
        observed={s: {0: ObservedTarget(0, 10), 1: ObservedTarget(0, 10)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": floor},
    )
    with pytest.raises(ValueError) as exc:
        split_units(candidates, targets=targets)
    message = str(exc.value)
    assert fragment in message, "the refusal must carry the exact arithmetic"
    assert "observed" in message, (
        "adequacy vocabulary must name OBSERVED labels (D-128)"
    )


def test_the_heldout_floor_is_not_silently_applied_to_train_or_validation(
        split_seed):
    """Train and validation take a floor only if one is separately registered
    (spec: 'not automatically applied')."""
    candidates = [
        cand("h0", "gH", 0), cand("h1", "gH", 0),
        cand("h2", "gH", 1), cand("h3", "gH", 1),
        cand("t0", "gT", 0),
        cand("v0", "gV", 1),
    ]
    targets = SplitTargets(
        observed={
            "train": {0: ObservedTarget(0, 1), 1: ObservedTarget(0, 1)},
            "validation": {0: ObservedTarget(0, 1), 1: ObservedTarget(0, 1)},
            "held_out": {0: ObservedTarget(2, 2), 1: ObservedTarget(2, 2)},
        },
        floors={"held_out": SplitFloor(min_surviving_observed=4,
                                       min_observed_per_class=1)},
    )
    mapping, manifest = split_units(candidates, targets=targets)
    assert set(manifest["floor_adequacy"].keys()) == {"held_out"}
    for s in ("train", "validation"):
        assert manifest["per_split"][s]["surviving_observed_decidable"] < 4, (
            "the fixture must leave a non-floored split below the held-out "
            "floor value, or nothing distinguishes applying it from not"
        )


# --- infeasibility fails closed with the exact arithmetic --------------------


def test_an_infeasible_whole_group_target_is_refused_with_the_exact_shortfall(
        split_seed):
    """Aggregate counts fit, but the one four-unit group is indivisible
    (D-039), so no whole-group assignment reaches 2/2: refuse with the
    numbers, no partial output, no group splitting."""
    candidates = [
        cand("b1", "gBig", 0), cand("b2", "gBig", 0),
        cand("b3", "gBig", 0), cand("b4", "gBig", 0),
        cand("s1", "gSmall", 1),
    ]
    targets = SplitTargets(
        observed={
            "train": {0: ObservedTarget(2, 2), 1: ObservedTarget(0, 1)},
            "validation": {0: ObservedTarget(2, 2), 1: ObservedTarget(0, 1)},
            "held_out": {0: ObservedTarget(0, 0), 1: ObservedTarget(0, 1)},
        },
        floors={"held_out": SplitFloor(0, 0)},
    )
    with pytest.raises(ValueError) as exc:
        split_units(candidates, targets=targets)
    message = str(exc.value)
    assert "shortfall 2" in message and "excess 2" in message, (
        "the refusal must state the exact per-split arithmetic"
    )
    assert "lo=2" in message and "achieved=" in message
    assert "observed class 0" in message


def test_a_feasible_swap_case_is_not_mislabeled_infeasible(split_seed):
    """A single-move local minimum is not an infeasibility proof.

    The witness requires swapping two groups: neither individual move improves
    the heuristic violation, so the old repair reached fixpoint and refused.
    The complete fallback must recover a valid whole-group assignment.
    """
    profiles = {"g0": (2, 1), "g1": (3, 1), "g2": (3, 0), "g3": (1, 1)}
    candidates = []
    for group, (n0, n1) in profiles.items():
        candidates.extend(cand(f"{group}-0-{i}", group, 0) for i in range(n0))
        candidates.extend(cand(f"{group}-1-{i}", group, 1) for i in range(n1))
    targets = SplitTargets(
        observed={
            "train": {0: ObservedTarget(3, 3), 1: ObservedTarget(1, 1)},
            "validation": {0: ObservedTarget(1, 1), 1: ObservedTarget(1, 1)},
            "held_out": {0: ObservedTarget(5, 5), 1: ObservedTarget(1, 1)},
        },
        floors={"held_out": SplitFloor(2, 1)},
    )
    mapping, manifest = split_units(candidates, targets=targets)
    counts = observed_counts(mapping, candidates)
    assert (counts["train"][0], counts["train"][1]) == (3, 1)
    assert (counts["validation"][0], counts["validation"][1]) == (1, 1)
    assert (counts["held_out"][0], counts["held_out"][1]) == (5, 1)
    assert manifest["n_groups"] == 4


@pytest.mark.parametrize("lo,hi,fragment", [
    (2, 4, "deficit 3"),   # sum(lo)=6 over 3 available
    (0, 0, "excess 3"),    # sum(hi)=0 under 3 that must be assigned
])
def test_aggregate_infeasibility_reports_provable_deficit_and_excess(
        split_seed, lo, hi, fragment):
    """Total assignment makes an excess over sum(hi) as infeasible as a
    deficit under sum(lo); both directions refuse with the exact number."""
    candidates = []
    for i in range(3):
        candidates.append(cand(f"e{i}", f"ge{i}", 0))
        candidates.append(cand(f"f{i}", f"ge{i}", 1))
    targets = SplitTargets(
        observed={s: {0: ObservedTarget(lo, hi), 1: ObservedTarget(0, 2)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(0, 0)},
    )
    with pytest.raises(ValueError, match="proven in aggregate") as exc:
        split_units(candidates, targets=targets)
    assert fragment in str(exc.value)
    assert "observed class 0" in str(exc.value)


# --- eligibility is a separate, later step (Sol, delta 61) -------------------


def test_undecidable_units_receive_splits_and_are_reported_per_split(
        split_seed):
    candidates = basic_candidates()
    n_amb = sum(1 for c in candidates if c.observed_label == "ambiguous")
    n_und = sum(1 for c in candidates if c.observed_label == "undiagnosed")
    assert n_amb == 2 and n_und == 1, "fixture must carry undecidables"
    mapping, manifest = split_units(candidates, targets=uniform_targets())
    for c in candidates:
        assert c.unit_id in mapping
    assert sum(manifest["per_split"][s]["ambiguous"]
               for s in CANONICAL_SPLITS) == n_amb
    assert sum(manifest["per_split"][s]["undiagnosed"]
               for s in CANONICAL_SPLITS) == n_und


def test_eligibility_boundary_passes_only_observed_decidable_records(
        split_seed):
    """End to end against the UNMODIFIED certified balancer: the boundary
    excludes undecidables first, so balance() has nothing to exclude and
    every split's excluded_undecidable is empty."""
    candidates = basic_candidates()
    assert any(c.observed_label in UNDECIDABLE for c in candidates), (
        "without undecidable inputs the boundary has nothing to prove"
    )
    mapping, _ = split_units(candidates, targets=uniform_targets())
    traces = {c.unit_id: tuple(range(5)) for c in candidates}
    units = eligible_units(candidates, mapping, traces)
    assert {u.label for u in units} <= {0, 1}
    assert len(units) == sum(
        1 for c in candidates if c.observed_label in (0, 1))
    _, manifests = balance.balance(units)
    for s, manifest in manifests.items():
        assert manifest["excluded_undecidable"] == [], (
            f"split {s}: the balancer received something to exclude — an "
            "undecidable leaked through the eligibility boundary"
        )


def test_end_to_end_split_then_balance_is_one_implementation(split_seed):
    """candidates -> split_units -> eligible_units -> balance() runs green,
    and the balanced manifests' unit_to_comparison_group is consistent with
    the split manifest's group_to_split — no invariant restated locally."""
    candidates = basic_candidates()
    mapping, split_manifest = split_units(candidates, targets=uniform_targets())
    traces = {c.unit_id: tuple(range(5)) for c in candidates}
    units = eligible_units(candidates, mapping, traces)
    selections, manifests = balance.balance(units)
    assert any(len(sel.X_trace_ids) > 0 for sel in selections.values()), (
        "the pipeline selected nothing; the end-to-end claim is vacuous"
    )
    for s, manifest in manifests.items():
        for uid, group in manifest["unit_to_comparison_group"].items():
            assert split_manifest["group_to_split"][group] == s, (
                f"unit {uid}: balanced into {s} but its group was split "
                f"to {split_manifest['group_to_split'][group]}"
            )


# --- split names have exactly one source (Sol, delta 54/55) ------------------


def test_split_names_are_the_balancers_not_a_second_source(split_seed):
    """Deliberate mechanism-level assert, required by the spec's single-source
    rule: a copied tuple drifts when the balancer's changes."""
    import bu.critic.split as split_module
    assert split_module.CANONICAL_SPLITS is balance.CANONICAL_SPLITS
    _, manifest = split_units(basic_candidates(), targets=uniform_targets())
    assert set(manifest["per_split"].keys()) == set(balance.CANONICAL_SPLITS)
    assert set(manifest["group_to_split"].values()) <= set(
        balance.CANONICAL_SPLITS)


def test_a_noncanonical_split_name_in_targets_is_refused():
    targets = SplitTargets(
        observed={
            "train": {0: ObservedTarget(1, 4), 1: ObservedTarget(1, 4)},
            "validation": {0: ObservedTarget(1, 4), 1: ObservedTarget(1, 4)},
            "held-out": {0: ObservedTarget(1, 4), 1: ObservedTarget(1, 4)},
        },
        floors={"held_out": SplitFloor(2, 1)},
    )
    with pytest.raises(ValueError, match="not canonical"):
        validate_targets(targets)


def test_targets_must_name_all_three_canonical_splits():
    """With total exclusive assignment, an uncovered split cannot lawfully
    absorb units — it must not become a silent dumping ground."""
    targets = SplitTargets(
        observed={
            "train": {0: ObservedTarget(1, 4), 1: ObservedTarget(1, 4)},
            "validation": {0: ObservedTarget(1, 4), 1: ObservedTarget(1, 4)},
        },
        floors={"held_out": SplitFloor(2, 1)},
    )
    with pytest.raises(ValueError, match="no observed range"):
        validate_targets(targets)


@pytest.mark.parametrize("targets,match", [
    (SplitTargets(
        observed={s: {True: ObservedTarget(1, 4), 0: ObservedTarget(1, 4)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(2, 1)}), "boolean"),
    (SplitTargets(
        observed={s: {0: ObservedTarget(1, 4)} for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(2, 1)}), "exactly the integers"),
    (SplitTargets(
        observed={s: {0: ObservedTarget(True, 4), 1: ObservedTarget(1, 4)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(2, 1)}), "boolean"),
    (SplitTargets(
        observed={s: {0: ObservedTarget(1.5, 4), 1: ObservedTarget(1, 4)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(2, 1)}), "exact integer"),
    (SplitTargets(
        observed={s: {0: ObservedTarget(5, 4), 1: ObservedTarget(1, 4)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(2, 1)}), "lo=5 > hi=4"),
    (SplitTargets(
        observed={s: {0: ObservedTarget(1, 4), 1: ObservedTarget(1, 4)}
                  for s in CANONICAL_SPLITS},
        floors={"train": SplitFloor(2, 1)}), "held_out"),
])
def test_target_class_keys_and_bounds_are_validated(targets, match):
    """Exact-integer discipline on the registered parameters themselves
    (delta 55): booleans before the integer check, no coercion, lo <= hi, and
    the mandatory held-out floor declared."""
    validate_targets(uniform_targets())  # the well-formed case passes
    with pytest.raises(ValueError, match=match):
        validate_targets(targets)


@pytest.mark.parametrize("targets,match", [
    (SplitTargets(observed=None, floors={}), "observed must be a mapping"),
    (SplitTargets(observed={s: None for s in CANONICAL_SPLITS},
                  floors={"held_out": SplitFloor(0, 0)}),
     "must map observed classes"),
    (SplitTargets(
        observed={s: {0: ObservedTarget(0, 1), 1: ObservedTarget(0, 1)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(0, 2)}),
     "exceeds an observed-class upper bound"),
    (SplitTargets(
        observed={s: {0: ObservedTarget(0, 1), 1: ObservedTarget(0, 1)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(3, 0)}),
     r"exceeds hi0\+hi1"),
])
def test_cross_field_target_contradictions_fail_before_allocation(targets, match):
    with pytest.raises(ValueError, match=match):
        validate_targets(targets)


# --- input validation, mirroring the balancer's certified history ------------


def test_the_splitter_refuses_an_empty_candidate_list():
    with pytest.raises(ValueError, match="zero attempted units"):
        split_units([], targets=uniform_targets())


def test_duplicate_unit_ids_are_refused():
    """One content-hashed unit twice — under two different group ids — could
    reach two splits (the upstream mirror of the balancer's guard)."""
    validate_candidates([cand("a", "g1", 0)])  # the well-formed case passes
    with pytest.raises(ValueError, match="duplicate unit_id"):
        validate_candidates([cand("dup", "g1", 0), cand("dup", "g2", 1)])


@pytest.mark.parametrize("unit_id", ["", "   ", 7, None])
def test_unit_ids_must_be_nonblank_strings(unit_id):
    with pytest.raises(ValueError, match="unit_id.*non-blank string"):
        validate_candidates([cand(unit_id, "g1", 0)])


def test_boolean_observed_labels_are_refused_before_the_integer_check():
    """True == 1 and bool subclasses int, so the boolean branch must fire
    first or True silently becomes an observed hypothesis-class label."""
    with pytest.raises(ValueError, match="boolean observed_label"):
        validate_candidates([cand("a", "g1", True)])


@pytest.mark.parametrize("bad", ["0", 4.9, "Ambiguous", None])
def test_invalid_observed_labels_are_refused_not_treated_as_undecidable(bad):
    """A type slip must not vanish into the undecidable category, which
    exists for a different reason (Sol, delta 54)."""
    validate_candidates([cand("ok", "g0", "ambiguous")])  # well-formed passes
    with pytest.raises(ValueError, match="observed_label"):
        validate_candidates([cand("a", "g1", bad)])


@pytest.mark.parametrize("bad", [0, 1, True, "hypothesis-class"])
def test_intended_class_is_a_named_string_not_an_integer(bad):
    """Transposing the two class fields must fail loudly in both directions
    (D-128): integers are refused here, and the named strings are refused as
    observed labels."""
    for good in INTENDED_CLASSES:
        validate_candidates([cand("ok", "g0", 0, intended=good)])
    with pytest.raises(ValueError, match="intended_class"):
        validate_candidates([cand("a", "g1", 0, intended=bad)])
    with pytest.raises(ValueError, match="observed_label"):
        validate_candidates([cand("b", "g2", "estimation")])


@pytest.mark.parametrize("stage", ["", "unknown", "exp9", None])
def test_missing_or_unknown_stage_metadata_fails_closed(stage):
    """C-007 at the splitter: provenance is refused, not defaulted."""
    validate_candidates([cand("ok", "g0", 0, stage="exp1")])
    with pytest.raises(ValueError, match="stage"):
        validate_candidates([cand("a", "g1", 0, stage=stage)])


@pytest.mark.parametrize("stage", [s for s in STAGES if s != "pilot"])
def test_development_label_seeds_are_refused_at_the_splitter(stage):
    """A planted sub-1000 record cannot reach this critic path, whatever the
    stage — one arm passing is not evidence about another (D-034, D-055)."""
    validate_candidates([cand("ok", "g0", 0, stage=stage)])
    with pytest.raises(ValueError, match="development seeds"):
        validate_candidates([cand("a", "g1", 0, stage=stage,
                                  seeds=(1000, 999))])


def test_pilot_stage_cannot_reach_the_splitter_at_a_confirmatory_seed():
    with pytest.raises(ValueError, match="pilot"):
        validate_candidates([cand("a", "g1", 0, stage="pilot", seeds=(1000,))])


def test_blank_comparison_group_ids_are_refused():
    """A blank group id would make a unit its own group and evade D-039."""
    with pytest.raises(ValueError, match="comparison_group_id"):
        validate_candidates([cand("a", "", 0)])
    with pytest.raises(ValueError, match="comparison_group_id"):
        validate_candidates([cand("a", "   ", 0)])


def test_a_non_candidate_element_is_refused_positively():
    with pytest.raises(ValueError, match="not a SplitCandidate"):
        validate_candidates([{"unit_id": "a"}])


# --- the seed: registered, never caller-overridable --------------------------


def test_the_split_seed_is_not_caller_overridable_and_absence_fails_closed(
        monkeypatch):
    with pytest.raises(TypeError):
        split_units(basic_candidates(), targets=uniform_targets(), seed=1)
    monkeypatch.delattr(K, "CRITIC_SPLIT_SEED", raising=False)
    with pytest.raises(ValueError, match="Change Record"):
        split_units(basic_candidates(), targets=uniform_targets())


# --- determinism across processes (D-115) ------------------------------------


def test_mapping_is_identical_across_processes_and_hash_seeds():
    """`hash()` is randomised by PYTHONHASHSEED, so an allocation touched by
    it — or by set/dict iteration order — is reproducible within a run and
    not across runs. Fresh interpreters under two hash seeds, twice each,
    must produce one unique mapping and manifest. The fixture is SELECTIVE:
    slack on both sides of every aggregate bound, so more than one assignment
    satisfies the ranges and the allocator makes real choices — a fixture
    where every allocation is forced would pass vacuously."""
    import json
    import os
    import subprocess
    import sys
    import textwrap
    from pathlib import Path

    script = textwrap.dedent("""
        import json, sys
        sys.path.insert(0, "src")
        import bu.constants as K
        K.CRITIC_SPLIT_SEED = 4242  # fixture injection; the API takes no seed
        from bu.critic.balance import CANONICAL_SPLITS
        from bu.critic.split import (ObservedTarget, SplitCandidate,
                                     SplitFloor, SplitTargets, split_units)

        def cand(uid, group, observed):
            return SplitCandidate(uid, group, "estimation", observed,
                                  "exp1", (1000,))

        profiles = {"gA": (3, 1), "gB": (2, 2), "gC": (1, 0), "gD": (0, 1),
                    "gE": (1, 1), "gF": (1, 1)}
        cands = []
        for g, (n0, n1) in sorted(profiles.items()):
            for i in range(n0):
                cands.append(cand(g + "z" + str(i), g, 0))
            for i in range(n1):
                cands.append(cand(g + "o" + str(i), g, 1))
        cands.append(cand("gGa", "gG", "ambiguous"))
        cands.append(cand("gGu", "gG", "undiagnosed"))

        targets = SplitTargets(
            observed={s: {0: ObservedTarget(1, 4), 1: ObservedTarget(1, 3)}
                      for s in CANONICAL_SPLITS},
            floors={"held_out": SplitFloor(2, 1)},
        )
        a0 = sum(n for n, _ in profiles.values())
        a1 = sum(n for _, n in profiles.values())
        assert 3 < a0 < 12 and 3 < a1 < 9, "fixture is not selective"
        assert profiles["gE"] == profiles["gF"], \\
            "no profile-identical pair: the tie path is unexercised"
        mapping, manifest = split_units(cands, targets=targets)
        print(json.dumps({"mapping": mapping, "manifest": manifest},
                         sort_keys=True))
    """)
    root = Path(__file__).resolve().parents[1]
    outs = set()
    for hash_seed in ("0", "12345"):
        for _ in range(2):
            r = subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True,
                cwd=str(root), env={**os.environ, "PYTHONHASHSEED": hash_seed},
            )
            assert r.returncode == 0, r.stderr
            outs.add(r.stdout.strip())
    assert len(outs) == 1, f"allocation changed with PYTHONHASHSEED: {outs}"
    payload = json.loads(next(iter(outs)))
    assert payload["manifest"]["n_groups"] == 7, "fixture drifted"


def test_the_blake2b_key_breaks_a_genuine_tie_deterministically(
    split_seed, monkeypatch
):
    """Two profile-identical groups the targets force into DIFFERENT splits:
    nothing but the keyed hash separates them, so this exercises the
    tie-breaker path rather than assuming it — and reversed input order must
    not change the outcome (position is not a key)."""
    cands = [
        cand("x0", "gX", 0), cand("x1", "gX", 1),
        cand("y0", "gY", 0), cand("y1", "gY", 1),
    ]
    targets = SplitTargets(
        observed={
            "train": {0: ObservedTarget(1, 1), 1: ObservedTarget(1, 1)},
            "validation": {0: ObservedTarget(1, 1), 1: ObservedTarget(1, 1)},
            "held_out": {0: ObservedTarget(0, 0), 1: ObservedTarget(0, 0)},
        },
        floors={"held_out": SplitFloor(0, 0)},
    )
    first, _ = split_units(cands, targets=targets)
    again, _ = split_units(cands, targets=targets)
    reversed_input, _ = split_units(list(reversed(cands)), targets=targets)
    assert first == again == reversed_input
    assert {first["x0"], first["y0"]} == {"train", "validation"}, (
        "the two tied groups must be separated across the two floored-open "
        "splits"
    )
    alternatives = []
    for seed in range(4243, 4260):
        monkeypatch.setattr(K, "CRITIC_SPLIT_SEED", seed, raising=False)
        mapping, _ = split_units(cands, targets=targets)
        alternatives.append(mapping)
    assert any(mapping != first for mapping in alternatives), (
        "changing the registered split seed never changed a genuine tie; a "
        "lexical tie-breaker that ignores the seed would pass the old test"
    )


def test_assignment_does_not_depend_on_input_order(split_seed):
    candidates = basic_candidates()
    mapping_a, manifest_a = split_units(candidates, targets=uniform_targets())
    mapping_b, manifest_b = split_units(list(reversed(candidates)),
                                        targets=uniform_targets())
    assert mapping_a == mapping_b
    assert manifest_a == manifest_b


# --- the manifest (SPLIT_SCHEMA_VERSION = 1; D-072, D-118, D-121) ------------


def test_manifest_counts_recompute_from_mapping_and_inputs(split_seed):
    """Every count cross-checked against the INPUTS, never against the
    manifest itself (D-072)."""
    candidates = basic_candidates()
    mapping, manifest = split_units(candidates, targets=uniform_targets())
    assert manifest["unit_to_split"] == mapping
    assert manifest["n_attempted_units"] == len(candidates)
    assert manifest["input_digest"] == input_digest(candidates)
    records = [
        {
            "unit_id": c.unit_id,
            "comparison_group_id": c.comparison_group_id,
            "intended_class": c.intended_class,
            "observed_label": c.observed_label,
            "stage": c.stage,
            "label_seeds": list(c.label_seeds),
        }
        for c in sorted(candidates, key=lambda c: c.unit_id)
    ]
    independent_blob = json.dumps(
        records, sort_keys=True, separators=(",", ":")
    ).encode()
    assert manifest["input_digest"] == hashlib.sha256(independent_blob).hexdigest()
    counts = observed_counts(mapping, candidates)
    for s in CANONICAL_SPLITS:
        per = manifest["per_split"][s]
        assert per["observed_decidable_0"] == counts[s][0]
        assert per["observed_decidable_1"] == counts[s][1]
        assert per["ambiguous"] == counts[s]["ambiguous"]
        assert per["undiagnosed"] == counts[s]["undiagnosed"]
        assert per["surviving_observed_decidable"] == counts[s][0] + counts[s][1]
        assert per["observed_min_class_count"] == min(counts[s][0], counts[s][1])
        assert per["attempted_units"] == sum(
            1 for c in candidates if mapping[c.unit_id] == s)
        for intended in INTENDED_CLASSES:
            assert per["intended_class_counts"][intended] == sum(
                1 for c in candidates
                if mapping[c.unit_id] == s and c.intended_class == intended)
    for c in candidates:
        assert manifest["group_to_split"][c.comparison_group_id] == mapping[
            c.unit_id]


def test_input_digest_commits_to_every_candidate_field():
    """Omitting any provenance field must change the delivered-byte digest."""
    original = cand("u", "g", 0, intended="estimation", stage="exp1",
                    seeds=(1000, 1001))
    baseline = input_digest([original])
    variants = [
        replace(original, unit_id="u2"),
        replace(original, comparison_group_id="g2"),
        replace(original, intended_class="hypothesis_class"),
        replace(original, observed_label=1),
        replace(original, stage="exp2a"),
        replace(original, label_seeds=(1000, 1002)),
    ]
    assert all(input_digest([variant]) != baseline for variant in variants)


def test_manifest_schema_version_is_one_and_names_both_class_concepts(
        split_seed):
    """Versioned from 1 before any real manifest exists (D-121); every
    adequacy field names OBSERVED labels; intended counts are diagnostics
    under string keys and never stand in for observed counts (D-128)."""
    assert SPLIT_SCHEMA_VERSION == 1
    _, manifest = split_units(basic_candidates(), targets=uniform_targets())
    assert manifest["schema_version"] == 1
    for s in CANONICAL_SPLITS:
        per = manifest["per_split"][s]
        assert {"observed_decidable_0", "observed_decidable_1",
                "observed_min_class_count",
                "surviving_observed_decidable"} <= set(per.keys())
        assert set(per["intended_class_counts"].keys()) == set(INTENDED_CLASSES)
    for adequacy in manifest["floor_adequacy"].values():
        assert all("observed" in field for field in adequacy), (
            "an adequacy field failed to name the observed labels (D-128)"
        )
    assert "split_seed" in manifest and "input_digest" in manifest
    assert "group_to_split" in manifest, "the mapping, not a name set (D-118)"


# --- the eligibility boundary's join guards ----------------------------------


@pytest.fixture
def split_result(split_seed):
    candidates = basic_candidates()
    mapping, _ = split_units(candidates, targets=uniform_targets())
    traces = {c.unit_id: tuple(range(5)) for c in candidates}
    return candidates, mapping, traces


def test_eligible_units_requires_assignment_to_cover_exactly_the_candidates(
        split_result):
    candidates, mapping, traces = split_result
    assert eligible_units(candidates, mapping, traces), "well-formed case"
    short = dict(mapping)
    short.pop(candidates[0].unit_id)
    with pytest.raises(ValueError, match="missing unit"):
        eligible_units(candidates, short, traces)
    with pytest.raises(ValueError, match="unknown unit"):
        eligible_units(candidates, {**mapping, "ghost": "train"}, traces)
    typo = dict(mapping)
    typo[candidates[0].unit_id] = "held-out"
    with pytest.raises(ValueError, match="not canonical"):
        eligible_units(candidates, typo, traces)
    with pytest.raises(ValueError, match="assignment must be a mapping"):
        eligible_units(candidates, None, traces)
    with pytest.raises(ValueError, match="traces_by_unit must be a mapping"):
        eligible_units(candidates, mapping, None)


def test_a_decidable_unit_missing_from_the_trace_inventory_is_refused(
        split_result):
    """Defaulting a failed join to zero traces would let the balancer's
    zero-trace refusal fire with the wrong diagnosis — or not at all."""
    candidates, mapping, traces = split_result
    decidable = next(c.unit_id for c in candidates
                     if c.observed_label in (0, 1))
    short = {uid: t for uid, t in traces.items() if uid != decidable}
    with pytest.raises(ValueError, match="trace inventory"):
        eligible_units(candidates, mapping, short)


def test_a_trace_inventory_naming_unknown_units_is_refused(split_result):
    candidates, mapping, traces = split_result
    with pytest.raises(ValueError, match="not among the candidates"):
        eligible_units(candidates, mapping, {**traces, "ghost": (1, 2)})
