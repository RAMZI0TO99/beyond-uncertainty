"""D-154 report tests: fabricated sources only, CPU, no experimental results.

Set TMP/TEMP/MPLCONFIGDIR and pytest --basetemp beneath the project. The final
composition fixture reuses the existing fabricated physical-sidecar builder;
neither it nor the report writer is permitted to train anything.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import replace
from itertools import product
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import numpy as np
import pytest

import test_experiment_1_evidence as fixtures
from bu import durable as D
from bu.experiments import experiment_1_evidence as E
from bu.experiments import experiment_1_report as R
from bu.experiments import fit_evidence as F
from bu.runrecord import GitState
from bu.stats import trend as T
from bu.streams import comparison_group_id


FIT_COMMIT = fixtures.COMMIT
ANALYSIS_COMMIT = "a" * 40


def _forbidden(*args, **kwargs):
    raise AssertionError("source/analysis/training access is forbidden on this path")


@pytest.fixture(scope="module")
def analyzed(tmp_path_factory):
    root = tmp_path_factory.mktemp("fabricated-h1-report")
    jobs = fixtures.experiment_1_jobs()
    store = fixtures._StubStore(root / "sources", jobs)
    groups = sorted({comparison_group_id(job.unit, "exp1") for job in jobs})
    # Different levels/seed shapes, with a small-end peak retained. Error rises
    # while disagreement falls: error cannot become an extra veto.
    for path, fit in list(store.entries.items()):
        group = comparison_group_id(fit.unit, "exp1")
        i = R._SIZES.index(fit.unit.n_transitions)
        seed = fit.seed - 1000
        disagreement = [0.60, 0.82, 0.55, 0.42, 0.27, 0.21][i] * (1 + groups.index(group))
        disagreement += seed * 0.001 * (i % 2)
        error = 0.1 + i * 0.2 + seed * 0.001
        diagnostics = dict(fit.diagnostics)
        diagnostics["disagreement"] = np.full(fit.error.shape, disagreement)
        store.entries[path] = replace(fit, error=np.full(fit.error.shape, error),
                                      diagnostics=MappingProxyType(diagnostics))
    calls = []
    original = T.trend_test

    def traced(curves, *, partition):
        result = original(curves, partition=partition)
        calls.append((copy.deepcopy(curves), partition, result))
        return result

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(E, "load_fit_evidence", store.load)
        patch.setattr(R, "git_state", lambda: GitState(ANALYSIS_COMMIT, False, "main"))
        patch.setattr(R, "trend_test", traced)
        patch.setattr(F, "run_confirmatory", _forbidden)
        report = R.write_experiment_1_report(store.paths[::-1], expected_fit_commit=FIT_COMMIT,
                                           analysis_commit=ANALYSIS_COMMIT, report_path=root / "report.json")
    return SimpleNamespace(report=report, document=json.loads(report.read_bytes()), store=store,
                           calls=calls, sha256=D.sha256_file(report))


def _signed(document, path):
    """Re-sign fabricated artifacts so tests exercise more than hash mismatch."""
    doc = copy.deepcopy(document)
    doc["provenance"]["source_inventory_sha256"] = R._hash(doc["rows"])
    doc["payload_sha256"] = R._hash({k: v for k, v in doc.items() if k != "payload_sha256"})
    path.write_bytes((json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    return D.sha256_file(path)


def test_writer_binds_150_sources_and_calls_one_core_per_configuration_metric(analyzed):
    doc = analyzed.document
    assert len(analyzed.store.calls) == 150
    assert set(analyzed.store.calls) == {(p, FIT_COMMIT) for p in analyzed.store.paths}
    assert len(analyzed.calls) == 10
    assert len(doc["rows"]) == len({r["fit_id"] for r in doc["rows"]}) == 150
    assert sum(len(r["roles"]) == 2 for r in doc["rows"]) == 30
    assert doc["provenance"]["expected_fit_commit"] == FIT_COMMIT
    assert doc["provenance"]["analysis_commit"] == ANALYSIS_COMMIT
    assert doc["provenance"]["amendment_document_sha256"] == D.sha256_file(R._AMENDMENT_PATH)
    assert doc["overall"]["all_five_meet_disagreement_criterion"] is True
    for config_index, config in enumerate(doc["configurations"]):
        for metric_index, metric in enumerate(R._METRICS):
            record = config["results"][metric]
            curves, partition, original = analyzed.calls[config_index * 2 + metric_index]
            assert partition == "confirmatory"
            assert tuple(curves) == R._SEEDS
            assert all(tuple(curve) == R._SIZES for curve in curves.values())
            assert record["rho"] == original.rho
            assert [record["ci_low"], record["ci_high"]] == [original.ci_low, original.ci_high]
            assert record["mean_curve"] == list(original.mean_curve)
            assert record["per_seed_rho"] == list(original.per_seed_rho)
            assert record["support"] == R._support(original)
            if metric == "error":
                assert record["status"] == "reversed"
                assert record["role"] == "diagnostic_only"
                assert "criterion_met" not in record
                assert "H1" not in json.dumps(record)
    assert doc["amendment"]["registration_status"] == "post-collection, partially exposed amendment"
    assert doc["amendment"]["fully_blinded_pre_data_registration"] is False
    assert doc["amendment"]["external_sol_certification"] == "pending"
    assert len(doc["amendment"]["known_exposed_fit_ids"]) == 2
    assert "not zero sampling uncertainty" in doc["amendment"]["discreteness"]


@pytest.mark.parametrize("flags", list(product((False, True), repeat=5)))
def test_all_32_pass_patterns_use_only_disagreement(analyzed, flags):
    configurations = copy.deepcopy(analyzed.document["configurations"])
    for c, flag in zip(configurations, flags, strict=True):
        c["results"]["disagreement"]["criterion_met"] = flag
        c["results"]["error"]["status"] = "reversed" if flag else "negative"
    result = R._overall(configurations)
    assert result["all_five_meet_disagreement_criterion"] is all(flags)
    assert result["n_meeting_criterion"] == sum(flags)
    assert result["not_meeting_criterion"] == [c["comparison_group_id"] for c, f in zip(configurations, flags) if not f]
    assert result["amendment_id"] == "D-154"
    assert "not a pristine preregistered global test" in result["limitation"]


def test_replay_reads_only_report_never_sources_git_or_analysis(analyzed, monkeypatch):
    for module, name in ((R, "load_experiment_1_evidence"), (E, "load_fit_evidence"),
                         (R, "trend_test"), (T, "trend_test"), (T, "spearman"),
                         (R, "git_state"), (R, "_metric_record"), (R, "_build")):
        monkeypatch.setattr(module, name, _forbidden)
    read = Path.read_bytes
    reads = []

    def only_report(path):
        assert path == analyzed.report
        reads.append(path)
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", only_report)
    monkeypatch.setattr(Path, "resolve", _forbidden)
    assert R.replay_experiment_1_report(analyzed.report, expected_sha256=analyzed.sha256) == analyzed.document
    assert reads == [analyzed.report]


@pytest.mark.parametrize("bad", [None, "", "A" * 64, "a" * 63, 1, True])
def test_external_digest_is_required_and_strict(analyzed, bad):
    with pytest.raises(ValueError, match="expected_sha256"):
        R.replay_experiment_1_report(analyzed.report, expected_sha256=bad)


def test_exact_byte_tamper_and_missing_external_digest_refused(analyzed, tmp_path):
    target = tmp_path / "tampered.json"
    target.write_bytes(analyzed.report.read_bytes() + b" ")
    with pytest.raises(ValueError, match="externally supplied"):
        R.replay_experiment_1_report(target, expected_sha256=analyzed.sha256)
    with pytest.raises(TypeError):
        R.replay_experiment_1_report(analyzed.report)
    with pytest.raises(ValueError, match="handcrafted"):
        R.replay_experiment_1_report(analyzed.document, expected_sha256=analyzed.sha256)


def _mutate(doc, kind):
    config = doc["configurations"][0]
    record = config["results"]["disagreement"]
    if kind == "version": doc["schema_version"] = 99
    elif kind == "bool_version": doc["schema_version"] = True
    elif kind == "extra": doc["global_p_value"] = 0.01
    elif kind == "disclosure": doc["amendment"]["fully_blinded_pre_data_registration"] = True
    elif kind == "timing": doc["timing"]["week10"] = "new analysis"
    elif kind == "rule": doc["rule"]["strict_upper_bound_below"] = 0.1
    elif kind == "fit_commit": doc["provenance"]["expected_fit_commit"] = "unknown"
    elif kind == "analysis_dirty": doc["provenance"]["analysis_git_clean"] = False
    elif kind == "missing_row": doc["rows"].pop()
    elif kind == "duplicate": doc["rows"][1] = copy.deepcopy(doc["rows"][0])
    elif kind == "seed": doc["rows"][0]["seed"] = 1005
    elif kind == "bool_seed": doc["rows"][0]["seed"] = True
    elif kind == "roles": doc["rows"][0]["roles"] = ["pilot"]
    elif kind == "pairing": doc["rows"][0]["scale"]["vector"][0] += 1e-10
    elif kind == "source_id": doc["rows"][0]["fit_id"] = "invented"
    elif kind == "source_config": doc["rows"][0]["config"]["seed"] = 1005
    elif kind == "source_mean": doc["rows"][0]["mean_disagreement"] += 0.1
    elif kind == "source_digest": doc["rows"][0]["execution_digest"] = "bad"
    elif kind == "missing_config": doc["configurations"].pop()
    elif kind == "missing_error": del config["results"]["error"]
    elif kind == "error_decision": config["results"]["error"]["criterion_met"] = True
    elif kind == "error_title": config["results"]["error"]["title"] = "H1 PASS"
    elif kind == "curves": record["seed_curves"][0][0] += 0.1
    elif kind == "mean_curve": record["mean_curve"][0] += 0.1
    elif kind == "rho_range": record["rho"] = 5.0
    elif kind == "point_not_in_support": record["rho"] = 0.123456789
    elif kind == "point_null_without_undefined": record["rho"] = None
    elif kind == "interval": record["ci_high"] = 0.0
    elif kind == "decision": record["criterion_met"] = False
    elif kind == "int_decision": record["criterion_met"] = 1
    elif kind == "reason": record["reason"] = "no relationship exists"
    elif kind == "undefined_seed": record["per_seed_rho"][0] = None
    elif kind == "mass": record["support"]["atoms"][0]["mass"] = 0.0
    elif kind == "count": record["support"]["atoms"][0]["count"] -= 1
    elif kind == "bool_count": record["support"]["atoms"][0]["count"] = True
    elif kind == "undefined_count": record["support"]["undefined_count"] = 1
    elif kind == "duplicate_atom": record["support"]["atoms"].append(copy.deepcopy(record["support"]["atoms"][0]))
    elif kind == "overall": doc["overall"]["all_five_meet_disagreement_criterion"] = False
    else: raise AssertionError(kind)


@pytest.mark.parametrize("kind", [
    "version", "bool_version", "extra", "disclosure", "timing", "rule", "fit_commit", "analysis_dirty",
    "missing_row", "duplicate", "seed", "bool_seed", "roles", "pairing", "source_id", "source_config", "source_mean", "source_digest",
    "missing_config", "missing_error", "error_decision", "error_title", "curves", "mean_curve", "rho_range",
    "point_not_in_support", "point_null_without_undefined", "interval", "decision", "int_decision", "reason", "undefined_seed",
    "mass", "count", "bool_count", "undefined_count", "duplicate_atom", "overall",
])
def test_resigned_internally_inconsistent_reports_fail_closed(analyzed, tmp_path, kind):
    document = copy.deepcopy(analyzed.document)
    _mutate(document, kind)
    target = tmp_path / "resigned.json"
    digest = _signed(document, target)
    with pytest.raises(ValueError):
        R.replay_experiment_1_report(target, expected_sha256=digest)


@pytest.mark.parametrize("raw", [b'{"schema_version":1,"schema_version":1}', b'{"rho":NaN}', b'{"rho":Infinity}', b'{"rho":1e309}', b'\xff'])
def test_strict_json_refusals_even_with_matching_external_hash(tmp_path, raw):
    target = tmp_path / "not-strict.json"
    target.write_bytes(raw)
    with pytest.raises(ValueError):
        R.replay_experiment_1_report(target, expected_sha256=D.sha256_bytes(raw))


@pytest.mark.parametrize("kind", ["rows", "grid", "strings", "short", "duplicate", "generator"])
def test_writer_public_api_cannot_accept_handcrafted_or_incomplete_input(analyzed, tmp_path, monkeypatch, kind):
    bad = {"rows": analyzed.document["rows"], "grid": analyzed.document,
           "strings": [str(p) for p in analyzed.store.paths], "short": analyzed.store.paths[:-1],
           "duplicate": (analyzed.store.paths[0], *analyzed.store.paths[:-1]),
           "generator": iter(analyzed.store.paths)}[kind]
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    with pytest.raises(ValueError):
        R.write_experiment_1_report(bad, expected_fit_commit=FIT_COMMIT, analysis_commit=ANALYSIS_COMMIT,
                                   report_path=tmp_path / "report.json")


@pytest.mark.parametrize("field", ["expected_fit_commit", "analysis_commit"])
def test_writer_requires_exact_commits_before_source_access(analyzed, tmp_path, monkeypatch, field):
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    kwargs = dict(expected_fit_commit=FIT_COMMIT, analysis_commit=ANALYSIS_COMMIT, report_path=tmp_path / "report.json")
    kwargs[field] = "unknown"
    with pytest.raises(ValueError, match=field):
        R.write_experiment_1_report(analyzed.store.paths, **kwargs)
    del kwargs[field]
    with pytest.raises(TypeError):
        R.write_experiment_1_report(analyzed.store.paths, **kwargs)


@pytest.mark.parametrize("state", [GitState(ANALYSIS_COMMIT, True, "main"), GitState("c" * 40, False, "main"), GitState("UNCOMMITTED", False, "main")])
def test_actual_analysis_provenance_not_a_caller_stamp(analyzed, tmp_path, monkeypatch, state):
    monkeypatch.setattr(R, "git_state", lambda: state)
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    with pytest.raises(ValueError, match="clean trustworthy"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=tmp_path / "report.json")


def test_dirty_even_with_lying_trustworthy_property_refused_before_loader(analyzed, tmp_path, monkeypatch):
    state = GitState(ANALYSIS_COMMIT, True, "main")
    monkeypatch.setattr(GitState, "trustworthy", property(lambda self: True))
    assert state.trustworthy is True and state.dirty is True
    monkeypatch.setattr(R, "git_state", lambda: state)
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    with pytest.raises(ValueError, match="clean trustworthy"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=tmp_path / "report.json")


def test_roles_swapped_between_units_are_not_repaired_by_total_30(analyzed, tmp_path):
    doc = copy.deepcopy(analyzed.document)
    reference = next(row for row in doc["rows"] if len(row["roles"]) == 2)
    other = next(row for row in doc["rows"] if len(row["roles"]) == 1)
    reference["roles"], other["roles"] = other["roles"], reference["roles"]
    assert sum(len(row["roles"]) == 2 for row in doc["rows"]) == 30
    target = tmp_path / "role-swap.json"
    digest = _signed(doc, target)
    with pytest.raises(ValueError, match="exact registered Experiment-1 roles"):
        R.replay_experiment_1_report(target, expected_sha256=digest)


@pytest.mark.parametrize(("field", "value"), [
    ("CONFIDENCE_LEVEL", 0.90), ("TREND_PASS_REQUIRES_UPPER_BOUND_BELOW", 0.1),
    ("TREND_EXPECTED_DIRECTION", "positive"), ("TREND_BOOTSTRAP", "sampled"),
    ("TREND_QUANTILE_METHOD", "nearest"), ("SEEDS_HYPOTHESIS", 4),
    ("CONFIRMATORY_SEED_BASE", 2000), ("DATA_SIZES", (100, 250, 500, 1000, 2500)),
    ("NORMALISATION_SCALE_DOMAIN", "other"), ("NORMALISATION_SCALE_SOURCE", "failure_set"),
])
def test_changed_live_rule_refused_before_loader(analyzed, tmp_path, monkeypatch, field, value):
    monkeypatch.setattr(R.K, field, value)
    monkeypatch.setattr(R, "git_state", lambda: GitState(ANALYSIS_COMMIT, False, "main"))
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    with pytest.raises(ValueError, match="live constants"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=tmp_path / "report.json")


def test_replay_keeps_v1_rule_when_live_trend_constants_change(analyzed, monkeypatch):
    monkeypatch.setattr(R.K, "CONFIDENCE_LEVEL", 0.90)
    monkeypatch.setattr(R.K, "TREND_PASS_REQUIRES_UPPER_BOUND_BELOW", 0.2)
    monkeypatch.setattr(R.K, "NORMALISATION_SCALE_DOMAIN", "future_domain")
    monkeypatch.setattr(R, "_writer_contract", _forbidden)
    assert R.replay_experiment_1_report(analyzed.report, expected_sha256=analyzed.sha256) == analyzed.document


def test_changed_amendment_document_refused_before_loader(analyzed, tmp_path, monkeypatch):
    fake = tmp_path / "different-amendment.md"
    fake.write_text("different scientific choice", encoding="utf-8")
    monkeypatch.setattr(R, "_AMENDMENT_PATH", fake)
    monkeypatch.setattr(R, "git_state", lambda: GitState(ANALYSIS_COMMIT, False, "main"))
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    with pytest.raises(ValueError, match="amendment document digest"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=tmp_path / "report.json")


def test_analysis_tree_change_before_publication_refuses(analyzed, tmp_path, monkeypatch):
    states = iter([GitState(ANALYSIS_COMMIT, False, "main"), GitState(ANALYSIS_COMMIT, True, "main")])
    monkeypatch.setattr(R, "git_state", lambda: next(states))
    monkeypatch.setattr(R, "load_experiment_1_evidence", lambda *a, **k: None)
    monkeypatch.setattr(R, "_build", lambda *a: copy.deepcopy(analyzed.document))
    target = tmp_path / "report.json"
    with pytest.raises(ValueError, match="clean trustworthy"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=target)
    assert not target.exists()


@pytest.mark.parametrize("relation", ["inside", "equal", "outside_workspace"])
def test_source_overlap_or_outside_output_refuses_before_access(analyzed, tmp_path, monkeypatch, relation):
    source = analyzed.store.paths[0]
    target = source / "report.json" if relation == "inside" else source
    if relation == "outside_workspace":
        monkeypatch.setattr(R, "WORKSPACE_ROOT", tmp_path / "different-workspace")
        target = tmp_path / "report.json"
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    with pytest.raises(ValueError, match="overlap|workspace"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=target)


def test_hardlinked_destination_and_replay_refused(analyzed, tmp_path, monkeypatch):
    target, alias = tmp_path / "report.json", tmp_path / "alias.json"
    target.write_bytes(analyzed.report.read_bytes())
    os.link(target, alias)
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    with pytest.raises(ValueError, match="independent regular"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=target)
    with pytest.raises(ValueError, match="independent regular"):
        R.replay_experiment_1_report(target, expected_sha256=analyzed.sha256)


def test_regeneration_is_byte_identical_reopens_sources_and_rejects_divergence(analyzed, tmp_path, monkeypatch):
    monkeypatch.setattr(E, "load_fit_evidence", analyzed.store.load)
    monkeypatch.setattr(R, "git_state", lambda: GitState(ANALYSIS_COMMIT, False, "main"))
    target = tmp_path / "report.json"
    target.write_bytes(analyzed.report.read_bytes())
    before = (target.stat().st_mtime_ns, target.read_bytes())
    count = len(analyzed.store.calls)
    R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                               analysis_commit=ANALYSIS_COMMIT, report_path=target)
    assert len(analyzed.store.calls) == count + 150
    assert (target.stat().st_mtime_ns, target.read_bytes()) == before
    # Existing report is never a token permitting changed sources to pass.
    def tampered(*args, **kwargs):
        raise ValueError("synthetic source tampered")
    monkeypatch.setattr(E, "load_fit_evidence", tampered)
    with pytest.raises(ValueError, match="tampered"):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=target)
    assert (target.stat().st_mtime_ns, target.read_bytes()) == before
    monkeypatch.setattr(E, "load_fit_evidence", analyzed.store.load)
    target.write_bytes(b"prior immutable unrelated bytes\n")
    with pytest.raises(D.DivergentTargetError):
        R.write_experiment_1_report(analyzed.store.paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=target)
    assert target.read_bytes() == b"prior immutable unrelated bytes\n"


def test_report_zero_boundary_uses_core_and_is_not_a_pass(analyzed):
    rows = copy.deepcopy(analyzed.document["rows"])
    group = rows[0]["comparison_group_id"]
    for row in rows:
        if row["comparison_group_id"] == group:
            row["mean_disagreement"] = [1., 2., 3., 3., 2., 1.][R._SIZES.index(row["n_transitions"])]
    record = R._metric_record(group, "disagreement", rows)
    assert record["rho"] == record["ci_low"] == record["ci_high"] == 0.0
    assert record["criterion_met"] is False
    R._validate_metric(record, group, "disagreement", rows)


def test_report_undefined_replicates_remain_explicit_nulls_and_masses(analyzed):
    rows = copy.deepcopy(analyzed.document["rows"])
    group = rows[0]["comparison_group_id"]
    for row in rows:
        if row["comparison_group_id"] == group:
            row["mean_disagreement"] = 0.5
    record = R._metric_record(group, "disagreement", rows)
    assert record["rho"] is record["ci_low"] is record["ci_high"] is None
    assert record["per_seed_rho"] == [None] * 5
    assert record["support"] == {"n_resamples": 3125, "undefined_count": 3125, "undefined_mass": 1.0, "atoms": []}
    assert record["criterion_met"] is False
    assert record["status"] == "undefined" and "fails closed" in record["reason"]
    json.dumps(record, allow_nan=False)
    R._validate_metric(record, group, "disagreement", rows)


def test_no_mean_of_rhos_or_configuration_pooling(analyzed):
    rows = copy.deepcopy(analyzed.document["rows"])
    group = rows[0]["comparison_group_id"]
    seed_values = [[9., 7., 5., 4., 3., 2.]] * 4 + [[1., 3., 6., 9., 14., 20.]]
    for row in rows:
        if row["comparison_group_id"] == group:
            row["mean_disagreement"] = seed_values[row["seed"] - 1000][R._SIZES.index(row["n_transitions"])]
        else:
            row["mean_disagreement"] *= 1000  # must not enter this coefficient
    result = R._metric_record(group, "disagreement", rows)
    expected = T.trend_test({s: dict(zip(R._SIZES, v)) for s, v in zip(R._SEEDS, seed_values)}, partition="confirmatory")
    assert result["rho"] == expected.rho
    assert result["rho"] != pytest.approx(np.mean(expected.per_seed_rho))


def test_full_fabricated_150_fit_source_to_report_to_offline_replay(tmp_path, monkeypatch):
    """Unmodified physical reader + real statistic + writer, never training."""
    monkeypatch.setattr(F, "run_confirmatory", _forbidden)
    monkeypatch.setattr(R, "git_state", lambda: GitState(ANALYSIS_COMMIT, False, "main"))
    jobs = fixtures.experiment_1_jobs()
    paths = tuple(tmp_path / "sources" / f"fit-{i:03d}" for i in range(150))
    for path, job in zip(paths, jobs, strict=True):
        fixtures._make_sidecar(path, job)
    before = fixtures._tree_fingerprint(paths)
    calls = []
    original = E.load_fit_evidence
    assert original is F.load_fit_evidence
    def traced(path, *, expected_git_commit):
        calls.append((path, expected_git_commit))
        return original(path, expected_git_commit=expected_git_commit)
    monkeypatch.setattr(E, "load_fit_evidence", traced)
    report = R.write_experiment_1_report(paths, expected_fit_commit=FIT_COMMIT,
                                        analysis_commit=ANALYSIS_COMMIT, report_path=tmp_path / "report.json")
    assert calls == [(path.resolve(), FIT_COMMIT) for path in paths]
    assert fixtures._tree_fingerprint(paths) == before
    digest = D.sha256_file(report)
    monkeypatch.setattr(E, "load_fit_evidence", _forbidden)
    monkeypatch.setattr(R, "load_experiment_1_evidence", _forbidden)
    monkeypatch.setattr(R, "trend_test", _forbidden)
    doc = R.replay_experiment_1_report(report, expected_sha256=digest)
    assert len(doc["rows"]) == 150 and len(doc["configurations"]) == 5
    # A real-byte source mutation is refused on re-generation even though the
    # prior report still exists. Offline replay does not claim source auditing.
    monkeypatch.setattr(R, "load_experiment_1_evidence", E.load_experiment_1_evidence)
    monkeypatch.setattr(E, "load_fit_evidence", original)
    target = paths[0] / "evaluation" / "error.npy"
    target.write_bytes(target.read_bytes() + b"synthetic tamper")
    with pytest.raises(ValueError, match="artifact 'error' bytes"):
        R.write_experiment_1_report(paths, expected_fit_commit=FIT_COMMIT,
                                   analysis_commit=ANALYSIS_COMMIT, report_path=report)
    assert D.sha256_file(report) == digest
