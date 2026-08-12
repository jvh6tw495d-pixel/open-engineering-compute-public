import json
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_capabilities_probe() -> None:
    data = json.loads((_SKILL_DIR / "examples" / "example.json").read_text(encoding="utf-8"))
    out = implementation.execute(data["input"])
    assert "transformers_available" in out["result"]
    assert "embedding_backends" in out["result"]
