#!/usr/bin/env python3
"""Public-API docstring coverage gate (v2.5 gate item, ADR 0005/0015).

Scans the fixed list of modules that make up OEC's public surface --
the SDK entrypoint, CLI, REST API, MCP server, and the shared
execution/errors/OPS contract shapes every adapter passes through --
and checks that every public (non-underscore) module-level function,
class, and public class method has a non-empty docstring.

Static (``ast``), not import-based: the API/MCP extras are optional, and
this gate must run the same way regardless of which extras are
installed.

Usage::

    uv run python scripts/audit_public_api_docs.py
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# The public API surface (v2.5 critical-path-adjacent, distinct list):
# the single shared entrypoint, every transport adapter, and the
# contract shapes ("what shape does a caller get back") those adapters
# pass through unchanged (ADR 0005).
_PUBLIC_API_FILES: tuple[str, ...] = (
    "src/oec/sdk.py",
    "src/oec/cli/main.py",
    "src/oec/api/app.py",
    "src/oec/mcp/server.py",
    "src/oec/execution/models.py",
    "src/oec/errors.py",
    "src/oec/ops/models.py",
    "src/oec/ops/schema.py",
)

# Method names every class carries structurally (pydantic/dataclass
# machinery, dunders) that don't need their own docstring -- the class
# docstring already documents the shape.
_SKIP_METHOD_NAMES = frozenset(
    {
        "__init__",
        "__repr__",
        "__str__",
        "__eq__",
        "__hash__",
        "__post_init__",
    }
)


@dataclass
class _Finding:
    path: str
    qualname: str
    lineno: int
    kind: str  # "function" | "class" | "method"


@dataclass
class _AuditResult:
    total: int = 0
    documented: int = 0
    missing: list[_Finding] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        return 100.0 * self.documented / self.total if self.total else 100.0


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _audit_file(path: Path, result: _AuditResult) -> None:
    rel = str(path.relative_to(_ROOT)).replace("\\", "/")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if not _is_public(node.name):
                continue
            result.total += 1
            if ast.get_docstring(node):
                result.documented += 1
            else:
                result.missing.append(_Finding(rel, node.name, node.lineno, "function"))

        elif isinstance(node, ast.ClassDef):
            if not _is_public(node.name):
                continue
            result.total += 1
            if ast.get_docstring(node):
                result.documented += 1
            else:
                result.missing.append(_Finding(rel, node.name, node.lineno, "class"))

            for sub in node.body:
                if not isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                if not _is_public(sub.name) or sub.name in _SKIP_METHOD_NAMES:
                    continue
                result.total += 1
                qualname = f"{node.name}.{sub.name}"
                if ast.get_docstring(sub):
                    result.documented += 1
                else:
                    result.missing.append(_Finding(rel, qualname, sub.lineno, "method"))


def main() -> int:
    result = _AuditResult()
    for rel_path in _PUBLIC_API_FILES:
        path = _ROOT / rel_path
        if not path.exists():
            print(f"warning: {rel_path} not found, skipping", file=sys.stderr)
            continue
        _audit_file(path, result)

    print(
        f"Public API docstring coverage: {result.documented}/{result.total} "
        f"({result.coverage:.1f}%)"
    )
    if result.missing:
        print("\nMissing docstrings:")
        for finding in result.missing:
            print(f"  {finding.path}:{finding.lineno}: {finding.kind} {finding.qualname!r}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
