"""Fixed zero-compute publication of the Week-8 first-sweep exclusion report.

This is an attempt-001 production wrapper around :mod:`week8_exclusion`.  It
has no caller-selected paths, source hashes, source commits, units, or source
inventories.  The caller must name the current clean reporting commit so the
derived publication is bound to its implementation revision.
Both independently retained Week-7 authorities are reopened through the
strict lower evidence boundary before and after publication.  The published
report is copied byte-for-byte to a disjoint project-evidence root, and a
separate receipt binds both historical authorities to both report files.

The module performs no experiment execution, source discovery, unit drawing,
or model training.  Its CLI emits operational status and SHA-256 values only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..config import Config, UnitSpec
from ..durable import (
    DurabilityError,
    atomic_write_bytes,
    atomic_write_json,
    read_json,
    sha256_file,
)
from ..runrecord import GitState, git_state
from . import week8_exclusion as Exclusion
from .ordinary_sweep_label_evidence import (
    ORDINARY_SWEEP_LABEL_EVIDENCE_FILE,
    PairedRepairSource,
    SweepBaselineSource,
    SweepRepairCondition,
)


PRODUCTION_SCHEMA_VERSION = 1
ATTEMPT = "2026-09-01-attempt-001"
WORKSPACE_ROOT = Path("D:/Aenv/pro2")
LABEL_ORIGINAL_ROOT = (
    WORKSPACE_ROOT / "week7-first-sweep-label-2026-08-31-attempt-001"
)
LABEL_COPY_ROOT = (
    WORKSPACE_ROOT
    / "week7-first-sweep-label-2026-08-31-attempt-001-project-evidence"
)
OUTPUT_ROOT = WORKSPACE_ROOT / f"week8-exclusion-{ATTEMPT}"
OUTPUT_COPY_ROOT = WORKSPACE_ROOT / f"week8-exclusion-{ATTEMPT}-project-evidence"

FINALIZATION_MANIFEST_FILE = "week7_first_sweep_label_finalization.json"
REPORT_FILE = Exclusion.WEEK8_SWEEP_EXCLUSION_FILE
BINDING_FILE = "week8_exclusion_source_binding.json"
EXPECTED_LABEL_SHA256 = (
    "bf96e423a9e41d811683b58adc9a51136210d4664c0a4cec040096f06217e9f6"
)
EXPECTED_FINALIZATION_MANIFEST_SHA256 = (
    "430839f3094bfb1ecaf18b1220ae43e0d7597b00627aff12c57863c3cdc19d26"
)
EXPECTED_LIBRARY_COMMIT = "1f302d1a05425827229e6ba3f41010a2b003c6f1"

FIRST_SWEEP_UNIT = UnitSpec(
    family="capacity",
    layout="uniform",
    causal_attribute="position",
    confound_rate=0.9,
    grid_size=8,
    n_objects=4,
    hidden_size=64,
    n_transitions=5000,
    withheld_features=(),
)

# (seed, baseline directory/digest, data directory/digest,
#  registered model-repair directory/digest).  The model repair for this unit
# is capacity_repair; SweepRepairCondition intentionally calls that role
# ``model_repair`` at its generic consumer boundary.
PINNED_CONDITIONS: tuple[
    tuple[int, str, str, str, str, str, str], ...
] = (
    (
        1000,
        "cc428cf4ab47-s1000",
        "bbcc6b899396b0b13c1bdcdd245b5e1294c6eb0e041f6c39a9391e91e6bbc058",
        "ps1-fc1c31138fefc72db77cf0493c96b22b",
        "0f67d61bc3a830110cf9515b89fb4ae6545b0a672c9164b1a14503c4647215bf",
        "ps1-db069456e35162c455609b715ab4e428",
        "f962a76ccd32b45b705272032e841097089f2af2f49c2dfc815af7126c545de7",
    ),
    (
        1001,
        "cc428cf4ab47-s1001",
        "13ff942999b29e8fda421d02c1f058f8370168c8ab953d183e8aeca627530001",
        "ps1-bf5ee529c893f49d406f7cb6bff0d78c",
        "326adcf28c888173deecc93ed555a29b3902f836c8265adcf06754848928c545",
        "ps1-e5911ef57fb3270c4dadfbeb4e2efa38",
        "72351cba77d04cc020d53a7f47a320b97c5a85d40654ede8a70629037d05f66e",
    ),
    (
        1002,
        "cc428cf4ab47-s1002",
        "2ffae16353627ab4b1759c761fdd322fdd783b99ff0e80fd52dcd2a72fa9afc3",
        "ps1-e4bd4947bccdebaeb78249a73523ae4a",
        "896bbbe95f86fed31124d663f7ef9957f103641c058526462cc92056bf142b11",
        "ps1-e40dafc6da0475aba28019483e300d73",
        "71b6f034916b0c8883e60691c216c75399cec1e6609e043797f7fe803152f462",
    ),
)

_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Week-8 exclusion production evidence must be strict JSON") from exc


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _commit(value: object) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None:
        raise ValueError(
            "expected_git_commit must be an exact lowercase 40-hex commit"
        )
    return value


def _require_current_clean_reporting_commit(expected_git_commit: object) -> str:
    """Bind zero-compute reporting to one current clean trustworthy commit."""

    expected = _commit(expected_git_commit)
    state = git_state()
    if type(state) is not GitState:
        raise ValueError("git_state returned a non-GitState reporting identity")
    if not state.trustworthy or state.commit != expected:
        raise ValueError(
            "current clean trustworthy reporting commit does not equal the "
            f"requested commit: current={state.commit!r}, dirty={state.dirty!r}"
        )
    return expected


def _seal(payload: Mapping[str, Any], field: str) -> dict[str, Any]:
    if type(payload) is not dict or field in payload:
        raise ValueError("receipt payload must be an exact unsealed dictionary")
    return {**payload, field: _digest(payload)}


def _is_reparse(info: os.stat_result) -> bool:
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(marker and getattr(info, "st_file_attributes", 0) & marker)


def _absolute(value: Path, *, what: str) -> Path:
    if not isinstance(value, Path) or not str(value).strip():
        raise ValueError(f"{what} must be a nonblank Path")
    try:
        candidate = Path(os.path.abspath(value))
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid {what}") from exc
    try:
        for item in (candidate, *candidate.parents):
            if not os.path.lexists(item):
                continue
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
                raise ValueError(f"{what} contains a link/reparse point: {item}")
            if item != candidate and not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"{what} has a non-directory parent: {item}")
    except OSError as exc:
        raise ValueError(f"cannot inspect {what}: {exc}") from exc
    return candidate


def _plain_directory(value: Path, *, what: str) -> Path:
    candidate = _absolute(value, what=what)
    if not os.path.lexists(candidate):
        raise ValueError(f"{what} is absent: {candidate}")
    try:
        info = candidate.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {what}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{what} must be a plain directory")
    return candidate


def _plain_file(value: Path, *, what: str) -> Path:
    candidate = _absolute(value, what=what)
    if not os.path.lexists(candidate):
        raise ValueError(f"{what} is absent: {candidate}")
    try:
        info = candidate.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {what}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{what} must be an independent regular file")
    return candidate


def _overlap(left: Path, right: Path) -> bool:
    first = Path(os.path.abspath(left))
    second = Path(os.path.abspath(right))
    return first == second or first in second.parents or second in first.parents


def _validate_fixed_layout() -> tuple[Path, Path, Path, Path, Path]:
    workspace = _plain_directory(WORKSPACE_ROOT, what="workspace root")
    original = _plain_directory(LABEL_ORIGINAL_ROOT, what="historical label root")
    copied = _plain_directory(LABEL_COPY_ROOT, what="historical label copy root")
    output = _absolute(OUTPUT_ROOT, what="Week-8 exclusion output root")
    output_copy = _absolute(
        OUTPUT_COPY_ROOT, what="Week-8 exclusion project-evidence root"
    )

    expected_names = {
        original: "week7-first-sweep-label-2026-08-31-attempt-001",
        copied: "week7-first-sweep-label-2026-08-31-attempt-001-project-evidence",
        output: "week8-exclusion-2026-09-01-attempt-001",
        output_copy: "week8-exclusion-2026-09-01-attempt-001-project-evidence",
    }
    if any(path.parent != workspace or path.name != name for path, name in expected_names.items()):
        raise ValueError("fixed attempt-001 roots differ from the registered workspace layout")
    roots = (original, copied, output, output_copy)
    for index, left in enumerate(roots):
        for right in roots[index + 1 :]:
            if _overlap(left, right):
                raise ValueError("historical and publication roots must be pairwise disjoint")
    for path in (output, output_copy):
        if os.path.lexists(path):
            raise ValueError(f"publication output root is preexisting: {path}")
    if (
        ATTEMPT != "2026-09-01-attempt-001"
        or EXPECTED_LIBRARY_COMMIT
        != "1f302d1a05425827229e6ba3f41010a2b003c6f1"
        or _HEX40.fullmatch(EXPECTED_LIBRARY_COMMIT) is None
        or _HEX64.fullmatch(EXPECTED_LABEL_SHA256) is None
        or _HEX64.fullmatch(EXPECTED_FINALIZATION_MANIFEST_SHA256) is None
        or Config(unit=FIRST_SWEEP_UNIT).unit_id
        != Exclusion.FIRST_SWEEP_BATCH_1_UNIT_ID
        or tuple(row[0] for row in PINNED_CONDITIONS) != (1000, 1001, 1002)
    ):
        raise ValueError("fixed Week-8 exclusion authority registry drifted")
    return workspace, original, copied, output, output_copy


def _conditions(root: Path) -> tuple[SweepRepairCondition, ...]:
    sources = _plain_directory(root / "sources", what="historical source root")
    result: list[SweepRepairCondition] = []
    seen: set[Path] = set()
    for (
        _seed,
        baseline_name,
        baseline_digest,
        data_name,
        data_digest,
        model_name,
        model_digest,
    ) in PINNED_CONDITIONS:
        paths = tuple(
            _plain_directory(sources / name, what=f"pinned historical source {name}")
            for name in (baseline_name, data_name, model_name)
        )
        if any(path.parent != sources for path in paths) or any(path in seen for path in paths):
            raise ValueError("pinned historical source paths are not exact and unique")
        seen.update(paths)
        result.append(
            SweepRepairCondition(
                SweepBaselineSource(
                    paths[0], EXPECTED_LIBRARY_COMMIT, baseline_digest
                ),
                PairedRepairSource(paths[1], EXPECTED_LIBRARY_COMMIT, data_digest),
                PairedRepairSource(paths[2], EXPECTED_LIBRARY_COMMIT, model_digest),
            )
        )
    if len(seen) != 9:
        raise ValueError("fixed Week-8 exclusion source inventory is not exactly nine fits")
    return tuple(result)


def _source(root: Path) -> Exclusion.SourceBoundSweepLabel:
    label = _plain_file(
        root / ORDINARY_SWEEP_LABEL_EVIDENCE_FILE,
        what="historical ordinary-sweep label",
    )
    return Exclusion.SourceBoundSweepLabel(
        path=label,
        unit=FIRST_SWEEP_UNIT,
        conditions=_conditions(root),
    )


def _manifest_inventory() -> set[tuple[int, str, str, str]]:
    expected: set[tuple[int, str, str, str]] = set()
    for seed, _base, base_sha, _data, data_sha, _model, model_sha in PINNED_CONDITIONS:
        expected.update(
            {
                (seed, "baseline", EXPECTED_LIBRARY_COMMIT, base_sha),
                (seed, "data_repair", EXPECTED_LIBRARY_COMMIT, data_sha),
                (seed, "capacity_repair", EXPECTED_LIBRARY_COMMIT, model_sha),
            }
        )
    return expected


def _load_manifest(root: Path) -> dict[str, Any]:
    path = _plain_file(
        root / FINALIZATION_MANIFEST_FILE,
        what="historical first-sweep finalization manifest",
    )
    before = sha256_file(path)
    if before != EXPECTED_FINALIZATION_MANIFEST_SHA256:
        raise ValueError("historical finalization manifest SHA256 differs from its pin")
    try:
        document = read_json(path)
    except DurabilityError as exc:
        raise ValueError("cannot read historical first-sweep finalization manifest") from exc
    after = sha256_file(path)
    if before != after:
        raise ValueError("historical finalization manifest changed while reopening it")
    if type(document) is not dict:
        raise ValueError("historical finalization manifest must be an exact JSON object")
    required = {
        "schema_version": 1,
        "artifact_type": "week7_first_sweep_label_completion",
        "status": "complete",
        "library_commit": EXPECTED_LIBRARY_COMMIT,
        "label_file": ORDINARY_SWEEP_LABEL_EVIDENCE_FILE,
        "label_sha256": EXPECTED_LABEL_SHA256,
        "unit_id": Exclusion.FIRST_SWEEP_BATCH_1_UNIT_ID,
        "physical_source_fits": 9,
        "seeds": [1000, 1001, 1002],
        "w8_exclusion_analysis_run": False,
    }
    if any(document.get(key) != value for key, value in required.items()):
        raise ValueError("historical finalization manifest differs from fixed authority fields")
    rows = document.get("sources")
    if type(rows) is not list or len(rows) != 9:
        raise ValueError("historical finalization manifest must name exactly nine sources")
    observed: set[tuple[int, str, str, str]] = set()
    for row in rows:
        if type(row) is not dict:
            raise ValueError("historical finalization source row must be an object")
        seed = row.get("seed")
        arm = row.get("arm")
        commit = row.get("expected_commit")
        digest = row.get("execution_digest")
        if (
            type(seed) is not int
            or type(arm) is not str
            or type(commit) is not str
            or type(digest) is not str
        ):
            raise ValueError("historical finalization source row has invalid pin types")
        observed.add((seed, arm, commit, digest))
    if len(observed) != 9 or observed != _manifest_inventory():
        raise ValueError("historical finalization source inventory differs from fixed pins")
    return document


def _validate_label(root: Path) -> Path:
    path = _plain_file(
        root / ORDINARY_SWEEP_LABEL_EVIDENCE_FILE,
        what="historical ordinary-sweep label",
    )
    before = sha256_file(path)
    if before != EXPECTED_LABEL_SHA256:
        raise ValueError("historical ordinary-sweep label SHA256 differs from its pin")
    if sha256_file(path) != before:
        raise ValueError("historical ordinary-sweep label changed while reopening it")
    return path


def _independent_equal(left: Path, right: Path, *, what: str) -> str:
    first = _plain_file(left, what=f"{what} original")
    second = _plain_file(right, what=f"{what} independent copy")
    try:
        if os.path.samefile(first, second):
            raise ValueError(f"{what} files are the same filesystem object")
    except OSError as exc:
        raise ValueError(f"cannot establish {what} file independence") from exc
    first_bytes = first.read_bytes()
    second_bytes = second.read_bytes()
    if first_bytes != second_bytes:
        raise ValueError(f"{what} original and independent copy bytes differ")
    first_sha = hashlib.sha256(first_bytes).hexdigest()
    if hashlib.sha256(second_bytes).hexdigest() != first_sha:
        raise ValueError(f"{what} independent digest check failed")
    return first_sha


def _normalised_report(value: object) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("lower exclusion boundary returned a non-object report")
    try:
        copied = json.loads(_canonical(value))
    except json.JSONDecodeError as exc:  # pragma: no cover - canonical JSON is valid
        raise ValueError("cannot detach lower exclusion report") from exc
    sources = copied.get("sources")
    if type(sources) is not list or len(sources) != 1 or type(sources[0]) is not dict:
        raise ValueError("lower exclusion report lacks its exact one-source inventory")
    sources[0]["label_path"] = "<independently-retained-label-authority>"
    copied.pop("source_inventory_sha256", None)
    copied.pop("report_digest", None)
    return copied


def _reopen_authorities(
    original_root: Path, copied_root: Path
) -> tuple[
    Exclusion.SourceBoundSweepLabel,
    Exclusion.SourceBoundSweepLabel,
    dict[str, Any],
    dict[str, Any],
]:
    original_label = _validate_label(original_root)
    copied_label = _validate_label(copied_root)
    _independent_equal(original_label, copied_label, what="historical label")
    original_manifest_path = original_root / FINALIZATION_MANIFEST_FILE
    copied_manifest_path = copied_root / FINALIZATION_MANIFEST_FILE
    original_manifest = _load_manifest(original_root)
    copied_manifest = _load_manifest(copied_root)
    _independent_equal(
        original_manifest_path,
        copied_manifest_path,
        what="historical finalization manifest",
    )
    if _canonical(original_manifest) != _canonical(copied_manifest):
        raise ValueError("historical finalization manifests differ after parsing")

    original_source = _source(original_root)
    copied_source = _source(copied_root)
    original_report = Exclusion.summarize_sweep_exclusion(
        (original_source,),
        expected_unit_ids=Exclusion.FIRST_SWEEP_BATCH_1_UNIT_IDS,
    )
    copied_report = Exclusion.summarize_sweep_exclusion(
        (copied_source,),
        expected_unit_ids=Exclusion.FIRST_SWEEP_BATCH_1_UNIT_IDS,
    )
    if _canonical(_normalised_report(original_report)) != _canonical(
        _normalised_report(copied_report)
    ):
        raise ValueError("independently retained label authorities derive different reports")
    return original_source, copied_source, original_report, copied_report


def _make_output_root(path: Path, *, what: str) -> Path:
    candidate = _absolute(path, what=what)
    if os.path.lexists(candidate):
        raise ValueError(f"{what} is preexisting")
    try:
        candidate.mkdir()
    except OSError as exc:
        raise ValueError(f"cannot create {what}: {exc}") from exc
    return _plain_directory(candidate, what=what)


def _source_pin(root: Path) -> dict[str, Any]:
    return {
        "root": str(root),
        "label": {
            "path": str(root / ORDINARY_SWEEP_LABEL_EVIDENCE_FILE),
            "sha256": EXPECTED_LABEL_SHA256,
        },
        "finalization_manifest": {
            "path": str(root / FINALIZATION_MANIFEST_FILE),
            "sha256": EXPECTED_FINALIZATION_MANIFEST_SHA256,
        },
        "expected_library_commit": EXPECTED_LIBRARY_COMMIT,
        "physical_source_fits": 9,
    }


def publish(*, expected_git_commit: str) -> dict[str, Any]:
    """Reopen both fixed authorities and publish the attempt-001 report once."""

    reporting_commit = _require_current_clean_reporting_commit(expected_git_commit)
    _, original_root, copied_root, output_root, output_copy_root = (
        _validate_fixed_layout()
    )
    original_source, _copied_source, before_original, before_copied = (
        _reopen_authorities(original_root, copied_root)
    )
    _require_current_clean_reporting_commit(reporting_commit)

    # Recheck nonexistence after the potentially long source verification.
    for path in (output_root, output_copy_root):
        _absolute(path, what="publication output root")
        if os.path.lexists(path):
            raise ValueError(f"publication output root became preexisting: {path}")
    local = _make_output_root(output_root, what="Week-8 exclusion output root")
    peer = _make_output_root(
        output_copy_root, what="Week-8 exclusion project-evidence root"
    )
    report_path = local / REPORT_FILE
    report_copy_path = peer / REPORT_FILE
    receipt_path = local / BINDING_FILE
    receipt_copy_path = peer / BINDING_FILE

    written = Exclusion.write_sweep_exclusion_report(
        (original_source,),
        expected_unit_ids=Exclusion.FIRST_SWEEP_BATCH_1_UNIT_IDS,
        path=report_path,
    )
    loaded = Exclusion.load_sweep_exclusion_report(
        report_path,
        labels=(original_source,),
        expected_unit_ids=Exclusion.FIRST_SWEEP_BATCH_1_UNIT_IDS,
    )
    if _canonical(written) != _canonical(loaded):
        raise ValueError("persisted exclusion report differs from lower-boundary reload")
    atomic_write_bytes(report_copy_path, _plain_file(report_path, what="report").read_bytes())
    report_sha = _independent_equal(report_path, report_copy_path, what="report")
    copied_loaded = Exclusion.load_sweep_exclusion_report(
        report_copy_path,
        labels=(original_source,),
        expected_unit_ids=Exclusion.FIRST_SWEEP_BATCH_1_UNIT_IDS,
    )
    if _canonical(copied_loaded) != _canonical(loaded):
        raise ValueError("independently copied exclusion report failed strict reload")

    _, _, after_original, after_copied = _reopen_authorities(
        original_root, copied_root
    )
    if any(
        _canonical(before) != _canonical(after)
        for before, after in (
            (before_original, after_original),
            (before_copied, after_copied),
        )
    ):
        raise ValueError("historical authority changed during exclusion publication")
    if sha256_file(report_path) != report_sha or sha256_file(report_copy_path) != report_sha:
        raise ValueError("report bytes changed before source-binding publication")

    receipt = _seal(
        {
            "week8_exclusion_production_schema_version": PRODUCTION_SCHEMA_VERSION,
            "purpose": "bind_fixed_first_sweep_authorities_to_zero_compute_exclusion_report",
            "status": "complete",
            "attempt": ATTEMPT,
            "unit_id": Exclusion.FIRST_SWEEP_BATCH_1_UNIT_ID,
            "reporting_git_commit": reporting_commit,
            "source_authorities": {
                "original": _source_pin(original_root),
                "independent_copy": _source_pin(copied_root),
                "source_inventory_sha256": _digest(PINNED_CONDITIONS),
                "derived_reports_match": True,
            },
            "publication": {
                "report_path": str(report_path),
                "report_copy_path": str(report_copy_path),
                "report_sha256": report_sha,
                "report_payload_sha256": loaded["report_digest"],
                "independent_copy": True,
            },
            "execution": {
                "physical_fits_executed": 0,
                "models_trained": 0,
                "new_labels_created": 0,
                "source_discovery_performed": False,
            },
        },
        "receipt_digest",
    )
    atomic_write_json(receipt_path, receipt)
    atomic_write_bytes(receipt_copy_path, receipt_path.read_bytes())
    receipt_sha = _independent_equal(
        receipt_path, receipt_copy_path, what="source-binding receipt"
    )
    persisted = read_json(receipt_path)
    if type(persisted) is not dict or persisted != receipt:
        raise ValueError("persisted source-binding receipt differs from sealed content")
    expected_receipt = _seal(
        {key: value for key, value in receipt.items() if key != "receipt_digest"},
        "receipt_digest",
    )
    if persisted != expected_receipt:
        raise ValueError("source-binding receipt digest is invalid")

    # Last read-back closes the source/report race window before success.
    _require_current_clean_reporting_commit(reporting_commit)
    _reopen_authorities(original_root, copied_root)
    if (
        _independent_equal(report_path, report_copy_path, what="report") != report_sha
        or _independent_equal(
            receipt_path, receipt_copy_path, what="source-binding receipt"
        )
        != receipt_sha
    ):
        raise ValueError("published Week-8 exclusion evidence changed on final read-back")
    return {
        "command": "publish",
        "status": "complete",
        "report_sha256": report_sha,
        "receipt_sha256": receipt_sha,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--expected-git-commit", required=True)
    return parser


def _operational_failure(command: str, exc: Exception) -> dict[str, str]:
    """Return a deterministic failure token without exposing exception text."""

    failure_type = type(exc).__name__
    return {
        "command": command,
        "status": "failed",
        "failure_type": failure_type,
        "failure_sha256": _digest(
            {
                "failure_type": failure_type,
                "failure_message": str(exc),
            }
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "publish":  # pragma: no cover - argparse owns choices
        raise ValueError("unknown Week-8 exclusion production command")
    try:
        result = publish(expected_git_commit=args.expected_git_commit)
    except Exception as exc:
        print(json.dumps(_operational_failure(args.command, exc), sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
