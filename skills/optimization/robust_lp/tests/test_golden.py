from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_robust_rhs_tightens_and_solves() -> None:
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
                    {
                        "name": "cover",
                        "coeffs": {"x": 1, "y": 1},
                        "sense": ">=",
                        "rhs": 1,
                    }
                ],
                "objective": {"coeffs": {"x": 1, "y": 1}},
            },
            "rhs_uncertainty": {"cover": 0.2},
        }
    )["result"]
    if out["solver_status"] == "other" and "not installed" in str(
        out["feasibility_issues"]
    ):
        pytest.skip("highspy not installed")
    assert out["rhs_adjusted"]["cover"]["rhs_robust"] == pytest.approx(1.2)
    if out["converged"]:
        assert out["objective_value"] == pytest.approx(1.2)
