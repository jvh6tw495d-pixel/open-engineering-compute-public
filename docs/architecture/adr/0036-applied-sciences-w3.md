# ADR 0036: Applied Sciences Foundations (W3)

- **Status:** accepted
- **Date:** 2026-08-10
- **Phase:** Framework W3 after Experiment Engine (W2)
- **Related:** ADR 0024–0029 (physics/chemistry foundations), ADR 0034 (experiment)

## Context

W0–W2 froze framework layers and the Experiment Engine. Applied sciences already
had P1–P5 physics v0 and chemistry C1–C4 library slices, but lacked first-class
coverage for waves, geometrical optics, elementary EM, ideal-gas statistical
physics, and thermochemistry (van't Hoff / Hess) as **skills** that compose under
`ExperimentSpec`.

## Decision

1. **Claim:** "Applied Sciences Foundations v0" — not industrial FEM, Maxwell
   solvers, multi-rxn Gibbs, or full continuum acoustics/optics.
2. **New physics modules:** `waves`, `optics`, `electromagnetism`, `statistical`
   under `src/oec/physics/`.
3. **New chemistry module:** `thermochemistry` under `src/oec/chemistry/`.
4. **Skills (9):**
   - `waves.phase_speed`
   - `optics.snell`, `optics.thin_lens`
   - `em.coulomb`, `em.parallel_plate_capacitor`
   - `statistical_physics.ideal_gas`
   - `mechanics.kinematics_1d` (exposes existing P3 kinematics)
   - `chemistry.vanthoff`, `chemistry.hess_enthalpy`
5. **Experiments** under `experiments/w3_*.json` demonstrate multi-skill and
   metric gates without inventing numbers.
6. **Engineering domains** (electrical/energy/control) remain applications of
   foundations; no new silo packages in W3.

## Consequences

- Core install stays free of AI extras.
- MCP/REST/SDK expose new skills automatically via registry.
- W4/W5 re-homologation of neural/evo still separate; W3 does not depend on them.

## Non-goals

- Full EM wave solvers, ray-tracing engines, statistical ensembles
- Multi-reaction Gibbs free-energy minimisation
- Persistent scientific harness (POST-OEC)
