from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

_OPS = {
    "ops_version": "0.1.0",
    "problem_class": "lp",
    "sense": "min",
    "variables": [
        {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
        {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
    ],
    "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
    "objective": {"coeffs": {"x": 1, "y": 1}},
}


def test_pareto_sweep_finds_optimal_points() -> None:
    out = implementation.execute(
        {
            "ops": _OPS,
            "objective_a": {"x": 1, "y": 2},
            "objective_b": {"x": 2, "y": 1},
            "n_points": 5,
        }
    )["result"]
    if out["points"] and "not installed" in str(out["points"][0].get("feasibility_issues", [])):
        pytest.skip("highspy not installed")
    assert out["n_points_requested"] == 5
    assert out["n_solved_optimal"] >= 1
    assert out["n_nondominated"] >= 1
