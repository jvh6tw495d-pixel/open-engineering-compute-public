"""Unit tests for electrical.current_from_power's own validation.py (CurrentFromPowerValidator)."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
CurrentFromPowerValidator = _validation_module.CurrentFromPowerValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = CurrentFromPowerValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def _base(**overrides: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "power": {"value": 1000.0, "unit": "W"},
        "power_type": "active",
        "voltage": {"value": 230.0, "unit": "V"},
        "phase_count": 1,
        "power_factor": 0.9,
    }
    inputs.update(overrides)
    return inputs


def test_valid_active_input_has_no_errors() -> None:
    assert _errors(_base()) == []


def test_valid_apparent_input_has_no_errors() -> None:
    inputs = _base(power_type="apparent")
    del inputs["power_factor"]
    assert _errors(inputs) == []


def test_active_without_power_factor_is_an_error() -> None:
    inputs = _base()
    del inputs["power_factor"]
    errors = _errors(inputs)
    assert any("power_factor" in e for e in errors)


def test_apparent_with_power_factor_is_an_error() -> None:
    errors = _errors(_base(power_type="apparent"))
    assert any("power_factor" in e for e in errors)


def test_zero_power_is_an_error() -> None:
    errors = _errors(_base(power={"value": 0.0, "unit": "W"}))
    assert any("power" in e for e in errors)


def test_negative_voltage_is_an_error() -> None:
    errors = _errors(_base(voltage={"value": -230.0, "unit": "V"}))
    assert any("voltage" in e for e in errors)


def test_layer_class_attribute() -> None:
    assert CurrentFromPowerValidator.layer == "physical"
