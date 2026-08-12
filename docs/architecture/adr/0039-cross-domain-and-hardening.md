# ADR 0039: Cross-domain experiments (W7) & Framework hardening (W8)

- **Status:** accepted
- **Date:** 2026-08-10
- **Phase:** Framework W7 + W8
- **Related:** ADR 0034–0038

## W7 Decision

Ship a **library of cross-domain ExperimentSpec builders** in
``oec.experiment.cross_domain``:

| Builder | Composition |
|---------|-------------|
| physics kinematics | mechanics skill + metric gate |
| wave + stats | waves → statistics.describe |
| MC uncertainty | monte_carlo → describe |
| evo sphere | evolutionary optimize + gate |
| physics→neural surrogate | synthetic linear law → MLP |
| foundation embed + stats | builtin embed → describe |
| root→PDF bind | solve_root binds into distribution_eval |

No new domain silos. Builders are pure planning; numbers still come only from
``ExecutionResult`` paths.

## W8 Decision

Hardening for the ``3.5.0`` framework cut:

1. Package version **3.5.0**
2. CLI ``oec backends`` — Backend Capability Registry dump
3. CLI ``oec experiment builders`` — W7 catalog
4. SymPy declared in capability registry (core dep honesty)
5. Transformers optional probe
6. Docs: skill promotion remains explicit policy (skills stay `experimental`
   until a future promotion gate; no silent status flip in W8)
7. POST-OEC scientific harness remains out of repo

## Non-goals

- Full dataset lake / remote artifact store
- Production auth on REST/MCP
- Competitive performance benchmarks vs SciPy/HF (correctness catalog only)
