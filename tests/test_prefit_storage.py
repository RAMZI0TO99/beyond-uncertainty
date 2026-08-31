"""Synthetic-only storage and exact adapter-body boundary tests.

This module never imports a launcher or the scientific package initializer.
Only the real proposed guard, stdlib-only durable primitives and selected AST
function bodies are loaded. All provenance/model/transport dependencies are
explicit local fakes. These are NOT integrated production-evidence tests.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROPOSED = Path(__file__).resolve().parents[1]
SCRATCH = PROPOSED.parent if PROPOSED.name == "proposed" else PROPOSED
SOURCE = PROPOSED / "src/bu/experiments"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# A deliberately separate package name prevents real bu imports/spawn hooks.
for name in ("_storage_proposal", "_storage_proposal.experiments"):
    package = types.ModuleType(name)
    package.__path__ = []
    sys.modules[name] = package
durable_source = PROPOSED / "src/bu/durable.py"
if not durable_source.exists():
    durable_source = SCRATCH / "reference/src/bu/durable.py"
_load("_storage_proposal.durable", durable_source)
S = _load("_storage_proposal.experiments.prefit_storage", SOURCE / "prefit_storage.py")


def _body(filename, name, namespace):
    tree = ast.parse((SOURCE / filename).read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    fragment = ast.Module(body=[ast.ImportFrom(module="__future__",
        names=[ast.alias(name="annotations")], level=0), node], type_ignores=[])
    exec(compile(ast.fix_missing_locations(fragment), str(SOURCE / filename), "exec"), namespace)
    return namespace[name]


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _seal(document):
    payload = {k: v for k, v in document.items() if k != "execution_context_digest"}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode()
    return {**payload, "execution_context_digest": _sha(raw)}


class StorageCases(unittest.TestCase):
    def setUp(self):
        # Applied-package use stays under the repository pytest cache; the
        # explicit package-isolated loader below/above remains unchanged.
        run_root = SCRATCH / ".pytest_cache" / "prefit-storage"
        run_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-", dir=run_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.roots = {name: self.root / name for name in ("preflight", "output", "staging", "sync")}
        for path in self.roots.values():
            path.mkdir()
        self.free = 100
        self.observations = []

        def usage(path):
            self.observations.append(Path(path))
            return types.SimpleNamespace(free=self.free)

        self.usage = self.enterContext(patch.object(S.shutil, "disk_usage", side_effect=usage))

    def preflight(self, *, baseline=False, minimum=80):
        self.document = {
            ("week7_preflight_schema_version" if baseline else "exp1_repair_preflight_schema_version"): 1,
            "status": "ready", "launch_performed": False,
            "storage": {"minimum_free_bytes": minimum, "roots": {
                name: {"path": str(path), "writable": True, "free_bytes": 1000}
                for name, path in self.roots.items()}},
        }
        self.source = self.roots["preflight"] / (
            "week7_preflight_report.json" if baseline else "week7_exp1_repair_preflight.json")
        self.publish()

    def publish(self):
        raw = json.dumps(self.document, sort_keys=True).encode()
        self.source.write_bytes(raw)
        self.pin = _sha(raw)

    def check(self):
        S.check_preflight_storage(self.source, self.pin, roots=self.roots)

    def sweep(self):
        roots = {k: str(v) for k, v in self.roots.items() if k != "preflight"}
        self.document = _seal({"sweep_repair_launch_schema_version": 1,
            "purpose": "exact_first_sweep_six_paired_repairs", "roots": roots,
            "minimum_free_bytes": 80, "environment": {"git_commit": "synthetic-not-executed"},
            "attempt_timeout_seconds": 30})
        self.source = self.roots["output"] / "week7_sweep_repair_context.json"
        self.publish()
        self.context_pin = self.document["execution_context_digest"]

    def check_sweep(self):
        S.check_sweep_context_storage(self.source, self.context_pin,
            roots={k: v for k, v in self.roots.items() if k != "preflight"})

    def test_each_preflight_kind_checks_every_root_and_equality_passes(self):
        for baseline in (False, True):
            with self.subTest(baseline=baseline):
                self.preflight(baseline=baseline)
                self.free = 80
                self.observations.clear()
                self.check()
                self.assertCountEqual(self.observations, self.roots.values())

    def test_current_low_free_not_old_snapshot_refuses(self):
        self.preflight()
        self.check()
        self.free = 79
        with self.assertRaisesRegex(ValueError, "before attempt_started"):
            self.check()

    def test_any_root_low_free_refuses(self):
        self.preflight()
        for root in self.roots.values():
            with self.subTest(root=root):
                self.usage.side_effect = lambda path: types.SimpleNamespace(free=79 if path == root else 100)
                with self.assertRaises(ValueError):
                    self.check()

    def test_unavailable_and_malformed_current_capacity_refuse(self):
        self.preflight()
        with patch.object(S.shutil, "disk_usage", side_effect=OSError("unmounted")):
            with self.assertRaisesRegex(ValueError, "cannot inspect"):
                self.check()
        for free in (True, False, None, "100", 100.0, -1):
            with self.subTest(free=free):
                self.free = free
                with self.assertRaises(ValueError):
                    self.check()

    def test_nonwritable_refuses(self):
        self.preflight()
        with patch.object(S.os, "access", return_value=False):
            with self.assertRaisesRegex(ValueError, "writable"):
                self.check()

    def test_malformed_source_minimum_refuses_before_capacity(self):
        for minimum in (True, False, -1, "80", 80.0, None):
            with self.subTest(minimum=minimum):
                self.preflight(minimum=minimum)
                self.usage.reset_mock()
                with self.assertRaises(ValueError):
                    self.check()
                self.usage.assert_not_called()

    def test_zero_floor_preserves_preflight_legacy_policy(self):
        self.preflight(minimum=0)
        self.free = 0
        self.check()

    def test_changed_even_resigned_preflight_cannot_lower_floor(self):
        self.preflight()
        original = self.pin
        self.document["storage"]["minimum_free_bytes"] = 0
        self.publish()
        self.pin = original
        with self.assertRaisesRegex(ValueError, "original launch pin"):
            self.check()

    def test_actual_root_drift_missing_extra_or_duplicate_source_root_refuses(self):
        for mutation in ("drift", "missing", "extra", "overlap"):
            with self.subTest(mutation=mutation):
                self.preflight()
                roots = dict(self.roots)
                if mutation == "drift":
                    roots["output"] = roots["sync"]
                elif mutation == "missing":
                    roots.pop("staging")
                elif mutation == "extra":
                    roots["extra"] = roots["sync"]
                else:
                    roots["output"] = roots["sync"]
                    self.document["storage"]["roots"]["output"]["path"] = str(roots["sync"])
                    self.publish()
                with self.assertRaises(ValueError):
                    S.check_preflight_storage(self.source, self.pin, roots=roots)

    def test_malformed_snapshots_refuse(self):
        for field, value in (("writable", 1), ("free_bytes", True), ("free_bytes", 1), ("path", 5)):
            with self.subTest(field=field, value=value):
                self.preflight()
                self.document["storage"]["roots"]["output"][field] = value
                self.publish()
                with self.assertRaises(ValueError):
                    self.check()

    def test_missing_file_root_and_non_directory_refuse(self):
        self.preflight()
        self.source.unlink()
        with self.assertRaises(ValueError):
            self.check()
        self.publish()
        self.roots["staging"].rmdir()
        with self.assertRaises(ValueError):
            self.check()
        self.roots["staging"].write_text("not a directory")
        with self.assertRaises(ValueError):
            self.check()

    def test_reparse_or_symlink_at_any_component_refuses_without_resolution(self):
        self.preflight()
        original = Path.lstat
        for target in (self.source, self.source.parent, self.root, self.roots["staging"]):
            for link in (False, True):
                with self.subTest(target=target, symlink=link):
                    def lstat(path, *args, **kwargs):
                        info = original(path, *args, **kwargs)
                        if path == target:
                            return types.SimpleNamespace(
                                st_mode=stat.S_IFLNK if link else info.st_mode,
                                st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
                        return info
                    with patch.object(Path, "lstat", lstat):
                        with self.assertRaisesRegex(ValueError, "link/reparse"):
                            self.check()

    def test_bad_digest_duplicate_json_and_schema_refuse(self):
        self.preflight()
        for pin in (None, "", "a" * 63, "A" * 64):
            with self.subTest(pin=pin):
                with self.assertRaises(ValueError):
                    S.check_preflight_storage(self.source, pin, roots=self.roots)
        raw = b'{"status":"ready","status":"ready"}'
        self.source.write_bytes(raw)
        with self.assertRaises(ValueError):
            S.check_preflight_storage(self.source, _sha(raw), roots=self.roots)
        self.document["exp1_repair_preflight_schema_version"] = True
        self.publish()
        with self.assertRaises(ValueError):
            self.check()

    def test_report_parent_and_canonical_root_spelling_are_bound(self):
        self.preflight()
        source = self.roots["output"] / self.source.name
        source.write_bytes(self.source.read_bytes())
        with self.assertRaisesRegex(ValueError, "preflight root"):
            S.check_preflight_storage(source, self.pin, roots=self.roots)
        self.document["storage"]["roots"]["output"]["path"] = str(self.roots["output"]) + "/../output"
        self.publish()
        with self.assertRaises(ValueError):
            self.check()

    def test_sweep_checks_all_three_roots_and_original_start_pin(self):
        self.sweep()
        self.check_sweep()
        self.assertCountEqual(self.observations, [v for k, v in self.roots.items() if k != "preflight"])
        self.document["minimum_free_bytes"] = 1
        self.document = _seal(self.document)
        self.publish()
        with self.assertRaisesRegex(ValueError, "unbound"):
            self.check_sweep()

    def test_sweep_corrupt_payload_own_digest_cannot_authorize(self):
        self.sweep()
        self.document["minimum_free_bytes"] = 1
        self.publish()  # Leave its own digest untouched; external start pin wins.
        with self.assertRaisesRegex(ValueError, "changed from its launch start"):
            self.check_sweep()

    def test_sweep_strict_positive_floor_and_root_binding(self):
        for floor in (0, -1, True, 80.0, "80"):
            with self.subTest(floor=floor):
                self.sweep()
                self.document["minimum_free_bytes"] = floor
                self.document = _seal(self.document)
                self.publish()
                self.context_pin = self.document["execution_context_digest"]
                with self.assertRaises(ValueError):
                    self.check_sweep()
        self.sweep()
        self.free = 79
        with self.assertRaisesRegex(ValueError, "before attempt_started"):
            self.check_sweep()

    def guard(self):
        return S.PreflightStorageGuard(self.source, self.pin, tuple(sorted(self.roots.items())))

    def test_guard_creation_does_not_check_capacity_and_engine_roots_are_bound(self):
        self.preflight(baseline=True)
        guard = self.guard()
        self.usage.assert_not_called()
        for output, staging in ((self.roots["sync"], self.roots["staging"]),
                                (self.roots["output"], self.roots["sync"]),
                                (self.roots["output"], None)):
            with self.subTest(output=output, staging=staging):
                with self.assertRaisesRegex(ValueError, "batch roots differ"):
                    guard.check(output_root=output, staging_root=staging)

    def e1_body(self):
        self.preflight()
        self.child = Mock()
        self.sequence = []
        validated = types.SimpleNamespace(roots=self.roots, report_path=self.source,
            report_sha256=self.pin, git_commit="synthetic-not-executed", report={"attempt_timeout_seconds": 30})

        def append(roots, start, events, *, kind, job_id, data):
            self.sequence.append(kind)
            events.append({"kind": kind, "job_id": job_id, "data": data})

        def child(*args, **kwargs):
            self.sequence.append("child")
            self.child(kwargs["job_id"])
            return types.SimpleNamespace(job_id=kwargs["job_id"], succeeded=True,
                canonical_dir=self.roots["output"] / "jobs" / kwargs["job_id"])

        namespace = {"os": os, "W": types.SimpleNamespace(_environment=lambda _: None, _fit_worker=object()),
            "_request": lambda *args: {}, "_sync_complete": lambda *args: {"synthetic": True},
            "_append_event": append, "run_isolated_attempt": child, "AttemptOutcome": types.SimpleNamespace,
            "check_preflight_storage": S.check_preflight_storage}
        body = _body("week7_exp1_repair_launch.py", "_run_one_job", namespace)
        return lambda job_id, events: body(types.SimpleNamespace(job_id=job_id), validated=validated,
            checkpoint_path=self.root / "unused-start.json", start={"checkpoint_digest": "synthetic"}, events=events)

    def test_e1_refuses_before_event_child_or_failed_attempt(self):
        run = self.e1_body()
        self.free = 79
        events = []
        with self.assertRaisesRegex(ValueError, "pre-fit storage"):
            run("synthetic-1", events)
        self.assertEqual(events, [])
        self.child.assert_not_called()

    def test_e1_refreshes_between_jobs_and_does_not_attempt_next(self):
        run = self.e1_body()
        events = []
        self.assertEqual(run("synthetic-1", events), "executed")
        self.assertEqual(self.sequence[:2], ["attempt_started", "child"])
        before = list(events)
        self.free = 79
        with self.assertRaises(ValueError):
            run("synthetic-2", events)
        self.assertEqual(events, before)
        self.child.assert_called_once_with("synthetic-1")

    def test_e1_complete_recovery_skips_new_guard_but_failed_attempt_stays_failed(self):
        run = self.e1_body()
        job = "synthetic-1"
        (self.roots["output"] / "jobs" / job).mkdir(parents=True)
        events = [{"kind": "attempt_started", "job_id": job, "data": {}}]
        self.source.unlink()  # New-child guard would refuse, but complete-fit branch is separate.
        self.free = 0
        self.assertEqual(run(job, events), "resumed")
        self.child.assert_not_called()
        self.usage.assert_not_called()
        with self.assertRaisesRegex(ValueError, "no automatic retry"):
            run("synthetic-2", [{"kind": "attempt_failed", "job_id": "synthetic-2"}])

    def sweep_body(self):
        self.sweep()
        context = self.document
        self.child = Mock()
        self.sequence = []
        start = {"lease": {"token": "synthetic"}, "start_digest": "synthetic",
                 "execution_context_digest": self.context_pin}

        def append(context, events, kind, job_id, data):
            self.sequence.append(kind)
            events.append({"kind": kind, "job_id": job_id, "data": data})

        def child(*args, **kwargs):
            self.child(kwargs["job_id"])
            self.sequence.append("child")
            return types.SimpleNamespace(job_id=kwargs["job_id"], succeeded=True, published=True,
                canonical_dir=self.roots["output"] / "jobs" / kwargs["job_id"])

        namespace = {"os": os, "CONTEXT_FILE": self.source.name,
            "_paths": lambda c: {k: Path(v) for k, v in c["roots"].items()},
            "_revalidate_context": Mock(), "_prior_attempts": Mock(),
            "W": types.SimpleNamespace(_lease_record=lambda _: None),
            "_sync": lambda *args, **kwargs: {"synthetic": True}, "_append": append,
            "_fit_worker": object(), "sha256_file": lambda _: "synthetic-never-executed",
            "AttemptOutcome": types.SimpleNamespace, "run_isolated_attempt": child,
            "check_sweep_context_storage": S.check_sweep_context_storage}
        body = _body("week7_sweep_repair_launch.py", "_run_one", namespace)
        run = lambda job_id, events: body(context, types.SimpleNamespace(job_id=job_id),
            self.root / "unused-start.json", start, events)
        return run, namespace

    def test_sweep_refresh_after_earlier_validation_and_before_attempt(self):
        run, namespace = self.sweep_body()
        namespace["_prior_attempts"].side_effect = lambda *args: setattr(self, "free", 79)
        events = []
        with self.assertRaisesRegex(ValueError, "pre-fit storage"):
            run("synthetic-1", events)
        namespace["_revalidate_context"].assert_called_once()
        self.assertEqual(events, [])
        self.child.assert_not_called()

    def test_sweep_refreshes_between_jobs(self):
        run, _ = self.sweep_body()
        events = []
        self.assertEqual(run("synthetic-1", events), "executed")
        self.assertEqual(self.sequence[:2], ["attempt_started", "child"])
        before = list(events)
        self.free = 79
        with self.assertRaises(ValueError):
            run("synthetic-2", events)
        self.assertEqual(events, before)
        self.child.assert_called_once_with("synthetic-1")

    def test_sweep_recovery_skips_new_guard_and_keeps_earlier_validation(self):
        run, namespace = self.sweep_body()
        job = "synthetic-1"
        (self.roots["output"] / "jobs" / job).mkdir(parents=True)
        events = [{"kind": "attempt_started", "job_id": job, "data": {"start_digest": "synthetic"}}]
        self.source.unlink()
        self.assertEqual(run(job, events), "resumed")
        self.assertEqual(namespace["_revalidate_context"].call_count, 2)
        self.usage.assert_not_called()
        self.child.assert_not_called()

    def batch_body(self, *, completed=False, prior_status=None):
        self.preflight(baseline=True)
        self.children = []
        self.transitions = []
        receipt = types.SimpleNamespace(as_record=lambda: {"synthetic": True})

        def append(path, latest, event):
            self.transitions.append(event)
            latest[event["job_id"]] = event

        def child(*args, **kwargs):
            self.children.append(kwargs["job_id"])
            job_dir = kwargs["root"] / "jobs" / kwargs["job_id"]
            job_dir.mkdir(parents=True)
            (job_dir / "job_result.json").write_text('{"synthetic": true}')
            self.free = 79  # Simulate first fit consuming the reserve; never actual disk fill.
            return types.SimpleNamespace(succeeded=True)

        namespace = {"Path": Path, "json": json, "PreflightStorageGuard": S.PreflightStorageGuard,
            "_manifest": lambda _: {"batch_id": "synthetic-batch"},
            "_write_json_exclusive": lambda *args: None, "MANIFEST_FILE": "manifest.json",
            "EVENTS_FILE": "events.jsonl", "RESULT_FILE": "job_result.json",
            "recover_unterminated_jsonl": lambda *args, **kwargs: None,
            "_events": lambda *args: ({"synthetic-1": {"status": "completed", "result_digest": "synthetic"}}
                                        if completed else {"synthetic-1": {"status": prior_status}}
                                        if prior_status else {}),
            "_recover_result": lambda *args, **kwargs: {"synthetic": True} if completed else None,
            "_result_digest": lambda _: "synthetic", "_append_transition": append,
            "_event": lambda job, status, **extra: {"job_id": job.job_id, "status": status, **extra},
            "_execute_in_spawned_child": object(), "run_isolated_attempt": child,
            "_validate_result": lambda job, result: result,
            "_validate_sync_receipt": lambda receipt, **kwargs: receipt,
            "BatchReport": lambda **kwargs: types.SimpleNamespace(**kwargs)}
        body = _body("batch.py", "_run_batch", namespace)
        def run(*, jobs=2, guard=True):
            return body(tuple(types.SimpleNamespace(job_id=f"synthetic-{i + 1}") for i in range(jobs)),
                root=self.roots["output"], sync=lambda *args: receipt,
                executor=lambda *args: None, require_fit_evidence=False,
                attempt_timeout_seconds=30, attempt_staging_root=self.roots["staging"],
                preflight_storage_guard=self.guard() if guard is True else guard)
        return run

    def test_baseline_batch_checks_each_child_and_refusal_is_batch_level(self):
        run = self.batch_body()
        with self.assertRaisesRegex(ValueError, "pre-fit storage"):
            run()
        self.assertEqual(self.children, ["synthetic-1"])
        self.assertEqual([row["status"] for row in self.transitions], ["started", "completed", "synced"])
        self.assertTrue(all(row["job_id"] == "synthetic-1" for row in self.transitions))

    def test_baseline_no_attempt_at_initial_refusal(self):
        run = self.batch_body()
        self.free = 79
        with self.assertRaises(ValueError):
            run()
        self.assertEqual(self.children, [])
        self.assertEqual(self.transitions, [])

    def test_baseline_complete_recovery_does_not_call_guard(self):
        run = self.batch_body(completed=True)
        self.source.unlink()
        result = run(jobs=1)
        self.assertEqual((result.executed, result.resumed, result.synced), (0, 1, 1))
        self.usage.assert_not_called()
        self.assertEqual(self.children, [])

    def test_baseline_low_space_does_not_reclassify_prior_attempt_or_retry(self):
        for status in ("started", "failed"):
            with self.subTest(status=status):
                run = self.batch_body(prior_status=status)
                self.free = 79
                with self.assertRaisesRegex(ValueError, "pre-fit storage"):
                    run(jobs=1)
                self.assertEqual(self.transitions, [])
                self.assertEqual(self.children, [])

    def test_legacy_batch_no_guard_keeps_existing_behavior(self):
        run = self.batch_body()
        self.free = 0
        result = run(guard=None)
        self.assertEqual((result.executed, result.synced), (2, 2))
        self.usage.assert_not_called()

    def test_batch_rejects_callback_duck_guard_and_subclass(self):
        run = self.batch_body()
        class Subclass(S.PreflightStorageGuard):
            pass
        for guard in (lambda: None, types.SimpleNamespace(check=lambda **kwargs: None),
                      Subclass(self.source, self.pin, tuple(sorted(self.roots.items())))):
            with self.subTest(guard=type(guard).__name__):
                with self.assertRaisesRegex(ValueError, "exact source-bound guard"):
                    run(guard=guard)
        self.assertEqual(self.children, [])

    def test_fixed_week7_adapter_binds_original_preflight_and_all_roots(self):
        self.preflight(baseline=True)
        job = types.SimpleNamespace(as_record=lambda: {"synthetic": True})
        validated = types.SimpleNamespace(report_path=self.source, report_sha256=self.pin,
            roots=self.roots, git_commit="synthetic-not-executed", jobs=(job,),
            report={"inputs": {"plan": {"path": "synthetic"}, "reuse_ledger": {"path": "synthetic"}},
                    "batch_key": "exp2a"})
        run_batch = Mock(return_value="not executed")
        namespace = {"PreflightStorageGuard": S.PreflightStorageGuard,
            "PF": types.SimpleNamespace(validate_week7_preflight=lambda *args, **kwargs: validated,
                _batch_jobs=lambda *args: (job,), _input_files=lambda *args: (None, {})),
            "B": types.SimpleNamespace(_run_batch=run_batch, sync_to_directory=lambda _: None,
                                       _default_executor=object())}
        body = _body("week7_launch.py", "_run_initial_batch", namespace)
        for key in ("exp2a", "sweep-001"):
            validated.report["batch_key"] = key
            self.assertEqual(body(validated, 30), "not executed")
            kwargs = run_batch.call_args.kwargs
            guard = kwargs["preflight_storage_guard"]
            self.assertIs(type(guard), S.PreflightStorageGuard)
            self.assertEqual(guard.source_sha256, self.pin)
            self.assertEqual(guard.source_path, self.source)
            self.assertEqual(dict(guard.roots), self.roots)
            self.assertIs(kwargs["require_fit_evidence"], True)
            self.assertEqual(kwargs["expected_git_commit"], validated.git_commit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
