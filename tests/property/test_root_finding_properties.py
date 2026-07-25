"""Property tests call the kernel directly, never through the execution
sandbox -- a subprocess per Hypothesis example (hundreds per run) would
make the suite unusably slow (flagged in the independent Sprint 03
review)."""

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.kernel.numerics.root_finding import find_root_bracketed

# f(x) = x - c has an exact, trivially-known root at x = c, for any c.
# Using a closed-form root (not the solver's own output) as the oracle,
# per plan section 22's rule against self-referential golden values.
_ROOTS = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(root=_ROOTS)
def test_brentq_recovers_a_known_linear_root(root: float) -> None:
    def f(x: float) -> float:
        return x - root

    # Bracket [root - 1000, root + 1000] always contains the root and
    # has opposite-sign endpoints since f is monotonic increasing.
    result = find_root_bracketed(f, root - 1000.0, root + 1000.0, method="brentq")
    assert result.diagnostics.converged is True
    assert math.isclose(result.root, root, rel_tol=1e-6, abs_tol=1e-6)
