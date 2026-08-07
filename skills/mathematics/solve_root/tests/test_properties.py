"""Property-based tests for mathematics.solve_root.

Call implementation.execute() directly (in-process), not through the
sandboxed ExecutionService -- a subprocess per Hypothesis example would
make hundreds of examples per run unusably slow (flagged in the
independent Sprint 03 review). oec.execution.runner's own tests cover
the sandboxing behavior separately.
"""

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

# f(x) = x - c has the exact, independently-known root x = c for any c.
_ROOTS = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(root=_ROOTS)
def test_linear_root_recovered_from_bracket(root: float) -> None:
    output = implementation.execute(
        {"expression": f"x - ({root!r})", "bracket": [root - 1000.0, root + 1000.0]}
    )
    assert output["diagnostics"]["converged"] is True
    assert math.isclose(output["result"]["root"], root, rel_tol=1e-6, abs_tol=1e-6)


@settings(deadline=None)
@given(root=st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False))
def test_linear_root_recovered_from_initial_guess(root: float) -> None:
    output = implementation.execute({"expression": f"x - ({root!r})", "initial_guess": root + 1.0})
    assert output["diagnostics"]["converged"] is True
    assert math.isclose(output["result"]["root"], root, rel_tol=1e-6, abs_tol=1e-6)


@settings(deadline=None)
@given(positive=st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_square_root_of_a_positive_number(positive: float) -> None:
    """x^2 - c has root sqrt(c) for c > 0 -- math.sqrt is the independent oracle."""
    output = implementation.execute(
        {"expression": f"x**2 - ({positive!r})", "bracket": [0, max(positive, 1.0) + 1.0]}
    )
    assert output["diagnostics"]["converged"] is True
    assert math.isclose(output["result"]["root"], math.sqrt(positive), rel_tol=1e-6)
