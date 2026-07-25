"""Unit tests for electrical.three_phase_power's own validation.py (ThreePhasePowerValidator)."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
ThreePhasePowerValidator = _validation_module.ThreePhasePowerValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = ThreePhasePowerValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def test_valid_input_has_no_errors() -> None:
    inputs = {
        "voltage_line_to_line": {"value": 380.0, "unit": "V"},
        "current_line": {"value": 10.0, "unit": "A"},
        "power_factor": 0.8,
    }
    assert _errors(inputs) == []


def test_zero_voltage_is_an_error() -> None:
    inputs = {
        "voltage_line_to_line": {"value": 0.0, "unit": "V"},
        "current_line": {"value": 10.0, "unit": "A"},
        "power_factor": 0.8,
    }
    errors = _errors(inputs)
    assert any("voltage_line_to_line" in e for e in errors)


def test_negative_current_is_an_error() -> None:
    inputs = {
        "voltage_line_to_line": {"value": 380.0, "unit": "V"},
        "current_line": {"value": -5.0, "unit": "A"},
        "power_factor": 0.8,
    }
    errors = _errors(inputs)
    assert any("current_line" in e for e in errors)


def test_missing_fields_are_not_this_validators_concern() -> None:
    """A missing field is a schema-layer error (required), not physical -- this
    validator only checks values that are actually present."""
    assert _errors({}) == []


def test_layer_class_attribute() -> None:
    assert ThreePhasePowerValidator.layer == "physical"
