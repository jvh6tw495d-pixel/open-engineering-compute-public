# Codebase map

Living summary of OEC's structure. Updated at the end of each sprint (see
`docs/development/graphify.md` for the tool used to help maintain it).

**As of 2026-07-27:** package **`oec==2.0.0`** Scientific Kernel.
**GPT handoff:** [../implementation/GPT_CONSTRUCTION_HANDOFF.md](../implementation/GPT_CONSTRUCTION_HANDOFF.md)
**Next build:** v2.1 Quantities (`kernel/units` consolidation).

## Main components (v2.0.0)

| Component | Path | Status |
|---|---|---|
| **Scientific Kernel (`oec.core`)** | `src/oec/core/` | **v2.0** — `ScientificResult`, `ValidityDomain`, `Diagnostic`, `ProvenanceRecord`, types, core errors; ADR 0019 |
| Shared value objects | `src/oec/common.py` | implemented — `VersionedRef` |
| Base error hierarchy | `src/oec/errors.py` | implemented — `OECError` + subclasses; core extends with domain errors |
| Skill manifest model | `src/oec/skills/schemas/manifest.py` | implemented — `SkillManifest`, `MethodRef` (`iterative: bool`, ADR 0013) |
| Execution models | `src/oec/execution/models.py` | implemented — `ExecutionResult` **unchanged** in 2.0 |
| Skill Loader/Registry/Lifecycle | `src/oec/skills/{loader,registry,lifecycle}/` | implemented |
| CLI | `src/oec/cli/main.py` | implemented — `oec version`, skills, run, server |
| Public Python SDK | `src/oec/sdk.py` | `Engine.run` → ExecutionResult; **`Engine.run_scientific`** → ScientificResult |
| Validator factory | `src/oec/execution/factory.py` | implemented |
| Units kernel | `src/oec/kernel/units/` | implemented — **v2.1 target** for Quantity consolidation |
| Numerics kernel | `src/oec/kernel/numerics/` | expressions AST, root finding, vector compile |
| Optimization kernel | `src/oec/kernel/optimization/` | scalar, constrained, curve_fit, HiGHS path |
| OPS | `src/oec/ops/` | v0.1 LP/MILP model |
| Validation Engine | `src/oec/validation/` | multi-layer validators |
| Execution Service | `src/oec/execution/` | service, runner, sandbox, status, provenance |
| Agents (outside wheel) | `agents/` | 5 specialists; formulate only |
| Skills catalog | `skills/**` | ~40 experimental skills |
| **REST API** | `src/oec/api/app.py` | implemented |
| **MCP server** | `src/oec/mcp/server.py` | implemented |

### Scientific Kernel modules (`src/oec/core/`)

- `scientific_result.py` — frozen `ScientificResult` + `from_execution_result`
- `validity.py` — `ValidityDomain`
- `diagnostics.py` — `Diagnostic`, legacy dict → typed list
- `provenance.py` — `ProvenanceRecord` + backends
- `types.py` — `MethodRef`, `BackendRef`, `Assumption`
- `errors.py` — scientific domain errors (subclass `OECError`)

### Numerics kernel, module by module

- `expressions.py` — `compile_expression()`: parses a user-submitted
  `f(x)` string into a safe callable. Never calls `eval()`/`exec()`
  (plan section 4.7 is an absolute prohibition, not "prohibited unless
  careful") — walks a whitelisted `ast` tree once, then *interprets*
  that validated tree directly. A SciPy/SymPy-`parse_expr`-based
  approach was tried and rejected during development: even sandboxed,
  it still accepted `().__class__.__bases__[0].__subclasses__()`, a
  known Python sandbox escape, because SymPy's parser is itself built
  on `eval()`.
- `root_finding.py` — `find_root_bracketed` (brentq/bisect),
  `find_root_from_guess` (secant/newton), `select_default_method()` (the
  explicit, documented method-selection rule — plan section 4.4). All
  return the same `RootFindingDiagnostics` shape regardless of method.
- `compile_expression_vector()` (Sprint 05, new) — N-variable
  generalization of `compile_expression()`, same restricted-AST grammar
  and safety guarantee, for models/constraints with more than one named
  symbol (`optimize_constrained`'s objective/constraints,
  `curve_fit`'s model). `compile_expression`'s own public signature and
  behavior are unchanged — the module's private `_validate_node`/
  `_eval_node` helpers were generalized internally (symbol set /
  bindings dict instead of one hardcoded name) so both functions share
  one whitelist-then-interpret implementation.

### Optimization kernel, module by module (Sprint 05, new)

- `diagnostics.py` — `OptimizationDiagnostics`: **one** shared model
  every optimization skill reports through (`method`, `converged`,
  `message`, `n_iterations`, `n_function_evaluations`, plus the
  method-specific `optimality`, `constraint_violation`, `feasible`,
  `residuals`, `covariance`, all `Optional`). A field a given method
  can't measure stays `None` — never fabricated to make three skills'
  output look uniform when it isn't.
- `scalar.py` — `minimize_scalar()` wraps `scipy.optimize.minimize_scalar`
  (bounded/brent/golden). `bounds` selects `bounded` by default; `bounds`
  combined with any other method is rejected, not silently dropped.
- `constrained.py` — `minimize_constrained()` wraps
  `scipy.optimize.minimize` (SLSQP default; `trust-constr` explicit
  alternative). Reports SciPy's *native* `optimality`/`constr_violation`
  when the method actually computes them (`trust-constr`); SLSQP
  doesn't, so `constraint_violation`/`feasible` are computed by
  evaluating each constraint at the solution instead.
- `curve_fit.py` — `fit_curve()` wraps `scipy.optimize.curve_fit` (`lm`
  default when unbounded — it doesn't support bounds at all; `trf` once
  bounds are given; `dogbox` as an explicit bounded alternative). SciPy
  raises a bare `RuntimeError` on non-convergence with no
  partial-progress state; caught and turned into
  `diagnostics.converged = False`, with `params`/`residuals`/
  `covariance` falling back to the initial guess (documented, not
  silently approximated as something better).

### Validator auto-discovery and the `oec` SDK (Sprint 06, new; ADR 0014)

- **`src/oec/execution/factory.py`** — `build_validators(skill) ->
  (input_validators, result_validators)`: reads
  `skill.manifest.validation` (`ValidationPolicy`) and assembles the
  right validator list. `schema`/`dimensional`/`numerical` map to
  shared validator classes; `mathematical` discovers the skill's own
  `validation.py` class by introspection (defined in that module,
  has a `layer` `ClassVar` and a callable `validate` — duck-typed,
  since `InputValidator`/`ResultValidator` aren't `@runtime_checkable`);
  `physical` stays documentation-only (no shared `PhysicalValidator`
  exists — a skill needing physical checks calls
  `oec.validation.physical`'s helpers from its own `validation.py`, the
  same pattern `mathematical` already used). `InvariantValidator` is
  always included, not policy-gated — a structural guarantee, not an
  opt-out layer. Replaced every `tests/integration/test_*_end_to_end.py`'s
  hand-built `ExecutionService(input_validators=[SchemaValidator(),
  <SkillSpecificValidator>()], ...)` with `build_validators(skill)` —
  all 26 tests across the six skills pass unchanged, the regression
  guard that auto-discovery reproduces the prior hand-wiring exactly.
- **`src/oec/sdk.py`** — `Engine`/`run()`: the public "import direto em
  Python" surface deferred since Sprint 03, distinct from
  `oec.testing` (a test-authoring helper, not a runtime facade).
  `ExecutionService` still binds one fixed validator list per instance
  (Sprint 03 design, unchanged); `Engine` owns one `ExecutionService`
  per `(skill_id, version)`, built lazily via `build_validators` and
  cached, so a long-lived `Engine` (the CLI's process, or a future
  REST server) assembles each skill's validators once, not once per
  call. Tolerates individual broken-skill registration failures
  (`Engine.registration_failures`) rather than refusing to construct —
  mirrors the CLI's existing `skills list`/`inspect` tolerance.
- **`oec run <skill_id>`** (`src/oec/cli/main.py`): built on `Engine`.
  Reads inputs from exactly one of `--input-file`/`--input`/stdin.
  Exit code reflects `ExecutionStatus` (frozen in ADR 0014): `0` for a
  usable result (`VERIFIED`/`VALIDATED`/`CONVERGED_WITH_WARNINGS`/
  `APPROXIMATE`), `2` for `INCONCLUSIVE`, `3` for `INVALID`, `4` for
  `FAILED`, `1` for a CLI-level error that never produced a result at
  all (unknown skill, malformed `--input` JSON).
- **`NumericalDiagnosticsValidator` fixed** (`src/oec/validation/numerical.py`):
  an independent review of Sprint 05 found its key names
  (`iterations`/`max_iterations`/`residual`/`tolerance`, all read from
  `diagnostics`) matched **zero** of the six shipped skills' actual
  diagnostics shapes — `max_iterations`/`tolerance` are caller
  *inputs*, never echoed into `diagnostics`, so `CONVERGED_WITH_WARNINGS`
  was practically unreachable since Sprint 03. Now reads
  `normalized_inputs` for `max_iterations`/`tolerance` and falls back
  across the real key names skills use (`n_iterations`, `abs_error`,
  a `residuals` list's max magnitude).

### REST API and MCP server (Sprint 07, new; ADR 0015)

Both are thin adapters over one shared, warmed `oec.sdk.Engine` — no
new validator-wiring story, no scientific-content reshaping (ADR 0005).

- **`src/oec/api/app.py`** — `create_app(skills_root)` returns a
  FastAPI app; a `lifespan` handler builds and `.warm()`s one `Engine`
  for the app's whole lifetime. `GET /health`, `GET /skills` (wraps
  `registry.search`), `GET /skills/{skill_id}` (404 on miss), `POST
  /skills/{skill_id}/run`. Status codes are transport-only: `200` with
  the full `ExecutionResult` body even for `INVALID`/`FAILED`/
  `INCONCLUSIVE` (those are scientific outcomes read from `body.status`,
  not transport failures); `404` unresolvable skill; `422` a request
  body that doesn't even parse (`RunRequest` forbids extra fields).
  `oec server api --host --port` launches it via `uvicorn.run()`.
- **`src/oec/mcp/server.py`** — `build_tools(engine)` returns one MCP
  `Tool` per registered skill (name = skill id, `inputSchema` = that
  skill's own real `input.schema.json`, not a hand-written copy) plus a
  fixed `list_skills` discovery tool. `call_tool(engine, name,
  arguments)` dispatches by name and returns the full `ExecutionResult`
  JSON as a single text content block. Uses the **low-level** MCP
  `Server` API, not the `FastMCP` convenience wrapper — `FastMCP`
  derives a tool's schema from a Python function's type annotations and
  cannot accept an arbitrary pre-built JSON Schema dict, which is
  exactly what's needed here. `run_stdio_server(skills_root)` is the
  entrypoint (`oec server mcp`): builds + warms an `Engine`, serves over
  stdio. Built by Grok in an isolated worktree in parallel with the REST
  API (Claude Code) — the first successful Grok parallel handoff since
  Sprint 04 (blocked by the environment's permission classifier in
  Sprints 05 and 06; see "Decisions").
- **`oec.sdk.Engine` now serializes every execution through one lock**
  (`threading.Lock`, added this sprint): at most one skill subprocess
  runs at a time per `Engine` instance, regardless of how many
  concurrent REST/MCP callers share it. Direct consequence of ADR 0012's
  own forward-reference ("execução síncrona no Alpha... revisit if
  Sprint 07's REST API needs to run many executions concurrently") —
  with zero OS-level resource isolation per subprocess, unbounded
  concurrency is a resource-exhaustion risk this project has no
  sandboxing story for yet. Also fixes a real bug: the `_services` cache
  was previously a plain `dict` with no protection against concurrent
  first-calls to the same skill racing to build it.
- **`Engine.warm()`** (added this sprint) — eagerly builds every
  registered skill's `ExecutionService`/validators at startup instead
  of lazily on first call, so a skill's validator-discovery failure
  (`SkillEntrypointError`, ADR 0014) surfaces at server boot, not
  mid-request. Optional for `oec run` (one skill, one process — nothing
  to warm ahead of that); required for REST/MCP's startup hook.
- **`tests/integration/test_adr0005_conformance.py`** — the acceptance
  bar ADR 0005 names for every interface, exercised across all four
  (SDK, CLI, REST, MCP) at once for the first time: the same
  `ExecutionRequest` must agree on status, numeric result, method
  identity, and `diagnostics.converged`, for both a converged case and
  an `INVALID` case (confirming transport-level differences — CLI exit
  code, HTTP status, MCP `isError` — are still allowed to differ while
  the scientific content doesn't).

### `oec.testing` — a small public testing SDK

- `load_skill_module(skill_dir, module_name)` — dynamically imports a
  skill's sibling `implementation.py`/`validation.py` under a name
  unique to that skill directory. Needed because every skill package
  has a same-named `implementation.py`; a naive dynamic import would
  have the second skill's tests import the first skill's cached module
  when a single `pytest` run covers many skills.
- `write_skill_dir(...)` — writes a minimal, overridable skill directory
  to disk (used by OEC's own loader/registry/CLI tests, and available to
  any third-party skill author's tests too).
- Moved here from `tests/_skill_helpers.py` this sprint after adding a
  skill's own test suite surfaced a real pytest collision (see "Decisions").

### MVP math skills (plan section 14.1, 3 of 6 math skills done)

All three follow the same package layout (`skill.md`, `skill.yaml`,
`input.schema.json`, `output.schema.json`, `implementation.py`,
`validation.py`, `references.md`, `examples/`, `tests/`), established by
`solve_root` and copied by `interpolate`/`integrate`.

- **`mathematics.solve_root`** — brentq/bisect/secant/newton.
  `method.iterative: true`. Method selection: bracket → brentq;
  initial_guess only → secant; `newton` requires an explicit derivative.
  5 golden cases, all sourced from `mpmath.findroot` (independent of the
  SciPy solvers under test) — includes the Burden & Faires textbook
  cubic and the Dottie number (`cos(x)=x`).
- **`mathematics.interpolate`** — linear (`numpy.interp`)/cubic_spline/
  pchip. `method.iterative: false` (closed-form construction+evaluation,
  no convergence concept). `method` is **required**, no auto-select —
  documented in `skill.md` as a deliberate choice: the three methods are
  philosophically different (robust/smooth/shape-preserving), none is
  "more correct" by default. Extrapolation outside `[min(x), max(x)]` is
  a `WARNING`, not an `ERROR`.
- **`mathematics.integrate`** — two mutually exclusive modes: function
  (`expression` + `bounds` → `scipy.integrate.quad`, adaptive) XOR
  tabulated (`x`/`y` → Simpson if ≥3 points else trapezoid, auto-selected
  by point count). `method.iterative: true` for the *whole* skill (a
  static, manifest-level declaration — can't vary by input), because
  function mode is genuinely adaptive; the tabulated path always reports
  `diagnostics["converged"] = true` (a fixed-formula computation given
  samples has no iteration to fail), satisfying ADR 0013 either way.

All three built on `oec.kernel.numerics`, none reimplement solving logic
in `implementation.py`. `interpolate`/`integrate` were built by Grok in
an isolated git worktree in parallel with this sprint's closing work,
after `solve_root` (built solo) established the template — zero file
overlap, independently gated before merge (402 tests, 97.30% coverage,
matched exactly what was reported).

### Optimization skills (Sprint 05, 3 of 6 math skills done)

Same package layout as the Sprint 04 skills, now on top of
`oec.kernel.optimization` instead of `oec.kernel.numerics`:

- **`mathematics.optimize_scalar`** — bounded/brent/golden scalar
  minimization. `method.iterative: true`. Template skill for the
  family; golden cases include a closed-form-verified multi-minima case
  (`x**4 - x**2`, two tied global minima) documenting explicitly that
  bounded Brent returns whichever minimum its bracket contains.
- **`mathematics.optimize_constrained`** — N-variable, box- and
  nonlinearly-constrained minimization (SLSQP default, `trust-constr`
  alternative), built on `compile_expression_vector`. Golden cases:
  a Lagrange-multiplier-verified constrained minimum, two of
  Himmelblau's function's four well-known tied global minima reached
  from different `x0` (SLSQP is a local optimizer), and a
  mutually-contradictory-constraints case asserting
  `converged=False`/`feasible=False` comes back as a diagnostic, not a
  crash.
- **`mathematics.curve_fit`** — nonlinear least-squares fitting (`lm`
  default when unbounded, `trf`/`dogbox` for bounded problems), also on
  `compile_expression_vector` (independent variable fixed as `x`,
  `parameter_names` supplies the rest of the symbols). Golden cases use
  noiseless data generated from known true parameters as the
  independent oracle (ground truth fixed by construction, not derived
  from any solver), plus a case showing a poor `initial_guess` on a
  periodic parameter converges to a different, wrong local optimum
  (`converged=True` in SciPy's sense, but the wrong parameters).

All three built and reviewed by Claude Code solo, not the planned
Claude Code / Grok parallel split: Grok's autonomous CLI launch
(`grok -p ... --always-approve` / `--permission-mode auto`) was blocked
by this environment's own permission classifier under every mode tried.
Per the classifier's own guidance, no further workaround was attempted;
the isolated worktree created for the handoff was removed unused, and
both remaining skills were built sequentially instead. See "Decisions"
below.

## Dependencies (declared, not all wired yet)

- Core: `pydantic`, `numpy`, `scipy`, `sympy` (still unused directly —
  the safe expression evaluator uses stdlib `ast`, not SymPy), `pint`,
  `pyyaml`, `typer`/`rich`, `jsonschema`.
- Dev/quality: ruff, mypy, pytest, pytest-cov, hypothesis, pre-commit,
  bandit, `types-PyYAML`, `types-jsonschema`, `scipy-stubs` (new this
  sprint, for `oec.kernel.numerics.root_finding`'s mypy strict pass).
- `pytest` now runs with `--import-mode=importlib` and
  `testpaths = ["tests", "skills"]` (see "Decisions").

## Entrypoints

- `oec` console script → `oec.cli.main:app` (`version`,
  `skills list/inspect/validate`, `run` — new this sprint, ADR 0014).
  `oec run mathematics.solve_root --input '{"expression": "x**2 - 2",
  "bracket": [0, 2]}'` executes through the real `Engine`/
  `ExecutionService`/sandboxed subprocess, not a mock. `oec skills list
  --skills-root skills` lists all 6 real MVP skills.
- **`oec.sdk.Engine`/`oec.sdk.run`** — the public Python SDK;
  `import oec; result = oec.sdk.run("mathematics.solve_root",
  {...}, skills_root="skills")` or a longer-lived
  `oec.sdk.Engine(skills_root="skills")` for repeated calls.
- **`oec server api`/`oec server mcp`** (new this sprint, ADR 0015) —
  REST (`uvicorn`) and MCP (stdio) servers, both requiring their
  respective optional extras (`uv sync --extra api` / `--extra mcp`);
  `oec.cli.main` imports `fastapi`/`uvicorn`/`mcp` lazily inside each
  command so the base install (no extras) never needs them.

## Execution flow (current state)

Unchanged pipeline shape from Sprint 03 (`resolve → input validators →
sandbox → result validators → compute_status → provenance`), now proven
against six real skills — and, as of this sprint, validators are
assembled via `oec.execution.factory.build_validators` (ADR 0014)
instead of hand-wired per test:
`tests/integration/test_solve_root_end_to_end.py`,
`test_interpolate_end_to_end.py`, `test_integrate_end_to_end.py`,
`test_optimize_scalar_end_to_end.py`,
`test_optimize_constrained_end_to_end.py`,
`test_curve_fit_end_to_end.py` each resolve the skill, call
`build_validators(skill)`, and execute through the actual sandboxed
subprocess. `tests/integration/test_sdk_engine.py` exercises the same
auto-discovery path through `Engine` directly, and
`tests/installation/test_installation_smoke.py` (new, opt-in/slow —
`uv run pytest -m slow --no-cov`) proves the installed `oec` console
script works end to end from a real wheel install, not just the source
tree.

`QuantityValue`/`normalize()`/`x-oec-unit` remain unused by any real
skill — all six MVP math skills are dimensionless by design (see each
skill's "Units and dimensions" section in `skill.md`). Units enter the
picture with the electrical skills (Sprint 08).

## Decisions

- **`SkillManifest.method` is now `MethodRef`, not `VersionedRef`**
  (ADR 0013): a method must declare `iterative: bool` explicitly. Fixed
  a real bug an independent review caught before any skill existed to
  trigger it — an iterative method's implementation forgetting to
  report `diagnostics["converged"]` was indistinguishable from an exact
  method with no convergence concept, both silently producing the
  strongest status (`VERIFIED`).
- **ADR 0013 amendment (Sprint 05)**: `diagnostics["converged"]` may be
  present but explicitly `null`, meaning "this call was exact" —
  distinct from the key being missing (still `FAILED`). Fixed a real
  status inconsistency: `mathematics.integrate`'s exact tabulated mode
  got `VALIDATED` instead of `VERIFIED` purely because it shares a
  manifest with an adaptive function mode declaring `iterative: true`.
- **`mathematics.integrate`'s function-mode convergence check now uses
  `quad(..., full_output=True)`** and treats QUADPACK's explain message
  (returned only on a real problem) as the authoritative signal,
  alongside `abs_error <= tolerance` — comparing `abs_error` to
  tolerance alone is a false-convergence risk for integrands that
  genuinely trip QUADPACK's subdivision limit (independent review of
  Sprint 04).
- **`ExecutionService` validator calls are now individually
  try/excepted** — a crashing validator becomes an `ERROR`-severity
  outcome (fail closed) instead of taking down the whole service.
- **`--import-mode=importlib`** — every skill's own test suite uses the
  same file names (`test_golden.py`/`test_properties.py`/
  `test_validation.py`, per plan section 8), which collided with each
  other and with `tests/unit/test_golden.py` under pytest's default
  rootless import mode (requires unique basenames). Switched to
  `importlib` mode (resolves by full path, no basename uniqueness
  needed), which in turn required moving `tests/_skill_helpers.py`'s
  `sys.path`-dependent helper into the properly-installed `oec.testing`
  package.
- **Validator auto-discovery landed this sprint** (Sprint 06, ADR
  0014) — `build_validators(skill)` reads `skill.manifest.validation`
  and discovers the skill's own `validation.py` validator by
  introspection; see "Validator auto-discovery and the `oec` SDK"
  above. `ExecutionService` itself is unchanged — it still binds one
  fixed validator list per instance; `Engine` is what builds the right
  list per skill and caches the resulting service.
- **`physical: true` stays documentation-only** (ADR 0014) — no shared
  `PhysicalValidator` class exists (unlike `dimensional`, which already
  has `DimensionalValidator`); a skill needing physical-limit checks
  calls `oec.validation.physical`'s helpers from its own
  `validation.py`. Revisit only if a future skill needs a *shared,
  cross-skill* physical check, not before.
- **`oec run`'s exit codes are frozen by ADR 0014**: `0` for a usable
  result, `2`/`INCONCLUSIVE`, `3`/`INVALID`, `4`/`FAILED`, `1` for a
  CLI-level error that never produced an `ExecutionResult` (unknown
  skill, malformed `--input` JSON).
- **Grok's autonomous CLI launch was blocked in Sprints 05 and 06**:
  `grok -p ... --always-approve` and `--permission-mode auto` were both
  denied by this environment's own permission classifier both times,
  unrelated to Grok itself — it had worked in Sprint 04. Both sprints'
  work was built by Claude Code solo instead. **A cheap re-probe at the
  start of Sprint 07 Fase B (`grok -p "print ok" --permission-mode
  auto`, ~2 minutes) succeeded** — the block was not permanent/
  environment-fixed. Grok built the MCP server (Track 2) in an isolated
  worktree while Claude Code built the REST API (Track 1) in parallel,
  the first successful Grok handoff since Sprint 04. Lesson for future
  sprints: re-probe cheaply each time rather than assuming either
  "always blocked" or "always available" from the last sprint's result.
- **`oec.sdk.Engine.run()` serializes all executions through one lock**
  (ADR 0015) — see "REST API and MCP server" above. This is an
  Alpha-stage concurrency bound, not a performance target; revisit only
  alongside real OS-level sandboxing (ADR 0012's deferred hardening
  sprint), which is the actual prerequisite for safe concurrent
  execution, not a locking strategy change.
- **REST status codes are transport-only** (ADR 0015 §1) — `200` even
  for `INVALID`/`FAILED`/`INCONCLUSIVE`. Deliberately diverges from
  `oec run`'s exit-code model (ADR 0014), because HTTP responses always
  have a body to inspect while a shell exit code is the only signal
  available without one.
- **MCP exposes one tool per skill** (ADR 0015 §2), not a single
  generic `run_skill(skill_id, inputs)` tool — makes every skill a
  self-describing MCP tool with its own real input schema, matching the
  project's skill-first thesis (ADR 0001), at the cost of the tool list
  growing with the skill catalog (6 tools today).

## Known structural debt

- `runner.py`'s `main()`/`__main__` still not instrumented by coverage
  across the subprocess boundary (known since Sprint 03).
- `SkillLifecycle.validate_transition` still not called anywhere at
  runtime (known since Sprint 01).
- Development telemetry (plan section 19: cost per accepted task) still
  not implemented — flagged by the independent Sprint 00-02 review,
  still open.
- No `docs/skills/`, `docs/integrations/`, `docs/contributing/`,
  `docs/concepts/` content yet (`docs/api/`, `docs/mcp/` landed this
  sprint).
- No authentication or rate-limiting on the REST API/MCP server (ADR
  0015 §4, explicit MVP scope decision) — do not expose either to an
  untrusted network as shipped. The concurrency lock (`Engine.run()`)
  is a resource-exhaustion floor, not access control.
- `mathematics.curve_fit` has no per-point weighting (`sigma`) or
  `tolerance` override — documented as an explicit MVP scope decision
  in its `skill.md`, not an oversight.
- No shared `PhysicalValidator` (see "physical stays documentation-only"
  above) — no skill has needed one yet; revisit when one does.
- `NumericalDiagnosticsValidator`'s `condition_number` check is still
  forward-looking — no shipped skill reports `condition_number` yet
  (left in place for a future linear-algebra skill, not removed).
