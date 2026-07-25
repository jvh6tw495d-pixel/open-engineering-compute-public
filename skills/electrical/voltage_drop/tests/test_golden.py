"""Golden cases for electrical.voltage_drop, per plan section 12.6.

Expected values are hand-derived closed form (see examples' descriptions)
-- never by trusting the implementation under test.
"""

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-9) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="electrical.voltage_drop",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form: dV=2*I*L*(R cos + X sin) or sqrt(3)*..., see references.md",
        justification=data["description"],
    )


def test_single_phase_current_matches_example() -> None:
    golden = _golden_from_example("single_phase_current.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_three_phase_material_matches_example() -> None:
    golden = _golden_from_example("three_phase_material.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_single_phase_from_power_matches_example() -> None:
    golden = _golden_from_example("single_phase_from_power.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_power_path_matches_equivalent_current_path() -> None:
    """1840 W at 230 V / 0.8 PF is exactly 10 A — both load_types must agree."""
    from_current = implementation.execute(
        {
            "load_type": "current",
            "phase_count": 1,
            "voltage_reference": {"value": 230.0, "unit": "V"},
            "power_factor": 0.8,
            "length": {"value": 50.0, "unit": "m"},
            "current": {"value": 10.0, "unit": "A"},
            "resistance_per_length": {"value": 0.001, "unit": "ohm/m"},
        }
    )["result"]
    from_power = implementation.execute(
        {
            "load_type": "power",
            "phase_count": 1,
            "voltage_reference": {"value": 230.0, "unit": "V"},
            "power_factor": 0.8,
            "length": {"value": 50.0, "unit": "m"},
            "power": {"value": 1840.0, "unit": "W"},
            "resistance_per_length": {"value": 0.001, "unit": "ohm/m"},
        }
    )["result"]
    assert from_current["voltage_drop"] == from_power["voltage_drop"]
    assert from_current["current_used"] == from_power["current_used"]


def test_power_factor_type_defaults_to_lagging() -> None:
    inputs = {
        "load_type": "current",
        "phase_count": 1,
        "voltage_reference": {"value": 230.0, "unit": "V"},
        "power_factor": 0.8,
        "length": {"value": 50.0, "unit": "m"},
        "current": {"value": 10.0, "unit": "A"},
        "resistance_per_length": {"value": 0.001, "unit": "ohm/m"},
        "reactance_per_length": {"value": 0.0005, "unit": "ohm/m"},
    }
    out = implementation.execute(inputs)
    assert out["result"]["power_factor_type"] == "lagging"
