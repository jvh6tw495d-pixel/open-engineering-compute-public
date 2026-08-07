"""mathematics.differentiate entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Estimates ``f'(x)`` via finite differences
(``oec.kernel.computational.differentiation``); see ``skill.md``'s
"Official methodology" for the default step-size formulas.

Not iterative — a closed-form estimate at a fixed step, not an adaptive
solver — so ``diagnostics`` does **not** report ``converged`` (ADR 0013:
only iterative methods must).
"""

from __future__ import annotations

from typing import Any

from oec.kernel.computational.differentiation import differentiate
from oec.kernel.numerics.expressions import compile_expression


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    f = compile_expression(inputs["expression"])
    method = inputs.get("method", "central")
    step = inputs.get("step")

    result = differentiate(f, float(inputs["at"]), method=method, step=step)
    diag = result.diagnostics.model_dump()

    return {
        "result": {"value": result.value},
        "diagnostics": {
            "method": diag["method"],
            "step": diag["step"],
        },
    }
