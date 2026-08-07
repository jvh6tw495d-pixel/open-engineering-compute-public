from __future__ import annotations

from typing import Any

from oec.kernel.numerics.expressions import compile_expression_vector
from oec.kernel.optimization.constrained import Constraint, minimize_constrained


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    variables = tuple(inputs["variables"])
    f = compile_expression_vector(inputs["expression"], symbols=variables)

    bounds = None
    if inputs.get("bounds") is not None:
        bounds = [
            (
                None if pair[0] is None else float(pair[0]),
                None if pair[1] is None else float(pair[1]),
            )
            for pair in inputs["bounds"]
        ]

    constraints = [
        Constraint(
            kind=c["type"],
            fun=compile_expression_vector(c["expression"], symbols=variables),
        )
        for c in inputs.get("constraints", [])
    ]

    result = minimize_constrained(
        f,
        inputs["x0"],
        bounds=bounds,
        constraints=constraints,
        method=inputs.get("method"),
    )
    return {
        "result": {
            "x": result.x,
            "fun": result.fun,
            "method": result.diagnostics.method,
            "iterations": result.diagnostics.n_iterations,
        },
        "diagnostics": {
            "method": result.diagnostics.method,
            "converged": result.diagnostics.converged,
            "message": result.diagnostics.message,
            "n_iterations": result.diagnostics.n_iterations,
            "optimality": result.diagnostics.optimality,
            "constraint_violation": result.diagnostics.constraint_violation,
            "feasible": result.diagnostics.feasible,
        },
    }
