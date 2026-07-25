"""Golden cases for electrical.per_unit_conversion."""

import json
import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _normalize_bases(inputs: dict) -> dict:
    """Mirror ADR 0016 for bases so direct execute() matches e2e."""
    out = dict(inputs)
    conversions = {
        "voltage_base": ("kV", 1000.0, "V"),
        "new_voltage_base": ("kV", 1000.0, "V"),
        "power_base": ("MVA", 1_000_000.0, "W"),
        "new_power_base": ("MVA", 1_000_000.0, "W"),
    }
    for key, (from_unit, factor, to_unit) in conversions.items():
        if key in out and out[key].get("unit") == from_unit:
            out[key] = {"value": float(out[key]["value"]) * factor, "unit": to_unit}
    return out


def _golden_from_example(filename: str, *, tolerance: float = 1e-9) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    return GoldenCase(
        id=filename,
        skill_id="electrical.per_unit_conversion",
        skill_version="0.1.0",
        inputs=_normalize_bases(data["input"]),
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form: Z_pu=Z/Z_base, Z_base=V^2/S",
        justification=data["description"],
    )


def test_impedance_to_pu_matches_example() -> None:
    golden = _golden_from_example("impedance_to_pu.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_change_base_matches_example() -> None:
    golden = _golden_from_example("change_base.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_to_and_from_per_unit_round_trip() -> None:
    bases = {
        "phase_count": 3,
        "voltage_base": {"value": 13800.0, "unit": "V"},
        "power_base": {"value": 100_000_000.0, "unit": "W"},
    }
    to_pu = implementation.execute(
        {
            **bases,
            "operation": "to_per_unit",
            "quantity_kind": "voltage",
            "value": {"value": 13800.0, "unit": "V"},
        }
    )["result"]
    assert math.isclose(to_pu["value_pu"], 1.0, rel_tol=1e-12)
    back = implementation.execute(
        {
            **bases,
            "operation": "from_per_unit",
            "quantity_kind": "voltage",
            "value_pu": to_pu["value_pu"],
        }
    )["result"]
    assert math.isclose(back["value_actual"]["value"], 13800.0, rel_tol=1e-12)
