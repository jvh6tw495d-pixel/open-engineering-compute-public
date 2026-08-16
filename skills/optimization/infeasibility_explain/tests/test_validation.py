"""Unit tests for optimization.infeasibility_explain's own validation.py."""

from __future__ import annotations

from pathlib import Path

from oec.skills.loader.loader import load_skill
from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
validation = load_skill_module(_SKILL_DIR, "validation")
_skill = load_skill(_SKILL_DIR)
_validator = validation.InfeasibilityExplainValidator()


def _errors(inputs: dict) -> list[str]:
    outcomes = _validator.validate(_skill, inputs)
    return [m for o in outcomes for m in o.messages if str(o.severity) == "error"]


def test_non_mapping_ops_is_an_error() -> None:
    assert _errors({"ops": "not-a-mapping"})


def test_milp_is_an_error() -> None:
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
        "variables": [{"name": "x", "kind": "continuous", "lower": 0}],
        "constraints": [{"name": "use", "coeffs": {"x": 1}, "sense": ">=", "rhs": 0}],
        "objective": {"coeffs": {"x": 1}},
    }
    assert not _errors({"ops": ops})
