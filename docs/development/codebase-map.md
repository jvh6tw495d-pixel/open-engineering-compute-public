# Codebase map

Living summary of OEC's structure. Updated at the end of each sprint (see
`docs/development/graphify.md` for the tool used to help maintain it).

## Main components (as of Sprint 00)

| Component | Path | Status |
|---|---|---|
| Shared value objects | `src/oec/common.py` | implemented — `VersionedRef` |
| Base error hierarchy | `src/oec/errors.py` | implemented — `OECError` and 5 subclasses |
| Skill manifest model | `src/oec/skills/schemas/manifest.py` | implemented — `SkillManifest` + nested specs |
| Execution models | `src/oec/execution/models.py` | implemented — `ExecutionRequest`, `ExecutionResult`, `ExecutionStatus` |
| Skill Loader | `src/oec/skills/loader/` | empty package, scaffolded for Sprint 01 |
| Skill Registry | `src/oec/skills/registry/` | empty package, scaffolded for Sprint 01 |
| Skill Lifecycle | `src/oec/skills/lifecycle/` | empty package, scaffolded for Sprint 01 |
| Engineering Kernel | `src/oec/kernel/{numerics,optimization,statistics,uncertainty,units}` | empty packages, scaffolded for Sprints 02+ |
| Validation Engine | `src/oec/validation/` | empty package, scaffolded for Sprint 03 |
| Execution Service | `src/oec/execution/` | only models so far; service lands in Sprint 03 |
| Python SDK / CLI | `src/oec/cli/` | empty package, scaffolded for Sprint 06 |
| REST API | `src/oec/api/` | empty package, scaffolded for Sprint 07 |
| MCP adapter | `src/oec/mcp/` | empty package, scaffolded for Sprint 07 |
| Reports | `src/oec/reports/` | empty package, not yet scheduled in detail |

## Dependencies (declared, not all wired yet)

- Core: `pydantic>=2.7`, `numpy`, `scipy`, `sympy`, `pint` (units engine
  arrives in Sprint 02; not imported anywhere yet).
- Optional extras: `api` (fastapi, uvicorn), `cli` (typer, rich), `mcp`
  (mcp SDK) — declared in `pyproject.toml` but unused until their
  respective sprints.
- Dev/quality: ruff, mypy, pytest, pytest-cov, hypothesis, pre-commit,
  bandit.

## Entrypoints

- `oec` console script → `oec.cli.main:app` — **declared, not yet
  implemented**. Running `oec` today will fail; this is expected until
  Sprint 06.
- No HTTP or MCP entrypoint exists yet.

## Execution flow (current state)

Nothing executes yet — this sprint only established the data contracts
(`SkillManifest`, `ExecutionRequest`, `ExecutionResult`) that every later
component will pass around. There is no loader, no registry, and no
execution pipeline wiring them together yet; that is the entire scope of
Sprint 01 and Sprint 03.

## Modules touched this sprint

All of `src/oec/` (new), all of `tests/unit/` (new), all ADRs 0001–0005
(new), all `.github/` workflow and template files (new).

## Areas of highest coupling

- `oec.common.VersionedRef` is imported by both
  `oec.skills.schemas.manifest` (as `SkillManifest.method`) and
  `oec.execution.models` (as `ExecutionResult.skill` / `.method`). This is
  intentional reuse (used 3 times) rather than premature abstraction, and
  Graphify's own report independently flagged it as the highest-degree
  node in the graph (19 edges) — worth keeping an eye on as the loader and
  registry start depending on it too.

## Known structural debt

- `oec.errors` currently only defines the root hierarchy; skill-loading,
  validation-layer, and execution-pipeline errors that Sprint 01–03 need
  (e.g. a dedicated timeout error, a dimensional-mismatch error) are not
  yet modeled as distinct subclasses — deferred until the code that raises
  them exists, to avoid speculative error types.
- `ValidationPolicy.schema_layer` uses a Pydantic alias (`schema`) because
  `schema` collides with a deprecated `BaseModel` method name under mypy
  strict mode. Documented inline in `manifest.py`; revisit if a cleaner
  Pydantic v2 idiom emerges.
- No `docs/skills/`, `docs/api/`, `docs/mcp/`, `docs/integrations/`,
  `docs/contributing/`, `docs/concepts/` content yet — directories exist,
  content is scheduled per-sprint as the corresponding component lands.
