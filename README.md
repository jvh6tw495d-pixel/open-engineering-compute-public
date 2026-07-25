# Open Engineering Compute (OEC) — Private Incubation

> **Status:** private incubation repository. Not for public distribution yet.

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

## Status

This repository is in **private incubation**. It has no remote configured and
is not published. A dedicated sanitization sprint precedes any public
release — see `docs/sprints/`.

## Repository layout

See `docs/development/codebase-map.md` for a summary of the main components,
entrypoints and current structural debt.

## Development

This project uses [`uv`](https://docs.astral.sh/uv/) for environment and
dependency management.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

## License

Apache-2.0 (provisional — see `LICENSE`). The final public license will be
reviewed before any public release.
