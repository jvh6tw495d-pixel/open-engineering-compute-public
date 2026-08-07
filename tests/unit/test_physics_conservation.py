"""Owner-level tests for the dense conservation checks (Wave 3 slice 3.1)."""

from __future__ import annotations

import pytest

from oec.physics.conservation import aggregate_balance, evaluate_residual, evaluate_vector_residual
from oec.physics.errors import ConservationError


def test_evaluate_vector_residual_checks_each_component_via_the_scalar_owner() -> None:
    checks = evaluate_vector_residual(
        {"bus-1": 0.0005, "bus-2": -0.0002},
        atol=1e-3,
        rtol=1e-9,
        scale=1.0,
        unit="pu",
    )

    assert set(checks) == {"bus-1", "bus-2"}
    assert checks["bus-1"].balanced is True
    assert checks["bus-2"].balanced is True
    assert checks["bus-1"].unit == "pu"


def test_evaluate_vector_residual_rejects_empty_input() -> None:
    with pytest.raises(ConservationError):
        evaluate_vector_residual({}, atol=1e-6, rtol=1e-9, scale=1.0, unit="W")


def test_aggregate_balance_sums_component_residuals_like_a_network_injection_check() -> None:
    checks = evaluate_vector_residual(
        {"bus-1": 0.4, "bus-2": -0.4},
        atol=0.5,
        rtol=1e-9,
        scale=1.0,
        unit="pu",
    )

    aggregate = aggregate_balance(checks)

    assert aggregate.residual == pytest.approx(0.0)
    assert aggregate.balanced is True
    assert aggregate.unit == "pu"


def test_aggregate_balance_is_false_when_any_component_is_unbalanced_even_if_sum_cancels() -> None:
    checks = {
        "bus-1": evaluate_residual(10.0, atol=1e-9, rtol=1e-9, scale=1.0, unit="W"),
        "bus-2": evaluate_residual(-10.0, atol=1e-9, rtol=1e-9, scale=1.0, unit="W"),
    }

    aggregate = aggregate_balance(checks)

    assert aggregate.residual == pytest.approx(0.0)
    assert aggregate.balanced is False


def test_aggregate_balance_rejects_mismatched_units() -> None:
    checks = {
        "a": evaluate_residual(0.0, atol=1e-6, rtol=1e-9, scale=1.0, unit="W"),
        "b": evaluate_residual(0.0, atol=1e-6, rtol=1e-9, scale=1.0, unit="Pa"),
    }
    with pytest.raises(ConservationError, match="different units"):
        aggregate_balance(checks)


def test_aggregate_balance_rejects_mismatched_tolerance_policy() -> None:
    checks = {
        "a": evaluate_residual(0.0, atol=1e-6, rtol=1e-9, scale=1.0, unit="W"),
        "b": evaluate_residual(0.0, atol=1e-3, rtol=1e-9, scale=1.0, unit="W"),
    }
    with pytest.raises(ConservationError, match="tolerance policy"):
        aggregate_balance(checks)


def test_aggregate_balance_rejects_empty_input() -> None:
    with pytest.raises(ConservationError):
        aggregate_balance({})


def test_evaluate_residual_rejects_non_finite_inputs() -> None:
    with pytest.raises(ConservationError, match="must be finite"):
        evaluate_residual(float("nan"), atol=1e-6, rtol=1e-9, scale=1.0, unit="W")
    with pytest.raises(ConservationError, match="must be finite"):
        evaluate_residual(0.0, atol=1e-6, rtol=float("inf"), scale=1.0, unit="W")
    with pytest.raises(ConservationError, match="must be finite"):
        evaluate_residual(0.0, atol=1e-6, rtol=1e-9, scale=float("-inf"), unit="W")


def test_evaluate_residual_rejects_negative_tolerances_or_scale() -> None:
    with pytest.raises(ConservationError, match="non-negative"):
        evaluate_residual(0.0, atol=-1e-6, rtol=1e-9, scale=1.0, unit="W")
    with pytest.raises(ConservationError, match="non-negative"):
        evaluate_residual(0.0, atol=1e-6, rtol=-1e-9, scale=1.0, unit="W")
    with pytest.raises(ConservationError, match="non-negative"):
        evaluate_residual(0.0, atol=1e-6, rtol=1e-9, scale=-1.0, unit="W")


def test_evaluate_residual_rejects_empty_unit() -> None:
    with pytest.raises(ConservationError, match="must not be empty"):
        evaluate_residual(0.0, atol=1e-6, rtol=1e-9, scale=1.0, unit="")
