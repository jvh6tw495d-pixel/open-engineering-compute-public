# Skill versioning policy (Phase A)

## Identifiers

- Skill id: `domain.name` (e.g. `mathematics.solve_root`, `electrical.voltage_drop`).
- Version: semver string on `skill.yaml` / front matter (e.g. `0.1.0`).
- Method: separate `{id, version}` under `method:` in the manifest.

## When to bump

| Change | Bump |
|---|---|
| Bugfix, docs-only, clearer errors, no schema change | **patch** |
| New optional input, new optional output field, new method alternative with explicit opt-in | **minor** |
| Required input added/removed/renamed; output shape break; semantic change of default method | **major** |
| Lifecycle only (`experimental` → `validated`) | usually **minor** or patch; document in skill Changelog |

## Schemas

- `input.schema.json` / `output.schema.json` are part of the skill contract.
- Breaking JSON Schema changes require a **major** skill version.
- Two directories with the same id+version must not both register (`skill_version_conflict`).

## Backends

- Changing SciPy/NumPy minor versions in the environment is **not** automatically a skill major.
- Changing **which** SciPy routine is the default for a declared method **is** a skill contract change (major if silent behavior change).
- Provenance records backend package versions per run (`backends[]`) for audit; it does not replace skill semver.

## Public claims

- Do not claim a skill is `stable` without golden coverage and human review.
- Open Science proposals must not auto-mutate `stable` packages.
