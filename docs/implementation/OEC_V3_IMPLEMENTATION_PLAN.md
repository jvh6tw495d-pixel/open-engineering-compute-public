# OEC V3 — Plano de implementação

**Fonte:** Roadmap detalhado de versões até v3.0 (plano V3)
**Data do plano:** 2026-07-26
**Actualização de estado:** 2026-07-27 — **`oec==2.0.0` Scientific Kernel cortado** (`51407ec`)
**Baseline real:** **40 skills**, 5 agentes, SDK/CLI/REST/MCP, OPS v0.1, HiGHS, `oec.core` Scientific Kernel, árvore public-alpha local
**Marco público V3:** **v3.0 = primeiro lançamento oficial no GitHub**
**Handoff construção (GPT):** [GPT_CONSTRUCTION_HANDOFF.md](GPT_CONSTRUCTION_HANDOFF.md) — GPT constrói; Grok valida.

---

## 0. Resumo executivo

| Bloco V3 | Significado | Estado actual (2026-07-27) | Acção |
|---|---|---|---|
| **v0.x – v1.5** | Skill Engine + interfaces + alpha privado | **DONE** (`1.5.0` closed) | Manter |
| **v2.0** | Scientific Kernel | **DONE** (`2.0.0` — `oec.core`, ADR 0019) | — |
| **v2.1 – v2.5** | Quantities → Math IR → Math Complete | **NEXT** (sem Math IR ainda) | **GPT constrói a partir de v2.1** |
| **v2.6 – v2.8** | Physics / Multiphysics / Chemistry | **Não iniciado** (só eléctrica clássica + energy genérico) | Após v2.5 estável |
| **v2.9 – v3.0** | Integração + lançamento público | Prep parcial (árvore limpa local) | Gates + publish no fim |

**Tese de execução:** não recomeçar do zero. **v1.5 e v2.0 fechados.** Empilhar **v2.1→v2.5** em fatias com gates mensuráveis. Física/química são programas multi-trimestre **depois** da matemática completa.

**Regra de ouro (inalterada):**

> OEC = ciência generalizável. Private decision engines / commercial scoring /
> pricing / client data = **fora**.

---

## 1. Mapa honestidade: roadmap V3 ↔ repositório actual

### 1.1 Já coberto (crédito v0–v1.5)

| Capability V3 | Evidência no repo |
|---|---|
| Skills executáveis com contrato | `skills/**/skill.yaml` + schemas + golden tests |
| Registry / loader / lifecycle | `src/oec/skills/` |
| Execução síncrona + sandbox | `src/oec/execution/` |
| Status graduado (não bool success) | ADR 0007, `ExecutionStatus` |
| Validação multi-camada | `src/oec/validation/` |
| Unidades (Pint) | `src/oec/kernel/units/` |
| Proveniência | `input_hash`, `backends[]` (ADR 0017) |
| SDK / CLI / REST / MCP | `sdk.py`, `cli/`, `api/`, `mcp/` |
| Matemática inicial | roots, integrate, interpolate, curve_fit, opt scalar/constrained |
| Eléctrica inicial | 6 skills `electrical.*` |
| Linear / ODE / stats / TS / opt / energy / finance | ~40 skills |
| Agentes formuladores (fora do wheel) | `agents/*` |
| OPS v0.1 LP/MILP | `src/oec/ops/`, `optimization.lp/milp` |
| Alpha privado operacional (gates) | pytest ~800, ruff/mypy, forbidden-names, public tree local |

### 1.2 Gaps estruturais vs V3 (ainda não existem)

| Bloco V3 | Gap |
|---|---|
| **Scientific Kernel** (`ScientificResult`, `Assumption`, …) | Hoje: `ExecutionResult` + dicts de skill; não há camada `core/` formal unificada |
| **Math IR** | Expressões AST restritas + OPS linear; **sem IR simbólico geral** |
| **Backend Registry** | Backends listados em provenance; **sem registry de capabilities/fallback** |
| **Verification Engine** formal pré/pós | Validadores existem, mas não o pipeline Verification V3 completo |
| **Applied math completo** | Faltam: controle, decisão, Pareto/CVaR, forecast TS, sparse sistemático, DAE, autodiff |
| **Physics / Chemistry Complete** | Fora do catálogo (excepto eléctrica clássica / energy genérico) |
| **Model Registry / Fidelity** | Não existe |
| **ScientificResult unificado** | Contrato ainda é `ExecutionResult` por skill |
| **v3.0 public GitHub** | Árvore limpa local; **sem remote público** |

### 1.3 Versão semântica recomendada (transição)

| Etiqueta de marketing V3 | Tag git / pyproject sugerida | Quando |
|---|---|---|
| v1.5 Alpha privado | `1.5.0` | Após fecho de gaps §2 |
| v2.0 Scientific Kernel | `2.0.0` | Kernel formal estável |
| … | `2.1.0` … `2.9.0` | Por gate |
| v3.0 public | `3.0.0` | Lançamento GitHub |

Manter `0.1.0` só até o primeiro cut v1.5; evitar inflação de minor sem gates.

---

## 2. Sequência de implementação (dependências)

```text
[AGORA]
   │
   ▼
v1.5 Closeout ──► versionamento + gaps alpha + agents packaging
   │
   ▼
v2.0 Scientific Kernel ──► tipos core, ScientificResult, provenance unificada
   │
   ▼
v2.1 Quantities ──► consolidar units/dimensions (já parcial) + tensor/uncertainty hooks
   │
   ▼
v2.2 Math IR + Modeling ──► IR, classificador, compile→backend
   │
   ├──────────────────────┐
   ▼                      ▼
v2.3 Applied Math      v2.4 Computational + Verification
   │                      │
   └──────────┬───────────┘
              ▼
           v2.5 Mathematics Complete  (GATE DURO)
              │
              ▼
           v2.6 Physics Complete
              │
              ▼
           v2.7 Multiphysics
              │
              ▼
           v2.8 Chemistry Complete
              │
              ▼
           v2.9 RC + Scientific IR + Model Registry
              │
              ▼
           v3.0 Public GitHub launch
```

**Paralelo permitido:** documentação, benchmarks, CI, exemplos — em todas as fases.
**Proibido em paralelo cedo:** física/química profundas **antes** de v2.5 (gera dívida de IR/unidades).

---

## 3. Fase imediata — v1.5 Closeout (2–4 semanas)

### Objectivo
Declarar **Alpha privado operacional** alinhado ao §10 do roadmap V3, sem fingir Math IR.

### Work packages

| ID | Entrega | DoD |
|---|---|---|
| **C1** | Mapa de compliance v1.5 | Doc: cada bullet v1.0–v1.5 → path no repo ou “N/A com gap” |
| **C2** | Version bump `1.5.0` | pyproject + CHANGELOG + classifier Pre-Alpha/Alpha |
| **C3** | Skill contract completeness audit | Script: toda skill tem schema, references, golden, method.iterative |
| **C4** | Agents packaging | Documentar/import path; opcional `oec-agents` extra ou package separado |
| **C5** | Golden set v1.5 | Inventário canónico ≥ N casos eléctricos + math + opt (sem 130 ainda) |
| **C6** | Security alpha | bandit no CI (já parcial), secrets scan, forbidden-names no gate |
| **C7** | Public tree refresh | Regenerar sibling public tree a partir de `1.5.0` |

### Gate v1.5

- [x] Lint / mypy / pytest verdes
- [x] Forbidden names 0
- [x] Nenhuma skill pública sem contrato (40/40)
- [x] CHANGELOG 1.5.0
- [x] README: “v1.5 private alpha; v3.0 future public”

### Fora de escopo v1.5

Math IR, física, química, ScientificResult renome global.

---

## 4. v2.0 — Scientific Kernel (4–6 semanas)

### Objectivo
Núcleo **independente de domínio** (§11 V3).

### Desenho proposto (evolutivo, não big-bang)

```text
src/oec/
  core/                 # NOVO (v2.0)
    identifiers.py
    assumptions.py
    validity.py
    diagnostics.py
    scientific_result.py   # ScientificResult (wrapper/adapter)
    provenance.py          # unifica execution.provenance
  execution/            # mantém pipeline skill
  kernel/               # backends numéricos (mérito SciPy/…)
  ...
```

### Work packages

| ID | Entrega | Notas |
|---|---|---|
| **K1** | `ScientificResult` Pydantic | Campos V3; **adapter** `ExecutionResult → ScientificResult` (compat) |
| **K2** | `Assumption`, `ValidityDomain`, `MethodRef`, `BackendRef` | Tipos partilhados |
| **K3** | `Diagnostic` tipado | Substituir dicts soltos onde possível |
| **K4** | Provenance unificada | Já há hash/backends; formalizar schema JSON |
| **K5** | Erros tipados alargados | Domínio, dimensional, backend, subdeterminação |
| **K6** | Testes de núcleo | Sem imports de `electrical`/`finance` no core |
| **K7** | ADR 0019 Scientific Kernel | Decisão de compat com ExecutionResult |

### Gate v2.0

- Core **não** importa skills de domínio
- Toda execução expõe ScientificResult (directo ou via adapter)
- Documentação de conceitos V3 secção Kernel

### Risco

Reescrever `ExecutionResult` quebra clientes. **Mitigação:** adapter additivo; deprecar campos só em v3.0.

---

## 5. v2.1 — Quantities, units, contracts (3–4 semanas)

### Objectivo
Consolidar o que **já existe** em `kernel/units` para o desenho V3 §12.

### Work packages

| ID | Entrega |
|---|---|
| **Q1** | API estável `Quantity` / dimensions / convert |
| **Q2** | Validação dimensional obrigatória onde skill declara unidades |
| **Q3** | Constantes SI seleccionadas |
| **Q4** | Hooks de incerteza em Quantity (mesmo se estimador ainda simples) |
| **Q5** | Rejeição explícita de ops dimensionalmente inválidas (property tests) |
| **Q6** | Skills eléctricas: audit 100% unidades em I/O |

### Gate v2.1

- Property tests de conversão
- Zero bare float em skills físicas sem unidade (gate lint/doc)

---

## 6. v2.2 — Math IR e modelagem (6–10 semanas) — **crítico**

### Objectivo
Representar problemas **sem** dependência de solver (§13).

### Fases internas

#### 6.1 Math IR v0 (MVP)

Escopo **mínimo útil** (não o IR completo de uma vez):

- symbols, constants, expressions (estender AST actual)
- equations / inequalities
- systems (algébricos)
- objectives + constraints lineares (ligar a OPS)
- units on symbols
- assumptions

**Não no MVP IR:** PDE, eventos híbridos, stochastic full, tensor calculus.

#### 6.2 Pipeline

```text
Problem (skill input | MathProblem doc)
  → Math IR
  → structural validation
  → problem class (lp, nlp, root, ode, …)
  → method selection (declared, not silent)
  → compile to backend (HiGHS, SciPy, …)
  → execute
  → verify
  → ScientificResult
```

#### 6.3 Modeling package

```text
src/oec/modeling/
  problem.py, system.py, state.py, constraint.py,
  objective.py, scenario.py, composition.py
```

#### 6.4 Work packages

| ID | Entrega |
|---|---|
| **M1** | Spec Math IR JSON Schema v0 |
| **M2** | Pydantic models + validate |
| **M3** | Compile IR → `optimization.lp` / SciPy root / ODE |
| **M4** | Classificador de problema (regras + testes) |
| **M5** | Skill `mathematics.solve_ir` experimental |
| **M6** | Migração piloto: 2 skills math → IR path opcional |
| **M7** | ADR 0020 Math IR |

### Gate v2.2

- 1 problema LP e 1 root resolvidos **só** via IR → backend
- Schema versionado
- Sem Python arbitrário no IR

---

## 7. v2.3 — Matemática aplicada (8–12 semanas, fatiada)

Expandir catálogo **sobre** kernel + IR parcial. Prioridade por reutilização multi-consumidor:

### Wave A (base engenharia)

| Pacote | Skills / módulos |
|---|---|
| Linear | eig full API skill, least squares, residual norms, condition (parcial já) |
| Stats | regression, intervals, bootstrap |
| TS | lag/window features, simple forecast (naive/seasonal), backtest hook |
| Opt | dual/gap reporting enrichment, infeasibility explain |

### Wave B

| Pacote | Conteúdo |
|---|---|
| Uncertainty | LHS, Morris/Sobol leves, propagation wrappers |
| Dynamics | state-space simulate, stability margins básicos |
| Control | PID discrete, Kalman filter linear v0 |

### Wave C (só se Wave A/B verdes)

Multiobjetivo Pareto v0, CVaR linear, robust LP v0.

### Gate parcial v2.3

- ≥ 15 skills math/applied novas ou major bumps
- Cada skill: schema, golden, references, backend declarado

---

## 8. v2.4 — Computational math + Verification Engine (6–8 semanas)

### Computational

| Módulo V3 | Acção |
|---|---|
| root/interp/diff/int/ode | Unificar sob `kernel/computational` (refactor) |
| DAE v0 | 1 skill experimental se SciPy/algo estável |
| sparse | scipy.sparse path opcional |
| symbolic | SymPy skill wrappers controlados |
| autodiff | JAX **optional extra** (não core obrigatório cedo) |

### Verification Engine

| Fase | Checks |
|---|---|
| Pré | symbols, units, domain, contradictory constraints, missing data, backend fit |
| Pós | convergence, residuals, violations, gap, conditioning, reproducibility |

### Backend Registry

```text
src/oec/backends/
  registry.py, capabilities.py, selection.py, fallback.py, adapters/
```

### Gate v2.4

- Verification report estruturado em toda execução
- Registry lista numpy/scipy/highs (+ opcionais) com capabilities
- Fallback documentado (ex. HiGHS ausente → INVALID claro)

---

## 9. v2.5 — Mathematics Complete (gate duro, 4–6 semanas de consolidação)

### Significado (do V3)

Não “toda a matemática”. Significa **infraestrutura madura** para representar, executar, validar e compor métodos de engenharia.

### Checklist obrigatória V3 §16

| Item | Critério |
|---|---|
| Kernel + units + IR + modeling | Estáveis |
| Applied + computational + verification | Operacionais |
| Backend registry | Operacional |
| SDK/CLI/API/MCP | Mantidos |
| Golden set | **≥ 130** casos canónicos (distribuição V3) |
| Cobertura | global ≥ 85%, crítica ≥ 90% |
| Docs API pública | 100% |
| Zero regras de negócio | gate forbidden + review |
| Proveniência | obrigatória |

### Programa golden set (distribuição)

| Domínio | Mínimo |
|---|---|
| Álgebra e cálculo | 20 |
| Probabilidade e estatística | 20 |
| Séries temporais | 20 |
| Otimização | 20 |
| Incerteza | 10 |
| Dinâmica | 10 |
| Controle | 10 |
| Validação e falhas | 20 |
| **Total** | **130** |

### Definição de pronto v2.5

> Representar, resolver e validar problemas matemáticos de engenharia **sem** regras de domínio e **sem** backend único hard-coded.

**STOP:** não abrir Physics Complete em escala até este gate.

---

## 10. v2.6 — Physics Complete (12–20 semanas+)

### Estratégia de fatia (não “tudo de uma vez”)

| Slice | Domínio | Skills/exemplos iniciais |
|---|---|---|
| P1 | Eléctrica avançada | power flow v0, harmónicas leves (sobre eléctrica actual) |
| P2 | Termo / calor | condução 1D, capacidade térmica |
| P3 | Mecânica partículas / 1D | cinemática, energia |
| P4 | Fluidos 0D/1D | Bernoulli + perdas |
| P5 | Materiais props | tabelas + constitutive linear |

### Objetos

Introduzir gradualmente: `PhysicalLaw`, `ConservationLaw`, `MaterialProperty`, `BoundaryCondition` — **sobre** Math IR / ScientificResult.

### Gate v2.6

- ≥ 1 skill por fatia P1–P4 com conservação/unidades/hipóteses
- Zero import of private decision engines

---

## 11. v2.7 — Multiphysics hardening (8–12 semanas)

Após ≥ 2 física estáveis:

| Entrega |
|---|
| Coupling graph |
| Weak coupling co-sim v0 |
| Sync temporal simples |
| Convergência de acoplamento |
| Validação cruzada golden |

Prioridade de acoplamentos: **eléctrico+térmico**, **solar+térmico+eléctrico**
(genéricos, sem produto comercial proprietário).

---

## 12. v2.8 — Chemistry Complete (12–20 semanas+)

Só após v2.5 e boa base de física/transporte:

| Slice | Conteúdo |
|---|---|
| C1 | Espécies, estequiometria, balanços molares |
| C2 | Equilíbrio Gibbs simplificado |
| C3 | Cinética Arrhenius batch |
| C4 | Eletroquímica Nernst / bateria genérica (não BTM) |

Gate: reações + transporte simples executáveis e verificáveis.

---

## 13. v2.9 — Integração e RC (6–10 semanas)

| Entrega |
|---|
| **Scientific IR** (Math IR + leis + espécies + propriedades) |
| **Model Registry** (schema V3 §20) |
| Fidelity tags (reduced / mid / high) |
| Deprecations + migrations guide |
| Security/performance pass |
| Docs completas por domínio |
| RC tags `2.9.0-rc.N` |

---

## 14. v3.0 — Lançamento público GitHub

### Objectivo
Primeira versão **oficial pública** unificada.

### Pré-requisitos (checklist V3 §21)

**Código**

- [ ] Histórico limpo (ou tree sibling — já ensaiado)
- [ ] Zero dados privados / nomes proibidos
- [ ] Zero private engine / commercial-score nomenclature in tree
- [ ] Licenças e deps auditadas
- [ ] Secrets zero
- [ ] APIs estáveis versionadas

**Qualidade**

- [ ] Lint/mypy limpos
- [ ] Cobertura global ≥ 85%, crítica ≥ 90%
- [ ] Golden set 100%
- [ ] Benchmarks publicados
- [ ] Docs públicas completas

**Estrutura**

Alinhar ao layout V3 (`GOVERNANCE.md`, `schemas/`, etc.).

### Definição de pronto v3.0

> Pessoa externa instala, compreende, executa, valida e contribui **sem** conhecimento interno da equipa.

### Publicação

1. Refresh `prepare_public_alpha` / `prepare_public_v3`
2. Review humano
3. Remote público + tag `v3.0.0`
4. **Nunca** push da incubação com história suja se contiver vazamentos

---

## 15. Programa de PRs / sprints (horizonte 12 meses)

Estimativa **orientativa** (equipa pequena, 1–2 devs):

| Trimestre | Foco | Saída |
|---|---|---|
| **T0 (agora–1 mês)** | v1.5 closeout | tag `1.5.0` |
| **T1** | v2.0 Kernel + v2.1 quantities | `2.0`, `2.1` |
| **T2** | v2.2 Math IR MVP + compile paths | `2.2` |
| **T3** | v2.3 Wave A + v2.4 verification/backends | `2.3-a`, `2.4` |
| **T4** | v2.3 Wave B + golden set ramp | progresso v2.5 |
| **T5–T6** | fecho v2.5 | **`2.5.0` Mathematics Complete** |
| **Ano 2** | v2.6–v2.8 física/química fatiadas | releases 2.6+ |
| **Ano 2–3** | v2.9 + v3.0 | **GitHub public** |

Ajustar se a equipa crescer; **não** comprimir física+química no mesmo trimestre que Math IR.

---

## 16. Work packages priorizados **agora** (backlog ordenado)

### P0 — esta sprint / mês

1. **v1.5 compliance matrix** (doc + script audit skills)
2. **Version `1.5.0`** + CHANGELOG
3. **ADR 0019** rascunho ScientificResult adapter
4. **Backend capability table** (doc → código v2.4)
5. **Expand golden inventory** toward 130 (partial target 40 to 70)

### P1 — próximo

6. Pacote `oec.core` + ScientificResult
7. Math IR schema v0 + skill `mathematics.solve_ir`
8. Verification pré/pós report unificado
9. Agents: contrato “só ExecutionResult/ScientificResult” nos testes de métricas

### P2 — depois v2.2

10. Applied math waves
11. Control/dynamics v0
12. Uncertainty suite

### P3 — pós v2.5

13. Physics slices
14. Multiphysics
15. Chemistry
16. v3.0 publish

---

## 17. Gates de qualidade (transversais)

Aplicar em **toda** release minor:

| Gate | Critério |
|---|---|
| Lint | ruff clean |
| Types | mypy clean (core strict) |
| Tests | pytest verde |
| Forbidden names | 0 hits |
| Circular deps | 0 (camadas core ← domain) |
| Business rules | 0 no OEC |
| Provenance | presente em execuções |
| Skill contract | schema + method + tests |
| Coverage | subir até metas v2.5 |

---

## 18. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Escopo v2.3–v2.8 vira “reescrever SciPy” | Orquestrar backends; proibir reimplementar LAPACK |
| Math IR monstro | MVP IR estreito; expandir por classes de problema |
| Quebra de ExecutionResult | Adapter ScientificResult; compat até v3 |
| Física cedo demais | Gate duro v2.5 |
| Vazamento proprietário | ADR 0008 + forbidden-names + classificação §23 |
| Agentes inventam números | Métricas `benchmarks/agent_metrics.py` + regra ExecutionResult |
| Pressão por v3.0 prematuro | v3.0 só com Math+Physics+Chem **ou** redefinir v3.0 como “Math Complete public” se negócio exigir — **decisão explícita** |

### Decisão estratégica a tomar cedo

O roadmap V3 define v3.0 como **Math+Physics+Chem unificados**. Isso é **anos** de trabalho.

**Opção A (fiel ao texto V3):** v3.0 só após 2.8–2.9.
**Opção B (go-to-market):** publicar **v2.5** como primeiro GitHub “Mathematics Platform” e reservar v3.0 para unified science.
**Opção C:** v3.0 = “public launch da plataforma skill-based actual + kernel v2.x parcial” com roadmap physics/chem como 3.x.

Este plano assume **Opção A** no papel; recomenda **Opção B** se o marco “público no GitHub” for urgente.

---

## 19. Classificação de componentes (§23)

Para cada PR futuro:

> Este componente faria sentido se a empresa e os motores proprietários
> deixassem de existir?

| Sim → OEC | Não → motor privado |
|---|---|
| LP genérico, ODE, unidades, IR | Commercial score, pricing, funding |
| Power flow genérico | Despacho comercial BTM |
| Bateria coulomb genérica | Política de produto proprietária |

---

## 20. Métricas de progresso

| KPI | v1.5 | v2.5 | v3.0 |
|---|---|---|---|
| Skills públicas | ~40 | ≥ 80 math-focused | ≥ 120 cross-domain |
| Golden cases | ~40–70 | ≥ 130 | ≥ 200 |
| Domínios maduros | electrical + math + opt + ts | mathematics complete | + physics + chemistry |
| IR | OPS only | Math IR v0+ | Scientific IR |
| Public GitHub | tree local | optional pre-release | **official** |

---

## 21. Primeiros 10 PRs concretos (ordem)

| # | PR | Versão |
|---|---|---|
| 1 | `docs: v1.5 compliance matrix vs V3 roadmap` | 1.5 |
| 2 | `chore: release 1.5.0 alpha private` | 1.5 |
| 3 | `feat(core): ScientificResult + adapter from ExecutionResult` | 2.0 |
| 4 | `feat(core): Assumption, MethodRef, BackendRef models` | 2.0 |
| 5 | `test: core independence from domain skills` | 2.0 |
| 6 | `feat(math-ir): JSON schema + pydantic MathProblem v0` | 2.2 |
| 7 | `feat(math-ir): compile linear subset → optimization.lp` | 2.2 |
| 8 | `feat(verification): pre/post VerificationReport on execute` | 2.4 |
| 9 | `feat(backends): registry + highs/scipy capabilities` | 2.4 |
| 10 | `test(golden): expand optimization + failure cases toward 130` | 2.5 ramp |

---

## 22. Relação com planos anteriores

| Plano | Papel |
|---|---|
| Plano GPT S0′–S26 / Phases A–G | **Entregue** no essencial; alimentou o catálogo actual |
| V3 roadmap (este documento fonte) | **Norte de produto** até GitHub public |
| Este plano de implementação | **Tradução executável** baseline → v3.0 |

Não descartar o que já existe: **reclassificar** como v1.5 e **empilhar** v2.x em cima.

---

## 23. Conclusão

1. Hoje o OEC já é um **alpha privado forte** (v1.x no mapa V3), não um protótipo vazio.
2. O salto de valor seguinte é **formalização científica** (Kernel + Math IR + Verification), não mais skills avulsas sem IR.
3. **v2.5** é o primeiro “complete” real e deve ser um **gate de produto**.
4. Física/química são **programas seguintes**, não sprints paralelos descontrolados.
5. **v3.0 público** exige limpeza total + maturidade multi-domínio **ou** uma decisão explícita de publicar mais cedo (v2.5 public).

**Próximo passo recomendado:** executar **Fase v1.5 Closeout** (PRs 1–2) e em paralelo rascunhar **ADR ScientificResult + Math IR v0** (PRs 3–7).

---

*Fim do plano de implementação OEC V3 — 2026-07-26*
