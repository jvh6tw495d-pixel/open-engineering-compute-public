# Sprint 07 — REST API e MCP

- **Datas:** 2026-07-25 (execução em sessão única, continuação da Sprint 06 — stretch goal explicitamente autorizado pelo usuário)
- **Executor principal:** Claude Code
- **Executor paralelo:** Grok Build (worktree isolada, Fase B, Track 2)
- **Status:** concluída

## Objetivo

Completar as duas interfaces que faltavam desde a Sprint 00 (seção 13
do plano): REST API e servidor MCP, ambas como adaptadores finos sobre
`oec.sdk.Engine` (ADR 0005) — sem lógica científica própria, sem
revalidar, sem reformatar resultado.

## Validação da Sprint 06 (Opus, pré-sprint)

Um agente Opus revisou a Sprint 06 antes de começar. Nenhum bug
bloqueante; 2 achados corrigidos imediatamente:

- **Finding 1**: `oec run --input-file <arquivo inexistente>` vazava
  um traceback bruto em vez do erro limpo de exit 1 que o próprio
  comando promete — `read_text()` rodava fora de qualquer
  try/except de `OECError`. Corrigido.
- **Finding 2**: o smoke test de instalação (Sprint 06) nunca rodava
  em CI (`addopts` tem `-m "not slow"` fixo, e não havia nenhum job
  que passasse `-m slow`). Adicionado um job de CI separado, noturno/
  manual, para não deixar uma regressão de empacotamento passar
  despercebida até um usuário real rodar `pip install`.

Outros achados (fix da `NumericalDiagnosticsValidator` não exercitado
por nenhuma skill real em teste de integração, framing da ADR 0014
sobre cache do CLI) foram documentados como dívida técnica aceitável,
não corrigidos nesta sprint.

## Entregas

### Fase A — ADR 0015, `Engine.warm()`, trava de execução única

- **ADR 0015** congela três decisões relacionadas: (1) mapeamento
  status HTTP ↔ `ExecutionStatus` — `200` com o `ExecutionResult`
  completo mesmo para `INVALID`/`FAILED`/`INCONCLUSIVE` (são
  resultados científicos estruturados, não falhas de transporte;
  diverge deliberadamente do modelo de exit code do `oec run`, ADR
  0014, porque HTTP sempre tem um corpo para inspecionar e um shell
  não); (2) convenção de exposição MCP — uma tool por skill, usando o
  `input.schema.json` real da skill como `inputSchema`, mais
  `list_skills`; (3) postura de concorrência.
- **`oec.sdk.Engine.run()` agora serializa toda execução por um único
  lock** — no máximo uma skill roda por vez por instância de `Engine`.
  Consequência direta de uma referência futura já presente na ADR 0012
  ("execução síncrona no Alpha... revisar se a API REST da Sprint 07
  precisar rodar muitas execuções concorrentes") e, sem isolamento de
  recursos no nível de SO por subprocesso, o único limite seguro de
  concorrência disponível antes da sprint de hardening futura. Corrige
  de brinde uma corrida real que uma revisão da Sprint 06 encontrou no
  cache `_services`.
- **`Engine.warm()`**: constrói os validadores de toda skill registrada
  no startup em vez de sob demanda — uma falha de descoberta de
  validador (`SkillEntrypointError`, ADR 0014) aparece no boot do
  servidor, não no meio de uma requisição.
- **`Engine.registry` exposto publicamente** (renomeado de `_registry`)
  — a API REST precisa listar/inspecionar skills, não só executá-las.

### Fase B — REST API (Track 1) e MCP (Track 2, paralelo)

Diferente da Sprint 06, este trabalho separa limpo em duas trilhas sem
sobreposição de arquivo real (`src/oec/api/` vs `src/oec/mcp/`), então
valia a pena tentar paralelizar de novo. Uma sondagem barata do Grok
(~2 min, `grok -p "print ok" --permission-mode auto`) **funcionou** —
diferente das Sprints 05 e 06, onde o classificador de permissões do
ambiente bloqueou o lançamento autônomo em todas as tentativas. Sem
explicação definitiva do porquê mudou; documentado como lição para
sprints futuras (sondar de novo a cada vez, não assumir do resultado
da sprint anterior).

- **Track 1 (Claude Code) — `src/oec/api/app.py`**: FastAPI com um
  `Engine` compartilhado, aquecido em um `lifespan` handler. `GET
  /health`, `GET /skills`, `GET /skills/{skill_id}`, `POST
  /skills/{skill_id}/run`. Verificado manualmente ponta a ponta
  (servidor real, requisições HTTP reais via curl) antes de escrever
  os testes automatizados. `oec server api` no CLI.
- **Track 2 (Grok, worktree isolada `sprint07-mcp`) —
  `src/oec/mcp/server.py`**: uma tool MCP por skill registrada, usando
  o `input.schema.json` real da skill como `inputSchema` (API
  *low-level* do MCP, não o wrapper `FastMCP` — este deriva schema de
  anotações de tipo Python e não aceita um dict JSON Schema arbitrário
  pronto). Trabalho de qualidade alta: cobertura de teste completa,
  incluindo um teste de conformidade próprio comparando `Engine.run()`
  com `call_tool()`. A sessão do Grok terminou sem commitar (seguiu à
  risca a instrução de não tocar `.pre-commit-config.yaml`, que
  precisava da entrada `mcp>=1.0` para o hook de mypy passar) — commitado
  pelo Claude Code durante a revisão, com gate completo rodado de forma
  independente na worktree antes do merge (543 testes, 96.78%
  cobertura, bateu com o esperado). Merge `--no-ff`, um único conflito
  trivial em `.pre-commit-config.yaml` (ambas as trilhas adicionaram
  dependências na mesma lista), resolvido mantendo as duas.

### Fase C — fechamento

- `oec server mcp` cabeado no CLI (mesmo padrão de import preguiçoso
  com erro limpo do `oec server api` — `mcp` é extra opcional).
- **Teste de conformidade da ADR 0005**
  (`tests/integration/test_adr0005_conformance.py`): a mesma
  `ExecutionRequest` via SDK, CLI, REST e MCP, comparadas de verdade
  pela primeira vez (antes cada interface só testava a si mesma). Dois
  casos: convergido (`VALIDATED`) e `INVALID` — confirmando que
  diferenças de nível de transporte (exit code do CLI, status HTTP,
  `isError` do MCP) continuam permitidas enquanto o conteúdo científico
  não diverge.
- Gate completo, `codebase-map.md` atualizado, Graphify, este relatório.

## Arquivos alterados

~20 arquivos novos/modificados (7 commits, incluindo o merge).

## Commits

```
056358a fix: patch two findings from the Sprint 06 independent review
0548dde feat(sdk): freeze ADR 0015, add Engine.warm() and single-execution lock
f7e9dbc refactor(sdk): expose Engine.registry publicly
7a844f3 feat(api): add REST API and oec server api CLI command
cd9537c feat(mcp): add MCP server exposing skills as tools
bd30ff1 Merge branch 'sprint07-mcp' into main
c1369b8 feat(cli): wire oec server mcp; add ADR 0005 four-interface conformance test
```

## Testes

```text
uv run pytest -q
558 passed, 3 deselected in ~73s
```

## Cobertura

96.05% em `src/oec`.

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | All formatted |
| `uv run mypy` (strict) | Success: no issues found in 56 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified |
| `uv run pytest -q` | 558 passed, 3 deselected, 96.05% coverage |
| `uv build` | sdist + wheel built successfully |
| Verificação manual da API REST (servidor real + curl) | confirmado antes dos testes automatizados |
| Gate independente na worktree do Grok (antes do merge) | 543 testes, 96.78% cobertura — bateu com o relatado |

## Graphify

1958 → 2093 nós.

## Decisões

- **ADR 0015** — a decisão central da sprint: mapeamento de status
  HTTP, convenção de exposição MCP, e o modelo de concorrência de
  execução única.
- **`oec.sdk.Engine.run()` serializado por um único lock** — não é
  uma escolha de performance, é a leitura honesta da ADR 0012 (zero
  isolamento de SO por subprocesso) combinada com a própria intenção
  documentada do plano ("execução síncrona no Alpha"). Revisitar só
  junto com sandboxing real, não com uma estratégia de lock mais
  sofisticada isoladamente.
- **Status HTTP são só de transporte** (ADR 0015 §1) — diverge do
  modelo de exit code do CLI de propósito, não por inconsistência.
- **MCP expõe uma tool por skill**, não uma tool genérica — mais
  tools para manter conforme o catálogo cresce, mas cada skill fica
  auto-descritiva (schema próprio), alinhado com a tese central do
  projeto.
- **Sondar o Grok de novo a cada sprint, não assumir do resultado
  anterior** — bloqueado nas Sprints 05 e 06, funcionou de primeira
  nesta. Sem explicação definitiva; documentado como lição.

## Riscos

- Sem autenticação nem rate-limiting em nenhuma das duas interfaces
  novas (decisão explícita da ADR 0015 §4) — não expor a rede não
  confiável como está. A trava de concorrência é um piso contra
  esgotamento de recursos, não controle de acesso.
- O bloqueio do Grok continua sem causa raiz identificada — pode
  voltar a acontecer na próxima sprint sem aviso.

## Dívida técnica

- Sem autenticação/rate-limiting (ver Riscos).
- `NumericalDiagnosticsValidator`'s correção da Sprint 06 ainda não
  tem teste de integração ponta a ponta contra uma skill real
  disparando `CONVERGED_WITH_WARNINGS` de verdade (achado da revisão
  pré-sprint, não corrigido).
- `runner.py`'s `main()` sem cobertura instrumentada entre processos.
- `SkillLifecycle.validate_transition` sem uso em runtime.
- Telemetria de desenvolvimento (seção 19 do plano) ainda não
  implementada.

## Itens adiados

Skills elétricas (Sprint 08+), sandboxing real de SO (sprint de
hardening futura, candidata Sprint 09), autenticação/rate-limiting.

## Próxima sprint

Esta sprint era o limite explícito autorizado pelo usuário ("siga até
o 6, se tiver limite vai até o 7"). Sem instrução para continuar além
da Sprint 07 nesta sessão — próximos passos ficam para quando o
usuário retomar.
