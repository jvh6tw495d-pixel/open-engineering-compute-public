"""Unit tests for finance public primitives (S19)."""

from __future__ import annotations

import pytest

from oec.kernel.finance.metrics import historical_var, max_drawdown, simple_returns


def test_simple_returns() -> None:
    out = simple_returns([100.0, 110.0, 99.0])
    assert out["n_returns"] == 2
    assert out["returns"][0] == pytest.approx(0.1)
    assert out["returns"][1] == pytest.approx(-0.1)


def test_simple_returns_rejects_short() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        simple_returns([1.0])


def test_simple_returns_rejects_zero_denom() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        simple_returns([0.0, 1.0])


def test_max_drawdown() -> None:
    out = max_drawdown([100.0, 120.0, 90.0, 110.0])
    assert out["max_drawdown"] == pytest.approx(90.0 / 120.0 - 1.0)


def test_max_drawdown_rejects_nonpositive() -> None:
    with pytest.raises(ValueError, match="positive"):
        max_drawdown([100.0, -1.0])


def test_historical_var() -> None:
    rets = [-0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03]
    out = historical_var(rets, confidence=0.9)
    assert out["var"] >= 0
    assert out["method"] == "historical"


def test_historical_var_rejects_bad_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        historical_var([0.1, -0.1], confidence=0.4)
