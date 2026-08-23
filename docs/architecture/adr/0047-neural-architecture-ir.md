# ADR 0047: Governed Neural Architecture IR

- **Status:** accepted
- **Date:** 2026-08-22
- **Updated:** 2026-08-23
- **Phase:** post-3.6.1
- **Related:** ADR 0031, 0032, 0033
- **Source:** OEC Neural Architecture IR v0.2.3, waves A0–A8 landed

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
   linear chain**, with one named-port exception: a node whose block
   declares arity > 1 input ports (`cross_attention`) may have
   indegree == arity ("named joins"). Forks, extra skips, empty and
   disconnected graphs still fail closed. `EdgeGene.target_port` /
   `source_port` (default `"in"` / `"out"`) make wiring explicit;
   `validate_graph` requires every declared input port of a target node to
   be wired exactly once (root nodes with a single "in" port are exempt —
   they receive their tensor from outside the graph). `check_connection`
   checks tensor-kind compatibility only; arity is a graph-level concern.
   Torch builders now cover `kan` (honest B-spline/RBF basis, no MLP+GELU
   stand-in), `gcn`/`graphsage`/`gat` (via `oec.kernel.neural.gnn`, with a
   real `graph_global_pool` — mean over nodes, not `Identity` — and
   fail-closed if `edge_index` is missing), `fno`/`fno_2d` (rfft → truncated
   modes → irfft, rank-preserving), `cross_attention`
   (`nn.MultiheadAttention`, `forward(query, context)`), and the honest A6
   extras (geglu, highway, residual_gated, depthwise/separable/dilated/
   grouped conv, squeeze_excitation, self_attention, swiglu, residual_mlp,
   vector_to_sequence, tcn). `local_attention`, `linear_attention`,
   `neural_ode`, `deeponet`, and `pinn_motif` remain fail-closed — no torch
   builder, no `nn.Identity` stand-in. `graph_for_skill("neural.mlp.*")`
   expands multi-width `hidden_dims` into an honest N-layer `linear` chain
   (activation applied per layer, last layer is a plain projection) instead
   of squashing to a single `mlp` block; a single hidden width still uses
   one `mlp` block. Multi-width autoencoders reflect every declared width
   in the encoder/decoder chain rather than dropping the extras.
9. **A8:** `oec.neural.architecture.governance` adds `ArchitectureManifest`
   (graph fingerprint, registry version, catalog hash, a closed
   `compatibility_version` constant, backend, experimental block ids used,
   optional `created_at`, closed-key `ArchitectureProvenance`) via
   `manifest_for_graph()`, and `audit_catalog()` — a read-only catalog
   health check for duplicate ids, experimental blocks missing
   `backend_requirements`, unknown parameter kinds, an unsealed registry,
   and missing `input_ports`, plus an experimental/stable id partition.
   `compatibility_version` is part of the fingerprint's canonical payload
   (catalog bumped 0.2.1 → 0.2.2 for the payload change). Same graph + same
   sealed catalog still → same fingerprint. `manifest_for_graph()` fails
   closed: it requires a **sealed** registry, requires the graph to
   `validate_graph()` clean, and closes `backend` to a known set — a
   manifest can never certify an invalid graph or a mutable/unknown-backend
   catalog. `audit_catalog()` fails closed too: an unsealed registry and an
   experimental block missing `backend_requirements` are **errors**
   (`valid=False`), not warnings.
10. **A8+ search:** `oec.neural.architecture.search.search_graphs()` is a
    core-safe, IR-governed search over a **closed candidate family**
    (sequential MLP/CNN1d/LSTM graphs from the catalog, widths/depths from a
    closed, runtime-validated list of ints — non-empty, every value an
    `int >= 1`). Every candidate is validated against the catalog. The
    objective is closed and built-in only (`objective: Literal["param_count"]`)
    — a static parameter-count estimate. There is **no caller-supplied
    fitness callback of any kind**: `search_graphs` never executes arbitrary
    Python to score a candidate, and never imports torch itself. This is
    independent of `neural.search_architecture` (ADR 0033's hybrid
    evolutionary training-facet search, unchanged) and is **not** TITAN — no
    mutation/crossover/population ecology.
11. **A8+ port and attention hardening:** `BlockSpec.output_ports` (default
    `("out",)`) closes `EdgeGene.source_port`: `validate_graph` rejects an
    edge whose `source_port` is not in the source block's declared output
    ports, and `output_ports` are part of the catalog snapshot (sorted) so
    the catalog hash stays stable (catalog bumped 0.2.2 → 0.2.3). Blocks
    declaring both `d_model` and `nhead` (`self_attention`,
    `transformer_encoder`, `cross_attention`) require `d_model % nhead == 0`
    and `nhead <= d_model` at `validate_config` time, so a bad head split
    fails closed in the IR instead of raising a raw PyTorch exception. A
    graph block (`gcn`/`graphsage`/`gat`) always receives `edge_index` when
    materialized, whether it is the chain root or a later node — a
    GNN→GNN chain no longer silently falls through to the unary invocation
    path. `fno`/`fno_2d` reject wrong-rank input explicitly.

## Non-goals

TITAN, mutation/crossover, ES-HyperNEAT, evolvability/population ecology,
autonomous research harness, fake NeuralODE/DeepONet/PINN builders.

## Consequences

Architecture knowledge is separated from the execution backend. Skills remain
the public training surface. The IR is a governed catalog + sequential
builder, not a heterogeneous executable graph compiler.
