# Experiment contract (W2)

**Status:** normative for OEC framework path
**ADRs:** 0034 (layer), 0035 (spec family)

## API surfaces

| Surface | Entry |
|---------|--------|
| SDK | `Engine.run_experiment(spec, *, artifact_root=…, persist_artifacts=…)` |
| CLI | `oec experiment run --spec-file exp.json [--artifact-root DIR] [--persist]` |
| REST | `POST /v1/experiments/run` |
| MCP | `experiment.run` with `{ "spec": {…} }` |

```python
from oec.sdk import Engine

engine = Engine(skills_root="skills")
record = engine.run_experiment({
    "id": "demo",
    "seed": 42,
    "steps": [
        {
            "step_id": "root",
            "skill_id": "mathematics.solve_root",
            "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
        },
        {
            "step_id": "pdf",
            "skill_id": "statistics.distribution_eval",
            "inputs": {
                "distribution": "norm",
                "operation": "pdf",
                "params": {"loc": 0.0, "scale": 1.0},
            },
            "binds_from": [
                {"step_id": "root", "path": "result.root", "as": "x"}
            ],
        },
    ],
    "metrics": [
        {
            "name": "pdf_at_root",
            "path": "result.value",
            "step_id": "pdf",
            "direction": "target",
            "target": 0.24,
            "target_abs_tol": 0.1,
        }
    ],
})
```

## W2.2 — Metrics, gates, binds

1. **Metrics** — resolved only from dotted paths into step `ExecutionResult`s.
2. **Gates** — `ValidationSpec.metric_max` / `metric_min` / `metric_target_abs_tol`;
   `MetricSpec.target` + `target_abs_tol` for TARGET direction.
3. **`binds_from`** — copy prior step execution values into the next step's inputs
   (`step_id`, `path`, `as`).
4. **`require_all_metrics`** — fail when a declared metric cannot be resolved.

## W2.3 — Artifacts

When `artifact_root` is set or `persist_artifacts=True`:

```text
{root}/{experiment_id}/{run_id}/record.json
{root}/{experiment_id}/{run_id}/steps/{step_id}.json
```

Env default root: `OEC_ARTIFACT_ROOT` or `./.oec/artifacts`.

## Rules

1. Each step = one `Engine.run` → one `ExecutionResult`.
2. Metrics never invent numbers.
3. `ExperimentStatus` ≠ `ExecutionStatus`.
4. Seed is provenance-only (not auto-injected into skill inputs).
5. `config_hash` = SHA-256 of canonical JSON of the frozen `ExperimentSpec`.

## ExperimentStatus → process exit (CLI)

| Status | Exit |
|--------|------|
| COMPLETED | 0 |
| VALIDATION_FAILED | 2 |
| ABORTED / INVALID | 3 |
| FAILED | 4 |
