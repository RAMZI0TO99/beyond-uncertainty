"""Worker admission has no bu imports or mutation capability before its claim."""
import copy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def worker():
    path = Path(__file__).resolve().parents[1] / "scripts/week8_exp2a_recovery_worker.py"
    spec = importlib.util.spec_from_file_location("relocation_worker_admission_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def admitted(worker, monkeypatch):
    raw = {"synthetic": "raw"}
    authority = {"preimport_authority_record": copy.deepcopy(raw)}
    raw_module = ModuleType(worker.RAW_AUTHORITY_MODULE_NAME)
    binding = {"helper_schema_version": 1, "synthetic": True}
    access = SimpleNamespace(attestation_sha256="a" * 64)
    calls = []
    metadata = SimpleNamespace(POLICY_SHA256="b" * 64, EXPECTED_PAIR_COUNT=304,
        EXPECTED_DOCUMENT_COUNT=629, load_registered_access=lambda verifier: access)
    def validate(value):
        assert value is raw
        calls.append("validate")
        return copy.deepcopy(binding)
    bundle = SimpleNamespace(modules={"metadata": metadata, "provenance": object()}, validate=validate)
    def load(value):
        assert value is raw
        calls.append("load")
        return bundle
    raw_module.load_verified_relocation_helpers = load
    monkeypatch.setitem(sys.modules, worker.RAW_AUTHORITY_MODULE_NAME, raw_module)
    monkeypatch.setattr(worker, "_validate_entrypoint_gate", lambda: {"raw_authority": raw})
    monkeypatch.setattr(worker, "_load_raw_authority_module", lambda: raw_module)
    return authority, raw_module, metadata, access, binding, calls


@pytest.mark.parametrize("failure", [None, "body", "helpers", "raw_module", "evidence"])
def test_worker_admission_restores_and_detects_drift(worker, admitted, monkeypatch, failure):
    authority, raw_module, metadata, access, binding, calls = admitted
    before = {name: module for name, module in sys.modules.items() if name == "bu" or name.startswith("bu.")}
    def run():
        with worker._worker_relocation_admission(authority):
            assert calls.count("load") == 1
            observed_metadata, observed_access, observed = worker._admitted_relocation()
            assert observed_metadata is metadata and observed_access is access
            assert observed == {"relocation_schema_version": 1, "attestation_sha256": "a" * 64,
                "policy_sha256": "b" * 64, "pair_count": 304, "document_count": 629, "helpers": binding}
            with pytest.raises(worker.BootstrapRefused, match="already active"):
                with worker._worker_relocation_admission(authority):
                    pytest.fail("nested admission accepted")
            if failure == "body": raise ValueError("synthetic body refusal")
            if failure == "helpers": binding["synthetic"] = False
            if failure == "raw_module": monkeypatch.setitem(sys.modules, worker.RAW_AUTHORITY_MODULE_NAME, ModuleType("replacement"))
            if failure == "evidence": access.attestation_sha256 = "f" * 64
    if failure is None: run()
    else:
        with pytest.raises(ValueError): run()
    assert worker._ACTIVE_RELOCATION is None
    assert calls.count("load") == 1
    assert {name: module for name, module in sys.modules.items() if name == "bu" or name.startswith("bu.")} == before
    with pytest.raises(worker.BootstrapRefused, match="not admitted"):
        worker._admitted_relocation()


def test_worker_refuses_authority_mismatch_before_helper_load(worker, admitted):
    authority, *_, calls = admitted
    authority["preimport_authority_record"]["synthetic"] = "different"
    with pytest.raises(worker.BootstrapRefused, match="differs from invocation"):
        with worker._worker_relocation_admission(authority):
            pytest.fail("mismatched admission accepted")
    assert calls == [] and worker._ACTIVE_RELOCATION is None


@pytest.mark.parametrize("refused", [False, True])
def test_worker_run_requires_admission_before_claim_body(worker, admitted, monkeypatch, refused):
    authority, _, metadata, _, _, calls = admitted
    invocation = {"authority": authority}
    monkeypatch.setattr(worker, "_load_authorized_invocation", lambda: (invocation, "c" * 64))
    body_calls = []
    def body(value, digest):
        assert value is invocation and digest == "c" * 64
        assert worker._admitted_relocation()[0] is metadata
        body_calls.append(True)
        return {"status": "synthetic complete"}
    monkeypatch.setattr(worker, "_run_authorized", body)
    if refused:
        def unavailable(verifier): raise ValueError("synthetic evidence refusal")
        metadata.load_registered_access = unavailable
        with pytest.raises(ValueError, match="evidence refusal"): worker._run()
        assert body_calls == []
    else:
        assert worker._run() == {"status": "synthetic complete"}
        assert body_calls == [True]
    assert calls.count("load") == 1 and worker._ACTIVE_RELOCATION is None
