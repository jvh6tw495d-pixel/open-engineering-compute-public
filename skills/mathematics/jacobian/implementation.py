"""mathematics.jacobian — multi-variable finite-difference Jacobian."""

from __future__ import annotations

from typing import Any

from oec.kernel.computational.differentiation import jacobian
from oec.kernel.numerics.expressions import compile_expression_vector


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    variables = [str(v) for v in inputs["variables"]]
    expressions = [str(e) for e in inputs["expressions"]]
    point = [float(v) for v in inputs["at"]]
    method = inputs.get("method", "central")
    step = inputs.get("step")

    compiled = [compile_expression_vector(expr, symbols=tuple(variables)) for expr in expressions]
    result = jacobian(
        compiled,
        point,
        variables=variables,
        method=method,
        step=step,
    )
    diag = result.diagnostics.model_dump()
    return {
        "result": {
            "jacobian": result.jacobian,
            "point": result.point,
            "variables": result.variables,
            "shape": [len(result.jacobian), len(result.point)],
        },
        "diagnostics": {
            "method": diag["method"],
            "step": diag.get("step"),
            "backend": diag["backend"],
        },
    }
