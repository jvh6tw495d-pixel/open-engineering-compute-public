"""HiGHS adapter unit tests (requires oec[optimization])."""

import pytest

from oec.kernel.optimization.highs import (
    LinearConstraint,
    LinearVariable,
    SolverStatus,
    check_bound_conflicts,
    solve_linear,
)

pytest.importorskip("highspy")


def test_simple_lp_optimal() -> None:
    result = solve_linear(
        variables=[
            LinearVariable("x", lower=0, upper=1, objective_coeff=1),
            LinearVariable("y", lower=0, upper=1, objective_coeff=1),
        ],
        constraints=[
            LinearConstraint("c", {"x": 1, "y": 1}, ">=", 1),
        ],
        sense="min",
    )
    assert result.status is SolverStatus.OPTIMAL
    assert result.objective_value is not None
    assert abs(result.objective_value - 1.0) < 1e-8


def test_bound_conflict_helper() -> None:
    issues = check_bound_conflicts([LinearVariable("x", lower=2, upper=1, objective_coeff=0)])
    assert issues
