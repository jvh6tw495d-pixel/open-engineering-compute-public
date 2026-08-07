"""mathematics.optimize_constrained entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Builds on ``oec.kernel.optimization.constrained`` and
``oec.kernel.numerics.expressions.compile_expression_vector`` rather
than calling SciPy directly here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.numerics.expressions import compile_expression_vector
from oec.kernel.optimization.constrained import Constraint, minimize_constrained


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    variables = tuple(inputs["variables"])
    f = compile_expression_vector(inputs["expression"], symbols=variables)

    bounds_input = inputs.get("bounds")
    bounds = None
    if bounds_input is not None:
        bounds = [
            (
                None if pair[0] is None else float(pair[0]),
                None if pair[1] is None else float(pair[1]),
            )
            for pair in bounds_input
        ]

    constraints = [
        Constraint(
            kind=constraint["type"],
            fun=compile_expression_vector(constraint["expression"], symbols=variables),
        )
        for constraint in inputs.get("constraints", [])
    ]

    kwargs: dict[str, Any] = {}
    if "tolerance" in inputs:
        kwargs["tolerance"] = inputs["tolerance"]
    if "max_iterations" in inputs:
        kwargs["max_iterations"] = inputs["max_iterations"]

    result = minimize_constrained(
        f,
        inputs["x0"],
        bounds=bounds,
        constraints=constraints,
        method=inputs.get("method"),
        **kwargs,
    )

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
            "optimality": result.diagnostics.optimality,
            "constraint_violation": result.diagnostics.constraint_violation,
            "feasible": result.diagnostics.feasible,
        },
    }
