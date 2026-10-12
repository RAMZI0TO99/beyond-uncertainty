"""Isolated synthetic tests for the new continuation archive tool only."""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

TOOL_PATH = Path(__file__).with_name("continuation.py")
spec = importlib.util.spec_from_file_location("synthetic_continuation_under_review", TOOL_PATH)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SyntheticBundle:
    def __init__(self, root, logical=None, raw_tar=None, mutate_gzip=None, split_at=13):
        self.repo = root
        self.destination = root.parent / "fresh-restored"
        (root / "continuation").mkdir(parents=True)
        self.logical = logical or [
            ("records/evidence.txt", b"synthetic-only\r\n\x00payload", 0o644),
            ("records/copy.txt", b"synthetic-only\r\n\x00payload", 0o600),
            ("records/empty.bin", b"", 0o644),
        ]
        rows = [{"path": name, "bytes": len(data), "sha256": sha(data), "mode": mode}
                for name, data, mode in self.logical]
        objects = {sha(data): data for _, data, _ in self.logical}
        if raw_tar is None:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for digest, data in objects.items():
                    member = tarfile.TarInfo("objects/" + digest)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            raw_tar = buffer.getvalue()
        packed = gzip.compress(raw_tar, mtime=0)
        if mutate_gzip:
            packed = mutate_gzip(packed)
        self.part_pins = []
        for index, start in enumerate(range(0, len(packed), split_at)):
            self.part_pins.append(self.put_pin("continuation/parts/part%03d" % index, packed[start:start + split_at]))
        self.index = {"schema_version": 1, "files": rows}
        index_pin = self.put_pin("continuation/index.json.gz",
                                 gzip.compress(json.dumps(self.index).encode(), mtime=0))
        self.group = {"name": "synthetic-test", "format": "content_addressed_tar_gzip_multipart_v1",
                      "parts": self.part_pins, "index": index_pin, "file_count": len(rows),
                      "distinct_object_count": len(objects), "raw_file_bytes": sum(row["bytes"] for row in rows)}
        self.manifest = {"schema_version": 1, "record_type": "portable_byte_preserving_continuation_snapshot",
                         "bundles": [self.group], "selected_file_count": len(rows),
                         "raw_file_bytes": self.group["raw_file_bytes"],
                         "original_workspace_root": "D:/synthetic-only",
                         "final_acceptance": {"path": rows[0]["path"], "bytes": rows[0]["bytes"],
                                              "sha256": rows[0]["sha256"]},
                         "link_overrides": [], "external_path_map": {}}
        self.canonical_data = b"synthetic canonical data; never imported"
        canonical_pin = self.put_pin("synthetic-canonical.txt", self.canonical_data)
        self.put_pin("continuation/canonical-source.json",
                     json.dumps({"schema_version": 1, "files": [canonical_pin]}).encode())
        self.save_manifest()

    def put_pin(self, relative, data):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"path": relative, "bytes": len(data), "sha256": sha(data)}

    def save_manifest(self):
        (self.repo / "continuation/manifest.json").write_text(json.dumps(self.manifest), encoding="utf8")

    def replace_index(self):
        self.group["index"] = self.put_pin("continuation/index.json.gz",
                                          gzip.compress(json.dumps(self.index).encode(), mtime=0))
        self.save_manifest()

    def set_directory_layout(self, values, count=None, padding=None):
        record = {"schema_version": 1, "directories": values}
        if padding is not None:
            record["padding"] = padding
        pin = self.put_pin("continuation/directories.json.gz",
                           gzip.compress(json.dumps(record).encode(), mtime=0))
        pin["directory_count"] = len(values) if count is None else count
        self.manifest["directory_layout"] = pin
        self.save_manifest()

    def run_cli(self, *arguments):
        with mock.patch.object(tool, "REPO", self.repo), \
                mock.patch("sys.argv", ["continuation.py", *arguments]), \
                contextlib.redirect_stdout(io.StringIO()):
            return tool.main()


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="continuation-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.bundle = SyntheticBundle(self.repo)
        self.patch = mock.patch.object(tool, "REPO", self.repo)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_complete_roundtrip_multipart_dedup_and_empty_file(self):
        self.bundle.run_cli("restore", "--destination", str(self.bundle.destination))
        for name, data, _ in self.bundle.logical:
            self.assertEqual((self.bundle.destination / name).read_bytes(), data)
        self.assertNotEqual((self.bundle.destination / "records/evidence.txt").stat().st_ino,
                            (self.bundle.destination / "records/copy.txt").stat().st_ino)
        receipt = json.loads((self.bundle.destination / "PORTABLE_RESTORE_RECEIPT.json").read_text())
        self.assertEqual(receipt["restored_files"], 3)
        self.assertFalse(receipt["project_code_executed"])
        self.assertFalse(receipt["runtime_or_case_authority_granted"])
        self.bundle.run_cli("verify", "--workspace", str(self.bundle.destination))

    def test_empty_directory_layout_roundtrip_and_missing_directory_refusal(self):
        values = ["records", "empty-stage", "empty-stage/nested"]
        self.bundle.set_directory_layout(values)
        self.bundle.run_cli("restore", "--destination", str(self.bundle.destination))
        for value in values:
            self.assertTrue((self.bundle.destination / value).is_dir())
        self.assertEqual(list((self.bundle.destination / "empty-stage/nested").iterdir()), [])
        self.bundle.run_cli("verify", "--workspace", str(self.bundle.destination))
        (self.bundle.destination / "empty-stage/nested").rmdir()
        with self.assertRaises(ValueError):
            self.bundle.run_cli("verify", "--workspace", str(self.bundle.destination))

    def test_directory_layout_path_collisions_and_marker_prefix_refused_before_restore(self):
        groups = tool.inputs(self.bundle.manifest)
        cases = [
            ["../escape"], ["/absolute"], ["name."], ["a//b"],
            ["empty", "EMPTY"], ["records/evidence.txt"],
            ["records/evidence.txt/child"], ["PORTABLE_RESTORE_RECEIPT.json"],
            ["portable_restore_receipt.json/subdir"],
        ]
        for values in cases:
            with self.subTest(values=values):
                self.bundle.set_directory_layout(values)
                with self.assertRaises(ValueError):
                    tool.directory_layout(self.bundle.manifest, groups)
                self.assertFalse(self.bundle.destination.exists())

    def test_directory_layout_typed_counts_pins_and_decompression_bound(self):
        groups = tool.inputs(self.bundle.manifest)
        for values, count in [("abc", 3), ({"empty": []}, 1), (["empty"], 2),
                              (["empty"], True), (["empty"], 200001)]:
            with self.subTest(values=values, count=count):
                self.bundle.set_directory_layout(values, count=count)
                with self.assertRaises(ValueError):
                    tool.directory_layout(self.bundle.manifest, groups)
        self.bundle.set_directory_layout(["empty"])
        self.bundle.manifest["directory_layout"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            tool.directory_layout(self.bundle.manifest, groups)
        self.bundle.set_directory_layout([], padding="x" * 1024)
        with mock.patch.object(tool, "MAX_INDEX_BYTES", 128):
            with self.assertRaises(ValueError):
                tool.directory_layout(self.bundle.manifest, groups)
        self.assertFalse(self.bundle.destination.exists())

    def test_zero_length_parts_read_does_not_consume_payload(self):
        paths = [self.repo / pin["path"] for pin in self.bundle.part_pins]
        with tool.PartsReader(paths) as reader:
            self.assertEqual(reader.readinto(bytearray()), 0)
            actual = io.BufferedReader(reader).read()
        self.assertEqual(actual, b"".join(path.read_bytes() for path in paths))

    def test_reader_close_releases_current_handle(self):
        path = self.repo / self.bundle.part_pins[0]["path"]
        reader = tool.PartsReader([path])
        self.assertGreater(reader.readinto(bytearray(1)), 0)
        held = reader.current
        reader.close()
        self.assertTrue(held.closed)

    def test_rejects_path_traversal_absolute_and_noncanonical_names(self):
        bad = ["../escape", "/absolute", "C:/absolute", "a/../b", "a//b",
               "a/./b", "a\\b", "a/name.", "a/name ", "."]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    tool.safe_relative(value)

    def test_rejects_windows_devices_and_illegal_name_characters(self):
        for value in ["CON", "dir/con.txt", "NUL.bin", "AUX", "COM1", "LPT9.log",
                      "dir/name?", "dir/name*", 'dir/name"', "dir/name|"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    tool.safe_relative(value)

    def test_duplicate_json_keys_refused(self):
        with self.assertRaises(ValueError):
            tool.decode(b'{"schema_version":1,"schema_version":1}')

    def test_casefold_duplicate_logical_path_refused(self):
        self.bundle.index["files"][1]["path"] = "RECORDS/EVIDENCE.TXT"
        self.bundle.replace_index()
        with self.assertRaises(ValueError):
            tool.inputs(self.bundle.manifest)

    def test_file_directory_prefix_collision_refused_before_restore(self):
        self.bundle.index["files"][0]["path"] = "node"
        self.bundle.index["files"][1]["path"] = "node/child"
        self.bundle.replace_index()
        with self.assertRaises(ValueError):
            tool.inputs(self.bundle.manifest)

    def test_wrong_manifest_raw_total_refused(self):
        self.bundle.manifest["raw_file_bytes"] = 0
        with self.assertRaises(ValueError):
            tool.inputs(self.bundle.manifest)

    def test_payload_sha_corruption_refused(self):
        pin = self.bundle.part_pins[0]
        path = self.repo / pin["path"]
        old = path.read_bytes()
        path.write_bytes(bytes([old[0] ^ 1]) + old[1:])
        with self.assertRaises(ValueError):
            tool.inputs(self.bundle.manifest)

    def test_snapshot_receipt_name_is_reserved_before_restore(self):
        self.bundle.index["files"][0]["path"] = "PORTABLE_RESTORE_RECEIPT.json"
        self.bundle.replace_index()
        with self.assertRaises(ValueError):
            tool.inputs(self.bundle.manifest)

    def test_same_object_cannot_have_two_declared_byte_lengths(self):
        self.bundle.index["files"][1]["bytes"] += 1
        self.bundle.group["raw_file_bytes"] += 1
        self.bundle.manifest["raw_file_bytes"] += 1
        self.bundle.replace_index()
        with self.assertRaises(ValueError):
            tool.inputs(self.bundle.manifest)

    def test_deduplicated_restore_uses_bounded_open_handles(self):
        rows = [("copies/f%03d.txt" % i, b"synthetic handle-bound data", 0o644) for i in range(80)]
        bundle = SyntheticBundle(self.base / "many-copies-repo", logical=rows)
        destination = self.base / "many-copies-restored"
        original_open = Path.open
        active = 0
        peak = 0

        class HeldFile:
            def __init__(self, handle):
                self.handle = handle
                self.closed_once = False
            def __getattr__(self, name):
                return getattr(self.handle, name)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
            def close(self):
                nonlocal active
                if not self.closed_once:
                    self.closed_once = True
                    active -= 1
                    self.handle.close()

        def tracking_open(path, *args, **kwargs):
            nonlocal active, peak
            handle = original_open(path, *args, **kwargs)
            active += 1
            peak = max(peak, active)
            return HeldFile(handle)

        with mock.patch.object(tool, "REPO", bundle.repo), mock.patch.object(Path, "open", tracking_open), \
                contextlib.redirect_stdout(io.StringIO()):
            tool.inspect_payloads(bundle.manifest, tool.inputs(bundle.manifest), destination)
        self.assertEqual(active, 0)
        self.assertLessEqual(peak, 4)
        for name, body, _ in rows:
            self.assertEqual((destination / name).read_bytes(), body)

    def test_canonical_source_corruption_refused(self):
        (self.repo / "synthetic-canonical.txt").write_bytes(b"corrupted")
        with self.assertRaises(ValueError):
            tool.verify_canonical()

    def test_decompressed_index_budget_is_enforced(self):
        self.bundle.index["padding"] = "x" * (2 * tool.CHUNK)
        self.bundle.replace_index()
        with self.assertRaises(ValueError):
            tool.inputs(self.bundle.manifest)

    def test_excessive_zero_tar_padding_is_refused(self):
        body = b"synthetic padding budget"
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            member = tarfile.TarInfo("objects/" + sha(body))
            member.size = len(body)
            archive.addfile(member, io.BytesIO(body))
        raw = buffer.getvalue() + b"\x00" * (2 * tool.TAR_BUFFER)
        bundle = SyntheticBundle(self.base / "padding-repo",
                                 logical=[("records/evidence.txt", body, 0o644)], raw_tar=raw)
        with mock.patch.object(tool, "REPO", bundle.repo), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                tool.inspect_payloads(bundle.manifest, tool.inputs(bundle.manifest))

    def test_simulated_reparse_destination_ancestor_refused(self):
        parent = self.base / "simulated-reparse-directory"
        parent.mkdir()
        destination = parent / "new"
        original_lstat = Path.lstat

        class ReparseStat:
            def __init__(self, actual):
                self.actual = actual
                self.st_file_attributes = getattr(actual, "st_file_attributes", 0) | 0x400
            def __getattr__(self, name):
                return getattr(self.actual, name)

        def fake_lstat(path, *args, **kwargs):
            actual = original_lstat(path, *args, **kwargs)
            normalized = str(path).removeprefix("\\\\?\\").casefold()
            return ReparseStat(actual) if normalized == str(parent).casefold() else actual

        with mock.patch.object(Path, "lstat", fake_lstat):
            with self.assertRaises(ValueError):
                self.bundle.run_cli("restore", "--destination", str(destination))
        self.assertFalse(destination.exists())

    def test_simulated_reparse_payload_ancestor_refused(self):
        parent = self.repo / "simulated-reparse-directory"
        parent.mkdir()
        path = parent / "data"
        path.write_bytes(b"synthetic")
        original_lstat = Path.lstat

        class ReparseStat:
            def __init__(self, actual):
                self.actual = actual
                self.st_file_attributes = getattr(actual, "st_file_attributes", 0) | 0x400
            def __getattr__(self, name):
                return getattr(self.actual, name)

        def fake_lstat(candidate, *args, **kwargs):
            actual = original_lstat(candidate, *args, **kwargs)
            normalized = str(candidate).removeprefix("\\\\?\\").casefold()
            return ReparseStat(actual) if normalized == str(parent).casefold() else actual

        with mock.patch.object(Path, "lstat", fake_lstat):
            with self.assertRaises(ValueError):
                tool.validate_pin({"path": "simulated-reparse-directory/data", "bytes": 9,
                                   "sha256": sha(b"synthetic")})

    def test_corrupt_gzip_crc_refused_even_with_updated_part_pins(self):
        def corrupt(packed):
            out = bytearray(packed)
            out[-8] ^= 1
            return bytes(out)
        b = SyntheticBundle(self.base / "crc-repo", mutate_gzip=corrupt)
        with mock.patch.object(tool, "REPO", b.repo), contextlib.redirect_stdout(io.StringIO()):
            groups = tool.inputs(b.manifest)
            with self.assertRaises((OSError, ValueError, EOFError, tarfile.TarError)):
                tool.inspect_payloads(b.manifest, groups)

    def test_wrong_object_bytes_refused(self):
        first = self.bundle.logical[0][1]
        digest = sha(first)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            member = tarfile.TarInfo("objects/" + digest)
            member.size = len(first)
            archive.addfile(member, io.BytesIO(b"x" * len(first)))
            empty = tarfile.TarInfo("objects/" + sha(b""))
            empty.size = 0
            archive.addfile(empty, io.BytesIO(b""))
        b = SyntheticBundle(self.base / "bad-object-repo", raw_tar=buffer.getvalue())
        with mock.patch.object(tool, "REPO", b.repo), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                tool.inspect_payloads(b.manifest, tool.inputs(b.manifest))

    def test_non_file_tar_member_refused(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            link = tarfile.TarInfo("objects/" + sha(self.bundle.logical[0][1]))
            link.type = tarfile.SYMTYPE
            link.linkname = "../../outside"
            archive.addfile(link)
        b = SyntheticBundle(self.base / "symlink-member-repo", raw_tar=buffer.getvalue())
        with mock.patch.object(tool, "REPO", b.repo), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                tool.inspect_payloads(b.manifest, tool.inputs(b.manifest))

    def test_hidden_nonzero_bytes_after_tar_end_marker_refused(self):
        body = b"synthetic"
        digest = sha(body)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            member = tarfile.TarInfo("objects/" + digest)
            member.size = len(body)
            archive.addfile(member, io.BytesIO(body))
        raw = buffer.getvalue()
        # A valid file header and padded payload, then two zero TAR blocks and
        # nonzero bytes inside TAR's first read-ahead record.
        crafted = raw[:1024] + b"\x00" * 1024 + b"not-zero-after-tar"
        crafted += b"\x00" * (10240 - len(crafted))
        b = SyntheticBundle(self.base / "trailing-repo",
                            logical=[("records/evidence.txt", body, 0o644)], raw_tar=crafted)
        with mock.patch.object(tool, "REPO", b.repo), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                tool.inspect_payloads(b.manifest, tool.inputs(b.manifest))

    def test_existing_destination_is_not_overwritten(self):
        destination = self.bundle.destination
        destination.mkdir()
        sentinel = destination / "keep.txt"
        sentinel.write_bytes(b"untouched")
        with self.assertRaises(ValueError):
            self.bundle.run_cli("restore", "--destination", str(destination))
        self.assertEqual(sentinel.read_bytes(), b"untouched")

    def test_symlinked_destination_parent_refused_without_external_write(self):
        outside = self.base / "outside"
        outside.mkdir()
        linked = self.base / "link"
        try:
            os.symlink(outside, linked, target_is_directory=True)
        except OSError as error:
            self.skipTest("OS lacks directory symlink privilege: " + type(error).__name__)
        destination = linked / "new"
        with self.assertRaises(ValueError):
            self.bundle.run_cli("restore", "--destination", str(destination))
        self.assertFalse((outside / "new").exists())

    def test_payload_ancestor_symlink_refused(self):
        outside = self.base / "outside-payloads"
        outside.mkdir()
        (outside / "data").write_bytes(b"payload")
        linked = self.repo / "linked"
        try:
            os.symlink(outside, linked, target_is_directory=True)
        except OSError as error:
            self.skipTest("OS lacks directory symlink privilege: " + type(error).__name__)
        pin = {"path": "linked/data", "bytes": 7, "sha256": sha(b"payload")}
        with self.assertRaises(ValueError):
            tool.validate_pin(pin)

    def test_relative_and_external_document_mapping_and_escape(self):
        manifest = dict(self.bundle.manifest)
        manifest["external_path_map"] = {"external/source.json": "D:/other/source.json"}
        manifest["link_overrides"] = [{"document": "docs/current.md", "literal_target": "WORK/proof.json",
                                       "workspace_relative_path": "WORK/proof.json"}]
        workspace = self.base / "workspace"
        self.assertEqual(tool.resolve_path(manifest, "D:/synthetic-only/records/evidence.txt", workspace),
                         workspace / "records/evidence.txt")
        self.assertEqual(tool.resolve_path(manifest, "D:/other/source.json", workspace),
                         workspace / "external/source.json")
        self.assertEqual(tool.resolve_path(manifest, "WORK/proof.json", workspace, "docs/current.md"),
                         workspace / "WORK/proof.json")
        with self.assertRaises(ValueError):
            tool.resolve_path(manifest, "../../outside", workspace, "docs/current.md")


if __name__ == "__main__":
    unittest.main(verbosity=2)

