"""Fixture implementation for the mathematics.identity loader/registry test skill.

Not imported by the Sprint 01 loader (which only checks this file exists);
imported for real by the Sprint 03 Execution Service's sandboxed runner
(``oec.execution.runner``), so the return shape follows that runner's
contract: ``{"result": ..., "diagnostics": ...}``.
"""

from __future__ import annotations

from typing import Any


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    return {"result": {"value": inputs["value"]}, "diagnostics": {}}
