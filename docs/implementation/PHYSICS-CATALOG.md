# OEC — Catálogo de Áreas de Física (Roadmap de Domínio)

> Documento mestre de planejamento funcional físico do OEC. Lista as áreas de
> física que o projeto pode vir a cobrir, com estado em **três níveis**
> (primitive/kernel · skill · API `oec.physics`), fatia de roadmap (P1–P5 do
> V3 §10, quando aplicável) e precedência sugerida. Usar como base para decidir
> o escopo de cada release (v2.6, v2.6.1, v2.7+).
>
> **Planos de execução (fonte operacional):**
> - [v2.6-EXECUTION-PLAN.md](v2.6-EXECUTION-PLAN.md) — **Physics Foundation P1–P5 v0** / Engineering Physics Foundation (plataforma + P1–P5)
> - [v2.6.1-EXECUTION-PLAN.md](v2.6.1-EXECUTION-PLAN.md) — Energy-rich **feature release** (storage/PV/hybrid/grid-zero/service_metrics)
> - Fonte de verdade de escopo de produto: [OEC_V3_IMPLEMENTATION_PLAN.md](OEC_V3_IMPLEMENTATION_PLAN.md) §10–§11
> - Auditoria de planos: [v26-CODEX-DEPENDENT-AUDIT.md](v26-CODEX-DEPENDENT-AUDIT.md)

### Legenda de estado — **3 colunas** (não usar status único ambíguo)

| Coluna | Significado |
|--------|-------------|
| **Kernel / primitive** | Função ou tipo em `src/oec/kernel/*`, `oec.core`, ou primitiva numérica existente |
| **Skill** | Skill versionada em `skills/**` (contrato público skill-first) |
| **API `oec.physics`** | Superfície em `src/oec/physics/` (plataforma multi-domínio) |

Valores típicos por célula:

- `✔ no repo` — implementado e usável
- `plano v2.6` — compromisso do release **2.6.0** (Physics Foundation P1–P5 v0)
- `plano v2.6.1` — compromisso do release **2.6.1** (energy-rich feature)
- `futuro` — roadmap posterior (v2.7+ / não escalonado nesta geração de planos)
- `—` — não aplicável neste nível

> **Marco de produto (honestidade de claim):** o V3 §10 chama o marco de
> roadmap **“Physics Complete”**. O claim de entrega de **v2.6.0** é
> **Physics Foundation P1–P5 v0** (também: **Engineering Physics Foundation**).
> Não alegar “Physics Complete” industrial enquanto o gate cobre foundation v0
> (sem óptica/acústica/campos/quântica, sem solvers estruturais, etc.).

---

## 1. Elétrica e Eletromagnetismo

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Elétrica clássica (DC/AC básico) | current_from_power, three_phase_power, voltage_drop, power_factor_correction, transformer_loading, per_unit_conversion | — / helpers pontuais | ✔ no repo — `electrical.*` ×6 (zero rewrite em v2.6) | plano v2.6 — façade documentada (opcional) | base pré-2.6 |
| Elétrica de rede / power flow v0 | **DC linear power flow meshed** (`dc_power_flow`); B-matrix; residual KCL | — | plano v2.6 — `electrical.dc_power_flow` | plano v2.6 — `electrical` / `electrical_network` | **P1** (canónico) |
| Harmônicas leves | THD, filtros passivos v0 | — | plano v2.6 **opcional** — `electrical.harmonics_thd` | plano v2.6 **opcional** — `harmonics` | **P1** (não bloqueia release) |
| Eletrostática | campo, potencial, capacitância, dipolos | — | futuro | futuro | — |
| Eletrodinâmica clássica | correntes, indução, indutância, Maxwell em regime | — | futuro | futuro | — |
| Circuitos AC avançados | fasores, impedância complexa, ressonância, RLC | — | futuro | futuro | — |
| AC power flow completo / máquinas / sequências | OPF, máquinas rotativas, sequências simétricas | — | futuro (pós-P1 v0) | futuro | — |
| Radial branch-flow | branch-flow radial simplificado | — | futuro (extensão; **não** canónico P1) | futuro | — |

## 2. Energia e Sistemas de Energia

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Energia genérica (primitiva) | `energy_balance`, `soc_update` (**energy-based**, não coulomb), `load_metrics`, power_to_energy | ✔ no repo — `kernel/energy/metrics.py` | ✔ no repo — `energy.balance` / `energy.load_metrics` / `battery.soc_step` (**não migrados** em 2.6.1; parity posterior) | ✔ no repo — reuso via `conservation` (owner); wrap storage 2.6.1 | base pré-2.6 |
| Armazenamento / BESS rico | trajectory multi-step, **energy-based SOC**, η_c/η_d, clip | wrap de `soc_update` | ✔ no repo — `battery.soc_trajectory` (nova); legada `soc_step` intacta | ✔ no repo — `storage` (`energy_based_soc_update`, `storage_trajectory`) | energy-rich **2.6.1** |
| Fotovoltaico (FV) genérico | irradiância × área × eficiência, série PV | — | ✔ no repo — `energy.pv_power` | ✔ no repo — `pv` (`pv_power`, `pv_energy_from_series`) | energy-rich **2.6.1** |
| Híbrido multiperíodo | LOAD = PV + grid + discharge − charge | — | ✔ no repo — `energy.hybrid_balance` | ✔ no repo — `hybrid` (`hybrid_balance`, `hybrid_period_residual`) | energy-rich **2.6.1** |
| Grid-zero feasibility | avaliação **determinística** de trajectória fornecida (deficit / factível); **≠** sizing | — | ✔ no repo — `energy.grid_zero_feasibility` | ✔ no repo — `grid_zero` (feasibility only; no solver) | energy-rich **2.6.1** |
| Min storage capacity | sizing óptimo (horizonte, curtailment, η) | compõe kernel optimization | ✔ no repo — `energy.min_storage_capacity` → **`optimization.lp`** | **não** em physics (composição LP; physics só feasibility) | energy-rich / optimização **2.6.1** |
| Métricas de serviço de energia (EaaS) | energy delivered, autonomy hours (sem score comercial) | — | ✔ no repo — `energy.service_metrics` | ✔ no repo — `service_metrics` (`energy_delivered`, `autonomy_hours`) | energy-rich **2.6.1** |
| Coulomb-counting (corrente/Ah) | ∫I dt / Q | futuro (se input de corrente) | futuro | futuro | — |
| TOU / despacho econômico | curvas de tarifa, dispatch horário | — | futuro / `optimization.lp` | — | — |
| Termossolar / CSP | concentração, ciclo térmico (acopla com P2) | — | futuro | futuro | P2+ / v2.7 |

## 3. Objetos de domínio (transversais — V3 §10)

| Objeto | Uso | Kernel / primitive | Skill | API `oec.physics` |
|--------|-----|--------------------|-------|-------------------|
| `PhysicalLaw` | declaração de lei + **execução** (não só serialização) em ≥2 fatias | reuso `Assumption` / core | — (consumido por skills) | plano v2.6 (plataforma) |
| `ConservationLaw` | balanços de conservação; residual via owner `conservation` | `kernel.energy.energy_balance` = **adapter/consumidor** | — | plano v2.6 — **owner** `conservation` |
| `MaterialProperty` | propriedades com valores/unidades/tabela | — | plano v2.6 — materials skills | plano v2.6 (plataforma + P5) |
| `BoundaryCondition` | contorno auditável (tipo, valor, unidade, entidade) | — | — | plano v2.6 (plataforma) |

> Estes objectos vivem em `src/oec/physics/` **sobre** Math IR / ScientificResult
> (ADR 0020 / 0019). `oec.modeling` permanece domain-agnostic.
> Critério de gate: objectos **não decorativos** — ≥2 fatias executam a partir
> de `PhysicalLaw`/`ConservationLaw` (ver v2.6 GATE-W1/W3).

## 4. Termodinâmica e Calor

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Condução 1D | lei de Fourier, condução em placa/haste | — | plano v2.6 — `thermal.conduction_1d` | plano v2.6 — `thermal` | **P2** |
| Capacidade térmica | calor específico, capacidade, mudança de fase v0 limitada | — | plano v2.6 (pode partilhar skill P2) | plano v2.6 — `thermal` | **P2** |
| Convecção | coeficiente convectivo, trocadores v0 | — | futuro | futuro | — |
| Radiação térmica | Stefan-Boltzmann, corpos cinza | — | futuro | futuro | — |
| Termodinâmica clássica | 1ª/2ª lei, ciclos (Carnot, Rankine), entropia | — | futuro | futuro | — |
| Termofísica de componentes | juntas, isolamento, perfis térmicos transientes | — | futuro | futuro | — |

## 5. Mecânica

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Cinemática | posição, velocidade, aceleração (1D), MRU/MRUV | — | plano v2.6 — `mechanics.kinematics_1d` (ou energy) | plano v2.6 — `mechanics` | **P3** |
| Energia mecânica | cinética, potencial gravitacional, trabalho | — | plano v2.6 | plano v2.6 — `mechanics` | **P3** |
| Dinâmica de partículas | leis de Newton 1D, momento, impulso | — | plano v2.6 (v0 se couber; senão pós-patch) | plano v2.6 (v0 se couber) | **P3** |
| Estática / estruturas | equilíbrio, reações, vigas, momento fletor | — | futuro | futuro | — |
| Mecânica do corpo rígido | rotação, torque, momento de inércia | — | futuro | futuro | — |
| Vibrações 1D | oscilador harmônico, amortecimento, ressonância | — | futuro | futuro | — |
| **Lei material uniaxial v0** | Hooke uniaxial, módulo de Young, tensão/deformação **1D** (constitutivo) | — | plano v2.6 — `materials.linear_constitutive` | plano v2.6 — `materials` | **P5** (não P3) |
| **Solver estrutural / elástico** | análise de estruturas, MEF, multi-axial, contorno estrutural completo | — | futuro | futuro | **≠ P5** |

> **Elasticidade — dupla marcação corrigida:** P5 entrega apenas a **lei material
> uniaxial / property** (constitutivo linear). Qualquer **solver estrutural ou
> elástico** (estática de estruturas, campos multi-axiais) é **futuro**, não
> claim de v2.6.

## 6. Mecânica dos Fluidos

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Fluidos ideais 0D/1D | Bernoulli, vazão, continuidade | — | plano v2.6 — `fluids.bernoulli` | plano v2.6 — `fluids` | **P4** |
| Perdas de carga v0 | perdas por atrito (Darcy-Weisbach) com **fator de atrito `f` como INPUT conhecido**; perdas localizadas v0 | — | plano v2.6 (mesma skill ou satélite) | plano v2.6 — `fluids` | **P4** |
| Hidrostática | pressão, empuxo, princípio de Pascal | — | futuro | futuro | — |
| Regime / Reynolds / Colebrook | laminar/turbulento, Re, rugosidade → f | — | futuro | futuro (extensão **após** P4 v0) | — |
| Escoamento em tubulações (sistema) | bomba/curva do sistema, rede multi-ramo | — | futuro | futuro | — |
| Aerodinâmica básica | arrasto, sustentação v0 | — | futuro | futuro | — |

> **P4 v0:** **não** alegar “resolver regime de escoamento”. `f` entra como
> input; Reynolds/Colebrook são extensão posterior.

## 7. Ciência dos Materiais

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Tabelas de propriedades | densidade, condutividade, resistividade, módulos | — | plano v2.6 — `materials.property_lookup` | plano v2.6 — `materials` | **P5** |
| Constitutivos lineares uniaxiais | relação tensão-deformação linear 1D (Hooke) | — | plano v2.6 — `materials.linear_constitutive` | plano v2.6 — `materials` | **P5** |

## 8. Óptica

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Óptica geométrica | reflexão, refração (Snell), lentes finas, espelhos | — | futuro | futuro | — |
| Óptica ondulatória | interferência, difração, fenda dupla, rede | — | futuro | futuro | — |

## 9. Acústica

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Ondas sonoras 1D | velocidade do som, intensidade, dB | — | futuro | futuro | — |
| Ressonância acústica | tubos, cordas, frequências harmônicas | — | futuro | futuro | — |

## 10. Matéria Condensada / Estado Sólido

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Estrutura cristalina | células unitárias, parâmetros de rede | — | futuro | futuro | — |
| Condutividade eletrônica | Ohm microscópico, semicondutores básicos, band gap | — | futuro | futuro | — |
| Física de dispositivos | diodo, transistor v0, junção PN (conceitual) | — | futuro | futuro | — |

## 11. Física Moderna e Quântica

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Relatividade restrita | dilatação do tempo, contração, E=mc² | — | futuro | futuro | — |
| Física quântica básica | fóton, efeito fotoelétrico, incerteza | — | futuro | futuro | — |
| Mecânica quântica 1D | poço infinito/finito, oscilador quântico | — | futuro | futuro | — |
| Física atômica | Bohr, linhas espectrais, números quânticos | — | futuro | futuro | — |
| Física nuclear | decaimento, meia-vida, fissão/fusão conceitual | — | futuro | futuro | — |

## 12. Astrofísica e Cosmologia

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Gravitação | gravitação universal, órbitas circulares v0, Kepler | — | futuro | futuro | — |
| Radiação de corpo negro | espectro, Wien, fluxo estelar | — | futuro | futuro | — |
| Cosmologia básica | desvio para o vermelho, Hubble (conceitos) | — | futuro | futuro | — |

## 13. Física de Campos e Ondas

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` | Fatia |
|------|--------------------|--------------------|-------|-------------------|-------|
| Ondas mecânicas | corda, propagação, superposição | — | futuro | futuro | — |
| Ondas eletromagnéticas | espectro EM, intensidade, pressão de radiação | — | futuro | futuro | — |

## 14. Química e transporte de espécies (pré-v2.8)

| Área | Exemplos / objetos | Kernel / primitive | Skill | API `oec.physics` / chemistry | Fatia |
|------|--------------------|--------------------|-------|-------------------------------|-------|
| Reações / estequiometria / equilíbrio | V3 chemistry | — | **DONE** `oec.chemistry` + skills | `chemistry.*` | v2.8 / 3.2.0 |
| Eletroquímica de célula genérica (C4) | ≠ BESS energy-based SOC do 2.6.1 | — | **DONE** Nernst | `chemistry.nernst` | v2.8 C4 |
| **Species transport / diffusion v0** | transporte e difusão de espécies (≠ hidráulica P4) | — | **DONE** Fick 1-D | `chemistry.fick_flux` | v2.8 wave-0 |

> **v2.8:** P4 cobre hidráulica/Bernoulli/perdas, **não** transporte de espécies.
> Declarar **species transport/diffusion v0** como pré-condição ou primeira wave
> da chemistry antes de reações/eletroquímica de célula com campos de concentração.

---

## Precedência de lançamento (alinhada a V3 + planos de execução)

1. **v2.6 — Physics Foundation P1–P5 v0** (Engineering Physics Foundation; marco V3 §10 em profundidade foundation):
   plataforma `oec.physics` + objectos de domínio (`PhysicalLaw`, `ConservationLaw`,
   `MaterialProperty`, `BoundaryCondition`) + fatias **P1** DC linear meshed
   (+ harmónicas **opcionais**), **P2** termo, **P3** mecânica, **P4** fluidos
   (f atrito = input), **P5** materiais (lei uniaxial, não solver estrutural).
   **Gates:** ≥1 skill por fatia P1–P4 com conservação/unidades/hipóteses; zero
   private engines; e2e skill→engine→envelope em **P1–P4**; schema AA **1.1** +
   kind `physics_result`; conservation owner único + tol `atol+rtol×scale`.
2. **v2.6.1 — Energy-rich (feature release, número patch) — ✔ shipped 2026-08-04:**
   storage energy-based SOC, pv, hybrid, `grid_zero_feasibility`,
   `min_storage_capacity` via `optimization.lp`, service_metrics — consome a
   plataforma 2.6.0 + `kernel.energy` + Energy Specialist; **não** migra skills
   legadas até parity em release posterior; ownership de conservação **herdado**
   (ADR 0027 Accepted). See [v2.6.1-CLOSEOUT.md](v2.6.1-CLOSEOUT.md).
3. **v2.7 — Multiphysics** (V3 §11): **DELIVERED in `oec==2.7.0`** (`src/oec/physics/coupling/`, ADR 0028, weak GS co-sim, I²R + solar/thermal/electrical). Historical plan text: coupling graph, co-sim v0, acoplamentos
   eléctrico+térmico, solar+térmico+eléctrico.
   **Gate adicional — coupling readiness contract** (obrigatório no plano v2.7):
   - ownership temporal do estado acoplado (quem avança o tempo / passo)
   - variáveis acopladas e interfaces (quem escreve / quem lê)
   - unidades e conversões nos acoplamentos
   - critério de convergência / residual de coupling
   - rollback / checkpoint em falha de co-sim
   - **não** basta “≥2 físicas estáveis”
4. **v2.8 — Chemistry** (V3): **DELIVERED as foundation v0 in `oec==3.1.0`**
   (`src/oec/chemistry/`, ADR 0029) — species/stoichiometry, Qc/Kc equilibrium,
   Arrhenius batch, Nernst C4 (≠ BESS SOC), Fick 1-D transport wave-0.
   Skills thin-wraps / multi-reaction / Gibbs minimiser: still deferred.
5. **Pós-v2.9**: óptica, acústica, matéria condensada, física moderna/quântica,
   núcleo/astro/campos — conforme demanda e maturidade do IR.

### ADRs de física

| ADR | Tema | Release | Status |
|-----|------|---------|--------|
| 0024 | Architecture `oec.physics` + domain objects + schema AA 1.1 / `physics_result` + **ownership `conservation`** | v2.6 | Accepted |
| 0025 | Units / dimensional API + **tol `atol+rtol×scale`** | v2.6 | Accepted |
| 0026 | Escopo Physics Foundation P1–P5 v0 + P1 DC meshed + claim + deferral energy → 2.6.1 + THD opcional | v2.6 | Accepted |
| 0027 | Escopo energy-systems rich + SOC energy-based + grid-zero split + **ownership herdado** + feature release 2.6.1 | v2.6.1 | **Accepted 2026-08-04** |

> **Nota de gate (V3 §10):** qualquer nova área de física exige conservação,
> unidades dimensionais (ADR 0016) e hipóteses explícitas. Zero import de
> engines privados. Math IR (`oec.modeling`) permanece domain-agnostic (ADR 0020).
>
> **Correção histórica:** um rascunho anterior de `v2.6-EXECUTION-PLAN.md`
> estreitou v2.6 a energy-first; isso **divergia** do V3 §10. O catálogo e os
> planos acima restauram a precedência correta (foundation multidomínio →
> energy-rich feature → multiphysics → chemistry).
>
> **Pós-auditoria Codex (2026-08-03):** status em 3 colunas; claim Foundation;
> elasticidade uniaxial vs solver; P4 f-input; coupling readiness em v2.7;
> species transport em v2.8.

---

## Mapa de ressalvas Codex (catálogo) → secções

| # | Ressalva | Secção |
|---|----------|--------|
| 13 | Status em 3 colunas | Legenda + todas as tabelas |
| 14 | Renomear marco Foundation | Header, precedência §1, nota de claim |
| 15 | Elasticidade uniaxial vs solver | §5 Mecânica |
| 16 | P4 f atrito input; Re/Colebrook depois | §6 Fluidos |
| 17 | v2.7 coupling readiness contract | Precedência item 3 |
| 18 | v2.8 species transport pré-condição | §14 + precedência item 4 |
