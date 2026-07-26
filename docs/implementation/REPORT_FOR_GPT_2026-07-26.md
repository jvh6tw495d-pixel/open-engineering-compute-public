# OEC — Status report for GPT review

**Date:** 2026-07-26
**Product:** Open Engineering Compute (OEC)
**Incubation repo:** local private tree (no git remote)
**Audience:** external GPT review of plan vs delivery

---

## 1. Executive summary

OEC was advanced from a partial Alpha of skills + interfaces into a full **agent-oriented scientific infrastructure**:

- **Compute merit:** SciPy / NumPy / pandas / HiGHS (not rebranded as OEC algorithms).
- **OEC role:** skill contracts, validation, provenance, execution status (ADR 0007 — no `status: success` bool).
- **Agents role:** formulate OPS / skill inputs; narrate **only** from `ExecutionResult` (no invented numbers).
- **Public/private:** ADR 0008 separation; forbidden-name gate; Public Alpha = **new tree + clean history**, not push of incubation.

**Verdict on the GPT construction plan (S0′–S9′ Alpha + Roadmap B S10–S26):**

| Layer | Status |
|---|---|
| Skills + kernels + agents in code | **Closed** (~40 skills, 5 agents) |
| Opus review findings F1–F5 | **Closed** (+ residual R1–R3) |
| Local Public Alpha tree | **Prepared & validated** (no remote/push) |
| Public remote publish | **Not done** (human step remaining) |

Local gate (incubation + public tree): **800 tests passed**, coverage **~91%**, ruff/mypy green, forbidden-names **0 hits**.

---

## 2. Product thesis (unchanged)

```text
LLM / user
  → Specialist agents (formulate OPS / skill inputs)
  → OEC Skill Engine (validate + execute + provenance)
  → Backends (SciPy / NumPy / pandas / HiGHS)
  → Scientific Reviewer (audit OPS + ExecutionResult)
```

Rules:

1. Agent formulates; OEC validates and executes.
2. Narrative cites only `ExecutionResult` fields.
3. No private commercial dispatch / proprietary scoring in the public catalog.
4. Backend ≠ public contract.

---

## 3. Map: GPT plan → delivery

### 3.1 Alpha (S0′–S9′)

| Sprint | Intent | Delivery |
|---|---|---|
| S0′ | Baseline / inventory | Skill inventory, commits, hygiene |
| S1′ | Contract + provenance+ | `input_hash`, `backends[]` (ADR 0017) |
| S2′ | Execution hardening | Limits, sandbox docs |
| S3′ | HiGHS | `oec.kernel.optimization.highs` + extra `optimization` |
| S4′ | OPS v0.1 | `oec.ops` schema + validation |
| S5′–S6′ | LP / MILP skills | `optimization.lp`, `optimization.milp` |
| S7′ | Feasibility & scenarios | `optimization.check_feasibility`, `optimization.scenario_batch` |
| S8′ | Optimization Specialist | `agents/optimization_specialist/` |
| S9′ | Scientific Reviewer | `agents/scientific_reviewer/` |

Alpha DoD checkboxes in `docs/implementation/OEC_IMPLEMENTATION_PLAN.md` are marked **complete** (reconciled 2026-07-26).

### 3.2 Roadmap B (S10–S26 reordered)

| Phase | Content | Delivery |
|---|---|---|
| B1 Time | timegrid, align, resample, missing, power↔energy, quality | `timeseries.*` (incl. `timegrid`, outliers, clip, normalize, rolling) |
| B2 Math | linear, ODE, roots, stats, MC | `linear.*`, `numerical.*`, `statistics.*` (incl. `matrix_properties`, `monte_carlo`) |
| B3 Energy | balance, SOC, load metrics (public only) | `energy.*`, `battery.soc_step` |
| B4 Finance | public primitives only | `finance.simple_returns`, `max_drawdown`, `var_historical` |
| B5 Agents | Math / TS / Energy specialists | `agents/applied_mathematics`, `time_series`, `energy` |
| B6 Opt advanced | QP / NLP / multiobjective | `optimization.qp`, `nlp`, `multiobjective` |

**Not implemented (optional / future, not blocking catalog close):**

- Native CasADi / IPOPT (plan: “if needed”; SciPy covers NLP/QP v0).
- Live LLM API inside specialists (prompts exist; demos are deterministic harnesses).
- Sparse linear algebra as first-class skill.

### 3.3 Catalog size

~**40** experimental skills @ 0.1.0 across:

`mathematics`, `electrical`, `timeseries`, `linear`, `numerical`, `statistics`, `optimization`, `energy`, `battery`, `finance`.

Interfaces already present: **SDK, CLI, REST, MCP**.

---

## 4. Agents

| Agent | Path | Role |
|---|---|---|
| Optimization Specialist | `agents/optimization_specialist/` | OPS → LP/MILP → narrate |
| Scientific Reviewer | `agents/scientific_reviewer/` | Independent audit of OPS + result |
| Applied Mathematics | `agents/applied_mathematics/` | Math / linear / stats / ODE demos |
| Time-Series | `agents/time_series/` | `timeseries.*` demos |
| Energy | `agents/energy/` | Public energy / battery / electrical demos |

Shared harness: `agents/common.py` (`SkillSpecialist`, `narrate_execution`).

**Agent metrics harness (plan §7):** `benchmarks/agent_metrics.py`

Measured on controlled golden demos (no live LLM):

- OPS valid on first attempt
- LP/MILP classification accuracy
- Assumptions present
- **Invented-number rate = 0** (narrative numbers ⊆ `ExecutionResult`)
- Reviewer catch rate (invalid OPS / forged objective / bad status claim)

Test gate: `tests/unit/test_agent_metrics.py` (requires `highspy`; CI uses `--all-extras`).

---

## 5. Governance decisions worth knowing

| ADR | Topic |
|---|---|
| 0007 | Graded `ExecutionStatus` (no boolean success) |
| 0008 | Public / private separation |
| 0010 | Graphify artifacts not versioned |
| 0012 | Subprocess sandbox |
| 0017 | Provenance `input_hash` + `backends[]` |
| **0018** | Roadmap B on incubation ratified; pandas stays **core**; HiGHS is **extra** `optimization` |

**Sequencing note (Opus F1):** Roadmap B landed before formal Public Alpha publish. ADR 0018 **accepts** this for incubation; Public Alpha is a **sibling tree with clean history**, not a rollback of B.

---

## 6. Independent review (Claude Opus)

### Round 1 (after skill/agent close)

- Code delivered **more** than the plan required.
- Gaps were process/docs/metrics, not missing skill sprints.
- Findings F1–F5 (sequencing, agent metrics, pandas core, plan drift, convert coverage).

### Round 2 (after F1–F5 fixes)

- F1–F5 **closed** (with small residual R1–R3, later fixed).
- `prepare_public_alpha` **dry-run safe**.
- Real public copy recommended after doc reconciliation (done).

### Residual after R1–R3

- Human license/doc review before any public remote.
- Optional graphify regen in public tree.
- Optional future: CasADi/IPOPT, richer multiobjective, sparse linear.

---

## 7. Public Alpha preparation (done locally)

### Incubation gates

| Check | Result |
|---|---|
| `git remote -v` | **empty** |
| Forbidden names | **0 hits** |
| ruff / mypy | green |
| pytest | **800 passed**, ~91% coverage |
| bandit | exit 0 |
| `uv build` | wheel + sdist |

### Public sibling tree

**Path:**

```text
…/Documentos/open-engineering-compute-public-2026-07-26
```

| Property | Value |
|---|---|
| Git history | **Fresh** — 1 commit `8f7accb` *chore: initial public alpha import (clean history)* |
| Remotes | **none** |
| Forbidden-name scan | 0 hits (649 files) |
| `uv sync --all-extras --all-groups` | ok |
| pytest in public tree | **800 passed** |
| `oec skills list --skills-root skills` | full catalog |

**Included:** `src/`, `skills/`, `tests/`, `agents/`, `benchmarks/`, docs (minus incubation-only paths), integrations, packaging, CI.

**Excluded by design:** incubation git history, `docs/sprints`, `docs/release`, `codebase-map.md`, `graphify-out`, `.venv`, dist, master handbooks.

**Not done:**

1. Human review of licenses / third-party notices.
2. Choice of public remote URL.
3. `git remote add` + **push of the public tree only**.
4. Optional graphify in public tree.

> Do **not** push the incubation repository. Publish only the sibling public tree.

---

## 8. Tooling / documentation side artifacts

| Artifact | Location / note |
|---|---|
| Implementation plan (reconciled) | `docs/implementation/OEC_IMPLEMENTATION_PLAN.md` |
| Skill inventory | `docs/implementation/skill-inventory.md` |
| GPT plan completion report | `docs/implementation/gpt-plan-completion-report.md` |
| Public Alpha prep report | `docs/implementation/public-alpha-prep-report.md` |
| Graphify | `graphify-out/` (~4411 nodes / 6871 edges) — **not in git** (ADR 0010) |
| Obsidian notes | local vault folder `OEC/` (paths not in public docs) |

---

## 9. Recent commits (incubation, illustrative)

```text
5b682f0 docs: record Public Alpha local tree prep (no remote push)
7b9197d fix: sanitize public-alpha gate (forbidden name, mypy) and include agents/
b910eea docs: close Opus re-review residual R1-R3
e413094 fix: address Opus review F1-F5 (ADR 0018, agent metrics, plan DoD)
0134ea3 feat: close GPT plan remainder (S7, S10, S19, S23-S26)
105978a feat: priorities 1-2 — S20-S22 specialists + S11/S13/S15 skills
```

Public tree:

```text
8f7accb chore: initial public alpha import (clean history)
```

---

## 10. Honest “% closed”

| Scope | Closed? |
|---|---|
| GPT plan skills + agents (S0′–S26 / B1–B6) | **Yes** |
| Opus remediation F1–F5 + R1–R3 | **Yes** |
| Local Public Alpha tree + validation | **Yes** |
| Public remote published on the internet | **No** |
| Optional CasADi/IPOPT / live LLM agents | **No** (out of plan DoD) |

**One-line status for GPT:**
*OEC incubation has fully delivered the GPT Alpha + Roadmap B construction plan in code, with independent Opus review addressed, agent metric gates green, and a clean public-alpha sibling repository validated at 800 tests — remaining work is human publish (remote + push), not missing plan sprints.*

---

## 11. Suggested questions for GPT

1. Is the public catalog scope (~40 skills) appropriate for an Alpha tag, or should finance/QP/NLP be marked experimental-only in README packaging?
2. Should `agents/` remain outside the installable wheel (current design) forever, or become an optional extra package?
3. Any missing skill you consider **blocking** for “agent-ready optimization” Alpha that is not covered by `optimization.lp/milp` + feasibility + specialist + reviewer?
4. Review ADR 0018 (B before formal STOP; pandas core) for process risk.
5. Recommend a minimal publish checklist for the first public remote (beyond what is already in the prep report).

---

## 12. File pointers (start here)

| File | Why |
|---|---|
| `docs/implementation/OEC_IMPLEMENTATION_PLAN.md` | Canonical plan + DoD |
| `docs/implementation/skill-inventory.md` | Skill list |
| `docs/architecture/adr/0018-roadmap-sequencing-and-pandas-core.md` | Sequencing + pandas decision |
| `benchmarks/agent_metrics.py` | Agent metrics harness |
| `agents/README.md` | Agent layer overview |
| `docs/implementation/public-alpha-prep-report.md` | Public tree details |
| `scripts/prepare_public_alpha.py` | How the public tree is built |

---

*End of report — 2026-07-26*
