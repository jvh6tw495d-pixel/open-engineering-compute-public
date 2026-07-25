# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x (private incubation / public Alpha) | yes |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Email the maintainers with:

- a description of the issue;
- steps to reproduce;
- impact assessment if known;
- whether a fix is already proposed.

We aim to acknowledge reports within 7 days.

## Alpha network posture

The REST API and MCP server ship **without authentication or rate
limiting** (see ADR 0015). Treat them as local/dev tools:

- prefer stdio MCP on the same host;
- do not expose `oec server api` / MCP to untrusted networks as shipped;
- skill execution uses a subprocess sandbox with no network access by
  default (ADR 0012) — this is not a multi-tenant hardened jail.

## Expression evaluation

User-supplied mathematical expressions are parsed with a restricted AST
(never `eval` / `exec`). See the numerics kernel and plan section 4.7.
