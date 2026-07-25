"""Unit tests for mathematics.integrate's own validation.py."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
IntegrateValidator = _validation_module.IntegrateValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = IntegrateValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def test_valid_function_mode_has_no_errors() -> None:
    assert _errors({"expression": "sin(x)", "bounds": [0.0, 1.0]}) == []


def test_valid_tabulated_mode_has_no_errors() -> None:
    assert _errors({"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0, 0.0]}) == []


def test_missing_both_modes_is_an_error() -> None:
    errors = _errors({})
    assert any("exactly one" in e for e in errors)


def test_both_modes_is_an_error() -> None:
    errors = _errors(
        {
            "expression": "x",
            "bounds": [0.0, 1.0],
            "x": [0.0, 1.0],
            "y": [0.0, 1.0],
        }
    )
    assert any("not both" in e or "exactly one" in e for e in errors)


def test_malformed_expression_is_an_error() -> None:
    errors = _errors({"expression": "x +", "bounds": [0.0, 1.0]})
    assert len(errors) >= 1


def test_disallowed_expression_is_an_error() -> None:
    errors = _errors({"expression": "__import__('os')", "bounds": [0.0, 1.0]})
    assert len(errors) >= 1


def test_equal_bounds_is_an_error() -> None:
    errors = _errors({"expression": "x", "bounds": [1.0, 1.0]})
    assert any("distinct" in e or "equal" in e for e in errors)


def test_method_in_function_mode_is_an_error() -> None:
    errors = _errors({"expression": "x", "bounds": [0.0, 1.0], "method": "simpson"})
    assert any("method" in e and "tabulated" in e for e in errors)


def test_mismatched_x_y_lengths_is_an_error() -> None:
    errors = _errors({"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0]})
    assert any("same length" in e for e in errors)


def test_non_increasing_x_is_an_error() -> None:
    errors = _errors({"x": [0.0, 2.0, 1.0], "y": [0.0, 1.0, 0.0]})
    assert any("strictly increasing" in e for e in errors)


def test_simpson_with_two_points_is_an_error() -> None:
    errors = _errors({"x": [0.0, 1.0], "y": [0.0, 1.0], "method": "simpson"})
    assert any("simpson" in e for e in errors)


def test_trapezoid_with_two_points_has_no_errors() -> None:
    assert _errors({"x": [0.0, 1.0], "y": [0.0, 1.0], "method": "trapezoid"}) == []


def test_function_mode_missing_bounds_is_an_error() -> None:
    errors = _errors({"expression": "x"})
    assert any("bounds" in e for e in errors)


def test_tabulated_mode_missing_y_is_an_error() -> None:
    errors = _errors({"x": [0.0, 1.0]})
    assert any("x" in e and "y" in e for e in errors)
