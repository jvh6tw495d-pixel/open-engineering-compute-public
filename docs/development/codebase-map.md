# Codebase map

Living summary of OEC's structure. Updated at the end of each sprint (see
`docs/development/graphify.md` for the tool used to help maintain it).

## Main components (as of Sprint 05)

| Component | Path | Status |
|---|---|---|
| Shared value objects | `src/oec/common.py` | implemented — `VersionedRef` |
| Base error hierarchy | `src/oec/errors.py` | implemented — `OECError` + 12 subclasses |
| Skill manifest model | `src/oec/skills/schemas/manifest.py` | implemented — `SkillManifest`, `MethodRef` (`iterative: bool`, ADR 0013) |
| Execution models | `src/oec/execution/models.py` | implemented |
| Skill Loader/Registry/Lifecycle | `src/oec/skills/{loader,registry,lifecycle}/` | implemented |
| CLI | `src/oec/cli/main.py` | implemented — `oec version`, `oec skills {list,inspect,validate}` |
| Units kernel | `src/oec/kernel/units/` | implemented, not yet wired into a real skill's schema |
| **Numerics kernel** | `src/oec/kernel/numerics/{expressions,root_finding}.py` | **implemented** — see below |
| **Optimization kernel** | `src/oec/kernel/optimization/{diagnostics,scalar,constrained,curve_fit}.py` | **implemented** — see below |
| Engineering Kernel (rest) | `src/oec/kernel/{statistics,uncertainty}` | empty, scaffolded |
| Validation Engine | `src/oec/validation/{base,schema,dimensions,mathematical,physical,numerical,invariants,golden}.py` | implemented |
| Execution Service | `src/oec/execution/{service,runner,sandbox,status,provenance}.py` | implemented |
| Testing SDK | `src/oec/testing.py` | implemented |
| **MVP skills (6 of 12 planned math skills)** | `skills/mathematics/{solve_root,interpolate,integrate,optimize_scalar,optimize_constrained,curve_fit}/` | **implemented** — see below |
| REST API | `src/oec/api/` | empty, scaffolded for Sprint 07 |
| MCP adapter | `src/oec/mcp/` | empty, scaffolded for Sprint 07 |

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
  `skills list/inspect/validate`). No `oec run` yet (Sprint 06).
  `ExecutionService` is exercised via direct Python import in tests and
  `tests/integration/`, e.g. `oec skills list --skills-root skills` now
  lists all 6 real MVP skills, not just the loader test fixture.
- No HTTP or MCP entrypoint yet (Sprint 07).

## Execution flow (current state)

Unchanged pipeline shape from Sprint 03 (`resolve → input validators →
sandbox → result validators → compute_status → provenance`), now proven
against six real skills:
`tests/integration/test_solve_root_end_to_end.py`,
`test_interpolate_end_to_end.py`, `test_integrate_end_to_end.py`,
`test_optimize_scalar_end_to_end.py`,
`test_optimize_constrained_end_to_end.py`,
`test_curve_fit_end_to_end.py` each wire the real `SchemaValidator` +
the skill's own `validation.py` validator into a real
`ExecutionService` and execute through the actual sandboxed subprocess.

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
- **No per-skill validator auto-discovery yet** — `ExecutionService`
  does not read `skill.yaml`'s `validation:` block to automatically
  assemble a skill's validator list; whoever constructs the service
  must explicitly include a skill's own `validation.py` validator (see
  every `tests/integration/test_*_end_to_end.py`). Deferred
  deliberately: three skills weren't enough to know what the right
  auto-wiring convention should look like; still deferred at six —
  Sprint 06 candidate now that there's more precedent.
- **Grok's autonomous CLI launch was blocked this sprint** (Sprint 05):
  `grok -p ... --always-approve` and `--permission-mode auto` were both
  denied by this environment's own permission classifier, unrelated to
  Grok itself — it had worked in Sprint 04. `math.optimize_constrained`
  and `math.curve_fit` (planned as a Claude Code / Grok parallel split,
  per the same pattern that worked for `interpolate`/`integrate`) were
  both built by Claude Code solo instead, sequentially, directly on
  `main` (no worktree needed without a second parallel agent). Not a
  structural repo issue — flagged here so a future sprint's
  orchestration plan doesn't assume Grok delegation is unconditionally
  available in every environment.

## Known structural debt

- Validator auto-discovery from `skill.yaml` (see Decisions above).
- `runner.py`'s `main()`/`__main__` still not instrumented by coverage
  across the subprocess boundary (known since Sprint 03).
- `SkillLifecycle.validate_transition` still not called anywhere at
  runtime (known since Sprint 01).
- Development telemetry (plan section 19: cost per accepted task) still
  not implemented — flagged by the independent Sprint 00-02 review,
  still open.
- No `docs/skills/`, `docs/api/`, `docs/mcp/`, `docs/integrations/`,
  `docs/contributing/`, `docs/concepts/` content yet.
- `mathematics.curve_fit` has no per-point weighting (`sigma`) or
  `tolerance` override — documented as an explicit MVP scope decision
  in its `skill.md`, not an oversight.
