"""Every figure regenerable from logs only (S§W5 Fri, P§13.7).

The command reads immutable attempt directories and never trains. These tests
run it against the real tracked logs — cheap, because plotting is not compute —
and check the two properties that make "every figure from logs only" a real
guarantee rather than a hopeful one: it produces the whole registered set, and
it fails loudly when a log it needs is missing.
"""

from __future__ import annotations

import json
import os

import pytest

from bu.experiments import make_figures as MF


def test_the_registry_regenerates_every_figure(tmp_path):
    written = MF.main(figures_dir=tmp_path)
    assert len(written) >= 3, "fewer figures than the two W3 curves and the W4 gate"
    for path in written:
        assert path.exists() and path.stat().st_size > 1000, f"{path} is empty or tiny"
    # Every producer in the registry contributed at least one figure.
    names = {p.stem for p in written}
    assert any("w3" in n for n in names) and any("w4" in n for n in names)


def test_it_is_idempotent(tmp_path):
    """Regenerating twice yields the same set — figures are a function of logs."""
    first = {p.name for p in MF.main(figures_dir=tmp_path)}
    second = {p.name for p in MF.main(figures_dir=tmp_path)}
    assert first == second


@pytest.mark.parametrize("producer", list(MF.FIGURES.values()))
def test_each_producer_fails_loudly_without_its_log(producer, tmp_path, monkeypatch):
    """A missing log must raise, never silently produce a smaller set."""
    monkeypatch.chdir(tmp_path)  # an empty tree: no runs/ at all
    with pytest.raises(FileNotFoundError, match="not present"):
        producer(tmp_path / "figures")


def test_the_w4_figure_refuses_an_incomplete_grid(tmp_path, monkeypatch):
    """A curve missing seeds is not the certified result, and is refused.

    Copies the real attempt, drops one seed's rows, and checks the producer
    raises rather than plotting a four-seed mean that would look like the
    five-seed one.
    """
    import shutil
    from bu.stats.gate import RungSpec

    spec = RungSpec.for_rung(0)
    src = f"runs/w4_gate/rung-{spec.rung:02d}-{spec.spec_hash}"
    dst = tmp_path / src
    shutil.copytree(src, dst)
    rows_path = dst / "attempt-001" / "rows.json"
    rows = json.loads(rows_path.read_text())
    rows = [r for r in rows if not (r["layout"] == "uniform" and r["seed"] == 4)]
    rows_path.write_text(json.dumps(rows))

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="expected"):
        MF.w4_gate_figure(tmp_path / "figures")


def test_the_w4_figure_reads_the_attempt_select_refuses_to_guess(tmp_path, monkeypatch):
    """If two attempts exist, the figure will not silently pick one (C-010)."""
    import shutil
    from bu.stats.gate import RungSpec

    spec = RungSpec.for_rung(0)
    src = f"runs/w4_gate/rung-{spec.rung:02d}-{spec.spec_hash}"
    dst = tmp_path / src
    shutil.copytree(src, dst)
    shutil.copytree(dst / "attempt-001", dst / "attempt-002")

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="name the one you mean"):
        MF.w4_gate_figure(tmp_path / "figures")


def test_w3_rows_reconstruct_into_pilot_rows():
    """The logged rows.json round-trips into the dataclass the pilot plots."""
    from pathlib import Path

    rows = MF._load_w3_rows(Path("runs/w3_pilot/attempt-001/rows.json"))
    assert rows and all(hasattr(r, "uncertainty") for r in rows)
    assert {r.n_transitions for r in rows}  # non-empty, parsed
