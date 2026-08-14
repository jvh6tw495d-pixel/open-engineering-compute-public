"""Unit tests for linear.eig's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.EigValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_non_square_is_an_error() -> None:
    assert _errors({"A": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]})


def test_square_is_ok() -> None:
    assert not _errors({"A": [[1.0, 0.0], [0.0, 2.0]]})


def test_empty_is_an_error() -> None:
    assert _errors({"A": []})
    assert _errors({"A": [[]]})
