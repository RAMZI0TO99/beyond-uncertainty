"""C-007 — the confirmatory critic-loading boundary (docs/c005_c007_spec.md).

Seeds below ``CONFIRMATORY_SEED_BASE`` are development data, permanently
excluded from the critic's training, evaluation and labels (D-034). The spec's
delta-61 resolution: **the confirmatory requirement is a property of this
boundary, not a flag threaded through call sites.** There are two roads:

* :func:`load_critic_runs` enforces the requirement INTERNALLY and exposes no
  caller-overridable exemption — the flag it hands the metrics loader is a
  literal in its body, not a parameter. It returns :class:`ConfirmatoryRuns`,
  the only type :func:`assert_critic_input` accepts.
* :func:`load_development_runs` is the separate development-data path for a
  pilot probe. It returns :class:`DevelopmentRuns`, which every critic-facing
  consumer rejects. The probe is not exempted; it is on a different road that
  dead-ends before the critic.

Records missing stage or seed metadata fail closed — refused, not defaulted
(D-034). Critic-facing consumers are discovered from
:data:`CRITIC_CONSUMER_REGISTRY`, the authoritative registry: a hardcoded list
goes stale silently, and a fix in one layer is not a fix (D-056). The registry
is checked for coherence at import, like ``schema.py``'s feature schema, so a
drifted registry fails before any test runs. Every guard raises ``ValueError``
(never a bare ``assert`` — D-059); registry drift raises ``RuntimeError`` at
import.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from numbers import Integral
from pathlib import Path
from typing import Iterable

import pandas as pd

from ..config import STAGES
from ..metrics import load_runs
from ..streams import assert_confirmatory


def _check_stage(stage: object, *, where: str, allow_pilot: bool) -> None:
    if not isinstance(stage, str) or stage == "unknown" or stage not in STAGES:
        raise ValueError(
            f"{where} carries stage {stage!r}, which is missing, 'unknown', or "
            f"not a registered stage {list(STAGES)}. Stage metadata is refused, "
            "not defaulted: a record whose provenance cannot be classified must "
            "not be computed on (C-007; D-034)"
        )
    if stage == "pilot" and not allow_pilot:
        raise ValueError(
            f"{where} carries stage 'pilot'. Pilot output travels the "
            "development road and dead-ends before the critic — the two roads "
            "never merge, even at a confirmatory seed "
            "(docs/c005_c007_spec.md; D-034)"
        )


def _check_seed(seed: object, *, where: str) -> int:
    if isinstance(seed, bool):
        raise ValueError(
            f"{where} carries boolean seed {seed!r}. `True == 1` in Python and "
            "`bool` subclasses `int`, so a boolean would silently become seed "
            "1 — a development seed wearing a type disguise (D-034)"
        )
    if not isinstance(seed, Integral):
        raise ValueError(
            f"{where} carries seed {seed!r} ({type(seed).__name__}); a usable "
            "exact integer seed is required. Seed metadata is refused, not "
            "defaulted or coerced (C-007; D-034; Sol, delta 55)"
        )
    return int(seed)


def _validate_frame(frame: pd.DataFrame, *, root: object, allow_pilot: bool) -> None:
    if len(frame) == 0:
        raise ValueError(
            f"no runs loaded from {str(root)!r}: an empty frame is returned by "
            "a loader that ran perfectly, so nothing downstream would raise — "
            "a critic boundary that loaded nothing fails closed instead "
            "(D-117 shape; D-034)"
        )
    for row in frame.itertuples(index=False):
        where = f"run {row.run_id!r}"
        _check_seed(row.seed, where=where)
        _check_stage(row.stage, where=where, allow_pilot=allow_pilot)


@dataclass(frozen=True)
class ConfirmatoryRuns:
    """The confirmatory boundary's output type — the only type
    :func:`assert_critic_input` accepts.

    ``__post_init__`` RE-verifies the provenance (defense in depth, and
    ``ValueError`` rather than assert per D-059), so a hand-constructed wrapper
    around development data fails at construction, not at first use.
    """

    frame: pd.DataFrame
    seeds: tuple[int, ...]
    stages: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.seeds or not self.stages:
            raise ValueError(
                "ConfirmatoryRuns with empty seeds or stages: a wrapper over "
                "nothing passes every downstream guard vacuously, and unknown "
                "provenance is refused, not defaulted (C-007; D-034)"
            )
        for s in self.seeds:
            _check_seed(s, where="ConfirmatoryRuns")
        assert_confirmatory(self.seeds, what="ConfirmatoryRuns")
        for stage in self.stages:
            _check_stage(stage, where="ConfirmatoryRuns", allow_pilot=False)


@dataclass(frozen=True)
class DevelopmentRuns:
    """The development road's output type.

    Every critic-facing consumer rejects this type (D-034). The pilot probe is
    not exempted from the confirmatory guard — it is on a different road that
    dead-ends before the critic (docs/c005_c007_spec.md, C-007 interface).
    """

    frame: pd.DataFrame
    seeds: tuple[int, ...]


def load_critic_runs(
    root: str | Path = "runs", *, run_ids: Iterable[str] | None = None
) -> ConfirmatoryRuns:
    """THE confirmatory-only critic loader.

    The confirmatory requirement is enforced internally — the flag handed to
    the metrics loader is a literal in this body, NOT a parameter — so the
    requirement is a property of the boundary with no caller-flippable flag
    (the spec's delta-61 resolution). Stage and seed metadata are validated
    per row and refused, not defaulted; stage 'pilot' is refused even at a
    confirmatory seed, because the two roads never merge (D-034).
    """
    try:
        frame = load_runs(root, run_ids=run_ids, require_confirmatory=True)
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"critic loading from {str(root)!r} failed on run metadata: "
            f"{exc!r}. A run record without a usable seed or stage is refused, "
            "not defaulted, and never surfaces as a bare KeyError/TypeError — "
            "an incidental crash is indistinguishable from a bug and a wrapper "
            "upstream could swallow it (C-007; D-034)"
        ) from exc
    _validate_frame(frame, root=root, allow_pilot=False)
    seeds = tuple(sorted({int(s) for s in frame["seed"]}))
    stages = tuple(sorted({str(s) for s in frame["stage"]}))
    return ConfirmatoryRuns(frame=frame, seeds=seeds, stages=stages)


load_critic_runs.__critic_consumer__ = "critic.load_runs"


def load_development_runs(
    root: str | Path = "runs", *, run_ids: Iterable[str] | None = None
) -> DevelopmentRuns:
    """The separate development-data path (a pilot probe's road).

    No confirmatory requirement — this is the road development data lawfully
    travels — but the same metadata presence checks: a record missing stage or
    seed fails closed on this road too (C-007). The returned type,
    :class:`DevelopmentRuns`, is rejected by every critic-facing consumer, so
    no single call both loads development data and reaches the critic.
    """
    try:
        frame = load_runs(root, run_ids=run_ids)
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"development loading from {str(root)!r} failed on run metadata: "
            f"{exc!r}. A run record without a usable seed or stage is refused, "
            "not defaulted, on this road too (C-007; D-034)"
        ) from exc
    _validate_frame(frame, root=root, allow_pilot=True)
    seeds = tuple(sorted({int(s) for s in frame["seed"]}))
    return DevelopmentRuns(frame=frame, seeds=seeds)


load_development_runs.__critic_consumer__ = "critic.development_runs"


def assert_critic_input(obj: object, *, consumer: str) -> None:
    """The consumer-side guard every critic-facing consumer calls on its
    loaded-runs input.

    Only the exact type :class:`ConfirmatoryRuns` passes — not a subclass, not
    a duck-typed mimic, not a bare DataFrame. Unknown provenance is refused,
    not defaulted (D-034). The consumer name must be registered with a
    critic-facing role, so the guard cannot be used anonymously and coverage
    stays registry-authoritative (D-056).
    """
    entry = CRITIC_CONSUMER_REGISTRY.get(consumer)
    if entry is None or entry.role not in _CRITIC_FACING_ROLES:
        raise ValueError(
            f"consumer {consumer!r} is not registered with a critic-facing "
            "role in CRITIC_CONSUMER_REGISTRY. Critic-facing consumers are "
            "discovered from the registry — register the consumer rather than "
            "guarding anonymously, or coverage goes stale silently (D-056)"
        )
    if type(obj) is DevelopmentRuns:
        raise ValueError(
            f"consumer {consumer!r} received DevelopmentRuns: the development "
            "path's output is rejected by every critic-facing consumer "
            "(D-034). The pilot probe is not exempted — it is on a different "
            "road that dead-ends before the critic (docs/c005_c007_spec.md)"
        )
    if type(obj) is not ConfirmatoryRuns:
        raise ValueError(
            f"consumer {consumer!r} received {type(obj).__name__}: unknown "
            "provenance fails closed. Only the confirmatory boundary's own "
            "output type, ConfirmatoryRuns, is accepted — by exact type, not "
            "by subclass or attribute shape (C-007; D-034)"
        )


@dataclass(frozen=True)
class CriticConsumer:
    name: str
    #: Dotted path, e.g. ``bu.critic.split.split_units``. Declared as a string
    #: to avoid circular imports; resolved and checked at import time.
    qualname: str
    role: str


_ROLES = ("confirmatory_loader", "critic_consumer", "development_loader")
_CRITIC_FACING_ROLES = ("confirmatory_loader", "critic_consumer")

#: The authoritative registry (docs/c005_c007_spec.md: consumers are
#: discovered FROM the registry, never from a hardcoded test list — D-056).
CRITIC_CONSUMER_REGISTRY: dict[str, CriticConsumer] = {
    "critic.load_runs": CriticConsumer(
        "critic.load_runs", "bu.critic.loading.load_critic_runs",
        "confirmatory_loader"),
    "critic.development_runs": CriticConsumer(
        "critic.development_runs", "bu.critic.loading.load_development_runs",
        "development_loader"),
    "critic.split_units": CriticConsumer(
        "critic.split_units", "bu.critic.split.split_units", "critic_consumer"),
    "critic.eligible_units": CriticConsumer(
        "critic.eligible_units", "bu.critic.split.eligible_units",
        "critic_consumer"),
}


# The run-loading tokens the coverage invariant scans for. Built from pieces so
# this module's own definitions are not false hits: the invariant is that these
# call shapes appear nowhere in bu/critic except inside this module's
# registered loader functions.
_RUN_LOADING_CALLS: tuple[str, ...] = ("load_runs", "iter_run_dirs",
                                       "read_run_record")
_METRICS_CONSTANT = "METRICS" + "_FILE"


def find_run_loading_tokens(source_text: str) -> list[str]:
    """The run-loading CALL SITES found in a module's source text.

    Public so the coverage-invariant test can (a) scan every module under
    ``src/bu/critic`` and require all hits to fall inside this module's
    registered loader functions — so adding an unregistered critic loader
    itself fails the test (D-056) — and (b) feed a synthetic offending module
    and prove the scanner has teeth: a check that cannot fail is not a check
    (D-055, D-057).

    The scan is over Python tokens, not raw text: string literals and comments
    are excluded, because the invariant targets call sites and the certified
    ``schema.py`` legitimately *mentions* the loader in its frozen docstring.
    Text that does not tokenize falls back to a plain substring scan — failing
    open on a syntax error would let a malformed module dodge the invariant.
    """
    import io
    import tokenize

    fallback = [c + "(" for c in _RUN_LOADING_CALLS] + [_METRICS_CONSTANT]
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source_text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return [t for t in fallback if t in source_text]
    found: list[str] = []
    for i, tok in enumerate(toks):
        if tok.type != tokenize.NAME:
            continue
        if tok.string in _RUN_LOADING_CALLS:
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            called = (nxt is not None and nxt.type == tokenize.OP
                      and nxt.string == "(")
            if called and (tok.string + "(") not in found:
                found.append(tok.string + "(")
        elif tok.string == _METRICS_CONSTANT and _METRICS_CONSTANT not in found:
            found.append(_METRICS_CONSTANT)
    return found


def _resolve_qualname(qualname: str):
    module_name, _, attr = qualname.rpartition(".")
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _assert_registry_is_coherent(
    registry: dict[str, CriticConsumer] | None = None,
) -> None:
    """Checked at import, like ``schema.py``'s feature schema.

    A drifted registry — a renamed function leaving a dangling qualname, a tag
    that no longer matches, an entry wearing both roads' roles — fails here,
    before any test runs, rather than at first use (D-056). ``registry`` is
    parameterisable so the checker's own teeth are testable (D-055/D-057).
    """
    reg = CRITIC_CONSUMER_REGISTRY if registry is None else registry
    qualnames = [e.qualname for e in reg.values()]
    if len(set(qualnames)) != len(qualnames):
        raise RuntimeError(
            f"duplicate qualname(s) in the critic consumer registry: "
            f"{sorted(q for q in qualnames if qualnames.count(q) > 1)}"
        )
    resolved: dict[str, object] = {}
    for key, entry in reg.items():
        if key != entry.name:
            raise RuntimeError(
                f"registry key {key!r} disagrees with entry name "
                f"{entry.name!r}; the registry is keyed by name and a mismatch "
                "means two names for one consumer"
            )
        if entry.role not in _ROLES:
            raise RuntimeError(
                f"registry entry {entry.name!r} has unknown role "
                f"{entry.role!r}; roles come from the closed set {_ROLES}"
            )
        try:
            fn = _resolve_qualname(entry.qualname)
        except (ImportError, AttributeError) as exc:
            raise RuntimeError(
                f"registry entry {entry.name!r} names qualname "
                f"{entry.qualname!r}, which does not resolve: {exc!r}. A "
                "renamed function must update the registry, not orphan it"
            ) from exc
        if not callable(fn):
            raise RuntimeError(
                f"registry entry {entry.name!r} resolves to a non-callable "
                f"{type(fn).__name__}"
            )
        tag = getattr(fn, "__critic_consumer__", None)
        if tag != entry.name:
            raise RuntimeError(
                f"registry entry {entry.name!r} resolves to a function tagged "
                f"__critic_consumer__={tag!r}; the tag and the registry must "
                "agree in both directions or coverage silently goes stale"
            )
        resolved[entry.name] = fn
    # Compared as resolved FUNCTION OBJECTS, not qualname strings: two
    # different qualnames can resolve to one function through a re-export
    # alias, and an alias bridging the two roads is exactly the "no single
    # call both loads development data and reaches the critic" violation.
    dev_fns = {id(resolved[e.name]) for e in reg.values()
               if e.role == "development_loader"}
    facing_fns = {id(resolved[e.name]) for e in reg.values()
                  if e.role in _CRITIC_FACING_ROLES}
    if dev_fns & facing_fns:
        raise RuntimeError(
            "a registered callable is both development-loading and "
            "critic-facing: no single call may both load development data and "
            "reach the critic (docs/c005_c007_spec.md; D-034)"
        )


_assert_registry_is_coherent()
