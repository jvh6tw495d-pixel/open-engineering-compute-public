# Sprint 11 — Sanitização e Public Alpha (Fase 9)

- **Datas:** 2026-07-25
- **Executor:** Grok Build
- **Status:** preparação concluída no repositório de incubação; **publicação não executada** (ADR 0008)

## Objetivo

Deixar o Alpha publicável: docs de comunidade, gate de nomenclatura,
procedimento de histórico Git limpo, imagem Docker, checklist.

## Entregas

- `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`
- `Dockerfile`
- `docs/release/public-alpha.md`
- `scripts/check_forbidden_names.py`
- `scripts/prepare_public_alpha.py` (dry-run por padrão; copy + `git init` opcional)
- README atualizado com ponteiros Alpha

## Explicitamente NÃO feito

- Não adicionar remote
- Não fazer push
- Não copiar automaticamente para `open-engineering-compute-public/` sem flag do operador
- Não reescrever o histórico de incubação

## Critérios de aceite (prep)

| Critério | Status |
|---|---|
| Histórico público limpo (procedimento) | documentado + script |
| Zero referências internas (gate) | script pronto |
| Testes / pacote | existentes; revalidar no tree público |
| Docs reproduzíveis | sim |
| MCP demonstrável | docs + integrations/odysseus |

## Como publicar (humano)

```bash
uv run python scripts/prepare_public_alpha.py --dry-run
uv run python scripts/prepare_public_alpha.py \
  --dest ../open-engineering-compute-public \
  --init-git
# então, no dest: uv sync && uv run pytest && review && remote
```
