"""Unit tests for mathematics.optimize_constrained's own validation.py
(OptimizeConstrainedValidator)."""

from pathlib import Path
from typing import Any

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module
from oec.validation.base import Severity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_validation_module = load_skill_module(_SKILL_DIR, "validation")
OptimizeConstrainedValidator = _validation_module.OptimizeConstrainedValidator


def _skill() -> Any:
    return load_skill(_SKILL_DIR)


def _errors(inputs: dict[str, Any]) -> list[str]:
    outcomes = OptimizeConstrainedValidator().validate(_skill(), inputs)
    return [msg for o in outcomes if o.severity is Severity.ERROR for msg in o.messages]


def test_valid_unconstrained_input_has_no_errors() -> None:
    assert _errors({"variables": ["x", "y"], "expression": "x**2 + y**2", "x0": [1.0, 1.0]}) == []


def test_valid_bounded_input_has_no_errors() -> None:
    inputs = {
        "variables": ["x", "y"],
        "expression": "x**2 + y**2",
        "x0": [0.0, 0.0],
        "bounds": [[-10, 10], [-10, 10]],
    }
    assert _errors(inputs) == []


def test_valid_constrained_input_has_no_errors() -> None:
    inputs = {
        "variables": ["x", "y"],
        "expression": "x**2 + y**2",
        "x0": [0.0, 0.0],
        "constraints": [{"type": "ineq", "expression": "x + y - 1"}],
    }
    assert _errors(inputs) == []


def test_duplicate_variable_names_is_an_error() -> None:
    errors = _errors({"variables": ["x", "x"], "expression": "x**2", "x0": [0.0, 0.0]})
    assert any("duplicate" in e for e in errors)


def test_x0_length_mismatch_is_an_error() -> None:
    errors = _errors({"variables": ["x", "y"], "expression": "x**2 + y**2", "x0": [0.0]})
    assert any("x0" in e and "variables" in e for e in errors)


def test_bounds_length_mismatch_is_an_error() -> None:
    inputs = {
        "variables": ["x", "y"],
        "expression": "x**2 + y**2",
        "x0": [0.0, 0.0],
        "bounds": [[-10, 10]],
    }
    errors = _errors(inputs)
    assert any("bounds" in e and "variables" in e for e in errors)


def test_inverted_bound_pair_is_an_error() -> None:
    inputs = {
        "variables": ["x", "y"],
        "expression": "x**2 + y**2",
        "x0": [0.0, 0.0],
        "bounds": [[10, -10], [-10, 10]],
    }
    errors = _errors(inputs)
    assert any("interval" in e for e in errors)


def test_bound_with_one_null_side_has_no_errors() -> None:
    inputs = {
        "variables": ["x", "y"],
        "expression": "x**2 + y**2",
        "x0": [0.0, 0.0],
        "bounds": [[None, 10], [-10, None]],
    }
    assert _errors(inputs) == []


def test_malformed_expression_is_an_error() -> None:
    errors = _errors({"variables": ["x"], "expression": "x +", "x0": [0.0]})
    assert len(errors) == 1


def test_unknown_variable_in_expression_is_an_error() -> None:
    errors = _errors({"variables": ["x", "y"], "expression": "x**2 + z**2", "x0": [0.0, 0.0]})
    assert any("unknown name" in e for e in errors)


def test_disallowed_expression_is_an_error() -> None:
    errors = _errors({"variables": ["x"], "expression": "__import__('os')", "x0": [0.0]})
    assert len(errors) == 1


def test_malformed_constraint_expression_is_an_error() -> None:
    inputs = {
        "variables": ["x", "y"],
        "expression": "x**2 + y**2",
        "x0": [0.0, 0.0],
        "constraints": [{"type": "ineq", "expression": "x + y +"}],
    }
    errors = _errors(inputs)
    assert any("constraints[0]" in e for e in errors)
