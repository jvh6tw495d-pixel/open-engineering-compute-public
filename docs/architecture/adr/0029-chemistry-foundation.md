# ADR 0029 — Chemistry foundation (v2.8)

- Status: **Accepted**
- Date: 2026-08-06
- Release: content ships in `oec==3.1.0` (closes deferred V3 §12 / v2.8 scope)
- Baseline: multiphysics weak co-sim (`oec==2.7.0`, ADR 0028)

## Context

V3 §12 defines Chemistry Complete after multiphysics: species, stoichiometry,
equilibrium, Arrhenius batch kinetics, and generic cell electrochemistry
(Nernst). PHYSICS-CATALOG also requires **species transport / diffusion v0**
as wave-0 before concentration-field cell models.

Energy-based BESS SOC (`oec.physics.storage`) remains a **different** model —
not cell electrochemistry.

## Decision

1. **Package:** top-level `src/oec/chemistry/` (sibling of `oec.physics`, not
   nested under electrical energy).
2. **Slices v0:**
   - **C1** — `species`, `stoichiometry` (atom/charge balance, extent ξ)
   - **C2** — concentration equilibrium Qc vs Kc + bisection extent
   - **C3** — Arrhenius k(T) + power-law rate + isothermal batch Euler step
   - **C4** — Nernst open-circuit potential (generic cell; not pack SOC)
   - **Wave-0** — 1-D Fick flux + two-node diffusion step
3. **Conservation:** atom-balance residuals route through
   `oec.physics.conservation.evaluate_residual` (single owner, ADR 0024).
4. **No** Gibbs free-energy minimiser, multi-reaction networks, CFD, or
   proprietary BTM product models in v0.
5. **Skills:** thin wraps deferred; library primitives first (same pattern as
   physics foundation).

## Consequences

- Chemistry imports physics conservation only for residual policy — does not
  own a second tolerance formula.
- Model Registry (ADR 0030) seeds chemistry entrypoints with fidelity tags.
- Strong coupling chemistry↔thermal remains out of scope (post-2.9).

## Related

- ADR 0024 physics · ADR 0025 units · ADR 0027 energy SOC · ADR 0028 coupling
- PHYSICS-CATALOG §14 · V3 §12
