"""Golden cases for thermal.conduction_1d.

Expected values are hand-derived closed form (Q = k A dT / L) -- never by
trusting the implementation under test.
"""

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_planar_wall_heat_rate_and_trivial_balance() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "planar_wall.json").read_text(encoding="utf-8"))
    golden = GoldenCase(
        id="planar_wall.json",
        skill_id="thermal.conduction_1d",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result={
            "heat_rate": {"value": 2250.0, "unit": "W"},
            "balance": {
                "residual": 0.0,
                "balanced": True,
                "atol": 1e-6,
                "rtol": 1e-9,
                "scale": 2250.0,
                "unit": "W",
            },
        },
        tolerance=1e-9,
        source="closed form: Q = k * A * (T_hot - T_cold) / L = 1.5*0.5*60/0.02 = 2250 W",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_explicit_heat_out_produces_a_real_imbalance() -> None:
    out = implementation.execute(
        {
            "conductivity": {"value": 1.5, "unit": "W / (m * K)"},
            "area": {"value": 0.5, "unit": "m ** 2"},
            "length": {"value": 0.02, "unit": "m"},
            "hot_temperature": {"value": 80.0, "unit": "degC"},
            "cold_temperature": {"value": 20.0, "unit": "degC"},
            "heat_out": {"value": 2100.0, "unit": "W"},
        }
    )["result"]
    assert out["heat_rate"]["value"] == pytest.approx(2250.0)
    assert out["balance"]["residual"] == pytest.approx(150.0)
    assert out["balance"]["balanced"] is False


def test_hot_below_cold_temperature_raises() -> None:
    with pytest.raises(ValueError):
        implementation.execute(
            {
                "conductivity": {"value": 1.5, "unit": "W / (m * K)"},
                "area": {"value": 0.5, "unit": "m ** 2"},
                "length": {"value": 0.02, "unit": "m"},
                "hot_temperature": {"value": 10.0, "unit": "degC"},
                "cold_temperature": {"value": 20.0, "unit": "degC"},
            }
        )
