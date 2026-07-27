# Changelog

All notable changes to Open Engineering Compute are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.0] — 2026-07-27

### Added

- **Scientific Kernel (v2.0)** — domain-independent `oec.core` package:
  - `ScientificResult` — additive scientific outcome adapter over `ExecutionResult` (ADR 0019)
  - `ValidityDomain` — declared applicability envelope (constraints, bounds)
  - `Diagnostic` + `diagnostics_from_mapping` — typed diagnostics; legacy payload retained as `diagnostics_raw`
  - `ProvenanceRecord` — formal provenance with `BackendRef` list and passthrough extras
  - Core errors: `ScientificDomainError`, `DimensionalIncompatibilityError`,
    `BackendUnavailableError`, `UnderdeterminedProblemError`, `OverdeterminedProblemError`
  - Shared types: `MethodRef`, `BackendRef`, `Assumption`
- `Engine.run_scientific(...)` — SDK entry that returns `ScientificResult` without changing `Engine.run` / REST / MCP
- ADR 0019: ScientificResult adapter design
- Concept page: [docs/concepts/scientific-kernel.md](docs/concepts/scientific-kernel.md)
- Unit tests: `tests/unit/test_core_scientific_result.py`

### Changed

- Package version **1.5.0 → 2.0.0**
- README status: **v2.0.0 Scientific Kernel alpha** (private); public GitHub remains **v3.0**

### Notes

- **`ExecutionResult` is unchanged** — Skill Engine, CLI, REST, and MCP contracts stay as in v1.5
- Full Math Complete / Physics-Chemistry Complete remain **v2.x+ / v3.0** milestones
- Semver major: new public scientific surface in `oec.core`; no intentional breaking changes to execution APIs

## [1.5.0] — 2026-07-27

### Added

- **v1.5 private operational alpha** (V3 roadmap §10 closeout)
- ~40 public skills across mathematics, electrical, timeseries, linear, numerical,
  statistics, optimization (LP/MILP/QP/NLP/multiobjective), energy, battery, finance
- OPS v0.1 + HiGHS adapter (`optimization.lp` / `milp`) + feasibility / scenario_batch
- Provenance: `input_hash`, `backends[]` (ADR 0017)
- Agents layer outside the wheel: Optimization, Scientific Reviewer, Applied Math,
  Time-Series, Energy specialists (`agents/`)
- Agent metrics harness (`benchmarks/agent_metrics.py`)
- Skill contract audit script (`scripts/audit_skill_contracts.py`) — 40/40 clean
- v1.5 compliance matrix vs V3 roadmap (`docs/implementation/v1.5-compliance-matrix.md`)
- LLM vs OEC thesis experiments (with/without OEC multi-agent)
- Public sibling tree prep (clean history; no remote push)

### Changed

- Package version **0.1.0 → 1.5.0**; classifier **Pre-Alpha → Alpha**
- README status: private **v1.5 alpha**; public GitHub remains a **v3.0** milestone

### Notes

- Math IR / Scientific Kernel formal / Physics-Chemistry Complete are **v2.x+** (not 1.5)
- Private incubation history is not the public history (ADR 0008)
- REST/MCP ship without auth in Alpha (ADR 0015)

## [0.1.0] — 2026-07-25

### Added

- Skill Engine: loader, registry, lifecycle, manifests (`skill.yaml` + `skill.md`)
- Engineering kernel: units (Pint), numerics, optimization
- Validation engine: schema, dimensional, mathematical, physical helpers, numerical, invariants, golden cases
- Execution pipeline with subprocess sandbox, provenance, graded status (ADR 0007)
- Central dimensional normalization (ADR 0016)
- Public surfaces: Python SDK, CLI (`oec`), REST API (`/v1`), MCP server
- MVP mathematics skills (6): solve_root, interpolate, integrate, optimize_scalar, optimize_constrained, curve_fit
- MVP electrical skills (6): three_phase_power, current_from_power, voltage_drop, power_factor_correction, transformer_loading, per_unit_conversion
- Optional integrations: Odysseus (MCP host config) and Open Science (Method Change Proposal)
- Public Alpha preparation scripts and security/community docs

### Notes

- Private incubation history is not the public history (ADR 0008).
- REST/MCP ship without auth in Alpha (ADR 0015).
