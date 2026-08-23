# ADR 0048: Governed ES-HyperNEAT Backend

- **Status:** accepted
- **Date:** 2026-08-23
- **Phase:** post-3.6.1
- **Related:** ADR 0044, 0045
- **Supersedes (partially):** ADR 0045 §4 — re-opens **ES-HyperNEAT** as a
  closed substrate, not a free layout.

## Context

ADR 0045 shipped HyperNEAT with a fixed `layered_1d` substrate and left
ES-HyperNEAT out. ES-HyperNEAT (Gauci & Stanley) lets the CPPN discover
*where* hidden neurons sit via a quadtree, not only *how* they connect.

The risk is unbounded substrates and caller Python. This ADR keeps the
same fail-closed fitness catalog as NEAT/HyperNEAT.

## Decision

1. Substrate catalog gains `es_quadtree` on `evolutionary.hyperneat`
   (`HyperNeatSubstrateName.ES_QUADTREE`).
2. Hidden neurons are leaf centres of a bounded quadtree over
   x∈(-0.8, 0.8), y∈[-1, 1]. Subdivision happens when CPPN corner
   variance ≥ `es_variance_threshold` and depth < `es_max_depth`.
   Presence uses `|CPPN(x,y,x,y)| ≥ weight_threshold`. Caps:
   `es_max_hidden` (≤64), `es_max_depth` (≤5).
3. Inputs/outputs remain the layered_1d columns. Connection expression
   is the same `|w| ≥ weight_threshold` query as ADR 0045.
4. Fitness catalog unchanged (`xor` / tabular). No caller Python.
5. TITAN, mutation of populations outside neat-python's own NEAT loop,
   and free substrate coordinates stay out.

## Consequences

- `run_hyperneat()` result `algorithm` is `es_hyperneat` when the
  quadtree substrate is selected.
- D-AI-05 HyperNEAT exclusion of ES is closed.
