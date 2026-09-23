"""Local synthetic label-source provenance; no labels or training are produced."""
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from bu.durable import sha256_file
from bu.experiments import week8_exp2a_recovery as C
from bu.experiments import week8_exp2a_label_finalization as Z
from test_week8_relocation_metadata import (
    M, X, W, S, COMMIT, authority, source_trees, environment, relocated,
    relocated_preflight, relocated_checkpoint, completed_history, completed_epoch,
    copy_synthetic_fit, persist_new_repair,
)


@pytest.fixture
def released_inventory(completed_epoch, monkeypatch):
    d = completed_epoch
    new_job, path, _ = persist_new_repair(d)
    copy_synthetic_fit(d["store"], path.parent, d["roots"]["sync"] / "jobs" / new_job.job_id)
    copy_synthetic_fit(d["store"], d["roots"]["output"] / "jobs" / M.ORPHAN_JOB_ID,
                       d["roots"]["sync"] / "jobs" / M.ORPHAN_JOB_ID)
    d["lease"].release()
    reader = M.ReleasedInventoryReader(d["access"], d["readers"])
    monkeypatch.setattr(C, "EXECUTION_COMMIT", COMMIT)
    # Native/helper admission is tested separately. All inventory and pair
    # readers here are real, installed readers over actual synthetic files.
    monkeypatch.setattr(C, "_parent_readers", lambda: {
        "sources": d["sources"], "checkpoints": d["checkpoints"], "released": reader})
    def no_training(*a, **k):
        pytest.fail("source validation attempted training")
    monkeypatch.setattr(X.F, "run_confirmatory_fit", no_training)
    plan, ledger = W.WORKSPACE_ROOT / "plan.json", W.WORKSPACE_ROOT / "ledger.json"
    inputs = Z.Exp2AFinalizationInputs(plan, sha256_file(plan), ledger, sha256_file(ledger),
        d["new_path"], sha256_file(d["new_path"]), COMMIT, "c" * 40)
    with reader.installed():
        yield d, reader, inputs


def test_label_collection_preserves_historical_records_and_verifies_current_pairs(released_inventory, monkeypatch):
    d, reader, inputs = released_inventory
    before = {d["old_path"]: d["old_path"].read_bytes(),
              Path(inputs.source_ledger_path): Path(inputs.source_ledger_path).read_bytes()}
    calls = []
    original = Z._verify_pair
    def pair(job, row):
        calls.append(job.job_id)
        return original(job, row)
    monkeypatch.setattr(Z, "_verify_pair", pair)
    inventory = Z._collect_sources(inputs)
    assert len(inventory["sources"]) + len(inventory["pending_new_fit_ids"]) == 384
    assert len(inventory["non_label_existing_fit_ids"]) == 32
    assert len(calls) == len(set(calls)) == 155 + len(d["completed"]) + 1
    assert len(calls) + len(inventory["pending_new_fit_ids"]) == 416
    assert inventory["execution_context_digest"] == d["new"]["execution_context_digest"]
    originals = {row["job"]["job_id"]: row for row in d["ledger"]["sources"]}
    old_rows = [row for row in inventory["sources"] if row["job"]["job_id"] in originals]
    assert len(old_rows) == 123
    for row in old_rows:
        old = originals[row["job"]["job_id"]]
        assert row["source_path"] != old["source_path"]
        assert row["copy_evidence_digest"] != old["copy_evidence_digest"]
        assert row["source_tree_digest"] == old["source_tree_digest"]
    assert all(path.read_bytes() == raw for path, raw in before.items())


def test_parent_reopens_real_inventory_and_rejects_changed_origin(released_inventory):
    d, reader, inputs = released_inventory
    inventory = reader.load_inventory(checkpoint_path=inputs.checkpoint_path,
        checkpoint_sha256=inputs.checkpoint_sha256, expected_execution_commit=COMMIT)
    historical = next(row for row in inventory["source_provenance"]
                      if row["origin"]["kind"] == "historical_source_ledger")
    historical["origin"] = copy.deepcopy(historical["origin"])
    historical["origin"]["source"]["copy_evidence_digest"] = "0" * 64
    with pytest.raises(C.RecoveryRefused, match="independently reopened provenance"):
        C.validate_relocated_finalization_inventory(inventory, d["ledger"],
            checkpoint_path=inputs.checkpoint_path, checkpoint_sha256=inputs.checkpoint_sha256,
            ledger_sha256=inputs.source_ledger_sha256, expected_execution_commit=COMMIT)


@pytest.fixture
def inventory_contract(tmp_path, monkeypatch):
    binding = {"relocation_schema_version": 1, "attestation_sha256": "a" * 64}
    historical = {"job": {"job_id": "old"}, "source_path": "historical", "copy_evidence_digest": "b" * 64}
    current = {**historical, "source_path": str(tmp_path / "current"), "copy_evidence_digest": "c" * 64}
    ledger = {"sources": [historical]}
    fresh = {"start": {"exp2a_repair_start_schema_version": 2, "relocation": binding},
        "ledger": ledger, "roots": {"output": tmp_path}, "sources": [current],
        "pending_new_fit_ids": ["pending"], "relocation": binding,
        "source_provenance": [{"job_id": "old", "origin": {"kind": "historical_source_ledger",
            "ledger_sha256": "d" * 64, "source": historical}}]}
    calls = []
    args = dict(checkpoint_path=tmp_path / "checkpoint.json", checkpoint_sha256="e" * 64,
        ledger_sha256="d" * 64, expected_execution_commit=C.EXECUTION_COMMIT)
    def reopen(**kwargs):
        assert kwargs == {key: value for key, value in args.items() if key != "ledger_sha256"}
        calls.append(True)
        return copy.deepcopy(fresh)
    monkeypatch.setattr(C, "_parent_readers", lambda: {
        "sources": SimpleNamespace(ledger_sha256="d" * 64),
        "checkpoints": SimpleNamespace(relocation_binding=lambda: copy.deepcopy(binding)),
        "released": SimpleNamespace(load_inventory=reopen)})
    return fresh, ledger, args, calls


def test_parent_inventory_contract_reopens_exact_independent_pins(inventory_contract):
    fresh, ledger, args, calls = inventory_contract
    C.validate_relocated_finalization_inventory(copy.deepcopy(fresh), ledger, **args)
    assert calls == [True]


@pytest.mark.parametrize("damage", ["missing_origin", "duplicate_origin", "extra_origin", "origin_kind",
    "origin_identity", "current_identity", "scientific_tree", "ledger", "relocation", "start_relocation",
    "float_schema", "legacy_schema", "pending", "root", "string_root", "extra_field", "ledger_pin", "commit"])
def test_parent_inventory_contract_refuses_untrusted_assertions(inventory_contract, damage):
    fresh, ledger, args, _ = inventory_contract
    document = copy.deepcopy(fresh)
    if damage == "missing_origin": document["source_provenance"] = []
    elif damage == "duplicate_origin": document["source_provenance"] *= 2
    elif damage == "extra_origin": document["source_provenance"].append({"job_id": "extra", "origin": {}})
    elif damage == "origin_kind": document["source_provenance"][0]["origin"]["kind"] = "relocated_epoch_fit"
    elif damage == "origin_identity": document["source_provenance"][0]["origin"]["source"]["copy_evidence_digest"] = "0" * 64
    elif damage == "current_identity": document["sources"][0]["copy_evidence_digest"] = "b" * 64
    elif damage == "scientific_tree": document["sources"][0]["source_tree_digest"] = "0" * 64
    elif damage == "ledger": document["ledger"] = {}
    elif damage == "relocation": document["relocation"] = {}
    elif damage == "start_relocation": document["start"]["relocation"] = {}
    elif damage == "float_schema": document["start"]["exp2a_repair_start_schema_version"] = 2.0
    elif damage == "legacy_schema": document["start"]["exp2a_repair_start_schema_version"] = 1
    elif damage == "pending": document["pending_new_fit_ids"] = []
    elif damage == "root": document["roots"]["output"] /= "elsewhere"
    elif damage == "string_root": document["roots"]["output"] = str(document["roots"]["output"])
    elif damage == "extra_field": document["unverified"] = True
    elif damage == "ledger_pin": args["ledger_sha256"] = "0" * 64
    else: args["expected_execution_commit"] = "0" * 40
    with pytest.raises(C.RecoveryRefused):
        C.validate_relocated_finalization_inventory(document, ledger, **args)


def test_relocated_inventory_requires_native_parent_admission(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "_ACTIVE_RELOCATION", None)
    with pytest.raises(C.RecoveryRefused, match="not admitted"):
        C.validate_relocated_finalization_inventory({}, {}, checkpoint_path=tmp_path / "unused",
            checkpoint_sha256="a" * 64, ledger_sha256="b" * 64, expected_execution_commit=C.EXECUTION_COMMIT)
