# Skill inventory

**Updated:** 2026-08-06 (`oec==3.3.0` — chemistry complete + multiphysics skills + THD)
**Registry root:** `skills/`

## Summary

| Domain | Count | Notes |
|---|---|---|
| mathematics | 8 | Math IR `solve_ir`, differentiate, … |
| electrical | **8** | classic + `dc_power_flow` + **`harmonics_thd`** |
| timeseries | 16 | AR/PACF package |
| linear | 5 | |
| numerical | 2 | ode_ivp, root_system |
| statistics | 5 | |
| optimization | 12 | |
| energy | 7 | hybrid, grid_zero, pv, service_metrics, … |
| battery | 2 | soc_step, soc_trajectory |
| finance | 3 | |
| control | 2 | |
| dynamics | 2 | |
| uncertainty | 3 | |
| thermal | 1 | conduction_1d |
| mechanics | 1 | energy_1d |
| fluids | 1 | bernoulli |
| materials | 1 | linear_constitutive |
| **chemistry** | **6** | nernst, fick, reaction_extent, equilibrium, arrhenius, batch_kinetics |
| **multiphysics** | **2** | wire_i2r, solar_thermal_electrical |
| **Total** | **87** | experimental |

## Chemistry (3.2+)

| Skill id | Library |
|----------|---------|
| `chemistry.reaction_extent` | stoichiometry |
| `chemistry.fick_flux` | transport |
| `chemistry.equilibrium` | Qc/Kc |
| `chemistry.arrhenius` | kinetics |
| `chemistry.batch_kinetics` | batch Euler |
| `chemistry.nernst` | electrochemistry |

## Multiphysics (3.3)

| Skill id | Library |
|----------|---------|
| `multiphysics.wire_i2r` | `oec.physics.coupling.run_wire_i2r_coupling` |
| `multiphysics.solar_thermal_electrical` | `run_solar_thermal_electrical_coupling` |

## Physics Foundation P1–P5

| Slice | Skill |
|-------|--------|
| P1 | `electrical.dc_power_flow` (+ optional `harmonics_thd`) |
| P2 | `thermal.conduction_1d` |
| P3 | `mechanics.energy_1d` |
| P4 | `fluids.bernoulli` |
| P5 | `materials.linear_constitutive` |
