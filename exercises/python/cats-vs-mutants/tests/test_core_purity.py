"""The core must stay pure: no UI, no I/O, no clock, and randomness only from a seeded RNG."""

import ast
from pathlib import Path

import pytest

CORE = Path(__file__).parent.parent / "src" / "cats_vs_mutants" / "core"
FORBIDDEN = {"cats_vs_mutants.ui", "curses", "time", "datetime", "io", "os", "sys", "secrets"}


def imported_modules(tree: ast.AST) -> set[str]:
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def unseeded_random_uses(tree: ast.AST) -> list[str]:
    """Anything from the random module other than the seedable random.Random class."""
    uses = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "random":
            uses += [alias.name for alias in node.names if alias.name != "Random"]
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "random"
            and node.attr != "Random"
        ):
            uses.append(f"random.{node.attr}")
    return uses


@pytest.mark.parametrize("path", sorted(CORE.glob("*.py")), ids=lambda p: p.name)
def test_core_module_imports_nothing_impure(path):
    for module in imported_modules(ast.parse(path.read_text())):
        assert not any(module == f or module.startswith(f + ".") for f in FORBIDDEN), module


@pytest.mark.parametrize("path", sorted(CORE.glob("*.py")), ids=lambda p: p.name)
def test_core_uses_only_seeded_random_instances(path):
    # random.Random(config.seed + n) is fine; random.randint(...) uses hidden global state.
    assert unseeded_random_uses(ast.parse(path.read_text())) == []


def test_unseeded_random_detection_works():
    code = (
        "import random\nfrom random import choice\nrng = random.Random(1)\nrandom.randint(0, 4)\n"
    )
    assert sorted(unseeded_random_uses(ast.parse(code))) == ["choice", "random.randint"]
