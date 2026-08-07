"""Golden cases for battery.soc_trajectory (energy-based)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_charge_then_discharge() -> None:
    data = json.loads(
        (_SKILL_DIR / "examples" / "charge_then_discharge.json").read_text(encoding="utf-8")
    )
    out = implementation.execute(data["input"])["result"]
    # Hand: 0.5 + 10/100 = 0.6; 0.6 - 20/100 = 0.4
    assert out["soc_path"] == pytest.approx([0.5, 0.6, 0.4])
    assert out["soc"] == pytest.approx([0.6, 0.4])
    assert out["soc_final"] == pytest.approx(0.4)
    assert out["any_clipped"] is False
    assert out["unit"] == "Wh"
    assert out["energy_delta"][0] == pytest.approx(10.0)
    assert out["energy_delta"][1] == pytest.approx(-20.0)


def test_not_labeled_coulomb_counting() -> None:
    yaml_text = (_SKILL_DIR / "skill.yaml").read_text(encoding="utf-8")
    md = (_SKILL_DIR / "skill.md").read_text(encoding="utf-8")
    assert "coulomb" not in yaml_text.lower() or "not" in yaml_text.lower()
    assert "energy-based" in yaml_text.lower() or "energy-based" in md.lower()
    assert "storage_trajectory" in (_SKILL_DIR / "implementation.py").read_text(encoding="utf-8")


def test_clipping_reported() -> None:
    out = implementation.execute(
        {
            "initial_soc": 0.95,
            "powers": [{"value": 20.0, "unit": "W"}],
            "dt_hours": {"value": 1.0, "unit": "h"},
            "capacity": {"value": 100.0, "unit": "Wh"},
            "eta_charge": 1.0,
            "eta_discharge": 1.0,
        }
    )["result"]
    assert out["soc_final"] == pytest.approx(1.0)
    assert out["any_clipped"] is True
    assert out["clipped"] == [True]
