"""Unit tests for timeseries.lag_features's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.LagFeaturesValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_empty_values_is_an_error() -> None:
    assert _errors({"values": [], "lags": [1]})


def test_empty_lags_is_an_error() -> None:
    assert _errors({"values": [1.0, 2.0], "lags": []})


def test_too_short_for_max_lag_is_an_error() -> None:
    assert _errors({"values": [1.0, 2.0], "lags": [1, 5]})


def test_valid_is_ok() -> None:
    assert not _errors({"values": [1.0, 2.0, 3.0], "lags": [1]})
