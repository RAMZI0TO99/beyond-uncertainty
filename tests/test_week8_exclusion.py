"""Synthetic tests for the source-bound Week-8 first-sweep report.

No production evidence directory is opened.  The certified ordinary-sweep
loader is replaced with a strict synthetic double so these tests exercise the
new consumer boundary, arithmetic, source binding and immutable report I/O.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.config import Config
from bu.experiments import label_evidence as L
from bu.experiments import ordinary_sweep_label_evidence as O
from bu.experiments import week8_exclusion as W
from bu.experiments import week7_launch_plan as W7
from bu.streams import group_of


def _sha1(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(value) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@pytest.fixture(scope="module")
def batch_unit():
    matches = [
        unit
        for unit in O.sweep_ordinary_units()
        if Config(unit=unit).unit_id == W.FIRST_SWEEP_BATCH_1_UNIT_ID
    ]
    assert len(matches) == 1
    return matches[0]


def test_frozen_week7_partition_derives_exact_first_sweep_singleton():
    first = W7.sweep_baseline_batches()[0]
    assert len(first) == 3
    assert {Config(unit=job.unit).unit_id for job in first} == {
        W.FIRST_SWEEP_BATCH_1_UNIT_ID
    }
    assert tuple(job.seed for job in first) == (1000, 1001, 1002)


def _outcomes(label):
    return {
        0: (True, False),
        1: (False, True),
        "ambiguous": (True, True),
        "undiagnosed": (False, False),
    }[label]


def _make_case(tmp_path, monkeypatch, batch_unit, *, observed="undiagnosed"):
    workspace = tmp_path / "workspace"
    source_root = workspace / "source-bundle"
    report_root = workspace / "report-bundle"
    source_root.mkdir(parents=True)
    report_root.mkdir()
    monkeypatch.setattr(W, "WORKSPACE_ROOT", workspace)
    label_path = source_root / "ordinary_sweep_label_evidence.json"
    label_path.write_text('{"synthetic_source":true}\n', encoding="utf-8")
    conditions = []
    runs = []
    for offset, seed in enumerate((1000, 1001, 1002)):
        sources = []
        identities = {}
        for arm in ("baseline", "data_repair", "model_repair"):
            commit = _sha1(f"commit:{seed}:{arm}")
            execution = _sha256(f"execution:{seed}:{arm}")
            path = source_root / f"source-{seed}-{arm}"
            if arm == "baseline":
                source = O.SweepBaselineSource(path, commit, execution)
            else:
                source = O.PairedRepairSource(path, commit, execution)
            sources.append(source)
            identities[arm] = {
                "expected_git_commit": commit,
                "execution_digest": execution,
            }
        conditions.append(O.SweepRepairCondition(*sources))
        runs.append({"seed": seed, **identities})

    data_works, model_works = _outcomes(observed)
    unit_id = Config(unit=batch_unit).unit_id
    comparison_group_id = group_of(batch_unit, "config_sweep")
    label = {
        "unit_id": unit_id,
        "comparison_group_id": comparison_group_id,
        "intended_class": "hypothesis_class",
        "data_repair_works": data_works,
        "model_repair_works": model_works,
        "observed_label": observed,
    }
    payload = {
        "ordinary_sweep_label_evidence_schema_version": 1,
        "unit_id": unit_id,
        "unit": L._unit_row(batch_unit),
        "family": batch_unit.family,
        "comparison_group_id": comparison_group_id,
        "intended_class": "hypothesis_class",
        "stage": "exp3_repairs",
        "baseline_stage": "config_sweep",
        "seeds": [1000, 1001, 1002],
        "runs": runs,
        "label": label,
    }
    record = {**payload, "record_digest": L._digest(payload)}
    calls = []

    def loader(path, *, unit, conditions):
        calls.append((Path(path), unit, conditions))
        return copy.deepcopy(record)

    monkeypatch.setattr(W, "load_ordinary_sweep_label_evidence", loader)
    source = W.SourceBoundSweepLabel(label_path, batch_unit, tuple(conditions))
    return SimpleNamespace(
        path=label_path,
        conditions=tuple(conditions),
        source=source,
        record=record,
        calls=calls,
        output=report_root / W.WEEK8_SWEEP_EXCLUSION_FILE,
        workspace=workspace,
    )


def _summary(case):
    return W.summarize_sweep_exclusion(
        [case.source], expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS
    )


def _write(case, path):
    return W.write_sweep_exclusion_report(
        [case.source],
        expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
        path=path,
    )


def _refresh_record_digest(record):
    payload = {key: value for key, value in record.items() if key != "record_digest"}
    record["record_digest"] = L._digest(payload)


def test_exact_undiagnosed_arithmetic_and_all_source_hashes(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    report = _summary(case)
    pooled = report["counts"]["pooled"]
    assert pooled == {
        "attempted": 1,
        "observed_0": 0,
        "observed_1": 0,
        "ambiguous": 0,
        "undiagnosed": 1,
        "excluded": 1,
        "exclusion_rate": 1.0,
    }
    per_class = report["counts"]["per_intended_class"]
    assert per_class["hypothesis_class"] == pooled
    assert per_class["estimation"] == {
        "attempted": 0,
        "observed_0": 0,
        "observed_1": 0,
        "ambiguous": 0,
        "undiagnosed": 0,
        "excluded": 0,
        "exclusion_rate": None,
    }
    assert report["registered_planning_exclusion_rate"] == 0.0
    assert report["planning_assumption_missed"] is True
    assert report["shortfall_before_reserve_count"] == 1
    assert report["shortfall_before_reserve_by_intended_class"] == {
        "estimation": 0,
        "hypothesis_class": 1,
    }
    assert report["surviving_min_n0_n1"] == 0
    assert report["reserve_status"] == "not_authorized_not_drawn"
    source = report["sources"][0]
    assert source["unit_id"] == W.FIRST_SWEEP_BATCH_1_UNIT_ID
    assert source["label_file_sha256"] == hashlib.sha256(case.path.read_bytes()).hexdigest()
    assert source["label_record_sha256"] == case.record["record_digest"]
    assert [row["seed"] for row in source["runs"]] == [1000, 1001, 1002]
    assert source["verified_label_runs"] == case.record["runs"]
    for row, condition in zip(source["runs"], case.conditions, strict=True):
        for arm, supplied in (
            ("baseline", condition.baseline),
            ("data_repair", condition.data_repair),
            ("model_repair", condition.model_repair),
        ):
            assert row[arm] == {
                "expected_git_commit": supplied.expected_git_commit,
                "execution_sha256": supplied.expected_execution_digest,
            }
    assert report["source_inventory_sha256"] == _digest(report["sources"])
    payload = {key: value for key, value in report.items() if key != "report_digest"}
    assert report["report_digest"] == _digest(payload)


def test_certified_loader_is_called_with_exact_external_contract(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    _summary(case)
    assert case.calls == [(case.path.resolve(), batch_unit, case.conditions)]


@pytest.mark.parametrize(
    "observed,key,missed",
    [
        (0, "observed_0", False),
        (1, "observed_1", False),
        ("ambiguous", "ambiguous", True),
        ("undiagnosed", "undiagnosed", True),
    ],
)
def test_all_observed_labels_are_counted_without_changing_intended_class(
    tmp_path, monkeypatch, batch_unit, observed, key, missed
):
    case = _make_case(tmp_path, monkeypatch, batch_unit, observed=observed)
    report = _summary(case)
    pooled = report["counts"]["pooled"]
    assert pooled[key] == 1
    assert report["counts"]["per_intended_class"]["hypothesis_class"] == pooled
    assert report["counts"]["per_intended_class"]["estimation"]["attempted"] == 0
    assert report["planning_assumption_missed"] is missed


@pytest.mark.parametrize("bad", [{}, "label.json", Path("label.json"), b"label"])
def test_raw_records_and_bare_paths_are_refused(
    tmp_path, monkeypatch, batch_unit, bad
):
    _make_case(tmp_path, monkeypatch, batch_unit)
    with pytest.raises(ValueError, match="SourceBoundSweepLabel|sequence"):
        W.summarize_sweep_exclusion(
            bad if isinstance(bad, (str, bytes, Path)) else [bad],
            expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
        )


@pytest.mark.parametrize("shape", ["empty", "extra", "duplicate"])
def test_missing_extra_and_duplicate_batch_inputs_are_refused(
    tmp_path, monkeypatch, batch_unit, shape
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    labels = [] if shape == "empty" else [case.source, case.source]
    with pytest.raises(ValueError, match="exactly one"):
        W.summarize_sweep_exclusion(
            labels, expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS
        )


@pytest.mark.parametrize(
    "bad",
    [(), [W.FIRST_SWEEP_BATCH_1_UNIT_ID], ("ffffffffffff",),
     (W.FIRST_SWEEP_BATCH_1_UNIT_ID, W.FIRST_SWEEP_BATCH_1_UNIT_ID)],
)
def test_expected_inventory_cannot_be_caller_redefined(
    tmp_path, monkeypatch, batch_unit, bad
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    with pytest.raises(ValueError, match="exact frozen first-batch tuple"):
        W.summarize_sweep_exclusion([case.source], expected_unit_ids=bad)


def test_wrong_unit_is_refused_before_loader_access(tmp_path, monkeypatch, batch_unit):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    wrong = replace(batch_unit, hidden_size=batch_unit.hidden_size + 1)
    source = W.SourceBoundSweepLabel(case.path, wrong, case.conditions)
    with pytest.raises(ValueError, match="not exact first-sweep"):
        W.summarize_sweep_exclusion(
            [source], expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS
        )
    assert case.calls == []


@pytest.mark.parametrize("bad", [(), (object(),), [object(), object(), object()]])
def test_conditions_must_be_exact_three_item_tuple(
    tmp_path, monkeypatch, batch_unit, bad
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    source = W.SourceBoundSweepLabel(case.path, batch_unit, bad)
    with pytest.raises(ValueError, match="conditions|condition"):
        W.summarize_sweep_exclusion(
            [source], expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS
        )
    assert case.calls == []


@pytest.mark.parametrize("field", ["baseline", "data_repair", "model_repair"])
def test_nested_source_kinds_are_not_interchangeable(
    tmp_path, monkeypatch, batch_unit, field
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    first = case.conditions[0]
    changed = replace(first, **{field: object()})
    source = replace(case.source, conditions=(changed, *case.conditions[1:]))
    with pytest.raises(ValueError, match="must be exact"):
        W.summarize_sweep_exclusion(
            [source], expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS
        )


@pytest.mark.parametrize("field,bad", [("expected_git_commit", "A" * 40),
                                        ("expected_execution_digest", "a" * 63),
                                        ("path", b"not-a-path")])
def test_independent_source_pins_are_strict(
    tmp_path, monkeypatch, batch_unit, field, bad
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    first = case.conditions[0]
    baseline = replace(first.baseline, **{field: bad})
    source = replace(
        case.source,
        conditions=(replace(first, baseline=baseline), *case.conditions[1:]),
    )
    with pytest.raises(ValueError, match="lowercase|filesystem path"):
        W.summarize_sweep_exclusion(
            [source], expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS
        )


def test_opposite_label_schema_is_refused(tmp_path, monkeypatch, batch_unit):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    case.record.clear()
    case.record.update({"label_evidence_schema_version": 3})
    with pytest.raises(ValueError, match="ordinary-sweep label schema"):
        _summary(case)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda r: r.update(unit_id="ffffffffffff"), "unit_id"),
        (lambda r: r.update(stage="repair_validation"), "label stage"),
        (lambda r: r.update(baseline_stage="exp1"), "baseline stage"),
        (lambda r: r.update(seeds=[1000, 1001, 1003]), "label seeds"),
        (lambda r: r.update(intended_class="estimation"), "intended class"),
    ],
)
def test_wrong_unit_stage_seed_or_intended_class_is_refused(
    tmp_path, monkeypatch, batch_unit, mutation, match
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    mutation(case.record)
    _refresh_record_digest(case.record)
    with pytest.raises(ValueError, match=match):
        _summary(case)


@pytest.mark.parametrize("bad", [False, "0", 2, None])
def test_invalid_or_boolean_observed_label_is_refused(
    tmp_path, monkeypatch, batch_unit, bad
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    case.record["label"]["observed_label"] = bad
    _refresh_record_digest(case.record)
    with pytest.raises(ValueError, match="observed_label|observed label"):
        _summary(case)


def test_observed_label_must_match_both_repair_verdicts(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    case.record["label"]["observed_label"] = 0
    _refresh_record_digest(case.record)
    with pytest.raises(ValueError, match="repair verdicts"):
        _summary(case)


def test_source_execution_hash_must_match_independent_conditions(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    case.record["runs"][0]["baseline"]["execution_digest"] = "f" * 64
    _refresh_record_digest(case.record)
    with pytest.raises(ValueError, match="source hashes"):
        _summary(case)


def test_record_digest_tampering_is_refused(tmp_path, monkeypatch, batch_unit):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    case.record["record_digest"] = "f" * 64
    with pytest.raises(ValueError, match="record_digest"):
        _summary(case)


def test_label_file_change_during_verification_is_refused(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)

    def changing_loader(path, *, unit, conditions):
        Path(path).write_text('{"changed":true}\n', encoding="utf-8")
        return copy.deepcopy(case.record)

    monkeypatch.setattr(W, "load_ordinary_sweep_label_evidence", changing_loader)
    with pytest.raises(ValueError, match="changed while"):
        _summary(case)


def test_report_and_digest_are_deterministic(tmp_path, monkeypatch, batch_unit):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    first = _summary(case)
    second = _summary(case)
    assert first == second
    assert first["report_digest"] == second["report_digest"]


def test_immutable_write_and_source_reverified_load_round_trip(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    output = case.output
    written = _write(case, output)
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == written
    loaded = W.load_sweep_exclusion_report(
        output,
        labels=[case.source],
        expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
    )
    assert loaded == written
    loaded["reserve_status"] = "mutated-copy"
    assert json.loads(output.read_text(encoding="utf-8"))["reserve_status"] == W.RESERVE_STATUS


def test_idempotent_write_succeeds_but_divergent_write_never_overwrites(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    output = case.output
    first = _write(case, output)
    assert _write(case, output) == first
    original = output.read_bytes()
    case.path.write_text('{"different_source_bytes":true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="overwrite immutable"):
        _write(case, output)
    assert output.read_bytes() == original


def test_load_refuses_tampered_report_even_with_recomputed_internal_digest(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    output = case.output
    _write(case, output)
    document = json.loads(output.read_text(encoding="utf-8"))
    document["reserve_status"] = "drawn"
    payload = {key: value for key, value in document.items() if key != "report_digest"}
    document["report_digest"] = _digest(payload)
    output.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="stored Week-8 exclusion report"):
        W.load_sweep_exclusion_report(
            output,
            labels=[case.source],
            expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
        )


def test_load_refuses_changed_source_even_when_label_loader_returns_same_record(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    output = case.output
    _write(case, output)
    case.path.write_text('{"changed_after_report":true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="stored Week-8 exclusion report"):
        W.load_sweep_exclusion_report(
            output,
            labels=[case.source],
            expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
        )


def test_report_output_cannot_replace_source_label(tmp_path, monkeypatch, batch_unit):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    original = case.path.read_bytes()
    with pytest.raises(ValueError, match="must not replace"):
        _write(case, case.path)
    assert case.path.read_bytes() == original


def test_malformed_report_file_is_refused(tmp_path, monkeypatch, batch_unit):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    output = case.output
    output.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exact JSON object"):
        W.load_sweep_exclusion_report(
            output,
            labels=[case.source],
            expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
        )


def test_report_path_must_be_a_path(tmp_path, monkeypatch, batch_unit):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    with pytest.raises(ValueError, match="filesystem path"):
        W.write_sweep_exclusion_report(
            [case.source],
            expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
            path={"not": "a path"},
        )


def test_report_path_outside_project_workspace_is_refused(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    outside = tmp_path / "outside" / W.WEEK8_SWEEP_EXCLUSION_FILE
    outside.parent.mkdir()
    with pytest.raises(ValueError, match="inside the project workspace"):
        _write(case, outside)


def test_report_output_root_cannot_overlap_label_or_fit_sources(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    inside_sources = case.path.parent / "reports" / W.WEEK8_SWEEP_EXCLUSION_FILE
    inside_sources.parent.mkdir()
    with pytest.raises(ValueError, match="disjoint"):
        _write(case, inside_sources)


def test_report_path_symlink_is_refused_before_resolution(
    tmp_path, monkeypatch, batch_unit
):
    case = _make_case(tmp_path, monkeypatch, batch_unit)
    target = case.output
    target.write_text("{}\n", encoding="utf-8")
    link = target.with_name("linked-report.json")
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("this Windows account cannot create test symlinks")
    with pytest.raises(ValueError, match="link/reparse"):
        W.load_sweep_exclusion_report(
            link,
            labels=[case.source],
            expected_unit_ids=W.FIRST_SWEEP_BATCH_1_UNIT_IDS,
        )


def test_module_has_no_reserve_import_or_call_and_runtime_never_invokes_it(
    tmp_path, monkeypatch, batch_unit
):
    import bu.experiments.reserve as reserve

    case = _make_case(tmp_path, monkeypatch, batch_unit)

    def forbidden(*args, **kwargs):
        raise AssertionError("reserve API must never be invoked")

    monkeypatch.setattr(reserve, "next_reserve_units", forbidden)
    report = _summary(case)
    assert report["reserve_status"] == W.RESERVE_STATUS

    tree = ast.parse(Path(W.__file__).read_text(encoding="utf-8"))
    imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    ]
    assert all("reserve" not in name for name in imports)
