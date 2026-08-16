<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/oec-logo-compact-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/oec-logo-compact-light.svg">
    <img src="docs/assets/oec-logo-compact-light.svg" alt="OEC logo" width="220">
  </picture>
</p>

# Open Engineering Compute (OEC)

> **Status:** **`oec==3.6.0` Scientific AI Completion code baseline** (S0–S5 complete; S6 release gate/CI pending).
> Skill catalog: **151** skills / **28** domains, including **6 foundation** skills (extras optional).
> Framework notes: [FRAMEWORK-3.5.0.md](docs/release/FRAMEWORK-3.5.0.md).
> Scientific AI completion (3.6): [SCIENTIFIC-AI-3.6.md](docs/release/SCIENTIFIC-AI-3.6.md).
> Prior neural/evo incubation: [v3.4-closeout.md](docs/implementation/v3.4-closeout.md).

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
uv sync --extra neural        # PyTorch: neural.* families / training (ADR 0031)
uv sync --extra evolutionary  # pymoo/DEAP/Nevergrad: evolutionary.* (ADR 0031/0033)
uv sync --extra foundation    # transformers + Pillow: foundation.embed / generate / vision / VLM
```

## Interfaces

| Surface | Entry |
|---|---|
| Python SDK | `oec.sdk.Engine` / `oec.sdk.run` → `ExecutionResult` |
| Python SDK (scientific) | `Engine.run_scientific` → `ScientificResult` ([ADR 0019](docs/architecture/adr/0019-scientific-kernel.md)) |
| CLI | `oec skills …`, `oec run`, `oec server …` |
| REST | `/v1/skills`, `/v1/skills/{id}/run` — [docs/api](docs/api/README.md) |
| MCP | agent-first tools + raw skills + `experiment.*` — [docs/mcp](docs/mcp/README.md) |

See [docs/concepts/scientific-kernel.md](docs/concepts/scientific-kernel.md) for when to use `ScientificResult` vs `ExecutionResult`.

## Optional integrations

| Integration | Path | Notes |
|---|---|---|
| Odysseus (MCP host) | `integrations/odysseus/` | config + tutorial; core has zero Odysseus deps |
| Open Science | `integrations/open_science/` | Method Change Proposals; **never** auto-mutates `stable` skills |
| **Agents (v1.5+)** | `agents/` | 9 specialists outside the wheel (incl. neural + foundation) — formulate/review only; numbers from OEC ([packaging](agents/README.md)) |

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

**Current code baseline: `oec==3.6.0`**, Scientific AI Completion S0–S5, **151** skills
across **28** domains, including **6** optional foundation skills (see
[skill-inventory.md](docs/implementation/skill-inventory.md),
[SCIENTIFIC-AI-3.6.md](docs/release/SCIENTIFIC-AI-3.6.md), and the
[3.6 closeout](docs/release/3.6.0-CLOSEOUT.md)). S6 is the release-gate/CI closeout;
this repository state does not claim a tag, push, or published package.

**3.5.0 theme (W0–W8):** Experiment Engine (`Engine.run_experiment`), applied-sciences
foundations (waves/optics/EM/statistical physics/…), neural + evolutionary experiment
builders, optional **Foundation** models (`oec[foundation]`), cross-domain builder library,
and hardened MCP/CLI surfaces (`agent.foundation`, `experiment.list_builders` /
`experiment.run` with fail-closed builder catalog). Core install remains free of torch /
pymoo / transformers.

**3.6 S0–S5:** ADR freeze; governed PEFT/full fine-tune artifacts; tabular
distillation and checkpoint hardening; fail-closed evolutionary/hybrid experiment
builders (with NEAT excluded); and bounded, pinned, optional vision/VLM skills.
The core install remains free of torch, pymoo, Transformers, PEFT, and Pillow.

**3.4.x baseline:** optional **Neural** / **Evolutionary** extras under ADR 0031–0033
([waves](docs/implementation/OEC_NEURAL_EVOLUTIONARY_WAVES.md),
[v3.4 closeout](docs/implementation/v3.4-closeout.md)). Hybrid paths never promote
surrogate optima to engineering truth without high-fidelity re-check.

Open residuals (REST/MCP auth, OS sandbox, routing as classifier) stay in
[technical-debt.md](docs/implementation/technical-debt.md).

<details>
<summary>Earlier release history (v2.2.0 → v2.5.1)</summary>

**v2.2.0** delivered Math IR foundation (`oec.modeling`, ADR 0020).
**v2.3.0** closed the Applied Math expansion (Waves A+B+C): 21 new skills since
2.2 (linear/stats/TS/opt, uncertainty, dynamics, control, Pareto/CVaR/robust LP),
plus A23/B23 scientific corrections — **accepted** for private incubation
([acceptance seal](docs/implementation/v2.3-accepted-and-merge-prep.md)).
**v2.5.0** closes v2.4 (Backend Capability Registry + Verification Engine,
ADR 0021) and v2.5 (computational kernel unification under ADR 0022,
`mathematics.differentiate`, MCP agent-first tool catalog with
natural-language routing) in one consolidated release: golden-set
distribution (193 cases / 8 domains), critical-path coverage (90%), and
public-API docstring coverage (100%) gates are all met — see
[CHANGELOG.md](CHANGELOG.md). **v2.5.1** is a refinement release (not a new
domain wave): a `timeseries.*` AR/autocorrelation package
(`autocorrelation`, `pacf`, `ar_yule_walker`, `levinson_durbin`),
`agent.default` routing for that domain's intent, catalog reconciliation,
and a coverage push on the four weakest kernel modules
(`quality`/`ops`/`timegrid`/`feasibility`, aggregate suite coverage
90.67% → 92.0%). Catalog was **67** skills at that point. **v2.6–v2.7** added
physics/multiphysics co-simulation; **v2.8–v2.9** added the chemistry
foundation, Scientific IR and Model Registry; **v3.0.0** was an early
"public-claimable" cut later withdrawn (see above); **v3.1–v3.3.0** completed
chemistry, added THD and the sequential chemistry network. Full detail in
`CHANGELOG.md` and the versioned closeout docs under `docs/implementation/`.

</details>

This tree is the **incubation / scientific framework** line. A separate Public Alpha
export (clean history) may still use a new directory — see:

- [docs/release/public-alpha.md](docs/release/public-alpha.md)
- `uv run python scripts/prepare_public_alpha.py --dry-run`
- `uv run python scripts/check_forbidden_names.py`

Layout map: [docs/development/codebase-map.md](docs/development/codebase-map.md).

## Learning backends (optional)

OEC **never auto-installs** Unsloth, Axolotl, or ART. Calling those
functions without the package raises `BackendNotAvailableError` with the
exact command. See [LEARNING-OPERATIONAL.md](docs/release/LEARNING-OPERATIONAL.md).

```bash
# ART/GRPO — PyPI name is openpipe-art (import name: art)
uv pip install "openpipe-art==0.5.18"
# WRONG: pip install art   # ASCII-art library, no train_grpo

# Unsloth — isolated venv only (downgrades torch if mixed with OEC)
# Axolotl — Linux/WSL only (no Windows wheel for triton)
```

## Development

```bash
uv sync --extra api --extra mcp --extra optimization --extra neural --extra evolutionary --extra foundation
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
