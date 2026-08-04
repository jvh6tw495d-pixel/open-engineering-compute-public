"""Golden cases for energy.min_storage_capacity (composes optimization.lp)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_two_period_grid_zero_hand_oracle() -> None:
    """Hand: discharge 2 then 1 from full SOC → min capacity 3 Wh."""
    data = json.loads(
        (_SKILL_DIR / "examples" / "two_period_grid_zero.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])["result"]
    assert out["solver_status"] == "optimal"
    assert out["backend"] == "highs"
    assert out["optimal_capacity"]["unit"] == "Wh"
    assert out["optimal_capacity"]["value"] == pytest.approx(3.0, abs=1e-6)
    assert out["trajectory"]["grid_import"] == pytest.approx([0.0, 0.0], abs=1e-9)
    assert out["trajectory"]["discharge"] == pytest.approx([2.0, 1.0], abs=1e-6)
    assert out["n"] == 2


def test_curtailment_allows_surplus_pv() -> None:
    """With curtailment, surplus PV need not charge; capacity covers night only."""
    # t0: load 2, pv 0 → discharge 2; t1: load 0, pv 5 → curtail 5, no charge needed
    out = implementation.execute(
        {
            "load": [{"value": 2.0, "unit": "Wh"}, {"value": 0.0, "unit": "Wh"}],
            "pv": [{"value": 0.0, "unit": "Wh"}, {"value": 5.0, "unit": "Wh"}],
            "eta_charge": 1.0,
            "eta_discharge": 1.0,
            "soc_min": 0.0,
            "soc_max": 1.0,
            "initial_soc": 1.0,
            "horizon_hours": {"value": 2.0, "unit": "h"},
            "curtailment_allowed": True,
        }
    )["result"]
    assert out["solver_status"] == "optimal"
    assert out["optimal_capacity"]["value"] == pytest.approx(2.0, abs=1e-6)
    assert out["trajectory"]["curtailment"][1] == pytest.approx(5.0, abs=1e-6)


def test_unit_conversion_kwh() -> None:
    out = implementation.execute(
        {
            "load": [{"value": 0.002, "unit": "kWh"}, {"value": 0.001, "unit": "kWh"}],
            "pv": [{"value": 0.0, "unit": "kWh"}, {"value": 0.0, "unit": "kWh"}],
            "eta_charge": 1.0,
            "eta_discharge": 1.0,
            "soc_min": 0.0,
            "soc_max": 1.0,
            "initial_soc": 1.0,
            "horizon_hours": {"value": 2.0, "unit": "h"},
        }
    )["result"]
    assert out["solver_status"] == "optimal"
    # 0.002 + 0.001 kWh = 3 Wh
    assert out["optimal_capacity"]["value"] == pytest.approx(3.0, abs=1e-6)


def test_does_not_import_highs_directly() -> None:
    src = (_SKILL_DIR / "implementation.py").read_text(encoding="utf-8")
    assert "from oec.kernel.optimization.highs" not in src
    assert "solve_linear" not in src
    assert "import highspy" not in src
    assert "optimization" in src and "lp" in src
    assert "importlib" in src  # loads optimization.lp by path
