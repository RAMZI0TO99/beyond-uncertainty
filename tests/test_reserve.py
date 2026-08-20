"""C-003's predeclared reserve order (D-031).

A preregistration is only worth the property that it was fixed before the thing
it governs was known. These tests assert that property mechanically rather than
trusting the file's presence.
"""

from __future__ import annotations

import inspect
import json

import pytest

from bu.config import Config
from bu.experiments import reserve as R
from bu.experiments.enumerate_units import _intended_class, canonical_units, select_sweep


def test_the_predeclaration_exists_and_is_committed():
    assert R.PREDECLARATION.exists(), (
        "the reserve order is missing; a contingency that does not exist before "
        "the shortfall is not a contingency"
    )
    order = R.load_reserve_order()
    assert order["registered_sweep"] == R.REGISTERED_SWEEP == 225


def test_the_order_is_read_not_recomputed(monkeypatch):
    """A predeclaration regenerated on demand is not one.

    If `load_reserve_order` recomputed, a later change to `select_sweep` would
    silently rewrite a commitment made in advance. This asserts it reads a file
    by making the file unreadable and requiring a refusal.
    """
    monkeypatch.setattr(R, "PREDECLARATION", R.PREDECLARATION.with_name("absent.json"))
    with pytest.raises(FileNotFoundError, match="PREDECLARATION"):
        R.load_reserve_order()


def test_every_reserve_unit_is_outside_the_registered_design():
    """A 'reserve' that was already being run would fill a shortfall with nothing."""
    registered = {
        Config(unit=u).unit_id
        for u in tuple(canonical_units())
        + tuple(select_sweep(R.REGISTERED_SWEEP, balance_against=canonical_units()))
    }
    order = R.load_reserve_order()
    overlap = registered & set(order["draw_order_all"])
    assert not overlap, f"{len(overlap)} reserve units are already in the design"


def test_the_reserve_has_no_duplicates():
    order = R.load_reserve_order()["draw_order_all"]
    assert len(order) == len(set(order))


def test_the_per_class_orders_partition_the_whole_order():
    order = R.load_reserve_order()
    by_class = order["draw_order_by_intended_class"]
    assert set(by_class["0"]) | set(by_class["1"]) == set(order["draw_order_all"])
    assert not set(by_class["0"]) & set(by_class["1"])


def test_the_per_class_order_preserves_the_admission_order():
    """Splitting by class must not reorder: the draw order IS the commitment."""
    order = R.load_reserve_order()
    whole = order["draw_order_all"]
    for cls in ("0", "1"):
        sub = order["draw_order_by_intended_class"][cls]
        assert sub == [u for u in whole if u in set(sub)]


def test_both_classes_have_reserve_depth():
    """A shortfall is always in ONE class, and the other's excess cannot repair it."""
    by_class = R.load_reserve_order()["draw_order_by_intended_class"]
    assert len(by_class["0"]) > 50 and len(by_class["1"]) > 50


def test_drawing_cannot_see_results():
    """D-031's requirement made structural: the drawer is given no outcome data.

    `next_reserve_units` takes a class and a count. There is no parameter through
    which critic performance, repair-verified labels or observed class survival
    could reach it -- so 'without inspecting critic performance' is a property of
    the signature rather than a rule someone must remember.
    """
    params = set(inspect.signature(R.next_reserve_units).parameters)
    assert params == {"intended_class", "n"}


def test_drawing_returns_the_predeclared_prefix():
    by_class = R.load_reserve_order()["draw_order_by_intended_class"]
    assert R.next_reserve_units(0, 3) == tuple(by_class["0"][:3])
    assert R.next_reserve_units(1, 5) == tuple(by_class["1"][:5])


def test_over_drawing_is_refused_rather_than_extended():
    """Extending the reserve after seeing a shortfall is choosing, not drawing."""
    depth = len(R.load_reserve_order()["draw_order_by_intended_class"]["0"])
    with pytest.raises(ValueError, match="chosen with knowledge of the result"):
        R.next_reserve_units(0, depth + 1)


def test_the_admission_order_is_reproducible_on_a_short_prefix():
    """The generator still yields the committed order -- checked cheaply.

    Only a short prefix, because the point is to detect drift in `select_sweep`,
    not to recompute the whole predeclaration on every test run.
    """
    drawn = R.incremental_draw_order(R.REGISTERED_SWEEP, R.REGISTERED_SWEEP + 6)
    ids = [Config(unit=u).unit_id for u in drawn]
    assert ids == R.load_reserve_order()["draw_order_all"][:len(ids)], (
        "the registered selection no longer reproduces the predeclared order; "
        "the predeclaration stands, and the discrepancy needs explaining"
    )


def test_a_selection_that_removed_units_would_be_refused(monkeypatch):
    """Could `incremental_draw_order` fail? Yes -- and here is the case."""
    canonical = canonical_units()
    full = list(select_sweep(R.REGISTERED_SWEEP + 3, balance_against=canonical))

    def shrinking(n, *, balance_against=None):
        return full[: R.REGISTERED_SWEEP + 3 - (n - R.REGISTERED_SWEEP)]

    monkeypatch.setattr(R, "select_sweep", shrinking)
    with pytest.raises(RuntimeError, match="removed"):
        R.incremental_draw_order(R.REGISTERED_SWEEP, R.REGISTERED_SWEEP + 2)


# --- the guards Sol required before any draw (delta 44) ---------------------


def test_a_negative_count_is_refused_rather_than_slicing_the_reserve():
    """Measured: next_reserve_units(0, -1) returned 119 of 120 units.

    A list slice with a negative index is silently almost-everything. Asking for
    -1 unit and receiving the entire reserve minus one is the worst possible
    reading of an out-of-range request.
    """
    with pytest.raises(ValueError, match="must not be negative"):
        R.next_reserve_units(0, -1)


@pytest.mark.parametrize("bad", [2, -1, 7])
def test_a_class_outside_the_two_intended_ones_is_refused(bad):
    with pytest.raises(ValueError, match="not one of"):
        R.next_reserve_units(bad, 1)


@pytest.mark.parametrize("bad", [1.5, "3", None, True])
def test_a_non_integer_count_is_refused(bad):
    with pytest.raises(TypeError):
        R.next_reserve_units(0, bad)


@pytest.mark.parametrize("bad", [1.0, "0", None])
def test_a_non_integer_class_is_refused(bad):
    with pytest.raises(TypeError):
        R.next_reserve_units(bad, 1)


def test_zero_is_a_legitimate_draw():
    """Refusing negatives must not also refuse the empty draw."""
    assert R.next_reserve_units(0, 0) == ()


def test_an_edited_predeclaration_is_refused_by_digest(tmp_path, monkeypatch):
    """THE guard that makes this a predeclaration rather than a file.

    Without it, editing the JSON silently redefines a commitment made in
    advance: the file would still load, still be self-consistent, and still be
    called the predeclared order.
    """
    import json

    order = R.load_reserve_order()
    order["draw_order_all"][0] = "tampered0000"
    forged = tmp_path / "reserve_order.json"
    forged.write_text(json.dumps(order, indent=2), encoding="utf-8")
    monkeypatch.setattr(R, "PREDECLARATION", forged)
    with pytest.raises(ValueError, match="not the same document"):
        R.load_reserve_order()


def test_the_frozen_digest_matches_the_committed_file():
    """If this fails, either the file changed or the constant was not updated."""
    import hashlib

    actual = hashlib.sha256(R.PREDECLARATION.read_bytes()).hexdigest()
    assert actual == R.PREDECLARED_DIGEST


@pytest.mark.parametrize("mutate, match", [
    (lambda o: o.pop("n_reserve"), "missing field"),
    (lambda o: o.__setitem__("registered_sweep", 999), "different point"),
    (lambda o: o.__setitem__("n_reserve", 7), "n_reserve says"),
    # n_reserve is bumped too, so the DUPLICATE clause is what fires rather
    # than the count clause -- otherwise this would pass without ever
    # reaching the check it names.
    (lambda o: (o["draw_order_all"].append(o["draw_order_all"][0]),
                o.__setitem__("n_reserve", o["n_reserve"] + 1)), "duplicate"),
    (lambda o: o["draw_order_by_intended_class"].__setitem__("2", []), "keyed"),
])
def test_a_structurally_invalid_predeclaration_is_refused(tmp_path, monkeypatch, mutate, match):
    """Schema, counts, uniqueness, partition and sweep, each checked."""
    import json

    order = R.load_reserve_order()
    mutate(order)
    forged = tmp_path / "reserve_order.json"
    forged.write_text(json.dumps(order, indent=2), encoding="utf-8")
    monkeypatch.setattr(R, "PREDECLARATION", forged)
    monkeypatch.setattr(
        R, "PREDECLARED_DIGEST",
        __import__("hashlib").sha256(forged.read_bytes()).hexdigest(),
    )
    with pytest.raises(ValueError, match=match):
        R.load_reserve_order()


def test_a_class_order_that_does_not_partition_the_whole_is_refused(tmp_path, monkeypatch):
    """A shortfall must not be fillable from a unit the predeclaration never named."""
    import hashlib, json

    order = R.load_reserve_order()
    order["draw_order_by_intended_class"]["0"] = order["draw_order_by_intended_class"]["0"][:-1]
    forged = tmp_path / "reserve_order.json"
    forged.write_text(json.dumps(order, indent=2), encoding="utf-8")
    monkeypatch.setattr(R, "PREDECLARATION", forged)
    monkeypatch.setattr(R, "PREDECLARED_DIGEST",
                        hashlib.sha256(forged.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="do not partition"):
        R.load_reserve_order()
