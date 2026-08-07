---
id: materials.linear_constitutive
version: 0.1.0
status: experimental
domain: materials
title: Linear Uniaxial Constitutive (Hooke)
---

# Purpose

Evaluate the uniaxial linear-elastic constitutive relation `σ = E ε`
(Hooke's law), optionally sourcing Young's modulus `E` from the P5
engineering material property table. Thin adapter over
`oec.physics.materials` — the skill validates and adapts inputs; it
performs no physics arithmetic of its own.

# Problem definition

Given an elastic modulus (looked up or supplied) and an engineering
strain (supplied or derived from gauge length + axial deformation),
return the uniaxial stress.

# Required inputs

Exactly one modulus source:

- `material_id` (string): keyed into `oec.physics.materials.MATERIAL_TABLE`
  (e.g. `steel_astm_a36`, `aluminum_6061_t6`, `copper_c11000`); **or**
- `elastic_modulus` (`QuantityValue`, canonical `Pa`).

Exactly one strain source:

- `strain` (number, dimensionless engineering strain); **or**
- `original_length` + `deformation` (`QuantityValue`, canonical `m`).

# Official methodology

- Lookup path: `material_property(material_id, "elastic_modulus")`.
- Strain-from-deformation path:
  `uniaxial_strain_from_deformation(L0, ΔL)`.
- Stress: `uniaxial_stress(E, ε)` executes `HOOKES_LAW` (`PhysicalLaw`).

This skill is **not** a structural/elastic solver (no mesh, no equilibrium
equations) — it is the uniaxial constitutive evaluation only (P5 v0).

# Assumptions

See `UNIAXIAL_ASSUMPTIONS` / `MATERIAL_TABLE_ASSUMPTIONS` in
`oec.physics.materials`:

- Linear-elastic, uniaxial loading; small-strain regime.
- Homogeneous, isotropic material.
- Table values are room-temperature bulk engineering numbers.

# Conservation

Hooke's law is a constitutive (non-balance) relation — it does not route
through `oec.physics.conservation` (D5 reserves that owner for
inflow/outflow residuals).

# Failure conditions

- Unknown `material_id` or property name → `PhysicsEvaluationError`.
- Non-positive `original_length` → `ValueError`.

# Worked examples

See `examples/steel_uniaxial.json` and `tests/test_golden.py`: ASTM A36
steel at `ε = 0.001` yields `σ = 200 MPa`.

# References

- OEC v2.6-EXECUTION-PLAN.md, PHYSICS-CATALOG P5.
- Gere & Goodno, *Mechanics of Materials* — Hooke's law.
