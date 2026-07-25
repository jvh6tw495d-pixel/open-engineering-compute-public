"""Property-based tests for electrical.voltage_drop."""

from __future__ import annotations

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_POSITIVE = st.floats(min_value=1e-3, max_value=1e4, allow_nan=False, allow_infinity=False)
_PF = st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False)
_R = st.floats(min_value=1e-6, max_value=0.1, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(current=_POSITIVE, length=_POSITIVE, resistance=_R, power_factor=_PF)
def test_single_phase_drop_scales_with_current(
    current: float, length: float, resistance: float, power_factor: float
) -> None:
    base = implementation.execute(
        {
            "load_type": "current",
            "phase_count": 1,
            "voltage_reference": {"value": 230.0, "unit": "V"},
            "power_factor": power_factor,
            "length": {"value": length, "unit": "m"},
            "current": {"value": current, "unit": "A"},
            "resistance_per_length": {"value": resistance, "unit": "ohm/m"},
        }
    )["result"]["voltage_drop"]["value"]
    doubled = implementation.execute(
        {
            "load_type": "current",
            "phase_count": 1,
            "voltage_reference": {"value": 230.0, "unit": "V"},
            "power_factor": power_factor,
            "length": {"value": length, "unit": "m"},
            "current": {"value": 2.0 * current, "unit": "A"},
            "resistance_per_length": {"value": resistance, "unit": "ohm/m"},
        }
    )["result"]["voltage_drop"]["value"]
    assert math.isclose(doubled, 2.0 * base, rel_tol=1e-9)


@settings(deadline=None)
@given(current=_POSITIVE, length=_POSITIVE, resistance=_R, power_factor=_PF)
def test_three_phase_is_sqrt3_over_2_times_single_phase(
    current: float, length: float, resistance: float, power_factor: float
) -> None:
    """With X=0, three-phase dV / single-phase dV = sqrt(3) / 2."""
    common = {
        "load_type": "current",
        "voltage_reference": {"value": 400.0, "unit": "V"},
        "power_factor": power_factor,
        "length": {"value": length, "unit": "m"},
        "current": {"value": current, "unit": "A"},
        "resistance_per_length": {"value": resistance, "unit": "ohm/m"},
    }
    single = implementation.execute({**common, "phase_count": 1})["result"]["voltage_drop"]["value"]
    three = implementation.execute({**common, "phase_count": 3})["result"]["voltage_drop"]["value"]
    assert math.isclose(three, single * math.sqrt(3.0) / 2.0, rel_tol=1e-9)


@settings(deadline=None)
@given(cross_section=_POSITIVE)
def test_copper_resistance_is_rho_over_area(cross_section: float) -> None:
    out = implementation.execute(
        {
            "load_type": "current",
            "phase_count": 1,
            "voltage_reference": {"value": 230.0, "unit": "V"},
            "power_factor": 1.0,
            "length": {"value": 10.0, "unit": "m"},
            "current": {"value": 1.0, "unit": "A"},
            "material": "copper",
            "cross_section": {"value": cross_section, "unit": "mm^2"},
        }
    )["result"]
    expected_r = 0.017241 / cross_section
    assert math.isclose(out["resistance_per_length_used"]["value"], expected_r, rel_tol=1e-12)
