# ADR 0031: Neural Compute and Evolutionary Compute

- **Status:** accepted
- **Date:** 2026-08-02
- **Phase:** OEC 3.4+ (N0 foundation → N1 MLP / E1 evolutionary core)

## Context

OEC 3.3.1 is a mature skill engine with Backend Capability Registry (ADR 0021),
Verification Engine, Scientific IR / Model Registry (ADR 0030), and optional
HiGHS via `oec[optimization]`. Product roadmap
`docs/implementation/OEC_NEURAL_EVOLUTIONARY_WAVES.md` adds two optional
compute families:

- **Neural Compute** — merit owner **PyTorch**
- **Evolutionary Compute** — merit owner **pymoo** (DEAP / Nevergrad later)

Agents (LLMs) must not inject arbitrary Python (`nn.Module`, fitness
`eval`/`exec`). Architecture and algorithms are declared via closed enums and
versioned contracts; engines compute; OEC governs.

## Decision

1. **Optional extras only** — core install stays free of torch/pymoo:

   ```toml
   neural = ["torch>=2.2"]
   evolutionary = ["pymoo>=0.6"]
   ```

2. **Package layout**
   - `src/oec/neural/` — public Pydantic specs + result DTOs + architecture enums
   - `src/oec/evolutionary/` — public problem/algorithm specs + result DTOs
   - `src/oec/kernel/neural/` — thin training/eval loops (torch)
   - `src/oec/kernel/evolutionary/` — thin algorithm dispatch (pymoo)
   - `skills/neural/`, `skills/evolutionary/` — agent-facing skill contracts

3. **Backend registry** — extend ADR 0021:
   - `torch` → domains `neural_train`, `neural_eval` (optional)
   - `pymoo` → domains `evolutionary_single`, `evolutionary_multi` (optional)
   - adapters probe availability only; missing backend → **ERROR**, never
     silent swap to SciPy/`numpy` reimplementation of the same method id

4. **ExecutionResult unchanged** — DTOs serialize inside `result` /
   `diagnostics`. No new top-level keys (`extra="forbid"`).

5. **No arbitrary code** — skill inputs are JSON/YAML enums + hyperparameters.
   Genetic programming (later wave) uses operator IR only, not free Python.

6. **Stochastic policy (ADR 0004)** — train / evolutionary skills set
   `execution.deterministic: false` and require `seed`. Provenance records
   `deterministic_status` ∈ {`strict`, `practical`, `best_effort`}.

7. **Physics boundary** — neural/evolutionary outputs are statistical /
   search results, not conservation-law physics. Surrogates require explicit
   high-fidelity verification before engineering acceptance (X2).

8. **Merit ownership** — OEC does not claim backprop / NSGA / CMA-ES
   algorithmic merit; skill `references.md` cites torch/pymoo.

## Consequences

- mypy `ignore_missing_imports` for `torch` / `pymoo`
- pytest markers `neural` / `evolutionary` with `importorskip`
- CI core job stays without extras; optional jobs install extras
- Next skills: `neural.mlp.regressor`, `evolutionary.optimize_single`, …

## Related

- ADR 0004 deterministic execution
- ADR 0008 public/private / no reimplementation of solvers
- ADR 0017 provenance backends
- ADR 0021 backend registry + verification
- ADR 0030 scientific IR and model registry
