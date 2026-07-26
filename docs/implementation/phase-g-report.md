# Phase G report — specialist agents

**Status:** delivered (v0.1 harness)
**Date:** 2026-07-26

## Delivered

| Agent | Path | Capability |
|---|---|---|
| Optimization Specialist | `agents/optimization_specialist/` | classify LP/MILP, validate OPS, run `optimization.lp`/`milp`, narrate from `ExecutionResult` only |
| Scientific Reviewer | `agents/scientific_reviewer/` | independent checklist on OPS + result; catches forged claims / inconsistent status |

## Design

- Agents live **outside** the core wheel (`agents/`, not `src/oec`).
- Numerical merit remains **HiGHS** (via OEC skills).
- NL→OPS for production LLMs: prompts under `prompts/system.md`;
  automated tests use `demo_ops_from_label` for fixed golden problems.

## Not in v0.1

- Live LLM API calls
- Math / Time-Series / Energy specialists
- Automatic multi-skill non-linear workflows

## Acceptance

- `run_demo("diet")` → optimal obj 1.0 + narrative with `run_id`
- Reviewer passes clean solve; fails forged objective / inconsistent status
