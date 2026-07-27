"""v2.2 stop gate (LP half): a small LP solved via the existing governed OPS
path and via the new Math IR `linear_program` path must match exactly, since
`oec.modeling.compile_linear` compiles to and calls the identical
`ops_to_linear_parts` -> `solve_linear` sequence `optimization.lp` uses.
"""

from __future__ import annotations

import pytest

from oec.kernel.optimization.highs import check_bound_conflicts, solve_linear
from oec.modeling.compile_linear import compile_linear
from oec.modeling.ir import MathProblem, Symbol
from oec.ops.convert import ops_to_linear_parts
from oec.ops.models import validate_ops

highspy = pytest.importorskip("highspy")

_OPS_DOCUMENT = {
    "ops_version": "0.1.0",
    "problem_class": "lp",
    "sense": "min",
    "variables": [
        {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
        {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
    ],
    "constraints": [
        {"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1},
    ],
    "objective": {"coeffs": {"x": 1, "y": 1}},
}


def _solve_via_existing_ops_path() -> dict[str, float]:
    problem = validate_ops(_OPS_DOCUMENT)
    variables, constraints, sense = ops_to_linear_parts(problem)
    assert not check_bound_conflicts(variables)
    solved = solve_linear(variables=variables, constraints=constraints, sense=sense)  # type: ignore[arg-type]
    return {"objective_value": solved.objective_value, **solved.primal}


def _solve_via_math_ir() -> dict[str, float]:
    math_problem = MathProblem(
        symbols=[Symbol(name="x", lower=0, upper=1), Symbol(name="y", lower=0, upper=1)],
        sense="min",
        objective={"coeffs": {"x": 1, "y": 1}},
        constraints=[{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
    )
    result, diagnostics = compile_linear(math_problem)
    assert diagnostics["converged"] is True
    return {"objective_value": result["objective_value"], **result["primal"]}


def test_math_ir_linear_program_matches_existing_ops_path() -> None:
    via_ops = _solve_via_existing_ops_path()
    via_ir = _solve_via_math_ir()

    assert via_ir["objective_value"] is not None
    assert via_ops["objective_value"] is not None
    assert abs(via_ir["objective_value"] - via_ops["objective_value"]) < 1e-8
    assert abs(via_ir["objective_value"] - 1.0) < 1e-8

    for name in ("x", "y"):
        assert abs(via_ir[name] - via_ops[name]) < 1e-8
