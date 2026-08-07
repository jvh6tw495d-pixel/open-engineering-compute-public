from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_cvar_runs_or_skips() -> None:
    out = implementation.execute(
        {
            "decision_vars": [{"name": "x", "lower": 0.0, "upper": 5.0}],
            "loss_scenarios": [{"x": 1.0}, {"x": 3.0}],
            "alpha": 0.5,
            "structural_constraints": [
                {"name": "lb", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1.0}
            ],
        }
    )["result"]
    if out["solver_status"] == "other" and "not installed" in str(out["feasibility_issues"]):
        pytest.skip("highspy not installed")
    assert out["method"] == "rockafellar_uryasev"
    if out["converged"]:
        assert out["cvar"] is not None
        assert out["decision"]["x"] >= 1.0 - 1e-8
