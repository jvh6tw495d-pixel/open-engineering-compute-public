"""Golden cases for electrical.current_from_power, per plan section 12.6.

Expected values are derived from the closed-form formulas in
skill.md's "Mathematical formulation" (I = P/(V*PF) single-phase,
I = P/(sqrt(3)*V*PF) three-phase, apparent-power variants dropping PF)
via a fresh, independent computation -- never by trusting the
implementation under test.
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
        skill_id="electrical.current_from_power",
        skill_version="0.1.0",
        inputs=data["input"],
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form: I=P/(V*PF) or P/V, x sqrt(3) for three-phase, see references.md",
        justification=data["description"],
    )


def test_single_phase_active_matches_example() -> None:
    golden = _golden_from_example("single_phase_active.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_three_phase_apparent_matches_example() -> None:
    golden = _golden_from_example("three_phase_apparent.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_single_phase_active_with_efficiency_matches_example() -> None:
    golden = _golden_from_example("single_phase_active_with_efficiency.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_lower_efficiency_increases_current() -> None:
    """A lossier load draws more current for the same useful power output."""
    base_inputs = {
        "power": {"value": 1000.0, "unit": "W"},
        "power_type": "active",
        "voltage": {"value": 230.0, "unit": "V"},
        "phase_count": 1,
        "power_factor": 0.9,
    }
    full_efficiency = implementation.execute({**base_inputs, "efficiency": 1.0})["result"]
    lossy = implementation.execute({**base_inputs, "efficiency": 0.5})["result"]

    assert lossy["current"]["value"] > full_efficiency["current"]["value"]


def test_default_efficiency_is_one() -> None:
    inputs = {
        "power": {"value": 1000.0, "unit": "W"},
        "power_type": "active",
        "voltage": {"value": 230.0, "unit": "V"},
        "phase_count": 1,
        "power_factor": 0.9,
    }
    with_default = implementation.execute(inputs)["result"]
    with_explicit_one = implementation.execute({**inputs, "efficiency": 1.0})["result"]
    assert with_default == with_explicit_one
