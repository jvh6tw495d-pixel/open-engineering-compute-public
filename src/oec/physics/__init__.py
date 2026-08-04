"""Public API for the OEC Physics Foundation."""

from oec.physics.conservation import aggregate_balance, evaluate_residual, evaluate_vector_residual
from oec.physics.electrical import (
    DcPowerFlowResult,
    ElectricalNetworkError,
    LineFlow,
    NetworkLine,
    dc_power_flow,
)
from oec.physics.errors import ConservationError, PhysicsError, PhysicsEvaluationError
from oec.physics.laws import BoundaryCondition, ConservationLaw, MaterialProperty, PhysicalLaw
from oec.physics.result import ConservationCheck, PhysicsResult
from oec.physics.types import PhysicsDomain, Residual, ValidityFrame

__all__ = [
    "BoundaryCondition",
    "ConservationError",
    "ConservationCheck",
    "ConservationLaw",
    "DcPowerFlowResult",
    "ElectricalNetworkError",
    "LineFlow",
    "MaterialProperty",
    "NetworkLine",
    "PhysicsDomain",
    "PhysicsError",
    "PhysicsEvaluationError",
    "PhysicsResult",
    "PhysicalLaw",
    "Residual",
    "ValidityFrame",
    "aggregate_balance",
    "dc_power_flow",
    "evaluate_residual",
    "evaluate_vector_residual",
]
