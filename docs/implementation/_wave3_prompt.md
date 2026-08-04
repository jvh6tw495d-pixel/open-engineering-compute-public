# WAVE 3 — Executor Sonnet — Núcleo físico multidomínio P1-P5 (funções puras)

Estás a implementar a Wave 3 do release OEC 2.6.0 ("Physics Foundation P1-P5 v0").
REPO: C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC
Branch a usar: criar feat/v2.6-wave-3 a partir de feat/v2.6-wave-2 (baseline 4f19b75).
Ambiente de teste: .venv/Scripts/python.exe -m pytest <arquivos> (não usar python global).
Plano mestre de referência: docs/implementation/v2.6-EXECUTION-PLAN.md (secção 7 = Wave 3).

## GATE-W3 já aprovado (Opus, veredito GO baseline 4f19b75)
Baseline W2 coerente. Objetos transversais executáveis (satisfazem W1, são stubs dummy). Densificação = esta wave.

## O que criar (DENTRO de src/oec/physics/)
1. **Expandir `conservation.py` como OWNER denso (owner D5)** — ANTES de P1. Sem isto, nada.
   - Residual multi-nó/vetorial para DC power flow: agregação KCL por nó + Σinjeções; retorna residual+balanced.
   - Manter evaluate_residual (escalar) e evaluate_dimensional_residual (QuantityValue) como pontos de entrada ÚNICOS do owner.
   - FATIA** PROIBIDO reimplementar `abs≤atol+rtol×scale` inline em electrical.py ou outro módulo — tudo roteia por oec.physics.conservation.
   - Reconciliar unidade de residual por check com o balanço REAL (não confiar cegamente nos defaults N/Pa da TOLERANCE_DEFAULTS existente; ex. P3 balanço é energia em J, P5 é constitutivo não-balanço).
2. **`electrical.py` (P1)** — `dc_power_flow` MESHED conforme D4:
   - Matriz B / susceptâncias, nó slack, ângulos θ relativos, fluxos P_ij, residual KCL + `balanced`.
   - NÃO radial-as-canonical. NÃO AC PF. NÃO máquinas. NÃO LP/dispatch (isso é Optimization Specialist).
   - Façade documentada da elétrica clássica (skills electrical.* intocadas).
3. **`thermal.py` (P2)** — condução 1D + capacidade térmica, com unidades e residual de balanço térmico onde couber.
4. **`mechanics.py` (P3)** — cinemática 1D + energia mecânica (cinética/potencial/trabalho), balanço de energia em J.
5. **`fluids.py` (P4)** — Bernoulli + perdas v0 com f (fator de atrito) como INPUT; continuidade 0D/1D. SEM alegar Reynolds/Colebrook/regime.
6. **`materials.py` (P5)** — lookup de propriedades + lei material uniaxial v0 (Hooke). NÃO solver estrutural.
7. **Harmónicas/THD (`harmonics.py`)** — OPCIONAL (D7). Se ausente, deixar debt residual documentado. NÃO bloqueia.
8. **`__init__.py`** — exportar a API pública nova.
9. **Data** `data/` (tabelas materiais) — opcional.

## Non-goals (NÃO fazer nesta wave)
- NENHUM módulo storage/pv/hybrid/grid_zero/service_metrics (energy-rich = 2.6.1).
- NENHUM pricing/tarifa/LP/comercial dentro de physics.
- NENHUM toque em envelope.py, schema authoritative_answer, kernel/energy/metrics.py.
- NÃO reabrir D3 (schema 1.1/physics_result = Wave 4), nem D4, nem D5, nem D6, nem D7.
- NÃO reescrever skills electrical.* clássicas.

## Testes
- tests/unit/test_physics_*.py (novos por módulo/slice).
- tests/golden/physics/ ou inline golden.
- **GOLDEN 3.8 obrigatória:** provar ≥2 fatias usando PhysicalLaw e/ou ConservationLaw EXECUTADOS sobre modelos REAIS (não stubs dummy). Ex.: P1 roteia residual por ConservationLaw; P2/P3 por PhysicalLaw+ConservationLaw.
- Suite full deve ficar GREEN. Cobertura global 90% é meta do release (atualmente 86%); a Wave 3 deve subir isso com as funções novas. Se ficar abaixo, deixa explícito o que falta.

## Cada modelo v0 deve listar `assumptions` (texto estruturado ou objeto Assumption)
## Hipóteses por slice. Cada função pública ≥1 docstring + golden.

## Commits (git)
1. feat(physics): conservation checks owner denso (3.1)
2. feat(physics): electrical dc power flow meshed v0 (3.2)
3. (opcional) feat(physics): light harmonics thd v0 (3.3)
4. feat(physics): thermal conduction and capacity (3.4)
5. feat(physics): mechanics kinematics and energy (3.5)
6. feat(physics): fluids bernoulli and losses (3.6)
7. feat(physics): materials properties and linear constitutive (3.7)
8. test(physics): multidomain golden set (3.8)

Termina com: (a) lista de arquivos criados/alterados; (b) resultado da suite (green? cobertura?); (c) lista de assumptions por slice; (d) se THD feito ou debt residual; (e) SHA do commit final.
NÃO digas que fizeste sem correr os testes. Se algo falhar, corrige antes de terminar.
