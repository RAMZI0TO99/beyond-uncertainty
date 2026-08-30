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

from .streams import is_confirmatory, seed_partition
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
    "matplotlib",
    "PyYAML",
)

#: Repository associated with this installed source tree.  Provenance must not
#: depend on whichever directory happened to be current when a runner started.
#: In an editable install this is the project checkout; in a built install it
#: deliberately fails closed unless that installed tree is itself in Git.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GitState:
    commit: str
    dirty: bool
    branch: str

    @property
    def identifies_commit(self) -> bool:
        """True only when ``commit`` is an exact Git SHA-1 object name.

        ``git rev-parse`` writes failures to stderr.  The old wrapper ignored
        that return code and substituted ``UNCOMMITTED`` while ``git status``
        produced empty stdout, making a non-repository look clean.  P§13.7
        requires an exact commit hash; absence of one must fail closed.
        """
        return (
            isinstance(self.commit, str)
            and len(self.commit) == 40
            and all(ch in "0123456789abcdef" for ch in self.commit)
        )

    @property
    def trustworthy(self) -> bool:
        """True only when the code is exactly a named committed tree."""
        return self.identifies_commit and not self.dirty


def _provenance_repo(repo: str | Path | None) -> Path:
    """Resolve the repository used for provenance.

    ``None`` means the project containing this module. Any supplied path,
    including ``"."``, is an explicit caller choice and is preserved. Keeping
    those cases distinct prevents a caller that intentionally names another
    checkout from being silently rebound to this installed source tree.
    """
    if repo is None:
        return PROJECT_ROOT
    return Path(repo)


def git_state(repo: str | Path | None = None) -> GitState:
    repo_path = _provenance_repo(repo)

    def run(*args: str) -> tuple[str, bool]:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_path),
            capture_output=True,
            check=False,
        )
        # Git emits bytes. Decoding through the Windows process locale made a
        # UTF-8 source diff crash a provenance check under cp1252. Replacement
        # is safe for these status/ref names; dirty.diff below keeps raw bytes.
        output = completed.stdout.decode("utf-8", errors="replace").strip()
        return output, completed.returncode == 0

    commit_output, commit_ok = run("rev-parse", "HEAD")
    branch_output, branch_ok = run("rev-parse", "--abbrev-ref", "HEAD")
    status_output, status_ok = run("status", "--porcelain")

    # A command failure is evidence we do not know the state, never evidence
    # of a clean tree.  Ignore even plausible-looking stdout from a failed Git
    # invocation: wrappers and hooks can emit partial/stale output on failure.
    commit = commit_output if commit_ok and commit_output else "UNCOMMITTED"
    branch = branch_output if branch_ok and branch_output else "unknown"
    dirty = bool(status_output) or not (commit_ok and branch_ok and status_ok)
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
    repo: str | Path | None = None,
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

    repo_path = _provenance_repo(repo)
    git = git_state(repo_path)
    record: dict[str, Any] = {
        "run_id": config.run_id,
        "config_id": config.config_id,
        "unit_id": config.unit_id,
        # The identity of the computation, distinct from the obligation-specific
        # run_id (D-033). Historical schema-v2 records may omit this duplicate;
        # loaders reconstruct and validate it from Config.
        "fit_id": config.fit_id,
        "seed": config.seed,
        # Promoted to the top level alongside the other identity parts: the
        # stage says which experimental obligation this run discharges, and a
        # unit can owe runs to several (D-012).
        "stage": config.stage,
        # Which side of the pilot boundary this run sits on (D-034, D-040).
        # Recorded rather than inferred later: an analysis that has to
        # reconstruct it from the seed will one day forget to.
        "seed_partition": seed_partition(config.seed),
        "confirmatory": is_confirmatory(config.seed),
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
            ["git", "diff", "HEAD"], cwd=str(repo_path), capture_output=True,
            check=False,
        ).stdout
        # Preserve the exact Git bytes. In particular, never ask the host's
        # locale codec to interpret a UTF-8 patch before recording it.
        (run_dir / "dirty.diff").write_bytes(diff)

    return path


def read_run_record(run_dir: str | Path) -> dict[str, Any]:
    return json.loads((Path(run_dir) / "run.json").read_text())


def _diff_of_arm(config: Config) -> dict[str, Any]:
    """The fields the repair arm changed, so the record shows what actually ran."""
    base = dataclasses.asdict(config.unit)
    eff = dataclasses.asdict(config.effective_unit)
    return {k: v for k, v in eff.items() if base[k] != v}
