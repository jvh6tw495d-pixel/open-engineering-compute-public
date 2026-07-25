# Sprint 03 — Execution Pipeline e Validation Engine

- **Datas:** 2026-07-25 (execução em sessão única)
- **Executor principal:** Claude Code
- **Executor paralelo:** Grok Build (worktree isolada, validadores concretos)
- **Status:** concluída

## Objetivo

Executar uma skill de ponta a ponta com diagnóstico e proveniência:
`ExecutionService`, validação em camadas, status de execução, timeout
básico, framework de golden case.

## Contexto: primeira sprint com orquestração multi-agente

Esta foi a primeira sprint executada com divisão real de trabalho entre
agentes, seguindo uma estratégia decidida por um agente Opus independente
(ver mensagem do usuário e resposta anterior nesta sessão) e o framework
de papéis da seção 18 do plano mestre:

- **Fase A (Claude Code, sozinho):** decisões arquiteturais que não
  podiam ser paralelizadas sem risco — ADR de sandboxing (0012), o
  contrato congelado de validadores (`oec.validation.base`), a semântica
  exata do `ExecutionStatus` (ADR 0007, preenchendo um slot que o
  próprio plano já reservava na seção 25), e o shape de proveniência.
- **Fase B (paralela, git worktrees separadas):** Grok implementou as
  camadas concretas da Validation Engine numa worktree isolada
  (`../oec-validation`, branch `sprint03-validation`); Claude Code
  implementou o `ExecutionService` na árvore principal, ao mesmo tempo.
  Zero sobreposição de arquivos entre as duas fatias — confirmado via
  `git diff --stat` antes do merge.
- **Fase C (Claude Code):** revisão do diff do Grok, gate de qualidade
  rodado de forma independente na worktree (227 testes, 98.92%
  cobertura — bateu exatamente com o relatado pelo Grok), merge
  (`--no-ff`) para `main`, e um teste de integração novo
  (`test_full_validation_wiring.py`) provando que os dois lados do
  contrato realmente batem sem ajuste nenhum.

## Entregas

### Fase A — contrato congelado

- **ADR 0012** (`docs/architecture/adr/0012-subprocess-execution-sandbox.md`):
  skills executam em subprocesso, não in-process. `timeout_seconds` é
  imposto de verdade (cross-platform, inclusive Windows).
  `network_access`/`filesystem_access` do manifesto **não** são impostos
  nesta sprint — declarado explicitamente, nunca implícito
  (`ExecutionResult.provenance.sandbox` sempre reporta o que foi
  realmente aplicado).
- **ADR 0007** (`docs/architecture/adr/0007-validation-status-model.md`):
  tabela de precedência exata dos 7 status de `ExecutionStatus`.
  `VERIFIED` = método exato/fechado sem warnings; `VALIDATED` = método
  iterativo convergido sem warnings; não convergido vence warning na
  precedência. Preenche o slot de ADR que a seção 25 do plano já
  reservava para "validation-status-model".
- `oec.validation.base`: `Severity`, `ValidationOutcome`,
  `InputValidator`/`ResultValidator` (Protocols) — ambos recebem o
  `LoadedSkill` completo, não só o manifesto (corrigido antes do handoff
  ao Grok: o validador de schema precisa do `input_schema` já parseado).
- `oec.execution.status.compute_status()`: única implementação da tabela
  da ADR 0007.
- `oec.execution.provenance`: `build_provenance()`, `SandboxReport`,
  `QuantityProvenance` — shape completo de `ExecutionResult.provenance`.

### Fase B — implementação paralela

**Claude Code (`ExecutionService`):**
- `oec.execution.runner`: roda dentro do subprocesso; único lugar do
  código que importa a implementação Python de uma skill. Protocolo
  stdin/stdout JSON: `{"result": ..., "diagnostics": ...}`.
- `oec.execution.sandbox.run_in_sandbox()`: wrapper do lado do processo
  pai; timeout real testado (~1s, mata o processo de fato).
- `oec.execution.service.ExecutionService`: pipeline completo
  resolve→validate→execute→validate→status→provenance. Validadores
  injetados via lista, sem import direto de nenhuma camada concreta —
  é isso que permitiu o paralelismo.
- `oec.validation.golden`: `GoldenCase`, `assert_matches_golden()` —
  framework de golden case (seção 12.6), nunca roda no pipeline runtime.
- Fixture `mathematics.identity` atualizada para o novo contrato do
  runner; `write_skill_dir()` ganhou `implementation_code` override.

**Grok (Validation Engine concreta, worktree isolada):**
- `schema.py` — `SchemaValidator` via `jsonschema.Draft202012Validator`.
- `dimensions.py` — `DimensionalValidator`, convenção `x-oec-unit`.
- `mathematical.py`/`physical.py` — bibliotecas de funções puras
  reutilizáveis (não plugadas no pipeline ainda — sem skill real para
  declarar as regras; decisão explícita no meu briefing para não fazer
  over-engineering especulativo).
- `numerical.py` — `NumericalDiagnosticsValidator` (só `WARNING`s).
- `invariants.py` — `InvariantValidator` (NaN/Infinity + output schema).
- `jsonschema>=4.20` adicionado às dependências core.

### Fase C — integração

- Merge `--no-ff` de `sprint03-validation` em `main` (16 arquivos, zero
  conflitos).
- `tests/integration/test_full_validation_wiring.py`: prova concreta
  (não só afirmação em relatório) de que os validadores reais do Grok
  funcionam com o `ExecutionService` sem nenhum ajuste.
- Worktree e branch removidas após confirmação do merge.

## Arquivos alterados

~35 arquivos novos/modificados no total (Fase A + B + merge + Fase C).

## Commits

25 commits nesta sprint (ver `git log --oneline` para a lista completa),
incluindo o merge `--no-ff` que preserva a história paralela das duas
fatias de trabalho. Todos locais; nenhum remote configurado.

## Testes

```text
uv run pytest -q
268 passed in ~18-19s
```

## Cobertura

97.77% em `src/oec` (852 statements, 15 miss). Todos os módulos novos de
validação e a maior parte da execução em 95-100%; `runner.py` em ~73%
por limitação de medição de cobertura entre processos (a lógica interna
está 100% coberta via testes unitários diretos de `_run`/
`_load_entrypoint`; só o bloco `main()`/`__main__` que roda de fato
dentro do subprocesso filho não é instrumentado pelo processo pai).

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | All formatted |
| `uv run mypy` (strict) | Success: no issues found in 45 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified (4 `#nosec` justificados: subprocess fixo, sem shell, sem input do usuário) |
| `uv run pytest -q` | 268 passed, 97.77% coverage, gate de 90% ativo |
| `uv build` | sdist + wheel built successfully |
| Gate independente na worktree do Grok (antes do merge) | 227 passed, 98.92% coverage — bateu com o relatado pelo Grok |
| `graphify update .` | 787 nodes, 1531 edges, 62 communities |

## Graphify

Atualizado ao final da sprint. Cresceu de 459→787 nós — o maior salto
até agora, refletindo o volume de código novo desta sprint.
`docs/development/codebase-map.md` documenta o pipeline completo módulo
por módulo, incluindo a divisão exata entre o trabalho do Claude Code e
do Grok.

## Decisões

- **Sandboxing por subprocesso, não in-process** (ADR 0012) — a decisão
  mais importante da sprint. In-process não consegue impor timeout real
  nem isolamento de rede/filesystem em Python; subprocesso pelo menos
  entrega timeout real, cross-platform. Isolamento de rede/filesystem
  fica declarado como gap real, não implícito.
- **`LoadedSkill` em vez de `SkillManifest` puro nos validadores** —
  achado durante a própria Fase A, antes do handoff: o validador de
  schema precisa do JSON Schema já parseado, que só está no
  `LoadedSkill`. Corrigido antes do Grok começar a codar contra o
  contrato errado.
- **`mathematical.py`/`physical.py` como bibliotecas de funções, não
  validadores plugados no pipeline** — decisão explícita no briefing do
  Grok: JSON Schema nativo já cobre a maior parte da seção 12.3/12.4
  (`minimum`/`maximum`/etc.); o que sobra são checagens específicas de
  cada skill, que só existirão a partir da Sprint 04. Evita
  over-engineering especulativo.
- **Validadores injetados, nunca importados diretamente pelo
  `ExecutionService`** — é a decisão de design que tornou o paralelismo
  real possível: o pipeline só depende do contrato congelado
  (`oec.validation.base`), nunca de uma camada concreta específica.
- **Git worktrees para isolamento físico** — zero risco de conflito de
  arquivo entre os dois agentes trabalhando ao mesmo tempo, confirmado
  por `git diff --stat` antes do merge (16 arquivos, todos exclusivos do
  Grok).
- **Grok nunca commitou em `main`** — só na branch da própria worktree;
  o merge foi decisão e ação exclusiva do Claude Code, depois de revisão
  de código linha por linha e gate independente.

## Riscos

- Nenhuma skill real (matemática ou elétrica) existe ainda, então
  `QuantityValue`, a convenção `x-oec-unit`, e as bibliotecas
  `mathematical.py`/`physical.py` estão testadas isoladamente mas nunca
  exercitadas por uma skill de verdade. Esse é exatamente o trabalho da
  Sprint 04 — e é o primeiro teste real da arquitetura completa.
- Isolamento de rede/filesystem continua não implementado (gap
  documentado, não escondido) — se alguma skill precisar de garantia
  real de isolamento antes da sprint de hardening, precisa ser tratada
  como não-confiável por padrão até lá.
- Overhead de subprocesso por execução (~0.5s de startup de interpretador,
  medido manualmente) é aceitável para o modelo síncrono do Alpha (seção
  13.3 do plano: "execução síncrona no Alpha"), mas vira gargalo real se
  a API REST (Sprint 07) precisar de muitas execuções concorrentes —
  meio caminho andado é usar um pool de processos, ainda não decidido.

## Dívida técnica

- `runner.py`'s `main()`/`__main__` não instrumentado por cobertura
  entre processos (ver seção Cobertura acima).
- `QuantityValue`/`x-oec-unit`/bibliotecas mathematical/physical sem uso
  real ainda — só testes isolados.
- `SkillLifecycle.validate_transition` continua não chamado em runtime
  (dívida já registrada desde a Sprint 01).
- Sem `oec run` na CLI ainda — `ExecutionService` só é exercitado via
  import direto em Python/testes; isso é escopo da Sprint 06
  (Python SDK/CLI), deliberadamente não antecipado aqui.

## Itens adiados

Skills matemáticas/elétricas reais, engine de unidades wired em schemas
reais, REST API, MCP, Odysseus, Open Science, telemetria de
desenvolvimento (seção 19 do plano — ainda não implementada, achado
pendente da revisão Opus anterior).

## Próxima sprint

**Sprint 04 — Skills matemáticas A** (semanas 9–10): `math.solve_root`,
`math.interpolate`, `math.integrate` — as primeiras skills reais do
catálogo (seção 14), com metodologia oficial, golden cases de verdade, e
o primeiro teste honesto de toda a arquitetura construída até aqui.
