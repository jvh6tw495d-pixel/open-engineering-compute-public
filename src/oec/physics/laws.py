"""Immutable, executable domain objects for engineering physics."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.types import ValidityFrame

if TYPE_CHECKING:
    from oec.physics.result import ConservationCheck

LawEvaluator = Callable[[Mapping[str, Any]], float]


class PhysicalLaw(BaseModel):
    """A physical law with provenance and an executable evaluation path."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    id: str
    name: str
    hypotheses: tuple[Assumption, ...]
    validity: ValidityFrame
    references: tuple[str, ...]
    evaluator: LawEvaluator = Field(exclude=True, repr=False)

    def evaluate(self, state: Mapping[str, Any]) -> float:
        """Evaluate the law against an explicit state and return a scalar value."""
        try:
            return float(self.evaluator(state))
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise PhysicsEvaluationError(
                f"could not evaluate physical law {self.id!r}: {exc}",
                details={"law_id": self.id},
            ) from exc


class ConservationLaw(PhysicalLaw):
    """An executable law whose scalar evaluation is a conservation residual."""

    def check(
        self,
        state: Mapping[str, Any],
        *,
        atol: float,
        rtol: float,
        scale: float,
        unit: str,
    ) -> ConservationCheck:
        """Evaluate this law and apply the package conservation policy."""
        from oec.physics.conservation import evaluate_residual

        return evaluate_residual(self.evaluate(state), atol=atol, rtol=rtol, scale=scale, unit=unit)


class MaterialProperty(BaseModel):
    """A sourced material property valid within a declared frame."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    hypotheses: tuple[Assumption, ...]
    validity: ValidityFrame
    references: tuple[str, ...]
    value: QuantityValue


class BoundaryCondition(BaseModel):
    """An auditable boundary value attached to a target entity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    hypotheses: tuple[Assumption, ...]
    validity: ValidityFrame
    references: tuple[str, ...]
    condition_type: str
    value: QuantityValue
    target: str


__all__ = [
    "BoundaryCondition",
    "ConservationLaw",
    "LawEvaluator",
    "MaterialProperty",
    "PhysicalLaw",
]
