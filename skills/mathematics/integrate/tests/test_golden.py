"""Golden cases for mathematics.integrate, per plan section 12.6.

Reference integrals were computed independently with mpmath.quad (and
closed forms where available) — never from SciPy's quad/simpson under
test (plan section 22).
"""

import json
import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-9) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="mathematics.integrate",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="mpmath.quad / closed form (independent of SciPy), see references.md #4",
        justification=data["description"],
    )


def test_function_sin_matches_example() -> None:
    golden = _golden_from_example("function_sin.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)
    assert implementation.execute(golden.inputs)["diagnostics"]["converged"] is True


def test_function_x_squared_matches_example() -> None:
    golden = _golden_from_example("function_x_squared.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_tabulated_x_squared_matches_example() -> None:
    golden = _golden_from_example("tabulated_x_squared.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)
    # ADR 0013 amendment: tabulated mode is exact, so `converged` is a
    # present-but-null "not applicable" signal, not `True` -- eligible
    # for VERIFIED just like an iterative:false skill's result.
    assert implementation.execute(golden.inputs)["diagnostics"]["converged"] is None
    assert implementation.execute(golden.inputs)["diagnostics"]["method"] == "simpson"


def test_gaussian_bump_function_mode() -> None:
    """∫_0^1 exp(-x^2) dx ≈ 0.7468241328124271 (mpmath.quad oracle)."""
    golden = GoldenCase(
        id="function-exp-neg-x2",
        skill_id="mathematics.integrate",
        skill_version="0.1.0",
        inputs={"expression": "exp(-x**2)", "bounds": [0.0, 1.0]},
        expected_result={"value": 0.7468241328124271, "mode": "function"},
        tolerance=1e-9,
        source="mpmath.quad(lambda x: mpmath.exp(-x**2), [0, 1])",
        justification="standard smooth integrand; independent high-precision reference",
    )
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_tabulated_trapezoid_two_points_of_linear() -> None:
    """Two samples of y=x on [0, 1]: trapezoid (auto) equals closed form 0.5."""
    golden = GoldenCase(
        id="tabulated-trapezoid-linear",
        skill_id="mathematics.integrate",
        skill_version="0.1.0",
        inputs={"x": [0.0, 1.0], "y": [0.0, 1.0]},
        expected_result={"value": 0.5, "mode": "tabulated"},
        tolerance=1e-12,
        source="closed form ∫_0^1 x dx = 1/2",
        justification="len(x)==2 forces trapezoid; exact on linear data",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)
    assert out["diagnostics"]["method"] == "trapezoid"
    assert out["diagnostics"]["converged"] is None


def test_quadpack_problem_is_reported_not_masked() -> None:
    """A genuinely hard integrand (oscillatory near 0, tight tolerance)
    makes QUADPACK hit its subdivision limit -- converged must be False
    and the reason must be surfaced, not hidden behind a small abs_error
    (independent review of Sprint 04: relying on abs_error<=tolerance
    alone is a false-convergence risk for exactly this class of integrand)."""
    out = implementation.execute(
        {
            "expression": "sin(1/x)",
            "bounds": [0.0001, 1.0],
            "epsabs": 1e-14,
            "epsrel": 1e-14,
        }
    )
    assert out["diagnostics"]["converged"] is False
    assert "quadpack_message" in out["diagnostics"]
    assert "subdivisions" in out["diagnostics"]["quadpack_message"]


def test_function_sin_uses_math_pi_bound() -> None:
    """Same sin integral with math.pi bound (sanity vs example's literal)."""
    out = implementation.execute({"expression": "sin(x)", "bounds": [0.0, math.pi]})
    assert out["result"]["mode"] == "function"
    assert math.isclose(out["result"]["value"], 2.0, rel_tol=1e-12, abs_tol=1e-12)
