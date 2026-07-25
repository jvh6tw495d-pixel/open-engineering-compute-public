# ADR 0001: Skill-first architecture

- **Status:** accepted
- **Date:** 2026-07-24

## Context

OEC could be organized around any of its interfaces — a REST API, an MCP
server, a CLI, or a Python SDK — treating the engineering logic as a detail
behind whichever surface came first. That produces a system where the
"real" behavior lives wherever the first integration needed it, and later
interfaces drift from each other as they grow their own shortcuts.

## Decision

The **skill** — a self-contained specification of an engineering problem,
its official methodology, and a deterministic implementation — is the
product. The Skill Engine and Engineering Kernel are the core. The Python
SDK, CLI, REST API, and MCP server are thin, interchangeable adapters over
that core; none of them may hold engineering logic of its own.

```text
Skill Specification
        ↓
Skill Engine
        ↓
Engineering Kernel
        ↓
Interfaces
```

## Consequences

- Any new interface (a future GUI, a different protocol) can be added
  without touching skill logic.
- A change in methodology only ever happens in one place: the skill.
- Interfaces cannot ship a "quick fix" that silently diverges from what the
  other interfaces do for the same skill (see also
  [0005](0005-thin-interface-adapters.md)).
- Building a new skill is the primary unit of contribution and review, not
  building a new endpoint.
