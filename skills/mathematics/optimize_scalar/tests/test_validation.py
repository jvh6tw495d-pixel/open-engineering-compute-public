"""Unit tests for mathematics.optimize_scalar's own validation.py (OptimizeScalarValidator)."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
OptimizeScalarValidator = _validation_module.OptimizeScalarValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = OptimizeScalarValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def test_valid_bounded_input_has_no_errors() -> None:
    assert _errors({"expression": "(x-3)**2", "bounds": [0, 10], "method": "bounded"}) == []


def test_valid_unbounded_input_has_no_errors() -> None:
    assert _errors({"expression": "(x-3)**2", "method": "brent"}) == []


def test_valid_input_with_no_method_or_bounds_has_no_errors() -> None:
    assert _errors({"expression": "(x-3)**2"}) == []


def test_bounded_without_bounds_is_an_error() -> None:
    errors = _errors({"expression": "(x-3)**2", "method": "bounded"})
    assert any("bounded" in e and "bounds" in e for e in errors)


def test_bounds_with_brent_is_an_error() -> None:
    errors = _errors({"expression": "(x-3)**2", "bounds": [0, 10], "method": "brent"})
    assert any("bounds" in e for e in errors)


def test_bounds_with_golden_is_an_error() -> None:
    errors = _errors({"expression": "(x-3)**2", "bounds": [0, 10], "method": "golden"})
    assert any("bounds" in e for e in errors)


def test_bounds_without_explicit_method_has_no_errors() -> None:
    """bounds alone (method omitted) implicitly selects bounded -- not an error."""
    assert _errors({"expression": "(x-3)**2", "bounds": [0, 10]}) == []


def test_inverted_bounds_is_an_error() -> None:
    errors = _errors({"expression": "(x-3)**2", "bounds": [10, 0], "method": "bounded"})
    assert any("interval" in e for e in errors)


def test_degenerate_bounds_is_an_error() -> None:
    errors = _errors({"expression": "(x-3)**2", "bounds": [5, 5], "method": "bounded"})
    assert any("interval" in e for e in errors)


def test_malformed_expression_is_an_error() -> None:
    errors = _errors({"expression": "x +", "bounds": [0, 10], "method": "bounded"})
    assert len(errors) == 1


def test_disallowed_expression_is_an_error() -> None:
    errors = _errors({"expression": "__import__('os')"})
    assert len(errors) == 1
