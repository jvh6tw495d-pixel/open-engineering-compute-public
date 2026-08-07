# Reproducing an OEC execution (Phase A)

## What to record

From any `ExecutionResult`:

| Field | Use |
|---|---|
| `run_id` | Correlate logs and support tickets |
| `skill.id` + `skill.version` | Which skill contract |
| `method.id` + `method.version` | Which declared method |
| `inputs` | Exact caller payload |
| `provenance.input_hash` | Fingerprint of canonical JSON(`inputs`) |
| `provenance.backends[]` | numpy/scipy/sympy/pint versions in that env |
| `provenance.oec_version` | OEC package version |
| `provenance.git_commit` | Incubation tree commit if available |
| `status` / `diagnostics` / `warnings` | Scientific outcome |

## How to re-run

```bash
# Same inputs JSON file as the original call
uv run oec run <skill.id> --input-file inputs.json --skills-root skills --json
```

```python
from oec.sdk import Engine

engine = Engine(skills_root="skills")
result = engine.run("<skill.id>", inputs)  # same dict as before
assert result.provenance["input_hash"] == "<original input_hash>"
```

If `input_hash` matches and skill/backend versions match, results for
deterministic skills should match (same status and numeric content within
documented tolerances).

## What is *not* claimed

- Bit-identical floats across OS/CPU without pinning BLAS — document
  tolerances in the skill when needed.
- Reproducibility if the skill version or method selection rules changed
  (bump skill semver; see `skill-versioning.md`).
- That every package in `backends[]` was invoked — that list is the
  **installed engine environment** (ADR 0017).

## Timeouts

Each skill declares `execution.timeout_seconds` in `skill.yaml`. The
subprocess is killed when exceeded (`diagnostics.timed_out` / FAILED path).
There is no per-request override in Alpha CLI/API unless added later.
