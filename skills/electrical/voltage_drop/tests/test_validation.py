"""Unit tests for electrical.voltage_drop's VoltageDropValidator."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
VoltageDropValidator = _validation_module.VoltageDropValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = VoltageDropValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def _base(**overrides: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "load_type": "current",
        "phase_count": 1,
        "voltage_reference": {"value": 230.0, "unit": "V"},
        "power_factor": 0.9,
        "length": {"value": 50.0, "unit": "m"},
        "current": {"value": 10.0, "unit": "A"},
        "resistance_per_length": {"value": 0.001, "unit": "ohm/m"},
    }
    inputs.update(overrides)
    return inputs


def test_valid_current_input_has_no_errors() -> None:
    assert _errors(_base()) == []


def test_valid_material_path_has_no_errors() -> None:
    inputs = _base()
    del inputs["resistance_per_length"]
    inputs["material"] = "copper"
    inputs["cross_section"] = {"value": 10.0, "unit": "mm^2"}
    assert _errors(inputs) == []


def test_current_without_current_field_is_an_error() -> None:
    inputs = _base()
    del inputs["current"]
    assert any("current" in e for e in _errors(inputs))


def test_current_with_power_is_an_error() -> None:
    errors = _errors(_base(power={"value": 1000.0, "unit": "W"}))
    assert any("power" in e for e in errors)


def test_both_resistance_paths_is_an_error() -> None:
    errors = _errors(
        _base(
            material="copper",
            cross_section={"value": 10.0, "unit": "mm^2"},
        )
    )
    assert any("resistance_per_length" in e for e in errors)


def test_missing_resistance_path_is_an_error() -> None:
    inputs = _base()
    del inputs["resistance_per_length"]
    assert any("resistance" in e for e in _errors(inputs))


def test_zero_length_is_an_error() -> None:
    errors = _errors(_base(length={"value": 0.0, "unit": "m"}))
    assert any("length" in e for e in errors)


def test_negative_reactance_is_an_error() -> None:
    errors = _errors(_base(reactance_per_length={"value": -0.001, "unit": "ohm/m"}))
    assert any("reactance_per_length" in e for e in errors)


def test_layer_class_attribute() -> None:
    assert VoltageDropValidator.layer == "physical"
