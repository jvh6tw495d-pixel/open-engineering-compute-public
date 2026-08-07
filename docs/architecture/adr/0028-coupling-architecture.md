# ADR 0028 — Coupling architecture (weak co-sim v0)

- Status: **Accepted**
- Date: 2026-08-06
- Release: `oec==2.7.0`
- Plan: `docs/implementation/v2.7-EXECUTION-PLAN.md`

## Context

v2.6.x delivered stable mono-domain physics slices (electrical, thermal, PV,
storage, …) but no first-class **coupling engine**. v2.7 adds weak co-simulation
so domain owners remain single-owner (ADR 0024) while exchanging interface
variables with explicit units (ADR 0025).

## Decision

1. **Package:** `src/oec/physics/coupling/` (not a top-level multiphysics package).
2. **Scheme v0:** staggered / Gauss–Seidel weak coupling (not monolithic implicit).
3. **Graph:** declarative `CouplingGraph` + `CouplingEdge` + `InterfaceVariable`
   with mandatory units, direction, and per-edge `time_owner`.
4. **One clock owner** per coupled simulation (v0).
5. **Convergence:** residual `atol + rtol × scale`; max iterations; on failure
   restore checkpoint and raise `CouplingConvergenceError`.
6. **Out of scope v0:** strong/implicit coupling, chemistry, structural DOF
   solvers, AC power flow, OPF.

## Coupling readiness gate (per pair)

1. Temporal ownership
2. Coupled variables / interfaces
3. Units / explicit conversions
4. Convergence residual
5. Rollback / checkpoint

## Consequences

- Skills remain thin wrappers; physics stays in domain owners.
- Co-sim orchestrates variable exchange only — does not reimplement conduction
  or power-flow solvers.
- Schema AA stays 1.1 unless a new skill kind is registered later.

## Related

- ADR 0016 units · ADR 0020 IR · ADR 0023 AA · ADR 0024–0027 physics/energy
