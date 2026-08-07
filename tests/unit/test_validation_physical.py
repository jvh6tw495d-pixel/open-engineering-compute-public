"""Unit tests for physical-limit helper functions."""

from __future__ import annotations

import pytest

from oec.validation.base import Severity
from oec.validation.physical import (
    LAYER,
    require_above_absolute_zero,
    require_positive,
    require_probability,
)


def test_require_positive_ok() -> None:
    outcome = require_positive("mass", 1.0)
    assert outcome.severity == Severity.OK
    assert outcome.layer == LAYER


@pytest.mark.parametrize("value", [0.0, -1.0, -1e-12])
def test_require_positive_error(value: float) -> None:
    outcome = require_positive("mass", value)
    assert outcome.severity == Severity.ERROR
    assert "positive" in outcome.messages[0]


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_require_probability_ok(value: float) -> None:
    assert require_probability("pf", value).severity == Severity.OK


@pytest.mark.parametrize("value", [-0.01, 1.01, 2.0, -1.0])
def test_require_probability_error(value: float) -> None:
    outcome = require_probability("pf", value)
    assert outcome.severity == Severity.ERROR
    assert "probability" in outcome.messages[0]


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        (1.0, "kelvin"),
        (0.01, "K"),
        (0.0, "degC"),  # 273.15 K
        (20.0, "degC"),
        (32.0, "degF"),
    ],
)
def test_require_above_absolute_zero_ok(value: float, unit: str) -> None:
    assert require_above_absolute_zero("T", value, unit).severity == Severity.OK


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        (0.0, "K"),
        (-1.0, "kelvin"),
        (-273.15, "degC"),
        (-273.16, "degC"),
        (-459.67, "degF"),
    ],
)
def test_require_above_absolute_zero_error(value: float, unit: str) -> None:
    outcome = require_above_absolute_zero("T", value, unit)
    assert outcome.severity == Severity.ERROR
    assert "absolute zero" in outcome.messages[0]


def test_require_above_absolute_zero_incompatible_unit() -> None:
    outcome = require_above_absolute_zero("T", 1.0, "meter")
    assert outcome.severity == Severity.ERROR
    assert "cannot interpret" in outcome.messages[0] or "temperature" in outcome.messages[0]


def test_require_above_absolute_zero_unknown_unit() -> None:
    outcome = require_above_absolute_zero("T", 1.0, "notaunit")
    assert outcome.severity == Severity.ERROR
