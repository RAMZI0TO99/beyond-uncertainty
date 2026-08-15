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

METRICS_FILE = "metrics.jsonl"


class RunLogger:
    """Append-only JSONL metric log for a single run.

    Use as a context manager::

        with RunLogger.start(config, root="runs") as log:
            log.log(epoch=3, split="val", mse=0.021)

    ``start`` also writes the run record, so a metrics file never exists
    without the provenance that explains it.
    """

    def __init__(self, run_dir: str | Path, run_id: str) -> None:
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._fh = (self.run_dir / METRICS_FILE).open("a", buffering=1)
        self._n = 0

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
    for p in sorted(Path(root).glob("*/run.json")):
        yield p.parent


def load_runs(
    root: str | Path = "runs",
    *,
    run_ids: Iterable[str] | None = None,
    require_clean_git: bool = False,
) -> pd.DataFrame:
    """Load every run's metrics into one long-format DataFrame.

    Each row is one logged record, joined to identity columns from the run
    record: ``run_id``, ``config_id``, ``unit_id``, ``seed``, ``arm``,
    ``family``, and the unit's configuration axes prefixed with ``unit_``.

    The identity columns are the point. Every confidence interval in this
    thesis is taken over ``unit_id`` rather than over rows (Plan §10.7), and
    that is only convenient if the unit travels with the data.

    Returns an empty DataFrame with the identity columns if nothing is found,
    so callers can filter without a length check.

    Args:
        run_ids: restrict to these run ids.
        require_clean_git: raise if any loaded run was recorded from a dirty
            working tree. Off by default (development runs are routinely
            dirty); switch on for anything that reaches the thesis.
    """
    wanted = set(run_ids) if run_ids is not None else None
    frames: list[pd.DataFrame] = []

    for run_dir in iter_run_dirs(root):
        rec = read_run_record(run_dir)
        if wanted is not None and rec["run_id"] not in wanted:
            continue
        if require_clean_git and not rec["git"]["trustworthy"]:
            raise RuntimeError(
                f"run {rec['run_id']} was recorded from a dirty working tree; "
                "its commit hash does not identify the code that ran"
            )

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
    "arm",
    "family",
)


def _identity_columns(rec: dict[str, Any]) -> dict[str, Any]:
    unit = rec["config"]["unit"]
    cols: dict[str, Any] = {
        "run_id": rec["run_id"],
        "unit_id": rec["unit_id"],
        "config_id": rec["config_id"],
        "seed": rec["seed"],
        "arm": rec["config"]["arm"]["kind"],
        "family": unit["family"],
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
    """Last-resort encoder: numpy scalars and anything with .item()."""
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    return str(obj)
