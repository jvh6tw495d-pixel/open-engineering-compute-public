"""Unit tests for linear.least_squares's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.LeastSquaresValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_dimension_mismatch_is_an_error() -> None:
    assert _errors({"A": [[1.0, 2.0], [3.0, 4.0]], "b": [1.0, 2.0, 3.0]})


def test_jagged_rows_is_an_error() -> None:
    assert _errors({"A": [[1.0, 2.0], [3.0]], "b": [1.0, 2.0]})


def test_valid_match_is_ok() -> None:
    assert not _errors({"A": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]], "b": [1.0, 3.0, 5.0]})


def test_empty_b_is_an_error() -> None:
    assert _errors({"A": [[1.0]], "b": []})
