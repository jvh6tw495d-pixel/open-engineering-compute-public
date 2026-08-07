import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_runs() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "balanced.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "result" in out
    assert isinstance(out["result"], dict)
    assert out["result"]["total_in"] == {"value": 15.0, "unit": "Wh"}
    assert out["result"]["residual"] == {"value": 0.0, "unit": "Wh"}


def test_quantity_inputs_are_converted_to_wh() -> None:
    out = implementation.execute(
        {
            "energy_in": [{"value": 1.0, "unit": "kWh"}],
            "energy_out": [{"value": 750.0, "unit": "Wh"}],
            "storage_delta": {"value": 0.25, "unit": "kWh"},
        }
    )
    assert out["result"]["balanced"] is True
    assert out["result"]["total_in"] == {"value": 1000.0, "unit": "Wh"}
