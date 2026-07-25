# Codebase map

Living summary of OEC's structure. Updated at the end of each sprint (see
`docs/development/graphify.md` for the tool used to help maintain it).

## Main components (as of Sprint 02)

| Component | Path | Status |
|---|---|---|
| Shared value objects | `src/oec/common.py` | implemented — `VersionedRef` |
| Base error hierarchy | `src/oec/errors.py` | implemented — `OECError` + 9 subclasses |
| Skill manifest model | `src/oec/skills/schemas/manifest.py` | implemented — `SkillManifest` + nested specs, nested `schemas`/`execution`/`validation` shape matches plan section 8.2 |
| Execution models | `src/oec/execution/models.py` | implemented — `ExecutionRequest`, `ExecutionResult`, `ExecutionStatus` |
| Skill front matter parser | `src/oec/skills/loader/frontmatter.py` | implemented — `SkillFrontMatter`, `parse_front_matter` |
| Skill Loader | `src/oec/skills/loader/{loader.py,models.py}` | implemented — `load_skill`, `LoadedSkill`; never imports skill Python code |
| Skill Registry | `src/oec/skills/registry/registry.py` | implemented — `SkillRegistry`, `discover_skill_dirs`, `RegistrationReport` |
| Skill Lifecycle | `src/oec/skills/lifecycle/lifecycle.py` | implemented — `is_loadable_by_default`, `validate_transition` |
| CLI | `src/oec/cli/main.py` | implemented — `oec version`, `oec skills {list,inspect,validate}` |
| Units kernel | `src/oec/kernel/units/{registry,quantity,serialization,normalize}.py` | implemented — `QuantityValue`, `normalize`, `is_compatible`, single shared Pint `ureg` |
| Engineering Kernel (rest) | `src/oec/kernel/{numerics,optimization,statistics,uncertainty}` | empty packages, scaffolded for Sprint 04+ |
| Validation Engine | `src/oec/validation/` | empty package, scaffolded for Sprint 03 |
| Execution Service | `src/oec/execution/` | only models so far; service lands in Sprint 03 |
| REST API | `src/oec/api/` | empty package, scaffolded for Sprint 07 |
| MCP adapter | `src/oec/mcp/` | empty package, scaffolded for Sprint 07 |
| Reports | `src/oec/reports/` | empty package, not yet scheduled in detail |

## Dependencies (declared, not all wired yet)

- Core: `pydantic>=2.7`, `numpy`, `scipy`, `sympy`, `pint` (units engine —
  **now implemented and imported**, `src/oec/kernel/units/`), `pyyaml`
  (parses `skill.yaml` and `skill.md` front matter), `typer`/`rich` (CLI
  — core dependency, not an optional extra, since the CLI ships from
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

Physical quantities can now be normalized independently of any skill:

```text
QuantityValue(value, unit)                     -- public shape, Pint-validated at construction
        ↓ normalize(quantity, to_unit=...)
                ↓ to_pint(quantity) -- via the single shared `ureg`
                ↓ .to(to_unit)      -- raises UnitError on dimensional mismatch
        ↓ NormalizedQuantity(original=..., normalized=...)
```

`QuantityValue` and `normalize()` are not wired into `SkillManifest`,
`ExecutionRequest`, or the loader yet — `inputs`/`result` on those models
are still plain `dict[str, Any]`. Wiring typed quantities into a skill's
actual input/output schema is Sprint 03/04 work, once the Validation
Engine and the first real skills exist to consume them.

## Modules touched this sprint

`src/oec/kernel/units/{registry,quantity,serialization,normalize}.py`
(new), `src/oec/errors.py` (+`UnitError`), `pyproject.toml`
(`fail_under` raised to 90), `tests/unit/{test_quantity,
test_serialization,test_normalize}.py`,
`tests/property/test_units_properties.py`,
`docs/architecture/adr/{0010,0011}-*.md`.

## Areas of highest coupling

- `write_skill_dir()` (test helper) and `load_skill()` remain the
  graph's highest-degree nodes — expected, unrelated to this sprint's
  units work, which is deliberately self-contained (`kernel/units/` has
  no dependents yet outside its own tests).
- `oec.skills.schemas.manifest.SkillManifest` is imported by loader,
  registry, lifecycle, and CLI — the busiest production node, as
  expected for a skill-first architecture (ADR 0001).
- `oec.kernel.units.registry.ureg` is a deliberate single point of
  coupling by design (ADR 0011) — every quantity conversion in the
  kernel must go through it; that is the point, not a smell.

## Known structural debt

- `QuantityValue` is not yet referenced by `SkillManifest`,
  `ExecutionRequest`/`ExecutionResult`, or any JSON Schema — a skill's
  `inputs`/`result` are still untyped `dict[str, Any]`. Sprint 03
  (Validation Engine) is where dimensional validation actually gets
  applied to a skill's declared inputs; Sprint 02 only builds the
  primitive it will use.
- No curated allow-list of engineering units — Pint's full default unit
  set is available, including units no skill will ever need (see ADR
  0011). Deferred until real skills reveal what is actually used.
- `oec.errors` still has no dedicated timeout error — deferred until
  Sprint 03 code (Execution Service) actually raises it.
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
