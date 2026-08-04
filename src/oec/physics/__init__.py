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
from oec.physics.fluids import (
    bernoulli_balance,
    bernoulli_head,
    continuity_balance,
    continuity_mass_flow,
    darcy_weisbach_head_loss,
)
from oec.physics.harmonics import total_harmonic_distortion
from oec.physics.hybrid import hybrid_balance, hybrid_period_residual
from oec.physics.laws import BoundaryCondition, ConservationLaw, MaterialProperty, PhysicalLaw
from oec.physics.materials import (
    material_property,
    uniaxial_strain_from_deformation,
    uniaxial_stress,
)
from oec.physics.mechanics import (
    kinetic_energy,
    mechanical_energy_balance,
    potential_energy,
    uniform_acceleration_position,
    uniform_acceleration_velocity,
    work_done,
)
from oec.physics.pv import PV_ASSUMPTIONS, pv_energy_from_series, pv_power
from oec.physics.result import ConservationCheck, PhysicsResult
from oec.physics.service_metrics import autonomy_hours, energy_delivered
from oec.physics.storage import energy_based_soc_update, storage_trajectory
from oec.physics.thermal import (
    conduction_heat_rate,
    steady_conduction_balance,
    stored_thermal_energy,
)
from oec.physics.types import PhysicsDomain, Residual, ValidityFrame

__all__ = [
    "PV_ASSUMPTIONS",
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
    "autonomy_hours",
    "bernoulli_balance",
    "bernoulli_head",
    "conduction_heat_rate",
    "continuity_balance",
    "continuity_mass_flow",
    "darcy_weisbach_head_loss",
    "dc_power_flow",
    "energy_based_soc_update",
    "energy_delivered",
    "evaluate_residual",
    "evaluate_vector_residual",
    "hybrid_balance",
    "hybrid_period_residual",
    "kinetic_energy",
    "material_property",
    "mechanical_energy_balance",
    "potential_energy",
    "pv_energy_from_series",
    "pv_power",
    "steady_conduction_balance",
    "stored_thermal_energy",
    "storage_trajectory",
    "total_harmonic_distortion",
    "uniaxial_strain_from_deformation",
    "uniaxial_stress",
    "uniform_acceleration_position",
    "uniform_acceleration_velocity",
    "work_done",
]
