import math

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.optimization.curve_fit import fit_curve, select_default_method


def _linear_model(v: list[float]) -> float:
    x, a, b = v
    return a * x + b


def test_lm_recovers_exact_linear_parameters() -> None:
    xdata = [0.0, 1.0, 2.0, 3.0, 4.0]
    ydata = [2.0 * x + 1.0 for x in xdata]
    result = fit_curve(_linear_model, xdata, ydata, p0=[1.0, 1.0])
    assert math.isclose(result.params[0], 2.0, abs_tol=1e-6)
    assert math.isclose(result.params[1], 1.0, abs_tol=1e-6)
    assert result.diagnostics.method == "lm"
    assert result.diagnostics.converged is True
    assert all(abs(r) < 1e-6 for r in result.diagnostics.residuals)
    assert result.diagnostics.optimality is None
    assert result.diagnostics.constraint_violation is None
    assert result.diagnostics.feasible is None


def test_trf_used_when_bounds_given() -> None:
    xdata = [0.0, 1.0, 2.0, 3.0, 4.0]
    ydata = [2.0 * x + 1.0 for x in xdata]
    result = fit_curve(
        _linear_model, xdata, ydata, p0=[1.0, 1.0], bounds=([0.0, 0.0], [10.0, 10.0])
    )
    assert result.diagnostics.method == "trf"
    assert math.isclose(result.params[0], 2.0, abs_tol=1e-6)


def test_lm_with_bounds_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        fit_curve(
            _linear_model,
            [0.0, 1.0],
            [0.0, 1.0],
            p0=[1.0, 1.0],
            bounds=([0.0, 0.0], [10.0, 10.0]),
            method="lm",
        )


def test_unknown_method_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        fit_curve(_linear_model, [0.0, 1.0], [0.0, 1.0], p0=[1.0, 1.0], method="not_a_method")  # type: ignore[arg-type]


def test_xdata_ydata_length_mismatch_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        fit_curve(_linear_model, [0.0, 1.0, 2.0], [0.0, 1.0], p0=[1.0, 1.0])


def test_insufficient_data_points_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        fit_curve(_linear_model, [0.0], [0.0], p0=[1.0, 1.0])


def test_low_max_iterations_yields_unconverged_not_an_exception() -> None:
    xdata = [0.0, 1.0, 2.0, 3.0, 4.0]
    ydata = [2.0 * x + 1.0 for x in xdata]
    result = fit_curve(_linear_model, xdata, ydata, p0=[0.0, 0.0], max_iterations=1)
    assert result.diagnostics.converged is False
    assert result.params == [0.0, 0.0]


def test_select_default_method() -> None:
    assert select_default_method(has_bounds=False) == "lm"
    assert select_default_method(has_bounds=True) == "trf"
