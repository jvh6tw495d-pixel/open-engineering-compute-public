"""Unified integration kernel tests (ADR 0022)."""

from __future__ import annotations

import pytest

from oec.kernel.computational.integration import integrate_function, integrate_tabulated


def test_integrate_function_linear() -> None:
    result = integrate_function(lambda x: x, 0.0, 1.0)
    assert result.value == pytest.approx(0.5, abs=1e-8)
    assert result.mode == "function"
    assert result.diagnostics.converged is True
    assert result.diagnostics.model_dump()["n_evaluations"] > 0


def test_integrate_tabulated_simpson_autoselected() -> None:
    result = integrate_tabulated([0, 1, 2], [0, 1, 4])
    assert result.mode == "tabulated"
    assert result.diagnostics.method == "simpson"
    assert result.diagnostics.converged is None


def test_integrate_tabulated_trapezoid_for_two_points() -> None:
    result = integrate_tabulated([0, 1], [0, 1])
    assert result.diagnostics.method == "trapezoid"
    assert result.value == pytest.approx(0.5, abs=1e-8)


def test_integrate_tabulated_explicit_method_overrides_autoselect() -> None:
    result = integrate_tabulated([0, 1, 2], [0, 1, 4], method="trapezoid")
    assert result.diagnostics.method == "trapezoid"


def test_integrate_tabulated_converged_is_none_not_false() -> None:
    """ADR 0013 amendment: present-but-null means exact, not 'did not converge'."""
    result = integrate_tabulated([0, 1, 2], [0, 1, 4])
    assert result.diagnostics.converged is None
    assert result.diagnostics.converged is not False
