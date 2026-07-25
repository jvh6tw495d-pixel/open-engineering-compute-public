"""mathematics.optimize_scalar entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Builds on ``oec.kernel.optimization.scalar`` rather than
calling SciPy directly here; see ``skill.md``'s "Official methodology"
for the method-selection rule this mirrors.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.numerics.expressions import compile_expression
from oec.kernel.optimization.scalar import minimize_scalar


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    f = compile_expression(inputs["expression"])

    bounds_input = inputs.get("bounds")
    bounds = (float(bounds_input[0]), float(bounds_input[1])) if bounds_input is not None else None

    kwargs: dict[str, Any] = {}
    if "tolerance" in inputs:
        kwargs["tolerance"] = inputs["tolerance"]
    if "max_iterations" in inputs:
        kwargs["max_iterations"] = inputs["max_iterations"]

    result = minimize_scalar(f, bounds=bounds, method=inputs.get("method"), **kwargs)

    return {
        "result": {
            "x": result.x,
            "fun": result.fun,
            "method": result.diagnostics.method,
            "iterations": result.diagnostics.n_iterations,
            "function_evaluations": result.diagnostics.n_function_evaluations,
        },
        "diagnostics": {
            "method": result.diagnostics.method,
            "converged": result.diagnostics.converged,
            "message": result.diagnostics.message,
            "n_iterations": result.diagnostics.n_iterations,
            "n_function_evaluations": result.diagnostics.n_function_evaluations,
        },
    }
