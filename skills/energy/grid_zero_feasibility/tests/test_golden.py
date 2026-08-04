"""Golden cases for energy.grid_zero_feasibility."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_islanded_feasible() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "islanded_feasible.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])["result"]
    # Hand: t0 supply = 0.5+0+1.5-0 = 2; t1 = 1.5+0+0-0.5 = 1; residuals 0; no import.
    assert out["feasible"] is True
    assert out["deficit_per_period"] == [0.0, 0.0]
    assert out["balance_residual"] == [0.0, 0.0]
    assert out["flags"]["grid_zero"] is True
    assert out["flags"]["balance_ok"] is True


def test_import_makes_grid_zero_infeasible() -> None:
    out = implementation.execute(
        {
            "load": [{"value": 3.0, "unit": "W"}],
            "pv": [{"value": 1.0, "unit": "W"}],
            "storage_charge": [{"value": 0.0, "unit": "W"}],
            "storage_discharge": [{"value": 0.0, "unit": "W"}],
            "grid_import": [{"value": 2.0, "unit": "W"}],
            "dt_hours": {"value": 1.0, "unit": "h"},
        }
    )["result"]
    assert out["feasible"] is False
    assert out["flags"]["has_grid_import"] is True
    assert out["flags"]["grid_zero"] is False
    # Local deficit without grid: max(0, 3-1) = 2
    assert out["deficit_per_period"] == [2.0]
    assert out["balance_residual"] == [0.0]


def test_export_allowed_when_no_import() -> None:
    out = implementation.execute(
        {
            "load": [{"value": 1.0, "unit": "W"}],
            "pv": [{"value": 2.0, "unit": "W"}],
            "storage_charge": [{"value": 0.0, "unit": "W"}],
            "storage_discharge": [{"value": 0.0, "unit": "W"}],
            "grid_import": [{"value": -1.0, "unit": "W"}],
            "dt_hours": {"value": 1.0, "unit": "h"},
        }
    )["result"]
    assert out["feasible"] is True
    assert out["flags"]["has_grid_export"] is True
    assert out["flags"]["grid_zero"] is True
