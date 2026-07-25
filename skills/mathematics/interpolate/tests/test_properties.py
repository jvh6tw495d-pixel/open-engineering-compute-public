"""Property-based tests for mathematics.interpolate.

Call implementation.execute() directly (in-process), not through the
sandboxed ExecutionService — a subprocess per Hypothesis example would
make hundreds of examples per run unusably slow. oec.execution.runner's
own tests cover the sandboxing behavior separately.
"""

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_FINITE = st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False)


@settings(deadline=None, max_examples=50)
@given(
    gaps=st.lists(
        st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=8,
    ),
    y_vals=st.lists(_FINITE, min_size=3, max_size=3),
)
def test_linear_recovers_sample_points(gaps: list[float], y_vals: list[float]) -> None:
    """Evaluating the linear interpolant at the sample abscissae returns y."""
    # pad/trim y to match x length
    x = [0.0]
    for g in gaps:
        x.append(x[-1] + g)
    y = (y_vals * ((len(x) // len(y_vals)) + 1))[: len(x)]
    output = implementation.execute({"x": x, "y": y, "query_points": list(x), "method": "linear"})
    values = output["result"]["values"]
    assert len(values) == len(y)
    for actual, expected in zip(values, y, strict=True):
        assert abs(actual - expected) < 1e-9


@settings(deadline=None, max_examples=40)
@given(
    gaps=st.lists(
        st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=6,
    ),
    slope=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    intercept=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_linear_exact_on_affine_data(gaps: list[float], slope: float, intercept: float) -> None:
    """Linear interpolant of an affine function is exact at interior queries."""
    x = [0.0]
    for g in gaps:
        x.append(x[-1] + g)
    y = [slope * xi + intercept for xi in x]
    # midpoints of each segment
    queries = [(x[i] + x[i + 1]) / 2.0 for i in range(len(x) - 1)]
    expected = [slope * q + intercept for q in queries]
    output = implementation.execute({"x": x, "y": y, "query_points": queries, "method": "linear"})
    for actual, exp in zip(output["result"]["values"], expected, strict=True):
        assert abs(actual - exp) < 1e-9


@settings(deadline=None, max_examples=30)
@given(
    gaps=st.lists(
        st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
        min_size=4,
        max_size=6,
    ),
    a=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    b=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    c=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    d=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_cubic_spline_exact_on_cubics(
    gaps: list[float], a: float, b: float, c: float, d: float
) -> None:
    """Not-a-knot cubic spline recovers cubic polynomials exactly."""
    x = [0.0]
    for g in gaps:
        x.append(x[-1] + g)
    y = [a * xi**3 + b * xi**2 + c * xi + d for xi in x]
    queries = [(x[i] + x[i + 1]) / 2.0 for i in range(len(x) - 1)]
    expected = [a * q**3 + b * q**2 + c * q + d for q in queries]
    output = implementation.execute(
        {"x": x, "y": y, "query_points": queries, "method": "cubic_spline"}
    )
    for actual, exp in zip(output["result"]["values"], expected, strict=True):
        assert abs(actual - exp) < 1e-8


@settings(deadline=None, max_examples=30)
@given(
    n=st.integers(min_value=2, max_value=10),
    y0=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_pchip_preserves_constant(n: int, y0: float) -> None:
    """PCHIP of a constant series is the constant (shape preservation)."""
    x = [float(i) for i in range(n)]
    y = [y0] * n
    queries = [0.5 * i for i in range(2 * n - 1)]
    # clamp queries into [x[0], x[-1]] to avoid extrapolation edge cases
    queries = [min(max(q, x[0]), x[-1]) for q in queries]
    output = implementation.execute({"x": x, "y": y, "query_points": queries, "method": "pchip"})
    for actual in output["result"]["values"]:
        assert abs(actual - y0) < 1e-9
