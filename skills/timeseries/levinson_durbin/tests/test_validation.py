"""Unit tests for timeseries.levinson_durbin's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.LevinsonDurbinValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_valid_inputs_are_ok() -> None:
    assert not _errors({"autocorrelation": [1.0, 0.5, 0.25]})


def test_too_short_is_an_error() -> None:
    assert _errors({"autocorrelation": [1.0]})


def test_nonpositive_r0_is_an_error() -> None:
    assert _errors({"autocorrelation": [0.0, 0.5]})
    assert _errors({"autocorrelation": [-1.0, 0.5]})


def test_non_finite_value_is_an_error() -> None:
    assert _errors({"autocorrelation": [1.0, float("nan")]})
    assert _errors({"autocorrelation": [1.0, float("inf")]})
