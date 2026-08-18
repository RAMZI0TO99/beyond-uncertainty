"""The W4 evidence contract: a verdict bound to the artefacts behind it (D-072).

Sol refused to certify the gate twice, each time because the trust boundary had
not reached the execution evidence. First it took bare curves and stamped the
golden identities on them — five lines of invented floats returned PASS. Then it
read a flattened manifest and checked only that the manifest agreed with itself,
so a longer fabrication passed just as cleanly.

Every test here is a route by which a number could still have been issued the
authority of a gate verdict. The fixture writes **real run records** through
`RunLogger` but trains nothing, so the whole 90-cell contract is exercised in
under a second and no compute is spent.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from bu import constants as K
from bu.config import Config, TrainConfig, UnitSpec
from bu.experiments.w4_gate import CellResult, write_manifest, gate_units
from bu.metrics import RunLogger
from bu.runrecord import GitState
from bu.stats.gate import (
    GATE_LAYOUTS, GATE_SEEDS, GATE_STAGE, GateEvidence, RungSpec, reliability_gate,
)

SIZES = K.DATA_SIZES
CLEAN = GitState(commit="a" * 40, dirty=False, branch="main")
# Falls monotonically in N, so a well-formed attempt PASSES and the refusal
# tests are refusing something that would otherwise have been a verdict.
FALLING = {n: 0.9 - 0.1 * i for i, n in enumerate(SIZES)}


def build_attempt(tmp_path, *, spec=None, name="attempt-001", layouts=GATE_LAYOUTS,
                  seeds=GATE_SEEDS, sizes=SIZES, pool_per_size=False,
                  disagreement=None, train=None):
    """A complete, well-formed attempt directory. Trains nothing."""
    spec = spec or RungSpec.for_rung(0)
    attempt = tmp_path / name
    attempt.mkdir(parents=True)
    cells = []
    for layout in layouts:
        for seed in seeds:
            for n in sizes:
                config = Config(
                    unit=gate_units(layout, n), seed=seed, stage=GATE_STAGE,
                    train=train or spec.train_config(),
                )
                extra = {"granularity": spec.granularity, "rung": spec.rung}
                with RunLogger.start(config, root=attempt / "records", extra=extra) as log:
                    for k in range(spec.ensemble_size):
                        log.log(member=k, val_position=0.01 * (k + 1),
                                granularity=spec.granularity)
                value = (disagreement or FALLING)[n]
                record_dir = attempt / "records" / config.run_id
                pool = f"pool-{layout}-{seed}" + (f"-{n}" if pool_per_size else "")
                row = {"layout": layout, "n_transitions": n, "seed": seed,
                       "uncertainty": {"mean_disagreement": value}}
                cells.append(CellResult(row=row, run={
                    "config": config.to_dict(), "run_id": config.run_id,
                    "config_id": config.config_id, "unit_id": config.unit_id,
                    "layout": layout, "n_transitions": n, "seed": seed,
                    "stage": GATE_STAGE, "seed_partition": "development",
                    "granularity": spec.granularity,
                    "member_count": spec.ensemble_size,
                    "member_indices": list(range(spec.ensemble_size)),
                    "member_record_digest": _digest(record_dir / "metrics.jsonl"),
                    "run_record_digest": _digest(record_dir / "run.json"),
                    "evaluation_pool_id": f"{layout}-s{seed:03d}",
                    "evaluation_pool_digest": pool,
                    "normalisation": {"scale": [1.0, 1.0], "n_reference": 800},
                    "metric_schema_version": 1,
                    "mean_disagreement": value,
                    "row_index": -1, "row_digest": "",
                }))
    write_manifest(attempt, spec=spec, cells=cells, git=CLEAN, artifacts=[])
    return attempt


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def _prototype(tmp_path_factory):
    """One well-formed 90-cell attempt, built once.

    `write_run_record` shells out to git per record, so building this ninety
    times over would dominate the suite. Refusal tests copy it and mutate the
    copy, which is also closer to what they are modelling: a real attempt that
    something has since altered.
    """
    return build_attempt(tmp_path_factory.mktemp("prototype"))


@pytest.fixture
def attempt(_prototype, tmp_path):
    import shutil

    target = tmp_path / _prototype.name
    shutil.copytree(_prototype, target)
    return target


def edit_manifest(attempt, fn):
    manifest = json.loads((attempt / "manifest.json").read_text())
    fn(manifest)
    (attempt / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return attempt


# --- the well-formed case, so every refusal below refuses a real verdict -----


def test_a_well_formed_attempt_produces_a_verdict(attempt):
    result = reliability_gate(GateEvidence.from_attempt(attempt), rung=0)
    assert result.passed
    assert result.evidence.attempt_id.startswith("w4-gate-r00-")
    assert len(result.evidence.cells) == 90
    assert result.as_row()["evidence"]["n_cells"] == 90


def test_the_verdict_recomputes_from_its_own_record(attempt):
    original = reliability_gate(GateEvidence.from_attempt(attempt), rung=0)
    from bu.stats.gate import recompute
    again = recompute(json.loads(json.dumps(original.as_row())))
    assert again.as_row() == original.as_row()


# --- Sol's required refusals ------------------------------------------------


def test_a_config_conflicting_with_its_flattened_identity_is_refused(attempt):
    edit_manifest(attempt, lambda m: m["runs"][0].update(config_id="deadbeefcafe"))
    with pytest.raises(ValueError, match="contradict its own canonical config"):
        reliability_gate(GateEvidence.from_attempt(attempt), rung=0)


def test_a_train_config_differing_outside_the_rung_fields_is_refused(tmp_path):
    """Learning rate is in no identity and in none of the three rung fields."""
    attempt = build_attempt(
        tmp_path, train=TrainConfig(**{**RungSpec.for_rung(0).train_config().__dict__, "lr": 0.1})
    )
    with pytest.raises(ValueError, match="not rung 0's frozen specification"):
        reliability_gate(GateEvidence.from_attempt(attempt), rung=0)


def test_two_directories_sharing_the_label_attempt_001_get_different_identities(tmp_path):
    """The bare label is not an identity — two attempts can both be attempt-001.

    Deriving the id from rung, spec hash and directory name produced the SAME id
    for both; that is why it is derived from the run records instead, which
    carry `started_utc`. This test is the reason the derivation changed.
    """
    a = GateEvidence.from_attempt(build_attempt(tmp_path / "a", name="attempt-001"))
    b = GateEvidence.from_attempt(build_attempt(tmp_path / "b", name="attempt-001"))

    assert a.attempt == b.attempt == "attempt-001"
    assert a.attempt_id != b.attempt_id, (
        "two distinct executions share an evidence identity; cells from both "
        "could be merged into one verdict without anything noticing"
    )
    with pytest.raises(ValueError, match="spans 2 attempts"):
        reliability_gate(GateEvidence(cells=a.cells[:-1] + b.cells[-1:]), rung=0)


def test_an_attempt_id_not_naming_its_rung_and_spec_hash_is_refused(attempt):
    edit_manifest(attempt, lambda m: m.update(attempt_id="attempt-001"))
    with pytest.raises(ValueError, match="disagrees with"):
        GateEvidence.from_attempt(attempt)


@pytest.mark.parametrize("bad", ["deadbeef0000", None])
def test_an_incorrect_or_missing_rung_spec_hash_is_refused(attempt, bad):
    def edit(m):
        if bad is None:
            del m["rung_spec_hash"]
        else:
            m["rung_spec_hash"] = bad

    edit_manifest(attempt, edit)
    with pytest.raises(ValueError, match="missing|hashes to"):
        GateEvidence.from_attempt(attempt)


def test_a_modified_member_record_fails_its_digest(attempt):
    path = next((attempt / "records").glob("*/metrics.jsonl"))
    path.write_text(path.read_text().replace('"val_position": 0.01', '"val_position": 0.99'))
    with pytest.raises(ValueError, match="member records hash to"):
        GateEvidence.from_attempt(attempt)


def test_a_modified_run_record_fails_its_digest(attempt):
    path = next((attempt / "records").glob("*/run.json"))
    record = json.loads(path.read_text())
    record["seed"] = 99
    path.write_text(json.dumps(record, indent=2, sort_keys=True))
    with pytest.raises(ValueError, match="record hashes to"):
        GateEvidence.from_attempt(attempt)


def test_a_modified_source_row_fails_its_digest(attempt):
    rows = json.loads((attempt / "rows.json").read_text())
    rows[0]["uncertainty"]["mean_disagreement"] = 0.123
    (attempt / "rows.json").write_text(json.dumps(rows, indent=2))
    with pytest.raises(ValueError, match="digest|hash"):
        GateEvidence.from_attempt(attempt)


def test_a_claimed_disagreement_that_does_not_reproduce_is_refused(attempt):
    """The number in the manifest must be the number that was measured."""
    edit_manifest(attempt, lambda m: m["runs"][0].update(mean_disagreement=0.0001))
    with pytest.raises(ValueError, match="not the one that was measured"):
        GateEvidence.from_attempt(attempt)


def test_different_evaluation_pools_across_the_six_sizes_are_refused(tmp_path):
    """A curve measured on six different pools is not a trend in dataset size."""
    attempt = build_attempt(tmp_path, pool_per_size=True)
    with pytest.raises(ValueError, match="different evaluation pools"):
        reliability_gate(GateEvidence.from_attempt(attempt), rung=0)


def test_a_run_that_left_no_record_is_refused(attempt):
    import shutil
    shutil.rmtree(next((attempt / "records").glob("*/")).parent)
    with pytest.raises(ValueError, match="no run record"):
        GateEvidence.from_attempt(attempt)


def test_a_claimed_member_never_fitted_is_refused(attempt):
    """Members are counted from the metric stream, not from the manifest."""
    manifest = json.loads((attempt / "manifest.json").read_text())
    path = attempt / "records" / manifest["runs"][0]["run_id"] / "metrics.jsonl"
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    path.write_text("\n".join(lines[:-1]) + "\n")
    # Digest updated to the truncated file, so this is not caught as tampering:
    # the claim is refused because the members were never fitted.
    edit_manifest(attempt, lambda m: m["runs"][0].update(member_record_digest=_digest(path)))
    with pytest.raises(ValueError, match="metric stream holds"):
        GateEvidence.from_attempt(attempt)


def test_a_granularity_contradicting_the_run_record_is_refused(attempt):
    """`granularity` is outside Config, so the run record is its only attestation."""
    edit_manifest(attempt, lambda m: m["runs"][0].update(granularity="transition"))
    with pytest.raises(ValueError, match="run record says"):
        GateEvidence.from_attempt(attempt)


def test_an_unrecognised_contract_version_is_refused(attempt):
    edit_manifest(attempt, lambda m: m.update(evidence_contract_version=99))
    with pytest.raises(ValueError, match="contract version 99"):
        GateEvidence.from_attempt(attempt)


def test_a_dirty_tree_cannot_produce_a_verdict(attempt):
    edit_manifest(attempt, lambda m: m.update(dirty=True))
    with pytest.raises(ValueError, match="dirty tree"):
        GateEvidence.from_attempt(attempt)


def test_a_missing_rows_file_is_a_refusal_not_a_crash(attempt):
    """An incidental FileNotFoundError is an accident; this must be a refusal."""
    (attempt / "rows.json").unlink()
    edit_manifest(attempt, lambda m: m.update(artifacts=[]))
    with pytest.raises(ValueError, match="no rows.json"):
        GateEvidence.from_attempt(attempt)


def test_a_missing_artefact_is_refused(attempt):
    (attempt / "rows.json").write_text("[]")
    with pytest.raises(ValueError, match="digest|hash"):
        GateEvidence.from_attempt(attempt)


def test_the_w3_pilot_manifest_is_refused_as_gate_evidence():
    """Real evidence, on the uniform gate configuration — and still not a verdict."""
    from pathlib import Path

    attempt = Path("runs/w3_pilot/attempt-001")
    if not attempt.exists():
        pytest.skip("pilot attempt not present in this checkout")
    with pytest.raises(ValueError, match="missing"):
        GateEvidence.from_attempt(attempt)


# --- the runner itself, exercised for real ---------------------------------


def test_the_runner_reuses_one_scale_and_one_pool_across_dataset_sizes(tmp_path):
    """C-010's invariant, on the real path rather than a fixture.

    Every other test in this module builds evidence without training, which is
    what keeps them fast — but it also means none of them would notice if the
    runner built a fresh `NormalisationScale` per dataset size. D-061 registers
    ONE scale, measured on the full movement evaluation pool before any mask and
    reused for every size sharing that pool; W4 Friday's masked statistics must
    reuse that same object. So this one runs the machinery: two sizes, one seed,
    ten fits, a few seconds on CPU.
    """
    from bu.experiments.w4_gate import run

    attempt = run(
        rung=0, layouts=("uniform",), seeds=(0,), sizes=(100, 250),
        out_dir=tmp_path / "gate", verbose=False,
    )
    manifest = json.loads((attempt / "manifest.json").read_text())
    assert len(manifest["runs"]) == 2

    scales = {json.dumps(r["normalisation"], sort_keys=True) for r in manifest["runs"]}
    assert len(scales) == 1, (
        "the two dataset sizes carry different normalising scales; D-061 requires "
        "one scale per evaluation pool, reused across sizes"
    )
    pools = {r["evaluation_pool_digest"] for r in manifest["runs"]}
    assert len(pools) == 1, (
        "the evaluation pool differs between dataset sizes, so the trend would "
        "compare disagreement measured on different data (D-052)"
    )
    # And the artefacts it wrote are internally consistent: dirty flag aside,
    # this is exactly what the gate will read on Tuesday.
    edit_manifest(attempt, lambda m: m.update(dirty=False))
    evidence = GateEvidence.from_attempt(attempt)
    assert len(evidence.cells) == 2
    assert evidence.cells[0].member_indices == (0, 1, 2, 3, 4)


def test_the_runner_refuses_confirmatory_seeds(tmp_path):
    """Estimator selection must never consume the W10 verdict's evidence."""
    from bu.experiments.w4_gate import run

    with pytest.raises(ValueError, match="confirmatory"):
        run(rung=0, layouts=("uniform",), seeds=(K.CONFIRMATORY_SEED_BASE,),
            sizes=(100,), out_dir=tmp_path / "gate", verbose=False)


def test_the_runner_refuses_a_rung_whose_parameters_are_unfrozen(tmp_path):
    from bu.experiments.w4_gate import run

    with pytest.raises(ValueError, match="deliberately NOT frozen"):
        run(rung=3, layouts=("uniform",), seeds=(0,), sizes=(100,),
            out_dir=tmp_path / "gate", verbose=False)
