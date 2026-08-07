"""Unit tests for optimization.lp_diagnostics's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.LpDiagnosticsValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_non_mapping_ops_is_an_error() -> None:
    assert _errors({"ops": "not-a-mapping"})


def test_milp_ops_is_an_error() -> None:
    ops = {
        "ops_version": "0.1.0",
        "problem_class": "milp",
        "sense": "min",
        "variables": [{"name": "x", "kind": "integer", "lower": 0}],
        "constraints": [],
        "objective": {"coeffs": {"x": 1}},
    }
    assert _errors({"ops": ops})


def test_valid_lp_is_ok() -> None:
    ops = {
        "ops_version": "0.1.0",
        "problem_class": "lp",
        "sense": "min",
        "variables": [
            {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
            {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
        ],
        "constraints": [
            {"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}
        ],
        "objective": {"coeffs": {"x": 1, "y": 1}},
    }
    assert not _errors({"ops": ops})