# Changelog

All notable changes to Open Engineering Compute are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.3.0a0] — 2026-07-27

### Added — v2.3 Wave A (applied math expansion)

**Eleven** new experimental skills under `skills/linear`, `skills/statistics`,
`skills/timeseries`, and `skills/optimization`, each with the full contract
(`skill.yaml`, `skill.md`, schemas, `implementation.py`, `validation.py`,
`references.md`, `examples/`, `tests/test_validation.py`, `tests/test_golden.py`):

- `linear.eig` — eigenvalues and (right) eigenvectors for square
  matrices (NumPy `linalg.eig`).
- `linear.least_squares` — overdetermined `Ax = b` least squares with
  rank/residual reporting (NumPy `linalg.lstsq`).
- `linear.residual_norms` — L1/L2/L∞ norms of a residual vector.
- `statistics.regression` — OLS with coefficients, fitted values,
  residuals, R², adjusted R², RMSE, residual standard error.
- `statistics.intervals` — Student-t / Gaussian confidence interval
  for the mean.
- `statistics.bootstrap` — nonparametric bootstrap CI for mean, median,
  or sample variance.
- `timeseries.lag_features` — lag columns aligned to a response slice.
- `timeseries.forecast_simple` — naive, seasonal-naive, and mean
  forecasters for a requested lead window (`steps_ahead`).
- `timeseries.backtest` — rolling backtest for the simple forecasters;
  per-step error metrics and skill score vs naive baseline.
- `optimization.lp_diagnostics` — reduced costs, slacks, and dual
  values for a solved LP (HiGHS).
- `optimization.infeasibility_explain` — bound conflicts plus
  drop-one IIS candidate explanation (HiGHS).

Kernel support (no LAPACK reimplementation; ADR 0008):

- `oec.kernel.linear.analysis` — `eigendecomposition`, `least_squares`, `residual_norms`
- `oec.kernel.statistics.{regression,intervals,bootstrap}`
- `oec.kernel.timeseries.{lag,forecast,backtest}`
- HiGHS adapter: reduced costs + slacks on `LinearSolveResult`;
  `explain_infeasibility` on the feasibility module

### Changed

- Package version `2.2.0 → 2.3.0a0` (Wave A **pre-release**; full v2.3
  gate in the V3 plan is ≥ 15 new/major applied skills — Wave B/C still open).
- Forecast API uses the field name `steps_ahead` (avoids ADR 0008 reserved product tokens).
- No existing skill contract broken; new skills are additive.

### Notes

- `optimization.lp_diagnostics` and `optimization.infeasibility_explain`
  require the optional `highspy` extra (`uv sync --extra optimization`).
- Coefficient standard errors and property-test suites for Wave A skills
  are deferred (not claimed in this alpha).

## [2.2.0] — 2026-07-27

### Added

- **Math IR v0 foundation** (`oec.modeling`) — a versioned, closed Pydantic model
  set for problems represented independently of any solver (ADR 0020):
  - `MathProblem` root document (`ir_version`), `Symbol` (optionally
    dimensioned/bounded)
  - a closed, discriminated `Expr` node tree: `NumberLiteral`, `QuantityLiteral`,
    `ConstantRef`, `SymbolRef`, `UnaryOp`, `BinaryOp`, `FunctionCall` — safe by
    construction, no `eval`/`exec`
  - `oec.modeling.expressions.parse_expression` — builds the same node tree from
    a string via the kernel's already-audited AST whitelist (one grammar, not two)
  - `oec.modeling.dimensions` — structural/dimensional validation over the tree;
    first real use of `DimensionalIncompatibilityError`
  - `oec.modeling.classify` — deterministic, non-silent problem classifier;
    first real use of `UnderdeterminedProblemError`/`OverdeterminedProblemError`
  - `oec.modeling.compile_linear` — `linear_program` variant compiled to an OPS
    document and solved via the existing `ops_to_linear_parts`/`solve_linear`
    (HiGHS) path; no new solver logic
  - `oec.modeling.compile_scalar_root` — `scalar_root` variant (v0: exactly one
    equation, one unknown) compiled to a residual function and solved via SciPy
    root-finding (`find_root_bracketed`/`find_root_from_guess`)
- **Minimal Backend Capability skeleton** (`oec.backends.registry`) —
  availability/version descriptors for `highs` and `scipy` only; the full
  registry (selection, fallback, adapters) remains a v2.4 item
- **Experimental skill `mathematics.solve_ir`** — classifies a submitted Math IR
  document and dispatches to the linear or scalar-root compiler
- ADR 0020: Math IR v0 foundation

### Changed

- Package version **2.1.0 → 2.2.0**
- `optimization.lp`, `optimization.milp` and `numerical.root_system` are
  unchanged; `mathematics.solve_ir` is purely additive

### Notes

- v2.2 stop gate proven: one LP and one scalar-root problem solved exclusively
  through the IR match the existing governed paths within tolerance
  (`tests/integration/test_math_ir_linear_parity.py`,
  `test_math_ir_scalar_root_parity.py`)
- Full local gate: global coverage ≥90% (new `oec.modeling`/`oec.backends`
  modules individually 83–96%), ruff lint/format PASS, mypy strict PASS,
  physical-unit audit PASS, skill contract audit PASS, forbidden-names PASS,
  bandit PASS
- v0 non-goals (see ADR 0020): MILP-in-IR, systems of equations in the
  scalar-root compiler, ODE-in-IR, tensor quantities, general uncertainty
  propagation, automatic unit rescaling during scalar-root evaluation, any
  `sympy` string-parsing path, and the full v2.4 Backend Registry
- See [docs/architecture/adr/0020-math-ir-foundation.md](docs/architecture/adr/0020-math-ir-foundation.md)

## [2.1.0] — 2026-07-27

### Added

- **Quantity API and dimensional contracts**:
  - JSON-safe dimension and conversion APIs on `QuantityValue`
  - explicit add/subtract/multiply/divide operations with a typed `QuantityOperationError`
  - rejection of incompatible dimensional operations
  - `same_dimension` as a distinct check from direct convertibility
  - separation of affine temperatures (`degC`/`degF`) from delta-temperature intervals
  - preserved original versus normalized input provenance
  - a small immutable SI-2019 constants catalogue (`c`, `h`, `e`)
  - representation-only `Uncertainty` and `UncertainQuantity` (general propagation excluded from v2.1)
- **Input/output physical enforcement**:
  - central normalization to canonical units for scalar and array quantities
  - `ResultDimensionalValidator` wired automatically for dimensional skills
  - fail-closed behavior for malformed, non-finite, unknown-unit and noncanonical outputs
- **Physical skill migration to `QuantityValue`-only contracts** (bumped to skill version `0.2.0`):
  `energy.balance`, `energy.load_metrics`, `battery.soc_step`
- **Automated authoring gate**: `scripts/audit_physical_units.py` — checks physical skill schemas
  for unclassified bare numeric fields, missing/invalid canonical units, malformed quantity
  contracts, undocumented dynamic-unit exceptions, and explicit dimensionless classification
  (9 physical skills scanned, 0 errors)

### Changed

- Package version **2.0.0 → 2.1.0**
- `ExecutionResult`, REST and MCP shapes remain unchanged

### Notes

- Full local gate: 863 tests passed (4 slow deselected), 91.33% coverage, ruff lint/format PASS,
  mypy strict PASS (91 source files), physical-unit audit PASS, skill contract audit 40/40,
  forbidden-names PASS
- Independently reviewed by GPT-5.6 Terra, Grok, Claude Opus; corrections closed include a
  private-Pint-API offset-unit check, direct-convertibility vs same-dimensionality for
  uncertainty, affine-vs-multiplicative temperature interval handling, dimension-string
  rendering, a rejected transitional bare-number allowance for energy/battery skills, and
  array-quantity coverage in central validation/normalization
- See [docs/implementation/v2.1-delivery-status-and-v2.5-next-steps.md](docs/implementation/v2.1-delivery-status-and-v2.5-next-steps.md)
  for full delivery evidence and the v2.2+ Math IR roadmap
- Math IR, Backend Capability Registry, and formal Verification remain **v2.2+** milestones

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
