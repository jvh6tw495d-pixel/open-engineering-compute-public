# REST API

A thin adapter over `oec.sdk.Engine` (ADR 0005) — see
[`docs/architecture/adr/0015-rest-mcp-contract.md`](../architecture/adr/0015-rest-mcp-contract.md)
for the design rationale (HTTP status mapping, concurrency).

## Running it

```bash
uv sync --extra api
uv run oec server api --skills-root skills --host 127.0.0.1 --port 8000
```

Requires the `api` extra (`fastapi`/`uvicorn`) — not part of the base install.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check. |
| `GET` | `/skills` | List registered skills. Query params: `domain`, `tag` (repeatable), `include_retired`. |
| `GET` | `/skills/{skill_id}` | A single skill's manifest. Optional `?version=`. `404` if unknown. |
| `POST` | `/skills/{skill_id}/run` | Execute a skill. Body: `{"inputs": {...}, "version"?, "seed"?, "trace_id"?, "requested_by"?}`. |

## Status codes

`POST /skills/{skill_id}/run` returns `200` with the full
`ExecutionResult` body whenever the pipeline produced one — **including**
`INVALID`/`FAILED`/`INCONCLUSIVE`. Those are structured scientific
outcomes read from `body.status`, not transport failures. `404` means
the skill id doesn't resolve; `422` means the request body itself
didn't parse (e.g. an unknown field). See ADR 0015 §1 for the full
rationale.

## Concurrency

At most one skill executes at a time, server-wide (`oec.sdk.Engine`'s
internal lock — ADR 0015 §3). This is deliberate for the Alpha: skill
subprocesses have no OS-level resource isolation yet (ADR 0012), so
unbounded concurrency is a resource-exhaustion risk this project has no
sandboxing story for yet.

## Not yet implemented

No authentication, no rate-limiting (ADR 0015 §4) — do not expose this
server to an untrusted network as shipped.
