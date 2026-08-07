"""Unit tests for timeseries.ar_yule_walker's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.ArYuleWalkerValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_valid_inputs_are_ok() -> None:
    assert not _errors({"series": [1.0, -1.0, 1.0, -1.0], "order": 1})


def test_order_too_large_is_an_error() -> None:
    assert _errors({"series": [1.0, 2.0, 3.0], "order": 3})


def test_nonpositive_order_is_an_error() -> None:
    assert _errors({"series": [1.0, 2.0, 3.0], "order": 0})


def test_short_series_is_an_error() -> None:
    assert _errors({"series": [1.0], "order": 1})


def test_constant_series_is_an_error() -> None:
    assert _errors({"series": [5.0, 5.0, 5.0], "order": 1})
