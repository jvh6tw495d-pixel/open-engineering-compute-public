"""W1 1D heat / Poisson FDM tests."""

from __future__ import annotations

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.computational.pde import heat_1d


def test_steady_linear_profile() -> None:
    out = heat_1d(
        mode="steady",
        length=1.0,
        n_intervals=8,
        left_value=0.0,
        right_value=2.0,
        source=0.0,
    )
    for xi, ui in zip(out["x"], out["u"], strict=True):
        assert ui == pytest.approx(2.0 * xi, abs=1e-12)


def test_transient_cfl() -> None:
    with pytest.raises(NumericalDomainError, match="CFL"):
        heat_1d(mode="transient", n_intervals=4, diffusivity=1.0, dt=10.0, n_steps=1)
