"""OEC Chemistry foundation (v2.8).

Slices:
  C1 — species, stoichiometry, molar balances
  C2 — concentration equilibrium (Kc / Qc)
  C3 — Arrhenius + isothermal batch extent
  C4 — Nernst cell potential (generic; not BESS SOC)
  Wave-0 — 1-D Fick species transport

Conservation residual checks route through :mod:`oec.physics.conservation`
where applicable (atom-balance residuals).
"""

from oec.chemistry.electrochemistry import (
    F_FARADAY_C_PER_MOL,
    NERNST_ASSUMPTIONS,
    NernstVoltage,
    nernst_potential,
)
from oec.chemistry.equilibrium import (
    EQUILIBRIUM_ASSUMPTIONS,
    ReactionQuotient,
    evaluate_equilibrium,
    extent_to_equilibrium_binary,
    reaction_quotient_concentration,
)
from oec.chemistry.errors import ChemistryError, ChemistryEvaluationError, StoichiometryError
from oec.chemistry.kinetics import (
    KINETICS_ASSUMPTIONS,
    R_GAS_J_PER_MOL_K,
    ArrheniusRate,
    BatchExtentStep,
    arrhenius_rate_constant,
    batch_extent_euler_step,
    power_law_rate,
)
from oec.chemistry.species import Composition, Mixture, Species
from oec.chemistry.stoichiometry import Reaction, water_formation_reaction
from oec.chemistry.transport import (
    TRANSPORT_ASSUMPTIONS,
    DiffusionFlux1D,
    fick_flux_1d,
    two_node_diffusion_step,
)

__all__ = [
    "ArrheniusRate",
    "BatchExtentStep",
    "ChemistryError",
    "ChemistryEvaluationError",
    "Composition",
    "DiffusionFlux1D",
    "EQUILIBRIUM_ASSUMPTIONS",
    "F_FARADAY_C_PER_MOL",
    "KINETICS_ASSUMPTIONS",
    "Mixture",
    "NERNST_ASSUMPTIONS",
    "NernstVoltage",
    "R_GAS_J_PER_MOL_K",
    "Reaction",
    "ReactionQuotient",
    "Species",
    "StoichiometryError",
    "TRANSPORT_ASSUMPTIONS",
    "arrhenius_rate_constant",
    "batch_extent_euler_step",
    "evaluate_equilibrium",
    "extent_to_equilibrium_binary",
    "fick_flux_1d",
    "nernst_potential",
    "power_law_rate",
    "reaction_quotient_concentration",
    "two_node_diffusion_step",
    "water_formation_reaction",
]
