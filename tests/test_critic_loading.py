"""C-007 — the confirmatory critic-loading boundary, the two roads, and the
registry-authoritative coverage invariant (docs/c005_c007_spec.md; D-034,
D-056).

Run directories are built for real via RunLogger.start into tmp_path (the
pattern test_critic_schema.py already uses), so planted sub-1000-seed records
travel the same loading path as everything else. Every fixture is synthetic;
development seeds appear only where a refusal is the property under test.
"""

from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import bu.critic
from bu.config import Config, UnitSpec
from bu.critic.balance import CANONICAL_SPLITS
from bu.critic.loading import (
    CRITIC_CONSUMER_REGISTRY,
    ConfirmatoryRuns,
    CriticConsumer,
    DevelopmentRuns,
    _assert_registry_is_coherent,
    assert_critic_input,
    find_run_loading_tokens,
    load_critic_runs,
    load_development_runs,
)
from bu.critic.split import (
    ObservedTarget,
    SplitCandidate,
    SplitFloor,
    SplitTargets,
    eligible_units,
    split_units,
)
from bu.metrics import RunLogger


def _run(root, seed: int, stage: str = "exp1") -> Config:
    cfg = Config(unit=UnitSpec(n_transitions=100), seed=seed, stage=stage)
    with RunLogger.start(cfg, root=root) as log:
        log.log(epoch=0, split="val", error=0.5)
    return cfg


def _resolve(qualname: str):
    module_name, _, attr = qualname.rpartition(".")
    return getattr(importlib.import_module(module_name), attr)


def _dev_runs() -> DevelopmentRuns:
    return DevelopmentRuns(frame=pd.DataFrame({"seed": [999]}), seeds=(999,))


def _confirmatory_wrapper() -> ConfirmatoryRuns:
    return ConfirmatoryRuns(frame=pd.DataFrame({"seed": [1000]}),
                            seeds=(1000,), stages=("exp1",))


def _targets():
    return SplitTargets(
        observed={s: {0: ObservedTarget(0, 4), 1: ObservedTarget(0, 4)}
                  for s in CANONICAL_SPLITS},
        floors={"held_out": SplitFloor(0, 0)},
    )


# --- the boundary: confirmatory-only, no caller-flippable flag ---------------


def test_confirmatory_runs_load_through_the_boundary(tmp_path):
    """The grounding case every refusal below rests on: well-formed
    confirmatory directories load, and the wrapper passes the consumer guard."""
    _run(tmp_path, 1000)
    _run(tmp_path, 1001)
    runs = load_critic_runs(tmp_path)
    assert type(runs) is ConfirmatoryRuns
    assert len(runs.frame) == 2
    assert runs.seeds == (1000, 1001)
    assert_critic_input(runs, consumer="critic.split_units")  # must not raise


def test_a_planted_development_seed_record_cannot_reach_the_critic_boundary(
        tmp_path):
    """A positive refusal, not an absence-of-failure (D-054): the boundary
    refuses the whole load rather than silently filtering to fewer runs than
    it reports."""
    _run(tmp_path, 999)
    _run(tmp_path, 1000)
    with pytest.raises(ValueError, match="development seeds") as exc:
        load_critic_runs(tmp_path)
    assert "999" in str(exc.value), "the refusal must name the offending seed"


def test_the_confirmatory_requirement_is_not_a_caller_flag(tmp_path):
    """The spec's delta-61 resolution: the requirement is a property of the
    boundary. Neither polarity of a flag exists — passing one is a TypeError,
    not a request."""
    _run(tmp_path, 1000)
    with pytest.raises(TypeError):
        load_critic_runs(tmp_path, require_confirmatory=True)
    with pytest.raises(TypeError):
        load_critic_runs(tmp_path, require_confirmatory=False)


@pytest.mark.parametrize("loader", [load_critic_runs, load_development_runs],
                         ids=["confirmatory_road", "development_road"])
def test_missing_stage_metadata_fails_closed_at_the_boundary(tmp_path, loader):
    """metrics defaults an absent stage to 'unknown'; the boundary refuses
    that default rather than inheriting it — on both roads."""
    cfg = _run(tmp_path, 1000)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    del data["stage"]
    del data["config"]["stage"]
    record.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="'unknown'"):
        loader(tmp_path)


def test_missing_or_noninteger_seed_fails_closed(tmp_path):
    """A tampered record without a usable seed surfaces as a positive
    ValueError from the boundary, never a bare KeyError a wrapper upstream
    could swallow."""
    cfg = _run(tmp_path, 1000)
    record = tmp_path / cfg.run_id / "run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    del data["seed"]
    record.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata"):
        load_critic_runs(tmp_path)


def test_pilot_stage_is_refused_even_at_a_confirmatory_seed(tmp_path):
    """Seed-only checking would let exploratory pilot output into the critic
    because someone ran a probe at a high seed. The roads never merge."""
    _run(tmp_path, 1000, stage="pilot")
    with pytest.raises(ValueError, match="pilot"):
        load_critic_runs(tmp_path)


def test_an_empty_load_is_refused_not_wrapped(tmp_path):
    """A boundary that loaded nothing ran perfectly, and a wrapper over
    nothing passes every downstream guard vacuously — so it fails closed."""
    with pytest.raises(ValueError, match="no runs loaded"):
        load_critic_runs(tmp_path)
    with pytest.raises(ValueError, match="no runs loaded"):
        load_development_runs(tmp_path)


def test_boundary_provenance_matches_its_frame(tmp_path):
    """Wrapper metadata cross-checked against the CONTENT consumers actually
    receive, not against itself (D-072)."""
    _run(tmp_path, 1000, stage="exp1")
    _run(tmp_path, 1001, stage="exp2a")
    runs = load_critic_runs(tmp_path)
    assert runs.seeds == tuple(sorted({int(s) for s in runs.frame["seed"]}))
    assert runs.stages == tuple(sorted({str(s) for s in runs.frame["stage"]}))
    assert set(runs.stages) == {"exp1", "exp2a"}, "fixture must span stages"


# --- the two roads ------------------------------------------------------------


def test_the_development_path_loads_development_data(tmp_path):
    """The probe is not exempted from the guard — it is on a different road.
    Over-tightening this road would push probes to hack the confirmatory one."""
    _run(tmp_path, 999, stage="pilot")
    runs = load_development_runs(tmp_path)
    assert type(runs) is DevelopmentRuns
    assert runs.seeds == (999,)
    assert len(runs.frame) == 1


_CRITIC_FACING = [e for e in CRITIC_CONSUMER_REGISTRY.values()
                  if e.role != "development_loader"]


@pytest.mark.parametrize("entry", _CRITIC_FACING, ids=lambda e: e.name)
def test_every_registered_critic_consumer_rejects_development_input(
        entry, tmp_path):
    """Discovery is FROM the registry, so a consumer added there without a
    demonstrated rejection path fails this test rather than passing because it
    was never exercised. One consumer passing is not evidence about another
    (D-055, D-056)."""
    with pytest.raises(ValueError):
        assert_critic_input(_dev_runs(), consumer=entry.name)

    dev_candidate = SplitCandidate(
        unit_id="a", comparison_group_id="g1", intended_class="estimation",
        observed_label=0, stage="exp1", label_seeds=(999,),
    )
    if entry.name == "critic.load_runs":
        _run(tmp_path, 999)
        with pytest.raises(ValueError, match="development seeds"):
            load_critic_runs(tmp_path)
    elif entry.name == "critic.split_units":
        with pytest.raises(ValueError, match="development seeds"):
            split_units([dev_candidate], targets=_targets())
    elif entry.name == "critic.eligible_units":
        with pytest.raises(ValueError, match="development seeds"):
            eligible_units([dev_candidate], {"a": "train"}, {"a": (0,)})
    else:
        pytest.fail(
            f"registered critic-facing consumer {entry.name!r} has no "
            "demonstrated development-rejection path; add one here before "
            "extending the registry (D-056)"
        )


def test_no_registered_call_both_loads_development_data_and_reaches_the_critic():
    """The roles partition, and behaviourally the development road's output
    type is rejected by the consumer guard — no bridging wrapper exists."""
    roles = {e.role for e in CRITIC_CONSUMER_REGISTRY.values()}
    assert roles <= {"confirmatory_loader", "critic_consumer",
                     "development_loader"}
    dev_entries = [e for e in CRITIC_CONSUMER_REGISTRY.values()
                   if e.role == "development_loader"]
    assert dev_entries, "the development road must be registered, not implicit"
    dev_fns = {_resolve(e.qualname) for e in dev_entries}
    facing_fns = {_resolve(e.qualname) for e in _CRITIC_FACING}
    assert not dev_fns & facing_fns
    assert load_development_runs in dev_fns
    with pytest.raises(ValueError, match="development"):
        assert_critic_input(_dev_runs(), consumer="critic.split_units")


# --- consumer-side rejection: exact type, registered name --------------------


@pytest.mark.parametrize("obj", [
    pd.DataFrame({"seed": [1000]}),
    None,
    SimpleNamespace(frame=pd.DataFrame(), seeds=(1000,), stages=("exp1",)),
], ids=["bare_dataframe", "none", "duck_typed"])
def test_bare_dataframes_and_unknown_types_are_refused_by_assert_critic_input(
        obj):
    """Unknown provenance fails closed: attribute sniffing or a raw frame
    must not pass for the boundary's own output type."""
    assert_critic_input(_confirmatory_wrapper(),
                        consumer="critic.split_units")  # grounding
    with pytest.raises(ValueError, match="provenance"):
        assert_critic_input(obj, consumer="critic.split_units")


def test_a_confirmatory_runs_subclass_is_refused():
    """Exact type, not isinstance: a subclass could override behaviour while
    inheriting the label."""

    class Mimic(ConfirmatoryRuns):
        pass

    mimic = Mimic(frame=pd.DataFrame({"seed": [1000]}), seeds=(1000,),
                  stages=("exp1",))
    with pytest.raises(ValueError, match="provenance"):
        assert_critic_input(mimic, consumer="critic.split_units")


def test_assert_critic_input_requires_a_registered_consumer_name():
    """The guard cannot be used anonymously, or coverage stops being
    registry-authoritative (D-056). A development-road name is registered but
    not critic-facing, and is refused too."""
    with pytest.raises(ValueError, match="not registered"):
        assert_critic_input(_confirmatory_wrapper(), consumer="something_new")
    with pytest.raises(ValueError, match="not registered"):
        assert_critic_input(_confirmatory_wrapper(),
                            consumer="critic.development_runs")


@pytest.mark.parametrize("seeds,stages,match", [
    ((999,), ("exp1",), "development seeds"),
    ((999, 1000), ("exp1",), "development seeds"),
    ((1000,), ("pilot",), "pilot"),
    ((1000,), ("unknown",), "stage"),
    ((), ("exp1",), "empty"),
    ((True,), ("exp1",), "boolean seed"),
    (("1000",), ("exp1",), "exact integer"),
])
def test_confirmatory_wrapper_cannot_be_hand_built_around_development_data(
        seeds, stages, match):
    """The type is a check, not a label: hand-construction around development
    or unclassifiable data fails at construction, not at first use."""
    assert _confirmatory_wrapper() is not None  # the well-formed case builds
    with pytest.raises(ValueError, match=match):
        ConfirmatoryRuns(frame=pd.DataFrame({"seed": list(seeds)}),
                         seeds=seeds, stages=stages)


# --- the registry is authoritative, and its checker has teeth ----------------


def test_registry_is_coherent_and_tags_match():
    """Both directions: every registry entry resolves to a callable carrying
    its tag, and every tagged callable in the critic package is registered —
    a tagged-but-unregistered consumer would escape the parametrised
    rejection test above."""
    package_dir = Path(bu.critic.__file__).parent
    module_names = sorted(p.stem for p in package_dir.glob("*.py")
                          if p.stem != "__init__")
    assert module_names, "the critic package scan found nothing"
    tagged: dict[str, set[str]] = {}
    for name in module_names:
        module = importlib.import_module(f"bu.critic.{name}")
        for obj in vars(module).values():
            tag = getattr(obj, "__critic_consumer__", None)
            if callable(obj) and tag is not None:
                tagged.setdefault(tag, set()).add(
                    f"{obj.__module__}.{obj.__name__}")
    assert set(tagged.keys()) == set(CRITIC_CONSUMER_REGISTRY.keys()), (
        "tagged functions and registry entries disagree: a consumer exists "
        "on one side only"
    )
    for name, entry in CRITIC_CONSUMER_REGISTRY.items():
        fn = _resolve(entry.qualname)
        assert getattr(fn, "__critic_consumer__", None) == name
        assert entry.qualname in tagged[name]


@pytest.mark.parametrize("registry,match", [
    ({"x": CriticConsumer("x", "bu.critic.loading.nonexistent",
                          "critic_consumer")}, "does not resolve"),
    ({"y": CriticConsumer("y", "bu.critic.balance.balance",
                          "critic_consumer")}, "tagged"),
    ({"a": CriticConsumer("a", "bu.critic.loading.load_critic_runs",
                          "confirmatory_loader"),
      "b": CriticConsumer("b", "bu.critic.loading.load_critic_runs",
                          "critic_consumer")}, "duplicate qualname"),
    ({"k": CriticConsumer("other", "bu.critic.loading.load_critic_runs",
                          "confirmatory_loader")}, "disagrees"),
    ({"critic.load_runs": CriticConsumer(
        "critic.load_runs", "bu.critic.loading.load_critic_runs",
        "vibes")}, "unknown role"),
], ids=["dangling_qualname", "tag_mismatch", "duplicate_qualname",
        "key_name_mismatch", "unknown_role"])
def test_a_drifted_registry_fails_the_import_time_check(registry, match):
    """The checker itself can fail (D-055/D-057): each drift shape raises."""
    _assert_registry_is_coherent()  # the real registry passes
    with pytest.raises(RuntimeError, match=match):
        _assert_registry_is_coherent(registry)


def test_an_unregistered_critic_loader_fails_the_coverage_invariant():
    """Run-loading call sites may exist only inside loading.py's registered
    loader functions. Adding bu/critic/anything.py with its own run-loading
    call — or an unregistered helper inside loading.py — fails this scan, so
    a new loader cannot dodge the registry silently (D-056). The scanner's
    own teeth are proven on synthetic offending sources (D-055/D-057)."""
    registered_spans = []
    for entry in CRITIC_CONSUMER_REGISTRY.values():
        fn = _resolve(entry.qualname)
        if fn.__module__ == "bu.critic.loading":
            lines, start = inspect.getsourcelines(fn)
            registered_spans.append(range(start, start + len(lines)))
    assert registered_spans, "no registered loader functions in loading.py"

    package_dir = Path(bu.critic.__file__).parent
    scanned = 0
    for path in sorted(package_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        scanned += 1
        hits = find_run_loading_tokens(text)
        if path.name != "loading.py":
            assert hits == [], (
                f"{path.name} contains run-loading call site(s) {hits} outside "
                "the C-007 boundary; register a loader in loading.py instead"
            )
            continue
        assert hits, "anti-vacuity: the boundary itself must show call sites"
        # The source OUTSIDE the registered loader functions must be clean:
        # an unregistered helper inside loading.py is as much a dodge as a
        # new module.
        covered = set()
        for span in registered_spans:
            covered |= set(span)
        remainder = "\n".join(
            line for lineno, line in enumerate(text.splitlines(), start=1)
            if lineno not in covered
        )
        assert find_run_loading_tokens(remainder) == [], (
            "loading.py contains run-loading call site(s) outside its "
            "registered loader functions"
        )
    assert scanned >= 4, "the package scan missed modules"

    # The scanner can fail: synthetic offending modules are flagged, and a
    # clean source yields nothing.
    assert find_run_loading_tokens("df = load_runs('runs')") == ["load_runs("]
    synthetic = ("from bu.metrics import iter_run_dirs\n"
                 "for d in iter_run_dirs(root):\n    pass\n")
    assert "iter_run_dirs(" in find_run_loading_tokens(synthetic)
    assert "METRICS" + "_FILE" in find_run_loading_tokens(
        "path = run_dir / METRICS" + "_FILE")
    assert find_run_loading_tokens("x = 1  # nothing loaded here") == []
