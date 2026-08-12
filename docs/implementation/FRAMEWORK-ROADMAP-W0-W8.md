# OEC Framework Roadmap W0–W8

**Status:** active (W0 freeze landed)
**Baseline:** `oec==3.4.1` · 131 skills · skill-first engine
**Priority:** **W0 → W1 → W2**
**Normative layers:** [`docs/architecture/OEC-FRAMEWORK-LAYERS.md`](../architecture/OEC-FRAMEWORK-LAYERS.md)
**ADRs:** [0034 Experiment Layer](../architecture/adr/0034-experiment-layer.md) ·
[0035 Spec Family](../architecture/adr/0035-scientific-spec-family.md)

---

## Frozen sequence

```text
W0  Architecture Freeze          ✅ contracts + docs + specs stubs
 ↓
W1  Scientific Core (no AI)      ✅ MVP: distributions, hypothesis, jacobian, pde_1d_heat
 ↓
W2  Experiment Engine            ✅ MVP: run_experiment sequential + metrics + CLI
 ↓
W3  Applied Sciences             physics → chemistry → engineering apps
 ↓
W4  Neural Computing             re-homologate existing skills under Experiment
 ↓
W5  Evolutionary Computing       re-homologate + NEAT later
 ↓
W6  Foundation Models            Transformers/PEFT behind contracts
 ↓
W7  Hybrid scientific experiments
 ↓
W8  Hardening / OEC 3.x product surfaces

POST-OEC (not this repo): Persistent Scientific Harness
```

---

## Diagnosis (3.4.1)

| Need | State |
|------|--------|
| Skill engine + `ExecutionResult` | Mature — do not break |
| Spec family (Experiment, Metric, Artifact, …) | **W0 stubs** in `src/oec/experiment/specs.py` |
| Experiment runner | Absent → **W2** |
| Scientific core without AI | Partial — missing distributions, hypothesis tests, PDE, symbolic skills |
| Neural / evolutionary skills | Advanced (26 + 15) — **re-homologate** in W4/W5, do not rewrite |
| Foundation models | Absent → W6 only after W2+W4 |

### Dependency rules

```text
Core  ↛  ML/AI
ML/AI  →  Core
External backend  ≠  public OEC API
```

---

## W0 — Architecture Freeze (this release slice)

| Deliverable | Path |
|-------------|------|
| Framework layers | `docs/architecture/OEC-FRAMEWORK-LAYERS.md` |
| ADR 0034 | `docs/architecture/adr/0034-experiment-layer.md` |
| ADR 0035 | `docs/architecture/adr/0035-scientific-spec-family.md` |
| Spec stubs | `src/oec/experiment/specs.py` |
| Tests | `tests/unit/test_experiment_specs.py` |
| Architecture entry | `ARCHITECTURE.md` |

**Done when:** specs JSON round-trip; no skill behavior change; Core ↛ ML verified by package imports (experiment package has no torch).

---

## W1 — Scientific Core (no AI)

**Goal:** honest core install without neural/evo extras.

| Priority | Gaps |
|----------|------|
| P0 | `statistics.distribution_eval`, `statistics.hypothesis_test` |
| P0 | Jacobian/Hessian; `numerical.pde_1d_heat` (FDM foundation) |
| P1 | SymPy skills via AST whitelist (no free `sympify`) |
| P1 | Multivariate unconstrained opt; ε-constraint multiobjective |

Backends: NumPy, SciPy, SymPy, Pint — all behind OEC skills/contracts.

---

## W2 — Experiment Engine

**Goal:** universal scientific run contract.

```python
record = engine.run_experiment(experiment_spec)
# each step → Engine.run → ExecutionResult
```

| Sub | Delivery |
|-----|----------|
| W2.0 | package + specs (started in W0) |
| W2.1 | sequential runner + `ExperimentRecord` |
| W2.2 | metrics + validation gates |
| W2.3 | artifact store + CLI |
| W2.4 | REST/MCP thin surface |

**Rules:** no invented numbers; no arbitrary Python steps; sequential v0 only.

---

## W3–W8 (summary)

| Wave | Focus |
|------|--------|
| **W3** | Physics / chemistry depth; engineering as applications of foundations |
| **W4** | Re-homolog neural under Experiment; schedulers/artifacts; no HF yet |
| **W5** | Re-homolog evo; NEAT/HyperNEAT; hybrid steps with W4 |
| **W6** | `oec[foundation]` — transformers/peft behind contracts |
| **W7** | Canonical hybrid ExperimentSpecs (physics→surrogate→evo, …) |
| **W8** | SDK/CLI/REST/MCP polish, promotion policy, correctness benchmarks |

---

## Immediate execution (sprints)

| Sprint | Work |
|--------|------|
| **A (done in W0)** | Layers, ADRs, specs, tests |
| **B** | W1-MVP: distributions + hypothesis tests + 1 PDE |
| **C** | W2-MVP: `run_experiment` sequential + metrics + e2e |

Do **not** start Transformers, NEAT productization, or a persistent harness before **W2-MVP gate**.

---

## Versioning suggestion

| Milestone | Version hint |
|-----------|--------------|
| W0–W2 | `3.5.x` |
| W4 re-homolog | `3.6.x` |
| W6 foundation | `3.7+` or `4.0` if breaking public imports |

`ExecutionResult` shape remains frozen across all waves (ADR 0007 / 0031).
