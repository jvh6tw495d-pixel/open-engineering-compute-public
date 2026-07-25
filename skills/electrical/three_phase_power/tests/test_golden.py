"""Golden cases for electrical.three_phase_power, per plan section 12.6.

Expected values are hand-derived closed form (S = sqrt(3)*V*I, P = S*PF,
Q = S*sin(acos(PF))) using 3-4-5-triangle power factors (0.8, 0.6) so
sin(acos(PF)) is exactly rational -- never by trusting the implementation
under test to have computed the right answer (plan section 22).
"""

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-6) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="electrical.three_phase_power",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form: S=sqrt(3)*V*I, P=S*PF, Q=S*sin(acos(PF)), see references.md",
        justification=data["description"],
    )


def test_lagging_0_8_matches_example() -> None:
    golden = _golden_from_example("lagging_0_8.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_unity_power_factor_matches_example() -> None:
    golden = _golden_from_example("unity_power_factor.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_leading_0_6_matches_example() -> None:
    golden = _golden_from_example("leading_0_6.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_lagging_and_leading_have_opposite_reactive_power_sign() -> None:
    """Same magnitudes, opposite power_factor_type -- Q must flip sign,
    P and S must be identical (only Q's direction depends on lag/lead)."""
    base_inputs = {
        "voltage_line_to_line": {"value": 400.0, "unit": "V"},
        "current_line": {"value": 10.0, "unit": "A"},
        "power_factor": 0.8,
    }
    lagging = implementation.execute({**base_inputs, "power_factor_type": "lagging"})["result"]
    leading = implementation.execute({**base_inputs, "power_factor_type": "leading"})["result"]

    assert lagging["reactive_power"]["value"] == -leading["reactive_power"]["value"]
    assert lagging["active_power"]["value"] == leading["active_power"]["value"]
    assert lagging["apparent_power"]["value"] == leading["apparent_power"]["value"]


def test_power_factor_type_defaults_to_lagging() -> None:
    inputs = {
        "voltage_line_to_line": {"value": 400.0, "unit": "V"},
        "current_line": {"value": 10.0, "unit": "A"},
        "power_factor": 0.8,
    }
    out = implementation.execute(inputs)
    assert out["result"]["power_factor_type"] == "lagging"
    assert out["result"]["reactive_power"]["value"] > 0
