# ADR 0040: Scientific AI Completion (post-3.5)

- **Status:** accepted
- **Date:** 2026-08-12
- **Phase:** Scientific AI Closure S0–S6 → `oec==3.6.x`
- **Related:** ADR 0021, 0031–0033, 0034–0035, 0037–0039, 0041, 0042

## Context

OEC **3.5.0** delivered the scientific framework cut (W0–W8): Experiment Engine,
applied-sciences foundations, neural/evolutionary re-homologation under
experiments, foundation embed/generate MVP, and hardened MCP/CLI surfaces.

The product postulado still requires a **common scientific infrastructure** for:

- neural compute and training;
- evolutionary compute and neuroevolution;
- foundation models, PEFT, fine-tuning;
- knowledge distillation;
- hybrid composition across those paradigms;
- governed LLM (and optional VLM) inference.

These capabilities must close **without** reimplementing PyTorch, Transformers,
or evolutionary libraries, and without pulling ML/AI into the core install.

## Decision

1. **Successor programme** after W0–W8 is numbered **S0–S6** (Scientific AI
   Completion), version line **3.6.x** — not a rewrite of 3.5.
2. **Principle (frozen):** *Backends compute. OEC defines the scientific contract.*
3. **Rules (frozen):**
   - `Core ↛ ML/AI`
   - `ML/AI → Core` (ExecutionResult, units, validation, provenance)
   - External backends ≠ public OEC API
   - No arbitrary agent Python (`nn.Module`, free fitness `eval`)
4. **Definition of done (functional completeness)** for Scientific AI:
   - Closed contracts for neural / evolutionary / foundation / PEFT / distill
     (and VLM if in-scope under D3);
   - Each postulated capability has ≥1 public skill **or** an explicit exclusion ADR;
   - Canonical experiment builders on the fail-closed catalog;
   - MCP / REST / CLI discovery without open `getattr` surfaces;
   - Core install remains green without torch / transformers / pymoo;
   - Closeout doc + CHANGELOG 3.6.x; residuals only in technical-debt with IDs.
5. **Wave order (fixed dependencies):**
   - **S0** architecture freeze & inventory (this ADR + 0041/0042 + release matrix)
   - **S1** foundation depth (PEFT train, artifacts, generate harden)
   - **S2** knowledge distillation (+ experiment builder)
   - **S3** neural industrial hardening (checkpoints, promotion criteria)
   - **S4** evolutionary / neuroevolution closure (NEAT per ADR 0042)
   - **S5** multimodal / VLM MVP (optional per D3)
   - **S6** surfaces, optional CI extras job, tag `v3.6.0-scientific-ai`
6. **POST-OEC Scientific Harness** (autonomous multi-agent research loop, durable
   hypothesis state) remains **out of this repository** (ADR 0039).

## Closed decisions (S0)

| ID | Decision | Choice for 3.6 |
|----|----------|----------------|
| D1 | NEAT / HyperNEAT | **Excluded** from 3.6 DoD — see ADR 0042 |
| D2 | vLLM / llama.cpp / SGLang | **Out** of 3.6; HF Transformers only; residual debt |
| D3 | VLM / multimodal | **In-scope MVP** as S5 (tiny HF path) |
| D4 | Distillation primary domain | **`neural.*` first** (tabular, CI-cheap); foundation LM distill later if needed |
| D5 | Skill status promotion | **Promote a documented core subset** when gates pass; remainder stays experimental |

## Non-goals

- Replacing SciPy / PyTorch / Transformers merit claims
- Multi-node / multi-GPU product training
- Full TRL RLHF / DPO productization
- Auto model download as default CI behaviour
- Breaking the skill-first `ExecutionResult` contract

## Consequences

- Implementation work after S0 starts at **S1** (`foundation.peft_train` + artifacts).
- Roadmap living document: [`docs/release/SCIENTIFIC-AI-3.6.md`](../../release/SCIENTIFIC-AI-3.6.md).
- Capability contracts for PEFT / distill: ADR 0041.
- NEAT exclusion rationale: ADR 0042.
