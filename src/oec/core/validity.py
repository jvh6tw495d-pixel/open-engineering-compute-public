"""Validity domain for scientific runs (v2.0 kernel)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidityDomain(BaseModel):
    """Declared applicability envelope of a method or result.

    Domain-independent: no physics/chemistry-specific fields required.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str = ""
    # Free-form constraints (e.g. "x > 0", "matrix square") — not executable code.
    constraints: list[str] = Field(default_factory=list)
    # Optional structured limits: parameter name → {min, max, unit?}
    bounds: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
