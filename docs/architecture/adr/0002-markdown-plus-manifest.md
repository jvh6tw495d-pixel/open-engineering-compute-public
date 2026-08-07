# ADR 0002: Skills are described by Markdown plus a machine-readable manifest

- **Status:** accepted
- **Date:** 2026-07-24

## Context

A skill needs to be understood by two very different readers: a human
engineer reviewing the methodology, and a program (the Skill Loader) that
needs to resolve an entrypoint, schemas, and an execution policy without
parsing prose. Encoding everything as YAML/JSON makes the methodology
unreadable to reviewers; encoding everything as prose makes it unusable by
the loader.

## Decision

Each skill ships two co-located, mandatory files:

- `skill.md` — the human- and agent-legible specification: problem
  definition, official methodology, mathematical formulation, assumptions,
  applicability limits, worked examples, references, and changelog.
- `skill.yaml` — the operational manifest consumed by the Skill Loader:
  `id`, `version`, `status`, `entrypoint`, `schemas`, `method`,
  `execution` policy, and `validation` policy. This is parsed into the
  `SkillManifest` Pydantic model (`oec.skills.schemas.manifest`).

Neither file is optional, and neither substitutes for the other:
`skill.yaml` never contains the methodology narrative, and `skill.md` never
carries the entrypoint or execution policy.

## Consequences

- The Skill Loader only needs to parse `skill.yaml`; `skill.md` is never
  parsed for control flow, so a documentation edit cannot change runtime
  behavior.
- Reviewers can approve a methodology change (`skill.md`) and an
  operational change (`skill.yaml`) as clearly separated diffs.
- `SkillManifest` is `frozen` and validates `id` and `version` shape at
  construction time, so a malformed manifest fails to load instead of
  loading with silently wrong metadata.
