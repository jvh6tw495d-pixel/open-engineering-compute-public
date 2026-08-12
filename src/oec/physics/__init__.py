"""Public API for the OEC Physics Foundation."""

from oec.physics.conservation import aggregate_balance, evaluate_residual, evaluate_vector_residual

# Coupling (2.7) — re-exported for discovery; prefer oec.physics.coupling
from oec.physics.coupling import (  # noqa: E402
    CouplingGraph,
    run_solar_thermal_electrical_coupling,
    run_wire_i2r_coupling,
)
from oec.physics.electrical import (
    DcPowerFlowResult,
    ElectricalNetworkError,
    LineFlow,
    NetworkLine,
    dc_power_flow,
)
from oec.physics.electromagnetism import coulomb_force, parallel_plate_capacitance  # W3
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
from oec.physics.optics import snell_refracted_angle, thin_lens_image_distance  # W3
from oec.physics.pv import PV_ASSUMPTIONS, pv_energy_from_series, pv_power
from oec.physics.result import ConservationCheck, PhysicsResult
from oec.physics.service_metrics import autonomy_hours, energy_delivered
from oec.physics.statistical import ideal_gas_pressure  # W3
from oec.physics.storage import energy_based_soc_update, storage_trajectory
from oec.physics.thermal import (
    conduction_heat_rate,
    steady_conduction_balance,
    stored_thermal_energy,
)
from oec.physics.types import PhysicsDomain, Residual, ValidityFrame
from oec.physics.waves import period_from_frequency, phase_speed  # W3

__all__ = [
    "CouplingGraph",
    "run_solar_thermal_electrical_coupling",
    "run_wire_i2r_coupling",
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
    # W3 applied-sciences foundations
    "phase_speed",
    "period_from_frequency",
    "snell_refracted_angle",
    "thin_lens_image_distance",
    "coulomb_force",
    "parallel_plate_capacitance",
    "ideal_gas_pressure",
]
