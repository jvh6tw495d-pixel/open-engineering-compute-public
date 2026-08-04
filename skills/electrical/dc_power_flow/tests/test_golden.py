"""Golden cases for electrical.dc_power_flow.

Numeric fields (angles/flows/node_balance/balance) are hand-derived
independently of ``dc_power_flow`` -- never by trusting the
implementation under test. ``assumptions`` is compared against the
imported ``DC_POWER_FLOW_ASSUMPTIONS`` constant since that field is
documentation content passed through verbatim, not a physics result.
"""

import json
from pathlib import Path

import pytest

from oec.physics.electrical import DC_POWER_FLOW_ASSUMPTIONS
from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_ASSUMPTIONS = [assumption.model_dump(mode="json") for assumption in DC_POWER_FLOW_ASSUMPTIONS]


def test_three_bus_triangle_matches_hand_solved_balanced_flow() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "three_bus_balanced.json").read_text(encoding="utf-8")
    )
    inputs = data["input"]

    # Hand-solved oracle: reduced susceptance matrix for non-slack buses B, C
    # is [[20, -10], [-10, 20]] (each diagonal = sum of adjacent line
    # susceptances; off-diagonal = -susceptance of the connecting line).
    # theta = B_reduced^-1 @ [0.4, 0.6], via the explicit 2x2 inverse
    # (1/det) * [[20, 10], [10, 20]], det = 20*20 - 10*10 = 300.
    theta_b = (20.0 * 0.4 + 10.0 * 0.6) / 300.0
    theta_c = (10.0 * 0.4 + 20.0 * 0.6) / 300.0
    p_ab = 10.0 * (0.0 - theta_b)
    p_bc = 10.0 * (theta_b - theta_c)
    p_ac = 10.0 * (0.0 - theta_c)

    zero_check = {
        "residual": 0.0,
        "balanced": True,
        "atol": 1e-9,
        "rtol": 1e-9,
        "scale": 1.0,
        "unit": "pu",
    }

    golden = GoldenCase(
        id="three_bus_balanced.json",
        skill_id="electrical.dc_power_flow",
        skill_version="0.1.0",
        inputs=inputs,
        expected_result={
            "slack_bus": "A",
            "angles": {"A": 0.0, "B": theta_b, "C": theta_c},
            "flows": [
                {"from_bus": "A", "to_bus": "B", "power": p_ab},
                {"from_bus": "B", "to_bus": "C", "power": p_bc},
                {"from_bus": "A", "to_bus": "C", "power": p_ac},
            ],
            "node_balance": {"A": zero_check, "B": zero_check, "C": zero_check},
            "balance": zero_check,
            "assumptions": _ASSUMPTIONS,
        },
        tolerance=1e-9,
        source=(
            "hand-solved: theta = B_reduced^-1 P_reduced (2x2 explicit inverse); "
            "sum(injections)==0 on a lossless network forces an exact KCL balance"
        ),
        justification=data["description"],
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_unbalanced_injections_produce_a_nonzero_slack_residual() -> None:
    """sum(injections) != 0 on a lossless network must surface as a residual."""
    out = implementation.execute(
        {
            "lines": [{"from_bus": "A", "to_bus": "B", "susceptance": 5.0}],
            "injections": {"A": -1.0, "B": 0.5},
            "slack_bus": "A",
        }
    )["result"]

    assert out["balance"]["balanced"] is False
    # theta_B = 0.5 / 5 = 0.1; flow A->B = 5*(0-0.1) = -0.5; outflow[A] = -0.5.
    # residual_A = injection_A - outflow_A = -1.0 - (-0.5) = -0.5; residual_B = 0.
    assert out["balance"]["residual"] == pytest.approx(-0.5, abs=1e-9)


def test_atol_rtol_overrides_are_forwarded() -> None:
    out = implementation.execute(
        {
            "lines": [{"from_bus": "A", "to_bus": "B", "susceptance": 5.0}],
            "injections": {"A": -1.0, "B": 0.5},
            "slack_bus": "A",
            "atol": 1.0,
            "rtol": 0.0,
        }
    )["result"]
    assert out["balance"]["atol"] == 1.0
    assert out["balance"]["balanced"] is True  # |residual|=0.5 <= atol=1.0
