"""Shared scientific kernel types (domain-independent)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MethodRef(BaseModel):
    """Declared method identity (skill method, not backend algorithm brand)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str


class BackendRef(BaseModel):
    """Computational engine observed at runtime (merit owner)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str | None = None


class Assumption(BaseModel):
    """Explicit hypothesis recorded with a scientific run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    source: str | None = None  # e.g. skill.md, ops, user
