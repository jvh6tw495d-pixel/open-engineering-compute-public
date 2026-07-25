# Sprint 02 — Kernel de unidades e normalização

- **Datas:** 2026-07-25 (execução em sessão única)
- **Executor:** Claude Code
- **Status:** concluída

## Objetivo

Impedir cálculos físicos com grandezas ambíguas: Pint, modelo público de
quantidade, conversão, normalização, validação dimensional, política
para floats adimensionais, erros de unidades.

## Entregas

- `oec.kernel.units.registry.ureg`: instância única e compartilhada de
  `pint.UnitRegistry`. Nenhum outro módulo instancia `pint.UnitRegistry()`
  diretamente — evita o problema conhecido do Pint de quantidades de
  registries diferentes não serem comparáveis/convertíveis entre si.
- `oec.kernel.units.quantity.QuantityValue`: modelo Pydantic frozen
  `{value: float, unit: str}` — a forma pública exata da ADR 0003.
  Rejeita unidade vazia (Pint trata `""` como `dimensionless` por padrão,
  então isso precisa ser barrado explicitamente), unidade desconhecida, e
  valores não finitos (NaN/Infinity). Não assume sinal — quantidades como
  queda de tensão ou temperatura em Celsius podem ser legitimamente
  negativas; isso fica para a validação física de cada skill (seção 12.4).
- `oec.kernel.units.serialization`: `to_pint()`/`from_pint()` — conversão
  entre `QuantityValue` e `pint.Quantity`, sempre pela registry
  compartilhada; forma abreviada de unidade (`kW`, não `kilowatt`).
- `oec.kernel.units.normalize`: `normalize(quantity, to_unit=...) ->
  NormalizedQuantity` (par original+normalizado, para proveniência) e
  `is_compatible(unit_a, unit_b) -> bool`. Incompatibilidade dimensional
  ou unidade de destino desconhecida levantam `UnitError`.
- `oec.errors.UnitError` (extends `OECValidationError`): carrega
  `from_unit`/`to_unit` em `details`.
- ADR 0011: decisões de implementação (registry único, sem curadoria de
  unidades exóticas ainda, comportamento padrão do Pint para unidades
  com offset mantido — falha alto em vez de adivinhar).
- 25 novos testes: unitários (`QuantityValue`, serialização, normalize,
  incompatibilidade) + 2 suites de propriedade (Hypothesis: round-trip
  A→B→A recupera o valor original; conversão dupla para a mesma unidade
  é idempotente) sobre pares de unidades SI compatíveis.

## Arquivos alterados

11 arquivos novos, 3 modificados (`errors.py`, `.pre-commit-config.yaml`,
`codebase-map.md`).

## Commits

```text
a6b665a feat(kernel): add the controlled Pint unit registry
b216c38 feat(kernel): add QuantityValue
5ce8ab4 feat(kernel): add QuantityValue <-> pint.Quantity conversion
c0d2ad7 feat(kernel): add unit normalization and dimensional validation
6e8fe61 test: add property-based tests for unit conversion
54c7879 docs(adr): add ADR 0011 for unit engine implementation choices
133d32e docs(development): update codebase map for Sprint 02
```

Mais dois commits de infraestrutura: `chore: enforce the 90% coverage
gate` e `chore(pre-commit): add pint to the mypy hook's isolated env`
(mesma classe de problema já visto na Sprint 01 — hook mypy roda em venv
isolado do pre-commit, precisa de `additional_dependencies` explícitas).

**Nota:** o primeiro commit desta sprint (`UnitError`) falhou por causa
do hook mypy (pint não instalado no venv isolado); ao corrigir e
recommitar, o `errors.py` staged acabou entrando junto no commit
seguinte (`chore(pre-commit): add pint...`), misturando as duas
mudanças num único commit. Cosmético, não vale reescrever histórico
para corrigir.

Todos os commits são locais; nenhum remote configurado, nenhum push.

## Testes

```text
uv run pytest -q
119 passed in ~11s
```

## Cobertura

99.07% em `src/oec` (472 statements, 1 miss). Todos os módulos novos do
kernel de unidades em 100%. **O gate de 90% agora é imposto de verdade**
(`fail_under = 90`, absorvido antes desta sprint por recomendação da
revisão independente do Opus) — a suíte já falha se a cobertura cair.

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 66 files already formatted |
| `uv run mypy` (strict) | Success: no issues found in 32 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified |
| `uv run pytest -q` | 119 passed, 99.07% coverage, gate de 90% ativo |
| `uv build` | sdist + wheel built successfully |
| `graphify update .` | 459 nodes, 765 edges, 44 communities |

## Graphify

Atualizado ao final da sprint. Cresceu de 376→459 nós. `docs/development/
codebase-map.md` documenta o fluxo de normalização de quantidades e
deixa explícito que `QuantityValue`/`normalize()` ainda **não** estão
plugados em `SkillManifest`/`ExecutionRequest` — isso é trabalho da
Sprint 03/04, quando a Validation Engine e as primeiras skills reais
existirem para consumi-los.

## Decisões

- **Registry único e compartilhado** (`ureg`) — decisão central da
  sprint; documentada como ADR 0011 por ser uma escolha de implementação
  não coberta pela ADR 0003 (que só fixou a política, não o mecanismo).
- **Sem curadoria de unidades exóticas ainda** — Pint vem com unidades
  que nenhuma skill de engenharia jamais vai precisar (até algumas
  "piada", como `smoot`). Curar uma lista explícita agora seria
  especulativo sem skills reais para derivar a lista; adiado para
  quando as skills matemáticas/elétricas (Sprints 04/08) revelarem o
  que é de fato necessário.
- **Comportamento padrão do Pint para unidades com offset mantido**
  (não habilitado `autoconvert_offset_to_baseunit`) — permitir aritmética
  ambígua com temperatura silenciosamente poderia produzir resultado
  fisicamente errado; alinhado à instrução 10 do plano ("não mascarar
  warnings de solver").
- **`normalize()` retorna par original+normalizado** (`NormalizedQuantity`)
  em vez de só o valor convertido — é o que permite ao futuro
  `ExecutionResult.provenance` (Sprint 03) registrar a unidade original
  sem a Sprint 02 precisar tocar no pipeline de execução.
- **`QuantityValue` não assume sinal** — decisão deliberada para não
  quebrar quantidades legitimamente negativas (queda de tensão, potência
  reativa, temperatura Celsius); validação de sinal fica na camada física
  de cada skill.

## Riscos

- Nenhum skill real ainda usa `QuantityValue` — a integração real só
  acontece quando `input.schema.json` de uma skill de verdade precisar
  representar uma grandeza física, o que só ocorre a partir da Sprint 04.
  Até lá, o kernel de unidades está testado isoladamente, não
  end-to-end.
- Achado da revisão independente anterior (Opus, antes desta sprint):
  `ExecutionPolicy` promete `timeout_seconds`/`network_access: false`/
  `filesystem_access: false` por skill, mas isso é praticamente
  inaplicável a código Python importado in-process. Esta sprint não
  resolveu isso (fora de escopo — é problema da Sprint 03, Execution
  Service); permanece como risco arquitetural relevante para a próxima
  sprint, e deve virar uma ADR formal lá, não uma implementação
  apressada.

## Dívida técnica

- Sem lista curada de unidades permitidas (ver Decisões acima).
- `QuantityValue`/`normalize()` desconectados de `SkillManifest`/
  `ExecutionRequest`/`ExecutionResult` — os campos `inputs`/`result`
  continuam `dict[str, Any]` sem tipo.
- `oec.errors` ainda não tem erro dedicado de timeout — só quando a
  Execution Service (Sprint 03) existir para levantá-lo.

## Itens adiados

Validation Engine, Execution Service, skills matemáticas/elétricas
reais, REST API, MCP, Odysseus, Open Science — conforme escopo da
Sprint 02 (seção 33 do plano).

## Próxima sprint

**Sprint 03 — Execution Pipeline e Validation Engine** (semanas 7–8):
`ExecutionService`, validadores compostos (schema/dimensional/
matemática/física/numérica/invariantes), status de execução,
proveniência, timeout básico, golden case framework. Ponto de atenção
explícito: decidir e documentar em ADR como o sandboxing de execução
(timeout, sem rede, sem filesystem) será de fato implementado, dado que
"importar o módulo Python da skill in-process" não impõe nenhuma dessas
garantias por si só.

## Nota sobre ferramentas de execução

Nesta sessão, confirmou-se a disponibilidade local de dois agentes de
codificação adicionais além do Claude Code: **Grok Build**
(`C:\Users\joaop\.grok\bin\grok.exe`, invocável via `grok --cwd <dir> -p
"<tarefa>"`) e **OpenCode** (`opencode`, com acesso a múltiplos modelos
— Kimi K3, GLM 5.2, Grok 4.5, entre outros). A partir da Sprint 03, o
plano é usar o Grok como executor paralelo de subtarefas bem delimitadas
(fatias isoladas do trabalho, sem edição simultânea dos mesmos arquivos),
com a divisão de trabalho a ser decidida com apoio de uma avaliação
independente antes de cada divisão.
