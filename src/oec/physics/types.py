"""Cross-cutting immutable types for the public physics API."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class PhysicsDomain(StrEnum):
    """Engineering domains covered by the Physics Foundation."""

    ELECTRICAL = "electrical"
    THERMAL = "thermal"
    MECHANICS = "mechanics"
    FLUIDS = "fluids"
    MATERIALS = "materials"


class ValidityFrame(BaseModel):
    """Auditable statement of where a law or datum is valid."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    domains: tuple[PhysicsDomain, ...]
    description: str
    constraints: tuple[str, ...] = ()

    @field_validator("domains")
    @classmethod
    def _require_domain(cls, value: tuple[PhysicsDomain, ...]) -> tuple[PhysicsDomain, ...]:
        if not value:
            raise ValueError("validity frame must declare at least one domain")
        return value


class Residual(BaseModel):
    """A finite residual magnitude paired with its canonical unit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float
    unit: str


__all__ = ["PhysicsDomain", "Residual", "ValidityFrame"]
