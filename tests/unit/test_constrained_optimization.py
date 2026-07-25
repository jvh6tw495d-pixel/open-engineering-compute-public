import math

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.optimization.constrained import (
    Constraint,
    minimize_constrained,
    select_default_method,
)


def _paraboloid(v: list[float]) -> float:
    x, y = v
    return x**2 + y**2


def test_unconstrained_finds_origin() -> None:
    result = minimize_constrained(_paraboloid, [1.0, 1.0])
    assert math.isclose(result.x[0], 0.0, abs_tol=1e-6)
    assert math.isclose(result.x[1], 0.0, abs_tol=1e-6)
    assert result.diagnostics.method == "SLSQP"
    assert result.diagnostics.converged is True
    assert result.diagnostics.constraint_violation is None
    assert result.diagnostics.feasible is None


def test_inequality_constraint_finds_boundary_minimum() -> None:
    constraints = [Constraint(kind="ineq", fun=lambda v: v[0] + v[1] - 1.0)]
    result = minimize_constrained(
        _paraboloid, [0.0, 0.0], bounds=[(-10.0, 10.0), (-10.0, 10.0)], constraints=constraints
    )
    assert math.isclose(result.x[0], 0.5, abs_tol=1e-6)
    assert math.isclose(result.x[1], 0.5, abs_tol=1e-6)
    assert result.diagnostics.feasible is True
    assert result.diagnostics.constraint_violation < 1e-6


@pytest.mark.parametrize("method", ["SLSQP", "trust-constr"])
def test_both_methods_find_the_same_constrained_minimum(method: str) -> None:
    constraints = [Constraint(kind="ineq", fun=lambda v: v[0] + v[1] - 1.0)]
    result = minimize_constrained(
        _paraboloid,
        [0.0, 0.0],
        bounds=[(-10.0, 10.0), (-10.0, 10.0)],
        constraints=constraints,
        method=method,  # type: ignore[arg-type]
    )
    assert math.isclose(result.x[0], 0.5, abs_tol=1e-3)
    assert result.diagnostics.method == method
    assert result.diagnostics.feasible is True


def test_trust_constr_reports_native_optimality() -> None:
    constraints = [Constraint(kind="ineq", fun=lambda v: v[0] + v[1] - 1.0)]
    result = minimize_constrained(
        _paraboloid,
        [0.0, 0.0],
        bounds=[(-10.0, 10.0), (-10.0, 10.0)],
        constraints=constraints,
        method="trust-constr",
    )
    assert result.diagnostics.optimality is not None


def test_slsqp_never_fabricates_optimality() -> None:
    constraints = [Constraint(kind="ineq", fun=lambda v: v[0] + v[1] - 1.0)]
    result = minimize_constrained(
        _paraboloid,
        [0.0, 0.0],
        bounds=[(-10.0, 10.0), (-10.0, 10.0)],
        constraints=constraints,
        method="SLSQP",
    )
    assert result.diagnostics.optimality is None


def test_contradictory_constraints_yield_infeasible_not_an_exception() -> None:
    constraints = [
        Constraint(kind="ineq", fun=lambda v: -(v[0] + v[1])),
        Constraint(kind="ineq", fun=lambda v: v[0] + v[1] - 1.0),
    ]
    result = minimize_constrained(
        _paraboloid, [0.0, 0.0], bounds=[(-10.0, 10.0), (-10.0, 10.0)], constraints=constraints
    )
    assert result.diagnostics.converged is False
    assert result.diagnostics.feasible is False


def test_unknown_method_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        minimize_constrained(_paraboloid, [0.0, 0.0], method="not_a_method")  # type: ignore[arg-type]


def test_unknown_constraint_kind_is_rejected() -> None:
    bad_constraint = Constraint(kind="not_a_kind", fun=lambda v: v[0])  # type: ignore[arg-type]
    with pytest.raises(NumericalDomainError):
        minimize_constrained(_paraboloid, [0.0, 0.0], constraints=[bad_constraint])


def test_bounds_length_mismatch_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        minimize_constrained(_paraboloid, [0.0, 0.0], bounds=[(-10.0, 10.0)])


def test_low_maxiter_yields_unconverged_not_an_exception() -> None:
    result = minimize_constrained(_paraboloid, [5.0, 5.0], max_iterations=1)
    assert result.diagnostics.converged is False


def test_select_default_method() -> None:
    assert select_default_method() == "SLSQP"
