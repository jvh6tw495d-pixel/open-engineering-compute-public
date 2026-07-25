"""Unit tests for TransformerLoadingValidator."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
TransformerLoadingValidator = _validation_module.TransformerLoadingValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = TransformerLoadingValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def _base(**overrides: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "rated_apparent_power": {"value": 1_000_000.0, "unit": "W"},
        "load_type": "apparent_power",
        "load_apparent_power": {"value": 800_000.0, "unit": "W"},
    }
    inputs.update(overrides)
    return inputs


def test_valid_apparent_power_has_no_errors() -> None:
    assert _errors(_base()) == []


def test_valid_current_path_has_no_errors() -> None:
    inputs = {
        "rated_apparent_power": {"value": 500_000.0, "unit": "W"},
        "load_type": "current",
        "load_current": {"value": 100.0, "unit": "A"},
        "rated_current": {"value": 120.0, "unit": "A"},
    }
    assert _errors(inputs) == []


def test_apparent_without_load_s_is_an_error() -> None:
    inputs = _base()
    del inputs["load_apparent_power"]
    assert any("load_apparent_power" in e for e in _errors(inputs))


def test_current_missing_rated_current_is_an_error() -> None:
    errors = _errors(
        {
            "rated_apparent_power": {"value": 500_000.0, "unit": "W"},
            "load_type": "current",
            "load_current": {"value": 100.0, "unit": "A"},
        }
    )
    assert any("rated_current" in e for e in errors)


def test_zero_rated_is_an_error() -> None:
    errors = _errors(_base(rated_apparent_power={"value": 0.0, "unit": "W"}))
    assert any("rated_apparent_power" in e for e in errors)


def test_layer_class_attribute() -> None:
    assert TransformerLoadingValidator.layer == "physical"
