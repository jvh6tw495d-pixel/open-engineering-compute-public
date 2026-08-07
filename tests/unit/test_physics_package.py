"""Package-boundary tests for :mod:`oec.physics`."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import oec.physics

PHYSICS_ROOT = Path(oec.physics.__file__).parent
DENIED_PREFIXES = ("oec.mcp", "oec.api", "oec.agents", "oec.skills", "skills")
ARCHITECTURAL_LAYERS = {
    "api",
    "agents",
    "core",
    "kernel",
    "mcp",
    "modeling",
    "skills",
    "validation",
}
ALLOWED_LOWER_LAYERS = {"core", "kernel", "modeling", "validation"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_physics_public_package_imports() -> None:
    assert importlib.import_module("oec.physics") is oec.physics


def test_physics_import_graph_has_no_forbidden_or_upward_layers() -> None:
    for path in PHYSICS_ROOT.glob("*.py"):
        for imported in _imports(path):
            assert not imported.startswith(DENIED_PREFIXES), (
                f"{path.name} imports forbidden dependency {imported}"
            )
            if imported.startswith("oec."):
                layer = imported.split(".", maxsplit=2)[1]
                if layer in ARCHITECTURAL_LAYERS and layer != "physics":
                    assert layer in ALLOWED_LOWER_LAYERS, (
                        f"{path.name} imports non-allowed OEC layer {imported}"
                    )


def test_layering_guard_detects_an_oec_mcp_import(tmp_path: Path) -> None:
    violating_module = tmp_path / "violating.py"
    violating_module.write_text("from oec.mcp import envelope\n", encoding="utf-8")

    imports = _imports(violating_module)

    assert any(name.startswith(DENIED_PREFIXES) for name in imports)
