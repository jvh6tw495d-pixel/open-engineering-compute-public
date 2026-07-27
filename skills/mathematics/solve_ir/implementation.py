"""mathematics.solve_ir — classify a Math IR document and compile it to an
existing governed backend (OPS/HiGHS for linear_program, SciPy root for
scalar_root). See docs/architecture/adr/0020-math-ir-foundation.md.
"""

from __future__ import annotations

from typing import Any

from oec.modeling.classify import classify
from oec.modeling.compile_linear import compile_linear
from oec.modeling.compile_scalar_root import compile_scalar_root
from oec.modeling.ir import MathProblem


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = MathProblem.model_validate(inputs["ir"])
    problem_class = classify(problem)

    if problem_class == "linear_program":
        result, diagnostics = compile_linear(problem)
        return {
            "result": {
                "problem_class": problem_class,
                "backend": result["backend"],
                "solution": result,
            },
            "diagnostics": diagnostics,
        }

    root_result = compile_scalar_root(problem)
    solution = {
        "unknown": problem.unknowns[0],
        "root": root_result.root,
    }
    return {
        "result": {
            "problem_class": problem_class,
            "backend": "scipy",
            "solution": solution,
        },
        "diagnostics": root_result.diagnostics.model_dump(),
    }
