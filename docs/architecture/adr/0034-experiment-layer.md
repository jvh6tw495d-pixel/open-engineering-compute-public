# ADR 0034: Experiment Layer v0

- **Status:** accepted
- **Date:** 2026-08-10
- **Phase:** Framework W0 freeze → W2 runtime
- **Related:** ADR 0001, 0005, 0007, 0015, 0017, 0019, 0021, 0031, **0035**

## Context

OEC 3.4.1 is a mature **skill engine**: one skill invocation yields one
`ExecutionResult` with graded status, validation, and provenance. Neural and
evolutionary families already expose rich skills and Pydantic contracts, but
there is **no first-class multi-step scientific experiment** type.

Without an experiment layer, physics, chemistry, neural, and evolutionary work
remain parallel skill catalogs that share execution plumbing but not a universal
“this was a reproducible scientific run” contract.

## Decision

1. **Introduce an Experiment layer** that **composes** skills. It does **not**
   replace skills, `ExecutionResult`, or `Engine.run`.

2. **Canonical types** (schema freeze in ADR 0035; runtime in W2):
   - `ExperimentSpec` — declarative plan (seed, steps, metrics, validation, artifacts)
   - `ExperimentRecord` — immutable outcome of running a spec
   - `ExperimentStatus` — experiment-level status (distinct from `ExecutionStatus`)

3. **Execution model v0:**
   - Steps run **sequentially**
   - Each step is exactly one `Engine.run(skill_id, inputs)` → one `ExecutionResult`
   - Later versions may add DAG/parallel steps under ADR 0015 concurrency policy

4. **Authority policy:**
   - Experiments **never invent numbers**
   - Metrics are resolved only from declared paths into step `ExecutionResult`s
   - Narrative/agents must cite experiment `run_id` and/or step `run_id`s

5. **Dependency rules** (framework-wide):
   - Core ↛ ML/AI
   - ML/AI → Core
   - External backend ≠ public OEC API

6. **Out of scope for this ADR:**
   - Persistent scientific harness / autonomous agents
   - Remote experiment databases
   - Arbitrary Python step bodies
   - Replacing REST/MCP skill endpoints

7. **Package layout:**
   - `src/oec/experiment/` — specs (W0), runner + record (W2)
   - Optional sugars later: `NeuralExperiment` as thin wrapper over `ExperimentSpec`

## Consequences

- W2 implements `Engine.run_experiment` / `experiment.run`
- Existing skill single-shot API remains the primary low-level surface
- Hybrid training (ADR 0033) should eventually be expressible as experiment steps
- MCP may add at most a thin `experiment.run` tool after W2-MVP; raw skills stay

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Replace skills with experiments | Breaks 131-skill ecosystem and ADR 0001 |
| Notebook-only provenance | Not machine-contractual |
| Airflow-style general workflows | Out of OEC product boundary |
