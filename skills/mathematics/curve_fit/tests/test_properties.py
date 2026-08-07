"""Property-based tests for mathematics.curve_fit.

Call implementation.execute() directly (in-process), not through the
sandboxed ExecutionService -- a subprocess per Hypothesis example would
make hundreds of examples per run unusably slow (same rationale as
optimize_scalar/optimize_constrained's test_properties.py).
"""

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


@settings(deadline=None)
@given(
    slope=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    intercept=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_noiseless_linear_data_always_recovers_true_parameters(
    slope: float, intercept: float
) -> None:
    """y = slope*x + intercept, noiseless, for any real slope/intercept --
    curve_fit's Levenberg-Marquardt should recover them (near-)exactly,
    since a linear model has a unique global least-squares optimum."""
    xdata = [0.0, 1.0, 2.0, 3.0, 4.0]
    ydata = [slope * x + intercept for x in xdata]
    out = implementation.execute(
        {
            "model": "a*x + b",
            "parameter_names": ["a", "b"],
            "x": xdata,
            "y": ydata,
            "initial_guess": [0.0, 0.0],
        }
    )
    assert out["diagnostics"]["converged"] is True
    assert math.isclose(out["result"]["params"][0], slope, rel_tol=1e-4, abs_tol=1e-4)
    assert math.isclose(out["result"]["params"][1], intercept, rel_tol=1e-4, abs_tol=1e-4)


@settings(deadline=None)
@given(
    scale=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_residuals_are_near_zero_on_a_noiseless_exact_fit(scale: float) -> None:
    """For noiseless data generated exactly from the model, residuals at
    the fitted solution must all be near zero -- an independent property
    of a correctly-converged exact fit, not derived from curve_fit
    itself (the residual formula yi - f(xi; popt) is defined identically
    regardless of which solver produced popt)."""
    xdata = [0.0, 1.0, 2.0, 3.0]
    ydata = [scale * x for x in xdata]
    out = implementation.execute(
        {
            "model": "a*x",
            "parameter_names": ["a"],
            "x": xdata,
            "y": ydata,
            "initial_guess": [1.0],
        }
    )
    assert out["diagnostics"]["converged"] is True
    assert all(abs(r) < 1e-6 for r in out["diagnostics"]["residuals"])
