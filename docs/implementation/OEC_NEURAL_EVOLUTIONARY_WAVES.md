# OEC — Neural + Evolutionary Waves (implementation status)

**Baseline:** `oec==3.3.1`
**ADR:** [0031-neural-and-evolutionary-compute.md](../architecture/adr/0031-neural-and-evolutionary-compute.md)
**Product source:** expanded from the Neural/Evolutionary roadmap (governance over engines).

## Philosophy

```text
External engine (torch / pymoo / …)
  → OEC skill contract
  → validation / governance
  → SDK / CLI / REST / MCP
```

**Not:** `LLM → arbitrary PyTorch/pymoo code`.

## Wave status

| Wave | Scope | Status |
|---|---|---|
| **N0** | Contracts, extras, capability probes | **in tree** |
| **N1** | MLP regressor / classifier / predict | **in tree (v0)** |
| **E1** | Single-objective DE / GA / CMA-ES / PSO via pymoo | **in tree (v0)** |
| E2 | NSGA-II/III multiobjective | backlog |
| N2–N5, E3–E4, X1–X3 | see full roadmap | backlog |

## Install

```bash
uv sync --extra neural
uv sync --extra evolutionary
# or both
uv sync --extra neural --extra evolutionary
```

## Skills (v0)

### Neural

- `neural.mlp.regressor` — supervised MLP regression train
- `neural.mlp.classifier` — supervised MLP classification train
- `neural.predict` — forward pass from checkpoint payload
- `neural.evaluate` — metrics on held-out arrays

### Evolutionary

- `evolutionary.optimize_single` — dispatch by algorithm name
- `evolutionary.differential_evolution`
- `evolutionary.genetic_algorithm`
- `evolutionary.cma_es`
- `evolutionary.pso`

## Safety

- Closed architecture / algorithm enums only
- Optional backends: missing extra → verification ERROR
- Stochastic skills require `seed`
- Neural/evo results are **not** physics conservation claims
