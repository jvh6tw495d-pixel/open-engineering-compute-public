# OEC Chemistry API (module complete foundation)

Library: `oec.chemistry`. Skills are thin adapters.

## Install / import

```python
from oec.chemistry import (
    Species,
    Composition,
    Mixture,
    Reaction,
    parse_formula,
    parse_reaction,
    molar_mass_g_per_mol,
    water_formation_reaction,
    fick_flux_1d,
    two_node_diffusion_step,
    evaluate_equilibrium,
    extent_to_equilibrium_binary,
    equilibrium_constant_from_delta_g,
    kp_from_kc,
    reaction_quotient_mole_fraction,
    arrhenius_rate_constant,
    batch_extent_euler_step,
    batch_extent_trajectory,
    nernst_potential,
    nernst_potential_from_concentrations,
)
```

## Modules

| Module | Role |
|--------|------|
| `formula` | Parse `H2O`-style formulas; conventional molar mass |
| `species` | Species, composition, mixture mass / element inventory |
| `stoichiometry` | Balanced reactions, extent ξ, `parse_reaction` |
| `transport` | Fick 1-D + two-node diffusion |
| `equilibrium` | Qc/Kc, ΔG°→K, Kp, mole-fraction Q |
| `kinetics` | Arrhenius, power-law rate, batch Euler + trajectory |
| `electrochemistry` | Nernst (+ concentration form) |

## Skills

| Skill | Owner |
|-------|--------|
| `chemistry.reaction_extent` | stoichiometry / water formation |
| `chemistry.fick_flux` | transport |
| `chemistry.equilibrium` | Qc/Kc isomerisation check |
| `chemistry.arrhenius` | Arrhenius k(T) |
| `chemistry.batch_kinetics` | A→B batch Euler step |
| `chemistry.nernst` | Nernst E(Q) |

## Explicitly out of scope (still)

- Full multi-reaction Gibbs free-energy minimisation
- Parenthesized formulas `(OH)2`, mechanism reduction
- CFD / multi-D transport
- Pack/BESS energy SOC (`oec.physics.storage`)
- Strong chemistry↔thermal multiphysics
