"""Stable result models for physics functions (not the MCP envelope)."""

from pydantic import BaseModel, ConfigDict, Field


class ConservationCheck(BaseModel):
    """Auditable outcome of applying the dimensional tolerance policy."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    residual: float
    balanced: bool
    atol: float = Field(ge=0.0)
    rtol: float = Field(ge=0.0)
    scale: float = Field(ge=0.0)
    unit: str = Field(min_length=1)


class PhysicsResult(ConservationCheck):
    """Stable physics-function result shape, distinct from the MCP envelope."""


__all__ = ["ConservationCheck", "PhysicsResult"]
