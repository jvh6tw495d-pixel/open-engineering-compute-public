"""Golden cases for optimization.lp_diagnostics (v2.3 Wave A).

Requires the optional ``highspy`` extra.
"""

from __future__ import annotations

import json
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