"""Synthetic-only historical reuse: real evidence writer/reader, no training.

The synthetic authority pins below replace the production constants only in
these tests. No real run, label, preflight or result file is opened. All fit
documents are fabricated using the existing fit-evidence test fixture.
"""

from __future__ import annotations

import copy
import hashlib
import os
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_fit_evidence as fixture_source
from bu.durable import DivergentTargetError, atomic_write_json, read_json, sha256_file
from bu.experiments import batch as B
from bu.experiments import fit_evidence as F
from bu.experiments import week7_launch_plan as P
from bu.experiments import week7_sources as S


SYNTHETIC_COMMIT = "b" * 40


def _copy_fixture_file(source, destination):
    # Python 3.13's native Windows CopyFile2 raised a fatal stack overflow in
    # repeated fixture setup on this host. Synthetic fixtures need independent
    # bytes, not metadata preservation or the native fast-copy implementation.
    Path(destination).write_bytes(Path(source).read_bytes())
    return str(destination)


def _copy_fixture_tree(source, destination):
    assert not Path(destination).resolve().is_relative_to(Path(source).resolve())
    return shutil.copytree(source, destination, copy_function=_copy_fixture_file)


@pytest.fixture(scope="module")
def template(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic-history-template")
    output = root / "output"
    project_copy = root / "copy"
    preflight = root / "preflight"
    output.mkdir()
    preflight.mkdir()
    jobs = P.reused_experiment_2a_jobs()
    digests = []
    for job in jobs:
        planned = SimpleNamespace(unit=job.unit, arm=job.arm, seed=job.seed - 1000)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(fixture_source, "_registered_shared_fit", lambda: planned)
            fit = output / "jobs" / job.job_id
            completed, spec = fixture_source._completed_run(fit)
            F.write_fit_evidence(completed, fit_dir=fit)
            digests.append(read_json(fit / F.FIT_EVIDENCE_FILE)["execution_digest"])
            # Operational metadata is included in tree binding too.
            atomic_write_json(fit / "synthetic_attempt_receipt.json", {"fixture": True})
    preflight_file = atomic_write_json(preflight / "repair_label_preflight_report.json", {
        "environment": {"git": {
            "commit": SYNTHETIC_COMMIT, "dirty": False, "trustworthy": True,
        }},
    })
    label_file = atomic_write_json(output / "label_evidence.json", {
        "synthetic_provenance_only": True,
        "execution_digests": digests,
    })
    finalization_file = atomic_write_json(output / S.HISTORICAL_FINALIZATION_FILE, {
        "synthetic_provenance_only": True, "fit_commit": SYNTHETIC_COMMIT,
    })
    _copy_fixture_tree(output, project_copy)
    _copy_fixture_file(preflight_file, project_copy / preflight_file.name)
    return SimpleNamespace(
        root=root, jobs=jobs, digests=tuple(digests),
        preflight_sha=sha256_file(preflight_file), label_sha=sha256_file(label_file),
        finalization_sha=sha256_file(finalization_file),
    )


@pytest.fixture
def history(tmp_path, monkeypatch, template):
    root = tmp_path / "history"
    _copy_fixture_tree(template.root, root)
    attrs = {
        "PROJECT_ROOT": root,
        "HISTORICAL_OUTPUT_ROOT": root / "output",
        "HISTORICAL_COPY_ROOT": root / "copy",
        "HISTORICAL_PREFLIGHT_ROOT": root / "preflight",
        "HISTORICAL_EXECUTION_COMMIT": SYNTHETIC_COMMIT,
        "HISTORICAL_EXECUTION_DIGESTS": template.digests,
        "HISTORICAL_PREFLIGHT_SHA256": template.preflight_sha,
        "HISTORICAL_LABEL_SHA256": template.label_sha,
        "HISTORICAL_FINALIZATION_SHA256": template.finalization_sha,
    }
    for name, value in attrs.items():
        monkeypatch.setattr(S, name, value)
    sources = tuple(root / "output" / "jobs" / j.job_id for j in template.jobs)
    copies = tuple(root / "copy" / "jobs" / j.job_id for j in template.jobs)
    return SimpleNamespace(root=root, sources=sources, copies=copies, jobs=template.jobs)


def _resign(document):
    payload = {k: v for k, v in document.items() if k != "ledger_digest"}
    document["ledger_digest"] = hashlib.sha256(P._canonical(payload)).hexdigest()


def test_registered_historical_pins_are_not_blank_or_current_commit():
    assert S.HISTORICAL_EXECUTION_COMMIT == "750266c7b8c4eb955b03f6081a861aed1051907b"
    assert S.HISTORICAL_FINALIZER_COMMIT == "f6833f2eb0d0dc5652effdf4e1fc066722761d09"
    assert len(S.HISTORICAL_EXECUTION_DIGESTS) == len(set(S.HISTORICAL_EXECUTION_DIGESTS)) == 5
    assert all(len(d) == 64 for d in S.HISTORICAL_EXECUTION_DIGESTS)
    assert S.HISTORICAL_EXECUTION_COMMIT != S.HISTORICAL_FINALIZER_COMMIT


def test_full_reader_reopens_all_five_originals_and_copies(history, monkeypatch):
    original = F.load_fit_evidence
    calls = []
    def observed(path, *, expected_git_commit):
        calls.append((path, expected_git_commit))
        return original(path, expected_git_commit=expected_git_commit)
    monkeypatch.setattr(F, "load_fit_evidence", observed)
    before = {p: B._job_tree_digest(p) for p in history.sources + history.copies}
    ledger = S.build_week7_source_ledger()
    assert len(calls) == 10
    assert {p for p, _ in calls} == set(history.sources + history.copies)
    assert {commit for _, commit in calls} == {SYNTHETIC_COMMIT}
    assert ledger["reused_fit_count"] == 5
    assert ledger["newly_executed_fit_count"] == 0
    assert ledger["replacement_training_allowed"] is False
    assert ledger["reuse_inside_new_batch_directories_allowed"] is False
    assert [r["job"]["fit_id"] for r in ledger["sources"]] == list(P.REUSED_FIT_IDS)
    for row, source, dest in zip(ledger["sources"], history.sources, history.copies):
        assert row["source_tree_digest"] == row["copy_tree_digest"] == B._job_tree_digest(source)
        assert row["copy_evidence_digest"] == B._copy_evidence_digest(source, dest)
        assert row["source_tree_digest"] != row["copy_evidence_digest"]
        assert row["job"]["roles"] == ["exp2a", "repair_validation"]
        assert row["source_path"] == str(source)
        assert row["copy_path"] == str(dest)
    assert {p: B._job_tree_digest(p) for p in history.sources + history.copies} == before


def test_reuse_accepts_old_commit_even_when_current_source_commit_differs(history, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("reuse consulted current Git or executed a fit")
    monkeypatch.setattr(F, "git_state", forbidden)
    monkeypatch.setattr(B, "_default_executor", forbidden)
    assert S.build_week7_source_ledger()["historical_execution_commit"] == SYNTHETIC_COMMIT


def test_write_load_and_equal_retry_reopen_sources_without_reexecution(history, monkeypatch):
    output = history.root / "ledger"
    output.mkdir()
    path = S.write_week7_source_ledger(output)
    before = path.read_bytes(), path.stat().st_mtime_ns
    loaded = S.load_week7_source_ledger(path)
    assert S.reverify_week7_source_ledger(loaded) == loaded
    assert S.write_week7_source_ledger(output) == path
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    # A valid snapshot cannot survive a subsequently missing source.
    missing = history.sources[-1] / F.FIT_EVIDENCE_FILE
    missing.unlink()
    with pytest.raises(ValueError):
        S.load_week7_source_ledger(path)


@pytest.mark.parametrize("side", ["source", "copy"])
@pytest.mark.parametrize("change", ["missing", "payload", "extra_file"])
def test_missing_or_changed_source_never_becomes_replacement_training(history, monkeypatch, side, change):
    root = history.sources[0] if side == "source" else history.copies[0]
    def forbidden(*args, **kwargs):
        pytest.fail("historical failure attempted replacement training")
    monkeypatch.setattr(B, "_default_executor", forbidden)
    path = root / F.FIT_EVIDENCE_FILE
    if change == "missing":
        path.unlink()
    elif change == "payload":
        error = root / read_json(path)["artifacts"]["error"]["path"]
        error.write_bytes(error.read_bytes() + b"corrupt")
    else:
        (root / "invented.txt").write_text("not in other tree")
    with pytest.raises(ValueError):
        S.build_week7_source_ledger()


def test_changed_both_copies_are_not_their_own_historical_digest_authority(history):
    for root in (history.sources[0], history.copies[0]):
        fixture_source._resign_physical_sources(
            root, lambda run, confirm: run.__setitem__("started_utc", "2026-08-29T00:00:00+00:00"),
        )
    # Both fit readers can validate a coherent source; only the external
    # historical execution digest distinguishes it from the real old source.
    F.load_fit_evidence(history.sources[0], expected_git_commit=SYNTHETIC_COMMIT)
    with pytest.raises(ValueError, match="pinned execution_digest"):
        S.build_week7_source_ledger()


def test_source_own_commit_is_never_taken_as_expected_authority(history):
    for root in (history.sources[0], history.copies[0]):
        fixture_source._resign_physical_sources(
            root, lambda run, confirm: run["git"].__setitem__("commit", "c" * 40),
        )
    with pytest.raises(ValueError, match="Git commit"):
        S.build_week7_source_ledger()


@pytest.mark.parametrize("mutation", [
    "missing", "duplicate", "reorder", "commit", "digest", "path", "train",
    "role", "tree", "copy_attestation", "replacement", "bool_schema", "float_count", "extra",
])
def test_resigned_ledger_not_its_own_authority(history, mutation):
    ledger = S.build_week7_source_ledger()
    forged = copy.deepcopy(ledger)
    rows = forged["sources"]
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows[-1] = copy.deepcopy(rows[0])
    elif mutation == "reorder":
        rows.reverse()
    elif mutation == "commit":
        forged["historical_execution_commit"] = "c" * 40
    elif mutation == "digest":
        rows[0]["execution_digest"] = "d" * 64
    elif mutation == "path":
        rows[0]["source_path"] = rows[0]["copy_path"]
    elif mutation == "train":
        rows[0]["job"]["config"]["train"]["lr"] *= 2
    elif mutation == "role":
        rows[0]["job"]["roles"] = ["exp2a"]
    elif mutation == "tree":
        rows[0]["source_tree_digest"] = "e" * 64
    elif mutation == "copy_attestation":
        rows[0]["copy_evidence_digest"] = rows[0]["source_tree_digest"]
    elif mutation == "replacement":
        forged["replacement_training_allowed"] = True
    elif mutation == "bool_schema":
        forged["week7_source_ledger_schema_version"] = True
    elif mutation == "float_count":
        forged["reused_fit_count"] = 5.0
    else:
        forged["ignore_missing"] = True
    _resign(forged)
    with pytest.raises(ValueError, match="pinned/reopened history"):
        S.reverify_week7_source_ledger(forged)


@pytest.mark.parametrize("field,value", [
    ("fit_id", "wrong"), ("unit_id", "wrong"), ("roles", ("exp2a",)),
    ("seed", True), ("execution_stage", "repair_validation"),
    ("n_train", 5001), ("ensemble_size", 1), ("fit_dir", Path("somewhere_else")),
])
def test_consumer_checks_identity_even_when_inner_reader_is_stubbed(history, monkeypatch, field, value):
    original = F.load_fit_evidence
    def drift(path, *, expected_git_commit):
        value_read = original(path, expected_git_commit=expected_git_commit)
        return replace(value_read, **{field: value})
    monkeypatch.setattr(F, "load_fit_evidence", drift)
    with pytest.raises(ValueError, match="pinned|different source"):
        S.build_week7_source_ledger()


def test_full_config_checked_beyond_fit_identity(history, monkeypatch):
    original = F.load_fit_evidence
    values = {p: original(p, expected_git_commit=SYNTHETIC_COMMIT) for p in history.sources + history.copies}
    for root in (history.sources[0], history.copies[0]):
        run = root / history.jobs[0].config.run_id / "run.json"
        row = read_json(run)
        row["config"]["train"]["lr"] *= 2
        run.write_bytes(fixture_source._json_bytes(row))
    monkeypatch.setattr(F, "load_fit_evidence", lambda path, **kwargs: values[path])
    with pytest.raises(ValueError, match="full registered configuration"):
        S.build_week7_source_ledger()


@pytest.mark.parametrize("authority", ["preflight", "label", "finalization"])
def test_modified_historical_authority_refused_before_payload_loading(history, monkeypatch, authority):
    if authority == "preflight":
        path = S.HISTORICAL_PREFLIGHT_ROOT / "repair_label_preflight_report.json"
    elif authority == "label":
        path = S.HISTORICAL_OUTPUT_ROOT / "label_evidence.json"
    else:
        path = S.HISTORICAL_OUTPUT_ROOT / S.HISTORICAL_FINALIZATION_FILE
    path.write_bytes(path.read_bytes() + b"\n")
    monkeypatch.setattr(F, "load_fit_evidence", lambda *a, **k: pytest.fail("read payload too early"))
    with pytest.raises(ValueError, match="independently pinned digest"):
        S.build_week7_source_ledger()


def test_hardlinked_copy_refused(history):
    source = history.sources[0] / F.FIT_EVIDENCE_FILE
    dest = history.copies[0] / F.FIT_EVIDENCE_FILE
    dest.unlink()
    os.link(source, dest)
    with pytest.raises(ValueError, match="aliases|hard-linked"):
        S.build_week7_source_ledger()


def test_authority_hardlinked_copy_refused(history):
    source = S.HISTORICAL_PREFLIGHT_ROOT / "repair_label_preflight_report.json"
    dest = S.HISTORICAL_COPY_ROOT / source.name
    dest.unlink()
    os.link(source, dest)
    with pytest.raises(ValueError, match="independent files"):
        S.build_week7_source_ledger()


def test_same_roots_refused(history, monkeypatch):
    monkeypatch.setattr(S, "HISTORICAL_COPY_ROOT", S.HISTORICAL_OUTPUT_ROOT)
    with pytest.raises(ValueError):
        S.build_week7_source_ledger()


def test_path_outside_project_refused_before_read(history, tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text('{}')
    with pytest.raises(ValueError, match="project-local"):
        S.load_week7_source_ledger(outside)


def test_symlink_component_refused_without_needing_windows_symlink_privilege(history, monkeypatch):
    real = Path.lstat
    path = history.sources[0]
    def linked(self, *args, **kwargs):
        info = real(self, *args, **kwargs)
        if self == path:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path, "lstat", linked)
    with pytest.raises(ValueError, match="link/junction"):
        S.build_week7_source_ledger()


def test_copy_changed_while_reader_runs_fails_closed(history, monkeypatch):
    original = F.load_fit_evidence
    def altered(path, *, expected_git_commit):
        result = original(path, expected_git_commit=expected_git_commit)
        if path == history.copies[0]:
            (path / "changed-during-read").write_text("invalid")
        return result
    monkeypatch.setattr(F, "load_fit_evidence", altered)
    with pytest.raises(ValueError):
        S.build_week7_source_ledger()


def test_nested_junction_refused_before_tree_hashing(history, monkeypatch):
    real = Path.lstat
    redirected = history.sources[0] / history.jobs[0].config.run_id
    def linked(self, *args, **kwargs):
        info = real(self, *args, **kwargs)
        if self == redirected:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path, "lstat", linked)
    monkeypatch.setattr(B, "_copy_evidence_digest", lambda *a: pytest.fail("hashed redirected bytes"))
    with pytest.raises(ValueError, match="link/junction"):
        S.build_week7_source_ledger()


def test_divergent_existing_ledger_preserved(history):
    output = history.root / "ledger"
    output.mkdir()
    path = output / S.WEEK7_SOURCE_LEDGER_FILE
    path.write_text('{}\n')
    with pytest.raises(DivergentTargetError):
        S.write_week7_source_ledger(output)
    assert path.read_text() == '{}\n'


@pytest.mark.parametrize("invalid", [None, [], "ledger", True, {"nan": float("nan")}])
def test_invalid_ledger_refused_before_reopening_sources(monkeypatch, invalid):
    monkeypatch.setattr(S, "build_week7_source_ledger", lambda: pytest.fail("invalid input reopened sources"))
    with pytest.raises(ValueError):
        S.reverify_week7_source_ledger(invalid)
