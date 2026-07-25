"""Property-based tests for mathematics.optimize_scalar.

Call implementation.execute() directly (in-process), not through the
sandboxed ExecutionService -- a subprocess per Hypothesis example would
make hundreds of examples per run unusably slow (same rationale as
solve_root's test_properties.py).
"""

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_CENTERS = st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(center=_CENTERS)
def test_quadratic_minimum_recovered_bounded(center: float) -> None:
    """(x - c)^2 has the exact, independently-known minimum x = c, fun = 0,
    for any real c -- found via bounded Brent on a bracket around c."""
    output = implementation.execute(
        {
            "expression": f"(x - ({center!r}))**2",
            "bounds": [center - 1000.0, center + 1000.0],
            "method": "bounded",
        }
    )
    assert output["diagnostics"]["converged"] is True
    assert math.isclose(output["result"]["x"], center, rel_tol=1e-4, abs_tol=1e-4)
    assert math.isclose(output["result"]["fun"], 0.0, abs_tol=1e-6)


@settings(deadline=None)
@given(center=st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False))
def test_quadratic_minimum_recovered_unbounded_brent(center: float) -> None:
    output = implementation.execute({"expression": f"(x - ({center!r}))**2", "method": "brent"})
    assert output["diagnostics"]["converged"] is True
    assert math.isclose(output["result"]["x"], center, rel_tol=1e-4, abs_tol=1e-4)


@settings(deadline=None)
@given(
    a=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    center=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_scaled_quadratic_fun_at_minimum_is_zero(a: float, center: float) -> None:
    """a*(x - c)^2 always has fun = 0 at its minimum, regardless of the
    scale a > 0 -- an independent property of any scaled square term."""
    output = implementation.execute(
        {
            "expression": f"({a!r})*(x - ({center!r}))**2",
            "bounds": [center - 500.0, center + 500.0],
            "method": "bounded",
        }
    )
    assert output["diagnostics"]["converged"] is True
    assert math.isclose(output["result"]["fun"], 0.0, abs_tol=1e-5)
