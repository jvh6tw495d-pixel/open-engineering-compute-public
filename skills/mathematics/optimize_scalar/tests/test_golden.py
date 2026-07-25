"""Golden cases for mathematics.optimize_scalar, per plan section 12.6.

Reference minimizers are derived independently of SciPy, via the
first-derivative-zero / second-derivative-sign test (closed form,
Press et al. Numerical Recipes Sec. 10.1) — never by trusting the
solver under test to have found the right answer (plan section 22).
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
        skill_id="mathematics.optimize_scalar",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form (f'=0, sign of f''), see references.md #2",
        justification=data["description"],
    )


def test_quadratic_bounded_matches_example() -> None:
    """Global minimum of an unconstrained quadratic, found by bounded Brent."""
    golden = _golden_from_example("quadratic_bounded.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)
    assert implementation.execute(golden.inputs)["diagnostics"]["converged"] is True


def test_quadratic_unbounded_brent_matches_example() -> None:
    golden = _golden_from_example("quadratic_unbounded_brent.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_double_well_left_local_minimum() -> None:
    """f(x) = x^4 - x^2 has two GLOBAL minima (tied), at x = +-1/sqrt(2),
    fun = -0.25 -- independently derived from f'(x) = 4x^3 - 2x = 0
    (roots x in {0, +-1/sqrt(2)}) and f''(x) = 12x^2 - 2 (positive at
    +-1/sqrt(2), confirming a minimum; negative at 0, confirming a local
    maximum there instead). Restricting `bounds` to [-2, 0] finds the
    LEFT one -- this is the skill's documented multi-minima behavior
    (skill.md "Assumptions"): it returns whichever minimum the given
    bracket contains, not a global search across all basins."""
    golden = GoldenCase(
        id="double-well-left",
        skill_id="mathematics.optimize_scalar",
        skill_version="0.1.0",
        inputs={"expression": "x**4 - x**2", "bounds": [-2, 0], "method": "bounded"},
        expected_result={"x": -1.0 / math.sqrt(2), "fun": -0.25},
        tolerance=1e-6,
        source="closed form: f'(x)=4x^3-2x=0, f''(x)=12x^2-2>0 at x=-1/sqrt(2)",
        justification="multi-minima case: bounded search finds the minimum inside its bracket",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden({"x": out["result"]["x"], "fun": out["result"]["fun"]}, golden)
    assert out["diagnostics"]["converged"] is True


def test_double_well_right_local_minimum() -> None:
    """Symmetric counterpart of test_double_well_left_local_minimum:
    bounds=[0, 2] finds the RIGHT minimum, x = +1/sqrt(2), same fun.
    Both are simultaneously global minima of the unbounded function --
    the skill has no way to know that from a single bounded call."""
    golden = GoldenCase(
        id="double-well-right",
        skill_id="mathematics.optimize_scalar",
        skill_version="0.1.0",
        inputs={"expression": "x**4 - x**2", "bounds": [0, 2], "method": "bounded"},
        expected_result={"x": 1.0 / math.sqrt(2), "fun": -0.25},
        tolerance=1e-6,
        source="closed form: f'(x)=4x^3-2x=0, f''(x)=12x^2-2>0 at x=1/sqrt(2)",
        justification="multi-minima case: opposite bracket, opposite (but tied-fun) minimum",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden({"x": out["result"]["x"], "fun": out["result"]["fun"]}, golden)
    assert out["diagnostics"]["converged"] is True


def test_max_iterations_exhausted_is_not_converged() -> None:
    """A budget of 1 iteration on an otherwise-easy quadratic must not
    silently report success -- diagnostics.converged is False and the
    result is not to be trusted as a minimizer (skill.md "Failure
    conditions"). Mirrors solve_root's iteration-budget test."""
    out = implementation.execute(
        {"expression": "(x - 3)**2", "bounds": [0, 10], "method": "bounded", "max_iterations": 1}
    )
    assert out["diagnostics"]["converged"] is False
    assert out["diagnostics"]["n_iterations"] <= 2
