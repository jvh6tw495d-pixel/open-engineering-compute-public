# OEC 3.6 — Scientific AI Completion

**Baseline:** `oec==3.5.0` (W0–W8 complete)
**Code baseline:** `oec==3.6.0` (S0–S6 local gates complete; remote optional-extras CI and release-owner tag/push decision pending)
**Release action:** a `v3.6.0-scientific-ai` tag is a future owner action; none is claimed here.
**Governing ADRs:** [0040](../architecture/adr/0040-scientific-ai-completion.md),
[0041](../architecture/adr/0041-peft-finetune-distill-contracts.md),
[0042](../architecture/adr/0042-neat-exclusion-3.6.md)

**Post-3.6:** [ADR 0044](../architecture/adr/0044-neat-governed-backend.md) re-opens
**NEAT** (not HyperNEAT) as a governed optional path. This document remains the
3.6 freeze record.
**Principle:** **Backends compute. OEC defines the scientific contract.**

---

## 1. Postulado

OEC is the **common scientific infrastructure** for neural computing, training,
evolutionary computing, neuroevolution, foundation models, governed LLM/VLM
inference, PEFT, knowledge distillation, and hybrid experiments across those
paradigms — without reimplementing PyTorch, Transformers, or evo libraries.

POST-OEC autonomous research harness remains **out of repo**.

---

## 2. Closed decisions (S0)

| ID | Topic | 3.6 choice |
|----|--------|------------|
| D1 | NEAT / HyperNEAT | **Excluded** (ADR 0042) |
| D2 | vLLM / llama.cpp / SGLang | **Out** — HF only |
| D3 | VLM / multimodal | **In** as S5 MVP |
| D4 | Distillation home | **`neural.distill` first** |
| D5 | Status promotion | **Core subset** when gates pass |

---

## 3. Baseline inventory (3.5.0)

| Domain | Skills (approx) | Extra | Notes |
|--------|-----------------|-------|--------|
| neural | 26 | `oec[neural]` | families + train + search + eval/predict |
| evolutionary | 15 | `oec[evolutionary]` | single/multi-obj + portfolio + GP |
| hybrid | 2 | neural/evolutionary | ADR 0033 paths |
| foundation | 6 | `oec[foundation]` | embed / generate / capabilities / PEFT / vision / VLM |
| Experiment | builders W4–W7 | — | fail-closed catalog on MCP |

All AI skills ship as `experimental` until S3/S6 promotion.

---

## 4. Gap matrix → planned skills

| Capability | 3.5 state | 3.6 plan | Wave | Skill / action |
|------------|-----------|----------|------|----------------|
| Neural train/eval | Done | Harden checkpoints | S3 | existing + predict reload |
| Evolutionary | Done | Harden builders/gates | S4 | existing |
| Neuroevolution / hybrid | Done | Builders + smoke | S4 | existing |
| Foundation embed/generate | Done | Provenance harden | **S1 done** | `adapter_path` reload, fail-closed |
| **PEFT train** | **Done (S1)** | Implement | **S1 done** | `foundation.peft_train` |
| **Full fine-tune** | **Done (S1)** | Mode or skill | **S1 done** | `mode: full` on `foundation.peft_train` |
| **Distillation** | **Done (S2)** | Implemented | **S2 done** | `neural.distill` + catalogued builder |
| **VLM** | **Delivered (S5)** | Bounded, fail-closed MVP | **S5 done** | `foundation.vision_embed`, `foundation.vlm_generate` |
| NEAT | Deferred | **Exclude** | — | ADR 0042 |
| vLLM etc. | Missing | Debt only | — | technical-debt |
| Experiment PEFT→gen | **Done (S1)** | Builder | **S1 done** | `build_peft_train_then_generate_experiment` |
| Experiment distill→eval | **Done (S2)** | Builder | **S2 done** | catalog allow-list |
| MCP demos | foundation embed + PEFT | VLM raw + agent discovery | **S5 done** | `agent.foundation` demos `vision_embed` / `vlm_generate`; raw S5 skills discoverable |
| CI extras job | core-minimal + PR/push optional and wheel-install gates | **S6 local gate done; remote evidence pending** | core-only plus neural + evolutionary + foundation |

---

## 5. Waves S0–S6

| Wave | Goal | Exit criteria |
|------|------|---------------|
| **S0** | ADR freeze + this matrix | ADRs 0040–0042 accepted; decisions closed |
| **S1** ✅ | PEFT / FT + artifacts | train→artifact→generate path; `-m foundation` smoke |
| **S2** ✅ | Distill | `neural.distill` + catalogued builder completed in a neural-enabled focused run |
| **S3** ✅ | Neural industrial | versioned checkpoint normalization/reload; SHA-checked and cache-confined file checkpoints; bounded S2 teacher/student MLPs; promotion criteria documented (skills remain experimental) |
| **S4** ✅ | Evo industrial | no NEAT; hybrid/neuroevolution builders hardened |
| **S5** ✅ | VLM MVP | bounded vision embedding + Vision2Seq generation, immutable HF commit pins, no URL fetch, and MCP raw/agent discovery |
| **S6** | Release gate / CI | version and public surfaces updated; core-minimal plus PR/push optional-extras and wheel-install CI added; verification evidence and any owner tag/push remain pending |

### Recommended execution if capacity is tight

`S0 → S1 → S3 → S2 → S4 → S6` with **S5** still in DoD but schedulable after S1.

---

## 6. Architecture (target)

```text
                         OEC
                          │
                 Scientific Framework
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
     Neural          Evolutionary        Foundation
    Computing         Computing           Models
        │                 │                  │
     PyTorch       pymoo / DEAP /       Transformers
                      Nevergrad          + peft
        │                 │                  │
        └──────────┬──────┴─────────┬────────┘
                   │                │
             Experiment Engine      │
                   │                │
             Validation Engine      │
                   │                │
             Provenance / Artifacts │
                   └────────────────┘
```

---

## 7. Neural skill promotion criteria

S2/S3 hardening does **not** promote any skill. All neural skills, including
`neural.distill`, remain `experimental` until a release owner records every gate
below for the exact version being promoted:

1. Clean core suite plus neural-enabled focused suite, Ruff, MyPy, contract audit,
   and the ExecutionResult contract test.
2. Multi-seed benchmark report with declared data, metrics, tolerances, and a
   documented regression threshold for the candidate skill.
3. Independent review of checkpoint behavior: inline state-integrity digest,
   file SHA verification, cache-root confinement, and `weights_only=True` loading.
4. Reproducibility evidence for the supported CPU/device configuration and a
   documented operational rollback/compatibility path.
5. A release decision updates the manifest status and release notes together.

The inline SHA-256 check is integrity-only: it is neither a signature nor evidence
of cryptographic origin/provenance. Failure or absence of any gate leaves the skill
`experimental`.

---

## 8. DoD checklist (release gate)

- [x] ADR 0040–0042 in tree (S0)
- [x] `foundation.peft_train` (+ FT mode/skill) with golden / fail-closed (S1)
- [x] Adapter/checkpoint artifact + generate reload provenance (S1)
- [x] `neural.distill` + builder (S2)
- [x] Neural checkpoint reload stable for predict/evaluate (S3)
- [x] Evo/hybrid builders green; NEAT documented excluded (S4)
- [x] VLM MVP: `foundation.vision_embed` + `foundation.vlm_generate`, immutable remote commit pins, bounded image metadata decode, and no URL fetch (S5)
- [x] MCP discovery for raw S5 skills + `agent.foundation` demos (S5)
- [x] Core suite green without AI extras (S6 evidence) — local core-only gate verified
- [x] Version bump, truthful Unreleased CHANGELOG, public catalog/MCP surfaces, and closeout document (S6)
- [x] Scheduled/manual optional-extras CI marker gate for neural/evolutionary/foundation (S6)
- [ ] Release owner reviews evidence and decides whether to tag/push/publish (out of this closeout)

---

## 8. Non-goals

- POST-OEC harness
- Full TRL RLHF/DPO productization
- Multi-node training
- Arbitrary agent `nn.Module` / free fitness eval
- Core install depending on torch/transformers/pymoo

---

## 9. Relation to 3.5.0

See [FRAMEWORK-3.5.0.md](FRAMEWORK-3.5.0.md). Items formerly listed under
“Out of scope (POST-OEC / later)” that are **in** 3.6:

- Full PEFT train skill → **S1**
- VLM inference MVP → **S5**

Still out / debt:

- NEAT productization → ADR 0042
- vLLM / llama.cpp adapters → technical-debt
- POST-OEC harness → out of repo
