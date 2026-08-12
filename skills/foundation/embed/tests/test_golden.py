import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_builtin_embed() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert out["result"]["backend"] == "builtin_hash"
    assert out["result"]["n"] == 2
    assert len(out["result"]["vectors"][0]) == 16
