"""D-154: one source-bound Week-7 report, artifact-only Week-10 replay.

``write_experiment_1_report`` accepts only 150 explicit source directories, an
expected FIT commit, and the separately verified clean ANALYSIS commit. It never
trains. Repeat generation is verification, not another independent analysis.

``replay_experiment_1_report`` reads exactly one report and requires an externally
retained SHA-256. It never opens the source paths, calls a loader, computes rank
correlations, or enumerates bootstrap resamples. It checks stored support,
percentiles, decisions and provenance for internal consistency. The external
digest authenticates the calculations; replay cannot authenticate an entirely
fabricated report accompanied by a replacement 'trusted' digest. Independent
source/computation auditing is a separate, explicitly authorised verification.

There is no CLI, implicit discovery, automatic figure integration, caller-row
input, or claim of external Sol certification. All output is project-local.
"""

from __future__ import annotations

import json
import math
import re
import stat
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import numpy as np

from .. import durable as D
from .. import constants as K
from ..config import Config, UnitSpec
from ..runrecord import GitState, git_state
from ..stats.trend import TrendResult, trend_test
from ..streams import comparison_group_id
from .experiment_1_evidence import Experiment1Evidence, load_experiment_1_evidence


REPORT_SCHEMA_VERSION = 1
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_AMENDMENT_PATH = Path(__file__).resolve().parents[3] / "docs" / "week7_scientific_amendment.md"
AMENDMENT_SHA256 = "4a856c65b4a0ae2f7b609d6dbf88f97e0489931498c26c165bd38b769a1e1707"
_SCALE_DOMAIN, _SCALE_SOURCE = "movement", "evaluation_pool"
_SEEDS = (1000, 1001, 1002, 1003, 1004)
_SIZES = (100, 250, 500, 1000, 2500, 5000)
_PAIRS = (
    ("shape", "uniform"), ("shape", "clustered"), ("shape", "sparse"),
    ("colour", "uniform"), ("colour", "clustered"),
)
_METRICS = ("disagreement", "error")
_RULE = {
    "statistic": "Spearman rho of the equal-seed mean six-size curve",
    "point_estimand": "equal-seed mean of equal-movement-row, normalised whole-pool means",
    "bootstrap": "exact_paired_seed_block",
    "n_resamples": 3125,
    "confidence_level": 0.95,
    "quantile_method": "linear",
    "direction": "negative",
    "strict_upper_bound_below": 0.0,
    "interval_scope": "pointwise, not simultaneous; enumeration is not exact coverage",
    "configuration_pooling": False,
    "error_is_diagnostic_only": True,
}
_DISCLOSURE = {
    "amendment_id": "D-154",
    "amendment_document": "docs/week7_scientific_amendment.md",
    "decision_owner": "Sol2 under explicit project-owner authority",
    "external_sol_certification": "pending",
    "registration_status": "post-collection, partially exposed amendment",
    "fully_blinded_pre_data_registration": False,
    "prior_knowledge": (
        "Development/calibration evidence and D-149 smoke label were known; all "
        "150 Experiment-1 fits existed. D-150 records the agent seeing two raw "
        "confirmatory per-fit summaries during collection, with no reported adaptation."
    ),
    "known_exposed_fit_ids": ["daaba764439a-s1004", "00608aa75f91-s1000"],
    "new_outcomes_opened_to_choose_amendment": False,
    "scope": (
        "Operational Experiment-1 trend only; does not establish model adequacy "
        "or repair-derived class membership. Pending repairs are not failed "
        "repairs, undiagnosed labels, or exclusion counts."
    ),
    "discreteness": (
        "A zero-width percentile interval reflects quantile discreteness, not "
        "zero sampling uncertainty. Support/masses accompany every interval."
    ),
    "no_adaptation": "No new seeds, preferred subset, smoothing, estimator change, or outcome-tuned repair/design choices.",
}
_TIMING = {
    "coefficient_analysis": "Week 7, one source-bound report",
    "week10": "Review this same immutable artifact; no retesting or new seeds",
    "regeneration": "Verification only, not independent replication",
    "full_h1_and_gate2": "Week-10 interpretation remains open, informed by scheduled repair validation; dates unchanged",
}
_STATUS_REASON = {
    "negative": "the whole interval lies below zero",
    "reversed": "the whole interval lies above zero; direction is reversed",
    "non_directional": "the interval contains or touches zero; this does not prove no relationship",
    "undefined": "at least one coefficient or paired seed-block resample is undefined; the registered interval fails closed",
}


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _hash(value: Any) -> str:
    return D.sha256_bytes(_canonical(value))


def _same(actual: Any, expected: Any, what: str) -> None:
    # JSON equality distinguishes bool/int/float, unlike Python ==.
    if _canonical(actual) != _canonical(expected):
        raise ValueError(f"inconsistent {what}")


def _keys(value: Any, names: set[str], what: str) -> dict:
    if type(value) is not dict or set(value) != names:
        raise ValueError(f"invalid {what} schema")
    return value


def _hex(value: Any, length: int, what: str) -> str:
    if type(value) is not str or re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is None:
        raise ValueError(f"{what} must be an exact lowercase {length}-hex value")
    return value


def _number(value: Any, what: str, *, nullable: bool = False, rho: bool = False) -> None:
    if nullable and value is None:
        return
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(f"{what} must be a finite float" + (" or null" if nullable else ""))
    if (rho and not -1.000000000000001 <= value <= 1.000000000000001) or (not rho and value < 0):
        raise ValueError(f"{what} outside its scientific range")


def _regular(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("report must be an independent regular file, not a link")


def _analysis_state(expected: str) -> None:
    try:
        state = git_state()
    except OSError as exc:
        raise ValueError("cannot verify analysis Git provenance") from exc
    if (type(state) is not GitState or state.dirty is not False
            or state.trustworthy is not True or state.commit != expected):
        raise ValueError("analysis_commit must match the current clean trustworthy Git tree")


def _writer_contract() -> None:
    """Positive pre-access check: code/constants still implement report v1.

    Replay deliberately does not call this or read the amendment document.
    Its frozen v1 rule is not reinterpreted under future live constants.
    """
    actual = {
        "seeds": [K.CONFIRMATORY_SEED_BASE + i for i in range(K.SEEDS_HYPOTHESIS)],
        "sizes": list(K.DATA_SIZES), "confidence": K.CONFIDENCE_LEVEL,
        "direction": K.TREND_EXPECTED_DIRECTION,
        "upper_bound": K.TREND_PASS_REQUIRES_UPPER_BOUND_BELOW,
        "bootstrap": K.TREND_BOOTSTRAP, "quantile": K.TREND_QUANTILE_METHOD,
        "scale_domain": K.NORMALISATION_SCALE_DOMAIN,
        "scale_source": K.NORMALISATION_SCALE_SOURCE,
    }
    expected = {
        "seeds": list(_SEEDS), "sizes": list(_SIZES), "confidence": 0.95,
        "direction": "negative", "upper_bound": 0.0,
        "bootstrap": "exact_paired_seed_block", "quantile": "linear",
        "scale_domain": _SCALE_DOMAIN, "scale_source": _SCALE_SOURCE,
    }
    _same(actual, expected, "live constants versus frozen report rule")
    _same(D.sha256_file(_AMENDMENT_PATH), AMENDMENT_SHA256, "D-154 amendment document digest")


def _paths(fit_directories: Sequence[Path], report_path: Path) -> tuple[tuple[Path, ...], Path]:
    if (not isinstance(fit_directories, Sequence) or isinstance(fit_directories, (str, bytes))
            or len(fit_directories) != 150 or any(not isinstance(p, Path) for p in fit_directories)):
        raise ValueError("supply exactly 150 explicit fit directory Paths, never handcrafted rows")
    if not isinstance(report_path, Path):
        raise ValueError("report_path must be an explicit Path")
    if report_path.exists() or report_path.is_symlink():
        _regular(report_path)
    paths = tuple(p.resolve() for p in fit_directories)
    if len(set(paths)) != 150:
        raise ValueError("duplicate resolved source directory")
    output = report_path.resolve()
    if not output.is_relative_to(WORKSPACE_ROOT):
        raise ValueError("report output must stay inside the project workspace")
    if any(output == p or p in output.parents or output in p.parents for p in paths):
        raise ValueError("report output must not overlap a source directory")
    return paths, output


def _input_binding(group: str, metric: str, rows: list[dict]) -> dict:
    selected = [r for r in rows if r["comparison_group_id"] == group]
    return {
        "comparison_group_id": group, "metric": metric,
        "seeds": list(_SEEDS), "sizes": list(_SIZES),
        "fit_ids": [r["fit_id"] for r in selected],
        "seed_curves": [[r[f"mean_{metric}"] for r in selected if r["seed"] == seed]
                        for seed in _SEEDS],
    }


def _support(result: TrendResult) -> dict:
    values = result.bootstrap_values
    if len(values) != 3125 or result.n_resamples != 3125:
        raise ValueError("core did not supply all 3125 original bootstrap values")
    counts = Counter(v for v in values if math.isfinite(v))
    undefined = sum(math.isnan(v) for v in values)
    if sum(counts.values()) + undefined != len(values):
        raise ValueError("core bootstrap contains infinity")
    return {
        "n_resamples": len(values), "undefined_count": undefined,
        "undefined_mass": undefined / len(values),
        "atoms": [{"rho": value, "count": count, "mass": count / len(values)}
                  for value, count in sorted(counts.items())],
    }


def _status(rho: float | None, low: float | None, high: float | None, undefined: int) -> str:
    if rho is None or undefined:
        return "undefined"
    if low is None or high is None:
        raise ValueError("defined bootstrap must have both interval endpoints")
    if high < 0.0:
        return "negative"
    return "reversed" if low > 0.0 else "non_directional"


def _metric_record(group: str, metric: str, rows: list[dict]) -> dict:
    binding = _input_binding(group, metric, rows)
    curves = {seed: dict(zip(_SIZES, values, strict=True))
              for seed, values in zip(_SEEDS, binding["seed_curves"], strict=True)}
    result = trend_test(curves, partition="confirmatory")
    support = _support(result)
    nullable = lambda value: None if math.isnan(value) else value
    rho, low, high = (nullable(v) for v in (result.rho, result.ci_low, result.ci_high))
    status = _status(rho, low, high, support["undefined_count"])
    if result.passed is not (status == "negative"):
        raise ValueError("core verdict disagrees with the unchanged reading rule")
    record = {
        "metric": metric,
        "role": "registered_disagreement_component" if metric == "disagreement" else "diagnostic_only",
        "title": "Disagreement trend: registered criterion" if metric == "disagreement" else "Error trend: diagnostic only",
        "input_sha256": _hash(binding), "seed_curves": binding["seed_curves"],
        "rho": rho, "ci_low": low, "ci_high": high,
        "per_seed_rho": [nullable(v) for v in result.per_seed_rho],
        "mean_curve": list(result.mean_curve), "support": support,
        "status": status, "reason": _STATUS_REASON[status],
    }
    if metric == "disagreement":
        record["criterion_met"] = result.passed
    return record


def _overall(configurations: list[dict]) -> dict:
    if len(configurations) != 5 or len({c["comparison_group_id"] for c in configurations}) != 5:
        raise ValueError("all-five summary requires exactly five distinct configurations")
    flags = [c["results"]["disagreement"]["criterion_met"] for c in configurations]
    if any(type(flag) is not bool for flag in flags):
        raise ValueError("disagreement component flags must be exact bools")
    missing = [c["comparison_group_id"] for c, met in zip(configurations, flags, strict=True) if not met]
    return {
        "kind": "amended_descriptive_decision_summary", "amendment_id": "D-154",
        "all_five_meet_disagreement_criterion": all(flags),
        "n_meeting_criterion": sum(flags), "not_meeting_criterion": missing,
        "statement": ("all five meet the registered disagreement criterion" if all(flags)
                      else "support was not established across all five configurations"),
        "limitation": "New amended operational conjunction, not a pristine preregistered global test, calibrated omnibus test, or simultaneous confidence claim.",
    }


def _build(evidence: Experiment1Evidence, fit_commit: str, analysis_commit: str) -> dict:
    if type(evidence) is not Experiment1Evidence or evidence.expected_git_commit != fit_commit:
        raise ValueError("loader returned evidence with incorrect type or fit commit")
    _same(list(evidence.seeds), list(_SEEDS), "loader seeds")
    _same(list(evidence.data_sizes), list(_SIZES), "loader sizes")
    rows = []
    for row in evidence.rows:
        cfg = Config(unit=row.unit, stage=row.execution_stage, seed=row.seed)
        item = {name: getattr(row, name) for name in (
            "comparison_group_id", "causal_attribute", "layout", "seed", "n_transitions",
            "unit_id", "config_id", "fit_id", "execution_stage", "execution_run_id",
            "execution_digest", "evaluation_pool_digest", "n_movement", "mean_error", "mean_disagreement",
        )}
        item.update(config=cfg.to_dict(), roles=list(row.roles), source_path=str(row.source_path),
                    scale={**asdict(row.scale), "vector": list(row.scale.vector)},
                    transition_identity_sha256=_hash({"episode": row.episode, "step": row.step,
                                                       "evaluation_action": row.evaluation_action}))
        rows.append(item)
    rows.sort(key=lambda r: (r["comparison_group_id"], r["seed"], r["n_transitions"]))
    # Refuse malformed mocked/future loader output BEFORE any statistic is run.
    groups = _validate_rows(rows)
    _same(list(evidence.comparison_group_ids), sorted(groups), "loader configuration IDs")
    configurations = [
        {"comparison_group_id": group, "causal_attribute": pair[0], "layout": pair[1],
         "results": {metric: _metric_record(group, metric, rows) for metric in _METRICS}}
        for group, pair in sorted(groups.items())
    ]
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION, "kind": "experiment_1_coefficient_report",
        "amendment": dict(_DISCLOSURE), "timing": dict(_TIMING), "rule": dict(_RULE),
        "seeds": list(_SEEDS), "data_sizes": list(_SIZES),
        "provenance": {"expected_fit_commit": fit_commit, "analysis_commit": analysis_commit,
                       "analysis_git_clean": True, "analysis_git_trustworthy": True,
                       "amendment_document_sha256": AMENDMENT_SHA256,
                       "source_inventory_sha256": _hash(rows)},
        "rows": rows, "configurations": configurations, "overall": _overall(configurations),
    }
    return {**payload, "payload_sha256": _hash(payload)}


def _validate_rows(rows: Any) -> dict[str, tuple[str, str]]:
    if type(rows) is not list or len(rows) != 150:
        raise ValueError("report requires exactly 150 source rows")
    groups: dict[str, tuple[str, str]] = {}
    identities, paths, paired = set(), set(), {}
    multirole = 0
    row_keys = {
        "comparison_group_id", "causal_attribute", "layout", "seed", "n_transitions",
        "unit_id", "config_id", "fit_id", "execution_stage", "execution_run_id", "roles",
        "source_path", "execution_digest", "evaluation_pool_digest", "n_movement",
        "mean_error", "mean_disagreement", "config", "scale", "transition_identity_sha256",
    }
    for row in rows:
        _keys(row, row_keys, "source row")
        pair = (row["causal_attribute"], row["layout"])
        if (pair not in _PAIRS or type(row["seed"]) is not int or row["seed"] not in _SEEDS
                or type(row["n_transitions"]) is not int or row["n_transitions"] not in _SIZES):
            raise ValueError("unregistered configuration, seed, or size")
        expected = Config(unit=UnitSpec(causal_attribute=pair[0], layout=pair[1], confound_rate=0.0,
                                       family="estimation", n_transitions=row["n_transitions"]),
                          stage="exp1", seed=row["seed"])
        _same(row["config"], expected.to_dict(), "canonical Config")
        for field in ("unit_id", "config_id", "fit_id"):
            _same(row[field], getattr(expected, field), field)
        _same(row["execution_stage"], "exp1", "execution stage")
        _same(row["execution_run_id"], expected.run_id, "execution run")
        group = comparison_group_id(expected.unit, "exp1")
        _same(row["comparison_group_id"], group, "comparison group")
        groups[group] = pair
        # D-025's complete six-size reference ladder; not just a total count.
        expected_roles = ["exp1", "repair_validation"] if pair == ("shape", "uniform") else ["exp1"]
        _same(row["roles"], expected_roles, "exact registered Experiment-1 roles")
        multirole += len(row["roles"]) == 2
        source = row["source_path"]
        if type(source) is not str or not (PureWindowsPath(source).is_absolute() or PurePosixPath(source).is_absolute()):
            raise ValueError("source path must be an explicit absolute path")
        # Pure path comparison only: replay must NOT resolve/stat source paths.
        path_key = PureWindowsPath(source) if PureWindowsPath(source).is_absolute() else PurePosixPath(source)
        if row["fit_id"] in identities or path_key in paths:
            raise ValueError("duplicate source path or physical fit")
        identities.add(row["fit_id"])
        paths.add(path_key)
        for field in ("execution_digest", "evaluation_pool_digest", "transition_identity_sha256"):
            _hex(row[field], 64, field)
        if type(row["n_movement"]) is not int or not 0 < row["n_movement"] <= 1000:
            raise ValueError("invalid movement count")
        scale = _keys(row["scale"], {"vector", "n_reference", "domain", "source"}, "scale")
        _same(scale["n_reference"], row["n_movement"], "scale reference count")
        # Preserve the loader's scale contract without reading any source file.
        _same(scale["domain"], _SCALE_DOMAIN, "scale domain")
        _same(scale["source"], _SCALE_SOURCE, "scale source")
        if type(scale["vector"]) is not list or len(scale["vector"]) != 2:
            raise ValueError("invalid scale vector")
        for v in scale["vector"]:
            _number(v, "scale")
            if v == 0:
                raise ValueError("scale must be positive")
        for metric in _METRICS:
            _number(row[f"mean_{metric}"], metric)
        ref = {field: row[field] for field in ("evaluation_pool_digest", "scale", "transition_identity_sha256", "n_movement")}
        _same(ref, paired.setdefault((group, row["seed"]), ref), "cross-size pairing")
    if len(groups) != 5 or set(groups.values()) != set(_PAIRS) or multirole != 30:
        raise ValueError("incomplete five-configuration or 30-multirole inventory")
    order = [(r["comparison_group_id"], r["seed"], r["n_transitions"]) for r in rows]
    if order != [(group, seed, size) for group in sorted(groups) for seed in _SEEDS for size in _SIZES]:
        raise ValueError("source grid must be exact and canonically ordered")
    return groups


def _validate_metric(record: Any, group: str, metric: str, rows: list[dict]) -> None:
    names = {"metric", "role", "title", "input_sha256", "seed_curves", "rho", "ci_low", "ci_high",
             "per_seed_rho", "mean_curve", "support", "status", "reason"}
    if metric == "disagreement":
        names.add("criterion_met")
    _keys(record, names, "metric result")
    _same(record["metric"], metric, "metric name")
    _same(record["role"], "registered_disagreement_component" if metric == "disagreement" else "diagnostic_only", "metric role")
    _same(record["title"], "Disagreement trend: registered criterion" if metric == "disagreement" else "Error trend: diagnostic only", "metric title")
    binding = _input_binding(group, metric, rows)
    _same(record["seed_curves"], binding["seed_curves"], "metric input curves")
    _same(record["input_sha256"], _hash(binding), "metric input digest")
    _same(record["mean_curve"], np.asarray(binding["seed_curves"]).mean(axis=0).tolist(), "stored mean curve")
    for field in ("rho", "ci_low", "ci_high"):
        _number(record[field], field, nullable=True, rho=True)
    if type(record["per_seed_rho"]) is not list or len(record["per_seed_rho"]) != 5:
        raise ValueError("exactly five per-seed coefficients required")
    for value in record["per_seed_rho"]:
        _number(value, "per-seed rho", nullable=True, rho=True)
    support = _keys(record["support"], {"n_resamples", "undefined_count", "undefined_mass", "atoms"}, "bootstrap support")
    _same(support["n_resamples"], 3125, "bootstrap size")
    undefined = support["undefined_count"]
    if type(undefined) is not int or not 0 <= undefined <= 3125:
        raise ValueError("invalid undefined-resample count")
    _same(support["undefined_mass"], undefined / 3125, "undefined mass")
    if type(support["atoms"]) is not list or len(support["atoms"]) > 3125:
        raise ValueError("invalid bootstrap atoms")
    expanded, previous = [], -math.inf
    for atom in support["atoms"]:
        _keys(atom, {"rho", "count", "mass"}, "bootstrap atom")
        _number(atom["rho"], "atom rho", rho=True)
        if atom["rho"] <= previous or type(atom["count"]) is not int or not 0 < atom["count"] <= 3125:
            raise ValueError("atoms must be distinct, sorted, and have positive integer counts")
        previous = atom["rho"]
        _same(atom["mass"], atom["count"] / 3125, "atom mass")
        expanded.extend([atom["rho"]] * atom["count"])
        if len(expanded) + undefined > 3125:
            raise ValueError("bootstrap masses exceed the full resample space")
    if len(expanded) + undefined != 3125:
        raise ValueError("bootstrap counts must total 3125, including undefined resamples")
    rho, low, high = record["rho"], record["ci_low"], record["ci_high"]
    if rho is None and not undefined:
        raise ValueError("undefined point coefficient requires undefined bootstrap support")
    if rho is not None and rho not in expanded:
        raise ValueError("the original mean-curve coefficient must occur in bootstrap support")
    if rho is None or undefined:
        if low is not None or high is not None:
            raise ValueError("undefined bootstrap must have null interval endpoints")
    else:
        # Algebraic consistency of STORED support, not a new bootstrap/trend.
        # Match the core's floating-point percentile expressions exactly.
        bounds = np.percentile(expanded, [100 * (1 - 0.95) / 2, 100 * (1 + 0.95) / 2], method="linear").tolist()
        _same([low, high], bounds, "interval versus stored bootstrap support")
    # Every original seed repeated five times is an enumerated resample.
    if any(value is None for value in record["per_seed_rho"]) and not undefined:
        raise ValueError("undefined seed coefficient requires undefined bootstrap support")
    status = _status(rho, low, high, undefined)
    _same(record["status"], status, "metric status")
    _same(record["reason"], _STATUS_REASON[status], "metric reason")
    if metric == "disagreement":
        _same(record["criterion_met"], status == "negative", "disagreement criterion")


def _validate_document(document: Any) -> dict:
    _keys(document, {"schema_version", "kind", "amendment", "timing", "rule", "seeds", "data_sizes",
                     "provenance", "rows", "configurations", "overall", "payload_sha256"}, "report")
    _same(document["schema_version"], REPORT_SCHEMA_VERSION, "report schema version")
    _same(document["kind"], "experiment_1_coefficient_report", "report kind")
    _same(document["amendment"], _DISCLOSURE, "amendment disclosure")
    _same(document["timing"], _TIMING, "timing policy")
    _same(document["rule"], _RULE, "statistical rule")
    _same(document["seeds"], list(_SEEDS), "registered seeds")
    _same(document["data_sizes"], list(_SIZES), "registered sizes")
    _hex(document["payload_sha256"], 64, "payload digest")
    _same(document["payload_sha256"], _hash({k: v for k, v in document.items() if k != "payload_sha256"}), "payload digest")
    provenance = _keys(document["provenance"], {"expected_fit_commit", "analysis_commit", "analysis_git_clean",
                                               "analysis_git_trustworthy", "source_inventory_sha256",
                                               "amendment_document_sha256"}, "provenance")
    for field in ("expected_fit_commit", "analysis_commit"):
        _hex(provenance[field], 40, field)
    _same(provenance["analysis_git_clean"], True, "clean analysis tree")
    _same(provenance["analysis_git_trustworthy"], True, "trustworthy analysis tree")
    _same(provenance["amendment_document_sha256"], AMENDMENT_SHA256, "amendment document digest")
    rows = document["rows"]
    groups = _validate_rows(rows)
    _same(provenance["source_inventory_sha256"], _hash(rows), "source inventory digest")
    configurations = document["configurations"]
    if type(configurations) is not list or len(configurations) != 5:
        raise ValueError("report requires exactly five configurations")
    for config, (group, pair) in zip(configurations, sorted(groups.items()), strict=True):
        _keys(config, {"comparison_group_id", "causal_attribute", "layout", "results"}, "configuration")
        _same(config["comparison_group_id"], group, "configuration ID")
        _same([config["causal_attribute"], config["layout"]], list(pair), "configuration metadata")
        _keys(config["results"], set(_METRICS), "configuration results")
        for metric in _METRICS:
            _validate_metric(config["results"][metric], group, metric, rows)
    _same(document["overall"], _overall(configurations), "all-five amended summary")
    return document


def write_experiment_1_report(
    fit_directories: Sequence[Path], *, expected_fit_commit: str,
    analysis_commit: str, report_path: Path,
) -> Path:
    """Verify sources, compute the fixed ten results, and publish immutably.

    Both commits are required; analysis provenance is checked before source
    access and again before publication. Existing artifacts never bypass source
    verification. No file is published on a scientific/provenance refusal.
    """
    _hex(expected_fit_commit, 40, "expected_fit_commit")
    _hex(analysis_commit, 40, "analysis_commit")
    sources, output = _paths(fit_directories, report_path)
    _analysis_state(analysis_commit)
    _writer_contract()
    evidence = load_experiment_1_evidence(sources, expected_git_commit=expected_fit_commit)
    document = _build(evidence, expected_fit_commit, analysis_commit)
    _validate_document(document)
    _writer_contract()
    _analysis_state(analysis_commit)
    # Recheck links/path containment after analysis as well as before access.
    if _paths(fit_directories, report_path) != (sources, output):
        raise ValueError("report/source paths changed during analysis")
    written = D.atomic_write_json(output, document)
    return written


def replay_experiment_1_report(report_path: Path, *, expected_sha256: str) -> dict:
    """Read only this artifact using an EXTERNALLY supplied exact-byte digest.

    Stored source paths/digests remain provenance, not instructions to open
    anything. No Git query, evidence loader or trend function is used here.
    A returned dict is an inspection copy, never accepted by the writer.
    """
    _hex(expected_sha256, 64, "expected_sha256")
    if not isinstance(report_path, Path):
        raise ValueError("report_path must be a Path, not a handcrafted report")
    _regular(report_path)
    raw = report_path.read_bytes()
    if D.sha256_bytes(raw) != expected_sha256:
        raise ValueError("report SHA-256 does not match the externally supplied digest")
    # Parse the SAME bytes that were hashed; do not reopen with read_json().
    document = D._decode_json(raw, source=str(report_path))
    return _validate_document(document)
