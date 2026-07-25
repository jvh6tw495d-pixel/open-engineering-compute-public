"""Unit tests for PowerFactorCorrectionValidator."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
PowerFactorCorrectionValidator = _validation_module.PowerFactorCorrectionValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = PowerFactorCorrectionValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def _base(**overrides: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "active_power": {"value": 10000.0, "unit": "W"},
        "existing_power_factor": 0.8,
        "desired_power_factor": 0.95,
        "voltage": {"value": 380.0, "unit": "V"},
        "frequency": {"value": 50.0, "unit": "Hz"},
        "phase_count": 3,
        "connection": "delta",
    }
    inputs.update(overrides)
    return inputs


def test_valid_input_has_no_errors() -> None:
    assert _errors(_base()) == []


def test_phase1_with_delta_is_an_error() -> None:
    errors = _errors(_base(phase_count=1, connection="delta"))
    assert any("single_phase" in e for e in errors)


def test_phase3_with_single_phase_is_an_error() -> None:
    errors = _errors(_base(phase_count=3, connection="single_phase"))
    assert any("delta" in e or "star" in e for e in errors)


def test_desired_below_existing_is_an_error() -> None:
    errors = _errors(_base(existing_power_factor=0.95, desired_power_factor=0.8))
    assert any("desired_power_factor" in e for e in errors)


def test_zero_voltage_is_an_error() -> None:
    errors = _errors(_base(voltage={"value": 0.0, "unit": "V"}))
    assert any("voltage" in e for e in errors)


def test_layer_class_attribute() -> None:
    assert PowerFactorCorrectionValidator.layer == "physical"
