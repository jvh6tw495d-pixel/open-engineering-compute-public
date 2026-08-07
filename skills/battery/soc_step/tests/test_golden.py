import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_runs() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "charge_1h.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "result" in out
    assert isinstance(out["result"], dict)
    assert out["result"]["soc"] == 0.6
    assert out["result"]["energy_delta"] == {"value": 10.0, "unit": "Wh"}


def test_quantity_inputs_are_converted_to_canonical_units() -> None:
    out = implementation.execute(
        {
            "soc": 0.5,
            "power": {"value": 0.01, "unit": "kW"},
            "dt_hours": {"value": 60.0, "unit": "min"},
            "capacity": {"value": 0.1, "unit": "kWh"},
        }
    )
    assert out["result"]["soc"] == 0.6
    assert out["result"]["energy_delta"] == {"value": 10.0, "unit": "Wh"}
