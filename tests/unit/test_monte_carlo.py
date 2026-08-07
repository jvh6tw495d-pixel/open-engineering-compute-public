"""Unit tests for statistics.monte_carlo kernel (S15)."""

from __future__ import annotations

import pytest

from oec.kernel.statistics.monte_carlo import monte_carlo_mean


def test_monte_carlo_mean_x_squared() -> None:
    # E[x^2] for X~U(0,1) = 1/3
    out = monte_carlo_mean("x**2", n_samples=20000, low=0.0, high=1.0, seed=0)
    assert out["mean"] == pytest.approx(1.0 / 3.0, abs=0.02)
    assert out["n_samples"] == 20000
    assert out["ci95_low"] < out["mean"] < out["ci95_high"]


def test_monte_carlo_rejects_bad_bounds() -> None:
    with pytest.raises(ValueError, match="high"):
        monte_carlo_mean("x", n_samples=10, low=1.0, high=0.0, seed=1)
