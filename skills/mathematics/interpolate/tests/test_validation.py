"""Unit tests for mathematics.interpolate's own validation.py."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
InterpolateValidator = _validation_module.InterpolateValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _outcomes(inputs: dict[str, Any]) -> list[Any]:
    return InterpolateValidator().validate(_skill(), inputs)


def _errors(inputs: dict[str, Any]) -> list[str]:
    return [msg for o in _outcomes(inputs) if o.severity is Severity.ERROR for msg in o.messages]


def _warnings(inputs: dict[str, Any]) -> list[str]:
    return [msg for o in _outcomes(inputs) if o.severity is Severity.WARNING for msg in o.messages]


def _valid_base(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "x": [0.0, 1.0, 2.0, 3.0],
        "y": [0.0, 1.0, 0.0, 1.0],
        "query_points": [0.5, 1.5],
        "method": "linear",
    }
    base.update(overrides)
    return base


def test_valid_linear_input_has_no_errors() -> None:
    assert _errors(_valid_base()) == []


def test_valid_cubic_spline_input_has_no_errors() -> None:
    assert _errors(_valid_base(method="cubic_spline")) == []


def test_valid_pchip_input_has_no_errors() -> None:
    assert _errors(_valid_base(method="pchip")) == []


def test_mismatched_x_y_lengths_is_an_error() -> None:
    errors = _errors(_valid_base(y=[0.0, 1.0]))
    assert any("same length" in e for e in errors)


def test_non_increasing_x_is_an_error() -> None:
    errors = _errors(_valid_base(x=[0.0, 2.0, 1.0, 3.0]))
    assert any("strictly increasing" in e for e in errors)


def test_duplicate_x_is_an_error() -> None:
    errors = _errors(_valid_base(x=[0.0, 1.0, 1.0, 2.0]))
    assert any("strictly increasing" in e for e in errors)


def test_cubic_spline_with_fewer_than_four_points_is_an_error() -> None:
    errors = _errors(_valid_base(x=[0.0, 1.0, 2.0], y=[0.0, 1.0, 0.0], method="cubic_spline"))
    assert any("cubic_spline" in e and "4" in e for e in errors)


def test_linear_with_three_points_is_ok() -> None:
    assert _errors(_valid_base(x=[0.0, 1.0, 2.0], y=[0.0, 1.0, 0.0], method="linear")) == []


def test_query_outside_range_is_a_warning_not_an_error() -> None:
    outcomes_inputs = _valid_base(query_points=[-1.0, 0.5, 10.0])
    assert _errors(outcomes_inputs) == []
    warnings = _warnings(outcomes_inputs)
    assert any("outside" in w or "extrapolation" in w for w in warnings)


def test_query_inside_range_has_no_extrapolation_warning() -> None:
    assert _warnings(_valid_base(query_points=[0.0, 1.5, 3.0])) == []
