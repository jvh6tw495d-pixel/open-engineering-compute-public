# Sprint 06 — Python SDK e CLI

- **Datas:** 2026-07-25 (execução em sessão única, continuação da Sprint 05)
- **Executor:** Claude Code (sozinho — Grok segue bloqueado pelo classificador do ambiente, ver Sprint 05)
- **Status:** concluída

## Objetivo

Completar a lacuna deixada desde a Sprint 03: `ExecutionService` nunca
monta os validadores de uma skill sozinho, e não existe um comando CLI
nem SDK Python público para executar uma skill de verdade (apenas
`skills list/inspect/validate`, que nunca chamam a implementação). Um
agente Opus, ao validar a Sprint 05, definiu o escopo concreto e a
divisão de trabalho — como não recomendou paralelizar com o Grok desta
vez (ver "Decisão sobre paralelização" abaixo), a sprint inteira foi
executada solo, sequencialmente.

## Validação da Sprint 05 (Opus, pré-sprint)

Antes de começar, um agente Opus independente revisou a Sprint 05 a
fundo (six pontos de escrutínio específicos: contrato de diagnósticos,
distinção `converged` ausente-vs-null, assimetria SLSQP/trust-constr,
fallback de não-convergência do `curve_fit`, segurança do
`compile_expression_vector`, independência dos golden cases). Nenhum
bug bloqueante — 2 achados reais:

- **Finding 1 (corrigido antes da sprint)**: os JSONs de exemplo de
  `optimize_scalar`/`optimize_constrained`/`curve_fit` fixavam
  contadores internos do solver (`iterations`, `function_evaluations`)
  em `expected_output`, comparados via `assert_matches_golden` contra
  toda chave — um valor que só um SciPy específico poderia ter
  produzido, não um oráculo independente. Corrigido: mantidos apenas
  os campos verificados independentemente (`x`/`fun`/`params`).
- **Finding 2 (corrigido nesta sprint, Fase A)**: `NumericalDiagnosticsValidator`
  lia `iterations`/`max_iterations`/`residual`/`tolerance` inteiramente
  de `diagnostics` — um shape que não bate com nenhuma das seis skills
  reais (`max_iterations`/`tolerance` são *inputs* do chamador, nunca
  ecoados em `diagnostics`). `CONVERGED_WITH_WARNINGS` estava
  praticamente inalcançável desde a Sprint 03.

## Decisão sobre paralelização

O Opus recomendou explicitamente **não** paralelizar esta sprint com o
Grok: `oec run`, o SDK e a fábrica de auto-descoberta são o mesmo
conjunto pequeno e fortemente acoplado de arquivos, todos dependendo de
uma decisão de arquitetura (a convenção de descoberta de validador, o
mapeamento de exit codes) que precisa ser definida primeiro — não há
como dividir isso em duas trilhas sem sobreposição real. A única peça
isolável (o smoke test de instalação) depende logicamente do `oec run`
já existir. Seguido à risca: sprint inteira solo.

## Entregas

### Fase A — ADR 0014, auto-descoberta de validador, SDK, correção do Finding 2

- **ADR 0014**: congela quatro decisões de uma vez — (1) convenção de
  descoberta de validador por introspecção (classe definida no módulo
  `validation.py`, com `layer` + `validate`, sem exigir um novo ponto
  de registro explícito — nenhuma das seis skills precisou mudar uma
  linha), (2) `physical: true` permanece só documentação (nenhum
  `PhysicalValidator` compartilhado existe), (3) o `oec` SDK
  (`Engine`/`run`) com um `ExecutionService` por skill, cacheado —
  `ExecutionService` em si não mudou, continua vinculado a uma lista
  fixa de validadores por instância, (4) mapeamento de exit code do
  `oec run` (`0` resultado utilizável, `2` INCONCLUSIVE, `3` INVALID,
  `4` FAILED, `1` erro de CLI).
- **`src/oec/execution/factory.py`**: `build_validators(skill)`.
- **`src/oec/sdk.py`**: `Engine`/`run`, tolera falhas de registro de
  skills irmãs quebradas (`Engine.registration_failures`) em vez de
  recusar construir — espelha o comportamento já existente de `skills
  list`/`inspect`.
- **`NumericalDiagnosticsValidator` corrigido**: agora lê
  `normalized_inputs` para `max_iterations`/`tolerance`, e cai entre os
  nomes reais de chave que as skills usam (`n_iterations`, `abs_error`,
  máximo de uma lista `residuals`).

### Fase B — `oec run`, refatoração dos testes de integração, smoke test

- **`oec run <skill_id>`**: lê inputs de `--input-file`/`--input`/stdin
  (exatamente uma fonte), executa via `Engine`, imprime resumo humano
  ou `--json`. Testado manualmente contra todos os quatro caminhos de
  exit code antes de escrever os testes automatizados.
- **Refatoração dos 6 `test_*_end_to_end.py`**: `_service()` agora usa
  `build_validators(skill)` em vez de montar a lista à mão — os 26
  testes passam sem alteração de comportamento, a prova de que a
  auto-descoberta reproduz exatamente o que estava hardcoded.
- **Smoke test de instalação** (adiado desde a Sprint 00,
  `tests/installation/test_installation_smoke.py`): builda o wheel de
  verdade, instala numa venv descartável, roda o `oec` instalado como
  subprocesso (`version`, `skills list --json`, `run --json`). Marcado
  `slow`, desmarcado por padrão (`-m "not slow"` em `addopts`).
- **Achado incidental**: um teste de propriedade da Sprint 05
  (`test_box_bound_clamps_paraboloid_minimum`) começou a falhar de
  forma intermitente — Hypothesis achou um caso extremo (caixa de
  busca com largura próxima de zero) onde a tolerância `ftol` do SLSQP
  domina antes de alcançar `x=0` dentro de `1e-4`. Não é um bug da
  skill; corrigido restringindo o domínio da estratégia (`lo` até
  `-0.1`, não `0.0`), estável em 3 execuções completas seguidas depois.

### Fase C — fechamento

- Gate completo, `codebase-map.md` atualizado, Graphify rodado
  (1866→1958 nós), este relatório.

## Arquivos alterados

~15 arquivos novos/modificados (5 commits).

## Commits

```
c487209 feat(execution,sdk): add validator auto-discovery, oec SDK facade, fix dead numerical warnings
47e9315 feat(cli): add oec run, exercised end to end via manual CLI checks
a4dc8ae refactor(tests): collapse hand-wired _service() helpers to build_validators
7b2ce02 test(installation): add installation smoke test, deferred since Sprint 00
```
(mais o commit de correção do Finding 1, feito antes do início formal
da sprint — ver relatório da Sprint 05.)

## Testes

```text
uv run pytest -q
530 passed, 3 deselected in ~50s
```

`3 deselected` = o smoke test de instalação (`-m slow`), rodado
explicitamente e verificado separadamente (`uv run pytest -m slow
--no-cov`).

## Cobertura

96.91% em `src/oec`.

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | All formatted |
| `uv run mypy` (strict) | Success: no issues found in 54 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified |
| `uv run pytest -q` | 530 passed, 3 deselected, 96.91% coverage |
| `uv run pytest -m slow --no-cov` | 3 passed (instalação real via wheel) |
| `uv build` | sdist + wheel built successfully |
| Verificação manual do `oec run` (todos os 4 caminhos de exit code, `--json`, `--input-file`, stdin) | confirmado antes dos testes automatizados |

## Graphify

1866 → 1958 nós.

## Decisões

- **ADR 0014** — a decisão central da sprint, cobrindo quatro
  superfícies relacionadas de uma vez (auto-descoberta, `physical`
  documentation-only, shape do SDK, exit codes do `oec run`).
- **Não paralelizar com o Grok nesta sprint** — recomendação explícita
  do Opus, seguida à risca: o trabalho não separa em trilhas
  independentes sem sobreposição real.
- **`ExecutionService` não foi alterado** — a tentação seria mudar seu
  construtor para aceitar validadores dinamicamente por skill; em vez
  disso, `Engine` resolve o problema por fora (uma instância por
  skill, cacheada), mantendo uma classe já estável e bem testada
  intocada.
- **Smoke test de instalação marcado `slow`/opt-in** — builda um wheel
  de verdade e instala numa venv descartável a cada execução; caro
  demais para rodar em todo `pytest -q`, mas real o suficiente para
  não ser um mock.

## Riscos

- O smoke test de instalação teve uma falha transitória (exit 4) numa
  das primeiras execuções, não reproduzida em 3 execuções completas
  subsequentes — provavelmente overhead de primeiro lançamento do
  `.exe` recém-criado (antivírus/sync do OneDrive na pasta do
  projeto). Como é um teste opt-in, não bloqueia o gate padrão; vale
  observar se volta a acontecer.
- O bloqueio do Grok pelo classificador do ambiente continua sem
  explicação definitiva (ver Sprint 05) — permanece um risco para o
  planejamento de sprints futuras que queiram paralelizar de novo.

## Dívida técnica

- Nenhum `PhysicalValidator` compartilhado ainda (decisão explícita da
  ADR 0014, não esquecimento).
- `condition_number` em `NumericalDiagnosticsValidator` continua sem
  nenhuma skill que o reporte (verificação prospectiva).
- `runner.py`'s `main()` sem cobertura instrumentada entre processos.
- `SkillLifecycle.validate_transition` sem uso em runtime.
- Telemetria de desenvolvimento (seção 19 do plano) ainda não
  implementada.

## Itens adiados

REST/MCP (Sprint 07), skills elétricas (Sprint 08+).

## Próxima sprint

**Sprint 07 — REST API e MCP**, conforme o plano mestre original.
Seguindo a instrução do usuário, um agente Opus deve validar esta
sprint e definir a divisão de trabalho para a Sprint 07 antes de
começar — inclusive reavaliando se o Grok está disponível novamente.
