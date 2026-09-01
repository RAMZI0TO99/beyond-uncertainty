"""Source-bound Week-8 adapter for the Experiment-2A family report.

The scientific report deliberately accepts explicit typed source inventories.
That low-level boundary is useful for testing, but production must not assemble
those inventories by hand or by discovering directories.  This adapter starts
from the independently SHA-pinned, source-rederived Week-8 label-finalization
manifest and the released execution checkpoint, constructs the exact typed
inventory, publishes one immutable report plus one independent byte copy, and
then reopens every authority once more.

No fit, label, sign-consistency result, or H2 verdict is created here.  The
adapter only removes operator discretion from the evidence-to-report bridge.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import Config
from ..durable import atomic_write_bytes, atomic_write_json, read_json, sha256_file
from . import experiment_2a_report as R
from . import fit_evidence as F
from . import launch as Launch
from . import week8_exp2a_label_finalization as Z
from . import week8_exp2a_repair_launch as X
from . import week8_exp2a_repairs as W
from . import week8_exp2a_sources as S


REPORTING_ADAPTER_SCHEMA_VERSION = 1
_RELEASED_ROW_FIELDS = {
    "job", "source_kind", "source_path", "copy_path",
    "expected_git_commit", "execution_digest", "sidecar_sha256",
    "source_tree_digest", "copy_tree_digest", "copy_evidence_digest",
    "independent_files",
}
_FINALIZED_ROW_FIELDS = {
    "fit_id", "expected_git_commit", "execution_digest",
    "source_tree_digest", "source_path", "copy_path",
    "original_copy_evidence_digest", "job", "relative_path",
    "independent_export_copy_digest",
}
_FIXED_AUTHORITY_ROOTS = (
    W.PROJECT_ROOT,
    W.COMMON_LEASE_ROOT,
    S.SMOKE_OUTPUT_ROOT,
    S.SMOKE_COPY_ROOT,
    S.WEEK7_OUTPUT_ROOT,
    S.WEEK7_COPY_ROOT,
    S.WEEK7_RECEIPT_ROOT,
)


@dataclass(frozen=True)
class Exp2AReportPublicationInputs:
    """External pins needed to cross the finalization/report boundary."""

    finalization_inputs: Z.Exp2AFinalizationInputs
    export_root: Path
    durable_copy_root: Path
    expected_finalization_manifest_sha256: str
    expected_reporting_commit: str


def _same(actual: object, expected: object, what: str) -> None:
    W._equal(actual, expected, what=what)


def _roots(inputs: Exp2AReportPublicationInputs) -> tuple[Path, Path]:
    if type(inputs) is not Exp2AReportPublicationInputs:
        raise ValueError("inputs must be exact Exp2AReportPublicationInputs")
    if type(inputs.finalization_inputs) is not Z.Exp2AFinalizationInputs:
        raise ValueError("finalization_inputs must be exact Exp2AFinalizationInputs")
    digest = Launch._lower_sha256(
        inputs.expected_finalization_manifest_sha256,
        what="independent finalization-manifest SHA256",
    )
    if digest != inputs.expected_finalization_manifest_sha256:
        raise ValueError("finalization-manifest SHA256 must be canonical lowercase hex")
    reporting_commit = F._validate_expected_git_commit(
        inputs.expected_reporting_commit
    )
    if reporting_commit != inputs.finalization_inputs.expected_finalizer_commit:
        raise ValueError(
            "reporting and label-finalizer commits must be the same clean revision"
        )
    export = R._project_path(
        inputs.export_root,
        what="Experiment-2A finalized export root",
        kind="directory",
        must_exist=True,
    )
    durable = R._project_path(
        inputs.durable_copy_root,
        what="Experiment-2A finalized durable-copy root",
        kind="directory",
        must_exist=True,
    )
    R._independent_pair(export, durable, what="Experiment-2A finalization roots")
    return export, durable


def _released_inventory(inputs: Exp2AReportPublicationInputs) -> dict[str, Any]:
    pins = inputs.finalization_inputs
    return X.load_released_exp2a_source_inventory(
        checkpoint_path=pins.checkpoint_path,
        checkpoint_sha256=pins.checkpoint_sha256,
        expected_execution_commit=pins.expected_execution_commit,
    )


def _released_record(value: dict[str, Any]) -> dict[str, Any]:
    """Convert the loader's trusted Path-valued roots to strict JSON."""

    roots = value.get("roots")
    if type(roots) is not dict:
        raise ValueError("released E2A inventory lacks explicit roots")
    return {
        **value,
        "roots": {name: str(path) for name, path in roots.items()},
    }


def _exact_released_rows(
    released: object,
) -> dict[str, dict[str, Any]]:
    if type(released) is not dict:
        raise ValueError("released E2A inventory must be an exact object")
    rows = released.get("sources")
    pending = released.get("pending_new_fit_ids")
    if type(rows) is not list or type(pending) is not list:
        raise ValueError("released E2A inventory lacks explicit sources/pending rows")
    if pending:
        raise ValueError("Experiment-2A reporting requires all 261 new fits released")
    jobs = {job.job_id: job for job in W.registered_exp2a_jobs()}
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if (
            type(row) is not dict
            or set(row) != _RELEASED_ROW_FIELDS
            or type(row.get("job")) is not dict
        ):
            raise ValueError("released E2A source row is malformed")
        job_id = row["job"].get("job_id")
        if job_id not in jobs or job_id in by_id:
            raise ValueError("released E2A source rows contain an unknown or duplicate fit")
        _same(row["job"], jobs[job_id].as_record(), "released report-source job")
        Launch._lower_sha256(
            row.get("execution_digest"), what="released execution digest"
        )
        F._validate_expected_git_commit(row.get("expected_git_commit"))
        if row["source_kind"] != W.source_kind(jobs[job_id]):
            raise ValueError("released E2A source kind differs from the registered job")
        if row["independent_files"] is not True:
            raise ValueError("released E2A source row lacks an independent physical copy")
        for field in (
            "sidecar_sha256",
            "source_tree_digest",
            "copy_tree_digest",
            "copy_evidence_digest",
        ):
            Launch._lower_sha256(row[field], what=f"released {field}")
        for field in ("source_path", "copy_path"):
            if type(row.get(field)) is not str:
                raise ValueError("released E2A source paths must be explicit strings")
        by_id[job_id] = row
    if set(by_id) != set(jobs) or len(by_id) != 416:
        raise ValueError("released E2A report inventory must contain exactly 416 fits")
    historical = {job.job_id for job in W.existing_exp2a_jobs()}
    new = {job.job_id for job in W.new_exp2a_jobs()}
    if len(set(by_id) & historical) != 155 or len(set(by_id) & new) != 261:
        raise ValueError("released E2A report inventory must partition 155 historical/261 new")
    return by_id


def _exact_finalized_rows(
    manifest: object,
    *,
    export: Path,
    durable: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if type(manifest) is not dict:
        raise ValueError("E2A finalization manifest must be an exact object")
    if manifest.get("status") != "complete":
        raise ValueError("E2A finalization must be complete before reporting")
    _same(
        manifest.get("roots"),
        {"export": str(export), "durable_copy": str(durable)},
        "report-bound finalization roots",
    )
    counts = manifest.get("counts")
    if type(counts) is not dict or any(
        counts.get(key) != value
        for key, value in {
            "registered_units": 20,
            "labelled_units": 20,
            "pending_units": 0,
            "blocked_units": 0,
            "label_required_fits": 384,
            "exported_fit_trees_per_root": 384,
            "pending_new_fits": 0,
            "historical_fits_required": 123,
            "non_label_historical_fits": 32,
            "verified_source_pairs": 384,
            "executed_fits": 0,
            "retrained_fits": 0,
        }.items()
    ):
        raise ValueError("E2A finalization counts are not the complete zero-compute inventory")
    if manifest.get("pending_new_fit_ids") != []:
        raise ValueError("E2A finalization retains pending label fits")
    units = manifest.get("units")
    if type(units) is not list or len(units) != 20:
        raise ValueError("E2A finalization must contain exactly twenty unit rows")
    registered_jobs = {job.job_id: job for job in W.label_required_exp2a_jobs()}
    unit_rows: dict[str, dict[str, Any]] = {}
    exported: dict[str, dict[str, Any]] = {}
    for unit_row in units:
        if type(unit_row) is not dict:
            raise ValueError("E2A finalization unit row is malformed")
        unit_id = unit_row.get("unit_id")
        if type(unit_id) is not str or unit_id in unit_rows:
            raise ValueError("E2A finalization has a malformed or duplicate unit")
        if (
            unit_row.get("status") != "labelled"
            or unit_row.get("reason") is not None
            or unit_row.get("missing_fit_ids") != []
            or unit_row.get("empty_failure_seeds") != []
        ):
            raise ValueError("every E2A report unit must have a completed nonempty label")
        Launch._lower_sha256(
            unit_row.get("label_file_sha256"), what="finalized label-file SHA256"
        )
        Launch._lower_sha256(
            unit_row.get("label_record_digest"), what="finalized label-record digest"
        )
        rows = unit_row.get("exported_sources")
        required = unit_row.get("required_fit_ids")
        if type(rows) is not list or type(required) is not list:
            raise ValueError("E2A finalization unit lacks explicit required/exported fits")
        if [row.get("fit_id") for row in rows if type(row) is dict] != required:
            raise ValueError("E2A finalization exported order differs from required fits")
        for row in rows:
            if type(row) is not dict or set(row) != _FINALIZED_ROW_FIELDS:
                raise ValueError("E2A finalized source row is malformed")
            fit_id = row.get("fit_id")
            if fit_id not in registered_jobs or fit_id in exported:
                raise ValueError("E2A finalization has an unknown or duplicate exported fit")
            job = registered_jobs[fit_id]
            if Config(unit=job.unit).unit_id != unit_id:
                raise ValueError("E2A finalized fit is attached to the wrong unit")
            _same(row.get("job"), job.as_record(), "finalized report-source job")
            if row.get("relative_path") != f"{Z.SOURCE_DIRECTORY}/{fit_id}":
                raise ValueError("E2A finalized fit has a noncanonical relative path")
            Launch._lower_sha256(
                row.get("execution_digest"), what="finalized execution digest"
            )
            for field in (
                "source_tree_digest",
                "original_copy_evidence_digest",
                "independent_export_copy_digest",
            ):
                Launch._lower_sha256(row[field], what=f"finalized {field}")
            F._validate_expected_git_commit(row.get("expected_git_commit"))
            exported[fit_id] = row
        unit_rows[unit_id] = unit_row
    registered_units = {Config(unit=unit).unit_id for unit in R._registered_units()}
    if set(unit_rows) != registered_units or set(exported) != set(registered_jobs):
        raise ValueError("E2A finalization does not cover the exact 20-unit/384-fit inventory")
    return unit_rows, exported


def _pair(
    row: dict[str, Any],
    *,
    source_path: Path,
    copy_path: Path,
) -> R.Experiment2AFitSourcePair:
    return R.Experiment2AFitSourcePair(
        source_path=source_path,
        copy_path=copy_path,
        expected_git_commit=row["expected_git_commit"],
        expected_execution_digest=row["execution_digest"],
    )


def _typed_sources(
    manifest: dict[str, Any],
    released: dict[str, Any],
    *,
    export: Path,
    durable: Path,
) -> tuple[
    tuple[R.Experiment2ABaselineSources, ...],
    tuple[R.RepairValidationLabelSource, ...],
    tuple[R.OrdinaryLabelSource, ...],
]:
    released_by_id = _exact_released_rows(released)
    unit_rows, exported_by_id = _exact_finalized_rows(
        manifest, export=export, durable=durable
    )
    for fit_id, row in exported_by_id.items():
        released_row = released_by_id[fit_id]
        expected = {
            "job": released_row["job"],
            "source_path": released_row["source_path"],
            "copy_path": released_row["copy_path"],
            "expected_git_commit": released_row["expected_git_commit"],
            "execution_digest": released_row["execution_digest"],
            "source_tree_digest": released_row["source_tree_digest"],
            "original_copy_evidence_digest": released_row["copy_evidence_digest"],
        }
        _same(
            {key: row[key] for key in expected},
            expected,
            "finalized/released report-source binding",
        )
    jobs = W.registered_exp2a_jobs()
    by_cell = {
        (Config(unit=job.unit).unit_id, job.arm, job.seed): job for job in jobs
    }
    if len(by_cell) != 416:
        raise ValueError("E2A report job-cell registry is not unique")

    def exported_pair(unit_id: str, job_id: str) -> R.Experiment2AFitSourcePair:
        row = exported_by_id[job_id]
        relative = Path(row["relative_path"])
        return _pair(
            row,
            source_path=export / unit_id / relative,
            copy_path=durable / unit_id / relative,
        )

    baselines: list[R.Experiment2ABaselineSources] = []
    validation: list[R.RepairValidationLabelSource] = []
    ordinary: list[R.OrdinaryLabelSource] = []
    for unit in R._registered_units():
        unit_id = Config(unit=unit).unit_id
        unit_row = unit_rows[unit_id]
        baseline_pairs: list[R.Experiment2AFitSourcePair] = []
        for seed in R._SEEDS:
            job = by_cell[(unit_id, "baseline", seed)]
            if job.job_id in exported_by_id:
                pair = exported_pair(unit_id, job.job_id)
            else:
                row = released_by_id[job.job_id]
                pair = _pair(
                    row,
                    source_path=Path(row["source_path"]),
                    copy_path=Path(row["copy_path"]),
                )
            baseline_pairs.append(pair)
        baselines.append(R.Experiment2ABaselineSources(unit, tuple(baseline_pairs)))

        seeds = tuple(unit_row.get("seeds", ()))
        expected_stage = (
            "repair_validation"
            if unit_id in R._validation_unit_ids()
            else "exp3_repairs"
        )
        expected_seeds = (
            tuple(range(1000, 1020))
            if expected_stage == "repair_validation"
            else tuple(range(1000, 1003))
        )
        if unit_row.get("label_stage") != expected_stage or seeds != expected_seeds:
            raise ValueError("E2A finalization label policy differs from the registered unit")
        conditions: list[R.Experiment2ARepairConditionSources] = []
        for seed in expected_seeds:
            arm_pairs: dict[str, R.Experiment2AFitSourcePair] = {}
            for arm in ("baseline", "data_repair", "feature_repair"):
                job = by_cell[(unit_id, arm, seed)]
                arm_pairs[arm] = exported_pair(unit_id, job.job_id)
            conditions.append(
                R.Experiment2ARepairConditionSources(
                    seed=seed,
                    baseline=arm_pairs["baseline"],
                    data_repair=arm_pairs["data_repair"],
                    feature_repair=arm_pairs["feature_repair"],
                )
            )
        label_path = export / unit_id / Z.LABEL_FILE
        label_copy = durable / unit_id / Z.LABEL_FILE
        label_sha = unit_row["label_file_sha256"]
        args = (
            unit,
            label_path,
            label_copy,
            label_sha,
            label_sha,
            tuple(conditions),
        )
        if expected_stage == "repair_validation":
            validation.append(R.RepairValidationLabelSource(*args))
        else:
            ordinary.append(R.OrdinaryLabelSource(*args))

    if (
        len(baselines) != 20
        or len(validation) != 4
        or len(ordinary) != 16
        or sum(len(item.sources) for item in baselines) != 100
        or sum(len(item.conditions) for item in validation + ordinary) != 128
        or 3 * sum(len(item.conditions) for item in validation + ordinary) != 384
    ):
        raise ValueError("typed E2A report inventory has drifted from 20/100/4/16/384")
    baseline_ids = {
        by_cell[(Config(unit=item.unit).unit_id, "baseline", seed)].job_id
        for item in baselines
        for seed in R._SEEDS
    }
    label_ids = set(exported_by_id)
    exported_baselines = baseline_ids & label_ids
    baseline_only = baseline_ids - label_ids
    historical = {job.job_id for job in W.existing_exp2a_jobs()}
    new = {job.job_id for job in W.new_exp2a_jobs()}
    if (
        len(exported_baselines) != 68
        or len(baseline_only) != 32
        or not baseline_only.issubset(historical)
        or len(label_ids & historical) != 123
        or len(label_ids & new) != 261
        or len(label_ids | baseline_ids) != 416
        or label_ids | baseline_ids != set(released_by_id)
    ):
        raise ValueError("E2A report sources violate the exact 68/32/123/261 union")
    return tuple(baselines), tuple(validation), tuple(ordinary)


def _source_paths(
    baselines: tuple[R.Experiment2ABaselineSources, ...],
    validation: tuple[R.RepairValidationLabelSource, ...],
    ordinary: tuple[R.OrdinaryLabelSource, ...],
) -> set[Path]:
    paths: set[Path] = set()
    for baseline in baselines:
        for pair in baseline.sources:
            paths.update((pair.source_path, pair.copy_path))
    for label in validation + ordinary:
        paths.update((label.source_path, label.copy_path))
        for condition in label.conditions:
            for pair in (condition.baseline, condition.data_repair, condition.feature_repair):
                paths.update((pair.source_path, pair.copy_path))
    return {Path(os.path.abspath(path)) for path in paths}


def _whole_authority_roots(
    inputs: Exp2AReportPublicationInputs,
    released: dict[str, Any],
    *,
    export: Path,
    durable: Path,
) -> set[Path]:
    """Protect complete evidence/control trees, not only individual fits."""

    root_rows = released.get("roots")
    if type(root_rows) is not dict or set(root_rows) != {"output", "staging", "sync"}:
        raise ValueError("released E2A inventory lacks its exact execution roots")
    start = released.get("start")
    if type(start) is not dict or type(start.get("preflight")) is not dict:
        raise ValueError("released E2A inventory lacks its checkpoint-bound preflight")
    preflight_path = start["preflight"].get("path")
    if type(preflight_path) is not str:
        raise ValueError("released E2A preflight path is malformed")
    roots = {export, durable}
    for name, value in root_rows.items():
        roots.add(
            R._project_path(
                Path(value),
                what=f"released E2A {name} root",
                kind="directory",
                must_exist=True,
            )
        )
    for value in _FIXED_AUTHORITY_ROOTS:
        roots.add(
            R._project_path(
                Path(value),
                what="fixed Experiment-2A authority root",
                kind="directory",
                must_exist=True,
            )
        )
    pins = inputs.finalization_inputs
    for value in (
        pins.plan_path,
        pins.source_ledger_path,
        pins.checkpoint_path,
        preflight_path,
    ):
        roots.add(
            R._project_path(
                Path(value).parent,
                what="Experiment-2A pinned-input parent",
                kind="directory",
                must_exist=True,
            )
        )
    return roots


def write_source_bound_exp2a_report(
    inputs: Exp2AReportPublicationInputs,
    *,
    report_path: Path,
    report_copy_path: Path,
    binding_receipt_path: Path,
) -> dict[str, Any]:
    """Publish and independently copy the exact source-derived E2A report."""

    export, durable = _roots(inputs)
    environment = Z._finalizer_environment(inputs.expected_reporting_commit)
    manifest = Z.load_exp2a_label_finalization(
        inputs.finalization_inputs,
        export_root=export,
        durable_copy_root=durable,
        expected_manifest_sha256=inputs.expected_finalization_manifest_sha256,
    )
    released = _released_inventory(inputs)
    baselines, validation, ordinary = _typed_sources(
        manifest, released, export=export, durable=durable
    )

    report = R._project_path(
        report_path,
        what="Experiment-2A production report",
        kind="file",
        must_exist=False,
    )
    copy = R._project_path(
        report_copy_path,
        what="Experiment-2A production report copy",
        kind="file",
        must_exist=False,
    )
    receipt = R._project_path(
        binding_receipt_path,
        what="Experiment-2A production report binding receipt",
        kind="file",
        must_exist=False,
    )
    R._independent_pair(report, copy, what="Experiment-2A report", inspect_filesystem=False)
    authorities = _source_paths(
        baselines, validation, ordinary
    ) | _whole_authority_roots(
        inputs, released, export=export, durable=durable
    ) | {
        Path(os.path.abspath(inputs.finalization_inputs.plan_path)),
        Path(os.path.abspath(inputs.finalization_inputs.source_ledger_path)),
        Path(os.path.abspath(inputs.finalization_inputs.checkpoint_path)),
    }
    if any(
        R._overlap(destination, authority)
        for destination in (report, copy, receipt)
        for authority in authorities
    ):
        raise ValueError("report, copy, and receipt must be disjoint from every authority")
    if any(
        R._overlap(left, right)
        for left, right in ((report, copy), (report, receipt), (copy, receipt))
    ):
        raise ValueError("report, independent copy, and receipt must be pairwise disjoint")

    written = R.write_experiment_2a_report(
        baselines,
        validation,
        ordinary,
        report_path=report,
    )
    digest = sha256_file(written)
    document = R.load_experiment_2a_report(written, expected_sha256=digest)
    atomic_write_bytes(copy, written.read_bytes())
    R._independent_pair(written, copy, what="Experiment-2A report")
    copied = R.load_experiment_2a_report(copy, expected_sha256=digest)
    _same(copied, document, "independently copied Experiment-2A report")

    # Reopen all lower authorities after publication.  This catches a source
    # mutation during a long report build instead of accepting a mixed view.
    after_manifest = Z.load_exp2a_label_finalization(
        inputs.finalization_inputs,
        export_root=export,
        durable_copy_root=durable,
        expected_manifest_sha256=inputs.expected_finalization_manifest_sha256,
    )
    after_released = _released_inventory(inputs)
    after_environment = Z._finalizer_environment(inputs.expected_reporting_commit)
    _same(after_manifest, manifest, "finalization manifest before/after reporting")
    _same(
        _released_record(after_released),
        _released_record(released),
        "released sources before/after reporting",
    )
    _same(after_environment, environment, "reporting environment before/after")
    if sha256_file(written) != digest or sha256_file(copy) != digest:
        raise ValueError("Experiment-2A report bytes changed during final read-back")
    pins = inputs.finalization_inputs
    receipt_document = W._seal({
        "week8_exp2a_reporting_adapter_schema_version": REPORTING_ADAPTER_SCHEMA_VERSION,
        "purpose": "bind_rederived_week8_exp2a_sources_to_descriptive_report",
        "status": "complete",
        "binding_receipt_path": str(receipt),
        "fits_executed": 0,
        "labels_created": 0,
        "sign_consistency_applied": False,
        "h2_verdict": None,
        "reporting_environment": environment,
        "upstream": {
            "plan": {"path": str(Path(pins.plan_path).resolve()), "sha256": pins.plan_sha256},
            "source_ledger": {
                "path": str(Path(pins.source_ledger_path).resolve()),
                "sha256": pins.source_ledger_sha256,
            },
            "checkpoint": {
                "path": str(Path(pins.checkpoint_path).resolve()),
                "sha256": pins.checkpoint_sha256,
            },
            "expected_execution_commit": pins.expected_execution_commit,
            "expected_finalizer_commit": pins.expected_finalizer_commit,
            "expected_reporting_commit": inputs.expected_reporting_commit,
            "finalization": {
                "export_manifest_path": str(export / Z.MANIFEST_FILE),
                "durable_manifest_path": str(durable / Z.MANIFEST_FILE),
                "sha256": inputs.expected_finalization_manifest_sha256,
                "manifest_digest": manifest["manifest_digest"],
            },
        },
        "report": {
            "path": str(written),
            "copy_path": str(copy),
            "sha256": digest,
            "payload_sha256": document["payload_sha256"],
            "source_inventory_sha256": document["source_manifests"][
                "source_inventory_sha256"
            ],
            "independent_copy": True,
        },
        "counts": {
            "released_fits": 416,
            "historical_fits": 155,
            "new_fits": 261,
            "label_required_fits": 384,
            "historical_label_fits": 123,
            "new_label_fits": 261,
            "baseline_diagnostic_fits": 100,
            "exported_label_baselines": 68,
            "historical_baseline_only_fits": 32,
            "union_fits": 416,
            "labelled_units": 20,
            "twenty_seed_labels": 4,
            "three_seed_labels": 16,
        },
    }, "receipt_digest")
    written_receipt = atomic_write_json(receipt, receipt_document)
    _same(read_json(written_receipt), receipt_document, "persisted E2A report receipt")
    if sha256_file(written) != digest or sha256_file(copy) != digest:
        raise ValueError("report bytes changed while publishing the binding receipt")
    return receipt_document
