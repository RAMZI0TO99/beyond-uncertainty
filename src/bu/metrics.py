"""Structured metric logging, and loading it back.

One JSONL file per run, one JSON object per line, flushed on every write.
Flushing matters more than it looks: Kaggle sessions are time-limited and can
die mid-run, and Plan §14.4 requires results to be written incrementally rather
than at the end. A buffered logger loses exactly the runs that were expensive.

Every figure in the thesis is regenerated from these logs without rerunning
experiments (Plan §13.7), so anything a figure needs must be logged, not
printed.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any, Iterable, Iterator

import pandas as pd

from .config import Config
from .runrecord import read_run_record, write_run_record
from .streams import assert_confirmatory, is_confirmatory, seed_partition

METRICS_FILE = "metrics.jsonl"

#: The only permitted values of a run record's seed_partition field.
SEED_PARTITIONS = frozenset({"development", "confirmatory"})


class RunLogger:
    """Append-only JSONL metric log for a single run.

    Use as a context manager::

        with RunLogger.start(config, root="runs") as log:
            log.log(epoch=3, split="val", mse=0.021)

    ``start`` also writes the run record, so a metrics file never exists
    without the provenance that explains it.
    """

    def __init__(self, run_dir: str | Path, run_id: str, *, append: bool = False) -> None:
        """
        Args:
            append: continue an existing metric stream. **Off by default**, and
                the default is the safety property (D-062).

                The stream opened in append mode while the record counter
                restarted at zero, so writing twice into one run directory
                produced two records numbered ``i=0``, two numbered ``i=1``, and
                an analysis with no way to tell a rerun from a longer run.
                ``RunLogger.start`` never reaches this — ``write_run_record``
                rejects a duplicate ``run_id`` first — but the constructor is
                public, and the confirmatory runner (C-008) is exactly the
                caller that would hold a run directory open across a resume.

                When explicitly requested, the counter **continues** from the
                records already on disk rather than restarting, so ``i`` stays
                unique within a stream either way.
        """
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        path = self.run_dir / METRICS_FILE
        existing = 0
        if path.exists():
            existing = sum(1 for line in path.read_text().splitlines() if line.strip())
        if existing and not append:
            raise FileExistsError(
                f"{path} already holds {existing} record(s). Refusing to append: "
                "a second write into one run directory silently mixes two runs' "
                "evidence under one run_id. Write to a fresh directory, or pass "
                "append=True to continue this stream deliberately (D-062)."
            )
        self._fh = path.open("a", buffering=1)
        self._n = existing

    @classmethod
    def start(
        cls,
        config: Config,
        root: str | Path = "runs",
        *,
        repo: str | Path = ".",
        extra: dict[str, Any] | None = None,
    ) -> RunLogger:
        run_dir = Path(root) / config.run_id
        write_run_record(config, run_dir, repo=repo, extra=extra)
        return cls(run_dir, config.run_id)

    def log(self, **fields: Any) -> None:
        """Write one record. Keys are free-form; ``i`` is added automatically."""
        if not fields:
            raise ValueError("refusing to log an empty record")
        self._fh.write(json.dumps({"i": self._n, **fields}, default=_jsonable) + "\n")
        self._fh.flush()
        self._n += 1

    @property
    def n_records(self) -> int:
        return self._n

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> RunLogger:
        return self

    def __exit__(self, exc_type, exc, tb: TracebackType | None) -> None:
        self.close()


def iter_run_dirs(root: str | Path = "runs") -> Iterator[Path]:
    """Yield every directory under ``root`` holding a run record."""
    # rglob rather than glob: batch runners may group runs into subdirectories
    # by stage or sweep, and a run that is not found is a run silently missing
    # from an analysis.
    for p in sorted(Path(root).rglob("run.json")):
        yield p.parent


def load_runs(
    root: str | Path = "runs",
    *,
    run_ids: Iterable[str] | None = None,
    require_clean_git: bool = False,
    require_confirmatory: bool = False,
) -> pd.DataFrame:
    """Load every run's metrics into one long-format DataFrame.

    Each row is one logged record, joined to identity columns from the run
    record: ``run_id``, ``config_id``, ``unit_id``, ``seed``, ``arm``,
    ``family``, and the unit's configuration axes prefixed with ``unit_``.

    The identity columns are the point. Every confidence interval in this
    thesis is taken over ``unit_id`` rather than over rows (Plan §10.7), and
    that is only convenient if the unit travels with the data.

    .. warning::

       **The ``family`` and ``unit_*`` columns are construction metadata.**
       Plan §7.5 forbids the critic from seeing the condition label used to
       construct a scenario, the dataset size, or the capacity setting -- and
       all three are here. This frame is the experimenter's view, not the
       critic's.

       The Week 6 leakage firewall must therefore **whitelist** critic features
       rather than blacklist metadata: a blacklist silently fails open every
       time a column is added, and Plan §16 rates this leakage as "silent
       invalidation of all critic results". Nothing in this module may be fed
       to the critic dataset builder unfiltered.

    Returns an empty DataFrame with the identity columns if nothing is found,
    so callers can filter without a length check.

    Args:
        run_ids: restrict to these run ids.
        require_clean_git: raise if any loaded run was recorded from a dirty
            working tree. Off by default (development runs are routinely
            dirty); switch on for anything that reaches the thesis.
        require_confirmatory: raise if any loaded run used a development seed
            (D-034, D-040). **Switch this on in threshold calibration, repair
            acceptance and every critic loader.** Off by default so pipeline
            debugging at low seeds still works, which is the whole point of
            keeping a development range.
    """
    wanted = set(run_ids) if run_ids is not None else None
    frames: list[pd.DataFrame] = []
    seen: dict[str, Path] = {}

    for run_dir in iter_run_dirs(root):
        rec = read_run_record(run_dir)
        if wanted is not None and rec["run_id"] not in wanted:
            continue

        # Two directories carrying one run_id are two *executions* of the same
        # identity -- most plainly, two attempt directories from the same pilot
        # (D-062). Loading both silently doubles every one of that run's records
        # and every interval taken over them. The run_id uniqueness guard in
        # write_run_record only protects a single directory, so the merge is
        # where this has to be caught.
        if rec["run_id"] in seen:
            raise RuntimeError(
                f"run_id {rec['run_id']} appears in two directories:\n"
                f"  {seen[rec['run_id']]}\n  {run_dir}\n"
                "These are separate executions of one identity. Load a single "
                "attempt directory rather than a tree containing several."
            )
        seen[rec["run_id"]] = run_dir
        if require_clean_git and not rec.get("git", {}).get("trustworthy", False):
            raise RuntimeError(
                f"run {rec['run_id']} was recorded from a dirty working tree; "
                "its commit hash does not identify the code that ran"
            )

        # The numerical seed is authoritative; the recorded fields are a
        # convenience. If they disagree, something rewrote a run record and the
        # analysis must not proceed on either value (D-042).
        seed = int(rec["seed"])
        recorded = rec.get("seed_partition")
        if recorded is not None:
            # Type first, then value. `bool("false")` is True and `"false"` is a
            # perfectly ordinary thing for a hand-edited or round-tripped JSON
            # record to contain, so a truthiness check would wave through the
            # exact corruption this exists to catch (D-045).
            if recorded not in SEED_PARTITIONS:
                raise RuntimeError(
                    f"run {rec['run_id']} records seed_partition={recorded!r}, "
                    f"which is not one of {sorted(SEED_PARTITIONS)}"
                )
            if recorded != seed_partition(seed):
                raise RuntimeError(
                    f"run {rec['run_id']} records seed_partition={recorded!r} but "
                    f"seed {seed} is {seed_partition(seed)!r}. The seed is "
                    "authoritative; the record has been altered."
                )
        recorded_flag = rec.get("confirmatory")
        if recorded_flag is not None:
            if type(recorded_flag) is not bool:
                raise RuntimeError(
                    f"run {rec['run_id']} records confirmatory="
                    f"{recorded_flag!r} of type {type(recorded_flag).__name__}; "
                    "it must be a JSON boolean. A truthy string would pass a "
                    "value check while meaning the opposite."
                )
            if recorded_flag != is_confirmatory(seed):
                raise RuntimeError(
                    f"run {rec['run_id']} records confirmatory={recorded_flag!r} "
                    f"but seed {seed} is {seed_partition(seed)!r}."
                )
        if require_confirmatory:
            assert_confirmatory(seed, what=f"load_runs({root!r})")

        path = run_dir / METRICS_FILE
        if not path.exists():
            continue
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if not rows:
            continue

        df = pd.DataFrame(rows)
        for col, val in _identity_columns(rec).items():
            df[col] = val
        frames.append(df)

    if not frames:
        return pd.DataFrame(columns=list(_IDENTITY_COLS))

    out = pd.concat(frames, ignore_index=True)
    # Identity first, then whatever was logged.
    lead = [c for c in _IDENTITY_COLS if c in out.columns]
    return out[lead + [c for c in out.columns if c not in lead]]


_IDENTITY_COLS = (
    "run_id",
    "unit_id",
    "config_id",
    "seed",
    "stage",
    "arm",
    "family",
    "seed_partition",
)


def _identity_columns(rec: dict[str, Any]) -> dict[str, Any]:
    unit = rec["config"]["unit"]
    cols: dict[str, Any] = {
        "run_id": rec["run_id"],
        "unit_id": rec["unit_id"],
        "config_id": rec["config_id"],
        "seed": rec["seed"],
        # Without this, a unit's five H1/H2 seeds cannot be separated from the
        # twenty behind its repair label -- they differ only by stage (D-012).
        "stage": rec.get("stage", rec["config"].get("stage", "unknown")),
        "arm": rec["config"]["arm"]["kind"],
        "family": unit["family"],
        # Which side of the pilot boundary. Carried into the frame so an
        # analysis can assert on it rather than reconstruct it from the seed.
        "seed_partition": rec.get("seed_partition", seed_partition(int(rec["seed"]))),
    }
    for k, v in unit.items():
        if k == "family":
            continue
        # Sequence-valued fields become a canonical string. A tuple in a cell
        # would be broadcast by pandas as a column of values, and would not
        # survive a groupby or a CSV round-trip.
        cols[f"unit_{k}"] = ",".join(sorted(v)) if isinstance(v, list) else v
    return cols


def _jsonable(obj: Any) -> Any:
    """Encoder for values json does not handle natively.

    Arrays are converted element-wise, never stringified. A numpy array logged
    as "[0.1 0.2 0.3]" is silently unusable -- it survives the write, loads back
    as a string, and only fails much later when a figure or a test tries to do
    arithmetic on it. Per-dimension error (Plan §10.3) is exactly this shape.
    """
    tolist = getattr(obj, "tolist", None)
    if callable(tolist):  # numpy arrays and numpy scalars both have this
        return tolist()
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    return str(obj)
