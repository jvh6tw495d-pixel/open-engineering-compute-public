"""mathematics.integrate entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Two mutually exclusive modes (function vs tabulated); see
``skill.md``'s "Official methodology" for the tabulated method-selection
rule and for why the skill-wide ``method.iterative: true`` declaration
covers both modes.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.integrate import quad, simpson, trapezoid

from oec.kernel.numerics.expressions import compile_expression

# SciPy quad defaults (kept explicit so diagnostics/convergence use the
# same numbers that were actually passed to the solver).
_DEFAULT_EPSABS = 1.49e-08
_DEFAULT_EPSREL = 1.49e-08


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    if inputs.get("expression") is not None:
        return _integrate_function(inputs)
    return _integrate_tabulated(inputs)


def _integrate_function(inputs: dict[str, Any]) -> dict[str, Any]:
    f = compile_expression(inputs["expression"])
    a, b = inputs["bounds"]
    epsabs = float(inputs.get("epsabs", _DEFAULT_EPSABS))
    epsrel = float(inputs.get("epsrel", _DEFAULT_EPSREL))

    value, abs_error = quad(f, a, b, epsabs=epsabs, epsrel=epsrel)
    value_f = float(value)
    abs_error_f = float(abs_error)

    # ADR 0013: iterative method must always populate diagnostics["converged"].
    # Treat the QUADPACK absolute-error estimate as the convergence signal.
    tolerance = max(epsabs, epsrel * abs(value_f))
    converged = abs_error_f <= tolerance

    return {
        "result": {"value": value_f, "mode": "function"},
        "diagnostics": {
            "mode": "function",
            "method": "adaptive_quad",
            "converged": converged,
            "abs_error": abs_error_f,
            "epsabs": epsabs,
            "epsrel": epsrel,
            "tolerance": tolerance,
        },
    }


def _integrate_tabulated(inputs: dict[str, Any]) -> dict[str, Any]:
    x = np.asarray(inputs["x"], dtype=float)
    y = np.asarray(inputs["y"], dtype=float)
    method = _select_tabulated_method(inputs.get("method"), n_points=int(x.size))

    value = float(simpson(y, x=x)) if method == "simpson" else float(trapezoid(y, x=x))

    # Tabulated path is a fixed closed-form quadrature rule (no iteration).
    # The skill still declares iterative:true because function mode is
    # adaptive; ADR 0013 therefore requires diagnostics["converged"] on
    # every call. Report True: given the samples, the rule is exact by
    # definition (there is no iterative process that can fail).
    return {
        "result": {"value": value, "mode": "tabulated"},
        "diagnostics": {
            "mode": "tabulated",
            "method": method,
            "converged": True,
            "n_points": int(x.size),
        },
    }


def _select_tabulated_method(requested: str | None, *, n_points: int) -> str:
    """Mirror the documented rule in skill.md "Official methodology"."""
    if requested == "trapezoid":
        return "trapezoid"
    if requested == "simpson":
        return "simpson"
    # Auto-select: Simpson needs ≥ 3 samples; 2-point data → trapezoid.
    if n_points >= 3:
        return "simpson"
    return "trapezoid"
