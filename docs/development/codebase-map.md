# Codebase map

Living summary of OEC's structure. Updated at the end of each sprint (see
`docs/development/graphify.md` for the tool used to help maintain it).

## Main components (as of Sprint 03)

| Component | Path | Status |
|---|---|---|
| Shared value objects | `src/oec/common.py` | implemented — `VersionedRef` |
| Base error hierarchy | `src/oec/errors.py` | implemented — `OECError` + 10 subclasses |
| Skill manifest model | `src/oec/skills/schemas/manifest.py` | implemented — `SkillManifest` + nested specs |
| Execution models | `src/oec/execution/models.py` | implemented — `ExecutionRequest`, `ExecutionResult`, `ExecutionStatus` |
| Skill front matter parser | `src/oec/skills/loader/frontmatter.py` | implemented |
| Skill Loader | `src/oec/skills/loader/{loader.py,models.py}` | implemented — never imports skill Python code |
| Skill Registry | `src/oec/skills/registry/registry.py` | implemented |
| Skill Lifecycle | `src/oec/skills/lifecycle/lifecycle.py` | implemented |
| CLI | `src/oec/cli/main.py` | implemented — `oec version`, `oec skills {list,inspect,validate}` |
| Units kernel | `src/oec/kernel/units/{registry,quantity,serialization,normalize}.py` | implemented |
| Engineering Kernel (rest) | `src/oec/kernel/{numerics,optimization,statistics,uncertainty}` | empty, scaffolded for Sprint 04+ |
| **Validation Engine** | `src/oec/validation/{base,schema,dimensions,mathematical,physical,numerical,invariants,golden}.py` | **implemented** — see below |
| **Execution Service** | `src/oec/execution/{service,runner,sandbox,status,provenance}.py` | **implemented** — see below |
| REST API | `src/oec/api/` | empty package, scaffolded for Sprint 07 |
| MCP adapter | `src/oec/mcp/` | empty package, scaffolded for Sprint 07 |
| Reports | `src/oec/reports/` | empty package, not yet scheduled in detail |

### Validation Engine, module by module

- `base.py` — the frozen contract: `Severity`, `ValidationOutcome`,
  `InputValidator`/`ResultValidator` protocols. Both take a full
  `LoadedSkill`, not just its manifest, so the schema layer can read
  parsed `input_schema`/`output_schema`.
- `schema.py` — `SchemaValidator` (`InputValidator`): JSON Schema
  (`jsonschema.Draft202012Validator`) against `normalized_inputs`.
- `dimensions.py` — `DimensionalValidator` (`InputValidator`): validates
  `{value, unit}`-shaped inputs as `QuantityValue`; checks compatibility
  against an optional `x-oec-unit` JSON Schema extension via
  `oec.kernel.units.normalize.is_compatible`.
- `mathematical.py` / `physical.py` — **not** pipeline-wired validators;
  reusable pure functions (`require_nonzero`, `require_bracket`,
  `require_positive`, `require_above_absolute_zero`, etc.) that a real
  skill's own `validation.py` (plan section 8, arriving Sprint 04+) will
  call. What JSON Schema already expresses (`minimum`/`maximum`/etc.)
  belongs in `schema.py`, not here — deliberately not duplicated.
- `numerical.py` — `NumericalDiagnosticsValidator` (`ResultValidator`):
  non-fatal `WARNING`s from `diagnostics` (near iteration limit, poor
  conditioning, residual above tolerance). Never re-decides convergence
  — that's `compute_status`'s job via a separate `converged` argument.
- `invariants.py` — `InvariantValidator` (`ResultValidator`): no
  NaN/Infinity anywhere in `result`; `result` conforms to
  `output_schema` if declared.
- `golden.py` — `GoldenCase` + `assert_matches_golden` /
  `diff_against_golden`: development-time regression testing (plan
  section 12.6), never part of the runtime pipeline.

### Execution Service, module by module

- `runner.py` — runs *inside* the sandboxed subprocess (ADR 0012). The
  only file in the codebase that ever imports a skill's Python code.
  Invoked as `python -m oec.execution.runner`, stdin/stdout JSON
  protocol: `{"result": ..., "diagnostics": ...}` or it's a contract
  violation (`RunnerContractError`).
- `sandbox.py` — parent-side `run_in_sandbox()`: launches the runner via
  `subprocess.run(..., timeout=...)`. Real, cross-platform timeout
  enforcement; network/filesystem isolation explicitly not enforced
  (ADR 0012) and reported as such, never implied.
- `status.py` — `compute_status()`: the only implementation of ADR
  0007's precedence table (`implementation_failed` → any `ERROR` → not
  converged → any `WARNING` → exact-or-converged-clean).
- `provenance.py` — `build_provenance()`: `oec_version`, cached
  `git_commit`, `trace_id`, `requested_by`, `seed`, a `SandboxReport`
  (what was *actually* enforced, not what the manifest declared), and
  per-field original/normalized units.
- `service.py` — `ExecutionService`: resolve → input validators →
  sandbox execution (skipped entirely if any input validator reports an
  `ERROR`) → result validators → `compute_status` → `build_provenance` →
  `ExecutionResult`. Validators are constructor-injected
  (`list[InputValidator]`/`list[ResultValidator]`) — this module has no
  import-time dependency on any concrete validator layer.

## Dependencies (declared, not all wired yet)

- Core: `pydantic>=2.7`, `numpy`, `scipy`, `sympy`, `pint`, `pyyaml`,
  `typer`/`rich`, `jsonschema>=4.20` (new this sprint — JSON Schema
  validation for `schema.py`/`invariants.py`).
- Optional extras: `api` (fastapi, uvicorn), `mcp` (mcp SDK) — unused
  until Sprint 07.
- Dev/quality: ruff, mypy, pytest, pytest-cov, hypothesis, pre-commit,
  bandit, `types-PyYAML`, `types-jsonschema`.

## Entrypoints

- `oec` console script → `oec.cli.main:app` — implemented (`version`,
  `skills list/inspect/validate`). No `oec run` yet — that's Sprint 06
  (Python SDK/CLI) scope; `ExecutionService` is exercised via the SDK
  surface (direct Python import) and tests only for now.
- No HTTP or MCP entrypoint exists yet (Sprint 07).

## Execution flow (current state)

The full pipeline now runs end to end, in a real subprocess:

```text
ExecutionService.execute(ExecutionRequest)
        ↓ registry.get_skill(id[, version])           -- LoadedSkill
        ↓ input_validators: list[InputValidator]        (e.g. SchemaValidator)
                ↓ any ERROR? -> skip execution entirely, status=INVALID
        ↓ run_in_sandbox(...)                            -- ADR 0012, real timeout
                ↓ oec.execution.runner in a subprocess    -- only place that imports skill code
        ↓ result_validators: list[ResultValidator]       (e.g. InvariantValidator)
        ↓ compute_status(outcomes, implementation_failed, converged)   -- ADR 0007
        ↓ build_provenance(...)                          -- honest sandbox report
        ↓ ExecutionResult
```

Proven, not just designed: `tests/integration/test_full_validation_wiring.py`
wires the real `SchemaValidator`/`InvariantValidator`/
`NumericalDiagnosticsValidator` (built independently by Grok in an
isolated worktree) into `ExecutionService` (built independently in this
tree) with zero adjustment on either side — both halves only ever
depended on `oec.validation.base`'s frozen protocols.

`QuantityValue`/`normalize()` are still not wired into any real skill's
input schema (no MVP skill exists yet — Sprint 04). `dimensions.py`'s
`x-oec-unit` convention is ready for when one does.

## Modules touched this sprint

`src/oec/execution/{service,runner,sandbox,status,provenance}.py`,
`src/oec/validation/{base,schema,dimensions,mathematical,physical,
numerical,invariants,golden}.py`, `docs/architecture/adr/{0007,0012}-*.md`,
`tests/unit/test_{runner,sandbox,execution_service,golden,
validation_base,validation_schema,validation_dimensions,
validation_mathematical,validation_physical,validation_numerical,
validation_invariants}.py`, `tests/integration/`,
`tests/fixtures/skills/mathematics/identity/implementation.py` (updated
to the runner's return-value contract), `tests/_skill_helpers.py`
(`implementation_code` override).

## Areas of highest coupling

- `oec.validation.base` is now imported by every validator layer *and*
  `oec.execution.service` — the busiest module in the codebase by
  design (it's the frozen contract everything else is built against,
  per ADR-adjacent Sprint 03 planning).
- `oec.execution.runner` is intentionally the *only* importer of
  skill-authored code — this is a deliberate security boundary (ADR
  0012), not incidental coupling.
- `oec.kernel.units.registry.ureg` remains the single shared Pint
  instance (ADR 0011); `physical.py`'s `require_above_absolute_zero`
  now also depends on it directly.

## Known structural debt

- No MVP skill (math or electrical) exists yet, so `QuantityValue`,
  `dimensions.py`'s `x-oec-unit`, and `mathematical.py`/`physical.py`'s
  helper functions are all tested in isolation but never exercised by a
  real skill's actual `validation.py`. That's Sprint 04.
- Network/filesystem isolation is declared in `ExecutionPolicy` but not
  enforced (ADR 0012, deliberate, documented, reported honestly in
  every `ExecutionResult.provenance.sandbox`). Real OS-level isolation
  is a future hardening-sprint concern.
- `runner.py`'s `main()`/`__main__` block shows as uncovered in the
  parent process's coverage report — it genuinely runs (via
  `test_sandbox.py`'s subprocess-level tests) but in a *child* process
  coverage.py doesn't instrument from the parent run. Would need
  `COVERAGE_PROCESS_START` subprocess coverage hooks to fix; not worth
  the setup cost given the module's logic is otherwise fully covered via
  direct unit tests of `_run`/`_load_entrypoint`.
- `SkillLifecycle.validate_transition` still not called anywhere at
  runtime (same debt noted since Sprint 01) — no re-registration flow
  exists yet.
- No `docs/skills/`, `docs/api/`, `docs/mcp/`, `docs/integrations/`,
  `docs/contributing/`, `docs/concepts/` content yet.
