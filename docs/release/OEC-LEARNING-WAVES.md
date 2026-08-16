# OEC Learning — Gap analysis & wave plan

**Source:** `OEC Learning — Arquitetura, Política de Backends e Plano de Waves` (2026-08-16)
**Compared against:** RC `integration/3.6-scientific-ai` @ `014894f` (`oec==3.6.0`, 151 skills / 28 domains / 12 builders)
**Status:** planning (post–Scientific AI 3.6)
**Package today:** there is **no** `oec.learning` — neural / foundation / experiment are separate families.

Principle (unchanged): **OEC defines scientific contracts. External frameworks are replaceable backends.**

Kronos is **out** of these waves (time-series FM later).

---

## 1. What 3.6 already covers vs the Learning spec

| Learning capability | 3.6 reality | Verdict |
|---------------------|-------------|---------|
| Neural train/eval (MLP/CNN/RNN/TF/GNN) | 26 `neural.*` skills + `oec.neural` | **Partial** — skill-first, not `oec.learning` |
| PEFT / LoRA / QLoRA / full FT | `foundation.peft_train`, `PEFTSpec` 0.2.0 | **Partial** — HF-only, no backend swap |
| Distillation | `neural.distill` (tabular teacher→student) | **Partial** — not FM teacher/SFT dataset/benchmark |
| Foundation infer | embed / generate / vision / VLM | **Partial** — HF Transformers only |
| Experiment Engine | W2 `ExperimentSpec`/`Record`, 12 builders | **Partial** — skill orchestration, not training lineage |
| Checkpoints + SHA | json_inline/file + digest | **Done** for neural/PEFT artifacts |
| Evaluation / golden | skill goldens + `ExecutionResult` | **Partial** — no Benchmark protocol / compare() |
| Datasets | `DatasetSpec` tabular / PEFT texts | **Thin** — no version/provenance/splits/types |
| Backend registry | ADR 0021 torch/transformers/pymoo… | **Exists** — not FineTuneBackend/Unsloth/Axolotl/ART |
| Unsloth / Axolotl / ART / GRPO / TRL | absent | **Missing** |
| RL contracts / scientific rewards | absent | **Missing** |
| Worker factory E2E | absent | **Missing** |
| `oec.learning` package | **does not exist** | **Missing** |
| Core ↛ ML/AI | still frozen | **Keep** |

**Read of 3.6:** it is a **skill + experiment** cut for Scientific AI. Learning spec is a **new layer** on top — do not rewrite 3.6 skills; **re-home** them under contracts and adapters.

---

## 2. What still needs finishing (before claiming Learning)

### Must exist as *OEC* types (Wave L1–L4)

- Public contracts: `Model`, `Dataset`+schema/provenance, `Trainer`/`TrainingConfig`/`TrainingResult`, `Metric`/`Evaluator`/`Verifier`, `Benchmark`, `Experiment` (learning-grade), `Artifact`/`Checkpoint`
- Dataset types: scientific, supervised, SFT, preference, distillation, tool-use, trajectory, RL
- Experiment must capture: id, commit, dataset version, model+revision, hparams, seed, hardware, backend, metrics, logs, artifacts, eval
- `experiments.compare([...])` under one benchmark protocol
- Evaluation ≠ Benchmark (spec §4 / regra 4)

### Must exist as *adapters* (Wave L5+)

- HF = **reference** backend (Transformers, PEFT, later TRL/Datasets) — **no HF types in public API**
- Unsloth / Axolotl swap on the **same** FineTune contract
- ART implements ReinforcementTrainer (GRPO), does not define RL architecture

### Must remain out of core install

HF, PEFT, TRL, Unsloth, Axolotl, ART — extras only, fail-closed.

---

## 3. Mapping 3.6 → Learning waves (reuse, don’t duplicate)

| Learning wave | Reuse from 3.6 | New work |
|---------------|----------------|----------|
| **L1 Contracts** | ADR 0034/0035/0040–0042, `oec.neural.contracts`, `oec.foundation.contracts`, `oec.experiment.specs` | New `oec.learning` closed Pydantic + backend protocols |
| **L2 Datasets** | tabular `DatasetSpec`, PEFT `TrainingDatasetSpec` | Version/provenance/splits/types + HF Datasets **adapter only** |
| **L3 Experiments** | `run_experiment`, artifacts, builders | Training-run snapshot: hardware, backend id, dataset version, lineage |
| **L4 Eval/Benchmark** | skill goldens, verification engine | Metric/Evaluator/Benchmark + compare two checkpoints |
| **L5 HF reference** | `foundation.*`, `peft_train`, generate+adapter | Wrap as `HuggingFaceBackend`; hide HF objects |
| **L6 Distillation** | `neural.distill` | Teacher/demo/SFT dataset/FM distill + benchmark vs base |
| **L7 Unsloth** | — | Adapter + HF-vs-Unsloth bench |
| **L8 Axolotl** | — | Recipe → Experiment translation |
| **L9 RL contracts** | — | Env/Trajectory/Reward/Policy (no ART) |
| **L10 ART/GRPO** | MCP/skills as future tools | ARTBackend |
| **L11 Scientific rewards** | validation/units/skills | Math/Physics/EE/Tool environments |
| **L12 Worker pipeline** | MCP + experiment | E2E demo worker (not a product) |
| **L13 Backend suite** | — | Permanent A/B/C experiments |
| **L14 Hardening** | CI 3.6 gates, capability registry | Isolation, resume, integrity, docs |

Numbering **L1–L14** avoids collision with W0–W8 (3.5) and S0–S6 (3.6).

---

## 4. Recommended execution order

```text
L1 Contracts
 → L2 Datasets
 → L3 Learning Experiments (extend W2, do not fork)
 → L4 Evaluation / Benchmark
 → L5 HF reference backend (re-home 3.6 foundation/PEFT)
 → L6 Distillation (extend neural.distill)
 → L7 Unsloth
 → L8 Axolotl
 → L9 RL contracts
 → L10 ART / GRPO
 → L11 OEC scientific reward environments
 → L12 Worker training pipeline
 → L13 Backend benchmark suite
 → L14 Production hardening
```

**Do not** implement Unsloth/Axolotl/ART before L1–L5. Adapters without contracts violate the source spec.

**First delivery slice (if capacity limited):** `L1 → L2 → L3 → L4 → L5` then stop for a Learning MVP review. L6 can start after L5. L7+ only after HF swap is proven.

---

## 5. Wave cards (implementation)

### L1 — Learning contracts

- New package `oec.learning` (core-safe: pydantic only)
- Closed enums; no `nn.Module` / free Python from agents
- Protocols: `FineTuneBackend`, `DistillationTrainer`, later `ReinforcementTrainer`
- ADR 0043 (proposed): OEC Learning layer
- **Gate:** core install has zero HF/Unsloth/Axolotl/ART imports

### L2 — Dataset foundation

- `Dataset` + schema, loader, transform, split, seed, version, provenance, lineage
- Types: supervised, scientific, SFT, preference, distillation, tool-use, trajectory
- **Gate:** reconstruct + identify a dataset by version + provenance hash

### L3 — Learning experiment engine

- Extend `oec.experiment` or add `oec.learning.experiments` **on top** of ExperimentRecord
- Capture commit, hardware, backend, dataset version, model revision
- **Gate:** a finished training run is reproducible from the record alone

### L4 — Evaluation & benchmarking

- Metric / Evaluator / Verifier / EvaluationSuite / Benchmark
- Golden sets as versioned artifacts
- `compare(run_ids)`
- **Gate:** two checkpoints compared under one frozen protocol

### L5 — Hugging Face reference backend

- Move current Transformers/PEFT runtime behind `HuggingFaceBackend`
- Public API stays OEC contracts
- Optional extra still `oec[foundation]`
- **Gate:** no HF types leaked on public surfaces

### L6 — Distillation workflow

- Teacher → demonstrations → DistillationDataset → student → eval → benchmark
- Keep `neural.distill` as first backend path
- **Gate:** Base Student vs Distilled Student numbers from ExecutionResult only

### L7–L8 — Unsloth / Axolotl

- Same FineTune contract; `backend="huggingface"|"unsloth"|"axolotl"`
- **Gate L7:** swap backend with no contract change
- **Gate L8:** Axolotl recipe ≡ OEC Experiment (not an opaque script)

### L9–L11 — RL

- L9 contracts only; L10 ART adapter + GRPO; L11 OEC verifiers as reward
- **Gate L11:** reward mostly from deterministic verifiers (units, constraints, skill status)

### L12–L14

- L12: one E2E scientific/Python worker demo
- L13: permanent backend + agentic metrics suite
- L14: CI extras, capability discovery, resume, integrity, docs

---

## 6. Non-goals (this programme)

- Kronos / temporal FMs
- POST-OEC autonomous research harness
- Making Unsloth/Axolotl/ART structurally required
- Replacing 3.6 skill engine
- Declaring a backend “better” without a benchmark (regra 6)

---

## 7. Relation to unfinished 3.6 process

PR #1 (`integration/3.6-scientific-ai` → `main`) can still merge/tag independently.
Learning L1+ should land **after** 3.6 is on `main` (or branch from the RC) so Learning sits on a tagged Scientific AI baseline.

---

## 8. Graphify

This note is indexed as a first-class planning node. Rebuild OEC graph after adding this file (`graphify update .`). Vault copy: `joao-knowledge-vault/03_Projetos/OEC/`.
