# Changelog

All notable changes to Open Engineering Compute are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- MCP `agent.*` tools (`agent.default`, `agent.optimization_specialist`,
  `agent.applied_mathematics`, `agent.time_series`, `agent.energy`) failed
  with `ModuleNotFoundError: No module named 'agents'` when the MCP server
  was launched by an external host (e.g. Hermes running `uv run oec server
  mcp`) from a working directory other than the repo root — the `agents/`
  companion package lives outside `src/oec` and only resolves when the repo
  root happens to be on `sys.path`, which `pytest` provides incidentally but
  no real launcher guarantees. `oec.mcp.server` now resolves the repo root
  from its own file location and makes `agents/` importable at import time,
  independent of the caller's cwd or `PYTHONPATH`. See
  `docs/implementation/technical-debt.md` (D-CUR-21) for the open structural
  follow-up (packaging `agents/` properly instead of patching `sys.path`).
- MCP `call_tool()` only caught `OECError`/`ValueError`/`TypeError` around
  agent and raw-skill dispatch; any other exception (e.g. the
  `ModuleNotFoundError` above, or an unexpected bug in a specialist) escaped
  to the underlying `mcp` SDK's generic handler, which still returned a
  clean `isError=True` result but as an unstructured plain-text message
  instead of this codebase's own `{"error", "details": {"tool",
  "error_type"}}` JSON shape. `call_tool()` now catches unexpected
  exceptions on both dispatch paths and logs them (`oec.mcp.server`) before
  returning the same structured shape as every other error path.
- `oec server mcp`/`oec server api` silently started with zero registered
  skills when `--skills-root`/`OEC_SKILLS_ROOT` pointed at a missing or
  non-existent directory (`discover_skill_dirs` tolerates a missing root by
  design, for one-shot commands like `skills list`) — every tool call then
  failed downstream with no indication the root itself was the problem.
  Both server commands now fail fast with a clear error instead.
- `agent.default` — the documented default MCP entrypoint — was a dead end
  for free-text `request` in 4 of 5 domains: the router correctly inferred
  the domain from natural language, but the resulting specialist (every
  agent except `agent.applied_mathematics`, and even that one only for a
  narrow scalar-extrema grammar) immediately rejected the bare `request`
  with `ValueError`, requiring `demo_label` or `skill_id`+`inputs` instead.
  Confirmed by a real Ollama-driven stress test (`docs/implementation/
  OLLAMA_AGENT_STRESS_TEST_REPORT.md`). A specialist that receives a
  `request` it can't act on now returns a non-error
  `{"status": "needs_more_information", "candidates": [...]}` payload
  (new `oec.mcp.discovery` module) with each candidate skill's real input
  schema and a worked example, instead of raising — see
  `docs/mcp/README.md` ("Free-text `request` and `needs_more_information`")
  for the expected host behavior. Also fixed in the same pass:
  `_infer_domain_from_request`'s `"lp" in text`/`"ops" in text` were bare
  substring checks that misrouted any request containing "he**lp**" or
  "sh**ops**"/"dr**ops**" into the optimization domain; matching is now
  word-boundary-aware. See `docs/implementation/technical-debt.md`
  (D-CUR-22, D-CUR-23) for what's still open (ranking quality, orphan
  domains with no specialist at all).
- `agent.default` treated the mere *presence* of an `execution` key as a
  signal to route to `agent.scientific_reviewer`, even when it was an empty
  or incomplete placeholder — something local LLMs sometimes hallucinate
  alongside an otherwise clear optimization request. That diverted valid
  `ops`/`preferred_domain`/`request` calls into the reviewer, which then
  failed validating the empty `execution`. `_router_target_for` now only
  treats `execution` as a review signal via `_has_execution_payload()`,
  which requires the dict to actually carry `status`/`skill`/`method`/
  `started_at`; an empty or incomplete `execution` falls through to the
  next real signal (`ops`/`ops_document`, `preferred_domain`, `skill_id`,
  `demo_label`, or `request` inference) instead of winning by default.
  `agent.scientific_reviewer` called directly is unchanged — it still
  requires a real `execution` when invoked explicitly.
- The free-text discovery fallback (previous entry) told callers to retry
  `agent.optimization_specialist` with `skill_id` + `inputs`, but that
  specialist only ever accepted `ops` or `demo_label` — the promised retry
  loop was a dead end, confirmed by a live Ollama-driven stress test and an
  independent audit (`docs/implementation/oec-agent-router-post-audit-
  corrections.md`). `OptimizationSpecialist.run_skill()`
  (`agents/optimization_specialist/specialist.py`) now runs an explicit
  `optimization.*` skill directly via `Engine.run`, restricted to that
  domain prefix (anything else is a structured, explicit error); wired into
  `agent.optimization_specialist`'s dispatch in `src/oec/mcp/server.py`.

## [2.5.1] — 2026-07-30

A refinement release, not a new platform wave (no Physics/Chemistry/
multiphysics scope): reconciles the published catalog against the real
repository state, closes the most visible domain gap exposed by
model-facing tests, improves `agent.default` routing where the contract
already promises generic entry, and reduces the highest-value residual
coverage risk left after the v2.5 gate.

### Added — governed capabilities

Four new `timeseries.*` skills for classic autoregressive/autocorrelation
estimation, none of which existed anywhere in OEC before this release:

- `timeseries.autocorrelation` — sample ACF (biased/unbiased estimators).
- `timeseries.pacf` — partial ACF via the Levinson-Durbin recursion's
  reflection coefficients.
- `timeseries.ar_yule_walker` — AR(`order`) coefficient + innovation
  variance estimation.
- `timeseries.levinson_durbin` — the shared `O(p^2)` Toeplitz-solve engine
  behind the two skills above, exposed directly for callers who already
  have an autocorrelation/autocovariance sequence in hand. Honestly
  reports (rather than raising) when an input sequence isn't a valid
  positive-semidefinite autocorrelation sequence.

All four share one hand-rolled kernel module
(`src/oec/kernel/timeseries/ar.py` — no SciPy/pandas primitive exists for
Levinson-Durbin; OEC does not depend on statsmodels) and carry the full
skill contract (schema/implementation/validation/references/examples/
golden+validation tests) plus a dedicated kernel-level unit test file with
hand-derived closed-form expected values.

### Added — improved routing behavior

`agent.default`'s request-keyword router recognizes autocorrelation/PACF/
Yule-Walker/Levinson-Durbin/autoregression intent and routes it to
`agent.time_series`. No natural-language argument-extraction parser was
built for arbitrary numeric series (unlike the existing mathematics
scalar-extrema case) — a request-only call in this domain now selects the
right specialist but still fails with the existing honest "requires
demo_label or skill_id+inputs" message rather than hallucinating a route
or a number. The realistic invocation — request text for routing,
explicit `skill_id`+`inputs` for the actual numbers — is proven end-to-end
in a new integration test. Explicit `skill_id` still wins over
request-text keywords, even when the text itself contains AR/timeseries
terms.

### Changed — documentation reconciliation

- Package version **2.5.0 → 2.5.1**.
- `docs/implementation/skill-inventory.md`: **63 → 67** skills (the four
  new ones above); per-domain counts refreshed.

### Fixed — residual coverage risk reduction

Targeted coverage push on the four weakest modules named in
`docs/implementation/v2.5-critical-path-coverage.md`:

- `kernel/timeseries/quality.py`: 67% → **100%**.
- `kernel/timeseries/ops.py`: 68% → **96%**.
- `kernel/timeseries/timegrid.py`: 70% → **100%**.
- `kernel/optimization/feasibility.py`: 77% → **84%**.

Aggregate suite coverage rose from 90.67% to **92.0%** (1362 → 1425 tests).

### Notes — residual limitations that remain open

- `kernel/optimization/feasibility.py`'s remaining coverage gap is not a
  shortfall to chase further without a design decision first: its
  precheck branches (`check_bound_conflicts`, empty-coefficient
  constraint detection) are unreachable through any of its three public
  entrypoints, because `oec.ops.models.validate_ops` — which all three
  call first — already rejects the same malformed input earlier
  (Pydantic rejects `lower > upper`; the OPS JSON Schema requires
  non-empty `coeffs`). Flagged as a follow-up rather than force-covered
  or silently fixed.
- Burg's method (`timeseries.ar_burg`), the documented optional stretch
  item, was not implemented.
- No AIC/BIC order selection, standard errors, or confidence intervals are
  reported by any of the four new skills.
- REST/MCP still ship without authentication or rate limiting; no
  OS-level sandbox isolation exists yet (unchanged from prior releases).

## [2.5.0] — 2026-07-29

This release closes both **v2.4** (Backend Registry + Verification Engine)
and **v2.5** (Math IR / kernel consolidation + release gates) in a single
version bump — neither had a package version, CHANGELOG, or README update at
implementation time, by explicit design mirroring the v2.1/v2.2 pattern
(commits stayed on `oec==2.3.0` while the work landed). See
[v2.1-delivery-status-and-v2.5-next-steps.md](docs/implementation/v2.1-delivery-status-and-v2.5-next-steps.md)
§6 Step E for the consolidation gate this closes.

### Added — v2.4 Backend Registry + Verification Engine (ADR 0021)

- **Backend Capability Registry** (`src/oec/backends/`): static per-backend
  capability domains (numpy/scipy/HiGHS), thin availability probes, backend
  selection by capability, and a structured `ERROR` outcome when a method's
  declared backend is unavailable instead of a raw exception.
- **Verification Engine** (`src/oec/verification/`): `VerificationReport`
  with pre-checks (`input_validation`, `backend_fit`) and post-checks
  (`convergence`, `residuals_and_conditioning`, `lp_gap_report`,
  `provenance_integrity`), wired additively into `ExecutionService.execute`
  as `validation["verification"]`. `ExecutionResult`'s required shape is
  unchanged.
- Independent review (fable) found and closed two real defects before this
  closeout: `lp_gap` had a hardcoded `passed=True` (renamed to
  `lp_gap_report`, informational — no configured gap tolerance exists to
  evaluate against); `reproducibility` only confirmed a hash was present, not
  that anything was re-run (renamed `provenance_integrity`). The Math IR LP
  parity test was also rewritten to go through the real `optimization.lp`
  skill instead of re-deriving the same internal call sequence it was meant
  to check.

### Added — v2.5 computational kernel unification (ADR 0022)

- Root-finding, root-system solving, ODE integration, interpolation, and
  numerical integration unified under `src/oec/kernel/computational/` behind
  a shared `ComputationalDiagnostics` model and per-domain result wrappers.
  Interpolation/integration had no kernel module before this (logic was
  inline in each skill); differentiation did not exist anywhere.
- New experimental skill: `mathematics.differentiate` (central/forward/
  backward finite differences; hand-rolled since `scipy.misc.derivative` was
  removed from modern SciPy).
- No existing skill's schema, manifest, version, or golden tests changed —
  each skill's `implementation.py` already reshaped the kernel's raw output
  into its own result/diagnostics dict.

### Added — v2.5 release gates

- **Golden-set distribution gate**: the "Mathematics Complete" hard gate
  (≥130 canonical cases across 8 domains with explicit per-domain minimums,
  `OEC_V3_IMPLEMENTATION_PLAN.md` §9) is now met — **193** total cases across
  all 8 buckets, including a new `tests/golden/test_validation_and_failures.py`
  (22 cases) covering non-convergence, solver infeasibility, and
  linear-algebra/physical/dimensional/expression/schema validation failures.
  See `docs/implementation/v2.5-golden-set-expansion.md`.
- **Critical-path coverage gate**: the scientific-correctness path
  (execution/validation/verification/kernel/modeling/ops/backends/core/sdk/
  errors — distinct from CLI/REST/MCP adapters and skill packaging) measured
  for the first time at **90%** aggregate, meeting the gate.
  `src/oec/kernel/` alone sits at 86%; see
  `docs/implementation/v2.5-critical-path-coverage.md` for the 11 weakest
  submodules, tracked as `D-CUR-19`.
- **Public API docstring coverage gate**: new `scripts/audit_public_api_docs.py`
  (AST-based, no import side effects) scanning SDK/CLI/REST/MCP entrypoints
  and the `ExecutionResult`/OPS/errors contract shapes — **87.8% → 100%**
  after five one-line docstring additions, no schema/behavior change.
- `forbidden_names` gate back to zero hits (reworded a stray private-product
  term in `v2.4-team-brief.md`).

### Added — MCP agent-first tool catalog

- The pre-existing `agents/` companion layer (Optimization Specialist,
  Scientific Reviewer, Applied Mathematics, Time-Series, Energy) is now
  wired into the MCP server as first-class tools: an `agent.default` router
  plus one `agent.<specialist>` tool per domain, and a `list_agents`
  discovery tool. Raw skill tools remain available, now nudged toward the
  agent-first path in their descriptions.
- `agent.default` additionally accepts a free-text `request` field and
  infers the target specialist from keyword heuristics (mathematics/energy/
  timeseries/optimization/review) when no other routing signal (`ops`,
  `execution`, `preferred_domain`, `demo_label`, `skill_id`) is present.
- The Applied Mathematics Specialist's new `run_request()` handles a narrow
  class of natural-language scalar-extrema requests ("find the max/min of
  f(x)=... on [a,b]", including clock-offset phrasing like "t hours after
  noon"): it normalizes the expression and answers by running
  `mathematics.optimize_scalar` twice (min, and negated for max) through the
  governed `Engine` path — no numerical answer is computed outside OEC.

### Changed

- Package version **2.3.0 → 2.5.0**.
- `docs/implementation/skill-inventory.md` reconciled against the real
  `skills/` tree: **40 → 63** skill packages (the count had drifted stale
  across the v2.2–v2.5 work above without an inventory refresh); per-domain
  counts and the skills added since each prior version are now listed.
- `docs/implementation/technical-debt.md` reconciled: `D-CUR-14` (Backend
  Registry/Verification) closed; `D-CUR-19` (kernel coverage residual)
  opened.

### Notes

- `src/oec/kernel/` coverage (86%) remains below the 90% bar the rest of the
  critical path clears — tracked as `D-CUR-19`, not blocking this gate
  (aggregate critical-path coverage is 90%).
- REST/MCP still ship without authentication or rate limiting (unchanged
  from prior releases; `D-CUR-10`).
- Public GitHub release remains a separate **v3.0** milestone.

## [2.3.0] — 2026-07-27

### Added — v2.3 Wave C + Applied Math Complete (private)

Three experimental optimization skills (Wave C):

- `optimization.pareto_lp` — bi-objective Pareto via weighted-sum sweep (HiGHS)
- `optimization.cvar_lp` — linear CVaR (Rockafellar–Uryasev; HiGHS)
- `optimization.robust_lp` — robust LP with box uncertainty on constraint RHS

Kernels: `oec.kernel.optimization.{pareto,cvar,robust}`.

### Fixed — Wave A/B scientific correction package (A23/B23)

- `statistics.intervals`: population SD path; skill **0.2.0**
- `optimization.infeasibility_explain`: honest drop-one naming; no unproven IIS claims
- `control.kalman_filter`: Joseph update, PSD/PD checks, structured numerical errors
- `uncertainty.propagate_linear`: `nominal` checks + `nominal_output` in schema (**0.2.0**)
- Morris / spectral stability / PID: method honesty + version bumps **0.2.0**
- See `docs/implementation/v2.3-ab-correction-report.md` and acceptance seal
  `docs/implementation/v2.3-accepted-and-merge-prep.md`.

### Changed

- Package version **2.3.0b0 → 2.3.0** (v2.3 Applied Math expansion closed for
  private alpha: Waves A+B+C).
- **21** new applied skills since 2.2.0 (11 A + 7 B + 3 C); catalog **62** skills.
- V3 partial gate (≥15 new applied skills with contracts) **met**.

### Notes

- Wave C is v0: supported Pareto points only; CVaR min-only; robust equalities
  not supported.
- Public GitHub remains a **v3.0** milestone.
- Formal Verification Engine + Backend Registry remain **v2.4** (team brief:
  `docs/implementation/v2.4-team-brief.md`).

## [2.3.0b0] — 2026-07-27

### Added — v2.3 Wave B (uncertainty / dynamics / control)

Seven experimental skills (full contracts + golden/validation tests):

- `uncertainty.lhs` — Latin Hypercube design over rectangular bounds
- `uncertainty.morris` — Morris elementary effects for linear models
- `uncertainty.propagate_linear` — first-order delta-method propagation
- `dynamics.state_space_simulate` — discrete / continuous (ZOH) LTI simulation
- `dynamics.stability_margins` — eigenvalue stability + margin
- `control.pid_discrete` — position-form discrete PID (+ optional saturation)
- `control.kalman_filter` — discrete linear Kalman filter

Kernels: `oec.kernel.uncertainty.{sampling,morris,propagate}`,
`oec.kernel.dynamics.{state_space,stability}`,
`oec.kernel.control.{pid,kalman}`.

### Changed

- Package version `2.3.0a0 → 2.3.0b0` (Wave A+B beta; Wave C still open).
- Combined Wave A+B yields **18** new applied skills since 2.2.0 (V3 partial
  gate ≥15 satisfied; Wave C optional).

### Notes

- Morris Wave B is **linear-model only** (no arbitrary callables in sandbox).
- Full Sobol estimators and black-box SA remain future work.
- No ExecutionResult / REST / MCP shape changes.

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
