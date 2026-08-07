# Mathematical engine and governance

## Positioning (non-negotiable)

**OEC is not a new numerical library.** It does not claim credit for the
mathematical algorithms that power most of its computational skills.

| Layer | Owner of the merit | What it provides |
|---|---|---|
| **SciPy** (and NumPy, where used) | SciPy / NumPy communities | Numerical methods: root finding, quadrature, interpolation, optimization, least squares, … |
| **Pint** | Pint project | Unit arithmetic and conversion |
| **OEC** | This project | **Governance** around those engines: executable methodology, versioning, schemas, units policy, validation layers, diagnostics policy, provenance, multi-interface reproducibility |

> **The mathematical merit belongs to SciPy (and peers).**
> **OEC contributes context and methodology** so engineers, physicists,
> mathematicians, and researchers can run the *same* procedure
> repeatedly — with audit trail — including when the caller is an LLM
> or agent.

## What “governance on top” means

For skills that use SciPy as the compute engine, OEC adds:

1. **Explicit methodology** — which SciPy routine, when, and why (no silent method shopping).
2. **Versioned skill contract** — `skill.yaml` / `skill.md`, semver, lifecycle.
3. **Input/output schemas** — structured, documentable, MCP/REST-friendly.
4. **Units and dimensions** (physical skills) — mandatory quantities, central normalization.
5. **Validation layers** — schema → dimensional → domain → physical → numerical → golden.
6. **Graded execution status** — converged is not automatically “validated”.
7. **Provenance** — skill version, method version, `run_id`, environment metadata.
8. **Thin interfaces** — SDK, CLI, REST, MCP all hit the same `ExecutionService`.

OEC **wraps, selects, documents, and audits** SciPy calls. It does not
rebrand SciPy’s mathematics as “OEC algorithms.”

## What OEC does *not* claim

- Inventing Brent, QUADPACK, SLSQP, Levenberg–Marquardt, cubic splines, etc.
- Replacing SciPy as a general-purpose scientific Python stack.
- Owning the numerical correctness of upstream solvers beyond honest
  reporting of their diagnostics and our golden-case policy.

Where a skill is **closed-form engineering arithmetic** (e.g. balanced
three-phase power identities) rather than a SciPy solver, the skill
still cites textbooks/standards; the merit of classical identities is
not claimed as a numerical invention of OEC either.

## Audience

OEC is meant to help:

- **Engineers** — repeatable methods with units and limits of use
- **Physicists** — explicit assumptions and provenance
- **Mathematicians / applied math** — solvers used under a declared contract
- **Researchers** — versioned methodology suitable for review (see also Open Science integration)

Agents and LLMs are *callers*, not the source of methodology.

## Attribution in skill packages

Every skill that delegates to SciPy **must**:

- name the SciPy entry points in `skill.md` / `references.md`;
- treat golden oracles as independent of the SciPy path under test
  where plan section 22 applies;
- keep method selection rules in the skill contract, not in the UI.

## Related

- ADR 0001 — skill-first architecture
- ADR 0004 — deterministic execution
- ADR 0005 — thin interface adapters
- Project dependencies: `pyproject.toml` (`scipy`, `numpy`, `pint`, …)
- Upstream: [SciPy](https://scipy.org/), [NumPy](https://numpy.org/), [Pint](https://pint.readthedocs.io/)
