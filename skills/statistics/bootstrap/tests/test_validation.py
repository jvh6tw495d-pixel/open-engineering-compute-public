"""Unit tests for statistics.bootstrap's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.BootstrapValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_empty_is_an_error() -> None:
    assert _errors({"samples": []})


def test_non_number_is_an_error() -> None:
    assert _errors({"samples": [1.0, "x", 3.0]})


def test_unsupported_statistic_is_an_error() -> None:
    assert _errors({"samples": [1.0, 2.0], "statistic": "mode"})


def test_valid_is_ok() -> None:
    assert not _errors({"samples": [1.0, 2.0]})
    assert not _errors({"samples": [1.0, 2.0], "statistic": "median"})