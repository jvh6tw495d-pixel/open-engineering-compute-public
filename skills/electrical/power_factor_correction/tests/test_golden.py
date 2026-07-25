"""Golden cases for electrical.power_factor_correction."""

import json
import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-9) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="electrical.power_factor_correction",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form: Qc=P*(tan phi1 - tan phi2); C=Qc/(n*w*V^2)",
        justification=data["description"],
    )


def test_three_phase_delta_matches_example() -> None:
    golden = _golden_from_example("three_phase_delta.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_single_phase_matches_example() -> None:
    golden = _golden_from_example("single_phase.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_star_capacitance_is_three_times_delta() -> None:
    """Same Q_c and V_LL: C_star = 3 * C_delta by the connection identities."""
    base = {
        "active_power": {"value": 100000.0, "unit": "W"},
        "existing_power_factor": 0.8,
        "desired_power_factor": 0.95,
        "voltage": {"value": 380.0, "unit": "V"},
        "frequency": {"value": 50.0, "unit": "Hz"},
        "phase_count": 3,
    }
    delta = implementation.execute({**base, "connection": "delta"})["result"]
    star = implementation.execute({**base, "connection": "star"})["result"]
    assert math.isclose(
        star["capacitance_per_unit"]["value"],
        3.0 * delta["capacitance_per_unit"]["value"],
        rel_tol=1e-12,
    )
    assert delta["capacitor_reactive_power"] == star["capacitor_reactive_power"]


def test_unity_desired_pf_drives_desired_q_to_zero() -> None:
    out = implementation.execute(
        {
            "active_power": {"value": 1000.0, "unit": "W"},
            "existing_power_factor": 0.8,
            "desired_power_factor": 1.0,
            "voltage": {"value": 230.0, "unit": "V"},
            "frequency": {"value": 50.0, "unit": "Hz"},
            "phase_count": 1,
            "connection": "single_phase",
        }
    )["result"]
    assert math.isclose(out["desired_reactive_power"]["value"], 0.0, abs_tol=1e-12)
