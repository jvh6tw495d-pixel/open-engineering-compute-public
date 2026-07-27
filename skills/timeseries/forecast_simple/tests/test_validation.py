"""Unit tests for timeseries.forecast_simple's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.ForecastSimpleValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_seasonal_naive_without_period_is_an_error() -> None:
    assert _errors(
        {"series": [1.0, 2.0, 3.0, 4.0], "steps_ahead": 2, "method": "seasonal_naive"}
    )


def test_seasonal_naive_short_series_is_an_error() -> None:
    assert _errors(
        {"series": [1.0], "steps_ahead": 2, "method": "seasonal_naive", "period": 2}
    )


def test_invalid_steps_ahead_is_an_error() -> None:
    assert _errors({"series": [1.0], "steps_ahead": 0, "method": "naive"})


def test_valid_naive_is_ok() -> None:
    assert not _errors({"series": [1.0, 2.0], "steps_ahead": 2, "method": "naive"})