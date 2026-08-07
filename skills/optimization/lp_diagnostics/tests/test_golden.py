"""Golden cases for optimization.lp_diagnostics (v2.3 Wave A).

Requires the optional ``highspy`` extra.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

highspy = pytest.importorskip("highspy")


def test_lp_diagnostic_diet_example() -> None:
    path = _SKILL_DIR / "examples" / "diet_lp.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert out["result"]["solver_status"] == "optimal"
    assert out["result"]["objective_value"] == 1.0
    # KKT report: each variable's reduced cost and each constraint's slack
    # present in the result dict.
    assert "cover" in out["result"]["slacks"]
    assert "x" in out["result"]["reduced_costs"]
    assert "y" in out["result"]["reduced_costs"]
    # The cover constraint is tight at the optimum (x+y == 1),
    # so slack = LHS - rhs = 0 within numerical tolerance.
    assert abs(out["result"]["slacks"]["cover"]) < 1e-6
    assert out["diagnostics"]["converged"] is True


def test_at_least_one_basic_variable_has_zero_reduced_cost() -> None:
    """At any LP optimum, at least one basic variable has zero reduced
    cost (KKT optimality, complementary slackness). Derivable independently
    of HiGHS' implementation."""
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
                    {"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}
                ],
                "objective": {"coeffs": {"x": 1, "y": 1}},
            }
        }
    )
    reduced_costs = out["result"]["reduced_costs"]
    assert any(abs(v) < 1e-6 for v in reduced_costs.values())


def test_slack_sign_convention_for_slack_and_tight_constraints() -> None:
    """minimize x s.t. x >= 1 (tight at the optimum) and x <= 10 (slack).
    Per skill.md's slack convention: '>=' slack = LHS - rhs (tight -> 0),
    '<=' slack = rhs - LHS (here 10 - 1 = 9)."""
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [{"name": "x", "kind": "continuous", "lower": 0, "upper": 10}],
                "constraints": [
                    {"name": "lower", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1},
                    {"name": "upper", "coeffs": {"x": 1}, "sense": "<=", "rhs": 10},
                ],
                "objective": {"coeffs": {"x": 1}},
            }
        }
    )
    result = out["result"]
    assert result["solver_status"] == "optimal"
    assert math.isclose(result["objective_value"], 1.0, abs_tol=1e-6)
    assert abs(result["slacks"]["lower"]) < 1e-6
    assert math.isclose(result["slacks"]["upper"], 9.0, abs_tol=1e-6)


def test_equality_constraint_slack_is_zero_residual() -> None:
    """minimize x s.t. x + y = 4, x,y in [0,10]: optimum is x=0,y=4.
    Equality slack is the signed residual LHS - rhs, ~0 by construction."""
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 10},
                    {"name": "y", "kind": "continuous", "lower": 0, "upper": 10},
                ],
                "constraints": [
                    {"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": "=", "rhs": 4}
                ],
                "objective": {"coeffs": {"x": 1}},
            }
        }
    )
    result = out["result"]
    assert result["solver_status"] == "optimal"
    assert math.isclose(result["objective_value"], 0.0, abs_tol=1e-6)
    assert abs(result["slacks"]["cover"]) < 1e-6


def test_degenerate_lp_objective_is_invariant_to_chosen_vertex() -> None:
    """minimize x+y s.t. x+y >= 2, x,y in [0,2]: every point on x+y=2
    within the box is optimal, so objective_value=2.0 is closed-form
    regardless of which vertex HiGHS returns -- assert the invariant, not
    a specific primal point."""
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 2},
                    {"name": "y", "kind": "continuous", "lower": 0, "upper": 2},
                ],
                "constraints": [
                    {"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 2}
                ],
                "objective": {"coeffs": {"x": 1, "y": 1}},
            }
        }
    )
    result = out["result"]
    assert result["solver_status"] == "optimal"
    assert math.isclose(result["objective_value"], 2.0, abs_tol=1e-6)
