# Sprint 05 — Skills matemáticas B

- **Datas:** 2026-07-25 (execução em sessão única, continuação da Sprint 04)
- **Executor:** Claude Code (sozinho — ver "Desvio do plano" abaixo)
- **Status:** concluída

## Objetivo

Completar o núcleo matemático do MVP (seção 14.1 do plano):
`math.optimize_scalar`, `math.optimize_constrained`, `math.curve_fit` —
as três skills de otimização, construídas sobre um novo
`oec.kernel.optimization` com um contrato de diagnóstico único
compartilhado entre elas.

## Contexto: correções pré-sprint (Fase A)

Antes de construir as skills de otimização, uma revisão independente
(Opus) da Sprint 04 encontrou dois problemas reais em `mathematics.integrate`:

- **Inconsistência VERIFIED/VALIDATED**: `integrate` tem dois modos sob
  um único manifesto — modo função (adaptativo) e modo tabulado (exato,
  fórmula fechada) — mas `method.iterative` é uma única flag no nível
  da skill. Declarar `iterative: true` (correto para o modo adaptativo)
  fazia o modo tabulado, igualmente exato, receber `VALIDATED` em vez
  de `VERIFIED` — pior status que `interpolate`, que faz o mesmo tipo
  de cálculo exato. **Corrigido via emenda à ADR 0013**:
  `diagnostics["converged"]` agora pode ser `null` *presente* (não
  ausente) para sinalizar "esta chamada específica foi exata", elegível
  para `VERIFIED` mesmo em uma skill cujo `iterative: true` cobre outro
  modo.
- **Heurística de convergência fraca em `quad()`**: comparar apenas
  `abs_error <= tolerance` não capta os sinais reais de falha do
  QUADPACK. Corrigido usando `quad(..., full_output=True)` e tratando a
  mensagem de explicação do QUADPACK (só retornada quando há um
  problema real) como sinal autoritativo — verificado contra um caso
  real de falha (`sin(1/x)` em `[0.0001, 1.0]` com tolerâncias `1e-14`).

## Desvio do plano: Grok bloqueado pelo classificador de permissões

O plano original (definido pelo Opus ao fechar a Sprint 04) era repetir
o padrão da Sprint 04: Claude Code constrói `optimize_scalar` sozinho
(template), depois paraleliza — Claude Code fica com
`optimize_constrained`, Grok fica com `curve_fit` em uma worktree
isolada. A worktree (`sprint05-curve-fit`) foi criada e um prompt
completo e autocontido foi escrito para o Grok.

O lançamento autônomo do Grok (`grok -p ... --always-approve` e depois
`--permission-mode auto`) foi **bloqueado pelo classificador de
permissões do próprio ambiente** em ambos os modos tentados — não um
problema do Grok em si (funcionou normalmente na Sprint 04). Seguindo a
orientação explícita da ferramenta ("não tente contornar a negação"),
nenhuma outra tentativa de workaround foi feita. A worktree não usada
foi removida e ambas as skills (`optimize_constrained` e `curve_fit`)
foram construídas por Claude Code, sozinho, sequencialmente,
diretamente em `main` — sem necessidade de worktree isolada, já que não
havia um segundo agente paralelo. Documentado em
`docs/development/codebase-map.md` para que uma sprint futura não
assuma que a delegação ao Grok está disponível incondicionalmente.

## Entregas

### `oec.kernel.optimization` — novo kernel de otimização

- **`diagnostics.py`**: `OptimizationDiagnostics`, um único modelo
  compartilhado pelas três skills (`method`, `converged`, `message`,
  `n_iterations`, `n_function_evaluations`, mais `optimality`,
  `constraint_violation`, `feasible`, `residuals`, `covariance`, todos
  opcionais). Um campo que um método não mede fica `None` — nunca
  inventado para fazer as três skills parecerem uniformes quando não
  são.
- **`scalar.py`**: `minimize_scalar()` sobre `scipy.optimize.minimize_scalar`
  (bounded/brent/golden), mesmo padrão de `root_finding.py`.
- **`constrained.py`**: `minimize_constrained()` sobre
  `scipy.optimize.minimize` (SLSQP padrão, `trust-constr` alternativa
  explícita). Reporta `optimality`/`constr_violation` nativos quando o
  método realmente os calcula (`trust-constr`); SLSQP não calcula nada
  disso, então `constraint_violation`/`feasible` são computados
  avaliando cada restrição na solução.
- **`curve_fit.py`**: `fit_curve()` sobre `scipy.optimize.curve_fit`
  (`lm` padrão sem bounds — não suporta bounds; `trf` com bounds;
  `dogbox` alternativa explícita). SciPy lança `RuntimeError` puro em
  não-convergência, sem estado parcial exposto; capturado e convertido
  em `diagnostics.converged = False` (resultado diagnóstico válido, ADR
  0007), com `params`/`residuals`/`covariance` caindo de volta para o
  chute inicial — documentado, não aproximado silenciosamente.
- **`oec.kernel.numerics.expressions.compile_expression_vector()`**:
  generalização de `compile_expression()` para N variáveis nomeadas,
  mesma gramática AST restrita e mesma garantia de segurança —
  necessário para os objetivos/restrições multivariáveis de
  `optimize_constrained` e o modelo de `curve_fit`. A assinatura pública
  de `compile_expression()` não mudou; os helpers privados
  `_validate_node`/`_eval_node` foram generalizados internamente
  (conjunto de símbolos / dict de bindings em vez de um nome fixo).

### Skills

- **`mathematics.optimize_scalar`** — minimização escalar
  bounded/brent/golden. Skill template da família; golden case de
  múltiplos mínimos verificado por forma fechada (`x**4 - x**2`, dois
  mínimos globais empatados), documentando explicitamente que Brent
  bounded retorna o mínimo que estiver dentro do intervalo dado, não
  uma busca global.
- **`mathematics.optimize_constrained`** — minimização N-variável, com
  bounds e restrições não-lineares (SLSQP padrão, `trust-constr`
  alternativa), sobre `compile_expression_vector`. Golden cases: um
  mínimo restrito verificado por multiplicadores de Lagrange, dois dos
  quatro mínimos globais empatados da função de Himmelblau alcançados a
  partir de `x0` diferentes (otimizador local), e um caso de restrições
  mutuamente contraditórias confirmando `converged=False`/
  `feasible=False` como resultado diagnóstico, não crash.
- **`mathematics.curve_fit`** — ajuste não-linear por mínimos quadrados
  (`lm`/`trf`/`dogbox`), também sobre `compile_expression_vector`
  (variável independente fixa `x`, `parameter_names` fornece o resto
  dos símbolos). Golden cases usam dados sem ruído gerados a partir de
  parâmetros verdadeiros conhecidos como oráculo independente (a
  verdade é fixada por construção, não derivada de nenhum solver), mais
  um caso mostrando que um `initial_guess` ruim em um parâmetro
  periódico converge para um mínimo local diferente e errado
  (`converged=True` no sentido do SciPy, mas os parâmetros errados).

## Arquivos alterados

45 arquivos novos/modificados no total (6 commits).

## Commits

6 commits nesta sprint, de
`1dac808 fix(execution): allow a present-but-null converged for per-call exact results`
até `079565e feat(kernel,skills): add oec.kernel.optimization.curve_fit and math.curve_fit`.
Ver `git log --oneline` para a lista completa. Todos locais; nenhum
remote, nenhum push.

## Testes

```text
uv run pytest -q
499 passed in ~35s
```

## Cobertura

96.78% em `src/oec` (gate de 90% ativo, `fail_under=90`).

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | All formatted |
| `uv run mypy` (strict) | Success: no issues found in 52 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified |
| `uv run pytest -q` | 499 passed, 96.78% coverage |
| `uv build` | sdist + wheel built successfully |

## Decisões

- **Emenda à ADR 0013** — `converged: null` presente (distinto de
  ausente) sinaliza "esta chamada foi exata" por chamada, não apenas
  por skill. Corrige o problema de status de `integrate` sem enfraquecer
  a checagem original de omissão.
- **`OptimizationDiagnostics` como contrato único para as três skills de
  otimização** — em vez de cada skill inventar seu próprio shape de
  diagnóstico, um modelo com campos opcionais cobre os três casos;
  campos não aplicáveis ficam `None`, nunca inventados.
- **`compile_expression_vector` generaliza `compile_expression`
  internamente, sem quebrar a API pública existente** — os três skills
  da Sprint 04 continuam funcionando exatamente como antes, verificado
  contra a suíte de testes existente antes de prosseguir.
- **`curve_fit` sem `sigma` (peso por ponto) nem `tolerance`** — escopo
  MVP deliberado, documentado no `skill.md`, não esquecimento.
- **Grok bloqueado pelo classificador do ambiente** — ver seção "Desvio
  do plano" acima. Decisão: não insistir em contornar, adaptar a
  execução para solo.

## Riscos

- A dependência de `oec.kernel.optimization` em `scipy-stubs` para
  passar no mypy estrito exigiu um pequeno cuidado extra: o parâmetro
  `fun` de `scipy.optimize.minimize`/`curve_fit` é tipado pelo
  scipy-stubs como aceitando um ndarray especificamente — resolvido com
  um adaptador tipado (`_objective`/`_vectorized_model`) em vez de
  `# type: ignore`, evitando uma dependência frágil de qual versão
  exata do scipy-stubs resolve no ambiente do pre-commit vs. no venv do
  projeto (achado real durante a sprint, documentado nas mensagens de
  commit).
- O bloqueio do Grok pelo classificador é específico deste ambiente/
  sessão — não se sabe se é permanente. Uma sprint futura que planeje
  delegação ao Grok deve verificar isso cedo, não assumir.

## Dívida técnica

- Auto-descoberta de validador por skill a partir do `skill.yaml`
  (conhecida desde a Sprint 04, ainda não resolvida — 6 skills ainda
  não são amostra suficiente segundo o critério original, mas a
  decisão deve ser revisitada na Sprint 06).
- Telemetria de desenvolvimento (seção 19 do plano) — ainda não
  implementada.
- `runner.py`'s `main()` sem cobertura instrumentada entre processos.
- `SkillLifecycle.validate_transition` sem uso em runtime.
- `curve_fit` sem suporte a `sigma`/`tolerance` (ver Decisões).

## Itens adiados

SDK/CLI polido (Sprint 06), REST/MCP (Sprint 07), skills elétricas
(Sprint 08+).

## Próxima sprint

**Sprint 06 — Python SDK e CLI** (conforme o plano mestre). Seguindo a
instrução do usuário, um agente Opus deve validar esta sprint e definir
a divisão de trabalho para a Sprint 06 antes de começar.
