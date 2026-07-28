"""v2.2 stop gate (LP half): a small LP solved via the existing governed
`optimization.lp` skill and via the new Math IR `linear_program` path must
match, proving the IR path is a genuine alternative route to the same
answer -- not merely a re-invocation of the exact same internal call
sequence.

Earlier revision called `ops_to_linear_parts`/`solve_linear` directly here,
which is the *same* call sequence `oec.modeling.compile_linear` itself
uses internally -- a near-tautological comparison that couldn't catch the
two paths diverging (found by an independent review, ADR 0021 amendment).
This version goes through `optimization.lp`'s actual `implementation.py`,
the same way `test_math_ir_scalar_root_parity.py` already does for its
half of this stop gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.modeling.compile_linear import compile_linear
from oec.modeling.ir import MathProblem, Symbol
from oec.testing import load_skill_module

highspy = pytest.importorskip("highspy")

_OPTIMIZATION_LP_SKILL_DIR = (
    Path(__file__).resolve().parent.parent.parent / "skills" / "optimization" / "lp"
)

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


def _solve_via_existing_optimization_lp_skill() -> dict[str, float]:
    implementation = load_skill_module(_OPTIMIZATION_LP_SKILL_DIR, "implementation")
    out = implementation.execute({"ops": _OPS_DOCUMENT})
    result = out["result"]
    assert out["diagnostics"]["converged"] is True
    return {"objective_value": result["objective_value"], **result["primal"]}


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


def test_math_ir_linear_program_matches_existing_optimization_lp_skill() -> None:
    via_skill = _solve_via_existing_optimization_lp_skill()
    via_ir = _solve_via_math_ir()

    assert via_ir["objective_value"] is not None
    assert via_skill["objective_value"] is not None
    assert abs(via_ir["objective_value"] - via_skill["objective_value"]) < 1e-8
    assert abs(via_ir["objective_value"] - 1.0) < 1e-8

    for name in ("x", "y"):
        assert abs(via_ir[name] - via_skill[name]) < 1e-8
