# ADR 0048: Governed ES-HyperNEAT Backend

- **Status:** accepted
- **Date:** 2026-08-23
- **Updated:** 2026-08-23
- **Phase:** post-3.6.1
- **Related:** ADR 0044, 0045
- **Supersedes (partially):** ADR 0045 §4 — re-opens **ES-HyperNEAT** as a
  closed substrate, not a free layout.

## Context

ADR 0045 shipped HyperNEAT with a fixed `layered_1d` substrate and left
ES-HyperNEAT out. ES-HyperNEAT (Gauci & Stanley, 2010/2012) lets the CPPN
discover *where* hidden neurons sit and *how* they connect, by analysing
each source neuron's outgoing (and each output's incoming) connectivity
pattern on the substrate.

An earlier cut of this ADR documented a global quadtree over
`CPPN(x,y,x,y)` leaf centres. That is adaptive hidden *placement*, not
ES-HyperNEAT. This revision implements the paper algorithm under the same
fail-closed fitness catalog as NEAT/HyperNEAT.

The risk remains unbounded substrates and caller Python.

## Decision

1. Substrate catalog gains `es_quadtree` on `evolutionary.hyperneat`
   (`HyperNeatSubstrateName.ES_QUADTREE`). Result `algorithm` is
   `es_hyperneat` only on this path.
2. **Per-source connectivity-pattern quadtree.** For source `(x_s, y_s)`
   the tree covers the destination plane `[-1,1]²`. Each square is scored
   by the four child-centre queries `CPPN(x_s, y_s, x_t, y_t)` (incoming
   trees for outputs reverse the argument order). Subdivide while
   `depth < min(2, es_max_depth)` (initial resolution) or
   `depth < es_max_depth` and the four-weight variance
   `≥ es_variance_threshold`.
3. **Extraction + band pruning.** A child square becomes a connection
   candidate when `|w_centre| ≥ weight_threshold` **and**
   `max(min(d_top, d_bottom), min(d_left, d_right)) > es_band_threshold`,
   with `d_*` the absolute difference between the centre weight and the
   CPPN value one child-width away. Hidden neurons are created at
   quantized extracted destinations in the interior
   (`|x| < 0.95`), never from a diagonal presence query.
4. **Hidden-as-source iteration.** Inputs extract first (outgoing). New
   hidden neurons become sources for up to `es_max_iteration` further
   outgoing passes. Outputs then run an incoming extraction that may
   only attach to already-discovered inputs/hidden (no new hidden in
   that phase). Connections are feed-forward (`x_src < x_tgt`).
5. Caps: `es_max_hidden` (≤64), `es_max_depth` (≤5),
   `es_max_iteration` (≤4), `es_band_threshold` ∈ [0, 1].
6. Inputs/outputs remain the layered_1d columns. `layered_1d` cartesian
   expression is unchanged.
7. ES-HyperNEAT requires `feed_forward=True`. Recurrent CPPNs make
   query order part of the geometry.
8. Substrate IR is discriminated: `kind=es_hyperneat`,
   `extraction=gauci_quadtree`, `actual_hidden`, depth/band/iteration
   knobs. It does **not** reuse `hidden_layers` / `hidden_width`.
9. Fitness catalog unchanged (`xor` / tabular). No caller Python.
10. TITAN, free substrate coordinates, and free Python fitness stay out.

## Consequences

- D-AI-05 HyperNEAT exclusion of ES is closed by the Gauci loop, not by
  a renamed placement heuristic.
- Callers that only needed fixed-grid HyperNEAT keep `layered_1d`.
