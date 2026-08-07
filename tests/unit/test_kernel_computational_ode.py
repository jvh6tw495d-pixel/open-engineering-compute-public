"""Unified ODE kernel tests (ADR 0022)."""

from __future__ import annotations

import math

import pytest

from oec.kernel.computational.ode import integrate_ivp


def test_exponential_decay() -> None:
    result = integrate_ivp(lambda t, y: [-y[0]], (0.0, 1.0), [1.0], t_eval=[0.0, 1.0])
    assert result.t == pytest.approx([0.0, 1.0])
    assert result.y[-1][0] == pytest.approx(math.exp(-1.0), abs=1e-4)
    assert result.diagnostics.converged is True
    assert result.diagnostics.backend == "scipy"


def test_diagnostics_reports_function_calls() -> None:
    result = integrate_ivp(lambda t, y: [-y[0]], (0.0, 1.0), [1.0])
    assert result.diagnostics.function_calls is not None
    assert result.diagnostics.function_calls > 0


def test_default_method_is_rk45() -> None:
    result = integrate_ivp(lambda t, y: [1.0], (0.0, 1.0), [0.0])
    assert result.diagnostics.method == "RK45"
