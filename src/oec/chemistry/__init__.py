"""OEC Chemistry foundation (v2.8 complete library surface).

Slices:
  C1 — species, formula/molar mass, stoichiometry, parse reaction
  C2 — Qc/Kc equilibrium, ΔG°→K, Kp, mole-fraction quotient
  C3 — Arrhenius + batch Euler + multi-step trajectory
  C4 — Nernst (+ concentration form; not BESS SOC)
  Wave-0 — 1-D Fick species transport

Conservation residual checks route through :mod:`oec.physics.conservation`
where applicable (atom-balance residuals).
"""

from oec.chemistry.electrochemistry import (
    F_FARADAY_C_PER_MOL,
    NERNST_ASSUMPTIONS,
    NernstVoltage,
    nernst_potential,
    nernst_potential_from_concentrations,
)
from oec.chemistry.equilibrium import (
    EQUILIBRIUM_ASSUMPTIONS,
    ReactionQuotient,
    equilibrium_constant_from_delta_g,
    evaluate_equilibrium,
    extent_to_equilibrium_binary,
    gas_delta_n,
    kp_from_kc,
    reaction_quotient_concentration,
    reaction_quotient_mole_fraction,
)
from oec.chemistry.errors import ChemistryError, ChemistryEvaluationError, StoichiometryError
from oec.chemistry.formula import (
    ATOMIC_MASS_G_PER_MOL,
    formula_to_string,
    molar_mass_g_per_mol,
    parse_formula,
)
from oec.chemistry.kinetics import (
    KINETICS_ASSUMPTIONS,
    R_GAS_J_PER_MOL_K,
    ArrheniusRate,
    BatchExtentStep,
    BatchTrajectory,
    arrhenius_rate_constant,
    batch_extent_euler_step,
    batch_extent_trajectory,
    power_law_rate,
)
from oec.chemistry.network import NetworkResult, ReactionStep, apply_reaction_network
from oec.chemistry.species import Composition, Mixture, Species
from oec.chemistry.stoichiometry import Reaction, parse_reaction, water_formation_reaction
from oec.chemistry.thermochemistry import hess_reaction_enthalpy, vanthoff_k2  # W3
from oec.chemistry.transport import (
    TRANSPORT_ASSUMPTIONS,
    DiffusionFlux1D,
    fick_flux_1d,
    two_node_diffusion_step,
)

__all__ = [
    "ATOMIC_MASS_G_PER_MOL",
    "ArrheniusRate",
    "BatchExtentStep",
    "BatchTrajectory",
    "ChemistryError",
    "ChemistryEvaluationError",
    "Composition",
    "DiffusionFlux1D",
    "EQUILIBRIUM_ASSUMPTIONS",
    "F_FARADAY_C_PER_MOL",
    "KINETICS_ASSUMPTIONS",
    "Mixture",
    "NERNST_ASSUMPTIONS",
    "NetworkResult",
    "NernstVoltage",
    "R_GAS_J_PER_MOL_K",
    "Reaction",
    "ReactionQuotient",
    "ReactionStep",
    "Species",
    "StoichiometryError",
    "TRANSPORT_ASSUMPTIONS",
    "apply_reaction_network",
    "arrhenius_rate_constant",
    "batch_extent_euler_step",
    "batch_extent_trajectory",
    "equilibrium_constant_from_delta_g",
    "evaluate_equilibrium",
    "extent_to_equilibrium_binary",
    "fick_flux_1d",
    "formula_to_string",
    "gas_delta_n",
    "kp_from_kc",
    "molar_mass_g_per_mol",
    "nernst_potential",
    "nernst_potential_from_concentrations",
    "parse_formula",
    "parse_reaction",
    "power_law_rate",
    "reaction_quotient_concentration",
    "reaction_quotient_mole_fraction",
    "two_node_diffusion_step",
    "water_formation_reaction",
    "hess_reaction_enthalpy",
    "vanthoff_k2",
]
