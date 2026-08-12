# ADR 0042: NEAT / HyperNEAT Exclusion from 3.6 DoD

- **Status:** accepted
- **Date:** 2026-08-12
- **Phase:** Scientific AI S0 / S4
- **Related:** ADR 0031, 0033, 0037, 0040

## Context

ADR 0037 deferred NEAT / HyperNEAT from W5-MVP. Scientific AI Completion must
either implement a governed NEAT path or **explicitly exclude** it from the
3.6 functional-completeness claim so residual work is not silent.

NEAT-class systems require genotype encoding, speciation, complexification, and
careful fitness contracts. A half-implemented skill would violate OEC’s
fail-closed / no-stub policy.

## Decision

1. **NEAT, HyperNEAT, and related topology-evolution engines are out of scope
   for `oec==3.6.x` Scientific AI DoD.**
2. Existing coverage for neuroevolution remains:
   - `neural.training.neuroevolution`
   - `neural.training.hybrid` (ADR 0033)
   - evolutionary skills (DE, GA, ES, CMA-ES, PSO, GP, NSGA-II/III, …)
3. No `evolutionary.neat` / `neural.neat` skill stubs may be added without a
   future ADR that defines genotype IR, fitness closed forms, and backend ownership.
4. Documentation and capability matrices MUST list NEAT as **excluded**, not
   “TODO without owner”.
5. Re-opening NEAT requires a new ADR (post-3.6) and is not implied by ADR 0040.

## Rationale

- Cost/risk disproportionate to DoD (S4 high if NEAT in).
- Neuroevolution + hybrid already exercise evo↔neural composition under
  Expression IR / built-ins without free Python fitness.
- Prefer depth on PEFT, distill, checkpoints, and VLM MVP (S1–S3, S5).

## Consequences

- S4 focuses on industrial hardening of existing evolutionary + hybrid paths
  and experiment builders — not genotype engines.
- Technical-debt may keep a single residual ID pointing here (no open-ended
  “implement NEAT soon” without ADR).
