# Sprint 10 — Integrações nativas (Fases 7–8)

- **Datas:** 2026-07-25
- **Executor:** Grok Build
- **Status:** concluída (artefatos no working tree; commit pendente de review)

## Objetivo

Integrar Odysseus e Open Science **sem acoplar o core**.

## Entregas

### Odysseus (Fase 7)

- `integrations/odysseus/` — README, local/remote MCP examples, docker-compose example, examples.md, tutorial.md
- Smoke + e2e path tests: config validity and MCP `list_skills` + skill run over `Engine`

### Open Science (Fase 8)

- `integrations/open_science/proposal.schema.json`
- `export.py` / `import_proposal.py` / `workflow.py`
- examples + tests
- Hard rule enforced: never auto-mutate `stable` skills; Alpha import never writes skill packages

## Critérios de aceite

| Critério | Status |
|---|---|
| Integrações opcionais | ok — core deps unchanged |
| Core instala sem deps externas das integrações | ok |
| Open Science não altera stable automaticamente | ok — tested |
| Odysseus path executa skills via MCP adapter | ok — tested |

## Próxima

Sprint 11 / Fase 9 — sanitização e Public Alpha prep.
