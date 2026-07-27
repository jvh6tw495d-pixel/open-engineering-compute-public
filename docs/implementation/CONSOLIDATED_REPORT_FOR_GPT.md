# OEC — Consolidated report for GPT

**Date:** 2026-07-26 (baseline) · **Status addendum:** 2026-07-27
**Product:** Open Engineering Compute (OEC)
**Purpose:** Single document for external GPT review of product thesis, plan delivery, and empirical LLM vs OEC experiments.
**Incubation repo:** local private tree (no public remote required to read this file).

> **Construction handoff (current):** [GPT_CONSTRUCTION_HANDOFF.md](GPT_CONSTRUCTION_HANDOFF.md)
> Package **`2.0.0` Scientific Kernel done**. GPT builds **v2.1+**; Grok validates gates.
> Refresh Graphify: `uv tool run --from graphifyy graphify update .`

---

## 0. One-paragraph summary

OEC is **agent-oriented scientific infrastructure**: specialists formulate problems; OEC validates and executes versioned **skills** with provenance; numerical merit stays with **SciPy / NumPy / pandas / HiGHS**. The GPT construction plan (Alpha S0′–S9′ + Roadmap B S10–S26) is **implemented in code** (~40 skills, 5 agents). **v1.5** private alpha and **v2.0** Scientific Kernel (`oec.core.ScientificResult`, ADR 0019) are **closed**. Independent Opus review findings were closed. A **Public Alpha sibling tree** was prepared and validated without push. Empirical benchmarks on a **6-period BESS + TOU LP** show **weak local LLMs fail** when solving alone (scores ~0–2/10) but reach **10/10** when they only extract parameters and **OEC multi-agent + HiGHS** owns numerics—supporting the thesis that OEC supplies **method + guaranteed, auditable results**.

---

## 1. Product thesis

```text
LLM / user
  → Specialist agents (formulate OPS / skill inputs; never invent numbers)
  → OEC Skill Engine (schema, validation, sandbox, ExecutionStatus, provenance)
  → Backends (SciPy / NumPy / pandas / HiGHS)
  → Scientific Reviewer (audit OPS + ExecutionResult)
```

| Principle | Meaning |
|---|---|
| Agent formulates | Missing data listed; no silent invention of optima |
| OEC computes | Only `ExecutionResult` is scientific truth |
| Backend ≠ contract | Skills/OPS are the API; HiGHS/SciPy are engines |
| Public / private | No commercial BTM dispatch IP in public skills (ADR 0008) |
| No `success: bool` | Graded status (ADR 0007) |

---

## 2. Plan delivery status (GPT roadmap)

### 2.1 Alpha S0′–S9′

| Sprint | Delivery |
|---|---|
| S0′–S2′ | Baseline, provenance (`input_hash`, `backends[]`), hardening |
| S3′–S6′ | HiGHS adapter, OPS v0.1, `optimization.lp` / `milp` |
| S7′ | `optimization.check_feasibility`, `optimization.scenario_batch` |
| S8′–S9′ | Optimization Specialist + Scientific Reviewer |

### 2.2 Roadmap B S10–S26

| Phase | Delivery |
|---|---|
| B1 Time | `timeseries.*` incl. timegrid, quality (outliers, clip, normalize, rolling) |
| B2 Math | linear, numerical ODE/roots, stats, Monte Carlo |
| B3 Energy | balance, load metrics, battery SOC step (generic) |
| B4 Finance | simple returns, max drawdown, historical VaR (public only) |
| B5 Agents | Math, Time-Series, Energy specialists |
| B6 Opt advanced | QP, NLP, multiobjective weighted sum |

**Catalog size:** ~**40** experimental skills @ 0.1.0.
**Interfaces:** SDK, CLI, REST, MCP.
**Optional not required for DoD:** CasADi/IPOPT, live LLM inside specialists, sparse LA.

### 2.3 Ops / governance follow-ups (done)

| Item | Status |
|---|---|
| Opus review F1–F5 | Closed (ADR 0018, agent metrics harness, plan DoD, convert tests) |
| Agent metrics §7 | `benchmarks/agent_metrics.py` (gates green) |
| Public Alpha local tree | `open-engineering-compute-public-2026-07-26`, 800 tests, **no push** |
| pandas core / B sequencing | ADR 0018 |

---

## 3. Empirical thesis: LLMs with vs without OEC

### 3.1 Problem (complex, multi-agent)

**6-period microgrid + BESS under time-of-use prices** (awkward decimals):

| Parameter | Value |
|---|---|
| LOAD | `[3.1, 2.4, 1.6, 2.15, 2.35, 2.1]` → sum **13.7** MWh |
| PV | `[0.0, 1.45, 2.55, 1.35, 0.65, 0.25]` → sum **6.25** MWh |
| PRICE | `[1.15, 0.55, 0.28, 0.42, 0.95, 1.35]` |
| CAP / PMAX / SOC0 | **3.75** / **1.35** / **1.85** MWh |

**Physics/optimization:**

- Balance each period: `LOAD = PV + grid + discharge − charge`
- SOC: `s[t] = s[t−1] + charge − discharge`, bounds `[0, CAP]`
- Charge/discharge ≤ PMAX; grid ≥ 0; η = 1
- **Minimize** `Σ PRICE[t] · grid[t]`
- Trap: if CAP were 0.5 with SOC0=1.85 → **infeasible**

### 3.2 OEC multi-agent method (oracle)

| # | Agent | Skill | Role |
|---|---|---|---|
| 1 | Time-Series Specialist | `timeseries.timegrid` | period grid |
| 2 | Energy Specialist | `energy.load_metrics` | peak, load factor |
| 3 | Energy Specialist | `energy.balance` | day residual / deficit |
| 4 | Optimization Specialist | `optimization.lp` | multiperiod BESS LP (**HiGHS**) |
| 5 | Scientific Reviewer | checklist | OPS + ExecutionResult audit |
| 6 | Engine | `optimization.check_feasibility` | CAP trap |

### 3.3 Oracle numerics (from ExecutionResult only)

| Metric | Value |
|---|---|
| `min_tou_cost` | **4.2825** |
| `total_grid_mwh` | **5.6** |
| `grid_trajectory` | `[1.75, 0.45, 0.40, 2.15, 0.35, 0.50]` (approx) |
| `deficit_mwh` | **7.45** |
| `peak_load_mwh` | **3.1** |
| `load_factor` | **~0.737** |
| `reviewer_passed` | **true** |
| `impossible_cap_feasible` | **false** |
| Backend | **highspy / HiGHS** |
| Provenance | `run_id`, `input_hash`, `solver_status=optimal` |

### 3.4 Experimental arms

| Arm | Model role | Who owns numerics | Auditable |
|---|---|---|---|
| **A — without OEC** | Free-solve full problem in JSON | LLM weights | **No** |
| **C — with OEC** | Extract only LOAD/PV/PRICE/CAP/PMAX/SOC0 | **OEC multi-agent + HiGHS** | **Yes** |

Scoring: 10-point rubric (sums, deficit, peak, LF, min cost, totals, trap feasibility, grid trajectory L1 ≤ 1.0).

### 3.5 Results (thesis run 2026-07-26)

| Model | Provider | **A without OEC** | **C with OEC** | Δ | A cost | C cost |
|---|---|---|---|---|---|---|
| llama3.1:8b | Ollama | **2/10** | **10/10** | **+8** | 14.45 | **4.2825** |
| nemotron-3-nano:4b | Ollama | **0/10** | **10/10** | **+10** | invalid JSON | **4.2825** |
| qwen2.5:7b-instruct | Ollama | **2/10** | **10/10** | **+8** | 8.175 | **4.2825** |
| Claude Opus | Claude CLI | **8/10** | **10/10** | **+2** | 4.3475 | **4.2825** |
| **OEC oracle (no LLM)** | OEC | — | **10/10** | — | — | **4.2825** |

**Aggregate:**

| Metric | Without OEC (A) | With OEC (C) |
|---|---|---|
| Mean score | **~3.0 / 10** | **10.0 / 10** |
| Correct min cost | **0–1 / 4** models (Opus close but not exact) | **4 / 4** (exact 4.2825) |
| Provenance | None | `run_id` + solver status + reviewer |

**Claude Sonnet:** not scored in thesis run (CLI timeout historically); Opus included.

### 3.6 Interpretation for product

1. **Weak/local LLMs alone cannot be trusted** for multiperiod storage dispatch optima (wrong cost, wrong trajectories, broken JSON).
2. **Same weak models + OEC** become reliable **if** they only fill parameters: method is fixed in skills; **HiGHS guarantees** the LP.
3. **Strong models** (Opus) may nearly solve small LPs mentally (**8/10**, cost 4.3475 ≈ 4.2825) but still:
   - miss exact optimum / trajectory sometimes;
   - produce **no scientific audit trail**.
4. OEC value is not “smarter chat”—it is **method + verification + provenance**.

---

## 4. Supporting simpler experiment (BESS size)

Single-period aggregates (load 13.7, UFV 6.25):

| Arm | Llama 3.1 8B |
|---|---|
| Alone | Score **2/4** (deficit OK; BESS min hallucinated as 0) |
| Params + fixed OPS + OEC | Score **4/4**, BESS min **7.45** MWh |

Report: `docs/implementation/LLAMA_VS_OEC_REPORT.md`.

---

## 5. Why cheating is hard (evaluation design)

| Trap | Purpose |
|---|---|
| Awkward decimals (13.7 / 6.25 / 3.75…) | Blocks “14−7=7” memorization |
| Multiperiod SOC coupling | Blocks naive one-shot energy deficit as “dispatch” |
| TOU objective | Optimal grid ≠ constant residual allocation |
| Trajectory match | L1 vs HiGHS vector |
| CAP=0.5 feasibility trap | SOC0 > CAP ⇒ infeasible |
| Provenance requirement | Correct number without `run_id` ≠ full credit in process scoring |

---

## 6. Architecture pointers

| Path | Content |
|---|---|
| `docs/implementation/OEC_IMPLEMENTATION_PLAN.md` | Canonical plan + DoD |
| `docs/architecture/adr/0018-*.md` | Sequencing + pandas core |
| `benchmarks/agent_metrics.py` | Agent gates (invented numbers = 0) |
| `agents/` | Specialists (outside core wheel) |
| `skills/` | Executable skill packages |
| `scripts/multiagent_with_without_oec.py` | Thesis harness A vs C |
| `scripts/multiagent_llm_benchmark.py` | Multi-model freeform benchmark |
| `scripts/llama_oec_experiment.py` | Simple BESS A vs template+OEC |
| `docs/implementation/THESIS_LLM_WITH_WITHOUT_OEC.md` | Full thesis report |
| `docs/implementation/MULTIAGENT_LLM_BENCHMARK.md` | Multi-LLM freeform scores |
| `docs/implementation/public-alpha-prep-report.md` | Public tree prep (no push) |
| `docs/implementation/REPORT_FOR_GPT_2026-07-26.md` | Earlier plan-status report |

---

## 7. Public Alpha (status)

| Item | Status |
|---|---|
| Incubation remotes | Empty |
| Forbidden-name gate | Green |
| Tests (incubation / public tree) | **800 passed**, ~91% coverage |
| Sibling public tree | `…/open-engineering-compute-public-2026-07-26` clean history (1 commit) |
| Public remote + push | **Not done** (human step) |

---

## 8. Claims vs non-claims

### Claims supported by this work

- GPT plan skills/agents largely **delivered**.
- OEC can run a **multi-agent scientific pipeline** with audit trail.
- On a multiperiod BESS/TOU instance, **weak LLMs alone fail**; **with OEC they match oracle** when params are correct.
- Separation “formulate vs compute” is **empirically useful**.

### Non-claims

- OEC does not replace domain expertise or data quality.
- Public catalog does **not** include proprietary commercial dispatch products.
- Opus matching oracle once ≠ LLMs are safe as sole solvers for engineering claims.
- Public internet publish is **not** completed.

---

## 9. Suggested questions for GPT

1. Does the A vs C design fairly test the thesis, or should Arm C force the model to emit full OPS (harder extraction)?
2. Should scoring **require** provenance for “full marks” even if freeform numerics match?
3. Is multiperiod T=6 enough complexity, or recommend T=24 + efficiency & binary charge/discharge for the next paper-style eval?
4. Product packaging: keep `agents/` outside the wheel forever, or optional `oec[agents]`?
5. Any missing public skill that would strengthen “method completeness” for microgrid demos?

---

## 10. Reproduce

```bash
# Thesis A vs C
uv sync --extra optimization
# Ollama models: llama3.1:8b, nemotron-3-nano:4b, qwen2.5:7b-instruct
uv run python scripts/multiagent_with_without_oec.py --skip-claude
# with Claude CLI configured:
uv run python scripts/multiagent_with_without_oec.py

# Freeform multi-LLM benchmark
uv run python scripts/multiagent_llm_benchmark.py --skip-claude
```

---

## 11. Bottom line for GPT

| Layer | Verdict |
|---|---|
| **Plan build-out** | Closed in incubation code |
| **Thesis (weak LLM vs OEC)** | **Supported** by measured A≪C scores on multiperiod BESS/TOU |
| **OEC role** | Method (skills/agents/OPS) + guarantee (solver + status + hash + reviewer) |
| **LLM role** | Formulation / parameter extraction / UX — not sole numerical authority |

> **LLMs propose; OEC disposes—and can prove what it did.**

---

*End of consolidated report — 2026-07-26*
