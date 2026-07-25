"""Fixture implementation for the mathematics.identity loader/registry test skill.

Not imported by the Sprint 01 loader (which only checks this file exists);
kept executable and correct anyway so the fixture is honest about what it
claims to do, and so it is ready to exercise the Skill Execution Service
once that lands in Sprint 03.
"""

from __future__ import annotations

from typing import Any


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    return {"value": inputs["value"]}
