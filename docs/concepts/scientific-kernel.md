# Scientific Kernel (`oec.core`)

**Package version:** 2.0.0
**ADR:** [0019 — ScientificResult](../architecture/adr/0019-scientific-kernel.md)

## What it is

The Scientific Kernel is the **domain-independent** layer of OEC: types and errors that describe a scientific outcome without coupling to a skill package (electrical, finance, …) or to Skill Engine execution plumbing.

| Type | Role |
|------|------|
| `ScientificResult` | Public scientific outcome (value, status, method, assumptions, diagnostics, provenance, optional validity) |
| `ValidityDomain` | Declared applicability envelope (constraints, bounds, notes) |
| `Diagnostic` | One typed diagnostic item (code, message, severity, details) |
| `ProvenanceRecord` | Formal provenance (`input_hash`, backends, oec_version, …) |
| `MethodRef` / `BackendRef` / `Assumption` | Shared identity types |
| Core errors | Domain-independent failures (`ScientificDomainError`, `BackendUnavailableError`, …) |

`oec.core` must **not** import skill domains.

## `ScientificResult` vs `ExecutionResult`

| | `ExecutionResult` | `ScientificResult` |
|--|-------------------|--------------------|
| Owner | Skill Engine | Scientific Kernel (`oec.core`) |
| When | CLI, REST, MCP, audits, full replay | Reviewers, notebooks, agents, external scientific pipelines |
| Carries | Full execution record (inputs, normalized_inputs, conventions, skill/method refs, …) | Outcome-focused view: `value`, method, assumptions, diagnostics, provenance, optional `validity` |
| Stability | Canonical execution contract (unchanged in 2.0) | Additive adapter (ADR 0019) |

**Rule of thumb**

- Need **how** it ran (inputs, normalization, conventions) → `ExecutionResult` / `Engine.run`
- Need **what** was found scientifically (value + method + provenance + status) → `ScientificResult` / `Engine.run_scientific`

```python
from oec.sdk import Engine

engine = Engine(skills_root="skills")

# Skill Engine (unchanged)
er = engine.run("mathematics.solve_root", {"expression": "x**2 - 2", "bracket": [0, 2]})

# Scientific Kernel (v2.0)
sr = engine.run_scientific("mathematics.solve_root", {"expression": "x**2 - 2", "bracket": [0, 2]})
assert sr.value["root"]  # scientific payload
assert sr.backend_names  # e.g. numpy, scipy
```

`from_execution_result(er)` maps without mutating `er`. Legacy diagnostics stay in `diagnostics_raw`; typed items live in `diagnostics`.

## What 2.0 is *not*

- Not full Math Complete / Math IR
- Not Physics or Chemistry Complete
- Not a public GitHub release (that remains **v3.0**)

SciPy/NumPy/HiGHS remain the **merit engines**; OEC remains **governance** on top.
