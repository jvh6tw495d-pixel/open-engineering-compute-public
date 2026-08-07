"""Unit tests for mathematics.curve_fit's own validation.py (CurveFitValidator)."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
CurveFitValidator = _validation_module.CurveFitValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = CurveFitValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def _base_inputs() -> dict[str, Any]:
    return {
        "model": "a*x + b",
        "parameter_names": ["a", "b"],
        "x": [0.0, 1.0, 2.0],
        "y": [1.0, 3.0, 5.0],
        "initial_guess": [1.0, 1.0],
    }


def test_valid_input_has_no_errors() -> None:
    assert _errors(_base_inputs()) == []


def test_valid_bounded_input_has_no_errors() -> None:
    inputs = {**_base_inputs(), "bounds": [[0, 10], [None, 10]]}
    assert _errors(inputs) == []


def test_duplicate_parameter_names_is_an_error() -> None:
    inputs = {**_base_inputs(), "parameter_names": ["a", "a"], "initial_guess": [1.0, 1.0]}
    errors = _errors(inputs)
    assert any("duplicate" in e for e in errors)


def test_parameter_named_x_is_an_error() -> None:
    inputs = {**_base_inputs(), "parameter_names": ["a", "x"], "initial_guess": [1.0, 1.0]}
    errors = _errors(inputs)
    assert any("'x'" in e for e in errors)


def test_x_y_length_mismatch_is_an_error() -> None:
    inputs = {**_base_inputs(), "y": [1.0, 3.0]}
    errors = _errors(inputs)
    assert any("'x'" in e and "'y'" in e for e in errors)


def test_insufficient_data_points_is_an_error() -> None:
    inputs = {**_base_inputs(), "x": [0.0], "y": [1.0]}
    errors = _errors(inputs)
    assert any("not enough" in e for e in errors)


def test_initial_guess_length_mismatch_is_an_error() -> None:
    inputs = {**_base_inputs(), "initial_guess": [1.0]}
    errors = _errors(inputs)
    assert any("initial_guess" in e and "parameter_names" in e for e in errors)


def test_bounds_length_mismatch_is_an_error() -> None:
    inputs = {**_base_inputs(), "bounds": [[0, 10]]}
    errors = _errors(inputs)
    assert any("bounds" in e and "parameter_names" in e for e in errors)


def test_inverted_bound_pair_is_an_error() -> None:
    inputs = {**_base_inputs(), "bounds": [[10, 0], [0, 10]]}
    errors = _errors(inputs)
    assert any("interval" in e for e in errors)


def test_malformed_model_is_an_error() -> None:
    inputs = {**_base_inputs(), "model": "a*x +"}
    errors = _errors(inputs)
    assert len(errors) == 1


def test_unknown_name_in_model_is_an_error() -> None:
    inputs = {**_base_inputs(), "model": "a*x + c"}
    errors = _errors(inputs)
    assert any("unknown name" in e for e in errors)


def test_disallowed_model_is_an_error() -> None:
    inputs = {**_base_inputs(), "model": "__import__('os')"}
    errors = _errors(inputs)
    assert len(errors) == 1
