"""Shared value objects used across the skill manifest and execution models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"


class VersionedRef(BaseModel):
    """A reference to a versioned entity (a skill or a numerical method)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
