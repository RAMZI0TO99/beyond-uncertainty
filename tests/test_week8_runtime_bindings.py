"""Keep every independent recovery consumer bound to the local runtime."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
CONSUMERS = (
    "src/bu/experiments/week8_exp2a_recovery.py",
    "scripts/week8_exp2a_recovery_entrypoint.py",
    "scripts/week8_exp2a_recovery_inspector.py",
    "scripts/week8_exp2a_recovery_worker.py",
    "scripts/week8_exp2a_recovery_fit_child.py",
)


def _bindings(relative: str) -> dict[str, object]:
    # Read only the independent declarative runtime contract. No production
    # module, entrypoint, authority operation or dependency is imported here.
    tree = ast.parse((ROOT / relative).read_bytes(), filename=relative)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and (
                target.id == "WORKSPACE_ROOT"
                or target.id.startswith(("PINNED_", "EXPECTED_PINNED_"))
            ):
                selected.append(node)
    scope: dict[str, object] = {"Path": Path}
    exec(compile(ast.Module(body=selected, type_ignores=[]), relative, "exec"), scope)
    return scope


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_runtime_locations_are_inside_consolidated_workspace(consumer: str) -> None:
    bindings = _bindings(consumer)
    assert bindings["WORKSPACE_ROOT"] == WORKSPACE
    for key in (
        "PINNED_PYTHON", "PINNED_BASE_PYTHON", "PINNED_BASE_RUNTIME",
        "PINNED_PYVENV", "PINNED_VENV_SCRIPTS", "PINNED_SITE_PACKAGES",
        "PINNED_GIT", "PINNED_GIT_RUNTIME_ROOT",
    ):
        path = bindings[key]
        assert isinstance(path, Path) and path.is_absolute()
        assert path.is_relative_to(WORKSPACE), (consumer, key, path)
        assert path.exists(), (consumer, key, path)


@pytest.mark.parametrize("consumer", CONSUMERS[1:])
def test_independent_consumers_agree_on_all_runtime_fingerprints(consumer: str) -> None:
    controller = _bindings(CONSUMERS[0])
    observed = _bindings(consumer)
    expected = {k: v for k, v in controller.items() if k.startswith("EXPECTED_PINNED_")}
    actual = {k: v for k, v in observed.items() if k.startswith("EXPECTED_PINNED_")}
    assert len(expected) >= 20
    assert actual == expected
