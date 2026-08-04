"""Golden cases for mechanics.energy_1d.

Expected values are hand-derived closed form (free fall: KE_final = PE0)
-- never by trusting the implementation under test.
"""

import json
import math
from pathlib import Path

import pytest

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_G = 9.80665


def test_free_fall_matches_hand_solved_energy_conversion() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "free_fall.json").read_text(encoding="utf-8"))
    inputs = data["input"]

    mass = inputs["mass"]["value"]
    height0 = inputs["height_initial"]["value"]
    v_final = inputs["velocity_final"]["value"]

    pe0 = mass * _G * height0
    ke_final = 0.5 * mass * v_final * v_final

    golden = GoldenCase(
        id="free_fall.json",
        skill_id="mechanics.energy_1d",
        skill_version="0.1.0",
        inputs=inputs,
        expected_result={
            "kinetic_energy_initial": {"value": 0.0, "unit": "J"},
            "kinetic_energy_final": {"value": ke_final, "unit": "J"},
            "potential_energy_initial": {"value": pe0, "unit": "J"},
            "potential_energy_final": {"value": 0.0, "unit": "J"},
            "delta_kinetic": {"value": ke_final, "unit": "J"},
            "delta_potential": {"value": -pe0, "unit": "J"},
            "balance": {
                "residual": 0.0,
                "balanced": True,
                "atol": 1e-9,
                "rtol": 1e-9,
                "scale": pytest.approx(ke_final + pe0, rel=1e-6),
                "unit": "J",
            },
        },
        tolerance=1e-6,
        source="closed form: free fall converts PE0 = m g h0 entirely into KE_final = 1/2 m v^2",
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_explicit_losses_break_the_balance() -> None:
    out = implementation.execute(
        {
            "mass": {"value": 2.0, "unit": "kg"},
            "height_initial": {"value": 8.0, "unit": "m"},
            "height_final": {"value": 0.0, "unit": "m"},
            "velocity_initial": {"value": 0.0, "unit": "m / s"},
            "velocity_final": {"value": math.sqrt(2 * _G * 8.0), "unit": "m / s"},
            "losses": {"value": 10.0, "unit": "J"},
        }
    )["result"]
    assert out["balance"]["balanced"] is False
    assert out["balance"]["residual"] == pytest.approx(-10.0, abs=1e-6)


def test_gravity_override_is_applied() -> None:
    out = implementation.execute(
        {
            "mass": {"value": 1.0, "unit": "kg"},
            "height_initial": {"value": 1.0, "unit": "m"},
            "height_final": {"value": 0.0, "unit": "m"},
            "velocity_initial": {"value": 0.0, "unit": "m / s"},
            "velocity_final": {"value": 0.0, "unit": "m / s"},
            "gravity": {"value": 1.0, "unit": "m / s ** 2"},
        }
    )["result"]
    assert out["potential_energy_initial"]["value"] == pytest.approx(1.0)
