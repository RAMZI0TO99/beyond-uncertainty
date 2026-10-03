"""Contemporaneous, experimenter-only baseline data anchors (D-155 follow-up).

The collector captures immutable latent states in its existing transition loop.
The runner must publish/read back this companion *before* training, then link
it to completed fit evidence. This module cannot establish wall-clock ordering
from a caller's assertion: the new launch/runner boundary owns that invariant.
It never reconstructs old data or calls old reconstructions contemporaneous.

Schema 1 binds full arrays and symbolic states, baseline identities, six data
keys, generating commit and full movement-evaluation scale. Old Config IDs,
stream keys and fit-evidence schemas are unchanged. Anchor identity contains
no paths, inode numbers or time stamps, so a verified copy is the same anchor.
All writes are exclusive/idempotent, using the project's durable primitives.
The separate after-fit link prevents a circular hash. Neither latent state nor
this metadata is an eligible model input or critic feature.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import re
import stat
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .. import constants as K
from ..config import IDENTITY_VERSION, SCHEMA_VERSION, Arm, Config, UnitSpec
from ..durable import (
    _decode_json, atomic_write_bytes, atomic_write_json, read_json, sha256_file,
)
from ..env.collect import (
    CapturedPools, CoverageReport, Pools, SymbolicTransition, TransitionDataset,
    _tally, expected_size,
)
from ..env.encoder import ObservationEncoder
from ..env.gridworld import (
    COLOURS, INTERACT, N_ACTIONS, SHAPES, GridObject, GridState, GridWorld,
)
from ..models.uncertainty import NormalisationScale
from ..models.world_model import MOVEMENT_ACTIONS
from ..streams import DATA_PURPOSES, POOL_PURPOSES, STREAM_VERSION, stream_key

POOL_ANCHOR_SCHEMA_VERSION = 1
SYMBOLIC_CAPTURE_VERSION = 1
POOL_ANCHORS_DIRECTORY = "pool_anchors"
POOL_ANCHOR_FILE = "pool_anchors.json"
POOL_ANCHOR_LINK_FILE = "fit_link.json"
_BASELINE_STAGES = ("exp1", "exp2a", "exp2b", "config_sweep")
_FIELDS = ("obs", "action", "next_obs", "episode", "step", "state", "next_state")
_ARRAY_FIELDS = _FIELDS[:5]
_DELTAS = ((0, -1), (1, 0), (0, 1), (-1, 0))


@dataclass(frozen=True)
class VerifiedPoolAnchors:
    """Read-back evidence; consumers must reload before reuse, not trust a tag."""

    path: Path
    anchor_sha256: str
    captured: CapturedPools
    scale: NormalisationScale
    source_commit: str

    @property
    def sha(self) -> str:
        """Short integration alias for the exact manifest SHA256."""
        return self.anchor_sha256

    @property
    def pools(self) -> Pools:
        return self.captured.pools


def _json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def _plain(value: Any) -> Any:
    return json.loads(_json(dataclasses.asdict(value)))


def _hex(value: Any, length: int, what: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{%d}" % length, value) is None:
        raise ValueError(f"{what} must be an exact lowercase {length}-hex digest")
    return value


def _identity(unit: UnitSpec, seed: int, stage: str, source_commit: str) -> dict:
    if type(unit) is not UnitSpec:
        raise ValueError("anchor unit must be an exact UnitSpec")
    if type(seed) is not int or seed < 0:
        raise ValueError("anchor seed must be a non-negative exact integer")
    if type(stage) is not str or stage not in _BASELINE_STAGES:
        raise ValueError(f"anchor stage must be an original baseline stage: {_BASELINE_STAGES}")
    _hex(source_commit, 40, "source_commit")
    config = Config(unit=unit, arm=Arm("baseline"), seed=seed, stage=stage)
    return {
        "schema_version": SCHEMA_VERSION, "identity_version": IDENTITY_VERSION,
        "unit": _plain(unit), "unit_id": config.unit_id,
        "config_id": config.config_id, "fit_id": config.fit_id,
        "execution_run_id": config.run_id, "arm": "baseline", "seed": seed,
        "generation_stage": stage, "source_commit": source_commit,
        "stream_version": STREAM_VERSION,
        "data_keys": {purpose: dict(stream_key(unit, stage, purpose), seed=seed)
                      for purpose in sorted(DATA_PURPOSES)},
        "episode_length": K.EPISODE_LENGTH,
    }


def _regular(path: Path, *, directory: bool = False) -> None:
    # Check all components, before resolve: resolving first hides link aliases.
    for part in (path, *path.parents):
        if not part.exists() and not part.is_symlink():
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"anchor evidence may not traverse a link/reparse point: {part}")
    try:
        info = path.stat()
    except OSError as exc:
        raise ValueError(f"missing anchor evidence: {path}") from exc
    predicate = stat.S_ISDIR if directory else stat.S_ISREG
    if not predicate(info.st_mode):
        raise ValueError(f"anchor evidence is not a regular {'directory' if directory else 'file'}: {path}")


def _state_row(state: GridState, unit: UnitSpec) -> list[int]:
    if type(state) is not GridState or type(state.agent) is not tuple or len(state.agent) != 2:
        raise ValueError("symbolic anchor must contain a complete GridState")
    if type(state.objects) is not tuple or len(state.objects) != unit.n_objects:
        raise ValueError("symbolic anchor object inventory differs from the unit")
    coordinates = [*state.agent]
    positions = []
    row = [*state.agent]
    for obj in state.objects:
        if type(obj) is not GridObject:
            raise ValueError("symbolic object must be an exact GridObject")
        if obj.shape not in SHAPES or obj.colour not in COLOURS or type(obj.activated) is not bool:
            raise ValueError("invalid symbolic shape/colour/activation")
        coordinates.extend(obj.pos)
        positions.append(obj.pos)
        row.extend([obj.x, obj.y, SHAPES.index(obj.shape), COLOURS.index(obj.colour),
                    int(obj.activated)])
    if any(type(v) is not int or not 1 <= v <= unit.grid_size - 2 for v in coordinates):
        raise ValueError("symbolic coordinates must be interior exact integers")
    if len(set(positions)) != len(positions):
        raise ValueError("symbolic objects occupy duplicate positions")
    if positions != sorted(positions, key=lambda p: (p[1], p[0])):
        raise ValueError("symbolic objects are not in canonical raster order")
    return row


def _from_row(row: np.ndarray, unit: UnitSpec) -> GridState:
    values = row.tolist()
    objects = []
    for start in range(2, len(values), 5):
        x, y, shape, colour, active = values[start:start + 5]
        if shape not in (0, 1) or colour not in (0, 1) or active not in (0, 1):
            raise ValueError("invalid symbolic categorical value")
        objects.append(GridObject(x, y, SHAPES[shape], COLOURS[colour], bool(active)))
    state = GridState(tuple(values[:2]), tuple(objects))
    if _state_row(state, unit) != values:
        raise ValueError("symbolic state is not canonical")
    return state


def reencode_anchors(
    transitions: tuple[SymbolicTransition, ...], unit: UnitSpec, *, next_state: bool = False,
) -> np.ndarray:
    """Re-encode latent states through an arm's encoder; never delete columns.

    Restoring an attribute can change the descriptor sort and hence object slot
    order. This is an experimenter-side compatibility operation only.
    """
    if type(transitions) is not tuple or not transitions:
        raise ValueError("re-encoding requires non-empty symbolic transitions")
    if type(unit) is not UnitSpec or type(next_state) is not bool:
        raise ValueError("re-encoding requires an exact UnitSpec and boolean selector")
    encoder = ObservationEncoder(unit.n_objects, unit.grid_size, unit.withheld_features)
    rows = []
    for transition in transitions:
        if type(transition) is not SymbolicTransition:
            raise ValueError("re-encoding requires exact SymbolicTransition records")
        state = transition.next_state if next_state else transition.state
        _state_row(state, unit)
        rows.append(encoder.encode(state))
    return np.asarray(rows, dtype=np.float32)


def _coverage(transitions: tuple[SymbolicTransition, ...], unit: UnitSpec) -> CoverageReport:
    # Reuse the collector's informative-transition tally, never infer coverage
    # from stored prose. Movement/wall totals follow its exact branch order.
    shape_action, causal_action, bumps = Counter(), Counter(), Counter()
    moved = blocked_object = blocked_wall = 0
    for t in transitions:
        _tally(unit, t.state, t.action, t.next_state, shape_action, causal_action, bumps)
        if t.next_state.agent != t.state.agent:
            moved += 1
        elif t.action != INTERACT:
            dx, dy = _DELTAS[t.action]
            target = (t.state.agent[0] + dx, t.state.agent[1] + dy)
            if t.state.object_at(target) is not None:
                blocked_object += 1
            else:
                blocked_wall += 1
    n = len(transitions)
    return CoverageReport(n, transitions[-1].episode + 1, dict(shape_action),
                          dict(causal_action), dict(bumps), blocked_object / n,
                          blocked_wall / n, moved / n)


def _array_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.save(stream, array, allow_pickle=False)
    return stream.getvalue()


def _encoding(unit: UnitSpec) -> dict:
    encoder = ObservationEncoder(unit.n_objects, unit.grid_size, unit.withheld_features)
    return {
        "name": "ObservationEncoder", "symbolic_capture_version": SYMBOLIC_CAPTURE_VERSION,
        "object_order": "raster_y_x", "observation_slot_order": "visible_descriptor_sorted",
        "state_columns": ["agent_x", "agent_y"],
        "object_columns": ["x", "y", "shape_index", "colour_index", "activated"],
        "shape_values": list(SHAPES), "colour_values": list(COLOURS),
        "withheld": list(encoder.withheld), "blocks": [_plain(b) for b in encoder.blocks],
        "obs_dim": encoder.size,
    }


def _scale(pools: Pools) -> NormalisationScale:
    action = torch.as_tensor(pools.evaluation.action)
    move = torch.isin(action, torch.as_tensor(MOVEMENT_ACTIONS))
    # Match WorldModel.targets' advanced indexing, including its reduction
    # layout. The full movement pool precedes any prediction/failure mask.
    targets = torch.as_tensor(pools.evaluation.next_obs)[move][:, [0, 1]]
    if len(targets) == 0:
        raise ValueError("anchor evaluation pool contains no movement targets")
    return NormalisationScale.from_evaluation_pool(targets)


def _validated_arrays(
    captured: CapturedPools, *, unit: UnitSpec, seed: int, stage: str,
) -> dict[str, dict[str, np.ndarray]]:
    if type(captured) is not CapturedPools or type(captured.pools) is not Pools:
        raise ValueError("anchor capture must be exact CapturedPools with ordinary Pools")
    result = {}
    env = GridWorld(unit)
    for name in POOL_PURPOSES:
        data, transitions = getattr(captured.pools, name), getattr(captured, name)
        n = expected_size(unit, name, K.EPISODE_LENGTH)
        if type(data) is not TransitionDataset:
            raise ValueError(f"{name} is not an exact TransitionDataset")
        provenance = (data.unit, data.source_unit, data.arm, data.stage, data.seed,
                      data.pool, data.episode_length, data.stream_version)
        expected = (unit, unit, "baseline", stage, seed, name, K.EPISODE_LENGTH, STREAM_VERSION)
        if (provenance != expected
                or any(type(value) is not int for value in
                       (data.seed, data.episode_length, data.stream_version))
                or any(type(value) is not str for value in (data.arm, data.stage, data.pool))):
            raise ValueError(f"{name} pool provenance differs from the expected baseline")
        if type(transitions) is not tuple or len(transitions) != n:
            raise ValueError(f"{name} symbolic transition count differs from its frozen size")
        arrays = {field: getattr(data, field) for field in _ARRAY_FIELDS}
        for field, value in arrays.items():
            floating = field in ("obs", "next_obs")
            shape = (n, env.encoder.size) if floating else (n,)
            dtype = np.dtype("float32" if floating else "int64")
            if (type(value) is not np.ndarray or value.dtype != dtype or value.shape != shape
                    or not np.isfinite(value).all()):
                raise ValueError(f"{name}.{field} has invalid dtype, shape or finite content")
        states, next_states = [], []
        for i, t in enumerate(transitions):
            if type(t) is not SymbolicTransition:
                raise ValueError(f"{name} has a non-symbolic transition")
            if (type(t.action) is not int or not 0 <= t.action < N_ACTIONS
                    or type(t.episode) is not int or type(t.step) is not int
                    or t.episode != i // K.EPISODE_LENGTH or t.step != i % K.EPISODE_LENGTH):
                raise ValueError(f"{name} symbolic action/episode/step is invalid")
            if (t.action != data.action[i] or t.episode != data.episode[i] or t.step != data.step[i]):
                raise ValueError(f"{name} symbolic transition identifiers differ from arrays")
            states.append(_state_row(t.state, unit))
            next_states.append(_state_row(t.next_state, unit))
            if t.next_state != env.transition(t.state, t.action):
                raise ValueError(f"{name} symbolic successor contradicts the environment")
            if t.step and t.state != transitions[i - 1].next_state:
                raise ValueError(f"{name} symbolic trajectory is discontinuous")
        arrays["state"] = np.asarray(states, dtype=np.int64)
        arrays["next_state"] = np.asarray(next_states, dtype=np.int64)
        for field, future in (("obs", False), ("next_obs", True)):
            if arrays[field].tobytes() != reencode_anchors(transitions, unit, next_state=future).tobytes():
                raise ValueError(f"{name}.{field} differs from symbolic re-encoding")
        if type(data.coverage) is not CoverageReport or _json(data.coverage.to_dict()) != _json(_coverage(transitions, unit).to_dict()):
            raise ValueError(f"{name} coverage differs from symbolic transitions")
        result[name] = arrays
    return result


def _payload(captured: CapturedPools, *, unit: UnitSpec, seed: int, stage: str,
             source_commit: str) -> tuple[dict, dict[str, bytes]]:
    identity = _identity(unit, seed, stage, source_commit)
    arrays = _validated_arrays(captured, unit=unit, seed=seed, stage=stage)
    files, inventory = {}, {}
    for pool, values in arrays.items():
        inventory[pool] = {}
        for name, array in values.items():
            filename = f"{pool}.{name}.npy"
            raw = _array_bytes(array)
            files[filename] = raw
            inventory[pool][name] = {
                "path": filename, "dtype": array.dtype.str, "shape": list(array.shape),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
    document = {
        "pool_anchor_schema_version": POOL_ANCHOR_SCHEMA_VERSION,
        "capture_kind": "contemporaneous", "experimenter_only": True,
        "identity": identity, "encoding": _encoding(unit), "arrays": inventory,
        "coverage": {name: getattr(captured.pools, name).coverage.to_dict() for name in POOL_PURPOSES},
        "normalisation": _scale(captured.pools).as_row(),
    }
    return document, files


def write_pool_anchors(
    path: str | Path, captured: CapturedPools, *, unit: UnitSpec, seed: int,
    stage: str, source_commit: str,
) -> VerifiedPoolAnchors:
    """Publish before training, then compare readback to the exact input pools.

    A resumed identical write is idempotent; partial divergent files fail closed.
    There is no reconstructed/capture-kind override or arbitrary metadata input.
    """
    document, files = _payload(captured, unit=unit, seed=seed, stage=stage,
                               source_commit=source_commit)
    root = Path(path).absolute()
    for part in (root, *root.parents):
        if part.exists() or part.is_symlink():
            _regular(part, directory=True)
    root.mkdir(parents=True, exist_ok=True)
    for filename, raw in files.items():
        atomic_write_bytes(root / filename, raw)
    atomic_write_json(root / POOL_ANCHOR_FILE, document)
    return load_pool_anchors(
        root, expected_unit=unit, expected_seed=seed, expected_stage=stage,
        expected_source_commit=source_commit,
        expected_anchor_sha256=hashlib.sha256(_json(document)).hexdigest(),
        expected_pools=captured.pools,
    )


def load_pool_anchors(
    path: str | Path, *, expected_unit: UnitSpec, expected_seed: int,
    expected_stage: str, expected_source_commit: str, expected_anchor_sha256: str,
    expected_pools: Pools | None = None,
) -> VerifiedPoolAnchors:
    """Strict reload against independently expected identity and manifest hash.

    Re-derives metadata, sizes, keys, scale, coverage, latent dynamics and exact
    encoding. A checksum alone is insufficient. No collection or training runs.
    """
    identity = _identity(expected_unit, expected_seed, expected_stage, expected_source_commit)
    _hex(expected_anchor_sha256, 64, "expected_anchor_sha256")
    root = Path(path).absolute()
    _regular(root, directory=True)
    manifest = root / POOL_ANCHOR_FILE
    _regular(manifest)
    if sha256_file(manifest) != expected_anchor_sha256:
        raise ValueError("anchor manifest differs from independently expected digest")
    document = read_json(manifest)
    if type(document) is not dict or set(document) != {
        "pool_anchor_schema_version", "capture_kind", "experimenter_only", "identity",
        "encoding", "arrays", "coverage", "normalisation",
    }:
        raise ValueError("anchor manifest has missing/extra fields")
    if (_json(document["identity"]) != _json(identity)
            or _json(document["encoding"]) != _json(_encoding(expected_unit))
            or type(document["pool_anchor_schema_version"]) is not int
            or document["pool_anchor_schema_version"] != POOL_ANCHOR_SCHEMA_VERSION
            or document["capture_kind"] != "contemporaneous"
            or document["experimenter_only"] is not True):
        raise ValueError("anchor identity, schema, capture kind or encoding differs from expected")
    if (type(document["arrays"]) is not dict or set(document["arrays"]) != set(POOL_PURPOSES)
            or type(document["coverage"]) is not dict or set(document["coverage"]) != set(POOL_PURPOSES)):
        raise ValueError("anchor pool inventory is not exactly train/validation/evaluation")
    datasets, symbolic = {}, {}
    expected_files = {POOL_ANCHOR_FILE, POOL_ANCHOR_LINK_FILE}
    for name in POOL_PURPOSES:
        entries = document["arrays"][name]
        if type(entries) is not dict or set(entries) != set(_FIELDS):
            raise ValueError(f"{name} anchor array inventory differs from schema")
        n = expected_size(expected_unit, name, K.EPISODE_LENGTH)
        arrays = {}
        for field in _FIELDS:
            entry = entries[field]
            filename = f"{name}.{field}.npy"
            expected_files.add(filename)
            if type(entry) is not dict or set(entry) != {"path", "dtype", "shape", "sha256"} or entry["path"] != filename:
                raise ValueError(f"invalid anchor array entry: {name}.{field}")
            _hex(entry["sha256"], 64, "array sha256")
            file = root / filename
            _regular(file)
            # Bound input bytes from the expected unit, before decoding NPY.
            width = max(_encoding(expected_unit)["obs_dim"], 2 + 5 * expected_unit.n_objects)
            if file.stat().st_size > n * width * 8 + 1024:
                raise ValueError("anchor array exceeds its registered size bound")
            raw = file.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError(f"anchor array digest mismatch: {filename}")
            try:
                array = np.load(io.BytesIO(raw), allow_pickle=False)
            except (OSError, TypeError, ValueError, EOFError) as exc:
                raise ValueError(f"invalid anchor NPY array: {filename}") from exc
            if type(array) is not np.ndarray or _array_bytes(array) != raw:
                raise ValueError(f"noncanonical anchor NPY array: {filename}")
            floating = field in ("obs", "next_obs")
            shape = ((n, _encoding(expected_unit)["obs_dim"]) if floating else
                     (n, 2 + 5 * expected_unit.n_objects) if field in ("state", "next_state") else (n,))
            dtype = np.dtype("float32" if floating else "int64")
            if (array.shape != shape or array.dtype != dtype or not np.isfinite(array).all()
                    or _json(entry["shape"]) != _json(list(shape)) or entry["dtype"] != dtype.str):
                raise ValueError(f"invalid anchor array shape/dtype/content: {filename}")
            arrays[field] = array
        transitions = tuple(SymbolicTransition(
            _from_row(arrays["state"][i], expected_unit), int(arrays["action"][i]),
            _from_row(arrays["next_state"][i], expected_unit),
            int(arrays["episode"][i]), int(arrays["step"][i]),
        ) for i in range(n))
        # Validate dynamics and IDs before coverage (which indexes action IDs).
        if np.any((arrays["action"] < 0) | (arrays["action"] >= N_ACTIONS)):
            raise ValueError("invalid anchor action range")
        data = TransitionDataset(
            **{field: arrays[field] for field in _ARRAY_FIELDS}, unit=expected_unit,
            coverage=_coverage(transitions, expected_unit), seed=expected_seed,
            source_unit=expected_unit, arm="baseline", stage=expected_stage,
            pool=name, episode_length=K.EPISODE_LENGTH, stream_version=STREAM_VERSION,
        )
        datasets[name], symbolic[name] = data, transitions
    if any(item.name not in expected_files for item in root.iterdir()):
        raise ValueError("anchor directory contains an unregistered artifact")
    captured = CapturedPools(Pools(**datasets), **symbolic)
    derived, _ = _payload(captured, unit=expected_unit, seed=expected_seed,
                           stage=expected_stage, source_commit=expected_source_commit)
    if manifest.read_bytes() != _json(derived):
        raise ValueError("anchor manifest differs from rederived canonical content/scale/coverage")
    if expected_pools is not None:
        assert_pools_equal(captured.pools, expected_pools)
    return VerifiedPoolAnchors(root, expected_anchor_sha256, captured,
                               _scale(captured.pools), expected_source_commit)


def assert_pools_equal(actual: Pools, expected: Pools) -> None:
    """Exact arrays and provenance, not approximate numerical equality."""
    if type(actual) is not Pools or type(expected) is not Pools:
        raise ValueError("pool comparison requires exact Pools objects")
    for name in POOL_PURPOSES:
        a, b = getattr(actual, name), getattr(expected, name)
        if type(a) is not TransitionDataset or type(b) is not TransitionDataset:
            raise ValueError("pool comparison requires exact TransitionDataset objects")
        for field in dataclasses.fields(TransitionDataset):
            x, y = getattr(a, field.name), getattr(b, field.name)
            if field.name in _ARRAY_FIELDS:
                if (type(x) is not np.ndarray or type(y) is not np.ndarray
                        or x.dtype != y.dtype or x.shape != y.shape or x.tobytes() != y.tobytes()):
                    raise ValueError(f"{name}.{field.name} differs from exact consumed pool")
            elif _json(_plain(x) if dataclasses.is_dataclass(x) else x) != _json(_plain(y) if dataclasses.is_dataclass(y) else y):
                raise ValueError(f"{name}.{field.name} provenance differs from exact consumed pool")


def _link_payload(anchor: VerifiedPoolAnchors, fit_dir: str | Path, *, unit: UnitSpec,
                  seed: int, stage: str, source_commit: str) -> dict:
    # Local imports avoid a cycle when confirmatory itself captures anchors.
    from .confirmatory import _digest_pool
    from .fit_evidence import FIT_EVIDENCE_FILE, load_fit_evidence

    _regular(Path(fit_dir).absolute(), directory=True)
    fit = load_fit_evidence(fit_dir, expected_git_commit=source_commit)
    metrics = Path(fit_dir) / fit.execution_run_id / "metrics.jsonl"
    _regular(metrics)
    with metrics.open("rb") as handle:
        records = [_decode_json(line, source="sealed fit metrics event") for line in handle]
    if not records:
        raise ValueError("first sealed metrics event is missing")
    event = records[0]
    expected_event = {
        "i": 0, "event": "pool_anchors", "pool_anchor_schema_version": POOL_ANCHOR_SCHEMA_VERSION,
        "pool_anchor_sha256": anchor.anchor_sha256,
    }
    if (_json(event) != _json(expected_event)
            or sum(type(row) is dict and row.get("event") == "pool_anchors"
                   for row in records) != 1):
        raise ValueError("first sealed metrics event does not bind the pre-training anchor")
    config = Config(unit=unit, arm=Arm("baseline"), seed=seed, stage=stage)
    if (fit.unit != unit or fit.arm != "baseline" or fit.seed != seed
            or fit.execution_stage != stage or fit.fit_id != config.fit_id
            or fit.execution_run_id != config.run_id
            or fit.evaluation_pool_digest != _digest_pool(anchor.pools)
            or fit.scale.as_row() != anchor.scale.as_row()):
        raise ValueError("completed fit identity/pool/scale differs from the baseline anchor")
    evaluation = anchor.pools.evaluation
    move = np.isin(evaluation.action, MOVEMENT_ACTIONS)
    for key, expected in (("evaluation_action", evaluation.action),
                          ("episode", evaluation.episode[move]), ("step", evaluation.step[move])):
        if not np.array_equal(fit.diagnostics[key], expected):
            raise ValueError(f"completed fit {key} differs from the anchor")
    return {
        "pool_anchor_link_schema_version": 1, "anchor_sha256": anchor.anchor_sha256,
        "fit_evidence_sha256": sha256_file(Path(fit_dir) / FIT_EVIDENCE_FILE),
        "fit_execution_digest": fit.execution_digest, "fit_id": fit.fit_id,
        "execution_run_id": fit.execution_run_id, "source_commit": source_commit,
    }


def link_pool_anchors(
    path: str | Path, fit_dir: str | Path, *, expected_unit: UnitSpec,
    expected_seed: int, expected_stage: str, expected_source_commit: str,
    expected_anchor_sha256: str,
) -> Path:
    """After completion, strictly reopen both sources and publish a separate link."""
    expected = dict(expected_unit=expected_unit, expected_seed=expected_seed,
                    expected_stage=expected_stage, expected_source_commit=expected_source_commit,
                    expected_anchor_sha256=expected_anchor_sha256)
    anchor = load_pool_anchors(path, **expected)
    payload = _link_payload(anchor, fit_dir, unit=expected_unit, seed=expected_seed,
                            stage=expected_stage, source_commit=expected_source_commit)
    target = atomic_write_json(anchor.path / POOL_ANCHOR_LINK_FILE, payload)
    load_pool_anchor_link(path, fit_dir, **expected)
    return target


def load_pool_anchor_link(
    path: str | Path, fit_dir: str | Path, *, expected_unit: UnitSpec,
    expected_seed: int, expected_stage: str, expected_source_commit: str,
    expected_anchor_sha256: str,
) -> VerifiedPoolAnchors:
    """Recovery boundary: missing/tampered linkage is not a completed anchor."""
    anchor = load_pool_anchors(
        path, expected_unit=expected_unit, expected_seed=expected_seed,
        expected_stage=expected_stage, expected_source_commit=expected_source_commit,
        expected_anchor_sha256=expected_anchor_sha256,
    )
    link = anchor.path / POOL_ANCHOR_LINK_FILE
    _regular(link)
    expected = _link_payload(anchor, fit_dir, unit=expected_unit, seed=expected_seed,
                            stage=expected_stage, source_commit=expected_source_commit)
    if link.read_bytes() != _json(expected):
        raise ValueError("pool anchor linkage differs from revalidated fit evidence")
    return anchor
