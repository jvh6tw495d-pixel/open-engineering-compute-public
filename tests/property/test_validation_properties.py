"""Property-based tests for mathematical and physical validation helpers."""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from oec.validation.base import Severity
from oec.validation.mathematical import require_in_range
from oec.validation.physical import require_above_absolute_zero

_FINITE = st.floats(allow_nan=False, allow_infinity=False, width=64)
_TEMP_UNITS = st.sampled_from(["kelvin", "K", "degC", "degF"])


@settings(deadline=None, max_examples=100)
@given(
    low=_FINITE,
    high=_FINITE,
    value=_FINITE,
)
def test_require_in_range_matches_closed_interval(low: float, high: float, value: float) -> None:
    """For any finite bounds, severity is OK iff value is inside [min, max]."""
    minimum, maximum = (low, high) if low <= high else (high, low)
    # Skip degenerate float ranges where comparison is not reliable.
    assume(minimum < maximum or minimum == maximum)

    outcome = require_in_range("x", value, minimum=minimum, maximum=maximum)
    if minimum <= value <= maximum:
        assert outcome.severity == Severity.OK
    else:
        assert outcome.severity == Severity.ERROR


@settings(deadline=None, max_examples=100)
@given(
    value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    unit=_TEMP_UNITS,
)
def test_require_above_absolute_zero_consistent_with_kelvin(value: float, unit: str) -> None:
    """OK iff the temperature converts to a strictly positive kelvin magnitude."""
    from oec.kernel.units.registry import ureg

    try:
        kelvin = float(ureg.Quantity(value, unit).to("kelvin").magnitude)
    except Exception:
        # Incompatible / unconvertible — helper should error too.
        assert require_above_absolute_zero("T", value, unit).severity == Severity.ERROR
        return

    outcome = require_above_absolute_zero("T", value, unit)
    if kelvin > 0.0:
        assert outcome.severity == Severity.OK
    else:
        assert outcome.severity == Severity.ERROR
