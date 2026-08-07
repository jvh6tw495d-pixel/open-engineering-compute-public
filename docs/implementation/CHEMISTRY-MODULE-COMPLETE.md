# Chemistry module — complete foundation (local)

**Package:** `oec==3.2.0`
**Date:** 2026-08-06

## Claim

`oec.chemistry` is a **finished foundation module** for OEC: every V3 §12
slice (C1–C4 + transport wave-0) has library primitives **and** thin skills
with golden tests. Not a research-grade kinetic/thermo suite.

## Surface

| Area | Library | Skill(s) |
|------|---------|----------|
| Formula / mass | `formula`, `Species.from_formula_string` | (via reaction_extent / mix) |
| Stoichiometry | `Reaction`, `parse_reaction`, extent | `chemistry.reaction_extent` |
| Transport | Fick 1-D, two-node | `chemistry.fick_flux` |
| Equilibrium | Qc/Kc, ΔG→K, Kp, x-activities | `chemistry.equilibrium` |
| Kinetics | Arrhenius, batch Euler, trajectory | `chemistry.arrhenius`, `batch_kinetics` |
| Electrochemistry | Nernst (+ c-form) | `chemistry.nernst` |

## Deferred (honest)

- Multi-reaction Gibbs minimiser
- Parenthesized formulas
- Strong multiphysics with chemistry
- Publish to GitHub (your step later)

## Terminal

```text
CHEMISTRY_MODULE: FOUNDATION_COMPLETE
PACKAGE: oec==3.2.0
PUBLIC_PUSH: DEFERRED_HUMAN
```
