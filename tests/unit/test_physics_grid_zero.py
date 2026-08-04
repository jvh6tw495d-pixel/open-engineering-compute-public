"""Unit tests for grid-zero feasibility helpers (v2.6.1 Wave 1 step 1.5)."""

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
)

from oec.physics.grid_zero import grid_zero_feasibility
from oec.physics.hybrid import hybrid_period_residual


def test_grid_zero_feasibility_true_when_islanded_and_balanced() -> None:
    """PV + storage cover load; grid_import all zero → grid-zero feasible."""
    # load 5 = pv 2 + discharge 3 - charge 0; grid 0
    out = grid_zero_feasibility(
        load=[5.0],
        pv=[2.0],
        grid_import=[0.0],
        charge=[0.0],
        discharge=[3.0],
        atol=1e-9,
        rtol=0.0,
        scale=1.0,
        unit="MWh",
    )
    assert out["feasible"] is True
    assert out["deficit_per_period"] == [pytest.approx(0.0)]
    assert out["balance_residual"] == [pytest.approx(0.0)]
    assert out["flags"]["balance_ok"] is True
    assert out["flags"]["has_deficit"] is False
    assert out["flags"]["has_grid_import"] is False
    assert out["flags"]["grid_zero"] is True
    assert out["flags"]["has_grid_export"] is False
    assert out["n"] == 1
    assert out["unit"] == "MWh"


def test_grid_zero_feasibility_allows_export_when_no_import() -> None:
    """Export (negative grid_import) is still grid-zero if balance holds."""
    # load 5 = pv 8 + grid (-2) + d 0 - c 1
    out = grid_zero_feasibility(
        load=[5.0],
        pv=[8.0],
        grid_import=[-2.0],
        charge=[1.0],
        discharge=[0.0],
        atol=1e-9,
        rtol=0.0,
        scale=1.0,
    )
    assert out["feasible"] is True
    assert out["deficit_per_period"][0] == pytest.approx(0.0)
    assert out["balance_residual"][0] == pytest.approx(0.0)
    assert out["flags"]["has_grid_export"] is True
    assert out["flags"]["has_grid_import"] is False
    assert out["flags"]["grid_zero"] is True


def test_grid_zero_feasibility_false_when_import_required() -> None:
    """Positive grid_import with a balanced trajectory is not grid-zero."""
    # load 10 = pv 1 + grid 7 + d 2 - c 0
    out = grid_zero_feasibility(
        load=[10.0],
        pv=[1.0],
        grid_import=[7.0],
        charge=[0.0],
        discharge=[2.0],
        atol=1e-9,
        rtol=0.0,
        scale=1.0,
    )
    assert out["balance_residual"][0] == pytest.approx(0.0)
    assert out["flags"]["balance_ok"] is True
    # Local shortfall without grid: 10 - (1 + 2 - 0) = 7
    assert out["deficit_per_period"][0] == pytest.approx(7.0)
    assert out["flags"]["has_deficit"] is True
    assert out["flags"]["has_grid_import"] is True
    assert out["flags"]["grid_zero"] is False
    assert out["feasible"] is False


def test_grid_zero_feasibility_false_when_unbalanced_zero_grid() -> None:
    """Zero grid but unmet load → deficit, not feasible."""
    out = grid_zero_feasibility(
        load=[10.0],
        pv=[1.0],
        grid_import=[0.0],
        charge=[0.0],
        discharge=[1.0],
        atol=1e-9,
        rtol=0.0,
        scale=1.0,
    )
    # residual = 10 - (1 + 0 + 1 - 0) = 8
    assert out["balance_residual"][0] == pytest.approx(8.0)
    assert out["deficit_per_period"][0] == pytest.approx(8.0)
    assert out["flags"]["balance_ok"] is False
    assert out["flags"]["has_deficit"] is True
    assert out["flags"]["grid_zero"] is True  # no import term, but load unmet
    assert out["feasible"] is False


def test_grid_zero_deficit_equals_import_when_balanced() -> None:
    """When hybrid residual is 0, deficit_per_period[t] == max(0, grid_import[t])."""
    load = [3.0, 4.0, 2.0]
    pv = [1.0, 0.5, 3.0]
    charge = [0.0, 0.0, 0.5]
    discharge = [0.5, 1.0, 0.0]
    # Close balance with grid
    grid = [load[t] - pv[t] - discharge[t] + charge[t] for t in range(3)]
    out = grid_zero_feasibility(
        load=load,
        pv=pv,
        grid_import=grid,
        charge=charge,
        discharge=discharge,
        atol=1e-12,
        rtol=0.0,
        scale=1.0,
    )
    assert out["flags"]["balance_ok"] is True
    for t in range(3):
        assert out["balance_residual"][t] == pytest.approx(0.0)
        assert out["deficit_per_period"][t] == pytest.approx(max(0.0, grid[t]))


def test_grid_zero_balance_residual_matches_hybrid_formula() -> None:
    load, pv, g, c, d = 6.0, 1.5, 2.0, 0.5, 1.0
    out = grid_zero_feasibility(
        load=[load],
        pv=[pv],
        grid_import=[g],
        charge=[c],
        discharge=[d],
    )
    expected = hybrid_period_residual(load, pv, g, c, d)
    assert out["balance_residual"][0] == pytest.approx(expected)


def test_grid_zero_defaults_charge_discharge_to_zero() -> None:
    out = grid_zero_feasibility(load=[3.0], pv=[1.0], grid_import=[2.0])
    assert out["charge"] == [0.0]
    assert out["discharge"] == [0.0]
    assert out["flags"]["balance_ok"] is True
    assert out["feasible"] is False  # import used
    assert out["deficit_per_period"][0] == pytest.approx(2.0)


def test_grid_zero_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="pv length"):
        grid_zero_feasibility(load=[1.0, 2.0], pv=[1.0], grid_import=[0.0, 0.0])
    with pytest.raises(ValueError, match="grid_import length"):
        grid_zero_feasibility(load=[1.0, 2.0], pv=[0.0, 0.0], grid_import=[0.0])


def test_grid_zero_rejects_empty_load() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        grid_zero_feasibility(load=[], pv=[], grid_import=[])


def test_grid_zero_rejects_negative_charge_discharge_pv_load() -> None:
    with pytest.raises(ValueError, match="charge"):
        grid_zero_feasibility(load=[1.0], pv=[0.0], grid_import=[1.0], charge=[-0.1])
    with pytest.raises(ValueError, match="discharge"):
        grid_zero_feasibility(load=[1.0], pv=[0.0], grid_import=[1.0], discharge=[-0.1])
    with pytest.raises(ValueError, match="pv"):
        grid_zero_feasibility(load=[1.0], pv=[-0.1], grid_import=[1.1])
    with pytest.raises(ValueError, match="load"):
        grid_zero_feasibility(load=[-1.0], pv=[0.0], grid_import=[-1.0])


def test_grid_zero_public_6period_fixture_not_grid_zero() -> None:
    """Canonical hybrid fixture uses imports → not grid-zero feasible."""
    assert len(LOAD) == N == 6
    out = grid_zero_feasibility(
        load=LOAD,
        pv=PV,
        grid_import=GRID_IMPORT,
        charge=CHARGE,
        discharge=DISCHARGE,
        atol=1e-9,
        rtol=0.0,
        unit=UNIT,
    )
    assert out["n"] == 6
    assert out["flags"]["balance_ok"] is True
    assert out["flags"]["has_grid_import"] is True
    assert out["flags"]["has_grid_export"] is True  # period 2 export
    assert out["feasible"] is False
    for t in range(N):
        assert out["balance_residual"][t] == pytest.approx(0.0, abs=1e-12)
        assert out["deficit_per_period"][t] == pytest.approx(max(0.0, GRID_IMPORT[t]), abs=1e-12)


def test_grid_zero_public_6period_islanded_variant_feasible() -> None:
    """Same load/PV with storage-only schedule that zeros imports and residual."""
    # Islanded schedule: cover local shortfall with discharge; store surplus.
    # residual_local = load - pv - d + c; set c,d so residual_local <= 0 and
    # close with grid_import = 0 (export not required if we don't charge beyond).
    # Simple construction: discharge = max(0, load-pv), charge = max(0, pv-load)
    charge = [max(0.0, PV[t] - LOAD[t]) for t in range(N)]
    discharge = [max(0.0, LOAD[t] - PV[t]) for t in range(N)]
    grid = [0.0] * N
    out = grid_zero_feasibility(
        load=LOAD,
        pv=PV,
        grid_import=grid,
        charge=charge,
        discharge=discharge,
        atol=1e-9,
        rtol=0.0,
        unit=UNIT,
    )
    assert out["flags"]["balance_ok"] is True
    assert out["flags"]["has_grid_import"] is False
    assert out["flags"]["has_deficit"] is False
    assert out["flags"]["grid_zero"] is True
    assert out["feasible"] is True
    assert all(d == pytest.approx(0.0) for d in out["deficit_per_period"])
    assert all(r == pytest.approx(0.0) for r in out["balance_residual"])


def test_grid_zero_module_has_no_lp_or_min_capacity() -> None:
    """Contract: physics.grid_zero exposes only feasibility evaluation."""
    import ast
    from pathlib import Path

    import oec.physics.grid_zero as mod

    assert list(mod.__all__) == ["grid_zero_feasibility"]
    assert not hasattr(mod, "min_storage_capacity")
    assert not hasattr(mod, "min_capacity")

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        name
        for name in imported
        if name.startswith(
            (
                "highspy",
                "scipy.optimize",
                "oec.kernel.optimization",
                "oec.backends",
            )
        )
        or name in {"highs", "linprog"}
    }
    assert not forbidden, f"unexpected solver/LP imports: {forbidden}"
