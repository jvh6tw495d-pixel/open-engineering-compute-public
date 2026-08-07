"""Property-based tests for electrical.three_phase_power.

Call implementation.execute() directly (in-process), not through the
sandboxed ExecutionService -- matches every other skill's
test_properties.py (a subprocess per Hypothesis example would be
unusably slow).
"""

from __future__ import annotations

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_POSITIVE = st.floats(min_value=1e-3, max_value=1e5, allow_nan=False, allow_infinity=False)
_POWER_FACTOR = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_PF_TYPE = st.sampled_from(["lagging", "leading"])


@settings(deadline=None)
@given(voltage=_POSITIVE, current=_POSITIVE, power_factor=_POWER_FACTOR, pf_type=_PF_TYPE)
def test_power_triangle_identity_holds(
    voltage: float, current: float, power_factor: float, pf_type: str
) -> None:
    """S^2 = P^2 + Q^2 always -- the defining identity of the power
    triangle, independent of the specific voltage/current/PF chosen."""
    out = implementation.execute(
        {
            "voltage_line_to_line": {"value": voltage, "unit": "V"},
            "current_line": {"value": current, "unit": "A"},
            "power_factor": power_factor,
            "power_factor_type": pf_type,
        }
    )["result"]

    apparent = out["apparent_power"]["value"]
    active = out["active_power"]["value"]
    reactive = out["reactive_power"]["value"]

    assert math.isclose(apparent**2, active**2 + reactive**2, rel_tol=1e-9, abs_tol=1e-6)


@settings(deadline=None)
@given(voltage=_POSITIVE, current=_POSITIVE, power_factor=_POWER_FACTOR, pf_type=_PF_TYPE)
def test_apparent_power_is_always_nonnegative(
    voltage: float, current: float, power_factor: float, pf_type: str
) -> None:
    out = implementation.execute(
        {
            "voltage_line_to_line": {"value": voltage, "unit": "V"},
            "current_line": {"value": current, "unit": "A"},
            "power_factor": power_factor,
            "power_factor_type": pf_type,
        }
    )["result"]
    assert out["apparent_power"]["value"] >= 0.0


@settings(deadline=None)
@given(voltage=_POSITIVE, current=_POSITIVE)
def test_doubling_current_doubles_all_powers(voltage: float, current: float) -> None:
    """Every power quantity is linear in current (fixed V, PF) -- a
    direct consequence of S = sqrt(3)*V*I."""
    base = implementation.execute(
        {
            "voltage_line_to_line": {"value": voltage, "unit": "V"},
            "current_line": {"value": current, "unit": "A"},
            "power_factor": 0.85,
        }
    )["result"]
    doubled = implementation.execute(
        {
            "voltage_line_to_line": {"value": voltage, "unit": "V"},
            "current_line": {"value": 2.0 * current, "unit": "A"},
            "power_factor": 0.85,
        }
    )["result"]

    assert math.isclose(doubled["apparent_power"]["value"], 2.0 * base["apparent_power"]["value"])
    assert math.isclose(doubled["active_power"]["value"], 2.0 * base["active_power"]["value"])
    assert math.isclose(doubled["reactive_power"]["value"], 2.0 * base["reactive_power"]["value"])
