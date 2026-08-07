"""Golden cases for fluids.bernoulli.

Expected values are hand-derived closed form
(H = p/(rho g) + v^2/(2g) + z; h_L = f (L/D) v^2/(2g)) -- never by
trusting the implementation under test.
"""

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_G = 9.80665


def test_pipe_run_matches_hand_solved_head_balance() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "pipe_run.json").read_text(encoding="utf-8"))
    inputs = data["input"]

    p1 = inputs["pressure_upstream"]["value"]
    p2 = inputs["pressure_downstream"]["value"]
    v = inputs["velocity_upstream"]["value"]
    z = inputs["elevation_upstream"]["value"]
    rho = inputs["density"]["value"]
    f = inputs["friction_factor"]
    length = inputs["length"]["value"]
    diameter = inputs["diameter"]["value"]

    head_upstream = p1 / (rho * _G) + v * v / (2.0 * _G) + z
    head_downstream = p2 / (rho * _G) + v * v / (2.0 * _G) + z
    head_loss = f * (length / diameter) * v * v / (2.0 * _G)
    scale = max(abs(head_upstream), abs(head_downstream))

    golden = GoldenCase(
        id="pipe_run.json",
        skill_id="fluids.bernoulli",
        skill_version="0.1.0",
        inputs=inputs,
        expected_result={
            "head_upstream": {"value": head_upstream, "unit": "m"},
            "head_downstream": {"value": head_downstream, "unit": "m"},
            "head_loss": {"value": head_loss, "unit": "m"},
            "balance": {
                "residual": 0.0,
                "balanced": True,
                "atol": 1e-6,
                "rtol": 1e-9,
                "scale": scale,
                "unit": "m",
            },
        },
        tolerance=1e-9,
        source=(
            "closed form: H = p/(rho g) + v^2/(2g) + z; "
            "h_L = f (L/D) v^2/(2g); pressure drop chosen to match h_L"
        ),
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_unaccounted_pressure_drop_breaks_the_balance() -> None:
    """Same pipe as the golden, but downstream pressure too low for the loss."""
    out = implementation.execute(
        {
            "pressure_upstream": {"value": 300000.0, "unit": "Pa"},
            "pressure_downstream": {"value": 250000.0, "unit": "Pa"},
            "velocity_upstream": {"value": 2.0, "unit": "m / s"},
            "velocity_downstream": {"value": 2.0, "unit": "m / s"},
            "elevation_upstream": {"value": 10.0, "unit": "m"},
            "elevation_downstream": {"value": 10.0, "unit": "m"},
            "density": {"value": 1000.0, "unit": "kg / m ** 3"},
            "friction_factor": 0.02,
            "length": {"value": 50.0, "unit": "m"},
            "diameter": {"value": 0.1, "unit": "m"},
        }
    )["result"]

    # Hand residual: delta_p/(rho g) - h_L with delta_p = 50000 Pa
    expected_head_drop = 50000.0 / (1000.0 * _G)
    expected_loss = 0.02 * (50.0 / 0.1) * 4.0 / (2.0 * _G)
    assert out["balance"]["balanced"] is False
    assert out["balance"]["residual"] == pytest.approx(expected_head_drop - expected_loss, abs=1e-9)


def test_negative_friction_factor_raises() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        implementation.execute(
            {
                "pressure_upstream": {"value": 300000.0, "unit": "Pa"},
                "pressure_downstream": {"value": 280000.0, "unit": "Pa"},
                "velocity_upstream": {"value": 2.0, "unit": "m / s"},
                "velocity_downstream": {"value": 2.0, "unit": "m / s"},
                "elevation_upstream": {"value": 10.0, "unit": "m"},
                "elevation_downstream": {"value": 10.0, "unit": "m"},
                "density": {"value": 1000.0, "unit": "kg / m ** 3"},
                "friction_factor": -0.01,
                "length": {"value": 50.0, "unit": "m"},
                "diameter": {"value": 0.1, "unit": "m"},
            }
        )
