"""Architecture guard (ADR 0001): the inner layers import no framework.

``app/domain`` and ``app/application`` must never import fastapi, sqlalchemy,
or pydantic — that is the dependency rule made executable.
"""

from __future__ import annotations

import ast
import pathlib

FORBIDDEN = {"fastapi", "sqlalchemy", "pydantic", "pydantic_settings"}
INNER_LAYERS = ("domain", "application")

_APP_ROOT = pathlib.Path(__file__).resolve().parents[2] / "app"


def _python_files():
    for layer in INNER_LAYERS:
        yield from (_APP_ROOT / layer).rglob("*.py")


def _imported_top_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    return modules


def test_inner_layers_import_no_framework():
    offenders = {}
    for path in _python_files():
        bad = _imported_top_modules(path) & FORBIDDEN
        if bad:
            offenders[str(path.relative_to(_APP_ROOT))] = sorted(bad)
    assert not offenders, f"inner layers must stay framework-free: {offenders}"
