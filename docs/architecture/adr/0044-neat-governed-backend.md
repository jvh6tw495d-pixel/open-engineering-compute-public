# ADR 0044: Governed NEAT Backend (post-3.6)

- **Status:** accepted
- **Date:** 2026-08-17
- **Phase:** post-3.6 (Scientific AI follow-on)
- **Related:** ADR 0031, 0033, 0037, 0040, 0042
- **Supersedes (partially):** ADR 0042 — re-opens **NEAT**. HyperNEAT: ADR 0045.

## Context

ADR 0042 excluded NEAT / HyperNEAT from the 3.6 DoD because a half-implemented
genotype engine would violate fail-closed / no-stub policy. The 3.6 cut shipped
without topology evolution. Product now requires the previously indicated 100%
cut **including NEAT**: a real, governed path — not a stub and not free Python
fitness.

NEAT-class systems need:

1. A closed fitness catalog (no caller-supplied callables).
2. An OEC-owned genotype IR in the result (not a leak of backend objects).
3. A named backend that OEC orchestrates and that fails closed when missing.
4. A skill + experiment builder on the same catalog as GA / NSGA-II.

## Decision

1. **NEAT is in scope** as `evolutionary.neat` (skill) + `run_neat()` (kernel)
   + `build_neat_experiment` (fail-closed catalog).
2. **Backend:** `neat-python` ≥ 2.0, pulled only by `oec[evolutionary]`.
   Missing package → `NeatNotAvailableError` (never auto-install).
3. **Fitness catalog (closed):**
   - `xor` — fixed 2-in/1-out XOR; `x`/`y` forbidden.
   - `tabular_regression` — MSE negated (NEAT maximises); rectangular finite `x`,`y`.
   - `tabular_classification` — accuracy; `y` non-negative integer labels.
4. **Genotype IR** is OEC-owned (`NeatGenotypeIR`: nodes, connections, enabled
   flags, optional innovation ids). Callers never receive a `neat.DefaultGenome`.
5. **No free Python fitness, no stubs.** HyperNEAT is re-opened by ADR 0045
   (fixed substrate only; ES-HyperNEAT remains excluded).
6. Algorithm knobs are a closed subset (population, generations, seed,
   compatibility, add/delete rates, initial hidden, feed-forward, elitism).
   Other neat-python keys stay at documented defaults (`no_fitness_termination`,
   `enabled_default`).
7. NSGA-II (and sibling MO skills) must accept an explicit `hv_reference` so
   hypervolume is comparable across runs; auto-from-front remains the fallback.

## Rationale

- ADR 0042 required a post-3.6 ADR before any `evolutionary.neat` skill.
- Neuroevolution-of-weights (`neural.training.neuroevolution`) does not evolve
  topology; NEAT is the missing topology path.
- `neat-python` is stdlib-only and belongs next to pymoo/DEAP/Nevergrad, not
  in core and not as an Unsloth-style isolated extra.

## Consequences

- Documentation and capability matrices list NEAT as **available** (optional
  extra), HyperNEAT as **excluded**.
- D-AI-05 is closed for NEAT; HyperNEAT is ADR 0045.
- 3.6 historical ADRs/docs stay accurate: 3.6 DoD excluded NEAT; 0044 re-opens
  it after that freeze.
