"""Golden cases for mathematics.optimize_constrained, per plan section 12.6.

Reference minimizers come from sources independent of this skill and of
SciPy: trivial closed-form (unconstrained quadratic), Lagrange
multipliers (the classic constrained quadratic), and Himmelblau's
function's well-known, independently documented four minima (Himmelblau,
1972 -- a standard textbook test function, not derived from this skill
or from SciPy; see references.md #2).
"""

import json
import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-6) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="mathematics.optimize_constrained",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form / Lagrange multipliers, see skill.md 'Worked examples'",
        justification=data["description"],
    )


def test_unconstrained_quadratic_matches_example() -> None:
    """Only x/fun are checked against the golden case -- the independently
    known values. method/iterations/function_evaluations are this
    implementation's own observed diagnostics, not pinned here: tying a
    mathematical correctness check to SciPy's exact internal call count
    is a false-regression risk with no correctness signal (independent
    review of Sprint 05)."""
    golden = _golden_from_example("unconstrained_quadratic.json", tolerance=1e-6)
    out = implementation.execute(golden.inputs)
    assert_matches_golden({"x": out["result"]["x"], "fun": out["result"]["fun"]}, golden)
    assert out["result"]["method"] == "SLSQP"
    assert out["diagnostics"]["converged"] is True
    assert out["diagnostics"]["feasible"] is None  # SLSQP + no constraints: nothing measured


def test_constrained_quadratic_matches_example() -> None:
    """min x^2+y^2 s.t. x+y>=1 -- Lagrange multipliers give (0.5, 0.5),
    fun=0.5, independent of SciPy (see skill.md 'Worked examples')."""
    golden = _golden_from_example("constrained_quadratic.json", tolerance=1e-6)
    out = implementation.execute(golden.inputs)
    assert_matches_golden({"x": out["result"]["x"], "fun": out["result"]["fun"]}, golden)
    assert out["diagnostics"]["converged"] is True
    assert out["diagnostics"]["feasible"] is True
    assert out["diagnostics"]["constraint_violation"] < 1e-6


def test_himmelblau_first_minimum_from_nearby_x0() -> None:
    """Himmelblau's function (x^2+y-11)^2 + (x+y^2-7)^2 has four known
    global minima, all with fun=0 -- independently documented (Himmelblau,
    1972), not derived from SciPy. x0=[3,2] is exactly the first minimum,
    so SLSQP converges to it in very few iterations."""
    golden = GoldenCase(
        id="himmelblau-minimum-1",
        skill_id="mathematics.optimize_constrained",
        skill_version="0.1.0",
        inputs={
            "variables": ["x", "y"],
            "expression": "(x**2 + y - 11)**2 + (x + y**2 - 7)**2",
            "x0": [3.0, 2.0],
        },
        expected_result={"x": [3.0, 2.0], "fun": 0.0},
        tolerance=1e-6,
        source="Himmelblau (1972), a standard textbook multi-minima test function",
        justification="multi-minima case: x0 at the first known minimum recovers it exactly",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden({"x": out["result"]["x"], "fun": out["result"]["fun"]}, golden)
    assert out["diagnostics"]["converged"] is True


def test_himmelblau_second_minimum_from_different_x0() -> None:
    """Same objective as test_himmelblau_first_minimum_from_nearby_x0, but
    x0 near Himmelblau's SECOND known minimum (-2.805118, 3.131312)
    converges there instead -- demonstrating explicitly (skill.md
    'Assumptions') that this skill returns whichever local minimum x0's
    basin of attraction leads to, not a global search across all four."""
    golden = GoldenCase(
        id="himmelblau-minimum-2",
        skill_id="mathematics.optimize_constrained",
        skill_version="0.1.0",
        inputs={
            "variables": ["x", "y"],
            "expression": "(x**2 + y - 11)**2 + (x + y**2 - 7)**2",
            "x0": [-2.8, 3.1],
        },
        expected_result={"x": [-2.805118, 3.131312], "fun": 0.0},
        tolerance=1e-4,
        source="Himmelblau (1972), a standard textbook multi-minima test function",
        justification="multi-minima case: a different x0 basin finds a different tied minimum",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden({"x": out["result"]["x"], "fun": out["result"]["fun"]}, golden)
    assert out["diagnostics"]["converged"] is True
    assert not math.isclose(out["result"]["x"][0], 3.0, abs_tol=0.1)


def test_mutually_contradictory_constraints_is_infeasible_not_an_exception() -> None:
    """x+y<=0 (as -(x+y)>=0) and x+y>=1 simultaneously cannot both hold --
    no exception is raised; converged/feasible come back False, and
    constraint_violation reports how much the two disagree (skill.md
    'Failure conditions')."""
    out = implementation.execute(
        {
            "variables": ["x", "y"],
            "expression": "x**2 + y**2",
            "x0": [0.0, 0.0],
            "bounds": [[-10, 10], [-10, 10]],
            "constraints": [
                {"type": "ineq", "expression": "-(x + y)"},
                {"type": "ineq", "expression": "x + y - 1"},
            ],
        }
    )
    assert out["diagnostics"]["converged"] is False
    assert out["diagnostics"]["feasible"] is False
    assert out["diagnostics"]["constraint_violation"] >= 0.5
