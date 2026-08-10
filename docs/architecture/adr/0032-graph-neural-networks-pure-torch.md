# ADR 0032: Graph Neural Networks without PyG/DGL (N5)

- **Status:** accepted
- **Date:** 2026-08-02
- **Phase:** Neural Compute N5

## Context

Roadmap Wave N5 targets GCN / GraphSAGE / GAT for engineering graphs
(electrical topology, thermal/hydraulic networks). Product draft left the
choice of PyTorch Geometric vs DGL open pending license/API maintenance
review.

Adding either stack as a required peer of `oec[neural]` increases install
size, Windows binary friction, and version coupling to torch builds.

## Decision

1. **N5 v0 implements message-passing in pure PyTorch** under
   `oec.kernel.neural.gnn` (sparse adjacency matmul for GCN/SAGE; edge-wise
   attention for GAT).
2. **No new extra** — skills use existing `oec[neural]` / torch capability
   domains `neural_train` / `neural_eval`.
3. **Skill IDs:** `neural.gcn`, `neural.graphsage`, `neural.gat` (node-level
   regression/classification on `node_features` + `edge_index`).
4. **PyG / DGL remain optional future adapters** behind a later ADR if a
   project needs production-scale kernels; merit ownership stays with the
   library then, not OEC.

## Consequences

- Smaller dependency surface; reproducible CPU tests without CUDA/PyG wheels.
- Feature set is intentionally limited (no mini-batch neighbor sampling,
  no heterogeneous graphs in v0).
- Agents still cannot inject custom `MessagePassing` Python classes — only
  declarative architecture enums + numeric tensors.
