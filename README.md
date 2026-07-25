# Open Engineering Compute (OEC)

> **Status:** private incubation → Public Alpha **prep** complete.
> Not published from this history (see [Public Alpha procedure](docs/release/public-alpha.md)).

Open Engineering Compute is an open framework for executable, versioned and
auditable engineering skills. It lets different language models, agents,
applications and interfaces run the same engineering methodology and obtain
numerically consistent, reproducible and auditable results.

> Language models can vary.
> Engineering methodology must not change silently.

The core of the system is the **Skill Engine**, which turns an engineering
specification into an executable procedure. Every skill declares its problem
definition, official methodology, mathematical formulation, units, schemas,
assumptions, applicability limits, deterministic implementation, validations,
tests, references, version and provenance.

## Quick start

```bash
uv sync
uv run oec skills list --skills-root skills
uv run oec run mathematics.solve_root --input '{"expression":"x**2 - 2","bracket":[0,2]}' --skills-root skills
```

Optional extras:

```bash
uv sync --extra api   # REST:  oec server api --skills-root skills
uv sync --extra mcp   # MCP:   oec server mcp --skills-root skills
```

## Interfaces

| Surface | Entry |
|---|---|
| Python SDK | `oec.sdk.Engine` / `oec.sdk.run` |
| CLI | `oec skills …`, `oec run`, `oec server …` |
| REST | `/v1/skills`, `/v1/skills/{id}/run` — [docs/api](docs/api/README.md) |
| MCP | stdio tools per skill — [docs/mcp](docs/mcp/README.md) |

## Optional integrations

| Integration | Path | Notes |
|---|---|---|
| Odysseus (MCP host) | `integrations/odysseus/` | config + tutorial; core has zero Odysseus deps |
| Open Science | `integrations/open_science/` | Method Change Proposals; **never** auto-mutates `stable` skills |

## MVP skills

- **Mathematics (6):** `solve_root`, `interpolate`, `integrate`, `optimize_scalar`, `optimize_constrained`, `curve_fit`
- **Electrical (6):** `three_phase_power`, `current_from_power`, `voltage_drop`, `power_factor_correction`, `transformer_loading`, `per_unit_conversion`

## Status / release

This clone is the **incubation** repository (no remote). Public Alpha must use a
**new directory and clean git history** — see:

- [docs/release/public-alpha.md](docs/release/public-alpha.md)
- `uv run python scripts/prepare_public_alpha.py --dry-run`
- `uv run python scripts/check_forbidden_names.py`

Layout map: [docs/development/codebase-map.md](docs/development/codebase-map.md).

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy
uv run bandit -c pyproject.toml -r src/oec
```

## License

Apache-2.0 (provisional — see `LICENSE`). Community docs: `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`.
