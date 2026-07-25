"""Unit tests for mathematical-domain helper functions."""

from __future__ import annotations

import pytest

from oec.validation.base import Severity
from oec.validation.mathematical import (
    LAYER,
    require_bracket,
    require_in_range,
    require_nonzero,
    require_square_matrix,
)


def test_require_nonzero_ok() -> None:
    outcome = require_nonzero("denominator", 1.5)
    assert outcome.severity == Severity.OK
    assert outcome.layer == LAYER


def test_require_nonzero_error() -> None:
    outcome = require_nonzero("denominator", 0.0)
    assert outcome.severity == Severity.ERROR
    assert "non-zero" in outcome.messages[0]
    assert outcome.details["field"] == "denominator"


def test_require_in_range_ok_with_both_bounds() -> None:
    outcome = require_in_range("x", 0.5, minimum=0.0, maximum=1.0)
    assert outcome.severity == Severity.OK


def test_require_in_range_ok_at_boundaries() -> None:
    assert require_in_range("x", 0.0, minimum=0.0, maximum=1.0).severity == Severity.OK
    assert require_in_range("x", 1.0, minimum=0.0, maximum=1.0).severity == Severity.OK


def test_require_in_range_below_minimum() -> None:
    outcome = require_in_range("x", -0.1, minimum=0.0, maximum=1.0)
    assert outcome.severity == Severity.ERROR
    assert ">=" in outcome.messages[0]


def test_require_in_range_above_maximum() -> None:
    outcome = require_in_range("x", 1.1, minimum=0.0, maximum=1.0)
    assert outcome.severity == Severity.ERROR
    assert "<=" in outcome.messages[0]


def test_require_in_range_open_ended() -> None:
    assert require_in_range("x", 1e9, minimum=0.0).severity == Severity.OK
    assert require_in_range("x", -1e9, maximum=0.0).severity == Severity.OK
    assert require_in_range("x", 0.0).severity == Severity.OK


def test_require_bracket_opposite_signs_ok() -> None:
    assert require_bracket("fa", -1.0, "fb", 2.0).severity == Severity.OK
    assert require_bracket("fa", 3.0, "fb", -0.5).severity == Severity.OK


@pytest.mark.parametrize(
    ("f_a", "f_b"),
    [
        (1.0, 2.0),
        (-1.0, -2.0),
        (0.0, 1.0),
        (1.0, 0.0),
        (0.0, 0.0),
        (-0.0, 5.0),
    ],
)
def test_require_bracket_invalid(f_a: float, f_b: float) -> None:
    """Product >= 0 (including exact zero) is not a valid root-finding bracket."""
    outcome = require_bracket("fa", f_a, "fb", f_b)
    assert outcome.severity == Severity.ERROR
    assert "bracket" in outcome.messages[0]


def test_require_square_matrix_ok() -> None:
    assert require_square_matrix("A", [[1.0, 2.0], [3.0, 4.0]]).severity == Severity.OK
    assert require_square_matrix("A", [[1.0]]).severity == Severity.OK
    assert require_square_matrix("A", []).severity == Severity.OK


def test_require_square_matrix_wrong_row_length() -> None:
    outcome = require_square_matrix("A", [[1.0, 2.0], [3.0]])
    assert outcome.severity == Severity.ERROR
    assert "square" in outcome.messages[0]
    assert outcome.details["row_index"] == 1


def test_require_square_matrix_rectangular() -> None:
    outcome = require_square_matrix("A", [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    assert outcome.severity == Severity.ERROR


def test_require_square_matrix_non_list_row() -> None:
    outcome = require_square_matrix("A", [[1.0, 2.0], "not-a-row"])  # type: ignore[list-item]
    assert outcome.severity == Severity.ERROR
    assert "not a list" in outcome.messages[0]
