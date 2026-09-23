"""Adversarial synthetic checks; never import or call a production entrypoint."""
import hashlib
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from bu.experiments import week8_relocation_provenance as R


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def evidence(tmp_path):
    for name in ("source", "copy"):
        (tmp_path/name).mkdir()
        (tmp_path/name/"file.bin").write_bytes(b"unchanged scientific bytes")
    (tmp_path/"original.json").write_bytes(b'{"frozen":true}')
    # Length is derived independently of the implementation under test.
    content = R.digest([{"path":"file.bin", "size":len(b"unchanged scientific bytes"), "sha256":sha(b"unchanged scientific bytes")}])
    pair = R.Pair("job-1", "D:/Aenv/pro/pro/old-source/job-1", "D:/Aenv/pro/pro/old-copy/job-1",
                  "source", "copy", content, "1"*64)
    doc = R.Document("original.json", sha((tmp_path/"original.json").read_bytes()))
    return tmp_path, (pair,), (doc,)


def test_accepts_content_identical_relocation_without_claiming_original_identity(evidence):
    root, pairs, docs = evidence
    original = (root/"original.json").read_bytes()
    raw = R.build_record(*evidence)
    record = R.verify_record(raw, sha(raw), *evidence)
    row = record["pairs"][0]
    assert row["policy"]["historical_copy_digest"] == "1"*64
    assert row["observed_copy_digest"] != "1"*64
    assert row["historical_identity_reproduced"] is False
    assert (root/"original.json").read_bytes() == original


@pytest.mark.parametrize("mutation", ["changed", "both_changed", "missing", "extra", "empty", "document"])
def test_rejects_corruption_and_inventory_changes(evidence, mutation):
    root, _, _ = evidence
    raw = R.build_record(*evidence)
    if mutation == "changed":
        (root/"copy/file.bin").write_bytes(b"corrupt")
    elif mutation == "both_changed":
        for side in ("source", "copy"):
            (root/side/"file.bin").write_bytes(b"same but unregistered")
    elif mutation == "missing":
        (root/"source/file.bin").unlink()
    elif mutation == "extra":
        (root/"copy/extra.bin").write_bytes(b"unexpected")
    elif mutation == "empty":
        (root/"source/empty").mkdir()
    else:
        (root/"original.json").write_bytes(b"different receipt")
    with pytest.raises(R.RelocationRefused):
        R.verify_record(raw, sha(raw), *evidence)


def test_rejects_same_byte_replacement_after_attestation(evidence):
    root, _, _ = evidence
    raw = R.build_record(*evidence)
    path = root/"copy/file.bin"
    saved = path.read_bytes()
    path.rename(root/"previous-file.bin")
    path.write_bytes(saved)
    with pytest.raises(R.RelocationRefused, match="current trusted observation"):
        R.verify_record(raw, sha(raw), *evidence)


def test_rejects_hardlinked_copy(evidence):
    root, _, _ = evidence
    (root/"copy/file.bin").unlink()
    os.link(root/"source/file.bin", root/"copy/file.bin")
    with pytest.raises(R.RelocationRefused, match="hardlinked"):
        R.build_record(*evidence)


def test_rejects_empty_directory_not_covered_by_historical_content_hash(evidence):
    (evidence[0]/"source/unregistered").mkdir()
    with pytest.raises(R.RelocationRefused, match="unregistered empty directory"):
        R.build_record(*evidence)


def test_rejects_symlink(evidence):
    root, _, _ = evidence
    (root/"copy/file.bin").unlink()
    try:
        (root/"copy/file.bin").symlink_to(root/"source/file.bin")
    except OSError as exc:
        pytest.skip(f"host cannot create symlinks: {exc}")
    with pytest.raises(R.RelocationRefused, match="linked"):
        R.build_record(*evidence)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction test")
def test_rejects_real_junction_in_evidence(evidence):
    root, _, _ = evidence
    junction = root/"source"/"junction"
    script = "New-Item -ItemType Junction -Path $env:WEEK8_TEST_LINK -Target $env:WEEK8_TEST_TARGET -ErrorAction Stop | Out-Null"
    # Paths travel as data, never interpolated into PowerShell code.
    result = subprocess.run([r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                    "-NoProfile", "-NonInteractive", "-Command", script,
                    ], capture_output=True, text=True,
                    env={**os.environ, "WEEK8_TEST_LINK":str(junction), "WEEK8_TEST_TARGET":str(root/"copy")})
    assert result.returncode == 0, result.stderr
    try:
        with pytest.raises(R.RelocationRefused, match="linked"):
            R.build_record(*evidence)
    finally:
        # Remove only the junction itself; never traverse or delete its target.
        os.rmdir(junction)
    assert (root/"copy/file.bin").read_bytes() == b"unchanged scientific bytes"


def test_rejects_file_exchange_before_open(evidence, monkeypatch):
    real = Path.open
    changed = False
    def exchange(path, *args, **kwargs):
        nonlocal changed
        if not changed and path == evidence[0]/"source/file.bin":
            changed = True
            saved = path.parent/"original.bin"
            path.rename(saved)
            with real(saved, "rb") as stream:
                data = stream.read()
            with real(path, "wb") as stream:
                stream.write(data)
        return real(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", exchange)
    with pytest.raises(R.RelocationRefused, match="before read"):
        R.build_record(*evidence)


@pytest.mark.parametrize("path", ["../outside", "/absolute", "C:/outside", "source/../copy",
                                 "source//child", "source\\child", "copy.", "NUL", "copy:stream"])
def test_rejects_noncanonical_or_escaping_paths(evidence, path):
    root, pairs, docs = evidence
    with pytest.raises(R.RelocationRefused):
        R.build_record(root, (replace(pairs[0], source=path),), docs)


def test_rejects_alias_and_overlapping_roots(evidence):
    root, pairs, docs = evidence
    for path in ("source", "SOURCE", "source/subtree"):
        with pytest.raises(R.RelocationRefused, match="overlapping"):
            R.build_record(root, (replace(pairs[0], copy=path),), docs)


def test_record_cannot_change_the_trusted_mapping_even_with_rehashed_bytes(evidence):
    root, pairs, docs = evidence
    raw = R.build_record(*evidence)
    record = json.loads(raw)
    record["pairs"][0]["policy"]["copy"] = "source"
    forged = R.canonical(record)
    with pytest.raises(R.RelocationRefused, match="current trusted observation"):
        R.verify_record(forged, sha(forged), *evidence)


def test_swapped_mapping_is_not_equivalent(evidence):
    root, pairs, docs = evidence
    raw = R.build_record(*evidence)
    pair = replace(pairs[0], source="copy", copy="source")
    with pytest.raises(R.RelocationRefused, match="current trusted observation"):
        R.verify_record(raw, sha(raw), root, (pair,), docs)


@pytest.mark.parametrize("alter", ["unknown", "duplicate", "whitespace", "incomplete", "wrong_pin"])
def test_rejects_malformed_or_unpinned_records(evidence, alter):
    raw = R.build_record(*evidence)
    if alter == "unknown":
        changed = dict(json.loads(raw), extra=True)
        raw = R.canonical(changed)
    elif alter == "duplicate":
        raw = b'{"schema_version":1,' + raw[1:]
    elif alter == "whitespace":
        raw += b"\n"
    elif alter == "incomplete":
        raw = raw[:-1]
    with pytest.raises(R.RelocationRefused):
        R.verify_record(raw, "0"*64 if alter=="wrong_pin" else sha(raw), *evidence)


def test_rejects_motion_between_observations(evidence, monkeypatch):
    real = R._observe
    count = 0
    def change_between(*args):
        nonlocal count
        result = real(*args)
        count += 1
        if count == 1:
            path = evidence[0]/"source/file.bin"
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns+1_000_000_000))
        return result
    monkeypatch.setattr(R, "_observe", change_between)
    with pytest.raises(R.RelocationRefused, match="between observations"):
        R.build_record(*evidence)


def test_rejects_motion_during_hash(evidence, monkeypatch):
    real = hashlib.file_digest
    def change_during(stream, algorithm):
        result = real(stream, algorithm)
        if Path(stream.name).name == "file.bin":
            with open(stream.name, "ab") as target:
                target.write(b"changed")
        return result
    monkeypatch.setattr(hashlib, "file_digest", change_during)
    with pytest.raises(R.RelocationRefused, match="during read"):
        R.build_record(*evidence)


def test_rejects_duplicate_pairs_or_logical_aliases(evidence):
    root, pairs, docs = evidence
    with pytest.raises(R.RelocationRefused, match="duplicate pair"):
        R.build_record(root, pairs+pairs, docs)
    with pytest.raises(R.RelocationRefused, match="overlapping"):
        R.build_record(root, (replace(pairs[0], logical_copy=pairs[0].logical_source),), docs)


def test_rejects_empty_policy(evidence):
    root, pairs, docs = evidence
    for p,d in [((), docs), (pairs, ())]:
        with pytest.raises(R.RelocationRefused, match="empty trusted policy"):
            R.build_record(root, p, d)


def access(evidence):
    raw = R.build_record(*evidence)
    return R.EvidenceAccess(raw, sha(raw), *evidence)


def test_access_keeps_original_document_bytes_and_returns_fresh_parsed_objects(evidence):
    root, _, _ = evidence
    view = access(evidence)
    file = view.historical_file(r"D:\Aenv\pro\pro\original.json")
    assert file.raw == b'{"frozen":true}'
    assert file.physical_path == root/"original.json"
    assert file.logical_path == r"D:\Aenv\pro\pro\original.json"
    assert file.sha256 == sha(file.raw)
    assert file.attestation_sha256 == view.attestation_sha256
    parsed = file.document()
    parsed["frozen"] = False
    assert file.document() == {"frozen":True}
    assert view.historical_file_at(root/"original.json").raw == file.raw


def test_access_pair_returns_old_claim_and_new_observation_separately(evidence):
    root, pairs, _ = evidence
    view = access(evidence)
    pair = view.historical_pair(pairs[0].logical_source, pairs[0].logical_copy)
    assert pair.source == root/"source" and pair.copy == root/"copy"
    assert pair.historical_copy_digest == "1"*64
    assert pair.observed_copy_digest != pair.historical_copy_digest
    assert pair == view.historical_pair_at(pair.source, pair.copy)
    file = view.historical_file(str(Path(pairs[0].logical_source)/"file.bin"))
    assert file.raw == b"unchanged scientific bytes"


def test_membership_cannot_be_changed_by_rewriting_or_removing_a_preserved_file(evidence):
    root,_,_ = evidence
    view = access(evidence)
    path = root/'original.json'
    assert view.has_historical_file(path)
    assert not view.has_historical_file(root/'unregistered.json')
    path.write_bytes(b'{"claimed_new_epoch":true}')
    assert view.has_historical_file(path)
    with pytest.raises(R.RelocationRefused):view.historical_file_at(path)
    path.unlink()
    assert view.has_historical_file(path)
    with pytest.raises(R.RelocationRefused):view.historical_file_at(path)
    with pytest.raises(R.RelocationRefused):view.has_historical_file(Path('relative.json'))


@pytest.mark.parametrize("which", ["unknown_logical", "unknown_physical", "wrong_root", "swapped", "unknown_pair"])
def test_access_has_no_discovery_or_fallback(evidence, which):
    root, pairs, _ = evidence
    view = access(evidence)
    (root/"unregistered.json").write_bytes(b'{"frozen":true}')
    with pytest.raises(R.RelocationRefused):
        if which == "unknown_logical":
            view.historical_file('D:/Aenv/pro/pro/unregistered.json')
        elif which == "unknown_physical":
            view.historical_file_at(root/"unregistered.json")
        elif which == "wrong_root":
            view.historical_file('C:/Aenv/pro/pro/original.json')
        elif which == "swapped":
            view.historical_pair_at(root/"copy", root/"source")
        else:
            view.historical_pair(pairs[0].logical_source, 'D:/Aenv/pro/pro/other')


@pytest.mark.parametrize("which", ["document", "evidence_file", "pair", "same_bytes_new_object"])
def test_access_rechecks_after_initial_verification(evidence, which):
    root, pairs, _ = evidence
    view = access(evidence)
    if which == "document":
        (root/"original.json").write_bytes(b'{"frozen":false}')
        call = lambda:view.historical_file_at(root/"original.json")
    else:
        path = root/"source/file.bin"
        if which == "same_bytes_new_object":
            path.rename(root/"old-file.bin")
            path.write_bytes(b"unchanged scientific bytes")
        else:
            path.write_bytes(b"changed")
        call = (lambda:view.historical_file_at(path)) if which == "evidence_file" else (
            lambda:view.historical_pair(pairs[0].logical_source, pairs[0].logical_copy))
    with pytest.raises(R.RelocationRefused):
        call()


def test_access_archive_document_has_exact_old_logical_binding(evidence):
    root, pairs, _ = evidence
    target = root/"project 2(ongoing)/lease.json"
    target.parent.mkdir()
    target.write_bytes(b'{"historical":true}')
    docs = (R.Document('project 2(ongoing)/lease.json',sha(target.read_bytes())),)
    view = access((root,pairs,docs))
    assert view.historical_file('D:/Aenv/pro/pro/lease.json').physical_path == target
    with pytest.raises(R.RelocationRefused):
        view.historical_file('D:/Aenv/pro/pro/project 2(ongoing)/lease.json')


def test_access_rejects_ambiguous_archived_document_mapping(evidence):
    root, pairs, docs = evidence
    archived = root/"project 2(ongoing)/original.json"
    archived.parent.mkdir()
    archived.write_bytes((root/"original.json").read_bytes())
    docs = docs+(R.Document('project 2(ongoing)/original.json',sha(archived.read_bytes())),)
    with pytest.raises(R.RelocationRefused, match="duplicate logical"):
        access((root,pairs,docs))


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'[]', b'not JSON'])
def test_historical_file_parser_rejects_ambiguous_json(raw):
    file = R.HistoricalFile('D:/Aenv/pro/pro/file.json',Path('file.json'),raw,sha(raw),'a'*64)
    with pytest.raises(R.RelocationRefused):
        file.document()
