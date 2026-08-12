"""Static capability domain declarations (v2.4 Backend Registry, ADR 0021).

These are declarations, not probes — whether a backend is actually
*available* in this environment is `registry.py`'s job (via
`backends/adapters/`). This module only answers "what capability domains
does backend X provide, and is it required or an optional extra," derived
from the concrete kernel import survey in ADR 0021: numpy is used
pervasively (dense linear algebra + RNG in four modules); scipy is used for
scalar/system root-finding, curve fitting, constrained/QP/scalar
optimization, ODE integration, `linalg.expm`, and `stats`-based confidence
intervals — `scipy.interpolate` is deliberately not declared here since
nothing in the kernel calls it today (declaring it would be aspirational,
not a real capability); highs is used exclusively via
`kernel/optimization/highs.py` for LP/MILP, gated behind the optional
`oec[optimization]` extra.
"""

from __future__ import annotations

from types import MappingProxyType

DECLARED_CAPABILITIES: MappingProxyType[str, frozenset[str]] = MappingProxyType(
    {
        "numpy": frozenset({"dense_linear_algebra", "rng"}),
        "scipy": frozenset(
            {
                "root_finding",
                "root_system",
                "curve_fit",
                "optimize",
                "integrate_ivp",
                "linalg",
                "stats",
            }
        ),
        "highs": frozenset({"lp", "milp"}),
        # ADR 0031 — optional extras oec[neural] / oec[evolutionary]
        "torch": frozenset({"neural_train", "neural_eval", "neural_distill"}),
        "pymoo": frozenset({"evolutionary_single", "evolutionary_multi"}),
        # E3 / E4 — still oec[evolutionary] extra
        "deap": frozenset({"genetic_programming", "evolution_strategy"}),
        "nevergrad": frozenset({"blackbox_optimize"}),
        # W6/S1 — optional oec[foundation]
        "transformers": frozenset(
            {"foundation_embed", "foundation_generate", "foundation_peft", "foundation_finetune"}
        ),
        # SymPy is a core dep; declare symbolic domain for registry honesty
        "sympy": frozenset({"symbolic"}),
    }
)

# Required backends are hard runtime dependencies (always importable in a
# correctly installed environment); optional backends are gated behind an
# extra and may legitimately be unavailable (ADR 0021 fallback policy).
REQUIRED_BACKENDS: frozenset[str] = frozenset({"numpy", "scipy", "sympy"})
OPTIONAL_BACKENDS: frozenset[str] = frozenset(
    {"highs", "torch", "pymoo", "deap", "nevergrad", "transformers"}
)


def domains_for(backend: str) -> frozenset[str]:
    """Return the declared capability domains for ``backend``, or an empty set."""
    return DECLARED_CAPABILITIES.get(backend, frozenset())


def is_required(backend: str) -> bool:
    """Whether ``backend`` is a hard runtime dependency rather than an optional extra."""
    return backend in REQUIRED_BACKENDS
