"""Property-based tests for electrical.current_from_power.

Call implementation.execute() directly (in-process), matching every
other skill's test_properties.py.
"""

from __future__ import annotations

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_POSITIVE = st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False)
_PF = st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(power=_POSITIVE, voltage=_POSITIVE, power_factor=_PF)
def test_single_phase_active_equals_three_phase_divided_by_sqrt3(
    power: float, voltage: float, power_factor: float
) -> None:
    """For the same P, V, PF: three-phase current is exactly the
    single-phase current divided by sqrt(3) -- a direct algebraic
    consequence of the two formulas differing only by that factor."""
    single = implementation.execute(
        {
            "power": {"value": power, "unit": "W"},
            "power_type": "active",
            "voltage": {"value": voltage, "unit": "V"},
            "phase_count": 1,
            "power_factor": power_factor,
        }
    )["result"]["current"]["value"]
    three = implementation.execute(
        {
            "power": {"value": power, "unit": "W"},
            "power_type": "active",
            "voltage": {"value": voltage, "unit": "V"},
            "phase_count": 3,
            "power_factor": power_factor,
        }
    )["result"]["current"]["value"]

    assert math.isclose(single / math.sqrt(3.0), three, rel_tol=1e-9)


@settings(deadline=None)
@given(power=_POSITIVE, voltage=_POSITIVE, power_factor=_PF)
def test_apparent_power_current_matches_active_at_unity_pf(
    power: float, voltage: float, power_factor: float
) -> None:
    """At PF=1, active and apparent power are numerically the same
    quantity, so the apparent-power path (no PF) must agree with the
    active-power path evaluated at power_factor=1 -- regardless of
    whatever PF is passed to the active-power call for OTHER cases."""
    del power_factor  # unused: this test fixes PF=1 for the active-power branch
    apparent = implementation.execute(
        {
            "power": {"value": power, "unit": "VA"},
            "power_type": "apparent",
            "voltage": {"value": voltage, "unit": "V"},
            "phase_count": 1,
        }
    )["result"]["current"]["value"]
    active_at_unity = implementation.execute(
        {
            "power": {"value": power, "unit": "W"},
            "power_type": "active",
            "voltage": {"value": voltage, "unit": "V"},
            "phase_count": 1,
            "power_factor": 1.0,
        }
    )["result"]["current"]["value"]

    assert math.isclose(apparent, active_at_unity, rel_tol=1e-9)


@settings(deadline=None)
@given(power=_POSITIVE, voltage=_POSITIVE)
def test_current_is_inversely_proportional_to_voltage(power: float, voltage: float) -> None:
    base = implementation.execute(
        {
            "power": {"value": power, "unit": "VA"},
            "power_type": "apparent",
            "voltage": {"value": voltage, "unit": "V"},
            "phase_count": 1,
        }
    )["result"]["current"]["value"]
    doubled_voltage = implementation.execute(
        {
            "power": {"value": power, "unit": "VA"},
            "power_type": "apparent",
            "voltage": {"value": 2.0 * voltage, "unit": "V"},
            "phase_count": 1,
        }
    )["result"]["current"]["value"]

    assert math.isclose(doubled_voltage, base / 2.0, rel_tol=1e-9)
