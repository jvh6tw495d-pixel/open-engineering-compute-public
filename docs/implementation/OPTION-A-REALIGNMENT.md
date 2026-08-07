# Option A realignment — follow the original V3 plan

**Date:** 2026-08-06
**Decision:** **Option A** (original plan §18) is restored as the product north star.
**Source:** `OEC_V3_IMPLEMENTATION_PLAN.md`

---

## 1. What Option A means

| Item | Rule |
|------|------|
| Sequence | … → 2.6 → 2.7 → 2.8 → 2.9 RC → **3.0 = public GitHub** |
| v3.0 content | Math + Physics + Chemistry **unified enough to publish** (not years-deep every subfield) |
| v3.0 gate | External person installs, runs, validates, contributes without internal lore |
| Publish | Sibling public tree + human review + remote — **never** dirty incubation history |

**Option C** (early “platform claimable” `3.0.0` without finishing 2.8/2.9 RC) is **withdrawn** as the product claim for “official v3.0”.

---

## 2. Honest map: SemVer history vs product milestones

Incubation already used inflated tags under Option C pressure:

| Git / pyproject (history) | Product milestone (Option A) | Status |
|---------------------------|------------------------------|--------|
| `2.6.x` – `2.7.0` | Physics + multiphysics | **DONE** |
| `3.0.0` (Option C cut) | **Not** official public v3.0 | **Claim withdrawn** for Option A |
| `3.1.0` | Chemistry foundation + Sci IR + Model Registry (2.8/2.9 **library**) | **DONE** foundation |
| next `3.1.x` / RC docs | **2.9 RC residual** (skills, migrations, security, docs) | **THIS TRACK** |
| **public tag `v3.0.0`** on clean tree | Official GitHub launch (plan §14) | **HUMAN_GATE** after RC green |

SemVer on incubation may stay ≥ 3.1.x for code continuity. The **public tree’s first official tag remains `v3.0.0`** per plan §1.3 / §14 (clean history, ADR 0008).

---

## 3. Residual backlog (execute in order)

### 2.8 Chemistry Complete — gate residual

| Item | Plan | Status |
|------|------|--------|
| C1–C4 + transport library | §12 | DONE in `oec.chemistry` |
| Executable + verifiable via skills | gate “executáveis e verificáveis” | **skills thin-wrap** (this cut) |
| Gibbs simplified | §12 C2 | **ΔG° → K** helper (not full G-minimiser) |

### 2.9 RC residual

| Item | Plan §13 | Status |
|------|----------|--------|
| Scientific IR | | DONE v0 |
| Model Registry + fidelity | | DONE v0 |
| Deprecations + migrations guide | | **this cut** |
| Security / performance pass | | **this cut** (checklist + forbidden) |
| Domain docs | | **this cut** (api/chemistry, registry) |
| RC tag process | `2.9.0-rc.N` product label | **docs RC; public tag later** |

### 3.0 public (plan §14)

| Item | Status |
|------|--------|
| Sibling public tree | process known (`prepare_public_alpha`) |
| Forbidden-names 0 on public tree | required before push |
| Human review | required |
| Remote + tag `v3.0.0` | **HUMAN only** |
| Coverage ≥ 85% / golden 200 | aspirational; document residual |

---

## 4. Terminal (product)

```text
STRATEGY: OPTION_A_RESTORED
OPTION_C_PLATFORM_CLAIM: WITHDRAWN_AS_V3_0_OFFICIAL
CHEMISTRY_LIBRARY: IN_3_1_0
SCIENTIFIC_IR_REGISTRY: IN_3_1_0
NEXT: 2_9_RC_RESIDUAL_THEN_PUBLIC_V3_0
PUBLIC_PUSH: HUMAN_GATE
```
