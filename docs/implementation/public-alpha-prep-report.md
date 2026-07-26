# Public Alpha prep report

**Date:** 2026-07-26
**Incubation HEAD:** `7b9197d` (plus prior GPT/Opus stream)
**Public tree:** `Documentos/open-engineering-compute-public-2026-07-26`
**Public HEAD:** `8f7accb` — *chore: initial public alpha import (clean history)*

## Gates (incubation)

| Check | Result |
|---|---|
| `git remote -v` | empty |
| `check_forbidden_names --all-files` | ok (0 hits) |
| ruff / mypy | green |
| pytest | 800 passed, ~91% cov |
| bandit | exit 0 |
| `uv build` | wheel + sdist |

## Public tree validation

| Check | Result |
|---|---|
| Forbidden names in copy | ok (649 files) |
| Fresh history | 1 commit on `main`, **no remotes** |
| `uv sync --all-extras --all-groups` | ok |
| `uv run pytest --no-cov` | **800 passed** |
| `oec skills list --skills-root skills` | full catalog listed |

## Excluded from public copy (by design)

- `docs/sprints`, `docs/release`, `docs/development/codebase-map.md`
- `graphify-out`, `.venv`, `dist`, incubation handbooks
- incubation git history

## Included

- `src/`, `skills/`, `tests/`, `agents/`, `benchmarks/`
- ADRs, contracts, integrations (Odysseus, Open Science)
- packaging + CI workflows

## Not done (human / publish)

1. Review license headers and third-party notices
2. Decide public remote URL
3. `git remote add` + push **only after** human OK
4. Optional: graphify in public tree

**Do not push the incubation repo.** Publish only the sibling public tree.
