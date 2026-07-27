"""mathematics.solve_root entrypoint.

Runs inside the sandboxed subprocess (ADR 0012) — imported only by
``oec.execution.runner``, never by the Skill Loader or the parent
process. Builds on the kernel primitives in ``oec.kernel.numerics``
rather than re-implementing root finding here; see ``skill.md``'s
"Official methodology" for the method-selection rule this mirrors.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.computational.roots import (
    RootResult,
    find_root_bracketed,
    find_root_from_guess,
    select_default_method,
)
from oec.kernel.numerics.expressions import compile_expression


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    f = compile_expression(inputs["expression"])

    bracket = inputs.get("bracket")
    initial_guess = inputs.get("initial_guess")
    method = inputs.get("method") or select_default_method(
        has_bracket=bracket is not None, has_initial_guess=initial_guess is not None
    )

    result: RootResult
    if method in ("brentq", "bisect"):
        a, b = bracket
        kwargs: dict[str, Any] = {}
        if "tolerance" in inputs:
            kwargs["xtol"] = inputs["tolerance"]
        if "max_iterations" in inputs:
            kwargs["max_iterations"] = inputs["max_iterations"]
        result = find_root_bracketed(f, a, b, method=method, **kwargs)
    else:
        fprime = compile_expression(inputs["derivative"]) if inputs.get("derivative") else None
        open_kwargs: dict[str, Any] = {}
        if "tolerance" in inputs:
            open_kwargs["tolerance"] = inputs["tolerance"]
        if "max_iterations" in inputs:
            open_kwargs["max_iterations"] = inputs["max_iterations"]
        result = find_root_from_guess(f, initial_guess, method=method, fprime=fprime, **open_kwargs)

    return {
        "result": {
            "root": result.root,
            "method": result.diagnostics.method,
            "iterations": result.diagnostics.iterations,
            "residual": result.diagnostics.residual,
        },
        "diagnostics": {
            "method": result.diagnostics.method,
            "converged": result.diagnostics.converged,
            "iterations": result.diagnostics.iterations,
            "function_calls": result.diagnostics.function_calls,
            "residual": result.diagnostics.residual,
        },
    }
