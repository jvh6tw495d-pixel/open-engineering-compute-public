"""Multiphysics coupling — weak co-sim v0 (OEC 2.7).

Orchestrates mono-domain physics owners via a declarative graph and
staggered (Gauss–Seidel) iteration. Does not reimplement domain solvers.
"""

from __future__ import annotations

from oec.physics.coupling.checkpoint import CheckpointStore
from oec.physics.coupling.co_sim import CoupledStepResult, run_coupled
from oec.physics.coupling.convergence import ConvergenceCriteria, residual_ok
from oec.physics.coupling.electrical_thermal import (
    WireThermalState,
    analytical_wire_equilibrium_temperature,
    run_wire_i2r_coupling,
)
from oec.physics.coupling.errors import (
    CouplingConvergenceError,
    CouplingError,
    CouplingGraphError,
)
from oec.physics.coupling.graph import (
    CouplingEdge,
    CouplingGraph,
    InterfaceVariable,
    VariableDirection,
)
from oec.physics.coupling.schedule import CouplingSchedule
from oec.physics.coupling.solar_thermal_electrical import (
    SolarThermalElectricalState,
    run_solar_thermal_electrical_coupling,
)

__all__ = [
    "CheckpointStore",
    "ConvergenceCriteria",
    "CoupledStepResult",
    "CouplingConvergenceError",
    "CouplingEdge",
    "CouplingError",
    "CouplingGraph",
    "CouplingGraphError",
    "CouplingSchedule",
    "InterfaceVariable",
    "SolarThermalElectricalState",
    "VariableDirection",
    "WireThermalState",
    "analytical_wire_equilibrium_temperature",
    "residual_ok",
    "run_coupled",
    "run_solar_thermal_electrical_coupling",
    "run_wire_i2r_coupling",
]
