"""Property-based tests for electrical.per_unit_conversion."""

from __future__ import annotations

import math
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_POS = st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False)
_BASE_V = st.floats(min_value=100.0, max_value=1e6, allow_nan=False, allow_infinity=False)
_BASE_S = st.floats(min_value=1e3, max_value=1e10, allow_nan=False, allow_infinity=False)


@settings(deadline=None)
@given(v=_BASE_V, s=_BASE_S, z=_POS)
def test_impedance_round_trip(v: float, s: float, z: float) -> None:
    bases = {
        "phase_count": 1,
        "voltage_base": {"value": v, "unit": "V"},
        "power_base": {"value": s, "unit": "W"},
    }
    pu = implementation.execute(
        {
            **bases,
            "operation": "to_per_unit",
            "quantity_kind": "impedance",
            "value": {"value": z, "unit": "ohm"},
        }
    )["result"]["value_pu"]
    back = implementation.execute(
        {
            **bases,
            "operation": "from_per_unit",
            "quantity_kind": "impedance",
            "value_pu": pu,
        }
    )["result"]["value_actual"]["value"]
    assert math.isclose(back, z, rel_tol=1e-9)


@settings(deadline=None)
@given(
    v=_BASE_V,
    s=_BASE_S,
    pu=st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_change_base_identity_when_bases_equal(v: float, s: float, pu: float) -> None:
    out = implementation.execute(
        {
            "operation": "change_base",
            "phase_count": 3,
            "voltage_base": {"value": v, "unit": "V"},
            "power_base": {"value": s, "unit": "W"},
            "value_pu": pu,
            "new_voltage_base": {"value": v, "unit": "V"},
            "new_power_base": {"value": s, "unit": "W"},
        }
    )["result"]
    assert math.isclose(out["value_pu"], pu, rel_tol=1e-12)
