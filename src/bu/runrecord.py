"""Run records.

A run record is the answer to "what exactly produced this number?", written at
the moment the run starts rather than reconstructed later. Plan §13.7 requires
the full config, the seed, and the exact commit hash for every run.

One addition the plan does not name but which a reviewer would: the working
tree's dirty flag. A commit hash recorded from a modified tree identifies code
that was never committed, which is worse than recording nothing, because it
looks trustworthy. When the tree is dirty we say so and store the diff.
"""

from __future__ import annotations

import dataclasses
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import IDENTITY_VERSION, SCHEMA_VERSION, UNIT_IDENTITY_FIELDS, Config

#: Recorded for every run so an environment difference is visible in the record
#: rather than inferred from a failure months later.
TRACKED_PACKAGES = (
    "torch",
    "gymnasium",
    "numpy",
    "scipy",
    "statsmodels",
    "pandas",
)


@dataclass(frozen=True)
class GitState:
    commit: str
    dirty: bool
    branch: str

    @property
    def trustworthy(self) -> bool:
        """False if the code that ran is not the code at `commit`."""
        return not self.dirty


def git_state(repo: str | Path = ".") -> GitState:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

    commit = run("rev-parse", "HEAD") or "UNCOMMITTED"
    branch = run("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    dirty = bool(run("status", "--porcelain"))
    return GitState(commit=commit, dirty=dirty, branch=branch)


def package_versions() -> dict[str, str]:
    import importlib.metadata as md

    out: dict[str, str] = {}
    for name in TRACKED_PACKAGES:
        try:
            out[name] = md.version(name)
        except md.PackageNotFoundError:
            out[name] = "MISSING"
    return out


def write_run_record(
    config: Config,
    run_dir: str | Path,
    *,
    repo: str | Path = ".",
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write ``run.json`` for a run and return its path.

    Creates ``run_dir`` if needed. Refuses to overwrite an existing record --
    two runs sharing a run_id means the seed is not in the identity, which
    would silently merge distinct runs in the analysis.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run.json"
    if path.exists():
        raise FileExistsError(
            f"{path} already exists; run_id {config.run_id} is not unique"
        )

    git = git_state(repo)
    record: dict[str, Any] = {
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        "seed": config.seed,
        "schema_version": SCHEMA_VERSION,
        # Which identity registry produced unit_id. Ids are comparable only
        # within one identity version (see config.UNIT_IDENTITY_FIELDS).
        "identity_version": IDENTITY_VERSION,
        "unit_identity_fields": list(UNIT_IDENTITY_FIELDS),
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config.to_dict(),
        # What the arm actually trained, and which fields it changed. Stored
        # explicitly so a repair run is readable without re-deriving the arm.
        "effective_unit": dataclasses.asdict(config.effective_unit),
        "arm_changed": _diff_of_arm(config),
        "git": {
            "commit": git.commit,
            "branch": git.branch,
            "dirty": git.dirty,
            "trustworthy": git.trustworthy,
        },
        "env": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": package_versions(),
        },
    }
    if extra:
        record["extra"] = extra

    path.write_text(json.dumps(record, indent=2, sort_keys=True))

    # A dirty tree is recoverable only if we keep the diff.
    if git.dirty:
        diff = subprocess.run(
            ["git", "diff", "HEAD"], cwd=str(repo), capture_output=True, text=True
        ).stdout
        (run_dir / "dirty.diff").write_text(diff)

    return path


def read_run_record(run_dir: str | Path) -> dict[str, Any]:
    return json.loads((Path(run_dir) / "run.json").read_text())


def _diff_of_arm(config: Config) -> dict[str, Any]:
    """The fields the repair arm changed, so the record shows what actually ran."""
    base = dataclasses.asdict(config.unit)
    eff = dataclasses.asdict(config.effective_unit)
    return {k: v for k, v in eff.items() if base[k] != v}
