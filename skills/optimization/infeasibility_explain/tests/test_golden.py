"""Golden + adversarial cases for optimization.infeasibility_explain 0.2.0."""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

pytest.importorskip("highspy")


def test_single_constraint_drop_one() -> None:
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 1}
                ],
                "constraints": [
                    {"name": "must_ge_2", "coeffs": {"x": 1}, "sense": ">=", "rhs": 2}
                ],
                "objective": {"coeffs": {"x": 1}},
            }
        }
    )["result"]
    assert out["feasible"] is False
    assert out["claims_iis"] is False
    assert out["tier"] == "single_constraint_relaxation"
    assert "must_ge_2" in out["single_constraint_relaxations"]
    assert out["single_constraint_relaxations"] == out["iis_candidate_constraints"]
    assert "IIS" not in out["explanation"] or "NOT" in out["explanation"]


def test_feasible_model() -> None:
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 1}
                ],
                "constraints": [
                    {"name": "use", "coeffs": {"x": 1}, "sense": ">=", "rhs": 0}
                ],
                "objective": {"coeffs": {"x": 1}},
            }
        }
    )["result"]
    assert out["feasible"] is True
    assert out["status"] == "feasible"


def test_contradictory_pair_drop_one() -> None:
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 1}
                ],
                "constraints": [
                    {"name": "c1", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1},
                    {"name": "c2", "coeffs": {"x": 1}, "sense": "<=", "rhs": 0},
                ],
                "objective": {"coeffs": {"x": 1}},
            }
        }
    )["result"]
    assert out["feasible"] is False
    assert out["claims_iis"] is False
    assert out["tier"] == "single_constraint_relaxation"
    assert set(out["single_constraint_relaxations"]) >= {"c1", "c2"}


def test_two_independent_conflicts_no_single_relaxation() -> None:
    """Two separate variables each forced outside their bounds via constraints.

    Dropping only one constraint leaves the other conflict → empty drop-one list.
    """
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                    {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
                ],
                "constraints": [
                    {"name": "cx", "coeffs": {"x": 1}, "sense": ">=", "rhs": 2},
                    {"name": "cy", "coeffs": {"y": 1}, "sense": ">=", "rhs": 2},
                ],
                "objective": {"coeffs": {"x": 1, "y": 1}},
            }
        }
    )["result"]
    assert out["feasible"] is False
    assert out["claims_iis"] is False
    # Dropping only cx still leaves cy infeasible (and vice versa)
    assert out["tier"] == "no_single_relaxation"
    assert out["single_constraint_relaxations"] == []
    assert "single" in out["explanation"].lower() or "jointly" in out["explanation"].lower()
