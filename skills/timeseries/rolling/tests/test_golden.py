import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_runs() -> None:
    examples = sorted((_SKILL_DIR / "examples").glob("*.json"))
    assert examples, "expected at least one example"
    data = json.loads(examples[0].read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "result" in out
    assert isinstance(out["result"], dict)
