"""Real Windows hard-kill coverage for the D-161 publication window.

The subprocess and every artifact are confined to ``tmp_path``.  The child
patches only :mod:`bu.experiments.batch`'s ``shutil.copytree`` reference so it
can stop after copying eleven of fifteen synthetic files into the publisher's
real hidden ``.partial`` directory.  No production root, network, or GPU is
used.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from bu.experiments import week8_exp2a_recovery as recovery


pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="the D-161 liveness and hard-kill boundary is Windows-only"
)


_CHILD = r"""
import sys
import threading
from pathlib import Path

from bu.experiments import batch


source = Path(sys.argv[1])
target = Path(sys.argv[2])
marker = Path(sys.argv[3])


def copy_eleven_then_block(source_arg, destination_arg, *args, **kwargs):
    source_path = Path(source_arg)
    destination_path = Path(destination_arg)
    files = sorted(path for path in source_path.rglob("*") if path.is_file())
    if len(files) != 15:
        raise RuntimeError(f"expected 15 source files, found {len(files)}")
    for path in files[:11]:
        copied = destination_path / path.relative_to(source_path)
        copied.parent.mkdir(parents=True, exist_ok=True)
        copied.write_bytes(path.read_bytes())
    marker.write_text(str(destination_path.resolve()), encoding="utf-8")
    threading.Event().wait()


batch.shutil.copytree = copy_eleven_then_block
batch._publish_job_tree(source, target)
"""


def _wait_for_copy_marker(
    process: subprocess.Popen[str], marker: Path, *, timeout: float = 20.0
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if marker.is_file():
            return
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(
                "hard-kill child exited before publishing its marker\n"
                f"stdout:\n{stdout}\nstderr:\n{stderr}"
            )
        time.sleep(0.02)
    pytest.fail("timed out waiting for the hard-kill child copy marker")


def _stop_child(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_publish_job_tree_hard_kill_preserves_valid_hidden_partial(
    tmp_path: Path,
) -> None:
    case_root = tmp_path / "hard-kill-copy-window"
    source = case_root / "source"
    destination_parent = case_root / "durable" / "jobs"
    target = destination_parent / "synthetic-job"
    marker = case_root / "copied-eleven.marker"
    source.mkdir(parents=True)
    destination_parent.mkdir(parents=True)
    for index in range(15):
        payload = (f"synthetic-file-{index:02d}:" + "x" * (index + 1)).encode()
        (source / f"file-{index:02d}.bin").write_bytes(payload)

    source_root = Path(__file__).resolve().parents[1] / "src"
    child_environment = os.environ.copy()
    child_environment["PYTHONPATH"] = str(source_root)
    child_environment["PYTHONNOUSERSITE"] = "1"
    child_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    child_environment["CUDA_VISIBLE_DEVICES"] = "-1"
    child_environment["HIP_VISIBLE_DEVICES"] = "-1"

    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", _CHILD, str(source), str(target), str(marker)],
            cwd=case_root,
            env=child_environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _wait_for_copy_marker(process, marker)

        process.terminate()
        process.wait(timeout=10)

        assert not os.path.lexists(target)
        partials = sorted(destination_parent.glob(f".{target.name}.*.partial"))
        assert len(partials) == 1
        partial = partials[0]
        assert marker.read_text(encoding="utf-8") == str(partial.resolve())

        source_files = _file_bytes(source)
        partial_files = _file_bytes(partial)
        assert len(source_files) == 15
        assert len(partial_files) == 11
        assert partial_files.keys() <= source_files.keys()
        assert partial_files == {
            name: source_files[name] for name in partial_files
        }

        accounting = recovery._validate_partial_subset(source, partial)
        assert len(source_files) == recovery.EXPECTED_INITIAL_COUNTS[
            "orphan_local_files"
        ]
        assert accounting["file_count"] == recovery.EXPECTED_INITIAL_COUNTS[
            "partial_files"
        ]
        assert (len(source_files), accounting["file_count"]) == (15, 11)
    finally:
        if process is not None:
            _stop_child(process)
        shutil.rmtree(case_root, ignore_errors=True)
