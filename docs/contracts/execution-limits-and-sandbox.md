# Execution limits and sandbox honesty (Phase A2)

## Input limits (enforced)

Applied to every run **before** schema/domain validators
(`oec.execution.limits`):

| Limit | Default | Effect on breach |
|---|---|---|
| `max_input_json_bytes` | 1 048 576 (1 MiB) | `INVALID`, layer `limits` |
| `max_sequence_length` | 100 000 | `INVALID`, layer `limits` |
| `max_depth` | 64 | `INVALID`, layer `limits` |

Same behavior on SDK, CLI, REST, and MCP (limits run inside
`ExecutionService`).

Override only by constructing `ExecutionService(..., input_limits=InputLimits(...))`
— not exposed as a public unstable API for agents in Alpha.

## Timeout

- Declared per skill: `execution.timeout_seconds` in `skill.yaml`.
- Enforced by killing the skill subprocess (ADR 0012).
- **Enforced:** yes (`provenance.sandbox.timeout_enforced: true`).

## What the sandbox does **not** enforce (Alpha)

| Policy flag on skill | Actually isolated? |
|---|---|
| `network_access: false` | **No** OS-level network jail |
| `filesystem_access: false` | **No** OS-level filesystem jail |
| memory cap | **No** (`memory_limit_enforced: false`) |

Provenance reports these flags **honestly** so agents and operators do not
over-trust Alpha isolation. Real multi-tenant hardening is post–Phase A
(technical debt P1).

## Expression safety

User-supplied math expressions (root finding, integrate function mode,
optimization objectives, curve-fit models) use a **restricted AST**
interpreter — never `eval`/`exec`. Attribute access, dunder chains, and
unknown calls are rejected (`ExpressionError` / skill `INVALID` or
`FAILED` path as wired).

See `tests/unit/test_expressions.py` for rejection of known escape patterns.

## REST note

Oversized or limit-breaking inputs still produce an `ExecutionResult` with
`status: INVALID` and HTTP **200** (ADR 0015: scientific outcomes travel in
the body). Clients must read `body.status`, not only the HTTP code.
