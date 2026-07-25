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

    quad_result = quad(f, a, b, epsabs=epsabs, epsrel=epsrel, full_output=True)
    value_f = float(quad_result[0])
    abs_error_f = float(quad_result[1])
    # QUADPACK returns a 4th element (a human-readable explanation) only
    # when it hit a real problem (subdivision limit, slow convergence,
    # a suspected singularity, ...). Its *absence* is the authoritative
    # convergence signal -- comparing abs_error to the requested tolerance
    # alone is not: abs_error is QUADPACK's own estimate, which can look
    # deceptively small for the exact integrand that triggers the warning
    # (independent review of Sprint 04 flagged this as a real gap, not
    # hypothetical -- the class of failure that "explodes in optimization").
    quadpack_reported_a_problem = len(quad_result) > 3
    tolerance = max(epsabs, epsrel * abs(value_f))
    converged = not quadpack_reported_a_problem and abs_error_f <= tolerance

    diagnostics: dict[str, Any] = {
        "mode": "function",
        "method": "adaptive_quad",
        "converged": converged,
        "abs_error": abs_error_f,
        "epsabs": epsabs,
        "epsrel": epsrel,
        "tolerance": tolerance,
        "n_evaluations": int(quad_result[2]["neval"]),
    }
    if quadpack_reported_a_problem:
        diagnostics["quadpack_message"] = str(quad_result[3])

    return {"result": {"value": value_f, "mode": "function"}, "diagnostics": diagnostics}


def _integrate_tabulated(inputs: dict[str, Any]) -> dict[str, Any]:
    x = np.asarray(inputs["x"], dtype=float)
    y = np.asarray(inputs["y"], dtype=float)
    method = _select_tabulated_method(inputs.get("method"), n_points=int(x.size))

    value = float(simpson(y, x=x)) if method == "simpson" else float(trapezoid(y, x=x))

    # Tabulated path is a fixed closed-form quadrature rule (no iteration).
    # The skill declares iterative:true because function mode is adaptive,
    # so ADR 0013 requires diagnostics["converged"] to be *present* on every
    # call -- but its value here is `None`, not `True`: per the ADR 0013
    # amendment (Sprint 05), a present-but-null value means "this specific
    # call was exact, not iterative", so it is eligible for VERIFIED just
    # like mathematics.interpolate's equally exact results -- not held to
    # the weaker VALIDATED tier just because it shares a manifest with an
    # adaptive mode.
    return {
        "result": {"value": value, "mode": "tabulated"},
        "diagnostics": {
            "mode": "tabulated",
            "method": method,
            "converged": None,
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
