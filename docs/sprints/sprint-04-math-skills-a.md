# Sprint 04 — Skills matemáticas A

- **Datas:** 2026-07-25 (execução em sessão única, continuação da Sprint 03)
- **Executor principal:** Claude Code
- **Executor paralelo:** Grok Build (worktree isolada)
- **Status:** concluída

## Objetivo

Entregar as três primeiras skills reais do catálogo MVP (seção 14.1):
`math.solve_root`, `math.interpolate`, `math.integrate` — a primeira vez
que o framework produz skills de engenharia de verdade, não fixtures de
teste.

## Contexto: correções pré-sprint

Antes de começar a construir skills, um agente Opus independente validou
a Sprint 03 e encontrou um bug real (não hipotético) que precisava ser
corrigido antes de paralelizar com o Grok:

- **Bug do `converged`**: `compute_status` tratava
  `diagnostics.get("converged") is None` como "método exato" — mas isso
  é indistinguível de "método iterativo cuja implementação esqueceu de
  reportar `converged`". Ambos produziam silenciosamente `VERIFIED`, o
  status de maior confiança do sistema, para um resultado nunca
  confirmado. Corrigido com a **ADR 0013**: `SkillManifest.method` virou
  `MethodRef` com `iterative: bool` obrigatório; se `iterative: true` e
  `diagnostics` não tiver a chave `converged`, isso agora é `FAILED`
  (violação de contrato), nunca um `VERIFIED` silencioso.
- **Validador sem blindagem**: `ExecutionService` agora envolve cada
  chamada de validador em try/except — um validador com bug vira um
  `ValidationOutcome` de `ERROR` (fail closed) em vez de derrubar o
  serviço inteiro.
- **Gap de memória não declarado**: `SandboxReport` ganhou
  `memory_limit_enforced: false`, com adendo na ADR 0012 — a seção 4.7
  do plano também exige limite de memória, que a ADR original não
  mencionava como gap.

## Entregas

### Fase A (Claude Code, sozinho)

- Correções acima (3 commits).
- `oec.kernel.numerics.expressions.compile_expression()`: avaliador
  seguro de expressões matemáticas. **Achado importante**: uma
  abordagem inicial baseada em `sympy.parsing.sympy_parser.parse_expr`
  foi testada e **rejeitada** — mesmo com `global_dict` restrito e
  `__builtins__` bloqueado, ainda aceitava
  `().__class__.__bases__[0].__subclasses__()`, um escape de sandbox
  conhecido, porque o parser do SymPy é construído sobre `eval()`.
  Reescrito para caminhar uma árvore `ast` com whitelist e interpretá-la
  diretamente — **zero uso de `eval()`/`exec()`** em qualquer lugar do
  módulo, verificado por teste estrutural
  (`test_evaluator_never_uses_eval_or_exec`).
- `oec.kernel.numerics.root_finding`: `find_root_bracketed` (brentq/
  bisect), `find_root_from_guess` (secant/newton), regra de seleção de
  método explícita e documentada (`select_default_method`).
- **`mathematics.solve_root`** completa — a skill template. 5 golden
  cases, todos de fonte independente (`mpmath.findroot`, implementação
  diferente da testada), incluindo o exemplo clássico de Burden & Faires
  (`x³-x-2`) e o número de Dottie (`cos(x)=x`).
- Achado durante a construção: colisão real de nomes de teste
  (`test_golden.py` existe tanto em `tests/unit/` quanto em cada
  skill). Corrigido com `--import-mode=importlib` no pytest, o que por
  sua vez exigiu mover `tests/_skill_helpers.py` para dentro de
  `oec.testing` (agora um pequeno SDK de teste público, útil também
  para autores de skills de terceiros).

### Fase B (Grok, worktree isolada `sprint04-math-skills`)

- **`mathematics.interpolate`**: linear/cubic_spline/pchip. `method`
  obrigatório (sem auto-seleção — os três métodos são filosoficamente
  diferentes, nenhum é "mais correto" por padrão). `iterative: false`.
  Extrapolação fora do range vira `WARNING`, não `ERROR`.
- **`mathematics.integrate`**: dois modos mutuamente exclusivos —
  função (`quad`, adaptativo) XOR tabulado (Simpson/trapézio,
  auto-selecionado por contagem de pontos). Toda a skill declara
  `iterative: true` (decisão conservadora, já que o modo função é
  adaptativo); o modo tabulado sempre reporta `converged: true`
  (cálculo direto por fórmula fixa, sem iteração que possa falhar) —
  raciocínio documentado inline no código.
- Zero sobreposição de arquivo com a árvore principal (confirmado via
  `git diff --stat` antes do merge).

### Fase C (Claude Code)

- Revisão de código linha por linha do trabalho do Grok.
- Gate de qualidade rodado de forma independente na worktree antes do
  merge (402 testes, 97.30% cobertura — bateu exatamente com o
  reportado pelo Grok).
- Merge `--no-ff` para `main`, gate completo rodado de novo na árvore
  integrada.
- Verificação manual via CLI real: `oec skills list --skills-root
  skills` lista as 3 skills MVP corretamente (achado cosmético: truncamento
  visual do Rich no terminal por causa do codepage do bash, não um bug —
  confirmado correto via `--json`).

## Arquivos alterados

~50 arquivos novos/modificados no total (Fase A + B + merge + Fase C).

## Commits

11 commits nesta sprint (mais o merge `--no-ff`), do
`6442b63 feat(skills): require methods to declare iterative convergence`
até `7d08ed2 docs(development): update codebase map for Sprint 04`. Ver
`git log --oneline` para a lista completa. Todos locais; nenhum remote,
nenhum push.

## Testes

```text
uv run pytest -q
402 passed in ~30s
```

## Cobertura

97.30% em `src/oec`. Todos os módulos novos (`expressions.py`,
`root_finding.py`, `testing.py`) em 90%+ (branches defensivos
inalcançáveis explicam o resto).

## Checks executados

| Check | Resultado |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | All formatted |
| `uv run mypy` (strict) | Success: no issues found in 48 source files |
| `uv run bandit -c pyproject.toml -r src/oec` | No issues identified |
| `uv run pytest -q` | 402 passed, 97.30% coverage, gate de 90% ativo |
| `uv build` | sdist + wheel built successfully |
| Gate independente na worktree do Grok (antes do merge) | 402 passed, 97.30% coverage — bateu com o relatado |
| `graphify update .` | 1306 nodes, 2340 edges, 89 communities |
| `oec skills list --skills-root skills` (manual) | lista as 3 skills MVP corretamente |

## Graphify

Cresceu de 787→1306 nós, o maior salto até agora (volume de código de
3 skills completas + kernel numérico). `docs/development/codebase-map.md`
documenta cada skill e módulo novo em detalhe.

## Decisões

- **`MethodRef` com `iterative: bool` obrigatório** (ADR 0013) —
  decisão mais importante da sprint, motivada por um bug real
  encontrado antes de qualquer skill existir para disparar o problema.
- **Parser AST restrito em vez de SymPy** — achado técnico central da
  sprint: a abordagem "óbvia" (SymPy) falhou um teste de segurança real
  (escape de sandbox via `__subclasses__()`), corrigido antes de virar
  parte do template que o Grok copiaria.
- **`interpolate.method` obrigatório, sem auto-seleção** — ao contrário
  de `solve_root` (que tem uma regra natural bracket-vs-guess), os três
  métodos de interpolação não têm um "padrão correto" óbvio; exigir
  escolha explícita é mais honesto que inventar uma regra arbitrária.
- **`integrate` declara `iterative: true` para a skill inteira**, mesmo
  o modo tabulado sendo determinístico — `iterative` é uma declaração
  estática do manifesto, não pode variar por chamada; a escolha
  conservadora (mais restritiva) foi a certa.
- **`oec.testing` como SDK público de teste** — resolveu a colisão de
  nomes de forma que também beneficia autores de skills de terceiros
  (não é um workaround interno, é infraestrutura reutilizável de
  verdade).
- **Sem auto-descoberta de validador por skill ainda** — `ExecutionService`
  continua exigindo que quem o constrói inclua explicitamente o
  `validation.py` de cada skill. Decisão consciente de não resolver
  isso ainda (só 3 skills não são amostra suficiente para desenhar a
  convenção certa de auto-wiring); documentado como dívida técnica
  explícita, não esquecida.

## Riscos

- Nenhuma skill usa `QuantityValue`/unidades ainda (as 3 skills
  matemáticas são intencionalmente adimensionais) — a validação
  dimensional (`dimensions.py`, `x-oec-unit`) só será exercitada de
  verdade nas skills elétricas (Sprint 08). Risco: pode haver ajustes
  necessários no contrato quando isso finalmente acontecer.
- `integrate`'s escolha de `iterative: true` para o modo tabulado é
  correta mas um pouco não-intuitiva (lida com isso via documentação
  extensa no código e no skill.md) — vale revisar se esse padrão se
  repete em skills futuras com múltiplos modos de execução.

## Dívida técnica

- Auto-descoberta de validador por skill a partir do `skill.yaml` (ver
  Decisões).
- Telemetria de desenvolvimento (seção 19 do plano) — ainda não
  implementada, sinalizada desde a revisão da Sprint 00-02, continua em
  aberto.
- `runner.py`'s `main()` sem cobertura instrumentada entre processos
  (conhecido desde a Sprint 03).
- `SkillLifecycle.validate_transition` sem uso em runtime (conhecido
  desde a Sprint 01).

## Itens adiados

Skills matemáticas B (`curve_fit`, `optimize_scalar`,
`optimize_constrained` — Sprint 05), SDK/CLI polido (Sprint 06), REST/MCP
(Sprint 07), skills elétricas (Sprint 08+).

## Próxima sprint

**Sprint 05 — Skills matemáticas B** (semanas 11–12): `math.curve_fit`,
`math.optimize_scalar`, `math.optimize_constrained` — completa o núcleo
matemático do MVP. Conforme instrução do usuário, ao final desta
sprint um agente Opus vai validar o trabalho e definir a divisão
Claude Code / Grok para a Sprint 05.
