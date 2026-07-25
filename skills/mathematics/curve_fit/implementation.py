"""mathematics.curve_fit entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Builds on ``oec.kernel.optimization.curve_fit`` and
``oec.kernel.numerics.expressions.compile_expression_vector`` rather
than calling SciPy directly here. ``x`` is always the independent
variable's name in ``model`` — matching every other math skill's
convention of a fixed, blessed variable name — with ``parameter_names``
supplying the rest of the symbols.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.numerics.expressions import compile_expression_vector
from oec.kernel.optimization.curve_fit import fit_curve

_INDEPENDENT_VARIABLE = "x"


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    parameter_names = tuple(inputs["parameter_names"])
    model = compile_expression_vector(
        inputs["model"], symbols=(_INDEPENDENT_VARIABLE, *parameter_names)
    )

    bounds_input = inputs.get("bounds")
    bounds = None
    if bounds_input is not None:
        lower = [float("-inf") if pair[0] is None else float(pair[0]) for pair in bounds_input]
        upper = [float("inf") if pair[1] is None else float(pair[1]) for pair in bounds_input]
        bounds = (lower, upper)

    kwargs: dict[str, Any] = {}
    if "max_iterations" in inputs:
        kwargs["max_iterations"] = inputs["max_iterations"]

    result = fit_curve(
        model,
        inputs["x"],
        inputs["y"],
        inputs["initial_guess"],
        bounds=bounds,
        method=inputs.get("method"),
        **kwargs,
    )

    return {
        "result": {
            "params": result.params,
            "method": result.diagnostics.method,
            "function_evaluations": result.diagnostics.n_function_evaluations,
        },
        "diagnostics": {
            "method": result.diagnostics.method,
            "converged": result.diagnostics.converged,
            "message": result.diagnostics.message,
            "n_iterations": result.diagnostics.n_iterations,
            "n_function_evaluations": result.diagnostics.n_function_evaluations,
            "residuals": result.diagnostics.residuals,
            "covariance": result.diagnostics.covariance,
        },
    }
