"""Synthetic parent admission and independent relocation evidence checks."""
import copy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from bu.experiments import week8_exp2a_recovery as C
from bu.experiments import week8_relocation_provenance as V
from bu.durable import atomic_write_json
from bu.experiments.supervisor import acquire_batch_lease
from test_week8_relocation_metadata import (
    M, X, COMMIT, authority, source_trees, environment, relocated,
    relocated_preflight, relocated_checkpoint, control_history, control_scope,
)


@pytest.mark.parametrize("failure", [None, "handler", "helper", "authority"])
def test_parent_installs_real_readers_and_restores(control_history, monkeypatch, failure):
    d = control_history
    raw = {"synthetic": True}
    raw_module = ModuleType(C.RAW_AUTHORITY_MODULE_NAME)
    completed = M.CompletedJobReaders(d["access"], d["checkpoints"])
    released = M.ReleasedInventoryReader(d["access"], completed)
    changed = False
    validations = []
    metadata = SimpleNamespace(
        load_registered_access=lambda verifier: d["access"],
        SourceReaders=lambda *a: d["sources"],
        PreflightReaders=lambda *a: d["preflight"],
        CheckpointReaders=lambda *a: d["checkpoints"],
        CompletedJobReaders=lambda *a: completed,
        EventReaders=lambda *a: d["events"],
        ControlReaders=lambda *a: d["reader"],
        ReleasedInventoryReader=lambda *a: released,
        POLICY_SHA256="a" * 64, EXPECTED_PAIR_COUNT=len(d["access"]._pairs),
        EXPECTED_DOCUMENT_COUNT=len(d["access"]._documents),
    )
    def validate(value):
        assert value is raw
        validations.append(True)
        return {"helper_schema_version": 1, "synthetic_changed": changed}
    bundle = SimpleNamespace(modules={"metadata": metadata, "provenance": object()}, validate=validate)
    loads = []
    def load(value):
        assert value is raw
        loads.append(True)
        return bundle
    raw_module.load_verified_relocation_helpers = load
    monkeypatch.setitem(sys.modules, C.RAW_AUTHORITY_MODULE_NAME, raw_module)
    before = X._read_start, X._baseline, X._load_events, X.load_released_exp2a_source_inventory, d["P"]._load_control
    def run():
        nonlocal changed
        with C._parent_relocation({"raw_authority": raw}):
            access, binding = C._relocation_state()
            assert access is d["access"]
            assert C._parent_readers()["controls"] is d["reader"]
            assert binding["attestation_sha256"] == access.attestation_sha256
            assert X._read_start == d["checkpoints"].read_start
            assert X.load_released_exp2a_source_inventory == released.load_inventory
            control = d["P"]._load_control(COMMIT, monitor_only=True)
            checkpoint, _ = d["P"]._checkpoint_material(control)
            assert d["P"]._events_material(control, checkpoint) == (d["rows"], [])
            with pytest.raises(C.RecoveryRefused, match="already active"):
                with C._parent_relocation({"raw_authority": raw}):
                    pytest.fail("nested parent admitted")
            if failure == "handler":
                raise ValueError("synthetic handler refusal")
            if failure == "helper":
                changed = True
            if failure == "authority":
                monkeypatch.setitem(sys.modules, C.RAW_AUTHORITY_MODULE_NAME, ModuleType("replacement"))
    if failure is None:
        run()
    else:
        with pytest.raises(ValueError, match={"handler": "handler refusal", "helper": "binding changed", "authority": "module changed"}[failure]):
            run()
    assert C._ACTIVE_RELOCATION is None
    assert (X._read_start, X._baseline, X._load_events, X.load_released_exp2a_source_inventory, d["P"]._load_control) == before
    assert loads == [True]
    assert len(validations) >= 3


def test_parent_requires_its_own_admitted_state(monkeypatch):
    monkeypatch.setattr(C, "_ACTIVE_RELOCATION", None)
    with pytest.raises(C.RecoveryRefused, match="not admitted"):
        C._relocation_state()
    with pytest.raises(C.RecoveryRefused, match="unavailable"):
        with C._parent_relocation({"command": "status"}):
            pytest.fail("missing raw admission accepted")


@pytest.fixture
def final_checkpoints(control_scope, monkeypatch):
    d = control_scope
    W, reader = C.Plan, d["checkpoints"]
    active = W.COMMON_LEASE_ROOT / "leases" / f"{W.COMMON_LEASE_NAME}.lease.json"
    old_proof = X._lease_record(reader.old_token)
    # Only the synthetic old lease is moved; D-161 transition has separate tests.
    active.rename(active.with_suffix(".synthetic-orphan"))
    historical = X._historical_lease_record
    monkeypatch.setattr(X, "_historical_lease_record", lambda token:
                        old_proof if token == reader.old_token else historical(token))
    with acquire_batch_lease(W.COMMON_LEASE_ROOT, lease_name=W.COMMON_LEASE_NAME) as lease:
        path = X.write_exp2a_repair_start_checkpoint(
            source_ledger_path=d["sources"].ledger_logical_path, expected_git_commit=COMMIT,
            output_root=d["roots"]["output"], staging_root=d["roots"]["staging"],
            sync_root=d["roots"]["sync"], attempt_timeout_seconds=3600.0,
            lease=lease, preflight_report=d["roots"]["preflight"] / X.PREFLIGHT_FILE)
        token = lease.token
    monkeypatch.setattr(C, "EXECUTION_COMMIT", COMMIT)
    monkeypatch.setattr(C, "EXPECTED_OLD_CHECKPOINT_DIGEST", reader.old_checkpoint_digest)
    monkeypatch.setattr(C, "EXPECTED_PLAN_DIGEST", d["old"]["plan_digest"])
    monkeypatch.setattr(C, "EXPECTED_HASHES", {**C.EXPECTED_HASHES,
        "old_checkpoint": reader.old_sha256, "old_lease": old_proof["sha256"],
        "preflight_report": d["preflight"].sha256,
        "source_ledger_file": d["sources"].ledger_sha256})
    monkeypatch.setattr(C, "_parent_readers", lambda: {"checkpoints": reader, "controls": d["reader"]})
    def no_science(*a, **k):
        pytest.fail("final metadata proof opened scientific or environment validation")
    monkeypatch.setattr(X, "_environment", no_science)
    monkeypatch.setattr(X.F, "load_fit_evidence", no_science)
    d["store"].loads.clear()
    return d, path, token


def test_parent_final_checkpoints_prove_two_epochs_without_science(final_checkpoints):
    d, path, token = final_checkpoints
    actual = C._checkpoint_documents()
    assert set(actual) == {C.OLD_LEASE_TOKEN, token}
    assert actual[C.OLD_LEASE_TOKEN] == (d["old"], d["checkpoints"].old_sha256)
    assert actual[token] == (C.read_json(path), C.sha256_file(path))
    assert actual[token][0]["execution_context_digest"] != d["old"]["execution_context_digest"]
    assert not d["store"].loads
    # Initial status still rejects a completed two-epoch namespace.
    control = d["P"]._load_control(COMMIT, monitor_only=True)
    with pytest.raises(M.MetadataRefused, match="exactly the old checkpoint"):
        d["reader"].checkpoint_material(control)


@pytest.mark.parametrize("damage", ["scientific_setting", "relocation", "context", "third_checkpoint", "released_lease", "active_lease", "old_bytes"])
def test_parent_final_checkpoint_proof_refuses_substitution(final_checkpoints, damage):
    d, path, token = final_checkpoints
    if damage in {"scientific_setting", "relocation"}:
        document = C.read_json(path)
        if damage == "scientific_setting": document["attempt_timeout_seconds"] = 7200.0
        else: document["relocation"]["attestation_sha256"] = "0" * 64
        context = X._execution_context(document)
        document["execution_context_digest"] = context["execution_context_digest"]
        document = C.Plan._seal({k:v for k,v in document.items() if k != "checkpoint_digest"}, "checkpoint_digest")
        for role in ("output", "sync"):
            (d["roots"][role] / C.Plan.START_DIRECTORY / path.name).write_bytes(X.L._pretty_json_bytes(document))
            (d["roots"][role] / M.RELOCATION_CONTEXT_FILE).write_bytes(X.L._pretty_json_bytes(context))
    elif damage == "context":
        (d["roots"]["sync"] / M.RELOCATION_CONTEXT_FILE).write_bytes(b"{}")
    elif damage == "third_checkpoint":
        for role in ("output", "sync"):
            atomic_write_json(d["roots"][role] / C.Plan.START_DIRECTORY / ("f" * 32 + ".json"), {})
    elif damage in {"released_lease", "active_lease"}:
        root = C.Plan.COMMON_LEASE_ROOT / "leases"
        history = root / "history" / f"{C.Plan.COMMON_LEASE_NAME}.{token}.released.json"
        if damage == "active_lease":
            (root / f"{C.Plan.COMMON_LEASE_NAME}.lease.json").write_bytes(history.read_bytes())
        else:
            row = C.read_json(history)
            row["timestamp_utc"] = "2026-09-02T00:00:00Z"
            history.write_bytes(X.L._pretty_json_bytes(row))
    else:
        target = d["roots"]["output"] / C.Plan.START_DIRECTORY / f"{C.OLD_LEASE_TOKEN}.json"
        target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        C._checkpoint_documents()


@pytest.mark.parametrize("tamper", [False, True])
def test_parent_history_scope_uses_exact_transition_validator_and_restores(monkeypatch, tamper):
    calls = []
    ordinary = lambda token: calls.append(("ordinary", token)) or {"ordinary": token}
    orphan = lambda token: calls.append(("orphan", token)) or {"orphan": token}
    monkeypatch.setattr(C.Launch, "_historical_lease_record", ordinary)
    monkeypatch.setattr(C, "historical_orphan_lease_record", orphan)
    def run():
        with C._parent_orphan_history():
            assert C.Launch._historical_lease_record(C.OLD_LEASE_TOKEN) == {"orphan": C.OLD_LEASE_TOKEN}
            assert C.Launch._historical_lease_record("d" * 32) == {"ordinary": "d" * 32}
            if tamper: C.Launch._historical_lease_record = lambda token: None
    if tamper:
        with pytest.raises(C.RecoveryRefused, match="failed restoration"): run()
    else: run()
    assert calls == [("orphan", C.OLD_LEASE_TOKEN), ("ordinary", "d" * 32)]
    assert C.Launch._historical_lease_record is ordinary


@pytest.fixture
def pair(tmp_path):
    local, durable = tmp_path / "local", tmp_path / "durable"
    for path in (local, durable):
        path.mkdir()
        (path / "evidence.bin").write_bytes(b"synthetic preserved evidence")
    tree = C.B._job_tree_digest(local)
    policy = V.Pair("preserved-001", "D:/Aenv/pro/pro/local/job", "D:/Aenv/pro/pro/durable/job",
                    "local", "durable", tree, "1" * 64)
    original = tmp_path / "original.json"
    original.write_bytes(b'{"synthetic":true}')
    documents = (V.Document("original.json", C.sha256_file(original)),)
    raw = V.build_record(tmp_path, (policy,), documents)
    access = V.EvidenceAccess(raw, C.sha256_bytes(raw), tmp_path, (policy,), documents)
    current = C.B._copy_evidence_digest(local, durable)
    assert current != policy.historical_copy_digest
    row = {"job_id": "job", "tree_digest": tree, "execution_digest": "2" * 64,
           "copy_evidence_digest": current, "historical_copy_evidence_digest": "1" * 64,
           "relocation_pair_key": policy.key}
    event = {"data": {"execution_digest": "2" * 64, "source_tree_digest": tree,
                       "copy_evidence_digest": "1" * 64}}
    return local, durable, access, row, event


def test_parent_records_both_identities_with_actual_independent_rehash(pair):
    local, durable, access, row, event = pair
    observed = C._validate_preserved_durable_pair("job", event, row, local, durable, access)
    assert observed == {**row, "tree_inventory_digest": C._tree_digest(C._plain_tree_inventory(local, what="test"))}


@pytest.mark.parametrize("field", ["tree_digest", "copy_evidence_digest", "historical_copy_evidence_digest", "relocation_pair_key", "execution_digest"])
def test_parent_refuses_resealed_inspector_pair_claims(pair, field):
    local, durable, access, row, event = pair
    row[field] = "f" * 64
    with pytest.raises(C.RecoveryRefused, match="copy evidence digest differs"):
        C._validate_preserved_durable_pair("job", event, row, local, durable, access)


@pytest.mark.parametrize("mutation", ["before", "during", "same_bytes", "event_current_identity"])
def test_parent_refuses_pair_drift_and_historical_identity_substitution(pair, monkeypatch, mutation):
    local, durable, access, row, event = pair
    if mutation == "before":
        (durable / "evidence.bin").write_bytes(b"changed")
    elif mutation == "same_bytes":
        path = durable / "evidence.bin"
        original = path.read_bytes()
        path.rename(durable.parent / "previous.bin")
        path.write_bytes(original)
    elif mutation == "event_current_identity":
        event["data"]["copy_evidence_digest"] = row["copy_evidence_digest"]
    else:
        original = C.B._copy_evidence_digest
        def swap(left, right):
            value = original(left, right)
            (right / "evidence.bin").write_bytes(b"changed after parent hashing")
            return value
        monkeypatch.setattr(C.B, "_copy_evidence_digest", swap)
    with pytest.raises(ValueError):
        C._validate_preserved_durable_pair("job", event, row, local, durable, access)


@pytest.fixture
def inspection(monkeypatch):
    binding = {"relocation_schema_version": 1, "attestation_sha256": "a" * 64,
        "policy_sha256": "b" * 64, "pair_count": 304, "document_count": 629,
        "helpers": {"helper_schema_version": 1, "synthetic": True}}
    trusted_binding = copy.deepcopy(binding)
    monkeypatch.setattr(C, "_relocation_state", lambda: (object(), copy.deepcopy(trusted_binding)))
    synced = [f"job-{i:03d}" for i in range(149)]
    started = sorted([*synced, C.ORPHAN_JOB_ID])
    return C._seal({
        "inspector_schema_version": 2, "status": "complete", "execution_commit": C.EXECUTION_COMMIT,
        "relocation": binding,
        "control": {"hashes": C.EXPECTED_HASHES, "plan_digest": C.EXPECTED_PLAN_DIGEST,
            "checkpoint": {"token": C.OLD_LEASE_TOKEN, "file_sha256": C.EXPECTED_HASHES["old_checkpoint"],
                "checkpoint_digest": C.EXPECTED_OLD_CHECKPOINT_DIGEST, "execution_context_digest": "c" * 64,
                "lease_sha256": C.EXPECTED_HASHES["old_lease"]},
            "active_lease": {"token": C.OLD_LEASE_TOKEN, "pid": C.OLD_LEASE_PID, "sha256": C.EXPECTED_HASHES["old_lease"]}},
        "events": {"count": 299, "chain_digest": C.EXPECTED_HASHES["old_event_stream"],
            "tail_file_sha256": C.EXPECTED_HASHES["old_event_tail_file"], "kind_counts": {"attempt_started": 150, "job_synced": 149},
            "started_job_ids": started, "synced_job_ids": synced},
        "jobs": {"roster_count": 261,
            "local_completed": [{"job_id": job, "tree_digest": "d" * 64, "execution_digest": "e" * 64,
                "attempt_receipt_sha256": "f" * 64, "child_pid": C.ORPHAN_CHILD_PID} for job in started],
            "durable_completed": [{"job_id": job, "tree_digest": "d" * 64, "execution_digest": "e" * 64,
                "copy_evidence_digest": "2" * 64, "historical_copy_evidence_digest": "1" * 64,
                "relocation_pair_key": f"pair-{job}"} for job in synced],
            "untouched_job_ids": [f"untouched-{i}" for i in range(111)], "orphan_job_id": C.ORPHAN_JOB_ID,
            "orphan_child_pid": C.ORPHAN_CHILD_PID, "hidden_partial": {"name": C.HIDDEN_PARTIAL_NAME,
                "file_count": 11, "orphan_local_file_count": 15, "inventory_digest": "3" * 64}},
        "staging": {"staging_count": 0, "quarantine_count": 0}, "lower_report_count": 0,
        "production_launch_receipt_present": False, "loaded_bu_modules": [{"module_id": "bu", "source_sha256": "4" * 64}],
        "scientific_files_opened": True, "scientific_outcomes_consulted": False,
        "scientific_values_emitted": False, "production_mutation_performed": False,
    }, "inspector_digest")


def test_parent_accepts_complete_schema_two_with_own_binding(inspection):
    assert C._validate_inspector_material(inspection) == inspection


@pytest.mark.parametrize("mutation", ["attestation", "helpers", "extra", "missing", "legacy", "old_identity_missing", "pair_key_missing"])
def test_parent_refuses_resealed_receipt_drift(inspection, mutation):
    if mutation in {"attestation", "helpers", "extra"}:
        key = {"attestation": "attestation_sha256", "helpers": "helpers", "extra": "extra"}[mutation]
        inspection["relocation"][key] = "f" * 64
    elif mutation == "missing":
        del inspection["relocation"]
    elif mutation == "legacy":
        inspection["inspector_schema_version"] = 1
    else:
        key = "historical_copy_evidence_digest" if mutation == "old_identity_missing" else "relocation_pair_key"
        del inspection["jobs"]["durable_completed"][0][key]
    inspection = C._seal({k: v for k, v in inspection.items() if k != "inspector_digest"}, "inspector_digest")
    with pytest.raises(C.RecoveryRefused):
        C._validate_inspector_material(inspection)


@pytest.mark.parametrize("mutation", [None, "legacy", "missing", "changed", "extra"])
def test_parent_incident_requires_its_own_relocation_admission(inspection, mutation):
    hidden_rows = [{"path": f"file-{i}", "kind": "file", "size": 1, "sha256": "1" * 64} for i in range(11)]
    checkpoint = inspection["control"]["checkpoint"]
    inventory = {
        "inventory_schema_version": 2, "execution_commit": C.EXECUTION_COMMIT,
        "relocation": copy.deepcopy(inspection["relocation"]), "control": {"synthetic": True},
        "lease": {"path": str((C.Plan.COMMON_LEASE_ROOT / "leases" / f"{C.Plan.COMMON_LEASE_NAME}.lease.json").resolve()),
            "sha256": C.EXPECTED_HASHES["old_lease"], "pid": C.OLD_LEASE_PID, "token": C.OLD_LEASE_TOKEN,
            "timestamp": 1.0, "timestamp_utc": "synthetic"},
        "checkpoint": {"token": C.OLD_LEASE_TOKEN, "sha256": checkpoint["file_sha256"],
            "checkpoint_digest": checkpoint["checkpoint_digest"], "execution_context_digest": checkpoint["execution_context_digest"]},
        "events": {**inspection["events"], "failure_count": 0},
        "jobs": {"registered_count": 261, **{key: value for key, value in inspection["jobs"].items()
                 if key not in {"roster_count", "hidden_partial"}},
            "hidden_partial": {"name": C.HIDDEN_PARTIAL_NAME, "entry_count": 11, "file_count": 11,
                "inventory": hidden_rows, "inventory_digest": C.sha256_bytes(C._canonical(hidden_rows))}},
        "staging": inspection["staging"], "lower_report_count": 0, "production_launch_receipt_present": False,
        "mechanical_source_validation_performed": True, "scientific_outcomes_consulted": False, "scientific_values_emitted": False,
    }
    if mutation == "legacy": inventory["inventory_schema_version"] = 1
    elif mutation == "missing": del inventory["relocation"]
    elif mutation == "changed": inventory["relocation"]["attestation_sha256"] = "f" * 64
    elif mutation == "extra": inventory["relocation"]["extra"] = True
    inventory = C._seal(inventory, "inventory_digest")
    liveness = {"stability": {"verdict": "pass"}, "synthetic": True}
    base = {"path": sys.executable, "sha256": "c" * 64}
    process = {"pid": 12345, "kernel_executable_path": sys.executable, "kernel_executable_sha256": "c" * 64,
               "creation_time_100ns": 123456789, "base_interpreter": base}
    incident = C._seal({**C._base_record("incident"), "status": "outcome_blind_interruption_adjudicated",
        "automatic_retry_allowed": False, "authority": {"base_python": base}, "controller_process": process, "inventory": inventory,
        "inventory_digest": inventory["inventory_digest"],
        "liveness_stability_reports": [{"report": liveness, "sha256": C.sha256_bytes(C._canonical(liveness))}]})
    if mutation is None:
        C._validate_incident_contract(incident)
    else:
        with pytest.raises(C.RecoveryRefused):
            C._validate_incident_contract(incident)


@pytest.fixture
def final_jobs(tmp_path, monkeypatch):
    """261 tiny metadata trees with real hashes, identities and 149 attestations."""
    monkeypatch.setattr(C.Plan, "WORKSPACE_ROOT", tmp_path)
    for name, folder in (("OUTPUT_ROOT", "output"), ("SYNC_ROOT", "sync"), ("STAGING_ROOT", "staging")):
        root = tmp_path / folder
        root.mkdir()
        monkeypatch.setattr(C.P, name, root)
    for name in ("staging", "quarantine"):
        (C.P.STAGING_ROOT / name).mkdir()
    jobs = list(C.Plan.new_exp2a_jobs())
    orphan = next(job for job in jobs if job.job_id == C.ORPHAN_JOB_ID)
    others = [job for job in jobs if job.job_id != C.ORPHAN_JOB_ID]
    old_jobs, new_jobs = others[:149] + [orphan], others[149:]
    old_ids = {job.job_id for job in old_jobs}
    checkpoints = {
        C.OLD_LEASE_TOKEN: ({"checkpoint_digest": "a" * 64, "execution_context_digest": "b" * 64}, "c" * 64),
        "d" * 32: ({"checkpoint_digest": "e" * 64, "execution_context_digest": "f" * 64}, "1" * 64),
    }
    events, started, pairs, durable_rows, local_rows = [], {}, [], [], []
    for job in old_jobs + new_jobs:
        local, durable = (root / "jobs" / job.job_id for root in (C.P.OUTPUT_ROOT, C.P.SYNC_ROOT))
        token = C.OLD_LEASE_TOKEN if job.job_id in old_ids else "d" * 32
        start = checkpoints[token][0]
        parent = C.OLD_LEASE_PID if token == C.OLD_LEASE_TOKEN else 777
        result = {"exp2a_repair_result_schema_version": 1, "job": job.as_record(),
            "expected_git_commit": C.EXECUTION_COMMIT, **start,
            "fit_evidence_digest": "2" * 64, "baseline_source": None}
        local.mkdir(parents=True)
        atomic_write_json(local / C.Supervisor.RESULT_FILE, result)
        attempt = {"job_id": job.job_id, "attempt_token": "3" * 32, "parent_pid": parent}
        atomic_write_json(local / C.Supervisor.ATTEMPT_FILE, attempt)
        receipt = {**attempt, "status": "success", "exit_code": 0, "published": True,
            "result_digest": C.sha256_bytes(C.Supervisor._canonical_json_bytes(result)),
            "job_tree_digest": C.Supervisor._job_tree_digest(local)}
        atomic_write_json(local / C.Supervisor.RECEIPT_FILE, receipt)
        durable.mkdir(parents=True)
        for file in local.iterdir():
            (durable / file.name).write_bytes(file.read_bytes())
        tree = C.B._job_tree_digest(local)
        current = C.B._copy_evidence_digest(local, durable)
        historical = C.sha256_bytes(("original:" + job.job_id).encode())
        preserved = job.job_id in old_ids and job.job_id != C.ORPHAN_JOB_ID
        sync = {"execution_digest": "2" * 64, "source_tree_digest": tree,
                "copy_evidence_digest": historical if preserved else current}
        events.append({"kind": "job_synced", "job_id": job.job_id, "data": sync})
        started[job.job_id] = token
        if job.job_id in old_ids:
            local_rows.append({"job_id": job.job_id, "tree_digest": tree})
        if preserved:
            policy = V.Pair(job.job_id, "D:/Aenv/pro/pro/output/jobs/" + job.job_id,
                "D:/Aenv/pro/pro/sync/jobs/" + job.job_id,
                local.relative_to(tmp_path).as_posix(), durable.relative_to(tmp_path).as_posix(),
                tree, historical)
            pairs.append(policy)
            durable_rows.append({"job_id": job.job_id, "tree_digest": tree,
                "tree_inventory_digest": C._tree_digest(C._plain_tree_inventory(local, what="fixture")),
                "execution_digest": "2" * 64, "copy_evidence_digest": current,
                "historical_copy_evidence_digest": historical, "relocation_pair_key": policy.key})
    doc = atomic_write_json(tmp_path / "original.json", {"synthetic": True})
    documents = (V.Document("original.json", C.sha256_file(doc)),)
    raw = V.build_record(tmp_path, tuple(pairs), documents)
    access = V.EvidenceAccess(raw, C.sha256_bytes(raw), tmp_path, tuple(pairs), documents)
    monkeypatch.setattr(C, "_relocation_state", lambda: (access, {}))
    incident = {"inventory": {"jobs": {"local_completed": local_rows, "durable_completed": durable_rows},
        "events": {"synced_job_ids": sorted(row["job_id"] for row in durable_rows)}}}
    return incident, events, started, checkpoints, {"lease_pid": 777}


def test_parent_final_jobs_prove_preserved_and_current_copies(final_jobs):
    actual = C._validate_final_job_trees(*final_jobs)
    assert actual["local_completed"] == actual["durable_completed"] == 261
    assert actual["old_completed_unchanged"] == 150


@pytest.mark.parametrize("damage", ["old_event_current_identity", "orphan_historical_identity", "new_historical_identity", "old_current_claim", "old_inventory_claim", "old_tree_changed", "new_result_context", "old_receipt_parent", "orphan_in_old_pairs"])
def test_parent_final_jobs_refuse_identity_or_epoch_substitution(final_jobs, damage):
    incident, events, started, checkpoints, lower = final_jobs
    old = incident["inventory"]["jobs"]["durable_completed"][0]
    old_id = old["job_id"]
    new_id = next(job_id for job_id, token in started.items() if token != C.OLD_LEASE_TOKEN)
    event_by_id = {row["job_id"]: row for row in events}
    if damage == "old_event_current_identity":
        event_by_id[old_id]["data"]["copy_evidence_digest"] = old["copy_evidence_digest"]
    elif damage in {"orphan_historical_identity", "new_historical_identity"}:
        job_id = C.ORPHAN_JOB_ID if damage.startswith("orphan") else new_id
        event_by_id[job_id]["data"]["copy_evidence_digest"] = old["historical_copy_evidence_digest"]
    elif damage == "old_current_claim": old["copy_evidence_digest"] = "0" * 64
    elif damage == "old_inventory_claim": old["tree_inventory_digest"] = "0" * 64
    elif damage == "orphan_in_old_pairs":
        old["job_id"] = C.ORPHAN_JOB_ID
        incident["inventory"]["events"]["synced_job_ids"] = sorted(row["job_id"] for row in incident["inventory"]["jobs"]["durable_completed"])
    else:
        job_id = new_id if damage == "new_result_context" else old_id
        filename = C.Supervisor.RECEIPT_FILE if damage == "old_receipt_parent" else C.Supervisor.RESULT_FILE
        path = C.P.OUTPUT_ROOT / "jobs" / job_id / filename
        row = C.read_json(path)
        if damage == "new_result_context": row["execution_context_digest"] = checkpoints[C.OLD_LEASE_TOKEN][0]["execution_context_digest"]
        elif damage == "old_receipt_parent": row["parent_pid"] = lower["lease_pid"]
        else: row["fit_evidence_digest"] = "0" * 64
        raw = X.L._pretty_json_bytes(row)
        path.write_bytes(raw)
        (C.P.SYNC_ROOT / "jobs" / job_id / filename).write_bytes(raw)
        if damage == "new_result_context":
            # Rebind the event to current bytes, so the epoch check is exercised.
            event_by_id[job_id]["data"].update(
                source_tree_digest=C.B._job_tree_digest(path.parent),
                copy_evidence_digest=C.B._copy_evidence_digest(path.parent, C.P.SYNC_ROOT / "jobs" / job_id))
    with pytest.raises(ValueError):
        C._validate_final_job_trees(*final_jobs)
