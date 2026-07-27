"""v2.2 stop gate (scalar-root half): the same nonlinear equation solved via
the existing `numerical.root_system` skill and via the new Math IR
`scalar_root` path must converge to the same root.
"""

from __future__ import annotations

from pathlib import Path

from oec.modeling.compile_scalar_root import compile_scalar_root
from oec.modeling.ir import BinaryOp, MathProblem, NumberLiteral, Symbol, SymbolRef
from oec.testing import load_skill_module

_ROOT_SYSTEM_SKILL_DIR = (
    Path(__file__).resolve().parent.parent.parent / "skills" / "numerical" / "root_system"
)


def _solve_via_existing_root_system_path() -> float:
    implementation = load_skill_module(_ROOT_SYSTEM_SKILL_DIR, "implementation")
    out = implementation.execute({"variables": ["x"], "equations": ["x**2 - 4"], "x0": [3.0]})
    return float(out["result"]["x"][0])


def _solve_via_math_ir() -> float:
    equation_lhs = BinaryOp(op="**", left=SymbolRef(name="x"), right=NumberLiteral(value=2))
    math_problem = MathProblem(
        symbols=[Symbol(name="x")],
        unknowns=["x"],
        initial_guess={"x": 3.0},
        equations=[{"lhs": equation_lhs, "rhs": NumberLiteral(value=4)}],
    )
    result = compile_scalar_root(math_problem)
    assert result.diagnostics.converged is True
    return result.root


def test_math_ir_scalar_root_matches_existing_root_system_path() -> None:
    via_root_system = _solve_via_existing_root_system_path()
    via_ir = _solve_via_math_ir()

    assert abs(via_ir - 2.0) < 1e-6
    assert abs(via_root_system - 2.0) < 1e-6
    assert abs(via_ir - via_root_system) < 1e-5
