"""Public API for the OEC Physics Foundation."""

from oec.physics.errors import ConservationError, PhysicsError, PhysicsEvaluationError
from oec.physics.laws import BoundaryCondition, ConservationLaw, MaterialProperty, PhysicalLaw
from oec.physics.result import ConservationCheck, PhysicsResult
from oec.physics.types import PhysicsDomain, Residual, ValidityFrame

__all__ = [
    "BoundaryCondition",
    "ConservationError",
    "ConservationCheck",
    "ConservationLaw",
    "MaterialProperty",
    "PhysicsDomain",
    "PhysicsError",
    "PhysicsEvaluationError",
    "PhysicsResult",
    "PhysicalLaw",
    "Residual",
    "ValidityFrame",
]
