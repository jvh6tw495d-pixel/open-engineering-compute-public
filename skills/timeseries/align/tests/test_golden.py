import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_example_runs() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "inner.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "result" in out
    assert isinstance(out["result"], dict)
