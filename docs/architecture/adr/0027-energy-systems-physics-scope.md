# ADR 0027: Energy-systems physics scope on top of `oec.physics`

- **Status:** Accepted
- **Date:** 2026-08-04
- **Accepted:** 2026-08-04 (Wave 4 closeout — `docs/implementation/v2.6.1-CLOSEOUT.md`)
- **Phase:** v2.6.1 "Energy-rich feature release" (`docs/implementation/v2.6.1-EXECUTION-PLAN.md`, decisions D3–D8)

## Context

v2.6.0 delivers the Physics Foundation P1–P5 v0: platform `oec.physics` + domain objects + conservation ownership (`oec.physics.conservation` per ADR 0024 §4) + units/tolerance policy (ADR 0025) + multidomain scope P1–P5 (ADR 0026). Energy-rich functionality (storage/PV/hybrid/grid-zero/service_metrics) was explicitly deferred to v2.6.1 per ADR 0026 §2 and the sibling `v2.6.1-EXECUTION-PLAN.md`.

An independent Codex audit (`docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md` §C) raised six risks against the original v2.6.1 draft:
1. Patch release too large semantically (5 modules + skills + specialist) — more minor/feature than patch
2. SOC naming: `soc_update` in `kernel/energy/metrics.py` integrates **power×time / capacity** (energy counting), not coulomb-counting by current/Ah
3. "min storage for autonomy" is not a pure analytical helper — becomes temporal/optimization problem; boundary with `optimization.lp` needs explicit contract
4. Migration of existing skills (`energy.balance`, `battery.soc_step`) = unnecessary churn — adapters first
5. Three possible owners of balance/conservation (`physics.balance`, `physics.conservation`, `kernel.energy.metrics`) — must decide in ADR, not implementation
6. Version convention inconsistent (`2.6.1` vs `2.6.1.0`) — standardize `2.6.1`

This ADR closes those risks before Wave 1 implementation.

## Decision

### 1. Scope: energy systems rich — single slice on top of 2.6.0 platform

| Included in 2.6.1 | Excluded (already in 2.6.0 or future) |
|-------------------|--------------------------------------|
| `oec.physics.storage` — BESS trajectory, **energy-based SOC** (`energy_based_soc_update`), η_c/η_d, clip, multi-step; wraps/extends `kernel.energy.metrics.soc_update` | Platform `oec.physics` + domain objects (2.6.0) |
| `oec.physics.pv` — generic PV model v0: irradiance × area × efficiency **or** pre-computed PV power/energy series | P1–P5 multidomain foundation (2.6.0) |
| `oec.physics.hybrid` — multi-period: LOAD = PV + grid + discharge − charge | Multiphysics coupling (2.7) |
| `oec.physics.grid_zero` — **only** `grid_zero_feasibility` helpers (deterministic evaluation of a **provided** trajectory) | Cell electrochemistry (2.8 C4) |
| Skill/composition `energy.min_storage_capacity` — **optimization** problem (horizon, curtailment, η) via `optimization.lp` | Pricing, proprietary tariffs, commercial scoring |
| `oec.physics.service_metrics` — energy delivered, autonomy hours (EaaS as **public concept**) | New MCP tools |
| **New** thin skills `energy.*` / `battery.*` + Energy Specialist demos; **adapters** over kernel | Migration of legacy `energy.balance` / `battery.soc_step` → post-2.6.1 (after proven parity) |

Justification (factual in repo):
1. Energy Specialist + skills already exist: `energy.balance`, `energy.load_metrics`, `battery.soc_step`, `timeseries.power_to_energy`; demos for balance/SOC/electrical
2. Lean kernel `kernel/energy/metrics.py` (`energy_balance`, `soc_update`, `load_metrics`) is the correct base for **wrap/adapter**, not fork
3. Benchmarks and OEC thesis (multi-period microgrid PV+BESS+load+grid) gain conservation/autonomy physical checks **beyond** LP (`optimization.lp`)
4. Fits under prefixes already mapped to `kind: "energy_result"` — minimal envelope impact (ADR 0023 / schema 1.1 inherits `energy_result`)

### 2. Location: modules **inside** `oec.physics` (not new top-level package)

| Option | Verdict |
|--------|---------|
| New `oec.energy_systems` top-level | **Rejected** — fragments physics library |
| **Modules `oec.physics.{storage,pv,hybrid,grid_zero,service_metrics}`** (+ `balance` only if real gap vs conservation) | **Accepted** |
| Skills only without reusable core | **Rejected** — violates skill-thin / reuse principle |

Layering (inherited from 2.6.0):
```
Skills energy.* / battery.* (NEW; legacy untouched in 2.6.1)
        ↓
oec.physics.{storage,pv,hybrid,grid_zero,service_metrics}
        ↓
oec.physics (platform, conservation OWNER, units)   ← from 2.6.0 / D5
oec.kernel.energy.metrics                           ← adapter / parity (not rival residual)
oec.kernel.units / oec.modeling.dimensions
optimization.lp / Optimization Specialist           ← min_storage_capacity (not embedded in physics)
```

Import rules (same as 2.6):
- `oec.physics` → may import modeling/kernel/core; **not** mcp/api/agents/skills
- `oec.modeling` **does not** import physics
- Thin skills → only adapt and call physics/kernel
- Dispatch / optimal sizing → Optimization Specialist + `optimization.lp` (physics **does not** reimplement LP)
- Determinism ADR 0004; forbidden names ADR 0008

### 3. SOC naming: **energy-based**, not coulomb-counting — CLOSED

Problem (Codex): `soc_update` in `src/oec/kernel/energy/metrics.py` (~L32–69) integrates **power × time / capacity** (= **energy counting**), not coulomb-counting by current/Ah. The kernel docstring currently says "Coulomb-counting" **imprecisely**.

| Name / concept | Meaning | Verdict |
|----------------|---------|---------|
| **`energy_based_soc_update`** | ΔSOC from power×time×η / energy capacity | **Canonical in `oec.physics.storage`** and 2.6.1 docs |
| `soc_update` (kernel) | Legacy API **untouched** in code this release; docs/parity refer to it as **energy-based** | Wrap/adapter without breaking rename of kernel symbol in 2.6.1 (debt: align kernel docstring in docs-only PR or future patch) |
| **`coulomb_counting`** | Methods by **current / Ah** (∫I dt / Q) | **Reserved** — **not** used for power×time path; out of 2.6.1 minimum unless explicit current input added later |

Action in plan: correct all references to "coulomb-counting" for BESS 2.6.1 → **energy-based SOC**. Factual reference: `metrics.py` L41–44 (docstring) + integration L55–60.

### 4. Grid-zero: **two distinct deliveries** — CLOSED

Problem (Codex): "min storage for autonomy" is **not** a pure analytical helper — becomes temporal/optimization; conflating it with feasibility contaminates boundary with `optimization.lp`.

| Delivery | Type | Where it lives | Contract |
|----------|------|----------------|----------|
| **`grid_zero_feasibility`** | **Deterministic** evaluation of a **provided** trajectory (load/pv/storage/grid series already given) | `oec.physics.grid_zero` + skill `energy.grid_zero_feasibility` | Inputs: trajectories; outputs: feasible?, deficit per period, balance residual, flags; **no** solver; **no** HiGHS |
| **`min_storage_capacity`** | **Optimization** problem (horizon, optional curtailment, η_c/η_d, SOC bounds) | Skill `energy.min_storage_capacity` (or stable name) that **composes** `optimization.lp` / Optimization Specialist | Physics **does not** embed LP; formulates model (vars/constraints/objective) and calls existing optimization path |

Boundary with `optimization.lp` (contract):
1. Physics may expose **helpers for residual / feasibility / deficit** and builders of **instance data** (coefficients, bounds) if reusable and deterministic
2. **Any** capacity minimization / optimal dispatch / sizing → **Optimization Specialist + skill optimization path**, not `oec.physics.*` calling HiGHS directly
3. Smoke W3: at least one **feasibility** exercise (physics) and, if schedule allows, one **min capacity** via LP; feasibility does **not** count as "solved sizing"

### 5. Ownership of balance/conservation — INHERITED from v2.6 D5; CLOSED in ADR 0027

**Do not reopen** this question in 2.6.1 implementation.

| Role | Owner | In 2.6.1 |
|------|-------|----------|
| Generic multi-domain conservation | **`oec.physics.conservation`** (2.6.0) | **Single owner** of generic residual |
| Fine-grained energy balance | `kernel.energy.metrics.energy_balance` | **Adapter/consumer**; parity; may thin-wrap conservation if needed **without** second formula |
| `oec.physics.balance` | Only if real API gap vs conservation | Optional; if created, **delegates** to conservation — never reimplements residual |

**ADR 0027** explicitly records: *ownership closed per v2.6 D5 / ADR 0024; this ADR does not introduce a rival owner.*

Tolerances: inherit `atol + rtol×scale` + unit (2.6 D5 / ADR 0025). Overlaps with `energy_balance(..., tolerance=)` legacy: parity documented; kernel evolution = debt, not reopening owner.

### 6. No legacy skill migration in 2.6.1 — CLOSED

| Legacy skill | In 2.6.1 | After |
|--------------|----------|-------|
| `energy.balance` | **Untouched** (goldens intact); physics exposes parallel adapter/API if needed | Thin-wrap migration **only** after proven parity + release notes — **later release** (e.g. 2.6.2 or closeout note) |
| `battery.soc_step` | **Untouched**; new skill `battery.soc_trajectory` / energy-based path in physics | Same |
| **New** skills | `energy.hybrid_balance`, `energy.grid_zero_feasibility`, `energy.min_storage_capacity`, `energy.pv_power`, `energy.service_metrics`, optional `battery.soc_trajectory` | — |

Justification (Codex): migration = skill versioning churn without need; adapters first reduce risk.

### 7. Version vs scope: **2.6.1 is a feature release** — CLOSED

| Option | Description | Verdict |
|--------|-------------|---------|
| **(a) chosen** | Keep **`2.6.1`** but declare **explicitly** as **feature release** (despite patch SemVer): 5 modules + new skills + specialist + LP composition | **Accepted** |
| (b) | Bump to **2.7** and shift multiphysics | **Rejected** — V3 §11 reserves 2.7 for multiphysics; renumbering contaminates roadmap |

Implications:
- CHANGELOG / release note: section **"Feature release (patch number)"** — list modules and skills; don't pretend "bugfix only"
- Strict SemVer: patch number is **sequencing legacy** after 2.6.0 foundation; **content** is minor/feature
- **Never** use `2.6.1.0` anywhere (docs, tags, pyproject)

### 8. Power signal conventions (freeze in ADR 0027)

| Signal | v0 Convention |
|--------|---------------|
| Storage power | `power > 0` **charges**; `power < 0` **discharges** (aligned with `metrics.soc_update`) |
| Grid | import > 0 from grid; export as negative term or separate field — **pick one** in ADR and schemas, don't mix |
| Hybrid residual | LOAD − (PV + grid_import + discharge − charge − grid_export…) = 0 under feasible trajectory |
| SOC | fraction [0, 1] of **energy capacity** in energy-based path |

### Pre-conditions (hard)

| Check | Passes if |
|-------|-----------|
| Release 2.6.0 | Claim/tag `2.6.0` or release branch merged with 2.6 DoD (Foundation) satisfied |
| Platform | `import oec.physics` + domain objects + units helpers + **conservation owner** available |
| Envelope | Wrap-once intact; schema ≥1.0 with `energy.` / `battery.` → `energy_result` (1.1 OK) |
| Suite | Full green on 2.6.0 baseline |

### Interdependence with envelope / AA

- Skills `energy.*` / `battery.*` → `kind: "energy_result"` (**already** in map)
- Prefer **no** new `physics.*` prefix for this slice
- `authoritative_answer.values` = `execution.result` verbatim; 0 double-wrap
- If any skill id falls outside energy/battery prefixes → register kind **before** smoke

---

## Non-goals (this release)

- Reopen / expand P1–P5 depth beyond platform reuse
- Multiphysics coupling (v2.7)
- Cell electrochemistry (v2.8 C4) — BESS here is **generic energy-based SOC**, not cell model or coulomb-by-Ah
- AC power flow / machines
- Model Registry / Scientific IR (v2.9)
- Envelope AA on REST/SDK/CLI (D-CUR-27)
- Packaging `agents/` → `src/oec/agents` (D-CUR-21)
- Pricing, TOU commercial, private scoring, forbidden names
- New MCP tools
- **Migration** of `energy.balance` / `battery.soc_step` (later release)
- Reopen conservation ownership / second residual

---

## Consequences

- Skills across energy-rich slice share one place for storage/PV/hybrid physics and one place for conservation checking (inherited), instead of each skill re-deriving balance/residual logic
- Envelope taxonomy grows in versioned, backward-compatible way (already `energy_result` in map) — no invisible enum mutation
- Conservation results auditable via single owner (`oec.physics.conservation`) with documented tolerance policy (`atol + rtol×scale`)
- A domain that has not had its canonical unit/tolerance defaults in Wave 2 table (ADR 0025) cannot ship a conservation check claiming a default — must extend table or pass explicit `atol`/`rtol`/`scale`
- Residual: whether `kernel.energy.metrics.energy_balance` is ever rewritten to call `oec.physics.conservation` directly, and whether v2.7 multiphysics changes how `ConservationCheck` composes across domains, remain open for later releases

---

## References

- `docs/implementation/v2.6.1-EXECUTION-PLAN.md` §0 (D3–D8), Wave 0–4, §16 (DoD), §18 (ADR table)
- `docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md` §C risks 1–6
- ADR 0024 (physics library architecture, conservation ownership)
- ADR 0025 (physics units and dimensional API, tolerance policy)
- ADR 0026 (Physics Foundation multidomain scope, energy-rich deferral)
- ADR 0023 (authoritative-answer envelope, wrap-once, kind taxonomy)
- `schemas/authoritative_answer.schema.json` (enum, version)
- `src/oec/kernel/energy/metrics.py` (`soc_update`, `energy_balance`)

---

*ADR 0027 accepted 2026-08-04 — Wave 4 energy-rich feature release closeout.*
