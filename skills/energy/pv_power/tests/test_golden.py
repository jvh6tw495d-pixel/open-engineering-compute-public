"""Golden cases for energy.pv_power."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_stc_simple() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "stc_simple.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])["result"]
    # P = 1000 * 10 * 0.2 = 2000 W
    assert out["power"] == {"value": 2000.0, "unit": "W"}
    assert out["temperature_factor"] == 1.0
    assert out["efficiency_effective"] == pytest.approx(0.2)


def test_temperature_correction() -> None:
    # f_temp = 1 + (-0.004)*(45-25) = 0.92; P = 1000*1*0.2*0.92 = 184
    out = implementation.execute(
        {
            "irradiance": {"value": 1000.0, "unit": "W / m ** 2"},
            "area": {"value": 1.0, "unit": "m ** 2"},
            "efficiency": 0.2,
            "temperature": {"value": 45.0, "unit": "degC"},
            "temperature_coefficient": -0.004,
        }
    )["result"]
    assert out["temperature_factor"] == pytest.approx(0.92)
    assert out["power"]["value"] == pytest.approx(184.0)
    assert out["efficiency_effective"] == pytest.approx(0.184)


def test_irradiance_unit_conversion() -> None:
    # 1 kW/m² = 1000 W/m²
    out = implementation.execute(
        {
            "irradiance": {"value": 1.0, "unit": "kW / m ** 2"},
            "area": {"value": 2.0, "unit": "m ** 2"},
            "efficiency": 0.15,
        }
    )["result"]
    assert out["power"]["value"] == pytest.approx(300.0)
