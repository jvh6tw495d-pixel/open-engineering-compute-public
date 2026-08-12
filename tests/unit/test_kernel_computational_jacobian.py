"""W1 Jacobian finite-difference tests."""

from __future__ import annotations

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.computational.differentiation import jacobian


def test_identity_map_jacobian() -> None:
    # f(x,y) = (x, y) → I
    def f0(v: list[float]) -> float:
        return v[0]

    def f1(v: list[float]) -> float:
        return v[1]

    result = jacobian([f0, f1], [2.0, 3.0], variables=["x", "y"])
    assert result.jacobian[0][0] == pytest.approx(1.0, abs=1e-8)
    assert result.jacobian[0][1] == pytest.approx(0.0, abs=1e-8)
    assert result.jacobian[1][0] == pytest.approx(0.0, abs=1e-8)
    assert result.jacobian[1][1] == pytest.approx(1.0, abs=1e-8)


def test_empty_functions_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        jacobian([], [1.0])
