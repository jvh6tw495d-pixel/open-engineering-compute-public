import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_runs() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "sample_load.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "result" in out
    assert isinstance(out["result"], dict)
    assert out["result"]["peak"] == {"value": 20.0, "unit": "W"}
    assert out["result"]["load_factor"] == 0.625


def test_quantity_inputs_are_converted_to_watts() -> None:
    out = implementation.execute(
        {"power_values": [{"value": 1.0, "unit": "kW"}, {"value": 500.0, "unit": "W"}]}
    )
    assert out["result"]["peak"] == {"value": 1000.0, "unit": "W"}
    assert out["result"]["average"] == {"value": 750.0, "unit": "W"}
