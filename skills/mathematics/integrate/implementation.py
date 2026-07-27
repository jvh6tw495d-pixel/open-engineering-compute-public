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

from oec.kernel.computational.integration import (
    DEFAULT_EPSABS,
    DEFAULT_EPSREL,
    integrate_function,
    integrate_tabulated,
)
from oec.kernel.numerics.expressions import compile_expression


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    if inputs.get("expression") is not None:
        return _integrate_function(inputs)
    return _integrate_tabulated(inputs)


def _integrate_function(inputs: dict[str, Any]) -> dict[str, Any]:
    f = compile_expression(inputs["expression"])
    a, b = inputs["bounds"]
    epsabs = float(inputs.get("epsabs", DEFAULT_EPSABS))
    epsrel = float(inputs.get("epsrel", DEFAULT_EPSREL))

    result = integrate_function(f, a, b, epsabs=epsabs, epsrel=epsrel)
    diag = result.diagnostics.model_dump()

    diagnostics: dict[str, Any] = {
        "mode": "function",
        "method": diag["method"],
        "converged": diag["converged"],
        "abs_error": diag["abs_error"],
        "epsabs": diag["epsabs"],
        "epsrel": diag["epsrel"],
        "tolerance": diag["tolerance"],
        "n_evaluations": diag["n_evaluations"],
    }
    if "quadpack_message" in diag:
        diagnostics["quadpack_message"] = diag["quadpack_message"]

    return {"result": {"value": result.value, "mode": "function"}, "diagnostics": diagnostics}


def _integrate_tabulated(inputs: dict[str, Any]) -> dict[str, Any]:
    result = integrate_tabulated(inputs["x"], inputs["y"], method=inputs.get("method"))
    diag = result.diagnostics.model_dump()

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
        "result": {"value": result.value, "mode": "tabulated"},
        "diagnostics": {
            "mode": "tabulated",
            "method": diag["method"],
            "converged": diag["converged"],
            "n_points": diag["n_points"],
        },
    }
