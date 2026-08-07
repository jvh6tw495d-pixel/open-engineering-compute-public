"""Unit tests for multi-period hybrid balance (v2.6.1 Wave 1 step 1.4)."""

from __future__ import annotations

import pytest
from tests.fixtures.physics.hybrid_6period import (
    CHARGE,
    DISCHARGE,
    GRID_IMPORT,
    LOAD,
    PV,
    UNIT,
    N,
    hybrid_6period_inputs,
)

from oec.physics.conservation import evaluate_residual
from oec.physics.hybrid import hybrid_balance, hybrid_period_residual


def test_hybrid_period_residual_zero_when_balance_holds() -> None:
    # LOAD = PV + grid + discharge - charge
    r = hybrid_period_residual(
        load=10.0,
        pv=3.0,
        grid_import=4.0,
        charge=1.0,
        discharge=4.0,
    )
    assert r == pytest.approx(0.0)


def test_hybrid_period_residual_export_as_negative_grid_import() -> None:
    """Single-field convention: export is negative grid_import, not a second field."""
    # LOAD 5 = PV 8 + grid_import (-2) + discharge 0 - charge 1
    r = hybrid_period_residual(
        load=5.0,
        pv=8.0,
        grid_import=-2.0,
        charge=1.0,
        discharge=0.0,
    )
    assert r == pytest.approx(0.0)
    # Positive residual means unmet load / missing supply
    r_short = hybrid_period_residual(5.0, 1.0, 0.0, 0.0, 0.0)
    assert r_short == pytest.approx(4.0)


def test_hybrid_balance_single_period_balanced() -> None:
    out = hybrid_balance(
        load=[5.0],
        pv=[2.0],
        grid_import=[2.0],
        charge=[0.0],
        discharge=[1.0],
        unit="MWh",
    )
    assert out["n"] == 1
    assert out["residuals"][0] == pytest.approx(0.0)
    assert out["supply"][0] == pytest.approx(5.0)
    assert out["balanced"] is True
    assert out["period_checks"]["t0"].balanced is True
    assert out["balance"].balanced is True
    assert out["balance"].unit == "MWh"


def test_hybrid_balance_defaults_charge_discharge_to_zero() -> None:
    out = hybrid_balance(load=[3.0], pv=[1.0], grid_import=[2.0])
    assert out["charge"] == [0.0]
    assert out["discharge"] == [0.0]
    assert out["balanced"] is True


def test_hybrid_balance_unbalanced_when_supply_short() -> None:
    out = hybrid_balance(
        load=[10.0],
        pv=[1.0],
        grid_import=[1.0],
        charge=[0.0],
        discharge=[1.0],
        atol=1e-9,
        rtol=0.0,
        scale=1.0,
        unit="MWh",
    )
    # residual = 10 - (1+1+1-0) = 7
    assert out["residuals"][0] == pytest.approx(7.0)
    assert out["balanced"] is False
    assert out["period_checks"]["t0"].balanced is False


def test_hybrid_balance_uses_conservation_owner_for_tolerance() -> None:
    """Residual check must match evaluate_residual (no rival formula)."""
    residual = 0.0005
    atol, rtol, scale = 1e-3, 1e-9, 1.0
    direct = evaluate_residual(residual, atol=atol, rtol=rtol, scale=scale, unit="MWh")
    # Craft series so residual is exactly 0.0005:
    # load - (pv + grid + d - c) = 1.0005 - (0.5 + 0.5 + 0 - 0) = 0.0005
    out = hybrid_balance(
        load=[1.0005],
        pv=[0.5],
        grid_import=[0.5],
        charge=[0.0],
        discharge=[0.0],
        atol=atol,
        rtol=rtol,
        scale=scale,
        unit="MWh",
    )
    check = out["period_checks"]["t0"]
    assert check.residual == pytest.approx(direct.residual)
    assert check.balanced is direct.balanced
    assert check.atol == direct.atol
    assert check.rtol == direct.rtol
    assert check.scale == direct.scale
    assert check.unit == direct.unit


def test_hybrid_balance_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="pv length"):
        hybrid_balance(load=[1.0, 2.0], pv=[1.0], grid_import=[0.0, 0.0])
    with pytest.raises(ValueError, match="grid_import length"):
        hybrid_balance(load=[1.0, 2.0], pv=[0.0, 0.0], grid_import=[0.0])
    with pytest.raises(ValueError, match="charge length"):
        hybrid_balance(
            load=[1.0, 2.0],
            pv=[0.0, 0.0],
            grid_import=[0.0, 0.0],
            charge=[0.0],
        )


def test_hybrid_balance_rejects_empty_load() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        hybrid_balance(load=[], pv=[], grid_import=[])


def test_hybrid_balance_rejects_negative_charge_discharge_pv_load() -> None:
    with pytest.raises(ValueError, match="charge"):
        hybrid_balance(load=[1.0], pv=[0.0], grid_import=[1.0], charge=[-0.1])
    with pytest.raises(ValueError, match="discharge"):
        hybrid_balance(load=[1.0], pv=[0.0], grid_import=[1.0], discharge=[-0.1])
    with pytest.raises(ValueError, match="pv"):
        hybrid_balance(load=[1.0], pv=[-0.1], grid_import=[1.1])
    with pytest.raises(ValueError, match="load"):
        hybrid_balance(load=[-1.0], pv=[0.0], grid_import=[-1.0])


def test_hybrid_6period_fixture_is_balanced() -> None:
    """Wave 1 accept: hybrid 6-period residual ~0 under a feasible trajectory."""
    assert len(LOAD) == N == 6
    # Sanity: fixture grid closes the balance algebraically
    for t in range(N):
        expected_grid = LOAD[t] - PV[t] - DISCHARGE[t] + CHARGE[t]
        assert GRID_IMPORT[t] == pytest.approx(expected_grid)

    out = hybrid_balance(**hybrid_6period_inputs(), atol=1e-9, rtol=0.0)
    assert out["n"] == 6
    assert out["unit"] == UNIT
    assert out["balanced"] is True
    assert out["balance"].balanced is True
    assert out["balance"].residual == pytest.approx(0.0, abs=1e-12)
    for t in range(N):
        assert out["residuals"][t] == pytest.approx(0.0, abs=1e-12)
        assert out["period_checks"][f"t{t}"].balanced is True
    # Period 2 must use negative grid_import (export), not a separate field
    assert out["grid_import"][2] < 0
    assert "grid_export" not in out


def test_hybrid_6period_export_period_supply_equals_load() -> None:
    """Explicit export period: PV surplus split between charge and export."""
    t = 2
    supply = PV[t] + GRID_IMPORT[t] + DISCHARGE[t] - CHARGE[t]
    assert supply == pytest.approx(LOAD[t])
    out = hybrid_balance(**hybrid_6period_inputs())
    assert out["supply"][t] == pytest.approx(LOAD[t])


def test_hybrid_6period_unbalanced_if_export_sign_flipped() -> None:
    """If someone mistakes export as +grid without charge, residual blows up."""
    bad_grid = list(GRID_IMPORT)
    bad_grid[2] = abs(bad_grid[2])  # wrong sign: treat export as import
    out = hybrid_balance(
        load=LOAD,
        pv=PV,
        grid_import=bad_grid,
        charge=CHARGE,
        discharge=DISCHARGE,
        atol=1e-9,
        rtol=0.0,
        scale=1.0,
        unit=UNIT,
    )
    assert out["balanced"] is False
    assert out["period_checks"]["t2"].balanced is False
    # residual at t2: 1.6 - (2.55 + 0.45 + 0 - 0.5) = 1.6 - 2.5 = -0.9
    assert out["residuals"][2] == pytest.approx(-0.9)
