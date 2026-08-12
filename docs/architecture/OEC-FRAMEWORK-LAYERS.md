# OEC Framework Layers

**Status:** normative for framework roadmap W0+
**Standing rules:** Core ↛ ML/AI · ML/AI → Core · external backend ≠ public OEC API
**Related:** ADR 0001 (skill-first), ADR 0008 (public/private), ADR 0021 (backends),
ADR 0031 (neural/evo), ADR 0034 (experiment layer), ADR 0035 (spec family)

---

## 1. Purpose

This document freezes the **architectural layers** of Open Engineering Compute as a
scientific framework. It does **not** replace the skill-execution engine; it situates
that engine inside a larger, product-agnostic scientific stack.

OEC is:

- a **governed skill engine** (`ExecutionResult`, validation, provenance)
- a **scientific core** (units, numerics, optimization, statistics, symbolic)
- optional **compute families** (neural, evolutionary, foundation models)
- an **experiment infrastructure** that composes skills into reproducible science

OEC is **not**:

- a persistent autonomous research harness (agents, durable hypothesis loops)
- a product brand surface
- a thin re-export of PyTorch / SciPy / Transformers as the public API

---

## 2. Layer diagram

```text
OEC Architecture
├── Core
│   ├── Skill registry + manifests
│   ├── ExecutionService + sandbox
│   ├── ExecutionResult / ScientificResult
│   ├── Validation + Verification
│   ├── Units (Pint) + dimensional policy
│   ├── Provenance (input_hash, backends[])
│   └── Backend Capability Registry
│
├── Applied Sciences
│   ├── Physics foundations
│   ├── Chemistry foundations
│   └── Engineering domains (applications of the above)
│
├── ML / Neural          (optional extra oec[neural])
├── Evolutionary         (optional extra oec[evolutionary])
├── Foundation Models    (optional extra — future oec[foundation])
│
└── Experiment Infrastructure
    ├── ExperimentSpec / ExperimentRecord
    ├── Dataset / Metric / Artifact / Validation specs
    └── run_experiment → N × Engine.run
```

---

## 3. Layer contracts

### 3.1 Core

| Owns | Does not own |
|------|----------------|
| Skill lifecycle, execution, status taxonomy | Domain physics merit claims |
| Units, provenance, sandbox policy | Torch training loops |
| Backend *capability* registration | Reimplementation of SciPy/PyTorch algorithms |

**Install rule:** `pip install oec` (core) must run scientific skills **without**
torch, pymoo, transformers, or HF.

### 3.2 Applied Sciences

Domain packages (`oec.physics`, `oec.chemistry`, engineering skills) consume Core
units, validation, and execution. Engineering domains are **applications** of
physical/chemical foundations, not a parallel universe of one-off solvers.

### 3.3 ML / Neural · Evolutionary · Foundation Models

| Rule | Meaning |
|------|---------|
| Optional extras only | Never hard-require in core |
| Closed contracts | Enums / IR; no arbitrary agent Python (`nn.Module`, fitness `eval`) |
| Merit ownership | Backend libraries own algorithm merit; OEC owns governance |
| Fail-closed | Missing extra → ERROR, never silent SciPy swap of the same method id |

### 3.4 Experiment Infrastructure

| Rule | Meaning |
|------|---------|
| Composition | An experiment **orchestrates** skills; it does not replace skills |
| Authority | Numbers come only from `ExecutionResult` fields of steps |
| Record | `ExperimentRecord` freezes spec + environment + steps + metrics + artifacts |
| No LLM orchestration inside the engine | Agents may *author* specs; OEC executes them |

---

## 4. Three frozen dependency rules

```text
1. Core  ↛  ML / AI
   Core install and core code paths must not import torch / transformers / peft.

2. ML / AI  →  Core
   Neural, evolutionary, and foundation packages consume ExecutionResult,
   units, validation, provenance, and the backend registry.

3. External backend  ≠  public OEC API
   Callers use OEC contracts (skills, specs, ExperimentSpec).
   PyTorch, SciPy, SymPy, Pint, pymoo, Transformers remain behind adapters.
```

---

## 5. Public surface (import policy)

| Allowed high-level | Package |
|--------------------|---------|
| `Engine`, version | `oec` / `oec.sdk` |
| Experiment specs + runner (W2+) | `oec.experiment` |
| Neural contracts (optional runtime) | `oec.neural` |
| Evolutionary contracts | `oec.evolutionary` |
| ScientificResult | `oec.core` |
| Physics / chemistry libraries | `oec.physics`, `oec.chemistry` |

Skill filesystem (`skills/`) remains the **unit of agent-facing capability**.
REST/CLI/MCP are thin adapters (ADR 0005 / 0015).

---

## 6. Explicit non-goals (POST-OEC)

The following live **outside** this repository’s framework roadmap:

```text
POST-OEC
└── Persistent Scientific Harness
    ├── long-running agents
    ├── durable research state
    ├── autonomous hypothesis generation
    └── multi-day experiment planning
```

OEC supplies deterministic compute + experiment records for such harnesses to
*consume*; it does not embed them.

---

## 7. Roadmap alignment

| Wave | Layer focus |
|------|-------------|
| W0 | Freeze this document + spec family (ADR 0034/0035) |
| W1 | Core scientific completeness **without AI** |
| W2 | Experiment Infrastructure runtime |
| W3 | Applied Sciences depth |
| W4–W5 | Neural / Evolutionary re-homologation under Experiment |
| W6 | Foundation Models extra |
| W7 | Cross-domain experiments |
| W8 | Hardening (SDK/CLI/REST/MCP, promotion, benchmarks) |

See `docs/implementation/FRAMEWORK-ROADMAP-W0-W8.md`.
