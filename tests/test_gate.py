"""The Week 4 reliability gate's eligibility, aggregation and evidence binding.

The gate is where an *authorised verdict* is distinguished from a computed
number. Every test here asserts a refusal or an aggregation rule, because the
statistic itself is already tested in `test_trend.py` and is deliberately not
reimplemented here.

D-071 added the part that was missing: a verdict must be bound to the evidence
that produced it. Before it, five lines of invented floats produced a PASS
carrying all eighteen golden `config_id`s with no model ever fitted.
"""

from __future__ import annotations

import json
from dataclasses import replace as dataclass_replace

import pytest

from bu import constants as K
from bu.config import Config, TrainConfig, UnitSpec
from bu.stats.gate import (
    GATE_CONFIG_IDS, GATE_LAYOUTS, GATE_SEEDS, GATE_STAGE, RUNGS, EvidenceCell,
    GateEvidence, GateResult, RungSpec, _gate_from_curves, gate_config_ids,
    gate_units, recompute, reliability_gate,
)
from bu import constants as K  # noqa: F811  (K is used by the helpers above)
from bu.streams import seed_partition

SIZES = K.DATA_SIZES
FALLING = [0.9, 0.7, 0.5, 0.4, 0.3, 0.2]
RISING = [0.2, 0.3, 0.4, 0.5, 0.7, 0.9]
COMMIT = "a" * 40


def curves(values, seeds=GATE_SEEDS, jitter=0.01):
    return {
        seed: {n: v + jitter * i for n, v in zip(SIZES, values)}
        for i, seed in enumerate(seeds)
    }


def all_configurations(values=FALLING, **overrides):
    out = {name: values for name in GATE_LAYOUTS}
    out.update(overrides)
    return out


def cell_fields(layout, seed, n, spec, *, attempt="attempt-001", commit=COMMIT):
    """A well-formed cell's fields, derived from a real Config."""
    unit = UnitSpec(
        causal_attribute=K.GATE_CAUSAL_ATTRIBUTE, layout=layout,
        confound_rate=K.GATE_CONFOUND_RATE, family="estimation",
        n_transitions=n, hidden_size=256,
    )
    config = Config(unit=unit, seed=seed, stage=GATE_STAGE, train=spec.train_config())
    return dict(
        layout=layout, seed=seed, size=n, config=config.to_dict(),
        config_id=config.config_id, run_id=config.run_id, unit_id=config.unit_id,
        stage=GATE_STAGE, partition=seed_partition(seed), granularity=spec.granularity,
        member_count=spec.ensemble_size,
        member_indices=tuple(range(spec.ensemble_size)),
        member_record_digest="a" * 64, run_record_digest="b" * 64,
        evaluation_pool_id=f"{layout}-s{seed:03d}",
        evaluation_pool_digest=f"pool-{layout}-{seed}",
        normalisation={"scale": [1.0, 1.0], "n_reference": 800},
        metric_schema_version=1, row_index=0, row_digest="c" * 64,
        attempt_id=f"w4-gate-r{spec.rung:02d}-{spec.spec_hash}-{attempt}",
        attempt=attempt, commit=commit,
    )


def evidence_with_config(spec=None, **config_kwargs):
    """Evidence whose CONFIG is altered — the source of truth, not a flat claim."""
    spec = spec or RungSpec.for_rung(0)
    cells = []
    for layout in GATE_LAYOUTS:
        for i, seed in enumerate(GATE_SEEDS):
            for n, v in zip(SIZES, FALLING):
                fields = cell_fields(layout, seed, n, spec)
                unit = UnitSpec(
                    causal_attribute=K.GATE_CAUSAL_ATTRIBUTE, layout=layout,
                    confound_rate=K.GATE_CONFOUND_RATE, family="estimation",
                    n_transitions=n, hidden_size=config_kwargs.pop("hidden_size", 256),
                )
                config = Config(
                    unit=unit, seed=seed,
                    stage=config_kwargs.get("stage", GATE_STAGE),
                    train=config_kwargs.get("train", spec.train_config()),
                )
                fields.update(
                    config=config.to_dict(), config_id=config.config_id,
                    run_id=config.run_id, unit_id=config.unit_id,
                    stage=config.stage, disagreement=v + 0.01 * i,
                )
                cells.append(EvidenceCell(**fields))
    return GateEvidence(cells=_with_content_id(cells, spec))


def evidence(
    values_by_layout=None, *, seeds=GATE_SEEDS, spec=None, attempt="attempt-001",
    commit=COMMIT, jitter=0.01, **cell_overrides,
):
    """Well-formed gate evidence, unless a test deliberately breaks one field."""
    if values_by_layout is None:
        values_by_layout = all_configurations()
    spec = spec or RungSpec.for_rung(0)
    cells = []
    for layout, values in values_by_layout.items():
        for i, seed in enumerate(seeds):
            for n, v in zip(SIZES, values):
                known = layout in GATE_LAYOUTS and n in SIZES
                fields = (
                    cell_fields(layout, seed, n, spec, attempt=attempt, commit=commit)
                    if known
                    else dict(
                        cell_fields(GATE_LAYOUTS[0], seed, SIZES[0], spec,
                                    attempt=attempt, commit=commit),
                        layout=layout, size=n,
                    )
                )
                fields["disagreement"] = v + jitter * i
                fields.update(cell_overrides)
                cells.append(EvidenceCell(**fields))
    return GateEvidence(cells=_with_content_id(cells, spec, cell_overrides))


def merge(*evidences, spec=None):
    """Combine cells under ONE attempt identity.

    Tests about the grid want a single attempt whose *shape* is wrong. Merging
    two separately-built evidences would instead trip the one-attempt rule,
    which is a different refusal and would leave the grid rule untested.
    """
    spec = spec or RungSpec.for_rung(0)
    cells = [c for ev in evidences for c in ev.cells]
    return GateEvidence(cells=_with_content_id(cells, spec))


def _with_content_id(cells, spec, overrides=()):
    """Stamp the identity the cells actually imply, unless a test overrode it."""
    if "attempt_id" in (overrides or ()):
        return tuple(cells)
    ident = GateEvidence.content_id(
        [[getattr(c, f) for f in GateEvidence.IDENTITY_DIGESTS] for c in cells],
        rung=spec.rung, spec_hash=spec.spec_hash,
    )
    return tuple(dataclass_replace(c, attempt_id=ident) for c in cells)


# --- the predeclared configurations, frozen before Tuesday ----------------


def test_the_frozen_config_ids_still_describe_the_intended_units():
    """Golden values. If identity canonicalisation moves, this fails loudly.

    The gate's record names exact `config_id`s. Were they regenerated at run
    time, a change to identity fields would silently redirect the gate at
    different units while the record kept claiming the old ones (D-016).
    """
    for layout in GATE_LAYOUTS:
        assert gate_config_ids(layout) == GATE_CONFIG_IDS[layout], (
            f"{layout}: derived config ids no longer match the frozen set. If "
            "this is an intended identity change, it needs a Change Record and "
            "an IDENTITY_VERSION bump, not a test update."
        )


def test_a_configuration_spans_the_six_registered_sizes():
    """A configuration is six units, not one — the curve runs *across* them."""
    for layout in GATE_LAYOUTS:
        units = gate_units(layout)
        assert tuple(u.n_transitions for u in units) == tuple(SIZES)
        assert {u.layout for u in units} == {layout}
        assert {u.causal_attribute for u in units} == {"shape"}
        assert {u.confound_rate for u in units} == {0.0}
        assert len(set(GATE_CONFIG_IDS[layout])) == 6, "config ids must be distinct"


def test_the_three_configurations_vary_only_the_layout():
    """Causal rule and confounding held fixed, so the gate tests the estimator."""
    ids = {layout: set(GATE_CONFIG_IDS[layout]) for layout in GATE_LAYOUTS}
    assert len(set.union(*ids.values())) == 18, "configurations share a unit"
    assert set(GATE_LAYOUTS) == {"uniform", "clustered", "sparse"}


# --- eligibility ----------------------------------------------------------


def test_exactly_three_predeclared_configurations():
    with pytest.raises(ValueError, match="not the registered one|exactly the three"):
        reliability_gate(evidence({"uniform": FALLING}), rung=0)

    extra = all_configurations()
    extra["dense"] = FALLING
    with pytest.raises(ValueError, match="not the registered one|exactly the three"):
        reliability_gate(evidence(extra), rung=0)

    substituted = all_configurations()
    substituted["elsewhere"] = substituted.pop("sparse")
    with pytest.raises(ValueError, match="not the registered one|exactly the three"):
        reliability_gate(evidence(substituted), rung=0)


@pytest.mark.parametrize(
    "seeds, why",
    [
        ((0, 1, 2), "the three-seed pilot is not a gate result"),
        ((0, 1, 2, 3), "four seeds is not five"),
        ((0, 1, 2, 3, 4, 5), "six seeds is not five"),
        ((0, 1, 2, 3, 7), "a substituted seed is not the registered set"),
    ],
)
def test_exactly_five_development_seeds(seeds, why):
    """The pilot's three seeds cannot become a gate verdict by being rerun."""
    ev = merge(
        GateEvidence(tuple(c for c in evidence().cells if c.layout != "clustered")),
        evidence({"clustered": FALLING}, seeds=seeds),
    )
    with pytest.raises(ValueError, match="not the registered one|the gate requires"):
        reliability_gate(ev, rung=0)


def test_the_gate_refuses_confirmatory_seeds():
    """Estimator selection must not consume the verdict's evidence."""
    conf = tuple(K.CONFIRMATORY_SEED_BASE + i for i in range(5))
    ev = merge(
        GateEvidence(tuple(c for c in evidence().cells if c.layout != "uniform")),
        evidence({"uniform": FALLING}, seeds=conf),
    )
    with pytest.raises(
        ValueError, match="not the registered one|development-only|the gate requires"
    ):
        reliability_gate(ev, rung=0)


def test_an_unknown_rung_is_refused():
    with pytest.raises(ValueError, match="rung must be one of"):
        reliability_gate(evidence(), rung=9)


def test_an_incomplete_curve_is_still_refused_downstream():
    """The private helper does not weaken any of `trend_test`'s refusals."""
    bad = {name: curves(FALLING) for name in GATE_LAYOUTS}
    del bad["sparse"][GATE_SEEDS[0]][SIZES[2]]
    with pytest.raises(ValueError, match="missing dataset sizes"):
        _gate_from_curves(bad, spec=RungSpec.for_rung(0), evidence=evidence())


# --- aggregation ----------------------------------------------------------


def test_rung_zero_passes_only_when_all_three_pass():
    result = reliability_gate(evidence(all_configurations(FALLING)), rung=0)
    assert result.passed
    assert len(result.per_configuration) == 3
    assert all(r.passed for r in result.per_configuration.values())
    assert result.estimator == "ensemble"


def test_one_failing_configuration_fails_the_rung():
    """No majority vote. Configuration sensitivity IS a reliability failure."""
    result = reliability_gate(evidence(all_configurations(FALLING, sparse=RISING)), rung=0)

    assert not result.passed
    assert result.per_configuration["uniform"].passed
    assert result.per_configuration["clustered"].passed
    assert not result.per_configuration["sparse"].passed
    assert "1 of 3 configurations failed (sparse)" in result.reason
    assert "no majority vote" in result.reason


def test_every_configuration_result_is_preserved():
    """All three coefficients and intervals are reported, never reduced."""
    row = reliability_gate(evidence(all_configurations(FALLING, sparse=RISING)), rung=0).as_row()

    assert set(row["configurations"]) == set(GATE_LAYOUTS)
    for name in GATE_LAYOUTS:
        entry = row["configurations"][name]
        assert "rho" in entry and "ci_low" in entry and "ci_high" in entry
        assert entry["partition"] == "development"
        assert entry["n_resamples"] == 5 ** 5
    assert row["aggregation"] == "all_configurations_must_pass"


def test_curves_are_never_pooled_across_configurations():
    """Pooling would let a strong layout carry a weak one.

    Constructed so the *pooled* curve would pass while one configuration on its
    own does not — the gate must report the failure, not the average.
    """
    mixed = all_configurations(
        [0.90, 0.70, 0.50, 0.40, 0.30, 0.20], sparse=[0.20, 0.30, 0.40, 0.50, 0.55, 0.60]
    )
    result = reliability_gate(evidence(mixed), rung=0)
    assert not result.passed
    assert not result.per_configuration["sparse"].passed
    # Each configuration's own seeds only: five blocks, not fifteen.
    for r in result.per_configuration.values():
        assert r.seeds == GATE_SEEDS
        assert r.n_resamples == 5 ** 5


# --- the rung on the record ------------------------------------------------


def test_the_rung_and_estimator_travel_with_the_verdict():
    """"Passed at rung 0" and "passed at rung 3" are different claims."""
    for rung in sorted(K.RUNG_SPECS):
        spec = RungSpec.for_rung(rung)
        result = reliability_gate(evidence(all_configurations(FALLING), spec=spec), rung=rung)
        assert result.rung == rung
        assert result.estimator == spec.estimator
        assert result.as_row()["rung"] == rung
        assert result.as_row()["estimator"] == spec.estimator
        assert result.as_row()["rung_spec"] == spec.as_row()


def test_reaching_rung_three_reports_h1_falsified_for_ensembles():
    """P§11.3: a pass at rung 3 or 4 is a secondary path, not a clean pass.

    Rung 3 cannot be *executed* until its parameters are frozen, so the reporting
    property is asserted on a hand-built result. The refusal is asserted
    separately below — these are two different claims and both must hold.
    """
    passing = reliability_gate(evidence(all_configurations(FALLING)), rung=0)
    high = GateResult(
        spec=dataclass_replace(
            RungSpec.for_rung(0), rung=3, estimator="mc_dropout",
            description="hypothetical",
        ),
        passed=True,
        reason=passing.reason,
        per_configuration=passing.per_configuration,
        seeds=passing.seeds,
        config_ids=passing.config_ids,
        evidence=passing.evidence,
    )
    assert "FALSIFIED FOR" in high.summary()
    assert "secondary" in high.summary()
    assert "FALSIFIED FOR" not in passing.summary()


def test_the_record_states_the_partition_and_the_aggregation_rule():
    row = reliability_gate(evidence(all_configurations(FALLING)), rung=0).as_row()
    assert row["partition"] == "development"
    assert row["seeds"] == list(GATE_SEEDS)
    assert row["config_ids"]["uniform"] == list(GATE_CONFIG_IDS["uniform"])


# --- evidence binding (D-071) ---------------------------------------------
#
# Sol, 2026-08-18. Each of these is a route by which a number could have been
# issued the authority of a gate verdict without having earned it.


def test_invented_curves_cannot_become_a_verdict():
    """The regression for the defect itself.

    Before D-071 this exact construction returned PASS carrying all eighteen
    golden `config_id`s, having fitted nothing. It is the whole reason the
    public entry point takes evidence rather than curves.
    """
    invented = {
        layout: {seed: {n: 1.0 / (i + 1) for i, n in enumerate(SIZES)} for seed in GATE_SEEDS}
        for layout in GATE_LAYOUTS
    }
    with pytest.raises(TypeError):
        reliability_gate(invented, rung=0)


def test_evidence_from_a_non_golden_configuration_cannot_receive_golden_ids():
    """A curve of the right shape from the wrong unit is refused, not relabelled.

    The unit is altered in the CONFIG — hidden_size 64 rather than the frozen
    256 — so the identity the gate derives genuinely differs. Altering only the
    flattened `config_id` would be caught one clause earlier, which is a weaker
    test than the one this claims to be.
    """
    with pytest.raises(ValueError, match="frozen identity for"):
        reliability_gate(evidence_with_config(hidden_size=64), rung=0)


def test_a_flattened_field_that_contradicts_the_canonical_config_is_refused():
    """The config is the source of truth; an independent claim cannot override it."""
    ev = evidence(run_id="ea25c6151f4d-exp1-s999")
    with pytest.raises(ValueError, match="contradict its own canonical config"):
        reliability_gate(ev, rung=0)

    ev = evidence(config_id="deadbeefcafe")
    with pytest.raises(ValueError, match="contradict its own canonical config"):
        reliability_gate(ev, rung=0)


def test_a_run_from_another_stage_is_not_gate_evidence():
    with pytest.raises(ValueError, match="stage 'pilot'|not gate evidence"):
        reliability_gate(evidence_with_config(stage="pilot"), rung=0)


@pytest.mark.parametrize(
    "wrong, why",
    [
        (dict(ensemble_size=10), "rung 1's ensemble size presented as rung 0"),
        (dict(bootstrap_ratio=0.5), "rung 2's subbagging presented as rung 0"),
        (dict(lr=0.1), "a different learning rate, outside the rung's two fields"),
        (dict(batch_size=32), "a different batch size"),
        (dict(max_epochs=5), "a truncated epoch budget"),
        (dict(patience=1), "different early-stopping patience"),
    ],
)
def test_incorrect_rung_training_parameters_are_refused(wrong, why):
    """The COMPLETE TrainConfig, not just the two fields the rung varies (D-072).

    Sol: "a run altered through learning rate, batch size, epoch budget or
    patience could pass the present gate." Four of these six cases are exactly
    those, and every one is invisible to every identity in the project.
    """
    train = dataclass_replace(RungSpec.for_rung(0).train_config(), **wrong)
    with pytest.raises(ValueError, match="not rung 0's frozen specification"):
        reliability_gate(evidence_with_config(train=train), rung=0)


def test_a_secondary_bootstrap_granularity_is_refused():
    """`granularity` is not a TrainConfig field, so it needs its own clause."""
    with pytest.raises(ValueError, match="frozen at 'episode'"):
        reliability_gate(evidence(granularity="transition"), rung=0)


def test_the_rung_train_fields_cover_TrainConfig_exhaustively():
    """A field added to TrainConfig without being frozen would go unchecked."""
    import dataclasses
    assert set(K.RUNG_TRAIN_FIELDS) == {
        f.name for f in dataclasses.fields(RungSpec.for_rung(0).train_config())
    }, (
        "TrainConfig has a field the frozen ladder does not pin. Add it to "
        "RUNG_TRAIN_FIELDS and to every entry of RUNG_SPECS, or the gate will "
        "accept a run that differs in it."
    )


def test_the_rungs_are_indistinguishable_by_every_identity():
    """Why the parameter check above is the *only* defence, not a belt-and-braces one.

    `ensemble_size` and `bootstrap_ratio` are deliberately non-identity fields,
    so rung 0, rung 1 and rung 2 runs of the same cell share config_id, run_id
    and fit_id exactly. Verifying identity against the golden list — which is
    what the D-071 finding literally asked for — therefore passes unchanged for
    rung-1 evidence presented as rung 0. If this test ever fails, the rungs have
    become identity-bearing and the gate's provenance story changes.
    """
    unit = gate_units("uniform")[0]
    rung0 = Config(unit=unit, seed=0, stage=GATE_STAGE, train=TrainConfig(ensemble_size=5, bootstrap_ratio=1.0))
    rung2 = Config(unit=unit, seed=0, stage=GATE_STAGE, train=TrainConfig(ensemble_size=10, bootstrap_ratio=0.5))

    assert rung0.config_id == rung2.config_id
    assert rung0.run_id == rung2.run_id
    assert rung0.fit_id == rung2.fit_id
    # ...and yet the run record does carry the distinction, which is what makes
    # the rung verifiable at all.
    assert rung0.to_dict()["train"]["ensemble_size"] == 5
    assert rung2.to_dict()["train"]["bootstrap_ratio"] == 0.5


def test_a_missing_cell_fails_closed():
    ev = GateEvidence(cells=evidence().cells[:-1])
    with pytest.raises(ValueError, match="1 missing"):
        reliability_gate(ev, rung=0)


def test_a_duplicated_cell_fails_closed():
    """Which of two runs the verdict used would otherwise be iteration order."""
    cells = evidence().cells
    ev = GateEvidence(cells=cells + (cells[0],))
    with pytest.raises(ValueError, match="duplicate evidence"):
        reliability_gate(ev, rung=0)


def test_evidence_mixed_across_attempts_fails_closed():
    """A verdict assembled from two runs is not a verdict about either (D-062)."""
    first = evidence().cells
    ev = GateEvidence(
        cells=first[:-1] + (dataclass_replace(first[-1], attempt_id="other-attempt"),)
    )
    with pytest.raises(ValueError, match="spans 2 attempts"):
        reliability_gate(ev, rung=0)


def test_evidence_mixed_across_commits_fails_closed():
    first = evidence().cells
    ev = GateEvidence(cells=first[:-1] + (dataclass_replace(first[-1], commit="b" * 40),))
    with pytest.raises(ValueError, match="spans 2 commits"):
        reliability_gate(ev, rung=0)


# --- rungs whose parameters are not frozen ---------------------------------


@pytest.mark.parametrize("rung", K.RUNG_PARAMETERS_UNFROZEN)
def test_a_rung_without_frozen_parameters_is_refused(rung):
    """Sol: freeze them before executing, not after watching a lower rung fail."""
    with pytest.raises(ValueError, match="deliberately NOT frozen"):
        reliability_gate(evidence(), rung=rung)


def test_the_frozen_rungs_are_cumulative_and_ordered():
    """Each rung changes exactly one parameter from the one below it."""
    zero, one, two = (RungSpec.for_rung(r) for r in (0, 1, 2))
    assert (zero.ensemble_size, zero.bootstrap_ratio) == (5, 1.0)
    assert (one.ensemble_size, one.bootstrap_ratio) == (10, 1.0)
    assert (two.ensemble_size, two.bootstrap_ratio) == (10, 0.5)
    assert zero.granularity == one.granularity == two.granularity == "episode"


def test_rung_two_lowers_the_bootstrap_ratio_because_that_is_what_raises_diversity():
    """The pre-data semantic correction to P§11.3, asserted rather than annotated.

    `bootstrap_ratio` is draws-with-replacement over episode count, so expected
    unique coverage is 1 - e^-ratio: raising it makes members *more* alike. Rung
    2 therefore subbags at 0.5. A future edit that "restores" the plan's literal
    wording by raising the ratio above 1.0 fails here.
    """
    import numpy as np

    assert RungSpec.for_rung(2).bootstrap_ratio < 1.0

    rng = np.random.default_rng(0)
    episodes = 80
    coverage = {}
    for ratio in (0.5, 1.0, 2.0):
        n = max(1, int(round(episodes * ratio)))
        coverage[ratio] = np.mean(
            [len(np.unique(rng.choice(episodes, size=n, replace=True))) / episodes for _ in range(200)]
        )
    assert coverage[0.5] < coverage[1.0] < coverage[2.0]
    assert coverage[0.5] == pytest.approx(1 - np.exp(-0.5), abs=0.02)


# --- the verdict is recomputable from its own record ------------------------


def test_a_serialised_verdict_recomputes_from_its_own_evidence():
    """Sol: recomputable "without consulting informal logs"."""
    original = reliability_gate(evidence(all_configurations(FALLING, sparse=RISING)), rung=0)
    row = json.loads(json.dumps(original.as_row()))

    again = recompute(row)
    assert again.passed == original.passed
    assert again.estimator == original.estimator
    assert again.as_row() == original.as_row()
    for name in GATE_LAYOUTS:
        assert again.per_configuration[name].rho == original.per_configuration[name].rho
        assert again.per_configuration[name].ci_low == original.per_configuration[name].ci_low


def test_the_record_carries_every_raw_cell_not_just_the_mean_curve():
    """The exact paired bootstrap cannot be rebuilt from a mean curve."""
    row = reliability_gate(evidence(), rung=0).as_row()
    cells = row["evidence"]["cells"]
    assert len(cells) == len(GATE_LAYOUTS) * len(GATE_SEEDS) * len(SIZES) == 90
    assert {c["layout"] for c in cells} == set(GATE_LAYOUTS)
    assert {c["seed"] for c in cells} == set(GATE_SEEDS)
    assert {c["size"] for c in cells} == set(SIZES)
    for c in cells:
        assert c["run_id"] and c["config_id"] and c["commit"]


def test_a_tampered_estimator_in_the_record_does_not_survive_recomputation():
    """The estimator is derived from the rung, so a record cannot assert one.

    This is the property behind removing the free-form override: it is not that
    the argument is gone, it is that no serialised claim about the estimator is
    load-bearing anywhere.
    """
    row = json.loads(json.dumps(reliability_gate(evidence(), rung=0).as_row()))
    row["estimator"] = "mc_dropout"
    row["rung_spec"]["estimator"] = "mc_dropout"

    assert recompute(row).estimator == "ensemble"


def test_the_public_gate_cannot_be_handed_an_estimator():
    with pytest.raises(TypeError):
        reliability_gate(evidence(), rung=0, estimator="mc_dropout")
