# Public Alpha procedure (Fase 9 / Sprint 11)

This repository is **private incubation**. Do **not** publish it by
adding a remote and pushing. Public Alpha requires a **new directory
and a new Git history** (ADR 0008).

## Goals

- Installable `oec` package (Apache-2.0 provisional)
- Documented SDK / CLI / REST / MCP
- Optional integrations (Odysseus, Open Science) that do not couple the core
- Zero private nomenclature (handbook §2.1)
- Clean git history

## Forbidden public content

Do not ship, even in history:

- Private product / system names — the authoritative list lives in
  `scripts/check_forbidden_names.py` and the external master handbook
  (§2), not enumerated here (ADR 0008): a document that spells the
  names out is itself a leak surface, and the list may be extended
  without needing this doc revised.
- Client names, commercial rules, proprietary formulations
- Operational data, private repo names, funding strategy
- Master incubation handbooks that enumerate internal systems
  (`OEC_MASTER_HANDBOOK.md`, plano mestre) — keep out of the public tree

## Procedure

1. On the incubation repo:
   ```bash
   git remote -v          # must be empty
   uv run pytest
   uv run ruff check .
   uv run mypy
   uv run bandit -c pyproject.toml -r src/oec
   uv build
   uv run python scripts/check_forbidden_names.py --all-files
   uv run python scripts/prepare_public_alpha.py --dry-run
   ```
2. Create the public tree (sibling directory recommended):
   ```bash
   uv run python scripts/prepare_public_alpha.py \
     --dest ../open-engineering-compute-public \
     --init-git
   ```
3. In the public tree:
   ```bash
   uv sync --all-extras
   uv run pytest
   uv run oec skills list --skills-root skills
   # optional MCP demo
   uv sync --extra mcp
   uv run oec server mcp --skills-root skills
   ```
4. Human review of docs, license, and dependency licenses.
5. Only then: add the public remote and push the **new** history.

## Definition of Done (Alpha)

- [ ] Fresh git history
- [ ] No private remotes in incubation
- [ ] Forbidden-name gate green
- [ ] Tests green; package installable
- [ ] SECURITY / CONTRIBUTING / CHANGELOG / CODE_OF_CONDUCT present
- [ ] MCP path demonstrated (stdio)
- [ ] Open Science stable-guard tested
- [ ] Graphify regenerated if published as a dev aid (artifacts not required in git — ADR 0010)
