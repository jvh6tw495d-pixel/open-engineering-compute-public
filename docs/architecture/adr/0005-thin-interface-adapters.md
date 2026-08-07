# ADR 0005: Interfaces are thin adapters over one internal service layer

- **Status:** accepted
- **Date:** 2026-07-24

## Context

OEC ships four interfaces to the same engine: a Python SDK, a CLI, a REST
API, and an MCP server (section 13 of the master plan). If each interface
independently re-implements request validation, skill resolution, or
result formatting, they will drift — the same skill call could behave
differently through the CLI than through MCP, which directly contradicts
the project's central thesis (see [0001](0001-skill-first-architecture.md)).

## Decision

The SDK, CLI, REST API, and MCP server call the same internal services
(`Skill Registry`, `Skill Execution Service`, `Validation Engine`) and
exchange the same core models (`SkillManifest`, `ExecutionRequest`,
`ExecutionResult`). An interface may translate transport concerns (HTTP
status codes, CLI exit codes, MCP tool schemas) but must not:

- select a numerical method,
- apply validation rules,
- reshape scientific content (values, units, methodology, diagnostics),
- or hold state that the other interfaces don't have access to.

## Consequences

- A conformance expectation is testable directly: the same
  `ExecutionRequest` submitted through any interface must yield the same
  scientific content in `ExecutionResult` (allowing only transport-level
  formatting differences).
- New interfaces are additive and cannot introduce new engine behavior.
- REST and MCP are explicitly deferred past Sprint 00; when they land
  (Sprint 07), this ADR is the acceptance bar for both.
