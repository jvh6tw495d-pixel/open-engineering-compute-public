# OEC — Dense Neural Runtime + Evolutionary Maturity Map

**Status:** Part A **done**; Part B **done** (E-D0–E-D4; E-D5 partial via expression IR)
**Date:** 2026-08-10
**Baseline:** `oec==3.4.0` (N0–N5, E1–E4, X1–X3 in tree as experimental v0)
**Related:** ADR 0031, ADR 0032, ADR 0033 (evolutionary neural training modes),
`OEC_NEURAL_EVOLUTIONARY_WAVES.md`, `OEC_EVOLUTIONARY_NEURAL_TRAINING.md`,
P0 goldens / agent authority

**Next product arc:** three-mode training (gradient · neuroevolution · hybrid) —
see ADR 0033. Hybrid evo→gradient is the strategic default for larger nets.

### Part A delivery map

| Slice | Status | Location |
|-------|--------|----------|
| N-D0–N-D5 | **done** | shared neural runtime + all train skills |

### Part B delivery map

| Slice | Status | Location |
|-------|--------|----------|
| E-D0/E-D1 runtime | **done** | `src/oec/evolutionary/runtime.py` |
| E-D2 expression IR | **done** | `kernel/evolutionary/expression.py` + `optimize.py` |
| E-D3 inequality constraints | **done** | `constraints` on problem → pymoo `G` |
| E-D4 multi-seed + HV ref | **done** | `seed_matrix.py`; multi-obj `hv_reference` |
| E-D5 domain adapters | **partial** | engineering f via expression IR (skill-id fitness deferred) |
| E-D6 skill promotion | **pending** | still experimental |

## Purpose

1. Design a **shared dense neural training runtime** so MLP and *all* other
   neural families get stronger together (not only toy `hidden=32`).
2. Define **capacity presets per architecture** (closed enums — no agent Python).
3. Publish an **evolutionary maturity map** (breadth of algorithms vs depth of
   engineering usefulness) so neural and evo priorities stay aligned.
4. Sequence implementable slices without breaking ADR 0031 governance.

---

## Non-goals

- Darknet / foundation-model scale training.
- Agent-injected `nn.Module`, fitness `eval`/`exec`, or free PyTorch code.
- Promoting neural/evo skills to `stable` / `validated` in this design alone.
- Moving `torch` / `pymoo` into core dependencies.
- Treating surrogate or evolutionary optima as physics truth (X2 remains).

---

## Part A — Shared neural runtime

### A.1 Problem today

| Layer | Reality in 3.4 |
|-------|----------------|
| MLP | Own contracts (`NeuralModelSpec` / `TrainingSpec`) + `train_mlp` |
| Sequences | Parallel mini-loop in `sequences.py` (defaults `hidden=32`, `n_layers=1`) |
| Transformer | Separate builder/train defaults (`d_model=64`, …) |
| GNN | Separate train loop (`hidden=32`) |
| Autoencoder | Separate builder/train |
| I/O | In-memory `list[list[float]]` / 3D lists; checkpoint as JSON state_dict |
| Training polish | Minimal: optional early stop on MLP; little scheduler / AMP / clip |

**Consequence:** “make neural denser” if done only on MLP leaves the rest toy.

### A.2 Target architecture

```text
                 ┌──────────────────────────────────────┐
                 │  oec.neural.runtime (public specs)   │
                 │  TrainingRuntimeSpec                 │
                 │  CapacityName + resolve_capacity()   │
                 │  DatasetRef / CheckpointRef          │
                 └──────────────────┬───────────────────┘
                                    │
                 ┌──────────────────▼───────────────────┐
                 │  oec.kernel.neural.runtime           │
                 │  device/AMP/seed · scheduler · clip  │
                 │  data load · train loop skeleton     │
                 │  checkpoint file + hash · metrics    │
                 │  n_params · caps · timeouts          │
                 └──────────────────┬───────────────────┘
                                    │
        ┌───────────┬───────────┬───┴────┬───────────┬──────────┐
        ▼           ▼           ▼        ▼           ▼          ▼
      MLP        Seq/RNN     Transf.    GNN         AE       Hybrid
   build_mlp   build_seq   build_tx  build_gnn  build_ae  surrogate
```

Skills stay thin: pick architecture enum + capacity + task; call shared runtime.

### A.3 `TrainingRuntimeSpec` (proposed public contract)

Location: `src/oec/neural/runtime.py` (new) — pure Pydantic, no torch import.

```python
CapacityName = Literal["tiny", "medium", "dense", "wide"]


class DeviceSpec:  # existing, reused
    device: Literal["cpu", "cuda", "auto"] = "cpu"


class TrainingRuntimeSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int = 42
    device: DeviceSpec = Field(default_factory=DeviceSpec)
    epochs: int = Field(default=100, ge=1, le=10_000)
    batch_size: int = Field(default=32, ge=1, le=65_536)
    optimizer: OptimizerSpec = Field(default_factory=OptimizerSpec)
    lr_scheduler: Literal["none", "cosine", "step"] = "none"
    step_size: int = Field(default=50, ge=1)  # for step scheduler
    grad_clip: float | None = Field(default=None, gt=0.0)
    amp: bool = False  # CUDA only; ignored on CPU
    early_stopping_patience: int | None = Field(default=20, ge=1)
    # Hard caps (fail closed before train if exceeded)
    max_params: int = Field(default=5_000_000, ge=1_000, le=50_000_000)
    max_seconds: float | None = Field(default=None, gt=0.0)
```

**Rules:**

- `amp=True` + `device=cpu` → warning or INVALID (prefer INVALID on skill
  validation for honesty).
- Missing torch → existing `TorchNotAvailableError` / fail-closed registry.
- Runtime always returns: `epochs_ran`, `train_metrics`, `val_metrics?`,
  `device`, `seed`, `deterministic_status`, `n_params`, `checkpoint_ref`,
  `dataset_fingerprint`, `model_fingerprint`.

### A.4 Dataset and checkpoint references

**Today:** arrays + JSON checkpoint (fine for toys; blocks dense work).

**Proposed:**

```python
class DatasetRef(BaseModel):
    """Exactly one of inline | path modes (validator)."""

    # inline (current skills; size-capped)
    x: list[Any] | None = None
    y: list[Any] | None = None
    # reference mode (dense path)
    path: str | None = None  # local .npy / .parquet
    format: Literal["json_inline", "npy", "parquet"] = "json_inline"
    val_fraction: float = Field(default=0.2, ge=0.0, lt=1.0)


class CheckpointRef(BaseModel):
    storage: Literal["json_inline", "file"] = "json_inline"
    # json_inline: payload in result["checkpoint"] (current)
    # file: path relative to OEC run cache + sha256
    path: str | None = None
    sha256: str | None = None
    format_version: int = 1
```

**Policy:**

- `format=json_inline` remains default for small demos and unit tests.
- If estimated params > threshold (e.g. 100k) or capacity ∈ {`dense`,`wide`},
  skills **prefer** `checkpoint.storage=file` (or require it).
- Provenance stores fingerprint of weights (sha256), never silent omission.

### A.5 Capacity presets per architecture

`CapacityName` is shared. Resolution is **per family** (closed tables).

#### MLP (`architecture: mlp | mlp_bn | mlp_residual` later)

| Capacity | `hidden_dims` | notes |
|----------|---------------|--------|
| `tiny` | `[64, 32]` | current mental default |
| `medium` | `[256, 256, 128]` | engineering tabular |
| `dense` | `[512, 512, 256, 128]` | target “more dense” bar |
| `wide` | `[1024, 512, 256]` | wide, fewer layers |

Optional closed flags (MLP-only, later slice): `batch_norm: bool`,
`residual: Literal["none","linear"]`.

#### Sequence (`cnn1d` | `lstm` | `gru` | `tcn`)

| Capacity | `hidden` | `n_layers` | TCN/CNN extras |
|----------|----------|------------|----------------|
| `tiny` | 32 | 1 | kernel 3 |
| `medium` | 128 | 2 | kernel 5 |
| `dense` | 256 | 3 | kernel 5, deeper dilations |
| `wide` | 512 | 2 | kernel 7 |

#### Transformer encoder / seq head

| Capacity | `d_model` | `n_heads` | `n_layers` | `ff_dim` |
|----------|-----------|-----------|------------|----------|
| `tiny` | 64 | 4 | 2 | 128 |
| `medium` | 128 | 4 | 3 | 256 |
| `dense` | 256 | 8 | 4 | 512 |
| `wide` | 384 | 8 | 3 | 768 |

Constraint: `d_model % n_heads == 0` (already enforced).

#### GNN (`gcn` | `graphsage` | `gat`)

| Capacity | `hidden` | `n_layers` | GAT `heads` |
|----------|----------|------------|-------------|
| `tiny` | 32 | 2 | 2 |
| `medium` | 64 | 3 | 4 |
| `dense` | 128 | 3 | 4 |
| `wide` | 256 | 2 | 8 |

#### Autoencoder

| Capacity | encoder `hidden_dims` | `latent_dim` |
|----------|----------------------|--------------|
| `tiny` | `[32]` | 8 |
| `medium` | `[128, 64]` | 16 |
| `dense` | `[256, 128, 64]` | 32 |
| `wide` | `[512, 256]` | 64 |

#### Explicit override rule

If the skill input provides **both** `capacity` and raw knobs
(`hidden_dims`, `hidden`, …):

1. Prefer **raw knobs** if fully specified (advanced users / tests).
2. Else expand `capacity` via the table.
3. Always re-check `max_params` after build.

Agents should prefer `capacity` for routing; specialists may expand.

### A.6 Shared train loop responsibilities

| Step | Owner |
|------|--------|
| Resolve device + seed | `kernel.neural.seeding` (existing) + AMP init |
| Build module | family builder (`build_mlp`, `build_sequence_model`, …) |
| Count params / enforce `max_params` | runtime |
| Load batch iterator | runtime (inline arrays or file) |
| Optimizer + scheduler + clip + AMP | runtime |
| Epoch loop + early stop | runtime |
| Metrics | existing `metrics.py` |
| Serialize checkpoint | runtime (`json_inline` or file+sha256) |
| Fingerprints | existing hashing helpers |

Family modules **stop owning** full train loops once migrated; they only build
architectures and declare default capacity maps.

### A.7 Skill surface (migration)

Keep skill ids stable. Extend inputs:

```json
{
  "capacity": "dense",
  "seed": 0,
  "device": "cuda",
  "epochs": 200,
  "amp": true,
  "grad_clip": 1.0,
  "lr_scheduler": "cosine"
}
```

Backward compatible: omit `capacity` → current numeric defaults (tiny-ish).

Pilot order:

1. `neural.mlp.regressor` / `classifier`
2. `neural.lstm` / `gru` / `tcn`
3. `neural.transformer.*`
4. `neural.gcn` / `gat` / `graphsage`
5. `neural.autoencoder.*`
6. hybrid skills that call `train_mlp`

### A.8 Neural implementation slices

| Slice | Deliverable | Gate |
|-------|-------------|------|
| **N-D0** | `TrainingRuntimeSpec` + capacity tables + unit tests (no torch loop yet) | contracts only |
| **N-D1** | Shared train skeleton + AMP/scheduler/clip; migrate MLP | strong golden dense MLP R² + n_params |
| **N-D2** | `CheckpointRef` file mode + sha256 | round-trip predict/evaluate |
| **N-D3** | `DatasetRef` path/npy (parquet optional) | fingerprint stable |
| **N-D4** | Migrate sequence + transformer to runtime | dense preset goldens |
| **N-D5** | Migrate GNN + AE | capacity + max_params goldens |
| **N-D6** | CI extras job: subset `-k dense or capacity` | timeout-bounded |

---

## Part B — Evolutionary maturity map

### B.1 Clarification

OEC “evolutionary” means **evolutionary / black-box optimizers** (pymoo, DEAP,
Nevergrad), not primarily neuroevolution (NEAT). Hybrid X2 can tune MLP
hyperparameters; evolving network *topology* is out of scope until explicitly
added.

### B.2 Two axes

```text
                    DEPTH (engineering usefulness)
                    low                         high
              ┌─────────────┬─────────────────────────┐
  BREADTH     │  toy demo   │  industrial skill       │
  (algorithms │             │  (constraints, real f,  │
   in catalog)│             │   validated status)     │
              ├─────────────┼─────────────────────────┤
  low         │  empty      │  (unlikely)             │
  high        │  OEC 3.4 ★  │  target 3.5–3.6        │
              └─────────────┴─────────────────────────┘
```

**★ Today:** high breadth, low–medium depth.

### B.3 Breadth inventory (already in tree)

| Wave | Algorithms / skills | Backend | Catalog level |
|------|---------------------|---------|---------------|
| E1 | DE, GA, CMA-ES, PSO, `optimize_single` | pymoo | intermediate–advanced names |
| E2 | NSGA-II, NSGA-III, MOEA/D, `pareto_search` | pymoo | advanced multi-obj |
| E3 | GP (closed IR), ES, custom GA | DEAP | intermediate |
| E4 | black-box, optimizer portfolio | Nevergrad | intermediate–advanced |
| X1 | multi-algo × multi-seed benchmark | harness | meta |
| X2 | surrogate+evo, evo hyperparams | torch+nevergrad | hybrid |
| X3 | method_select | catalog | routing |

This breadth is **not** “only a basic GA tutorial.”

### B.4 Depth gaps (why still “basic” as product)

| Depth dimension | 3.4 state | Mature target |
|-----------------|-----------|---------------|
| Objective definition | Built-ins (`sphere`, `rosenbrock`, `rastrigin`, `zdt*`, `bi_sphere`) | Expression IR + skill-bound engineering objectives |
| Constraints | Box bounds mainly | Inequality/equality IR, discrete vars |
| Budgets | Small pop/gens in examples/goldens | Declared eval budget + wall-clock |
| Metrics | best_f, simple HV | HV with fixed ref, IGD+, attainment, multi-seed stats |
| Reproducibility | seed practical | seed matrix + distribution report (X1 full) |
| GP | poly2-scale IR | richer terminals, multi-var engineering formulas |
| Problem I/O | JSON vectors | same DatasetRef spirit / problem fingerprint |
| Skill status | experimental v0.1 | experimental → validated for select skills |
| Physics boundary | documented | enforced messaging on hybrid surrogates |
| Neuroevolution | absent | optional later wave (closed genotype IR) |

### B.5 Maturity scores (honest, 1–5)

| Area | Breadth | Depth | Notes |
|------|---------|-------|-------|
| Single-obj continuous box | 4 | 4 | Built-in + expression IR + multi-seed |
| Multi-obj Pareto | 4 | 3 | Fixed HV reference option + multi-seed matrix |
| Symbolic GP | 3 | 2 | Unchanged (separate DEAP path) |
| Black-box portfolio | 3 | 2 | Unchanged Nevergrad wrap |
| Hybrid surrogate | 3 | 2 | Unchanged X2 |
| Constraint handling | 3 | 3 | Inequality IR g(x)≤0 on SOO |
| Real domain skills (energy, control) | 2 | 2 | Via expression IR (not skill-id fitness yet) |
| Governance (seed, fingerprint, fail-closed) | 4 | 4 | Strong OEC core |

**Overall evo 3.4 (pre-Part-B):** breadth **~4/5**, depth **~2/5**.
**After Part B (this delivery):** breadth **~4/5**, depth **~3.5/5** (expression+constraints+multi-seed+fixed HV; domain skill-fitness still thin).

### B.6 Evolutionary depth slices (mirror of neural dense)

| Slice | Deliverable | Aligns with neural |
|-------|-------------|-------------------|
| **E-D0** | Maturity map + problem/budget contracts tightened (doc + schema caps) | N-D0 contracts |
| **E-D1** | Shared `EvolutionaryRuntimeSpec` (seed, budget, max_seconds, multi-seed) | TrainingRuntimeSpec |
| **E-D2** | Expression IR for SOO objectives (closed ops, like GP IR) | Dataset/architecture enums |
| **E-D3** | Constraint IR (ineq) on box problems | max_params caps spirit |
| **E-D4** | Strong multi-seed benchmark report (mean/std best_f, HV fixed ref) | dense goldens |
| **E-D5** | Domain adapters: call existing energy/math skills as fitness (no Python inject) | hybrid X2 denser MLP |
| **E-D6** | Promote 1–2 skills toward validated when gates green | neural skill promotion later |

### B.7 `EvolutionaryRuntimeSpec` (proposed)

```python
class EvolutionaryRuntimeSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int = 42
    seeds: list[int] | None = None  # multi-seed matrix; None → [seed]
    budget: BudgetSpec = Field(default_factory=BudgetSpec)
    max_seconds: float | None = None
    max_evaluations: int | None = Field(default=None, ge=1)
    # Reporting
    history: bool = True
    # Multi-obj
    hv_reference: list[float] | None = None  # fixed ref when set; else documented auto
```

Algorithms remain closed enums (`AlgorithmName`, `MultiObjectiveAlgorithmName`,
Nevergrad optimizer names). Runtime does not add free callables.

### B.8 What “more advanced evo” is *not*

- Rewriting NSGA inside OEC (merit stays pymoo).
- Silent fallback to SciPy if pymoo missing.
- Fitness = agent-generated Python.
- Claiming global optimality without budget/diagnostics.

---

## Part C — Aligned priority roadmap

### C.1 Principle

> **Share runtime and governance; specialize capacity/problem IR per family.**

Neural densification and evo depth should land in **paired releases** so the
product story stays coherent: “optional heavy compute, still fail-closed and
auditable.”

### C.2 Suggested sequencing

| Release theme | Neural | Evolutionary | Why together |
|---------------|--------|--------------|--------------|
| **3.4.x design freeze** | this doc | this doc | shared language |
| **3.5.0 “Dense core”** | N-D0 + N-D1 + N-D2 (MLP pilot) | E-D0 + E-D1 (runtime/budget) | same seed/device/budget culture |
| **3.5.x** | N-D3 data refs; N-D4 sequences | E-D2 expression IR SOO | both escape pure toys |
| **3.6.0 “Engineering depth”** | N-D5 GNN/AE; hybrid uses dense MLP | E-D3 constraints; E-D4 multi-seed HV | real problems |
| **Later** | skill promotion gates | E-D5 domain fitness; optional NEAT wave | validated path |

### C.3 Cross-cutting governance (both tracks)

1. Optional extras only (`neural` / `evolutionary`).
2. Closed enums / IR — no agent code inject.
3. `seed` required; report `deterministic_status`.
4. Numbers in agent narrative only with `run_id` (P0 authority).
5. Surrogate / evo optimum ≠ physics law.
6. Pytest markers + extras CI job with timeouts (already sketched).
7. Fingerprints on problem/model/dataset/checkpoint.

### C.4 Success metrics

**Neural dense**

- [ ] `capacity=dense` MLP trains under cap with file checkpoint + sha256
- [ ] Same runtime powers LSTM/TCN golden with `capacity=medium`
- [ ] Default PR CI unchanged; extras job runs dense subset
- [ ] Agent cannot pass arbitrary module paths

**Evolutionary depth**

- [ ] Multi-seed report API stable (mean/std best objective)
- [ ] At least one non-built-in objective via expression IR
- [ ] Fixed HV reference option for ZDT-class tests
- [ ] Documented maturity scores updated in this file when slices land

---

## Part D — API sketch (import surface)

```text
oec.neural.runtime
  CapacityName
  TrainingRuntimeSpec
  DatasetRef
  CheckpointRef
  resolve_capacity(family, capacity) -> dict[str, Any]

oec.kernel.neural.runtime
  run_training(module_factory, data, runtime_spec, task, ...) -> NeuralTrainingResult

oec.evolutionary.runtime
  EvolutionaryRuntimeSpec

oec.kernel.evolutionary.runtime
  run_single(problem, algorithm, runtime_spec) -> EvolutionaryResult
  run_multi(...)
  run_seed_matrix(...) -> BenchmarkResult
```

Existing `train_mlp` / `optimize_single` become thin wrappers during migration
(deprecate internals, keep skill behavior).

---

## Part E — Open decisions (resolve at implement time)

1. **Checkpoint directory:** process cwd vs `OEC_CACHE_DIR` vs temp per run_id?
   Recommendation: `OEC_CACHE_DIR` default `~/.cache/oec/checkpoints/{run_id}`.
2. **Parquet dependency:** add to `neural` extra or support npy-only first?
   Recommendation: npy in N-D3; parquet later if pandas already present (core has pandas).
3. **Expression IR for evo:** reuse GP operator IR vs smaller math subset?
   Recommendation: reuse `gp_operators` allow-list for SOO scalar f(x).
4. **Capacity vs raw knobs precedence:** documented in A.5; freeze in schema tests.
5. **NEAT / topology evolution:** explicit non-goal until after E-D5.

---

## Part F — Doc maintenance

When a slice merges:

1. Tick the checklist in C.4.
2. Bump maturity scores in B.5 if depth moved.
3. Link the PR / commit in CHANGELOG under Neural or Evolutionary.
4. Keep ADR 0031 as governance source of truth; this file is the *density/depth*
   execution design only.

---

## Summary

| Track | Today (3.4) | Design target |
|-------|-------------|----------------|
| Neural | Many arches, toy defaults, split train loops | Shared runtime + capacity presets for **all** arches |
| Evolutionary | Advanced algorithm **names**, toy problems | Keep breadth; grow **depth** (IR, budgets, multi-seed, domain fitness) |
| Alignment | Separate vibes | Paired slices N-D* / E-D* under same governance |

**Next implementation step when approved:** N-D0 + E-D0 (contracts + tables +
unit tests only), then N-D1 MLP pilot on the shared train skeleton.
