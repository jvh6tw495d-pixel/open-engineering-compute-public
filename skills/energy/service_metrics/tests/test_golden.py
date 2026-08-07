"""Golden cases for energy.service_metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_two_hour_service() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "two_hour_service.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])["result"]
    # energy_delivered = 10*1 + 20*1 = 30 Wh
    assert out["energy_delivered"] == {"value": 30.0, "unit": "Wh"}
    # autonomy: 50 Wh covers 10+20 over 2 h fully
    assert out["autonomy_hours"] == {"value": 2.0, "unit": "h"}


def test_partial_autonomy() -> None:
    # capacity 15 Wh full; load 10 W then 20 W at 1 h → covers first hour + 5/20 h
    out = implementation.execute(
        {
            "load": [{"value": 10.0, "unit": "W"}, {"value": 20.0, "unit": "W"}],
            "pv": [{"value": 0.0, "unit": "W"}, {"value": 0.0, "unit": "W"}],
            "storage_discharge": [{"value": 0.0, "unit": "W"}, {"value": 0.0, "unit": "W"}],
            "grid_import": [{"value": 10.0, "unit": "W"}, {"value": 20.0, "unit": "W"}],
            "dt_hours": {"value": 1.0, "unit": "h"},
            "capacity": {"value": 15.0, "unit": "Wh"},
            "initial_soc": 1.0,
        }
    )["result"]
    assert out["energy_delivered"]["value"] == pytest.approx(30.0)
    assert out["autonomy_hours"]["value"] == pytest.approx(1.25)
