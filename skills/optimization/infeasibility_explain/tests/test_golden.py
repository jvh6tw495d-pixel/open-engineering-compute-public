"""Golden cases for optimization.infeasibility_explain (v2.3 Wave A).

Requires the optional ``highspy`` extra.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")

highspy = pytest.importorskip("highspy")


def test_single_tight_constraint_is_an_iis_candidate() -> None:
    """Variable x in [0,1] with a single constraint x >= 2 is infeasible
    at the HiGHS solve tier (no bound conflict at the variable level).
    Dropping that constraint restores feasibility, so the IIS candidate
    must contain it. Tree of infeasible why: explain = which constraint,
    and the dropped subset gives back a feasible solve."""
    golden = GoldenCase(
        id="bound_conflict.json",
        skill_id="optimization.infeasibility_explain",
        skill_version="0.1.0",
        inputs={
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
        },
        expected_result={
            "feasible": False,
            "tier": "iis_candidate",
            "n_constraints": 1,
            "backend": "highs",
        },
        tolerance=1e-12,
        source="closed form + drop-one IIS scan",
        justification=(
            "The single constraint x>=2 cannot coexist with the variable bound "
            "[0,1]; removing it makes the trivial solve feasible again."
        ),
    )
    out = implementation.execute(golden.inputs)
    actual = {
        "feasible": out["result"]["feasible"],
        "tier": out["result"]["tier"],
        "n_constraints": out["result"]["n_constraints"],
        "backend": out["result"]["backend"],
    }
    assert_matches_golden(actual, golden)
    assert "must_ge_2" in out["result"]["iis_candidate_constraints"]


def test_feasible_model_is_reported_as_feasible() -> None:
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
    )
    assert out["result"]["feasible"] is True
    assert out["result"]["tier"] == "feasible"


def test_infeasible_constraint_pair_yields_iis_candidate() -> None:
    """x>=0, x<=1, AND two contradictory constraints:
    c1: x >= 1, c2: x <= 0. The model is infeasible; dropping either
    one of c1, c2 restores feasibility, so the IIS candidate should
    contain at least one of [c1, c2]."""
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
    )
    assert out["result"]["feasible"] is False
    assert out["result"]["tier"] == "iis_candidate"
    candidate = out["result"]["iis_candidate_constraints"]
    assert "c1" in candidate or "c2" in candidate
    assert len(candidate) >= 1