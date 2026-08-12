# OEC 3.6 — Scientific AI Completion

**Baseline:** `oec==3.5.0` (W0–W8 complete)
**Target:** `oec==3.6.x` / tag `v3.6.0-scientific-ai`
**Governing ADRs:** [0040](../architecture/adr/0040-scientific-ai-completion.md),
[0041](../architecture/adr/0041-peft-finetune-distill-contracts.md),
[0042](../architecture/adr/0042-neat-exclusion-3.6.md)
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
| foundation | 3 | `oec[foundation]` | embed / generate / capabilities |
| Experiment | builders W4–W7 | — | fail-closed catalog on MCP |

All AI skills ship as `experimental` until S3/S6 promotion.

---

## 4. Gap matrix → planned skills

| Capability | 3.5 state | 3.6 plan | Wave | Skill / action |
|------------|-----------|----------|------|----------------|
| Neural train/eval | Done | Harden checkpoints | S3 | existing + predict reload |
| Evolutionary | Done | Harden builders/gates | S4 | existing |
| Neuroevolution / hybrid | Done | Builders + smoke | S4 | existing |
| Foundation embed/generate | Done | Provenance harden | S1 | existing |
| **PEFT train** | Spec only | **Implement** | S1 | `foundation.peft_train` |
| **Full fine-tune** | Missing | Mode or skill | S1 | `foundation.finetune` or mode |
| **Distillation** | Missing | Implement | S2 | `neural.distill` |
| **VLM** | Missing | MVP | S5 | `foundation.vision_embed`, `foundation.vlm_generate` |
| NEAT | Deferred | **Exclude** | — | ADR 0042 |
| vLLM etc. | Missing | Debt only | — | technical-debt |
| Experiment PEFT→gen | Partial | Builder | S1 | catalog allow-list |
| Experiment distill→eval | Missing | Builder | S2 | catalog allow-list |
| MCP demos | foundation embed | + peft | S1/S6 | `agent.foundation` |
| CI extras job | markers only | optional job | S6 | torch+HF tiny |

---

## 5. Waves S0–S6

| Wave | Goal | Exit criteria |
|------|------|---------------|
| **S0** | ADR freeze + this matrix | ADRs 0040–0042 accepted; decisions closed |
| **S1** | PEFT / FT + artifacts | train→artifact→generate path; `-m foundation` smoke |
| **S2** | Distill | `neural.distill` + builder COMPLETED |
| **S3** | Neural industrial | checkpoint contract; promotion criteria; subset stable optional |
| **S4** | Evo industrial | no NEAT; hybrid/neuroevolution builders hardened |
| **S5** | VLM MVP | vision embed + vlm generate fail-closed |
| **S6** | Release | CHANGELOG, README counts, tag, optional CI job |

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

## 7. DoD checklist (release gate)

- [ ] ADR 0040–0042 in tree (S0)
- [ ] `foundation.peft_train` (+ FT mode/skill) with golden / fail-closed (S1)
- [ ] Adapter/checkpoint artifact + generate reload provenance (S1)
- [ ] `neural.distill` + builder (S2)
- [ ] Neural checkpoint reload stable for predict/evaluate (S3)
- [ ] Evo/hybrid builders green; NEAT documented excluded (S4)
- [ ] VLM MVP skills or explicit waiver if blocked (S5)
- [ ] MCP allow-list builders updated; agent demos (S6)
- [ ] Core suite green without AI extras (S6)
- [ ] CHANGELOG 3.6.0 + version bump + closeout (S6)

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
