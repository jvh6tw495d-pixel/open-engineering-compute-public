# OEC Chemistry API v0 (milestone 2.8)

Library surface under `oec.chemistry`. Skills are thin adapters; do not put
stoichiometry arithmetic in skill modules.

## Public surface

```python
from oec.chemistry import (
    Species, Composition, Reaction, water_formation_reaction,
    fick_flux_1d, two_node_diffusion_step,
    evaluate_equilibrium, extent_to_equilibrium_binary,
    arrhenius_rate_constant, batch_extent_euler_step,
    nernst_potential, equilibrium_constant_from_delta_g,
)
```

| Module | Role |
|--------|------|
| `species` | Species + composition (mol) |
| `stoichiometry` | Atom/charge-balanced reactions, extent ξ |
| `transport` | Fick 1-D + two-node diffusion |
| `equilibrium` | Qc/Kc, extent-to-equilibrium, ΔG°→K |
| `kinetics` | Arrhenius + batch Euler |
| `electrochemistry` | Nernst (≠ BESS SOC) |

Conservation atom residuals use `oec.physics.conservation`.

## Skills (thin)

| Skill id | Library owner |
|----------|---------------|
| `chemistry.nernst` | `nernst_potential` |
| `chemistry.fick_flux` | `fick_flux_1d` |
| `chemistry.reaction_extent` | `Reaction.apply_extent` |

## Out of scope v0

Full multi-reaction G-minimisation, CFD transport, pack SOC models.
