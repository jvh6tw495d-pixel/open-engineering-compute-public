"""Property-based tests for electrical.power_factor_correction."""

from __future__ import annotations

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_P = st.floats(min_value=100.0, max_value=1e6, allow_nan=False, allow_infinity=False)
_PF = st.floats(min_value=0.5, max_value=0.95, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(power=_P, existing=_PF)
def test_raising_pf_never_increases_reactive_demand(power: float, existing: float) -> None:
    desired = min(0.99, existing + 0.05)
    out = implementation.execute(
        {
            "active_power": {"value": power, "unit": "W"},
            "existing_power_factor": existing,
            "desired_power_factor": desired,
            "voltage": {"value": 400.0, "unit": "V"},
            "frequency": {"value": 50.0, "unit": "Hz"},
            "phase_count": 3,
            "connection": "delta",
        }
    )["result"]
    assert out["capacitor_reactive_power"]["value"] >= -1e-9
    assert out["desired_reactive_power"]["value"] <= out["existing_reactive_power"]["value"] + 1e-9


@settings(deadline=None)
@given(power=_P, existing=_PF)
def test_qc_matches_tan_difference(power: float, existing: float) -> None:
    desired = min(0.99, existing + 0.05)
    out = implementation.execute(
        {
            "active_power": {"value": power, "unit": "W"},
            "existing_power_factor": existing,
            "desired_power_factor": desired,
            "voltage": {"value": 230.0, "unit": "V"},
            "frequency": {"value": 60.0, "unit": "Hz"},
            "phase_count": 1,
            "connection": "single_phase",
        }
    )["result"]
    expected = power * (math.tan(math.acos(existing)) - math.tan(math.acos(desired)))
    assert math.isclose(out["capacitor_reactive_power"]["value"], expected, rel_tol=1e-9)
