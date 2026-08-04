"""Golden cases for energy.hybrid_balance."""

from __future__ import annotations

import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_two_period_balanced() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "balanced_two_period.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])["result"]
    assert out["balanced"] is True
    assert out["n"] == 2
    assert out["residuals"] == [0.0, 0.0]
    # supply[t] = pv + grid + discharge - charge → t0: 3, t1: 3-0.5-0.5=2
    assert out["supply"] == [3.0, 2.0]
    assert out["aggregate"]["balanced"] is True
    assert out["unit"] == "Wh"


def test_power_unit_conversion_kw_and_dt() -> None:
    """1 kW for 2 h → 2000 Wh energy residual bookkeeping."""
    out = implementation.execute(
        {
            "load": [{"value": 1.0, "unit": "kW"}],
            "pv": [{"value": 0.5, "unit": "kW"}],
            "grid_import": [{"value": 0.5, "unit": "kW"}],
            "storage_charge": [{"value": 0.0, "unit": "kW"}],
            "storage_discharge": [{"value": 0.0, "unit": "kW"}],
            "dt_hours": {"value": 2.0, "unit": "h"},
        }
    )["result"]
    # energy: load 2000 Wh, supply 0.5*2*1000 + 0.5*2*1000 = 2000 Wh
    assert out["balanced"] is True
    assert out["residuals"] == [0.0]
    assert out["supply"] == [2000.0]


def test_unbalanced_shortfall() -> None:
    out = implementation.execute(
        {
            "load": [{"value": 5.0, "unit": "W"}],
            "pv": [{"value": 1.0, "unit": "W"}],
            "grid_import": [{"value": 1.0, "unit": "W"}],
            "storage_charge": [{"value": 0.0, "unit": "W"}],
            "storage_discharge": [{"value": 0.0, "unit": "W"}],
            "dt_hours": {"value": 1.0, "unit": "h"},
        }
    )["result"]
    assert out["balanced"] is False
    assert out["residuals"][0] == 3.0
