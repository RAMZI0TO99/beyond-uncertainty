"""Adversarial tests for the reusable crash-safe filesystem primitives."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from bu import durable


def _temps(directory: Path) -> list[Path]:
    return sorted(directory.glob(".*.tmp"))


def test_sha256_bytes_and_file_cover_exact_bytes(tmp_path: Path) -> None:
    payload = b"binary\x00evidence\xff"
    path = tmp_path / "artifact.bin"
    path.write_bytes(payload)

    expected = hashlib.sha256(payload).hexdigest()
    assert durable.sha256_bytes(payload) == expected
    assert durable.sha256_file(path) == expected


def test_sha256_bytes_refuses_bytes_like_substitutes() -> None:
    with pytest.raises(TypeError, match="exact bytes"):
        durable.sha256_bytes(bytearray(b"not exact bytes"))  # type: ignore[arg-type]


def test_atomic_bytes_publish_is_exact_and_leaves_no_temporary_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "nested" / "artifact.bin"

    returned = durable.atomic_write_bytes(target, b"first payload")

    assert returned == target.resolve()
    assert target.read_bytes() == b"first payload"
    assert _temps(target.parent) == []


def test_atomic_bytes_retry_with_exact_content_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "artifact.bin"
    durable.atomic_write_bytes(target, b"same")
    before = target.stat()

    durable.atomic_write_bytes(target, b"same")

    after = target.stat()
    assert target.read_bytes() == b"same"
    assert (after.st_ino, after.st_size) == (before.st_ino, before.st_size)
    assert _temps(tmp_path) == []


def test_atomic_bytes_never_overwrites_divergent_target(tmp_path: Path) -> None:
    target = tmp_path / "artifact.bin"
    durable.atomic_write_bytes(target, b"trusted")

    with pytest.raises(durable.DivergentTargetError, match="refusing overwrite"):
        durable.atomic_write_bytes(target, b"tampered replacement")

    assert target.read_bytes() == b"trusted"
    assert _temps(tmp_path) == []


def test_atomic_json_is_canonical_and_logically_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "evidence.json"
    durable.atomic_write_json(target, {"z": 1, "a": ["é", True]})

    expected = '{\n  "a": [\n    "é",\n    true\n  ],\n  "z": 1\n}\n'
    assert target.read_text(encoding="utf-8") == expected
    assert durable.read_json(target) == {"a": ["é", True], "z": 1}

    # Input mapping order does not change the canonical evidence bytes.
    durable.atomic_write_json(target, {"a": ["é", True], "z": 1})
    assert target.read_text(encoding="utf-8") == expected


def test_atomic_json_refuses_tampered_existing_bytes(tmp_path: Path) -> None:
    target = tmp_path / "evidence.json"
    durable.atomic_write_json(target, {"claim": "original"})
    target.write_text('{"claim":"forged"}\n', encoding="utf-8")

    with pytest.raises(durable.DivergentTargetError):
        durable.atomic_write_json(target, {"claim": "original"})

    assert target.read_text(encoding="utf-8") == '{"claim":"forged"}\n'


def test_atomic_json_idempotency_requires_exact_canonical_bytes(
    tmp_path: Path,
) -> None:
    target = tmp_path / "evidence.json"
    target.write_text('{"same":true}\n', encoding="utf-8")

    with pytest.raises(durable.DivergentTargetError):
        durable.atomic_write_json(target, {"same": True})

    assert target.read_text(encoding="utf-8") == '{"same":true}\n'


@pytest.mark.parametrize(
    "raw, message",
    [
        (b'{"a":', "not valid JSON"),
        (b'{"a":1,"a":2}', "duplicate JSON object key"),
        (b'{"a":NaN}', "non-finite JSON number"),
        (b'\xff', "not valid UTF-8"),
    ],
)
def test_read_json_fails_closed_on_ambiguous_content(
    tmp_path: Path, raw: bytes, message: str
) -> None:
    target = tmp_path / "bad.json"
    target.write_bytes(raw)

    with pytest.raises(durable.DurabilityError, match=message):
        durable.read_json(target)


def test_read_json_missing_file_has_contextual_fail_closed_error(
    tmp_path: Path,
) -> None:
    target = tmp_path / "missing.json"

    with pytest.raises(durable.DurabilityError, match="cannot read JSON document"):
        durable.read_json(target)


def test_atomic_json_refuses_non_finite_values_before_creating_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "bad.json"

    with pytest.raises(durable.DurabilityError, match="strict JSON"):
        durable.atomic_write_json(target, {"value": float("nan")})

    assert not target.exists()


def test_temporary_provider_cannot_escape_destination_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "destination"
    destination.mkdir()
    outside = tmp_path / "escaped.tmp"
    descriptor = os.open(outside, os.O_CREAT | os.O_EXCL | os.O_RDWR)

    def escaped_mkstemp(**_kwargs: object) -> tuple[int, str]:
        return descriptor, str(outside)

    monkeypatch.setattr(durable.tempfile, "mkstemp", escaped_mkstemp)

    with pytest.raises(durable.DurabilityError, match="escaped destination"):
        durable.atomic_write_bytes(destination / "artifact.bin", b"payload")

    assert not outside.exists()
    assert not (destination / "artifact.bin").exists()


def test_publish_error_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_link(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected publish failure")

    monkeypatch.setattr(durable.os, "link", fail_link)

    with pytest.raises(durable.DurabilityError, match="cannot atomically publish"):
        durable.atomic_write_bytes(tmp_path / "artifact.bin", b"payload")

    assert not (tmp_path / "artifact.bin").exists()
    assert _temps(tmp_path) == []


def test_immutable_publish_flushes_and_fsyncs_before_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(durable.os, "fsync", calls.append)

    durable.atomic_write_bytes(tmp_path / "artifact.bin", b"payload")

    assert len(calls) >= 1


def test_append_jsonl_writes_sorted_newline_committed_records(tmp_path: Path) -> None:
    journal = tmp_path / "events.jsonl"

    durable.append_jsonl(journal, {"z": 2, "a": 1})
    durable.append_jsonl(journal, {"event": "done"})

    assert journal.read_bytes() == b'{"a":1,"z":2}\n{"event":"done"}\n'
    assert durable.read_jsonl(journal) == [
        {"a": 1, "z": 2},
        {"event": "done"},
    ]


def test_append_flushes_and_fsyncs_each_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(durable.os, "fsync", calls.append)

    durable.append_jsonl(tmp_path / "events.jsonl", {"event": "durable"})

    assert len(calls) >= 1


@pytest.mark.parametrize(
    "tail",
    [b'{"event":', b'{"event":"complete"}', b"\xff"],
)
def test_jsonl_reader_ignores_only_unterminated_final_fragment(
    tmp_path: Path, tail: bytes
) -> None:
    journal = tmp_path / "events.jsonl"
    journal.write_bytes(b'{"event":"committed"}\n' + tail)

    assert durable.read_jsonl(journal) == [{"event": "committed"}]


def test_jsonl_reader_refuses_malformed_newline_terminated_final_line(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "events.jsonl"
    journal.write_bytes(b'{"event":"good"}\n{"event":}\n')

    with pytest.raises(durable.DurabilityError, match="line 2.*not valid JSON"):
        durable.read_jsonl(journal)


def test_jsonl_reader_refuses_earlier_corruption_even_with_torn_tail(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "events.jsonl"
    journal.write_bytes(b'{"event":}\n{"torn":')

    with pytest.raises(durable.DurabilityError, match="line 1.*not valid JSON"):
        durable.read_jsonl(journal)


@pytest.mark.parametrize("bad_line", [b"[]\n", b"null\n", b"\n"])
def test_jsonl_reader_requires_an_object_on_every_committed_line(
    tmp_path: Path, bad_line: bytes
) -> None:
    journal = tmp_path / "events.jsonl"
    journal.write_bytes(bad_line)

    with pytest.raises(durable.DurabilityError, match="line 1"):
        durable.read_jsonl(journal)


def test_jsonl_reader_refuses_duplicate_keys_and_non_finite_values(
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "duplicate.jsonl"
    duplicate.write_bytes(b'{"a":1,"a":2}\n')
    with pytest.raises(durable.DurabilityError, match="duplicate JSON object key"):
        durable.read_jsonl(duplicate)

    non_finite = tmp_path / "non-finite.jsonl"
    non_finite.write_bytes(b'{"a":Infinity}\n')
    with pytest.raises(durable.DurabilityError, match="non-finite JSON number"):
        durable.read_jsonl(non_finite)


def test_append_refuses_torn_tail_without_modifying_it(tmp_path: Path) -> None:
    journal = tmp_path / "events.jsonl"
    original = b'{"event":"committed"}\n{"event":'
    journal.write_bytes(original)

    with pytest.raises(durable.DurabilityError, match="unterminated final record"):
        durable.append_jsonl(journal, {"event": "must-not-append"})

    assert journal.read_bytes() == original


def test_append_refuses_non_object_or_non_finite_record_without_writing(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "events.jsonl"
    with pytest.raises(TypeError, match="mapping"):
        durable.append_jsonl(journal, [1, 2])  # type: ignore[arg-type]
    with pytest.raises(durable.DurabilityError, match="strict JSON"):
        durable.append_jsonl(journal, {"value": float("inf")})
    assert not journal.exists()


def test_empty_jsonl_is_a_valid_empty_journal(tmp_path: Path) -> None:
    journal = tmp_path / "events.jsonl"
    journal.write_bytes(b"")
    assert durable.read_jsonl(journal) == []


def test_torn_jsonl_tail_is_preserved_before_resume(tmp_path: Path) -> None:
    journal = tmp_path / "events.jsonl"
    fragment = b'{"event":"uncommitted"'
    journal.write_bytes(b'{"event":"committed"}\n' + fragment)

    preserved = durable.recover_unterminated_jsonl(
        journal, evidence_dir=tmp_path / "recovery"
    )

    assert preserved is not None
    assert preserved.read_bytes() == fragment
    assert durable.read_jsonl(journal) == [{"event": "committed"}]
    durable.append_jsonl(journal, {"event": "resumed"})
    assert durable.read_jsonl(journal)[-1] == {"event": "resumed"}
    assert (
        durable.recover_unterminated_jsonl(
            journal, evidence_dir=tmp_path / "recovery"
        )
        is None
    )
