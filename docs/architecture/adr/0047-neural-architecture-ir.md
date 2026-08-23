# ADR 0047: Governed Neural Architecture IR

- **Status:** accepted
- **Date:** 2026-08-22
- **Updated:** 2026-08-23
- **Phase:** post-3.6.1
- **Related:** ADR 0031, 0032, 0033
- **Source:** OEC Neural Architecture IR v0.1, waves A0–A7 landed

## Context

Neural families today are separate skills (`neural.mlp.*`, `cnn1d`, `lstm`,
GNN, transformer). Future NAS / neuroevolution / heterogeneous graphs need
one declarative, auditable architecture contract — without arbitrary
`nn.Module` or Python.

## Decision

1. Add `oec.neural.architecture` (core-safe, no torch on import).
2. Closed taxonomy: `TensorKind`, `NeuralFamily`, `BlockCategory`.
3. Governed `BlockRegistry` + default catalog (MLP, conv, recurrent,
   transformer, GNN, KAN catalog entry, autoencoder motifs, adapters, A6
   extras). `default_registry` is **sealed** after construction; extensions
   use `clone()` / `make_default_registry()` with their own version.
4. Explicit adapters; no implicit reshape. Unknown block / family /
   incompatible edge / extra config key fails closed.
5. `ArchitectureGraph` is a DAG of `NodeGene`/`EdgeGene`. Validation covers
   DAG, orphan nodes (n>1), `BlockParameterSpec` configs, and compatibility.
   Fingerprint is SHA-256 of JSON-canonical, finite config **after default
   materialization**, plus registry version and catalog hash.
6. **A5:** `graph_for_skill()` is a declarative map of current neural family
   skills onto the IR. It translates architectural fields (`hidden_dims` →
   `hidden_dim`, `n_heads` → `nhead`, inferred `in_features` / `input_size`)
   and ignores training keys. It does **not** hijack skill runtime.
7. **A6:** catalog-only extras. GEGLU is SEQUENCE→SEQUENCE. FNO is split by
   rank (`fno`, `fno_2d`). `cross_attention` declares named ports
   `(query, context)` and rejects unary sequential edges.
8. **A7:** `build_architecture(..., backend="torch")` materializes a **strict
   linear chain** only. Forks, joins, skips, empty and disconnected graphs
   fail closed. KAN/GNN/A6 extras without a torch builder fail closed before
   importing torch. Multi-width `hidden_dims` map the first width onto the
   single `mlp` block; they are not expanded into N-layer graphs.

## Non-goals

TITAN, architecture search, mutation/crossover, ES-HyperNEAT, NeuralODE/FNO
torch builders, named-port wiring beyond fail-closed arity, autonomous
harness. Full A8 (manifest/promotion workflow) is not this ADR.

## Consequences

Architecture knowledge is separated from the execution backend. Skills remain
the public training surface. The IR is a governed catalog + sequential
builder, not a heterogeneous executable graph compiler.
