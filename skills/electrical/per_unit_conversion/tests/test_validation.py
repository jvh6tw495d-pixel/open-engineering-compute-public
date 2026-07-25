"""Unit tests for PerUnitConversionValidator."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
PerUnitConversionValidator = _validation_module.PerUnitConversionValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = PerUnitConversionValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def _base(**overrides: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "operation": "to_per_unit",
        "quantity_kind": "impedance",
        "phase_count": 3,
        "voltage_base": {"value": 13800.0, "unit": "V"},
        "power_base": {"value": 100_000_000.0, "unit": "W"},
        "value": {"value": 0.5, "unit": "ohm"},
    }
    inputs.update(overrides)
    return inputs


def test_valid_to_pu_has_no_errors() -> None:
    assert _errors(_base()) == []


def test_to_pu_without_value_is_an_error() -> None:
    inputs = _base()
    del inputs["value"]
    assert any("value" in e for e in _errors(inputs))


def test_wrong_value_unit_is_an_error() -> None:
    errors = _errors(_base(value={"value": 0.5, "unit": "V"}))
    assert any("ohm" in e or "convertible" in e for e in errors)


def test_change_base_requires_new_bases() -> None:
    errors = _errors(
        {
            "operation": "change_base",
            "phase_count": 3,
            "voltage_base": {"value": 13800.0, "unit": "V"},
            "power_base": {"value": 100_000_000.0, "unit": "W"},
            "value_pu": 0.1,
        }
    )
    assert any("new_voltage_base" in e for e in errors)


def test_zero_voltage_base_is_an_error() -> None:
    errors = _errors(_base(voltage_base={"value": 0.0, "unit": "V"}))
    assert any("voltage_base" in e for e in errors)


def test_layer_class_attribute() -> None:
    assert PerUnitConversionValidator.layer == "physical"
