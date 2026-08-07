"""Model Registry schema (v2.9 / V3 §20 fidelity tags).

A *model* here is a versioned, auditable computational artefact — a skill
entrypoint, a physics primitive, or a chemistry law — tagged with fidelity
(reduced / mid / high). This is not the skill package registry in
``oec.skills.registry`` (that resolves skill folders on disk).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from oec.errors import OECError


class ModelRegistryError(OECError):
    """Raised for invalid registry operations."""

    default_code = "model_registry_error"


class FidelityLevel(StrEnum):
    """Fidelity ladder for registered models (V3 §20)."""

    REDUCED = "reduced"
    MID = "mid"
    HIGH = "high"


class ModelRecord(BaseModel):
    """One registry entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, description="Stable model id, e.g. chemistry.nernst_v0")
    version: str = Field(min_length=1, description="SemVer-ish version string")
    domain: str = Field(min_length=1, description="Domain label, e.g. chemistry, physics.thermal")
    fidelity: FidelityLevel
    entrypoint: str = Field(
        min_length=1,
        description="Import path module:attr, e.g. oec.chemistry.electrochemistry:nernst_potential",
    )
    title: str = Field(min_length=1)
    summary: str = ""
    assumptions: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    inputs_schema: dict[str, Any] | None = None
    outputs_schema: dict[str, Any] | None = None
    tags: tuple[str, ...] = ()
    deprecated: bool = False
    replaced_by: str | None = None

    @field_validator("id", "version", "domain", "entrypoint", "title")
    @classmethod
    def _strip_nonempty(cls, value: str) -> str:
        v = value.strip()
        if not v:
            raise ValueError("field must be non-empty")
        return v

    @property
    def key(self) -> str:
        """Composite key id@version."""
        return f"{self.id}@{self.version}"

    def to_manifest(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_manifest(cls, data: dict[str, Any]) -> ModelRecord:
        return cls.model_validate(data)


__all__ = ["FidelityLevel", "ModelRecord", "ModelRegistryError"]
