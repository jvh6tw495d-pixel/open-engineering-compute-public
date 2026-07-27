# GPT construction handoff — OEC after v2.0.0

**Date:** 2026-07-27
**Package:** `oec==2.0.0` (private Scientific Kernel alpha)
**Release commit:** `51407ec` · notes: `d43956a`
**Graphify:** regenerate with `uv tool run --from graphifyy graphify update .` → `graphify-out/`
**Role split:** **GPT builds** · **Grok validates** (gates, review, release cuts)

---

## 0. Where we are (roadmap V3)

```text
[x] v0.x – v1.5   Skill Engine + private alpha (~40 skills, 5 agents, OPS, interfaces)
[x] v2.0          Scientific Kernel              ← DONE (this handoff baseline)
[ ] v2.1          Quantities / units / contracts ← YOUR NEXT BUILD
[ ] v2.2          Math IR + modeling             (critical path)
[ ] v2.3          Applied math expansion
[ ] v2.4          Computational + Verification Engine
[ ] v2.5          Mathematics Complete           ← HARD GATE
[ ] v2.6–v2.8     Physics / Multiphysics / Chemistry  (NOT before v2.5)
[ ] v2.9–v3.0     RC + public GitHub
```

**North-star doc:** [OEC_V3_IMPLEMENTATION_PLAN.md](OEC_V3_IMPLEMENTATION_PLAN.md)
**Concept kernel:** [../concepts/scientific-kernel.md](../concepts/scientific-kernel.md)
**ADR kernel:** [../architecture/adr/0019-scientific-kernel.md](../architecture/adr/0019-scientific-kernel.md)

### Explicit non-goals right now

- Physics / Chemistry Complete
- Public GitHub push (v3.0)
- Replacing `ExecutionResult` / REST / MCP shapes
- Private commercial decision engines in public skills (ADR 0008)

---

## 1. Product thesis (do not drift)

```text
LLM / user
  → Specialist agents (formulate OPS / skill inputs; never invent numbers)
  → OEC Skill Engine (schema, validation, sandbox, graded status, provenance)
  → Backends (SciPy / NumPy / pandas / HiGHS)   ← numerical MERIT
  → ScientificResult adapter (optional scientific view) / Reviewer
```

| Principle | Meaning |
|---|---|
| Agent formulates | Missing data listed; no silent invention of optima |
| OEC governs | Versioned skills + validation + provenance |
| Backend owns merit | SciPy/NumPy/HiGHS compute; OEC does not claim their math |
| No `success: bool` | Graded `ExecutionStatus` (ADR 0007) |
| Public / private | Forbidden names + ADR 0008 |
| Core ≠ domain | `oec.core` must not import `skills.*` domains |

---

## 2. What is already shipped (do not rebuild)

### 2.1 v1.5 private operational alpha

- ~40 skills: math, electrical, timeseries, linear, numerical, stats, opt, energy, battery, finance
- OPS v0.1 + HiGHS (`optimization.lp` / `milp`) + feasibility / scenario_batch
- Agents outside wheel (`agents/`): Optimization, Scientific Reviewer, Applied Math, TS, Energy
- SDK / CLI / REST / MCP
- Provenance: `input_hash`, `backends[]` (ADR 0017)
- Gates: pytest unit suite large, ruff/mypy hooks, `scripts/check_forbidden_names.py`
- Public sibling tree prepared locally — **no remote push**

### 2.2 v2.0 Scientific Kernel (`src/oec/core/`)

| Piece | Path / API |
|---|---|
| `ScientificResult` | `scientific_result.py` — adapter over `ExecutionResult` |
| `from_execution_result` | non-mutating map |
| `ValidityDomain` | `validity.py` |
| `Diagnostic` + `diagnostics_from_mapping` | `diagnostics.py` |
| `ProvenanceRecord` | `provenance.py` (`extra="allow"`) |
| Types | `MethodRef`, `BackendRef`, `Assumption` in `types.py` |
| Errors | `ScientificDomainError`, `DimensionalIncompatibilityError`, `BackendUnavailableError`, `UnderdeterminedProblemError`, `OverdeterminedProblemError` |
| SDK | `Engine.run_scientific(...)` → `ScientificResult` |
| Unchanged | `Engine.run` → `ExecutionResult`; REST/MCP still ExecutionResult |

**Tests:** `tests/unit/test_core_scientific_result.py` (10) · full unit ~448 at cut
**Release validation:** [v2.0-release-validation.md](v2.0-release-validation.md)

### 2.3 Residual risks called out at cut (fix if you touch core)

1. Thin coverage of `diagnostics_from_mapping` heuristics
2. `ProvenanceRecord` passthrough not schema-strict
3. Prefer independent validation (Grok) before version bumps

---

## 3. Your construction charter (GPT)

### 3.1 Immediate build: **v2.1 Quantities** (V3 plan §5)

**Do not start by rebuilding `QuantityValue`.** Complete and approve the Q0
inventory first:
[v2.1-quantities-q0-inventory.md](v2.1-quantities-q0-inventory.md).
The repository already has quantity parsing, conversion, central input
normalization and narrow property tests. The remaining work is contract
stabilization and enforceable physical I/O coverage; energy and battery are
confirmed gaps in addition to the electrical audit.

| ID | Delivery | Notes |
|---|---|---|
| Q1 | Stable `Quantity` / dimensions / convert API | Build on `src/oec/kernel/units/` |
| Q2 | Dimensional validation mandatory where skill declares units | Wire validation policy |
| Q3 | Selected SI constants | Small, referenced set |
| Q4 | Uncertainty hooks on Quantity | Can be simple estimators first |
| Q5 | Explicit reject of dimensionally invalid ops | Property tests |
| Q6 | Electrical skills: 100% units on I/O audit | No bare floats where units apply |

**Gate v2.1 (DoD):**

- Property tests for conversion
- Zero bare float in physical skills without unit (lint/doc gate as agreed)
- Does **not** require Math IR
- Version bump only after green suite + Grok validation

### 3.2 Then (in order — do not skip)

1. **v2.2 Math IR v0** — symbols, expressions, equations, linear systems/objectives; compile → backend
2. **v2.3 Applied math** — expand catalog (control, decision, Pareto/CVaR, forecast, sparse, DAE, …)
3. **v2.4** Backend registry + Verification Engine formalization
4. **v2.5 Mathematics Complete** — hard product gate (plan §9)

**Forbidden early:** deep Physics/Chemistry before v2.5.

### 3.3 Working rules

1. **Additive first** — prefer adapters over breaking ExecutionResult
2. **No domain imports in `oec.core`**
3. **Numbers only from OEC runs** in agents/demos
4. **Forbidden names** must stay clean (`scripts/check_forbidden_names.py`)
5. **Commit with hooks green** (ruff, ruff-format, mypy)
6. **Update Graphify** after structural work:
   `uv tool run --from graphifyy graphify update .`
7. **Do not push public remote** without explicit human decision
8. When stuck on design: write short ADR draft; do not silently invent contracts

---

## 4. Validation protocol (call Grok)

Before any minor/major version cut (`2.1.0`, `2.2.0`, …):

| Check | Owner |
|---|---|
| Scope vs this handoff / V3 plan | Grok |
| Tests + ruff + mypy + forbidden-names | Grok or CI |
| ExecutionResult / REST / MCP unbroken | Grok |
| Core domain-independence | Grok |
| CHANGELOG / README honesty | Grok |
| Graphify refresh present locally | Builder (GPT) |

**Trigger phrase for user:** “Grok, valida o X.Y” → Grok does not rebuild; Grok gates.

---

## 5. Key paths (navigation)

| Area | Path |
|---|---|
| Scientific Kernel | `src/oec/core/` |
| Units (v2.1 base) | `src/oec/kernel/units/` |
| Numerics AST | `src/oec/kernel/numerics/` |
| Optimization + HiGHS | `src/oec/kernel/optimization/`, `src/oec/ops/` |
| Execution | `src/oec/execution/` |
| Validation | `src/oec/validation/` |
| Skills | `skills/**` |
| Agents | `agents/**` |
| V3 plan | `docs/implementation/OEC_V3_IMPLEMENTATION_PLAN.md` |
| Prior GPT reports | `CONSOLIDATED_REPORT_FOR_GPT.md`, `REPORT_FOR_GPT_2026-07-26.md` |
| Graphify how-to | `docs/development/graphify.md` |
| Codebase map | `docs/development/codebase-map.md` |

---

## 6. Suggested first PR sequence for GPT

1. Inventory `kernel/units` + electrical unit coverage gaps (doc only)
2. Q1 Quantity API + tests (property)
3. Q2 wire dimensional policy
4. Q5 invalid ops rejection
5. Q3–Q4 constants + uncertainty hooks
6. Q6 electrical audit fixes
7. CHANGELOG + version `2.1.0` **only after Grok validation**

---

## 7. Graphify memory snapshot (indexed by update)

**Nodes of interest after v2.0:**

- package `oec.core` (new community hub)
- `ScientificResult` / `from_execution_result`
- `Engine.run_scientific`
- ADR 0019
- this handoff + V3 plan §4–§5

**Query hints for GPT after graph rebuild:**

```text
graphify query "ScientificResult adapter ExecutionResult"
graphify query "units Quantity dimensional validation"
graphify god-nodes
```

---

*End of handoff. GPT owns construction from v2.1; Grok owns validation gates.*
