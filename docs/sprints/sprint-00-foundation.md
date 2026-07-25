# Sprint 00 — Foundation e repositório local

- **Datas:** 2026-07-24 (execução em sessão única)
- **Executor:** Claude Code
- **Status:** concluída

## Objetivo

Estabelecer o repositório local, a governança de qualidade e a memória
estrutural (Graphify) do Open Engineering Compute, sem implementar
skills completas, FastAPI, MCP, Odysseus, Open Science ou frontend.

## Entregas

- Repositório Git local novo em
  `C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC`, sem remote,
  sem histórico herdado, branch `main`.
- Estrutura mínima do monorepo (`src/oec`, `tests`, `docs`, `examples`,
  `integrations`, `skills`, `benchmarks`, `scripts`, `.github`) conforme
  seção 6 do plano mestre.
- `pyproject.toml` + `uv.lock`: Python 3.12.13 (instalado via `uv`,
  isolado do Python 3.11 de sistema), dependências científicas
  (pydantic, numpy, scipy, sympy, pint) e extras opcionais (api, cli, mcp)
  declaradas mas não usadas ainda.
- Qualidade: Ruff (lint + format), mypy `strict`, pytest + pytest-cov,
  Hypothesis (dependência instalada, sem uso ainda), Bandit, pre-commit
  (hooks instalados em `.git/hooks/pre-commit`).
- CI local (sem remote, portanto não executado por nenhum runner ainda):
  `.github/workflows/{ci,security,release}.yml`, templates de issue e PR.
- Modelos centrais Pydantic v2:
  - `oec.common.VersionedRef` — par id/version reutilizado por método e
    skill.
  - `oec.errors.OECError` e subclasses (`SkillError`,
    `SkillNotFoundError`, `SkillManifestError`, `OECValidationError`,
    `ExecutionError`) — estruturados, sem exposição de segredos.
  - `oec.skills.schemas.manifest.SkillManifest` (+ `EntrypointSpec`,
    `SchemaRefs`, `ExecutionPolicy`, `ValidationPolicy`, `SkillStatus`).
  - `oec.execution.models.ExecutionRequest`,
    `oec.execution.models.ExecutionResult`,
    `oec.execution.models.ExecutionStatus` (enum graduado de 7 estados,
    sem campo booleano `success`).
- 5 ADRs iniciais em `docs/architecture/adr/` (0001–0005).
- Documentação e primeira indexação do Graphify
  (`docs/development/graphify.md`, `docs/development/codebase-map.md`).
- 26 testes unitários em `tests/unit/`, 100% de cobertura em `src/oec`.

## Arquivos alterados

37 arquivos novos, 0 modificados/removidos (repositório iniciado do zero
nesta sprint). Ver `git log --stat` para o detalhamento por commit.

## Commits

```text
bdcf610 chore: initialize local OEC repository
a0512ad feat(core): add shared value objects and base error hierarchy
5590a04 feat(skills): add SkillManifest model
340a150 feat(execution): add ExecutionRequest and ExecutionResult models
d92657f test: add unit tests for core models and error hierarchy
12103f3 docs(adr): add initial architecture decision records
262ed14 chore(ci): add CI, security and release workflows
d6a1c35 docs(development): document Graphify setup and initial codebase map
```

Todos os commits são locais; nenhum remote foi configurado, nenhum push
foi feito.

## Testes

```text
uv run pytest -q
26 passed in 0.80s
```

## Cobertura

100% em `src/oec` (132 statements, 4 branches — todos cobertos). Módulos
com apenas `__init__.py` vazio contam como 100% trivialmente; serão
recalculados conforme ganham conteúdo nas próximas sprints.

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 37 files already formatted |
| `uv run mypy` (strict) | Success: no issues found in 22 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified |
| `uv run pytest -q` | 26 passed, 100% coverage |
| `uv build` | sdist + wheel built successfully (`oec-0.1.0`) |
| `graphify update .` | 143 nodes, 166 edges, 31 communities |

## Graphify

Ferramenta pré-existente detectada via `uv tool list` (`graphifyy` v0.8.39,
expõe `graphify`/`graphify-mcp`), acessada por `uv tool run --from
graphifyy graphify ...` já que não está diretamente no `PATH`. Backend
local Ollama com `llama3.1:8b` confirmado disponível, mas não foi
necessário para a extração estrutural desta sprint (`graphify update`
não usa LLM). Grafo gerado em `graphify-out/` (~275 KB), mantido fora do
controle de versão por decisão documentada em
`docs/development/graphify.md` (regenerável, sem dados sensíveis, sem
caminhos absolutos, mas gerado a cada mudança estrutural).

## Decisões

- Python 3.12 gerenciado via `uv python install`, sem alterar o Python
  3.11 do sistema — evita conflito com outras ferramentas do usuário que
  dependem do 3.11 já instalado.
- `ValidationPolicy` usa alias Pydantic (`schema` → `schema_layer`)
  porque `schema` colide com um método legado de `BaseModel` sob mypy
  strict; documentado em `manifest.py` e em `codebase-map.md`.
- `VersionedRef` foi extraído como modelo compartilhado (usado por
  `SkillManifest.method`, `ExecutionResult.skill` e
  `ExecutionResult.method`) — reuso real em 3 pontos, não abstração
  especulativa; o próprio Graphify identificou-o independentemente como
  nó de maior grau do grafo (19 arestas), o que corrobora a decisão.
- `graphify-out/` gitignorado por ora (ver seção Graphify acima).
- Identidade Git configurada localmente (`git config --local`, não
  `--global`) após confirmação explícita do usuário, para não alterar
  configuração global da máquina.

## Riscos

- **CI nunca executado de fato:** os workflows em `.github/workflows/`
  foram escritos e revisados manualmente, mas sem remote configurado
  (por design da fase de incubação) nenhum deles rodou em um runner real
  ainda. Risco de erro de sintaxe/ambiente só detectável na Sprint 11
  (sanitização) ou antes, se um remote temporário for usado para validar.
- **Cobertura 100% é enganosa neste estágio:** quase todo o código ainda
  são modelos de dados puros (Pydantic faz a validação pesada); a
  cobertura vai cair naturalmente quando lógica de loader/execução for
  adicionada, o que é esperado e não deve ser lido como regressão.
- **`oec` console script declarado mas não implementado:** `pyproject.toml`
  referencia `oec.cli.main:app`, que não existe ainda — rodar `oec` hoje
  falha. Aceitável para Sprint 00, mas deve ser lembrado ao rodar
  qualquer smoke test de instalação antes da Sprint 06.

## Dívida técnica

- Nenhuma hierarquia de erro específica de domínio (timeout de skill,
  incompatibilidade dimensional, etc.) além da raiz genérica — adiado
  propositalmente até que o código que os levanta exista (Sprint 01–03).
- `docs/skills/`, `docs/api/`, `docs/mcp/`, `docs/integrations/`,
  `docs/contributing/`, `docs/concepts/` existem como diretórios vazios,
  sem conteúdo.

## Itens adiados

Tudo fora do escopo explícito da Sprint 00 (seção 33): SkillLoader,
SkillRegistry, lifecycle, engine de unidades, pipeline de execução,
Validation Engine, skills matemáticas/elétricas, SDK, CLI, REST, MCP,
Odysseus, Open Science.

## Próxima sprint

**Sprint 01 — Contrato e registry de skills** (semanas 3–4): schema de
`skill.yaml` (já coberto por `SkillManifest`), parser de front matter do
`skill.md`, `SkillLoader`, `SkillRegistry`, resolução de versão,
lifecycle, erros estruturados de carregamento, CLI mínima de listagem e
inspeção, primeira skill experimental de exemplo.
