# Open Engineering Compute (OEC)

> **Status:** **v2.3.0 Applied Math expansion** (private; V3 roadmap).
> First **public GitHub** release is planned for **v3.0** — not this history
> (see [Public Alpha procedure](docs/release/public-alpha.md) and
> [V3 implementation plan](docs/implementation/OEC_V3_IMPLEMENTATION_PLAN.md)).

Open Engineering Compute is an open framework for executable, versioned and
auditable engineering skills. It lets different language models, agents,
applications and interfaces run the same engineering methodology and obtain
numerically consistent, reproducible and auditable results.

> Language models can vary.
> Engineering methodology must not change silently.

The core of the system is the **Skill Engine**, which turns an engineering
specification into an executable procedure. Every skill declares its problem
definition, official methodology, mathematical formulation, units, schemas,
assumptions, applicability limits, deterministic implementation, validations,
tests, references, version and provenance.

## SciPy is the math engine — OEC is governance

**OEC is not a competitor to SciPy and does not claim SciPy’s mathematical
merit.** For numerical work (roots, quadrature, interpolation, optimization,
curve fitting, …) OEC uses **SciPy** (and **NumPy** where appropriate) as the
computational engine. **Pint** handles units.

What OEC contributes on top is **governance and methodology** for engineering
and applied work:

- which method is used, when, and under which assumptions;
- versioned skill contracts (schemas, limits, references);
- validation, diagnostics policy, and provenance (`run_id`, skill/method versions);
- the same procedure via SDK, CLI, REST, and MCP — including for agents.

In short: **SciPy computes; OEC contextualizes and governs** so engineers,
physicists, mathematicians, and researchers can trust *which* procedure ran.

See [docs/concepts/mathematical-engine-and-governance.md](docs/concepts/mathematical-engine-and-governance.md).

## Quick start

```bash
uv sync
uv run oec skills list --skills-root skills
uv run oec run mathematics.solve_root --input '{"expression":"x**2 - 2","bracket":[0,2]}' --skills-root skills
```

Optional extras:

```bash
uv sync --extra api           # REST:  oec server api --skills-root skills
uv sync --extra mcp           # MCP:   oec server mcp --skills-root skills
uv sync --extra optimization  # HiGHS: optimization.lp / optimization.milp
```

## Interfaces

| Surface | Entry |
|---|---|
| Python SDK | `oec.sdk.Engine` / `oec.sdk.run` → `ExecutionResult` |
| Python SDK (scientific) | `Engine.run_scientific` → `ScientificResult` ([ADR 0019](docs/architecture/adr/0019-scientific-kernel.md)) |
| CLI | `oec skills …`, `oec run`, `oec server …` |
| REST | `/v1/skills`, `/v1/skills/{id}/run` — [docs/api](docs/api/README.md) |
| MCP | stdio tools per skill — [docs/mcp](docs/mcp/README.md) |

See [docs/concepts/scientific-kernel.md](docs/concepts/scientific-kernel.md) for when to use `ScientificResult` vs `ExecutionResult`.

## Optional integrations

| Integration | Path | Notes |
|---|---|---|
| Odysseus (MCP host) | `integrations/odysseus/` | config + tutorial; core has zero Odysseus deps |
| Open Science | `integrations/open_science/` | Method Change Proposals; **never** auto-mutates `stable` skills |
| **Agents (v1.5+)** | `agents/` | 5 specialists outside the wheel — formulate/review only; numbers from OEC ([packaging](agents/README.md)) |

```python
from agents.optimization_specialist.specialist import OptimizationSpecialist
from agents.scientific_reviewer.reviewer import ScientificReviewer

spec = OptimizationSpecialist(skills_root="skills")
report = spec.run_demo("diet")  # or execute_ops(ops_dict)
review = ScientificReviewer().review(report.ops, report.execution)
assert review.passed
print(report.narrative)  # cites run_id / objective from ExecutionResult only
```

## MVP skills

- **Mathematics (6):** `solve_root`, `interpolate`, `integrate`, `optimize_scalar`, `optimize_constrained`, `curve_fit`
- **Electrical (6):** `three_phase_power`, `current_from_power`, `voltage_drop`, `power_factor_correction`, `transformer_loading`, `per_unit_conversion`
- **Optimization (2):** `optimization.lp`, `optimization.milp` (HiGHS — `uv sync --extra optimization`)
- **Time series (4):** `timeseries.resample`, `align`, `fill_missing`, `power_to_energy` (pandas)
- **Linear / numerical / stats (4):** `linear.solve_system`, `numerical.root_system`, `numerical.ode_ivp`, `statistics.describe`
- **Energy generic (3):** `energy.balance`, `energy.load_metrics`, `battery.soc_step` (public formulas only)

LP/MILP use **OPS v0.1** (`docs/contracts/ops.md`). Numerical merit: SciPy / NumPy / pandas / [HiGHS](https://highs.dev/) as declared per skill.

## Status / release

**v2.2.0** delivered Math IR foundation (`oec.modeling`, ADR 0020).  
**v2.3.0** closes the Applied Math expansion (Waves A+B+C): 21 new skills since
2.2 (linear/stats/TS/opt, uncertainty, dynamics, control, Pareto/CVaR/robust LP).  
See [CHANGELOG.md](CHANGELOG.md). Backend Registry and formal Verification remain **v2.4+**.

This clone is the **incubation** repository (no remote). Public Alpha must use a
**new directory and clean git history** — see:

- [docs/release/public-alpha.md](docs/release/public-alpha.md)
- `uv run python scripts/prepare_public_alpha.py --dry-run`
- `uv run python scripts/check_forbidden_names.py`

Layout map: [docs/development/codebase-map.md](docs/development/codebase-map.md).

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy
uv run bandit -c pyproject.toml -r src/oec
```

## Acknowledgments

Numerical methods are provided by the **[SciPy](https://scipy.org/)** and
**[NumPy](https://numpy.org/)** communities; unit handling by
**[Pint](https://pint.readthedocs.io/)**. OEC’s contribution is the skill
contract, validation, and execution governance around those engines — not
ownership of the underlying mathematics.

## License

Apache-2.0 (provisional — see `LICENSE`). SciPy, NumPy, and Pint remain under
their own licenses (see dependency metadata). Community docs:
`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`.
