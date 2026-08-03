# Análise Geral — Codex gpt-5.6-sol (auditoria independente)

**Data:** 2026-08-03 · **Branch:** feat/v2.5.3-wave-3 · **HEAD:** `3607987c11fd` · **Modo:** estritamente read-only (sem testes, sem alteração de arquivos)

> Veredito geral: **GO-COM-RESSALVAS** para iniciar a implementação do 2.6.

---

## A — Release v2.5.3 · Veredito: ⚠ Atenção

A implementação principal cumpre a intenção arquitetural: normalização única no boundary público, preservação de payloads, autoridade independente da narrativa e comparação pós-serialização. Funcionalmente bem desenhada, mas o schema publicado é permissivo demais para sustentar o claim de "contrato v1.0".

### Riscos
1. **Schema v1.0 não valida efetivamente o envelope.** Objeto raiz sem `required`/`additionalProperties:false` → `{}` e envelopes sem `authoritative_answer_schema_version` podem validar. [authoritative_answer.schema.json:90]
2. **Sem validação de output real com `jsonschema`.** Testes verificam campos individualmente; possível drift código↔schema. [COMPLETE-AUDIT-AND-ADDITIONS.md:120]
3. **Wrap-once corretamente posicionado.** `normalize()` só após `_run_specialist_by_name`; recursão default abaixo do boundary → sem double-wrap de fato. [server.py:810,821]
4. **Idempotência usa marcador confiado.** Payload interno com `authoritative_answer_schema_version=="1.0"` não é recalculado; colisão de namespace possível p/ futuros reports. [envelope.py:421]
5. **Autoridade verbatim semanticamente correta** no wire (dict copy em vez de ref, JSON equivalente; dual fechado em {min,max}). [envelope.py:287,305]
6. **Claim "nove shapes" impreciso.** ADR inclui bare ExecutionResult entre as nove, mas raw-skill tools são excluídos da normalização. [ADR 0023:9 vs :115]
7. **Divergência aditiva e não contamina autoridade.** Compara sobre values, suporta claims parciais, falha fechada p/ NaN/Infinity. [divergence.py:96,217]

### Recomendações
- Tornar `authoritative_answer_schema_version` obrigatório no envelope normalizado.
- Schemas distintos: normalizado com autoridade / sem autoridade / passthrough needs_* / erro-raw.
- Testes de validação Draft 2020-12 das respostas reais de cada shape.
- Guard de idempotência por marcador privado/interno (ou detectar payload marcado mas inválido).
- Corrigir doc para "nove shapes reconhecidas; apenas agent-tool success normalizadas".
- Não reabrir o desenho do envelope: correções contratuais localizadas.

---

## B — Plano v2.6 · Veredito: ⚠ Atenção

Alinhado ao V3 §10; layering `skills → oec.physics → modeling/kernel/core` correto; sequenciamento plataforma→unidades→física→skills faz sentido. Porém o "v0" reúne decisões não congeladas e há conflito com o schema fechado da v2.5.3.

### Riscos
1. **`physics_result` quebra a taxonomia fechada v1.0.** Plano manda adicionar o valor mantendo schema 1.0, mas não existe no enum publicado. [v2.6:97 vs schema.json:16] → evolução contratual, não extensão invisível.
2. **P1 ambíguo: "DC ou radial".** São modelos diferentes (entradas/hipóteses/oracles distintos). Decisão deve preceder a API comum. [v2.6:22]
3. **THD obrigatório no núcleo** embora o gate exija só 1 skill P1 → superfície desnecessária. [v2.6:378]
4. **Objetos transversais podem virar abstrações decorativas** — critérios Wave 1 não exigem que ≥2 fatias executem a partir deles. [v2.6:268]
5. **BoundaryCondition antes de semântica de modelo** — pode virar só metadata; falta decidir se é declaração auditável ou input do solver.
6. **Conservation API pode duplicar kernel.energy.energy_balance** sem definir ownership. [v2.6:388 vs metrics.py:8]
7. **Tolerâncias "versionadas" sem política transversal** — residual depende de escala/unidade/condicionamento; tol absoluta genérica gera falsos pass/fail.
8. **Cronograma subestimado operacionalmente** — V3 est. 12–20 semanas+ vs Wave 3 em 3–5 sessões. [V3:403 vs v2.6:438]
9. **Smoke final cobre só 2 fatias** — insuficiente p/ claim P1–P5; P1–P4 deveriam atravessar skill→engine→envelope.

### Recomendações (pré GATE-W1)
- Política de evolução do envelope: `physics_result` → schema 1.1/2.0 OU evitar usando `generic_result` até versionamento formal.
- Fechar P1: **DC power flow linear meshed** OU **radial branch-flow** (uma escolha).
- THD opcional de verdade, posterior ao 1º P1 completo.
- Contrato operacional dos 4 objetos (metadata vs avaliativo).
- Uso real dos objetos em ≥2 fatias.
- Ownership conservation: `oec.physics.conservation` generaliza; `kernel.energy.energy_balance` vira adapter OU canônico — nunca duas fórmulas independentes.
- Tolerância dimensional `atol + rtol×scale`, registrada com unidade e política.
- Claim de produto: **"Physics Foundation P1–P5 v0"** (em vez de "Physics Complete") ou elevar gates.
- Integração end-to-end P1–P4, não smoke de 2 fatias.

---

## C — Plano v2.6.1 · Veredito: ⚠ Atenção

Dependência sobre 2.6.0 correta; isolamento energy-rich evita contaminar P1–P5. Sem conflito conceitual forte com 2.6, mas há duplicação de ownership e 2 entregas subespecificadas (storage, grid-zero).

### Riscos
1. **Patch release grande demais semanticamente** (5 módulos, skills, migração, especialista) — mais patent/minor do que patch. [v2.6.1:445]
2. **SOC atual não é "coulomb-counting".** `soc_update` integra potência×tempo/capacidade = **energy counting**; coulomb exigiria corrente/Ah. [metrics.py:41, v2.6.1:19]
3. **"min storage p/ autonomy" não é helper analítico** — vira problema temporal/otimização; fronteira com optimization.lp precisa ser contrato. [v2.6.1:211]
4. **Migração de skills existentes = churn sem necessidade** — energy.balance/battery.soc_step podem ficar adapters. [v2.6.1:290]
5. **3 possíveis owners** (physics.balance, physics.conservation, kernel.energy.metrics) — decidir no ADR 0027, não na implementação.
6. **Convenção de versão inconsistente** (`2.6.1` vs `2.6.1.0`). Padronizar `2.6.1`.

### Recomendações
- Considerar **2.7** para energy-rich (ou declarar 2.6.1 como feature release apesar do patch number).
- `energy_based_soc_update` (potência/energia); reservar `coulomb_counting` p/ corrente/Ah.
- Congelar sinais/convenções de potência (carga/descarga/import/export/storage delta).
- Separar: `grid_zero_feasibility` (determinístico p/ trajetória dada) vs `min_storage_capacity` (compõe optimization.lp).
- Não migrar skills legadas até parity; adapters primeiro.
- ADR 0027 escolhe um único owner de balanço/conservação.
- Release padronizada como **2.6.1**.

---

## D — Catálogo e coerência global · Veredito: ⚠ Atenção

Precedência macro coerente (2.6 → 2.6.1 → multiphysics → chemistry). Catálogo mistura inventário, compromisso de release e taxonomia acadêmica.

### Riscos
1. **"Physics Complete" > conteúdo entregue.** Óptica/acústica/campos/quântica futuros; claim excessivo. [CATALOG:92,135]
2. **Elasticidade em 2 estados** (P5 constitutivo linear vs mecânica futura) — distinguir "lei uniaxial v0" de "solver estrutural". [CATALOG:75 vs 89]
3. **Darcy-Weisbach depende do futuro** (rugosidade/Re) — v0 deve receber f como input. [CATALOG:80]
4. **Catálogo não distingue nível:** primitive/kernel vs skill vs API oec.physics.
5. **v2.7 multiphysics depende de contratos de estado**, não só "≥2 físicas": ownership temporal, variáveis acopladas, convergência, rollback. [V3:426]
6. **v2.8 chemistry precisa de species transport/diffusion v0** (P4 cobre hidráulica, não transporte).

### Recomendações
- Status em 3 colunas: primitive/kernel · skill · API oec.physics.
- Renomear marco: **"Physics Complete — V3 P1–P5"** ou **"Engineering Physics Foundation"**.
- P5 = só constitutivo uniaxial/property; análise estrutural futura.
- P4 v0 recebe fator de atrito conhecido; Reynolds/Colebrook posteriores.
- Gate v2.7 com "coupling readiness contract".
- Species transport/diffusion v0 como pré-condição ou 1ª wave da v2.8.
- **Manter precedência 2.6 → 2.6.1 → multiphysics → chemistry** (arquiteturalmente defensável).

---

## Resumo executivo (10 pontos)
1. v2.5.3: boundary wrap-once correto, sem double-wrap evidente.
2. `claimed_answer`/`host_output_diverged` aditivos, preservam autoridade do solver.
3. Schema v1.0 permissivo demais — não garante nem a presença da versão.
4. Sem teste que valide envelopes reais contra o JSON Schema publicado.
5. 2.6 alinhado ao V3 §10; layering correto.
6. **Obrigatório**: resolver evolução do enum fechado p/ `physics_result` antes de código.
7. P1 precisa escolher formalmente DC ou radial; "ou" não é contrato.
8. Claim "Physics Complete" mais forte que os gates/smokes.
9. 2.6.1 coerente, mas grande p/ patch + corrigir semântica SOC/coulomb.
10. Precedência global boa; multiphysics precisa de gates de coupling; chemistry de transporte.

**Veredito: GO-COM-RESSALVAS.** Ressalvas são precondições da Wave 1: (1) política de schema/versionamento, (2) fechar modelo P1, (3) ownership de conservação/tolerâncias, (4) ajustar claim/gates "Physics Complete". Sem elas: risco de cristalizar APIs prematuras e quebrar o contrato v1.0.
