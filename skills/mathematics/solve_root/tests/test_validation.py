"""Unit tests for mathematics.solve_root's own validation.py (SolveRootValidator)."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
SolveRootValidator = _validation_module.SolveRootValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = SolveRootValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def test_valid_bracketed_input_has_no_errors() -> None:
    assert _errors({"expression": "x**2 - 2", "bracket": [0, 2]}) == []


def test_valid_guess_input_has_no_errors() -> None:
    assert _errors({"expression": "x**2 - 2", "initial_guess": 1.0}) == []


def test_missing_bracket_and_guess_is_an_error() -> None:
    errors = _errors({"expression": "x**2 - 2"})
    assert any("bracket" in e and "initial_guess" in e for e in errors)


def test_newton_without_derivative_is_an_error() -> None:
    errors = _errors({"expression": "x**2 - 2", "initial_guess": 1.0, "method": "newton"})
    assert any("newton" in e for e in errors)


def test_derivative_with_non_newton_method_is_an_error() -> None:
    errors = _errors(
        {
            "expression": "x**2 - 2",
            "initial_guess": 1.0,
            "method": "secant",
            "derivative": "2*x",
        }
    )
    assert any("derivative" in e for e in errors)


def test_newton_with_derivative_has_no_errors() -> None:
    errors = _errors(
        {
            "expression": "x**2 - 2",
            "initial_guess": 1.0,
            "method": "newton",
            "derivative": "2*x",
        }
    )
    assert errors == []


def test_malformed_expression_is_an_error() -> None:
    errors = _errors({"expression": "x +", "bracket": [0, 2]})
    assert len(errors) == 1


def test_disallowed_expression_is_an_error() -> None:
    errors = _errors({"expression": "__import__('os')", "bracket": [0, 2]})
    assert len(errors) == 1


def test_malformed_derivative_is_an_error() -> None:
    errors = _errors(
        {
            "expression": "x**2 - 2",
            "initial_guess": 1.0,
            "method": "newton",
            "derivative": "2*x +",
        }
    )
    assert any("syntax" in e or "invalid" in e for e in errors)


def test_bracket_without_sign_change_is_an_error() -> None:
    errors = _errors({"expression": "x**2 - 2", "bracket": [0, 1]})
    assert len(errors) == 1


def test_bracket_with_sign_change_has_no_bracket_error() -> None:
    assert _errors({"expression": "x**2 - 2", "bracket": [0, 2]}) == []
