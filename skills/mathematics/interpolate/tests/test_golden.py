"""Golden cases for mathematics.interpolate, per plan section 12.6.

Reference ordinates come from closed-form evaluation of the sampled
function (exact linear / cubic polynomials, or ``math.sin``) — never
from re-running SciPy's interpolant under test (plan section 22).
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
        skill_id="mathematics.interpolate",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed-form / math.sin (independent of SciPy interpolants), see references.md #4",
        justification=data["description"],
    )


def test_linear_exact_matches_example() -> None:
    golden = _golden_from_example("linear_exact.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_cubic_spline_exact_matches_example() -> None:
    golden = _golden_from_example("cubic_spline_exact.json")
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_pchip_sin_matches_math_sin_within_interpolation_error() -> None:
    """PCHIP of sin samples is compared to math.sin, not to SciPy's PCHIP.

    Tolerance is loose enough for interpolation error on a 0.5-step grid
    (~2e-2 observed) while still catching a broken method selection or
    swapped axes.
    """
    golden = _golden_from_example("pchip_sin.json", tolerance=2e-2)
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)


def test_linear_sin_against_math_sin() -> None:
    """Independent linear case: sample sin, compare queries to math.sin."""
    xs = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    ys = [math.sin(x) for x in xs]
    qs = [0.25, 0.75, 1.25, 1.75, 2.25]
    golden = GoldenCase(
        id="linear-sin-vs-math",
        skill_id="mathematics.interpolate",
        skill_version="0.1.0",
        inputs={"x": xs, "y": ys, "query_points": qs, "method": "linear"},
        expected_result={"values": [math.sin(q) for q in qs]},
        # Piecewise-linear error on a 0.5-step sin grid is ~3e-2 at midpoints.
        tolerance=5e-2,
        source="math.sin (stdlib), independent of numpy.interp",
        justification="linear interpolant of sin samples vs true sin",
    )
    actual = implementation.execute(golden.inputs)["result"]
    assert_matches_golden(actual, golden)
