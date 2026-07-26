# OEC — Plano de implementação (análise + execução)

**Status:** plano de execução revisado (pós-análise)
**Data:** 2026-07-25
**Fonte analisada:** proposta “Plano de Construção por Etapas e Sprints”
**Baseline real:** repositório de incubação OEC (12 skills, interfaces SDK/CLI/REST/MCP)

---

## 0. Resumo executivo

A proposta está **alinhada com o ouro do produto**:

> Agentes especialistas formulam → OEC valida e executa → backends (SciPy/HiGHS/…) calculam.
> Motores privados decidem o *quê* e o *porquê*; o OEC público só o *como calcular* de forma genérica e auditável.

### Veredito

| Aspecto | Avaliação |
|---|---|
| Visão (agentes + governança + separação público/privado) | **Excelente — manter** |
| Separação “OEC calcula / motores privados decidem” | **Excelente — manter** |
| Critérios de pronto de skill | **Fortes — adotar com ajustes** |
| Primeiro release até Optimization Specialist + Reviewer | **Correto — âncora** |
| Sprints 0–2 vs estado real do repo | **Desatualizados — reescrever** |
| Sprints 10–26 | **Roadmap válido, não compromisso do Alpha** |
| Reestruturação monorepo (`backends/`, `agents/` no core) | **Adiar — evoluir in-place** |
| Contrato `status: success` | **Rejeitar — conflita com ADR 0007** |

**Recomendação:** executar **Fase Alpha (S0′–S9′)** como um único programa fechado; só então abrir séries temporais / energia / finanças.

---

## 1. Análise da proposta

### 1.1 O que está certo (não negociar)

1. **OEC sem especialistas ≈ SciPy governado (enxuto).** O valor de mercado está na pilha *agente + contrato + execução*.
2. **Regra de separação** público/privado (sem metodologias, dados, scores ou despacho proprietários no OEC).
3. **Backend ≠ contrato.** Skills e OPS são a API; SciPy/HiGHS são detalhes de implementação.
4. **OPS (OEC Problem Specification)** como língua estruturada entre LLM e solvers.
5. **LP/MILP + diagnóstico de factibilidade** antes de explodir o catálogo de domínio.
6. **Optimization Specialist + Scientific Reviewer** como primeiros agentes.
7. **Parar no “Sprint 9”** antes de alargar domínio (energia, FV, finanças, CasADi…).
8. **Mérito numérico dos backends** (SciPy, HiGHS, …); OEC contribui governança e metodologia de uso.

### 1.2 O que está errado ou arriscado

#### A) O plano subestima o que já existe

Auditoria rápida do repo (2026-07-25):

| Capacidade no plano (S1–S2) | Estado real |
|---|---|
| Skill Engine / Registry / lifecycle | **Existe** |
| Schemas input/output por skill | **Existe** |
| ExecutionResult estruturado | **Existe** (campos abaixo) |
| Status graduado (não bool success) | **Existe** — ADR 0007 |
| Unidades (Pint) + normalização central | **Existe** — ADR 0011/0016 |
| Proveniência (`run_id`, sandbox meta, oec_version, git) | **Existe** (parcial: sem `input_hash` formal) |
| Timeout + subprocess sandbox | **Existe** — ADR 0012 (limites de memória OS: **não**) |
| API / CLI / MCP finos sobre o mesmo Engine | **Existe** — ADR 0005/0015 |
| 6 math + 6 electrical skills | **Existem** (várias ainda uncommitted no working tree) |
| Testes (~696) + coverage ~96% | **Existem** |
| Graphify, ADRs, prep Public Alpha | **Existem** |
| HiGHS / pandas / adapters de backend plugáveis | **Não** |
| OPS | **Não** |
| Camada de agentes no repo | **Não** (só integração Odysseus/MCP host) |

**IDs reais das skills:** `mathematics.*` e `electrical.*` (não `math.*`).

**ExecutionResult real (não reescrever para `success`):**

```text
run_id, status, skill, method, inputs, normalized_inputs, result,
assumptions, conventions, diagnostics, validation, warnings,
provenance, started_at, completed_at, duration_ms

status ∈ {
  VERIFIED, VALIDATED, CONVERGED_WITH_WARNINGS, APPROXIMATE,
  INCONCLUSIVE, INVALID, FAILED
}
```

Refazer S1 como se o contrato não existisse **quebraria** clientes e ADRs.

#### B) Sprints 0–2 como “construção do zero” são desperdício

Devem virar **auditoria + gaps + hardening**, não reimplementação.

#### C) Escopo S10–S26 é um segundo produto

Séries temporais, energia, FV, finanças, risco, CasADi, MPC — coerentes com a visão de longo prazo, mas **não** com o primeiro release forte. Tratar como **Roadmap B** após métricas do Alpha.

#### D) “Trocar backend sem mudar contrato” (S3) é prematuro como meta universal

Para Alpha:

- **SciPy/NumPy/Pint** = backends de fato das skills numéricas atuais.
- **HiGHS** = backend **novo** só para LP/MILP.
- Adapter plugável genérico (trocar SciPy por outro sem mudar skill) = **dívida aceitável pós-Alpha**, exceto onde o contrato da skill já expõe `method.id`.

#### E) Agentes dentro de `src/oec` acoplam o core

Agentes devem viver em:

```text
agents/          # specs, prompts, tools, testes de contrato OPS
```

ou pacote opcional `oec-agents`, **sem** dependência obrigatória no wheel `oec`.
O core expõe skills + OPS + MCP; o especialista é **cliente**.

#### F) Risco de propriedade intelectual no texto do plano

A proposta nomeia sistemas privados como *fronteira do que não entra*.
No **código e docs públicos** do OEC: manter a regra ADR 0008 — descrever só a separação genérica (“private decision engines”), sem codinomes, em artefatos que vão para o tree público.

#### G) Critério de pronto de skill é ambicioso demais para cada skill MVP

Manter o espírito; no Alpha, **mínimo obrigatório**:

- schemas in/out
- validação de domínio
- testes golden + unitários da skill
- skill.md + references
- execução via Engine (cobre CLI/SDK; API/MCP por conformidade ADR 0005 em amostra)
- method/backend documentados
- deterministic quando aplicável

Exemplos *dedicados* API/CLI/MCP **por skill** → checklist do release, não bloqueio de merge de cada skill.

### 1.3 Tese de produto (congelar)

```text
SciPy / HiGHS / …     →  mérite numérico (motor)
OEC skills + OPS      →  governança e execução científica
Agentes especialistas →  ouro de UX: decompor, propor método, pedir dados, orquestrar
Motores privados      →  o que/por que/encadear/decidir (fora do OEC)
```

Sem agentes, o OEC é **infra**. Com agentes, vira **infraestrutura de computação científica orientada a agentes**.

---

## 2. Estado atual — inventário oficial (parcial; S0′ completa)

### 2.1 Skills (IDs reais)

| ID | Versão | Método | Iterativo |
|---|---|---|---|
| `mathematics.solve_root` | 0.1.0 | `scalar_root_finding` | sim |
| `mathematics.interpolate` | 0.1.0 | `scalar_interpolation` | não |
| `mathematics.integrate` | 0.1.0 | `scalar_integration` | sim* |
| `mathematics.optimize_scalar` | 0.1.0 | `scalar_minimization` | sim |
| `mathematics.optimize_constrained` | 0.1.0 | `constrained_minimization` | sim |
| `mathematics.curve_fit` | 0.1.0 | `nonlinear_least_squares` | sim |
| `electrical.three_phase_power` | 0.1.0 | `balanced_three_phase_power` | não |
| `electrical.current_from_power` | 0.1.0 | `current_from_power` | não |
| `electrical.voltage_drop` | 0.1.0 | `conductor_voltage_drop` | não |
| `electrical.power_factor_correction` | 0.1.0 | `capacitor_bank_sizing` | não |
| `electrical.transformer_loading` | 0.1.0 | `apparent_power_loading` | não |
| `electrical.per_unit_conversion` | 0.1.0 | `classical_per_unit` | não |

\*function mode adaptativo; tabulated mode exato.

### 2.2 Interfaces

- SDK: `oec.sdk.Engine` / `run`
- CLI: `oec skills|run|server`
- REST: `/v1/...`
- MCP: uma tool por skill + `list_skills`

### 2.3 Backends instalados (core)

- NumPy, SciPy, SymPy, Pint — **sim**
- pandas, HiGHS — **não** (Alpha LP/MILP deve adicionar HiGHS; pandas só se timeseries entrar)

### 2.4 Débitos relevantes para o plano

- Working tree com skills elétricas / integrações **ainda não commitadas** (risco de baseline suja).
- `assumptions` / `conventions` frequentemente `[]` no result (docs na skill, não no result).
- Proveniência sem `input_hash` / `backend_version` estável por skill.
- Sandbox: timeout sim; isolamento real de rede/FS/memória **não** (documentado).
- Telemetria de dev (plano antigo §19) ausente.
- Lifecycle transitions não aplicadas em runtime de forma sistemática.

---

## 3. Arquitetura-alvo (ajustada)

```text
┌─────────────────────────────────────────────────────────┐
│  LLMs · apps · motores de decisão (privados, fora)      │
└────────────────────────────┬────────────────────────────┘
                             │  OPS + skill calls (MCP/REST/SDK)
┌────────────────────────────▼────────────────────────────┐
│  agents/  (opcional, não no core wheel)                 │
│  optimization-specialist · scientific-reviewer · …    │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│  OEC Core (src/oec)                                     │
│  registry · execution · validation · units · OPS        │
│  skills/*  (mathematics, optimization, electrical, …) │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│  Backends (deps + thin wrappers em kernel/)             │
│  NumPy · SciPy · SymPy · Pint · HiGHS (+ futuros)       │
└─────────────────────────────────────────────────────────┘
```

**Não** migrar agora para a árvore monorepo total da proposta (`backends/` top-level, `interfaces/` renomeado). Evoluir:

- `src/oec/kernel/` = adapters de backend
- `skills/` = catálogo
- `agents/` = novo, no root, opcional
- `contracts/` = schemas OPS em `schemas/ops/` ou `src/oec/ops/`

---

## 4. Critérios de pronto (Alpha)

### 4.1 Skill

Obrigatório:

1. `skill.yaml` + `skill.md` + references
2. `input.schema.json` / `output.schema.json`
3. `implementation.py` + `validation.py`
4. Unidades (`x-oec-unit`) se físico
5. Golden tests + testes de validação
6. Method id/versão; backend citado (SciPy/HiGHS/…)
7. Status OEC coerente (ADR 0007)
8. Sem código arbitrário do usuário (`eval`/`exec` proibidos)

Desejável no Alpha, obrigatório no release notes:

- exemplo CLI documentado
- cobertura no teste ADR 0005 (amostra de skills)
- `input_hash` na proveniência

### 4.2 Agente especialista

1. Escopo e recusas explícitas
2. Taxonomia de problemas
3. Checklist de dados
4. Mapa → OPS e/ou skills
5. **Nunca** inventa números: só interpreta `ExecutionResult`
6. Testes: problema NL → OPS válido → execução → reviewer

---

## 5. Plano de implementação revisado

### 5.1 Programa Alpha — “OEC Agent-Ready Optimization”
**Meta:** infraestrutura pública usável por agentes para **otimização estruturada + review**, sem domínio proprietário.

**Duração sugerida:** 8–12 semanas (sprints de 2 semanas *ou* sprints comprimidos de 1 semana se a base atual for reaproveitada).

| Sprint | Nome | Objetivo | Depende de |
|---|---|---|---|
| **S0′** | Baseline & higiene | Congelar verdade do repo; commits; inventário; dívida | — |
| **S1′** | Contrato & proveniência+ | Gaps no ExecutionResult/provenance; doc de contrato; NÃO redesenhar status | S0′ |
| **S2′** | Hardening execução | input_hash; limites de payload/tamanho; política de expressão; doc sandbox | S1′ |
| **S3′** | Backend HiGHS (+ protocol mínimo) | Adapter HiGHS; versão no provenance; SciPy continua default math | S1′ |
| **S4′** | OPS v0.1 | Schema, parser, validador, exemplos LP | S1′ |
| **S5′** | `optimization.lp` | OPS → HiGHS LP E2E | S3′, S4′ |
| **S6′** | `optimization.milp` | Inteiros/binários, gap, time limit | S5′ |
| **S7′** | Factibilidade & cenários | check_feasibility, sweep básico, mensagens úteis | S5′ |
| **S8′** | Optimization Specialist v0.1 | NL → OPS → validate → run (MCP/SDK) | S4′–S7′ |
| **S9′** | Scientific Reviewer v0.1 | Auditoria independente de OPS + ExecutionResult | S8′ |

**Definition of Done do Alpha (release forte):**

- [ ] Contratos estáveis documentados (sem `status: success`)
- [ ] Unidades + normalização (já) + gaps de proveniência fechados
- [ ] SciPy/SymPy/Pint + **HiGHS**
- [ ] OPS v0.1
- [ ] LP + MILP + diagnóstico de inviabilidade
- [ ] Optimization Specialist v0.1
- [ ] Scientific Reviewer v0.1
- [ ] API, CLI, MCP verdes no gate
- [ ] Zero referências proprietárias no tree público
- [ ] README: SciPy/HiGHS = motor; OEC = governança; agentes = formulação

### 5.2 Detalhamento dos sprints Alpha

#### S0′ — Baseline & higiene (1 sprint curto)

**Tarefas**

1. Completar inventário (`docs/implementation/skill-inventory.md` — gerar a partir do registry).
2. Commitar working tree em blocos: elétricas, open_science/odysseus, docs SciPy-governança, scripts Alpha.
3. `check_forbidden_names` + grep de codinomes privados.
4. Matriz skill → backend → testes → interface.
5. Congelar branch `main` como baseline Alpha.
6. Lista de gaps S1′–S2′ (somente itens reais).

**Entregáveis:** este plano + inventário + technical-debt.md + baseline commit(s).

**Aceite:** qualquer dev responde IDs, como chamar, backends, testes, interfaces.

#### S1′ — Contrato & proveniência+ (não big-bang)

**Fazer**

- Documentar contrato oficial do `ExecutionResult` atual (não o mock `success` da proposta).
- Estender proveniência de forma **compatível**:
  - `backend`: `{ name, version }` quando aplicável
  - `input_hash` (hash canônico JSON dos inputs originais)
  - `skill_version` / `method` já cobertos por `skill`/`method`
- Preencher `assumptions`/`conventions` a partir de skill.md **só se** barato (senão issue explícita).
- Teste de regressão: 12 skills serializam e deserializam.

**Não fazer:** renomear `mathematics`→`math`; mudar enum de status; quebrar MCP.

#### S2′ — Hardening

- Limites configuráveis: tamanho de arrays, profundidade JSON, timeout já existente.
- Documentar e, se viável, reforçar política de expressões (AST whitelist já em numerics).
- Rejeitar payloads absurdos na API com 422 claro.
- Checklist segurança Alpha (sem auth — documentar; não expor rede).

#### S3′ — HiGHS

- Extra opcional: `oec[optimization]` ou dep core se LP for central ao Alpha.
- `oec.kernel.optimization.highs` (ou `backends/highs` wrapper interno).
- Provenance registra `highs` + versão.
- Testes de smoke + problemas de textbook.

#### S4′ — OPS v0.1

Schema mínimo:

```text
ops_version, problem_class (lp|milp|…),
sense (min|max),
variables[], constraints[],
objective, units/notes/assumptions[],
execution_limits (time, …)
```

- Validador JSON Schema + erros legíveis.
- **Proibição:** Python arbitrário no OPS.
- Exemplos: diet problem, knapsack pequeno, alocação contínua.

#### S5′–S6′ — LP / MILP skills

- IDs sugeridos: `optimization.lp`, `optimization.milp`
- Entrada: OPS ou subconjunto tipado
- Saída: x*, obj, status solver, dual/slack se disponível, mip_gap, runtime
- Golden sets com oráculos independentes / soluções conhecidas
- Mapear status HiGHS → `ExecutionStatus` OEC (Optimal→VERIFIED/VALIDATED; Infeasible→INVALID ou status dedicado em diagnostics)

#### S7′ — Diagnóstico

- `optimization.check_feasibility` ou modo na skill LP
- Mensagens: restrições conflitantes óbvias, bounds inverted
- `scenario_batch` v0: lista de OPS com parâmetro varrido
- Nunca retornar só “solver failed” sem `diagnostics`

#### S8′ — Optimization Specialist v0.1

Entregar como **spec + harness**, não como magia:

```text
agents/optimization_specialist/
  SKILL_OR_AGENT.md      # escopo, recusas, taxonomia
  prompts/
  tools.md               # list_skills, validate_ops, run optimization.*
  tests/test_ops_pipeline.py
```

Fluxo obrigatório:

1. Classificar LP vs MILP vs “fora de escopo”
2. Listar dados faltantes (não inventar)
3. Emitir OPS
4. Validar OPS
5. Executar skill
6. Narrar **somente** com base no ExecutionResult

Teste de aceite: problema textual fixo → OPS schema-valid → status solver esperado.

#### S9′ — Scientific Reviewer v0.1

Checklist automatizável + LLM opcional:

- unidades / sinais / bounds
- variáveis vs parâmetros
- status real vs claim
- hipóteses presentes
- residual/gap se houver
- reprodutibilidade (`run_id`, versões)

Teste: OPS propositalmente errado + result forjado → reviewer falha.

---

## 6. Roadmap B — pós-Alpha (proposta original S10–S26, reordenado)

Só iniciar com Alpha estável e métricas mínimas (OPS válido 1ª tentativa, reviewer catch rate).

| Fase | Conteúdo | Sprints originais ~ |
|---|---|---|
| **B1 Time** | timegrid, align, resample, missing, power↔energy | S10–S12 |
| **B2 Math ampla** | linear algebra, root systems, ODE, stats básicas | S13–S15 |
| **B3 Energy generic** | balanço, SOC genérico, métricas de carga (sem despacho proprietário) | S16–S18 |
| **B4 Finance/Risk generic** | primitives públicas apenas | S19 |
| **B5 Mais agentes** | Math, Time-Series, Energy specialists | S20–S22 |
| **B6 Opt avançada** | QP, NLP, multiobjetivo; CasADi/IPOPT se necessário | S23–S26 |

**Filtro de entrada em B:** cada skill deve ser reutilizável por **mais de um** consumidor sem carregar política de negócio privada.

---

## 7. Métricas (do Alpha em diante)

### Core

- gate: ruff, mypy, pytest, bandit, build
- cobertura core ≥ 90%
- taxa `INVALID` por schema vs falha interna
- % problemas inviáveis com diagnóstico estruturado

### Agentes

- % OPS válido na 1ª tentativa (golden prompts)
- % classificação LP/MILP correta
- % hipóteses explícitas no OPS
- **taxa de dados inventados = 0** em testes controlados
- % erros capturados pelo reviewer

### Separação

- `check_forbidden_names` verde
- CI grepa codinomes privados
- core instala sem `agents/`

---

## 8. Governança (adotar da proposta, com 2 emendas)

1. Backend não é contrato.
2. Toda skill precisa de validação.
3. Sem código arbitrário por padrão.
4. Toda suposição explícita.
5. Toda transformação com proveniência.
6. Nenhuma metodologia proprietária no público.
7. API/CLI/MCP são interfaces, não o produto.
8. **O agente formula; o OEC valida e executa.**
9. Reviewer independente.
10. Claims públicos = testes reais.
11. **Emenda:** SciPy/HiGHS detêm o mérito numérico; OEC não rebranda algoritmos.
12. **Emenda:** status graduado ADR 0007; proibido colapsar para bool `success` no contrato público.

---

## 9. Sequência executiva (a seguir agora)

```text
1. S0′  — inventário + commits + dívida (esta semana)
2. S1′  — proveniência+ e doc de contrato
3. S2′  — hardening payload/limites
4. S3′  — HiGHS
5. S4′  — OPS v0.1
6. S5′  — optimization.lp
7. S6′  — optimization.milp
8. S7′  — feasibility/sensitivity v0
9. S8′  — Optimization Specialist v0.1
10. S9′ — Scientific Reviewer v0.1
11. STOP — release notes Alpha / prep public tree
12. Só então Roadmap B
```

---

## 10. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Reescrever ExecutionResult e quebrar tudo | S1′ só additive |
| Alpha virar “mais um SciPy wrapper” sem agentes | S8′/S9′ inegociáveis no DoD |
| Agentes inventarem números | testes + regra dura: só ExecutionResult |
| Vazamento de metodologia privada | ADR 0008 + gate CI + review humano |
| Escopo S10+ engolir o Alpha | freeze de domínio até S9′ done |
| HiGHS packaging no Windows | smoke no S3′ cedo; fallback documentado |

---

## 11. Conclusão

A proposta original é o **mapa de produto certo** (agentes + OPS + otimização + separação).
O plano de implementação **corrigido** reconhece que o OEC **já não está no Sprint 0 de fundação vazia**: está num **Alpha de skills + interfaces**, e o próximo salto de valor é:

> **OPS + HiGHS (LP/MILP) + Optimization Specialist + Scientific Reviewer**

Isso transforma o OEC de “SciPy nerfado com schemas” em **infraestrutura de computação científica orientada a agentes**, utilizável por motores privados **sem** incorporar IP privada — exatamente o objetivo declarado.
