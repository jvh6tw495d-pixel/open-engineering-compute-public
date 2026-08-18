# ADR 0045: Governed HyperNEAT Backend (post-3.6)

- **Status:** accepted
- **Date:** 2026-08-17
- **Phase:** post-3.6 (Scientific AI follow-on)
- **Related:** ADR 0031, 0042, 0044
- **Supersedes (partially):** ADR 0044 §5 — re-opens **HyperNEAT** under the
  same fail-closed rules as NEAT. **ES-HyperNEAT** stays excluded.

## Context

ADR 0042 excluded NEAT and HyperNEAT from the 3.6 DoD. ADR 0044 re-opened
NEAT (direct topology) and left HyperNEAT out until a dedicated ADR defined
the substrate contract. Product now requires a governed HyperNEAT path.

HyperNEAT evolves a CPPN with NEAT; the CPPN queries a **fixed geometric
substrate** to produce connection weights. The risk is the same as NEAT:
free Python fitness or a leaky backend object.

## Decision

1. **HyperNEAT is in scope** as `evolutionary.hyperneat` + `run_hyperneat()`
   + `build_hyperneat_experiment`.
2. **Backend:** same `neat-python` extra as NEAT (`oec[evolutionary]`).
   Missing package → `NeatNotAvailableError`.
3. **Fitness catalog:** identical to ADR 0044 (`xor` / tabular regression /
   classification). No caller Python.
4. **Substrate catalog (closed):** `layered_1d` only — inputs at x=−1,
   optional hidden columns, outputs at x=+1. Hidden layer count and width
   are bounded knobs, not free layouts. ES-HyperNEAT (evolved substrate)
   is out.
5. **CPPN IR** is the existing `NeatGenotypeIR`. The result also carries an
   OEC-owned **substrate IR** (node coordinates + expressed weights).
   Callers never receive a neat-python genome.
6. CPPN query: four inputs `(x_src, y_src, x_tgt, y_tgt)`, one weight
   output. A connection is expressed iff `|w| ≥ weight_threshold`.

## Consequences

- Capability matrices list HyperNEAT as available (optional extra).
- D-AI-05 is closed for both NEAT and HyperNEAT.
- ES-HyperNEAT still needs a future ADR.
