"""Property-based tests for mathematics.integrate.

Call implementation.execute() directly (in-process), not through the
sandboxed ExecutionService — a subprocess per Hypothesis example would
make hundreds of examples per run unusably slow.
"""

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


@settings(deadline=None, max_examples=40)
@given(
    c=st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False),
    a=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    width=st.floats(min_value=1e-3, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_integral_of_constant(c: float, a: float, width: float) -> None:
    """∫_a^{a+w} c dx = c · w — independent closed form."""
    b = a + width
    out = implementation.execute({"expression": f"({c!r})", "bounds": [a, b]})
    assert out["diagnostics"]["converged"] is True
    assert math.isclose(out["result"]["value"], c * width, rel_tol=1e-6, abs_tol=1e-6)
    assert out["result"]["mode"] == "function"


@settings(deadline=None, max_examples=40)
@given(
    slope=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    a=st.floats(min_value=-20.0, max_value=20.0, allow_nan=False, allow_infinity=False),
    width=st.floats(min_value=0.1, max_value=20.0, allow_nan=False, allow_infinity=False),
)
def test_integral_of_linear(slope: float, a: float, width: float) -> None:
    """∫_a^b (slope · x) dx = slope/2 · (b² - a²)."""
    b = a + width
    out = implementation.execute({"expression": f"({slope!r})*x", "bounds": [a, b]})
    expected = slope / 2.0 * (b * b - a * a)
    assert out["diagnostics"]["converged"] is True
    assert math.isclose(out["result"]["value"], expected, rel_tol=1e-6, abs_tol=1e-6)


@settings(deadline=None, max_examples=30)
@given(
    n=st.integers(min_value=3, max_value=20),
    a=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    width=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
)
def test_tabulated_simpson_exact_on_quadratic(n: int, a: float, width: float) -> None:
    """Composite Simpson is exact for y = x² on any grid with ≥ 3 points."""
    b = a + width
    xs = [a + (b - a) * i / (n - 1) for i in range(n)]
    ys = [xi * xi for xi in xs]
    out = implementation.execute({"x": xs, "y": ys})
    expected = (b**3 - a**3) / 3.0
    assert out["result"]["mode"] == "tabulated"
    assert out["diagnostics"]["converged"] is True
    assert out["diagnostics"]["method"] == "simpson"
    assert math.isclose(out["result"]["value"], expected, rel_tol=1e-9, abs_tol=1e-9)


@settings(deadline=None, max_examples=30)
@given(
    a=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    b=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    ya=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    yb=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_tabulated_two_points_uses_trapezoid(a: float, b: float, ya: float, yb: float) -> None:
    """len(x)==2 always selects trapezoid; value is the trapezoid formula."""
    if a == b:
        b = a + 1.0
    if a > b:
        a, b = b, a
        ya, yb = yb, ya
    out = implementation.execute({"x": [a, b], "y": [ya, yb]})
    expected = (b - a) * (ya + yb) / 2.0
    assert out["diagnostics"]["method"] == "trapezoid"
    assert out["diagnostics"]["converged"] is True
    assert math.isclose(out["result"]["value"], expected, rel_tol=1e-9, abs_tol=1e-9)


@settings(deadline=None, max_examples=20)
@given(
    a=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    width=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_explicit_trapezoid_method_honoured(a: float, width: float) -> None:
    """method='trapezoid' is used even when Simpson would also apply."""
    b = a + width
    xs = [a, (a + b) / 2.0, b]
    ys = [1.0, 1.0, 1.0]  # constant → both rules give width * 1
    out = implementation.execute({"x": xs, "y": ys, "method": "trapezoid"})
    assert out["diagnostics"]["method"] == "trapezoid"
    assert math.isclose(out["result"]["value"], width, rel_tol=1e-9, abs_tol=1e-9)
