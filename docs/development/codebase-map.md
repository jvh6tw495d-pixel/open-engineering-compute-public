# Codebase map

Living summary of OEC's structure. Updated at the end of each sprint (see
`docs/development/graphify.md` for the tool used to help maintain it).

## Main components (as of Sprint 01)

| Component | Path | Status |
|---|---|---|
| Shared value objects | `src/oec/common.py` | implemented — `VersionedRef` |
| Base error hierarchy | `src/oec/errors.py` | implemented — `OECError` + 8 subclasses |
| Skill manifest model | `src/oec/skills/schemas/manifest.py` | implemented — `SkillManifest` + nested specs, nested `schemas`/`execution`/`validation` shape matches plan section 8.2 |
| Execution models | `src/oec/execution/models.py` | implemented — `ExecutionRequest`, `ExecutionResult`, `ExecutionStatus` |
| Skill front matter parser | `src/oec/skills/loader/frontmatter.py` | implemented — `SkillFrontMatter`, `parse_front_matter` |
| Skill Loader | `src/oec/skills/loader/{loader.py,models.py}` | implemented — `load_skill`, `LoadedSkill`; never imports skill Python code |
| Skill Registry | `src/oec/skills/registry/registry.py` | implemented — `SkillRegistry`, `discover_skill_dirs`, `RegistrationReport` |
| Skill Lifecycle | `src/oec/skills/lifecycle/lifecycle.py` | implemented — `is_loadable_by_default`, `validate_transition` |
| CLI | `src/oec/cli/main.py` | implemented — `oec version`, `oec skills {list,inspect,validate}` |
| Engineering Kernel | `src/oec/kernel/{numerics,optimization,statistics,uncertainty,units}` | empty packages, scaffolded for Sprint 02+ |
| Validation Engine | `src/oec/validation/` | empty package, scaffolded for Sprint 03 |
| Execution Service | `src/oec/execution/` | only models so far; service lands in Sprint 03 |
| REST API | `src/oec/api/` | empty package, scaffolded for Sprint 07 |
| MCP adapter | `src/oec/mcp/` | empty package, scaffolded for Sprint 07 |
| Reports | `src/oec/reports/` | empty package, not yet scheduled in detail |

## Dependencies (declared, not all wired yet)

- Core: `pydantic>=2.7`, `numpy`, `scipy`, `sympy`, `pint` (units engine
  arrives in Sprint 02; not imported anywhere yet), `pyyaml` (parses
  `skill.yaml` and `skill.md` front matter), `typer`/`rich` (CLI — now
  core dependencies, not an optional extra, since the CLI ships from
  Sprint 01 onward).
- Optional extras: `api` (fastapi, uvicorn), `mcp` (mcp SDK) — declared in
  `pyproject.toml` but unused until Sprint 07.
- Dev/quality: ruff, mypy, pytest, pytest-cov, hypothesis, pre-commit,
  bandit, `types-PyYAML`.

## Entrypoints

- `oec` console script → `oec.cli.main:app` — **implemented**. Try:
  `uv run oec skills list --skills-root tests/fixtures/skills`.
- No HTTP or MCP entrypoint exists yet (Sprint 07).

## Execution flow (current state)

A skill directory can now be discovered, loaded, validated, and inspected
end to end:

```text
SkillRegistry.register_all(root)
        ↓ discover_skill_dirs (rglob for skill.yaml)
        ↓ load_skill(path) per directory
                ↓ parse skill.yaml -> SkillManifest (pydantic)
                ↓ parse skill.md front matter -> SkillFrontMatter
                ↓ cross-check the two agree (id/version/status/domain/title)
                ↓ check entrypoint .py file exists (never imported)
                ↓ check + parse input/output JSON Schema files
        ↓ LoadedSkill stored in registry, indexed by id -> version
registry.get_skill(id[, version]) / .list_skills() / .search() / .validate()
        ↑ consumed by `oec skills list/inspect/validate`
```

No skill is ever *executed* yet — that is still the Skill Execution
Service's job, arriving in Sprint 03. The loader deliberately stops at
"the manifest, front matter, and declared artifacts are internally
consistent," not "the implementation actually runs."

## Modules touched this sprint

`src/oec/skills/{loader,registry,lifecycle}/*`, `src/oec/cli/main.py`,
`src/oec/errors.py` (4 new subclasses), `src/oec/skills/schemas/manifest.py`
(reshaped to the plan's nested `schemas`/`execution`/`validation` YAML
shape), `tests/unit/{test_loader,test_registry,test_lifecycle,
test_frontmatter,test_cli}.py`, `tests/property/*`,
`tests/fixtures/skills/mathematics/identity/*` (the Sprint 01 example
skill), `tests/_skill_helpers.py` + `tests/conftest.py` (shared test
fixture-writer, importable from every test subpackage).

## Areas of highest coupling

- `write_skill_dir()` (test helper) and `load_skill()` are now the graph's
  highest-degree nodes (39 and 28 edges per Graphify) — expected, since
  nearly every Sprint 01 test exercises the loader through that one
  helper. Not a production coupling concern; worth remembering if the
  helper ever needs to change shape, since it will touch ~50 tests.
- `oec.skills.schemas.manifest.SkillManifest` is now imported by loader,
  registry, lifecycle, and CLI — the busiest production node, as
  expected for a skill-first architecture (ADR 0001).

## Known structural debt

- `oec.errors` still has no dedicated timeout or dimensional-mismatch
  error — deferred until Sprint 02/03 code actually raises them.
- The loader checks only that the entrypoint `.py` file exists and that
  the schema files are syntactically valid JSON; it does not validate
  the JSON Schemas against the JSON Schema meta-schema, and it does not
  import or introspect the entrypoint function. Both are intentional
  (plan section 4.7: don't execute untrusted code without need) and both
  become real work in Sprint 03 (Validation Engine, Execution Service).
- `SkillLifecycle.validate_transition` is implemented and tested but not
  yet called from anywhere at runtime — there is no code path today that
  changes a skill's status, so it is exercised only directly by
  `tests/unit/test_lifecycle.py`. It will be wired in once a
  re-registration/update flow exists.
- The experimental example skill (`tests/fixtures/skills/mathematics/identity`)
  intentionally lives under `tests/fixtures/`, not the top-level `skills/`
  catalog — it is a loader/registry test fixture, not one of the MVP
  skills from plan section 14. `skills/mathematics/` and
  `skills/electrical/` remain empty until Sprint 04 and Sprint 08.
- No `docs/skills/`, `docs/api/`, `docs/mcp/`, `docs/integrations/`,
  `docs/contributing/`, `docs/concepts/` content yet — directories exist,
  content is scheduled per-sprint as the corresponding component lands.
