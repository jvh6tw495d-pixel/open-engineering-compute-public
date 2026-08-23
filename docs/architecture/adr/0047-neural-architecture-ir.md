# ADR 0047: Governed Neural Architecture IR

- **Status:** accepted
- **Date:** 2026-08-22
- **Phase:** post-3.6.1
- **Related:** ADR 0031, 0032, 0033
- **Source:** OEC Neural Architecture IR v0.1 (A0–A4)

## Context

Neural families today are separate skills (`neural.mlp.*`, `cnn1d`, `lstm`,
GNN, transformer). Future NAS / neuroevolution / heterogeneous graphs need
one declarative, auditable architecture contract — without arbitrary
`nn.Module` or Python.

## Decision

1. Add `oec.neural.architecture` (core-safe, no torch on import).
2. Closed taxonomy: `TensorKind`, `NeuralFamily`, `BlockCategory`.
3. Governed `BlockRegistry` + default catalog (MLP, conv, recurrent,
   transformer, GNN, KAN catalog entry, autoencoder motifs, adapters).
4. Explicit adapters; no implicit reshape. Unknown block / incompatible
   edge fails closed.
5. `ArchitectureGraph` is a DAG of `NodeGene`/`EdgeGene` with deterministic
   SHA-256 fingerprint.
6. This wave does **not** change `runtime.py`, skills, checkpoints, or
   training loops (A5 mapping comes later).

## Non-goals

TITAN, architecture search, mutation/crossover, NeuralODE/FNO builders,
autonomous harness.

## Consequences

Architecture knowledge is separated from the execution backend. Skills stay
the public surface until A5 maps them onto this IR.
