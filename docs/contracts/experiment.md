# Experiment contract (W2-MVP)

**Status:** normative for OEC 3.5+ framework path
**ADRs:** 0034 (layer), 0035 (spec family)

## API

```python
from oec.sdk import Engine
from oec.experiment import ExperimentSpec, ExperimentStep, MetricSpec

engine = Engine(skills_root="skills")
record = engine.run_experiment(ExperimentSpec(
    id="demo",
    seed=42,
    steps=(
        ExperimentStep(
            step_id="describe",
            skill_id="statistics.describe",
            inputs={"values": [1.0, 2.0, 3.0]},
        ),
    ),
    metrics=(
        MetricSpec(name="mean", path="result.mean", step_id="describe"),
    ),
))
```

CLI:

```bash
oec experiment run --spec-file experiment.json --skills-root skills
```

## Rules

1. Each step = one `Engine.run` → one `ExecutionResult`.
2. Metrics are resolved only from dotted paths into step results (no invented numbers).
3. `ExperimentStatus` is **not** `ExecutionStatus` (`COMPLETED`, `VALIDATION_FAILED`, `ABORTED`, `FAILED`, `INVALID`).
4. Seed is recorded on the experiment and in `Engine.run` provenance; it is **not** auto-injected into skill inputs.
5. `config_hash` = SHA-256 of canonical JSON of the frozen `ExperimentSpec`.

## ExperimentStatus → process exit (CLI)

| Status | Exit |
|--------|------|
| COMPLETED | 0 |
| VALIDATION_FAILED | 2 |
| ABORTED / INVALID | 3 |
| FAILED | 4 |
