"""Imports point down only: narrate at the bottom, the labs above it, the CLI on top. Only the CLI prints."""

import ast
from pathlib import Path

PKG = "python_data_structures_and_utilities"
SRC = Path(__file__).resolve().parents[1] / "src" / PKG


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(PKG):
            # `from pkg import cli` imports the module pkg.cli, so name each imported name too
            yield node.module
            yield from (f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            yield from (a.name for a in node.names if a.name.startswith(PKG))


def test_imports_point_down():
    assert len(list(SRC.rglob("*.py"))) >= 8  # the test can't pass by finding no files
    wrong = []
    for path in SRC.rglob("*.py"):
        mods = list(_imports(ast.parse(path.read_text())))
        if path.name == "narrate.py":
            wrong += mods
        elif path.name != "cli.py":
            wrong += [m for m in mods if m == f"{PKG}.cli"]
    assert wrong == []


def test_only_the_cli_prints():
    printing = [p.name for p in SRC.rglob("*.py") if p.name != "cli.py"
                and any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"
                        for n in ast.walk(ast.parse(p.read_text())))]
    assert printing == []
