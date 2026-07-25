# Codebase map

Living summary of OEC's structure. Updated at the end of each sprint (see
`docs/development/graphify.md` for the tool used to help maintain it).

## Main components (as of Sprint 04)

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
| Engineering Kernel (rest) | `src/oec/kernel/{optimization,statistics,uncertainty}` | empty, scaffolded |
| Validation Engine | `src/oec/validation/{base,schema,dimensions,mathematical,physical,numerical,invariants,golden}.py` | implemented |
| Execution Service | `src/oec/execution/{service,runner,sandbox,status,provenance}.py` | implemented |
| **Testing SDK** | `src/oec/testing.py` | **implemented** — see below |
| **MVP skills (3 of 12)** | `skills/mathematics/{solve_root,interpolate,integrate}/` | **implemented** — see below |
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
  lists all 3 real MVP skills, not just the loader test fixture.
- No HTTP or MCP entrypoint yet (Sprint 07).

## Execution flow (current state)

Unchanged pipeline shape from Sprint 03 (`resolve → input validators →
sandbox → result validators → compute_status → provenance`), now proven
against real skills, not just a trivial fixture:
`tests/integration/test_solve_root_end_to_end.py`,
`test_interpolate_end_to_end.py`, `test_integrate_end_to_end.py` each
wire the real `SchemaValidator` + the skill's own `validation.py`
validator into a real `ExecutionService` and execute through the actual
sandboxed subprocess.

`QuantityValue`/`normalize()`/`x-oec-unit` remain unused by any real
skill — all three MVP math skills are dimensionless by design (see each
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
  deliberately: three skills aren't enough to know what the right
  auto-wiring convention should look like. Sprint 05/06 candidate.

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
