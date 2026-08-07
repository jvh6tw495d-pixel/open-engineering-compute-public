"""Golden cases for electrical.transformer_loading."""

import json
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_from_example(filename: str, *, tolerance: float = 1e-9) -> GoldenCase:
    data = json.loads((_SKILL_DIR / "examples" / filename).read_text(encoding="utf-8"))
    # Golden examples store kVA inputs as a human would write them; the
    # implementation receives ADR-0016-normalized watts. Convert here so
    # direct execute() calls match the e2e path.
    inputs = data["input"]
    return GoldenCase(
        id=filename,
        skill_id="electrical.transformer_loading",
        skill_version="0.1.0",
        inputs=_normalize_for_direct_call(inputs),
        expected_result=data["expected_output"],
        tolerance=tolerance,
        source="closed form: loading=100*S_load/S_rated",
        justification=data["description"],
    )


def _normalize_for_direct_call(inputs: dict) -> dict:
    """Convert kVA/A example values to the canonical units implementation sees."""
    out = dict(inputs)
    for key in ("rated_apparent_power", "load_apparent_power"):
        if key in out and out[key].get("unit") == "kVA":
            out[key] = {"value": float(out[key]["value"]) * 1000.0, "unit": "W"}
    return out


def test_underloaded_kva_matches_example() -> None:
    golden = _golden_from_example("underloaded_kva.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_overloaded_current_matches_example() -> None:
    golden = _golden_from_example("overloaded_current.json")
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_custom_threshold_can_warn_below_100() -> None:
    out = implementation.execute(
        {
            "rated_apparent_power": {"value": 1_000_000.0, "unit": "W"},
            "load_type": "apparent_power",
            "load_apparent_power": {"value": 900_000.0, "unit": "W"},
            "overload_threshold_percent": 85.0,
        }
    )["result"]
    assert out["loading_percent"] == 90.0
    assert out["overload_warning"] is True


def test_current_ratio_matches_power_ratio() -> None:
    via_power = implementation.execute(
        {
            "rated_apparent_power": {"value": 500_000.0, "unit": "W"},
            "load_type": "apparent_power",
            "load_apparent_power": {"value": 250_000.0, "unit": "W"},
        }
    )["result"]
    via_current = implementation.execute(
        {
            "rated_apparent_power": {"value": 500_000.0, "unit": "W"},
            "load_type": "current",
            "load_current": {"value": 50.0, "unit": "A"},
            "rated_current": {"value": 100.0, "unit": "A"},
        }
    )["result"]
    assert via_power["loading_percent"] == via_current["loading_percent"]
