"""Golden LP cases (Phase C)."""

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

highspy = pytest.importorskip("highspy")

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_diet_lp_optimal() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "diet_lp.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert out["result"]["solver_status"] == "optimal"
    assert abs(out["result"]["objective_value"] - 1.0) < 1e-8
    assert out["diagnostics"]["converged"] is True


def test_infeasible_lp_reports_issues() -> None:
    out = implementation.execute(
        {
            "ops": {
                "ops_version": "0.1.0",
                "problem_class": "lp",
                "sense": "min",
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                ],
                "constraints": [
                    {"name": "a", "coeffs": {"x": 1}, "sense": ">=", "rhs": 2},
                ],
                "objective": {"coeffs": {"x": 1}},
            }
        }
    )
    assert out["result"]["solver_status"] == "infeasible"
    assert out["diagnostics"]["converged"] is False
    assert out["result"]["feasibility_issues"]
